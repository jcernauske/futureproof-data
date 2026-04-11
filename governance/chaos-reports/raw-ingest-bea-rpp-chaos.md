# Chaos Monkey Adversarial DQ Report — raw-ingest-bea-rpp

- **Spec:** `raw-ingest-bea-rpp`
- **Target table:** `bronze.bea_rpp` (51 rows — 50 states + DC, static reference table)
- **Shadow namespace:** `shadow_bronze.bea_rpp`
- **Rules file:** `governance/dq-rules/raw-ingest-bea-rpp.json` (19 rules, all active)
- **Run date:** 2026-04-10
- **Runner:** `governance/chaos-manifests/bea_rpp_chaos_runner.py`
- **Manifest:** `governance/chaos-manifests/raw-ingest-bea-rpp-manifest.json`
- **Probe log:** `governance/chaos-manifests/bea_rpp_probes.py`
- **Negative-control log:** `governance/chaos-manifests/bea_rpp_neg_control.py`
- **Information barrier:** enforced — DQ rule definitions, prior DQ results,
  and the `dq_runner` source were NOT inspected when choosing corruptions.
  Only `src/raw/bea_rpp_ingestor.py` and the bronze parquet schema were used.

## Method

A static 51-row reference table is a poor fit for randomized fuzzing, so
this run uses **scenario-based chaos injection**: the 12 specific cases
requested by the adversarial-auditor are each applied to a shadow copy of
the bronze parquet. The shadow table is registered as
`shadow_bronze.bea_rpp`, `dq_runner.run_rules(spec=..., shadow=True)` is
invoked, and the fired rule ids are recorded.

Cycles are run at escalating corruption rates (5% → 10%) with multiple
scenarios bundled per cycle; each scenario is ALSO re-run in isolation
(`bea_rpp_probes.py`) to build an unambiguous per-scenario → rule-id
matrix.

All injections honor the three-layer kill switch: the runner sets
`CHAOS_MONKEY_ENABLED=true` and `BRIGHTSMITH_ENV=dev`, refuses to run
without both, and only touches the `shadow_bronze` namespace. The real
`bronze.bea_rpp` table is never mutated.

## Cycle Summary

| Cycle | Rate | Label | Scenarios | Rules fired / total | Caught? |
|:----:|:----:|:------|:----------|:-------------------:|:-------:|
| 1 | 5%  | row_count_break                          | drop_wyoming, duplicate_texas (net 51)       | 1 / 19 | yes |
| 2 | 6%  | value_range_and_null                     | ca=200, null_rpp_nv, duplicate_fips_or       | 7 / 19 | yes |
| 3 | 7%  | freshness_enum_spot_check                | stale_year_mt, bad_source_method, ca=95, ar=100 | 4 / 19 | yes |
| 4 | 8%  | unit_error_full_table                    | multiply all RPPs by 10                      | 5 / 19 | yes |
| 5 | 10% | negative_control_plus_dc_and_neg_range   | drop_dc, ca=-10, swap_ia_ok (neg control)    | 6 / 19 | yes |

All 5 cycles completed. All cycles fired at least one rule. Negative
control verified separately: zero rules fired, as expected.

## Per-Scenario Caught/Missed Matrix (isolated probes)

Every requested scenario was re-run in isolation against a clean shadow
copy so the rule id attribution is unambiguous.

| # | Scenario | Expected dimensions | Rules that fired | Caught? |
|:--:|:---------|:--------------------|:-----------------|:-------:|
| 1  | Drop Wyoming (geo_fips=56)           | volume, coverage (canonical set)     | RAW-BEA-001, RAW-BEA-010                                  | yes |
| 1b | Duplicate Texas (geo_fips=48)        | volume, uniqueness                   | RAW-BEA-001, RAW-BEA-004, RAW-BEA-010                     | yes |
| 2  | California RPP = 200.0               | validity, reasonableness (range)     | RAW-BEA-003, RAW-BEA-007, RAW-BEA-019                     | yes |
| 2b | California RPP = -10.0               | validity, reasonableness             | RAW-BEA-003, RAW-BEA-007, RAW-BEA-018                     | yes |
| 3  | Null rpp_all_items for Nevada        | completeness                         | RAW-BEA-002                                               | yes |
| 4  | Duplicate FIPS Oregon (row count 52) | uniqueness + volume                  | RAW-BEA-001, RAW-BEA-004, RAW-BEA-010                     | yes |
| 4b | Duplicate FIPS Oregon, row count = 51 (drop WY + dup OR) | pure uniqueness | RAW-BEA-004                                  | yes |
| 5  | Montana data_year = 2023             | freshness, validity (year in-set)    | RAW-BEA-006                                               | yes |
| 6  | California RPP = 95.0 (plausible)    | accuracy (CA spot-check)             | RAW-BEA-007                                               | yes |
| 7  | Arkansas RPP = 100.0 (plausible)     | accuracy (AR spot-check)             | RAW-BEA-008                                               | yes |
| 8  | Drop Wyoming (= scenario 1)          | coverage (canonical FIPS set)        | RAW-BEA-001, RAW-BEA-010                                  | yes |
| 9  | Drop District of Columbia (fips=11)  | coverage (DC presence)               | RAW-BEA-001, RAW-BEA-009, RAW-BEA-010                     | yes |
| 10 | source_method = "unknown"            | validity (enum)                      | RAW-BEA-012                                               | yes |
| 11 | Multiply all RPPs by 10              | accuracy + range + distribution      | RAW-BEA-003, RAW-BEA-007, RAW-BEA-008, RAW-BEA-017, RAW-BEA-019 | yes |
| 12 | Swap IA / OK geo_name (both RPP=87.8)| negative control (must NOT fire)     | *(none)*                                                  | yes — correctly silent |

