# Staff Engineer Review: silver-base-bea-rpp

**Review Type:** Final Sign-off
**Reviewer:** @staff-engineer
**Date:** 2026-04-10
**Zone:** Silver (Base)
**Spec:** `docs/specs/silver-base-bea-rpp.md`
**Parent spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Pre-review:** `governance/approvals/silver-base-bea-rpp-pre-review.md` (APPROVED after remediation)
**Post-review:** `governance/approvals/silver-base-bea-rpp-post-review.md` (APPROVED)
**Adversarial audit:** `governance/adversarial-audits/silver-base-bea-rpp.md` (HIGH-2, HIGH-3 fixed; HIGH-1 deferred as a brightsmith framework ticket)
**Verdict:** **APPROVED WITH CONDITIONS**

---

## Verdict

This is a small table done carefully. The transformation is two passthroughs, three derivations, one provenance column, 51 rows, closed-set reference data, and it is implemented cleanly. The chain of evidence — spec → physical model → transformer → 101 tests → 39 DQ rules → 39/39 PASS on a fresh post-rebuild run against the live warehouse → adversarial audit with its two correctable HIGH findings actually fixed — is the most coherent governance trail in the project to date. I would put my name on it, with the two narrow conditions stated below.

I re-ran the test suite (101/101 pass in 0.63s), re-queried the live `brightsmith.base.bea_rpp` table (51 rows, 11 columns, correct column order, `verification_status` distribution 8 `bea_official` / 43 `estimate`, inverse invariant holds at zero violations, multiplier range `[0.9033, 1.1507]`, single `data_year=2024`, FIPS-abbr bijection complete at 51), and re-verified the final DQ run artifact (`silver-base-bea-rpp-20260411T012113Z.json`, run_id `e8c3d354`, 39/39 pass, 0 failed, 0 errored, p0_passed=true). The pipeline gate shows all 19 upstream steps COMPLETED.

The conditions on this approval are both documentation anchors, not code changes. They exist to make sure the inherited open items are tracked by name rather than lost in commit history.

---

## Code Quality

### `src/silver/bea_rpp_transformer.py` — clean

- One responsibility: read Bronze, transform rows, promote via the shared idempotent pattern. No god function. The public surface is four derivation helpers + `transform_row` + `transform_rows` + `promote_bea_rpp`, each with a tight contract.
- Error handling is real: `_validate_state_fips` rejects `None`, non-2-digit, and out-of-set values with distinct error messages; `derive_purchasing_power_multiplier` separately handles `None`, zero, and `NaN`; `transform_row` fails loud on missing `geo_name`, `rpp_all_items`, and `load_date`. No bare excepts, no silent swallowing, no `assert`-as-runtime-check.
- The `EXPECTED_ROW_COUNT != len(bronze_rows)` branch logs a warning instead of raising — this is deliberate and right. A short Bronze snapshot is caught by the DQ row-count rule at run time; raising here would mask the real failure mode in pipeline runs against partial warehouses.
- `transform_rows` also has an in-Python uniqueness guard on `state_fips` before promote. Redundant with the promote dedup, but defensible — it gives a clearer error at the place the bug lives.
- Naming is precise. `derive_state_abbr`, `derive_census_region`, `derive_purchasing_power_multiplier`, `derive_verification_status` — each name says exactly what the function does. No `helper`, `utils`, `data`, `info`.
- The `promote_bea_rpp` entry point accepts explicit warehouse/catalog overrides for tests. Good. The manifest wrapper `transform(project_dir)` exists and is a two-line passthrough. Good.
- Module docstring reads like a specification, not a novel. Appropriate for a governance-critical file.

### `src/silver/_us_state_reference.py` — structural reference handled correctly

