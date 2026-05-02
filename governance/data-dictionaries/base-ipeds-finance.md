# Data Dictionary: base.ipeds_finance

**Table:** `base.ipeds_finance`
**Zone:** Silver (Base)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) (§5)
**Transformer:** [src/silver/ipeds_finance_base.py](../../src/silver/ipeds_finance_base.py)
**Runner:** [scripts/promote_ipeds_finance_base.py](../../scripts/promote_ipeds_finance_base.py)
**Conceptual model:** [governance/models/base-ipeds-finance-conceptual.md](../models/base-ipeds-finance-conceptual.md)
**Logical model:** [governance/models/base-ipeds-finance-logical.md](../models/base-ipeds-finance-logical.md)
**Physical model:** [governance/models/base-ipeds-finance-physical.md](../models/base-ipeds-finance-physical.md)
**DQ Rules:** [governance/dq-rules/base-ipeds-finance.json](../dq-rules/base-ipeds-finance.json) (19 rules: 13 P0 + 6 P1)
**DQ Scorecard:** [governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md](../dq-scorecards/full-pipeline-ipeds-finance-scorecard.md) (44/44 PASS across all three zones)
**Bronze data dictionary:** [governance/data-dictionaries/raw-ipeds-finance.md](raw-ipeds-finance.md)
**Domain Context:** [governance/domain-context.md](../domain-context.md) § IPEDS Finance Survey
**EDA Report:** [governance/eda/raw-ingest-ipeds-finance-eda.md](../eda/raw-ingest-ipeds-finance-eda.md)
**Source:** `bronze.ipeds_finance` (1:1 promote with derivations)
**Grain:** one row per institution (`unitid`) per fiscal cycle
**Observed rows:** 2,675 (FY2023 cycle, snapshot `1277941459950591173`)
**Documented by:** @doc-generator
**Date:** 2026-04-30

---

## What This Table Contains

The Silver/Base layer of the IPEDS Finance pipeline. Every row is one U.S. 4-year bachelor's-granting institution in one fiscal cycle, promoted 1:1 from Bronze with no row-grain change. The table carries the four Bronze numerators verbatim (the three monetary fields plus the EFIA-sourced FTE denominator) and adds **four new derivations**: three per-FTE rates (`institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`) and one cross-field ratio (`marketing_ratio`). All four derivations are pure arithmetic on Bronze inputs; none use imputation or substitution.

Per spec §5 the per-FTE math is:

```
metric_per_fte = metric / total_fte_enrollment
                  → NULL when either operand is NULL or total_fte_enrollment ≤ 0
```

And the marketing-ratio is:

```
marketing_ratio = institutional_support_expenses / NULLIF(instruction_expenses, 0)
                   → NULL when either operand is NULL or instruction is 0
```

**Why these derivations live in Base, not Consumable:** The per-FTE rates are the *canonical institution-scale finance signal*. Carrying the raw dollars without per-FTE normalization would force every downstream consumer (the consumable, the EADA fusion in `full-pipeline-eada.md`, future receipts/comparison specs) to repeat the same division — risking formula drift and re-introducing the EFIA-vs-EFFY-vs-EFTOTLT taxonomy bug at every read site. Computing per-FTE once in Base, with both operands present in the same row, is the single source of truth for institution-scale comparison. The marketing-ratio lives in Base for the same reason — and because the downstream EADA fusion needs it as a Base-zone composite input.

**Form mix (FY2023):** F1A 30.6% (819) / F2 59.0% (1,579) / F3 10.4% (277) = 2,675 total. Exactly matches Bronze (BSE-IPF-001 conservation invariant).

**CDE density:** 6 of 15 columns are CDE candidates (40%) — `unitid` (the join key), `total_fte_enrollment` (the universal denominator and EFIA-bug trip-wire), and the four derivations (`institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio`). The four monetary inputs are NOT CDE-flagged at Base; they become CDE at the consumable layer (per spec §6 Data Contract) once exposed to the downstream EADA fusion that needs raw dollars for composite ratios.

**PII:** None. IPEDS Finance is institution-level reporting by design.

