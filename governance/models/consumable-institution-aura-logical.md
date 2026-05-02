# Logical Model: consumable-institution-aura

**Status:** PROPOSED
**Mode:** Greenfield (cross-source fusion)
**Zone:** Gold (Consumable)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §6
**Conceptual model:** [consumable-institution-aura-conceptual.md](consumable-institution-aura-conceptual.md)
**Base logical models:** [base-eada-logical.md](base-eada-logical.md), [base-ipeds-finance-logical.md](base-ipeds-finance-logical.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    CONSUMABLE_INSTITUTION_AURA {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        numeric endowment_per_fte
        numeric institutional_support_per_fte
        numeric instruction_per_fte
        numeric marketing_ratio
        numeric athletic_spend_per_fte
        numeric athletic_revenue_per_fte
        numeric athletic_subsidy_ratio
        text athletic_fte_source
        numeric aura_score
        numeric aura_score_continuous
        text aura_score_version
        text aura_score_basis
        boolean has_ipeds_finance
        boolean has_eada
        text coverage_tier
        timestamp promoted_at
    }
```

---

## Design Rationale: Single Denormalized Cross-Source Fusion Table

The conceptual model identifies ten entities. Per the Brightsmith Gold Consumable zone pattern, all ten collapse into a single denormalized 19-attribute table. This is appropriate because:

1. All conceptual relationships are 1:1 per row — the grain is one row per UNITID per snapshot.
2. The cross-source fusion is naturally row-aligned — every Base row from either side contributes to exactly one consumable row, with NULLs filling the un-reported side.
3. Gold Consumable tables are designed as wide, query-ready tables for downstream MCP and frontend consumption.
4. Carrying the four Finance signals + three Athletics signals + the FTE-source provenance + the aura composite + the basis stamp + the coverage tier all in the same row is what enables CON-AUR-007 (the `marketing_ratio × instruction ≈ institutional_support` invariant) and CON-AUR-034 (the `aura_score IS NULL iff aura_score_basis IS NULL` invariant) to be self-auditable at rest.
5. This matches the established pattern from `consumable.ipeds_finance_profile` (denormalized 15-column profile) and `consumable.regional_price_parities` (denormalized 15-column reference profile).

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per U.S. postsecondary institution (`unitid`) per snapshot |
| **Natural key fields** | `unitid` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['unitid'], prefix='aur')`) |
| **Uniqueness constraints** | Zero duplicates on `unitid` (CON-AUR-003 P0). Zero duplicates on `record_id` (CON-AUR-004 P0). |
| **Expected cardinality** | 3,223 rows (FULL OUTER JOIN of `base.ipeds_finance` 2,675 + `base.eada` 2,040; CON-AUR-001 P0 conservation: row count ∈ [max(2,675, 2,040), 2,675 + 2,040] = [2,675, 4,715]). |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from.

### Identity

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | (Brightsmith convention) | identifier | NOT NULL | false | false | Deterministic surrogate key computed via `compute_grain_id(row, ['unitid'], prefix='aur')`. Format: `aur-<16 hex chars>`. The `aur` prefix is distinct from upstream Base prefixes (`ipf` for `base.ipeds_finance`, `ead` for `base.eada`) and the sibling `consumable.ipeds_finance_profile` prefix (`ifp`) — no cross-zone hash collisions are possible. |
| unitid | BT-001 | identifier | NOT NULL | true | false | The 6-digit IPEDS UNITID. Coalesced from `base.ipeds_finance.unitid` and `base.eada.unitid` (both sides P0 non-null). Natural key. The universal join key for downstream consumers. |
| institution_name | BT-002 | text | NOT NULL | false | false | Institution display name. `COALESCE(f.institution_name, e.institution_name)`. Display-only — do not use for joins. |

### Finance Signals (from `base.ipeds_finance` Base)

