# DQ Engineer Audit Trail — silver-base-college-scorecard-institution

**Date:** 2026-04-16 (UTC run timestamp 2026-04-16T03:45:32Z)
**Agent:** @dq-engineer
**Spec:** silver-base-college-scorecard-institution
**Target table:** `base.college_scorecard_institution` (in-memory DuckDB mirror; Iceberg table not yet materialized)
**Run ID:** `6bb600a5`
**Evidence Hash:** `8c8b03a16b664a5b`

## Summary

First authoritative DQ gate execution for the silver-base-college-scorecard-institution spec. All 17 SLV-CSI rules passed on the first attempt; the P0 gate is PASS.

## Execution

The Silver Iceberg table does not yet exist — rules were executed against the data the Silver transformer would produce. Driver script: `scripts/dq_execute_silver_csi.py`.

Pipeline:
1. Read cached College Scorecard institution CSV (`/tmp/Most-Recent-Cohorts-Institution.csv`; source = fallback ZIP `Most-Recent-Cohorts-Institution_04172025.zip`).
2. Apply Bronze ingestor filter (PREDDEG=3 OR ICLEVEL=1) + dedup on UNITID + sentinel-to-null coercion → 3,039 Bronze-equivalent rows.
3. Apply `src/silver/college_scorecard_institution_transformer.transform_row` to each row → 3,039 Silver rows (zero skips).
4. Load into in-memory DuckDB table `base.college_scorecard_institution`.
5. Execute all 17 SLV-CSI-* rules verbatim from `governance/dq-rules/silver-base-college-scorecard-institution.json`.

| Run ID   | Executed At (UTC)             | Total | Passed | Failed | Errored | P0 Gate |
|----------|-------------------------------|-------|--------|--------|---------|---------|
| 6bb600a5 | 2026-04-16T03:45:32.219637Z   | 17    | 17     | 0      | 0       | PASS    |

## Rule Inventory

| Priority | Count | Rule IDs |
|----------|-------|----------|
| P0       | 11    | SLV-CSI-001..011 |
| P1       | 5     | SLV-CSI-012, 013, 015, 016, 017 |
| P2       | 1     | SLV-CSI-014 |

Category breakdown (all 100% passing):

| Dimension     | Rules | Passing |
|---------------|-------|---------|
| volume        | 1     | 1       |
| uniqueness    | 2     | 2       |
| completeness  | 6     | 6       |
| validity      | 3     | 3       |
| consistency   | 5     | 5       |
| **Total**     | 17    | 17      |

## Gating Decision

- **P0 gate:** PASS (11/11 P0 rules passed).
- **P1 signals:** all 5 P1 rules passed. Headroom is tight on two:
  - SLV-CSI-015 (q1<=q5 monotonicity): 46 violations vs. threshold 50 (4-row headroom).
  - SLV-CSI-014 (for-profit coverage, P2): 52.63% vs. threshold 50% (2.63pp headroom).
- **Spec status:** cleared for governance completion from the DQ perspective.

## Key Numeric Findings (vs. EDA Predictions)

Every number reproduces the EDA from 2026-04-14 exactly:

| Metric | EDA | Executed |
|--------|----:|---------:|
| Row count | 3,039 | 3,039 |
| Distinct unitid | 3,039 | 3,039 |
| Distinct record_id | 3,039 | 3,039 |
| NP/COA overall coverage | 73.48% | 73.48% |
| Public NP coverage | 89.27% | 89.27% |
| Private nonprofit NP coverage | 70.64% | 70.64% |
| Private for-profit NP coverage | 52.63% | 52.63% |
| NP <= COA violations | 0 | 0 |
| 4yr = annual × 4 tautology violations | 0 | 0 |
| q1 > q5 inversions (total) | 46 | 46 |
| q1 > q5 by control | 7 / 33 / 6 | 7 / 33 / 6 |
| net_price_annual range | [-$1,180, $77,180] | [-$1,180, $77,180] |
| cost_of_attendance_annual range | [$6,362, $87,804] | [$6,362, $87,804] |

## Threshold Corrections That Held

The EDA-informed threshold corrections from @dq-rule-writer were necessary — the logical-model draft thresholds would have produced P0 failures on green data:

| Rule | Draft | Corrected | Actual | Would Draft Fail? |
|------|-------|-----------|-------:|-------------------|
| SLV-CSI-010 net_price_annual coverage | >= 85% | >= 70% | 73.48% | Yes |
| SLV-CSI-011 COA coverage | >= 80% | >= 70% | 73.48% | Yes |
| SLV-CSI-013 Private nonprofit NP coverage | implicit 80% | >= 65% | 70.64% | Yes |
| SLV-CSI-014 Private for-profit NP coverage | implicit 80% | >= 50% | 52.63% | Yes |
| SLV-CSI-015 q1 <= q5 | strict equality | <= 50 violations | 46 | Yes |
| SLV-CSI-016 net_price_annual floor | >= 0 | >= -$5,000 | min -$1,180 | Yes |

## Regression Check vs. Prior Run

No prior Silver DQ run for this spec exists. The Bronze scorecard (`raw-ingest-college-scorecard-institution-scorecard.md`, run `c2578683`) recorded the same q1>q5 inversion count (46) for the Bronze quintile monotonicity rule; this cross-layer consistency is expected and confirms the Silver transform did not introduce synthetic violations.

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Driver script | `scripts/dq_execute_silver_csi.py` |
| Results JSON | `governance/dq-results/silver-base-college-scorecard-institution-20260416T034532Z.json` |
| Scorecard (canonical) | `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md` |
| Audit trail (this file) | `governance/audit-trail/2026-04-16-dq-engineer-silver-base-college-scorecard-institution.md` |

## Decisions

1. Accept run `6bb600a5` as the authoritative Silver DQ gate for silver-base-college-scorecard-institution.
2. Mark the spec as DQ-cleared: no P0 failures, no P1 failures, no errored rules. @governance-reviewer may proceed.
3. No escalation required.
4. Flag two tight-headroom rules for monitoring on future data refreshes:
   - SLV-CSI-015 (q1<=q5) — 4 rows of headroom.
   - SLV-CSI-014 (for-profit coverage) — 2.63pp of headroom.