- The three static dicts (`FIPS_TO_USPS`, `FIPS_TO_CENSUS_REGION`, `BEA_VERIFIED_FIPS`) are the correct way to encode closed-set structural data that is a property of U.S. geography, not business-managed entity data. I agree with the spec's own rationalization of this exception.
- The import-time `_self_check()` is doing real work: it asserts exact lengths (51/51), cross-validates the two dict key sets against each other, and cross-validates both against `BeaRppIngestor.VALID_STATE_FIPS`. That last cross-check is the control that catches Silver-vs-Bronze drift and it runs whether or not tests do. Any renaming sweep on the Bronze ingestor will fail-fast on Silver import, not silently in production.
- The DC → South assignment is called out in a comment. Correct Census convention, correct documentation.
- `BEA_VERIFIED_FIPS` as a `frozenset` is the right container for an immutable membership check.

### Tests — 101 pass in 0.63s, mostly real, a few tautologies

- The eight byte-for-byte spot checks in `TestSpotChecks` for CA/HI/DC/NJ/AR/MS/IA/OK are the real correctness anchors. Each asserts `state_abbr`, `census_region`, `rpp_all_items`, `purchasing_power_multiplier` (±0.001), and `verification_status`. If any row goes wrong, these catch it immediately.
- `TestTransformRow` covers all the error paths individually (missing geo_fips, invalid format, unknown FIPS, missing geo_name, missing rpp, missing load_date). Real assertions against real exception types with matchers on the error messages.
- `TestIntegration::test_idempotent_second_run_zero_new` runs promote twice against a temp Iceberg warehouse and asserts second-run `promoted=0, skipped_dedup=51`. That is a real round-trip test of the dedup logic.
- `TestTransformRow::test_record_id_depends_only_on_state_fips` — mutates a non-grain field and asserts the grain ID is stable. That is the right test for a grain function.
- `TestStateReferenceSelfCheck::test_self_check_detects_length_drift` and `::test_self_check_detects_key_mismatch` — monkeypatches the dicts, asserts `_self_check()` raises. Real negative tests of the structural guard.
- **Adversarial audit MEDIUM-4 is partly valid.** `test_all_values_uppercase_2_letter` and `test_all_regions_are_valid_enum` iterate the same dicts they import and assert shape. They do catch some hallucination classes (e.g., Alabama → "Southeast"), but not the one that matters (e.g., Alabama → "West"). The 101-test number is inflated by a handful of these. The real correctness-anchoring test count is closer to the 8 spot checks + 8 verification-status parametrizations + the error-path coverage + the integration round trip. That is still enough for a closed-set 51-row reference table; I flag it because the "101 tests" claim overstates.
- Test minimum for Silver is 15. Actual is 101. Pass.

---

## Test Quality

Real, not theater, with the MEDIUM-4 caveat above. Assertions validate specific values and specific error messages. The 8-state spot-check suite is byte-for-byte. The integration test writes to a real Iceberg table and reads back to verify the 8/43 verification split. The idempotency test actually runs the promote function twice and asserts second-run = 0. The error-path tests use `pytest.raises(..., match=...)` with specific matchers, not bare `pytest.raises(Exception)`.

What I did NOT see: a test that promotes against the persistent `data/silver/iceberg_warehouse/` and asserts the same idempotency. Audit MEDIUM-1 called this out. I accept the deferral — the temp-warehouse test proves the code, and the DQ rule `rpp_all_items` passthrough integrity + the row-count rule would catch a runtime double-write, not silently mask it. Flagged as engineering backlog.

---

## Spec Compliance

Full matrix against the 9 Silver Transformations in the spec:

