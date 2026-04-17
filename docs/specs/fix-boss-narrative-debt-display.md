# Bugfix: Boss Fight Narrative Shows debt_median Instead of Modeled Debt

## Claude Code Prompt

```
Read and implement the spec at docs/specs/fix-boss-narrative-debt-display.md

The ROI calculation in stat_engine.py correctly uses net_price_annual × 4 × loan_pct
when institution-level cost data is available, but the narrative generation in
boss_fights.py still displays debt_median in all cases. This creates a disconnect
where the student sees "Your $19,500 debt" (median grad debt) when their actual
modeled debt from the cost-of-attendance formula might be $45,000.

Key changes:
1. backend/app/services/boss_fights.py — update stat_explainer() to prefer modeled_total_debt
2. backend/app/services/boss_fights.py — update _boss_context() loans block (already partially correct)
3. backend/tests/services/test_boss_fights.py — add coverage for both code paths

After implementing, run full test suite (pytest + ruff + mypy). Report any failures.
```

---

**Spec Status:** COMPLETE
**Created:** 2026-04-16
**Updated:** 2026-04-16
**Priority:** High
**Related Specs:** raw-ingest-college-scorecard-institution.md, roi-formula-cost-of-attendance.md

---

## §1 Problem

### Symptom

Boss fight narratives (especially Fight Student Loans) display the **median debt of past graduates** (`debt_median`) instead of the **student's modeled debt** (`modeled_total_debt`) derived from the cost-of-attendance formula.

Example bad output:
> "You crushed the Student Loan boss with a massive ROI victory. Your **$19,500 debt** is only 45% of your $43,480 starting salary..."

The $19,500 is `debt_median` — what the median graduate of this program borrowed. But if the student is attending a school with `net_price_annual = $25,000` and `loan_pct = 0.75`, their **actual modeled debt** is:

```
$25,000 × 4 years × 0.75 = $75,000
```

The ROI stat and boss score are calculated correctly using $75,000, but the narrative cites $19,500.

### Root Cause

`stat_engine.py` correctly implements the cost-of-attendance formula in `_compute_roi_with_cost()`:

```python
# Cost-of-attendance branch (preferred).
if net_price_annual is not None and earnings_1yr_median:
    modeled_debt = float(net_price_annual) * 4.0 * float(loan_pct)
    ...
```

But `boss_fights.py`'s `stat_explainer()` function (lines 60-100) unconditionally references `career.debt_median`:

```python
if career.debt_median is not None and career.earnings_1yr_median is not None:
    ...
    debt = fmt_dollars(career.debt_median)  # <-- Always uses debt_median
```

### Impact

- **Students see wrong debt figures** in coach narratives
- **Cognitive dissonance** between displayed debt and ROI score
- **Undermines trust** in the product's data accuracy
- Affects: `stat_explainer()`, Fight Student Loans narrative, any Gemma prompt that references debt

---

## §2 Solution

### Principle

- When `career.modeled_total_debt` is available (cost-of-attendance formula was used), display it as "your debt"
- Keep `career.debt_median` / `career.debt_median_reference` as context: "median grad borrowed $X"
- When `modeled_total_debt` is None (legacy fallback path), continue using `debt_median × loan_pct` as before

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/boss_fights.py` | Modify | Update `stat_explainer()` and `_boss_context()` |
| `backend/tests/services/test_boss_fights.py` | Modify | Add test coverage for both code paths |

### Code Changes

#### `boss_fights.py` — `stat_explainer()` (around line 60)

**Current:**
```python
# ROI — return on investment
if s.roi is not None:
    roi_ctx = ""
    if career.debt_median is not None and career.earnings_1yr_median is not None:
        loan_pct = career.loan_pct
        pct_label = f"{int(loan_pct * 100)}%"
        debt = fmt_dollars(career.debt_median)
        earn = fmt_dollars(career.earnings_1yr_median)
        # ...
        if loan_pct >= 1.0:
            roi_ctx = (
                f" The median graduate debt is {debt} vs. "
                f"{earn} starting salary."
            )
        elif loan_pct <= 0.0:
            roi_ctx = (
                f" No loans — {earn} starting salary "
                f"is all yours."
            )
        else:
            roi_ctx = (
                f" Covering {pct_label} of the median "
                f"{debt} debt vs. {earn} starting salary."
            )
