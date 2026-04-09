# Insight Report: Silver to Gold
**Date:** 2026-04-06
**Agent:** @insight-manager
**Source Tables:** base.college_scorecard (Silver zone)
**Entities:** 2,559 institutions x 390 programs = 69,947 institution-program rows
**Records:** 69,947
**Time Range:** Single snapshot (Most Recent Cohorts, ~2022-2024 completers measured 2024-2025)

## Domain Context
From `governance/domain-context.md`: This is a Higher Education Outcomes domain covering program-level career outcomes from the U.S. Department of Education College Scorecard. The data uses CIP codes (Classification of Instructional Programs) for program taxonomy and IPEDS UNITIDs for institution identity. The core FutureProof question is: "If I study X at school Y, what career outcomes can I expect, and how exposed are those careers to AI?" The CIP-to-SOC crosswalk is the critical bridge to BLS and O*NET occupation data, which is not yet integrated.

## Executive Summary

The Silver `base.college_scorecard` table contains 69,947 rows across 2,559 institutions and 390 programs. **Only 36% of rows (25,196) have 1-year earnings data, and only 31% (21,763) have both earnings and debt data needed for the debt-to-earnings ratio.** However, the 21,763 rows with full data cover the most consequential programs: those with 30+ completers at well-established institutions. The highest-value Gold data product is the `consumable.career_outcomes` table already drafted in the Gold spec, which computes CIP-family percentile bands, debt-to-earnings ratios, confidence tiers, and relative position metrics. The data strongly supports this design. Two additional data products -- a CIP Family Summary table and a period-over-period change table (deferred until multi-year data exists) -- should also be considered. The most impactful external data integration is the CIP-to-SOC crosswalk + BLS OOH, which would transform this from "school earnings" data into true "career guidance" data.

## Data Products -- Ranked

### Tier 1: High Value, High Feasibility

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|-------------|-------------|---------------|------------|----------------|
| 1 | **consumable.career_outcomes** | One row per institution-program-credential with percentile bands, debt-to-earnings ratio, confidence tier, and relative position within CIP family. Core consumable table. | base.college_scorecard | debt_to_earnings_annual, earnings percentile bands, confidence_tier | Powers the primary FutureProof query: school + major = career outcomes. Directly serves the effort slider (p25/p50/p75 bands). Already drafted as gold-career-outcomes-college-scorecard spec. |
| 2 | **consumable.cip_family_summary** | One row per CIP family (45 rows) with aggregate statistics: median earnings, median debt, mean DTE ratio, program count, institution count, data coverage rate. Pre-computed for fast LLM lookups. | consumable.career_outcomes | family_median_earnings, family_avg_dte, coverage_rate | LLMs will frequently ask "what does a typical Business graduate earn?" -- this answers that without scanning 8,402 rows. Also useful for "which fields pay the most/least?" ranking queries. 45 rows is trivially small and can be included in MCP system prompts as grounding context. |

**Verification Criteria (Product 1 - career_outcomes):**
- Row count = 69,947 (1:1 with Silver, no row drops per spec)
- Grain uniqueness: zero duplicates on unitid x cipcode x credlev
- debt_to_earnings_annual computable for exactly 21,763 rows (those with both earnings_1yr_median and debt_median non-null)
- Percentile bands: p25 <= p50 <= p75 for every CIP family where computed
- Percentile bands null for CIP families with < 3 non-null values (7 families: 28, 32, 33, 34, 35, 48, 53)
- Confidence tier distribution: ~52.7% insufficient, ~23.7% low, ~1.8% medium, ~21.8% high (within 5pp)
- DTE tier distribution: ~69% Low, ~30% Moderate, <1% High, <0.1% Very High (among computable rows)

