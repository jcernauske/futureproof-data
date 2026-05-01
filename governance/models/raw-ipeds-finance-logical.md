# Logical Model: raw-ipeds-finance

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) §4
**Conceptual model:** [raw-ipeds-finance-conceptual.md](raw-ipeds-finance-conceptual.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Logical Schema

The Bronze zone is a flattened representation of the conceptual `Finance Report` entity — one logical row per `(Institution, Fiscal Cycle)`. The seven conceptual entities (Institution, Finance Report, Accounting Form, Fiscal Cycle, Monetary Measurement, Enrollment Denominator, Ingest Provenance) collapse onto a single 12-attribute table because Bronze policy is "land what the source publishes plus the upstream FTE denominator, do not normalize."

### Attributes

| Attribute | Conceptual Entity | Role | Logical Type | Required | Source-System Origin |
|-----------|-------------------|------|--------------|----------|----------------------|
| `unitid` | Institution | Primary identifier (natural key + dedup grain) | Long Integer | Yes | Finance form `UNITID` (case-tolerant); also keys the joins to EFIA and HD |
| `institution_name` | Institution | Display name | Text | Yes | HD `INSTNM`, joined on UNITID at ingest |
| `report_form` | Accounting Form | Form-of-origin tag | Text (enum: `F1A` / `F2` / `F3`) | Yes | Stamped by ingestor based on which form CSV the row came from |
| `fiscal_year` | Fiscal Cycle | IPEDS fiscal year | Integer (year) | Yes | Pinned by ingestor from `DEFAULT_FISCAL_YEAR` (2023) or constructor kwarg |
| `institutional_support_expenses` | Monetary Measurement | Administration / fundraising / executive expenses (USD) | Decimal Money | No | F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1` (post-2014-15 schedule) |
| `instruction_expenses` | Monetary Measurement | Teaching delivery expenses (USD) | Decimal Money | No | F1A `F1C011` / F2 `F2E011` / F3 `F3E011` |
| `endowment_value` | Monetary Measurement | End-of-year endowment market value (USD) | Decimal Money | No | F1A `F1H02` / F2 `F2H02` / F3 N/A (no `F3H` family — structural NULL) |
| `total_fte_enrollment` | Enrollment Denominator | 12-month total FTE | Decimal | No | EFIA `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` (NULL only when all three components are NULL) |
| `source_url` | Ingest Provenance | Provenance — pipe-delimited list of all 5 source URLs (F1A / F2 / F3 / EFIA / HD) | Text (URL list) | Yes | Stamped by ingestor; constant per batch |
| `source_method` | Ingest Provenance | Provenance — fetch path used | Text (enum-like) | Yes | Stamped by ingestor; current value `bulk_csv_download` |
| `ingested_at` | Ingest Provenance | Provenance — UTC wall-clock of the Bronze write | Timestamp | Yes | Stamped by ingestor; identical across all rows in a batch |
| `load_date` | Ingest Provenance | Provenance — UTC calendar date of the load | Date | Yes | Stamped by ingestor; identical across all rows in a batch |

### Keys

| Key Type | Columns | Notes |
|----------|---------|-------|
| Natural key (per-cycle) | `unitid` | One row per institution per fiscal cycle. Within a single `fiscal_year` partition, `unitid` is unique (RAW-IPF-003, P0). |
| Dedup grain | `[unitid]` | Declared by the ingestor as the dedup grain for idempotent re-runs of a single cycle. |
| Foreign keys (downstream) | `unitid` → `bronze.college_scorecard_institution.unitid`, `bronze.eada.unitid`, `consumable.career_outcomes.unitid` | Bronze does not enforce FK integrity; consumers do. |

### Derivations and Defaults

The Bronze zone performs **no per-FTE derivations and no marketing-ratio derivation**. The `total_fte_enrollment` column is the only computed value at Bronze, and it is not a derivation in the Brightsmith sense — it is a NULL-safe sum across three EFIA component columns (`FTEUG + FTEGD + FTEDPP`) that produces the canonical "total FTE" figure NCES itself uses in its Data Feedback Reports. This computation lives at Bronze (not Silver) because:

- It is upstream-of-derivation: every per-FTE rate downstream depends on it.
- It is mechanically deterministic from three source columns with documented IPEDS semantics — it has no judgment calls.
- Doing the sum at Silver instead would require `base.ipeds_finance` to JOIN to a Bronze EFIA table that doesn't exist (we don't land EFIA as its own table).

All true derivations live downstream:

- `institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio` → all derived at `base.ipeds_finance` (Silver).
- `data_completeness_tier` → derived at `consumable.ipeds_finance_profile` (Gold).
- `aura_score`, `coverage_tier` → derived at `consumable.institution_aura` (downstream spec `full-pipeline-eada.md`, Gold).

All other values are either passthroughs from the IPEDS source files, pinned ingestor constants (`source_method`, `fiscal_year`), or system clocks (`ingested_at`, `load_date`).

### Cardinality

- 2,675 rows in the current load (FY23 cycle).
- Expected band: 2,500–3,200 per cycle (RAW-IPF-001, P0). The lower bound covers EFIA join attrition or an HD-filter narrowing (e.g., a year where many small religious 4-year colleges close); the upper bound trips if the HD-filter weakens or a non-finance file leaks into the UNION.
- **Note:** The spec-as-originally-written had RAW-IPF-001 at 5,000–8,000, sized for the unfiltered Finance UNION (~6,500 institutions). After applying `ICLEVEL = 1 AND HLOFFER >= 5`, only 2,675 rows survive. EDA §0 gate 6 explicitly recommended recalibrating to 2,500–3,200, and `governance/dq-rules/raw-ipeds-finance.json` already adopts the EDA-recommended band.
- Form mix in FY23: F1A 30.6% (819) / F2 59.0% (1,579) / F3 10.4% (277).
- Future cycles append. The table is partition-friendly on `fiscal_year`, but the current Bronze write is single-cycle (no partition spec).

---

## Constraints (Logical)

| Constraint | Type | Source |
|------------|------|--------|
| `unitid IS NOT NULL` for every row | Total | RAW-IPF-002 (P0) |
| `unitid` is unique within a single `fiscal_year` | Uniqueness | RAW-IPF-003 (P0) |
| `report_form ∈ {F1A, F2, F3}` | Validity (enum) | RAW-IPF-004 (P0) |
| `instruction_expenses ≥ 0` where non-null | Range | RAW-IPF-005 (P0) |
| `institutional_support_expenses ≥ 0` where non-null | Range | RAW-IPF-006 (P0) |
| `endowment_value ≥ 0` where non-null (underwater funds report 0, never negative; F3 is structural NULL) | Range | RAW-IPF-007 (P0) |
| `total_fte_enrollment > 0` where non-null (no 0-FTE institution can exist in EFIA) | Range | RAW-IPF-008 (P0) |
| `instruction_expenses` non-null ≥ 90% (observed 100.0%) | Completeness | RAW-IPF-009 (P0) |
| `institutional_support_expenses` non-null ≥ 90% (observed 100.0%; EDA refuted pre-v1.3 hypothesis that F3 omits this) | Completeness | RAW-IPF-010 (P0) |
| `total_fte_enrollment` non-null ≥ 95% (observed 97.94%) | Completeness | RAW-IPF-011 (P0) |
| `endowment_value` non-null ≥ 60% (observed 76.0%; the 24% NULL is mostly structural F3 + ~16% small F2) | Completeness | RAW-IPF-012 (P1) |
| `COUNT(DISTINCT fiscal_year) == 1` per load | Consistency (single-vintage invariant) | RAW-IPF-013 (P0) |
| ≥1 row with `instruction_expenses > $100M` (R1 anchor; observed 269 rows) | Plausibility | RAW-IPF-014 (P1) |

---

## Data Quality Summary

- 14/14 DQ rules PASS against the FY23 cycle (scorecard `governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.{json,md}`).
- Adversarial chaos (raw): 6/6 caught (`governance/chaos-reports/raw-ipeds-finance-chaos.md`).
- PII scan: N/A (institution-level data, no individual identifiers).
- Entity resolution: N/A (single-key UNITID across all five source files).
- Temporal modeling: N/A (single-cycle snapshot; no SCD2).

---

## Modeling Decisions (Logical Layer)

1. **One flat row per (institution, cycle).** No normalization of `Monetary Measurement` into a long-form `(unitid, fiscal_year, measurement_name, value)` shape. The wide form matches IPEDS Finance's published shape and is what every downstream consumer expects (Silver derivations operate on the three columns side by side; long-form would force a pivot at every read site).

2. **`fiscal_year` as Integer, not Date.** The cycle is a discrete fiscal year, not a calendar date. Stamping it as the ending-fiscal-year integer (e.g., 2023 for the FY23 cycle / academic year 2022–23) matches the IPEDS publication convention and keeps year-over-year comparisons trivial.

3. **Monetary measurements as `Decimal Money` logically, `DOUBLE` physically.** IPEDS Finance publishes whole-dollar values, but the upstream codebook does not promise integer-only output (some derived fields elsewhere in the file carry cents). Using `DOUBLE` at Iceberg matches the sibling `bronze.eada` and `bronze.college_scorecard_institution` cost columns. The "Decimal Money" logical type is documentary — it tells consumers the unit is USD, not unitless.

4. **`total_fte_enrollment` computed at Bronze, not Silver.** The NULL-safe three-column sum (`COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)`) is materialized at Bronze for two reasons: (a) per-FTE rates downstream all depend on it, and (b) we do not land EFIA as a separate Bronze table — the join to EFIA happens once at Bronze ingest, then the result is carried through. This is the one Bronze-zone "computation" that is not strictly a passthrough; the conceptual model treats EFIA as a separate entity (`Enrollment Denominator`) precisely so this Bronze-time decision is visible.

5. **`report_form` as an enum-typed string, not a separate dimension table.** The form has only three values (F1A / F2 / F3) and is part of the row's natural identity (an institution's form is determined by sector and rarely changes). Joining to a forms dimension table would add no resolvable structure. Validated by RAW-IPF-004 (P0).

6. **Provenance fields are `Required: Yes` even though they are stamped, not sourced.** Bronze policy: every row carries provenance. A NULL `source_url` or `ingested_at` would mean the row bypassed the ingestor entirely (e.g., manual SQL append) and is a governance violation regardless of payload validity.

7. **No `imputation_flag_*` columns.** Per §2 Decision #8, IPEDS publishes parallel `X*`-prefixed flag columns indicating bureau-imputation; we accept imputed values as raw and do not store the flags. EDA Req 7 measured prevalence ≤1.22% on every field — well below the threshold (~5%) where the cost of a flag-column schema change would be justified.

8. **No SCD2.** Bronze keeps the latest single-fiscal-cycle snapshot. Multi-cycle history is a future-amendment concern (would require a partition spec on `fiscal_year` and an extension of the dedup grain to `[unitid, fiscal_year]`).

9. **`source_url` as a pipe-delimited URL list, not a single string.** This Bronze ingest fans out across 5 source files (3 Finance forms + EFIA + HD). A single `source_url` would lose lineage attribution to one of the four-or-five upstream files. The pipe-delimited list preserves all five for the lineage tracker. EDA §10 flagged a cosmetic point (the docstring says "list of all 4 files" but the impl emits 5) — that is a docstring fix only; the schema remains 5-entry pipe-delimited.

---

## Scope and Boundaries

- This logical model covers `raw.ipeds_finance` (Iceberg `bronze.ipeds_finance`) only.
- Derivations (`*_per_fte`, `marketing_ratio`, `data_completeness_tier`) belong to downstream zones.
- Cross-source FK integrity to `bronze.college_scorecard_institution`, `bronze.eada`, etc. is enforced at Silver (cross-source coverage rules), not Bronze.
- Future cycles will append rows for additional `fiscal_year` values; the schema does not change.
- The hundreds of additional fields in the Finance Survey (per-functional-category breakdowns, revenue by source, debt, scholarships) are out of scope.