| # | Transformation | Implementation | Match? |
|---|---|---|---|
| 1 | state_fips normalization, 2-digit zero-padded, validate 51 present | `_validate_state_fips` regex `^\d{2}$` + set membership in `FIPS_TO_USPS` | Yes |
| 2 | state_name passthrough from geo_name | `transform_row` strips and passes through | Yes |
| 3 | state_abbr derivation from in-code 51-entry lookup | `derive_state_abbr` + `FIPS_TO_USPS` | Yes |
| 4 | census_region derivation, DC → South | `derive_census_region` + `FIPS_TO_CENSUS_REGION`, DC mapped to South | Yes |
| 5 | rpp_all_items passthrough | `transform_row` casts to float and passes through | Yes |
| 6 | purchasing_power_multiplier = 100.0 / rpp_all_items | `derive_purchasing_power_multiplier` | Yes |
| 7 | data_year passthrough, default 2024 | `transform_row` with fallback to `DEFAULT_DATA_YEAR` | Yes |
| 8 | verification_status derivation from 8-FIPS allow-list | `derive_verification_status` + `BEA_VERIFIED_FIPS = {'05','06','11','15','19','28','34','40'}` | Yes |
| 9 | source_load_date + ingested_at | Both present in the schema and populated in `transform_row` | Yes |

Schema matches the spec exactly: 11 columns, all required, correct types and ordering. Physical Iceberg table matches the schema (verified by direct pyiceberg scan). DQ rule set matches the spec's required coverage: row count = 51, grain uniqueness, state_abbr uppercase+USPS set, census region enum + coverage, purchasing_power range, inverse invariant, passthrough invariant, record_id uniqueness, data_year = 2024, count(DISTINCT data_year) = 1, verification_status enum, verification_status count = 8, allow-list FIPS membership. All present and all pass.

**Bronze staff-review Condition 6 — closed here.** The `verification_status` column exists with the exact 8-FIPS allow-list, the P0 count-of-8 rule is in place, and the spec's forward path (flip to count-of-51 when the live BEA API refresh lands) is a minor version bump, not a breaking change, which is the right contract posture. The contract `staff_review_conditions.condition_6_implemented` block cites the Bronze staff review by name.

**Bronze staff-review Condition 7 — formally carried forward.** The contract `staff_review_conditions.condition_7_carry_forward` block names the owner (`@primary-agent on gold-regional-price-parities and mcp-bea-rpp specs`), the requirement (Gold must propagate `verification_status`; MCP must return a `data_source` field per row with a strict-mode option), and leaves Silver correctly disavowing the implementation responsibility — because Silver is not the MCP tier. This is exactly the right disposition.

---

## Data Correctness Spot-Check

Queried the live `brightsmith.base.bea_rpp` table via the canonical catalog at `data/catalog/catalog.db`.

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|---|---|---|---|---|---|---|
| California (`06`) | rpp_all_items | 2024 (labeled) | 110.7 | 110.7 | Spec frozen value; BEA publication (primary-agent curated) | Exact |
| California (`06`) | purchasing_power_multiplier | 2024 | 0.9033 (→0.9034 @ 4dp) | 0.9034 (from spec table) | `100.0/110.7 = 0.903342…` | Exact within ±0.001 |
| California (`06`) | census_region | 2024 | West | West | U.S. Census Bureau four-region | Exact |
| California (`06`) | state_abbr | 2024 | CA | CA | USPS | Exact |
| Hawaii (`15`) | rpp_all_items | 2024 | 110.0 | 110.0 | Spec frozen value | Exact |
| DC (`11`) | census_region | 2024 | South | South | U.S. Census Bureau (DC-in-South convention) | Exact (quirk documented) |
| New Jersey (`34`) | purchasing_power_multiplier | 2024 | 0.9191 | 0.9191 | `100.0/108.8 = 0.919117…` | Exact |
| Arkansas (`05`) | purchasing_power_multiplier | 2024 | 1.1507 | 1.1507 | `100.0/86.9 = 1.15074…` | Exact |
| Iowa (`19`) + Oklahoma (`40`) | rpp_all_items | 2024 | 87.8, 87.8 | 87.8, 87.8 | Spec frozen value (legit tie) | Exact |
| Verification split | `bea_official`/`estimate` | 2024 | 8 / 43 | 8 / 43 | Spec + Condition 6 | Exact |
| Inverse invariant | `mult × rpp ≈ 100.0` | 2024 | 0 violations at tol 0.01 | Must hold for all 51 rows | SIL-BEA-021 | Exact |

