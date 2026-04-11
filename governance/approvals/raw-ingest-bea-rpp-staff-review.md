# Staff Engineer Review: raw-ingest-bea-rpp

**Review Type:** Final (Bronze zone only)
**Reviewer:** @staff-engineer
**Date:** 2026-04-10
**Zone:** Bronze (Raw)
**Status:** APPROVED-WITH-CONDITIONS

---

## Scope of this review

This review covers **only the Bronze zone** of the `raw-ingest-bea-rpp` spec. The spec describes Bronze → Silver → Gold → MCP, but Silver/Gold/MCP have not been implemented yet. Bronze sign-off here unblocks Silver. It does NOT authorize the data contract to transition from `DRAFT` to `ACTIVE`, and it does NOT authorize a refresh of the underlying CSV load until the named conditions below are met.

The adversarial auditor issued `CONDITIONAL PROCEED` with 4 HIGH / 3 MEDIUM / 2 LOW / 2 NOTE findings. A remediation pass closed HIGH-1 (on the bea_rpp path, not at framework root-cause level), HIGH-2, and HIGH-3 (at the contract level). The governance reviewer issued `APPROVED-WITH-CONDITIONS` and forwarded four specific rulings to me. This document is those rulings.

---

## Verdict

Fine. Bronze ingest is in the state it needs to be in for Silver to proceed: 51 rows, correct schema, all 8 spec-verified values match to the cent, single catalog row under the canonical `brightsmith` namespace, 19/19 DQ rules green with P0 clean, fresh post-remediation run, 12/12 chaos scenarios caught, no PII, no API key leakage, comprehensive test suite (40 tests — 4x the minimum). The agents earned this approval; they didn't get it for free.

Four things keep this from being a clean APPROVED:

1. **The framework drift that caused HIGH-1 is not fixed.** It was papered over for this table. `scripts/rebuild_all.py` line 26 still says `project_name="futureproof-data"` while `dq_runner` uses `"brightsmith"`. I independently verified the catalog and there is still a stray `futureproof-data|governance|lineage_events` row sitting there, proving the drift is real and has already bitten once. If anyone runs `rebuild_all.py` before this is fixed, every table it touches re-registers under the wrong namespace and dq_runner silently reads an older snapshot.

2. **Only 2 of 8 spec-verified values are enforced by DQ rules** (CA, AR). HI, DC, NJ, MS, IA, OK are free spot-checks that nobody added. RAW-BEA-017 (mean window) was derived from a dataset where 43/51 rows are primary-agent estimates, not BEA values, so the window is load-bearing on numbers that nobody has verified.

3. **The BEA API path has never been exercised end-to-end.** Every row in the persisted table came from the CSV cache. `TestLiveApi` exists but is gated on `@pytest.mark.network` and has no audit-trail evidence of a successful run. The quality tier disclosure makes this honest, but "honest about being half-verified" is not the same as "verified."

4. **The data contract file is internally inconsistent.** Line 5 comment says `Status: DRAFT`, line 15 YAML field says `status: ACTIVE`. The governance reviewer and I both expect DRAFT. Whichever tool reads the YAML field will read ACTIVE and treat it as a production contract. This is a real defect, not a cosmetic one.

None of those is severe enough on its own to block Bronze sign-off — the present state of the table is correct, the consumer-facing governance artifacts are consistent, and Silver can be built against what's here without risk. But every one of them is a forward risk for the next refresh, and one of them (the contract status field) is a present-state misrepresentation. Hence CONDITIONS, not clean APPROVED.

Would I put my name on this? Yes, with the conditions below checked off before a refresh and with condition #4 fixed immediately.

---

## Code Quality

### `src/raw/bea_rpp_ingestor.py` — acceptable

