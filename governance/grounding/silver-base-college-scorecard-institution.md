# Grounding Document: base.college_scorecard_institution

**Table:** `base.college_scorecard_institution`
**Zone:** Silver (Base)
**Grain:** one row per institution (`unitid`)
**Source:** `raw.college_scorecard_institution` (Bronze — U.S. Department of Education College Scorecard)
**Date Range:** single snapshot (inherited from Bronze; no within-source temporal dimension)
**Record Count:** 3,039 institutions (1:1 with Bronze)
**Data Quality:** 17/17 rules passing — 11 P0, 5 P1, 1 P2
**Sensitivity:** Public (U.S. Government Work, no PII)
**Spec:** [docs/specs/raw-ingest-college-scorecard-institution.md](../../docs/specs/raw-ingest-college-scorecard-institution.md)
**Contract:** [governance/data-contracts/silver-base-college-scorecard-institution.yaml](../data-contracts/silver-base-college-scorecard-institution.yaml)
**Dictionary:** [governance/data-dictionaries/silver-base-college-scorecard-institution.md](../data-dictionaries/silver-base-college-scorecard-institution.md)
**Lineage:** [governance/lineage/silver-base-college-scorecard-institution-20260414T220000Z.json](../lineage/silver-base-college-scorecard-institution-20260414T220000Z.json)
**Parent grounding (Bronze):** [raw-college-scorecard-institution.md](raw-college-scorecard-institution.md)

---

## Purpose

This Silver table is the **unified cost-side reference data** that powers the new FutureProof ROI formula. Its single job is to hide the public-vs-private column-pair zigzag of the raw College Scorecard CSV and give the Gold zone one authoritative column per business concept.

### What Silver solved

The Bronze table (`raw.college_scorecard_institution`) stores the same concept twice: once in a `_pub` column (populated only when `control = 1`) and once in a `_priv` column (populated only when `control` is 2 or 3). That shape is a faithful reflection of the source CSV, but it is hostile to Gold queries — every ROI computation would have to encode a `CASE WHEN control = 1 THEN npt4_pub ELSE npt4_priv END` in-line, and the same pattern for each of the five income quintiles.

Silver collapses the nine pairs into nine unified columns:

| Silver column | Replaces Bronze pair | Routed by |
|---------------|----------------------|-----------|
| `cost_of_attendance_annual` | `costt4_a` / `costt4_p` (COALESCE — not control-routed) | source reporting type |
| `net_price_annual` | `npt4_pub` / `npt4_priv` | `institution_control` |
| `net_price_q1` | `npt41_pub` / `npt41_priv` | `institution_control` |
| `net_price_q2` | `npt42_pub` / `npt42_priv` | `institution_control` |
| `net_price_q3` | `npt43_pub` / `npt43_priv` | `institution_control` |
| `net_price_q4` | `npt44_pub` / `npt44_priv` | `institution_control` |
| `net_price_q5` | `npt45_pub` / `npt45_priv` | `institution_control` |
| `cost_of_attendance_4yr` | derived (annual × 4) | null-propagating |
| `net_price_4yr` | derived (annual × 4) | null-propagating |

`institution_control` itself is also a Silver derivation: the Bronze integer `control` (1/2/3) becomes the human-readable string `'Public'` / `'Private nonprofit'` / `'Private for-profit'`.

### Business context: the new ROI formula

This table is the denominator input for:

```
ROI = earnings / (net_price_annual × 4 × loan_pct)
```

Before this Silver table existed, the Gold ROI proxy was `earnings / debt_median` — what past graduates borrowed, which is a behavior, not a price. The new formula uses what the school actually charges, net of the grants and scholarships the average student receives, over a four-year degree, pro-rated by the fraction of students who take out loans. Every ROI number, every Fight Student Loans boss outcome, and every "Public university · $12,800 net price/yr" CareerCard label traces through `net_price_annual` on this table.

### Why also keep the raw columns (`*_raw`)?

Twelve raw Bronze columns are passed through verbatim as provenance (`costt4_a_raw`, `costt4_p_raw`, `npt4_pub_raw`, `npt4_priv_raw`, and the 10 quintile raw copies). They do not feed any downstream calculation. They exist so a regulator or auditor asking *"show me every CDE value for UNITID 166027"* sees both the derived unified value and the raw input it came from on a single row scan, without having to federate back to Bronze. This is the same audit-reconstruction pattern the sibling BEA RPP Silver contract applies to `rpp_all_items`.

