## PII Scan Report: silver-base-bls-ooh
**Date:** 2026-04-07
**Agent:** @pii-scanner
**Domain:** BLS Employment Projections (Occupational Outlook Handbook)
**Zone:** Silver (Base)
**Spec:** docs/specs/silver-base-bls-ooh.md
**Records Scanned:** 832 (schema-level scan; one row per occupation)
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | No PII detected in any field |

### Summary by Sensitivity
| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 - Public | 0 | -- |
| 2 - Internal | 0 | -- |
| 3 - Confidential | 0 | -- |
| 4 - Restricted | 0 | -- |

### Field-by-Field Analysis

All 25 columns in `base.bls_ooh` were evaluated against PII detection categories.

| Field | Data Type | PII Risk | Rationale |
|-------|-----------|----------|-----------|
| record_id | VARCHAR | None | Deterministic hash (SHA-256 truncated). Not derived from personal data. Grain key is soc_code (a public taxonomy code). |
| soc_code | VARCHAR | None | Standard Occupational Classification code (XX-XXXX). Public federal taxonomy maintained by OMB/BLS. |
| occupation_title | VARCHAR | None | Official BLS occupation names (e.g., "Software Developers", "Registered Nurses"). Not personal names. |
| soc_major_group | VARCHAR | None | 2-digit SOC major group code. Public taxonomy. |
| soc_major_group_name | VARCHAR | None | Human-readable SOC group label (e.g., "Management"). Public taxonomy. |
| broad_occupation_flag | BOOLEAN | None | Derived classification flag. No personal data. |
| catchall_flag | BOOLEAN | None | Derived classification flag. No personal data. |
| employment_current | BIGINT | None | Aggregate employment count across all workers in an occupation nationally. Not individual-level. |
| employment_projected | BIGINT | None | Aggregate projected employment count. Not individual-level. |
| employment_change | BIGINT | None | Aggregate change in employment. Not individual-level. |
| employment_change_pct | DOUBLE | None | Percentage change in aggregate employment. Not individual-level. |
| openings_annual_avg | BIGINT | None | Aggregate annual job openings. Not individual-level. |
| growth_category | VARCHAR | None | Derived categorical tier from aggregate percentage. |
| median_annual_wage | DOUBLE | None | Occupation-level median wage. This is a statistical aggregate across all workers in the occupation, not any individual's compensation. |
| median_wage_capped | BOOLEAN | None | Boolean flag about wage reporting methodology. No personal data. |
| wage_available | BOOLEAN | None | Derived convenience flag. No personal data. |
| education_typical | VARCHAR | None | BLS occupation-level education requirement label. Not any individual's education history. |
| education_code | INTEGER | None | Categorical code for occupation education requirement. Not individual-level. |
| education_level_name | VARCHAR | None | Normalized label for education requirement. Not individual-level. |
| work_experience | VARCHAR | None | Occupation-level experience requirement. Not individual-level. |
| work_experience_code | INTEGER | None | Categorical code for experience requirement. Not individual-level. |
| training_typical | VARCHAR | None | Occupation-level training requirement. Not individual-level. |
| training_code | INTEGER | None | Categorical code for training requirement. Not individual-level. |
| source_load_date | DATE | None | Pipeline metadata date. Not a personal date of birth or other personal date. |
| ingested_at | TIMESTAMP | None | Pipeline metadata timestamp. Not personal data. |

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| occupation_title | Personal Names (NER) | Occupation titles may contain words that overlap with name patterns (e.g., "Baker" appears in "Bakers"), but these are standardized BLS occupation labels, not personal names. | No action required. Zero risk. |
| median_annual_wage | Financial PII | Wage values are occupation-level statistical medians published by a federal agency, not any individual's compensation. | No action required. Zero risk. |

### Regulatory Implications

**No PII-related regulations apply to this dataset.**

- **FERPA:** Not applicable. No student-level data.
- **HIPAA:** Not applicable. No health records or patient data. (Healthcare occupation titles like "Registered Nurses" describe the occupation category, not patients or providers.)
- **CCPA/CPRA:** Not applicable. No California consumer personal information.
- **GDPR:** Not applicable. No EU personal data. All data is U.S. aggregate occupation statistics.
- **PCI DSS:** Not applicable. No payment card data.

The BLS Employment Projections data is produced by a federal statistical agency and published as public domain data. No privacy protections are required beyond standard data governance practices.

### Recommendations

1. **No PII remediation needed.** All 25 fields contain either public taxonomy codes, aggregate statistical measures, derived classification flags, or pipeline metadata.
2. **No column masking required.** @policy-engineer can skip PII-based column masking policies for this table.
3. **No RLS policies needed for PII reasons.** Access controls should be based on business need, not PII sensitivity.
4. **Standard access controls sufficient.** This table can be classified as Sensitivity Level 1 (Public) for all fields — the source data is publicly available from BLS.
5. **Domain context confirms finding.** The `governance/domain-context.md` BLS OOH PII section explicitly states: "This dataset contains NO PII. All values are occupation-level aggregates published by a federal statistical agency."

### Scan Methodology

- **Schema analysis:** All 25 columns evaluated against 9 PII categories (Personal Names, Addresses, Government IDs, Financial Accounts, Contact Information, Health Information, Dates of Birth, Biometric Data, Location Data).
- **Domain calibration:** Scanning expectations set from `governance/domain-context.md` BLS OOH PII section, which confirms no personal data is expected.
- **Data characteristics:** 832 rows at one-row-per-occupation grain. All data is aggregate national-level statistics. No individual-level records exist in this dataset.
- **Source provenance:** Data originates from BLS Employment Projections (public federal statistical data). Silver transformation adds derived fields only (no new external data introduced).
- **False positive review:** Two fields (occupation_title, median_annual_wage) evaluated for false positive risk and cleared.
