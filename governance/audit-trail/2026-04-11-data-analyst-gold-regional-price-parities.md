# Audit Trail — @data-analyst — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @data-analyst
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Phase:** Gold dry-run EDA (pre-build)
**Session Type:** Exploratory data analysis on derived Gold columns
**Mode:** Dry-run (Gold table does not exist yet)

---

## What was analyzed and why

The Gold target `consumable.regional_price_parities` has not been built yet. This EDA is a dry-run profiling pass: I read all 51 rows from the Silver source `base.bea_rpp` (catalog `brightsmith`, warehouse `data/silver/iceberg_warehouse`), derived the 4 new Gold columns in memory using the spec's frozen CASE expression and rounding rule, and profiled the result to give @dq-rule-writer evidence for threshold decisions and to give @chaos-monkey a prioritized list of boundary rows to target.

**Source:**
- Silver table: `base.bea_rpp` (51 rows, 11 columns)
- Access path: DuckDB `iceberg_scan` with `unsafe_enable_version_guessing = true` against the local Iceberg warehouse
- Data vintage: 2024 (single `data_year` value across all rows)
- Verification mix: 8 `bea_official` (AR, CA, DC, HI, IA, MS, NJ, OK) + 43 `estimate`

**Derivations computed (spec-frozen):**
1. `cost_tier` — 5-bucket CASE: very_high ≥ 108, high ∈ [103, 108), average ∈ [97, 103), low ∈ [91, 97), very_low < 91 (left-closed)
2. `adjusted_30k` = round(30000.0 × purchasing_power_multiplier, 2)
3. `adjusted_50k` = round(50000.0 × purchasing_power_multiplier, 2)
4. `adjusted_75k` = round(75000.0 × purchasing_power_multiplier, 2)
5. `adjusted_100k` = round(100000.0 × purchasing_power_multiplier, 2)

No data was modified. No files were written to the warehouse. This pass is purely analytical.

---

## Key findings

1. **cost_tier distribution — all 5 tiers materialize.** Despite the spec's warning that some tiers might not have members with only 8 verified rows, all 5 buckets are populated: `very_high=4`, `high=8`, `average=13`, `low=11`, `very_low=15`. The P1 "at least 3 distinct tiers" rule can be tightened to exactly 5.
2. **All 8 BEA spot checks PASS with zero delta.** Not just within the spec's 0.01 tolerance — observed delta is exactly 0.0 for all 8 verified states (CA, HI, DC, NJ, AR, MS, IA, OK), for both tier classification and adjusted_50k value.
3. **Derivation is pure and deterministic.** `adjusted_50k == round(50000.0 × ppm, 2)` for all 51 rows (delta = 0.0). Same for the other three adjusted_Nk fields.
4. **CA / IA sanity holds.** CA adjusted_50k = 45167.12 (< 50000.0 as expected for high-cost). IA adjusted_50k = 56947.61 (> 50000.0 as expected for low-cost).
5. **Inverse invariant essentially exact.** max |ppm × rpp − 100| = 1.42e-14 across all 51 rows (floating-point noise only). Spec's 0.01 tolerance has 12 orders of magnitude of slack.
6. **17 states (33.3%) are within 1.0 RPP of a cost_tier breakpoint.** High-value chaos targets. TN sits exactly on 91.0 — the single most important boundary witness row.
7. **0 nulls observed** in any field across all 51 rows.
8. **Observed data ranges inside spec CHECK ranges.** rpp ∈ [86.9, 110.7] ⊂ [70.0, 130.0]; ppm ∈ [0.903342, 1.150748] ⊂ [0.7, 1.3]. Healthy headroom for future vintages.

---

## Threshold recommendations with evidence

