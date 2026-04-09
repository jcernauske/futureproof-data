# Lineage Audit Trail: gold-occupation-profiles-bls-ooh

**Agent:** @lineage-tracker
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Timestamp:** 2026-04-07T23:00:00Z
**Lineage File:** governance/lineage/gold-occupation-profiles-bls-ooh-20260407T230000Z.json

## Transformations Captured

| # | Transformation | Type | Source Field(s) | Target Field(s) | Notes |
|---|---------------|------|----------------|-----------------|-------|
| 1 | Identity carry | DIRECT | soc_code | soc_code | Natural key, no transformation |
| 2 | Identity carry | DIRECT | occupation_title | occupation_title | No transformation |
| 3 | Identity carry | DIRECT | soc_major_group | soc_major_group | No transformation |
| 4 | Identity carry | DIRECT | soc_major_group_name | soc_major_group_name | No transformation |
| 5 | Classification carry | DIRECT | broad_occupation_flag | broad_occupation_flag | Also input to confidence_tier |
| 6 | Classification carry | DIRECT | catchall_flag | catchall_flag | Also input to confidence_tier |
| 7 | Employment carry | DIRECT | employment_current | employment_current | Also input to data_completeness |
| 8 | Employment carry | DIRECT | employment_projected | employment_projected | No transformation |
| 9 | Employment carry | DIRECT | employment_change_pct | employment_change_pct | Primary input to grw_score |
| 10 | Employment carry | DIRECT | openings_annual_avg | openings_annual_avg | Input to openings_score and data_completeness |
| 11 | Growth category carry | DIRECT | growth_category | growth_category | Bucketed in Silver |
| 12 | Wage carry | DIRECT | median_annual_wage | median_annual_wage | Input to percentile derivations and data_completeness |
| 13 | Wage flag carry | DIRECT | wage_available | wage_available | Input to confidence_tier |
| 14 | Education carry | DIRECT | education_code | education_code | Also partitions wage_percentile_education_tier |
| 15 | Education name carry | DIRECT | education_level_name | education_level_name | No transformation |
| 16 | Experience carry | DIRECT | work_experience_code | work_experience_code | No transformation |
| 17 | Training carry | DIRECT | training_code | training_code | No transformation |
| 18 | GRW score derivation | DERIVED | employment_change_pct | grw_score | Piecewise linear, 8 segments, 1.0-10.0 scale |
| 19 | GRW score rounding | DERIVED | employment_change_pct | grw_score_rounded | round_half_up(grw_score), integer 1-10 |
| 20 | Wage percentile overall | DERIVED | median_annual_wage, soc_code | wage_percentile_overall | PERCENT_RANK, null-safe via LEFT JOIN |
| 21 | Wage percentile by education | DERIVED | median_annual_wage, education_code, soc_code | wage_percentile_education_tier | PERCENT_RANK partitioned by education_code |
| 22 | Wage tier bucketing | DERIVED | median_annual_wage | wage_tier | 5 tiers from wage_percentile_overall |
| 23 | Market score | DERIVED | employment_change_pct, openings_annual_avg | market_score | 0.6*grw + 0.4*openings_score |
| 24 | Market score rounding | DERIVED | employment_change_pct, openings_annual_avg | market_score_rounded | round_half_up(market_score), integer 1-10 |
| 25 | Confidence tier | DERIVED | wage_available, broad_occupation_flag, catchall_flag | confidence_tier | Priority: no-wage=low, broad/catchall=medium, else=high |
| 26 | Data completeness | DERIVED | median_annual_wage, employment_current, employment_change_pct, openings_annual_avg | data_completeness | Non-null count / 4 |
| 27 | Static stat mapping | DERIVED | (none) | backs_stats | Constant: "ERN,GRW" |
| 28 | Static boss mapping | DERIVED | (none) | backs_bosses | Constant: "Market,Ceiling" |
| 29 | Record ID | DERIVED | soc_code | record_id | compute_grain_id with 'op' prefix |
| 30 | Promotion timestamp | DERIVED | (none) | promoted_at | UTC timestamp at promote time |
| 31 | Provenance carry | DIRECT | source_load_date | source_load_date | Original BLS load date |

## Dropped Fields

| Field | Reason |
|-------|--------|
| record_id (Silver) | Replaced by Gold record_id with 'op' prefix (was 'ooh' prefix) |
| employment_change | Redundant with employment_change_pct; absolute change less useful for stat scoring |
| median_wage_capped | All False in current data; wage_available flag is more useful |
| education_typical | Redundant with education_level_name (normalized in Silver) |
| work_experience | Redundant with work_experience_code |
| training_typical | Redundant with training_code |
| ingested_at | Silver metadata; replaced by promoted_at in Gold |

## Naming Decisions

| Element | Name | Rationale |
|---------|------|-----------|
| Job name | gold.transform-occupation-profiles | Zone.action-entity pattern consistent with silver.transform-bls-ooh |
| Input dataset | base.bls_ooh | Silver zone catalog table name |
| Output dataset | consumable.occupation_profiles | Gold zone catalog table name per spec |
| Run ID | a3f19c72-8d4e-4b6a-91e3-7c5b2d0f6a18 | UUID v4, unique to this lineage capture |

## Interpretation Notes

1. **Hybrid SQL+Python execution:** The transformer uses DuckDB SQL for window functions (PERCENT_RANK for wage percentiles and openings_score) and CASE expressions (wage_tier, confidence_tier, data_completeness), but computes grw_score and market_score in Python. The lineage captures both execution contexts but attributes to the transformer module.

2. **Intermediate field (openings_score):** The DuckDB SQL computes openings_score as 1.0 + 9.0 * PERCENT_RANK(openings_annual_avg), but this field is popped from the row dict after market_score computation and does not appear in the Gold schema. The lineage traces openings_annual_avg -> openings_score (intermediate) -> market_score (output).

3. **Null-safe wage percentiles:** The DuckDB SQL uses a critical pattern where PERCENT_RANK is computed on a filtered CTE (WHERE median_annual_wage IS NOT NULL), then LEFT JOINed back. This was flagged in code comments as essential: if nulls participate in PERCENT_RANK, DuckDB places them at ~0.185, corrupting all positions.

4. **Rounding function:** The transformer uses a custom _round_half_up() function (floor(x + 0.5)) instead of Python's built-in round() to match DuckDB ROUND() behavior. Python uses banker's rounding (round half to even), which would produce different results at half-integer boundaries (e.g., round(2.5)=2 vs floor(2.5+0.5)=3).

## Completeness Check

- **Total output fields:** 31
- **Fields with lineage:** 31 (100%)
- **Dropped fields documented:** 7 (including Silver record_id replacement)
- **Every spec transformation (items 1-15 in spec) has a corresponding lineage record:** Yes
- **Agent attribution:** @primary-agent
- **Spec reference:** docs/specs/gold-occupation-profiles-bls-ooh.md
