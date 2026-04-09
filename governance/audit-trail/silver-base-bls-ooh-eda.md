# Audit Trail: Silver EDA for base.bls_ooh

**Date:** 2026-04-07
**Agent:** @data-analyst
**Spec:** silver-base-bls-ooh
**Zone:** Silver (profiling Bronze data for Silver DQ thresholds)

## Dataset Analyzed

- **Source:** Bronze `raw.bls_ooh` (832 rows, parsed from BLS Employment Projections interactive export via `BlsOohIngestor`)
- **Data file:** `data/raw/xlsx_cache/bls_ooh.xlsx` (the Bronze Iceberg table was not yet available in the catalog; data was parsed through the ingestor pipeline to replicate Bronze output)
- **Purpose:** Establish evidence-based DQ thresholds for the Silver `base.bls_ooh` transformation

## Key Findings

1. **Catchall count is 70, not 46 as stated in the spec.** Case-insensitive substring match for "all other" in occupation_title yields 70 rows. The spec's number of 46 must be corrected.
2. **12 rows have sign discrepancy** between employment_change (integer, rounded from thousands) and employment_change_pct (more precise). This is a BLS rounding artifact, not a data quality issue.
3. **All 7 broad occupation codes confirmed present.** No overlap with catchall categories.
4. **23 null-wage occupations confirmed.** Breakdown: 14 physicians/surgeons, 5 performers, 3 dental specialists, 1 fishing/hunting.
5. **Growth category distribution verified:** declining_fast=54, declining=155, stable=80, growing=481, growing_fast=51, booming=11.
6. **Boundary values exist at every growth category threshold.** Half-open interval logic is critical.
7. **All 22 SOC major groups populated.** All code-to-text mappings are deterministic.

## Threshold Recommendations

- Catchall flag TRUE count: 70 (not 46)
- Broad occupation flag TRUE count: exactly 7
- Null wage rate: max 5% (actual 2.8%)
- Wage range: $15,000 - $250,000 (actual $30,160 - $238,380)
- Employment change pct range: -100 to +200 (actual -36.1 to 49.9)
- Do NOT enforce sign consistency between employment_change and employment_change_pct
- Row count: exactly 832 (no rows added or dropped in Silver)

## Artifacts Produced

- `governance/eda/silver-bls-ooh-eda.md` -- Full EDA report with all field profiles and threshold recommendations

## Methodology

- Parsed raw XLSX through `BlsOohIngestor.flatten()` to replicate Bronze output
- Exported to CSV, loaded into DuckDB for statistical profiling
- Ran 14 profiling query groups covering all spec-required areas
- Cross-referenced findings against Bronze EDA and Silver spec
