## Audit Trail: PII Scan — silver-base-bls-ooh
**Timestamp:** 2026-04-07
**Agent:** @pii-scanner
**Spec:** docs/specs/silver-base-bls-ooh.md
**Dataset:** base.bls_ooh (Silver zone)

### Action Summary
| Action | Detail |
|--------|--------|
| Dataset scanned | base.bls_ooh (25 columns, 832 rows, grain: soc_code) |
| Detection methods | Schema analysis, field name heuristics, domain context calibration, false positive review |
| PII instances found | 0 |
| False positive candidates reviewed | 2 (occupation_title, median_annual_wage) |
| Sensitivity classification | Level 1 (Public) for all fields |

### Detection Methods Used
1. **Field name heuristics:** Checked all 25 column names against PII-indicative patterns (name, ssn, dob, address, email, phone, account, etc.). No matches.
2. **Data type analysis:** Reviewed types (VARCHAR, BIGINT, DOUBLE, BOOLEAN, INTEGER, DATE, TIMESTAMP) for PII-carrying potential. All numeric/boolean fields are aggregate statistics.
3. **Domain context calibration:** Read `governance/domain-context.md` BLS OOH PII section confirming no personal data expected.
4. **Source provenance check:** Confirmed data originates from BLS (federal statistical agency, public domain data).
5. **Silver transformation review:** Verified no new external data introduced in Silver — only derived fields from existing Bronze data.

### False Positive Decisions
| Field | Initial Flag | Decision | Rationale |
|-------|-------------|----------|-----------|
| occupation_title | Potential personal name overlap | Cleared — not PII | Standardized BLS occupation labels, not personal names. Field context (soc_code grain) confirms occupational taxonomy. |
| median_annual_wage | Potential financial PII | Cleared — not PII | Occupation-level statistical median, not individual compensation. Published as public data by BLS. |

### Sensitivity Classification Rationale
All fields classified as Level 1 (Public) because:
- Source data is published by a federal statistical agency as public domain data
- All values are occupation-level aggregates (no individual records)
- No personal identifiers, contact information, or sensitive personal data present
- Domain context document explicitly confirms zero PII expectation

### Artifacts Produced
| Artifact | Path |
|----------|------|
| PII Scan Report | governance/pii-scans/silver-base-bls-ooh-pii-scan.md |
| Audit Trail Entry | governance/audit-trail/pii-scan-silver-base-bls-ooh-2026-04-07.md |
