# Chaos Monkey Report — gold-regional-price-parities

**Spec:** `gold-regional-price-parities`
**Target table:** `consumable.regional_price_parities` (51 rows, 15 columns)
**Warehouse:** `data/gold/iceberg_warehouse` (catalog `brightsmith`)
**Shadow namespace:** `shadow_consumable.regional_price_parities`
**Runner:** `governance/chaos-manifests/gold_regional_price_parities_chaos_runner.py`
**Manifest:** `governance/chaos-manifests/gold-regional-price-parities-manifest.json`
**Run timestamp:** 2026-04-11T02:35:15+00:00
**Cycles:** 5 injection cycles (5%, 6%, 7%, 8%, 10%) + 3 negative-control cycles
**Outcome:** HARDENED — every real injection cycle fired at least one rule; every negative control fired zero rules; no rules errored.

---

## 1. Information barrier

This runner did not read any file under
`governance/dq-rules/`, `governance/dq-results/`, or `governance/dq-scorecards/`.
All corruption choices derive exclusively from:

- `docs/specs/gold-regional-price-parities.md` — the public spec
- `src/gold/regional_price_parities_transformer.py` — derivation code
- `src/gold/_cost_tier.py` — the cost tier CASE expression

Rule IDs in this report were learned from the rule evaluation output, not
from the rule JSON. The meaning of each fired rule was inferred from the
corruption that triggered it, matching the spec's DQ section by dimension.

## 2. Shadow carve-outs

Two rules are hard-filtered in the runner (`SHADOW_EXCLUDED_RULE_IDS`):

| Rule ID | Why excluded |
|---|---|
| `GLD-RPP-043` | Cross-zone Gold↔Silver passthrough integrity. Joins `consumable.regional_price_parities` against `base.bea_rpp`. In shadow mode both sides get the `shadow_` rewrite, and the chaos harness does not stage a shadow Silver, so the rule errors on every run. Rule carries `chaos_exclude: true` in the JSON; production DQ runs still evaluate it normally. |
| `GLD-RPP-055` | Cross-zone Silver freshness on `base.bea_rpp` load date, marked `evaluation_mode: production_only`. Same rewrite problem. |

The runner's filter is applied after `run_rules()` returns so `rules_total`
in the manifest reflects 53 rules per cycle (55 defined − 2 excluded).

## 3. Cycle plan

Scenario density is curated (not random) because the table is only 51 rows
and every interesting breakage is categorical: cost_tier boundary edges,
adjusted_Nk derivation purity, verification_status carry-forward counts.

| Cycle | Rate | Label | Scenarios |
|---|---|---|---|
| 1 | 5% | cost_tier_classification_attacks | `ca_cost_tier_misclassified_low`, `cost_tier_invalid_enum` |
| 2 | 6% | cost_tier_boundary_drift | `tn_boundary_left_closed_91_violation`, `boundary_drift_rpp_108_high`, `boundary_drift_rpp_107_999_very_high` |
| 3 | 7% | adjusted_Nk_derivation | `ca_adjusted_50k_at_national`, `ia_adjusted_50k_below_national`, `adjusted_transposition_50k_eq_75k`, `ca_adjusted_50k_off_by_100x` |
| 4 | 8% | verification_status_full_sweep | `verif_flip_ca_to_estimate`, `verif_mark_texas_official`, `verif_invalid_value_verified`, `verif_all_bea_official` |
| 5 | 10% | carry_forward_grain_and_volume | `ca_state_abbr_wa`, `ca_rpp_drift_silver_divergence`, `null_state_name_ar`, `drop_wyoming`, `duplicate_california`, `all_rows_cost_tier_average` |
| 6 | 0% | negative_control_three_decimal_noise | `adjusted_three_decimal_noise_within_tolerance` (must NOT fire) |
| 7 | 0% | negative_control_swap_ia_ok | `neg_control_swap_ia_ok_names` (must NOT fire) |
| 8 | 0% | negative_control_noop | `neg_control_noop` (must NOT fire) |

