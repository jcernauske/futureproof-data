## Staff Engineer Review

### Date: 2026-04-09
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is production-quality work. The cross-source join chain is correctly implemented, stat derivations match the spec precisely, dedup handles the CIP prefix fan-out correctly, and all three golden dataset chains verify against the warehouse down to exact record_id hashes. 626,406 rows in program_career_paths and 15,944 in career_branches, both with zero grain duplicates. The adversarial auditor caught hallucinated golden dataset values and they were replaced with real warehouse queries -- that is exactly how the process is supposed to work. I would put my name on this.

### Code Quality

**`src/gold/futureproof_engine.py`** -- Clean separation of concerns. Pure functions for stat derivation (`compute_stat_ern`, `compute_stat_roi`, `compute_boss_ceiling`, `derive_match_quality`, `derive_overall_confidence`) are individually testable and match spec formulas exactly. The `_round_half_up` function exists because Python's `round()` uses banker's rounding while the spec assumes standard rounding -- the WHY comment is there and justified. The SQL CTE approach for the join chain with DuckDB is the right call for this cardinality (626K rows after fan-out). The `derive_pcp_rows` function does the SQL join, then post-processes in Python for stat computation -- this is a reasonable split between set-based join logic and row-level derivation. `derive_br_rows` uses dict lookups for the simpler 1:1 enrichment pattern -- appropriate given the smaller cardinality. Empty table handling with explicit PyArrow schema stubs is defensive but not over-engineered. No god functions. No abstraction astronautics. The `_read_table` helper is simple and does one thing.

**One design note (not blocking):** The `derive_pcp_rows` function is ~120 lines including the SQL constant. It does join + dedup + stat computation + quality derivation. This is at the upper bound of what I'd accept in a single function, but each step is clearly delineated with comments and the alternative (splitting into 5 functions that pass intermediate state) would be worse.

### Test Quality

51 tests, well above the 15 minimum for Consumable zone. These are real tests:

- **Stat derivation tests** assert exact computed values with math shown in comments (e.g., `0.6*0.45 + 0.4*0.75 = 0.57, ROUND(1 + 9*0.57) = 6`). Not `assert result > 0`.
- **Boundary tests** cover min/max inputs (ERN 1 and 10), floor/cap behavior (ROI at DTE 0.10 and 5.0), and piecewise midpoint (ROI at DTE 1.125 = 7).
- **Null propagation tests** verify that null inputs produce null outputs through the entire derivation chain, not just at the function level.
- **CIP prefix join tests** verify the actual join behavior: prefix match works, fan-out produces multiple rows, same-SOC dedup works, no-match exclusion works.
- **Occupation title fallback** tests the 4-level COALESCE chain (BLS -> O*NET -> crosswalk -> "Unknown").
- **Career branches tests** verify delta computation including sign correctness (negative wage_delta when target pays less), null propagation for deltas when one side is missing, and `branch_has_full_data` flag logic.

No test theater detected. Every assertion validates a specific expected value.

### Spec Compliance

Full compliance. Checked every success criterion:

