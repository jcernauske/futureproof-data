# Audit Trail — @lineage-tracker — raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @lineage-tracker
**Spec:** docs/specs/raw-ingest-bea-rpp.md
**Artifact:** governance/lineage/raw-ingest-bea-rpp-20260410.json

## Scope

Captured OpenLineage for the Bronze ingest of BEA Regional Price Parities (SARPP, All Items, 2024) into `bronze.bea_rpp`. One lineage event emitted for the single ingest job `brightsmith:ingest:bea_rpp`. No transformations in Silver, Gold, or MCP zones were in scope for this run — those will be captured in subsequent lineage events as each zone lands.

## Run Summary

| Field | Value |
|-------|-------|
| Job | `brightsmith:ingest:bea_rpp` |
| Output dataset | `brightsmith:bronze.bea_rpp` (Iceberg) |
| Row count | 51 (50 states + DC) |
| Source method | `csv_cache` (BEA API not exercised on this run) |
| Input | `data/raw/bea_cache/bea_rpp_2024.csv` (fallback path); logical upstream is the BEA JSON API endpoint `Regional/SARPP/LineCode=1/Year=2024/GeoFips=STATE` |
| Ingestor | `src/raw/bea_rpp_ingestor.py` (class `BeaRppIngestor`) |
| Runner | `scripts/ingest_bea_rpp.py` |
| Spec version | 1.0 |

## Events Emitted

- 1 OpenLineage run event (`eventType: COMPLETE`).

## Column Mappings Captured

Eight output columns on `bronze.bea_rpp`. All are captured in the `columnLineage.fields` facet.

| Target field | Source field(s) | Type | Transformation |
|---|---|---|---|
| `geo_fips` | `GeoFips` (API/CSV) | DERIVED | `_normalize_geo_fips`: strip trailing "000" from 5-digit state form, zero-pad to 2 chars. Metro/CBSA rows not matching the 50-states-plus-DC allow-list are filtered upstream in `flatten`. |
| `geo_name` | `GeoName` (API/CSV) | DIRECT | `_coerce_string` (trim; empty → null). No renaming. |
| `rpp_all_items` | `DataValue` (API/CSV) | DERIVED | `_coerce_double`: strip commas/whitespace, coerce string → float. Units are "index, national = 100.0". |
| `data_year` | `TimePeriod` (API/CSV) | DERIVED | `_coerce_int` via `int(float(value))`; defaults to `DEFAULT_YEAR` = 2024 if null/unparseable. |
| `source_url` | (none) | FRAMEWORK/DERIVED | Injected by `BaseIngestor` via `BeaRppIngestor.get_source_url()`. BEA API URL template with `API_KEY` redacted. Same canonical value regardless of whether API or CSV cache served the request. |
| `source_method` | (none) | FRAMEWORK/DERIVED | Injected by `BaseIngestor`. `BeaRppIngestor.ingest()` overrides `BaseIngestor.ingest()` so the effective method (`bea_api` vs `csv_cache`) is resolved from the actual fetch payload before the framework's row-level metadata pass. This run: `csv_cache`. |
| `ingested_at` | (none) | FRAMEWORK | UTC timestamp at ingest time. |
| `load_date` | (none) | FRAMEWORK | Date of load. |

## Unmapped / Dropped Source Fields

The BEA API Data array contains two additional fields the ingestor reads but does not persist to Bronze:

- `CL_UNIT` — classification unit label. Informational only; constant for the SARPP/LineCode=1 slice.
- `UNIT_MULT` — unit multiplier. Informational only; constant for an index value.

Neither is required by the spec's Bronze schema and both would be constants across the 51 rows, so they were intentionally dropped at the `flatten` stage. This is expected and documented in the ingestor docstring. No downstream zone currently depends on them.

## Naming Decisions