**Caveat on reference values.** The 8 "BEA-verified" values are declared in the spec as primary-agent-curated from BEA publications, with the project-wide `partial_verification` quality tier explicitly labeling the 43 other rows as estimates. I am **not** independently cross-checking these 8 values against a fresh pull of the BEA SARPP API — that is the open item the live BEA API refresh is designed to close. What I **am** verifying is that the pipeline honestly surfaces the partial verification status on a per-row basis via `verification_status`, that the DQ rules pin the current state exactly, and that the spec's frozen 8 values round-trip byte-for-byte through the transformer. All three are confirmed.

This is the correct posture for a hackathon-tier project that pre-discloses its data provenance. If this were a production regulated workload, I would block on a live BEA API refresh. Here, the `verification_status` column plus the per-row propagation requirement in Condition 7 is a sufficient mitigation, and the SIL-BEA-023 DQ rule (`COUNT(*) WHERE verification_status='bea_official' = 8`) will flip to `= 51` as a contract minor version bump the moment the live refresh lands. Spec-local conditional verification handled correctly.

**No golden dataset file at `governance/golden-datasets/silver-base-bea-rpp-golden.json`.** The minimum test requirements table flags golden datasets as mandatory for Consumable and MCP zones, not Silver/Base. The 8 frozen spec spot-checks encoded in SIL-BEA-031..038 are the effective golden reference for this table. Accepted.

---

## Governance Artifacts

Spot-checked for boilerplate vs. real content. All files have real content:

- `governance/dq-rules/silver-base-bea-rpp.json` — 39 rules with real SQL, real thresholds, real rationale referencing the EDA and physical model. 36 P0, 3 P1. Categories: volume 1, completeness 10, uniqueness 3, validity 17, consistency 7, referential_integrity 1.
- `governance/dq-results/silver-base-bea-rpp-20260411T012113Z.json` — 39/39 pass, zero errored, p0_passed=true, run_id `e8c3d354` against the live post-rebuild warehouse.
- `governance/data-contracts/silver-base-bea-rpp.yaml` — DRAFT, `version: 1.0.0`, `record_count: 51`, `quality_tier: partial_verification`, all 11 columns with full `dq_rules` arrays that actually match the rule SQL (verified rule-by-rule), 8 CDEs, 0 PII, downstream_consumers listed, staff_review_conditions block present with both Condition 6 and Condition 7 anchors.
- `governance/data-dictionary.json` — 11 entries for `base.bea_rpp` at line 5932.
- `governance/business-glossary.json` — BT-103, BT-104, BT-105 added at lines 1330, 1343, 1356.
- `governance/models/silver-base-bea-rpp-{conceptual,logical,physical}.md` — all three exist, physical matches the live table.
- `governance/lineage/silver-base-bea-rpp-20260410.json` — column-level lineage.
- `governance/cde-tagging/silver-base-bea-rpp.md` — 8 CDEs tagged with rationale.
- `governance/pii-scans/silver-base-bea-rpp.md`, `governance/entity-resolution/silver-base-bea-rpp.md`, `governance/temporal/silver-base-bea-rpp.md` — skip recommendations with real reasoning.
- `governance/chaos-reports/silver-base-bea-rpp-chaos.md` — 28 probes + 5 cycles, 2 gaps found and remediated (SIL-BEA-018 rewritten, SIL-BEA-039 added). Has the 38→39 rule-count drift flagged in the audit as MEDIUM-3 — minor, I am not blocking on it.
- `governance/adversarial-audits/silver-base-bea-rpp.md` — three HIGH findings, two fixed (HIGH-2, HIGH-3), one deferred (HIGH-1) per the audit's own recommendation #3.

No boilerplate detected. The rationale fields in the DQ rules cite the EDA and physical model by name. The CDE tagging rationale is specific to each column's downstream role.

---

## Issues

| # | Severity | File | Issue | Required Fix |
|---|---|---|---|---|
| — | — | — | None blocking. | — |

---

## Conditions on Approval

Neither of these blocks code or contracts. Both are documentation anchors that must live as named tracked items so the inherited debt does not silently disappear on a commit-history sweep.

