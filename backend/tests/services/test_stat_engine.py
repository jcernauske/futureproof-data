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
    # Per the 2026-05-02 cost-anchor change, ROI's DTE is computed from
    # published_cost_4yr (= COA × 4 in-state, COA × 4 + tuition gap × 4
    # OOS at publics). Setting COA = 11_882.75 gives published_cost_4yr
    # = 47_531 → 47_531 / 63_371 = 0.75, matching the legacy
    # debt_to_earnings_annual value so existing ROI band assertions
    # continue to hold.
    "cost_of_attendance_annual": 11_882.75,
    "institution_control": "Public",
    "tuition_in_state": 9_800.0,
    "tuition_out_of_state": 21_400.0,
    "state_abbr": "IN",
    "education_level_name": "Bachelor's degree",
    "growth_category": "growing",
    "top_5_activities": [{"activity": "Interpersonal", "importance": 4.81}],
    "top_human_activities": [{"activity": "Interpersonal", "importance": 4.81}],
    "burnout_drivers": [{"element": "Duration", "value": 0.91}],
    "stats_available_count": 5,
    "overall_confidence": "high",
}


def _patch_mcp(monkeypatch, response, *, aura_response=None):
    """Patch mcp_client.call to handle both tools stat_engine now calls.

    ``response`` mocks ``get_career_paths`` (the existing pattern).
    ``aura_response`` mocks ``get_institution_aura``, defaulting to a
    structured-null payload so legacy tests that don't care about AURA
    just see ``stats.aura is None`` on every outcome.
    """
    from app.services import mcp_client

    if aura_response is None:
        aura_response = {"data": None, "message": "no row"}

    def fake_call(tool, args):
        if tool == "get_career_paths":
            return response
        if tool == "get_institution_aura":
            return aura_response
        raise AssertionError(f"Unexpected MCP tool called: {tool!r}")

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
        # Pentagon-stat-reshape: stats.res is blended from stat_res=4 +
        # stat_hmn=6 → mean=5. Raw inputs preserved on CareerOutcome.
        assert career.stats.res == 5
        assert career.raw_stat_res == 4
        assert career.raw_stat_hmn == 6
        assert career.stats.aura is None  # default mock returns no aura row
        assert career.bosses.ai == 7
        # Per the 2026-05-02 cost-anchor change, bosses.loans derives
        # from published_cost_4yr × loan_pct / earnings:
        # published_cost_4yr (in-state default) = 11_882.75 × 4 = 47_531
        # modeled = 47_531 × 1.0 = 47_531
        # financed_dte = 47_531 / 63_371 ≈ 0.75 → equivalent ROI 7,
        # boss = 11 − 7 = 4.
        assert career.bosses.loans == 4
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
        # Blended RES = mean(stat_res=4, stat_hmn=6) = 5.
        assert career.stats.res == 5
        assert career.stats.grw == 6
        # AURA mock defaults to None when no aura_response is passed.
        assert career.stats.aura is None

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
            if tool == "get_institution_aura":
                # AURA lookup is not the subject of these tests.
                return {"data": None, "message": "no row"}
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
            if tool == "get_institution_aura":
                # AURA lookup is not the subject of these tests.
                return {"data": None, "message": "no row"}
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
            if tool == "get_institution_aura":
                # AURA lookup is not the subject of these tests.
                return {"data": None, "message": "no row"}
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

    def test_missing_cost_falls_back_to_raw_roi(self, monkeypatch):
        """When cost_of_attendance_annual is missing, published_cost_4yr
        is None and _derive_roi falls back to the row's raw stat_roi.
        debt_to_earnings_annual is no longer the cost-basis input.
        """
        row = {**_RAW_ROW}
        row["cost_of_attendance_annual"] = None
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
        # With no COA, _derive_roi falls back to the row's raw stat_roi.
        assert career.stats.roi == 6
        assert career.published_cost_4yr is None


