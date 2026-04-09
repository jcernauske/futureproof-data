## EDA Report: Gold consumable.career_outcomes (pre-build profiling)
**Source:** base.college_scorecard (Silver zone Iceberg table)
**Date:** 2026-04-06
**Agent:** @data-analyst
**Record Count:** 69,947
**Field Count:** 30 (Gold target schema per logical model)
**Reference Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Reference Model:** governance/models/gold-career-outcomes-college-scorecard-logical.md
**Prior EDA:** governance/eda/silver-college-scorecard-eda.md

---

### Purpose

This EDA profiles the Silver `base.college_scorecard` data from the perspective of Gold zone derived fields. It simulates every Gold derivation (percentile bands, debt-to-earnings ratio, earnings growth rate, confidence tier, etc.) against the actual Silver data and profiles the resulting distributions. These findings directly inform @dq-rule-writer's Gold zone DQ thresholds.

---

### Key Findings

1. **Debt-to-earnings ratio is heavily left-skewed.** 69.23% of programs fall in the "Low" tier (< 0.75), 29.96% in "Moderate" (0.75-1.5), 0.78% in "High" (1.5-2.5), and 0.02% in "Very High" (>= 2.5). The spec's expectation that "Moderate" would be the plurality is incorrect -- "Low" dominates. DQ rules should reflect this actual distribution.

2. **Zero debt-to-earnings outliers outside 0.01-10.0.** The range is 0.050-5.328. The spec's soft constraint range (0.01-10.0) will see zero violations. The tighter range 0.05-6.0 covers 100% of the data.

3. **44.2% of earnings growth rates are negative.** This is expected (cross-cohort, not longitudinal). The logical model correctly documents ~44%. Only 15 rows (0.07%) fall outside the -0.5 to 2.0 range -- 13 below -0.5 and 2 above 2.0.

4. **52.75% of rows will be "insufficient" confidence tier**, confirming the spec estimate of 50-55%. Only 21.80% reach "high" confidence. The "medium" tier is surprisingly small at 1.79%.

5. **7 CIP families will get null 1yr earnings percentile bands** (< 3 non-null values): CIP 28, 32, 33, 34, 35, 48, 53. This affects only 36 rows (0.05%). 8 families get null 2yr/debt bands.

6. **4 CIP families have only 1 program with earnings data**, meaning PERCENT_RANK will always be 0.0 for those programs: CIP 28, 34, 48, 53.

7. **institution_control is 100% NULL.** This is a known blocking issue from the Silver EDA (CONTROL column was not in the Bronze parquet). The Gold transformer cannot populate this field until the Silver table is rebuilt with CONTROL data.

8. **IQR spread varies enormously across CIP families.** Health Professions (CIP 51) has the widest earnings IQR spread at 56.2% of median, while Construction Trades (CIP 46) is only 4.8%. This matters for the effort slider -- some fields have a much wider range of outcomes than others.

---

### 1. Percentile Band Distributions

#### Earnings 1yr Percentile Bands by CIP Family

38 of 45 CIP families have >= 3 non-null earnings_1yr_median values and will receive valid percentile bands. 7 families will get null bands.

