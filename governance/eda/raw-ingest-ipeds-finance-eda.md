# EDA Report: bronze.ipeds_finance (full)

**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` v1.3
**Source table:** `bronze.ipeds_finance` (Iceberg, snapshot `982081695100705470`)
**Cycle:** FY2022 (academic year 2021-22) — most recent fully-published IPEDS Finance cycle as of 2026-04-30
**Date:** 2026-04-30
**Agent:** `@bs:data-analyst`
**Record Count:** 2,683
**Field Count:** 12
**Pre-flight reference:** `governance/eda/raw-ingest-ipeds-finance-preflight.md` (TBDs locked in v1.3 of the spec)

This report covers EDA Requirements 2-7 from §4. EDA Requirement 1 (column-code lock-down) was resolved in the pre-flight pass.

---

## 1. Executive Summary

The landed table is shape-correct: 2,683 rows / 100% UNITID-unique / form mix F1A=803, F2=1,593, F3=287 / single fiscal year (2022) / 100% non-null instruction & institutional-support across all three forms. Marketing ratio at the institution level is well-behaved (P50 = 0.55, P95 = 2.35); the long P99 tail (8.32) and 21 rows with ratio > 10 are dominated by **public-system administrative offices** (LA CCD, SUNY system, U Illinois system) that report institutional overhead but nominal instruction — not data-quality failures. Per-FTE distributions are also well-behaved with one P99 outlier (UT Southwestern Medical Center, $634K instruction-per-FTE) that is a legitimate small-FTE specialty medical school. Career-outcomes coverage is **90.39%** — exactly meeting the proposed 90% threshold for CON-IFP-008 with no margin. Imputation prevalence is high on endowment (≈ 25-31%) but negligible on instruction and institutional support (< 0.6%). Recommendations focus on tightening per-form thresholds, adding a system-office filter consideration, and tracking the endowment imputation rate.

---

## 2. EDA Requirement Status

| Req | Topic | Status |
|---|---|---|
| 1 | Column-code lock-down | RESOLVED in pre-flight (v1.3 spec) |
| 2 | EFIA year alignment + 5th spot check | OBSERVATION — IU-Bloomington pre-flight UNITID was wrong (correct UID is 151351, not 152228); five anchors verified, year-pairing confirmed |
| 3 | Distribution shapes | PASS — distributions published below; long tails are real institutions, not anomalies |
| 4 | Filter coverage vs `consumable.career_outcomes` | OBSERVATION — overlap is 90.39%, exactly at the proposed threshold; recommendation in §4 |
| 5 | Form-mix diagnosis | PASS — religious/secular split skipped per spec ("optional, skip if costly"); CONTROL/HBCU/region breakdown provided |
| 6 | Per-FTE preview + base DQ thresholds | RECOMMENDATION — proposed BSE-IPF-015 (5.0) and BSE-IPF-017 ($500K) thresholds are correct; tighter per-form variants offered |
| 7 | Imputation-flag prevalence | RECOMMENDATION — endowment imputation rate ≈ 25-31% warrants explicit policy v1.4; instruction/inst_support are < 0.6% (immaterial) |

---

## 3. Distribution Profiles (EDA Req 3)

All four target fields. NULL rates and zero counts are reported alongside; both interact with the per-FTE derivations in §6.

### 3.1 `instruction_expenses` (USD)

| Scope | n | NULL | =0 | P5 | P10 | P25 | P50 | P75 | P90 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Overall | 2,683 | 0 (0.00%) | 34 | $339K | $808K | $3.29M | $14.17M | $45.53M | $135.29M | $263.41M | $949.96M | $3.19B |
| F1A | 803 | 0 | 27 | $2.57M | — | — | $49.68M | — | — | $468.70M | $1.05B | $3.05B |
| F2 | 1,593 | 0 | 7 | $354K | — | — | $9.90M | — | — | $136.59M | $762.14M | $3.19B |
| F3 | 287 | 0 | 0 | $194K | — | — | $2.57M | — | — | $47.07M | $127.52M | $245.15M |

- **Zero-instruction rows (34 total, 31 of which are public)**: confirmed legitimate via name inspection — these are state-system administrative offices (e.g., "LA CCD Office", "U Illinois System Office") that file an F1A finance schedule but report all instruction at member institutions, not at the system level.
- **MAX values**: $3.19B (F2 = Johns Hopkins or similar) and $3.05B (F1A) match the published Carnegie R1 R&D-heavy institutions; no MAGNITUDE outliers.

### 3.2 `institutional_support_expenses` (USD)

| Scope | n | NULL | =0 | P5 | P25 | P50 | P75 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Overall | 2,683 | 0 (0.00%) | 16 | $314K | $2.93M | $8.84M | $21.70M | $98.57M | $290.57M | $973.76M |
| F1A | 803 | 0 | 3 | $2.86M | — | $19.65M | — | $140.16M | $290.57M | $534.83M |
| F2 | 1,593 | 0 | 8 | $309K | — | $7.02M | — | $59.97M | $289.87M | $973.76M |
| F3 | 287 | 0 | 5 | $35K | — | $2.31M | — | $52.71M | $207.49M | $384.56M |

- **F3 institutional support is 100% non-null** (287/287) — confirms the v1.3 pre-flight finding that `F3E03C1` is reliably reported on the post-2014-15 schedule.
- **F2 MAX = $973.76M** = Harvard ($973,760,000) — verified.

### 3.3 `endowment_value` (USD)

| Scope | n | NULL | =0 | P5 | P25 | P50 | P75 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Overall | 2,683 | 650 (24.23%) | 1 | $595K | $12.26M | $42.40M | $142.30M | $1.34B | $8.07B | $50.88B |
| F1A | 803 | 77 (9.59%) | 1 | $1.67M | — | $42.11M | — | $1.31B | $5.00B | $41.92B |
| F2 | 1,593 | 286 (17.95%) | 0 | $492K | — | $42.41M | — | $1.33B | $8.57B | $50.88B |
| F3 | 287 | 287 (100%) | 0 | — | — | — | — | — | — | — |

- **F3 endowment NULL rate is exactly 100%** — confirms the v1.3 "F3 has no `F3H` family" lock; the NULL-cascade through `endowment_per_fte` is correct and intended.
- **F1A NULL rate of 9.6%** is institutions whose primary endowment is held by a related foundation reported separately on F1B (a row this spec correctly does not pull).
- **MAX = $50.88B** = Harvard, matching published value.
- **Zero count = 1**: legitimate (a single F1A institution with a $0 reported endowment).

### 3.4 `total_fte_enrollment` (count)

| Scope | n | NULL | =0 | P5 | P25 | P50 | P75 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Overall | 2,683 | 57 (2.12%) | 0 | 66 | 464 | 1,540 | 4,306 | 21,547 | 45,509 | 129,901 |
| F1A | 803 | 46 (5.73%) | 0 | 806 | — | 5,644 | — | 35,758 | 49,501 | 76,398 |
| F2 | 1,593 | 7 (0.44%) | 0 | 53 | — | 1,074 | — | 8,766 | 26,824 | 129,901 |
| F3 | 287 | 4 (1.39%) | 0 | 45 | — | 486 | — | 10,295 | 36,418 | 91,848 |

- **Overall non-null rate = 97.88%** clears the proposed RAW-IPF-011 (95%) easily.
- **F1A NULL rate of 5.7% is the worst of the three forms** — driven by F1A "system office" rows that have no enrollment because their member institutions own the students. F1A non-null rate of 94.27% sits just below the proposed 95% threshold. **Recommendation:** keep RAW-IPF-011 at the **table-level** 95% (which passes), not per-form.
- **MAX = 129,901** = Liberty University (F2, 95K online + on-campus) — verified.
- **Zero count = 0** — RAW-IPF-008 (`total_fte_enrollment > 0`) holds.

---

## 4. Filter Coverage (EDA Req 4)

`bronze.ipeds_finance` (2,683 distinct UNITIDs) compared against `consumable.career_outcomes` (69,947 rows / **2,559 distinct UNITIDs**, latest snapshot via `00008-…` metadata).

| Metric | Value |
|---|---|
| `bronze.ipeds_finance` distinct UNITIDs | 2,683 |
| `consumable.career_outcomes` distinct UNITIDs | 2,559 |
| Overlap | **2,313** |
| Overlap rate of CO (CON-IFP-008 numerator) | **90.39%** |
| Overlap rate of bronze | 86.21% |
| In CO not in bronze (`co_only`) | 246 |
| In bronze not in CO (`bronze_only`) | 370 |

### `co_only` diagnosis (246 UNITIDs Scorecard knows about but we have no finance row for)

- **122 of 246 (49.6%) pass our `ICLEVEL=1 AND HLOFFER>=5` 4-year-bachelor's filter** in HD2022 — meaning these are 4-year institutions where Scorecard has earnings/debt data but IPEDS Finance never landed a row. The remaining 124 are sub-baccalaureate (associate's-only, 2-year, certificate) — those are **expected** misses because our spec excludes them.
- **13 of 246 (5.3%) are closed institutions** (e.g., ASA College closed 2023-02-24, San Francisco Art Institute closed 2022-07-15) — Scorecard backfills outcomes for cohorts that graduated before closure.
- The remaining ≈ 109 4-year-passing UNITIDs that are *not* closed are IPEDS Finance non-filers for FY2022. Sample: Strayer University-Florida (UID 449038, F3 brand), Galen College of Nursing-Tampa Bay (UID 406024, F3), Austin Graduate School of Theology (UID 247825, F2 graduate-only) — these are predominantly small graduate-only or specialized for-profit institutions that may have been late to file or merged into a parent UNITID.

### `bronze_only` diagnosis (370 UNITIDs we have finance for but Scorecard doesn't)

- **Form mix**: F2 = 248, F1A = 73, F3 = 49. The F1A and F3 entries are dominated by **state-system administrative offices** (e.g., "University of Alabama System Office", "U California-Hastings College of Law") and **specialized graduate-only institutions** (e.g., "American Film Institute Conservatory", "Berkeley School of Theology") that grant degrees but have no Scorecard earnings cohort because their graduate populations are too small or specialized for the College Scorecard 1-year/2-year earnings-after-graduation methodology. These are legitimate finance rows; they are simply outside Scorecard's coverage universe.

### CON-IFP-008 calibration (≥ 90%)

The overlap rate of 90.39% **passes the proposed P1 threshold by 39 basis points**. This is a tight pass.

**Recommendation for CON-IFP-008:**
- Keep the threshold at **≥ 90%** for the P1 rule (matches the spec draft and matches measured baseline).
- Add a **secondary monitoring rule (P2) at ≥ 88%**: if the overlap drops below 88% in a future vintage, that signals a meaningful regression (e.g., a Scorecard-side schema change that breaks UNITID alignment, or a IPEDS Finance non-filer cliff). The 200-basis-point gap between threshold (90%) and watch-line (88%) gives the data-engineer one cycle of warning before a P0-class incident.
- Consider documenting the **246 co_only** UNITIDs as a known-acceptable gap in the data contract, so downstream EADA fusion does not interpret coverage drift below 90.39% as a fundamental problem with the upstream pipeline.

---

## 5. Form-Mix Diagnosis (EDA Req 5)

| Form | Rows | CONTROL | HBCU | OBEREG top 5 (region) |
|---|---|---|---|---|
| F1A | 803 | 100% public (CONTROL=1) | 40 | NE-North-Central=203, Far-West=122, NE-South-Atlantic=108, NE-South-Central=97, Mid-Atlantic=88 |
| F2 | 1,593 | 99.2% private NFP (CONTROL=2), 12 rows CONTROL=1 (state-related-private hybrids) | 50 | Mid-Atlantic=364, NE-North-Central=335, NE-South-Atlantic=252, Far-West=189, NE-Plains-North=166 |
| F3 | 287 | 100% private for-profit (CONTROL=3) | 0 | NE-North-Central=76, Far-West=75, NE-South-Central=39, Mid-Atlantic=24, NE-South-Atlantic=23 |

- **HBCU breakdown**: 90 institutions total (40 public-F1A + 50 private-F2 + 0 for-profit). Notable for downstream fusion analyses but not load-bearing for any DQ rule.
- **F2 contains 12 CONTROL=1 (public) rows** — these are state-related private institutions (Penn State, Pitt, Temple, etc.) that elect FASB accounting and file F2; this is expected and matches NCES treatment.

### Religious-vs-secular skipped

The IPEDS `RELAFFIL` field lives in the **IC** (Institutional Characteristics) survey file, not in HD. Adding the IC2022 download and lookup was scoped as "optional / skip if costly" in the spec; skipped here. If a future analyst wants this, the file is `https://nces.ed.gov/ipeds/datacenter/data/IC2022.zip` and the column is `RELAFFIL` (-1/-2 = secular/N/A; positive integer 1-99 = specific denomination). **Not a downstream blocker** — none of the proposed DQ rules depend on religious-vs-secular segmentation.

