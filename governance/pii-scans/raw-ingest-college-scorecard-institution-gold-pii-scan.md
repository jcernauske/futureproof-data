# PII Scan Report: gold-career-outcomes-college-scorecard (institution enrichment)

**Date:** 2026-04-16
**Agent:** @pii-scanner
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md §Zone 3
**Scope:** Gold enrichment of `consumable.career_outcomes` — 7 new institution-level cost columns added via LEFT JOIN on `unitid`
**Transformer:** src/gold/college_scorecard_career_outcomes.py (additive update)
**Upstream Scans:**
- `governance/pii-scans/silver-base-college-scorecard-institution-pii-scan.md` — NO PII (Level 1 Public)
- `governance/pii-scans/gold-career-outcomes-college-scorecard-pii-scan.md` — NO PII (Level 1 Public)
**Domain:** Higher Education Outcomes — Program × Institution Cost & Earnings
**Grain:** program × institution × credential level (69,947 rows; invariant preserved)
**PII Instances Found:** 0

---

## Overall Classification: NO PII (Level 1 — Public)

This is a **light-touch confirming scan** for the Gold enrichment defined in §Zone 3 of the spec. The enrichment is a pure LEFT JOIN on `unitid` from `base.college_scorecard_institution` (Silver) into `consumable.career_outcomes` (Gold), adding 7 nullable institution-level cost columns. No new personal data is introduced at Gold.

### 1. Confirm no new PII is added at Gold

The 7 enrichment columns are all **institution-level aggregate statistics** passed through from Silver without transformation:

| # | New Gold Column | Silver Source | Character | PII |
|---|----------------|---------------|-----------|-----|
| 1 | `net_price_annual` | net_price_annual | Institutional aggregate (USD) | None |
| 2 | `cost_of_attendance_annual` | cost_of_attendance_annual | Institutional aggregate (USD) | None |
| 3 | `net_price_4yr` | net_price_4yr | Institutional aggregate × 4 (USD) | None |
| 4 | `institution_control` | institution_control | Deterministic label ("Public" / "Private nonprofit" / "Private for-profit") | None |
| 5 | `tuition_in_state` | tuition_in_state | Published rate (USD) | None |
| 6 | `tuition_out_of_state` | tuition_out_of_state | Published rate (USD) | None |
| 7 | `room_board_on_campus` | room_board_on_campus | Published estimate (USD) | None |

None is personal, identifying, health, biometric, location (beyond institution grain), or financial-account data. All are school-level aggregates or institutional attributes already published by the U.S. Department of Education in the public College Scorecard dataset.

### 2. Confirm inheritance from Silver PII classification

The Silver scan classified **all 35 fields** of `base.college_scorecard_institution` as **Level 1 — Public / NO PII**. Because:

- The Gold transformer applies only a **LEFT JOIN on `unitid`** — a deterministic selection operation with no external enrichment.
- Grain moves from program (69,947 rows) × institution-level attributes via a 1:many join on a public institutional key; the join cannot fabricate personal data.
- No field is renamed, re-typed, re-aggregated, or combined with any non-public source.
- The existing `consumable.career_outcomes` table was already Level 1 — Public (upstream Gold scan).

the Gold-enriched table **inherits Level 1 — Public field-for-field** from both parent Silvers. No sensitivity upgrade occurs.

### 3. Verdict

**NO PII — Level 1 Public.**

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|-----------------|
| Level 1 — Public | 7 (new) + all existing | All enrichment columns and all prior Gold columns |
| Level 2–4 | 0 | — |

---

## Regulatory Implications

Unchanged. No FERPA / GDPR / CCPA / HIPAA / PCI DSS triggers. Institution-level cost aggregates are public government data.

---

## Recommendations for @policy-engineer

- No RLS, column masking, or access-logging changes required.
- Downstream MCP tools (`get_school_programs`, `get_career_paths`) expose these 7 columns with no privacy controls needed.
- Governance focus remains DQ, contract, and lineage — not privacy.

---

## Summary (≤60 words)

Gold enrichment of `consumable.career_outcomes` adds 7 institution-level cost columns via LEFT JOIN on `unitid`. All values are aggregate public statistics inherited verbatim from `base.college_scorecard_institution`, classified Level 1 Public. No personal data is introduced. **Verdict: NO PII / Level 1 Public.** No policy changes required; Gold inherits Silver classification field-for-field.
