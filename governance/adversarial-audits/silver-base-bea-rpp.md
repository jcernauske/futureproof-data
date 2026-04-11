# Adversarial Audit — silver-base-bea-rpp

- **Spec:** `docs/specs/silver-base-bea-rpp.md`
- **Target table:** `base.bea_rpp` (11 columns, 51 rows — 50 states + DC)
- **Audit date:** 2026-04-10
- **Auditor:** @adversarial-auditor
- **Latest DQ run under review:** `governance/dq-results/silver-base-bea-rpp-20260411T003356Z.json` (run_id `6667c311`, 39/39 PASS, 0 errored)
- **Chaos cycle under review:** `governance/chaos-reports/silver-base-bea-rpp-chaos.md` (5 cycles + 8 extra probes; 18/18 main-pack caught; SIL-BEA-018 + SIL-BEA-039 remediated)
- **Standard applied:** "Would a regulator accept this explanation?"

This audit is the skeptical read-through of the Silver layer after the chaos cycle closed its two gaps. It exists to find problems chaos cannot find: hallucinated values, documentation drift, theater dressed up as control, and hidden single points of failure.

---

## Risk Register

### HIGH-1 — `chaos_exclude` / `evaluation_mode` metadata is documentation-only; no framework reads it

**Severity:** HIGH
**Category:** Governance theater

**Finding.** `SIL-BEA-018` carries the markers `evaluation_mode: production_only` and `chaos_exclude: true`. These are plain JSON fields. A full-tree grep of `src/` (project) and `src/` (brightsmith) shows **zero** code paths that read either field. The field appears only in: the rule JSON itself, a dq-scorecard write-up, a dq-rule-writer audit trail, and the chaos runner's comment block.

The carve-out is enforced instead by a hard-coded Python set inside `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py`:

```python
SHADOW_EXCLUDED_RULE_IDS = frozenset({"SIL-BEA-018"})
```

**Why this matters.**
1. If anyone reads the rule JSON and assumes the framework honors `chaos_exclude`, they are wrong. The two fields are decorative from the runner's perspective.
2. The actual enforcement is a **spec-local opt-in list in a single script**. There is no integration with the brightsmith chaos runner or dq runner.
3. If SIL-BEA-018 is ever renumbered (e.g., during a renumbering sweep) or if a second cross-zone rule is added (e.g., a silver<->bronze `data_year` passthrough rule), the hard-coded list silently goes stale. The next chaos run would error again on the new cross-zone rule, and no metadata check would catch it.
4. The chaos runner does not — and by design cannot — read the rules JSON (information barrier). This makes the stale-list risk structural, not fixable by convention.

**Evidence references.**
- `governance/dq-rules/silver-base-bea-rpp.json` rule SIL-BEA-018 (fields `evaluation_mode`, `chaos_exclude`, `chaos_exclude_reason`)
- `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py` lines 80–82 (`SHADOW_EXCLUDED_RULE_IDS`)
- `grep -r "evaluation_mode\|chaos_exclude\|production_only" /Users/jcernauske/code/bright/brightsmith/src` returned zero matches
- Same grep across futureproof-data project code returned zero matches (only audit trail / docs / the runner hit)

### HIGH-2 — Per-column `dq_rules` mapping is contiguous-slice hallucination; 7 rules are orphaned from any column

**Severity:** HIGH
**Category:** Documentation drift / verification theater

