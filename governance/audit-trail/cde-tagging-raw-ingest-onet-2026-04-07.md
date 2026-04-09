# CDE/PII Tagging Audit: raw-ingest-onet
**Date:** 2026-04-07
**Agent:** @cde-tagger
**Spec:** raw-ingest-onet
**Contracts:**
- governance/data-contracts/raw-onet-occupations.yaml
- governance/data-contracts/raw-onet-task-statements.yaml
- governance/data-contracts/raw-onet-work-activities.yaml
- governance/data-contracts/raw-onet-work-context.yaml
- governance/data-contracts/raw-onet-related-occupations.yaml

## Scope Note

The spec targets 7 tables but EDA confirmed that Career Changers Matrix and Career Starters Matrix files do not exist in the O*NET 30.2 ZIP archive (HTTP 404, files missing). Contracts are written for the 5 tables that have actual data. No contracts created for raw.onet_career_changers or raw.onet_career_starters.

## Domain Context Referenced
- governance/domain-context.md -- O*NET section (added 2026-04-07)
- O*NET 30.2 Database: 1,016 occupations coded with O*NET-SOC (XX-XXXX.XX), published under CC BY 4.0 by DOL/ETA
- Cross-source integration: O*NET-SOC truncates to 6-digit BLS SOC for joining to BLS OOH; bridges to College Scorecard via CIP-to-SOC crosswalk
- FutureProof downstream use: RES stat (AI Resilience) from tasks + activities, HMN stat (Human Edge) from activities, Burnout boss fight from work context, Stage 3 career branching from related occupations, Gemma career descriptions from occupations + tasks
- PII expectations: NO PII -- all fields are occupation-level aggregates from anonymized DOL surveys. Survey respondent identities are never published.
- Applicable regulations: DOL/ETA Data Publication Terms (CC BY 4.0, public domain); OMB SOC taxonomy governance. No FERPA/HIPAA/GLBA concerns.

## Columns Flagged as CDE

| Column | Table | Rationale |
|--------|-------|-----------|
| onet_soc_code | raw.onet_occupations | Primary identifier, grain field, JOIN KEY for all O*NET tables and cross-source bridge to BLS OOH via 6-digit truncation. |
| title | raw.onet_occupations | Human-readable occupation name required for all consumer-facing outputs and Gemma career descriptions. |
| onet_soc_code | raw.onet_task_statements | Grain field and FK to occupations. Required to associate tasks with occupations for AI exposure scoring. |
| task_id | raw.onet_task_statements | Globally unique task identifier. Atomic unit for AI automation exposure scoring (RES stat, AI boss fight). |
| task | raw.onet_task_statements | Task description text. Input to AI automation susceptibility scoring via semantic matching. |
| onet_soc_code | raw.onet_work_activities | Grain field and FK to occupations. Required to associate activity ratings with occupations for HMN stat. |
| element_id | raw.onet_work_activities | Content Model element ID identifying which of 41 work activities is rated. Structural key for HMN stat dimensions. |
| data_value | raw.onet_work_activities | The actual activity rating (IM 1-5, LV 0-7). Core quantitative input to HMN stat and AI boss fight. |
| onet_soc_code | raw.onet_work_context | Grain field and FK to occupations. Required to associate context ratings with occupations for Burnout boss fight. |
| element_id | raw.onet_work_context | Content Model element ID identifying which of 57 context dimensions is rated. Key burnout elements: Time Pressure, Work Schedules, etc. |
| data_value | raw.onet_work_context | The actual context rating. Primary input to Burnout boss fight scoring. |
| onet_soc_code | raw.onet_related_occupations | Source occupation in career relationship. Required for Stage 3 career branching. |
| related_onet_soc_code | raw.onet_related_occupations | Target occupation in career relationship. Powers career pathway recommendations. |
| is_primary | raw.onet_related_occupations | Primary vs supplemental relationship flag. Determines which career suggestions are highlighted vs deprioritized. |

