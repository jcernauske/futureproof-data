## EDA Report: CIP-SOC Crosswalk (CIP2020 x SOC2018)
**Source:** NCES CIP 2020 to SOC 2018 Crosswalk (`CIP2020_SOC2018_Crosswalk.xlsx`)
**Date:** 2026-04-08
**Agent:** @data-analyst
**Record Count:** 6,097 (CIP-SOC sheet)
**Field Count:** 4

### Domain Context
**Identified Domain:** Education-to-occupation taxonomy crosswalk (public domain, U.S. government)
**Primary Entities:** CIP program codes mapped to SOC occupation codes
**Grain:** One row per CIP-SOC pairing (many-to-many relationship)
**Temporal Pattern:** Static reference table (CIP 2020 x SOC 2018 vintage; updated ~10-year cycles)
**Domain Vocabulary:** CIP (Classification of Instructional Programs), SOC (Standard Occupational Classification), crosswalk, no-match sentinel (99-9999 / 99.9999)
**Taxonomy/Codes Found:** CIP 2020 (XX.XXXX format), SOC 2018 (XX-XXXX format)

### XLSX Structure

The workbook contains 8 sheets. Only the **CIP-SOC** sheet is the primary ingest target:

| Sheet | Rows | Purpose |
|-------|------|---------|
| File Guide | 7 | Documentation |
| **CIP-SOC** | **6,097** | **Primary crosswalk: CIP -> SOC (ascending by CIP)** |
| SOC-CIP | 6,093 | Inverse view: SOC -> CIP (ascending by SOC). 4 fewer rows than CIP-SOC -- minor discrepancy worth noting. |
| New CIP | 1,076 | CIP codes new in 2020 edition |
| New SOC | 415 | SOC codes new in 2018 edition |
| Added Matches | 1,007 | New pairings added in this revision |
| Unmatched CIP Codes | 194 | CIPs with no SOC match (sentinel rows) |
| Unmatched SOC Codes | 180 | SOCs with no CIP match |

**Note:** The SOC-CIP sheet has 6,093 rows vs CIP-SOC's 6,097 -- a discrepancy of 4 rows. The ingestor should use the CIP-SOC sheet as the authoritative source per the spec.

### Key Findings

- **6,097 total rows, zero duplicates.** The grain (cipcode x soc_code) is perfectly unique. Zero nulls on all four fields.
- **100% format compliance.** All 6,097 CIP codes match XX.XXXX; all 6,097 SOC codes match XX-XXXX. No edge cases or malformed codes.
- **194 "no match" rows (3.18%).** These have SOC code 99-9999 and represent CIP programs with no corresponding occupation. After filtering, 5,903 valid crosswalk pairs remain.
- **CRITICAL: CIP granularity mismatch with College Scorecard.** The crosswalk uses 6-digit CIP codes (XX.XXXX), but `base.college_scorecard` stores CIPs as 4-digit (XX.XX). Zero direct matches exist at the 6-digit level. Truncating crosswalk CIPs to 4 digits yields 91.0% coverage of Scorecard CIPs, covering 97.1% of Scorecard rows. This is a known design decision in the spec (exact match only; 4-digit fallback deferred to Gold zone).
- **Strong BLS coverage.** 94.6% of crosswalk SOC codes match `base.bls_ooh`. The 47 mismatches are SOC version granularity differences (e.g., crosswalk has 13-1021/13-1022/13-1023 while BLS has the rolled-up 13-1020).
- **Complete O*NET coverage (one direction).** 100% of O*NET SOC codes exist in the crosswalk. 92.0% of crosswalk SOC codes exist in O*NET; the 69 missing are "All Other" residual categories (e.g., 11-9039, 27-2099) that O*NET does not profile.
- **Estimated match quality (if 4-digit CIP matching were used):** 76.6% full, 3.1% partial_no_onet, 1.4% partial_no_bls, 0.8% scorecard_only, 18.0% no_scorecard.
- **With strict 6-digit CIP matching (per spec): 100% no_scorecard.** This is the expected outcome given the granularity mismatch. The has_scorecard_match flag will be FALSE for every row until the CIP matching strategy is resolved at the Gold zone level.

### Field Profiles

