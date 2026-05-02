# DQ Execution Audit - consumable.institution_aura

- **Spec:** `full-pipeline-eada`
- **Table:** `consumable.institution_aura`
- **Snapshot:** `5887248523326294782` (3,223 rows, 19 columns)
- **Rules file:** `governance/dq-rules/consumable-institution-aura.json` (19 rules: CON-AUR-001..007, 010..014, 020..021, 030..034)
- **Executed by:** @dq-engineer
- **Executed at:** 2026-05-01T23:50:38Z (run 2026-05-01T23:47:58Z)
- **Source run id:** `b5484940`
- **Source results:** `governance/dq-results/full-pipeline-eada-20260501T234758Z.json`
- **Scorecard JSON:** `governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.json`
- **Scorecard MD:** `governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.md`

## Lifecycle Actions

- All 19 CON-AUR-* rules transitioned `proposed -> approved` via `python -m brightsmith.infra.dq_runner approve <RULE-ID>` prior to execution.
- All 19 transitioned `approved -> active` automatically on first successful execution against real data.

## Summary

- **Rules executed:** 19 / 19 (no errors, no skips)
- **Passed:** 18
- **Failed:** 1 (CON-AUR-021, P1)
- **P0 gate:** PASS (14 / 14 P0 rules passed)
- **P1 results:** 4 / 5 passed

## P0 Detail (14 rules, all PASS)

CON-AUR-001 (row count bound), CON-AUR-002 (unitid non-null), CON-AUR-003 (unitid uniqueness),
CON-AUR-004 (record_id non-null + unique), CON-AUR-005 (coverage_tier enum), CON-AUR-006 (>=1 source TRUE),
CON-AUR-007 (marketing_ratio arithmetic identity), CON-AUR-010 (aura_score in [1,10]),
CON-AUR-011 (aura_score NULL iff aura_score_basis NULL - v1 invariant), CON-AUR-012 (aura_score_version='v1'),
CON-AUR-013 (aura_score = ROUND(continuous)), CON-AUR-014 (continuous in [1.0, 10.0]),
CON-AUR-033 (aura_score_basis enum 5-value v1), CON-AUR-034 (NULL-iff-NULL explicit form).

All 14 P0 rules returned violations=0. No regressions vs. EDA-calibrated live observations.

## P1 Detail (5 rules, 4 PASS / 1 FAIL)

- **PASS** CON-AUR-020 referential integrity: 928 aura UNITIDs without career_outcomes counterparts (well below the 1,611 cap; the bulk are athletics_only and finance_only rows which legitimately have no Scorecard program-completion presence).
- **FAIL** CON-AUR-021 coverage `>=90% of distinct career_outcomes UNITIDs found in aura`. Live measurement: **89.68%** (2,295 matched / 2,559 distinct), 0.32 percentage points below the 90% threshold. 264 College Scorecard institutions with program-completion rows are absent from BOTH `base.ipeds_finance` and `base.eada`. Threshold is spec-pinned (not EDA-calibrated) per CON-AUR-021 rationale - "raises to P0 candidate after one full annual cycle of observation".
- **PASS** CON-AUR-030 stratified bucket coverage: 10 of 10 overall buckets populated; per-stratum minimum >=4 of 10 across all four `aura_score_basis` strata. Threshold passes by margin.
- **PASS** CON-AUR-031 aura_score median == 7 (within [4, 7] band, exactly at upper edge as the EDA predicted).
- **PASS** CON-AUR-032 14 anchor schools all match expected v1 scores exactly (Harvard 9, Princeton 10, Stanford 10, MIT 9, Yale 9, Duke 9, Cornell 9, Northwestern 9, Alabama 9, Phoenix 10, Ohio State 8, Michigan 9, Grand Canyon 8, Liberty 5).

## Regression Comparison

No prior `consumable-institution-aura-*` scorecards exist - this is the first execution of the v1 ruleset against real data. Baseline established at this run.

## Decisions Required

- **CON-AUR-021 (P1) failure** does NOT block the P0 gate or chaos-monkey hardening, but requires @governance-reviewer acknowledgment per the gating framework. Recommended dispositions:
  1. **Widen threshold to 0.89** with rationale documented in the rules file (the current 89.68% is inside the natural noise floor for a ruleset whose constituent base tables - IPEDS Finance and EADA - have independent Title IV / NCAA-Title-IX coverage universes that don't perfectly overlay College Scorecard's program-completion universe).
  2. **Enumerate the 264 missing UNITIDs** in the EDA report as documented drift.
  3. **Defer** until one full annual refresh cycle establishes whether 89.68% is a stable plateau or a thin-tail artifact.

## Gate Decision

**P0 gate: PASS.** consumable.institution_aura is CLEARED for chaos-monkey hardening. The single P1 failure (CON-AUR-021) is logged for @governance-reviewer review and does not gate progression.
