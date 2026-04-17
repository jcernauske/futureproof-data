# Staff Engineer Review: onet-experience-requirements (Silver Zone)

**Review Type:** Final Quality Gate — Silver zone only
**Reviewer:** @staff-engineer
**Date:** 2026-04-17
**Status:** **APPROVED (with mandatory pre-Gold cleanup items)**

---

## Verdict

The Silver zone is production-quality. The weighted-median algorithm is correct, the multi-detail aggregation math checks out against raw O*NET Bronze data for all three spec spot-checks, the transformer is small and readable, and the 55-test suite is real coverage — not ceremony. I'd put my name on this, with one caveat: there are five documentation drifts and status flips that will bite someone in 12 months if nobody sweeps them before Gold. None are data-integrity defects; all are housekeeping. I'm approving Silver so Gold can proceed, but the cleanup list below is not optional — register it as a pre-Gold checklist or park it as a tech-debt spec.

---

## Correctness of the Weighted-Median Implementation

I re-derived each spot-check by hand from raw Bronze (real O*NET 30.2 `bronze.onet_experience` parquet) and compared to Silver output:

| BLS SOC | Bronze distribution (reconstructed) | Expected median (manual walk) | Silver output | Spec §Test Matrix | Match? |
|---|---|---|---|---|---|
| 15-1252 (Software Developers, single detail `.00`) | cat 1: 4.42, cat 6: 11.13, cat 7: 7.13, cat 8: 15.04, cat **9: 43.91**, cat 10: 7.82, cat 11: 10.55 | cat 9 → 7.0 yr → **mid** | cat 9, 7.0 yr, **mid** | mid | YES |
| 41-2031 (Retail Salespersons, bimodal) | cat 1: 39.75, cat 2: 0.65, cat 3: 2.97, cat **5: 32.02**, cat 6: 7.29, cat 7: 6.87, cat 10: 9.79 | cat 5 (cum 43.37 → 75.39) → 0.75 yr → **entry** | cat 5, 0.75 yr, **entry** | entry | YES |
| 11-1011 (Chief Executives, multi-detail `.00`+`.03`) | `.00`: cat 11=68.24 → cat 11, 12yr; `.03`: cat 6=3.7, 7=11.11, **8=40.74**, 9=18.52, 10=11.11, 11=14.81 → cat 8, 5yr | Unweighted mean years: (12+5)/2 = **8.5 yr** → senior (just above threshold). Merged distribution yields median cat 9 (cum 52.36 at cat 9) | cat 9, 8.5 yr, **senior** | senior | YES |

All three are mathematically correct given the human-approved rules. The bimodal case for 41-2031 is the important one — the spec explicitly warns against writing a `median_category <= 3` rule for entry tier, and the transformer demonstrably produces cat=5 while still correctly classifying as `entry` via the 0.75 yr midpoint. Good.

The tie-break logic at 50% (pick-lower) is covered by three targeted unit tests (`test_tie_at_50pct_picks_lower`, `test_tie_at_50pct_three_buckets`, `test_multi_detail_aggregation`). The `_TIE_EPS = 1e-9` epsilon is defensible given EDA's reported ±0.03 precision on upstream frequency sums.

---

## Code Quality

**`src/silver/onet_experience_transformer.py` — 557 lines, clean.** Reads like a staff engineer wrote it:

- Pure helpers (`weighted_median_category`, `derive_experience_tier`, `_argmax_category`) are isolated from Iceberg I/O. This is why the unit tests can run in 0.52s — they exercise the actual logic without warehouse mocks.
- Constants at module top, every magic number has a named reference and a comment linking to the approval file.
- `transform_experience_profiles()` accepts `valid_bls_socs: set[str] | None` — the `None` case is a real, tested degradation path, not a TODO.
- `_read_valid_bls_socs` catches a broad `Exception` for the "table not present" case. I'd prefer a narrower catch (pyiceberg raises `NoSuchTableError`), but the broad catch is logged at WARNING with the exception chained, and the test suite covers both branches. Acceptable.
- Docstrings cite the approval file for every non-obvious decision (midpoints, tie-break, multi-detail averaging). This is what "comments explain WHY, not WHAT" looks like.

