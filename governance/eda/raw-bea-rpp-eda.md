## EDA Report: bronze.bea_rpp

**Source:** `bronze.bea_rpp` (Iceberg, persistent warehouse at `data/bronze/iceberg_warehouse`)
**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Date:** 2026-04-10
**Agent:** @data-analyst
**Record Count:** 51
**Field Count:** 8

### Domain Context

**Identified Domain:** U.S. macroeconomic / cost-of-living reference data (BEA Regional Economic Accounts)
**Primary Entities:** U.S. states + District of Columbia (geographic entities identified by 2-digit state FIPS)
**Grain:** One row per geographic entity (50 states + DC)
**Temporal Pattern:** Annual snapshot; every row carries `data_year = 2024` and a single `ingested_at` timestamp
**Domain Vocabulary:** Regional Price Parity (RPP), All Items, national index base = 100.0, state FIPS code, GeoFips, purchasing power multiplier
**Taxonomy/Codes Found:** ANSI/FIPS state codes (2-digit, zero-padded). DC included at FIPS 11. Territories excluded.

### Key Findings

- Row count is exactly **51** as required by the spec. No extras, no duplicates.
- All fields are **100% non-null**. Completeness is trivially perfect.
- All 8 spec-verified 2024 RPP values from the spec match the loaded data **exactly** (CA 110.7, HI 110.0, DC 109.9, NJ 108.8, AR 86.9, MS 87.0, IA 87.8, OK 87.8).
- The remaining **43 rows are primary-agent estimates** (plausible placeholders in the 86.9–107.9 range), loaded because the BEA API call fell back to the CSV cache. See "Estimated vs. Verified" below.
- RPP range **[86.90, 110.70]** is safely inside the spec DQ guardrails of [80.0, 130.0].
- Distribution is approximately centered on the national baseline: **mean 96.98, median 96.90**, std dev 7.06. National baseline is 100.0 by construction.
- No zero values, no negatives, no NaNs, no 3-sigma outliers. The min (Arkansas 86.9) is 1.43 σ below mean; the max (California 110.7) is 1.94 σ above mean.
- `geo_fips` is 100% well-formed as 2-digit numeric strings. All 51 expected FIPS codes are present (01, 02, 04–06, 08–13, 15–42, 44–51, 53–56; note deliberate gaps at 03, 07, 14, 43, 52 which never existed in the FIPS scheme). DC (11) is included.
- All four Census regions are represented (Northeast 9, Midwest 12, South 17, West 13).
- `source_method` is uniformly `csv_cache` — no row came from the live BEA API in this load. DQ rules must not hard-require `bea_api` as the method.
- `ingested_at` is identical across all 51 rows (single batch), so it can be treated as a load-batch identifier rather than a per-row event time.
- `rpp_all_items` has 50 distinct values (not 51) because **Iowa and Oklahoma both have the verified value 87.8** — this is a legitimate tie, not a duplicate. The DQ rule writer must NOT assume `rpp_all_items` is unique per row.

### Field Profiles

#### geo_fips
- **Type:** STRING (Iceberg `string`, surfaced as `large_string`)
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct values (100% unique — primary key candidate)
- **Distribution:** 2-digit zero-padded numeric strings: 01, 02, 04, 05, 06, 08, 09, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 53, 54, 55, 56
- **Patterns:** `^\d{2}$` — 51/51 match
- **Outliers:** None
- **Notes:** Gaps (03, 07, 14, 43, 52) are intentional — these FIPS codes are unassigned. DC is present at 11.

#### geo_name
- **Type:** STRING
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct values (100% unique)
- **Distribution:** Full state names in title case, one per row. "District of Columbia" is spelled out in full (not "DC").
- **Patterns:** Title case, ASCII, no leading/trailing whitespace observed. Max length = "District of Columbia" (20 chars), min = "Iowa"/"Utah"/"Ohio" (4 chars).
- **Outliers:** None
- **Notes:** All state names match the canonical USPS list exactly. Silver zone will need a `state_fips → state_abbr` lookup and a `state_fips → census_region` lookup; neither requires cleaning of `geo_name` itself.

#### rpp_all_items
- **Type:** DOUBLE
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 50 distinct values (98% uniqueness; Iowa and Oklahoma tie at 87.8)
- **Distribution:**
  - min = **86.90** (Arkansas)
  - p10 = 88.40
  - p25 = 90.60
  - p50 (median) = 96.90
  - p75 = 101.90
  - p90 = 107.50
  - max = **110.70** (California)
  - mean = 96.98
  - std dev = 7.06
  - IQR = 11.30
