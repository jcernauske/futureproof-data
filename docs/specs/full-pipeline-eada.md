# Spec: full-pipeline-eada

**Status:** DRAFT
**Zone:** Raw → Base → Consumable
**Primary Agent:** @primary-agent
**Created:** 2026-04-30
**Hard Dependency (base zone only):** This spec's `raw` zone is fully independent and can run in parallel with `docs/specs/raw-ingest-ipeds-finance.md`. The dependency kicks in at the `base` zone — `base.ipeds_finance` must exist before §5 runs (`base.eada` LEFT JOINs it for FTE), and both base tables must exist before §6 runs (`consumable.institution_aura` FULL OUTER JOINs them). No dependency on Spec 1's `consumable` zone.

---

## Claude Code Prompt

```
Read the spec at docs/specs/full-pipeline-eada.md in its entirety.

This spec lands the EADA Athletics Disclosure Survey (single source) through three zones:
  raw.eada  →  base.eada  →  consumable.institution_aura

The consumable in this spec is the FUSED institution-level aura table — it joins base.eada
(produced here) with base.ipeds_finance (produced by raw-ingest-ipeds-finance.md) on UNITID
to compute the composite aura_score.

DEPENDENCY (base-zone only — raw can run in parallel with Spec 1):
  - §4 (raw): no dependency. Run immediately, in parallel with raw-ingest-ipeds-finance.md.
  - §5 (base): requires base.ipeds_finance to exist. If missing, STOP and escalate.
  - §6 (consumable): requires both base.ipeds_finance AND base.eada to exist.
  - No dependency on Spec 1's consumable.ipeds_finance_profile.

This is data-only work. NO MCP tool, NO backend service, NO frontend. Stop at consumable.

Execute the standard Brightsmith pipeline workflow:

1. PRE-IMPLEMENTATION REVIEW
   - @bs:governance-reviewer reviews §1–§6.
   - @fp-data-reviewer reviews §3 (Source) and §4–§6 (zones), with explicit assessment of:
       (a) the EADA institution-total filter (the file also has per-team rows),
       (b) the cross-source FTE join from base.ipeds_finance into base.eada,
       (c) the FULL OUTER JOIN strategy at consumable,
       (d) the DRAFT aura_score formula and its weight assumptions.
   - Both write findings to §7.

2. RAW IMPLEMENTATION
   - Implement EadaIngestor at src/raw/eada_ingestor.py extending BaseIngestor.
   - Land raw.eada per §4.

3. EDA + DOMAIN CONTEXT (BLOCKING for aura_score)
   - @bs:data-analyst runs EDA per §4 EDA Requirements + §6 Aura Score EDA Requirements.
   - EDA must finalize the aura_score weights and rescaling bounds before §6 ships.
   - The §6 formula in this spec is DRAFT. Do not implement weights blindly.

4. BASE IMPLEMENTATION
   - Build the base.eada transformer at src/silver/eada_base.py per §5.
   - Cross-source LEFT JOIN base.ipeds_finance for FTE.
   - Use the idempotent promote pattern.

5. CONSUMABLE IMPLEMENTATION
   - Build consumable.institution_aura transformer at src/gold/institution_aura.py per §6.
   - FULL OUTER JOIN base.ipeds_finance ⨝ base.eada on UNITID.
   - Apply EDA-finalized aura_score formula. Stamp aura_score_version.

6. DQ + CHAOS + GOVERNANCE
   - @bs:dq-rule-writer authors rules from §4/§5/§6 + EDA evidence.
   - @bs:dq-engineer executes rules. P0 failures block.
   - @bs:chaos-monkey runs adversarial hardening on consumable.institution_aura (5-cycle).
   - @bs:lineage-tracker, @bs:cde-tagger, @bs:doc-generator produce governance artifacts per §8.

7. SIGN-OFF
   - @bs:governance-reviewer post-implementation review.
   - @bs:staff-engineer final review.
   - @fp-builder runs ruff + mypy + pytest.

OUT OF SCOPE — do not extend:
  - No MCP tool (no entry in src/mcp_server/futureproof_server.py).
  - No backend service / FastAPI router.
  - No frontend wiring (no Stage 2 reveal field, no receipt, no badge).
  - No modification of consumable.career_outcomes, consumable.program_career_paths,
    consumable.career_branches, consumable.occupation_profiles, consumable.onet_work_profiles,
    consumable.career_transitions, consumable.ai_exposure, or consumable.regional_price_parities.
  - No wiring of aura_score into the Five-Stat Pentagon or the boss gauntlet.
  - No imputation of missing values.
  - No multi-year SCD2.

If a reviewer requests one of the above, REJECT it as scope creep — that belongs in a
follow-up spec.
```

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-30 |
| Author | Jeff + Claude |
| Spec Version | 1.0 (DRAFT) |
| Last Updated | 2026-04-30 |
| Blocked By | Partial — `raw` zone is independent and parallelizable. `base` zone requires `base.ipeds_finance` from `raw-ingest-ipeds-finance.md`. `consumable` zone requires both `base.ipeds_finance` and `base.eada`. No dependency on Spec 1's `consumable` zone. |
| Related Specs | `docs/specs/raw-ingest-ipeds-finance.md` (upstream — provides `base.ipeds_finance`); `docs/specs/completed/raw-ingest-bea-rpp.md` (single-spec multi-zone reference); `docs/specs/completed/raw-ingest-college-scorecard-institution.md` (UNITID join partner) |

---

## §1 Problem Statement

EADA (Equity in Athletics Disclosure Act) publishes per-institution athletic expenses, athletic revenue, and recruiting expenses for every postsecondary institution that has intercollegiate athletics. Combined with the IPEDS Finance signals (`raw-ingest-ipeds-finance.md`), it answers a second-order question students rarely see surfaced honestly: **how much of this school's institutional posture is funded by — or subsidizing — its athletic program?**

This spec lands EADA through Raw → Base → Consumable. The consumable in this spec is the **fused** institution-level aura table that combines IPEDS Finance signals with EADA athletic signals into a single composite `aura_score`. EADA contributes athletic-spend-per-FTE, athletic-revenue-per-FTE, and the athletic-subsidy ratio; IPEDS Finance contributes the marketing_ratio and endowment_per_fte. The composite is min/max rescaled to 1–10 like HMN.

**The aura_score is a DRAFT.** Weights and rescaling bounds must be finalized after EDA on real data — see §6 Aura Score EDA Requirements.

**Hard scope boundary:** No modification of the Five-Stat Pentagon, the boss fight system, or any existing `consumable.*` table other than the new `consumable.institution_aura` produced here. Additive only.

---

## §2 Design Decisions

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Single spec covers all three zones for one source, modeled on `raw-ingest-bea-rpp.md` | EADA is narrow (~2,100 rows, 3 fields). The fusion belongs in this spec because it's the EADA-side enrichment that "completes" the aura signal. | 3 specs. Rejected per BEA precedent and per Jeff's instruction (1 spec per source). |
| 2 | The fused `consumable.institution_aura` lives in this spec, not in the IPEDS Finance spec | The IPEDS Finance spec already produces a clean stand-alone profile. Adding fusion there would couple it to EADA's lifecycle. The fusion happens here because it's the EADA-side completion of the composite. | Put fusion in IPEDS spec. Rejected — couples lifecycles. Third-spec fusion. Rejected — Jeff said 2 specs total. |
| 3 | FTE for EADA's per-FTE derivations is **COALESCE(base.ipeds_finance.total_fte_enrollment, raw.eada.eada_fte_headcount)** with explicit `fte_source` provenance — primary IPEDS Finance where available, fall back to EADA's in-file `EFTotalCount` (12-month enrollment headcount) where IPEDS Finance is missing. EDA-determined coverage: IPEDS-only path was 74.5%; hybrid is ~100%. **Amended 2026-04-30.** Original decision (single-source IPEDS Finance LEFT JOIN) was rejected post-EDA because it NULL-ed the 521 (~25.5%) EADA institutions missing from `base.ipeds_finance` — predominantly 2-year colleges (NJCAA / CCCAA / NWAC), which is exactly the population for whom Title IX / equity questions about athletic spend are most policy-relevant. The two FTE definitions (`total_fte_enrollment` is annualized; `EFTotalCount` is 12-month headcount) are NOT identical; the `fte_source` column makes the methodological mix explicit so downstream consumers can stratify or reject the hybrid as needed. See `governance/domain-context.md` "Decision 3" for the full Options A/B/C analysis, including Knight Commission's per-FTE benchmarks (which use EADA's `EFTotalCount`). | A — IPEDS Finance only (original spec). Rejected — 25.5% coverage gap on 2-year colleges. B — EADA EFTotalCount only. Rejected — methodologically inconsistent with `endowment_per_fte` which already uses IPEDS Finance FTE; loses single-source consistency at consumable. C (chosen) — Hybrid COALESCE with provenance column. |
| 4 | Consumable is a FULL OUTER JOIN on UNITID | Many institutions report IPEDS Finance but not EADA (no athletic program); a small number have EADA without complete IPEDS Finance. INNER would silently drop schools the user can search for in the existing product. | INNER. Rejected — violates CLAUDE.md "no path is out of scope." |
| 5 | aura_score is DRAFT pending EDA | The proposed three-signal blend is plausible but unvalidated. Real distributions, correlations, and outlier behavior must be observed before locking weights. | Lock weights now. Rejected — same failure mode as the v3 AI exposure rescore. |
| 6 | Min/max rescaling to integer 1–10 mirrors HMN | Project-wide convention for 1–10 scores. | 0–100 percentile. Rejected — convention break. |
| 7 | aura_score is computed only when `has_ipeds_finance = TRUE` | The marketing_ratio + endowment signal is the analytical core. Athletics is additive when present. EADA-only rows get NULL aura_score. | Compute from athletic data alone. Rejected — single-signal composite is not a composite. |
| 8 | aura_score_version column is stamped on every row (`"v0-draft"`) | Future formula revisions are traceable without schema churn. | Implicit version. Rejected — no provenance. |
| 9 | "PrivacySuppressed" / EADA sentinels → NULL in raw | Project convention. | Preserve sentinels. Rejected. |
| 10 | `aura_score` is a **neutral brand-gravity signal** — all three input signals push aura UP when brand presence is strong (high endowment, high marketing spend, high athletic spend) | Aura is meant to be neutral, not a value judgment. The score itself does not encode "good" or "bad." Whether brand gravity delivers outcomes is what the **pentagon shape reveals** when aura is viewed alongside ERN and ROI — a high-aura/low-ERN combination tells a different story than a high-aura/high-ERN combination. The score must not pre-judge that interpretation. | Inverted formula treating high marketing or high athletic spend as "lower aura." Rejected — encodes a value judgment that duplicates ROI / ERN signal and removes the analytical tension that makes aura useful alongside the pentagon. |
| 11 | Aura input signals: `endowment_per_fte`, `marketing_ratio`, `athletic_spend_per_fte` | All three are direct (not inverted) and all three are size-of-brand-presence measures. `athletic_subsidy_ratio` is excluded from the composite because it encodes a normative judgment (subsidy = bad). It remains on the consumable as useful context, just not as an aura input. | Use `athletic_subsidy_ratio` (inverted) as the athletic input. Rejected per Decision 10. |

### Constraints

- Hard dependency on `base.ipeds_finance` (from `raw-ingest-ipeds-finance.md`).
- Hard scope ends at `consumable.institution_aura` write.
- Additive-only — no modification of any other table.
- Chunked CSV reads per CLAUDE.md.
- `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)` on all downloads.

---

## §3 Source

| Property | Value |
|---|---|
| Provider | U.S. Department of Education, Office of Postsecondary Education |
| URL | `https://ope.ed.gov/athletics/` (Custom Data → CSV) |
| Method | Bulk CSV download |
| Grain | One row per institution (UNITID) per reporting year (multiple per-team rows in source; we filter to institution totals) |
| Key | UNITID |
| Expected rows | ~2,100 (only institutions with intercollegiate athletics report) |
| License | U.S. Government Work — public domain |

### Target Fields

The EADA file publishes per-team detail rows AND institution-level total rows. We want institution-level totals only. **Exact column names must be verified against the EADA codebook by @bs:data-analyst during EDA**; EADA renames columns periodically.

| Concept | EADA column (EDA-confirmed) | raw column |
|---|---|---|
| Total athletic expenses | `GRND_TOTAL_EXPENSE` | `total_athletic_expenses` |
| Total athletic revenue | `GRND_TOTAL_REVENUE` | `total_athletic_revenue` |
| Recruiting expenses | `RECRUITEXP_TOTAL` | `recruiting_expenses` |
| EADA in-file FTE / 12-month enrollment headcount | `EFTotalCount` | `eada_fte_headcount` |

> **§5 EFTotalCount addition (2026-04-30 amendment):** The original spec did not capture EADA's own `EFTotalCount` column. §2 Decision 3 was amended to adopt Option C (COALESCE hybrid with provenance) for the §5 FTE join, which requires `EFTotalCount` to be present in `raw.eada`. Add `eada_fte_headcount` (double) to the raw schema (§4) and to the EadaIngestor's column extraction. **The currently-landed `bronze.eada` (2,040 rows) does NOT contain this column and must be re-ingested with the EFTotalCount addition before §5 base implementation.** See §5 Sources line for the full COALESCE expression.

> **EDA correction (2026-04-30):** Original working assumptions were `EXP_TOTAL_TOTAL` / `REV_TOTAL_TOTAL` / `RECRUITEXP_TOTAL_TOTAL`. @bs:data-analyst confirmed against the live EADA 2022–2023 datafile (`InstLevel.xlsx`, 2,040 rows) that the actual column names are `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL`. Identity columns are lowercase `unitid` / `institution_name` (not `UNITID` / `INSTNM`). EDA report: `governance/eda/full-pipeline-eada-raw-eda.md`.

> **EDA correction — institution-total filter (2026-04-30):** Original spec assumed institution totals were a marker-filtered subset (e.g., "rows where `SPORT_CODE IS NULL`"). @bs:data-analyst confirmed institution totals live in a **separate file** — the EADA datafile zip contains both `InstLevel.xlsx` (institution totals, what we want) and `Schools.xlsx` (per-team rows, which we do NOT ingest). No in-pipeline filter is needed; the ingestor consumes `InstLevel.xlsx` directly. RAW-EAD-012 remains valuable as a regression tripwire (post-ingest row count must remain ≈ distinct UNITIDs). Pin: `INSTITUTION_TOTAL_FILTER_COLUMN = None`, `INSTITUTION_TOTAL_FILTER_VALUE = None`.

---

## §4 Zone 1 — Raw

### Iceberg Table: `raw.eada`

- **Grain:** UNITID
- **Dedup grain:** `[unitid]`
- **Expected rows:** ~2,100

### Ingestor

