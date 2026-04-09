# CDE/PII Tagging Audit: gold-futureproof-engine
**Date:** 2026-04-09
**Agent:** @cde-tagger
**Spec:** docs/specs/gold-futureproof-engine.md
**Physical Model:** governance/models/gold-futureproof-engine-physical.md
**Domain Context:** governance/domain-context.md

## Domain Context Referenced

- **Domain:** Higher Education Outcomes / Career Guidance
- **Regulatory context:** Department of Education Gainful Employment methodology; BCBS 239 principles applied to data criticality (columns critical to downstream business decisions and consumer-facing outputs)
- **PII context:** All source data is aggregated public statistics from College Scorecard, BLS OOH, and O*NET. PII scanner (governance/audit-trail/pii-scan-gold-futureproof-engine-2026-04-09.md) confirmed zero PII. No individual-level data present.
- **Downstream consumers:** MCP layer (/bs:serve), Gemma agent, frontend pentagon/boss fight/branch tree rendering

## Physical Model Discrepancy

The physical model summary states "15 CDE columns" for program_career_paths, but the column-level definitions contain 17 columns flagged as `Is CDE: true`. The column-level definitions are authoritative. The 2 additional CDEs (match_quality, overall_confidence) appear to have been added during model refinement after the summary was written. This tagger verified all 17 and concurs with the column-level flags.

## Table 1: consumable.program_career_paths (40 columns)

### Columns Flagged as CDE (17)

| Column | Business Term | Rationale |
|--------|---------------|-----------|
| unitid | BT-001 | Natural key; institution identifier required for all consumer queries |
| cipcode | BT-003 | Natural key; CIP-to-SOC crosswalk join pivots on this field |
| soc_code | BT-027 | Natural key; occupation identifier linking to BLS and O*NET |
| stat_ern | BT-078 | Pentagon stat: Earning Power; directly rendered in product UI |
| stat_roi | BT-079 | Pentagon stat: ROI; feeds boss_loans_score; Gainful Employment aligned |
| stat_grw | BT-047 | Pentagon stat: Growth; from BLS; directly rendered in product UI |
| stat_hmn | BT-066 | Pentagon stat: Human Edge; from O*NET; directly rendered in product UI |
| boss_loans_score | BT-084 | Boss fight score: Student Loans; derived from stat_roi |
| boss_market_score | BT-051 | Boss fight score: Market; from BLS; directly rendered in product UI |
| boss_burnout_score | BT-068 | Boss fight score: Burnout; from O*NET; directly rendered in product UI |
| boss_ceiling_score | BT-085 | Boss fight score: Ceiling; derived from wage percentile |
| earnings_1yr_median | BT-009 | Primary earnings metric; feeds stat_ern derivation (60% weight) |
| debt_median | BT-011 | Primary debt metric; feeds debt_to_earnings_annual and stat_roi |
| debt_to_earnings_annual | BT-019 | Key affordability ratio; Gainful Employment aligned; feeds stat_roi |
| median_annual_wage | BT-036 | BLS wage; feeds stat_ern derivation (40% weight) |
| match_quality | BT-093 | Cross-source join quality signal; consumed by MCP layer |
| overall_confidence | BT-089 | Synthesized quality tier; controls product display prominence |

### Columns Flagged as PII (0)

None. All data is aggregated public statistics.

### Columns Evaluated -- Not Flagged (23)

