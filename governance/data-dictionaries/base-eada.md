# Data Dictionary: base.eada

**Table:** `base.eada`
**Zone:** Silver (Base)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §5 (Option-C amendment, 2026-04-30)
**Transformer:** [src/silver/eada_base.py](../../src/silver/eada_base.py)
**Conceptual model:** [governance/models/base-eada-conceptual.md](../models/base-eada-conceptual.md)
**Logical model:** [governance/models/base-eada-logical.md](../models/base-eada-logical.md)
**Physical model:** [governance/models/base-eada-physical.md](../models/base-eada-physical.md)
**DQ Rules:** [governance/dq-rules/base-eada.json](../dq-rules/base-eada.json) (13 rules: 11 P0 + 2 P1)
**DQ Scorecard:** [governance/dq-scorecards/base-eada-20260501T210828Z.md](../dq-scorecards/base-eada-20260501T210828Z.md) (13/13 PASS)
**Chaos:** [governance/chaos-reports/base-eada-chaos.md](../chaos-reports/base-eada-chaos.md) (7/7 caught)
**Entity resolution:** [governance/entity-resolution/base-eada-er-assessment.md](../entity-resolution/base-eada-er-assessment.md) (N/A)
**PII scan:** [governance/pii-scans/base-eada-pii-scan.md](../pii-scans/base-eada-pii-scan.md) (NONE)
**Temporal model:** [governance/temporal-models/base-eada-temporal-assessment.md](../temporal-models/base-eada-temporal-assessment.md) (N/A — single-cycle snapshot)
**CDE/PII tagging:** [governance/cde-tagging/raw-eada.md](../cde-tagging/raw-eada.md) (Bronze; Base flags follow the upstream-feeder + analytical lens documented in this dictionary)
**Lineage:** `governance/lineage/full-pipeline-eada-silver-*.json` (silver run)
**Domain Context:** [governance/domain-context.md](../domain-context.md) § EADA Athletics Disclosure
**Bronze data dictionary:** [governance/data-dictionaries/raw-eada.md](raw-eada.md)
**Sibling cross-source dictionary:** [governance/data-dictionaries/base-ipeds-finance.md](base-ipeds-finance.md)
**Source:** `bronze.eada` (1:1 promote with derivations) + `base.ipeds_finance` (LEFT JOIN on UNITID for FTE)
**Grain:** one row per institution (`unitid`) per academic reporting cycle
**Observed rows:** 2,040 (academic year 2022–23 cycle, snapshot `973879610917339278`)
**Documented by:** @doc-generator
**Date:** 2026-04-30

---

## What This Table Contains

