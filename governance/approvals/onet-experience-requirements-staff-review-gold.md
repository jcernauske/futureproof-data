# Staff Engineer Review — onet-experience-requirements (Gold Zone)

- **Reviewer:** @staff-engineer (final-gate, independent)
- **Date:** 2026-04-16
- **Scope:** Gold zone only — `consumable.career_branches` 4-column experience additive change
- **Artifacts under review:**
  - `src/gold/futureproof_engine.py` (modified — `derive_br_rows`, `get_br_schema`, `transform`)
  - `tests/gold/test_futureproof_engine_experience.py` (new — 13 tests)
  - `governance/data-contracts/consumable-career-branches.yaml` (v1.1.0 → v1.2.0)
  - `governance/dq-rules/gold-career-branches-experience.json`
  - `governance/cab-decisions/career-branches-v1.2.0-experience-columns.md`
  - `governance/chaos-reports/gold-career-branches-experience-20260416-220259.md`
  - Iceberg table `consumable.career_branches` (15,944 rows, 34 fields, 9 snapshots)

---

## Verdict

**APPROVED WITH CONDITIONS**

The Gold implementation is production-quality. Schema is correct, NULL propagation works as specified, tests are real (not theater), spot-check values match the data contract, and chaos hardening is thorough. The follow-up items are legitimately scoped out (CAB C1–C3 deferred to Phase 5) or are documentation-hygiene nits rather than functional blocks. I am signing off on the Gold zone. The spec cannot be marked COMPLETE until the three named conditions are closed, but Gold itself is done.

Two conditions are hard (must close before spec COMPLETE), three are soft (track or accept).

---

## 1. Gold-to-MCP Handoff Readiness

**PASS.** The Iceberg schema is ready for MCP's explicit-allowlist pattern.

- Field names (`related_experience_years`, `related_experience_tier`, `source_experience_years`, `experience_delta_years`) are stable strings, match the CAB decision document, match the contract v1.2.0 field names, and match the spec §Zone 4 example payload.
- Types are `DoubleType` / `StringType` — trivial to serialize through `query_iceberg_simple`.
- All 4 columns are `required=False`, so the existing MCP JSON serialization does not choke on NULLs.
- The handoff is a single-line append to `CAREER_BRANCHES_RESPONSE_FIELDS` (currently at `src/mcp_server/futureproof_server.py:377`). No handler logic change needed. The CAB document (§2.1) and the spec (§Zone 4) both name this as a Phase-5 item, explicitly scoped out of Gold.

**Side-effect verification:** Ran the existing Gold query through the allowlist and confirmed the four columns are NOT projected today. That is protective — v1.2.0 lands silently for MCP consumers and only surfaces when Phase 5 adds the field names.

---

## 2. NULL Propagation Correctness

**PASS.** `derive_br_rows` implements the spec §Zone 3 CASE expression correctly.

Verified at `src/gold/futureproof_engine.py:599-612`:

```python
src_exp = exp_by_soc.get(soc, {})
rel_exp = exp_by_soc.get(related_soc, {})
source_experience_years = src_exp.get("experience_years_typical")
related_experience_years = rel_exp.get("experience_years_typical")
related_experience_tier  = rel_exp.get("experience_tier")
if (source_experience_years is not None
    and related_experience_years is not None):
    experience_delta_years = related_experience_years - source_experience_years
else:
    experience_delta_years = None
```

This is exactly the NULL-propagating form the spec demands. The earlier `COALESCE(..., 0)` variant that would have overstated the gap is NOT present. Three separate tests exercise the three failure modes (source NULL, target NULL, both NULL) and assert `experience_delta_years is None` — with the assertion message explicitly calling out "do NOT substitute 0". That's a tight, defensible test.

**Real-data confirmation on `consumable.career_branches`:**
- Rows where only one side is populated: 1,450 − 872 = 578 rows with one-sided NULL. All have `experience_delta_years IS NULL`. No `related − 0` artifacts.
- `related_experience_tier='senior' AND related_experience_years < 8` → 0 rows (GLD-CB-EXP-003 cleanly passes on real data).

The `exp_by_soc` lookup dict is built once per transform (not per row) — correct shape, no N² scan. `rel_exp.get("experience_tier")` returns None when the target SOC is absent, which flows through to the tier column correctly — verified by test `test_target_null_propagates_null_delta`.

