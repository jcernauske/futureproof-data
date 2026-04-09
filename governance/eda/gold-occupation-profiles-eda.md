## EDA Report: Gold Pre-Implementation Profiling of `consumable.occupation_profiles`
**Source:** Silver table `base.bls_ooh` (832 rows, 25 fields)
**Date:** 2026-04-07
**Agent:** @data-analyst
**Record Count:** 832
**Field Count:** 25 Silver source fields; 28 Gold output fields (after drops + derivations)
**Zone:** Gold (profiling Silver input data to validate Gold derivation design)
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Builds on:** `governance/eda/silver-bls-ooh-eda.md` (Silver EDA)

---

### Key Findings

- **GRW score distribution validates the design.** Mean = 5.321, median = 5.562. The spec target of 5.5-6.5 for the mean is slightly missed (5.321 is 0.18 below the low end), but the median at 5.562 is solidly within range. This places the national average growth (~4%) at approximately 6.0 on the scale, which is the intended design -- "average" slightly above midpoint. All 10 integer buckets (1-10) are populated. StdDev = 1.691, providing good spread for the pentagon stat.

- **Market score distribution is healthy.** Mean = 5.380, StdDev = 1.607 (well above the 1.0 minimum). The blended 0.6*grw + 0.4*openings formula produces a more centered distribution than GRW alone. Only 9 integer buckets represented (1-9); no occupation reaches bucket 10. This is structurally expected -- achieving market_score = 10.0 requires both top growth AND top openings volume simultaneously, which is a rare combination.

- **SPEC ERROR: Golden dataset #3 is wrong.** The spec claims Family Medicine Physicians (29-1215) has null wage fields and confidence_tier = "low". In the actual data, 29-1215 has median_annual_wage = $238,380 and wage_available = True, which gives confidence_tier = "high". The spec should use a confirmed null-wage occupation such as Anesthesiologists (29-1211) instead.

- **CRITICAL IMPLEMENTATION NOTE: Wage percentile null handling.** If null wages participate in the PERCENT_RANK window function, DuckDB orders them above some real wages (at ~percentile 0.185), corrupting all percentile positions. The implementation MUST filter nulls out before computing PERCENT_RANK, then LEFT JOIN back to assign null percentiles. This changes the wage_tier distribution significantly (81 vs 61 in very_high tier).

- **3 null-wage occupations are also catchall.** 27-2099, 29-1229, and 29-1249 have both wage_available=False AND catchall_flag=True. Per the spec's confidence tier logic, wage_available=False takes priority, so all 3 go to "low" (not "medium"). This means medium tier has 74 occupations (7 broad + 67 catchall-with-wage), not 77.

- **DuckDB ROUND is standard (round half up), not banker's rounding.** ROUND(2.5)=3, ROUND(4.5)=5, ROUND(6.5)=7, ROUND(7.5)=8. This is consistent across all integer boundaries. 15 occupations sit exactly at GRW .5 boundaries (pct = -10.0, 0.0, 5.0, 10.0).

- **Data completeness has only 2 distinct values: {0.75, 1.0}.** The spec lists {0.0, 0.25, 0.5, 0.75, 1.0} as possible values, but since the only nullable core field in this data is median_annual_wage (23 nulls), and employment_current, employment_change_pct, and openings_annual_avg are all 100% non-null, only 0.75 (23 rows) and 1.0 (809 rows) appear. The spec is correct that 0.0 never appears.

- **61 tied wages** exist (same dollar amount for 2-3 occupations). PERCENT_RANK assigns the same percentile to ties, which is correct behavior but means wage_percentile_overall has 748 distinct values, not 809.

---

### 1. GRW Score Distribution Preview

Piecewise linear function applied to employment_change_pct per spec breakpoints:

| Statistic | Value |
|-----------|-------|
| N | 832 (0 null -- employment_change_pct has no nulls) |
| Min | 1.000 |
| P05 | 2.225 |
| P10 | 3.068 |
| P25 | 3.983 |
| Median | 5.562 |
| Mean | 5.321 |
| P75 | 6.500 |
| P90 | 7.218 |
| P95 | 7.815 |
| Max | 9.997 |
| StdDev | 1.691 |

#### GRW Score Rounded Distribution (ROUND to integer)

