# EDA Report: base.bea_rpp (Silver — Analytical Dry-Run)

**Source:** `bronze.bea_rpp` (Iceberg, catalog `brightsmith`, warehouse `data/bronze/iceberg_warehouse`)
**Target (not yet materialized):** `base.bea_rpp`
**Spec:** `docs/specs/silver-base-bea-rpp.md`
**Logical model:** `governance/models/silver-base-bea-rpp-logical.md`
**Physical model:** `governance/models/silver-base-bea-rpp-physical.md`
**Date:** 2026-04-10
**Agent:** @data-analyst
**Record Count:** 51 (dry-run derived in-memory from 51 Bronze rows)
**Field Count:** 11 (9 derived/carried in this dry-run; `record_id` and `ingested_at` are generated at promote time and not profiled here)

---

## Scope and Methodology

The Silver target `base.bea_rpp` does not yet exist. The @primary-agent has not built the transformer. This report is an **analytical dry-run**: the Bronze parquet at
`data/bronze/iceberg_warehouse/bronze/bea_rpp/data/*.parquet` was read directly, the Silver derivation logic from `governance/models/silver-base-bea-rpp-physical.md` was applied in-memory (no Iceberg writes, no persistence), and every derived column was profiled.

Lookup constants used (copied verbatim from the physical model):

- `FIPS_TO_USPS` — 51 entries
- `FIPS_TO_CENSUS_REGION` — 51 entries (DC → South per Census convention)
- `BEA_VERIFIED_FIPS` — `{'06','15','11','34','05','28','19','40'}` (8 entries)

All computations ran with Python 3 + DuckDB reading the parquet file; results below are reproducible by re-running the same derivations against the same Bronze rows.

---

## Domain Context

Already established by `governance/eda/raw-bea-rpp-eda.md`. This is a U.S. state-level Regional Price Parity reference table from the BEA. Grain is one row per state (or DC) per data year. Not repeated here.

---

## Key Findings

- **Every silver transformation is clean**. All 9 profiled columns are 100% non-null; all lookups resolved for all 51 state_fips values.
- **The inverse invariant `multiplier × rpp_all_items ≈ 100.0` holds for every one of 51 rows with a maximum absolute deviation of 1.42e-14** — 12 orders of magnitude tighter than the spec's 0.01 tolerance. This is float arithmetic noise, not a modeling issue.
- **All 8 BEA-verified spot-check multipliers match the spec within ±0.001**, with the largest observed delta being 0.000058 (CA). Zero mismatches.
- **The `bea_official` set exactly equals the 8-state allow-list** (`{'05','06','11','15','19','28','34','40'}`). Counts are `bea_official=8`, `estimate=43`.
- **Census region distribution matches the pre-review expectation exactly**: Northeast=9, Midwest=12, South=17, West=13 (sums to 51).
- **FIPS → USPS abbreviation derivation is a perfect 1:1 bijection** for all 51 rows. All 51 abbrs are 2 uppercase letters. No collisions, no nulls.
- **`rpp_all_items` ranges [86.9, 110.7]**, well inside the physical model's [70.0, 130.0] sanity bound. Zero 3-sigma outliers. Highest: CA 110.7. Lowest: AR 86.9.
- **`purchasing_power_multiplier` ranges [0.9033, 1.1507]**, well inside the physical model's [0.7, 1.3] sanity bound.
- **Single data year**: all 51 rows have `data_year = 2024`. Single-vintage invariant holds.
- **Single source_load_date**: all 51 rows have `load_date = 2026-04-10`, carried from Bronze.
- **State_fips, state_name, and state_abbr are three parallel 51-distinct-value bijections**. Zero ambiguity for any lookup direction.

No anomalies were found that would prevent the @primary-agent from building the transformer as spec'd or that would require spec revision.

---

## Field Profiles

