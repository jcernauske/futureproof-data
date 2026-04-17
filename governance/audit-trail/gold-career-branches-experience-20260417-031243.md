# DQ execution: gold-career-branches-experience (988dd93e)

- **Timestamp (UTC)**: 2026-04-17T03:12:43.311249+00:00
- **Spec**: `docs/specs/onet-experience-requirements.md`
- **Zone**: Gold
- **Table**: `consumable.career_branches`
- **Iceberg snapshot**: `5050994341048740398`
- **Rules executed**: 3 (GLD-CB-EXP-001, 002, 003)
- **Rules file**: `governance/dq-rules/gold-career-branches-experience.json`

## Result summary

- Passed: 3 / 3
- Failed: 0
- Errored: 0
- **P0 gate**: PASS
- **P1 warnings**: 0

## Observed table stats

- total_rows = 15944
- null_rates_pct = {'related_experience_years': 5.4691, 'source_experience_years': 3.8761, 'experience_delta_years': 9.0943, 'related_experience_tier': 5.4691}
- experience_delta_years_where_both_nonnull = {'rows': 14494, 'min': -7.75, 'max': 8.5, 'avg': 0.10428622878432538}
- senior_tier_check = {'rows': 39, 'min_related_experience_years': 8.5, 'max_related_experience_years': 8.5}
- related_experience_tier_distribution = [{'tier': 'early', 'rows': 8121}, {'tier': 'entry', 'rows': 5701}, {'tier': 'mid', 'rows': 1211}, {'tier': '(null)', 'rows': 872}, {'tier': 'senior', 'rows': 39}]

## Rule status transition

All 3 rules passed against real Gold data (snapshot `5050994341048740398`). Rule status in `governance/dq-rules/gold-career-branches-experience.json` updated from `proposed` to `active` for GLD-CB-EXP-001, GLD-CB-EXP-002, GLD-CB-EXP-003.

## Regression comparison

_First Gold DQ execution for the experience-addendum rules on `consumable.career_branches`; no prior run to compare._

## Artifacts

- Results JSON: `governance/dq-results/gold-career-branches-experience-20260417-031243.json`
- Scorecard: `governance/dq-scorecards/gold-career-branches-experience.md`

## Decision

P0 gate cleared. Gold addendum DQ is green for `onet-experience-requirements`. Proceed to Zone 4 work.
