# DQ execution: silver-onet-experience (0c24bea4)

- **Timestamp (UTC)**: 2026-04-17T02:30:11.770710+00:00
- **Spec**: `docs/specs/onet-experience-requirements.md`
- **Zone**: Silver
- **Table**: `base.onet_experience_profiles`
- **Iceberg snapshot**: `5745163851101673330`
- **Rules executed**: 10 (SLV-ONET-EXP-001 through 010)
- **Rules file**: `governance/dq-rules/silver-onet-experience.json`

## Result summary

- Passed: 10 / 10
- Failed: 0
- Errored: 0
- **P0 gate**: PASS

## Observed table stats

- total_rows = 765
- distinct bls_soc_code = 765
- tier distribution = [{'tier': 'early', 'rows': 404}, {'tier': 'entry', 'rows': 304}, {'tier': 'mid', 'rows': 56}, {'tier': 'senior', 'rows': 1}]
- spot checks (11-1011 senior / 15-1252 mid / 41-2031 entry): [{'bls_soc_code': '11-1011', 'experience_tier': 'senior', 'experience_category_median': 9, 'experience_years_typical': 8.5}, {'bls_soc_code': '15-1252', 'experience_tier': 'mid', 'experience_category_median': 9, 'experience_years_typical': 7.0}, {'bls_soc_code': '41-2031', 'experience_tier': 'entry', 'experience_category_median': 5, 'experience_years_typical': 0.75}]

## Regression comparison

_First Silver DQ execution for `base.onet_experience_profiles`; no prior run to compare._

## Artifacts

- Results JSON: `governance/dq-results/silver-onet-experience-20260417-023011.json`
- Scorecard: `governance/dq-scorecards/silver-onet-experience.md`

## Decision

P0 gate cleared. Silver DQ is green for `onet-experience-requirements`. Proceed to Zone 3 (Gold) work.