Read the whole file. No god functions, no swallowed exceptions, parsers are strict and fail loudly on schema drift before falling back. The API-vs-CSV fallback is honest about what it did and stamps `source_method` on every row so auditors can tell the difference. Secrets hygiene is real — `get_source_url()` returns a redacted URL and this was independently verified against the persisted table (every row has `UserID=REDACTED`).

What I'd flag but am not blocking on:

- **`_prefetched` stateful hack in `ingest()` (LOW-1 accepted).** The override runs `fetch()` eagerly, stashes the payload on `self._prefetched`, then calls `super().ingest()` which calls `fetch()` a second time, which sees the stash and returns it. The comment explains why (the framework overwrites `source_method` with the `method` argument, so we have to know the real method *before* calling into the framework). It's ugly but it's the right workaround for a framework limitation and the comment is clear about what it's doing and why. Acceptable.
- **`source_url` is constant per batch (LOW-2 accepted).** Every row gets the same URL regardless of which entity it came from. For a 51-row batch with a single entity this is correct. If this ingestor ever grew to multiple entities it would stop being correct. Fine for now.
- **The `_prefetched` stash is not reset on exception before the `finally`.** If `super().ingest()` raises between `self._prefetched = raw_data` and the `finally`, it will be reset correctly. OK, re-read it — the `finally` is in the right place. Fine.
- **`_normalize_geo_fips` returns the raw digit string for metro/CBSA codes and relies on the caller to filter by length.** Subtle, but the filter in `flatten()` handles it and there's a direct test for it (`test_flatten_filters_five_digit_metro_codes`). Acceptable.

Naming is precise: `_fetch_from_api`, `_parse_api_response`, `_normalize_geo_fips`, `VALID_STATE_FIPS`. No `data`, `info`, `helper`, `utils`. Comments explain *why* (metro filter rationale, framework method-override workaround) not *what*. This is fine.

### `scripts/ingest_bea_rpp.py` — acceptable (fixed)

Remediated: no longer overrides `project_name`. The module-level note explaining why the override was removed is exactly the kind of *why* comment I want to see. Fine.

### `scripts/rebuild_all.py` — BROKEN (condition 1)

Line 26: `project_name="futureproof-data"`. This is the framework drift root cause. Not fixed. See Conditions.

---

## Test Quality

40 tests, 40 pass locally. Raw zone minimum is 10 — this is 4x. The tests are real, not theater:

- **Verified-value assertions are exact (`== 110.7`, `== 87.8`), not range-based.** `test_flatten_verified_values` checks all 8 spec-anchored values. This is what I want — a spec that says "California is 110.7" backed by a test that asserts `== 110.7`.
- **Error-path tests actually assert the right exception with the right message.** `TestParseApiResponse` has 9 tests covering non-dict, missing BEAAPI, missing Results, Error object, missing Data array, empty Data array, missing keys. Each uses `pytest.raises(ValueError, match=...)` with a specific substring. No `except: pass`, no `assert True`.
- **Fallback tests assert the API was retried the expected number of times (`mock_get.call_count == 2`).** Not "eventually called" — exactly 2.
- **`test_csv_path_bypasses_api` patches `requests.get` and asserts `mock_get.assert_not_called()`.** The negative path is tested.
- **`test_flatten_does_not_add_framework_metadata` asserts metadata keys are disjoint from flatten output.** This test exists because a well-meaning future refactor could break the contract between `flatten()` and the framework's metadata pass. Good test.
- **`TestIngestIntegration::test_ingest_lands_51_rows` writes to a real temp Iceberg warehouse and reads back with DuckDB.** Asserts row count is exactly 51, asserts three verified values round-trip exactly, asserts `source_method == "csv_cache"` on every row. This is a real integration test, not a smoke test.

What's missing:

