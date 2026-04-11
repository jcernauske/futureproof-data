# Lineage Tracker Audit — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @lineage-tracker
**Spec:** docs/specs/gold-regional-price-parities.md
**Transformer:** src/gold/regional_price_parities_transformer.py (`transform`)
**Cost-Tier Module:** src/gold/_cost_tier.py (`classify_cost_tier`, `COST_TIER_BREAKPOINTS`)
**Runner:** scripts/promote_regional_price_parities.py
**Lineage Artifact:** governance/lineage/gold-regional-price-parities-20260411.json

---

## Scope

Silver -> Gold promote for BEA Regional Price Parities. One OpenLineage `COMPLETE` event covering the full `base.bea_rpp` (51 rows, 11 columns) -> `consumable.regional_price_parities` (51 rows, 15 columns) transformation. No sub-events — this is a single atomic promote pattern via `brightsmith.infra.promote`, not a multi-stage pipeline. This is the smallest Gold transformation in the project: no joins, no concept normalization, no cross-source work.

## Inputs Captured

1. **brightsmith / base.bea_rpp** — the Silver source Iceberg table (51 rows, 11 columns). Schema fields enumerated include all 11 Silver columns. Three Silver columns are explicitly noted as NOT carried forward to Gold:
   - `record_id` (Silver grain id, prefix `rpp`) — Gold computes its own `rpc`-prefixed record_id
   - `source_load_date` — stops at Silver
   - `ingested_at` — replaced by Gold `promoted_at`

2. **brightsmith / gold._cost_tier** — the in-code frozen cost-tier classifier module. Captured as a named input dataset so `cost_tier` has a traceable, named provenance rather than opaque in-code logic. This follows the precedent set in `silver-base-bea-rpp-20260410.json` where `silver._us_state_reference` was modeled as a named input for the same reason. The module exposes `COST_TIER_BREAKPOINTS` (the frozen descending tuple) and `CostTier` (the 5-value string enum). Both are BT-106 governance-frozen per the physical model.

## Job

- **Namespace:** `brightsmith`
- **Name:** `gold.promote-regional-price-parities`
- **Source code:** `src/gold/regional_price_parities_transformer.py`
- Used `promote-` rather than `transform-` to match the Silver precedent (`silver.promote-bea-rpp`) and to reflect that this spec uses the idempotent `promote` pattern rather than a bespoke transform. This is a subtle but load-bearing distinction for the governance reviewer.

## Outputs Captured

- **brightsmith / consumable.regional_price_parities** with full 15-column schema and column-level lineage for every column.

## Column Mapping Summary

All 15 Gold columns are mapped. Mapping count: **15 of 15**.

| Gold Column                   | Transformation Type | Source                                                        |
|-------------------------------|---------------------|---------------------------------------------------------------|
| record_id                     | DERIVED             | base.bea_rpp.state_fips (via compute_grain_id, prefix='rpc')  |
| state_fips                    | DIRECT (passthrough)| base.bea_rpp.state_fips                                       |
| state_name                    | DIRECT (passthrough)| base.bea_rpp.state_name                                       |
| state_abbr                    | DIRECT (passthrough)| base.bea_rpp.state_abbr                                       |
| census_region                 | DIRECT (passthrough)| base.bea_rpp.census_region                                    |
| rpp_all_items                 | DIRECT (passthrough)| base.bea_rpp.rpp_all_items                                    |
| purchasing_power_multiplier   | DIRECT (passthrough)| base.bea_rpp.purchasing_power_multiplier                      |
| cost_tier                     | DERIVED (frozen CASE)| base.bea_rpp.rpp_all_items + gold._cost_tier.COST_TIER_BREAKPOINTS |
| adjusted_30k                  | DERIVED (round)     | base.bea_rpp.purchasing_power_multiplier                      |
| adjusted_50k                  | DERIVED (round)     | base.bea_rpp.purchasing_power_multiplier                      |
| adjusted_75k                  | DERIVED (round)     | base.bea_rpp.purchasing_power_multiplier                      |
| adjusted_100k                 | DERIVED (round)     | base.bea_rpp.purchasing_power_multiplier                      |
| verification_status           | DIRECT (passthrough)| base.bea_rpp.verification_status                              |
| data_year                     | DIRECT (passthrough)| base.bea_rpp.data_year                                        |
| promoted_at                   | DERIVED (framework) | (none — UTC now() at promote time)                            |

## Unmapped Fields

**None.** Every Gold column in `consumable.regional_price_parities` has a column-level lineage entry. No ambiguous fields. The 15-target expected count from the task matches 15 actual column-lineage entries.

## Decisions and Rationale

1. **Single event, not per-column events.** The promote runs as one atomic pass through `derive_gold_rows -> add_record_ids -> promote`. Splitting into per-column events would overstate the pipeline's structure. Matches the precedent set by all prior Silver and Gold lineage files in the repo.

2. **`gold._cost_tier` modeled as a named input dataset.** The classifier drives the `cost_tier` derivation; modeling it as a named input makes `cost_tier`'s `inputFields` non-empty (with both `rpp_all_items` and `COST_TIER_BREAKPOINTS` cited) and lets downstream lineage tooling traverse `cost_tier`'s provenance to a concrete artifact. Same rationale as the Silver lineage file modeling `silver._us_state_reference` as a named input. This is the right abstraction because the breakpoints are governance-frozen (BT-106) — they are a first-class lineage concept, not a framework accident.

