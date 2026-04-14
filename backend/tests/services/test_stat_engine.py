"""Tests for stat_engine — effort adjustment, row mapping, error paths.

The MCP handler is patched so these tests are hermetic: they never
touch the real Iceberg catalog.
"""

from __future__ import annotations

import pytest

from app.models.career import PentagonStats
from app.services import stat_engine

_RAW_ROW = {
    "unitid": 151351,
    "institution_name": "Indiana University-Bloomington",
    "cipcode": "52.14",
    "program_name": "Marketing",
    "soc_code": "13-1131",
    "occupation_title": "Fundraisers",
    "soc_major_group_name": "Business and Financial Operations",
    "stat_ern": 8,
    "stat_roi": 6,
    "stat_res": 4,
    "stat_grw": 6,
    "stat_hmn": 6,
    "boss_ai_score": 7,
    "boss_loans_score": 5,
    "boss_market_score": 7,
    "boss_burnout_score": 6,
    "boss_ceiling_score": None,
    "median_annual_wage": 66490.0,
    "earnings_1yr_median": 63371.0,
    "earnings_1yr_p25": 38515.0,
    "earnings_1yr_p75": 49674.0,
    "debt_median": 19500.0,
    "debt_to_earnings_annual": 0.75,
    "education_level_name": "Bachelor's degree",
    "growth_category": "growing",
    "top_5_activities": [{"activity": "Interpersonal", "importance": 4.81}],
    "top_human_activities": [{"activity": "Interpersonal", "importance": 4.81}],
    "burnout_drivers": [{"element": "Duration", "value": 0.91}],
    "stats_available_count": 5,
    "overall_confidence": "high",
}


def _patch_mcp(monkeypatch, response):
    from app.services import mcp_client

    def fake_call(tool, args):
        assert tool == "get_career_paths"
        return response

    monkeypatch.setattr(mcp_client, "call", fake_call)


class TestComputePentagon:
    def test_maps_row_into_career_outcome(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {
                "data": [_RAW_ROW],
                "substitution_applied": False,
            },
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None
        )
        assert len(outcomes) == 1
        career = outcomes[0]
        assert career.occupation_title == "Fundraisers"
        assert career.stats.ern == 8
        assert career.stats.roi == 6  # pass-through at loan_pct default 1.0
        assert career.stats.res == 4
        assert career.bosses.ai == 7
        assert career.bosses.loans == 5
        assert career.debt_to_earnings_annual == 0.75
        assert career.loan_pct == 1.0
        assert career.top_human_activities[0]["activity"] == "Interpersonal"
        assert career.substitution_applied is False

    def test_effort_all_in_bumps_ern_only(self, monkeypatch):
        """ROI is intentionally excluded from the effort shift — debt
        load isn't something the student controls by studying harder.
        all_in now shifts ERN by +2 (base 8 → 10, clamped)."""
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            effort="all_in",
        )
        career = outcomes[0]
        assert career.stats.ern == 10  # base 8 + 2, clamped to 10
        assert career.stats.roi == 6  # unchanged by effort
        assert career.stats.res == 4
        assert career.stats.grw == 6
        assert career.stats.hmn == 6

    def test_effort_working_drops_ern_only(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            effort="working",
        )
        career = outcomes[0]
        assert career.stats.ern == 7
        assert career.stats.roi == 6  # unchanged by effort

    def test_effort_balanced_is_pass_through(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            effort="balanced",
        )
        assert outcomes[0].stats.ern == 8
        assert outcomes[0].stats.roi == 6

    def test_empty_result_raises_value_error(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [], "message": "No career paths found."},
        )
        with pytest.raises(ValueError, match="No career paths"):
            stat_engine.compute_pentagon(
                unitid=151351, cipcode="52.14", student_major=None
            )

    def test_substitution_metadata_passes_through(self, monkeypatch):
        caveat = {"type": "blended_substitution", "message": "test caveat"}
        _patch_mcp(
            monkeypatch,
            {
                "data": [_RAW_ROW],
                "substitution_applied": True,
                "reported_cipcode": "52.01",
                "substituted_cipcode": "52.14",
                "data_caveat": caveat,
            },
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.01",
            student_major="Marketing",
        )
        career = outcomes[0]
        assert career.substitution_applied is True
        assert career.reported_cipcode == "52.01"
        assert career.substituted_cipcode == "52.14"
        assert career.data_caveat == caveat

    def test_student_major_passed_to_handler(self, monkeypatch):
        captured = {}
        from app.services import mcp_client

        def capture(tool, args):
            captured.update(args)
            return {"data": [_RAW_ROW], "substitution_applied": False}

        monkeypatch.setattr(mcp_client, "call", capture)
        stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.01",
            student_major="Marketing",
        )
        assert captured["student_major"] == "Marketing"
        assert captured["cipcode"] == "52.01"

    def test_student_major_omitted_when_none(self, monkeypatch):
        captured = {}
        from app.services import mcp_client

        def capture(tool, args):
            captured.update(args)
            return {"data": [_RAW_ROW], "substitution_applied": False}

        monkeypatch.setattr(mcp_client, "call", capture)
        stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None
        )
        assert "student_major" not in captured