- **No live API test has ever run.** `TestLiveApi` is skipped by default (correct) but there is no audit-trail record of it ever being run with a real key. See Condition 3.
- **No test asserts the `_prefetched` cleanup happens even when `super().ingest()` raises.** If I were being strict I'd require a test that mocks `super().ingest()` to raise and asserts `ingestor._prefetched is None` after the exception propagates. I am not being strict about this — noting it for whoever adds the next test.
- **No test covers the framework drift regression.** Once `rebuild_all.py` is fixed, a regression test should ingest + dq-run in one process and assert exactly one catalog row for each table. See Condition 1.

### Test count vs. minimum

| Zone | Minimum | Actual | Status |
|---|---|---|---|
| Raw | 10 | 40 | PASS |

---

## Spec Compliance

| Spec requirement | Implementation | Match? |
|---|---|---|
| Raw data lands in Iceberg table `raw.bea_rpp` | Lands in `bronze.bea_rpp` (Brightsmith convention) | PASS — governance reviewer confirmed this is the documented alias |
| All 51 geographic entities ingested | 51 rows, 51 unique geo_fips | PASS |
| BEA API preferred, CSV fallback | Code path exists, CSV path is what actually ran | PARTIAL — API path never exercised end-to-end (Condition 3) |
| Filter `LineCode=1` (All Items) | URL template hard-codes `LineCode=1`; CSV cache is pre-filtered | PASS |
| Filter state-level GeoFips only | `VALID_STATE_FIPS` allow-list enforces 50 states + DC; metros dropped with warning | PASS (directly tested) |
| `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)` | Hard-coded in `USER_AGENT` constant | PASS |
| Raw schema matches spec | Iceberg columns: geo_fips, geo_name, rpp_all_items, data_year, source_url, ingested_at, source_method, load_date — exact match | PASS |
| DQ rules: row count exactly 51 (P0) | RAW-BEA-001 | PASS |
| DQ rules: RPP range 80.0 ≤ x ≤ 130.0 (P0) | RAW-BEA-003 | PASS |
| DQ rules: CA spot-check [108.0, 115.0] (P0) | RAW-BEA-007 | PASS (CA=110.7 observed) |
| DQ rules: AR spot-check [84.0, 90.0] (P0) | RAW-BEA-008 | PASS (AR=86.9 observed) |
| DQ rules: geo_fips uniqueness (P0) | RAW-BEA-004 | PASS |
| DQ rules: data_year = 2024 (P0) | RAW-BEA-010 | PASS |
| 8 spec-verified values as reference data | 2/8 codified as DQ rules (CA, AR); 6/8 unenforced (HI, DC, NJ, MS, IA, OK) | GAP — Condition 2 |
| Data contract produced | `governance/data-contracts/raw-bea-rpp.yaml` exists, but status field contradicts header comment | DEFECT — Condition 4 |
| Business glossary terms defined | BT-098, BT-099 from spec + BT-100/101/102 created during remediation | PASS |

---

## Data Correctness Spot-Check

Per staff-engineer protocol I must validate 3-5 output values against independently verifiable reference data. For BEA RPP the spec itself lists 8 verified values from the February 2026 BEA SARPP release; these are public-domain U.S. government statistics published at https://apps.bea.gov/itable/?ReqID=70. Since the spec-listed reference values are the authoritative source and are externally verifiable, I'm using them as the golden set and independently queried the persisted Iceberg table via PyIceberg+DuckDB to confirm round-trip.

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|---|---|---|---|---|---|---|
| California | rpp_all_items | 2024 | 110.7 | 110.7 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| Hawaii | rpp_all_items | 2024 | 110.0 | 110.0 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| District of Columbia | rpp_all_items | 2024 | 109.9 | 109.9 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| New Jersey | rpp_all_items | 2024 | 108.8 | 108.8 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| Arkansas | rpp_all_items | 2024 | 86.9 | 86.9 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| Mississippi | rpp_all_items | 2024 | 87.0 | 87.0 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| Iowa | rpp_all_items | 2024 | 87.8 | 87.8 | BEA SARPP, spec §Key 2024 Values | YES (exact) |
| Oklahoma | rpp_all_items | 2024 | 87.8 | 87.8 | BEA SARPP, spec §Key 2024 Values | YES (exact) |

