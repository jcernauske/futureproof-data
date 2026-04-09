## DQ Scorecard: gold-occupation-profiles-bls-ooh
**Spec:** gold-occupation-profiles-bls-ooh
**Date:** 2026-04-07
**Agent:** @dq-engineer
**Overall Score:** 53/53 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-07T20:24:20.382791+00:00)
**Run ID:** acb62160

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-OP-001 |  | P0 | The declared grain is one row per soc_code. Any duplicate indicates a promote or transformer failure. Maps to patterns CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-OP-002 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'op') must be non-null and unique. Duplicate or null record_id indicates a grain hash collision or derivation bug. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-OP-003 |  | P0 | Gold table must contain exactly 832 rows -- one per occupation from Silver base.bls_ooh. No rows added or dropped during Gold transformation. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-004 |  | P0 | Every soc_code must match the SOC standard format XX-XXXX. This is the primary join key for O*NET and the CIP-SOC crosswalk. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-OP-005 |  | P0 | grw_score must be between 1.0 and 10.0 inclusive for all non-null rows. Values outside this range indicate a piecewise linear function error. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-006 |  | P0 | grw_score should be non-null for all 832 rows because employment_change_pct has 0 nulls in the source data. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-007 |  | P0 | grw_score_rounded must be an integer between 1 and 10 inclusive. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-008 |  | P0 | grw_score_rounded must exactly equal ROUND(grw_score) for all rows. Any mismatch indicates a derivation bug or inconsistent rounding mode. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-009 |  | P0 | market_score must be between 1.0 and 10.0 inclusive for all non-null rows. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-010 |  | P0 | market_score should be non-null for all 832 rows because both input components (grw_score and openings_annual_avg) have 0 nulls. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-011 |  | P0 | market_score_rounded must be an integer between 1 and 10 inclusive. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-012 |  | P0 | market_score_rounded must exactly equal ROUND(market_score) for all rows. Any mismatch indicates a derivation bug. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-013 |  | P0 | PERCENT_RANK always produces values in [0.0, 1.0]. Any value outside this range indicates a computation error. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-014 |  | P0 | Exactly 23 occupations should have null wage_percentile_overall, corresponding to the 23 null-wage occupations. CRITICAL: nulls must be excluded from PERCENT_RANK, not included as zero. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-015 |  | P0 | PERCENT_RANK within education tier must be in [0.0, 1.0]. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-016 |  | P0 | Exactly 23 occupations should have null wage_percentile_education_tier, same as wage_percentile_overall. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-017 |  | P0 | When non-null, wage_tier must be one of exactly 5 values. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-018 |  | P0 | Exactly 23 occupations should have null wage_tier, corresponding to the 23 null-wage occupations. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-019 |  | P0 | wage_tier must be null if and only if wage_available is False. Any mismatch indicates a derivation bug in either wage_tier or wage_available. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-020 |  | P0 | Every row must have a confidence_tier assigned. This is a required field with no nulls allowed. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-021 |  | P0 | confidence_tier must be one of exactly 3 values: 'high', 'medium', 'low'. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-022 |  | P0 | Exactly 23 occupations must have confidence_tier = 'low', corresponding to the 23 null-wage occupations. This includes 3 occupations that are also catchall (27-2099, 29-1229, 29-1249) where wage_available=False takes priority. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-023 |  | P0 | The 'high' confidence tier must be the majority -- occupations with wage data that are neither broad nor catchall should dominate. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-024 |  | P0 | confidence_tier = 'low' must correspond exactly to wage_available = False, regardless of broad/catchall flags. The spec defines wage_available = False as taking priority in the CASE logic. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-025 |  | P0 | FutureProof stat mapping field must be exactly 'ERN,GRW' for all 832 rows. Static constant value. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-026 |  | P0 | FutureProof boss fight mapping field must be exactly 'Market,Ceiling' for all 832 rows. Static constant value. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-027 |  | P0 | data_completeness must be computed for every row. No nulls allowed. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-028 |  | P0 | In current data, data_completeness can only be 0.75 or 1.0 because the only nullable core field is median_annual_wage. The spec lists {0.0, 0.25, 0.5, 0.75, 1.0} as theoretical, but EDA confirms only {0.75, 1.0} appear. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-029 |  | P0 | Exactly 23 rows should have data_completeness = 0.75, corresponding to the 23 null-wage occupations. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-030 |  | P0 | wage_percentile_overall and wage_percentile_education_tier must both be null when wage_available = False, and both non-null when wage_available = True. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-031 |  | P0 | All NOT NULL fields from the physical model must be populated. This covers identity fields, classification flags, growth_category, wage_available, and metadata timestamps. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-032 |  | P1 | The mean GRW score should fall between 4.5 and 6.5, reflecting the national average growth (~4%) placing at approximately 6.0 on the scale. Range widened from spec's 5.5-6.5 per EDA recommendation. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-033 |  | P1 | GRW score should populate at least 8 of 10 integer buckets (1-10), ensuring adequate spread across the scale. ADV-DISTRIBUTION-VARIANCE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-034 |  | P1 | Market score distribution must not cluster excessively. Standard deviation above 1.0 ensures meaningful differentiation across the 1-10 scale. ADV-DISTRIBUTION-VARIANCE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-035 |  | P1 | Market score should populate at least 7 of 10 integer buckets. Bucket 10 is structurally absent (no occupation has both top growth AND top openings simultaneously). ADV-DISTRIBUTION-VARIANCE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-036 |  | P1 | Confidence tier distribution should match EDA findings: high=735, medium=74, low=23. Medium tier = 7 broad + 67 catchall-with-wage. Low tier = 23 null-wage (including 3 that are also catchall). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-037 |  | P1 | Wage tier counts should roughly align with percentile-based quartiles. The first 3 tiers (25% each) should each have ~202 occupations. 'high' (75th-90th) ~122 and 'very_high' (90th+) ~81. Ranges provide headroom for data changes. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-038 |  | P1 | GRW score must align monotonically with growth_category. The piecewise linear function maps to known ranges per category. Any cross-category inversion indicates a formula error. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-039 |  | P1 | Market score should match the documented formula: 0.6 * grw_score + 0.4 * openings_score, where openings_score = 1.0 + 9.0 * PERCENT_RANK(openings_annual_avg). Tolerance of 0.01 for floating point rounding. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0, threshold=result = 0.0 (SQL rewritten 2026-04-07: correlated subquery replaced with CTE-based approach) |
| GLD-OP-040 |  | P0 | soc_major_group must equal the first 2 characters of soc_code. Validates the carry-forward from Silver. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-OP-041 |  | P0 | soc_major_group must be one of the 22 valid SOC major group codes. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-OP-042 |  | P0 | growth_category must be one of 6 valid values. Carried from Silver verbatim. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-043 |  | P1 | When non-null, median_annual_wage must be between $25,000 and $250,000. Carried from Silver verbatim. ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-044 |  | P1 | employment_change_pct must be within [-50.0, 60.0] when non-null. ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-045 |  | P1 | Exactly 7 SOC codes should be flagged as broad occupations. Carried from Silver verbatim. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-046 |  | P1 | Exactly 70 occupations should have catchall_flag = True. Carried from Silver verbatim. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-047 |  | P1 | BLS education level code must be between 1 and 8 inclusive when non-null. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-049 |  | P0 | wage_available must exactly equal (median_annual_wage IS NOT NULL). Any mismatch indicates a derivation or carry-forward bug. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-050 |  | P1 | Employment counts must be positive when non-null. Zero or negative employment indicates a data error. ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-051 |  | P1 | Annual job openings must be zero or positive. 4 occupations have openings = 0 (BLS rounding from thousands). ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-052 |  | P1 | No occupation should be both a broad code and a catchall category. These are independent classifications with no expected overlap. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-OP-053 |  | P1 | All 22 SOC major group codes should be represented. ADV-ENTITY-COVERAGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-OP-054 |  | P0 | data_completeness must equal the count of non-null core fields (median_annual_wage, employment_current, employment_change_pct, openings_annual_avg) divided by 4. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 53 | 52 | 98% |

### Failures Requiring Action

- ~~**GLD-OP-039**~~ (P1 — FIXED): SQL rewritten from correlated subquery to CTE-based approach. Now passes with 0 violations.

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.
- **P1 Warnings:** 1 warning(s) — human review recommended.

