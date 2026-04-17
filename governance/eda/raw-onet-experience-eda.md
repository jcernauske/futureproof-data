## EDA Report: raw.onet_experience
**Source:** O*NET 30.2 Database — `Education, Training, and Experience.txt` (extracted from `db_30_2_text.zip`)
**Date:** 2026-04-16
**Agent:** bs:data-analyst
**Spec:** `docs/specs/onet-experience-requirements.md`
**Record Count:** 35,998 (plus 1,127 rows skipped by ingestor for null grain fields)
**Field Count:** 17 (13 data + 4 metadata)
**Ingest parquet:** `data/bronze/iceberg_warehouse/bronze/onet_experience/data/00000-0-f09a19fa-5466-46ed-a39d-58f4db0dac5e.parquet`

---

### Executive Summary

The `raw.onet_experience` ingest landed clean. 35,998 rows cover the full four-scale Education/Training/Experience distribution for **878 O*NET-SOC occupations** (mapping to **765 distinct BLS SOC codes**). All four scales (RL/RW/PT/OJ) are present for every one of those 878 occupations with the exact expected category counts from the spec (12/11/9/9). Every (occupation × scale) group sums to 100 ± 0.03; `data_value` is cleanly bounded in [0.0, 95.83] (with one RL row at 100.0). Suppression is low (2.4% overall, 2.2% on RW). The weighted-median spot checks confirm the spec's expectations with one caveat: `41-2031.00` (Retail Salespersons) has a **bimodal** RW distribution where the weighted median lands on category 5 (0.75 yr midpoint), not category 1–3; it still lands in the "entry" tier (0–1 years threshold includes 0.75 yr) so the Silver DQ spot-check `tier = "entry"` will still pass. Three numbers worth calling out:

1. **878 occupations** — not the spec's "~1,016". This is the expected count given the Bronze-zone pattern established by Work Activities/Work Context (both also 894 vs. 1,016 in Occupation Data). 93+ "All Other"/Military residual codes plus ~45 recently-added codes have no ETE survey rows. **The "~1,016" figure in the spec is O*NET Occupation Data's master count, not the ETE file row count** — clarify before the Silver DQ `800 ≤ row count ≤ 900` threshold is treated as P0.
2. **RW rows = 9,658**, below the spec's P1 expectation of 11,000–12,000. That expectation assumes 1,016 occupations × 11 categories = 11,176; the actual 878 × 11 = 9,658 is a perfect fit once the occupation coverage reality is accounted for. The P1 threshold should be rewritten to `9,500 ≤ rw_rows ≤ 12,500` or explicitly tied to `distinct_onet_soc × 11`.
3. **Silver row count will be 765**, not 867 — every BLS-SOC truncation happens against the 878 O*NET codes available, which collapses to 765 BLS 6-digit roots. The spec's `800 ≤ count ≤ 900` Silver P0 rule needs updating to `720 ≤ count ≤ 810` or similar.

No data-quality red flags that should block downstream work. One finding (retail salesperson weighted median = 5 not 1–3) is worth documenting in the Silver spec's "known-value spot checks" so nobody mis-tunes the DQ rule to insist on `median_category <= 3`.

---

### Domain Context

**Identified Domain:** Occupational experience-requirements / labor-market analytics.
**Primary Entities:** Occupations (O*NET-SOC `XX-XXXX.XX`) × ETE scales (RL, RW, PT, OJ) × duration categories.
**Grain:** `(onet_soc_code, element_id, scale_id, category)` — verified unique (0 duplicates at that 4-tuple grain).
**Temporal Pattern:** Rolling annual updates per occupation; dates span 06/2008 to 08/2025.
**Domain Vocabulary:** O*NET Content Model element IDs (`2.D.1`, `3.A.1`, `3.A.2`, `3.A.3`), ETE scale codes (RL/RW/PT/OJ), domain sources (Incumbent, Occupational Expert).
**Taxonomy/Codes Found:** O*NET-SOC (XX-XXXX.XX), BLS SOC (XX-XXXX via truncation), O*NET Content Model (2.D / 3.A).