- **Class:** `EadaIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/eada_ingestor.py`
- **Implementation notes:**
  - Download single CSV from `https://ope.ed.gov/athletics/`. Specify in the docstring whether the request returns institution-totals-only (preferred) or all-rows-with-in-pipeline filter; the EADA Custom Data Cutting Tool exposes both modes. If all-rows-with-filter, the institution-total marker (column + value) chosen during EDA must be cited verbatim in the `EadaIngestor` docstring.
  - Filter to institution-total rows (the file also has per-team rows). The exact filter (column + sentinel) is **BLOCKING on @bs:data-analyst's EDA confirmation** — see §4 EDA Requirements item 1. Do not hardcode a filter before EDA finalizes.
  - Coerce `unitid` to `long` at raw write (matching `raw.ipeds_finance.unitid` typing). Preserve any leading zeros if EADA delivers UNITID as a string with quoted/zero-padded values; non-null assertion on every row.
  - Replace EADA suppression sentinels (blank, `-1`, `-2`) with NULL across all numeric fields before type coercion
  - Capture EADA's `EFTotalCount` column as `eada_fte_headcount` (double) per §3 Target Fields. Required for the §5 Option-C COALESCE FTE source. **The currently-landed `bronze.eada` (2,040 rows, 2026-04-30) was ingested before this amendment and does NOT contain this column.** A one-off re-ingest is required before §5 base implementation runs; the re-ingest is idempotent (same UNITID grain, same snapshot semantics) and overwrites the existing snapshot.
  - Set `User-Agent` header

### Raw Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| unitid | long | yes | IPEDS institution ID |
| institution_name | string | yes | EADA `institution_name` (lowercase column in InstLevel.xlsx) |
| reporting_year | int | yes | Pinned per ingest (EADA file does not carry an in-row year column); EADA 2022-2023 datafile → `reporting_year=2022` (academic-year-start convention) |
| total_athletic_expenses | double | no | GRND_TOTAL_EXPENSE |
| total_athletic_revenue | double | no | GRND_TOTAL_REVENUE |
| recruiting_expenses | double | no | RECRUITEXP_TOTAL |
| eada_fte_headcount | double | no | EADA's `EFTotalCount` (12-month enrollment headcount). Added 2026-04-30 to support §5 Decision 3 Option-C hybrid FTE source. |
| source_url | string | yes | EADA download URL |
| source_method | string | yes | `bulk_csv_download` |
| ingested_at | timestamp | yes | Raw write timestamp |
| load_date | date | yes | Date of load |

> **DQ threshold footnote (2026-04-30):** The completeness rules below show the original spec thresholds (`≥ 95%` / `≥ 80%`). The runtime DQ rule JSON at `governance/dq-rules/raw-eada.json` was tightened to `≥ 99%` based on EDA-observed 100% non-null on all three monetary fields. Rule JSON is the runtime source-of-truth; rule notes in the JSON document the divergence with EDA citation.

### DQ Rules (Raw) — `RAW-EAD-*`

| Rule | Priority | Dimension |
|---|---|---|
| RAW-EAD-001 row count between 1,800 and 2,300 | P0 | Volume |
| RAW-EAD-002 unitid non-null 100% | P0 | Completeness |
| RAW-EAD-003 unitid uniqueness | P0 | Uniqueness |
| RAW-EAD-004 total_athletic_expenses ≥ 0 where non-null | P0 | Validity |
| RAW-EAD-005 total_athletic_revenue ≥ 0 where non-null | P0 | Validity |
| RAW-EAD-006 recruiting_expenses ≥ 0 where non-null | P0 | Validity |
| RAW-EAD-007 total_athletic_expenses non-null ≥ 95% | P0 | Completeness |
| RAW-EAD-008 total_athletic_revenue non-null ≥ 95% | P0 | Completeness |
| RAW-EAD-009 recruiting_expenses non-null ≥ 80% | P1 | Completeness |
| RAW-EAD-010 reporting_year is single value across all rows | P0 | Consistency |
| RAW-EAD-011 spot check: at least one row total_athletic_expenses > $100M (D1 anchor) | P1 | Plausibility |
| RAW-EAD-012 post-filter row count is within 1% of distinct UNITIDs in raw (catches per-team leak AND over-filter) | P0 | Conservation |

### EDA Requirements

@bs:data-analyst must answer before base proceeds:

1. **Institution-total filter correctness (BLOCKING for raw promotion).** The EADA file has per-team rows. Confirm the *exact* column and value that distinguishes institution totals (e.g., "rows where `SPORT_CODE IS NULL`" or "rows from the `institution_totals.csv` sub-file"). The chosen marker must be (a) cited verbatim in the EDA report, and (b) pinned in the `EadaIngestor` docstring before raw promotion. RAW-EAD-012 (P0) is the runtime tripwire for filter misfires.
2. **Column name verification (RESOLVED 2026-04-30).** Confirmed against EADA 2022-2023 InstLevel.xlsx: `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL` (not the original spec assumptions). Identity columns are lowercase `unitid` / `institution_name`. Pinned in the EadaIngestor via the `__init__` parameters listed in the EDA report's "EadaIngestor Configuration Pin" block.
3. **Distribution shapes** for the three monetary fields — histograms, P5/P50/P95.
4. **UNITID overlap** with `base.ipeds_finance` (most EADA reporters should also be in IPEDS Finance) and with `consumable.career_outcomes`. The observed overlap calibrates BSE-EAD-009's 95% threshold; mark the threshold as EDA-promoted before base ships.

EDA report → `governance/eda/full-pipeline-eada-raw-eda.md`.

---

## §5 Zone 2 — Base

### Iceberg Table: `base.eada`

- **Grain:** UNITID
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='ead')`
- **Idempotent:** Yes
- **Sources:** `raw.eada` LEFT JOIN `base.ipeds_finance` on UNITID (Option-C COALESCE hybrid — see Base Transformations item 2).

> **§5 Option-C amendment (2026-04-30):** The original spec used `base.ipeds_finance.total_fte_enrollment` as the sole FTE source. EDA found that path covered only 74.5% of EADA institutions, NULL-ing per-FTE derivations for the 521 (~25.5%) institutions missing from IPEDS Finance — predominantly 2-year colleges (NJCAA / CCCAA / NWAC). §2 Decision 3 was amended to adopt Option C: COALESCE the IPEDS-Finance FTE with EADA's in-file `EFTotalCount` (added to `raw.eada` per the §4 amendment) and stamp an explicit `fte_source` provenance column. Hybrid coverage: ~100%. The two FTE definitions are NOT identical — `total_fte_enrollment` is annualized, `EFTotalCount` is 12-month headcount — so the `fte_source` column makes the methodological mix explicit. Knight Commission's per-FTE athletic-spend benchmarks already use EADA's `EFTotalCount`, which strengthens this choice.

### Base Transformations

1. **Passthrough from raw:** `unitid`, `institution_name`, `reporting_year`, `total_athletic_expenses`, `total_athletic_revenue`, `recruiting_expenses`, `eada_fte_headcount`.
2. **Hybrid FTE source (Option C):** LEFT JOIN `base.ipeds_finance` on UNITID to fetch `total_fte_enrollment` (the IPEDS-Finance annualized FTE). Then COALESCE with `raw.eada.eada_fte_headcount` and stamp the provenance:
   ```sql
   total_fte_enrollment = COALESCE(
     base.ipeds_finance.total_fte_enrollment,
     raw.eada.eada_fte_headcount
   )

   fte_source = CASE
     WHEN base.ipeds_finance.total_fte_enrollment IS NOT NULL THEN 'ipeds_finance'
     WHEN raw.eada.eada_fte_headcount            IS NOT NULL THEN 'eada_fte_headcount'
     ELSE                                                          'none'
   END

   has_ipeds_finance_fte = (base.ipeds_finance.total_fte_enrollment IS NOT NULL)
   has_eada_fte          = (raw.eada.eada_fte_headcount             IS NOT NULL)
   ```
   Schools with no FTE from either source get NULL FTE and consequently NULL per-FTE values — this is correct behavior. The expected residual NULL rate is < 1% based on EDA. **No imputation.**
3. **Per-FTE derivations:**
   ```
   athletic_spend_per_fte   = total_athletic_expenses / total_fte_enrollment
   athletic_revenue_per_fte = total_athletic_revenue  / total_fte_enrollment
   recruiting_per_fte       = recruiting_expenses     / total_fte_enrollment
   ```
   NULL when either operand is NULL or `total_fte_enrollment ≤ 0`. **No imputation.** Each derivation inherits the `fte_source` of its denominator — downstream consumers can stratify or filter on `fte_source` if methodological homogeneity is required.
4. **Athletic subsidy ratio:**
   ```
   athletic_subsidy_ratio = (total_athletic_expenses - total_athletic_revenue) / NULLIF(total_athletic_expenses, 0)
   ```
   Positive = athletics is subsidized by the rest of the budget. Near 0 = self-sustaining. Negative = profitable. (Independent of FTE source.)
5. **Provenance:** `source_load_date` (from raw), `ingested_at` (base promotion timestamp), plus the `fte_source` column described in item 2.

### Base Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| record_id | string | yes | `ead-…` |
| unitid | long | yes | |
| institution_name | string | yes | |
| reporting_year | int | yes | |
| total_athletic_expenses | double | no | Raw passthrough |
| total_athletic_revenue | double | no | Raw passthrough |
| recruiting_expenses | double | no | Raw passthrough |
| eada_fte_headcount | double | no | Raw passthrough — EADA's in-file `EFTotalCount` (12-month headcount). Available on every EADA row. |
| total_fte_enrollment | double | no | **COALESCE result** — `base.ipeds_finance.total_fte_enrollment` if non-null, else `raw.eada.eada_fte_headcount`. NULL only when both sources are missing. |
| fte_source | string | yes | Provenance for `total_fte_enrollment`: `'ipeds_finance'` (preferred, annualized FTE) / `'eada_fte_headcount'` (fallback, 12-month headcount) / `'none'` (both missing — should be < 1%). |
| has_ipeds_finance_fte | boolean | yes | TRUE iff `base.ipeds_finance.total_fte_enrollment` was non-null for this UNITID |
| has_eada_fte | boolean | yes | TRUE iff `raw.eada.eada_fte_headcount` was non-null for this UNITID (expected ~100%) |
| athletic_spend_per_fte | double | no | Derived; inherits `fte_source` of denominator |
| athletic_revenue_per_fte | double | no | Derived; inherits `fte_source` of denominator |
| recruiting_per_fte | double | no | Derived; inherits `fte_source` of denominator |
| athletic_subsidy_ratio | double | no | Derived (independent of FTE source) |
| source_load_date | date | yes | |
| ingested_at | timestamp | yes | |

### DQ Rules (Base) — `BSE-EAD-*`

| Rule | Priority | Dimension |
|---|---|---|
| BSE-EAD-001 row count == raw row count | P0 | Conservation |
| BSE-EAD-002 unitid uniqueness | P0 | Uniqueness |
| BSE-EAD-003 record_id non-null + unique | P0 | Validity |
| BSE-EAD-004 athletic_spend_per_fte ≥ 0 where non-null | P0 | Validity |
| BSE-EAD-005 athletic_revenue_per_fte ≥ 0 where non-null | P0 | Validity |
| BSE-EAD-006 recruiting_per_fte ≥ 0 where non-null | P0 | Validity |
| BSE-EAD-007 athletic_subsidy_ratio ∈ [-1.0, 1.0] where non-null | P0 | Validity |
| BSE-EAD-008 invariant: `athletic_spend_per_fte * total_fte_enrollment` ≈ `total_athletic_expenses` within $1 where all three non-null | P0 | Arithmetic |
| BSE-EAD-009 `fte_source IN {'ipeds_finance', 'eada_fte_headcount', 'none'}` and `fte_source = 'none'` rate ≤ 1% (post-Option-C residual NULL rate, expected < 1% based on EDA — chaos manifest must force a UNITID-type-mismatch test against the IPEDS-Finance LEFT JOIN to confirm fall-through to `eada_eftotalcount` works) | P0 | Validity, EDA-calibrated |
| BSE-EAD-010 athletic_subsidy_ratio P50 > 0 (most athletic programs lose money) — threshold EDA-calibrated against the BSE EDA item 1 distribution measurement | P1 | Plausibility, EDA-calibrated |
| BSE-EAD-011 fte_source distribution: `ipeds_finance` rate is approximately 74.5% of total rows (matches the EDA-measured IPEDS-Finance UNITID overlap) and `eada_eftotalcount` rate is approximately 25.5% — threshold EDA-calibrated, ±5pp tolerance | P1 | Distribution, EDA-calibrated |
| BSE-EAD-012 every row with `total_fte_enrollment IS NOT NULL` has `fte_source ≠ 'none'`; every row with `total_fte_enrollment IS NULL` has `fte_source = 'none'` | P0 | Arithmetic / Provenance |
| BSE-EAD-013 IPEDS-preference invariant: for every UNITID in `base.ipeds_finance` with non-null `total_fte_enrollment`, the corresponding `base.eada` row stamps `fte_source = 'ipeds_finance'`. Violation count must be 0. Catches partial silent LEFT-JOIN failure where some institutions correctly resolve to IPEDS while others silently fall through to the EADA fallback. | P0 | Cross-source / Provenance |

---

## §6 Zone 3 — Consumable

### Iceberg Table: `consumable.institution_aura`

- **Grain:** UNITID
- **Dedup grain:** `[unitid]`
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='aur')`
- **Idempotent:** Yes
- **Sources:** `base.ipeds_finance` FULL OUTER JOIN `base.eada` on UNITID
- **Expected rows:** approximately the union of finance reporters and EADA reporters (effectively bounded by IPEDS Finance row count since most EADA reporters also report Finance)

### Consumable Transformations

1. **Identity columns from the merge:**
   ```sql
   COALESCE(f.unitid, e.unitid)                     AS unitid,
   COALESCE(f.institution_name, e.institution_name) AS institution_name
   ```
