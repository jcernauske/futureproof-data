## Staff Engineer Review

### Date: 2026-04-16
### Reviewer: @staff-engineer
### Spec: `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 2 — Silver)
### Status: CHANGES REQUIRED

---

### Verdict

The transformer itself is fine. The code is readable, the helpers are small and single-purpose, `transform_row()` honors the physical model's NOT NULL contract by returning `None` rather than emitting a nullable primary key row, and the 78 unit tests actually assert specific values instead of "no exception." Real data spot-checked cleanly against the raw CSV for four reference institutions (UC Berkeley, MIT, Michigan, Stanford). All DQ rules now pass 23/23 against the observed Bronze data, and the P0 gate is green.

What I cannot sign off on is the **governance artifact state**. The governance reviewer's blockers were directionally addressed, but the fixes were applied inconsistently across artifacts. The data contract and the physical model both advertise guarantees that do not match what the pipeline actually does. Three governance artifacts disagree on how many DQ rules exist, and two threshold caps are documented three different ways across the physical model, the DQ rule SQL, and the DQ rule prose. That is precisely the class of defect the staff engineer gate is supposed to catch. The post-review closed Issue #1 (CDE count) and Issue #3 (state_abbr rule) but did not close Issue #4 cleanly — widening the SQL thresholds without updating the physical-model CHECK constraints or the rule `description` fields just moved the inconsistency from "rule fails execution" to "rule passes execution against a contract that lies about what it checks." Fix the drift and this gets approved.

---

### Code Quality

**`src/silver/college_scorecard_institution_transformer.py`** — Acceptable.

- Small helpers (`map_control_label`, `pick_by_control`, `multiply_or_none`) do exactly one thing. Each has a docstring that says *why* the null-handling matters, not what the code does.
- `transform_row()` returns `None` for unmappable rows instead of emitting a row with null in a NOT NULL column. This is the right call — downstream DQ sees the right row count, the physical model's NOT NULL guarantee holds by construction. Skipped-row counter is surfaced in the return dict for operator visibility.
- `pick_by_control` correctly refuses to silently collapse a null or unexpected control to the private branch. That's a subtle but important choice — this is the multiplexer the whole ROI formula routes through.
- Schema field IDs are hard-coded to 1..35. A test (`test_field_ids_stable`) pins a spot-check of those IDs so schema evolution can't silently scramble them.
- Grain is `['unitid']` with `csi` prefix, matching the physical model.

**Nits I'll let go:**

- `transform_row` could split the "validate required fields" block out from the "compute derivations" block for readability. Not worth a change request.
- `logger.warning("Skipped %d rows...")` is fine but a structured `extra={"skipped_count": skipped}` would be nicer when someone's log-aggregating this.

---

### Test Quality

**`tests/silver/test_college_scorecard_institution_transformer.py`** — Good. Not theater.

- 78 tests passing. Fixtures represent three realistic institutions (Berkeley/Stanford/example for-profit) with plausible values, not zeros.
- Assertions are specific — `assert result["net_price_annual"] == 18000.0`, not `assert result["net_price_annual"]`.
- Parametrized quintile routing tests (5 quintiles × 3 control types = 15 assertions) actually catch the off-by-one "I typo'd q3/q4" bug that would otherwise slip through.
- Null-propagation tested independently of routing — `test_net_price_null_when_routed_field_null` and `test_missing_quintile_preserved_as_null` are the tests that catch the "I forgot to handle None" regression.
- `test_record_id_stable_across_measure_changes` is the right test — it locks down that the grain hash depends only on `unitid`, not on derived measures. Without it, any future refactor that accidentally includes a measure in the hash would silently break idempotency.
- Row-skip branches are covered explicitly (null unitid, null instnm, null stabbr, null control, unexpected control=99).

**What's missing** — `transform()` orchestration is untested end-to-end. The governance reviewer marked this ADVISORY with the caveat that it must close before Gold pre-review. I accept that framing but I'm flagging it here too so it doesn't get lost.

---

### Spec Compliance

The transformer implements every Silver transformation the spec calls for:

| Spec requirement | Implemented | Verified |
|------------------|-------------|----------|
| Unified `net_price_annual` via control-based routing | Yes | `pick_by_control` + 3 tests per control type |
| Unified `cost_of_attendance_annual` via COALESCE | Yes | `test_coa_prefers_costt4_a`, `test_coa_falls_back_to_costt4_p` |
| `institution_control` string mapping | Yes | `map_control_label` + 7 tests |
| `net_price_4yr` / `cost_of_attendance_4yr` derivations | Yes | `multiply_or_none` + null-propagation tests |
| 5 unified quintile fields | Yes | 15 parametrized tests |
| Raw field pass-through for provenance | Yes | 4 dedicated pass-through tests |
| Grain = `[unitid]`, prefix `csi` | Yes | `test_grain_fields`, `test_grain_prefix` |
| Promote idempotency | Structure present | Not exercised end-to-end (HR-6) |

Silver schema also matches the spec's §Silver Schema table. The 14 raw pass-through columns (`*_raw`) are additions beyond the spec's minimum, introduced for provenance per the physical model, and called out explicitly in the CDE registry as audit-reconstruction CDEs. That's a reasonable scope expansion and it's documented.

---

### Data Correctness Spot-Check

Ran four reference institutions through `transform_row()` with values pulled directly from the source CSV (`/tmp/Most-Recent-Cohorts-Institution.csv`). All values match raw-to-Silver without loss, and every cross-field invariant holds.

| Institution | UNITID | Field | Raw CSV | Silver Output | Match |
|-------------|-------:|-------|---------|---------------|-------|
| UC Berkeley | 110635 | COSTT4_A → cost_of_attendance_annual | 42,708 | 42,708 | Yes |
| UC Berkeley | 110635 | NPT4_PUB → net_price_annual (control=1) | 14,979 | 14,979 | Yes |
| UC Berkeley | 110635 | net_price_4yr (derived ×4) | n/a | 59,916 | Yes (= 14,979 × 4) |
| MIT | 166683 | NPT4_PRIV → net_price_annual (control=2) | 19,813 | 19,813 | Yes |
| MIT | 166683 | COSTT4_A → cost_of_attendance_annual | 79,850 | 79,850 | Yes |
| Michigan | 170976 | NPT4_PUB → net_price_annual (control=1) | 14,832 | 14,832 | Yes |
| Michigan | 170976 | TUITIONFEE_IN → tuition_in_state | 17,228 | 17,228 | Yes |
| Stanford | 243744 | NPT4_PRIV → net_price_annual (control=2) | 12,136 | 12,136 | Yes |
| Stanford | 243744 | COSTT4_A → cost_of_attendance_annual | 82,162 | 82,162 | Yes |

**Invariant spot-check:** `net_price_annual ≤ cost_of_attendance_annual` holds for all four. `net_price_4yr == net_price_annual × 4` exact in IEEE-754 for all four. `record_id` is deterministic and unique across the four institutions. Routing picks NPT4_PUB for both public schools and NPT4_PRIV for both private nonprofits. No cross-contamination.

**Aggregate-level spot-check (from the DQ scorecard and re-executed 23/23 PASS run):**