---

### Key Findings

- **Row count: 35,998** (P0-rule `30,000 ≤ count ≤ 45,000` holds with wide margin).
- **Exactly 4 scales present:** RL (10,536), RW (9,658), PT (7,902), OJ (7,902). Spec's P1 RW expectation (11,000-12,000) is not met because only 878 occupations have ETE data (not 1,016).
- **Every one of the 878 occupations has all 4 scales with the exact spec-expected category count** (RL=12, RW=11, PT=9, OJ=9). No partial-scale coverage anywhere. The spec's "PT=9, OJ=11" guess is inverted vs. observed reality — **both PT and OJ have 9 categories, not PT=9/OJ=11**. The ETE file has OJ with 9 categories (None, Anything beyond a Short Demo up to 1 month, … , Over 10 years). Update spec + DQ rules.
- **element_id is 1:1 with scale_id:** RL↔2.D.1, RW↔3.A.1, PT↔3.A.2, OJ↔3.A.3. Silver's filter `scale_id='RW' AND element_id='3.A.1'` is redundant but safe.
- **878 distinct O*NET-SOC codes** across all scales; **765 distinct BLS-SOC codes** (after 7-char truncation). **This will be the Silver row count, not 867.**
- **Per-(occupation × scale) frequency sum is uniformly ~100.0:** mean 100.0004, std 0.008, max |dev| 0.03 across all 3,512 groups. Zero groups off by more than 1.0. The P1 sum-to-100 rule is trivially satisfied.
- **Suppression is low:** 864 rows (2.4%) flagged `recommend_suppress='Y'` overall; 209/9,658 (2.2%) on RW, 223 RL, 228 PT, 204 OJ. 8,610 rows (23.9%) have `recommend_suppress='n/a'` — these are exclusively the Occupational Expert source rows.
- **Zero occupations have all RW rows suppressed.** Zero RW rows have `data_value = 100.0` (no single-category-100% case in RW). Silver's edge-case test matrix for "all suppressed" and "single-category 100%" must therefore be synthetic, not drawn from real data.
- **754 of 878 occupations (85.9%) have no single RW category above 50%.** This is the primary justification for weighted-median-across-cumulative-frequency logic vs. simple mode.
- **Retail salespersons `41-2031.00` has a bimodal RW distribution** (cat 1 = 39.75%, cat 5 = 32.02%). Cumulative crosses 50% at category 5, not 1-3. Weighted median = 5 (midpoint 0.75 yr). Still "entry" tier (0-1 yr). Spec's hint that 41-2031 should skew cat 1-3 is only half right.
- **Chief Executives `11-1011.00` confirmed senior-heavy:** 68.24% at category 11 (10+ years), weighted median = 11 (midpoint 12 yr). Tier = "senior" confirmed.
- **Software Developers `15-1252.00` confirmed mid-senior:** 43.91% at category 9, weighted median = 9 (midpoint 7 yr). Tier = "mid" (4-8 yr threshold). Confirmed.
- **lower_ci_bound / upper_ci_bound are null 52.75% of the time** — populated only for the ~17K Incumbent rows where CI was computed. Not a DQ issue; document null semantics.
- **Sample size `n`** is populated on 100% of rows (median 23, mean 25.2, p95 40). The spec Raw schema marked it optional; in practice it is always present.

---

### 1. Row Counts by Scale

| Scale ID | Element ID | Element Name | Rows | % of total |
|----------|-----------|--------------|------|-----------:|
| RL | 2.D.1 | Required Level of Education | 10,536 | 29.3% |
| RW | 3.A.1 | Related Work Experience | 9,658 | 26.8% |
| PT | 3.A.2 | On-Site or In-Plant Training | 7,902 | 21.9% |
| OJ | 3.A.3 | On-the-Job Training | 7,902 | 21.9% |
| **Total** | | | **35,998** | 100% |