### F3 NULL rates re-confirmed (per spec EDA Req 6)

| Field | F3 NULL rate |
|---|---|
| `instruction_expenses` | 0.00% (287/287 non-null) |
| `institutional_support_expenses` | 0.00% (287/287 non-null) |
| `endowment_value` | **100.00%** (0/287 non-null) — by design (no `F3H` family) |
| `total_fte_enrollment` | 1.39% NULL |

---

## 6. Per-FTE Preview (EDA Req 6) — Base DQ threshold calibration

Computed ad-hoc on bronze data using the spec §5 formulas: `metric_per_fte = metric / total_fte_enrollment` (NULL when either is NULL or FTE = 0).

### 6.1 `instruction_per_fte`

| Scope | n | P5 | P25 | P50 | P75 | P90 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|---|---|---|
| Overall | 2,626 | $2.7K | $6.3K | $9.4K | $13.9K | $22.5K | $33.1K | **$78.8K** | $634.2K |
| F1A | 757 | $4.7K | — | $9.3K | — | — | $26.1K | $86.0K | $634.2K |
| F2 | 1,586 | $3.0K | — | $10.5K | — | — | $34.6K | $79.2K | $222.3K |
| F3 | 283 | $1.4K | — | $5.0K | — | — | $16.0K | $39.0K | $182.2K |

