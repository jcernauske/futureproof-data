## Staff Engineer Review

### Date: 2026-04-09
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is a clean, well-executed backfill. The transformer was extended to accept an optional `ai_exposure_rows` parameter that integrates via dictionary lookup -- no new SQL complexity, no schema changes to the PCP table, and additive-only columns on career_branches. The join logic is correct, null handling is correct, the inverse invariant holds, and row counts are preserved. The DQ rules are well-designed with real thresholds derived from actual EDA, not guesses. I would put my name on this.

### Code Quality

**src/gold/futureproof_engine.py** -- The backfill integration is minimal and well-placed. `derive_pcp_rows` takes an optional `ai_exposure_rows` parameter, builds a dict lookup keyed by SOC code, and does two `.get()` calls per row. `derive_br_rows` does the same for both source and related SOC codes. The `_overwrite_table` helper is straightforward. Schema evolution for career_branches (lines 758-767) is handled correctly -- checks for missing fields and adds them. One nit: the `Table` type annotation on `_overwrite_table` (line 622) is unresolved -- `pyiceberg.table.Table` is never imported. Works on Python 3.14 due to PEP 649 deferred annotations, but would be a `NameError` on 3.12 or 3.13. Not blocking since this project runs on 3.14, but sloppy.

**Overall:** The code is simple, readable, and does what it says. No over-engineering. The pattern of building a SOC-keyed lookup dict and doing `.get()` is exactly the right approach for this kind of enrichment -- no need for a SQL join on this side since the data is already in memory.

### Test Quality

66 tests, 16 specific to the backfill. All pass in 0.47s. The backfill tests are real:

- `test_stat_res_populated_from_ai_exposure`: Asserts exact value `== 3`, not `is not None`. Good.
- `test_boss_ai_score_populated_from_ai_exposure`: Asserts exact value `== 8`. Good.
- `test_stat_res_null_when_soc_not_in_ai_exposure`: Tests the miss case with a non-matching SOC code. Good.
- `test_stats_available_count_increments_with_ai`: Tests both with and without AI data, asserts `== 4` and `== 5` respectively. Good.
- `test_res_delta_computed`: Asserts `== 2` (6 - 4). Good.
- `test_ai_boss_delta_computed`: Asserts `== -2` (5 - 7). Good.
- `test_deltas_null_when_source_missing` / `test_deltas_null_when_target_missing`: Both verify null propagation for partial matches. Good.
- `test_all_ai_fields_null_without_ai_data`: Verifies all 6 fields are None. Good.
- `test_empty_ai_exposure_list_same_as_none`: Verifies empty list is handled like None. Good.

These are real tests with real assertions. No theater.

### Spec Compliance

The spec is `gold-futureproof-engine` with the addendum noting stat_res and boss_ai_score as placeholders pending Karpathy integration. This backfill completes that integration. Specifically:

- stat_res populated from ai_exposure.stat_res via SOC code lookup: DONE
- boss_ai_score populated from ai_exposure.boss_ai_score via SOC code lookup: DONE
- stats_available_count recomputed to include stat_res: DONE (verified 134,114 rows at count=5, zero mismatches)
- bosses_available_count recomputed to include boss_ai_score: DONE
- career_branches extended with source_res, source_ai_boss, related_res, related_ai_boss, res_delta, ai_boss_delta: DONE
- Row counts preserved (626,406 PCP, 15,944 CB): DONE
- Inverse invariant stat_res + boss_ai_score = 11: VERIFIED (0 violations)
- 4 superseded DQ rules deactivated: DONE

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| PCP: ISU Business Admin (151324/52.02/11-1021) | stat_res | N/A | NULL | NULL | SOC 11-1021 not in ai_exposure (389 rows) | YES -- correct null |
| PCP: SOC 19-1011 (Animal Scientists) | stat_res | N/A | 5 | 5 | ai_exposure table direct query | YES |
| PCP: SOC 19-1011 (Animal Scientists) | boss_ai_score | N/A | 6 | 6 | ai_exposure table direct query | YES |
| PCP total | stat_res coverage | N/A | 57.4% (359,855/626,406) | 57.4% | DQ scorecard GLD-BF-004 | YES |
| PCP total | full pentagon (count=5) | N/A | 134,114 (21.4%) | 20-25% | DQ rule GLD-BF-010 | YES |
| CB: 11-2021 -> 11-2022 | source_res | N/A | 3 | 3 | ai_exposure table direct query | YES |
| CB: 11-2021 -> 11-2022 | res_delta | N/A | 1 | 4 - 3 = 1 | Manual computation | YES |
| CB total | delta coverage | N/A | 25.7% (4,097/15,944) | 22-32% | DQ rule GLD-BF-020 | YES |
| Invariant | stat_res + boss_ai_score = 11 | N/A | 0 violations | 0 | Direct query | YES |

### Governance Artifacts

- **DQ Rules** (20): Real rules with real thresholds. The invariant check (GLD-BF-003) is particularly good -- it catches corruption that range checks alone would miss. Supersession of 4 prior rules is properly documented. Not boilerplate.
- **DQ Scorecard**: 20/20 passing. Run ID 94e7b6d3.
- **Lineage**: Backfill-specific event exists. References consumable.ai_exposure as new input. Column lineage traces stat_res and boss_ai_score back to their source. All 6 career_branches columns documented.
- **Data Contracts**: Both bumped to v1.1.0. stat_res CDE flag updated to true. All 6 new career_branches columns present with constraints.
- **Data Dictionary**: 6 new entries, 2 updated (no more "PLACEHOLDER" language).
- **CAB**: CAB-001 MINOR APPROVED. Requirements executed (contracts, lineage, dictionary all updated).
- **Chaos Monkey**: 5 cycles, 75-85% detection. Acceptable.

### Golden Dataset

The existing golden dataset at `governance/golden-datasets/gold-futureproof-engine-golden.json` was written pre-backfill and correctly shows stat_res=null for the ISU and Daemen rows (those SOC codes are not in ai_exposure). There is no backfill-specific golden dataset. This is acceptable because the backfill adds values from a passthrough join (no derivation complexity), and the data correctness spot-check above confirms the values match the source table. A backfill-specific golden dataset with AI-matched rows would be nice-to-have but is not required given the verification evidence.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | ADVISORY | src/gold/futureproof_engine.py:622 | `Table` type annotation on `_overwrite_table` is unresolved -- `pyiceberg.table.Table` is not imported. Works on Python 3.14 (PEP 649) but would fail on 3.12/3.13. | Add `from pyiceberg.table import Table` to imports, or use a string annotation `"Table"`. Not blocking. |
| 2 | ADVISORY | governance/dq-scorecards | Category column is empty in scorecard (all 20 rows show blank). Cosmetic. | Not blocking. |

### What's Acceptable

The backfill integration pattern is well-chosen -- optional parameter, dictionary lookup, graceful degradation to nulls. The test coverage for the new functionality is thorough with exact-value assertions. The DQ rule suite is well-designed, especially the invariant checks and null-agreement rules. The governance remediation (lineage, contracts, dictionary) was completed per the governance reviewer's requirements. The data is correct.
