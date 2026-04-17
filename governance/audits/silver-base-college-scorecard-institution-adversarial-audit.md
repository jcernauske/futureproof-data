# Adversarial Audit: silver-base-college-scorecard-institution

**Audit Date:** 2026-04-14
**Auditor:** @adversarial-auditor (independent)
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md`
**Status:** READY-WITH-CAVEATS (no CRITICAL blockers, several MODERATE findings)

---

## TL;DR

The Silver transformer and its 17 DQ rules are substantially sound. I verified the transformer code against the physical model, ran all 78 tests (all pass), traced all 17 DQ SQL queries by shape and semantics, and verified the two "chaos runner cycle 1-2 misses" against the actual `rng.choice`-based strategy selection in `corrupt_consistency`. The sampling-artifact explanation is real, not hallucinated.

However, a regulator-grade review would not accept this package as-is. There are four MODERATE evidence-integrity issues and three MINOR nits that future me (or a human approver) should address before Gold builds on this table:

1. **SLV-CSI-015 (q1≤q5) and SLV-CSI-014 (for-profit coverage) are one bad data refresh away from a red gate** — 46/50 and 52.63%/50.00%. The project treats both as "calibrated" but headroom on SLV-CSI-015 is only 4 rows of drift.
2. **12 fields in the Silver schema have NO DQ rules at all.** The physical model declares CHECK constraints on `state_abbr`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`, `room_board_off_campus`, `books_supplies` and 10 raw pass-through fields — none are exercised by SLV-CSI-001 through SLV-CSI-017.
3. **DQ was executed against reconstructed in-memory data, not a real Iceberg table** — the Silver table does not yet exist in the catalog at scorecard time. This is documented but remains a gap.
4. **No test exercises `transform()` end-to-end.** All 78 tests target `transform_row` and helper functions. The Iceberg read/promote/schema-evolution path is untested.

None of the risks are fabricated. I flagged every issue I could verify against source code, physical model, EDA, scorecard, chaos manifest, and the DQ driver script.

---

## 1. Risk Register

### HR-1 — CRITICAL: None found.

The transformer's routing (`pick_by_control`), coalesce (`COALESCE(costt4_a, costt4_p)`), null-propagating multiplication (`multiply_or_none`), and row-skip logic all behave exactly as the physical model specifies. Schema field IDs 1–35 match the physical model verbatim. Test assertions cover every derivation path I inspected.

---

### HR-2 — MODERATE: SLV-CSI-015 headroom is 4 rows; SLV-CSI-014 headroom is ~0.55pp

- SLV-CSI-015 threshold `<= 50`, observed 46. A single refresh cycle where +5 more institutions flip q1>q5 turns a PASS into a P1 FAIL.
- SLV-CSI-014 threshold `>= 50%` (for-profit NP coverage), observed 52.63% (220/418). A net loss of 11 for-profit NP reports out of 418 institutions pushes below 50%.

Both rules are documented as "on the edge" in `governance/dq-scorecards/silver-base-college-scorecard-institution-scorecard.md` §4 and §5. They pass today, but the project has no alert/tracking mechanism — just a narrative warning in a markdown file that no automated process reads. A future refresh silently pushing either over the line will not trigger a pre-build human review unless someone remembers to read the scorecard.

The EDA explicitly recommended `<= 50 rows` for SLV-CSI-015 based on an observed 46, and `>= 50%` for SLV-CSI-014 based on observed 52.63%. In both cases the DQ rule writer chose the exact observed value + minimal-tolerance threshold. This is calibration-by-observation, not calibration-with-margin. The EDA Recommendation language ("≥ 97% pass rate or ≤ 50 rows") for SLV-CSI-015 is actually weaker than what was implemented: 46/1,832 = 2.51%, and 97% pass = ≤ 55 violations (since 3% of 1,832 is ~55). The implementer chose the tighter `<= 50`, which sits just 4 rows above the observed count.

**Severity:** MODERATE. The rules don't falsely report OK — they just sit too close to the edge for a 1:1 refresh-to-execution cadence to feel safe.

---

### HR-3 — MODERATE: 12 physical-model columns have NO DQ rule coverage

