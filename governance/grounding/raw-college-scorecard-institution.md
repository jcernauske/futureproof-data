# Grounding Document: raw.college_scorecard_institution

**Table:** `raw.college_scorecard_institution`
**Zone:** Bronze (Raw)
**Grain:** one row per institution (`unitid`)
**Source:** U.S. Department of Education College Scorecard — `Most-Recent-Cohorts-Institution.csv`
**Date Range:** single snapshot (most recent cohort data available at download time)
**Record Count:** 3,039 institutions (after filter `PREDDEG=3 OR ICLEVEL=1`)
**Data Quality:** 13/13 rules passing — 7 P0, 6 P1, 0 P2
**Sensitivity:** Public (U.S. Government Work, no PII)
**Spec:** [docs/specs/raw-ingest-college-scorecard-institution.md](../../docs/specs/raw-ingest-college-scorecard-institution.md)
**Contract:** [governance/data-contracts/raw-college-scorecard-institution.yaml](../data-contracts/raw-college-scorecard-institution.yaml)
**Dictionary:** [governance/data-dictionaries/raw-college-scorecard-institution.md](../data-dictionaries/raw-college-scorecard-institution.md)
**Lineage:** [governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json](../lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json)

---

## Purpose

This table is the cost-side reference data for every U.S. college and university FutureProof knows about. It answers a single question for each institution: **what does it cost a student to go here, after financial aid?**

Before this table existed, FutureProof could tell students "graduates of this program earned $X one year out" and "the median student borrowed $Y" — but those are the outcome and the historical borrowing pattern. Neither tells the student what they will actually have to pay. This table closes that gap by providing:

- **Cost of attendance** — the "sticker price" for one year (tuition + fees + books + room & board + living expenses)
- **Net price** — what the average student really pays after grants and scholarships
- **Net price by family income** — the same figure broken down into five income brackets, because a low-income student at a high-endowment private school may pay less than a middle-income student at a state school

The table is the denominator for the rewritten ROI formula:

```
ROI = earnings / (net_price_annual × 4 × loan_pct)
```

Where previously it was `earnings / debt_median` (what past grads borrowed — a proxy, not a price).

---

## How It Relates to Existing Tables

### Primary Join: raw.college_scorecard (program-level earnings/debt)

Both tables come from the same source (U.S. Department of Education College Scorecard) and share the same join key: `unitid` (the 6-digit IPEDS institutional identifier).

```
raw.college_scorecard_institution (this table)
  unitid, control, cost_of_attendance, net_price, tuition, room & board
    │
    │  JOIN ON unitid
    ▼
raw.college_scorecard (existing)
  unitid, cipcode, credlev, earnings, debt, program name
```

The difference is grain:
- `raw.college_scorecard` — one row per **institution × program × credential** (69,947 rows, ~2,559 institutions)
- `raw.college_scorecard_institution` (this table) — one row per **institution** (3,039 rows)

**Join coverage:** 91.9% — 2,352 of 2,559 program-level UNITIDs find a match here. The remaining 207 (8.1%) are institutions that report program-level outcomes but were excluded from this table by the `PREDDEG=3 OR ICLEVEL=1` filter, or didn't report institutional cost data to IPEDS. These will get null cost fields after the Gold LEFT JOIN — expected, not a DQ failure.

### Downstream: consumable.career_outcomes (Gold zone)

The Gold table `consumable.career_outcomes` gains the following enrichment columns via LEFT JOIN on `unitid`:

| Enrichment Column | Source | Purpose |
|-------------------|--------|---------|
| `net_price_annual` | Silver unified from `npt4_pub`/`npt4_priv` | **ROI denominator input** |
| `cost_of_attendance_annual` | Silver `COALESCE(costt4_a, costt4_p)` | Sticker-price receipt line |
| `net_price_4yr` | `net_price_annual × 4` | 4-year total net cost |
| `institution_control` | Silver string-mapped from `control` | "Public" / "Private nonprofit" / "Private for-profit" label |
| `tuition_in_state` | `tuitionfee_in` pass-through | Receipt breakdown |
| `tuition_out_of_state` | `tuitionfee_out` pass-through | Receipt breakdown |
| `room_board_on_campus` | `roomboard_on` pass-through | Receipt breakdown |