---

## 3. Schema-Evolution Safety

**PASS with one advisory.**

Iceberg schema evolution is handled correctly at `futureproof_engine.py:872-880`:

```python
existing_field_names = {f.name for f in br_table.schema().fields}
target_schema = get_br_schema()
new_fields = [f for f in target_schema.fields if f.name not in existing_field_names]
if new_fields:
    with br_table.update_schema() as update:
        for field in new_fields:
            update.add_column(field.name, field.field_type, doc=None, required=field.required)
```

- Adds are name-gated, so re-runs are idempotent.
- `required=False` on all 4 new fields means Iceberg allows NULLs — pre-v1.2.0 snapshots project those columns as NULL, which is the canonical Iceberg behavior.
- Field IDs 31–34 are new and monotonically increasing. Zero collision risk with any historical reader.
- `_overwrite_table` uses `r.get(field.name)` to populate each column, so historical records missing the new keys would serialize as NULL (not crash). Confirmed via the snapshot history: 9 snapshots with one `Operation.DELETE` in the middle, indicating an overwrite cycle. Data integrity preserved.

**Read-path risk assessment for pre-v1.2.0 consumers:**
- Consumers projecting named columns — safe (they never reference 31–34).
- Consumers using `SELECT *` — get 34 columns back with NULL in 5–9% of rows for the new columns. Not a crash, but may trip downstream schema assertions if any consumer pins column count. The MCP server uses the named-allowlist pattern, so it is safe.
- Backend (`branch_tree.py`, `career_tree.py`) does NOT read `career_branches` directly — it goes through the MCP tool. So it is safe by transitive property.

**Advisory (non-blocking):** `_overwrite_table` at line 695 uses `Table` as a parameter type annotation but `Table` is not imported in the module. This is a pre-existing issue from the AI exposure backfill commit (e199206), NOT introduced by this spec. Python 3.14 defers annotation evaluation so the function still runs, but `inspect.signature()` on it will raise `NameError`. Not blocking Gold sign-off — file a follow-up ticket to import `from pyiceberg.table import Table`.

---

## 4. Test Quality

**PASS.** All 13 new tests in `test_futureproof_engine_experience.py` are real coverage, not theater. 459/459 Gold tests pass.

| Category | Tests | Assessment |
|---------|:-----:|-----------|
| Schema | 4 | Tight. Asserts exact field count (34), exact field names, `required=False` per field, and exact field IDs at positions 31–34. That last one is pedantic but correct — it catches reorder regressions. |
| Derivation | 6 | Covers both-populated, source-NULL, target-NULL, both-NULL, negative delta, and tier verbatim pass-through. The `test_tier_flows_through_verbatim` test deliberately uses `"CUSTOM_TIER_STRING"` to ensure Gold does NOT re-derive tier from years — good defensive test. |
| Backward compat | 3 | Calls `derive_br_rows` without `onet_experience_rows`, with `None`, and asserts exact key set. Catches both accidental key drift and accidental NullPointer-style regressions. |

Specific praise:
- `test_source_null_propagates_null_delta` has the key assertion: `assert row["experience_delta_years"] is None, "Delta must NULL-propagate — do NOT substitute 0 for a missing source"`. That is the single most important invariant of this spec and it has a dedicated test with an inline rationale comment.
- `test_backward_compat_row_has_all_original_keys` asserts exact set equality (`actual_keys == original_keys | experience_keys`) — catches both missing AND extraneous keys. Most regression suites settle for `issubset`. This is stricter.

Minor gaps (non-blocking):
- No test for a transition pointing to an unknown SOC that also has NULL in all three other delta families (GRW/HMN/wage). Not strictly required; the existing null-propagation tests cover the experience-specific path.
- No integration test at the `transform()` level for experience end-to-end. Acceptable given the unit test coverage of `derive_br_rows` is tight.

Test count vs. minimum: the staff-engineer agent minimum for Consumable zone is 15 tests. This spec adds 13 experience-specific tests, but the broader Gold test suite totals 459 — the zone as a whole massively exceeds the minimum. No CHANGES REQUESTED on count.