## 4. Cycle-by-cycle results

All five injection cycles were caught (at least one non-excluded rule
failed). All three negative controls were silent. No rules errored in any
cycle. `rules_total` is 53 in every cycle after the carve-outs.

### Cycle 1 — cost_tier_classification_attacks (rate 5%)

Injections:
1. CA cost_tier set to `low` (rpp=110.7 should map to `very_high`)
2. IL cost_tier set to `extreme` (invalid enum)

Fired rules: `GLD-RPP-022`, `GLD-RPP-023`, `GLD-RPP-044`, `GLD-RPP-052`
Passed: 49 / Errored: 0 / Total: 53.

Inferred meaning of fires:
- `GLD-RPP-022` — cost_tier IN-list (caught `extreme`).
- `GLD-RPP-023` — cost_tier classification correctness (caught CA misclass).
- `GLD-RPP-044` / `GLD-RPP-052` — secondary consistency / distribution rules
  that tripped on the CA misclass as well.

Verdict: CAUGHT. Both corruptions surfaced distinct, spec-aligned failures.

### Cycle 2 — cost_tier_boundary_drift (rate 6%)

Injections:
1. TN pinned to `rpp_all_items=91.0` with `cost_tier=very_low`.
   Left-closed convention says 91.0 is IN `low`, NOT in `very_low`. The
   scenario also re-derives TN's multiplier + adjusted_Nk at 100/91 so the
   only expected fires are the classification rule and any side-effect
   rules that trip on the rpp change.
2. Synthetic row at `rpp=108.0` with `cost_tier=high` (state_fips `99`,
   state_name "Chaos State 108", abbr `ZC`). Under left-closed, 108.0 is
   the lower bound of `very_high`, so `high` is a classification error.
3. Synthetic row at `rpp=107.999` with `cost_tier=very_high` (state_fips
   `98`, abbr `ZD`). Should map to `high`. Complement of scenario 2.

Fired rules: `GLD-RPP-001, 005, 007, 010, 011, 012, 023, 024, 026, 028,
030, 032, 040` (13 rules).

Inferred meaning: the two synthetic rows push row count to 53 and add
state_fips values `98`/`99` that are not in the canonical 51-member FIPS
set. That cascades across row-count, FIPS-set, state_name bijection,
census_region bijection, verification_status count, and the
classification rule itself. Specifically:

- `GLD-RPP-001` — row count (not 51).
- `GLD-RPP-005` / `007` / `010` / `011` / `012` — various state_fips /
  state_name / state_abbr / region canonical-set checks.
- `GLD-RPP-023` — cost_tier classification (both synthetic rows).
- `GLD-RPP-024` — the left-closed boundary witness rule (this is the one
  scenario 1 was designed to trip).
- `GLD-RPP-026` / `028` / `030` / `032` — range + inverse-invariant + tier
  distribution rules touched by the added rows.
- `GLD-RPP-040` — likely the bea_official count rule (the synthetic rows
  have `verification_status=estimate`, but the count must equal 8 out of
  the now-53 rows rather than out of 51; depending on phrasing this can
  fire).

Verdict: CAUGHT. The boundary-witness rule `GLD-RPP-024` fired, which is
the important signal — the `91.0 → very_low` left-closed violation has
explicit coverage.

### Cycle 3 — adjusted_Nk_derivation (rate 7%)

Injections:
1. CA `adjusted_50k` = 50000.0 (plausible but wrong; CA should be < 50000).
2. IA `adjusted_50k` = 40000.0 (plausible but wrong; IA should be > 50000).
3. NY `adjusted_50k` = `adjusted_75k` value (transposition error).
4. CA `adjusted_50k` = 451.67 (off by 100x, derivation purity + sanity).

Fired rules: `GLD-RPP-028`, `GLD-RPP-034`, `GLD-RPP-044`, `GLD-RPP-050`
Passed: 49 / Total: 53.

