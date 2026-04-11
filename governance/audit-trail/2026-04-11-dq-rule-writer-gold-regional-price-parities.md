# Audit Trail: @dq-rule-writer — gold-regional-price-parities

**Agent:** @dq-rule-writer
**Date:** 2026-04-11
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Zone:** Gold (Consumable)
**Target table:** `consumable.regional_price_parities`
**Artifact produced:** `governance/dq-rules/gold-regional-price-parities.json`

---

## Inputs consulted

| Source | Path | Role |
|--------|------|------|
| Spec | `docs/specs/gold-regional-price-parities.md` | Business requirements, spot-check table, boundary semantics |
| EDA report | `governance/eda/gold-regional-price-parities-eda.md` | Primary evidence for all thresholds (51 rows, 0 anomalies, 0.0 spot-check delta) |
| Physical model | `governance/models/gold-regional-price-parities-physical.md` | Schema, CHECK constraints, derivation formulas, frozen CASE expression |
| Silver reference | `governance/dq-rules/silver-base-bea-rpp.json` | 39-rule pattern to mirror and scale |
| Domain context | `governance/domain-context.md` (BEA RPP section) | Edge cases and validity semantics |

---

## Rule count summary

- **Total rules written:** 55 (`GLD-RPP-001` through `GLD-RPP-055`)
- **By priority:**
  - **P0:** 51 rules (structural constraints, derivation purity, spot checks, passthrough integrity)
  - **P1:** 4 rules (`GLD-RPP-052`, `GLD-RPP-053`, `GLD-RPP-054`, `GLD-RPP-055`)
- **By category (every rule populates the top-level `category` field — closes MEDIUM-3 from Bronze audit):**
  - `validity`: 19
  - `completeness`: 15
  - `consistency`: 14
  - `uniqueness`: 3
  - `volume`: 1
  - `referential_integrity`: 1
  - `coverage`: 1
  - `freshness`: 1
- **Rules with `chaos_exclude: true` / `evaluation_mode: "production_only"`:** 2 (`GLD-RPP-043` passthrough integrity, `GLD-RPP-055` Silver freshness) — both cross-zone rules that cannot run under the Gold shadow harness, same pattern as Silver's `SIL-BEA-018`.

---

## Rule design rationale

### Scaling from Silver's 39 to Gold's 55
The Silver table has 11 columns; Gold has 15. Gold adds 4 derivations (`cost_tier`, `adjusted_30k/50k/75k/100k`) plus 1 carry-forward (`verification_status` per Bronze Condition 7). The extra 16 rules beyond Silver's count come from:

- +1 `record_id` format rule (`rpc-` prefix is Gold-specific, `GLD-RPP-040`)
- +1 canonical FIPS set rule at `GLD-RPP-005` (Silver placed it at position 39 after chaos remediation — Gold puts it inline at position 5)
- +4 `adjusted_Nk` non-null rules (one per column)
- +4 `adjusted_Nk` derivation-purity rules (one per column)
- +2 cost_tier rules (enum + classification correctness)
- +1 TN boundary witness rule (`GLD-RPP-024`)
- +1 CA high-cost sanity (`GLD-RPP-033`)
- +1 IA low-cost sanity (`GLD-RPP-034`)
- +1 cost_tier per-tier coverage rule (`GLD-RPP-053`)
- +1 passthrough integrity rule (`GLD-RPP-043` consolidates all 8 carry-forward columns into one JOIN rule)
- Dropped Silver rules that don't apply to Gold: the Census region exact count rule (`SIL-BEA-015`) was **not** carried forward because it's a reachable-by-passthrough invariant already covered by `GLD-RPP-043` — keeping a fixed-count rule at Gold would double-count and force two rule flips on any refresh. Silver's `source_load_date` and `ingested_at` non-null rules collapse into Gold's single `promoted_at` non-null rule.