class TestEffortShift:
    def test_clamp_low_end_ern(self):
        stats = PentagonStats(ern=1, roi=4, res=5, grw=5, aura=5)
        shifted = stat_engine._apply_effort(stats, "working")
        assert shifted.ern == 1  # clamped, not 0
        assert shifted.roi == 4  # untouched by effort

    def test_clamp_high_end_ern(self):
        stats = PentagonStats(ern=10, roi=4, res=5, grw=5, aura=5)
        shifted = stat_engine._apply_effort(stats, "all_in")
        assert shifted.ern == 10
        assert shifted.roi == 4  # untouched by effort

    def test_roi_not_shifted(self):
        """ROI must ignore effort — studying harder doesn't cut tuition."""
        stats = PentagonStats(ern=5, roi=3, res=5, grw=5, aura=5)
        assert stat_engine._apply_effort(stats, "all_in").roi == 3
        assert stat_engine._apply_effort(stats, "working").roi == 3
        assert stat_engine._apply_effort(stats, "balanced").roi == 3

    def test_none_ern_passes_through(self):
        stats = PentagonStats(ern=None, roi=5, res=None, grw=None, aura=None)
        shifted = stat_engine._apply_effort(stats, "all_in")
        assert shifted.ern is None
        assert shifted.roi == 5


