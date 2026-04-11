# Entity Resolution Decision: gold-regional-price-parities

**Spec:** `docs/specs/gold-regional-price-parities.md`
**Target Table:** `brightsmith.consumable.regional_price_parities` (Gold)
**Silver Parent Decision:** `governance/entity-resolution/silver-base-bea-rpp.md` (SKIP, carried forward from Bronze)
**Bronze Parent Decision:** `governance/entity-resolution/raw-ingest-bea-rpp.md` (SKIP)
**Agent:** @entity-resolver
**Date:** 2026-04-11
**Decision:** SKIP CONFIRMED (carry-forward chain Bronze -> Silver -> Gold) — no entity resolution work required
**Entity Type:** U.S. state (including District of Columbia)
**Resolution Strategy:** ID-based resolution against the canonical ANSI/FIPS state code (`state_fips`) — inherited unchanged from Silver

---

## Summary

`consumable.regional_price_parities` is a pure row-for-row promotion of `base.bea_rpp` with four new **pure derivations** and one explicit carry-forward. It introduces no new identifier, no new alias surface, no new cross-source join, and no entity-lifecycle event model. The canonical state identity (`state_fips`) is promoted verbatim from Silver, which itself promoted it verbatim from Bronze (`geo_fips`).

Because the Gold layer adds no new identity surface, the entity-resolution posture is inherited unchanged from Silver: **skip**. `state_fips` remains a fully resolved canonical primary key with resolution confidence 1.0 across all 51 rows. This decision is the Gold-zone restatement of `governance/entity-resolution/silver-base-bea-rpp.md`.

---

## What Changed From Silver

| Concern | Silver (`base.bea_rpp`) | Gold (`consumable.regional_price_parities`) | ER impact |
|---|---|---|---|
| Canonical state ID | `state_fips` | `state_fips` (verbatim passthrough) | None — 1:1 passthrough |
| Canonical state name | `state_name` | `state_name` (verbatim passthrough) | None — 1:1 passthrough |
| USPS abbreviation | `state_abbr` | `state_abbr` (verbatim passthrough) | None — 1:1 passthrough |
| Census region | `census_region` | `census_region` (verbatim passthrough) | None — 1:1 passthrough |
| RPP index | `rpp_all_items` | `rpp_all_items` (verbatim passthrough) | Not an identifier |
| Purchasing power multiplier | `purchasing_power_multiplier` | `purchasing_power_multiplier` (verbatim passthrough) | Not an identifier |
| Verification provenance | `verification_status` | `verification_status` (explicit carry-forward per Bronze Condition 7) | Not an identifier |
| Data vintage | `data_year` | `data_year` (verbatim passthrough) | Not an identifier |
| **NEW** Cost tier | — | `cost_tier` (CASE on `rpp_all_items`) | Pure derivation, functional dependent of rpp |
| **NEW** Adjusted 30k | — | `adjusted_30k` (`30000 * purchasing_power_multiplier`) | Pure derivation, functional dependent of multiplier |
| **NEW** Adjusted 50k | — | `adjusted_50k` (`50000 * purchasing_power_multiplier`) | Pure derivation, functional dependent of multiplier |
| **NEW** Adjusted 75k | — | `adjusted_75k` (`75000 * purchasing_power_multiplier`) | Pure derivation, functional dependent of multiplier |
| **NEW** Adjusted 100k | — | `adjusted_100k` (`100000 * purchasing_power_multiplier`) | Pure derivation, functional dependent of multiplier |
| Grain surrogate | (none) | `record_id = compute_grain_id(row, ['state_fips'], prefix='rpc')` | Deterministic surrogate of `state_fips`; not a new identity |
| Promote timestamp | `ingested_at` / `source_load_date` | `promoted_at` | Housekeeping column, not an identifier |
| Cross-source joins | none | none | No new ER surface |
| Entity lifecycle events | none | none | None |

### Why the four new columns are NOT entity-resolution concerns

- `cost_tier` is a 5-bucket enum that is a **strict function** of `rpp_all_items` via the spec's CASE expression. It categorizes an attribute of the already-resolved entity; it does not identify anything.
- `adjusted_30k / 50k / 75k / 100k` are **pure arithmetic** on `purchasing_power_multiplier`, a numeric attribute of the entity. They are per-row derivations that cannot introduce ambiguity, alias collisions, or new entities.
- `record_id` is a deterministic surrogate computed from `state_fips` alone (`prefix='rpc'`). It is a restatement of the canonical identifier in a namespace-safe form, not a new identity. Its bijection with `state_fips` is guaranteed by construction.
- `promoted_at` is a pipeline housekeeping column and has no identity semantics.

None of these derivations open a new identity surface, introduce aliasing, or create lifecycle events. All four are functional dependents of columns that are themselves already resolved.

---

## Evidence — Live Gold Table Verification

Queried directly against the Gold Iceberg parquet at `data/gold/iceberg_warehouse/consumable/regional_price_parities/data/00000-0-07edfd60-dda9-4d71-936a-0ea5bdb54bb6.parquet` (catalog `brightsmith`, namespace `consumable`, table `regional_price_parities`).

### Row count, shape, and cardinality

