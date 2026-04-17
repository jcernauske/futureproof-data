# Logical Model: silver-base-college-scorecard-institution

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** Higher Education Institutional Finance
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Conceptual Model:** governance/models/silver-base-college-scorecard-institution-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-14
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    COLLEGE_SCORECARD_INSTITUTION {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        text state_abbr
        text institution_control
        numeric cost_of_attendance_annual
        numeric net_price_annual
        numeric cost_of_attendance_4yr
        numeric net_price_4yr
        numeric net_price_q1
        numeric net_price_q2
        numeric net_price_q3
        numeric net_price_q4
        numeric net_price_q5
        numeric tuition_in_state
        numeric tuition_out_of_state
        numeric room_board_on_campus
        numeric room_board_off_campus
        numeric books_supplies
        numeric costt4_a_raw
        numeric costt4_p_raw
        numeric npt4_pub_raw
        numeric npt4_priv_raw
        numeric npt41_pub_raw
        numeric npt42_pub_raw
        numeric npt43_pub_raw
        numeric npt44_pub_raw
        numeric npt45_pub_raw
        numeric npt41_priv_raw
        numeric npt42_priv_raw
        numeric npt43_priv_raw
        numeric npt44_priv_raw
        numeric npt45_priv_raw
        date source_load_date
        timestamp ingested_at
    }
    COLLEGE_SCORECARD_INSTITUTION ||--o{ COLLEGE_SCORECARD : "enriches via unitid"
    COLLEGE_SCORECARD {
        identifier unitid NK
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies 7 entities (Institution, Control Type, Institution Location, Cost of Attendance, Net Price, Income Band Net Price, Tuition Structure, Living Cost Estimate). Per the Silver Base zone pattern, these are flattened into a single denormalized `base.college_scorecard_institution` table.

This is appropriate because:
1. The source data is already at institution grain with every measure in a single row.
2. Silver Base tables are designed as wide, query-ready fact tables for downstream Gold zone consumption.
3. All conceptual relationships resolve to 1:1 or 1:0..1 per row at institution grain -- no many-to-many relationships exist.
4. The 5 Income Band Net Price values are a bounded, ordered set (q1..q5) and are naturally modeled as 5 wide columns rather than a long-form satellite.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per institution (UNITID) |
| **Natural key fields** | `unitid` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id()` with prefix `csi`) |
| **Uniqueness constraint** | Zero duplicates on `unitid`. Enforced at load time. |
| **Expected cardinality** | ~6,500 rows (after PREDDEG=3 / ICLEVEL=1 filter) |

---

## Relationships

| From | To | Type | Key | Notes |
|------|-----|------|-----|-------|
| `base.college_scorecard_institution` | `raw.college_scorecard_institution` | 1:1 | `unitid` | Lineage -- every Silver row has exactly one Bronze source row. Lineage edges written to `governance/lineage/`. |
| `base.college_scorecard_institution` | `base.college_scorecard` | 1:M | `unitid` | An institution (this table) has many program offerings (field-of-study table). Used by Gold LEFT JOIN. No referential integrity enforced (institutions here may have zero programs in the field-of-study data and vice versa). |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. `NK` denotes natural key components.

### Institution (Core Identity)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-001 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from `unitid` via `compute_grain_id()` with prefix `csi`. Stable across pipeline re-runs. |
| unitid | BT-001 | identifier | NOT NULL | true | false | IPEDS 6-digit institution identifier. Natural key. Authoritative, stable across reporting years. Join key to `base.college_scorecard` and downstream `consumable.career_outcomes`. |
| institution_name | BT-002 | text | NOT NULL | false | false | Official institution name as reported to IPEDS. Source: `instnm`. Multi-campus systems may share the same name across distinct UNITIDs. |

### Institution Location

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| state_abbr | BT-103 | text | NOT NULL | false | false | 2-letter USPS state abbreviation (e.g., `CA`, `NY`, `TX`). Source: `stabbr`. Supports state-level filtering and future RPP (Regional Price Parity) joins. |

### Control Type

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| institution_control | *pending* | text | NOT NULL | false | false | Human-readable governance classification: `Public`, `Private nonprofit`, or `Private for-profit`. Derived from raw integer `control` field: 1→Public, 2→Private nonprofit, 3→Private for-profit. Drives public/private routing for Net Price and Income Band Net Price. @data-steward should propose a dedicated glossary term. |

### Cost of Attendance

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| cost_of_attendance_annual | BT-110 | numeric | NULLABLE | true | false | Unified annual Cost of Attendance. Derived: `COALESCE(costt4_a, costt4_p)`. Represents total sticker price (tuition + fees + books + supplies + room & board + living expenses) before any aid. Null when both raw variants are null. |
| cost_of_attendance_4yr | BT-110 | numeric | NULLABLE | true | false | 4-year total Cost of Attendance. Derived: `cost_of_attendance_annual × 4`. Null iff `cost_of_attendance_annual` is null. Assumes flat year-over-year pricing. |
| costt4_a_raw | BT-110 | numeric | NULLABLE | false | false | Raw academic-year Cost of Attendance from source. Carried through for provenance. Source: `costt4_a`. |
| costt4_p_raw | BT-110 | numeric | NULLABLE | false | false | Raw program-year Cost of Attendance from source. Carried through for provenance. Source: `costt4_p`. |

### Net Price

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| net_price_annual | BT-111 | numeric | NULLABLE | true | false | Unified annual Net Price. Derived via control-based routing: control=1 → `npt4_pub`; control∈(2,3) → `npt4_priv`. Represents what students actually pay per year after grants and scholarships. Null when the routed raw field is null. |
| net_price_4yr | BT-111 | numeric | NULLABLE | true | false | 4-year total Net Price. Derived: `net_price_annual × 4`. Null iff `net_price_annual` is null. Primary input to the Gold ROI formula. |
| npt4_pub_raw | BT-111 | numeric | NULLABLE | false | false | Raw average net price from the public-institution population. Carried through for provenance. Source: `npt4_pub`. |
| npt4_priv_raw | BT-111 | numeric | NULLABLE | false | false | Raw average net price from the private-institution population. Carried through for provenance. Source: `npt4_priv`. |

### Income Band Net Price

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| net_price_q1 | BT-112 | numeric | NULLABLE | true | false | Unified Net Price for family income band 1 ($0–$30K). Derived via control-based routing: control=1 → `npt41_pub`; control∈(2,3) → `npt41_priv`. |
| net_price_q2 | BT-112 | numeric | NULLABLE | true | false | Unified Net Price for family income band 2 ($30K–$48K). Routed via control the same way as q1. |
| net_price_q3 | BT-112 | numeric | NULLABLE | true | false | Unified Net Price for family income band 3 ($48K–$75K). Routed via control. |
| net_price_q4 | BT-112 | numeric | NULLABLE | true | false | Unified Net Price for family income band 4 ($75K–$110K). Routed via control. |
| net_price_q5 | BT-112 | numeric | NULLABLE | true | false | Unified Net Price for family income band 5 ($110K+). Routed via control. |
| npt41_pub_raw, npt42_pub_raw, npt43_pub_raw, npt44_pub_raw, npt45_pub_raw | BT-112 | numeric | NULLABLE | false | false | Raw public-population quintile net prices. Carried through for provenance. Source: `npt41_pub` … `npt45_pub`. |
| npt41_priv_raw, npt42_priv_raw, npt43_priv_raw, npt44_priv_raw, npt45_priv_raw | BT-112 | numeric | NULLABLE | false | false | Raw private-population quintile net prices. Carried through for provenance. Source: `npt41_priv` … `npt45_priv`. |

### Tuition Structure

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| tuition_in_state | BT-110 | numeric | NULLABLE | false | false | In-state tuition and fees (tuition component only -- excludes books, housing, living expenses). Source: `tuitionfee_in`. For display/receipts. |
| tuition_out_of_state | BT-110 | numeric | NULLABLE | false | false | Out-of-state tuition and fees (tuition component only). Source: `tuitionfee_out`. For display/receipts. |

### Living Cost Estimate

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| room_board_on_campus | BT-110 | numeric | NULLABLE | false | false | On-campus room and board estimate. Source: `roomboard_on`. |
| room_board_off_campus | BT-110 | numeric | NULLABLE | false | false | Off-campus room and board estimate (not with family). Source: `roomboard_off`. |
| books_supplies | BT-110 | numeric | NULLABLE | false | false | Books and supplies cost estimate. Source: `booksupply`. |

### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the raw zone. Represents data fetch date, not measurement date. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. Generated at transformation time. Used for pipeline auditing and data freshness tracking. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 34 | Total attributes |
| 1 | Natural key component (unitid) |
| 1 | Surrogate key (record_id) |
| 9 | CDE attributes (unitid, cost_of_attendance_annual, cost_of_attendance_4yr, net_price_annual, net_price_4yr, net_price_q1–q5) |
| 0 | PII attributes |
| 27 | Nullable attributes (all cost/price measures and raw pass-throughs) |
| 7 | NOT NULL attributes (record_id, unitid, institution_name, state_abbr, institution_control, source_load_date, ingested_at) |
| 9 | Derived attributes (record_id, institution_control label, cost_of_attendance_annual, cost_of_attendance_4yr, net_price_annual, net_price_4yr, net_price_q1, net_price_q2, net_price_q3, net_price_q4, net_price_q5 = 11 derivations) |
| 12 | Raw pass-through attributes (2 COA raw + 2 avg NP raw + 10 quintile raw) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model maps these to DuckDB/Iceberg types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR (surrogate/normalized) or BIGINT (raw IPEDS ID) |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A monetary measure. May be aggregated. | DOUBLE |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | `compute_grain_id(row, ['unitid'], prefix='csi')` | unitid |
| institution_control | Map integer control: 1→'Public', 2→'Private nonprofit', 3→'Private for-profit' | raw `control` |
| cost_of_attendance_annual | `COALESCE(costt4_a, costt4_p)` | costt4_a, costt4_p |
| cost_of_attendance_4yr | `cost_of_attendance_annual × 4` (null-preserving) | cost_of_attendance_annual |
| net_price_annual | `CASE WHEN control=1 THEN npt4_pub WHEN control IN (2,3) THEN npt4_priv END` | control, npt4_pub, npt4_priv |
| net_price_4yr | `net_price_annual × 4` (null-preserving) | net_price_annual |
| net_price_q1 | `CASE WHEN control=1 THEN npt41_pub WHEN control IN (2,3) THEN npt41_priv END` | control, npt41_pub, npt41_priv |
| net_price_q2 | `CASE WHEN control=1 THEN npt42_pub WHEN control IN (2,3) THEN npt42_priv END` | control, npt42_pub, npt42_priv |
| net_price_q3 | `CASE WHEN control=1 THEN npt43_pub WHEN control IN (2,3) THEN npt43_priv END` | control, npt43_pub, npt43_priv |
| net_price_q4 | `CASE WHEN control=1 THEN npt44_pub WHEN control IN (2,3) THEN npt44_priv END` | control, npt44_pub, npt44_priv |
| net_price_q5 | `CASE WHEN control=1 THEN npt45_pub WHEN control IN (2,3) THEN npt45_priv END` | control, npt45_pub, npt45_priv |
| ingested_at | `CURRENT_TIMESTAMP` at transformation time | -- |
| source_load_date | Cast from raw `load_date` | load_date |

---

## Constraints

### Key Constraints
- **PK:** `record_id` -- unique, NOT NULL.
- **NK:** `unitid` -- unique, NOT NULL. Duplicate UNITID fails the load.

### Domain Constraints
- `institution_control ∈ {'Public', 'Private nonprofit', 'Private for-profit'}`
- `unitid` must be positive (IPEDS IDs are always > 0).
- `state_abbr` must match `^[A-Z]{2}$` (2-letter USPS format).

### Range Constraints (where non-null)
- `cost_of_attendance_annual ∈ [5,000, 100,000]` — P0 DQ rule.
- `net_price_annual ∈ [0, 80,000]` — P0 DQ rule. Public institutions cap closer to 60K empirically; private can run higher.
- `net_price_q1 … net_price_q5 ∈ [0, 80,000]` — P1 DQ rule.
- `tuition_in_state ∈ [0, 65,000]` — P1 DQ rule.
- `room_board_on_campus ∈ [3,000, 25,000]` — P1 DQ rule.

### Cross-Field Tolerance Rules
- **NP ≤ COA:** `net_price_annual ≤ cost_of_attendance_annual` where both non-null (P0). Net price cannot exceed sticker price.
- **4yr math:** `net_price_4yr = net_price_annual × 4` within $1 tolerance (P0).
- **4yr math:** `cost_of_attendance_4yr = cost_of_attendance_annual × 4` within $1 tolerance (P0).
- **Quintile monotonicity:** `net_price_q1 ≤ net_price_q5` where both non-null (P1). Lower-income families should receive more aid, resulting in lower net price.
- **Population coverage:** ≥90% of rows have `cost_of_attendance_annual` non-null (P0). ≥85% have `net_price_annual` non-null (P0).

---

## Nullability Semantics

Null values carry specific business meaning:

| Pattern | Business Meaning |
|---------|-----------------|
| `cost_of_attendance_annual IS NULL` | Institution did not report either `costt4_a` or `costt4_p` in this cycle. |
| `net_price_annual IS NULL` | Institution did not report a net price to its own control population (e.g., a public school with null `npt4_pub`). Usually reflects IPEDS reporting gaps rather than privacy suppression. |
| `net_price_q{n} IS NULL` | No data reported for that specific income band in the institution's control population. Individual bands suppress independently. |
| `tuition_in_state IS NULL` vs `tuition_out_of_state IS NULL` | Some institutions (especially private) have equal in-state and out-of-state tuition; still, each field is independently nullable. |
| `room_board_on_campus IS NULL` | Institution does not offer on-campus housing or did not report the estimate. |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attributes | Notes |
|-------------------|--------------------|-------|
| Institution | record_id, unitid, institution_name | Grain anchor. unitid is the natural key. |
| Institution Location | state_abbr | 2-letter USPS code. Required, never null. |
| Control Type | institution_control | Derived from raw `control` integer. Drives pub/priv routing. |
| Cost of Attendance | cost_of_attendance_annual, cost_of_attendance_4yr, costt4_a_raw, costt4_p_raw | Unified annual + 4yr derivation + 2 raw pass-through. |
| Net Price | net_price_annual, net_price_4yr, npt4_pub_raw, npt4_priv_raw | Unified annual + 4yr derivation + 2 raw pass-through. |
| Income Band Net Price | net_price_q1–q5 + 10 raw pub/priv pass-through | 5 unified bands + 10 raw provenance fields. |
| Tuition Structure | tuition_in_state, tuition_out_of_state | Display/receipt fields. |
| Living Cost Estimate | room_board_on_campus, room_board_off_campus, books_supplies | Display/receipt fields. |
| (Pipeline Metadata) | source_load_date, ingested_at | Not a conceptual entity — pipeline infrastructure. |

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | `institution_control` has no dedicated business term | Logical model uses `*pending*` placeholder. Physical model will inherit. | @data-steward should propose a new "Institution Control Type" term (suggested next available BT-ID). Non-blocking for approval of logical model draft. |
| 2 | Raw pub/priv pass-through fields multiply attribute count | 34 attributes total — wider than typical Silver Base. | Accepted per governance reviewer finding. Provenance and auditability outweigh minor schema bloat; rows are ~6,500 so storage impact is negligible. |
