# Lineage Tracker Audit — silver-base-karpathy-ai-exposure

- **Date:** 2026-04-09
- **Agent:** @lineage-tracker
- **Spec:** silver-base-karpathy-ai-exposure
- **Lineage File:** `governance/lineage/silver-base-karpathy-ai-exposure-20260409T160000Z.json`

## Transformations Captured

All 11 output fields in `base.karpathy_ai_exposure` have column-level lineage recorded:

| Output Field | Type | Source(s) |
|---|---|---|
| record_id | DERIVED | bronze.soc_code or bronze.slug (conditional grain hash) |
| soc_code | DERIVED | bronze.soc_code + base.bls_ooh (multi-path resolution) |
| slug | DIRECT | bronze.slug |
| occupation_title | DIRECT | bronze.occupation_title |
| category | DIRECT | bronze.category |
| exposure_score | DIRECT | bronze.exposure_score (int cast) |
| rationale | DIRECT | bronze.rationale |
| bls_match | DERIVED | bronze.soc_code + base.bls_ooh.soc_code |
| soc_resolved_method | DERIVED | bronze.soc_code + base.bls_ooh (resolution path classification) |
| source_load_date | DIRECT | bronze.load_date (renamed) |
| ingested_at | DERIVED | framework-generated UTC timestamp |

## Dropped Fields Documented

6 Bronze fields not carried to Silver: median_pay_annual, num_jobs_2024 (used internally for dedup then dropped), entry_education, source_url, source_method, ingested_at (replaced by Silver timestamp).

## Row Count Lineage

342 Bronze input rows -> 419 Silver output rows. Increase due to broad SOC expansion (~70 rows) and title matching (~28 rows), partially offset by deduplication.

## Reference Table Usage

base.bls_ooh used as REFERENCE input (not row-for-row join). Three lookup structures built: SOC code set, title-to-SOC map, prefix-to-detailed-codes map.

## Naming Decisions

- **Job name:** `silver.transform-karpathy-ai-exposure` — follows `{zone}.{action}-{source}` convention established by `silver.transform-bls-ooh`.
- **Dataset names:** `bronze.karpathy_ai_exposure` and `base.karpathy_ai_exposure` — follow existing `{zone}.{table}` convention.
- **Run ID:** UUID v4 `a7f3c812-4d6e-48b1-9a25-3e8b1c5f7d09`.

## Interpretation Notes

- The `soc_code` output field has the most complex lineage: four distinct resolution paths (direct, title_match, broad_expansion, unresolved) each with different source field dependencies. Documented as DERIVED rather than DIRECT because the value may differ from the Bronze input.
- `num_jobs_2024` is used internally as a dedup tiebreaker (`_num_jobs_2024` temporary field) but is not persisted. Documented in droppedFields with explanation.
- `bls_match` for title_match rows is always True by construction, since matches come from the BLS title lookup. Noted in the lineage description.