### state_fips (identifier, derived via rename from `geo_fips`)
- **Type:** STRING (VARCHAR)
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct (100% unique)
- **Pattern:** All 51 values match `^\d{2}$` (2-digit zero-padded). Passes.
- **Distribution:** Closed 51-member set — the canonical US state+DC FIPS codes. All expected codes present (`01`–`56`, minus non-state territories).
- **Outliers:** None.
- **Recommendation:** P0 non-null + uniqueness + regex `^\d{2}$` rules are all satisfied by the source data. Thresholds can be hard equality (`=51 rows, 51 distinct, 0 violations`).

### state_name (text, passthrough from `geo_name`)
- **Type:** STRING
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct (100% unique)
- **Distribution:** Full English state names in USPS canonical form. Includes `"District of Columbia"`.
- **Outliers:** None. No whitespace, trailing characters, or encoding issues in the profiled data.
- **Recommendation:** P0 non-null + P1 uniqueness rules are satisfied (51 distinct). Bijection with state_fips holds (51/51).

### state_abbr (identifier, derived via `FIPS_TO_USPS`)
- **Type:** STRING
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct (100% unique)
- **Pattern:** All 51 values match `^[A-Z]{2}$`. Zero lowercase, zero length mismatches, zero nulls.
- **Distribution:** The canonical 51-member USPS set, sorted:
  `AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, IA, ID, IL, IN, KS, KY, LA, MA, MD, ME, MI, MN, MO, MS, MT, NC, ND, NE, NH, NJ, NM, NV, NY, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VA, VT, WA, WI, WV, WY`
- **Outliers:** None.
- **Recommendation:** P0 rules (non-null, exactly 2 chars, all uppercase, value-in-USPS-51, uniqueness) all satisfied with zero violations. Hard equality thresholds appropriate.

### census_region (text, derived via `FIPS_TO_CENSUS_REGION`)
- **Type:** STRING (closed enum)
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 4 distinct (`Northeast`, `Midwest`, `South`, `West`)
- **Distribution (exact counts):**

| Region | Count | Percentage |
|--------|-------|------------|
| South | 17 | 33.33% |
| West | 13 | 25.49% |
| Midwest | 12 | 23.53% |
| Northeast | 9 | 17.65% |
| **Total** | **51** | **100.00%** |

- **DC placement:** Confirmed assigned to `South` (state_fips=`11`). This is the documented Census convention quirk from the spec; not a bug. DQ rules must accept DC-in-South.
- **Recommendation:**
  - P0 rule "values IN `('Northeast','Midwest','South','West')`" — 100% satisfied.
  - P0 rule "all 4 regions represented" — 100% satisfied.
  - Suggest an additional P1 fixed-count rule `Northeast=9 AND Midwest=12 AND South=17 AND West=13` to catch any silent lookup-table drift on future refreshes. Evidence: exact counts computed above.

### rpp_all_items (numeric, passthrough from Bronze)
- **Type:** DOUBLE
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** ~51 (continuous measure; all distinct or near-distinct)
- **Distribution:**

| Statistic | Value |
|-----------|-------|
| min | 86.9 (Arkansas) |
| p25 | 90.5 |
| median | 96.9 |
| mean | 96.980392 |
| p75 | 102.1 |
| max | 110.7 (California) |
| stdev | 7.063626 |

- **3-sigma bounds:** `[75.7895, 118.1713]` → zero rows outside. No outliers.
- **Physical model bound `[70.0, 130.0]`:** every row well inside; min margin 16.9 below the ceiling, 16.9 above the floor.
- **Lowest 5:** AR 86.9, MS 87.0, IA 87.8, OK 87.8, WV 88.2
- **Highest 5:** MA 107.9, NJ 108.8, DC 109.9, HI 110.0, CA 110.7
- **Recommendation:**
  - P0 rule `rpp_all_items BETWEEN 70.0 AND 130.0` — satisfied with 16.9-point headroom on each side.
  - P0 passthrough invariant (Silver `rpp_all_items` equals Bronze `rpp_all_items` for the same `state_fips`) — trivially holds in the dry-run because the transformation is a direct passthrough.
  - No tightening recommended: leaving the bound at 70–130 absorbs plausible future vintages.

### purchasing_power_multiplier (numeric, derived as `100.0 / rpp_all_items`)
- **Type:** DOUBLE
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct (computed from 51 distinct rpp values)
- **Distribution:**