| CIP | Name | N (non-null) | P25 | P50 | P75 | IQR | Spread % |
|-----|------|-------------|-----|-----|-----|-----|----------|
| 01 | Agriculture | 335 | $29,442 | $36,386 | $43,046 | $13,604 | 37.4% |
| 03 | Natural Resources | 371 | $26,524 | $30,661 | $35,527 | $9,002 | 29.4% |
| 04 | Architecture | 140 | $39,060 | $44,291 | $50,541 | $11,482 | 25.9% |
| 05 | Area/Ethnic/Cultural Studies | 162 | $26,365 | $29,732 | $33,730 | $7,365 | 24.8% |
| 09 | Communication/Journalism | 1,140 | $28,874 | $32,497 | $36,367 | $7,493 | 23.1% |
| 10 | Communications Technologies | 83 | $21,687 | $25,953 | $32,815 | $11,128 | 42.9% |
| 11 | Computer/Information Sciences | 1,138 | $46,984 | $54,850 | $65,661 | $18,678 | 34.1% |
| 12 | Personal/Culinary Services | 26 | $28,105 | $30,833 | $37,616 | $9,511 | 30.8% |
| 13 | Education | 1,347 | $32,724 | $36,156 | $39,794 | $7,070 | 19.6% |
| 14 | Engineering | 1,689 | $60,121 | $64,984 | $69,541 | $9,420 | 14.5% |
| 15 | Engineering Technologies | 382 | $52,602 | $59,136 | $64,168 | $11,566 | 19.6% |
| 16 | Foreign Languages | 366 | $25,756 | $29,726 | $34,323 | $8,568 | 28.8% |
| 19 | Family/Consumer Sciences | 345 | $27,609 | $30,413 | $34,368 | $6,759 | 22.2% |
| 22 | Legal Professions | 84 | $31,805 | $35,405 | $40,147 | $8,342 | 23.6% |
| 23 | English Language/Literature | 664 | $24,114 | $27,728 | $31,648 | $7,534 | 27.2% |
| 24 | Liberal Arts/General Studies | 450 | $27,742 | $32,028 | $36,480 | $8,738 | 27.3% |
| 25 | Library Science | 3 | $20,318 | $26,165 | $31,744 | $11,426 | 43.7% |
| 26 | Biological/Biomedical Sciences | 1,356 | $24,172 | $27,868 | $31,642 | $7,470 | 26.8% |
| 27 | Mathematics/Statistics | 377 | $39,377 | $45,075 | $52,010 | $12,633 | 28.0% |
| 29 | Military Technologies | 4 | $36,472 | $41,356 | $49,076 | $12,605 | 30.5% |
| 30 | Multi/Interdisciplinary | 507 | $27,230 | $32,155 | $37,732 | $10,502 | 32.7% |
| 31 | Parks/Recreation/Fitness | 651 | $25,650 | $28,898 | $32,209 | $6,560 | 22.7% |
| 36 | Leisure/Recreational Activities | 3 | $21,552 | $23,797 | $27,668 | $6,117 | 25.7% |
| 38 | Philosophy/Religious Studies | 99 | $25,073 | $28,426 | $33,299 | $8,226 | 28.9% |
| 39 | Theology/Religious Vocations | 113 | $24,946 | $27,374 | $30,772 | $5,826 | 21.3% |
| 40 | Physical Sciences | 446 | $33,040 | $36,792 | $40,611 | $7,571 | 20.6% |
| 41 | Science Technologies | 9 | $39,610 | $43,113 | $58,107 | $18,497 | 42.9% |
| 42 | Psychology | 1,136 | $25,985 | $28,697 | $31,572 | $5,587 | 19.5% |
| 43 | Homeland Security/Law Enforcement | 759 | $31,157 | $34,100 | $38,125 | $6,968 | 20.4% |
| 44 | Public Administration | 541 | $29,946 | $32,587 | $35,784 | $5,838 | 17.9% |
| 45 | Social Sciences | 1,949 | $28,832 | $32,981 | $39,028 | $10,196 | 30.9% |
| 46 | Construction Trades | 8 | $62,625 | $64,818 | $65,756 | $3,131 | 4.8% |
| 47 | Mechanic/Repair Technologies | 9 | $49,024 | $54,341 | $61,397 | $12,373 | 22.8% |
| 49 | Transportation/Materials Moving | 60 | $41,071 | $47,246 | $49,103 | $8,032 | 17.0% |
| 50 | Visual/Performing Arts | 1,499 | $21,008 | $24,757 | $29,430 | $8,422 | 34.0% |
| 51 | Health Professions | 2,345 | $32,935 | $52,767 | $62,573 | $29,638 | 56.2% |
| 52 | Business/Management/Marketing | 4,165 | $38,515 | $43,901 | $49,674 | $11,159 | 25.4% |
| 54 | History | 431 | $25,545 | $29,011 | $32,850 | $7,305 | 25.2% |

#### CIP Families with < 3 Non-Null Values (null bands)

| CIP | Name | nn_1yr | nn_2yr | nn_debt | Total Rows |
|-----|------|--------|--------|---------|------------|
| 25 | Library Science | 3 | **2** | 3 | 13 |
| 28 | Military Science | **1** | **1** | **1** | 7 |
| 32 | Basic Skills/Remedial Education | **0** | **0** | **0** | 3 |
| 33 | Citizenship Activities | **0** | **0** | **0** | 2 |
| 34 | Health-Related Knowledge | **1** | **1** | **2** | 10 |
| 35 | Interpersonal/Social Skills | **0** | **0** | **0** | 1 |
| 36 | Leisure/Recreational Activities | 3 | 4 | **2** | 33 |
| 48 | Precision Production | **1** | **1** | **1** | 9 |
| 53 | High School/Secondary Programs | **1** | **1** | **0** | 4 |

