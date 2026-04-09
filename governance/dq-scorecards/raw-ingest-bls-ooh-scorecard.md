## DQ Scorecard: raw-ingest-bls-ooh
**Spec:** raw-ingest-bls-ooh
**Date:** 2026-04-07
**Agent:** @dq-engineer
**Run ID:** 90c87408
**Results File:** governance/dq-results/raw-ingest-bls-ooh-20260407T164344Z.json
**Overall Score:** 16/17 executable rules passing (94.1%), 1 deferred
**Data Source:** FULL DATASET (data/raw/xlsx_cache/bls_ooh.xlsx, 832 rows of real BLS Employment Projections data)
**Note:** Full-dataset run. Supersedes all previous sample-data runs. Previously deferred rules RAW-OOH-008 and RAW-OOH-010 are now fully evaluated and PASS.

### Execution Results

| Rule ID | Dimension | Priority | Description | Result | Evidence |
|---------|-----------|----------|-------------|--------|----------|
| RAW-OOH-001 | validity | P0 | SOC code format: XX-XXXX | PASS | violations=0; all 832 SOC codes match ^\d{2}-\d{4}$ |
| RAW-OOH-002 | validity | P0 | SOC code is not a summary code (no XX-0000) | PASS | violations=0; no summary codes in 832 rows |
| RAW-OOH-003 | uniqueness | P0 | Grain uniqueness: soc_code | PASS | total=832, distinct=832, duplicates=0 |
| RAW-OOH-004 | consistency | P0 | Wage cap consistency: capped=true IFF wage=239200.0 | PASS | violations=0; capped_rows=0, null_wage=23; interactive export uses numeric wages (max $238,380), no wages hit the $239,200 cap |
| RAW-OOH-005 | validity | P0 | Education code range: 1-8 | PASS | violations=0; all 8 codes present: [1,2,3,4,5,6,7,8] |
| RAW-OOH-006 | validity | P0 | Work experience code range: 1-3 | PASS | violations=0; all 3 codes present: [1,2,3] |
| RAW-OOH-007 | validity | P0 | Training code range: 1-6 | PASS | violations=0; all 6 codes present: [1,2,3,4,5,6] |
| RAW-OOH-008 | completeness | P1 | Median wage null rate below 5% | PASS | null_rate=2.8% (23/832); threshold=5%; previously DEFERRED on 10-row sample |
| RAW-OOH-009 | completeness | P0 | Occupation title completeness: 0% null | PASS | violations=0; all 832 rows have occupation_title |
| RAW-OOH-010 | volume | P0 | Row count within expected range: 750-900 | PASS | count=832; range=[750,900]; previously DEFERRED on 10-row sample |
| RAW-OOH-011 | validity | P0 | Employment current must be positive | PASS | violations=0; range: 200 - 4,347,700 |
| RAW-OOH-012 | validity | P0 | Employment projected must be positive | PASS | violations=0; range: 200 - 5,087,500 |
| RAW-OOH-013 | validity | P0 | Openings annual avg must be positive | **FAIL** | violations=4; 4 niche occupations have openings=0 due to BLS rounding from thousands (see investigation below) |
| RAW-OOH-014 | completeness | P0 | soc_code completeness: 0% null | PASS | violations=0; all 832 rows have soc_code |
| RAW-OOH-015 | completeness | P0 | median_wage_capped completeness: 0% null | PASS | violations=0; all 832 rows have median_wage_capped |
| RAW-OOH-016 | validity | P1 | Median wage range: $20,000-$239,200 | PASS | violations=0; observed range: $30,160 - $238,380 |
| RAW-OOH-017 | freshness | P1 | load_date within last 30 days | DEFERRED | load_date is a metadata field added by framework at Iceberg write time; not testable pre-write |
| RAW-OOH-018 | consistency | P1 | Employment change = projected - current (within +/-1000) | PASS | violations=0; all 832 rows consistent |

### Summary by Priority

| Priority | Total | Executed | Pass | Fail | Deferred |
|----------|-------|----------|------|------|----------|
| P0 | 13 | 13 | 12 | 1 | 0 |
| P1 | 5 | 4 | 4 | 0 | 1 |
| **Total** | **18** | **17** | **16** | **1** | **1** |

### P0 Failure Investigation: RAW-OOH-013

**Rule:** Openings annual avg must be strictly positive (> 0)
**Violations:** 4 occupations with openings_annual_avg = 0

| SOC Code | Occupation | Openings | Employment Current | Employment Change |
|----------|-----------|----------|-------------------|------------------|
| 51-7032 | Patternmakers, wood | 0 | 500 | 0 |
| 29-1243 | Pediatric surgeons | 0 | 1,100 | 0 |
| 29-1024 | Prosthodontists | 0 | 900 | 0 |
| 51-2061 | Timing device assemblers and adjusters | 0 | 200 | 0 |

**Root Cause:** BLS employment projections data is reported in thousands. These four occupations have fewer than 50 annual openings each, which rounds to 0 when the source value (e.g., 0.04 thousands) is multiplied by 1000 and rounded to the nearest integer. This is a BLS rounding artifact, not a data quality issue.

**Recommendation for @dq-rule-writer:** Amend RAW-OOH-013 threshold from `openings_annual_avg > 0` (strictly positive) to `openings_annual_avg >= 0` (non-negative). The rule description should note that zero openings are valid for very small occupations due to BLS rounding from thousands.

**Impact:** This P0 failure does NOT indicate a data integrity problem. The ingestor is correctly processing the BLS source data. Escalating to @governance-reviewer for acknowledgment.

### Deferred Rules

One rule remains deferred:

1. **RAW-OOH-017** (P1): Freshness check requires load_date metadata field, which is added by the Brightsmith framework at Iceberg write time. Will be validated on first production write.

### Comparison to Previous Run (Sample Data)

| Metric | Previous (10-row sample) | Current (832-row full) | Change |
|--------|-------------------------|----------------------|--------|
| Rows evaluated | 10 | 832 | +822 |
| Rules executed | 15 | 17 | +2 (RAW-OOH-008, RAW-OOH-010 now evaluated) |
| Rules passed | 15 | 16 | +1 |
| Rules failed | 0 | 1 | +1 (RAW-OOH-013: zero-openings rounding) |
| Rules deferred | 3 | 1 | -2 |
| P0 gate | PASS (conditional) | FAIL (rule calibration issue) | Regression |

### Gate Status
- **P0 Gate: FAIL** -- RAW-OOH-013 has 4 violations (zero openings due to BLS rounding). This is a rule calibration issue, not a data integrity problem. Escalating to @governance-reviewer.
- **P1 Rules: PASS** -- All 4 executable P1 rules passed. RAW-OOH-008 (wage null rate 2.8%) and RAW-OOH-016 (wage range) confirmed on full data.
- **Action required:**
  1. @dq-rule-writer should amend RAW-OOH-013 to allow zero openings (>= 0 instead of > 0)
  2. @governance-reviewer should acknowledge the P0 failure as a rule calibration issue
  3. Re-run DQ suite after rule amendment to clear the P0 gate