---

## How It Relates to Other Tables

### Upstream: `raw.college_scorecard_institution` (Bronze)

Silver is a **1:1 promote** of Bronze. No filtering, no aggregation, no cross-source joins. Every Bronze row produces exactly one Silver row; every Bronze `unitid` appears in Silver with the same value. The row-count DQ rule SLV-CSI-001 enforces exactly 3,039 rows ± 5.

```
raw.college_scorecard_institution (Bronze, 3,039 rows)
  │
  │  1:1 promote
  │  + COALESCE cost-of-attendance
  │  + control-routed net-price unification
  │  + × 4 pre-materialization
  │  + control integer → string mapping
  ▼
base.college_scorecard_institution (Silver, 3,039 rows)
```

### Downstream: `consumable.career_outcomes` (Gold)

The Gold program-grain table gains the following enrichment columns via LEFT JOIN on `unitid`:

| Gold enrichment column | Source in this Silver table | Purpose |
|------------------------|------------------------------|---------|
| `net_price_annual` | `net_price_annual` | **ROI denominator input** |
| `net_price_4yr` | `net_price_4yr` | ROI formula direct input |
| `cost_of_attendance_annual` | `cost_of_attendance_annual` | Sticker-price receipt line |
| `institution_control` | `institution_control` | "Public" / "Private nonprofit" / "Private for-profit" label |
| `tuition_in_state` | `tuition_in_state` | Receipt breakdown |
| `tuition_out_of_state` | `tuition_out_of_state` | Receipt breakdown |
| `room_board_on_campus` | `room_board_on_campus` | Receipt breakdown |

The existing `debt_median` column on `consumable.career_outcomes` stays — demoted from ROI driver to reference field ("the median grad from this program borrowed $X").

### Downstream: `consumable.program_career_paths` (Gold)

This is THE CORE table for the FutureProof product (626K rows, school + major → career with all stats and bosses). It inherits the Silver cost fields indirectly via `consumable.career_outcomes`.

### Not a Join: BEA Regional Price Parities

This table does **not** join to `consumable.regional_price_parities`. The RPP adjustment is keyed on the **student-selected destination state** (where they plan to work), not the institution's home state. A student attending University of Iowa but planning to work in California gets a California RPP adjustment, not an Iowa one. `state_abbr` on this table is therefore a display/filter field, not a cross-source join key. (Tripwire for future re-evaluation: if a spec adds an "adjust institution COA by local cost of living" feature, re-flag `state_abbr` as CDE at that time.)

---

## Key Metrics

| Metric | Value | CDE? | DQ Status | Notes |
|--------|-------|------|-----------|-------|
| Institutions covered | 3,039 | — | SLV-CSI-001 PASS | 1:1 with Bronze. |
| Institutions with `net_price_annual` populated | 2,233 (73.48%) | **Yes** | SLV-CSI-010 PASS (floor 70%) | Row-identical in nullness with COA. |
| Institutions with `cost_of_attendance_annual` populated | 2,233 (73.48%) | **Yes** | SLV-CSI-011 PASS (floor 70%) | Same 2,233 rows as net_price. |
| Public schools | 867 (28.53%) | — | — | 89.27% have `net_price_annual`. |
| Private nonprofit schools | 1,754 (57.72%) | — | — | 70.64% have `net_price_annual`. |
| Private for-profit schools | 418 (13.75%) | — | — | 52.63% have `net_price_annual` — known IPEDS underreporting. |
| Schools with negative `net_price_annual` | 3 (Skyline, San Diego Mesa, St Petersburg) | **Yes** | SLV-CSI-016 PASS | Aid exceeds COA — legitimate. |
| `net_price_annual` range | −$1,180 to $77,180 (median $18,990) | **Yes** | SLV-CSI-016 PASS | Validator: [−$5,000, $80,000]. |
| `cost_of_attendance_annual` range | $6,362 to $87,804 (median $30,354) | **Yes** | SLV-CSI-017 PASS | Validator: [$5,000, $100,000]. |
| `net_price_annual <= cost_of_attendance_annual` | 100% of 2,233 rows with both populated | **Yes (invariant)** | SLV-CSI-007 PASS | 0 violations. |
| `net_price_4yr = net_price_annual × 4` (within $0.01) | 100% of 2,233 rows | **Yes (invariant)** | SLV-CSI-008 PASS | IEEE-754 exact. |
| `cost_of_attendance_4yr = cost_of_attendance_annual × 4` (within $0.01) | 100% of 2,233 rows | **Yes (invariant)** | SLV-CSI-009 PASS | IEEE-754 exact. |
| Quintile coverage | q1 71.90% → q5 60.74% | **Yes** | SLV-CSI-015 PASS | Coverage degrades with income (source-side suppression). |
| Rows with `net_price_q1 > net_price_q5` | 46 of 1,832 rows with both populated (2.51%) | — | SLV-CSI-015 PASS (tolerance 50) | Legitimate — aid caps + merit aid. |