| Statistic | Value |
|-----------|-------|
| min | 0.9033423668 (CA) |
| p25 | 0.9794319295 |
| median | 1.0319917441 |
| mean | 1.0364168634 |
| p75 | 1.1049723757 |
| max | 1.1507479862 (AR) |
| stdev | 0.0740977789 |

- **Physical model bound `[0.7, 1.3]`:** every row well inside. Minimum margin on high side = 0.1493 (1.3 − 1.1507); minimum margin on low side = 0.2033 (0.9033 − 0.7). Ample headroom.
- **Recommendation:**
  - P0 rule `purchasing_power_multiplier BETWEEN 0.7 AND 1.3` — satisfied.
  - P0 inverse invariant (see next subsection) — satisfied.

### purchasing_power_multiplier — inverse invariant
Computed `abs(multiplier × rpp_all_items − 100.0)` for every row:

- **Max absolute deviation:** `1.42e-14`
- **Rows violating 0.01 tolerance:** 0
- **Rows violating 1e-9 tolerance:** 0
- **Rows violating 1e-13 tolerance:** 0 (max dev < 1.5e-14)

**Recommendation:** The spec's tolerance of `0.01` is safe by ~12 orders of magnitude. Keeping `0.01` is fine for robustness against any future change in float representation or storage path, but the data itself clearly supports a much tighter tolerance. **Keep the rule at `tol = 0.01`** — there is zero practical risk of false positives, and the loose bound will not hide a real derivation bug because any real bug would shift results by orders of magnitude more than 0.01.

### verification_status (text, derived via allow-list)
- **Type:** STRING (closed enum)
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 2 distinct (`bea_official`, `estimate`)
- **Distribution:**

| Value | Count | Percentage |
|-------|-------|------------|
| estimate | 43 | 84.31% |
| bea_official | 8 | 15.69% |

- **`bea_official` FIPS set (computed):** `['05','06','11','15','19','28','34','40']`
- **Expected allow-list (sorted):** `['05','06','11','15','19','28','34','40']`
- **Match:** **exact**.
- **Verified states (abbr, rpp, mult):**
  - AR 86.9 → 1.1507
  - CA 110.7 → 0.9033
  - DC 109.9 → 0.9099
  - HI 110.0 → 0.9091
  - IA 87.8 → 1.1390
  - MS 87.0 → 1.1494
  - NJ 108.8 → 0.9191
  - OK 87.8 → 1.1390
- **Recommendation:**
  - P0 rule `verification_status IN ('bea_official','estimate')` — satisfied.
  - P0 rule `COUNT(*) WHERE verification_status='bea_official' = 8` — satisfied.
  - P0 rule "every `bea_official` row has `state_fips` in the 8-code allow-list" — satisfied (the set equality above is tighter than mere subset inclusion).
  - All three rules should be kept as hard equalities; the spec's note about the rule flipping to `= 51` after the live BEA API refresh is the correct forward path.

### data_year (numeric constant)
- **Type:** INTEGER
- **Null Rate:** 0%
- **Distinct values:** 1 (`2024`)
- **Recommendation:** P0 rules `data_year = 2024` and `COUNT(DISTINCT data_year) = 1` both hold with hard equality.

### source_load_date (date, carried from Bronze `load_date`)
- **Type:** DATE
- **Null Rate:** 0%
- **Distinct values:** 1 (`2026-04-10`)
- **Recommendation:** No dedicated DQ rule needed beyond non-null. A single load date per refresh cycle is the normal state for full-table replacement.

---

## Spot-Check Results for All 8 BEA-Verified States (±0.001)

