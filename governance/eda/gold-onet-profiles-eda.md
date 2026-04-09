# EDA Report: Gold O*NET Profiles (Silver Source Data)

**Spec:** gold-onet-profiles
**Date:** 2026-04-08
**Agent:** @data-analyst
**Zone:** Gold (pre-implementation EDA on Silver sources)

---

## Source Tables Profiled

| Silver Table | Expected Rows | Actual Rows | Match |
|-------------|--------------|-------------|-------|
| base.onet_occupations | 798 | 798 | YES |
| base.onet_activity_profiles | 31,734 | 31,734 | YES |
| base.onet_context_profiles | 44,118 | 44,118 | YES |
| base.onet_career_transitions | 15,944 | 15,944 | YES |

All row counts match spec expectations exactly.

---

## Key Findings

### CRITICAL: Spec Element ID Errors for Human-Intensive Activities

The spec's human-intensive activity classification table (lines 108-124) contains **incorrect element_ids for 13 out of 14 activities**. Only `4.A.2.b.2` (Thinking Creatively) has the correct ID. The spec also duplicates `4.A.4.a.1` for two different activity names and references a nonexistent ID `4.A.1.e.2`.

**Corrected mapping (by matching element_name to actual data):**

| Correct Element ID | Activity Name | Spec's Wrong ID |
|-------------------|--------------|-----------------|
| 4.A.4.b.4 | Guiding, Directing, and Motivating Subordinates | 4.A.4.a.1 |
| 4.A.4.b.5 | Coaching and Developing Others | 4.A.4.a.2 |
| 4.A.4.a.7 | Resolving Conflicts and Negotiating with Others | 4.A.4.a.4 |
| 4.A.4.a.8 | Performing for or Working Directly with the Public | 4.A.4.a.5 |
| 4.A.4.a.4 | Establishing and Maintaining Interpersonal Relationships | 4.A.4.a.8 |
| 4.A.4.b.2 | Developing and Building Teams | 4.A.4.b.4 |
| 4.A.4.b.3 | Training and Teaching Others | 4.A.4.b.5 |
| 4.A.4.a.6 | Selling or Influencing Others | 4.A.4.b.6 |
| 4.A.4.b.1 | Coordinating the Work and Activities of Others | 4.A.4.a.1 (duplicate) |
| 4.A.2.b.2 | Thinking Creatively | 4.A.2.b.2 (CORRECT) |
| 4.A.2.b.1 | Making Decisions and Solving Problems | 4.A.2.b.4 |
| 4.A.3.a.1 | Performing General Physical Activities | 4.A.1.e.2 (nonexistent) |
| 4.A.3.a.2 | Handling and Moving Objects | 4.A.3.a.3 |
| 4.A.4.a.5 | Assisting and Caring for Others | 4.A.3.b.5 |

**The implementation MUST use the corrected IDs above.** The spec explicitly noted this was expected: "The exact element IDs and classification need to be validated against the actual Silver activity data."

### CRITICAL: HMN Score Range is Severely Compressed

Using the ratio-based formula from the spec (`hmn_score = 1 + 9 * human_ratio`), the simulated HMN scores span only **3.46 to 4.94** (std = 0.212) on a 1-10 scale. This means the entire workforce occupational spectrum fits into roughly 1.5 points.

- The compression is structural: 14 of 41 activities are human-intensive (34.1%), so the ratio is always near 0.27-0.44
- Even extreme occupations (Choreographers vs. Court Reporters) differ by only 1.5 points
- When rounded to integers, virtually all occupations would be 4 (with a few 3s and 5s)
- This defeats the purpose of a 1-10 scale and produces meaningless pentagon stats

**Recommendation for human decision:** Either (a) rescale the output using the actual observed min/max to fill the 1-10 range, or (b) change the formula to use absolute importance sums rather than ratios, or (c) adjust the number of human-intensive activities to create more spread. This is a formula design issue, not a data issue.

### Burnout Element Name Mismatches (Documentation Only)

The spec's burnout element table has name mismatches against the actual data. The element_ids are correct (confirmed by is_burnout_element flag in Silver), but the names in the spec table are wrong for 3 elements:

| Element ID | Spec Says | Data Says |
|-----------|----------|----------|
| 4.C.3.a.2.a | Responsibility for Others' Health and Safety | Impact of Decisions on Co-workers or Company Results |
| 4.C.3.b.7 | Responsibility for Outcomes and Results | Importance of Repeating Same Tasks |
| 4.C.3.d.4 | Importance of Repeating Same Tasks | Work Schedules |

The implementation should use `is_burnout_element = true` from Silver (which correctly identifies all 9 elements by ID) rather than hardcoding names.

### Burnout Score Distribution is Healthy

Unlike HMN, the burnout score has good spread: 3.48 to 8.32 (std = 0.778), covering about half the 1-10 range. This is usable for the pentagon display.

### Suppression Rates are Negligible

- Activity profiles: 1 row suppressed out of 31,734 (0.003%) -- SOC 27-3043 (Writers and Authors), element "Repairing and Maintaining Mechanical Equipment"
- Context profiles: 18 rows suppressed out of 44,118 (0.04%) -- spread across 7 SOCs, none involving burnout elements
- No SOC has activity suppression >= 5%. Only 1 SOC (29-1241, Ophthalmologists) has context suppression >= 5% (10.5%)
- Confidence tier impact: 773 SOCs will be "high", 1 SOC (29-1241) will be "medium", 24 SOCs will be "low" (partial)

---

## Field Profiles

### base.onet_occupations (798 rows)

#### bls_soc_code
- **Type:** STRING
- **Null Rate:** 0% (0 of 798)
- **Cardinality:** 798 distinct (100% unique)
- **Pattern:** XX-XXXX format, 7 characters

#### primary_title
- **Null Rate:** 0%
- **Cardinality:** 798 distinct

#### description
- **Null Rate:** 0%

#### multi_detail_flag
- **Distribution:** True = 76 (9.5%), False = 722 (90.5%)

#### data_completeness_tier
- **Distribution:** "full" = 774 (97.0%), "partial" = 24 (3.0%)

#### has_work_activities / has_work_context
- **Distribution:** True = 774, False = 24 (perfectly correlated -- all 24 partial SOCs lack both)

#### source_load_date
- **Value:** 2026-04-08 for all rows (single snapshot)

### base.onet_activity_profiles (31,734 rows)

#### element_id
- **Cardinality:** 41 distinct values
- **Distribution:** Exactly 774 rows per element (uniform -- every SOC has all 41 activities)

#### importance
- **Type:** DOUBLE
- **Null Rate:** 0%
- **Range:** 1.000 to 4.990
- **Distribution:** mean=3.132, std=0.850, p25=2.540, p50=3.200, p75=3.790
- **Note:** Maximum is 4.99, not 5.00. Scale is 1-5 but no value reaches exactly 5.

#### is_high_importance
- **Distribution:** True = 11,822 (37.3%), False = 19,912 (62.7%)

#### suppress_flag
- **Distribution:** True = 1 (0.003%), False = 31,733

#### Activities by Mean Importance (top 5):
1. 4.A.1.a.1 | Getting Information | avg=4.198
2. 4.A.4.a.2 | Communicating with Supervisors, Peers, or Subordinates | avg=3.976
3. 4.A.2.b.1 | Making Decisions and Solving Problems | avg=3.950
4. 4.A.1.b.1 | Identifying Objects, Actions, and Events | avg=3.828
5. 4.A.2.b.3 | Updating and Using Relevant Knowledge | avg=3.744

#### Activities by Mean Importance (bottom 5):
1. 4.A.3.b.2 | Drafting, Laying Out, and Specifying Technical Devices | avg=2.080
2. 4.A.4.c.2 | Staffing Organizational Units | avg=2.132
3. 4.A.3.b.5 | Repairing and Maintaining Electronic Equipment | avg=2.140
4. 4.A.3.b.4 | Repairing and Maintaining Mechanical Equipment | avg=2.266
5. 4.A.4.a.6 | Selling or Influencing Others | avg=2.426

### base.onet_context_profiles (44,118 rows)

#### element_id
- **Cardinality:** 57 distinct values
- **Distribution:** Exactly 774 rows per element (uniform)

#### scale_id
- **Distribution:** "CX" = 42,570 (55 elements), "CT" = 1,548 (2 elements)