Arithmetic check: 878 occupations × (12 + 11 + 9 + 9) = 878 × 41 = 35,998. ✓

**Spec conflict:** Spec §Zone 1 lists "RL=12, RW=11, PT=9, OJ=11" for category counts. Observed is **OJ=9** (not 11). Both RL's `2.D.1` scale and the OJ `3.A.3` scale are consistent with O*NET's published scale definitions — the spec's "OJ=11" is a drafting error. Update spec language and any DQ rule that hardcodes 11.

### 2. Occupation Coverage

| Metric | Value |
|--------|------:|
| Distinct `onet_soc_code` values | **878** |
| Distinct BLS SOC codes (XX-XXXX truncation) | **765** |
| Occupations with all 4 scales | **878 (100%)** |
| Occupations with 3 or fewer scales | 0 |
| onet_soc_code format violations | 0 / 35,998 |

Every occupation that appears in the file appears in all four scales. Unlike Work Activities (894 occupations) or Work Context (894), the ETE file has 878 — the **smallest footprint** of any O*NET file in the pipeline. The 138 missing O*NET codes (1,016 − 878) are a superset of the 122 missing from Work Activities/Context; the 16 extras are likely recently-added occupations where ETE survey data has not yet been collected.

**Spec gap:** The spec says "~1,016 occupations × 4 scales × variable categories." The actual occupation footprint is 878. Downstream Silver row count expectation is 765, not 867. Both numbers must be reconciled in the Silver DQ rule writer's bounds.

### 3. Category Distribution per Scale

| Scale ID | Observed category count | Spec expectation | Match? |
|----------|----------------------:|-----------------:|:------:|
| RL | 12 | 12 | ✓ |
| RW | 11 | 11 | ✓ |
| PT | 9 | 9 | ✓ |
| OJ | 9 | **11** | ✗ — spec error |

**Every one of the 878 occupations has exactly 12/11/9/9 categories for RL/RW/PT/OJ respectively.** No partial-coverage cases. Min/max category per scale is [1, N] with no gaps.

### 4. data_value Sanity

**Overall:** min = 0.0, max = 100.0, mean = 9.76. Out-of-range values (< 0 or > 100): **0**.

| Scale | Min | Max | Mean | Std |
|-------|----:|----:|-----:|----:|
| OJ | 0.0 | 90.40 | 11.11 | 12.63 |
| PT | 0.0 | 81.22 | 11.11 | 12.48 |
| RL | 0.0 | 100.00 | 8.33 | 17.18 |
| RW | 0.0 | 95.83 | 9.09 | 12.31 |

Mean closely matches the theoretical uniform-if-balanced value (100 / N categories): OJ/PT = 11.11 (100/9), RL = 8.33 (100/12), RW = 9.09 (100/11). Healthy signal that the ingest did not drop or duplicate rows.

**Per-(occupation × scale) sum (P1 rule):**

| Scale | Groups | Mean sum | Std | Min | Max | Off-by > 1.0 | Off-by > 5.0 | Zero sum |
|-------|-------:|---------:|----:|----:|----:|-------------:|-------------:|--------:|
| OJ | 878 | 100.0001 | 0.0075 | 99.98 | 100.02 | 0 | 0 | 0 |
| PT | 878 | 100.0006 | 0.0079 | 99.98 | 100.02 | 0 | 0 | 0 |
| RL | 878 | 100.0002 | 0.0066 | 99.97 | 100.02 | 0 | 0 | 0 |
| RW | 878 | 100.0005 | 0.0081 | 99.98 | 100.03 | 0 | 0 | 0 |

The P1 "sum ≈ 100" rule passes with enormous margin. Tolerance of ±0.1 is sufficient; ±1.0 is trivially safe.

### 5. Suppression Rate

**Overall:**

