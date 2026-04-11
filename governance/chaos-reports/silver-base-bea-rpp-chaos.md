# Chaos Monkey Adversarial DQ Report — silver-base-bea-rpp

- **Spec:** `silver-base-bea-rpp`
- **Target table:** `base.bea_rpp` (51 rows — 50 states + DC, static reference table, 11 columns)
- **Shadow namespace:** `shadow_base.bea_rpp` (in the Silver warehouse)
- **Rules file:** `governance/dq-rules/silver-base-bea-rpp.json` (38 rules — NOT inspected)
- **Run date:** 2026-04-10
- **Runner:** `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py`
- **Isolated probes:** `governance/chaos-manifests/silver_bea_rpp_probes.py`
- **Extra targeted probes:** `governance/chaos-manifests/silver_bea_rpp_extra_probes.py`
- **Manifest:** `governance/chaos-manifests/silver-base-bea-rpp-manifest.json`
- **Probe matrix:** `governance/chaos-manifests/silver-base-bea-rpp-probes.json`
- **Extra probe matrix:** `governance/chaos-manifests/silver-base-bea-rpp-extra-probes.json`
- **Information barrier:** enforced. The chaos runner did NOT read
  `governance/dq-rules/silver-base-bea-rpp.json`, any file under
  `governance/dq-results/`, any file under `governance/dq-scorecards/`,
  `tests/`, or the source of `brightsmith.infra.dq_runner`. The runner
  imports `run_rules()` as an opaque function only. Corruption choices
  are derived from `docs/specs/silver-base-bea-rpp.md`,
  `src/silver/bea_rpp_transformer.py`, and
  `src/silver/_us_state_reference.py`.

## Method

A static 51-row reference table is a poor fit for randomized fuzzing,
so this run uses **scenario-based chaos injection**. The Bronze chaos
cycle (see `governance/chaos-reports/raw-ingest-bea-rpp-chaos.md`)
already covered raw-column mutations; this Silver cycle focuses on
the **Silver-specific derivations** and the new `verification_status`
column:

1. `state_abbr` (derived via `FIPS_TO_USPS` lookup)
2. `census_region` (derived via `FIPS_TO_CENSUS_REGION`, DC → South)
3. `purchasing_power_multiplier` (derived as `100.0 / rpp_all_items`)
4. `verification_status` (derived from the 8-FIPS allow-list)
5. `rpp_all_items` passthrough integrity (Silver row vs Bronze row)
6. `record_id` / `state_fips` uniqueness
7. `data_year` literal + supersession-by-replacement contract

Five escalating cycles (5% → 10%) each apply a bundled scenario pack;
every scenario is then re-run **in isolation** against a clean shadow
to produce an unambiguous per-scenario → rule-id matrix. Two negative
controls (name-swap between IA and OK — both bea_official with
identical rpp and ppm — and a noop) verify the rules do not generate
false positives. Eight **extra targeted probes** (E1–E8) exercise
edge cases the main scenario pack did not isolate cleanly.

All injections honor the three-layer kill switch: the runner sets
`CHAOS_MONKEY_ENABLED=true` and `BRIGHTSMITH_ENV=dev`, refuses to run
without both, and only touches the `shadow_base` namespace. The real
`base.bea_rpp` table is never mutated.

## Cycle Summary

| Cycle | Rate | Label                                    | Scenarios | Rules fired (F) / errored (E) / total | Caught? |
|:----:|:----:|:-----------------------------------------|:----------|:-----:|:-:|
| 1 | 5%  | state_abbr_regex_and_range             | lowercase CA, 3-char CAL, ppm out-of-range | 5F / 1E / 38 | yes |
| 2 | 6%  | census_region_validity_and_coverage    | CA→Pacific, drop West, WY W→MW           | 4F / 1E / 38 | yes |
| 3 | 7%  | verification_status_full_sweep         | unknown value, count drift, flip CA, mark TX | 3F / 1E / 38 | yes |
| 4 | 8%  | passthrough_and_spot_checks            | CA rpp=105, CA ppm drift, DC→WA         | 5F / 1E / 38 | yes |
| 5 | 10% | year_recordid_and_invariants           | year=2023, mixed supersession, dup record_id, ppm=1.0, swap CA/IA | 9F / 1E / 38 | yes |
| 6 | neg | negative_control_swap_ia_ok            | swap IA/OK names (all numerics identical) | 0F / 1E / 38 | yes (silent) |
| 7 | neg | negative_control_noop                  | no mutations                             | 0F / 1E / 38 | yes (silent) |

