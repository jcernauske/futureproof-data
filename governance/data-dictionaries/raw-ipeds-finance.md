# Data Dictionary: raw.ipeds_finance

**Table:** `raw.ipeds_finance` (physical Iceberg namespace: `bronze.ipeds_finance`)
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md)
**Ingestor:** [src/raw/ipeds_finance_ingestor.py](../../src/raw/ipeds_finance_ingestor.py)
**Conceptual model:** [governance/models/raw-ipeds-finance-conceptual.md](../models/raw-ipeds-finance-conceptual.md)
**Logical model:** [governance/models/raw-ipeds-finance-logical.md](../models/raw-ipeds-finance-logical.md)
**Physical model:** [governance/models/raw-ipeds-finance-physical.md](../models/raw-ipeds-finance-physical.md)
**DQ Rules:** [governance/dq-rules/raw-ipeds-finance.json](../dq-rules/raw-ipeds-finance.json) (14 rules)
**DQ Scorecard:** [governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.md](../dq-scorecards/raw-ipeds-finance-20260501T202737Z.md) (14/14 PASS)
**Chaos:** [governance/chaos-reports/raw-ipeds-finance-chaos.md](../chaos-reports/raw-ipeds-finance-chaos.md)
**Lineage:** `governance/lineage/full-pipeline-ipeds-finance-{timestamp}.json` (Bronze run; produced by lineage-tracker)
**Domain Context:** [governance/domain-context.md](../domain-context.md) § IPEDS Finance Survey
**EDA Report:** [governance/eda/full-pipeline-ipeds-finance-raw-eda.md](../eda/full-pipeline-ipeds-finance-raw-eda.md)
**Source:** IPEDS Finance Survey (F1A / F2 / F3) + EFIA (12-Month Instructional Activity) + HD (Header), NCES / U.S. Dept. of Education
**Grain:** one row per institution (`unitid`) per fiscal cycle
**Observed rows:** 2,675 (FY23 cycle, `fiscal_year=2023`, post-filter `ICLEVEL=1 AND HLOFFER>=5`)
**Documented by:** @doc-generator
**Date:** 2026-04-30

---

## What This Table Contains

Institution-level financial disclosures from the IPEDS Finance Survey, joined at ingest time with the IPEDS EFIA (12-Month Instructional Activity) survey for the FTE denominator and the IPEDS HD (Header) survey for institution name and the 4-year bachelor's-or-above filter. Every U.S. postsecondary institution that grants a bachelor's degree or higher and reports to IPEDS files exactly one Finance survey per fiscal year, on exactly one of three accounting forms — F1A (public, GASB), F2 (private nonprofit, FASB), or F3 (private for-profit). This Bronze table lands the institution-totals row from each reporter.

Three monetary fields are carried through Bronze: instruction expenses (the educational product), institutional support expenses (administration / fundraising / executive direction — the "marketing and overhead" signal), and endowment value end-of-year. Plus the EFIA-sourced `total_fte_enrollment` denominator. The downstream Silver zone (`base.ipeds_finance`) computes per-FTE values plus `marketing_ratio` (institutional support ÷ instruction). The Gold zone (`consumable.ipeds_finance_profile`) adds a `data_completeness_tier` and exposes raw-dollar passthroughs for the downstream EADA fusion (`consumable.institution_aura` in the separate spec `full-pipeline-eada.md`).

**Source file structure:** IPEDS publishes three parallel finance forms per cycle:

- `F{YY}{YY}_F1A.zip` — public institutions (GASB).
- `F{YY}{YY}_F2.zip` — private nonprofit institutions (FASB).
- `F{YY}{YY}_F3.zip` — private for-profit institutions.

This Bronze ingest UNIONs all three with a `report_form` tag, then LEFT JOINs `EFIA{YYYY}.csv` for the FTE denominator and `HD{YYYY}.csv` for institution name + the 4-year filter. **Five files in, one Bronze table out.**