One nit, not blocking: the `load_date` handling in `_group_rw_rows_by_onet_soc` keeps the **first-seen** load_date for a given O*NET-SOC, while `_aggregate_to_bls` takes the **min** across multi-details. Both are deterministic but the asymmetry isn't called out anywhere. If you refresh O*NET mid-run (you won't), the per-SOC load_date could lag the per-BLS one by up to one ingest cycle. Document it or unify to min across both layers.

---

## Test Quality

55 tests, all pass in 0.52s. Spot-checked three:

1. **`test_retail_salespersons_bimodal`** — asserts `weighted_median_category(...)` returns exactly `5` on a real-data distribution where cat 1 is the mode (39.75%). This is the test that would have caught a naive "pick the mode" bug. Real assertion against real upstream data. Not theater.

2. **`test_tie_at_50pct_picks_lower`** — `{3: 50.0, 8: 50.0}` → asserts `== 3`. This is a single-line assertion with a specific expected value, not `> 0` or `is not None`. If the epsilon-compare at line 139 ever flipped sign, this test fails deterministically.

3. **`test_multi_detail_aggregation`** — builds rows for `15-1252.00` (cat 9, years 7) + `15-1252.01` (cat 7, years 3), asserts BLS row has `experience_years_typical == 5.0`, `experience_tier == "mid"`, AND the merged distribution median is cat 7 (the tie-at-50 rule fires correctly in the merged distribution). This is not just a smoke test — it validates that the re-derivation-from-merged-distribution rule in `_aggregate_to_bls` produces the same result a human would compute.

Test depth verdict: **real coverage**. Well above the 15-test Silver minimum. The fixtures use `make_distribution_rows` so test data mirrors Bronze shape; there's no "construct a Silver row directly and assert on it" shortcut.

---

## Spec Compliance

All 7 cases in spec §Test Matrix have corresponding tests and production-code behaviour:

| Case | Spec expectation | Test / Code? |
|---|---|---|
| 1. Empty distribution | Skip, log provenance | `test_empty_input`, `test_empty_distribution_case_skipped` — PASS |
| 2. Single category 100% | Median = that category | `test_single_category_100pct`, `test_single_category_at_cat_11` — PASS |
| 3. All suppressed | `suppress_flag=True`, excluded from DQ spot checks | `test_all_suppressed_produces_row_with_flag`, `test_all_suppressed_still_produces_detail` — PASS |
| 4. Tie at 50% | Pick lower-numbered | 3 tests — PASS |
| 5. Multi-detail aggregation | Unweighted avg, `onet_details_averaged=2` | `test_multi_detail_aggregation` — PASS |
| 6. Missing source experience (Gold) | NULL propagation | Gold rule `GLD-CB-EXP-002` uses `WHERE ... IS NOT NULL` clause; Silver Test Matrix case is Gold's job to verify |
| 7. Known-value spot checks | 11-1011=senior, 41-2031=entry | 3 DQ spot-check rules + 3 unit tests — PASS |

Silver schema matches physical model (11 NOT NULL fields, types aligned). Grain matches (`bls_soc_code`). DQ row-count range `[720, 810]` matches contract volume range. Column-level CDE flags match between contract and data-dictionary.

---

## Silver-to-Gold Handoff Readiness

**Green light, with known coverage gap surfaced.** Specifically:

