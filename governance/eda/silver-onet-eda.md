## EDA Report: Silver O*NET Base Tables
**Source:** Bronze tables raw.onet_occupations, raw.onet_work_activities, raw.onet_work_context, raw.onet_related_occupations
**Date:** 2026-04-08
**Agent:** @data-analyst
**Spec:** docs/specs/silver-base-onet.md
**Logical Model:** governance/models/silver-base-onet-logical.md

### Key Findings

- **The spec overestimates the Silver occupation count.** The spec says ~867 Silver rows after excluding 93 "All Other"/Military codes. In reality, at the BLS SOC level, only 69 BLS SOCs are truly empty (zero child data). The other 24 of the 93 zero-data O*NET codes share a BLS prefix with detailed codes that DO have data. Expected Silver onet_occupations: **798 rows**, not ~867.
- **76 BLS SOCs have multiple O*NET detail codes**, confirmed. The max is 10 (15-1299). 708 BLS SOCs with WA/WC data are 1:1 mappings; 66 require multi-detail averaging.
- **Work Activities: exactly 41 distinct IM elements across 894 O*NET SOCs** (774 BLS SOCs). Every occupation has all 41 activities. Only 1 row on IM scale has recommend_suppress = "Y" (effectively 0%).
- **Work Context: exactly 57 CX/CT elements across 894 O*NET SOCs** (774 BLS SOCs). 55 CX elements (range 1.0-5.0) and 2 CT elements (range 1.0-3.0). 18 rows have suppress = "Y" on CX scale (0.04%). Zero suppress on CT.
- **CRITICAL: 4 of the 9 proposed burnout element IDs are wrong.** The spec maps element names to incorrect IDs. Two IDs (4.C.3.d.5, 4.C.3.d.7) do not exist in the data at all. Two others (4.C.3.b.2, 4.C.3.d.4) map to different element names than the spec claims. One element name ("Responsibility for Outcomes and Results") does not exist in O*NET. See the corrected mapping below.
- **343 self-references emerge** when Related Occupations are aggregated to BLS level (0 at O*NET level). These must be excluded from Silver.
- **15,944 career transition pairs remain** after BLS aggregation, self-reference removal, and exclusion of "none"-tier SOCs. The spec estimated ~16,000-18,000.
- **Data completeness: 774 "full" BLS SOCs, 24 "partial", 69 "none".** The spec said 29 partial. At BLS level the number is 24 because some partial O*NET codes share BLS SOCs with full-data codes. All 24 partial occupations have Tasks + Related but lack Work Activities and Work Context.
- **WA and WC detail counts are perfectly synchronized** -- no BLS SOC has a different number of O*NET detail codes in Work Activities vs Work Context.

---

### CRITICAL: Corrected Burnout Element Mapping

The spec proposes 9 burnout-relevant element IDs. **4 are incorrect and 1 element name does not exist.** The corrected mapping (8 validated elements):

| Spec Element ID | Spec Element Name | Actual Element ID | Actual Element Name | Status |
|----------------|-------------------|-------------------|---------------------|--------|
| 4.C.3.d.1 | Time Pressure | 4.C.3.d.1 | Time Pressure | CORRECT |
| 4.C.3.d.8 | Duration of Typical Work Week | 4.C.3.d.8 | Duration of Typical Work Week | CORRECT |
| 4.C.3.a.1 | Consequence of Error | 4.C.3.a.1 | Consequence of Error | CORRECT |
| 4.C.3.d.3 | Pace Determined by Speed of Equipment | 4.C.3.d.3 | Pace Determined by Speed of Equipment | CORRECT |
| 4.C.3.b.2 | Frequency of Decision Making | **4.C.3.a.2.b** | Frequency of Decision Making | **WRONG ID** -- actual is 4.C.3.a.2.b (CX), not 4.C.3.b.2 (which is "Degree of Automation") |
| 4.C.3.d.4 | Importance of Being Exact or Accurate | **4.C.3.b.4** | Importance of Being Exact or Accurate | **WRONG ID** -- actual is 4.C.3.b.4 (CX), not 4.C.3.d.4 (which is "Work Schedules", CT scale) |
| 4.C.3.d.5 | Importance of Repeating Same Tasks | **4.C.3.b.7** | Importance of Repeating Same Tasks | **WRONG ID** -- actual is 4.C.3.b.7 (CX); 4.C.3.d.5 does not exist |
| 4.C.3.b.7 | Responsibility for Outcomes and Results | **NONE** | Does not exist in O*NET | **ELEMENT NOT FOUND** -- no element with this name exists. Closest match: 4.C.3.a.2.a "Impact of Decisions on Co-workers or Company Results" |
| 4.C.3.d.7 | Work Schedules | **4.C.3.d.4** | Work Schedules | **WRONG ID** -- actual is 4.C.3.d.4 (CT scale); 4.C.3.d.7 does not exist |

