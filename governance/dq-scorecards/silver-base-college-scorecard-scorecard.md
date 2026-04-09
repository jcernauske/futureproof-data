## DQ Scorecard: silver-base-college-scorecard
**Spec:** silver-base-college-scorecard
**Date:** 2026-04-07
**Agent:** @dq-engineer
**Overall Score:** 34/35 rules passing (97%)
**Data Source:** Production Data Validation (executed 2026-04-07T00:57:02.729313+00:00)
**Run ID:** bf62611d

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| SLV-CS-001 |  | P0 | The declared grain is one row per unitid x cipcode x credential_level. Any duplicate combination indicates a transformer or promote failure. This is the structural foundation of the table. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-002 |  | P0 | After CIP code normalization (inserting dot at position 2), all cipcode values must match the pattern XX.XX (or XX.XXXX if zero-padded). The EDA found all 69,947 source codes are 4-digit, producing XX.XX format. The regex allows 2-4 digits after the dot to accommodate both formats. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-003 |  | P1 | The cip_family field is derived as the first 2 characters of the normalized cipcode. It must be a 2-digit string. All 45 observed families are valid CIP 2020 codes. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-004 |  | P0 | The cip_family field must equal the first 2 characters of cipcode. This validates the derivation logic is correct. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-005 |  | P0 | unitid is a NOT NULL natural key field. Must be present in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-006 |  | P0 | institution_name is a NOT NULL field. Must be non-empty in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-007 |  | P0 | cipcode is a NOT NULL natural key field. Must be present in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-008 |  | P0 | program_name is a NOT NULL field. Must be non-empty in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-009 |  | P0 | credential_level is a NOT NULL natural key field. Must be present in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-010 |  | P0 | credential_description is a NOT NULL field. Must be non-empty in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-011 |  | P0 | cip_family is a NOT NULL derived field. Since cipcode is 0% null and cip_family is derived from cipcode, it must always be populated. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-012 |  | P0 | cip_family_name is a NOT NULL derived field. All 45 observed CIP families must resolve in the lookup table. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-013 |  | P0 | small_cohort_flag is a NOT NULL derived boolean. Must be True or False for every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-014 |  | P0 | source_load_date is a NOT NULL pipeline metadata field. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-015 |  | P0 | ingested_at is a NOT NULL pipeline metadata timestamp, generated at transformation time. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-016 |  | P2 | The earnings_1yr_median field is nullable due to privacy suppression. The null rate should not exceed 70%. A higher rate would suggest a source data change. | PASS | actual=64.0, threshold=result <= 70.0 |
| SLV-CS-017 |  | P2 | The earnings_2yr_median field is nullable due to privacy suppression. The null rate should not exceed 65%. A higher rate would suggest a source data change. | PASS | actual=60.4, threshold=result <= 65.0 |
| SLV-CS-018 |  | P2 | The debt_median field is nullable due to privacy suppression. The null rate should not exceed 68%. A higher rate would suggest a source data change. | PASS | actual=63.1, threshold=result <= 68.0 |
| SLV-CS-019 |  | P2 | The completions_count_1 field has a low null rate. An increase beyond 12% would suggest a source change. | PASS | actual=8.7, threshold=result <= 12.0 |
| SLV-CS-020 |  | P2 | The completions_count_2 field has a low null rate. An increase beyond 12% would suggest a source change. | PASS | actual=8.3, threshold=result <= 12.0 |
| SLV-CS-021 |  | P1 | The Silver base table should contain 60,000-80,000 rows. The current source has 69,947 rows. A count outside this range indicates a transformation filter error or source data change. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-CS-022 |  | P1 | When present, earnings_1yr_median must be between $1,000 and $250,000. This matches the physical model CHECK constraint. The EDA observed range is $4,880-$161,723 with 0 violations. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-023 |  | P1 | When present, earnings_2yr_median must be between $1,000 and $250,000. This matches the physical model CHECK constraint. The EDA observed range is $5,938-$160,116 with 0 violations. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-024 |  | P1 | When present, debt_median must be between $1,000 and $100,000. This matches the physical model CHECK constraint. The EDA observed range is $2,750-$57,500 with 0 violations. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-025 |  | P0 | This MVP dataset is filtered to bachelor's degrees only (credential_level=3). Any other value indicates a filter failure in the pipeline. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-026 |  | P1 | The small_cohort_flag must exactly match the derivation rule: True when completions_count_1 IS NULL OR completions_count_1 < 30, False otherwise. This validates the derived field logic. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-027 |  | P1 | institution_control must be one of the three allowed values per the physical model CHECK constraint. DEFERRED: CONTROL field is not yet in Bronze parquet (EDA Critical Finding #2). This rule is written for when the field is populated. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-028 |  | P1 | The Silver base table row count should be within 5% of the raw zone count. The Silver transformation is a 1:1 row mapping (no filtering, no aggregation), so counts should match exactly. The 5% threshold allows for minor pipeline variations. | ERROR | Catalog Error: Table with name raw_college_scorecard does no |
| SLV-CS-029 |  | P1 | The Silver table should contain 2,200-3,000 distinct institutions. The current source has 2,559 distinct UNITIDs. A count outside this range indicates a data loss or unexpected source expansion. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-CS-030 |  | P0 | Completions counts are non-negative integers representing IPEDS completion volumes. Negative values are impossible in this domain. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-031 |  | P0 | record_id is the deterministic surrogate primary key. It must be non-null and unique across all rows. Duplicates would indicate a grain hash collision or derivation bug. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-032 |  | P2 | The Silver table should contain 40-50 distinct CIP families. The current source has exactly 45 distinct families. This is a stable count tied to the CIP 2020 taxonomy. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-CS-033 |  | P2 | The Silver table should contain 350-450 distinct CIP codes. The current source has 390 distinct codes. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-CS-034 |  | P1 | IPEDS UNITIDs are 6-digit identifiers in the range 100,000-999,999. Values outside this range indicate data corruption or a non-IPEDS identifier. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-CS-035 |  | P2 | The small_cohort_flag True rate should be between 70-80%. A rate outside this range would suggest a change in source data completions distribution or a derivation threshold change. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 35 | 34 | 97% |

### Failures Requiring Action

- **SLV-CS-028** (P1 — WARNING): Catalog Error: Table with name raw_college_scorecard does not exist!
Did you mean "base_college_scorecard"?

LINE 1: ... base_college_scorecard) silver, (SELECT COUNT(*) AS cnt FROM raw_college_scorecard) raw
                                                                         ^

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.
- **P1 Warnings:** 1 warning(s) — human review recommended.