- **Job namespace:** `brightsmith` (matches prior lineage events in this project — `brightsmith:ingest:karpathy_ai_exposure`, `brightsmith:ingest:bls_ooh`, etc.).
- **Job name:** `ingest:bea_rpp` — consistent with the `ingest:<source>` pattern already established by other raw ingest lineage files in `governance/lineage/`.
- **Output dataset name:** `bronze.bea_rpp` — matches spec Section "Zone 1: Bronze (Raw Ingest)" and the Iceberg table actually written. (Note: the spec prose says `raw.bea_rpp` in Success Criteria line 51 and `bronze.bea_rpp` in the task brief. The latter matches the framework's current Bronze zone table naming; used here for consistency with other lineage events.)
- **Input datasets:** two logical inputs captured to reflect the dual-path fetch strategy:
  - `apps.bea.gov:Regional/SARPP/LineCode=1/Year=2024/GeoFips=STATE` — the logical API endpoint.
  - `local.fs:data/raw/bea_cache/bea_rpp_2024.csv` — the fallback CSV that was actually consumed on this run.
  Both are listed so downstream consumers of the lineage graph see that either path can satisfy the job; the `brightsmith_runMetrics.sourceMethod` run facet disambiguates which one fired.

## Ambiguities / Interpretations

1. **`source_url` lineage.** The framework-injected `source_url` is the API URL template even when the fetch fell back to CSV. This is captured as `DERIVED` with no input field and the transformationDescription explains that the value represents the canonical source locator, not the physical fetch path. The physical fetch path is disclosed via `source_method` and the run-level `sourceFiles` metric.

2. **Double-source inputFields for data fields.** Each mapped column lists both the API and CSV inputs as input fields. This is accurate: `_read_csv_file` and `_parse_api_response` both emit dicts with BEA API field names (`GeoFips`, `GeoName`, `DataValue`, `TimePeriod`) and the same `flatten` path consumes either payload. The column lineage therefore reflects the logical source schema, not the physical file served on this run.

3. **Filtered row lineage.** Metro/CBSA rows and territory rows are filtered in `flatten` before being written. They are not represented as output rows, so no column-level lineage exists for them. The run metric `metroRowsFiltered` / `nonStateRowsFiltered` is set to 0 for this run because the CSV cache already contained only the 51 allowed rows.

## Verification

- Lineage file JSON is syntactically valid (matches the shape of prior events such as `raw-ingest-karpathy-ai-exposure-20260409T142500Z.json`).
- Every field in the output Iceberg schema (per `BeaRppIngestor.get_schema()`) is present in `columnLineage.fields`.
- Spec reference (`docs/specs/raw-ingest-bea-rpp.md`) exists on disk.
- Source code reference (`src/raw/bea_rpp_ingestor.py`) exists and the `BeaRppIngestor` class is defined there.
- Row count in lineage (51) matches the target table row count reported by the runner.

## Completeness Checklist

- [x] Every transformation described in the spec's Bronze section is covered by a lineage event.
- [x] All 8 Bronze output columns have column-level lineage entries.
- [x] Agent attribution present (`@primary-agent` — original implementer; `@lineage-tracker` authored this record).
- [x] Spec reference present.
- [x] Run metrics (row count, source method, data vintage) captured.
- [x] Source and target dataset names follow project conventions.

## Notes for Downstream Agents

- When Silver (`base.bea_rpp`) lands, emit a new lineage event with `brightsmith:base:bea_rpp` as the job and `bronze.bea_rpp` as the input. The Silver-side derived fields (`state_abbr`, `census_region`, `purchasing_power_multiplier`, `record_id`) need explicit column lineage rules since they are derived or framework-computed.
- `@cde-tagger` should tag `rpp_all_items` and (eventually) `purchasing_power_multiplier` as Critical Data Elements given their central role in the salary adjustment flow.
- `@dq-engineer` should confirm the Bronze DQ rules (row count = 51, RPP range 80.0–130.0, California/Arkansas spot checks) are tied to this run's output snapshot.