**The arithmetic invariants are self-auditable at rest.** Because each Base row carries both the Bronze numerator and its per-FTE derivation, BSE-IPF-008/009 (`per_fte × total_fte_enrollment ≈ original_numerator` within $1) and BSE-IPF-010 (`marketing_ratio × instruction ≈ institutional_support` within $1) can be checked without a cross-row join. All three pass against the landed table.

---

## Field Inventory

### Grain & Identifiers

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `record_id` | `compute_grain_id(row, ['unitid'], prefix='ipf')` | string | Yes | No | (Brightsmith convention) | Deterministic surrogate key for this Base row, format `ipf-<16 hex>`. Pure function of `unitid` with constant prefix `ipf` — re-running the promote yields the same hash for the same UNITID (verified: Stanford UNITID 243744 → `ipf-267f20f48b4b772f` across multiple runs). The Consumable layer uses prefix `ifp-` (distinct namespace) so no cross-zone hash collisions are possible. **Observed:** 2,675/2,675 non-null and 2,675/2,675 unique. |
| `unitid` | `bronze.ipeds_finance.unitid` (passthrough) | long | Yes | **Yes** | [BT-001](../business-glossary.json) | The 6-digit IPEDS UNITID, promoted verbatim from Bronze. Natural key and dedup grain. The universal join key linking IPEDS Finance to every other institution-keyed table in the pipeline. **Observed:** 2,675 distinct values, 0 nulls. |
| `institution_name` | `bronze.ipeds_finance.institution_name` (passthrough) | string | Yes | No | [BT-002](../business-glossary.json) | The official name of the institution (HD `INSTNM`-derived), promoted verbatim from Bronze. Display-only — do not use for joins. **Observed:** 100% non-null. |

### Reporting Form & Cycle

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `report_form` | `bronze.ipeds_finance.report_form` (passthrough) | string | Yes | No | (proposed) BT-IPF-ACCOUNTING-FORM | The IPEDS Finance form the institution filed on. Three values: `F1A` (public, GASB), `F2` (private nonprofit, FASB), `F3` (private for-profit). Carried unchanged from Bronze. Drives the per-form segmentation used by the BSE-IPF-015a/b/c marketing-ratio thresholds. **Observed (FY2023):** F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%). |
| `fiscal_year` | `bronze.ipeds_finance.fiscal_year` (passthrough) | int | Yes | No | (proposed) BT-IPF-FISCAL-CYCLE | The IPEDS fiscal year this row covers (current load: `2023`). Constant across every row in a single load (single-vintage invariant inherited from Bronze RAW-IPF-013). |

### Monetary Inputs (Bronze Passthroughs)

The three Bronze monetary fields, carried verbatim. They are the *numerator inputs* for the per-FTE derivations and the marketing-ratio. NULLs propagate honestly — no imputation, no substitution.

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `institutional_support_expenses` | `bronze.ipeds_finance.institutional_support_expenses` (passthrough) | double | No | No | [BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES](../business-glossary.json) | The institution's total annual expenses for executive management, fiscal operations, public relations, fundraising, legal services, administrative computing, and similar administrative functions. Often a proxy for "marketing and administration overhead" in budget-transparency analyses. Sourced from F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1`. **Observed (FY2023):** 100.00% non-null. The numerator of `marketing_ratio` and the input for `institutional_support_per_fte`. |
| `instruction_expenses` | `bronze.ipeds_finance.instruction_expenses` (passthrough) | double | No | No | [BT-IPF-INSTRUCTION-EXPENSES](../business-glossary.json) | The institution's total annual expenses for instructional divisions — faculty salaries, instructional materials, departmental research, public service not separately budgeted. Sourced from F1A `F1C011` / F2 `F2E011` / F3 `F3E011`. **Observed (FY2023):** 100.00% non-null. The denominator of `marketing_ratio` and the input for `instruction_per_fte`. |
| `endowment_value` | `bronze.ipeds_finance.endowment_value` (passthrough) | double | No | No | [BT-IPF-ENDOWMENT-VALUE](../business-glossary.json) | End-of-year market value of the institution's endowment funds. Reported on F1A and F2 only — for-profit institutions (F3) have no `F3H` family on their finance schedule and report NULL by design. Sourced from F1A `F1H02` / F2 `F2H02`. **Observed (FY2023):** 76.00% non-null overall (2,033 / 2,675); 100% structural NULL on F3 (277/277). The 642 NULLs split as ~277 F3 structural + ~365 F2/F1A institutions without endowment. The input for `endowment_per_fte`. |

