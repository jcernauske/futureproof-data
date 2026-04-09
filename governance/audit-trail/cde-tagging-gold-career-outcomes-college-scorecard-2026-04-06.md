# Audit Trail: CDE/PII Tagging
**Spec:** gold-career-outcomes-college-scorecard
**Agent:** @cde-tagger
**Date:** 2026-04-06
**Table:** consumable.career_outcomes
**Zone:** Gold (Consumable)

## Summary

Evaluated all 30 columns in consumable.career_outcomes for CDE and PII classification.

- **11 columns flagged as CDE** (4 carried from Silver, 6 percentile bands new in Gold, 1 financial ratio new in Gold)
- **0 columns flagged as PII** (all data is aggregated program-level statistics per governance/domain-context.md)
- **19 columns evaluated and not flagged** (with documented rationale for each)

## Domain Context

Read governance/domain-context.md before flagging. Key inputs:
- Domain: Higher Education Outcomes (program-level career outcomes)
- PII Expectations section: "This dataset contains NO PII"
- All earnings/debt values are cohort-level medians, not individual records
- Gainful Employment rule methodology informs debt-to-earnings as key metric

## CDE Decisions

### Flagged as CDE (11 columns)

| Column | Why CDE |
|--------|---------|
| unitid | Natural key; all downstream joins depend on it |
| earnings_1yr_median | Primary outcome metric; feeds 5 derived columns |
| earnings_2yr_median | Multi-horizon outcome metric; feeds growth rate and 2yr bands |
| debt_median | Primary affordability metric; feeds 4 derived columns |
| earnings_1yr_p25 | Effort slider lower bound (1yr) |
| earnings_1yr_p75 | Effort slider upper bound (1yr) |
| earnings_2yr_p25 | 2yr earnings range lower bound |
| earnings_2yr_p75 | 2yr earnings range upper bound |
| debt_p25 | Debt range lower bound |
| debt_p75 | Debt range upper bound |
| debt_to_earnings_annual | Key affordability ratio (Gainful Employment alignment) |

### Not Flagged as CDE (19 columns)

| Column | Why Not CDE |
|--------|-------------|
| record_id | Technical surrogate key |
| institution_name | Display label only |
| institution_control | Segmentation dimension, not outcome metric |
| cipcode | Join key, not outcome metric |
| program_name | Display label only |
| cip_family | Partition key, integrity enforced by DQ |
| cip_family_name | Display label |
| credential_level | Key component, single value in MVP |
| completions_count | Size indicator, not outcome metric |
| small_cohort_flag | Intermediate quality flag |
| debt_to_earnings_tier | Convenience bucketing of CDE ratio |
| earnings_growth_rate | Supplementary, not primary decision metric |
| cip_family_earnings_rank | Relative positioning, supplementary |
| program_value_index | Inverse of CDE ratio, redundant |
| confidence_tier | Quality classification, not outcome metric |
| has_earnings | Convenience flag |
| has_debt | Convenience flag |
| outcome_completeness | Quality proportion |
| source_load_date | Pipeline metadata |
| promoted_at | Pipeline metadata |

## PII Decisions

All 30 columns evaluated. Zero PII found. Justification: governance/domain-context.md PII section confirms "No personal data expected -- all fields are institutional/aggregate." FERPA suppression applied at source by Department of Education.

## Artifacts Produced

- Data contract: governance/data-contracts/consumable-career-outcomes.yaml
- CDE tagging report: governance/reviews/gold-career-outcomes-college-scorecard-cde-tags.md
- Audit trail: governance/audit-trail/cde-tagging-gold-career-outcomes-college-scorecard-2026-04-06.md (this file)
