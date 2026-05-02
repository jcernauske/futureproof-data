# Data Dictionary: consumable.ipeds_finance_profile

**Table:** `consumable.ipeds_finance_profile`
**Zone:** Gold (Consumable)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) (§6)
**Transformer:** [src/gold/ipeds_finance_profile.py](../../src/gold/ipeds_finance_profile.py)
**Runner:** [scripts/promote_ipeds_finance_profile.py](../../scripts/promote_ipeds_finance_profile.py)
**Conceptual model:** [governance/models/consumable-ipeds-finance-profile-conceptual.md](../models/consumable-ipeds-finance-profile-conceptual.md)
**Logical model:** [governance/models/consumable-ipeds-finance-profile-logical.md](../models/consumable-ipeds-finance-profile-logical.md)
**Physical model:** [governance/models/consumable-ipeds-finance-profile-physical.md](../models/consumable-ipeds-finance-profile-physical.md)
**DQ Rules:** [governance/dq-rules/consumable-ipeds-finance-profile.json](../dq-rules/consumable-ipeds-finance-profile.json) (11 rules: 8 P0 + 2 P1 + 1 P2)
**DQ Scorecard:** [governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md](../dq-scorecards/full-pipeline-ipeds-finance-scorecard.md) (44/44 PASS across all three zones)
**Data Contract:** [governance/data-contracts/consumable-ipeds-finance-profile.yaml](../data-contracts/consumable-ipeds-finance-profile.yaml)
**Base data dictionary:** [governance/data-dictionaries/base-ipeds-finance.md](base-ipeds-finance.md)
**Domain Context:** [governance/domain-context.md](../domain-context.md) § IPEDS Finance Survey
**EDA Report:** [governance/eda/raw-ingest-ipeds-finance-eda.md](../eda/raw-ingest-ipeds-finance-eda.md)
**Source:** `base.ipeds_finance` (1:1 promote with `data_completeness_tier` synthesis)
**Grain:** one row per institution (`unitid`) per fiscal cycle
**Observed rows:** 2,675 (FY2023 cycle, snapshot `6649279885162971471`)
**Documented by:** @doc-generator
**Date:** 2026-04-30

---

## What This Table Contains

The Gold/Consumable layer of the IPEDS Finance pipeline — the institution-level finance profile served to downstream consumers. Every row is one U.S. 4-year bachelor's-granting institution in one fiscal cycle, promoted 1:1 from Base with no row-grain change. The table:

