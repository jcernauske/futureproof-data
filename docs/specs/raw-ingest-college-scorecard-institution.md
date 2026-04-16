# Spec: raw-ingest-college-scorecard-institution

**Status:** DRAFT
**Zone:** Raw → Silver → Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-14

---

## Problem Statement

Ingest the College Scorecard **institution-level** data file to bring in cost-of-attendance, net price, tuition, and room & board fields. FutureProof already has the field-of-study file (earnings, debt by school+major) but lacks the institution-level cost structure. Without this, the loan slider scales against historical median debt — what past grads borrowed — rather than what the school actually costs. That's misleading: a student at a $60K/year school with a $50K scholarship and a student at a $40K/year school with zero aid can both graduate with $80K in debt, but their financial situations are completely different.

This data enables a more honest ROI formula: `earnings / (net_price × 4 × loan_pct)` instead of `earnings / debt_median`. The median debt stays as a reality-check reference: "The median debt of graduates from this program is $X."

**Joins to existing data on UNITID.** Same source, same provider, same key — different CSV file, different grain (institution-level, not program-level).

## Source Data

- **Source:** U.S. Department of Education College Scorecard (Institution-Level)
- **Method:** Bulk CSV download
- **URL:** `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Institution.csv`
- **Entities:** All Title IV institutions (~6,500 rows after filtering to 4-year bachelor's-granting)
- **Size:** ~170MB (full file has 1,900+ columns; we extract ~15)
- **License:** U.S. Government Work — public domain
- **User-Agent:** `FutureProof/0.1 (jeff@hyenastudios.com)`

### Key Fields We Need

| Scorecard Field | What It Is | Includes Housing? |
|----------------|-----------|-------------------|
| `COSTT4_A` | Average cost of attendance (academic year programs) | Yes — tuition + fees + books + room & board + living expenses |
| `COSTT4_P` | Average cost of attendance (program-year programs) | Yes |
| `NPT4_PUB` | Average net price — public institutions | Yes — COA minus grants/scholarships |
| `NPT4_PRIV` | Average net price — private institutions | Yes |
| `NPT41_PUB` through `NPT45_PUB` | Net price by income quintile — public | Yes |
| `NPT41_PRIV` through `NPT45_PRIV` | Net price by income quintile — private | Yes |
| `TUITIONFEE_IN` | In-state tuition and fees | No — tuition only |
| `TUITIONFEE_OUT` | Out-of-state tuition and fees | No — tuition only |
| `ROOMBOARD_ON` | On-campus room and board | Housing + meals only |
| `ROOMBOARD_OFF` | Off-campus room and board (not with family) | Housing + meals only |
| `BOOKSUPPLY` | Books and supplies | No |
| `OTHEREXPENSE_ON` | Other expenses, on campus | No |
| `OTHEREXPENSE_OFF` | Other expenses, off campus | No |
| `CONTROL` | Institution control (1=Public, 2=Private nonprofit, 3=Private for-profit) | N/A — needed to pick NPT4_PUB vs NPT4_PRIV |

### What We Already Have

The field-of-study file (`raw.college_scorecard`) provides per-program:
- `debt_all_stgp_eval_mdn` → `debt_median` in Silver — median debt at graduation
- `earn_mdn_hi_1yr` → `earnings_1yr_median` — median earnings 1yr post-completion
- `unitid`, `cipcode`, `instnm`, etc.

This spec adds institution-level cost data that joins to the existing program data on `unitid`.

## Success Criteria

- [ ] Raw data lands in Iceberg table `raw.college_scorecard_institution`
- [ ] All cost/price fields ingested with PrivacySuppressed → null handling
- [ ] Filter to PREDDEG=3 (predominantly bachelor's degree-granting) or ICLEVEL=1 (4-year)
- [ ] Silver base table `base.college_scorecard_institution` produced with unified net price field
- [ ] Gold update: `consumable.career_outcomes` gains `net_price_annual` column
- [ ] DQ rules written and passing at each zone
- [ ] Data contract updated

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: raw.college_scorecard_institution

- **Grain:** One row per institution (UNITID)
- **Dedup grain:** [unitid]
- **Expected rows:** ~6,500 (after filtering to 4-year bachelor's-granting)

### Ingestor

- **Class:** `CollegeScorecardInstitutionIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/college_scorecard_institution_ingestor.py`
- **Implementation notes:**
  - Use `pandas.read_csv(..., usecols=[...])` to extract only the ~20 fields we need from the 1,900+ column file
  - Replace "PrivacySuppressed" with None across all columns before type coercion
  - Filter: `PREDDEG == 3` (predominantly bachelor's) or `ICLEVEL == 1` (4-year institution)
  - UNITID is integer — matches the field-of-study file's UNITID
  - Set `User-Agent` header on download request
  - Chunked reading recommended given file size (~170MB)

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| unitid | long | yes | Institution IPEDS ID — join key to existing Scorecard data |
| instnm | string | yes | Institution name |
| stabbr | string | yes | State abbreviation (2-letter) |
| control | int | yes | 1=Public, 2=Private nonprofit, 3=Private for-profit |
| preddeg | int | yes | Predominant degree (3=Bachelor's) |
| costt4_a | double | no | Average cost of attendance, academic year (tuition + fees + books + room & board) |
| costt4_p | double | no | Average cost of attendance, program year |
| npt4_pub | double | no | Average net price, public institutions |
| npt4_priv | double | no | Average net price, private institutions |
| npt41_pub | double | no | Net price, $0-$30K income, public |
| npt42_pub | double | no | Net price, $30K-$48K income, public |
| npt43_pub | double | no | Net price, $48K-$75K income, public |
| npt44_pub | double | no | Net price, $75K-$110K income, public |
| npt45_pub | double | no | Net price, $110K+ income, public |
| npt41_priv | double | no | Net price, $0-$30K income, private |
| npt42_priv | double | no | Net price, $30K-$48K income, private |
| npt43_priv | double | no | Net price, $48K-$75K income, private |
| npt44_priv | double | no | Net price, $75K-$110K income, private |
| npt45_priv | double | no | Net price, $110K+ income, private |
| tuitionfee_in | double | no | In-state tuition and fees |
| tuitionfee_out | double | no | Out-of-state tuition and fees |
| roomboard_on | double | no | On-campus room and board |
| roomboard_off | double | no | Off-campus room and board |
| booksupply | double | no | Books and supplies |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_url | string | yes | Download URL |
| source_method | string | yes | "bulk_csv_download" |
| load_date | date | yes | Date of load |

### DQ Rules (Bronze)

- Row count: 5,000–8,000 (P0 — reasonable range for 4-year bachelor's institutions)
- unitid uniqueness (P0 — institution grain, no duplicates)
- unitid non-null: 100% (P0)
- control values IN (1, 2, 3) (P0)
- costt4_a range: $5,000–$100,000 where non-null (P0)
- npt4_pub range: $0–$60,000 where non-null (P0)
- npt4_priv range: $0–$80,000 where non-null (P0)
- tuitionfee_in range: $0–$65,000 where non-null (P1)
- roomboard_on range: $3,000–$25,000 where non-null (P1)
- At least one of costt4_a or costt4_p non-null: ≥90% of rows (P0)
- control=1 → npt4_pub non-null ≥80% (P1 — public schools should have public net price)
- control=2 → npt4_priv non-null ≥80% (P1)

---

## Zone 2: Silver (Normalize + Model)

### Iceberg Table: base.college_scorecard_institution

- **Grain:** One row per institution (unitid)
- **Dedup grain:** [unitid]
- **Promote pattern:** `compute_grain_id(row, ['unitid'], prefix='csi')`

### Silver Transformations

1. **Unified net price:** Create a single `net_price_annual` field that picks the right net price based on institution control:
   ```
   net_price_annual = CASE
     WHEN control = 1 THEN npt4_pub      -- Public
     WHEN control IN (2, 3) THEN npt4_priv  -- Private nonprofit or for-profit
   END
   ```

2. **Unified cost of attendance:** Pick the right COA:
   ```
   cost_of_attendance_annual = COALESCE(costt4_a, costt4_p)
   ```

3. **Institution control label:** Map numeric control to string:
   - 1 → "Public"
   - 2 → "Private nonprofit"
   - 3 → "Private for-profit"

4. **4-year total cost estimates:**
   ```
   net_price_4yr = net_price_annual × 4
   cost_of_attendance_4yr = cost_of_attendance_annual × 4
   ```

5. **Net price by income quintile — unified:** Create 5 unified quintile fields that pick pub/priv based on control:
   ```
   net_price_q1 = CASE WHEN control=1 THEN npt41_pub ELSE npt41_priv END  -- $0-$30K
   net_price_q2 = ...  -- $30K-$48K
   net_price_q3 = ...  -- $48K-$75K
   net_price_q4 = ...  -- $75K-$110K
   net_price_q5 = ...  -- $110K+
   ```

6. **All raw cost fields carried through** for receipt/provenance display.

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `csi`) |
| unitid | long | yes | IPEDS institution ID — join key |
| institution_name | string | yes | |
| state_abbr | string | yes | 2-letter state code |
| institution_control | string | yes | "Public" / "Private nonprofit" / "Private for-profit" |
| cost_of_attendance_annual | double | no | Best available COA (COSTT4_A or COSTT4_P) |
| net_price_annual | double | no | Average net price (pub or priv based on control) |
| net_price_4yr | double | no | net_price_annual × 4 |
| cost_of_attendance_4yr | double | no | cost_of_attendance_annual × 4 |
| net_price_q1 | double | no | Net price for $0-$30K family income |
| net_price_q2 | double | no | Net price for $30K-$48K |
| net_price_q3 | double | no | Net price for $48K-$75K |
| net_price_q4 | double | no | Net price for $75K-$110K |
| net_price_q5 | double | no | Net price for $110K+ |
| tuition_in_state | double | no | In-state tuition and fees |
| tuition_out_of_state | double | no | Out-of-state tuition and fees |
| room_board_on_campus | double | no | On-campus room and board |
| room_board_off_campus | double | no | Off-campus room and board |
| books_supplies | double | no | Books and supplies estimate |
| source_load_date | date | yes | |
| ingested_at | timestamp | yes | Silver promotion timestamp |

### DQ Rules (Silver)

- Row count matches Bronze (P0)
- unitid uniqueness (P0)
- net_price_annual non-null: ≥85% (P0 — most institutions should have this)
- cost_of_attendance_annual non-null: ≥80% (P0)
- net_price_annual ≤ cost_of_attendance_annual where both non-null (P0 — net price can't exceed sticker price)
- net_price_4yr = net_price_annual × 4 within $1 tolerance (P0)
- institution_control values IN ("Public", "Private nonprofit", "Private for-profit") (P0)
- net_price_q1 ≤ net_price_q5 where both non-null (P1 — lower-income families should have lower net price due to aid)

### Business Glossary Terms

| Term ID | Name | Definition |
|---------|------|-----------|
| BT-110 | Cost of Attendance (COA) | The total annual cost of attending an institution, including tuition, fees, books, supplies, room & board, and living expenses. Source: College Scorecard COSTT4_A field, derived from IPEDS. This is the "sticker price" before financial aid. |
| BT-111 | Net Price | The average annual cost students actually pay after subtracting grants and scholarships from the cost of attendance. Source: College Scorecard NPT4_PUB/NPT4_PRIV. This is what students need to cover through savings, earnings, and/or loans. |
| BT-112 | Net Price by Income Quintile | Net price broken down by family income bracket ($0-$30K, $30K-$48K, $48K-$75K, $75K-$110K, $110K+). Lower-income families typically receive more aid, resulting in lower net prices. Source: College Scorecard NPT41-NPT45 fields. |

---

## Zone 3: Gold (Enrich Existing Tables)

This spec does NOT create a new standalone Gold table. Instead, it enriches the existing `consumable.career_outcomes` table with a LEFT JOIN to `base.college_scorecard_institution` on `unitid`.

### Gold Table Update: consumable.career_outcomes

**New columns added via LEFT JOIN on unitid:**

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| net_price_annual | double | base.college_scorecard_institution | What students actually pay per year after aid |
| cost_of_attendance_annual | double | base.college_scorecard_institution | Full sticker price per year |
| net_price_4yr | double | base.college_scorecard_institution | 4-year total net cost |
| institution_control | string | base.college_scorecard_institution | Public / Private nonprofit / Private for-profit |
| tuition_in_state | double | base.college_scorecard_institution | For display/receipts |
| tuition_out_of_state | double | base.college_scorecard_institution | For display/receipts |
| room_board_on_campus | double | base.college_scorecard_institution | For display/receipts |

**Existing columns unchanged:** All current fields on `consumable.career_outcomes` are preserved. `debt_median` stays — it becomes a reference/comparison field rather than the ROI driver.

### Gold DQ Rules (Updated)

- All existing DQ rules on `consumable.career_outcomes` still pass (P0)
- net_price_annual non-null: ≥80% of rows (P1 — some institutions may not report)
- net_price_annual ≤ cost_of_attendance_annual where both non-null (P0)
- net_price_annual > 0 where non-null (P0)

### Data Contract Update

| Property | Value |
|----------|-------|
| Change | Added institution-level cost fields via LEFT JOIN |
| Backward compatible | Yes — all existing columns unchanged |
| New nullable columns | net_price_annual, cost_of_attendance_annual, net_price_4yr, institution_control, tuition_in_state, tuition_out_of_state, room_board_on_campus |

---

## Agent Workflow

Same pipeline as the existing Scorecard ingest, abbreviated for a smaller source:

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implement ingestor (fetch, filter, schema)
3. @data-analyst — EDA (institution-level cost distributions, null rates, outliers)
4. @dq-rule-writer — Write DQ rules for Bronze + Silver
5. @dq-engineer — Execute rules
6. @primary-agent — Build Silver transformer
7. @primary-agent — Update Gold engine spec to LEFT JOIN new table
8. @governance-reviewer — Post-implementation check
9. @staff-engineer — Final review

---

## Estimated Effort

| Step | Estimate |
|------|----------|
| Bronze ingest (CSV download, field extraction, PrivacySuppressed handling) | 1.5 hours |
| Silver transform (unified net price, control label, 4yr estimates) | 1.5 hours |
| Gold engine update (LEFT JOIN on unitid, add columns) | 1 hour |
| DQ rules + governance | 1 hour |
| **Total** | **~5 hours** |

---

## Cross-Source Integration Notes

This is the sixth data source in the FutureProof pipeline, but it's really an extension of the first:

1. **College Scorecard — Field of Study** (COMPLETE) — program-level: earnings, debt
2. **College Scorecard — Institution** (this spec) — institution-level: cost, net price, tuition, room & board
3. **BLS OOH** (COMPLETE) — occupation projections
4. **O*NET** (COMPLETE) — task-level occupation data
5. **Karpathy AI Exposure** (COMPLETE) — AI exposure scores
6. **BEA Regional Price Parities** (COMPLETE) — state-level cost of living

Join topology:
```
base.college_scorecard_institution (unitid)
  LEFT JOIN → consumable.career_outcomes (unitid)
    → ROI formula uses net_price_annual × 4 × loan_pct instead of debt_median
    → debt_median becomes reference/comparison field
    → Receipts show full cost breakdown
```

---

*— End of Spec —*
