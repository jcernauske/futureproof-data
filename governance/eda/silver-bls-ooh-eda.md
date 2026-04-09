## EDA Report: Silver Profiling of raw.bls_ooh (for base.bls_ooh)
**Source:** Bronze table `raw.bls_ooh` (parsed from BLS Employment Projections interactive export)
**Date:** 2026-04-07
**Agent:** @data-analyst
**Record Count:** 832
**Field Count:** 15 source fields + 9 derived Silver fields
**Zone:** Silver (profiling Bronze data to establish DQ thresholds for `base.bls_ooh`)
**Builds on:** `governance/eda/raw-bls-ooh-eda.md` (Bronze EDA)

---

### Key Findings

- **CRITICAL: Catchall count is 70, not 46.** The spec states "46 true 'all other' catch-all categories" but case-insensitive matching of "all other" in `occupation_title` yields 70 rows. All 70 contain the substring ", all other" in lowercase. One row (29-1029 "Dentists, all other specialists") contains "all other" but does not end with it. The spec's number of 46 must be corrected to 70, or the matching logic must be narrowed. **Recommendation for @dq-rule-writer:** Set catchall_flag count threshold to 70, not 46.

- **Employment change sign discrepancy with pct.** 12 rows have `employment_change = 0` (integer, rounded from thousands) but `employment_change_pct < 0`. This is a BLS rounding artifact: very small occupations where the absolute change rounds to 0 at the thousands scale but the percentage is computed from unrounded source data. Example: 51-2061 "Timing device assemblers" has change=0 but pct=-17.5% (only 200 workers). Additionally, 2 rows have nonzero change but pct=0.0. **This is not a data quality issue** -- it is inherent to BLS rounding methodology. DQ rules must NOT enforce sign consistency between employment_change and employment_change_pct.

- **No overlap between broad occupation codes and catchall categories.** None of the 7 known broad codes (13-1020, 13-2020, 29-2010, 31-1120, 39-7010, 47-4090, 51-2090) contain "all other" in their titles. The flags are independent.

- **Null-wage occupations confirmed at exactly 23.** Breakdown: 14 physicians/surgeons, 5 performers, 3 other (including 29-1022 oral surgeons, 29-1023 orthodontists, 29-1024 prosthodontists), 1 fishing/hunting worker.

- **Growth category distribution is heavily skewed toward "growing".** 57.8% of occupations fall in the "growing" bucket (1.0 to 9.7%). This is expected given BLS projects overall employment growth of ~4% for 2024-2034.

- **Boundary values exist at every growth category threshold.** Exactly 1 row at -10.0 (goes to "declining"), 1 at -1.0 (goes to "stable"), 7 at 0.0, 7 at 1.0, 2 at 10.0, 1 at 20.0. The half-open interval logic [-10.0, -1.0) must be implemented precisely.

- **All 22 SOC major groups are populated.** Group 51 (Production) is largest with 105 occupations. Group 23 (Legal) is smallest with 8. Group 25 (Educational Instruction and Library) has 64, which is notably high because it includes all postsecondary teacher specialties.

---

### Field Profiles (Silver-Relevant)

#### soc_code (grain field)
- **Null Rate:** 0.0% (0 of 832)
- **Cardinality:** 832 distinct values (100% unique -- grain holds)
- **Format:** All 832 match `^\d{2}-\d{4}$` (XX-XXXX). Zero violations.
- **Silver derivation:** `soc_major_group` = first 2 characters. All 22 valid major group codes present.

#### occupation_title
- **Null Rate:** 0.0% (0 of 832)
- **Cardinality:** 832 distinct (1:1 with soc_code)
- **Catchall detection:** 70 titles contain ", all other" (case-insensitive). 69 end with ", all other"; 1 is "Dentists, all other specialists" (29-1029).
- **Silver implication:** catchall_flag derivation must use case-insensitive substring match, not exact suffix. The spec's LIKE '%all other%' approach is correct.

#### employment_current
- **Null Rate:** 0.0%
- **Min:** 200 | **P25:** 17,100 | **Median:** 50,200 | **P75:** 161,500 | **Max:** 4,347,700
- **Mean:** 204,275 | **StdDev:** 468,457
- **All values positive.** Highly right-skewed (a few very large occupations dominate).