```

**Fixed:**
```python
# ROI — return on investment
if s.roi is not None:
    roi_ctx = ""
    earn = fmt_dollars(career.earnings_1yr_median) if career.earnings_1yr_median else None

    # Cost-of-attendance path (preferred) — student's modeled debt from
    # net_price_annual × 4 × loan_pct.
    if career.modeled_total_debt is not None and earn:
        modeled = fmt_dollars(career.modeled_total_debt)
        loan_pct = career.loan_pct

        if loan_pct <= 0.0:
            roi_ctx = f" No loans — {earn} starting salary is all yours."
        else:
            roi_ctx = f" Your projected debt is {modeled} vs. {earn} starting salary."
            # Add median grad context if available
            ref_debt = career.debt_median_reference or career.debt_median
            if ref_debt is not None:
                roi_ctx += f" (Median grad borrowed {fmt_dollars(ref_debt)}.)"

    # Legacy fallback — debt_median × loan_pct when no institution cost data.
    elif career.debt_median is not None and earn:
        loan_pct = career.loan_pct
        pct_label = f"{int(loan_pct * 100)}%"
        debt = fmt_dollars(career.debt_median)

        if loan_pct >= 1.0:
            roi_ctx = f" The median graduate debt is {debt} vs. {earn} starting salary."
        elif loan_pct <= 0.0:
            roi_ctx = f" No loans — {earn} starting salary is all yours."
        else:
            scaled = fmt_dollars(career.debt_median * loan_pct)
            roi_ctx = f" At {pct_label} loans, your debt is ~{scaled} vs. {earn} starting salary."

    # Debt range context (applies to both paths)
    if career.debt_p25 is not None and career.debt_p75 is not None:
        debt_range = (
            f" Graduates typically owe {fmt_dollars(career.debt_p25)} to "
            f"{fmt_dollars(career.debt_p75)}."
        )
        roi_ctx += debt_range

    # DTE interpretation
    if career.debt_to_earnings_annual is not None:
        dte = career.debt_to_earnings_annual
        if dte <= 0.5:
            roi_ctx += " Very manageable."
        elif dte <= 1.0:
            roi_ctx += " About one year of earnings."
        else:
            roi_ctx += f" That's {dte:.1f}x annual salary in debt."

    lines.append(
        f"- ROI {s.roi}/10 (Return on Investment): How quickly you can "
        f"pay off your student loans with what you'll earn.{roi_ctx}"
    )
```

#### `boss_fights.py` — `_boss_context()` loans block (around line 140)

The `_boss_context()` function is **already partially correct** — it checks for `career.net_price_annual` and `career.modeled_total_debt`. However, it should also include the median grad reference for context consistency.

**Current (already good, minor enhancement):**
```python
if career.net_price_annual is not None:
    parts.append(
        f"School net price: "
        f"{fmt_dollars(career.net_price_annual)}/year"
    )
    if career.modeled_total_debt is not None:
        parts.append(
            f"Student's modeled 4-year debt: "
            f"{fmt_dollars(career.modeled_total_debt)}"
        )
    ref_debt = (
        career.debt_median_reference
        if career.debt_median_reference is not None
        else career.debt_median
    )
    if ref_debt is not None:
        parts.append(
            f"Median debt of graduates from this program: "
            f"{fmt_dollars(ref_debt)}"
        )
