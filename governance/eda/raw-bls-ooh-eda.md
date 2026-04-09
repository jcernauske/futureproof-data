## EDA Report: raw.bls_ooh
**Source:** Bureau of Labor Statistics, Employment Projections program (Table 1.7 -- Occupational projections, 2023-33, and worker characteristics)  
**Date:** 2026-04-07  
**Agent:** @data-analyst (initial), @dq-engineer (full-dataset update)  
**Record Count:** 832 (FULL DATASET -- all BLS detailed occupations)  
**Field Count:** 15 (excludes metadata fields ingested_at, source_url, source_method, load_date)  
**Data File:** `data/raw/xlsx_cache/bls_ooh.xlsx` (real BLS Employment Projections interactive export)  
**Status:** FULL DATASET -- validated against all 832 detailed occupations from the BLS EP interactive export.

---

### Domain Context

**Identified Domain:** U.S. labor market -- occupation-level employment projections, wage data, and education/training requirements  
**Primary Entities:** Occupations classified by Standard Occupational Classification (SOC) codes  
**Grain:** One row per detailed occupation (SOC code in XX-XXXX format)  
**Temporal Pattern:** Snapshot -- BLS Employment Projections are released on a 2-year cycle (current cycle: 2023-2033); each release is a complete replacement, not incremental  
**Domain Vocabulary:**
- **SOC code** -- Standard Occupational Classification code (XX-XXXX format); 2018 taxonomy is current, SOC 2028 migration anticipated
- **Employment (in thousands)** -- Source values are in thousands (e.g., 1795.5 = 1,795,500 workers); ingestor multiplies by 1000 and rounds to long
- **Median annual wage** -- BLS-reported median wage; top-coded at $239,200 (the BLS wage cap for occupations where median exceeds data limits). Note: the interactive export uses actual numeric values, so no wages hit the exact $239,200 cap; the maximum observed wage is $238,380.
- **N/A wage** -- Occupations where wage data is not available or not applicable (e.g., elected officials, self-employed-dominated occupations)
- **Education code** -- BLS integer classification (1-8) mapping to entry-level education requirements (note: the ingestor derives codes from labels; 1=Doctoral, 8=No formal credential)
- **Work experience code** -- BLS integer classification for required related-occupation experience (1=5 years or more, 2=Less than 5 years, 3=None)
- **Training code** -- BLS integer classification for on-the-job training requirements (1=Internship/residency, 2=Apprenticeship, ..., 6=None)
- **Summary SOC codes** -- Codes ending in "0000" (e.g., 11-0000 "Management occupations") are major group aggregates; the ingestor filters these out

**Taxonomy/Codes Found:**
- SOC 2018 classification system -- all 832 detailed occupation codes present
- BLS education level codes 1-8: all 8 values observed in full dataset
- BLS work experience codes 1-3: all 3 values observed
- BLS training codes 1-6: all 6 values observed

---

### Key Findings

- **832 detailed occupations loaded.** All summary/aggregate SOC codes (XX-0000) were correctly filtered by the ingestor. The full BLS EP interactive export is correctly parsed.
- **All SOC codes pass XX-XXXX format validation.** 832 of 832 codes match the `^\d{2}-\d{4}$` pattern. Zero format anomalies.
- **Grain uniqueness holds.** 832 distinct SOC codes across 832 rows, zero duplicates.
- **Zero capped wages in interactive export.** Unlike the static EP tables, the interactive export uses actual numeric wage values. The maximum observed wage is $238,380 -- no wages hit the BLS cap of $239,200. As a result, `median_wage_capped` is False for all rows.
- **23 null wages (2.8%).** These are N/A occupations (elected officials, self-employed-dominated occupations). Well within the 5% threshold.
- **232 negative employment changes.** 27.9% of occupations are projected to decline -- expected for a full dataset. Range: -313,600 to +739,800.
- **4 occupations have zero annual openings.** Due to BLS rounding from thousands (occupations with <50 annual openings round to 0). These are Patternmakers wood, Pediatric surgeons, Prosthodontists, and Timing device assemblers.
- **Wide wage dispersion.** Wages range from $30,160 to $238,380. Median $59,280, mean $66,755 -- right-skewed distribution typical of U.S. wage data.
- **Education requirements heavily favor high school diploma** (39.2%), followed by Bachelor's degree (21.4%). All 8 education levels are represented.
- **Employment conversion from thousands is correct.** Smallest occupation has 200 workers (0.2 thousands in source), largest has 4,347,700.

