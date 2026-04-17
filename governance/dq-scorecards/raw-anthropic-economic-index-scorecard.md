## DQ Scorecard: raw-ingest-anthropic-economic-index (bronze)
**Spec:** raw-ingest-anthropic-economic-index
**Zone:** bronze
**Table:** `raw.anthropic_economic_index`
**Run ID:** fdb689e5
**Executed At:** 2026-04-17T01:52:37.428950+00:00
**Agent:** @dq-engineer
**Results File:** governance/dq-results/raw-anthropic-economic-index-20260417T015237Z.json
**Rows in Table:** 4,082
**Overall Score:** 17/17 rules passing (100.0%)

### Execution Results

| Rule ID | Priority | Dimension | Status | Actual | Threshold | Evidence |
|---------|----------|-----------|--------|--------|-----------|----------|
| RAW-AEI-001 | P0 | uniqueness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-002 | P0 | volume | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| RAW-AEI-003 | P0 | consistency | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| RAW-AEI-004 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-005 | P0 | completeness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-006 | P0 | completeness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-007 | P1 | completeness | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| RAW-AEI-008 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-010 | P1 | consistency | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-011 | P1 | completeness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-013 | P1 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-014 | P1 | completeness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-015 | P1 | freshness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-016 | P1 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-017 | P0 | completeness | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| RAW-AEI-019 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| RAW-AEI-018 | P2 | validity | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |

### Summary by Priority

| Priority | Total | Pass | Fail | Error | Rate |
|----------|-------|------|------|-------|------|
| P0 | 9 | 9 | 0 | 0 | 100% |
| P1 | 7 | 7 | 0 | 0 | 100% |
| P2 | 1 | 1 | 0 | 0 | 100% |
| **Total** | **17** | **17** | **0** | **0** | **100%** |

### Summary by Dimension

| Dimension | Total | Pass | Rate |
|-----------|-------|------|------|
| completeness | 6 | 6 | 100% |
| consistency | 2 | 2 | 100% |
| freshness | 1 | 1 | 100% |
| uniqueness | 1 | 1 | 100% |
| validity | 6 | 6 | 100% |
| volume | 1 | 1 | 100% |

### Gate Status

- **P0 Gate: PASS** — All P0 rules passed.
- **P1 Warnings:** None.