### Condition A — HIGH-1 must be filed as a brightsmith framework ticket before this spec is marked COMPLETE

The adversarial audit HIGH-1 finding is that `evaluation_mode: production_only` and `chaos_exclude: true` on SIL-BEA-018 are decorative metadata — no code in `brightsmith/src` or project `src/` reads either field. Enforcement lives in a hard-coded `SHADOW_EXCLUDED_RULE_IDS` set inside `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py`. This works today. It silently breaks the moment SIL-BEA-018 is renumbered or a second cross-zone rule is added.

The audit's own recommendation #3 says to "pick a lane" — either have the brightsmith `dq_runner` and chaos harness read the metadata, or remove the metadata and document that the carve-out is spec-local. Both are correct; both are out of scope for this Silver spec. The condition is that a brightsmith framework ticket must be filed and linked in the project backlog with the exact text "`dq_runner` and chaos harness must honor `evaluation_mode: production_only` and `chaos_exclude: true` fields natively" and the adversarial audit file path as evidence. No code change is required in this project to clear the condition. Owner: `@staff-engineer` at the brightsmith framework level.

### Condition B — Bronze Condition 7 must be enforced at Gold and MCP pre-review

The Silver contract's `staff_review_conditions.condition_7_carry_forward` block names the owners (`@primary-agent on gold-regional-price-parities and mcp-bea-rpp specs`) and the requirement (Gold must propagate `verification_status` as a first-class column; MCP must return a `data_source` field per row with a strict-mode option that refuses to return `estimate` rows). This is the correct disposition at Silver.

The condition is that `@governance-reviewer` must enforce both at the Gold and MCP pre-review gates — the Gold pre-review must verify that `verification_status` is preserved as a first-class column on every Gold row, and the MCP pre-review must verify that the tool response includes a `data_source` field that defaults to strict mode. If either pre-review passes without verifying its half of Condition 7, the staff-engineer Gold/MCP sign-off is automatically blocked back to CHANGES REQUESTED. This condition is a governance policy anchor, not a code change, and it clears when the Gold and MCP specs reach their staff sign-offs.

---

## Deferred Items (Non-Blocking)

Recorded for backlog tracking:

1. **HIGH-1 deferral** — see Condition A. Brightsmith framework ticket.
2. **MEDIUM-1** — Idempotency test against persistent warehouse, not just temp catalog. Engineering backlog.
3. **MEDIUM-2** — External FIPS-to-USPS and FIPS-to-Census-region anchor (committed NIST/Census CSV under `governance/reference-data/` with an import-time cross-check). Cheap; would close the hallucination risk on the 43 non-spot-checked states. Engineering backlog.
4. **MEDIUM-3** — Chaos report footnote: the post-remediation rule count is 39, not 38. One-line fix. Engineering backlog.
5. **MEDIUM-4** — Test-count inflation from tautology tests (`test_all_values_uppercase_2_letter`, `test_all_regions_are_valid_enum`). The real anchor count is ~30, not 101. Not a correctness issue; a reporting honesty issue. Engineering backlog.
6. **LOW-1** — Contract `status: draft` can flip to `active` at staff sign-off time. See flip instruction below.
7. **LOW-2** — `scripts/promote_bea_rpp_silver.py::main` does not self-verify second-run idempotency. Cheap two-line fix. Engineering backlog.
8. **Framework ticket from Bronze era** — `scripts/rebuild_all.py` still carries `project_name="futureproof-data"` override for non-BEA tables. The BEA path is safely isolated via subprocess in this Silver fix, so this Silver spec does not regress the issue, but the broader project remediation remains open from Bronze. Framework backlog.
9. **Live BEA API path never exercised end-to-end** — both Bronze and Silver use the CSV fallback. Closes when the live refresh lands. At that point SIL-BEA-023 flips from `= 8` to `= 51` as a minor version bump.
10. **CSV cache integrity** — no sha256 check on the BEA cache CSV. Pre-existing Bronze issue, not re-opened here. Engineering backlog.

