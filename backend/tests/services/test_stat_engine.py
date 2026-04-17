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
        assert career.stats.roi == 7  # derived from dte=0.75 → band 0.5-0.75 → 7
        assert career.stats.res == 4
        assert career.bosses.ai == 7
        # bosses.loans derives from financed_dte at loan_pct=1.0:
        # cost_per_year = debt_median/4 = 4875; modeled = 4875*4 = 19500;
        # financed_dte = 19500/63371 ≈ 0.308 → equivalent ROI 10, boss = 1.
        assert career.bosses.loans == 1
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
        assert career.stats.roi == 7  # unchanged by effort
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
        assert career.stats.roi == 7  # unchanged by effort

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
        assert outcomes[0].stats.roi == 7

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
    """Loan percentage drives the Student Loans Boss — NOT ROI.

    After the cost-based-ROI rewrite (plan
    ~/.claude/plans/why-are-we-still-jaunty-curry.md), stat_roi reflects
    the program's cost-of-attendance vs. starting salary and is
    independent of loan_pct. The slider only scales modeled debt +
    financed DTE, which drive boss_loans_score.

    ``_RAW_ROW``'s ``debt_to_earnings_annual`` = 0.75 is treated as the
    Gold-level cost-based DTE → compute_stat_roi(0.75) = 7.
    """

    def test_default_loan_pct_yields_derived_roi(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None
        )
        career = outcomes[0]
        # ROI derived from dte=0.75 → compute_stat_roi(0.75) = 7.
        assert career.stats.roi == 7
        assert career.loan_pct == 1.0

    def test_roi_is_independent_of_loan_pct(self, monkeypatch):
        """Slider should NOT shift ROI — it reflects program economics."""
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        roi_by_loan: dict[float, int | None] = {}
        for loan_pct in (0.0, 0.25, 0.5, 0.75, 1.0):
            outcomes = stat_engine.compute_pentagon(
                unitid=151351,
                cipcode="52.14",
                student_major=None,
                loan_pct=loan_pct,
            )
            roi_by_loan[loan_pct] = outcomes[0].stats.roi
        assert len(set(roi_by_loan.values())) == 1, (
            f"ROI should be constant across loan_pct; got {roi_by_loan}"
        )

    def test_loans_boss_scales_with_loan_pct(self, monkeypatch):
        """Higher loan coverage → harder Loans Boss (lower auto-win)."""
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        losses_at: dict[float, int | None] = {}
        for loan_pct in (0.0, 0.5, 1.0):
            outcomes = stat_engine.compute_pentagon(
                unitid=151351,
                cipcode="52.14",
                student_major=None,
                loan_pct=loan_pct,
            )
            losses_at[loan_pct] = outcomes[0].bosses.loans
        # Zero loans → auto-win (score 1).
        assert losses_at[0.0] == 1
        # Loans boss should monotonically increase with loan_pct.
        assert losses_at[0.0] is not None
        assert losses_at[0.5] is not None
        assert losses_at[1.0] is not None
        assert losses_at[0.0] <= losses_at[0.5] <= losses_at[1.0]

    def test_zero_loans_zeros_modeled_debt(self, monkeypatch):
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
        assert career.modeled_total_debt == 0.0
        assert career.bosses.loans == 1
        assert career.financed_dte == 0.0

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

    def test_missing_dte_falls_back_to_raw_roi(self, monkeypatch):
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
        # With no DTE, _derive_roi falls back to the row's raw stat_roi.
        assert career.stats.roi == 6


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


