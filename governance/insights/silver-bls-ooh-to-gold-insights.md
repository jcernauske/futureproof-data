# Insight Report: Silver BLS OOH to Gold
**Date:** 2026-04-07
**Agent:** @insight-manager
**Source Tables:** base.bls_ooh (Silver zone)
**Entities:** 832 occupations across 22 SOC major groups
**Records:** 832
**Time Range:** 2024-2034 BLS Employment Projections cycle (single snapshot)

## Domain Context
From `governance/domain-context.md`: This is a Higher Education Outcomes domain. The BLS Employment Projections data is the second data source in the FutureProof pipeline, providing occupation-level employment growth, wages, and education requirements classified by SOC codes (Standard Occupational Classification). The core integration challenge is the CIP-to-SOC crosswalk that bridges College Scorecard programs (CIP codes) to career outcomes (SOC codes). This Silver table establishes the SOC-side anchor for that bridge.

## Executive Summary

The Silver `base.bls_ooh` table is in excellent shape for Gold zone promotion: 832 rows, 36/36 DQ rules passing at 100%, zero P0 failures, and only 23 null-wage rows (2.8%) representing a well-understood population of physicians and performers. The data is remarkably complete -- every field except `median_annual_wage` has zero nulls. The highest-value Gold data product is `consumable.occupation_profiles`, already drafted as a spec, which computes GRW scores (1-10 growth stat), market scores, wage percentile ranks, and occupation confidence tiers. This product is self-contained and does not require the CIP-SOC crosswalk to deliver value -- it stands alone as an occupation reference that Gemma can query directly. The primary risk is not data quality (which is strong) but rather the 77 occupations (7 broad + 70 catchall) that carry inherently weaker career guidance signal due to their heterogeneous nature.

## Data Products -- Ranked

### Tier 1: High Value, High Feasibility

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|-------------|-------------|---------------|------------|----------------|
| 1 | **consumable.occupation_profiles** | One row per occupation with GRW score (1-10), market score (1-10), wage percentile ranks (overall and within education tier), wage tier, confidence tier, and FutureProof stat mappings. The occupation reference table for Gemma and the frontend. | base.bls_ooh | grw_score, market_score, wage_percentile_overall, confidence_tier | Directly backs the GRW pentagon stat and Market/Ceiling boss fights. Self-contained -- works without the crosswalk. Already drafted as `gold-occupation-profiles-bls-ooh`. |
| 2 | **consumable.soc_major_group_summary** | One row per SOC major group (22 rows) with aggregate statistics: median wage, mean GRW score, occupation count, growth distribution, employment totals. Pre-computed for fast LLM lookups and system prompt embedding. | consumable.occupation_profiles | group_median_wage, group_mean_grw, occupation_count | LLMs will frequently ask "how is the healthcare field doing?" or "which sectors are growing fastest?" This answers those questions without scanning 832 rows. 22 rows is small enough to embed in MCP system prompts as grounding context. Analogous to `consumable.cip_family_summary` on the College Scorecard side. |

**Verification Criteria (Product 1 - occupation_profiles):**
- Row count = 832 (1:1 with Silver, no rows added or dropped)
- Grain uniqueness: zero duplicates on soc_code
- grw_score range: 1.0-10.0 for all non-null rows; null only when employment_change_pct is null (0 rows currently, so 0 nulls expected)
- grw_score for Software Developers (15-1252): employment_change_pct=15.8 should produce grw_score of approximately 8.37 (interpolated in 10.0-20.0 band)
- grw_score for Registered Nurses (29-1141): employment_change_pct=4.9 should produce grw_score of approximately 6.46 (interpolated in 1.0-5.0 band)
- wage_percentile_overall null count = 23 (the null-wage occupations)
- confidence_tier distribution: "high" should be the majority (832 - 7 broad - 70 catchall - 23 null-wage + overlaps); "low" count = exactly 23
- backs_stats = "ERN,GRW" for all 832 rows
- backs_bosses = "Market,Ceiling" for all 832 rows
- market_score null count = 0 (all rows have both employment_change_pct and openings_annual_avg)

