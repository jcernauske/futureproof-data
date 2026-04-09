# Lineage Capture: raw-ingest-bls-ooh

**Agent:** @lineage-tracker
**Spec:** docs/specs/raw-ingest-bls-ooh.md
**Timestamp:** 2026-04-07T12:00:00Z
**Lineage File:** governance/lineage/raw-ingest-bls-ooh-20260407T120000Z.json

## Transformations Captured

Single OpenLineage COMPLETE event covering the full XLSX-to-Iceberg ingest pipeline.

### Source
- **Namespace:** bls.gov
- **Dataset:** employment-projections.occupational-characteristics-xlsx
- **Format:** XLSX (Excel)
- **Fields captured:** 14 source columns mapped via fuzzy header matching

### Target
- **Namespace:** brightsmith
- **Dataset:** raw.bls_ooh
- **Fields captured:** 19 (15 data + 4 metadata)

### Key Transformation Decisions

1. **Employment figures (DERIVED, not DIRECT):** Source values are reported "in thousands" so the ingestor multiplies by 1000 and rounds to long. This is a mathematical transformation, not a direct copy, so `employment_current`, `employment_projected`, `employment_change`, and `openings_annual_avg` are classified as DERIVED.

2. **Median wage (DERIVED):** Complex string parsing including top-code detection (">=" prefix), N/A handling, and dollar/comma stripping. Classified as DERIVED due to conditional logic.

3. **Median wage capped flag (DERIVED):** Boolean derived from the same median wage source field via conditional string matching. Two output fields from one input field.

4. **Employment change percent (DIRECT):** Simple numeric coercion with comma/percent stripping -- classified as DIRECT since the semantic value is preserved.

5. **Education/training codes (DIRECT):** Integer coercion via int(float(value)) -- straightforward type cast, classified as DIRECT.

6. **Summary row filtering:** SOC codes ending in "0000" are excluded during XLSX parsing (_read_xlsx method). This is documented in the soc_code transformation description.

7. **Metadata fields (DERIVED, no input):** ingested_at, source_url, source_method, load_date are framework-generated with empty inputFields arrays.

### Naming Decisions
- **Input namespace:** `bls.gov` (matches the data provider, parallel to `ed.gov` used for College Scorecard)
- **Input dataset name:** `employment-projections.occupational-characteristics-xlsx` (descriptive of the specific BLS EP table)
- **Job name:** `raw.ingest-bls-ooh` (follows zone.transformation-name convention)

### Runtime Metrics Note
This is a static lineage capture. Runtime row counts and snapshot IDs will be populated automatically by BaseIngestor auto-emission on the first live ingest run. The runtimeMetrics facet includes null rowCount with an explanatory note.
