## EDA Report: bronze.karpathy_ai_exposure
**Source:** Andrej Karpathy's `karpathy/jobs` GitHub repository -- `scores.json` (AI exposure scores) joined with `occupations.csv` (BLS occupation metadata)
**Date:** 2026-04-09
**Agent:** @data-analyst
**Record Count:** 342
**Field Count:** 13 (slug, occupation_title, category, soc_code, exposure_score, rationale, median_pay_annual, num_jobs_2024, entry_education, ingested_at, source_url, source_method, load_date)

---

### Domain Context

**Identified Domain:** AI labor market impact -- LLM-generated estimates of how current AI will reshape U.S. occupations
**Primary Entities:** BLS occupations, scored by AI exposure level (0-10)
**Grain:** One row per occupation slug (Karpathy's kebab-case identifier). 342 distinct slugs, 342 rows -- grain uniqueness confirmed.
**Temporal Pattern:** Static snapshot -- single LLM scoring run ("a saturday morning 2 hour vibe coded project"). Not time-series. Event-driven refresh only.
**Domain Vocabulary:**
- **exposure_score** -- 0-10 integer measuring "how much will AI reshape this occupation" (higher = more exposed). Not a job-loss predictor; measures reshaping.
- **slug** -- kebab-case occupation identifier from Karpathy's repo (e.g., "financial-analysts")
- **category** -- Karpathy's BLS category grouping (25 categories, e.g., "business-and-financial", "healthcare")
- **rationale** -- 2-3 sentence LLM explanation of scoring factors
**Taxonomy/Codes Found:**
- SOC 2018 codes (XX-XXXX format) -- present for 290 of 342 rows. Mix of detailed codes (exact BLS match) and broad codes (XX-XXX0 pattern, roll-up of multiple detailed occupations).
- Karpathy category taxonomy -- 25 categories derived from BLS occupation groups. Not a standard BLS taxonomy but maps cleanly to BLS major groups.

---

### Key Findings

- **342 rows ingested, exactly matching the expected count.** All slugs are unique. Zero duplicate slugs or occupation titles.
- **SOC coverage is 84.8% (290/342), not the 95% estimated in the spec.** 52 occupations have null SOC codes. The spec's SOC coverage threshold of ~95% should be revised downward to ~85%. These 52 null-SOC rows are spread across all categories, with the highest concentration in transportation-and-material-moving (54.5% null), installation-maintenance-and-repair (33.3%), production (31.3%), and computer-and-information-technology (30.0%).
- **46 of 290 SOC codes (15.9%) are "broad" codes that do not directly match our BLS OOH data.** These are codes ending in 0 (e.g., 11-2030, 15-1230) that represent rolled-up occupation groups. Our BLS OOH uses detailed codes (e.g., 11-2032, 15-1231). All 46 broad codes have at least one detailed BLS match under the same prefix, meaning Silver can potentially resolve them via SOC prefix expansion.
- **244 of 290 SOC codes (84.1%) directly match our BLS OOH data.** These are detailed SOC codes with exact matches.
- **Wage cross-validation shows perfect alignment.** For all 241 matched rows with wage data, Karpathy's `median_pay_annual` equals our BLS OOH `median_annual_wage` exactly ($0 difference on every row). This confirms Karpathy used the same BLS data snapshot as our pipeline. The 20% diff threshold in the DQ spec will pass trivially.
- **No exposure scores of 0 exist in the data.** Scores range 1-10, not 0-10 as the spec allows. Only 1 occupation scores 10 (Medical transcriptionists). The DQ rule for range 0-10 is correct but the effective range is 1-10.
- **Score distribution is roughly normal, slightly right-skewed.** Mean 5.31, median 5.0, std dev 2.26. Mode is 7 (70 rows, 20.5%) -- the largest single bucket by a wide margin.
- **Moderate positive correlation between exposure score and pay** (Pearson r=0.387). Higher-paid occupations tend to be more AI-exposed, consistent with the "computer-based office work" heuristic in Karpathy's methodology.
- **All 342 source methods are "github_download"** -- no fallback to local cache was needed.

---

### Field Profiles

#### slug
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 342)
- **Cardinality:** 342 distinct values (100% unique -- this is the grain)
- **Distribution:** All valid kebab-case (`^[a-z0-9-]+$`). Length: min=5, max=78, mean=27 chars.
- **Outliers:** 5 slugs exceed 60 chars (longest: "dental-and-ophthalmic-laboratory-technicians-and-medical-appliance-technicians" at 78 chars). These are verbose but valid.
- **Patterns:** Consistent kebab-case format. No underscores, uppercase, or special characters.

#### occupation_title
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 342)
- **Cardinality:** 342 distinct values (100% unique)
- **Distribution:** Human-readable BLS occupation titles. Range from short ("Actors", "Cooks") to long composite titles.
- **Patterns:** Title case. Many include "and" conjunctions for combined occupation groups.