### Evidence-based thresholds (all cited in `rationale` fields)
- **Row count = 51** — EDA derived 51 rows from 51 Silver rows in the dry-run.
- **0 nulls on all 15 columns** — EDA field profiles show `Null Rate: 0%` for every column.
- **`rpp_all_items ∈ [70, 130]` and `ppm ∈ [0.7, 1.3]`** — EDA observed `[86.9, 110.7]` and `[0.9033, 1.1507]`, with 16.9-point and 0.1493/0.2033 margins to the sanity bounds. Physical model CHECK constraints match.
- **Inverse invariant at tol 0.01** — EDA: max absolute deviation = 1.42e-14 (twelve orders of magnitude tighter than threshold). Robustness margin deliberately kept at 0.01.
- **`adjusted_Nk` at tol 0.01** — EDA: max delta = 0.0 exactly on all 51 rows for all 4 adjusted columns. Tolerance held at the spec's 0.01 for consistency with the physical model CHECK.
- **8 BEA-verified spot checks** — EDA: all 8 spot checks pass with ZERO delta on `adjusted_50k`. This lets the rules pin the exact expected values (e.g., `abs(adjusted_50k - 45167.12) > 0.01`).
- **TN boundary witness (`GLD-RPP-024`)** — EDA: TN sits exactly on the 91.0 breakpoint and is classified `low`. This is the highest-value chaos target identified in the EDA; a dedicated rule guards the left-closed convention.
- **cost_tier classification correctness (`GLD-RPP-023`)** — The rule re-runs the frozen CASE expression in SQL and asserts 0 mismatches. Covers all 17 "boundary-adjacent" states flagged by the EDA as chaos targets.
- **All 5 cost_tier values present (`GLD-RPP-052`)** — EDA: very_high=4, high=8, average=13, low=11, very_low=15. Every tier has ≥ 4 rows today; the rule asserts distinct count = 5.
- **P1 per-tier coverage (`GLD-RPP-053`)** — Deliberately loose at `≥ 1` per tier per task input ("do not pin to exact counts 4/8/13/11/15 — estimates may shift on refresh"). Surfaces *which* tier is empty rather than just that distinct < 5.
- **8 bea_official rows** — EDA confirms the count and the exact 8-FIPS allow-list matches Silver's `SIL-BEA-023` + `SIL-BEA-024`. Will flip to `= 51` when the live BEA API refresh lands, in lockstep.
- **Freshness threshold 400 days** — BEA RPP release cadence is annual (≈ December of year N+1 for vintage N); 400 days = 365 + 35-day grace period. P1 because a single missed refresh is operationally important but not catastrophic.

---

## Spot check table (mirrored from task input, all P0)

| Rule | state_fips | state_abbr | cost_tier | adjusted_50k (±0.01) | verification_status |
|---|---|---|---|---|---|
| GLD-RPP-044 | 06 | CA | very_high | 45167.12 | bea_official |
| GLD-RPP-045 | 15 | HI | very_high | 45454.55 | bea_official |
| GLD-RPP-046 | 11 | DC | very_high | 45495.91 | bea_official |
| GLD-RPP-047 | 34 | NJ | very_high | 45955.88 | bea_official |
| GLD-RPP-048 | 05 | AR | very_low | 57537.40 | bea_official |
| GLD-RPP-049 | 28 | MS | very_low | 57471.26 | bea_official |
| GLD-RPP-050 | 19 | IA | very_low | 56947.61 | bea_official |
| GLD-RPP-051 | 40 | OK | very_low | 56947.61 | bea_official |

Each rule asserts all 4 conjuncts simultaneously. EDA confirms every spot check passes with **zero delta** on `adjusted_50k` (not just within tolerance) — stronger evidence than the rule requires.

---

## Rules considered but NOT written

1. **Census region exact counts (NE=9, MW=12, S=17, W=13)** — Silver's `SIL-BEA-015` is *reachable via passthrough* at Gold. Adding a fixed-count Gold rule would duplicate the Silver rule and force two refresh flips instead of one. The passthrough integrity rule `GLD-RPP-043` already covers this transitively.
2. **`adjusted_100k ≈ 2 × adjusted_50k` cross-column sanity** — EDA suggests this as an optional P1 rule. Declined: the 4 `adjusted_Nk` derivation-purity rules (`GLD-RPP-026/028/030/032`) already individually enforce each column against `round(N * 1000 * ppm, 2)`, which is a strictly stronger check. Adding a pairwise cross-column rule would only fire if one of the individual derivation rules is *already* firing, so it adds noise without new signal.
3. **Per-tier exact counts (very_high=4, high=8, etc.)** — Task input explicitly forbids pinning exact counts. Replaced with `GLD-RPP-052` (distinct count = 5) and `GLD-RPP-053` (each tier ≥ 1 row).
4. **Mutation/boundary nudge rules (±0.01 RPP around breakpoints)** — EDA recommends these for the chaos harness, not the DQ suite. They require mutating input data, which is out of scope for DQ runner rules. Will be handled by `@chaos-engineer`.
5. **`state_name` format/regex** — Free-form display names; no canonical regex. Covered by the bijection rule (`GLD-RPP-007`) and the implicit requirement that all 51 names are distinct.

