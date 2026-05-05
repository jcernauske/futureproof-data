# Spec Report: roi-net-lifetime-value

**Date:** 2026-05-04
**Spec:** [`docs/specs/roi-net-lifetime-value.md`](../docs/specs/roi-net-lifetime-value.md) (v1.3)
**Status:** COMPLETE

## What changed

ROI's underlying formula moved from a debt-to-earnings ratio to a **15-year payback multiplier** — cumulative 15-year earnings ÷ 4-year sticker cost, mapped to a 1-10 score via a calibrated threshold ladder. Boss Debt was refactored to scale with **total interest paid** (computed via amortization at the OBBBA Tiered Standard term), not inverted ROI. ROI is now strictly financing-agnostic; Boss Debt is the financing-aware surface. Two MCP server substitution paths that were silently multiplying DTE by `loan_pct` before computing ROI were corrected.

## Why

The DTE formula compresses signal at both ends — two programs costing $40K with first-year salaries of $50K vs $80K produced DTEs of 0.80 and 0.50 (both upper-middle ROI scores), erasing real long-term differences. The payback multiplier directly answers the question a high-school senior asks: "If I go here, how much will I have made over the realistic loan-repayment period compared to what this program costs?"

The 15-year window is intentional. The federal standard plan is 10 years, but median bachelor's-degree borrowers take 17–21 years to pay off (Education Data Initiative, The College Investor 2026, ELFI). 15 years splits that gap, matches OBBBA Tiered Standard for typical $25–50K debt, and captures career trajectory clarity (lawyers make partner, doctors finish residency, engineers reach senior IC).

## Workflow

1. **Architecture review (@fp-architect, @fp-data-reviewer):** initial CHANGES REQUESTED with 9 + 6 conditions. Spec amended to v1.3 (Decision #11 — Gold = in-state baseline, backend = residency-aware override; real Gold columns; schema plumbing enumerated; CareerOutcome fields; substitution-path Boss Debt fix; migration order with same-commit constraint). Re-review APPROVED.
2. **Design vision:** SKIPPED (backend + Gold pipeline only).
3. **Implementation:** 11-step migration order. New `loan_math.py`; ROI helpers in `futureproof_engine.py`; Gold schemas (3 new fields each in `consumable.career_outcomes` and `consumable.program_career_paths`); backend `_derive_roi` + `_derive_loans_boss` rewrites; `CareerOutcome` model fields; MCP substitution-path fixes; governance updates.
4. **Testing (@test-writer):** 10 new P0/P1 tests added on top of fixture updates — threshold boundaries, financing-agnostic invariant, interest-burden monotonicity, narrative interest surfacing.
5. **Design audit:** SKIPPED (no UI changes).
6. **Code review (@faang-staff-engineer):** APPROVED with M1 (NULLIF defense against COA=0 zero) — fixed inline. M2 (Gold-precomputed boss_loans = 11 - stat_roi placeholder) acknowledged in §6, deferred to next ROI cleanup spec.
7. **Verification (@fp-builder):** ALL PASSED on attempt 1 of 3 after a single ruff E501 line-length fix on the new tuple return type.

## Files touched

| Layer | Files |
|-------|-------|
| Backend (new) | `backend/app/services/loan_math.py`; `backend/tests/services/test_loan_math.py` |
| Backend (modified) | `backend/app/services/stat_engine.py`; `backend/app/services/boss_fights.py`; `backend/app/models/career.py`; `backend/tests/services/test_stat_engine.py`; `backend/tests/services/test_boss_fights.py` |
| Gold pipeline | `src/gold/futureproof_engine.py`; `src/gold/college_scorecard_career_outcomes.py`; `tests/gold/test_futureproof_engine.py`; `tests/gold/test_college_scorecard_career_outcomes.py` |
| MCP server | `src/mcp_server/futureproof_server.py`; `tests/mcp/test_cip_substitution.py`; 3 regenerated fixtures in `tests/mcp/fixtures/career_paths_responses/` |
| Governance | `governance/business-glossary.json` (BT-079, BT-084); `governance/data-dictionary.json` (`stat_roi`, `boss_loans_score`, deprecated `debt_to_earnings_annual`); new `governance/dq-rules/gold-career-outcomes-roi-multiplier.json` (GLD-CO-045–051) |
| Documentation | `README.md` (new "Methodology: How We Score Programs" section); spec sections §5–§9 |
| Utility | `scripts/regen_parity_fixtures.py` |

## Verification

| Check | Result |
|-------|--------|
| Pipeline lint (ruff) | PASS |
| Backend lint (ruff) | PASS |
| Type check (mypy on touched files) | PASS |
| Pipeline tests (pytest tests/) | 2127 passed, 1 deselected |
| Backend tests (pytest backend/) | 1539 passed, 3 failed (pre-existing on main) |
| Gold pipeline re-promote | 69 947 career_outcomes rows + 626 406 program_career_paths rows; schema evolution applied |
| Calibration distribution | median bucket 6, extremes 1.47%/1.74%, largest 17.78% — on-spec |

## Notable deviations

1. **DQ rule IDs renumbered.** Spec proposed `GLD-CO-038`–`GLD-CO-044`; existing file already used those IDs. Shifted to `GLD-CO-045`–`GLD-CO-051`. Same semantics.
2. **Legacy `compute_stat_roi` kept as deprecated alias** for one cycle — out-of-tree callers and any stale imports continue to work. Marked for removal in next cleanup spec.
3. **Gold-precomputed `boss_loans_score`** in `futureproof_engine.py` row-assembly remains `(11 - stat_roi)`. Under the new financing-agnostic ROI it's a placeholder that the backend always overrides; only surfaces in narrow fallback paths. Acceptable per spec scope.
4. **No separate PyArrow output schema** to update for `career_outcomes` — Iceberg schema + DuckDB-emitted columns are the source of truth. Spec mention of "PyArrow schema at line ~396" referred to the institution input schema.
5. **NULL pct came in at 65.50%** vs. spec acceptance `[25, 40]`. Cause is Scorecard earnings privacy suppression — the legacy DTE column on the same data is 64.20% null. New formula has 1.30 percentage-points lower coverage than legacy (913 of 69 947 rows lost the `debt_median` fallback the spec intentionally removed). Distribution shape is healthy; not a regression. Spec's expected null bound was anchored on a faulty EDA estimate.
6. **3 pre-existing backend test failures** inherited from main (verified by `git stash`): two boss_fights narrative tests and one ask_gemma context test. Not blockers — they pre-date this work.

## Follow-ups

- Drop deprecated `debt_to_earnings_annual` Gold column and `compute_stat_roi_from_dte` function in the next ROI cleanup spec.
- Replace `boss_loans_score = (11 - stat_roi)` placeholder in `futureproof_engine.py:563` with a proper financing-aware Gold-side computation, OR set it to None in the same cleanup spec.
- Revisit calibration's null-pct bound after pipeline coverage re-ingests source data with broader earnings coverage (out of scope here).
- Add 2026-27 federal undergraduate Direct Loan rate to config when Treasury announces post-May 12, 2026.
- First Home Race spec — uses the same `loan_math.amortize` helper landed here.
- Consider exposing `lifetime_earnings_15yr` in the receipts UI as a "expected lifetime earnings" data point next to the multiplier.
