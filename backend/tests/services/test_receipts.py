"""Tests for the inline provenance receipts.

Plan: ~/.claude/plans/why-are-we-still-jaunty-curry.md. The ROI receipt
now renders in a single cost-based path: it always shows the 4-year cost
(net_price_annual × 4 when available, or debt_median as an approximation
fallback) alongside the financing context (modeled_total_debt +
financed_dte), and labels the cost basis explicitly via roi_cost_basis.
"""

from __future__ import annotations

from app.models.career import BossScores, CareerOutcome, PentagonStats
from app.services import receipts


def _career(
    *,
    roi: int | None = 6,
    net_price_annual: float | None = None,
    cost_of_attendance_annual: float | None = None,
    modeled_total_debt: float | None = None,
    debt_median_reference: float | None = None,
    debt_median: float | None = None,
    earnings_1yr_median: float | None = None,
    institution_control: str | None = None,
    debt_to_earnings_annual: float | None = None,
    roi_cost_basis: str | None = None,
    financed_dte: float | None = None,
) -> CareerOutcome:
    return CareerOutcome(
        unitid=151801,
        institution_name="Indiana State University",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-1131",
        occupation_title="Fundraisers",
        net_price_annual=net_price_annual,
        cost_of_attendance_annual=cost_of_attendance_annual,
        modeled_total_debt=modeled_total_debt,
        debt_median_reference=debt_median_reference,
        debt_median=debt_median,
        earnings_1yr_median=earnings_1yr_median,
        debt_to_earnings_annual=debt_to_earnings_annual,
        institution_control=institution_control,
        roi_cost_basis=roi_cost_basis,  # type: ignore[arg-type]
        financed_dte=financed_dte,
        stats=PentagonStats(ern=7, roi=roi, res=5, grw=6, hmn=6),
        bosses=BossScores(ai=6, loans=5, market=6, burnout=5, ceiling=5),
    )


class TestReceiptCostBreakdown:
    """Cost-based ROI receipt — one path, labeled by roi_cost_basis."""

    def test_cost_of_attendance_basis_renders_4yr_cost(self):
        career = _career(
            roi=6,
            net_price_annual=14_200.0,
            cost_of_attendance_annual=22_800.0,
            modeled_total_debt=14_200.0 * 4.0 * 0.75,
            debt_median_reference=19_500.0,
            debt_median=19_500.0,
            earnings_1yr_median=48_000.0,
            institution_control="Public",
            debt_to_earnings_annual=(14_200.0 * 4.0) / 48_000.0,
            roi_cost_basis="cost_of_attendance",
            financed_dte=(14_200.0 * 4.0 * 0.75) / 48_000.0,
        )
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=0.75)
        roi_line = next(line for line in lines if line.startswith("ROI "))

        # School + control
        assert "Indiana State University" in roi_line
        assert "Public" in roi_line
        # Cost basis: 4-year cost of attendance surfaced.
        assert "$14,200" in roi_line  # net_price_annual
        assert "$22,800" in roi_line  # cost_of_attendance_annual
        assert "$56,800" in roi_line  # 14_200 × 4
        # Earnings + ROI DTE.
        assert "$48,000" in roi_line
        assert "ROI DTE" in roi_line
        # Financing context.
        assert "75%" in roi_line  # loan coverage
        assert "$42,600" in roi_line  # modeled_total_debt (14_200 × 4 × 0.75)
        assert "Financed DTE" in roi_line
        # Median reference still cited for comparison.
        assert "$19,500" in roi_line
        # Source attribution includes institution level.
        assert "College Scorecard" in roi_line
        assert "Institution Level" in roi_line

    def test_debt_median_basis_surfaces_approximation(self):
        """No net_price → receipt labels cost basis as approximation."""
        career = _career(
            roi=6,
            net_price_annual=None,
            modeled_total_debt=19_500.0,
            debt_median=19_500.0,
            debt_median_reference=19_500.0,
            earnings_1yr_median=48_000.0,
            debt_to_earnings_annual=19_500.0 / 48_000.0,
            roi_cost_basis="debt_median",
            financed_dte=19_500.0 / 48_000.0,
        )
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        roi_line = next(line for line in lines if line.startswith("ROI "))

        # Cost basis labeled as approximation, net price omitted.
        assert "median graduate debt" in roi_line.lower()
        assert "approximation" in roi_line.lower()
        assert "$19,500" in roi_line
        # Earnings + DTE still shown.
        assert "$48,000" in roi_line
        # Institution-level fields must NOT appear.
        assert "Net price per" not in roi_line
        assert "Institution Level" not in roi_line
        assert "Field of Study" in roi_line

    def test_roi_receipt_wording_constant_across_loan_pct(self):
        """The ROI DTE wording is cost-based and loan_pct-agnostic."""
        base = dict(
            roi=6,
            net_price_annual=14_200.0,
            earnings_1yr_median=48_000.0,
            debt_to_earnings_annual=(14_200.0 * 4.0) / 48_000.0,
            roi_cost_basis="cost_of_attendance",
        )
        c_low = _career(**base, modeled_total_debt=0.0, financed_dte=0.0)
        c_low_lines = receipts.stats_receipt(c_low, effort="balanced", loan_pct=0.0)
        c_high = _career(
            **base,
            modeled_total_debt=14_200.0 * 4.0,
            financed_dte=(14_200.0 * 4.0) / 48_000.0,
        )
        c_high_lines = receipts.stats_receipt(
            c_high, effort="balanced", loan_pct=1.0
        )
        low_roi = next(line for line in c_low_lines if line.startswith("ROI "))
        high_roi = next(line for line in c_high_lines if line.startswith("ROI "))
        # The cost-basis + ROI DTE substring must be identical in both.
        low_cost_chunk = low_roi.split("Loan coverage")[0]
        high_cost_chunk = high_roi.split("Loan coverage")[0]
        assert low_cost_chunk == high_cost_chunk