2. **Passthrough analytical columns:**
   - From `base.ipeds_finance`: `endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `marketing_ratio`
   - From `base.eada`: `athletic_spend_per_fte`, `athletic_revenue_per_fte`, `athletic_subsidy_ratio` (context column — **not an aura_score input**, see §2 Decision 11)
3. **Coverage flags:**
   ```
   has_ipeds_finance = (f.unitid IS NOT NULL)
   has_eada          = (e.unitid IS NOT NULL)
   coverage_tier     = CASE
     WHEN has_ipeds_finance AND has_eada THEN 'both'
     WHEN has_ipeds_finance              THEN 'finance_only'
     WHEN has_eada                       THEN 'athletics_only'
   END
   ```
4. **`aura_score` (DRAFT — see Aura Score EDA Requirements below):** Neutral brand-gravity composite per §2 Decision 10/11. All three input signals are direct (not inverted): higher input → higher aura. `athletic_subsidy_ratio` is **deliberately excluded** as an input.
   ```
   -- DRAFT formula. Weights and rescaling bounds finalized post-EDA.
   -- All three signals push aura UP when brand presence is strong.
   norm_marketing  = clip(rank_pct(marketing_ratio),        0.0, 1.0)   -- higher → HIGHER aura
   norm_endowment  = clip(rank_pct(endowment_per_fte),      0.0, 1.0)   -- higher → HIGHER aura
   norm_athletic   = clip(rank_pct(athletic_spend_per_fte), 0.0, 1.0)   -- higher → HIGHER aura

   raw_score = (
       0.40 * norm_marketing
     + 0.40 * norm_endowment
     + 0.20 * norm_athletic               -- coverage: when has_eada=FALSE, EDA decides
                                          -- whether to drop term and reweight 0.50/0.50,
                                          -- impute 0.5, or null aura_score.
   )

   aura_score_continuous = 1.0 + 9.0 * raw_score          -- min/max rescale to [1, 10]
   aura_score            = ROUND(aura_score_continuous)   -- integer 1..10
   ```
   **`athletic_subsidy_ratio` is intentionally NOT an aura input.** It carries a value judgment (subsidy = "bad") that overlaps with ROI / ERN and removes the analytical tension between aura and the pentagon. It remains on the consumable as a context column for downstream consumers that want it.
   - `rank_pct` is a percentile rank computed across all rows with a non-null value for that signal — same pattern HMN uses.
   - `aura_score` is computed only when `has_ipeds_finance = TRUE`. EADA-only rows get NULL `aura_score`.
   - `aura_score_version` is stamped `"v0-draft"` for all rows produced by this spec.
5. **Provenance:** `promoted_at` timestamp.

### Consumable Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| record_id | string | yes | `aur-…` |
| unitid | long | yes | Join key to existing consumable.* tables |
| institution_name | string | yes | |
| endowment_per_fte | double | no | From `base.ipeds_finance` |
| institutional_support_per_fte | double | no | From `base.ipeds_finance` |
| instruction_per_fte | double | no | From `base.ipeds_finance` |
| marketing_ratio | double | no | From `base.ipeds_finance` |
| athletic_spend_per_fte | double | no | From `base.eada`. Aura input. FTE denominator provenance is in `athletic_fte_source`. |
| athletic_revenue_per_fte | double | no | From `base.eada`. Context only. |
| athletic_subsidy_ratio | double | no | From `base.eada`. **Context only — NOT an aura_score input** (see §2 Decision 11). |
| athletic_fte_source | string | no | Provenance for the FTE denominator behind the three EADA per-FTE columns: `'ipeds_finance'` / `'eada_fte_headcount'` / `'none'`. NULL when `has_eada = FALSE`. Pass-through from `base.eada.fte_source`. Surfaced so downstream consumers can stratify or filter on FTE methodology consistency (see §2 Decision 3). |
| aura_score | int | no | 1–10 integer composite. NULL when `has_ipeds_finance = FALSE`. Neutral brand-gravity signal — higher = stronger brand presence (endowment + marketing + athletic spend), not "better" or "worse." |
| aura_score_continuous | double | no | Pre-rounding continuous value, for downstream auditability |
| aura_score_version | string | yes | `"v0-draft"` for the formula in this spec |
| aura_score_basis | string | no | Records which input set computed the score: `three_term` (marketing + endowment + athletic), `two_term_finance_only` (marketing + endowment, athletic dropped + reweighted 0.50/0.50), or NULL when `aura_score` itself is NULL. Documents cross-stratum comparability for downstream consumers. Final basis-handling rule for `coverage_tier = finance_only` is selected by EDA per §6 Aura Score EDA Requirements item 4. |
| has_ipeds_finance | boolean | yes | |
| has_eada | boolean | yes | |
| coverage_tier | string | yes | `both` / `finance_only` / `athletics_only` |
| promoted_at | timestamp | yes | |

### DQ Rules (Consumable) — `CON-AUR-*`

**P0 — structural & invariants**

| Rule | Priority | Dimension |
|---|---|---|
| CON-AUR-001 row count between max(base row counts) and (base.ipeds_finance + base.eada) row counts (FULL OUTER bound) | P0 | Conservation |
| CON-AUR-002 unitid non-null 100% | P0 | Completeness |
| CON-AUR-003 unitid uniqueness | P0 | Uniqueness |
| CON-AUR-004 record_id non-null + unique | P0 | Validity |
| CON-AUR-005 coverage_tier ∈ {both, finance_only, athletics_only} | P0 | Validity |
| CON-AUR-006 every row has ≥1 of (has_ipeds_finance, has_eada) = TRUE | P0 | Validity |
| CON-AUR-007 institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio within 0.001 where all three non-null | P0 | Arithmetic |

**P0 — aura_score validity**

| Rule | Priority | Dimension |
|---|---|---|
| CON-AUR-010 aura_score ∈ [1, 10] where non-null | P0 | Validity |
| CON-AUR-011 aura_score IS NULL exactly when has_ipeds_finance = FALSE | P0 | Validity |
| CON-AUR-012 aura_score_version = `"v0-draft"` for all rows produced by this spec | P0 | Provenance |
| CON-AUR-013 aura_score = ROUND(aura_score_continuous) for every row | P0 | Arithmetic |
| CON-AUR-014 aura_score_continuous ∈ [1.0, 10.0] where non-null | P0 | Validity |

**P1 — referential integrity to existing consumables**

| Rule | Priority | Dimension |
|---|---|---|
| CON-AUR-020 every UNITID in `consumable.institution_aura` exists in `consumable.career_outcomes.unitid` OR is documented as expected drift in EDA | P1 | Cross-source |
| CON-AUR-021 ≥ 90% of distinct UNITIDs in `consumable.career_outcomes` find a matching row in `consumable.institution_aura` | P1 | Coverage, EDA-calibrated |

> **Note on CON-AUR-020 (downgrade rationale):** The FULL OUTER JOIN can legitimately surface institutions that report Finance / EADA but are not in `consumable.career_outcomes` — international campuses, specialty institutions, schools below the program-completion threshold that filtered out at College Scorecard ingest. CON-AUR-021's 90% coverage rule already catches the cases that matter (real gaps in the student-facing join graph). Exceptions surfaced by CON-AUR-020 should be enumerated and explained in the EDA report, not block promotion.

**P1 — distribution sanity**

| Rule | Priority | Dimension |
|---|---|---|
| CON-AUR-030 aura_score distribution: ≥ 6 of 10 buckets populated (rejects degenerate concentration) — threshold EDA-calibrated; multimodality from `coverage_tier` strata may require relaxing 6/10 or stratifying the rule by `aura_score_basis` | P1 | Distribution, EDA-calibrated |
| CON-AUR-031 aura_score median ∈ [4, 7] | P1 | Distribution, EDA-calibrated |
| CON-AUR-032 known-anchor spot checks (filled in post-EDA): public flagship vs. private LAC vs. high-athletic-subsidy program | P1 | Plausibility |

### Aura Score EDA Requirements (BLOCKING)

Before §6 ships, EDA must answer:

1. **Distribution shapes** of `marketing_ratio`, `endowment_per_fte`, `athletic_subsidy_ratio` — histograms + P5/P50/P95.
2. **Outlier behavior at anchor schools** — Harvard / Princeton (extreme endowment), an SEC athletics powerhouse (extreme `athletic_spend_per_fte`), a marketing-heavy for-profit (extreme `marketing_ratio`). The composite must not collapse to a single signal at the tails. **Pass criterion (explicit):** each of the three anchor classes must produce `aura_score ≥ 8`. If any anchor class lands below 8 because the other two signals drag it down, the composite is broken and the formula must be revised.
3. **Correlation structure.** Are the three signals independent enough to justify a weighted blend? If `endowment_per_fte` and `marketing_ratio` are strongly anti-correlated (likely at the tails — endowment-rich electives have low marketing ratios; endowment-poor for-profits have high marketing ratios), the 0.40/0.40 split partially **cancels** rather than reinforces. **Action criterion (explicit):** if `|corr(norm_endowment, norm_marketing)| > 0.4` (Spearman or rank-percentile correlation, EDA's choice), EDA must produce ≥3 candidate composite forms (e.g., weighted-mean as today, `MAX(norm_marketing, norm_endowment)` for either-dimension brand gravity, log-additive composite) and select one via the §6 EDA item 2 anchor-school validation.
4. **Coverage when `coverage_tier = finance_only`.** §2 Decision 7 says EADA-only rows get NULL aura. The reciprocal — finance-only rows (no athletic program; ~30–40% of US 4-years) — is undefined in the v0 draft. **EDA must produce a recommendation, not a menu.** Three options were considered:
   - (a) **Drop the athletic term and reweight `0.50 / 0.50` marketing/endowment.** Preserves rank ordering within the no-athletics class; changes score meaning across `coverage_tier` strata. The `aura_score_basis` column documents the difference for downstream consumers.
   - (b) **Impute neutral 0.5 for `norm_athletic`.** Biases the no-athletics class toward median brand gravity, understates the truth at extreme cases like MIT (no major athletic program; very high endowment + marketing). **EDA should reject this option** unless it can show the bias is small at MIT-class anchors.
   - (c) **NULL aura_score for finance_only.** NULLs aura for ~30–40% of US 4-years. **EDA should reject this** — violates CLAUDE.md "no path is out of scope" if a student picks MIT or any non-athletics 4-year.

   **Default recommendation (subject to EDA confirmation):** option (a) — drop term + reweight 0.50/0.50, stamp `aura_score_basis = 'two_term_finance_only'` so cross-stratum comparability is documented in the schema. EDA may overrule with evidence; if so, the chosen option must be cited in `governance/eda/consumable-institution-aura-eda.md` and the `aura_score_basis` column populated accordingly.
5. **Rescaling target.** Is the post-rescale distribution a usable 1–10 spread, or does everything land in [4, 7]? If the latter, switch to percentile bounds (e.g., P5/P95).
6. **Sign convention (locked — confirm only).** Per §2 Decision 10/11, aura is a **neutral brand-gravity** signal: higher aura = higher brand presence (high endowment, high marketing spend, high athletic spend). The score does NOT encode "good" or "bad." Whether brand gravity delivers outcomes is the pentagon's job (aura vs. ERN/ROI). EDA must (a) confirm the rank-percentile transformation produces the expected directional alignment for all three signals against anchor schools (Harvard high; a low-marketing low-athletic regional public lower), and (b) confirm that `athletic_subsidy_ratio` is reported as a context column only and not threaded into any aura computation.
7. **FTE-source stratification (added 2026-04-30 with Option-C amendment).** §2 Decision 3 introduces a methodological mix at `athletic_spend_per_fte`: ~74.5% of rows are denominated against IPEDS-Finance annualized FTE, ~25.5% against EADA's 12-month headcount (`eada_fte_headcount`). The two definitions are NOT identical. EDA must stratify both `athletic_spend_per_fte` and the resulting `aura_score` distribution by `athletic_fte_source ∈ {'ipeds_finance', 'eada_fte_headcount'}`. **Pass criterion (explicit):** if the median `aura_score` differs by ≥ 1 integer bucket between the two strata, EDA must either (i) rank-percentile within stratum and recombine before rescaling, or (ii) drop the athletic term and stamp `aura_score_basis = 'two_term_finance_only'` for the `eada_fte_headcount` stratum. The intent is to convert the methodological mix from an implicit assumption into an EDA-validated property. Also examine the 2 × 3 (`aura_score_basis` × `athletic_fte_source`) interaction grid — if any of the six cells is degenerate or systematically biased, document it in the EDA report and decide whether CON-AUR-030 needs stratification by `athletic_fte_source` rather than just `aura_score_basis`.

EDA output may revise the §6 formula, the §6 DQ thresholds, and the `aura_score_version` string. Treat the formula as v0-draft; bump to v1 only after EDA + sign-off.

EDA report → `governance/eda/consumable-institution-aura-eda.md`.

### Data Contract

| Property | Value |
|---|---|
| Owner | @bs:data-steward |
| SLA | Annual refresh aligned with the upstream IPEDS Finance + EADA cadences |
| Quality tier | `partial_verification` until EDA finalizes the aura_score |
| Consumers | None at the time of this spec — additive landing only |
| Row count guarantee | Full outer of base inputs, no additional drops |
| CDE candidates | `aura_score`, `marketing_ratio`, `endowment_per_fte`, `athletic_spend_per_fte`, `athletic_subsidy_ratio`, `athletic_fte_source` (methodological-provenance CDE — affects how `athletic_spend_per_fte` is interpreted across rows; added with Option-C amendment 2026-04-30) |

### Business Glossary Terms (Proposed)

Final IDs assigned by @bs:data-steward.

- **BT-EAD-ATHLETIC-SUBSIDY-RATIO** — Fraction of an institution's athletic expenses not covered by athletic revenue. `(expenses − revenue) / expenses`. Positive values mean the rest of the institution's budget subsidizes athletics; near-zero values mean self-sustaining; negative values mean the program is profitable.
- **BT-AUR-AURA-SCORE** — A neutral institution-level **brand-gravity** signal. Composite of three direct (non-inverted) inputs: `endowment_per_fte`, `marketing_ratio`, and `athletic_spend_per_fte`. All three push aura UP when brand presence is strong. Min/max rescaled to integer 1–10 via rank-percentile of each input. **Higher aura = higher brand gravity, not "better" or "worse."** The score itself does not encode a value judgment about whether the brand delivers outcomes — that interpretation emerges from the pentagon shape when aura is viewed alongside ERN and ROI (e.g., high-aura/low-ERN tells a different story than high-aura/high-ERN). `athletic_subsidy_ratio` is **deliberately excluded** from the composite (it encodes a normative judgment that overlaps with ROI/ERN); it lives on the consumable as a context column only. Versioned via `aura_score_version`; initial release is `"v0-draft"` pending EDA finalization.
- **BT-AUR-COVERAGE-TIER** — Classification of which upstream sources contributed to a given aura row: `both` / `finance_only` / `athletics_only`. Used by downstream consumers to gauge confidence in the composite.

---

## §7 Architecture / Data Review

### @bs:governance-reviewer
**Status:** APPROVED — CHANGES REQUESTED (non-blocking, post-impl cleanup)
**Review Type:** Pre-Implementation
**Date:** 2026-04-30

#### Verdict
- [x] APPROVED (with required path renames + minor additions enumerated below — all are non-blocking on §4 raw start, but must be resolved before the post-implementation review will sign off)
- [ ] CHANGES REQUESTED (blocking)
- [ ] REJECTED

The spec is implementation-ready. The §4 raw zone may begin in parallel with `full-pipeline-ipeds-finance.md` immediately. The §6 consumable is correctly gated behind a BLOCKING EDA on aura_score weights — that gate is wired tightly enough that no plausible read of the spec authorizes locking weights without EDA evidence + version bump. Required changes below are governance-artifact hygiene, glossary IDs, and one missing CDE candidate; none of them block §4 or §5.

#### Pre-Implementation Checklist
- [x] Problem statement and success criteria (§1) — clear: composite institution-level brand-gravity signal; aura_score is the deliverable; no surfacing.
- [x] Input sources identified (§3) — provider, URL, grain, key, expected row count, license all present. Column names flagged as "working assumption, verify in EDA," which is correct since EADA renames columns.
- [x] Output artifacts defined (§4/§5/§6) — three Iceberg tables with full schemas, types, required flags, derivation rules.
- [x] Transformations described (§5/§6) — passthroughs, cross-source LEFT JOIN, FULL OUTER JOIN, derivation formulas, NULL semantics, all spelled out.
- [x] Zone assignment correct — Raw / Base / Consumable. EADA is canonical raw; FTE join is properly placed at base; composite is properly at consumable.
- [x] Primary implementation agent identified — Claude Code general (per fan-out from prompt).
- [x] DQ rule categories specified — RAW-EAD-* (11), BSE-EAD-* (10), CON-AUR-* (14). Volume / Completeness / Uniqueness / Validity / Conservation / Arithmetic / Cross-source / Plausibility / Distribution / Provenance dimensions all covered.
- [x] CDE mapping impact assessed — §6 Data Contract lists 4 candidates (see issue #4 below for the missed one).
- [x] Lineage scope defined — §8 explicitly requires lineage to list both `base.ipeds_finance` and `base.eada` as inputs to the consumable.
- [x] Breaking changes flagged — none. Spec is rigorously additive (§2 Constraints, prompt OUT OF SCOPE block).
- [x] Testing approach — per-zone DQ rules + chaos manifest on consumable + adversarial audit + scorecards + golden anchors.
- [x] Data Model Gate (Greenfield) — three new tables, three sets of conceptual/logical/physical models required in §8. Models must exist and be APPROVED before §4/§5/§6 implementations respectively. Per-zone gating is appropriate for a multi-zone spec.

#### Assessment Against Reviewer's Eight Questions

**1. Spec completeness (§3 source / §4–§6 schemas + DQ).** PASS. §3 has provider, URL (`https://ope.ed.gov/athletics/`), method (bulk CSV), grain (UNITID), key (UNITID), expected rows (~2,100), license. §4/§5/§6 each have complete typed schemas with required flags and per-zone DQ rule tables. The "working assumption" caveat on EADA column names is properly handled by gating column verification on @bs:data-analyst's EDA before base proceeds — not a gap, this is the correct treatment for a source whose schema drifts.

