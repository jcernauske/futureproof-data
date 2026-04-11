# Lineage Tracker Audit — silver-base-bea-rpp

**Date:** 2026-04-10
**Agent:** @lineage-tracker
**Spec:** docs/specs/silver-base-bea-rpp.md
**Transformer:** src/silver/bea_rpp_transformer.py (`promote_bea_rpp`)
**Reference Module:** src/silver/_us_state_reference.py
**Runner:** scripts/promote_bea_rpp_silver.py
**Lineage Artifact:** governance/lineage/silver-base-bea-rpp-20260410.json

---

## Scope

Bronze -> Silver promote for BEA Regional Price Parities. One OpenLineage `COMPLETE` event covering the full `bronze.bea_rpp` (51 rows) -> `base.bea_rpp` (51 rows, 11 columns) transformation. No sub-events — this is a single atomic promote pattern, not a multi-stage pipeline.

## Inputs Captured

1. **brightsmith / bronze.bea_rpp** — the source Iceberg table (51 rows). Schema fields enumerated include the 4 data fields carried to Silver (`geo_fips`, `geo_name`, `rpp_all_items`, `data_year`) and the 4 framework/metadata fields that are NOT carried forward (`ingested_at`, `source_url`, `source_method`, `load_date` — noting that `load_date` is renamed to `source_load_date` at the Silver layer). Captured as an input dataset so downstream lineage consumers can traverse the full Bronze -> Silver hop without touching the Bronze lineage file.

2. **brightsmith / silver._us_state_reference** — the in-code reference module holding `FIPS_TO_USPS` (51 entries), `FIPS_TO_CENSUS_REGION` (51 entries), and `BEA_VERIFIED_FIPS` (8 entries). Captured as a second input dataset so the derived columns (`state_abbr`, `census_region`, `verification_status`) have a traceable, named provenance rather than opaque "in-code constants." This treats the reference module as a proper lineage node, which matches the spec's declaration that these lookups are structural U.S. geography.

## Job

- **Namespace:** `brightsmith`
- **Name:** `silver.promote-bea-rpp`
- **Source code:** `src/silver/bea_rpp_transformer.py`
- Naming follows the precedent set by `silver.transform-bls-ooh` in `silver-base-bls-ooh-20260407T210000Z.json`. Used `promote-` rather than `transform-` to reflect that this spec uses the idempotent `promote` pattern, not a bespoke transform — a subtle but load-bearing distinction for the governance reviewer.

## Outputs Captured

- **brightsmith / base.bea_rpp** with full 11-column schema and column-level lineage for every column.

## Column Mapping Summary

All 11 Silver columns are mapped. Mapping count: **11 of 11**.

| Silver Column                 | Transformation Type | Source                                                   |
|-------------------------------|---------------------|----------------------------------------------------------|
| record_id                     | DERIVED             | bronze.bea_rpp.geo_fips (via compute_grain_id)           |
| state_fips                    | DIRECT (rename)     | bronze.bea_rpp.geo_fips                                  |
| state_name                    | DIRECT (rename)     | bronze.bea_rpp.geo_name                                  |
| state_abbr                    | DERIVED (lookup)    | bronze.bea_rpp.geo_fips + FIPS_TO_USPS                   |
| census_region                 | DERIVED (lookup)    | bronze.bea_rpp.geo_fips + FIPS_TO_CENSUS_REGION          |
| rpp_all_items                 | DIRECT (passthrough)| bronze.bea_rpp.rpp_all_items                             |
| purchasing_power_multiplier   | DERIVED (100/x)     | bronze.bea_rpp.rpp_all_items                             |
| verification_status           | DERIVED (allow-list)| bronze.bea_rpp.geo_fips + BEA_VERIFIED_FIPS              |
| data_year                     | DIRECT (passthrough)| bronze.bea_rpp.data_year                                 |
| source_load_date              | DIRECT (rename)     | bronze.bea_rpp.load_date                                 |
| ingested_at                   | DERIVED (framework) | (none — UTC now() at promote time)                      |

## Unmapped Fields

None. Every Silver column in `base.bea_rpp` has a column-level lineage entry. No ambiguous fields.

