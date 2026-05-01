# Data Dictionary: raw.eada

**Table:** `raw.eada` (physical Iceberg namespace: `bronze.eada`)
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md)
**Ingestor:** [src/raw/eada_ingestor.py](../../src/raw/eada_ingestor.py)
**Conceptual model:** [governance/models/raw-eada-conceptual.md](../models/raw-eada-conceptual.md)
**Logical model:** [governance/models/raw-eada-logical.md](../models/raw-eada-logical.md)
**Physical model:** [governance/models/raw-eada-physical.md](../models/raw-eada-physical.md)
**DQ Rules:** [governance/dq-rules/raw-eada.json](../dq-rules/raw-eada.json) (12 rules)
**DQ Scorecard:** [governance/dq-scorecards/raw-eada-20260501T040238Z.md](../dq-scorecards/raw-eada-20260501T040238Z.md) (12/12 PASS)
**Chaos:** [governance/chaos-reports/raw-eada-chaos.md](../chaos-reports/raw-eada-chaos.md) (6/6 caught)
**Adversarial audit:** [governance/adversarial-audits/raw-eada-bronze-audit.md](../adversarial-audits/raw-eada-bronze-audit.md) (CLEAR)
**PII scan:** [governance/pii-scans/raw-eada-pii-scan.md](../pii-scans/raw-eada-pii-scan.md) (NONE)
**Lineage:** `governance/lineage/full-pipeline-eada-{timestamp}.json` (Bronze run; produced by lineage-tracker)
**Domain Context:** [governance/domain-context.md](../domain-context.md) § EADA Athletics Disclosure
**EDA Report:** [governance/eda/full-pipeline-eada-raw-eda.md](../eda/full-pipeline-eada-raw-eda.md)
**Source:** EADA Athletics Disclosure Survey, U.S. Dept. of Education / Office of Postsecondary Education — `EADA_<YYYY-YYYY>.zip` → `InstLevel.xlsx` (institution-totals)
**Grain:** one row per institution (`unitid`) per academic reporting cycle
**Observed rows:** 2,040 (academic year 2022–23 cycle, `reporting_year=2022`)
**Documented by:** @doc-generator
**Date:** 2026-04-30

---

## What This Table Contains

Institution-level intercollegiate athletics financial disclosures filed under the Equity in Athletics Disclosure Act (§485g of the Higher Education Act). Every U.S. postsecondary institution that operates intercollegiate athletics and receives federal Title IV funds is mandated to file an EADA report each academic year — this Bronze table lands the institution-grand-total row from each reporter.

Three monetary grand totals are carried through Bronze: total athletic expenses, total athletic revenue, and recruiting expenses. The downstream Silver zone (`base.eada`) joins to `base.ipeds_finance` for an FTE denominator and computes per-FTE values plus the `athletic_subsidy_ratio`. The Gold zone (`consumable.institution_aura`) consumes the EADA-side `athletic_spend_per_fte` as one of three direct (non-inverted) inputs to the `aura_score` brand-gravity composite.

**Source file structure:** EADA publishes a per-cycle zip containing both `InstLevel.xlsx` (institution totals — one row per UNITID) and `Schools.xlsx` (per-team rows keyed `(UNITID, SPORTSCODE)`). This Bronze ingest consumes `InstLevel.xlsx` only. The institution-totals file is already one-row-per-UNITID by construction; **no in-pipeline filter is required.**

**Coverage gaps:** UNITID overlap with `bronze.college_scorecard_institution` is 74.5% (1,519/2,040). The 521 missing institutions are concentrated in 2-year community/junior colleges (NJCAA-I/II/III, CCCAA, NWAC, USCAA) — College Scorecard is 4-year-skewed by design. This is expected, not a data quality failure, and downstream `base.eada` LEFT JOINs to `base.ipeds_finance` produce NULL FTE values for these institutions (correct behavior — see spec §5).

**CDE density:** 4 of 10 columns are CDE candidates (40%) — `unitid` (the join key into every IPEDS-keyed downstream), `total_athletic_expenses`, `total_athletic_revenue`, and `recruiting_expenses` (all three feed the downstream `aura_score` and `athletic_subsidy_ratio`, which are spec §6 CDE candidates).

**PII:** None. EADA is institution-level disclosure by design; no individual identifiers are present. Confirmed by `governance/pii-scans/raw-eada-pii-scan.md`.

---

## Field Inventory

### Grain & Identifiers

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `unitid` | `unitid` (lowercase, NOT `UNITID`) | long | Yes | **Yes** | [BT-001](../business-glossary.json) | The 6-digit IPEDS ID that uniquely identifies each institution that filed an EADA report this cycle. This is the only join key linking EADA to `bronze.college_scorecard_institution`, `base.ipeds_finance`, and every downstream consumable. **EDA-observed:** 2,040 distinct values, 0 nulls (100% unique, 100% non-null). The natural key and dedup grain. |
| `institution_name` | `institution_name` (lowercase, NOT `INSTNM`) | string | Yes | No | [BT-002](../business-glossary.json) | The name of the institution as filed with EADA. Display-only — do not use for joins (case, punctuation, and `-Main Campus` suffix conventions vary across IPEDS sources). **EDA-observed:** examples include `Alabama A & M University`, `Ohio State University-Main Campus`. |

