# PII Scan Audit Log
**Timestamp:** 2026-04-05
**Agent:** @pii-scanner
**Spec:** raw-ingest-college-scorecard
**Dataset:** raw.college_scorecard (69,947 rows, 16 columns)

## Scan Decision Log

### 1. Pre-Scan Domain Calibration
- **Action:** Read `governance/domain-context.md` PII Expectations section
- **Result:** Domain context states "No PII -- all fields are institutional/aggregate statistics"
- **Decision:** Proceed with confirmatory scan (low PII risk expected)

### 2. Data Sampling
- **Action:** Sampled 5 full rows and 10 values from each string column
- **Result:** All values confirmed as institution names, program codes, academic descriptions, and system metadata
- **Decision:** No PII indicators found in sample

### 3. Pattern Matching (Full Scan)
- **Action:** Scanned all 69,947 rows across 6 string columns for email, SSN, phone, and ZIP code patterns
- **Columns scanned:** instnm, cipcode, cipdesc, creddesc, source_url, source_method
- **Result:** 0 matches across all patterns
- **Decision:** No PII detected via pattern matching

### 4. Contextual Analysis
- **Action:** Reviewed each column's semantics against PII categories
- **Result:** All fields are institutional identifiers (unitid), public taxonomy codes (cipcode, credlev), aggregate statistics (earnings, debt, counts), or system metadata
- **Decision:** No field contains or could contain individual-level PII

### 5. False Positive Assessment
- **instnm:** Institution names could superficially resemble personal names but are organizational entities. Confirmed by field context. Marked as false positive candidate.
- **unitid:** Numeric identifier but assigned to institutions, not individuals. Marked as false positive candidate.

### 6. Privacy Suppression Assessment
- **Action:** Verified that null values in earnings/debt columns represent FERPA-compliant privacy suppression by the Department of Education
- **Result:** Source applies suppression for cohorts < ~30 completers. Ingestor correctly converts "PrivacySuppressed" to null.
- **Decision:** This is source-side compliance, not PII in our pipeline. No additional action needed.

## Final Classification
**PII Found:** None
**Sensitivity Level:** Level 1 (Public) for all fields
**Regulatory Action Required:** None
**Report Written To:** governance/pii-scans/raw-ingest-college-scorecard-pii-scan.md
