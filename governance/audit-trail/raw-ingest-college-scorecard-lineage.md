# Lineage Audit Trail: raw-ingest-college-scorecard

**Agent:** @lineage-tracker
**Date:** 2026-04-06T03:10:47Z
**Spec:** docs/specs/raw-ingest-college-scorecard.md

## Verification Summary

### Runtime Lineage Events (governance.lineage_events Iceberg table)

BaseIngestor._emit_lineage() auto-emitted runtime events. Found **4 events** across **2 runs**:

| Run ID | Event Type | Row Count | Snapshot ID | Event Time |
|--------|-----------|-----------|-------------|------------|
| 0d89ba14-22f7-4883-a38f-fd31c264413f | START | - | - | 2026-04-06T02:33:20.659920Z |
| 0d89ba14-22f7-4883-a38f-fd31c264413f | COMPLETE | 50 | 7888250684691178698 | 2026-04-06T02:33:20.694358Z |
| 32ea029e-74c9-4aeb-a058-1190df46b643 | START | - | - | 2026-04-06T02:34:21.429997Z |
| 32ea029e-74c9-4aeb-a058-1190df46b643 | COMPLETE | 69,947 | 2229077043664148049 | 2026-04-06T02:34:21.452516Z |

**Run 1** (0d89ba14): Test run with sample data (50 rows). Snapshot 7888250684691178698 was later overwritten.
**Run 2** (32ea029e): Production run with full dataset (69,947 rows). Snapshot 2229077043664148049 is the current active snapshot.

### Iceberg Table Verification

Current Iceberg snapshot `2229077043664148049` confirms:
- Operation: append
- Added records: 69,947
- Total records: 69,947
- Data file size: 587,268 bytes

The snapshot ID in the COMPLETE lineage event matches the current Iceberg table snapshot. Row count is consistent.

### Gaps Identified in Runtime Events

The auto-emitted events are structurally valid but missing governance metadata:

| Field | Status | Impact |
|-------|--------|--------|
| spec_reference | MISSING (null) | Cannot trace lineage back to spec |
| agent_id | MISSING (null) | Cannot attribute transformation to agent |
| transformation_steps | MISSING (null) | No record of what transformations were applied |
| duration_ms | MISSING (null) | No performance baseline |
| input_tables on COMPLETE | EMPTY (`[]`) | COMPLETE event drops input reference |
| skipped_duplicates | 0 | Correct -- this was first load, no dedup occurred |

### Supplemental Lineage File Created

Because the runtime events lack column-level lineage and transformation documentation, a supplemental OpenLineage JSON file was created:

**File:** `governance/lineage/raw-ingest-college-scorecard-20260406T031047Z.json`

This file contains:
- Full OpenLineage run event format
- Column-level lineage for all 16 fields (12 source + 4 framework-derived)
- Transformation descriptions for each field
- Transformation type classification (DIRECT vs DERIVED)
- Spec reference and agent attribution
- Input source metadata (URL, fallback URL, schema)
- Output Iceberg schema with types

### Transformations Documented

| # | Transformation | Type | Description |
|---|---------------|------|-------------|
| 1 | CREDLEV filter | Row filter | fetch() filters CSV to CREDLEV=3 only (bachelor's degrees) |
| 2 | Column selection | Column filter | COLUMN_MAP selects 12 of ~174 source columns |
| 3 | Sentinel nullification | Value transform | PrivacySuppressed, PS, NA, NULL, empty string all become None |
| 4 | Type coercion (long) | Type cast | unitid, ipedscount1, ipedscount2: string to int |
| 5 | Type coercion (int) | Type cast | credlev: string to int |
| 6 | Type coercion (double) | Type cast | md_earn_wne, earn_mdn_hi_1yr, earn_mdn_hi_2yr, debt_all_stgp_eval_mdn: string to float |
| 7 | Null grain filter | Row filter | Rows with null unitid, cipcode, or credlev are dropped |
| 8 | Dedup | Row filter | BaseIngestor deduplicates on (unitid, cipcode, credlev) grain |
| 9 | Metadata enrichment | Column add | BaseIngestor adds ingested_at, source_url, source_method, load_date |

### Naming Decisions

- **Job name:** `raw.ingest-college-scorecard` (follows `{zone}.{transformation-name}` convention)
  - Note: Runtime events use `ingest:college_scorecard` (BaseIngestor default). The supplemental file uses the spec naming convention.
- **Input namespace:** `ed.gov` (data authority is U.S. Department of Education)
- **Input dataset:** `college-scorecard.field-of-study-csv` (describes the specific dataset)
- **Output namespace:** `brightsmith` (project namespace)
- **Output dataset:** `raw.college_scorecard` (matches Iceberg table identifier)

### Recommendations

1. **BaseIngestor enhancement:** `_emit_lineage()` should populate `spec_reference`, `agent_id`, and `transformation_steps` fields. These are available in the SourceConfig and manifest but not currently passed through.
2. **COMPLETE event input_tables:** The COMPLETE event should carry forward the input_tables from the START event rather than emitting an empty list.
3. **Duration tracking:** `_emit_lineage()` should capture elapsed time between fetch start and append completion.
