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

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are Gemma writing a 'Your Next Steps' action checklist for a "
    "student who just finished their FutureProof gauntlet. This is the "
    "one surface where you drop the RPG metaphor entirely — no 'boss', "
    "no 'fight', no 'build', no 'stats'. Speak as a knowledgeable peer "
    "advisor with receipts.\n\n"
    "Register: imperative and verb-led. Every item starts with a verb "
    "('Take', 'Email', 'Enroll in', 'Ask', 'Verify', 'Search'). Each "
    "item must cite something concrete from the student's session — "
    "their school name, major, occupation title, a salary dollar "
    "figure, a debt amount, or a fight outcome in plain language "
    "('the fight where AI exposure came up short').\n\n"
    "Anti-patterns: no 'empowering', no 'journey', no 'your future "
    "awaits', no exclamation points, no filler like 'research your "
    "options'. No raw stat scores ('ROI 9/10') — translate to dollars "
    "or plain English. When the data shows a real weakness, name it "
    "honestly and pair it with the mitigation. Arm the student with "
    "facts, not rhetoric.\n\n"
    "Output format: four markdown ## sections as specified below, "
    "3-5 numbered items per section, each verb-led. No preamble, no "
    "closing. Concise — one or two sentences per item."
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


def generate_next_steps(build: Build) -> str:
    text = gemma_client.generate(
        system=_SYSTEM,
        user=_build_prompt(build),
        max_tokens=2000,
        temperature=0.7,
    )
    if text:
        return text

    logger.warning("next_steps gen failed; using fallback")
    career = build.career
    gauntlet = build.gauntlet
    return (
        f"## Questions to Ask Your Guidance Counselor\n\n"
        f"1. Does {career.institution_name} offer minors or electives "
        f"that could strengthen the stats where this build scored lowest?\n\n"
        f"## Questions to Ask College Recruiters\n\n"
        f"1. What percentage of {career.program_name} graduates enter "
        f"{career.occupation_title} roles within a year of graduating?\n\n"
        f"## Things to Verify on Your Own\n\n"
        f"1. Search {career.institution_name}'s course catalog for the "
        f"courses and minors recommended in the skill recommendations.\n\n"
        f"## Points to Discuss with Your Parents\n\n"
        f"1. This path scored {gauntlet.wins} wins and {gauntlet.losses} "
        f"losses in the boss gauntlet — here's what that means for "
        f"long-term career risk."
    )
