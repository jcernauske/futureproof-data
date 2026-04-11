# EDA Report: consumable.regional_price_parities (Gold — Dry Run)

**Spec:** `docs/specs/gold-regional-price-parities.md`
**Source:** `base.bea_rpp` (Silver) in `data/silver/iceberg_warehouse`, catalog `brightsmith`
**Mode:** Dry-run. Gold table does not yet exist. All 51 Silver rows were read and the 4 Gold derivations (`cost_tier`, `adjusted_30k/50k/75k/100k`) were computed in memory using the CASE expression and rounding rule from the spec.
**Date:** 2026-04-11
**Agent:** @data-analyst
**Record Count:** 51 (exactly 51 — 50 states + DC)
**Field Count (Gold projected):** 15

---

## Key Findings

- **All 5 cost tiers materialize.** The spec warned that with only 8 verified rows and 43 estimates some tiers might not have members. They all do: `very_high=4`, `high=8`, `average=13`, `low=11`, `very_low=15`. The P1 distribution rule ("at least 3 distinct tiers present") can comfortably be tightened to `= 5`.
- **Derivation is pure and deterministic.** `adjusted_50k == round(50000.0 × purchasing_power_multiplier, 2)` for all 51 rows with delta `0.0`. Same holds for the other three `adjusted_Nk` fields.
- **All 8 BEA spot checks PASS exactly.** Every verified state matches the expected tier and the expected `adjusted_50k` to zero delta (not just within 0.01). This is stronger evidence than the rule requires and lets `@dq-rule-writer` tighten the tolerance if desired.
- **Inverse invariant is essentially exact.** `max |purchasing_power_multiplier × rpp_all_items − 100.0| = 1.42e-14`. The Silver layer's pre-computed multiplier has no observable rounding drift. The spec's 0.01 tolerance is ~12 orders of magnitude looser than actual.
- **CA sanity holds:** `adjusted_50k = 45167.12 < 50000.0`. **IA sanity holds:** `adjusted_50k = 56947.61 > 50000.0`.
- **17 states are within 1.0 RPP of a cost-tier breakpoint.** These are the high-value targets for chaos boundary testing. In particular, `MA (107.9)`, `TX (96.9)`, `ME (97.1)`, `OH (90.8)`, `TN (91.0)`, and `IN (90.7)` sit within 0.3 of a breakpoint.
- **Single-vintage data.** `data_year = 2024` for all 51 rows. `COUNT(DISTINCT data_year) = 1`.
- **0 nulls observed** across every field scanned. The Gold "0% nulls on all 15 columns" contract guarantee is consistent with source.

---

## Domain Context

**Identified Domain:** U.S. regional cost-of-living reference data (economic geography / purchasing power).
**Primary Entities:** U.S. states (including D.C.) with their 2024 BEA Regional Price Parity index and derived display-ready purchasing-power adjustments at four salary anchors.
**Grain:** One row per `state_fips` (50 states + DC = 51). Closed set. Static annual snapshot.
**Temporal Pattern:** Annual snapshot, vintage 2024. Single `data_year` value. Gold refresh cadence: yearly when BEA publishes.
**Domain Vocabulary (carried from Silver/Bronze):** RPP, purchasing power multiplier, state FIPS, USPS state abbreviation, Census region, verification status (`bea_official` vs `estimate`). New at Gold: `cost_tier` (BT-106), `adjusted_Nk` (BT-107).
**Taxonomy / Codes:** FIPS state codes (2-digit zero-padded), USPS state abbreviations, Census Bureau regions (`Northeast / Midwest / South / West`), 5-bucket cost tier editorial taxonomy defined in this spec.

---

## Field Profiles (Gold — projected)

### record_id
- **Type:** STRING (VARCHAR), derived via `compute_grain_id(row, ['state_fips'], prefix='rpc')`
- **Null Rate:** 0% projected (deterministic derivation over non-null state_fips)
- **Cardinality:** 51 distinct (100% uniqueness — natural key is already unique)
- **Format:** `rpc-<16 hex chars>`

### state_fips (carry-forward)
- **Type:** STRING
- **Null Rate:** 0% (0 of 51)
- **Cardinality:** 51 distinct (100% uniqueness)
- **Pattern:** 2-digit zero-padded. All 51 observed values match `^\d{2}$`. Canonical set confirmed: `01,02,04,05,06,08,09,10,11,12,13,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,44,45,46,47,48,49,50,51,53,54,55,56`.

### state_name (carry-forward)
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 51 distinct (100% uniqueness)
- **Note:** `District of Columbia` present as a full USPS canonical string.

