## PII Scan Report: O*NET Raw Tables (5 Tables)
**Date:** 2026-04-07
**Agent:** @pii-scanner
**Domain:** Occupational Information / Labor Market Analytics (O*NET 30.2 Database)
**Spec:** docs/specs/raw-ingest-onet.md
**Records Scanned:** 409,256 total across 5 tables
**PII Instances Found:** 0

### Tables Scanned
| # | Table | Records | Columns | Status |
|---|-------|---------|---------|--------|
| 1 | raw.onet_occupations | 1,016 | 7 | Scanned -- 0 PII |
| 2 | raw.onet_task_statements | 18,796 | 11 | Scanned -- 0 PII |
| 3 | raw.onet_work_activities | 73,308 | 17 | Scanned -- 0 PII |
| 4 | raw.onet_work_context | 297,676 | 18 | Scanned -- 0 PII |
| 5 | raw.onet_related_occupations | 18,460 | 9 | Scanned -- 0 PII |

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | No PII detected in any field across all 5 tables |

### Field-by-Field Analysis

#### raw.onet_occupations (7 fields)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| onet_soc_code | string (XX-XXXX.XX) | None | Federal occupational classification code from SOC taxonomy. Not a personal identifier. |
| title | string | None | Standardized occupation titles (e.g., "Chief Executives", "General and Operations Managers"). These are job category labels from the SOC taxonomy, not personal names. |
| description | string | None | Occupation definition text describing job duties in generic terms. No individual-identifying information. |
| ingested_at | timestamp | None | Pipeline metadata. |
| source_url | string | None | Static download URL for O*NET ZIP archive. |
| source_method | string | None | Constant value "bulk_zip_download". Pipeline metadata. |
| load_date | date | None | Pipeline metadata. |

#### raw.onet_task_statements (11 fields)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| onet_soc_code | string | None | SOC taxonomy code. Not a personal identifier. |
| task_id | long | None | Sequential task identifier internal to O*NET. Not a personal identifier. |
| task | string | None | Generic task descriptions (e.g., "Direct or coordinate an organization's financial or budget activities"). Describes occupation duties, not individual worker actions. |
| task_type | string | None | Categorical: "Core", "Supplemental", "n/a". Metadata. |
| incumbents_responding | int | None | Aggregate count of anonymous survey respondents (range 18-238). This is a sample size, not an individual identifier. Respondent identities are never published by O*NET. |
| date | string (MM/YYYY) | None | Data collection date at month/year granularity. Not a personal date. |
| domain_source | string | None | Categorical: "Incumbent", "Occupational Expert", "Analyst", "Analyst - Transition". Refers to survey methodology, not named individuals. |
| ingested_at | timestamp | None | Pipeline metadata. |
| source_url | string | None | Pipeline metadata. |
| source_method | string | None | Pipeline metadata. |
| load_date | date | None | Pipeline metadata. |

#### raw.onet_work_activities (17 fields)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| onet_soc_code | string | None | SOC taxonomy code. |
| element_id | string | None | O*NET Content Model element ID (e.g., "4.A.1.a.1"). Internal taxonomy code. |
| element_name | string | None | Activity name (e.g., "Getting Information", "Monitoring Processes"). Standardized labels, not personal data. |
| scale_id | string | None | Scale type: "IM" (importance) or "LV" (level). Metadata. |
| data_value | double | None | Numeric rating (IM: 1-5, LV: 0-7). Aggregate occupation-level scores from anonymized surveys. |
| n | int | None | Anonymous survey sample size. |
| standard_error | double | None | Statistical measure. |
| lower_ci_bound | double | None | Statistical measure. |
| upper_ci_bound | double | None | Statistical measure. |
| recommend_suppress | string | None | O*NET data quality flag: "Y", "N", or "n/a". |
| not_relevant | string | None | O*NET relevance flag: "Y", "N", or "n/a". |
| date | string (MM/YYYY) | None | Data collection date. Not a personal date. |
| domain_source | string | None | Survey methodology category. Not named individuals. |
| ingested_at | timestamp | None | Pipeline metadata. |
| source_url | string | None | Pipeline metadata. |
| source_method | string | None | Pipeline metadata. |
| load_date | date | None | Pipeline metadata. |

#### raw.onet_work_context (18 fields)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| onet_soc_code | string | None | SOC taxonomy code. |
| element_id | string | None | O*NET Content Model element ID. |
| element_name | string | None | Context dimension name (e.g., "Public Speaking", "Time Pressure"). Standardized labels. |
| scale_id | string | None | Scale type: "CX", "CXP", "CT", or "CTP". Metadata. |
| data_value | double | None | Numeric rating or percentage. Aggregate occupation-level scores. |
| n | int | None | Anonymous survey sample size. |
| standard_error | double | None | Statistical measure. |
| lower_ci_bound | double | None | Statistical measure. |
| upper_ci_bound | double | None | Statistical measure. |
| recommend_suppress | string | None | O*NET data quality flag. |
| not_relevant | string | None | Always "n/a" in Work Context. |
| date | string (MM/YYYY) | None | Data collection date. Not a personal date. |
| domain_source | string | None | Survey methodology category. |
| category | int | None | Response category index (1-5 for CXP, 1-3 for CTP, null for point-estimate scales). Metadata. |
| ingested_at | timestamp | None | Pipeline metadata. |
| source_url | string | None | Pipeline metadata. |
| source_method | string | None | Pipeline metadata. |
| load_date | date | None | Pipeline metadata. |

