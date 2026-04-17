# DQ Scorecard: silver-onet-experience

- **Spec**: `docs/specs/onet-experience-requirements.md`
- **Zone**: Silver
- **Table**: `base.onet_experience_profiles`
- **Iceberg snapshot**: `5745163851101673330`
- **Run ID**: `0c24bea4`
- **Executed at (UTC)**: 2026-04-17T02:30:11.770710+00:00
- **Rules file**: `governance/dq-rules/silver-onet-experience.json`

## Summary

| Metric | Value |
|---|---|
| Total rules | 10 |
| Passed | 10 |
| Failed | 0 |
| Errored | 0 |
| Pass rate | 100.0% |
| **P0 gate** | **PASS** |
| P1 warnings | 0 |

## Table stats (observed)

- **Total rows**: 765
- **Distinct bls_soc_code**: 765
- **experience_years_typical**: min=0.0, max=8.5, avg=1.709
- **experience_category_median**: min=1, max=9

### Tier distribution

| Tier | Rows |
|---|---|
| early | 404 |
| entry | 304 |
| mid | 56 |
| senior | 1 |

### Spot checks

| BLS SOC | Tier | Category median | Years typical |
|---|---|---|---|
| 11-1011 | senior | 9 | 8.5 |
| 15-1252 | mid | 9 | 7.0 |
| 41-2031 | entry | 5 | 0.75 |

## Rule results

| Rule ID | Priority | Dimension | Status | Actual | Threshold | Name |
|---|---|---|---|---|---|---|
| `SLV-ONET-EXP-001` | P0 | Volume | **PASS** | 0 | `result = 0` | onet_experience_profiles: row count 720-810 |
| `SLV-ONET-EXP-002` | P0 | Validity | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: bls_soc_code format XX-XXXX |
| `SLV-ONET-EXP-003` | P0 | Uniqueness | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: bls_soc_code uniqueness (grain integrity) |
| `SLV-ONET-EXP-004` | P0 | Validity | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: experience_years_typical range 0-15 |
| `SLV-ONET-EXP-005` | P0 | Validity | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: experience_tier in ('entry','early','mid','senior') |
| `SLV-ONET-EXP-006` | P0 | Validity | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: experience_category_median range 1-11 |
| `SLV-ONET-EXP-007` | P1 | Coverage | **PASS** | 0 | `result = 0` | onet_experience_profiles: all 4 tiers represented |
| `SLV-ONET-EXP-008` | P0 | Consistency | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: spot check 11-1011 tier = 'senior' |
| `SLV-ONET-EXP-009` | P0 | Consistency | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: spot check 15-1252 tier = 'mid' |
| `SLV-ONET-EXP-010` | P0 | Consistency | **PASS** | 0 | `result_count = 0` | onet_experience_profiles: spot check 41-2031 tier = 'entry' |

## Failures / errors

_None. All rules passed._

## Gate decision

**P0 gate: PASS.** Silver zone of `onet-experience-requirements` is cleared from the DQ perspective.
