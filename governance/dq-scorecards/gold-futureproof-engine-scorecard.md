## DQ Scorecard: gold-futureproof-engine
**Spec:** gold-futureproof-engine
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Overall Score:** 44/45 rules passing (98%)
**Data Source:** Production Data Validation (executed 2026-04-09T14:44:08.288315+00:00)
**Run ID:** 08e351f2

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-FE-001 |  | P0 | The declared grain is one row per unitid x cipcode x soc_code. Any duplicate indicates dedup failure after CIP prefix fan-out. Maps to patterns CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-002 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'pcp') must be non-null and unique. Duplicate or null record_id indicates a grain hash collision or derivation bug. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-003 |  | P0 | Gold table row count must be within 580,000-700,000. EDA-observed count is 626,406. This range accommodates normal variation from CIP prefix fan-out and crosswalk updates. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-004 |  | P1 | At least 90% of distinct CIP codes from career_outcomes must appear in program_career_paths, confirming the 4-digit CIP prefix join is working. The ~9% unmatched CIPs are XX.99/XX.00 catch-all categories with no crosswalk mapping. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-005 |  | P1 | At least 95% of career_outcomes rows (by distinct unitid+cipcode) must appear in program_career_paths. The unmatched 2.9% rows are from niche catch-all CIP categories. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-006 |  | P0 | Earning Power stat must be in the 1-10 integer range when non-null. Values outside this range indicate a derivation bug in the ERN formula. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-007 |  | P0 | Return on Investment stat must be in the 1-10 integer range when non-null. Piecewise linear derivation is bounded by floor=1 and cap=10. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-008 |  | P0 | Growth stat must be in the 1-10 integer range when non-null. Carried directly from occupation_profiles.grw_score_rounded, which is validated by GLD-OP-005. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-009 |  | P0 | Human Edge stat must be in the 1-10 integer range when non-null. Carried from onet_work_profiles.hmn_score_rounded. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-010 |  | P0 | AI Resilience stat is a placeholder -- must be null for every row in MVP. Any non-null value indicates premature population or data corruption. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-011 |  | P0 | AI Boss score is a placeholder -- must be null for every row in MVP. Same dependency as stat_res. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-012 |  | P0 | Student Loans Boss score must be in the 1-10 integer range when non-null. Derived as 11 - stat_roi, so mathematically constrained to [1,10]. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-013 |  | P0 | Market Boss score must be in the 1-10 integer range when non-null. Carried from occupation_profiles.market_score_rounded. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-014 |  | P0 | Burnout Boss score must be in the 1-10 integer range when non-null. Carried from onet_work_profiles.burnout_score_rounded. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-015 |  | P0 | Ceiling Boss score must be in the 1-10 integer range when non-null. Derived as ROUND(10 - 9 * wage_percentile_education_tier) with input in [0,1], constraining output to [1,10]. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-016 |  | P0 | match_quality must be NOT NULL and one of the four defined categories. This field is derived at Gold time from actual join results. Null or unexpected values indicate derivation failure. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-017 |  | P1 | At least 90% of rows should have 'full' match quality (both BLS and O*NET data present). A significant drop indicates join chain degradation. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-018 |  | P0 | overall_confidence must be NOT NULL and one of 'high', 'medium', 'low'. Derived from stats_available_count and match_quality. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-019 |  | P1 | At least 25% of rows should have 'high' overall confidence. A drop below this indicates stat availability regression. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-020 |  | P0 | stats_available_count must be NOT NULL and 0-4 in MVP (max 4 because stat_res is always null). Count of 5 would indicate stat_res was incorrectly populated. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-021 |  | P1 | At least 90% of rows should have 2 or more stats available. Most rows get at least GRW + HMN from BLS/O*NET coverage. Rows with 0-1 stats indicate join chain failures. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-022 |  | P0 | bosses_available_count must be NOT NULL and 0-4 in MVP (max 4 because boss_ai_score is always null). | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-023 |  | P0 | boss_loans_score must equal exactly 11 - stat_roi when both are non-null. This is a derivation invariant. Maps to pattern ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-024 |  | P0 | When stat_roi is null, boss_loans_score must also be null. Null propagation invariant from derivation rule. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-025 |  | P1 | stat_ern should be null when earnings_1yr_median is null, since earnings_1yr_median null indicates the cip_family_earnings_rank input to ERN derivation is also null (both driven by Scorecard privacy suppression). | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-026 |  | P0 | All NOT NULL fields from the logical model must be populated. Covers identity fields, data quality fields, and metadata. Note: occupation_title excluded -- EDA found 22 SOC codes with no title from either BLS or O*NET. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-027 |  | P0 | Every soc_code must match SOC standard format XX-XXXX. This is the join key to BLS and O*NET sources. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-028 |  | P0 | Every cipcode must match the 4-digit Scorecard format XX.XX. This field is carried from career_outcomes, not the crosswalk's 6-digit format. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-029 |  | P1 | When match_quality is 'scorecard_only' (no BLS or O*NET data), all occupation-sourced stats and bosses must be null. Maps to pattern ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-030 |  | P0 | Every soc_code in program_career_paths must exist in the cip_soc_crosswalk. The crosswalk is the source of SOC codes via the join chain. Maps to pattern ADV-FK-VALID. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-031 |  | P0 | Every unitid in program_career_paths must exist in career_outcomes. All institutions flow from the Scorecard source. Maps to pattern ADV-FK-VALID. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-032 |  | P0 | The declared grain is one row per soc_code x related_soc_code. This is a 1:1 enrichment of career_transitions. Maps to patterns CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-033 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'br') must be non-null and unique. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-034 |  | P0 | career_branches must contain exactly 15,944 rows -- one per career_transitions row. No rows added or dropped during enrichment. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-035 |  | P0 | Both soc_code and related_soc_code must match SOC format XX-XXXX. Carried from career_transitions. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-036 |  | P0 | All score fields (source_grw, source_hmn, source_burnout, related_grw, related_hmn, related_burnout) must be in 1-10 when non-null. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-037 |  | P0 | Stat deltas (grw_delta, hmn_delta, burnout_delta) must be in -9 to +9 range when non-null. Since both source and target scores are 1-10, the maximum possible delta is 10-1=9 and minimum is 1-10=-9. Maps to pattern CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-038 |  | P0 | Delta fields must be null when either the source or target stat is null. Null propagation invariant. Maps to pattern ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-039 |  | P1 | branch_has_full_data=True requires related occupation to have both BLS (related_grw) and O*NET (related_hmn) data. branch_has_full_data=False should not have all four related stats populated. Maps to pattern ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-040 |  | P1 | At least 95% of career_branches rows should have full data for the related occupation. | FAIL | actual=1.0, threshold=result = 0.0 |
| GLD-FE-041 |  | P0 | All NOT NULL fields from the logical model must be populated. Covers identity, classification, derived flag, and metadata. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-042 |  | P0 | relatedness_tier must be one of three defined values. Carried from career_transitions. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-043 |  | P0 | Every (soc_code, related_soc_code) pair in career_branches must exist in career_transitions. career_branches is a 1:1 enrichment of career_transitions. Maps to pattern ADV-FK-VALID. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-FE-044 |  | P0 | Verifies 3 golden dataset chains against pipeline output: (1) ISU Business Admin 52.02 -> SOC 11-1021, (2) Daemen Natural Sciences 30.18 -> SOC 19-2099, (3) Career branch Chief Executives 11-1011 -> Financial Managers 11-3031. All stat/boss scores and derived fields must match expected values from governance/golden-datasets/gold-futureproof-engine-golden.json. Maps to pattern CONS-GOLDEN-DATASET. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-FE-045 |  | P2 | wage_delta (related_wage - source_wage) should be within a reasonable range. BLS median wages range from ~$25K to ~$250K, so maximum plausible delta is ~$225K in either direction. | PASS | actual=0, threshold=result_count = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 45 | 44 | 98% |

### Failures Requiring Action

- **GLD-FE-040** (P1 — WARNING): actual=1.0, threshold=result = 0.0

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.
- **P1 Warnings:** 1 warning(s) — human review recommended.

