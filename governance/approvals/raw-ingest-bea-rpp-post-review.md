# Governance Review: raw-ingest-bea-rpp

**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-10
**Zone:** Bronze (Raw)
**Verdict:** APPROVED-WITH-CONDITIONS

---

## Scope of this review

This review covers **only the Bronze zone** of the `raw-ingest-bea-rpp` spec. The spec is a multi-zone spec (Bronze → Silver → Gold → MCP), but the Silver, Gold, and MCP zones are not yet implemented. Governance sign-off here clears the Bronze ingest to proceed to Silver, conditioned on the open findings below being resolved before the data contract transitions from `DRAFT` to `ACTIVE` and before any downstream refresh.

The adversarial auditor issued a `CONDITIONAL PROCEED` with four HIGH and three MEDIUM findings. A remediation pass closed HIGH-1, HIGH-2, and HIGH-3. I independently verified each closure against source-of-truth artifacts (SQLite catalog, Iceberg table, YAML contract, JSON glossary, data dictionary, DQ results). The remaining open items are documented and forwarded to @staff-engineer.

---

## Post-implementation completeness checklist

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Lineage event exists | PASS | `governance/lineage/raw-ingest-bea-rpp-20260410.json` — valid OpenLineage COMPLETE event, 51/51 rows, sourceMethod=csv_cache, full agent attribution |
| 2 | DQ rules exist | PASS | `governance/dq-rules/raw-ingest-bea-rpp.json` — 19 rules (10 P0, 5 P1, 4 P2) |
| 3 | DQ rules executed against real Iceberg data | PASS | `governance/dq-results/raw-ingest-bea-rpp-20260410T231317Z.json` — fresh run at 23:13 UTC after remediation, 11 earlier runs retained for audit |
| 4 | DQ P0 gate passes | PASS | `p0_passed: true`, 19/19 rules passed, 0 violations across all rules |
| 5 | DQ scorecard produced | PASS | `governance/dq-scorecards/raw-ingest-bea-rpp-scorecard.md` (per pipeline-state; built from real execution results) |
| 6 | CDE/PII flags on contract | PASS | 4 `is_cde: true` (geo_fips, geo_name, rpp_all_items, data_year), 0 `is_pii: true`. Matches cde-tagging report (4 CDE / 0 PII) |
| 7 | Data dictionary entries exist | PASS | `governance/data-dictionary.json` — `raw.bea_rpp` block with all 8 columns, each with description, cde flag, lineage ref, dq rule links, business term |
| 8 | Data contract exists for zone | PASS | `governance/data-contracts/raw-bea-rpp.yaml` — complete, status `ACTIVE` in header (DRAFT per spec lifecycle, covered below) |
| 9 | Audit trail entries | PASS | 10 entries in `governance/audit-trail/2026-04-10-*-raw-bea-rpp*.md` covering every agent |
| 10 | Schema matches spec | PASS | Iceberg table columns: geo_fips, geo_name, rpp_all_items, data_year, source_url, ingested_at, source_method, load_date — exactly matches spec §Raw Schema |
| 11 | Data models (Bronze-only) | N/A | Bronze zone uses physical-only model (raw data lands as-is per Brightsmith convention) |
| 12 | No orphaned artifacts | PASS | Every field referenced in dictionary, contract, cde-tagging, and lineage resolves to a real column in the persisted table |
| 13 | Cross-agent consistency | PASS | geo_fips / geo_name / rpp_all_items / data_year referenced identically across contract, dictionary, lineage, DQ rules, cde-tagging, business glossary |
| 14 | Chaos-monkey pack executed | PASS | `governance/chaos-reports/raw-ingest-bea-rpp-chaos.md` — 12/12 scenarios caught, zero gaps |
| 15 | Adversarial auditor executed | PASS | `governance/adversarial-audits/raw-ingest-bea-rpp.md` — comprehensive, 4 HIGH / 3 MEDIUM / 2 LOW / 2 NOTE |

---

## Independent verification of the four specific cross-checks

