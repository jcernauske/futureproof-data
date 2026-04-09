# Audit Trail: PII Scan — BLS OOH

**Date:** 2026-04-07
**Agent:** @pii-scanner
**Spec:** docs/specs/raw-ingest-bls-ooh.md
**Dataset:** raw.bls_ooh
**Sample File:** tests/raw/bls_ooh_sample.xlsx

## Actions Taken
1. Read domain context (`governance/domain-context.md`) — confirmed BLS OOH PII Expectations section states no PII expected.
2. Read spec (`docs/specs/raw-ingest-bls-ooh.md`) — confirmed data source is BLS Employment Projections, aggregate occupation-level statistics.
3. Loaded sample data from `tests/raw/bls_ooh_sample.xlsx` — 12 data rows, 14 columns.
4. Performed field-by-field PII analysis across all 14 columns.
5. Evaluated two false positive candidates (occupation_title, median_annual_wage) — both confirmed non-PII.
6. Wrote scan report to `governance/pii-scans/raw-ingest-bls-ooh-pii-scan.md`.

## Detection Methods Used
- Field name heuristic analysis (checked for name/address/SSN/DOB-indicating field names)
- Value pattern matching (checked for SSN, phone, email, address, credit card formats)
- Context analysis (verified all numeric fields are aggregates, not individual-level)
- Domain context cross-reference (confirmed expectations from domain-context.md)

## Findings
- **PII instances detected:** 0
- **False positive candidates evaluated:** 2 (occupation_title, median_annual_wage)
- **False positive resolution:** Both confirmed as non-PII based on context (occupation taxonomy labels and aggregate medians)

## Sensitivity Classifications
No fields classified at any sensitivity level — dataset contains exclusively public aggregate statistics.

## Rationale
This dataset is published by the Bureau of Labor Statistics as part of its Employment Projections program. All values are occupation-level aggregates (national employment counts, median wages, education requirements). No individual worker, employer, or personal information is present. The domain context document independently confirms zero PII expectation for this data source.
