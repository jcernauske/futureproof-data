# Audit Trail: Silver DQ Execution (Re-run, 23 rules)

**Spec:** silver-base-college-scorecard-institution
**Agent:** @dq-engineer
**Date:** 2026-04-16T04:28:01Z
**Run ID:** 21e6a396
**Prior Run:** 6bb600a5 (2026-04-16T03:45:32Z, 17 rules, 17/17 PASS)

## Trigger

@dq-rule-writer expanded the rule set from 17 to 23 rules, adding SLV-CSI-018 through SLV-CSI-023. This re-execution validates the expanded suite against the same Bronze-derived Silver snapshot used in the prior run.

## Rules Executed

23 rules total, picked up automatically by `scripts/dq_execute_silver_csi.py` from `governance/dq-rules/silver-base-college-scorecard-institution.json`:
- 12 P0 (was 11; added SLV-CSI-018)
- 9 P1 (was 5; added SLV-CSI-019, 020, 021, 022)
- 2 P2 (was 1; added SLV-CSI-023)

## Results Summary

| Priority | Total | Pass | Fail | Gate |
|----------|------:|-----:|-----:|------|
| P0 | 12 | 12 | 0 | **PASS (hard gate)** |
| P1 | 9 | 8 | 1 | FAIL (warning, SLV-CSI-022) |
| P2 | 2 | 1 | 1 | FAIL (informational, SLV-CSI-023) |
| **Total** | **23** | **21** | **2** | **P0 gate: PASS** |

## P0 Gate Decision

**P0 gate: PASS.** The spec is not blocked. All 12 P0 rules (including the new SLV-CSI-018 state_abbr regex) pass with zero violations.

## P1 Failure — SLV-CSI-022 (room_board_off_campus range [$1,000, $30,000])

Actual: 4 violations. Cap is $30,000; Bronze max is $39,100.

Violating rows (all legitimate published COA data, not transformation defects):
- 486354 United International College (FL, Priv-FP): $39,100
- 117672 Southern California University of Health Sciences (CA, Priv-NP): $34,500
- 123509 Skyline College (CA, Public): $31,288
- 122375 San Diego Mesa College (CA, Public): $30,736

The rule evidence cites the EDA-recommended range as [$2,000, $40,000]. The post-governance decision to narrow to [$1,000, $30,000] with a `result_count = 0` threshold is inconsistent with the documented intent ("flag higher values as outliers rather than widen the range") — a `result_count = 0` threshold cannot accommodate any flagged outliers.

## P2 Failure — SLV-CSI-023 (books_supplies range [$0, $5,000])

Actual: 3 violations. Cap is $5,000; Bronze max is $9,741.

Violating rows (plausible at cited institutions):
- 217864 The Citadel (SC, Public): $9,741 — military uniform-and-book requirements
- 207254 Spartan College of Aeronautics and Technology (OK, Priv-FP): $6,278 — aviation kits
- 205391 The Modern College of Design (OH, Priv-FP): $5,941 — design materials

The rule evidence cites the EDA-recommended range as [$0, $10,000]. The post-governance decision to narrow to [$0, $5,000] was based on the rationale that *"outliers above $5K are more likely data-entry issues than legitimate costs"* — the three observed cases do not clearly fit that pattern.

## Regression Check vs. Prior Run

All 17 original rules produced identical actual values to the prior run (run_id 6bb600a5):
- SLV-CSI-015 q1>q5 inversions: 46 (unchanged)
- net_price_annual coverage: 73.48% overall (unchanged)
- Coverage by control: 89.27% / 70.64% / 52.63% (unchanged)
- All P0 rules at 0 violations (unchanged)

**No regressions.** No new P0 failures introduced by the expanded ruleset. The two failures are both on new rules, not pre-existing rules.

## Escalation

Per @dq-engineer role boundaries: I do not modify rule thresholds or override gate decisions. Escalating to @governance-reviewer with two concrete resolution paths for each failure (widen threshold vs. relax `result_count = 0` to a small positive integer). Recommended fix in both cases is to adopt the EDA-recommended ranges ($40K cap and $10K cap respectively), which would also require updating the corresponding physical-model CHECK constraints in lockstep.

Scorecard documents the resolution options: `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md`

## Artifacts

- Results JSON: `governance/dq-results/silver-base-college-scorecard-institution-20260416T042801Z.json`
- Scorecard: `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md`
- Rules source: `governance/dq-rules/silver-base-college-scorecard-institution.json`
- Driver: `scripts/dq_execute_silver_csi.py`

---

*Logged by @dq-engineer on 2026-04-16T04:28:01Z*
