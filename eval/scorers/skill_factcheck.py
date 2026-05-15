"""Skill fact-checkability scorer — Claude Opus 4.7 as judge.

The pattern-based skill_pool scorer (eval/scorers/skill_pool.py) tells us
whether a generated skill *looks* concrete and well-formed. It can't tell
us whether the named program actually exists at the named school. This
scorer asks Claude:

  "School: {school}. Skill: {title}. Rationale: {rationale}. Based on your
  knowledge of this school, does this program/course/club plausibly exist?"

Why Claude, not Gemma: same anti-circularity argument as the prose rubric.
We're verifying Gemma's claims about real-world US universities; using a
different, larger model with broad knowledge of those universities is the
right approach.

System prompt is cached (ephemeral) so repeated calls amortize the prefix
cost. Cost target: ~$1-2 for 111 calls.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, ValidationError

from eval.scorers.base import ScoreResult

if TYPE_CHECKING:
    import anthropic


_JUDGE_MODEL = "claude-opus-4-7"


class FactCheckAxis(BaseModel):
    score: int = Field(..., ge=1, le=5)
    reason: str = Field(..., max_length=400)


class SkillFactCheck(BaseModel):
    specificity: FactCheckAxis
    plausible_existence: FactCheckAxis
    factual_accuracy: FactCheckAxis
    flagged_hallucinations: list[str] = Field(default_factory=list)

    @property
    def realism_score(self) -> float:
        """Mean of plausible_existence + factual_accuracy.

        We don't average specificity in — a skill can be hand-wavy ("Take
        Initiative") and still not be a *fabrication*. The realism question
        is: did Gemma make up something that doesn't exist? That's the
        plausible_existence + factual_accuracy axes.
        """
        return (self.plausible_existence.score + self.factual_accuracy.score) / 2.0


_SYSTEM_PROMPT = """\
You are an independent fact-checker verifying AI-generated career advice
that cites specific programs at named US universities. You judge whether
the cited program/course/club/certification plausibly exists at the named
school.

You will be given:
- The student's school name
- The skill title (a program, course, minor, certification, club, etc.)
- The skill rationale (the explanation given to the student)

Score the skill on three axes (integer 1-5 each):