**Form mix (FY23):** F1A 30.6% (819) / F2 59.0% (1,579) / F3 10.4% (277) = 2,675 total. Public 4-year institutions are larger than private nonprofits at the median (FTE 5,461 vs 1,047); for-profits are smaller still (FTE 504) and dominated by online or single-campus operators.

**Coverage:** UNITID overlap with `bronze.college_scorecard_institution` is **98.0%** (2,621 / 2,675). The 54 missing institutions are mostly small religious or specialty institutions that opted out of Title IV reporting (or have suppressed Scorecard rows). The 418 Scorecard-only UNITIDs are predominantly 2-year and certificate-granting institutions correctly excluded by the `ICLEVEL = 1 AND HLOFFER >= 5` filter. This 98% overlap calibrates the downstream cross-source coverage threshold to ≥97% — a notably tighter coupling than EADA (74.5% overlap), reflecting that IPEDS Finance is comprehensive in 4-year coverage by federal mandate.

**CDE density:** 5 of 12 columns are CDE candidates (42%) — `unitid` (the join key), and the four analytical fields (`institutional_support_expenses`, `instruction_expenses`, `endowment_value`, `total_fte_enrollment`). All four feed downstream per-FTE rates, the `marketing_ratio` (a spec §6 CDE candidate at consumable), and the `aura_score` composite in the downstream EADA fusion spec.

**PII:** None. IPEDS Finance is institution-level reporting by design; no individual identifiers are present.

---

## Field Inventory

### Grain & Identifiers

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `unitid` | Finance form `UNITID` | long | Yes | **Yes** | [BT-001](../business-glossary.json) | The 6-digit IPEDS ID that uniquely identifies each institution that filed an IPEDS Finance survey on F1A, F2, or F3 this cycle. This is the universal join key linking IPEDS Finance to `bronze.college_scorecard_institution`, `bronze.eada`, `consumable.career_outcomes`, and every downstream institution-keyed table in the pipeline. **EDA-observed:** 2,675 distinct values, 0 nulls (100% unique, 100% non-null). The natural key and dedup grain. |
| `institution_name` | HD `INSTNM` (joined on UNITID at ingest from `HD2023.csv`) | string | Yes | No | [BT-002](../business-glossary.json) | The official name of the institution as published in the IPEDS HD (Header) survey. Display-only — do not use for joins (case, punctuation, and `-Main Campus` suffix conventions vary across IPEDS sources). **EDA-observed:** examples include `University of California, Berkeley`, `Stanford University`, `Indiana University-Bloomington`. |

### Reporting Form & Cycle

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `report_form` | (stamped by ingestor) | string | Yes | No | (proposed) BT-IPF-ACCOUNTING-FORM | The IPEDS Finance form the institution filed on. Three values: `F1A` (public, GASB — Governmental Accounting Standards Board basis), `F2` (private nonprofit, FASB — Financial Accounting Standards Board basis), or `F3` (private for-profit). Drives column-code coalescing at ingest (the four target fields use different column codes on each form) and segments downstream analysis (e.g., GASB-vs-FASB-vs-for-profit comparison of institutional support intensity). **EDA-observed:** F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%). Validated by RAW-IPF-004 (P0). |
| `fiscal_year` | (not in source — pinned by ingestor) | int | Yes | No | (proposed) BT-IPF-FISCAL-CYCLE | The IPEDS fiscal year this row covers. The FY23 cycle (academic year 2022–23, fiscal year ending June 30 2023) is stamped as `2023`, matching the IPEDS publication convention and the academic-year-end convention used elsewhere in the pipeline (College Scorecard, EADA). IPEDS does **not** publish an in-row year column — the cycle is encoded only in the source ZIP filename (`F2223_F1A.zip` → fiscal_year 2023). The ingestor stamps this from `DEFAULT_FISCAL_YEAR=2023` (or a constructor kwarg). **NCES has not yet released FY24** as of 2026-04-30 (HTTP 404 on F2324 ZIPs); current promote target is FY23. RAW-IPF-013 (P0) verifies the value is constant across every row in a load. |

