"""Audience-question generation for PDF Report Exports.

See docs/specs/feature-pdf-report-exports.md §4 ``pdf_questions.py``.

Single scoped Gemma call returning all 3 audience arrays in JSON mode.
Falls back to static copy on every transport failure, malformed
response, schema violation, or forbidden-vocabulary leak. Every code
path emits exactly one ``logs/gemma.jsonl`` record (architect G3).

Token budget for ``_SYSTEM`` measured at ~280 tokens via
``tiktoken cl100k_base`` (see module docstring for the latest
measurement before merge — A2 from genai-architect §10).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from app.models.api import (
    AudienceQuestion,
    AudienceQuestions,
    GemmaPath,
)
from app.models.career import Build
from app.services import gemma_client
from app.services.pdf_copy import (
    BOSS_ORDER,
    FORBIDDEN_IN_GEMMA_OUTPUT,
    boss_advisory_label,
    contains_forbidden_term,
    risk_level_for_boss,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static fallback copy (§3.11.4).
# ---------------------------------------------------------------------------

STATIC_COLLEGE_MANDATORY: tuple[str, str] = (
    "Which majors at {school} most often lead graduates into {career}?",
    "How can I augment this major with the suggested skills above — through "
    "coursework, clubs, or internships you already offer?",
)

STATIC_COLLEGE_FALLBACK: str = (
    "What outcomes data do you publish for this program — median earnings "
    "one year out, employment rate, average debt at graduation?"
)

STATIC_PARENTS_FALLBACK: tuple[str, ...] = (
    "If the loan numbers on page 1 are accurate, can our family carry that "
    "monthly payment alongside everything else after I graduate?",
    "Whose career did you watch up close growing up — and what about it "
    "would you want for me, or want to spare me from?",
)

STATIC_YOURSELF_FALLBACK: tuple[str, ...] = (
    "Will I still want to be doing this work in 10 years if the day-to-day "
    "looks like the O*NET task profile on page 1?",
    "Am I picking this major because it interests me, or because it's "
    "familiar — and would I know the difference yet?",
)


# ---------------------------------------------------------------------------
# Gemma system prompt (§4 Gemma System Prompt and JSON Schema).
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You write follow-up questions for a one-page printed report a high "
    "school student takes home from a 90-second guidance-counselor "
    "conversation. The report shows a school, a major, a likely career, a "
    "five-stat profile, a five-row risk profile, and a cost-and-earnings "
    "strip. The student will read these questions aloud or silently with a "
    "counselor, with a parent, and to themselves.\n\n"
    "Voice: candid, concrete, useful. Coach posture, not cheerleader. "
    "Treat the student and audience as adults making a six-figure decision. "
    "No flattery, no hype, no apology. Each question is one sentence and "
    "names something specific from the build context (a school, a career, "
    "a risk factor, a number) — never a vague 'your future' or 'your "
    "passion'.\n\n"
    "Audience-voice rules (strict):\n"
    "- ask_the_college: audience-first. The student is talking to admissions, "
    "  a department head, or a counselor. Use action verbs ('publish', "
    "  'show', 'connect', 'tour') and refer to the school by name. NEVER "
    "  start with 'Will I' or 'Am I'.\n"
    "- ask_your_parents: audience-first. The student is at the kitchen "
    "  table. Reference family ('our family', 'you'), use shared verbs "
    "  ('carry', 'cover', 'spare'). NEVER start with 'Will I' or 'Am I'.\n"
    "- ask_yourself: student-first. The student is asking themselves. "
    "  Start with 'Will I', 'Am I', 'Do I', or 'Would I'. Present-future "
    "  tense. NEVER address an external audience.\n\n"
    "Anchor each question to a concrete element of the build. If the top "
    "risk is debt burden, write a debt question. If the top risk is AI "
    "displacement, write an AI question. Don't write the same question "
    "twice across audiences in different words.\n\n"
    "FORBIDDEN VOCABULARY — these terms appear in the in-app product but "
    "MUST NOT appear in any output you produce here. The output is for a "
    "printed advisory report and these terms read as unserious in print:\n"
    "  boss, boss fight, gauntlet, fight, win, lose, draw, won, lost, "
    "  reroll, build, builds, level up, ERN, ROI, RES, GRW, AURA, "
    "  HMN, Fight AI, Fight Student Loans, Fight the Market, Fight "
    "  Burnout, Fight the Ceiling, Fight the Future, WIN, DRAW, LOSE.\n"
    "If you need to refer to the cost-vs-earnings ratio, say 'debt-to-"
    "earnings' or 'debt service'. If you need to refer to AI exposure, "
    "say 'AI displacement', 'automation', or 'AI exposure'. If you need "
    "to refer to the program, say 'this program' or 'this major', not "
    "'this build' or 'this plan'.\n\n"
    "Length: each question is one sentence, 240 characters maximum.\n"
    "Count: zero to three questions per audience. Write fewer if you have "
    "nothing useful to add — the report has guaranteed static questions "
    "filling any gaps. Do not pad. Do not write filler.\n\n"
    "Output format: valid JSON, exactly this schema, no prose, no "
    "code-fence, no commentary. Each array holds zero to three short "
    "question strings. Example shape (illustrative only — do not echo "
    "these exact strings):\n"
    '{"ask_the_college": ["Question for the college?"], '
    '"ask_your_parents": ["Question for the parents?"], '
    '"ask_yourself": ["Will I question for myself?"]}\n'
    "If you cannot write a question for an audience, return an empty "
    "array for that audience. Do not write 'N/A', do not apologize, do "
    "not explain."
)


# ---------------------------------------------------------------------------
# Build-context scoping (per feedback_scoped_llm_contexts.md).
# ---------------------------------------------------------------------------


def _top_two_risks(build: Build) -> list[tuple[str, str]]:
    """Up-to-2 boss outcomes with the most concerning risk levels.

    Each tuple is (advisory_label, risk_level). ``Insufficient`` rows
    are skipped — Gemma should not be asked to riff on missing data.
    """
    severity = {"High": 0, "Elevated": 1, "Moderate": 2, "Low": 3, "Insufficient": 4}
    rows: list[tuple[str, str, int]] = []
    for boss in BOSS_ORDER:
        # Find this boss's fight in the gauntlet.
        fight = next((f for f in build.gauntlet.fights if f.boss == boss), None)
        if fight is None:
            continue
        level = risk_level_for_boss(boss, fight.raw_score)
        if level == "Insufficient":
            continue
        rows.append((boss_advisory_label(boss), level, severity[level]))
    rows.sort(key=lambda r: r[2])
    return [(label, level) for label, level, _ in rows[:2]]


def _top_two_strengths(build: Build) -> list[tuple[str, str]]:
    """Symmetric to _top_two_risks. Lowest risk = strongest factor."""
    severity = {"Low": 0, "Moderate": 1, "Elevated": 2, "High": 3, "Insufficient": 4}
    rows: list[tuple[str, str, int]] = []
    for boss in BOSS_ORDER:
        fight = next((f for f in build.gauntlet.fights if f.boss == boss), None)
        if fight is None:
            continue
        level = risk_level_for_boss(boss, fight.raw_score)
        if level == "Insufficient":
            continue
        rows.append((boss_advisory_label(boss), level, severity[level]))
    rows.sort(key=lambda r: r[2])
    return [(label, level) for label, level, _ in rows[:2]]


def _user_prompt(build: Build) -> str:
    """Build the small, scoped user message Gemma sees for this PDF.

    Per feedback_scoped_llm_contexts.md, only fields Gemma needs:
    school, major, career, top-2 risks, top-2 strengths. No PII, no raw
    scores, no internal IDs.
    """
    risks = _top_two_risks(build)
    strengths = _top_two_strengths(build)
    risks_str = "; ".join(f"{lbl}: {lvl}" for lbl, lvl in risks) or "(none ranked)"
    strengths_str = (
        "; ".join(f"{lbl}: {lvl}" for lbl, lvl in strengths) or "(none ranked)"
    )
    major = build.career.program_name or build.major_text or "this program"
    return (
        f"School: {build.school_name}\n"
        f"Major: {major}\n"
        f"Career: {build.career.occupation_title}\n"
        f"Top risk factors: {risks_str}\n"
        f"Strongest factors: {strengths_str}\n"
        "\n"
        "Write the JSON object now."
    )


# ---------------------------------------------------------------------------
# Static-fallback assembly.
# ---------------------------------------------------------------------------


def _static_college_questions(build: Build) -> list[AudienceQuestion]:
    """The 2 mandatory + 1 fallback static college questions (§3.11.4)."""
    school = build.school_name
    career = build.career.occupation_title
    return [
        AudienceQuestion(
            text=STATIC_COLLEGE_MANDATORY[0].format(school=school, career=career),
            is_static_mandatory=True,
        ),
        AudienceQuestion(
            text=STATIC_COLLEGE_MANDATORY[1],
            is_static_mandatory=True,
        ),
        AudienceQuestion(text=STATIC_COLLEGE_FALLBACK),
    ]


def _static_parents_questions() -> list[AudienceQuestion]:
    return [AudienceQuestion(text=q) for q in STATIC_PARENTS_FALLBACK]


def _static_yourself_questions() -> list[AudienceQuestion]:
    return [AudienceQuestion(text=q) for q in STATIC_YOURSELF_FALLBACK]


def _all_static(build: Build) -> tuple[
    list[AudienceQuestion],
    list[AudienceQuestion],
    list[AudienceQuestion],
]:
    return (
        _static_college_questions(build),
        _static_parents_questions(),
        _static_yourself_questions(),
    )


# ---------------------------------------------------------------------------
# Response parsing + validation.
# ---------------------------------------------------------------------------


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)


def _strip_code_fence(raw: str) -> str:
    """Strip optional ``` / ```json fencing — A3 from genai-architect §10."""
    return _CODE_FENCE_RE.sub("", raw).strip()


def _has_forbidden_term(text: str) -> bool:
    """True if ``text`` contains any term from FORBIDDEN_IN_GEMMA_OUTPUT."""
    return contains_forbidden_term(text, FORBIDDEN_IN_GEMMA_OUTPUT)


def _parse_response(raw: str) -> dict[str, list[str]] | None:
    """Parse a Gemma response into the 3-audience dict, or None on failure.

    None signals a "fallback_malformed" path. Caller distinguishes
    empty-response (raw == "") from malformed (raw != "" but unparseable).
    """
    if not raw:
        return None
    stripped = _strip_code_fence(raw)
    try:
        obj = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    out: dict[str, list[str]] = {}
    for key in ("ask_the_college", "ask_your_parents", "ask_yourself"):
        v = obj.get(key)
        if not isinstance(v, list):
            return None
        clean: list[str] = []
        for item in v:
            if not isinstance(item, str):
                return None
            text = item.strip()
            if not text:
                continue
            if len(text) > 240:
                # Spec contract — anything > 240 chars is malformed output.
                return None
            if _has_forbidden_term(text):
                return None
            clean.append(text)
        out[key] = clean
    return out


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def _assemble(
    college: list[AudienceQuestion],
    parents: list[AudienceQuestion],
    yourself: list[AudienceQuestion],
    *,
    gemma_path: GemmaPath,
) -> AudienceQuestions:
    """Cap each audience at 5 (Pydantic max) and floor at 1."""
    return AudienceQuestions(
        ask_the_college=college[:5],
        ask_your_parents=parents[:5],
        ask_yourself=yourself[:5],
        gemma_path=gemma_path,
    )


def _live_assemble(
    build: Build,
    parsed: dict[str, list[str]],
) -> AudienceQuestions:
    """Successful Gemma path: 2 mandatory college Qs + Gemma's additions.

    Static fallbacks fill the floor of 1 for parents/yourself when Gemma
    returns an empty array for that audience.
    """
    college = _static_college_questions(build)[:2]  # 2 mandatory only
    college += [AudienceQuestion(text=t) for t in parsed["ask_the_college"][:3]]

    parents_live = parsed["ask_your_parents"]
    if parents_live:
        parents = [AudienceQuestion(text=t) for t in parents_live]
    else:
        parents = _static_parents_questions()

    yourself_live = parsed["ask_yourself"]
    if yourself_live:
        yourself = [AudienceQuestion(text=t) for t in yourself_live]
    else:
        yourself = _static_yourself_questions()

    return _assemble(college, parents, yourself, gemma_path="live")


def _fallback(build: Build, path: GemmaPath) -> AudienceQuestions:
    """Static-only assembly — guaranteed non-empty per spec contract."""
    college, parents, yourself = _all_static(build)
    return _assemble(college, parents, yourself, gemma_path=path)


async def generate_audience_questions(
    build: Build,
    *,
    timeout_s: float = 6.0,
) -> AudienceQuestions:
    """Generate the 3-audience question set via a single scoped Gemma call.

    Always returns a non-empty AudienceQuestions. Every code path emits
    exactly one ``logs/gemma.jsonl`` record. See module docstring + spec
    §4 ``pdf_questions.py`` for the full contract.
    """
    extra = {"call_site": "pdf_questions"}
    user_msg = _user_prompt(build)

    try:
        raw = await asyncio.wait_for(
            gemma_client.generate_chat_async(
                system=_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=400,
                temperature=0.3,
                extra=extra,
                timeout_s=timeout_s,
                response_format="json",
            ),
            timeout=timeout_s + 1.0,
        )
    except asyncio.TimeoutError:
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_timeout",
            extra={"reason": "asyncio.TimeoutError"},
        )
        return _fallback(build, "fallback_timeout")
    except Exception as exc:
        # The gemma_client itself catches and returns "" on transport
        # error — but if this path raises (e.g. cold env, missing config)
        # we treat it as a disabled-backend signal.
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_disabled",
            extra={"reason": f"{type(exc).__name__}: {exc}"},
        )
        logger.warning("pdf_questions: gemma client unavailable: %s", exc)
        return _fallback(build, "fallback_disabled")

    if not raw:
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_empty",
        )
        return _fallback(build, "fallback_empty")

    parsed = _parse_response(raw)
    if parsed is None:
        gemma_client.log_synthetic_event(
            call_site="pdf_questions",
            event="fallback_malformed",
            extra={"raw_preview": raw[:300]},
        )
        return _fallback(build, "fallback_malformed")

    return _live_assemble(build, parsed)
