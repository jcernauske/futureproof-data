## PII Scan Report: crosswalk-cip-soc
**Date:** 2026-04-08
**Agent:** @pii-scanner
**Domain:** Higher Education Outcomes (CIP-SOC Crosswalk sub-domain)
**Spec:** docs/specs/crosswalk-cip-soc.md
**Records Scanned:** 6,097 (CIP-SOC sheet from CIP2020_SOC2018_Crosswalk.xlsx) + 180 (Unmatched SOC Codes sheet)
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | No PII detected in any field |

### Field-by-Field Analysis
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| CIP2020Code (cipcode) | string (XX.XXXX) | None | Classification of Instructional Programs code. A federal taxonomy identifier for academic programs, not a personal identifier. Example: "52.0201". |
| CIP2020Title (cip_title) | string | None | Academic program names from the NCES CIP taxonomy. Examples: "Agriculture, General.", "Business Administration and Management, General." These are standardized program category names, not personal names. |
| SOC2018Code (soc_code) | string (XX-XXXX) | None | Standard Occupational Classification code. A federal taxonomy identifier for occupations, not a personal identifier. Example: "11-1021". |
| SOC2018Title (soc_title) | string | None | Occupation names from the BLS SOC taxonomy. Examples: "General and Operations Managers", "Animal Scientists". These are standardized occupation category names, not personal names. |

### Derived Fields (Silver zone)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| record_id | string | None | Deterministic hash of cipcode + soc_code. Not a personal identifier. |
| cip_family | string (2-digit) | None | First 2 characters of cipcode. Taxonomy grouping code. |
| soc_major_group | string (2-digit) | None | First 2 characters of soc_code. Taxonomy grouping code. |
| has_scorecard_match | boolean | None | Join-existence flag. Contains true/false only. |
| has_bls_match | boolean | None | Join-existence flag. Contains true/false only. |
| has_onet_match | boolean | None | Join-existence flag. Contains true/false only. |
| match_quality | string (enum) | None | Derived category label. One of 5 fixed values. |

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
| cip_title | Could trigger name detection | These are standardized academic program names from the NCES CIP 2020 taxonomy (e.g., "Agricultural Economics", "Computer Science"). They are federal taxonomy labels, not personal names. | No action needed -- confirmed non-PII. |
| soc_title | Could trigger name detection | These are standardized occupation names from the BLS SOC 2018 taxonomy (e.g., "Economists", "Software Developers"). They are federal taxonomy labels, not personal names. | No action needed -- confirmed non-PII. |

### Regulatory Implications
No PII was detected. No privacy regulations (GDPR, HIPAA, CCPA, FERPA) apply to this dataset. The CIP-SOC crosswalk is a public-domain government publication jointly produced by the National Center for Education Statistics (NCES) and the Bureau of Labor Statistics (BLS). It contains only taxonomy codes and standardized category names. No individual-level data of any kind is present.

### Recommendations
1. **No PII remediation required.** All fields contain federal taxonomy codes and standardized category names with zero individual-level data.
2. **No column masking or RLS policies needed** for PII reasons. Access controls, if any, should be based on business requirements rather than privacy requirements.
3. **@policy-engineer:** Skip PII-based policy generation for this dataset. Standard access controls sufficient.
4. **Justification reference:** governance/domain-context.md confirms no personal data across all three source domains (College Scorecard, BLS OOH, O*NET). The crosswalk is a pure taxonomy bridge containing only codes and labels from these same federal sources.
5. **Spec concurrence:** The spec itself (docs/specs/crosswalk-cip-soc.md) marks @pii-scanner as SKIP with justification "Public taxonomy crosswalk. No individual data." This scan confirms that assessment.
