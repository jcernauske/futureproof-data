## DQ Scorecard: raw-ingest-anthropic-economic-index (gold)
**Spec:** raw-ingest-anthropic-economic-index
**Zone:** gold
**Table:** `consumable.ai_exposure`
**Run ID:** fdb689e5
**Executed At:** 2026-04-17T01:52:37.428950+00:00
**Agent:** @dq-engineer
**Results File:** governance/dq-results/gold-ai-exposure-anthropic-20260417T015237Z.json
**Rows in Table:** 815
**Overall Score:** 7/8 rules passing (87.5%)

### Execution Results

| Rule ID | Priority | Dimension | Status | Actual | Threshold | Evidence |
|---------|----------|-----------|--------|--------|-----------|----------|
| GLD-AIE-ANT-001 | P1 | coverage | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| GLD-AIE-ANT-002 | P1 | consistency | **PASS** | 0 | `result = 0` | actual=0; rows_returned=1; threshold='result = 0' |
| GLD-AIE-ANT-003 | P1 | completeness | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| GLD-AIE-ANT-004 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| GLD-AIE-ANT-005 | P0 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| GLD-AIE-ANT-006 | P1 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| GLD-AIE-ANT-008 | P2 | validity | **PASS** | 0 | `result_count = 0` | actual=0; rows_returned=0; threshold='result_count = 0' |
| GLD-AIE-ANT-007 | P2 | consistency | **SKIPPED** | - | `result_count = 0` | Baseline snapshot table consumable.ai_exposure_baseline_pre_anthropic does not exist in this environ |

### Summary by Priority

| Priority | Total | Pass | Fail | Error | Rate |
|----------|-------|------|------|-------|------|
| P0 | 2 | 2 | 0 | 0 | 100% |
| P1 | 4 | 4 | 0 | 0 | 100% |
| P2 | 2 | 1 | 0 | 0 | 50% |
| **Total** | **8** | **7** | **0** | **0** | **88%** |

### Summary by Dimension

| Dimension | Total | Pass | Rate |
|-----------|-------|------|------|
| completeness | 1 | 1 | 100% |
| consistency | 2 | 1 | 50% |
| coverage | 1 | 1 | 100% |
| validity | 4 | 4 | 100% |

### Gate Status

- **P0 Gate: PASS** — All P0 rules passed.
- **P1 Warnings:** None.
