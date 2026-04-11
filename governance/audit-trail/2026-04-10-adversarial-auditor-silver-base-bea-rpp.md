# Audit Trail — @adversarial-auditor — silver-base-bea-rpp

- **Agent:** @adversarial-auditor
- **Spec:** `docs/specs/silver-base-bea-rpp.md`
- **Date:** 2026-04-10
- **Session type:** Skeptical post-chaos audit
- **Deliverable:** `governance/adversarial-audits/silver-base-bea-rpp.md`

## Inputs read

| Path | Purpose |
|---|---|
| `docs/specs/silver-base-bea-rpp.md` | Primary spec — column list, DQ rule enumeration, spot-check table, Condition 6 scope |
| `src/silver/bea_rpp_transformer.py` | Transformer implementation — verify derivation code matches spec |
| `src/silver/_us_state_reference.py` | Three in-code lookups plus import-time self-check |
| `src/raw/bea_rpp_ingestor.py` | Cross-validate `BeaRppIngestor.VALID_STATE_FIPS` vs Silver lookup key set |
| `scripts/promote_bea_rpp_silver.py` | Runner — verify no project_name override regression (Bronze HIGH-1) |
| `scripts/rebuild_all.py` | Check fresh-clone reproducibility path |
| `tests/silver/test_bea_rpp_transformer.py` | 101 tests — check for tautologies and external-anchor coverage |
| `governance/eda/silver-base-bea-rpp-eda.md` | EDA claims anchor the DQ thresholds |
| `governance/dq-rules/silver-base-bea-rpp.json` | 39 rules — enumerate IDs, parse SIL-BEA-018 / 039 in detail, grep per-column SQL references |
| `governance/dq-results/silver-base-bea-rpp-20260411T003356Z.json` | Latest DQ run — verify 39/39 pass, no errors |
| `governance/chaos-reports/silver-base-bea-rpp-chaos.md` | Chaos cycle + 8 probes + Gap analysis |
| `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py` | How the carve-out for SIL-BEA-018 is actually enforced |
| `governance/data-contracts/silver-base-bea-rpp.yaml` | 11 columns, 39 rules, per-column dq_rules arrays |
| `governance/data-dictionary.json` (`tables/base.bea_rpp`) | Same per-column dq_rules claims, verify consistency with contract |
| `governance/lineage/silver-base-bea-rpp-20260410.json` | OpenLineage — input schemas, transformations, column lineage |
| `governance/audit-trail/2026-04-10-doc-generator-silver-base-bea-rpp.md` | Doc-generator's judgment call #7 on the dq_rules slice assignment |

## Probes executed

1. **Enumerated all 39 DQ rules** with rule_id, dimension, severity, evaluation_mode, chaos_exclude flags. Verified unique IDs and 1:1 rule count with the data contract's claim of 39.
2. **Parsed SIL-BEA-018 and SIL-BEA-039** in detail — verified the SQL, the remediation note, and the metadata markers.
3. **Grepped brightsmith and futureproof-data source** for any code reading `evaluation_mode` / `chaos_exclude` / `production_only`. Zero hits. Metadata is decorative.
4. **Verified the carve-out enforcement path** in `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py`: the chaos runner hard-codes `SHADOW_EXCLUDED_RULE_IDS = frozenset({"SIL-BEA-018"})` and filters post-hoc. Information barrier prevents reading the rules JSON, so this is the only enforcement surface.
5. **Cross-walked per-column `dq_rules`** arrays in the contract and data-dictionary against each rule's SQL column references. Found that 9 of 11 columns have wrong rule mappings and rules SIL-BEA-033 through SIL-BEA-039 are orphaned from any column in both artifacts.
6. **Cross-checked the Silver `_us_state_reference` module** against `BeaRppIngestor.VALID_STATE_FIPS` — the self-check import path is real and correctly deferred to avoid circular imports. Verified Bronze exports the 51-member set expected.
7. **Checked `rebuild_all.py`** for `bea_rpp` / `promote_bea_rpp_silver` / `bea-rpp` — zero hits. BEA RPP is not in the fresh-clone rebuild path.
8. **Reviewed idempotency testing** — the temp-catalog unit test in `tests/silver/test_bea_rpp_transformer.py::TestIntegration::test_idempotent_second_run_zero_new` covers the promote pattern end-to-end but against a fresh warehouse, not the persistent `data/silver/iceberg_warehouse/`.
9. **Counted chaos-report vs rules-file rules** — chaos report says 38, rules file has 39 post-remediation. Chaos report ran before SIL-BEA-039 landed.
10. **Categorized test file for tautologies** — `test_all_values_uppercase_2_letter`, `test_all_regions_are_valid_enum`, `test_census_region_counts`, and the self-check mirror tests all assert against the same dicts they import.
11. **Read the lineage file** (first 160 lines) to confirm it describes the real schemas and transformations rather than boilerplate. It's honest and detailed.
12. **Verified the latest DQ run** — run_id `6667c311` at 2026-04-11T00:33:56Z shows 39/39 PASS, 0 errored, including SIL-BEA-018 PASSing (production mode, not shadow) and SIL-BEA-039 PASSing.

