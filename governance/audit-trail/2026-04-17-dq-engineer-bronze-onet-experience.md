# Audit Trail: @dq-engineer — Bronze DQ Execution for onet-experience-requirements

**Date:** 2026-04-17T01:20:02Z
**Agent:** @dq-engineer
**Spec:** onet-experience-requirements
**Zone:** Bronze (Raw)
**Run ID:** 650f134b
**Evidence Hash:** 28d12a164be36a3c

---

## Actions Taken

1. Loaded 10 DQ rules from `governance/dq-rules/raw-onet-experience.json` (IDs RAW-ONET-EXP-001 through 010).
2. Attempted Iceberg catalog load path; confirmed `bs:data-analyst` finding that `catalog.load_table("bronze.onet_experience")` does not resolve in the current catalog state.
3. Fell back to reading the Iceberg data parquet directly via DuckDB: `data/bronze/iceberg_warehouse/bronze/onet_experience/data/00000-0-f09a19fa-5466-46ed-a39d-58f4db0dac5e.parquet` (35,998 rows).
4. Materialized the parquet in-memory as `raw.onet_experience` so DQ rule SQL ran unchanged.
5. Executed all 10 rules; all PASSED.
6. Wrote results to `governance/dq-results/raw-onet-experience-20260417-012002.json`.
7. Wrote scorecard to `governance/dq-scorecards/bronze-onet-experience.md`.

---

## Results Summary

- **Total:** 10 rules
- **Passed:** 10
- **Failed:** 0
- **Errored:** 0
- **P0 gate:** PASS (6/6 P0 rules passed)
- **P1 rules:** PASS (4/4 P1 rules passed)

---

## P0 / P1 Failures

None.

---

## Regressions from Prior Runs

None. This is the first DQ execution against `bronze.onet_experience`. Baseline established at run `650f134b`.

---

## Decisions & Rationale

1. **Direct parquet read as fallback for Iceberg catalog miss.** Per spec context, the parquet on disk is authoritative and readable; catalog registration is a separate, known-open governance item. The DQ rule SQL is agnostic to how the data is materialized as long as the `raw.onet_experience` schema-qualified name resolves. Chose DuckDB `read_parquet` over attempting catalog re-registration because (a) scope of this deliverable is Zone 1 DQ execution, not catalog remediation, and (b) the measured data is identical either way.

2. **Filename stamp format `YYYYMMDD-HHMMSS`.** The requesting context specified this format. Note the existing project convention is `YYYYMMDDTHHMMSSZ`; followed the explicit request rather than the convention.

3. **No rule modifications.** All 10 rules passed first-run against real data. No rationale for touching the rules file. @governance-reviewer should validate the rule definitions as locked.

---

## Follow-ups Flagged

- **Catalog re-registration for `bronze.onet_experience`.** Data on disk is correct; only the PyIceberg catalog pointer is missing. Future DQ runs should resolve via `catalog.load_table` rather than direct parquet read.
- **Spec OJ-count correction verification.** The spec originally said OJ=11; EDA corrected to OJ=9; DQ rule RAW-ONET-EXP-010 encodes OJ=9 and passed. Governance should confirm the spec text itself has been updated.

---

## Artifacts Produced

- `scripts/dq_execute_onet_experience.py` (executor)
- `governance/dq-results/raw-onet-experience-20260417-012002.json` (results)
- `governance/dq-scorecards/bronze-onet-experience.md` (scorecard)
- `governance/audit-trail/2026-04-17-dq-engineer-bronze-onet-experience.md` (this file)

---

*Logged by @dq-engineer*
