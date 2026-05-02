# Data Dictionary: consumable.institution_aura

**Table:** `consumable.institution_aura`
**Zone:** Gold (Consumable)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) (§6)
**Transformer:** [src/gold/institution_aura.py](../../src/gold/institution_aura.py) (640 lines)
**Conceptual model:** [governance/models/consumable-institution-aura-conceptual.md](../models/consumable-institution-aura-conceptual.md)
**Logical model:** [governance/models/consumable-institution-aura-logical.md](../models/consumable-institution-aura-logical.md)
**Physical model:** [governance/models/consumable-institution-aura-physical.md](../models/consumable-institution-aura-physical.md)
**DQ Rules:** [governance/dq-rules/consumable-institution-aura.json](../dq-rules/consumable-institution-aura.json) (19 rules: 14 P0 + 5 P1)
**DQ Scorecard:** [governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.md](../dq-scorecards/consumable-institution-aura-20260501T235038Z.md) (14/14 P0 PASS, 4/5 P1 PASS — CON-AUR-021 0.32 pp short)
**Chaos Report:** [governance/chaos-reports/consumable-institution-aura-chaos.md](../chaos-reports/consumable-institution-aura-chaos.md) (10/10 caught)
**Data Contract:** [governance/data-contracts/consumable-institution-aura.yaml](../data-contracts/consumable-institution-aura.yaml)
**EDA Report:** [governance/eda/consumable-institution-aura-eda.md](../eda/consumable-institution-aura-eda.md)
**Sibling consumable:** [governance/data-dictionaries/consumable-ipeds-finance-profile.md](consumable-ipeds-finance-profile.md)
**Base data dictionaries:** [governance/data-dictionaries/base-eada.md](base-eada.md), [governance/data-dictionaries/base-ipeds-finance.md](base-ipeds-finance.md)
**Domain Context:** [governance/domain-context.md](../domain-context.md) §§ "EADA Athletics Disclosure", "IPEDS Finance Survey", "Aura Score brand-gravity composite"
**Source:** `base.ipeds_finance` FULL OUTER JOIN `base.eada` on UNITID
**Grain:** one row per institution (`unitid`) per snapshot
**Observed rows:** 3,223 (snapshot `5887248523326294782`, FY2023 Finance × 2022 EADA)
**Documented by:** @doc-generator
**Date:** 2026-04-30

---

## What This Table Contains

The Gold/Consumable layer of the EADA + IPEDS Finance fusion — the institution-level **brand-gravity** profile served to downstream consumers (the FutureProof career-outcomes pentagon, future MCP tools, future cross-institution comparison specs). Every row is one U.S. postsecondary institution at one snapshot in time, built from a FULL OUTER JOIN of two upstream Base tables on UNITID. The table:

