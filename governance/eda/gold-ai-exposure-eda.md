## EDA Report: consumable.ai_exposure (Gold)
**Source:** base.karpathy_ai_exposure (Silver)
**Date:** 2026-04-09
**Agent:** @data-analyst
**Source Record Count:** 419 (Silver), 389 after bls_match=true filter (Gold input)
**Gold Field Count:** 9

### Key Findings

- **Gold row count will be 389.** Of 419 Silver rows, 389 have bls_match=true and will promote to Gold. The 30 excluded rows are all soc_resolved_method='unresolved' (24 with null SOC, 6 with broad SOC codes that had no BLS OOH detailed match).
- **No exposure_score=0 rows exist in the bls_match=true subset.** The MIN(11 - exposure_score, 10) cap at 10 is therefore never exercised. All 389 rows have exposure_score between 1 and 10, so stat_res ranges 1-10 and boss_ai_score ranges 1-10 without any floor/ceiling edge cases being triggered.
- **The inverse invariant holds perfectly.** stat_res + boss_ai_score = 11 for all 389 rows (100.0%). No violations. This is guaranteed by the math when exposure_score >= 1: (11 - x) + x = 11.
- **SOC grain is clean.** 389 distinct soc_code values across 389 rows. Zero duplicates.
- **100% cross-validation pass.** All 389 SOC codes exist in consumable.occupation_profiles (832 rows). The Gold DQ rule requiring joinability will pass.
- **Coverage is 46.8%.** 389 of 832 occupation_profiles SOCs have AI exposure data. The remaining 443 occupations will have null stat_res/boss_ai_score in downstream tables.
- **Rationale is 100% complete.** Zero nulls. Minimum length 297 characters, maximum 587, median 404. All rationales exceed the 100-char minimum threshold.
- **Score distribution is roughly symmetric** with a slight right skew. Mean 5.20, median 5.0, IQR [3.0, 7.0]. The mode is 7 (71 rows, 18.3%). Only 1 row has exposure_score=10.

### Derived Field Distributions

#### stat_res (MIN(11 - exposure_score, 10))

| stat_res | Count | Pct   | Meaning           |
|----------|-------|-------|-------------------|
| 1        | 1     | 0.3%  | Minimal resilience |
| 2        | 33    | 8.5%  |                   |
| 3        | 29    | 7.5%  |                   |
| 4        | 71    | 18.3% | (mode)            |
| 5        | 45    | 11.6% |                   |
| 6        | 52    | 13.4% |                   |
| 7        | 45    | 11.6% |                   |
| 8        | 61    | 15.7% |                   |
| 9        | 41    | 10.5% |                   |
| 10       | 11    | 2.8%  | Highly resilient  |

- Range: 1-10 (full range exercised)
- Mean: 5.80, median: 6.0
- The distribution is mirror-symmetric to boss_ai_score (by construction)

#### boss_ai_score (MAX(exposure_score, 1))

| boss_ai_score | Count | Pct   | Meaning       |
|---------------|-------|-------|---------------|
| 1             | 11    | 2.8%  | Easiest boss  |
| 2             | 41    | 10.5% |               |
| 3             | 61    | 15.7% |               |
| 4             | 45    | 11.6% |               |
| 5             | 52    | 13.4% |               |
| 6             | 45    | 11.6% |               |
| 7             | 71    | 18.3% | (mode)        |
| 8             | 29    | 7.5%  |               |
| 9             | 33    | 8.5%  |               |
| 10            | 1     | 0.3%  | Hardest boss  |

- Identical to exposure_score distribution since no exposure_score=0 rows exist (floor at 1 never triggered)
- Range: 1-10 (full range exercised)
- Mean: 5.20, median: 5.0

### Inverse Invariant Verification

| Condition | Rows | stat_res + boss_ai_score = 11? |
|-----------|------|-------------------------------|
| exposure_score >= 1 | 389 (100%) | Yes, all 389 rows |
| exposure_score = 0  | 0 (0%)     | N/A (no rows)     |
| **Total violations** | **0** | **Invariant holds universally** |