**Verification Criteria (Product 2 - soc_major_group_summary):**
- Exactly 22 rows (one per SOC major group)
- group_median_wage for Computer and Mathematical (15) should be approximately $100K+ (tech occupations)
- group_median_wage for Food Preparation and Serving (35) should be among the lowest
- occupation_count for Production (51) = 105 (largest group per EDA)
- occupation_count for Legal (23) = 8 (smallest group per EDA)
- All group-level aggregations should exclude null-wage rows from wage computations

### Tier 2: High Value, Moderate Effort

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|-------------|-------------|---------------|------------|----------------|
| 3 | **consumable.education_pathway_profiles** | One row per education_code (8 rows) with wage distributions, growth distributions, occupation counts, and representative occupations. Shows "what does the job market look like at each education level?" | consumable.occupation_profiles | tier_median_wage, tier_mean_grw, tier_occupation_count | Directly answers the FutureProof question "is a bachelor's degree worth it?" by showing the wage and growth landscape at each education level. The wage_percentile_education_tier in occupation_profiles provides individual positioning; this table provides the tier-level context. 8 rows -- trivially embeddable in system prompts. |
| 4 | **consumable.growth_leaders** | Top 20 and bottom 20 occupations by employment_change_pct, with full profile data. Pre-computed ranking table for "fastest growing" and "most declining" queries. | consumable.occupation_profiles | employment_change_pct, grw_score, occupation_title | "What are the fastest growing careers?" is one of the most common career guidance questions. Pre-computing this avoids window-function queries at MCP query time and provides a stable, curated list that excludes catchall/broad occupations for cleaner results. |

**Verification Criteria (Product 3):**
- Exactly 8 rows (one per education code, 1-8)
- tier_median_wage should increase monotonically from education_code 8 (No formal) to education_code 1 (Doctoral), with possible exceptions for code 6 (Some college) which has only 7 occupations
- tier_occupation_count for code 7 (High school) = 326 (largest per EDA)
- tier_occupation_count for code 6 (Some college) = 7 (smallest per EDA)

**Verification Criteria (Product 4):**
- 40 rows total (20 top + 20 bottom)
- Top-1 occupation should be the one with employment_change_pct = 49.9 (max in dataset)
- Bottom-1 occupation should be Word Processors and Typists (43-9022) with -36.1% (min in dataset)
- No catchall_flag = True or broad_occupation_flag = True occupations in the list (filtered out for cleaner guidance)

### Tier 3: Exploratory / Future

| # | Data Product | Description | Dependency | Why It Matters |
|---|-------------|-------------|------------|----------------|
| 5 | **consumable.career_projections** (cross-source) | Programs joined with occupation projections via CIP-SOC crosswalk. The "full FutureProof" data product answering "study X at Y, earn Z, in an occupation growing at G%." | reference.cip_soc_crosswalk (Silver), base.college_scorecard (Silver), consumable.occupation_profiles (Gold) | This is the ultimate product goal -- connecting school+major to career outcomes. Requires the crosswalk table to exist first. |
| 6 | **consumable.ai_exposure_profiles** | Occupations scored by AI task exposure using O*NET task-level data and Karpathy-style AI capability scoring. | base.onet (Silver -- not yet ingested), consumable.occupation_profiles (Gold) | Backs the RES and HMN pentagon stats and the AI boss fight. Core differentiator of FutureProof vs. generic career guidance tools. Blocked on O*NET ingest. |
| 7 | **consumable.period_over_period_occupations** | BLS projection cycle comparison (2022-2032 vs 2024-2034). | Second BLS EP cycle ingest (different vintage year) | Shows whether occupation growth outlooks are improving or deteriorating across projection cycles. Blocked on multi-vintage ingestion. |

## Cross-Entity Coverage Matrix

