"""Residency-aware cost computation.

Single source of truth for the 4-year published cost of attendance
adjusted for in-state vs. out-of-state public-school applicants. Used by:

- The MCP `get_career_paths` tool (per spec
  ``roi-net-lifetime-value`` Decision #11 followup) — applies the
  adjustment server-side when ``home_state`` is supplied so Gemma's
  tool call returns values consistent with what the backend computes
  and the UI displays.
- The backend ``stat_engine._published_cost_4yr`` callsite —
  re-exports from here to avoid drift.

Lives under ``src/mcp_server/`` because the MCP layer is the
canonical owner per the followup to spec
``roi-net-lifetime-value`` (the "Explain this to me" cost-mismatch
fix). Pure functions, no I/O, no service dependencies.
"""

from __future__ import annotations


def is_public_control(institution_control: str | None) -> bool:
    """Return True for Scorecard public-control labels.

    Upstream rows are not guaranteed to be the exact string ``"Public"``;
    they may carry labels such as ``"Public, 4-year or above"``. Frontend
    and backend agree on a starts-with check, so the MCP layer matches.
    """
    return bool(institution_control and institution_control.startswith("Public"))


def published_cost_4yr(
    *,
    cost_of_attendance_annual: float | None,
    tuition_in_state: float | None,
    tuition_out_of_state: float | None,
    institution_control: str | None,
    home_state: str | None,
    school_state: str | None,
) -> float | None:
    """Return the school's residency-aware 4-year published cost.

    Math:

      Private:                                COA × 4
      Public, in-state (home == school):       COA × 4
      Public, out-of-state (home != school):   (COA + (OOS_tuition - IS_tuition)) × 4
      Public, residency unknown:               COA × 4   (defaults to in-state)
      COA missing or non-positive:             None      (caller renders "—")

    Returns the 4-YEAR total. Callers divide by 4 if they need an
    annual figure (e.g. modeled_total_debt = published_cost_4yr ×
    loan_pct).
    """
    if cost_of_attendance_annual is None or cost_of_attendance_annual <= 0:
        return None
    coa = float(cost_of_attendance_annual)

    if not is_public_control(institution_control):
        return coa * 4.0

    if home_state is None or school_state is None:
        return coa * 4.0
    if home_state == school_state:
        return coa * 4.0
    if tuition_in_state is None or tuition_out_of_state is None:
        return coa * 4.0
    gap = float(tuition_out_of_state) - float(tuition_in_state)
    if gap <= 0:
        return coa * 4.0
    return (coa + gap) * 4.0
