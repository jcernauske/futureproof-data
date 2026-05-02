# Logical Model: base-eada

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §5 (Option-C amendment, 2026-04-30)
**Conceptual model:** [base-eada-conceptual.md](base-eada-conceptual.md)
**Bronze logical model:** [raw-eada-logical.md](raw-eada-logical.md)
**Cross-source dependency:** [base-ipeds-finance-logical.md](base-ipeds-finance-logical.md) (FTE LEFT-JOIN source)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    BASE_EADA {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        numeric reporting_year
        numeric total_athletic_expenses
        numeric total_athletic_revenue
        numeric recruiting_expenses
        numeric eada_fte_headcount
        numeric total_fte_enrollment
        text fte_source
        boolean has_ipeds_finance_fte
        boolean has_eada_fte
        numeric athletic_spend_per_fte
        numeric athletic_revenue_per_fte
        numeric recruiting_per_fte
        numeric athletic_subsidy_ratio
        date source_load_date
        timestamp ingested_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies eight entities (Institution, Athletic Financial Report, Reporting Cycle, Monetary Measurement, Enrollment Denominator, FTE Source Provenance, Per-FTE Derivation, Subsidy Intensity, Ingest Provenance). Per the Brightsmith Silver Base zone pattern, all eight collapse into a single denormalized 18-attribute table. This is appropriate because:

1. All conceptual relationships are 1:1 per row — the grain is one (institution, cycle) and every attribute resolves to exactly one value (or NULL) per row.
2. The source Bronze table is already a single flat table of 2,040 rows; there is no normalization benefit to splitting it.
3. Silver Base tables are designed as wide, query-ready tables for downstream Gold consumption.
4. Carrying the Bronze numerators and the chosen FTE denominator in the same row as their per-FTE derivations is what makes the BSE-EAD-008 arithmetic invariant self-auditable at rest.
5. This matches the established pattern from `base.ipeds_finance` (15-column denormalized table with per-FTE derivations and one cross-field ratio) and from the project's other base zones.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per U.S. postsecondary institution (`unitid`) for a single EADA reporting cycle |
| **Natural key fields** | `unitid` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['unitid'], prefix='ead')`) |
| **Uniqueness constraints** | Zero duplicates on `unitid` (BSE-EAD-002 P0). Zero duplicates on `record_id` (BSE-EAD-003 P0). |
| **Expected cardinality** | 2,040 rows in the current load (academic year 2022–23 cycle). Matches Bronze 1:1 (BSE-EAD-001 P0 conservation invariant). |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from.

### Identity & Reporting

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | (Brightsmith convention) | identifier | NOT NULL | false | false | Deterministic surrogate key computed via `compute_grain_id(row, ['unitid'], prefix='ead')`. Format: `ead-<16 hex chars>`. Stable across pipeline re-runs (idempotent promote). The downstream consumable uses prefix `aur` so cross-zone hash collisions are impossible by construction. |
| unitid | BT-001 | identifier | NOT NULL | true | false | The 6-digit IPEDS UNITID, promoted verbatim from Bronze. Natural key and dedup grain. The universal join key linking EADA to every other institution-keyed table in the pipeline (LEFT JOIN to `base.ipeds_finance` for FTE here; FULL OUTER JOIN at `consumable.institution_aura`). |
| institution_name | BT-002 | text | NOT NULL | false | false | The name of the institution as filed with EADA, promoted verbatim from Bronze. Display-only — do not use for joins. |
| reporting_year | (proposed) BT-120 | numeric (year) | NOT NULL | false | false | The academic-year-start of the EADA reporting cycle (current load: `2022` for the 2022–23 cycle). Constant across every row in a single load (single-vintage invariant inherited from Bronze RAW-EAD-010). |

### Monetary Inputs (Passthrough from Bronze)

The three Bronze monetary fields, carried verbatim. They are the *numerator inputs* for the per-FTE derivations and the subsidy-ratio derivation.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| total_athletic_expenses | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO (one of two inputs) | numeric (USD) | NULLABLE | false at Base (analytical CDE is on `athletic_spend_per_fte`) | false | The institution's total intercollegiate athletics expenses for the cycle, in USD, rolled up across every sport. Promoted verbatim from `bronze.eada.total_athletic_expenses`. **Observed (2022–23):** 100% non-null. **Source:** EADA `GRND_TOTAL_EXPENSE`. The numerator of `athletic_spend_per_fte` and the denominator of `athletic_subsidy_ratio`. |
| total_athletic_revenue | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO (one of two inputs) | numeric (USD) | NULLABLE | false at Base (analytical CDE is on `athletic_revenue_per_fte` and `athletic_subsidy_ratio`) | false | The institution's total intercollegiate athletics revenue for the cycle, in USD. EADA convention requires reported revenue ≥ expense at the grand-total grain, so revenue ≈ expense for nearly every row. Promoted verbatim from Bronze. **Observed (2022–23):** 100% non-null. **Source:** EADA `GRND_TOTAL_REVENUE`. The numerator of `athletic_revenue_per_fte` and one input to `athletic_subsidy_ratio`. |
| recruiting_expenses | — | numeric (USD) | NULLABLE | false | false | The institution's total athletic recruiting expenses for the cycle, in USD. **17.8% of institutions report exactly $0** (real reported zeros — not suppressions; mostly NJCAA II/III, CCCAA, NWAC, NCCAA programs that don't recruit off-campus). Promoted verbatim from Bronze. **Observed (2022–23):** 100% non-null. **Source:** EADA `RECRUITEXP_TOTAL`. The numerator of `recruiting_per_fte`. |

### EADA-Sourced Headcount (Passthrough from Bronze; New Column for Option C)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| eada_fte_headcount | — | numeric (headcount) | NULLABLE | false at Base (the analytical CDE flag lives on the COALESCE'd `total_fte_enrollment`) | false | EADA's in-file 12-month enrollment headcount, sourced from `EFTotalCount` in `InstLevel.xlsx` and added to Bronze in the §4 amendment as the §5 Option-C fallback denominator. Available on every EADA row (~100% non-null observed). **Note:** This is a *headcount*, not an annualized FTE — methodologically distinct from `base.ipeds_finance.total_fte_enrollment`. The `fte_source` column makes the methodology explicit when this column is the chosen denominator. |

### Enrollment Denominator (Hybrid — COALESCE in Base)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| total_fte_enrollment | (proposed) BT-IPF-PER-FTE (the convention; this column is the denominator) | numeric (FTE-or-headcount) | NULLABLE | true | false | The COALESCE'd FTE denominator. **Derivation:** `COALESCE(base.ipeds_finance.total_fte_enrollment, bronze.eada.eada_fte_headcount)`. Prefers IPEDS-Finance annualized FTE (~74.5% of rows); falls back to EADA's 12-month headcount (~25.5% of rows); NULL when both sources are missing (< 1%). The single most load-bearing column for downstream per-FTE comparison. **Observed FTE-source mix (BSE-EAD-011 P1, ±5pp):** ipeds_finance ~74.5% / eada_fte_headcount ~25.5% / none < 1%. |

### FTE Source Provenance (NEW in Base)

Three columns that surface the methodological mix introduced by the §5 Option-C COALESCE. The `fte_source` enum is the primary signal; the two booleans surface per-source presence.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| fte_source | (methodological provenance) | text (enum: `ipeds_finance` / `eada_fte_headcount` / `none`) | NOT NULL | true | false | Explicit per-row stamp of which FTE source produced `total_fte_enrollment`. `'ipeds_finance'` (preferred — annualized FTE from `base.ipeds_finance`); `'eada_fte_headcount'` (fallback — 12-month headcount from `bronze.eada.eada_fte_headcount`); `'none'` (both sources missing — bounded ≤ 1% by BSE-EAD-009). **Tautology (BSE-EAD-012 P0):** `total_fte_enrollment IS NULL ⟺ fte_source = 'none'`. **IPEDS-preference invariant (BSE-EAD-013 P0):** every UNITID present in `base.ipeds_finance` with non-null FTE stamps `'ipeds_finance'` (zero violations) — catches partial silent LEFT-JOIN failures. |
| has_ipeds_finance_fte | — | boolean | NOT NULL | false | false | True iff `base.ipeds_finance.total_fte_enrollment` was non-null for this UNITID. Surfaces per-source presence independently of which source was *chosen*. ~74.5% true in the current load. |
| has_eada_fte | — | boolean | NOT NULL | false | false | True iff `bronze.eada.eada_fte_headcount` was non-null for this UNITID. Expected ~100% true (EADA's `EFTotalCount` is populated on every row). |

### Per-FTE Derivations (NEW in Base)

The three per-student normalizations of the monetary inputs. Computed in Silver via plain-double arithmetic. NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **No imputation.** Each derivation inherits the `fte_source` of its denominator.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| athletic_spend_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student athletic spending. **Derivation:** `total_athletic_expenses / total_fte_enrollment`. **NULL semantics:** NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **Arithmetic invariant (BSE-EAD-008 P0):** `athletic_spend_per_fte × total_fte_enrollment ≈ total_athletic_expenses` within $1 wherever all three are non-null. **Range guard (BSE-EAD-004 P0):** `≥ 0` where non-null. The EADA-side aura input per spec §6 Decision 11. |
| athletic_revenue_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student athletic revenue. **Derivation:** `total_athletic_revenue / total_fte_enrollment`. Same NULL rule. **Range guard (BSE-EAD-005 P0):** `≥ 0` where non-null. Carried as a context column on `consumable.institution_aura` (not an aura input). |
| recruiting_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student recruiting spending. **Derivation:** `recruiting_expenses / total_fte_enrollment`. Same NULL rule. **Range guard (BSE-EAD-006 P0):** `≥ 0` where non-null. **Note:** ~17.8% of institutions report `recruiting_expenses = 0` (real zeros, not suppressions); their `recruiting_per_fte` is therefore exactly 0.0 — valid, not a DQ failure. |

### Subsidy Intensity (NEW in Base)

A cross-field ratio with no FTE dependency. Computed in Silver via plain-double arithmetic with `NULLIF` semantics on the denominator.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| athletic_subsidy_ratio | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO | numeric (unitless ratio) | NULLABLE | true | false | The institution-level athletic subsidy ratio. Positive = subsidized (revenue < expenses); near 0 = self-sustaining; negative = profitable. **Derivation:** `(total_athletic_expenses − total_athletic_revenue) / NULLIF(total_athletic_expenses, 0)`. **NULL semantics:** NULL when either operand is NULL or `total_athletic_expenses = 0`. **Range guard (BSE-EAD-007 P0, EDA-calibrated 2026-04-30):** `[-3.0, 1.0]` where non-null (original spec band `[-1.0, 1.0]` was empirically falsified by 4 institutions reflecting institutional-transfer accounting — Binghamton −2.92, Haskell Indian Nations −2.56, Kennedy-King −1.57, Rust College −1.43; not data defects). **Distribution invariant (BSE-EAD-010 P1, EDA-calibrated):** `P50 == 0 ∧ P5 < 0 ∧ P95 == 0` (OPE/EADA ledger convention bunches the distribution at zero — see conceptual model "OPE/EADA Ledger Convention" section). Independent of FTE source. Carried as a context column on `consumable.institution_aura` (not an aura input — see spec §2 Decision 11). |

### Pipeline Provenance

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | (Brightsmith convention) | date | NOT NULL | false | false | Date the source Bronze data was loaded. Direct passthrough of `bronze.eada.load_date`. Identical across all rows in a single Base promote run. |
| ingested_at | (Brightsmith convention) | timestamp | NOT NULL | false | false | UTC wall-clock recording when this Base row was promoted from Bronze. Identical across all rows in a single Base promote run. Distinct from `source_load_date` (the *Bronze* ingest date). |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 18 | Total attributes |
| 1 | Surrogate key (record_id) |
| 1 | Natural key (unitid) |
| 6 | Analytical CDE attributes (unitid, total_fte_enrollment, fte_source, athletic_spend_per_fte, athletic_revenue_per_fte, recruiting_per_fte, athletic_subsidy_ratio — seven total CDE flags) |
| 0 | PII attributes |
| 9 | NOT NULL attributes (record_id, unitid, institution_name, reporting_year, fte_source, has_ipeds_finance_fte, has_eada_fte, source_load_date, ingested_at) |
| 7 | Passthroughs from Bronze (unitid, institution_name, reporting_year, total_athletic_expenses, total_athletic_revenue, recruiting_expenses, eada_fte_headcount) |
| 1 | Cross-source COALESCE (total_fte_enrollment) |
| 3 | FTE-source provenance (fte_source, has_ipeds_finance_fte, has_eada_fte) |
| 4 | Derivations (athletic_spend_per_fte, athletic_revenue_per_fte, recruiting_per_fte, athletic_subsidy_ratio) |
| 1 | Surrogate-key-derived (record_id) |
| 2 | Provenance (source_load_date, ingested_at) |

---

## Type Domain Definitions

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. UNITID is a numeric long; record_id is a string hash. | LongType for unitid; StringType for record_id |
| text | A human-readable label, display value, or short categorical enum. | StringType |
| numeric (USD) | A dollar-denominated measurement, promoted verbatim from Bronze. | DoubleType |
| numeric (USD per FTE) | A per-student dollar rate computed in Base. | DoubleType |
| numeric (unitless ratio) | A dimensionless ratio computed in Base. | DoubleType |
| numeric (FTE-or-headcount) | A 12-month enrollment count — FTE when sourced from IPEDS Finance; headcount when sourced from EADA's `EFTotalCount`. The `fte_source` column disambiguates. | DoubleType |
| numeric (headcount) | EADA's `EFTotalCount`, a 12-month enrollment headcount. | DoubleType |
| numeric (year) | A calendar/academic year used for filtering and single-vintage enforcement. | IntegerType |
| boolean | Per-source presence flag. | BooleanType |
| date | A calendar date without time component. | DateType |
| timestamp | A point in time used for pipeline auditing. | TimestampType |

---

## Derivation Rules (Plain-English)

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | Apply `compute_grain_id(row, ['unitid'], prefix='ead')`. Output format: `ead-<16 hex>`. | unitid |
| total_fte_enrollment | Take `base.ipeds_finance.total_fte_enrollment` if non-null, else `bronze.eada.eada_fte_headcount`, else NULL. | base.ipeds_finance.total_fte_enrollment, bronze.eada.eada_fte_headcount |
| fte_source | `'ipeds_finance'` when the IPEDS-Finance value was non-null; `'eada_fte_headcount'` when the IPEDS-Finance value was NULL but the EADA headcount was non-null; `'none'` when both were NULL. | base.ipeds_finance.total_fte_enrollment, bronze.eada.eada_fte_headcount |
| has_ipeds_finance_fte | True iff `base.ipeds_finance.total_fte_enrollment` was non-null for this UNITID. | base.ipeds_finance.total_fte_enrollment |
| has_eada_fte | True iff `bronze.eada.eada_fte_headcount` was non-null for this UNITID. | bronze.eada.eada_fte_headcount |
| athletic_spend_per_fte | Divide `total_athletic_expenses` by `total_fte_enrollment`. Return NULL if either operand is NULL or `total_fte_enrollment ≤ 0`. | total_athletic_expenses, total_fte_enrollment |
| athletic_revenue_per_fte | Divide `total_athletic_revenue` by `total_fte_enrollment`. Same NULL rule. | total_athletic_revenue, total_fte_enrollment |
| recruiting_per_fte | Divide `recruiting_expenses` by `total_fte_enrollment`. Same NULL rule. | recruiting_expenses, total_fte_enrollment |
| athletic_subsidy_ratio | `(total_athletic_expenses − total_athletic_revenue) / NULLIF(total_athletic_expenses, 0)`. NULL when either operand is NULL or expenses is 0. Independent of FTE. | total_athletic_expenses, total_athletic_revenue |
| source_load_date | Direct passthrough from `bronze.eada.load_date`. | bronze.eada.load_date |
| ingested_at | Generated at promote time via `datetime.now(tz=UTC)`. | -- |

---

## Passthrough Attributes

| Attribute | Source |
|-----------|--------|
| unitid | `bronze.eada.unitid` (verbatim) |
| institution_name | `bronze.eada.institution_name` (verbatim) |
| reporting_year | `bronze.eada.reporting_year` (verbatim) |
| total_athletic_expenses | `bronze.eada.total_athletic_expenses` (verbatim) |
| total_athletic_revenue | `bronze.eada.total_athletic_revenue` (verbatim) |
| recruiting_expenses | `bronze.eada.recruiting_expenses` (verbatim) |
| eada_fte_headcount | `bronze.eada.eada_fte_headcount` (verbatim) |

---

## Nullability Semantics

| Attribute Group | NOT NULL? | Reason |
|----------------|-----------|--------|
| Identity (record_id, unitid, institution_name, reporting_year) | Yes | Every row must have a complete identity stamp. NULL would mean the row bypassed Bronze ingestion. |
| Monetary inputs | NO | Bronze observes 100% non-null in 2022–23, but the schema permits NULL because (a) future cycles may suppress small-program totals and (b) the suppression-sentinel scrub maps unparseable values to NULL by design. Honest NULL propagation. |
| EADA headcount (`eada_fte_headcount`) | NO | Bronze observes ~100% non-null, but the schema permits NULL for cycle-drift safety. The COALESCE then produces `fte_source = 'none'` for the rare double-NULL case. |
| FTE denominator (`total_fte_enrollment`) | NO | The COALESCE produces NULL only when both sources are missing (< 1%). |
| FTE source provenance (fte_source, has_ipeds_finance_fte, has_eada_fte) | Yes | Every row must carry an explicit source stamp — this is the methodological-mix governance signal. The `'none'` enum value handles the double-NULL case rather than NULLing the column. |
| Per-FTE derivations | NO | NULL-cascade by design when either operand is missing or `total_fte_enrollment ≤ 0`. |
| Subsidy ratio | NO | NULL-cascade by design (NULLIF on the denominator). |
| Provenance (source_load_date, ingested_at) | Yes | Pipeline-stamped — a NULL would mean the promote bypassed `promote()`. |

---

## Key Constraints (Logical)

| Constraint | Type | Source |
|------------|------|--------|
| `unitid IS NOT NULL` for every row | Total | Inherited from Bronze |
| `unitid` is unique (within a single `reporting_year`) | Uniqueness | BSE-EAD-002 (P0) |
| `record_id IS NOT NULL` and unique | Validity + Uniqueness | BSE-EAD-003 (P0) |
| Row count == Bronze row count | Conservation | BSE-EAD-001 (P0) |
| `athletic_spend_per_fte ≥ 0` where non-null | Range | BSE-EAD-004 (P0) |
| `athletic_revenue_per_fte ≥ 0` where non-null | Range | BSE-EAD-005 (P0) |
| `recruiting_per_fte ≥ 0` where non-null | Range | BSE-EAD-006 (P0) |
| `athletic_subsidy_ratio ∈ [-3.0, 1.0]` where non-null (silver-EDA-calibrated) | Range | BSE-EAD-007 (P0) |
| `athletic_spend_per_fte × total_fte_enrollment ≈ total_athletic_expenses` within $1 | Arithmetic invariant | BSE-EAD-008 (P0) |
| `fte_source ∈ {'ipeds_finance', 'eada_fte_headcount', 'none'}` AND `'none'` rate ≤ 1% | Validity (enum + completeness) | BSE-EAD-009 (P0) |
| `athletic_subsidy_ratio` distribution: `P50 == 0 ∧ P5 < 0 ∧ P95 == 0` (OPE ledger convention) | Plausibility (EDA-calibrated) | BSE-EAD-010 (P1) |
| `fte_source` distribution: ipeds_finance ~74.5% / eada_fte_headcount ~25.5% (±5pp) | Distribution (EDA-calibrated) | BSE-EAD-011 (P1) |
| `total_fte_enrollment IS NULL ⟺ fte_source = 'none'` | Arithmetic / Provenance | BSE-EAD-012 (P0) |
| Every UNITID with non-null `base.ipeds_finance.total_fte_enrollment` stamps `fte_source = 'ipeds_finance'` (zero violations) | Cross-source / Provenance (IPEDS-preference invariant) | BSE-EAD-013 (P0) |

All 13 rules pass against the landed Iceberg table (`governance/dq-rules/base-eada.json`; scorecard `governance/dq-scorecards/base-eada-20260501T210828Z.{json,md}`, snapshot `973879610917339278`, 2,040 rows, 11 P0 + 2 P1, all PASS).

---

## Cardinality

- **2,040 rows** in the current academic year 2022–23 cycle.
- Matches Bronze 1:1 (BSE-EAD-001 P0 conservation invariant; 0 row delta).
- FTE-source mix: ipeds_finance ~74.5% / eada_fte_headcount ~25.5% / none < 1% (BSE-EAD-011 P1).
- Future cycles append. Single-cycle snapshots today; multi-cycle backfill is a future-amendment concern.

---

## Modeling Decisions

1. **One flat row per (institution, cycle).** Same as Bronze; no normalization of monetary fields into a long-form measurement table. Matches `base.ipeds_finance` precedent.

2. **`total_fte_enrollment` modeled as a single COALESCE'd column with explicit `fte_source` provenance, not as two separate columns (one per source).** Two-column-per-source would force every downstream consumer to repeat the same COALESCE — risking formula drift and re-introducing the source-selection logic at every read site. Computing the COALESCE once in Base, with the chosen denominator and its provenance present in the same row, is the single source of truth. Downstream consumers who require methodological homogeneity can filter on `fte_source = 'ipeds_finance'`.

3. **`fte_source` typed as a text enum, not as separate boolean columns.** The two booleans (`has_ipeds_finance_fte`, `has_eada_fte`) carry per-source *presence*; `fte_source` carries the *chosen* source. They are not redundant — the IPEDS-preference invariant (BSE-EAD-013) is a relationship between `has_ipeds_finance_fte` and `fte_source`. An institution might have both sources present (`has_ipeds_finance_fte = TRUE ∧ has_eada_fte = TRUE`) but the COALESCE chose IPEDS-Finance — the enum tells you which.

4. **Derivations live alongside their numerators and denominator.** Carrying the Bronze numerator and the COALESCE'd FTE denominator in the same Base row as the per-FTE derivation is what makes BSE-EAD-008 self-auditable at rest. Splitting them would force the DQ rule into a cross-row join. Same pattern as `base.ipeds_finance`.

5. **No imputation, no substitution.** Per the standing user constraint and per spec §2 Decision #8, NULLs propagate honestly through the per-FTE and subsidy-ratio derivations. The COALESCE is **not** imputation — it is *source selection between two equally-real measurements*, with the choice surfaced as provenance. There is no fallback value or sentinel; when both sources are missing, the FTE column is genuinely NULL and `fte_source` is `'none'`.

6. **`athletic_subsidy_ratio` is dimensionally unitless and uses `NULLIF` semantics on the denominator.** Mirrors `base.ipeds_finance.marketing_ratio`. Reading `0.0` means break-even; `0.2` means 20% of expenses are subsidized; negative means profitable. The `NULLIF(total_athletic_expenses, 0)` gate prevents division-by-zero on the (unobserved-but-possible) zero-expense rows.

7. **`record_id` uses prefix `ead` (not `aur`).** Per spec §5: `compute_grain_id(row, ['unitid'], prefix='ead')`. The downstream consumable uses prefix `aur` (different namespace) so that hash collisions across zones are impossible by construction. Same pattern as `base.ipeds_finance` (`ipf` at Base, `ifp` at Consumable).

8. **`reporting_year` typed as `Integer`, not `Date`.** Same as Bronze — discrete academic-year-start value used for filtering and single-vintage enforcement, not a date for arithmetic. Matches the `fiscal_year` decision at `base.ipeds_finance`.

9. **`total_fte_enrollment` is CDE.** It is the universal denominator for every per-FTE derivation and the trip-wire for the source-selection bug. Wrong values here mis-state every per-FTE rate downstream. The `fte_source` column is also CDE because it governs which methodological cohort each row belongs to.

10. **The three monetary inputs are NOT analytical-CDE *at Base*.** They become CDE at the consumable layer (per spec §6 Data Contract) once exposed to the downstream `aura_score` and `athletic_subsidy_ratio` fields. At Base, the per-FTE rates and the subsidy ratio carry the analytical CDE flag. (Note: `unitid`, `total_athletic_expenses`, and `total_athletic_revenue` were Bronze CDEs under the upstream-feeder lens — see `governance/cde-tagging/raw-eada.md` — but the *Base* analytical CDE flag follows the derivation, not the raw input.)

11. **No SCD2.** Same as Bronze: latest single-cycle snapshot. Multi-cycle history would require partitioning on `reporting_year` and extending the dedup grain.

---

## Scope and Boundaries

- This logical model covers `base.eada` only.
- Bronze raw data (`bronze.eada`) is the source for seven passthrough columns and one COALESCE fallback (`eada_fte_headcount`); fully modeled in `raw-eada-logical.md`.
- The cross-source IPEDS-Finance LEFT-JOIN source (`base.ipeds_finance.total_fte_enrollment`) is consumed here and fully modeled in `base-ipeds-finance-logical.md`.
- The downstream Gold fusion (`consumable.institution_aura`) is a downstream consumer and will be modeled separately once aura-score EDA finalizes the formula.
- No imputation, no substitution. Standing user constraints re-affirmed.
- PII: None. Confirmed by `governance/pii-scans/base-eada-pii-scan.md`.