The four IPEDS Finance per-FTE / ratio signals carried forward verbatim from `base.ipeds_finance`. NULL when `has_ipeds_finance = FALSE` (the 548 athletics-only rows) or when the underlying FTE denominator was NULL.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| endowment_per_fte | BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student endowment value. Promoted verbatim from `base.ipeds_finance`. **EDA observed:** 1,998 / 3,223 rows non-null (62.0%). NULL on for-profits (F3 structural NULL) and 548 athletics-only rows. **Aura input** — feeds `rp_endowment`. |
| institutional_support_per_fte | BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student administrative-and-overhead spending. Promoted verbatim. NOT a direct aura input — the canonical aura input on the marketing dimension is `marketing_ratio` (which is derived from this column over `instruction_per_fte`); CON-AUR-007 enforces the arithmetic identity. |
| instruction_per_fte | BT-IPF-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student instructional spending. Promoted verbatim. NOT a direct aura input — see above. |
| marketing_ratio | BT-IPF-MARKETING-RATIO | numeric (unitless ratio) | NULLABLE | true | false | The dimensionless ratio of institutional support expenses to instruction expenses. Higher = more spend on administration vs. teaching. Promoted verbatim from `base.ipeds_finance.marketing_ratio`. **EDA observed:** P5=0.183 / P50=0.545 / P95=2.345; long pathological tail dominated by IPEDS reporting artifacts (system offices with near-zero instruction). **Aura input** — feeds `rp_marketing` and is the only signal that produces non-NULL aura on the `one_term_marketing_only` basis. |

### Athletics Signals (from `base.eada` Base)

The three EADA per-FTE / ratio signals carried forward verbatim from `base.eada`. NULL when `has_eada = FALSE` (the 1,183 finance-only rows). The FTE denominator behind the per-FTE / ratio columns is recorded by `athletic_fte_source` (next section).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| athletic_spend_per_fte | (proposed) BT-AUR-ATHLETIC-SPEND-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student athletic-program expense. Promoted verbatim from `base.eada`. **EDA observed:** P5=$148 / P50=$1,579 / P95=$7,177 across all 2,040 EADA reporters; meaningfully bimodal between the two `athletic_fte_source` strata (`ipeds_finance` median $1,990, `eada_fte_headcount` median $673 — see §5 Option-C amendment). **Aura input** — feeds `rp_athletic`. |
| athletic_revenue_per_fte | (proposed) BT-AUR-ATHLETIC-REVENUE-PER-FTE | numeric (USD per FTE) | NULLABLE | true | false | Per-student athletic-program revenue. Promoted verbatim. **Context column only** — NOT an aura input. |
| athletic_subsidy_ratio | BT-EAD-ATHLETIC-SUBSIDY-RATIO | numeric (unitless ratio) | NULLABLE | true | false | The fraction of athletic expenses not covered by athletic revenue: `(expenses − revenue) / expenses`. **Context column only — explicitly EXCLUDED from the aura composite per spec §2 Decision 11.** Surface for downstream consumers that want a "subsidy intensity" signal; do not read into aura. **EDA observed:** 1,284 / 2,040 rows are exactly 0 (silver-zone clipping artifact); column is heavily right-clipped at the EADA grand-total grain because EADA convention requires reported revenues to at least equal expenses. |

### FTE Source Provenance (Option-C Amendment, 2026-04-30)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| athletic_fte_source | (proposed) BT-AUR-FTE-SOURCE | text (enum: `ipeds_finance`/`eada_fte_headcount`/`none`) | NULLABLE | true | false | Provenance for the FTE denominator behind the three EADA per-FTE / ratio columns. `ipeds_finance` (1,492 rows, all `coverage_tier='both'`) — IPEDS-Finance annualized FTE; preferred. `eada_fte_headcount` (548 rows, all `coverage_tier='athletics_only'`) — EADA's own 12-month student headcount. `none`/NULL (1,183 rows, all `coverage_tier='finance_only'`) — no EADA reporting. The two FTE definitions are NOT identical; downstream consumers can stratify or filter on this column for FTE-methodology consistency. Pass-through from `base.eada.fte_source`. |