## Columns Flagged as PII

None. Per governance/domain-context.md O*NET PII section: all fields are occupation-level aggregates derived from anonymized surveys conducted by the U.S. Department of Labor. Survey respondent identities are never included in the published database. No personal names, worker identifiers, individual compensation, health records, or other personal data.

## Columns Evaluated -- Not Flagged

| Column | Table | Reason Not Critical |
|--------|-------|---------------------|
| description | raw.onet_occupations | Supplementary occupation text for Gemma descriptions. Not a join key or computational input; title + task data suffice for core FutureProof functionality. |
| task_type | raw.onet_task_statements | Task classification (Core/Supplemental/n/a). Useful for filtering but both Core and Supplemental tasks feed AI exposure scoring. |
| incumbents_responding | raw.onet_task_statements | Survey sample size. Data quality indicator, not analytical input. |
| date | raw.onet_task_statements | Data collection date. Temporal metadata, not analytical input. |
| domain_source | raw.onet_task_statements | Source of task data (Incumbent/Expert/Analyst). Data quality context, not analytical input. |
| element_name | raw.onet_work_activities | Display label for element_id. 1:1 mapping; element_id is the computational key. |
| scale_id | raw.onet_work_activities | Structural classifier (IM/LV). Contextualizes data_value but not independently critical. |
| n | raw.onet_work_activities | Survey sample size. Data quality indicator. |
| standard_error | raw.onet_work_activities | Statistical metadata. Not analytical input. |
| lower_ci_bound | raw.onet_work_activities | Statistical metadata. Not analytical input. |
| upper_ci_bound | raw.onet_work_activities | Statistical metadata. Not analytical input. |
| recommend_suppress | raw.onet_work_activities | Data quality flag (1.5% "Y"). Modifies data_value interpretation. Silver zone filter, not standalone CDE. |
| not_relevant | raw.onet_work_activities | Relevance flag (1.5% "Y" on LV scale only). Modifies data_value interpretation. |
| date | raw.onet_work_activities | Data collection date. Temporal metadata. |
| domain_source | raw.onet_work_activities | Source of rating. Data quality context. |
| element_name | raw.onet_work_context | Display label for element_id. 1:1 mapping; element_id is the computational key. |
| scale_id | raw.onet_work_context | Structural classifier (CX/CXP/CT/CTP). Contextualizes data_value but not independently critical. |
| category | raw.onet_work_context | Response category for CXP/CTP rows. Part of grain but is a structural classifier, not independently critical. |
| n | raw.onet_work_context | Survey sample size. Data quality indicator. |
| standard_error | raw.onet_work_context | Statistical metadata. Not analytical input. |
| lower_ci_bound | raw.onet_work_context | Statistical metadata. Not analytical input. |
| upper_ci_bound | raw.onet_work_context | Statistical metadata. Not analytical input. |
| recommend_suppress | raw.onet_work_context | Data quality flag (2.5% "Y"). Higher rate on CXP/CTP scales. Silver zone filter. |
| not_relevant | raw.onet_work_context | Always "n/a" (100% of rows). Constant value, no analytical use. |
| date | raw.onet_work_context | Data collection date. Temporal metadata. |
| domain_source | raw.onet_work_context | Source of rating. Data quality context. |
| related_index | raw.onet_related_occupations | Rank ordinal (1-20). is_primary and relatedness_tier provide the actionable classification. |
| relatedness_tier | raw.onet_related_occupations | Finer-grained tier (Primary-Short/Primary-Long/Supplemental). Adds nuance beyond is_primary but not required for core branching logic. |
| ingested_at | all 5 tables | Pipeline metadata -- no business criticality. |
| source_url | all 5 tables | Pipeline metadata -- provenance tracking only. |
| source_method | all 5 tables | Pipeline metadata -- provenance tracking only. |
| load_date | all 5 tables | Pipeline metadata -- freshness tracking only. |