- [x] Both tables exist with correct schemas (40 and 24 columns)
- [x] 4-digit CIP prefix join (LEFT(cipcode, 5)) -- verified in SQL and tested
- [x] Joins all 4 source tables via crosswalk
- [x] Five stats: ERN (60/40 blend), ROI (piecewise), GRW (carried), HMN (carried), RES (null placeholder)
- [x] Boss scores: Loans (11-ROI), Market (carried), Burnout (carried), Ceiling (10-9*pct), AI (null placeholder)
- [x] Career branches enriched with source/target stats and deltas
- [x] stats_available_count and bosses_available_count accurate
- [x] match_quality derived from join flags (NOT from crosswalk Silver has_scorecard_match)
- [x] overall_confidence correctly derived per spec
- [x] Grain integrity: zero duplicates on both tables
- [x] DQ: 43/45 pass, all P0 pass, 1 P1 warning (GLD-FE-040), 1 deferred and fixed
- [x] Golden dataset with 3 verification chains, all matching warehouse values exactly

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| ISU Business Admin -> Gen & Ops Mgrs | stat_ern | 2026 | 5 | 5 (manual calc: ROUND(1+9*(0.6*0.125+0.4*0.890))=ROUND(4.88)=5) | Golden dataset chain 1 | YES |
| ISU Business Admin -> Gen & Ops Mgrs | stat_roi | 2026 | 8 | 8 (DTE=0.627, band [0.25,0.75], frac=0.755, 10-1.51=8.49->8) | Golden dataset chain 1 | YES |
| Daemen Natural Sciences -> Phys Scientists | stat_roi | 2026 | 1 | 1 (DTE=4.669 > 4.0, floor) | Golden dataset chain 2 | YES |
| Daemen Natural Sciences -> Phys Scientists | boss_loans_score | 2026 | 10 | 10 (11-1=10) | Golden dataset chain 2 | YES |
| Chief Executives -> Financial Managers | wage_delta | 2026 | -44720.0 | -44720.0 (161700-206420) | Golden dataset chain 3 | YES |
| Financial Analysts (13-2051) | median_annual_wage | BLS 2024 | 101350.0 | ~$99,890-$101,350 | BLS OOH | YES |
| General & Ops Managers (11-1021) | median_annual_wage | BLS 2024 | 102950.0 | ~$101,280-$102,950 | BLS OOH | YES |
| Chief Executives (11-1011) | median_annual_wage | BLS 2024 | 206420.0 | ~$206,420 | BLS OOH | YES |

All 8 spot-check values match. No Apple FY2010 revenue surprises here.

### Pipeline Gate

`pipeline_gate validate` reports 5 issues. None are code quality problems:

1. **4 hash mismatches** on conceptual model, logical model, DQ rules, and DQ scorecard. These artifacts were legitimately modified during the governance-reviewer-post fix cycle (model statuses updated, scorecard regenerated). The pipeline gate hashes were recorded before the fixes. The implementing agent should re-stamp these steps after fixes are applied. This is a process gap in the pipeline gate workflow, not a data or code issue.

2. **Golden dataset format**: Uses `verification_chains` key instead of `values`/`records` that the gate expects. The golden dataset contains 3 detailed verification chains with exact expected values, all of which match the warehouse. The implementing agent should add a `values` key that the gate recognizes, or the gate should be updated to accept `verification_chains`.

Neither issue affects data correctness or code quality. Both are fixable in minutes.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | INFO | spec | Overall confidence tier logic creates a gap: rows with match_quality="full" and stats_available_count in [2,3] fall to "low" because "medium" requires "partial" match. This affects 371K rows (59% of table). Code correctly implements spec. | None -- spec design decision, not a code bug. Flag for product team. |
| 2 | INFO | scorecard | GLD-FE-040 P1 warning: <95% of career_branches have full data for related occupation. 93.8% actual. Known gap from O*NET coverage. | None -- P1 warning acknowledged, not blocking. |
| 3 | LOW | pipeline-state | 4 output hashes stale after governance-reviewer-post fix cycle. | Re-stamp modified steps in pipeline-state JSON. |
| 4 | LOW | golden-datasets | Golden dataset uses `verification_chains` key instead of `values`/`records`. | Add `values` alias or update gate to accept `verification_chains`. |

### What's Acceptable

- The SQL CTE for the 4-way join with dedup-by-richness is well-structured and readable.
- Pure function extraction for all stat derivations makes the math auditable.
- The `_round_half_up` function with its justification comment is the kind of detail that prevents subtle bugs.
- Golden dataset was fixed after adversarial audit caught hallucinated values. The process worked.
- 51 tests with real assertions.
- Governance pipeline fully executed, all steps tracked.