**2. Idempotency / grain prefix conventions.** PASS. `compute_grain_id(row, ['unitid'], prefix='ead')` (base) and `compute_grain_id(row, ['unitid'], prefix='aur')` (consumable) both follow the 3-letter lowercase convention demonstrated in `docs/specs/completed/raw-ingest-bea-rpp.md` (`prefix='rpp'`, `prefix='rpc'`) and confirmed in `src/silver/bls_ooh_transformer.py` (`prefix='ooh'`), `src/silver/college_scorecard_transformer.py` (`prefix='cs'`). The single-key `[unitid]` grain is consistent with the §3-declared grain. The promote is idempotent — re-running over the same `raw.eada` deterministically yields the same `record_id`s.

**3. Cross-source dependency on `base.ipeds_finance`.** PASS, well-stated. The dependency is declared in three places that are mutually consistent: (a) the **Hard Dependency** field at the top of the spec (line 7); (b) the **Blocked By** row in §1 Metadata (line 97); (c) the Claude Code Prompt's DEPENDENCY block (lines 23–27). All three correctly identify that §4 raw is independent and parallelizable, §5 base requires `base.ipeds_finance`, §6 consumable requires both base tables. The escalation path on missing `base.ipeds_finance` ("STOP and escalate") is explicit. No ambiguity.

**4. BLOCKING EDA gate on aura_score weights.** PASS. The gate is wired in five places that close every plausible bypass: (a) §1 line 108 — "weights and rescaling bounds must be finalized after EDA on real data"; (b) §2 Decision 5 — "aura_score is DRAFT pending EDA"; (c) Claude Code Prompt step 3 — "EDA must finalize the aura_score weights and rescaling bounds before §6 ships. Do not implement weights blindly"; (d) §6 formula block lines 322–343, every weight is annotated DRAFT and the coverage-tier=finance_only branch is explicitly deferred to EDA; (e) §6 Aura Score EDA Requirements (BLOCKING), lines 410–423, six required answers including a confirmation-only check on the locked sign convention. `aura_score_version = "v0-draft"` is stamped on every row and (CON-AUR-012, P0) any row missing that stamp fails P0. Rule: bumping to v1 requires "EDA + sign-off." There is no path through the spec that authorizes locking weights without EDA evidence and an explicit version bump.

**5. Governance artifact path consistency in §8.** **CHANGES REQUESTED (non-blocking).** The spec was renamed from `raw-ingest-eada.md` to `full-pipeline-eada.md` but several §8 paths still use the old basename. Recommend renaming the **spec-scoped** artifacts to `full-pipeline-eada-*` and keeping the **table-scoped** artifacts as-is. Specifically:

   | §8 line | Current path | Required action |
   |---|---|---|
   | 466 | `governance/eda/raw-ingest-eada-eda.md` | Rename to `governance/eda/full-pipeline-eada-raw-eda.md` (this EDA covers the raw zone of the full-pipeline spec, not a raw-ingest spec). |
   | 467 | `governance/eda/consumable-institution-aura-eda.md` | Keep as-is — table-scoped, not spec-scoped. |
   | 469 | `governance/models/raw-ingest-eada-{conceptual,logical,physical}.md` | Rename to `governance/models/raw-eada-{conceptual,logical,physical}.md` (drop the spec verb; the model names a table, not a spec). |
   | 470 | `governance/models/base-eada-{...}.md` | Keep as-is. |
   | 471 | `governance/models/consumable-institution-aura-{...}.md` | Keep as-is. |
   | 472 | `governance/dq-rules/raw-ingest-eada.json` | Rename to `governance/dq-rules/raw-eada.json` to match the table name (the rules are scoped to `raw.eada`, not to a spec). The `base-eada.json` and `consumable-institution-aura.json` siblings (lines 473–474) already use this convention; this one is the outlier. |
   | 478 | `governance/lineage/raw-ingest-eada-{timestamp}.json` | Rename to `governance/lineage/full-pipeline-eada-{timestamp}.json`. The lineage event is spec-scoped (it lists both base inputs to the consumable, which is a §6 thing, not a raw thing). The current name misleadingly suggests this is a raw-only lineage event. |
   | 483 | `governance/approvals/raw-ingest-eada-{pre,post,staff}-review.md` | Rename to `governance/approvals/full-pipeline-eada-{pre,post,staff}-review.md`. Approvals are spec-scoped. |
   | (new) | — | Add `governance/reviews/full-pipeline-eada-pre-review.md` and `…-post-review.md` to §8 to match the path declared in this agent's CLAUDE.md ("Save review reports to: `governance/reviews/[spec-name]-[pre|post]-review.md`"). The spec currently only references `governance/approvals/`; both should exist. |

   Rationale for the rename split: artifacts that describe a **table** (DQ rules, models for that table, EDA on that table) carry the table name. Artifacts that describe a **spec's execution** (lineage event, approvals, reviews, the multi-zone EDA bundle) carry the spec name. The current §8 mixes these conventions because the spec was renamed mid-draft.

   This is non-blocking on §4 raw start. Fix before @bs:doc-generator runs and before post-implementation review.

**6. CDE candidates in §6 Data Contract.** **CHANGES REQUESTED (non-blocking).** The four named candidates (`aura_score`, `marketing_ratio`, `endowment_per_fte`, `athletic_subsidy_ratio`) are correct. **`athletic_spend_per_fte` should be added** as a fifth CDE candidate. Rationale: per §2 Decision 11 it is one of the three direct inputs to `aura_score`, alongside `marketing_ratio` and `endowment_per_fte` (both already CDEs). It is the **only aura_score input** not flagged. Excluding it breaks the cross-agent consistency check between the data contract and the aura formula — @bs:cde-tagger needs to flag every signal the score depends on, not just two of three. Add it; final tagging is @bs:cde-tagger's call but the candidate list must not have a hole.

**7. Business glossary terms.** PASS with one minor suggestion. The three BT-* proposals (BT-EAD-ATHLETIC-SUBSIDY-RATIO, BT-AUR-AURA-SCORE, BT-AUR-COVERAGE-TIER) carry full enough definitions for @bs:data-steward to assign final IDs without further clarification. BT-AUR-AURA-SCORE in particular is unusually thorough — it explicitly states the neutrality property, the input set, the exclusion of `athletic_subsidy_ratio` with rationale, the rescaling target, and the versioning hook. **Suggestion (non-blocking):** consider whether `athletic_spend_per_fte` deserves its own BT term given it is the EADA-side aura input and is not synonymous with `total_athletic_expenses`. Steward's call.

**8. Scope discipline.** PASS. The Claude Code Prompt's OUT OF SCOPE block (lines 72–82) is explicit and exhaustive: no MCP tool, no backend service, no FastAPI router, no frontend wiring (no Stage 2 reveal field, no receipt, no badge), no modification of any existing `consumable.*` table, no aura_score wiring into pentagon or boss gauntlet, no imputation, no SCD2. §1 line 110 reinforces "additive only." §2 Constraints (line 134) reinforces "additive-only." The spec is internally consistent on this point and the prompt explicitly authorizes REJECTING reviewer requests that violate scope as scope creep — that is the correct posture.

#### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | §8 governance-artifact paths mix `raw-ingest-eada-*` (legacy, pre-rename) with table-scoped names. See question 5 table above for the seven specific path renames. | Update §8 path strings before @bs:doc-generator runs. Non-blocking on §4. |
| 2 | CHANGES REQUESTED | §6 Data Contract CDE candidate list omits `athletic_spend_per_fte`, the EADA-side aura_score input. The other two aura inputs are listed; the candidate list must not asymmetrically exclude one of three. | Add `athletic_spend_per_fte` to the §6 Data Contract CDE candidates row. Non-blocking on §4/§5; must be in place before @bs:cde-tagger runs. |
| 3 | CHANGES REQUESTED | §8 does not list `governance/reviews/full-pipeline-eada-{pre,post}-review.md` even though @bs:governance-reviewer's contract requires writing to that path. The spec lists `governance/approvals/` only. | Add both review paths to §8. Non-blocking. |
| 4 | ADVISORY | §3 column-name table flags EADA columns as "working assumption" pending @bs:data-analyst verification. The §4 EDA Requirements item 2 captures this correctly. No spec change required, but the raw ingestor must not hardcode column names — it must read column names from the verified-codebook output of EDA before implementation locks. | Implementation guidance for the raw step; flag for @fp-data-reviewer. |
| 5 | ADVISORY | §6 CON-AUR-001 row-count rule expresses an FOJ bound but does not also assert `count(consumable) ≤ count(base.ipeds_finance) + count(base.eada) − count(both)` — the inclusion-exclusion tighter bound. Current loose bound passes but admits drift. | Optional tightening. Non-blocking; consider in @bs:dq-rule-writer's pass. |
| 6 | ADVISORY | BT-AUR-AURA-SCORE definition is excellent but BT-AUR-COVERAGE-TIER could specify that downstream consumers of `aura_score` SHOULD prefer rows where `coverage_tier='both'` for cross-school comparisons. Steward's call. | Optional refinement. Non-blocking. |

#### Decision Rationale

This spec is one of the most rigorous I've reviewed for this project. The signal-direction debate captured in §2 Decisions 10–11 and §10 Discussion is exactly the kind of design conversation that should be visible on the artifact, not buried in chat history. The decision to make `aura_score` a **neutral brand-gravity signal** and exclude `athletic_subsidy_ratio` from the composite is well-reasoned and prevents the score from double-counting the ROI / ERN signal that the pentagon already carries.

The DRAFT status of the formula is properly defended by a multi-layer EDA gate (§1, §2 Decision 5, prompt step 3, §6 formula annotations, §6 Aura Score EDA Requirements, CON-AUR-012 P0). I tried to find a path through the spec where weights could be locked without EDA evidence; there is no such path. The version-stamping hook (`aura_score_version`) and the explicit "bump to v1 only after EDA + sign-off" instruction close the door.

The cross-source dependency is correctly hard-stated in three mutually-consistent places. The FULL OUTER JOIN at consumable is correctly defended against scope-discipline pressure to use INNER (which would silently drop searchable schools — a CLAUDE.md "no path is out of scope" violation).