`debt_median` stays on `consumable.career_outcomes` — it's demoted from ROI driver to reference field ("the median grad from this program borrowed $X").

### Not a Join: BEA Regional Price Parities

This table does **not** join to `consumable.regional_price_parities`. The BEA data joins at a different layer — at the student-selected state, not the institution's state — so `stabbr` here is display-only and not a cross-source join key.

---

## Key Metrics

| Metric | Value | CDE? | DQ Status | Notes |
|--------|-------|------|-----------|-------|
| Institutions covered | 3,039 | — | RAW-CSI-001 PASS | Bachelor's-granting or 4-year schools. |
| Institutions with COA (sticker price) | 2,233 (73.5%) | **Yes** (costt4_a/p) | RAW-CSI-010 PASS | 806 institutions have no COA figure. |
| Institutions with net price (any) | 2,013 (66.2%) | **Yes** (npt4_pub/priv) | RAW-CSI-011, 012 PASS | Combined `npt4_pub`/`npt4_priv` coverage. |
| Public schools | 867 (28.5%) | — | — | 89.3% have `npt4_pub`. |
| Private nonprofit schools | 1,754 (57.7%) | — | — | 70.6% have `npt4_priv`. |
| Private for-profit schools | 418 (13.8%) | — | — | 52.6% have `npt4_priv` — known IPEDS underreporting. |
| Schools with negative net price | 3 public + 5 private quintile-level | — | RAW-CSI-006, 007 PASS (allow neg) | Aid exceeds COA — legitimate. |
| Observed COA range | $6,362 – $87,804 (median $30,288) | **Yes** | RAW-CSI-005 PASS | Wider in private institutions. |
| Observed public net price range | -$1,180 – $32,598 | **Yes** | RAW-CSI-006 PASS | Min is Skyline College. |
| Observed private net price range | $1,525 – $77,180 | **Yes** | RAW-CSI-007 PASS | Max near the upper tail of elite privates. |

---

## Lineage

This document describes data generated by the `CollegeScorecardInstitutionIngestor` in [src/raw/college_scorecard_institution_ingestor.py](../../src/raw/college_scorecard_institution_ingestor.py). Full column-level transformations from source CSV to Iceberg table are recorded in [governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json](../lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json) in OpenLineage format.

All fields are sourced directly from the College Scorecard CSV (`transformationType: DIRECT`) with only type coercion (string → long/int/double) and sentinel normalization (`PrivacySuppressed`, `PS`, `NA`, `NULL`, empty → null). Pipeline metadata fields (`ingested_at`, `source_url`, `source_method`, `load_date`) are `transformationType: DERIVED`, framework-generated at ingest time.

---

## Confidence Notes (for AI consumers)

An AI consuming this data should weight its answers against the following known caveats:

### 1. CONTROL determines which net price column to read — never mix them

The institution-level file stores separate net price columns for public (`npt4_pub`) and private (`npt4_priv`) schools, and Silver zone uses `control` as a multiplexer:
- `control = 1` → read `npt4_pub`
- `control IN (2, 3)` → read `npt4_priv`

If you see non-null `npt4_pub` on a row with `control = 2`, it is a data bug — not a valid reading. The EDA verified zero cross-contamination across all 3,039 rows.

**For grounded answers:** when discussing a specific school's net price, always confirm which `control` value applies before citing a figure.

### 2. Negative net prices are legitimate — do not clip to $0

