# Logical Model: base-ipeds-finance

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) §5
**Conceptual model:** [base-ipeds-finance-conceptual.md](base-ipeds-finance-conceptual.md)
**Bronze logical model:** [raw-ipeds-finance-logical.md](raw-ipeds-finance-logical.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    BASE_IPEDS_FINANCE {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        text report_form
        numeric fiscal_year
        numeric institutional_support_expenses
        numeric instruction_expenses
        numeric endowment_value
        numeric total_fte_enrollment
        numeric institutional_support_per_fte
        numeric instruction_per_fte
        numeric endowment_per_fte
        numeric marketing_ratio
        date source_load_date
        timestamp ingested_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies eight entities (Institution, Finance Report, Accounting Form, Fiscal Cycle, Monetary Measurement, Enrollment Denominator, Per-FTE Derivation, Marketing Intensity, Ingest Provenance). Per the Brightsmith Silver Base zone pattern, all eight collapse into a single denormalized 15-attribute table. This is appropriate because:

1. All conceptual relationships are 1:1 per row — the grain is one (institution, fiscal cycle) and every attribute resolves to exactly one value (or NULL) per row.
2. The source Bronze table is already a single flat table of 2,675 rows; there is no normalization benefit to splitting it.
3. Silver Base tables are designed as wide, query-ready tables for downstream Gold and MCP consumption.
4. Carrying the Bronze numerators in the same row as their per-FTE derivations is what makes the BSE-IPF-008/009 arithmetic invariants self-auditable at rest.
5. This matches the established pattern from `base.bea_rpp` (denormalized 11-column reference table) and from the project's other base zones.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per U.S. 4-year bachelor's-granting postsecondary institution (`unitid`) for a single IPEDS fiscal cycle |
| **Natural key fields** | `unitid` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['unitid'], prefix='ipf')`) |
| **Uniqueness constraints** | Zero duplicates on `unitid` (BSE-IPF-002 P0). Zero duplicates on `record_id` (BSE-IPF-003 P0). |
| **Expected cardinality** | 2,675 rows in the current load (FY2023). Matches Bronze 1:1 (BSE-IPF-001 P0 conservation invariant). |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from.

### Identity & Reporting

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | (Brightsmith convention) | identifier | NOT NULL | false | false | Deterministic surrogate key computed via `compute_grain_id(row, ['unitid'], prefix='ipf')`. Format: `ipf-<16 hex chars>`. Stable across pipeline re-runs (verified: Stanford UNITID 243744 → `ipf-267f20f48b4b772f` across multiple promotes). |
| unitid | BT-001 | identifier | NOT NULL | true | false | The 6-digit IPEDS UNITID, promoted verbatim from Bronze. Natural key and dedup grain. The universal join key linking IPEDS Finance to every other institution-keyed table in the pipeline. |
| institution_name | BT-002 | text | NOT NULL | false | false | The official name of the institution (HD `INSTNM`), promoted verbatim from Bronze. Display-only — do not use for joins. |
| report_form | (proposed) BT-IPF-ACCOUNTING-FORM | text (enum: `F1A`/`F2`/`F3`) | NOT NULL | false | false | The IPEDS Finance form the institution filed on. Carried unchanged from Bronze. Drives per-form segmentation downstream (e.g., the per-form marketing-ratio P99 thresholds in BSE-IPF-015a/b/c). |
| fiscal_year | (proposed) BT-IPF-FISCAL-CYCLE | numeric (year) | NOT NULL | false | false | The IPEDS fiscal year the row covers (current load: 2023). Constant across every row in a single load (single-vintage invariant inherited from Bronze RAW-IPF-013). |

### Monetary Inputs (Passthrough from Bronze)

The three Bronze monetary fields, carried verbatim. They are the *numerator inputs* for the per-FTE derivations and the marketing-ratio derivation.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| institutional_support_expenses | BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES | numeric (USD) | NULLABLE | false | false | The institution's total annual expenses for executive management, fiscal operations, public relations, fundraising, and similar administrative functions. Promoted verbatim from `bronze.ipeds_finance.institutional_support_expenses`. **Observed (FY23):** 100.00% non-null (2,675 / 2,675). **Sourced from F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1`** (post-2014-15 schedule populated). |
| instruction_expenses | BT-IPF-INSTRUCTION-EXPENSES | numeric (USD) | NULLABLE | false | false | The institution's total annual expenses for instructional divisions — faculty salaries, instructional materials, departmental research. Promoted verbatim from Bronze. **Observed (FY23):** 100.00% non-null. **Sourced from F1A `F1C011` / F2 `F2E011` / F3 `F3E011`**. |
| endowment_value | BT-IPF-ENDOWMENT-VALUE | numeric (USD) | NULLABLE | false | false | End-of-year market value of the institution's endowment funds. Reported on F1A and F2 only — for-profit (F3) institutions have no `F3H` family on their finance schedule. Promoted verbatim from Bronze. **Observed (FY23):** 76.00% non-null overall; 100% structural NULL on F3 by design. **Sourced from F1A `F1H02` / F2 `F2H02`**. |
| endowment_value_flag (v1.4) | (proposed) BT-IPF-ENDOWMENT-PROVENANCE | text (enum: `R`/`A`/`P`/`Z`/`N` OR NULL) | NULLABLE | false | false | **NEW v1.4** — IPEDS-published imputation flag for `endowment_value`, passthrough from `bronze.ipeds_finance.endowment_value_flag` per spec §5. **Authoritative semantics (corrected v1.2):** `R` = Reported by institution; `A` = **Not applicable** (no endowment fund — exact `A`↔NULL coupling on `endowment_value`, enforced by BSE-IPF-020 P0); `N` = **Imputed using Nearest Neighbor procedure**; `P` = Imputed prior year; `Z` = Imputed zero. NULL on F3 by structure (no `F3H` family). The CDE flag is `false` at base — the column becomes CDE at consumable as `endowment_value_provenance` where the rename signals consumer-facing posture. Validated by BSE-IPF-018 (P0 passthrough fidelity), BSE-IPF-019 (P1 per-form prevalence band: F1A 5–15%, F2 12–25%), BSE-IPF-020 (P0 bi-implicational `A`↔NULL coupling invariant). |
| total_fte_enrollment | (proposed) BT-IPF-PER-FTE (the convention; this column is the denominator) | numeric (FTE) | NULLABLE | true | false | The institution's 12-month total full-time-equivalent enrollment, computed at Bronze as the NULL-safe sum `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` from EFIA. Promoted verbatim. **Observed (FY23):** 97.94% non-null (2,620 / 2,675); the 55 NULL rows cause every per-FTE value in this row to NULL-cascade. The single most load-bearing column for downstream analysis. |

### Per-FTE Derivations (NEW in Base)

The three per-student normalizations of the monetary inputs. Computed in Silver via plain-double arithmetic. NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **No imputation.**

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| institutional_support_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student administrative-and-overhead spending. **Derivation:** `institutional_support_expenses / total_fte_enrollment`. **NULL semantics:** NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **Observed (FY23):** 97.94% non-null. **Arithmetic invariant (BSE-IPF-009):** `institutional_support_per_fte × total_fte_enrollment ≈ institutional_support_expenses` within $1 wherever all three are non-null. |
| instruction_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student instructional spending. **Derivation:** `instruction_expenses / total_fte_enrollment`. **NULL semantics:** same as above. **Observed (FY23):** 97.94% non-null. **Arithmetic invariant (BSE-IPF-008):** `instruction_per_fte × total_fte_enrollment ≈ instruction_expenses` within $1 wherever all three are non-null. **Tripwire:** BSE-IPF-017 requires P99 < $500K — guards against an EFFY-headcount-vs-FTE field-selection regression. |
| endowment_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student endowment value. **Derivation:** `endowment_value / total_fte_enrollment`. **NULL semantics:** NULL when either operand is NULL or `total_fte_enrollment ≤ 0`; F3 rows are 100% NULL by design (endowment is structurally NULL on F3). **Observed (FY23):** 74.69% non-null. **Arithmetic invariant (BSE-IPF-009):** symmetric with the other two per-FTE rates. |

### Marketing Intensity (NEW in Base)

A cross-field ratio with no FTE dependency. Computed in Silver via plain-double arithmetic with `NULLIF` semantics on the denominator.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| marketing_ratio | (proposed) BT-IPF-MARKETING-RATIO | numeric (unitless ratio) | NULLABLE | true | false | The ratio of institutional support expenses to instruction expenses. Higher = relatively more spending on administration, marketing, and recruiting vs. teaching. **Derivation:** `institutional_support_expenses / NULLIF(instruction_expenses, 0)`. **NULL semantics:** NULL when either operand is NULL or `instruction_expenses = 0`. **Observed (FY23):** 98.84% non-null (2,644 / 2,675); the 31 NULL rows are the small set of zero-instruction system-office UNITIDs. **Per-form P99 (FY23 actual):** F1A 14.15 / F2 6.35 / F3 8.75 — the per-form thresholds in BSE-IPF-015a/b/c (15.0 / 7.0 / 11.0) are calibrated against these values with FY-vintage drift headroom. **Arithmetic invariant (BSE-IPF-010):** `marketing_ratio × instruction_expenses ≈ institutional_support_expenses` within $1 wherever all three are non-null. |

### Pipeline Provenance

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | (Brightsmith convention) | date | NOT NULL | false | false | Date the source Bronze data was loaded. Direct passthrough of `bronze.ipeds_finance.load_date`. |
| ingested_at | (Brightsmith convention) | timestamp | NOT NULL | false | false | UTC wall-clock recording when this Base row was promoted from Bronze. Identical across all rows in a single Base promote run. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 15 | Total attributes |
| 1 | Surrogate key (record_id) |
| 1 | Natural key (unitid) |
| 5 | CDE attributes (unitid, total_fte_enrollment, institutional_support_per_fte, instruction_per_fte, endowment_per_fte, marketing_ratio — five columns plus unitid for six total CDE-flagged) |
| 0 | PII attributes |
| 5 | NOT NULL attributes (record_id, unitid, institution_name, report_form, fiscal_year, source_load_date, ingested_at — seven NOT NULL; the four monetary inputs and four derivations are NULLABLE) |
| 8 | Passthroughs from Bronze (unitid, institution_name, report_form, fiscal_year, institutional_support_expenses, instruction_expenses, endowment_value, total_fte_enrollment) |
| 4 | Derived in Base (institutional_support_per_fte, instruction_per_fte, endowment_per_fte, marketing_ratio) |
| 1 | Surrogate-key-derived (record_id) |
| 2 | Provenance (source_load_date, ingested_at) |

---

## Type Domain Definitions

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. UNITID is a numeric long; record_id is a string hash. | LongType for unitid; StringType for record_id |
| text | A human-readable label or display value. | StringType |
| numeric (USD) | A dollar-denominated measurement. Promoted verbatim from Bronze. | DoubleType |
| numeric (USD per FTE) | A per-student dollar rate computed in Base. | DoubleType |
| numeric (unitless ratio) | A dimensionless ratio computed in Base. | DoubleType |
| numeric (FTE) | A 12-month full-time-equivalent enrollment count, may carry tenths from EFIA. | DoubleType |
| numeric (year) | A calendar/fiscal year used for filtering and single-vintage enforcement. | IntegerType |
| date | A calendar date without time component. | DateType |
| timestamp | A point in time used for pipeline auditing. | TimestampType |

---

## Derivation Rules (Plain-English)

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | Apply `compute_grain_id(row, ['unitid'], prefix='ipf')`. Output format: `ipf-<16 hex>`. | unitid |
| institutional_support_per_fte | Divide `institutional_support_expenses` by `total_fte_enrollment`. Return NULL if either operand is NULL or `total_fte_enrollment ≤ 0`. | institutional_support_expenses, total_fte_enrollment |
| instruction_per_fte | Divide `instruction_expenses` by `total_fte_enrollment`. Same NULL rule. | instruction_expenses, total_fte_enrollment |
| endowment_per_fte | Divide `endowment_value` by `total_fte_enrollment`. Same NULL rule. F3 rows are always NULL because endowment is structurally NULL on F3. | endowment_value, total_fte_enrollment |
| marketing_ratio | Divide `institutional_support_expenses` by `instruction_expenses`. Return NULL if either operand is NULL or `instruction_expenses = 0` (mirrors `NULLIF` semantics). No FTE dependency — broader coverage than the per-FTE rates. | institutional_support_expenses, instruction_expenses |
| source_load_date | Direct passthrough from `bronze.ipeds_finance.load_date`. | bronze.ipeds_finance.load_date |
| ingested_at | Generated at promote time via `datetime.now()` (UTC). | -- |

---

## Passthrough Attributes

| Attribute | Source |
|-----------|--------|
| unitid | `bronze.ipeds_finance.unitid` (verbatim) |
| institution_name | `bronze.ipeds_finance.institution_name` (verbatim) |
| report_form | `bronze.ipeds_finance.report_form` (verbatim) |
| fiscal_year | `bronze.ipeds_finance.fiscal_year` (verbatim) |
| institutional_support_expenses | `bronze.ipeds_finance.institutional_support_expenses` (verbatim) |
| instruction_expenses | `bronze.ipeds_finance.instruction_expenses` (verbatim) |
| endowment_value | `bronze.ipeds_finance.endowment_value` (verbatim) |
| total_fte_enrollment | `bronze.ipeds_finance.total_fte_enrollment` (verbatim) |

---

## Nullability Semantics

| Attribute Group | NOT NULL? | Reason |
|----------------|-----------|--------|
| Identity (record_id, unitid, institution_name, report_form, fiscal_year) | Yes | Every row must have a complete identity stamp. NULL would mean the row bypassed Bronze ingestion. |
| Monetary inputs | NO | Bronze observes 100% non-null on the two expense fields and 76% on endowment. The schema permits NULL because (a) F3 endowment is structurally NULL, (b) bureau imputation can render fields NULL on cycle drift, and (c) the Brightsmith no-substitution convention prohibits filling NULLs with sentinels. |
| FTE denominator | NO | Bronze observes 97.94% non-null. The 55 NULL rows are real institution-fiscal-year cases where EFIA had no row (typically newly-opened institutions or late filers). NULL must propagate honestly. |
| Per-FTE derivations | NO | NULL-cascade by design when either operand is missing. |
| marketing_ratio | NO | NULL-cascade by design. |
| Provenance (source_load_date, ingested_at) | Yes | Pipeline-stamped — a NULL would mean the promote bypassed `promote()`. |

---

## Key Constraints (Logical)

| Constraint | Type | Source |
|------------|------|--------|
| `unitid IS NOT NULL` for every row | Total | Inherited from Bronze |
| `unitid` is unique within a single `fiscal_year` | Uniqueness | BSE-IPF-002 (P0) |
| `record_id IS NOT NULL` and unique | Validity + Uniqueness | BSE-IPF-003 (P0) |
| `report_form ∈ {F1A, F2, F3}` | Validity (enum) | Inherited from Bronze (RAW-IPF-004) |
| `instruction_per_fte ≥ 0` where non-null | Range | BSE-IPF-004 (P0) |
| `institutional_support_per_fte ≥ 0` where non-null | Range | BSE-IPF-005 (P0) |
| `endowment_per_fte ≥ 0` where non-null | Range | BSE-IPF-006 (P0) |
| `marketing_ratio ≥ 0` where non-null | Range | BSE-IPF-007 (P0) |
| `instruction_per_fte × total_fte_enrollment ≈ instruction_expenses` within $1 | Arithmetic invariant | BSE-IPF-008 (P0) |
| Same invariant for institutional_support and endowment | Arithmetic invariant | BSE-IPF-009 (P0) |
| `marketing_ratio × instruction_expenses ≈ institutional_support_expenses` within $1 | Arithmetic invariant | BSE-IPF-010 (P0) |
| `instruction_per_fte` non-null ≥ 85% (observed 97.94%) | Completeness | BSE-IPF-011 (P0) |
| `institutional_support_per_fte` non-null ≥ 85% (observed 97.94%) | Completeness | BSE-IPF-012 (P0) |
| `endowment_per_fte` non-null ≥ 70% (observed 74.69%) | Completeness | BSE-IPF-013 (P1; tightened from spec 55% per EDA) |
| `marketing_ratio` non-null ≥ 95% (observed 98.84%) | Completeness | BSE-IPF-014 (P0; tightened from spec 85% per EDA) |
| `marketing_ratio` per-form P99 < {15.0 / 7.0 / 11.0} for F1A / F2 / F3 | Plausibility (per-form, EDA-calibrated) | BSE-IPF-015a/b/c (P1) |
| `endowment_per_fte` spot check: at least one row > $1M | Plausibility | BSE-IPF-016 (P1) |
| `instruction_per_fte` P99 < $500,000 | Plausibility (FTE-bug tripwire) | BSE-IPF-017 (P1) |
| Row count = Bronze row count | Conservation | BSE-IPF-001 (P0) |
| `endowment_value_flag` passthrough fidelity (every base row matches the source bronze row, joined on `unitid`; 0 mismatches) | Conservation (column-level) | BSE-IPF-018 (P0) — v1.4 |
| `endowment_value_flag = 'A'` rate per form: F1A within 5–15%, F2 within 12–25% (denominator: rows with `endowment_value_flag IS NOT NULL` for that form) | Distribution (EDA-calibrated v1.2 against FY2023-landed steady-state baselines F1A 9.77% / F2 18.05%) | BSE-IPF-019 (P1) — v1.4 |
| `A`↔NULL coupling invariant (bi-implication, both directions): every row with `endowment_value_flag = 'A'` has `endowment_value IS NULL`, AND every F1A/F2 row with `endowment_value IS NULL` has `endowment_value_flag = 'A'`. F3 rows exempt by structure. | Consistency / semantic invariant | BSE-IPF-020 (P0) — v1.4 |

All 22 rules pass against the v1.4 landed table (`governance/dq-rules/base-ipeds-finance.json`).

---

## Cardinality

- **2,675 rows** in the current FY2023 load.
- Matches Bronze 1:1 (BSE-IPF-001 conservation invariant).
- Form mix: F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%).
- Future cycles append. Single-cycle snapshots today; multi-cycle backfill is a future-amendment concern.