| Value | Rows | % |
|-------|-----:|----:|
| N | 26,524 | 73.7% |
| n/a | 8,610 | 23.9% |
| Y | 864 | 2.4% |

**Per scale:**

| Scale | N | n/a | Y | Y rate |
|-------|--:|----:|--:|-------:|
| OJ | 5,808 | 1,890 | 204 | 2.6% |
| PT | 5,784 | 1,890 | 228 | 2.9% |
| RL | 7,793 | 2,520 | 223 | 2.1% |
| RW | 7,139 | 2,310 | 209 | 2.2% |

`recommend_suppress = 'n/a'` correlates exactly with `domain_source = 'Occupational Expert'` (8,610 rows each — 1:1 match). Only the Incumbent-source rows carry a real Y/N flag. **Silver DQ must allow `{"N","Y","n/a"}` as the value set, same as Work Activities/Context precedent.**

### 6. Known-Value Spot Checks (RW Scale)

#### `11-1011.00` Chief Executives (expected: senior)

| Cat | data_value | recommend_suppress |
|----:|-----------:|:------------------:|
| 1 | 0.0 | N |
| 2 | 0.0 | N |
| 3 | 0.0 | N |
| 4 | 0.0 | N |
| 5 | 0.0 | N |
| 6 | 0.0 | N |
| 7 | 9.69 | N |
| 8 | 5.87 | N |
| 9 | 15.09 | N |
| 10 | 1.11 | N |
| **11** | **68.24** | N |

**Weighted median = 11** (cumulative at cat 11 = 100.0). Midpoint = 12 yr. Tier = **senior**. Spec assumption confirmed. Skews even more senior than "categories 9-11" — essentially everything is at category 11.

#### `41-2031.00` Retail Salespersons (expected: entry)

| Cat | data_value | recommend_suppress |
|----:|-----------:|:------------------:|
| **1** | **39.75** | N |
| 2 | 0.65 | N |
| 3 | 2.97 | N |
| 4 | 0.0 | N |
| **5** | **32.02** | N |
| 6 | 7.29 | N |
| 7 | 6.87 | N |
| 8 | 0.65 | N |
| 9 | 0.0 | N |
| 10 | 9.79 | N |
| 11 | 0.0 | N |

**Bimodal!** Cumulative: 39.75 / 40.40 / 43.37 / 43.37 / **75.39** / 82.68 / 89.55 / 90.20 / 90.20 / 99.99 / 99.99. Weighted median = **category 5** (first category where cumulative ≥ 50), not 1-3. Midpoint = 0.75 yr. Tier = **entry** (0-1 yr threshold) — spec's tier expectation passes. The specific claim "should skew categories 1-3" is only half-true. The Silver DQ spot check `41-2031 tier = "entry"` is safe; do not write a median-category rule that insists on `category <= 3`.

#### `15-1252.00` Software Developers (expected: mid, categories 6-8)

| Cat | data_value | recommend_suppress |
|----:|-----------:|:------------------:|
| 1 | 4.42 | N |
| 2 | 0.0 | N |
| 3 | 0.0 | N |
| 4 | 0.0 | N |
| 5 | 0.0 | N |
| 6 | 11.13 | N |
| 7 | 7.13 | N |
| 8 | 15.04 | N |
| **9** | **43.91** | N |
| 10 | 7.82 | N |
| 11 | 10.55 | N |

Cumulative: 4.42 / 4.42 / 4.42 / 4.42 / 4.42 / 15.55 / 22.68 / 37.72 / **81.63** / 89.45 / 100.0. **Weighted median = category 9** (midpoint 7 yr). Tier = **mid** (4-8 yr threshold). Spec's "around categories 6-8" is directionally right (mode is cat 9, just past the 6-8 band), and the weighted median comfortably lands in the mid tier.

### 7. Multi-Detail Aggregation Preview

Distribution of O*NET detail codes per BLS SOC (RW scale, 765 BLS SOCs covered):