All 5 real cycles fired at least one rule. Both negative controls
were silent (zero failing rules). **Every cycle — including both
negative controls and the untouched noop — shows SIL-BEA-018 as
ERROR.** See *Known noise / pre-existing gap* below.

## Per-Scenario Caught/Missed Matrix (main scenario pack, isolated probes)

Each of the 20 distinct scenarios was re-run in isolation against a
clean shadow copy. `SIL-BEA-018` always errors in shadow mode and is
reported separately at the end.

| #  | Scenario                                | Expected dimensions                  | Rules fired (excluding SIL-BEA-018 ERROR)                      | Caught? |
|:--:|:----------------------------------------|:-------------------------------------|:----------------------------------------------------------------|:-:|
| 1  | state_abbr lowercase (CA→ca)            | validity                             | SIL-BEA-008, SIL-BEA-009, SIL-BEA-031                            | yes |
| 2  | state_abbr 3-char (CA→CAL)              | validity                             | SIL-BEA-008, SIL-BEA-009, SIL-BEA-031                            | yes |
| 3  | state_abbr swap CA↔IA                   | consistency, validity (bijection)    | SIL-BEA-031, SIL-BEA-037                                         | yes |
| 4  | ppm out-of-range (AZ→2.0)               | validity, reasonableness             | SIL-BEA-020, SIL-BEA-021                                         | yes |
| 5  | census_region CA→Pacific                | validity (IN-list)                   | SIL-BEA-013, SIL-BEA-014, SIL-BEA-015, SIL-BEA-031               | yes |
| 6  | drop West region (13 rows → South)      | coverage, reasonableness             | SIL-BEA-014, SIL-BEA-015, SIL-BEA-031, SIL-BEA-032               | yes |
| 7  | region count shift (WY W→Midwest)       | reasonableness, accuracy             | SIL-BEA-015                                                      | yes |
| 8  | verification_status unknown (AZ→verified) | validity                           | SIL-BEA-022                                                      | yes |
| 9  | verification_status count drift (9th)   | reasonableness, consistency          | SIL-BEA-023, SIL-BEA-024                                         | yes |
| 10 | flip CA verification_status → estimate  | consistency, accuracy                | SIL-BEA-023, SIL-BEA-031                                         | yes |
| 11 | mark TX verification_status → bea_official | consistency, accuracy             | SIL-BEA-023, SIL-BEA-024                                         | yes |
| 12 | passthrough break CA rpp 110.7 → 105.0  | referential_integrity, accuracy      | SIL-BEA-021                                                      | **yes, but only incidentally** — see Gap 1 |
| 13 | CA ppm drift 0.9034 → 0.9100            | accuracy (CA spot check)             | SIL-BEA-021, SIL-BEA-031                                         | yes |
| 14 | DC state_abbr → WA                      | accuracy, consistency                | SIL-BEA-010, SIL-BEA-011, SIL-BEA-033                            | yes |
| 15 | data_year literal break (MT→2023)       | freshness, validity                  | SIL-BEA-027, SIL-BEA-028                                         | yes |
| 16 | year mixed supersession (append 2nd AZ, year=2023) | freshness, uniqueness, reasonableness | SIL-BEA-001, SIL-BEA-003, SIL-BEA-015, SIL-BEA-027, SIL-BEA-028 | yes |
| 17 | duplicate record_id (NJ ← AR's id)      | uniqueness                           | SIL-BEA-026                                                      | yes |
| 18 | ppm inverse invariant break (CA ppm=1.0, rpp=110.7) | consistency, accuracy     | SIL-BEA-021, SIL-BEA-031                                         | yes |
| 19 | negative control: swap IA/OK state_name | (must NOT fire)                      | *(none)*                                                         | yes — correctly silent |
| 20 | negative control: noop                  | (must NOT fire)                      | *(none)*                                                         | yes — correctly silent |

**Main pack score: 18 / 18 real scenarios caught; 2 / 2 negative controls correctly silent.**

## Extra targeted probes (edge cases)

| #  | Probe                                     | Strategy                                                                 | Rules fired                                     | Caught? |
|:--:|:------------------------------------------|:-------------------------------------------------------------------------|:-------------------------------------------------|:-:|
| E1 | self-consistent divergence from Bronze   | CA rpp=105.0 AND ppm=100/105 (inverse invariant stays satisfied)        | SIL-BEA-031 only                                 | **only by CA-row spot check — see Gap 1** |
| E2 | drop Northeast (9 rows → Midwest)         | coverage test on a different region                                     | SIL-BEA-014, SIL-BEA-015, SIL-BEA-034            | yes |
| E3 | DC state_abbr → 'ZZ' (regex-valid, non-canonical) | regex-compliant but not in USPS canonical set               | SIL-BEA-009, SIL-BEA-033                         | yes |
| E4 | data_year future (AL→2025)               | stale/future year                                                       | SIL-BEA-027, SIL-BEA-028                         | yes |
| E5 | null purchasing_power_multiplier (AL)    | completeness on derived column                                          | SIL-BEA-019                                      | yes |
| E6 | state_fips='99' (Alaska)                 | unknown/non-canonical FIPS                                              | *(none)*                                         | **NO — see Gap 2** |
| E7 | duplicate state_fips, unique record_id (2nd Oregon) | state_fips uniqueness independent of record_id               | SIL-BEA-001, SIL-BEA-003, SIL-BEA-006, SIL-BEA-015 | yes |
| E8 | all 51 rows → bea_official               | count=8 rule hard-break                                                  | SIL-BEA-023, SIL-BEA-024                         | yes |

**Extra probe score: 6 / 8 cleanly caught; 2 / 8 trip a real gap.**

## Key observations

- **Every real scenario fires at least one rule.** The rule suite has
  excellent breadth coverage. No corruption slipped entirely undetected.
- **SIL-BEA-031 is clearly a CA-row multi-column spot check.** It
  fires whenever any CA column is mutated (state_abbr, census_region,
  ppm, verification_status) but never fires for non-CA changes or
  negative controls. It accidentally acts as a last-line defense for
  the passthrough invariant when CA is corrupted — but only for CA.
- **SIL-BEA-033 is a DC-specific spot check** (fires only when DC is
  touched). SIL-BEA-034 appears to fire on Northeast coverage drops
  and did NOT fire on West-region drops — suggesting it may be a
  region-specific count rule rather than a generic all-regions check.
- **Pure uniqueness violation is detected.** Scenario 17 changes a
  single record_id to collide without touching row count; SIL-BEA-026
  fires on its own. Probe E7 duplicates state_fips with a unique
  record_id; SIL-BEA-006 fires distinct from the row-count rule.
- **The ppm range rule (SIL-BEA-020) is wide enough to miss
  plausible-but-wrong values** (0.91 vs 0.9034). The CA spot check
  (SIL-BEA-031) catches that case for California. Whether every
  BEA-verified state has the same spot-check coverage is NOT verified
  by this run; see Hardening Proposal 3.
- **Both negative controls are silent.** Swapping IA/OK names (both
  bea_official, both rpp=87.8, both ppm=1.1390) fires zero rules.
  The no-op fires zero rules. The rule suite does not produce false
  positives on the specific cases tested.

## Gaps found

### Gap 1 — No dedicated Silver↔Bronze referential integrity rule for `rpp_all_items`

**Evidence:** Probe E1 sets `rpp_all_items=105.0` **and**
`purchasing_power_multiplier=100/105` on California. This is
self-consistent (inverse invariant `SIL-BEA-021` passes) but diverges
from Bronze, which still has 110.7. Only **SIL-BEA-031** fires — the
CA row spot check. If the same self-consistent divergence had been
applied to Texas, Florida, or any of the 43 estimate rows, **nothing
would have caught it** (because only CA and DC have spot-check rules
matching SIL-BEA-031 / SIL-BEA-033).

The spec (line 93) promises a rule: *"rpp_all_items passthrough
invariant: every Silver row's rpp_all_items equals the Bronze row's
value for the same state_fips (P0 — referential integrity to source)"*.
From the error pattern (see Gap 3), that rule may be **SIL-BEA-018**,
but it errors in shadow mode and therefore never fires on a real
corruption. Either way, the observable behavior is the same: **a
self-consistent rpp/ppm edit on any non-CA, non-DC state would ship
silently.**

**Recommended new (or repaired) rule:**

> `SIL-BEA-NEW-PASSTHROUGH`: for every `state_fips` in `base.bea_rpp`,
> assert `silver.rpp_all_items == bronze.bea_rpp.rpp_all_items`
> within a tight tolerance (e.g., `1e-9`). Must be evaluated in
> shadow mode by pointing the Silver side at `{zone_prefix}.bea_rpp`
> and the Bronze side at the real `bronze.bea_rpp`.

### Gap 2 — No `state_fips` canonical-set rule

**Evidence:** Probe E6 sets Alaska's `state_fips` to `'99'` (not in
the 51 valid FIPS codes). The regex `^\d{2}$` still matches, so any
format-only check lets it through. **Zero rules fire.** SIL-BEA-031
does not fire because CA is untouched. The row count is still 51 so
volume rules are silent. The state_name still says "Alaska" so
bijection rules (whichever one SIL-BEA-037 is, keyed on the pair)
are silent unless they actually enforce that state_fips ∈ valid set.

