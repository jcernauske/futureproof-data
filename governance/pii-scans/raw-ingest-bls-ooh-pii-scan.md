## PII Scan Report: raw.bls_ooh
**Date:** 2026-04-07
**Agent:** @pii-scanner
**Domain:** Higher Education Outcomes (BLS Employment Projections sub-domain)
**Spec:** docs/specs/raw-ingest-bls-ooh.md
**Records Scanned:** 12 (sample from tests/raw/bls_ooh_sample.xlsx)
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| — | — | — | — | — | — | No PII detected in any field |

### Field-by-Field Analysis
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| occupation_title | string | None | Occupation names (e.g., "Software developers", "Registered nurses"). These are job category labels, not personal names. |
| soc_code | string (XX-XXXX) | None | Standard Occupational Classification codes. Federal taxonomy identifiers, not personal identifiers. |
| employment_current | numeric | None | Aggregate national employment counts (in thousands). No individual-level data. |
| employment_projected | numeric | None | Projected aggregate employment. No individual-level data. |
| employment_change_numeric | numeric | None | Aggregate change figures. No individual-level data. |
| employment_change_pct | numeric | None | Percentage change. No individual-level data. |
| openings_annual_avg | numeric | None | Aggregate annual openings. No individual-level data. |
| median_annual_wage | string/numeric | None | Occupation-level median wages. Not individual compensation. Special values include ">=239,200" (top-coded) and "N/A". |
| education_typical | string | None | Categorical education requirement (e.g., "Bachelor's degree"). Not personal education history. |
| education_code | integer | None | Numeric encoding of education level. Not a personal identifier. |
| work_experience | string | None | Categorical experience requirement (e.g., "None", "5 years or more"). Not personal work history. |
| work_experience_code | integer | None | Numeric encoding of experience level. Not a personal identifier. |
| training_typical | string | None | Categorical training requirement (e.g., "None", "Apprenticeship"). Not personal training records. |
| training_code | integer | None | Numeric encoding of training level. Not a personal identifier. |

### Summary by Sensitivity
| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 (Public) | 0 | — |
| 2 (Internal) | 0 | — |
| 3 (Confidential) | 0 | — |
| 4 (Restricted) | 0 | — |

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| occupation_title | Could trigger name detection | These are standardized occupation category names from the SOC taxonomy, not personal names. Values like "Software developers" and "Registered nurses" are job classifications. | No action needed — confirmed non-PII. |
| median_annual_wage | Could trigger financial data detection | These are occupation-level median aggregates published by a federal statistical agency, not individual compensation records. | No action needed — confirmed non-PII. |

### Regulatory Implications
No PII was detected. No privacy regulations (GDPR, HIPAA, CCPA, FERPA) apply to this dataset. All data is published aggregate statistics from the Bureau of Labor Statistics, a federal statistical agency. This data is freely available to the public.

### Recommendations
1. **No PII remediation required.** All fields contain occupation-level aggregate statistics with zero individual-level data.
2. **No column masking or RLS policies needed** for PII reasons. Access controls, if any, should be based on business requirements rather than privacy requirements.
3. **@policy-engineer:** Skip PII-based policy generation for this dataset. Standard access controls sufficient.
4. **Justification reference:** governance/domain-context.md BLS OOH PII Expectations section confirms no personal data — all fields are occupation-level aggregates published by a federal statistical agency.