---

## Lineage

This document describes data generated by `CollegeScorecardInstitutionTransformer` in [src/silver/college_scorecard_institution_transformer.py](../../src/silver/college_scorecard_institution_transformer.py). Full column-level transformations from Bronze to Silver are recorded in [governance/lineage/silver-base-college-scorecard-institution-20260414T220000Z.json](../lineage/silver-base-college-scorecard-institution-20260414T220000Z.json) in OpenLineage format.

Transformation summary:
- **12 derived columns** (record_id, institution_control, cost_of_attendance_annual, cost_of_attendance_4yr, net_price_annual, net_price_4yr, net_price_q1–q5, ingested_at)
- **23 pass-through columns** (unitid, institution_name, state_abbr, 2 tuition, 3 room/board/books, 14 raw provenance, source_load_date)
- **0 joined columns** (Silver is a 1:1 promote — no cross-source enrichment at this layer)

All derivations are **deterministic**: re-running the transform against the same Bronze snapshot produces byte-identical Silver output. No fuzzy matching, no entity resolution, no imputation.

---

## Confidence Notes (for AI consumers)

An AI consuming this data should weight its answers against the following caveats:

### 1. The control multiplexing has already been done — do not re-route

At Bronze, a net price question required the chain "read `control`, branch on it, pick `npt4_pub` or `npt4_priv`, handle the null cases." At Silver, `net_price_annual` already IS the right value for every row. Reading `npt4_pub_raw` / `npt4_priv_raw` and re-branching would reproduce work and risk inconsistency. The raw columns exist for audit reconstruction, not for re-derivation.

**For grounded answers:** when discussing a school's net price, cite `net_price_annual` directly. Optionally also cite `institution_control` so the user knows which population the number reflects.

### 2. Coverage is 73.48%, not 100% — and the two cost fields are row-identical

806 institutions (26.52%) have null `net_price_annual` **and** null `cost_of_attendance_annual`. The EDA confirmed Key Finding #1: the two fields are row-identical in nullness — no school reports one without the other. These are concentrated in `PREDDEG=0` (unclassified, 288 schools) and `PREDDEG=4` (graduate-dominant, 280 schools) that entered the scope via the `ICLEVEL=1` branch of the Bronze filter.

**For grounded answers:** if a student asks about a specific school and `cost_of_attendance_annual` is null, say so explicitly — "the Department of Education doesn't publish a cost-of-attendance figure for [school] in this snapshot." Don't try to estimate from tuition alone; tuition is only a component of COA.

### 3. Negative net prices are real — do not clip

Three community colleges have genuinely negative `net_price_annual` — Skyline College (−$1,180), San Diego Mesa (−$904), St Petersburg (−$52) — because the average student's grant and scholarship aid exceeds their cost of attendance. The range validator (SLV-CSI-016) allows down to −$5,000 for this reason. Private quintile-level values can also go negative (MIT Q1 at −$4,129 is a famous example).

**For grounded answers:** if asked "what does Skyline College cost the average student?" the honest answer includes "the average student receives more aid than the cost — net price is about −$1,180, meaning aid exceeds what they charge."

### 4. Adjacent quintiles are not monotonic — only the full span is

Do not assume `net_price_q1 <= net_price_q2 <= net_price_q3 <= net_price_q4 <= net_price_q5`. The EDA found that 37.9% of private institutions legitimately invert at the Q1 → Q2 boundary, because merit-aid programs targeted at lower-middle-income students (Q2) can outweigh need-based aid for lowest-income students (Q1). The DQ pack enforces **only** the full-span invariant `q1 <= q5`, and even that allows up to 50 legitimate violations (SLV-CSI-015). 46 such violations exist in the current snapshot — all genuine, with magnitudes median $1,396.

**For grounded answers:** never describe the quintile series as "always ascending." Use phrasing like "net price generally decreases for lower-income families, though merit aid can complicate the middle brackets."

### 5. Quintile coverage degrades as income rises