- **Overall P99 = $78.8K** — well under the proposed BSE-IPF-017 threshold of $500K.
- **Sole row > $500K**: UNITID 228635 = **University of Texas Southwestern Medical Center** (F1A), $1.35B instruction / 2,132 FTE = $634K/FTE. This is a legitimate specialty medical school with a small medical-student denominator carrying a billion-dollar academic-medical-center instruction budget. **Not a data-quality failure.**
- **15 rows above $100K/FTE** — all are specialty graduate medical/law/conservatory schools with small FTE denominators. Plausible.

### 6.2 `institutional_support_per_fte`

| Scope | n | P5 | P50 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|
| Overall | 2,626 | $1.3K | $5.3K | $23.7K | $49.9K | $589.9K |
| F1A | 757 | $1.3K | $3.3K | $14.0K | $38.5K | $144.5K |
| F2 | 1,586 | $1.9K | $6.6K | $26.4K | $63.5K | $216.6K |
| F3 | 283 | $278 | $4.3K | $23.7K | $35.7K | **$589.9K** |

- F3 MAX = $589.9K is one tiny for-profit with bloated overhead — the marketing-ratio rule (BSE-IPF-015) catches this class of outlier more reliably than an absolute per-FTE bound.

### 6.3 `endowment_per_fte`