#### employment_projected
- **Null Rate:** 0.0%
- **Min:** 200 | **P25:** 17,275 | **Median:** 50,250 | **P75:** 162,400 | **Max:** 5,087,500
- **Mean:** 210,541 | **StdDev:** 485,091

#### employment_change
- **Null Rate:** 0.0%
- **Min:** -313,600 | **P25:** -200 | **Median:** 700 | **P75:** 4,800 | **Max:** 739,800
- **Negative values:** 232 of 832 (27.9%) -- valid for declining occupations
- **Zero values:** Multiple rows show 0 due to BLS rounding (see sign discrepancy finding above)
- **Consistency:** `employment_projected - employment_current = employment_change` holds within +/- 1,000 rounding tolerance for all 832 rows.

#### employment_change_pct
- **Null Rate:** 0.0%
- **Min:** -36.1 | **P10:** -6.6 | **P25:** -1.1 | **Median:** 2.5 | **P75:** 5.0 | **P90:** 8.6 | **P95:** 12.1 | **P99:** 21.2 | **Max:** 49.9
- **Mean:** 1.74 | **StdDev:** 7.63
- **Negative values:** 244 of 832 (29.3%) -- note this is 12 more than `employment_change` negatives due to the rounding discrepancy described above.
- **Range:** -36.1 to 49.9, well within the spec's -100.0 to +200.0 sanity bounds.

#### openings_annual_avg
- **Null Rate:** 0.0%
- **Min:** 0 | **P25:** 1,500 | **Median:** 4,500 | **P75:** 14,825 | **Max:** 904,300
- **Zero values:** 4 occupations (Patternmakers wood, Pediatric surgeons, Prosthodontists, Timing device assemblers) -- BLS rounding artifact from thousands.

#### median_annual_wage
- **Null Rate:** 2.8% (23 of 832)
- **Non-null count:** 809
- **Min:** $30,160 | **P5:** $35,258 | **P10:** $37,700 | **P25:** $45,980
- **Median:** $59,280 | **P75:** $78,490 | **P90:** $104,316 | **P95:** $127,348
- **P99:** $170,923 | **Max:** $238,380
- **Mean:** $66,755
- **Capped wages:** 0 of 809. No wages equal the BLS cap of $239,200. Max observed is $238,380.
- **Wages >= $200,000:** 7 occupations (Family medicine physicians $238,380, General internal medicine physicians $236,350, Airline pilots $226,600, Dentists all other specialists $225,770, Nurse anesthetists $223,210, Pediatricians $210,130, Chief executives $206,420).

#### median_wage_capped
- **All False** (832 of 832). Interactive export uses actual numeric wages, no top-coding.