1. **Carries forward 12 Base columns verbatim** — identity (`unitid`, `institution_name`, `report_form`, `fiscal_year`), the FTE denominator (`total_fte_enrollment`), three raw expense passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`), three per-FTE derivations (`institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`), and the marketing-ratio.
2. **Synthesizes one new field** — `data_completeness_tier`, classifying each row by the count of non-null **independent raw inputs**.
3. **Adds one provenance field** — `promoted_at`.
4. **Computes one new surrogate key** — `record_id` under the `ifp-` prefix.

There are no cross-source joins, no derived score, no row consolidation. The downstream EADA fusion (`consumable.institution_aura`, in the separate `raw-ingest-eada.md` spec) is the consumer that drives this profile's shape — the raw expense passthroughs let that fusion compute composite ratios like "athletic spending as percentage of institutional support" without back-joining to Base.

### The Raw Expense Passthrough Exception

Per the standard "consumable is shaped, not raw-pass-through" Brightsmith convention, raw dollar fields would not normally appear at consumable. Spec §6 makes a **narrow, explicit exception** for the three raw expense fields, justified by the named downstream consumer. The v1.1 governance-reviewer ruling approved this exception on three grounds:

1. Without the passthrough, downstream `raw-ingest-eada.md` would have to back-join to `base.ipeds_finance` — a more severe convention violation.
2. The dollar values were already exposed at Base, so there is no new information leak.
3. §6 explicitly documents the rationale on each of the three schema rows ("Raw passthrough USD. Exposed at consumable for downstream EADA composite ratios.").

### The Data Completeness Tier — v1.1 Reformulation

The `data_completeness_tier` field classifies each row by **source-data completeness**:

| Tier | Rule | Observed (FY2023) |
|------|------|-------------------|
| `high` | All 4 independent raw inputs present | 1,998 (74.7%) |
| `medium` | 2-3 of the 4 inputs present | 677 (25.3%) |
| `low` | Exactly 1 of the 4 inputs present | 0 |
| `insufficient` | 0 of the 4 inputs present | 0 |

The four independent raw inputs counted are:
- `instruction_expenses` IS NOT NULL
- `institutional_support_expenses` IS NOT NULL
- `endowment_value` IS NOT NULL
- `total_fte_enrollment` IS NOT NULL AND > 0

Two things make this formulation defensible:

1. **It counts independent raw inputs, NOT derived signals.** The v1.0 formulation mixed in `marketing_ratio`, which inflated tier scores because a present marketing_ratio re-counted the two expense fields it was derived from. The v1.1 reformulation makes the tier a pure function of source-field non-null count.

2. **`total_fte_enrollment` is first-class.** When FTE is missing, all three per-FTE values NULL-cascade and the row is unusable for per-student comparison even if all three dollar fields are present. By including FTE as a fourth tier input, the tier correctly de-rates such rows.

**Per-form (FY2023):** F1A `high:706, medium:113`; F2 `high:1,292, medium:287`; F3 `high:0, medium:277`. **Every F3 row caps at `medium` by construction** — F3 endowment is structurally NULL (no `F3H` family on the for-profit schedule), so F3 rows can never reach 4/4 inputs.

### Disambiguation From CIP→SOC Crosswalk-Confidence Tiers

The column was named `confidence_tier` in spec v1.0 and renamed to `data_completeness_tier` in v1.1 to disambiguate from the CIP→SOC crosswalk-confidence tiers used elsewhere in the project (e.g., the `ConceptNormalizer` tiers in the career-outcomes pipeline). The downstream `raw-ingest-eada.md` is likely to introduce its own crosswalk-confidence tiers. Without this rename, two semantically distinct "confidence_tier" fields could end up in adjacent tables. The business glossary entry **BT-IPF-DATA-COMPLETENESS-TIER** explicitly states: "**This is NOT a CIP→SOC crosswalk-confidence tier** — it measures source-field non-null count, not crosswalk match quality."

**Form mix (FY2023):** F1A 30.6% (819) / F2 59.0% (1,579) / F3 10.4% (277) = 2,675 total. Exactly matches Base (CON-IFP-001 conservation invariant).

**CDE density:** 9 of 15 columns are CDE candidates (60%) — `unitid` (the join key), the three raw expense passthroughs (newly CDE at consumable per spec §6 Data Contract — exposed for downstream EADA composite ratios), the three per-FTE derivations, the marketing-ratio, and the `data_completeness_tier`.

**PII:** None. IPEDS Finance is institution-level reporting by design.

---

## Field Inventory

### Grain & Identifiers

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `record_id` | `compute_grain_id(row, ['unitid'], prefix='ifp')` | string | Yes | No | (Brightsmith convention) | Deterministic surrogate key for this consumable row, format `ifp-<16 hex>`. Pure function of `unitid` with constant prefix `ifp` — re-running the promote yields the same hash for the same UNITID (verified: Stanford UNITID 243744 → `ifp-267f20f48b4b772f` across multiple runs). The Base layer uses prefix `ipf-` (distinct namespace) so no cross-zone hash collisions are possible. The `ifp` mnemonic is "**i**peds-**f**inance-**p**rofile". **Observed:** 2,675/2,675 non-null and 2,675/2,675 unique. |
| `unitid` | `base.ipeds_finance.unitid` (passthrough) | long | Yes | **Yes** | [BT-001](../business-glossary.json) | The 6-digit IPEDS UNITID. Promoted verbatim from Base. Natural key. The universal join key for downstream consumers — the EADA fusion in `raw-ingest-eada.md`, future receipts/comparison specs, and any MCP tool that surfaces institution finance signals. **Observed:** 2,675 distinct values, 0 nulls. |
| `institution_name` | `base.ipeds_finance.institution_name` (passthrough) | string | Yes | No | [BT-002](../business-glossary.json) | The official name of the institution (HD `INSTNM`-derived), promoted verbatim from Base. Display-only — do not use for joins. **Observed:** 100% non-null. |

### Reporting Form & Cycle

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `report_form` | `base.ipeds_finance.report_form` (passthrough) | string | Yes | No | (proposed) BT-IPF-ACCOUNTING-FORM | The IPEDS Finance form the institution filed on. Three values: `F1A` (public, GASB), `F2` (private nonprofit, FASB), `F3` (private for-profit). Carried unchanged from Base. Drives per-form interpretation — F3 rows have endowment structurally NULL and cap at `data_completeness_tier='medium'`. **Observed (FY2023):** F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%). |
| `fiscal_year` | `base.ipeds_finance.fiscal_year` (passthrough) | int | Yes | No | (proposed) BT-IPF-FISCAL-CYCLE | The IPEDS fiscal year this row covers (current load: `2023`). Constant across batch. |

### Enrollment Denominator (Base Passthrough)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `total_fte_enrollment` | `base.ipeds_finance.total_fte_enrollment` (passthrough; ultimately from Bronze EFIA) | double | No | No | (proposed) BT-IPF-PER-FTE | The institution's 12-month total full-time-equivalent enrollment, sourced from the IPEDS EFIA survey at Bronze. **Observed (FY2023):** 97.94% non-null (2,620 / 2,675). The 55 NULL rows cause the corresponding per-FTE values in the same row to be NULL and the `data_completeness_tier` to cap at `medium`. |

### Raw Expense Passthroughs (Newly Exposed at Consumable per spec §6)

The three raw dollar fields exposed at consumable for the named downstream EADA fusion. **Narrow exception** to the standard "consumable is shaped, not raw-pass-through" Brightsmith convention; reviewer-approved per the v1.1 governance-reviewer ruling.

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `instruction_expenses` | `base.ipeds_finance.instruction_expenses` (passthrough; ultimately from Bronze) | double | No | **Yes** | [BT-IPF-INSTRUCTION-EXPENSES](../business-glossary.json) | The institution's total annual expenses for instructional divisions — faculty salaries, instructional materials, departmental research. Sourced from F1A `F1C011` / F2 `F2E011` / F3 `F3E011`. **Newly CDE at consumable per spec §6 Data Contract** — exposed at this layer so the downstream `raw-ingest-eada.md` fusion can compute composite ratios like "athletic spending as percentage of instruction" without back-joining to Base. **Observed (FY2023):** 100.00% non-null. |
| `institutional_support_expenses` | `base.ipeds_finance.institutional_support_expenses` (passthrough) | double | No | **Yes** | [BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES](../business-glossary.json) | The institution's total annual expenses for executive management, fiscal operations, public relations, fundraising, legal services, and similar administrative functions. Often a proxy for "marketing and administration overhead." Sourced from F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1`. **Newly CDE at consumable per spec §6 Data Contract** — same EADA-composite-ratio rationale. **Observed (FY2023):** 100.00% non-null. |
| `endowment_value` | `base.ipeds_finance.endowment_value` (passthrough) | double | No | **Yes** | [BT-IPF-ENDOWMENT-VALUE](../business-glossary.json) | End-of-year market value of the institution's endowment funds. Reported on F1A and F2 only — for-profit institutions (F3) have no `F3H` family on their finance schedule and report NULL by design. Sourced from F1A `F1H02` / F2 `F2H02`. **Newly CDE at consumable per spec §6 Data Contract** — same EADA-composite-ratio rationale. **Observed (FY2023):** 76.00% non-null overall; 100% structural NULL on F3 (277/277). |

