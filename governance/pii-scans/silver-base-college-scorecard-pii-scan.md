## PII Scan Report: base.college_scorecard
**Date:** 2026-04-06
**Agent:** @pii-scanner
**Spec:** silver-base-college-scorecard
**Domain:** Higher Education Outcomes (College Scorecard)
**Records Scanned:** 69,947
**PII Instances Found:** 0

### Scan Methodology

| Method | Description | Result |
|--------|-------------|--------|
| Schema inspection | Read parquet schema to identify column names and types | 18 columns identified; no structurally suspicious fields |
| Field name heuristics | Checked all column names against PII keyword list (name, email, phone, ssn, dob, birth, address, salary, patient, tax, passport, license, account, person) | 2 fields flagged for review: `institution_name`, `program_name` -- both resolved as false positives (see below) |
| Regex pattern matching | Scanned string columns for SSN, email, phone, credit card, IP address, and date-of-birth patterns | Zero matches across all string columns |
| Domain context calibration | Referenced `governance/domain-context.md` PII Expectations section | Domain context explicitly confirms: "This dataset contains NO PII" |
| Cardinality analysis | Reviewed unique value counts and sample values for string columns | All string values are institutional identifiers, program codes, or aggregate labels |

### Fields Scanned

| # | Field | Type | PII Risk Assessment | Conclusion |
|---|-------|------|-------------------|------------|
| 1 | record_id | string | None -- deterministic hash of grain fields | Not PII |
| 2 | unitid | int64 | None -- IPEDS institutional identifier (public record) | Not PII |
| 3 | institution_name | string | Evaluated -- contains institution names (e.g., universities, colleges), NOT personal names | Not PII |
| 4 | institution_control | string | None -- categorical: Public, Private nonprofit, Private for-profit | Not PII |
| 5 | cipcode | string | None -- Classification of Instructional Programs code (XX.XXXX format) | Not PII |
| 6 | program_name | string | Evaluated -- contains academic program descriptions, NOT personal names | Not PII |
| 7 | cip_family | string | None -- 2-digit CIP family code | Not PII |
| 8 | cip_family_name | string | None -- CIP family description (e.g., "Business, Management, Marketing") | Not PII |
| 9 | credential_level | int32 | None -- credential type code (all values = 3 for Bachelor's) | Not PII |
| 10 | credential_description | string | None -- credential label ("Bachelor's Degree") | Not PII |
| 11 | earnings_1yr_median | double | Evaluated -- median aggregate across cohorts, NOT individual earnings | Not PII |
| 12 | earnings_2yr_median | double | Evaluated -- median aggregate across cohorts, NOT individual earnings | Not PII |
| 13 | debt_median | double | Evaluated -- median aggregate across cohorts, NOT individual debt | Not PII |
| 14 | completions_count_1 | int64 | None -- aggregate count of completions | Not PII |
| 15 | completions_count_2 | int64 | None -- aggregate count of completions | Not PII |
| 16 | small_cohort_flag | bool | None -- derived boolean flag | Not PII |
| 17 | source_load_date | date | None -- pipeline metadata date | Not PII |
| 18 | ingested_at | timestamp | None -- pipeline metadata timestamp | Not PII |

### Findings

| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | -- |

**No PII findings.** Zero fields contain personally identifiable information.

### Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 - Public | 0 | None |
| 2 - Internal | 0 | None |
| 3 - Confidential | 0 | None |
| 4 - Restricted | 0 | None |

All 18 fields are institutional/aggregate data requiring no PII-specific handling.

### False Positive Candidates

| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| institution_name | Field name contains "name" keyword | Values are institution names (universities, colleges), not personal names. IPEDS institutional names are public record. | Confirmed not PII. No action required. |
| program_name | Field name contains "name" keyword | Values are academic program descriptions (e.g., "Computer Science", "Nursing"), not personal names. These are CIP taxonomy labels. | Confirmed not PII. No action required. |
| earnings_1yr_median / earnings_2yr_median | Could be mistaken for individual financial data | Values are median aggregates across entire program cohorts, not individual earnings. Source data is pre-aggregated by the Department of Education. | Confirmed not PII. No action required. |
| debt_median | Could be mistaken for individual financial data | Values are median aggregates across entire program cohorts, not individual debt records. Source data is pre-aggregated by the Department of Education. | Confirmed not PII. No action required. |

### Regulatory Implications

**No PII-specific regulations apply to this dataset.**

- **FERPA:** Privacy is already protected at the source. The Department of Education applies suppression rules (cohorts below ~30 completers have earnings/debt values replaced with null) before publishing the College Scorecard data. These suppressed values arrive as null in the Silver table and are preserved as-is.
- **GDPR/CCPA/HIPAA:** Not applicable. No personal data, health records, or individual consumer information is present.
- **PCI DSS:** Not applicable. No payment card or financial account data is present.

### Recommendations

1. **No PII remediation required.** Zero PII was detected. @policy-engineer does not need to create column masking, RLS policies, or encryption rules for PII protection on this table.
2. **Preserve FERPA suppression.** The null values in `earnings_1yr_median`, `earnings_2yr_median`, and `debt_median` represent Department of Education privacy suppression for small cohorts. These must remain null (never imputed or estimated) to maintain FERPA compliance.
3. **Re-scan on schema changes.** If future specs add fields to this table (e.g., institution addresses, contact information, or individual-level data), a new PII scan should be triggered.
4. **Domain context alignment confirmed.** This scan result is consistent with `governance/domain-context.md` which states: "This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures."
