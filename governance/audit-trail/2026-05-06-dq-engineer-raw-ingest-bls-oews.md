# dq-engineer audit log: raw-ingest-bls-oews

**Date:** 2026-05-06 / 2026-05-07T03:05:58Z (UTC execution timestamp)
**Agent:** @dq-engineer
**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Run ID:** 4edd3cea

## Actions taken

1. Reviewed three rule files queued for this spec:
   - `governance/dq-rules/raw-ingest-bls-oews.json` — 10 P0 rules, target `bronze.bls_oews`
   - `governance/dq-rules/silver-base-bls-oews.json` — 11 P0 rules, target `base.bls_oews` (table not yet created)
   - `governance/dq-rules/gold-occupation-profiles-bls-oews.json` — 4 rules (3 P0, 1 P1), target `consumable.occupation_profiles` OEWS columns (not yet enriched)
2. Approved all 10 PROPOSED Bronze rules via `dq_runner approve RAW-OEWS-001 .. RAW-OEWS-010` so they could be executed.
3. Executed Bronze rules with `uv run python -m brightsmith.infra.dq_runner run --spec raw-ingest-bls-oews`.
4. Verified results JSON at `governance/dq-results/raw-ingest-bls-oews-20260507T030558Z.json`.
5. Pulled supporting evidence from `bronze.bls_oews` directly via PyIceberg + DuckDB: row count, suppression list, capped count, spot-check medians.
6. Generated and enriched scorecard at `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md`.

## Results summary

| Zone | Rules | Executed | Passed | Failed | Deferred |
|------|-------|----------|--------|--------|----------|
| Bronze (`bronze.bls_oews`) | 10 | 10 | 10 | 0 | 0 |
| Silver (`base.bls_oews`) | 11 | 0 | — | — | 11 (table not created) |
| Gold (`consumable.occupation_profiles` OEWS cols) | 4 | 0 | — | — | 4 (not enriched) |
| **Total** | **25** | **10** | **10** | **0** | **15** |

**P0 gate (Bronze): PASS** — zero violations across all 10 rules. No regressions (no prior run; first execution).

## Decisions

- **Approve & execute Bronze rules now.** The Bronze table is landed, the EDA validates the rule set, and downstream zones depend on this gate clearing. Approval and execution proceeded together because there is no prior run to compare against.
- **Defer Silver and Gold rules.** Their target tables do not yet exist. Executing now would either error out or trivially "pass" against missing data, which would corrupt the audit trail. They are explicitly marked DEFERRED in the scorecard with the exact follow-up commands.
- **Do not escalate the governance-DB sync warning.** The runner emitted a non-fatal warning when syncing rule results into the governance metadata DB (`Column 'category' is declared non-nullable but contains nulls` from PyArrow). The rule executions themselves succeeded against the live Iceberg table and produced correct results in the JSON results file. The warning relates to the metadata category field being unpopulated in the rule JSON — a framework-level concern, not a data-quality issue. Documented in the scorecard's Operational Notes section.

## Verdict

**ALL_PASSED (Bronze).** No P0 failures, no P1 failures, no calibration issues. Spec workflow may proceed to Silver dispatch.

## Artifacts produced

- `governance/dq-results/raw-ingest-bls-oews-20260507T030558Z.json` — raw rule results
- `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md` — human-readable scorecard
- `governance/audit-trail/2026-05-06-dq-engineer-raw-ingest-bls-oews.md` — this file

## Follow-ups

1. After Silver dispatch creates `base.bls_oews`: run `uv run python -m brightsmith.infra.dq_runner approve SLV-OEWS-001 .. SLV-OEWS-011` then `... run --spec silver-base-bls-oews`.
2. After Gold dispatch enriches `consumable.occupation_profiles` with the OEWS percentile columns: run `... approve GLD-OP-OEWS-001 .. GLD-OP-OEWS-004` then `... run --spec gold-occupation-profiles-bls-oews`.
3. Framework maintainer: investigate the `category` non-nullable column issue in the governance-DB sync path so DQ runs cleanly without the PyArrow warning.