### Cross-check 1: DQ rules executed against real Iceberg data (fresh run after remediation)

**PASS.** Twelve result files exist under `governance/dq-results/raw-ingest-bea-rpp-*.json`. The latest is `raw-ingest-bea-rpp-20260410T231317Z.json`, executed at 23:13:17 UTC on 2026-04-10 — strictly after the adversarial audit (23:10:38 UTC per pipeline-state) and after the remediation work. I opened the file and confirmed:

- `run_id: "4dbbfee6"`
- `rules_total: 19`, `rules_passed: 19`, `rules_failed: 0`, `rules_errored: 0`
- `p0_passed: true`
- Every one of the 19 rule results has `"passed": true` and `"violations": 0`
- Execution times are per-rule (0–3 ms), consistent with real DuckDB queries against the Iceberg snapshot, not a stubbed result

### Cross-check 2: No P0 failures

**PASS.** `p0_passed: true` in the latest result file. All 10 P0 rules (RAW-BEA-001 through RAW-BEA-010 per the spec) executed cleanly with zero violations. Spot-checks RAW-BEA-007 (California in [108.0, 115.0]) and RAW-BEA-008 (Arkansas in [84.0, 90.0]) both passed — independently confirmed by reading the persisted table (CA=110.7, AR=86.9).

### Cross-check 3: Data contract does not contain phantom BT-RPP-* business term IDs

**PASS.** `grep BT-RPP /Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/raw-bea-rpp.yaml` → **0 matches**. The contract's four CDE columns now reference real glossary IDs:

- `geo_fips → BT-100` (State FIPS Code)
- `geo_name → BT-101` (State Name)
- `rpp_all_items → BT-098` (Regional Price Parity) — pre-existing
- `data_year → BT-102` (RPP Data Year)

The data dictionary block for `raw.bea_rpp` has been updated in lockstep — grep returns 0 matches for `BT-RPP` within the `raw.bea_rpp` dictionary entry. **Note:** the historical `governance/cde-tagging/raw-ingest-bea-rpp.md` file still contains the original placeholder IDs (`BT-RPP-STATE-FIPS`, etc.) because that artifact is a forensic input document produced by the @cde-tagger agent earlier in the run; the downstream consumer artifacts (contract, dictionary, glossary) are clean, which is what governance enforcement requires.

### Cross-check 4: Business glossary has BT-098, BT-099, BT-100, BT-101, BT-102

**PASS.** All five term IDs confirmed present in `governance/business-glossary.json`:

| Term ID | Name | Evidence |
|---|---|---|
| BT-098 | Regional Price Parity (RPP) | line 1265 |
| BT-099 | Purchasing Power Multiplier | line 1278 |
| BT-100 | State FIPS Code | line 1291 (created during remediation) |
| BT-101 | State Name | line 1304 (created during remediation) |
| BT-102 | RPP Data Year | line 1317 (created during remediation) |

Cross-references between related terms (BT-098↔BT-099, BT-100↔BT-101, BT-102↔BT-098) are present.

### Additional cross-check: Quality tier matches actual verification state

**PASS.** The contract's `quality_tier` field now reads:

> `partial_verification — 51/51 rows structurally valid; 8/51 rows match spec-verified 2024 BEA values (CA, HI, DC, NJ, AR, MS, IA, OK); 43/51 rows are plausible primary-agent estimates pending live BEA API refresh. Source is a U.S. Government statistical publication (public domain) but the CSV-cache load shipped with this spec is NOT fully BEA-authoritative. Downgraded from 'high' per HIGH-3 of governance/adversarial-audits/raw-ingest-bea-rpp.md.`

This accurately and prominently reflects the 8/51 verified / 43/51 estimated split. The tier label is no longer misleading.

### Additional cross-check: Catalog has exactly one row for bea_rpp

**PASS.** Direct SQLite query against `data/catalog/catalog.db`:

```
SELECT catalog_name, table_namespace, table_name, metadata_location
FROM iceberg_tables WHERE table_name = 'bea_rpp';
```

