# Audit Trail: Gold FutureProof Engine EDA

**Date:** 2026-04-09
**Agent:** @data-analyst
**Spec:** docs/specs/gold-futureproof-engine.md
**Artifact:** governance/eda/gold-futureproof-engine-eda.md

## What Was Analyzed

Five source tables profiled for the Gold FutureProof Engine spec:
- consumable.career_outcomes (69,947 rows)
- consumable.occupation_profiles (832 rows)
- consumable.onet_work_profiles (798 rows)
- consumable.career_transitions (15,944 rows)
- base.cip_soc_crosswalk (5,903 rows)

Full join chain simulated with CIP 4-digit prefix matching, dedup, and stat derivation.

## Key Findings

1. **Row count 626,406 exceeds spec estimate of 150K-500K.** DQ rule range must be widened.
2. **CIP prefix match coverage: 91.0% of CIPs, 97.1% of rows.** Confirmed spec estimates.
3. **47.8% of grain tuples require dedup** (1.8M raw rows collapse to 626K).
4. **stat_ern/stat_roi computable for only 41.4%/37.6% of rows** due to Scorecard earnings/debt suppression (64% null).
5. **Match quality 93.2% "full"** -- better than spec estimate of 76.6%.
6. **Overall confidence 63.5% "low"** driven by Scorecard null rates, not join failures.
7. **24 O*NET partial profiles** create null HMN/burnout despite match_quality="full."
8. **22 crosswalk SOCs** have no occupation title from either BLS or O*NET.

## Threshold Recommendations

| Metric | Recommended Threshold | Evidence |
|--------|----------------------|----------|
| Row count (Table 1) | 580,000-700,000 | Actual: 626,406 |
| Row count (Table 2) | 15,944 (exact) | 1:1 with career_transitions |
| CIP prefix match rate | >= 90% | Actual: 91.0% |
| match_quality "full" | >= 90% | Actual: 93.2% |
| stats_available >= 2 | >= 95% | Actual: 94.4% |
| overall_confidence "high" | >= 30% | Actual: 33.9% |
| branch_has_full_data True | >= 95% | Actual: 96.5% |

## Decisions

- Row count DQ range in spec (150K-500K) needs update based on evidence.
- occupation_title required constraint may need relaxation for 22 unmapped SOCs.
- match_quality semantic gap (row exists vs scores available) documented for @dq-rule-writer awareness.