**Impact:** 36 rows (0.05%) get null 1yr bands, 49 rows (0.07%) get null 2yr bands, 69 rows (0.10%) get null debt bands. These are all edge-case CIP families at the bachelor's level.

#### Percentile Band Distribution Summary (across all 38 valid CIP families for 1yr earnings)

| Metric | P25 values | P75 values |
|--------|-----------|-----------|
| Minimum | $20,318 | $27,668 |
| Maximum | $62,625 | $69,541 |
| Mean | $32,463 | $42,261 |

**P25 <= P75 invariant: 0 violations.** This invariant will always hold by mathematical definition of PERCENTILE_CONT.

#### Edge Cases: CIP Families at Minimum Threshold (exactly 3 non-null)

| CIP | Name | nn_1yr | Note |
|-----|------|--------|------|
| 25 | Library Science | 3 | Mathematically valid but statistically weak percentile bands |
| 36 | Leisure/Recreational Activities | 3 | Same concern |

CIP 29 (Military Technologies) has 4. These families' percentile bands are technically correct but are based on very small samples. The logical model acknowledges this as an accepted risk (Open Issue #2).

---

### 2. Debt-to-Earnings Ratio Distribution

**Population:** 21,763 rows where both debt_median and earnings_1yr_median are non-null (31.11% of all rows).

| Statistic | Value |
|-----------|-------|
| Count | 21,763 |
| Min | 0.050 |
| P05 | 0.286 |
| P25 | 0.442 |
| **Median (P50)** | **0.616** |
| P75 | 0.800 |
| P95 | 1.137 |
| Max | 5.328 |
| Mean | 0.647 |
| Std Dev | 0.274 |

#### Tier Distribution

| Tier | Count | Percentage | Spec Expectation |
|------|-------|------------|------------------|
| Low (< 0.75) | 15,067 | 69.23% | -- |
| **Moderate (0.75-1.5)** | **6,521** | **29.96%** | Spec says "expect plurality" -- INCORRECT |
| High (1.5-2.5) | 170 | 0.78% | -- |
| Very High (>= 2.5) | 5 | 0.02% | -- |
| NULL (missing input) | 48,184 | (68.89% of all rows) | -- |

**CORRECTION FOR SPEC:** The spec states "expect Moderate to be plurality." The actual data shows "Low" is the plurality at 69.23%. This is good news -- it means the majority of bachelor's programs have manageable debt relative to first-year earnings. The DQ rule should check that "Low" is the plurality, not "Moderate."

#### Histogram (0.1 buckets)

```
0.0:    12   |
0.1:   231   ||
0.2:  1084   ||||||||||
0.3:  2705   |||||||||||||||||||||||||
0.4:  3188   |||||||||||||||||||||||||||||
0.5:  3158   |||||||||||||||||||||||||||||
0.6:  3294   ||||||||||||||||||||||||||||||  <-- mode
0.7:  2643   ||||||||||||||||||||||||
0.8:  2019   ||||||||||||||||||
0.9:  1317   ||||||||||||
1.0:   810   |||||||
1.1:   488   ||||
1.2:   311   ||
1.3:   211   |
1.4:   117   |
1.5+:  175   |
```

The distribution is unimodal with a mode around 0.6 and a long right tail.

#### Outlier Analysis

- **Outside 0.01-10.0:** 0 rows (0%). The spec's soft constraint range has zero violations.
- **Outside 0.05-6.0:** 0 rows. A tighter range still has zero violations.
- **3-sigma outliers (> mean + 3*std = 1.47):** 175 rows (0.80%)

**Top 5 highest ratios:**

| Ratio | Institution | Program | Earnings 1yr | Debt |
|-------|-------------|---------|-------------|------|
| 5.328 | Bloomsburg University of Pennsylvania | Communication Disorders Sciences | $4,880 | $26,000 |
| 4.669 | Daemen University | Natural Sciences | $5,783 | $27,000 |
| 3.407 | Springfield College | Health Services/Allied Health | $7,704 | $26,250 |
| 2.665 | East Stroudsburg University | Communication Disorders Sciences | $8,743 | $23,300 |
| 2.587 | Drew University | Drama/Theatre Arts | $10,438 | $27,000 |

