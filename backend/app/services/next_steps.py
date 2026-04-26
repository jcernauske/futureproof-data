"""Your Next Steps — post-gauntlet action checklist.

One Gemma call after the gauntlet completes. Produces four sections of
specific, data-grounded actions the student can take into the real world.
This is the one place we drop the RPG metaphor entirely.
"""

from __future__ import annotations

import logging

from app.models.career import AppliedSkill, Build
from app.services import gemma_client
from app.services.boss_fights import fmt_dollars, stat_explainer
from app.services.locale import (
    AppLocale,
    fallback_text,
    gemma_language_instruction,
    normalize_locale,
)

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are Gemma, writing a 'Your Next Steps' checklist for a high "
    "school student who just finished looking at one career path they "
    "could take. Each item is one concrete thing they can actually "
    "do next — a question to ask, a person to email, a page to "
    "verify, a conversation to have.\n\n"
    "Voice: candid, factual, warm, reassuring. Every item starts with "
    "a verb ('Ask', 'Email', 'Verify', 'Search', 'Enroll in', "
    "'Compare', 'Visit'). Every item names something real from the "
    "student's session — their school, their major, their likely "
    "career, a salary figure, a debt amount, an AI-exposure concern — "
    "in plain words.\n\n"
    "Never use these words or framings in your output:\n"
    "- stat codes: ERN, ROI, RES, GRW, HMN. Translate — 'the starting "
    "salary is low compared to other graduates from this program', "
    "never 'ERN is low'.\n"
    "- score fractions: never '7/10' or '3 out of 10'.\n"
    "- outcome labels: never WIN, DRAW, LOSE, won, lost, tied.\n"
    "- game framing: never 'fight', 'boss', 'gauntlet', 'battle', "
    "'beat', 'defeat', 'build', 'reroll', 'level up'. The student "
    "reads this checklist as a plan for real life, not as a game "
    "summary.\n"
    "- filler: no exclamation points, no 'your future awaits', no "
    "'empowering', no 'journey', no 'research your options', no "
    "'unleash', no 'dream career'.\n\n"
    "When the data shows a real weakness, name it honestly and pair "
    "it with one concrete thing the student can do about it. Never "
    "doom-frame — the student can always change school, major, or "
    "path.\n\n"
    "Output format: four markdown ## sections as specified below, "
    "3-5 numbered items per section, each verb-led. One or two plain "
    "sentences per item at a 7th-grade reading level. No preamble, "
    "no closing, no bullets inside items."
)


def _format_fights(build: Build) -> str:
    lines = []
    for fight in build.gauntlet.fights:
        parts = [f"{fight.label}: {fight.result.upper()} ({fight.reason})"]
        if fight.rerolled and fight.original_result:
            crafted = [
                s for s in build.skills_crafted if fight.boss in s.targets
            ]
            skill_names = ", ".join(s.title for s in crafted) if crafted else "none"
            parts.append(
                f"  Rerolled: {fight.original_result.upper()} → "
                f"{fight.result.upper()} using skills: {skill_names}"
            )
        lines.append("\n".join(parts))
    return "\n".join(lines)


def _format_skills_crafted(build: Build) -> str:
    if not build.skills_crafted:
        return "(none)"
    return "\n".join(
        f"- {s.title}: {_skill_delta_str(s)} — {s.rationale}"
        for s in build.skills_crafted
    )


def _skill_delta_str(skill: AppliedSkill) -> str:
    parts = []
    for label, val in (
        ("ERN", skill.delta_ern),
        ("ROI", skill.delta_roi),
        ("RES", skill.delta_res),
        ("GRW", skill.delta_grw),
        ("HMN", skill.delta_hmn),
    ):
        if val:
            parts.append(f"{label} {val:+d}")
    return ", ".join(parts) or "no stat change"


def _format_skill_recs(build: Build) -> str:
    if not build.skill_recs:
        return "(none)"
    return "\n".join(
        f"- {r.title} ({r.stat_impact}) — {r.rationale}"
        for r in build.skill_recs
    )


def _build_prompt(build: Build) -> str:
    career = build.career
    gauntlet = build.gauntlet
    wage = fmt_dollars(career.median_annual_wage)
    stats_block = stat_explainer(career)

    return (
        f"School: {career.institution_name}\n"
        f"Major: {career.program_name} (CIP {career.cipcode})\n"
        f"Primary career: {career.occupation_title} (SOC {career.soc_code})\n"
        f"Median salary: {wage}\n"
        f"Entry education: {career.education_level_name or 'unknown'}\n"
        f"Effort level: {build.effort}\n"
        f"Loan coverage: {int(build.loan_pct * 100)}%\n\n"
        f"{stats_block}\n\n"
        f"Boss fight results ({gauntlet.wins}W/{gauntlet.losses}L/"
        f"{gauntlet.draws}D):\n{_format_fights(build)}\n\n"
        f"Skills crafted during rerolls:\n"
        f"{_format_skills_crafted(build)}\n\n"
        f"Skill recommendations offered (not yet equipped):\n"
        f"{_format_skill_recs(build)}\n\n"
        "Write a 'Your Next Steps' action checklist with exactly four "
        "sections. Number the items within each section.\n\n"
        "## Questions to Ask Your Guidance Counselor\n"
        "3-5 questions grounded in this student's specific salary, debt, "
        "career outlook, boss fight results, and skill gaps. Use real "
        "dollar figures, not stat scores.\n\n"
        "## Questions to Ask College Recruiters\n"
        "3-5 questions to ask admissions/recruiters at this specific "
        "school, grounded in the build results.\n\n"
        "## Things to Verify on Your Own\n"
        "3-5 concrete items to look up online: verify courses/minors "
        "exist at the school, check job postings for the career, "
        "cross-reference salary data on BLS.gov.\n\n"
        "## Points to Discuss with Your Parents\n"
        "3-5 data-backed talking points for a productive family "
        "conversation. Be honest and two-sided — if the build has real "
        "weaknesses, acknowledge them and pair with the mitigation "
        "strategy (skills crafted, reroll results). Frame as informed "
        "discussion, not spin. Acknowledge when parents' concerns are "
        "valid and show what the data says about mitigation. Arm the "
        "student with facts, not rhetoric.\n\n"
        "Use markdown headers (##) for each section. Number items "
        "within each section. Every item must reference something "
        "specific from this student's data."
    )


def generate_next_steps(build: Build, locale: AppLocale | None = None) -> str:
    effective_locale = normalize_locale(locale or build.locale)
    system = f"{_SYSTEM}\n\n{gemma_language_instruction(effective_locale)}"
    text = gemma_client.generate(
        system=system,
        user=_build_prompt(build),
        max_tokens=2000,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("next_steps gen failed; using fallback")
    return fallback_text("next_steps_unavailable", effective_locale)
