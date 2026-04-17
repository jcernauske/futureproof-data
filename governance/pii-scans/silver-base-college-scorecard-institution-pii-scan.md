# PII Scan Report: silver-base-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @pii-scanner
**Spec:** docs/specs/silver-base-college-scorecard-institution.md
**Transformer:** src/silver/college_scorecard_institution_transformer.py
**Physical Model:** governance/models/silver-base-college-scorecard-institution-physical.md
**Upstream Scan:** governance/pii-scans/raw-ingest-college-scorecard-institution-pii-scan.md (concluded: NO PII)
**Domain:** Higher Education Outcomes — Institution-Level Cost of Attendance
**Grain:** Institution (UNITID) — one row per institution
**PII Instances Found:** 0

---

## Overall Classification: NO PII (Level 1 — Public)

This is a **confirming scan**. The Silver `base.college_scorecard_institution` table is derived entirely from Bronze `raw.college_scorecard_institution`, which was scanned and classified as **NO PII / Level 1 — Public** in its entirety. No new data is introduced at the Silver layer — all Silver fields are one of:

1. **Direct pass-through** from Bronze (same value, renamed or typed)
2. **Deterministic label mapping** from a Bronze integer code (institution_control)
3. **Deterministic derivation** from Bronze aggregates (unified COA, unified net price, 4-year totals, quintile routing)
4. **Pipeline metadata** (record_id, source_load_date, ingested_at)

Since transformations are deterministic functions of Bronze values and no external data is joined in at this layer, **PII cannot be introduced by Silver transformations.** The Silver classification inherits Bronze's Level 1 — Public status field-for-field.

---

## Field-by-Field Classification

All 35 Silver fields are classified as **Level 1 — Public** with **No PII**. Each field is listed with its derivation source so the inheritance chain is auditable.

