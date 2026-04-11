# Audit: @data-analyst — raw-ingest-bea-rpp EDA

**Date:** 2026-04-10
**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Zone:** Bronze (post-ingest, pre-DQ-rule-writer)
**Artifact:** `governance/eda/raw-bea-rpp-eda.md`

## What I Did

- Loaded `bronze.bea_rpp` from the persistent Iceberg warehouse at `data/bronze/iceberg_warehouse/bronze/bea_rpp` via `pyiceberg.table.StaticTable.from_metadata` (the table is on disk as valid Iceberg metadata but is not currently registered in the project SQL catalog at `data/catalog/catalog.db` — reading the metadata file directly returned the same snapshot that was written by the ingestor).
- Confirmed schema matches the spec: `geo_fips:string, geo_name:string, rpp_all_items:double, data_year:int, source_url:string, source_method:string, load_date:date, ingested_at:timestamp`.
- Profiled all 51 rows: nulls, cardinality, full RPP distribution (min/max/mean/median/stdev/percentiles/histogram), top/bottom 5, Census region distribution, format checks on `geo_fips`, 3-sigma outlier scan, and constant-column detection.
- Verified the 8 spec-authoritative 2024 RPP values exactly match the loaded data.
- Catalogued the 43 estimates-in-place rows with their observed values so the DQ rule writer (and a future refresh review) can diff them.

## Key Findings

- **51 rows, zero nulls, zero format violations, zero outliers.** The ingest is structurally clean.
- **RPP range [86.90, 110.70]** — well inside the spec's P0 guardrail of [80.0, 130.0]. No state is anywhere near the edges.
- **Mean 96.98, median 96.90, std dev 7.06.** Simple-average-of-states centers slightly below the population-weighted national baseline of 100, which is expected.
- **8/8 spec-verified values match exactly** (CA 110.7, HI 110.0, DC 109.9, NJ 108.8, AR 86.9, MS 87.0, IA 87.8, OK 87.8). California and Arkansas both sit inside the spec's prescribed sanity windows.
- **43 rows are primary-agent estimates** because the ingest fell back to `csv_cache`. All estimates are directionally plausible, internally consistent, and observed in the range [88.2, 107.9]. I designed the recommended DQ thresholds so a future live-BEA refresh will still pass.
- **Iowa and Oklahoma tie at 87.8** (both verified). `rpp_all_items` has 50 distinct values for 51 rows. The DQ rule writer must NOT write a uniqueness rule on `rpp_all_items`.
- **All 51 rows came from `csv_cache`** — the DQ rule writer must use `source_method IN ('bea_api','csv_cache')` rather than pinning to either literal.
- **`data_year`, `source_url`, `source_method`, `load_date`, `ingested_at` are all constant across the table** — they are provenance/batch columns, not per-row attributes.
- **Census region distribution:** NE 9, MW 12, S 17, W 13 — all four regions represented. DC falls in "South" under standard Census mapping even though its RPP is Northeast-like; this is intentional, leave it.

## Recommendations to @dq-rule-writer

All 18 recommended rules are tabulated in `governance/eda/raw-bea-rpp-eda.md` under "Recommended DQ Rule Thresholds." Highlights:

- Row count `= 51` (P0)
- `rpp_all_items BETWEEN 80.0 AND 130.0` non-null (P0) — matches spec
- `geo_fips` uniqueness + `^\d{2}$` regex (P0 + P1)
- California spot-check `BETWEEN 108.0 AND 115.0` WHERE `geo_fips='06'` (P0)
- Arkansas spot-check `BETWEEN 84.0 AND 90.0` WHERE `geo_fips='05'` (P0)
- DC presence: `count(*) WHERE geo_fips='11' = 1` (P0)
- `data_year = 2024` (P0, bump on annual refresh)
- `source_method IN ('bea_api','csv_cache')` (P1, NOT pinned to either)
- Soft distribution guards: mean within 3.0 of 97.0; min >= 84.0; max <= 115.0 (P1)

Explicit NON-rules (things that look appealing but would be wrong):
- No uniqueness rule on `rpp_all_items` (IA/OK tie at 87.8).
- No literal equality rule on `source_method`.
- No `ingested_at` constant check (batch timestamp rotates every load).

## Notes for @dq-engineer and @semantic-modeler

- The bronze Iceberg table is on disk but not registered in the SQL catalog. `@primary-agent` or `@dq-engineer` may want to (re-)register it in `data/catalog/catalog.db` so downstream agents can `load_table("bronze.bea_rpp")` through the normal catalog path.
- Silver zone will need static `state_fips → state_abbr` and `state_fips → census_region` lookups. My region mapping used in this EDA follows standard U.S. Census Bureau definitions (NE: CT, ME, MA, NH, NJ, NY, PA, RI, VT; MW: IL, IN, IA, KS, MI, MN, MO, NE, ND, OH, SD, WI; S: AL, AR, DE, DC, FL, GA, KY, LA, MD, MS, NC, OK, SC, TN, TX, VA, WV; W: AK, AZ, CA, CO, HI, ID, MT, NV, NM, OR, UT, WA, WY).
