## EDA Report: base.karpathy_ai_exposure (Silver)
**Source:** bronze.karpathy_ai_exposure (342 rows) -> Silver transformation with SOC expansion
**Date:** 2026-04-09
**Agent:** @data-analyst
**Bronze Record Count:** 342
**Predicted Silver Record Count:** 406 (after expansion and accounting for broad-to-broad matches)
**Field Count:** 11 (per physical model)

---

### Key Findings

- **Predicted Silver row count is ~406, within the physical model's 400-700 range.** Bronze has 342 rows. SOC broad code expansion adds 110 rows (40 broad codes expand to 110 detailed BLS codes). 4 broad codes match BLS exactly as broad-to-broad. 6 broad codes have no BLS match at all. Null SOC remains at 52 rows. Title matching may resolve ~28 of those 52, leaving ~24 unresolved. No duplicate SOC codes arise from expansion (zero overlaps between direct codes and expanded codes).
- **SOC code composition: 240 detailed direct (58.3%), 110 broad expansion (26.7%), 10 broad kept-as-is (2.4%), 52 null (12.6%).** The spec's predicted distribution of ~70% direct / ~15% broad_expansion / ~10% title_match / ~5% unresolved is inaccurate. Actual will be closer to 58% direct / 27% broad_expansion / 7% title_match / 8% unresolved (including 6 unmatched broad codes counted as unresolved).
- **4 of 10 "unmatched" broad codes actually exist as broad codes in BLS OOH.** SOC codes 13-2020, 29-2010, 31-1120, and 39-7010 appear in BLS OOH as broad codes. The Silver transformer must handle broad-to-broad exact matches -- these should be soc_resolved_method = "direct" with bls_match = true, NOT expanded. The remaining 6 broad codes (19-5000, 37-3000, 39-2000, 41-4000, 43-6000, 53-5000) have no BLS match of any kind.
- **Zero duplicate SOC codes after expansion.** No detailed SOC code appears in both the direct-match set and the broad-expansion set. No two broad codes expand to overlapping detailed codes. The deduplication logic in the physical model will not be triggered by current data, but should remain as defensive code.
- **Title matching for null-SOC rows yields ~28 resolvable occupations out of 52.** 0 exact case-insensitive matches. 36 partial matches found, but many are 1:N (one Karpathy title maps to multiple BLS occupations). Estimated 28 unique Karpathy slugs can be title-matched, potentially producing more rows if one slug matches multiple BLS codes. 24 occupations are fully unresolvable, including "Financial analysts", "Physicians and surgeons", "Top executives", and "Military careers".
- **Exposure scores are unchanged from Bronze.** Range 1-10, mean 5.31, median 5.0. No mutation risk since Silver is a passthrough. The physical model CHECK constraint of 0-10 is correct (0 is valid per methodology, just not present in current data).
- **Rationale lengths all pass the physical model's >= 250 char CHECK.** Minimum is 297 chars, maximum is 587 chars. The 250-char threshold has 47 chars of headroom above the shortest observed value.
- **BLS match rate prediction: ~87% of non-null SOC rows.** 240 direct matches + 110 expanded matches + 4 broad-to-broad matches = 354 BLS-matched rows. Out of ~360 non-null SOC rows (after title matching), that is ~98%. However, the 6 unmatched broad codes and any failed title matches reduce this. Conservative estimate: 90-95% bls_match = true among non-null SOC rows. This exceeds the physical model's >= 90% threshold.

---

### SOC Code Pattern Analysis

| SOC Type | Bronze Count | Bronze % | Silver Predicted Count | Silver % | soc_resolved_method |
|----------|-------------|---------|----------------------|---------|---------------------|
| Detailed, direct BLS match | 240 | 70.2% | 240 | ~59% | direct |
| Broad, expandable to detailed | 40 | 11.7% | 110 (expanded) | ~27% | broad_expansion |
| Broad, exact BLS match (broad-to-broad) | 4 | 1.2% | 4 | ~1% | direct |
| Broad, no BLS match | 6 | 1.8% | 6 | ~1.5% | unresolved (bls_match=false) |
| Null SOC, title-matchable | ~28 | ~8.2% | ~28+ | ~7% | title_match |
| Null SOC, unresolvable | ~24 | ~7.0% | ~24 | ~6% | unresolved |
| **Total** | **342** | **100%** | **~412** | **100%** | |

