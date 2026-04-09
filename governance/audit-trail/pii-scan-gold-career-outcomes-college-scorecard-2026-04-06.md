## Audit Trail: PII Scan — gold-career-outcomes-college-scorecard

**Timestamp:** 2026-04-06T00:00:00Z
**Agent:** @pii-scanner
**Spec:** gold-career-outcomes-college-scorecard
**Zone:** Gold
**Dataset:** consumable.career_outcomes
**Source file:** data/gold/iceberg_warehouse/consumable/career_outcomes/data/00000-0-c041776d-1eed-4aaa-b959-edee018939cc.parquet

### Actions Taken

1. Read Gold spec (`docs/specs/gold-career-outcomes-college-scorecard.md`) to understand schema and data lineage
2. Read domain context (`governance/domain-context.md`) PII Expectations section for pre-scan calibration
3. Inspected parquet schema (31 fields) via PyArrow
4. Scanned 69,947 rows using DuckDB queries for:
   - Email patterns in string fields
   - SSN-format patterns in string fields
   - Personal name indicators in institution_name and program_name
   - Financial account number patterns in numeric fields
   - Address patterns in string fields
5. Reviewed sample values from institution_name, program_name, cipcode, record_id
6. Verified numeric field ranges (unitid, earnings, debt) are consistent with aggregate data

### Detection Methods Used

| Method | Target Fields | Result |
|--------|--------------|--------|
| Email regex (`@`) | All string fields | 0 matches |
| SSN format (NNN-NN-NNNN) | All string fields | 0 matches |
| Field name heuristics | All 31 fields | No PII-suggestive field names |
| Value range analysis | All numeric fields | All within expected aggregate ranges |
| Sample review | String fields (15+ samples each) | All institutional/program names |
| Domain context calibration | N/A | domain-context.md confirms "No PII expected" |

### Decisions Made

| Decision | Rationale |
|----------|-----------|
| institution_name is NOT PII | Contains university/college names, not personal names. Confirmed by sample review and field context. |
| unitid is NOT personal identifier | IPEDS institution ID from a public registry. Not linked to individuals. |
| Earnings/debt fields are NOT personal financial data | All values are median aggregates across program cohorts, pre-aggregated by the Department of Education. |
| record_id is NOT traceable to individuals | Deterministic hash of grain fields (unitid, cipcode, credlev). Cannot be reversed to identify a person. |
| Overall: Zero PII in dataset | Consistent with domain context assessment and Gold spec's conditional skip recommendation. |

### Sensitivity Classifications

All 31 fields classified as: **No PII / Not applicable**

No sensitivity-based access controls recommended for @policy-engineer.

### Output Artifacts

- PII scan report: `governance/pii-scans/gold-career-outcomes-college-scorecard-pii-scan.md`
- This audit trail: `governance/audit-trail/pii-scan-gold-career-outcomes-college-scorecard-2026-04-06.md`