#### raw.onet_related_occupations (9 fields)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| onet_soc_code | string | None | Source occupation SOC code. |
| related_onet_soc_code | string | None | Related occupation SOC code. |
| related_index | int | None | Rank position (1-20). |
| is_primary | boolean | None | Derived flag (true for index 1-10). |
| relatedness_tier | string | None | Categorical: "Primary-Short", "Primary-Long", "Supplemental". |
| ingested_at | timestamp | None | Pipeline metadata. |
| source_url | string | None | Pipeline metadata. |
| source_method | string | None | Pipeline metadata. |
| load_date | date | None | Pipeline metadata. |

### Summary by Sensitivity
| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 (Public) | 0 | -- |
| 2 (Internal) | 0 | -- |
| 3 (Confidential) | 0 | -- |
| 4 (Restricted) | 0 | -- |

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| title (onet_occupations) | Could trigger personal name detection | These are standardized SOC occupation titles from the U.S. Department of Labor taxonomy (e.g., "Chief Executives", "Chief Sustainability Officers"). They describe job categories, not named individuals. | No action needed -- confirmed non-PII. |
| task (onet_task_statements) | Could trigger free-text PII scan | Task descriptions use generic occupation-level language (e.g., "Direct or coordinate an organization's financial or budget activities"). No personal names, identifiers, or individual-specific details appear in any of the 18,796 task statements. | No action needed -- confirmed non-PII. |
| description (onet_occupations) | Could trigger free-text PII scan | Occupation definitions are generic role descriptions. No individual-identifying language. | No action needed -- confirmed non-PII. |
| incumbents_responding (onet_task_statements) | Could trigger "respondent count" concern | This is an aggregate sample size (range 18-238), not an individual identifier. O*NET never publishes respondent identities. The DOL anonymizes all survey responses before aggregation. | No action needed -- confirmed non-PII. |
| element_name (work_activities, work_context) | Could trigger health-data detection for elements like "Exposed to Hazardous Conditions" or "Exposed to Disease or Infections" | These are occupation-level environmental descriptors rated on a scale, not individual health records. They describe typical working conditions for an occupation, not any person's medical status. | No action needed -- confirmed non-PII. |
| domain_source (multiple tables) | Could trigger "person role" detection for values like "Incumbent" or "Occupational Expert" | These are categorical survey methodology labels indicating the type of respondent pool, not named individuals. "Incumbent" means "workers currently in this occupation" as a group. | No action needed -- confirmed non-PII. |

### Regulatory Implications
No PII was detected. No privacy regulations apply to this dataset:

- **GDPR:** Not applicable. No personal data of EU or any individuals. All data is occupation-level aggregate.
- **HIPAA:** Not applicable. Work Context includes health-adjacent occupational descriptors (e.g., "Exposed to Disease or Infections") but these describe occupation environments, not individual patient records.
- **CCPA:** Not applicable. No consumer personal information.
- **FERPA:** Not applicable. No student education records.
- **SOX/GLBA:** Not applicable. No individual financial records.

All data is published by the U.S. Department of Labor under Creative Commons Attribution 4.0 International (CC BY 4.0) license. Survey respondent identities are anonymized and aggregated at the occupation level before publication. The DOL explicitly designs O*NET to contain zero individually-identifiable data.

### Recommendations
1. **No PII remediation required.** All 62 fields across 5 tables contain occupation-level aggregate statistics, taxonomy codes, survey methodology metadata, or pipeline metadata. Zero individual-level data.
2. **No column masking or RLS policies needed** for PII reasons. Access controls, if any, should be based on business requirements rather than privacy requirements.
3. **@policy-engineer:** Skip PII-based policy generation for all 5 O*NET tables. Standard access controls sufficient.
4. **CDE tagger confirmation:** The @cde-tagger previously confirmed 0 PII columns across all O*NET tables (see `governance/audit-trail/cde-tagging-raw-ingest-onet-2026-04-07.md`). This formal PII scan corroborates that finding.
5. **Justification reference:** governance/domain-context.md O*NET PII Expectations section confirms no personal data -- all fields are occupation-level aggregates from anonymized federal surveys.

### Detection Methods Used
| Method | Applied To | Result |
|--------|-----------|--------|
| Field name heuristic analysis | All 62 fields across 5 tables | No field names suggest PII (no "name", "ssn", "email", "phone", "address", "dob" patterns) |
| Format-specific regex (SSN, EIN, phone, email, credit card) | All string fields | No matches |
| NER pattern matching (personal names) | title, description, task, element_name fields | No personal names detected; all values are standardized occupational vocabulary |
| Address pattern matching | All string fields | No address patterns detected |
| Date-of-birth context analysis | date fields | All dates are survey collection dates (MM/YYYY format), not personal dates of birth |
| Financial data detection | data_value, n fields | All numeric values are survey ratings (1-7 scale) or sample sizes, not financial amounts |
| Domain context calibration | All tables | governance/domain-context.md confirms O*NET contains zero PII -- all occupation-level aggregates from anonymized DOL surveys |