Returns exactly one row:

```
('brightsmith', 'bronze', 'bea_rpp', '.../00001-da1c6259-....metadata.json')
```

The pre-remediation duplicate row under `catalog_name='futureproof-data'` has been removed. This resolves the HIGH-1 landmine on the Bronze bea_rpp path itself. **Caveat for staff-engineer (see open findings):** the underlying root cause — `scripts/ingest_bea_rpp.py` calling `brightsmith.config.configure(project_name="futureproof-data")` while `dq_runner` defaults to `"brightsmith"` — is a framework-level bug that remains unaddressed. Until that is fixed (or a regression test is added), a future refresh of bea_rpp will re-introduce the dual-registration.

### Additional cross-check: Table state

**PASS.** Loaded `bronze.bea_rpp` via PyIceberg + DuckDB:

- Row count: **51** (matches spec, matches DQ rule RAW-BEA-001)
- Distinct `geo_fips`: **51** (uniqueness constraint)
- Distinct `data_year`: **{2024}**
- Distinct `source_method`: **{csv_cache}**
- RPP range: **[86.9, 110.7]** — California 110.7, Arkansas 86.9 (both exact matches to spec-verified values)
- `source_url` on every row contains `UserID=REDACTED` — no API key leak
- Schema columns exactly match the spec's §Raw Schema section

---

## Audit closure table — what the remediation pass actually fixed

| Finding | Severity | Remediation attested | Independent verification | Status |
|---|---|---|---|---|
| HIGH-1 catalog dual-registration | HIGH | Deleted `catalog_name='futureproof-data'` row for bea_rpp | SQLite query returns 1 row under `brightsmith` | **CLOSED** on bea_rpp path. Framework root-cause OPEN (see next table) |
| HIGH-2 phantom BT-RPP-* IDs | HIGH | Created BT-100/101/102 in glossary; updated contract + dictionary | grep confirms 0 phantom IDs in contract + dictionary; glossary has all 5 terms | **CLOSED** |
| HIGH-3 quality tier claim | HIGH | Downgraded `quality_tier` to `partial_verification` with explicit 8/43 split | Read contract YAML, verified wording | **CLOSED** at the contract level. Still OPEN: per-row `verification_status` column and MCP tool hallucination guard (deferred to Silver/Gold specs per remediation notes) |
| HIGH-4 DQ rule windows shaped around estimates | HIGH | — | Rule file still has only 2 verified-value spot-checks (RAW-BEA-007/008); RAW-BEA-017 mean window unchanged | **OPEN** |
| MEDIUM-1 live API test never run | MEDIUM | — | `TestLiveApi` still gated on `@pytest.mark.network`; no audit-trail evidence of a live run | **OPEN** |
| MEDIUM-2 CSV cache integrity | MEDIUM | — | No `.sha256` file alongside `data/raw/bea_cache/bea_rpp_2024.csv` | **OPEN** |
| MEDIUM-3 `category` ArrowInvalid suppressing governance DB mirror | MEDIUM | — | Rule file has no `category` field; framework issue persists | **OPEN** |
| LOW-1 `_prefetched` stateful hack | LOW | — | Unchanged in `src/raw/bea_rpp_ingestor.py` | **OPEN (accepted)** |
| LOW-2 constant `source_url` per batch | LOW | — | Unchanged | **OPEN (accepted)** |
| NOTE-1 secrets hygiene | NOTE | — | Independently re-verified: all 51 rows have `UserID=REDACTED` | **CONFIRMED PASS** |
| NOTE-2 chaos-runner "skip me" language | NOTE | — | Wording unchanged | **OPEN (documentation-only)** |

---

## Issues found (scoped to this review)