### state_abbr (carry-forward)
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 51 distinct
- **Pattern:** 100% match `^[A-Z]{2}$`.

### census_region (carry-forward)
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 4 distinct
- **Distribution:** `South=17`, `West=13`, `Midwest=12`, `Northeast=9`. DC is classified as `South` (per Census convention).

### rpp_all_items (carry-forward)
- **Type:** DOUBLE
- **Null Rate:** 0%
- **Cardinality:** 50 distinct (IA and OK both = 87.8 — one duplicate, expected)
- **Distribution:** min=86.9, max=110.7, mean=96.98, median=96.9
- **Range:** [86.9, 110.7] — well inside the spec's declared [70.0, 130.0] CHECK range. Headroom: 16.9 below the floor, 19.3 above the ceiling.
- **Outliers:** None beyond 3 sigma. Range is tight and plausible.

### purchasing_power_multiplier (carry-forward)
- **Type:** DOUBLE
- **Null Rate:** 0%
- **Cardinality:** 50 distinct (IA == OK duplicate)
- **Distribution:** min=0.903342, max=1.150748, mean=1.036417
- **Range:** [0.903342, 1.150748] — well inside the spec's declared [0.7, 1.3].
- **Inverse invariant:** max |ppm × rpp − 100| = **1.42e-14** (floating-point noise only).

### cost_tier (derived at Gold)
- **Type:** STRING
- **Null Rate:** 0% (derived over non-null rpp_all_items)
- **Cardinality:** **5 distinct** — all 5 buckets materialize.
- **Distribution:**

| tier | count | pct |
|------|------:|----:|
| very_high | 4 | 7.84% |
| high | 8 | 15.69% |
| average | 13 | 25.49% |
| low | 11 | 21.57% |
| very_low | 15 | 29.41% |

- **Members by tier:**
  - `very_high` (4): CA (110.7), DC (109.9), HI (110.0), NJ (108.8)
  - `high` (8): AK (104.6), CO (103.5), CT (105.1), MA (107.9), MD (104.8), NH (104.3), NY (107.5), WA (106.4)
  - `average` (13): AZ (100.5), DE (100.2), FL (100.3), IL (99.6), ME (97.1), MN (97.3), NV (101.2), OR (102.1), PA (97.6), RI (99.8), UT (97.4), VA (101.7), VT (100.8)
  - `low` (11): GA (95.8), ID (93.6), MI (92.9), MT (94.2), NC (94.3), NM (92.3), SC (93.7), TN (91.0), TX (96.9), WI (92.4), WY (92.7)
  - `very_low` (15): AL (88.4), AR (86.9), IA (87.8), IN (90.7), KS (89.6), KY (88.8), LA (90.5), MO (90.2), MS (87.0), ND (90.4), NE (90.1), OH (90.8), OK (87.8), SD (89.9), WV (88.2)

### adjusted_30k (derived at Gold)
- **Type:** DOUBLE (cents precision via `round(..., 2)`)
- **Null Rate:** 0%
- **Distribution:** min=27100.27 (CA), max=34522.44 (AR), mean=31092.51, median=30959.75
- **Check:** For all 51 rows, `adjusted_30k == round(30000.0 × ppm, 2)` exactly.

### adjusted_50k (derived at Gold)
- **Type:** DOUBLE
- **Null Rate:** 0%
- **Distribution:** min=45167.12 (CA), max=57537.40 (AR), mean=51820.84, median=51599.59 (TX)
- **Check:** For all 51 rows, `adjusted_50k == round(50000.0 × ppm, 2)` exactly (delta = 0.0).
- **Histogram ($500 bins):**

```
[45000, 45500)  ###     (3)   CA, HI, DC
[45500, 46000)  #       (1)   NJ
[46000, 46500)  #       (1)   MA
[46500, 47000)  ##      (2)   NY, WA
[47500, 48000)  ####    (4)   CT, MD, AK, NH
[48000, 48500)  #       (1)   CO
[48500, 49000)  #       (1)   OR
[49000, 49500)  ##      (2)   VA, NV
[49500, 50000)  ####    (4)   VT, AZ, FL, DE
[50000, 50500)  ##      (2)   RI, IL
[51000, 51500)  ####    (4)   PA, UT, MN, ME
[51500, 52000)  #       (1)   TX
[52000, 52500)  #       (1)   GA
[53000, 53500)  ####    (4)   NC, MT, SC, ID
[53500, 54000)  ##      (2)   MI, WY
[54000, 54500)  ##      (2)   WI, NM
[54500, 55000)  #       (1)   TN
[55000, 55500)  ######  (6)   OH, IN, LA, ND, MO, NE
[55500, 56000)  ##      (2)   SD, KS
[56000, 56500)  #       (1)   KY
[56500, 57000)  ####    (4)   AL, WV, IA, OK
[57000, 57500)  #       (1)   MS
[57500, 58000)  #       (1)   AR
```

