# Adversarial Audit — raw-ingest-bea-rpp

- **Auditor:** @adversarial-auditor
- **Date:** 2026-04-10
- **Spec:** `docs/specs/raw-ingest-bea-rpp.md`
- **Target table:** `bronze.bea_rpp` (51 rows)
- **Complementary to:** chaos-monkey report (`governance/chaos-reports/raw-ingest-bea-rpp-chaos.md`, 12/12 scenarios caught, 0 gaps)

This audit looks for problems the chaos run's happy-path scenario pack is structurally incapable of finding: hallucination in the source data itself, governance artifacts that misrepresent provenance, latent infra bugs that will bite on the next refresh, and placeholder IDs masquerading as governance.

---

## Executive verdict

| Gate | Status |
|---|---|
| Data in the table is wrong today | **Yes (43 of 51 rows)** — but disclosed in EDA, data contract, and data dictionary |
| DQ rules catch the disclosed badness | No (by design — rules are estimate-tolerant) |
| Secrets hygiene (API key not persisted) | **PASS** (verified against live parquet) |
| Ingestor API path actually tested | **PASS** (mocked response path is exercised) |
| Catalog registration is stable across refreshes | **FAIL** — fragile, manual-insert band-aid; will silently break |
| Business glossary referenced by contract & dictionary | **FAIL** — three term IDs do not exist |
| Chaos report's "adversarial-auditor can be skipped" claim | **REJECTED** — chaos only tested shadow mutations; it could not have found items 1, 4, or 7 below |

**Can @staff-engineer proceed?** **CONDITIONAL PROCEED.** Bronze ingest is good enough to unblock Silver/Gold on the understanding that Bronze holds mostly synthetic data. The catalog-registration bug (HIGH-1) and the missing business glossary entries (HIGH-2) must be tracked as release-blockers for the `DRAFT → ACTIVE` contract promotion and for any refresh. The spec cannot claim "quality tier: high" without qualification until 43 of 51 rows become real.

---

## Risk register

Severity legend: **BLOCKER** (do not proceed), **HIGH** (must-fix before contract ACTIVE), **MEDIUM** (fix on the next iteration), **LOW** (nice-to-have), **NOTE** (informational).

### HIGH-1 — Catalog registration is a manual band-aid that will break on next refresh

**Finding.** The DQ engineer's audit trail (`governance/audit-trail/2026-04-10-dq-engineer-raw-bea-rpp.md` section "Catalog Registration Fix") documents that `bronze.bea_rpp` was originally registered under `catalog_name='futureproof-data'` and had to be manually duplicated under `catalog_name='brightsmith'` via a direct `INSERT` into `data/catalog/catalog.db` so that `dq_runner` could see the table.

**Root cause (verified by reading source).** `brightsmith.infra.iceberg_setup.get_catalog()` hardcodes `SqlCatalog(PROJECT_NAME, ...)`. `PROJECT_NAME` is a module-level variable in `brightsmith.config` that defaults to `"brightsmith"`. `scripts/ingest_bea_rpp.py` calls `brightsmith.config.configure(project_name="futureproof-data", ...)` at the top of the module, which flips `PROJECT_NAME` to `"futureproof-data"` for the duration of that process. `dq_runner` (invoked as `uv run python -m brightsmith.infra.dq_runner ...`) does NOT call `configure()`, so its `PROJECT_NAME` stays `"brightsmith"`. Result: the ingest script writes under one catalog_name and the DQ runner reads under another.

**Verification.** Direct SQLite query against `data/catalog/catalog.db`:
```
('futureproof-data', 'bronze', 'bea_rpp', '...00001-da1c6259....metadata.json')
('brightsmith',      'bronze', 'bea_rpp', '...00001-da1c6259....metadata.json')
```
Two rows, same metadata_location — confirms the band-aid.

**Why it is a landmine.** On the next refresh:
1. `scripts/ingest_bea_rpp.py` runs with `PROJECT_NAME="futureproof-data"`.
2. `get_catalog()` returns a catalog bound to `catalog_name='futureproof-data'`.
3. PyIceberg appends new data and updates `metadata_location` ONLY on the `futureproof-data` row.
4. The `brightsmith` row continues to point at the **old** metadata file (`00001-...`) which still references the original parquet snapshot.
5. `dq_runner` reads via `catalog_name='brightsmith'` and silently validates a stale snapshot. Rules pass. Nobody notices that the refreshed data never entered the audited path.