The physical model (`governance/models/silver-base-college-scorecard-institution-physical.md` §DDL lines 373–397) declares CHECK constraints on:
- `unitid > 0`
- `tuition_in_state BETWEEN 0 AND 65000`
- `tuition_out_of_state BETWEEN 0 AND 80000`
- `room_board_on_campus BETWEEN 3000 AND 25000`
- `room_board_off_campus BETWEEN 3000 AND 30000`
- `books_supplies BETWEEN 0 AND 5000`
- `costt4_a_raw >= 0`, `costt4_p_raw >= 0`
- `npt41_pub_raw >= 0` through `npt45_pub_raw >= 0` (5 cols)
- `npt41_priv_raw >= 0` through `npt45_priv_raw >= 0` (5 cols)

None of these appear in `governance/dq-rules/silver-base-college-scorecard-institution.json`. A `grep` on the DQ rule file for `state_abbr|tuition_in_state|tuition_out|room_board|books_supplies|npt4.*_raw|costt4_[ap]_raw` returns zero matches.

Two of these are not rhetorical:
- **`tuition_in_state` draft cap was $65,000** in the physical model, but the EDA found Bronze max $69,330 — the EDA explicitly recommended "raise cap to $70K" for the DQ rule. The cap was never added as a rule at all; the physical-model constraint is stale and would fail if ever enforced.
- **`room_board_on_campus BETWEEN 3000 AND 25000`** would fail on the Bronze data (min $1,000). The EDA explicitly flagged this (Surprise: "Widen both ends"). The physical-model CHECK constraint is wrong *and* there is no DQ rule to enforce it.

Iceberg doesn't enforce SQL CHECK constraints, so these are advisory. But writing constraints in the physical model and then not implementing them as rules is a governance gap. A regulator would ask: "The physical model says `tuition_out_of_state <= 80000` — how do I know Iceberg writes respect that?" Answer today: you don't.

**Severity:** MODERATE. Non-critical fields (tuition display, raw provenance) — but 12 fields with advertised constraints and zero enforcement is a coverage gap.

---

### HR-4 — MODERATE: The `state_abbr` field has no DQ rule despite being NOT NULL with semantic format requirements

- Physical model (line 95, referenced by logical model) expects 2-letter USPS state/territory code.
- Logical model §Bronze EDA draft rule was "`state_abbr` matches `^[A-Z]{2}$`".
- EDA confirms this: "58 distinct (50 states + DC + territories), 0 violations."
- **No SLV-CSI-* rule asserts this.**

If Bronze ever lets a 3-letter territory code through (e.g., "VI " with trailing space, or "PRI" as a typo for "PR"), or a null slips through the Bronze filter (`stabbr` being the only required Silver field not checked), the Silver transformer will happily emit it. The `transform_row` does skip rows with falsy `stabbr`, but doesn't check length or format.

The logical model drafts a `state_abbr` DQ rule as P0; the final DQ rule set doesn't implement it.

**Severity:** MODERATE. This field feeds the Gold `consumable.career_outcomes` table and RPP (Regional Price Parity) joins — a malformed state code silently breaks joins.

---

### HR-5 — MODERATE: DQ executed against reconstructed in-memory DuckDB, not a real Iceberg table

The scorecard §Execution Method explicitly acknowledges: "The Silver Iceberg table does not yet exist in the catalog. DQ rules were executed against the data the Silver transformer would produce... Loaded 3,039 rows into an in-memory DuckDB table."

Implications:
1. **Field IDs are irrelevant to the test.** The test validates SQL against a freshly defined DuckDB DDL (see `dq_execute_silver_csi.py` lines 184–224). If the transformer's Iceberg schema has a field ID mismatch, this DQ execution would not catch it. The separate `test_field_ids_stable` unit test covers IDs 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 34, 35 — but not 11, 12, 13 (q2, q3, q4) or any of 15–33 (tuition, room_board, books_supplies, all raw pass-throughs). A field-ID rotation in the middle of the schema would not be detected.
2. **Iceberg-specific concerns (schema evolution, snapshot isolation, sort order `unitid ASC`, `bucket(16, unitid)` partitioning) are not exercised at all.**
3. **Promote idempotency is tested elsewhere** (Brightsmith core has its own tests) but this spec's test suite doesn't verify that a second run of `transform()` produces zero new snapshot rows.