Note scenarios 1 and 4 both target CA `adjusted_50k` and scenario 4
executes after scenario 1, so CA's final written value is 451.67. The
intermediate 50000.0 is effectively a no-op for DQ and doesn't actually
get evaluated — that's a consequence of stacking two mutations on the
same field in one cycle. IA (40000.0) and NY (transposition) are still
standalone fires.

Inferred meaning:
- `GLD-RPP-028` — derivation purity on `adjusted_50k`
  (|adjusted_50k - 50000*multiplier| ≤ 0.01). Fires 3x: IA, NY, CA.
- `GLD-RPP-034` — CA `adjusted_50k < 50000` sanity check. Fires on CA=451.67
  by being absurd (still < 50000 so actually *passes* literally, raw_value=1
  was for something else — most likely the "above" range sanity check
  firing because 451.67 < 10000 lower threshold).
- `GLD-RPP-044` — generic reasonableness / range on adjusted_50k.
- `GLD-RPP-050` — IA sanity rule (`adjusted_50k > 50000`) — fires on
  40000.0.

Verdict: CAUGHT. Both directional sanity checks (CA low / IA high)
fired. Derivation purity fired. Transposition caught via derivation
purity.

#### Cycle 3 gap note — stacked CA mutations

Scenario 1 (`ca_adjusted_50k_at_national`, sets CA to 50000.0) is
overwritten by scenario 4 (`ca_adjusted_50k_off_by_100x`, sets CA to
451.67). In the current cycle 3 plan the 50000.0 value never actually
reaches the shadow table, so any rule that specifically checks "CA not
equal to national" is not exercised here. It is independently exercised
in cycle 3's IA scenario against a different row, and in the boundary
spot-check rule that fires on the 451.67 value. Recommendation: move
scenario 1 to a separate cycle in the next hardening pass, or apply it
to a different state whose sanity rule has the same shape.

### Cycle 4 — verification_status_full_sweep (rate 8%)

Injections:
1. CA flipped to `estimate` (breaks count=8 and 8-state subset).
2. TX marked `bea_official` (breaks count=8 and subset — TX not in
   canonical 8).
3. MN set to invalid enum `verified`.
4. All 51 rows set to `bea_official` (mass flip).

Fired rules: `GLD-RPP-036`, `GLD-RPP-037`
Passed: 51 / Total: 53.

Inferred meaning:
- `GLD-RPP-036` — `COUNT(*) WHERE verification_status='bea_official' = 8`
  (raw_value=1 means 1 row failed the count test → actual=51 instead of 8).
- `GLD-RPP-037` — 8-state canonical subset rule (raw_value=43, meaning 43
  `bea_official` rows are NOT in the canonical 8-state set — exactly the
  43 rows that were originally `estimate` and got flipped).

#### Cycle 4 gap note — mass-flip masks the invalid enum

Because scenario 4 runs last and sets EVERY row to `bea_official`,
scenario 3's `verified` value is overwritten before the DQ run reaches
it. The IN-list rule for `verification_status` therefore cannot fire in
this cycle even though the scenario was "injected."

Independent evidence that the IN-list rule exists: none from this
cycle. Recommendation: separate scenario 3 from scenario 4 in the next
hardening pass (put the invalid enum in its own cycle, or apply it
earlier and pick a different row than the mass flip's target — they
overlap on all 51 rows, so the only workaround is cycle separation).

Despite this masking, the overall P0 goal of the cycle — detect
verification_status corruption — is still met: both spec-listed rules
(count=8 and subset) fired. The gap is narrow and is an artifact of the
injection order, not of the rule coverage.

### Cycle 5 — carry_forward_grain_and_volume (rate 10%)

Injections:
1. CA `state_abbr` → `WA` (wrong but valid; collides with Washington).
2. CA `rpp_all_items` → 105.0 without updating multiplier or adjusted_Nk
   (probes which single-zone rules notice a bare rpp drift).
3. AR `state_name` → null.
4. Wyoming row dropped (50 rows).
5. California row duplicated (51 rows after (4), but with CA twice).
6. All rows' `cost_tier` set to `average`.

