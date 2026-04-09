# CDE/PII Tagging Audit: silver-base-bls-ooh

**Date:** 2026-04-07
**Agent:** @cde-tagger
**Spec:** silver-base-bls-ooh
**Table:** base.bls_ooh
**Zone:** Silver (Base)
**Domain Context Referenced:** governance/domain-context.md (BLS OOH section, PII Expectations section)
**Physical Model Referenced:** governance/models/silver-base-bls-ooh-physical.md

---

## CDE Tagging Decisions

### Columns Flagged as CDE (5)

| Column | Business Term | Rationale |
|--------|---------------|-----------|
| soc_code | BT-027 | Natural key and primary crosswalk anchor for CIP-to-SOC bridge linking College Scorecard programs to career outcomes. Join key for all downstream Gold zone stats (ERN, GRW, Market boss fight) and O*NET integration. |
| employment_current | BT-031 | Current employment count backing Gold zone employment statistics and Market boss fight (labor market size by occupation). |
| employment_projected | BT-032 | Projected employment at end of 10-year BLS horizon. Combined with employment_current, enables forward-looking employment change metrics for GRW stat and Market boss fight. |
| employment_change_pct | BT-034 | Directly backs the GRW (growth) stat in Gold zone. Primary metric for occupation growth/decline classification. Drives growth_category derivation. |
| median_annual_wage | BT-036 | Directly backs the ERN (earnings) stat in Gold zone. Headline compensation metric for career guidance. Feeds debt-to-earnings comparisons via CIP-SOC crosswalk. |

### Columns Evaluated -- Not Flagged as CDE (20)

| Column | Reason Not Critical |
|--------|---------------------|
| record_id | Technical surrogate key; pipeline infrastructure, not consumed by business processes. |
| occupation_title | Display label; soc_code is the authoritative identifier. Not used in joins or calculations. |
| soc_major_group | Derived from soc_code (first 2 chars); can be recomputed. Used for grouping, not as primary join key. |
| soc_major_group_name | Display label for soc_major_group; derived via lookup. |
| broad_occupation_flag | Classification flag for 7 broad codes; informational for crosswalk confidence, not a primary metric. |
| catchall_flag | Classification flag for residual categories; informational, not a primary metric. |
| employment_change | Absolute change derived from employment_current and employment_projected; can be recomputed. |
| openings_annual_avg | Useful for Market boss fight context but not a primary Gold stat on its own. |
| growth_category | Derived from employment_change_pct via bucketing; can be recomputed. |
| median_wage_capped | Defensive flag; 0 True values in current data. Informational only. |
| wage_available | Derived convenience flag (median_annual_wage IS NOT NULL); can be recomputed. |
| education_typical | Original BLS text label; normalized version exists in education_level_name. |
| education_code | Categorical code for entry-level education; useful context but not a primary output metric. |
| education_level_name | Derived lookup label for education_code; can be recomputed. |
| work_experience | Original BLS text label for experience requirement. |
| work_experience_code | Categorical code for experience requirement; useful context, not primary metric. |
| training_typical | Original BLS text label for training requirement. |
| training_code | Categorical code for training requirement; useful context, not primary metric. |
| source_load_date | Pipeline metadata. |
| ingested_at | Pipeline metadata. |

---

## PII Tagging Decisions

### Columns Flagged as PII: 0

No columns contain personally identifiable information. This table contains aggregated occupation-level statistics from the Bureau of Labor Statistics. All data is publicly available and describes occupations, not individuals.

**Justification:** governance/domain-context.md PII Expectations section confirms no personal data expected across the FutureProof dataset. BLS Employment Projections data is published aggregate statistics with no individual-level records.

---

## Summary

| Metric | Count |
|--------|-------|
| Total columns evaluated | 25 |
| Columns flagged CDE | 5 |
| Columns flagged PII | 0 |
| Columns not flagged | 20 |

**Contract written to:** governance/data-contracts/base-bls-ooh.yaml
