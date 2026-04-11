## PII Scan Report: gold-ai-exposure
**Date:** 2026-04-09
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance (AI Exposure sub-domain)
**Zone:** Gold (Consumable)
**Spec:** gold-ai-exposure
**Records Scanned:** 389 (schema-level scan; one row per occupation)
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

All 9 columns in `consumable.ai_exposure` were evaluated against PII detection categories.

| Field | Data Type | PII Risk | Rationale |
|-------|-----------|----------|-----------|
| record_id | STRING | None | Deterministic SHA-256 hash with prefix 'aie', computed from soc_code. Pipeline-generated, not derived from personal data. |
| soc_code | STRING | None | Standard Occupational Classification code (XX-XXXX). Public federal taxonomy identifier. Not a personal identifier. |
| occupation_title | STRING | None | Standardized BLS occupation names (e.g., "Accountants and auditors"). Job category labels, not personal names. |
| exposure_score | INTEGER | None | Occupation-level AI exposure score (1-10). Aggregate metric, not individual-level data. |
| stat_res | INTEGER | None | Derived score: MIN(11 - exposure_score, 10). Computed from aggregate occupation data. |
| boss_ai_score | INTEGER | None | Derived score: MAX(exposure_score, 1). Computed from aggregate occupation data. |
| rationale | STRING | None | LLM-generated explanation of exposure score (297-587 chars). Describes occupation characteristics. No personal references. |
| category | STRING | None | BLS category grouping (e.g., "healthcare", "business-and-financial"). 24 distinct values. Taxonomy label. |
| promoted_at | TIMESTAMP | None | Gold zone promotion timestamp. Pipeline metadata, not personal data. |

### Re-identification Risk Assessment

| Risk Vector | Assessment | Rationale |
|-------------|-----------|-----------|
| Direct identifiers | None | No names, SSNs, emails, addresses, or other direct identifiers. |
| Quasi-identifiers | None | SOC codes identify occupations (389 categories), not individuals. No geographic or demographic dimensions. |
| Sensitive categories | None | Occupation titles describe career categories, not individual employment status. |
| Re-identification via linkage | None | Occupation-level aggregates. Even if linked to other datasets, no individual-level records exist to re-identify. |

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| occupation_title | Personal Names (NER) | Occupation titles may contain words overlapping with name patterns (e.g., "Baker" in "Bakers"). These are standardized BLS labels. | No action required. |
| rationale | Person-referencing keywords | Words like "patient" and "employee" appear in occupation descriptions. These describe the type of people an occupation serves, not specific individuals. | No action required. |

### Regulatory Implications

**No PII-related regulations apply to this dataset.**

- **FERPA:** Not applicable. No student-level data.
- **HIPAA:** Not applicable. No health records.
- **CCPA/CPRA:** Not applicable. No California consumer personal information.
- **GDPR:** Not applicable. No EU personal data. All data is U.S. occupation-level statistics.

### Lineage from Silver Scan

The upstream Silver table `base.karpathy_ai_exposure` was scanned and confirmed PII-free (see `governance/pii-scans/silver-base-karpathy-ai-exposure-pii-scan.md`). The Gold transformation introduces 2 derived columns (stat_res, boss_ai_score), both computed deterministically from occupation-level exposure_score. No external data sources are joined. No individual-level data is introduced.

### Recommendations

1. **No PII remediation needed.** All 9 fields contain public taxonomy codes, occupation-level LLM scores, derived integers, or pipeline metadata.
2. **No column masking or RLS policies needed** for PII reasons.
3. **Sensitivity Level 1 (Public)** for all fields. Source data is public (BLS taxonomy + Karpathy GitHub).
4. **Consistent with upstream scans.** Raw and Silver PII scans both found zero PII.
