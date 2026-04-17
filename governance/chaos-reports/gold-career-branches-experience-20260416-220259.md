# Chaos Monkey Adversarial DQ Report — consumable.career_branches (experience columns)

- **Spec:** `onet-experience-requirements` (§Zone 3)
- **Target:** `consumable.career_branches` — the 4 additive experience columns:
  - `related_experience_years`
  - `related_experience_tier`
  - `source_experience_years`
  - `experience_delta_years`
- **Transformer:** `src/gold/futureproof_engine.py::derive_br_rows`
- **Runner:** `scripts/gold_career_branches_experience_chaos_runner.py`
- **Output artifact:** `scripts/_gold_career_branches_experience_chaos_output.json`
- **Report timestamp:** 20260416-220259
- **Information barrier:** enforced — `governance/dq-rules/gold-career-branches-experience.json` was NOT read. Rule predicates used for probes are (a) the user-provided reference `GLD-CB-EXP-002: -12 ≤ experience_delta_years ≤ 12` (from the task brief), (b) spec §Zone 3 text predicates (`-10 ≤ delta ≤ 15`, `tier='senior' ⇒ years ≥ 8`).

## Method

In-memory mutations to the list-of-dict representation of `base.onet_experience_profiles` rows, passed via the `onet_experience_rows` kwarg of `derive_br_rows`. **NO real tables — shadow, silver, or gold — are touched.** The transformer is the system under test; we do not modify it.

Each scenario:
1. Starts from a 5-transition × 9-Silver-row baseline.
2. Applies one perturbation (drop, corrupt, extend).
3. Calls `derive_br_rows(...)` and captures all 34 columns of each resulting branch plus any exception.
4. Evaluates three Gold-level rule predicates against the output.
5. Produces invariant checks specific to the scenario and assigns a disposition.

Five cycles at escalating rates (5%, 6%, 7%, 8%, 10%) are driven — but because these are targeted in-memory perturbations rather than row-sample-rate injections, all 9 scenarios are re-run each cycle. The cycle loop confirms determinism (every scenario produces the same disposition in every cycle) rather than scaling the corruption.

## Baselines

- **Clean baseline** (5 transitions, 9 Silver rows, all populated): all 4 experience columns populated on every branch; deltas in {−11.25, +2.0, +4.0, −2.0, +6.0}; no predicate violations under the user-quoted `-12..12` rule; 1 violation under the spec-text `-10..15` rule due to the `Chief Executives → Retail Salespersons` branch (`0.75 − 12.0 = −11.25` is inside `-12..12` but outside `-10..15`).
- This baseline "noise" is present across many scenarios because the 11-1011 → 41-2031 branch persists in each fixture unless the scenario explicitly prunes it. It is not an artefact introduced by chaos — it is a design-intent delta (entry-level branch off a senior source) and is surfaced here as an observation for the rule writer, not attributed to any scenario.

## Cycle summary

| Cycle | Rate | Scenarios run | PASS | ACCEPTABLE | GAP |
|:----:|:----:|:--------------|:----:|:----------:|:---:|
| 1 | 5%  | all 9 | 7 | 2 | 0 |
| 2 | 6%  | all 9 | 7 | 2 | 0 |
| 3 | 7%  | all 9 | 7 | 2 | 0 |
| 4 | 8%  | all 9 | 7 | 2 | 0 |
| 5 | 10% | all 9 | 7 | 2 | 0 |

**Dispositions are deterministic across cycles** — no scenario flapped between PASS/GAP/ACCEPTABLE across cycles. `7 PASS + 2 ACCEPTABLE + 0 GAP` per cycle.

## Per-scenario matrix

| # | Scenario | Input perturbation | Gold output | Rule check outcome | Disposition |
|:--:|:---------|:-------------------|:------------|:-------------------|:-----------:|
| 1 | Silver-missing-for-source | Dropped all Silver rows whose `bls_soc_code` is a source SOC in the fixture | `source_experience_years=NULL` and `experience_delta_years=NULL` on all 5 branches; related side still populated | No rule tripped (null rows excluded from predicates) | **PASS** |
| 2 | Silver-missing-for-related | Dropped all Silver rows whose `bls_soc_code` is a related SOC | `related_experience_years=NULL`, `related_experience_tier=NULL`, `experience_delta_years=NULL` on all 5 branches; source side still populated | No rule tripped | **PASS** |
| 3 | Silver-tier-invalid | Set `experience_tier='unknown'` on Silver row for `11-3021` | Gold propagates `related_experience_tier='unknown'` verbatim | No Gold DQ rule for tier enum; Silver DQ is authoritative | **ACCEPTABLE** |
| 4 | Silver-years-negative | Set `experience_years_typical=-1.0` on Silver row for `15-1252` | Gold propagates `source_experience_years=-1.0`; `experience_delta_years` inflates by +1 (becomes 10.0 on `15-1252→11-3021`) | No Gold negative-years guard; spec-text `-10..15` delta rule happens to still pass on the affected branch | **ACCEPTABLE** |
| 5 | Silver-years-extreme (12.5) | Set `experience_years_typical=12.5` on Silver row for `11-3021` | `experience_delta_years = 12.5 − 7.0 = 5.5` exactly — correctly represented | All three rules evaluate: user-quoted OK, senior-years OK, spec-range's `-11.25` violation is from unrelated baseline branch | **PASS** |
| 6 | Cross-zone tier contradiction | Set `years=7.0` and `tier='senior'` on Silver row for `11-3021` (should be `mid` per 4–8 threshold) | Gold propagates contradiction verbatim — but the senior-years≥8 Gold DQ rule FIRES (1 violation) | `GLD-CB-EXP-senior-years (>=8 when tier=senior)` catches it as designed | **PASS** |
| 7 | Empty Silver table | `base.onet_experience_profiles` has zero rows | All 5 branches materialize with all 4 experience columns NULL; non-experience columns intact | No rule tripped | **PASS** |
| 8 | Duplicate BLS SOC in Silver | Appended duplicate Silver row for `11-3021` (years=2.0, tier=early) on top of baseline (years=9.0, tier=senior) | `last-one-wins`: Gold resolves to years=2.0, tier=early (dict-comprehension overwrite semantics) | Deterministic; no error | **PASS** |
| 9 | Sparse Silver — delta-range coverage | Pruned Silver to `{11-1011, 41-2031}` only; 4 branches have NULL deltas, 1 has `-11.25` | NULL branches excluded from all predicates; sole non-null delta (`-11.25`) passes user-quoted `-12..12` but trips spec-text `-10..15` | Both rules behave correctly on NULLs; the `-10..15` trip exposes a rule-calibration tension | **PASS** |