The CDE-candidate hole on `athletic_spend_per_fte` (issue #2) and the §8 path renames (issue #1) are real but small. They are governance-artifact hygiene, not design defects, and they do not block §4 raw start. The post-implementation review will not sign off until both are fixed.

Verdict: APPROVED to begin §4 raw work in parallel with `full-pipeline-ipeds-finance.md`. Issues #1–#3 must be resolved before post-implementation review.

#### Audit Trail Reference

This decision is logged under spec-name `full-pipeline-eada` at `governance/audit-trail/full-pipeline-eada-pre-review-2026-04-30.md` (to be written by this agent on review completion).

#### Amendment — Re-Review After Spec Edits
**Date:** 2026-04-30
**Review Type:** Pre-Implementation (re-review)

##### Updated Verdict
- [x] APPROVED (no remaining issues)
- [ ] CHANGES REQUESTED
- [ ] REJECTED

##### Issue Resolution

| # | Original Issue | Status | Verification |
|---|---|---|---|
| 1 | §8 governance-artifact paths mixed `raw-ingest-eada-*` (legacy) with table-scoped names; seven specific renames required. | **RESOLVED** | §8 lines 665–684 verified: spec-scoped artifacts now use `full-pipeline-eada-*` (raw EDA at line 665, lineage at line 678, approvals at line 684); table-scoped artifacts use the table name (`consumable-institution-aura-eda.md` line 666, `raw-eada-*` / `base-eada-*` / `consumable-institution-aura-*` models at lines 668–670, `raw-eada.json` / `base-eada.json` / `consumable-institution-aura.json` DQ rules at lines 671–673). All seven path renames from question 5's table are applied. |
| 2 | §6 Data Contract CDE candidate list omitted `athletic_spend_per_fte` (the EADA-side aura input), creating an asymmetric hole — the other two aura inputs were listed but not the third. | **RESOLVED** | §6 line 442 verified: CDE candidates row now reads `` `aura_score`, `marketing_ratio`, `endowment_per_fte`, `athletic_spend_per_fte`, `athletic_subsidy_ratio` `` — five candidates including `athletic_spend_per_fte`. Cross-agent consistency between data contract and aura formula is restored; @bs:cde-tagger now sees all three direct aura inputs flagged. |
| 3 | §8 missing entries for `governance/reviews/full-pipeline-eada-{pre,post}-review.md` despite this agent's contract requiring writes to that path. | **RESOLVED** | §8 line 683 verified: `` `governance/reviews/full-pipeline-eada-pre-review.md`, `governance/reviews/full-pipeline-eada-post-review.md` `` are now both listed as required artifacts, distinct from the `governance/approvals/` entries on line 684. Both paths now appear in the spec's artifact ledger. |

##### Confirmation
All three CHANGES REQUESTED items from the original review are resolved. The spec is now fully implementation-ready with no remaining governance-artifact hygiene gaps. ADVISORY items #4–#6 from the original review are unchanged in disposition (still advisory; not blocking). The BLOCKING EDA gate on aura_score weights, the FULL OUTER coverage strategy, the cross-source dependency on `base.ipeds_finance`, and the additive-only scope discipline all remain correctly wired. No new issues introduced by the amendments. Verdict upgraded from "APPROVED — CHANGES REQUESTED (non-blocking)" to clean **APPROVED**.

### @fp-data-reviewer
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-30

#### Data Sources Affected
- **EADA Athletics Disclosure Survey** (new) — `raw.eada` → `base.eada`
- **IPEDS Finance** (existing, from `full-pipeline-ipeds-finance.md`) — joined into `base.eada` for FTE, and full-outer-joined at `consumable.institution_aura`
- **Pipeline zones touched:** Bronze (raw.eada), Silver (base.eada), Gold (consumable.institution_aura)
- **Existing consumables affected:** None (additive landing; UNITID referential checks against `consumable.career_outcomes` only)

#### Crosswalk Impact
No CIP↔SOC crosswalk. The only join is institution-level on UNITID. UNITID typing is consistent: `long` in `raw.eada` (§4), `long` in `raw.ipeds_finance` / `base.ipeds_finance` / `base.college_scorecard_institution`, and `long` in `consumable.career_outcomes`. No string/long mismatch risk if the EADA ingestor coerces UNITID to `long` at raw landing — **§4 should state this explicitly** (see Concern B-1 below).

#### Formula Verification
- **`athletic_subsidy_ratio = (expenses − revenue) / NULLIF(expenses, 0)`** — correct sign (positive = subsidized), correctly NULL-safe at the divisor. BSE-EAD-007 bounds it to [-1, 1] which is right when `revenue ∈ [0, 2 × expenses]`; tail outliers (revenue > 2× expenses, theoretically possible at a profitable D1 program) would violate the bound. **EDA must verify no real row exceeds [-1, 1]** before this stays P0.
- **Per-FTE derivations** — clean. NULL-safe on both operands and on `total_fte_enrollment ≤ 0`. BSE-EAD-008 arithmetic invariant is correct.
- **`marketing_ratio` invariant CON-AUR-007** — algebraically sound: `institutional_support_per_fte / instruction_per_fte = (institutional_support / FTE) / (instruction / FTE) = institutional_support / instruction = marketing_ratio`. FTE cancels correctly. Within-0.001 tolerance is appropriate for double division.
- **`aura_score` rescale** `1.0 + 9.0 * raw_score` correctly maps `[0, 1] → [1, 10]`. Floor-of-1 invariant is preserved. `ROUND` to integer is consistent with HMN convention.

#### Findings

##### (a) EADA institution-total filter correctness
**Risk: HIGH if filter misfires.** The EADA file mixes per-team rows (one per sport, per institution, per gender) with institution-total rows. A leak of per-team rows would:
1. Violate `RAW-EAD-003 unitid uniqueness` (multiple rows per UNITID) — this is the right tripwire and it is in place.
2. If uniqueness is enforced via "first row wins" rather than total-row filter, the kept row is a single team's expenses, which would silently undercount `total_athletic_expenses` by 5–20× at a multi-sport school. Anchor schools (Ohio State, Alabama) would surface as having lower athletic spend than mid-majors. `RAW-EAD-011` (at least one row > $100M) catches the gross-anchor failure but **not** the per-team-leak failure where every row is plausibly sized.

**The filtering plan is inadequate as currently written.** §4 says "Filter to institution-total rows (the file also has per-team rows)" — that's a directive, not a specification. The EADA codebook uses a sport-code column (historically `SPORT_CODE` or `Sport`) and a gender column; institution totals are typically the rows where the sport code = a sentinel (e.g., 0, blank, "Total", or a separate file). **We do not declare which marker we trust.**

**Concern A-1 — Specify the institution-total marker:** §3 / §4 must require `@bs:data-analyst` to confirm during EDA the *exact* column and value that distinguishes institution totals (e.g., "rows where `SPORT_CODE IS NULL`" or "rows from the `institution_totals.csv` sub-file"). The §4 EDA Requirements item 1 currently says "Confirm the column or row marker" — this is correct in spirit but needs to be **BLOCKING** for raw promotion, not just an EDA deliverable.
- **Risk:** silent per-team leak undercounts athletic spend at multi-sport schools, inverting the rank-percentile direction of `norm_athletic`. Anchor schools end up with low aura inputs.
- **Fix:** Add `RAW-EAD-012 row count after filter ≈ row count of distinct UNITIDs in raw (within 1%)` as P0. This catches both per-team leak AND over-filter (where totals get dropped). Also require @bs:data-analyst's EDA report to explicitly cite the chosen marker in `governance/eda/raw-ingest-eada-eda.md` and pin it in `EadaIngestor`'s docstring.

**Concern A-2 — EADA file format:** The EADA "Custom Data Cutting Tool" has historically allowed users to choose institution-total OR per-team output at download time. If the ingestor downloads from a stable URL, it must hardcode the request such that totals are guaranteed. If it downloads the raw all-rows file, the filter is in-pipeline. §4 doesn't say which. **Specify the download mode in `EadaIngestor` implementation notes.**

##### (b) Cross-source FTE join from base.ipeds_finance into base.eada

**LEFT JOIN is correct** (not INNER). EADA reporters that lack IPEDS Finance rows (small institutions below Finance's filtering threshold; very rarely, EADA-reporters that didn't file Finance that cycle) would be silently dropped under INNER, violating CLAUDE.md's "no path is out of scope." LEFT preserves EADA rows with NULL FTE → NULL per-FTE values. This is the right semantics.

**`fte_source_available BOOLEAN` flag and BSE-EAD-009** — handled correctly. The flag is set at base, and BSE-EAD-009 P1 ≥ 95% catches systemic join failure (e.g., UNITID-type mismatch making all FTE NULL). Good.

**UNITID-typing risk:** Both `raw.eada.unitid` (§4) and `raw.ipeds_finance.unitid` are declared `long`. The base-zone join will not silently INNER-fail on type mismatch *if* the ingestors actually coerce.

**Concern B-1 — UNITID coercion in EadaIngestor:** §4 declares `unitid: long` but doesn't state how it's coerced. EADA CSVs have historically delivered UNITID as `int` (6-digit) but occasionally with leading zeros stripped or quoted. The ingestor must explicitly cast to `long` (matching IPEDS Finance) and validate non-null at raw write. Add: `EadaIngestor must coerce unitid to long with leading-zero preservation if encountered as string`. This belongs in §4 Ingestor implementation notes.
- **Risk:** silent type mismatch → all 2,100 EADA rows get NULL FTE → BSE-EAD-009 fires → caught. So this is well-tripwired *if* BSE-EAD-009 runs as P1-blocking. **Recommend BSE-EAD-009 stay P1 but be added to the chaos manifest** (force a UNITID-type mismatch and confirm BSE-EAD-009 catches it).

**Concern B-2 — FTE staleness:** `base.ipeds_finance.total_fte_enrollment` comes from Fall 2023 EF in the IPEDS Finance spec. EADA's reporting cycle and IPEDS EF cycle are not always co-aligned (EADA is typically published ~12 months after the academic year; EF is Fall snapshot). This isn't a blocker — annual variance in FTE is small (<3% at most institutions) — but it is a measurement artifact worth a doc-only acknowledgment in `governance/eda/raw-ingest-eada-eda.md`. **Suggested note only.**

##### (c) FULL OUTER JOIN strategy at consumable

**FULL OUTER is correct per §2 Decision 4.** INNER would drop:
- Schools with IPEDS Finance but no athletic program (no NCAA / no NAIA participation) — a large class.
- Schools with EADA but historical / atypical Finance gaps (specialty institutions, military academies sometimes file differently).

**Identity column COALESCE** is the right pattern but has one risk:

**Concern C-1 — Institution name divergence on COALESCE:** `COALESCE(f.institution_name, e.institution_name)` silently picks IPEDS's name when both are present. IPEDS HD and EADA INSTNM occasionally diverge in formatting (e.g., "Ohio State University-Main Campus" vs. "Ohio State University, The"). This is fine for the canonical name, but if `coverage_tier = athletics_only` (~rare), the consumable carries EADA's name which may not match `consumable.career_outcomes.institution_name`. Downstream consumers joining on name (not UNITID) would split.
- **Risk:** Low — UNITID is the canonical join key, not name. Name is for display.
- **Fix:** Add `institution_name_source string` column (`'ipeds_finance'` / `'eada'`) for downstream debuggability. **Optional, not blocking.**

**`coverage_tier` exhaustiveness** — the CASE expression is exhaustive *given* CON-AUR-006 (every row has ≥1 source). The fourth case (both NULL) is impossible by FULL OUTER semantics on UNITID. CON-AUR-006 is the right guard. **Approved.**

**INNER-like behavior guards:** CON-AUR-001 (row count between max(base counts) and sum of base counts) and CON-AUR-006 (≥1 source TRUE) together would catch silent INNER degradation. CON-AUR-001's lower bound `max(base row counts)` is the critical tripwire — if FULL OUTER silently degraded to INNER, the row count would equal *intersection size*, which is below `max(base)` if either source has a tail not in the other. **Both rules are sufficient. Approved.**

**Concern C-2 — Empty UNITID handling:** If either base table contains a row with `unitid IS NULL` (it shouldn't — both have P0 non-null rules), FULL OUTER would produce a "ghost row" with NULL on both sides of identity. CON-AUR-002 catches this at the consumable. **Belt-and-suspenders only; not a fix request.**

##### (d) DRAFT aura_score formula and weight assumptions

**Architectural soundness:** The rank-percentile transformation is the right choice — it's distribution-agnostic and matches HMN. The min/max rescale to [1,10] is correct. The neutral brand-gravity sign convention (Decision 10/11) is well-articulated and §6 EDA item 6 properly locks it as **confirmation-only**, which is the right disposition pre-EDA.

**Weight risks (must be enumerated in EDA before v1):**

**Concern D-1 — Signal correlation / double-counting (endowment + marketing):** Endowment-rich institutions (Harvard, Princeton, Yale) have low `marketing_ratio` because their `instruction_expenses` are very large in absolute terms (low-student-faculty-ratio model). Endowment-poor for-profits (Phoenix, Liberty) have high `marketing_ratio`. **The two signals are likely strongly anti-correlated at the tails**, which means 0.40 × norm_marketing + 0.40 × norm_endowment partially **cancels** rather than reinforces — Harvard gets high endowment, low marketing, mid composite; Phoenix gets low endowment, high marketing, mid composite. The aura collapses to "athletic spend" as the deciding factor. §6 EDA item 3 correctly flags correlation, but **does not specify the action** if anti-correlation is found. Should the formula switch to `MAX(norm_marketing, norm_endowment)` (brand gravity from either dimension), or to a log-additive composite? **EDA must select among at least three remediation options before locking weights.** Recommend §6 EDA item 3 be expanded to: "If |corr| > 0.4, EDA must produce three candidate formulas and pick one with anchor-school validation."

**Concern D-2 — Tail collapse at anchor schools:** §6 EDA item 2 already requires Harvard / SEC / for-profit anchor checks — this is the right hook. **But the spec doesn't say what the pass criterion is.** A reasonable bar: each of the three anchor classes (extreme endowment, extreme athletic, extreme marketing) must produce aura_score ≥ 8. If any anchor lands below 8 because the other two signals drag it down, the composite is broken. **Add explicit pass criterion to §6 EDA item 2.**

**Concern D-3 — `coverage_tier = finance_only` behavior is undefined:** §2 Decision 7 says "aura_score is computed only when has_ipeds_finance = TRUE" — i.e., EADA-only rows get NULL aura. But it does NOT specify what happens for finance-only (no athletics) rows. §6 says the formula has three terms; if `norm_athletic` is NULL because the school has no EADA row, the spec offers three options (drop term + reweight, impute 0.5, NULL the score) and defers to EDA. **This is correct disposition for v0-draft, but two of the three options are subtly wrong:**
   - **Impute 0.5** — biases the no-athletics class toward median brand gravity, which understates the truth at, e.g., MIT (no major athletic program; very high endowment + marketing). MIT would lose 0.20 × (its true high signal) and gain 0.20 × 0.5 instead. *Reject this option in EDA.*
   - **Drop term and reweight 0.50/0.50** — preserves rank ordering within the no-athletics class but changes the score's meaning across `coverage_tier` strata. Harvard (both, has athletics) and MIT (finance-only) would no longer be on the same scale.
   - **NULL aura_score for finance_only** — would NULL aura for ~30–40% of all institutions (most US 4-years aren't NCAA/NAIA filers). **This violates the CLAUDE.md "no path out of scope" principle** if a student picks MIT. *Likely the wrong choice.*
   - **Recommend EDA explicitly select "drop term + reweight 0.50/0.50" with a `aura_score_basis` column** indicating which input set was used. Then the score remains comparable within each basis-stratum, and downstream consumers can branch on the column. Add this as §6 EDA item 4 expansion.
- **Risk:** high — this affects ~1,000+ rows, not an edge case.
- **Fix:** §6 EDA item 4 must produce a *recommendation*, not a list of options. The data review will revisit at v1.

**Concern D-4 — Sign convention check (§6 item 6):** §6 EDA item 6 properly locks the neutral brand-gravity convention and explicitly requires confirming that `athletic_subsidy_ratio` is *not* threaded into aura. **This is correctly framed and matches Decisions 10/11.** Approved as-is. The §6 schema also correctly marks `athletic_subsidy_ratio` as "context only — NOT an aura_score input." Good.

**Concern D-5 — EDA-calibrated DQ thresholds:** Several rules are flagged "EDA-calibrated" (BSE-EAD-010, CON-AUR-021, CON-AUR-031). Two more should be:
- **CON-AUR-030 ≥ 6 of 10 buckets populated** — this is a guess pre-EDA. If the rank-percentile composite + the integer round produces a multimodal distribution (likely if there are coverage_tier strata), 6/10 may be too aggressive or not aggressive enough. **Mark as EDA-calibrated.**
- **BSE-EAD-009 fte_source_available ≥ 95%** — depends on the actual EADA × IPEDS Finance UNITID overlap, which is what §4 EDA item 4 measures. **Mark as EDA-calibrated** (or hard-promote after EDA confirms).

#### Disclaimer Check
- [x] AI-estimated values labeled — N/A, no Gemma-derived fields in this spec
- [x] Confidence scores propagated where crosswalk < Tier 2 — N/A, no CIP↔SOC mapping
- [x] Required disclaimer strings present — `aura_score_version = "v0-draft"` is the per-row provenance flag; `coverage_tier` exposes basis; adequate
- [ ] **Missing data states handled** — partial: per-FTE NULLs are correctly NULL (not 0); aura_score NULL for `has_ipeds_finance = FALSE` is correctly stamped. **Missing piece: `coverage_tier = finance_only` aura behavior is undefined (Concern D-3).** Until EDA decides, downstream consumers cannot tell whether a NULL aura means "EADA-only" or "finance-only with athletic term dropped." Resolve in EDA.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Required before raw promotion (BLOCKING):**
1. (A-1) Add P0 row-count rule `RAW-EAD-012 post-filter row count ≈ distinct UNITIDs (within 1%)` to catch per-team leak / over-filter.
2. (A-1) Mark `@bs:data-analyst` confirmation of the institution-total marker as BLOCKING for raw promotion in §4 EDA Requirements item 1; require the chosen marker to be cited in `EadaIngestor` docstring.
3. (A-2) Specify in §4 Ingestor implementation notes whether the download is institution-totals-only (preferred) or all-rows-with-filter.
4. (B-1) Add explicit `unitid → long` coercion note in §4 Ingestor implementation notes.

**Required before consumable promotion (BLOCKING):**
5. (D-1) Expand §6 EDA item 3: if signal correlation |r| > 0.4, EDA produces ≥3 candidate formulas and picks one via anchor-school validation.
6. (D-2) Add explicit pass criterion to §6 EDA item 2: each anchor class produces `aura_score ≥ 8`.
7. (D-3) Expand §6 EDA item 4 to require an actual recommendation (not a menu). Add `aura_score_basis` column to schema if drop-term-and-reweight is chosen, so cross-stratum comparability is documented.
8. (D-5) Mark CON-AUR-030 and BSE-EAD-009 as EDA-calibrated.

**Suggested (non-blocking):**
- (B-2) Document FTE-staleness measurement artifact in raw EDA report.
- (C-1) Optional `institution_name_source` column for cross-source name divergence debuggability.

The architecture is sound. The neutral brand-gravity sign convention is the right call and well-defended. The FULL OUTER + coverage_tier strategy is correct. The blocker set is concentrated in (a) the EADA filter specification — a real silent-failure vector — and (d) the EDA's required outputs being more prescriptive than menu-style.

#### Amendment — Re-Review 2026-04-30
**Status:** APPROVED
**Reviewed:** 2026-04-30 (re-review against prior CHANGES REQUESTED)

Re-read §4 (Ingestor + DQ rules + EDA Requirements), §5 (BSE-EAD-009), and §6 (Schema, CON-AUR-030, EDA Requirements items 2/3/4) to verify the eight prior blocking items.

##### Resolution Status

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | (A-1) RAW-EAD-012 P0 post-filter row count rule | **RESOLVED** | §4 DQ table: "RAW-EAD-012 post-filter row count is within 1% of distinct UNITIDs in raw (catches per-team leak AND over-filter) \| P0 \| Conservation" |
| 2 | (A-1) §4 EDA item 1 marked BLOCKING + marker-citation in `EadaIngestor` docstring | **RESOLVED** | §4 EDA Requirements item 1: "BLOCKING for raw promotion... must be (a) cited verbatim in the EDA report, and (b) pinned in the `EadaIngestor` docstring before raw promotion. RAW-EAD-012 (P0) is the runtime tripwire for filter misfires." Reinforced in §4 Ingestor notes: "the institution-total marker (column + value) chosen during EDA must be cited verbatim in the `EadaIngestor` docstring." |
| 3 | (A-2) Download mode in §4 Ingestor implementation notes | **RESOLVED** | §4 Ingestor: "Specify in the docstring whether the request returns institution-totals-only (preferred) or all-rows-with-in-pipeline filter; the EADA Custom Data Cutting Tool exposes both modes." |
| 4 | (B-1) Explicit `unitid → long` coercion note | **RESOLVED** | §4 Ingestor: "Coerce `unitid` to `long` at raw write (matching `raw.ipeds_finance.unitid` typing). Preserve any leading zeros if EADA delivers UNITID as a string with quoted/zero-padded values; non-null assertion on every row." |
| 5 | (D-1) §6 EDA item 3 expanded: \|r\| > 0.4 → ≥3 candidate formulas + anchor-validation | **RESOLVED** | §6 EDA Requirements item 3: "if `\|corr(norm_endowment, norm_marketing)\| > 0.4` (Spearman or rank-percentile correlation, EDA's choice), EDA must produce ≥3 candidate composite forms (e.g., weighted-mean as today, `MAX(norm_marketing, norm_endowment)` for either-dimension brand gravity, log-additive composite) and select one via the §6 EDA item 2 anchor-school validation." |
| 6 | (D-2) §6 EDA item 2 explicit pass criterion `aura_score ≥ 8` | **RESOLVED** | §6 EDA Requirements item 2: "**Pass criterion (explicit):** each of the three anchor classes must produce `aura_score ≥ 8`. If any anchor class lands below 8 because the other two signals drag it down, the composite is broken and the formula must be revised." |
| 7 | (D-3) §6 EDA item 4 produces recommendation (not menu) + `aura_score_basis` column added | **RESOLVED** | §6 EDA Requirements item 4: "**EDA must produce a recommendation, not a menu.**" Default recommendation: option (a) drop term + reweight 0.50/0.50, stamp `aura_score_basis = 'two_term_finance_only'`. Options (b) impute 0.5 and (c) NULL aura are rationale-rejected ("EDA should reject this option"). Schema (line 366) adds `aura_score_basis` column with documented semantics `three_term` / `two_term_finance_only` / NULL and explicit cross-stratum comparability rationale. |
| 8 | (D-5) CON-AUR-030 and BSE-EAD-009 marked EDA-calibrated | **RESOLVED** | BSE-EAD-009: "threshold EDA-calibrated against the §4 item 4 overlap measurement; chaos manifest must include a forced UNITID-type-mismatch test against this rule" — also closes prior advisory B-1 chaos hook. CON-AUR-030: "threshold EDA-calibrated; multimodality from `coverage_tier` strata may require relaxing 6/10 or stratifying the rule by `aura_score_basis`." |

##### Spot Verification

- §4 Ingestor notes — download-mode statement present; UNITID-long-coercion note present. Confirmed.
- §4 RAW-EAD-012 P0 post-filter rule — present. Confirmed.
- §4 EDA item 1 BLOCKING + marker-citation — present. Confirmed.
- §5 BSE-EAD-009 EDA-calibrated + chaos-manifest UNITID-mismatch hook — present. Confirmed; this also closes the prior advisory B-1 belt-and-suspenders ask.
- §6 schema `aura_score_basis` — present with `three_term` / `two_term_finance_only` / NULL semantics fully documented. Confirmed.
- §6 CON-AUR-030 EDA-calibrated — present. Confirmed.
- §6 EDA item 2 anchor-class pass criterion `aura_score ≥ 8` — present. Confirmed.
- §6 EDA item 3 |corr| > 0.4 trigger + ≥3 candidate formulas + anchor-validation — present. Confirmed.
- §6 EDA item 4 default recommendation (option a, drop-term + reweight 0.50/0.50) — present; options (b) and (c) explicitly rationale-rejected within the item body. Confirmed.

##### Updated Verdict

- [x] **APPROVED**
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All eight prior blocking items resolved. The aura_score formula remains v0-draft and gated behind the §6 BLOCKING EDA, which is the correct disposition. The four pre-raw blockers are tight enough that §4 implementation cannot proceed past raw-write without the institution-total marker pinned in the `EadaIngestor` docstring and verified by RAW-EAD-012 (P0). The four pre-consumable blockers convert the EDA from a discovery exercise into a prescriptive validation: the default formula path is now stated, the rejection rationale for the alternatives is on the record, and `aura_score_basis` carries cross-stratum comparability forward into downstream consumers.

Suggested (non-blocking, carried forward):
- (B-2) Document FTE-staleness measurement artifact in `governance/eda/full-pipeline-eada-raw-eda.md`.
- (C-1) Optional `institution_name_source` column for cross-source name divergence debuggability.

§4 raw work is cleared to proceed in parallel with `full-pipeline-ipeds-finance.md`. §6 consumable remains gated on the BLOCKING EDA at `governance/eda/consumable-institution-aura-eda.md`.

#### Re-Review After §5 Option-C Amendment
**Status:** CHANGES REQUESTED (non-blocking on silver impl start; must fix before §6 consumable promotion)
**Reviewed:** 2026-04-30
**Review Type:** Pre-Silver-Implementation re-review against the §2 Decision 3 / §3 / §4 / §5 / §6 Option-C amendments

##### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

Silver implementation **may proceed** in parallel with the fixes below — none of the items I'm flagging block the COALESCE expression itself. They block clean §6 consumable promotion.

##### Issues (a) — (f)

**(a) Methodological mix risk in `aura_score`. CHANGES REQUESTED.** The two FTE definitions are not the same number (annualized vs. 12-month headcount), and §6 EDA does not yet stratify the `aura_score` distribution by `athletic_fte_source`. The aura formula uses `rank_pct(athletic_spend_per_fte)`, and 25.5% of rows are now ranked against a denominator with a different shape than the IPEDS-side rows. 2-year colleges (the 25.5%) tend to have lower athletic spend AND lower headcount-FTE than annualized-FTE — the ratio bias direction is not obvious without measurement. **Fix:** Add §6 Aura Score EDA Requirements item 7 — "Stratify the `athletic_spend_per_fte` distribution and the resulting `aura_score` distribution by `athletic_fte_source`. If the median `aura_score` differs by ≥ 1 integer bucket between strata, EDA must either (i) rank-percentile within stratum and recombine, or (ii) drop the athletic term for the eada_eftotalcount stratum (basis = `two_term_finance_only`)." This converts the methodological mix from an implicit assumption into an EDA-validated property.

**(b) `fte_source` value naming. CHANGES REQUESTED (cosmetic).** Real inconsistency: the column is `eada_fte_headcount` but the source-stamp value is `'eada_fte_headcount'`. Pick one. Recommend `'eada_fte_headcount'` to match the column name — the value is a downstream-readable provenance stamp, not a raw EADA column reference. Update §5 transformation SQL, §5 schema row for `fte_source`, BSE-EAD-009 / 011, §6 schema `athletic_fte_source` notes. Five surfaces, all string-replace.

**(c) Re-ingest idempotency vs lineage event. CHANGES REQUESTED.** Idempotent on the *grain* — same UNITID set, same row count, deterministic `record_id`. **Not** idempotent on Iceberg snapshot identity — the new snapshot will have a new ID, and lineage events that referenced snapshot `5935703872733658125` are now dangling. **Fix:** §4 Ingestor notes must require (i) a new lineage event emitted post-re-ingest with the new snapshot ID, (ii) the §8 lineage path entry references the new snapshot, and (iii) the bronze-zone post-impl review is re-issued or amended to cite the new snapshot. The "overwrites the existing snapshot" language in §4 should be qualified: data is overwritten; snapshot ID is replaced; lineage must be re-emitted.

**(d) DQ rule sufficiency. CHANGES REQUESTED.** BSE-EAD-009 (`'none' rate ≤ 1%`) catches the all-NULL `eada_fte_headcount` regression I described — a 25.5% spike in `'none'` would fail loudly. BSE-EAD-011 catches the inverse (~74.5/25.5 distribution drift). BSE-EAD-012 catches the tautology between FTE nullness and `'none'`. **Gap:** none of the three catches a regression where the COALESCE silently picks `eada_eftotalcount` for an institution that *does* have IPEDS-Finance FTE — i.e., the LEFT JOIN silently broken at the UNITID level for some institutions but not others. **Fix:** Add BSE-EAD-013 (P0, Cross-source) — "for every UNITID present in `base.ipeds_finance` with non-null `total_fte_enrollment`, `fte_source = 'ipeds_finance'`. Violation count must be 0." This is the IPEDS-preference invariant; without it, partial join failure looks normal.

**(e) `fte_source` × `aura_score_basis` interaction. CHANGES REQUESTED.** Six (basis, fte_source) combinations, and §6 does not require the EDA to examine them. This is the right hook for the issue (a) concern. **Fix:** Same as (a) — extend §6 EDA item 7 to require the joint `aura_score` distribution be examined across all 6 (basis × fte_source) cells. CON-AUR-030 should be stratified by `athletic_fte_source` in addition to `aura_score_basis`, or the rule note should explicitly cite that multimodality is now expected from a 2-axis stratification.

**(f) Prior CHANGES REQUESTED items applicability.** D-1 (endowment/marketing anti-correlation) is unchanged by Option C — it's a properties-of-IPEDS-Finance question, not an FTE-source question. D-2 (anchor pass criterion) is unchanged. D-3 (`finance_only` basis) is unchanged. D-5 (EDA-calibrated thresholds) is reinforced — BSE-EAD-009/011/012 are correctly flagged as EDA-calibrated. **No prior items are reframed by Option C; all remain in their resolved state.**

##### Guidance for the silver-impl agent

1. Do not start coding until issue (b) is resolved — the value-name churn is cheaper as a spec edit than a code edit.
2. Issue (d)'s BSE-EAD-013 — wire it into `governance/dq-rules/base-eada.json` at silver implementation time; do not defer to post-impl.
3. Issue (c) — emit the new lineage event in the same PR that lands the re-ingest; do not let the lineage corpus drift.
4. Issues (a) and (e) — these are §6 EDA expansions, not silver blockers. Silver impl may proceed; §6 EDA must clear them before consumable promotion.
5. Confirm the re-ingest preserves `bronze.eada` row count at 2,040 (per the bronze post-impl review's spot-checks). A row-count delta would surface a regression unrelated to the EFTotalCount addition.

The Option-C COALESCE is the right call. The 25.5% coverage gap on 2-year colleges was a real CLAUDE.md "no path is out of scope" violation, and Knight Commission's per-FTE benchmarks already use `EFTotalCount` — the methodological-mix concession is well-defended. The remaining work is in the DQ wiring, the value-naming, the lineage hygiene, and an EDA expansion that turns the methodological mix from an assumption into a measured property.

---

#### Post-Implementation Review (Bronze Zone)
**Review Type:** Post-Implementation — Bronze Zone Only
**Date:** 2026-04-30
**Reviewer:** @bs:governance-reviewer

##### §8 Bronze-Zone Artifact Inventory

All 14 bronze-zone artifacts mandated by §8 are present:

| # | Artifact | Path | Status |
|---|---|---|---|
| 1 | EDA | `governance/eda/full-pipeline-eada-raw-eda.md` | PRESENT |
| 2 | DQ rules | `governance/dq-rules/raw-eada.json` (12 rules) | PRESENT |
| 3 | DQ scorecard | `governance/dq-scorecards/raw-eada-20260501T040238Z.{json,md}` | PRESENT — 12/12 PASS |
| 4 | Chaos report | `governance/chaos-reports/raw-eada-chaos.md` (5-cycle + 6 targeted) | PRESENT — 6/6 caught |
| 5 | Adversarial audit | `governance/adversarial-audits/raw-eada-bronze-audit.md` | PRESENT — CLEAR |
| 6 | Lineage | `governance/lineage/full-pipeline-eada-20260501T040238Z.json` | PRESENT (OpenLineage) |
| 7 | CDE tagging | `governance/cde-tagging/raw-eada.md` (3 CDEs, all Public) | PRESENT |
| 8 | Conceptual model | `governance/models/raw-eada-conceptual.md` | PRESENT |
| 9 | Logical model | `governance/models/raw-eada-logical.md` | PRESENT |
| 10 | Physical model | `governance/models/raw-eada-physical.md` | PRESENT |
| 11 | Entity-resolution | `governance/entity-resolution/raw-eada-er-assessment.md` (N/A justification) | PRESENT |
| 12 | PII scan | `governance/pii-scans/raw-eada-pii-scan.md` (NO PII DETECTED) | PRESENT |
| 13 | Temporal model | `governance/temporal-models/raw-eada-temporal-assessment.md` (N/A justification) | PRESENT |
| 14 | Data dictionary | `governance/data-dictionaries/raw-eada.md` | PRESENT |
| + | Glossary | `governance/business-glossary.json` — `BT-EAD-ATHLETIC-SUBSIDY-RATIO` appended (term_id at line 1514) | PRESENT |
| + | Domain context | `governance/domain-context.md` — EADA section (lines 2117–2254) | PRESENT |

##### Cross-Artifact Consistency

Spot-checks all hold:
- **Row count 2,040** — consistent across EDA report, DQ rules `notes`, RAW-EAD-007/008/009 rationales, scorecard, lineage outputFacets, CDE tagging memo, PII scan ("2,040 rows, reporting year 2022"), and physical model.
- **Column names** — `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL` plus lowercase `unitid` / `institution_name` cited identically in EDA, DQ rules JSON, ingestor (per audit-trail), domain-context, CDE tagging memo, and §3 amendment block.
- **Institution-total mental model** — separate-file (`InstLevel.xlsx` vs `Schools.xlsx`, no in-pipeline filter) consistent across §3 amendment, EDA, DQ rules `notes` (RAW-EAD-012 explicitly retained as regression tripwire), domain-context, and CDE tagging memo.
- **3 bronze CDEs** — `unitid`, `total_athletic_expenses`, `total_athletic_revenue`, all Public tier — consistent between CDE tagging memo and PII scan (no PII / Level 1 Public).
- **DQ thresholds 99%** — RAW-EAD-007/008/009 in `raw-eada.json` all set to ≥0.99 with EDA-evidenced rationale; scorecard reports 12/12 PASS against these tightened thresholds.

##### Findings

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | ADVISORY | §4 DQ-rule table at lines 212–214 still reads "≥ 95%" / "≥ 95%" / "≥ 80%" while the executed rules in `raw-eada.json` are 99% / 99% / 99% per EDA recommendation. The §3 EDA-correction blocks document the column-name and file-model amendments but no equivalent block exists in §4 documenting the threshold tightening. **Decision: ADVISORY only, do not block.** The DQ rules JSON is the runtime source of truth, the rule notes carry full traceability back to the spec text and the EDA evidence, and the spec amendment in §3 already establishes the EDA-promoted-thresholds pattern. A footnote-style amendment in §4 ("EDA-promoted to 99% on RAW-EAD-007/008/009 — see `raw-eada.json` rule notes") would be a cosmetic improvement; recommend folding it into the same edit pass that resolves the EFTotalCount question (item 2 below) so we don't churn §4 twice. |
| 2 | CHANGES REQUESTED — silver gate only | The EFTotalCount in-file FTE source vs cross-source IPEDS Finance LEFT JOIN architectural question is captured in `governance/domain-context.md` §EADA (Decision 3, lines ~2225–2240, with full options A/B/C trade-off table and BSE-EAD-009 calibration impact) but is NOT mirrored in the spec. §2 Constraints, §5 Base Zone, §5 Decision 3 placeholder, and the §7 §5 walkthrough all assume the cross-source LEFT JOIN approach. **Recommendation: amend §5 with a short "Open Question — FTE source" subsection citing the domain-context decision matrix and marking the BSE-EAD-009 95% threshold as PROVISIONAL until resolved.** This must happen before any base-zone work begins — base implementation cannot start without this gate cleared. Tracking this only in domain-context risks the same disconnect that prompted the §3 EDA-correction amendment. **Blocking on the silver gate, not on the bronze sign-off.** |
| 3 | ADVISORY | The three open advisory items from the pre-impl review (#4 ingestor column-name lock, CON-AUR-001 inclusion-exclusion tightening, BT-AUR-COVERAGE-TIER refinement) are correctly still in the silver/gold zones for later resolution. No new advisory items are introduced by bronze. |

##### Verdict

- [x] **APPROVED for bronze zone** (silver gated on EFTotalCount question + base.ipeds_finance dependency)
- [ ] CHANGES REQUESTED
- [ ] REJECTED

The bronze zone of `full-pipeline-eada.md` is governance-complete. All 14 mandated artifacts are present, internally consistent, and the row-count / column-name / mental-model corrections from EDA flow cleanly through every downstream artifact. DQ tightening from 95%/80% → 99% is well-justified by the EDA evidence and the rule rationale fields carry the full audit trail. Bronze is signed off.

**Silver-zone gates** (must clear before §5 base implementation begins):
1. EFTotalCount architectural question resolved (option A / B / C from domain-context Decision 3) and reflected back into §5 of the spec.
2. `base.ipeds_finance` available as a join surface (sibling spec dependency).
3. BSE-EAD-009 threshold rebased against the resolved FTE source (likely ~75% if we stay with cross-source LEFT JOIN against `bronze.college_scorecard_institution`).

##### Decision Rationale

The spec author's pattern of pinning EDA findings back into §3 of the spec (column names, file model) worked well — every downstream artifact agrees. The same discipline should be applied to the EFTotalCount question before base work starts; its current location only in domain-context creates a divergence risk identical to the one that the §3 amendments fixed for column names. That said, this is a silver-zone gate, not a bronze-zone gate, so it does not block bronze approval.

The DQ threshold-tightening pattern (rule notes carry full EDA traceability + rationale + original spec quote) is exemplary and should be the template for future EDA-promoted threshold edits.

---

#### Re-Review After §5 Option-C Amendment
**Review Type:** Pre-Silver (re-review of the 2026-04-30 §5 amendment)
**Date:** 2026-04-30
**Reviewer:** @bs:governance-reviewer

##### Verdict
- [x] **APPROVED** — silver implementation may proceed once `base.ipeds_finance` lands and `bronze.eada` is re-ingested with `eada_fte_headcount`.
- [ ] CHANGES REQUESTED
- [ ] REJECTED

This closes the post-impl bronze finding #2 ("EFTotalCount architectural question … must happen before any base-zone work begins"). The Option-C decision is now mirrored back into the spec from `governance/domain-context.md` Decision 3 with the same discipline used for the §3 EDA-correction blocks.

##### Cross-Section Consistency Verified

| Check | Result |
|---|---|
| §2 Decision 3 wording vs §5 Sources line + §5 Base Transformations item 2 SQL | MATCH — both name `COALESCE(base.ipeds_finance.total_fte_enrollment, raw.eada.eada_fte_headcount)` and both stamp identical `fte_source` enum (`'ipeds_finance'` / `'eada_fte_headcount'` / `'none'`). |
| §3 Target Fields adds `EFTotalCount → eada_fte_headcount (double)` | PRESENT (line 161) |
| §4 Raw Schema adds `eada_fte_headcount` row | PRESENT (line 201) |
| §4 Ingestor notes call out the re-ingest requirement on `bronze.eada` | PRESENT (line 188), with idempotency rationale |
| §5 fte_source provenance column | PRESENT (line 298), exhaustive enum |
| §5 has_ipeds_finance_fte / has_eada_fte boolean flags | PRESENT (lines 299–300) |
| §5 BSE-EAD-009 P0 (`fte_source = 'none'` rate ≤ 1%) | PRESENT (line 320), EDA-calibrated |
| §5 BSE-EAD-011 P1 distribution (74.5% / 25.5% ±5pp) | PRESENT (line 322), EDA-calibrated |
| §5 BSE-EAD-012 P0 tautology (NULL FTE ↔ `fte_source = 'none'`) | PRESENT (line 323) |
| §6 Consumable schema adds `athletic_fte_source` pass-through | PRESENT (line 397) |
| §6 schema correctly notes `athletic_fte_source` is NULL when `has_eada = FALSE` | PRESENT (line 397) |
| Old `fte_source_available BOOLEAN` removed from §5 schema | CONFIRMED — replaced by the richer `fte_source` string + two boolean flags |

##### Answers to the Six Re-Review Questions

**a) Internal consistency across §2 / §5 / §6.** PASS. The SQL block in §5 Transformations item 2 is the canonical statement; §2 Decision 3 prose and §6 `athletic_fte_source` schema entry both correctly reference it. The pass-through is "rename only" (`base.eada.fte_source` → `consumable.institution_aura.athletic_fte_source`); the column name is qualified with `athletic_` at consumable because it sits next to non-EADA per-FTE columns there (`endowment_per_fte`, `instruction_per_fte`) which use only `total_fte_enrollment` from `base.ipeds_finance`. Naming disambiguation is correct.

**b) Decision rationale durability.** PASS. §2 Decision 3's Alternatives column captures both rejections cleanly: A rejected on coverage gap (25.5% on 2-year colleges, named cohort: NJCAA / CCCAA / NWAC); B rejected on methodological inconsistency with `endowment_per_fte` (which uses IPEDS Finance FTE, not EADA EFTotalCount). The Knight Commission per-FTE benchmark citation strengthens the C choice. The §5 amendment block (line 249) restates the rejection rationale in narrative form. Future readers will not need to consult `governance/domain-context.md` to understand why C was chosen — the spec is self-contained.

**c) §8 governance artifacts.** No new artifacts required. The existing §8 ledger covers the Option-C surface area:
- Lineage event (line 944) already required to list both `base.ipeds_finance` and `base.eada` as inputs to consumable — the COALESCE inside `base.eada` is captured by the existing `governance/lineage/full-pipeline-eada-{timestamp}.json` event.
- DQ rules at `governance/dq-rules/base-eada.json` already required (line 938) — BSE-EAD-009/011/012 land there.
- `governance/eda/full-pipeline-eada-raw-eda.md` already required (line 931) — the EFTotalCount distribution + IPEDS Finance UNITID overlap percentages live there.
- Domain-context update for the Options A/B/C analysis already required (line 933) and per the post-impl bronze review is already written.

A separate "FTE methodology tradeoff" doc is **not** needed — domain-context Decision 3 + the §2 Alternatives column + the proposed BT-EAD-FTE-SOURCE glossary candidate (see (d) below) cover this. Proliferating governance docs without a forcing function violates the artifact-discipline pattern this project has established.

**d) CDE candidates — `athletic_fte_source`.** **CHANGES REQUESTED — minor.** The §6 Data Contract CDE row currently lists 5 candidates (post the original re-review fix): `aura_score`, `marketing_ratio`, `endowment_per_fte`, `athletic_spend_per_fte`, `athletic_subsidy_ratio`. `athletic_fte_source` is **methodological provenance**, not a substantive financial signal — but it materially affects how analysts interpret the three EADA per-FTE columns (one of which, `athletic_spend_per_fte`, is itself a CDE and an aura input). A row with `athletic_fte_source = 'eada_fte_headcount'` has its `athletic_spend_per_fte` denominator measured on a different basis (12-month headcount) than a row with `athletic_fte_source = 'ipeds_finance'` (annualized FTE). Cross-row comparisons within `athletic_spend_per_fte` therefore depend on this column.

Recommend: add `athletic_fte_source` to the §6 CDE candidate list as a **provenance CDE** (analogous to how `aura_score_version` and `aura_score_basis` are already exposed as cross-stratum-comparability flags — those should also be reviewed by @bs:cde-tagger when the time comes). Final tagging is @bs:cde-tagger's call, but the candidate list should not exclude a methodological flag downstream analysts must condition on. Non-blocking on silver implementation start; must be in place before @bs:cde-tagger runs the consumable pass.

Also recommend a new business glossary candidate **BT-EAD-FTE-SOURCE** for the enum (`ipeds_finance` / `eada_eftotalcount` / `none`) — defines a methodological provenance term that downstream consumers will reference. Steward's call; non-blocking.

**e) Scope discipline.** PASS. The Option-C amendment respects the OUT OF SCOPE block. The required changes are: (1) re-ingest `bronze.eada` with the new `eada_fte_headcount` column — same UNITID grain, same snapshot semantics, idempotent overwrite (§4 line 188 explicitly states this); (2) add three columns to `base.eada` schema; (3) add one pass-through column to `consumable.institution_aura`. No MCP tool, no backend service, no FastAPI router, no frontend wiring, no modification of any other table, no SCD2, no imputation. The §5 SQL block is explicit that schools with no FTE from either source get NULL FTE and consequently NULL per-FTE values ("**No imputation.**" — line 270 and again line 277).

