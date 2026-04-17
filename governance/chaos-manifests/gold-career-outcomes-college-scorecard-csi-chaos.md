# Chaos Monkey — CSI Enrichment Rules After-Action Report

**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md`
**Table (real Iceberg):** `consumable.career_outcomes` (brightsmith catalog)
**Rules under test:** GLD-CSI-001 … GLD-CSI-009 (9 rules)
**Baseline:** 69,947 rows × 37 cols, clean DQ 51/51 PASS at evidence hash `1f57cd28e28b296b` (run `9dd4463a`)
**Runner:** `governance/chaos-manifests/gold_career_outcomes_csi_chaos_runner.py`
**Manifest:** `governance/chaos-manifests/gold-career-outcomes-csi-manifest.json`
**Cycles:** 5 (seeds 43, 44, 45, 46, 47)
**Pattern:** Shadow-corruption — real Iceberg snapshot cloned into DuckDB memory, corrupted in-memory per scenario, rules re-executed. Production table never mutated.

## Scenario Plan

Each scenario targets a specific CSI rule. Every scenario is applied to a **fresh clone** of the 69,947-row baseline so that rule attribution is unambiguous. All 9 rule SQLs are executed against every corrupted shadow; collateral firings (where a scenario trips an adjacent rule as a side-effect) are recorded but not counted as detection.

| # | Target Rule | Dimension | Scenario | Expected Detection |
|---|-------------|-----------|---------------------------------------------|--------------------|
| 1 | GLD-CSI-001 | Volume         | Drop 100 rows → count = 69,847            | count ≠ 69,947 |
| 2 | GLD-CSI-002 | Consistency    | Inflate `net_price_annual` to 1.5 × COA on 50 rows | NP > COA on 50 rows |
| 3 | GLD-CSI-003 | Consistency    | Set `net_price_4yr = net_price_annual × 2` on 30 rows | 30 rows violate 4× invariant |
| 4 | GLD-CSI-004 | Validity       | Set `net_price_annual = -$50,000` on 10 rows | 10 rows < -$10k floor |
| 5 | GLD-CSI-005 | Completeness   | Null `net_price_annual` on 10% of rows      | coverage drops below 90% |
| 6 | GLD-CSI-006 | Completeness   | Null `cost_of_attendance_annual` on 10% of rows | coverage drops below 90% |
| 7 | GLD-CSI-007 | Completeness   | Null `institution_control` on 10% of rows   | coverage drops below 95% |
| 8 | GLD-CSI-008 | Validity       | Fabricate 500 phantom unmatched UNITIDs (null all 3 CSI attrs) | unmatched count > 300 |
| 9 | GLD-CSI-009 | Consistency    | Set `institution_control = 'Unknown'` on 25 rows | 25 rows out of 3-value enum |

## Negative Control (clean baseline)

All 9 GLD-CSI-* rules PASS against the unmutated 69,947-row real snapshot. Zero false positives. This matches the pipeline's clean DQ run (`9dd4463a`, hash `1f57cd28e28b296b`).

| Rule | Violations on clean baseline | Verdict |
|------|------------------------------|---------|
| GLD-CSI-001 | 0 | PASS |
| GLD-CSI-002 | 0 | PASS |
| GLD-CSI-003 | 0 | PASS |
| GLD-CSI-004 | 0 | PASS |
| GLD-CSI-005 | 0 | PASS |
| GLD-CSI-006 | 0 | PASS |
| GLD-CSI-007 | 0 | PASS |
| GLD-CSI-008 | 0 | PASS |
| GLD-CSI-009 | 0 | PASS |

## Per-Cycle Evidence

Legend: `target_value` is the scalar returned by the target rule's SQL (row count for `result_count` rules, scalar flag for `result = 0` rules). `fired = True` ⇒ detected.

### Cycle 1 — seed 43

| Rule | Scenario | Target Value | Fired | Collateral firings |
|------|-----------|--------------|-------|---------------------|
| GLD-CSI-001 | drop_100_rows | 1 | True | — |
| GLD-CSI-002 | netprice_gt_coa_50rows | 50 | True | GLD-CSI-003 |
| GLD-CSI-003 | netprice4yr_mismatch_30rows | 30 | True | — |
| GLD-CSI-004 | netprice_below_floor_10rows | 10 | True | GLD-CSI-003 |
| GLD-CSI-005 | null_netprice_10pct | 1 | True | — |
| GLD-CSI-006 | null_coa_10pct | 1 | True | — |
| GLD-CSI-007 | null_instctrl_10pct | 1 | True | — |
| GLD-CSI-008 | phantom_500_unmatched_unitids | 1 | True | GLD-CSI-005, GLD-CSI-006, GLD-CSI-007 |
| GLD-CSI-009 | bad_instctrl_value_25rows | 25 | True | — |

**Detection: 9/9 (100%).**

### Cycle 2 — seed 44

Same scenario plan; results identical to Cycle 1.
**Detection: 9/9 (100%).** Target values: {001:1, 002:50, 003:30, 004:10, 005:1, 006:1, 007:1, 008:1, 009:25}.

### Cycle 3 — seed 45

**Detection: 9/9 (100%).** Target values identical.

### Cycle 4 — seed 46

**Detection: 9/9 (100%).** Target values identical.

### Cycle 5 — seed 47

**Detection: 9/9 (100%).** Target values identical.

## Summary

| Metric | Value |
|--------|-------|
| Cycles executed | 5 |
| Total scenario invocations | 45 (9 scenarios × 5 cycles) |
| Detections | 45/45 |
| Detection rate | **100.0%** |
| False positives on clean baseline | 0/9 |
| Gaps found | 0 |
| Cycles with zero new gaps | 5 (exit criterion satisfied after cycle 2 per 2-consecutive rule) |

## Collateral Firings — Interpretation

Collateral firings are not gaps; they are **cascade detections** that validate rule orthogonality:

- **CSI-002 → CSI-003**: Inflating `net_price_annual` to 1.5 × COA necessarily breaks `net_price_4yr = net_price_annual × 4` because `net_price_4yr` was not also updated. Expected.
- **CSI-004 → CSI-003**: Setting `net_price_annual = -$50,000` without touching `net_price_4yr` breaks the 4× derivation. Expected.
- **CSI-008 → CSI-005 / CSI-006 / CSI-007**: Phantom-unmatched UNITIDs null all three enriched attributes across every row for those UNITIDs (500 UNITIDs × multiple rows each), pushing all three completeness rates below their respective floors. Expected — completeness and entity-coverage rules probe the same underlying join.

The cascades are benign and predictable from the logical-model relationships the spec documents.

## Verdict

**PASS — CSI rule suite hardened.** The 9 GLD-CSI-* rules collectively achieve 100% detection across 5 independent chaos cycles with deterministic attribution for each corruption class declared in spec §Zone 3. No gaps identified; no new rules needed. The exit condition *(no new gaps for 2 consecutive cycles)* is satisfied; we ran all 5 for completeness of evidence.

Rules are cleared for the DQ rule writer's `proposed → active` status transition and for the governance-reviewer-post gate.
