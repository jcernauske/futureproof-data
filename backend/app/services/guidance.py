"""'Gemma's Take' — the headline career guidance narrative.

Assembles the full context (school, major, career, pentagon, boss
results, branches) into a single prompt and asks Gemma for 4-6
sentences of coaching. This is the core value prop: the section
the student actually reads and acts on.

Tone: coach, not doom. Never tell a student their path is doomed;
tell them what to do about the weak spots.
"""

from __future__ import annotations

import logging

from app.models.career import (
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    SkillRec,
)
from app.services import gemma_client
from app.services.boss_fights import fmt_dollars, stat_explainer

logger = logging.getLogger(__name__)


_SYSTEM = (
    "You are Gemma. A high school student is looking at the career path "
    "that comes out of their school and major — who they'd likely become "
    "after graduating, what they'd earn, what the work actually involves. "
    "Your job is to explain, in plain words, what that whole picture "
    "means for their real life.\n\n"
    "Voice: candid, factual, warm, reassuring. Talk the way a calm older "
    "sibling with honest answers would talk — short, clear, no "
    "performance. You are the interpretation layer, not a judge. Never "
    "make the student feel small; never sugar-coat the numbers.\n\n"
    "Every sentence must translate the data into something real. If "
    "earnings are low compared to other graduates with this degree, say "
    "exactly that. If most of the daily work is something a computer can "
    "already do, say exactly that. If the cost is big compared to the "
    "starting salary, say exactly that. Use the actual dollar figures, "
    "years, and percentages the prompt gives you.\n\n"
    "Never use these words or framings in your output:\n"
    "- stat codes: ERN, ROI, RES, GRW, HMN. The student has never seen "
    "these letters. Translate to plain words — 'earnings start low "
    "compared to other graduates from this program', never the code or "
    "the number.\n"
    "- score fractions: never '7/10', '3 out of 10', or any numeric "
    "rating.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied. The "
    "student already sees labels above your words; repeating them is "
    "redundant.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat', 'villain', 'level up', 'quest', 'gauntlet "
    "scored', 'receipts'. Those belong to the app's framing, not yours. "
    "Talk about 'how high pay can go', 'what AI means for this work', "
    "'paying off the debt' — not 'the Ceiling fight' or 'Fight AI'.\n"
    "- filler: no exclamation points, bullet points, or 'as an AI'. "
    "Never 'empowering', 'journey', 'amazing', 'great news', 'unlock', "
    "'transform', 'your future awaits', 'unfortunately'.\n\n"
    "Structure: 4-6 sentences of prose at a 7th-grade reading level. "
    "First, explain what the whole career picture means in plain terms. "
    "Then name one or two concrete things the student can do while "
    "they're still in school to strengthen the weakest part of the "
    "picture. Never doom-frame — the student can always change school, "
    "major, or path."
)


def _format_bosses(gauntlet: GauntletResult) -> str:
    lines = []
    for fight in gauntlet.fights:
        marker = {
            "win": "WIN",
            "lose": "LOSE",
            "draw": "DRAW",
            "unknown": "N/A",
        }[fight.result]
        lines.append(f"- {fight.label}: {marker} ({fight.reason})")
    return "\n".join(lines)


def _format_branches(branches: list[CareerBranch]) -> str:
    if not branches:
        return "- (no Stage 3 branches available for this occupation)"
    lines = []
    for branch in branches[:5]:
        deltas = [
            f"{name}{delta:+d}"
            for name, delta in (
                ("ERN", branch.delta_ern),
                ("ROI", branch.delta_roi),
                ("RES", branch.delta_res),
                ("GRW", branch.delta_grw),
                ("HMN", branch.delta_hmn),
            )
            if isinstance(delta, int) and delta != 0
        ]
        delta_str = ", ".join(deltas) if deltas else "no stat deltas"
        lines.append(
            f"- {branch.to_title} ({branch.to_soc}): {delta_str}"
        )
    return "\n".join(lines)