---

### Field Profiles

#### soc_code
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 832 distinct values (100% uniqueness) -- this is the grain field
- **Patterns:** All match `^\d{2}-\d{4}$` (XX-XXXX format). No format anomalies.
- **Outliers:** None

#### occupation_title
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 832 distinct values (100% uniqueness -- 1:1 with soc_code)

#### employment_current
- **Type:** LONG (integer, converted from thousands)
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 832 distinct values

| Statistic | Value |
|-----------|-------|
| Min | 200 |
| P10 | 7,000 |
| P25 | 17,100 |
| Median | 50,200 |
| P75 | 161,500 |
| P90 | 477,130 |
| Max | 4,347,700 |
| Mean | 204,275 |
| StdDev | 468,176 |

- **Outliers:** Highly right-skewed. A few very large occupations (e.g., retail salespersons, food service) dominate the upper tail.

#### employment_projected
- **Type:** LONG (integer, converted from thousands)
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 832 distinct values

| Statistic | Value |
|-----------|-------|
| Min | 200 |
| P10 | 6,910 |
| P25 | 17,275 |
| Median | 50,250 |
| P75 | 162,400 |
| P90 | 500,390 |
| Max | 5,087,500 |
| Mean | 210,541 |
| StdDev | 484,799 |

#### employment_change
- **Type:** LONG (integer, converted from thousands)
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 806 distinct values

| Statistic | Value |
|-----------|-------|
| Min | -313,600 |
| P10 | -3,090 |
| P25 | -200 |
| Median | 700 |
| P75 | 4,800 |
| P90 | 17,730 |
| Max | 739,800 |
| Mean | 6,263 |
| StdDev | 38,553 |

- **Negative values:** 232 of 832 occupations (27.9%) are projected to decline. This is expected and valid.
- **Zero values:** Some occupations show 0 change (flat employment).

#### employment_change_pct
- **Type:** DOUBLE
- **Null Rate:** 0.0% (0 of 832 rows)

| Statistic | Value |
|-----------|-------|
| Min | -36.1% |
| P10 | -7.0% |
| P25 | -1.0% |
| Median | 2.0% |
| P75 | 5.0% |
| P90 | 9.0% |
| Max | 49.9% |
| Mean | 2.0% |
| StdDev | 8.0% |

#### openings_annual_avg
- **Type:** LONG (integer, converted from thousands)
- **Null Rate:** 0.0% (0 of 832 rows)

| Statistic | Value |
|-----------|-------|
| Min | 0 |
| P10 | 600 |
| P25 | 1,500 |
| Median | 4,500 |
| P75 | 14,825 |
| P90 | 49,900 |
| Max | 904,300 |
| Mean | 22,670 |
| StdDev | 66,199 |

- **Zero openings:** 4 occupations have 0 openings due to BLS rounding from thousands (actual openings < 50 rounds to 0).

#### median_annual_wage
- **Type:** DOUBLE
- **Null Rate:** 2.8% (23 of 832 rows) -- N/A occupations (elected officials, self-employed-dominated)
- **Non-null count:** 809

| Statistic | Value |
|-----------|-------|
| Min | $30,160 |
| P10 | $37,700 |
| P25 | $45,980 |
| Median | $59,280 |
| P75 | $78,490 |
| P90 | $104,316 |
| Max | $238,380 |
| Mean | $66,755 |
| StdDev | $31,033 |

