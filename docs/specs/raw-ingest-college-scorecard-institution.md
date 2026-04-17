# Spec: raw-ingest-college-scorecard-institution

**Status:** IMPLEMENTATION (Bronze + Silver COMPLETE; Gold in progress)
**Zone:** Raw → Silver → Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-14

---

## Problem Statement

Ingest the College Scorecard **institution-level** data file to bring in cost-of-attendance, net price, tuition, and room & board fields. FutureProof already has the field-of-study file (earnings, debt by school+major) but lacks the institution-level cost structure. Without this, the loan slider scales against historical median debt — what past grads borrowed — rather than what the school actually costs. That's misleading: a student at a $60K/year school with a $50K scholarship and a student at a $40K/year school with zero aid can both graduate with $80K in debt, but their financial situations are completely different.

This data **enables** a more honest ROI formula — `earnings / (net_price × 4 × loan_pct)` — which is implemented in a **follow-up spec, `roi-formula-cost-of-attendance.md`** (sequential). The scope of *this* spec is to land `net_price_annual` (and 6 related cost columns) as nullable columns on `consumable.career_outcomes`. The engine transformer (`src/gold/futureproof_engine.py`) and the `compute_stat_roi` signature are **not modified here**. `debt_median` remains the active ROI driver for the duration of this spec; the migration to the net-price formula happens in the follow-up spec after this pipeline completes.

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
- [ ] Gold update: `consumable.career_outcomes` gains 7 nullable columns — `net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `institution_control`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus` — via LEFT JOIN on `unitid`; row count preserved at 69,947
- [ ] DQ rules written and passing at each zone (Gold minimum: 9 rules — see §Gold DQ Rules)
- [ ] Data contract updated with CDE flags for new columns (`net_price_annual`, `cost_of_attendance_annual` = CDE; others = non-CDE)
- [ ] Gold data models (conceptual, logical, physical) for `gold-career-outcomes-college-scorecard` updated with the 7 new columns
- [ ] Business-glossary terms added for new columns not covered by BT-110/111/112 (institution_control, tuition, room_board, net_price_4yr)
- [ ] Lineage event updated to reflect two Silver inputs (`base.college_scorecard`, `base.college_scorecard_institution`)

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

