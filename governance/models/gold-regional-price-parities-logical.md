# Logical Model: gold-regional-price-parities

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Domain:** Regional Economic Reference / Cost of Living Adjustment
**Spec:** docs/specs/gold-regional-price-parities.md
**Conceptual Model:** governance/models/gold-regional-price-parities-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-11
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)
**Source Model:** governance/models/silver-base-bea-rpp-logical.md

---

```mermaid
erDiagram
    REGIONAL_PRICE_PARITIES {
        identifier record_id PK
        identifier state_fips NK
        text state_name
        identifier state_abbr
        text census_region
        numeric rpp_all_items
        numeric purchasing_power_multiplier
        text cost_tier
        numeric adjusted_30k
        numeric adjusted_50k
        numeric adjusted_75k
        numeric adjusted_100k
        text verification_status
        numeric data_year
        timestamp promoted_at
    }
```

---

## Design Rationale: Single Denormalized Consumable Table

The conceptual model identifies eight entities (State Cost-of-Living Reference, State Identity, Census Region, RPP Measurement, Cost Tier, Adjusted Salary, Verification Status, Reference Vintage). Per the Gold Consumable zone pattern, all eight are flattened into a single denormalized `consumable.regional_price_parities` table with 15 columns. This is appropriate because:

1. Every conceptual relationship is 1:1 per row — the grain is one state and every attribute resolves to exactly one value.
2. Cost Tier is a deterministic function of `rpp_all_items`; a lookup table would add a join with no analytic value. The CASE expression is frozen in this model and implemented inline.
3. Adjusted Salary is a measure group of four bound evaluations (`adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`). It is flattened to four sibling columns rather than a struct or map; the rationale is recorded below and in the physical model.
4. Silver is already a single denormalized table and Gold is a pure shaping layer on top of it. Row-for-row promote with 4 derived columns + 1 carry-forward.
5. Gold Consumable tables are designed as wide, display-ready tables for direct frontend and MCP consumption. Query latency, not storage, is the optimization target.