### Reporting Cycle

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `reporting_year` | (not in source — pinned by ingestor) | int | Yes | No | (proposed) BT-120 — EADA Reporting Cycle | The academic-year-start of the EADA reporting cycle this row covers. The 2022–23 academic year is stamped as `2022`, matching the `academic_year_start` convention used across `raw.college_scorecard` and IPEDS Finance. EADA does **not** publish an in-row year column — the cycle is encoded only in the source filename (`EADA_2022-2023.zip` → 2022). The ingestor stamps this from `DEFAULT_REPORTING_YEAR` (or a constructor kwarg). RAW-EAD-010 (P0) verifies the value is constant across every row in a load. |

### Monetary Grand Totals

The three institution-grand-total dollar columns published by EADA. All three are USD, all three are non-negative when present, and all three reach the downstream `aura_score` either directly (via `athletic_spend_per_fte`) or as a derivation input (via `athletic_subsidy_ratio` for the EADA-only context column).

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `total_athletic_expenses` | `GRND_TOTAL_EXPENSE` | double | No | **Yes** | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO (this column is one of two inputs) | The institution's total intercollegiate athletics expenses for the cycle, in USD, rolled up across every sport the institution operates. Includes coach salaries, athletic scholarships, operating expenses, recruiting, facilities, travel, equipment, and athletically related student aid. **EDA-observed:** range $11,532 – $234,409,941; p50 $3,452,941; p95 $44,300,839. 60 institutions exceed $100M (D1 power conferences; top: Ohio State, USC, Notre Dame, Michigan, Texas). 100% non-null in the 2022–23 cycle. Drives `base.eada.athletic_spend_per_fte` (the EADA-side aura input) and `athletic_subsidy_ratio`. |
| `total_athletic_revenue` | `GRND_TOTAL_REVENUE` | double | No | **Yes** | (proposed) BT-EAD-ATHLETIC-SUBSIDY-RATIO (this column is the other input) | The institution's total intercollegiate athletics revenue for the cycle, in USD. EADA convention requires institutions to report revenues at least equal to expenses (any deficit is conventionally booked as institutional support), so at the grand-total level revenue ≈ expense for nearly every row. **EDA-observed:** range $11,532 – $261,353,404; p50 $3,577,777; p95 $44,777,300. 100% non-null. The "athletics loses money" insight does **not** appear at the grand-total grain — it lives in the unbundled `direct institutional support` field which we do not currently ingest. Note for Silver: this means BSE-EAD-010 ("`athletic_subsidy_ratio` P50 > 0") will not behave as the spec author imagined; flagged for @bs:dq-rule-writer review. |
| `recruiting_expenses` | `RECRUITEXP_TOTAL` (NOT `RECRUITEXP_TOTAL_TOTAL`) | double | No | **Yes** | — | The institution's total athletic recruiting expenses for the cycle, in USD. Includes travel, lodging, meals, and other costs incurred by coaches recruiting prospective student-athletes. **EDA-observed:** range $0 – $7,455,849; p50 $28,298; p95 $878,902. **17.8% of institutions report exactly $0** (363/2,040) — these are real reported zeros (mostly NJCAA II/III, CCCAA, NWAC, NCCAA programs that do not recruit off-campus), not suppressions. RAW-EAD-006 (`≥ 0`) is the right rule — never add a `> 0` rule for this field. Drives `base.eada.recruiting_per_fte`. |

### Pipeline Provenance

Every row carries pipeline-stamped provenance. These fields are required at the Iceberg level and identical across all rows in a single batch.

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `source_url` | (derived) | string | Yes | No | — | Provenance URL recording where this row was downloaded from. Constant per batch — currently `https://ope.ed.gov/athletics/` (the EADA Custom Data landing page). The actual fetch path goes through the SPA backend at `/api/dataFiles/file?fileName=EADA_<YYYY-YYYY>.zip` (discovered during EDA), but the human-facing landing page is what we record for lineage-friendly attribution. Unauthenticated public URL — no secrets-hygiene concern. |
| `source_method` | (derived) | string | Yes | No | — | Literal string identifying the ingest path used. Current value `csv_cache` — the ingestor reads a pre-converted `InstLevel.xlsx` → CSV at `data/raw/eada_cache/eada_<year>.csv`. Switches to `bulk_csv_download` when the SPA-API refresh path is invoked via the ingestor's `bulk_url` kwarg. |
| `ingested_at` | (derived) | timestamp | Yes | No | — | UTC wall-clock recording when the Bronze ingest run wrote this row. Identical across all rows in a single batch — acts as a batch identifier, not a per-row event time. |
| `load_date` | (derived) | date | Yes | No | — | Calendar date of the load run, in UTC. Used by the freshness DQ guardrail. Identical across all rows in a single batch. |