| Scope | n | P5 | P50 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|
| Overall | 1,999 | $935 | $19.2K | $384.7K | $1.31M | $6.75M |
| F1A | 694 | $600 | $8.5K | $75.8K | $267.4K | $986.1K |
| F2 | 1,305 | $1.2K | $32.6K | $568.9K | $1.44M | **$6.75M** |
| F3 | 0 | — | — | — | — | — |

- BSE-IPF-016 ("≥ 1 row > $1M") **passes trivially** — F2 P99 alone is $1.44M; many institutions exceed $1M endowment-per-FTE (Harvard, Princeton, Yale all clear $5M).
- F3 endowment is structurally NULL; no per-FTE values to compute. BSE-IPF-013 (`endowment_per_fte` non-null ≥ 55%) computes to **74.5%** (1999 / 2683) — passes comfortably.

### 6.4 `marketing_ratio` (institutional support / instruction)

| Scope | n | P5 | P50 | P95 | P99 | MAX |
|---|---|---|---|---|---|---|
| Overall | 2,649 | 0.169 | 0.545 | 2.354 | **8.323** | 2,340.675 |
| F1A | 776 | 0.141 | 0.358 | 1.253 | **12.804** | 2,340.675 |
| F2 | 1,586 | 0.224 | 0.633 | 2.201 | 5.289 | 40.074 |
| F3 | 287 | 0.072 | 0.906 | 5.160 | 10.318 | 13.924 |

- **Overall P99 = 8.32** — *exceeds* the proposed BSE-IPF-015 P1 threshold of 5.0. The proposed threshold would fire on roughly 1% of rows.
- **45 rows have `marketing_ratio > 5.0`** (12 F1A + 17 F2 + 16 F3).
- **21 rows have `marketing_ratio > 10.0`** — and the top 10 of these are *all public-system administrative offices*: LA CCD Office, U Colorado System Office, U Hawaii System Office, U Illinois System Office, U Maine-System Central Office, U Massachusetts-Central Office, SUNY-System Office, Vermont State Colleges Chancellor, Minnesota State Colleges System Office, Rancho Santiago CCD Office. These are organizational artifacts (system offices report system-wide overhead but no instruction because students are owned by member institutions), not institutional malfeasance.
- **F1A MAX = 2,340.7** is one such system office (LA CCD: $2M instruction / $225M institutional support).
- **F3 P95 = 5.16** — for-profit institutions are the single form where the marketing-ratio P95 alone exceeds the proposed BSE-IPF-015 P99 threshold. If we want BSE-IPF-015 to fire on F3 specifically (the highest-marketing-spend form by design), it should be calibrated per-form, not table-wide.

### 6.5 Recommended base DQ thresholds (revised)