| `onet_details_averaged` | BLS SOCs | % |
|-----------------------:|---------:|----:|
| 1 | 702 | 91.8% |
| 2 | 40 | 5.2% |
| 3 | 10 | 1.3% |
| 4 | 6 | 0.8% |
| 5 | 2 | 0.3% |
| 6 | 4 | 0.5% |
| 8 | 1 | 0.1% |

**63 BLS SOCs (8.2%) have multiple O*NET detail codes.** The "unweighted average of `experience_years_typical` across details" rule (approved in `governance/approvals/onet-experience-requirements-open-decisions.md`) will apply to 63 BLS SOCs.

### 8. Null Rates per Field

| Field | Nulls | Null % | Notes |
|-------|------:|-------:|-------|
| onet_soc_code | 0 | 0.00% | Required (P0). |
| element_id | 0 | 0.00% | Required (P0). |
| element_name | 0 | 0.00% | Required. |
| scale_id | 0 | 0.00% | Required (P0). |
| category | 0 | 0.00% | Required. |
| data_value | 0 | 0.00% | Required. |
| n | 0 | 0.00% | **Never null on real data.** Spec marks optional; can be upgraded to required in DQ. |
| standard_error | 8,610 | 23.92% | Null ⇔ `domain_source = 'Occupational Expert'` (1:1 match). |
| lower_ci_bound | 18,989 | 52.75% | Null both for Expert rows AND any Incumbent row where CI could not be computed. |
| upper_ci_bound | 18,989 | 52.75% | Null exactly when lower_ci_bound is null (paired). 17,009 rows have both populated. |
| recommend_suppress | 0 | 0.00% | But 8,610 rows (23.9%) carry the string `'n/a'`, not null. |
| date | 0 | 0.00% | MM/YYYY format, 8/2021 most recent peak (3,813 rows). |
| domain_source | 0 | 0.00% | Two values only: Incumbent (27,388) and Occupational Expert (8,610). |
| ingested_at / source_url / source_method / load_date | 0 | 0.00% | Bronze metadata, populated by ingestor. |

### 9. n (sample size) and CI Bounds

| Metric | Count | Min | Median | Mean | p95 | Max |
|--------|------:|----:|-------:|-----:|----:|----:|
| n (sample size) | 35,998 (100%) | 13 | 23.0 | 25.23 | 40.0 | 98 |
| standard_error | 27,388 (76.1%) | 0.0 | 2.68 | 4.82 | — | 29.73 |
| lower_ci_bound | 17,009 (47.3%) | — | — | — | — | — |
| upper_ci_bound | 17,009 (47.3%) | — | — | — | — | — |

**Observations:**
- `n` is always populated — the Optional flag in the spec Raw schema is defensive. If downstream logic ever needs `n`, it will not encounter a null.
- `standard_error` is present only for Incumbent-source rows; Expert rows have no sampling distribution and leave it null. This is expected and matches Work Activities/Context precedent.
- CI bounds are paired (17,009 populated on both; 18,989 null on both; no mixed rows).

### 10. Weighted-Median Edge Cases Already Present in RW

| Edge Case | Count | Details |
|-----------|------:|---------|
| All RW rows suppressed (`recommend_suppress='Y'`) | **0** | No real-data case exists; chaos monkey must synthesize. |
| RW coverage < 11 categories | **0** | All 878 occupations have exactly 11 RW rows. |
| Single RW category at `data_value = 100.0` | **0** | No real-data case; synthesize for test. |
| No RW category above 50% (multi-modal distribution) | **754** | **85.9% of occupations** — the normal case. Weighted-median walk is mandatory. |
| Bimodal distributions (2 peaks > 20%) | several | `41-2031.00` is a documented example (cat 1 = 39.75%, cat 5 = 32.02%). |

---

### Cross-Field Analysis