### adjusted_75k (derived at Gold)
- **Type:** DOUBLE
- **Null Rate:** 0%
- **Distribution:** min=67750.68 (CA), max=86306.10 (AR), mean=77731.26, median=77399.38

### adjusted_100k (derived at Gold)
- **Type:** DOUBLE
- **Null Rate:** 0%
- **Distribution:** min=90334.24 (CA), max=115074.80 (AR), mean=103641.69, median=103199.17

### verification_status (carry-forward)
- **Type:** STRING
- **Null Rate:** 0%
- **Cardinality:** 2 distinct
- **Distribution:** `estimate=43` (84.31%), `bea_official=8` (15.69%)
- **The 8 `bea_official` states:** AR, CA, DC, HI, IA, MS, NJ, OK — **exactly matches** the spec's canonical 8-state set.

### data_year (carry-forward)
- **Type:** INTEGER
- **Null Rate:** 0%
- **Cardinality:** 1 (only 2024)

### promoted_at (derived at Gold)
- **Type:** TIMESTAMP
- **Null Rate:** 0% projected (set by promote())
- **Distribution:** N/A — will be set at Gold write time.

---

## Cross-Field Analysis

1. **cost_tier ↔ rpp_all_items** — Perfect monotonic mapping by construction. Breakpoints observed in effect: the `very_low` / `low` boundary hits exactly at TN rpp=91.0 (TN is `low`; OH at 90.8 is `very_low`), confirming the left-closed convention.
2. **adjusted_Nk scales linearly with N** — For every row, `adjusted_100k ≈ 2 × adjusted_50k` (within rounding). `adjusted_75k ≈ 1.5 × adjusted_50k`. `adjusted_30k ≈ 0.6 × adjusted_50k`. This is an optional sanity rule @dq-rule-writer could add as a P1 cross-column invariant: `abs(adjusted_100k − 2 × adjusted_50k) ≤ 0.02` (to allow 2 × round-half-even tolerance).
3. **ppm × rpp = 100** — Exact to 1.42e-14. The spec's 0.01 tolerance is conservative but correct to keep.
4. **verification_status ↔ cost_tier** — All 4 `very_high` rows are `bea_official` (CA, DC, HI, NJ). All 8 `bea_official` rows are in `very_high` or `very_low` (the extremes). Every middle-tier row is `estimate`. This is a feature of the verification effort, not a data issue.
5. **ppm × adjusted_30k calibration** — `adjusted_50k / adjusted_30k` ≈ 5/3 = 1.6667 exactly (before rounding). Verified.

---

## Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|------:|-----------:|----------------|
| Rows with `verification_status='bea_official'` | 8 | 15.69% | Exact count rule: `= 8`. Allow-list: `state_fips IN ('05','06','11','15','19','28','34','40')`. |
| Rows with `verification_status='estimate'` | 43 | 84.31% | Informational. Derives from `51 − 8`. |
| Distinct `cost_tier` values materialized | 5 | 100% of spec-defined | Tighten P1 from "at least 3" to `= 5` (evidence: all 5 present). |
| `cost_tier='very_high'` count | 4 | 7.84% | Soft bound: `BETWEEN 3 AND 6` (CA, DC, HI, NJ are BEA-verified and stable; small drift only from estimates near 108). |
| `cost_tier='very_low'` count | 15 | 29.41% | Soft bound: `BETWEEN 10 AND 18`. |
| `cost_tier='high'` count | 8 | 15.69% | Soft bound: `BETWEEN 5 AND 10`. |
| `cost_tier='average'` count | 13 | 25.49% | Soft bound: `BETWEEN 10 AND 16`. |
| `cost_tier='low'` count | 11 | 21.57% | Soft bound: `BETWEEN 8 AND 14`. |
| rpp_all_items range | 51 | 100% | Observed [86.9, 110.7]; spec CHECK is [70.0, 130.0]. Keep spec range — headroom is reasonable for future vintages. |
| purchasing_power_multiplier range | 51 | 100% | Observed [0.903342, 1.150748]; spec CHECK is [0.7, 1.3]. Keep spec range. |
| Max |ppm × rpp − 100| | 51 | 100% | Observed 1.42e-14. Keep spec tolerance 0.01 — it provides 12 orders of magnitude of slack for any future precision changes. |
| adjusted_50k vs round(50000 × ppm, 2) | 51 | 100% | Max delta = 0.0. Spec tolerance 0.01 is safe. |
| CA adjusted_50k | 1 | — | 45167.12 < 50000.0. Keep the spec's CA sanity rule as written. |
| IA adjusted_50k | 1 | — | 56947.61 > 50000.0. Keep the spec's IA sanity rule as written. |
| adjusted_30k range | 51 | 100% | [27100.27, 34522.44]. Candidate P1 range rule: `BETWEEN 25000 AND 36000`. |
| adjusted_50k range | 51 | 100% | [45167.12, 57537.40]. Candidate P1 range rule: `BETWEEN 42000 AND 60000`. |
| adjusted_75k range | 51 | 100% | [67750.68, 86306.10]. Candidate P1 range rule: `BETWEEN 63000 AND 90000`. |
| adjusted_100k range | 51 | 100% | [90334.24, 115074.80]. Candidate P1 range rule: `BETWEEN 84000 AND 120000`. |
| States within 1.0 RPP of a breakpoint | 17 | 33.33% | See "Boundary Proximity" below. Target for chaos-monkey boundary tests. |
| Duplicate rpp_all_items values | 1 pair | 3.92% (IA, OK both 87.8) | Informational. Both are `bea_official`, both in `very_low`. No action. |