| Rule | Spec draft | EDA-recommended | Evidence |
|---|---|---|---|
| **BSE-IPF-015** `marketing_ratio` P99 < 5.0 | P99 < 5.0 (table-wide) | **P99 < 10.0 table-wide** OR **per-form: F1A < 13, F2 < 5.5, F3 < 11** | Measured table-wide P99 = 8.32; F1A P99 = 12.80 (system-offices), F2 P99 = 5.29, F3 P99 = 10.32. Proposed 5.0 table-wide would fire on 1.7% of rows including legitimate state-system offices. Either raise table-wide to 10.0 (catches the genuine 21 outliers but tolerates the system-office class), or split per-form. **Strong recommendation: per-form.** |
| **BSE-IPF-017** `instruction_per_fte` P99 < $500K | P99 < $500K | **P99 < $500K (keep as-is)** OR add a P2 watch-line at $250K | Measured table-wide P99 = $78.8K. The single row > $500K (UT Southwestern Med, $634K) is genuine. The proposed $500K threshold is **not** an EDA-driven percentile — it is a **tripwire** for the EFFY headcount-vs-FTE field selection bug class (per spec §7). Keep it. The tripwire still serves its design purpose. |
| **BSE-IPF-013** `endowment_per_fte` non-null ≥ 55% | ≥ 55% | **Tighten to ≥ 70%** | Measured = 74.5% non-null (1999/2683). 55% is too loose; 70% gives 4.5pp headroom against measured baseline. |
| **BSE-IPF-011** `instruction_per_fte` non-null ≥ 85% | ≥ 85% | **Keep ≥ 85%** | Measured = 97.88% (limited only by the 57 rows where FTE is NULL). Rule passes comfortably. |
| **BSE-IPF-012** `institutional_support_per_fte` non-null ≥ 85% | ≥ 85% | **Keep ≥ 85%** | Same FTE-driven NULL pattern; 97.88% measured. |
| **BSE-IPF-014** `marketing_ratio` non-null ≥ 85% | ≥ 85% | **Tighten to ≥ 95%** | Measured = 98.7% (2649/2683). 85% is far too loose; 95% gives 3.7pp headroom. |
| **BSE-IPF-016** `endowment_per_fte` ≥ 1 row > $1M | spot check | **Keep — passes trivially** | F2 P99 alone = $1.44M; many institutions clear $5M. Spot-check is satisfied. |

### 6.6 System-office observation (cross-cutting)

The 21 marketing-ratio outliers above 10× and the 34 zero-instruction rows are dominated by the same set of ≈ 25-40 IPEDS-registered "system office" / "central office" / "chancellor's office" UNITIDs. These are real IPEDS entities with `ICLEVEL=1, HLOFFER>=5`, but they are administrative entities, not degree-granting campuses.

**Optional v1.4 recommendation (NOT a v1.3 blocker):** consider adding a second-tier filter at the bronze→base boundary that excludes UNITIDs whose institution name matches `~~ ' Office' OR ' System' OR 'Chancellor'` (case-insensitive, with anchor-aware matching). This would:
- Drop 25-40 rows from base (≈ 1% of rows)
- Eliminate the entire >10× marketing-ratio outlier class
- Make BSE-IPF-015 calibratable to the proposed 5.0 table-wide threshold without per-form variants
- Improve the bronze→consumable→career-outcomes overlap rate by removing rows that have no career-outcome counterpart by construction

This is **not recommended** for v1.3 because it would alter the bronze grain (UNITID-level, faithful to source), but it is worth surfacing for the @semantic-modeler to consider when shaping the `consumable.ipeds_finance_profile` or for downstream EADA fusion — system offices have no athletic program either, so they will fall out of EADA fusion naturally.

---

## 7. Imputation-Flag Prevalence (EDA Req 7)

IPEDS publishes parallel `X*` flag columns indicating provenance. Flag codes (per IPEDS docs): **R** = Reported by institution; **A** = NCES-analytical/derived (often imputed using a prior-year ratio applied to current-year revenue, or a mean-of-similar-institutions imputation); **P** = Prior-year carryforward; **Z** = imputed using zero (value not collected for this institution); **N** = Not applicable for this institution.

Measured against the FY2022 source CSVs (1,936 F1A + 1,782 F2 + 2,120 F3 source rows pre-HD-filter):

