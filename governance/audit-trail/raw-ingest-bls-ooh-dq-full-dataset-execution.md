## Audit Trail: DQ Full-Dataset Execution -- raw-ingest-bls-ooh

**Date:** 2026-04-07
**Agent:** @dq-engineer
**Run ID:** 90c87408
**Spec:** raw-ingest-bls-ooh

### Action

Executed all 18 DQ rules against the full BLS OOH dataset (832 rows from real BLS Employment Projections interactive export). This supersedes all previous sample-data runs (10-row sample).

### Data Source

- File: `data/raw/xlsx_cache/bls_ooh.xlsx`
- Rows: 832 detailed occupations
- Source: BLS Employment Projections, Table 1.7, projection cycle 2023-2033

### Results Summary

- **Rules executed:** 17 of 18
- **Rules passed:** 16
- **Rules failed:** 1 (RAW-OOH-013)
- **Rules deferred:** 1 (RAW-OOH-017 -- freshness, requires Iceberg write)
- **P0 gate:** FAIL (due to RAW-OOH-013)

### Previously Deferred Rules Now Evaluated

| Rule | Previous Status | Current Status | Detail |
|------|----------------|----------------|--------|
| RAW-OOH-008 (P1) | DEFERRED (sample 10% null) | PASS | null_rate=2.8% (23/832), under 5% threshold |
| RAW-OOH-010 (P0) | DEFERRED (10-row sample) | PASS | count=832, within 750-900 range |
| RAW-OOH-017 (P1) | DEFERRED | Still DEFERRED | load_date metadata field not available pre-write |

### P0 Failure: RAW-OOH-013

**Rule:** Openings annual avg must be positive (> 0)
**Violations:** 4 occupations with openings_annual_avg = 0
**Root Cause:** BLS rounding artifact. These 4 occupations have fewer than 50 annual openings, which rounds to 0 from the thousands-based source.
**Affected occupations:** 51-7032, 29-1243, 29-1024, 51-2061
**Assessment:** Rule calibration issue, not a data integrity problem. The ingestor is correctly processing BLS source data.
**Recommendation:** @dq-rule-writer should amend RAW-OOH-013 to allow >= 0 (non-negative) instead of > 0 (strictly positive).
**Escalation:** P0 failure escalated to @governance-reviewer for acknowledgment.

### Regressions from Previous Run

| Metric | Previous (sample) | Current (full) | Assessment |
|--------|-------------------|----------------|------------|
| RAW-OOH-013 | PASS (all sample openings > 0) | FAIL (4 zero-openings) | Rule calibration, not regression |

### Artifacts Produced

- Results: `governance/dq-results/raw-ingest-bls-ooh-20260407T164344Z.json`
- Stats: `governance/dq-results/raw-bls-ooh-full-stats.json`
- Scorecard: `governance/dq-scorecards/raw-ingest-bls-ooh-scorecard.md`
- EDA: `governance/eda/raw-bls-ooh-eda.md` (updated to FULL DATASET status)
