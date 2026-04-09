# Session: Gold Primary Agent - career_outcomes transformer

**Session ID:** 2026-04-06-gold-primary-agent
**Date:** 2026-04-06
**Agent:** @primary-agent
**Spec:** gold-career-outcomes-college-scorecard

## Actions Taken

1. Read all reference materials: Gold spec, physical model, Silver transformer pattern, Brightsmith framework APIs (promote, grain, iceberg_setup), EDA report, DQ rules
2. Created `src/gold/__init__.py` and `src/gold/college_scorecard_career_outcomes.py`
3. Created `tests/gold/test_college_scorecard_career_outcomes.py` (59 tests, 0 failures)
4. Updated `domain/manifest.yaml` with Gold zone pipeline entry
5. Ran transformer against real Silver data: 69,947 rows promoted to `consumable.career_outcomes`
6. Verified idempotency: re-run produced 0 new rows (all 69,947 skipped)
7. Verified data quality: grain uniqueness, record_id uniqueness, p25<=p75 invariant, outcome_completeness value set, confidence tier distribution
8. Registered pipeline gate completion

## Artifacts Produced

- `/Users/jcernauske/code/bright/futureproof-data/src/gold/__init__.py`
- `/Users/jcernauske/code/bright/futureproof-data/src/gold/college_scorecard_career_outcomes.py`
- `/Users/jcernauske/code/bright/futureproof-data/tests/gold/test_college_scorecard_career_outcomes.py`
- `/Users/jcernauske/code/bright/futureproof-data/domain/manifest.yaml` (updated)
- Gold Iceberg table: `consumable.career_outcomes` at `data/gold/iceberg_warehouse/`

## Decisions and Rationale

1. **Grain ID uses 'credlev' key per spec:** The physical model specifies `compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='co')`. Since the Gold row dict uses `credential_level` as the column name, the transformer builds a temporary grain dict mapping `credlev` -> `credential_level` value for hash computation.

2. **DuckDB SQL for all derivations:** All Gold derivations (percentile bands, DTE ratio/tier, earnings growth, rankings, confidence tier, flags) are computed in a single DuckDB SQL query over the Silver Arrow table. This is more efficient and testable than row-by-row Python.

3. **Percentile bands via aggregate + join (not window):** Used `PERCENTILE_CONT ... WITHIN GROUP ... GROUP BY cip_family` with a separate CTE for per-family counts, then joined back. This avoids DuckDB's limitations with conditional window functions and cleanly handles the minimum-3-non-null guard.

4. **PERCENT_RANK via separate CTE with WHERE filter:** Rows with null earnings_1yr_median are excluded from the ranking window, then left-joined back so they get null rank.

5. **outcome_completeness snap function:** Added `_snap_outcome_completeness()` to guard against floating-point drift from ROUND(n/3, 2). The value set is contractually {0.0, 0.33, 0.67, 1.0}.

6. **institution_control nullable:** The physical model says NOT NULL but EDA confirms 100% null from Bronze. Made the schema field `required=False` per EDA recommendation (known gap).

7. **No tests/gold/__init__.py:** The Silver tests directory has no `__init__.py`, and adding one to `tests/gold/` would shadow `src/gold/` in Python's module resolution. Followed the existing pattern.

## Verification Results

- Row count: 69,947 (exact match with Silver source)
- Column count: 31 (30 data + promoted_at)
- Grain uniqueness: 0 duplicates
- Record ID uniqueness: 0 duplicates
- P25 <= P75 violations: 0
- Outcome completeness values: {0.0, 0.33, 0.67, 1.0}
- Confidence tier: insufficient=36,894, low=16,556, high=15,245, medium=1,252
- DTE tier: Low=15,067, Moderate=6,521, High=170, Very High=5
- Idempotency: re-run promoted 0 rows, skipped 69,947
- Full test suite: 130 passed (59 Gold + 71 existing)