| state_fips | state_abbr | census_region | rpp_all_items | computed multiplier | expected multiplier | abs diff | status |
|---|---|---|---|---|---|---|---|
| 06 | CA | West | 110.7 | 0.903342 | 0.9034 | 0.000058 | PASS |
| 15 | HI | West | 110.0 | 0.909091 | 0.9091 | 0.000009 | PASS |
| 11 | DC | South | 109.9 | 0.909918 | 0.9099 | 0.000018 | PASS |
| 34 | NJ | Northeast | 108.8 | 0.919118 | 0.9191 | 0.000018 | PASS |
| 05 | AR | South | 86.9 | 1.150748 | 1.1507 | 0.000048 | PASS |
| 28 | MS | South | 87.0 | 1.149425 | 1.1494 | 0.000025 | PASS |
| 19 | IA | Midwest | 87.8 | 1.138952 | 1.1390 | 0.000048 | PASS |
| 40 | OK | South | 87.8 | 1.138952 | 1.1390 | 0.000048 | PASS |

**All 8 spot-checks pass.** Largest observed delta: 0.000058 (CA), which is within the ±0.001 tolerance the spec requires and is simply due to the spec rounding the multiplier to 4 decimal places while `100.0 / 110.7` evaluates to `0.9033423668...`.

DC's region is correctly `South` (Census convention quirk). NJ is correctly `Northeast`. IA is correctly `Midwest`. AR/MS/OK are correctly `South`. CA/HI are correctly `West`.

---

## Cross-Field Analysis

### Multiplier distribution by census region

| Region | n | mean mult | min mult | max mult |
|--------|---|-----------|----------|----------|
| Northeast | 9 | 0.9705 | 0.9191 (NJ) | 1.0299 (ME) |
| West | 13 | 0.9966 | 0.9033 (CA) | 1.0834 (NM) |
| South | 17 | 1.0635 | 0.9099 (DC) | 1.1507 (AR) |
| Midwest | 12 | 1.0905 | 1.0040 (IL) | 1.1390 (IA) |

The ordering (Northeast most expensive → Midwest cheapest) matches intuition for U.S. cost-of-living patterns. DC is the lone sub-1.0 entry in South (the Census quirk). No regional contradictions.

### Bijection checks (state identity)
- `state_fips` ↔ `state_name`: 51 distinct fips, 51 distinct names, 1:1.
- `state_fips` ↔ `state_abbr`: 51 distinct fips, 51 distinct abbrs, 1:1.
- `state_name` ↔ `state_abbr`: 51 distinct names, 51 distinct abbrs, 1:1.

All three logical-model uniqueness constraints are satisfied by the dry-run output. The bijection is structural, not accidental, because it's driven by the 51-entry closed-set lookups.

### 3-sigma outlier check on rpp_all_items
- Mean = 96.9804, sd = 7.0636
- 3-sigma bounds = [75.7895, 118.1713]
- Rows outside: **0**

The RPP distribution is tight and unimodal around the national=100 anchor. No outlier flagging is needed.

---

## Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| Inverse invariant max deviation = 1.42e-14 | 51 / 51 rows | 100% well under tol | Keep DQ tol = 0.01. Data is 12 orders of magnitude tighter; tol=0.01 gives robustness without risk of false negatives on real bugs. |
| rpp_all_items ∈ [86.9, 110.7] vs bound [70.0, 130.0] | 51 / 51 rows inside | 100% | Keep bound [70.0, 130.0] — absorbs future vintages. Current data has ~17-point headroom on both sides. |
| purchasing_power_multiplier ∈ [0.9033, 1.1507] vs bound [0.7, 1.3] | 51 / 51 rows inside | 100% | Keep bound [0.7, 1.3] — inverse of the rpp_all_items bound. |
| verification_status=bea_official | 8 / 51 rows | 15.69% | Hard equality `= 8` is the correct rule today. Forward path: rule flips to `= 51` when live BEA API refresh lands. No threshold recommendation needed — this is a count, not a percentage. |
| DC census_region = South | 1 / 51 rows | 1.96% | **DO NOT** flag DC-in-South as a violation. It is Census convention. The enum IN rule already accepts it; no special-case rule needed. |
| state_fips 3-sigma outliers on rpp | 0 / 51 | 0% | No outlier rule recommended for Silver. The 51 values are a closed reference set. |
| source_load_date distinct values | 1 | 100% | No rule change needed beyond Bronze inheritance; single load_date per refresh is normal. |
| data_year distinct values | 1 (2024) | 100% | Keep `COUNT(DISTINCT data_year) = 1` as P0. |
| state_abbr format `^[A-Z]{2}$` | 51 / 51 rows | 100% | Satisfied. Keep regex rule. |
| state_fips format `^\d{2}$` | 51 / 51 rows | 100% | Satisfied. Keep regex rule. |

