# DQ Scorecard: silver-base-college-scorecard-institution (post-promote)

**Spec:** silver-base-college-scorecard-institution
**Zone:** Silver (Base)
**Table:** `base.college_scorecard_institution`
**Executed:** 2026-04-16T15:23:05Z
**Run ID:** `7389603f`
**Evidence Hash:** `a4396c5f21a42be8`
**Agent:** Claude Code (Opus 4.6)
**Upstream:** `bronze.college_scorecard_institution` (filter PREDDEG=3 OR ICLEVEL=1, dedup on UNITID)
**Source Snapshot:** `Most-Recent-Cohorts-Institution_04172025.zip` (fallback URL; primary URL returned 404)
**Closes advisory:** [A3 — in-memory DQ must be re-executed against the real Silver Iceberg table](../reviews/silver-base-college-scorecard-institution-post-review.md)

---

## Overall Score: 23 / 23 (100%)

- **P0 Gate:** PASS (12 / 12 P0 rules)
- **P1 Rules:** PASS (9 / 9)
- **P2 Rules:** PASS (2 / 2)

Parity with the pre-promote in-memory run (`04635d71`, 23/23) is confirmed against the real Iceberg table — no rule flipped status when moved from in-memory DuckDB to the materialized `base.college_scorecard_institution` Iceberg table.

---

## Execution Method

The advisory `A3` from the Silver post-review required re-executing all 23 Silver DQ rules against the **real** Silver Iceberg table rather than against an in-memory DuckDB reconstruction of the Silver transformer's output. This scorecard reports that re-execution.

1. Bronze ingestor runner (`scripts/ingest_college_scorecard_institution.py`) downloaded the fallback ZIP, applied the `PREDDEG=3 OR ICLEVEL=1` filter + UNITID dedup, and wrote **3,039** rows to `bronze.college_scorecard_institution` in the shared Brightsmith Iceberg catalog (snapshot `8416909008952105360`).
2. Silver promote runner (`scripts/promote_college_scorecard_institution_silver.py`) read 3,039 rows from Bronze via `read_with_duckdb(table)`, applied `transform_row` (produced 0 skipped rows), and wrote **3,039** rows to `base.college_scorecard_institution` in the Silver Iceberg warehouse (snapshot `2618048705278132549`). Re-running produced **0 new rows, 3,039 skipped** — confirming idempotency.
3. Silver DQ runner (`scripts/dq_execute_silver_csi_iceberg.py`) loaded the Silver Iceberg table via `read_with_duckdb`, materialized it as a DuckDB view with the same fully-qualified name the rule SQL expects (`base.college_scorecard_institution`), and executed all 23 `SLV-CSI-*` rules verbatim from `governance/dq-rules/silver-base-college-scorecard-institution.json`.

Neither the ingestor, the transformer, nor any DQ rule was modified for this run.

---

## Table Snapshots in the Catalog

| Catalog | Path | Table | Rows | Snapshot ID |
|---------|------|-------|-----:|-------------|
| Bronze | `data/bronze/iceberg_warehouse` | `bronze.college_scorecard_institution` | 3,039 | `8416909008952105360` |
| Silver | `data/silver/iceberg_warehouse` | `base.college_scorecard_institution` | 3,039 | `2618048705278132549` |

Catalog name for both: `brightsmith` (framework default — matches the BEA-RPP remediation so `dq_runner` and downstream readers resolve the same namespace).

---

## Rule Results

### P0 Rules (Hard Gate — 12 / 12 PASS)

| Rule ID | Name | Status | Actual | Threshold |
|---------|------|--------|-------:|-----------|
| SLV-CSI-001 | Row count exact match to Bronze (3,039 ± 5) | PASS | 0 | `result = 0` |
| SLV-CSI-002 | `record_id` uniqueness | PASS | 0 | `result_count = 0` |
| SLV-CSI-003 | `unitid` uniqueness and non-null | PASS | 0 | `result = 0` |
| SLV-CSI-004 | `record_id` non-null | PASS | 0 | `result_count = 0` |
| SLV-CSI-005 | `institution_control` valid enum values | PASS | 0 | `result_count = 0` |
| SLV-CSI-006 | `institution_control` 100% non-null | PASS | 0 | `result_count = 0` |
| SLV-CSI-007 | `net_price_annual <= cost_of_attendance_annual` (both non-null) | PASS | 0 | `result_count = 0` |
| SLV-CSI-008 | `net_price_4yr = net_price_annual * 4` (IEEE-754 exact) | PASS | 0 | `result_count = 0` |
| SLV-CSI-009 | `cost_of_attendance_4yr = cost_of_attendance_annual * 4` (IEEE-754 exact) | PASS | 0 | `result_count = 0` |
| SLV-CSI-010 | `net_price_annual` non-null coverage ≥ 70% overall | PASS | 0 | `result = 0` |
| SLV-CSI-011 | `cost_of_attendance_annual` non-null coverage ≥ 70% overall | PASS | 0 | `result = 0` |
| SLV-CSI-018 | `state_abbr` matches `^[A-Z]{2}$` | PASS | 0 | `result_count = 0` |

### P1 Rules (Warning — 9 / 9 PASS)

