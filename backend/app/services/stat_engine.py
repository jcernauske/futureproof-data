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

logger = logging.getLogger(__name__)

# Effort adjustment: shift applied to ERN in score points. ROI is
# intentionally excluded — effort reflects earning potential while in
# school, not debt load. A student studying harder doesn't reduce the
# tuition bill; ROI is set by the school's DTE and the loan_pct knob.
EFFORT_SHIFT: dict[str, int] = {
    "working_hard": -2,
    "working": -1,
    "balanced": 0,
    "focused": +1,
    "all_in": +2,
}


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    return None


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


def _apply_loan_pct(
    raw_stat_roi: int | None,
    raw_boss_loans: int | None,
    debt_to_earnings_annual: float | None,
    loan_pct: float,
) -> tuple[int | None, int | None]:
    """Re-derive stat_roi and boss_loans_score for the student's chosen
    loan percentage.

    loan_pct is 0.0-1.0. 1.0 (default) is a pass-through — the caller
    keeps the row's pre-computed stat_roi/boss_loans. 0.0 means the
    student takes no loans; ROI pins to 10 and the loans boss is trivial
    regardless of the program's raw DTE. Anything in between scales the
    raw DTE down and feeds it back through compute_stat_roi.
    """
    if loan_pct >= 1.0:
        return raw_stat_roi, raw_boss_loans
    if loan_pct <= 0.0:
        return 10, 1
    if debt_to_earnings_annual is None:
        # No DTE on this row (occupation-only rows in the substitution
        # path can hit this). Can't scale — leave the raw values alone.
        return raw_stat_roi, raw_boss_loans

    # Lazy import keeps the backend importable even when ``src/gold`` is
    # not on ``sys.path`` (e.g. isolated unit test environments).
    from gold.futureproof_engine import (
        compute_stat_roi,  # type: ignore[import-not-found]
    )

    adjusted_dte = float(debt_to_earnings_annual) * float(loan_pct)
    new_roi = compute_stat_roi(adjusted_dte)
    new_boss_loans = (11 - new_roi) if new_roi is not None else None
    return new_roi, new_boss_loans


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
    raw_stat_roi = _as_int(row.get("stat_roi"))
    raw_boss_loans = _as_int(row.get("boss_loans_score"))
    dte = row.get("debt_to_earnings_annual")
    adj_stat_roi, adj_boss_loans = _apply_loan_pct(
        raw_stat_roi, raw_boss_loans, dte, loan_pct
    )

    stats = PentagonStats(
        ern=_as_int(row.get("stat_ern")),
        roi=adj_stat_roi,
        res=_as_int(row.get("stat_res")),
        grw=_as_int(row.get("stat_grw")),
        hmn=_as_int(row.get("stat_hmn")),
    )
    stats = _apply_effort(stats, effort)

    bosses = BossScores(
        ai=_as_int(row.get("boss_ai_score")),
        loans=adj_boss_loans,
        market=_as_int(row.get("boss_market_score")),
        burnout=_as_int(row.get("boss_burnout_score")),
        ceiling=_as_int(row.get("boss_ceiling_score")),
    )

    def _list_field(name: str) -> list[dict[str, object]]:
        value = row.get(name)
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        return []

    return CareerOutcome(
        unitid=int(row["unitid"]),
        institution_name=str(row.get("institution_name") or ""),
        cipcode=str(row["cipcode"]),
        program_name=str(row.get("program_name") or ""),
        soc_code=str(row["soc_code"]),
        occupation_title=str(row.get("occupation_title") or ""),
        soc_major_group_name=row.get("soc_major_group_name"),
        median_annual_wage=row.get("median_annual_wage"),
        earnings_1yr_median=row.get("earnings_1yr_median"),
        earnings_1yr_p25=row.get("earnings_1yr_p25"),
        earnings_1yr_p75=row.get("earnings_1yr_p75"),
        debt_median=row.get("debt_median"),
        debt_to_earnings_annual=dte if isinstance(dte, (int, float)) else None,
        education_level_name=row.get("education_level_name"),
        growth_category=row.get("growth_category"),
        stats=stats,
        bosses=bosses,
        top_5_activities=_list_field("top_5_activities"),
        top_human_activities=_list_field("top_human_activities"),
        burnout_drivers=_list_field("burnout_drivers"),
        stats_available_count=_as_int(row.get("stats_available_count")),
        overall_confidence=row.get("overall_confidence"),
        substitution_applied=substitution_applied,
        reported_cipcode=reported_cipcode,
        substituted_cipcode=substituted_cipcode,
        data_caveat=data_caveat,
        loan_pct=loan_pct,
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
