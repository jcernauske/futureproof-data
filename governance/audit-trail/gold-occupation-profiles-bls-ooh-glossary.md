# Audit Trail: Business Glossary Update
**Spec:** gold-occupation-profiles-bls-ooh
**Date:** 2026-04-07
**Agent:** @data-steward
**Mode:** Greenfield
**Domain:** Higher Education Outcomes / Occupational Profiles

---

## Action Summary

Updated `governance/business-glossary.json` with 8 new business terms (BT-047 through BT-054) and updated `used_in_models` for 20 existing terms to include `gold-occupation-profiles-bls-ooh`.

## New Terms Added

| Term ID | Name | Source | Category | Status | Rationale |
|---------|------|--------|----------|--------|-----------|
| BT-047 | GRW Score | project-specific | derived | approved | Piecewise linear growth stat (1-10 scale) derived from employment_change_pct. Backs the GRW pentagon stat. |
| BT-048 | Wage Percentile Overall | project-specific | derived | approved | PERCENT_RANK of median_annual_wage across all occupations. Input for wage tier and ERN stat. |
| BT-049 | Wage Percentile Education Tier | project-specific | derived | approved | PERCENT_RANK of median_annual_wage within education requirement tier. Backs Ceiling boss fight. |
| BT-050 | Wage Tier | project-specific | classification | approved | Five-bucket classification of wage_percentile_overall (low through very_high). |
| BT-051 | Market Score | project-specific | derived | approved | Composite score (60% growth + 40% openings) on 1-10 scale. Backs Market boss fight. |
| BT-052 | Occupation Confidence Tier | project-specific | classification | approved | Three-level data quality classification (high/medium/low) based on occupation specificity and wage availability. Distinct from BT-024 (career outcomes confidence tier). |
| BT-053 | Data Completeness (Occupation) | project-specific | derived | approved | Proportion of 4 core fields that are non-null (0.0 to 1.0 in 0.25 increments). |
| BT-054 | FutureProof Stat Mapping | project-specific | entity | approved | Static metadata fields (backs_stats, backs_bosses) documenting which game-system elements this data product feeds. |

## Approval Details

All 8 terms are `project-specific` source and would normally require `REQUIRE_HUMAN_APPROVAL` gate. Human approval was granted for all 8 terms in the same session. Terms were set to `approved` status (not `proposed`).

## Existing Terms Updated (used_in_models)

The following 20 existing terms had `gold-occupation-profiles-bls-ooh` added to their `used_in_models` array:

| Term ID | Name | Previous Models |
|---------|------|-----------------|
| BT-015 | Record ID | silver-base-college-scorecard, silver-base-bls-ooh |
| BT-016 | Source Load Date | silver-base-college-scorecard, silver-base-bls-ooh, gold-career-outcomes-college-scorecard |
| BT-026 | Promotion Timestamp | gold-career-outcomes-college-scorecard |
| BT-027 | SOC Code | silver-base-bls-ooh |
| BT-028 | Occupation Title | silver-base-bls-ooh |
| BT-029 | SOC Major Group | silver-base-bls-ooh |
| BT-030 | SOC Major Group Name | silver-base-bls-ooh |
| BT-031 | Employment Current | silver-base-bls-ooh |
| BT-032 | Employment Projected | silver-base-bls-ooh |
| BT-034 | Employment Change Percent | silver-base-bls-ooh |
| BT-035 | Annual Average Openings | silver-base-bls-ooh |
| BT-036 | Median Annual Wage (Occupation) | silver-base-bls-ooh |
| BT-038 | Education Code (BLS) | silver-base-bls-ooh |
| BT-039 | Education Level Name | silver-base-bls-ooh |
| BT-040 | Broad Occupation Flag | silver-base-bls-ooh |
| BT-041 | Growth Category | silver-base-bls-ooh |
| BT-042 | Wage Available | silver-base-bls-ooh |
| BT-043 | Catchall Flag | silver-base-bls-ooh |
| BT-044 | Work Experience Code (BLS) | silver-base-bls-ooh |
| BT-045 | Training Code (BLS) | silver-base-bls-ooh |

## Terms NOT Updated (Dropped from Gold)

The following Silver terms are explicitly dropped in the Gold spec and were not added to `used_in_models`:

| Term ID | Name | Reason Dropped |
|---------|------|----------------|
| BT-033 | Employment Change | Redundant with employment_change_pct for Gold consumers |
| BT-037 | Median Wage Capped | All False in current data; wage_available flag is more useful |
| BT-046 | Projection Cycle | Not a field in the Gold schema |

## Ambiguities

**Confidence Tier disambiguation:** BT-024 (Confidence Tier, from gold-career-outcomes-college-scorecard) and BT-052 (Occupation Confidence Tier, from this spec) are related but distinct concepts. BT-024 uses four levels (high/medium/low/insufficient) based on cohort size and earnings/debt data availability. BT-052 uses three levels (high/medium/low) based on occupation specificity (broad/catchall flags) and wage availability. Named differently to avoid confusion.

## Post-Update State

- Total terms in glossary: 54 (was 46)
- Terms referencing gold-occupation-profiles-bls-ooh: 28 (20 existing + 8 new)