| Bucket | Count | Pct | Histogram |
|--------|-------|-----|-----------|
| 1 | 19 | 2.3% | ### |
| 2 | 35 | 4.2% | ####### |
| 3 | 79 | 9.5% | ############### |
| 4 | 111 | 13.3% | ###################### |
| 5 | 153 | 18.4% | ############################## |
| 6 | 225 | 27.0% | ############################################# |
| 7 | 148 | 17.8% | ############################# |
| 8 | 41 | 4.9% | ######## |
| 9 | 18 | 2.2% | ### |
| 10 | 3 | 0.4% | # |

**Assessment:** All 10 buckets are populated (spec requires at least 8). Distribution is right-skewed with the mode at 6, which correctly reflects BLS's overall employment growth of ~4%. The design goal -- "average is slightly above midpoint" -- is achieved. Buckets 1-2 (declining fast) and 9-10 (booming) are appropriately sparse.

**Threshold recommendation for @dq-rule-writer:** grw_score mean should be 4.5-6.0 (actual 5.321). The spec's target range of 5.5-6.5 is too tight; recommend widening to 4.5-6.5 to account for the left-skew from declining occupations pulling the mean below median.

---

### 2. Market Score Distribution Preview

Formula: `market_score = 0.6 * grw_score + 0.4 * openings_score`
Where: `openings_score = 1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg)`

| Statistic | Value |
|-----------|-------|
| N | 832 (0 null -- both components are fully populated) |
| Min | 1.017 |
| P05 | 2.720 |
| P10 | 3.169 |
| P25 | 4.264 |
| Median | 5.421 |
| Mean | 5.380 |
| P75 | 6.544 |
| P90 | 7.455 |
| P95 | 7.832 |
| Max | 9.239 |
| StdDev | 1.607 |

#### Market Score Rounded Distribution

| Bucket | Count | Pct | Histogram |
|--------|-------|-----|-----------|
| 1 | 10 | 1.2% | ## |
| 2 | 21 | 2.5% | #### |
| 3 | 73 | 8.8% | ############## |
| 4 | 153 | 18.4% | ############################## |
| 5 | 180 | 21.6% | #################################### |
| 6 | 178 | 21.4% | ################################### |
| 7 | 137 | 16.5% | ########################### |
| 8 | 64 | 7.7% | ############ |
| 9 | 16 | 1.9% | ### |
| 10 | 0 | 0.0% | |

**Assessment:** StdDev = 1.607 (well above the 1.0 minimum). No excessive clustering. The blending of grw_score (growth direction) with openings_score (volume) produces a smoother, more centered distribution than GRW alone.

**Missing bucket 10:** No occupation achieves market_score_rounded = 10. The maximum is 9.239 (Nurse Practitioners: grw=9.67, openings=8.59). To reach 10.0, an occupation would need both top growth percentage AND top openings volume simultaneously. The highest-growth occupations (e.g., Wind turbine technicians at 49.9%) tend to be small (few openings), while the highest-openings occupations (e.g., Fast food workers at 904,300) have moderate growth. This is a real property of the labor market, not a scoring defect.

**Correlation:** Pearson correlation between grw_score and openings_score is 0.209 (weak positive). The two components provide substantially independent signals, confirming the 60/40 blend adds information beyond GRW alone.

**Top 5 market scores:**
| SOC | Title | Market | GRW | Openings | Pct | Annual Openings |
|-----|-------|--------|-----|----------|-----|----------------|
| 29-1171 | Nurse practitioners | 9.24 | 9.67 | 8.59 | 40.1% | 29,500 |
| 11-9111 | Medical/health services mgrs | 9.17 | 9.11 | 9.25 | 23.2% | 62,100 |
| 31-1120 | Home health/personal care aides | 9.13 | 8.55 | 9.99 | 17.0% | 765,800 |
| 15-2051 | Data scientists | 9.02 | 9.45 | 8.38 | 33.5% | 23,400 |
| 35-2014 | Cooks, restaurant | 8.89 | 8.23 | 9.88 | 14.9% | 250,700 |

