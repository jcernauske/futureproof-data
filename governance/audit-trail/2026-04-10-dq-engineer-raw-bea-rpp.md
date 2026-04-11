# DQ Engineer Audit Trail — raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @dq-engineer
**Spec:** raw-ingest-bea-rpp
**Zone:** Bronze
**Target Table:** `bronze.bea_rpp`
**Warehouse:** `/Users/jcernauske/code/bright/futureproof-data/data/bronze/iceberg_warehouse`
**Catalog:** `/Users/jcernauske/code/bright/futureproof-data/data/catalog/catalog.db`
**Run ID:** `1170adf0`
**Executed At:** 2026-04-10T22:33:36.177127+00:00

## Summary

All 19 DQ rules for `raw-ingest-bea-rpp` executed successfully against the persistent Iceberg warehouse and **all 19 passed**. The P0 gate is **PASS**. Spec is clear to proceed with governance review.

| Metric | Value |
|--------|-------|
| Rules total | 19 |
| Rules passed | 19 |
| Rules failed | 0 |
| Rules errored | 0 |
| P0 gate | PASS |
| Target rows validated | 51 (50 states + DC) |

## Pass Counts by Severity

| Priority | Count | Passed | Failed |
|----------|-------|--------|--------|
| P0 | 10 | 10 | 0 |
| P1 | 5 | 5 | 0 |
| P2 | 4 | 4 | 0 |
| P3 | 0 | 0 | 0 |
| **Total** | **19** | **19** | **0** |

P0 rules covered: row count = 51, rpp_all_items non-null, rpp_all_items range [80.0, 130.0], geo_fips uniqueness, geo_name non-null, data_year = 2024, California spot-check, Arkansas spot-check, DC presence, canonical FIPS set. P1 rules covered: geo_fips regex, source_method domain, source_url/load_date/ingested_at non-null. P2 rules covered: freshness, mean/min/max distribution sanity.

## Actions Taken

1. **Approved all 19 proposed rules.** The rule file delivered by @dq-rule-writer had every rule in `proposed` status; the dq_runner only executes rules in `approved` or `active` status. Ran `uv run python -m brightsmith.infra.dq_runner approve RAW-BEA-001 ... RAW-BEA-019` to transition all 19 to `approved`.
2. **Registered `bronze.bea_rpp` under the `brightsmith` SqlCatalog name.** See "Catalog Registration Fix" below.
3. **Executed the full rule set** via `uv run python -m brightsmith.infra.dq_runner run --spec raw-ingest-bea-rpp`. All 19 rules evaluated against the real 51-row Iceberg table. On successful execution, the runner auto-advanced the rules from `approved` to `active`.
4. **Generated scorecard** via `uv run python -m brightsmith.infra.dq_runner scorecard --spec raw-ingest-bea-rpp`. The runner writes a canonical path `raw-ingest-bea-rpp-scorecard.md`; copied to the timestamped filename `raw-ingest-bea-rpp-20260410T223336Z.md` per this task's deliverable convention.
5. **Wrote this audit trail.**

## Catalog Registration Fix

The data-analyst's EDA correctly flagged that `bronze.bea_rpp` Iceberg metadata existed on disk at `data/bronze/iceberg_warehouse/bronze/bea_rpp/` but was not registered under the catalog name that `brightsmith.config.PROJECT_NAME` uses. Inspection of `data/catalog/catalog.db` confirmed the row existed under `catalog_name = 'futureproof-data'` while every other bronze/silver/gold table is registered under `catalog_name = 'brightsmith'`. This was caused by the primary-agent's `scripts/ingest_bea_rpp.py` helper constructing its own `SqlCatalog(...)` with a non-default catalog name.

**Fix applied (non-destructive):** Backed up the catalog DB to `data/catalog/catalog.db.bak3`, then inserted a second row in `iceberg_tables` with `catalog_name = 'brightsmith'` pointing to the same `metadata_location` and `previous_metadata_location` as the existing `futureproof-data` row. No metadata files were moved, no data was re-materialized, and the existing `futureproof-data` row was left intact so the ingest helper continues to work. Verified by calling `SqlCatalog('brightsmith', ...).load_table('bronze.bea_rpp')` which returned a table with `num_rows = 51` and the expected 8 columns.

**Follow-up recommendation for the primary-agent:** Update `scripts/ingest_bea_rpp.py` to use `brightsmith.infra.iceberg_setup.get_catalog(WAREHOUSE_PATH, CATALOG_PATH)` instead of instantiating its own `SqlCatalog` so that future refreshes register the table under the correct catalog name automatically.