#### category
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 342)
- **Cardinality:** 25 distinct values
- **Distribution (top 10):**
  - healthcare: 49 (14.3%)
  - life-physical-and-social-science: 29 (8.5%)
  - architecture-and-engineering: 29 (8.5%)
  - management: 26 (7.6%)
  - business-and-financial: 24 (7.0%)
  - construction-and-extraction: 20 (5.8%)
  - production: 16 (4.7%)
  - installation-maintenance-and-repair: 15 (4.4%)
  - education-training-and-library: 14 (4.1%)
  - office-and-administrative-support: 13 (3.8%)
- **Outliers:** "military" has only 1 row. "building-and-grounds-cleaning" has 3. These low-count categories are legitimate BLS groups.
- **Patterns:** Kebab-case, matching Karpathy's BLS category slugs.

#### soc_code
- **Type:** STRING (nullable)
- **Null Rate:** 15.2% (52 of 342)
- **Cardinality:** 290 distinct values among non-null (100% unique within non-null -- no duplicate SOCs)
- **Distribution:** All 290 non-null values pass XX-XXXX format validation. Zero malformed codes.
- **Outliers:** None in format. However, 46 of 290 codes are "broad" SOC codes (last digit is 0, e.g., 11-2030) that do not exist in our BLS OOH detailed-code table.
- **Patterns:** 244 detailed codes match BLS OOH exactly. 46 broad codes match BLS OOH by prefix (first 5 chars) but not by full code. Zero codes with no BLS prefix match at all.

#### exposure_score
- **Type:** INTEGER
- **Null Rate:** 0.0% (0 of 342)
- **Cardinality:** 10 distinct values (scores 1 through 10; score 0 not present)
- **Distribution:**
  - Min: 1, Max: 10, Mean: 5.31, Median: 5.0, StdDev: 2.26
  - P10: 2.0, P25: 3.0, P75: 7.0, P90: 8.0
  - Score 1: 9 (2.6%)
  - Score 2: 36 (10.5%)
  - Score 3: 47 (13.7%)
  - Score 4: 42 (12.3%)
  - Score 5: 43 (12.6%)
  - Score 6: 35 (10.2%)
  - Score 7: 70 (20.5%) -- mode, clear peak
  - Score 8: 29 (8.5%)
  - Score 9: 30 (8.8%)
  - Score 10: 1 (0.3%)
- **Outliers:** Score 10 has only 1 occupation (Medical transcriptionists, SOC 31-9094). Score 7 is disproportionately represented at 20.5% -- the LLM appears to have a "default high" tendency for computer-based work.
- **Patterns:** Bimodal tendency with clusters at 3 (physical/manual work) and 7 (office/digital work), consistent with Karpathy's heuristic that computer-based office work scores 7+.

#### rationale
- **Type:** STRING
- **Null Rate:** 0.0% (0 of 342)
- **Cardinality:** 342 distinct values (all unique rationales)
- **Distribution:** Length: min=297 chars, max=587 chars, mean=412 chars, median=408.5 chars, stddev=48 chars.
  - 200-299 chars: 1 (0.3%)
  - 300-399 chars: 142 (41.5%)
  - 400-499 chars: 182 (53.2%)
  - 500-599 chars: 17 (5.0%)
- **Outliers:** 1 rationale is under 300 chars (297) and 17 exceed 500 chars. All are substantive multi-sentence explanations. No truncated or placeholder text.
- **Patterns:** Consistent 2-3 sentence structure. All rationales are grammatically complete. No boilerplate repetition detected.

#### median_pay_annual
- **Type:** DOUBLE
- **Null Rate:** 0.6% (2 of 342)
- **Cardinality:** 327 distinct values among non-null
- **Distribution:** Min: $31,040, Max: $239,200, Mean: $75,258, Median: $65,345
- **Outliers:** $239,200 is the BLS wage cap (top-coded). 2 null values: Fishing and hunting workers, Military careers -- both legitimate BLS N/A cases.
- **Patterns:** Right-skewed wage distribution typical of U.S. labor market data. Perfectly matches BLS OOH values for all 241 cross-validated rows.

#### num_jobs_2024
- **Type:** LONG
- **Null Rate:** 0.3% (1 of 342)
- **Cardinality:** 335 distinct values among non-null
- **Distribution:** Min: 1,500, Max: 6,950,000, Mean: 419,550, Median: 141,000
- **Outliers:** 1 null value: Military careers (BLS does not report civilian employment for military). Extreme right skew -- a few very large occupations.