**Bottom 5 market scores:**
| SOC | Title | Market | GRW | Openings | Pct | Annual Openings |
|-----|-------|--------|-----|----------|-----|----------------|
| 47-5043 | Roof bolters, mining | 1.02 | 1.00 | 1.04 | -34.2% | 100 |
| 51-4062 | Patternmakers, metal/plastic | 1.02 | 1.00 | 1.04 | -24.4% | 100 |
| 43-2021 | Telephone operators | 1.12 | 1.00 | 1.30 | -27.5% | 300 |
| 51-2061 | Timing device assemblers | 1.23 | 1.38 | 1.00 | -17.5% | 0 |
| 51-4032 | Drilling/boring machine setters | 1.24 | 1.06 | 1.51 | -19.6% | 400 |

**Threshold recommendation for @dq-rule-writer:** market_score_rounded should have representation in at least 8 of 10 buckets (actual: 9 of 10). Do NOT require bucket 10 -- it is structurally absent in this data.

---

### 3. Wage Percentile Analysis

#### Overall Percentile (809 non-null occupations)

| Statistic | Value |
|-----------|-------|
| N | 809 |
| Null count | 23 (confirmed exactly 23) |
| Min percentile | 0.0000 |
| Max percentile | 1.0000 |
| Distinct percentile values | 748 (61 tied-wage pairs reduce distinct count) |

#### Wage Tier Distribution (Approach A: filter nulls before ranking)

| Tier | Count | Min Wage | Max Wage | Avg Wage | Percentile Range |
|------|-------|----------|----------|----------|------------------|
| low | 202 | $30,160 | $45,920 | $38,943 | 0.0000 - 0.2488 |
| below_average | 202 | $45,980 | $59,190 | $51,164 | 0.2500 - 0.4988 |
| above_average | 202 | $59,280 | $78,420 | $67,314 | 0.5000 - 0.7488 |
| high | 122 | $78,490 | $104,240 | $91,349 | 0.7500 - 0.8998 |
| very_high | 81 | $104,620 | $238,380 | $136,560 | 0.9010 - 1.0000 |
| NULL | 23 | -- | -- | -- | -- |

Quartile breakpoints are very clean: low/below_average/above_average each have exactly 202 occupations. The "high" (75th-90th) has 122, and "very_high" (90th+) has 81.

#### Wage Percentile Within Education Tier

| Code | Education Level | N | Min Wage | Max Wage | Notes |
|------|----------------|---|----------|----------|-------|
| 1 | Doctoral/professional | 56 | $60,400 | $238,380 | 17 null-wage MDs excluded from ranking |
| 2 | Master's | 40 | $46,110 | $223,210 | Includes nurse anesthetists ($223K) |
| 3 | Bachelor's | 178 | $38,470 | $226,600 | Includes airline pilots ($227K) |
| 4 | Associate's | 48 | $37,040 | $144,580 | |
| 5 | Postsecondary nondegree | 51 | $34,660 | $122,670 | |
| 6 | Some college | 6 | $35,240 | $60,340 | Very small group; percentiles less meaningful |
| 7 | High school | 325 | $30,460 | $122,610 | Largest group; 1 null wage |
| 8 | No formal credential | 105 | $30,160 | $89,990 | 4 null wages (performers, fishing) |

**Note on education_code = 6:** Only 6 occupations. PERCENT_RANK within this tier will have only 5 distinct values (0.0, 0.2, 0.4, 0.6, 0.8, 1.0). This is technically correct but may be misleading for users. Consider flagging small-tier percentiles in the data contract.

#### Critical Implementation Warning

The spec defines `wage_percentile_overall` as `PERCENT_RANK() OVER (ORDER BY median_annual_wage)`. If null wages are included in the window partition:

- DuckDB orders NULL wages above some real wages (~percentile 0.185)
- All percentile positions shift
- very_high tier gets 61 occupations instead of 81
- Wage tier boundaries no longer align with true quartiles

**Correct implementation:** Filter to `WHERE median_annual_wage IS NOT NULL` before computing PERCENT_RANK, then LEFT JOIN results back to assign NULL percentiles to the 23 null-wage rows. Same approach for `wage_percentile_education_tier`.

---

### 4. Confidence Tier Distribution

| Tier | Count | Pct | Composition |
|------|-------|-----|-------------|
| high | 735 | 88.3% | Not broad, not catchall, has wage |
| medium | 74 | 8.9% | 7 broad-only + 67 catchall-with-wage |
| low | 23 | 2.8% | All null-wage (20 non-catchall + 3 catchall) |

