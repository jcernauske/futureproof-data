"""Compute career outcome pentagon stats for a school+major.

Thin deterministic wrapper around the MCP server's
``get_career_paths`` handler. The handler already performs CIP intent
substitution and returns per-career rows with pre-computed stats and
boss scores. This module:

1. Maps the raw MCP rows into ``CareerOutcome`` Pydantic models.
2. Applies the effort-level adjustment to ERN/ROI (deterministic
   shift; the raw data only carries median earnings so effort acts
   as a calibration nudge, not a recomputation).
3. Sorts by ``stats_available_count`` so the most data-complete
   outcome is the CLI's headline career.
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

# Residency adjustment moved to the MCP layer per spec
# roi-net-lifetime-value followup ("Explain this to me" cost-mismatch fix).
# Import the shared helpers so both layers compute the same residency-aware
# cost without drift.
from mcp_server.residency import (  # type: ignore[import-not-found]
    is_public_control as _shared_is_public_control,
)
from mcp_server.residency import (
    published_cost_4yr as _shared_published_cost_4yr,
)

from app.models.career import (
    BossScores,
    CareerOutcome,
    EffortLevel,
    PentagonStats,
)
from app.services import mcp_client
from app.services._coercion import as_int
from app.services.loan_math import amortize, repayment_term_months

logger = logging.getLogger(__name__)


def _round_half_up(value: float) -> int:
    """Half-up rounding (NOT banker's rounding).

    Python's built-in ``round()`` is half-even (banker's), which would
    give different numbers than the spec implies. We use Decimal.quantize
    so 0.5 always rounds away from zero.
    """
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _blend_res(stat_res: int | None, stat_hmn: int | None) -> int | None:
    """DRAFT 50/50 mean of the two AI-resilience signals.

    Pending EDA. The two underlying scores measure related but distinct
    things — ``stat_res`` is adoption-level resilience (Karpathy +
    Anthropic + Gemma), ``stat_hmn`` is task-level human-essential ratio
    (O*NET). EDA needs to confirm the correlation and pick weights;
    until then a simple mean ships (see pentagon-stat-reshape.md §2
    Decision 3).

    Partial-null rule: if one input is None, return the other; if both
    None, return None. Never fabricates a value.

    NOTE: this rounded value is the DISPLAY value. Fight AI scores from
    the raw inputs (Decision 4 revised in pentagon-stat-reshape.md) so
    this rounding never reaches boss-fight outcomes.
    """
    if stat_res is None and stat_hmn is None:
        return None
    if stat_res is None:
        return stat_hmn
    if stat_hmn is None:
        return stat_res
    return _round_half_up((stat_res + stat_hmn) / 2)


def _fetch_aura(unitid: int) -> tuple[int | None, str | None, str | None]:
    """Return ``(aura_score, aura_score_basis, aura_score_version)``.

    All three are None when the institution has no row in
    ``consumable.institution_aura``, or when the row has NULL
    ``aura_score`` (no marketing_ratio signal — see §6 of
    full-pipeline-eada.md).

    AURA is supplementary to the build — it surfaces on the 5th
    pentagon vertex but does not drive any boss fight scoring. A
    pyiceberg flake or transient MCP failure on this lookup must NOT
    cascade to a 500 on /outcomes; we log and degrade to "no AURA
    available for this build" (the pentagon's open-ring missing-data
    treatment handles the rendering side cleanly).
    """
    try:
        result = mcp_client.call("get_institution_aura", {"unitid": unitid})
    except Exception as exc:  # noqa: BLE001 — supplementary lookup, must fail soft
        logger.warning(
            "get_institution_aura failed for unitid=%s; degrading to no-aura: %s",
            unitid,
            exc,
        )
        return None, None, None
    row = result.get("data")
    if not row:
        return None, None, None
    return (
        as_int(row.get("aura_score")),
        row.get("aura_score_basis"),
        row.get("aura_score_version"),
    )

# Effort adjustment: shift applied to ERN in score points. ROI is
# intentionally excluded — effort reflects earning potential while in
# school, not debt load. A student studying harder doesn't reduce the
# tuition bill; ROI is a property of the program's cost vs. earnings and
# is independent of the loan_pct knob (which only drives the Student
# Loans Boss). Plan: ~/.claude/plans/why-are-we-still-jaunty-curry.md
EFFORT_SHIFT: dict[str, int] = {
    "working_hard": -2,
    "working": -1,
    "balanced": 0,
    "focused": +1,
    "all_in": +2,
}


def _is_public_control(institution_control: str | None) -> bool:
    """Backwards-compat wrapper for `mcp_server.residency.is_public_control`.

    The canonical implementation now lives in the MCP layer (per spec
    roi-net-lifetime-value followup). This shim keeps existing backend
    callers working during the transition.
    """
    result: bool = _shared_is_public_control(institution_control)
    return result


def _clamp_stat(value: int | None) -> int | None:
    if value is None:
        return None
    return max(1, min(10, value))


def _apply_effort(stats: PentagonStats, effort: EffortLevel) -> PentagonStats:
    shift = EFFORT_SHIFT.get(effort, 0)
    if shift == 0:
        return stats
    new_ern = _clamp_stat(None if stats.ern is None else stats.ern + shift)
    return PentagonStats(
        ern=new_ern,
        roi=stats.roi,
        res=stats.res,
        grw=stats.grw,
        aura=stats.aura,
    )


# Closed-form geometric-series multiplier for 15 years at 3% growth:
#     ((1 + WAGE_GROWTH_RATE)^ROI_WINDOW_YEARS - 1) / WAGE_GROWTH_RATE
# Equivalent to summing earnings × 1.03^(t-1) for t in [1..15].
# See docs/specs/roi-net-lifetime-value.md §2 Decision #10.
WAGE_GROWTH_RATE: float = 0.03
ROI_WINDOW_YEARS: int = 15
LIFETIME_EARNINGS_MULTIPLIER: float = (
    (1 + WAGE_GROWTH_RATE) ** ROI_WINDOW_YEARS - 1
) / WAGE_GROWTH_RATE


def _derive_roi(
    *,
    published_cost_4yr: float | None,
    earnings_1yr_median: float | None,
    raw_stat_roi: int | None,
) -> int | None:
    """Compute stat_roi as a 15-year payback multiplier mapped to 1-10.

    ROI is financing-agnostic — ``loan_pct`` is NOT an argument. The
    formula is:

        lifetime_earnings_15yr = earnings_1yr_median × 18.5989
        roi_raw = lifetime_earnings_15yr / published_cost_4yr
        stat_roi = compute_stat_roi_from_multiplier(roi_raw)

    where ``published_cost_4yr`` is the residency-aware sticker per
    ``_published_cost_4yr``. Falls back to ``raw_stat_roi`` (from the
    Gold row, in-state baseline) when residency-aware inputs are
    missing — see spec roi-net-lifetime-value.md Decision #11.
    """
    if published_cost_4yr is None or earnings_1yr_median is None:
        return raw_stat_roi
    if published_cost_4yr <= 0 or earnings_1yr_median <= 0:
        return raw_stat_roi
    from gold.futureproof_engine import (  # type: ignore[import-not-found]
        compute_stat_roi_from_multiplier,
    )
    lifetime_earnings_15yr = (
        float(earnings_1yr_median) * LIFETIME_EARNINGS_MULTIPLIER
    )
    roi_raw = lifetime_earnings_15yr / float(published_cost_4yr)
    score: int | None = compute_stat_roi_from_multiplier(roi_raw)
    return score


# Total-interest-paid as multiple of first-year salary → boss power (1-10).
# Calibrated against the OBBBA Tiered Standard term tiers — interest burden
# scales with both principal (because longer-tier loans accrue more) and
# the cost-vs-earnings spread. See spec roi-net-lifetime-value.md §4.
_INTEREST_BURDEN_THRESHOLDS: list[tuple[float, int]] = [
    (0.05, 1),
    (0.10, 2),
    (0.20, 3),
    (0.30, 4),
    (0.45, 5),
    (0.60, 6),
    (0.75, 7),
    (0.90, 8),
    (1.00, 9),
]


def _interest_burden_to_score(burden: float) -> int:
    """Map total_interest_paid / first_year_salary to a 1-10 boss score."""
    if burden <= 0:
        return 1
    for upper_bound, score in _INTEREST_BURDEN_THRESHOLDS:
        if burden < upper_bound:
            return score
    return 10


def _derive_loans_boss(
    *,
    published_cost_4yr: float | None,
    earnings_1yr_median: float | None,
    loan_pct: float,
) -> tuple[
    int | None, float | None, float | None, float | None, float | None, int | None
]:
    """Compute Student Loans Boss + amortization byproducts.

    Returns
    ``(boss_loans_score, modeled_total_debt, financed_dte,
       total_interest_paid, monthly_payment, term_months)``.

    Unlike ROI (financing-agnostic, see ``_derive_roi``), the Student
    Loans Boss IS financing-aware. Power scales with **total interest
    paid** under the OBBBA Tiered Standard term:

        modeled_total_debt   = published_cost_4yr × loan_pct
        (term, monthly, interest) = amortize(modeled_total_debt)
        interest_burden      = total_interest_paid / earnings_1yr_median
        boss_loans_score     = _interest_burden_to_score(interest_burden)

    Special cases:
    - loan_pct <= 0.0:  no debt, boss is auto-win (score 1).
    - published_cost_4yr is None: caller substitutes the row value.
    - earnings missing or zero: can't form an interest burden — caller
      handles fallback.
    """
    # No-loans branch — no debt, trivially win the loans boss.
    if loan_pct <= 0.0:
        return 1, 0.0, 0.0, 0.0, 0.0, 0

    if published_cost_4yr is None:
        return None, None, None, None, None, None

    modeled_debt = float(published_cost_4yr) * float(loan_pct)
    term = repayment_term_months(modeled_debt)
    monthly, _total_repayment, total_interest = amortize(
        modeled_debt, term_months=term
    )

    if earnings_1yr_median is None or float(earnings_1yr_median) <= 0:
        # We have the loan math but can't form a financed DTE or burden.
        return None, modeled_debt, None, total_interest, monthly, term

    earnings = float(earnings_1yr_median)
    financed_dte = modeled_debt / earnings
    interest_burden = total_interest / earnings
    boss_loans = _interest_burden_to_score(interest_burden)
    return boss_loans, modeled_debt, financed_dte, total_interest, monthly, term


def _adjust_net_price_for_residency(
    *,
    net_price_annual: float | None,
    tuition_in_state: float | None,
    tuition_out_of_state: float | None,
    institution_control: str | None,
    home_state: str | None,
    school_state: str | None,
) -> float | None:
    """DEPRECATED — kept for back-compat callers only.

    The cost basis for ROI and the Student Loans Boss has switched to
    ``_published_cost_4yr`` (full sticker, residency-aware) per the
    2026-05-02 cost-anchor change. This helper is retained because some
    legacy display paths still cite "average net price" as a reference
    (i.e. "for context, the average aided student paid $X"). New cost
    work should use ``_published_cost_4yr``, not this.
    """
    if net_price_annual is None:
        return None
    if home_state is None or school_state is None:
        return net_price_annual
    if not _is_public_control(institution_control):
        return net_price_annual
    if home_state == school_state:
        return net_price_annual
    if tuition_in_state is None or tuition_out_of_state is None:
        return net_price_annual
    gap = tuition_out_of_state - tuition_in_state
    if gap <= 0:
        return net_price_annual
    return net_price_annual + gap


def _published_cost_4yr(
    *,
    cost_of_attendance_annual: float | None,
    tuition_in_state: float | None,
    tuition_out_of_state: float | None,
    institution_control: str | None,
    home_state: str | None,
    school_state: str | None,
) -> float | None:
    """Backwards-compat wrapper for `mcp_server.residency.published_cost_4yr`.

    The canonical implementation now lives in the MCP layer (per spec
    roi-net-lifetime-value followup, "Explain this to me" cost-mismatch
    fix). Single source of truth — both the MCP server and the backend
    `_row_to_outcome` / `apply_published_cost_override` callers compute
    the same residency-aware sticker without drift. Kept under this name
    so existing imports in tests and call-sites don't churn.
    """
    result: float | None = _shared_published_cost_4yr(
        cost_of_attendance_annual=cost_of_attendance_annual,
        tuition_in_state=tuition_in_state,
        tuition_out_of_state=tuition_out_of_state,
        institution_control=institution_control,
        home_state=home_state,
        school_state=school_state,
    )
    return result


def _row_to_outcome(
    row: dict[str, Any],
    effort: EffortLevel,
    loan_pct: float,
    *,
    substitution_applied: bool,
    reported_cipcode: str | None,
    substituted_cipcode: str | None,
    data_caveat: dict[str, Any] | None,
    home_state: str | None = None,
    aura_score: int | None = None,
    aura_score_basis: str | None = None,
    aura_score_version: str | None = None,
) -> CareerOutcome:
    raw_stat_roi = as_int(row.get("stat_roi"))
    raw_boss_loans = as_int(row.get("boss_loans_score"))
    dte = row.get("debt_to_earnings_annual")
    net_price_annual_raw = row.get("net_price_annual")
    debt_median_raw = row.get("debt_median")
    earnings_raw = row.get("earnings_1yr_median")

    # Coerce numeric inputs once so the cost-of-attendance branch can
    # pass clean floats through to ``compute_stat_roi``.
    def _maybe_float(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    net_price_f = _maybe_float(net_price_annual_raw)
    debt_median_f = _maybe_float(debt_median_raw)
    earnings_f = _maybe_float(earnings_raw)
    dte_f = _maybe_float(dte)

    coa_f = _maybe_float(row.get("cost_of_attendance_annual"))
    tuition_in_f = _maybe_float(row.get("tuition_in_state"))
    tuition_out_f = _maybe_float(row.get("tuition_out_of_state"))
    inst_control = row.get("institution_control")
    school_state = row.get("state_abbr")

    # Residency-aware 4-year published cost. This is the single cost
    # anchor for both ROI (financing-agnostic) and the Student Loans
    # Boss (financing-aware). Replaces the prior net-price-based path
    # per the 2026-05-02 cost-anchor change.
    published_cost_4yr = _published_cost_4yr(
        cost_of_attendance_annual=coa_f,
        tuition_in_state=tuition_in_f,
        tuition_out_of_state=tuition_out_f,
        institution_control=inst_control,
        home_state=home_state,
        school_state=school_state,
    )

    # Net-price residency adjustment retained for the FinancesCard
    # "for context" display only — does NOT drive ROI or the loans
    # boss anymore.
    adjusted_net_price = _adjust_net_price_for_residency(
        net_price_annual=net_price_f,
        tuition_in_state=tuition_in_f,
        tuition_out_of_state=tuition_out_f,
        institution_control=inst_control,
        home_state=home_state,
        school_state=school_state,
    )

    # Legacy DTE (deprecated) — kept on the model for one release cycle.
    # Computed from residency-aware cost when available; falls through to
    # the Gold-precomputed value otherwise.
    roi_dte: float | None = None
    if (
        published_cost_4yr is not None
        and earnings_f is not None
        and earnings_f > 0
    ):
        roi_dte = published_cost_4yr / earnings_f

    # ROI is loan_pct-independent — it reflects program cost vs earnings.
    # The 15-year payback multiplier (= cumulative earnings ÷ sticker cost)
    # is computed from raw inputs inside _derive_roi; falls back to the
    # Gold-precomputed in-state-baseline ``raw_stat_roi`` when residency-
    # aware inputs are missing (spec roi-net-lifetime-value Decision #11).
    adj_stat_roi = _derive_roi(
        published_cost_4yr=published_cost_4yr,
        earnings_1yr_median=earnings_f,
        raw_stat_roi=raw_stat_roi,
    )
    # Student Loans Boss IS loan_pct-aware — it reflects financing choices.
    (
        boss_loans_derived,
        modeled_total_debt,
        financed_dte,
        total_interest_paid,
        monthly_payment,
        term_months,
    ) = _derive_loans_boss(
        published_cost_4yr=published_cost_4yr,
        earnings_1yr_median=earnings_f,
        loan_pct=loan_pct,
    )
    # If the helper couldn't derive a boss (no cost inputs on the row),
    # fall back to the Gold-derived baseline so the gauntlet still has
    # a score to score.
    adj_boss_loans = (
        boss_loans_derived
        if boss_loans_derived is not None
        else raw_boss_loans
    )

    raw_stat_res = as_int(row.get("stat_res"))
    raw_stat_hmn = as_int(row.get("stat_hmn"))
    blended_res = _blend_res(raw_stat_res, raw_stat_hmn)
    stats = PentagonStats(
        ern=as_int(row.get("stat_ern")),
        roi=adj_stat_roi,
        res=blended_res,
        grw=as_int(row.get("stat_grw")),
        aura=aura_score,
    )
    stats = _apply_effort(stats, effort)

    bosses = BossScores(
        ai=as_int(row.get("boss_ai_score")),
        loans=adj_boss_loans,
        market=as_int(row.get("boss_market_score")),
        burnout=as_int(row.get("boss_burnout_score")),
        ceiling=as_int(row.get("boss_ceiling_score")),
    )

    def _list_field(name: str) -> list[dict[str, object]]:
        value = row.get(name)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        return []

    # ``debt_median_reference`` is a clearer-named alias surfaced
    # alongside the legacy ``debt_median`` so receipts and narrative
    # prompts can refer to "median debt of past graduates" without
    # confusing it with the student's modeled debt.
    debt_median_reference = debt_median_f

    displayed_dte = roi_dte if roi_dte is not None else dte_f
    displayed_roi_basis: str | None
    if published_cost_4yr is not None:
        displayed_roi_basis = "cost_of_attendance"
    elif row.get("roi_cost_basis") in ("cost_of_attendance", "debt_median", "none"):
        displayed_roi_basis = row.get("roi_cost_basis")
    else:
        displayed_roi_basis = "none"

    return CareerOutcome(
        unitid=int(row["unitid"]),
        institution_name=str(row.get("institution_name") or ""),
        cipcode=str(row["cipcode"]),
        program_name=str(row.get("program_name") or ""),
        soc_code=str(row["soc_code"]),
        occupation_title=str(row.get("occupation_title") or ""),
        soc_major_group_name=row.get("soc_major_group_name"),
        median_annual_wage=row.get("median_annual_wage"),
        wage_p10=row.get("wage_p10"),
        wage_p25=row.get("wage_p25"),
        wage_p75=row.get("wage_p75"),
        wage_p90=row.get("wage_p90"),
        earnings_1yr_median=earnings_raw,
        earnings_1yr_p25=row.get("earnings_1yr_p25"),
        earnings_1yr_p75=row.get("earnings_1yr_p75"),
        debt_median=debt_median_raw,
        debt_p25=row.get("debt_p25"),
        debt_p75=row.get("debt_p75"),
        debt_to_earnings_annual=displayed_dte,
        education_level_name=row.get("education_level_name"),
        growth_category=row.get("growth_category"),
        work_experience_code=row.get("work_experience_code"),
        net_price_annual=(
            adjusted_net_price
            if adjusted_net_price is not None
            else net_price_annual_raw
        ),
        cost_of_attendance_annual=row.get("cost_of_attendance_annual"),
        published_cost_4yr=published_cost_4yr,
        modeled_total_debt=modeled_total_debt,
        total_interest_paid=total_interest_paid,
        monthly_payment=monthly_payment,
        term_months=term_months,
        debt_median_reference=debt_median_reference,
        institution_control=inst_control,
        state_abbr=school_state,
        net_price_annual_reference=(
            net_price_f
            if adjusted_net_price != net_price_f
            else None
        ),
        tuition_in_state=row.get("tuition_in_state"),
        tuition_out_of_state=row.get("tuition_out_of_state"),
        room_board_on_campus=row.get("room_board_on_campus"),
        stats=stats,
        bosses=bosses,
        raw_stat_res=raw_stat_res,
        raw_stat_hmn=raw_stat_hmn,
        aura_score_basis=aura_score_basis,
        aura_score_version=aura_score_version,
        scoring_model=row.get("scoring_model"),
        model_tag=row.get("model_tag"),
        karpathy_score=as_int(row.get("karpathy_score")),
        task_breakdown_automatable=_list_field("task_breakdown_automatable"),
        task_breakdown_human=_list_field("task_breakdown_human"),
        top_5_activities=_list_field("top_5_activities"),
        top_human_activities=_list_field("top_human_activities"),
        burnout_drivers=_list_field("burnout_drivers"),
        stats_available_count=as_int(row.get("stats_available_count")),
        overall_confidence=row.get("overall_confidence"),
        substitution_applied=substitution_applied,
        reported_cipcode=reported_cipcode,
        substituted_cipcode=substituted_cipcode,
        data_caveat=data_caveat,
        loan_pct=loan_pct,
        # Option B composite provenance (S4 v4). MCP threads these through
        # from consumable.ai_exposure via consumable.program_career_paths.
        # Pre-v4 rows have them missing from `row`, so the .get() calls
        # default to None and the downstream receipt / narrative code
        # falls back to legacy wording.
        ai_adoption_share=row.get("ai_adoption_share"),
        adoption_percentile=row.get("adoption_percentile"),
        velocity_label=row.get("velocity_label"),
        composite_method=row.get("composite_method"),
        # Cost-based ROI provenance. `roi_cost_basis` comes through from
        # consumable.career_outcomes via consumable.program_career_paths
        # (Gold transformer stamps it based on which numerator was used
        # when computing DTE). `financed_dte` is computed right here in
        # _derive_loans_boss — it's the loan_pct-aware ratio that drives
        # the Student Loans Boss, distinct from debt_to_earnings_annual
        # which is the financing-agnostic cost-vs-earnings ratio.
        roi_cost_basis=displayed_roi_basis,
        financed_dte=financed_dte,
        match_quality=row.get("match_quality"),
    )


def recompute_for_sliders(
    career: CareerOutcome,
    original_effort: EffortLevel,
    new_effort: EffortLevel,
    new_loan_pct: float,
) -> CareerOutcome:
    """Recompute stats and boss scores for new slider values.

    Pure arithmetic — no DB query, no Gemma call. Used by the
    ``/rescore`` endpoint to give instant feedback when the student
    adjusts effort or loan percentage on the results page.
    """
    old_shift = EFFORT_SHIFT.get(original_effort, 0)
    new_shift = EFFORT_SHIFT.get(new_effort, 0)

    if career.stats.ern is not None:
        base_ern = career.stats.ern - old_shift
        new_ern = _clamp_stat(base_ern + new_shift)
    else:
        new_ern = career.stats.ern

    (
        boss_loans,
        modeled_debt,
        financed_dte,
        total_interest,
        monthly,
        term,
    ) = _derive_loans_boss(
        published_cost_4yr=career.published_cost_4yr,
        earnings_1yr_median=career.earnings_1yr_median,
        loan_pct=new_loan_pct,
    )

    return career.model_copy(
        update={
            "stats": PentagonStats(
                ern=new_ern,
                roi=career.stats.roi,
                res=career.stats.res,
                grw=career.stats.grw,
                aura=career.stats.aura,
            ),
            "bosses": BossScores(
                ai=career.bosses.ai,
                loans=boss_loans if boss_loans is not None else career.bosses.loans,
                market=career.bosses.market,
                burnout=career.bosses.burnout,
                ceiling=career.bosses.ceiling,
            ),
            "loan_pct": new_loan_pct,
            "modeled_total_debt": (
                modeled_debt
                if modeled_debt is not None
                else career.modeled_total_debt
            ),
            "financed_dte": financed_dte,
            "total_interest_paid": (
                total_interest
                if total_interest is not None
                else career.total_interest_paid
            ),
            "monthly_payment": (
                monthly if monthly is not None else career.monthly_payment
            ),
            "term_months": term if term is not None else career.term_months,
        },
    )


def apply_published_cost_override(
    career: CareerOutcome,
    published_cost_4yr: float | None,
    *,
    loan_pct: float,
) -> CareerOutcome:
    """Force a career outcome onto a caller-supplied published 4-year cost.

    The Set Your Course screen already computes the residency-aware sticker
    total shown to the student. When that value is supplied during build
    creation, preserve it as the single cost anchor for /my-build and Gemma.
    """
    if published_cost_4yr is None or published_cost_4yr <= 0:
        return career

    cost = float(published_cost_4yr)
    earnings = (
        float(career.earnings_1yr_median)
        if career.earnings_1yr_median is not None
        else None
    )
    dte = cost / earnings if earnings and earnings > 0 else None
    roi = _derive_roi(
        published_cost_4yr=cost,
        earnings_1yr_median=earnings,
        raw_stat_roi=career.stats.roi,
    )
    (
        boss_loans,
        modeled_debt,
        financed_dte,
        total_interest,
        monthly,
        term,
    ) = _derive_loans_boss(
        published_cost_4yr=cost,
        earnings_1yr_median=earnings,
        loan_pct=loan_pct,
    )

    return career.model_copy(
        update={
            "published_cost_4yr": cost,
            "debt_to_earnings_annual": dte,
            "modeled_total_debt": modeled_debt,
            "roi_cost_basis": "cost_of_attendance",
            "financed_dte": financed_dte,
            "loan_pct": loan_pct,
            "total_interest_paid": (
                total_interest
                if total_interest is not None
                else career.total_interest_paid
            ),
            "monthly_payment": (
                monthly if monthly is not None else career.monthly_payment
            ),
            "term_months": term if term is not None else career.term_months,
            "stats": PentagonStats(
                ern=career.stats.ern,
                roi=roi,
                res=career.stats.res,
                grw=career.stats.grw,
                aura=career.stats.aura,
            ),
            "bosses": BossScores(
                ai=career.bosses.ai,
                loans=boss_loans if boss_loans is not None else career.bosses.loans,
                market=career.bosses.market,
                burnout=career.bosses.burnout,
                ceiling=career.bosses.ceiling,
            ),
        },
    )


def compute_pentagon(
    *,
    unitid: int,
    cipcode: str,
    student_major: str | None,
    student_cip: str | None = None,
    effort: EffortLevel = "balanced",
    loan_pct: float = 1.0,
    intent_keywords: list[str] | None = None,
    home_state: str | None = None,
) -> list[CareerOutcome]:
    """Return every career outcome for a school+major combo.

    ``loan_pct`` (0.0-1.0) scales the student's actual debt load before
    ROI/loans-boss are derived: 0.0 = no loans (ROI pins at 10), 1.0 =
    full published debt. Values in between reduce the raw DTE
    proportionally. The same value is passed down to the MCP handler so
    the CIP-substitution path can apply it at the source.

    Raises ``ValueError`` if the MCP handler returns no rows — the
    caller is expected to handle that (either retry with a different
    cipcode or report "program has no crosswalk coverage"). The CLI
    treats the first element of the returned list as the headline
    career since rows come back sorted by ``stats_available_count``.
    """
    loan_pct = max(0.0, min(1.0, float(loan_pct)))
    args: dict[str, Any] = {
        "unitid": unitid,
        "cipcode": cipcode,
        "loan_pct": loan_pct,
    }
    if student_major:
        args["student_major"] = student_major
    if student_cip:
        args["student_cip"] = student_cip
    if intent_keywords:
        args["intent_keywords"] = intent_keywords

    result = mcp_client.call("get_career_paths", args)
    rows = result.get("data") or []
    if not rows:
        message = result.get("message") or "No career paths found."
        raise ValueError(message)

    substitution_applied = bool(result.get("substitution_applied"))
    reported_cipcode = result.get("reported_cipcode") or cipcode
    substituted_cipcode = result.get("substituted_cipcode")
    data_caveat = result.get("data_caveat") if substitution_applied else None

    # AURA is institution-level — one MCP lookup per build, value stamped
    # onto every CareerOutcome row. CIP substitution does NOT change unitid
    # so this lookup also doesn't change under substitution (Decision 6).
    aura_score, aura_score_basis, aura_score_version = _fetch_aura(unitid)

    outcomes = [
        _row_to_outcome(
            row,
            effort,
            loan_pct,
            substitution_applied=substitution_applied,
            reported_cipcode=reported_cipcode,
            substituted_cipcode=substituted_cipcode,
            data_caveat=data_caveat,
            home_state=home_state,
            aura_score=aura_score,
            aura_score_basis=aura_score_basis,
            aura_score_version=aura_score_version,
        )
        for row in rows
    ]
    return outcomes


def compute_one(
    *,
    unitid: int,
    cipcode: str,
    soc_code: str,
    effort: EffortLevel = "balanced",
    loan_pct: float = 1.0,
    student_major: str | None = None,
    student_cip: str | None = None,
    intent_keywords: list[str] | None = None,
    home_state: str | None = None,
) -> CareerOutcome:
    """Return a single ``CareerOutcome`` for the selected SOC.

    /career-pick already ran ``compute_pentagon`` via ``/build/outcomes``
    and the user's selection carries the SOC forward. ``/build`` only
    needs that one row, so we reuse the same MCP fetch path and filter
    to the selected SOC in memory. Isolating this call site keeps the
    ``compute_pentagon`` signature frozen for every other caller.

    Raises ``ValueError`` when the MCP handler returns no rows at all
    (bubbled from ``compute_pentagon``) and ``LookupError`` when the
    requested SOC isn't among the rows we got back.
    """
    outcomes = compute_pentagon(
        unitid=unitid,
        cipcode=cipcode,
        student_major=student_major,
        student_cip=student_cip,
        effort=effort,
        loan_pct=loan_pct,
        intent_keywords=intent_keywords,
        home_state=home_state,
    )
    for outcome in outcomes:
        if outcome.soc_code == soc_code:
            return outcome
    raise LookupError(
        f"SOC {soc_code} not found for unitid={unitid}, cipcode={cipcode}"
    )