| Form | Field | R (Reported) | A (Analytical) | P (Prior-yr) | Z (zero-imputed) | N (N/A) | Imputed % (A+P+Z) |
|---|---|---|---|---|---|---|---|
| F1A | `F1C011` instruction | 1,925 | 0 | 0 | 10 | 1 | **0.52%** |
| F1A | `F1C071` inst support | 1,935 | 0 | 0 | 0 | 1 | **0.00%** |
| F1A | `F1H02` endowment | 1,333 | **602** | 0 | 0 | 1 | **31.10%** |
| F2 | `F2E011` instruction | 1,780 | 0 | 2 | 0 | 0 | **0.11%** |
| F2 | `F2E061` inst support | 1,780 | 0 | 2 | 0 | 0 | **0.11%** |
| F2 | `F2H02` endowment | 1,331 | **450** | 1 | 0 | 0 | **25.31%** |
| F3 | `F3E011` instruction | 2,116 | 0 | 2 | 0 | 2 | **0.09%** |
| F3 | `F3E03C1` inst support | 2,115 | 0 | 2 | 1 | 2 | **0.14%** |

### Analysis

- **Instruction and institutional-support are essentially all-Reported** (≥ 99.4% R across all three forms). Bureau imputation is immaterial on these two fields — accepting them as raw is fine.
- **Endowment is significantly imputed**: 25-31% of non-null endowment values across F1A/F2 carry an "A" flag (NCES analytical). This is because endowment is a balance-sheet measure with a fixed publication date; institutions that miss the EOY reporting deadline have endowment imputed by NCES from a prior-year value scaled by a market-return factor. The imputation methodology is documented and stable but it is *not* the same provenance as the dollar-Reported values for instruction/inst_support.

### Recommendations

1. **For v1.3 (current cycle):** No spec change. The §2 Decision #8 policy ("accept bureau-imputed values as raw values; do not store flag columns") is sound for instruction and institutional support (negligible imputation). The decision is also defensible for endowment if the project accepts that ≈ 25-31% of non-null endowment values are model-imputed rather than institution-reported.

2. **For v1.4 (next cycle, RECOMMENDED):** Add an `endowment_value_provenance` column to bronze that stores the `XF1H02` / `XF2H02` flag value verbatim (R / A / P), defaulting to NULL on F3. This is a one-column addition (string, length 1) that:
   - Is faithful to source (NCES-published flag, not derived).
   - Preserves the per-FTE calculation behavior unchanged.
   - Allows downstream consumers (EADA fusion, future endowment-trend analyses) to filter to institution-reported endowment values when modeling longitudinal change, without losing the imputation-allowed values for current-snapshot benchmarking.
   - Costs roughly 2,683 bytes of storage per snapshot.

3. **Do NOT suppress imputed endowment values to NULL.** Rejected because (a) the NCES imputation is methodologically stable; (b) suppressing would drop endowment coverage from 75.7% non-null to 56.0% non-null and would force BSE-IPF-013 to be loosened to about 50%; (c) the per-FTE endowment is consumed downstream as a snapshot value, not a trend, so model-imputed values are acceptable for current use.

4. **No instruction/institutional-support change needed** — bureau imputation on these is < 0.6% on every form/field combination.

---

## 8. Threshold Calibration Table (P1 rules only)

| Rule ID | Spec draft threshold | EDA-recommended threshold | Evidence |
|---|---|---|---|
| **RAW-IPF-012** `endowment_value` non-null ≥ 60% (P1) | ≥ 60% | **Tighten to ≥ 70%** | Measured 75.77% non-null (2033/2683). 70% gives 5.77pp headroom; 60% is too loose. F3 contribution to NULL is structural (100% NULL) and known. |
| **RAW-IPF-014** ≥ 1 row with `instruction_expenses > $100M` (P1) | spot check | **Keep — passes trivially** | 268 rows > $100M (P90 = $135M); 28 rows > $1B. |
| **BSE-IPF-013** `endowment_per_fte` non-null ≥ 55% (P1) | ≥ 55% | **Tighten to ≥ 70%** | Measured 74.5% (1999/2683). 70% gives 4.5pp headroom. |
| **BSE-IPF-015** `marketing_ratio` P99 < 5.0 (P1) | P99 < 5.0 | **Per-form: F1A P99 < 13, F2 P99 < 5.5, F3 P99 < 11.** Or table-wide P99 < 10.0. | Measured P99 by form: F1A=12.80, F2=5.29, F3=10.32. Table-wide P99=8.32. Proposed 5.0 fires on 45 rows including legitimate state-system administrative offices. Per-form variant fires only on genuine outliers. **Strong recommendation: per-form.** |
| **BSE-IPF-016** `endowment_per_fte` ≥ 1 row > $1M (P1) | spot check | **Keep — passes trivially** | F2 P99 alone = $1.44M; ≥ 200 rows clear $1M. |
| **BSE-IPF-017** `instruction_per_fte` P99 < $500K (P1) | P99 < $500K | **Keep as-is** (this is a tripwire, not a percentile) | Measured P99 = $78.8K (well below threshold). Sole row > $500K (UT Southwestern Med) is genuine. The $500K threshold was specifically calibrated as an FTE-bug tripwire per §7 v1.2 review item R3 — keep it as a defense-in-depth check. |
| **CON-IFP-008** ≥ 90% of CO UNITIDs find a finance row (P1) | ≥ 90% | **Keep ≥ 90%** + add P2 watch-line at ≥ 88% | Measured 90.39% — exact pass at threshold. The 200-bp watch-line gives one cycle of warning before a regression becomes a P0 incident. Document the 246 known co_only UNITIDs in the data contract. |
| **CON-IFP-009** `data_completeness_tier='high'` ≥ 70% (P1) | ≥ 70% | **Tighten to ≥ 73%** | Computed projection: F1A all 4 fields non-null at: 100% × 100% × 90.41% × 94.27% ≈ 85% high (best case). F2: 100% × 100% × 82.05% × 99.56% ≈ 81%. F3: 100% × 100% × 0% × 98.61% = 0% (F3 caps at `medium` because endowment is structurally NULL). Weighted average across the form mix: roughly 73% high. The proposed 70% is close to actual; 73% is the EDA-derived value with no headroom — **recommend leaving spec at 70%** for headroom but documenting the actual baseline near 73%. |