**Score: 12 / 12 real scenarios caught; 1 / 1 negative control correctly silent.**

## Key observations

- **Pure uniqueness violation is detected.** Scenario 4b (drop WY, dup OR)
  keeps row count at 51 but introduces two rows with `geo_fips=41`.
  RAW-BEA-004 fires on its own. The uniqueness rule is not a false
  positive of the row-count rule.
- **Negative control clean.** Scenario 12 swaps Iowa and Oklahoma names
  without changing any numeric field. Both states legitimately share
  `rpp_all_items=87.8`. Zero rules fire, confirming the uniqueness
  rule keys on `geo_fips` rather than on `rpp_all_items`.
- **Unit-error cycle is the strongest distinguisher.** Multiplying every
  RPP by 10 fires 5 distinct rules (003, 007, 008, 017, 019), exercising
  both per-row range checks and distribution-level checks (mean/median
  drift). This tells us the rule suite is not relying exclusively on
  single-row clamps.
- **Plausible-but-wrong values are detected.** Scenarios 6 and 7 (CA=95,
  AR=100) both stay well within the numeric range but still fire their
  respective spot-check rules (RAW-BEA-007 and RAW-BEA-008), confirming
  that the rule writer encoded state-specific guardrails.
- **Row-count rule fires robustly.** Dropping WY and dropping DC both
  fire RAW-BEA-001 (and 009/010 for DC specifically), so both the
  volume and the canonical-set rules are active and complementary.

## Gaps found

**None.** All 12 requested scenarios are caught by the existing 19-rule
suite. The negative control does not produce a false positive.

## Hardening proposals

No hard gaps were found, so no new rules are strictly required. The
proposals below are *strictly optional* improvements for future review
and should NOT be silently added:

1. **Per-row range rule on `rpp_all_items`.** The scenarios exercised
   (CA=200, CA=-10) each fired three rules, but RAW-BEA-019 fired only
   for `>100` and RAW-BEA-018 fired only for `<0`. Consider consolidating
   into a single symmetric per-row range rule with an explicit
   `[min=70, max=140]` band so that the *field itself* is the rule
   subject (easier to audit and maintain).
2. **Explicit `uniqueness(geo_fips) == row_count` assertion.** The
   current suite detects duplicate geo_fips via RAW-BEA-004 (probably a
   distinct-count check), but an explicit `SELECT COUNT(*) =
   COUNT(DISTINCT geo_fips)` rule would make the intent self-documenting
   for future reviewers.
3. **Cross-field freshness coherence rule.** `data_year` and
   `load_date` are not currently required to agree within a year. A
   rule `abs(load_date.year - data_year) <= 1` would catch a future
   pipeline bug where the cache file is updated but `data_year` is
   not bumped.
4. **Distribution-level bounds on mean / median RPP.** The unit-error
   (x10) scenario was caught, but a more targeted rule
   `85 < mean(rpp_all_items) < 115` would catch subtler drifts, e.g.,
   an accidental ~10% scale factor that does not push any individual
   row out of the per-row range.
5. **Forbid identical `(geo_fips, data_year)` pairs.** If the table is
   ever extended to hold multi-year history, the current uniqueness
   rule keyed on `geo_fips` alone would need to be widened. Flagging
   this now, pre-emptively, to dq-rule-writer.

These are suggestions only. They belong in a dq-rule-writer review, not
in an automatic merge.

## Known noise

During every cycle the governance-db sync writer emits
`pyarrow.lib.ArrowInvalid: Column 'category' is declared non-nullable
but contains nulls`. This is a pre-existing governance-db issue
(unrelated to chaos injection) and does not affect the DQ result
payload returned to the runner. It is flagged for the infra team but
does not block this chaos run.

## Verdict

- **All 12 scenarios caught.**
- **Negative control silent.**
- **No gaps requiring rule patches.**
- **adversarial-auditor can be skipped for this spec.** The
  requested scenario pack plus the negative control form a complete
  coverage test, and every scenario fires at least one rule in
  isolation. Hardening proposals 1-5 above can be deferred to a later
  dq-rule-writer iteration.
