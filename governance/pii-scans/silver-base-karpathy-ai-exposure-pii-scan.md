## PII Scan Report: base.karpathy_ai_exposure (Silver)
**Date:** 2026-04-09
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance (AI Exposure sub-domain)
**Spec:** silver-base-karpathy-ai-exposure
**Records Scanned:** 419
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | No PII detected in any field |

### Field-by-Field Analysis
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| record_id | string (not null) | None | Deterministic hash identifier (format `kai-{hex}`). Pipeline-generated, not a personal identifier. |
| soc_code | string (nullable) | None | Standard Occupational Classification codes (XX-XXXX format). Federal taxonomy identifiers, not personal identifiers. |
| slug | string (not null) | None | Kebab-case occupation identifier (e.g., "accountants-and-auditors"). Derived from BLS occupation names. Not a personal identifier. |
| occupation_title | string (not null) | None | Standardized BLS occupation names (e.g., "Accountants and auditors", "Aerospace engineers"). Job category labels, not personal names. |
| category | string (not null) | None | BLS category grouping (e.g., "business-and-financial", "healthcare"). 25 unique values. Taxonomy label, not personal data. |
| exposure_score | int32 (not null) | None | Occupation-level AI exposure score (1-10 in current data, 0-10 valid range). Aggregate metric, not individual-level data. |
| rationale | string (not null) | None | LLM-generated explanations of exposure scores (297-587 chars). All 419 values scanned with multiple regex patterns and keyword detection. Content discusses occupation characteristics only. Generic words like "patient", "individual", and "employee" appear frequently but refer to occupation duties, not specific people. |
| bls_match | boolean (not null) | None | Flag indicating whether SOC code matches BLS OOH data. Pipeline metadata, not personal data. |
| soc_resolved_method | string (not null) | None | Enum of 4 values: direct, broad_expansion, title_match, unresolved. Pipeline metadata, not personal data. |
| source_load_date | date (not null) | None | Pipeline load date. Not personal data. |
| ingested_at | timestamp (not null) | None | Pipeline processing timestamp. Not personal data. |

### Detection Methods Applied
| Method | Fields Scanned | Matches |
|--------|---------------|---------|
| Email regex (`[a-zA-Z0-9._%+-]+@...`) | All 7 string fields | 0 |
| SSN regex (`\d{3}-\d{2}-\d{4}`) | All 7 string fields | 0 |
| Phone number regex (`\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}`) | All 7 string fields | 0 |
| Credit card regex (`\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}`) | All 7 string fields | 2 (false positives in record_id -- see below) |
| IP address regex (`\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`) | All 7 string fields | 0 |
| Date of birth pattern matching | All 7 string fields | 0 |
| Street address pattern matching | All 7 string fields | 0 |
| Personal name title detection (Mr./Mrs./Ms./Dr./Prof.) | rationale field (free text) | 0 (generic words only -- see False Positive Candidates) |
| Person-referencing keyword detection (patient, employee, individual) | rationale field | 80+ matches (all generic occupation descriptions -- see False Positive Candidates) |
| Person-name field heuristics | All column names | 0 |

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
| record_id | Credit card pattern (2 matches) | Hash-based record IDs (`kai-9758096660841610`, `kai-6510768448277948`) contain 16-digit numeric substrings that match the credit card regex. These are deterministic pipeline-generated identifiers, not financial instruments. | No action needed -- confirmed non-PII. |
| occupation_title | Could trigger name detection | Standardized BLS occupation category names from the SOC taxonomy (e.g., "Accountants and auditors"). Not personal names. 419 values checked. | No action needed -- confirmed non-PII. |
| rationale | Generic person-referencing words | Words like "patient" (45+ occurrences), "individual" (25+ occurrences), and "employee" (4+ occurrences) appear in occupation descriptions. These describe the type of people an occupation serves, not specific individuals. Example: "The core duties of nursing assistants...such as bathing, dressing, and physically transf[erring patients]..." | No action needed -- confirmed non-PII. Generic occupational vocabulary. |

### Regulatory Implications
No PII was detected. No privacy regulations (GDPR, HIPAA, CCPA, FERPA) apply to this dataset. All data is either:
- Public BLS occupation-level aggregates (titles, SOC codes, categories)
- LLM-generated text describing occupation characteristics (exposure scores and rationales)
- Pipeline-derived metadata (record IDs, match flags, resolution methods, timestamps)

The source data (Karpathy's GitHub repository) is public. The BLS occupation data underlying it is public domain (produced by a federal statistical agency). The Silver transformation (SOC broad code expansion, title matching) introduces no new PII -- it only maps existing occupation-level data to additional SOC codes.

### Recommendations
1. **No PII remediation required.** All fields contain occupation-level aggregate data or LLM-generated occupation descriptions with zero individual-level data.
2. **No column masking or RLS policies needed** for PII reasons. Access controls, if any, should be based on business requirements rather than privacy requirements.
3. **@policy-engineer:** Skip PII-based policy generation for this dataset. Standard access controls sufficient.
4. **Consistent with Raw zone scan.** The Raw zone PII scan (governance/pii-scans/raw-ingest-karpathy-ai-exposure-pii-scan.md) also found zero PII. The Silver transformation adds no new data sources or personal information.
5. **Justification reference:** governance/domain-context.md confirms: "No PII. This is entirely occupation-level aggregate data sourced from public BLS descriptions and scored by an LLM. No individual-level data exists anywhere in the pipeline for this source."
