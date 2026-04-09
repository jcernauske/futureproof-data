## EDA Report: Gold consumable.program_career_paths + consumable.career_branches
**Source:** consumable.career_outcomes, consumable.occupation_profiles, consumable.onet_work_profiles, consumable.career_transitions, base.cip_soc_crosswalk
**Date:** 2026-04-09
**Agent:** @data-analyst
**Reference Spec:** docs/specs/gold-futureproof-engine.md
**Table 1 Estimated Row Count:** 626,406
**Table 2 Estimated Row Count:** 15,944

---

### Key Findings

1. **Row count estimate is 626,406 -- EXCEEDS spec range.** The spec estimates 150,000-500,000 rows for program_career_paths. The actual deduped grain count is 626,406. The DQ rule row count range must be widened to at least 600,000-700,000. The overshoot comes from higher-than-expected fan-out: median 5 SOC codes per CIP4 prefix, but heavy-tail CIPs like 52.02 (Business Admin) map to 43 SOC codes.

2. **CIP prefix match coverage confirmed at 91.0% (distinct CIPs) and 97.1% (rows).** 355 of 390 Scorecard CIP codes find at least one crosswalk match via 4-digit prefix. The 35 unmatched CIPs account for only 2,008 rows (2.9%). The largest unmatched CIP is 30.99 "Multi/Interdisciplinary Studies, Other" with 699 rows -- these are catch-all "Other" categories (XX.99, XX.00) that the crosswalk does not map.

3. **Massive dedup requirement: 47.8% of grain tuples have duplicates.** The raw INNER JOIN produces 1,817,092 rows. After dedup on (unitid, cipcode, soc_code), this collapses to 626,406 rows. 299,513 grain combinations appear in multiple crosswalk paths (same SOC code reached via different 6-digit CIPs). Max duplicates per grain: 37. The dedup logic must handle this correctly.

4. **stat_ern computable for only 41.4% of rows.** The bottleneck is cip_family_earnings_rank, which is null for 64.0% of career_outcomes rows (programs with suppressed earnings). wage_percentile_overall is available for 96.3% of joined rows. This means the majority of rows will have null stat_ern.

5. **stat_roi computable for only 37.6% of rows.** debt_to_earnings_annual is null for 68.9% of career_outcomes. The ROI stat and boss_loans_score will be null for the majority of output rows.

6. **stat_grw and stat_hmn have strong coverage: 97.4% and 93.0%.** These occupation-level stats are available for nearly all rows that match the crosswalk, since BLS and O*NET have broad SOC coverage.

7. **Match quality distribution is heavily "full" (93.2%).** 584,051 of 626,406 rows have both BLS and O*NET data. Only 830 rows (0.1%) are "scorecard_only" with no occupation data at all. The spec's estimate of 76.6% "full" was conservative -- the actual crosswalk-to-BLS/O*NET coverage is stronger than estimated.

8. **Overall confidence skews "low" (63.5%) due to Scorecard nulls, not join failures.** 397,816 rows are "low" confidence despite 93.2% having "full" match quality. The reason: stats_available_count requires both ERN and ROI to reach 4 stats, and both depend on Scorecard earnings/debt data that is null for ~64% of programs. High confidence (33.9%) requires 4+ stats AND full match quality.