**f) §7 prior reviews.** Leave the historical record intact. The prior post-impl bronze APPROVED was scoped to bronze, not to silver, and its finding #2 explicitly flagged the §5 EFTotalCount question as a silver-zone gate that must clear before base implementation begins — which is precisely what the Option-C amendment now resolves. The prior staff-engineer review (Issue #1) made the same call. Both reviews are correct as-of-their-date; the amendment closes the gates they opened. **Do not retroactively edit prior reviews.** This re-review subsection is the bridge.

##### Issue Summary

| # | Severity | Description | Resolution |
|---|---|---|---|
| 1 | CHANGES REQUESTED — non-blocking on silver start | §6 Data Contract CDE candidate list does not include `athletic_fte_source`. The column is a methodological provenance flag that downstream analysts must condition on when comparing `athletic_spend_per_fte` (itself a CDE) across rows. | Add `athletic_fte_source` to the §6 Data Contract CDE candidates row (will be the 6th). Must be in place before @bs:cde-tagger runs the consumable pass; does not block silver implementation start. |
| 2 | ADVISORY | New business glossary candidate **BT-EAD-FTE-SOURCE** (the enum + its semantic meaning) is not yet listed in §6 Business Glossary Terms. | Steward's call. Non-blocking. |
| 3 | ADVISORY | `aura_score_version` and `aura_score_basis` are also methodological-provenance columns that should be reviewed by @bs:cde-tagger alongside `athletic_fte_source`. They are not currently in the CDE candidate list either. | Surface to @bs:cde-tagger when consumable runs. Non-blocking. |

