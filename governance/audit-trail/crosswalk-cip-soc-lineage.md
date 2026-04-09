# Lineage Tracker Audit Trail: crosswalk-cip-soc

**Agent:** @lineage-tracker
**Spec:** docs/specs/crosswalk-cip-soc.md
**Timestamp:** 2026-04-08T12:00:00Z
**Output:** governance/lineage/crosswalk-cip-soc-20260408T120000Z.json

## Events Captured

Two OpenLineage run events covering the full Bronze + Silver pipeline:

### Event 1: Bronze Ingest (raw.ingest-cip-soc-crosswalk)

- **Source:** NCES XLSX (CIP2020_SOC2018_Crosswalk.xlsx)
- **Target:** raw.cip_soc_crosswalk (6,097 rows, 8 columns)
- **Transformations documented:**
  - CIP code float-to-string coercion (openpyxl returns floats for numeric-looking CIP codes)
  - SOC code string preservation
  - Title field whitespace stripping
  - Framework metadata enrichment (ingested_at, source_url, source_method, load_date)
- **Agent:** @primary-agent via CipSocCrosswalkIngestor

### Event 2: Silver Transform (silver.transform-cip-soc-crosswalk)

- **Source:** raw.cip_soc_crosswalk + 3 lookup tables
- **Target:** base.cip_soc_crosswalk (5,903 rows, 13 columns)
- **Transformations documented (13 output fields):**
  - record_id: DERIVED from cipcode + soc_code via compute_grain_id with 'xw' prefix
  - cipcode: DIRECT with validation (XX.XXXX regex)
  - cip_title: DIRECT copy
  - cip_family: DERIVED from cipcode[:2]
  - soc_code: DIRECT with validation (XX-XXXX regex) and pre-filtering of 99-9999
  - soc_title: DIRECT copy
  - soc_major_group: DERIVED from soc_code[:2] with 23-value allowlist validation
  - has_scorecard_match: DERIVED via set-membership lookup against base.college_scorecard.cipcode
  - has_bls_match: DERIVED via set-membership lookup against base.bls_ooh.soc_code
  - has_onet_match: DERIVED via set-membership lookup against base.onet_occupations.bls_soc_code
  - match_quality: DERIVED from 3 match flags via 5-tier CASE expression
  - source_load_date: DIRECT (renamed from load_date)
  - ingested_at: DERIVED (new UTC timestamp)
- **Dropped fields:** source_url, source_method (raw metadata not needed in Silver)
- **Filtered rows:** 194 rows where soc_code = '99-9999' (no-match sentinel)
- **Agent:** @primary-agent via transform()

## Naming Decisions

| Entity | Name | Rationale |
|--------|------|-----------|
| Bronze job | raw.ingest-cip-soc-crosswalk | Follows raw.{verb}-{source} pattern |
| Silver job | silver.transform-cip-soc-crosswalk | Follows silver.{verb}-{source} pattern from existing lineage files |
| Bronze dataset | raw.cip_soc_crosswalk | Matches Iceberg table name |
| Silver dataset | base.cip_soc_crosswalk | Matches Iceberg table name |
| External source | nces.ed.gov / CIP2020_SOC2018_Crosswalk.xlsx | Publisher namespace + filename |

## Interpretation Notes

1. **Cross-table lookups are a distinguishing feature.** Unlike other Silver transformations in this project, the crosswalk transformer reads from 4 input tables (1 Bronze source + 3 Silver lookups). All 4 are documented as inputs in the Silver event with their roles and specific fields used.

2. **match_quality is transitively derived.** It depends on 3 boolean flags, each of which depends on a cross-table lookup. The column lineage for match_quality lists all 5 source fields (cipcode, soc_code from raw + cipcode from scorecard + soc_code from bls + bls_soc_code from onet) to capture the full dependency chain.

3. **The 194 filtered rows are documented.** The filteredRows facet on the output dataset explains why rows were removed and what they represent (NCES 'no match' sentinel for non-career-oriented CIP codes).

## Completeness Check

- [x] Every Bronze transformation has a lineage record
- [x] Every Silver transformation has a lineage record
- [x] All 13 Silver output fields have column-level lineage
- [x] All 4 input tables documented with schemas
- [x] Dropped fields documented with reasons
- [x] Filtered rows documented with criteria and count
- [x] Agent attribution on both events
- [x] Spec reference on both events
- [x] Runtime metrics on both events