**Note:** 3 occupations (27-2099, 29-1229, 29-1249) are both null-wage AND catchall. Per the spec's tiering logic, `wage_available = False` takes priority, placing them in "low" regardless of catchall status. This means medium tier contains only 67 catchall occupations (not all 70).

Medium tier breakdown:
- broad_only: 7 occupations (all 7 broad codes have wages)
- catchall_only: 67 occupations (70 catchall minus 3 that are null-wage)
- both broad AND catchall: 0 (no overlap between broad codes and catchall titles)

**Threshold recommendation for @dq-rule-writer:**
- high: 735 (exact match)
- medium: 74 (exact match; 7 broad + 67 catchall-with-wage)
- low: 23 (exact match; equals null-wage count)
- Total: 832 (every row gets a tier)

---

### 5. Data Completeness Distribution

Core fields: median_annual_wage, employment_current, employment_change_pct, openings_annual_avg

| Non-null Fields | Completeness | Count | Missing Field |
|-----------------|-------------|-------|---------------|
| 3 | 0.75 | 23 | median_annual_wage only |
| 4 | 1.00 | 809 | none |

**Assessment:** Only 2 distinct completeness values appear: {0.75, 1.0}. The spec lists {0.0, 0.25, 0.5, 0.75, 1.0} as the value set, which is the theoretical range. In practice, since employment_current, employment_change_pct, and openings_annual_avg are all 100% non-null, the only variation comes from median_annual_wage. No rows have completeness = 0.0 (confirmed: 0 rows with all 4 core fields null).

**The 0.75 completeness rows exactly equal the 23 null-wage occupations.** This is a tautological relationship: the only path to completeness < 1.0 is a null wage.

**Threshold recommendation for @dq-rule-writer:**
- data_completeness valid values: {0.75, 1.0} (not the full theoretical set)
- No 0.0 rows: confirmed
- 0.75 count: exactly 23
- 1.0 count: exactly 809

---

### 6. Golden Dataset Verification

#### Software Developers (15-1252) -- VERIFIED

| Field | Silver Value | Gold Derivation | Gold Value |
|-------|-------------|-----------------|------------|
| soc_code | 15-1252 | carried | 15-1252 |
| employment_change_pct | 15.8 | carried | 15.8 |
| grw_score | -- | Band 10.0-20.0: 7.5 + (15.8-10.0)/10.0 * 1.5 | **8.3700** |
| grw_score_rounded | -- | ROUND(8.37) | **8** |
| median_annual_wage | $133,080 | carried | $133,080 |
| wage_percentile_overall | -- | PERCENT_RANK (809 non-null) | **0.9579** |
| wage_tier | -- | pctile >= 0.90 | **very_high** |
| confidence_tier | -- | not broad, not catchall, has wage | **high** |
| openings_annual_avg | 115,200 | carried | 115,200 |
| market_score | -- | see below | computed |

Spec expected grw_score ~8.37. Actual: 8.3700. **Match confirmed.**

#### Registered Nurses (29-1141) -- VERIFIED

| Field | Silver Value | Gold Derivation | Gold Value |
|-------|-------------|-----------------|------------|
| soc_code | 29-1141 | carried | 29-1141 |
| employment_change_pct | 4.9 | carried | 4.9 |
| grw_score | -- | Band 1.0-5.0: 5.0 + (4.9-1.0)/4.0 * 1.5 | **6.4625** |
| grw_score_rounded | -- | ROUND(6.4625) | **6** |
| median_annual_wage | $93,600 | carried | $93,600 |
| wage_percentile_overall | -- | PERCENT_RANK (809 non-null) | **0.8354** |
| wage_tier | -- | 0.75 <= 0.8354 < 0.90 | **high** |
| openings_pctile | -- | PERCENT_RANK(openings) | 0.9807 |
| openings_score | -- | 1.0 + 9.0 * 0.9807 | **9.8267** |
| market_score | -- | 0.6 * 6.4625 + 0.4 * 9.8267 | **7.8082** |
| market_score_rounded | -- | ROUND(7.8082) | **8** |
| confidence_tier | -- | not broad, not catchall, has wage | **high** |

Spec expected grw_score ~6.46. Actual: 6.4625. **Match confirmed.**
RN has 3rd largest employment (3.39M) and 189,100 annual openings, producing a very high openings_score (9.83) and strong market_score (7.81).