No side tables. No reference catalogs materialized in Gold. No additional in-code lookup constants beyond what Silver already carries — all FIPS/USPS/region/verification lookups happen once in Silver and are passed through.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per U.S. state (or DC) for a single RPP vintage |
| **Natural key fields** | `state_fips` (2-digit zero-padded FIPS code) |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['state_fips'], prefix='rpc')`) |
| **Surrogate key prefix** | `rpc` (Gold Regional Price parities Consumable) — distinct from Silver's `rpp` prefix to keep hash namespaces separate across zones |
| **Dedup grain** | `['state_fips']` |
| **Uniqueness constraint** | Zero duplicates on `state_fips`. Zero duplicates on `record_id`. Zero duplicates on `state_abbr`. Zero duplicates on `state_name`. |
| **Expected cardinality** | Exactly 51 rows (50 states + DC). Closed set — no growth path. |
| **Promote pattern** | `promote(df, table='consumable.regional_price_parities', schema=SCHEMA, dedup_on=['state_fips'])` — full-table replace, idempotent |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The column ordering here exactly matches the spec and the physical model.

### 1. Surrogate Key (anchor of State Cost-of-Living Reference)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key via `compute_grain_id(row, ['state_fips'], prefix='rpc')`. Format: `rpc-<16 hex chars>`. Stable across pipeline re-runs. Distinct from Silver's `rpp-` prefix by design. |

### 2. State Identity

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| state_fips | BT-100 | identifier | NOT NULL | true | false | Two-digit zero-padded FIPS code for a U.S. state or DC (e.g., `06` for California, `11` for DC). Canonical geographic key and dedup grain. Carried verbatim from Silver `base.bea_rpp.state_fips`. The 51-member set is closed. |
| state_name | BT-101 | text | NOT NULL | false | false | Full English name of the state or District of Columbia in USPS canonical form (e.g., `California`, `District of Columbia`). Carried verbatim from Silver. Used for display only; never a join key. |
| state_abbr | BT-103 | identifier | NOT NULL | true | false | Two-letter uppercase USPS postal abbreviation (e.g., `CA`, `IA`, `DC`). Carried verbatim from Silver. The primary key used by the frontend and MCP tool signatures (`get_regional_price_parity(state_abbr)`). |
| census_region | BT-104 | text | NOT NULL | false | false | U.S. Census Bureau region assignment. Carried verbatim from Silver. Values drawn from the closed four-member set `{Northeast, Midwest, South, West}`. DC is assigned to `South` by Census convention. |

### 3. RPP Measurement

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| rpp_all_items | BT-098 | numeric | NOT NULL | true | false | Regional Price Parity index for all items, on the national=100.0 scale. Carried verbatim from Silver with no rescaling. Range expected 70.0 to 130.0. Passthrough invariant: every Gold row's `rpp_all_items` must equal the Silver row for the same `state_fips`. |
| purchasing_power_multiplier | BT-099 | numeric | NOT NULL | true | false | Pre-computed salary scaling factor equal to `100.0 / rpp_all_items`. Carried verbatim from Silver (not recomputed at Gold). Expected range 0.7 to 1.3. Inverse invariant: `purchasing_power_multiplier × rpp_all_items ≈ 100.0` within tolerance 0.01. Single source of truth for salary adjustment across the pipeline. |

### 4. Cost Tier (derived at Gold)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| cost_tier | BT-106 | text | NOT NULL | false | false | Five-bucket editorial classification of state cost of living drawn from the closed set `{very_high, high, average, low, very_low}`. Derived at Gold from `rpp_all_items` via fixed left-closed breakpoints at 108, 103, 97, 91 (see Derivation Rules). Frozen in this model — any breakpoint change is a breaking change to downstream consumers. |

### 5. Adjusted Salary Measure Group (derived at Gold)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| adjusted_30k | BT-107 | numeric | NOT NULL | true | false | Pre-computed adjusted salary at the $30K national benchmark. Formula: `round(30000.0 × purchasing_power_multiplier, 2)`. USD, cents precision. CDE because it is a direct derivation from `purchasing_power_multiplier`. |
| adjusted_50k | BT-107 | numeric | NOT NULL | true | false | Pre-computed adjusted salary at the $50K national benchmark. Formula: `round(50000.0 × purchasing_power_multiplier, 2)`. USD, cents precision. |
| adjusted_75k | BT-107 | numeric | NOT NULL | true | false | Pre-computed adjusted salary at the $75K national benchmark. Formula: `round(75000.0 × purchasing_power_multiplier, 2)`. USD, cents precision. |
| adjusted_100k | BT-107 | numeric | NOT NULL | true | false | Pre-computed adjusted salary at the $100K national benchmark. Formula: `round(100000.0 × purchasing_power_multiplier, 2)`. USD, cents precision. |

### 6. Verification Status (carry-forward from Silver)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| verification_status | BT-105 | text | NOT NULL | false | false | Per-row provenance qualifier drawn from the closed set `{bea_official, estimate}`. Carried verbatim from Silver per Bronze staff-review Condition 7. Current allocation: 8 rows `bea_official` (CA, HI, DC, NJ, AR, MS, IA, OK), 43 rows `estimate`. |

### 7. Reference Vintage

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| data_year | BT-102 | numeric | NOT NULL | false | false | Year of the RPP estimate. Constant `2024` in the current vintage. Carried verbatim from Silver. `COUNT(DISTINCT data_year) = 1` is a P0 invariant. |

### 8. Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| promoted_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Gold consumable table. Generated at transformation time via `datetime.now()`. Replaces Silver's `ingested_at`/`source_load_date` metadata pair — Gold tables carry a single promote timestamp, not a full ingest chain. |

---

## Column Ordering (15 columns, confirmed)

The column order in this logical model exactly matches the spec's 15-column list and will be preserved byte-for-byte by the physical model and the `promote()` call:

| # | Column | Group | Source |
|---|--------|-------|--------|
| 1 | record_id | Surrogate Key | Derived at Gold (`rpc` prefix) |
| 2 | state_fips | State Identity | Passthrough from Silver |
| 3 | state_name | State Identity | Passthrough from Silver |
| 4 | state_abbr | State Identity | Passthrough from Silver |
| 5 | census_region | State Identity | Passthrough from Silver |
| 6 | rpp_all_items | RPP Measurement | Passthrough from Silver |
| 7 | purchasing_power_multiplier | RPP Measurement | Passthrough from Silver |
| 8 | cost_tier | Cost Tier | Derived at Gold (CASE expression) |
| 9 | adjusted_30k | Adjusted Salary | Derived at Gold |
| 10 | adjusted_50k | Adjusted Salary | Derived at Gold |
| 11 | adjusted_75k | Adjusted Salary | Derived at Gold |
| 12 | adjusted_100k | Adjusted Salary | Derived at Gold |
| 13 | verification_status | Verification Status | Carry-forward from Silver (Condition 7) |
| 14 | data_year | Reference Vintage | Passthrough from Silver |
| 15 | promoted_at | Pipeline Metadata | Generated at Gold |

**Logical grouping rationale.** Identity (1-5) → measurement (6-7) → derivations (8-12) → provenance (13) → vintage (14) → metadata (15). Derivations are grouped together (`cost_tier` followed by the four `adjusted_Nk`), so a reader scanning left-to-right sees the raw RPP, then everything it powers, then the provenance flag that qualifies it. `verification_status` sits after the derivations so a consumer deciding whether to trust a row sees all the values first, then the qualifier, then the vintage.

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 15 | Total attributes |
| 1 | Natural key components (state_fips) |
| 1 | Surrogate key (record_id) |
| 6 | CDE attributes (state_fips, state_abbr, rpp_all_items, purchasing_power_multiplier, adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k — 8 total if counting the 4 Adjusted Salary columns individually) |
| 0 | PII attributes |
| 0 | Nullable attributes |
| 15 | NOT NULL attributes |
| 6 | Derived at Gold (record_id, cost_tier, adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k) |
| 8 | Silver passthroughs (state_fips, state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, data_year) plus verification_status carry-forward = 8 total |
| 1 | Generated metadata (promoted_at) |

*(Note: "6 CDE attributes" counts Adjusted Salary as a group; expanded to individual columns the CDE count is 8.)*

---

## Type Domain Definitions

These are logical type categories, not physical implementations. The physical model maps them to Iceberg / DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. String-valued even when the content is digits (FIPS codes must be zero-padded strings). | VARCHAR |
| text | A human-readable label or display value, or a closed enum. Not used for joins. Constrained to a closed enum for `census_region`, `cost_tier`, and `verification_status`. | VARCHAR |
| numeric | A quantitative measure that participates in arithmetic (`rpp_all_items`, `purchasing_power_multiplier`, the four `adjusted_Nk`) or a calendar-year value used for filtering (`data_year`). | DOUBLE for the two RPP values and the four adjusted salary values; INTEGER for data_year |
| timestamp | A point in time used for pipeline auditing. | TIMESTAMP |

No `date` domain is required at Gold — Silver's `source_load_date` is not carried forward; Gold tracks only a single `promoted_at` timestamp.

---

## Derivation Rules

| Derived Attribute | Rule | Source Attributes | Notes |
|-------------------|------|-------------------|-------|
| record_id | `compute_grain_id(row, ['state_fips'], prefix='rpc')` | state_fips | SHA-256 truncated to 16 hex chars. Output format: `rpc-<hex>`. Prefix `rpc` (Regional Price parities Consumable). |
| cost_tier | Left-closed 5-bucket CASE on `rpp_all_items` at breakpoints 108, 103, 97, 91. See "Cost Tier Derivation" below for the exact expression. | rpp_all_items | Frozen in this model. Breakpoints inclusive on lower bound, exclusive on upper bound. |
| adjusted_30k | `round(30000.0 * purchasing_power_multiplier, 2)` | purchasing_power_multiplier | USD, cents precision. Rounding mode: banker's rounding (Python default / IEEE 754 round-half-to-even). |
| adjusted_50k | `round(50000.0 * purchasing_power_multiplier, 2)` | purchasing_power_multiplier | USD, cents precision. |
| adjusted_75k | `round(75000.0 * purchasing_power_multiplier, 2)` | purchasing_power_multiplier | USD, cents precision. |
| adjusted_100k | `round(100000.0 * purchasing_power_multiplier, 2)` | purchasing_power_multiplier | USD, cents precision. |
| promoted_at | `datetime.now()` at transformation time | -- | Generated per run. |

### Cost Tier Derivation (Frozen)

```sql
cost_tier = CASE
  WHEN rpp_all_items >= 108.0 THEN 'very_high'
  WHEN rpp_all_items >= 103.0 THEN 'high'
  WHEN rpp_all_items >= 97.0  THEN 'average'
  WHEN rpp_all_items >= 91.0  THEN 'low'
  ELSE                             'very_low'