---

## Spot Check Pass / Fail (8/8 PASS)

| state_fips | state_abbr | expected tier | observed tier | expected a50 | observed a50 | delta | vs | status |
|---|---|---|---|---:|---:|---:|---|---|
| 06 | CA | very_high | very_high | 45167.12 | 45167.12 | 0.0000 | bea_official | PASS |
| 15 | HI | very_high | very_high | 45454.55 | 45454.55 | 0.0000 | bea_official | PASS |
| 11 | DC | very_high | very_high | 45495.91 | 45495.91 | 0.0000 | bea_official | PASS |
| 34 | NJ | very_high | very_high | 45955.88 | 45955.88 | 0.0000 | bea_official | PASS |
| 05 | AR | very_low  | very_low  | 57537.40 | 57537.40 | 0.0000 | bea_official | PASS |
| 28 | MS | very_low  | very_low  | 57471.26 | 57471.26 | 0.0000 | bea_official | PASS |
| 19 | IA | very_low  | very_low  | 56947.61 | 56947.61 | 0.0000 | bea_official | PASS |
| 40 | OK | very_low  | very_low  | 56947.61 | 56947.61 | 0.0000 | bea_official | PASS |

All 8 BEA-verified spot checks pass with **zero delta** (not just within 0.01). This exceeds the spec's tolerance.

---

## Boundary Proximity (Chaos-Monkey Candidates)

17 states (33.3%) sit within 1.0 RPP of a `cost_tier` breakpoint. Sorted by proximity to breakpoint.

| state | fips | rpp | breakpoint | delta from bp | tier | vs | notes |
|---|---|---:|---:|---:|---|---|---|
| **TN** | 47 | 91.0  | 91.0  | +0.00 | low      | estimate | **Exact boundary hit.** Left-closed convention puts TN in `low`. Single biggest chaos target. |
| **TX** | 48 | 96.9  | 97.0  | -0.10 | low      | estimate | 0.1 below `average` boundary. |
| **ME** | 23 | 97.1  | 97.0  | +0.10 | average  | estimate | 0.1 above — sits immediately on the `low/average` line. |
| **MA** | 25 | 107.9 | 108.0 | -0.10 | high     | estimate | 0.1 below `very_high`. |
| **OH** | 39 | 90.8  | 91.0  | -0.20 | very_low | estimate | 0.2 below `low` boundary. |
| IN | 18 | 90.7  | 91.0  | -0.30 | very_low | estimate | |
| MN | 27 | 97.3  | 97.0  | +0.30 | average  | estimate | |
| UT | 49 | 97.4  | 97.0  | +0.40 | average  | estimate | |
| CO | 08 | 103.5 | 103.0 | +0.50 | high     | estimate | |
| LA | 22 | 90.5  | 91.0  | -0.50 | very_low | estimate | |
| NY | 36 | 107.5 | 108.0 | -0.50 | high     | estimate | |
| ND | 38 | 90.4  | 91.0  | -0.60 | very_low | estimate | |
| PA | 42 | 97.6  | 97.0  | +0.60 | average  | estimate | |
| MO | 29 | 90.2  | 91.0  | -0.80 | very_low | estimate | |
| NJ | 34 | 108.8 | 108.0 | +0.80 | very_high | bea_official | Only `bea_official` row near a boundary — do not mutate. |
| NE | 31 | 90.1  | 91.0  | -0.90 | very_low | estimate | |
| OR | 41 | 102.1 | 103.0 | -0.90 | average  | estimate | |