#### Family Medicine Physicians (29-1215) -- SPEC ERROR

| Field | Spec Expectation | Actual Silver Value |
|-------|-----------------|---------------------|
| median_annual_wage | NULL | **$238,380** |
| wage_available | False | **True** |
| confidence_tier | low | **high** |

**The spec's golden dataset #3 is incorrect.** 29-1215 Family Medicine Physicians has a real wage in the current BLS data ($238,380, the highest reported wage in the dataset). This SOC code should NOT be used as a null-wage example.

**Recommended replacement:** Use **Anesthesiologists (29-1211)** instead:
- median_annual_wage: NULL
- wage_available: False
- wage_tier: NULL
- wage_percentile_overall: NULL
- wage_percentile_education_tier: NULL
- confidence_tier: **low**
- employment_change_pct: 3.2 -> grw_score = 5.0 + (3.2-1.0)/4.0 * 1.5 = **5.825**
- grw_score_rounded: **6**
- openings_annual_avg: 1,300 -> market_score still computes
- broad_occupation_flag: False, catchall_flag: False
- This is the cleanest null-wage golden dataset candidate: no catchall overlap, has employment data

---

### 7. Edge Cases for DQ Thresholds

#### Extreme employment_change_pct Values (beyond +/- 20%)

21 occupations have employment_change_pct beyond the +/-20% range where the GRW piecewise function uses less granular scaling:

| Direction | Count | Range | Notable Examples |
|-----------|-------|-------|------------------|
| Below -20% | 11 | -36.1 to -21.1 | Word processors (-36.1%), Roof bolters (-34.2%) |
| Above +20% | 10 | 20.4 to 49.9 | Wind turbine techs (49.9%), Solar installers (42.1%), Nurse practitioners (40.1%) |

The GRW score for extreme values:
- pct = -36.1: grw = 1.0 (capped at floor)
- pct = 49.9: grw = 9.0 + (49.9-20.0)/30.0 * 1.0 = 9.997 (just under cap)

No occupation exceeds 50.0%, so the cap at 10.0 is never hit but is barely missed (49.9% -> 9.997).

#### GRW Piecewise Function Boundary Occupations

| Boundary Pct | GRW Score | Count | SOC Examples |
|-------------|-----------|-------|--------------|
| -10.0 | 2.500 | 1 | 41-9091 Door-to-door sales workers |
| -1.0 | 4.000 | 1 | 53-6031 Automotive service attendants |
| 0.0 | 4.500 | 7 | Multiple (budget analysts, clergy, etc.) |
| 1.0 | 5.000 | 7 | Multiple (adhesive bonding, butchers, etc.) |
| 5.0 | 6.500 | 5 | Civil engineers, HR managers, paramedics |
| 10.0 | 7.500 | 2 | Medical equipment preparers, SQA testers |
| 20.0 | 9.000 | 1 | Psychiatric technicians |

These 24 occupations sit exactly at piecewise breakpoints. The ROUND behavior at .5 boundaries determines their integer bucket assignment.

#### ROUND(.5) Behavior