- **(onet_soc_code, scale_id, category) is unique** across the file (0 duplicates). The ingestor's dedup grain of `[onet_soc_code, element_id, scale_id, category]` is safe — `element_id` is 1:1 with `scale_id` so adding it doesn't change uniqueness.
- **element_id ⊆ {2.D.1, 3.A.1, 3.A.2, 3.A.3}** exactly — no stray elements slipped in. Silver's filter `element_id='3.A.1'` is equivalent to `scale_id='RW'` for this file.
- **recommend_suppress='n/a' iff domain_source='Occupational Expert'** (bijection, 8,610 rows on each side).
- **standard_error IS NULL iff domain_source='Occupational Expert'** (same bijection). CI bounds are null more broadly (52.75%).
- **date distribution correlates with rolling O*NET updates** — 14 distinct month/year values, peaks in August each year (survey cadence).

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation for @dq-rule-writer |
|-------------|------:|-----------:|-----------------------------------|
| Row count | 35,998 | — | Bronze P0 rule `30,000 ≤ count ≤ 45,000` is fine with a ~6K margin on each side. |
| RW rows | 9,658 | 26.8% | Spec P1 `11,000-12,000` **is wrong**. Set `9,000 ≤ rw_rows ≤ 12,500` OR tie to `rw_rows = distinct_onet_soc × 11`. |
| Distinct O*NET-SOC | 878 | — | Bronze should not enforce 1,016 anywhere (spec mentions it but no rule pins it). Silver row count (BLS SOC grain) will be 765. |
| Distinct BLS SOC (post-truncation) | 765 | — | Silver P0 `800 ≤ count ≤ 900` needs to be `720 ≤ count ≤ 810` (or `distinct_bls_soc ± 5%`). |
| OJ categories | 9 per occupation | 100% | Spec says "PT=9, OJ=11" — **drop the OJ=11 claim** from Bronze DQ. Correct: RL=12, RW=11, PT=9, OJ=9. |
| `data_value` out of [0, 100] | 0 | 0% | P0 rule `0 ≤ data_value ≤ 100` is trivially safe. Can tighten to `≤ 100.01` if float tolerance bites later. |
| Sum of (occ × scale) off by > 0.05 | 0 | 0% | P1 rule "sum ≈ 100 (±0.1)" passes with ~25× margin. Safe. |
| `recommend_suppress='Y'` | 864 | 2.4% | Rule: `Y rate ≤ 5%` (current 2.4%, per-scale max 2.9%). |
| `recommend_suppress='n/a'` | 8,610 | 23.9% | Must allow `{"N","Y","n/a"}` as value set. `n/a` correlates 1:1 with Occupational Expert rows. |
| `scale_id` values | {RL, RW, PT, OJ} | 100% | P0 `scale_id IN ('RL','RW','PT','OJ')` — exact match. |
| `element_id` values | {2.D.1, 3.A.1, 3.A.2, 3.A.3} | 100% | P0 candidate: `element_id IN (...)` (spec does not list; add for defense-in-depth). |
| `domain_source` values | {Incumbent, Occupational Expert} | 100% | **Narrower than other O*NET files** (Work Activities adds Analyst, Analyst - Transition; ETE does not). Rule: `domain_source IN ('Incumbent','Occupational Expert')`. |
| `n` null rate | 0% | — | Spec Optional → in practice Required. Safe to lift to P0 non-null. |
| `standard_error` null rate | 23.9% | 23.9% | Null ⇔ Expert source. No DQ action, document. |
| CI-bound null rate | 52.75% | 52.75% | Null ⇔ Expert rows OR CI-unavailable Incumbent rows. Document; no rule. |
| onet_soc format violations | 0 | 0% | P0 regex `^\d{2}-\d{4}\.\d{2}$` — safe. |
| Occupations with all RW suppressed | 0 | 0% | Synthesized-data test only. Silver `suppress_flag=TRUE` path has 0 real-world triggers today. |
| Occupations with single RW cat at 100% | 0 | 0% | Synthesized-data test only. |
| Occupations with no cat > 50% | 754 | 85.9% | The common case. Weighted-median walk is mandatory for Silver. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|------:|----------|---------|
| Occupation coverage | Deviation from spec | 138 | Medium | Spec says "~1,016 occupations"; actual is 878. Not a bug — matches Work Activities/Context precedent. |
| OJ category count | Spec error | 878 × 9 = 7,902 rows | Medium | Spec claims OJ=11 categories; actual is 9. Bronze DQ must use 9. |
| RW row count | P1 threshold mismatch | 9,658 vs. 11,000-12,000 | Medium | Spec P1 is predicated on the wrong occupation count. |
| `41-2031.00` bimodal RW | Documented edge case | 1 occupation | Low | Weighted median = cat 5 (0.75 yr), not cat 1-3. Tier still "entry". Document in Silver DQ. |
| CI bounds 52.75% null | Expected pattern | 18,989 | Low | Not all Incumbent rows have computed CIs. No DQ action. |