**Scope:** columns land as data. The ROI-formula wiring (use `net_price_annual` instead of `debt_median` in the engine's `compute_stat_roi`) is **out of scope for this spec** and is handled in the follow-up spec `roi-formula-cost-of-attendance.md`. `debt_median` remains the active ROI driver here.

### Gold Table Update: consumable.career_outcomes

**New columns added via LEFT JOIN on unitid (all nullable):**

| Field | Type | Source | CDE? | Notes |
|-------|------|--------|------|-------|
| net_price_annual | double | base.college_scorecard_institution | **YES (CDE)** | What students actually pay per year after aid. CDE rationale: becomes the ROI-formula driver in the follow-up spec; directly consumed by MCP `get_school_programs`. |
| cost_of_attendance_annual | double | base.college_scorecard_institution | **YES (CDE)** | Full sticker price per year. CDE rationale: upper-bound invariant partner for `net_price_annual` (`net_price_annual ≤ cost_of_attendance_annual`) and primary display field for receipts. |
| net_price_4yr | double | base.college_scorecard_institution | No | 4-year total net cost. Display/comparison field; derivable as `net_price_annual × 4`. |
| institution_control | string | base.college_scorecard_institution | No | Public / Private nonprofit / Private for-profit. Categorical, used for segmentation and for picking which net-price bracket to show. Closes the 2026-04-06 insight-report recommendation on institution-type segmentation. |
| tuition_in_state | double | base.college_scorecard_institution | No | Display/receipts only. |
| tuition_out_of_state | double | base.college_scorecard_institution | No | Display/receipts only. |
| room_board_on_campus | double | base.college_scorecard_institution | No | Display/receipts only. |

**Existing columns unchanged:** All current fields on `consumable.career_outcomes` are preserved by name and type. No row is dropped, renamed, or retyped. `debt_median` continues to drive ROI in this spec (semantic demotion to "reference" happens in `roi-formula-cost-of-attendance.md`, not here).

### Enrichment Mode

This is a **full idempotent re-promote**, not an `ALTER TABLE` with backfill UPDATE. The existing transformer pattern at `src/gold/college_scorecard_career_outcomes.py` runs `derive_gold_rows()` against a DuckDB view of Silver and writes the full 69,947-row result to the Iceberg `consumable.career_outcomes` table each run. Extending it requires:

1. **Transformer file:** `src/gold/college_scorecard_career_outcomes.py`
2. **Add a new CTE `institution`** after the existing `cip_bands` CTE:
   ```sql
   institution AS (
       SELECT
           unitid,
           net_price_annual,
           cost_of_attendance_annual,
           net_price_4yr,
           institution_control,
           tuition_in_state,
           tuition_out_of_state,
           room_board_on_campus
       FROM base.college_scorecard_institution
   )
   ```
3. **Final SELECT** adds `LEFT JOIN institution i ON i.unitid = b.unitid` after the existing joins, and propagates the 7 new columns through the projection. Join is LEFT so no row is dropped if a UNITID has no institution match; those rows get NULLs for the 7 new fields.
4. **Row count invariant:** `SELECT COUNT(*) FROM consumable.career_outcomes` must return exactly 69,947 before and after enrichment (or whatever the current production count is — see DQ Rule GLD-CSI-001).
5. **Unmatched UNITIDs:** 207 UNITIDs in `consumable.career_outcomes` do not exist in `base.college_scorecard_institution` (2,559 distinct career_outcomes UNITIDs − 2,352 matched = 207 unmatched). Pre-EDA the estimate was ~1,131 based on a 4,170 baseline; the EDA at `docs/sessions/eda-gold-career-outcomes-csi-enrichment.md` corrected the baseline — `consumable.career_outcomes` has 2,559 distinct UNITIDs, not 4,170. Those 207 UNITIDs × their cipcode × credlev combinations produce the row-level null pattern. Row-level null rate on `net_price_annual` / `cost_of_attendance_annual` is **4.55%** each; `institution_control` is **2.58%** null.
6. **`promoted_at` timestamp:** refreshes to the new promotion time on all rows — this is consistent with the idempotent promote pattern and is not data drift.
7. **Schema evolution:** 7 new Iceberg columns added via Iceberg schema-evolution (additive, nullable). Existing field IDs unchanged.

### Gold DQ Rules

Minimum 9 rules. IDs use the `GLD-CSI-*` prefix (Gold institution enrichment).

| Rule ID | Priority | Dimension | Rule |
|---------|----------|-----------|------|
| GLD-CSI-001 | P0 | Accuracy (row count) | `SELECT COUNT(*) FROM consumable.career_outcomes` equals the pre-enrichment count (currently 69,947). LEFT JOIN must not drop rows. |
| GLD-CSI-002 | P0 | Accuracy (invariant) | `net_price_annual ≤ cost_of_attendance_annual` where both non-null. Net price cannot exceed sticker price. |
| GLD-CSI-003 | P0 | Accuracy (invariant) | `\|net_price_4yr − (net_price_annual × 4)\| ≤ $1` where both non-null. Preserves the Silver invariant that `net_price_4yr` = 4× annual. |
| GLD-CSI-004 | P0 | Validity | `net_price_annual > 0` where non-null. Negative values are legitimate at high-aid institutions per BT-111 — **rule relaxed** to `net_price_annual ≥ -10000` (matches Silver's observed min of -$1,180 with headroom). |
| GLD-CSI-005 | P1 | Completeness | `net_price_annual` non-null: threshold **calibrated during EDA** after first real join. Pre-calibration target `≥ 60%`. Must not be set blindly to 80% — real coverage depends on the UNITID overlap pattern (see §Enrichment Mode note 5). |
| GLD-CSI-006 | P1 | Completeness | `cost_of_attendance_annual` non-null ≥ 60% (calibrated during EDA). |
| GLD-CSI-007 | P1 | Completeness | `institution_control` non-null ≥ 60% (calibrated during EDA). **Validates the 2026-04-06 insight-report recommendation that `institution_control` be surfaced** — the pre-enrichment table had this field 100% null. |
| GLD-CSI-008 | P1 | Validity | Unmatched-UNITID pattern: `SELECT COUNT(DISTINCT unitid) FROM consumable.career_outcomes WHERE net_price_annual IS NULL` ≤ 300 (EDA calibrated to 207 actual; 93-unit drift buffer). If this deviates materially, the LEFT JOIN grain or match logic changed unexpectedly. |
| GLD-CSI-009 | P2 | Consistency | `institution_control` values are exactly one of {`Public`, `Private nonprofit`, `Private for-profit`} where non-null. Categorical safety check. |

All existing DQ rules on `consumable.career_outcomes` (GLD-CO-*) must still pass (regression gate).

### Data Contract Update

| Property | Value |
|----------|-------|
| Change | Added 7 institution-level cost columns via LEFT JOIN; 2 flagged CDE. |
| Backward compatible | Yes — all existing columns preserved by name and type; row count preserved at 69,947. |
| New nullable columns | `net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `institution_control`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus` |
| New CDE flags | `net_price_annual`, `cost_of_attendance_annual` (rationale inline in contract) |
| Minor version bump | 1.x → 1.(x+1) |

### Governance Artifacts Produced at Gold

The following artifacts are produced or updated during the Gold pipeline for this spec:

- Updated conceptual / logical / physical data models under `governance/models/gold-career-outcomes-college-scorecard-*.md` (additive — 7 new attributes on the `CareerOutcomes` entity; Mermaid `erDiagram` and DDL blocks updated)
- New/updated business-glossary terms in `governance/business-glossary.json`: `institution_control`, `tuition (in-state/out-of-state)`, `room and board`, `net_price_4yr` (or reuse of BT-110/111/112 where semantically equivalent) — assigned by `@data-steward` at the Gold pipeline's glossary step
- Updated data contract at `governance/data-contracts/consumable-career-outcomes.yaml` (7 new columns, 2 new CDE flags, minor version bump)
- Updated data dictionary at `governance/data-dictionary.json` (7 new entries)
- New DQ rules file / update at `governance/dq-rules/gold-career-outcomes-college-scorecard.json` (9 new `GLD-CSI-*` rules)
- New DQ scorecard at `governance/dq-scorecards/gold-career-outcomes-college-scorecard-csi-enrichment-scorecard.md`
- New lineage event at `governance/lineage/gold-career-outcomes-college-scorecard-<timestamp>.json` listing **two** Silver inputs (`base.college_scorecard`, `base.college_scorecard_institution`) — supersedes the prior single-input event
- Updated CDE registry at `governance/cde-registry/gold-career-outcomes-college-scorecard-cdes.md` (count +2)
- Chaos-manifest update at `governance/chaos-manifests/gold-career-outcomes-college-scorecard-csi-chaos.md` (at minimum: corrupt a `net_price_annual` value and confirm GLD-CSI-002 detects; corrupt an institution row count and confirm GLD-CSI-001 detects)

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
    → 7 nullable cost columns land on each row
    → debt_median continues to drive ROI here; the migration to
      `earnings / (net_price × 4 × loan_pct)` is handled in the
      follow-up spec `roi-formula-cost-of-attendance.md`
    → Receipts / MCP `get_school_programs` gain real values for
      `institution_control` (previously 100% null)
```

---

*— End of Spec —*
