"""Skill-pool realism scorer.

Gemma's job in ``skill_pool``: name **real, specific things the student at
[their school] could actually do** to overcome career challenges. The
production prompt is explicit about this. So the eval question is: are
the named skills real or hand-wavy?

We don't have a programmatic way to verify "does Indiana University offer
a Kelley Business Analytics Minor" without web search. What we CAN do is
score each generated skill on five proxies for realism, all deterministic
and free:

1. ``structural``: line parses as ``boss|title|deltas|rationale`` with a
   valid boss tag and at least one valid delta token.
2. ``specific``: the title contains a recognized category noun (minor,
   certification, fellowship, course, club, internship, program, etc.).
   Distinguishes "Kelley Business Analytics Minor" (specific) from
   "Take Initiative" (generic).
3. ``school_attributed``: the rationale mentions the student's school
   name (substring match, case-insensitive). The production prompt
   demands this — checks it.
4. ``boss_relevant``: the deltas align with the boss tag. A skill tagged
   ``ai`` should boost RES; a skill tagged ``loans`` should reduce
   loans/raise ROI. Wrong-sign deltas get dropped in production anyway —
   this metric counts how often Gemma gets it right pre-clamp.
5. ``voice_compliant``: rationale doesn't violate the explicit voice
   rules in the production system prompt (no stat codes, no game framing,
   no score fractions).

The pool-level metric is the % of generated skills passing each axis.
"""

from __future__ import annotations

import re
from typing import Any

from eval.scorers.base import GoldenCase, ScoreResult


_POOL_LINE = re.compile(
    r"^\s*(?P<boss>ai|loans|market|burnout|ceiling)\s*"
    r"\|\s*(?P<title>[^|]+?)\s*"
    r"\|\s*(?P<deltas>[^|]+?)\s*"
    r"\|\s*(?P<rationale>.+?)\s*$",
    re.IGNORECASE,
)

_DELTA_TOKEN = re.compile(
    r"(ern|roi|res|grw|hmn|burnout|ceiling|loans)\s*([+\-])\s*(\d+)",
    re.IGNORECASE,
)

# Category nouns that imply a specific, fact-checkable thing.
_SPECIFIC_NOUNS = [
    "minor",
    "major",
    "certification",
    "certificate",
    "cert ",  # avoid matching 'certain' but catch 'CCNA cert'
    "license",
    "fellowship",
    "scholarship",
    "internship",
    "co-op",
    "co op",
    "coop",
    "club",
    "society",
    "course",
    "elective",
    "program",
    "track",
    "concentration",
    "specialization",
    "bootcamp",
    "boot camp",
    "lab",
    "research project",
    "thesis",
    "capstone",
    "study abroad",
    "residency",
    "rotation",
    "apprenticeship",
    "honors",
    "AP exam",  # advanced placement
    "exam",  # captures CPA exam, MCAT, etc.
    "summer program",
]

# Voice violations.
_STAT_CODES = ["ERN", "ROI", "RES", "GRW", "AURA", "HMN"]
_GAME_WORDS = [
    "boss",
    "fight",
    "gauntlet",
    "battle",
    "beat",
    "defeat",
    "won",
    "lost",
    "tied",
    "victory",
    "loss",  # ambiguous but the prompt forbids it
]
_SCORE_FRACTION = re.compile(r"\b\d+\s*/\s*10\b")

# Boss → expected delta direction(s).
# The production sign-clamp in skill_pool.py:608-614:
#   ERN/ROI/RES/GRW/ceiling can only be positive (skills help)
#   burnout/loans can only be negative (skills reduce risk)
# So a skill targeting boss X should have at least one delta that matches:
_BOSS_RELEVANT_DELTAS: dict[str, set[str]] = {
    "ai": {"res+", "grw+"},                       # AI resilience
    "loans": {"loans-", "roi+"},                   # debt reduction
    "market": {"grw+", "ern+", "res+"},            # job market
    "burnout": {"burnout-"},                       # stress reduction
    "ceiling": {"ceiling+", "ern+", "roi+"},       # earnings ceiling
}


def _parse_skills(text: str) -> list[dict[str, Any]]:
    """Parse the pipe-delimited skill pool output."""
    skills = []
    for line in text.splitlines():
        m = _POOL_LINE.match(line.strip())
        if not m:
            continue
        boss = m.group("boss").lower()
        title = m.group("title").strip()
        deltas_raw = m.group("deltas").strip()
        rationale = m.group("rationale").strip()
        delta_tokens = []
        for tok in _DELTA_TOKEN.finditer(deltas_raw):
            stat = tok.group(1).lower()
            sign = tok.group(2)
            mag = int(tok.group(3))
            delta_tokens.append((stat, sign, mag))
        skills.append({
            "boss": boss,
            "title": title,
            "deltas_raw": deltas_raw,
            "delta_tokens": delta_tokens,
            "rationale": rationale,
        })
    return skills