## Specificity
Does the title name a concrete, fact-checkable thing?
- 5: Names a specific verifiable entity (e.g., "Kelley School of Business
  Investment Banking Club", "ME 477: Engineering Economics", "Wharton
  Operations Minor")
- 4: Names a specific category at a named institution (e.g., "Purdue
  Co-op Program", "UCLA Financial Aid Office Workshops")
- 3: Names a recognizable generic category that universities reliably
  have (e.g., "Undergraduate Research Assistantship", "Federal Work-Study")
- 2: Vague but pointed at something (e.g., "Take a Personal Finance
  course")
- 1: Generic advice with no fact-checkable specifics (e.g., "Take
  Initiative", "Build a Portfolio")

## Plausible existence at this school
Based on your knowledge of US universities, does this specific
thing plausibly exist at this specific school?
- 5: You're confident it exists — famous named programs (Wharton at
  Penn, Kelley at IU, Tisch at NYU, Sloan at MIT), well-known course
  numbering conventions, established campus organizations
- 4: Very likely exists — schools of this type typically have this
  program (most R1 universities have an Honors College, a co-op
  program, etc.)
- 3: Plausible category but you can't verify the specific name (e.g.,
  "Investment Management Club" — most business schools have one;
  this school probably does too)
- 2: Doubtful — the cited program is in the wrong school type for
  this institution (e.g., "Pharm.D. program" at a community college
  that doesn't grant doctorates)
- 1: Almost certainly does not exist — clearly fabricated or
  mis-attributed (e.g., a "Kelley School of Business" at a school
  that isn't Indiana University)

## Factual accuracy
Are there clear factual errors in the title or rationale?
- 5: No errors detected
- 4: One small inaccuracy (e.g., slightly wrong program name) but
  the gist is right
- 3: One moderate error (e.g., wrong department attribution)
- 2: Multiple errors or one significant error (e.g., wrong degree
  level, wrong school)
- 1: Clear hallucination — invented facts or wrong school attribution

## Hallucinations
If you spot any clearly fabricated facts (made-up program names,
wrong school attributions, impossible course codes), quote them
verbatim in `flagged_hallucinations`. If none, return an empty list.

# Output format

Output ONLY valid JSON, no prose outside:

{
  "specificity": {"score": <1-5>, "reason": "<one sentence>"},
  "plausible_existence": {"score": <1-5>, "reason": "<one sentence>"},
  "factual_accuracy": {"score": <1-5>, "reason": "<one sentence>"},
  "flagged_hallucinations": ["<verbatim quote>", ...]
}
"""


def _make_client() -> "anthropic.Anthropic":
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Skill fact-check requires Claude as judge."
        )
    return anthropic.Anthropic(api_key=api_key)


def factcheck_one_skill(
    *,
    school: str,
    title: str,
    rationale: str,
    boss: str,
    client: "anthropic.Anthropic | None" = None,
) -> tuple[SkillFactCheck | None, str | None, dict[str, Any]]:
    """Run Claude judge on one (school, title, rationale) tuple.

    Returns (parsed_result, error_message, usage_dict). On success, error
    is None. On any failure (API error, parse error), returns (None, error,
    usage_dict_or_empty).
    """
    client = client or _make_client()
    user_prompt = (
        f"# School\n{school}\n\n"
        f"# Skill title\n{title}\n\n"
        f"# Skill rationale\n{rationale}\n\n"
        f"# Boss this skill targets (context)\n{boss}\n\n"
        "Score this skill on the three axes. Output JSON only."
    )

    try:
        response = client.messages.create(
            model=_JUDGE_MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # noqa: BLE001 — judge failure must not crash
        return None, f"api_error: {type(exc).__name__}: {exc}", {}

    text = next(
        (b.text for b in response.content if getattr(b, "type", None) == "text"),
        "",
    )
    usage = getattr(response, "usage", None)
    usage_dict = {
        "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
        "cache_read": getattr(usage, "cache_read_input_tokens", None) if usage else None,
        "cache_creation": getattr(usage, "cache_creation_input_tokens", None) if usage else None,
    }

    if not text:
        return None, "empty_response", usage_dict

    # Strip code fences if Claude wrapped the JSON
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0]

    try:
        payload = json.loads(cleaned)
        result = SkillFactCheck.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, f"parse_error: {type(exc).__name__}: {exc}", usage_dict

    return result, None, usage_dict


def factcheck_to_scoreresult(
    *, case_id: str, surface: str, school: str, title: str, rationale: str, boss: str,
    result: SkillFactCheck | None, error: str | None, usage: dict[str, Any],
) -> ScoreResult:
    """Adapt fact-check output to the eval harness ScoreResult shape."""
    if result is None:
        return ScoreResult(
            case_id=case_id,
            surface=surface,
            metric="skill_factcheck",
            score=0.0,
            passed=False,
            error=error,
            details={"school": school, "title": title, "usage": usage},
        )

    realism = result.realism_score / 5.0  # normalize to 0-1
    return ScoreResult(
        case_id=case_id,
        surface=surface,
        metric="skill_factcheck",
        score=realism,
        passed=result.realism_score >= 3.5,
        details={
            "school": school,
            "title": title,
            "rationale": rationale,
            "boss": boss,
            "specificity": result.specificity.model_dump(),
            "plausible_existence": result.plausible_existence.model_dump(),
            "factual_accuracy": result.factual_accuracy.model_dump(),
            "flagged_hallucinations": result.flagged_hallucinations,
            "realism_score": result.realism_score,
            "usage": usage,
        },
        tokens_input=usage.get("input_tokens"),
        tokens_output=usage.get("output_tokens"),
    )
