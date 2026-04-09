## Audit Trail: PII Scan for gold-occupation-profiles-bls-ooh

**Timestamp:** 2026-04-07
**Agent:** @pii-scanner
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Table:** consumable.occupation_profiles
**Zone:** Gold (Consumable)
**Domain:** BLS Employment Projections (Occupational Outlook Handbook)

### What Was Scanned

- **Dataset:** consumable.occupation_profiles (832 rows, 31 columns)
- **Grain:** One row per occupation (soc_code)
- **Source:** Derived from `base.bls_ooh` (Silver zone, previously scanned PII-free)

### Detection Methods Used

1. **Schema-level field analysis:** Evaluated all 31 column names, types, and descriptions against 9 PII categories (Personal Names, Addresses, Government IDs, Financial Accounts, Contact Information, Health Information, Dates of Birth, Biometric Data, Location Data).
2. **Domain context calibration:** Read `governance/domain-context.md` BLS OOH PII Expectations section before scanning. Section confirms: "This dataset contains NO PII. All values are occupation-level aggregates published by a federal statistical agency."
3. **Upstream lineage review:** Reviewed Silver PII scan (`governance/pii-scans/silver-base-bls-ooh-pii-scan.md`) to confirm no PII in source data.
4. **Physical model review:** Reviewed `governance/models/gold-occupation-profiles-bls-ooh-physical.md` for all column definitions. Physical model explicitly marks all 31 columns as `Is PII: false`.
5. **Re-identification risk assessment:** Four-vector analysis (direct identifiers, quasi-identifiers, sensitive categories, linkage risk).
6. **False positive evaluation:** Four field groups identified as potential false positives, all cleared with documented rationale.

### Sensitivity Classifications

All 31 fields classified as Sensitivity Level 1 (Public). No fields require elevated handling.

### False Positive Decisions

| Field Group | Pattern Triggered | Decision | Rationale |
|-------------|------------------|----------|-----------|
| occupation_title | NER name patterns | Not PII | BLS standardized occupation labels, not personal names |
| median_annual_wage | Financial data pattern | Not PII | Occupation-level statistical median, not individual compensation |
| grw_score, market_score | Sensitive metric pattern | Not PII | Derived from aggregate public data, not individual performance |
| wage_percentile_overall, wage_percentile_education_tier | Individual ranking pattern | Not PII | Rank occupations against each other, not individuals |

### Result

**Zero PII instances found.** Scan confirms this Gold data product requires no PII remediation, column masking, or PII-based RLS policies.

### Output Artifact

- PII scan report: `governance/pii-scans/gold-occupation-profiles-bls-ooh-pii-scan.md`
