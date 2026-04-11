# Audit Trail: @entity-resolver — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @entity-resolver
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Zone:** Gold (Consumable)
**Target Table:** `brightsmith.consumable.regional_price_parities`
**Decision Document:** `governance/entity-resolution/gold-regional-price-parities.md`
**Decision:** SKIP CONFIRMED — carry-forward from Silver (which carries forward from Bronze)

---

## Inputs Consulted

| Path | Purpose |
|---|---|
| `docs/specs/gold-regional-price-parities.md` | Gold spec — shape, derivations, DQ rules, carry-forward obligations |
| `governance/entity-resolution/silver-base-bea-rpp.md` | Silver ER decision — SKIP carried forward from Bronze |
| `governance/entity-resolution/raw-ingest-bea-rpp.md` | Bronze ER decision — initial SKIP on canonical FIPS |
| `data/gold/iceberg_warehouse/consumable/regional_price_parities/data/00000-0-07edfd60-dda9-4d71-936a-0ea5bdb54bb6.parquet` | Live Gold table for evidence verification |

## Procedure

1. Read the Gold spec and identified the four new columns (`cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`) plus the explicit `verification_status` carry-forward. Confirmed that the promote is row-for-row on `state_fips`.
2. Walked the 15-column Gold schema looking for any new identifier-class column. The only candidate was `record_id`, which is a deterministic surrogate of `state_fips` via `compute_grain_id(row, ['state_fips'], prefix='rpc')` — not a new identity.
3. Read both parent ER decisions to confirm the carry-forward chain and the exact resolution posture being inherited (ID-based, confidence 1.0, no lifecycle events, `state_fips` canonical).
4. Verified the live Gold parquet against the spec claims:
   - Row count = 51, column count = 15.
   - `state_fips` cardinality = 51, `state_name` cardinality = 51, `state_abbr` cardinality = 51.
   - `state_fips` <-> `state_name` bijection confirmed (max 1 in each direction).
   - `state_fips` <-> `state_abbr` bijection confirmed (max 1 in each direction).
   - `cost_tier` distribution: very_high=4, high=8, average=13, low=11, very_low=15 (all 5 tiers materialize, sum = 51).
   - `verification_status`: bea_official=8, estimate=43 (matches Bronze carry-forward exactly).
   - `data_year` distinct count = 1.
5. Confirmed no cross-source joins are performed in the Gold transform — the Gold BEA RPP table joins at query time in MCP / frontend, not in the pipeline.
6. Authored the Gold ER decision document at `governance/entity-resolution/gold-regional-price-parities.md` restating the SKIP, documenting what changed vs Silver, showing the live-table evidence, and explicitly classifying each new Gold column as non-ER.

## Decisions Made

| # | Decision | Rationale |
|---|---|---|
| 1 | **SKIP entity resolution for the Gold spec.** | Gold adds no new identifier, no alias surface, no cross-source join, and no lifecycle events. State FIPS remains canonical. |
| 2 | **Carry-forward Silver resolution posture unchanged.** | The four new columns are pure functional dependents of already-resolved columns. Identity is preserved verbatim through the promote. |
| 3 | **Do not add entries to `governance/entity-registry.json`.** | The Gold table is itself the authoritative state registry for FutureProof; duplicating it into the registry would be redundant. Downstream consumers join directly. |
| 4 | **Do not flag any row for human review.** | 0 ambiguous rows. Live-table verification shows perfect bijections and row-count preservation from Silver. |
| 5 | **Classify `record_id` as a grain surrogate, not a new identity.** | It is computed deterministically from `state_fips` alone via the standard `compute_grain_id` helper; it carries no identity information that `state_fips` does not already carry. Its DQ verification (non-null, unique) belongs to @dq-engineer. |
| 6 | **Classify `cost_tier` as a derivation, not a taxonomy requiring resolution.** | The CASE expression is deterministic on `rpp_all_items`; there are no external cost-tier authorities to reconcile against. Any tier-boundary concerns are CDE/DQ scope, not ER. |
| 7 | **Defer MCP-layer state-input resolution (abbrev / name / FIPS) to the `mcp-bea-rpp` spec.** | That is user-input normalization at query time, not pipeline entity resolution. Already called out as a forward-looking obligation. |

## Evidence Snapshot (live Gold table)

- Rows: 51
- Columns: 15
- `state_fips` cardinality: 51 (100% unique)
- `state_name` cardinality: 51 (100% unique)
- `state_abbr` cardinality: 51 (100% unique)
- Bijection `state_fips` <-> `state_name`: confirmed
- Bijection `state_fips` <-> `state_abbr`: confirmed
- `cost_tier` buckets: {very_high: 4, high: 8, average: 13, low: 11, very_low: 15}
- `verification_status` buckets: {bea_official: 8, estimate: 43}
- Distinct `data_year`: 1

## Resolution Statistics

- Total entities processed: **51** (U.S. states + DC)
- Exact ID matches (confidence 1.0): **51**
- High-confidence matches (0.9-0.99): **0**
- Medium-confidence matches (0.7-0.9): **0**
- Low-confidence matches flagged for review (<0.7): **0**
- Lifecycle events discovered: **0**
- New entity-registry entries added: **0**
- Unresolved rows: **0**

## Outputs

| Artifact | Path |
|---|---|
| ER decision document | `governance/entity-resolution/gold-regional-price-parities.md` |
| Audit trail (this file) | `governance/audit-trail/2026-04-11-entity-resolver-gold-regional-price-parities.md` |
| `governance/entity-registry.json` | not modified (no new canonical entities required) |

## Carry-Forward Chain (Bronze -> Silver -> Gold)

| Zone | Decision Doc | Identifier | Decision |
|---|---|---|---|
| Bronze | `governance/entity-resolution/raw-ingest-bea-rpp.md` | `geo_fips` | SKIP (canonical FIPS, 51/51 clean) |
| Silver | `governance/entity-resolution/silver-base-bea-rpp.md` | `state_fips` (renamed from `geo_fips`) | SKIP (carry-forward, 3 invariants verified live) |
| Gold | `governance/entity-resolution/gold-regional-price-parities.md` | `state_fips` (verbatim) | SKIP (carry-forward, bijections re-verified live, 4 new columns classified as non-ER) |

Chain is complete and internally consistent. No open ER obligations remain for the BEA RPP data product through the Gold zone.
