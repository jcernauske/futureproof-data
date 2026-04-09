# CDE Field Quality Validation: raw.bls_ooh

**Date:** 2026-04-07
**Agent:** @data-analyst
**Dataset:** data/raw/xlsx_cache/bls_ooh.xlsx
**Record Count:** 832
**CDEs Validated:** 5 (soc_code, occupation_title, employment_change_pct, median_annual_wage, education_code)

## Validation Summary

| CDE | Null Rate | Format Valid | Issues |
|-----|-----------|-------------|--------|
| soc_code | 0.0% | 100.0% | 7 rolled-up/broad codes ending in 0 |
| occupation_title | 0.0% | 100.0% | 16 titles exceed 80 chars (max 112) |
| employment_change_pct | 0.0% | 100.0% | No outliers beyond +/- 50% |
| median_annual_wage | 2.8% | 100.0% | 23 nulls (physicians, performers, fishing) |
| education_code | 0.0% | 100.0% | All 8 BLS categories represented |

**Overall assessment:** All 5 CDEs pass quality validation. The dataset is clean with well-understood null patterns. No data quality rules need exception thresholds beyond those documented below.

---

## CDE 1: soc_code

### Completeness
- **Null count:** 0 of 832 (0.0%)
- **Expected:** 0% -- PASS

### Format Validity
- **Pattern:** XX-XXXX (two digits, hyphen, four digits)
- **Valid:** 832 of 832 (100.0%)
- **Invalid:** 0
- **Expected:** 100% -- PASS

### Uniqueness
- **Distinct values:** 832
- **Duplicates:** 0
- **Expected:** 0 duplicates (grain field) -- PASS

### Distribution by SOC Major Group (2-digit prefix)

| Major Group | Group Name | Count | % of Total |
|-------------|-----------|-------|------------|
| 11 | Management | 38 | 4.6% |
| 13 | Business and Financial Operations | 32 | 3.8% |
| 15 | Computer and Mathematical | 21 | 2.5% |
| 17 | Architecture and Engineering | 36 | 4.3% |
| 19 | Life, Physical, and Social Science | 48 | 5.8% |
| 21 | Community and Social Service | 17 | 2.0% |
| 23 | Legal | 8 | 1.0% |
| 25 | Educational Instruction and Library | 64 | 7.7% |
| 27 | Arts, Design, Entertainment, Sports, and Media | 41 | 4.9% |
| 29 | Healthcare Practitioners and Technical | 71 | 8.5% |
| 31 | Healthcare Support | 17 | 2.0% |
| 33 | Protective Service | 24 | 2.9% |
| 35 | Food Preparation and Serving Related | 17 | 2.0% |
| 37 | Building and Grounds Cleaning and Maintenance | 10 | 1.2% |
| 39 | Personal Care and Service | 32 | 3.8% |
| 41 | Sales and Related | 22 | 2.6% |
| 43 | Office and Administrative Support | 54 | 6.5% |
| 45 | Farming, Fishing, and Forestry | 14 | 1.7% |
| 47 | Construction and Extraction | 60 | 7.2% |
| 49 | Installation, Maintenance, and Repair | 51 | 6.1% |
| 51 | Production | 105 | 12.6% |
| 53 | Transportation and Material Moving | 50 | 6.0% |

All 22 SOC major groups are represented. Production (51-xxxx) is the largest group at 12.6%, consistent with the BLS classification having many detailed manufacturing occupations.

### Special Codes Noted

7 rolled-up/broad occupation codes ending in `0` (see SOC Code Alignment Audit for details):
- 13-1020, 13-2020, 29-2010, 31-1120, 39-7010, 47-4090, 51-2090

These are legitimate BLS codes but combine multiple detailed occupations. ConceptNormalizer should handle these as parent codes.

---

## CDE 2: occupation_title

### Completeness
- **Null count:** 0 of 832 (0.0%)
- **Empty/whitespace-only:** 0
- **Expected:** 0% -- PASS

### Casing Consistency
- **Title/sentence case:** 832 (100.0%)
- **ALL CAPS:** 0
- **all lowercase:** 0
- **Assessment:** Perfectly consistent title case throughout -- PASS

### Length Analysis
- **Minimum length:** 6 characters
- **Maximum length:** 112 characters
- **Titles exceeding 80 characters:** 16 (1.9%)
- **Titles exceeding 100 characters:** 2 (0.2%)