**Severity:** MODERATE. The DQ rule SQL is validated semantically but not against the actual Silver table physical reality.

---

### HR-6 — MODERATE: No end-to-end test of `transform()` — 78 tests cover only helpers and `transform_row`

Every one of the 78 tests imports `transform_row`, `pick_by_control`, `multiply_or_none`, `map_control_label`, `get_silver_schema`, `CONTROL_LABELS`, `GRAIN_FIELDS`, or `GRAIN_PREFIX`. None import or exercise `transform()` itself.

Consequences:
- The Bronze read path (`read_with_duckdb(bronze_table)`) is untested at unit level.
- The `get_or_create_table(silver_catalog, 'base', 'college_scorecard_institution', get_silver_schema())` call is untested.
- The `promote(silver_table, silver_rows, id_field='record_id', spec_name=SPEC_NAME, agent_name='@primary-agent')` call is untested from this module.
- The skipped-rows logger warning path (`if skipped: logger.warning(...)`) is untested.
- The returned result dict shape (`rows_read`, `rows_transformed`, `rows_skipped_transform`, `promoted`, `skipped_dedup`, `snapshot_id`) is not type-asserted anywhere.

The chaos runner exercises a parallel code path (injecting into `shadow_base`), which gives some confidence. But "the chaos runner works" is not equivalent to "`transform()` works."

**Severity:** MODERATE. The transformation logic is well-tested at the unit level; the orchestration is not.

---

### HR-7 — MINOR: Chaos runner `rng.choice` sampling artifact is real, not hallucinated

I verified this against source. `governance/chaos-manifests/silver_base_college_scorecard_institution_chaos_runner.py` line 348:

```python
strategy = rng.choice(["np_gt_coa", "break_np_4yr_tautology",
                       "break_coa_4yr_tautology"])
```

With `_pick_indices(rows, indices, rng, divisor=3)` and cycle rates of 5-6%, the target-count for consistency corruption lands at 6-7 rows. `rng.choice` over 3 strategies on 6 samples has a non-trivial probability (~1.4%) of picking 0 of a given strategy. The chaos manifest's claim that cycles 1 and 2 produced zero tautology-breaking corruptions is consistent with this.

The manifest's own remediation recommendation (round-robin strategy selection, minimum-3-per-strategy floor) is correct and would eliminate the silent-cycle artifact. This is a **chaos runner quality issue, not a DQ rule gap.** SLV-CSI-008 and SLV-CSI-009 both fired in 4/5 cycles — when the corruption was present, the rules caught it 100% of the time.

**Severity:** MINOR. Self-disclosed by the chaos monkey agent with a fix proposed. Not a DQ rule defect.

---

### HR-8 — MINOR: Evidence text in SLV-CSI-005 lists raw `control` distribution `(867 / 1,754 / 418)` with no explicit "sum = 3,039" cross-check; SLV-CSI-015 evidence lists `(7/716 + 33/998 + 6/118)` where `716 + 998 + 118 = 1,832` — I verified this.

Both add up. Not fabricated. Noting the check was possible in case future EDAs drift.

---

### HR-9 — MINOR: `map_control_label` returns `None` for string `"1"` coercion path, but the test assertion `test_string_digit_coerces` says `map_control_label("1") == "Public"`.

The code is correct — `int("1") == 1`, so string digits do coerce through the `int()` call on line 113 of the transformer. The test passes because the actual coercion works. This is not a defect; I checked because the physical model specifies `control` as `int` from Bronze and does not document that string-typed controls are a defensive guard. The test `test_string_digit_coerces` is a good defensive contract — I flag it only because the physical model doesn't document the "defensive coercion" behavior anywhere, so a future Bronze change that starts emitting int-typed control values will silently make those two tests no longer provide meaningful coverage.

**Severity:** MINOR. Defensive; well-tested.

---