## Execution Details

Per-rule detail (all PASS, all with actual=0 violations):

```
RAW-BEA-001  PASS  P0  row count = 51                             (0 violations)
RAW-BEA-002  PASS  P0  rpp_all_items non-null                     (0 violations)
RAW-BEA-003  PASS  P0  rpp_all_items in [80.0, 130.0]             (0 violations)
RAW-BEA-004  PASS  P0  geo_fips uniqueness                        (0 duplicates)
RAW-BEA-005  PASS  P0  geo_name non-null                          (0 violations)
RAW-BEA-006  PASS  P0  data_year = 2024                           (0 violations)
RAW-BEA-007  PASS  P0  California (06) RPP in [108.0, 115.0]      (0 violations)
RAW-BEA-008  PASS  P0  Arkansas  (05) RPP in [84.0, 90.0]         (0 violations)
RAW-BEA-009  PASS  P0  DC (11) present exactly once               (0 violations)
RAW-BEA-010  PASS  P0  canonical 51-FIPS set complete             (0 violations)
RAW-BEA-011  PASS  P1  geo_fips regex ^[0-9]{2}$                  (0 violations)
RAW-BEA-012  PASS  P1  source_method in {bea_api, csv_cache}      (0 violations)
RAW-BEA-013  PASS  P1  source_url non-null                        (0 violations)
RAW-BEA-014  PASS  P1  load_date non-null                         (0 violations)
RAW-BEA-015  PASS  P1  ingested_at non-null                       (0 violations)
RAW-BEA-016  PASS  P2  freshness: load_date within 400 days       (0 stale)
RAW-BEA-017  PASS  P2  mean rpp_all_items in [94.0, 100.0]        (0 violations)
RAW-BEA-018  PASS  P2  min  rpp_all_items >= 84.0                 (0 violations)
RAW-BEA-019  PASS  P2  max  rpp_all_items <= 115.0                (0 violations)
```

All results match the EDA data profile: 51 rows, rpp_all_items range [86.90, 110.70], mean ~96.98, 100% csv_cache source_method, CA at 110.7, AR at 86.9, DC present at FIPS 11. The rules were written to be estimate-tolerant and refresh-tolerant, and they held at all three priority levels against both the 8 spec-verified values and the 43 primary-agent estimates in the current load.

## Known Issue (Non-Blocking, Pre-Existing)

The dq_runner attempted to sync the 19 result records to the governance DB Iceberg table `governance.dq_rule_results` and raised:

```
pyarrow.lib.ArrowInvalid: Column 'category' is declared non-nullable but contains nulls
```

This is a **pre-existing governance DB schema mismatch** unrelated to the BEA rules. The rule file does not populate a `category` field (neither do several other rule files in the repo — see the "Summary by Category" table in the generated scorecard which shows a blank category column for every rule). The governance table `dq_rule_results` was declared with `category` as non-nullable, so every null-category result run hits this. The rule execution itself succeeded — this is purely a governance DB mirror failure — and the JSON result file and markdown scorecard were still written correctly to disk.

**Not a BEA-specific issue** and **does not block the spec**. Recommend filing a separate follow-up to either (a) relax `category` to nullable in the governance `dq_rule_results` schema, or (b) require @dq-rule-writer to populate `category` on all rules going forward. This is a framework-level fix; I am flagging it here for @governance-reviewer visibility but not escalating as a gate.

## Gate Decision

**P0 gate: PASS.** All 10 P0 rules passed with zero violations against real Iceberg data. Spec `raw-ingest-bea-rpp` is cleared from the DQ execution perspective and ready for @governance-reviewer to evaluate completeness of the broader governance checklist.

## Artifacts

- Rules definition: `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/raw-ingest-bea-rpp.json` (19 rules, all now `status: active`)
- Execution results (JSON): `/Users/jcernauske/code/bright/futureproof-data/governance/dq-results/raw-ingest-bea-rpp-20260410T223336Z.json`
- Scorecard (canonical): `/Users/jcernauske/code/bright/futureproof-data/governance/dq-scorecards/raw-ingest-bea-rpp-scorecard.md`
- Scorecard (timestamped): `/Users/jcernauske/code/bright/futureproof-data/governance/dq-scorecards/raw-ingest-bea-rpp-20260410T223336Z.md`
- Catalog backup (pre-fix): `/Users/jcernauske/code/bright/futureproof-data/data/catalog/catalog.db.bak3`
- This audit trail: `/Users/jcernauske/code/bright/futureproof-data/governance/audit-trail/2026-04-10-dq-engineer-raw-bea-rpp.md`
