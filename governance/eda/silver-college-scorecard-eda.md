## EDA Report: Silver base.college_scorecard
**Source:** raw.college_scorecard (Bronze zone parquet)
**Date:** 2026-04-06
**Agent:** @data-analyst
**Record Count:** 69,947
**Field Count:** 18 (Silver target schema)
**Reference:** governance/eda/raw-college-scorecard-eda.md (Bronze EDA)
**Physical Model:** governance/models/silver-base-college-scorecard-physical.md

---

### Purpose

This Silver EDA profiles the raw.college_scorecard data from the perspective of the Silver transformations defined in the physical model. It focuses on transformation correctness, derived field distributions, and DQ threshold recommendations for the Silver base table.

---

### Critical Findings

1. **CIP code CHECK constraint mismatch (BLOCKING).** The physical model defines `CHECK (cipcode ~ '^\d{2}\.\d{4}$')` expecting XX.XXXX format (7 characters). However, all 69,947 source CIP codes are 4 digits (e.g., "5202"). The transformation `raw[:2] + '.' + raw[2:]` produces XX.XX format (5 characters, e.g., "52.02"), NOT XX.XXXX (e.g., "52.0200"). The CHECK constraint will reject every single row. **The CHECK must be corrected to `^\d{2}\.\d{2}$` or the transformation must zero-pad to 4 digits after the dot.**

