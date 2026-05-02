"""Gemma-generated skill recommendations.

Takes an assembled career outcome (with top O*NET activities and
boss fight results) and asks Gemma for 3-5 concrete actions the
student can take *while still in school* to strengthen weak stats.

Output is parsed into ``SkillRec`` structs for the CLI table. If
Gemma is unavailable, returns a deterministic placeholder set so
the CLI still renders the section.
"""

from __future__ import annotations

import logging
import re

from app.models.career import CareerOutcome, GauntletResult, SkillRec
from app.services import gemma_client
from app.services.locale import AppLocale, gemma_language_instruction, normalize_locale

logger = logging.getLogger(__name__)


_SYSTEM = (
    "You generate a short list of skill and coursework suggestions for "
    "a high school student choosing a college major. Each suggestion "
    "names one concrete thing the student can do while they're still "
    "in school at the school they picked — a course, a minor, a club, "
    "an internship. Never suggest changing school or major.\n\n"
    "Output format is strict. One suggestion per line, exactly:\n"
    "Title | STAT+N | Rationale\n\n"
    "The STAT+N tag is a machine-readable signal that the frontend "
    "renders as a small badge — it is NOT for the student to read. Use "
    "ERN, ROI, RES, or GRW, with a magnitude of +1 or +2 (rarely "
    "+3 for a full minor or certification). Never +4 or higher.\n\n"
    "Voice rules apply to the RATIONALE only — that is what the student "
    "actually reads. The rationale must be one plain-English sentence "
    "that names why this specific suggestion helps this specific "
    "student. In the rationale you must never use:\n"
    "- stat codes: ERN, ROI, RES, GRW, AURA, HMN. Explain in real-world "
    "terms — 'teaches you to direct AI tools instead of competing "
    "with them', not 'raises RES'.\n"
    "- score fractions: never '7/10' or '3 out of 10'.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat'. The suggestion connects to the student's real "
    "career, not the app's framing.\n"
    "- filler: no exclamation points, 'empowering', 'journey', "
    "'amazing', 'game-changer', 'unlock', 'transform'.\n\n"
    "Tone in the rationale: candid, factual, warm, reassuring. Short, "
    "clear, specific. 7th-grade reading level. Reference the student's "
    "actual school, major, or career when you have them."
)


# Hard ceiling on parsed stat deltas. Belt-and-suspenders for the
# prompt: even if Gemma ignores the instruction and emits RES+5, the
# parser clamps it to +2 so the downstream display never shows an
# implausible gain.
_MAX_POSITIVE_DELTA = 3
_CLAMPED_DELTA = 2


_REC_LINE = re.compile(
    r"^\s*[-*\d.)]*\s*"
    r"(?P<title>[^|;:()]+?)"
    r"\s*[|;:()]+\s*"
    # HMN kept in pattern for legacy parsing; folded to RES at clamp time.
    r"(?P<impact>(?:ERN|ROI|RES|GRW|HMN)\s*[+\-]?\d+)"
    r"\s*[|;:()]+\s*"
    r"(?P<rationale>.+?)\s*$",
    re.IGNORECASE,
)

_IMPACT_PARTS = re.compile(
    r"^(?P<stat>ERN|ROI|RES|GRW|HMN)\s*(?P<sign>[+\-]?)(?P<mag>\d+)$",
    re.IGNORECASE,
)


def _clamp_impact(raw: str) -> str:
    """Normalize ``stat_impact`` and clamp runaway magnitudes.

    Gemma occasionally emits ``RES+5`` or ``HMN+5`` even when the system
    prompt forbids it. Anything larger than ``_MAX_POSITIVE_DELTA`` is
    pulled back to ``_CLAMPED_DELTA``. Negative deltas are left alone —
    the prompt never asks for them and the rare legitimate use (e.g.
    "drop an elective that hurts GRW") is inherently modest. Unparseable
    input falls back to the raw cleaned string so downstream display
    doesn't crash.
    """
    cleaned = raw.replace(" ", "").upper()
    match = _IMPACT_PARTS.match(cleaned)
    if not match:
        return cleaned
    stat = match.group("stat")
    # Legacy HMN folds into RES (RES absorbs the human-essential signal
    # post-pentagon-stat-reshape). Done at clamp time so any code path
    # that emits HMN+N — Gemma, fallback, parsed line — lands cleanly.
    if stat == "HMN":
        stat = "RES"
    sign = match.group("sign") or "+"
    magnitude = int(match.group("mag"))
    if sign == "+" and magnitude > _MAX_POSITIVE_DELTA:
        logger.info(
            "clamping skill rec delta %s%s%d -> %s+%d",
            stat,
            sign,
            magnitude,
            stat,
            _CLAMPED_DELTA,
        )
        magnitude = _CLAMPED_DELTA
        sign = "+"
    return f"{stat}{sign}{magnitude}"