9. **All career_outcomes rows are credential_level=3 (Bachelor's).** No credlev fan-out issue. Each (unitid, cipcode) appears exactly once in career_outcomes.

10. **O*NET has 24 "partial" profiles with null HMN/burnout scores.** These include SOC 13-2051 (Financial and Investment Analysts), which is a high-relevance occupation. These profiles have activity_profile_available=False and context_profile_available=False. Their presence in the golden dataset means the ISU Business Admin -> Financial Analyst trace will show null HMN and null burnout.

11. **CIP 99.9999 "NO MATCH" in crosswalk (180 SOC codes) is harmless.** No Scorecard row has cipcode=99.99, so these rows will never join.

12. **22 crosswalk SOC codes (2.5%) have no title from either BLS or O*NET.** The spec requires occupation_title as a required field sourced from occupation_profiles OR onet_work_profiles. These 22 SOCs will have null occupation_title, which violates the required constraint unless handled.

---

### Source Table Profiles

#### 1. consumable.career_outcomes (69,947 rows, 31 fields)

**Grain:** unitid x cipcode x credential_level (all credlev=3)

| Field | Null Rate | Notes |
|-------|-----------|-------|
| unitid | 0.0% | IPEDS ID, always present |
| cipcode | 0.0% | 390 distinct values, XX.XX format |
| institution_name | 0.0% | |
| program_name | 0.0% | |
| cip_family | 0.0% | 45 distinct families |
| cip_family_name | 0.0% | |
| earnings_1yr_median | 64.0% (44,751 null) | Privacy-suppressed for small cohorts |
| earnings_1yr_p25 | 0.1% (36 null) | |
| earnings_1yr_p75 | 0.1% (36 null) | |
| debt_median | 63.1% (44,138 null) | |
| debt_to_earnings_annual | 68.9% (48,184 null) | Range: 0.050-5.328, median=0.616 |
| cip_family_earnings_rank | 64.0% (44,751 null) | Range: 0.0-1.0, uniform distribution |
| confidence_tier | 0.0% | |

**Top CIP codes by row count:** 52.02 (1,701), 42.01 (1,438), 26.01 (1,411), 23.01 (1,334), 54.01 (1,303)

#### 2. consumable.occupation_profiles (832 rows, 31 fields)

**Grain:** soc_code (unique)

| Field | Null Rate | Notes |
|-------|-----------|-------|
| soc_code | 0.0% | 832 distinct, XX-XXXX format |
| occupation_title | 0.0% | |
| grw_score_rounded | 0.0% | Range 1-10, median=6, right-skewed |
| median_annual_wage | 2.8% (23 null) | |
| wage_percentile_overall | 2.8% (23 null) | Range 0.0-1.0, uniform |
| wage_percentile_education_tier | 2.8% (23 null) | Range 0.0-1.0, uniform |
| market_score_rounded | 0.0% | |
| growth_category | 0.0% | |
| employment_current | 0.0% | |
| education_level_name | 0.0% | |
| soc_major_group_name | 0.0% | |

**GRW score distribution:** 1(19), 2(35), 3(79), 4(111), 5(153), 6(225), 7(148), 8(41), 9(18), 10(3)

#### 3. consumable.onet_work_profiles (798 rows, 27 fields)

**Grain:** bls_soc_code (unique)

| Field | Null Rate | Notes |
|-------|-----------|-------|
| bls_soc_code | 0.0% | 798 distinct |
| primary_title | 0.0% | |
| hmn_score_rounded | 3.0% (24 null) | Range 1-10 when present |
| burnout_score_rounded | 3.0% (24 null) | |
| top_5_activities | 3.0% (24 null) | JSON string |
| top_human_activities | 3.0% (24 null) | JSON string |
| burnout_drivers | 3.0% (24 null) | JSON string |
| time_pressure | 3.0% (24 null) | |
| work_hours | 3.0% (24 null) | |

**HMN score distribution:** 1(2), 2(37), 3(133), 4(194), 5(227), 6(126), 7(40), 8(12), 9(2), 10(1)

The 24 null profiles are "partial" data_completeness_tier occupations with no activity or context data.

#### 4. consumable.career_transitions (15,944 rows, 14 fields)

**Grain:** bls_soc_code x related_bls_soc_code (unique)

| Field | Notes |
|-------|-------|
| bls_soc_code | 798 distinct source SOCs |
| related_bls_soc_code | 796 distinct target SOCs |
| best_index | Range: 1-75 |
| is_primary | True: 8,072, False: 7,872 |

**Relatedness tier:** Primary-Short (4,134), Primary-Long (3,938), Supplemental (7,872)
**Transitions per source:** min=14, median=20, max=75, mean=20.0

#### 5. base.cip_soc_crosswalk (5,903 rows, 13 fields)

**Grain:** cipcode x soc_code (unique, no duplicates)

| Field | Notes |
|-------|-------|
| cipcode | 1,949 distinct 6-digit CIPs (XX.XXXX), 416 distinct 4-digit prefixes |
| soc_code | 867 distinct SOC codes |
| has_scorecard_match | FALSE for all 5,903 rows (uses strict 6-digit match -- not usable) |

**Includes 180 rows for CIP 99.9999 "NO MATCH"** mapping to 180 SOC codes. These are orphan SOCs with no CIP mapping and will never join to Scorecard data.

---

### CIP Prefix Join Analysis

#### Coverage

| Metric | Value |
|--------|-------|
| Scorecard distinct CIP codes | 390 |
| Matched via 4-digit prefix | 355 (91.0%) |
| Unmatched | 35 (9.0%) |
| Scorecard rows matched | 67,939 (97.1%) |
| Scorecard rows unmatched | 2,008 (2.9%) |

#### Unmatched CIP Codes (top 10 by row count)

| CIP | Program | Rows | Pattern |
|-----|---------|------|---------|
| 30.99 | Multi/Interdisciplinary Studies, Other | 699 | .99 "Other" catch-all |
| 30.00 | Multi-/Interdisciplinary Studies, General | 293 | .00 "General" catch-all |
| 51.11 | Health/Medical Preparatory Programs | 272 | Prep programs not in crosswalk |
| 51.99 | Health Professions, Other | 155 | .99 catch-all |
| 52.99 | Business, Other | 136 | .99 catch-all |
| 39.99 | Theology, Other | 68 | .99 catch-all |
| 11.99 | Computer Science, Other | 50 | .99 catch-all |
| 15.99 | Engineering Tech, Other | 49 | .99 catch-all |
| 22.99 | Legal Professions, Other | 41 | .99 catch-all |
| 44.99 | Public Admin, Other | 38 | .99 catch-all |

**Pattern:** Unmatched CIPs are predominantly XX.99 "Other" and XX.00 "General" categories -- these are catch-all buckets that the crosswalk does not map to specific occupations.

#### Fan-Out: SOC Codes per CIP4 Prefix

| Metric | Value |
|--------|-------|
| Min | 1 |
| P25 | 3 |
| Median | 5 |
| P75 | 7 |
| Max | 180 (99.99 NO MATCH, excluded) |
| Max (real) | 43 (52.02 Business Admin) |
| Mean | 6.3 |

**Fan-out distribution:**

| SOC Count | CIP Codes |
|-----------|-----------|
| 1 | 26 |
| 2-5 | 224 |
| 6-10 | 120 |
| 11-20 | 39 |
| 21-50 | 6 |
| 51+ | 1 (99.99 NO MATCH, harmless) |

#### Dedup Impact

| Metric | Value |
|--------|-------|
| Raw INNER JOIN rows | 1,817,092 |
| Distinct (unitid, cipcode, soc_code) grains | 626,406 |
| Compression ratio | 2.90x |
| Grain combos with duplicates | 299,513 (47.8%) |
| Max duplicates per grain | 37 |

---

### SOC Code Overlap Analysis

| Source | Distinct SOCs |
|--------|--------------|
| occupation_profiles (BLS) | 832 |
| onet_work_profiles (O*NET) | 798 |
| In both BLS and O*NET | 773 |
| BLS only | 59 |
| O*NET only | 25 |

**Crosswalk SOC coverage:**

| Match | Count | Pct |
|-------|-------|-----|
| Crosswalk SOCs in BLS | 820 | 94.6% |
| Crosswalk SOCs in O*NET | 798 | 92.0% |
| Crosswalk SOCs in BOTH | 773 | 89.2% |
| Crosswalk SOCs in NEITHER | 22 | 2.5% |

---

### Full Join Chain Simulation (Table 1: program_career_paths)

#### Row Count and Match Quality

| match_quality | Rows | Pct |
|---------------|------|-----|
| full | 584,051 | 93.2% |
| partial_no_onet | 26,149 | 4.2% |
| partial_no_bls | 15,376 | 2.5% |
| scorecard_only | 830 | 0.1% |
| **Total** | **626,406** | **100%** |

#### Stat Availability

| Stat | Computable Rows | Pct | Bottleneck |
|------|----------------|-----|------------|
| stat_ern | 259,059 | 41.4% | cip_family_earnings_rank null 64.0% in Scorecard |
| stat_roi | 235,299 | 37.6% | debt_to_earnings_annual null 68.9% in Scorecard |
| stat_grw | 610,200 | 97.4% | BLS coverage |
| stat_hmn | 582,291 | 93.0% | O*NET coverage + 24 partial profiles |
| stat_res | 0 | 0.0% | Placeholder (always null) |

#### stats_available_count Distribution

| Count | Rows | Pct |
|-------|------|-----|
| 0 | 1,301 | 0.2% |
| 1 | 33,545 | 5.4% |
| 2 | 333,769 | 53.3% |
| 3 | 45,398 | 7.2% |
| 4 | 212,393 | 33.9% |

**Majority (53.3%) will have exactly 2 stats** (GRW + HMN only, missing ERN and ROI due to Scorecard suppressions). Only 33.9% will have all 4 non-placeholder stats.

#### Boss Availability

| Boss | Computable Rows | Pct |
|------|----------------|-----|
| boss_loans | 235,299 | 37.6% |
| boss_ceiling | 603,289 | 96.3% |
| boss_market | 610,200 | 97.4% |
| boss_burnout | 582,291 | 93.0% |
| boss_ai | 0 | 0.0% |

#### bosses_available_count Distribution

| Count | Rows | Pct |
|-------|------|-----|
| 0 | 1,301 | 0.2% |
| 1 | 11,298 | 1.8% |
| 2 | 34,033 | 5.4% |
| 3 | 367,381 | 58.7% |
| 4 | 212,393 | 33.9% |

#### Overall Confidence Distribution

| Tier | Rows | Pct |
|------|------|-----|
| high | 212,393 | 33.9% |
| medium | 16,197 | 2.6% |
| low | 397,816 | 63.5% |

---

### Simulated Stat Distributions

#### stat_ern (1-10, where computable)

| Score | Rows |
|-------|------|
| 1 | 115 |
| 2 | 2,175 |
| 3 | 9,341 |
| 4 | 30,175 |
| 5 | 50,234 |
| 6 | 48,653 |
| 7 | 45,327 |
| 8 | 40,898 |
| 9 | 27,541 |
| 10 | 4,600 |

Roughly normal distribution centered around 5-6. Full range 1-10 is used.

#### stat_roi (1-10, where computable, program-level pre-fanout)

| Score | Rows |
|-------|------|
| 1 | 2 |
| 2 | 1 |
| 3 | 5 |
| 4 | 46 |
| 5 | 278 |
| 6 | 807 |
| 7 | 2,711 |
| 8 | 6,737 |
| 9 | 7,966 |
| 10 | 3,210 |

**Heavily right-skewed** -- most programs have good ROI (score 8-10). Only 54 programs (0.25%) have ROI of 4 or below. This matches the career_outcomes EDA finding that 69.23% of debt-to-earnings ratios are in the "Low" tier (< 0.75). The piecewise breakpoints work well with this data.

#### grw_score_rounded (1-10, occupation-level)

Right-skewed toward 5-7. Peak at 6 (225 occupations). Only 3 occupations reach 10.

#### hmn_score_rounded (1-10, occupation-level)

Centered around 4-5. Peak at 5 (227 occupations). Only 1 occupation reaches 10, 2 at score 1.

#### boss_ceiling_score (1-10, occupation-level)

Uniform distribution (by design -- wage_percentile_education_tier is a percentile rank).

---

### Table 2: career_branches Simulation

| Metric | Value |
|--------|-------|
| Row count | 15,944 (1:1 with career_transitions) |
| Distinct source SOCs | 798 |
| Distinct related SOCs | 796 |
| Transitions per source | min=14, median=20, max=75 |
| branch_has_full_data (True) | 15,390 (96.5%) |

**SOC coverage for enrichment:**

| Source | Coverage |
|--------|----------|
| All SOCs in career_transitions found in BLS | 773 of 798 (96.9%) |
| All SOCs in career_transitions found in O*NET | 798 of 798 (100.0%) |
| Both BLS and O*NET | 773 of 798 (96.9%) |

**Relatedness tier distribution:**

| Tier | Rows | Primary |
|------|------|---------|
| Primary-Short | 4,134 | All |
| Primary-Long | 3,938 | All |
| Supplemental | 7,872 | None |

---

### Golden Dataset Trace: ISU Business Admin

**career_outcomes row:** unitid=151324, cipcode=52.02, credlev=3, earnings_1yr_median=$34,830, debt_median=$21,854, debt_to_earnings_annual=0.627, cip_family_earnings_rank=0.125

**Crosswalk prefix match:** 52.02 matches 91 crosswalk rows across 15 six-digit CIPs (52.0201 through 52.0216), producing 43 distinct SOC codes after dedup.

**Example trace to SOC 13-2051 (Financial and Investment Analysts):**
- BLS: GRW=7, median_wage=$101,350, wage_pct_overall=0.879, wage_pct_edu_tier=0.701, market=7
- O*NET: HMN=null, burnout=null (partial profile -- no activity/context data)
- Simulated stat_ern = ROUND(1 + 9 * (0.6 * 0.125 + 0.4 * 0.879)) = ROUND(1 + 9 * 0.427) = ROUND(4.84) = 5
- Simulated stat_roi: dte=0.627 is in 0.25-0.75 range, so ROI = ROUND(10.0 - 2.0 * (0.627-0.25)/0.5) = ROUND(10 - 1.508) = ROUND(8.49) = 8
- Simulated boss_loans = 11 - 8 = 3
- Simulated boss_ceiling = ROUND(10 - 9 * 0.701) = ROUND(3.69) = 4
- match_quality = partial_no_onet (BLS present, O*NET has null scores)
- stats_available = 3 (ERN, ROI, GRW -- no HMN due to O*NET partial)

**Note:** The golden dataset's example SOC (13-2051) is one of the 24 O*NET partial profiles. This is a realistic representation of the data quality challenges. A better golden dataset trace for full coverage might use a SOC like 11-1021 (General and Operations Managers).

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Row count exceeds spec estimate (626K vs 150K-500K) | 626,406 | -- | Widen DQ row count range to 580,000-700,000 |
| Grain tuples requiring dedup | 299,513 | 47.8% of grains | Verify dedup produces exactly 626,406 rows |
| stats_available_count = 2 (GRW+HMN only) | 333,769 | 53.3% | Majority will lack ERN/ROI. Set DQ threshold: expect >= 30% with count >= 3 |
| overall_confidence = "low" | 397,816 | 63.5% | Driven by Scorecard null rates, not join failures. Acceptable for hackathon |
| Scorecard programs with no crosswalk match | 2,008 rows (35 CIPs) | 2.9% | These get zero output rows (INNER JOIN). Document as expected |
| SOCs with no occupation title from either source | 22 | 2.5% of crosswalk SOCs | Handle null occupation_title or make field nullable |
| O*NET partial profiles (null HMN/burnout) | 24 | 3.0% of O*NET | Creates partial_no_onet-like behavior even when O*NET row exists |
| 99.9999 "NO MATCH" crosswalk rows | 180 | 3.0% of crosswalk | Harmless -- no Scorecard CIP 99.99 exists |
| boss_loans computable | 235,299 | 37.6% | Low coverage due to Scorecard debt suppression |
| stat_roi = 1 (worst) | 2 | <0.01% | Extremely rare at bottom end |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| Row count | Estimate mismatch | 1 | HIGH | 626,406 exceeds spec range of 150K-500K. DQ rule must be updated. |
| occupation_title | Null title risk | 22 SOCs | MEDIUM | 22 crosswalk SOC codes have no title from BLS or O*NET. Required field will be null. |
| hmn_score_rounded | Partial O*NET | 24 occupations | LOW | O*NET "partial" profiles have null HMN/burnout despite row existing. match_quality will show "full" but stats will still be null for these SOCs. |
| stats_available_count | Distribution skew | 333,769 rows | INFO | Majority have only 2/5 stats due to Scorecard suppressions. Product UX should handle sparse pentagons gracefully. |
| overall_confidence | Low majority | 397,816 rows | INFO | 63.5% low confidence despite 93.2% full match quality. Confidence is gated by stat availability, not join coverage. |
| match_quality vs actual nulls | Semantic gap | 24 SOCs | LOW | match_quality="full" indicates BLS+O*NET rows exist, but 24 O*NET rows have null scores. Consider differentiating "row exists" from "scores available." |

---

### Audit Trail

- **Dataset analyzed:** consumable.career_outcomes (69,947 rows), consumable.occupation_profiles (832 rows), consumable.onet_work_profiles (798 rows), consumable.career_transitions (15,944 rows), base.cip_soc_crosswalk (5,903 rows)
- **Analysis purpose:** Gold zone pre-build EDA for gold-futureproof-engine spec. Validate CIP prefix join chain, estimate row counts, profile stat input distributions, simulate match quality and stat availability.
- **Key findings:** Row count 626,406 exceeds spec range (needs DQ rule update). CIP prefix match coverage confirmed at 91.0%/97.1%. Match quality 93.2% "full." Stat availability limited by Scorecard null rates (64% earnings suppressed). 24 O*NET partial profiles create null HMN/burnout despite "full" match quality.
- **Threshold recommendations:** Row count 580K-700K, stats_available >= 2 for 95%+ rows, match_quality "full" >= 90%, overall_confidence "high" >= 30%.
- **Timestamp:** 2026-04-09
- **Spec reference:** docs/specs/gold-futureproof-engine.md