```

**No change needed here** — this block is already correct. The issue is isolated to `stat_explainer()`.

### Edge Cases

| Scenario | `modeled_total_debt` | `debt_median` | Behavior |
|----------|---------------------|---------------|----------|
| Institution cost data available | $75,000 | $19,500 | Display "Your projected debt is $75,000" + "(Median grad borrowed $19,500.)" |
| No institution cost data, full loans | None | $19,500 | Display "The median graduate debt is $19,500" |
| No institution cost data, 50% loans | None | $19,500 | Display "At 50% loans, your debt is ~$9,750" |
| No loans (loan_pct = 0) | $0 | $19,500 | Display "No loans — $X starting salary is all yours." |
| Both debt fields null | None | None | Skip debt context entirely |

---

## §3 Testing

### Test Scenarios

| # | Scenario | Input | Expected Output Contains |
|---|----------|-------|-------------------------|
| 1 | Cost-of-attendance path | `modeled_total_debt=75000`, `debt_median=19500`, `loan_pct=0.75` | "Your projected debt is $75,000" AND "(Median grad borrowed $19,500.)" |
| 2 | Legacy path, full loans | `modeled_total_debt=None`, `debt_median=19500`, `loan_pct=1.0` | "The median graduate debt is $19,500" |
| 3 | Legacy path, partial loans | `modeled_total_debt=None`, `debt_median=20000`, `loan_pct=0.5` | "At 50% loans, your debt is ~$10,000" |
| 4 | No loans | `loan_pct=0.0` | "No loans" |
| 5 | Both debt fields null | `modeled_total_debt=None`, `debt_median=None` | No debt context in ROI explanation |

### Test File Location

`backend/tests/services/test_boss_fights.py`

### Test Implementation

```python
import pytest
from app.models.career import CareerOutcome, PentagonStats, BossScores
from app.services.boss_fights import stat_explainer


def _make_career(
    *,
    modeled_total_debt: float | None = None,
    debt_median: float | None = None,
    debt_median_reference: float | None = None,
    earnings_1yr_median: float | None = 50000,
    loan_pct: float = 1.0,
    roi: int = 7,
) -> CareerOutcome:
    """Factory for minimal CareerOutcome with debt fields."""
    return CareerOutcome(
        unitid=100000,
        institution_name="Test University",
        cipcode="52.0201",
        program_name="Business Administration",
        soc_code="11-1021",
        occupation_title="General Manager",
        earnings_1yr_median=earnings_1yr_median,
        debt_median=debt_median,
        debt_median_reference=debt_median_reference,
        modeled_total_debt=modeled_total_debt,
        loan_pct=loan_pct,
        stats=PentagonStats(ern=6, roi=roi, res=5, grw=6, hmn=7),
        bosses=BossScores(ai=5, loans=4, market=6, burnout=5, ceiling=6),
    )


class TestStatExplainerDebtDisplay:
    """Verify stat_explainer uses modeled_total_debt when available."""

    def test_cost_of_attendance_path_shows_modeled_debt(self):
        """When modeled_total_debt exists, display it as 'your debt'."""
        career = _make_career(
            modeled_total_debt=75000,
            debt_median=19500,
            loan_pct=0.75,
        )
        result = stat_explainer(career)

        assert "$75,000" in result, "Should display modeled debt"
        assert "Your projected debt" in result or "your debt" in result.lower()
        assert "$19,500" in result, "Should include median grad reference"
        assert "Median grad borrowed" in result or "median" in result.lower()

    def test_legacy_path_full_loans(self):
        """When no modeled_total_debt, fall back to debt_median."""
        career = _make_career(
            modeled_total_debt=None,
            debt_median=19500,
            loan_pct=1.0,
        )
        result = stat_explainer(career)

        assert "$19,500" in result
        assert "median graduate debt" in result.lower()

    def test_legacy_path_partial_loans(self):
        """Partial loans on legacy path should scale debt_median."""
        career = _make_career(
            modeled_total_debt=None,
            debt_median=20000,
            loan_pct=0.5,
        )
        result = stat_explainer(career)

        assert "$10,000" in result, "Should show scaled debt"
        assert "50%" in result

    def test_no_loans_path(self):
        """Zero loans should show 'no loans' message."""
        career = _make_career(
            modeled_total_debt=0,
            debt_median=19500,
            loan_pct=0.0,
        )
        result = stat_explainer(career)

        assert "no loans" in result.lower()

    def test_both_debt_fields_null(self):
        """Missing debt data should not crash, skip debt context."""
        career = _make_career(
            modeled_total_debt=None,
            debt_median=None,
            loan_pct=1.0,
        )
        result = stat_explainer(career)

        # Should still have ROI line, just without debt context
        assert "ROI" in result
        # Should not contain dollar figures for debt
        assert "debt" not in result.lower() or "unavailable" in result.lower()