### Aura Score and Provenance

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| aura_score | BT-AUR-AURA-SCORE | numeric (integer 1–10) | NULLABLE | true | false | Integer 1–10 aura score. **Derivation:** `ROUND(aura_score_continuous)` where `aura_score_continuous = 1.0 + 9.0 * clip((raw_score − 0.1413) / (0.9400 − 0.1413), 0, 1)` and `raw_score = 0.65 * MAX(available_rp_*) + 0.35 * MEAN(available_rp_*)`. Available rp_* values are determined per-row by `aura_score_basis`. NULL ⇔ `aura_score_basis IS NULL`. **EDA observed (v1):** integer 1..10 all 10 buckets populated across 2,644 non-NULL aura rows; median = 7; band distribution [1,3]=17.4% / [4,6]=25.7% / [7,10]=56.9%. |
| aura_score_continuous | (Brightsmith convention) | numeric (double 1.0–10.0) | NULLABLE | true | false | Pre-rounding continuous value, retained for downstream auditability and for the CON-AUR-013 round-correctness invariant. NULL when `aura_score` is NULL. |
| aura_score_version | (Brightsmith convention) | text | NOT NULL | false | false | Provenance stamp identifying the formula version. Always `"v1"` for rows produced by this snapshot (CON-AUR-012 P0). v0-draft was rejected during EDA after failing 11/14 anchor schools. |
| aura_score_basis | BT-AUR-AURA-SCORE-BASIS | text (enum: `three_term`/`two_term_finance_only`/`two_term_no_endowment`/`one_term_marketing_only`/NULL) | NULLABLE | true | false | The 5-value enum recording which input set was used to compute the aura score for this row. **EDA observed:** `three_term` 1,417 / `two_term_finance_only` 579 / `two_term_no_endowment` 75 / `one_term_marketing_only` 573 / NULL 579. NULL ⇔ aura_score IS NULL (CON-AUR-034 P0). The 4-value non-NULL enum was expanded from 3 → 5 during EDA after discovering 677 finance reporters with NULL endowment (mostly for-profits). |

### Coverage Flags

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| has_ipeds_finance | (proposed) BT-AUR-HAS-IPEDS-FINANCE | boolean | NOT NULL | false | false | TRUE when the institution reports IPEDS Finance (i.e., `f.unitid IS NOT NULL` after the FULL OUTER JOIN). **EDA observed:** TRUE on 2,675 rows. |
| has_eada | (proposed) BT-AUR-HAS-EADA | boolean | NOT NULL | false | false | TRUE when the institution reports EADA (`e.unitid IS NOT NULL`). **EDA observed:** TRUE on 2,040 rows. |
| coverage_tier | BT-AUR-COVERAGE-TIER | text (enum: `both`/`finance_only`/`athletics_only`) | NOT NULL | true | false | 3-value enum classifying which sources contributed. `both` (1,492 / 46.3%) / `finance_only` (1,183 / 36.7%) / `athletics_only` (548 / 17.0%). CON-AUR-005 P0 enforces the closed enum domain; CON-AUR-006 P0 enforces that every row has at least one source TRUE. |

### Promotion Provenance

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| promoted_at | (Brightsmith convention) | timestamp | NOT NULL | false | false | UTC wall-clock recording when this consumable row was promoted. Identical across all rows in a single consumable promote run. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 19 | Total attributes |
| 1 | Surrogate key (record_id) |
| 1 | Natural key (unitid) |
| 12 | CDE attributes (unitid, endowment_per_fte, institutional_support_per_fte, instruction_per_fte, marketing_ratio, athletic_spend_per_fte, athletic_revenue_per_fte, athletic_subsidy_ratio, athletic_fte_source, aura_score, aura_score_continuous, aura_score_basis, coverage_tier — 13 CDE-flagged in total counting coverage_tier) |
| 0 | PII attributes |
| 8 | NOT NULL attributes (record_id, unitid, institution_name, aura_score_version, has_ipeds_finance, has_eada, coverage_tier, promoted_at) |
| 11 | NULLABLE attributes (the 4 finance signals, the 3 athletics signals, athletic_fte_source, aura_score, aura_score_continuous, aura_score_basis) |
| 7 | Base passthroughs (4 finance signals + 3 athletics signals; identity columns coalesced rather than passed through) |
| 1 | Base-passthrough-with-rename (athletic_fte_source from `base.eada.fte_source`) |
| 4 | Synthesized in this zone (aura_score, aura_score_continuous, aura_score_basis, coverage_tier) |
| 3 | Coverage flags / FULL-OUTER-derived (has_ipeds_finance, has_eada, plus coverage_tier above) |
| 1 | Versioning (aura_score_version) |
| 1 | Provenance (promoted_at) |
| 1 | Surrogate-key-derived (record_id) |