| # | Severity | Description | Resolution required |
|---|---|---|---|
| 1 | ADVISORY | `governance/cde-tagging/raw-ingest-bea-rpp.md` still contains the original placeholder IDs (`BT-RPP-STATE-FIPS`, etc.). Downstream artifacts are clean, so this is a stale forensic document rather than an active governance gap — but a reader diffing the cde-tagging file against the contract would see the mismatch. | Non-blocking. Either regenerate the cde-tagging file with the final IDs or add a note at the top pointing to the remediated contract. |
| 2 | CHANGES REQUESTED (pre-contract-ACTIVE) | HIGH-1 root cause unresolved: `scripts/ingest_bea_rpp.py` still calls `brightsmith.config.configure(project_name="futureproof-data")` while `dq_runner` uses `"brightsmith"`. The bea_rpp row is currently clean but a refresh will recreate the dual-registration. No regression test exists. | Pick a single catalog-name strategy for `scripts/ingest_bea_rpp.py` and `scripts/rebuild_all.py`; add a regression test that ingests + dq-runs without manual fixup. Staff-engineer decision. |
| 3 | CHANGES REQUESTED (pre-refresh) | HIGH-4 unresolved: 6 additional verified-value DQ spot-checks (DC, HI, NJ, MS, IA, OK) are available at zero cost but not added. RAW-BEA-017 mean window is too tight. A real BEA API refresh could fail these rules spuriously. | Add RAW-BEA-020..025 per the adversarial auditor's proposal. Loosen or delete RAW-BEA-017. Can be batched into the next refresh PR. |
| 4 | CHANGES REQUESTED (pre-refresh) | MEDIUM-1 unresolved: no evidence the BEA API code path has ever successfully run end-to-end. The entire Bronze load is csv_cache. | Run `uv run pytest -m network tests/raw/test_bea_rpp_ingestor.py::TestLiveApi` with a real `BEA_API_KEY`. Capture result in audit trail. If it works, trigger a refresh that replaces the 43 estimates with live BEA values. |
| 5 | CHANGES REQUESTED (pre-refresh) | MEDIUM-2 unresolved: `data/raw/bea_cache/bea_rpp_2024.csv` has no integrity control. An agent or human can edit it and the change lands in Bronze with clean provenance. | Add `data/raw/bea_cache/bea_rpp_2024.sha256`; assert checksum at read time in the ingestor. |
| 6 | ADVISORY (framework) | MEDIUM-3 unresolved: `governance.dq_rule_results.category` non-nullable while rule files omit `category`. Results are still written to JSON correctly, but the governance DB mirror is dropping rows. | Framework-level fix (make column nullable OR backfill). Not a blocker for this spec. Forward to Brightsmith framework owners. |
| 7 | ADVISORY | HIGH-3 partial: the contract quality tier is now honest, but the spec's stated remediation for "MCP tool hallucination guard" (per-row `verification_status` column, `data_source: bea_official | estimate` flag on the MCP response) has been deferred to future Silver/Gold specs. This is a defensible scope decision for a Bronze-only review, but @staff-engineer should confirm the deferral. | Staff-engineer to confirm deferral is acceptable, or require a per-row `verification_status` addition to Bronze before Silver begins. |

---

## Decision rationale

**Bronze ingest is in a defensibly good state.** The DQ gate is green against real Iceberg data (19/19 passed, P0 clean), the table is structurally correct (51 rows, unique FIPS, correct schema, correct spot-check values for the 8 verified states), governance artifacts are complete and mutually consistent, secrets hygiene is verified against persisted data, and the three HIGH findings that the adversarial auditor flagged as contract-promotion blockers have been materially addressed:

1. **HIGH-1 (catalog drift)** — the immediate symptom on bea_rpp is fixed (single catalog row under `brightsmith`), and the fresh DQ run proves dq_runner can now see the canonical snapshot without a manual band-aid. The framework root cause remains a forward risk for the next refresh, which is why I am flagging it as a `CHANGES REQUESTED` pre-contract-ACTIVE blocker rather than a present-state blocker.

2. **HIGH-2 (phantom business terms)** — fully closed. Five real glossary entries exist; contract and dictionary reference them; zero BT-RPP-* strings in any consumer-facing artifact.