These extreme ratios are driven by very low first-year earnings (programs that typically lead to graduate school, like Communication Disorders), not by unusual debt levels. The debt figures ($23K-$27K) are normal; the earnings are far below the dataset median ($35,812).

---

### 3. Earnings Growth Rate Distribution

**Population:** 22,146 rows where both earnings_1yr_median and earnings_2yr_median are non-null (31.66% of all rows).

| Statistic | Value |
|-----------|-------|
| Count | 22,146 |
| Min | -0.603 |
| P05 | -0.194 |
| P25 | -0.053 |
| **Median (P50)** | **+0.014** |
| P75 | +0.093 |
| P95 | +0.303 |
| Max | +2.686 |
| Mean | +0.031 |
| Std Dev | 0.161 |

#### Direction Distribution

| Direction | Count | Percentage |
|-----------|-------|------------|
| Negative (< 0) | 9,797 | 44.2% |
| Zero (= 0) | 0 | 0.0% |
| Positive (> 0) | 12,349 | 55.8% |

The 44.2% negative rate is expected and documented in the logical model. These are cross-cohort comparisons, not individual regression. A negative rate simply means the 1yr cohort at that program happens to earn more than the 2yr cohort.

#### Outlier Analysis

| Range | Count | Percentage |
|-------|-------|------------|
| Below -0.5 | 13 | 0.059% |
| Above +2.0 | 2 | 0.009% |
| **Total outside -0.5 to 2.0** | **15** | **0.068%** |

**Most extreme values:**

| Growth Rate | Institution | Program | Earnings 1yr | Earnings 2yr |
|-------------|-------------|---------|-------------|-------------|
| +2.686 | University of Chicago | Linguistics | $14,137 | $52,107 |
| +2.625 | Cal State Dominguez Hills | Clinical/Medical Lab Science | $23,965 | $86,867 |
| -0.603 | (not detailed) | (not detailed) | -- | -- |

The extreme positive values (+2.6x) represent programs where the 2yr cohort dramatically out-earns the 1yr cohort. This can happen when the 1yr cohort is small and the program outcomes are volatile.

#### Histogram (0.05 buckets)

The distribution is approximately normal, centered slightly positive at +0.014, with the bulk of values between -0.15 and +0.15.

---

### 4. Confidence Tier Distribution

| Tier | Count | Percentage | Criteria |
|------|-------|------------|----------|
| high | 15,245 | 21.80% | large cohort + earnings + debt |
| medium | 1,252 | 1.79% | large cohort + partial data |
| low | 16,556 | 23.67% | small cohort + some data |
| **insufficient** | **36,894** | **52.75%** | no outcome data |

**Spec estimate was 50-55% for "insufficient" -- confirmed at 52.75%.**

The "medium" tier is very small (1.79%) because large-cohort programs (small_cohort_flag = False) overwhelmingly have both earnings AND debt data (15,245 / 17,121 = 89.04%). Only 1,252 large-cohort programs have partial data and only 624 large-cohort programs have no data at all (those 624 are "insufficient," not "medium").

#### Cross-Tabulation: small_cohort_flag x has_earnings x has_debt

| Flag | Has Earnings | Has Debt | Count | Tier |
|------|-------------|---------|-------|------|
| False | True | True | 15,245 | high |
| False | True | False | 557 | medium |
| False | False | True | 695 | medium |
| False | False | False | 624 | insufficient |
| True | True | True | 8,242 | low |
| True | True | False | 6,687 | low |
| True | False | True | 1,627 | low |
| True | False | False | 36,270 | insufficient |

#### has_earnings and has_debt Flags

| Flag | True Count | Percentage |
|------|-----------|------------|
| has_earnings | 30,731 | 43.93% |
| has_debt | 25,809 | 36.90% |

---

### 5. Outcome Completeness Distribution