def _prompt(career: CareerOutcome, gauntlet: GauntletResult) -> str:
    stats = career.stats
    weak_spots = [f.label for f in gauntlet.fights if f.result == "lose"]
    weak_spots_str = ", ".join(weak_spots) or "none"
    top_human = ", ".join(
        str(item.get("activity", ""))
        for item in career.top_human_activities[:4]
        if item.get("activity")
    )
    return (
        f"Student school: {career.institution_name}\n"
        f"Major: {career.program_name}\n"
        f"Primary career: {career.occupation_title} (SOC {career.soc_code})\n"
        f"Stats: ERN {stats.ern}, ROI {stats.roi}, RES {stats.res}, "
        f"GRW {stats.grw}, AURA {stats.aura}\n"
        f"Lost boss fights: {weak_spots_str}\n"
        f"Uniquely human activities in this career: {top_human}\n\n"
        f"Generate 4 skill recommendations. Each must target a specific "
        f"stat. Format EXACTLY as:\n"
        f"Name of action | STAT+N | 1-sentence reason\n\n"
        f"Example:\n"
        f"Data Analytics Minor | RES+2 | Learn to direct AI analysis, "
        f"not compete with it.\n\n"
        f"Do not number your responses. Do not add preamble."
    )


def _fallback_recs(career: CareerOutcome) -> list[SkillRec]:
    return [
        SkillRec(
            title="Data Analytics coursework",
            stat_impact="RES+1",
            rationale="Learn to direct AI tools rather than compete with them.",
        ),
        SkillRec(
            title="Internship in your field",
            stat_impact="RES+1",
            rationale="Real-world exposure beats any classroom lecture.",
        ),
        SkillRec(
            title="Communication-heavy elective",
            stat_impact="RES+1",
            rationale="The human-facing side is where careers compound.",
        ),
    ]


def _parse_recs(text: str, career: CareerOutcome) -> list[SkillRec]:
    """Parse Gemma's pipe-delimited output into SkillRecs.

    Falls back to the deterministic recommendation set when parsing
    yields zero usable lines or when the caller passed empty text.
    """
    if not text:
        return _fallback_recs(career)

    recs: list[SkillRec] = []
    for line in text.splitlines():
        match = _REC_LINE.match(line)
        if not match:
            continue
        title = match.group("title").strip(" -•")
        impact = _clamp_impact(match.group("impact"))
        rationale = match.group("rationale").strip().strip('"\'')
        if not title or not rationale:
            continue
        recs.append(
            SkillRec(title=title, stat_impact=impact, rationale=rationale)
        )
        if len(recs) >= 5:
            break

    if not recs:
        logger.debug("skill rec parsing failed, using fallback. raw=%r", text[:200])
        return _fallback_recs(career)
    return recs


def generate_recs(
    career: CareerOutcome, gauntlet: GauntletResult, locale: AppLocale = "en",
) -> list[SkillRec]:
    locale = normalize_locale(locale)
    system = f"{_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = gemma_client.generate(
        system=system,
        user=_prompt(career, gauntlet),
        # 4 pipe-delimited lines at ~25 tokens each = ~100, plus
        # Gemma preamble; 800 keeps every rec intact.
        max_tokens=800,
        temperature=0.6,
    )
    return _parse_recs(text, career)


async def generate_recs_async(
    career: CareerOutcome, gauntlet: GauntletResult, locale: AppLocale = "en",
) -> list[SkillRec]:
    """Async variant — same behavior, fans out through
    ``gemma_client.generate_async`` so the /build router can gather it
    alongside the boss narratives and guidance call.
    """
    locale = normalize_locale(locale)
    system = f"{_SYSTEM}\n\n{gemma_language_instruction(locale)}"
    text = await gemma_client.generate_async(
        system=system,
        user=_prompt(career, gauntlet),
        max_tokens=800,
        temperature=0.6,
    )
    return _parse_recs(text, career)