| Recommendation | Spec rule | Supporting evidence |
|---|---|---|
| Tighten P1 distinct tier rule from ≥ 3 to = 5 | `COUNT(DISTINCT cost_tier) ≥ 3` | All 5 tiers materialize (4 / 8 / 13 / 11 / 15). |
| Keep adjusted_Nk tolerance at 0.01 | `abs(adjusted_Nk − expected) ≤ 0.01` | Observed max delta = 0.0 across 51 × 4 = 204 cells. Slack is appropriate for portability. |
| Keep inverse invariant at 0.01 | `abs(ppm × rpp − 100) ≤ 0.01` | Observed max delta = 1.42e-14. Slack is 12 orders of magnitude. |
| Keep rpp_all_items CHECK at [70, 130] | `CHECK (rpp_all_items BETWEEN 70 AND 130)` | Observed [86.9, 110.7]. |
| Keep ppm CHECK at [0.7, 1.3] | `CHECK (ppm BETWEEN 0.7 AND 1.3)` | Observed [0.903342, 1.150748]. |
| Keep COUNT(bea_official) = 8 | Exact count of 8 | Observed exactly 8. Member set matches canonical list. |
| Add P1 cross-column arithmetic: `abs(adjusted_100k − 2 × adjusted_50k) ≤ 0.02` | New | Cheap self-consistency check across the four adjusted_Nk columns; derivation is mathematically equivalent. |
| Add P1 soft tier count ranges | New | very_high 4 (bound 3–6), high 8 (5–10), average 13 (10–16), low 11 (8–14), very_low 15 (10–18). |
| Add P1 adjusted_Nk range rules | New | a30 ∈ [27100.27, 34522.44]; a50 ∈ [45167.12, 57537.40]; a75 ∈ [67750.68, 86306.10]; a100 ∈ [90334.24, 115074.80]. |

---

## Chaos-monkey boundary candidates

17 states within 1.0 RPP of a breakpoint. Priority order:

1. **TN (91.0)** — exact boundary hit. Witness row for left-closed convention.
2. **TX (96.9), ME (97.1), MA (107.9), OH (90.8)** — within 0.2 of a breakpoint.
3. **IN (90.7), MN (97.3), UT (97.4)** — within 0.4.
4. **CO, LA, NY, ND, PA** — within 0.6.
5. **MO, NJ, NE, OR** — within 0.9.

NJ is the only `bea_official` row near a boundary; use it as an anchor, do not mutate.

See the EDA report for the full chaos playbook (perturbation plan, anchor invariants).

---

## Anomalies / unexpected findings

- **IA and OK share rpp=87.8** — identical ppm, identical adjusted_Nk. Both are `bea_official`. Expected but worth noting: any uniqueness rule on rpp_all_items or adjusted_Nk would fail. None is proposed.
- **`bea_official` rows cluster in the extremes** — all 4 `very_high` rows and 4 of the 15 `very_low` rows are `bea_official`. No middle-tier row is verified. This is a product of Bronze verification effort (the spec picked extremes intentionally) and is not a data issue.
- **TN is exactly on 91.0** — intentional witness row for the left-closed convention. Any future refresh that accidentally switches to right-closed would silently flip TN's tier.
- **Nothing surprising or alarming was found.** The Silver source is clean, the Gold derivations are pure, and the spec's rules line up with the data.

---

## Artifacts produced

- `governance/eda/gold-regional-price-parities-eda.md` — full EDA report with field profiles, spot check table, boundary proximity table, threshold recommendations
- `governance/audit-trail/2026-04-11-data-analyst-gold-regional-price-parities.md` — this file

## No artifacts mutated

- No Iceberg tables written
- No rules written (that is @dq-rule-writer's job)
- No model changes proposed
- No CDE / PII mappings (@cde-tagger / @pii-scanner handle those)

---

## Spec reference

`docs/specs/gold-regional-price-parities.md` — section "DQ Rules (Gold)" and "Cost Tier Derivation" (from the physical model `governance/models/gold-regional-price-parities-physical.md`) are the authoritative source for the CASE expression and rounding rule used in this dry-run.

---

*— End of Audit Trail —*
