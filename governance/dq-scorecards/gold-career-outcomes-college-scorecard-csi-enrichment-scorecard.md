# DQ Scorecard — gold-career-outcomes-college-scorecard (CSI enrichment)

**Scope:** Post-promote verification of the CSI (College Scorecard Institution) enrichment that added 7 institution-level attribute columns to `consumable.career_outcomes` via a LEFT JOIN against `silver_base.college_scorecard_institution` on `unitid`. This scorecard verifies the 9 new `GLD-CSI-*` rules pass and the 42 existing `GLD-CO-*` rules remain green (no regression).

| Field | Value |
|-------|-------|
| Spec | `gold-career-outcomes-college-scorecard` |
| Zone | Gold (`consumable`) |
| Table | `consumable.career_outcomes` |
| Source | Iceberg warehouse (`data/gold/iceberg_warehouse`) |
| Executed at | 2026-04-16T16:21:06Z |
| Run ID | `9dd4463a` |
| Evidence hash | `1f57cd28e28b296b` |
| Result file | `governance/dq-results/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T162106Z.json` |
| Executor | `scripts/dq_execute_gold_csi_iceberg.py` |
| Rules loaded | `governance/dq-rules/gold-career-outcomes-college-scorecard.json` |

---

## Priority Gate Summary

| Gate | Count | Passed | Failed | Errored | Status |
|------|------:|-------:|-------:|--------:|:------:|
| **P0 (hard block)** | 25 | 25 | 0 | 0 | **PASS** |
| **P1 (warning)** | 22 | 22 | 0 | 0 | **PASS** |
| **P2 (informational)** | 4 | 4 | 0 | 0 | **PASS** |
| **Total** | **51** | **51** | **0** | **0** | **PASS** |

All 51 rules PASS. The P0 gate is CLEAR; spec completion is unblocked from the DQ side.

---

## GLD-CSI-* — New enrichment rules (9/9 PASS)

