# DQ Execution: gold-futureproof-engine-backfill-ai

**Date:** 2026-04-09
**Agent:** @dq-engineer
**Spec:** gold-futureproof-engine-backfill-ai
**Run ID:** 94e7b6d3

## Actions Taken

1. **Approved 20 rules** (GLD-BF-001 through GLD-BF-020) from PROPOSED to APPROVED status.
2. **Deactivated 4 superseded rules** in gold-futureproof-engine.json:
   - GLD-FE-010: stat_res is 100% null (placeholder) -- superseded by GLD-BF-001
   - GLD-FE-011: boss_ai_score is 100% null (placeholder) -- superseded by GLD-BF-002
   - GLD-FE-020: stats_available_count range 0-4 (MVP) -- superseded by GLD-BF-006
   - GLD-FE-022: bosses_available_count range 0-4 (MVP) -- superseded by GLD-BF-007
3. **Executed all 20 rules** against real Iceberg data in consumable.program_career_paths (626K rows) and consumable.career_branches (15,944 rows).
4. **Generated scorecard** to governance/dq-scorecards/gold-futureproof-engine-backfill-ai-scorecard.md.

## Results Summary

| Metric | Value |
|--------|-------|
| Total rules | 20 |
| Passed | 20 |
| Failed | 0 |
| Errored | 0 |
| P0 gate | PASS |
| Score | 100% |

## Rule Breakdown by Priority

| Priority | Count | Passed | Failed |
|----------|-------|--------|--------|
| P0 | 16 | 16 | 0 |
| P1 | 3 | 3 | 0 |
| P2 | 1 | 1 | 0 |

## Key Validations Confirmed

- **Validity:** stat_res and boss_ai_score values are in [1, 10] range where non-null (both tables)
- **Consistency:** Inverse invariant stat_res + boss_ai_score = 11 holds perfectly across both tables
- **Consistency:** stat_res/boss_ai_score null agreement (both null or both non-null) confirmed
- **Completeness:** stat_res null rate is within 40-45% (expected ~42.6% based on 340/634 SOC match rate)
- **Coverage:** 20-25% of PCP rows achieve full 5/5 stat pentagon
- **Coverage:** 22-32% of career_branches rows have computable res_delta
- **Volume:** Row counts unchanged -- PCP 580K-700K, career_branches exactly 15,944
- **Consistency:** Delta derivations (res_delta, ai_boss_delta) correct; null when operands null
- **Validity:** stats_available_count and bosses_available_count now correctly range 0-5

## Regressions

None. This is the first execution of backfill-specific rules. The 4 deactivated rules in gold-futureproof-engine.json would now fail (by design) since AI data is populated.

## Notes

- Governance DB sync failed due to known `category` column nullability issue in governance Iceberg tables. This is non-blocking; JSON results file was written successfully.
- All 20 rules advanced from APPROVED to ACTIVE status on first successful execution.
