## PII Scan Report: consumable.career_outcomes
**Date:** 2026-04-06
**Agent:** @pii-scanner
**Domain:** Higher Education Outcomes (College Scorecard)
**Spec:** gold-career-outcomes-college-scorecard
**Zone:** Gold
**Records Scanned:** 69,947
**PII Instances Found:** 0

### Pre-Scan Calibration

Domain context (`governance/domain-context.md`) explicitly states under "PII Expectations":

> This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures. Privacy is protected at the source by the Department of Education's suppression rules (FERPA).

The spec itself lists @pii-scanner as conditionally skippable for this reason. This scan is executed to satisfy the pipeline gate requirement and provide formal confirmation.

### Schema Analysis

31 fields were analyzed for PII potential:

| # | Field | Type | PII Risk | Assessment |
|---|-------|------|----------|------------|
| 1 | record_id | string | None | Deterministic hash (prefix `co-`), not traceable to individuals |
| 2 | unitid | long | None | IPEDS institution identifier, not a personal identifier |
| 3 | institution_name | string | None | Organization names (universities), not personal names |
| 4 | institution_control | string | None | Categorical (Public/Private), no PII content |
| 5 | cipcode | string | None | Classification of Instructional Programs code (XX.XX format) |
| 6 | program_name | string | None | Academic program descriptions, not personal data |
| 7 | cip_family | string | None | 2-digit CIP family code |
| 8 | cip_family_name | string | None | CIP family description |
| 9 | credential_level | int | None | Categorical credential level code |
| 10 | earnings_1yr_median | double | None | Aggregate median statistic across cohort, not individual earnings |
| 11 | earnings_2yr_median | double | None | Aggregate median statistic across cohort |
| 12 | debt_median | double | None | Aggregate median statistic across cohort, not individual debt |
| 13 | completions_count | long | None | Count of completers, not individual identifiers |
| 14 | small_cohort_flag | boolean | None | Derived flag |
| 15 | earnings_1yr_p25 | double | None | Derived aggregate percentile |
| 16 | earnings_1yr_p75 | double | None | Derived aggregate percentile |
| 17 | earnings_2yr_p25 | double | None | Derived aggregate percentile |
| 18 | earnings_2yr_p75 | double | None | Derived aggregate percentile |
| 19 | debt_p25 | double | None | Derived aggregate percentile |
| 20 | debt_p75 | double | None | Derived aggregate percentile |
| 21 | debt_to_earnings_annual | double | None | Derived ratio |
| 22 | debt_to_earnings_tier | string | None | Categorical bucketed tier |
| 23 | earnings_growth_rate | double | None | Derived ratio |
| 24 | cip_family_earnings_rank | double | None | Derived rank |
| 25 | program_value_index | double | None | Derived ratio |
| 26 | confidence_tier | string | None | Categorical tier (high/medium/low/insufficient) |
| 27 | has_earnings | boolean | None | Derived flag |
| 28 | has_debt | boolean | None | Derived flag |
| 29 | outcome_completeness | double | None | Derived completeness score |
| 30 | source_load_date | date | None | Pipeline metadata |
| 31 | promoted_at | timestamp | None | Pipeline metadata |

### Data Content Scanning

The following detection methods were applied to all string fields across 69,947 rows:

| Detection Method | Fields Scanned | Matches Found |
|-----------------|---------------|--------------|
| Email pattern (`@` in string fields) | institution_name, program_name | 0 |
| SSN format (NNN-NN-NNNN) | record_id, all string fields | 0 |
| Phone number patterns | all string fields | 0 |
| Personal name heuristics | institution_name, program_name | 0 (all values are organization/program names) |
| Address patterns | all string fields | 0 |
| Financial account numbers | all numeric fields | 0 (all values are aggregate statistics in expected ranges) |

Sample values confirmed as non-PII:
- `institution_name`: "Alabama A & M University", "Auburn University", "Northeastern University" -- all institutional entities
- `program_name`: "Agriculture, General.", "Chemistry.", "Economics." -- all academic program descriptions
- `record_id`: "co-09faf08c11b450b4" -- deterministic grain hash, not traceable to individuals
- `unitid` range: 100654 - 497268 -- IPEDS institutional IDs
- `earnings_1yr_median` range: $4,880 - $161,723 -- aggregate medians, not individual salaries
- `debt_median` range: $2,750 - $57,500 -- aggregate medians, not individual debt records

### Findings

| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | -- |
| *(No PII findings)* | | | | | | |

### Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| Public (1) | 0 | N/A |
| Internal (2) | 0 | N/A |
| Confidential (3) | 0 | N/A |
| Restricted (4) | 0 | N/A |

**Overall classification: No PII detected. All fields contain institutional identifiers, program codes, aggregate statistics, or derived metrics.**

### False Positive Candidates

| Field | Detected As | Why It Is Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| institution_name | Could be mistaken for personal names | Values are university/college names (e.g., "Auburn University"), not individual names. Confirmed by field context and domain knowledge. | No action needed |
| unitid | Could be mistaken for personal identifier | IPEDS institution identifier, a public registry code. Not linked to individuals. | No action needed |
| earnings/debt fields | Could be mistaken for personal financial data | All values are median aggregates across program cohorts, not individual financial records. Source data is pre-aggregated by the Department of Education. | No action needed |

### Regulatory Implications

- **FERPA:** Privacy protection is applied at the source by the Department of Education. Programs with fewer than approximately 30 completers have earnings and debt data suppressed before publication. This pipeline inherits that protection.
- **GDPR:** Not applicable. No EU personal data present. All data is US institutional/aggregate.
- **CCPA:** Not applicable. No California consumer personal information present.
- **HIPAA:** Not applicable. No health data present.
- **PCI DSS:** Not applicable. No payment card data present.

No regulatory remediation is required for this dataset.

### Recommendations

1. **No PII remediation needed.** Zero PII instances detected across all 31 fields and 69,947 rows.
2. **No column masking required.** @policy-engineer can skip masking policies for this table.
3. **No RLS policies needed for PII reasons.** Access controls may still apply for business reasons but are not driven by PII sensitivity.
4. **Maintain FERPA awareness.** While this dataset contains no PII, the source data's privacy suppression pattern (null earnings/debt for small cohorts) is a FERPA-driven design choice. Downstream consumers should understand that null values represent privacy protection, not missing data.
5. **Re-scan if source data changes.** If future data refreshes include additional fields (e.g., individual-level earnings from longitudinal tracking), a new PII scan will be required.