### Per-FTE Derivations (Base Passthroughs)

The three per-student normalizations of the monetary inputs. Computed in Base; carried forward unchanged. The canonical institution-scale finance signal.

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `institutional_support_per_fte` | `base.ipeds_finance.institutional_support_per_fte` (passthrough) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student spending on administration, fundraising, executive direction, legal services, and similar institutional-support functions. Computed at Base as `institutional_support_expenses / total_fte_enrollment`; promoted verbatim. NULL when either operand was NULL or `total_fte_enrollment ≤ 0`. **Observed (FY2023):** 97.94% non-null. **Stanford spot check (UNITID 243744):** $42,427.78. |
| `instruction_per_fte` | `base.ipeds_finance.instruction_per_fte` (passthrough) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student spending on instructional divisions — the "what students get" cost-of-instruction signal. Computed at Base as `instruction_expenses / total_fte_enrollment`. Promoted verbatim. **Observed (FY2023):** 97.94% non-null. **Tripwire (inherited from BSE-IPF-017):** P99 must be < $500K — guards against an EFFY-headcount-vs-FTE field-selection regression. **Stanford spot check (UNITID 243744):** $140,522.42. |
| `endowment_per_fte` | `base.ipeds_finance.endowment_per_fte` (passthrough) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student endowment value — the "wealth backing" signal. Computed at Base as `endowment_value / total_fte_enrollment`. Promoted verbatim. F3 rows are 100% NULL by design. **Observed (FY2023):** 74.69% non-null. **Stanford spot check (UNITID 243744):** $1,911,327.80. |