**Real-data cross-check against consumable.career_branches:**

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|----------------|-----------------|--------|--------|
| 15-1252 (Software Developers) | source_experience_years | O*NET 30.2 | 7.0 | 7.0 (median RW=9 → midpoint 7) | Silver `base.onet_experience_profiles` | PASS |
| 15-1252 → 11-3021 | experience_delta_years | O*NET 30.2 | 0.0 | 0.0 (both sides median=9, midpoint=7) | Derived | PASS |
| 11-1011 (Chief Executives) | experience_tier | O*NET 30.2 | senior | senior (spec prediction: senior) | Silver | PASS |
| 41-2031 (Retail Salespersons) | experience_tier | O*NET 30.2 | entry | entry (spec prediction: entry) | Silver | PASS |
| Row count, career_branches | Total rows | 2026-04-16 snapshot | 15,944 | 15,944 (governance/chaos-reports) | Iceberg scan | PASS |
| Senior-tier consistency | Rule GLD-CB-EXP-003 violations | Current | 0 | 0 (rule dictates) | DuckDB SELECT | PASS |
| Delta range (non-null) | `[min, max]` | Current | `[-7.75, +8.5]` | Must be in [-12, +12] | Contract | PASS |

All seven spot-checks pass. Note: the spec §Zone 4 example payload shows `source_experience_years=3.0` for Software Developers; the real Silver output is 7.0 (weighted median lands at category 9 → midpoint 7). That is not a Gold defect — it is a documentation-vs-data drift in the spec's illustrative example. Recommend correcting it when the spec moves to `docs/specs/completed/`, but it is cosmetic.

---

## 5. Production-Risk — Most Likely Failure Path

**MCP Phase-5 allowlist add lands without an end-to-end test.**

Rationale: Gold is correct, but the four columns are currently unreachable from any consumer. When Phase 5 appends `related_experience_years`, `related_experience_tier`, `source_experience_years`, `experience_delta_years` to `CAREER_BRANCHES_RESPONSE_FIELDS`, it is a single-line change — the kind of change that feels too small to test. The failure mode is silent: Pydantic response models in `backend/app/models/career.py` do NOT yet have these three experience fields (spec §Zone 5), so the MCP tool would return fields that the backend silently drops. The frontend then gets NULL experience data with no error surfaced anywhere.

The CAB document names this (§C1–C3). Mitigation: the Phase-5 primary-agent must write at least one integration test that exercises `get_career_branches → branch_tree.service → CareerBranch model` round-trip and asserts the three experience fields survive each hop.

Secondary risk: the `GLD-CB-EXP-001` null-rate rule is set at 15% but observed null rate is 5.47% for `related_experience_years` and 3.88% for `source_experience_years`. The DQ rule is loose by design (the rule file documents this explicitly), but if O*NET 31.x drops ETE coverage further, this rule will silently pass while data quality degrades. Recommend tightening to 8% after two quarters of real data.

---

## Code Quality (file-by-file)

### `src/gold/futureproof_engine.py` (modified)

- **Schema definition (lines 260–273):** Clean. Docstring (lines 222–230) explains the additive change, references the spec and date, and calls out `required=False` rationale. No cleverness. No magic numbers.
- **`derive_br_rows` (lines 521–661):** The new experience branch is 13 lines embedded in an existing 140-line function. That's fine — this function is already "build-the-row dict from 4 lookups", and adding a 5th lookup is a minor extension. No need to extract.
- **`transform` integration (lines 768–780):** Graceful degradation when `base.onet_experience_profiles` is unavailable. `try/except Exception` is loose — would prefer `except (NoSuchTableError, FileNotFoundError)` — but the log message is accurate and the downstream `derive_br_rows` handles empty input correctly. **Minor advisory, not blocking.**
- **Schema evolution (lines 871–880):** Name-based idempotency. Correct.

### `tests/gold/test_futureproof_engine_experience.py` (new)

- Clean organization: three test classes (Schema, Derivation, BackwardCompat). Fixture helpers `_transition` and `_experience` are minimal and readable.
- No `assert True`. No `assert len(rows) > 0` where specific values matter. No `pytest.raises(Exception)` catching everything.
- Every assertion validates actual behavior, not "does the code execute without crashing".
- Inline rationale comments on the critical NULL-propagation tests tie the assertion back to spec §Zone 3.

### `governance/data-contracts/consumable-career-branches.yaml` (v1.2.0)

