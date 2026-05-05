"""Tests for backend/app/services/loan_math.py.

Reference values computed independently against the standard PMT formula:
    M = P * (r * (1+r)^n) / ((1+r)^n - 1)
where r = monthly_rate, n = term_months.
"""

from __future__ import annotations

import math

import pytest

from app.services.loan_math import (
    DEFAULT_FEDERAL_RATE,
    amortize,
    repayment_term_months,
)


def test_repayment_term_tiers_below_25k() -> None:
    assert repayment_term_months(0) == 120
    assert repayment_term_months(10_000) == 120
    assert repayment_term_months(24_999.99) == 120


def test_repayment_term_tiers_25k_to_50k() -> None:
    assert repayment_term_months(25_000) == 180
    assert repayment_term_months(40_000) == 180
    assert repayment_term_months(49_999.99) == 180


def test_repayment_term_tiers_50k_to_100k() -> None:
    assert repayment_term_months(50_000) == 240
    assert repayment_term_months(75_000) == 240
    assert repayment_term_months(99_999.99) == 240


def test_repayment_term_tiers_100k_plus() -> None:
    assert repayment_term_months(100_000) == 300
    assert repayment_term_months(250_000) == 300
    assert repayment_term_months(1_000_000) == 300


def test_amortize_zero_principal() -> None:
    monthly, total, interest = amortize(0.0)
    assert monthly == 0.0
    assert total == 0.0
    assert interest == 0.0


def test_amortize_negative_principal() -> None:
    monthly, total, interest = amortize(-1000.0)
    assert monthly == 0.0
    assert total == 0.0
    assert interest == 0.0


def test_amortize_zero_term() -> None:
    monthly, total, interest = amortize(10_000.0, term_months=0)
    assert monthly == 0.0
    assert total == 0.0
    assert interest == 0.0


def test_amortize_zero_rate_falls_back_to_principal_over_term() -> None:
    monthly, total, interest = amortize(12_000.0, annual_rate=0.0, term_months=120)
    assert monthly == pytest.approx(100.0)
    assert total == pytest.approx(12_000.0)
    assert interest == pytest.approx(0.0)


def _pmt(principal: float, annual_rate: float, term_months: int) -> float:
    """Standard PMT formula — independent reference for test assertions."""
    r = annual_rate / 12
    return principal * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)


def test_amortize_20k_at_default_rate_120mo() -> None:
    """$20,000 at 6.39% for 120 months. Tier-default term = 120."""
    monthly, total, interest = amortize(20_000.0)
    expected_monthly = _pmt(20_000.0, DEFAULT_FEDERAL_RATE, 120)
    assert monthly == pytest.approx(expected_monthly, rel=1e-9)
    assert total == pytest.approx(monthly * 120, rel=1e-9)
    assert interest == pytest.approx(total - 20_000.0, rel=1e-9)
    assert interest > 6_000.0
    assert interest < 8_000.0


def test_amortize_40k_at_default_rate_180mo() -> None:
    """$40,000 at 6.39% for 180 months (15 years). Tier-default term = 180."""
    monthly, total, interest = amortize(40_000.0)
    expected_monthly = _pmt(40_000.0, DEFAULT_FEDERAL_RATE, 180)
    assert monthly == pytest.approx(expected_monthly, rel=1e-9)
    assert total == pytest.approx(monthly * 180, rel=1e-9)
    assert interest == pytest.approx(total - 40_000.0, rel=1e-9)
    assert interest > 22_000.0
    assert interest < 24_000.0


def test_amortize_75k_at_default_rate_240mo() -> None:
    """$75,000 at 6.39% for 240 months (20 years)."""
    monthly, total, interest = amortize(75_000.0)
    expected_monthly = _pmt(75_000.0, DEFAULT_FEDERAL_RATE, 240)
    assert monthly == pytest.approx(expected_monthly, rel=1e-9)
    assert total == pytest.approx(monthly * 240, rel=1e-9)
    assert interest == pytest.approx(total - 75_000.0, rel=1e-9)


def test_amortize_150k_at_default_rate_300mo() -> None:
    """$150,000 at 6.39% for 300 months (25 years).

    Term auto-selected: 150K is in the 100K+ tier.
    """
    monthly, total, interest = amortize(150_000.0)
    assert repayment_term_months(150_000.0) == 300
    expected_monthly = _pmt(150_000.0, DEFAULT_FEDERAL_RATE, 300)
    assert monthly == pytest.approx(expected_monthly, rel=1e-9)
    assert math.isfinite(total)
    assert math.isfinite(interest)
    assert interest > 0.0


def test_amortize_explicit_term_overrides_tier() -> None:
    """Passing term_months=120 to a $40K principal should use 120, not the
    tier default of 180."""
    monthly_explicit, _, _ = amortize(40_000.0, term_months=120)
    monthly_default, _, _ = amortize(40_000.0)
    assert monthly_explicit > monthly_default


def test_amortize_higher_principal_higher_total_interest() -> None:
    """Boss Debt monotonicity sanity check: larger loans pay more interest."""
    _, _, interest_low = amortize(20_000.0)
    _, _, interest_med = amortize(40_000.0)
    _, _, interest_high = amortize(80_000.0)
    assert interest_low < interest_med < interest_high
