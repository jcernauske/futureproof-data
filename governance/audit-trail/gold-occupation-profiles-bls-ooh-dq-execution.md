# Audit Trail: DQ Execution — gold-occupation-profiles-bls-ooh

**Date:** 2026-04-07
**Agent:** @dq-engineer
**Spec:** gold-occupation-profiles-bls-ooh
**Table:** consumable.occupation_profiles (832 rows)
**Run ID:** acb62160
**Executed At:** 2026-04-07T20:24:20Z

## Execution Summary

- **Rules Executed:** 53 of 54 (1 deferred: GLD-OP-048, golden dataset validation)
- **Rules Passed:** 52
- **Rules Failed:** 1 (GLD-OP-039, P1)
- **Rules Errored:** 0
- **P0 Gate:** PASS (all 35 P0 rules passed)

## Rule Lifecycle

- 53 rules approved from PROPOSED to APPROVED status
- 52 rules advanced from APPROVED to ACTIVE on first successful execution
- 1 rule (GLD-OP-048) remains DEFERRED pending golden dataset creation by @primary-agent

## P0 Results (35 rules — all PASS)

All P0 rules passed with zero violations. Key validations confirmed:
- Grain uniqueness: 832 unique soc_code values, 0 duplicates
- Row count: exactly 832 (1:1 carry-forward from Silver)
- SOC code format: all match XX-XXXX pattern
- GRW score range: all 832 values within [1.0, 10.0]
- Market score range: all 832 values within [1.0, 10.0]
- Wage percentile ranges: all within [0.0, 1.0]
- Null-wage population: exactly 23 occupations, consistent across all derived fields
- Confidence tier: 3 valid values, correct derivation logic
- wage_tier/wage_available correspondence: exact
- NOT NULL fields: all populated
- Data completeness derivation: formula-verified

## P1 Results (18 rules — 17 PASS, 1 FAIL)

### GLD-OP-039: FAIL (P1 — WARNING, non-blocking)

**Rule:** Market score formula consistency: 0.6*grw + 0.4*openings
**Violations:** 828 (of 832 non-null market scores)
**Root Cause:** SQL formulation error in the rule definition, NOT a data quality issue. The correlated subquery `SELECT PERCENT_RANK() OVER (ORDER BY o2.openings_annual_avg) FROM consumable.occupation_profiles o2 WHERE o2.soc_code = op.soc_code` computes PERCENT_RANK within a single-row partition (since soc_code is the unique grain), always returning 0.0 rather than the correct rank across all occupations. The rule SQL needs to be rewritten by @dq-rule-writer to correctly recompute the openings PERCENT_RANK in the validation query.
**Impact:** No action required on data. Rule definition should be corrected by @dq-rule-writer.

### All other P1 rules PASS:

- GRW score mean: within 4.5-6.5 range
- GRW bucket coverage: all 10 of 10 buckets populated
- Market score std dev: > 1.0
- Market score bucket coverage: >= 7 of 10
- Confidence tier exact counts: high=735, medium=74, low=23
- Wage tier quartile alignment: within expected ranges
- GRW/growth_category monotonic alignment: 0 violations
- SOC major group: all 22 represented
- Broad occupation flag: exactly 7
- Catchall flag: exactly 70
- No broad+catchall overlap: 0 violations

## Regressions

No previous DQ runs exist for this spec. This is the baseline execution.

## Artifacts Produced

- Results JSON: `governance/dq-results/gold-occupation-profiles-bls-ooh-20260407T202420Z.json`
- Scorecard: `governance/dq-scorecards/gold-occupation-profiles-bls-ooh-scorecard.md`
- Rules file updated: `governance/dq-rules/gold-occupation-profiles-bls-ooh.json` (statuses updated)
