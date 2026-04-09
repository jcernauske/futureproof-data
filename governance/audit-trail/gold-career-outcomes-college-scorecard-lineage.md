# Lineage Tracker Audit Trail: gold-career-outcomes-college-scorecard

**Agent:** @lineage-tracker
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Timestamp:** 2026-04-06T22:00:00Z
**Session:** Lineage capture for Gold zone career outcomes transformation

## Transformations Captured

### 1. Identity Fields (9 fields) — DIRECT carry-forward from Silver
- `unitid`, `institution_name`, `institution_control`, `cipcode`, `program_name`, `cip_family`, `cip_family_name`, `credential_level`, `source_load_date`
- All carried directly from `base.college_scorecard` with no value transformation

### 2. Column Rename (1 field) — DIRECT with rename
- `completions_count_1` → `completions_count`: Rename in GOLD_SQL base CTE

### 3. CIP-Family Percentile Bands (6 fields) — AGGREGATION
- `earnings_1yr_p25`, `earnings_1yr_p75`, `earnings_2yr_p25`, `earnings_2yr_p75`, `debt_p25`, `debt_p75`
- PERCENTILE_CONT window functions partitioned by `cip_family`
- Minimum sample guard: CIP families with < 3 non-null values for a given metric get null percentile bands
- Implementation: `cip_counts` CTE counts non-nulls, `cip_bands` CTE computes percentiles with CASE guard

### 4. Financial Ratios (3 fields) — DERIVED
- `debt_to_earnings_annual`: `debt_median / earnings_1yr_median` (null-safe)
- `earnings_growth_rate`: `(earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median` (null-safe)
- `program_value_index`: `earnings_1yr_median / debt_median` (null-safe)

### 5. Tiered Classifications (2 fields) — DERIVED
- `debt_to_earnings_tier`: Bucketed from debt_to_earnings_annual (Low/Moderate/High/Very High)
- `confidence_tier`: Composite of small_cohort_flag + has_earnings + has_debt

### 6. Relative Position (1 field) — AGGREGATION
- `cip_family_earnings_rank`: PERCENT_RANK() partitioned by cip_family, ordered by earnings_1yr_median
- Only rows with non-null earnings participate (LEFT JOIN from base)

### 7. Convenience/Quality Flags (3 fields) — DERIVED
- `has_earnings`: OR of earnings_1yr_median and earnings_2yr_median nullity
- `has_debt`: debt_median nullity check
- `outcome_completeness`: count non-null / 3.0, snapped to {0.0, 0.33, 0.67, 1.0}

### 8. Generated Metadata (2 fields) — DERIVED
- `record_id`: compute_grain_id with prefix 'co' on grain fields [unitid, cipcode, credlev]
- `promoted_at`: UTC timestamp at promotion time

## Dropped Fields (from Silver)
| Field | Reason |
|-------|--------|
| completions_count_2 | Second-major completions not relevant to career outcomes |
| credential_description | Redundant with credential_level in MVP scope |
| ingested_at | Silver metadata replaced by promoted_at in Gold |
| record_id (Silver) | Re-computed with Gold prefix 'co' (was 'cs' in Silver) |

## Naming Decisions
- **Job name:** `gold.transform-career-outcomes` — follows `{zone}.{transformation-name}` convention
- **Input dataset:** `base.college_scorecard` — Silver zone table name from Iceberg catalog
- **Output dataset:** `consumable.career_outcomes` — Gold zone table name per spec
- **Run ID:** UUID v4 `c7e29a14-5b83-4d1f-a6c0-8f2d4e7b3a91`

## Interpretation Notes
- The SQL in `GOLD_SQL` runs entirely in DuckDB over an Arrow table registered as `silver`. All transformations happen in a single SQL statement with CTEs, but lineage is captured per output field for traceability.
- `_snap_outcome_completeness()` is a Python post-processing step applied after DuckDB execution — captured in the outcome_completeness lineage as part of the transformation description.
- The grain hash uses `credlev` as the key name (not `credential_level`) because the spec defines grain fields as `[unitid, cipcode, credlev]`. The transformer maps `credential_level` to `credlev` in the grain dict before hashing.

## Output Artifact
- `governance/lineage/gold-career-outcomes-college-scorecard-20260406T220000Z.json`