**Finding.** The data contract (`governance/data-contracts/silver-base-bea-rpp.yaml`) and the data dictionary (`governance/data-dictionary.json`, table `base.bea_rpp`) both claim per-column `dq_rules` arrays. The doc-generator admitted in its audit trail (judgment call #7) that these arrays are "plausible contiguous slices" aligned to the order columns appear in the spec, not to the actual rule SQL. I checked. The slices are wrong in 9 of 11 columns and 7 rules are orphaned:

| Column | Contract claim | Rules that actually reference the column (per SQL grep) | Verdict |
|---|---|---|---|
| record_id | 001, 002 | 025, 026 | wrong |
| state_fips | 003, 004, 005, 006 | 002, 003, 004, 006, 011, 018, 024, 039 | partially overlapping, but 005 doesn't touch state_fips at all |
| state_name | 007, 008 | 005, 006 | wrong |
| state_abbr | 009, 010, 011, 012, 013 | 007, 008, 009, 010, 011 | shifted by 2 |
| census_region | 014, 015, 016 | 012, 013, 014, 015 | shifted by 2 |
| rpp_all_items | 017, 018, 019, 020 | 016, 017, 018, 021 | shifted by 1 plus wrong |
| purchasing_power_multiplier | 021, 022, 023, 024 | 019, 020, 021 | shifted; 022–024 are verification_status rules |
| verification_status | 025, 026, 027 | 022, 023, 024 | wrong; 025–026 are record_id, 027 is data_year |
| data_year | 028, 029 | 027, 028 | shifted |
| source_load_date | 030, 031 | 029 | 031 is the CA spot-check rule, not source_load_date |
| ingested_at | 032 | 030 | 032 is the HI spot-check rule, not ingested_at |

**Orphaned rules** (referenced nowhere in either artifact's per-column mapping): **SIL-BEA-033 (DC spot check), 034 (NJ), 035 (AR), 036 (MS), 037 (IA), 038 (OK), 039 (canonical state_fips set)**. That is the entire non-CA/HI spot-check suite plus the brand-new Gap-2 remediation rule.

**Why this matters.** A regulator asked to produce column-level DQ coverage for `verification_status` would be pointed at rules `025/026/027`, and they would not be testing verification_status. The rules file is the ground truth and contains all 39 rules, but the column-level coverage claims in the contract and dictionary are wrong. The contract is `status: draft` pending staff sign-off — if a human staff engineer relies on the per-column mapping to spot-check coverage (exactly what the mapping exists for), they'll sign off on a mapping that does not describe the actual rule suite.

The doc-generator's audit trail does say this is correctable in a minor patch and anchors rule coverage on the whole rules JSON. Fair. But the artifacts that downstream humans and auditors read **say something false**, and they're presented with the same authority as the rules file. That is textbook documentation theater.

**Evidence references.**
- `governance/data-contracts/silver-base-bea-rpp.yaml` columns block
- `governance/data-dictionary.json` → `tables/base.bea_rpp` columns
- `governance/audit-trail/2026-04-10-doc-generator-silver-base-bea-rpp.md` judgment call #7 (self-admission)
- SQL column grep across all 39 rules in `governance/dq-rules/silver-base-bea-rpp.json`

### HIGH-3 — `rebuild_all.py` does not reproduce `base.bea_rpp`; no fresh-clone reproducibility

**Severity:** HIGH
**Category:** Coverage gap / reproducibility

**Finding.** `scripts/rebuild_all.py` is described in commit `66002ca` as "full pipeline rebuild script for fresh-clone recovery." It enumerates raw ingests and silver transforms for College Scorecard, BLS OOH, O*NET, CIP-SOC crosswalk, and Karpathy AI exposure. It does **not** include:

- Bronze ingest of BEA RPP (no `ingest_bea_rpp` function, no reference to `raw.bea_rpp_ingestor`)
- Silver promotion of BEA RPP (no reference to `silver.bea_rpp_transformer` or `scripts/promote_bea_rpp_silver.py`)

Grep of `scripts/rebuild_all.py` for `bea_rpp|promote_bea_rpp_silver|bea-rpp` returns zero matches.

**Why this matters.** The reproducibility claim is that a reviewer or regulator should be able to clone the repo and re-produce the pipeline. As of today, re-running `rebuild_all.py` on a fresh clone produces every Silver and Gold table **except** `base.bea_rpp`. Any Gold consumer that depends on BEA RPP (the Gold regional-price-parities spec and the MCP get_regional_price_parity tool are both declared as downstream consumers in the data contract) would either fail or silently run against stale/missing data.

The primary-agent's one-off runner (`scripts/promote_bea_rpp_silver.py`) exists, is clean, and avoids the Bronze HIGH-1 project_name drift. The gap is that `rebuild_all.py` does not call it.

**Evidence references.**
- `scripts/rebuild_all.py` (full file, zero bea_rpp hits)
- `scripts/promote_bea_rpp_silver.py` (exists and is clean — this is the correct artifact to wire in)

### MEDIUM-1 — Idempotency is tested against a temp catalog, not the persistent warehouse

**Severity:** MEDIUM
**Category:** Test coverage gap

**Finding.** `tests/silver/test_bea_rpp_transformer.py::TestIntegration::test_idempotent_second_run_zero_new` creates a fresh temp Iceberg warehouse, seeds Bronze, and verifies that the second promote produces `promoted=0, skipped_dedup=51`. That proves the promote pattern itself is correct. It does **not** prove the same holds when run against the persistent `data/silver/iceberg_warehouse/` that the real pipeline uses.

The claim "first run writes 51, second run writes 0" on the persistent warehouse comes from the primary-agent's run log — not a test. If the project's shared catalog ever ends up with schema drift, stale snapshot metadata, or a partial write, the temp-catalog unit test will continue to pass while production silently double-writes.

**Why this matters.** Idempotency is the entire point of the promote pattern. A regression would be catastrophic and silent (duplicate rows that pass the row-count rule because the dedup grain masks them). The control that prevents this is `compute_grain_id(['state_fips'], prefix='rpp')` + the promote pattern's dedup-on-id step. The test proves the code is correct; it does not prove the runtime environment never undermines it.

**Evidence references.**
- `tests/silver/test_bea_rpp_transformer.py::TestIntegration::test_idempotent_second_run_zero_new`
- `scripts/promote_bea_rpp_silver.py::main` (asserts row count = 51 after the run but does not assert second-run = 0)

### MEDIUM-2 — USPS abbreviations and Census regions are never cross-checked against an external authoritative source

**Severity:** MEDIUM
**Category:** AI hallucination risk / missing external anchor

**Finding.** The three lookups in `src/silver/_us_state_reference.py` (`FIPS_TO_USPS`, `FIPS_TO_CENSUS_REGION`, `BEA_VERIFIED_FIPS`) are the single point of truth for three derived columns. The self-check at import time asserts:

1. both dicts have exactly 51 entries
2. key sets match
3. the key set matches `BeaRppIngestor.VALID_STATE_FIPS`
4. `BEA_VERIFIED_FIPS` is a subset of that key set

This is good structural hygiene — it catches drift between Silver and Bronze. What it does **not** do is check any of the actual `FIPS → USPS` or `FIPS → Census region` values against an external authoritative source. The values themselves were produced by an AI agent. There is no CSV from NIST FIPS 5-2, no Census Bureau PDF reference, no BLS-maintained crosswalk, no checksum of a downloaded canonical file.

The tests in `TestDeriveStateAbbr` / `TestDeriveCensusRegion` assert on individual spot-check values (CA→West, NJ→Northeast, DC→South, etc.), which are correct. But the broad assertions (`test_all_values_uppercase_2_letter`, `test_all_regions_are_valid_enum`, `test_census_region_counts`) validate that the lookup satisfies its own shape — they import `FIPS_TO_USPS` / `FIPS_TO_CENSUS_REGION` from the same module they test. That is a tautology: if I swap Wyoming and Nevada's abbreviations in the dict, those broad tests still pass.

The individual spot checks in `TestDeriveStateAbbr` cover CA, DC, WY — only 3 of 51. `TestDeriveCensusRegion` parametrizes 8 (the BEA-verified states). That means 43 of 51 USPS abbreviations and 43 of 51 Census region assignments are validated **only by the self-check shape rules plus whatever spot checks happen to exist**.

**Why this matters.** If the AI hallucinated Rhode Island → `RL` instead of `RI`, or moved Kentucky from South to Midwest, nothing in the test suite, the self-check, or the DQ rules would catch it. The row count stays 51. The key set still matches Bronze. The enum still has four values. The spot checks for the 8 BEA-verified states and CA/DC/WY still pass. The error ships.

**Recommended fix.** Add a one-shot verification test that downloads (or caches) an authoritative file (NIST FIPS 5-2 or Census Bureau state-codes CSV) and asserts every key/value matches. Alternatively, commit the authoritative CSV at `governance/reference-data/` and cross-check the in-code constants against it at import time.

**Evidence references.**
- `src/silver/_us_state_reference.py::_self_check` (shape only, no external anchor)
- `tests/silver/test_bea_rpp_transformer.py::TestStateReferenceSelfCheck` (shape only)
- `tests/silver/test_bea_rpp_transformer.py::TestDeriveStateAbbr` (3 spot checks out of 51)

### MEDIUM-3 — Spec compliance text in the chaos report claims "38 rules", but the rules file has 39

**Severity:** MEDIUM
**Category:** Stale documentation

**Finding.** The chaos report header line 6 reads:

> **Rules file:** `governance/dq-rules/silver-base-bea-rpp.json` (38 rules — NOT inspected)

The rules file actually contains 39 rules (SIL-BEA-001 through SIL-BEA-039). The 39th is the post-chaos remediation rule (canonical state_fips set, closing Gap 2 / probe E6). The chaos report was written before SIL-BEA-039 landed, so the "38" is the count the chaos runner saw. The chaos report is not wrong for the run it documents — but the count discrepancy is the sort of thing a regulator would trip on during a consistency check (contract says 39, chaos report says 38, no one's lying, but the narrative is broken without explanation).

**Why this matters.** Minor in isolation. Important as part of the general pattern that the project has multiple independently-drifting artifacts describing the same rule suite.

**Recommended fix.** Add a one-line footnote to the chaos report: "Post-remediation rule count is 39; SIL-BEA-039 was added after this run to close Gap 2."

### MEDIUM-4 — Test suite has structural tautologies that reduce coverage claims

**Severity:** MEDIUM
**Category:** Test theater

**Finding.** The project reports "101 tests" for an 11-column static table. That's a large number, and some of those tests assert against the exact data they import, which is a tautology.

Examples:
- `test_all_values_uppercase_2_letter` — iterates `FIPS_TO_USPS.values()` and asserts `len(abbr) == 2 and abbr.isupper()`. This just asserts that the dict the test imports satisfies its own shape. If the dict is wrong, this test still passes.
- `test_all_regions_are_valid_enum` — iterates `FIPS_TO_CENSUS_REGION.values()` and asserts membership in `{"Northeast","Midwest","South","West"}`. Same issue — if the AI put Alabama in "Southeast" (wrong), this test would fail, so it does catch one hallucination class; but if the AI put Alabama in "West" (also wrong), this test would pass.
- `test_census_region_counts` — asserts counts NE=9 MW=12 S=17 W=13. That's a strong shape invariant (total of 51 and a known canonical distribution), but it's still a shape assertion, not a per-value assertion. Swapping two states between any two regions leaves the counts unchanged.
- `test_fips_to_usps_has_51_entries`, `test_fips_to_census_region_has_51_entries`, `test_lookup_key_sets_match` — all structurally identical to `_self_check()`, which runs at import anyway. These tests exist to assert the self-check hasn't been broken, which is fine, but they don't add correctness coverage.

Many of the 101 tests are solid: the 8 BEA-verified spot checks are byte-for-byte assertions against the spec's frozen values, the `transform_row` tests cover all the error paths, the integration tests exercise the full promote round trip. The point of this finding is not that the test suite is bad — it's that the "101 tests" number overstates the actual correctness anchor count. The real external anchors are the 8 spot-check values (which are all correct per the spec) and the individual parametrized values in `TestDeriveStateAbbr` / `TestDeriveCensusRegion`.

**Why this matters.** A test count is used as evidence of thoroughness. For this table, the correctness-relevant anchors are much fewer than 101.

**Evidence references.**
- `tests/silver/test_bea_rpp_transformer.py::TestStateReferenceSelfCheck` (shape tests)
- `tests/silver/test_bea_rpp_transformer.py::TestDeriveStateAbbr::test_all_values_uppercase_2_letter`
- `tests/silver/test_bea_rpp_transformer.py::TestDeriveCensusRegion::test_all_regions_are_valid_enum`

### LOW-1 — Data contract status is `draft` but the DQ scorecard already reports PASS

**Severity:** LOW
**Category:** Process ordering

**Finding.** `governance/data-contracts/silver-base-bea-rpp.yaml` shows `status: draft`. The dq-engineer run at `governance/dq-results/silver-base-bea-rpp-20260411T003356Z.json` shows 39/39 PASS. The sequence is correct (contract is drafted, approvals are pending staff sign-off, DQ run was successful). Flagged only to note that the contract should flip to `active` only after staff sign-off AND after the HIGH-2 per-column dq_rules fix lands — otherwise the active contract ships with wrong per-column mappings.

### LOW-2 — Promote runner does not verify second-run idempotency in the success condition

**Severity:** LOW
**Category:** Runtime assertion gap

**Finding.** `scripts/promote_bea_rpp_silver.py::main` runs the promote, then asserts `len(rows) == 51 and verif == {"bea_official": 8, "estimate": 43}`. It does not run the promote a second time to check that the second run is a no-op. Since the script is advertised as "Re-running the script produces 0 new rows" in its module docstring, that claim should be self-testing — the runner could do a second `promote_bea_rpp()` call, assert `result["promoted"] == 0 and result["skipped_dedup"] == 51`, and only then exit 0. This is cheap and would close MEDIUM-1's blind spot at runtime.

---

## Evidence Demands — What would satisfy me

| # | Demand |
|---|---|
| 1 | A linter or validator (human or code) that reads the per-column `dq_rules` arrays in the contract + dictionary, greps each rule's SQL for column references, and fails if they don't match. Run it in CI. |
| 2 | Read `evaluation_mode: production_only` / `chaos_exclude: true` from the rules JSON inside brightsmith's dq_runner and chaos harness, OR remove the fields from the rules JSON entirely and document that the carve-out is spec-local. One or the other — not both. |
| 3 | `rebuild_all.py` imports and runs the BEA RPP Bronze ingest and Silver promotion. Fresh-clone verification (preferably in CI) that rebuilds the entire project from empty `data/` and runs all DQ rules. |
| 4 | A committed authoritative state-reference CSV (e.g., NIST FIPS 5-2 export) and a test that cross-checks every entry in `FIPS_TO_USPS` and `FIPS_TO_CENSUS_REGION` against it. |
| 5 | An end-to-end integration test (not a unit test) that runs `promote_bea_rpp_silver.py` twice against the actual persistent warehouse, clears snapshot state between the two runs only if explicitly requested, and asserts second-run = 0 promoted. |
| 6 | The chaos report updated (or superseded) with a post-remediation count of 39 rules and an explicit note that SIL-BEA-039 was added after the run. |

---

## Control Assessment

| Risk | Existing controls | Grade |
|---|---|---|
| HIGH-1 (metadata-only carve-out) | Hard-coded `SHADOW_EXCLUDED_RULE_IDS` in the spec-local chaos runner | **Weak** — works today, drifts silently on any renumber or new cross-zone rule. Metadata is decorative. |
| HIGH-2 (per-column dq_rules slices) | None — doc-generator self-admitted the issue but did not fix it | **Missing** |
| HIGH-3 (rebuild_all.py gap) | A one-off runner script exists at `scripts/promote_bea_rpp_silver.py` | **Weak** — the runner is good, but it is not wired into the reproducibility path |
| MEDIUM-1 (idempotency test coverage) | Temp-catalog unit test + primary-agent run log | **Adequate** — proves correctness but not persistence |
| MEDIUM-2 (no external anchor on state reference) | Import-time self-check + 8-state spot checks + partial parametrized tests | **Weak** — every test asserts against the same dict it imports, except the 8-state spot checks |
| MEDIUM-3 (chaos report says 38 rules) | None | **Missing** — minor but visible inconsistency |
| MEDIUM-4 (test tautologies) | 8 byte-for-byte spot checks + 51-row integration round trip | **Adequate** — real correctness anchors exist; the test count just overstates |
| LOW-1 (draft contract) | Status marker + approval workflow | **Strong** — correctly in draft pending sign-off |
| LOW-2 (runner does not self-verify idempotency) | Unit test only | **Adequate** — cheap to fix |

---

## Recommendations (ordered)

1. **Fix HIGH-2 before staff sign-off.** Re-derive every column's `dq_rules` array from the SQL of each rule (programmatically, not by hand). Update `governance/data-contracts/silver-base-bea-rpp.yaml` and `governance/data-dictionary.json` in a single patch. Attach SIL-BEA-033 through SIL-BEA-039 to the correct columns (spot checks to state_fips + the state's three derived columns; SIL-BEA-039 to state_fips). Ship a one-line CI validator that will fail the next time this drifts.
2. **Fix HIGH-3.** Add `ingest_bea_rpp` and `transform_silver_bea_rpp` functions to `scripts/rebuild_all.py`. Add a fresh-clone smoke test in CI.
3. **Pick a lane on HIGH-1.** Either make the brightsmith dq_runner read `evaluation_mode: production_only` (and the chaos runner read `chaos_exclude: true`) directly from the rules JSON, or delete the two fields from the rules JSON and document that the carve-out lives in the spec-local runner's hard-coded set. Mixing both is a trap.
4. **Close MEDIUM-2.** Commit an authoritative state-reference CSV under `governance/reference-data/` and add a test that cross-checks `FIPS_TO_USPS` and `FIPS_TO_CENSUS_REGION` against it. Cheap. Catches the exact class of hallucination the current tests cannot.
5. **Close LOW-2.** Have `scripts/promote_bea_rpp_silver.py::main` run the promote twice and assert second-run = 0 promoted before exit 0.
6. **Patch the chaos report** with a post-remediation note on the 38→39 rule count.

---

## Verdict

**Do not flip the contract to `active` yet.** HIGH-2 is a real documentation integrity defect — the contract and the data dictionary describe a per-column DQ coverage that does not match the actual rule SQL, and the entire BEA-verified spot-check suite for HI/DC/NJ/AR/MS/IA/OK plus the brand-new canonical-set rule are unattached to any column. That is not a minor cosmetic issue; that is the artifact a staff engineer reads when asked "show me coverage for `verification_status`," and it will point at the wrong three rules. A regulator would fail this.

**The substance is solid.** The transformer is clean, the self-check module cross-validates against the Bronze ingestor at import time, the eight spot checks are byte-for-byte-correct against the spec, 39/39 DQ rules pass in production, and the chaos cycle is honest about its gaps and remediated both of them. The carve-out for SIL-BEA-018 in chaos mode is conceptually correct — cross-zone rules genuinely cannot run against a shadow Silver table without a shadow Bronze, and the chaos runner honors it. The lineage file is detailed, the semantic models exist, and the runner avoids the Bronze HIGH-1 project_name drift.

**But the governance surface around that substance has three real drift problems:**
1. Metadata that looks enforcing but is decorative (HIGH-1)
2. Per-column DQ mappings that are hallucinated contiguous slices (HIGH-2)
3. A reproducibility script that doesn't reproduce this table (HIGH-3)

All three are cheap to fix. None require a redesign. The primary-agent and doc-generator did good work; the HIGH-2 and HIGH-3 findings exist because nobody closed the last mile between "the rules work" and "the documents about the rules tell the truth."

**On the meta-question — can AI agents build data pipelines trustworthy for regulated industries?** For this table, with the three HIGH findings open, the answer is **not yet, but close**. The correctness chain (transformer → 39 DQ rules → 39 PASS → chaos gaps found and remediated) is real and defensible. What isn't yet defensible is the documentation chain that a human regulator would walk through to audit it. The AI can build the pipeline. What the AI has not yet built is the *certainty that the documents describing the pipeline describe it accurately*. HIGH-2 is the clearest example: the doc-generator knew its output was possibly wrong, said so in its audit trail, and shipped it anyway. A human signed off on that. This is exactly the hallucination-slipping-past-approval failure mode the audit process is supposed to catch.

The fix to all three HIGH findings is a morning of work. After that, this Silver spec is publishable.

*— End of audit —*
