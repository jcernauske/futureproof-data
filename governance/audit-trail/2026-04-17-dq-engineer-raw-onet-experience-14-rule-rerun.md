# DQ Engineer -- raw-onet-experience 14-rule re-execution

**Date:** 2026-04-17T01:39:25Z
**Agent:** @dq-engineer
**Spec:** docs/specs/onet-experience-requirements.md
**Zone:** Bronze (Raw)
**Trigger:** Rule set expanded from 10 to 14 by @dq-rule-writer following
`bs:adversarial-auditor` gap-closing recommendations (audit report
`governance/audit-reports/onet-experience-adversarial-20260417-013427.md`).

## Summary

Re-executed all 14 rules from `governance/dq-rules/raw-onet-experience.json`
against the Iceberg-backed parquet for `raw.onet_experience` (35,998 rows).

- **Rules executed:** 14 (P0: 8, P1: 6)
- **Passed:** 13
- **Failed:** 1 (P1 -- RAW-ONET-EXP-014)
- **Errored:** 0
- **P0 gate:** PASS (8/8)

## Regression vs prior run (2026-04-17T01:20:02Z, run_id 650f134b)

Rules 001-010 all return identical results. No data changed between runs
(same parquet file); this re-execution is a pure rule-set expansion.

## New rules (011-014) outcomes

| Rule | Priority | Expected | Actual | Match |
|------|----------|----------|--------|-------|
| RAW-ONET-EXP-011 canonical (scale_id, element_id) | P0 | PASS | PASS | yes |
| RAW-ONET-EXP-012 per-scale category value ENUM | P0 | PASS | PASS | yes |
| RAW-ONET-EXP-013 recommend_suppress ENUM + Y rate < 5% | P1 | PASS | PASS | yes |
| RAW-ONET-EXP-014 no group with MAX(data_value) >= 99.0 | P1 | PASS | **FAIL** | no |

## Rule 014 FAIL -- diagnosis

Two violations, both on RL scale:
- `11-3051.01` (Transportation, Storage, and Distribution Managers), RL, 100.00
- `29-9092.00` (Genetic Counselors), RL, 100.00

Per the task briefing and the rule's own rationale text, rule 014 was
intended to be scoped to RW: *"P1, scoped to RW per writer's tuning
recommendation"*. The SQL as written is unscoped and therefore flags RL
groups where MAX(data_value) = 100.00 is legitimate (and EDA-documented).

Verified: with `WHERE scale_id = 'RW'` added to the query, zero violations
are returned. The original adversarial probe P2 (all-entry-level RW
collapse) would still be trapped by the corrected rule.

## Decision & escalation

- Per @dq-engineer scope boundary: this agent does not modify rule
  definitions. Rule SQL left unchanged.
- Escalated to @governance-reviewer. Recommendation in scorecard:
  accept as documented false-positive until @dq-rule-writer narrows the
  SQL to `WHERE scale_id = 'RW'`. Silver consumes only scale_id='RW'
  rows and no RW group violates, so there is no data-quality risk to
  downstream.
- **P0 gate remains PASS.** Bronze is clear from a DQ perspective.

## Artifacts

- Results JSON: `governance/dq-results/raw-onet-experience-20260417-013925.json`
- Updated scorecard: `governance/dq-scorecards/bronze-onet-experience.md`
- Executor: `scripts/dq_execute_onet_experience.py` (unchanged; reads rules from JSON dynamically)

## Data source provenance

- Parquet: `data/bronze/iceberg_warehouse/bronze/onet_experience/data/00000-0-f09a19fa-5466-46ed-a39d-58f4db0dac5e.parquet`
- Rules file sha256 (first 16 hex): `3ce1d53cb911c75c`
- 35,998 rows, 878 distinct onet_soc_codes -- identical counts to 01:20:02Z baseline.