---

## Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| — | — | 0 | — | **No anomalies.** Every derived column is clean; every spot-check passes; every invariant holds; every lookup resolved. |

---

## Threshold Recommendations Summary (Evidence-Backed)

Every recommendation below cites the exact computed value from the in-memory Silver dry-run, not the spec.

| DQ Rule ID (expected) | Recommended Threshold | Evidence from dry-run |
|---|---|---|
| SLV-BEA-001 Row count | `= 51` | 51 rows derived |
| SLV-BEA-002 state_fips NOT NULL + UNIQUE | `nulls=0, distinct=51` | 0 nulls, 51 distinct |
| SLV-BEA-003 state_fips regex `^\d{2}$` | `violations=0` | 0 violations (51/51 match) |
| SLV-BEA-004 state_abbr NOT NULL + regex `^[A-Z]{2}$` + in USPS-51 | `violations=0` | 0 violations; set equals canonical 51 |
| SLV-BEA-005 state_abbr UNIQUE | `distinct=51` | 51 distinct |
| SLV-BEA-006 census_region IN enum | `violations=0` | all 51 rows map to one of 4 regions |
| SLV-BEA-007 All 4 regions represented | `regions_present=4` | Northeast=9, Midwest=12, South=17, West=13 |
| (new P1) census_region exact counts | `9/12/17/13` | Exact measured counts above |
| SLV-BEA-008 rpp_all_items passthrough | `violations=0` | passthrough is the derivation itself; trivially holds |
| SLV-BEA-009 multiplier range `[0.7, 1.3]` | `violations=0` | observed [0.9033, 1.1507] |
| SLV-BEA-010 inverse invariant, tol=0.01 | `violations=0` | max dev = 1.42e-14 |
| SLV-BEA-011 verification_status IN enum | `violations=0` | only bea_official and estimate present |
| SLV-BEA-012 `COUNT WHERE bea_official = 8` | `= 8` | exactly 8 rows bea_official |
| SLV-BEA-013 bea_official fips ∈ allow-list | `violations=0` | computed set equals `{05,06,11,15,19,28,34,40}` exactly |
| SLV-BEA-014 `data_year = 2024` | `violations=0` | 51/51 rows = 2024 |
| SLV-BEA-015 `COUNT(DISTINCT data_year) = 1` | `= 1` | exactly 1 distinct year |
| SLV-BEA-016 record_id NOT NULL + UNIQUE | (deferred to build) | record_id is hash of state_fips; uniqueness inherits from state_fips uniqueness (51 distinct) |
| SLV-BEA-017 state_fips ↔ state_name bijection | `violations=0` | 51/51/51 distinct triples |
| SLV-BEA-018 state_fips ↔ state_abbr bijection | `violations=0` | 51/51/51 distinct triples |

---

## Notes for Downstream Agents

- **@dq-rule-writer:** All P0 rules in the spec are supported by the dry-run evidence above. No rule needs to be softened. No rule needs to be added beyond the optional P1 exact-region-counts rule. The inverse-invariant tolerance of 0.01 is ~12 orders of magnitude looser than the observed deviation — this is intentional robustness, not sloppiness.
- **@primary-agent:** The physical model's pseudocode at `governance/models/silver-base-bea-rpp-physical.md` produces correct output for all 51 rows when applied to the live Bronze parquet. No transformation logic needs revision.
- **@semantic-modeler:** No model revisions surfaced. DC-in-South is explicitly handled by the enum rule; no special case needed.
- **@chaos-monkey:** Reasonable adversarial tests would be: (a) remove a FIPS code from the lookup and verify Silver build fails loudly rather than writing NULL, (b) inject an rpp_all_items near the 70.0/130.0 boundary, (c) inject a verification_status allow-list with 7 entries to verify the `= 8` rule catches under-verification. All three are Silver-build-time tests, not EDA findings.

---

*— End of EDA Report —*