The spec (line 88) promises a rule: *"state_fips non-null and
uniqueness"*, but **says nothing about state_fips being in a canonical
51-member set**. This is a gap in the spec itself, not just the rules.

**Recommended new rule:**

> `SIL-BEA-NEW-STATE-FIPS-SET`: assert every `state_fips` value is in
> the canonical 51-member set (50 states + `'11'` for DC). This is
> the same shape as the existing state_abbr canonical-set rule but
> for the underlying key.

### Gap 3 — SIL-BEA-018 errors in shadow mode on every cycle

**Evidence:** Every single cycle, every isolated probe, every extra
probe, and both negative controls show **`SIL-BEA-018` in ERROR**
state (not PASS, not FAIL). This includes `scenario_neg_noop`, which
injects zero mutations and leaves the shadow table bit-identical
to `base.bea_rpp`. If the rule errors on an untouched copy, the rule
— not the data — is at fault.

The most likely cause, inferred from the spec, is that SIL-BEA-018 is
the Silver↔Bronze `rpp_all_items` passthrough invariant rule. When
invoked with `shadow=True`, the DQ runner probably rewrites the
Silver table reference to `shadow_base.bea_rpp` but does not know how
to handle a cross-zone join and the rule raises.

**Impact:** Gap 1 and Gap 3 are the *same problem* observed from
two different angles. The rule exists on paper (spec line 93) and
probably exists in the JSON (since the suite reports 38 rules and
the spec enumerates roughly that many), but it is not **effectively
runnable** against a shadow table, which is exactly the context in
which chaos testing lives. This means:

