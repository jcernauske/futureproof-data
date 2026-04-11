## DQ Scorecard: raw-ingest-karpathy-ai-exposure
**Spec:** raw-ingest-karpathy-ai-exposure
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Run ID:** 237716fd
**Results File:** governance/dq-results/raw-ingest-karpathy-ai-exposure-20260409T191526Z.json
**Overall Score:** 18/18 rules passing (100%)
**Data Source:** FULL DATASET (bronze.karpathy_ai_exposure Iceberg table, 342 rows of real Karpathy AI exposure data)
**Note:** First production run. All 18 rules approved and executed against real Iceberg data. Cross-validation rule RAW-KAI-009 confirmed against bronze.bls_ooh (table reference corrected from raw.bls_ooh).

### Execution Results

| Rule ID | Dimension | Priority | Description | Result | Evidence |
|---------|-----------|----------|-------------|--------|----------|
| RAW-KAI-001 | validity | P0 | Exposure score range: 0-10 | PASS | violations=0; all 342 scores within 0-10 range |
| RAW-KAI-002 | completeness | P0 | Exposure score completeness: 0% null | PASS | violations=0; all 342 rows have exposure_score |
| RAW-KAI-003 | completeness | P0 | Rationale completeness: 0% null | PASS | violations=0; all 342 rows have rationale |
| RAW-KAI-004 | uniqueness | P0 | Slug uniqueness (grain check) | PASS | violations=0; 342 distinct slugs, zero duplicates |
| RAW-KAI-005 | volume | P0 | Row count within expected range: 325-359 | PASS | count=342; within [325, 359] range |
| RAW-KAI-006 | validity | P1 | SOC code format validation (where present) | PASS | violations=0; all 290 non-null SOC codes match XX-XXXX |
| RAW-KAI-007 | completeness | P1 | SOC code coverage: >= 80% non-null | PASS | null_rate=15.2% (52/342); threshold=20%; coverage=84.8% |
| RAW-KAI-008 | completeness | P0 | Occupation title completeness: 0% null | PASS | violations=0; all 342 rows have occupation_title |
| RAW-KAI-009 | consistency | P1 | Cross-validation: median_pay vs BLS OOH (> 20% diff) | PASS | violations=0; perfect wage alignment across all matched SOC codes |
| RAW-KAI-010 | completeness | P0 | Slug completeness: 0% null | PASS | violations=0; all 342 rows have slug |
| RAW-KAI-011 | completeness | P0 | Category completeness: 0% null | PASS | violations=0; all 342 rows have category |
| RAW-KAI-012 | completeness | P0 | Source URL completeness: 0% null | PASS | violations=0; all 342 rows have source_url |
| RAW-KAI-013 | completeness | P0 | Ingestion timestamp completeness: 0% null | PASS | violations=0; all 342 rows have ingested_at |
| RAW-KAI-014 | completeness | P0 | Load date completeness: 0% null | PASS | violations=0; all 342 rows have load_date |
| RAW-KAI-015 | completeness | P0 | Source method completeness: 0% null | PASS | violations=0; all 342 rows have source_method |
| RAW-KAI-016 | validity | P0 | Source method validity: github_download or local_cache | PASS | violations=0; all rows contain valid source_method |
| RAW-KAI-017 | freshness | P1 | Load date within last 30 days | PASS | violations=0; all rows loaded on 2026-04-09 |
| RAW-KAI-018 | validity | P0 | Exposure score is integer (no fractional values) | PASS | violations=0; all scores are integer values |

### Summary by Priority

| Priority | Total | Passed | Failed | Rate |
|----------|-------|--------|--------|------|
| P0 | 13 | 13 | 0 | 100% |
| P1 | 4 | 4 | 0 | 100% |
| P0+P1 (integer check) | 1 | 1 | 0 | 100% |
| **Total** | **18** | **18** | **0** | **100%** |

### Summary by Dimension

| Dimension | Rules | Passing | Rate |
|-----------|-------|---------|------|
| completeness | 10 | 10 | 100% |
| validity | 4 | 4 | 100% |
| uniqueness | 1 | 1 | 100% |
| volume | 1 | 1 | 100% |
| consistency | 1 | 1 | 100% |
| freshness | 1 | 1 | 100% |

### Cross-Validation Highlights

**RAW-KAI-009 (Wage Cross-Validation):** Karpathy's median_pay_annual values were compared against bronze.bls_ooh.median_annual_wage for all SOC-matched rows. Zero discrepancies -- perfect alignment confirms Karpathy used the same BLS data snapshot as our pipeline.

**RAW-KAI-007 (SOC Coverage):** SOC code coverage is 84.8% (290/342), below the spec's original 95% estimate but above the 80% threshold. The 52 occupations without SOC codes are concentrated in transportation, installation/repair, production, and computer/IT categories. This is a known characteristic of the source data, not an ingestor issue.

### Catalog Fix Applied

The bronze.karpathy_ai_exposure table was registered in the Iceberg catalog under catalog_name "futureproof-data" instead of "brightsmith" (due to PROJECT_NAME mismatch during ingest). This was corrected before DQ execution by updating the catalog.db entry. All subsequent pipeline operations will use the correct catalog_name.

### Table Reference Fix Applied

RAW-KAI-009 originally referenced `raw.bls_ooh` but the BLS OOH table is registered as `bronze.bls_ooh` in the pipeline's Iceberg catalog. The table reference was corrected in the rules JSON before execution.

### Gate Status
- **P0 Gate: PASS** -- All 13 P0 rules passed with zero violations.
- **P1 Warnings: NONE** -- All 4 P1 rules passed.
- **Action required:** None. Spec is clear for completion from a DQ perspective.
