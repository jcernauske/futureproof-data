## Audit Trail: BLS OOH EDA Analysis

**Date:** 2026-04-07  
**Agent:** @data-analyst  
**Spec:** raw-ingest-bls-ooh  
**Zone:** Bronze/Raw  

### What Was Analyzed
- Sample XLSX file: `tests/raw/bls_ooh_sample.xlsx` (10 detail rows + 1 summary row)
- Ingestor: `src/raw/bls_ooh_ingestor.py` (BlsOohIngestor class)
- Data loaded via `ingestor.fetch()` and `ingestor.flatten()` methods

### Key Findings
1. Summary row filtering works correctly (SOC 11-0000 filtered, 10 detail rows remain)
2. All SOC codes pass XX-XXXX format validation
3. Grain uniqueness holds (0 duplicates on soc_code)
4. Wage capping correctly identifies ">=239,200" as capped ($239,200, flag=true)
5. N/A wage correctly converts to null with capped=false
6. Employment thousands-to-actual conversion verified correct
7. Dollar-sign and comma stripping in wage parsing works correctly
8. All code-to-text mappings are deterministic and consistent

### Domain Discovery
- Domain: U.S. labor market / employment projections
- Taxonomy: SOC 2018 classification system
- Grain: one row per detailed occupation (SOC code)
- BLS education codes 1-8, work experience codes 1-3, training codes 1-6

### Threshold Recommendations
- All thresholds are PRELIMINARY (10-row sample)
- Must re-validate when full ~832-row dataset is ingested
- Key rules identified: SOC format, wage cap consistency, employment change allows negative, code range validation

### Artifacts Produced
- EDA report: `governance/eda/raw-bls-ooh-eda.md`
- Audit trail: this file