3. **Silver `record_id`, `source_load_date`, and `ingested_at` explicitly called out as NOT carried forward.** These three Silver columns are real columns in the input schema but do not appear in the output. Documenting this in the input schema field descriptions prevents a future reviewer from assuming the omissions were accidental. In particular, `record_id` not being carried forward is load-bearing: the Gold `record_id` uses a different prefix (`rpc` vs. `rpp`) so Silver and Gold hash namespaces cannot collide per the physical model.

4. **All 8 passthrough columns marked DIRECT.** For `state_fips`, `state_name`, `state_abbr`, `census_region`, `rpp_all_items`, `purchasing_power_multiplier`, `verification_status`, and `data_year`, the transformer performs `{field: row[field] for field in SILVER_PASSTHROUGH_FIELDS}` — literal dict copy, no value mutation. Marking any of these DERIVED would be misleading. Note that `rpp_all_items` and `purchasing_power_multiplier` are ALSO read as derivation inputs (for `cost_tier` and the four `adjusted_Nk` columns respectively), but that does not change their own lineage type as outputs — they are carried forward verbatim.

5. **`record_id` traces back to `state_fips`, not through Silver's `record_id`.** The grain is `['state_fips']` and the prefix is `rpc`. The Gold `record_id` is computed fresh from `state_fips` via `compute_grain_id`; Silver's `record_id` (with prefix `rpp`) is discarded. Drawing the lineage directly to `state_fips` reflects the actual data flow and matches the source-to-target framing of OpenLineage column lineage.

6. **`cost_tier` cites BOTH `rpp_all_items` AND `COST_TIER_BREAKPOINTS` as inputs.** The derivation depends on the data value AND the governance-frozen breakpoints. Omitting the breakpoints would hide the BT-106 dependency from the lineage, which matters because any change to the breakpoints is a breaking change requiring a new spec.

7. **Each `adjusted_Nk` column traces back to `purchasing_power_multiplier` only.** The national-salary anchor (30000, 50000, 75000, 100000) is a frozen in-code constant in `SALARY_ANCHORS`, not a data input. It is a transformation parameter, not a source field. Citing `purchasing_power_multiplier` as the sole source field is the accurate encoding — the anchor is captured in the `transformationDescription` instead. This matches how `100.0` is handled in Silver's `purchasing_power_multiplier` lineage.

8. **Banker's rounding (`round(x, 2)`) documented on every `adjusted_Nk`.** Python's `round()` implements IEEE 754 round-half-to-even, matching DuckDB's default `ROUND()`. The DQ engine evaluates `abs(adjusted_Nk - round(N*1000*multiplier, 2)) <= 0.01` on both sides of the engine boundary, so the rounding-mode consistency is load-bearing. Documenting it in every adjusted column's description gives the DQ reviewer the context without requiring a code dive.

9. **`promoted_at` kept as empty `inputFields`.** Unlike the cost-tier breakpoints, `promoted_at` genuinely has no upstream field — it is `datetime.now(tz=utc)` at `transform()` call time, injected by `add_record_ids`. Empty `inputFields` is the correct encoding, matching Silver's `ingested_at`.

10. **Runtime metrics recorded as expected counts.** `rowsRead`, `rowsDerived`, `promoted`, `skippedDedup` are recorded under `brightsmith_runtimeMetrics`. `snapshotId` and `costTierCounts` are left as `null` because the lineage event is authored pre-run; the framework's auto-emission path fills these at runtime. `costTierCounts` is included as a null placeholder so the schema is stable when the runtime fill lands.

## Naming Conventions Applied

- Job: `gold.promote-regional-price-parities` (zone-dot-verb-subject, matching Silver precedent `silver.promote-bea-rpp`)
- Dataset: `base.bea_rpp` -> `consumable.regional_price_parities` (zone.table, matching manifest and Silver lineage; Gold uses `consumable` as its zone namespace per the Brightsmith convention)
- Reference dataset: `gold._cost_tier` (zone.module, underscore-prefixed to flag it as an internal module rather than a data table, matching Silver's `silver._us_state_reference`)
- Run ID: UUID v4 (`a1c4e9f2-7d38-4b61-9e0a-2f6c83d1b5a7`)

## Completeness Check

- [x] Every transformation step in the spec is represented in the column lineage.
- [x] Every column in the Gold schema (record_id, state_fips, state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, cost_tier, adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k, verification_status, data_year, promoted_at) has a `columnLineage.fields` entry.
- [x] Every derived column names its reference input (`COST_TIER_BREAKPOINTS` for `cost_tier`) in addition to the Silver source column.
- [x] Agent attribution is present and reasoning cites the spec, BT-106 cost-tier freezing, Bronze Condition 7 for `verification_status` carry-forward, banker's-rounding consistency, and the `rpc` vs. `rpp` grain-prefix separation.
- [x] Spec reference facet points to `docs/specs/gold-regional-price-parities.md`.
- [x] Source-code location points to `src/gold/regional_price_parities_transformer.py`.
- [x] Input dataset `gold._cost_tier` points to `src/gold/_cost_tier.py`.

## Deliverables

- `governance/lineage/gold-regional-price-parities-20260411.json` (1 event, 15 output column mappings, 2 input datasets)
- `governance/audit-trail/2026-04-11-lineage-tracker-gold-regional-price-parities.md` (this file)

## Ambiguities / Followups

None. The transformation is small, deterministic, and completely described by the spec plus the transformer source plus the frozen cost-tier module. No interpretation was required. The 15-of-15 column coverage is complete and matches the task-specified target count.