### Marketing Intensity (Base Passthrough)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `marketing_ratio` | `base.ipeds_finance.marketing_ratio` (passthrough) | double | No | **Yes** | (proposed) BT-IPF-MARKETING-RATIO | The dimensionless ratio of institutional support expenses to instruction expenses. Higher = relatively more spending on administration, fundraising, marketing, and recruiting compared to teaching. Computed at Base as `institutional_support_expenses / NULLIF(instruction_expenses, 0)`. Promoted verbatim. **NULL semantics:** NULL when either operand was NULL or instruction was 0. **Observed (FY2023):** 98.84% non-null. **Per-form P99:** F1A 14.15 / F2 6.35 / F3 8.75 — F1A's high P99 reflects the public-system-administrative-office cluster (legitimate IPEDS entities with system-wide overhead and little instruction). **Cross-check (CON-IFP-007):** `institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 wherever all three are non-null — invariant holds upstream and is preserved through the consumable layer. **Stanford spot check (UNITID 243744):** 0.30193. |

### Data Completeness Tier (NEW in this Consumable)

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `data_completeness_tier` | **Derivation:** Count non-null among `{instruction_expenses, institutional_support_expenses, endowment_value, total_fte_enrollment > 0}`. Then: `4 → high`; `2-3 → medium`; `1 → low`; `0 → insufficient`. | string | Yes | **Yes** | (proposed) BT-IPF-DATA-COMPLETENESS-TIER | Source-data-completeness signal classifying each row by the count of non-null **independent raw inputs**. **Closed enum:** `{high, medium, low, insufficient}` — CON-IFP-005 (P0) enforces the domain. **Renamed from `confidence_tier` in v1.1** to disambiguate from CIP→SOC crosswalk-confidence tiers used elsewhere in the project — **NOT a crosswalk-confidence tier; it measures source-field non-null count, not crosswalk match quality.** **Observed (FY2023):** `high=1,998 (74.7%) / medium=677 (25.3%) / low=0 / insufficient=0`. **Per-form:** F1A `high:706, medium:113`; F2 `high:1,292, medium:287`; F3 `high:0, medium:277` — F3 always caps at `medium` because endowment is structurally NULL. **CON-IFP-006 (P0)** re-computes the classification from the four independent raw inputs and compares; the rule passes by construction. **Stanford spot check (UNITID 243744):** `tier=high` (all 4 raw inputs present). **F3 spot check (UNITID 101116, South University-Montgomery):** `tier=medium` with `endowment_value=NULL`. |

### Promotion Provenance

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `promoted_at` | `datetime.utcnow()` at promote time | timestamp | Yes | No | (Brightsmith convention) | UTC wall-clock recording when this consumable row was promoted from Base. Identical across all rows in a single consumable promote run. Distinct from Base's `ingested_at` (the Base promote stamp) and Bronze's `ingested_at` (the Bronze ingest stamp); downstream consumers needing per-zone freshness should reference the fully-qualified table name. **Observed:** 100% non-null (CON-IFP-010 P0). |

---

## Data Quality Rules

