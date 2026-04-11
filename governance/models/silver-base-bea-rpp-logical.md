# Logical Model: silver-base-bea-rpp

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** Regional Economic Reference / Cost of Living Adjustment
**Spec:** docs/specs/silver-base-bea-rpp.md
**Conceptual Model:** governance/models/silver-base-bea-rpp-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-10
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    BEA_RPP {
        identifier record_id PK
        identifier state_fips NK
        text state_name
        identifier state_abbr
        text census_region
        numeric rpp_all_items
        numeric purchasing_power_multiplier
        text verification_status
        numeric data_year
        date source_load_date
        timestamp ingested_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies five entities (State, RPP Measurement, Census Region, Verification Status, Reference Vintage). Per the Silver Base zone pattern, all five are flattened into a single denormalized `base.bea_rpp` table. No reference catalogs are materialized in the Silver zone — the USPS abbreviation lookup, the FIPS-to-region lookup, and the 8-state BEA-verified allow-list all live as in-code constants.

This is appropriate because:

1. All conceptual relationships are 1:1 per row — the grain is one state and every attribute resolves to exactly one value per state.
2. The source dataset is a single flat table of 51 rows. There is no normalization benefit to splitting.
3. Silver Base tables are designed as wide, query-ready tables for downstream Gold and MCP consumption.
4. This matches the established pattern from `base.bls_ooh`, `base.college_scorecard`, and `base.karpathy_ai_exposure` (single denormalized table with conceptual entities as attribute groups).
5. The reference lookups (USPS, Census region, BEA allow-list) are structural properties of U.S. geography, not entity data owned by this pipeline. They stay in code per the project's "no hardcoded entity data" convention — these are explicit exceptions because the 51-value sets are closed, static, and not business-managed.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per U.S. state (or DC) for a single RPP vintage |
| **Natural key fields** | `state_fips` (2-digit zero-padded FIPS code) |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['state_fips'], prefix='rpp')`) |
| **Uniqueness constraint** | Zero duplicates on `state_fips`. Zero duplicates on `record_id`. Zero duplicates on `state_abbr`. Zero duplicates on `state_name`. |
| **Expected cardinality** | Exactly 51 rows (50 states + DC). Closed set — no growth path. |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from.

### State Identity

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key via `compute_grain_id(row, ['state_fips'], prefix='rpp')`. Format: `rpp-<16 hex chars>`. Stable across pipeline re-runs. |
| state_fips | BT-100 | identifier | NOT NULL | true | false | Two-digit zero-padded FIPS code for a U.S. state or DC (e.g., `06` for California, `11` for DC). Canonical geographic key. Carried from Bronze `geo_fips`. The 51-member set is closed. |
| state_name | BT-101 | text | NOT NULL | false | false | Full English name of the state or District of Columbia in USPS canonical form (e.g., `California`, `District of Columbia`). Carried from Bronze `geo_name`. Used for display only; never a join key. |
| state_abbr | BT-103 | identifier | NOT NULL | true | false | Two-letter uppercase USPS postal abbreviation (e.g., `CA`, `IA`, `DC`). Derived in Silver via a static FIPS-to-USPS lookup. The primary key used by the frontend and MCP tool signatures (`get_regional_price_parity(state_abbr)`). |
| census_region | BT-104 | text | NOT NULL | false | false | U.S. Census Bureau region assignment. Derived in Silver via a static FIPS-to-region lookup. Values drawn from the closed four-member set `{Northeast, Midwest, South, West}`. DC is assigned to `South` by Census convention (documented quirk, not a bug). |

### RPP Measurement

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| rpp_all_items | BT-098 | numeric | NOT NULL | true | false | Regional Price Parity index for all items, on the national=100.0 scale. Carried verbatim from Bronze with no rescaling. Range expected 70.0 to 130.0 inclusive. Passthrough invariant: every Silver row's `rpp_all_items` must equal the Bronze row's value for the same `state_fips`. |
| purchasing_power_multiplier | BT-099 | numeric | NOT NULL | true | false | Pre-computed salary scaling factor equal to `100.0 / rpp_all_items`. Multiplying a national salary by this value yields its local purchasing-power equivalent. Expected range 0.7 to 1.3. Inverse invariant: `purchasing_power_multiplier × rpp_all_items ≈ 100.0` within tolerance 0.01. Single source of truth for salary adjustment across the pipeline. |

### Verification Status

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| verification_status | BT-105 | text | NOT NULL | false | false | Per-row provenance qualifier drawn from the closed set `{bea_official, estimate}`. Derived in Silver from a hard-coded allow-list of the 8 BEA-verified `state_fips` codes `{'06','15','11','34','05','28','19','40'}` (CA, HI, DC, NJ, AR, MS, IA, OK). All 43 other rows are `estimate`. Closes Bronze HIGH-3 per staff-review Ruling 2 / Condition 6. When the live BEA API refresh lands, the allow-list becomes all 51 codes and every row becomes `bea_official`. |

### Reference Vintage

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| data_year | BT-102 | numeric | NOT NULL | false | false | Year of the RPP estimate. Constant `2024` in the current vintage. `COUNT(DISTINCT data_year) = 1` is a P0 invariant — the supersession strategy is full-table replacement, not SCD2. |

### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. Direct passthrough from Bronze `load_date`. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. Generated at transformation time. Used for pipeline auditing and data freshness tracking. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 11 | Total attributes |
| 1 | Natural key components (state_fips) |
| 1 | Surrogate key (record_id) |
| 4 | CDE attributes (state_fips, state_abbr, rpp_all_items, purchasing_power_multiplier) |
| 0 | PII attributes |
| 0 | Nullable attributes |
| 11 | NOT NULL attributes |
| 5 | Derived attributes (record_id, state_abbr, census_region, purchasing_power_multiplier, verification_status) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. The physical model maps them to DuckDB / Iceberg types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. String-valued even when the content is digits (FIPS codes must be zero-padded strings). | VARCHAR |
| text | A human-readable label or display value. Not used for joins. Constrained to a closed enum for `census_region` and `verification_status`. | VARCHAR |
| numeric | A quantitative measure that participates in arithmetic (rpp_all_items, purchasing_power_multiplier) or a calendar-year value used for filtering (data_year). | DOUBLE for the two RPP values; INTEGER for data_year |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time used for pipeline auditing. | TIMESTAMP |

---

## Derivation Rules

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | `compute_grain_id(row, ['state_fips'], prefix='rpp')` | state_fips |
| state_abbr | Static FIPS-to-USPS lookup. In-code constant (dict or module-level table). 51-entry closed set. | state_fips |
| census_region | Static FIPS-to-region lookup. In-code constant. Values drawn from `{Northeast, Midwest, South, West}`. DC maps to `South` per Census convention. | state_fips |
| purchasing_power_multiplier | `100.0 / rpp_all_items` | rpp_all_items |
| verification_status | `'bea_official' if state_fips in {'06','15','11','34','05','28','19','40'} else 'estimate'` | state_fips |
| data_year | Constant `2024` (or carried from Bronze if Bronze materializes it) | -- |
| source_load_date | `CAST(bronze.load_date AS DATE)` | bronze.load_date |
| ingested_at | `CURRENT_TIMESTAMP` at transformation time | -- |

---

## Passthrough Attributes

| Attribute | Source |
|-----------|--------|
| state_fips | `bronze.bea_rpp.geo_fips` (renamed) |
| state_name | `bronze.bea_rpp.geo_name` (renamed) |
| rpp_all_items | `bronze.bea_rpp.rpp_all_items` (verbatim — passthrough invariant enforced by DQ) |

---

## Nullability Semantics

All 11 attributes are NOT NULL. This is a complete reference table with no nullable optional fields. The only "softness" in the data model is the `verification_status = 'estimate'` label on 43 of 51 rows, which is a provenance qualifier, not missing data.

---

## Key Constraints

| Constraint | Rationale |
|-----------|-----------|
| PRIMARY KEY (record_id) | Surrogate key uniqueness. P0 DQ rule. |
| UNIQUE (state_fips) | Natural key uniqueness. Bijection with state_name and state_abbr. P0 DQ rule. |
| UNIQUE (state_abbr) | 1:1 synonym for state_fips. P1 DQ rule. |
| UNIQUE (state_name) | 1:1 synonym for state_fips. P1 DQ rule. |
| CHECK (state_fips matches `^\d{2}$`) | Two-digit zero-padded format. |
| CHECK (state_abbr matches `^[A-Z]{2}$`) | Two uppercase letters. |
| CHECK (census_region IN ('Northeast','Midwest','South','West')) | Closed enum. |
| CHECK (verification_status IN ('bea_official','estimate')) | Closed enum. |
| CHECK (rpp_all_items BETWEEN 70.0 AND 130.0) | Observed-range sanity bound. |
| CHECK (purchasing_power_multiplier BETWEEN 0.7 AND 1.3) | Inverse of rpp_all_items range. |
| CHECK (data_year = 2024) | Single-vintage invariant. |
| Row count = 51 | Closed set: 50 states + DC. |
| All 4 census regions represented | P0 DQ rule. |
| COUNT(*) WHERE verification_status='bea_official' = 8 | Enforces current Bronze verification state (Condition 6). |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attributes | Notes |
|-------------------|--------------------|-------|
| State | record_id, state_fips, state_name, state_abbr | Identity group. state_abbr is a derived synonym for state_fips via the static USPS lookup. |
| Census Region | census_region | Flattened into a derived attribute via the static FIPS-to-region lookup. No separate table. |
| RPP Measurement | rpp_all_items, purchasing_power_multiplier | Measurement group. Multiplier is the pre-computed derivation. |
| Verification Status | verification_status | Single attribute drawn from a closed two-value enum via the 8-state allow-list. |
| Reference Vintage | data_year | Flattened into a single column. Single-vintage invariant enforced by DQ. |
| (Pipeline Metadata) | source_load_date, ingested_at | Not a conceptual entity — pipeline infrastructure. |

---

## Cross-Source Integration

None. This table is orthogonal to the SOC/CIP join graph. Join keys are consumed downstream at query time:

| Attribute | Integration Role |
|-----------|-----------------|
| state_fips | Direct join key for Gold `consumable.regional_price_parities` |
| state_abbr | Primary key used by MCP tool signatures and frontend state selection |
| purchasing_power_multiplier | Single source of truth for salary adjustment across every downstream consumer |
| verification_status | Must be carried forward to Gold and MCP per Bronze staff-review Condition 7 |

---

## Modeling Decisions

1. **Single denormalized table.** All five conceptual entities flatten into one table. The 1:1 cardinalities make separate tables unnecessary. This matches the BLS OOH and Karpathy AI Exposure Silver patterns.

2. **state_abbr modeled as an attribute of State, not a separate entity.** The abbreviation is a synonym identifier for FIPS — a second canonical key that the frontend and MCP tools use for display and selection. It does not carry independent relationships (no attributes of its own, no reference data hanging off it), so promoting it to an entity would be structural noise. Keeping it as an attribute preserves the clean one-table shape. This is the most common design question for this spec and the answer is **attribute, not entity**.

3. **census_region as a derived attribute, not a reference table.** The four-region set is a static Census convention. Materializing it as a reference table would add a join for no analytical value. The FIPS-to-region mapping lives in code and the column is resolved at Silver build time.

4. **verification_status as a first-class column, not a side table.** Bronze staff-review Condition 6 requires per-row provenance. Putting the label inline in `base.bea_rpp` (rather than in a separate provenance table joined at query time) ensures every downstream consumer — Gold, MCP tools, frontend — sees it without extra work. The column is `NOT NULL` and drawn from a closed two-value enum.

5. **purchasing_power_multiplier pre-computed in Silver, not in Gold.** Computing the multiplier once in Silver guarantees every downstream consumer reads an identical value and never risks formula drift. This is a deliberate placement decision: the multiplier is a business-meaningful derived measure, not a transformation Gold should have to repeat.

6. **data_year modeled as numeric rather than date.** The column is a calendar-year value used for filtering and single-vintage enforcement, not a date for arithmetic. Physical type is INTEGER.

7. **No SCD2, no versioning, no history.** The supersession strategy is full-table replacement on refresh. `data_year` captures vintage but there is no history preservation. When the BEA refresh lands post-hackathon, the 2024 snapshot is replaced wholesale by a new snapshot.

8. **No PII.** Zero PII columns. State-level geographic data is not personal information.

9. **All attributes NOT NULL.** There are no optional fields in this model. The "softness" is in `verification_status = 'estimate'`, which is a per-row provenance qualifier, not missing data.

10. **In-code lookup constants for USPS, Census region, and the BEA allow-list.** These are static 51-value and 8-value sets that are structural properties of U.S. geography and of the current verification state. They do not constitute hardcoded entity data in the sense the project convention prohibits — they are closed reference mappings. If the project requires an exception notice, it should be filed at `governance/exceptions/` per the spec note.

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | In-code USPS / Census region lookups may require an exception filing | Low — static structural data, not business-managed entity data | Check `governance/exceptions/` convention; file a short exception note if required. Spec already anticipates this. |
| 2 | `data_year` typed as numeric (INTEGER) rather than DATE | None — single-value column used for filtering | Physical model will resolve as INTEGER. Documented here for transparency. |
| 3 | DC's Census region assignment is `South`, not `Northeast` | None — documented Census convention, not a data quality bug | DQ rules must not flag DC-in-South as an error. Explicit allow-list in DQ rule wording. |