2. **CONTROL field missing from parquet (BLOCKING).** The `control` column is defined in the ingestor schema (field 17) but is absent from all existing parquet data files. The 69,947-row file and the 50-row file both lack this column. The raw ingestor must be re-run to populate the CONTROL field before the Silver transformer can produce `institution_control`. This is the blocking issue noted in the physical model (Open Issue #2).

3. **CONTROL field format mismatch.** The physical model derivation rule says `{1: 'Public', 2: 'Private nonprofit', 3: 'Private for-profit'}[int(raw_control)]`, implying CONTROL is an integer. However, the source CSV stores CONTROL as text labels (e.g., "Public", not "1"). The ingestor also treats it as a string field (line 229 of the ingestor). **The derivation expression must be updated** to either: (a) pass through the text value directly if it matches the allowed set, or (b) map text to text (identity transform with validation).

4. **75.5% of programs will be flagged as small cohort.** The `small_cohort_flag` (True when completions_count_1 IS NULL OR < 30) will be True for 52,826 of 69,947 rows (75.52%). Only 17,121 rows (24.48%) will have flag=False. This is a much higher flag rate than might be expected and affects downstream Gold zone filtering.

5. **Earnings suppression independence confirmed at 12.3%.** 8,585 rows (12.27%) have different suppression status between 1yr and 2yr earnings. This means the Silver table will have records where one earnings field is populated and the other is null -- DQ rules must not assume they are jointly null or jointly present.

---

### CIP Code Normalization Analysis

#### Source Format
- All 69,947 CIP codes are exactly 4 characters
- All 69,947 match the regex `^\d{4}$` (pure digits, no dots, no letters)
- 43 distinct CIP codes start with "0" (5,924 rows, 8.47%), requiring leading-zero preservation
- 0 codes contain dots, letters, or non-digit characters

#### Normalization Simulation
The transformation `cipcode[:2] + '.' + cipcode[2:]` produces:
- "0100" -> "01.00" (5 chars, XX.XX)
- "5202" -> "52.02" (5 chars, XX.XX)
- "0301" -> "03.01" (5 chars, XX.XX)

All 69,947 codes will produce valid XX.XX format strings. Zero codes will fail the transformation itself. However, all will fail the physical model CHECK constraint `^\d{2}\.\d{4}$` which expects XX.XXXX (7 chars).

**Recommendation:** Change the CHECK constraint to `^\d{2}\.\d{2}$` to match the actual data granularity. The source data uses 4-digit CIP series codes (2-digit family + 2-digit subfield), not 6-digit detailed codes.

#### Leading-Zero CIP Codes (Transformation Safety)

| CIP Family | Description | Rows | Distinct Codes |
|------------|-------------|------|----------------|
| 01 | Agriculture | 846 | 19 |
| 03 | Natural Resources | 1,084 | 6 |
| 04 | Architecture | 455 | 9 |
| 05 | Area Studies | 951 | 3 |
| 09 | Communication | 2,588 | 6 |

These 5,924 rows (8.47%) depend on the cipcode field being stored as STRING, not integer. If cipcode were ever cast to integer and back, leading zeros would be lost and normalization would fail. The parquet file correctly stores cipcode as VARCHAR.

---

### CIP Family Distribution (After Transformation)

The `cip_family` derived field (first 2 characters of normalized cipcode) produces 45 distinct families.

| CIP Family | Name | Rows | Pct |
|-----------|------|------|-----|
| 52 | Business, Management, Marketing | 8,402 | 12.01% |
| 51 | Health Professions | 5,455 | 7.80% |
| 50 | Visual and Performing Arts | 5,254 | 7.51% |
| 45 | Social Sciences | 5,153 | 7.37% |
| 13 | Education | 3,742 | 5.35% |
| 26 | Biological and Biomedical Sciences | 3,561 | 5.09% |
| 14 | Engineering | 3,200 | 4.57% |
| 11 | Computer and Information Sciences | 2,961 | 4.23% |
| 30 | Multi/Interdisciplinary Studies | 2,838 | 4.06% |
| 40 | Physical Sciences | 2,812 | 4.02% |
| 09 | Communication, Journalism | 2,588 | 3.70% |
| 16 | Foreign Languages | 2,527 | 3.61% |
| 23 | English Language and Literature | 1,998 | 2.86% |
| 42 | Psychology | 1,972 | 2.82% |
| 27 | Mathematics and Statistics | 1,825 | 2.61% |
| 38 | Philosophy and Religious Studies | 1,738 | 2.48% |
| 43 | Homeland Security, Law Enforcement | 1,427 | 2.04% |
| 54 | History | 1,303 | 1.86% |
| 44 | Public Administration | 1,295 | 1.85% |
| 31 | Parks, Recreation, Kinesiology | 1,292 | 1.85% |
| 24 | Liberal Arts, General Studies | 1,280 | 1.83% |
| 39 | Theology and Religious Vocations | 1,144 | 1.64% |
| 03 | Natural Resources and Conservation | 1,084 | 1.55% |
| 15 | Engineering Technologies | 1,003 | 1.43% |
| 05 | Area, Ethnic, Cultural Studies | 951 | 1.36% |
| 01 | Agriculture | 846 | 1.21% |
| 19 | Family and Consumer Sciences | 748 | 1.07% |
| 04 | Architecture | 455 | 0.65% |
| 22 | Legal Professions | 390 | 0.56% |
| 10 | Communications Technologies | 262 | 0.37% |
| 49 | Transportation and Materials Moving | 130 | 0.19% |
| 12 | Culinary, Entertainment, Personal Svc | 75 | 0.11% |
| 41 | Science Technologies | 47 | 0.07% |
| 29 | Military Technologies | 45 | 0.06% |
| 47 | Mechanic and Repair Technologies | 39 | 0.06% |
| 36 | Leisure and Recreational Activities | 33 | 0.05% |
| 46 | Construction Trades | 23 | 0.03% |
| 25 | Library Science | 13 | 0.02% |
| 34 | Health-Related Knowledge and Skills | 10 | 0.01% |
| 48 | Precision Production | 9 | 0.01% |
| 28 | Military Science | 7 | 0.01% |
| 53 | High School/Secondary Programs | 4 | 0.01% |
| 32 | Basic Skills/Remedial Education | 3 | <0.01% |
| 33 | Citizenship Activities | 2 | <0.01% |
| 35 | Interpersonal and Social Skills | 1 | <0.01% |

**All 45 families are valid CIP 2020 two-digit codes.** No unknown or invalid family codes exist.

#### CIP Family Lookup Validation

The Silver transformer must maintain a lookup table mapping 2-digit codes to family names. All 45 families in the data must resolve. Families 32, 33, 34, 35, 36, and 53 are unusual at the bachelor's degree level (combined: 52 rows, 0.07%) and represent edge cases in the CIP taxonomy. The lookup table must include these.

---

### institution_control Analysis

#### Current State
- **CONTROL column is NOT in the Bronze parquet.** The ingestor schema defines it (field 17, StringType) but the parquet files were written before the schema was updated to include it.
- **The CSV sample** (50 rows) has CONTROL = "Public" for all rows. This is text, not integer.
- **The source CSV** (from the College Scorecard) stores CONTROL as a text label in column 4.
- **The physical model derivation rule** assumes integer input: `{1: 'Public', 2: 'Private nonprofit', 3: 'Private for-profit'}[int(raw_control)]`. This will fail because the source values are already text.

#### What We Know
The College Scorecard Field-of-Study CSV uses text labels for CONTROL. The 50-row test sample only contains "Public" institutions. Based on the College Scorecard data dictionary, the expected values are:
- "Public"
- "Private nonprofit"
- "Private for-profit"

#### CONTROL Distribution Estimate (Cannot Confirm)
The full source CSV is not available locally (source URL returns 404). CONTROL distribution cannot be profiled from the 50-row sample. Based on IPEDS data for bachelor's-granting institutions nationally, the approximate expected distribution is:
- Public: ~35-40% of institutions, ~50-60% of programs (larger institutions)
- Private nonprofit: ~45-50% of institutions, ~30-40% of programs
- Private for-profit: ~10-15% of institutions, ~5-15% of programs

**This estimate must be validated** after the raw ingestor is re-run with the CONTROL field included.

#### Recommendations
1. Re-run the raw ingestor to include CONTROL in the parquet (blocking for Silver transformer)
2. Update the derivation rule to handle text values: validate against allowed set `{'Public', 'Private nonprofit', 'Private for-profit'}` rather than mapping from integers
3. After re-ingestion, run a targeted EDA on the CONTROL field to get the actual distribution for DQ thresholds

---

### small_cohort_flag Distribution

The flag is derived as: `completions_count_1 IS NULL OR completions_count_1 < 30`

| Bucket | Rows | Pct | Flag Value |
|--------|------|-----|------------|
| NULL completions | 6,098 | 8.72% | True |
| completions = 0 | 8,685 | 12.42% | True |
| completions 1-9 | 21,497 | 30.73% | True |
| completions 10-19 | 10,666 | 15.25% | True |
| completions 20-29 | 5,880 | 8.41% | True |
| completions 30-49 | 6,200 | 8.86% | False |
| completions 50-99 | 5,872 | 8.39% | False |
| completions 100-499 | 4,790 | 6.85% | False |
| completions 500+ | 259 | 0.37% | False |

**Summary:**
- **small_cohort_flag = True: 52,826 rows (75.52%)**
- **small_cohort_flag = False: 17,121 rows (24.48%)**

#### Flagged Programs with Earnings Data (Edge Case)
14,929 flagged programs (28.3% of flagged) still have at least one earnings value. This is expected -- privacy suppression is not absolute at the 30-completer boundary. The flag indicates elevated risk of suppression, not guaranteed suppression.

#### Earnings Availability by Flag

| Flag | Total | Has 1yr Earn | Pct | Has 2yr Earn | Pct |
|------|-------|-------------|-----|-------------|-----|
| True (flagged) | 52,826 | 10,003 | 18.94% | 12,826 | 24.28% |
| False (not flagged) | 17,121 | 15,193 | 88.74% | 14,855 | 86.76% |

The flag is highly predictive: unflagged programs have ~88% earnings availability vs ~19-24% for flagged programs.

---

### Earnings Suppression Patterns

#### Cross-Tabulation: 1yr vs 2yr Earnings Suppression

| 1yr Status | 2yr Status | Rows | Pct |
|-----------|-----------|------|-----|
| null | null | 39,216 | 56.07% |
| null | present | 5,535 | 7.91% |
| present | null | 3,050 | 4.36% |
| present | present | 22,146 | 31.66% |

**12.27% of rows (8,585) have different suppression status** between the two earnings fields. This means:
- 5,535 rows have 2yr earnings but NOT 1yr earnings
- 3,050 rows have 1yr earnings but NOT 2yr earnings

DQ rules must NOT assume joint nullity. Each earnings field should be validated independently.

#### Debt vs Earnings Cross-Suppression

| Earnings Status | Debt Status | Rows | Pct |
|----------------|------------|------|-----|
| has earnings | has debt | 23,487 | 33.58% |
| has earnings | no debt | 7,244 | 10.36% |
| no earnings | has debt | 2,322 | 3.32% |
| no earnings | no debt | 36,894 | 52.75% |

2,322 rows (3.32%) have debt data but no earnings data. 7,244 rows (10.36%) have earnings but no debt. Suppression is NOT uniform across all outcome fields.

---

### Completions Count Cross-Nullity

| ipedscount1 | ipedscount2 | Rows |
|------------|------------|------|
| null | null | 4,186 |
| null | present | 1,912 |
| present | null | 1,587 |
| present | present | 62,262 |

1,912 rows have ipedscount2 but not ipedscount1. The `small_cohort_flag` is derived solely from ipedscount1, so these rows will be flagged True (conservative default) even though ipedscount2 is available.

---

### Range Validation Against Silver CHECK Constraints

All non-null values in the source data pass the Silver physical model CHECK constraints:

| Constraint | Violations | Status |
|-----------|-----------|--------|
| `earnings_1yr_median >= 1000 AND <= 250000` | 0 | PASS |
| `earnings_2yr_median >= 1000 AND <= 250000` | 0 | PASS |
| `debt_median >= 1000 AND <= 100000` | 0 | PASS |
| `completions_count_1 >= 0` | 0 | PASS |
| `completions_count_2 >= 0` | 0 | PASS |
| `credential_level BETWEEN 1 AND 8` | 0 | PASS (all = 3) |
| Grain uniqueness (unitid x cipcode x credlev) | 0 duplicates | PASS |

---

### Required Field Null/Empty Check

All fields that map to NOT NULL Silver columns have zero null/empty values:

| Source Field | Silver Column | Null Count | Empty Count |
|-------------|--------------|-----------|-------------|
| unitid | unitid | 0 | n/a (integer) |
| instnm | institution_name | 0 | 0 |
| cipcode | cipcode | 0 | 0 |
| cipdesc | program_name | 0 | 0 |
| creddesc | credential_description | 0 | 0 |
| credlev | credential_level | 0 | n/a (integer) |
| load_date | source_load_date | 0 | n/a (date) |

No rows will be rejected due to null required fields during Silver transformation.

---

### Silver-Specific Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation for @dq-rule-writer |
|-------------|-------|------------|-------------------------------------|
| CIP CHECK constraint mismatch | 69,947 | 100% | **BLOCKING:** Fix CHECK to `^\d{2}\.\d{2}$` before writing cipcode format rule |
| CONTROL column missing from parquet | 69,947 | 100% | **BLOCKING:** Cannot validate institution_control until re-ingestion |
| CONTROL derivation rule assumes integers | n/a | n/a | Update rule to handle text values from source CSV |
| small_cohort_flag = True | 52,826 | 75.52% | Set expected True rate at 70-80%. Alert if outside this range. |
| Flagged programs with earnings | 14,929 | 21.3% of total | Normal -- flag indicates risk, not guaranteed suppression |
| 1yr/2yr suppression differs | 8,585 | 12.27% | Do NOT write joint-nullity rules. Validate each field independently. |
| Rows with debt but no earnings | 2,322 | 3.32% | Valid pattern -- suppression is per-field, not per-row |
| ipedscount1 null but ipedscount2 present | 1,912 | 2.73% | These will be flagged True (conservative). Document this edge case. |
| CIP families 32,33,34,35,36,53 at bachelor level | 52 | 0.07% | Unusual but valid. Ensure CIP family lookup includes these. |

---

### DQ Threshold Recommendations for Silver Base Table

#### Row Count Rules

| Rule | Threshold | Evidence |
|------|-----------|----------|
| Total row count | 60,000 - 80,000 | Source: 69,947. Carried from Bronze EDA. |
| Distinct institutions | 2,200 - 3,000 | Source: 2,559. Carried from Bronze EDA. |
| Distinct CIP codes | 350 - 450 | Source: 390. Carried from Bronze EDA. |
| Distinct CIP families | 40 - 50 | Source: 45. Stable (CIP taxonomy). |
| Grain uniqueness | 0 duplicates | Source: 0. Hard constraint. |

#### Completeness Rules (Silver Column Names)

| Column | Max Null Rate | Evidence |
|--------|---------------|----------|
| record_id | 0% | Derived, always generated. |
| unitid | 0% | Source: 0%. |
| institution_name | 0% | Source: 0%. |
| institution_control | 0% | Cannot validate yet -- CONTROL not in parquet. |
| cipcode | 0% | Source: 0%. |
| program_name | 0% | Source: 0%. |
| cip_family | 0% | Derived from cipcode, which is 0% null. |
| cip_family_name | 0% | Derived via lookup, all 45 families must resolve. |
| credential_level | 0% | Source: 0%. |
| credential_description | 0% | Source: 0%. |
| earnings_1yr_median | 70% | Source: 64.0% null. Allow headroom for variation. |
| earnings_2yr_median | 65% | Source: 60.4% null. |
| debt_median | 68% | Source: 63.1% null. |
| completions_count_1 | 12% | Source: 8.7% null. |
| completions_count_2 | 12% | Source: 8.3% null. |
| small_cohort_flag | 0% | Derived, always generated. |
| source_load_date | 0% | Source: 0%. |
| ingested_at | 0% | Generated at transformation time. |

#### Value Range Rules

| Column | Min | Max | Evidence |
|--------|-----|-----|----------|
| credential_level | 3 | 3 | Must be exactly 3 (bachelor's filter). Hard constraint. |
| earnings_1yr_median | $1,000 | $250,000 | Source range: $4,880 - $161,723. 0 violations. |
| earnings_2yr_median | $1,000 | $250,000 | Source range: $5,938 - $160,116. 0 violations. |
| debt_median | $1,000 | $100,000 | Source range: $2,750 - $57,500. 0 violations. |
| completions_count_1 | 0 | 15,000 | Source range: 0 - 7,888. 0 negative values. |
| completions_count_2 | 0 | 15,000 | Source range: 0 - 8,124. 0 negative values. |
| unitid | 100,000 | 999,999 | Source range: 100,654 - 497,268. |

#### Format Rules

| Column | Pattern | Evidence |
|--------|---------|----------|
| cipcode | `^\d{2}\.\d{2}$` | **CORRECTED from physical model.** All 69,947 codes will normalize to XX.XX (5 chars). |
| cip_family | `^\d{2}$` | Derived from cipcode[:2]. All values are 2-digit strings. |
| record_id | `^cs-[0-9a-f]{16}$` | Deterministic SHA-256 hash with prefix. |
| institution_control | IN ('Public', 'Private nonprofit', 'Private for-profit') | Per physical model CHECK constraint. Cannot validate distribution yet. |
| credential_description | Exact: "Bachelor's Degree" | Single value in source. |

#### Derived Field Accuracy Rules

| Rule | Expression | Expected |
|------|-----------|----------|
| small_cohort_flag accuracy | flag = (completions_count_1 IS NULL OR completions_count_1 < 30) | 100% match. No exceptions. |
| cip_family derivation | cip_family = cipcode[:2] | 100% match. |
| small_cohort_flag True rate | SUM(flag) / COUNT(*) | 70-80% (current: 75.52%) |

#### Statistical Rules (Warn, Not Reject)

| Column | Rule | Threshold | Evidence |
|--------|------|-----------|----------|
| earnings_1yr_median | Mean range | $30,000 - $50,000 | Current mean: $39,616. |
| earnings_2yr_median | Mean range | $30,000 - $50,000 | Current mean: $39,596. |
| debt_median | Mean range | $18,000 - $28,000 | Current mean: $22,869. |
| completions_count_1 | Zero-value rate | < 18% of non-null | Current: 13.6%. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| cipcode (physical model) | Schema mismatch | 69,947 (100%) | CRITICAL | CHECK `^\d{2}\.\d{4}$` will reject all rows. Must be `^\d{2}\.\d{2}$`. |
| control (parquet) | Missing column | 69,947 (100%) | CRITICAL | CONTROL not in parquet. Blocks institution_control derivation. |
| control (derivation) | Logic error | n/a | HIGH | Derivation assumes integer source, but source CSV has text labels. |
| small_cohort_flag | High flag rate | 52,826 (75.5%) | INFO | Expected behavior given the 30-completer threshold. Not an error. |
| earnings suppression | Independent | 8,585 (12.3%) | INFO | 1yr and 2yr earnings are independently suppressed. Expected. |

---

### Recommendations for Downstream Agents

**For @dq-rule-writer:**
- The CIP code CHECK constraint in the physical model is wrong. Coordinate with @semantic-modeler to fix before writing cipcode format rules. Use `^\d{2}\.\d{2}$` as the pattern.
- Write small_cohort_flag accuracy rules: verify that every row with flag=True has completions_count_1 IS NULL OR < 30, and vice versa.
- Write cip_family referential integrity rules: all 45 observed families must be in the CIP 2020 lookup table.
- Do NOT write institution_control rules until the CONTROL field is re-ingested and profiled.
- Earnings null-rate thresholds should apply independently to each field (1yr, 2yr, debt). Do not assume joint behavior.

**For @primary-agent (transformer implementer):**
- The transformation `cipcode[:2] + '.' + cipcode[2:]` is correct and will succeed for all 69,947 rows.
- Leading zeros are preserved in the source (cipcode is VARCHAR). Do not cast to integer.
- The CONTROL derivation must handle text values, not integers. Validate against `{'Public', 'Private nonprofit', 'Private for-profit'}`.
- The CIP family lookup must include all 45 families, including unusual ones (32, 33, 34, 35, 36, 53).
- The small_cohort_flag will be True for 75.5% of rows. This is correct, not a bug.

**For @semantic-modeler:**
- Fix the cipcode CHECK constraint: `^\d{2}\.\d{4}$` -> `^\d{2}\.\d{2}$`
- Fix the institution_control derivation rule: source is text, not integer
- Consider whether the CIP family CHECK `^\d{2}$` needs an additional referential integrity constraint (e.g., must be in a known set of 45 families)

---

### Audit Trail

- **Dataset analyzed:** raw.college_scorecard (Bronze parquet, 69,947 rows, 16 columns)
- **Additional source:** tests/raw/college_scorecard_sample.csv (50 rows, includes CONTROL column)
- **Additional source:** tests/raw/college_scorecard_columns.txt (full source CSV column listing)
- **Additional source:** src/raw/college_scorecard_ingestor.py (CONTROL field handling verification)
- **Analysis purpose:** Silver zone EDA per spec docs/specs/silver-base-college-scorecard.md, step 6 of agent workflow
- **Key findings:** CIP CHECK constraint mismatch (CRITICAL), CONTROL missing from parquet (CRITICAL), CONTROL derivation assumes integers (HIGH), small_cohort_flag at 75.5% True rate (INFO)
- **Domain discovery:** Not applicable (domain established in Bronze EDA)
- **Threshold recommendations:** 18 specific thresholds with supporting evidence for @dq-rule-writer
- **Timestamp:** 2026-04-06
- **Spec reference:** docs/specs/silver-base-college-scorecard.md