| CDE | Attribute | Entities Reporting | Time Range | Coverage Quality |
|-----|----------|-------------------|------------|-----------------|
| BT-027 | soc_code (Occupation ID) | 832 (100%) | 2024-2034 projection | EXCELLENT -- zero nulls, all valid XX-XXXX format, 100% unique grain |
| BT-028 | occupation_title | 832 (100%) | 2024-2034 | EXCELLENT -- zero nulls, 1:1 with soc_code |
| N/A | employment_current | 832 (100%) | 2024 base year | EXCELLENT -- zero nulls, all positive |
| N/A | employment_change_pct | 832 (100%) | 2024-2034 delta | EXCELLENT -- zero nulls, range -36.1% to +49.9% |
| N/A | openings_annual_avg | 832 (100%) | 2024-2034 annual avg | EXCELLENT -- zero nulls (4 zeros from BLS rounding, valid) |
| N/A | median_annual_wage | 809 (97.2%) | 2024 | STRONG -- 23 nulls are well-understood (physicians, performers). Not a gap, a structural feature of BLS reporting. |
| N/A | education_code | 832 (100%) | 2024 | EXCELLENT -- all 8 education levels represented, zero nulls |
| N/A | growth_category | 832 (100%) | derived from pct | EXCELLENT -- all 6 categories populated, distribution skews toward "growing" (57.8%) as expected |
| N/A | broad_occupation_flag | 7 of 832 (0.8%) flagged True | N/A | EXCELLENT -- hardcoded list from SOC audit, all 7 confirmed |
| N/A | catchall_flag | 70 of 832 (8.4%) flagged True | N/A | EXCELLENT -- corrected from initial 46 estimate to 70 after Silver EDA |

## Cross-Source Integration: BLS OOH x College Scorecard

This is the critical integration analysis. The two Silver tables are:
- `base.college_scorecard`: 69,947 rows, CIP codes (XX.XXXX), institution-program grain
- `base.bls_ooh`: 832 rows, SOC codes (XX-XXXX), occupation grain

### What the CIP-SOC Crosswalk Must Do

The NCES/BLS CIP-SOC crosswalk is a published many-to-many mapping (~5,000 rows). It enables:
- Each CIP code maps to 2-5 SOC codes on average
- Each SOC code may map from multiple CIP codes
- Join key: `base.college_scorecard.cipcode` (after dot-insertion to XX.XXXX format) to crosswalk `cipcode`, then crosswalk `soc_code` to `base.bls_ooh.soc_code`

### Coverage Expectations

- 390 distinct CIP codes exist in College Scorecard Silver
- The crosswalk should cover >90% of those 390 CIP codes
- The 832 SOC codes in BLS OOH cover the full detailed occupation universe; crosswalk SOC codes should all find matches
- 7 broad occupation codes may map differently in the crosswalk (parent codes that fan out to O*NET children)
- 70 catchall categories will have crosswalk matches but provide weaker guidance signal

### Integration Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broad occupation codes (7) match multiple O*NET children | Crosswalk join may produce unexpected fan-out | broad_occupation_flag already set in Silver; Gold confidence_tier downgrades these to "medium" |
| Catchall categories (70) match generic crosswalk entries | Career guidance for "Managers, all other" is inherently vague | catchall_flag already set; Gold confidence_tier handles this |
| CIP codes that map to zero SOC codes | Some niche programs may not appear in the crosswalk | Crosswalk coverage check is a DQ rule; fallback to CIP family-level matching at soc_major_group |
| SOC codes that receive zero CIP mappings | Some occupations are not primarily reached via academic programs | Expected for trades, military, etc. Not a data quality issue. |
| Many-to-many explosion | A student's program maps to 5 occupations, each with different stats | Gold zone must decide: show all mapped occupations, show weighted average, or show best/worst range |

## External Data Opportunities