- In normal operation, the rule passes on real data (hence the
  reported 38/38 pass rate).
- In chaos testing, the rule always errors, so any passthrough
  corruption escapes detection via this rule.
- The net effect is that Silver chaos coverage of the passthrough
  invariant is zero.

**Recommended fix (for @dq-rule-writer):**

1. Investigate the SIL-BEA-018 rule expression. If it uses a
   hard-coded `base.bea_rpp` reference that doesn't get rewritten in
   shadow mode, either (a) rewrite it using the DQ runner's shadow
   helper, or (b) rewrite the DQ runner to support shadow-rewritable
   cross-zone references.
2. Confirm with a repeat chaos run that SIL-BEA-018 PASSes on the
   noop probe and FAILs on probe E1 / scenario 12 (passthrough
   breaks).

### Gap 4 (suspected, not fully verified) — region-specific coverage rules

**Evidence:** `scenario_drop_west_region` fires SIL-BEA-032 but
`probe_drop_northeast_region` fires SIL-BEA-034. These look like
separate per-region rules rather than a single "all 4 regions
present" rule. If that inference is correct, dropping Midwest or
South might fire yet another rule, OR fire none at all if the suite
only has rules for West and Northeast.

**Recommended probe (NOT run here, to stay within the barrier):**
run two additional probes — drop all Midwest rows and drop all South
rows — and compare the fired-rule sets. If one region lacks a
dedicated rule, add one. This is a follow-up, not a blocker.

## Hardening proposals (optional — for dq-rule-writer review)