3. **HIGH-3 (quality tier)** — the contract label is now `partial_verification` with an explicit 8/43 split and a prominent note that the load is NOT fully BEA-authoritative. A regulator reading the contract can no longer miss this disclosure. The MCP-tool portion of HIGH-3 is deferred to future specs — defensible because the MCP zone is not yet implemented and any hallucination guard must live there.

The four remaining open items (HIGH-4, MEDIUM-1, MEDIUM-2, MEDIUM-3) are all **next-refresh hardening items**, not present-state correctness issues. They cannot cause current consumers to read wrong data; they can cause the next refresh to silently drift. The adversarial auditor's `CONDITIONAL PROCEED` recommendation maps cleanly onto this reality.

**Therefore: APPROVED-WITH-CONDITIONS.** Bronze ingest is cleared to unblock Silver/Gold implementation. The data contract is cleared to remain in `DRAFT` status. Promotion to `ACTIVE` requires resolution of issues 2–5 above. A refresh before those are resolved requires explicit sign-off from @staff-engineer.

---

## Forwarded to @staff-engineer

Staff-engineer must explicitly rule on:

1. **HIGH-1 framework fix ownership.** Whose job is it — futureproof-data repo scripts or brightsmith framework — to reconcile `PROJECT_NAME` between `scripts/ingest_bea_rpp.py` and `dq_runner`? A regression test is a pre-condition for contract ACTIVE but the fix itself could land anywhere.
2. **Deferral of per-row `verification_status` to Silver.** Is it acceptable that Bronze does not carry a per-row `verification_status` column, relying on the contract-level `quality_tier` disclosure alone until Silver adds the field? The adversarial auditor argued that Bronze is the right layer for this signal.
3. **HIGH-4 + MEDIUM-1 as next-refresh blockers.** Confirm that the pipeline cannot refresh BEA RPP until (a) the 6 additional spot-checks are added, (b) the mean window is loosened/deleted, and (c) the live API path has been exercised end-to-end at least once with a real key.
4. **MEDIUM-3 framework escalation.** Confirm whether the `category` ArrowInvalid issue should block Bronze sign-off for this spec or be forwarded to the Brightsmith framework maintainers for a nullable-column migration.

---

## Artifacts referenced

| Path | Role |
|---|---|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/raw-ingest-bea-rpp.md` | Spec under review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/raw-ingest-bea-rpp-pre-review.md` | Pre-implementation review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-results/raw-ingest-bea-rpp-20260410T231317Z.json` | Fresh DQ run (19/19, p0=true) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/raw-ingest-bea-rpp.json` | 19 rules |
| `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/raw-ingest-bea-rpp-20260410.json` | OpenLineage COMPLETE event |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/raw-bea-rpp.yaml` | Data contract (DRAFT) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-dictionary.json` (raw.bea_rpp block) | Column dictionary |
| `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` (BT-098..BT-102) | Business terms |
| `/Users/jcernauske/code/bright/futureproof-data/governance/cde-tagging/raw-ingest-bea-rpp.md` | CDE/PII tagging (4 CDE / 0 PII) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/eda/raw-bea-rpp-eda.md` | EDA report |
| `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-reports/raw-ingest-bea-rpp-chaos.md` | Chaos pack (12/12 caught) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/adversarial-audits/raw-ingest-bea-rpp.md` | Adversarial audit (source of findings) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/temporal/raw-ingest-bea-rpp.md` | Temporal model |
| `/Users/jcernauske/code/bright/futureproof-data/governance/pii-scans/raw-ingest-bea-rpp.md` | PII scan (none) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/entity-resolution/raw-ingest-bea-rpp.md` | Entity resolution (skip) |
| `/Users/jcernauske/code/bright/futureproof-data/data/bronze/iceberg_warehouse/bronze/bea_rpp/` | Persisted Iceberg table |
| `/Users/jcernauske/code/bright/futureproof-data/data/catalog/catalog.db` | Catalog SQLite (single `brightsmith` row verified) |

---

*— End of post-implementation review —*
