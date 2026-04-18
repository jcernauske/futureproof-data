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
from typing import Any

from app.models.career import (
    BossScores,
    CareerOutcome,
    EffortLevel,
    PentagonStats,
)
from app.services import mcp_client
from app.services._coercion import as_int

logger = logging.getLogger(__name__)

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
        hmn=stats.hmn,
    )


def _derive_roi(
    *,
    cost_based_dte: float | None,
    raw_stat_roi: int | None,
) -> int | None:
    """Compute stat_roi from the Gold-level cost-based DTE.

    ``cost_based_dte`` is already cost-of-attendance-vs-earnings (or
    debt_median-vs-earnings on the fallback row). loan_pct is NOT an
    argument — ROI reflects the economic value of the program, not how
    the student chooses to pay.

    Falls back to ``raw_stat_roi`` (from the row) when the DTE is
    missing, so occupation-only rows in the substitution path don't
    lose their pre-computed score.
    """
    if cost_based_dte is None:
        return raw_stat_roi
    from gold.futureproof_engine import (
        compute_stat_roi,  # type: ignore[import-not-found]
    )
    return compute_stat_roi(cost_based_dte)


def _derive_loans_boss(
    *,
    net_price_annual: float | None,
    debt_median: float | None,
    earnings_1yr_median: float | None,
    loan_pct: float,
) -> tuple[int | None, float | None, float | None]:
    """Compute (boss_loans_score, modeled_total_debt, financed_dte).

    Unlike ROI, the Student Loans Boss IS financing-aware. The math is:

        modeled_total_debt = cost_per_year * 4 * loan_pct
        financed_dte       = modeled_total_debt / earnings_1yr_median
        boss_loans_score   = 11 - compute_stat_roi(financed_dte)

    where ``cost_per_year`` is ``net_price_annual`` when available and
    ``debt_median / 4`` as a coarse back-compat fallback (legacy rows
    whose debt_median is a cumulative 4-year figure — this collapses to
    the pre-split behaviour when net_price is absent).

    Special cases:
    - loan_pct <= 0.0: no debt, boss is trivially auto-win (score 1).
    - loan_pct >= 1.0 with no cost inputs: pass the pre-computed
      boss_loans from the row (see caller) — this helper returns
      None/None/None and the caller substitutes the row value.
    - earnings missing or zero: can't compute a DTE — caller handles.

    Returns ``(boss_loans_score, modeled_total_debt, financed_dte)``.
    """
    from gold.futureproof_engine import (
        compute_stat_roi,  # type: ignore[import-not-found]
    )

    # No-loans branch — no debt, trivially win the loans boss.
    if loan_pct <= 0.0:
        return 1, 0.0, 0.0

    # Choose the cost-per-year basis. net_price_annual is the real
    # 4-year attendance cost; debt_median is a cumulative 4-year figure
    # so we divide by 4 to match the ``cost_per_year × 4`` formula.
    cost_per_year: float | None = None
    if net_price_annual is not None:
        cost_per_year = float(net_price_annual)
    elif debt_median is not None:
        cost_per_year = float(debt_median) / 4.0

    if cost_per_year is None:
        return None, None, None
    if earnings_1yr_median is None or float(earnings_1yr_median) <= 0:
        # We know the modeled debt but can't form a DTE.
        modeled_debt = cost_per_year * 4.0 * float(loan_pct)
        return None, modeled_debt, None

    modeled_debt = cost_per_year * 4.0 * float(loan_pct)
    financed_dte = modeled_debt / float(earnings_1yr_median)
    equivalent_roi = compute_stat_roi(financed_dte)
    boss_loans = (11 - equivalent_roi) if equivalent_roi is not None else None
    return boss_loans, modeled_debt, financed_dte


def _row_to_outcome(
    row: dict[str, Any],
    effort: EffortLevel,
    loan_pct: float,
    *,
    substitution_applied: bool,
    reported_cipcode: str | None,
    substituted_cipcode: str | None,
    data_caveat: dict[str, Any] | None,
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

    # ROI is loan_pct-independent — it reflects program cost vs earnings.
    adj_stat_roi = _derive_roi(
        cost_based_dte=dte_f,
        raw_stat_roi=raw_stat_roi,
    )
    # Student Loans Boss IS loan_pct-aware — it reflects financing choices.
    boss_loans_derived, modeled_total_debt, financed_dte = _derive_loans_boss(
        net_price_annual=net_price_f,
        debt_median=debt_median_f,
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

    stats = PentagonStats(
        ern=as_int(row.get("stat_ern")),
        roi=adj_stat_roi,
        res=as_int(row.get("stat_res")),
        grw=as_int(row.get("stat_grw")),
        hmn=as_int(row.get("stat_hmn")),
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

    return CareerOutcome(
        unitid=int(row["unitid"]),
        institution_name=str(row.get("institution_name") or ""),
        cipcode=str(row["cipcode"]),
        program_name=str(row.get("program_name") or ""),
        soc_code=str(row["soc_code"]),
        occupation_title=str(row.get("occupation_title") or ""),
        soc_major_group_name=row.get("soc_major_group_name"),
        median_annual_wage=row.get("median_annual_wage"),
        earnings_1yr_median=earnings_raw,
        earnings_1yr_p25=row.get("earnings_1yr_p25"),
        earnings_1yr_p75=row.get("earnings_1yr_p75"),
        debt_median=debt_median_raw,
        debt_p25=row.get("debt_p25"),
        debt_p75=row.get("debt_p75"),
        debt_to_earnings_annual=dte if isinstance(dte, (int, float)) else None,
        education_level_name=row.get("education_level_name"),
        growth_category=row.get("growth_category"),
        net_price_annual=net_price_annual_raw,
        cost_of_attendance_annual=row.get("cost_of_attendance_annual"),
        modeled_total_debt=modeled_total_debt,
        debt_median_reference=debt_median_reference,
        institution_control=row.get("institution_control"),
        tuition_in_state=row.get("tuition_in_state"),
        tuition_out_of_state=row.get("tuition_out_of_state"),
        room_board_on_campus=row.get("room_board_on_campus"),
        stats=stats,
        bosses=bosses,
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
        roi_cost_basis=row.get("roi_cost_basis"),
        financed_dte=financed_dte,
    )


def compute_pentagon(
    *,
    unitid: int,
    cipcode: str,
    student_major: str | None,
    effort: EffortLevel = "balanced",
    loan_pct: float = 1.0,
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

    result = mcp_client.call("get_career_paths", args)
    rows = result.get("data") or []
    if not rows:
        message = result.get("message") or "No career paths found."
        raise ValueError(message)

    substitution_applied = bool(result.get("substitution_applied"))
    reported_cipcode = result.get("reported_cipcode") or cipcode
    substituted_cipcode = result.get("substituted_cipcode")
    data_caveat = result.get("data_caveat") if substitution_applied else None

    outcomes = [
        _row_to_outcome(
            row,
            effort,
            loan_pct,
            substitution_applied=substitution_applied,
            reported_cipcode=reported_cipcode,
            substituted_cipcode=substituted_cipcode,
            data_caveat=data_caveat,
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
        effort=effort,
        loan_pct=loan_pct,
    )
    for outcome in outcomes:
        if outcome.soc_code == soc_code:
            return outcome
    raise LookupError(
        f"SOC {soc_code} not found for unitid={unitid}, cipcode={cipcode}"
    )
