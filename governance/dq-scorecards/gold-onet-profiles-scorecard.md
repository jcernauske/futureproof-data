## DQ Scorecard: gold-onet-profiles
**Spec:** gold-onet-profiles
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Overall Score:** 43/43 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-09T04:15:11.840927+00:00)
**Run ID:** fdc05592

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-ONP-001 |  | P0 | The declared grain is one row per bls_soc_code. Any duplicate indicates a promote or transformer failure. Maps to patterns CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-ONP-002 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'wp') must be non-null and unique. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-ONP-003 |  | P0 | Gold table must contain exactly 798 rows -- one per occupation from base.onet_occupations. All Silver rows carried forward, no filtering. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-004 |  | P0 | Every bls_soc_code must match SOC standard format XX-XXXX (7 characters). This is the primary join key to consumable.occupation_profiles. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-005 |  | P0 | hmn_score must be between 1.0 and 10.0 inclusive for all non-null rows. Values outside this range indicate a rescaling formula error. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-006 |  | P0 | Exactly 24 partial-data occupations should have null hmn_score. More nulls indicate a join failure; fewer indicate incorrect scoring of partial-data occupations. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-007 |  | P0 | burnout_score must be between 1.0 and 10.0 inclusive for all non-null rows. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-008 |  | P0 | Exactly 24 partial-data occupations should have null burnout_score. Same set as null hmn_score. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-009 |  | P0 | hmn_score and burnout_score must be null in exactly the same rows. A mismatch would indicate a partial join bug. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-010 |  | P1 | After min/max rescaling, hmn_score should have standard deviation > 1.0, indicating meaningful differentiation across occupations. Maps to ADV-DISTRIBUTION-VARIANCE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-011 |  | P1 | Burnout score should have standard deviation > 0.5, indicating meaningful differentiation. Maps to ADV-DISTRIBUTION-VARIANCE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-012 |  | P0 | hmn_score_rounded must equal ROUND(hmn_score) when hmn_score is non-null, and be null when hmn_score is null. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-013 |  | P0 | burnout_score_rounded must equal ROUND(burnout_score) when burnout_score is non-null, and be null when burnout_score is null. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-014 |  | P0 | top_human_activities must be a valid JSON array with at least 1 element for all scored occupations. Null allowed only when hmn_score is null. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-015 |  | P0 | burnout_drivers must be a valid JSON array with at least 1 element for all scored occupations. Null allowed only when burnout_score is null. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-016 |  | P1 | time_pressure (element 4.C.3.d.1) is a CX scale value with range 1-5. Maps to ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-017 |  | P1 | work_hours (element 4.C.3.d.8) is a CT scale value with range 1-3 (where 3 = >40 hrs). Maps to ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-018 |  | P1 | consequence_of_error (element 4.C.3.a.1) is a CX scale value with range 1-5. Maps to ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-019 |  | P1 | Confidence tier distribution must match expected counts: 772 high, 2 medium (SOC 29-1241 Ophthalmologists with 10.5% context suppression + SOC 51-2061 edge case with >=5% suppression), 24 low (partial-data occupations). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-020 |  | P0 | confidence_tier must be one of: high, medium, low. No nulls allowed (required field per spec). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-021 |  | P1 | Activity suppression percentage must be between 0 and 100. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-022 |  | P1 | Context suppression percentage must be between 0 and 100. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-023 |  | P0 | All required identity, quality, and metadata fields must be non-null for every row. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-024 |  | P0 | backs_stats must be 'HMN' for all rows (static field per spec). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-025 |  | P0 | backs_bosses must be 'AI,Burnout' for all rows (static field per spec). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-026 |  | P1 | data_completeness_tier must have exactly 774 'full' and 24 'partial' rows, carried from Silver. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-027 |  | P1 | activity_profile_available must be true for 'full' occupations and false for 'partial' ones. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-028 |  | P1 | top_5_activities must be a valid JSON array with exactly 5 elements for all occupations with activity profiles. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-029 |  | P0 | The declared grain is one row per bls_soc_code x related_bls_soc_code. Maps to CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE patterns. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-ONP-030 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'tr') must be non-null and unique. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-ONP-031 |  | P0 | Gold table must contain exactly 15,944 rows -- carried 1:1 from base.onet_career_transitions with title enrichment, no filtering. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-032 |  | P0 | No occupation should transition to itself. A self-reference indicates a data error in the similarity graph. Maps to CONS-IMPOSSIBLE-VALUE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-033 |  | P0 | source_title and related_title must be non-null for all rows. A null title indicates a failed join to base.onet_occupations. Maps to ADV-FK-VALID pattern (join completeness). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-034 |  | P0 | backs_feature must be 'Stage3Branching' for all rows (static field per spec). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-035 |  | P0 | relatedness_tier must be one of: Primary-Short, Primary-Long, Supplemental. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-036 |  | P0 | relationship_type must be 'similarity' for all rows. Current O*NET data only includes similarity-based transitions. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-037 |  | P1 | best_index (similarity rank) must be between 1 and 20 inclusive. Maps to ADV-VALUE-RANGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-038 |  | P1 | is_primary must be true for Primary-Short and Primary-Long tiers, false for Supplemental. Maps to ADV-CROSS-COLUMN pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-039 |  | P0 | Every source bls_soc_code in career_transitions must exist in onet_work_profiles. Maps to ADV-FK-VALID and CONS-CROSS-TABLE patterns. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-040 |  | P0 | All fields in career_transitions are marked as required per spec. No nulls allowed. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-041 |  | P0 | Both bls_soc_code and related_bls_soc_code must match SOC format XX-XXXX. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-042 |  | P0 | All 798 occupations from base.onet_occupations must be present. Maps to ADV-ENTITY-COVERAGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-ONP-043 |  | P0 | All 798 occupations must appear as source SOCs in career transitions. Maps to ADV-ENTITY-COVERAGE pattern. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 43 | 43 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