**Verification Criteria (Product 2 - cip_family_summary):**
- Exactly 45 rows (one per CIP family observed in Silver)
- family_median_earnings for Engineering (CIP 14) should be ~$64,984
- family_median_earnings for Visual and Performing Arts (CIP 50) should be ~$24,757
- coverage_rate = count(non-null earnings) / count(total rows) per family; Business (52) should be ~49.6%

### Tier 2: High Value, Moderate Effort

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|-------------|-------------|---------------|------------|----------------|
| 3 | **consumable.institution_program_rankings** | Top/bottom programs per institution ranked by earnings and program value index. Pre-computed for "best programs at school X" queries. | consumable.career_outcomes | cip_family_earnings_rank, program_value_index | The second most common user question after "how much does X earn" is "what are the best programs at my school?" Pre-computing these rankings avoids complex window queries at MCP query time. |
| 4 | **reference.cip_soc_crosswalk** | CIP-to-SOC crosswalk reference table. Many-to-many mapping between academic programs and occupations. Foundation for all BLS/O*NET integration. | NCES CIP-SOC crosswalk (external) | cip_code, soc_code, match_confidence | Without this table, FutureProof cannot answer "what jobs can I get with this degree?" -- which is the central product question. This is the most important reference table in the entire pipeline. |

**Verification Criteria (Product 3):**
- Rankings within each institution sum to the expected set of programs for that institution
- Top-ranked program per institution has highest earnings_1yr_median among that institution's programs
- program_value_index rankings should roughly correlate with earnings rank (r > 0.5)

**Verification Criteria (Product 4):**
- CIP codes in crosswalk should cover >90% of the 390 CIP codes in our Silver table
- SOC codes should be valid 6-digit XX-XXXX format
- Many-to-many: average CIP should map to 2-5 SOC codes

### Tier 3: Exploratory / Future

| # | Data Product | Description | Dependency | Why It Matters |
|---|-------------|-------------|------------|----------------|
| 5 | **consumable.period_over_period** | YoY earnings and debt changes with growth rates and 3-year CAGR. | Requires multi-year College Scorecard ingestion (currently single snapshot). | Mandatory per Brightsmith framework if 3+ years of data exist. Currently blocked -- single snapshot only. Recommend ingesting 3 historical College Scorecard releases to enable this. |
| 6 | **consumable.career_projections** | Programs joined with BLS occupation projections and O*NET AI exposure scores. The "full FutureProof" data product. | reference.cip_soc_crosswalk + BLS OOH ingest + O*NET ingest | This is the ultimate product goal: "Study X at Y, earn Z, in an occupation growing at G% with AI exposure of A." Requires 3 additional data sources. |
| 7 | **consumable.institution_comparison** | Side-by-side comparison of institutions offering the same program, with earnings, debt, and value index differences. | consumable.career_outcomes | Answers "Should I study CS at State U or Private U?" -- direct student decision-making support. |

## Cross-Entity Coverage Matrix

| CDE | Attribute | Entities Reporting | Time Range | Coverage Quality |
|-----|----------|-------------------|------------|-----------------|
| BT-001 | unitid (Institution ID) | 2,559 (100%) | Single snapshot | EXCELLENT -- zero nulls, all valid 6-digit IPEDS IDs |
| BT-003 | cipcode (Program Code) | 390 distinct across 69,947 rows | Single snapshot | EXCELLENT -- zero nulls, all valid CIP codes |
| BT-009 | earnings_1yr_median | 25,196 rows (36.0%) | Single snapshot | MODERATE -- 64% null due to privacy suppression. Coverage is strong for large programs (88.7% where completions >= 30) |
| BT-010 | earnings_2yr_median | 27,681 rows (39.6%) | Single snapshot | MODERATE -- 60.4% null. Slightly better coverage than 1yr. 12.3% of rows have different 1yr vs 2yr suppression status |
| BT-011 | debt_median | 25,809 rows (36.9%) | Single snapshot | MODERATE -- 63.1% null. Not always jointly available with earnings (only 21,763 have both earnings + debt) |
| BT-012 | completions_count_1 | 63,849 rows (91.3%) | Single snapshot | GOOD -- 8.7% null. Drives small_cohort_flag. 12.4% of non-null values are zero. |
| BT-014 | small_cohort_flag | 69,947 (100%) | Single snapshot | EXCELLENT -- derived, always populated. 75.5% flagged True. |
| N/A | institution_control | 0 rows (0%) | N/A | GAP -- field is 100% null in current Silver table. CONTROL was not included in Bronze parquet. Blocks institution-type segmentation. |

