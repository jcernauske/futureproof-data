# Audit Trail: Lineage Capture — raw-ingest-college-scorecard-institution

**Agent:** @lineage-tracker
**Timestamp:** 2026-04-14T21:30:00Z
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Lineage file:** governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json
**Run ID:** 81ba1e54-0862-441e-b1d0-62fbc014b8f3

## Scope

Captured OpenLineage events for the Bronze zone ingest only. The spec also defines Silver (`base.college_scorecard_institution`) and Gold (`consumable.career_outcomes` LEFT JOIN) transformations, but these are future work and will get their own lineage records when implemented.

## Transformations Captured

Single COMPLETE run event for `raw.ingest-college-scorecard-institution` job:

- **Input:** `ed.gov / college-scorecard.institution-csv` (bulk CSV download)
- **Output:** `brightsmith / raw.college_scorecard_institution` (Iceberg table)
- **Column lineage:** 24 DIRECT source-to-target mappings, 4 DERIVED framework-generated metadata columns

## Naming Decisions

- **Job name:** `raw.ingest-college-scorecard-institution` — follows the existing pattern `raw.ingest-college-scorecard` (same source, different file) with the `-institution` suffix to distinguish from the field-of-study ingest.
- **Input namespace:** `ed.gov` — matches existing Scorecard field-of-study lineage.
- **Input dataset name:** `college-scorecard.institution-csv` — parallels the existing `college-scorecard.field-of-study-csv`.
- **Output dataset:** `raw.college_scorecard_institution` — matches spec's Iceberg table name.

## Transformation Type Decisions

- All 24 mapped source columns are `DIRECT` — they are string parses from CSV with sentinel nullification and numeric coercion but no aggregation or derivation from multiple source fields. The Silver zone's `net_price_annual` (which picks between `npt4_pub` and `npt4_priv` based on `control`) will be `DERIVED` when that event is produced.
- Framework-generated columns (`ingested_at`, `source_url`, `source_method`, `load_date`) marked `DERIVED` with empty `inputFields` since they come from runtime metadata rather than source data.

## Filter / Dedup Documentation

Captured in `brightsmith_runtimeMetrics` and individual column `transformationDescription` fields:
- **Filter:** `PREDDEG == 3 OR ICLEVEL == 1` (documented on both `preddeg` column lineage and run facets)
- **Dedup:** first-row-wins on `unitid` (documented on `unitid` column lineage and run facets)
- **Sentinel nullification:** `PrivacySuppressed`, `PS`, `NA`, `NULL`, empty string

## Runtime Metrics — NOT YET POPULATED

This lineage event captures the transformation structure but does NOT include runtime metrics from an actual execution (row count, snapshot_id, duration_ms, dq metrics). The ingestor class (`src/raw/college_scorecard_institution_ingestor.py`) has been implemented, but no completed ingest run was identified at lineage capture time.

`brightsmith_runtimeMetrics` contains the spec's expected row count range (5,000-8,000) rather than actual post-run values. After the first successful ingest, a follow-up lineage event with actual `rowCount`, `snapshotId`, `durationMs`, and DQ pass/fail counts should be emitted (the framework may auto-emit this via `BaseIngestor.ingest()`).

## Completeness Status

- [x] Job + namespace documented
- [x] Input dataset with source URL, method, and schema documented
- [x] Output dataset with full Iceberg schema documented
- [x] Column-level lineage for all 28 output columns (24 DIRECT + 4 DERIVED)
- [x] Spec reference facet
- [x] Agent attribution facet with reasoning
- [ ] Runtime metrics from actual execution (pending first run)

## Governance Handoff

Lineage record is ready for @governance-reviewer's completeness checklist. Gaps noted:
- Runtime metrics are expected values, not observed. Re-verify after first ingest run populates `governance.lineage_events` Iceberg table.
- Silver and Gold lineage are future work — track separately when those transformers are implemented per the spec.
