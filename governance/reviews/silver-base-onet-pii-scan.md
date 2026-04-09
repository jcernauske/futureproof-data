## PII Scan Report: silver-base-onet
**Date:** 2026-04-08
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance (O*NET federal occupation data)
**Spec:** silver-base-onet
**Tables Scanned:** 4
**Total Records Scanned:** 92,594
**PII Instances Found:** 0

### Tables Scanned

| Table | Rows | Columns | Text Fields Scanned |
|-------|------|---------|-------------------|
| base.onet_occupations | 798 | 14 | primary_title, description, onet_detail_codes |
| base.onet_activity_profiles | 31,734 | 11 | element_name |
| base.onet_context_profiles | 44,118 | 11 | element_name |
| base.onet_career_transitions | 15,944 | 9 | (no free-text fields) |

### Detection Methods Applied

| Method | Patterns Tested | Hits |
|--------|----------------|------|
| Email address regex | `*@*.*` | 0 |
| Phone number regex | `\b\d{3}[-.]\\d{3}[-.]\\d{4}\b` | 0 |
| SSN regex | `\b\d{3}-\d{2}-\d{4}\b` | 0 |
| Street address patterns | `\b\d+ (Street|Ave|Rd|Blvd...)\b` | 0 |
| Honorific + name patterns | `(Mr.|Mrs.|Ms.|Dr.) + Name` | 0 |
| Credit card number patterns | 16-digit grouped | 0 |
| Field name heuristics | Checked for name/email/phone/ssn/address columns | None found |

### Findings

No PII detected. All fields contain aggregated occupation-level data:
- **SOC codes** (XX-XXXX format) -- occupation classification codes, not personal identifiers
- **Occupation titles** -- generic job titles (e.g., "Chief Executives"), not individual names
- **Occupation descriptions** -- standardized federal descriptions of job duties
- **Element names** -- O*NET Content Model taxonomy labels (e.g., "Getting Information")
- **Numeric scores** -- importance ratings, context values, relatedness indices
- **System fields** -- record_id hashes, dates, timestamps, boolean flags

### Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 - Public | 0 | N/A |
| 2 - Internal | 0 | N/A |
| 3 - Confidential | 0 | N/A |
| 4 - Restricted | 0 | N/A |

All data is aggregated federal survey data published by the U.S. Department of Labor. No individual-level data exists in these tables.

### False Positive Candidates

None. No PII patterns were detected, so no false positive analysis was needed.

### Regulatory Implications

No PII-related regulations apply. This data is:
- Aggregated occupation-level statistics from anonymized federal surveys
- Published openly by the U.S. Department of Labor via O*NET Online
- Contains no individual respondent data, no demographic breakdowns at the person level
- No GDPR, HIPAA, CCPA, or FERPA implications

### Recommendations

- **No masking, encryption, or RLS policies needed** for these 4 Silver tables
- **No special handling required** by @policy-engineer
- Standard access controls sufficient for all fields
- This aligns with the spec's own assessment: "@pii-scanner: SKIP -- Aggregated occupation-level data from anonymized federal surveys. No individual data."

### Scan Decision Rationale

The spec marked pii-scanner as conditionally skippable. This scan was run as a confirmation pass. The data matches expectations: all 92,594 rows across 4 tables contain only occupation-level aggregate data with zero individual PII.