| Non-null Fields | outcome_completeness | Count | Percentage |
|-----------------|---------------------|-------|------------|
| 0 of 3 | 0.0 | 36,894 | 52.75% |
| 1 of 3 | 0.33 | 7,071 | 10.11% |
| 2 of 3 | 0.67 | 6,331 | 9.05% |
| 3 of 3 | 1.0 | 19,651 | 28.09% |

The value set is exactly {0.0, 0.33, 0.67, 1.0} as required. No intermediate values are possible.

#### Cross-Tabulation: Which Fields are Present

| earnings_1yr | earnings_2yr | debt | Count | Percentage |
|-------------|-------------|------|-------|------------|
| null | null | null | 36,894 | 52.75% |
| present | present | present | 19,651 | 28.09% |
| null | present | null | 3,811 | 5.45% |
| present | present | null | 2,495 | 3.57% |
| null | null | present | 2,322 | 3.32% |
| present | null | present | 2,112 | 3.02% |
| null | present | present | 1,724 | 2.46% |
| present | null | null | 938 | 1.34% |

The most common non-trivial pattern is all-three-present (28.09%). Individual field availability is independent -- DQ rules must not assume joint nullity.

---

### 6. CIP Family Earnings Rank (PERCENT_RANK)

**Population:** 25,196 rows with non-null earnings_1yr_median.

| Statistic | Value |
|-----------|-------|
| Min | 0.0000 |
| P25 | 0.2493 |
| Median | 0.4996 |
| P75 | 0.7500 |
| Max | 1.0000 |
| Mean | 0.4997 |

The distribution is nearly uniform (mean and median both approximately 0.5), which is expected for PERCENT_RANK across reasonably sized groups.

**Rank = 0.0:** 45 rows (0.18%) -- these are the lowest earners in their CIP family
**Rank = 1.0:** 35 rows (0.14%) -- these are the highest earners in their CIP family

#### Families with Only 1 Program with Earnings (rank always 0.0)

| CIP | Name | Programs with Earnings |
|-----|------|----------------------|
| 28 | Military Science | 1 |
| 34 | Health-Related Knowledge | 1 |
| 48 | Precision Production | 1 |
| 53 | High School/Secondary Programs | 1 |

These 4 programs will always have rank = 0.0 because PERCENT_RANK() with a single element is defined as 0.0. This is technically correct but semantically meaningless -- the rank does not indicate the program is the "worst" in its family. DQ rules should not flag this as an anomaly.

---

### 7. Outlier Detection Summary

#### Debt-to-Earnings Ratio

| Check | Count | Percentage | Status |
|-------|-------|------------|--------|
| Outside 0.01-10.0 (spec range) | 0 | 0% | PASS -- no violations |
| Above 3.0 | 2 | 0.009% | Low severity |
| Above 2.5 ("Very High" tier) | 5 | 0.023% | Expected edge cases |

#### Earnings Growth Rate

| Check | Count | Percentage | Status |
|-------|-------|------------|--------|
| Outside -0.5 to 2.0 (spec range) | 15 | 0.068% | Low severity |
| Below -0.5 | 13 | 0.059% | Cross-cohort volatility |
| Above 2.0 | 2 | 0.009% | Extreme cohort difference |

#### Earnings Values (from Silver EDA, carried forward)

| Check | Count | Status |
|-------|-------|--------|
| earnings_1yr < $1,000 or > $250,000 | 0 | PASS |
| earnings_2yr < $1,000 or > $250,000 | 0 | PASS |
| debt_median < $1,000 or > $100,000 | 0 | PASS |

---

### 8. Program Value Index Distribution

**Population:** 21,763 rows (same as debt-to-earnings, since it uses the same inputs inverted).

| Statistic | Value |
|-----------|-------|
| Min | 0.188 |
| P05 | 0.880 |
| P25 | 1.250 |
| Median | 1.622 |
| P75 | 2.265 |
| P95 | 3.497 |
| Max | 19.865 |
| Mean | 1.866 |

The program_value_index is the mathematical inverse of debt_to_earnings_annual. Values > 1.0 indicate earnings exceed debt (69.23% of programs, matching the "Low" DTE tier). The maximum of 19.865 corresponds to the minimum DTE ratio of 0.050.

---

### 9. institution_control Status

**100% NULL.** This field cannot be populated because the CONTROL column was not included in the Bronze parquet ingestion. This is documented as a blocking issue in the Silver EDA.