def _prompt(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
) -> str:
    wage = fmt_dollars(career.median_annual_wage)
    stats_block = stat_explainer(career)
    return (
        f"Student is considering {career.institution_name}, majoring in "
        f"{career.program_name}.\n\n"
        f"Primary career after graduation: {career.occupation_title} "
        f"(SOC {career.soc_code})\n"
        f"Median salary: {wage}\n"
        f"Entry education: {career.education_level_name or 'unknown'}\n\n"
        f"{stats_block}\n\n"
        f"Boss fights:\n{_format_bosses(gauntlet)}\n\n"
        f"Career branches available:\n{_format_branches(branches)}\n\n"
        "Write 4-6 sentences of career guidance for this student. Be "
        "specific to their school and major — not generic advice. "
        "IMPORTANT: Do NOT reference stat scores directly (like 'ROI 9/10' "
        "or 'ERN 7/10') — students don't know what those mean. Instead, "
        "explain the real-world meaning: talk about salary amounts, debt "
        "levels, job market trends, and AI risk in plain English. Use the "
        "dollar figures and explanations provided above. "
        "If they lost a boss fight, explain what they can do about it. "
        "Mention 1-2 concrete actions they can take while still in school. "
        "Write at a 6th grade reading level. No jargon."
    )


def _fallback_narrative(
    career: CareerOutcome, gauntlet: GauntletResult
) -> str:
    """Degraded fallback — shown only when Gemma is unreachable.

    Voice contract matches ``_SYSTEM``: no stat codes, no outcome
    labels, no game framing. We name the school/major/career in plain
    terms and point the student at the weak spots in their build as
    something they can act on, without ranking them as wins or losses.
    """
    weak_labels = _weak_spot_phrases(gauntlet)
    if weak_labels:
        weak_clause = (
            " The parts of this path that look weakest right now are "
            f"{weak_labels} — those are the places to focus while you're "
            "still in school."
        )
    else:
        weak_clause = (
            " Nothing in this path looks broken right now — keep building on "
            "the parts that make it work."
        )
    return (
        f"{career.institution_name}'s {career.program_name} program "
        f"points toward {career.occupation_title}. The full write-up "
        f"didn't load this time — you can come back to it.{weak_clause}"
    )


# Plain-language phrases for the 5 boss concepts. Used in fallbacks so
# we can name the weak spot without ever saying "fight" or "boss".
_WEAK_SPOT_PHRASES: dict[str, str] = {
    "ai": "how much of this work a computer can already do",
    "loans": "how big the debt gets compared to the starting salary",
    "market": "how much hiring is happening in this field",
    "burnout": "how demanding the work is on the people doing it",
    "ceiling": "how high pay can go over a career",
}