## Key behavioral findings

1. **NULL propagation is robust.** Scenarios 1, 2, 7 — three distinct ways to remove Silver data — all produce the spec-mandated `(NULL, NULL, NULL, NULL)` tuple on affected branches. No exceptions, no coalesce-to-zero leakage, no row-drops. Confirms the §Zone 3 rationale for the CASE-WHEN rewrite (away from `COALESCE(..., 0) − COALESCE(..., 0)`) is implemented correctly.

2. **Gold is pure passthrough on Silver-invalid values** (scenarios 3, 4). Gold has no enum check for `experience_tier`, no non-negative check for `experience_years_typical`, and no upper-bound check at the transformer layer. The spec explicitly says `tier flows through verbatim from Silver` (§Test Matrix), and the spec's own Silver DQ rules (`experience_tier IN (…)` P0, `0 ≤ years ≤ 15` P0) are the authoritative guards. These are labelled ACCEPTABLE rather than GAP because they match the zone architecture — adding redundant Gold checks for already-P0-gated Silver fields is not required by spec.

3. **The senior-tier years≥8 Gold DQ rule is the one place Gold adds true cross-zone defense-in-depth** (scenario 6). When Silver and Gold disagree (e.g. years=7 but tier=senior), this rule catches the contradiction at the Gold layer. Confirmed to fire as designed.

4. **Dict-comprehension lookup is last-one-wins and deterministic** (scenario 8). Not a problem in practice because Silver grain-uniqueness is P0 — but the Gold code deserves a one-line comment explaining the contract (either "last-one-wins" or "use the last row DuckDB emits in iteration order"). Low priority.

5. **Rule-calibration tension between spec text and user-quoted rule ID** (scenario 9). The spec §Zone 3 explicitly states `experience_delta_years range: -10 ≤ delta ≤ 15` as a P1 DQ rule. The user's task brief names the live rule as `GLD-CB-EXP-002: -12 ≤ delta ≤ 12`. The real `Chief Executives → Retail Salespersons` branch produces `-11.25`, which:
   - Passes `GLD-CB-EXP-002 (-12..12)` ← live rule per user
   - Fails the spec-stated `-10..15` text ← if the spec were executed verbatim
   Either the spec text or the rule drifted during rule writing. The live rule (per the user's brief) is the more-permissive, more-correct bound for real data. **This is not a Gold transformer bug** — it's a specification/rule-artefact mismatch worth surfacing to `@dq-rule-writer` for reconciliation. If the live rule is `-12..12`, the spec text should be updated to match. If `-10..15` is still the authoritative bound, the rule file needs tightening and the baseline real data will trip it.

## Gaps

**None blocking.** Zero GAP dispositions across all 5 cycles × 9 scenarios = 45 scenario-cycle evaluations.

Two ACCEPTABLE dispositions reflect deliberate zone-architecture choices (Gold trusts Silver P0 DQ for enum and non-negative-years gates), not defense-in-depth gaps that warrant new Gold rules.

## Proposed new Gold DQ rules

None blocking. Three optional / nice-to-have recommendations follow:

1. **(Optional, low priority)** A Gold rule `related_experience_years ≥ 0 AND source_experience_years ≥ 0 WHERE NOT NULL`. This is pure defense-in-depth against Silver regression. Silver already has a P0 `0 ≤ years ≤ 15` rule; Gold duplication would only matter if Silver DQ were skipped. Marginal ROI.

2. **(Observation, not a new rule)** `@dq-rule-writer` to reconcile the `-12 ≤ delta ≤ 12` live rule with the spec-text `-10 ≤ delta ≤ 15`. Ideally the spec §Zone 3 is patched to match the live rule, since `-11.25` is a real value for entry-level branches off senior sources (e.g. `Chief Executives → Retail Salespersons`). No Gold transformer change needed either way.

3. **(Documentation, not a rule)** Add a one-line comment in `derive_br_rows` near `exp_by_soc = {...}` documenting last-one-wins semantics for the theoretically-impossible Silver grain-duplicate case. Non-functional; aids future readers.

## Adversarial-auditor disposition

Per §Phase 2 step 16 of the spec: **RECOMMEND SKIP for `bs:adversarial-auditor`** on the Gold zone's experience columns.

Justification: 5 cycles of targeted probing at the Silver→Gold join boundary with 9 scenarios covering all six Silver-failure modes (missing-source, missing-related, invalid-enum, negative, extreme, contradictory), the empty-table degenerate case, the grain-duplicate edge case, and the sparse-delta rule-applicability case. Zero GAPs. All NULL-propagation invariants from §Zone 3 verified. The one cross-zone Gold DQ rule (`senior ⇒ years ≥ 8`) was specifically adversarially probed (scenario 6) and fires as designed.

## Verdict

**CLEAN** — 0 gaps across 5 cycles × 9 scenarios.
