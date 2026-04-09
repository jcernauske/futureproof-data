## PII Scan Audit Log

**Timestamp:** 2026-04-06
**Agent:** @pii-scanner
**Spec:** silver-base-college-scorecard
**Dataset:** base.college_scorecard
**Source File:** data/silver/iceberg_warehouse/base/college_scorecard/data/00000-0-03c516a9-a2cb-462e-8217-70a1b596e133.parquet

### Scan Parameters

| Parameter | Value |
|-----------|-------|
| Records scanned | 69,947 |
| Columns scanned | 18 |
| String columns scanned | 8 (record_id, institution_name, institution_control, cipcode, program_name, cip_family, cip_family_name, credential_description) |
| Numeric columns reviewed | 7 (unitid, credential_level, earnings_1yr_median, earnings_2yr_median, debt_median, completions_count_1, completions_count_2) |

### Detection Methods Used

1. **Parquet schema inspection** -- Read Arrow schema to identify all column names, types, and nullability
2. **Field name heuristic matching** -- Compared column names against PII keyword list: name, email, phone, ssn, dob, birth, address, salary, patient, tax, passport, license, account, person
3. **Regex pattern scanning** -- Applied regex patterns for SSN, email, phone, credit card, IP address, DOB formats against all string column values
4. **Domain context calibration** -- Read `governance/domain-context.md` PII Expectations section to set scanning expectations
5. **Spec review** -- Read `docs/specs/silver-base-college-scorecard.md` to understand field semantics and data lineage

### False Positive Decisions

| Field | Flagged By | Resolution | Rationale |
|-------|-----------|------------|-----------|
| institution_name | Field name heuristic ("name") | Dismissed | Contains institution names (universities/colleges), not personal names. Values are public IPEDS data. |
| program_name | Field name heuristic ("name") | Dismissed | Contains CIP taxonomy program descriptions, not personal names. |
| earnings_1yr_median | Contextual review (financial data) | Dismissed | Median aggregates across program cohorts, not individual earnings. Pre-aggregated by Dept. of Education. |
| earnings_2yr_median | Contextual review (financial data) | Dismissed | Median aggregates across program cohorts, not individual earnings. Pre-aggregated by Dept. of Education. |
| debt_median | Contextual review (financial data) | Dismissed | Median aggregates across program cohorts, not individual debt. Pre-aggregated by Dept. of Education. |

### Sensitivity Classifications

All 18 fields classified as: **No PII -- no sensitivity level assigned.**

Justification: Domain context document (`governance/domain-context.md`) explicitly confirms "This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures. Privacy is protected at the source by the Department of Education's suppression rules (FERPA)."

### Outcome

- **PII found:** 0 instances
- **Report written to:** `governance/pii-scans/silver-base-college-scorecard-pii-scan.md`
- **Downstream action required:** None. @policy-engineer does not need PII-based access controls for this table.