1. **Coalesces 2 identity columns** (`unitid`, `institution_name`) from the FULL OUTER, so finance-only and athletics-only institutions both get a populated identity.
2. **Carries forward 7 Base signal columns verbatim** — 4 IPEDS Finance signals (`endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `marketing_ratio`) and 3 EADA signals (`athletic_spend_per_fte`, `athletic_revenue_per_fte`, `athletic_subsidy_ratio`).
3. **Surfaces 1 methodological-provenance column** — `athletic_fte_source` (`ipeds_finance` / `eada_fte_headcount` / NULL) so downstream consumers can stratify on FTE-denominator consistency. Introduced via the §5 Option-C amendment.
4. **Synthesizes 4 aura-score columns** — `aura_score` (integer 1–10), `aura_score_continuous` (pre-rounding), `aura_score_version` (`"v1"`), `aura_score_basis` (5-value enum recording which inputs were used).
5. **Adds 3 coverage-classification columns** — `has_ipeds_finance`, `has_eada`, `coverage_tier` (`both` / `finance_only` / `athletics_only`).
6. **Adds 1 provenance column** — `promoted_at`.
7. **Computes 1 new surrogate key** — `record_id` under the `aur-` prefix.

This is the **first cross-source fusion** in the FutureProof pipeline that joins two distinct upstream Base tables on UNITID and produces a derived composite signal (`aura_score`). The composite was EDA-finalized on 2026-04-30 after a v0-draft formula failed 11/14 anchor schools; the v1 formula passes 13/13 anchors at the §6-required `aura_score ≥ 8` threshold.

### What "Aura Score" Means (Plain English)

**Aura is a NEUTRAL brand-gravity signal — higher means more brand presence, NOT "better" or "worse."** The score composites three direct (non-inverted) inputs:

- **`marketing_ratio`** — institutional support spending divided by instruction spending. High = the institution spends more on administration, fundraising, and marketing relative to teaching.
- **`endowment_per_fte`** — endowment market value per full-time-equivalent student. High = the institution has a big financial backstop per student.
- **`athletic_spend_per_fte`** — athletic-program expense per FTE student. High = the institution invests heavily in intercollegiate athletics.

A **high aura** can mean very different things depending on which signals drove it:
- High aura with high endowment + high athletic = a public flagship or Ivy (Harvard, Stanford, Princeton, Alabama, Ohio State).
- High aura with high marketing + NULL endowment + NULL athletic = a for-profit (Phoenix, Grand Canyon).
- High aura with all three signals strong = a premier R1 (Stanford, Duke).

The score does not encode whether brand presence translates to *good outcomes for students*. That interpretation emerges from the **pentagon shape** when aura is read alongside ERN (earnings) and ROI (return on investment) — high-aura/low-ERN tells a different story than high-aura/high-ERN. The `aura_score_basis` column flags which inputs computed the score so downstream consumers can avoid apples-to-oranges comparisons across strata.

### The v1 Formula in One Sentence

For each institution: take the rank-percentile of each available input across all reporting institutions, drop NULL inputs (no imputation), compute `0.65 × MAX + 0.35 × MEAN` over the available rank-percentiles, rescale via the EDA-pinned P5/P95 bounds (0.1413 / 0.9400) to [1, 10], and ROUND. Stamp `aura_score_basis` to record which inputs were used and `aura_score_version = "v1"` to record which formula version produced the score.

### The 5-Value `aura_score_basis` Enum (v1 Expansion)

The original spec proposed a 3-value enum (`three_term`, `two_term_finance_only`, NULL). EDA discovered two structural cases the 3-value enum missed because **677 finance reporters have NULL `endowment_per_fte`** — for-profits like Phoenix and Grand Canyon, plus IPEDS shell offices. The v1 expansion stamps each row with a basis that accurately documents which inputs were used:

| Basis | Population | Inputs Used |
|-------|-----------:|-------------|
| `three_term` | 1,417 | marketing + endowment + athletic |
| `two_term_finance_only` | 579 | marketing + endowment (no EADA) |
| `two_term_no_endowment` | 75 | marketing + athletic (NULL endowment — for-profits-with-athletics) |
| `one_term_marketing_only` | 573 | marketing only (NULL endowment AND NULL athletic — for-profits without athletics, IPEDS shell offices) |
| NULL (no aura) | 579 | none — 548 athletics_only + 31 finance reporters with all-NULL inputs |

The v1 invariant is `aura_score IS NULL iff aura_score_basis IS NULL` (CON-AUR-034 P0). The spec-as-written `aura_score IS NULL exactly when has_ipeds_finance = FALSE` shorthand was rewritten because it does not cover the 31 zero-instruction-expense edge cases that have `has_ipeds_finance=TRUE` but no usable signal.

### Coverage Tier (How the FULL OUTER Played Out)

| Tier | Rows | % | What It Means |
|------|-----:|---:|----------------|
| `both` | 1,492 | 46.3% | Reports both IPEDS Finance AND EADA. Earns `three_term` aura when endowment is present. |
| `finance_only` | 1,183 | 36.7% | Reports IPEDS Finance only — non-athletic 4-years (most LACs/SLACs, MIT, Caltech, all for-profits without athletics). Earns aura on `two_term_finance_only`, `two_term_no_endowment`, or `one_term_marketing_only` basis. |
| `athletics_only` | 548 | 17.0% | Reports EADA only — institutions that report athletics but not IPEDS Finance (typically excluded from Finance by the HD `ICLEVEL=1 AND HLOFFER>=5` filter). Aura is NULL for these rows. |

**CDE density:** 13 of 19 columns are CDE candidates (68%) — the join key, every analytical input signal, the aura composite (all 4 columns), the FTE-source provenance, and the coverage tier.

**PII:** None. EADA and IPEDS Finance are institution-level reporting by design.

---

## Field Inventory

### Grain & Identifiers

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `record_id` | `compute_grain_id(row, ['unitid'], prefix='aur')` | string | Yes | No | (Brightsmith convention) | Deterministic surrogate key for this consumable row, format `aur-<16 hex>`. Pure function of `unitid` with constant prefix `aur` — re-running the promote yields the same hash for the same UNITID. The `aur` prefix is distinct from upstream Base prefixes (`ipf` for `base.ipeds_finance`, `ead` for `base.eada`) and from the sibling consumable prefix (`ifp` for `consumable.ipeds_finance_profile`) — no cross-zone hash collisions. The `aur` mnemonic is "**aur**a." **Observed:** 3,223 / 3,223 non-null and unique. |
| `unitid` | `COALESCE(f.unitid, e.unitid)` from FULL OUTER | long | Yes | **Yes** | [BT-001](../business-glossary.json) | The 6-digit IPEDS UNITID. Coalesced from `base.ipeds_finance.unitid` and `base.eada.unitid` (both sides P0 non-null). Natural key — the universal join key for downstream consumers. **Observed:** 3,223 distinct values, 0 nulls. |
| `institution_name` | `COALESCE(f.institution_name, e.institution_name)` | string | Yes | No | [BT-002](../business-glossary.json) | The official name of the institution, coalesced from whichever Base side reported it. Display-only — do not use for joins (case, punctuation, and `-Main Campus` suffix conventions vary across IPEDS sources). **Observed:** 100% non-null. |

### Finance Signals (Base Passthroughs from `base.ipeds_finance`)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `endowment_per_fte` | `base.ipeds_finance.endowment_per_fte` (passthrough) | double | No | **Yes** | (proposed) [BT-IPF-PER-FTE](../business-glossary.json) | Per-student endowment value. The "wealth backing" signal — high values mean a larger financial cushion per FTE student. Promoted verbatim from `base.ipeds_finance`. **Observed:** 1,998 / 3,223 (62.0%) non-null; structural NULL on for-profits (F3) and 548 athletics-only rows. **Aura input** — feeds `rp_endowment` in the v1 composite. |
| `institutional_support_per_fte` | `base.ipeds_finance.institutional_support_per_fte` (passthrough) | double | No | **Yes** | (proposed) [BT-IPF-PER-FTE](../business-glossary.json) | Per-student spending on administration, fundraising, executive direction, legal services, and similar institutional-support functions. Promoted verbatim. **Not a direct aura input** — the marketing-side aura input is `marketing_ratio` (which is derived from this column over `instruction_per_fte`); CON-AUR-007 cross-checks that the arithmetic identity holds at the row level. |
| `instruction_per_fte` | `base.ipeds_finance.instruction_per_fte` (passthrough) | double | No | **Yes** | (proposed) [BT-IPF-PER-FTE](../business-glossary.json) | Per-student spending on instructional divisions — the "what students get" cost-of-instruction signal. Promoted verbatim. **Not a direct aura input** — see above. |
| `marketing_ratio` | `base.ipeds_finance.marketing_ratio` (passthrough) | double | No | **Yes** | [BT-IPF-MARKETING-RATIO](../business-glossary.json) | The dimensionless ratio of institutional support expenses to instruction expenses. Higher = relatively more spending on administration, fundraising, marketing, and recruiting compared to teaching. Promoted verbatim. **Observed:** P5=0.183 / P50=0.545 / P95=2.345; long pathological tail dominated by IPEDS reporting artifacts (system offices and shells with near-zero instruction). **Aura input** — feeds `rp_marketing` and is the only signal that produces non-NULL aura on the `one_term_marketing_only` basis. CON-AUR-007 cross-checks `institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 wherever all three are non-null (live observation: differences within 1e-6 across 2,620 rows). |

### Athletics Signals (Base Passthroughs from `base.eada`)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `athletic_spend_per_fte` | `base.eada.athletic_spend_per_fte` (passthrough) | double | No | **Yes** | (proposed) BT-AUR-ATHLETIC-SPEND-PER-FTE | Per-student athletic-program expense. Sum of all sport-level athletic expenses (men's + women's + coed) divided by the FTE denominator declared in `athletic_fte_source` (next column). Promoted verbatim. **Observed:** 2,040 / 3,223 (63.3%) non-null; P5=$148 / P50=$1,579 / P95=$7,177 across all 2,040 EADA reporters. The two `athletic_fte_source` strata differ materially — `ipeds_finance` median $1,990 vs `eada_fte_headcount` median $673 — but the `eada_fte_headcount` stratum never enters aura computation (those rows are all `coverage_tier='athletics_only'` with NULL aura). **Aura input** — feeds `rp_athletic`. |
| `athletic_revenue_per_fte` | `base.eada.athletic_revenue_per_fte` (passthrough) | double | No | **Yes** | (proposed) BT-AUR-ATHLETIC-REVENUE-PER-FTE | Per-student athletic-program revenue. Promoted verbatim. **Context column only — NOT an aura input.** |
| `athletic_subsidy_ratio` | `base.eada.athletic_subsidy_ratio` (passthrough) | double | No | **Yes** | [BT-EAD-ATHLETIC-SUBSIDY-RATIO](../business-glossary.json) | The fraction of athletic expenses not covered by athletic revenue: `(expenses − revenue) / expenses`. Positive = institution subsidizes athletics; near-zero = self-sustaining; negative = profitable. **Context column only — explicitly EXCLUDED from the aura composite per spec §2 Decision 11** (the ratio encodes a normative judgment that overlaps with ROI / ERN and would remove the analytical tension between aura and the pentagon). **Observed:** 1,284 / 2,040 rows are exactly 0 — silver-zone clipping artifact; at the EADA grand-total grain, EADA convention requires reported revenues to at least equal expenses, so the column is heavily right-clipped. The "athletics loses money" insight requires the unbundled `direct_institutional_support` field, which is out of scope for this Bronze ingest. |

### FTE-Source Provenance (Option-C Amendment, 2026-04-30)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `athletic_fte_source` | `base.eada.fte_source` (passthrough, renamed) | string | No | **Yes** | (proposed) BT-AUR-FTE-SOURCE | **Methodological-provenance enum** recording which FTE denominator was used for the three EADA per-FTE / ratio columns. **3 values + NULL:** `ipeds_finance` (1,492 rows, all `coverage_tier='both'`) — IPEDS-Finance annualized FTE; preferred. `eada_fte_headcount` (548 rows, all `coverage_tier='athletics_only'`) — EADA's own 12-month student headcount. `none`/NULL (1,183 rows, all `coverage_tier='finance_only'`) — no EADA reporting, so no athletic per-FTE values. The two FTE definitions are NOT identical (EADA's headcount is unduplicated, IPEDS Finance's FTE is annualized); the provenance column lets downstream consumers stratify or filter on methodology consistency. **Observed:** the 2 × 3 (`aura_score_basis × athletic_fte_source`) interaction grid is structurally degenerate — every aura-computed row uses `ipeds_finance` (548 `eada_fte_headcount` rows are all NULL aura), so FTE-methodology mix never affects the aura distribution. Surfaced for downstream stratification only. |

### Aura Score & Provenance (Synthesized in This Zone)

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `aura_score` | **Derivation:** `ROUND(aura_score_continuous)`. See §"v1 Aura Formula" below. | int | No | **Yes** | (proposed) BT-AUR-AURA-SCORE | Integer 1–10 brand-gravity score. NULL when no usable signal (athletics-only rows + 31 zero-instruction edge cases). **Higher = stronger brand presence (endowment + marketing + athletic), not "better" or "worse"** — the value judgment emerges only when aura is read alongside ERN and ROI. **Observed:** 2,644 / 3,223 non-null; integer 1..10 all 10 buckets populated; median = 7; band distribution [1,3]=17.4% / [4,6]=25.7% / [7,10]=56.9%. **Validated:** 14 / 14 anchor schools produce their EDA-validated v1 scores exactly (CON-AUR-032 PASS) — Harvard 9, Princeton 10, Stanford 10, MIT 9, Yale 9, Duke 9, Cornell 9, Northwestern 9, Alabama 9, Phoenix 10, Ohio State 8, Michigan 9, Grand Canyon 8, Liberty 5 (the moderate-on-all-three control). |
| `aura_score_continuous` | **Derivation:** `1.0 + 9.0 * clip((raw_score − 0.1413) / (0.9400 − 0.1413), 0, 1)` where `raw_score = 0.65 * MAX(available_rp_*) + 0.35 * MEAN(available_rp_*)`. | double | No | **Yes** | (Brightsmith convention) | Pre-rounding continuous value in [1.0, 10.0]. Retained for downstream auditability and for the CON-AUR-013 round-correctness invariant (`aura_score == ROUND(aura_score_continuous)` for every row where both non-null). NULL when `aura_score` is NULL. |
| `aura_score_version` | constant `"v1"` | string | Yes | No | (Brightsmith convention) | Provenance stamp identifying the formula version. Always `"v1"` for rows produced by this snapshot (CON-AUR-012 P0). v0-draft was rejected during EDA after failing 11/14 anchor schools (composite-collapse at the tails because three near-equal weights cap any one-signal-extreme school at ~7). The version stamp is for the *formula*, not the score-existence — every row carries `"v1"` regardless of whether the score itself is NULL. |
| `aura_score_basis` | **Derivation:** Per-row basis assignment based on which of `marketing_ratio`, `endowment_per_fte`, `athletic_spend_per_fte` are non-null. See §"The 5-Value Enum" above. | string | No | **Yes** | (proposed) BT-AUR-AURA-SCORE-BASIS | The 5-value enum (4 non-NULL + NULL) recording which input set computed the aura score for this row. **NULL ⇔ aura_score IS NULL** (CON-AUR-034 P0 invariant). The enum was expanded from 3 → 5 values during EDA after discovering 677 finance reporters with NULL endowment. **Observed:** `three_term` 1,417 / `two_term_finance_only` 579 / `two_term_no_endowment` 75 / `one_term_marketing_only` 573 / NULL 579 = 3,223 total. **Why this column matters for downstream consumers:** comparing a `three_term` Stanford to a `one_term_marketing_only` Phoenix is **not** apples-to-apples in the same way that comparing two `three_term` flagships is — the basis stamp lets downstream consumers stratify or hedge accordingly. |

### Coverage Flags (Synthesized in This Zone)

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `has_ipeds_finance` | `f.unitid IS NOT NULL` after FULL OUTER | boolean | Yes | No | (proposed) BT-AUR-HAS-IPEDS-FINANCE | TRUE when the institution reports IPEDS Finance. **Observed:** TRUE on 2,675 rows. |
| `has_eada` | `e.unitid IS NOT NULL` after FULL OUTER | boolean | Yes | No | (proposed) BT-AUR-HAS-EADA | TRUE when the institution reports EADA. **Observed:** TRUE on 2,040 rows. |
| `coverage_tier` | **Derivation:** `CASE WHEN has_ipeds_finance AND has_eada THEN 'both' WHEN has_ipeds_finance THEN 'finance_only' WHEN has_eada THEN 'athletics_only' END`. | string | Yes | **Yes** | (proposed) BT-AUR-COVERAGE-TIER | 3-value enum classifying which sources contributed to this row. **Closed enum:** `{both, finance_only, athletics_only}` — CON-AUR-005 (P0) enforces the domain. **CON-AUR-006 (P0)** enforces that every row has at least one source TRUE (the CASE is exhaustive). **Observed:** `both` 1,492 (46.3%) / `finance_only` 1,183 (36.7%) / `athletics_only` 548 (17.0%). |

### Promotion Provenance

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `promoted_at` | `datetime.utcnow()` at promote time | timestamp | Yes | No | (Brightsmith convention) | UTC wall-clock recording when this consumable row was promoted. Identical across all rows in a single consumable promote run. Distinct from upstream Base `ingested_at` stamps; downstream consumers needing per-zone freshness should reference the fully-qualified table name. |

---

## v1 Aura Formula (Detail)

The exact computation, EDA-finalized 2026-04-30. Full evidence chain in `governance/eda/consumable-institution-aura-eda.md`.

### Step 1 — Population-Level Rank-Percentile Transform

For each input signal `s ∈ {marketing_ratio, endowment_per_fte, athletic_spend_per_fte}`, compute:

```sql
rp_s = PERCENT_RANK() OVER (ORDER BY s) -- where s IS NOT NULL
```

Rows with NULL `s` get NULL `rp_s` (no imputation). This matches the Brightsmith HMN convention.

### Step 2 — Per-Row Basis Assignment (5-value enum)

```python
if rp_marketing is None:
    basis = None  # athletics_only OR zero-instruction edge case
elif rp_endowment is not None and rp_athletic is not None:
    basis = "three_term"
elif rp_endowment is not None:
    basis = "two_term_finance_only"
elif rp_athletic is not None:
    basis = "two_term_no_endowment"
else:
    basis = "one_term_marketing_only"
```

### Step 3 — MAX + MEAN Composite

For rows with non-NULL basis:

```python
available = [r for r in (rp_marketing, rp_endowment, rp_athletic) if r is not None]
raw_score = 0.65 * max(available) + 0.35 * (sum(available) / len(available))
```

**Why this composite (and not the v0-draft weighted-mean):** EDA tested four candidates against 14 anchor schools. The v0-draft `0.40 · rp_mkt + 0.40 · rp_endow + 0.20 · rp_ath` formula passed only 3 / 14 because three near-equal weights cap any school extreme on only one signal at ~`0.40 + 0.40·median + 0.20·median ≈ 0.70` raw. The MAX + MEAN composite ensures a school with one extreme signal can still earn a high score (the MAX term carries) while preserving the aggregate signal (the MEAN term).

### Step 4 — P5/P95 Percentile Rescale to [1, 10]

```python
t = (raw_score - 0.1413) / (0.9400 - 0.1413)
t_clipped = max(0.0, min(1.0, t))
aura_score_continuous = 1.0 + 9.0 * t_clipped   # in [1.0, 10.0]
aura_score = round(aura_score_continuous)        # in [1, 10]
```

The P5 (0.1413) and P95 (0.9400) bounds are population-level percentiles of `raw_score` across the production population, EDA-pinned 2026-04-30 and recomputed on each annual refresh. Min/max rescale was rejected because it produced a degenerate band distribution (53% of rows in [4,6]).

### Step 5 — Stamp Provenance

```python
aura_score_version = "v1"
```

### Worked Examples

| Anchor | Class | rp_mkt | rp_endow | rp_ath | basis | raw_score | aura_score |
|--------|-------|-------:|---------:|-------:|-------|----------:|-----------:|
| Harvard | endowment | 0.65 | 0.99 | 0.42 | three_term | `0.65·0.99 + 0.35·0.687` = 0.884 | **9** |
| Princeton | endowment | 0.47 | 1.00 | 0.89 | three_term | `0.65·1.00 + 0.35·0.787` = 0.925 | **10** |
| Stanford | endowment | 0.17 | 1.00 | 0.97 | three_term | `0.65·1.00 + 0.35·0.713` = 0.900 | **10** |
| Phoenix | marketing-only | 0.98 | NULL | NULL | one_term_marketing_only | `0.65·0.98 + 0.35·0.98` = 0.980 | **10** |
| Liberty | moderate (control) | 0.55 | 0.57 | 0.29 | three_term | `0.65·0.57 + 0.35·0.470` = 0.535 | **5** |

---

## Data Quality Rules

The 19 Consumable DQ rules are defined in [governance/dq-rules/consumable-institution-aura.json](../dq-rules/consumable-institution-aura.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|----------------|
| CON-AUR-001 | P0 | (row count) | FULL OUTER conservation: row count ∈ [max(N_finance, N_eada), N_finance + N_eada] = [2,675, 4,715]. Live: 3,223. |
| CON-AUR-002 | P0 | `unitid` | Non-null in every row. |
| CON-AUR-003 | P0 | `unitid` | Uniqueness (dedup grain). |
| CON-AUR-004 | P0 | `record_id` | Non-null + unique. |
| CON-AUR-005 | P0 | `coverage_tier` | Domain ∈ {`both`, `finance_only`, `athletics_only`}. |
| CON-AUR-006 | P0 | `has_ipeds_finance`, `has_eada` | Every row has ≥ 1 source TRUE. |
| CON-AUR-007 | P0 | `institutional_support_per_fte`, `instruction_per_fte`, `marketing_ratio` | Arithmetic invariant: `support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001. |
| CON-AUR-010 | P0 | `aura_score` | Range [1, 10] where non-null. |
| CON-AUR-011 | P0 | `aura_score`, `aura_score_basis` | v1 invariant: `aura_score IS NULL ⇔ aura_score_basis IS NULL` (rewritten from spec-as-written `iff has_ipeds_finance = FALSE`). |
| CON-AUR-012 | P0 | `aura_score_version` | Stamp = `"v1"` (updated from spec-as-written `"v0-draft"` per EDA promotion). |
| CON-AUR-013 | P0 | `aura_score`, `aura_score_continuous` | `aura_score = ROUND(aura_score_continuous)`. |
| CON-AUR-014 | P0 | `aura_score_continuous` | Range [1.0, 10.0] where non-null. |
| CON-AUR-020 | P1 | (cross-source coverage) | Aura UNITIDs without a `consumable.career_outcomes` counterpart ≤ 1,611 (drift cap). Live: 928 — PASS. |
| CON-AUR-021 | P1 | (cross-source coverage) | ≥ 90% of distinct UNITIDs in `consumable.career_outcomes` find a matching row here. Live: 89.68% — **FAIL by 0.32 pp**. P1 warning; does NOT block the P0 gate. |
| CON-AUR-030 | P1 | `aura_score`, `aura_score_basis` | Stratified bucket coverage: per-stratum ≥ 4 of 10 buckets populated; overall ≥ 6 of 10. Stratification by `aura_score_basis` (4 strata), NOT by `athletic_fte_source` (which is structurally degenerate per EDA Item 7). Live: overall 10/10, per-stratum ≥ 5/10 — PASS by margin. |
| CON-AUR-031 | P1 | `aura_score` | Median ∈ [4, 7]. Live: 7 — PASS at upper edge. |
| CON-AUR-032 | P1 | `aura_score` | 14 anchor schools match v1 EDA-validated scores exactly. Live: 14/14 — PASS. |
| CON-AUR-033 | P0 | `aura_score_basis` | Domain ∈ {`three_term`, `two_term_finance_only`, `two_term_no_endowment`, `one_term_marketing_only`} where non-null. NEW v1 rule (not in spec-as-written). |
| CON-AUR-034 | P0 | `aura_score`, `aura_score_basis` | Explicit iff: `aura_score IS NULL ⇔ aura_score_basis IS NULL`. NEW v1 rule (the basis-tagged form of CON-AUR-011). |

**Gate decision:** P0 gate PASS (14/14). P1 warning on CON-AUR-021 (0.32 pp short of the 90% spec-pinned threshold) — does not block; @governance-reviewer to acknowledge. Full scorecard: `governance/dq-scorecards/consumable-institution-aura-20260501T235038Z.md`.

---

## Caveats for Consumers

1. **Aura is NEUTRAL — higher is NOT "better."** Higher aura means more brand presence (endowment + marketing + athletic spend). Whether brand gravity translates to good outcomes for students is a separate question — that interpretation emerges from the pentagon shape when aura is read alongside ERN and ROI. A high-aura/low-ERN school tells a different story than a high-aura/high-ERN school.

2. **`aura_score_basis` is load-bearing for cross-stratum comparison.** Comparing a `three_term` Stanford to a `one_term_marketing_only` Phoenix is **not** apples-to-apples in the same way as comparing two `three_term` flagships. Downstream consumers should read the basis when surfacing aura comparisons.

3. **`aura_score = NULL` for 579 rows.** 548 are `coverage_tier='athletics_only'` (institutions that report EADA but not IPEDS Finance — typically excluded from Finance by the HD `ICLEVEL=1 AND HLOFFER>=5` filter). 31 are finance reporters with all-NULL signals (zero-instruction-expense edge cases — typically system administrative offices, IPEDS shells). The v1 invariant `aura_score IS NULL iff aura_score_basis IS NULL` (CON-AUR-034 P0) covers both populations; the spec-as-written `iff has_ipeds_finance = FALSE` shorthand was rewritten because it does not cover the 31 edge cases.

4. **`athletic_subsidy_ratio` is NOT an aura input.** It is a **context column** carried for downstream consumers that want a "subsidy intensity" signal. Reading it into any aura computation is incorrect (per spec §2 Decision 11; verified by code inspection of all four candidate formulas during EDA Item 6).

5. **`athletic_subsidy_ratio` is heavily right-clipped at 0.** 1,284 / 2,040 EADA rows are exactly 0 — silver-zone clipping artifact. At the EADA grand-total grain, EADA convention requires reported revenues to at least equal expenses; the canonical "athletics loses money" insight requires the unbundled `direct_institutional_support` field which is out of scope for this Bronze ingest.

6. **`marketing_ratio` has a long pathological tail.** 11 rows have `marketing_ratio > 10`, dominated by IPEDS reporting artifacts (system offices like Sistema Universitario Ana G. Mendez at 5,265 — institutional support / near-zero instruction). These rows saturate `rp_marketing ≈ 1.0` and pollute the high-aura tail. Recommend post-base filter or P99 cap as a silver-zone follow-up (out of scope for v1).

7. **`athletic_fte_source` matters for cross-stratum comparison of athletics signals.** The two strata (`ipeds_finance` median $1,990 vs `eada_fte_headcount` median $673) differ ~3× at the median. **However**, the `eada_fte_headcount` stratum never enters aura computation (those rows are all `coverage_tier='athletics_only'` with NULL aura), so the methodology mix never affects the aura distribution. CON-AUR-030 stratifies by `aura_score_basis` accordingly, NOT by `athletic_fte_source`.

8. **The four enum-valued columns (`coverage_tier`, `aura_score_version`, `aura_score_basis`, `athletic_fte_source`) are stored as strings.** Iceberg does not have a first-class enum type; the closed domains are enforced by DQ rules CON-AUR-005 / 012 / 033 (P0) and the documented enum on `athletic_fte_source`.

9. **No imputation, no substitution.** Per spec §2 Decision #8 and the standing user constraint, NULLs propagate honestly from Base through this consumable. The `aura_score_basis` column is the *summary* of which inputs were missing, not a substitute for them. NULL aura means "no usable signal," not "low aura."

10. **`record_id` prefix is `aur-`.** Distinct from upstream Base prefixes (`ipf` for `base.ipeds_finance`, `ead` for `base.eada`) and from the sibling consumable prefix (`ifp` for `consumable.ipeds_finance_profile`). Cross-zone hash collisions impossible by construction.

11. **CON-AUR-021 is currently 0.32 pp short of the 90% threshold (live 89.68%).** The spec pinned 90% per a pre-EDA estimate; the live measurement reveals 264 College Scorecard institutions with program-completion rows do not appear in `consumable.institution_aura` (i.e., absent from BOTH `base.ipeds_finance` and `base.eada`). P1 warning; @governance-reviewer to either widen threshold to 0.89 with rationale or enumerate the 264 missing UNITIDs as documented drift in EDA. Does NOT block the P0 gate.

12. **Field IDs 1–19 are stable.** Future schema evolution (e.g., adding a v2 score column, surfacing additional EADA fields like `direct_institutional_support`, or adding sport-specific aura facets) must allocate IDs ≥ 20 and never rebind 1–19. Standard Iceberg-evolution discipline.

13. **v1 P5/P95 bounds (0.1413 / 0.9400) are pinned constants in the transformer.** They are recomputed on each annual refresh; if the bounds drift materially (e.g., P95 bumps above 1.0), the change should trigger a **v2** score with a new `aura_score_version` stamp rather than an in-place rebound. The version stamp is what protects downstream consumers from silent score-meaning drift.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-30 | Initial data dictionary for Consumable cross-source-fusion table `consumable.institution_aura` per spec full-pipeline-eada.md §6 (post-EDA v1 amendment + §5 Option-C amendment). 19 fields documented (3 identity + 4 finance signals + 3 athletics signals + 1 FTE-source provenance + 4 aura columns + 3 coverage flags + 1 provenance), 13 flagged CDE, 0 flagged PII. Field types and nullability verified against landed Iceberg metadata (snapshot `5887248523326294782`, 3,223 rows). v1 aura formula and 5-value `aura_score_basis` enum documented per the EDA evidence chain in `governance/eda/consumable-institution-aura-eda.md`. | @doc-generator |