#### context_value
- **Null Rate:** 0%
- **Range:** 1.000 to 5.000

#### is_burnout_element
- **Distribution:** True = 6,966 (15.8%), False = 37,152 (84.2%)
- 6,966 = 774 SOCs x 9 burnout elements (exact)

#### suppress_flag
- **Distribution:** True = 18 (0.04%), False = 44,100
- None of the suppressed rows are burnout elements

### base.onet_career_transitions (15,944 rows)

#### bls_soc_code (source)
- **Cardinality:** 798 distinct (all occupations have transitions, including partial-data ones)

#### related_bls_soc_code
- **Cardinality:** 796 distinct (2 SOCs never appear as a "related" target)

#### best_index
- **Range:** 1 to 20
- **Distribution:** Roughly uniform at ~780-860 rows per index value
- idx 1: 858, idx 2: 833, ... idx 20: 773

#### relatedness_tier
- Primary-Short (idx 1-5): 4,134 rows (25.9%)
- Primary-Long (idx 6-10): 3,938 rows (24.7%)
- Supplemental (idx 11-20): 7,872 rows (49.4%)

#### is_primary
- True = 8,072 (50.6%), False = 7,872 (49.4%)

#### relationship_type
- "similarity" = 15,944 (100%)

#### Self-references: 0 (confirmed)
#### Grain uniqueness: 0 duplicates (bls_soc_code x related_bls_soc_code is unique)
#### Referential integrity: All source and related SOCs exist in base.onet_occupations

#### Transitions per source SOC
- min=14, max=75, avg=20.0, median=20.0
- Most SOCs have exactly 20 transitions; some have fewer

---

## Simulated Score Distributions

### HMN Score (using corrected element IDs)

| Metric | Value |
|--------|-------|
| Count | 774 |
| Min | 3.464 |
| Max | 4.940 |
| Mean | 4.050 |
| Std Dev | 0.212 |
| P05 | 3.709 |
| P25 | 3.898 |
| P50 | 4.052 |
| P75 | 4.185 |
| P95 | 4.399 |

**Histogram:**
- 3.0-3.5: 2 occupations
- 3.5-4.0: 316 occupations
- 4.0-4.5: 439 occupations
- 4.5-5.0: 17 occupations

**Sample occupations:**
- Choreographers: 4.940 (highest)
- Actors: 4.786
- Registered Nurses: 4.257
- Software Developers: 3.647
- Court Reporters: 3.464 (lowest)

### Burnout Score

| Metric | Value |
|--------|-------|
| Count | 774 |
| Min | 3.475 |
| Max | 8.315 |
| Mean | 5.999 |
| Std Dev | 0.778 |
| P05 | 4.708 |
| P25 | 5.446 |
| P50 | 6.019 |
| P75 | 6.554 |
| P95 | 7.249 |

**Sample occupations:**
- Oil/Gas Service Unit Operators: 8.315 (highest)
- Machinists: 6.847
- Registered Nurses: 6.465
- Software Developers: 4.803
- Religious Activities Directors: 3.475 (lowest)

### Burnout Element Distributions (the 9 inputs)

| Element ID | Name | Scale | Mean | Std | Range |
|-----------|------|-------|------|-----|-------|
| 4.C.3.d.1 | Time Pressure | CX | 3.847 | 0.508 | 1.67-5.00 |
| 4.C.3.d.8 | Duration of Typical Work Week | CT | 2.273 | 0.390 | 1.00-3.00 |
| 4.C.3.a.1 | Consequence of Error | CX | 3.015 | 0.745 | 1.33-4.97 |
| 4.C.3.d.3 | Pace Determined by Speed of Equipment | CX | 1.985 | 0.947 | 1.00-4.76 |
| 4.C.3.a.2.b | Frequency of Decision Making | CX | 3.792 | 0.599 | 1.47-5.00 |
| 4.C.3.b.4 | Importance of Being Exact or Accurate | CX | 4.164 | 0.452 | 2.32-5.00 |
| 4.C.3.b.7 | Importance of Repeating Same Tasks | CX | 3.266 | 0.648 | 1.42-4.92 |
| 4.C.3.d.4 | Work Schedules | CT | 1.305 | 0.257 | 1.00-2.50 |
| 4.C.3.a.2.a | Impact of Decisions on Co-workers | CX | 3.772 | 0.517 | 1.96-4.99 |

