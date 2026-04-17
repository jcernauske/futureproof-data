# Cost-Based ROI (v2) — Completion Report

**Status:** ✅ COMPLETE (2026-04-17)
**Spec:** `docs/specs/roi-formula-cost-of-attendance.md`
**Plan:** `~/.claude/plans/why-are-we-still-jaunty-curry.md`
**Dependency:** `raw-ingest-college-scorecard-institution` ✅ COMPLETE

## The complaint

> *"A Special Ed program at Illinois State shows projected debt of $9,750 against a $43,480 salary, with the narrative declaring 'a massive ROI victory'... why are we still using median debt for the ROI calculation?"*

The `$9,750` was `debt_median × loan_pct = $19,500 × 50%` — the classic legacy scaling formula that predates the institution-level cost ingest. The real 4-year cost of attending Illinois State for that program is `$18,996 × 4 = $75,984`.

## What shipped

ROI is now **fully decoupled from financing**:

- **ROI (pentagon stat):** `DTE = (net_price_annual × 4) / earnings_1yr_median`. Fallback to `debt_median / earnings_1yr_median` when no institution cost. **loan_pct plays no role.**
- **Student Loans Boss:** `modeled_total_debt = net_price × 4 × loan_pct`; `financed_dte = modeled_total_debt / earnings`; `boss_loans = 11 − compute_stat_roi(financed_dte)`. **loan_pct drives this.**

Two students at the same school see the same ROI; only the Loans Boss difficulty scales with financing.

## Illinois State Special Ed — before vs. after

| Knob | Before (legacy scaling) | After (v2 cost-based) |
|------|-------------------------|-----------------------|
| Cost basis | $19,500 debt_median | $75,984 (net_price × 4) |
| DTE at 50% loan_pct | 0.225 | **ROI DTE: 1.748** (financing-independent) |
| **stat_roi** | ~9 (excellent / "victory") | **3** (challenging) |
| Loans boss at 50% | trivial (auto-win) | Financed DTE 0.87 → hard fight |
| Narrative framing | "massive ROI victory" | "4-year cost $75,984 vs $43,480 salary — that's 1.7× annual salary in cost, challenging return" |

## Coverage after materialization

**`consumable.career_outcomes` (69,947 rows):**
- `roi_cost_basis = cost_of_attendance`: 34.5%
- `roi_cost_basis = debt_median`: 1.3%
- `roi_cost_basis = none`: 64.2% (no earnings ∧ no cost — ROI genuinely unavailable)

**`consumable.program_career_paths` (626,406 rows):**
- `roi_cost_basis = cost_of_attendance`: 40.5%
- `roi_cost_basis = debt_median`: 1.9%
- `roi_cost_basis = none`: 57.6%

## Files changed

**Gold (data pipeline):**
- `src/gold/college_scorecard_career_outcomes.py` — DTE formula rewrite, `roi_cost_basis` column (field 38), `--overwrite` CLI flag.
- `src/gold/futureproof_engine.py` — PCP schema extended 44 → 52 columns to thread all institution cost fields plus `roi_cost_basis` through.
- `src/mcp_server/futureproof_server.py` — `roi_cost_basis` added to the `get_career_paths` response fields.

**Backend:**
- `backend/app/models/career.py` — `RoiCostBasis` Literal; `roi_cost_basis` + `financed_dte` on `CareerOutcome`.
- `backend/app/services/stat_engine.py` — `_compute_roi_with_cost` split into `_derive_roi` (loan_pct-independent) and `_derive_loans_boss` (loan_pct-aware).
- `backend/app/services/receipts.py` — RICH + LEGACY ROI receipt paths merged into one cost-based render; shows ROI DTE and Financed DTE separately.
- `backend/app/services/boss_fights.py` — ROI narrative is cost-only; Loans Boss narrative uses `financed_dte` + `modeled_total_debt`; `_BOSS_INSTRUCTIONS["loans"]` clarifies the fight is about financing, not ROI.

**Frontend:**
- `frontend/src/data/statExplanations.ts` — ROI blurb rewritten.
- `frontend/src/components/CareerDetail.tsx` — Single-path cost-based `RoiReceipt`.
- `frontend/src/components/school/EffortLoansPanel.tsx` — `LOAN_IMPACT` copy describes Loans Boss impact only.
- `frontend/src/types/build.ts` — Added `roi_cost_basis` + `financed_dte`.

**Governance:**
- PRD `docs/futureproof_hackathon_prd_v8.md` — ROI tagline updated; loan slider row clarifies ROI is financing-agnostic.

**Tests:**
- `backend/tests/services/test_stat_engine.py` — `TestLoanPct` rewritten (ROI independent of loan_pct; Loans Boss scales).
- `backend/tests/services/test_boss_fights.py` — `TestStatExplainerRoiNarrative` replaces `TestStatExplainerDebtDisplay`.
- `backend/tests/services/test_receipts.py` — `TestReceiptCostBreakdown` replaces `TestReceiptIncludesCostBreakdown`.
- `tests/gold/test_futureproof_engine.py` — PCP schema column count 40 → 52.
- `tests/gold/test_college_scorecard_career_outcomes.py` — career_outcomes column count 37 → 38.
- `frontend/src/components/CareerDetail.test.tsx`, `EffortLoansPanel.test.tsx` — updated for new copy.

## Verification

| Check | Result |
|-------|--------|
| Backend pytest | **302 / 302** ✅ |
| Pipeline pytest | 1669 pass / **2 pre-existing `debt_p25` failures** in test_get_career_paths + test_get_school_programs (unrelated; confirmed by stashing changes) |
| Frontend vitest | 323 pass / **2 pre-existing ProfileScreen failures** (unrelated) |
| Ruff (pipeline + backend) | clean on touched files (pre-existing warnings on untouched code only) |
| TypeScript (frontend) | clean |
| Gold materialization | career_outcomes + program_career_paths + career_branches re-promoted (overwrite) |
| User-reported case | Illinois State Special Ed: ROI **3/10** across all slider positions; financed DTE scales with slider |

## Design note — Why fully decouple

The v1 of this spec (2026-04-14) kept `loan_pct` multiplied into the ROI numerator. That was a smaller change but left the conceptual flaw intact: a student on a full scholarship at an expensive school would still see a different ROI than a student at the same school who financed everything. The economics of the program are the same; the financing differs. v2 models that correctly — ROI is a property of the program, Loans Boss is a property of the financing plan.

*— End of report —*