---

## Data Quality Rules

The 12 DQ rules covering this table are defined in [governance/dq-rules/raw-eada.json](../dq-rules/raw-eada.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|----------------|
| RAW-EAD-001 | P0 | (row count) | Row count between 1,800 and 2,300 (observed: 2,040). |
| RAW-EAD-002 | P0 | `unitid` | Non-null in every row. |
| RAW-EAD-003 | P0 | `unitid` | Uniqueness (dedup grain). |
| RAW-EAD-004 | P0 | `total_athletic_expenses` | `≥ 0` where non-null. |
| RAW-EAD-005 | P0 | `total_athletic_revenue` | `≥ 0` where non-null. |
| RAW-EAD-006 | P0 | `recruiting_expenses` | `≥ 0` where non-null (zeros are valid). |
| RAW-EAD-007 | P0 | `total_athletic_expenses` | Non-null `≥ 99%` (EDA-tightened from spec's 95%). |
| RAW-EAD-008 | P0 | `total_athletic_revenue` | Non-null `≥ 99%` (EDA-tightened from spec's 95%). |
| RAW-EAD-009 | P1 | `recruiting_expenses` | Non-null `≥ 99%` (EDA-tightened from spec's 80%). |
| RAW-EAD-010 | P0 | `reporting_year` | Single value across all rows in a load. |
| RAW-EAD-011 | P1 | `total_athletic_expenses` | At least one row exceeds $100M (D1 anchor; observed: 60 rows). |
| RAW-EAD-012 | P0 | `unitid`, row count | `|row_count − distinct(unitid)| ≤ max(1, 1% of distinct unitid)` (per-team-leak tripwire). |

All 12 rules PASS as of 2026-05-01T04:02:38Z (`governance/dq-scorecards/raw-eada-20260501T040238Z.md`). Adversarial chaos and audit cleared with 6/6 detections.

---

## Caveats for Consumers

1. **`unitid` is lowercase in the EADA source.** The original spec working draft assumed `UNITID`; EDA confirmed 2026-04-30 that EADA actually publishes `unitid`. The ingestor handles the case difference. Downstream readers see the consistent lowercase column.

2. **`reporting_year` is pinned by the ingestor, not present in the source.** EADA does not publish a year column in `InstLevel.xlsx` — the cycle is encoded in the filename only. Downstream consumers can rely on the value being correct (RAW-EAD-010 P0 enforces it), but be aware that loading a wrongly-named cache file would silently mis-stamp the year. The ingestor reads `DEFAULT_REPORTING_YEAR=2022` for the 2022–23 cycle.

3. **Revenue ≈ Expense at the grand-total level.** EADA convention requires reported revenues to be at least equal to expenses; deficits are booked as institutional support (a separate column we do **not** ingest). The grand-total `athletic_subsidy_ratio` derived at Silver will therefore be near zero everywhere. The "athletics loses money" insight needs the unbundled `direct_institutional_support` field — out of scope for this Bronze ingest. Flag for any future spec amendment that wants the subsidy signal to behave intuitively.

4. **`recruiting_expenses == $0` is a real value.** 17.8% of institutions report a true zero. Do **not** add a `> 0` rule. The current RAW-EAD-006 (`≥ 0`) is correct.

5. **Suppression sentinels (blank / `-1` / `-2`) are scrubbed to NULL before type coercion.** EDA observed zero sentinel hits in the 2022–23 institution-totals file (sentinels are a per-sport phenomenon in `Schools.xlsx`, which we do not ingest). The pre-coercion scrub remains for safety against future cycle drift.

6. **74.5% UNITID overlap with `bronze.college_scorecard_institution`.** 521 institutions (25.5%) are absent from College Scorecard, almost entirely 2-year colleges. The Silver `base.eada` LEFT JOIN to `base.ipeds_finance` will produce NULL FTE for these institutions, which propagates to NULL per-FTE derivations and (per spec §6) NULL `aura_score` — correct behavior, not a DQ failure. The BSE-EAD-009 cross-source threshold downstream is calibrated against this overlap, not against 100%.

7. **Field IDs 1–10 are stable.** Future schema evolution (e.g., adding `EFTotalCount`, `classification_name`, or per-sport coach counts) must allocate IDs ≥ 11 and never rebind 1–10. Standard Iceberg-evolution discipline.

8. **`bronze.eada` and `raw.eada` are the same physical table.** The spec uses the logical name `raw.eada`; the Iceberg catalog writes to `bronze.eada` (sibling-convention). DQ SQL and downstream reads use `bronze.eada`.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-30 | Initial data dictionary for Bronze table `raw.eada`. 10 fields documented (3 identity + 3 monetary + 4 provenance), 4 flagged CDE, 0 flagged PII. EDA-confirmed column names and constants pinned. | @doc-generator |