#### CIP2020Code (cipcode)
- **Type:** STRING
- **Null Rate:** 0% (0 of 6,097)
- **Cardinality:** 2,143 distinct values (35.1% uniqueness -- many CIPs map to multiple SOCs)
- **Distribution:** All values match XX.XXXX format. Ranges from 01.0000 to 99.9999.
- **Outliers:** None. 99.9999 is the "no match" sentinel used by CIP codes that have no SOC in the crosswalk (appears on the Unmatched SOC Codes sheet but not in CIP-SOC as a CIP value).
- **Patterns:** `^\d{2}\.\d{4}$` -- 100% compliance

#### CIP2020Title (cip_title)
- **Type:** STRING
- **Null Rate:** 0% (0 of 6,097)
- **Cardinality:** 2,142 distinct values (one title "Social Sciences, Other." maps to two CIP codes: 45.0199 and 45.9999)
- **Patterns:** Titles end with period. Mixed case. Maximum observed length ~80 chars.

#### SOC2018Code (soc_code)
- **Type:** STRING
- **Null Rate:** 0% (0 of 6,097)
- **Cardinality:** 868 distinct values (including 99-9999 sentinel)
- **Distribution:** 867 valid SOC codes + 1 sentinel (99-9999).
- **Outliers:** 99-9999 appears 194 times (3.18% of rows). This is the "no match" sentinel.
- **Patterns:** `^\d{2}-\d{4}$` -- 100% compliance

#### SOC2018Title (soc_title)
- **Type:** STRING
- **Null Rate:** 0% (0 of 6,097)
- **Cardinality:** 868 distinct values (1:1 with SOC codes)
- **Patterns:** Mixed case. "NO MATCH" is the sentinel title for SOC 99-9999.

### Many-to-Many Cardinality Analysis

#### SOC Codes per CIP (excluding no-match rows)

| Statistic | Value |
|-----------|-------|
| CIPs with valid SOC matches | 1,949 |
| Min SOCs per CIP | 1 |
| Max SOCs per CIP | 23 (excl. 99.9999 sentinel which maps to 180) |
| Mean | 3.03 |
| Median | 3 |
| P25 | 2 |
| P75 | 4 |
| P90 | 5 |
| P95 | 6 |

**Distribution of SOCs per CIP:**

| SOCs | CIP Count | Cumulative % |
|------|-----------|-------------|
| 1 | 432 | 22.2% |
| 2 | 481 | 46.8% |
| 3 | 485 | 71.7% |
| 4 | 263 | 85.2% |
| 5 | 117 | 91.2% |
| 6 | 77 | 95.2% |
| 7 | 56 | 98.1% |
| 8-23 | 38 | 100.0% |

Most CIPs map to 1-4 SOCs (85.2%). The long tail extends to 23 SOCs for Business Administration (52.0201).

**Top 5 CIPs by SOC count:**
1. 52.0201 Business Administration and Management, General -- 23 SOCs
2. 51.1201 Medicine -- 17 SOCs
3. 51.1202 Osteopathic Medicine/Osteopathy -- 17 SOCs
4. 52.0101 Business/Commerce, General -- 17 SOCs
5. 49.0202 Construction/Heavy Equipment Operation -- 16 SOCs

#### CIP Codes per SOC

| Statistic | Value |
|-----------|-------|
| SOCs with valid CIP matches | 867 |
| Min CIPs per SOC | 1 |
| Max CIPs per SOC | 337 |
| Mean | 6.81 |
| Median | 2 |
| P25 | 1 |
| P75 | 7 |
| P90 | 14 |
| P95 | 23 |

The CIPs-per-SOC distribution is highly right-skewed. 45.1% of SOCs map to exactly 1 CIP. But "catch-all" occupation codes (especially postsecondary teachers and managers) absorb hundreds of CIPs.

**Top 5 SOCs by CIP count:**
1. 25-1071 Health Specialties Teachers, Postsecondary -- 337 CIPs
2. 19-1042 Medical Scientists, Except Epidemiologists -- 210 CIPs
3. 11-9121 Natural Sciences Managers -- 149 CIPs
4. 11-9199 Managers, All Other -- 128 CIPs
5. 25-2031 Secondary School Teachers -- 92 CIPs

### CIP Family Distribution (2-digit prefix)

Top 5 families by row count (out of 47 total families):

| Family | Rows | Description |
|--------|------|-------------|
| 61 | 579 | (Residency programs -- medical specialty training) |
| 51 | 557 | Health Professions |
| 52 | 432 | Business, Management, Marketing |
| 13 | 416 | Education |
| 26 | 355 | Biological and Biomedical Sciences |