### Enrollment Denominator (Bronze Passthrough)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `total_fte_enrollment` | `bronze.ipeds_finance.total_fte_enrollment` (passthrough; computed at Bronze as `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` from EFIA) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | The institution's 12-month total full-time-equivalent enrollment, sourced from the IPEDS EFIA (12-Month Instructional Activity) survey. **Critical taxonomy:** EFIA is the right source — NOT EFFY (which is unduplicated 12-month *headcount*, broken out by `EFFYALEV` and at the wrong grain) and NOT EF Part A `EFTOTLT` (which is fall-snapshot headcount). The downstream BSE-IPF-017 P99 < $500K trip-wire on `instruction_per_fte` exists specifically to catch any future regression to the wrong field. **Observed (FY2023):** 97.94% non-null (2,620 / 2,675); the 55 NULL rows cause every per-FTE value in the same row to NULL-cascade. The single most load-bearing column for downstream analysis — the universal denominator. |

### Per-FTE Derivations (NEW in Base)

The three per-student normalizations of the monetary inputs. Computed in Silver via plain-double arithmetic. **NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. No imputation.**

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `institutional_support_per_fte` | **Derivation:** `institutional_support_expenses / total_fte_enrollment` (NULL when either operand is NULL or FTE ≤ 0) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student spending on administration, fundraising, executive direction, legal services, and similar institutional-support functions. Computed in this Base zone for the first time. **NULL semantics:** NULL when either the numerator or `total_fte_enrollment` is NULL or non-positive. **Observed (FY2023):** 97.94% non-null. **Arithmetic invariant (BSE-IPF-009):** `institutional_support_per_fte × total_fte_enrollment ≈ institutional_support_expenses` within $1 wherever all three are non-null — passes by construction (plain-double divide-then-multiply roundtrip is exact). **Spot check:** Stanford UNITID 243744 = $42,427.78 ($810,116,000 / 19,094 FTE). |
| `instruction_per_fte` | **Derivation:** `instruction_expenses / total_fte_enrollment` (same NULL rule) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student spending on instructional divisions — the "what students get" cost-of-instruction signal. Computed in this Base zone for the first time. **NULL semantics:** same as above. **Observed (FY2023):** 97.94% non-null. **Arithmetic invariant (BSE-IPF-008):** `instruction_per_fte × total_fte_enrollment ≈ instruction_expenses` within $1 — passes by construction. **Tripwire (BSE-IPF-017):** P99 must be < $500K — guards against an EFFY-headcount-vs-FTE field-selection regression. **Observed P99:** $78.8K, well under threshold; the sole row > $500K (UT Southwestern Medical Center, $634K) is a legitimate specialty medical school with a small medical-student denominator. **Spot check:** Stanford UNITID 243744 = $140,522.42 ($2,683,135,000 / 19,094 FTE). |
| `endowment_per_fte` | **Derivation:** `endowment_value / total_fte_enrollment` (same NULL rule) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student endowment value — the "wealth backing" signal. Computed in this Base zone for the first time. **NULL semantics:** NULL when either operand is NULL or FTE ≤ 0; F3 rows are 100% NULL by design (endowment is structurally NULL on F3). **Observed (FY2023):** 74.69% non-null. The non-null rate is intentionally below `instruction_per_fte`'s 97.94% because endowment NULLs add to the FTE NULLs. **Arithmetic invariant (BSE-IPF-009):** symmetric with the other per-FTE rates. **Spot check:** Stanford UNITID 243744 = $1,911,327.80 ($36,494,893,000 / 19,094 FTE) — among the highest endowment-per-FTE in the country. |