- **Wage capped values:** 0 of 809 non-null wages (0.0%) are capped. The interactive export uses actual numeric values, so no wages hit the exact $239,200 BLS cap ceiling. The maximum observed wage is $238,380.
- **Null wage occupations:** 23 occupations have N/A wages. These are elected officials, self-employed-dominated occupations, and similar categories where BLS does not report a standard median wage.

#### median_wage_capped
- **Type:** BOOLEAN
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 1 distinct value
- **Distribution:** False = 832 (100.0%)
- **Note:** All False because the interactive export uses actual numeric wages; no wages hit the exact $239,200 cap. This is consistent with the data source format.

#### education_typical
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 8 distinct values (all BLS education levels present)
- **Distribution:**

| Value | Count | Pct |
|-------|-------|-----|
| High school diploma or equivalent | 326 | 39.2% |
| Bachelor's degree | 178 | 21.4% |
| No formal educational credential | 109 | 13.1% |
| Doctoral or professional degree | 73 | 8.8% |
| Postsecondary nondegree award | 51 | 6.1% |
| Associate's degree | 48 | 5.8% |
| Master's degree | 40 | 4.8% |
| Some college, no degree | 7 | 0.8% |

#### education_code
- **Type:** INTEGER
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 8 distinct values (codes 1-8, all present)
- **Cross-field consistency:** education_code maps 1:1 with education_typical in all 832 rows.

#### work_experience
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 3 distinct values (all BLS work experience levels present)
- **Distribution:**

| Value | Count | Pct |
|-------|-------|-----|
| None | 716 | 86.1% |
| Less than 5 years | 88 | 10.6% |
| 5 years or more | 28 | 3.4% |

#### work_experience_code
- **Type:** INTEGER
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 3 distinct values (codes 1-3, all present)
- **Cross-field consistency:** work_experience_code maps 1:1 with work_experience in all 832 rows.

#### training_typical
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 6 distinct values (all BLS training levels present)
- **Distribution:**

| Value | Count | Pct |
|-------|-------|-----|
| None | 322 | 38.7% |
| Moderate-term on-the-job training | 229 | 27.5% |
| Short-term on-the-job training | 174 | 20.9% |
| Long-term on-the-job training | 56 | 6.7% |
| Internship/residency | 36 | 4.3% |
| Apprenticeship | 15 | 1.8% |

#### training_code
- **Type:** INTEGER
- **Null Rate:** 0.0% (0 of 832 rows)
- **Cardinality:** 6 distinct values (codes 1-6, all present)
- **Cross-field consistency:** training_code maps 1:1 with training_typical in all 832 rows.

---

### Cross-Field Analysis

#### Wage Capping Consistency
- `median_wage_capped` is False for all 832 rows.
- No wages equal $239,200 (the BLS cap).
- The interactive export uses actual numeric wage values, so the capping mechanism is not exercised. This is consistent behavior -- the ingestor correctly sets `median_wage_capped=False` for all rows.
- **Rule status:** RAW-OOH-004 PASSES. The rule correctly finds zero inconsistencies.

#### Employment Change Consistency
- For all 832 rows: `employment_projected - employment_current = employment_change` within the +/- 1000 rounding tolerance. Zero violations.
- **Rule status:** RAW-OOH-018 PASSES.

#### Education Level vs Wage
| Education Level | N | Mean Wage | Median Wage | Min | Max |
|----------------|---|-----------|-------------|-----|-----|
| High school diploma or equivalent | 326 | $49,148 | $43,860 | $30,160 | $112,860 |
| Bachelor's degree | 178 | $86,744 | $79,060 | $37,000 | $238,380 |
| No formal educational credential | 109 | $39,262 | $36,610 | $30,610 | $72,560 |
| Doctoral or professional degree | 73 | $104,835 | $93,320 | $42,480 | $231,750 |
| Postsecondary nondegree award | 51 | $48,905 | $44,870 | $33,680 | $99,620 |
| Associate's degree | 48 | $63,204 | $53,430 | $36,900 | $160,920 |
| Master's degree | 40 | $78,963 | $72,460 | $39,220 | $162,880 |
| Some college, no degree | 7 | $37,937 | $38,260 | $33,110 | $42,220 |