| Metric | Value | Expected | Result |
|---|---|---|---|
| Row count | **51** | 51 | pass |
| Column count | **15** | 15 | pass |
| Distinct `state_fips` | **51** | 51 | pass |
| Distinct `state_name` | **51** | 51 | pass |
| Distinct `state_abbr` | **51** | 51 | pass |
| Distinct `data_year` | **1** | 1 | pass |

### Bijection 1 — `state_fips` <-> `state_name` (Gold)

| Direction | Max distinct values per key | Result |
|---|---|---|
| `state_fips -> state_name` | **1** | strict function |
| `state_name -> state_fips` | **1** | strict function |

Bijection **confirmed** on the Gold table. Matches the Silver bijection verbatim.

### Bijection 2 — `state_fips` <-> `state_abbr` (Gold)

| Direction | Max distinct values per key | Result |
|---|---|---|
| `state_fips -> state_abbr` | **1** | strict function |
| `state_abbr -> state_fips` | **1** | strict function |

Bijection **confirmed** on the Gold table. Matches the Silver bijection verbatim.

### Functional dependency — `state_fips -> cost_tier`

Because `cost_tier` is a deterministic CASE expression on `rpp_all_items`, and `rpp_all_items` is a function of `state_fips` (passthrough from Silver, which is a function of state_fips), `cost_tier` is necessarily a function of `state_fips`. No cardinality check is required for ER purposes — this is a derivation, not an identifier.

Observed `cost_tier` distribution on the live 51-row Gold table:

| cost_tier | State count |
|---|---|
| very_high | 4 |
| high | 8 |
| average | 13 |
| low | 11 |
| very_low | 15 |
| **Total** | **51** |

All 5 tiers materialize (the spec's P1 soft rule of "at least 3 distinct tiers" is met, and the stronger informal expectation of all 5 is also met).

### Verification status carry-forward

| Bucket | Count | Expected | Result |
|---|---|---|---|
| `bea_official` | **8** | 8 | pass |
| `estimate` | **43** | 43 | pass |

Carry-forward from Silver/Bronze is intact. The 8 `bea_official` rows are the BEA-verified canonical set. This is provenance, not identity — but the count being exactly 8 on the Gold table confirms no row loss and no row duplication through the promotion, which in turn confirms that the canonical identity set was preserved 1:1.

### No new identifier columns

A column-by-column walk of the Gold schema confirms that every identifier-class column (`state_fips`, `state_name`, `state_abbr`, `census_region`) is a verbatim passthrough from Silver. The only column that could conceivably look like a new identifier — `record_id` — is a deterministic surrogate computed from `state_fips` alone, so it cannot carry any identity information that `state_fips` does not already carry. Verified: `record_id` cardinality = 51, matching `state_fips` cardinality.

---

## Resolution Strategy (Gold)

**Inherited from Silver, unchanged.** ID-based resolution against ANSI/FIPS state codes.

- Primary identifier: `state_fips` (2-digit zero-padded string, e.g., `"06"` = California)
- Secondary identifiers available for cross-checks: `state_name`, `state_abbr`
- Resolution confidence: **1.0** for all 51 rows (exact ID match, inherited transitively from Bronze)
- Resolution method: canonical ID is emitted by the source in its native form and promoted verbatim through Silver and Gold; no normalization, no fuzzy matching
- Flagged-for-review count: **0**
- Lifecycle events: **none** (US states + DC set has been stable since 1959)
- No entries added to `governance/entity-registry.json` — the Gold table is itself the authoritative state registry for FutureProof; any consumer needing a FIPS-keyed reference can join directly to `consumable.regional_price_parities`

---

## Scope Boundaries Observed

- `cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k` are Gold-zone derivations owned by @primary-agent / @semantic-modeler, not entity-resolution work.
- `verification_status` is a provenance label carried forward unchanged from a hard-coded 8-state allow-list at Bronze; it is not an identifier and does not participate in resolution.
- `record_id` is a deterministic grain surrogate, not a new identity — verification of its bijection with `state_fips` is a @dq-rule-writer / @dq-engineer concern, not @entity-resolver.
- No cross-source join is performed in this Gold table. The Gold BEA RPP table joins at query time by state (in MCP tools, in the frontend), not in the Gold pipeline itself — so there is no Gold-zone ER surface with College Scorecard, BLS, O*NET, or any other source.
- Any MCP-layer state-input resolution (accepting user input as abbreviation / full name / FIPS code and resolving to `state_fips`) is an MCP-layer concern, not a Gold-pipeline ER concern. It is called out as a forward-looking obligation for the `mcp-bea-rpp` spec.

---

## Conclusion

**Skip confirmed, carried forward from Silver (which carried forward from Bronze).** The Gold table `consumable.regional_price_parities` preserves the canonical FIPS identity of Silver verbatim, adds only four pure arithmetic / CASE derivations that are functional dependents of already-resolved columns, and performs no cross-source joins. All required bijection invariants — `state_fips` <-> `state_name` and `state_fips` <-> `state_abbr` — are verified on the live 51-row Gold table. No entity-resolution work is required for this spec and no updates to `governance/entity-registry.json` are required.

The Bronze -> Silver -> Gold carry-forward chain for state FIPS is now fully documented end-to-end.