---

### Implications for DQ Rules (for @dq-rule-writer)

**Bronze rules (concrete thresholds):**

1. `bronze.onet_experience.row_count` P0 — `30,000 ≤ count ≤ 45,000` — observed 35,998. SAFE.
2. `bronze.onet_experience.rw_row_count` P1 — **rewrite from `11,000-12,000` to `9,000 ≤ count ≤ 12,500`** (observed 9,658).
3. `bronze.onet_experience.scale_id_values` P0 — `scale_id IN ('RL','RW','PT','OJ')` — observed exact.
4. `bronze.onet_experience.category_count_by_scale` P1 — **rewrite from `RL=12, RW=11, PT=9, OJ=11` to `RL=12, RW=11, PT=9, OJ=9`**.
5. `bronze.onet_experience.data_value_range` P0 — `0.0 ≤ data_value ≤ 100.0` — 0 violations.
6. `bronze.onet_experience.per_group_sum` P1 — `abs(SUM(data_value) per (onet_soc,scale) - 100) ≤ 0.1` — 0 violations at even 0.05 tolerance.
7. `bronze.onet_experience.onet_soc_format` P0 — `REGEXP ^\d{2}-\d{4}\.\d{2}$` — 0 violations.
8. `bronze.onet_experience.grain_uniqueness` P0 — unique on `(onet_soc_code, element_id, scale_id, category)`. Observed unique.
9. `bronze.onet_experience.recommend_suppress_values` P0 — `IN ('N','Y','n/a')`. Observed exact.
10. `bronze.onet_experience.domain_source_values` P0 — `IN ('Incumbent','Occupational Expert')`. Observed exact (narrower than other O*NET files).
11. `bronze.onet_experience.element_id_values` P0 — `IN ('2.D.1','3.A.1','3.A.2','3.A.3')`. New rule; defensive.
12. `bronze.onet_experience.suppression_rate` P1 — `rows where recommend_suppress='Y' / rows ≤ 0.05`. Observed 0.024.
13. `bronze.onet_experience.required_fields_non_null` P0 — on `onet_soc_code, element_id, element_name, scale_id, category, data_value, n`. (n is always populated — can be lifted to P0 from optional.)

**Silver rules (threshold updates needed):**

- `silver.onet_experience_profiles.row_count` — **rewrite from `800 ≤ count ≤ 900` to `720 ≤ count ≤ 810`** (observed 765 BLS-SOC roots).
- `silver.onet_experience_profiles.11_1011_tier = "senior"` — confirmed by real data (weighted median cat 11 → 12 yr → senior).
- `silver.onet_experience_profiles.41_2031_tier = "entry"` — confirmed by real data (weighted median cat 5 → 0.75 yr → entry). **Do NOT add a `median_category ≤ 3` rule** for 41-2031 — it would fail.
- Tier distribution sanity (P1, new): none of the 4 tiers should be zero; "senior" should be 5-30% (CEOs, surgeons, senior management).