Note: The spec defines the invariant as applying "for all rows where exposure_score >= 1." Since no rows have exposure_score=0, the invariant applies to and holds for all 389 Gold rows.

### Cross-Validation: SOC Coverage

| Metric | Value |
|--------|-------|
| ai_exposure SOC codes | 389 |
| occupation_profiles SOC codes | 832 |
| ai_exposure SOCs found in occupation_profiles | 389 (100%) |
| occupation_profiles SOCs with ai_exposure coverage | 389 (46.8%) |
| occupation_profiles SOCs without coverage | 443 (53.2%) |

All 389 Gold SOC codes are joinable to consumable.occupation_profiles. The cross-validation DQ rule will pass.

### Source Field Profiles (bls_match=true subset)

#### exposure_score
- **Type:** INTEGER
- **Null Rate:** 0% (0 of 389)
- **Range:** 1-10
- **Distribution:** min=1, p25=3.0, median=5.0, p75=7.0, max=10, mean=5.20, stddev=2.25
- **Outliers:** 1 row at score=10 (Telemarketers, 0.3%). Low end: 11 rows at score=1 (2.8%)

#### soc_code
- **Type:** STRING
- **Null Rate:** 0% (all non-null by bls_match=true filter)
- **Cardinality:** 389 distinct (100% unique)
- **Pattern:** XX-XXXX format, all validated

#### rationale
- **Type:** STRING
- **Null Rate:** 0%
- **Length:** min=297, max=587, avg=410, median=404, p5=340

#### category
- **Type:** STRING
- **Cardinality:** 24 distinct values
- **Top 3:** healthcare (56), life-physical-and-social-science (38), architecture-and-engineering (33)

#### soc_resolved_method (Silver provenance)
- **direct:** 243 (62.5%)
- **broad_expansion:** 110 (28.3%)
- **title_match:** 36 (9.3%)

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| No exposure_score=0 rows in Gold subset | 0 | 0% | stat_res cap at 10 and boss_ai_score floor at 1 are never triggered. DQ rules should still validate range 1-10 in case future data includes score=0. |
| Only 1 row with exposure_score=10 | 1 | 0.3% | stat_res=1 is extremely rare. Consider flagging if count drops to 0 in future loads. |
| Only 11 rows with exposure_score=1 | 11 | 2.8% | boss_ai_score=1 cluster is small. Not anomalous given domain. |
| 30 rows excluded (bls_match=false) | 30 | 7.2% of Silver | Gold row count should be 389 +/- 5% (370-409). Use this as the row count threshold. |
| Invariant violations | 0 | 0% | Hard block (P0) at 0 violations. Any violation indicates a derivation bug. |
| SOC cross-validation misses | 0 | 0% | Hard block (P0) at 0. Any miss indicates a Silver/Gold data mismatch. |
| 46.8% occupation coverage | 389/832 | 46.8% | This is expected (Karpathy scored 342 OOH occupations; broad expansion brings it to 389). Not an anomaly. |

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| (none) | -- | -- | -- | No anomalies detected. This is a clean, simple derivation from Silver. |

### DQ Rule Threshold Evidence

| Rule | Spec Threshold | Evidence-Based Recommendation |
|------|---------------|-------------------------------|
| stat_res range | 1-10 | Confirmed: actual range is 1-10. Use 1 <= stat_res <= 10 (P0). |
| boss_ai_score range | 1-10 | Confirmed: actual range is 1-10. Use 1 <= boss_ai_score <= 10 (P0). |
| Inverse invariant | stat_res + boss_ai_score = 11 (exposure >= 1) | Confirmed: 0 violations in 389 rows. Apply universally since no exposure=0 rows exist. (P0). |
| Row count | Matches Silver filtered | Use 389 +/- 5% (370-409). (P0). |
| soc_code uniqueness | 100% | Confirmed: 389 distinct of 389 rows. (P0). |
| rationale non-null | 100% | Confirmed: 0 nulls. (P0). |
| Cross-validation with occupation_profiles | 100% match | Confirmed: 389/389 found. (P0). |
