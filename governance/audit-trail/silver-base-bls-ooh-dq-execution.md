# DQ Execution: silver-base-bls-ooh

**Date:** 2026-04-07
**Agent:** @dq-engineer
**Spec:** silver-base-bls-ooh
**Run ID:** 8fb39ca1

## Actions Taken

1. Read 36 DQ rules from `governance/dq-rules/silver-base-bls-ooh.json` (all in PROPOSED status)
2. Approved all 36 rules (PROPOSED -> APPROVED)
3. Executed all 36 rules against the persistent Iceberg warehouse at `data/silver/iceberg_warehouse`, table `base.bls_ooh` (832 rows)
4. Generated scorecard from execution results

## Results Summary

- **Total rules:** 36
- **Passed:** 36
- **Failed:** 0
- **Errored:** 0
- **P0 gate:** PASS

### By Priority

| Priority | Count | Passed | Failed |
|----------|-------|--------|--------|
| P0       | 16    | 16     | 0      |
| P1       | 20    | 20     | 0      |

### By Dimension

- Uniqueness: 2 rules, all passed
- Validity: 10 rules, all passed
- Volume: 1 rule, passed
- Referential Integrity: 2 rules, all passed
- Consistency: 5 rules, all passed
- Completeness: 10 rules, all passed
- Coverage: 1 rule, passed

## Rule Lifecycle

All 36 rules advanced: PROPOSED -> APPROVED -> ACTIVE (on first successful execution)

## Regressions

No previous runs for this spec exist. This is the baseline execution.

## Artifacts Produced

- Results: `governance/dq-results/silver-base-bls-ooh-20260407T175602Z.json`
- Scorecard: `governance/dq-scorecards/silver-base-bls-ooh-scorecard.md`
- Rules file updated: `governance/dq-rules/silver-base-bls-ooh.json` (all 36 rules now ACTIVE)

## Notes

- A non-blocking error occurred during governance DB sync (pyarrow schema issue with a nullable `category` column). This did not affect rule execution or results. The DQ runner executed all SQL rules directly against DuckDB/Iceberg and produced correct results.
- All rules executed in under 3ms each, total execution time well under 1 second.