Higher education levels correlate with higher wages, as expected.

#### Zero-Openings Occupations
4 occupations have `openings_annual_avg = 0`:
- 51-7032 Patternmakers, wood (employment: 500)
- 29-1243 Pediatric surgeons (employment: 1,100)
- 29-1024 Prosthodontists (employment: 900)
- 51-2061 Timing device assemblers and adjusters (employment: 200)

All are very small occupations. BLS source data is in thousands; values like 0.04 thousands (40 actual openings) round to 0 after the ingestor's multiply-by-1000-and-round conversion. This is a known BLS rounding artifact, not a data quality issue.

---

### Null Rate Summary (All Fields)

| Field | Null Count | Null Rate |
|-------|-----------|-----------|
| soc_code | 0 | 0.0% |
| occupation_title | 0 | 0.0% |
| employment_current | 0 | 0.0% |
| employment_projected | 0 | 0.0% |
| employment_change | 0 | 0.0% |
| employment_change_pct | 0 | 0.0% |
| openings_annual_avg | 0 | 0.0% |
| median_annual_wage | 23 | 2.8% |
| median_wage_capped | 0 | 0.0% |
| education_typical | 0 | 0.0% |
| education_code | 0 | 0.0% |
| work_experience | 0 | 0.0% |
| work_experience_code | 0 | 0.0% |
| training_typical | 0 | 0.0% |
| training_code | 0 | 0.0% |

---

### Edge Cases for DQ Thresholds (Updated from Full Dataset)

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Null median_annual_wage (N/A occupations) | 23 | 2.8% | Threshold 5% CONFIRMED appropriate. Actual rate well under limit. |
| Wage capped at $239,200 | 0 | 0.0% | Interactive export does not top-code. Capping rule still valid for static EP tables. |
| Negative employment_change values | 232 | 27.9% | CONFIRMED: negative values are valid and expected for declining occupations. |
| Zero openings_annual_avg | 4 | 0.5% | BLS rounding artifact for tiny occupations. Rule should allow >= 0. |
| education_code range 1-8 | 832 | 100% | All 8 levels present. Range constraint CONFIRMED. |
| work_experience_code range 1-3 | 832 | 100% | All 3 levels present. Range constraint CONFIRMED. |
| training_code range 1-6 | 832 | 100% | All 6 levels present. Range constraint CONFIRMED. |
| Zero or negative employment_current | 0 | 0.0% | All positive. Constraint CONFIRMED. |
| Zero or negative employment_projected | 0 | 0.0% | All positive. Constraint CONFIRMED. |
| Duplicate SOC codes | 0 | 0.0% | Grain uniqueness CONFIRMED. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| median_annual_wage | Null (N/A) | 23 (2.8%) | LOW | Expected for elected officials, self-employed-dominated occupations. Not a data quality issue. |
| median_wage_capped | All False | 832 (100%) | INFO | Interactive export uses actual numeric wages; no capping observed. Consistent with data source format. |
| openings_annual_avg | Zero openings | 4 (0.5%) | LOW | BLS rounding artifact for very small occupations. DQ rule RAW-OOH-013 needs amendment to allow zero. |
| employment_change | Negative values | 232 (27.9%) | INFO | Expected for declining occupations. DQ rules correctly allow negative values. |

No data integrity anomalies were detected in the full dataset. All field transformations (wage parsing, employment conversion, SOC formatting, summary filtering, education/training code derivation) are functioning correctly.

---

### DQ Threshold Recommendations (Updated from Full Dataset)

All thresholds previously marked PRELIMINARY have been validated against the full 832-row dataset. Updated status below.

#### Row Count Rules

| Rule | Threshold | Evidence | Status |
|------|-----------|----------|--------|
| Total row count (post-filter) | 750 - 900 | Actual: 832. Within range. | CONFIRMED |
| Grain uniqueness (soc_code) | 0 duplicates | Actual: 0 duplicates across 832 rows. | CONFIRMED |

