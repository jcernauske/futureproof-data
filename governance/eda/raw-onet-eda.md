## EDA Report: O*NET Database (7 Tables)
**Source:** O*NET 30.2 Database (`db_30_2_text.zip`)
**Date:** 2026-04-07
**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-onet.md`

### Data Availability

The spec targets 7 files from the O*NET 30.2 ZIP archive. **Only 5 of 7 are present** in the download:

| # | File | Status | Rows | Columns |
|---|------|--------|------|---------|
| 1 | Occupation Data.txt | Present | 1,016 | 3 |
| 2 | Task Statements.txt | Present | 18,796 | 7 |
| 3 | Work Activities.txt | Present | 73,308 | 13 |
| 4 | Work Context.txt | Present | 297,676 | 14 |
| 5 | Career Changers Matrix.txt | **MISSING** | -- | -- |
| 6 | Career Starters Matrix.txt | **MISSING** | -- | -- |
| 7 | Related Occupations.txt | Present | 18,460 | 4 |

**Career Changers Matrix and Career Starters Matrix are not included in the O*NET 30.2 text database ZIP.** They are not available as separate downloads either. Every URL variant attempted returned HTTP 404. These files may have been discontinued or consolidated into the Related Occupations file, which now includes a `Relatedness Tier` column with values "Primary-Short", "Primary-Long", and "Supplemental" that could serve a similar purpose.

### Domain Context

**Identified Domain:** Occupational information / labor market analytics
**Primary Entities:** Occupations (coded with O*NET-SOC XX-XXXX.XX), their tasks, work activities, work contexts, and inter-occupation relationships
**Grain:** Varies per table (see individual profiles below)
**Temporal Pattern:** Survey-based snapshot data; dates range from 12/2004 to 12/2025 indicating rolling updates across occupations
**Domain Vocabulary:** O*NET-SOC codes, element IDs (Content Model taxonomy), scale types (IM/LV/CX/CXP/CT/CTP), task types (Core/Supplemental), domain sources (Incumbent/Occupational Expert/Analyst)
**Taxonomy/Codes Found:** O*NET-SOC (XX-XXXX.XX), Content Model element IDs (e.g., 4.A.1.a.1), O*NET scale system (IM, LV, CX, CXP, CT, CTP)

### Key Findings

- **Row counts differ significantly from spec estimates.** Occupation Data has 1,016 rows (spec said ~886). Work Context has 297,676 rows (spec said ~49,000). The spec underestimated Work Context because it did not account for the CXP category-percentage rows (5 categories per element per occupation).
- **93 "All Other" and Military occupations exist in Occupation Data but have NO data in any other file.** These are placeholder/residual SOC codes (e.g., "Managers, All Other", "Infantry Officers") with no survey data. All 93 are base codes (.00 suffix). All 19 military occupations (55-xxxx) are in this set.
- **An additional 29 occupations have Tasks and Related Occupations data but NO Work Activities or Work Context data** (122 total missing from WA/WC vs. 93 missing from Tasks). This means 29 occupations have partial data.
- **Career Changers and Career Starters Matrix files do not exist** in the O*NET 30.2 ZIP archive. The ingestor code references these files but they will fail to load.
- **Related Occupations schema has changed.** The file now has columns `Relatedness Tier` and `Index` instead of the expected `Related Index`. The `Relatedness Tier` column contains "Primary-Short" (index 1-5), "Primary-Long" (index 6-10), and "Supplemental" (index 11-20). The ingestor reads `Related Index` which will fail.
- **Work Context is much larger than expected** due to categorical percentage scales (CXP/CTP). Each CX-scale element generates 5 additional CXP rows (one per response category with percentage), and each CT-scale element generates 3 CTP rows. Normal occupations have 338 rows (not ~55).
- **16 occupations have only 57 Work Context rows** instead of 338. These 16 are missing all CXP and CTP category-percentage data. They have only the point-estimate CX and CT rows.
- **Work Activities not_relevant="Y" occurs only on the LV (Level) scale**, never IM. These 1,094 rows have data_value between 0.00 and 1.79 (mean 0.47), indicating activities rated as not relevant to the occupation.
- **All data has 0% null rate on required grain fields.** O*NET-SOC code format validation passes 100% across all files.

---

## 1. Occupation Data (raw.onet_occupations)

**Source File:** Occupation Data.txt
**Record Count:** 1,016
**Field Count:** 3 (O*NET-SOC Code, Title, Description)
**Grain:** One row per O*NET-SOC code

### Field Profiles

#### O*NET-SOC Code
- **Type:** STRING
- **Null Rate:** 0% (0 of 1,016)
- **Cardinality:** 1,016 distinct values (100% unique)
- **Format Validation:** 100% match `XX-XXXX.XX` pattern (0 invalid)
- **Suffix Distribution:** 867 codes end in `.00` (base BLS occupations), 149 codes have non-`.00` suffixes (O*NET detailed occupations)
  - .00: 867, .01: 55, .02: 24, .03: 19, .04: 16, .05: 8, .06: 8, .07: 6, .08: 6, .09: 3, .10: 2, .11: 1, .12: 1
- **Major Group Distribution (23 SOC major groups):**
  - 51 (Production): 114, 29 (Healthcare Practitioners): 96, 25 (Education): 68, 19 (Life/Physical/Social Science): 66, 47 (Construction): 65
  - 11 (Management): 59, 17 (Architecture/Engineering): 59, 53 (Transportation): 57, 43 (Office/Admin): 55, 13 (Business/Financial): 50
  - 27 (Arts/Design/Entertainment): 45, 15 (Computer/Mathematical): 38, 49 (Installation/Maintenance): 52, 39 (Personal Care): 34
  - 33 (Protective Service): 28, 41 (Sales): 23, 35 (Food Preparation): 18, 21 (Community/Social Service): 18, 31 (Healthcare Support): 20
  - 55 (Military): 19, 37 (Building/Grounds): 10, 45 (Farming/Fishing): 14, 23 (Legal): 8
- **BLS Cross-Reference:** 867 unique 6-digit BLS SOC codes derivable. 76 BLS SOCs have multiple O*NET detailed codes.

#### Title
- **Type:** STRING
- **Null Rate:** 0% (0 of 1,016)
- **Length:** min=6, max=105, mean=33.6 characters

#### Description
- **Type:** STRING
- **Null Rate:** 0% (0 of 1,016)
- **Length:** min=25, max=811, mean=214.0 characters

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| Row count | Deviation from spec | 130 extra | MEDIUM | Spec estimated ~886, actual is 1,016. Difference is 14.7%. Likely reflects O*NET 30.2 additions vs. older estimate. |

---

## 2. Task Statements (raw.onet_task_statements)

**Source File:** Task Statements.txt
**Record Count:** 18,796
**Field Count:** 7
**Grain:** O*NET-SOC Code x Task ID (verified unique -- 18,796 distinct Task IDs)

### Field Profiles

#### O*NET-SOC Code
- **Type:** STRING
- **Null Rate:** 0% (0 of 18,796)
- **Cardinality:** 923 distinct values
- **Format Validation:** 100% valid XX-XXXX.XX
- **Referential Integrity:** All 923 SOC codes exist in Occupation Data. 93 Occupation Data SOCs have no tasks (all are "All Other" residual categories or Military occupations).

#### Task ID
- **Type:** LONG (integer)
- **Null Rate:** 0%
- **Cardinality:** 18,796 distinct values (100% globally unique)

#### Task
- **Type:** STRING
- **Null Rate:** 0%
- **Length:** min=13, max=332, mean=98.0, median=94.0 characters

#### Task Type
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:**
  - Core: 13,643 (72.6%)
  - Supplemental: 4,308 (22.9%)
  - n/a: 845 (4.5%)
- **Note:** "n/a" values correlate exactly with domain_source="Analyst" (845 rows). These are analyst-derived tasks where task_type classification was not performed.

#### Incumbents Responding
- **Type:** INTEGER
- **Null Rate:** 6.3% (1,190 of 18,796 are empty/n/a)
- **Populated Stats:** count=17,606, min=18, max=238, mean=62.3, median=62.0, p05=20.0, p95=114.0
- **Pattern:** Nulls correlate perfectly with domain_source:
  - Analyst: 845/845 missing (100%)
  - Analyst - Transition: 345/345 missing (100%)
  - Incumbent: 0/13,193 missing (0%), range 27-238, mean=75.4
  - Occupational Expert: 0/4,413 missing (0%), range 18-38, mean=23.0
- **Note:** Occupational Expert sample sizes are much smaller (max 38) than Incumbent (max 238). This is expected -- expert panels are small.

#### Date
- **Type:** STRING (MM/YYYY format)
- **Null Rate:** 0%
- **Range:** 12/2004 to 12/2025 (21 years of rolling updates)
- **Distribution peak:** 2019-2025 (most data collected recently)
  - Top 5: 08/2021 (1,883), 08/2019 (1,743), 08/2022 (1,721), 08/2023 (1,706), 08/2025 (1,663)

#### Domain Source
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:**
  - Incumbent: 13,193 (70.2%)
  - Occupational Expert: 4,413 (23.5%)
  - Analyst: 845 (4.5%)
  - Analyst - Transition: 345 (1.8%)

### Cross-Field Analysis

- **Tasks per occupation:** min=4, max=40, mean=20.4, median=20.0
  - 1-5 tasks: 3 occupations (sparse data)
  - 6-10 tasks: 27 occupations
  - 11-15 tasks: 194 occupations
  - 16-20 tasks: 280 occupations (mode)
  - 21-25 tasks: 209 occupations
  - 26-30 tasks: 168 occupations
  - 31+ tasks: 42 occupations
- **task_type by domain_source:**
  - Analyst: 100% n/a
  - Analyst - Transition: 77.4% Core, 22.6% Supplemental
  - Incumbent: 72.2% Core, 27.8% Supplemental
  - Occupational Expert: 87.1% Core, 12.9% Supplemental

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| task_type = "n/a" | 845 | 4.5% | Allow -- correlates 1:1 with Analyst domain_source |
| Incumbents Responding is null | 1,190 | 6.3% | Allow -- correlates 1:1 with Analyst/Analyst-Transition sources |
| Occupations with < 10 tasks | 30 | 3.3% of occupations | Flag as low-coverage, do not reject |
| Occupations with no tasks at all | 93 | 9.2% of occ data | Allow -- "All Other" and Military residual codes |

---

## 3. Work Activities (raw.onet_work_activities)

**Source File:** Work Activities.txt
**Record Count:** 73,308
**Field Count:** 13
**Grain:** O*NET-SOC Code x Element ID x Scale ID (verified unique -- 0 duplicates)

### Field Profiles

#### O*NET-SOC Code
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 894 distinct values
- **Format Validation:** 100% valid
- **Referential Integrity:** All 894 exist in Occupation Data. 122 Occupation Data SOCs have no work activities.

#### Element ID
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 41 distinct values
- **Pattern:** Content Model IDs like "4.A.1.a.1", "4.A.4.c.3"

#### Element Name
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 41 distinct values (1:1 mapping with Element ID)
- **All 41 activities have exactly 1,788 rows each** (894 occupations x 2 scales)

#### Scale ID
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:** IM: 36,654 (50.0%), LV: 36,654 (50.0%)
- **Perfectly balanced** -- every occupation has both IM and LV for all 41 activities.

#### Data Value
- **Type:** DOUBLE
- **Null Rate:** 0%
- **IM scale (Importance):** count=36,654, min=1.00, max=4.99, mean=3.15, median=3.23, stdev=0.86, p05=1.59, p95=4.43
  - Expected range per Scales Reference: 1-5. **Observed max 4.99 -- within range.**
- **LV scale (Level):** count=36,654, min=0.00, max=6.81, mean=3.31, median=3.38, stdev=1.32, p05=0.97, p95=5.36
  - Expected range per Scales Reference: 0-7. **Observed max 6.81 -- within range.**

#### N (sample size)
- **Type:** INTEGER
- **Null Rate:** 1.8% (1,312 of 73,308 -- these are the "Analyst - Transition" rows)
- **Populated Stats:** count=71,996, min=9, max=99, mean=24.8, median=22.0, p05=16.0, p95=40.0

#### Standard Error
- **Type:** DOUBLE
- **Null Rate:** 25.3% (18,532 of 73,308)
- **Populated Stats:** count=54,776, min=0.0, max=2.5548, mean=0.3784, median=0.3440
- **Pattern:** Null when domain_source is "Occupational Expert" or "Analyst - Transition" (no sampling distribution from expert panels)

#### Lower CI Bound / Upper CI Bound
- **Type:** DOUBLE
- **Null Rate:** 25.3% (same pattern as Standard Error)

#### Recommend Suppress
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:**
  - N: 54,943 (74.9%)
  - n/a: 17,302 (23.6%)
  - Y: 1,063 (1.5%)
- **Y (suppress recommended):** 1,062 on LV scale, only 1 on IM scale. Mean N for suppressed rows = 21.4 (small samples).

#### Not Relevant
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:**
  - n/a: 36,654 (50.0%) -- all IM-scale rows
  - N: 35,560 (48.5%) -- LV-scale, activity is relevant
  - Y: 1,094 (1.5%) -- LV-scale, activity rated not relevant
- **not_relevant = "Y" details:** Only on LV scale. Data values range 0.00-1.79, mean 0.47. Most common: "Repairing and Maintaining Mechanical Equipment" (211), "Drafting, Laying Out, and Specifying Technical Devices" (204), "Operating Vehicles" (146), "Repairing Electronic Equipment" (142).

#### Domain Source
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:**
  - Incumbent: 54,776 (74.7%)
  - Occupational Expert: 17,220 (23.5%)
  - Analyst - Transition: 1,312 (1.8%)

#### Date
- **Type:** STRING (MM/YYYY)
- **Null Rate:** 0%
- **Range:** 12/2005 to 08/2025

### Structural Patterns

- **Every occupation has exactly 82 rows** (41 activities x 2 scales). No exceptions.
- **16 "Analyst - Transition" occupations** have N=null, no Standard Error/CI, and recommend_suppress = "n/a". These are transitioning occupations with analyst-derived ratings rather than survey data.

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| recommend_suppress = "Y" | 1,063 | 1.5% | Preserve flag; Silver zone should filter these |
| not_relevant = "Y" | 1,094 | 1.5% | Preserve flag; data_value near zero is expected |
| N is null (Analyst - Transition) | 1,312 | 1.8% | Allow -- no survey sample for analyst-derived |
| Standard Error is null | 18,532 | 25.3% | Allow -- expected for Expert/Analyst sources |
| IM data_value range 1.00-4.99 | 36,654 | 100% | DQ rule: IM must be in [1.0, 5.0] |
| LV data_value range 0.00-6.81 | 36,654 | 100% | DQ rule: LV must be in [0.0, 7.0] |

---

## 4. Work Context (raw.onet_work_context)

**Source File:** Work Context.txt
**Record Count:** 297,676
**Field Count:** 14 (includes Category column not present in Work Activities)
**Grain:** O*NET-SOC Code x Element ID x Scale ID x Category (verified unique -- 0 duplicates)

### Critical Schema Difference from Spec

The spec estimated ~49,000 rows. The actual count is **297,676** -- roughly 6x the estimate. This is because Work Context uses 4 different scale types, and two of them (CXP, CTP) expand rows by response category:

| Scale ID | Scale Name | Range | Rows | Description |
|----------|-----------|-------|------|-------------|
| CX | Context (point estimate) | 1-5 | 49,170 (16.5%) | Single rating per element per occupation |
| CXP | Context Categories 1-5 (percentage) | 0-100 | 241,450 (81.1%) | Percentage of respondents choosing each of 5 categories |
| CT | Context (point estimate) | 1-3 | 1,788 (0.6%) | For Work Schedules and Duration elements |
| CTP | Context Categories 1-3 (percentage) | 0-100 | 5,268 (1.8%) | Percentage choosing each of 3 categories |

**The CXP rows represent 81.1% of all Work Context data.** For every CX row, there are 5 corresponding CXP rows (one per category). For every CT row, there are 3 CTP rows.

### Field Profiles

#### O*NET-SOC Code
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 894 distinct values
- **Referential Integrity:** All 894 exist in Occupation Data. Same 122 missing as Work Activities.

#### Element ID / Element Name
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 57 distinct elements
- **55 elements use CX/CXP scales** (5-point context rating)
- **2 elements use CT/CTP scales:** "Work Schedules" (3-point: Regular/Irregular/Seasonal) and "Duration of Typical Work Week" (3-point: <40/40/>40 hours)

#### Scale ID
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:** CXP: 241,450 (81.1%), CX: 49,170 (16.5%), CTP: 5,268 (1.8%), CT: 1,788 (0.6%)

#### Category
- **Type:** INTEGER (as string in source)
- **Null Rate:** 0% -- **but "n/a" is used as a sentinel value** for CX and CT scales (50,958 rows)
- **Distribution:**
  - n/a: 50,958 (17.1%) -- point-estimate rows (CX/CT scales)
  - 1: 50,046 (16.8%)
  - 2: 50,046 (16.8%)
  - 3: 50,046 (16.8%)
  - 4: 48,290 (16.2%)
  - 5: 48,290 (16.2%)
- **Ingestor impact:** The ingestor uses `_coerce_int()` on Category which will convert "n/a" to None. This is correct behavior.

#### Data Value
- **Type:** DOUBLE
- **Null Rate:** 0%
- **By scale:**
  - CX: min=1.00, max=5.00, mean=2.79, stdev=1.22 (expected range 1-5)
  - CXP: min=0.00, max=100.00, mean=20.00, stdev=24.20 (percentages, expected 0-100)
  - CT: min=1.00, max=3.00, mean=1.80, stdev=0.60 (expected range 1-3)
  - CTP: min=0.00, max=100.00, mean=33.33, stdev=30.27 (percentages, expected 0-100)
- **CXP mean of 20.00 is expected** (5 categories, each averaging 20% = 100/5)
- **CTP mean of 33.33 is expected** (3 categories, each averaging 33.3% = 100/3)

#### Recommend Suppress
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution by scale:**
  - CX: N=37,547 (76.4%), n/a=11,605 (23.6%), Y=18 (0.04%)
  - CXP: N=176,495 (73.1%), n/a=57,750 (23.9%), Y=7,205 (3.0%)
  - CT: N=1,366 (76.4%), n/a=422 (23.6%), Y=0
  - CTP: N=3,747 (71.1%), n/a=1,260 (23.9%), Y=261 (5.0%)
- **Total Y: 7,484 (2.5%)**. Higher suppression rate on percentage-based scales (CXP/CTP) than point-estimate scales (CX/CT).

#### Not Relevant
- **Type:** STRING (categorical)
- **Null Rate:** 0%
- **Distribution:** 100% "n/a" (297,676 rows). **Not Relevant is never used in Work Context.** Unlike Work Activities where it flags irrelevant activities on the LV scale, Work Context has no equivalent. DQ rule should accept only "n/a".

#### N (sample size)
- **Type:** INTEGER
- **Null Rate:** 0.3% (912 rows -- the Analyst - Transition occupations)
- **Populated Stats:** count=296,764, min=12, max=99, mean=25.5, median=23.0, p05=16.0, p95=42.0

#### Standard Error
- **Type:** DOUBLE
- **Null Rate:** 24.2% (null for Occupational Expert and Analyst - Transition sources)
- **Populated Stats:** count=225,784, min=0.0, max=34.01, mean=5.72
- **Note:** CXP percentages can have high standard errors (max 34.01) because they represent proportions of small samples.

### Two-Tier Row Count Pattern

| Row Count | Occupations | Explanation |
|-----------|-------------|-------------|
| 338 | 878 | Full data: 55 elements x (1 CX + 5 CXP) + 2 elements x (1 CT + 3 CTP) = 330 + 8 = 338 |
| 57 | 16 | CX/CT only: 55 CX + 2 CT = 57. Missing all CXP and CTP category-percentage rows. |

The 16 occupations with 57 rows are: 11-3071.00, 11-9013.00, 13-1041.00, 13-2011.00, 15-1299.02, 17-2111.00, 17-3011.00, 17-3023.00, 17-3031.00, 19-4043.00, 19-4051.00, 27-3023.00, 43-4041.00, 51-9195.00, 53-4022.00, 53-6051.00. These are likely recently updated occupations where category-percentage data has not yet been collected.

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| recommend_suppress = "Y" | 7,484 | 2.5% | Preserve flag; higher rate than Work Activities |
| not_relevant always "n/a" | 297,676 | 100% | DQ rule: not_relevant must be "n/a" |
| Category = "n/a" (string) | 50,958 | 17.1% | Normal for CX/CT point-estimate rows |
| 16 occupations with 57 rows | 912 | 0.3% of rows | Flag but allow -- partial data, not corrupt |
| CX data_value range 1.00-5.00 | 49,170 | -- | DQ rule: CX scale must be in [1.0, 5.0] |
| CXP data_value range 0.00-100.00 | 241,450 | -- | DQ rule: CXP scale must be in [0.0, 100.0] |
| CT data_value range 1.00-3.00 | 1,788 | -- | DQ rule: CT scale must be in [1.0, 3.0] |
| CTP data_value range 0.00-100.00 | 5,268 | -- | DQ rule: CTP scale must be in [0.0, 100.0] |

---

## 5. Career Changers Matrix (raw.onet_career_changers)

**Source File:** Career Changers Matrix.txt
**Status: FILE NOT FOUND in O*NET 30.2 ZIP archive**

The Career Changers Matrix is not included in the `db_30_2_text.zip` download. Multiple URL patterns were attempted and all returned HTTP 404. The ingestor `OnetCareerChangersIngestor` will fail at runtime.

**Recommendation:** Remove this table from the ingestor or make it conditional. The Related Occupations file with its `Relatedness Tier` column may serve as a replacement.

---

## 6. Career Starters Matrix (raw.onet_career_starters)

**Source File:** Career Starters Matrix.txt
**Status: FILE NOT FOUND in O*NET 30.2 ZIP archive**

Same situation as Career Changers Matrix. The `OnetCareerStartersIngestor` will fail at runtime.

**Recommendation:** Same as above.

---

## 7. Related Occupations (raw.onet_related_occupations)

**Source File:** Related Occupations.txt
**Record Count:** 18,460
**Field Count:** 4
**Grain:** O*NET-SOC Code x Related O*NET-SOC Code (verified unique -- 0 duplicates)

### Critical Schema Change from Spec

The actual file columns are: `O*NET-SOC Code`, `Related O*NET-SOC Code`, `Relatedness Tier`, `Index`

The spec and ingestor expect a column named `Related Index`. **The actual column is named `Index`.** The ingestor reads `raw_row.get("Related Index")` which will return None for every row, causing all rows to be skipped.

Additionally, the file now contains a `Relatedness Tier` column not in the spec, which categorizes relationships:
- **Primary-Short** (Index 1-5): 4,615 rows -- closest related occupations
- **Primary-Long** (Index 6-10): 4,615 rows -- next-closest related occupations
- **Supplemental** (Index 11-20): 9,230 rows -- broader related occupations

### Field Profiles

#### O*NET-SOC Code (source)
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 923 distinct values
- **Format Validation:** 100% valid XX-XXXX.XX
- **Referential Integrity:** All 923 exist in Occupation Data

#### Related O*NET-SOC Code
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 920 distinct values
- **Format Validation:** 100% valid XX-XXXX.XX
- **Referential Integrity:** All 920 exist in Occupation Data

#### Relatedness Tier
- **Type:** STRING (categorical) -- **NOT IN SPEC**
- **Null Rate:** 0%
- **Distribution:**
  - Supplemental: 9,230 (50.0%)
  - Primary-Short: 4,615 (25.0%)
  - Primary-Long: 4,615 (25.0%)
- **Mapping to Index:** Primary-Short = Index 1-5, Primary-Long = Index 6-10, Supplemental = Index 11-20

#### Index
- **Type:** INTEGER (as string in source) -- **Spec calls this "Related Index"**
- **Null Rate:** 0%
- **Range:** 1-20
- **Distribution:** Exactly 923 rows per index value (perfectly uniform -- every occupation has all 20 ranks)
- **Structural:** Index 1-5 = Primary-Short (5 per occupation), Index 6-10 = Primary-Long (5 per occupation), Index 11-20 = Supplemental (10 per occupation)

### Structural Analysis

- **Exactly 20 rows per source occupation** -- no exceptions. 923 occupations x 20 = 18,460.
- **No self-references:** 0 cases where source SOC = related SOC.
- **Symmetry:** 10,402 of 18,460 pairs (56.3%) are symmetric (if A relates to B, B also relates to A). The remaining 43.7% are one-directional.
- **93 Occupation Data SOCs are NOT in Related Occupations** (the same "All Other"/Military set missing from other files).
- **The is_primary derivation in the ingestor** (index <= 10 = primary) is approximately correct but the new Relatedness Tier provides finer granularity: Primary-Short vs Primary-Long.

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Rows per occupation != 20 | 0 | 0% | DQ rule: exactly 20 rows per source SOC |
| Self-references | 0 | 0% | DQ rule: source != related |
| Index outside 1-20 | 0 | 0% | DQ rule: Index must be in [1, 20] |
| Column name mismatch | -- | -- | Ingestor must read "Index" not "Related Index" |
| Missing Relatedness Tier | -- | -- | Ingestor should capture this new column |

---

## Cross-Table Referential Integrity

| Source File | SOCs | In Occupation Data? | Coverage |
|-------------|------|--------------------|-|
| Occupation Data | 1,016 | -- (master) | 100% |
| Task Statements | 923 | 923/923 = 100% | 90.8% of occupations |
| Work Activities | 894 | 894/894 = 100% | 88.0% of occupations |
| Work Context | 894 | 894/894 = 100% | 88.0% of occupations |
| Related Occupations | 923 | 923/923 = 100% | 90.8% of occupations |

### Missing SOC Analysis

- **93 occupations** have NO data in ANY file beyond Occupation Data. All are "All Other" residual categories (e.g., "Managers, All Other") or Military occupations (55-xxxx). All are .00 base codes.
- **29 additional occupations** (122 total minus 93) are in Task Statements and Related Occupations but NOT in Work Activities or Work Context. These include recently added occupations like "Web and Digital Interface Designers" (15-1255.00) and "Crematory Operators" (39-4012.00).
- **Work Activities and Work Context always have the same 894 occupations** -- they are perfectly synchronized.

### BLS SOC Code Mapping

- 867 unique 6-digit BLS SOC codes derivable from the 1,016 O*NET codes
- 76 BLS SOCs have multiple O*NET detailed codes (e.g., BLS 11-3051 maps to 6 O*NET codes: .00, .01, .02, .03, .04, .06)
- 867 O*NET codes end in .00 (direct BLS mapping), 149 have detailed suffixes

---

## Ingestor Issues Requiring Fixes

### 1. Missing Files (Critical)
`Career Changers Matrix.txt` and `Career Starters Matrix.txt` do not exist in the O*NET 30.2 ZIP. The `OnetCareerChangersIngestor` and `OnetCareerStartersIngestor` will raise `FileNotFoundError`.

**Action:** Remove these ingestors or make them conditional with graceful handling.

### 2. Related Occupations Column Name Mismatch (Critical)
The ingestor reads `raw_row.get("Related Index")` but the actual column is named `Index`. This will cause `related_index` to be None for every row, and every row will be skipped (100% data loss).

**Action:** Change `raw_row.get("Related Index")` to `raw_row.get("Index")` in `OnetRelatedOccupationsIngestor.flatten()`.

### 3. Related Occupations Missing Relatedness Tier (Medium)
The file contains a `Relatedness Tier` column that the ingestor does not capture. This column provides valuable tier information (Primary-Short, Primary-Long, Supplemental) that is more granular than the binary is_primary flag.

**Action:** Consider adding `relatedness_tier` to the schema and capture it during ingestion.

### 4. Work Context Row Count (Low -- Documentation Only)
The spec estimated ~49,000 rows. Actual is 297,676. This is not a bug -- the CXP/CTP percentage-based rows were not accounted for in the estimate. DQ row count rules should use the actual count.

---

## DQ Rule Threshold Recommendations

### raw.onet_occupations
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Row count | 1,016 +/- 5% | Current exact count |
| O*NET-SOC format | 100% match XX-XXXX.XX | 0 invalid in 1,016 |
| Null rate: all fields | 0% | 0 nulls observed |
| Unique O*NET-SOC codes | 100% | 1,016 distinct = 1,016 rows |

### raw.onet_task_statements
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Row count | 18,796 +/- 10% | Rolling updates add/remove tasks |
| O*NET-SOC format | 100% match | 0 invalid in 18,796 |
| Task ID globally unique | 100% | Confirmed unique |
| task_type values | {"Core", "Supplemental", "n/a"} | Only these 3 observed |
| domain_source values | {"Incumbent", "Occupational Expert", "Analyst", "Analyst - Transition"} | Only these 4 observed |
| Incumbents Responding null when domain_source in (Analyst, Analyst - Transition) | Allow nulls | 1,190 nulls = 6.3%, all explained |
| Referential integrity to occupations | 100% | 0 orphans |

### raw.onet_work_activities
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Row count | 73,308 +/- 5% | Very stable: 894 x 41 x 2 |
| Rows per occupation | Exactly 82 | 100% of occupations have 82 |
| IM scale data_value | [1.0, 5.0] | Observed 1.00-4.99 |
| LV scale data_value | [0.0, 7.0] | Observed 0.00-6.81 |
| scale_id values | {"IM", "LV"} | Only these 2 |
| recommend_suppress values | {"N", "Y", "n/a"} | Only these 3 |
| not_relevant values | {"N", "Y", "n/a"} | Only these 3 |
| recommend_suppress = "Y" rate | < 3% | Currently 1.5% |
| Referential integrity to occupations | 100% | 0 orphans |

### raw.onet_work_context
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Row count | 297,676 +/- 5% | Note: 6x the original spec estimate |
| Rows per occupation | 338 or 57 | 878 have 338, 16 have 57 |
| scale_id values | {"CX", "CXP", "CT", "CTP"} | Only these 4 |
| CX data_value | [1.0, 5.0] | Observed range |
| CXP data_value | [0.0, 100.0] | Percentage scale |
| CT data_value | [1.0, 3.0] | Observed range |
| CTP data_value | [0.0, 100.0] | Percentage scale |
| not_relevant | 100% "n/a" | Never used in Work Context |
| recommend_suppress = "Y" rate | < 5% | Currently 2.5% |
| Referential integrity to occupations | 100% | 0 orphans |

### raw.onet_related_occupations
| Rule | Threshold | Evidence |
|------|-----------|----------|
| Row count | 18,460 +/- 5% | Very stable: 923 x 20 |
| Rows per source occupation | Exactly 20 | 100% have 20 |
| Index range | [1, 20] | All values in range |
| Self-references | 0 | None observed |
| O*NET-SOC format (both columns) | 100% match | 0 invalid |
| Referential integrity (both columns) | 100% | 0 orphans |
| Relatedness Tier values | {"Primary-Short", "Primary-Long", "Supplemental"} | Only these 3 |