8/8 exact matches on the spec-verified set. Row count 51. Unique geo_fips 51. Data year {2024}. Source method {csv_cache}. RPP min/max 86.9 / 110.7 (consistent with AR and CA being the tails).

**Important caveat I am not glossing over:** this spot-check validates that the 8 spec-verified values survived the ingest round-trip. It does **not** validate the other 43 rows. Those rows are plausible primary-agent estimates in the correct range but are NOT independently verified against BEA. The contract's `quality_tier` field explicitly says this, which is why Condition 3 (live API end-to-end run) exists. **If Silver consumes this table right now, the 43 unverified rows propagate downstream unflagged at the row level.** That is an acceptable Bronze state only because the spec's primary consumers (Silver, Gold, MCP) have not been built yet, and because the quality_tier disclosure is honest. It is NOT an acceptable state for a refresh-to-production.

### Golden dataset

No formal golden dataset file at `governance/golden-datasets/raw-ingest-bea-rpp-golden.json`. For this spec the 8 spec-listed values *are* the golden set, codified in the spec itself and validated by `test_flatten_verified_values`. I am accepting this as equivalent to a separate golden file for a Raw-zone, 51-row, government-statistics ingest. For Silver/Gold/MCP specs built on top of this, I will require a proper `governance/golden-datasets/` file.

---

## Rulings on items forwarded by governance reviewer

### Ruling 1 — HIGH-1 framework fix ownership

**Fix `rebuild_all.py` under this spec.** The scope of this spec is "get BEA RPP Bronze into a refresh-safe state." `rebuild_all.py` is a project-level script that will destroy the canonical catalog the next time anyone runs it, including for bea_rpp. The fact that the symptom was paper-fixed for bea_rpp only means I cannot sign off without either fixing the root cause here or proving the script will never touch bea_rpp again. The former is a 1-line diff.

**Additionally:** audit `data/catalog/catalog.db` before the fix lands. I already did one pass and found a stray `futureproof-data|governance|lineage_events` row, proving `rebuild_all.py` has been run recently in the drifted state. Every table it registered under `futureproof-data` namespace that dq_runner now reads from `brightsmith` is in the same dual-registration state bea_rpp was in before remediation. That audit is in-scope for this condition because you cannot call `rebuild_all.py` "fixed" until you've also fixed what it already broke.

**The framework-level fix (making `brightsmith.config.configure(project_name=...)` actually propagate to `dq_runner`, or rejecting the argument entirely) is a Brightsmith framework issue.** File it upstream. It is not a blocker for this spec because fixing `rebuild_all.py` to stop overriding `project_name` eliminates the symptom at the caller level.

### Ruling 2 — Deferral of per-row `verification_status` to Silver

**Accepted deferral, with a named owner.** For a Bronze zone with 51 rows that has not yet been consumed by anything downstream, the contract-level `quality_tier` disclosure is sufficient. Per-row `verification_status` is more naturally a Silver concern because Silver is where the row transforms happen and where a computed column would live cleanly alongside `state_abbr` and `census_region`.

**Owner: @primary-agent on silver-base-bea-rpp.** The Silver spec must include a `verification_status` column with values `{bea_official, estimate}` derived from a hard-coded allow-list of the 8 spec-verified geo_fips codes, with at least one DQ rule asserting `count(verification_status='bea_official') == 8` until the live API refresh lands, after which the rule becomes `count(verification_status='bea_official') == 51` and this conditional deferral is closed.

**The MCP-tool hallucination guard portion of HIGH-3 is deferred to the MCP spec,** which will need to return `data_source` in its tool response and refuse to return unverified rows in strict mode. Owner: @primary-agent on mcp-bea-rpp or whoever writes that spec. Log as a known-open item in the MCP pre-review.