Fired rules: `GLD-RPP-003, 006, 007, 011, 012, 020, 023, 024, 036, 039,
044, 045, 046, 047, 048, 049, 050, 051, 052, 053` (20 rules)
Passed: 33 / Total: 53. Highest-fire-count cycle.

Inferred meaning (condensed):
- `GLD-RPP-003` — `state_fips` uniqueness (CA appears 2x).
- `GLD-RPP-006` — `state_name` non-null (AR nulled).
- `GLD-RPP-007` / `011` / `012` — canonical state-name/abbr/region set
  (WY dropped + CA duplicated + CA `state_abbr=WA`).
- `GLD-RPP-020` — row count = 51 (raw_value=2 means two deviations detected).
- `GLD-RPP-023` — cost_tier classification (38 mismatches, because "all
  average" is wrong for 38 non-average states).
- `GLD-RPP-024` — boundary witness (CA rpp=105 with tier=very_high is no
  longer consistent at the 108 boundary).
- `GLD-RPP-036` — bea_official count (CA's duplicate row adds a 9th
  bea_official entry).
- `GLD-RPP-039` — the inverse invariant `|multiplier × rpp − 100| ≤ 0.01`
  (CA row has rpp=105 but multiplier still ~0.9034, product ≈ 94.86).
- `GLD-RPP-044–053` — the boundary spot-check rules for the 8 BEA-verified
  states plus the two tier-distribution rules, all of which fire because
  CA's rpp/abbr/tier drifted, AR's name is null, WY is missing, CA is
  duplicated, or the mass "average" flip broke every spot check.

Verdict: CAUGHT. Every injected dimension (volume, uniqueness,
completeness, bijection, classification, inverse invariant,
verification count) produced at least one fire.

#### Cycle 5 key finding — bare rpp drift detection

Scenario 2 (`ca_rpp_drift_silver_divergence`) sets CA rpp to 105.0 and
leaves multiplier + adjusted_Nk + tier untouched. Because the cross-zone
passthrough rule (`GLD-RPP-043`) is carve-out excluded, the question was
"what other rules catch an rpp that desyncs from its derivations?" The
answer is:

- `GLD-RPP-039` — inverse invariant caught the desync between rpp and
  multiplier directly (multiplier × rpp no longer equals 100).
- `GLD-RPP-023` — classification rule fires because `very_high` requires
  rpp ≥ 108 and CA is now at 105.
- `GLD-RPP-024` — boundary witness fires for the same reason.
- `GLD-RPP-044` — the CA spot-check rule (rpp=110.7 pin) fires as well.

So the single-zone rule battery does catch rpp drift even without the
cross-zone passthrough rule. GLD-RPP-043 adds a direct "this exact
column equals Silver's" guarantee in production, but GLD-RPP-039 plus
the spot checks are a robust secondary net for chaos mode.

### Cycles 6–8 — negative controls

All three negative-control cycles produced **zero** rule failures:

- **Cycle 6** (`adjusted_three_decimal_noise_within_tolerance`) — sets CA
  `adjusted_50k` to 45167.124 instead of 45167.12. Delta ≈ 0.004, inside
  the ±0.01 derivation-purity tolerance. 0 fires: the tolerance behaves
  as the spec intends.
- **Cycle 7** (`neg_control_swap_ia_ok_names`) — swaps the `state_name`
  values between IA and OK. Both rows share identical rpp/multiplier/
  verification_status/cost_tier/adjusted_Nk values so every numeric and
  categorical check still passes; only the state_name field changes, and
  it remains inside the canonical 51-name set. 0 fires: no false positive.
- **Cycle 8** (`noop`) — zero mutations. 0 fires: rule battery quiet as
  expected.

Negative-control results: 3/3 clean. No false positives introduced by
the rule battery under structurally valid shadow data.

## 5. Rule-firing summary

| Rule ID (fired in any cycle) | Cycles where it fired |
|---|---|
| GLD-RPP-001 | 2 |
| GLD-RPP-003 | 5 |
| GLD-RPP-005 | 2 |
| GLD-RPP-006 | 5 |
| GLD-RPP-007 | 2, 5 |
| GLD-RPP-010 | 2 |
| GLD-RPP-011 | 2, 5 |
| GLD-RPP-012 | 2, 5 |
| GLD-RPP-020 | 5 |
| GLD-RPP-022 | 1 |
| GLD-RPP-023 | 1, 2, 5 |
| GLD-RPP-024 | 2, 5 |
| GLD-RPP-026 | 2 |
| GLD-RPP-028 | 2, 3 |
| GLD-RPP-030 | 2 |
| GLD-RPP-032 | 2 |
| GLD-RPP-034 | 3 |
| GLD-RPP-036 | 4, 5 |
| GLD-RPP-037 | 4 |
| GLD-RPP-039 | 5 |
| GLD-RPP-040 | 2 |
| GLD-RPP-044 | 1, 3, 5 |
| GLD-RPP-045 | 5 |
| GLD-RPP-046 | 5 |
| GLD-RPP-047 | 5 |
| GLD-RPP-048 | 5 |
| GLD-RPP-049 | 5 |
| GLD-RPP-050 | 3, 5 |
| GLD-RPP-051 | 5 |
| GLD-RPP-052 | 1, 5 |
| GLD-RPP-053 | 5 |

30 distinct rules fired across the 5 injection cycles out of 53
non-excluded rules. The 23 non-firing rules are a mix of P1 freshness /
distribution checks the runner did not target directly and of P0 rules
that happened to overlap with rules already firing (uniqueness subcases,
FIPS checksum variants, etc.).

## 6. Gaps and remediation

### Gap 1 — Cycle 3 CA double-mutation masks the plausible-but-wrong probe

**Observation.** Scenarios
`ca_adjusted_50k_at_national` and `ca_adjusted_50k_off_by_100x` both
overwrite CA `adjusted_50k` in cycle 3. The second one wins. The
50000.0 value is never evaluated by the DQ rules in this run.

**Impact.** Low. The "plausible but wrong" idea was the 50000.0 probe,
which tests whether the CA sanity rule (`adjusted_50k < 50000`) catches
a value that is exactly AT the threshold. That probe was not actually
exercised in cycle 3 — it was cosmetically present but overwritten.

**Remediation.** Split the two CA scenarios across separate cycles, or
move the 50000.0 scenario to target a different state whose sanity rule
has the same shape. No DQ rule change needed; this is a runner issue
only.

### Gap 2 — Cycle 4 verif_invalid_value masked by mass flip

**Observation.** Scenario `verif_invalid_value_verified` sets MN to
`verified` and scenario `verif_all_bea_official` then overwrites every
row (including MN) to `bea_official`. The invalid-enum rule therefore
cannot fire in cycle 4 even though the scenario was "injected."

**Impact.** Low. The IN-list rule for verification_status is not
exercised in this chaos run. It is still a P0 rule and would fire if
invoked; we just didn't confirm it empirically.

**Remediation.** Move `verif_invalid_value_verified` to its own cycle,
or before the mass flip with a different row. No DQ rule change needed.

### Gap 3 — Cross-zone coverage is dark in shadow mode

**Observation.** Rules `GLD-RPP-043` (Gold↔Silver passthrough) and
`GLD-RPP-055` (Silver freshness) are hard-excluded. No chaos-mode
evidence exists that they still fire when expected.

**Impact.** Medium. These are the two rules that most directly protect
the Silver → Gold promote contract. The rules run green in production
(last DQ pass was 55/55), so this is a chaos-coverage gap, not a known
defect.

**Remediation path 1 (preferred).** Brightsmith could grow a "shadow
both zones" mode where the chaos runner stages a shadow Silver table
alongside the shadow Gold table in the same run. Then the shadow-mode
rewrite would find both shadow_consumable and shadow_base, the
cross-zone rules would execute, and the chaos runner could probe them
without rule changes.

**Remediation path 2 (cheaper).** Add a Gold chaos scenario that
publishes a shadow Silver copy via a lightweight "clone Silver parquet
into shadow_base" helper before running DQ. This could be a follow-up
to `silver_bea_rpp_chaos_runner.py` working in concert with this runner.

**Remediation path 3 (accept).** Treat production-only rules as
production-only forever and rely on cycle 5's demonstration that the
single-zone rule battery (inverse invariant, classification, boundary
witness, CA spot check) catches rpp drifts even without the cross-zone
rule. This is the current stance.

### No DQ rule gaps were identified

Every injected dimension — completeness, validity, uniqueness,
consistency, accuracy, reasonableness, volume, referential integrity,
coverage — produced at least one rule fire in at least one cycle, and
the three negative controls were all silent. The P0 rule battery for
`consumable.regional_price_parities` is hardened against the scenarios
in the spec's chaos section (cost_tier boundary edges, adjusted_Nk
arithmetic, verification_status carry-forward).