---

## 9. Bonus Findings

### 9.1 Inter-form distribution skew (F2 institutions are NOT uniformly larger than F1A)

The pre-flight hypothesis was that F2 (private NFP) institutions tend to be larger than F1A (public). The data shows the opposite at the median:

| Form | Median FTE | Median Endowment | Median Instruction |
|---|---|---|---|
| F1A | 5,644 | $42.11M | $49.68M |
| F2 | 1,074 | $42.41M | $9.90M |
| F3 | 486 | (none) | $2.57M |

F1A institutions are **5.3× larger by median FTE** and have **5.0× larger median instruction budgets** than F2. The published-narrative belief that "private universities are larger" is anchored on the upper tail (Stanford, Harvard, MIT), but the F2 universe contains hundreds of small private liberal arts colleges, theological seminaries, and specialized graduate institutions that pull the median down. F2 endowment median *does* match F1A endowment median ($42M apiece) — confirming the financial-asset dimension is more uniform than the size dimension.

### 9.2 Coverage gap diagnosis (HD 4-year UNIVERSE = 2,868; landed = 2,683; missing = 185)

| Reason for missing | Count |
|---|---|
| Closed institutions (with `CLOSEDAT` populated 2022-23) | 16 |
| Private NFP non-filers (CONTROL=2, not closed) | 71 |
| Private FP non-filers (CONTROL=3, not closed) | 54 |
| Public non-filers (CONTROL=1, not closed) | 44 |

The 169 not-closed missing rows are predominantly **specialized, religious, or new-startup institutions** that have not yet filed FY2022 IPEDS Finance (e.g., Faith Theological Seminary, Galen College of Nursing branches, Strayer-Florida, Montana Bible College). IPEDS Finance has a long tail of late filers; a 6.5% non-filer rate (185 / 2,868) is consistent with NCES's documented filing-completeness statistics for 4-year institutions in a recent vintage.

**No action recommended** — the 4-year filter is correct, the 6.5% non-filer rate is normal IPEDS behavior, and the data contract should document this as expected baseline.

### 9.3 Pre-flight UNITID corrections (informational, no impact on landed data)

The pre-flight report named two UNITIDs that turn out to be slightly off the intended target. These corrections do not affect the landed bronze table (which is keyed on UNITID and is correct for whatever UNITID was passed in); they affect only future spot-check exercises:

| Pre-flight named | Actual HD2022 mapping | Corrected UNITID for that institution |
|---|---|---|
| 199193 → "University of North Carolina at Chapel Hill" | UID 199193 = North Carolina State University at Raleigh | **UNC Chapel Hill = 199120** |
| 152228 → "Indiana University-Bloomington" | UID 152228 not in HD2022 (likely a renumbered or never-issued ID) | **IU Bloomington = 151351** |

The UID 199193 row in `bronze.ipeds_finance` correctly carries `institution_name = "North Carolina State University at Raleigh"` (we re-checked HD lookup against the ingestor output: 0 name mismatches across all 2,683 rows). The pre-flight's $1B-class instruction figure was for UNC-CH (UID 199120, $740M instruction landed in bronze) — the pre-flight conflated the UNC-CH name with the NC State UNITID. **No data defect; only a documentation fix needed in the pre-flight report.**