| # | Silver Field | Derivation | Bronze Source | Type | Sensitivity | PII |
|---|-------------|-----------|---------------|------|-------------|-----|
| 1 | record_id | Grain hash over {unitid}, prefix "csi" | (derived) | string | Level 1 — Public | None — synthetic ID over a public institution key |
| 2 | unitid | Pass-through | unitid | long | Level 1 — Public | None — public IPEDS institutional ID |
| 3 | institution_name | Pass-through (renamed from instnm) | instnm | string | Level 1 — Public | None — organization name, not personal |
| 4 | state_abbr | Pass-through (renamed from stabbr) | stabbr | string | Level 1 — Public | None — 2-letter state code at institution grain |
| 5 | institution_control | Label map via CONTROL_LABELS dict | control | string | Level 1 — Public | None — deterministic label ("Public" / "Private nonprofit" / "Private for-profit") |
| 6 | cost_of_attendance_annual | Coalesce: costt4_a ?? costt4_p | costt4_a, costt4_p | double | Level 1 — Public | None — institutional aggregate |
| 7 | cost_of_attendance_4yr | #6 × 4 | (derived) | double | Level 1 — Public | None — institutional aggregate |
| 8 | net_price_annual | pick_by_control(npt4_pub, npt4_priv) | npt4_pub, npt4_priv | double | Level 1 — Public | None — institutional aggregate |
| 9 | net_price_4yr | #8 × 4 | (derived) | double | Level 1 — Public | None — institutional aggregate |
| 10 | net_price_q1 | pick_by_control(npt41_pub, npt41_priv) | npt41_pub, npt41_priv | double | Level 1 — Public | None — income-bracket aggregate across many students |
| 11 | net_price_q2 | pick_by_control(npt42_pub, npt42_priv) | npt42_pub, npt42_priv | double | Level 1 — Public | None — income-bracket aggregate |
| 12 | net_price_q3 | pick_by_control(npt43_pub, npt43_priv) | npt43_pub, npt43_priv | double | Level 1 — Public | None — income-bracket aggregate |
| 13 | net_price_q4 | pick_by_control(npt44_pub, npt44_priv) | npt44_pub, npt44_priv | double | Level 1 — Public | None — income-bracket aggregate |
| 14 | net_price_q5 | pick_by_control(npt45_pub, npt45_priv) | npt45_pub, npt45_priv | double | Level 1 — Public | None — income-bracket aggregate |
| 15 | tuition_in_state | Pass-through (renamed from tuitionfee_in) | tuitionfee_in | double | Level 1 — Public | None — published tuition rate |
| 16 | tuition_out_of_state | Pass-through (renamed from tuitionfee_out) | tuitionfee_out | double | Level 1 — Public | None — published tuition rate |
| 17 | room_board_on_campus | Pass-through (renamed from roomboard_on) | roomboard_on | double | Level 1 — Public | None — published rate |
| 18 | room_board_off_campus | Pass-through (renamed from roomboard_off) | roomboard_off | double | Level 1 — Public | None — published estimate |
| 19 | books_supplies | Pass-through (renamed from booksupply) | booksupply | double | Level 1 — Public | None — published estimate |
| 20 | costt4_a_raw | Pass-through (provenance) | costt4_a | double | Level 1 — Public | None — institutional aggregate |
| 21 | costt4_p_raw | Pass-through (provenance) | costt4_p | double | Level 1 — Public | None — institutional aggregate |
| 22 | npt4_pub_raw | Pass-through (provenance) | npt4_pub | double | Level 1 — Public | None — institutional aggregate |
| 23 | npt4_priv_raw | Pass-through (provenance) | npt4_priv | double | Level 1 — Public | None — institutional aggregate |
| 24 | npt41_pub_raw | Pass-through (provenance) | npt41_pub | double | Level 1 — Public | None — bracket aggregate |
| 25 | npt42_pub_raw | Pass-through (provenance) | npt42_pub | double | Level 1 — Public | None — bracket aggregate |
| 26 | npt43_pub_raw | Pass-through (provenance) | npt43_pub | double | Level 1 — Public | None — bracket aggregate |
| 27 | npt44_pub_raw | Pass-through (provenance) | npt44_pub | double | Level 1 — Public | None — bracket aggregate |
| 28 | npt45_pub_raw | Pass-through (provenance) | npt45_pub | double | Level 1 — Public | None — bracket aggregate |
| 29 | npt41_priv_raw | Pass-through (provenance) | npt41_priv | double | Level 1 — Public | None — bracket aggregate |
| 30 | npt42_priv_raw | Pass-through (provenance) | npt42_priv | double | Level 1 — Public | None — bracket aggregate |
| 31 | npt43_priv_raw | Pass-through (provenance) | npt43_priv | double | Level 1 — Public | None — bracket aggregate |
| 32 | npt44_priv_raw | Pass-through (provenance) | npt44_priv | double | Level 1 — Public | None — bracket aggregate |
| 33 | npt45_priv_raw | Pass-through (provenance) | npt45_priv | double | Level 1 — Public | None — bracket aggregate |
| 34 | source_load_date | Pass-through | load_date | date | Level 1 — Public | None — pipeline metadata |
| 35 | ingested_at | Pipeline timestamp (Silver promote time) | (pipeline) | timestamp | Level 1 — Public | None — pipeline metadata |

---

## Transformation-Level PII Analysis

The Silver transformer applies three categories of operations. None of them can introduce PII:

### 1. Pass-through (21 fields)
Bronze values copied verbatim (possibly renamed). If Bronze has no PII, pass-through cannot create it. Verified: all pass-through sources were classified Level 1 — Public in the Bronze scan.

### 2. Deterministic label mapping (1 field)
`institution_control` maps an integer {1,2,3} to a fixed string label via the `CONTROL_LABELS` dict. No external data, no personal identifier can emerge from mapping `1 -> "Public"`.