END
```

Breakpoints are inclusive on the lower bound, exclusive on the upper bound. The CASE is evaluated top-down so the highest-matching bucket wins.

**Coverage spot-check (8 BEA-verified states):**

| state_fips | state | rpp_all_items | cost_tier |
|---|---|---|---|
| 06 | CA | 110.7 | very_high |
| 15 | HI | 110.0 | very_high |
| 11 | DC | 109.9 | very_high |
| 34 | NJ | 108.8 | very_high |
| 05 | AR | 86.9 | very_low |
| 28 | MS | 87.0 | very_low |
| 19 | IA | 87.8 | very_low |
| 40 | OK | 87.8 | very_low |

### Cost Tier as an Enum vs. a Lookup Table

**Decision: inline CASE expression, no lookup table.** Cost Tier is modeled as a conceptual dependent entity but implemented as a single string column. A physical lookup table was considered and rejected for three reasons:

1. **The classification is a deterministic function of a single numeric column.** A lookup table keyed on a continuous range would introduce a range-join, which is more expensive and error-prone than the CASE. The five breakpoints are simpler to express in SQL than in a two-column `(tier, lower_bound)` table.
2. **The breakpoints are governance-frozen.** A lookup table invites the illusion that the breakpoints are data and could be edited by someone with write access to the table. Freezing the CASE in the model (and in the transformer code) is closer to the governance intent: breakpoint changes must go through a spec change, not a row update.
3. **Downstream consumers bind to the five literal values, not to the table.** The frontend, MCP tools, and boss-fight logic all write `if tier == 'very_high'`-style checks. A lookup table would not change their code or their contract.

If a future spec needs per-state breakpoint overrides (e.g., urban vs. rural adjustments), the right path is a separate spec, not a lookup table added here.

### Adjusted Salary: Four Columns vs. Struct/Map

**Decision: four sibling double columns (`adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`).** A `STRUCT<k30:DOUBLE, k50:DOUBLE, k75:DOUBLE, k100:DOUBLE>` and a `MAP<INTEGER, DOUBLE>` were considered and rejected.

**Why not a struct:**
- Every consumer (frontend, MCP tools, Gemma) reads scalar doubles. Struct access in DuckDB/Iceberg works but adds a `.field` access layer at every read site, making the MCP tool signature slightly clumsier (`row.adjusted_salaries.k50` vs. `row.adjusted_50k`).
- DQ rule expression is simpler with flat columns — a rule like "adjusted_50k within 1 cent of the formula" is a direct column reference; with a struct it becomes a struct-field reference that some DQ engines handle unevenly.
- The current benchmark set is closed and small (4 values). Structs pay off when you have many fields or variable-cardinality fields, neither of which applies here.
- Backwards compatibility: existing downstream code (including the MCP tool contract being developed in parallel) was designed around scalar column access. Switching to a struct now would require a coordinated change across every consumer for no consumer benefit.

**Why not a map:**
- The four benchmarks are a **closed contract**, not an arbitrary set of key-value pairs. A map semantically invites "you can add any salary you want", which is the opposite of the governance intent (the whole point of pre-computing is to prevent client-side math).
- Map key types in Iceberg are inflexible in many query engines, and range-query over integer keys is not supported the way it is over column values.
- DQ rules on map values are awkward — there is no clean way to express "the value at key 50000 must equal 50000 × multiplier" in most rule engines.

**Extension path if a fifth benchmark is added later.** Add `adjusted_150k` as column 13 (renumbering the verification/vintage/metadata columns to 14/15/16). This is a non-breaking additive schema change that existing consumers ignore. If the set ever grows to 10+ benchmarks, re-evaluate the struct/map choice — but that is a future spec's problem, not this one's.

---

## Passthrough Attributes

Silver columns that Gold carries forward verbatim with no transformation:

| Attribute | Silver Source | Transformation |
|-----------|---------------|----------------|
| state_fips | `base.bea_rpp.state_fips` | None |
| state_name | `base.bea_rpp.state_name` | None |
| state_abbr | `base.bea_rpp.state_abbr` | None |
| census_region | `base.bea_rpp.census_region` | None |
| rpp_all_items | `base.bea_rpp.rpp_all_items` | None — passthrough invariant enforced by DQ |
| purchasing_power_multiplier | `base.bea_rpp.purchasing_power_multiplier` | None — inverse invariant enforced by DQ |
| verification_status | `base.bea_rpp.verification_status` | None — Condition 7 carry-forward; COUNT(bea_official)=8 DQ rule re-asserted at Gold |
| data_year | `base.bea_rpp.data_year` | None |

Silver columns **not** carried forward:

| Silver Column | Reason Dropped |
|---------------|---------------|
| source_load_date | Gold metadata is a single `promoted_at` timestamp; the Silver ingest chain is not surfaced to consumers. |
| ingested_at | Same as above — replaced by Gold's `promoted_at`. |

---

## Nullability Semantics

All 15 attributes are NOT NULL. This is a complete, closed-set consumable reference table with no nullable optional fields. The "softness" in the data is carried entirely by `verification_status = 'estimate'` on 43 of 51 rows, which is a first-class value in a closed enum — not missing data.

Per the Gold data contract: **0% nulls on all 15 columns.**

---

## Key Constraints

| Constraint | Rationale |
|-----------|-----------|
| PRIMARY KEY (record_id) | Surrogate key uniqueness. P0 DQ rule. |
| UNIQUE (state_fips) | Natural key uniqueness. Bijection with state_name and state_abbr. P0 DQ rule. |
| UNIQUE (state_abbr) | 1:1 synonym for state_fips. |
| UNIQUE (state_name) | 1:1 synonym for state_fips. |
| CHECK (state_fips matches `^\d{2}$`) | Two-digit zero-padded format. |
| CHECK (state_abbr matches `^[A-Z]{2}$`) | Two uppercase letters. |
| CHECK (census_region IN ('Northeast','Midwest','South','West')) | Closed enum. |
| CHECK (cost_tier IN ('very_high','high','average','low','very_low')) | Closed enum. |
| CHECK (cost_tier matches CASE expression on rpp_all_items) | Derivation correctness. P0 DQ rule. |
| CHECK (verification_status IN ('bea_official','estimate')) | Closed enum. |
| CHECK (rpp_all_items BETWEEN 70.0 AND 130.0) | Observed-range sanity bound (inherited from Silver). |
| CHECK (purchasing_power_multiplier BETWEEN 0.7 AND 1.3) | Inverse-of-RPP range (inherited from Silver). |
| CHECK (abs(purchasing_power_multiplier * rpp_all_items - 100.0) <= 0.01) | Inverse invariant (inherited from Silver). |
| CHECK (abs(adjusted_Nk - round(N*1000*purchasing_power_multiplier, 2)) <= 0.01) | Adjusted salary derivation correctness (one rule per N). P0. |
| CHECK (data_year = 2024) | Single-vintage invariant. |
| Row count = 51 | Closed set: 50 states + DC. |
| COUNT(*) WHERE verification_status='bea_official' = 8 | Condition 7 carry-forward. |
| Passthrough: every Gold rpp_all_items equals Silver rpp_all_items for the same state_fips | Referential integrity to Silver. Production-only evaluation mode. |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attributes | Notes |
|-------------------|--------------------|-------|
| State Cost-of-Living Reference | record_id | Anchor surrogate key. |
| State Identity | state_fips, state_name, state_abbr, census_region | Identity group. census_region is an attribute of the state in this flattening, not a separate entity, matching Silver. |
| Census Region | (flattened into State Identity as census_region) | No separate table; inherits Silver's treatment. |
| RPP Measurement | rpp_all_items, purchasing_power_multiplier | Raw measurement + Silver-computed derivation. |
| Cost Tier | cost_tier | Single-column flattening of the dependent enum entity. Derived at Gold via CASE. |
| Adjusted Salary | adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k | Four-column flattening of the dependent measure group. Derived at Gold. |
| Verification Status | verification_status | Single attribute; Condition 7 carry-forward. |
| Reference Vintage | data_year | Single-column flattening. |
| (Pipeline Metadata — not conceptual) | promoted_at | Infrastructure column. |

---

## Cross-Source Integration

None. This table is orthogonal to the SOC/CIP join graph. Join keys are consumed downstream at query time:

| Attribute | Integration Role |
|-----------|-----------------|
| state_fips | Direct lookup key for any consumer that already uses FIPS internally. |
| state_abbr | Primary key for MCP tool signatures and frontend state selection. |
| purchasing_power_multiplier | Source of truth for salary adjustment across every downstream consumer. |
| adjusted_30k / 50k / 75k / 100k | Display-ready values; consumers read these directly rather than computing anything client-side. |
| cost_tier | Classification key for frontend color coding, boss-fight difficulty, and narrative prompts. |
| verification_status | Provenance flag carried forward to MCP and frontend per Condition 7. |

---

## Modeling Decisions

1. **Single denormalized table, 15 columns.** Matches the spec exactly and mirrors the Silver parent shape with the Gold-specific derivations added.

2. **Prefix `rpc` for Gold record_id, distinct from Silver's `rpp`.** Keeps hash namespaces separate across zones so a record_id collision between Silver and Gold is structurally impossible. The prefix also signals "consumable" vs. "base" at a glance.

3. **Dedup grain `['state_fips']`, same as Silver.** The Gold grain is identical to the Silver grain; no re-grainening happens between Silver and Gold. This is a pure shape-and-promote.

4. **Cost Tier as inline CASE, not lookup table.** See "Cost Tier as an Enum vs. a Lookup Table" above for full rationale. Summary: deterministic single-column derivation, governance-frozen breakpoints, consumers bind to literals.

5. **Adjusted Salary as four sibling columns, not struct/map.** See "Adjusted Salary: Four Columns vs. Struct/Map" above for full rationale. Summary: closed display contract, scalar consumer access, simpler DQ rules, backwards-compatible additive extension path.

6. **`purchasing_power_multiplier` carried from Silver, not recomputed at Gold.** Silver is the single source of truth; recomputing at Gold would risk formula drift and double-derivation bugs. Gold reads the Silver value as-is.

7. **`rpp_all_items` carried from Silver, not rescaled.** Same reason.

8. **All four `adjusted_Nk` rounded to 2 decimals at write time.** Cents precision. Sub-cent precision is false precision for a state-level index — this is a Silver-aligned decision propagated to Gold. Rounding mode is Python default (IEEE 754 round-half-to-even).

9. **`verification_status` carried forward intact, with the `COUNT(bea_official)=8` DQ rule re-asserted at Gold.** The Silver DQ rule is not sufficient — consumers read Gold, so Gold must independently enforce the count. The rule updates to `=51` in lockstep with Silver when the live BEA refresh lands.

10. **`promoted_at` replaces the Silver `ingested_at` + `source_load_date` pair.** Gold consumable tables expose a single promote timestamp; the full ingest chain is an infrastructure concern hidden from consumers. Lineage is tracked separately in OpenLineage, not in the consumable schema.

11. **No SCD2, no history, no versioning.** Full-table replacement on refresh. Matches Silver.

12. **No PII. CDE status inherited from Silver plus the four Adjusted Salary columns.** The Adjusted Salary values are CDEs because they are direct derivations from `purchasing_power_multiplier`, which is itself a CDE. The final CDE/PII flags live in the data contract at `governance/data-contracts/gold-regional-price-parities.yaml`; this model mirrors the contract values.

13. **Column ordering is load-bearing.** The 15-column order is specified in the spec and preserved here. The physical model and the transformer code must emit columns in this exact order.

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | Cost Tier distribution across the 51 rows may leave some tiers empty | Low — spec already notes only 4 of 5 tiers may materialize with current estimates | P1 DQ rule "at least 3 distinct tiers present" already specified. Full 5-tier coverage becomes a hard expectation only after the BEA refresh. |
| 2 | Rounding mode for `adjusted_Nk` (round-half-to-even vs. round-half-up) | Very low — differences show up only on ties at 0.5 cents; spot-check values in the spec are stable under either mode | Documented: Python default (round-half-to-even). Transformer must use Python `round()` or `numpy.round()`, both of which use banker's rounding. |
| 3 | Whether to add `adjusted_150k` or `adjusted_200k` in a future spec | None now | Non-breaking additive change. Add columns at the end of the Adjusted Salary group and renumber metadata columns. Document as a separate spec. |