class TestComputeOne:
    """compute_one is the /build router's single-row helper.

    It reuses compute_pentagon under the hood and filters to the SOC the
    student selected in career-pick. The router depends on three
    behaviors we lock in here:

    1. It returns EXACTLY the row matching ``soc_code``, not the first or
       most-complete one.
    2. It raises ``LookupError`` when the SOC isn't in the MCP result so
       the router can map it to HTTP 404.
    3. It propagates ``ValueError`` from compute_pentagon (empty MCP
       result) unchanged so the router can map it to HTTP 422.
    """

    def test_compute_one_returns_selected_soc(self, monkeypatch):
        other_row = {
            **_RAW_ROW,
            "soc_code": "11-2021",  # Marketing Manager — NOT the one we pick
            "occupation_title": "Marketing Managers",
            "stats_available_count": 5,
        }
        wanted_row = {
            **_RAW_ROW,
            "soc_code": "13-1131",  # Fundraisers — what we're picking
            "occupation_title": "Fundraisers",
            "stats_available_count": 3,  # less complete on purpose
        }
        _patch_mcp(
            monkeypatch,
            {
                "data": [other_row, wanted_row],
                "substitution_applied": False,
            },
        )
        outcome = stat_engine.compute_one(
            unitid=151351,
            cipcode="52.14",
            soc_code="13-1131",
            student_major=None,
        )
        # Must return the SOC the caller asked for, even when a different
        # SOC has a higher stats_available_count.
        assert outcome.soc_code == "13-1131"
        assert outcome.occupation_title == "Fundraisers"

    def test_compute_one_raises_on_missing_soc(self, monkeypatch):
        _patch_mcp(
            monkeypatch,
            {
                "data": [{**_RAW_ROW, "soc_code": "11-2021"}],
                "substitution_applied": False,
            },
        )
        with pytest.raises(LookupError, match="SOC 99-9999 not found"):
            stat_engine.compute_one(
                unitid=151351,
                cipcode="52.14",
                soc_code="99-9999",
                student_major=None,
            )

    def test_compute_one_propagates_value_error_on_empty_mcp(self, monkeypatch):
        """Empty MCP response must surface as ValueError so the router
        can translate to HTTP 422 (same contract as compute_pentagon)."""
        _patch_mcp(
            monkeypatch,
            {"data": [], "message": "No career paths found."},
        )
        with pytest.raises(ValueError, match="No career paths"):
            stat_engine.compute_one(
                unitid=151351,
                cipcode="52.14",
                soc_code="13-1131",
                student_major=None,
            )

    def test_compute_one_honors_effort_and_loan_pct(self, monkeypatch):
        """Delegation to compute_pentagon isn't enough — the selected
        outcome has to carry the effort/loan_pct adjustments through."""
        _patch_mcp(
            monkeypatch,
            {"data": [_RAW_ROW], "substitution_applied": False},
        )
        outcome = stat_engine.compute_one(
            unitid=151351,
            cipcode="52.14",
            soc_code="13-1131",
            effort="all_in",
            loan_pct=0.0,
            student_major=None,
        )
        # all_in bumps ERN by +2 (8 + 2 = 10).
        assert outcome.stats.ern == 10
        # loan_pct=0 → auto-win loans boss + zero modeled debt.
        assert outcome.loan_pct == 0.0
        assert outcome.bosses.loans == 1
        assert outcome.modeled_total_debt == 0.0


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

    def test_roi_derived_from_published_cost_dte(self, monkeypatch):
        """ROI derives from published_cost_4yr / earnings, not raw stat_roi.

        Per the 2026-05-02 cost-anchor change, ROI's DTE is anchored on
        the school's full sticker (COA × 4 in-state default), NOT on
        net_price × 4."""
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None, loan_pct=1.0
        )
        career = outcomes[0]
        # COA × 4 / earnings = (22,800 × 4) / 63,371 = 1.439
        # DTE 1.439 → band 1.0-1.5 → ROI ~3.
        assert career.stats.roi is not None
        assert 2 <= career.stats.roi <= 4
        assert career.published_cost_4yr == 91_200.0
        assert career.net_price_annual == 14_200.0  # still surfaced for reference
        assert career.cost_of_attendance_annual == 22_800.0
        assert career.institution_control == "Public"
        assert career.debt_median_reference == 19_500.0
        assert career.roi_cost_basis == "cost_of_attendance"

    def test_loans_boss_uses_financed_dte_with_published_cost(self, monkeypatch):
        """Loans Boss = f(published_cost_4yr × loan_pct / earnings).

        Per the 2026-05-02 cost-anchor change, the loans boss is
        anchored on COA × 4 (residency-aware), not on net_price × 4.
        """
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=0.5,
        )
        career = outcomes[0]
        # COA × 4 (in-state, no home_state passed) = 22_800 × 4 = 91_200.
        # modeled_debt = 91_200 × 0.5 = 45_600.
        # financed_dte = 45_600 / 63_371 ≈ 0.7196 → ROI band 0.5-0.75 → ROI ≈ 7.
        # Loans boss = 11 − 7 = 4.
        assert career.published_cost_4yr == 22_800.0 * 4.0
        assert career.modeled_total_debt == 22_800.0 * 4.0 * 0.5
        assert career.financed_dte is not None
        assert abs(career.financed_dte - (45_600.0 / 63_371.0)) < 1e-9
        assert career.bosses.loans == 4

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

    def test_no_debt_median_fallback_when_coa_missing(self, monkeypatch):
        """Per the 2026-05-02 cost-anchor change, the debt_median
        fallback is REMOVED. When cost_of_attendance_annual is missing,
        ROI falls back to the row's raw stat_roi (the Gold-zone
        baseline) and modeled_total_debt is None — no fabrication
        from debt_median."""
        row = {**_RAW_ROW}
        row.pop("cost_of_attendance_annual", None)
        row.pop("net_price_annual", None)
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})
        outcomes = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None, loan_pct=1.0
        )
        career = outcomes[0]
        # No COA → published_cost_4yr is None → ROI falls back to the
        # row's raw stat_roi (here 6, from _RAW_ROW).
        assert career.published_cost_4yr is None
        assert career.stats.roi == 6  # raw stat_roi from row
        # No cost basis → no modeled debt. The debt_median fallback
        # that USED to fabricate a number here is gone (intentionally).
        assert career.modeled_total_debt is None
        # debt_median is still surfaced as a "for reference" field, but
        # it does NOT drive the score.
        assert career.debt_median_reference == 19_500.0

    def test_modeled_total_debt_with_published_cost(self, monkeypatch):
        """modeled_total_debt = published_cost_4yr × loan_pct.

        Post-2026-05-02 cost-anchor change: net_price_annual no longer
        drives modeled_total_debt; the school's published 4-year COA
        does (residency-aware)."""
        _patch_mcp(
            monkeypatch,
            {
                "data": [self._row_with_cost(cost_of_attendance_annual=25_000.0)],
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
        # COA=25_000 → published_cost_4yr (in-state default) = 100_000.
        # modeled_debt = 100_000 × 0.75 = 75_000.
        assert career.published_cost_4yr == 100_000.0
        assert career.modeled_total_debt == 75_000.0

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


class TestResidencyAwareTuition:
    """Residency-aware tuition adjustment tests.

    Feature: docs/specs/feature-residency-aware-tuition.md

    When a student is out-of-state at a public school, net_price_annual
    is adjusted upward by the tuition gap (out_of_state - in_state)
    before computing ROI and the Student Loans Boss. Private schools,
    in-state students, and missing home_state all skip adjustment.

    _row_with_cost() defaults:
        net_price_annual = 14,200  (blended average from College Scorecard)
        tuition_in_state = 9,800
        tuition_out_of_state = 21,400
        gap = 11,600
        net_price_annual (adjusted) = 25,800 (for out-of-state public)
        earnings = 63,371
    """

    def _row_with_cost(self, **overrides):
        row = {
            **_RAW_ROW,
            "net_price_annual": 14_200.0,
            "cost_of_attendance_annual": 22_800.0,
            "institution_control": "Public",
            "state_abbr": "IN",
            "tuition_in_state": 9_800.0,
            "tuition_out_of_state": 21_400.0,
            "room_board_on_campus": 11_500.0,
            "debt_to_earnings_annual": (14_200.0 * 4.0) / 63_371.0,
            "roi_cost_basis": "cost_of_attendance",
        }
        row.update(overrides)
        return row

    # ── P0: Out-of-state public adjusts net_price ──────────────────────

    def test_out_of_state_public_adjusts_published_cost(self, monkeypatch):
        """Out-of-state at a public school: ROI, Loans Boss, and
        modeled_debt all reflect (COA + tuition_gap) × 4.

        Per the 2026-05-02 cost-anchor change, residency adjustment
        now drives published_cost_4yr (sticker), not net_price_annual.

        COA_in_state = 22,800
        gap = 21,400 - 9,800 = 11,600
        published_cost_4yr (OOS) = (22,800 + 11,600) × 4 = 137,600
        """
        row = self._row_with_cost()  # Public, state_abbr="IN"
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})

        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=1.0,
            home_state="OH",  # different from school's "IN"
        )
        career = outcomes[0]

        # published_cost_4yr carries the OOS-adjusted full sticker.
        assert career.published_cost_4yr == 137_600.0

        # modeled_total_debt = published_cost_4yr × loan_pct.
        assert career.modeled_total_debt == 137_600.0 * 1.0

        # ROI should be much worse than the unadjusted baseline.
        # Adjusted DTE = 137_600 / 63,371 = 2.171 → ROI ~2.
        assert career.stats.roi is not None
        assert career.stats.roi <= 3

        # Loans Boss should be hard (high score).
        # financed_dte = 137,600 / 63,371 = 2.171 → equiv ROI ~2 → boss 9+.
        assert career.bosses.loans is not None
        assert career.bosses.loans >= 8

    # ── P0: Out-of-state ROI uses recomputed DTE ──────────────────────

    def test_out_of_state_roi_uses_recomputed_dte(self, monkeypatch):
        """ROI must NOT use the pre-baked Gold dte_f when residency
        adjustment applies — it must recompute from
        (adjusted_net_price * 4) / earnings.

        If we accidentally pass the Gold DTE through, ROI would stay ~6
        (the unadjusted value). The recomputed DTE is 1.629, giving ROI ~3.
        """
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})

        # Without home_state: uses Gold DTE.
        baseline = stat_engine.compute_pentagon(
            unitid=151351, cipcode="52.14", student_major=None
        )
        baseline_roi = baseline[0].stats.roi

        # With out-of-state: must recompute DTE.
        adjusted = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            home_state="OH",
        )
        adjusted_roi = adjusted[0].stats.roi

        # The adjusted ROI must be strictly worse (lower score) because
        # the cost basis is higher.
        assert adjusted_roi is not None
        assert baseline_roi is not None
        assert adjusted_roi < baseline_roi

    # ── P0: In-state public → no adjustment ───────────────────────────

    def test_in_state_public_no_adjustment(self, monkeypatch):
        """When home_state matches school state_abbr, no adjustment.
        published_cost_4yr is just COA × 4, no OOS premium added."""
        row = self._row_with_cost()  # state_abbr="IN"
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})

        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            home_state="IN",  # matches school state
        )
        career = outcomes[0]

        # No OOS adjustment — published_cost_4yr is COA × 4 = 91,200.
        assert career.published_cost_4yr == 22_800.0 * 4.0
        # ROI derives from this in-state COA × 4 / earnings.
        from gold.futureproof_engine import compute_stat_roi

        expected_dte = (22_800.0 * 4.0) / 63_371.0
        expected_roi = compute_stat_roi(expected_dte)
        assert career.stats.roi == expected_roi

    # ── P0: Private school → no adjustment ────────────────────────────

    def test_private_school_no_adjustment(self, monkeypatch):
        """Private schools skip residency adjustment regardless of
        home_state — they charge the same for everyone."""
        row = self._row_with_cost(
            institution_control="Private nonprofit",
            tuition_in_state=35_000.0,
            tuition_out_of_state=35_000.0,
            debt_to_earnings_annual=(35_000.0 * 4.0) / 63_371.0,
            net_price_annual=35_000.0,
        )
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})

        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            home_state="OH",  # different state, but private school
        )
        career = outcomes[0]

        assert career.net_price_annual_reference is None
        assert career.institution_control == "Private nonprofit"

    # ── P0: No home_state → no adjustment (backward compat) ───────────

    def test_no_home_state_no_adjustment(self, monkeypatch):
        """When home_state is None (user skipped state selection),
        published_cost_4yr defaults to in-state COA × 4 — the lower
        of the two reasonable defaults at a public school."""
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})

        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            # home_state not passed → defaults to None
        )
        career = outcomes[0]

        # In-state COA × 4 (no OOS premium without home_state).
        assert career.published_cost_4yr == 22_800.0 * 4.0
        # ROI derives from this in-state COA × 4 / earnings.
        from gold.futureproof_engine import compute_stat_roi

        expected_dte = (22_800.0 * 4.0) / 63_371.0
        assert career.stats.roi == compute_stat_roi(expected_dte)

    # ── P1: Missing tuition values → no adjustment ────────────────────

    def test_missing_tuition_values_no_adjustment(self, monkeypatch):
        """When tuition_in_state or tuition_out_of_state is null,
        adjustment is skipped even for out-of-state public."""
        # Missing tuition_in_state
        row_no_in = self._row_with_cost(tuition_in_state=None)
        _patch_mcp(monkeypatch, {"data": [row_no_in], "substitution_applied": False})
        career_no_in = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            home_state="OH",
        )[0]
        assert career_no_in.net_price_annual_reference is None

        # Missing tuition_out_of_state
        row_no_out = self._row_with_cost(tuition_out_of_state=None)
        _patch_mcp(monkeypatch, {"data": [row_no_out], "substitution_applied": False})
        career_no_out = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            home_state="OH",
        )[0]
        assert career_no_out.net_price_annual_reference is None

        # Both missing
        row_neither = self._row_with_cost(
            tuition_in_state=None, tuition_out_of_state=None
        )
        _patch_mcp(
            monkeypatch, {"data": [row_neither], "substitution_applied": False}
        )
        career_neither = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            home_state="OH",
        )[0]
        assert career_neither.net_price_annual_reference is None

    # ── P1: Adjustment helper edge cases ──────────────────────────────

    def test_adjustment_helper_edge_cases(self):
        """Direct unit tests of _adjust_net_price_for_residency for
        degenerate inputs: gap <= 0, missing school_state, missing
        institution_control."""
        adjust = stat_engine._adjust_net_price_for_residency

        # Gap is zero (in-state == out-of-state) — no adjustment.
        result = adjust(
            net_price_annual=14_200.0,
            tuition_in_state=20_000.0,
            tuition_out_of_state=20_000.0,
            institution_control="Public",
            home_state="OH",
            school_state="IN",
        )
        assert result == 14_200.0

        # Negative gap (out-of-state < in-state, degenerate data).
        result = adjust(
            net_price_annual=14_200.0,
            tuition_in_state=25_000.0,
            tuition_out_of_state=20_000.0,
            institution_control="Public",
            home_state="OH",
            school_state="IN",
        )
        assert result == 14_200.0

        # Missing school_state — can't determine residency.
        result = adjust(
            net_price_annual=14_200.0,
            tuition_in_state=9_800.0,
            tuition_out_of_state=21_400.0,
            institution_control="Public",
            home_state="OH",
            school_state=None,
        )
        assert result == 14_200.0

        # Missing institution_control — can't determine public/private.
        result = adjust(
            net_price_annual=14_200.0,
            tuition_in_state=9_800.0,
            tuition_out_of_state=21_400.0,
            institution_control=None,
            home_state="OH",
            school_state="IN",
        )
        assert result == 14_200.0

        # net_price_annual is None — returns None.
        result = adjust(
            net_price_annual=None,
            tuition_in_state=9_800.0,
            tuition_out_of_state=21_400.0,
            institution_control="Public",
            home_state="OH",
            school_state="IN",
        )
        assert result is None

    # ── P1: recompute_for_sliders uses net_price_annual (now adjusted) ──

    def test_recompute_for_sliders_uses_published_cost(self, monkeypatch):
        """published_cost_4yr persists on CareerOutcome, so
        recompute_for_sliders reads it directly when the slider moves —
        no sidecar fields needed.

        Per the 2026-05-02 cost-anchor change, the slider-driven
        modeled_total_debt is published_cost_4yr × loan_pct. The OOS
        premium is baked into published_cost_4yr at build time, so
        sliding loan_pct correctly preserves the residency premium.
        """
        row = self._row_with_cost()
        _patch_mcp(monkeypatch, {"data": [row], "substitution_applied": False})

        # Build with out-of-state adjustment.
        outcomes = stat_engine.compute_pentagon(
            unitid=151351,
            cipcode="52.14",
            student_major=None,
            loan_pct=1.0,
            home_state="OH",
        )
        career = outcomes[0]
        # OOS public: published_cost_4yr = (22,800 + 11,600) × 4 = 137,600.
        assert career.published_cost_4yr == 137_600.0

        # Now rescore with a different loan_pct via the slider path.
        rescored = stat_engine.recompute_for_sliders(
            career,
            original_effort="balanced",
            new_effort="balanced",
            new_loan_pct=0.5,
        )

        # modeled_total_debt = published_cost_4yr × loan_pct.
        # 137,600 × 0.5 = 68,800.
        assert rescored.modeled_total_debt == 137_600.0 * 0.5

        # Loans boss at 50% financing still reflects the OOS premium —
        # 68,800 / 63,371 = 1.086 → equiv ROI ~5 → boss 6.
        assert rescored.bosses.loans is not None
        assert rescored.bosses.loans >= 5
