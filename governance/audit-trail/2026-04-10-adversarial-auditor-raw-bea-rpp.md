# Audit Trail: @adversarial-auditor — raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @adversarial-auditor
**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Zone:** Bronze
**Complementary to:** `governance/chaos-reports/raw-ingest-bea-rpp-chaos.md`
**Deliverable:** `governance/adversarial-audits/raw-ingest-bea-rpp.md`

---

## Scope

Skeptical review of the Bronze-zone BEA RPP artifacts to find hallucination risks, latent infra bugs, and governance theater that the chaos-monkey's happy-path scenario pack could not have surfaced. Explicitly in scope: catalog registration hack, synthetic-values provenance, business glossary placeholders, API key hygiene, DQ rule post-refresh behavior, pre-existing Arrow error impact.

## Artifacts reviewed

| Artifact | Path | Outcome |
|---|---|---|
| Spec | `docs/specs/raw-ingest-bea-rpp.md` | Complete, well-scoped |
| Ingestor | `src/raw/bea_rpp_ingestor.py` | Correct, with minor state-machine caveat |
| Tests | `tests/raw/test_bea_rpp_ingestor.py` | Offline coverage solid; live path never run |
| CSV cache | `data/raw/bea_cache/bea_rpp_2024.csv` | 51 rows, no integrity control, no verification annotation |
| EDA | `governance/eda/raw-bea-rpp-eda.md` | Excellent; discloses 8-verified/43-estimated split |
| DQ rules | `governance/dq-rules/raw-ingest-bea-rpp.json` | 19 rules; only 2 verified-value spot-checks |
| DQ results | `governance/dq-results/raw-ingest-bea-rpp-20260410T223336Z.json` | 19/19 PASS, JSON well-formed |
| DQ engineer trail | `governance/audit-trail/2026-04-10-dq-engineer-raw-bea-rpp.md` | Documents the manual catalog fix |
| Chaos report | `governance/chaos-reports/raw-ingest-bea-rpp-chaos.md` | 12/12 scenarios caught — within its scope |
| Data contract | `governance/data-contracts/raw-bea-rpp.yaml` | References phantom business term IDs |
| Lineage | `governance/lineage/raw-ingest-bea-rpp-20260410.json` | Complete |
| Data dictionary | `governance/data-dictionary.json` (`raw.bea_rpp` entry) | References phantom business term IDs |
| Business glossary | `governance/business-glossary.json` | Only BT-098, BT-099 present; BT-RPP-* absent |
| Doc-generator trail | `governance/audit-trail/2026-04-10-doc-generator-raw-bea-rpp.md` | Documents the placeholder decision |
| Script | `scripts/ingest_bea_rpp.py` | Catalog-name mismatch persists |
| Framework (read-only) | `brightsmith/src/brightsmith/config.py`, `iceberg_setup.py`, `bronze/base_ingestor.py`, `infra/dq_runner.py` | Confirmed `PROJECT_NAME` drift between entry points |

## Direct verification performed

Not "we tested it" — actual commands I ran against the real filesystem and warehouse:

1. **Live parquet read** via `catalog.load_table('bronze.bea_rpp')` → 51 rows, `source_method` uniformly `csv_cache`, `source_url` uniformly the redacted template. **No API key present in any persisted row.**
2. **Direct SQLite query** against `data/catalog/catalog.db` → two rows for `bea_rpp` (one under `catalog_name='futureproof-data'`, one under `'brightsmith'`), both pointing at the same metadata file. Confirms the DQ engineer's band-aid is still in place.
3. **Grep of `governance/business-glossary.json`** for `BT-RPP-STATE-FIPS`, `BT-RPP-STATE-NAME`, `BT-RPP-DATA-YEAR` → **0 matches**. These IDs are referenced by the data contract and data dictionary but do not resolve.
4. **CSV spot-check** against spec's 8 verified values → exact match (CA=110.7, HI=110.0, DC=109.9, NJ=108.8, AR=86.9, MS=87.0, IA=87.8, OK=87.8).
5. **Read of `brightsmith.config.PROJECT_NAME` resolution** → default `"brightsmith"`, flipped to `"futureproof-data"` only inside `scripts/ingest_bea_rpp.py` and `scripts/rebuild_all.py`. `dq_runner` never calls `configure()`, so it sees the default. This is the root cause of the dual-registration bug.
6. **DQ results JSON integrity** → all 19 rules present, all `passed: true`, all `raw_value: 0`. Structurally valid despite the documented governance DB mirror error.

