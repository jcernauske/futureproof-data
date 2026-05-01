# Logical Model: raw-eada

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §4
**Conceptual model:** [raw-eada-conceptual.md](raw-eada-conceptual.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Logical Schema

The Bronze zone is a flattened representation of the conceptual `Athletic Financial Report` entity — one logical row per `(Institution, Reporting Cycle)`. The five conceptual entities (Institution, Athletic Financial Report, Reporting Cycle, Monetary Measurement, Ingest Provenance) collapse onto a single 10-attribute table because Bronze policy is "land what the source publishes, do not normalize."

### Attributes

| Attribute | Conceptual Entity | Role | Logical Type | Required | Source-System Origin |
|-----------|-------------------|------|--------------|----------|----------------------|
| `unitid` | Institution | Primary identifier (natural key + dedup grain) | Long Integer | Yes | EADA `unitid` (lowercase, NOT `UNITID`) |
| `institution_name` | Institution | Display name | Text | Yes | EADA `institution_name` (lowercase, NOT `INSTNM`) |
| `reporting_year` | Reporting Cycle | Academic-year-start of the EADA cycle | Integer (year) | Yes | Pinned by ingestor from cache filename (no in-row column) |
| `total_athletic_expenses` | Monetary Measurement | Institution grand-total athletic expenses (USD) | Decimal Money | No | EADA `GRND_TOTAL_EXPENSE` |
| `total_athletic_revenue` | Monetary Measurement | Institution grand-total athletic revenue (USD) | Decimal Money | No | EADA `GRND_TOTAL_REVENUE` |
| `recruiting_expenses` | Monetary Measurement | Institution grand-total recruiting expenses (USD) | Decimal Money | No | EADA `RECRUITEXP_TOTAL` (NOT `RECRUITEXP_TOTAL_TOTAL`) |
| `source_url` | Ingest Provenance | Provenance — where the row was downloaded from | Text (URL) | Yes | Stamped by ingestor; constant per batch (`https://ope.ed.gov/athletics/`) |
| `source_method` | Ingest Provenance | Provenance — fetch path used | Text (enum-like) | Yes | Stamped by ingestor; current value `csv_cache` |
| `ingested_at` | Ingest Provenance | Provenance — UTC wall-clock of the Bronze write | Timestamp | Yes | Stamped by ingestor; identical across all rows in a batch |
| `load_date` | Ingest Provenance | Provenance — UTC calendar date of the load | Date | Yes | Stamped by ingestor; identical across all rows in a batch |

### Keys

| Key Type | Columns | Notes |
|----------|---------|-------|
| Natural key (per-cycle) | `unitid` | One row per institution per reporting cycle. Within a single `reporting_year` partition, `unitid` is unique (RAW-EAD-003, P0). |
| Dedup grain | `[unitid]` | Declared by the ingestor as the dedup grain for idempotent re-runs of a single cycle. |
| Foreign keys (downstream) | `unitid` → `base.ipeds_finance.unitid`, `bronze.college_scorecard_institution.unitid`, `consumable.career_outcomes.unitid` | Bronze does not enforce FK integrity; consumers do. |

### Derivations and Defaults

The Bronze zone performs **no derivations**. All values are either passthroughs from EADA, pinned ingestor constants (`source_url`, `source_method`, `reporting_year`), or system clocks (`ingested_at`, `load_date`). Every derivation lives downstream:

- `athletic_spend_per_fte`, `athletic_revenue_per_fte`, `recruiting_per_fte`, `athletic_subsidy_ratio` → all derived at `base.eada` (Silver)
- `aura_score`, `aura_score_continuous`, `aura_score_version`, `coverage_tier` → all derived at `consumable.institution_aura` (Gold)

### Cardinality

- 2,040 rows in the current load (academic year 2022–23 cycle).
- Expected band: 1,800–2,300 per cycle (RAW-EAD-001, P0). The lower bound covers historical EADA cohort sizes since the 2014 reporting expansion; the upper bound trips if per-team rows leak from `Schools.xlsx`.
- Future cycles append. The table is partition-friendly on `reporting_year`, but the current Bronze write is single-cycle (no partition spec).

---

## Constraints (Logical)

| Constraint | Type | Source |
|------------|------|--------|
| `unitid IS NOT NULL` for every row | Total | RAW-EAD-002 (P0) |
| `unitid` is unique within a single `reporting_year` | Uniqueness | RAW-EAD-003 (P0) |
| `total_athletic_expenses ≥ 0` where non-null | Range | RAW-EAD-004 (P0) |
| `total_athletic_revenue ≥ 0` where non-null | Range | RAW-EAD-005 (P0) |
| `recruiting_expenses ≥ 0` where non-null (zeros are valid) | Range | RAW-EAD-006 (P0) |
| `total_athletic_expenses` non-null ≥ 99% (EDA-tightened from spec's 95%) | Completeness | RAW-EAD-007 (P0) |
| `total_athletic_revenue` non-null ≥ 99% (EDA-tightened from spec's 95%) | Completeness | RAW-EAD-008 (P0) |
| `recruiting_expenses` non-null ≥ 99% (EDA-tightened from spec's 80%) | Completeness | RAW-EAD-009 (P1) |
| `COUNT(DISTINCT reporting_year) == 1` per load | Consistency | RAW-EAD-010 (P0) |
| ≥1 row with `total_athletic_expenses > $100M` (D1 anchor) | Plausibility | RAW-EAD-011 (P1) |
| `|row_count − distinct(unitid)| ≤ max(1, 1% of distinct unitid)` | Conservation (per-team-leak tripwire) | RAW-EAD-012 (P0) |

---

## Data Quality Summary

- 12/12 DQ rules PASS against the 2022–23 cycle (scorecard `governance/dq-scorecards/raw-eada-20260501T040238Z.{json,md}`).
- Adversarial chaos (5-cycle + 6 targeted): 6/6 caught (`governance/chaos-reports/raw-eada-chaos.md`).
- Independent adversarial audit: CLEAR (`governance/adversarial-audits/raw-eada-bronze-audit.md`).
- PII scan: NONE (`governance/pii-scans/raw-eada-pii-scan.md`).
- Entity resolution: N/A (single-source, single-grain) (`governance/entity-resolution/raw-eada-er-assessment.md`).
- Temporal modeling: N/A (single-cycle snapshot; no SCD2) (`governance/temporal-models/raw-eada-temporal-assessment.md`).

---

## Modeling Decisions (Logical Layer)

1. **One flat row per (institution, cycle).** No normalization of `Monetary Measurement` into a long-form `(unitid, reporting_year, measurement_name, value)` shape. The wide form matches EADA's published shape and is what every downstream consumer expects (Silver derivations operate on the three columns side by side; long-form would force a pivot at every read site).

2. **`reporting_year` as Integer, not Date.** The cycle is a discrete academic year, not a calendar date. Stamping it as the academic-year-start integer (e.g., 2022 for the 2022–23 cycle) matches the College Scorecard and IPEDS Finance conventions used elsewhere in the pipeline and keeps year-over-year comparisons trivial.

3. **Monetary measurements as `Decimal Money` logically, `DOUBLE` physically.** EADA publishes whole-dollar values, but the upstream codebook does not promise integer-only output (some derived fields elsewhere in the file carry cents). Using `DOUBLE` at Iceberg matches the sibling `bronze.college_scorecard_institution` cost columns. The "Decimal Money" logical type is documentary — it tells consumers the unit is USD, not unitless.

4. **Provenance fields are `Required: Yes` even though they are stamped, not sourced.** Bronze policy: every row carries provenance. A NULL `source_url` or `ingested_at` would mean the row was bypassed the ingestor entirely (e.g., manual SQL append) and is a governance violation regardless of payload validity.

5. **No `coach_count`, `student_athlete_count`, `EFTotalCount`, `classification_name` columns.** EDA flagged that EADA carries an in-file `EFTotalCount` (12-month enrollment count from IPEDS) that could replace the `base.ipeds_finance` FTE join — but in-scope-of-this-Bronze-spec is only the three monetary grand totals. The FTE source decision is a Silver-zone concern and is logged in the EDA report for the semantic-modeler. Pulling `EFTotalCount` into Bronze would be scope creep against spec §3.

6. **No SCD2.** Bronze keeps the latest single-cycle snapshot. Multi-cycle history is a future-amendment concern (would require a partition spec on `reporting_year`).

---

## Scope and Boundaries

- This logical model covers `raw.eada` (Iceberg `bronze.eada`) only.
- Derivations (`*_per_fte`, `athletic_subsidy_ratio`, `aura_score`) belong to downstream zones.
- Cross-source FK integrity to `base.ipeds_finance` is enforced at Silver (BSE-EAD-009 cross-source coverage rule), not Bronze.
- Future cycles will append rows for additional `reporting_year` values; the schema does not change.