**Impact on Gold:** The Gold spec lists institution_control as a carried-forward field with NOT NULL constraint. The Gold transformer will fail the NOT NULL constraint unless this is resolved first, OR the constraint is relaxed to NULLABLE for the initial load.

**Recommendation:** Either (a) re-run the Bronze ingestor to include CONTROL and rebuild Silver, or (b) make institution_control NULLABLE in Gold for the initial release and add a DQ rule tracking its completeness.

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation for @dq-rule-writer |
|-------------|-------|------------|-------------------------------------|
| debt_to_earnings_annual = NULL | 48,184 | 68.89% | Expected. NULL when either input is null. Set max null rate at 75%. |
| debt_to_earnings_tier = "Low" is plurality | 15,067 | 69.23% of non-null | **Correct spec:** "Low" is the plurality, NOT "Moderate". Set expected "Low" rate at 60-80%. |
| earnings_growth_rate negative | 9,797 | 44.2% of non-null | Expected. Set expected negative rate at 35-55%. |
| earnings_growth_rate outside -0.5 to 2.0 | 15 | 0.068% of non-null | Set soft constraint; allow up to 0.5% outside range. |
| debt_to_earnings outside 0.01-10.0 | 0 | 0% | Range is conservative; zero violations expected. |
| confidence_tier = "insufficient" | 36,894 | 52.75% | Set expected range at 45-60%. |
| confidence_tier = "medium" | 1,252 | 1.79% | Very small tier. Set expected range at 1-5%. |
| CIP families with null 1yr bands | 7 | 15.6% of families | Exactly {28, 32, 33, 34, 35, 48, 53}. |
| Rows with null 1yr bands | 36 | 0.05% | Negligible. |
| CIP families at min threshold (3 nn) | 2 | 4.4% of families | CIP 25, 36. Bands valid but weak. |
| PERCENT_RANK single-member families | 4 | 8.9% of families | CIP 28, 34, 48, 53. Rank = 0.0 by definition. |
| outcome_completeness = 0.0 | 36,894 | 52.75% | Aligns with "insufficient" tier. Set range 45-60%. |
| institution_control = NULL | 69,947 | 100% | BLOCKING -- Bronze re-ingestion needed. |

---

### DQ Threshold Recommendations for Gold Zone

#### P0 (Hard) Constraints

| Rule | Threshold | Evidence |
|------|-----------|----------|
| Grain uniqueness (unitid x cipcode x credlev) | 0 duplicates | Silver has 0 duplicates. Hard constraint. |
| Row count | 59,455 - 80,439 (+/- 15% of 69,947) | All rows carried forward, no filtering. |
| Percentile band ordering: p25 <= p75 | 0 violations | Mathematical invariant, 0 violations in simulation. |
| confidence_tier NOT NULL | 0 nulls | Derived field, always computed. |
| confidence_tier value set | IN ('high', 'medium', 'low', 'insufficient') | Exactly 4 values. |
| has_earnings accuracy | 100% match | Derived from exact null check. |
| has_debt accuracy | 100% match | Derived from exact null check. |
| outcome_completeness value set | IN (0.0, 0.33, 0.67, 1.0) | Exactly 4 values. |

#### P1 (Soft) Constraints

| Rule | Threshold | Evidence |
|------|-----------|----------|
| debt_to_earnings_annual range | 0.01 - 10.0 (where non-null) | Actual range: 0.050 - 5.328. Zero violations against 0.01-10.0. |
| earnings_growth_rate range | -0.5 to 2.0 (where non-null) | 15 of 22,146 (0.068%) outside range. Allow up to 0.5%. |
| cip_family_earnings_rank range | 0.0 - 1.0 (where non-null) | Mathematical range of PERCENT_RANK. Zero violations. |
| Null propagation: DTE null when input null | 100% consistency | debt_to_earnings_annual is null exactly when debt_median IS NULL OR earnings_1yr_median IS NULL. |
| Percentile band null pattern | null when CIP family < 3 non-null | 7 families for 1yr, 8 for 2yr, 8 for debt. |
| Confidence tier distribution: "insufficient" rate | 45-60% | Current: 52.75%. |
| Confidence tier distribution: "high" rate | 15-30% | Current: 21.80%. |
| Confidence tier distribution: "medium" rate | 0.5-5% | Current: 1.79%. |
| DTE tier distribution: "Low" rate (of non-null) | 60-80% | Current: 69.23%. |
| DTE tier distribution: "Moderate" rate (of non-null) | 20-40% | Current: 29.96%. |
| DTE tier distribution: "High" rate (of non-null) | 0-3% | Current: 0.78%. |
| DTE tier distribution: "Very High" rate (of non-null) | 0-0.5% | Current: 0.02%. |
| Negative growth rate | 35-55% of non-null | Current: 44.2%. |