## Findings

Detailed report at `governance/adversarial-audits/raw-ingest-bea-rpp.md`. Severity summary:

| Severity | Count | IDs |
|---|---|---|
| BLOCKER | 0 | — |
| HIGH | 4 | HIGH-1 catalog registration fragility; HIGH-2 phantom glossary IDs; HIGH-3 quality-tier label vs. synthetic data; HIGH-4 under-anchored DQ spot-checks |
| MEDIUM | 3 | MEDIUM-1 live API path never run; MEDIUM-2 CSV cache no integrity control; MEDIUM-3 Arrow error erodes governance DB mirror |
| LOW | 2 | LOW-1 ingestor `_prefetched` state machine; LOW-2 identical row-level provenance |
| NOTE | 2 | NOTE-1 secrets hygiene verified PASS; NOTE-2 chaos report's "skip adversarial-auditor" claim is wrong but defensible |

## Gate decision

**CONDITIONAL PROCEED.**

- @staff-engineer may sign off on Bronze implementation and unblock Silver/Gold.
- The data contract **cannot** move from `DRAFT` to `ACTIVE` until HIGH-1, HIGH-2, and HIGH-3 are resolved.
- The next refresh is blocked until HIGH-4, MEDIUM-1, and MEDIUM-2 are resolved, or the refresh is explicitly scoped as "estimates replacement only, not verified."

Chaos-monkey's "adversarial-auditor can be skipped" verdict is rejected: chaos scoped to rule coverage against data mutations, which cannot find infra bugs, governance theater, or provenance hallucinations.

## Key decisions documented

1. **Treated the 43-estimated/8-verified split as a governance disclosure success but a consumer-facing failure.** The EDA, DQ, and data contract all document the split; the MCP tool response, quality_tier label, and CSV cache file itself do not propagate the signal. Flagged as HIGH-3.
2. **Did NOT recommend deleting the 43 estimated rows.** Removing them would break the "row count = 51" DQ rule and the Silver/Gold fan-out. The correct fix is per-row `verification_status`, not row deletion.
3. **Treated the `category` ArrowInvalid error as material, not noise.** Prior audit trails dismissed it as non-blocking because the JSON payload is intact. That is only true for the current run's output. For governance rollup reporting, the mirror is silently dropping every rule that lacks a `category` field — including BEA RPP and Karpathy AI Exposure. Flagged as MEDIUM-3.
4. **Did NOT require the @staff-engineer to block on framework-level fixes.** MEDIUM-3 and parts of HIGH-1 need framework changes; flagged them as owner="framework" follow-ups rather than per-spec blockers.
5. **Required a live API test run before the next refresh** (MEDIUM-1), not before today's sign-off. The offline mock is sufficient for current Bronze.

## Handoff

- **@staff-engineer:** Read the full audit report. Proceed with Bronze sign-off, but track HIGH-1/2/3 as contract-promotion blockers in `governance/cab-decisions/` or wherever contract state transitions are logged.
- **@dq-rule-writer:** Iterate on HIGH-4 (add verified-value spot-checks for DC/HI/NJ/MS/IA/OK, loosen or delete RAW-BEA-017) before the next refresh.
- **@primary-agent:** Own HIGH-1 fix (catalog name ownership across scripts) and MEDIUM-2 (sha256 file next to the CSV cache).
- **@doc-generator:** Own HIGH-2 (create real BT-100/101/102 entries and update contract + dictionary references).
- **@governance-reviewer:** Confirm that HIGH-3 is tracked as a contract-promotion gate, not a post-hoc footnote.
- **Framework team (no agent):** MEDIUM-3 (make `governance.dq_rule_results.category` nullable) and the deeper HIGH-1 fix (have `get_catalog()` accept an explicit catalog name or stop relying on global `PROJECT_NAME`).

## Artifacts produced

- `governance/adversarial-audits/raw-ingest-bea-rpp.md` — full audit report (severity-ranked risk register, evidence demands, control assessments, recommendations, gate decision)
- `governance/audit-trail/2026-04-10-adversarial-auditor-raw-bea-rpp.md` — this file

---

*End of audit trail.*