##### Specific Items for @fp-data-reviewer to Address

1. **BSE-EAD-011 distribution thresholds (74.5% / 25.5% ±5pp)** are based on the EDA-measured IPEDS-Finance UNITID overlap. @fp-data-reviewer should confirm whether the ±5pp band is the right tolerance — particularly whether year-over-year EADA reporting class drift (institutions joining or leaving NCAA/NAIA) could cause natural drift larger than 5pp. If so, the band should widen to ±7-10pp to avoid false alarms in subsequent reporting cycles.

2. **BSE-EAD-012 (NULL FTE ↔ `fte_source = 'none'`)** is a pure tautology of the §5 transformation logic. It is correctly P0, but @fp-data-reviewer should verify there is no degenerate path — e.g., what happens if `eada_fte_headcount = 0` (not NULL)? The §5 per-FTE derivation logic (line 277, "NULL when … `total_fte_enrollment ≤ 0`") would NULL the per-FTE columns but `fte_source` would still be `'eada_fte_headcount'`. Is that the intended semantics, or should `fte_source` be `'none'` whenever the COALESCE result is unusable as a denominator? Worth nailing down before implementation.

3. **`athletic_fte_source` pass-through in §6** — confirm no transformation happens between `base.eada.fte_source` and `consumable.institution_aura.athletic_fte_source`. The §6 schema note says "Pass-through from `base.eada.fte_source`. NULL when `has_eada = FALSE`." That implies the pass-through is conditional on `has_eada`. @fp-data-reviewer should verify whether it should pass through even on FOJ-right-side-only rows (`coverage_tier = 'athletics_only'`) — those rows would have `has_eada = TRUE` so this should be fine, but worth a once-over against the FOJ semantics.

4. **Re-ingest verification** — once `bronze.eada` is re-ingested with `eada_fte_headcount`, RAW-EAD-* DQ should re-run against the new 11-column table. @fp-data-reviewer should confirm whether any RAW-EAD-* rules need adjustment for the new column (likely no — the existing rules are scoped to monetary + identity columns; `eada_fte_headcount` should get its own completeness rule, e.g., `eada_fte_headcount non-null ≥ 99%` per EDA evidence).