**Recommended corrected burnout element list (9 elements):**

| # | Element ID | Element Name | Scale | Mean | Range | Burnout Signal |
|---|-----------|-------------|-------|------|-------|---------------|
| 1 | 4.C.3.d.1 | Time Pressure | CX | 3.84 | 1.67-5.00 | Deadline stress |
| 2 | 4.C.3.d.8 | Duration of Typical Work Week | CT | 2.30 | 1.00-3.00 | Long hours |
| 3 | 4.C.3.a.1 | Consequence of Error | CX | 3.03 | 1.33-4.97 | Mistake stress |
| 4 | 4.C.3.d.3 | Pace Determined by Speed of Equipment | CX | 1.95 | 1.00-4.76 | Pace autonomy |
| 5 | 4.C.3.a.2.b | Frequency of Decision Making | CX | -- | -- | Cognitive load |
| 6 | 4.C.3.b.4 | Importance of Being Exact or Accurate | CX | -- | -- | Precision pressure |
| 7 | 4.C.3.b.7 | Importance of Repeating Same Tasks | CX | 3.26 | 1.42-4.92 | Monotony |
| 8 | 4.C.3.d.4 | Work Schedules | CT | 1.30 | 1.00-2.50 | Schedule disruption |
| 9 | 4.C.3.a.2.a | Impact of Decisions on Co-workers or Company Results | CX | -- | -- | Responsibility pressure (replaces nonexistent "Responsibility for Outcomes") |

---

### Table 1: base.onet_occupations

**Expected Row Count:** 798 (not ~867 as spec states)

#### SOC Code Distribution
- 1,016 O*NET-SOC codes in Bronze
- 867 end in .00 (base BLS occupations), 149 have non-.00 suffixes
- 867 unique BLS SOC codes derivable by truncation
- 76 BLS SOCs have multiple O*NET detail codes (confirmed)

#### Multi-Detail BLS SOC Breakdown
| Detail Count | BLS SOC Count |
|-------------|---------------|
| 1 | 791 |
| 2 | 43 |
| 3 | 18 |
| 4 | 6 |
| 5 | 3 |
| 6 | 1 |
| 7 | 3 |
| 9 | 1 |
| 10 | 1 |

Top multi-detail examples: 15-1299 (10 details), 17-2199 (9 details), 13-1041/29-1229/11-9199 (7 each).

#### "All Other"/Military Exclusion
- 93 O*NET-SOC codes with zero data in all child tables (74 "All Other" + 19 Military)
- At BLS level, 24 of these 93 codes share a 6-digit prefix with O*NET detail codes that DO have data
- Only 69 BLS SOCs are truly empty at BLS granularity
- **Implementation note:** The exclusion logic must work at BLS level. If a .00 "All Other" code has zero data but its BLS prefix has .01/.02 codes with data, the BLS SOC stays in Silver.

#### Data Completeness Tier (at BLS SOC level)
| Tier | BLS SOC Count | Pattern |
|------|---------------|---------|
| full | 774 | All 4 child tables present (WA + WC + RO + TS) |
| partial | 24 | Tasks + Related only, no Work Activities or Work Context |
| none | 69 | Zero data -- excluded from Silver |

All 24 partial-data occupations have has_work_activities=False, has_work_context=False, has_related=True, has_tasks=True. None have the reverse pattern. These occupations WILL be in base.onet_occupations but will NOT appear in base.onet_activity_profiles or base.onet_context_profiles.

#### Load Date
All tables have a single load_date: 2026-04-08.

---

### Table 2: base.onet_activity_profiles

**Expected Row Count:** 774 x 41 = 31,734

#### IM Scale Statistics
| Metric | Value |
|--------|-------|
| Total IM rows in Bronze | 36,654 |
| Distinct O*NET SOCs | 894 |
| Distinct BLS SOCs | 774 |
| Distinct elements | 41 |
| min | 1.00 |
| p05 | 1.59 |
| p25 | 2.55 |
| median | 3.23 |
| mean | 3.15 |
| p75 | 3.82 |
| p95 | 4.43 |
| max | 4.99 |
| stdev | 0.86 |