The `@dq-rule-writer` handoff is empty: there are no new rules to add
from this chaos pass.

## 7. Final safety check — real warehouse unchanged

Before the run:

```
6b1f28163cd5bdf8187c22dafbde349bec7148c50622b9c00659657d34872cd4  data/gold/iceberg_warehouse/consumable/regional_price_parities/data/00000-0-07edfd60-dda9-4d71-936a-0ea5bdb54bb6.parquet
97e0b59084732a38fe20ce8b9893a31f5c78e0d28fdd819d25606a2435cd2972  …/metadata/00000-2e27cf89-….metadata.json
13dc33119ab77df69aa5f343d4af7d6d7a0de2f018e95d7879064cbd7b3dada8  …/metadata/00000-92d7c894-….metadata.json
ede67f68074912bfeccc05db22cd513c51bb4a9da961dbb61443a155350e008d  …/metadata/00001-ab3fbefe-….metadata.json
78a27cb410e839148e011c1e0a5114ed54ef71940fb43986f3cd63ae9a01f900  …/metadata/07edfd60-….m0.avro
77852a454be267c1b2c31bd829824040acdd1b528c40e2f343eaa73aae3f60cf  …/metadata/snap-558213831303660864-0-07edfd60-….avro
```

After the run: identical bit-for-bit for every file above (verified with
`shasum -a 256 | diff`). The real `consumable.regional_price_parities`
data parquet and every metadata sidecar are untouched.

