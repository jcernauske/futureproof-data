# EDA Report: College Scorecard Institution-Level Data

**Source:** U.S. Department of Education College Scorecard, Most-Recent-Cohorts-Institution.csv
**Date:** 2026-04-15
**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md`
**Record Count (raw file):** 6,429
**Record Count (filtered):** 3,039
**Field Count (source file):** 3,306
**Fields Analyzed:** 25

---

## Domain Context

**Identified Domain:** U.S. higher education institution-level cost and financial aid data
**Primary Entities:** Title IV post-secondary institutions
**Grain:** One row per institution (UNITID). Zero duplicates confirmed.
**Temporal Pattern:** Annual snapshot (most recent cohort data as of March 2025 file date)
**Domain Vocabulary:** COA (cost of attendance), net price, IPEDS, Title IV, PREDDEG (predominant degree), ICLEVEL (institution level), CONTROL (public/private/for-profit)
**Taxonomy/Codes Found:** CONTROL (1/2/3), PREDDEG (0-4), ICLEVEL (1-3), STABBR (50 states + territories)

---

## Key Findings

- **Row count after filter is 3,039, not ~6,500.** The spec estimated ~6,500 but that is the unfiltered count (6,429). After applying PREDDEG=3 OR ICLEVEL=1, we get 3,039 rows. The DQ row count rule should be 2,500-3,500, not 5,000-8,000.
- **Zero PrivacySuppressed values** in any cost/price field. All nulls are genuine blanks (empty cells). This is unlike the field-of-study file where PS is common. The ingestor's sentinel handling is still correct (defensive), but expect zero PS conversions in practice.
- **COA coverage is only 73.5%**, not the 90% the spec assumes. 806 institutions (26.5%) have neither COSTT4_A nor COSTT4_P. These are heavily concentrated in PREDDEG=0 (not classified, 288), PREDDEG=4 (graduate-dominant, 280), and private nonprofits (515).
- **Unified net price coverage is also 73.5%** -- exactly the same set as COA. Where COA is missing, net price is also missing.
- **Negative net prices are legitimate.** MIT's lowest-income quintile net price is -$4,129 (aid exceeds total cost). 3 public schools and 5 private schools have negative average net prices. DQ rules should allow negatives in net price fields.
- **Quintile monotonicity violations are common** (Q1 > Q2 in 481 of 1,073 private rows = 44.8%). This is NOT a data quality issue -- it reflects that the lowest-income students may receive less institutional aid at some schools, or have higher need-based housing costs. The Q1-vs-Q5 inversion rate is much lower (39 of 1,073 = 3.6% private, 7 of 713 = 1.0% public; 46 total — reconfirmed by staff-engineer re-count. An earlier draft cited 34 private inversions; corrected here).
- **For-profit institutions have poor data coverage:** only 52.6% have net price, 44.3% have COA. These schools serve 418 of 3,039 filtered rows (13.8%).
- **UNITID join coverage is strong:** 2,352 of 2,559 field-of-study UNITIDs (91.9%) match institution-level data. 207 FoS schools have no institution match (likely closed or reporting gaps).
- **72 public schools report in-state = out-of-state tuition.** These appear to be tribal colleges, online-only, and state systems with uniform pricing. Not a data error.
- **COSTT4_A and COSTT4_P are mutually exclusive** -- zero institutions have both. COSTT4_A covers academic-year programs (2,192 rows), COSTT4_P covers program-year programs (41 rows).

---

## Row Count Summary

| Segment | Count |
|---------|-------|
| Raw file total | 6,429 |
| After PREDDEG=3 OR ICLEVEL=1 filter | 3,039 |
| Distinct UNITIDs (filtered) | 3,039 |
| Duplicate UNITIDs | 0 |

### PREDDEG Distribution (within filtered set)

| PREDDEG | Label | Count | % |
|---------|-------|-------|---|
| 0 | Not classified | 288 | 9.5% |
| 1 | Certificate | 153 | 5.0% |
| 2 | Associate's | 335 | 11.0% |
| 3 | Bachelor's | 1,983 | 65.3% |
| 4 | Graduate | 280 | 9.2% |

### CONTROL Distribution

| CONTROL | Label | Count | % |
|---------|-------|-------|---|
| 1 | Public | 867 | 28.5% |
| 2 | Private nonprofit | 1,754 | 57.7% |
| 3 | Private for-profit | 418 | 13.8% |

---

## Null/Suppression Rates

| Field | Non-null | Null | Null% | PrivacySuppressed |
|-------|----------|------|-------|-------------------|
| COSTT4_A | 2,192 | 847 | 27.9% | 0 |
| COSTT4_P | 41 | 2,998 | 98.7% | 0 |
| NPT4_PUB | 774 | 2,265 | 74.5% | 0 |
| NPT4_PRIV | 1,459 | 1,580 | 52.0% | 0 |
| NPT41_PUB | 773 | 2,266 | 74.6% | 0 |
| NPT42_PUB | 763 | 2,276 | 74.9% | 0 |
| NPT43_PUB | 766 | 2,273 | 74.8% | 0 |
| NPT44_PUB | 747 | 2,292 | 75.4% | 0 |
| NPT45_PUB | 716 | 2,323 | 76.4% | 0 |
| NPT41_PRIV | 1,412 | 1,627 | 53.5% | 0 |
| NPT42_PRIV | 1,343 | 1,696 | 55.8% | 0 |
| NPT43_PRIV | 1,313 | 1,726 | 56.8% | 0 |
| NPT44_PRIV | 1,234 | 1,805 | 59.4% | 0 |
| NPT45_PRIV | 1,130 | 1,909 | 62.8% | 0 |
| TUITIONFEE_IN | 2,518 | 521 | 17.1% | 0 |
| TUITIONFEE_OUT | 2,518 | 521 | 17.1% | 0 |
| ROOMBOARD_ON | 1,719 | 1,320 | 43.4% | 0 |
| ROOMBOARD_OFF | 2,256 | 783 | 25.8% | 0 |
| BOOKSUPPLY | 2,257 | 782 | 25.7% | 0 |

**Why are nulls high?** The null patterns align with institutional characteristics:
- NPT4_PUB is null for all 2,172 private/for-profit schools (expected -- they use NPT4_PRIV)
- NPT4_PRIV is null for all 867 public schools (expected)
- Among their own CONTROL group: public NPT4_PUB is 89.3% populated, private nonprofit NPT4_PRIV is 70.6%, for-profit NPT4_PRIV is only 52.6%
- COSTT4_P is nearly empty (41 rows) because almost all 4-year schools are academic-year programs
- ROOMBOARD_ON null for 43.4% -- many schools lack on-campus housing

---

## Field Profiles: Cost/Price Distributions

All values in USD, non-null rows only.

| Field | Count | Min | P25 | Median | P75 | Max | Mean | StdDev |
|-------|-------|-----|-----|--------|-----|-----|------|--------|
| COSTT4_A | 2,192 | $6,362 | $21,644 | $30,288 | $48,448 | $87,804 | $36,214 | $18,932 |
| COSTT4_P | 41 | $11,361 | $24,444 | $31,097 | $33,571 | $48,271 | $30,076 | $7,993 |
| NPT4_PUB | 774 | -$1,180 | $9,089 | $12,978 | $16,546 | $32,598 | $12,876 | $5,451 |
| NPT4_PRIV | 1,459 | $1,525 | $17,938 | $22,668 | $28,448 | $77,180 | $23,276 | $9,600 |
| NPT41_PUB | 773 | -$3,351 | $6,398 | $9,266 | $12,011 | $30,732 | $9,233 | $4,240 |
| NPT42_PUB | 763 | -$1,349 | $7,199 | $10,092 | $12,976 | $32,490 | $10,174 | $4,309 |
| NPT43_PUB | 766 | -$1,325 | $9,704 | $12,848 | $16,060 | $31,200 | $12,963 | $4,598 |
| NPT44_PUB | 747 | $3,333 | $13,200 | $16,857 | $19,861 | $33,579 | $16,599 | $5,092 |
| NPT45_PUB | 716 | -$1,447 | $15,236 | $18,887 | $22,994 | $37,209 | $19,085 | $5,799 |
| NPT41_PRIV | 1,412 | -$4,129 | $13,743 | $18,108 | $23,276 | $78,201 | $18,830 | $8,710 |
| NPT42_PRIV | 1,343 | -$2,483 | $14,354 | $18,608 | $24,193 | $74,499 | $19,449 | $8,974 |
| NPT43_PRIV | 1,313 | -$123 | $16,549 | $20,975 | $25,871 | $66,505 | $21,563 | $8,901 |
| NPT44_PRIV | 1,234 | $2,650 | $20,561 | $24,710 | $29,667 | $63,333 | $25,292 | $8,510 |
| NPT45_PRIV | 1,130 | $6,301 | $24,196 | $29,034 | $35,176 | $79,482 | $30,896 | $10,417 |
| TUITIONFEE_IN | 2,518 | $600 | $9,124 | $15,222 | $33,115 | $69,330 | $21,891 | $16,558 |
| TUITIONFEE_OUT | 2,518 | $600 | $13,755 | $20,504 | $34,930 | $69,330 | $25,179 | $15,374 |
| ROOMBOARD_ON | 1,719 | $1,000 | $9,802 | $12,040 | $14,736 | $29,874 | $12,181 | $3,902 |
| ROOMBOARD_OFF | 2,256 | $2,001 | $9,328 | $11,843 | $15,000 | $39,100 | $12,357 | $4,290 |
| BOOKSUPPLY | 2,257 | $0 | $900 | $1,200 | $1,460 | $9,741 | $1,213 | $639 |

---

## Cross-Field Analysis

### Net Price vs Cost of Attendance

- **Public institutions:** 0 of 774 cases where NPT4_PUB > COSTT4_A. Clean.
- **Private institutions:** 0 of 1,418 cases where NPT4_PRIV > COSTT4_A. Clean.
- The spec's DQ rule "net_price_annual <= cost_of_attendance_annual" holds at 100%.

### CONTROL vs Net Price Field Population

| CONTROL | N | NPT4_PUB populated | NPT4_PRIV populated |
|---------|---|-------------------|---------------------|
| 1 (Public) | 867 | 774 (89.3%) | 0 (0.0%) |
| 2 (Private NP) | 1,754 | 0 (0.0%) | 1,239 (70.6%) |
| 3 (For-profit) | 418 | 0 (0.0%) | 220 (52.6%) |

The expected pattern holds perfectly: public schools populate only NPT4_PUB, private/for-profit populate only NPT4_PRIV. No cross-contamination.

The spec's DQ rules of "control=1 -> npt4_pub non-null >= 80%" passes (89.3%). The "control=2 -> npt4_priv non-null >= 80%" will FAIL at 70.6%. Recommend lowering to >= 65% or splitting CONTROL=2 and CONTROL=3 rules.

### COA Field Mutual Exclusivity

COSTT4_A and COSTT4_P are mutually exclusive -- zero overlap. The COALESCE(costt4_a, costt4_p) Silver transformation is safe.

### Tuition In-State vs Out-of-State

- 0 cases where in-state > out-of-state (correct -- in-state should always be <= out-of-state)
- 1,771 of 2,518 (70.3%) have equal in-state and out-of-state tuition
- 1,699 of those 1,771 are private/for-profit (expected -- they don't distinguish in/out-of-state)
- 72 are public schools with equal tuition -- tribal colleges, online-only, and uniform-pricing systems

### Quintile Monotonicity

**Adjacent-pair inversions (Q[n] > Q[n+1]):**

| Pair | Public (of 713) | Private (of 1,073) |
|------|----------------|-------------------|
| Q1 > Q2 | 103 (14.4%) | 407 (37.9%) |
| Q2 > Q3 | 12 (1.7%) | 148 (13.8%) |
| Q3 > Q4 | 19 (2.7%) | 85 (7.9%) |
| Q4 > Q5 | 64 (9.0%) | 146 (13.6%) |

**Full-span inversions (Q1 > Q5):**
- Public: 7 of 713 (1.0%)
- Private: 39 of 1,073 (3.6%)
- Total: 46 inversions (matches DQ scorecard)

The Q1>Q2 inversion rate is very high (37.9% for private schools). This is a known pattern in College Scorecard data: many private institutions provide substantial merit aid to middle-income students (Q2: $30-48K) but their Pell-eligible lowest-income students (Q1: $0-30K) may face higher net prices because federal aid caps out. The median inversion magnitude is $1,378 and max is $13,584. The DQ rule "net_price_q1 <= net_price_q5" should use the full-span comparison only, and expect ~3% violation rate.

---

## UNITID Join Coverage

| Set | Count |
|-----|-------|
| Institution UNITIDs | 3,039 |
| Field-of-study UNITIDs (bronze) | 2,559 |
| Overlap (LEFT JOIN success) | 2,352 (91.9% of FoS) |
| Institution only (no FoS match) | 687 |
| FoS only (no institution match) | 207 |

The 207 FoS-only schools (8.1%) will get NULL cost data after the Gold LEFT JOIN. These are likely schools that report field-of-study earnings/debt data but didn't report institution-level cost data, or vice versa due to PREDDEG/ICLEVEL filter differences.

---

## Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| No COA at all (neither COSTT4_A nor COSTT4_P) | 806 | 26.5% | Lower COA non-null threshold from 90% to 73% (or 70% with margin) |
| Negative NPT4_PUB (average net price) | 3 | 0.4% of public | Allow negatives in net price range rules. Use range -$5,000 to $35,000 |
| Negative NPT4_PRIV (average net price) | 0 | 0% | NPT4_PRIV min is $1,525 -- positive. But quintile fields go negative |
| Negative quintile net prices (public) | up to 6 per quintile | <1% | Allow negatives. Range: -$5,000 to $40,000 |
| Negative quintile net prices (private) | up to 5 per quintile | <0.5% | Allow negatives. Range: -$5,000 to $80,000 |
| BOOKSUPPLY = 0 | 32 | 1.4% | Allow zero. Some schools include books in tuition or provide free textbooks |
| COSTT4_A max = $87,804 | 1 | -- | Spec DQ range $5K-$100K is correct and has headroom |
| ROOMBOARD_ON = $1,000 (minimum) | 1 | -- | Spec DQ floor of $3,000 will flag this. Consider $1,000 floor |
| For-profit NPT4_PRIV coverage only 52.6% | 220/418 | -- | For-profit schools underreport; do not set coverage thresholds above 55% for CONTROL=3 |
| Private NP NPT4_PRIV only 70.6% | 1,239/1,754 | -- | Spec threshold of 80% will FAIL. Lower to 68% or split by CONTROL |
| Q1 > Q2 inversions (private) | 407/1,073 | 37.9% | Do NOT use adjacent-pair monotonicity rules. Use Q1 <= Q5 only (3.2% violation) |
| Public in-state == out-of-state tuition | 72 | 8.9% of public | Not an error. Do not flag |

---

## Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| NPT4_PUB | Negative values | 3 | Low | San Diego Mesa (-$904), Skyline College (-$1,180), St Petersburg College (-$52). Aid exceeds COA for average student. Legitimate. |
| NPT41_PRIV | Negative values | 5 | Low | MIT (-$4,129), Williams (-$2,421), Brown (-$2,158), UChicago (-$1,428), Stanford (-$79). Very generous aid to lowest-income students. Legitimate. |
| BOOKSUPPLY | Zero values | 32 | Low | 32 institutions report $0 books/supplies. Some provide free textbooks or include in tuition. |
| BOOKSUPPLY | High outlier | 1 | Low | Max $9,741 vs median $1,200. Likely art/architecture/design program costs. |
| ROOMBOARD_ON | Low outlier | 1 | Low | Min $1,000 vs P25 $9,802. May be partial-year or subsidized housing. |
| COSTT4_P | Very sparse | 41 | Medium | Only 41 program-year institutions in the filtered set. All academic-year institutions use COSTT4_A exclusively. |
| All cost fields | Zero PrivacySuppressed | 0 | Info | Unlike the field-of-study file, institution-level cost data has NO suppressed values. All nulls are genuine blanks. |

---

## Spec DQ Rule Adjustments Recommended

Based on this analysis, the following spec DQ rules need revision:

1. **Row count:** Change from "5,000-8,000" to "2,500-3,500" (actual: 3,039)
2. **costt4_a range:** $5,000-$100,000 is correct (actual: $6,362-$87,804)
3. **npt4_pub range:** Change from "$0-$60,000" to "-$5,000-$35,000" (actual: -$1,180 to $32,598)
4. **npt4_priv range:** Change from "$0-$80,000" to "$0-$80,000" (correct as-is; actual: $1,525-$77,180)
5. **Quintile net price ranges:** Must allow negatives. Suggest -$5,000 lower bound for all quintile fields.
6. **"At least one of costt4_a or costt4_p non-null >= 90%":** Will FAIL. Actual is 73.5%. Lower to >= 70%.
7. **"control=2 -> npt4_priv non-null >= 80%":** Will FAIL. Actual is 70.6%. Lower to >= 65%.
8. **roomboard_on range:** Spec says $3,000-$25,000. Minimum is $1,000. Suggest $1,000-$30,000 (max is $29,874).
9. **Quintile monotonicity:** Do NOT enforce adjacent-pair monotonicity (Q[n] <= Q[n+1]). Only enforce Q1 <= Q5, and expect ~3% violation rate.