---

## Cross-zone shadow-mode carve-outs

Two rules carry `evaluation_mode: "production_only"` and `chaos_exclude: true`:

1. **`GLD-RPP-043`** (passthrough integrity) — Joins `consumable.regional_price_parities` (Gold) against `base.bea_rpp` (Silver). The DQ runner's shadow-mode rewrite stages only `shadow_consumable` during Gold chaos runs, not `shadow_base`, so this rule ERRORs under shadow invocation. Correct and passes in production. Same root cause as Silver `SIL-BEA-018` Gap 3.
2. **`GLD-RPP-055`** (Silver freshness) — Reads `base.bea_rpp.source_load_date` from the Gold DQ suite. Same shadow-mode limitation.

Both rules are documented with `chaos_exclude_reason` explaining the limitation. The `@chaos-engineer` must honor `evaluation_mode: "production_only"` and filter these rules out of shadow runs (rule_id allowlist or marker honor). A future cross-zone shadow mode in the runner would let us drop the carve-out.

---

## Confirmation checklist

- [x] Every rule populates top-level `category` field (55/55) — verified via JSON parse + category count
- [x] Every rule also retains `dimension` field as a synonym (55/55) — continuity with Bronze rule files
- [x] Rule IDs sequential `GLD-RPP-001` .. `GLD-RPP-055` — verified via enumerated comparison
- [x] Every rule has `sql`, `threshold`, `description`, `rationale`, `status`, `proposed_by`, `proposed_at`
- [x] `proposed_by` = `@dq-rule-writer` on all rules
- [x] `status` = `proposed` on all rules (awaiting @governance-reviewer + human approval)
- [x] Schema matches `governance/dq-rules/silver-base-bea-rpp.json` exactly
- [x] Cross-zone rules marked `evaluation_mode: "production_only"` and `chaos_exclude: true` with `chaos_exclude_reason`
- [x] `adjusted_Nk` tolerance = 0.01 (spec-declared, matches physical model CHECK)
- [x] `purchasing_power_multiplier` tolerance for spot checks = implicit (exact value comparisons use `adjusted_50k ± 0.01`, matching EDA-observed 0.0 delta)
- [x] TN boundary witness rule encoded as `GLD-RPP-024` — hardens left-closed semantics
- [x] Canonical FIPS set rule present as `GLD-RPP-005` — closes chaos Gap 2 lineage from Silver
- [x] cost_tier classification correctness re-runs the frozen CASE expression — hardens all 17 boundary-adjacent states
- [x] 8 BEA-verified spot checks encoded as individual P0 rules with exact `adjusted_50k` values from EDA
- [x] Per-tier distribution NOT pinned to exact counts (4/8/13/11/15) — P1 uses `distinct = 5` and `each tier ≥ 1`
- [x] JSON parses without error — validated via `python3 -c "import json; json.load(...)"`

---

## Deliverables

1. `governance/dq-rules/gold-regional-price-parities.json` — 55 rules (51 P0, 4 P1)
2. `governance/audit-trail/2026-04-11-dq-rule-writer-gold-regional-price-parities.md` — this file

## Next steps

- @governance-reviewer to review the rule set, verify every threshold is evidence-backed, and approve before promotion to `active`.
- After the Gold transformer runs and produces `consumable.regional_price_parities`, execute `python -m brightsmith.infra.dq_runner run --spec gold-regional-price-parities` to validate all 55 rules pass in production.
- Generate initial scorecard via `python -m brightsmith.infra.dq_runner scorecard --spec gold-regional-price-parities`.
- @chaos-engineer to exercise the TN boundary (GLD-RPP-024), the 17 boundary-adjacent states (covered by GLD-RPP-023), and the canonical FIPS set (GLD-RPP-005), filtering out GLD-RPP-043 and GLD-RPP-055 via the `evaluation_mode: "production_only"` marker.
- When the BEA live API refresh lands, flip GLD-RPP-036 from `= 8` to `= 51` in lockstep with Silver's SIL-BEA-023.