Notably, families 32, 33, 34, 35, 36, 37, and 53 have **100% no-match rates** -- every CIP in these families maps only to SOC 99-9999. These are military (33, 34, 35), personal awareness (36), general skills (32, 37), and high school (53) families.

### SOC Major Group Distribution (2-digit prefix, excluding 99)

Top 5 groups by row count (out of 23 total groups):

| Group | Rows | Description |
|-------|------|-------------|
| 25 | 1,766 | Educational Instruction and Library (30.0% of valid rows) |
| 19 | 783 | Life, Physical, and Social Science |
| 11 | 670 | Management |
| 29 | 623 | Healthcare Practitioners and Technical |
| 27 | 339 | Arts, Design, Entertainment, Sports, Media |

SOC group 25 (Education) dominates because postsecondary teacher codes absorb many CIP programs.

### Cross-Table Match Analysis

#### vs. base.college_scorecard (cipcode)

| Metric | Value |
|--------|-------|
| Scorecard distinct CIPs | 390 |
| Scorecard CIP format | 100% XX.XX (4-digit) |
| Crosswalk CIP format | 100% XX.XXXX (6-digit) |
| **Direct 6-digit match** | **0 (0.0%)** |
| 4-digit match (truncate crosswalk) | 355 of 390 Scorecard CIPs (91.0%) |
| 4-digit row coverage | 67,939 of 69,947 Scorecard rows (97.1%) |
| Unmatched Scorecard CIPs (at 4-digit) | 35 -- mostly "Other" residual categories (XX.99) and military/personal families |

**Families in crosswalk but not Scorecard:** 60, 61, 99 (residency programs and sentinel)
**Families in Scorecard but not crosswalk:** 32, 33, 34, 35, 36, 53 (military, personal awareness, high school -- these exist in Scorecard but have 100% no-match in crosswalk)

#### vs. base.bls_ooh (soc_code)

| Metric | Value |
|--------|-------|
| BLS distinct SOCs | 832 |
| Crosswalk SOCs (excl no-match) | 867 |
| Crosswalk SOCs found in BLS | 820 (94.6%) |
| Crosswalk SOCs NOT in BLS | 47 (5.4%) |
| BLS SOCs NOT in Crosswalk | 12 (1.4%) |

All 47+12 mismatches are **SOC version granularity differences**, not true coverage gaps. The crosswalk uses detailed SOC codes (e.g., 13-1021, 13-1022, 13-1023) while BLS uses rolled-up codes (e.g., 13-1020). Every mismatch has a near-match in the same 4-digit SOC prefix. The Silver transformer can match directly; the 12 BLS SOCs without crosswalk entries are the "rolled-up" parent codes.

#### vs. base.onet_occupations (bls_soc_code)

| Metric | Value |
|--------|-------|
| O*NET distinct SOCs | 798 |
| Crosswalk SOCs found in O*NET | 798 (92.0%) |
| Crosswalk SOCs NOT in O*NET | 69 (8.0%) |
| O*NET SOCs NOT in Crosswalk | 0 (0.0%) |

100% of O*NET SOCs exist in the crosswalk (perfect coverage). The 69 crosswalk SOCs missing from O*NET are residual "All Other" categories (e.g., 11-9039 Managers All Other, 27-2099 Entertainers All Other) that O*NET does not profile individually.

### Estimated Match Quality Distribution

#### Scenario A: Strict 6-digit CIP match (per spec)

| Quality | Count | Percentage |
|---------|-------|------------|
| full | 0 | 0.0% |
| partial_no_onet | 0 | 0.0% |
| partial_no_bls | 0 | 0.0% |
| scorecard_only | 0 | 0.0% |
| **no_scorecard** | **5,903** | **100.0%** |

**All rows will be no_scorecard** because the 6-digit crosswalk CIPs never match the 4-digit Scorecard CIPs. The spec explicitly states this is expected and defers resolution to the Gold zone.

#### Scenario B: If 4-digit CIP matching were used (informational only)

| Quality | Count | Percentage |
|---------|-------|------------|
| **full** | **4,520** | **76.6%** |
| partial_no_onet | 185 | 3.1% |
| partial_no_bls | 85 | 1.4% |
| scorecard_only | 49 | 0.8% |
| no_scorecard | 1,064 | 18.0% |

