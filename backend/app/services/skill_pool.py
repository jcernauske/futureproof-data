"""Boss-fight skill pool — personalized by Gemma, curated fallback.

The primary path is ``generate_pool(career, gauntlet)``: during the
build pass, once the gauntlet has scored and we know which bosses the
student lost, we call Gemma once to produce 3-5 structured skills per
losing boss, grounded in the student's actual school + major +
career path. The parsed ``AppliedSkill`` list lives on ``Build`` as
``skill_pool`` so the reroll flow has zero extra latency.

When Gemma fails, returns empty, or produces fewer than 3 valid skills
for a given losing boss, ``FALLBACK_POOL`` fills the gap. The fallback
is the original hand-curated set — generic but structurally sound, so
the reroll mechanic never fully breaks.

Each skill lists the bosses it's eligible to surface on (``targets``)
and the stat deltas it applies build-wide once crafted. Stat deltas
clamp to [1, 10] when they're applied in ``apply_skills``. Burnout and
ceiling have dedicated raw deltas because those fights score off the
raw boss fields rather than the pentagon stats.
"""

from __future__ import annotations

import logging
import re

from app.models.career import (
    AppliedSkill,
    BossId,
    BossScores,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import gemma_client

logger = logging.getLogger(__name__)


# Safety net — used when Gemma generation fails or under-produces for a
# specific boss. Generic but structurally correct: every skill has a
# valid target list and a non-zero delta so the reroll math still works.
FALLBACK_POOL: list[AppliedSkill] = [
    # --- Fight AI (RES + HMN) ----------------------------------------
    AppliedSkill(
        id="data_analytics_minor",
        title="Data Analytics Minor",
        rationale=(
            "Learn to direct AI analysis tools instead of competing "
            "with them. Adds a quantitative layer to any major."
        ),
        targets=["ai", "market"],
        delta_res=2,
    ),
    AppliedSkill(
        id="ai_literacy_course",
        title="AI Literacy Elective",
        rationale=(
            "One semester of hands-on prompt engineering and tool use "
            "moves you from 'replaced by AI' to 'operates with AI'."
        ),
        targets=["ai"],
        delta_res=1,
    ),
    AppliedSkill(
        id="field_internship",
        title="Paid Internship in Your Field",
        rationale=(
            "Real-world exposure beats any classroom lecture and "
            "signals human judgment employers actually value."
        ),
        targets=["ai", "burnout", "ceiling"],
        delta_hmn=1,
        delta_res=1,
    ),
    AppliedSkill(
        id="design_thinking_elective",
        title="Design Thinking / Human-Centered Design Course",
        rationale=(
            "Reframes the human-facing side of work as a teachable "
            "discipline — the part AI can't do well."
        ),
        targets=["ai"],
        delta_hmn=2,
    ),
    # --- Fight Student Loans (ROI) -----------------------------------
    AppliedSkill(
        id="cc_transfer_first_year",
        title="Community College Transfer (Year 1)",
        rationale=(
            "Knock out gen eds at community-college tuition, then "
            "transfer in — same degree, materially lower debt."
        ),
        targets=["loans"],
        delta_roi=2,
    ),
    AppliedSkill(
        id="work_study",
        title="Federal Work-Study Program",
        rationale=(
            "On-campus job that reduces cost-of-attendance and "
            "doesn't count against financial aid."
        ),
        targets=["loans"],
        delta_roi=1,
    ),
    AppliedSkill(
        id="scholarship_sprint",
        title="Scholarship Application Sprint",
        rationale=(
            "Treating scholarship applications like a part-time job "
            "during senior year of HS is the single highest-ROI "
            "activity in college planning."
        ),
        targets=["loans"],
        delta_roi=2,
    ),
    AppliedSkill(
        id="instate_tuition",
        title="Establish In-State Residency",
        rationale=(
            "If you're borderline, locking in in-state tuition can "
            "cut the sticker price in half."
        ),
        targets=["loans"],
        delta_roi=1,
    ),
    # --- Fight the Market (GRW + ERN) --------------------------------
    AppliedSkill(
        id="emerging_tech_cert",
        title="Emerging-Tech Certificate",
        rationale=(
            "A stackable credential in an adjacent growing field "
            "shifts you onto a higher-demand trajectory."
        ),
        targets=["market"],
        delta_grw=2,
    ),
    AppliedSkill(
        id="industry_conference",
        title="Industry Conference Circuit",
        rationale=(
            "Two conferences per year builds the professional "
            "network that routes you to growing employers."
        ),
        targets=["market", "ceiling"],
        delta_grw=1,
        delta_ern=1,
    ),
    AppliedSkill(
        id="portfolio_project",
        title="Portfolio-Building Independent Project",
        rationale=(
            "A concrete artifact employers can see moves you from "
            "'applicant pool' to 'specific candidate with receipts'."
        ),
        targets=["market"],
        delta_ern=1,
        delta_grw=1,
    ),
    # --- Fight Burnout (raw burnout score) ---------------------------
    AppliedSkill(
        id="campus_counseling",
        title="Campus Counseling Center Partnership",
        rationale=(
            "Free, confidential support that catches burnout before "
            "it derails your degree — use it before you need it."
        ),
        targets=["burnout"],
        delta_burnout_raw=-2,
    ),
    AppliedSkill(
        id="mindfulness_course",
        title="Stress Management / Mindfulness Course",
        rationale=(
            "Trained coping skills lower burnout risk and show up in "
            "research on sustained high performance."
        ),
        targets=["burnout"],
        delta_burnout_raw=-1,
        delta_hmn=1,
    ),
    AppliedSkill(
        id="cohort_study_group",
        title="Cohort Study Group",
        rationale=(
            "Sharing the load with peers in the same major is the "
            "cheapest, most reliable burnout prevention there is."
        ),
        targets=["burnout"],
        delta_burnout_raw=-1,
        delta_hmn=1,
    ),
    # --- Fight the Ceiling (raw ceiling / ERN trajectory) ------------
    AppliedSkill(
        id="grad_school_prep",
        title="Graduate School Prep Track",
        rationale=(
            "An advanced degree is the most reliable way to raise "
            "the long-term earnings ceiling in this career."
        ),
        targets=["ceiling"],
        delta_ceiling_raw=2,
    ),
    AppliedSkill(
        id="professional_cert",
        title="Professional Certification",
        rationale=(
            "Industry-recognized credentials translate directly into "
            "higher pay bands within the same job title."
        ),
        targets=["ceiling"],
        delta_ern=1,
        delta_ceiling_raw=1,
    ),
    AppliedSkill(
        id="senior_mentorship",
        title="Senior Leadership Mentorship",
        rationale=(
            "Informal mentorship from someone 10-15 years ahead of "
            "you is the single best predictor of promotion velocity."
        ),
        targets=["ceiling"],
        delta_ceiling_raw=2,
    ),
    AppliedSkill(
        id="tech_leadership_course",
        title="Technical Leadership Course",
        rationale=(
            "Learning to manage people *and* systems unlocks the "
            "staff/principal/director ladder in most fields."
        ),
        targets=["ceiling", "ai"],
        delta_ern=1,
        delta_ceiling_raw=1,
    ),
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_skills_for_boss(
    boss_id: BossId,
    pool: list[AppliedSkill] | None = None,
    *,
    exclude_ids: set[str] | None = None,
) -> list[AppliedSkill]:
    """Return pool skills eligible for this boss, minus any already crafted.

    ``pool`` is the personalized list stored on ``build.skill_pool``.
    If ``None`` (e.g. in unit tests), falls back to ``FALLBACK_POOL``.
    The CLI passes ``exclude_ids={s.id for s in build.skills_crafted}``
    so a student never sees a skill twice across reroll loops.
    """
    effective_pool = pool if pool is not None else FALLBACK_POOL
    excluded = exclude_ids or set()
    return [
        skill
        for skill in effective_pool
        if boss_id in skill.targets and skill.id not in excluded
    ]


def format_impact(skill: AppliedSkill) -> str:
    """Human-readable delta summary, e.g. ``'RES+2, HMN+1'``."""
    parts: list[str] = []
    for label, value in (
        ("ERN", skill.delta_ern),
        ("ROI", skill.delta_roi),
        ("RES", skill.delta_res),
        ("GRW", skill.delta_grw),
        ("HMN", skill.delta_hmn),
    ):
        if value:
            parts.append(f"{label}{value:+d}")
    if skill.delta_burnout_raw:
        parts.append(f"burnout{skill.delta_burnout_raw:+d}")
    if skill.delta_ceiling_raw:
        parts.append(f"ceiling{skill.delta_ceiling_raw:+d}")
    return ", ".join(parts) or "—"


def _clamp_stat(value: int | None) -> int | None:
    if value is None:
        return None
    return max(1, min(10, value))


def apply_skills(
    career: CareerOutcome,
    skills: list[AppliedSkill],
) -> CareerOutcome:
    """Return a copy of ``career`` with every crafted skill stacked in.

    Stat deltas accumulate additively and clamp to [1, 10]. ``None``
    stats stay ``None`` (can't boost what isn't there). Burnout raw
    delta is clamped so it can't push the raw score below 1 or above
    10. Same for ceiling raw.
    """
    if not skills:
        return career

    sum_ern = sum(s.delta_ern for s in skills)
    sum_roi = sum(s.delta_roi for s in skills)
    sum_res = sum(s.delta_res for s in skills)
    sum_grw = sum(s.delta_grw for s in skills)
    sum_hmn = sum(s.delta_hmn for s in skills)
    sum_burnout = sum(s.delta_burnout_raw for s in skills)
    sum_ceiling = sum(s.delta_ceiling_raw for s in skills)

    stats = career.stats
    new_stats = PentagonStats(
        ern=_clamp_stat(stats.ern + sum_ern) if stats.ern is not None else None,
        roi=_clamp_stat(stats.roi + sum_roi) if stats.roi is not None else None,
        res=_clamp_stat(stats.res + sum_res) if stats.res is not None else None,
        grw=_clamp_stat(stats.grw + sum_grw) if stats.grw is not None else None,
        hmn=_clamp_stat(stats.hmn + sum_hmn) if stats.hmn is not None else None,
    )

    bosses = career.bosses
    new_burnout = bosses.burnout
    if new_burnout is not None and sum_burnout:
        new_burnout = max(1, min(10, new_burnout + sum_burnout))
    new_ceiling = bosses.ceiling
    if new_ceiling is not None and sum_ceiling:
        new_ceiling = max(1, min(10, new_ceiling + sum_ceiling))

    new_bosses = BossScores(
        ai=bosses.ai,
        loans=bosses.loans,
        market=bosses.market,
        burnout=new_burnout,
        ceiling=new_ceiling,
    )

    # model_copy(update=...) gives us a new CareerOutcome without
    # touching the original — important because the CLI re-applies the
    # full skill list on every reroll iteration.
    return career.model_copy(update={"stats": new_stats, "bosses": new_bosses})


# ---------------------------------------------------------------------------
# Personalized pool generation via Gemma
# ---------------------------------------------------------------------------

_POOL_SYSTEM = (
    "You generate boss-fight skill pools for a career planning RPG. "
    "Every skill must be grounded in the student's actual school, "
    "major, and career path — never generic. Each skill has a boss "
    "tag, a concrete 3-7 word title naming a specific course / "
    "program / activity, explicit stat deltas, and a 1-sentence "
    "rationale that references the student's context. You output ONE "
    "skill per line, pipe-delimited. No preamble, no numbering, no "
    "commentary, no headers, no markdown."
)


_BOSS_DESCRIPTIONS: dict[BossId, str] = {
    "ai": "Fight AI (tests RES + HMN — AI resilience stacked with uniquely-human work)",
    "loans": "Fight Student Loans (tests ROI — debt-to-earnings ratio)",
    "market": "Fight the Market (tests GRW — job market demand and growth)",
    "burnout": "Fight Burnout (tests burnout risk from O*NET work context)",
    "ceiling": "Fight the Ceiling (tests long-term earnings trajectory)",
}


_POOL_LINE = re.compile(
    r"^\s*(?P<boss>ai|loans|market|burnout|ceiling)\s*"
    r"\|\s*(?P<title>[^|]+?)\s*"
    r"\|\s*(?P<deltas>[^|]+?)\s*"
    r"\|\s*(?P<rationale>.+?)\s*$",
    re.IGNORECASE,
)


_DELTA_TOKEN = re.compile(
    r"(ern|roi|res|grw|hmn|burnout|ceiling)\s*([+\-])\s*(\d+)",
    re.IGNORECASE,
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "skill"


def _pool_prompt(
    career: CareerOutcome,
    rerollable_bosses: list[tuple[BossId, str]],
) -> str:
    stats = career.stats
    boss_block = "\n".join(
        f"- {_BOSS_DESCRIPTIONS[boss]} — {result.upper()}"
        for boss, result in rerollable_bosses
        if boss in _BOSS_DESCRIPTIONS
    )
    top_human = ", ".join(
        str(item.get("activity", ""))
        for item in career.top_human_activities[:4]
        if item.get("activity")
    )
    return (
        f"Student context:\n"
        f"- School: {career.institution_name}\n"
        f"- Major: {career.program_name} (CIP {career.cipcode})\n"
        f"- Primary career: {career.occupation_title} "
        f"(SOC {career.soc_code})\n"
        f"- Stats: ERN {stats.ern}, ROI {stats.roi}, RES {stats.res}, "
        f"GRW {stats.grw}, HMN {stats.hmn}\n"
        f"- Uniquely human activities in this career: "
        f"{top_human or '(none)'}\n\n"
        f"Lost or drawn boss fights — generate 3-5 skills for EACH:\n"
        f"{boss_block}\n\n"
        f"Output format (ONE skill per line, NO headers, NO blank "
        f"lines between skills):\n"
        f"boss|Specific course or activity title|DELTAS|Rationale "
        f"that names the student's school/major/career\n\n"
        f"Rules:\n"
        f"- boss = one of: ai, loans, market, burnout, ceiling\n"
        f"- DELTAS = comma-separated STAT+N pairs, e.g. RES+2,HMN+1\n"
        f"- Valid stats: ERN, ROI, RES, GRW, HMN, burnout, ceiling\n"
        f"- Use burnout-N (negative) to reduce burnout risk\n"
        f"- Use ceiling+N (positive) to raise the earnings ceiling\n"
        f"- Stat magnitudes should be +1 or +2 (rarely +3)\n"
        f"- Skills must name real, specific things the student at "
        f"{career.institution_name} could actually do\n"
        f"- NEVER propose changing schools or majors\n\n"
        f"Example line (for an Indiana University marketing student "
        f"losing Fight AI):\n"
        f"ai|Kelley Business Analytics minor|RES+2,HMN+1|The Kelley "
        f"analytics minor teaches marketers to direct AI tools, not "
        f"compete with them.\n\n"
        f"Now generate 3-5 skills per lost boss listed above."
    )


def _parse_pool(
    text: str,
    rerollable_bosses: list[BossId],
) -> list[AppliedSkill]:
    """Parse Gemma's pipe-delimited pool output into ``AppliedSkill``s.

    Silently drops malformed lines, skills with no parseable deltas,
    duplicates (by derived id), and skills tagged for a boss the
    student didn't lose or draw. The caller decides what to do with
    an empty or under-sized result — ``generate_pool`` pads from the
    fallback.
    """
    losing_set = set(rerollable_bosses)
    skills: list[AppliedSkill] = []
    seen_ids: set[str] = set()

    for line in text.splitlines():
        match = _POOL_LINE.match(line)
        if not match:
            continue
        boss_str = match.group("boss").lower()
        if boss_str not in losing_set:
            continue
        title = match.group("title").strip(" -•\"'")
        if not title:
            continue
        rationale = match.group("rationale").strip().strip("\"'")
        if not rationale:
            continue

        deltas = {
            "ern": 0,
            "roi": 0,
            "res": 0,
            "grw": 0,
            "hmn": 0,
            "burnout": 0,
            "ceiling": 0,
        }
        for token in _DELTA_TOKEN.finditer(match.group("deltas")):
            stat = token.group(1).lower()
            sign = 1 if token.group(2) == "+" else -1
            magnitude = int(token.group(3))
            deltas[stat] += sign * magnitude

        if not any(deltas.values()):
            continue

        skill_id = _slug(f"{boss_str}_{title}")
        if skill_id in seen_ids:
            continue
        seen_ids.add(skill_id)

        skills.append(
            AppliedSkill(
                id=skill_id,
                title=title,
                rationale=rationale,
                targets=[boss_str],  # type: ignore[list-item]
                delta_ern=deltas["ern"],
                delta_roi=deltas["roi"],
                delta_res=deltas["res"],
                delta_grw=deltas["grw"],
                delta_hmn=deltas["hmn"],
                delta_burnout_raw=deltas["burnout"],
                delta_ceiling_raw=deltas["ceiling"],
            )
        )
    return skills


def _pad_from_fallback(
    pool: list[AppliedSkill],
    rerollable_bosses: list[BossId],
    *,
    minimum_per_boss: int = 3,
) -> list[AppliedSkill]:
    """Ensure every rerollable boss has at least ``minimum_per_boss``
    skills.

    If Gemma under-produced for a specific boss (e.g. 2 ai-skills
    parsed, spec wants 3), tops it up from ``FALLBACK_POOL`` without
    introducing duplicates. Gemma's personalized skills always come
    first; fallback rides at the end of the list for that boss.
    """
    padded = list(pool)
    for boss in rerollable_bosses:
        existing = [s for s in padded if boss in s.targets]
        needed = minimum_per_boss - len(existing)
        if needed <= 0:
            continue
        existing_ids = {s.id for s in padded}
        extras = [
            s
            for s in FALLBACK_POOL
            if boss in s.targets and s.id not in existing_ids
        ][:needed]
        padded.extend(extras)
    return padded


def _rerollable_from(
    gauntlet: GauntletResult,
) -> list[tuple[BossId, str]]:
    rerollable: list[tuple[BossId, str]] = []
    seen: set[str] = set()
    for fight in gauntlet.fights:
        if fight.result in ("lose", "draw") and fight.boss not in seen:
            rerollable.append((fight.boss, fight.result))
            seen.add(fight.boss)
    return rerollable


def _finalize_pool(
    text: str, rerollable: list[tuple[BossId, str]]
) -> list[AppliedSkill]:
    boss_ids = [boss for boss, _ in rerollable]
    parsed = _parse_pool(text, boss_ids) if text else []
    if not parsed:
        logger.warning(
            "skill pool gen returned 0 parseable lines; "
            "using fallback pool for %d rerollable boss(es)",
            len(boss_ids),
        )
    return _pad_from_fallback(parsed, boss_ids)


def generate_pool(
    career: CareerOutcome,
    gauntlet: GauntletResult,
) -> list[AppliedSkill]:
    """Pre-compute a personalized reroll skill pool for this build.

    Called once at build time, after the gauntlet has scored, so we
    know exactly which bosses to generate pools for. Builds that win
    every fight skip the Gemma call entirely and return an empty list.

    Both LOSE and DRAW fights get pools — the reroll flow fires on
    both outcomes. The prompt includes the fight result so Gemma can
    calibrate skill magnitude (a draw may need a smaller nudge than
    a loss).

    The returned list is a flat ``list[AppliedSkill]`` where each
    skill's ``targets`` identifies the boss it applies to. The CLI
    reroll flow filters with ``get_skills_for_boss(boss, pool)``.
    """
    rerollable = _rerollable_from(gauntlet)
    if not rerollable:
        return []

    text = gemma_client.generate(
        system=_POOL_SYSTEM,
        user=_pool_prompt(career, rerollable),
        # 3-5 skills × up to 5 bosses = ~25 lines at ~30 tokens each.
        # Gemma preamble usually burns another 200-400. 2000 is the
        # safe ceiling.
        max_tokens=2000,
        temperature=0.5,
    )
    return _finalize_pool(text, rerollable)


async def generate_pool_async(
    career: CareerOutcome,
    gauntlet: GauntletResult,
) -> list[AppliedSkill]:
    """Async variant — short-circuits to ``[]`` when no fights are
    rerollable, otherwise fans out the single Gemma call via
    ``gemma_client.generate_async``.
    """
    rerollable = _rerollable_from(gauntlet)
    if not rerollable:
        return []

    text = await gemma_client.generate_async(
        system=_POOL_SYSTEM,
        user=_pool_prompt(career, rerollable),
        max_tokens=2000,
        temperature=0.5,
    )
    return _finalize_pool(text, rerollable)
