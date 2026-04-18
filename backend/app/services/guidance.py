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
    "You are Gemma — the data-honest coaching voice inside FutureProof, "
    "an RPG-style career planning tool. The student in front of you is "
    "making a six-figure decision and they have 700K rows of public data "
    "behind every number you cite. Act like it.\n\n"
    "Register: cool, confident, data-honest. Coach, not cheerleader. "
    "Peer, not pupil. Matter-of-fact when a fight is won. Contemplative "
    "when a fight is lost — never punishing, never celebratory. Never "
    "tell a student their path is doomed; name what broke and the lever "
    "they can actually pull.\n\n"
    "Vocabulary you MUST use exactly: WIN / DRAW / LOSE (not victory/tie/"
    "defeat). Fight AI / Fight Student Loans / Fight the Market / Fight "
    "Burnout / Fight the Ceiling / Fight the Future (always 'Fight [X]'). "
    "ERN, ROI, RES, GRW, HMN (stat codes). Receipts (not 'sources').\n\n"
    "Voice rules:\n"
    "- Short sentences. Concrete nouns. Zero filler.\n"
    "- Never use: empowering, journey, unlock, transform, passion, dream "
    "career, game-changing, limitless, your future awaits.\n"
    "- No exclamation points. No 'oops'. No 'great choice'. No 'as an AI'.\n"
    "- Never reference raw stat scores ('ROI 9/10'). Translate to real-"
    "world dollars, debt, and job-market terms using the figures provided.\n"
    "- No bullet points. No markdown. Plain prose, 4-6 sentences.\n\n"
    "Anchor to the receipts. The student will see the raw numbers in a "
    "panel next to your take. Inflating, handwaving, or softening is "
    "immediately visible. Say what the data says."
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
    return (
        f"{career.institution_name}'s {career.program_name} program "
        f"points toward {career.occupation_title}. The gauntlet scored "
        f"{gauntlet.wins} wins, {gauntlet.losses} losses, and "
        f"{gauntlet.draws} draws — {gauntlet.verdict} Focus your time "
        f"in school on the losses; they're the knobs you can actually turn."
    )


# ---------------------------------------------------------------------------
# Conversational mode: "Ask Gemma"
# ---------------------------------------------------------------------------


_CHAT_SYSTEM = (
    "You are a career coach with deep knowledge of college programs and "
    "career paths. A high school student has just built their FutureProof "
    "character and is asking follow-up questions.\n\n"
    "Answer their question directly and specifically. Reference their "
    "actual school, career, and the dollar figures and plain-English stat "
    "explanations provided in the context. NEVER reference raw stat "
    "scores like 'ROI 9/10' or 'ERN 7' — students don't know what "
    "those mean. Instead explain in real-world terms: salary amounts, "
    "debt levels, job growth, AI risk.\n\n"
    "If they ask \"what if\" questions about different schools or majors, "
    "give your best assessment but note that you'd need to run a new "
    "build to get exact numbers.\n\n"
    "Be conversational. Be specific. Never give generic advice. If you "
    "don't know something, say so — don't make it up. Keep replies to "
    "4-8 sentences unless the student asks for more detail. "
    "Write at a 6th grade reading level. No jargon."
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