### Ruling 3 — HIGH-4 + MEDIUM-1 as next-refresh blockers

**Confirmed. Both are pre-refresh blockers, not pre-Silver blockers.**

- **HIGH-4 (DQ coverage):** Before any refresh, add RAW-BEA-020..025 per the adversarial auditor's proposal covering HI, DC, NJ, MS, IA, OK as individual spot-check P0 rules matching the pattern of RAW-BEA-007 and RAW-BEA-008. Delete or loosen RAW-BEA-017 (mean window) — it was derived from a dataset with 43 estimates so the window is not empirically grounded. If you want a distribution sanity rule, re-derive it after the live API refresh using the real 51 BEA values. Owner: @dq-rule-writer on the refresh PR.
- **MEDIUM-1 (live API never exercised):** Before the refresh data lands in the persisted table, someone with a real `BEA_API_KEY` must run `uv run pytest -m network tests/raw/test_bea_rpp_ingestor.py::TestLiveApi` and capture the pass/fail result in `governance/audit-trail/`. If it passes, run a real refresh ingest that hits the API and replaces the 43 estimates. If it fails, fix whatever's wrong with the API path before shipping. Owner: @primary-agent.
- **MEDIUM-2 (CSV cache integrity):** Before the refresh, add `data/raw/bea_cache/bea_rpp_2024.sha256` containing the checksum of the current CSV, and modify `BeaRppIngestor._read_csv_file()` to assert the checksum before parsing. If the checksum fails, the ingestor raises — it does NOT silently succeed on an edited CSV. This is a pre-refresh blocker because without it there's no forensic way to tell after-the-fact whether a refresh shipped authoritative data or edited data. Owner: @primary-agent.

All three of these are cheap. They should all land in the same refresh PR. That PR needs its own governance-reviewer + staff-engineer sign-off before the contract can transition from DRAFT to ACTIVE.

### Ruling 4 — MEDIUM-3 framework escalation

**Escalate to Brightsmith framework maintainers. Do not block Bronze sign-off for this spec.**

The `governance.dq_rule_results.category` ArrowInvalid issue is a framework-level schema problem: the column is non-nullable but rule files are allowed to omit `category`. The JSON DQ result files are written correctly, so the authoritative record of the DQ run is intact. The only affected artifact is the governance-DB mirror, which is a secondary store. This is exactly the kind of framework bug that should NOT be worked around in individual specs — working around it in bea_rpp would add boilerplate that every future spec then copies, making the framework fix harder to land.

**Owner:** file an issue against the Brightsmith framework repo with a reproducer from this spec and from karpathy_ai_exposure (which is also affected). Link the issue in the futureproof-data project README or in a known-issues doc. Not a blocker for staff-engineer sign-off on bea_rpp Bronze.

---

## Issues