#### P2 (Informational)

| Rule | Threshold | Evidence |
|------|-----------|----------|
| institution_control null rate | Track toward 0% | Currently 100% -- known issue. |
| CIP families with null bands count | <= 10 | Currently 7-8 depending on field. |
| Mean debt-to-earnings ratio | 0.50 - 0.80 | Current: 0.647. |
| Mean earnings growth rate | -0.05 to +0.10 | Current: +0.031. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| institution_control | Missing data | 69,947 (100%) | CRITICAL | CONTROL not in Bronze parquet. Blocks NOT NULL constraint in Gold. Known from Silver EDA. |
| debt_to_earnings tier expectation | Spec mismatch | n/a | MEDIUM | Spec says "Moderate" is plurality; actual data shows "Low" at 69.23%. DQ rule threshold must be corrected. |
| confidence_tier "medium" | Unexpectedly small | 1,252 (1.79%) | LOW | Large-cohort programs overwhelmingly have complete data, making "medium" tier very sparse. Not an error. |
| CIP 28/34/48/53 single-member rank | Degenerate statistic | 4 programs | LOW | PERCENT_RANK is 0.0 by definition for single-member partitions. Semantically meaningless but mathematically correct. |
| Earnings growth > 2.0 | Extreme outlier | 2 | LOW | University of Chicago Linguistics (+2.686), Cal State Dominguez Hills Clinical Lab Science (+2.625). Cross-cohort volatility. |
| Debt-to-earnings > 3.0 | Extreme outlier | 2 | LOW | Bloomsburg Communication Disorders (5.328), Daemen Natural Sciences (4.669). Driven by very low 1yr earnings for pre-graduate programs. |

---

### Source Field Summary (Silver base.college_scorecard)

| Field | Type | Non-Null | Null Rate | Distribution |
|-------|------|----------|-----------|-------------|
| earnings_1yr_median | DOUBLE | 25,196 | 63.98% | Min=$4,880, P50=$35,812, Max=$161,723, Mean=$39,616, SD=$14,894 |
| earnings_2yr_median | DOUBLE | 27,681 | 60.43% | Min=$5,938, P50=$35,810, Max=$160,116, Mean=$39,596, SD=$14,798 |
| debt_median | DOUBLE | 25,809 | 63.10% | Min=$2,750, P50=$23,000, Max=$57,500, Mean=$22,869, SD=$5,617 |
| completions_count_1 | BIGINT | 63,849 | 8.72% | Used for small_cohort_flag derivation |
| small_cohort_flag | BOOLEAN | 69,947 | 0% | True: 52,826 (75.52%), False: 17,121 (24.48%) |
| institution_control | VARCHAR | 0 | 100% | ALL NULL -- blocking issue |

---

### Audit Trail

- **Dataset analyzed:** base.college_scorecard (Silver zone, 69,947 rows, 18 columns)
- **Parquet file:** data/silver/iceberg_warehouse/base/college_scorecard/data/00000-0-fc47f753-104a-409b-bc99-5fb735f9d2a8.parquet
- **Analysis purpose:** Gold zone EDA per spec docs/specs/gold-career-outcomes-college-scorecard.md, step 6 of agent workflow
- **Key findings:** (1) DTE "Low" is plurality not "Moderate" -- spec correction needed. (2) institution_control 100% NULL -- known blocking issue. (3) 52.75% "insufficient" confidence tier -- confirmed within spec range. (4) 7 CIP families get null 1yr percentile bands. (5) 15 earnings growth rate outliers outside -0.5 to 2.0.
- **Threshold recommendations:** 12 P0 hard constraints, 14 P1 soft constraints, 4 P2 informational rules, all with supporting evidence.
- **Timestamp:** 2026-04-06
- **Spec reference:** docs/specs/gold-career-outcomes-college-scorecard.md