---

## Cross-Table Coverage

| Coverage Check | Count |
|---------------|-------|
| Total occupations | 798 |
| Occupations with activity profiles | 774 |
| Occupations with context profiles | 774 |
| Occupations with both profiles | 774 |
| Occupations with neither profile | 24 |
| Occupations with career transitions | 798 |

The 24 partial-data occupations have NEITHER activity NOR context data (perfectly correlated). They WILL have career transitions. Their HMN and Burnout scores will be null.

---

## Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| HMN score null (partial occupations) | 24 | 3.0% | DQ rule: exactly 24 null HMN scores expected |
| Burnout score null (partial occupations) | 24 | 3.0% | DQ rule: exactly 24 null burnout scores expected |
| HMN score range 3.46-4.94 | 774 | 100% of scored | DQ rule: hmn_score BETWEEN 1.0 AND 10.0 (allows headroom if formula changes) |
| Burnout score range 3.48-8.32 | 774 | 100% of scored | DQ rule: burnout_score BETWEEN 1.0 AND 10.0 |
| Activity suppress % >= 5% per SOC | 0 | 0% | No SOC triggers "medium" confidence from activity suppression |
| Context suppress % >= 5% per SOC | 1 | 0.13% | SOC 29-1241 (10.5% suppressed) -> confidence "medium" |
| Confidence "high" | 773 | 96.9% | Expected majority |
| Confidence "medium" | 1 | 0.13% | Only 29-1241 |
| Confidence "low" | 24 | 3.0% | All partial-data occupations |
| Career transition self-references | 0 | 0% | DQ rule: zero self-references |
| Career transition orphan joins | 0 | 0% | All SOCs in transitions exist in occupations |
| Career transition grain duplicates | 0 | 0% | DQ rule: zero duplicates on composite key |

---

## Anomalies

| Field/Table | Type | Count | Severity | Details |
|------------|------|-------|----------|---------|
| HMN score | Compressed range | 774 | HIGH | Entire score range is 3.46-4.94 (1.5 points of 10). Formula produces effectively meaningless differentiation. Requires human decision. |
| Activity element_ids | Spec error | 13 of 14 | HIGH | Spec's human-intensive classification table has wrong element_ids. Corrected mapping provided above. |
| Burnout element names | Spec documentation error | 3 of 9 | MEDIUM | Element names in spec don't match data. IDs are correct. Implementation should use is_burnout_element flag. |
| Importance max | Value cap | 774 SOCs | LOW | Max importance is 4.99, never exactly 5.00. This is normal O*NET data behavior, not an error. |
| Transition count variation | Non-uniform | ~798 SOCs | LOW | Most SOCs have 20 transitions but range is 14-75. Not an error -- some occupations have fewer similar occupations. |

---

## Recommendations for Downstream Agents

### For @dq-rule-writer
1. HMN score range DQ rule should allow 1.0-10.0 (not the current compressed range) in case the formula is adjusted
2. Burnout score range DQ rule: 1.0-10.0
3. Null count for both scores: exactly 24
4. Confidence tier distribution: 773 high, 1 medium, 24 low
5. Career transitions: 0 self-references, 0 grain duplicates, 15,944 rows
6. Suppression percentage thresholds: all activities < 5%, 1 context SOC >= 5%
7. All 774 scored occupations should have exactly 41 activity rows and 57 context rows in source

### For @primary-agent (implementer)
1. Use the **corrected element ID mapping** above for human-intensive activities, NOT the spec's table
2. Use `is_burnout_element = true` from Silver context profiles to identify burnout elements, NOT hardcoded names
3. The HMN score compression issue needs human decision before implementation. Flag this.
4. Suppression rates are so low that suppress_pct fields will be 0.000 for almost all rows

### For human approval
1. **HMN formula redesign needed** -- the ratio-based approach produces a 1.5-point range on a 10-point scale. Options: (a) rescale using observed min/max, (b) use absolute importance sums, (c) reclassify activities. This is the most important open decision.
