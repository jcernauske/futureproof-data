# Lineage Tracker Audit Trail — full-pipeline-eada (bronze zone)

- **Date:** 2026-04-30
- **Agent:** @bs:lineage-tracker
- **Spec:** `docs/specs/full-pipeline-eada.md`
- **Scope:** Bronze zone only — `bronze.eada` (silver and consumable lineage events are future appends)
- **Output file:** `governance/lineage/full-pipeline-eada-20260501T040238Z.json`
- **Scorecard referenced:** `governance/dq-scorecards/raw-eada-20260501T040238Z.json`

## Filename Convention Decision

Per the spec's §8 amendment (resolved in the §11 re-review on 2026-04-30), the lineage filename uses the **spec basename** rather than a table basename:

- Chosen: `governance/lineage/full-pipeline-eada-{timestamp}.json`
- Rejected: `governance/lineage/raw-eada-{timestamp}.json` (table-scoped)
- Rejected: `governance/lineage/raw-ingest-eada-{timestamp}.json` (legacy pre-rename)

Rationale: the lineage event is spec-scoped because subsequent appends will list multiple base inputs (`base.ipeds_finance` AND `base.eada`) into the consumable, which is a §6-thing — not a raw-zone-thing. Table-scoped lineage filenames would mislead.

Timestamp tied to the DQ scorecard (`20260501T040238Z`) so the lineage event and its DQ assertions correlate exactly.

## Inputs Captured

Single external input: the EDA-pre-converted CSV cache at `data/raw/eada_cache/eada_2022.csv`. Modeled as `external.eada_instlevel_2022_csv_cache` rather than as an Iceberg dataset because it is not a Brightsmith-warehouse-managed asset. The `dataSource` facet records:

- `uri`: cache file path (the actual read source for this run)
- `originUri`: SPA backend bulk-download URL (`/api/dataFiles/file?fileName=EADA_2022-2023.zip`) — refresh path
- `landingPageUri`: human-facing page (`https://ope.ed.gov/athletics/`) stamped on every row's `source_url`
- `spaBackendEndpoints`: all three SPA endpoints documented in `governance/domain-context.md` and the EDA report

Source schema lists only the 5 of 168 InstLevel.xlsx columns actually consumed by EadaIngestor: `unitid`, `institution_name`, `GRND_TOTAL_EXPENSE`, `GRND_TOTAL_REVENUE`, `RECRUITEXP_TOTAL`. The remaining 163 columns (per-sport breakdowns, demographic splits) are intentionally not ingested at bronze and are not enumerated.

## Outputs Captured

Single Iceberg output: `bronze.eada` at `data/bronze/iceberg_warehouse/bronze/eada/`. All 10 fields of the `EadaIngestor.get_schema()` Iceberg schema are listed (Iceberg field IDs 1-10), including the four framework metadata columns (`source_url`, `source_method`, `ingested_at`, `load_date`).

Snapshot ID `5935703872733658125` recorded in both the `version` facet and the `outputFacets.snapshotId` for cross-reference.

## Column Lineage Decisions

10 column-lineage entries — one per output field. Notable choices:

- **`reporting_year`** has empty `inputFields` (no source field) and `transformationType: DERIVED`. The EADA file has no in-row year column; the value is stamped from `EadaIngestor.DEFAULT_REPORTING_YEAR=2022`. Documented prominently because future cycles will require either an `__init__` override or a new ingestor instantiation.
- **The three monetary fields** are typed `DERIVED` (not `DIRECT`) because each goes through a two-stage transform: `_strip_sentinel` then `_coerce_double`. Description names both stages and explains why sentinel-strip happens BEFORE coercion (otherwise `'-1'` survives as numeric `-1` and trips RAW-EAD-004).
- **`unitid`** is typed `DERIVED` because `_coerce_long` handles four distinct input variants (int / float / quoted-string / leading-zero string) — non-trivial coercion, not identity.
- **`institution_name`** is typed `DIRECT` — `str().strip()` only, with empty-collapse-to-None enforced by the required=true schema constraint and DQ rule RAW-EAD-002.
- **`source_url`**, **`source_method`**, **`ingested_at`**, **`load_date`** all have empty `inputFields` and are marked `DERIVED` — framework-stamped, no payload provenance. `source_method` is specifically called out as set post-hoc by the `EadaIngestor.ingest()` override (mirrors the BEA RPP pattern).

## DQ Assertions

All 12 rules from the scorecard are enumerated with `ruleId`, `name`, `priority`, `dimension`, `column`, `status`, `actual`, and `threshold`. Summary fields (`p0Total`, `p0Pass`, `p1Total`, `p1Pass`, `overallPass`, `p0GateBlocking`) match the scorecard's `summary` block exactly.

The `dataQualityAssertions` facet is namespaced as a Brightsmith convention — it is not a vanilla OpenLineage facet. Documented in the runtime metadata and pointed back at the scorecard JSON for the underlying detail rows.

## OpenLineage Spec Conformance Notes

- `eventType: COMPLETE`, `eventTime`, `run.runId` (UUID v4), `job.namespace`, `job.name` all conform to the OpenLineage 0.x run-event schema.
- Standard facets used: `documentation`, `sourceCode`, `schema`, `dataSource`, `version`, `columnLineage`.
- Brightsmith-prefixed extension facets: `brightsmith_specReference`, `brightsmith_agentAttribution`, `brightsmith_runtimeMetrics`. The `brightsmith_` prefix follows the OpenLineage convention for vendor-namespaced custom facets.
- `dataQualityAssertions` on the output dataset facets is also a Brightsmith extension (the OpenLineage `dataQualityMetrics` facet exists but is row-count-oriented; we want rule-level pass/fail). Compatible with OpenLineage's open extension model.
- `inputFacets` and `outputFacets` (row counts and snapshot IDs) follow the OpenLineage InputDataset/OutputDataset facet pattern.

## Future Appends (Out of Scope for This Event)

Per the §8 amendment, this lineage file will receive additional events as silver and consumable land:

1. `base.eada` event — silver promotion from `bronze.eada` LEFT JOIN `base.ipeds_finance`, deriving four per-FTE / subsidy-ratio columns.
2. `consumable.institution_aura` event — multi-zone consumable that lists BOTH `base.ipeds_finance` AND `base.eada` as inputs (per §8 line 747).

Append-as-events to the existing JSON array, do not overwrite.