| External Source | Join Key | What It Unlocks | Effort | Priority |
|----------------|----------|-----------------|--------|----------|
| **NCES CIP-SOC Crosswalk** (https://nces.ed.gov/ipeds/cipcode/) | cipcode (XX.XXXX) to soc_code (XX-XXXX) | Bridges College Scorecard programs to BLS occupations. Foundation for ALL cross-source analysis. Enables "study X, work as Y" queries. | LOW -- single CSV, ~5,000 rows, reference table ingest | P0 -- CRITICAL. Already identified in prior insight report. Required for the full FutureProof product. |
| **O*NET Task-Level Data** (https://www.onetcenter.org/database.html) | soc_code (direct join to base.bls_ooh) | Task decomposition, work activities, skills, technology tools per occupation. Enables AI exposure scoring (RES/HMN stats), burnout boss fight, and Stage 3 career pathway branching. | MEDIUM -- bulk download, multiple files, ~1,000 occupations | P1 -- HIGH VALUE. Third planned data source. Completes the pentagon (RES + HMN stats). |
| **BLS OES Wage Percentiles** (https://www.bls.gov/oes/) | soc_code (direct join) | Actual 10th/25th/50th/75th/90th wage percentiles per occupation. Currently we only have median from EP data; OES provides the full distribution. Would power the Ceiling boss fight with real ceiling data instead of cross-occupation percentile proxy. | LOW -- annual CSV, ~800 occupations, direct SOC join | P2 -- MEDIUM VALUE. Significantly improves wage analysis but not blocking any Gold product. |
| **BLS EP Prior Vintage** (2022-2032 projections) | soc_code (same grain, different vintage) | Period-over-period comparison of occupation growth outlooks. Shows whether a field's prospects are improving or deteriorating. | LOW -- same format as current ingest, historical download | P3 -- FUTURE. Enables Tier 3 Product #7. Not urgent. |

## Coverage Gaps and Risks

| Gap | Impact | Mitigation |
|-----|--------|------------|
| **23 null-wage occupations** | Cannot compute ERN stat or wage percentile for 23 occupations (14 physicians/surgeons, 5 performers, 4 others). These are high-value careers (physicians) with missing data. | Gold spec handles this: confidence_tier = "low" for null-wage rows. For physicians specifically, BLS OES data (external) could supplement. The Gold spec's wage_available flag makes this transparent. |
| **70 catchall categories (8.4% of occupations)** | Career guidance for "all other" categories is inherently vague. A student mapped to "Business operations specialists, all other" (13-1199) gets less actionable guidance than "Management analysts" (13-1111). | Gold spec handles this: confidence_tier = "medium" for catchall/broad occupations. MCP system prompt should instruct Gemma to caveat results from catchall occupations. |
| **7 broad occupation codes (0.8%)** | Crosswalk behavior uncertain -- these parent codes may fan out to multiple O*NET children or match inconsistently. | Gold spec handles this: broad_occupation_flag preserved, confidence_tier = "medium". Crosswalk spec must decide fan-out strategy. |
| **No O*NET data yet** | Cannot compute RES stat (AI resilience), HMN stat (human skills), AI boss fight, or Burnout boss fight. The pentagon is half-empty without O*NET. | O*NET ingest is the next planned data source after the crosswalk. GRW + partial ERN + Market + Ceiling are available now. |
| **Single projection cycle** | Cannot assess whether occupation outlooks are improving or deteriorating over time. Growth of 15% in the 2024-2034 cycle might be better or worse than the prior cycle. | Low priority. BLS projections are long-horizon (10-year); single-cycle data is standard for career guidance. Multi-vintage is a nice-to-have. |
| **BLS rounding artifacts** | 12 rows have employment_change=0 but employment_change_pct<0 due to BLS rounding from thousands. 4 occupations have zero openings for the same reason. | Documented in Silver EDA; not a data quality issue. DQ rules explicitly do NOT enforce sign consistency between fields. Gold derivations use employment_change_pct (the precise field), not employment_change. |

## AI-Ready Considerations

### Data Shapes for LLM Consumption

1. **SOC Major Group Summary (22 rows) should be embedded in the MCP system prompt.** Small enough for direct context, answers the most common class of questions ("how is healthcare doing?", "which sectors are growing?") without tool calls. Analogous to the 45-row CIP family summary on the College Scorecard side.

2. **The occupation_profiles table should be queryable via parameterized SQL.** At 832 rows with ~25 columns, it is small enough that a full scan is feasible but wasteful. The MCP server should expose tool calls like `lookup_occupation(soc_code_or_title)`, `compare_occupations(soc_codes[])`, and `rank_occupations(by_metric, filters)`.

3. **Confidence tier must be prominently surfaced.** LLMs present data as authoritative regardless of quality. The MCP system prompt must instruct Gemma to always mention confidence tier, and to specifically caveat "medium" tier (catchall/broad) and "low" tier (null-wage) results.

4. **Pre-computed aggregations for fast LLM access:**
   - SOC major group summary (22 rows) -- system prompt embedding candidate
   - Education pathway profiles (8 rows) -- system prompt embedding candidate
   - Top/bottom 20 by growth -- common ranking query
   - Growth category distribution (6 values with counts) -- answers "how many careers are declining?"

5. **Natural language descriptions needed:**
   - Each SOC major group needs a 1-sentence plain-English description (e.g., "SOC 29 (Healthcare Practitioners) covers physicians, nurses, therapists, and other clinical roles")
   - Growth category labels need plain-English interpretations (e.g., "booming means employment is projected to grow 20%+ over the next decade -- roughly 4x the national average")
   - The confidence tier needs explanation of what "medium" and "low" mean and why
   - The GRW score scale needs explanation (e.g., "6.0 represents roughly average national growth of 4%")

### Context the LLM Needs

- **Projection cycle context** -- this is 2024-2034, a 10-year forward projection, not historical data
- **Growth score calibration** -- national average growth is ~4%, which maps to grw_score of ~6.0; "average" is slightly above midpoint by design
- **Null-wage explanation** -- 23 occupations (mostly physicians) lack wage data because BLS does not report standard median wages for these categories; this does NOT mean they have low wages
- **Catchall occupation caveat** -- 70 occupations are residual "all other" categories that represent heterogeneous groups; career guidance from these is inherently less specific
- **BLS data authority** -- this is authoritative federal labor market data, not survey or estimated data

## Chat Agent Design Considerations

### Questions Users Will Ask (Preliminary)

| Category | Example Questions | Data Source | Complexity |
|----------|------------------|-------------|------------|
| **Point Lookup** | "What's the growth outlook for software developers?" | occupation_profiles WHERE soc_code or title match | Simple -- direct row lookup |
| **Comparison** | "How does nursing compare to teaching in terms of growth and pay?" | occupation_profiles filtered by occupation or major group | Medium -- multi-row comparison |
| **Ranking** | "What are the fastest growing careers that require a bachelor's degree?" | occupation_profiles filtered by education_code, sorted by grw_score | Medium -- filter + sort |
| **Sector Overview** | "How is the healthcare sector doing overall?" | soc_major_group_summary for group 29/31 | Simple if pre-computed; medium otherwise |
| **Education ROI** | "Is a master's degree worth it vs. a bachelor's?" | education_pathway_profiles or occupation_profiles aggregated by education_code | Medium -- requires education tier comparison |
| **Declining Fields** | "Which careers are dying?" | occupation_profiles WHERE growth_category IN ('declining', 'declining_fast') | Simple -- filter query |
| **Cross-Source** | "If I major in CS, what careers can I get and are they growing?" | career_projections (requires CIP-SOC crosswalk) | Complex -- blocked until crosswalk exists |

### MCP Server Tools Needed (Preliminary)

1. `lookup_occupation(title_or_soc_code)` -- Point lookup returning full occupation profile
2. `compare_occupations(identifiers[], metrics[])` -- Side-by-side comparison
3. `rank_occupations(by_metric, education_filter?, growth_filter?, top_n?)` -- Ranking with filters
4. `sector_overview(soc_major_group_code_or_name)` -- Pre-computed group summary
5. `occupations_by_education(education_level)` -- Filter by education requirement

### Grounding Context for System Prompt

The system prompt should include:
- The 22-row SOC major group summary (small enough to embed)
- The 8-row education pathway profile (small enough to embed)
- Growth category definitions with plain-English interpretations
- GRW score calibration explanation (6.0 = average national growth)
- Null-wage explanation (physicians, performers -- high earners with no BLS median)
- Confidence tier definitions and when to caveat
- Projection cycle context (2024-2034, 10-year forward look)

## Readiness Assessment: Silver to Gold

### Overall: READY TO PROCEED

| Dimension | Status | Evidence |
|-----------|--------|---------|
| **Data Quality** | PASS | 36/36 DQ rules passing (100%), zero P0 failures |
| **Completeness** | PASS | Only median_annual_wage has nulls (23 rows, 2.8%); all other fields 100% complete |
| **Grain Integrity** | PASS | 832 unique soc_codes, zero duplicates, deterministic record_id |
| **Classification Flags** | PASS | broad_occupation_flag (7 True), catchall_flag (70 True) -- both verified against EDA |
| **Derived Fields** | PASS | growth_category distribution verified, education_level_name lookup verified, all code-text mappings deterministic |
| **Data Contract** | PRESENT | `governance/data-contracts/base-bls-ooh.yaml` exists (draft status) |
| **Gold Spec** | DRAFTED | `docs/specs/gold-occupation-profiles-bls-ooh.md` exists with full schema, derivation rules, and golden dataset |
| **Blocking Issues** | NONE | No blockers for Gold zone entry |

### Specific Notes for Gold Implementation

1. **GRW score piecewise function has 8 segments.** The Gold spec defines breakpoints at -20, -10, -1, 1, 5, 10, 20, and 50. All boundary values exist in the data (rows at exactly -10.0, -1.0, 0.0, 1.0, 10.0, 20.0 per Silver EDA). Edge case testing is critical.

2. **Market score denominator is non-zero.** All 832 rows have non-null openings_annual_avg (4 zeros, but PERCENT_RANK handles zeros correctly). No division-by-zero risk.

3. **Wage percentile computation must exclude nulls.** The 23 null-wage rows should be excluded from the PERCENT_RANK window (not ranked as 0). The Gold spec says "null-safe: exclude nulls from ranking" which is correct.

4. **Confidence tier counts (expected):**
   - "high": 832 - 7 - 70 - 23 + 0 overlap = 732 (broad and catchall do not overlap per EDA; need to check wage-null overlap with broad/catchall)
   - "medium": 7 + 70 = 77 (minus any that also lack wages)
   - "low": 23 (null-wage occupations)
   - Note: if any of the 23 null-wage occupations are also broad or catchall, they should be "low" (wage_available=False overrides per spec)

5. **The Gold spec drops employment_change, median_wage_capped, education_typical, work_experience, training_typical, and ingested_at.** All justified in the spec. Silver preserves them for lineage.

## Recommended Spec Order

### Gold Zone Specs (in order)

1. **gold-occupation-profiles-bls-ooh** (ALREADY DRAFTED -- Status: DRAFT)
   - The occupation reference table. Highest priority for this data path. No dependencies within Gold zone.
   - Estimated effort: Medium (piecewise GRW function, window functions for percentiles, confidence tier logic)
   - Dependencies: base.bls_ooh (Silver, COMPLETE)
   - Blocking: Nothing. This is self-contained.

2. **gold-soc-major-group-summary** (NEW -- to be drafted after Product 1 is built)
   - 22-row aggregate table. Depends on consumable.occupation_profiles.
   - Estimated effort: Low (GROUP BY aggregation from occupation_profiles)
   - Dependencies: consumable.occupation_profiles (Gold, Product #1)

### Deferred (Not Gold Zone -- Cross-Source Integration Path)

3. **silver-cip-soc-crosswalk** (Silver zone -- reference table)
   - The CIP-to-SOC crosswalk. Should be the NEXT Silver spec after Gold occupation_profiles is complete.
   - Enables all cross-source analysis between College Scorecard and BLS OOH.
   - Can be developed in parallel with Gold occupation_profiles.

4. **gold-career-projections** (Gold zone -- cross-source)
   - The "full FutureProof" product joining College Scorecard earnings with BLS occupation stats via crosswalk.
   - Depends on: consumable.career_outcomes + consumable.occupation_profiles + reference.cip_soc_crosswalk

5. **raw-ingest-onet** (Raw zone -- third data source)
   - O*NET task-level data. Direct SOC join to base.bls_ooh.
   - Enables RES, HMN stats and AI/Burnout boss fights.

### Note on Mandatory Tier 1 Products

Per Brightsmith framework rules:
- **Deduplicated metrics table**: The occupation_profiles table IS the deduplicated metrics table (one row per occupation with all computed stats).
- **Computed ratios**: GRW score, market score, wage percentile ranks, and data_completeness are computed ratios, all included in occupation_profiles.
- **Period-over-period changes**: BLOCKED by single-projection-cycle constraint. Cannot build until a second BLS EP vintage is ingested. Deferral is justified -- BLS projections are inherently 10-year forward looks; comparing vintages is a nice-to-have, not a core need.