| Column | Reason Not Critical/Sensitive |
|--------|-------------------------------|
| record_id | Surrogate key; derived from natural key components; no business meaning |
| institution_name | Display label only; unitid is authoritative |
| program_name | Display label only; cipcode is authoritative |
| cip_family | Derived grouping field; not a direct input to business decisions |
| cip_family_name | Display label for cip_family |
| occupation_title | Display label only; soc_code is authoritative |
| soc_major_group_name | Display label; contextual only |
| stat_res | Placeholder (always null in MVP); no downstream consumers yet |
| boss_ai_score | Placeholder (always null in MVP); no downstream consumers yet |
| earnings_1yr_p25 | Supplementary context (effort slider bounds); not a primary metric |
| earnings_1yr_p75 | Supplementary context (effort slider bounds); not a primary metric |
| confidence_tier_program | Upstream confidence tier; subsumed by overall_confidence at this layer |
| growth_category | Categorical label derived from stat_grw; contextual enrichment |
| employment_current | Background context; not a primary decision metric |
| education_level_name | Background context; not a primary decision metric |
| top_5_activities | JSON enrichment for deep dive; not a primary decision metric |
| top_human_activities | JSON enrichment for deep dive; not a primary decision metric |
| burnout_drivers | JSON enrichment for deep dive; not a primary decision metric |
| time_pressure | Individual burnout element; subsumed by boss_burnout_score |
| work_hours | Individual work condition; subsumed by boss_burnout_score |
| stats_available_count | Internal quality metric; subsumed by overall_confidence |
| bosses_available_count | Internal quality metric; not directly consumed by product |
| promoted_at | Pipeline metadata; no business meaning |

## Table 2: consumable.career_branches (24 columns)

### Columns Flagged as CDE (2)

| Column | Business Term | Rationale |
|--------|---------------|-----------|
| soc_code | BT-027 | Natural key; source node in career branching graph |
| related_soc_code | BT-027 | Natural key; destination node in career branching graph |

### Columns Flagged as PII (0)

None. All data is aggregated public statistics.

### Columns Evaluated -- Not Flagged (22)

| Column | Reason Not Critical/Sensitive |
|--------|-------------------------------|
| record_id | Surrogate key; derived; no business meaning |
| source_title | Display label; soc_code is authoritative |
| related_title | Display label; related_soc_code is authoritative |
| best_index | Ranking metadata; contextual |
| relatedness_tier | Classification label; contextual |
| is_primary | Boolean filter flag; derived from best_index |
| source_grw | Enrichment stat; carried from upstream where it is a CDE |
| source_hmn | Enrichment stat; carried from upstream where it is a CDE |
| source_burnout | Enrichment stat; carried from upstream where it is a CDE |
| source_wage | Enrichment stat; carried from upstream where it is a CDE |
| related_grw | Enrichment stat for branch target; contextual comparison |
| related_hmn | Enrichment stat for branch target; contextual comparison |
| related_burnout | Enrichment stat for branch target; contextual comparison |
| related_wage | Enrichment stat for branch target; contextual comparison |
| related_growth_category | Categorical label; contextual |
| related_education_level | Background context; contextual |
| grw_delta | Derived difference; contextual comparison metric |
| hmn_delta | Derived difference; contextual comparison metric |
| burnout_delta | Derived difference; contextual comparison metric |
| wage_delta | Derived difference; contextual comparison metric |
| branch_has_full_data | Data quality flag; contextual |
| promoted_at | Pipeline metadata; no business meaning |

## CDE Tagging Rationale for career_branches

The career_branches table is an enrichment/denormalization of career_transitions. The stats carried into this table (source_grw, related_wage, etc.) are CDEs at their origin tables (occupation_profiles, onet_work_profiles) but are NOT marked as CDEs here because: (1) per Brightsmith convention, CDE flags do not propagate across zones/tables -- each table's flags are independent; (2) this table's primary purpose is pre-computation for frontend rendering convenience, not authoritative stat reporting; (3) the authoritative values live in the upstream Gold tables. Only the natural keys (soc_code, related_soc_code) are CDEs because they anchor the branching graph structure.

## Summary

| Table | Total Columns | CDEs | PII |
|-------|--------------|------|-----|
| consumable.program_career_paths | 40 | 17 | 0 |
| consumable.career_branches | 24 | 2 | 0 |
| **Total** | **64** | **19** | **0** |