## Decisions and Rationale

1. **Single event, not per-column events.** The promote runs as one atomic pass through `transform_rows -> promote`. Splitting into per-column events would overstate the pipeline's structure. This matches the precedent set by all prior Silver lineage files in the repo.

2. **`silver._us_state_reference` modeled as an input dataset, not just a job annotation.** The three lookups drive three derived columns; modeling them as a named input makes the derived columns' `inputFields` non-empty and lets downstream lineage tooling traverse the provenance of `state_abbr`, `census_region`, and `verification_status` back to a concrete artifact. This is a slight departure from the Bronze lineage file (which used empty `inputFields` for framework-injected columns), but it is warranted here because the reference module is the actual source of derivation logic, not a framework accident.

3. **`ingested_at` kept as empty `inputFields`.** Unlike the state-reference lookups, `ingested_at` genuinely has no upstream field — it is `datetime.now(tz=utc)` at row-build time. Empty `inputFields` is the correct encoding.

4. **`rpp_all_items` marked DIRECT, not DERIVED.** The transformer performs `float(value)` but does not rescale, normalize, or re-unit. This is a type assertion, not a derivation. Marking it DERIVED would be misleading for DQ reviewers scanning the lineage for real transformations.

5. **`source_load_date` marked DIRECT.** Same reasoning: rename-only. The value bytes are identical to `bronze.load_date`.

6. **`record_id` traces back to `geo_fips`, not to all grain fields.** The grain is `['state_fips']`, and `state_fips` itself traces back to `geo_fips`. Drawing `record_id`'s lineage directly to the Bronze source column rather than chaining through the Silver intermediate is more useful to downstream consumers and matches the "source -> target" framing of OpenLineage column lineage.

7. **`verification_status` rationale documented in `transformationDescription`.** The 8-state allow-list and the Bronze staff-review Ruling 2 / Condition 6 closure are written into the transformation description so the governance reviewer does not have to cross-reference the staff-review file to verify provenance.

8. **Runtime metrics recorded as expected counts.** `rowsRead`, `rowsTransformed`, `promoted`, `skippedDedup`, and `verificationCounts` are recorded under `brightsmith_runtimeMetrics` to match the pattern in `silver-base-bls-ooh-20260407T210000Z.json`. `snapshotId` is left as `null` because the lineage event is authored pre-run; the framework's auto-emission path would fill this in at runtime.

## Naming Conventions Applied

- Job: `silver.promote-bea-rpp` (zone-dot-verb-subject, matching the Silver precedent)
- Dataset: `bronze.bea_rpp` / `base.bea_rpp` (zone.table, matching manifest and Bronze lineage)
- Reference dataset: `silver._us_state_reference` (zone.module, underscore-prefixed to flag it as an internal module rather than a data table)
- Run ID: UUID v4 (`9f7b2d14-3c1a-4e85-b6a2-8a0d5f9c17e3`)

## Completeness Check

- [x] Every transformation step in the spec (sections "Silver Transformations" 1-9) is represented in the column lineage.
- [x] Every column in the Silver schema (record_id, state_fips, state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, verification_status, data_year, source_load_date, ingested_at) has a `columnLineage.fields` entry.
- [x] Every derived column names its reference-table input (`FIPS_TO_USPS`, `FIPS_TO_CENSUS_REGION`, `BEA_VERIFIED_FIPS`) in addition to the Bronze source column.
- [x] Agent attribution is present and reasoning cites the spec, the Bronze staff-review ruling, and the DC Census quirk.
- [x] Spec reference facet points to `docs/specs/silver-base-bea-rpp.md`.
- [x] Source-code location points to `src/silver/bea_rpp_transformer.py`.

## Deliverables

- `governance/lineage/silver-base-bea-rpp-20260410.json` (1 event, 11 output column mappings, 2 input datasets)
- `governance/audit-trail/2026-04-10-lineage-tracker-silver-base-bea-rpp.md` (this file)

## Ambiguities / Followups

None. The transformation is small, deterministic, and completely described by the spec plus the transformer source. No interpretation was required.