---

## Modeling Decisions

1. **One flat row per (institution, cycle).** Same as Bronze; no normalization of monetary fields into a long-form measurement table.

2. **Derivations live alongside their numerators.** Carrying the Bronze numerator in the same Base row as its per-FTE derivation (and same for the marketing-ratio numerator and denominator) is what makes BSE-IPF-008/009/010 self-auditable at rest. Splitting them would force the DQ rules into cross-row joins.

3. **No imputation, no substitution.** Per the standing user constraint and per spec §2 Decision #8, NULLs propagate honestly through the per-FTE and marketing-ratio derivations.

4. **`marketing_ratio` is dimensionally unitless and uses `NULLIF` semantics on the denominator.** Reading "1.0" means parity (institutional support ≈ instruction); "5.0" means 5× as much spent on administration as instruction. The `NULLIF(instruction_expenses, 0)` gate prevents division-by-zero on the 34 zero-instruction system-office rows.

5. **`record_id` uses prefix `ipf` (not `ifp`).** Per spec §5 promote pattern: `compute_grain_id(row, ['unitid'], prefix='ipf')`. The downstream consumable uses prefix `ifp` (different namespace) so that hash collisions across zones are impossible by construction.

6. **`fiscal_year` typed as `Integer`, not `Date`.** Same as Bronze — discrete fiscal-year value used for filtering and single-vintage enforcement, not a date for arithmetic.