The chaos run could not have found this — it tested rule behavior against shadow mutations, not the catalog-name resolution path.

**The claim in the task brief that `scripts/ingest_bea_rpp.py` was "fixed" is partly true and partly misleading.** Lines 64–72 of the script use `get_catalog()` for a post-ingest row-count verification. That code is correct. But the WRITE path (`ingestor.ingest(force_fallback=True)` on line 60) also goes through `get_catalog()` — and both resolve to `PROJECT_NAME="futureproof-data"` because `configure()` was called at the top of the file. The script is internally consistent; the bug is cross-process: *no entry point reconciles PROJECT_NAME with the dq_runner entry point.*

**Must-do.** Pick ONE of:
- **(a) Delete the `futureproof-data` catalog row** and have `scripts/ingest_bea_rpp.py` stop calling `configure(project_name="futureproof-data", ...)` (or pass `project_name="brightsmith"`). Then everything — ingest, dq_runner, downstream — uses one name. Requires the same fix in `scripts/rebuild_all.py`.
- **(b) Change `get_catalog()`** to accept an explicit `catalog_name` argument with a sane default, and have `dq_runner` read from `brightsmith.config.PROJECT_NAME` at call time the same way. Framework-level change; bigger blast radius.

Until one of these is done, **every refresh of BEA RPP requires the DQ engineer to re-run the manual INSERT fix** and every other table in the repo that went through `scripts/*` is likely in the same dual-registration state. Spot-check the other bronze tables to see how widespread this is.

**Assessment of existing controls.** **Weak.** The audit trail documents the problem clearly but there is no test, no lint, no pre-flight check, and no CI assertion that `catalog_name` is consistent across writers and readers. A single silent refresh is enough to desynchronize dq_runner from reality.

**Evidence demanded before contract goes ACTIVE.**
1. A test that writes via `scripts/ingest_bea_rpp.py`, then runs `dq_runner` without any manual catalog fixup, and confirms it reads the same snapshot.
2. A one-paragraph "catalog name ownership" note in `governance/domain-context.md` explaining which name governs.
3. Either the script fix (delete the futureproof-data row + stop calling `configure`) or a framework fix with a regression test.

---

### HIGH-2 — Business glossary placeholders are referenced but do not exist

**Finding.** `governance/data-contracts/raw-bea-rpp.yaml` lists `business_term: BT-RPP-STATE-FIPS` (geo_fips), `BT-RPP-STATE-NAME` (geo_name), and `BT-RPP-DATA-YEAR` (data_year). `governance/data-dictionary.json` references the same three IDs. **None of them exist in `governance/business-glossary.json`** (grep confirmed: 0 matches). The highest real ID in the glossary is BT-099 (Purchasing Power Multiplier). BT-098 (Regional Price Parity) is the only BEA-related term that actually resolves.

**Why it matters.** A regulated-industry reviewer would flag a data contract whose CDE columns reference phantom business terms. Three of the four CDE columns in the BEA table (`geo_fips`, `geo_name`, `data_year`) have `is_cde: true` and `cde_rationale: ... per domain-context.md BEA RPP section` but the linked business term cannot be retrieved from any machine-readable artifact. If a downstream consumer dereferences `BT-RPP-STATE-FIPS` they get a null.