- `base.onet_experience_profiles` = 765 rows, 765 distinct `bls_soc_code`. Grain is solid for a double-join in Gold (`career_branches.soc_code → exp_source.bls_soc_code`, `career_branches.related_soc_code → exp_related.bls_soc_code`).
- Silver output range for `experience_years_typical` is `[0.0, 8.5]`, well within Gold rule `GLD-CB-EXP-002` range `[-12, +12]` on `experience_delta_years`.
- Gold null-rate rule `GLD-CB-EXP-001` has been pre-calibrated to `< 15%` (not the spec's original `< 5%`) because Silver covers 765 BLS SOCs vs the broader career_branches target universe (~867 BLS SOCs). Worst-case null rate is 11.8% — this is the right call, and the rule file documents the math clearly. **But:** the rule is still `proposed` and has not been executed — it will only pass if Silver coverage holds on the first Gold run. There is no margin for surprise.
- The NULL-propagating `CASE` for `experience_delta_years` is correctly specified in the spec at line 227; Gold transformer must implement it faithfully.
- FK integrity: 0 BLS SOCs from Silver are dropped by the LEFT-JOIN to `base.onet_occupations` in the last real run. Code path is exercised by tests + chaos scenario S6.

The single-row senior tier (`11-1011`, 8.5 yr, 0.5-yr margin above threshold) will become a P0 consistency alarm in Gold via rule `GLD-CB-EXP-003`. That's correct; if a future O*NET refresh flips this row to 7.95 yr (mid tier), Silver's `SLV-ONET-EXP-008` spot-check fires FIRST as a P0 regression signal. The canary is positioned correctly.

---

## Production Risk Analysis (12-Month Horizon)

What breaks on the next O*NET refresh:

1. **Senior tier goes to zero.** Most likely single failure. 11-1011's two details currently average to 8.5 yr. O*NET 30.3/31.x could nudge `.03` downward (e.g., cat 8 at 40.74% → cat 7 at 40.74%), dropping years to ~4.0 and flipping `.03`'s tier to early. Unweighted average becomes (12 + 3)/2 = 7.5 → mid tier. Senior tier count = 0. `SLV-ONET-EXP-007` (all-4-tiers-present, **P1**) fires a warning. `SLV-ONET-EXP-008` (11-1011=senior, **P0**) fires a hard failure. Good — the canary works. Action: when this fires, do NOT patch the P0 rule. Investigate whether the real-world role changed, and potentially lower the senior threshold or accept mid as the new answer.

2. **Row count drifts outside [720, 810].** Per EDA, 878 O*NET details → 765 BLS SOCs. O*NET versioning adds/retires ~5-20 SOCs per release. If a release adds 50+ new SOCs, the count hits 810 and `SLV-ONET-EXP-001` (P0) fails. This is the right behaviour — forces a governance review of the new SOCs before they silently flow to Gold.

3. **`experience_years_typical` max exceeds 8.5 yr.** Nothing in Silver guards against a genuine "all details hit cat 11" row pushing years to 12.0. `SLV-ONET-EXP-004` (range 0-15, P0) has 3.5 yr of headroom above the current maximum. Healthy margin.

4. **Multi-detail SOC fan-out explodes.** Currently max is `onet_details_averaged=8` (1 SOC). If a future release adds 15 details to one SOC, unweighted averaging continues to work but the distributional "meaning" gets fuzzy. Not a rule-fire, but worth adding a P1 rule: `MAX(onet_details_averaged) <= 12` would flag the edge case before Gold sees it.

5. **`base.onet_occupations` missing on first run.** The code handles this gracefully (falls back to no FK filter, logs WARNING). If someone runs Silver without Silver O*NET occupations, they get 765 rows either way — the LEFT-JOIN filter does nothing when the occupations table isn't populated. This is correct per spec, but a rebuild_all.py ordering bug would silently push unvetted SOCs through. Recommend a startup assertion in `_read_valid_bls_socs` that logs the occupation row count alongside the None-return, so a `0-rows-returned` state is visible in logs.

---

## Issues Found

| # | Severity | File / Artifact | Issue | Required Fix |
|---|---|---|---|---|
| 1 | **CHANGES REQUESTED (pre-Gold, non-blocking for Silver)** | `governance/lineage/onet-experience-silver-20260417-022909.json` lines 15, 37, 162, 195 | Lineage facet documents **wrong midpoint table** (`Cat 2=0.25, 3=0.75, 4=1.5, 5=3.0`). Actual transformer uses spec-correct midpoints (`2=0.0, 3=0.17, 4=0.38, 5=0.75`). This is a governance-artifact drift, not a code defect — but OpenLineage is supposed to be the authoritative provenance record. An auditor reading the lineage file and reconstructing the math would get wrong answers. | Regenerate the Silver lineage event with the correct midpoint table string in `brightsmith_agentAttribution.reasoning`, `job.facets.documentation.description`, `outputs[0].facets.transformationDescription.description`, and `outputs[0].columnLineage.experience_years_typical.transformationDescription`. Cite `governance/approvals/onet-experience-requirements-open-decisions.md` as the source. |
| 2 | MINOR | `governance/dq-rules/silver-onet-experience.json` — all 10 rules | All 10 rules remain `status: "proposed"` despite passing real-data execution. Post-review correctly flagged this; rule status is a governance gate. | Lift all 10 Silver rules to `status: "active"` before or concurrent with Gold DQ execution. |
| 3 | MINOR | `governance/models/silver-base-onet-experience-physical.md` lines 55, 62, 154 | Physical-model narrative still says "~867 rows" while binding artifacts (DQ rule, contract) correctly say `[720, 810]`. Documentation drift, not a data issue. | Search-and-replace `867 → 765` in the narrative sections. |
| 4 | MINOR | `governance/dq-rules/` — no FK assertion rule | Logical model declares FK `onet_experience_profiles.bls_soc_code → onet_occupations.bls_soc_code`. Transformer enforces via LEFT-JOIN-drop, but no DQ rule fails if a drift occurs. | Add Silver rule `SLV-ONET-EXP-011` (P1): `SELECT bls_soc_code FROM onet_experience_profiles WHERE bls_soc_code NOT IN (SELECT bls_soc_code FROM onet_occupations)` — threshold `result_count = 0`. |
| 5 | ADVISORY | `src/silver/onet_experience_transformer.py::_read_valid_bls_socs` | Broad `except Exception` at line 481 catches any failure mode but silently proceeds without the FK filter. Safer for development, riskier for production drift. | Narrow to `except pyiceberg.exceptions.NoSuchTableError` (or equivalent), emit WARNING with row count when table IS present, and error out (not warn) if table is present but empty. |
| 6 | ADVISORY | `src/silver/onet_experience_transformer.py::_aggregate_to_bls` | `load_date` handling: `_group_rw_rows_by_onet_soc` keeps first-seen load_date per O*NET-SOC; `_aggregate_to_bls` takes min across details. Asymmetric, undocumented. | Unify to min-across-all-layers OR add a 1-line comment explaining why first-wins-then-min is intentional. |

No CHANGES REQUESTED at a data-integrity level. No REJECTED.

---

## What's Acceptable

The transformer is short, pure, and obviously correct on inspection. The 55 unit tests don't cheat. The chaos-monkey 5-cycle × 9-scenario run produced zero gaps against real Bronze data. The adversarial audit produced three findings, one of which was fixed at the test layer (the 11-1011 single-detail docstring clarification) rather than being waved away. DQ execution ran against a real Iceberg snapshot, not a fixture, and recorded `snapshotId=5745163851101673330` in both the DQ results file and the lineage event — those two numbers actually reconcile.

The test file doesn't have a single `assert True`, `assert len(...) > 0`, or `assert X is not None` where a specific value was expected. `test_source_load_date_earliest_wins` is a good example: two details with different load dates, the test asserts `== EARLIER_LOAD_DATE`, not "is not None". That's how you tell someone wrote tests to catch regressions, not to hit coverage numbers.

Fine work. Ship it to Gold.

---

## Review Decision

**APPROVED for Silver zone closure.** Gold zone pre-implementation review (Phase 4 step 23, `bs:cab-agent`) may proceed.

The 6 issues above are **required cleanup items before Gold sign-off** — but none of them gate Silver closure. The cleanup can run in parallel with Gold Phase 4 work.

---

## Audit Trail

- **Scope:** Silver zone only. Bronze closed with prior staff-engineer APPROVED. Gold/MCP out of scope.
- **Spec:** `docs/specs/onet-experience-requirements.md` (v1.0, revised 2026-04-16)
- **Iceberg snapshot reviewed:** `5745163851101673330`
- **Transformer file:** `src/silver/onet_experience_transformer.py` (557 lines)
- **Test file:** `tests/silver/test_onet_experience_transformer.py` (55 tests, all PASS in 0.52s)
- **DQ run reviewed:** `governance/dq-results/silver-onet-experience-20260417-023011.json` (10/10 PASS, p0_passed=true)
- **Governance review:** `governance/approvals/onet-experience-requirements-post-review-silver.md` (APPROVED)
- **Spot-checks verified independently** against raw O*NET Bronze parquet (`data/bronze/iceberg_warehouse/bronze/onet_experience/`) — all three matched.
- **Reviewer:** @staff-engineer
- **Date:** 2026-04-17
- **Verdict:** APPROVED (with 6 pre-Gold cleanup items, none blocking Silver)
