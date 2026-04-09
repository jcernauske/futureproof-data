## DQ Scorecard: gold-career-outcomes-college-scorecard
**Spec:** gold-career-outcomes-college-scorecard
**Date:** 2026-04-07
**Agent:** @dq-engineer
**Overall Score:** 42/42 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-07T02:56:12.020087+00:00)
**Run ID:** 71fa5e3a

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-CO-001 |  | P0 | The declared grain is one row per unitid x cipcode x credential_level. Any duplicate indicates a promote or transformer failure. Maps to patterns CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-CO-002 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'co') must be non-null and unique. Duplicate or null record_id indicates a grain hash collision or derivation bug. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-CO-003 |  | P0 | Gold table row count must be within +/- 15% of Silver source (69,947). Range: 59,455 to 80,439. All Silver rows are carried forward with no filtering. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-004 |  | P0 | Within every CIP family, the 25th percentile of 1yr earnings must not exceed the 75th percentile. This is a mathematical invariant of PERCENTILE_CONT. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-CO-005 |  | P0 | Within every CIP family, the 25th percentile of 2yr earnings must not exceed the 75th percentile. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-CO-006 |  | P0 | Within every CIP family, the 25th percentile of debt must not exceed the 75th percentile. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-CO-007 |  | P0 | Every row must have a confidence_tier assigned. This is the only derived field that is NOT NULL regardless of input data availability. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-008 |  | P0 | confidence_tier must be one of exactly 4 values: 'high', 'medium', 'low', 'insufficient'. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-009 |  | P0 | has_earnings must exactly equal (earnings_1yr_median IS NOT NULL OR earnings_2yr_median IS NOT NULL). Any mismatch indicates a derivation bug. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-010 |  | P0 | has_debt must exactly equal (debt_median IS NOT NULL). Any mismatch indicates a derivation bug. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-011 |  | P0 | outcome_completeness must be exactly one of {0.0, 0.33, 0.67, 1.0} representing 0/3, 1/3, 2/3, or 3/3 core outcome fields populated. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-012 |  | P0 | debt_to_earnings_annual must be null whenever either debt_median or earnings_1yr_median is null. Non-null ratio with null inputs indicates a derivation bug. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-013 |  | P0 | debt_to_earnings_annual must be computed (non-null) whenever both inputs are present. A null ratio with non-null inputs indicates a derivation bug. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-014 |  | P0 | earnings_growth_rate must be null whenever either earnings_1yr_median or earnings_2yr_median is null. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-015 |  | P0 | cip_family_earnings_rank must be null when earnings_1yr_median is null (excluded from PERCENT_RANK window). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-016 |  | P0 | program_value_index must be null whenever either earnings_1yr_median or debt_median is null. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-017 |  | P0 | debt_to_earnings_tier must be null exactly when debt_to_earnings_annual is null, and non-null otherwise. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-018 |  | P0 | When non-null, debt_to_earnings_tier must be one of exactly 4 values. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-019 |  | P1 | When non-null, debt_to_earnings_annual must be between 0.01 and 10.0. Values outside this range indicate data quality issues in source earnings or debt fields. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-020 |  | P1 | No more than 0.5% of non-null earnings_growth_rate values may fall outside the range -0.5 to 2.0. Known outliers are expected from cross-cohort volatility. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-021 |  | P1 | PERCENT_RANK always produces values in [0.0, 1.0]. Any value outside this range indicates a computation error. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-022 |  | P1 | The 'Low' DTE tier must be the plurality (most frequent non-null tier). The spec incorrectly expected 'Moderate' to be plurality; EDA corrected this. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-023 |  | P1 | The 'Low' DTE tier should comprise 60-80% of non-null tier assignments. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-024 |  | P1 | The combined 'High' and 'Very High' DTE tiers should not exceed 3% of non-null assignments. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-025 |  | P1 | The 'insufficient' confidence tier should comprise 45-60% of all rows. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-026 |  | P1 | The 'high' confidence tier should comprise 15-30% of all rows. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-027 |  | P1 | 35-55% of non-null earnings growth rates should be negative. This is expected due to cross-cohort measurement (not longitudinal tracking). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-028 |  | P1 | CIP families with fewer than 3 non-null earnings_1yr_median values must have null percentile bands. Non-null bands for these families indicate a transformer bug. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-CO-029 |  | P0 | confidence_tier = 'insufficient' if and only if has_earnings = false AND has_debt = false. This is the logical model's key invariant linking confidence tier to outcome data availability. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-030 |  | P0 | confidence_tier = 'high' requires small_cohort_flag = false AND has_earnings = true AND has_debt = true. Any row assigned 'high' without meeting all three conditions is a derivation error. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-031 |  | P0 | outcome_completeness must exactly match the count of non-null core outcome fields divided by 3. Validates the derivation logic. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-032 |  | P0 | All NOT NULL fields per the logical model must be populated. Covers: record_id, unitid, institution_name, cipcode, program_name, cip_family, cip_family_name, credential_level, small_cohort_flag, source_load_date, promoted_at. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-033 |  | P0 | All derived data quality fields must be populated for every row: confidence_tier, has_earnings, has_debt, outcome_completeness. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-034 |  | P1 | Gold table should maintain the same institution coverage as Silver: 2,200-3,000 distinct institutions. Maps to ADV-ENTITY-COVERAGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-035 |  | P1 | Gold table should contain 40-50 distinct CIP families, matching Silver. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-036 |  | P0 | MVP is filtered to bachelor's degrees only (credential_level = 3). Any other value indicates a filter failure upstream. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-037 |  | P1 | program_value_index (earnings/debt) must be the mathematical inverse of debt_to_earnings_annual (debt/earnings), within floating point tolerance. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-038 |  | P0 | The debt_to_earnings_tier must match the exact bucketing boundaries defined in the logical model. Every non-null tier must correspond to the correct ratio range. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-039 |  | P2 | Tracks institution_control null rate. Currently 100% NULL due to Bronze re-ingestion blocker. This is a tracking rule, not a blocker. Target: 0% once CONTROL field is added to Bronze parquet. | PASS | actual=100.0, threshold=result <= 100.0 |
| GLD-CO-040 |  | P2 | The number of CIP families where a program has earnings data but null percentile bands should not exceed 10. This catches unexpected expansion of the null-band population. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-041 |  | P2 | The mean DTE ratio across all non-null values should be between 0.50 and 0.80. Monitors for distribution drift. Maps to ADV-VALUE-RANGE / ADV-DISTRIBUTION-VARIANCE patterns. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-CO-042 |  | P2 | The mean earnings growth rate across all non-null values should be between -0.05 and +0.10. Monitors for distribution drift. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 42 | 42 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