Proposals below are **suggestions only**, not gaps. They belong in a
dq-rule-writer iteration, not an automatic merge.

1. **Fix SIL-BEA-018 to work in shadow mode** — see Gap 3 above.
2. **Add `state_fips IN canonical_51_set` rule** — see Gap 2 above.
3. **Add per-state spot-check rules for every BEA-verified state.**
   Right now the run suggests spot-check rules exist for CA (SIL-BEA-031)
   and DC (SIL-BEA-033) but probably not for the other six
   bea_official states (HI, NJ, AR, MS, IA, OK). A self-consistent
   divergence on any of those six would not be caught outside of the
   Bronze passthrough rule (which currently errors in shadow).
4. **Add a generic `all 4 census_region values present` rule.** A
   single rule `COUNT(DISTINCT census_region) = 4` is simpler to
   audit than one rule per region and equally robust.
5. **Add a regional-count distribution rule** with the canonical
   `{Northeast: 9, Midwest: 12, South: 17, West: 13}` mapping. The
   current rule set catches the brute "all West → South" case but
   the `region_count_shift` probe (single-row WY West → Midwest) only
   fires SIL-BEA-015 which looks like the "all 4 regions present"
   rule; the count distribution itself does not appear to be checked.
6. **Add a `verification_status` subset rule keyed on `state_fips`.**
   The current rules catch (a) `COUNT(bea_official)=8` and (b)
   probably an allow-list subset. But they don't catch the
   *composition*. A rule of the form `verification_status='bea_official'
   IFF state_fips IN {canonical 8}` would collapse the three existing
   verification-status rules into one precise invariant that fires on
   any drift in either direction.
7. **Freshness coherence rule** — already proposed in the Bronze
   chaos report; carries forward here because Silver inherits the
   same risk (`source_load_date` and `data_year` could drift).

## Known noise / pre-existing gap

`SIL-BEA-018` errors in every cycle including the noop negative
control. The rule never returns either a PASS or FAIL in shadow
mode. This is treated as **pre-existing rule-level noise** for the
purposes of the chaos run (it is not caused by chaos injection), but
it is also **Gap 3 above**: the rule set's coverage of the Bronze
passthrough invariant is effectively zero in the chaos context.

The chaos reconciliation logic intentionally ignores ERROR'd rules
when deciding whether a cycle "caught" an injection — otherwise
every cycle would trivially show 1 "fired" rule from SIL-BEA-018 and
the negative controls would appear to be false positives. Classifying
ERROR as a third state (not PASS, not FAIL) is how we maintain
per-scenario attribution.

## Verdict

- **18 of 18** real main-pack scenarios caught at least once.
- **6 of 8** extra targeted probes cleanly caught.
- **2 real gaps** identified: (E1) self-consistent Silver↔Bronze
  divergence escapes for non-CA, non-DC states; (E6) unknown
  `state_fips` code escapes entirely.
- **1 pre-existing rule-level issue** (SIL-BEA-018) identified as
  the likely root cause of gap E1 — the Bronze passthrough rule
  errors in shadow mode on untouched data.
- **Both negative controls silent** — zero false positives in the
  tested no-op and IA/OK-name-swap cases.

### Skippable downstream step?

**The adversarial-auditor step should NOT be skipped for this spec.**
Despite 5 clean cycles and 18/18 main-pack scenarios caught, the
chaos run found two concrete gaps and a pre-existing rule error that
warrant review by a human adversarial auditor:

1. Gap 1 (self-consistent passthrough divergence) — needs a human
   judgment on whether SIL-BEA-018 should be patched, whether a new
   rule should be written, or whether the zone-join limitation is
   an acceptable shadow-mode carve-out documented in the DQ runner
   contract.
2. Gap 2 (state_fips canonical-set rule) — the spec itself doesn't
   require this rule; a human should decide whether the spec needs
   amending or whether the transformer-side validation
   (`_validate_state_fips`) is enough defense-in-depth.
3. Gap 3 / SIL-BEA-018 — a broken-in-shadow rule is a chaos-testing
   integrity issue, not a data issue, and should be surfaced to the
   staff engineer.

The "zero gaps in ≥5 cycles → skippable" condition is **not met**.
The auditor should see this report before staff review.
