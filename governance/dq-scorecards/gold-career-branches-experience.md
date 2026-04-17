# DQ Scorecard: gold-career-branches-experience

- **Spec**: `docs/specs/onet-experience-requirements.md`
- **Zone**: Gold
- **Table**: `consumable.career_branches`
- **Iceberg snapshot**: `5050994341048740398`
- **Run ID**: `988dd93e`
- **Executed at (UTC)**: 2026-04-17T03:12:43.311249+00:00
- **Rules file**: `governance/dq-rules/gold-career-branches-experience.json`

## Summary

| Metric | Value |
|---|---|
| Total rules | 3 |
| Passed | 3 |
| Failed | 0 |
| Errored | 0 |
| Pass rate | 100.0% |
| **P0 gate** | **PASS** |
| P1 warnings | 0 |

## Table stats (observed)

- **Total rows**: 15944
- **Null rates (%)**: related_experience_years=5.4691, source_experience_years=3.8761, experience_delta_years=9.0943, related_experience_tier=5.4691
- **experience_delta_years (both-sides non-null)**: rows=14494, min=-7.75, max=8.5, avg=0.104
- **Senior tier rows**: 39 (min years=8.5, max years=8.5)

### related_experience_tier distribution

| Tier | Rows |
|---|---|
| early | 8121 |
| entry | 5701 |
| mid | 1211 |
| (null) | 872 |
| senior | 39 |

## Rule results

| Rule ID | Priority | Dimension | Status | Actual | Threshold | Name |
|---|---|---|---|---|---|---|
| `GLD-CB-EXP-001` | P1 | Completeness | **PASS** | 0 | `result = 0` | career_branches: related_experience_years null rate < 15% |
| `GLD-CB-EXP-002` | P1 | Validity | **PASS** | 0 | `result_count = 0` | career_branches: experience_delta_years range -12 to 12 (NULL-propagating) |
| `GLD-CB-EXP-003` | P0 | Consistency | **PASS** | 0 | `result_count = 0` | career_branches: senior tier consistency (related_experience_years >= 8) |

## Failures / errors

_None. All rules passed._

## Gate decision

**P0 gate: PASS.** Gold addendum DQ for `onet-experience-requirements` is cleared. Rule status advanced from `proposed` to `active`.
