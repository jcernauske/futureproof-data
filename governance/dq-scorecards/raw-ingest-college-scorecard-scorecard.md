## DQ Scorecard: raw-ingest-college-scorecard
**Spec:** raw-ingest-college-scorecard
**Date:** 2026-04-06
**Agent:** @dq-engineer
**Overall Score:** 18/18 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-06T02:58:55.300588+00:00)
**Run ID:** f90a303e

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| RAW-CS-001 |  | P0 | The declared grain is unitid x cipcode x credlev. Any duplicate combination indicates an ingestor dedup failure. EDA confirmed 0 duplicates across 69,947 rows. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-002 |  | P0 | unitid is a required grain field. Must be present in every row. EDA shows 0% null rate across 69,947 rows. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-003 |  | P0 | cipcode is a required grain field. Must be present in every row. EDA shows 0% null rate across 69,947 rows. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-004 |  | P0 | credlev is a required grain field. Must be present in every row. EDA shows 0% null rate across 69,947 rows. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-005 |  | P0 | Institution name should be present for every row. EDA shows 0% null rate. Every institution has a name. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-006 |  | P1 | Earnings 1yr field is expected to be ~64% null due to Department of Education privacy suppression. Threshold set at 70% of total rows (48,963 of 69,947) to allow headroom for variation across data refreshes. Exceeding this threshold may indicate a source change or ingestor issue. | PASS | actual=44751, threshold=result_count <= 48963.0 |
| RAW-CS-007 |  | P1 | Earnings 2yr field is expected to be ~60% null due to privacy suppression. Threshold set at 65% of total rows (45,466 of 69,947). The 2yr field has slightly lower null rate than 1yr per EDA. | PASS | actual=42266, threshold=result_count <= 45466.0 |
| RAW-CS-008 |  | P1 | Debt field is expected to be ~63% null due to privacy suppression. Threshold set at 68% of total rows (47,564 of 69,947). | PASS | actual=44138, threshold=result_count <= 47564.0 |
| RAW-CS-009 |  | P1 | IPEDS completions count should be present for most rows. EDA shows 8.7% null. Threshold set at 12% (8,394 of 69,947) per EDA recommendation. | PASS | actual=6098, threshold=result_count <= 8394.0 |
| RAW-CS-010 |  | P0 | MVP filter requires CREDLEV=3 (bachelor's degree only). Any non-3 value indicates the ingestor filter failed. This is a hard structural constraint. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-011 |  | P0 | All CIP codes in the source are 4-character numeric strings (e.g., '5202'). This is the expected bronze zone format; silver zone will transform to XX.XXXX. Any deviation indicates a parsing or type-coercion issue. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-012 |  | P1 | When present, median earnings (1yr) must be positive and within a plausible range. The $300k upper bound provides generous headroom above the observed max of $161,723. Values <= 0 are domain-impossible (earnings of employed graduates). | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-013 |  | P1 | When present, median earnings (2yr) must be positive and within a plausible range. Same logic as 1yr rule. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-014 |  | P1 | When present, median debt must be positive and within a plausible range. The $200k upper bound provides generous headroom above the observed max of $57,500 to accommodate future data drift (e.g., graduate-professional programs if CREDLEV filter changes). | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-015 |  | P1 | IPEDS institution IDs are 6-digit integers in the range 100,000-999,999. Values outside this range indicate a data corruption or parsing issue. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-016 |  | P0 | Total row count should be between 50,000 and 100,000. Current count is 69,947. The range allows ~30% variation for annual data changes (institution openings/closures, program additions/removals). A count outside this range suggests a source format change, download failure, or filter error. | PASS | actual=0.0, threshold=result = 0.0 |
| RAW-CS-017 |  | P1 | The load_date should be recent (within 30 days of query execution). Stale data suggests the pipeline has not been refreshed. Returns at most 1 row as a sentinel check. | PASS | actual=0, threshold=result_count = 0.0 |
| RAW-CS-018 |  | P1 | When both earnings fields are present, 2yr earnings may be less than 1yr earnings because these are different cohort measurement windows, NOT longitudinal tracking of the same individuals. EDA shows 44.2% of dual-present rows exhibit this pattern. This rule monitors the rate but allows a high threshold. A dramatic increase could indicate a data processing change. | PASS | actual=9797, threshold=result_count <= 12000.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 18 | 18 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

