# PII Scan Report: ipeds-finance-v1.4 (delta)
**Date:** 2026-05-01
**Agent:** @pii-scanner
**Domain:** Higher education institutional finance (IPEDS)
**Spec:** `docs/specs/ipeds-finance-v1.4.md`
**Records Scanned:** N/A (additive delta — schema-level confirmation)
**PII Instances Found:** 0

## Summary

Confirming **PII = 0 across all zones (raw, base, consumable)** for the v1.4 additive delta to IPEDS Finance. This pass corroborates the cde-tagger's prior confirmation in `governance/cde-tagging/consumable-ipeds-finance-profile.md` (PII=0).

## v1.4 Delta Fields Reviewed

| Field | Type | Classification | Justification |
|-------|------|----------------|---------------|
| `endowment_value_flag` | string | Level 1 — Public | 5-code IPEDS imputation enum: `{R, A, P, Z, N}` or NULL. Categorical metadata, no person attached. |
| `source_load_date` | timestamp | Level 1 — Public | Pipeline load timestamp. System-generated, not associated with any natural person. |
| `endowment_value_provenance` | string | Level 1 — Public | Rename of the imputation flag — same enum, same non-PII status. |

## System-Office Filter

The v1.4 system-office filter operates on **institution names** and **financial metrics** (endowment, revenue, expenses). Institutions are organizations/legal entities, not natural persons — outside the scope of GDPR/CCPA/FERPA personal-data definitions. No PII implication.

## Regulatory Implications

None. IPEDS Finance is institution-level public reporting data published by NCES; no FERPA student-record exposure, no GDPR data-subject linkage, no HIPAA scope.

## Recommendations

- No new policies required from @policy-engineer for the v1.4 delta.
- Existing public-data handling continues to apply.

## Cross-References

- CDE tagging confirmation: `governance/cde-tagging/consumable-ipeds-finance-profile.md` (PII=0)
- Prior raw-zone scan: `governance/pii-scans/raw-ipeds-finance-pii-scan.md`