### 3. Deterministic numeric derivation (9 fields)
- `cost_of_attendance_annual` = coalesce(costt4_a, costt4_p)
- `cost_of_attendance_4yr` = annual × 4
- `net_price_annual` = pick_by_control(pub, priv) — selects one of two Bronze aggregates
- `net_price_4yr` = annual × 4
- `net_price_q1..q5` = pick_by_control over quintile pairs

All derivations are arithmetic or selection functions over institution-level aggregate financial statistics. They remain institution-level aggregates after transformation. No individualization occurs — four-year totals and quintile routing cannot reverse an aggregate into a person.

### 4. Grain preservation
Silver grain is still **institution (unitid)** — one row per institution, same as Bronze. There is no join, no fan-out, no enrichment that could introduce personal attributes. The ~3,039 row count is preserved minus any rows skipped for missing required fields.

---

## Detection Methods Used

1. **Bronze scan review** — confirmed upstream conclusion of NO PII across all 28 Bronze fields
2. **Transformer code review** — read `college_scorecard_institution_transformer.py` end-to-end. No external data sources, no joins, no PII-relevant enrichment. Only `transform_row` + three helpers (`map_control_label`, `pick_by_control`, `multiply_or_none`).
3. **Schema review** — all 35 Silver fields traced to their Bronze source in `get_silver_schema()`
4. **Grain verification** — grain remains institution-level (UNITID); structurally rules out personal data
5. **Field name heuristics** — no Silver field name suggests personal data (no names, emails, phones, SSNs, DOBs, addresses beyond state code, geolocation, health, biometrics)

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|-----------------|
| Level 1 — Public | 35 | All Silver fields |
| Level 2 — Internal | 0 | — |
| Level 3 — Confidential | 0 | — |
| Level 4 — Restricted | 0 | — |

---

## False Positive Candidates

None new at the Silver layer. The same candidates flagged and dismissed in the Bronze scan (`instnm`, `stabbr`, `unitid`, the `npt*` quintile fields) carry through unchanged:

| Silver Field | Could Look Like | Why It's Not PII |
|-------------|-----------------|------------------|
| institution_name | Personal name (NER) | Organization name — inherited from instnm |
| state_abbr | Address component | 2-letter state code at institution grain |
| unitid | Identifier | Public IPEDS institutional ID |
| net_price_q1..q5 | Individual income/financial | Aggregate averages across many students per income bracket |
| cost_of_attendance_4yr, net_price_4yr | Individual financial records | Institutional aggregate × 4, still aggregate |

---

## Regulatory Implications

Unchanged from Bronze. No regulation is triggered by the Silver transformation.

| Regulation | Applies? | Rationale |
|-----------|----------|-----------|
| FERPA | No | Student-level suppression already applied upstream by DoEd/IPEDS |
| GDPR | No | No identifiable natural persons |
| CCPA / CPRA | No | No personal information |
| HIPAA | No | Not health data |
| PCI DSS | No | No payment account data |

---

## Recommendations for @policy-engineer

- **No RLS policies required** for `base.college_scorecard_institution`. All fields are Level 1 — Public.
- **No column masking required.** No sensitive field exists.
- **No access logging required beyond standard pipeline audit.**
- **Downstream inheritance:** Gold tables derived from this Silver base (e.g., `consumable.career_outcomes` cost-of-attendance enrichment) inherit Level 1 — Public. No sensitivity upgrade occurs through any transformation in the current pipeline.
- **Governance focus:** Focus effort on data quality, contract, and lineage controls — not privacy controls — for this dataset.

---

## Conclusion

`base.college_scorecard_institution` contains **no PII**. All 35 Silver fields are classified **Level 1 — Public** by direct inheritance from the Bronze scan, confirmed by transformer-level analysis showing only deterministic pass-through, label mapping, and arithmetic derivation over institution-level aggregates.

**Scan confidence:** High. Inheritance chain is auditable field-by-field. Transformer introduces no external data.

**Recommended next step:** Proceed with Silver promote. No blocking PII concerns. No changes required to downstream policy posture.