---

## Type Domain Definitions

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. | LongType for unitid; StringType for record_id |
| text | A human-readable label or display value. Constrained to a closed enum for `athletic_fte_source`, `aura_score_version`, `aura_score_basis`, `coverage_tier`. | StringType |
| numeric (USD per FTE) | A per-student dollar rate. | DoubleType |
| numeric (unitless ratio) | A dimensionless ratio. | DoubleType |
| numeric (integer 1–10) | A clamped integer score. | IntegerType |
| numeric (double 1.0–10.0) | A clamped continuous score. | DoubleType |
| boolean | A two-valued flag. | BooleanType |
| timestamp | A point in time used for pipeline auditing. | TimestampType |

---

## Derivation Rules (Plain-English)

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | Apply `compute_grain_id(row, ['unitid'], prefix='aur')`. Output format: `aur-<16 hex>`. | unitid |
| unitid | `COALESCE(f.unitid, e.unitid)` from FULL OUTER. | base.ipeds_finance.unitid, base.eada.unitid |
| institution_name | `COALESCE(f.institution_name, e.institution_name)`. | base.ipeds_finance.institution_name, base.eada.institution_name |
| has_ipeds_finance | `f.unitid IS NOT NULL`. | base.ipeds_finance.unitid |
| has_eada | `e.unitid IS NOT NULL`. | base.eada.unitid |
| coverage_tier | `CASE WHEN has_ipeds_finance AND has_eada THEN 'both' WHEN has_ipeds_finance THEN 'finance_only' WHEN has_eada THEN 'athletics_only' END`. CON-AUR-006 ensures the CASE is exhaustive. | has_ipeds_finance, has_eada |
| aura_score_basis | Per-row enum assignment based on which of `marketing_ratio`, `endowment_per_fte`, `athletic_spend_per_fte` are non-null. NULL when marketing is NULL (always, for athletics-only rows) or when all three are NULL. See conceptual model §"The 5-Value `aura_score_basis` Enum" for the full assignment table. | marketing_ratio, endowment_per_fte, athletic_spend_per_fte |
| aura_score_continuous | Population-level percent rank of each non-null input signal → take only the rp_* values for the row's basis → `raw_score = 0.65·MAX + 0.35·MEAN` of those values → `(raw_score − 0.1413) / (0.9400 − 0.1413)` → clamp to [0, 1] → stretch to [1.0, 10.0]. | marketing_ratio, endowment_per_fte, athletic_spend_per_fte (all population-level) |
| aura_score | `ROUND(aura_score_continuous)`. CON-AUR-013 (P0) recomputes and compares. | aura_score_continuous |
| aura_score_version | Constant `"v1"`. | -- |
| promoted_at | Generated at promote time via `datetime.now()` (UTC). | -- |

All 7 Base passthrough attributes (the 4 finance signals + 3 athletics signals) are direct passthroughs from `base.ipeds_finance` / `base.eada` with no transformation. `athletic_fte_source` is a renamed passthrough from `base.eada.fte_source`.

---

## Passthrough Attributes

| Attribute | Source |
|-----------|--------|
| endowment_per_fte | `base.ipeds_finance.endowment_per_fte` (verbatim) |
| institutional_support_per_fte | `base.ipeds_finance.institutional_support_per_fte` (verbatim) |
| instruction_per_fte | `base.ipeds_finance.instruction_per_fte` (verbatim) |
| marketing_ratio | `base.ipeds_finance.marketing_ratio` (verbatim) |
| athletic_spend_per_fte | `base.eada.athletic_spend_per_fte` (verbatim) |
| athletic_revenue_per_fte | `base.eada.athletic_revenue_per_fte` (verbatim) |
| athletic_subsidy_ratio | `base.eada.athletic_subsidy_ratio` (verbatim) |
| athletic_fte_source | `base.eada.fte_source` (verbatim, renamed) |

---

## Nullability Semantics

