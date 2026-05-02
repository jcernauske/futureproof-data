# DQ Scorecard - consumable-institution-aura

- **Spec:** `full-pipeline-eada`
- **Table:** `consumable.institution_aura`
- **Snapshot:** `5887248523326294782`
- **Rules file:** `governance/dq-rules/consumable-institution-aura.json`
- **Executed at:** 2026-05-01T23:50:38.020146+00:00
- **Executed by:** @dq-engineer
- **Row count:** 3223
- **Source run:** `b5484940` (`governance/dq-results/full-pipeline-eada-20260501T234758Z.json`)

## Summary

- **Overall pass:** False
- **P0 gate:** PASS (14/14 passed)
- **P1:** 4/5 passed

## Results

| rule_id | priority | dimension | status | expected | actual | notes |
|---|---|---|---|---|---|---|
| CON-AUR-001 | P0 | consistency | PASS | result = 0 | 0 | Row count within FULL OUTER JOIN bounds |
| CON-AUR-002 | P0 | completeness | PASS | result_count = 0 | 0 rows | unitid non-null (100%) |
| CON-AUR-003 | P0 | uniqueness | PASS | result_count = 0 | 0 rows | unitid uniqueness (dedup grain) |
| CON-AUR-004 | P0 | validity | PASS | result = 0 | 0 | record_id non-null and unique |
| CON-AUR-005 | P0 | validity | PASS | result_count = 0 | 0 rows | coverage_tier in {both, finance_only, athletics_only} |
| CON-AUR-006 | P0 | validity | PASS | result_count = 0 | 0 rows | Every row has at least one source TRUE |
| CON-AUR-007 | P0 | consistency | PASS | result_count = 0 | 0 rows | marketing_ratio arithmetic identity |
| CON-AUR-010 | P0 | validity | PASS | result_count = 0 | 0 rows | aura_score in [1, 10] where non-null |
| CON-AUR-011 | P0 | validity | PASS | result_count = 0 | 0 rows | aura_score NULL iff aura_score_basis NULL (v1 invariant) |
| CON-AUR-012 | P0 | consistency | PASS | result_count = 0 | 0 rows | aura_score_version = 'v1' for all rows |
| CON-AUR-013 | P0 | consistency | PASS | result_count = 0 | 0 rows | aura_score = ROUND(aura_score_continuous) |
| CON-AUR-014 | P0 | validity | PASS | result_count = 0 | 0 rows | aura_score_continuous in [1.0, 10.0] where non-null |
| CON-AUR-020 | P1 | referential_integrity | PASS | result_count <= 1611 | 928 rows | Aura UNITIDs join to career_outcomes (or are documented drift) |
| CON-AUR-021 | P1 | coverage | FAIL | result = 0 | 1 | career_outcomes UNITIDs found in aura (>=90%) |
| CON-AUR-030 | P1 | validity | PASS | result = 0 | 0 | aura_score distribution: stratified bucket coverage by aura_score_basis |
| CON-AUR-031 | P1 | validity | PASS | result = 0 | 0 | aura_score median in [4, 7] |
| CON-AUR-032 | P1 | validity | PASS | result_count = 0 | 0 rows | Anchor school spot checks (14 EDA-validated) |
| CON-AUR-033 | P0 | validity | PASS | result_count = 0 | 0 rows | aura_score_basis enum validity (5-value v1 enum) |
| CON-AUR-034 | P0 | consistency | PASS | result_count = 0 | 0 rows | aura_score NULL iff aura_score_basis NULL (explicit v1 invariant) |

## Failures

### CON-AUR-021 - career_outcomes UNITIDs found in aura (>=90%) (P1)

- **Threshold:** `result = 0`
- **Actual raw value:** `1` (violations: 1)
- **Detail:** actual=1.0, threshold=result = 0.0
- **Diagnosis (live DuckDB measurement on snapshot 5887248523326294782):**
  `2,295 matched / 2,559 distinct career_outcomes UNITIDs = 89.68%`, **0.32 pp below the 90% threshold**.
  264 College Scorecard institutions with program-completion rows do not appear in
  `consumable.institution_aura` (i.e., absent from BOTH `base.ipeds_finance` and `base.eada`).
- **Priority:** P1 - does NOT block the P0 gate. Per spec rationale, the 90% threshold is
  spec-pinned (not EDA-calibrated) pending one full annual cycle of observation.
- **Recommended escalation:** @governance-reviewer to acknowledge as P1 warning and either
  (a) widen threshold to 0.89 with rationale, or (b) enumerate the 264 missing UNITIDs
  as documented drift in the EDA report.


## Gate Decision

**consumable.institution_aura is CLEARED for chaos-monkey hardening (P0 gate PASS).** P1 warning(s) present - see Failures section. P1 failures do not block chaos; human review required.