**Is this defensible as an interim state?** Partially. The `@doc-generator` audit trail (`governance/audit-trail/2026-04-10-doc-generator-raw-bea-rpp.md`, decision #2) explicitly documents the decision to retain placeholders because the brief only approved creating BT-098 and BT-099 and the glossary has no geographic-identifier terms yet. That's governance process working as intended — a known gap, explicitly scoped out, with a written handoff to a future run.

**But** the placeholder IDs follow the real `BT-###` naming pattern closely enough (`BT-RPP-STATE-FIPS`) that a mechanical validator that just grepped for `BT-` would miss them. And the data contract's `is_cde: true + business_term: BT-RPP-STATE-FIPS` pairing makes an implicit claim that is not backed by the glossary.

**Assessment of existing controls.** **Weak.** The audit trail makes the decision; nothing enforces that these placeholders are either filled in or flagged before the contract transitions to ACTIVE. A regulator would ask: "Is the contract internally consistent?" Today the answer is no.

**Must-do before contract ACTIVE:** either (a) create real BT-### entries for the three terms (recommended — there are only three), or (b) rename them to something obviously non-BT in the contract and dictionary (e.g., `TBD-RPP-STATE-FIPS`) so no consumer mistakes them for resolvable terms. Option (a) is a 15-minute task and should be the pre-condition for contract promotion.

---

### HIGH-3 — 43 of 51 rows are synthetic and the quality tier says "high"

**Finding.** The EDA (`governance/eda/raw-bea-rpp-eda.md`, "Estimated vs. Verified Values" section) is unambiguous: **8 rows are spec-verified from the real BEA 2024 release, 43 rows are "primary-agent estimates" (plausible placeholders) filled into the CSV cache.** This is disclosed prominently in EDA, in the data contract's `quality_tier` note, and in the data dictionary table description.

**What works.**
- The disclosure is present in every major governance artifact I checked.
- The DQ rules are explicitly designed to be estimate-tolerant: range guards, distribution sanity, spot-checks only on verified values (CA, AR, DC). The DQ rule writer's notes and the EDA's "Recommended DQ Rule Thresholds" section cross-reference this.
- All 8 verified values survive round-trip into the Iceberg table exactly (verified via the existing `test_flatten_verified_values` and `test_ingest_lands_51_rows` tests).

**What does not work.**
1. The **data contract's `quality_tier` says `"high (U.S. Government statistical publication, public domain)"` with the synthetic-values caveat tacked on as a trailing note.** That is technically accurate but misleading — a consumer reading "high" and missing the tail of the sentence would make purchasing-power decisions based on fabricated numbers for Alabama, Alaska, Arizona, Colorado, ..., (43 states total). The tier label should be downgraded, or a separate `data_completeness` flag should be introduced. "High tier with 84% of rows synthetic" is a contradiction.
2. The **MCP tool claim `get_regional_price_parity(state)` returns BEA-official data**. That claim is false for 43/51 queries today. If Gemma cites "California RPP is 110.7 from BEA" for any non-verified state, the citation is a hallucination. The MCP tool needs to either (a) reject non-verified states with "data pending", (b) return a `data_source: "bea_official"` vs `"estimate"` flag, or (c) filter to only the 8 verified states until a real refresh lands.
3. The **CSV cache file (`data/raw/bea_cache/bea_rpp_2024.csv`) contains NO annotation distinguishing verified from estimated rows**. Column layout is `GeoFips,GeoName,TimePeriod,DataValue`. A human reading the CSV in isolation would believe all 51 values are equally authoritative. The cache file is the actual landing zone when the API is down — a future engineer debugging an ingest failure could read that CSV and not realize 43 rows are fake. Recommend adding a 5th column `verification_status` (`verified`|`estimate`) or a header comment row, and having the ingestor carry that signal through to a per-row `verification_status` field in the Bronze schema.

**How a regulator would phrase this.** "You are telling me this is U.S. Government public-domain data. Eighty-four percent of the rows were generated by an LLM and labeled as if they came from BEA. Show me where the data contract says that in its primary quality signal, not in a parenthetical."

**Assessment of existing controls.** **Adequate for EDA and DQ, weak for downstream consumer-facing artifacts.** The pipeline knows the truth internally but does not propagate it past the contract boundary. A `verification_status` column at Bronze would fix this and propagate naturally to Silver, Gold, and the MCP tool response.

**Evidence demanded.**
- A field `rpp_source` or `verification_status` in the Bronze schema, per-row, carried through to Gold, and surfaced in the MCP tool response.
- `quality_tier` in the data contract explicitly qualified as `partial_verification` or `estimates_in_place` until the BEA API load succeeds.
- A test asserting `verification_status='verified'` for exactly 8 known FIPS codes and `'estimate'` for the rest.

---

### HIGH-4 — DQ rules are shaped around the estimates and will not detect a bad refresh

**Finding.** The DQ rule thresholds (`governance/dq-rules/raw-ingest-bea-rpp.json`) were designed from EDA that profiled the current estimates-in-place dataset. The rule writer explicitly states (in rule 17 evidence): "Rule is estimate-tolerant and refresh-tolerant." That is a claim, not a test.

**Specific concerns.**

1. **RAW-BEA-017 (mean in [94.0, 100.0]).** The observed mean is 96.98 and the window is [94.0, 100.0]. A real BEA 2024 refresh that happens to produce a simple-mean of 93.9 (plausible — depends on which states shift how) would fail this rule even though every individual row is correct. The rule would then need to be loosened post-hoc, after the refresh, which breaks the "refresh tolerance" claim.
2. **RAW-BEA-003 (range [80.0, 130.0]).** Generous, probably safe.
3. **RAW-BEA-018 / RAW-BEA-019 (min ≥ 84.0, max ≤ 115.0).** These are tighter than RAW-BEA-003 and are also derived from a dataset where 43 of 51 values are fabricated to look plausible. If the real BEA refresh puts Arkansas at 83.8 (within historical BEA precedent) the rule will fail spuriously.
4. **RAW-BEA-007 (California in [108.0, 115.0]) and RAW-BEA-008 (Arkansas in [84.0, 90.0]).** These are safe because both are spec-verified against the real 2024 BEA release. Good.
5. **Nothing in the rule set will detect "the estimates were replaced but the new values are also wrong."** If a future refresh silently swaps in a corrupted CSV that happens to stay inside [80, 130] and stay close to the current mean, the rules will pass and governance will mark it green. The only real anchors are the 2 state spot-checks (CA, AR).

**Coverage gap.** Only **2 of 51 states have a hard, verified-value spot-check** in the DQ rules (CA and AR). DC, Hawaii, New Jersey, Mississippi, Iowa, and Oklahoma are all spec-verified from the real BEA release but have no corresponding DQ guard. The rule writer could have added 6 more near-exact spot-checks at effectively zero cost and chose not to. Add them.

**Proposal.**
- Add RAW-BEA-020..025: per-state spot-checks for DC (109.5–110.3), HI (109.5–110.5), NJ (108.3–109.3), MS (86.5–87.5), IA (87.3–88.3), OK (87.3–88.3). These are verified values; the windows are 0.5-pt either side.
- Loosen RAW-BEA-017 mean window to [95.0, 99.0] OR delete it — a simple average of 51 state indices is not a meaningful quantity in the first place and only gives chaos runs something easy to catch.

**Assessment of existing controls.** **Adequate.** The rule writer's design is defensible and the chaos runner proved the rules catch gross errors. But the post-refresh claim is untested and only 2/8 verified values are anchored. This is not a blocker — it is a pre-refresh hardening item.

---

### MEDIUM-1 — API-success test path exists but tests only a mocked response

**Finding.** `tests/raw/test_bea_rpp_ingestor.py::TestFetchFallback::test_api_success_returns_parsed_records` patches `requests.get` with a hand-constructed BEA-shaped JSON. The ingestor never touches the real BEA endpoint in the default test suite. A live test exists (`TestLiveApi::test_live_bea_api`) but is marked `@pytest.mark.network` and skipped unless `BEA_API_KEY` is set.

**Is this test theater?** No, but the phrasing in the brief is generous. The mocked test exercises `_fetch_from_api → _parse_api_response → flatten` and asserts parsed row count. It catches regressions in the parser and the JSON shape assumptions. It does NOT catch:
- A BEA schema change (new required key added, field renamed).
- A BEA rate-limit response with a 200 status and a different error envelope.
- The actual URL being wrong (e.g., `TableName=SARPP` changed server-side).
- The API key query parameter being mis-encoded.

The live test (`test_live_bea_api`) would catch all of those but is opt-in and currently has never been run (no evidence in audit trail of a successful `pytest -m network` run for this spec).

**What works.** The parser is hardened — `_parse_api_response` raises `ValueError` on shape drift (missing `BEAAPI`, `Results`, `Data`, `Error` envelope, required keys, empty array). Ten `test_rejects_*` tests pin the negative cases. The fallback path is genuinely reached whenever the API raises.

**Assessment of existing controls.** **Adequate for offline CI, Missing for integration confidence.** The hardening and the mock are real. But there is no evidence that any agent ever successfully hit the live BEA API with this ingestor — the whole current Bronze load is `source_method='csv_cache'`, the audit trail says "For this run the CSV fallback was used", and the chaos report does not claim to have tested the API path against a real key. The API path works in theory.

**Evidence demanded.** A one-time execution of `uv run pytest -m network tests/raw/test_bea_rpp_ingestor.py::TestLiveApi` with a real BEA_API_KEY, result captured in the audit trail. This is a 30-second task that would collapse this risk.

---

### MEDIUM-2 — CSV fallback file is the actual source of truth but has no integrity guarantee

**Finding.** The CSV at `data/raw/bea_cache/bea_rpp_2024.csv` is a flat 4-column file committed to the repo (no checksum, no detached signature, no git-lfs attestation). The ingestor trusts this file absolutely — whatever is in it becomes the Bronze data. There is no assertion in the ingestor or in the tests that the CSV's 51 rows match any specific fingerprint.

**Attack surface.** Anyone with commit access — human or agent — can edit this file and the change will land in Bronze with a clean `source_method='csv_cache'`, a clean provenance URL, and (with values still in-range) a clean DQ run. The only defense is code review of the CSV diff.

**Why this matters in the AI-generated-data threat model.** The whole point of this audit is that an AI agent could hallucinate. An AI agent wrote 43 of the 51 rows in this file. That agent is no less trustworthy than the one that may edit it next week. There is no way to distinguish "Alabama 88.4 was the primary-agent's best guess" from "someone changed Alabama to 88.4 last Tuesday" from `git log` alone, and definitely not from the file itself.

**Proposal.**
- Add a `data/raw/bea_cache/bea_rpp_2024.sha256` alongside the CSV and have the ingestor assert the checksum matches at read time. The assertion value goes into the audit trail and the lineage record.
- When the real BEA API refresh succeeds, the live-API path can overwrite the CSV from the API response and regenerate the sha256 — the ingestor should update the checksum file automatically on successful API loads only.

**Assessment of existing controls.** **Missing.** No integrity control of any kind on the committed CSV. Git history is the only defense.

---

### MEDIUM-3 — The pre-existing `category` ArrowInvalid error is NOT affecting DQ correctness, but it IS suppressing the governance DB mirror

**Finding.** The DQ engineer and chaos reports both document a recurring `pyarrow.lib.ArrowInvalid: Column 'category' is declared non-nullable but contains nulls` error. This happens when `dq_runner` tries to sync its 19-row result set into the governance Iceberg table `governance.dq_rule_results`.

**Does it affect the JSON results? No.** I verified `governance/dq-results/raw-ingest-bea-rpp-20260410T223336Z.json` directly — all 19 rules are present, each with `raw_value`, `violations`, `execution_time_ms`, `passed`. The JSON is well-formed. The Arrow error is in a downstream write that happens AFTER the results are computed and serialized.

**But what it DOES affect:** the governance DB mirror (`governance.dq_rule_results`) is the single place where a governance reviewer or CAB reviewer could query across ALL spec DQ runs historically. If the mirror is silently dropping BEA RPP results — and every other spec whose rule file lacks a `category` field, including Karpathy AI Exposure per the cross-file grep — then the DB is an unreliable source for governance reporting. A CAB reviewer pulling a rollup would see missing rows and not know why. The error is "pre-existing and non-blocking" only in the narrow sense that it doesn't break the current JSON payload; in the wider sense it is silently eroding the reliability of the governance DB.

**Proposal.** Either:
- (a) Make `governance.dq_rule_results.category` nullable (one-line framework change), or
- (b) Require @dq-rule-writer to populate `category` on every rule going forward AND backfill the existing rule files.

Option (a) is strictly easier and has fewer side effects. This is a framework issue, not a BEA issue, but it is material to the "are we trustworthy" question and should not be dismissed as "noise."

**Assessment of existing controls.** **Weak.** The error is documented in two audit trails and one chaos report but no ticket, no fix, no assertion that the governance DB state matches the JSON result files. A rollup query against `governance.dq_rule_results` today would under-count BEA RPP runs. Governance reviewers relying on that mirror are reading stale data.

---

### LOW-1 — Ingestor has a stateful-hack in `ingest()` that could surprise a future refactor

**Finding.** `BeaRppIngestor.ingest()` overrides `BaseIngestor.ingest()` to run `fetch()` eagerly, stash the result on `self._prefetched`, and then call `super().ingest()` which re-invokes `fetch()` — `fetch()` detects the stash and returns it. This is a workaround for the framework's design where `BaseIngestor` always overwrites each row's `source_method` with the caller-supplied `method` argument; BEA needs the row-level `source_method` to reflect which path actually ran (API vs CSV), which is only knowable post-fetch.

**Is the hack correct? Yes.** `try/finally` clears `self._prefetched` even on exception. The logic is tight. But:
1. It introduces transient mutable state on `self`, which means a shared ingestor instance used across two overlapping `ingest()` calls would corrupt state. There is no evidence any caller does this, but there is no test asserting that it doesn't.
2. It makes the `fetch()` signature lie: `fetch()` advertises `kwargs` like `csv_path`, `api_key`, `force_fallback`, but it silently short-circuits them if `self._prefetched` is set. A test that calls `fetch()` directly after `ingest()` threw mid-flight could see stale data.
3. The right fix is a framework change to let subclasses return `source_method` from `fetch()` directly, but that's out of scope for this audit.

**Assessment of existing controls.** **Adequate** for the current single-threaded single-process use case. Flag for framework-level revisit.

---

### LOW-2 — `source_url` is identical across all 51 rows — provenance signal is weak

**Finding.** `source_url` is a constant string (the API URL template with `UserID=REDACTED`) for every row, regardless of whether the row came from the API or the CSV. The lineage record defends this as intentional: "Same value whether the API or CSV cache was used — represents the canonical source locator, not the fetch path." Fine. But then `source_method` is the only per-row signal that tells you whether the row is live or cached. And `source_method` is also constant across all 51 rows in a single load. So there is **no row-level provenance variation** within a batch — the whole batch is annotated identically.

**Impact.** If a future ingest mode introduces a hybrid fetch (some rows from API, some from CSV), the current schema cannot represent it. That is not the case today and is probably never the case for a 51-row reference table. Flagging for completeness.

**Assessment of existing controls.** **Adequate.** Low-impact, schema-extensible.

---

### NOTE-1 — Secrets hygiene verified against real data

**What I checked.** I loaded the actual persisted `bronze.bea_rpp` Iceberg table via PyIceberg, pulled every `source_url` value, and ran:
```
has api_key leaked? False
```
All 51 rows have `source_url = "https://apps.bea.gov/api/data/?&UserID=REDACTED&..."`. No row contains the literal string from the `BEA_API_KEY` env var. The ingestor's `get_source_url()` method returns the template with `UserID='REDACTED'` hardcoded, which is correct. The CSV cache file does not contain the API key either (grep: absent).

**This is genuine evidence, not self-attestation.** The claim in the data contract ("secrets-hygiene guardrail") matches the persisted data. **PASS.**

---

### NOTE-2 — Chaos report's "skip adversarial-auditor" claim is wrong, but for a defensible reason

**Finding.** The chaos report (`governance/chaos-reports/raw-ingest-bea-rpp-chaos.md`, final verdict) concludes: "adversarial-auditor can be skipped for this spec. The requested scenario pack plus the negative control form a complete coverage test."

**Why this is wrong.** The chaos runner only tests what the rules catch when data is mutated in the shadow parquet. It structurally cannot find:
- HIGH-1 (catalog name drift) — no data mutation involved.
- HIGH-2 (phantom glossary IDs) — no DQ rules reference business terms.
- HIGH-3 (synthetic data in quality-tier "high") — no rule knows the difference.
- HIGH-4 (rule windows shaped around estimates) — the chaos mutations all sit in the same "within historical plausibility" band; nothing tests the rules against a legitimately different but valid distribution.
- MEDIUM-2 (CSV file integrity) — the runner assumes the CSV is canonical.
- MEDIUM-3 (Arrow error suppressing governance DB mirror) — the runner reads the JSON, not the mirror.

The chaos run did exactly what it was designed to do (verify rule coverage against a scenario pack) and reached a defensible verdict within its own scope. But the chaos runner's scope is narrower than the adversarial-auditor's scope. The "skip me" claim in the verdict is a category error — chaos-monkey and adversarial-auditor are complementary, not substitutes.

**Assessment.** **Adequate** — the chaos run stands, its scenario-pack verdict is correct, and its hardening proposals are sensible. The wrapper verdict ("skip me") should be softened in the future to "within the scope of DQ rule coverage, no gaps; unscoped hallucinations and infra bugs remain for adversarial-auditor."

---

## Evidence summary — what I actually verified (not "we tested it")

| Claim | How I verified it | Result |
|---|---|---|
| CSV has 51 rows, verified values match | Direct read of `data/raw/bea_cache/bea_rpp_2024.csv`; manual diff against spec verified table | **PASS** (CA=110.7, HI=110.0, DC=109.9, NJ=108.8, AR=86.9, MS=87.0, IA=87.8, OK=87.8 all exact) |
| Bronze parquet contains those same values | Loaded table via `catalog.load_table('bronze.bea_rpp')` and `read_with_duckdb` | **PASS** |
| No API key leak in source_url | Scanned all 51 row source_url values for the redaction marker | **PASS** — every row has `UserID=REDACTED` |
| Catalog is doubly-registered | `SELECT * FROM iceberg_tables WHERE table_name='bea_rpp'` against `data/catalog/catalog.db` | **2 rows — 1 under `futureproof-data`, 1 under `brightsmith`** (confirms band-aid) |
| Business glossary has phantom IDs | Grep `BT-RPP-STATE-FIPS|BT-RPP-STATE-NAME|BT-RPP-DATA-YEAR` against `governance/business-glossary.json` | **0 matches** (confirms phantom) |
| Mocked API response test exists but live test is opt-in | Read `tests/raw/test_bea_rpp_ingestor.py` | **Confirmed** — `TestLiveApi` is `@pytest.mark.network` and skipped unless `BEA_API_KEY` set |
| DQ JSON result payload is well-formed despite Arrow error | Read `governance/dq-results/raw-ingest-bea-rpp-20260410T223336Z.json` directly | **PASS** — 19 rules, all passed, JSON structurally valid |
| DQ rule thresholds are consistent with EDA findings | Cross-referenced `dq-rules/raw-ingest-bea-rpp.json` against `eda/raw-bea-rpp-eda.md` recommended thresholds | **Match** — rules implement exactly what EDA recommended |

---

## Recommendations — prioritized

### Must-do before contract moves DRAFT → ACTIVE

1. **Fix HIGH-1.** Pick a catalog-name ownership strategy and enforce it across `scripts/ingest_bea_rpp.py`, `scripts/rebuild_all.py`, and `dq_runner`. Delete the redundant catalog row. Add a regression test.
2. **Fix HIGH-2.** Create the three real `BT-###` entries in `governance/business-glossary.json` (BT-100 State FIPS, BT-101 State Name, BT-102 Data Year) and update the contract + dictionary to reference them. Or explicitly rename placeholders to something non-BT.
3. **Fix HIGH-3.** Either downgrade `quality_tier` in the data contract to `partial_verification` until the API refresh lands, or add a per-row `verification_status` column to Bronze and propagate it to Silver, Gold, and the MCP tool response.

### Must-do before next refresh

4. **Fix HIGH-4.** Add 6 more spot-check DQ rules (DC, HI, NJ, MS, IA, OK) against their verified values. Loosen or delete RAW-BEA-017 (mean window).
5. **Fix MEDIUM-2.** Add a sha256 file alongside the CSV cache and assert it at ingest time.
6. **Run the live API test.** `uv run pytest -m network tests/raw/test_bea_rpp_ingestor.py::TestLiveApi` with a real key. Capture the result in the audit trail. If it works, trigger a refresh that replaces all 43 estimates with real BEA values, then re-run DQ and the chaos pack.

### Should-do

7. **Fix MEDIUM-3.** Make `governance.dq_rule_results.category` nullable at the framework level and re-sync the mirror.
8. **Annotate LOW-1.** Add a one-line warning comment in `BeaRppIngestor.ingest()` about the `_prefetched` state machine, flag as a framework-level revisit candidate.

### Nice-to-have

9. Audit the other bronze tables (`bronze.college_scorecard`, `bronze.bls_ooh`, `bronze.onet`, `bronze.karpathy_ai_exposure`) for the same dual-catalog-row problem. If they have it, they are also broken on refresh.
10. In the chaos-report verdict section, soften the "adversarial-auditor can be skipped" language.

---

## Final gate decision

**PROCEED CONDITIONALLY.**

@staff-engineer can sign off on Bronze-level approvals (DQ gate is green, secrets are clean, the ingestor is well-tested within its offline scope) provided the following are tracked as **contract-promotion blockers** (DRAFT → ACTIVE):

- HIGH-1 (catalog registration fragility)
- HIGH-2 (phantom business term IDs)
- HIGH-3 (quality-tier label vs. 84% synthetic data)

And the following are tracked as **next-refresh blockers**:

- HIGH-4 (under-anchored DQ spot-checks)
- MEDIUM-1 (no evidence the live API path has ever run end-to-end)
- MEDIUM-2 (CSV cache integrity)

The spec is NOT cleared to promote its data contract to ACTIVE today. It IS cleared to unblock Silver/Gold implementation work on the understanding that Silver/Gold will inherit the same `estimates-in-place` caveat in their own contracts.

A regulator would accept this audit. A regulator would NOT accept the project if items 1–3 go unaddressed before the contract goes ACTIVE.

---

*— End of audit —*