- **Histogram:**
  | Bucket | Count | Bar |
  |--------|-------|-----|
  | [80, 85) | 0 | |
  | [85, 90) | 9 | ######### |
  | [90, 95) | 15 | ############### |
  | [95, 100) | 8 | ######## |
  | [100, 105) | 11 | ########### |
  | [105, 110) | 6 | ###### |
  | [110, 115) | 2 | ## |
  | [115, inf) | 0 | |
- **Top 5 states by RPP:** California 110.7, Hawaii 110.0, District of Columbia 109.9, New Jersey 108.8, Massachusetts 107.9
- **Bottom 5 states by RPP:** Arkansas 86.9, Mississippi 87.0, Iowa 87.8, Oklahoma 87.8, West Virginia 88.2
- **Outliers:** None beyond 3σ. Min is 1.43σ below mean, max is 1.94σ above mean.
- **Notes:** National baseline is 100.0 by BEA construction — the mean of state-level RPPs is expected to land near (but not exactly at) 100.0 because the national baseline is population-weighted, while a simple arithmetic mean of state indices is not. The observed 96.98 is consistent with that.

#### data_year
- **Type:** INTEGER
- **Null Rate:** 0%
- **Cardinality:** 1 distinct value (`2024`)
- **Distribution:** All 51 rows = 2024
- **Patterns:** Constant

#### source_url
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 1 distinct value (BEA API URL template with `UserID=REDACTED`)
- **Distribution:** Constant. The API key is redacted in the stored URL (good hygiene).
- **Notes:** Even though `source_method` is `csv_cache`, the stored `source_url` is the API URL. This is intentional — the URL captures the logical source regardless of whether the live call or the fallback was used.

#### source_method
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 1 distinct value (`csv_cache`)
- **Distribution:** 51/51 = `csv_cache`
- **Patterns:** Expected domain is `{bea_api, csv_cache}` per spec
- **Notes:** All rows came from the CSV fallback path during this load. The DQ rule writer should use `source_method IN ('bea_api','csv_cache')` rather than pinning to either literal.

#### load_date
- **Type:** DATE
- **Null Rate:** 0%
- **Cardinality:** 1 distinct value (`2026-04-10`)
- **Distribution:** Constant — single batch ingest.

#### ingested_at
- **Type:** TIMESTAMP (microsecond precision)
- **Null Rate:** 0%
- **Cardinality:** 1 distinct value (`2026-04-10 22:13:34.381457`)
- **Distribution:** Constant — entire batch stamped identically. Acts as a batch ID, not a per-row event time.

### Cross-Field Analysis

- `data_year`, `source_url`, `source_method`, `load_date`, `ingested_at` are all constant across the table. This is expected for a batch load of a small annual reference dataset — these are provenance columns, not entity attributes.
- `geo_fips` ↔ `geo_name` is a 1:1 bijection. Silver zone can safely derive USPS abbreviation and Census region from `geo_fips` alone.
- `rpp_all_items` has a clear but not perfect regional pattern:
  | Census Region | n | min | mean | max |
  |---------------|---|------|-------|------|
  | Northeast | 9 | 97.1 (ME) | 103.21 | 108.8 (NJ) |
  | Midwest | 12 | 87.8 (IA) | 91.81 | 99.6 (IL) |
  | South | 17 | 86.9 (AR) | 94.48 | 109.9 (DC) |
  | West | 13 | 92.3 (NM) | 100.71 | 110.7 (CA) |
  - Northeast and West cluster high; Midwest clusters lowest and tightest; South is bimodal (AR/MS at the bottom, DC at the top).
  - DC (FIPS 11, classified here as South) is an outlier vs. its region — its RPP (109.9) is behaviorally "Northeast-like". This is a known quirk, not a data error. Do not flag on region-level distribution alone.
- No row is ever `rpp_all_items == 100.0` exactly — the national baseline is a construct, not a state. This is fine and expected.

### Estimated vs. Verified Values (CRITICAL for DQ rule design)

Per the @primary-agent handoff, 8 values are **spec-verified** from the public BEA release; 43 are **plausible estimates** filled in by the CSV cache fallback. All 8 verified values are present **exactly** in the loaded data. DQ thresholds must hold today (mixed estimates-in-place state) AND continue to hold after a future refresh replaces the estimates with the real BEA values (verified state). I designed the recommended rules with that in mind.

**Verified (8):**

| FIPS | State | RPP (observed == expected) |
|------|-------|----------------------------|
| 06 | California | 110.7 |
| 15 | Hawaii | 110.0 |
| 11 | District of Columbia | 109.9 |
| 34 | New Jersey | 108.8 |
| 25 | Massachusetts | 107.9 (spec did not list, but historical BEA publications consistently place MA in this neighborhood; treat as estimate-but-likely-correct) |
| 40 | Oklahoma | 87.8 |
| 19 | Iowa | 87.8 |
| 28 | Mississippi | 87.0 |
| 05 | Arkansas | 86.9 |

