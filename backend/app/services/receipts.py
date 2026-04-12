"""Inline provenance receipts for every CLI determination.

Each function takes the relevant model objects and returns a list of
compact, data-only lines suitable for a dim receipt box. No prose,
no narrative — raw values and source attribution.
"""

from __future__ import annotations

from app.models.career import (
    AppliedSkill,
    BossFightResult,
    Build,
    CareerOutcome,
    EffortLevel,
    GauntletResult,
)


def _wage(value: float | None) -> str:
    return f"${int(value):,}" if isinstance(value, (int, float)) else "N/A"


def _stat(value: int | None) -> str:
    return str(value) if isinstance(value, int) else "—"


# ---------------------------------------------------------------------------
# Stats receipt
# ---------------------------------------------------------------------------


def stats_receipt(
    career: CareerOutcome,
    effort: EffortLevel,
    loan_pct: float,
) -> list[str]:
    stats = career.stats
    effort_note = {
        "working": "−1 effort shift",
        "balanced": "no shift",
        "all_in": "+1 effort shift",
    }.get(effort, "")

    lines = []

    ern_parts = []
    if career.earnings_1yr_median is not None:
        ern_parts.append(f"Scorecard 1yr median: {_wage(career.earnings_1yr_median)}")
    if career.median_annual_wage is not None:
        ern_parts.append(f"BLS median wage: {_wage(career.median_annual_wage)}")
    if effort_note:
        ern_parts.append(f"effort: {effort} ({effort_note})")
    lines.append(
        f"ERN {_stat(stats.ern)}/10 ← "
        + (" | ".join(ern_parts) if ern_parts else "insufficient earnings data")
    )

    roi_parts = []
    if career.debt_to_earnings_annual is not None:
        raw_dte = career.debt_to_earnings_annual
        if loan_pct < 1.0:
            adj_dte = raw_dte * loan_pct
            roi_parts.append(
                f"DTE {raw_dte:.2f} × loan_pct {int(loan_pct * 100)}% = {adj_dte:.2f}"
            )
        else:
            roi_parts.append(f"DTE ratio: {raw_dte:.2f}")
    if career.debt_median is not None:
        roi_parts.append(f"median debt: {_wage(career.debt_median)}")
    lines.append(
        f"ROI {_stat(stats.roi)}/10 ← "
        + (" | ".join(roi_parts) if roi_parts else "DTE data unavailable")
    )

    lines.append(
        f"RES {_stat(stats.res)}/10 ← "
        f"Karpathy AI exposure + O*NET task analysis (SOC {career.soc_code})"
    )

    grw_source = career.growth_category or "category unavailable"
    lines.append(
        f"GRW {_stat(stats.grw)}/10 ← BLS growth outlook: \"{grw_source}\" "
        f"(SOC {career.soc_code})"
    )

    human_count = len(career.top_human_activities)
    human_names = ", ".join(
        str(item.get("activity", ""))
        for item in career.top_human_activities[:3]
        if item.get("activity")
    )
    hmn_detail = (
        f"{human_count} uniquely-human tasks"
        + (f": {human_names}" if human_names else "")
    )
    lines.append(
        f"HMN {_stat(stats.hmn)}/10 ← O*NET human activity ratio — {hmn_detail}"
    )

    return lines


# ---------------------------------------------------------------------------
# Boss fight receipt (single fight)
# ---------------------------------------------------------------------------


def fight_receipt(fight: BossFightResult) -> str:
    if fight.result == "unknown":
        return "Tested: data unavailable | Result: UNKNOWN"
    return (
        f"Tested: {fight.reason} | "
        f"WIN ≥ {fight.threshold_win}, DRAW ≥ {fight.threshold_draw} | "
        f"Result: {fight.result.upper()}"
    )


# ---------------------------------------------------------------------------
# Career tiering receipt
# ---------------------------------------------------------------------------


