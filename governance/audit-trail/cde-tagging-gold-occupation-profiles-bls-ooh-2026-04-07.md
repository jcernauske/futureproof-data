# CDE/PII Tagging Audit Trail: gold-occupation-profiles-bls-ooh

**Date:** 2026-04-07
**Agent:** @cde-tagger
**Spec:** gold-occupation-profiles-bls-ooh
**Zone:** Gold (Consumable)
**Table:** consumable.occupation_profiles
**Contract:** governance/data-contracts/consumable-occupation-profiles.yaml

## Domain Context Referenced

- **governance/domain-context.md** -- BLS OOH section confirms all data is occupation-level aggregates published by a federal statistical agency. No PII present. Applicable frameworks: SOC taxonomy (external standard), BLS Employment Projections methodology.
- **Logical model** (governance/models/gold-occupation-profiles-bls-ooh-logical.md) -- 9 CDEs identified: soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage (carried from Silver), grw_score, wage_percentile_overall, wage_percentile_education_tier, market_score (new derived in Gold).
- **Physical model** (governance/models/gold-occupation-profiles-bls-ooh-physical.md) -- 31 columns total. 5 CDE columns carried from Silver, 4 CDE columns new in Gold.
- **Silver contract** (governance/data-contracts/base-bls-ooh.yaml) -- Silver CDEs: soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage. Gold flags are independent per no-backward-propagation rule.

## CDE Tagging Decisions

### Columns Flagged as CDE (9 total)

| Column | Carried/New | Rationale |
|--------|-------------|-----------|
| soc_code | Carried | Natural key and sole grain field. Every downstream consumer (Gemma, game engine, crosswalk, O*NET) joins on soc_code. Incorrect values sever program-to-occupation linkage. |
| occupation_title | New in Gold | Primary user-facing display label consumed by Gemma agent and frontend. Elevated from non-CDE in Silver because in the Gold consumable layer this is the human-readable identifier students interact with. |
| employment_current | Carried | Primary input to Market boss fight and Gemma career descriptions. Distortion would mislead market size assessments. |
| employment_change_pct | Carried | Primary input to grw_score (GRW pentagon stat). Corruption cascades to grw_score, growth_category, market_score, and all growth guidance. |
| median_annual_wage | Carried | Backs ERN stat, Ceiling boss fight, and debt-to-earnings comparisons. Corruption cascades to 4 derived columns. |
| grw_score | New derived | Directly backs the GRW pentagon stat. Primary scored output consumed by game engine. Incorrect values miscalibrate pentagon and market_score. |
| wage_percentile_overall | New derived | Powers ERN stat relative positioning and wage_tier derivation. Misranking misclassifies occupations across wage tiers. |
| wage_percentile_education_tier | New derived | Directly backs the Ceiling boss fight. Shows how well a career pays relative to peers with same education. False impression would mislead students about education ROI. |
| market_score | New derived | Directly backs the Market boss fight. Composite score consumed by game engine. Miscalibration directly affects boss fight difficulty. |

### Divergences from Logical Model

| Column | Logical Model CDE | Gold Contract CDE | Rationale for Divergence |
|--------|-------------------|-------------------|--------------------------|
| occupation_title | false | true | Elevated in Gold because this is the consumable layer where the field is directly consumed by end users (students via Gemma and frontend). In Silver it was a display label; in Gold it is the primary human-facing identifier. |
| employment_projected | true | false | Demoted in Gold. While important as an input, its analytical signal is fully carried by employment_change_pct and grw_score in the Gold layer. Consumers do not use projected counts directly -- they use the derived percentage and score. The field can be recomputed from employment_current + employment_change_pct if needed. |

**Net effect:** 9 CDEs in both logical model and Gold contract, but 2 swaps (occupation_title promoted, employment_projected demoted).

## PII Tagging Decisions

### Columns Flagged as PII: None

**Rationale:** All data in this table is occupation-level aggregates published by the Bureau of Labor Statistics. Per governance/domain-context.md (BLS OOH PII section): "This dataset contains NO PII. All values are occupation-level aggregates published by a federal statistical agency." No personal names, individual identifiers, personal financial data, health records, or contact information are present. Wages are occupation-level medians, not individual compensation.

## Columns Evaluated -- Not Flagged

| Column | Reason Not Critical |
|--------|---------------------|
| record_id | Technical surrogate key. Infrastructure field not consumed by business processes. |
| soc_major_group | Derived from soc_code prefix. Grouping convenience field, not independently critical. |
| soc_major_group_name | Display label for major group. Lookup-derived from soc_major_group. |
| broad_occupation_flag | Input to confidence_tier. Boolean classification flag, not an analytical metric. |
| catchall_flag | Input to confidence_tier. Boolean classification flag, not an analytical metric. |
| employment_projected | Input to employment_change_pct. Analytical signal fully carried by employment_change_pct and grw_score in Gold. See divergence note above. |
| openings_annual_avg | Input to market_score (40% weight). While important, the scored market_score carries the critical signal to consumers. |
| growth_category | Bucketed from employment_change_pct. Derived label; grw_score is the primary analytical output. |
| grw_score_rounded | ROUND(grw_score). Derived from CDE grw_score; not independently critical. |
| wage_available | Convenience flag (NOT NULL check on median_annual_wage). Not independently critical. |
| wage_tier | Bucketed from wage_percentile_overall. Derived label; the percentile rank is the primary analytical output. |
| education_code | Categorical classification. Partition key for wage_percentile_education_tier but not independently critical. |
| education_level_name | Display label derived from education_code. |
| work_experience_code | Categorical classification. Informational, not primary analytical metric. |
| training_code | Categorical classification. Informational, not primary analytical metric. |
| market_score_rounded | ROUND(market_score). Derived from CDE market_score; not independently critical. |
| confidence_tier | Data quality metadata. Informational context, not a business metric. |
| data_completeness | Data quality metadata. Informational context, not a business metric. |
| backs_stats | Static documentation metadata. Always "ERN,GRW". |
| backs_bosses | Static documentation metadata. Always "Market,Ceiling". |
| source_load_date | Pipeline metadata. |
| promoted_at | Pipeline metadata. |