### Monetary Fields (Institution Totals)

The three institution-totals dollar columns published by IPEDS Finance. All three are USD, all three are non-negative when present, and all three reach downstream consumers via per-FTE derivations (`institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`) plus the `marketing_ratio` (institutional support ÷ instruction). Column codes differ across the three forms; the ingestor coalesces them into the canonical raw columns below.

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `institutional_support_expenses` | F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1` | double | No | **Yes** | (proposed) BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES | The institution's total annual expenses for executive management, fiscal operations, public relations, fundraising, legal services, administrative computing, and similar administrative functions. The IPEDS dictionary definition (FARM ¶703.9) is byte-equivalent across all three forms. Often a proxy for "marketing and administration overhead" in budget-transparency analyses — at for-profits (F3) it routinely exceeds instruction spending, the marketing-heavy signal `marketing_ratio` is designed to surface. **F3 column locked v1.3:** `F3E03C1` is the post-2014-15 schedule (the pre-v1.3 hypothesis that F3 omits institutional support was wrong — F3 reports it 100%). **EDA-observed (FY23):** range $0 – $1,228,381,000; p50 $9,419,560; p95 $106,263,601. 100% non-null. 17 rows at $0 (mostly F2 single-campus seminaries — real reported zeros, not suppressions). Drives `base.ipeds_finance.institutional_support_per_fte` and the numerator of `marketing_ratio`. |
| `instruction_expenses` | F1A `F1C011` / F2 `F2E011` / F3 `F3E011` | double | No | **Yes** | (proposed) BT-IPF-INSTRUCTION-EXPENSES | The institution's total annual expenses for the colleges, schools, departments, and other instructional divisions of the institution — including faculty salaries, instructional materials, departmental research, and public service that is not separately budgeted. The IPEDS dictionary definition (FARM ¶703.1) is byte-equivalent across all three forms. The denominator of `marketing_ratio`. **F3 column locked v1.3:** `F3E011` (the `1` suffix denotes "Total amount"; provisional `F3E01` was wrong — would have referenced the wrong subtotal column). **F1A column corrected v1.1:** Part C functional expenses (`F1C011`), NOT Part B revenues (`F1B01` — would have silently mis-labeled revenue values as expenses). **EDA-observed (FY23):** range $0 – $3,504,073,000; p50 $15,220,174; p95 $274,546,660; p99 $995,734,601. Top-of-distribution: Stanford $2.68B, UC Berkeley $1.00B, IU-Bloomington $762M, UNC-CH $561M. 269 institutions exceed $100M (R1 anchors). 5 rows at $0 (small F2/F3 institutions booking teaching costs under academic support — real reported zeros, allowed by RAW-IPF-005). 100% non-null. |
| `endowment_value` | F1A `F1H02` / F2 `F2H02` / F3 N/A (no `F3H` family) | double | No | **Yes** | (proposed) BT-IPF-ENDOWMENT-VALUE | The end-of-year market value of the institution's endowment funds. Reported on F1A and F2 only — for-profit institutions (F3) do not maintain endowments by design and have no `F3H` family on their finance schedule. **EDA-observed (FY23):** range $0 – $50,748,594,000 (Stanford); p50 $45,960,441; p95 $1,399,290,059; p99 $8,353,458,662. 76.0% non-null overall (2,033 / 2,675). **NULL composition:** 277 F3 rows (100% structural NULL — no `F3H` family) + ~253 small F2 institutions (~16% of F2) that do not maintain endowments. Per IPEDS reporting, underwater funds report `0`, never negative — RAW-IPF-007 enforces `≥ 0` where non-null. The 128 rows with `endowment_value = $0` (where non-null) are real reported values, not suppressions. Drives `base.ipeds_finance.endowment_per_fte`; F3 endowment NULL cascades correctly to NULL `endowment_per_fte` on F3 rows. |

### Enrollment Denominator

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `total_fte_enrollment` | EFIA `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` (computed at ingest) | double | No | **Yes** | (proposed) BT-IPF-PER-FTE (the convention; this column is the denominator) | The institution's 12-month total full-time-equivalent (FTE) enrollment for the fiscal cycle, sourced from the IPEDS EFIA (12-Month Instructional Activity) survey. Computed as the NULL-safe sum of three EFIA component columns: `FTEUG` (undergraduate FTE) + `FTEGD` (graduate FTE) + `FTEDPP` (doctor's-professional-practice FTE). NULL only when all three components are NULL. **Critical taxonomy clarification:** the source file is **EFIA** (12-Month Instructional Activity), NOT EFFY (which is unduplicated 12-month *headcount*, broken out by `EFFYALEV` and at the wrong grain — would inflate per-FTE rates if used) and NOT EF Part A `EFTOTLT` (which is fall-snapshot headcount, not 12-month FTE — would systematically deflate per-FTE rates for institutions with large part-time populations). EFIA publishes one row per UNITID — no dedup filter is required (verified 5,959/5,959 unique on EFIA2023). Uses *reported* FTE columns (`FTEUG`/`FTEGD`/`FTEDPP`); per the IPEDS dictionary, reported FTE defaults to NCES *estimated* FTE (`EFTEUG`/`EFTEGD`) when the institution did not provide a reported figure, so reported values preserve institution-confirmed FTE where given and fall back to NCES's estimate elsewhere. **EDA-observed (FY23):** range 6 – 135,698; p50 1,514; p95 21,975; non-null 97.94% (2,620 / 2,675). The 55 NULL rows are UNITIDs in the finance forms but absent from EFIA2023 (newly-opened in FY23 or late filers). Min FTE=6 is SUNY Empire State College (UNITID 196097, FY23 transition year, mostly online graduate students — verified plausible). Drives every per-FTE derivation downstream. RAW-IPF-008 enforces `> 0` where non-null (no zero-FTE institution can exist in EFIA). |

### Pipeline Provenance

Every row carries pipeline-stamped provenance. These fields are required at the Iceberg level and identical across all rows in a single batch. This Bronze ingest fans out across **five source files** (3 finance forms + EFIA + HD), so the `source_url` column is a pipe-delimited list reflecting that fan-out.

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `source_url` | (derived) | string | Yes | No | — | Provenance — pipe-delimited list of all 5 source URLs the row was assembled from: F1A, F2, and F3 finance ZIPs + EFIA ZIP + HD ZIP, all from `https://nces.ed.gov/ipeds/datacenter/data/`. Constant per batch. Unauthenticated public URLs — no secrets-hygiene concern. (Cosmetic flag from EDA §10: the ingestor docstring at line ~919 says "list of all 4 files" but the implementation correctly emits 5 entries — docstring fix only, not a schema issue.) |
| `source_method` | (derived) | string | Yes | No | — | Literal string identifying the ingest path used. Current value `bulk_csv_download` — the ingestor downloads each ZIP, unzips, reads the CSV in chunks (50,000 rows per CLAUDE.md rule), coalesces form-specific columns, joins EFIA + HD on UNITID, applies the 4-year filter, scrubs sentinels, and coerces types. ZIPs are cached at `data/raw/ipeds_finance_cache/` for re-runs. |
| `ingested_at` | (derived) | timestamp | Yes | No | — | UTC wall-clock recording when the Bronze ingest run wrote this row. Identical across all rows in a single batch — acts as a batch identifier, not a per-row event time. |
| `load_date` | (derived) | date | Yes | No | — | Calendar date of the load run, in UTC. Used by the freshness DQ guardrail. Identical across all rows in a single batch. |