def _check_specific(title: str) -> bool:
    """Does the title contain a recognized specific-noun category?"""
    haystack = title.lower()
    return any(noun.lower() in haystack for noun in _SPECIFIC_NOUNS)


def _check_school_attributed(rationale: str, school_name: str) -> bool:
    """Does the rationale mention the school by name? Use a substring
    of the school name (case-insensitive) — most schools have a short
    distinctive token (e.g., 'Indiana', 'Purdue', 'MIT', 'UCLA')."""
    if not school_name:
        return False
    haystack = rationale.lower()
    # Use the most distinctive token of the school name
    distinctive_tokens = [
        t.lower()
        for t in school_name.split()
        if len(t) >= 3 and t.lower() not in {"the", "and", "of", "for", "at", "in", "university", "college", "institute"}
    ]
    return any(tok in haystack for tok in distinctive_tokens)


def _check_boss_relevant(boss: str, delta_tokens: list[tuple[str, str, int]]) -> bool:
    """Does at least one delta align with the boss's expected direction?"""
    expected = _BOSS_RELEVANT_DELTAS.get(boss, set())
    if not expected:
        return False
    for stat, sign, _mag in delta_tokens:
        if f"{stat}{sign}" in expected:
            return True
    return False


def _check_voice_compliant(rationale: str) -> tuple[bool, list[str]]:
    """Returns (passed, list_of_violations)."""
    violations = []
    upper = rationale.upper()
    for code in _STAT_CODES:
        # Use word boundary to avoid 'aurora' matching 'AURA'
        if re.search(rf"\b{code}\b", upper):
            violations.append(f"stat_code:{code}")
    lower = rationale.lower()
    for word in _GAME_WORDS:
        if re.search(rf"\b{word}\b", lower):
            violations.append(f"game_word:{word}")
    if _SCORE_FRACTION.search(rationale):
        violations.append("score_fraction")
    return len(violations) == 0, violations


def score_skill_pool(
    *,
    case: GoldenCase,
    raw_text: str,
    surface: str,
    school_name: str,
) -> list[ScoreResult]:
    """Score one skill_pool output. Returns one ScoreResult per axis plus
    one summary result with the per-skill details."""
    skills = _parse_skills(raw_text or "")
    n = len(skills)

    if n == 0:
        return [ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric="skill_pool",
            score=0.0,
            passed=False,
            error="no parseable skills",
            details={"raw_text_excerpt": (raw_text or "")[:400]},
        )]

    per_skill: list[dict[str, Any]] = []
    counts = {"specific": 0, "school_attributed": 0, "boss_relevant": 0, "voice_compliant": 0}
    voice_violations: dict[str, int] = {}

    for skill in skills:
        specific = _check_specific(skill["title"])
        school_attr = _check_school_attributed(skill["rationale"], school_name)
        boss_rel = _check_boss_relevant(skill["boss"], skill["delta_tokens"])
        voice_ok, viols = _check_voice_compliant(skill["rationale"])

        if specific:
            counts["specific"] += 1
        if school_attr:
            counts["school_attributed"] += 1
        if boss_rel:
            counts["boss_relevant"] += 1
        if voice_ok:
            counts["voice_compliant"] += 1
        for v in viols:
            voice_violations[v] = voice_violations.get(v, 0) + 1

        per_skill.append({
            "boss": skill["boss"],
            "title": skill["title"],
            "specific": specific,
            "school_attributed": school_attr,
            "boss_relevant": boss_rel,
            "voice_compliant": voice_ok,
            "voice_violations": viols,
        })

    results = []
    for axis, count in counts.items():
        rate = count / n
        results.append(ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric=f"skill_{axis}_rate",
            score=rate,
            passed=rate >= 0.5,  # majority threshold for pool-level pass
            details={"n_skills": n, "passing": count, "rate": round(rate, 3)},
        ))

    # Aggregate "realism" = mean of specific + school_attributed
    realism = (counts["specific"] + counts["school_attributed"]) / (2 * n)
    results.append(ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="skill_realism_aggregate",
        score=realism,
        passed=realism >= 0.5,
        details={
            "n_skills": n,
            "axes": {k: round(v / n, 3) for k, v in counts.items()},
            "voice_violations": voice_violations,
            "per_skill": per_skill,
        },
    ))

    return results