Three public institutions (San Diego Mesa College at -$904, Skyline College at -$1,180, St Petersburg College at -$52) and five private quintile-level values (including MIT's Q1 at -$4,129) report negative net prices. This happens when the average student's grant and scholarship aid exceeds their total cost of attendance. Clipping to $0 hides legitimate institutional generosity.

**For grounded answers:** if asked "what does MIT cost a low-income student?" the honest answer includes "the average Q1 student receives more aid than the cost — net price is about -$4,000."

### 3. Adjacent quintiles are not monotonic — only the full span is

Do not assume that net price strictly increases with income quintile. EDA found:
- Full-span (Q1 ≤ Q5): 98.2% of private, 99.0% of public schools satisfy this
- Adjacent (Q1 ≤ Q2 ≤ Q3 ≤ Q4 ≤ Q5): **only 62.1% of private schools satisfy this**

The 37.9% of private schools where Q1 > Q2 reflects a real pattern: merit aid targeted at lower-middle-income students (Q2) can outweigh need-based aid for lowest-income students (Q1). This is a data feature, not a data error.

**For grounded answers:** never describe the quintile series as "always ascending." Use phrasing like "generally lower net price for lower-income families, though merit aid can complicate the middle."

### 4. COA coverage is 73.5%, not 100%

26.5% of institutions have no cost of attendance figure at all. These are concentrated in `PREDDEG=0` (unclassified — 288 schools) and `PREDDEG=4` (graduate-dominant — 280 schools) that are included in this table because `ICLEVEL=1` admits them even though they're not primarily bachelor's-granting.

**For grounded answers:** if a student asks about a specific school and `cost_of_attendance_annual` is null, say so explicitly — "the Department of Education doesn't publish a cost-of-attendance figure for [school], so ROI is computed from the median debt instead."

### 5. For-profit data is thin

For-profit institutions (`control=3`) have only 52.6% net-price coverage and 44.3% COA coverage. This is expected — for-profits underreport to IPEDS. Downstream, ROI for for-profit-school programs is frequently null after the Gold LEFT JOIN.

**For grounded answers:** when discussing for-profit schools, hedge confidence accordingly. A for-profit program without cost data in the Gold table is not unusual.

### 6. Tuition is NOT the ROI denominator

A common confusion: `tuitionfee_in` and `tuitionfee_out` are **tuition only**. They do not include housing, meals, books, or living expenses — all of which are in `costt4_a/p`. And they are not net of aid — `npt4_pub/priv` is. The ROI formula uses `net_price_annual`, not tuition.

**For grounded answers:** if tempted to quote "in-state tuition is $12,000" as the cost of attending, the honest figure is `cost_of_attendance_annual` (which is usually 2×–3× larger) or `net_price_annual` (which nets grants off it).

### 7. This is a snapshot, not a time series

The table contains one row per institution reflecting the most recent cohort data available at download time. There is no within-source temporal dimension — no field distinguishes 2023 data from 2024 data. Refresh cadence is annual (each fall when the Department of Education publishes the next Most-Recent-Cohorts file).

**For grounded answers:** don't make claims about year-over-year cost trends from this table alone.

### 8. Schools without on-campus housing have null roomboard_on — that's normal

43.4% of institutions have null `roomboard_on` — commuter schools, online-only programs, schools without dormitories. Not a DQ failure. `roomboard_off` or the unified COA figure is still available for these institutions.

---

## Glossary Terms Referenced

| Term ID | Name | Definition |
|---------|------|-----------|
| [BT-110](../business-glossary.json) | Cost of Attendance (COA) | Total annual cost including tuition, fees, books, room & board, and living expenses. The "sticker price" before aid. |
| [BT-111](../business-glossary.json) | Net Price | Average annual cost after grants and scholarships. What the student actually pays. |
| [BT-112](../business-glossary.json) | Net Price by Income Quintile | Net price broken out by five family-income brackets (Q1=$0–30K through Q5=$110K+). |

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-14 | Initial grounding document for Bronze table `raw.college_scorecard_institution`. | @doc-generator |