### HR-10 — MINOR: SLV-CSI-010 and SLV-CSI-011 both test "≥ 70%" but are row-identical per the EDA's Key Finding #1.

The EDA Key Finding #1 is explicit: "Coverage of net_price_annual and cost_of_attendance_annual is identical down to the row. 2,233 rows have both populated, 806 have both null, and zero rows have one without the other."

This means SLV-CSI-010 and SLV-CSI-011 are mathematically redundant on the current data. The EDA even suggests: "A single Silver DQ rule can cover both measures as a unified 'financial measures reported' gate." The DQ rule writer chose to keep both rules — defensible, because the source could diverge on future refreshes (College Scorecard could publish COA without publishing NP or vice versa). But there is no DQ rule that would **detect the divergence** if it ever happened. The tight co-null coupling is an observed property, not an enforced invariant.

**Severity:** MINOR. Not wrong; just doesn't catch a theoretical failure mode the EDA itself flags as possible.

---

## 2. Evidence Demands — Satisfied vs. Unsatisfied

For each risk, what evidence would a regulator want?

| Risk | Evidence Demanded | Present? |
|------|-------------------|----------|
| HR-1 (none) | Transformer routing correct for all {1,2,3,null,unexpected}; schema matches physical model | **YES** — `test_control_*` tests + `test_field_ids_stable` + scorecard's 100% mapping rate |
| HR-2 (HR-15/14 headroom) | Alert or tracking mechanism for SLV-CSI-015 and SLV-CSI-014 approaching limits | **NO** — only a narrative in a scorecard markdown file |
| HR-3 (12 cols no DQ) | A DQ rule per physical-model CHECK constraint | **NO** — 12 fields silently unverified |
| HR-4 (no state_abbr rule) | A rule asserting `state_abbr ~ '^[A-Z]{2}$'` | **NO** — logical-model draft rule never implemented |
| HR-5 (in-memory DQ) | DQ re-run against real Iceberg table after first transform | **NO** — acknowledged in scorecard, not scheduled |
| HR-6 (no E2E test) | A test that exercises `transform()` with fixture Iceberg warehouses | **NO** — all 78 tests target lower layers |
| HR-7 (chaos rng.choice) | Chaos runner uses round-robin strategy selection | **NO** — `rng.choice` still in place, remediation proposed but not applied |
| HR-8 (evidence math) | Evidence counts cross-check within rule descriptions | **YES** — I verified the sums manually |
| HR-9 (defensive coerce) | Physical model documents defensive coercion contract | **NO** — inferred from test, not documented |
| HR-10 (redundant coverage rules) | A rule to detect COA/NP coverage divergence | **NO** — EDA flagged the possibility, no rule implemented |

---

## 3. Assessment — Grade the Defenses

| Risk | Defense Claim | Grade |
|------|--------------|-------|
| Transformation correctness | 78 tests exercise all branch paths of `transform_row`, `pick_by_control`, `multiply_or_none`, `map_control_label` | **STRONG** |
| Schema field ID stability | `test_field_ids_stable` covers IDs 1-10, 14, 34, 35 | **ADEQUATE** (gaps at 11, 12, 13, 15-33) |
| DQ rule SQL correctness | 17 rules' SQL inspected; execution produces expected numbers matching EDA exactly | **STRONG** |
| DQ rule coverage of physical model | 17 rules cover row count, uniqueness, control enum, 2 cross-field invariants (NP≤COA, ×4 tautologies), overall and per-control coverage, q1≤q5, 2 range rules — but miss 12 fields | **WEAK** (coverage-by-field: 5 of 17 schema fields covered by range rules; 12 fields entirely uncovered) |
| Chaos coverage | 17/17 rules fire in cycles 3, 4, 5; 2 sampling artifacts in cycles 1-2 | **STRONG** (detection) / **ADEQUATE** (methodology — `rng.choice` should be round-robin) |
| End-to-end execution | `transform()` is never called by any test | **MISSING** |
| Field-level DQ rule completeness | 12 physical-model CHECK constraints have no corresponding DQ rule | **WEAK** |
| SLV-CSI-014/015 tight-threshold monitoring | Narrative warning in scorecard §4-§5 | **WEAK** (no automated alert) |
| Evidence integrity | EDA numbers reproduce exactly in scorecard; quintile breakdown sums to 1,832 | **STRONG** |
| DQ executed against real table | In-memory reconstruction; acknowledged, not scheduled | **MISSING** (real Iceberg execution pending) |