## External Data Opportunities

| External Source | Join Key | What It Unlocks | Effort | Priority |
|----------------|----------|-----------------|--------|----------|
| **NCES CIP-SOC Crosswalk** (https://nces.ed.gov/ipeds/cipcode/) | cipcode (XX.XX format) -> SOC code (XX-XXXX format) | Maps academic programs to occupations. Foundation for ALL occupation-based analysis. Many-to-many relationship. | LOW -- single CSV download, ~5,000 rows, straightforward reference table ingest | P0 -- CRITICAL DEPENDENCY for BLS and O*NET integration |
| **BLS Occupational Outlook Handbook** (https://www.bls.gov/ooh/) | SOC code (via crosswalk) | Occupation descriptions, 10-year projected job growth %, typical education, median pay by occupation. Answers "what jobs can I get and are they growing?" | MEDIUM -- API or scrape, ~300 occupation entries, joins via SOC code | P1 -- HIGH VALUE. Second planned data source per manifest.yaml |
| **O*NET Task-Level Data** (https://www.onetcenter.org/database.html) | SOC code (via crosswalk) | Task-level occupation decomposition, work activities, skills, technology tools. Enables AI exposure analysis: "what % of this job's tasks can be automated?" | MEDIUM -- bulk download, ~1,000 occupations x multiple task files. Joins via SOC code | P1 -- HIGH VALUE. Third planned data source. Enables the "AI exposure" analysis that is core to FutureProof |
| **IPEDS Institutional Characteristics** (https://nces.ed.gov/ipeds/datacenter/) | unitid | Institution type (public/private/for-profit), state, region, Carnegie classification, enrollment size. Enables segmentation: "Do for-profit schools have worse DTE ratios?" | LOW -- single CSV, joins on unitid directly | P2 -- MEDIUM VALUE. Could substitute for the missing institution_control field AND add geographic context |
| **BLS Occupational Employment and Wage Statistics (OES)** (https://www.bls.gov/oes/) | SOC code (via crosswalk) | Actual occupation-level earnings percentiles (10th/25th/50th/75th/90th). Would provide real within-occupation earnings distributions rather than our cross-institution proxy percentile bands. | MEDIUM -- annual release, ~800 occupations with wage percentiles | P2 -- Would significantly improve earnings percentile accuracy but requires crosswalk first |
| **College Scorecard Historical Releases** (https://collegescorecard.ed.gov/data/) | unitid + cipcode + credlev (same grain) | Multi-year tracking: earnings trends, debt trends, program growth/decline. Enables period-over-period analysis (currently blocked by single snapshot). | LOW -- same format as current ingest, just additional years | P2 -- Would unlock Tier 3 Product #5 (period_over_period) |

## Coverage Gaps and Risks

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **institution_control is 100% null** | Cannot segment outcomes by Public / Private nonprofit / Private for-profit. This is a known high-value analysis dimension (for-profit institutions are known to have worse debt-to-earnings ratios). | Re-run raw ingestor to include CONTROL field from source CSV. Alternatively, join IPEDS Institutional Characteristics data on unitid. The Gold spec should proceed without this field and add it when available. |
| **64% of rows lack earnings data** | Only 25,196 of 69,947 rows have 1yr earnings. Percentile bands for small CIP families will be based on very few data points. 7 CIP families have < 3 data points (bands will be null). | The Gold spec already handles this: percentile bands require minimum 3 values per CIP family, and confidence_tier flags data availability. The 25,196 rows with earnings cover the programs that matter most (large programs at established institutions). |
| **No occupation mapping (CIP-to-SOC crosswalk missing)** | Cannot answer "what jobs can I get with this degree?" -- the central FutureProof question. Gold zone career_outcomes table is "halfway there" without occupation data. | Ingest CIP-SOC crosswalk as a reference table. This should be the FIRST external data source prioritized after the Gold zone is complete. |
| **Single snapshot -- no temporal dimension** | Cannot compute period-over-period changes, identify trend directions, or assess whether programs are improving or declining. CAGR calculation impossible. | Ingest 2-3 historical College Scorecard releases (same format, same ingest pattern). Low effort, high value for trend analysis. |
| **2yr earnings < 1yr earnings in 44.2% of cases** | Users and LLMs will misinterpret the earnings_growth_rate field as indicating career regression. The median growth rate is only 1.4%, misleadingly low because these are different cohorts, not longitudinal tracking. | The Gold spec includes earnings_growth_rate but it MUST be accompanied by strong documentation explaining the cohort difference. The MCP system prompt must include a grounding caveat about this. Consider renaming to "cohort_earnings_difference" to avoid implying individual progression. |
| **Extreme DTE outliers** | 5 rows have DTE > 2.5 ("Very High") and 175 rows have DTE > 1.5 ("High" or above). While valid, these could skew aggregate statistics and surprise users. | The Gold spec's debt_to_earnings_tier field handles this well by bucketing. The MCP layer should present the tier label, not the raw ratio, for most queries. |

## AI-Ready Considerations

### Data Shapes for LLM Consumption

1. **CIP Family Summary (45 rows) should be embedded in the MCP system prompt.** This is small enough to include as grounding context and answers the most common class of questions ("what does a typical [field] graduate earn?") without any tool calls.

2. **The career_outcomes table should be queryable via parameterized SQL, not loaded in full.** At 69,947 rows with ~30 columns, it is too large for context windows. The MCP server should expose tool calls like `lookup_program(institution, program)` and `compare_programs(cip_family)`.

3. **Confidence tier should be prominently surfaced.** LLMs tend to present data as authoritative regardless of confidence. The MCP system prompt should instruct the LLM to always mention the confidence tier and to caveat "insufficient" tier results.

4. **Pre-computed aggregations that should exist for fast LLM access:**
   - CIP family summary (45 rows) -- system prompt embedding candidate
   - Top 10 / Bottom 10 programs by earnings -- common ranking query
   - Institution program counts and coverage rates -- answers "how much data do we have for school X?"
   - DTE tier distribution summary -- answers "what percentage of programs have concerning debt levels?"

5. **Natural language descriptions needed:**
   - Each CIP family should have a 1-sentence plain-English description (e.g., "CIP 14 (Engineering) covers programs like mechanical, electrical, and civil engineering")
   - The debt-to-earnings tier thresholds need plain-English interpretations (already in Gold spec)
   - The confidence tier needs a plain-English explanation of what "insufficient" means and why

### Context the LLM Needs

- **The 1yr vs 2yr earnings caveat** -- different cohorts, not longitudinal tracking. This MUST be in the system prompt.
- **Privacy suppression explanation** -- why 64% of programs lack earnings data (FERPA, not missing data)
- **Cross-institution percentile bands explanation** -- what p25/p50/p75 mean (distribution of program medians across schools, not individual student outcomes)
- **Institution control gap** -- the LLM should know that institution type segmentation is not yet available

## Chat Agent Design Considerations

### Questions Users Will Ask (Preliminary for Gold-to-MCP Transition)

| Category | Example Questions | Data Source | Complexity |
|----------|------------------|-------------|------------|
| **Point Lookup** | "What is the median earnings for Computer Science graduates from MIT?" | career_outcomes WHERE unitid + cipcode match | Simple -- direct row lookup |
| **Program Comparison** | "How does nursing compare to business in terms of earnings?" | cip_family_summary or career_outcomes aggregated by cip_family | Medium -- requires aggregation |
| **Ranking** | "What are the top 10 highest-paying majors?" | career_outcomes or cip_family_summary ORDER BY earnings | Medium -- window function or pre-computed |
| **Affordability** | "Which programs have the best debt-to-earnings ratios?" | career_outcomes WHERE debt_to_earnings_tier = 'Low' | Medium -- filter + sort |
| **Institution Comparison** | "Is Stanford CS worth it compared to state schools?" | career_outcomes filtered by cipcode, compared across unitids | Complex -- multi-row comparison |
| **Range/Effort** | "What is the earnings range for engineering graduates?" | career_outcomes percentile bands for CIP 14 | Simple -- direct column read |
| **Meta/Coverage** | "How reliable is the data for small liberal arts colleges?" | career_outcomes confidence_tier + completions_count | Medium -- requires understanding confidence tiers |

### MCP Server Tools Needed (Preliminary)

1. `lookup_program(institution_name_or_id, program_name_or_cip)` -- Point lookup
2. `compare_programs(cip_codes_or_names[], metric)` -- Side-by-side comparison
3. `rank_programs(by_metric, cip_family_filter?, top_n?)` -- Ranking with optional filters
4. `institution_programs(institution_name_or_id)` -- All programs at a school
5. `cip_family_overview(cip_family_code_or_name)` -- Aggregate family stats

### Grounding Context for System Prompt

The system prompt should include:
- The 45-row CIP family summary table (small enough to embed)
- Plain-English explanation of confidence tiers and what they mean
- The 1yr vs 2yr cohort caveat
- Privacy suppression explanation
- Debt-to-earnings tier definitions
- List of available tools and what they return
- Instruction to always mention confidence tier when presenting data

## Recommended Spec Order

### Gold Zone Specs (in order)

1. **gold-career-outcomes-college-scorecard** (ALREADY DRAFTED -- Status: DRAFT)
   - The core consumable table. Highest priority. No dependencies within Gold zone.
   - Estimated effort: Medium (transformer + DQ rules + governance artifacts)
   - Dependencies: base.college_scorecard (Silver, COMPLETE)

2. **gold-cip-family-summary** (NEW -- to be drafted)
   - 45-row aggregate table. Depends on consumable.career_outcomes being built first.
   - Estimated effort: Low (simple GROUP BY aggregation from career_outcomes)
   - Dependencies: consumable.career_outcomes (Gold, product #1)

### Deferred (Not Gold Zone -- Future Work)

3. **raw-ingest-cip-soc-crosswalk** (Raw zone -- reference table ingest)
   - The CIP-to-SOC crosswalk. Should be the NEXT raw ingest after Gold zone is complete.
   - Enables all occupation-based analysis.
   - No Gold zone dependency -- can be ingested independently.

4. **raw-ingest-bls-ooh** (Raw zone -- second data source)
   - BLS Occupational Outlook Handbook. Depends on crosswalk for joining.

5. **raw-ingest-onet** (Raw zone -- third data source)
   - O*NET task-level data. Depends on crosswalk for joining.

6. **gold-career-projections** (Gold zone -- cross-source integration)
   - The "full FutureProof" product combining earnings + occupation projections + AI exposure.
   - Depends on all three external sources being ingested and integrated in Silver.

### Note on Mandatory Tier 1 Products

Per Brightsmith framework rules:
- **Deduplicated metrics table**: The career_outcomes table IS the deduplicated metrics table (one row per entity-metric-period).
- **Computed ratios**: debt_to_earnings_annual and program_value_index are computed ratios, included in career_outcomes.
- **Period-over-period changes**: BLOCKED by single-snapshot constraint. Cannot build until multi-year data is ingested. This is documented as Tier 3 Product #5. Deferral is justified.