DuckDB ROUND is standard (round half up, not banker's rounding):

| GRW Score | ROUND Result | Count | Boundary Pct |
|-----------|-------------|-------|--------------|
| 2.500 | 3 | 1 | pct = -10.0 |
| 4.500 | 5 | 7 | pct = 0.0 |
| 6.500 | 7 | 5 | pct = 5.0 |
| 7.500 | 8 | 2 | pct = 10.0 |

All .5 values round up consistently. This is deterministic and correct. If the implementation uses Python's `round()` instead of DuckDB's `ROUND()`, results will differ (Python uses banker's rounding). **The implementation should use DuckDB ROUND for consistency.**

#### Zero Openings Occupations

4 occupations have openings_annual_avg = 0 (BLS rounding from thousands):

| SOC | Title | Pct | Employment |
|-----|-------|-----|------------|
| 29-1024 | Prosthodontists | 4.5% | 900 |
| 29-1243 | Pediatric surgeons | 1.5% | 1,100 |
| 51-2061 | Timing device assemblers | -17.5% | 200 |
| 51-7032 | Patternmakers, wood | -5.0% | 500 |

These receive openings_score = 1.0 (minimum). All 4 are tied for the lowest PERCENT_RANK = 0.0. This is correct behavior -- zero openings means minimum market opportunity score regardless of growth rate.

#### Very Small Occupations (employment_current <= 500)

| SOC | Title | Employment | Pct | Openings |
|-----|-------|-----------|-----|----------|
| 51-2061 | Timing device assemblers | 200 | -17.5% | 0 |
| 51-7032 | Patternmakers, wood | 500 | -5.0% | 0 |

Both are tiny, declining, with zero openings. Their scores are valid but represent occupations that are effectively vanishing. No special handling needed.

#### Null-Wage + Catchall Overlap (Confidence Tier Edge Case)

3 occupations trigger both null-wage (-> low) and catchall (-> medium) criteria:
- 27-2099 Entertainers and performers, all other
- 29-1229 Physicians, all other
- 29-1249 Surgeons, all other

Per spec: `wage_available = False` takes priority. All 3 go to **low**. The @primary-agent must implement the CASE logic with wage_available checked first.

---

### Cross-Field Analysis

#### GRW Score vs Growth Category Alignment

| Growth Category | Count | GRW Range | GRW Rounded Range |
|----------------|-------|-----------|-------------------|
| declining_fast (< -10.0) | 54 | 1.000 - 2.350 | 1 - 2 |
| declining (-10.0 to -1.0) | 155 | 2.500 - 3.833 | 3 - 4 |
| stable (-1.0 to 1.0) | 80 | 4.000 - 5.000 | 4 - 5 |
| growing (1.0 to 10.0) | 481 | 5.000 - 7.500 | 5 - 8 |
| growing_fast (10.0 to 20.0) | 51 | 7.500 - 9.000 | 8 - 9 |
| booming (>= 20.0) | 11 | 9.000 - 9.997 | 9 - 10 |

GRW score monotonically aligns with growth category. No cross-category inversion is possible given the piecewise linear design.

#### Wage Tier vs Confidence Tier

All 23 "low" confidence occupations have null wage_tier. All 735 "high" and 74 "medium" confidence occupations have a non-null wage_tier. The correspondence is exact: `confidence_tier = 'low'` if and only if `wage_tier IS NULL`.

#### Market Score Components

Market score (0.6*grw + 0.4*openings) has:
- GRW component range: 0.6 * [1.0, 10.0] = [0.6, 6.0]
- Openings component range: 0.4 * [1.0, 10.0] = [0.4, 4.0]
- Theoretical range: [1.0, 10.0]
- Actual range: [1.017, 9.239]

The GRW component contributes 60% of variance. This means high-growth occupations can score well even with low openings (max GRW contribution = 6.0 is achievable alone for a score of 6.4 if openings = 1.0).

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| Golden dataset #3 | Spec error | 1 | HIGH | Spec claims 29-1215 has null wages; actual wage = $238,380. Must correct to use a confirmed null-wage SOC (e.g., 29-1211). |
| Market score bucket 10 | Design gap | 0 rows in bucket 10 | LOW | Structurally expected. No occupation has both top growth AND top openings. Not a defect. |
| GRW mean vs spec target | Threshold mismatch | -- | LOW | Spec targets mean 5.5-6.5; actual is 5.321. Recommend widening target to 4.5-6.5. |
| data_completeness values | Spec over-specification | 2 values, not 5 | LOW | Spec lists {0.0, 0.25, 0.5, 0.75, 1.0}; only {0.75, 1.0} appear since only wage is nullable among core fields. |
| Wage PERCENT_RANK null handling | Implementation risk | 23 rows affected | HIGH | Nulls in PERCENT_RANK window corrupt all percentile positions. Must filter before ranking. |
| ROUND(.5) inconsistency risk | Implementation risk | 15 boundary rows | MEDIUM | Python round() uses banker's rounding; DuckDB ROUND uses standard rounding. Implementation must use DuckDB consistently. |
| Null-wage + catchall overlap | Logic edge case | 3 rows | MEDIUM | 3 occupations qualify for both "low" and "medium" tiers. Wage check must take priority per spec. |

---

### DQ Threshold Recommendations for @dq-rule-writer

#### Score Ranges
| Rule | Threshold | Evidence |
|------|-----------|----------|
| grw_score range | 1.0 <= grw_score <= 10.0 for all non-null | Actual: 1.000 - 9.997 |
| grw_score null count | 0 | employment_change_pct is 0% null |
| grw_score_rounded range | 1 - 10 integer | All 10 buckets populated |
| grw_score_rounded = ROUND(grw_score) | Exact match all rows | Deterministic derivation |
| grw_score mean | 4.5 - 6.5 | Actual: 5.321 |
| grw_score bucket coverage | >= 8 of 10 buckets | Actual: 10 of 10 |
| market_score range | 1.0 <= market_score <= 10.0 for all non-null | Actual: 1.017 - 9.239 |
| market_score null count | 0 | Both components 0% null |
| market_score_rounded range | 1 - 10 integer | Actual: 1-9 (bucket 10 absent) |
| market_score_rounded = ROUND(market_score) | Exact match all rows | Deterministic derivation |
| market_score stddev | > 1.0 | Actual: 1.607 |
| market_score bucket coverage | >= 7 of 10 buckets | Actual: 9 of 10 |

#### Percentile Ranks
| Rule | Threshold | Evidence |
|------|-----------|----------|
| wage_percentile_overall range | 0.0 - 1.0 when non-null | Actual: 0.0000 - 1.0000 |
| wage_percentile_overall null count | 23 | Equals null-wage count |
| wage_percentile_education_tier range | 0.0 - 1.0 when non-null | Confirmed across all 8 tiers |
| wage_percentile_education_tier null count | 23 | Equals null-wage count |
| wage_tier valid values | {low, below_average, above_average, high, very_high} | 5 values confirmed |
| wage_tier null count | 23 | Equals null-wage count |
| wage_tier = NULL iff wage_available = False | Exact correspondence | 23 rows both ways |

#### Confidence Tier
| Rule | Threshold | Evidence |
|------|-----------|----------|
| confidence_tier not null | 0 nulls | Every row assigned |
| confidence_tier valid values | {high, medium, low} | 3 values only |
| high count | 735 | 832 - 74 medium - 23 low |
| medium count | 74 | 7 broad + 67 catchall-with-wage |
| low count | 23 | Equals null-wage count |

#### Data Completeness
| Rule | Threshold | Evidence |
|------|-----------|----------|
| data_completeness not null | 0 nulls | Always computable |
| data_completeness valid values | {0.75, 1.0} | Only 2 values in current data |
| data_completeness = 0.0 count | 0 | All rows have at least 3 non-null core fields |
| data_completeness = 0.75 count | 23 | Exactly the null-wage rows |
| data_completeness = 1.0 count | 809 | All rows with wage data |

#### Row Count and Grain
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Total rows | 832 | Silver to Gold: no rows added or dropped |
| soc_code uniqueness | 0 duplicates | Grain holds |
| backs_stats | "ERN,GRW" all 832 rows | Static value |
| backs_bosses | "Market,Ceiling" all 832 rows | Static value |

---

### Recommendations for Downstream Agents

**For @dq-rule-writer:**
- Correct spec error: golden dataset #3 should not use 29-1215 (it has wage data). Use 29-1211 Anesthesiologists.
- market_score_rounded will NOT have bucket 10. Do not require it.
- grw_score mean target should be 4.5-6.5 (wider than spec's 5.5-6.5).
- data_completeness actual value set is {0.75, 1.0}, not the full theoretical {0.0-1.0}.
- 15 occupations sit at exact GRW piecewise breakpoints. Test these boundary values in golden dataset.

**For @primary-agent:**
- CRITICAL: Filter null wages out of PERCENT_RANK window before computing. Do not include nulls.
- Use DuckDB ROUND, not Python round(), for grw_score_rounded and market_score_rounded.
- Implement confidence_tier CASE logic with wage_available check FIRST (before broad/catchall).
- openings_score PERCENT_RANK denominator is 831 (832 - 1), since openings has no nulls.

**For @semantic-modeler:**
- education_code = 6 (Some college) has only 6 occupations. wage_percentile_education_tier for this group has very coarse resolution (only 6 distinct values). Consider documenting this limitation in the data contract.

**For spec owner:**
- Fix golden dataset #3: 29-1215 has wage data ($238,380), use 29-1211 instead.
- Widen grw_score mean target from 5.5-6.5 to 4.5-6.5.
- Note that market_score_rounded bucket 10 will be empty.
- Note that data_completeness only produces {0.75, 1.0} in current data.