Note: The 40 expandable broad codes produce 110 detailed rows (average 2.75 detailed codes per broad code; range 2-6). The largest expansion is SOC 35-2010 "Cooks" which fans out to 6 detailed codes (35-2011 through 35-2019).

---

### Broad Code Expansion Detail

The 40 expandable broad codes and their expansion counts:

| Broad Code | Occupation Title | Score | Detailed Codes | Expansion Count |
|-----------|-----------------|-------|----------------|-----------------|
| 35-2010 | Cooks | 3 | 35-2011..35-2019 | 6 |
| 29-1020 | Dentists | 3 | 29-1021..29-1029 | 5 |
| 25-2050 | Special education teachers | 5 | 25-2051..25-2059 | 5 |
| 45-4020 | Logging workers | 2 | 45-4021..45-4029 | 4 |
| 47-2040 | Flooring installers and tile and stone setters | 1 | 47-2041..47-2044 | 4 |
| 17-3010 | Drafters | 9 | 17-3011..17-3019 | 4 |
| 27-4010 | Broadcast, sound, and video technicians | 6 | 27-4011..27-4015 | 4 |
| 19-3030 | Psychologists | 6 | 19-3032..19-3039 | 4 |
| 21-1020 | Social workers | 4 | 21-1021..21-1029 | 4 |
| (31 more with 2-3 expansions each) | | | | |

**Unmatched broad codes (no BLS detailed or broad match):**

| Broad Code | Occupation Title | Score | Notes |
|-----------|-----------------|-------|-------|
| 19-5000 | Occupational health and safety specialists | 5 | Major group level code |
| 37-3000 | Grounds maintenance workers | 1 | Major group level code |
| 39-2000 | Animal care and service workers | 2 | Major group level code |
| 41-4000 | Wholesale and manufacturing sales reps | 7 | Major group level code |
| 43-6000 | Secretaries and administrative assistants | 8 | Major group level code |
| 53-5000 | Water transportation workers | 3 | Major group level code |

These 6 codes use 4-digit SOC patterns (XX-X000) that are higher-level groupings, not the standard XX-XXX0 broad codes. They will carry forward with bls_match = false and soc_resolved_method = "unresolved".

---

### Title Matching Analysis (Null-SOC Resolution)

**52 Bronze rows have null SOC codes.** Title matching against base.bls_ooh.occupation_title yields:

- **0 exact case-insensitive matches.** Karpathy uses composite titles (e.g., "Advertising, promotions, and marketing managers") while BLS uses specific titles ("Marketing managers").
- **36 partial matches across ~28 unique slugs.** Many Karpathy titles contain BLS titles as substrings, or vice versa. Examples:
  - "Nurse anesthetists, nurse midwives, and nurse practitioners" -> 3 BLS matches (29-1151, 29-1161, 29-1171)
  - "Machinists and tool and die makers" -> 2 BLS matches (51-4041, 51-4111)
  - "Bus drivers" -> 2 BLS matches (53-3051, 53-3052)