#### entry_education
- **Type:** STRING
- **Null Rate:** 0.3% (1 of 342 -- Military careers)
- **Cardinality:** 10 distinct values (including null)
- **Distribution:**
  - Bachelor's degree: 119 (34.8%)
  - High school diploma or equivalent: 74 (21.6%)
  - See How to Become One: 36 (10.5%)
  - Associate's degree: 29 (8.5%)
  - Master's degree: 25 (7.3%)
  - No formal educational credential: 21 (6.1%)
  - Postsecondary nondegree award: 19 (5.6%)
  - Doctoral or professional degree: 14 (4.1%)
  - Some college, no degree: 4 (1.2%)
- **Patterns:** "See How to Become One" (36 rows) is a BLS placeholder when education requirements vary widely or are non-standard. Not an error. "None" (1 row) differs from "No formal educational credential" (21 rows) and may be a data quality issue in the source.

#### source_url
- **Type:** STRING
- **Null Rate:** 0.0%
- **Cardinality:** 1 distinct value
- **Distribution:** All rows: `https://raw.githubusercontent.com/karpathy/jobs/master/scores.json`

#### source_method
- **Type:** STRING
- **Null Rate:** 0.0%
- **Cardinality:** 1 distinct value
- **Distribution:** All rows: `github_download`

#### ingested_at
- **Type:** TIMESTAMP
- **Null Rate:** 0.0%
- **Cardinality:** 1 distinct value
- **Distribution:** All rows: `2026-04-09 18:49:44.012739` (single batch ingest)

#### load_date
- **Type:** DATE
- **Null Rate:** 0.0%
- **Cardinality:** 1 distinct value
- **Distribution:** All rows: `2026-04-09`

---

### Cross-Field Analysis

**Exposure Score vs. Category:** Categories show clear clustering by AI exposure level:
- Highest exposure: computer-and-information-technology (avg 8.5), math (avg 8.8), media-and-communication (avg 7.8), office-and-administrative-support (avg 7.7), legal (avg 8.0), business-and-financial (avg 7.5)
- Lowest exposure: building-and-grounds-cleaning (avg 1.3), construction-and-extraction (avg 2.0), farming-fishing-and-forestry (avg 2.2), food-preparation-and-serving (avg 2.7), installation-maintenance-and-repair (avg 2.7)
- This aligns with the Karpathy heuristic: computer/office work scores high, physical/manual work scores low.

**Exposure Score vs. Education:** Strong positive trend. Bachelor's degree occupations average 6.9 exposure; no-credential occupations average 2.8. The correlation is not perfect -- doctoral occupations average only 5.1 (physicians, surgeons have moderate exposure despite high education).

**Exposure Score vs. Pay:** Moderate positive correlation (r=0.387). Average pay by score climbs from $50,576 (score 1) to $97,558 (score 8), then drops at score 9 ($79,047) and dramatically at score 10 ($37,550 -- Medical transcriptionists). This inversion at the top suggests the highest-exposure occupations are routine digital tasks, not high-skill knowledge work.

**SOC Null vs. Category:** Null SOC rates are highest in categories with occupation groups that BLS aggregates under broad codes: transportation-and-material-moving (54.5% null), installation-maintenance-and-repair (33.3%), production (31.3%), computer-and-information-technology (30.0%). These categories also have some of the highest-employment occupations (e.g., software developers, retail sales workers), so the null SOC issue affects a significant volume of the labor market.

**Null SOC vs. Exposure Score:** Null-SOC occupations have slightly lower average exposure (4.7 vs 5.4 for SOC-present) and a lower median (4.0 vs 6.0). This is because many null-SOC occupations are in physical/manual categories.

---

### Cross-Validation Against BLS OOH

**Direct SOC Match Rate:** 244 of 290 Karpathy SOC codes (84.1%) directly match our `bronze.bls_ooh` data.

**Broad Code Mismatch:** 46 of 290 SOC codes (15.9%) are "broad" codes (XX-XXX0 pattern) that don't match BLS OOH detailed codes. All 46 have at least one BLS detailed code under the same prefix. This is a SOC taxonomy granularity issue, not a data error. Silver zone resolution should expand these broad codes to their constituent detailed codes.

**Potential BLS Coverage:** Direct match covers 244 of 832 BLS occupations (29.3%). If broad codes are expanded to their detailed constituents, coverage could reach 595 of 832 (71.5%). This is significantly below the spec's claim of "342 of the OOH subset" -- the Karpathy dataset covers a selection of occupations, not a 1:1 mapping.

