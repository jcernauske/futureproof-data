## PII Scan Report: bronze.karpathy_ai_exposure
**Date:** 2026-04-09
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance (AI Exposure sub-domain)
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Records Scanned:** 342
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| — | — | — | — | — | — | No PII detected in any field |

### Field-by-Field Analysis
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| slug | string | None | Kebab-case occupation identifier (e.g., "accountants-and-auditors"). Derived from BLS occupation names. Not a personal identifier. |
| occupation_title | string | None | Standardized BLS occupation names (e.g., "Accountants and auditors", "Actors", "Actuaries"). Job category labels, not personal names. |
| category | string | None | BLS category grouping (e.g., "business-and-financial", "healthcare"). Taxonomy label, not personal data. |
| soc_code | string | None | Standard Occupational Classification codes (XX-XXXX format). Federal taxonomy identifiers, not personal identifiers. 52 nulls expected per domain context. |
| exposure_score | int32 | None | Occupation-level AI exposure score (0-10). Aggregate metric, not individual-level data. |
| rationale | string | None | LLM-generated 2-3 sentence explanations of exposure scores. All 342 values scanned for embedded PII patterns (emails, phone numbers, SSNs, personal names, addresses). Zero matches. Content discusses occupation characteristics only. |
| median_pay_annual | double | None | Occupation-level median wage from BLS (e.g., $81,680). Not individual compensation. 2 nulls. |
| num_jobs_2024 | int64 | None | National aggregate employment counts (e.g., 1,579,800). Not individual-level data. 1 null. |
| entry_education | string | None | Categorical education requirement (e.g., "Bachelor's degree"). Not personal education history. 1 null. |
| source_url | string | None | Single value: GitHub raw URL for scores.json. Not personal data. |
| ingested_at | timestamp | None | Pipeline processing timestamp. Not personal data. |
| source_method | string | None | Single value: "github_download". Not personal data. |
| load_date | date | None | Pipeline load date. Not personal data. |

### Detection Methods Applied
| Method | Fields Scanned | Matches |
|--------|---------------|---------|
| Email regex (`[a-zA-Z0-9._%+-]+@...`) | All 8 string fields | 0 |
| SSN regex (`\d{3}-\d{2}-\d{4}`) | All 8 string fields | 0 |
| Phone number regex | All 8 string fields | 0 |
| Credit card regex | All 8 string fields | 0 |
| IP address regex | All 8 string fields | 0 |
| Date of birth keyword detection | All 8 string fields | 0 |
| Street address pattern matching | All 8 string fields | 0 |
| Personal name title detection (Dr./Mr./Mrs./Ms.) | rationale field (free text) | 0 |
| Person-name field heuristics | All column names | 0 |

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
| occupation_title | Could trigger name detection | Standardized BLS occupation category names from the SOC taxonomy (e.g., "Accountants and auditors"). Not personal names. | No action needed — confirmed non-PII. |
| median_pay_annual | Could trigger financial data detection | Occupation-level median aggregates from BLS, not individual compensation records. | No action needed — confirmed non-PII. |
| rationale | Free text could embed PII | All 342 rationale values scanned with multiple regex patterns. Content is strictly about occupation characteristics and AI impact. No personal references found. | No action needed — confirmed non-PII. |

### Regulatory Implications
No PII was detected. No privacy regulations (GDPR, HIPAA, CCPA, FERPA) apply to this dataset. All data is either:
- Public BLS occupation-level aggregates (titles, wages, employment counts, education requirements)
- LLM-generated text describing occupation characteristics (exposure scores and rationales)
- Pipeline metadata (timestamps, URLs, load dates)

The source data (Karpathy's GitHub repository) is public. The BLS occupation data underlying it is public domain (produced by a federal statistical agency).

### Recommendations
1. **No PII remediation required.** All fields contain occupation-level aggregate data or LLM-generated occupation descriptions with zero individual-level data.
2. **No column masking or RLS policies needed** for PII reasons. Access controls, if any, should be based on business requirements rather than privacy requirements.
3. **@policy-engineer:** Skip PII-based policy generation for this dataset. Standard access controls sufficient.
4. **Justification reference:** governance/domain-context.md Karpathy AI Exposure PII section confirms: "No PII. This is entirely occupation-level aggregate data sourced from public BLS descriptions and scored by an LLM. No individual-level data exists anywhere in the pipeline for this source."