Population: q1 71.90%, q2 69.30%, q3 68.41%, q4 65.19%, q5 60.74%. The high-income quintile samples are smaller at most schools and are suppressed by the source more often. Income-quintile ROI answers must accept per-quintile nulls.

**For grounded answers:** if asked about the q5 net price for a specific school and it's null, that is not a data bug — it means the source suppressed that cell due to small sample size. Fall back to `net_price_annual` (the population-wide average) in that case.

### 6. For-profit data is thin

`institution_control = 'Private for-profit'` has only 52.63% `net_price_annual` coverage. This is a known IPEDS underreporting pattern, tracked at P2 informational only (SLV-CSI-014). Many for-profit-school programs will have null cost data after the Gold LEFT JOIN.

**For grounded answers:** hedge confidence on for-profit schools. If cost data is missing for a for-profit program, note "the Department of Education doesn't publish cost figures for many for-profit schools, so this ROI is based on debt patterns alone" rather than inventing a number.

### 7. `institution_control` drives public/private framing — surface it on receipts

Unlike Bronze's integer `control`, Silver's `institution_control` is ready for display: `'Public'`, `'Private nonprofit'`, `'Private for-profit'`. CHECK-constrained to those three values with zero tolerance. The CareerCard uses it directly for labels like "Public university · $12,800 net price/yr."

**For grounded answers:** when citing a net price, always pair it with the control type — a $25K net price means something different at a public university (high, unusual) than at a private nonprofit (low, unusual).

### 8. 4-year totals are pre-materialized — don't multiply again

`net_price_4yr` is already `net_price_annual × 4`, and `cost_of_attendance_4yr` is already `cost_of_attendance_annual × 4`. They exist as stored columns so the Gold ROI query doesn't have to multiply in the hot path. IEEE-754 exactness is enforced (SLV-CSI-008, SLV-CSI-009, $0.01 tolerance).

**For grounded answers:** if asked "what does four years cost at [school]?" use `net_price_4yr` or `cost_of_attendance_4yr` directly. Do not recompute — the stored value is exact and pre-validated.

### 9. This is a snapshot, not a time series

Silver inherits Bronze's vintage unchanged. There is no within-source temporal dimension — no field distinguishes 2023 data from 2024 data. Refresh cadence is annual (each fall when the Department of Education publishes the next Most-Recent-Cohorts file), and each refresh replaces the table entirely.

**For grounded answers:** don't make claims about year-over-year cost trends from this table alone.

### 10. Tuition is NOT the ROI denominator

`tuition_in_state` / `tuition_out_of_state` are **tuition only** — no housing, meals, books, or living expenses, and not net of aid. Everything you'd expect in "cost of attendance" is already rolled into `cost_of_attendance_annual`; the aid adjustment is in `net_price_annual`. The ROI formula uses `net_price_annual`, not tuition.

**For grounded answers:** if tempted to quote "in-state tuition is $12,000" as the cost of attending, the honest figure is `cost_of_attendance_annual` (usually 2×–3× larger) or, better, `net_price_annual` (which nets grants off the full COA).

### 11. `state_abbr` is NOT a cross-source join key

The institution's home-state abbreviation is for display and filtering only. The BEA purchasing-power overlay is keyed on the student-selected destination state, not the school's state. A tripwire is documented in the CDE registry for re-evaluation if a future spec joins institution `state_abbr` directly to `bea_rpp`, but no such spec exists today.

**For grounded answers:** do not combine `state_abbr` with purchasing-power figures to claim anything about what it costs to live while attending the school.

---

## Glossary Terms Referenced

| Term ID | Name | Definition |
|---------|------|-----------|
| [BT-001](../business-glossary.json) | Institution | A college or university identified by its IPEDS UNITID. |
| [BT-110](../business-glossary.json) | Cost of Attendance (COA) | Total annual cost including tuition, fees, books, room & board, and living expenses. The "sticker price" before aid. |
| [BT-111](../business-glossary.json) | Net Price | Average annual cost after grants and scholarships. What the student actually pays. The ROI denominator input. |
| [BT-112](../business-glossary.json) | Net Price by Income Quintile | Net price broken out by five family-income brackets (Q1=$0–30K through Q5=$110K+). |

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-14 | Initial grounding document for Silver table `base.college_scorecard_institution`. 35 fields (23 CDE, 0 PII), 17 DQ rules, 2,233 rows with ROI-critical cost data populated, 806 rows deliberately null (source coverage gap). | @doc-generator |
