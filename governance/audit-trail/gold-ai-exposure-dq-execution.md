## DQ Execution: gold-ai-exposure

**Spec:** gold-ai-exposure
**Zone:** Gold
**Table:** consumable.ai_exposure
**Agent:** @dq-engineer
**Timestamp:** 2026-04-09T21:27:59Z
**Run ID:** abd0ef16

### Actions Taken

1. Approved all 15 proposed DQ rules (GLD-AIE-001 through GLD-AIE-015) from PROPOSED to APPROVED status.
2. Executed full DQ suite against production Iceberg data via `dq_runner run --spec gold-ai-exposure`.
3. Generated scorecard via `dq_runner scorecard --spec gold-ai-exposure`.

### Results Summary

| Metric | Value |
|--------|-------|
| Rules total | 15 |
| Rules passed | 15 |
| Rules failed | 0 |
| Rules errored | 0 |
| P0 gate | PASS |

### Priority Breakdown

| Priority | Count | Passed | Failed |
|----------|-------|--------|--------|
| P0 | 12 | 12 | 0 |
| P1 | 1 | 1 | 0 |
| P2 | 1 | 1 | 0 |

### Key Validations

- Grain uniqueness (soc_code): 0 duplicates
- Record ID uniqueness: 0 duplicates, 0 nulls
- Row count: within 370-409 range (389 rows)
- Value ranges: exposure_score [0-10], stat_res [1-10], boss_ai_score [1-10] -- all valid
- Inverse invariant: stat_res + boss_ai_score = 11 holds for all 389 rows
- Derivation consistency: stat_res = LEAST(11 - exposure_score, 10) and boss_ai_score = GREATEST(exposure_score, 1) verified
- Cross-validation: all 389 SOC codes exist in consumable.occupation_profiles
- SOC format: all match XX-XXXX pattern
- Completeness: all 9 columns non-null across all rows
- Rationale length: all >= 100 characters
- Coverage: ai_exposure covers >= 40% of occupation_profiles SOC codes (46.8%)

### Regressions

No prior successful execution to compare against (previous run executed 0 rules due to PROPOSED status).

### Non-blocking Issues

- Governance DB sync failed with `ArrowInvalid: Column 'category' is declared non-nullable but contains nulls`. This is a metadata table schema issue, not a data quality issue. DQ results were written to JSON successfully.

### Artifacts

- Results: governance/dq-results/gold-ai-exposure-20260409T212759Z.json
- Scorecard: governance/dq-scorecards/gold-ai-exposure-scorecard.md
- Rules: governance/dq-rules/gold-ai-exposure.json (all 15 rules now APPROVED, will advance to ACTIVE)
