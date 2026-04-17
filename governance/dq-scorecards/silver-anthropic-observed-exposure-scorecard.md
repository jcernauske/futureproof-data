## DQ Scorecard: raw-ingest-anthropic-economic-index (silver)
**Spec:** raw-ingest-anthropic-economic-index
**Zone:** silver
**Table:** `base.anthropic_observed_exposure`
**Run ID:** fdb689e5
**Executed At:** 2026-04-17T01:52:37.428950+00:00
**Agent:** @dq-engineer
**Results File:** governance/dq-results/silver-anthropic-observed-exposure-20260417T015237Z.json
**Rows in Table:** 587
**Overall Score:** 13/13 rules passing (100.0%)

### Execution Results

| Rule ID | Priority | Dimension | Status | Actual | Threshold | Evidence |
|---------|----------|-----------|--------|--------|-----------|----------|
| SLV-AOE-001 | P0 | uniqueness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-002 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-003 | P0 | consistency | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| SLV-AOE-004 | P0 | volume | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| SLV-AOE-005 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-006 | P0 | coverage | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| SLV-AOE-007 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-008 | P0 | uniqueness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-011 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-012 | P1 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-013 | P1 | completeness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| SLV-AOE-014 | P2 | validity | **PASS** | 3 | `result_count <= 10` | actual=3; rows_returned=3; threshold='result_count <= 10' |
| SLV-AOE-015 | P3 | validity | **PASS** | 0.19080068143100512 | `tracked` | actual=0.19080068143100512; rows_returned=1; threshold='tracked' |

### Summary by Priority

| Priority | Total | Pass | Fail | Error | Rate |
|----------|-------|------|------|-------|------|
| P0 | 9 | 9 | 0 | 0 | 100% |
| P1 | 2 | 2 | 0 | 0 | 100% |
| P2 | 1 | 1 | 0 | 0 | 100% |
| P3 | 1 | 1 | 0 | 0 | 100% |
| **Total** | **13** | **13** | **0** | **0** | **100%** |

### Summary by Dimension

| Dimension | Total | Pass | Rate |
|-----------|-------|------|------|
| completeness | 1 | 1 | 100% |
| consistency | 1 | 1 | 100% |
| coverage | 1 | 1 | 100% |
| uniqueness | 2 | 2 | 100% |
| validity | 7 | 7 | 100% |
| volume | 1 | 1 | 100% |

### Gate Status

- **P0 Gate: PASS** — All P0 rules passed.
- **P1 Warnings:** None.