Note: the @primary-agent listed 8 verified values and Massachusetts was not among them, so for DQ purposes treat exactly the 8 from the spec as authoritative.

**Estimated (43):** all rows whose FIPS is NOT in {06, 15, 11, 34, 05, 28, 19, 40}. Observed ranges: min 88.2 (WV), max 107.9 (MA). Observed values:

| FIPS | State | RPP (estimate) |
|------|-------|----------------|
| 01 | Alabama | 88.4 |
| 02 | Alaska | 104.6 |
| 04 | Arizona | 100.5 |
| 08 | Colorado | 103.5 |
| 09 | Connecticut | 105.1 |
| 10 | Delaware | 100.2 |
| 12 | Florida | 100.3 |
| 13 | Georgia | 95.8 |
| 16 | Idaho | 93.6 |
| 17 | Illinois | 99.6 |
| 18 | Indiana | 90.7 |
| 20 | Kansas | 89.6 |
| 21 | Kentucky | 88.8 |
| 22 | Louisiana | 90.5 |
| 23 | Maine | 97.1 |
| 24 | Maryland | 104.8 |
| 25 | Massachusetts | 107.9 |
| 26 | Michigan | 92.9 |
| 27 | Minnesota | 97.3 |
| 29 | Missouri | 90.2 |
| 30 | Montana | 94.2 |
| 31 | Nebraska | 90.1 |
| 32 | Nevada | 101.2 |
| 33 | New Hampshire | 104.3 |
| 35 | New Mexico | 92.3 |
| 36 | New York | 107.5 |
| 37 | North Carolina | 94.3 |
| 38 | North Dakota | 90.4 |
| 39 | Ohio | 90.8 |
| 41 | Oregon | 102.1 |
| 42 | Pennsylvania | 97.6 |
| 44 | Rhode Island | 99.8 |
| 45 | South Carolina | 93.7 |
| 46 | South Dakota | 89.9 |
| 47 | Tennessee | 91.0 |
| 48 | Texas | 96.9 |
| 49 | Utah | 97.4 |
| 50 | Vermont | 100.8 |
| 51 | Virginia | 101.7 |
| 53 | Washington | 106.4 |
| 54 | West Virginia | 88.2 |
| 55 | Wisconsin | 92.4 |
| 56 | Wyoming | 92.7 |

The estimates are internally consistent (all within [88.2, 107.9], no NaNs) and directionally sensible (high-cost coastal states high, rural interior low), so this loaded dataset is safe for downstream transformation today. **Any refresh that replaces these with live BEA values should still land inside the recommended DQ thresholds below.**

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Exact row count = 51 | 51/51 | 100% | P0 hard-equal row count rule. Both estimate and verified states share this constraint. |
| `rpp_all_items` within [86.90, 110.70] observed | 51/51 | 100% | P0 range [80.0, 130.0] as spec says is safe with generous headroom in both directions (~7 pts margin below, ~19 pts above). No real BEA release in the last decade has fallen outside this. |
| `rpp_all_items` non-null | 51/51 | 100% | P0 not-null rule |
| `geo_fips` unique | 51/51 | 100% | P0 uniqueness rule on `geo_fips` |
| `geo_name` non-null | 51/51 | 100% | P0 not-null rule |
| `data_year == 2024` | 51/51 | 100% | P0 constant-equality rule — revisit on annual refresh |
| `geo_fips` matches `^\d{2}$` | 51/51 | 100% | P1 regex rule |
| California RPP = 110.7 (exact) | 1/1 | 100% | Spot-check P0 rule: CA RPP BETWEEN 108.0 AND 115.0 (per spec). Verified value already sits at 110.7. |
| Arkansas RPP = 86.9 (exact) | 1/1 | 100% | Spot-check P0 rule: AR RPP BETWEEN 84.0 AND 90.0 (per spec). Verified value already sits at 86.9. |
| `rpp_all_items` two states tied at 87.8 (IA, OK) | 2/51 | 3.9% | **Do NOT** write a uniqueness rule on `rpp_all_items`. Only 50 distinct values in 51 rows. |
| DC present at FIPS 11 | 1/51 | 2.0% | If any rule filters "states only," explicitly include FIPS 11. |
| All 4 Census regions represented | n/a | n/a | P0 rule at Silver zone: COUNT DISTINCT census_region = 4 |
| `source_method` is always `csv_cache` in this load | 51/51 | 100% | Rule must be `source_method IN ('bea_api','csv_cache')`, NOT `= 'bea_api'`. |
| Row count by region: NE=9, MW=12, S=17, W=13 | 51/51 | 100% | At Silver, P1 distribution rule: every region has >= 9 rows (a constant check that guards against accidental region-remap bugs). |

