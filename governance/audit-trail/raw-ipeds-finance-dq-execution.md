# Audit Trail — bronze.ipeds_finance DQ Execution

- **Agent:** @dq-engineer
- **Spec:** `full-pipeline-ipeds-finance`
- **Table:** `bronze.ipeds_finance`
- **Snapshot:** `2955168649587464831`
- **Executed at:** 2026-05-01T20:27:37Z
- **Rules file:** `governance/dq-rules/raw-ipeds-finance.json`
- **Runner:** `scripts/dq_execute_ipeds_finance.py` (DuckDB execution against
  Iceberg-loaded Arrow table; SqlCatalog at
  `data/bronze/iceberg_warehouse/catalog.db`)
- **Row count:** 2,675 / 12 columns

## Summary

| Tier | Count | Pass | Fail |
|---|---|---|---|
| P0 | 12 | 12 | 0 |
| P1 | 2 | 2 | 0 |
| **Total** | **14** | **14** | **0** |

Overall pass: **TRUE**. P0 gate: **PASS**. No regressions vs EDA expectations.

## Per-Rule Results

All 14 rules in `raw-ipeds-finance.json` returned `actual = 0` (i.e., zero
violations / single-value violation flag = 0):

- RAW-IPF-001 (volume) — row count 2,675 ∈ [2,500, 3,200]
- RAW-IPF-002 (completeness) — unitid 100% non-null
- RAW-IPF-003 (uniqueness) — 0 duplicate unitids (dedup grain holds)
- RAW-IPF-004 (validity) — report_form ⊆ {F1A, F2, F3}
- RAW-IPF-005/006/007 (validity) — instruction_expenses /
  institutional_support_expenses / endowment_value ≥ 0 where non-null
- RAW-IPF-008 (validity) — total_fte_enrollment > 0 where non-null
- RAW-IPF-009/010 (completeness) — instruction_expenses,
  institutional_support_expenses non-null = 100% (≥ 90% floor)
- RAW-IPF-011 (completeness) — total_fte_enrollment non-null = 97.94%
  (≥ 95% floor; narrow but passes per EDA §12 calibration)
- RAW-IPF-012 (completeness, P1) — endowment_value non-null = 76.0%
  (≥ 60% floor; structural F3 NULL accounted for)
- RAW-IPF-013 (consistency) — exactly 1 distinct fiscal_year (=2023)
- RAW-IPF-014 (validity, P1) — ≥ 1 row with instruction_expenses > $100M
  (269 such rows per EDA — large R1 anchor confirmed)

## Regressions

None. This is the first DQ run against `bronze.ipeds_finance`; no prior baseline
to diff against. Distributions match the EDA at
`governance/eda/full-pipeline-ipeds-finance-raw-eda.md` exactly (form mix
F1A 819 / F2 1,579 / F3 277 = 2,675; FTE non-null 97.94%).

## Gate Decision

**bronze.ipeds_finance is CLEARED for chaos-monkey hardening.** No P0
violations; both P1 rules pass with margin.

## Artifacts

- Scorecard JSON: `governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.json`
- Scorecard MD:   `governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.md`
- Results JSON:   `governance/dq-results/raw-ipeds-finance-20260501T202737Z.json`
- Runner:         `scripts/dq_execute_ipeds_finance.py`
