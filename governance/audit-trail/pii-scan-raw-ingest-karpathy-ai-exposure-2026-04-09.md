## PII Scanner Audit Log: raw-ingest-karpathy-ai-exposure

**Date:** 2026-04-09
**Agent:** @pii-scanner
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Dataset:** bronze.karpathy_ai_exposure
**Table Location:** data/bronze/iceberg_warehouse/bronze/karpathy_ai_exposure/

### Scan Summary
- **Records scanned:** 342
- **Fields scanned:** 13 (slug, occupation_title, category, soc_code, exposure_score, rationale, median_pay_annual, num_jobs_2024, entry_education, source_url, ingested_at, source_method, load_date)
- **String fields with pattern detection:** 8 (slug, occupation_title, category, soc_code, rationale, entry_education, source_url, source_method)
- **PII instances found:** 0
- **Result:** CLEAN — no PII detected

### Detection Methods Used
1. Regex pattern matching for: email addresses, SSNs, phone numbers, credit card numbers, IP addresses, street addresses, date-of-birth keywords
2. Named entity recognition heuristics for personal name titles (Dr./Mr./Mrs./Ms.) in free-text rationale field
3. Field name heuristics for person-name patterns
4. Domain context calibration from governance/domain-context.md

### Domain Context Calibration
- Read governance/domain-context.md Karpathy AI Exposure section before scanning
- Domain context states: "No PII. Entirely occupation-level aggregate data."
- PII Expectations table lists all PII types as "No" / "N/A"
- Scan results confirm domain context assessment

### False Positive Decisions
| Decision | Rationale |
|----------|-----------|
| occupation_title values are not personal names | All 342 values are standardized BLS occupation category names from the SOC taxonomy |
| median_pay_annual values are not financial PII | Occupation-level median aggregates from BLS, not individual compensation |
| rationale free text contains no embedded PII | All 342 values scanned with 8 regex patterns — zero matches; content discusses occupation characteristics only |

### Sensitivity Classifications
No fields classified at any sensitivity level. All data is public aggregate information.

### Artifacts Produced
- PII scan report: governance/pii-scans/raw-ingest-karpathy-ai-exposure-pii-scan.md
- Audit log: governance/audit-trail/pii-scan-raw-ingest-karpathy-ai-exposure-2026-04-09.md