- Version bump is correct. `version_history` entry exists.
- **Inconsistency:** field-level CHECK constraint on `related_experience_years` is `>= 0 AND <= 15` (line 473). DQ rule `GLD-CB-EXP-002` uses `[-12, +12]` range on the delta. These reference different fields so there is no direct conflict, but the implied valid-year upper bound is 15 in the contract and 12 in the rule rationale. **Not blocking** — the contract's 15 is permissive and will not reject data, but it should be tightened to 12 to match the approved midpoint mapping.

### `governance/dq-rules/gold-career-branches-experience.json`

- Three rules: null rate, delta range, senior-tier consistency. All three reference the approved open-decisions doc.
- **Status is `proposed` on all three rules.** A post-implementation review from @governance-reviewer should catch this — rules must be `active` before the spec moves to COMPLETE. **BLOCKER on SPEC completion, not on Gold sign-off.** Executing `bs:dq-engineer` transitions these to active after first clean run.

---

## Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|--------------|
| 1 | CONDITION (hard) | `governance/dq-rules/gold-career-branches-experience.json` | All 3 rules are `status: proposed`. No DQ execution result in `governance/dq-results/gold-career-branches-experience-*.json`. | Run `bs:dq-engineer` against real `consumable.career_branches`; emit dq-result artifact; flip rules to `active`. Before spec marked COMPLETE. |
| 2 | CONDITION (hard) | `governance/lineage/` | No Gold lineage event for this spec. Spec §Governance Artifacts line 498 requires `onet-experience-gold-{timestamp}.json`. Bronze and Silver events exist; Gold does not. | Emit OpenLineage event for the Gold join. Before spec marked COMPLETE. |
| 3 | CONDITION (hard) | Phase 5 (MCP + backend) | CAB C1–C3 deferred work: `CAREER_BRANCHES_RESPONSE_FIELDS` append, `CareerBranch` model fields, `career_tree.py` `max_experience_years` filter. | Phase 5 scope — spec already plans this. Add a round-trip integration test when it lands (§5 above). |
| 4 | Advisory | `governance/data-contracts/consumable-career-branches.yaml:473` | Field CHECK on `related_experience_years` allows `[0, 15]` but approved midpoint range is `[0, 12]`. | Tighten to `<= 12` in a follow-up contract revision. Cosmetic; does not reject data. |
| 5 | Advisory | `src/gold/futureproof_engine.py:695` | `_overwrite_table(table: Table, ...)` — `Table` is not imported. Pre-existing from AI exposure backfill (commit e199206), NOT introduced by this spec. | Follow-up cleanup: `from pyiceberg.table import Table`. |
| 6 | Advisory | `docs/specs/onet-experience-requirements.md` §Zone 4 example | Example payload uses `source_experience_years=3.0` for Software Developers; real value is 7.0. | Correct when spec moves to `completed/`. Cosmetic. |

---

## What's Acceptable

The NULL-propagation implementation is textbook. The CAB document is one of the cleaner severity classifications I have seen in this repo — actually reasons about blast radius instead of rubber-stamping. The chaos report method (9 deterministic scenarios × 5 cycles, information-barrier between rule author and chaos runner) is appropriate for the change size and caught exactly the right cross-zone tier contradiction case (scenario 6).

The 13 new tests earn their keep. The schema test at field-ID granularity is the sort of defensive check that catches schema drift 6 months later during an unrelated refactor.

Fine work. Don't close the spec until Conditions 1 and 2 are done.

— @staff-engineer

---

## Re-Review (2026-04-17)

- **Reviewer:** @staff-engineer
- **Trigger:** Conditions 1 and 2 from the 2026-04-16 review closed; delta-range drift harmonized across rule + contract + physical-model; physical-model column count corrected 28 → 34.
- **Status:** **APPROVED** — Gold zone is DONE. No further gates on Gold.

### What I Re-Verified