5. **`endowment_per_fte` vs `athletic_spend_per_fte` denominator inconsistency.** The Option-C amendment introduces a methodological asymmetry at the consumable: `endowment_per_fte` (from `base.ipeds_finance`) uses only IPEDS Finance FTE, while `athletic_spend_per_fte` (from `base.eada`) uses the COALESCE hybrid. For institutions with `coverage_tier = 'both'` AND `athletic_fte_source = 'eada_fte_headcount'` (the case where `base.ipeds_finance` has the institution but `base.ipeds_finance.total_fte_enrollment` is NULL or zero — rare but possible), the two per-FTE columns are denominated on different bases. @fp-data-reviewer should confirm this is intentional (it is per §2 Decision 3's "single-source consistency" rejection rationale for Option B) and whether a dedicated coverage-tier sub-flag is warranted, or whether `athletic_fte_source` carrying the provenance is sufficient. My read is that the provenance column is sufficient and adding more flags is over-engineering.

##### Decision Rationale

The Option-C amendment is the right call. The 25.5% coverage gap on 2-year colleges (NJCAA / CCCAA / NWAC) is exactly the population for whom Title IX / equity questions about athletic spend are most policy-relevant, and NULL-ing those institutions' per-FTE columns would have silently excluded them from any downstream analysis. The provenance column makes the methodological mix explicit rather than hiding it inside a NULL.

The five-section spec amendment is internally consistent. The BSE-EAD-009 priority promotion (P1 → P0) and the threshold tightening (`coverage ≥ 95%` → `'none' rate ≤ 1%`) reflect that the EDA-evidenced hybrid coverage is ~100%, so the residual NULL rate is now a much sharper signal than the original "did the join work" check. The two new rules (BSE-EAD-011 distribution, BSE-EAD-012 tautology) provide defense in depth.

The single CDE-candidate gap on `athletic_fte_source` is a minor governance-artifact hygiene issue and does not block silver implementation start. Same posture as the original pre-impl review's CDE-candidate gap on `athletic_spend_per_fte` — flag it now, fix it before the cde-tagger pass on consumable.

##### Audit Trail Reference

This re-review is logged under spec-name `full-pipeline-eada` at `governance/audit-trail/full-pipeline-eada-pre-silver-review-2026-04-30.md` (to be written by this agent on review completion).

---

### @bs:staff-engineer
**Status:** APPROVED for bronze (with one required spec amendment before silver kicks off)
**Reviewed:** 2026-04-30
**Review Type:** Final staff-engineer gate — bronze zone only

#### Verdict

Bronze is in good shape. The most dangerous failure mode in this spec — the wrong column names baked into §3 from the original draft — was caught by EDA against live data and propagated cleanly through every downstream artifact. The ingestor, DQ rules, chaos campaign, and adversarial audit all converge on the same EDA-pinned facts. I would put my name on this bronze zone.

One spec amendment is required before silver implementation begins (the §5 EFTotalCount FTE-source question). The 95%/80% → 99% DQ-threshold divergence is acceptable as-is because the rule JSON is runtime source-of-truth and carries its own EDA traceability — but I would still fold a §4 footnote into the same edit pass that resolves §5, so the spec is unambiguous.

#### Independent Spot-Checks Run

I did not take the adversarial-auditor's verification on faith. I re-queried the parquet at `data/bronze/iceberg_warehouse/bronze/eada/data/00000-0-82a082ef-60bf-4b61-aebd-f069e1aa61d2.parquet` directly:

| Claim | Source | Independent Re-Query | Match |
|---|---|---|---|
| 2,040 rows | EDA + scorecard + chaos | `SELECT COUNT(*) FROM eada` → 2040 | YES |
| 2,040 distinct UNITIDs | EDA | `COUNT(DISTINCT unitid)` → 2040 | YES |
| Single `reporting_year=2022` | RAW-EAD-010 | `DISTINCT reporting_year` → {2022} | YES |
| Ohio State $234,409,941 (top expense) | EDA + audit | Top-5 query → Ohio State first @ $234,409,941 | YES (exact) |
| 60 institutions > $100M expense | RAW-EAD-011 | `COUNT(*) WHERE > 1e8` → 60 | YES |
| 363 zero-recruiting rows (17.8%) | EDA + DQ rationale | `COUNT(*) WHERE recruiting_expenses=0` → 363 | YES |
| All three monetary fields 100% non-null | RAW-EAD-007/008/009 evidence | Count-non-null → 2040/2040/2040 | YES |
| MD5 `16948b7cd2801f9ac3513415416e64b7` | Chaos pre/post | Recomputed → identical | YES |

Top 5 by expense (Ohio State, USC, Notre Dame, Michigan, Texas) match the chaos report and the EDA. These are publicly-verifiable D1-FBS anchors; the magnitudes are sane.

I also confirmed the parquet schema is the exact 10-field schema in §4, that `source_method = 'csv_cache'` for every row (the EDA-disclosed cache-first ingest path), and that `EadaIngestor` imports cleanly with the EDA-pinned constants (`INSTITUTION_TOTAL_FILTER_COLUMN=None`, `GRND_TOTAL_EXPENSE/REVENUE`, `RECRUITEXP_TOTAL`, lowercase `unitid`, 2022).

#### Code Quality — `src/raw/eada_ingestor.py`

- `uv run ruff check src/raw/eada_ingestor.py` → All checks passed.
- 600 lines, single-responsibility, no `Any`-soup, no swallowed exceptions. The one `try/except` (in `fetch()`) is well-scoped, logs context, and falls back deliberately to the CSV cache.
- The Ellipsis-as-default-sentinel pattern in `__init__` for the two filter parameters is non-obvious but is the right call — it lets callers explicitly pass `None` to mean "no filter" without colliding with "use class default." It is documented in the docstring with the explicit rationale, which is the WHY-comment standard. Approved.
- Every EDA-pinned constant has an inline citation pointing back to `governance/eda/full-pipeline-eada-raw-eda.md`. Traceability is exemplary.
- `_coerce_long`, `_coerce_double`, `_strip_sentinel` are tight and correct: NaN-handled, `bool`-excluded, leading-zero-string-handled, sentinel-stripped before coercion. The dropped-row pattern for unparseable UNITIDs is logged at WARNING with the offending value, not silently swallowed.
- `ingest()` override correctly captures the post-fetch `source_method` for per-row stamping. The pattern mirrors BEA RPP precedent.

#### Chaos Campaign — Verified

The adversarial-auditor independently re-ran six targeted attacks and got matching results. I read both the chaos report and the audit; the audit re-built attacks from scratch (not invoking the harness) against the rule SQL. MD5 pre/post matches. The harness is read-only by inspection (no write paths). Every published rule fired at least once (no dead rules), and RAW-EAD-012 — the §8-amendment tripwire — fired exactly when the per-team-leak attack landed. I am satisfied without re-running it myself.

The two undetected dimensions (upper-bound reasonableness, freshness on `ingested_at`) are honest disclosures of out-of-rule-set coverage, not test theater. The freshness gap on a cache-first ingestor is a real residual risk and should graduate to P1 once base lands; that recommendation is correctly filed as P2 follow-up.

#### Spec Compliance — Bronze Zone

Spec §3 (post-EDA-correction blocks) and §4 accurately describe what landed:
- §3 column-name correction ✔ matches ingestor and parquet
- §3 file-model correction (separate `InstLevel.xlsx`, no in-pipeline filter) ✔ matches `INSTITUTION_TOTAL_FILTER_COLUMN=None` and the `_is_institution_total()` short-circuit
- §4 schema 10 fields ✔ matches `get_schema()` and parquet `DESCRIBE`
- §4 ingestor implementation notes (UA header, UNITID `long` coercion, sentinel-strip-before-coerce, reporting-year pin from filename) ✔ all implemented and visible in code
- §4 BLOCKING EDA item 1 ✔ resolved (separate-file model documented in EDA + ingestor docstring)
- §4 DQ rule list ✔ all 12 rules implemented, executed, scorecard 12/12 PASS

#### Scope Discipline — VERIFIED CLEAN

Per the spec's OUT OF SCOPE block I checked:
- `grep -n eada src/mcp_server/futureproof_server.py` → zero hits
- `grep -rn 'eada\|aura' backend/app/` → zero substantive hits (only false positives on "machine-readable")
- `grep -rn 'eada\|aura' frontend/src/` → zero substantive hits
- `git status --short | grep eada` → only the `docs/specs/` and `governance/` artifacts, plus `src/raw/eada_ingestor.py`. No MCP, no backend, no frontend.

The unrelated `career-path-enhancements` branch changes that show up in `git status` are pre-existing and orthogonal to this spec.

#### §8 Bronze Artifact Spot-Checks

I verified the four artifacts I most distrust on multi-agent pipelines:

| Artifact | Concern | Verification |
|---|---|---|
| `dq-scorecards/raw-eada-20260501T040238Z.{json,md}` | "12/12 PASS" can be cargo-culted | Rules JSON has 12 rules, governance review enumerates them, chaos campaign exercised all 12 (no dead rules per chaos §5). Match. |
| `chaos-reports/raw-eada-chaos.md` | Harness could silently mis-load | Adversarial-auditor independently rebuilt 6 attacks and matched results. MD5 pinned. |
| `lineage/full-pipeline-eada-20260501T040238Z.json` | OpenLineage events can be skeleton | 215 lines, more than a stub. Governance reviewer confirmed inputs. |
| `pii-scans/raw-eada-pii-scan.md` | Boilerplate "no PII" | 9-row count, 3 CDEs all Public tier, consistent with CDE tagging. EADA carries institution-level monetary aggregates and a UNITID — there is genuinely no PII. Correct conclusion. |

All four hang together with the rest of the corpus.

#### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|--------------|
| 1 | BLOCKING for silver only | `docs/specs/full-pipeline-eada.md` §5 | The §5 base-zone narrative still describes the cross-source IPEDS-Finance LEFT JOIN as the FTE source, but `governance/domain-context.md` Decision 3 now recommends Option C (COALESCE hybrid using EADA's in-file `EFTotalCount` first, falling back to IPEDS Finance). The decision matrix and the resulting BSE-EAD-009 threshold recalibration must be mirrored back into §5 before silver work begins, with the same discipline used for the §3 EDA-correction blocks. Tracking this only in domain-context is exactly the divergence pattern that produced the column-name failure mode in the first place. | Add a §5 "Open Question — FTE source" amendment block citing domain-context Decision 3, mark BSE-EAD-009 95% threshold as PROVISIONAL pending FTE-source resolution. Per @bs:governance-reviewer's silver-gate finding #2. **NOT a bronze blocker.** |
| 2 | ADVISORY | `docs/specs/full-pipeline-eada.md` §4 (lines 212–214) | The §4 DQ rule table still shows the pre-tightening 95%/95%/80% thresholds while `governance/dq-rules/raw-eada.json` ships 99%. The rule JSON is runtime truth and the rule notes document the divergence with EDA citation, so this is genuinely advisory. But the auditor and the post-impl reviewer both flagged it; fold a footnote-style amendment into the same edit pass that resolves issue #1 so §4 doesn't churn twice. | Add a one-line "EDA-promoted to ≥99% on RAW-EAD-007/008/009 — see `raw-eada.json` rule notes" footnote under the §4 DQ table. Cosmetic; not blocking. |
| 3 | ADVISORY | `tests/raw/` | There is no `test_eada_ingestor.py`. Every other ingestor in `tests/raw/` (BEA RPP, BLS OOH, College Scorecard, Karpathy, O*NET, Anthropic Economic Index, Gemma AI Exposure, CIP-SOC) has a unit-test file. The CLAUDE.md "Minimum Test Requirements" table specifies 10 tests for raw zones. The bronze gate has been driven by chaos campaign + adversarial-auditor verification + on-disk parquet spot-checks instead, and the chaos coverage is genuinely thorough — but unit tests for the coercion helpers (`_coerce_long` leading-zero handling, `_strip_sentinel` whitespace handling, `_is_institution_total` short-circuit, NaN/bool exclusion in `_coerce_double`) belong in the test suite as a regression tripwire independent of having the live parquet on disk. **NOT blocking bronze sign-off** because the chaos campaign + independent adversarial verification + my own on-disk re-query collectively exceed what the unit tests would have validated. But this should be filed as a P1 follow-up before silver, because once base joins layer in, the unit-test gap compounds. | File a follow-up to add `tests/raw/test_eada_ingestor.py` with at minimum: 10 tests covering the coercion helpers, the institution-total filter short-circuit, the sentinel-strip-before-coerce ordering, the unparseable-UNITID drop path, and the cache-first vs `bulk_url` fetch dispatch. Schedule before silver merges. |

#### What's Acceptable

The EDA-corrected-the-spec story is the right outcome. The `aura_score_basis` column added during pre-impl re-review is the correct way to handle cross-stratum comparability. Ingestor code is fine — terse, well-commented, no astronaut abstractions. DQ rule rationale fields are the cleanest I've seen on this project.

#### Sign-Off

**APPROVED for bronze.** Silver work is gated by:
1. The §5 EFTotalCount amendment (Issue #1 above) — required before silver kicks off.
2. The existence of `base.ipeds_finance` from the upstream IPEDS Finance spec (sibling-spec dependency, not an EADA-side gate).

Issues #2 (cosmetic §4 footnote) and #3 (missing unit tests) are non-blocking for bronze and should be folded into the silver-prep work. The bronze zone of `full-pipeline-eada.md` is signed off.

---

## §8 Governance Artifacts

- [ ] EDA: `governance/eda/full-pipeline-eada-raw-eda.md` (raw zone of full-pipeline-eada — institution-total filter marker, column verification, distributions, UNITID overlap)
- [ ] EDA: `governance/eda/consumable-institution-aura-eda.md` (aura_score finalization — BLOCKING)
- [ ] Domain context: `governance/domain-context.md` (append EADA + aura section)
- [ ] Models: `governance/models/raw-eada-{conceptual,logical,physical}.md`
- [ ] Models: `governance/models/base-eada-{conceptual,logical,physical}.md`
- [ ] Models: `governance/models/consumable-institution-aura-{conceptual,logical,physical}.md`
- [ ] DQ rules: `governance/dq-rules/raw-eada.json`
- [ ] DQ rules: `governance/dq-rules/base-eada.json`
- [ ] DQ rules: `governance/dq-rules/consumable-institution-aura.json`
- [ ] DQ scorecards under `governance/dq-scorecards/`
- [ ] Chaos report: `governance/chaos-reports/consumable-institution-aura-chaos.md` (focus on FULL OUTER edges, aura_score arithmetic, version-stamping)
- [ ] Chaos report: `governance/chaos-reports/base-eada-chaos.md` (forced UNITID-type-mismatch test against BSE-EAD-009 per §5/§7 fp-data-reviewer Concern B-1)
- [ ] Adversarial audit: `governance/adversarial-audits/consumable-institution-aura.md`
- [ ] Lineage: `governance/lineage/full-pipeline-eada-{timestamp}.json` listing both `base.ipeds_finance` and `base.eada` as inputs to the consumable
- [ ] **Re-ingest lineage event** (added 2026-04-30 with Option-C amendment): when `bronze.eada` is re-ingested to add the `eada_fte_headcount` column required by §5 Decision 3 Option-C, emit a NEW OpenLineage event under `governance/lineage/full-pipeline-eada-{timestamp}.json`. The pre-amendment event at `governance/lineage/full-pipeline-eada-20260501T040238Z.json` references snapshot ID `5935703872733658125` (10-column schema, pre-Option-C) and is preserved as historical record — the new event must reference the new snapshot ID and the 11-column schema. @fp-data-reviewer flagged the dangling-snapshot risk in §7 issue (c); this resolves it with explicit dual-event hygiene.
- [ ] CDE tagging: `governance/cde-tagging/consumable-institution-aura.md`
- [ ] Data contract: `governance/data-contracts/consumable-institution-aura.yaml`
- [ ] Data dictionary updates
- [ ] Business glossary updates: 3 BT-* terms (final IDs assigned by @bs:data-steward)
- [ ] Reviews: `governance/reviews/full-pipeline-eada-pre-review.md`, `governance/reviews/full-pipeline-eada-post-review.md`
- [ ] Approvals: `governance/approvals/full-pipeline-eada-{pre,post,staff}-review.md`

---

## §9 Implementation Log

**Status:** PENDING

### Files Modified

| File | Change Summary |
|---|---|

### Deviations from Spec

| Section | Deviation | Reason |
|---|---|---|

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---|---|---|---|

---

## §10 Discussion

```
[2026-04-30 14:30] @jeff → @primary-agent
Sign convention fix: aura is neutral brand gravity, not institutional efficiency.
Higher marketing, endowment, and athletic spend all push aura UP.
Interpretation of whether brand delivers outcomes belongs to the pentagon shape
(aura vs ERN/ROI), not the score itself. Also downgraded CON-AUR-020 to P1.

Spec changes applied:
  - §2: added Decisions 10 + 11 (neutral signal + input set rationale)
  - §6: flipped marketing direction; swapped athletic_subsidy_ratio for
    athletic_spend_per_fte as the athletic input; athletic_subsidy_ratio
    retained as a context-only passthrough column
  - §6 Aura Score EDA Requirements item 6: locked sign convention,
    confirmation-only check
  - §6 DQ: CON-AUR-020 P0 → P1 with EDA documentation note
  - Business glossary BT-AUR-AURA-SCORE: revised to neutral brand-gravity
```

---

## §11 Final Notes

**Human Review:** PENDING

The `aura_score` is the project's first composite institution-level signal. Lands in the warehouse for inspection — not as a product surface. Any future surfacing (receipts, badges, stretch boss) is a separate, follow-up spec.

---

*— End of Spec —*