---

## Data Quality Rules

The 14 DQ rules covering this table are defined in [governance/dq-rules/raw-ipeds-finance.json](../dq-rules/raw-ipeds-finance.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|----------------|
| RAW-IPF-001 | P0 | (row count) | Row count between 2,500 and 3,200 (observed: 2,675). Recalibrated from spec-as-written 5,000–8,000 per EDA §0 gate 6 — the original band predated the `ICLEVEL=1 AND HLOFFER>=5` HD-filter narrowing. |
| RAW-IPF-002 | P0 | `unitid` | Non-null in every row (observed: 100%). |
| RAW-IPF-003 | P0 | `unitid` | Uniqueness within fiscal_year (dedup grain; observed: 100%). |
| RAW-IPF-004 | P0 | `report_form` | Domain ∈ {`F1A`, `F2`, `F3`}. |
| RAW-IPF-005 | P0 | `instruction_expenses` | `≥ 0` where non-null. |
| RAW-IPF-006 | P0 | `institutional_support_expenses` | `≥ 0` where non-null. |
| RAW-IPF-007 | P0 | `endowment_value` | `≥ 0` where non-null (the "where non-null" wording is critical — F3's 277 structural NULLs must not trip this rule). |
| RAW-IPF-008 | P0 | `total_fte_enrollment` | `> 0` where non-null (no 0-FTE institution can exist in EFIA). |
| RAW-IPF-009 | P0 | `instruction_expenses` | Non-null `≥ 90%` (observed 100.0%). |
| RAW-IPF-010 | P0 | `institutional_support_expenses` | Non-null `≥ 90%` (observed 100.0%; refutes the pre-v1.3 hypothesis that F3 omitted this field). |
| RAW-IPF-011 | P0 | `total_fte_enrollment` | Non-null `≥ 95%` (observed 97.94%; flag if below 96%). |
| RAW-IPF-012 | P1 | `endowment_value` | Non-null `≥ 60%` (observed 76.0%; the floor is intentionally below the F3 + F2-small-private structural-NULL floor). |
| RAW-IPF-013 | P0 | `fiscal_year` | Single value across all rows in a load (single-vintage invariant). |
| RAW-IPF-014 | P1 | `instruction_expenses` | At least one row exceeds $100M (R1 anchor; observed: 269 rows). |

All 14 rules PASS as of 2026-05-01T20:27:37Z (`governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.md`). Adversarial chaos cleared (`governance/chaos-reports/raw-ipeds-finance-chaos.md`).

---

## Caveats for Consumers

1. **The FTE source is `EFIA`, not `EFFY` and not `EFTOTLT`.** This is the single most load-bearing taxonomy clarification in the whole spec:
   - **`EFIA{YYYY}`** — 12-Month Instructional Activity. **Carries FTE.** One row per UNITID. *This is the right source.*
   - **`EFFY{YYYY}`** — 12-Month Unduplicated *Headcount*. *Wrong grain* (broken out by `EFFYALEV`). Joining naïvely fans out finance rows.
   - **EF Part A `EFTOTLT`** — Fall-snapshot *headcount*. *Wrong concept* (headcount, not FTE; fall snapshot, not 12-month).

   The spec went through three revisions (v1.0 → v1.1 → v1.3) refining this. Downstream consumers should never re-derive `total_fte_enrollment` from any other IPEDS source — always use the column as supplied here.

2. **`fiscal_year` is pinned by the ingestor, not present in the source.** IPEDS Finance does not publish a fiscal-year column in the F1A / F2 / F3 CSVs — the cycle is encoded in the ZIP filename only. Downstream consumers can rely on the value being correct (RAW-IPF-013 P0 enforces it), but be aware that loading a wrongly-named cache file would silently mis-stamp the year. Current operative cycle is `fiscal_year=2023` (FY23); FY24 is not yet released by NCES as of 2026-04-30.

3. **F3 endowment is structurally NULL — not missing data.** For-profit institutions have no `F3H` family on their finance schedule (no endowment exists to report). 100% of F3 rows have NULL `endowment_value` by design. RAW-IPF-007 is correctly written `where non-null` so it does not trip on the 277 F3 rows. Downstream `endowment_per_fte` cascades to NULL on F3 rows — correct behavior, not a DQ failure.

4. **F3 institutional support IS reported — refutes pre-v1.3 hypothesis.** Earlier spec drafts assumed F3 omitted institutional support (true pre-2014-15). The post-2014-15 schedule revision added `F3E03C1`, which IPEDS now requires from for-profits. EDA observed 100% non-null on F3 institutional support (277/277). This means `marketing_ratio` is computable for essentially all F3 rows, and the marketing-heavy signal (F3 median `marketing_ratio` ~1.06) shows up as expected.

5. **F1A column codes were corrected v1.1 — Part C, not Part B.** The original spec used `F1B01` / `F1B07`, which point at Part B (revenues), not Part C (functional expenses). The corrected codes are `F1C011` / `F1C071`. Downstream consumers reading from this Bronze table can rely on the corrected codes; the silent-corruption window closed before any data was promoted.

6. **Bureau-imputed values are accepted as raw.** Per spec §2 Decision #8, NCES bureau-imputed values are accepted and the parallel `X*`-prefixed flag columns are not stored. EDA Req 7 measured prevalence ≤1.22% on every analytical field — well-calibrated; the policy should not flip in v1.3. If a future cycle shows imputation jumping above ~5% on any field, revisit (and consider adding flag columns at field IDs ≥ 13).

7. **Suppression sentinels (`-1`, `-2`, `.`, blank, `"PrivacySuppressed"`) are scrubbed to NULL before type coercion.** EDA observed zero sentinel hits in the FY23 institution-totals fields (sentinels are predominantly a per-program / per-race-ethnicity phenomenon at IPEDS; institution totals are essentially always populated when the institution reports). The pre-coercion scrub remains as a safety net against future cycle drift.

8. **The 4-year filter (`ICLEVEL = 1 AND HLOFFER >= 5`) is applied at ingest.** Spec v1.0 used `PREDDEG = 3 OR ICLEVEL = 1`, which mixed College Scorecard and IPEDS taxonomies. v1.1 corrected to the IPEDS-native form. The filter narrows 6,163 IPEDS UNITIDs to 2,864, which after joining to the finance forms produces 2,675 surviving rows. 2-year and certificate-only institutions are out of scope for this Bronze table by design; downstream consumers needing a wider population must source elsewhere.

9. **98% UNITID overlap with `bronze.college_scorecard_institution`.** Notably tighter than EADA's 74.5% overlap. The 54 finance-only UNITIDs are mostly small religious or specialty institutions that opted out of Title IV reporting; the 418 Scorecard-only UNITIDs are 2-year/certificate institutions correctly excluded by the 4-year filter. The downstream silver-zone cross-source coverage threshold should be calibrated to ≥97% (NOT the ≥95% the EADA EDA suggested).

10. **The `total_fte_enrollment` column is computed at Bronze, not Silver.** It is the one Bronze-zone "computation" that is not strictly a passthrough — a NULL-safe sum across three EFIA component columns (`FTEUG + FTEGD + FTEDPP`). This is upstream-of-derivation: every per-FTE rate downstream depends on it, and we do not land EFIA as its own Bronze table. Downstream consumers should treat this column as authoritative.

11. **Field IDs 1–12 are stable.** Future schema evolution (e.g., adding HD-derived columns like `SECTOR` / `CONTROL`, or adding imputation-flag columns if NCES imputation prevalence rises) must allocate IDs ≥ 13 and never rebind 1–12. Standard Iceberg-evolution discipline.

12. **`bronze.ipeds_finance` and `raw.ipeds_finance` are the same physical table.** The spec uses the logical name `raw.ipeds_finance`; the Iceberg catalog writes to `bronze.ipeds_finance` (sibling-convention with `bronze.eada`, `bronze.college_scorecard_institution`, etc.). DQ SQL and downstream reads use `bronze.ipeds_finance`.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-30 | Initial data dictionary for Bronze table `raw.ipeds_finance`. 12 fields documented (4 identity + 3 monetary + 1 enrollment + 4 provenance), 5 flagged CDE, 0 flagged PII. EDA-confirmed column codes pinned (F3 instruction `F3E011`, F3 institutional support `F3E03C1`, EFIA NULL-safe three-column FTE sum). | @doc-generator |
