# Data Dictionary: raw.college_scorecard_institution

**Table:** `raw.college_scorecard_institution`
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/raw-ingest-college-scorecard-institution.md](../../docs/specs/raw-ingest-college-scorecard-institution.md)
**Ingestor:** [src/raw/college_scorecard_institution_ingestor.py](../../src/raw/college_scorecard_institution_ingestor.py)
**CDE Registry:** [governance/cde-registry/raw-ingest-college-scorecard-institution-cdes.md](../cde-registry/raw-ingest-college-scorecard-institution-cdes.md)
**DQ Rules:** [governance/dq-rules/raw-ingest-college-scorecard-institution.json](../dq-rules/raw-ingest-college-scorecard-institution.json)
**Lineage:** [governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json](../lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json)
**Domain Context:** [domain/raw-ingest-college-scorecard-institution-context.md](../../domain/raw-ingest-college-scorecard-institution-context.md)
**Source:** U.S. Department of Education College Scorecard, `Most-Recent-Cohorts-Institution.csv`
**Grain:** one row per institution (`unitid`)
**Observed rows:** 3,039 (after filter `PREDDEG=3 OR ICLEVEL=1`)
**Documented by:** @doc-generator
**Date:** 2026-04-14

---

## What This Table Contains

Institution-level cost data for U.S. colleges and universities — what a school charges (cost of attendance), what students actually pay after grants and scholarships (net price), and how net price varies by family income. This is the **cost-side** partner to the program-level `raw.college_scorecard` table (earnings and debt). Together they let FutureProof compute a student-honest ROI: `earnings / (net_price × 4 × loan_pct)` instead of the older proxy `earnings / debt_median`.

The two tables join on `unitid`. 91.9% of program-level UNITIDs find a match here; the remaining 8.1% are either outside the 4-year bachelor's-granting filter or didn't report institutional cost data.

**CDE density:** 17 of 28 columns are flagged CDE (60.7%) — unusually high because this ingest was scoped specifically to fields that drive the ROI formula or the receipt breakdown.

**PII:** None. All fields are institution-level aggregates from a public federal dataset. No individual student data is present.

---

## Field Inventory

### Grain & Identifiers

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `unitid` | `UNITID` | long | Yes | **Yes** | — | The 6-digit IPEDS ID that uniquely identifies each college or university. This is the only join key linking this table to the program-level earnings data (`raw.college_scorecard`) and to the Gold table `consumable.career_outcomes`. Every institution appears exactly once. |
| `instnm` | `INSTNM` | string | Yes | No | — | The name of the institution as reported to IPEDS. Display-only — do not use for joins, because 10 institution names map to multiple UNITIDs (multi-campus systems). |
| `stabbr` | `STABBR` | string | Yes | No | — | The 2-letter U.S. state or territory code where the institution is located. Used for filters and display, not for joins into the rest of the pipeline. |