### Marketing Intensity (NEW in Base)

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `marketing_ratio` | **Derivation:** `institutional_support_expenses / NULLIF(instruction_expenses, 0)` (NULL when either operand is NULL or instruction is 0) | double | No | **Yes** | (proposed) BT-IPF-MARKETING-RATIO | The dimensionless ratio of institutional support expenses to instruction expenses. Higher = relatively more spending on administration, fundraising, marketing, and recruiting compared to teaching. Reading: `1.0` means parity (admin ≈ instruction); `5.0` means 5× as much spent on administration as instruction. Computed in this Base zone for the first time; has no FTE dependency, so its non-null rate is broader than the per-FTE rates (98.84% vs 97.94%). **NULL semantics:** NULL when either operand is NULL or instruction is exactly 0 (mirrors `NULLIF` semantics). The 31 NULL rows are the small set of zero-instruction system-office UNITIDs. **Observed (FY2023):** 98.84% non-null (2,644 / 2,675). **Per-form P99 (FY2023 actual):** F1A 14.15 / F2 6.35 / F3 8.75 — note F1A's high P99 reflects the public-system-administrative-office cluster (LA CCD Office, U Colorado System Office, etc.), which legitimately carry huge administrative spend with little instruction. The DQ thresholds in BSE-IPF-015a/b/c (15.0 / 7.0 / 11.0) are calibrated against these values with cross-vintage drift headroom. **Arithmetic invariant (BSE-IPF-010):** `marketing_ratio × instruction_expenses ≈ institutional_support_expenses` within $1 wherever all three are non-null — passes by construction. **Spot check:** Stanford UNITID 243744 = 0.30193 ($810,116,000 / $2,683,135,000) — Stanford spends ~30 cents on administration for every dollar on instruction. |

### Pipeline Provenance

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `source_load_date` | `bronze.ipeds_finance.load_date` (passthrough, cast to DATE) | date | Yes | No | (Brightsmith convention) | Calendar date the source Bronze data was loaded (UTC). Direct passthrough of `bronze.ipeds_finance.load_date`. Identical across all rows in a single Base promote run. Used by downstream freshness DQ to reach the original Bronze ingest date even after multiple Silver/Gold promote timestamps stack up. |
| `ingested_at` | `datetime.utcnow()` at promote time | timestamp | Yes | No | (Brightsmith convention) | UTC wall-clock recording when this Base row was promoted from Bronze. Identical across all rows in a single Base promote run. Distinct from `source_load_date` (the *Bronze* ingest date). |

---

## Data Quality Rules