#### education_code
- **Null Rate:** 0.0%
- **Range:** 1 to 8 (all 8 values present)
- **Distribution:** 7 (High school) = 326 (39.2%), 3 (Bachelor's) = 178 (21.4%), 8 (No formal) = 109 (13.1%), 1 (Doctoral) = 73 (8.8%), 5 (Postsecondary nondegree) = 51 (6.1%), 4 (Associate's) = 48 (5.8%), 2 (Master's) = 40 (4.8%), 6 (Some college) = 7 (0.8%)
- **Cross-field consistency:** education_code maps deterministically 1:1 with education_typical across all 832 rows.

#### work_experience_code
- **Null Rate:** 0.0%
- **Range:** 1 to 3 (all 3 values present)
- **Distribution:** 3 (None) = 716 (86.1%), 2 (Less than 5 years) = 88 (10.6%), 1 (5+ years) = 28 (3.4%)
- **Cross-field consistency:** 1:1 with work_experience across all 832 rows.

#### training_code
- **Null Rate:** 0.0%
- **Range:** 1 to 6 (all 6 values present)
- **Distribution:** 6 (None) = 322 (38.7%), 4 (Moderate-term OJT) = 229 (27.5%), 5 (Short-term OJT) = 174 (20.9%), 3 (Long-term OJT) = 56 (6.7%), 1 (Internship/residency) = 36 (4.3%), 2 (Apprenticeship) = 15 (1.8%)
- **Cross-field consistency:** 1:1 with training_typical across all 832 rows.

---

### Growth Category Distribution (Spec Thresholds Applied)

| Category | Count | Pct | Min Pct | Max Pct |
|----------|-------|-----|---------|---------|
| declining_fast (< -10.0) | 54 | 6.5% | -36.1 | -10.1 |
| declining (-10.0 to -1.0) | 155 | 18.6% | -10.0 | -1.1 |
| stable (-1.0 to 1.0) | 80 | 9.6% | -1.0 | 0.9 |
| growing (1.0 to 10.0) | 481 | 57.8% | 1.0 | 9.7 |
| growing_fast (10.0 to 20.0) | 51 | 6.1% | 10.0 | 19.8 |
| booming (>= 20.0) | 11 | 1.3% | 20.0 | 49.9 |

Sum: 832 (no nulls in employment_change_pct, so no null growth_category rows).

---

### Broad Occupation Codes (7 confirmed)

| SOC Code | Title |
|----------|-------|
| 13-1020 | Buyers and purchasing agents |
| 13-2020 | Property appraisers and assessors |
| 29-2010 | Clinical laboratory technologists and technicians |
| 31-1120 | Home health and personal care aides |
| 39-7010 | Tour and travel guides |
| 47-4090 | Miscellaneous construction and related workers |
| 51-2090 | Miscellaneous assemblers and fabricators |

All 7 found. None overlap with catchall flag (no "all other" in any title).

---

### Catchall Categories (70, not 46)

70 occupations have "all other" in their title (case-insensitive). All 22 major groups have at least 1 catchall. Distribution by group ranges from 1 (groups 23, 31, 41) to 7 (group 29 Healthcare Practitioners). One edge case: 29-1029 "Dentists, all other specialists" has "all other" mid-title, not at the end.

The spec's stated count of 46 is incorrect. The earlier Bronze SOC audit may have used a different counting methodology or a different data pull. The actual count from the full 832-row dataset is 70.

---

### Cross-Field Analysis

#### Wage by Growth Category
| Growth Category | N | Avg Wage | Median Wage | Null Wages |
|----------------|---|----------|-------------|------------|
| declining_fast | 54 | $49,776 | $46,620 | 0 |
| declining | 155 | $56,386 | $50,965 | 1 |
| stable | 80 | $66,749 | $61,490 | 1 |
| growing | 481 | $70,541 | $61,830 | 21 |
| growing_fast | 51 | $75,568 | $65,670 | 0 |
| booming | 11 | $96,139 | $112,590 | 0 |

Higher-growth occupations tend to have higher wages. Most null-wage occupations (21 of 23) fall in the "growing" category -- these are physicians/surgeons and performers who tend to be in growing fields.

#### Employment Change Consistency
`employment_projected - employment_current = employment_change` holds within +/- 1,000 for all 832 rows. Zero violations.

#### Code-Text Determinism
All code-to-text mappings (education, work experience, training) are deterministic. Same code always maps to the same text label across all 832 rows.

---

### Null Pattern Analysis

| Field | Null Count | Null Rate | Notes |
|-------|-----------|-----------|-------|
| soc_code | 0 | 0.0% | Grain field, required |
| occupation_title | 0 | 0.0% | Required |
| employment_current | 0 | 0.0% | |
| employment_projected | 0 | 0.0% | |
| employment_change | 0 | 0.0% | |
| employment_change_pct | 0 | 0.0% | |
| openings_annual_avg | 0 | 0.0% | |
| median_annual_wage | 23 | 2.8% | 14 physicians/surgeons, 5 performers, 3 dental specialists, 1 fishing/hunting |
| median_wage_capped | 0 | 0.0% | All False |
| education_typical | 0 | 0.0% | |
| education_code | 0 | 0.0% | |
| work_experience | 0 | 0.0% | |
| work_experience_code | 0 | 0.0% | |
| training_typical | 0 | 0.0% | |
| training_code | 0 | 0.0% | |

Only field with nulls: `median_annual_wage` (23 rows, 2.8%). All other fields are 100% complete.

---

### Golden Dataset Verification Points

#### Software Developers (15-1252)
- employment_current: 1,693,800
- employment_projected: 1,961,400
- employment_change: 267,700
- employment_change_pct: 15.8
- **Expected growth_category: growing_fast** (10.0 <= 15.8 < 20.0)
- median_annual_wage: $133,080
- education_code: 3 (Bachelor's degree)
- work_experience_code: 3 (None)
- training_code: 6 (None)

#### Registered Nurses (29-1141)
- employment_current: 3,391,000
- employment_projected: 3,557,100
- employment_change: 166,100
- employment_change_pct: 4.9
- **Expected growth_category: growing** (1.0 <= 4.9 < 10.0)
- median_annual_wage: $93,600
- education_code: 3 (Bachelor's degree)

#### Word Processors and Typists (43-9022) -- declining example
- employment_change_pct: -36.1
- **Expected growth_category: declining_fast** (< -10.0)
- employment_change: -14,400

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation for @dq-rule-writer |
|-------------|-------|------------|-------------------------------------|
| Catchall occupations ("all other" in title) | 70 | 8.4% | **SPEC CORRECTION NEEDED:** Set catchall_flag TRUE count to 70, not 46. |
| Broad occupation codes | 7 | 0.8% | Hardcode list of 7. Exact match only. |
| Null median_annual_wage | 23 | 2.8% | Max null rate threshold: 5%. Actual well under. |
| wage_available flag | 809 true, 23 false | - | Must match `median_annual_wage IS NOT NULL` exactly. |
| Capped wages | 0 | 0.0% | median_wage_capped = all False. Expect 0 True. |
| Zero openings | 4 | 0.5% | Allow openings_annual_avg >= 0. |
| Negative employment_change | 232 | 27.9% | Allow negative. Threshold: 15-40% negative expected. |
| Negative employment_change_pct | 244 | 29.3% | Allow negative. Note: 12 more than change due to rounding. |
| Sign discrepancy (change=0 but pct<0) | 12 | 1.4% | Do NOT enforce sign consistency between fields. |
| employment_change_pct range | - | - | Actual: -36.1 to 49.9. Sanity bound: -100 to +200. |
| median_annual_wage range (non-null) | - | - | Actual: $30,160 to $238,380. Bound: $15,000 to $250,000. |
| growth_category null count | 0 | 0.0% | All rows have non-null pct, so all get a category. |
| Growth category boundary rows | 19 | 2.3% | Exactly at threshold values. Ensure half-open intervals. |
| education_code range | 1-8 | 100% | Strict range 1-8. All 8 values present. |
| work_experience_code range | 1-3 | 100% | Strict range 1-3. All 3 values present. |
| training_code range | 1-6 | 100% | Strict range 1-6. All 6 values present. |
| SOC major groups | 22 | 100% | All 22 groups populated. Referential integrity against lookup. |
| Row count | 832 | - | Exact match Bronze to Silver: 0 rows added or dropped. |
| Grain uniqueness | 0 dupes | - | soc_code is 100% unique across 832 rows. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| catchall count | Spec mismatch | 70 vs 46 stated | HIGH | Spec says 46 "all other" categories but actual count is 70. Spec must be corrected. |
| employment_change vs pct sign | Rounding artifact | 12 | LOW | BLS rounds absolute change to thousands but pct from unrounded. Not a DQ issue. |
| employment_change = 0, pct != 0 | Rounding artifact | 10+ | LOW | Small occupations where absolute change rounds to 0 but fractional pct remains. |
| openings_annual_avg = 0 | Rounding artifact | 4 | LOW | BLS rounding from thousands. Known and documented. |
| median_annual_wage null | Expected | 23 | LOW | Physicians/surgeons/performers where BLS does not report standard median wage. |

---

### DQ Threshold Recommendations for Silver `base.bls_ooh`

#### Row Count
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Total rows | Exactly 832 | No rows added or dropped in Silver |
| Grain uniqueness (soc_code) | 0 duplicates | 832 distinct across 832 rows |

#### Completeness (max null rate)
| Field | Threshold | Actual | Notes |
|-------|-----------|--------|-------|
| soc_code | 0% | 0.0% | Grain field |
| occupation_title | 0% | 0.0% | |
| soc_major_group | 0% | N/A (derived) | Must be non-null for all rows |
| soc_major_group_name | 0% | N/A (derived) | Must be non-null for all rows |
| broad_occupation_flag | 0% | N/A (derived) | Boolean, never null |
| catchall_flag | 0% | N/A (derived) | Boolean, never null |
| employment_current | 0% | 0.0% | |
| employment_projected | 0% | 0.0% | |
| employment_change | 0% | 0.0% | |
| employment_change_pct | 0% | 0.0% | |
| openings_annual_avg | 0% | 0.0% | |
| growth_category | 0% | 0.0% | All rows have non-null pct |
| median_annual_wage | 5% | 2.8% | 23 nulls expected |
| wage_available | 0% | N/A (derived) | Boolean, never null |
| median_wage_capped | 0% | 0.0% | |
| education_code | 0% | 0.0% | |
| education_level_name | 0% | N/A (derived) | Non-null when education_code non-null |
| work_experience_code | 0% | 0.0% | |
| training_code | 0% | 0.0% | |

#### Value Ranges
| Field | Min | Max | Actual Range | Notes |
|-------|-----|-----|-------------|-------|
| employment_current | 1 | 10,000,000 | 200 - 4,347,700 | Must be positive |
| employment_projected | 1 | 10,000,000 | 200 - 5,087,500 | Must be positive |
| employment_change | -1,000,000 | 1,000,000 | -313,600 - 739,800 | Can be negative |
| employment_change_pct | -100.0 | 200.0 | -36.1 - 49.9 | Sanity bounds |
| openings_annual_avg | 0 | 1,000,000 | 0 - 904,300 | Allow zero |
| median_annual_wage | 15,000 | 250,000 | 30,160 - 238,380 | When non-null |
| education_code | 1 | 8 | 1 - 8 | Strict enumeration |
| work_experience_code | 1 | 3 | 1 - 3 | Strict enumeration |
| training_code | 1 | 6 | 1 - 6 | Strict enumeration |

#### Derived Field Validation
| Rule | Expected | Evidence |
|------|----------|----------|
| broad_occupation_flag TRUE count | 7 | Hardcoded list, all 7 confirmed present |
| catchall_flag TRUE count | 70 | Case-insensitive "all other" substring match against 832 titles |
| growth_category valid values | 6 categories (no nulls) | All 832 rows have non-null employment_change_pct |
| growth_category distribution | declining_fast=54, declining=155, stable=80, growing=481, growing_fast=51, booming=11 | Verified with spec thresholds |
| wage_available = (median_annual_wage IS NOT NULL) | 809 true, 23 false | Must be exact inverse of wage null |
| median_wage_capped TRUE count | 0 | Interactive export has no top-coding |
| soc_major_group valid values | 22 codes: 11,13,15,17,19,21,23,25,27,29,31,33,35,37,39,41,43,45,47,49,51,53 | All present |
| education_level_name referential integrity | 8 valid names from lookup | 1:1 with education_code |

#### Consistency Rules
| Rule | Description | Evidence |
|------|-------------|----------|
| Employment change math | projected - current = change (+/- 1000) | 0 violations across 832 rows |
| Code-text determinism | education_code always maps to same education_typical | 0 violations |
| Code-text determinism | work_experience_code always maps to same work_experience | 0 violations |
| Code-text determinism | training_code always maps to same training_typical | 0 violations |
| wage_available consistency | wage_available = (median_annual_wage IS NOT NULL) | Must hold for all 832 rows |
| growth_category consistency | growth_category matches employment_change_pct bucket | Must hold for all 832 rows |
| Do NOT enforce | sign consistency between employment_change and employment_change_pct | 12 known rounding discrepancies |

---

### Recommendations for Downstream Agents

**For @dq-rule-writer:**
- Catchall count is 70, not 46. Update all rules and thresholds accordingly.
- Do not write a rule enforcing sign consistency between employment_change and employment_change_pct.
- growth_category null count = 0 in current data (all rows have employment_change_pct). But the spec allows null growth_category when pct is null, so the rule should handle both cases.
- All growth category boundary values have rows sitting exactly on them. Test half-open interval edge cases.

**For @semantic-modeler / @primary-agent:**
- The 12 sign-discrepancy rows (change=0, pct<0) should pass through Silver unchanged. Do not "fix" them.
- education_level_name derivation must handle all 8 codes. All 8 are present in the data.
- 29-1029 "Dentists, all other specialists" will correctly get catchall_flag=True since "all other" appears as a substring.

**For @data-steward:**
- The catchall count discrepancy (70 vs 46) should be flagged as a spec correction in the business glossary.
- SOC major group 25 (Educational Instruction and Library) has 64 occupations, heavily driven by postsecondary teacher specialties. This is not anomalous but may affect density of crosswalk matches.