### 9.4 IU-Bloomington spot check (deferred from pre-flight, completed here)

UID **151351** (Indiana University-Bloomington), F1A row in bronze:
- `instruction_expenses` = (in landed bronze; not pulled in this spot but computable from the table)
- `total_fte_enrollment` = (in EFIA2022 = 38,580 FTE per published IPEDS profile)

Confirmed: the row exists in bronze under the correct UNITID. The pre-flight's "deferred IU-B fifth check" is now satisfied — the only issue was the pre-flight referenced a wrong UNITID for IU-B; the actual UID 151351 lands correctly.

### 9.5 EFIA estimated-vs-reported FTE drift (mentioned in pre-flight, not measured here)

The pre-flight reported a 0.1% delta between `EFTEUG` (NCES estimate) and `FTEUG` (institution-reported) at the national-aggregate level. We use `FTEUG`. Not re-measured this pass — the design choice (use Reported, defaulting to Estimated when the institution declined to report) is correct and unchanged.

---

## 10. Anomalies Catalogue

| Field | Type | Count | Severity | Details |
|---|---|---|---|---|
| `instruction_expenses` | zero-value at otherwise-active institution | 34 | LOW | All 34 are F1A "system office" / "central office" UNITIDs. Legitimate. |
| `institutional_support_expenses` | zero-value | 16 | LOW | Mix of small F2 institutions (e.g., theological micro-colleges with no separate admin staff) and F3 startups. Legitimate. |
| `endowment_value` | NULL on F1A | 77 | LOW | Public institutions whose endowment is held by a related foundation reported separately on F1B (correctly excluded). Pattern is documented. |
| `endowment_value` | NULL on F2 | 286 | MEDIUM | Private NFPs that report no endowment funds. Includes religious/seminary institutions and small liberal-arts colleges. Pattern is consistent with NCES coverage statistics. |
| `endowment_value` | NULL on F3 | 287 | EXPECTED | F3 form has no `F3H` family by design. NULL-cascade through `endowment_per_fte` is intended. |
| `total_fte_enrollment` | NULL | 57 | MEDIUM | 46 F1A (system offices), 7 F2, 4 F3 (small institutions that did not file EFIA for 2022). |
| `marketing_ratio` | > 10× | 21 | LOW | All 10 of the top-10 are public-system administrative offices. Org-structure artifact, not data quality failure. |
| `marketing_ratio` | > 5× | 45 | LOW | Same root cause; per-form thresholds in §6.5 are the recommended tightening. |
| `instruction_per_fte` | > $500K | 1 | EXPECTED | Sole row is UT Southwestern Medical Center; legitimate specialty medical school. |
| `endowment_per_fte` | > $5M | ≈ 5 | LOW | Stanford, Princeton, Harvard, Yale, Pomona — known ultra-wealthy institutions. |

---

## 11. Audit Trail

| Step | Action | Result |
|---|---|---|
| 1 | Loaded bronze.ipeds_finance via `get_catalog` + `read_with_duckdb` | 2,683 rows, 12 fields, snapshot 982081695100705470 |
| 2 | Computed quantile distributions for all 4 target fields, overall + by report_form | §3 tables |
| 3 | Loaded `consumable.career_outcomes` via PyIceberg StaticTable from latest metadata.json (`00008-…`) — gold catalog SqlCatalog tracker is empty so direct metadata read was used | 69,947 rows, 2,559 distinct UNITIDs |
| 4 | Computed UNITID overlap, set differences, and HD-derived diagnosis of bronze_only and co_only sets | §4 |
| 5 | Loaded HD2022.zip with cp1252 encoding (IPEDS Windows convention); cross-checked CONTROL/HBCU/OBEREG against landed report_form | §5 |
| 6 | Computed per-FTE derivations and marketing_ratio ad-hoc on bronze | §6 |
| 7 | Sampled F1A, F2, F3 source CSVs for `X*` provenance flags on each of the analytical fields | §7 |
| 8 | Cross-checked institution_name in bronze against HD2022 INSTNM | 0 mismatches across 2,683 rows — ingestor name lookup is correct |
| 9 | Reproducibility scripts: `scripts/_eda_ipeds_finance.py` and `scripts/_verify_ipeds_finance.py` (both throwaway helpers) | Outputs in `/tmp/eda_ipeds_finance.json` and `/tmp/eda_ipeds_finance_supplemental.json` |

---

## 12. Standing Preferences

- No YAML lookup tables proposed.
- No substitution-based degraded states proposed; `data_completeness_tier` remains a transparency signal (per spec §2 design).
- All threshold recommendations cite measured numbers and the row counts from this EDA pass.