7. **`total_fte_enrollment` is CDE.** It is the universal denominator for every per-FTE derivation and the trip-wire for the EFIA-vs-EFFY-vs-EFTOTLT field-selection bug. Wrong values here mis-state every per-FTE rate downstream.

8. **The four monetary inputs are NOT CDE *at Base*.** They become CDE at the consumable layer (per spec §6 Data Contract) once they are exposed to the downstream EADA fusion that needs raw dollars for composite ratios. At Base, the per-FTE rates and marketing-ratio carry the analytical CDE flag.

9. **Per-form DQ thresholds for marketing-ratio.** BSE-IPF-015 is split into a/b/c for F1A/F2/F3 because the public-system-administrative-office cluster legitimately drives F1A P99 to ~14, well above what F2 (~6) or F3 (~9) ever reach. A table-wide threshold would either fire on legitimate state-system offices or fail to catch genuine F2/F3 outliers.

10. **No SCD2.** Same as Bronze: latest single-fiscal-cycle snapshot. Multi-cycle history would require partitioning on `fiscal_year` and extending the dedup grain.

11. **v1.4 — `endowment_value_flag` is a passthrough, not a derivation.** The column carries verbatim from `bronze.ipeds_finance.endowment_value_flag` (BSE-IPF-018 P0 conservation). The CDE flag is intentionally false at base — the column becomes CDE at consumable as `endowment_value_provenance`, where the rename signals consumer-facing posture. The bi-implicational `A`↔NULL coupling invariant (BSE-IPF-020 P0) codifies the v1.2-corrected `A`="Not applicable" semantic at the rule layer; future-cycle NCES semantic drift (if `A` ever loses its no-endowment meaning) trips the rule before downstream consumers can misread the column.

---

## Scope and Boundaries

- This logical model covers `base.ipeds_finance` only.
- Bronze raw data (`bronze.ipeds_finance`) is fully modeled in `raw-ipeds-finance-logical.md`.
- Consumable products (`consumable.ipeds_finance_profile`) are downstream consumers, modeled in `consumable-ipeds-finance-profile-logical.md`.
- The downstream EADA fusion (`consumable.institution_aura`) lives in `full-pipeline-eada.md` and is not in this model.