class TestLoanPct:
    """Loan percentage scales raw DTE before ROI/loans-boss derivation.

    Uses ``_RAW_ROW``'s ``debt_to_earnings_annual`` = 0.75 as the basis.
    """

    def test_default_loan_pct_is_pass_through(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None
        )
        career = outcomes[0]
        # No loan_pct passed → defaults to 1.0 → row values pass through.
        assert career.stats.roi == 6
        assert career.bosses.loans == 5
        assert career.loan_pct == 1.0

    def test_zero_loans_pins_roi_to_ten(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.0,
        )
        career = outcomes[0]
        assert career.stats.roi == 10
        assert career.bosses.loans == 1  # minimum threat
        assert career.loan_pct == 0.0

    def test_half_loans_recomputes_from_adjusted_dte(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.5,
        )
        career = outcomes[0]
        # DTE 0.75 * 0.5 = 0.375 — better than raw 0.75 but worse than 0.
        # ROI must be strictly higher than the raw-row stat_roi (6) and
        # at most 10, and boss_loans = 11 - roi.
        assert career.stats.roi is not None
        assert career.stats.roi > 6
        assert career.stats.roi <= 10
        assert career.bosses.loans == 11 - career.stats.roi

    def test_loan_pct_clamps_out_of_range(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=2.5,
        )
        career = outcomes[0]
        # Clamped to 1.0 → pass-through behavior.
        assert career.stats.roi == 6
        assert career.loan_pct == 1.0

    def test_loan_pct_passed_to_mcp_args(self, monkeypatch):
        captured: dict = {}
        from app.services import mcp_client

        def capture(tool, args):
            captured.update(args)
            return {"data": [_RAW_ROW], "substitution_applied": False}

        monkeypatch.setattr(mcp_client, "call", capture)
        stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.25,
        )
        assert captured["loan_pct"] == 0.25

    def test_missing_dte_leaves_raw_values_when_not_zero(self, monkeypatch):
        row = {**_RAW_ROW}
        row["debt_to_earnings_annual"] = None
        _patch_mcp(
            monkeypatch,
            {"data": [row], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.5,
        )
        career = outcomes[0]
        # Can't recompute without DTE → raw values pass through.
        assert career.stats.roi == 6
        assert career.bosses.loans == 5


class TestEffortShift:
    def test_clamp_low_end_ern(self):
        stats = PentagonStats(ern=1, roi=4, res=5, grw=5, hmn=5)
        shifted = stat_engine._apply_effort(stats, "working")
        assert shifted.ern == 1  # clamped, not 0
        assert shifted.roi == 4  # untouched by effort

    def test_clamp_high_end_ern(self):
        stats = PentagonStats(ern=10, roi=4, res=5, grw=5, hmn=5)
        shifted = stat_engine._apply_effort(stats, "all_in")
        assert shifted.ern == 10
        assert shifted.roi == 4  # untouched by effort

    def test_roi_not_shifted(self):
        """ROI must ignore effort — studying harder doesn't cut tuition."""
        stats = PentagonStats(ern=5, roi=3, res=5, grw=5, hmn=5)
        assert stat_engine._apply_effort(stats, "all_in").roi == 3
        assert stat_engine._apply_effort(stats, "working").roi == 3
        assert stat_engine._apply_effort(stats, "balanced").roi == 3

    def test_none_ern_passes_through(self):
        stats = PentagonStats(ern=None, roi=5, res=None, grw=None, hmn=None)
        shifted = stat_engine._apply_effort(stats, "all_in")
        assert shifted.ern is None
        assert shifted.roi == 5