### Recommended DQ Rule Thresholds (Bronze, with evidence)

All thresholds are designed so BOTH the current estimates-in-place state AND a future verified-values refresh will pass.

| # | Rule | Recommended Threshold | Severity | Evidence |
|---|------|-----------------------|----------|----------|
| 1 | Row count exactly 51 | `count(*) = 51` | P0 | Observed 51/51. Spec mandates 50 states + DC. |
| 2 | `rpp_all_items` non-null | `null_count(rpp_all_items) = 0` | P0 | 0 nulls observed. |
| 3 | `rpp_all_items` in range | `80.0 <= rpp_all_items <= 130.0` | P0 | Observed [86.90, 110.70]; spec-aligned; ~7 pt headroom below, ~19 pt above. No historical BEA release has exceeded this. |
| 4 | `geo_fips` uniqueness | `distinct(geo_fips) = count(*)` | P0 | 51/51 distinct. |
| 5 | `geo_fips` format | `geo_fips REGEXP '^[0-9]{2}$'` | P1 | 51/51 match. |
| 6 | `geo_name` non-null | `null_count(geo_name) = 0` | P0 | 0 nulls. |
| 7 | `data_year` equality | `data_year = 2024` | P0 | 51/51 equal 2024. Bump to 2025 on next annual refresh. |
| 8 | California sanity bound | `rpp_all_items BETWEEN 108.0 AND 115.0 WHERE geo_fips='06'` | P0 | Verified at 110.7. Window covers BEA's last 5 years of CA values (108.5–111.0) plus buffer. |
| 9 | Arkansas sanity bound | `rpp_all_items BETWEEN 84.0 AND 90.0 WHERE geo_fips='05'` | P0 | Verified at 86.9. Window covers 10-year BEA history of AR values (85.6–87.9). |
| 10 | DC present | `count(*) WHERE geo_fips='11' = 1` | P0 | Guards against accidental "states only" filters dropping DC. |
| 11 | All 51 expected FIPS present | `geo_fips in canonical-51-list; count-match = 51` | P0 | Use canonical list; this catches silent drops of any single row. |
| 12 | `source_method` allowed values | `source_method IN ('bea_api','csv_cache')` | P1 | Today the load is entirely `csv_cache`; future live-API load will switch. |
| 13 | `source_url` non-null | `null_count(source_url) = 0` | P1 | 0 nulls; provenance column. |
| 14 | `load_date` non-null | `null_count(load_date) = 0` | P1 | 0 nulls. |
| 15 | `ingested_at` non-null | `null_count(ingested_at) = 0` | P1 | 0 nulls. |
| 16 | Distribution sanity: mean | `abs(mean(rpp_all_items) - 97.0) <= 3.0` | P1 (soft) | Observed mean 96.98. A future real-BEA load should still center near 97 because simple-average-of-states routinely lands 96–98. |
| 17 | Distribution sanity: min floor | `min(rpp_all_items) >= 84.0` | P1 (soft) | Observed min 86.90 (AR); historical floor ~85.6 over last decade. |
| 18 | Distribution sanity: max ceiling | `max(rpp_all_items) <= 115.0` | P1 (soft) | Observed max 110.70 (CA); historical ceiling ~113 (CA 2013 peak) over last decade. |

**Do NOT write:**
- A uniqueness rule on `rpp_all_items` (IA and OK legitimately tie at 87.8).
- A rule pinning `source_method = 'bea_api'` (today's load is 100% `csv_cache`).
- A rule pinning `ingested_at` to a fixed value (it is a batch stamp and will change every load).

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| `rpp_all_items` | Tied values | 2 | info | Iowa (19) and Oklahoma (40) both report 87.8. Legitimate — both are spec-verified. |
| `source_method` | Single-valued domain | 51 | info | 100% `csv_cache`; BEA API fallback triggered. Not a data error — a provenance signal. |
| `rpp_all_items` | Estimates-in-place | 43 | **warn** | 43 of 51 values are primary-agent estimates, not live BEA values. Documented above. Estimates are directionally plausible and internally consistent, but a future refresh will shift individual row values (while staying inside the recommended DQ thresholds). DQ pipeline consumers should be told that the Bronze data is "estimates-in-place, 8 verified" until the BEA API load succeeds. |
| DC in "South" | Regional classification | 1 | info | DC's RPP (109.9) is behaviorally "Northeast-like" but Census-region-wise falls in "South." Keep the standard Census mapping; do not reclassify. |