### Scope / Routing Fields

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `control` | `CONTROL` | int | Yes | **Yes** | — | Who runs the school. `1` = Public (state-funded), `2` = Private nonprofit, `3` = Private for-profit. This single field is a switch: Silver zone uses it to decide whether to read `npt4_pub` or `npt4_priv` (and the analogous quintile columns). If `control` is wrong for a given school, every ROI number for that school will be computed from the wrong column. |
| `preddeg` | `PREDDEG` | int | Yes | **Yes** | — | The predominant degree the school awards. `3` = Bachelor's is the primary target for this ingest. Rows must satisfy `PREDDEG=3 OR ICLEVEL=1` (4-year institution), so the filtered set is all bachelor's-granting schools plus 4-year schools that predominantly award something else (certificates, associate's, or graduate degrees). |

### Cost of Attendance (BT-110)

The "sticker price" — what a year of attendance nominally costs before financial aid. Includes tuition, fees, books, supplies, room & board, and living expenses. `COSTT4_A` (academic-year) and `COSTT4_P` (program-year) are mutually exclusive — no institution reports both.

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `costt4_a` | `COSTT4_A` | double | No | **Yes** | [BT-110](../business-glossary.json) | Average total cost of attendance for an **academic-year program** (the dominant case: ~72% of rows). Tuition + fees + books + room & board + living expenses, all rolled together. Silver zone uses this as the first preference for the unified `cost_of_attendance_annual` field. |
| `costt4_p` | `COSTT4_P` | double | No | **Yes** | [BT-110](../business-glossary.json) | Average total cost of attendance for a **program-year program** (~1.3% of rows — clock-hour or other non-academic-year formats). Silver zone falls back to this when `costt4_a` is null. |

### Net Price — Averages (BT-111)

The "real price" — what the average student actually pays after subtracting grants and scholarships from the cost of attendance. This is the **ROI denominator input** for the new formula. Exactly one of `npt4_pub` / `npt4_priv` is populated per row, determined by `control`.

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `npt4_pub` | `NPT4_PUB` | double | No | **Yes** | [BT-111](../business-glossary.json) | Average net price at **public** institutions (`control=1`). Can be negative when the average student's grant aid exceeds their total cost (e.g., San Diego Mesa College at -$904). Every ROI score and Fight Student Loans outcome at a public school traces back through Silver to this column. |
| `npt4_priv` | `NPT4_PRIV` | double | No | **Yes** | [BT-111](../business-glossary.json) | Average net price at **private** institutions (`control=2` nonprofit or `control=3` for-profit). Same role as `npt4_pub` but for the private branch. Current observed range is $1,525–$77,180. |

### Net Price by Income Quintile — Public Institutions (BT-112)

Net price broken down by family income bracket, for public schools. Lower-income families generally pay less due to more aid, but this is not guaranteed at the adjacent-quintile level (see Caveats). Five quintiles:

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `npt41_pub` | `NPT41_PUB` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at public schools for families earning **$0–$30K** (quintile 1 — lowest income). Drives Silver's `net_price_q1` for `control=1` rows. |
| `npt42_pub` | `NPT42_PUB` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at public schools for families earning **$30K–$48K** (quintile 2). Drives Silver's `net_price_q2` for `control=1` rows. |
| `npt43_pub` | `NPT43_PUB` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at public schools for families earning **$48K–$75K** (quintile 3 — median bracket, the most common student profile at public institutions). Drives Silver's `net_price_q3` for `control=1` rows. |
| `npt44_pub` | `NPT44_PUB` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at public schools for families earning **$75K–$110K** (quintile 4). Drives Silver's `net_price_q4` for `control=1` rows. |
| `npt45_pub` | `NPT45_PUB` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at public schools for families earning **$110K+** (quintile 5 — highest income, typically receives least aid, so this figure is usually closest to the full cost of attendance). Drives Silver's `net_price_q5` for `control=1` rows. |

### Net Price by Income Quintile — Private Institutions (BT-112)

Same structure as the public series, but for private schools (nonprofit and for-profit).

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `npt41_priv` | `NPT41_PRIV` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at private schools for families earning **$0–$30K** (quintile 1). Can be negative — MIT's Q1 net price is -$4,129, meaning the average low-income student receives more aid than the full cost. Drives Silver's `net_price_q1` for `control IN (2,3)` rows. |
| `npt42_priv` | `NPT42_PRIV` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at private schools for families earning **$30K–$48K** (quintile 2). Drives Silver's `net_price_q2` for `control IN (2,3)` rows. |
| `npt43_priv` | `NPT43_PRIV` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at private schools for families earning **$48K–$75K** (quintile 3). Drives Silver's `net_price_q3` for `control IN (2,3)` rows. |
| `npt44_priv` | `NPT44_PRIV` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at private schools for families earning **$75K–$110K** (quintile 4). Drives Silver's `net_price_q4` for `control IN (2,3)` rows. |
| `npt45_priv` | `NPT45_PRIV` | double | No | **Yes** | [BT-112](../business-glossary.json) | Average net price at private schools for families earning **$110K+** (quintile 5). Typically the value closest to full cost of attendance at a private school. Drives Silver's `net_price_q5` for `control IN (2,3)` rows. |

### Tuition & Fees

Tuition and fees are a **component** of cost of attendance, not the whole thing. These fields are carried through for receipt transparency ("your $22,800 cost of attendance breaks down as $10K tuition + $12K room & board + ..."), but they do **not** drive ROI — `net_price_annual` already nets grants and scholarships off the full cost.

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `tuitionfee_in` | `TUITIONFEE_IN` | double | No | No | — | In-state tuition and fees. For public institutions, this is the discounted rate offered to residents of the institution's state. For private institutions, this usually equals `tuitionfee_out`. Tuition only — does not include housing, meals, books, or living expenses. |
| `tuitionfee_out` | `TUITIONFEE_OUT` | double | No | No | — | Out-of-state tuition and fees. The rate charged to non-residents at public institutions; at private schools, usually identical to `tuitionfee_in`. Tuition only. |

### Room & Board and Books

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `roomboard_on` | `ROOMBOARD_ON` | double | No | No | — | On-campus housing and meals cost (dormitory + meal plan). Null at ~43% of institutions — schools without on-campus housing (commuter schools, online-only). Already rolled into `costt4_a`/`costt4_p`; separate field is for receipt display. |
| `roomboard_off` | `ROOMBOARD_OFF` | double | No | No | — | Off-campus housing and meals cost for students living independently (not with family). Already rolled into `costt4_a`/`costt4_p`; separate field is for receipt display. |
| `booksupply` | `BOOKSUPPLY` | double | No | No | — | Estimated annual cost for books and supplies. Can be $0 (~32 schools include books in tuition or provide them free). Already rolled into `costt4_a`/`costt4_p`; separate field is for receipt display. |

### Pipeline Metadata

| Field | Source Column | Type | Required | CDE | Business Term | Plain-English Definition |
|-------|--------------|------|----------|-----|---------------|--------------------------|
| `ingested_at` | (derived) | timestamp | Yes | No | — | UTC timestamp recording when the Bronze ingest run wrote this row. Identical across all rows in a single batch — acts as a batch identifier, not a per-row event time. |
| `source_url` | (derived) | string | Yes | No | — | Provenance URL recording where this row was downloaded from (the College Scorecard bulk CSV endpoint). Unauthenticated public URL — no secrets-hygiene concern. |
| `source_method` | (derived) | string | Yes | No | — | Literal string `"bulk_csv_download"` identifying the ingest path used. |
| `load_date` | (derived) | date | Yes | No | — | Calendar date the batch load ran, in UTC. Used by the freshness DQ guardrail. |

---

## Data Quality Rules

The 13 DQ rules covering this table are defined in [governance/dq-rules/raw-ingest-college-scorecard-institution.json](../dq-rules/raw-ingest-college-scorecard-institution.json). Summary:

| Rule ID | Priority | Field(s) | What It Checks |
|---------|----------|----------|---------------|
| RAW-CSI-001 | P0 | (row count) | Filtered row count between 2,500 and 3,500 (observed: 3,039). |
| RAW-CSI-002 | P0 | `unitid` | Uniqueness — no duplicate institutions. |
| RAW-CSI-003 | P0 | `unitid` | Non-null in every row. |
| RAW-CSI-004 | P0 | `control` | Value in {1, 2, 3} only. |
| RAW-CSI-005 | P0 | `costt4_a` | Range $5,000–$100,000 when non-null. |
| RAW-CSI-006 | P0 | `npt4_pub` | Range -$5,000–$60,000 when non-null (**negatives legitimate**). |
| RAW-CSI-007 | P0 | `npt4_priv` | Range -$5,000–$80,000 when non-null (**negatives legitimate**). |
| RAW-CSI-008 | P1 | `tuitionfee_in` | Range $0–$75,000 when non-null. |
| RAW-CSI-009 | P1 | `roomboard_on` | Range $1,000–$30,000 when non-null. |
| RAW-CSI-010 | P0 | `costt4_a`, `costt4_p` | At least one of the two non-null in ≥70% of rows. |
| RAW-CSI-011 | P1 | `npt4_pub` | ≥75% non-null when `control=1`. |
| RAW-CSI-012 | P1 | `npt4_priv` | ≥65% non-null when `control=2`. |
| RAW-CSI-013 | P1 | quintile series | Full-span monotonicity: `npt41 ≤ npt45` where both non-null (≤50 violations allowed). Adjacent-pair monotonicity is **not** enforced (37.9% legitimate Q1>Q2 inversions in private schools). |

---

## Caveats for Consumers

1. **CONTROL drives net-price selection.** Silver zone uses `CASE WHEN control=1 THEN npt4_pub WHEN control IN (2,3) THEN npt4_priv` to produce unified `net_price_annual`. Never mix the public and private columns — a private school with a non-null `npt4_pub` would be a data bug, not a valid reading.

2. **Negative net prices are real.** 3 public schools (San Diego Mesa -$904, Skyline College -$1,180, St Petersburg College -$52) and 5 private quintile values (including MIT Q1 at -$4,129) have negative net prices because average grant aid exceeds total cost. Downstream consumers must accept negative values — clipping to $0 would hide legitimate generosity.

3. **Adjacent quintile ordering is not monotonic.** 37.9% of private institutions have Q1 > Q2 because merit aid programs targeting lower-middle-income students can exceed need-based aid for lowest-income students. Only the full-span invariant `Q1 ≤ Q5` holds (with ~3.2% legitimate exceptions at private schools).

4. **COA coverage is 73.5%, not 100%.** 806 institutions have neither `costt4_a` nor `costt4_p` — concentrated in `PREDDEG=0` (unclassified) and `PREDDEG=4` (graduate-dominant) schools captured by the `ICLEVEL=1` filter.

5. **For-profit coverage is thin.** `control=3` institutions have only 52.6% net-price coverage and 44.3% COA coverage. Expected — for-profit schools underreport to IPEDS. The Gold LEFT JOIN will produce null cost data for many for-profit-school programs.

6. **Tuition is NOT the ROI denominator.** Use `net_price_annual` (which nets grants/scholarships off the full COA), not `tuitionfee_in`/`tuitionfee_out` (which is only the tuition slice). Confusing the two materially misstates student cost.

7. **91.9% join coverage to program data.** Of the ~2,559 UNITIDs in `raw.college_scorecard`, 2,352 match here (91.9%). The remaining 207 (8.1%) will get null cost fields after the Gold LEFT JOIN. This is expected and not a DQ failure.

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-04-14 | Initial data dictionary for Bronze table `raw.college_scorecard_institution`. 28 fields documented (24 source + 4 metadata), 17 flagged CDE, 0 flagged PII. | @doc-generator |