The Silver/Base layer of the EADA Athletics Disclosure pipeline. Every row is one U.S. postsecondary institution that filed an EADA report, in one academic reporting cycle. The table promotes 1:1 from Bronze (no row-grain change) and adds **eight new columns**: one cross-source FTE denominator, three FTE-source provenance columns, three per-FTE derivations, and one cross-field subsidy ratio. The seven Bronze passthroughs (identity + three monetary fields + EADA's `EFTotalCount`) carry through verbatim.

Per spec §5 (Option-C amendment 2026-04-30), the FTE denominator is a hybrid:

```
total_fte_enrollment = COALESCE(
    base.ipeds_finance.total_fte_enrollment,    -- preferred (annualized)
    bronze.eada.eada_fte_headcount               -- fallback (12-month headcount)
)

fte_source = CASE
    WHEN base.ipeds_finance.total_fte_enrollment IS NOT NULL THEN 'ipeds_finance'
    WHEN bronze.eada.eada_fte_headcount          IS NOT NULL THEN 'eada_fte_headcount'
    ELSE                                                          'none'
END
```

The original spec used IPEDS-Finance FTE alone, which covered only **74.5%** of EADA institutions. The Option-C amendment raises hybrid coverage to **~99.99%** by falling back to EADA's in-file `EFTotalCount`. The two FTE definitions are **not** identical (annualized vs. 12-month headcount) — the `fte_source` column makes the methodological mix explicit at the row level. Knight Commission's per-FTE athletic-spend benchmarks already use `EFTotalCount`, which strengthens the fallback choice.

Per-FTE math (per spec §5):

```
metric_per_fte = metric / total_fte_enrollment
                  → NULL when either operand is NULL or total_fte_enrollment ≤ 0
```

Subsidy ratio:

```
athletic_subsidy_ratio = (total_athletic_expenses − total_athletic_revenue)
                       / NULLIF(total_athletic_expenses, 0)
```

**Why these derivations live in Base, not Consumable:** The per-FTE rates are the *canonical institution-scale athletic-finance signal*. Carrying the raw dollars without per-FTE normalization would force every downstream consumer (the `consumable.institution_aura` fusion, future receipts/comparison specs) to repeat the same division — risking formula drift and re-introducing the source-selection bug at every read site. Computing per-FTE once in Base, with the chosen denominator and its provenance present in the same row, is the single source of truth. The subsidy ratio lives in Base for the same reason — the consumable carries it as a context column, not an aura input (per spec §2 Decision 11).

**FTE-source mix (2022–23):** ipeds_finance ~74.5% / eada_fte_headcount ~25.5% / none < 1% (BSE-EAD-011 P1, ±5pp tolerance).

**CDE density:** 7 of 18 columns are CDE-flagged (39%) — `unitid` (the join key), `total_fte_enrollment` (the universal denominator), `fte_source` (the methodological-mix governance signal), and the four derivations (`athletic_spend_per_fte`, `athletic_revenue_per_fte`, `recruiting_per_fte`, `athletic_subsidy_ratio`). The three monetary inputs are NOT analytical-CDE at Base — they become CDE at the consumable layer once they (transitively) reach `aura_score`. The CDE pattern follows `base.ipeds_finance` exactly: derivations carry the analytical CDE flag at Base; raw inputs carry it at Consumable.

**PII:** None. EADA is institution-level disclosure by design. Confirmed by `governance/pii-scans/base-eada-pii-scan.md`.

**Self-auditable arithmetic invariants:** Because each Base row carries both the Bronze numerator and the COALESCE'd denominator alongside the per-FTE derivation, BSE-EAD-008 (`spend_per_fte × fte ≈ expenses` within $1) can be checked without a cross-row join. Same self-audit pattern as `base.ipeds_finance` BSE-IPF-008/009/010.

---

## Field Inventory

### Grain & Identifiers

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `record_id` | `compute_grain_id(row, ['unitid'], prefix='ead')` | string | Yes | No | (Brightsmith convention) | Deterministic surrogate key for this Base row, format `ead-<16 hex>`. Pure function of `unitid` with constant prefix `ead` — re-running the promote yields the same hash for the same UNITID. The Consumable layer uses prefix `aur` (distinct namespace) so cross-zone hash collisions are impossible. **Observed:** 2,040 / 2,040 non-null and unique. |
| `unitid` | `bronze.eada.unitid` (passthrough) | long | Yes | **Yes** | [BT-001](../business-glossary.json) | The 6-digit IPEDS UNITID, promoted verbatim from Bronze. Natural key and dedup grain. The universal join key linking EADA to every other institution-keyed table — the LEFT JOIN to `base.ipeds_finance` for FTE here, the FULL OUTER JOIN at `consumable.institution_aura` downstream. **Observed:** 2,040 distinct values, 0 nulls, ~74.5% overlap with `base.ipeds_finance`. |
| `institution_name` | `bronze.eada.institution_name` (passthrough) | string | Yes | No | [BT-002](../business-glossary.json) | The name of the institution as filed with EADA (e.g., `Ohio State University-Main Campus`), promoted verbatim from Bronze. Display-only — do not use for joins (case, punctuation, and `-Main Campus` suffix conventions vary across IPEDS sources). **Observed:** 100% non-null. |
| `reporting_year` | `bronze.eada.reporting_year` (passthrough) | int | Yes | No | (proposed) BT-120 — EADA Reporting Cycle | The academic-year-start of the EADA cycle this row covers (current load: `2022` for the 2022–23 cycle). Constant across every row in a single load (single-vintage invariant inherited from Bronze RAW-EAD-010). EADA does not publish an in-row year column; the value is pinned by the ingestor at Bronze. |

### Monetary Inputs (Bronze Passthroughs)

The three Bronze monetary fields, carried verbatim. They are the *numerator inputs* for the per-FTE derivations and the subsidy-ratio derivation. NULLs propagate honestly — no imputation, no substitution. **Observed (2022–23):** all three are 100% non-null. CDE-flag posture mirrors `base.ipeds_finance`: not analytical-CDE at Base; the analytical CDE flag lives on the per-FTE derivation. (At Bronze, these columns ARE CDE under the upstream-feeder lens — see `governance/cde-tagging/raw-eada.md`. The Base posture re-evaluates against Base-zone consumers.)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `total_athletic_expenses` | `bronze.eada.total_athletic_expenses` (passthrough) | double | No | No (analytical CDE lives on `athletic_spend_per_fte`) | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO (one of two inputs) | The institution's total intercollegiate athletics expenses for the cycle, in USD, rolled up across every sport (coach salaries, scholarships, operating expenses, recruiting, facilities, travel, equipment, athletically related student aid). **Distribution (Bronze EDA-observed):** range $11,532–$234,409,941; p50 $3,452,941; p95 $44,300,839. 60 institutions exceed $100M (D1 power conferences). **Observed (Base):** 100% non-null. The numerator of `athletic_spend_per_fte` and the denominator of `athletic_subsidy_ratio`. Source: EADA `GRND_TOTAL_EXPENSE`. |
| `total_athletic_revenue` | `bronze.eada.total_athletic_revenue` (passthrough) | double | No | No (analytical CDE lives on `athletic_revenue_per_fte` and `athletic_subsidy_ratio`) | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO (one of two inputs) | The institution's total intercollegiate athletics revenue for the cycle, in USD. EADA convention requires reported revenue ≥ expense at the grand-total grain (deficits are booked as `direct_institutional_support`, a column we do **not** ingest), so revenue ≈ expense for nearly every row. **Distribution (Bronze EDA-observed):** range $11,532–$261,353,404; p50 $3,577,777; p95 $44,777,300. **Observed (Base):** 100% non-null. The numerator of `athletic_revenue_per_fte` and one input to `athletic_subsidy_ratio`. Source: EADA `GRND_TOTAL_REVENUE`. |
| `recruiting_expenses` | `bronze.eada.recruiting_expenses` (passthrough) | double | No | No | — | The institution's total athletic recruiting expenses for the cycle, in USD (travel, lodging, meals, and other costs incurred recruiting prospective student-athletes). **17.8% of institutions report exactly $0** (363/2,040) — these are real reported zeros (mostly NJCAA II/III, CCCAA, NWAC, NCCAA programs that do not recruit off-campus), not suppressions. **Distribution (Bronze EDA-observed):** range $0–$7,455,849; p50 $28,298; p95 $878,902. **Observed (Base):** 100% non-null. The numerator of `recruiting_per_fte`. Source: EADA `RECRUITEXP_TOTAL`. |

### EADA-Sourced Headcount (Bronze Passthrough — Option-C Fallback Denominator)

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `eada_fte_headcount` | `bronze.eada.eada_fte_headcount` (passthrough) | double | No | No (the analytical CDE flag lives on the COALESCE'd `total_fte_enrollment`) | — | EADA's in-file 12-month enrollment headcount, sourced from `EFTotalCount` in `InstLevel.xlsx`. Added to Bronze in the §4 amendment specifically to serve as the §5 Option-C fallback denominator. **Methodologically distinct** from `base.ipeds_finance.total_fte_enrollment` (which is annualized FTE) — the `fte_source` column makes the choice explicit when this column is selected. Available on every EADA row (`has_eada_fte` ~100% true). **Observed (Base):** ~100% non-null. |

### Enrollment Denominator (Hybrid — COALESCE'd in Base)

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `total_fte_enrollment` | **Cross-source LEFT JOIN + COALESCE:** `COALESCE(base.ipeds_finance.total_fte_enrollment, bronze.eada.eada_fte_headcount)` | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | The institution's 12-month enrollment denominator. Prefers `base.ipeds_finance.total_fte_enrollment` (annualized FTE — the project standard); falls back to `bronze.eada.eada_fte_headcount` (12-month headcount) when the IPEDS-Finance value is NULL; NULL only when both sources are missing. The single most load-bearing column for downstream per-FTE comparison. **The two source definitions are not identical** — annualized FTE vs. 12-month headcount — so the `fte_source` column carries the methodological tag. **Observed FTE-source mix (BSE-EAD-011 P1, ±5pp):** ipeds_finance ~74.5% / eada_fte_headcount ~25.5% / none < 1%. **Non-null rate:** > 99% (BSE-EAD-009 P0 caps the `'none'` rate at 1%). |

### FTE Source Provenance (NEW in Base)

Three columns that surface the methodological mix introduced by the §5 Option-C COALESCE. The `fte_source` enum is the primary cross-source-mix governance signal; the two booleans surface per-source presence independently of which source was *chosen*.

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `fte_source` | **Derivation:** `'ipeds_finance'` when IPEDS-Finance had a non-null FTE; else `'eada_fte_headcount'` when EADA's headcount was non-null; else `'none'`. | string (enum) | Yes | **Yes** | (methodological provenance — see Plain-English column) | Explicit per-row stamp recording **which** FTE source was used to compute `total_fte_enrollment`. Three values: `'ipeds_finance'` (preferred — annualized FTE; ~74.5% of rows), `'eada_fte_headcount'` (fallback — 12-month headcount; ~25.5% of rows), `'none'` (both sources missing; < 1% of rows). **Why CDE:** This column is the cross-source-mix governance signal. BSE-EAD-013 (P0) asserts the IPEDS-preference invariant against it (every UNITID with non-null IPEDS-Finance FTE must stamp `'ipeds_finance'` — zero violations) and BSE-EAD-012 (P0) asserts the tautology `total_fte_enrollment IS NULL ⟺ fte_source = 'none'`. Wrong values here would let the silent-LEFT-JOIN-failure bug pass undetected. **Note:** No business term is proposed because the column is methodological provenance, not a business concept — it tells consumers which FTE methodology produced the row, not what the row "is" in domain terms. |
| `has_ipeds_finance_fte` | **Derivation:** `(base.ipeds_finance.total_fte_enrollment IS NOT NULL)` for this UNITID. | boolean | Yes | No | — | True iff `base.ipeds_finance.total_fte_enrollment` was non-null for this UNITID. Surfaces per-source presence independently of which source was *chosen* — useful when downstream consumers want to know whether IPEDS-Finance had data even on rows where EADA's headcount was eventually used (e.g., they shouldn't be — the IPEDS-preference invariant says `has_ipeds_finance_fte = TRUE ⇒ fte_source = 'ipeds_finance'`). **Observed:** ~74.5% true. |
| `has_eada_fte` | **Derivation:** `(bronze.eada.eada_fte_headcount IS NOT NULL)` for this UNITID. | boolean | Yes | No | — | True iff `bronze.eada.eada_fte_headcount` was non-null for this UNITID. **Observed:** ~100% true (EADA's `EFTotalCount` is populated on every row in 2022–23). |

### Per-FTE Derivations (NEW in Base)

The three per-student normalizations of the monetary inputs. Computed in Silver via plain-double arithmetic. **NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. No imputation.** Each derivation inherits the `fte_source` of its denominator — downstream consumers who require methodological homogeneity can filter on `fte_source = 'ipeds_finance'`.

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `athletic_spend_per_fte` | **Derivation:** `total_athletic_expenses / total_fte_enrollment` (NULL when either operand is NULL or FTE ≤ 0) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student athletic spending — the canonical institution-scale athletic-finance signal. Computed in this Base zone for the first time. **NULL semantics:** NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **Observed:** > 99% non-null. **Range guard (BSE-EAD-004 P0):** `≥ 0` where non-null. **Arithmetic invariant (BSE-EAD-008 P0):** `athletic_spend_per_fte × total_fte_enrollment ≈ total_athletic_expenses` within $1 wherever all three are non-null — passes by construction (plain-double divide-then-multiply roundtrip is exact). The EADA-side aura input per spec §6 Decision 11 (the only EADA-sourced direct aura input). |
| `athletic_revenue_per_fte` | **Derivation:** `total_athletic_revenue / total_fte_enrollment` (same NULL rule) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student athletic revenue. Computed in this Base zone for the first time. **NULL semantics:** same as above. **Observed:** > 99% non-null. **Range guard (BSE-EAD-005 P0):** `≥ 0` where non-null. Carried as a context column on `consumable.institution_aura` (not an aura input). |
| `recruiting_per_fte` | **Derivation:** `recruiting_expenses / total_fte_enrollment` (same NULL rule) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE | Per-student athletic recruiting spending. Computed in this Base zone for the first time. **NULL semantics:** same as above. **Observed:** > 99% non-null. **Range guard (BSE-EAD-006 P0):** `≥ 0` where non-null. **Note:** ~17.8% of institutions report `recruiting_expenses = 0` (real reported zeros — see Bronze field above), so their `recruiting_per_fte` is exactly 0.0 — valid, not a DQ failure. |

### Subsidy Intensity (NEW in Base)

A cross-field ratio with no FTE dependency. Computed in Silver via plain-double arithmetic with `NULLIF` semantics on the denominator.

| Field | Source / Derivation | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|---------------------|------|----------|-----|---------------|--------------------------|
| `athletic_subsidy_ratio` | **Derivation:** `(total_athletic_expenses − total_athletic_revenue) / NULLIF(total_athletic_expenses, 0)` (NULL when either operand is NULL or expenses is exactly 0) | double | No | **Yes** | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO | The institution-level athletic subsidy ratio. Positive = subsidized (revenue < expenses); near 0 = self-sustaining; negative = profitable. Computed in this Base zone for the first time; independent of FTE source. **NULL semantics:** NULL when either operand is NULL or `total_athletic_expenses = 0` (mirrors `NULLIF`). **Observed:** 100% non-null in 2022–23 (both Bronze monetary inputs are 100% non-null). **Range guard (BSE-EAD-007 P0, EDA-calibrated 2026-04-30):** `[-3.0, 1.0]` where non-null (original spec band `[-1.0, 1.0]` was empirically falsified by 4 institutions reflecting institutional-transfer accounting — Binghamton −2.92, Haskell Indian Nations −2.56, Kennedy-King −1.57, Rust College −1.43; not data defects). **Distribution invariant (BSE-EAD-010 P1, EDA-calibrated):** `P50 == 0 ∧ P5 < 0 ∧ P95 == 0` (OPE/EADA ledger convention bunches the distribution at zero — see Caveat 3 below). Carried as a context column on `consumable.institution_aura` (NOT an aura input — see spec §2 Decision 11). |

### Pipeline Provenance

| Field | Source | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------|------|----------|-----|---------------|--------------------------|
| `source_load_date` | `bronze.eada.load_date` (passthrough) | date | Yes | No | (Brightsmith convention) | Calendar date the source Bronze data was loaded (UTC). Direct passthrough of `bronze.eada.load_date`. Identical across all rows in a single Base promote run. Used by downstream freshness DQ to reach the original Bronze ingest date even after multiple Silver/Gold promote timestamps stack up. |
| `ingested_at` | `datetime.now(tz=UTC)` at promote time | timestamp | Yes | No | (Brightsmith convention) | UTC wall-clock recording when this Base row was promoted from Bronze. Identical across all rows in a single Base promote run. Distinct from `source_load_date` (the *Bronze* ingest date). |

---

## Data Quality Rules

The 13 Base DQ rules are defined in [governance/dq-rules/base-eada.json](../dq-rules/base-eada.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|----------------|
| BSE-EAD-001 | P0 | (row count) | Base row count == Bronze row count (conservation). |
| BSE-EAD-002 | P0 | `unitid` | Uniqueness within `reporting_year`. |
| BSE-EAD-003 | P0 | `record_id` | Non-null + unique. |
| BSE-EAD-004 | P0 | `athletic_spend_per_fte` | `≥ 0` where non-null. |
| BSE-EAD-005 | P0 | `athletic_revenue_per_fte` | `≥ 0` where non-null. |
| BSE-EAD-006 | P0 | `recruiting_per_fte` | `≥ 0` where non-null. |
| BSE-EAD-007 | P0 | `athletic_subsidy_ratio` | `∈ [-3.0, 1.0]` where non-null (silver-EDA-calibrated). |
| BSE-EAD-008 | P0 | `athletic_spend_per_fte`, `total_fte_enrollment`, `total_athletic_expenses` | Arithmetic invariant: `spend_per_fte × fte ≈ expenses` within $1. |
| BSE-EAD-009 | P0 | `fte_source`, `total_fte_enrollment` | `fte_source` enum membership AND `'none'` rate ≤ 1%. |
| BSE-EAD-010 | P1 | `athletic_subsidy_ratio` | Distribution: `P50 == 0 ∧ P5 < 0 ∧ P95 == 0` (OPE ledger convention; silver-EDA-calibrated). |
| BSE-EAD-011 | P1 | `fte_source` | Distribution: ipeds_finance ~74.5% / eada_fte_headcount ~25.5% (±5pp). |
| BSE-EAD-012 | P0 | `total_fte_enrollment`, `fte_source` | Tautology: `total_fte_enrollment IS NULL ⟺ fte_source = 'none'`. |
| BSE-EAD-013 | P0 | `fte_source`, `base.ipeds_finance.total_fte_enrollment` | IPEDS-preference invariant: every UNITID with non-null IPEDS-Finance FTE stamps `fte_source = 'ipeds_finance'` (zero violations). |

All 13 rules pass against the landed table (snapshot `973879610917339278`). Full scorecard: `governance/dq-scorecards/base-eada-20260501T210828Z.{json,md}`. Adversarial chaos cleared 7/7 (`governance/chaos-reports/base-eada-chaos.md`).

---

## Caveats for Consumers

1. **Per-FTE values cascade NULL when the COALESCE'd FTE is missing.** Less than 1% of institutions have NULL `total_fte_enrollment` (both IPEDS-Finance and EADA-headcount missing), which causes all three per-FTE rates to be NULL on the same row. This is honest data — those rows are simply not usable for per-student comparison. The `fte_source = 'none'` enum value is the explicit marker.

2. **The two FTE sources are methodologically different.** `base.ipeds_finance.total_fte_enrollment` is *annualized FTE* (computed at Bronze as `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` from EFIA). `eada_fte_headcount` is *12-month enrollment headcount* (EADA's `EFTotalCount`). The two are correlated but not identical — annualized FTE accounts for part-time enrollment fractionally; headcount counts each student as 1. Knight Commission per-FTE athletic-spend benchmarks already use `EFTotalCount`, which is why the fallback is analytically defensible. **Downstream consumers who require methodological homogeneity should filter on `fte_source = 'ipeds_finance'`** and accept the 74.5% coverage.

3. **The OPE/EADA ledger convention bunches the subsidy-ratio distribution at zero.** EADA convention requires reported revenue ≥ expense at the grand-total grain — institutions book any operating deficit as `direct_institutional_support` (a separate column we do **not** ingest). The empirical effect: ~63% of rows have revenue exactly equal to expenses, 0% of rows have revenue < expenses. So `athletic_subsidy_ratio` is bunched at zero (P5 = −0.157, P50 = 0.0, P95 = 0.0, max = 0.0, min = −2.92). **The original spec said "P50 > 0 (most athletic programs lose money)" — empirically falsified during silver-EDA on 2026-04-30.** This is **not** a data defect; it is a structural feature of the federal disclosure convention. The "athletics loses money" insight needs the unbundled `direct_institutional_support` field, which is out of scope for this spec. Flag for any future spec amendment that wants the subsidy signal to behave intuitively. BSE-EAD-007 and BSE-EAD-010 are recalibrated against the empirical distribution.

4. **17.8% real-zero `recruiting_expenses` propagate to real-zero `recruiting_per_fte`.** Mostly NJCAA II/III, CCCAA, NWAC, NCCAA programs that don't recruit off-campus. Do **not** add a `> 0` rule for either column.

5. **`record_id` prefix is `ead` at Base, `aur` at Consumable.** Different namespaces. If you see `ead-...` in a consumable read or `aur-...` in a Base read, the wrong prefix was passed to `compute_grain_id()` somewhere upstream.

6. **No imputation.** Per spec §2 Decision #8 and the standing user constraint, NULLs propagate honestly. The Option-C COALESCE is **not** imputation — it is *source selection between two equally-real measurements*, with the choice surfaced as `fte_source` provenance. There is no fallback value or sentinel; when both sources are missing, the FTE column is genuinely NULL.

7. **Arithmetic invariants are self-auditable at rest.** Because the Bronze numerators are carried alongside the COALESCE'd denominator and the Base derivations in the same row, BSE-EAD-008 can be checked without a cross-row join. Passes by construction.

8. **Cycle vintage is academic year 2022–23.** Future-cycle ingest is a parameter change at the Bronze ingestor (`DEFAULT_REPORTING_YEAR`), not a code change at Silver.

9. **No SCD2.** Latest single-cycle snapshot. Multi-cycle history would require partitioning on `reporting_year` and extending the dedup grain.

10. **The three monetary inputs are NOT analytical-CDE *at Base*.** They become CDE at the consumable layer (per spec §6) once exposed to `aura_score` and `athletic_subsidy_ratio` on the consumable. At Base, the per-FTE rates and the subsidy ratio carry the analytical CDE flag. (At Bronze, `total_athletic_expenses` and `total_athletic_revenue` ARE flagged CDE under the upstream-feeder lens — see `governance/cde-tagging/raw-eada.md`. The Base posture re-evaluates against Base-zone consumers.)

11. **`fte_source` is CDE.** It is the cross-source-mix governance signal. Wrong values here would let the silent-LEFT-JOIN-failure bug pass undetected (BSE-EAD-013 P0 explicitly guards against this). Treat it as a load-bearing column even though it looks like a categorical label.

12. **No new business glossary terms introduced in this zone.** The methodological provenance carried by `fte_source` is documented at the `governance/domain-context.md` § EADA Athletics Disclosure level (and in this dictionary), but it is **not** a business term — it is a per-row methodological tag. Per the §6 spec EADA-side BT candidates, the only proposed BT-* term in scope (BT-EAD-ATHLETIC-SUBSIDY-RATIO) was already proposed in the bronze cycle.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-30 | Initial data dictionary for Base table `base.eada` per spec §5 (Option-C amendment 2026-04-30). 18 fields documented (4 identity + 3 monetary inputs + 1 EADA headcount passthrough + 1 hybrid FTE + 3 FTE-source provenance + 4 derivations + 2 provenance), 7 flagged CDE, 0 flagged PII. Field types and nullability verified against landed Iceberg metadata (snapshot `973879610917339278`). DQ scorecard `base-eada-20260501T210828Z` (13/13 PASS) and chaos report (7/7 caught) cross-referenced. | @doc-generator |
