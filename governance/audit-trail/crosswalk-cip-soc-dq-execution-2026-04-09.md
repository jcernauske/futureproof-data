# DQ Execution Audit Trail: crosswalk-cip-soc

**Date:** 2026-04-09
**Agent:** @dq-engineer
**Spec:** crosswalk-cip-soc
**Run ID:** fdb5660f
**Executed at:** 2026-04-09T03:27:36Z

## Summary

Executed 20 DQ rules (8 Bronze, 12 Silver) against the persistent Iceberg warehouse.
All rules were first approved from PROPOSED to APPROVED status, then executed against real data.

- **Total rules:** 20 (crosswalk-cip-soc specific; 28 total including other specs in run)
- **Passed:** 19 / 20 (95%)
- **Failed:** 1 / 20 (SLV-XW-011, P1)
- **Errored:** 0

## P0 Gate: PASS

All 14 P0 rules passed with zero violations. This includes:
- CIP format validation (Bronze + Silver)
- SOC format validation (Bronze + Silver)
- Grain uniqueness (both natural key and surrogate key)
- Row count volume checks (Bronze: 6,097 in range 5,500-6,500; Silver: 5,903 in range 5,500-6,200)
- Null completeness (all source and metadata fields)
- No-match sentinel filtering (zero 99-9999 rows in Silver)
- SOC major group validity (all 22 valid groups)
- match_quality enum validity
- Derivation consistency (cip_family, soc_major_group, match_quality vs flags)
- record_id format (xw-<16 hex chars>)

## P1 Warning: SLV-XW-011

**Rule:** has_bls_match should be TRUE for 90-97% of Silver rows
**Actual:** 97.39% (5,749 / 5,903)
**Expected range:** 90-97%
**Diagnosis:** The actual BLS match rate (97.39%) slightly exceeds the upper bound (97%).
The EDA predicted 94.6% based on distinct SOC code matching (820/867 SOCs).
The row-level rate is higher because high-frequency SOC codes (those with many CIP mappings)
tend to have BLS matches. This is a threshold calibration issue, not a data quality problem.
**Recommendation:** Widen the rule upper bound from 97% to 98%.

## P2/P3 Informational Rules: All Passed

- BRZ-XW-008: 194 sentinel rows (in range 180-210) -- PASS
- SLV-XW-018: 47 unmatched BLS SOCs (threshold <= 60) -- PASS
- SLV-XW-019: 69 unmatched O*NET SOCs (threshold <= 80) -- PASS
- SLV-XW-020: 1,949 unmatched Scorecard CIPs (threshold >= 1,900) -- PASS

## Regressions

No previous DQ runs exist for this spec. This is the first execution. No regression comparison possible.

## Artifacts Produced

- Results: governance/dq-results/crosswalk-cip-soc-20260409T032736Z.json
- Scorecard: governance/dq-scorecards/crosswalk-cip-soc-scorecard.md
- Audit trail: governance/audit-trail/crosswalk-cip-soc-dq-execution-2026-04-09.md

## Decision

P0 gate PASSES. The spec is not blocked by DQ failures.
The single P1 failure (SLV-XW-011) is a threshold calibration issue where the data
is better than expected. Recommended action: widen the upper bound to 98%.
Human review recommended per P1 protocol.
