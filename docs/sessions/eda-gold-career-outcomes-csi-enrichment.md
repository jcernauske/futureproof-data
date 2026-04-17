# EDA Report: Gold consumable.career_outcomes — CSI Enrichment (LEFT JOIN Simulation)

**Source (left):** Gold `consumable.career_outcomes` (pre-enrichment) — real Iceberg table at `data/gold/iceberg_warehouse/consumable/career_outcomes`
**Source (right):** Silver `base.college_scorecard_institution` — real Iceberg table at `data/silver/iceberg_warehouse/base/college_scorecard_institution`
**Date:** 2026-04-16
**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` §Zone 3
**Simulation script:** `scripts/eda_gold_csi_left_join.py`
**Raw stats JSON:** `docs/sessions/eda-gold-csi-join-stats.json`
**Silver baseline EDA:** `docs/sessions/eda-silver-base-college-scorecard-institution.md`

---

## Purpose

Calibrate the completeness thresholds on **GLD-CSI-005** (net_price_annual), **GLD-CSI-006** (cost_of_attendance_annual), **GLD-CSI-007** (institution_control), and the unmatched-UNITID magnitude on **GLD-CSI-008** — before the transformer is modified and before `@dq-rule-writer` commits the rules. The spec uses placeholder targets of ≥60% for all three completeness rules and predicts ~1,131 unmatched UNITIDs. This EDA replaces those placeholders with evidence-based numbers.

Method: simulate the exact LEFT JOIN the transformer will execute (`consumable.career_outcomes LEFT JOIN base.college_scorecard_institution ON unitid`) in-memory via DuckDB against Arrow scans of the real Iceberg tables. No data was written; the pre-enrichment Gold table was scanned read-only.

---

## Record Counts (Pre-Join)

| Side | Table | Rows | Distinct UNITIDs |
|------|-------|-----:|-----------------:|
| Left | `consumable.career_outcomes` | **69,947** | **2,559** |
| Right | `base.college_scorecard_institution` | **3,039** | **3,039** |

- Gold row count: **69,947** — confirms spec §Enrichment Mode note 4 exactly.
- Gold grain `(unitid, cipcode, credential_level)` has 0 duplicates (invariant preserved).
- **Distinct UNITIDs in Gold is 2,559, not ~4,170 as the spec's note 5 estimates.** See Surprise 1 below.

---

## Key Findings (1-paragraph calibration summary)

The LEFT JOIN behaves far better than the spec's pre-EDA placeholders assumed. Post-join coverage is:

- `net_price_annual` non-null: **95.45%** (66,763 / 69,947)
- `cost_of_attendance_annual` non-null: **95.45%** (66,763 / 69,947) — row-identical to net_price
- `institution_control` non-null: **97.42%** (68,143 / 69,947)
- Only **207** distinct UNITIDs are unmatched (not ~1,131), accounting for **1,804 rows** (2.58% of the 69,947)

The 60% placeholder thresholds in GLD-CSI-005/006/007 underestimate actual coverage by ~35pp. The ~1,131 estimate in GLD-CSI-008 overstates reality by ~5.5×. Both need tightening.

---

## UNITID Overlap Analysis (Join Key Behavior)

| Metric | Value |
|--------|------:|
| Distinct UNITIDs in `career_outcomes` | 2,559 |
| Distinct UNITIDs in `base.college_scorecard_institution` | 3,039 |
| Overlap (matched on both sides) | **2,352** |
| Unmatched in `career_outcomes` (no CSI record) | **207** |
| CSI UNITIDs with no program data in `career_outcomes` | 687 |

**Interpretation:**
- **91.9%** of `career_outcomes` UNITIDs match to Silver CSI (2,352 / 2,559).
- The remaining **8.1%** (207 UNITIDs) get NULLs for all 7 new columns.
- 687 institutions in CSI have no corresponding field-of-study rows in Gold — these don't affect the join (LEFT side drops them) and aren't a DQ concern for this spec.

### Sample Unmatched Institutions (10)

| UNITID | Institution Name |
|-------:|------------------|
| 134811 | AI Miami International University of Art and Design |
| 404994 | ASA College |
| 447935 | ATA College |
| 237118 | Alderson Broaddus University |
| 194161 | Alliance University |
| 137801 | Altierus Career College-Tampa |
| 188678 | American Academy of Dramatic Arts-New York |
| 457688 | American Business and Technology University |
| 461005 | American College for Medical Careers |
| 460738 | American Sentinel College of Nursing and Health Sciences |

**Pattern:** Unmatched institutions are overwhelmingly **closed / closing for-profit career colleges, small art institutes, and specialty nursing schools**. These are institutions where College Scorecard has field-of-study outcomes (historical earnings/debt data) but either (a) the institution has since closed and is excluded from the institution-level file, or (b) it falls outside the PREDDEG=3 OR ICLEVEL=1 filter used to build Silver CSI. This is expected and benign.

### Program-Weight of Unmatched UNITIDs

| Metric | Value |
|--------|------:|
| Unmatched UNITIDs | 207 |
| Total rows with unmatched UNITIDs | 1,804 |
| Min rows per unmatched UNITID | 1 |
| Median rows per unmatched UNITID | 4 |
| Mean rows per unmatched UNITID | 8.7 |
| Max rows per unmatched UNITID | 142 |

The unmatched UNITIDs skew toward institutions with few programs (median 4). The 142-row max is a single outlier — a large formerly-multiprogram for-profit.

---

## Post-Join Row-Level Null Rates (the core calibration evidence)

All percentages computed on the full 69,947-row joined result.

| Field | Non-null Rows | Null Rows | Non-null % | Null % |
|-------|--------------:|----------:|-----------:|-------:|
| `net_price_annual` | **66,763** | 3,184 | **95.448%** | 4.552% |
| `cost_of_attendance_annual` | **66,763** | 3,184 | **95.448%** | 4.552% |
| `net_price_4yr` | 66,763 | 3,184 | 95.448% | 4.552% |
| `institution_control` | **68,143** | 1,804 | **97.421%** | 2.579% |
| `tuition_in_state` | 67,322 | 2,625 | 96.247% | 3.753% |
| `tuition_out_of_state` | 67,322 | 2,625 | 96.247% | 3.753% |
| `room_board_on_campus` | 62,269 | 7,678 | 89.023% | 10.977% |

### Interpretation

- **`institution_control` has the highest coverage (97.42%).** It is null only for the 1,804 rows coming from the 207 unmatched UNITIDs. Every matched row has a control label (100%).
- **`net_price_annual` and `cost_of_attendance_annual` are row-identical co-null** (both null on exactly the same 3,184 rows; zero asymmetric-null rows). This is the inherited pattern from Silver (Silver EDA Surprise 1).
  - Split: **1,804 rows null because UNITID unmatched** + **1,380 rows null because matched UNITID has null NP/COA in Silver** = 3,184.
- **`room_board_on_campus` is the weakest at 89.02%** — institutions without on-campus housing legitimately have no value. The 7,678 null rows break down as 1,804 unmatched + 5,874 matched-but-no-on-campus-housing.

### Co-null Matrix: net_price_annual vs. cost_of_attendance_annual

| net_price_annual | cost_of_attendance_annual | Rows |
|------------------|---------------------------|-----:|
| populated | populated | 66,763 |
| null | null | 3,184 |
| null | populated | **0** |
| populated | null | **0** |

**A single coverage rule gates both** (same pattern observed in Silver). `@dq-rule-writer` can keep them as two rules for clarity, but they will always pass or fail together.

---

## `institution_control` Distribution (Post-Join, Row-Weighted)

| Control | Rows | % of 69,947 |
|---------|-----:|-----------:|
| Private nonprofit | 37,211 | 53.20% |
| Public | 29,374 | 41.99% |
| Private for-profit | 1,558 | 2.23% |
| **(null — unmatched UNITID)** | **1,804** | **2.58%** |

### Same distribution at the distinct-UNITID level

| Control | Distinct UNITIDs |
|---------|-----------------:|
| Private nonprofit | 1,349 |
| Public | 751 |
| Private for-profit | 252 |
| (null — unmatched) | 207 |
| **Total** | **2,559** |

**Interpretation:**
- Private nonprofits carry the majority of career-outcome rows (53.2%) because they offer the widest program diversity per institution.
- Public institutions are underrepresented at the row level (41.99%) vs. the field-of-study population (public schools produce half the students but have narrower program catalogs per institution).
- **Only 2.23% of joined rows are for-profits** — far below Silver's 13.75% for-profit share of institutions. For-profit schools have fewer programs per institution in the `consumable.career_outcomes` grain.
- Zero rows violate the domain `{Public, Private nonprofit, Private for-profit}`. GLD-CSI-009 (categorical safety) is safely 100% enforceable.

---

## Spot-Check: Elite Institutions (Sanity Check)

Five well-known institutions verified end-to-end through the LEFT JOIN:

| UNITID | Institution | Control | COA annual | Net Price annual | Tuition (OoS) | Programs |
|-------:|-------------|---------|-----------:|-----------------:|--------------:|---------:|
| 166027 | Harvard University | Private nonprofit | $82,842 | $16,816 | $59,076 | 66 |
| 166683 | Massachusetts Institute of Technology | Private nonprofit | $79,850 | $19,813 | $60,156 | 38 |
| 186131 | Princeton University | Private nonprofit | $80,440 | $10,555 | $59,710 | 37 |
| 243744 | Stanford University | Private nonprofit | $82,162 | $12,136 | $62,484 | 49 |
| 130794 | Yale University | Private nonprofit | $85,120 | $27,818 | $64,700 | 55 |

Values are **sensible and reflect real aid patterns**: COA $79–85K, net prices from $10K (Princeton — heaviest aid) to $28K (Yale). All five correctly resolve through the join. The join logic is sound.

---

## Cross-Check Against Silver Baseline

| Silver stat | Silver row-share | Implied Gold (via join) | Observed Gold row-share |
|-------------|------------------|-------------------------|-------------------------|
| NP non-null per UNITID | 2,233 / 3,039 = 73.48% | depends on which UNITIDs overlap | 66,763 / 69,947 = 95.45% |
| Matched UNITIDs | — | 2,352 | 2,352 ✓ |
| Unmatched UNITIDs | — | spec said ~1,131 | **207** ✗ (see Surprise 1) |

The **95.45% row-level NP coverage in Gold is HIGHER than Silver's 73.48% unitid-level NP coverage** because the Gold field-of-study universe is disproportionately concentrated on large comprehensive universities (lots of programs each, almost all of which report financial aid data). Smaller / for-profit / closed institutions produce fewer rows, so their higher null rate has a smaller row-weighted impact.

---

## Recommended DQ Thresholds (for @dq-rule-writer)

Each threshold is set to pass cleanly on current data while leaving a ~5pp buffer for year-over-year source drift.

| Rule | Field | Spec Placeholder | Observed | **Recommended Threshold** | Severity | Rationale |
|------|-------|------------------|---------:|---------------------------|----------|-----------|
| GLD-CSI-005 | `net_price_annual` non-null | ≥60% | **95.45%** | **≥90%** | P1 | 5.45pp headroom. Tighter than spec's 60% is critical — the spec value provides no real signal. |
| GLD-CSI-006 | `cost_of_attendance_annual` non-null | ≥60% | **95.45%** | **≥90%** | P1 | Identical co-null pattern with NP; same threshold applies. |
| GLD-CSI-007 | `institution_control` non-null | ≥60% | **97.42%** | **≥95%** | P1 | 2.42pp buffer. Only null when UNITID unmatched; highest-coverage field. |
| GLD-CSI-008 | Unmatched-UNITID count | ~1,131 ±10% | **207** | **≤300** (or 180–240 ±20%) | P1 | The spec's 1,131 estimate is ~5.5× too high. See Surprise 1. |

### Optional companion rules (P2, informational)

| Rule | Field | Observed | Recommendation |
|------|-------|---------:|----------------|
| GLD-CSI-010 (new) | `room_board_on_campus` non-null | 89.02% | ≥85% P2. Documents the weakest coverage field; legitimate nulls from no-residential institutions. |
| GLD-CSI-011 (new) | `tuition_in_state` / `tuition_out_of_state` non-null | 96.25% | ≥92% P2. |
| GLD-CSI-012 (new) | NP / COA co-null strict equality | 100% | The row-identical co-null pattern (0 asymmetric) is a structural source guarantee; worth a P2 sentinel that detects if College Scorecard starts diverging. |

### Stability / re-run guidance

GLD-CSI-005/006/007 thresholds should **not** be set with zero buffer (e.g. ≥95.4%) because College Scorecard reissues institution-level files annually and reporting completeness drifts ±2–3pp year over year. The 5pp buffer on each recommendation accommodates this.

---

## Surprises & Flags for Downstream Agents

### Surprise 1 — The spec's 1,131 unmatched-UNITID estimate is 5.5× too high

The spec (§Enrichment Mode note 5) predicts:
> ~1,131 UNITIDs in `consumable.career_outcomes` do not exist in `base.college_scorecard_institution` (4,170 − 3,039).

The 4,170 baseline is wrong. **`consumable.career_outcomes` actually has only 2,559 distinct UNITIDs, not 4,170.** The Silver-zone field-of-study file produced fewer institutions than the spec assumed (likely because the Gold transformer already filters on completion thresholds, bachelor's credentials, and small-cohort suppression).

- **Actual unmatched UNITIDs: 207.** Not ~1,131.
- **Actual unmatched row share: 2.58%.** Not the spec's predicted 55-80% null rate for `net_price_annual`.

**Action for @dq-rule-writer:** Replace GLD-CSI-008 threshold from "≈1,131 ± 10%" to **"≤300 unmatched UNITIDs"** (or "180–240 ± 20%" if a tight band is preferred). Do NOT use the 1,131 figure — it is not grounded in the real data.

**Action for @primary-agent / spec maintainer:** Spec §Enrichment Mode note 5 should be corrected in a follow-up edit. The "55-80%" null rate estimate for `net_price_annual` should be replaced with the measured "~4.5% null rate" once this EDA is accepted.

**Action for @governance-reviewer:** Flag that the baseline numbers in the spec are off by a large factor. The LEFT JOIN is correct; the prediction in the spec was not calibrated against real data.

### Surprise 2 — NP and COA are row-identical co-null post-join (inherited from Silver)

The Silver EDA already documented this at the institution level (Silver Surprise 1). It carries through row-for-row to Gold. 3,184 rows have both NP and COA null; 66,763 have both populated; **zero rows have one without the other**.

**Action for @dq-rule-writer:** GLD-CSI-005 and GLD-CSI-006 will always pass or fail together. Consider either (a) consolidating into a single "institution financial data reported" rule, or (b) keeping them separate for clarity and adding a P2 co-null sentinel (GLD-CSI-012 above) that detects if the source ever starts producing asymmetric nulls.

### Surprise 3 — `institution_control` is the highest-coverage new column

Spec §Gold Table Update lists `institution_control` as the CDE closure for the 2026-04-06 insight-report recommendation. At **97.42% non-null** (68,143 of 69,947 rows), this is immediately unblocked for segmentation use. The prior table was 100% null on this field; the post-enrichment state is 97.42% populated. This is the strongest uplift from the spec.

**Action for @cde-tagger / @insight-manager:** `institution_control` can be promoted to dashboard segmentation without hedging; coverage is sufficient for all analytical uses.

### Surprise 4 — For-profit institutions are heavily underweighted in Gold vs. Silver

Silver CSI: 418 for-profits (13.75% of institutions)
Gold CO joined: only 252 for-profit UNITIDs in the Gold universe (9.85% of matched UNITIDs), representing only 1,558 rows (2.23% of 69,947).

For-profit schools have fewer programs per institution that clear Gold's completion/cohort filters. This is a **modeling observation**, not a DQ issue: any for-profit-specific analysis using the enriched table needs to account for the heavy row-weight concentration on nonprofits (53.2%) and publics (42.0%).

**Action for @insight-manager:** Note this in any for-profit-segmentation narrative.

### No Surprise — row count preservation

`COUNT(*)` on the LEFT JOIN = 69,947 = pre-enrichment `COUNT(*)` on `consumable.career_outcomes`. The LEFT JOIN does not drop rows. GLD-CSI-001 will pass.

### No Surprise — spot-check correctness

Harvard, MIT, Princeton, Stanford, Yale all resolve to plausible COA and NP values through the join. The join logic is correct.

---

## Calibration Numbers (TL;DR for @dq-rule-writer)

| Rule | **Use this threshold** |
|------|------------------------|
| GLD-CSI-005 (net_price_annual non-null) | **≥ 90%** (actual 95.45%) |
| GLD-CSI-006 (cost_of_attendance_annual non-null) | **≥ 90%** (actual 95.45%) |
| GLD-CSI-007 (institution_control non-null) | **≥ 95%** (actual 97.42%) |
| GLD-CSI-008 (unmatched UNITIDs) | **≤ 300** (actual 207) |

---

## Audit Trail

- **Simulation method:** PyIceberg scan → Arrow → DuckDB LEFT JOIN, no writes to Iceberg.
- **Left table snapshot:** current production `consumable.career_outcomes` (pre-enrichment), 69,947 rows, 2,559 distinct UNITIDs.
- **Right table snapshot:** Silver `base.college_scorecard_institution` as materialized 2026-04-14, 3,039 rows / 3,039 distinct UNITIDs (Silver EDA confirmed).
- **Spot check institutions verified:** Harvard (166027), MIT (166683), Princeton (186131), Stanford (243744), Yale (130794). All produced sensible non-null COA/NP/tuition values.
- **Raw numeric JSON output:** `docs/sessions/eda-gold-csi-join-stats.json`
- **Reproduction:** `uv run python scripts/eda_gold_csi_left_join.py`
- **Row count invariant verified:** 69,947 before = 69,947 after LEFT JOIN. GLD-CSI-001 pre-flight passes.

*— End of Report —*