With 4-digit matching, 76.6% of crosswalk rows would achieve "full" quality -- well above the spec's target of "majority." This validates that the data will work well once the Gold zone resolves the granularity mismatch.

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| No-match rows (SOC 99-9999) | 194 | 3.18% | Filter out in Silver. DQ rule: 0 rows with soc_code containing "99-9999" after transform. |
| CIP 99.9999 sentinel | 0 in CIP-SOC | 0% | Not present in primary sheet. No filtering needed on CIP side. |
| Duplicate CIP titles (same title, different code) | 1 pair | 0.05% | "Social Sciences, Other." maps to both 45.0199 and 45.9999. Not a data quality issue -- these are legitimately different CIP codes. |
| CIPs in 100% no-match families | ~75 CIPs | 3.5% of distinct CIPs | Families 32, 33, 34, 35, 36, 37, 53 are all no-match. These are valid -- these programs genuinely have no SOC occupation. |
| SOC-CIP vs CIP-SOC row count discrepancy | 4 rows | 0.07% | CIP-SOC has 6,097 rows, SOC-CIP has 6,093. Use CIP-SOC as authoritative. |
| Crosswalk SOCs not in BLS (version mismatch) | 47 | 5.4% of crosswalk SOCs | SOC granularity difference. Informational flag only -- not a blocking DQ issue. |
| Crosswalk SOCs not in O*NET ("All Other" residuals) | 69 | 8.0% of crosswalk SOCs | Expected -- O*NET does not profile residual categories. Informational. |
| Scorecard CIP granularity (4-digit vs 6-digit) | 390 of 390 | 100% | **CRITICAL:** has_scorecard_match will be FALSE for all rows with strict matching. Spec is aware. DQ rule should expect 0% has_scorecard_match=TRUE, not the 60-90% stated in spec. |
| Row count | 6,097 | -- | Above spec estimate of 3,000-5,000. Actual range for DQ rule: 5,900-6,200. |

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| cipcode | Granularity mismatch | All 6,097 | CRITICAL | Crosswalk uses XX.XXXX (6-digit), Scorecard uses XX.XX (4-digit). Zero direct joins possible. Spec defers to Gold zone resolution. |
| soc_code | Version granularity | 47+12 | LOW | Minor SOC version differences between crosswalk (SOC 2018 detailed) and BLS OOH (SOC 2018 rolled-up). 94.6% direct match rate is excellent. |
| row_count | Higher than spec estimate | 6,097 | INFO | Spec estimated 3,000-5,000. Actual is 6,097. DQ row count rule should be adjusted to 5,500-6,500. |
| SOC-CIP sheet | Row count discrepancy | 4 | INFO | SOC-CIP sheet has 4 fewer rows than CIP-SOC. Not relevant for ingest (using CIP-SOC only) but worth documenting. |

### Recommendations for DQ Rule Writer

1. **Row count range:** Set to 5,500-6,500 (actual 6,097, above the spec's 3,000-5,000 estimate).
2. **has_scorecard_match threshold:** Override spec's 60-90% expectation. With strict 6-digit matching, expect **0% TRUE**. If the implementation switches to 4-digit matching, expect ~82% TRUE.
3. **has_bls_match threshold:** Expect 94-96% TRUE (actual: 94.6% of SOC codes match BLS).
4. **has_onet_match threshold:** Expect 90-94% TRUE (actual: 92.0% of SOC codes match O*NET).
5. **match_quality distribution:** With strict CIP matching: 100% no_scorecard. With 4-digit: ~77% full, ~3% partial_no_onet, ~1.5% partial_no_bls, ~1% scorecard_only, ~18% no_scorecard.
6. **No-match filter:** Exactly 194 rows should be excluded (SOC 99-9999). After filtering: 5,903 rows.
7. **Grain integrity:** Zero duplicates confirmed on (cipcode, soc_code). DQ rule can enforce strict uniqueness.
8. **Format validation:** 100% CIP and SOC format compliance. Set rules at 100% threshold.
9. **Null check:** Zero nulls on all fields. Set at 0% threshold.

### Recommendations for Spec / Architecture

1. **The has_scorecard_match flag will be FALSE for all rows under strict 6-digit matching.** The spec acknowledges this (Open Decision #1) and defers to Gold zone. However, the DQ rule expectations in the spec (60-90% has_scorecard_match) are incorrect for strict matching and should be updated.
2. **Consider adding a cip_4digit derived field** (first 5 chars of cipcode) to the Silver schema to simplify Gold zone matching without violating the "no fuzzy matching" principle.
3. **BLS SOC version differences are systematic,** not random. All 47+12 mismatches follow the same pattern: crosswalk uses detailed codes, BLS uses rolled-up parent codes. A future SOC normalization step could resolve these.