| # | Severity | File | Issue | Required Fix | Owner | Gates |
|---|---|---|---|---|---|---|
| 1 | BLOCKING (this spec) | `scripts/rebuild_all.py` line 26 | `brightsmith.config.configure(project_name="futureproof-data", ...)` — will recreate HIGH-1 catalog drift on next run. | Remove the `project_name` override (accept framework default `"brightsmith"`). Audit `data/catalog/catalog.db` for any other rows under `catalog_name='futureproof-data'` and clean them up. Add a regression test that runs ingest + dq-runner in one process and asserts exactly one catalog row per table. | @primary-agent | Pre-refresh AND pre-contract-ACTIVE. Must land before the next `rebuild_all.py` invocation. |
| 2 | BLOCKING (pre-refresh) | `governance/dq-rules/raw-ingest-bea-rpp.json` | Only 2/8 spec-verified values (CA, AR) are codified as DQ rules. HI, DC, NJ, MS, IA, OK are unanchored. RAW-BEA-017 mean window is derived from a half-estimated dataset. | Add RAW-BEA-020..025 as P0 spot-checks for the 6 missing states following the RAW-BEA-007/008 pattern. Delete or loosen RAW-BEA-017 (re-derive after live API refresh). | @dq-rule-writer | Pre-refresh. Bundled into the refresh PR. |
| 3 | BLOCKING (pre-refresh) | `tests/raw/test_bea_rpp_ingestor.py::TestLiveApi` | Live BEA API has never been exercised end-to-end. Every row in the persisted table is from csv_cache. | Run `uv run pytest -m network tests/raw/test_bea_rpp_ingestor.py::TestLiveApi` with a real `BEA_API_KEY`, log result to `governance/audit-trail/`. If it passes, trigger a refresh ingest that replaces the 43 estimates with authoritative BEA values. | @primary-agent | Pre-refresh. Must pass before refresh data lands. |
| 4 | BLOCKING (immediate) | `governance/data-contracts/raw-bea-rpp.yaml` line 15 | `status: ACTIVE` contradicts the `# Status: DRAFT` comment on line 5 and contradicts the governance reviewer's lifecycle ruling. A YAML parser will read ACTIVE and treat this as a production contract. | Change line 15 to `status: DRAFT`. Do not transition to `ACTIVE` until Conditions 1–3 are resolved. | @data-contract-author | Immediate — fix now, not on refresh. Present-state misrepresentation. |
| 5 | BLOCKING (pre-refresh) | `data/raw/bea_cache/bea_rpp_2024.csv` + `src/raw/bea_rpp_ingestor.py::_read_csv_file` | No integrity control on the CSV cache. Anyone can edit it and the change lands silently with clean provenance. | Add `data/raw/bea_cache/bea_rpp_2024.sha256`. Modify `_read_csv_file()` to compute SHA-256 of the file and compare to the .sha256 file before parsing. Raise `ValueError` on mismatch. Add a test for the mismatch path. | @primary-agent | Pre-refresh. Bundled into the refresh PR. |
| 6 | DEFERRED (Silver spec) | silver-base-bea-rpp (not yet started) | Per-row `verification_status` column deferred from HIGH-3. | Silver must add `verification_status` column with `{bea_official, estimate}` values derived from the 8-state allow-list, plus a P0 DQ rule. | @primary-agent on Silver spec | Silver spec pre-review must reference this. |
| 7 | DEFERRED (MCP spec) | mcp-bea-rpp (not yet started) | MCP tool hallucination guard deferred from HIGH-3. | MCP tool response must include `data_source: {bea_official | estimate}` per row. Strict mode refuses to return unverified rows. | @primary-agent on MCP spec | MCP spec pre-review must reference this. |
| 8 | ADVISORY (framework) | Brightsmith framework — `dq_runner`, `brightsmith.config.configure` | `project_name` argument is silently ignored by `dq_runner` which hard-codes `"brightsmith"`. Root cause of HIGH-1. | File framework issue. Either honor the argument end-to-end or reject it at `configure()` time with a clear error. | Brightsmith maintainers | Forward-only. Not a blocker here. |
| 9 | ADVISORY (framework) | Brightsmith framework — `governance.dq_rule_results.category` schema | Non-nullable column, but DQ rule files may omit `category`. ArrowInvalid suppresses governance-DB mirror writes for bea_rpp and karpathy_ai_exposure. JSON results are authoritative so no data loss. | File framework issue. Make column nullable or backfill default. | Brightsmith maintainers | Forward-only. Not a blocker here. |
| 10 | ADVISORY | `governance/cde-tagging/raw-ingest-bea-rpp.md` | Still contains original placeholder IDs (`BT-RPP-STATE-FIPS`, etc.). Downstream consumer artifacts are clean, so this is a stale forensic document, not a live governance gap. | Either regenerate with final IDs (BT-100/101/102/098) or add a header note pointing to the remediated contract. | @cde-tagger | Non-blocking, cosmetic. |

---

## What's acceptable