#### Completeness Rules

| Field | Max Null Rate | Actual Null Rate | Status |
|-------|---------------|-----------------|--------|
| soc_code | 0% | 0.0% | CONFIRMED |
| occupation_title | 0% | 0.0% | CONFIRMED |
| employment_current | 0% | 0.0% | CONFIRMED |
| employment_projected | 0% | 0.0% | CONFIRMED |
| employment_change | 0% | 0.0% | CONFIRMED |
| employment_change_pct | 0% | 0.0% | CONFIRMED |
| openings_annual_avg | 0% | 0.0% | CONFIRMED |
| median_annual_wage | 5% | 2.8% (23/832) | CONFIRMED |
| median_wage_capped | 0% | 0.0% | CONFIRMED |
| education_typical | 0% | 0.0% | CONFIRMED |
| education_code | 0% | 0.0% | CONFIRMED |
| work_experience | 0% | 0.0% | CONFIRMED |
| work_experience_code | 0% | 0.0% | CONFIRMED |
| training_typical | 0% | 0.0% | CONFIRMED |
| training_code | 0% | 0.0% | CONFIRMED |

#### Value Range Rules

| Field | Min | Max | Actual Min | Actual Max | Status |
|-------|-----|-----|-----------|-----------|--------|
| median_annual_wage | $20,000 | $239,200 | $30,160 | $238,380 | CONFIRMED |
| employment_current | 1 | 10,000,000 | 200 | 4,347,700 | CONFIRMED |
| employment_projected | 1 | 10,000,000 | 200 | 5,087,500 | CONFIRMED |
| openings_annual_avg | 0 (amended) | 1,000,000 | 0 | 904,300 | AMENDED (was >= 1) |
| education_code | 1 | 8 | 1 | 8 | CONFIRMED |
| work_experience_code | 1 | 3 | 1 | 3 | CONFIRMED |
| training_code | 1 | 6 | 1 | 6 | CONFIRMED |

#### Consistency Rules

| Rule | Description | Actual | Status |
|------|-------------|--------|--------|
| Wage cap flag consistency | capped=true IFF wage=239200.0 | 0 violations | CONFIRMED |
| Employment change consistency | projected - current = change (+/- 1000) | 0 violations | CONFIRMED |
| Code-text determinism | Same code always maps to same text | 0 violations | CONFIRMED |

#### Statistical Rules (Warn, Not Reject)

| Field | Rule | Threshold | Actual | Status |
|-------|------|-----------|--------|--------|
| median_annual_wage | Mean range | $40,000 - $70,000 | $66,755 | CONFIRMED (within range) |
| median_annual_wage | Capped rate | 0% - 8% | 0.0% | CONFIRMED (interactive export has no capping) |
| employment_change_pct | Negative rate | 15% - 40% | 27.9% | CONFIRMED (within range) |

---

### Recommendations for Downstream Agents (Updated)

**For @dq-rule-writer:**
- AMEND RAW-OOH-013 to allow zero openings (>= 0 instead of > 0). Root cause documented above.
- All other thresholds are confirmed against full data. No further changes needed.
- Consider adding a rule to validate that education_code/work_experience_code/training_code map deterministically to their text counterparts.

**For @semantic-modeler:**
- SOC code is the primary join to O*NET (direct join) and College Scorecard (via CIP-SOC crosswalk).
- `median_wage_capped` is always False in the interactive export. If static EP tables are used in the future, capping may appear. Preserve the field through silver zone.
- 232 occupations have negative employment changes -- ensure the silver/gold zone models handle negative growth correctly.
- 23 N/A-wage occupations need careful handling in any wage-based analysis.

**For @data-steward:**
- Domain vocabulary is consistent across all 832 rows.
- All BLS code-to-text mappings are deterministic and complete (8 education, 3 experience, 6 training levels).
- SOC taxonomy reference: https://www.bls.gov/soc/2018/