class TestRoiWithCostOfAttendance:
    """ROI and Loans Boss under the cost-based-ROI rewrite.

    Plan: ~/.claude/plans/why-are-we-still-jaunty-curry.md

    ROI is a loan_pct-independent property of the program — computed
    from the Gold-level cost-based DTE. The Student Loans Boss IS
    loan_pct-aware and uses modeled_total_debt / earnings as its own
    ratio (stored as financed_dte on the outcome).
    """

    def _row_with_cost(self, **overrides):
        # Indiana-State-style numbers. Under the new Gold SQL, the row's
        # debt_to_earnings_annual would be computed as
        # (net_price_annual × 4) / earnings = (14_200 × 4) / 63_371 = 0.896.
        row = {
            **_RAW_ROW,
            "net_price_annual": 14_200.0,
            "cost_of_attendance_annual": 22_800.0,
            "institution_control": "Public",
            "tuition_in_state": 9_800.0,
            "tuition_out_of_state": 21_400.0,
            "room_board_on_campus": 11_500.0,
            "debt_to_earnings_annual": (14_200.0 * 4.0) / 63_371.0,
            "roi_cost_basis": "cost_of_attendance",
        }
        row.update(overrides)
        return row

    def test_roi_derived_from_cost_based_dte(self, monkeypatch):
        """ROI derives from the Gold DTE, not from the raw stat_roi."""
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None, loan_pct=1.0
        )
        career = outcomes[0]
        # DTE ≈ 0.896 → in the 0.75-1.0 band, ROI should be 5-7.
        assert career.stats.roi is not None
        assert 4 <= career.stats.roi <= 7
        assert career.net_price_annual == 14_200.0
        assert career.cost_of_attendance_annual == 22_800.0
        assert career.institution_control == "Public"
        assert career.debt_median_reference == 19_500.0
        assert career.roi_cost_basis == "cost_of_attendance"

    def test_loans_boss_uses_financed_dte_with_net_price(self, monkeypatch):
        """Loans Boss = f(net_price × 4 × loan_pct / earnings)."""
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.5,
        )
        career = outcomes[0]
        # 14_200 × 4 × 0.5 = 28_400; 28_400 / 63_371 ≈ 0.448 → on the
        # 0.25-0.5 band fraction≈0.79, equivalent ROI = 9.
        # Loans boss = 11 − 9 = 2.
        assert career.modeled_total_debt == 14_200.0 * 4.0 * 0.5
        assert career.financed_dte is not None
        assert abs(career.financed_dte - (28_400.0 / 63_371.0)) < 1e-9
        assert career.bosses.loans == 2

    def test_roi_identical_across_loan_pcts(self, monkeypatch):
        """ROI must be the same at loan_pct=0.0, 0.5, and 1.0."""
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        rois = []
        for loan_pct in (0.0, 0.5, 1.0):
            outcomes = stat_engine.compute_pentagon(
                unitid=151351,
                cipcode="52.14",
                student_major=None,
                loan_pct=loan_pct,
            )
            rois.append(outcomes[0].stats.roi)
        assert len(set(rois)) == 1, f"ROI varied with loan_pct: {rois}"

    def test_fallback_to_debt_median_basis(self, monkeypatch):
        """Without net_price_annual, Gold stamps basis=debt_median."""
        row = {**_RAW_ROW}
        row.pop("net_price_annual", None)
        row["debt_to_earnings_annual"] = 19_500.0 / 63_371.0  # 0.308
        row["roi_cost_basis"] = "debt_median"
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None, loan_pct=1.0
        )
        career = outcomes[0]
        # DTE 0.308 → band 0.25-0.5 → ROI 10 (excellent).
        assert career.stats.roi == 10
        assert career.net_price_annual is None
        assert career.roi_cost_basis == "debt_median"
        # modeled from (debt_median/4) × 4 × loan_pct = debt_median × loan_pct.
        assert career.modeled_total_debt == 19_500.0
        assert career.debt_median_reference == 19_500.0

    def test_modeled_total_debt_with_net_price(self, monkeypatch):
        """modeled_total_debt = net_price × 4 × loan_pct."""
        _patch_mcp(
            monkeypatch,
            {
                "data": [self._row_with_cost(net_price_annual=20_000.0)],
                "substitution_applied": False,
            },
        )
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.75,
        )
        career = outcomes[0]
        # 20_000 × 4 × 0.75 = 60_000 exactly.
        assert career.modeled_total_debt == 60_000.0

    def test_zero_loans_zeros_modeled_debt_but_keeps_roi(self, monkeypatch):
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes_0 = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None, loan_pct=0.0
        )
        outcomes_1 = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None, loan_pct=1.0
        )
        # ROI doesn't move with financing.
        assert outcomes_0[0].stats.roi == outcomes_1[0].stats.roi
        # But the loans boss and modeled debt collapse to trivial.
        assert outcomes_0[0].bosses.loans == 1
        assert outcomes_0[0].modeled_total_debt == 0.0
        assert outcomes_0[0].financed_dte == 0.0

    def test_cost_fields_propagate_to_outcome(self, monkeypatch):
        """All institution-level cost fields land on CareerOutcome."""
        row = self._row_with_cost(
            net_price_annual=15_500.0,
            cost_of_attendance_annual=25_000.0,
            institution_control="Private nonprofit",
            tuition_in_state=18_000.0,
            tuition_out_of_state=18_000.0,
            room_board_on_campus=12_000.0,
            debt_to_earnings_annual=(15_500.0 * 4.0) / 63_371.0,
        )
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None
        )
        career = outcomes[0]
        assert career.net_price_annual == 15_500.0
        assert career.cost_of_attendance_annual == 25_000.0
        assert career.institution_control == "Private nonprofit"
        assert career.tuition_in_state == 18_000.0
        assert career.tuition_out_of_state == 18_000.0
        assert career.room_board_on_campus == 12_000.0
        # debt_median_reference mirrors debt_median.
        assert career.debt_median_reference == career.debt_median
        # New fields propagate.
        assert career.roi_cost_basis == "cost_of_attendance"
        assert career.financed_dte is not None