- Test suite. 40 tests, real assertions, exact-value spot checks, error-path tests with message matching, negative assertions on `mock_get.assert_not_called()`, real Iceberg integration test that reads back via DuckDB and checks round-trip. Fine.
- Ingestor code quality. Strict parsing, loud failures, honest fallback, redacted URL, precise naming, *why* comments. Fine.
- The 8/8 spec-verified value match on the persisted table. The agents got this right on the rows they verified.
- Secrets hygiene. Independently re-verified: every row has `UserID=REDACTED` in `source_url`. No key leak.
- Chaos pack. 12/12 scenarios caught, zero gaps. Fine.
- Governance artifact completeness. The post-implementation checklist is clean, lineage events reference real tables, glossary terms are real definitions (not "implemented as specified" boilerplate), and the cde-tagging has real CDE rationale per column.
- The remediation work that closed HIGH-1 (on bea_rpp path), HIGH-2, and HIGH-3 (contract level). The agents responded to adversarial findings with fixes, not excuses. That's the right behavior.

---

## Decision

**APPROVED-WITH-CONDITIONS.** Bronze is cleared to unblock Silver. Conditions:

1. **Condition 4 (contract status field) must be fixed immediately** — within this sign-off session, not on the refresh PR. It is a 1-character diff and fixing it is a precondition for me considering this review delivered.
2. **Conditions 1, 2, 3, 5 must land together in a refresh PR** before the next BEA RPP refresh occurs and before the contract transitions from DRAFT to ACTIVE. That PR needs its own governance-reviewer and staff-engineer sign-off.
3. **Conditions 6 and 7** are forwarded to the Silver and MCP specs respectively and must be referenced in those specs' pre-reviews.
4. **Conditions 8 and 9** are forwarded to Brightsmith framework maintainers as issues.

Silver-base-bea-rpp may begin implementation after Condition 4 is fixed.

---

## Artifacts referenced

| Path | Role |
|---|---|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/raw-ingest-bea-rpp.md` | Spec |
| `/Users/jcernauske/code/bright/futureproof-data/src/raw/bea_rpp_ingestor.py` | Ingestor implementation |
| `/Users/jcernauske/code/bright/futureproof-data/tests/raw/test_bea_rpp_ingestor.py` | 40-test suite (40 pass, 1 deselected network) |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/ingest_bea_rpp.py` | Ingest entry point (fixed) |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/rebuild_all.py` | NOT FIXED — Condition 1 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/raw-ingest-bea-rpp-pre-review.md` | Pre-review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/raw-ingest-bea-rpp-post-review.md` | Post-implementation review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/adversarial-audits/raw-ingest-bea-rpp.md` | Adversarial audit (source of findings) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/raw-ingest-bea-rpp.json` | 19 rules (missing 6 per-state spot-checks per Condition 2) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-results/raw-ingest-bea-rpp-20260410T231317Z.json` | Fresh post-remediation run, 19/19 passed, p0=true |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/raw-bea-rpp.yaml` | DEFECTIVE — line 15 status field (Condition 4) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/raw-ingest-bea-rpp-20260410.json` | OpenLineage COMPLETE event |
| `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-reports/raw-ingest-bea-rpp-chaos.md` | 12/12 caught |
| `/Users/jcernauske/code/bright/futureproof-data/data/catalog/catalog.db` | Single `brightsmith|bronze|bea_rpp` row confirmed. Stray `futureproof-data|governance|lineage_events` row present — forensic evidence of HIGH-1 framework drift still active (Condition 1). |
| `/Users/jcernauske/code/bright/futureproof-data/data/bronze/iceberg_warehouse/bronze/bea_rpp/` | 51-row Iceberg table, 8/8 spec-verified values match exactly |
| `/Users/jcernauske/code/bright/futureproof-data/data/raw/bea_cache/bea_rpp_2024.csv` | No .sha256 sibling (Condition 5) |

---

*— End of Staff Engineer Review —*