None of the above blocks this Silver spec. All are tracked in writing.

---

## What's Acceptable

Fine. The transformer is clean, the self-check is real, the 8 spot checks are byte-for-byte, the DQ rule suite is well-shaped and covers what matters, the idempotency test actually runs the promote twice, the chaos cycle found its gaps and closed them, the adversarial audit found three real issues and two of them are materially fixed (not papered over), and the governance artifacts are complete with real content. The Bronze Condition 6 obligation is discharged exactly as the Bronze staff review required. The Condition 7 carry-forward is formally anchored in the Silver contract with named owners. The pipeline gate shows 19 of 20 steps complete and this is the 20th.

The partial_verification tier is pre-disclosed at every surface of this pipeline — contract, data dictionary, CDE tagging, the `verification_status` column itself, and the DQ rule that pins the current 8-row count. That honesty is the right answer for a hackathon-tier project and it is the reason I am approving this with conditions instead of rejecting pending a live BEA refresh.

---

## Verdict

**APPROVED WITH CONDITIONS.**

Conditions are both documentation anchors (Condition A — file the brightsmith framework ticket; Condition B — enforce Condition 7 at Gold and MCP pre-review). Neither blocks the contract flip or the spec completion.

The data contract at `governance/data-contracts/silver-base-bea-rpp.yaml` may flip `status: draft` → `status: active` upon this sign-off. Spec `silver-base-bea-rpp` is cleared for COMPLETE status in the pipeline gate and the project spec registry.

---

## Artifacts Referenced

| Path | Role |
|---|---|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/silver-base-bea-rpp.md` | Spec under review |
| `/Users/jcernauske/code/bright/futureproof-data/src/silver/bea_rpp_transformer.py` | Silver transformer (reviewed line by line) |
| `/Users/jcernauske/code/bright/futureproof-data/src/silver/_us_state_reference.py` | Structural reference module with import-time self-check |
| `/Users/jcernauske/code/bright/futureproof-data/tests/silver/test_bea_rpp_transformer.py` | 101 tests, 101 pass (verified by re-run) |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/promote_bea_rpp_silver.py` | Silver promote runner (no project_name drift) |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/rebuild_all.py` | Fresh-clone reproducibility (HIGH-3 fix verified at lines 151, 257, 336, 357) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/silver-base-bea-rpp-pre-review.md` | Pre-implementation review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/silver-base-bea-rpp-post-review.md` | Post-implementation review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/raw-ingest-bea-rpp-staff-review.md` | Source of Conditions 6 and 7 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/adversarial-audits/silver-base-bea-rpp.md` | HIGH-1 deferred, HIGH-2 and HIGH-3 fixed |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/silver-base-bea-rpp.json` | 39 rules (SIL-BEA-001..039), 36 P0 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-results/silver-base-bea-rpp-20260411T012113Z.json` | Latest run, run_id `e8c3d354`, 39/39 PASS, p0_passed=true |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/silver-base-bea-rpp.yaml` | DRAFT contract — may flip to ACTIVE on this sign-off |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-dictionary.json` | 11 columns at line 5932 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` | BT-103/104/105 at lines 1330/1343/1356 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-bea-rpp-conceptual.md` | Conceptual model |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-bea-rpp-logical.md` | Logical model |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-bea-rpp-physical.md` | Physical model (matches live table) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/silver-base-bea-rpp-20260410.json` | Column-level OpenLineage |
| `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-reports/silver-base-bea-rpp-chaos.md` | 28 probes + 5 cycles; 2 gaps remediated |
| `/Users/jcernauske/code/bright/futureproof-data/governance/cde-tagging/silver-base-bea-rpp.md` | 8 CDEs, 0 PII |
| `/Users/jcernauske/code/bright/futureproof-data/data/catalog/catalog.db` | Canonical Silver catalog — single `(brightsmith, base, bea_rpp)` row |

---

*— End of Staff Engineer Review —*
