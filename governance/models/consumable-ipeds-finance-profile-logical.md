# Logical Model: consumable-ipeds-finance-profile

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) §6
**Conceptual model:** [consumable-ipeds-finance-profile-conceptual.md](consumable-ipeds-finance-profile-conceptual.md)
**Base logical model:** [base-ipeds-finance-logical.md](base-ipeds-finance-logical.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    CONSUMABLE_IPEDS_FINANCE_PROFILE {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        text report_form
        numeric fiscal_year
        numeric total_fte_enrollment
        numeric instruction_expenses
        numeric institutional_support_expenses
        numeric endowment_value
        numeric institutional_support_per_fte
        numeric instruction_per_fte
        numeric endowment_per_fte
        numeric marketing_ratio
        text data_completeness_tier
        timestamp promoted_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies eight entities (Institution, Finance Profile, Accounting Form, Fiscal Cycle, Monetary Measurement, Per-FTE Derivation, Marketing Intensity, Data Completeness Tier, Promotion Provenance). Per the Brightsmith Gold Consumable zone pattern, all eight collapse into a single denormalized 15-attribute table. This is appropriate because:

1. All conceptual relationships are 1:1 per row — the grain is one (institution, fiscal cycle).
2. The source Base table is already a single flat table of 2,675 rows; there is no normalization benefit to splitting.
3. Gold Consumable tables are designed as wide, query-ready tables for downstream MCP and frontend consumption.
4. Carrying the raw expense passthroughs alongside their per-FTE derivations and the marketing-ratio in the same row is what enables CON-IFP-007 (the `marketing_ratio × instruction ≈ institutional_support` invariant) to be self-auditable at rest.
5. This matches the established pattern from `consumable.regional_price_parities` (denormalized 15-column reference profile).

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per U.S. 4-year bachelor's-granting postsecondary institution (`unitid`) for a single IPEDS fiscal cycle |
| **Natural key fields** | `unitid` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['unitid'], prefix='ifp')`) |
| **Uniqueness constraints** | Zero duplicates on `unitid` (CON-IFP-003 P0). Zero duplicates on `record_id` (CON-IFP-004 P0). |
| **Expected cardinality** | 2,675 rows. Matches Base 1:1 (CON-IFP-001 P0 conservation invariant). |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from.

### Identity & Reporting (Base Passthroughs)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | (Brightsmith convention) | identifier | NOT NULL | false | false | Deterministic surrogate key computed via `compute_grain_id(row, ['unitid'], prefix='ifp')`. Format: `ifp-<16 hex chars>`. Distinct from Base's `ipf-` prefix to keep hash namespaces clean. Verified: Stanford UNITID 243744 → `ifp-267f20f48b4b772f`. |
| unitid | BT-001 | identifier | NOT NULL | true | false | The 6-digit IPEDS UNITID. Promoted verbatim from `base.ipeds_finance.unitid`. Natural key. The universal join key for downstream consumers. |
| institution_name | BT-002 | text | NOT NULL | false | false | Institution display name. Promoted verbatim from Base. Display-only — do not use for joins. |
| report_form | (proposed) BT-IPF-ACCOUNTING-FORM | text (enum: `F1A`/`F2`/`F3`) | NOT NULL | false | false | The IPEDS Finance form the institution filed on. Carried unchanged from Base. Drives per-form interpretation — F3 rows have endowment structurally NULL. |
| fiscal_year | (proposed) BT-IPF-FISCAL-CYCLE | numeric (year) | NOT NULL | false | false | The IPEDS fiscal year (current load: 2023). Constant across batch. |

### Enrollment Denominator (Base Passthrough)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| total_fte_enrollment | (proposed) BT-IPF-PER-FTE | numeric (FTE) | NULLABLE | false | false | The institution's 12-month total full-time-equivalent enrollment. Promoted verbatim from Base. **Observed (FY23):** 97.94% non-null. Used by downstream consumers to denominate per-FTE comparisons or to weight aggregates. |

### Monetary Measurements (Newly Exposed at Consumable per spec §6 Decision)

The three raw dollar fields exposed at the consumable layer for downstream EADA composite-ratio computation. Per the v1.1 governance-reviewer ruling, this is a narrow, justified exception to the standard "consumable is shaped, not raw-pass-through" Brightsmith convention. The downstream `raw-ingest-eada.md` spec needs raw dollars to compute composite ratios like "athletic spending as % of institutional support" without back-joining to Base.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| instruction_expenses | BT-IPF-INSTRUCTION-EXPENSES | numeric (USD) | NULLABLE | true | false | The institution's total annual expenses for instructional divisions. Promoted verbatim from Base. Exposed at consumable for downstream EADA composite ratios. **Observed (FY23):** 100.00% non-null. **Sourced from F1A `F1C011` / F2 `F2E011` / F3 `F3E011`**. |
| institutional_support_expenses | BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES | numeric (USD) | NULLABLE | true | false | The institution's total annual expenses for executive management, fiscal operations, public relations, fundraising, and similar administrative functions. Promoted verbatim from Base. Exposed at consumable for downstream EADA composite ratios. **Observed (FY23):** 100.00% non-null. **Sourced from F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1`**. |
| endowment_value | BT-IPF-ENDOWMENT-VALUE | numeric (USD) | NULLABLE | true | false | End-of-year market value of the institution's endowment funds. Promoted verbatim from Base. Exposed at consumable for downstream EADA composite ratios. **Observed (FY23):** 76.00% non-null overall; 100% structural NULL on F3. **v1.4 INTERPRETATION GUIDANCE:** read alongside `endowment_value_provenance` — only ~25–31% of non-null F1A/F2 endowment values are institution-reported. |
| endowment_value_provenance (v1.4) | (proposed) BT-IPF-ENDOWMENT-PROVENANCE | text (enum: `R`/`A`/`P`/`Z`/`N` OR NULL) | NULLABLE | **true** | false | **NEW v1.4** — Renamed passthrough from `base.ipeds_finance.endowment_value_flag` per spec §2 Decision A. **Authoritative semantics (corrected v1.2):** `R` = Reported by institution; `A` = **Not applicable** (no endowment fund — exact `A`↔NULL coupling on `endowment_value`, invariant per BSE-IPF-020 P0); `N` = **Imputed using Nearest Neighbor procedure**; `P` = Imputed prior year; `Z` = Imputed zero. NULL on F3 by structure. **CDE per spec §6 Data Contract delta** — interpretation-changing for `endowment_value` and `endowment_per_fte`. **Longitudinal consumers must filter to `endowment_value_provenance = 'R'`** to limit to institution-reported populated values; verbatim filter-to-`R` guidance is carried at the data contract layer in `governance/data-contracts/consumable-ipeds-finance-profile.yaml::consumer_guidance.endowment_provenance`. Validated by CON-IFP-013 (P0 rename-fidelity passthrough check). |

### Per-FTE Derivations (Base Passthroughs)

The three per-student normalizations of the monetary inputs. Computed in Base; carried forward unchanged. The canonical institution-scale finance signal.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| institutional_support_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student administrative-and-overhead spending. Computed at Base as `institutional_support_expenses / total_fte_enrollment`. Promoted verbatim. **Observed (FY23):** 97.94% non-null. |
| instruction_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student instructional spending. Computed at Base as `instruction_expenses / total_fte_enrollment`. Promoted verbatim. **Observed (FY23):** 97.94% non-null. |
| endowment_per_fte | (proposed) BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student endowment value. Computed at Base as `endowment_value / total_fte_enrollment`. Promoted verbatim. **Observed (FY23):** 74.69% non-null. F3 rows are 100% NULL by design. |

### Marketing Intensity (Base Passthrough)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| marketing_ratio | (proposed) BT-IPF-MARKETING-RATIO | numeric (unitless ratio) | NULLABLE | true | false | The ratio of institutional support expenses to instruction expenses. Higher = relatively more spending on administration vs. teaching. Computed at Base as `institutional_support_expenses / NULLIF(instruction_expenses, 0)`. Promoted verbatim. **Observed (FY23):** 98.84% non-null. **Per-form P99:** F1A 14.15 / F2 6.35 / F3 8.75. CON-IFP-007 cross-checks the invariant `institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 wherever all three are non-null. |

### Data Completeness Tier (NEW in this Consumable)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| data_completeness_tier | (proposed) BT-IPF-DATA-COMPLETENESS-TIER | text (enum: `high`/`medium`/`low`/`insufficient`) | NOT NULL | true | false | Source-data-completeness signal classifying each row by the count of non-null **independent raw inputs**: `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment` (positive). **Derivation:** `4 → high`, `2-3 → medium`, `1 → low`, `0 → insufficient`. **Observed (FY23):** `high=1,998 (74.7%) / medium=677 (25.3%) / low=0 / insufficient=0`. **Per-form (FY23):** F1A `high:706, medium:113`; F2 `high:1,292, medium:287`; F3 `high:0, medium:277` — all F3 rows cap at `medium` because endowment is structurally NULL. **NOT a CIP→SOC crosswalk-confidence tier** — measures source-field non-null count, not crosswalk match quality. Renamed from `confidence_tier` in v1.1. |

### Promotion Provenance

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date (v1.4) | (Brightsmith convention) | date | NOT NULL | false | false | **NEW v1.4** — Restored passthrough from `base.ipeds_finance.source_load_date` per spec §2 Decision G (v1.3 dropped it; v1.4 restores it as a vintage-observability metadata field). Calendar date the source bronze data was loaded (UTC). Distinct from `fiscal_year` (the IPEDS reporting cycle) and from `promoted_at` (the consumable promote run timestamp). **Explicitly NOT CDE per spec §6 Data Contract delta** — vintage-observability metadata only; does not change downstream interpretation of any analytical column. Validated by CON-IFP-015 (P0 NOT NULL) and CON-IFP-016 (P1 within 400 days of `promoted_at`). |
| promoted_at | (Brightsmith convention) | timestamp | NOT NULL | false | false | UTC wall-clock recording when this consumable row was promoted from Base. Identical across all rows in a single consumable promote run. Distinct from Base's `ingested_at` (the Base promote stamp), Bronze's `ingested_at` (the Bronze ingest stamp), and the v1.4-restored `source_load_date` (which records the bronze ingest *date*, not the consumable promote *time*). |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 15 | Total attributes |
| 1 | Surrogate key (record_id) |
| 1 | Natural key (unitid) |
| 8 | CDE attributes (unitid, instruction_expenses, institutional_support_expenses, endowment_value, institutional_support_per_fte, instruction_per_fte, endowment_per_fte, marketing_ratio, data_completeness_tier — note unitid + 8 = 9 CDE-flagged total) |
| 0 | PII attributes |
| 7 | NOT NULL attributes (record_id, unitid, institution_name, report_form, fiscal_year, data_completeness_tier, promoted_at) |
| 8 | NULLABLE attributes (the three monetary inputs, the three per-FTE derivations, total_fte_enrollment, marketing_ratio) |
| 12 | Base passthroughs |
| 1 | Synthesized in this zone (data_completeness_tier) |
| 1 | Provenance (promoted_at) |
| 1 | Surrogate-key-derived (record_id) |

---

## Type Domain Definitions

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. | LongType for unitid; StringType for record_id |
| text | A human-readable label or display value. Constrained to a closed enum for `report_form` and `data_completeness_tier`. | StringType |
| numeric (USD) | A dollar-denominated raw measurement. | DoubleType |
| numeric (USD per FTE) | A per-student dollar rate. | DoubleType |
| numeric (unitless ratio) | A dimensionless ratio. | DoubleType |
| numeric (FTE) | A 12-month FTE enrollment count, may carry tenths. | DoubleType |
| numeric (year) | A discrete fiscal-year value. | IntegerType |
| timestamp | A point in time used for pipeline auditing. | TimestampType |

---

## Derivation Rules (Plain-English)

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | Apply `compute_grain_id(row, ['unitid'], prefix='ifp')`. Output format: `ifp-<16 hex>`. | unitid |
| data_completeness_tier | Count the number of non-null independent raw inputs out of four: `instruction_expenses` IS NOT NULL, `institutional_support_expenses` IS NOT NULL, `endowment_value` IS NOT NULL, `total_fte_enrollment` IS NOT NULL AND > 0. Then classify: 4 → `high`; 2 or 3 → `medium`; 1 → `low`; 0 → `insufficient`. | instruction_expenses, institutional_support_expenses, endowment_value, total_fte_enrollment |
| promoted_at | Generated at promote time via `datetime.now()` (UTC). | -- |

All other attributes are direct passthroughs from `base.ipeds_finance` with no transformation.

---

## Passthrough Attributes

| Attribute | Source |
|-----------|--------|
| unitid | `base.ipeds_finance.unitid` (verbatim) |
| institution_name | `base.ipeds_finance.institution_name` (verbatim) |
| report_form | `base.ipeds_finance.report_form` (verbatim) |
| fiscal_year | `base.ipeds_finance.fiscal_year` (verbatim) |
| total_fte_enrollment | `base.ipeds_finance.total_fte_enrollment` (verbatim) |
| instruction_expenses | `base.ipeds_finance.instruction_expenses` (verbatim) |
| institutional_support_expenses | `base.ipeds_finance.institutional_support_expenses` (verbatim) |
| endowment_value | `base.ipeds_finance.endowment_value` (verbatim) |
| institutional_support_per_fte | `base.ipeds_finance.institutional_support_per_fte` (verbatim) |
| instruction_per_fte | `base.ipeds_finance.instruction_per_fte` (verbatim) |
| endowment_per_fte | `base.ipeds_finance.endowment_per_fte` (verbatim) |
| marketing_ratio | `base.ipeds_finance.marketing_ratio` (verbatim) |

---

## Nullability Semantics

| Attribute Group | NOT NULL? | Reason |
|----------------|-----------|--------|
| Identity (record_id, unitid, institution_name, report_form, fiscal_year) | Yes | Every row must have a complete identity stamp. |
| Monetary inputs and FTE | NO | Honest NULL propagation — F3 endowment is structural NULL, FTE is NULL on 55 institutions. No substitution per standing user constraint. |
| Per-FTE derivations | NO | NULL-cascades from operands. |
| marketing_ratio | NO | NULL-cascades from operands and from zero-instruction. |
| data_completeness_tier | Yes | Always classifiable into one of the four enum values; the `insufficient` value covers the all-NULL-inputs degenerate case (zero rows observed in current load). CON-IFP-005 P0 enforces the closed enum domain. |
| promoted_at | Yes | Pipeline-stamped — NULL would mean the promote bypassed `promote()`. |

---

## Key Constraints (Logical)

| Constraint | Type | Source |
|------------|------|--------|
| Row count <= Base row count | Conservation (upper bound) | CON-IFP-001a (P0) — v1.4 split |
| Row count >= Base row count - 50 (absorbs system-office filter cycle drift) | Conservation (lower bound) | CON-IFP-001b (P1) — v1.4 split |
| `unitid IS NOT NULL` for every row | Total | CON-IFP-002 (P0) |
| `unitid` is unique within a single `fiscal_year` | Uniqueness | CON-IFP-003 (P0) |
| `record_id IS NOT NULL` and unique | Validity + Uniqueness | CON-IFP-004 (P0) |
| `data_completeness_tier ∈ {high, medium, low, insufficient}` | Validity (enum) | CON-IFP-005 (P0) |
| `data_completeness_tier` classification check (recompute and compare) | Arithmetic | CON-IFP-006 (P0) |
| `institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 wherever all three non-null | Arithmetic invariant | CON-IFP-007 (P0) |
| ≥ 88% of distinct UNITIDs in `consumable.career_outcomes` find a matching row here | Coverage (EDA-calibrated) | CON-IFP-008 (P1) |
| ≥ 86% watch-line on the same coverage check | Coverage (early-warning) | CON-IFP-008b (P2) |
| `data_completeness_tier='high'` rows ≥ 70% (FY23 measured 74.7%) | Distribution (EDA-calibrated) | CON-IFP-009 (P1) |
| `promoted_at IS NOT NULL` | Completeness | CON-IFP-010 (P0) |
| `fiscal_year` present + single-valued (mirrors RAW-IPF-013 at the consumer surface; closes consumable adversarial audit Gap 3 / R3) | Consistency | CON-IFP-012 (P0) — v1.4 |
| `endowment_value_provenance` rename-passthrough fidelity (every row matches `base.ipeds_finance.endowment_value_flag` for the same UNITID; 0 mismatches) | Conservation (column-level) | CON-IFP-013 (P0) — v1.4 |
| 0 rows match the §6 system-office filter exclusion clause (the 8-pattern AND 4-clause-numeric-proxy intersection) | Validity | CON-IFP-014 (P1) — v1.4 |
| `source_load_date IS NOT NULL` (mirrors base's NOT NULL guarantee per §2 Decision G) | Completeness | CON-IFP-015 (P0) — v1.4 |
| `source_load_date` within last 400 days of `promoted_at` | Freshness | CON-IFP-016 (P1) — v1.4 |

All 16 rules pass against the v1.4 landed table (`governance/dq-rules/consumable-ipeds-finance-profile.json`).

---

## Cardinality

- **2,630 rows** in the v1.4 FY2023 load (snapshot `950547093607535235`). 45 system-administrative-office rows excluded by the v1.4 row-filter against the 2,675-row base.
- Row-count band: [base_count - 50, base_count] (CON-IFP-001a P0 upper bound + CON-IFP-001b P1 lower bound). v1.4 replaces the v1.3 strict equality with a band that absorbs system-office filter cycle drift.
- v1.3 historical baseline (no filter): 2,675 rows.
- Form mix (v1.4 post-filter, FY2023): F1A ~803 / F2 ~1,560 / F3 ~267.
- Tier distribution (post-filter): `high≈1,998 / medium≈632 / low=0 / insufficient=0`.
- UNITID overlap with `consumable.career_outcomes`: 88.71% (cross-source coverage; CON-IFP-008 P1 floor 88%, CON-IFP-008b P2 watch-line 86%).

---

## Modeling Decisions

1. **One flat row per (institution, cycle).** Same as Base; 1:1 promotion.

2. **Raw expense passthroughs exposed at consumable.** Narrow exception to the "consumable is shaped, not raw-pass-through" Brightsmith convention. Justified by the named downstream consumer (`raw-ingest-eada.md`) and reviewer-approved per the v1.1 governance-reviewer ADV-6 ruling.

3. **`data_completeness_tier` synthesized from 4 independent raw inputs (NOT derived signals).** The v1.1 reformulation prevents the v1.0 inflation effect where a present `marketing_ratio` re-counted the two expense fields it was derived from. The reformulation also makes `total_fte_enrollment` first-class — when FTE is NULL all per-FTE values cascade to NULL, so the tier correctly de-rates the row to `medium` even if all dollar fields are present.

4. **F3 rows always cap at `medium`.** A direct, intentional consequence of including `endowment_value` as a tier input — F3 has no `F3H` family, so endowment is structurally NULL on 100% of F3 rows. The v1.1 rework was specifically designed to eliminate the v1.0 misleading-`high` classification for F3 rows. Verified: 0 F3 rows at `high`, all 277 at `medium`.

5. **`record_id` uses prefix `ifp` (not `ipf`).** Per spec §6 promote pattern: `compute_grain_id(row, ['unitid'], prefix='ifp')`. The Base table uses prefix `ipf`. Different namespaces ⇒ no cross-zone hash collision possible.

6. **No new derivations beyond `data_completeness_tier`.** This consumable is a pure shaping promote — no new arithmetic on the per-FTE values or the marketing-ratio. CON-IFP-007 (`institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio`) is an *invariant check*, not a derivation; it carries the BSE-IPF-008/009/010 invariants forward into the consumable layer.

7. **`data_completeness_tier` is NOT NULL with the `insufficient` enum covering the degenerate case.** The four-value enum closes the domain; CON-IFP-005 P0 enforces it. No row can ever be missing a tier.

8. **No imputation, no substitution.** Standing user constraints re-affirmed; NULLs propagate honestly.

9. **Disambiguation rename from `confidence_tier` to `data_completeness_tier` in v1.1.** Avoids collision with CIP→SOC crosswalk-confidence tiers used elsewhere in the project (e.g., `ConceptNormalizer` tiers). The downstream `raw-ingest-eada.md` is likely to introduce its own crosswalk-confidence tiers — the rename forecloses the ambiguity.

10. **No SCD2.** Same as Base/Bronze; latest-snapshot-only.

11. **v1.4 — `endowment_value_provenance` is a CDE renamed passthrough (NOT a derivation).** The column carries verbatim from `base.ipeds_finance.endowment_value_flag` (CON-IFP-013 P0 rename-fidelity). The CDE flag is true at consumable because the column is interpretation-changing for `endowment_value` and `endowment_per_fte` — longitudinal consumers must filter to `R`-provenance values. The verbatim filter-to-`R` guidance is carried at the data contract layer (`governance/data-contracts/consumable-ipeds-finance-profile.yaml::consumer_guidance.endowment_provenance`) per the @fp-data-reviewer disclaimer-gap concern.

12. **v1.4 — `source_load_date` restored at consumable as a NOT-CDE vintage-observability passthrough.** v1.3 dropped the column at the base→consumable promote; v1.4 restores it (CON-IFP-015 P0 NOT NULL; CON-IFP-016 P1 within 400 days of `promoted_at`). NOT CDE because the column is metadata about *when bronze was loaded*, not *how to interpret an analytical column*. Compare with `endowment_value_provenance`, which IS CDE.

13. **v1.4 — System-administrative-office row filter at the base→consumable promote.** This is the only row-count-changing filter in the IPEDS Finance pipeline. CON-IFP-001 split into 001a (P0 upper bound) + 001b (P1 lower bound `base_count - 50`); CON-IFP-014 (P1) verifies 0 surviving rows match the exclusion clause. The 8-pattern AND 4-clause-numeric-proxy SQL is the v1.3 final form — see consumable data dictionary "System-Office Filter" section for the verbatim SQL and the partial-enumeration of the 45 FY2023 excluded UNITIDs.

14. **v1.4 — `A`/`N` semantic correction.** The v1.3 EDA §7 narrative inverted the meanings of `A` and `N`. The v1.4 amendment uses the IPEDS Finance FY2023 dictionary as the AUTHORITATIVE source — `A` = Not applicable (with exact `A`↔NULL coupling), `N` = Imputed using Nearest Neighbor procedure. Every entry in this logical model uses the corrected semantics.

---

## Scope and Boundaries

- This logical model covers `consumable.ipeds_finance_profile` only.
- Bronze raw data and Base data are fully modeled in their own logical models.
- The downstream EADA fusion (`consumable.institution_aura`) lives in `raw-ingest-eada.md` and is not in this model.
- MCP-zone fact sheets that may surface this profile are not in scope here.