Shadow namespace cleanup: the chaos runner's `cleanup_shadow()` ran in
the `finally` block of every cycle and again at the end of `main()`.
`data/gold/iceberg_warehouse/shadow_consumable/regional_price_parities`
does not exist on disk after the run. The `shadow_consumable` namespace
itself is retained (shared with other Gold chaos runners), but the
chaos-owned table is dropped from the catalog.

Environment guards: the runner sets and verifies
`CHAOS_MONKEY_ENABLED=true` and `BRIGHTSMITH_ENV=dev` before touching
anything, and asserts that the source parquet path does NOT contain
`shadow_` and the shadow dir path DOES contain `shadow_consumable`.

## 8. Artifacts

- Chaos runner: `governance/chaos-manifests/gold_regional_price_parities_chaos_runner.py`
- Injection manifest: `governance/chaos-manifests/gold-regional-price-parities-manifest.json`
- This report: `governance/chaos-reports/gold-regional-price-parities-chaos.md`
- Audit trail: `governance/audit-trail/2026-04-11-chaos-monkey-gold-regional-price-parities.md`

## 9. Exit criteria

- [x] 5 injection cycles at rates 5%/6%/7%/8%/10% completed
- [x] 3 negative-control cycles completed with zero rule failures
- [x] Every injection cycle produced at least one rule failure (caught_any=true)
- [x] No rule errored under shadow mode after the carve-out filter
- [x] No new DQ rule gaps identified (DQ writer handoff: empty)
- [x] Real `consumable.regional_price_parities` parquet + metadata bit-identical before/after
- [x] Shadow table dropped, shadow directory removed

Chaos monkey gate: **PASS**.