| Rule ID | Name | Status | Actual | Threshold |
|---------|------|--------|-------:|-----------|
| SLV-CSI-012 | Public (control=1) `net_price_annual` coverage ≥ 85% | PASS | 0 | `result = 0` |
| SLV-CSI-013 | Private nonprofit (control=2) `net_price_annual` coverage ≥ 65% | PASS | 0 | `result = 0` |
| SLV-CSI-015 | Quintile span monotonicity (`net_price_q1 <= net_price_q5`) | PASS | 46 | `result_count <= 50` |
| SLV-CSI-016 | `net_price_annual` range [-$5,000, $80,000] | PASS | 0 | `result_count = 0` |
| SLV-CSI-017 | `cost_of_attendance_annual` range [$5,000, $100,000] | PASS | 0 | `result_count = 0` |
| SLV-CSI-019 | `tuition_in_state` range [$0, $70,000] | PASS | 0 | `result_count = 0` |
| SLV-CSI-020 | `tuition_out_of_state` range [$0, $75,000] | PASS | 0 | `result_count = 0` |
| SLV-CSI-021 | `room_board_on_campus` range [$1,000, $30,000] | PASS | 0 | `result_count = 0` |
| SLV-CSI-022 | `room_board_off_campus` range [$1,000, $40,000] | PASS | 0 | `result_count = 0` |

### P2 Rules (Observation — 2 / 2 PASS)

| Rule ID | Name | Status | Actual | Threshold |
|---------|------|--------|-------:|-----------|
| SLV-CSI-014 | Private for-profit (control=3) `net_price_annual` coverage ≥ 50% | PASS | 0 | `result = 0` |
| SLV-CSI-023 | `books_supplies` range [$0, $10,000] | PASS | 0 | `result_count = 0` |

---

## Supplementary Stats (from the real Iceberg table)

| Metric | Value |
|--------|-------|
| Total rows | 3,039 |
| Distinct `unitid` | 3,039 |
| Distinct `record_id` | 3,039 |
| `institution_control` = Public | 867 |
| `institution_control` = Private nonprofit | 1,754 |
| `institution_control` = Private for-profit | 418 |
| `net_price_annual` non-null coverage | 73.48 % |
| `cost_of_attendance_annual` non-null coverage | 73.48 % |
| `net_price_q1 > net_price_q5` violations (SLV-CSI-015) | 46 |

Every supplementary stat matches the pre-promote in-memory numbers exactly (row count, record_id / unitid uniqueness, control distribution, 73.48% coverage, 46 quintile inversions) — the transformer, the promote step, and the real Iceberg table all agree.

---

## Parity With Pre-Promote Run

| Metric | Pre-promote (in-memory) | Post-promote (Iceberg) | Delta |
|--------|------------------------:|------------------------:|------:|
| Total rules executed | 23 | 23 | 0 |
| Rules passed | 23 | 23 | 0 |
| P0 gate | PASS | PASS | — |
| Row count | 3,039 | 3,039 | 0 |
| SLV-CSI-015 actual | 46 | 46 | 0 |

---

## Artifacts

| Artifact | Path |
|----------|------|
| Bronze ingest runner | `scripts/ingest_college_scorecard_institution.py` |
| Silver promote runner | `scripts/promote_college_scorecard_institution_silver.py` |
| Bronze DQ runner (Iceberg) | `scripts/dq_execute_csi_iceberg.py` |
| Silver DQ runner (Iceberg) | `scripts/dq_execute_silver_csi_iceberg.py` |
| Bronze DQ result (Iceberg) | `governance/dq-results/raw-ingest-college-scorecard-institution-iceberg-20260416T152220Z.json` |
| Silver DQ result (Iceberg) | `governance/dq-results/silver-base-college-scorecard-institution-iceberg-20260416T152305Z.json` |

---

## Advisory A3: CLOSED

Advisory A3 from `governance/reviews/silver-base-college-scorecard-institution-post-review.md` required re-executing all 23 Silver DQ rules against the real `base.college_scorecard_institution` Iceberg table once it was materialized. This scorecard is that re-execution:

- The Silver Iceberg table exists in the catalog at `data/silver/iceberg_warehouse` under catalog name `brightsmith`.
- All 23 rules executed against the real table via `read_with_duckdb(table)`.
- 23 / 23 PASS; P0 gate PASS; zero regressions vs. the pre-promote run.

**A3 is CLOSED.** Gold pre-review for this spec is unblocked with respect to Silver data-quality parity.

Advisory A4 (`test_transform_end_to_end`) is tracked separately and is not addressed by this scorecard.

---

## Deviations / Surprises

- The primary Department of Education download URL (`ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Institution.csv`) returned HTTP 404. The ingestor's built-in fallback to the `scorecard.network` mirror worked as designed; no change to the ingestor was needed and no data was lost. This is a one-line `WARNING` in the runner log, not a defect.
- A benign `AttributeError: 'Table' object has no attribute 'identifier'` was logged by `brightsmith.infra.promote._emit_lineage` during the Silver promote. The promote itself completed successfully (3,039 rows, snapshot `2618048705278132549`); only the lineage-emission side-effect failed. This is a framework-side bug in `brightsmith` that does not affect the promoted table or any DQ rule. It is outside the scope of this spec's advisory A3.