The 11 Consumable DQ rules are defined in [governance/dq-rules/consumable-ipeds-finance-profile.json](../dq-rules/consumable-ipeds-finance-profile.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|----------------|
| CON-IFP-001 | P0 | (row count) | Consumable row count == Base row count (conservation). |
| CON-IFP-002 | P0 | `unitid` | Non-null in every row (100%). |
| CON-IFP-003 | P0 | `unitid` | Uniqueness within `fiscal_year`. |
| CON-IFP-004 | P0 | `record_id` | Non-null + unique. |
| CON-IFP-005 | P0 | `data_completeness_tier` | Domain ∈ {`high`, `medium`, `low`, `insufficient`}. |
| CON-IFP-006 | P0 | `data_completeness_tier` | Classification check: recompute the tier from the four independent raw inputs and compare. |
| CON-IFP-007 | P0 | `institutional_support_per_fte`, `instruction_per_fte`, `marketing_ratio` | Arithmetic invariant: `institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 wherever all three are non-null. |
| CON-IFP-008 | P1 | (cross-source coverage) | ≥ 88% of distinct UNITIDs in `consumable.career_outcomes` find a matching row in `consumable.ipeds_finance_profile` (FY2023 measured 88.71%; recalibrated from spec/EDA 90% per FY2023-vs-FY2022 cross-vintage drift). |
| CON-IFP-008b | P2 | (cross-source coverage early-warning) | ≥ 86% watch-line on the same coverage check (200-bp warning gap before P1 fires). |
| CON-IFP-009 | P1 | `data_completeness_tier` | `high` rows ≥ 70% (FY2023 measured 74.7%). |
| CON-IFP-010 | P0 | `promoted_at` | Non-null. |

All 11 rules pass against the landed table. Full scorecard: `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` (44/44 PASS across all three zones).

---

## Caveats for Consumers

1. **Three raw expense fields are passthroughs at consumable.** This is a narrow, named exception to Brightsmith's standard "consumable is shaped, not raw-pass-through" convention. Justified by the named downstream consumer (`raw-ingest-eada.md`). Read the raw values when computing composite ratios that involve athletic dollars or other cross-source dollar amounts; otherwise prefer the per-FTE rates or marketing-ratio for cross-institution comparison.

2. **`data_completeness_tier` is NOT a crosswalk-confidence tier.** It measures source-field non-null count for the four independent raw inputs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment` > 0). It does NOT measure CIP→SOC crosswalk match quality (those tiers live in the `ConceptNormalizer` and downstream career-outcomes pipeline). The business glossary entry BT-IPF-DATA-COMPLETENESS-TIER says this explicitly.

3. **Every F3 row is `tier=medium` by construction.** F3 endowment is structurally NULL (no `F3H` family on the for-profit schedule), so F3 rows can never reach 4/4 inputs. This is the desired behavior and is the central reason the v1.1 reformulation matters — the v1.0 formula would have classified some F3 rows as `high`, misleadingly suggesting they had complete endowment data.

4. **Per-FTE values cascade NULL when FTE is missing.** 55 institutions have NULL `total_fte_enrollment`, which causes all three per-FTE rates and (in many cases) the marketing-ratio to be NULL on the same row. Such rows cap at `tier=medium`. This is honest data — those institutions are simply not usable for per-student comparison.

5. **No imputation, no substitution.** Per spec §2 Decision #8 and the standing user constraint, NULLs propagate honestly from Bronze through Base into this consumable. The `data_completeness_tier` is the *summary* of these NULLs, not a substitute for them.

6. **`record_id` prefix is `ifp-` at Consumable, `ipf-` at Base.** Different namespaces. Verified: Stanford UNITID 243744 yields `ipf-267f20f48b4b772f` at Base and `ifp-267f20f48b4b772f` at Consumable.

7. **CON-IFP-008 calibrated to 88% (not 90%).** The spec wrote 90%; EDA on FY2022 measured 90.39%. After the FY2023 re-ingest, the actual coverage rate is 88.71%, so the DQ rule was recalibrated to 88% with a 0.71pp headroom and a P2 watch-line at 86% (CON-IFP-008b) for early warning. Both rules pass.

8. **No new arithmetic on derivations.** The consumable does not re-compute the per-FTE rates or the marketing-ratio — they are Base passthroughs. CON-IFP-007 (`institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001) is an invariant *check* that carries the BSE-IPF-008/009/010 invariants forward into the consumable layer.

9. **Cycle vintage is FY2023.** Same as Base; the consumable is cycle-agnostic and promotes whatever fiscal year Base presents.

10. **Field IDs 1-15 are stable.** Future schema evolution (e.g., adding a separate CIP→SOC crosswalk-confidence tier as a new column, or surfacing additional Bronze fields) must allocate IDs ≥ 16 and never rebind 1-15. Standard Iceberg-evolution discipline.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-30 | Initial data dictionary for Consumable table `consumable.ipeds_finance_profile` per spec v1.3. 15 fields documented (3 identity + 2 reporting + 1 FTE + 3 raw expense passthroughs + 3 per-FTE derivations + 1 marketing-ratio + 1 tier + 1 provenance), 9 flagged CDE, 0 flagged PII. Field types and nullability verified against landed Iceberg metadata (snapshot `6649279885162971471`). | @doc-generator |