def tiering_receipt(
    career: CareerOutcome,
    outcome_count: int,
) -> list[str]:
    lines = []
    cip_display = career.cipcode
    if career.substitution_applied:
        lines.append(
            f"CIP {career.reported_cipcode} → substituted to "
            f"{career.substituted_cipcode} (intent substitution)"
        )
    else:
        lines.append(
            f"CIP {cip_display} ({career.program_name}) → "
            f"{outcome_count} SOC codes via CIP-SOC crosswalk"
        )
    if career.overall_confidence:
        lines.append(f"Crosswalk confidence: {career.overall_confidence}")
    lines.append("Tier assignment: Gemma grouped by school+major+education context")
    return lines


# ---------------------------------------------------------------------------
# Skill recs receipt
# ---------------------------------------------------------------------------


def skill_recs_receipt(
    career: CareerOutcome,
    gauntlet: GauntletResult,
) -> list[str]:
    stats = career.stats
    lost = [f.label for f in gauntlet.fights if f.result == "lose"]
    drawn = [f.label for f in gauntlet.fights if f.result == "draw"]
    weak = ", ".join(lost) if lost else "none"
    draw_str = ", ".join(drawn) if drawn else "none"

    lines = [
        f"Stats sent: ERN {_stat(stats.ern)}, ROI {_stat(stats.roi)}, "
        f"RES {_stat(stats.res)}, GRW {_stat(stats.grw)}, HMN {_stat(stats.hmn)}",
        f"Lost: {weak} | Drawn: {draw_str}",
    ]
    human_names = [
        str(item.get("activity", ""))
        for item in career.top_human_activities[:4]
        if item.get("activity")
    ]
    if human_names:
        lines.append(f"O*NET human tasks: {', '.join(human_names)}")
    return lines


# ---------------------------------------------------------------------------
# Reroll receipt
# ---------------------------------------------------------------------------


def reroll_receipt(
    fight: BossFightResult,
    picks: list[AppliedSkill],
    original_score: int | None,
    original_result: str,
) -> list[str]:
    skill_desc = ", ".join(
        f"\"{s.title}\" ({_skill_delta_str(s)})" for s in picks
    )
    lines = [
        f"Before: score {_stat(original_score)} → {original_result.upper()} | "
        f"Equipped: {skill_desc}",
        f"After: score {_stat(fight.raw_score)} → {fight.result.upper()} | "
        f"Thresholds: WIN ≥ {fight.threshold_win}, DRAW ≥ {fight.threshold_draw}",
    ]
    return lines


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
            parts.append(f"{label}{val:+d}")
    if skill.delta_burnout_raw:
        parts.append(f"burnout{skill.delta_burnout_raw:+d}")
    if skill.delta_ceiling_raw:
        parts.append(f"ceiling{skill.delta_ceiling_raw:+d}")
    return ", ".join(parts) or "—"


# ---------------------------------------------------------------------------
# Next steps receipt
# ---------------------------------------------------------------------------


def next_steps_receipt(build: Build) -> list[str]:
    career = build.career
    stats = career.stats
    gauntlet = build.gauntlet
    lines = [
        f"Gemma received: school={career.institution_name}, "
        f"major={career.program_name}, career={career.occupation_title} "
        f"({career.soc_code})",
        f"Stats: ERN {_stat(stats.ern)}, ROI {_stat(stats.roi)}, "
        f"RES {_stat(stats.res)}, GRW {_stat(stats.grw)}, "
        f"HMN {_stat(stats.hmn)} | "
        f"Gauntlet: {gauntlet.wins}W/{gauntlet.losses}L/{gauntlet.draws}D",
        f"Skills crafted: {len(build.skills_crafted)} | "
        f"Skill recs offered: {len(build.skill_recs)}",
    ]
    rerolled = [f for f in gauntlet.fights if f.rerolled]
    if rerolled:
        flips = ", ".join(
            f"{f.label}: {(f.original_result or '?').upper()}→{f.result.upper()}"
            for f in rerolled
        )
        lines.append(f"Rerolls: {flips}")
    return lines