```

---

## §5 Architecture Review

**Status:** SKIPPED (lightweight spec — isolated bugfix in single file)

---

## §6 Implementation Log

**Status:** COMPLETE

| File | Change Summary |
|------|---------------|
| `backend/app/services/boss_fights.py` | Rewrote ROI block in `stat_explainer()`. Prefers `modeled_total_debt` when present (renders "Your projected debt is $X" and an optional "(Median grad borrowed $Y.)" reference when distinct from modeled). Legacy branch — used when stat_engine couldn't compute a modeled debt — keeps "median graduate debt" / "At N% loans, your debt is ~$X" phrasing. Debt range + DTE interpretation now share both paths. |
| `backend/tests/services/test_boss_fights.py` | Added `TestStatExplainerDebtDisplay` with 5 cases: cost-of-attendance path, legacy full loans, legacy partial loans, no loans, and both debt fields null. |

### Notes

- `_boss_context()` was already correct — no changes there.
- Added a guard so the median-grad reference is only appended when it's distinct from the modeled debt. Otherwise the full-loans legacy path (`modeled_total_debt = debt_median × 1.0`) would print the same number twice.
- The partial-loans legacy branch (`elif debt_median is not None`) is only reachable when `modeled_total_debt` is None. In production `stat_engine` populates `modeled_total_debt` whenever `debt_median` is available, so this elif is effectively dead code under normal flow — but it stays for defensive rendering when an outcome is constructed without stat_engine (tests, future callers).

---

## §7 Test Coverage

**Status:** COMPLETE

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_boss_fights.py` | `test_cost_of_attendance_path_shows_modeled_debt` | `modeled_total_debt=75000`, `debt_median=19500` → narrative cites $75,000 as projected debt and $19,500 as median grad reference |
| `backend/tests/services/test_boss_fights.py` | `test_legacy_path_full_loans` | `modeled_total_debt=None`, `debt_median=19500`, `loan_pct=1.0` → "median graduate debt is $19,500" |
| `backend/tests/services/test_boss_fights.py` | `test_legacy_path_partial_loans` | `modeled_total_debt=None`, `debt_median=20000`, `loan_pct=0.5` → "At 50% loans, your debt is ~$10,000" |
| `backend/tests/services/test_boss_fights.py` | `test_no_loans_path` | `loan_pct=0.0` → "No loans — $X starting salary is all yours." |
| `backend/tests/services/test_boss_fights.py` | `test_both_debt_fields_null` | No crash; no debt figures or debt phrasing in the ROI explanation. |

---

## §8 Code Review

**Status:** SKIPPED (lightweight spec)

---

## §9 Verification

**Status:** PASS (scoped to spec touch points)

| Check | Result |
|-------|--------|
| `ruff check .` | PASS — all checks passed |
| `mypy app/services/boss_fights.py` | PASS — no issues found |
| `mypy app/` (full tree) | 44 pre-existing errors in unrelated routers (`builds.py`, `branches.py`, `gauntlet.py`, etc.); **none touch boss_fights or this spec**. Not introduced by this fix. |
| `pytest` (full backend) | PASS — 285 passed, 0 failed |
| `pytest tests/services/test_boss_fights.py` | PASS — 38 passed (33 existing + 5 new) |

---

## §10 Discussion

```
[Reserved for agent discussion if needed]
```

---

## §11 Final Notes

**Human Review:** PENDING

### Why This Matters

The entire point of adding institution-level cost data was to give students a more accurate picture of **their** debt, not just what past grads borrowed. The ROI formula now uses `net_price_annual × 4 × loan_pct`, but the narrative still cites `debt_median`. This creates a jarring disconnect:

- Student sees ROI score of 4/10 (bad) based on $75K modeled debt
- Narrative says "Your $19,500 debt is very manageable!"
- Student is confused — which number is real?

Fixing the narrative to use `modeled_total_debt` completes the cost-of-attendance rollout and ensures the coach's explanation matches the actual calculation.

### Kaggle Writeup Angle

This fix demonstrates **data lineage integrity** — when we changed the ROI formula denominator, we traced all downstream consumers (narrative prompts, boss context blocks, stat explainers) to ensure consistency. The adversarial auditor pattern applies here: if the formula changed but the narrative didn't, students would receive misleading guidance.