**Note:** Max observed IM value is 4.99, not 5.0. The 1.0-5.0 DQ range is correct (scale allows 5.0, it just doesn't appear in current data).

#### is_high_importance Threshold Validation
The spec proposes importance >= 3.5 as the threshold.

| Bucket | Count | Percentage |
|--------|-------|------------|
| 1.0-1.99 | 4,159 | 11.3% |
| 2.0-2.49 | 4,295 | 11.7% |
| 2.5-2.99 | 6,338 | 17.3% |
| 3.0-3.49 | 7,730 | 21.1% |
| 3.5-3.99 | 7,396 | 20.2% |
| 4.0-4.49 | 5,350 | 14.6% |
| 4.5-5.0 | 1,386 | 3.8% |

**38.6% of IM values are >= 3.5** (spec estimated ~40%). The threshold is well-calibrated.

#### recommend_suppress on IM Scale
| Value | Count | Percentage |
|-------|-------|------------|
| N | 28,002 | 76.4% |
| n/a | 8,651 | 23.6% |
| Y | 1 | 0.003% |

After BLS aggregation: only 1 BLS SOC x element pair has suppress_flag=True. This is negligible.

#### Multi-Detail Averaging
| Detail Count | BLS SOCs (with WA data) |
|-------------|------------------------|
| 1 | 708 |
| 2 | 42 |
| 3 | 10 |
| 4 | 7 |
| 5 | 1 |
| 6 | 4 |
| 7 | 1 |
| 8 | 1 |

66 BLS SOCs require multi-detail averaging. Detail counts are identical between WA and WC (perfect sync).

---

### Table 3: base.onet_context_profiles

**Expected Row Count:** 774 x 57 = 44,118

#### CX/CT Scale Statistics
| Scale | Rows | Elements | SOCs | Min | Max | Mean | Median | Stdev |
|-------|------|----------|------|-----|-----|------|--------|-------|
| CX | 49,170 | 55 | 894 | 1.00 | 5.00 | 2.789 | 2.800 | 1.215 |
| CT | 1,788 | 2 | 894 | 1.00 | 3.00 | 1.799 | 1.700 | 0.598 |
| **Total** | **50,958** | **57** | **894** | | | | | |

CX/CT represent 17.1% of Bronze Work Context rows (50,958 of 297,676). The CXP/CTP exclusion removes 82.9% of rows as expected.

#### CX Value Distribution
| Bucket | Count | Percentage |
|--------|-------|------------|
| 1.0-1.99 | 15,969 | 32.5% |
| 2.0-2.99 | 10,797 | 22.0% |
| 3.0-3.99 | 11,994 | 24.4% |
| 4.0-5.0 | 10,410 | 21.2% |

Fairly uniform distribution, slightly left-skewed. Many occupations score low on environmental hazard/physical demand dimensions.

#### CT Scale Distribution
CT values are continuous on 1.0-3.0 (not just integers). The two CT elements are "Work Schedules" (mean 1.30, most occupations regular schedule) and "Duration of Typical Work Week" (mean 2.30, most occupations near or above 40 hours).

#### recommend_suppress on CX/CT
| Scale | N | n/a | Y | Y% |
|-------|---|-----|---|-----|
| CX | 37,547 | 11,605 | 18 | 0.04% |
| CT | 1,366 | 422 | 0 | 0.00% |

After BLS aggregation: 18 pairs have suppress_flag=True. All on CX scale.

#### 16 Sparse Occupations
16 O*NET-SOC codes have only 57 Work Context rows (CX/CT only, no CXP/CTP). Since Silver uses CX/CT only, these occupations are not disadvantaged -- they have the same 57 elements per occupation as all others. No Silver impact.

---

### Table 4: base.onet_career_transitions

**Expected Row Count:** 15,944

#### BLS-Level Aggregation Impact
| Step | Count |
|------|-------|
| Raw Bronze rows | 18,460 |
| BLS-level self-references removed | -343 |
| Remaining rows | 18,117 |
| Duplicate BLS pairs deduplicated (keep best_index) | -2,173 |
| Unique BLS pairs (excl self-ref) | 15,944 |
| After excluding "none"-tier SOCs | 15,944 (no change -- none-tier SOCs already absent from Related Occupations) |

#### Self-References
- 0 self-references at O*NET-SOC level
- 343 self-references emerge after BLS truncation (when two O*NET details of the same BLS SOC relate to each other)
- All self-references have indexes in the range 1-10 (Primary-Short and Primary-Long tiers)

#### Tier Distribution (after BLS dedup, excl self-ref)
| Tier | Count | Percentage |
|------|-------|------------|
| Primary-Short (1-5) | 4,134 | 25.9% |
| Primary-Long (6-10) | 3,938 | 24.7% |
| Supplemental (11-20) | 7,872 | 49.4% |

#### Relationships per Source BLS SOC
| Metric | Value |
|--------|-------|
| Min | 14 |
| Max | 75 |
| Mean | 20.0 |
| Median | 20.0 |

798 distinct source BLS SOCs. Most have exactly 20 relationships; multi-detail BLS SOCs can have more (up to 75) due to combining relationships from multiple O*NET detail codes.

#### BLS-Level Deduplication Detail
1,326 BLS SOC pairs appear multiple times in raw data (from different O*NET detail pairings). The MIN(related_index) strategy selects the best relationship for each pair.

---

### Cross-Table Referential Integrity

All raw tables share the same 894 O*NET SOCs for Work Activities and Work Context (perfectly synchronized). Tasks and Related Occupations have 923 SOCs (29 more occupations with partial data).

At BLS level:
- 774 BLS SOCs have full data (all 4 child tables)
- 24 BLS SOCs have partial data (Tasks + Related only)
- 69 BLS SOCs have zero data (excluded from Silver)

After Silver transformation:
- All bls_soc_codes in activity_profiles will exist in onet_occupations (774 of 798)
- All bls_soc_codes in context_profiles will exist in onet_occupations (774 of 798)
- All bls_soc_codes in career_transitions (both columns) will exist in onet_occupations (798 of 798 for source, 798 of 798 for target -- the "none" SOCs have no related occupations)

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Silver onet_occupations row count | 798 | -- | Spec says ~867; actual is 798 after BLS-level exclusion. Update spec estimate. |
| multi_detail_flag = True | 76 BLS SOCs | 9.5% of 798 | DQ rule: exactly 76 (confirmed from data) |
| data_completeness_tier = "partial" | 24 BLS SOCs | 3.0% of 798 | DQ rule: < 5% partial allowed |
| data_completeness_tier = "full" | 774 BLS SOCs | 97.0% of 798 | Expect majority full |
| IM recommend_suppress = "Y" | 1 of 36,654 | 0.003% | DQ rule: < 1% suppress on IM |
| CX recommend_suppress = "Y" | 18 of 49,170 | 0.04% | DQ rule: < 1% suppress on CX/CT |
| IM value range | 1.00-4.99 | -- | DQ rule: [1.0, 5.0] |
| CX value range | 1.00-5.00 | -- | DQ rule: [1.0, 5.0] |
| CT value range | 1.00-3.00 | -- | DQ rule: [1.0, 3.0] |
| BLS-level self-references in transitions | 343 raw rows | 1.9% of 18,460 | Must be excluded; DQ rule: 0 self-refs |
| Transition dedup removes | 2,173 rows | 11.8% of non-self-ref | Expected from multi-detail BLS SOCs |
| Career transitions final count | 15,944 pairs | -- | DQ rule: row count ~15,944 +/- 5% |
| is_high_importance >= 3.5 | 38.6% of IM | -- | Well-calibrated threshold |
| Burnout element IDs wrong in spec | 4 of 9 | 44% | CRITICAL: use corrected IDs |

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| Burnout element IDs | Incorrect spec | 4 wrong + 1 nonexistent | CRITICAL | See corrected mapping above. 4.C.3.d.5 and 4.C.3.d.7 do not exist. 4.C.3.b.2 and 4.C.3.d.4 map to wrong elements. "Responsibility for Outcomes and Results" is not an O*NET element. |
| Silver onet_occupations count | Spec deviation | 69 fewer than expected | HIGH | Spec estimates ~867 but only 798 BLS SOCs have any child data. The 93 "All Other"/Military figure is at O*NET level; at BLS level only 69 are truly empty. |
| Partial data occupations | Count deviation | 24 not 29 | MEDIUM | At BLS level, 24 partial (not 29 as in spec). Some partial O*NET codes share BLS SOCs with full-data codes, promoting them to "full" at BLS level. |
| Career transition count | Within spec range | 15,944 | LOW | Within the spec's 16,000-18,000 estimate (slightly below). |