Long titles (>80 chars) -- all are legitimate BLS occupation names, not truncation artifacts:

| SOC Code | Title | Length |
|----------|-------|--------|
| 53-1047 | First-line supervisors of transportation and material moving workers, except aircraft cargo handling supervisors | 112 |
| 51-2028 | Electrical, electronic, and electromechanical assemblers, except coil winders, tapers, and finishers | 100 |
| 51-9012 | Separating, filtering, clarifying, precipitating, and still machine setters, operators, and tenders | 99 |
| 41-3091 | Sales representatives of services, except advertising, insurance, financial services, and travel | 96 |
| 25-3011 | Adult basic education, adult secondary education, and english as a second language instructors | 94 |
| 41-4012 | Sales representatives, wholesale and manufacturing, except technical and scientific products | 92 |
| 51-4072 | Molding, coremaking, and casting machine setters, operators, and tenders, metal and plastic | 91 |
| 51-6091 | Extruding and forming machine setters, operators, and tenders, synthetic and glass fibers | 89 |
| 39-1014 | First-line supervisors of entertainment and recreation workers, except gambling services | 88 |
| 51-4031 | Cutting, punching, and press machine setters, operators, and tenders, metal and plastic | 87 |
| 41-4011 | Sales representatives, wholesale and manufacturing, technical and scientific products | 85 |
| 51-9041 | Extruding, forming, pressing, and compacting machine setters, operators, and tenders | 84 |
| 51-4032 | Drilling and boring machine tool setters, operators, and tenders, metal and plastic | 83 |
| 51-6064 | Textile winding, twisting, and drawing out machine setters, operators, and tenders | 82 |
| 51-4034 | Lathe and turning machine tool setters, operators, and tenders, metal and plastic | 81 |
| 51-4033 | Grinding, lapping, polishing, and buffing machine tool setters, operators, and tenders, metal and plastic | 105 |

**Assessment:** No truncation artifacts detected. All long titles are standard BLS occupation names with detailed qualifiers. No DQ rule needed for truncation -- these are expected values.

---

## CDE 3: employment_change_pct

### Completeness
- **Null count:** 0 of 832 (0.0%)
- **Expected:** Low null rate -- PASS

### Distribution

| Statistic | Value |
|-----------|-------|
| Min | -36.1% |
| P10 | -6.7% |
| P25 | -1.1% |
| Median | 2.5% |
| P75 | 5.0% |
| P90 | 8.6% |
| Max | 49.9% |

### Directional Breakdown

| Direction | Count | % of Total |
|-----------|-------|------------|
| Positive (growing) | 581 | 69.8% |
| Negative (declining) | 244 | 29.3% |
| Zero (flat) | 7 | 0.8% |

### Outlier Check

- **Occupations > +50% growth:** 0 -- no extreme positive outliers
- **Occupations < -50% decline:** 0 -- no extreme negative outliers
- **Assessment:** The range of -36.1% to +49.9% is plausible for 10-year occupational projections. No values exceed the +/- 50% review threshold.

The distribution is right-skewed (median 2.5%, mean likely similar), reflecting an economy with more growing than declining occupations. This is consistent with BLS projection methodology.

**DQ rule recommendation:** Flag but do not reject values outside [-50%, +100%]. The current dataset has no values that would trigger this rule.

---

## CDE 4: median_annual_wage

### Completeness
- **Null count:** 23 of 832 (2.8%)
- **Non-null:** 809 (97.2%)

### Null Wage Occupations (23 total)

These fall into three explainable categories:

**Category 1: Performers and entertainers (5 occupations)** -- Wages are typically variable/project-based and not reported as annual median:
| SOC Code | Occupation Title |
|----------|-----------------|
| 27-2011 | Actors |
| 27-2031 | Dancers |
| 27-2042 | Musicians and singers |
| 27-2091 | Disc jockeys, except radio |
| 27-2099 | Entertainers and performers, sports and related workers, all other |

