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
        "working_hard": "−2 effort shift",
        "working": "−1 effort shift",
        "balanced": "no shift",
        "focused": "+1 effort shift",
        "all_in": "+2 effort shift",
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

    # Cost-based ROI receipt (plan: why-are-we-still-jaunty-curry).
    # ROI reflects program cost vs. earnings and is NOT sensitive to
    # loan_pct. The Student Loans Boss is where financing enters the
    # picture — its own modeled_debt + financed_dte are surfaced here
    # so the student sees both angles in one receipt.
    cost_lines: list[str] = []
    school_label = career.institution_name or "Unknown school"
    if career.institution_control:
        school_label = f"{school_label} ({career.institution_control})"
    cost_lines.append(f"School: {school_label}")

    # Cost basis — prefer net price × 4; fall back to debt_median when
    # the Gold row had no institution-level cost data.
    basis = career.roi_cost_basis
    if basis == "cost_of_attendance" and career.net_price_annual is not None:
        four_year_cost = career.net_price_annual * 4
        cost_lines.append(
            f"Net price/yr: {_wage(career.net_price_annual)}"
        )
        if career.net_price_annual_reference is not None:
            cost_lines.append(
                f"Out-of-state adjustment: median in-state"
                f" {_wage(career.net_price_annual_reference)}/yr"
                f" + tuition gap →"
                f" {_wage(career.net_price_annual)}/yr"
            )
        if career.cost_of_attendance_annual is not None:
            cost_lines.append(
                f"COA/yr: {_wage(career.cost_of_attendance_annual)} (sticker)"
            )
        label = (
            "net price × 4, out-of-state adjusted"
            if career.net_price_annual_reference
            else "net price × 4"
        )
        cost_lines.append(
            f"4-year cost of attendance: {_wage(four_year_cost)} ({label})"
        )
    elif basis == "debt_median" and career.debt_median is not None:
        cost_lines.append(
            f"Cost basis: median graduate debt {_wage(career.debt_median)} "
            f"(institution-level cost data unavailable — approximation)"
        )
    else:
        cost_lines.append(
            "Cost basis: unavailable (no net_price_annual or debt_median on row)"
        )

    if career.earnings_1yr_median is not None:
        cost_lines.append(
            f"Earnings 1yr: {_wage(career.earnings_1yr_median)}"
        )
    if career.debt_to_earnings_annual is not None:
        cost_lines.append(
            f"ROI DTE (cost vs earnings): {career.debt_to_earnings_annual:.2f} "
            f"→ ROI {_stat(stats.roi)}/10"
        )

    # Student Loans Boss context — financed portion of the cost.
    if career.modeled_total_debt is not None:
        cost_lines.append(
            f"Loan coverage: {int(loan_pct * 100)}%  |  "
            f"Modeled debt at {int(loan_pct * 100)}%: "
            f"{_wage(career.modeled_total_debt)}"
        )
    if career.financed_dte is not None:
        cost_lines.append(
            f"Financed DTE (loans boss input): {career.financed_dte:.2f}"
        )
    if career.debt_median_reference is not None and basis == "cost_of_attendance":
        cost_lines.append(
            f"Median debt of program graduates: "
            f"{_wage(career.debt_median_reference)} (reference)"
        )

    if basis == "cost_of_attendance":
        cost_lines.append(
            "Sources: College Scorecard (Field of Study + Institution Level)"
        )
    else:
        cost_lines.append("Sources: College Scorecard (Field of Study)")

    lines.append(
        f"ROI {_stat(stats.roi)}/10 ← " + " | ".join(cost_lines)
    )

    # RES is now blended from stat_res (AI exposure resilience) + stat_hmn
    # (O*NET human-essential ratio). Three branches per pentagon-stat-reshape
    # §4 — both present, stat_hmn NULL, stat_res NULL (~1.05M rows in gold).
    # The AI-exposure provenance from the underlying stat_res source is
    # appended after the blend description so the receipt remains a complete
    # audit trail.
    method = career.composite_method
    composite_methods = {
        "three_signal",
        "two_signal_no_anthropic",
        "gemma_plus_anthropic",
        "observed_override",
    }
    if method in composite_methods:
        velocity = career.velocity_label or "unknown"
        ai_src_parts = [
            f"stat_res via Option B composite ({method}) — Gemma theoretical × "
            f"Karpathy baseline blended by adoption percentile",
            f"velocity={velocity}",
        ]
        if career.ai_adoption_share is not None:
            ai_src_parts.append(
                f"ai_adoption_share={career.ai_adoption_share:.4f}"
            )
        ai_src_parts.append(f"SOC {career.soc_code}")
        ai_exposure_src = "; ".join(ai_src_parts)
    elif method == "gemma_only":
        ai_exposure_src = (
            f"stat_res via Gemma task-level AI exposure only — no observed "
            f"adoption data (SOC {career.soc_code})"
        )
    elif method == "karpathy_only":
        ai_exposure_src = (
            f"stat_res via Karpathy AI exposure baseline — Gemma unavailable "
            f"(SOC {career.soc_code})"
        )
    elif career.scoring_model == "gemma-4":
        model_tag = career.model_tag or "gemma-4"
        ai_exposure_src = (
            f"stat_res via Gemma task-level AI exposure ({model_tag}, "
            f"AI-estimated) on O*NET tasks (SOC {career.soc_code})"
        )
    else:
        ai_exposure_src = (
            f"stat_res via Karpathy AI exposure + O*NET task analysis "
            f"(SOC {career.soc_code})"
        )

    raw_res = career.raw_stat_res
    raw_hmn = career.raw_stat_hmn
    if raw_res is not None and raw_hmn is not None:
        blend_desc = (
            f"blended from stat_res {raw_res} + stat_hmn {raw_hmn} "
            f"(50/50 mean, draft)"
        )
    elif raw_res is not None and raw_hmn is None:
        blend_desc = (
            "stat_res only (no O*NET task signal — stat_hmn unavailable "
            "for this SOC)"
        )
    elif raw_res is None and raw_hmn is not None:
        blend_desc = (
            "stat_hmn only (no AI exposure signal — stat_res unavailable "
            "for this SOC)"
        )
    else:
        blend_desc = "no resilience signal — both stat_res and stat_hmn unavailable"

    lines.append(
        f"RES {_stat(stats.res)}/10 ← {blend_desc} | {ai_exposure_src}"
    )

    grw_source = career.growth_category or "category unavailable"
    lines.append(
        f"GRW {_stat(stats.grw)}/10 ← BLS growth outlook: \"{grw_source}\" "
        f"(SOC {career.soc_code})"
    )

    # AURA — institution-level brand gravity. Sourced from
    # consumable.institution_aura.aura_score (one MCP lookup per build,
    # stamped on every CareerOutcome). Roughly 10% of student-reachable
    # unitids have no row → render explicit "—" instead of a numeric.
    if stats.aura is not None:
        basis_label = _humanize_basis(career.aura_score_basis)
        lines.append(
            f"AURA {stats.aura}/10 ← {basis_label} (institution-level)"
        )
    else:
        lines.append(
            "AURA — (no brand-gravity data for this school yet)"
        )

    return lines


_BASIS_HUMAN: dict[str, str] = {
    "three_term": "endowment + marketing + athletics",
    "two_term_finance_only": "endowment + marketing (no athletics signal)",
    "two_term_no_endowment": "marketing + athletics (no endowment signal)",
    "one_term_marketing_only": "marketing reach only",
}


def _humanize_basis(basis: str | None) -> str:
    """Convert raw aura_score_basis enum to receipt-friendly label.

    Raw codes (``three_term``, ``one_term_marketing_only``) are
    pipeline-internal taxonomy. Receipts are student-facing surfaces, so
    they get human-readable labels. Falls back to the raw code for any
    unmapped value (defensive — shouldn't fire on shipped data).
    """
    if basis is None:
        return "unknown basis"
    return _BASIS_HUMAN.get(basis, basis)


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
        f"RES {_stat(stats.res)}, GRW {_stat(stats.grw)}, "
        f"AURA {_stat(stats.aura)}",
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
        f"AURA {_stat(stats.aura)} | "
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