---

## 4. Recommendations

### Must-fix before Gold consumes this table
1. **Add SLV-CSI-018: `state_abbr ~ '^[A-Z]{2}$'` as a P0 validity rule.** The logical model drafted it; drop-the-ball cost is silent data-quality erosion on RPP joins.
2. **Add SLV-CSI-019 through SLV-CSI-024: range rules for `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`, `room_board_off_campus`, `books_supplies`, and the 12 raw pass-through `>= 0` constraints.** The physical model promises these; DQ should enforce them. Priority P1.
3. **Re-align physical-model CHECK constraints with EDA observations.** `room_board_on_campus BETWEEN 3000 AND 25000` contradicts observed Bronze min $1,000 and max $29,874. Either tighten the Silver transformer to reject out-of-range or widen the constraints. Currently the physical model documents a constraint that real data violates.

### Should-fix
4. **Add end-to-end test** (`test_transform_end_to_end`) that builds a 5-row fake Bronze Iceberg warehouse, calls `transform()`, and asserts return-dict shape + row count + snapshot presence. Covers the 5 currently untested code paths in `transform()`.
5. **Add SLV-CSI-025: COA/NP co-null divergence detector.** EDA asserts they're row-identical today; a P2 informational rule that flags any row where exactly one is null protects the invariant downstream analysts will rely on.
6. **Widen SLV-CSI-015 threshold to 55 (≤ 3% of 1,832) and SLV-CSI-014 to 48%** to give actual margin above observed values. Current values leave zero cushion for natural refresh drift.
7. **Fix chaos runner `corrupt_consistency`** to round-robin the 3 strategies so every cycle exercises all three. Closes the 1-cycle silent-rule artifact at minimal cost.

### Would-be-nice
8. **Re-execute DQ against the real Silver Iceberg table** once it has been promoted, and add a second scorecard file (`silver-base-college-scorecard-institution-postpromote-scorecard.md`). This closes HR-5.
9. **Expand `test_field_ids_stable`** to assert IDs 11, 12, 13, 15–33 explicitly. A developer who accidentally inserts a new field in the middle of the schema would otherwise silently rotate all downstream field IDs.
10. **Document the `int(control)` defensive coercion contract** in the physical model's derivation notes. Currently it's implicit behavior tested by `test_string_digit_coerces` with no design rationale captured.

---

## 5. Meta-Assessment

**Would a regulator accept this?** Not quite. The transformation logic is correct and well-tested at the unit level. The DQ rules that exist are semantically sound (I traced each SQL and cross-checked against EDA evidence) and chaos-hardened (17/17 rules fire under matching corruption). **But the rule set covers only the measurement fields — 12 physical-model CHECK constraints have no corresponding DQ rule, and the flagship `state_abbr` format rule drafted in the logical model was never implemented.** A regulator would ask "how do you know this field is always a 2-letter USPS code?" and the answer today is "we hope Bronze rejects bad values" — which is true (Bronze DQ has `state_abbr` rules) but is not defense-in-depth.

**The two tight thresholds (SLV-CSI-014, SLV-CSI-015) pass today but will not survive a 5% drift event** without an automated alert. The project has no such alert, just a scorecard narrative that no automated process reads.

**The transformer itself I trust.** The 78 tests cover every branch of every helper, the routing semantics match the physical model verbatim, and the schema field IDs 1–35 line up exactly. What I don't trust is the scope of the DQ gate that sits downstream of it.

**Recommendation:** approve Silver transformer for Gold consumption, but do not mark the spec COMPLETE until HR-3 (12 missing field-level DQ rules) and HR-4 (state_abbr format rule) are closed. Everything else is fixable in a follow-up.

---

*End of audit — @adversarial-auditor, 2026-04-14*