**Chaos recommendations for @chaos-monkey:**

1. **TN is the single most important target** — sitting exactly on 91.0, it is the witness row for the left-closed convention. Any accidental swap to right-closed would move TN from `low` → `very_low`. Mutation: verify TN remains `low` at `rpp = 91.0`.
2. **Nudge test pairs** — for each of TN (91.0), ME (97.1), NJ (108.8), verify a ±0.01 RPP perturbation places the row correctly (TN→low at 91.00, →very_low at 90.99; ME→average at 97.00, →low at 96.99; NJ→very_high at 108.00, →high at 107.99).
3. **4 closest non-verified boundary rows** — TX (96.9), ME (97.1), MA (107.9), OH (90.8) are all within 0.2 of a breakpoint and are `estimate` rows. They are most vulnerable to classification flip if BEA publishes actual values slightly different from the primary-agent estimate.
4. **NJ is the only `bea_official` row near a breakpoint** (+0.80 above 108.0). It anchors the `very_high` tier's low boundary. Do not mutate NJ — it is truth. But test that a hypothetical NJ at 107.99 would land in `high`, not `very_high`.

---

## Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|------:|---------|---------|
| rpp_all_items | Tie | 1 pair | info | IA and OK both = 87.8 → same ppm, same adjusted_Nk. Both are `bea_official`. Not an anomaly, expected. |
| cost_tier boundary hit | Boundary | 1 | info | TN exactly 91.0 → classified `low` per left-closed rule. Not an anomaly; intentional witness. |
| verification_status distribution | Skew | — | info | `bea_official` rows cluster in the extremes of the distribution (4 very_high, 4 very_low). This is a product of Bronze verification effort, not a data quality issue. |
| Nulls | — | 0 | — | No nulls in any field across any of the 51 rows. |
| Negative / zero values | — | 0 | — | None. All rpp and ppm strictly positive; all adjusted_Nk strictly positive. |
| Out-of-range | — | 0 | — | All rpp ∈ [86.9, 110.7] ⊂ [70.0, 130.0]. All ppm ∈ [0.903, 1.151] ⊂ [0.7, 1.3]. |

---

## Recommendations to @dq-rule-writer

All recommendations cite computed values from the 51-row dry-run above.

1. **Keep** all 25+ P0 rules as written in the spec — every one is backed by the evidence above.
2. **Tighten** the P1 `cost_tier` distribution rule from "at least 3 distinct tiers" to `COUNT(DISTINCT cost_tier) = 5` — evidence: all 5 tiers materialize.
3. **Tighten** the `adjusted_Nk` delta rule from `≤ 0.01` to `≤ 0.001` if desired — evidence: observed max delta = 0.0. (Spec's 0.01 is also fine; the slack cushions any future precision change.)
4. **Tighten** the inverse invariant from `≤ 0.01` to `≤ 1e-10` if desired — evidence: observed max delta = 1.42e-14. (Again, 0.01 is fine and more portable.)
5. **Add** an optional P1 cross-column rule: `abs(adjusted_100k − 2.0 × adjusted_50k) ≤ 0.02` — provides a cheap arithmetic self-check across the four `adjusted_Nk` columns.
6. **Add** P1 range rules on adjusted_Nk (observed ranges above) as a soft anomaly tripwire for future refresh runs.
7. **Add** P1 tier count soft bounds:
   - `cost_tier='very_high'` count BETWEEN 3 AND 6
   - `cost_tier='high'` count BETWEEN 5 AND 10
   - `cost_tier='average'` count BETWEEN 10 AND 16
   - `cost_tier='low'` count BETWEEN 8 AND 14
   - `cost_tier='very_low'` count BETWEEN 10 AND 18
8. **No change** to the canonical FIPS set, the bijection rules, the census region enum, the `bea_official = 8` rule, the 8 spot-check rules, or the CA/IA sanity rules — all verified exactly.

---

## Recommendations to @chaos-monkey

See "Boundary Proximity" section. Priority targets in order:

1. TN (exact boundary)
2. TX, ME, MA, OH (within 0.2)
3. IN, MN, UT (within 0.4)
4. Mutation framework: perturb rpp_all_items by ±0.01 around each breakpoint (108.0, 103.0, 97.0, 91.0) and verify cost_tier flips exactly at the breakpoint, not before or after.
5. Do not mutate NJ, CA, DC, HI, AR, MS, IA, OK (the 8 `bea_official` rows) — use them as anchors for invariant checks.

---

*— End of EDA Report —*