---

### Implications for Silver Transformer

The Silver transformer must handle these realities:

1. **Input is 878 occupations, not 1,016** — the `distinct_onet_soc_code` read is 878. After BLS truncation the row count is **765**, not 867. Downstream `base.onet_experience_profiles` row count DQ must be recalibrated.
2. **Bimodal distributions are common** — 754 / 878 = 85.9% of occupations have no single RW category above 50%. The weighted-median-across-cumulative logic is non-negotiable (simple mode would be misleading).
3. **No all-suppressed occupations in real data** — `suppress_flag` will be FALSE for every row today. The flag still needs to exist (source data could change; chaos monkey exercises it) but current Silver rows will all be `suppress_flag=FALSE`.
4. **No single-category-100% cases in real data** — that edge case is a chaos-only test target, never a real row.
5. **Multi-detail aggregation applies to 63 BLS SOCs** (8.2%). `onet_details_averaged` will be ≥ 2 for those; = 1 for the other 702. Max observed is 8 (for one BLS SOC).
6. **Cumulative sum tolerance for weighted median** — per-(occ,scale) sums are always within ±0.03 of 100. The weighted-median implementation should use `cumulative >= 50.0` rather than exactly `== 50.0` to avoid float-comparison fragility (the `_sum` approved-open-decision on "tie at 50% → pick the lower-numbered category" is fine with `>= 50.0`).

---

### Implications for Spot Checks

Real-data confirmation of the three Silver DQ spot checks:

| O*NET-SOC | Title | RW mode cat | Weighted median cat | Midpoint years | Tier | Spec claim verified? |
|-----------|-------|-----------:|-------------------:|--------------:|------|:--------------------:|
| 11-1011.00 | Chief Executives | 11 (68.24%) | 11 | 12 | senior | ✓ confirmed |
| 41-2031.00 | Retail Salespersons | 1 (39.75%) | **5** | 0.75 | entry | ✓ tier confirmed (but weighted-median is cat 5, **not** cat 1-3 as spec hinted) |
| 15-1252.00 | Software Developers | 9 (43.91%) | 9 | 7 | mid | ✓ confirmed (mid tier = 4-8 yr) |

**Silver DQ rules should assert tier values, not category values.**
- `11-1011 tier == "senior"` — safe.
- `41-2031 tier == "entry"` — safe.
- Do **not** write `41-2031 experience_category_median ≤ 3` — that would fail on real data (actual = 5).
- A `15-1252 tier == "mid"` rule would also pass; not in the spec but worth adding.

---

### Data Quality Red Flags

**None that should block downstream work.** The three deltas from the spec are documentation/threshold updates, not data integrity problems:

1. Spec's "OJ=11 categories" is a drafting error — OJ has 9 categories, every occupation. Update spec + DQ rule.
2. Spec's "~1,016 occupations" is from Occupation Data, not the ETE file (878). Update Silver row-count bounds.
3. Spec's "RW 11,000-12,000 rows" is based on the wrong occupation count. Update P1 bound.

The ingest itself is clean: 0 format violations, 0 out-of-range values, 0 null rates on required fields, per-group sums within 0.03 of 100, full coverage of all 4 scales for all 878 occupations.

---

### Files

- **EDA report:** `/Users/jcernauske/code/bright/futureproof-data/governance/eda/raw-onet-experience-eda.md` (this file)
- **Underlying stats JSON:** `/Users/jcernauske/code/bright/futureproof-data/docs/sessions/eda-raw-onet-experience-stats.json`
- **EDA script:** `/Users/jcernauske/code/bright/futureproof-data/scripts/eda_raw_onet_experience.py`
- **Raw parquet:** `/Users/jcernauske/code/bright/futureproof-data/data/bronze/iceberg_warehouse/bronze/onet_experience/data/00000-0-f09a19fa-5466-46ed-a39d-58f4db0dac5e.parquet`
