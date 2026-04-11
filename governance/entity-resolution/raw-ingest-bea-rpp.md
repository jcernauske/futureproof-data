# Entity Resolution Decision: raw-ingest-bea-rpp

**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Source Table:** `bronze.bea_rpp`
**Agent:** @entity-resolver
**Date:** 2026-04-10
**Decision:** SKIP CONFIRMED — no entity resolution work required
**Entity Type:** U.S. state (including District of Columbia)
**Resolution Strategy:** ID-based resolution against the canonical ANSI/FIPS state code (`geo_fips`)

---

## Summary

The BEA RPP source is a 51-row static reference table keyed by `geo_fips`, the 2-digit ANSI/NIST state FIPS code. State FIPS is a canonical identifier with zero ambiguity across the U.S. federal statistical system. No fuzzy matching, alias reconciliation, or lifecycle-event handling is required. `geo_fips` is treated as a **resolved canonical identifier** for downstream joins.

This decision confirms the skip recommendation already documented in `governance/domain-context.md` under the BEA RPP "Entity Types" section.

---

## Evidence

All facts below were verified against the loaded Bronze table by reading `data/bronze/iceberg_warehouse/bronze/bea_rpp/data/*.parquet` directly.

### 1. No aliasing or synonyms in `geo_name`

| Check | Result |
|-------|--------|
| Distinct `geo_name` values | **51** (100% unique) |
| `geo_name` values with punctuation (dots, commas, parens) | **0** |
| `geo_name` values with leading/trailing whitespace | **0** |
| `geo_name` values matching the canonical USPS 50-state + DC list exactly | **51/51** |
| Missing canonical names | **None** |
| Unexpected / extra names | **None** |
| DC spelling | `District of Columbia` (full, canonical — not "Washington, D.C." or "D.C.") |

No alias forms are present. There is no "Washington, D.C." variant, no "USVI"/"PR"-style territory confusion, no ALL CAPS vs. title case drift, and no whitespace hygiene issues. Every `geo_name` matches the canonical USPS state name one-for-one.

### 2. No collisions or ambiguity in `geo_fips`

| Check | Result |
|-------|--------|
| Row count | **51** (matches spec) |
| Distinct `geo_fips` values | **51** (100% unique, zero collisions) |
| `geo_fips` regex `^\d{2}$` | **51/51 match** |
| Missing canonical FIPS (50 states + DC) | **None** |
| Unexpected FIPS (territories, metros, sub-state codes) | **None** |
| Duplicate rows (`geo_fips`, `geo_name`) tuples | **0** |

All 51 expected FIPS codes are present: `01, 02, 04–06, 08–13, 15–42, 44–51, 53–56`. The documented gaps at 03, 07, 14, 43, 52 are intentional — those FIPS codes were never assigned. DC is present at FIPS `11`.

### 3. `geo_fips` ↔ `geo_name` bijection

| Check | Result |
|-------|--------|
| Max distinct `geo_name` per `geo_fips` | **1** |
| Max distinct `geo_fips` per `geo_name` | **1** |

The mapping is a strict 1:1 bijection. Either column alone is a sufficient entity identifier; we prefer `geo_fips` because it is stable against cosmetic rename events and is the identifier used by every other federal statistical product (BLS, Census, etc.) that FutureProof may join to in the future.

### 4. Lifecycle events

The set of 50 U.S. states + DC has been stable since Hawaii's admission in 1959. There are no mergers, splits, name changes, or reclassifications to model on any timescale relevant to this pipeline. **No `lifecycle_events` entries are required.**

### 5. Downstream join suitability

`geo_fips` can be treated as a **fully resolved canonical identifier** for every downstream join and derivation in this pipeline:

- Silver zone renames `geo_fips → state_fips` and derives `state_abbr` (USPS 2-letter) and `census_region` from static lookups keyed on `state_fips`. These are **derivations**, not entity-resolution tasks.
- Gold zone `consumable.regional_price_parities` uses `state_fips` as its primary key.
- MCP tools `get_regional_price_parity(state)` and `compare_purchasing_power(salary, state_a, state_b)` accept user input in any of three forms (abbreviation, full name, FIPS code) and resolve them to `state_fips` via the same static lookup.
- No cross-source pipeline join uses `state_fips` today (BEA RPP applies at query time, not pipeline time), so there is no `state_fips`-keyed entity resolution work with any other source in the FutureProof pipeline.

---

## Resolution Strategy

**ID-based resolution against ANSI/FIPS state codes.**

- Primary identifier: `geo_fips` (2-digit zero-padded string, e.g., `"06"` = California)
- Secondary identifier: `geo_name` (full canonical USPS state name)
- Resolution confidence: **1.0** (exact ID match) for all 51 rows
- Resolution method: canonical ID is emitted by the source in its native form; no normalization, no fuzzy matching
- Flagged-for-review count: **0**

Because the source already emits the canonical identifier and a bijective canonical name, the entity registry for this source is the source itself. No separate `governance/entity-registry.json` entries are required for the BEA RPP source; any future consumer needing a FIPS-keyed reference can join directly to `base.bea_rpp` / `consumable.regional_price_parities`.

---

## Scope Boundaries Observed

- Cost-of-living tier classification (`cost_tier`) is a Gold-zone derivation — not entity resolution. Handled by the semantic modeler / primary agent, not @entity-resolver.
- FIPS → USPS abbreviation and FIPS → Census region are static lookups — derivations, not resolution.
- RPP value normalization (none required; it is already on a national=100 scale) is a CDE/normalization concern — not entity resolution.

---

## Conclusion

**Skip confirmed.** State FIPS is a canonical identifier with 100% coverage, zero ambiguity, a strict 1:1 bijection with `geo_name`, and no entity-lifecycle events to model. The source emits fully resolved canonical identifiers at ingest time. Downstream zones may treat `geo_fips` / `state_fips` as an already-resolved primary key for all joins and derivations.