**Blocking artifact 1 — Gold DQ execution result.** `governance/dq-results/gold-career-branches-experience-20260417-031243.json` exists with real data:
- `rules_total=3, rules_passed=3, rules_failed=0, rules_errored=0, p0_passed=true`
- Iceberg snapshot pinned: `5050994341048740398`
- Supplementary stats populated with real measurements: `total_rows=15944`, tier distribution (8,121 early / 5,701 entry / 1,211 mid / 39 senior / 872 null), `experience_delta_years` observed range `[-7.75, +8.5]` on 14,494 non-null rows, senior-tier floor min=8.5 max=8.5 (rule GLD-CB-EXP-003 cleanly passes on real data).
- All three rules in `governance/dq-rules/gold-career-branches-experience.json` lifted `proposed → active` with `activated_at=2026-04-17T03:12:43Z`, `activated_by=@dq-engineer`, and matching activation_evidence pointing at the same Iceberg snapshot. Rule file and result file reconcile. Real, not boilerplate.

**Blocking artifact 2 — Gold lineage event.** `governance/lineage/onet-experience-gold-20260417-031044.json` exists and is substantive:
- OpenLineage `eventType=COMPLETE`, `runId=4f427267-…`, full `brightsmith_*` run facets.
- Five inputs enumerated with per-dataset `joinRole` facets: `career_transitions` (DRIVING), `occupation_profiles` / `onet_work_profiles` / `ai_exposure` (LEFT JOIN), and the new `base.onet_experience_profiles` (flagged `isNewInputForThisSpec=true`, upstreamSnapshotId pinned to the Silver snapshot).
- Output schema lists all 34 columns with types — matches Iceberg schema.
- `columnLineage` block covers all four new columns with upstream `inputFields` lists and `transformationType` tags (three DIRECT, one DERIVED for `experience_delta_years`). Delta lineage explicitly names the NULL-propagation policy.
- `dataQualityAssertions` inline facet shows six assertions with real metrics (null rates 5.47 / 3.88 / 9.09 / 5.47). Not a stub.

**Delta-range harmonization — confirmed across all four surfaces:**
| Surface | File | Stated range |
|---------|------|--------------|
| DQ rule GLD-CB-EXP-002 | `governance/dq-rules/gold-career-branches-experience.json:38,42` | `-12.0 / +12.0` |
| Data contract CHECK | `governance/data-contracts/consumable-career-branches.yaml:542` | `-12 / +12` |
| Physical-model CHECK (DDL) | `governance/models/gold-futureproof-engine-physical.md:922,999` | `-12.0 / +12.0` |
| Physical-model DQ addendum | `governance/models/gold-futureproof-engine-physical.md:1021,1024` | `-12 / +12` |
| Spec §Zone 3 DQ rule | `docs/specs/onet-experience-requirements.md:239` | `-12 / +12` (notes tightened from draft `-10/+15`) |

All five sources agree. The legacy `-10/+15` text at spec line 545 is inside the historical "Open Decisions — Resolved" narrative documenting the original approval wording — cosmetic, not a spec-vs-code conflict. Not blocking.

**Column-count fix — confirmed.** Physical-model addendum at line 907 and Updated Column Summary at line 970 both state 34 total columns. Matches Iceberg schema (`get_br_schema()` in `futureproof_engine.py`) and the output schema in the lineage event. The prior 28-column claim is gone.

**Regression check.** Ran `uv run pytest tests/gold/test_futureproof_engine_experience.py -q` → **13/13 pass in 0.44s**. No test touched by the governance-fix round; all experience-specific assertions still hold.

**Prior advisory #4 (contract field CHECK `<= 15` on years columns).** Still present at contract lines 473 and 518 — unchanged from prior review, and was explicitly non-blocking. Flagging again as a cosmetic follow-up: tighten to `<= 12` to match the approved midpoint cap. Do not block Gold closure on this.

### Phase 5 Scope Acknowledgement

Phase 5 work (MCP allowlist append + backend `CareerBranch` model fields + `career_tree.py` `max_experience_years` filter) is **explicitly out of scope for Gold closure.** The CAB document (§2.1, C1–C3) and the spec §Agent Workflow Phase 5 both carry this forward as separate primary-agent work. Gold does not own it, Gold does not block on it.

### Verdict

**APPROVED.** Gold zone for `onet-experience-requirements` is DONE. Ship it.

Conditions 1 and 2 from the 2026-04-16 review are closed with real, reconcilable artifacts. Delta-range is harmonized everywhere it's stated. Column count is correct. No regressions. No new issues introduced by the fixes. The MCP/backend Phase-5 work is legitimately a separate spec phase and not a Gold blocker.

— @staff-engineer
