# Audit Trail: Lineage Capture — silver-base-bls-ooh

**Agent:** @lineage-tracker
**Spec:** silver-base-bls-ooh
**Timestamp:** 2026-04-07T21:00:00Z
**Lineage File:** `governance/lineage/silver-base-bls-ooh-20260407T210000Z.json`

## Transformations Captured

All 12 transformations from the spec were captured with full column-level lineage:

1. **Read Bronze table** — documented as job input (bronze.bls_ooh, 19 fields)
2. **Validate SOC code format** — captured in soc_code lineage (strip + regex validation)
3. **Derive SOC major group** — captured (soc_code[:2] extraction)
4. **Derive SOC major group name** — captured (22-entry SOC_MAJOR_GROUP_LOOKUP)
5. **Derive broad_occupation_flag** — captured (hardcoded 7-code BROAD_OCCUPATION_CODES frozenset)
6. **Derive catchall_flag** — captured (case-insensitive "all other" substring match)
7. **Derive growth_category** — captured (6-tier bucketing of employment_change_pct)
8. **Derive wage_available** — captured (median_annual_wage is not None)
9. **Derive education_level_name** — captured (8-entry EDUCATION_LEVEL_LOOKUP)
10. **Rename load_date to source_load_date** — captured as DIRECT with rename note
11. **Compute record_id** — captured (compute_grain_id with 'ooh' prefix on soc_code grain)
12. **Promote to base.bls_ooh** — documented in job description and runtime metrics

## Dropped Fields Documented

- source_url: raw metadata not needed in Silver
- source_method: raw metadata not needed in Silver

## Field Count Verification

- Input schema: 19 fields (bronze.bls_ooh)
- Output schema: 25 fields (base.bls_ooh)
- Derived fields: 8 (record_id, soc_major_group, soc_major_group_name, broad_occupation_flag, catchall_flag, growth_category, wage_available, education_level_name)
- Renamed fields: 1 (load_date -> source_load_date)
- Dropped fields: 2 (source_url, source_method)
- Direct pass-through: 14 fields
- New generated: 1 (ingested_at — Silver-zone timestamp, no Bronze input)
- Balance check: 19 input - 2 dropped + 8 derived + 1 generated = 26, but Bronze ingested_at is NOT carried forward (Silver generates its own) so effective: 18 carried - 1 renamed + 8 derived + 1 generated = 25 output fields. Correct.

## Naming Decisions

- **Input namespace:** `bronze.bls_ooh` (matches the actual Iceberg namespace/table used in the transformer code: `bronze_catalog.load_table("bronze.bls_ooh")`)
- **Output namespace:** `base.bls_ooh` (matches Silver catalog table: `get_or_create_table(silver_catalog, "base", "bls_ooh", ...)`)
- **Job name:** `silver.transform-bls-ooh` (follows convention from silver-base-college-scorecard lineage)

## Notes

- The Bronze table uses namespace `bronze.bls_ooh` in the Iceberg catalog, not `raw.bls_ooh`. The lineage file uses `bronze.bls_ooh` to match the actual catalog reference in the transformer code.
- Runtime metrics (snapshotId) left as null since this lineage was captured from code inspection, not from a live pipeline run. A future runtime emission should backfill the snapshot ID.
- The Bronze ingested_at field is not carried to Silver; Silver generates its own ingested_at independently. This is documented in the ingested_at column lineage with an empty inputFields array.
