## EDA Report: raw.college_scorecard
**Source:** U.S. Department of Education College Scorecard — Most Recent Cohorts Field-of-Study  
**Date:** 2026-04-05  
**Agent:** @data-analyst  
**Record Count:** 69,947  
**Field Count:** 16  

---

### Domain Context

**Identified Domain:** U.S. higher education — program-level career outcomes and student debt  
**Primary Entities:** Institution-program combinations (a specific bachelor's degree program at a specific institution)  
**Grain:** One row per `unitid` x `cipcode` x `credlev` (all `credlev=3`, so effectively `unitid` x `cipcode`)  
**Temporal Pattern:** Snapshot — single load on 2026-04-06, all rows share the same `ingested_at` timestamp  
**Domain Vocabulary:**
- **UNITID** — IPEDS institution identifier (6-digit integer)
- **CIPCODE** — Classification of Instructional Programs code (normally XX.XXXX format; ingested as 4-digit without dot separator)
- **CREDLEV** — Credential level (3 = Bachelor's Degree)
- **CREDDESC** — Human-readable credential description
- **CIPDESC** — Human-readable CIP program description
- **INSTNM** — Institution name
- **MD_EARN_WNE** — Median earnings of graduates working and not enrolled (field-level)
- **EARN_MDN_HI_1YR** — Median earnings, high estimate, 1 year after completion
- **EARN_MDN_HI_2YR** — Median earnings, high estimate, 2 years after completion
- **DEBT_ALL_STGP_EVAL_MDN** — Median debt at separation, all student groups evaluated
- **IPEDSCOUNT1** — IPEDS completions count (first measurement)
- **IPEDSCOUNT2** — IPEDS completions count (second measurement)
- **Privacy Suppression** — Values suppressed by the Department of Education when cohort sizes are too small to protect student privacy; these appear as null in the ingested data

**Taxonomy/Codes Found:**
- CIP code taxonomy (Classification of Instructional Programs) — 390 distinct codes observed, organized in 2-digit families
- CREDLEV integer code system (only level 3 present after ingestor filtering)
- UNITID integer identifiers (IPEDS institutional IDs)

---

### Key Findings

- **md_earn_wne is 100% null.** Every single row has a null value for this field. This is the most critical finding — either the source column was entirely privacy-suppressed for this cohort, the source CSV column name has changed, or there is an ingestor bug mapping the wrong column. This requires investigation before silver zone processing.
- **CIP codes are missing the dot separator.** All 69,947 CIP codes are 4-character strings (e.g., "5202" instead of "52.02"). The source CSV likely stores them without the dot, or the dot was stripped during ingestion. This is a format discrepancy versus the standard XX.XXXX CIP code format.
- **High null rates on earnings and debt fields are expected** due to Department of Education privacy suppression. Programs with small cohorts (ipedscount1 < 30) rarely have earnings data (6.8-10.7% availability), while larger programs (ipedscount1 >= 30) have 88.7% availability.
- **No duplicate grains exist.** All 69,947 rows have unique `unitid` x `cipcode` x `credlev` combinations.
- **44.2% of rows where both earnings fields are present show 2-year earnings below 1-year earnings.** This is not necessarily an anomaly — these are "high estimate" median values from different cohort windows, not longitudinal tracking of the same individuals.
- **12.4% of rows have zero completions** (ipedscount1 = 0 for 8,685 rows). These represent programs that existed but had no IPEDS-reported completions in the measurement window. Some of these still have earnings data (10.7%), likely from prior-year completers.
- **10 institution names map to multiple UNITIDs** (e.g., Stevens-Henager College has 6 campuses). This is expected for multi-campus systems.
- **2,534 distinct institution names vs. 2,559 distinct UNITIDs** — 25 UNITIDs share names with other institutions (different campuses or branches).

---

### Field Profiles

#### unitid
- **Type:** LONG (integer)
- **Null Rate:** 0.000% (0 of 69,947 rows) — required grain field
- **Cardinality:** 2,559 distinct values (3.66% uniqueness)
- **Distribution:** Min=100,654, Max=497,268, Mean=195,216
- **Patterns:** 6-digit IPEDS institutional identifiers. All values are positive integers.
- **Outliers:** None — all values fall within expected IPEDS ID range.

#### instnm
- **Type:** STRING
- **Null Rate:** 0.000% (0 of 69,947 rows)
- **Cardinality:** 2,534 distinct values
- **Note:** 2,534 names for 2,559 UNITIDs. No UNITID maps to multiple names. 10 names map to multiple UNITIDs (multi-campus institutions: Stevens-Henager College=6, Bethel University=3, Lincoln University=3, Bethany College=2, St. John's College=2).

#### cipcode
- **Type:** STRING
- **Null Rate:** 0.000% (0 of 69,947 rows) — required grain field
- **Cardinality:** 390 distinct values (0.56% uniqueness)
- **Distribution:** Top 5 by frequency: 5202 (Business Admin, 1,701), 4201 (Psychology, 1,438), 2601 (Biology, 1,411), 2301 (English, 1,334), 5401 (History, 1,303)
- **Patterns:** All values are exactly 4 characters long. Format is NNNN (digits only, no dot separator). The standard CIP code format is XX.XXXX — the dot is absent in all records. Leading zeros are preserved (e.g., "0100", "0501").
- **CIP 2-digit families (top 5):** 52-Business (8,402), 51-Health (5,455), 50-Visual/Performing Arts (5,254), 45-Social Sciences (5,153), 13-Education (3,742)

#### cipdesc
- **Type:** STRING
- **Null Rate:** 0.000% (0 of 69,947 rows)
- **Cardinality:** 390 distinct values (1:1 with cipcode)
- **Patterns:** Human-readable program descriptions, ending with a period.

#### creddesc
- **Type:** STRING
- **Null Rate:** 0.000% (0 of 69,947 rows)
- **Cardinality:** 1 distinct value
- **Distribution:** "Bachelor's Degree" = 69,947 (100%). Consistent with credlev=3 filter.

#### credlev
- **Type:** INTEGER
- **Null Rate:** 0.000% (0 of 69,947 rows) — required grain field
- **Cardinality:** 1 distinct value
- **Distribution:** 3 = 69,947 (100%). Confirmed: ingestor CREDLEV=3 filter is working correctly.

#### md_earn_wne
- **Type:** DOUBLE
- **Null Rate:** 100.000% (69,947 of 69,947 rows)
- **CRITICAL:** This field is entirely null. No non-null values exist. Possible causes: (a) the source CSV column name differs from "MD_EARN_WNE" for the field-of-study file (this metric may only be populated in the institution-level file), (b) the entire column was privacy-suppressed in this release, or (c) the column was renamed in the most recent data refresh. Recommend investigating the source CSV headers before writing any DQ rules for this field.

#### earn_mdn_hi_1yr
- **Type:** DOUBLE
- **Null Rate:** 63.978% (44,751 of 69,947 rows)
- **Cardinality:** 3,942 distinct values among non-null rows
- **Distribution (non-null, N=25,196):**

| Statistic | Value |
|-----------|-------|
| Min | $4,880 |
| P10 | $24,318 |
| P25 | $29,040 |
| Median | $35,812 |
| P75 | $47,252 |
| P90 | $62,406 |
| Max | $161,723 |
| Mean | $39,616 |
| StdDev | $14,894 |

- **Histogram:**

| Bucket | Count | Pct of Non-Null |
|--------|-------|-----------------|
| <$20k | 764 | 3.0% |
| $20-30k | 6,456 | 25.6% |
| $30-40k | 8,449 | 33.5% |
| $40-50k | 4,099 | 16.3% |
| $50-60k | 2,299 | 9.1% |
| $60-80k | 2,860 | 11.4% |
| $80-100k | 207 | 0.8% |
| $100-150k | 61 | 0.2% |
| $150k+ | 1 | <0.1% |

- **Outliers (3-sigma, above $84,299):** 186 rows (0.74% of non-null). These represent high-earning professional programs (CS, engineering, nursing at elite institutions).
- **Low-end outliers (<$10,000):** 14 rows. Examples: Bloomsburg U Communication Disorders ($4,880), Daemen U Natural Sciences ($5,783). These may represent programs where most graduates continue to graduate school (low earnings because not yet in workforce).

#### earn_mdn_hi_2yr
- **Type:** DOUBLE
- **Null Rate:** 60.426% (42,266 of 69,947 rows)
- **Cardinality:** 4,205 distinct values among non-null rows
- **Distribution (non-null, N=27,681):**

| Statistic | Value |
|-----------|-------|
| Min | $5,938 |
| P10 | $24,532 |
| P25 | $29,511 |
| Median | $35,810 |
| P75 | $46,869 |
| P90 | $61,728 |
| Max | $160,116 |
| Mean | $39,596 |
| StdDev | $14,798 |

- **Outliers (3-sigma, above $83,989):** 232 rows (0.84% of non-null).
- **Top outliers:** Carnegie Mellon CS ($160,116), Caltech CS ($155,297), Brown CS ($153,718).
- **Notable:** 2yr distribution is nearly identical to 1yr. The 2yr field has 2,485 more non-null values.

#### debt_all_stgp_eval_mdn
- **Type:** DOUBLE
- **Null Rate:** 63.102% (44,138 of 69,947 rows)
- **Cardinality:** 2,121 distinct values among non-null rows
- **Distribution (non-null, N=25,809):**

| Statistic | Value |
|-----------|-------|
| Min | $2,750 |
| P10 | $16,029 |
| P25 | $19,500 |
| Median | $23,000 |
| P75 | $26,000 |
| P90 | $27,000 |
| Max | $57,500 |
| Mean | $22,869 |
| StdDev | $5,617 |

- **Histogram:**

| Bucket | Count | Pct of Non-Null |
|--------|-------|-----------------|
| <$10k | 237 | 0.9% |
| $10-15k | 1,493 | 5.8% |
| $15-20k | 5,397 | 20.9% |
| $20-25k | 9,224 | 35.7% |
| $25-30k | 7,980 | 30.9% |
| $30-40k | 995 | 3.9% |
| $40-50k | 461 | 1.8% |
| $50k+ | 22 | 0.1% |

- **Outliers (3-sigma, above $39,720):** 555 rows (2.15% of non-null). Many are for-profit institutions (Purdue University Global, DeVry branches, Keiser University).
- **High debt cluster:** 22 rows exceed $50,000. The max ($57,500) is Purdue University Global teacher education.

#### ipedscount1
- **Type:** LONG (integer)
- **Null Rate:** 8.718% (6,098 of 69,947 rows)
- **Cardinality:** 596 distinct values among non-null rows
- **Distribution (non-null, N=63,849):**

| Statistic | Value |
|-----------|-------|
| Min | 0 |
| P10 | 0 |
| P25 | 3 |
| Median | 11 |
| P75 | 32 |
| P90 | 81 |
| Max | 7,888 |
| Mean | 33.73 |
| StdDev | 88.63 |

- **Zero values:** 8,685 rows (13.6% of non-null). Programs with zero completions in the measurement window.
- **High outliers (>1,000):** 46 rows. Top: Chamberlain University Nursing (7,888), University of Phoenix Business Admin (5,615), Grand Canyon University Nursing (4,638).
- **Right-skewed distribution:** Mean (33.73) far exceeds median (11), indicating heavy right tail from large online/for-profit institutions.

#### ipedscount2
- **Type:** LONG (integer)
- **Null Rate:** 8.253% (5,773 of 69,947 rows)
- **Cardinality:** 613 distinct values among non-null rows
- **Distribution (non-null, N=64,174):**

| Statistic | Value |
|-----------|-------|
| Min | 0 |
| P10 | 0 |
| P25 | 3 |
| Median | 10 |
| P75 | 32 |
| P90 | 82 |
| Max | 8,124 |
| Mean | 33.98 |
| StdDev | 92.95 |

- **Zero values:** 8,654 rows (13.5% of non-null).
- **Correlation with ipedscount1:** 0.9840 (very high). 25,256 rows have ipedscount2 > ipedscount1; 10,149 rows have them equal.

#### ingested_at
- **Type:** TIMESTAMP
- **Null Rate:** 0.000%
- **Cardinality:** 1 distinct value: 2026-04-06 02:34:20.757243
- **Pattern:** Single-batch load. All rows ingested simultaneously.

#### source_url
- **Type:** STRING
- **Null Rate:** 0.000%
- **Cardinality:** 1 distinct value: `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Field-of-Study.csv`

#### source_method
- **Type:** STRING
- **Null Rate:** 0.000%
- **Cardinality:** 1 distinct value: `bulk_csv_download`

#### load_date
- **Type:** DATE
- **Null Rate:** 0.000%
- **Cardinality:** 1 distinct value: 2026-04-06

---

### Cross-Field Analysis

#### Earnings Field Nullity Correlation

| Pattern | Count | Percentage |
|---------|-------|------------|
| All 3 outcome fields null (1yr, 2yr, debt) | 36,894 | 52.7% |
| All 3 outcome fields present | 19,651 | 28.1% |
| 1yr present but 2yr null | 3,050 | 4.4% |
| 2yr present but 1yr null | 5,535 | 7.9% |

Outcome field nullity is strongly correlated — when one field is null, others tend to be null as well. This is consistent with Department of Education privacy suppression being applied uniformly to small-cohort programs.

#### Completions Count Drives Earnings Availability

| ipedscount1 Bucket | Total Rows | Has earn_mdn_hi_1yr | Availability Rate |
|--------------------|------------|---------------------|-------------------|
| null | 6,098 | 597 | 9.8% |
| 0 | 8,685 | 930 | 10.7% |
| 1-9 | 21,497 | 1,468 | 6.8% |
| 10-29 | 16,546 | 7,008 | 42.4% |
| 30+ | 17,121 | 15,193 | 88.7% |

Privacy suppression threshold appears to be approximately N=30: programs with 30+ completions have 88.7% earnings availability, while programs with fewer than 10 completions have under 11%. This is consistent with Department of Education disclosure rules.

#### 1-Year vs 2-Year Earnings

- Pearson correlation: 0.9361 (very strong positive)
- 44.2% of rows with both values have 2yr < 1yr earnings. This is not an error — these are "high estimate" medians from different cohort measurement windows, not the same individuals tracked over time.

#### Institution Name to UNITID Mapping

- Each UNITID maps to exactly one institution name (no inconsistencies).
- 10 institution names map to multiple UNITIDs, representing multi-campus systems. This is expected and correct.

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| md_earn_wne entirely null | 69,947 | 100.0% | Investigate source. Do NOT write completeness rules for this field until root cause is determined. |
| earn_mdn_hi_1yr null | 44,751 | 64.0% | Set null threshold at 70% (allow for privacy suppression). Alert if > 70%. |
| earn_mdn_hi_2yr null | 42,266 | 60.4% | Set null threshold at 65%. Alert if > 65%. |
| debt_all_stgp_eval_mdn null | 44,138 | 63.1% | Set null threshold at 68%. Alert if > 68%. |
| ipedscount1 null | 6,098 | 8.7% | Set null threshold at 12%. Alert if > 12%. |
| ipedscount2 null | 5,773 | 8.3% | Set null threshold at 12%. Alert if > 12%. |
| ipedscount1 = 0 | 8,685 | 12.4% | Valid but noteworthy. Flag for downstream awareness. |
| earn_mdn_hi_1yr < $10k | 14 | 0.06% of non-null | Suspect values — likely grad-school-bound programs. Flag but do not reject. |
| earn_mdn_hi_1yr > $100k | 62 | 0.25% of non-null | Valid elite-program outliers. Do not reject. |
| debt > $50k | 22 | 0.09% of non-null | Valid but extreme. Mostly for-profit institutions. Flag for review. |
| CIP code missing dot separator | 69,947 | 100.0% | All codes are 4-char NNNN format vs. standard XX.XXXX. Silver zone transform needed. |
| Duplicate grains | 0 | 0.0% | No duplicates. Set uniqueness constraint on unitid x cipcode x credlev. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| md_earn_wne | Completeness | 69,947 (100%) | CRITICAL | Entirely null. Field may not exist in field-of-study source file, or column name mismatch in ingestor. Must investigate before silver zone. |
| cipcode | Format | 69,947 (100%) | MEDIUM | All CIP codes use 4-digit format (e.g., "5202") instead of standard "XX.XXXX" format (e.g., "52.02"). Consistent across all rows — likely source format, not ingestor bug. Needs transformation in silver zone. |
| earn_mdn_hi_1yr | Low values | 14 | LOW | Values below $10,000. Lowest: $4,880 (Bloomsburg U, Communication Disorders). Likely programs where graduates predominantly pursue graduate school. |
| debt_all_stgp_eval_mdn | High values | 22 | LOW | Values above $50,000. Concentrated at for-profit institutions (Purdue Global, DeVry branches). Valid but extreme. |
| ipedscount1 | High values | 46 | LOW | Values above 1,000. Large online/for-profit programs (Chamberlain Nursing=7,888, U of Phoenix Business=5,615). Valid. |
| instnm | Ambiguity | 10 names | LOW | 10 institution names shared across multiple UNITIDs (multi-campus systems). Expected behavior. |

---

### DQ Threshold Recommendations

The following thresholds are evidence-based recommendations for @dq-rule-writer. Each threshold is derived from observed distributions with headroom for normal variation across data refreshes.

#### Row Count Rules

| Rule | Threshold | Evidence |
|------|-----------|----------|
| Total row count | 60,000 - 80,000 | Current: 69,947. Allow ~15% variation for annual data changes. |
| Distinct institutions | 2,200 - 3,000 | Current: 2,559. Institutional closures/openings cause slow drift. |
| Distinct CIP codes | 350 - 450 | Current: 390. CIP taxonomy is stable, minor additions/removals. |
| Grain uniqueness | 0 duplicates | Current: 0. Any duplicate is an ingestor bug. |

#### Completeness Rules

| Field | Max Null Rate | Evidence |
|-------|---------------|----------|
| unitid | 0% | Required grain field. Current: 0%. |
| instnm | 0% | Current: 0%. Every institution has a name. |
| cipcode | 0% | Required grain field. Current: 0%. |
| cipdesc | 0% | Current: 0%. 1:1 with cipcode. |
| creddesc | 0% | Current: 0%. Single value "Bachelor's Degree". |
| credlev | 0% | Required grain field. Current: 0%. |
| md_earn_wne | DO NOT RULE | Current: 100% null. Investigate first. |
| earn_mdn_hi_1yr | 70% | Current: 64.0%. Privacy suppression expected. |
| earn_mdn_hi_2yr | 65% | Current: 60.4%. Slightly lower null rate than 1yr. |
| debt_all_stgp_eval_mdn | 68% | Current: 63.1%. Privacy suppression expected. |
| ipedscount1 | 12% | Current: 8.7%. |
| ipedscount2 | 12% | Current: 8.3%. |
| ingested_at | 0% | Metadata field, always populated by framework. |
| source_url | 0% | Metadata field, always populated by framework. |
| source_method | 0% | Metadata field, always populated by framework. |
| load_date | 0% | Metadata field, always populated by framework. |

#### Value Range Rules

| Field | Min | Max | Evidence |
|-------|-----|-----|----------|
| credlev | 3 | 3 | Must be exactly 3 (bachelor's only filter). |
| earn_mdn_hi_1yr | $1,000 | $250,000 | Observed: $4,880 - $161,723. Allow headroom for extreme values. |
| earn_mdn_hi_2yr | $1,000 | $250,000 | Observed: $5,938 - $160,116. |
| debt_all_stgp_eval_mdn | $1,000 | $100,000 | Observed: $2,750 - $57,500. Allow headroom above max. |
| ipedscount1 | 0 | 15,000 | Observed: 0 - 7,888. Allow 2x headroom for growing programs. |
| ipedscount2 | 0 | 15,000 | Observed: 0 - 8,124. |
| unitid | 100,000 | 999,999 | IPEDS IDs are 6-digit. Observed: 100,654 - 497,268. |

#### Format Rules

| Field | Pattern | Evidence |
|-------|---------|----------|
| cipcode | `^\d{4}$` (4-digit numeric string) | All 69,947 values are exactly 4 digits. NOTE: Standard CIP format is XX.XXXX — silver zone should transform. |
| creddesc | Exact match: "Bachelor's Degree" | Single value across all rows. |
| source_method | Exact match: "bulk_csv_download" | Single value across all rows. |

#### Statistical Rules (Warn, Not Reject)

| Field | Rule | Threshold | Evidence |
|-------|------|-----------|----------|
| earn_mdn_hi_1yr | Mean range | $30,000 - $50,000 | Current mean: $39,616. Alert if batch mean drifts significantly. |
| earn_mdn_hi_1yr | 3-sigma outlier rate | < 2% | Current: 0.74%. |
| debt_all_stgp_eval_mdn | Mean range | $18,000 - $28,000 | Current mean: $22,869. |
| debt_all_stgp_eval_mdn | 3-sigma outlier rate | < 4% | Current: 2.15%. Higher due to for-profit institution cluster. |
| ipedscount1 | Zero-value rate | < 18% | Current: 13.6% of non-null. |

---

### Recommendations for Downstream Agents

**For @dq-rule-writer:**
- Do NOT create completeness or range rules for `md_earn_wne` until the 100% null issue is investigated and resolved.
- Privacy suppression is the dominant source of nulls in earnings/debt fields. Rules should allow 60-70% null rates.
- The `credlev = 3` check is a hard constraint and should be enforced as a rejection rule.
- Grain uniqueness (`unitid` x `cipcode` x `credlev`) should be enforced as a rejection rule.

**For @semantic-modeler:**
- CIP codes need a dot inserted at position 2 during silver zone transformation (e.g., "5202" -> "52.02") to conform to standard CIP taxonomy format.
- `md_earn_wne` needs investigation before including in the logical model. It may need to be dropped or sourced from a different file.
- `creddesc` and `credlev` are redundant (1:1 mapping). Consider whether both are needed in the silver model.
- `ipedscount1` and `ipedscount2` are highly correlated (r=0.984) but represent different measurement windows. Both should be retained.

**For @data-steward:**
- The domain vocabulary section above catalogs all field-specific terminology for the glossary.
- Privacy suppression is a key concept: the Department of Education suppresses outcome data when program cohort sizes are too small (roughly < 30 completers) to protect student privacy.
- CIP taxonomy reference: https://nces.ed.gov/ipeds/cipcode/
