## DQ Scorecard: silver-base-onet
**Spec:** silver-base-onet
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Overall Score:** 37/37 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-09T00:49:39.704370+00:00)
**Run ID:** 4060c827

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| SLV-ONET-001 |  | P0 | Every bls_soc_code must match the BLS SOC standard format XX-XXXX (2-digit major group, hyphen, 4-digit detail). This is the primary cross-source join key for BLS OOH and CIP-SOC crosswalk. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-002 |  | P0 | The declared grain is one row per bls_soc_code. Any duplicate indicates a transformer or promote failure. This is the structural foundation of the occupation dimension table. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-003 |  | P0 | Silver onet_occupations must contain exactly 798 rows: 867 derivable BLS SOCs minus 69 truly empty BLS SOCs (those with zero child data at BLS granularity). | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-004 |  | P1 | Exactly 76 BLS SOCs should have multi_detail_flag = true (multiple O*NET detail codes mapping to one BLS SOC). | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-005 |  | P1 | Expect exactly 774 'full' BLS SOCs, 24 'partial' (tasks + related only), and zero 'none' (excluded from Silver). Only valid values are 'full' and 'partial'. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-006 |  | P0 | No BLS SOCs with data_completeness_tier = 'none' should be present in Silver. The 93 'All Other'/Military O*NET codes (69 at BLS level) with zero child data must be excluded. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-007 |  | P0 | All 14 columns in onet_occupations are defined as NOT NULL in the logical model. Any null indicates a transformer bug. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-010 |  | P0 | The declared grain is bls_soc_code x element_id. Any duplicate indicates a multi-detail aggregation or promote failure. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-011 |  | P0 | IM scale importance values must fall within the O*NET defined range of 1.0 to 5.0. Values outside this range indicate a transformation or averaging error. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-012 |  | P0 | There must be exactly 41 distinct Work Activity element IDs (Generalized Work Activities from the O*NET Content Model). | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-013 |  | P1 | Each occupation must have importance_rank values forming a complete 1-41 sequence with no gaps or duplicates. Rank 1 = most important activity, 41 = least. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-014 |  | P2 | Less than 1% of activity profile rows should have suppress_flag = true. Higher rates indicate unexpected data quality issues in the Bronze source. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-015 |  | P1 | Expected exactly 31,734 rows (774 BLS SOCs with WA data x 41 activities). Only occupations with Work Activities data contribute rows. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-016 |  | P0 | Every bls_soc_code in activity_profiles must exist in onet_occupations. Orphan activity profiles indicate a filtering or join error. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-017 |  | P0 | All 11 columns in onet_activity_profiles are defined as NOT NULL in the logical model. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-020 |  | P0 | The declared grain is bls_soc_code x element_id. Any duplicate indicates a scale filtering or aggregation failure. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-021 |  | P0 | CX scale context values must fall within O*NET defined range of 1.0 to 5.0. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-022 |  | P0 | CT scale context values must fall within O*NET defined range of 1.0 to 3.0. CT covers 2 elements: Duration of Typical Work Week and Work Schedules. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-023 |  | P0 | There must be exactly 57 distinct Work Context element IDs (55 CX + 2 CT from the O*NET Content Model). | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-024 |  | P1 | Exactly 9 distinct element_ids should have is_burnout_element = true, using the EDA-corrected IDs: 4.C.3.d.1, 4.C.3.d.8, 4.C.3.a.1, 4.C.3.d.3, 4.C.3.a.2.b, 4.C.3.b.4, 4.C.3.b.7, 4.C.3.d.4, 4.C.3.a.2.a. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-025 |  | P0 | Silver context_profiles must contain only CX and CT scale rows. CXP/CTP category-percentage rows (82.9% of Bronze Work Context) must be excluded. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-026 |  | P0 | Every bls_soc_code in context_profiles must exist in onet_occupations. Orphan context profiles indicate a filtering or join error. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-027 |  | P1 | Expected exactly 44,118 rows (774 BLS SOCs with WC data x 57 elements). Only occupations with Work Context data contribute rows. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-028 |  | P0 | All 11 columns in onet_context_profiles are defined as NOT NULL in the logical model. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-029 |  | P2 | Less than 1% of context profile rows should have suppress_flag = true. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-030 |  | P0 | The declared grain is bls_soc_code x related_bls_soc_code. Duplicates indicate deduplication failure during BLS-level aggregation. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-031 |  | P0 | No career transition should reference itself (bls_soc_code = related_bls_soc_code). Self-references emerge during BLS-level aggregation (343 raw) and must be excluded. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-032 |  | P0 | best_index must be in range 1-20 (O*NET Related Occupations provides up to 20 related occupations per source). Lower = more similar. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-033 |  | P0 | relatedness_tier must be exactly one of: 'Primary-Short' (index 1-5), 'Primary-Long' (index 6-10), 'Supplemental' (index 11-20). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-034 |  | P0 | is_primary must be true when relatedness_tier is 'Primary-Short' or 'Primary-Long', and false when 'Supplemental'. These are derived from the same source (best_index) so must be consistent. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-035 |  | P0 | Every source bls_soc_code in career_transitions must exist in onet_occupations. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-036 |  | P0 | Every target related_bls_soc_code in career_transitions must exist in onet_occupations. Orphan targets indicate an exclusion filter missed the 'none'-tier SOCs. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-037 |  | P1 | Expected exactly 15,944 rows after BLS-level aggregation, self-reference removal, and deduplication. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-ONET-038 |  | P0 | Both bls_soc_code and related_bls_soc_code must match XX-XXXX format. Invalid formats indicate a truncation error during BLS-level aggregation. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-039 |  | P0 | All 9 columns in onet_career_transitions are defined as NOT NULL in the logical model. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-040 |  | P0 | relationship_type must always be 'similarity' for this source (Related Occupations). Future sources may add 'transition' type. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-ONET-041 |  | P1 | relatedness_tier must be consistent with best_index ranges: Primary-Short (1-5), Primary-Long (6-10), Supplemental (11-20). | PASS | actual=0, threshold=result_count = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 37 | 37 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

