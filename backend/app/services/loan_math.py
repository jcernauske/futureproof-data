"""Pure financing math. No I/O, no service dependencies. Used by Boss Debt,
First Home Race, and any other surface that needs amortization.

ROI itself is financing-agnostic and does NOT use this module — see
`docs/specs/roi-net-lifetime-value.md` Decision #1.
"""

from __future__ import annotations

DEFAULT_FEDERAL_RATE: float = 0.0639  # 2025-26 undergraduate Direct Loan rate


def repayment_term_months(loan_principal: float) -> int:
    """OBBBA Tiered Standard Plan term, in months, by balance.

    Tiers (effective for federal loans disbursed July 1, 2026+):
    - <$25K        -> 120 months (10 years)
    - $25K-$50K    -> 180 months (15 years)
    - $50K-$100K   -> 240 months (20 years)
    - $100K+       -> 300 months (25 years)
    """
    if loan_principal < 25_000:
        return 120
    if loan_principal < 50_000:
        return 180
    if loan_principal < 100_000:
        return 240
    return 300


def amortize(
    principal: float,
    annual_rate: float = DEFAULT_FEDERAL_RATE,
    term_months: int | None = None,
) -> tuple[float, float, float]:
    """Standard fixed-rate amortization.

    Returns (monthly_payment, total_repayment, total_interest).
    If `term_months` is None, computed from `principal` via
    `repayment_term_months`.
    """
    if term_months is None:
        term_months = repayment_term_months(principal)
    if principal <= 0 or term_months <= 0:
        return 0.0, 0.0, 0.0
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        monthly_payment = principal / term_months
    else:
        monthly_payment = (
            principal
            * (monthly_rate * (1 + monthly_rate) ** term_months)
            / ((1 + monthly_rate) ** term_months - 1)
        )
    total_repayment = monthly_payment * term_months
    total_interest = total_repayment - principal
    return monthly_payment, total_repayment, total_interest
