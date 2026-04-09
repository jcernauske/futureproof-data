# CDE/PII Tagging Audit: raw-ingest-bls-ooh
**Date:** 2026-04-07
**Agent:** @cde-tagger
**Spec:** raw-ingest-bls-ooh
**Contract:** governance/data-contracts/raw-bls-ooh.yaml

## Domain Context Referenced
- governance/domain-context.md — BLS OOH section (added 2026-04-07)
- BLS Employment Projections methodology: SOC 2018 taxonomy, biennial projection cycle (2023-2033)
- Cross-source integration: SOC code is the bridge key for CIP-to-SOC crosswalk (College Scorecard) and direct O*NET join
- PII expectations: NO PII — all fields are occupation-level aggregates from a federal statistical agency
- Applicable regulations: BLS Data Use Terms (public domain data); no FERPA/HIPAA/GLBA concerns

## Columns Flagged as CDE

| Column | Rationale |
|--------|-----------|
| soc_code | Grain field and PRIMARY JOIN KEY for all Silver zone cross-source integration (CIP-to-SOC crosswalk, O*NET direct join). Without correct SOC codes the core FutureProof pipeline breaks. |
| occupation_title | Human-readable occupation identifier required for all consumer-facing outputs. Without it, career guidance data is uninterpretable to end users. |
| employment_change_pct | Primary demand trajectory indicator — directly answers "is this career growing or shrinking?" Feeds Gold zone career outlook scoring. |
| median_annual_wage | Core compensation metric — answers "how much does this career pay?" Feeds Gold zone debt-to-salary ratio, the most actionable metric for education ROI assessment. |
| education_code | Enables education requirements alignment analysis — matching occupation entry requirements against program credential levels (College Scorecard credlev). Core FutureProof integration point. |

## Columns Flagged as PII

None. Per governance/domain-context.md BLS OOH PII section: all fields are occupation-level aggregates published by a federal statistical agency. No personal names, worker identifiers, individual compensation, or other personal data.

## Columns Evaluated -- Not Flagged

| Column | Reason Not Critical |
|--------|---------------------|
| employment_current | Context metric for occupation size; not a primary decision driver. Downstream products use employment_change_pct as the actionable indicator. |
| employment_projected | Supporting metric; employment_change_pct is the derived actionable indicator that normalizes across occupation sizes. |
| employment_change | Absolute change figure; employment_change_pct is preferred because it normalizes for occupation size. |
| openings_annual_avg | Useful context but secondary to employment_change_pct and median_annual_wage as decision metrics. Could be reconsidered for Gold zone contracts. |
| median_wage_capped | Companion flag for median_annual_wage interpretation. Important for data quality but not independently critical — it modifies the CDE (median_annual_wage) rather than standing alone. |
| education_typical | Display label; education_code carries the same information in computational form (which is the CDE). |
| work_experience | Display label for work experience requirement. Extended concept, not core to FutureProof MVP. |
| work_experience_code | Extended concept (BLS code 1-3). Not part of the core CIP-to-SOC-to-outcomes integration. Could be reconsidered for Gold zone career accessibility scoring. |
| training_typical | Display label for training requirement. Extended concept. |
| training_code | Extended concept (BLS code 1-6). Not part of core integration. Could be reconsidered for Gold zone. |
| ingested_at | Pipeline metadata — no business criticality. |
| source_url | Pipeline metadata — provenance tracking only. |
| source_method | Pipeline metadata — provenance tracking only. |
| load_date | Pipeline metadata — freshness tracking only. |