**Category 2: Physicians and surgeons (17 occupations)** -- Wages exceed the BLS reportable threshold (top-coded), so BLS reports them as N/A rather than a capped value:
| SOC Code | Occupation Title |
|----------|-----------------|
| 29-1022 | Oral and maxillofacial surgeons |
| 29-1023 | Orthodontists |
| 29-1024 | Prosthodontists |
| 29-1211 | Anesthesiologists |
| 29-1212 | Cardiologists |
| 29-1213 | Dermatologists |
| 29-1214 | Emergency medicine physicians |
| 29-1217 | Neurologists |
| 29-1218 | Obstetricians and gynecologists |
| 29-1222 | Physicians, pathologists |
| 29-1223 | Psychiatrists |
| 29-1224 | Radiologists |
| 29-1229 | Physicians, all other |
| 29-1241 | Ophthalmologists, except pediatric |
| 29-1242 | Orthopedic surgeons, except pediatric |
| 29-1243 | Pediatric surgeons |
| 29-1249 | Surgeons, all other |

**Category 3: Seasonal/variable work (1 occupation)**:
| SOC Code | Occupation Title |
|----------|-----------------|
| 45-3031 | Fishing and hunting workers |

**Assessment:** All 23 null wages are explainable and expected. The physician/surgeon nulls are because BLS does not publish median wages for occupations above the reportable ceiling (approximately $239,200). The performer nulls are because these occupations lack a standard annual wage structure.

### Distribution of Non-Null Wages

| Statistic | Value |
|-----------|-------|
| Min | $30,160 |
| P10 | $37,700 |
| P25 | $45,950 |
| Median | $59,280 |
| P75 | $78,560 |
| P90 | $104,620 |
| Max | $238,380 |

### Wage Cap Check
- **Capped wages (median_wage_capped=True):** 0
- This is notable -- no wages in the dataset triggered the top-code detection logic in the ingestor. The 17 physician/surgeon occupations that exceed the BLS ceiling appear as null wages rather than capped values. This is correct behavior: the source reports these as N/A, not as ">=$239,200".

### Suspicious/Round Values
- **Values divisible by $10,000:** 0
- **Assessment:** No placeholder or suspiciously round values detected. All wages appear to be genuine BLS estimates.

**DQ rule recommendations:**
- Null rate threshold: allow up to 5% null (current 2.8% is within tolerance given known N/A categories)
- Wage range: flag values outside [$20,000, $250,000] for manual review
- Expect 0 capped wages if BLS reports high-earner occupations as N/A rather than capped

---

## CDE 5: education_code

### Completeness
- **Null count:** 0 of 832 (0.0%)
- **Expected:** 0% (derived from education_typical labels) -- PASS

### Distinct Values and Distribution

| Code | Label | Count | % of Total |
|------|-------|-------|------------|
| 1 | Doctoral or professional degree | 73 | 8.8% |
| 2 | Master's degree | 40 | 4.8% |
| 3 | Bachelor's degree | 178 | 21.4% |
| 4 | Associate's degree | 48 | 5.8% |
| 5 | Postsecondary nondegree award | 51 | 6.1% |
| 6 | Some college, no degree | 7 | 0.8% |
| 7 | High school diploma or equivalent | 326 | 39.2% |
| 8 | No formal educational credential | 109 | 13.1% |

### Validation Against BLS Categories

All 8 expected BLS education categories from Table 5.4 are present. No unexpected codes exist. The `education_typical` string labels map 1:1 to codes with no unmapped values.

**Label-to-code consistency check:** All 832 rows have matching `education_typical` labels and `education_code` values. No mismatches detected.

### Distribution Assessment

The distribution is consistent with BLS occupation structure:
- 39.2% of occupations require only a high school diploma -- expected, as the largest category in BLS projections
- 21.4% require a bachelor's degree -- the second-largest category
- Only 0.8% (7 occupations) fall in "Some college, no degree" -- a narrow category in BLS methodology
- Doctoral/professional degree at 8.8% reflects physician, lawyer, and PhD-requiring occupations

**DQ rule recommendation:** Enforce `education_code IN (1,2,3,4,5,6,7,8)` with 0% tolerance for out-of-range values.

---

## Cross-CDE Consistency Checks

### soc_code + occupation_title
- Every SOC code has exactly one occupation title (1:1 mapping confirmed by 832 unique codes = 832 unique pairs)
- No occupation title appears with multiple SOC codes

### median_annual_wage + education_code
- Null wages concentrate in education_code 1 (Doctoral/professional) -- 17 of 23 nulls are physicians/surgeons. This is a known and expected pattern.

### employment_change_pct completeness
- Unlike median_annual_wage, employment projections have 0% null rate -- BLS provides growth projections for all occupations including performers and physicians.