- Row count: 3,039 (matches EDA; SLV-CSI-001 exact ± 5 tolerance)
- `unitid` distinct: 3,039 with 0 nulls and 0 duplicates
- Control distribution: 867 Public / 1,754 Private nonprofit / 418 Private for-profit = 3,039 (sums correctly; matches EDA)
- Coverage: 73.48% on both COA and net price (row-identical in nullness per EDA Key Finding #1)
- `net_price_annual` range: [-$1,180, $77,180] (negatives legitimate for community colleges where grants exceed COA; SLV-CSI-016 allows down to -$5,000)
- `net_price_q1 ≤ net_price_q5`: 46 of 1,832 legitimate violations (merit-aid inversions); rule permits up to 50.

No correctness defects. The data the transformer emits is the data the source CSV contains, routed correctly by control.

---

### Governance Consistency — Where This Goes Wrong

These are the reasons I can't approve yet. They are not defects in the transformer; they are defects in the contracts and models the pipeline publishes.

#### Inconsistency 1 — Data contract `dq_summary` and `cde_summary` are stale

`governance/data-contracts/silver-base-college-scorecard-institution.yaml` still says:

```yaml
dq_summary:
  total_rules: 17
  p0_rules: 11
  p1_rules: 5
  p2_rules: 1
  rule_ids:
    - SLV-CSI-001
    ...
    - SLV-CSI-017
```

The actual DQ rules file now has 23 rules (SLV-CSI-001 through SLV-CSI-023) with **12 P0 / 9 P1 / 2 P2**. The contract lists SLV-CSI-001..017 only — it's missing SLV-CSI-018 through SLV-CSI-023 entirely.

Same file:

```yaml
cde_summary:
  total_columns: 35
  cde_columns: 23
  ...
  cde_density_commentary: >
    65.7% CDE density is higher than the 60.7% density on the parent Bronze
    contract (17/28). ... plus retention of the 12 raw pass-through columns
    as provenance CDEs ...
```

But `grep -c 'is_cde: true'` returns 26 on this same file. And the CDE registry, the data dictionary, and the physical model all say 26. The contract body has been updated but its own summary block hasn't — the narrative prose still claims "12 raw pass-through columns" when the columns section flags 14.

The contract is the external-facing guarantee document. It must not lie to consumers about how many rules it is gated by or how many CDEs it carries.

#### Inconsistency 2 — Physical model CHECK constraints disagree with DQ rule SQL

The user-reported fix was to widen SLV-CSI-022 cap from $30K to $40K and SLV-CSI-023 cap from $5K to $10K "to match EDA-recommended values." The rule `name` and `sql` fields were updated. The rule `description` fields and the physical model CHECK constraints were not.

| Field | Physical model CHECK (line refs in `silver-base-college-scorecard-institution-physical.md`) | DQ rule SQL | DQ rule `description` |
|-------|--------------------------------------------------------------------------------|-------------|-----------------------|
| `room_board_off_campus` | `BETWEEN 1000 AND 30000` (lines 153, 390) | `< 1000 OR > 40000` | "must be between $1,000 and $30,000" |
| `books_supplies` | `BETWEEN 0 AND 5000` (lines 154, 391) | `< 0 OR > 10000` | "must be between $0 and $5,000" |

Three artifacts, three different thresholds. Readers of the physical model will believe the data is gated at $30K/$5K. Readers of the rule SQL know it is actually gated at $40K/$10K. Readers of the rule description will think there's a contradiction — which there is.

Iceberg doesn't enforce CHECK constraints, so today the physical model's stricter range is just prose. But if this table is ever materialized in a SQL engine that does enforce CHECK constraints (Postgres, DuckDB's `CREATE TABLE ... CHECK`, Athena's Lake Formation constraints, etc.), 7 legitimate Bronze rows will be rejected at insert time. That's a real bug waiting to fire.

#### Inconsistency 3 — Scorecard markdown is stale

`governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md` still claims "Overall Score: 21/23 (91.3%)" and marks SLV-CSI-022 and SLV-CSI-023 as FAIL. The underlying JSON result file `silver-base-college-scorecard-institution-20260416T043128Z.json` is 23/23 PASS, and I re-executed the rules myself: 23/23 PASS.

The scorecard markdown is the file humans read for DQ status. It is wrong.

---

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | CHANGES REQUIRED | `governance/data-contracts/silver-base-college-scorecard-institution.yaml` | `dq_summary.total_rules: 17` with only rule_ids SLV-CSI-001..017. Real count is 23 (SLV-CSI-001..023 at 12/9/2 P0/P1/P2). Same file's `cde_summary.cde_columns: 23` and `cde_density_commentary` describing "12 raw pass-through columns" contradict the 26 `is_cde: true` flags in the same file's columns section. | Update `dq_summary` to `total_rules: 23`, `p0_rules: 12`, `p1_rules: 9`, `p2_rules: 2`, and extend `rule_ids` to include SLV-CSI-018..023. Update `cde_summary.cde_columns` to 26. Rewrite the `cde_density_commentary` prose to say "14 raw pass-throughs" and update the density number (26/35 = 74.3%). |
| 2 | CHANGES REQUIRED | `governance/models/silver-base-college-scorecard-institution-physical.md` (lines 153, 154, 390, 391) | CHECK constraints on `room_board_off_campus` and `books_supplies` still use the pre-widening thresholds [1000, 30000] and [0, 5000], while the corresponding DQ rules SLV-CSI-022/023 now enforce [1000, 40000] and [0, 10000]. | Either (a) widen the physical model CHECK constraints to match the DQ rule SQL — `BETWEEN 1000 AND 40000` and `BETWEEN 0 AND 10000` — with a line in the "range widened from..." description pattern already used for other fields, or (b) revert the DQ rules to the narrow thresholds and accept the 7 failures as a widening justification. Option (a) is the right call because the EDA evidence already supports the wider ranges. Both the table DDL block and the per-column table must be updated. |
| 3 | CHANGES REQUIRED | `governance/dq-rules/silver-base-college-scorecard-institution.json` (rules SLV-CSI-022 and SLV-CSI-023) | Rule `description` fields still say "must be between $1,000 and $30,000" and "must be between $0 and $5,000" even though the `name` and `sql` now use the widened caps. | Rewrite the `description` field on both rules to match the widened cap. Keep the "outlier flagging" narrative if desired, but the stated range must match the SQL. |
| 4 | CHANGES REQUIRED | `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md` | Scorecard markdown claims 21/23 PASS with SLV-CSI-022 and SLV-CSI-023 as FAIL. Current execution is 23/23 PASS (verified: `governance/dq-results/silver-base-college-scorecard-institution-20260416T043128Z.json` and a fresh re-run produce 23/23). | Regenerate the scorecard from the latest passing run. "Overall Score: 23/23 (100%)" at the top. SLV-CSI-022 and SLV-CSI-023 marked PASS with actual=0. Delete or rewrite the "New-Rule Failures — Analysis" section — it's historical noise now. |
| 5 | ADVISORY (non-blocking) | `governance/reviews/silver-base-college-scorecard-institution-post-review.md` | References 17 rules throughout and marks CDE summary as "23 vs 26." Historical review doc; not load-bearing once this staff review closes the loop. | No action required. Supersede by this review. |

---

### What's Acceptable

- Transformer code is clean, tested, and correct. 78/78 passing.
- Four reference institutions (Berkeley, MIT, Michigan, Stanford) round-trip from CSV to Silver with zero loss and every cross-field invariant holding.
- DQ rules, when executed, are 23/23 PASS with P0 gate green. No correctness defect in the data.
- CDE registry at 26/35 is well-reasoned — the 14 raw pass-through columns are flagged provenance CDE with a coherent audit-reconstruction argument.
- `pick_by_control` does not collapse unknown-control to the private branch. That's the right call for a multiplexer carrying this much downstream blast radius.
- Chaos detection at 100% in cycles 3–5. P0 gate correctly blocks contaminated data.
- Spot-check methodology ran live against the source CSV, not against cached test values.

Get the four contract / model / scorecard consistency issues fixed and this is approved. None of them require code changes — only governance-artifact edits. Estimated effort: under an hour.

---

*Filed by @staff-engineer, 2026-04-16*
*Review path: `governance/reviews/silver-base-college-scorecard-institution-staff-review.md`*

---

## Staff Engineer Review — Second Re-Review

### Date: 2026-04-16
### Reviewer: @staff-engineer
### Status: CHANGES REQUIRED

---

### Verdict

Close, but not yet. Four of the five items from the first re-review are closed cleanly. Two are not, and one of them is a direct factual contradiction of the user's own submission note. The submission claims "SLV-CSI-022 SQL, name, description, evidence all aligned to [$1K, $40K]" — I read the JSON and the SLV-CSI-022 `description` field still says "must be between $1,000 and $30,000." The `name`, `sql`, and `evidence` are correct. The `description` wasn't touched. That's the same `description` vs. `sql` drift I flagged as Issue #3 last round. Claim and reality do not agree.

The scorecard is also only half-fixed. The top-of-file rollup now correctly reads 23/23 (100%), and the per-rule table rows for SLV-CSI-022/023 correctly show PASS. But the bottom half of the document — "New-Rule Failures — Analysis" (50+ lines), Observation #3 ("SLV-CSI-022 and SLV-CSI-023 fail by construction against this snapshot"), and the Comparison-to-Logical-Model table row labeled "**FAIL at $30K; would PASS at $40K**" — all still read as if the rules are failing. A reader who scrolls past the header sees a FAIL story that contradicts the PASS header. That's worse than leaving it entirely unchanged, because it creates internal whiplash.

Re-ran the DQ suite myself via `uv run python scripts/dq_execute_silver_csi.py`: 23/23 PASS, P0 gate PASS. The data is correct and the transformer is unchanged from the prior review. No code concerns. This remains a governance-artifacts-only fix.

---

### Item-by-Item Verification Against First-Re-Review Issues

| Prior Issue | Status This Round | Evidence |
|-------------|-------------------|----------|
| #1 Data contract `dq_summary` + `cde_summary` | **CLOSED** | `total_rules: 23`, `p0_rules: 12`, `p1_rules: 9`, `p2_rules: 2`, `rule_ids` extends to SLV-CSI-023, `cde_columns: 26`, commentary now "74.3% CDE density" and "14 raw pass-through columns." Verified against same file. |
| #2 Physical model CHECK constraints | **CLOSED** | Line 153 `BETWEEN 1000 AND 40000`, line 154 `BETWEEN 0 AND 10000`, DDL block lines 390/391 match. Both the per-column table and the DDL agree. |
| #3 DQ rule `description` fields | **STILL OPEN (SLV-CSI-022)** | SLV-CSI-023 `description` correctly says "must be between $0 and $10,000." SLV-CSI-022 `description` still says "must be between $1,000 and $30,000" and the explanatory prose that follows still justifies keeping the $30K cap. Submission note is incorrect on this file. |
| #4 DQ scorecard markdown | **PARTIALLY CLOSED** | Top-line "Overall Score: 23/23 (100%)", P0/P1/P2 rollups, and per-rule table rows for 022/023 are correct. The "New-Rule Failures — Analysis" section (lines 83–126), Observation #3 (line 197), and the "Comparison to Logical-Model Draft Thresholds" final two rows (lines 227–228, still labeled "**FAIL at $30K**") are historical noise that now contradict the top-line status. The submission explicitly committed to "Delete or rewrite the 'New-Rule Failures — Analysis' section — it's historical noise now." That did not happen. |
| #5 Post-review doc | **ADVISORY, NO ACTION** | Non-blocking. Superseded by this review round. |

---

### Independent Verification Run

Re-executed the DQ suite to confirm the submitter's "23/23 PASS" claim is reproducible:

```
$ uv run python scripts/dq_execute_silver_csi.py
...
Totals: pass=23 fail=0 error=0  P0 gate: PASS
```

Transformer unit tests:

```
$ uv run pytest tests/silver/test_college_scorecard_institution_transformer.py -q
78 passed in 0.47s
```

Data correctness: unchanged from the first re-review. Four reference institutions (Berkeley, MIT, Michigan, Stanford) still round-trip from CSV to Silver with zero loss. No regressions.

---

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | CHANGES REQUIRED | `governance/dq-rules/silver-base-college-scorecard-institution.json` (rule SLV-CSI-022) | `description` field still reads "When non-null, room_board_off_campus must be between $1,000 and $30,000..." with a trailing justification for the $30K cap. The rule `name`, `sql`, and `evidence` have all been updated to $40K. The `description` field was not. Submission note asserts otherwise; the JSON says otherwise. | Rewrite `description` to state "must be between $1,000 and $40,000" and remove the justifying sentence for keeping the $30K cap (since the cap was widened). Mirror the style used on SLV-CSI-023's already-fixed description: state the widened range and cite the Bronze-observed max ($39,100) as support. |
| 2 | CHANGES REQUIRED | `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md` | The scorecard now carries a correct header but an obsolete body. Three sections still narrate SLV-CSI-022 and SLV-CSI-023 as failing: (a) "New-Rule Failures — Analysis" at lines 83–126, (b) Observation #3 at line 197 stating "SLV-CSI-022 and SLV-CSI-023 fail by construction against this snapshot," (c) final two rows of "Comparison to Logical-Model Draft Thresholds" at lines 227–228 labeled "**FAIL at $30K; would PASS at $40K**" and "**FAIL at $5K; would PASS at $10K**." | Delete the "New-Rule Failures — Analysis" section entirely (or rewrite as a one-paragraph historical note that says "initial $30K/$5K caps were widened to $40K/$10K following DQ re-run; current state 0 violations"). Rewrite Observation #3 to describe the final widened state ("SLV-CSI-022 and SLV-CSI-023 pass cleanly at the EDA-recommended thresholds"). Update the last two rows of the Logical-Model comparison table to show the final PASS state rather than the interim FAIL. Recommendation in the "Escalation" section (lines 237–241) should be removed or marked "Resolved — thresholds widened per this recommendation." |

---

### Not Re-Raising

- Transformer code. Unchanged, still acceptable.
- 78 transformer unit tests. Unchanged, still real tests.
- Data correctness. Unchanged, spot-checked cleanly last round.
- 23/23 DQ PASS. Reproduced independently.
- CDE registry 26/35 density. Unchanged.

---

### Path to Approval

Both remaining issues are text-only edits to governance artifacts. No code, no rerun required. Estimated effort: 10 minutes. On receipt of a third submission where SLV-CSI-022's `description` says $40,000 and the scorecard body stops claiming FAIL on rules that currently PASS, this approves.

---

*Filed by @staff-engineer, 2026-04-16 (second re-review)*
*Review path: `governance/reviews/silver-base-college-scorecard-institution-staff-review.md`*

---

## Staff Engineer Review — Third Re-Review

### Date: 2026-04-16
### Reviewer: @staff-engineer
### Status: APPROVED

---

### Verdict

Both remaining items from the second re-review are closed. Governance artifacts are now internally consistent with each other and with the rules actually being executed. Transformer code and tests are unchanged and still acceptable. DQ 23/23 PASS reproduced independently. Approved.

---

### Item-by-Item Close-Out

| Prior Issue | Status | Evidence |
|-------------|--------|----------|
| #1 SLV-CSI-022 `description` drift | **CLOSED** | `governance/dq-rules/silver-base-college-scorecard-institution.json` line 333: "When non-null, room_board_off_campus must be between $1,000 and $40,000. Bronze observed max is $39,100 at high-cost-metro institutions (including California schools). Physical model CHECK updated to BETWEEN 1000 AND 40000 to match." The stale $30K-justifying sentence is gone; style mirrors SLV-CSI-023's (states widened range, cites Bronze-observed max). |
| #2 Scorecard stale FAIL narratives | **CLOSED** | Grep for `FAIL` on `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md` returns 8 matches, all on rules SLV-CSI-010/011/013/014/015/016/019/021 in the "would FAIL at stricter threshold" counterfactual column of the Logical-Model comparison table. Zero FAIL mentions on SLV-CSI-022 or SLV-CSI-023. The old "New-Rule Failures — Analysis" block is replaced by a one-paragraph "Historical Note — Threshold Adjustments" (line 83). Observation #3 (line 156) now reads "SLV-CSI-022 and SLV-CSI-023 pass cleanly at the EDA-recommended thresholds." Logical-Model comparison table rows 186–187 show "PASS at adopted $40K cap" and "PASS at adopted $10K cap." Escalation section (line 193) is marked "Resolved — thresholds widened per recommendation." Amendment Log row appended at line 221 referencing run `04635d71`. |

End-to-end scorecard read is coherent — header, per-rule tables, observations, comparison table, and escalation all tell a consistent "23/23 PASS after threshold widening" story. No whiplash.

---

### Independent Verification

```
$ uv run python scripts/dq_execute_silver_csi.py
Totals: pass=23 fail=0 error=0  P0 gate: PASS

$ uv run pytest tests/silver/test_college_scorecard_institution_transformer.py -q
78 passed in 0.47s
```

No regressions. Matches expected state (23/23 + 78 tests).

---

### Final Verdict

**APPROVED.** The Silver zone for `college_scorecard_institution` is production-quality. Transformer is correct, tests are real and comprehensive, DQ suite gates cleanly at P0, governance artifacts are consistent. Ready for @fp-builder verification and promotion of the spec to `docs/specs/completed/`. No further staff-engineer review rounds required.

---

*Filed by @staff-engineer, 2026-04-16 (third re-review, close-out)*
*Review path: `governance/reviews/silver-base-college-scorecard-institution-staff-review.md`*