def _weak_spot_phrases(gauntlet: GauntletResult) -> str:
    names = [
        _WEAK_SPOT_PHRASES[f.boss]
        for f in gauntlet.fights
        if f.result == "lose" and f.boss in _WEAK_SPOT_PHRASES
    ]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def generate_guidance(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
) -> str:
    """Generate the 'Gemma's Take' narrative. Falls back to a template
    string if Gemma is unreachable so the CLI still renders the block."""
    text = gemma_client.generate(
        system=_SYSTEM,
        user=_prompt(career, gauntlet, branches),
        # 4-6 sentences of coaching averages ~180 words, but Gemma 4
        # frequently prefaces with a sentence or two; 1200 gives it
        # real headroom so it never gets clipped mid-thought.
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("guidance gen failed; using deterministic fallback")
    return _fallback_narrative(career, gauntlet)


async def generate_guidance_async(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
) -> str:
    """Async variant — same fallback contract as :func:`generate_guidance`."""
    text = await gemma_client.generate_async(
        system=_SYSTEM,
        user=_prompt(career, gauntlet, branches),
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("guidance gen failed; using deterministic fallback")
    return _fallback_narrative(career, gauntlet)


# ---------------------------------------------------------------------------
# Conversational mode: "Ask Gemma"
# ---------------------------------------------------------------------------


_CHAT_SYSTEM = (
    "You are Gemma, in a chat thread with a high school student who is "
    "looking at the career path that comes out of their school and "
    "major. They're asking a follow-up question. Answer it plainly and "
    "specifically, using the data in the context.\n\n"
    "Voice: candid, factual, warm, reassuring. Short, clear sentences. "
    "Interpretation layer, not a judge. Never make the student feel "
    "small; never sugar-coat the numbers. If you don't know the answer, "
    "say so — do not invent numbers.\n\n"
    "Translate every data point into something real: dollar figures, "
    "years, percentages, what the daily work looks like. If a stat is "
    "low, say what that means in the real world ('earnings start low "
    "compared to other graduates from this program'), never cite the "
    "stat code or the score.\n\n"
    "Never use these words or framings in your output:\n"
    "- stat codes: ERN, ROI, RES, GRW, HMN.\n"
    "- score fractions: never '7/10' or '3 out of 10'.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat', 'villain', 'level up'. Talk about the career, "
    "the work, the money, the debt — not the app's framing.\n"
    "- filler: no exclamation points, 'as an AI', 'empowering', "
    "'journey', 'amazing', 'your future awaits', 'unfortunately'.\n\n"
    "If the student asks a 'what if' question about a different school "
    "or major, give your best honest read and say that the exact "
    "numbers come from running it as a new pick.\n\n"
    "Keep replies to 4-8 sentences of plain prose at a 7th-grade "
    "reading level, unless the student asks for more detail."
)


def _format_boss_summary(gauntlet: GauntletResult) -> str:
    if not gauntlet.fights:
        return "(no fights)"
    return ", ".join(
        f"{f.label}={f.result.upper()}" for f in gauntlet.fights
    )


def _format_branch_summary(branches: list[CareerBranch]) -> str:
    if not branches:
        return "(none available)"
    return "; ".join(b.to_title for b in branches[:5])


def _format_recs_summary(recs: list[SkillRec]) -> str:
    if not recs:
        return "(none)"
    return "; ".join(r.title for r in recs)


def _build_context_block(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    skill_recs: list[SkillRec],
) -> str:
    wage = fmt_dollars(career.median_annual_wage)
    stats_block = stat_explainer(career)
    return (
        "Student's build:\n"
        f"- School: {career.institution_name}\n"
        f"- Major: {career.program_name} (CIP {career.cipcode})\n"
        f"- Primary career: {career.occupation_title} "
        f"(SOC {career.soc_code}), median {wage}\n"
        f"- Entry education: {career.education_level_name or 'unknown'}\n\n"
        f"{stats_block}\n\n"
        f"- Boss fight results: {_format_boss_summary(gauntlet)}\n"
        f"- Available career branches: {_format_branch_summary(branches)}\n"
        f"- Skill recommendations given: {_format_recs_summary(skill_recs)}"
    )


def chat_with_context(
    *,
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
    skill_recs: list[SkillRec],
    conversation_history: list[dict],
    user_question: str,
) -> str:
    """Freeform Q&A with full build context loaded.

    The build context rides in the system prompt so every turn stays
    grounded in the student's actual numbers. ``conversation_history``
    holds prior user/assistant turns and accumulates across the session.
    """
    context_block = _build_context_block(career, gauntlet, branches, skill_recs)
    system_with_context = f"{_CHAT_SYSTEM}\n\n{context_block}"
    messages: list[dict] = [
        *conversation_history,
        {"role": "user", "content": user_question},
    ]
    text = gemma_client.generate_chat(
        system=system_with_context,
        messages=messages,
        max_tokens=1200,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("chat_with_context failed; using fallback")
    return (
        "I'm having trouble reaching Gemma right now. Your build at "
        f"{career.institution_name} in {career.program_name} is still "
        "loaded — try the question again in a moment."
    )