The 19 Base DQ rules are defined in [governance/dq-rules/base-ipeds-finance.json](../dq-rules/base-ipeds-finance.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|----------------|
| BSE-IPF-001 | P0 | (row count) | Base row count == Bronze row count (conservation). |
| BSE-IPF-002 | P0 | `unitid` | Uniqueness within `fiscal_year`. |
| BSE-IPF-003 | P0 | `record_id` | Non-null + unique. |
| BSE-IPF-004 | P0 | `instruction_per_fte` | `≥ 0` where non-null. |
| BSE-IPF-005 | P0 | `institutional_support_per_fte` | `≥ 0` where non-null. |
| BSE-IPF-006 | P0 | `endowment_per_fte` | `≥ 0` where non-null. |
| BSE-IPF-007 | P0 | `marketing_ratio` | `≥ 0` where non-null. |
| BSE-IPF-008 | P0 | `instruction_per_fte`, `instruction_expenses`, `total_fte_enrollment` | Arithmetic invariant: `instruction_per_fte × total_fte_enrollment ≈ instruction_expenses` within $1. |
| BSE-IPF-009 | P0 | per-FTE × FTE ≈ raw | Same invariant for institutional_support and endowment. |
| BSE-IPF-010 | P0 | `marketing_ratio`, `instruction_expenses`, `institutional_support_expenses` | Arithmetic invariant: `marketing_ratio × instruction_expenses ≈ institutional_support_expenses` within $1. |
| BSE-IPF-011 | P0 | `instruction_per_fte` | Non-null `≥ 85%` (observed 97.94%). |
| BSE-IPF-012 | P0 | `institutional_support_per_fte` | Non-null `≥ 85%` (observed 97.94%). |
| BSE-IPF-013 | P1 | `endowment_per_fte` | Non-null `≥ 70%` (observed 74.69%; tightened from spec 55% per EDA recommendation). |
| BSE-IPF-014 | P0 | `marketing_ratio` | Non-null `≥ 95%` (observed 98.84%; tightened from spec 85% per EDA recommendation). |
| BSE-IPF-015a/b/c | P1 | `marketing_ratio` (per-form) | F1A P99 < 15.0 / F2 P99 < 7.0 / F3 P99 < 11.0 (calibrated per EDA §6.5 strong recommendation; FY2023 actuals: F1A 14.15 / F2 6.35 / F3 8.75). |
| BSE-IPF-016 | P1 | `endowment_per_fte` | At least one row > $1M (passes trivially — F2 P99 alone = $1.44M). |
| BSE-IPF-017 | P1 | `instruction_per_fte` | P99 < $500,000 (FTE-bug tripwire; observed P99 = $78.8K). |

All 19 rules pass against the landed table. Full scorecard: `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` (44/44 PASS across all three zones).

---

## Caveats for Consumers

1. **Per-FTE values cascade NULL when FTE is missing.** 55 institutions have NULL `total_fte_enrollment`, which causes all three per-FTE rates and (in many cases) the marketing-ratio to be NULL on the same row. This is honest data — those rows are simply not usable for per-student comparison. The `data_completeness_tier` at the consumable layer summarizes this.

2. **F3 endowment-per-FTE is always NULL.** F3 rows have `endowment_value = NULL` by design (no `F3H` family on the for-profit schedule), so `endowment_per_fte` cascades to NULL on 100% of F3 rows. This is the correct behavior; downstream consumers should not flag this as a data-quality failure.

3. **Public-system-administrative-office UNITIDs drive F1A's marketing-ratio P99.** A small but real cluster of UNITIDs (LA Community College District Office, U Colorado System Office, U Hawaii System Office, etc.) report system-wide administrative overhead with little or no instruction. They have legitimately huge marketing-ratios (F1A P99 = 14.15 in this load). The DQ rule BSE-IPF-015a is calibrated to 15.0 specifically to tolerate this cluster while still catching genuine outliers. **The optional v1.4 cleanup recommendation** in the EDA report (filter UNITIDs whose name matches `' Office' OR ' System' OR 'Chancellor'`) was deferred — it would alter the Base grain and is not v1.3 scope.

4. **`record_id` prefix is `ipf` at Base, `ifp` at Consumable.** Different namespaces. If you see `ipf-...` in a consumable read or `ifp-...` in a Base read, the wrong prefix was passed to `compute_grain_id()` somewhere upstream.

5. **No imputation.** Per spec §2 Decision #8 and the standing user constraint, NULLs propagate honestly. The three per-FTE derivations and the marketing-ratio do not substitute fallback values; missing data stays missing through the entire pipeline.

6. **`marketing_ratio` is dimensionally unitless and uses `NULLIF` semantics on the denominator.** Reading `1.0` means parity; `5.0` means 5× admin spend over instruction. The `NULLIF(instruction_expenses, 0)` gate prevents division-by-zero on the 34 zero-instruction system-office rows.

7. **Arithmetic invariants are self-auditable at rest.** Because the Bronze numerators are carried alongside the Base derivations in the same row, BSE-IPF-008/009/010 can be checked without a cross-row join. All three pass.

8. **Cycle vintage is FY2023, not the spec narrative's FY24.** NCES has not yet released FY24 finance files (HTTP 404 on `F2324_F1A.zip` etc.). The Base table reflects the Bronze re-ingest for FY2023 (snapshot `2955168649587464831`). The Base transformer is cycle-agnostic; promoting to FY24 once published is a parameter change, not a code change.

9. **No SCD2.** Latest single-fiscal-cycle snapshot. Multi-cycle history would require partitioning on `fiscal_year` and extending the dedup grain.

10. **The four monetary inputs are NOT CDE-flagged at Base.** They become CDE at the consumable layer (per spec §6 Data Contract) once exposed to the downstream EADA fusion that needs raw dollars for composite ratios. At Base, the per-FTE rates and marketing-ratio carry the analytical CDE flag.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-30 | Initial data dictionary for Base table `base.ipeds_finance` per spec v1.3. 15 fields documented (3 identity + 2 reporting + 3 monetary inputs + 1 FTE + 4 derivations + 2 provenance), 6 flagged CDE, 0 flagged PII. Field types and nullability verified against landed Iceberg metadata (snapshot `1277941459950591173`). | @doc-generator |
