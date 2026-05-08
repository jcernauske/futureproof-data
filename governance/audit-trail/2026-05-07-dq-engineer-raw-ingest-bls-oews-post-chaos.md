# dq-engineer audit log: raw-ingest-bls-oews (post-chaos re-execution)

**Date:** 2026-05-07T03:20:19Z (UTC execution timestamp)
**Agent:** @dq-engineer
**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Run ID:** 646f3c24
**Prior run:** 4edd3cea (2026-05-07T03:05:58Z) — see `2026-05-06-dq-engineer-raw-ingest-bls-oews.md`
**Trigger:** @dq-rule-writer added two new rules to `governance/dq-rules/raw-ingest-bls-oews.json` (rule count grew from 10 to 12) to close a chaos-monkey gap on scenario S10. Re-executing only Bronze rules — Silver/Gold tables still don't exist.

## Actions taken

1. Read updated `governance/dq-rules/raw-ingest-bls-oews.json` and confirmed the two new rules:
   - **RAW-OEWS-011** (P0, Validity): "All non-null annual wage values are >= 0 (non-negative wage guard)" — guards against chaos S10 (negative wage injection that satisfies monotonicity).
   - **RAW-OEWS-012** (P1, Volume): "wage_capped=TRUE row count in [5, 80] (top-code-floor drift detector)" — guards against $239,200 ceiling shift and `#` sentinel parser regression.
   Both entered as `proposed` on 2026-05-06T22:00:00Z.
2. Approved both proposed rules:
   ```
   uv run python -m brightsmith.infra.dq_runner approve RAW-OEWS-011 RAW-OEWS-012
   → RAW-OEWS-011: → approved
   → RAW-OEWS-012: → approved
   ```
3. Executed all Bronze rules:
   ```
   uv run python -m brightsmith.infra.dq_runner run --spec raw-ingest-bls-oews
   → Run 646f3c24 complete: Total: 12 | Passed: 12 | Failed: 0 | P0 gate: PASS
   ```
4. Verified results JSON at `governance/dq-results/raw-ingest-bls-oews-20260507T032019Z.json` — all 12 rules show `passed=true, violations=0`.
5. Independently cross-checked the two new rules against `bronze.bls_oews` via PyIceberg + DuckDB:
   - Negative wages across all 6 annual columns: **0 / 831** (RAW-OEWS-011 PASS).
   - wage_capped=TRUE count: **45** (RAW-OEWS-012 PASS, inside [5, 80], matches EDA exactly).
   - Smallest non-null p10: $18,500. Smallest non-null median: $30,160. Confirms no near-zero floor that could foreshadow a future RAW-OEWS-011 violation.
6. Updated `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md`:
   - Header rewritten for post-chaos run (run ID, results file, rule count 12, note explaining post-chaos additions).
   - Added rows for RAW-OEWS-011 and RAW-OEWS-012 to the execution-results table, both marked **POST-CHAOS ADDITION**.
   - Updated priority summary: 11 P0 + 1 P1 = 12 total, all passing.
   - Added "Comparison to Previous Run" delta table (10→12 rules, both new pass, no regressions).
   - Added dedicated "Post-Chaos Additions" section explaining why each rule was added and its real-data result.
   - Updated gate-status and verdict sections.

## Results summary

| Zone | Rules | Executed | Passed | Failed | Deferred |
|------|-------|----------|--------|--------|----------|
| Bronze (`bronze.bls_oews`) — prior run | 10 | 10 | 10 | 0 | 0 |
| Bronze (`bronze.bls_oews`) — this run | 12 | 12 | 12 | 0 | 0 |
| Silver (`base.bls_oews`) | 11 | 0 | — | — | 11 (table not created) |
| Gold (`consumable.occupation_profiles` OEWS cols) | 4 | 0 | — | — | 4 (not enriched) |

**P0 gate (Bronze): PASS** — zero violations across all 11 Bronze P0 rules (10 original + RAW-OEWS-011).
**P1 rules (Bronze): PASS** — RAW-OEWS-012 (the only P1) observed 45 capped rows inside [5, 80] window.

## Regression analysis vs. prior run (4edd3cea)

- All 10 rules from the prior run executed again with identical results (0 violations each). Same Iceberg snapshot, same 831 rows.
- 2 new rules added, both pass on first execution against real data with the EDA-predicted values.
- No regressions detected.
- No rule calibration changes requested or made.

## Verdict

**ALL_PASSED (Bronze)** — `bronze.bls_oews` is clean and the chaos-driven structural gap is now closed. No P0 failures, no P1 failures, no escalation needed. Both new rules confirmed correct on real data on first execution. Spec workflow may continue to the Silver dispatch when that table is ready.

## Files touched

- Read: `governance/dq-rules/raw-ingest-bls-oews.json` (now 12 rules)
- Read: `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md` (prior version)
- Wrote: `governance/dq-results/raw-ingest-bls-oews-20260507T032019Z.json` (via `dq_runner run`; 12 results)
- Updated: `governance/dq-rules/raw-ingest-bls-oews.json` (`approve` advanced status of RAW-OEWS-011 and RAW-OEWS-012 from `proposed` to `approved`; first successful run auto-advanced to `active`)
- Updated: `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md` (post-chaos rerun results + delta to prior run)
- Wrote: `governance/audit-trail/2026-05-07-dq-engineer-raw-ingest-bls-oews-post-chaos.md` (this file)

## Operational note

The same non-fatal `Column 'category' is declared non-nullable but contains nulls` warning was emitted from the governance-DB sync path (rule definitions in this file have no `category` populated). Identical to the prior run; does not affect rule execution, the on-disk results JSON, or the P0 gate verdict. Flagged for the framework maintainer; safe to ignore for this scorecard.