| Attribute Group | NOT NULL? | Reason |
|----------------|-----------|--------|
| Identity (record_id, unitid, institution_name) | Yes | Every row must have a complete identity stamp. UNITID is P0 non-null on both Base inputs. |
| Coverage flags (has_ipeds_finance, has_eada) | Yes | Every row in the FULL OUTER union has known TRUE/FALSE values for both flags by construction. |
| coverage_tier | Yes | CON-AUR-005 P0 enforces the closed 3-value enum. CON-AUR-006 P0 enforces that the CASE is exhaustive (every row has ≥1 source TRUE). |
| Finance signals (4) | NO | NULL on the 548 athletics-only rows; also NULL when underlying inputs were NULL upstream. Honest NULL propagation; standing user constraint "no substitution-based degraded states." |
| Athletics signals (3) | NO | NULL on the 1,183 finance-only rows; honest NULL propagation. |
| athletic_fte_source | NO | NULL on the 1,183 finance-only rows (no EADA reporting). |
| aura_score, aura_score_continuous, aura_score_basis | NO | NULL on the 579 rows where no usable signal exists (548 athletics-only + 31 zero-instruction edge cases). The three columns NULL together (CON-AUR-034 P0 enforces the iff). |
| aura_score_version | Yes | Pipeline-stamped — every row carries the formula version regardless of whether the score itself is NULL (the version stamp is for the *formula*, not for the score-existence). |
| promoted_at | Yes | Pipeline-stamped — NULL would mean the promote bypassed `promote()`. |

---

## Key Constraints (Logical)