**Wage Alignment:** Perfect. Zero discrepancies across 241 comparable rows. Karpathy's `occupations.csv` uses identical BLS wage values to our OOH ingest. No data vintage mismatch.

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Null SOC codes | 52 | 15.2% | Set SOC coverage threshold to >= 84% (not 95% as spec estimated). P1 warn. |
| Broad SOC codes (not in BLS OOH) | 46 | 15.9% of non-null SOC | Silver must handle broad-to-detailed resolution. Add DQ rule: warn if >20% of SOC codes are broad. |
| Score 0 absent | 0 | 0.0% | DQ rule range 0-10 is correct but effective range is 1-10. Consider whether score 0 is expected. |
| Score 10 (single row) | 1 | 0.3% | Valid edge case. Medical transcriptionists is a reasonable max-exposure occupation. No threshold issue. |
| Score 7 overrepresentation | 70 | 20.5% | LLM scoring bias toward 7 for office/computer work. Not a DQ issue but a data quality note for consumers. |
| Null median_pay_annual | 2 | 0.6% | Fishing/hunting workers and Military careers. Legitimate BLS N/A. Threshold: allow <= 1% null. |
| Null num_jobs_2024 | 1 | 0.3% | Military careers only. Threshold: allow <= 1% null. |
| Null entry_education | 1 | 0.3% | Military careers only. Threshold: allow <= 1% null. |
| "See How to Become One" education | 36 | 10.5% | BLS placeholder, not an error. Document for downstream consumers. |
| "None" vs "No formal educational credential" | 1 vs 21 | -- | "None" may be a variant of "No formal educational credential". Flag for manual review. |
| Wage cross-validation diff > 20% | 0 | 0.0% | Perfect match. Set threshold at 20% as spec says; all rows pass trivially. |
| Rationale under 300 chars | 1 | 0.3% | Single rationale at 297 chars. Set minimum threshold at 250 chars. |
| Duplicate SOC codes | 0 | 0.0% | No duplicates. Silver dedup rule on SOC will pass trivially for direct matches. |

---

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| soc_code | Null rate higher than spec estimate | 52 | Medium | Spec estimated ~5% null; actual is 15.2%. Adjust threshold. Not a data error -- these occupations genuinely lack SOC codes in Karpathy's source. |
| soc_code | Broad codes vs detailed | 46 | Medium | 46 SOC codes are broad (XX-XXX0) while BLS OOH uses detailed (XX-XXXX) codes. Silver must handle resolution. This was not anticipated in the spec. |
| exposure_score | No zeros observed | 0 | Low | Spec allows 0-10 range, but actual data is 1-10. The Gold formula `MIN(11 - exposure_score, 10)` works correctly for range 1-10 without needing the cap at 10. However, the cap is still correct defensive code for the 0 case. |
| exposure_score | Score 7 overrepresentation | 70 | Low | 20.5% of all scores are 7 -- nearly double any other score. Suggests LLM scoring heuristic creates a "gravity well" at 7 for office/digital occupations. This is a methodology artifact, not a data error. |
| entry_education | "None" singleton | 1 | Low | 1 row has education "None" (Military careers) vs 21 rows with "No formal educational credential". Likely legitimate since military has its own training pipeline, but may confuse downstream consumers. |
| category | "military" singleton | 1 | Low | Only 1 occupation in the military category, and it has null SOC, null education, and null num_jobs_2024. This row will not join downstream (no SOC) and carries minimal data. |
| median_pay_annual | BLS wage cap | 1 | Info | 1 row at $239,200 (BLS wage cap). This is expected BLS top-coding behavior, not a Karpathy data issue. |

---

### Summary for Downstream Agents

**For @dq-rule-writer:**
- Adjust SOC coverage threshold from 95% to >= 84% (P1 warn)
- Add broad SOC code detection rule: warn if `soc_code LIKE '__-___0'` exceeds 20% of non-null codes
- Row count threshold 342 +/- 5% is correct (325-359)
- Score range 0-10 is correct; effective range is 1-10 but 0 is valid per methodology
- Rationale min length threshold: 250 chars (1 row at 297 is the minimum observed)
- Wage cross-validation 20% threshold: will pass trivially (0% divergence)
- Slug uniqueness: passes (342 distinct of 342 rows)
- Allow up to 1% null for median_pay_annual, num_jobs_2024, entry_education

**For @semantic-modeler:**
- Silver must handle broad-to-detailed SOC code expansion (46 codes). Strategy: either (a) propagate the score to all detailed codes under a broad code, or (b) match by title to find the best detailed code. The spec describes title-based matching but does not address the broad code issue.
- Consider adding a `soc_code_type` field in Silver: "detailed" (direct match), "broad" (needs resolution), "null" (no SOC)
- The `bls_match` boolean in Silver should account for broad code partial matches

**For @domain-context:**
- 25 Karpathy categories map to BLS major occupation groups but are not a 1:1 mapping to SOC major groups
- Score 7 overrepresentation (20.5%) is a known LLM scoring artifact worth documenting
- The exposure-pay correlation (r=0.387) and exposure-education correlation are important context for the RES stat interpretation