- **24 fully unresolvable occupations.** No title match of any kind. Notable examples: "Financial analysts" (SOC 13-2051 exists in BLS but the exact string doesn't match via substring), "Physicians and surgeons", "Top executives", "Military careers".

**Implementation note:** Title matching will be imprecise. Partial/substring matching produces false positives (e.g., "Retail sales workers" partially matches "First-line supervisors of non-retail sales workers"). The transformer should use conservative matching logic and flag ambiguous matches for manual review rather than auto-resolving.

---

### Field Profiles (Silver-Relevant)

#### exposure_score
- **Type:** INTEGER (passthrough from Bronze)
- **Range:** 1-10 (no zeros in current data; 0 is valid per methodology)
- **Distribution:** Mean 5.31, Median 5.0, StdDev 2.26
- **By predicted soc_resolved_method:**
  - Direct: mean 5.63, median 6.0 (higher exposure -- more office/digital occupations)
  - Broad expansion: mean 4.44, median 4.0 (lower -- more physical/trade occupations)
  - Null SOC: mean 4.71, median 4.0 (lower -- similar to broad codes)
- **Silver impact:** Score is passthrough. After expansion, the 110 expanded rows inherit the broad code's score, so the Silver-level mean will shift downward slightly (more low-score rows from trade/physical occupation expansions).

#### rationale
- **Type:** VARCHAR (passthrough from Bronze)
- **Length stats:** Min 297, Max 587, Mean 411.8, Median 408.5, StdDev 47.8
- **Percentiles:** P5=342, P10=357, P25=378, P75=440, P90=471, P95=499
- **Physical model CHECK >= 250:** All 342 rows pass. Minimum (297) exceeds threshold by 47 chars.
- **Length buckets:** < 300: 1 (0.3%), 300-349: 22 (6.4%), 350-399: 120 (35.1%), 400-449: 133 (38.9%), 450-499: 49 (14.3%), 500+: 17 (5.0%)
- **Silver impact:** Expanded rows duplicate the rationale verbatim. No length change.

#### soc_code (after transformation)
- **Non-null predicted:** ~360-388 of ~412 rows (87-94%)
- **Format:** All will be XX-XXXX after normalization. 6 unmatched broad codes will remain as XX-XXX0 or XX-X000.
- **Uniqueness:** Unique among non-null values (zero duplicates after expansion, confirmed by analysis).

#### bls_match (derived)
- **Predicted distribution:** ~354 true / ~58 false (86% / 14%)
- **Among non-null SOC:** ~354 true / ~6 false (98.3% / 1.7%) -- well above the 90% threshold
- **All null SOC rows are bls_match = false by definition.**

#### soc_resolved_method (derived)
- **Predicted distribution:**
  - "direct": ~244 (59%) -- includes 240 detailed + 4 broad-to-broad exact matches
  - "broad_expansion": ~110 (27%)
  - "title_match": ~28 (7%)
  - "unresolved": ~30 (7%) -- includes ~24 null SOC + 6 unmatched broad codes

---

### Cross-Field Analysis

**Exposure score propagation in broad expansion:** When a broad code expands to multiple detailed codes, all expanded rows get the same exposure_score. This means occupations under the same broad code (e.g., all types of Cooks) are assumed equally AI-exposed. This is a modeling simplification documented in the spec. For DQ purposes, this means groups of consecutive SOC codes will have identical scores -- not an anomaly but by design.

**Category distribution shift:** After expansion, the category distribution changes because trade/physical categories have more broad codes. Healthcare will remain the largest category, but categories like construction-and-extraction, installation-maintenance-and-repair, and production will grow proportionally due to broad code expansion.

**num_jobs_2024 relevance for dedup:** The physical model specifies dedup by highest num_jobs_2024, but no duplicates exist in current data. This field is not carried to Silver. If future data creates duplicates, Bronze num_jobs_2024 would need to be available during transformation.

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Predicted Silver row count | ~412 | -- | Set DQ range to 380-500. The 400-700 range in the physical model is correct but the upper bound is generous. |
| SOC code uniqueness (non-null) | 0 duplicates predicted | 0% | P0 grain uniqueness check will pass. Keep as hard block. |
| bls_match rate (non-null SOC) | ~98% predicted | >= 90% threshold | Threshold of >= 90% is appropriate with margin. |
| Exposure score unchanged from Bronze | 342 of 342 | 100% | Set as P0 hard block. Verify score distribution matches Bronze exactly. |
| Rationale >= 250 chars | 342 of 342 | 100% | P1 check. All pass with 47-char margin above minimum. |
| soc_resolved_method enum values | 4 valid values | 100% | P0 check. Validate all rows use exactly one of: direct, title_match, broad_expansion, unresolved. |
| Null slug | 0 predicted | 0% | P0 hard block. Slug is always present (carried from Bronze). |
| Unresolvable null-SOC rows | ~24-30 | ~6-7% | P1 warn if unresolved exceeds 10% of total. |
| Broad codes without BLS match | 6 | 1.5% | These 6 rows will have bls_match=false, soc_resolved_method="unresolved". Acceptable edge case. |
| Broad-to-broad exact matches | 4 | 1% | Transformer must check BLS for exact broad code match before attempting expansion. |
| Title match 1:N expansion | ~8 slugs -> ~16+ rows | -- | If title matching produces multiple BLS matches per slug, Silver row count increases. Monitor for unexpected row growth. |
| Score 10 (maximum) | 1 row | 0.3% | Will appear once in Silver (direct match). Valid edge case. |
| Score 0 (minimum, absent) | 0 rows | 0% | 0-10 range check is correct but 0 is not present. Keep check as defensive. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| soc_code | 6 broad codes with no BLS match of any kind | 6 | Medium | SOC codes 19-5000, 37-3000, 39-2000, 41-4000, 43-6000, 53-5000 are higher-level groupings (XX-X000 pattern) with no detailed or broad BLS match. These must be handled as unresolved. |
| soc_code | 4 broad codes match BLS as broad-to-broad | 4 | Medium | 13-2020, 29-2010, 31-1120, 39-7010 exist in BLS OOH as broad codes. The expansion algorithm must check for exact broad match BEFORE attempting prefix expansion, or these 4 codes will be incorrectly classified as "no expansion found". |
| soc_resolved_method | Predicted distribution differs from spec | -- | Low | Spec predicted ~70% direct / ~15% broad_expansion / ~10% title_match / ~5% unresolved. Actual will be ~59% direct / ~27% broad_expansion / ~7% title_match / ~7% unresolved. The spec thresholds should be updated to match evidence. |
| title_match | Zero exact matches, all partial | 0 exact | Medium | No Karpathy occupation title exactly matches a BLS OOH title (case-insensitive). All title matches rely on substring/fuzzy logic, which introduces false positive risk. |
| title_match | 1:N matches possible | ~8 slugs | Low | Some null-SOC occupations match multiple BLS titles (e.g., "Nurse anesthetists, nurse midwives, and nurse practitioners" -> 3 matches). If all matches are kept, Silver row count increases beyond the 412 estimate. |

---

### Threshold Evidence Summary for @dq-rule-writer

| DQ Rule (Physical Model) | Rule ID | Threshold | Evidence |
|--------------------------|---------|-----------|----------|
| Grain uniqueness on soc_code (non-null) | SLV-KAI-001 | P0 hard block: 0 duplicates | Zero duplicates predicted after all expansion and dedup analysis |
| SOC code format XX-XXXX (non-null) | SLV-KAI-002 | P0 hard block | All 290 Bronze SOC codes pass format check. 6 unmatched broad codes use XX-X000 pattern -- these may fail regex if regex requires final digit != 0. Recommend: format check on non-broad codes only, OR accept XX-XXXX including XX-XXX0 patterns |
| Exposure score range 0-10 | SLV-KAI-003 | P0 hard block | All 342 Bronze scores in range 1-10. Physical model allows 0-10. |
| Rationale length >= 250 | SLV-KAI-004 | P1 warn | Minimum observed: 297 chars. All pass with margin. |
| soc_resolved_method enum | SLV-KAI-005 | P0 hard block | 4 valid values: direct, title_match, broad_expansion, unresolved |
| bls_match >= 90% (non-null SOC) | SLV-KAI-006 | P0 hard block; threshold 90% | Predicted ~98% for non-null SOC. Threshold has good margin. |
| Slug not null | SLV-KAI-007 | P0 hard block | 0 null slugs in Bronze (100% coverage) |
| record_id unique and not null | SLV-KAI-008 | P0 hard block | Deterministic hash, guaranteed unique by construction |
| Row count 400-700 | SLV-KAI-009 | P1 warn | Predicted ~412. Recommend tightening to 380-500. |

---

### Implementation Notes for @primary-agent

1. **Broad-to-broad matching:** Before attempting prefix expansion for XX-XXX0 codes, check if the exact code exists in base.bls_ooh. If yes, treat as soc_resolved_method = "direct" with bls_match = true. Do NOT expand.

2. **Higher-level group codes (XX-X000):** Six codes (19-5000, 37-3000, 39-2000, 41-4000, 43-6000, 53-5000) use major-group-level patterns. These will not match any BLS code. Mark as soc_resolved_method = "unresolved" and bls_match = false.

3. **Title matching strategy:** No exact matches exist. All resolution requires fuzzy/substring matching. Recommend implementing conservative substring match (BLS title contained in Karpathy title, or Karpathy title contained in BLS title) with minimum token overlap threshold. Flag all title matches for human review in the audit trail.

4. **1:N title matches:** When one Karpathy occupation matches multiple BLS codes, create multiple Silver rows (each with the same slug but different soc_code). This is analogous to broad code expansion but via title matching.

5. **num_jobs_2024 for dedup:** This field is in Bronze but not Silver. If dedup is ever needed, the transformer must access Bronze data during the transformation to resolve ties.

---

*End of Silver EDA Report*