| Constraint | Type | Source |
|------------|------|--------|
| Row count ∈ [max(N_finance, N_eada), N_finance + N_eada] = [2,675, 4,715]; observed 3,223 | FULL OUTER conservation | CON-AUR-001 (P0) |
| `unitid IS NOT NULL` for every row | Total | CON-AUR-002 (P0) |
| `unitid` is unique | Uniqueness | CON-AUR-003 (P0) |
| `record_id IS NOT NULL` and unique | Validity + Uniqueness | CON-AUR-004 (P0) |
| `coverage_tier ∈ {both, finance_only, athletics_only}` | Validity (enum) | CON-AUR-005 (P0) |
| Every row has ≥ 1 of (has_ipeds_finance, has_eada) = TRUE | Validity | CON-AUR-006 (P0) |
| `institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 wherever all three non-null | Arithmetic invariant | CON-AUR-007 (P0) |
| `aura_score ∈ [1, 10]` where non-null | Validity | CON-AUR-010 (P0) |
| `aura_score IS NULL` iff `aura_score_basis IS NULL` (v1 invariant — replaces spec-as-written `iff has_ipeds_finance = FALSE`) | Consistency | CON-AUR-011 (P0) |
| `aura_score_version = 'v1'` for every row | Provenance | CON-AUR-012 (P0) |
| `aura_score = ROUND(aura_score_continuous)` for every row where both non-null | Arithmetic | CON-AUR-013 (P0) |
| `aura_score_continuous ∈ [1.0, 10.0]` where non-null | Validity | CON-AUR-014 (P0) |
| `aura_score_basis ∈ {three_term, two_term_finance_only, two_term_no_endowment, one_term_marketing_only}` where non-null | Validity (enum) | CON-AUR-033 (P0) |
| `aura_score IS NULL ⇔ aura_score_basis IS NULL` (explicit iff) | Consistency | CON-AUR-034 (P0) |
| Aura UNITIDs without a `consumable.career_outcomes` counterpart ≤ 1,611 (drift cap) | Referential integrity (soft) | CON-AUR-020 (P1) |
| ≥ 90% of distinct UNITIDs in `consumable.career_outcomes` find a matching row here (live: 89.68% — 0.32 pp below threshold; documented as P1 drift in DQ scorecard) | Coverage (EDA-calibrated) | CON-AUR-021 (P1) |
| Stratified bucket coverage: per-stratum (4 strata by `aura_score_basis`) ≥ 4 of 10 buckets populated; overall ≥ 6 of 10 | Distribution (EDA-calibrated) | CON-AUR-030 (P1) |
| Aura score median ∈ [4, 7] (live: 7) | Distribution (EDA-calibrated) | CON-AUR-031 (P1) |
| 14 anchor schools produce their EDA-validated v1 scores exactly | Plausibility | CON-AUR-032 (P1) |

All 18 P0/P1 rules execute via `governance/dq-rules/consumable-institution-aura.json`; current execution: 14/14 P0 PASS, 4/5 P1 PASS (CON-AUR-021 0.32 pp short — see scorecard `governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.md`).

---

## Cardinality

- **3,223 rows** in the current load (2,675 IPEDS Finance + 2,040 EADA, FULL OUTER on UNITID with 1,492 dual-reporters).
- Coverage breakdown: `both` 1,492 (46.3%) / `finance_only` 1,183 (36.7%) / `athletics_only` 548 (17.0%).
- Aura basis breakdown: `three_term` 1,417 / `two_term_finance_only` 579 / `two_term_no_endowment` 75 / `one_term_marketing_only` 573 / NULL 579.
- Aura score band: [1,3]=17.4% / [4,6]=25.7% / [7,10]=56.9%; median = 7; all 10 integer buckets populated.
- UNITID overlap with `consumable.career_outcomes`: 89.68% (CON-AUR-021 floor: 90% — 0.32 pp drift).
- 14/14 anchor schools produce EDA-validated v1 scores exactly (CON-AUR-032).

---

## Modeling Decisions

1. **One flat row per UNITID per snapshot.** Cross-source FULL OUTER fusion preserves grain — every Base row from either side contributes one consumable row.

2. **`record_id` uses prefix `aur` — distinct from upstream Base prefixes (`ipf`, `ead`) and the sibling consumable prefix (`ifp`).** Cross-zone hash collisions impossible by construction.

3. **All 7 Base signal columns carried verbatim** (4 IPEDS Finance + 3 EADA). The consumable does not re-derive any of them. CON-AUR-007 (the marketing-ratio arithmetic identity) is an *invariant check* that carries the BSE-IPF-008/009/010 invariants forward into the consumable layer.

4. **`athletic_fte_source` retained as a column** (Option-C amendment 2026-04-30). Surfaces the FTE-methodology mix to downstream consumers; flagged as a methodological-provenance CDE.

5. **`athletic_subsidy_ratio` carried as a CONTEXT column ONLY.** Explicitly excluded from the aura composite per spec §2 Decision 11. EDA Item 6 verified by code inspection of all four candidate formulas.

6. **`aura_score_basis` is a 5-value enum (4 non-NULL + NULL).** Expanded from spec-as-written 3 values during EDA after discovering 677 finance reporters with NULL endowment. The two new cases (`two_term_no_endowment`, `one_term_marketing_only`) cover for-profits like Phoenix and Grand Canyon that the v0-draft formula scored too low because `COALESCE(rp_endowment, 0)` treated their NULL endowment as bottom-percentile.

7. **`aura_score_version = 'v1'` (NOT 'v0-draft').** EDA promoted to v1 on 2026-04-30 after the v0-draft formula failed 11/14 anchors. CON-AUR-012 enforces the v1 stamp.

8. **`aura_score IS NULL iff aura_score_basis IS NULL` (NOT `iff has_ipeds_finance = FALSE`).** Spec-as-written CON-AUR-011 used the legacy has_ipeds_finance shorthand; EDA discovered 31 zero-instruction-expense edge cases that have `has_ipeds_finance=TRUE` but no usable aura signal. The basis-tagged invariant is the faithful one. CON-AUR-011 was rewritten and CON-AUR-034 was added to enforce both forms of the iff.

9. **CON-AUR-030 stratifies by `aura_score_basis` (4 strata), NOT by `athletic_fte_source`.** EDA Item 7 verified that the 2 × 3 (`aura_score_basis × athletic_fte_source`) interaction grid is structurally degenerate — every aura-computed row uses `ipeds_finance` as its FTE source. Stratifying by basis tests the analytically meaningful axis.

10. **No imputation, no substitution.** Standing user constraints re-affirmed; NULLs propagate honestly through to the basis enum.

11. **No SCD2.** Same as Base/Bronze; latest-snapshot-only.

---

## Scope and Boundaries

- This logical model covers `consumable.institution_aura` only.
- Bronze raw data and Base data are fully modeled in their own logical models.
- The sibling `consumable.ipeds_finance_profile` is parallel to this aura consumable (both read from `base.ipeds_finance`); it is not upstream.
- MCP-zone fact sheets that may surface aura via Gemma tools are not in scope here.
- The pentagon-rendering frontend is not in scope here.