## Findings summary

| # | Severity | Title |
|---|---|---|
| HIGH-1 | HIGH | `chaos_exclude`/`evaluation_mode` metadata is documentation-only; no framework reads it |
| HIGH-2 | HIGH | Per-column `dq_rules` mapping is contiguous-slice hallucination; 7 rules are orphaned from any column |
| HIGH-3 | HIGH | `rebuild_all.py` does not reproduce `base.bea_rpp`; no fresh-clone reproducibility |
| MEDIUM-1 | MEDIUM | Idempotency is tested against a temp catalog, not the persistent warehouse |
| MEDIUM-2 | MEDIUM | USPS abbreviations and Census regions are never cross-checked against an external authoritative source |
| MEDIUM-3 | MEDIUM | Chaos report says 38 rules; rules file has 39 post-remediation |
| MEDIUM-4 | MEDIUM | Test suite has structural tautologies that reduce the 101-test headline |
| LOW-1 | LOW | Contract is `draft` while DQ already passes — correct state; flagged to block flip to `active` until HIGH-2 is fixed |
| LOW-2 | LOW | Promote runner does not self-verify second-run idempotency |

## Verdict

Do not flip the contract to `active` until HIGH-1, HIGH-2, and HIGH-3 are addressed. The substance of the pipeline (transformer, rules, chaos remediation, spot checks, lineage) is solid. The governance surface around the substance has three real drift problems that a regulator would fail, all cheap to fix in a single morning of work.

## Decisions logged

- Audited on the assumption that the chaos-report's information-barrier statement was honored; the chaos runner file corroborates this (no reads of the rules JSON or of dq_runner source).
- Did not re-run DQ rules or chaos probes; relied on the 20260411T003356Z result file and the chaos report.
- Did not score tests by running them (no test execution in this session); classified tautologies by reading assertion bodies.
- Treated the doc-generator's judgment call #7 as a good-faith self-disclosure; the HIGH-2 finding is about the fact that a self-disclosed correctable issue shipped uncorrected, not about the doc-generator lying.

## Next agents

- **@doc-generator** — rewrite per-column `dq_rules` arrays in `governance/data-contracts/silver-base-bea-rpp.yaml` and `governance/data-dictionary.json`, re-derived programmatically from each rule's SQL column references.
- **@dq-rule-writer** — decide whether the `evaluation_mode` / `chaos_exclude` metadata should become enforcing code in brightsmith or be removed entirely; document the decision.
- **@primary-agent** — wire `scripts/rebuild_all.py` to call the BEA RPP Bronze ingest and the Silver promoter. Add a self-idempotency second-run assertion to `scripts/promote_bea_rpp_silver.py`.
- **@governance-reviewer** (post-implementation) — re-review with HIGH-1/2/3 closed before staff sign-off.

## Files modified / created in this session

| Action | Path |
|---|---|
| CREATED | `governance/adversarial-audits/silver-base-bea-rpp.md` |
| CREATED | `governance/audit-trail/2026-04-10-adversarial-auditor-silver-base-bea-rpp.md` (this file) |

*— End of audit trail —*
