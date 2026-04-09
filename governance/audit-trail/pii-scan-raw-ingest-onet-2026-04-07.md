## PII Scan Audit Trail: raw-ingest-onet
**Date:** 2026-04-07
**Agent:** @pii-scanner
**Spec:** docs/specs/raw-ingest-onet.md
**Artifact:** governance/pii-scans/raw-ingest-onet-pii-scan.md

### What Was Scanned
5 Iceberg tables in the `raw` namespace containing O*NET 30.2 data ingested from the U.S. Department of Labor:

| Table | Records | Columns |
|-------|---------|---------|
| raw.onet_occupations | 1,016 | 7 |
| raw.onet_task_statements | 18,796 | 11 |
| raw.onet_work_activities | 73,308 | 17 |
| raw.onet_work_context | 297,676 | 18 |
| raw.onet_related_occupations | 18,460 | 9 |
| **Total** | **409,256** | **62 unique fields** |

### Detection Methods Used
1. **Field name heuristic analysis** -- scanned all 62 field names for PII-suggestive patterns (name, ssn, email, phone, address, dob, etc.)
2. **Format-specific regex** -- applied SSN, EIN, phone, email, credit card patterns to all string fields
3. **NER pattern matching** -- checked title, description, task, and element_name fields for personal name patterns
4. **Address pattern matching** -- checked all string fields for physical address patterns
5. **Date context analysis** -- evaluated date fields for date-of-birth characteristics
6. **Financial data detection** -- evaluated numeric fields for financial data patterns
7. **Domain context calibration** -- cross-referenced governance/domain-context.md O*NET PII Expectations section

### Classification Decisions
- **All 62 fields classified as non-PII** with high confidence
- O*NET is a public federal dataset containing exclusively occupation-level aggregate data
- Survey respondent identities are anonymized by the DOL before publication
- No field in any table contains, implies, or could be used to derive individual-level personal information

### False Positive Rationale
Six fields were evaluated as potential false positives and dismissed:
1. **title** -- Occupation titles, not personal names (SOC taxonomy labels)
2. **task** -- Generic task descriptions, not individual work records
3. **description** -- Occupation definitions, not individual profiles
4. **incumbents_responding** -- Aggregate sample sizes (18-238), not individual identifiers
5. **element_name** -- Includes health-adjacent terms (e.g., "Exposed to Disease") but these are occupation environment descriptors, not personal health records
6. **domain_source** -- Labels like "Incumbent" and "Occupational Expert" refer to respondent categories, not named individuals

### Corroboration
- governance/domain-context.md O*NET PII Expectations section (line 894): "This dataset contains NO PII. All values are occupation-level aggregates derived from anonymized surveys."
- @cde-tagger confirmed 0 PII columns (governance/audit-trail/cde-tagging-raw-ingest-onet-2026-04-07.md)
- O*NET is published under CC BY 4.0 by the U.S. DOL -- a federal agency would not publish PII in a public dataset

### Outcome
**0 PII instances found.** No remediation, masking, or access restriction required for PII reasons.