These rules are new with the CSI enrichment and target the 7 added columns (`institution_control`, `cost_of_attendance_annual`, `cost_of_attendance_4yr`, `net_price_annual`, `net_price_4yr`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`). Status in the rules file remains `proposed` — @staff-engineer is the approver; no status was changed as part of this execution. They were executed directly against the real Iceberg table via the Iceberg-backed runner pattern.

| Rule | Priority | Actual | Threshold | Status |
|------|:--------:|-------:|-----------|:------:|
| GLD-CSI-001 — CSI enrichment preserves row count exactly | P0 | 0 | `result = 0` (row count = 69,947) | PASS |
| GLD-CSI-002 — Net price cannot exceed cost of attendance | P0 | 0 | `result = 0` | PASS |
| GLD-CSI-003 — 4-year net price equals annual × 4 (±$1) | P0 | 0 | `result = 0` | PASS |
| GLD-CSI-004 — Net price lower bound respects BT-111 legitimate negatives (≥ −$10,000) | P0 | 0 | `result = 0` | PASS |
| GLD-CSI-005 — `net_price_annual` completeness ≥ 90% | P1 | 0 | `result = 0` (coverage 95.45%) | PASS |
| GLD-CSI-006 — `cost_of_attendance_annual` completeness ≥ 90% | P1 | 0 | `result = 0` (coverage 95.45%) | PASS |
| GLD-CSI-007 — `institution_control` completeness ≥ 95% | P1 | 0 | `result = 0` (coverage 97.42%) | PASS |
| GLD-CSI-008 — Unmatched UNITID count ≤ 300 | P1 | 0 | `result = 0` (actual 207) | PASS |
| GLD-CSI-009 — `institution_control` value set (Public / Private nonprofit / Private for-profit) | P2 | 0 | `result = 0` | PASS |

All 9 results exactly match the EDA predictions in `docs/sessions/eda-gold-career-outcomes-csi-enrichment.md`:

- Row count invariant preserved (69,947).
- NP ≤ COA with 0 violations (Silver invariant carried forward cleanly).
- 4yr = 4 × annual derivation holds within $1 tolerance.
- −$10,000 floor holds; Silver minimum was −$1,180 (headroom ~$8.8k).
- NP / COA coverage 95.45% (buffer 5.45pp above the 90% floor).
- `institution_control` coverage 97.42% (buffer 2.42pp above the 95% floor).
- Unmatched UNITIDs = 207 (buffer of 93 below the 300 ceiling, ~45% headroom).
- `institution_control` canonical enum: 0 out-of-set.

---

## GLD-CO-* — Regression suite (42/42 PASS)

Existing `active` rules re-executed against the freshly promoted table. Zero regressions from the addition of 7 columns.

### P0 regression (19/19 PASS)

| Rule | Actual | Status |
|------|-------:|:------:|
| GLD-CO-001 — Grain uniqueness (unitid × cipcode × credential_level) | 0 | PASS |
| GLD-CO-002 — record_id uniqueness | 0 | PASS |
| GLD-CO-003 — Row count within 59,455–80,439 | 0 | PASS |
| GLD-CO-004 — earnings_1yr p25 ≤ p75 | 0 | PASS |
| GLD-CO-005 — earnings_2yr p25 ≤ p75 | 0 | PASS |
| GLD-CO-006 — debt p25 ≤ p75 | 0 | PASS |
| GLD-CO-007 — confidence_tier NOT NULL | 0 | PASS |
| GLD-CO-008 — confidence_tier value set | 0 | PASS |
| GLD-CO-009 — has_earnings accuracy | 0 | PASS |
| GLD-CO-010 — has_debt accuracy | 0 | PASS |
| GLD-CO-011 — outcome_completeness value set | 0 | PASS |
| GLD-CO-012..016 — Null propagation invariants | 0 | PASS |
| GLD-CO-017 — DTE tier null iff ratio null | 0 | PASS |
| GLD-CO-018 — DTE tier value set | 0 | PASS |
| GLD-CO-029 — confidence_tier = insufficient iff no outcome data | 0 | PASS |
| GLD-CO-030 — confidence_tier = high requires large cohort + complete data | 0 | PASS |
| GLD-CO-031 — outcome_completeness ≡ count(non-null core) / 3 | 0 | PASS |
| GLD-CO-032 — Required identity fields NOT NULL | 0 | PASS |
| GLD-CO-033 — Derived quality fields NOT NULL | 0 | PASS |
| GLD-CO-036 — credential_level = 3 | 0 | PASS |
| GLD-CO-038 — DTE tier boundaries match ratio | 0 | PASS |

### P1 regression (13/13 PASS)

All distribution / range / coverage bounds hold: DTE tier plurality (Low ≥ Moderate), `Low` rate 60–80%, `High+Very High` ≤ 3%, `insufficient` rate 45–60%, `high` rate 15–30%, negative growth rate 35–55%, earnings_growth_rate range, PERCENT_RANK ∈ [0, 1], distinct-institution coverage 2,200–3,000, distinct-CIP-families 40–50, PVI = 1 / DTE, null percentile bands only for small CIP families. All 0 violations.

### P2 regression (4/4 PASS)

| Rule | Actual | Note |
|------|-------:|------|
| GLD-CO-039 — institution_control null rate tracking | 2.6% | Previously 100% NULL (Silver blocker). Resolved by this enrichment. Tracking value drops from 100 to 2.6, well within the ≤ 100 ceiling. GLD-CSI-007 now supersedes this with the tighter 95% floor. |
| GLD-CO-040 — CIP families with null 1yr bands ≤ 10 | 0 | PASS |
| GLD-CO-041 — Mean DTE 0.50–0.80 | 0 | PASS |
| GLD-CO-042 — Mean earnings growth rate −0.05 to +0.10 | 0 | PASS |

---

## Evidence / Supplementary Stats

| Metric | Value |
|--------|------:|
| Total rows | 69,947 |
| Distinct UNITIDs | 2,559 |
| Distinct record_ids | 69,947 (= total rows → surrogate key intact) |
| Schema columns | 37 |
| `net_price_annual` coverage | 95.45% |
| `cost_of_attendance_annual` coverage | 95.45% |
| `net_price_4yr` coverage | 95.45% (co-null with annual, as expected) |
| `institution_control` coverage | 97.42% |
| Unmatched UNITIDs (all 3 CSI fields null) | 207 |

### `institution_control` distribution (post-join)

| Control | Rows | % of total |
|---------|-----:|-----------:|
| Private nonprofit | 37,211 | 53.20% |
| Public | 29,374 | 41.99% |
| Private for-profit | 1,558 | 2.23% |
| (null — unmatched UNITID) | 1,804 | 2.58% |

### Cross-check with EDA predictions (`docs/sessions/eda-gold-career-outcomes-csi-enrichment.md`)

| EDA-predicted | Observed | Match |
|---------------|----------|:-----:|
| Row count 69,947 | 69,947 | yes |
| NP/COA coverage ≈ 95.45% | 95.45% / 95.45% | yes |
| `institution_control` coverage ≈ 97.42% | 97.42% | yes |
| Unmatched UNITIDs ≈ 207 | 207 | yes |
| NP ≤ COA: 0 violations | 0 | yes |
| 4yr = 4 × annual: 0 violations | 0 | yes |
| NP floor −$10k: 0 violations | 0 | yes |

---

## Regression Status

**No regressions.** All 42 `GLD-CO-*` rules that were active before CSI enrichment remain at PASS status against the re-promoted table. The 7 new columns are additive; no existing semantics changed. `GLD-CO-039` (institution_control null-rate tracker) observed a dramatic improvement from 100% null to 2.6% null — this is the expected resolution of the Silver institution-control blocker and does not indicate drift.

---

## P0 Gate Decision

**P0 gate: PASS.** No hard-block failures. The DQ side of spec completion for the CSI enrichment is unblocked. Remaining pipeline steps (governance-reviewer post-check, staff-engineer approval of the GLD-CSI-* rules promoting them from `proposed` → `active`, chaos-monkey, lineage/CDE/doc-generator, adversarial-auditor) proceed independently.

## Artifacts

- Results JSON (authoritative): `/Users/jcernauske/code/bright/futureproof-data/governance/dq-results/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T162106Z.json`
- Executor script: `/Users/jcernauske/code/bright/futureproof-data/scripts/dq_execute_gold_csi_iceberg.py`
- Rules source: `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/gold-career-outcomes-college-scorecard.json`
- EDA reference: `/Users/jcernauske/code/bright/futureproof-data/docs/sessions/eda-gold-career-outcomes-csi-enrichment.md`
