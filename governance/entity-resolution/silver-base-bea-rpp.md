# Entity Resolution Decision: silver-base-bea-rpp

**Spec:** `docs/specs/silver-base-bea-rpp.md`
**Source Table:** `brightsmith.base.bea_rpp` (Silver)
**Parent Decision:** `governance/entity-resolution/raw-ingest-bea-rpp.md` (Bronze — SKIP)
**Agent:** @entity-resolver
**Date:** 2026-04-10
**Decision:** SKIP CONFIRMED (carry forward from Bronze) — no entity resolution work required
**Entity Type:** U.S. state (including District of Columbia)
**Resolution Strategy:** ID-based resolution against the canonical ANSI/FIPS state code (`state_fips`)

---

## Summary

`base.bea_rpp` is a pure Silver projection of `bronze.bea_rpp`. It carries the Bronze identifier forward unchanged (`geo_fips → state_fips`) and adds two static structural derivations (`state_abbr`, `census_region`) from fixed lookup tables keyed on `state_fips`. No cross-source joins occur in this Silver table; Gold and MCP are the consumers that join by state at query time, not in the Silver transform.

Because the canonical identity is inherited verbatim from Bronze and the Silver additions are structural lookups (not identity reconciliation), the entity-resolution posture is identical to Bronze: **skip**. `state_fips` is treated as a fully resolved canonical primary key.

This decision is the Silver-zone restatement of `governance/entity-resolution/raw-ingest-bea-rpp.md`. It additionally verifies the three bijection invariants required by the Silver spec's P1 DQ rules against the live Silver table.

---

## What Changed From Bronze

| Concern | Bronze (`bronze.bea_rpp`) | Silver (`base.bea_rpp`) | ER impact |
|---|---|---|---|
| Canonical state ID | `geo_fips` (2-digit FIPS) | `state_fips` (renamed, same values) | None — 1:1 passthrough |
| Canonical state name | `geo_name` | `state_name` (renamed, same values) | None — 1:1 passthrough |
| USPS abbreviation | not present | `state_abbr` (static FIPS → USPS lookup, in-code) | Derivation, not resolution |
| Census region | not present | `census_region` (static FIPS → region lookup, in-code) | Derivation, not resolution |
| Cross-source joins | none | none | No new ER surface |
| Entity lifecycle events | none (stable US states + DC) | none | None |

Silver introduces no new identifier, no new alias surface, and no new cross-source join. The two derived columns (`state_abbr`, `census_region`) are **functional dependents** of `state_fips` read from fixed structural lookups; they do not create resolution obligations.

---

## Evidence — Live Silver Table Verification

Queried directly against the Silver Iceberg parquet at `data/silver/iceberg_warehouse/base/bea_rpp/data/*.parquet` (catalog `brightsmith`, namespace `base`, table `bea_rpp`).

### Row count and cardinality

| Metric | Value |
|---|---|
| Row count | **51** |
| Distinct `state_fips` | **51** |
| Distinct `state_name` | **51** |
| Distinct `state_abbr` | **51** |

### Bijection 1 — `state_fips` ↔ `state_name`

| Direction | Max distinct values per key | Result |
|---|---|---|
| `state_fips → state_name` | **1** | strict function |
| `state_name → state_fips` | **1** | strict function |

Bijection **confirmed**. Satisfies Silver DQ P1 rule "state_fips bijection with state_name."

### Bijection 2 — `state_fips` ↔ `state_abbr`

| Direction | Max distinct values per key | Result |
|---|---|---|
| `state_fips → state_abbr` | **1** | strict function |
| `state_abbr → state_fips` | **1** | strict function |

Bijection **confirmed**. Satisfies Silver DQ P1 rule "state_fips bijection with state_abbr."

### Functional dependency 3 — `state_fips → census_region`

| Check | Result |
|---|---|
| Max distinct `census_region` per `state_fips` | **1** |

Every `state_fips` maps to exactly **one** `census_region`. The reverse is (correctly) not a function because regions group multiple states.

Census region distribution across the 51 rows:

| Census region | State count |
|---|---|
| Northeast | 9 |
| Midwest | 12 |
| South | 17 |
| West | 13 |
| **Total** | **51** |

All four Census regions are represented, and DC (FIPS `11`) is placed in `South` per Census Bureau convention — the documented quirk called out in the Silver spec is honored.

### BEA-verified spot check (all 8 rows)

All 8 BEA-verified states in the spec's spot-check table match exactly on `(state_fips, state_name, state_abbr, census_region, rpp_all_items, verification_status)`:

| state_fips | state_name | state_abbr | census_region | rpp_all_items | verification_status |
|---|---|---|---|---|---|
| 05 | Arkansas | AR | South | 86.9 | bea_official |
| 06 | California | CA | West | 110.7 | bea_official |
| 11 | District of Columbia | DC | South | 109.9 | bea_official |
| 15 | Hawaii | HI | West | 110.0 | bea_official |
| 19 | Iowa | IA | Midwest | 87.8 | bea_official |
| 28 | Mississippi | MS | South | 87.0 | bea_official |
| 34 | New Jersey | NJ | Northeast | 108.8 | bea_official |
| 40 | Oklahoma | OK | South | 87.8 | bea_official |

Identity is stable from Bronze through Silver for every row in the verified set, and the derived columns align with the spec.

---

## Resolution Strategy (Silver)

**Inherited from Bronze, unchanged.** ID-based resolution against ANSI/FIPS state codes.

- Primary identifier: `state_fips` (2-digit zero-padded string, e.g., `"06"` = California)
- Secondary identifiers available for cross-checks: `state_name`, `state_abbr`
- Resolution confidence: **1.0** for all 51 rows (exact ID match, inherited from Bronze)
- Resolution method: canonical ID is emitted by the source in its native form; Silver renames only
- Flagged-for-review count: **0**
- Lifecycle events: **none** (US states + DC set has been stable since 1959)
- No entries added to `governance/entity-registry.json` — the Silver table is itself the authoritative state registry for this pipeline

---

## Scope Boundaries Observed

- `state_abbr` and `census_region` are static structural lookups on `state_fips`, not entity-resolution work. They belong to @semantic-modeler / @primary-agent.
- `purchasing_power_multiplier` is a numeric derivation (`100.0 / rpp_all_items`), not an identifier.
- `verification_status` is a provenance label derived from a hard-coded 8-state allow-list; it is not an identifier and does not participate in resolution.
- No cross-source join is performed in this Silver table, so there is no Silver-zone ER surface with College Scorecard, BLS, O*NET, or any other source.

---

## Conclusion

**Skip confirmed, carried forward from Bronze.** The Silver table `base.bea_rpp` preserves the canonical FIPS identity of Bronze verbatim, adds only functional derivations of `state_fips`, and performs no cross-source joins. All three required invariants — `state_fips` ↔ `state_name` bijection, `state_fips` ↔ `state_abbr` bijection, and `state_fips → census_region` functional dependency — are verified on the live 51-row Silver table. No entity-resolution work is required for this spec.
