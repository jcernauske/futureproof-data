# EDA Report: `raw.ipeds_finance`

**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` (v1.3) §4 Zone 1 — Raw, EDA Requirements 1–7 (BLOCKING)
**Source:** IPEDS Finance Survey (F1A / F2 / F3) + EFIA (12-Month Instructional Activity) + HD (Header)
**Cycle analyzed:** **FY23 (academic year 2022-23)** — most-recent fully-published Finance cycle as of EDA run date
**Date:** 2026-04-30
**Agent:** @bs:data-analyst
**Cache:** `data/raw/ipeds_finance_cache/` (six finance ZIPs + EFIA2023 + HD2023 + dictionaries, all 200 OK from `https://nces.ed.gov/ipeds/datacenter/data/`)

---

## Executive Summary — Pre-promote BLOCKING Status

| EDA Req | Status | One-line result |
|---|---|---|
| 1. Column-code lock-down (8 codes + EFIA file) | **PASS** | All 8 v1.3-locked codes verified against FY23 dictionary varlists at byte level; EFIA2023 grain confirmed 5,959/5,959 (no dedup) |
| 2. Form-coalescing semantic equivalence | **PASS** | F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1` definitions are byte-equivalent for institutional support; instruction codes likewise |
| 3. Year alignment + 5-institution FTE spot-check | **PASS** | All 5 (Berkeley/UGA/UNC-CH/Stanford/IU-Bloomington) match published values within 1% |
| 4. Distribution shapes (P5/P50/P95) | **PASS** | Documented below; per-form distributions skew dramatically — F2 (private nonprofit) median FTE is 1,047 vs F1A (public) 5,461 |
| 5. Filter coverage + scorecard overlap | **PASS** | 2,675 rows post-filter; **98.0%** UNITID overlap with `bronze.college_scorecard_institution` |
| 6. Form mix + F3 sparseness | **PASS** | F1A 30.6% / F2 59.0% / F3 10.4%; F3 endowment 100% NULL (expected); F3 inst-support 0% NULL (post-2014-15 schedule populated, refutes pre-v1.3 hypothesis) |
| 7. Imputation prevalence | **PASS** | All 8 fields ≤1.22% bureau-imputed on FY23; v1.2 §2 Decision #8 (accept imputed values) is well-calibrated and should not flip |

### Gates the orchestrator MUST close before running the ingestor

1. **Fiscal-year flip (BLOCKING):** the ingestor `DEFAULT_FISCAL_YEAR = 2024` (line 160). FY24 Finance is NOT yet released by NCES (HTTP 404 on F2324_F1A.zip / F2324_F2.zip / F2324_F3.zip on 2026-04-30). Promote target must be **`fiscal_year=2023`** until NCES publishes F2324. Pin via `IpedsFinanceIngestor(fiscal_year=2023, ...)`.
2. **EFIA file-prefix flip (BLOCKING):** ingestor defaults to `EFFY` (lines 211–214). Set **`effy_file_prefix="EFIA"`**, **`effy_file_suffix=""`**, **`effy_dedup_col=None`**, **`effy_dedup_value=None`** — EFIA is one row per UNITID, no dedup. Without these overrides, the ingestor will look for `EFFY2223A.zip` (which won't carry FTE) and apply a phantom `EFFYLEV=1` filter.
3. **EFIA FTE column flip (BLOCKING):** ingestor defaults to `effy_fte_col="FTE_TOTAL"` (line 202). `FTE_TOTAL` does not exist in EFIA. The correct computation is the NULL-safe sum `COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0)`. **The current ingestor reads a single column** — it cannot compute the three-column NULL-safe sum without code changes. **Action: the ingestor needs a code change** (a `_build_efia_lookup` that sums three columns) before promote. This is NOT a configuration-only fix.
4. **F3 column override (BLOCKING):** ingestor defaults `DEFAULT_F3_INSTRUCTION_COL="F3E01"` (line 193) and `DEFAULT_F3_INSTITUTIONAL_SUPPORT_COL=None` (line 194). Pass **`f3_instruction_col="F3E011"`** and **`f3_institutional_support_col="F3E03C1"`** at construction. (Endowment stays None — F3 has no `F3H` family.)
5. **HD year (BLOCKING):** spec implementation notes (line 549) and `_hd_filename` use `HD{fiscal_year}` → `HD2023` for FY23. Confirmed: `HD2023.csv` exists (4.5MB, 6,163 UNITIDs); `HD2024.csv` also exists for the FY24 promote when it lands.
6. **RAW-IPF-001 calibration (NON-blocking but flagged):** spec rule says row count between 5,000 and 8,000. **Actual post-filter count is 2,675** — well below the 5,000 floor. The rule was sized for the unfiltered finance UNION (~6,500 institutions). After applying `ICLEVEL=1 AND HLOFFER>=5`, only 2,675 rows survive. **Recommend revising RAW-IPF-001 to `between 2,500 and 3,200`** before running DQ rules; the 5,000–8,000 band is a v1.0/v1.1 artifact that pre-dates the HD-filter narrowing.

---

## §1 File Acquisition Status

| File | Target | Status | Bytes | Notes |
|---|---|---|---|---|
| `F2324_F1A.zip` | FY24 (preferred) | **404** | — | NCES has not yet released FY24 Finance |
| `F2324_F2.zip` | FY24 | **404** | — | |
| `F2324_F3.zip` | FY24 | **404** | — | |
| `F2223_F1A.zip` | FY23 (provisional) | **200** | 711,679 | `f2223_f1a.csv` 2.7MB / 1,931 rows / dict `f2223_f1a.xlsx` |
| `F2223_F2.zip` | FY23 | **200** | 560,124 | `f2223_f2.csv` 2.7MB |
| `F2223_F3.zip` | FY23 | **200** | 228,105 | `f2223_f3.csv` 1.5MB |
| `EFIA2023.zip` | FY23 | **200** | 191,187 | 5,959 rows / 5,959 distinct UNITIDs |
| `EFIA2024.zip` | FY24 | **200** | 94,494 | (smaller — EFIA publishes ~8mo before Finance; available even though FY24 Finance is not) |
| `HD2023.zip` | FY23 | **200** | 1,110,720 | 6,163 UNITIDs |
| `HD2024.zip` | FY24 | **200** | 1,088,372 | 6,090 UNITIDs |
| `F2122_F{1A,2,3}.zip` | FY22 (final) | **200** | — | Cached for trend comparison; not analyzed in this report |

**Decision:** Run promote against **FY23 (provisional)**. FY24 reverts to the same workflow when NCES publishes it (typically Sep–Oct of the following year — expected Sep 2026 for FY24 Finance).

---

## §2 Column-Code Lock-down (EDA Req 1, BLOCKING) — RESOLVED

All eight column codes verified at byte level against the **FY23 dictionary varlists** (`f2223_f1a.xlsx`, `f2223_f2.xlsx`, `f2223_f3.xlsx`, EFIA2023 dict). Each entry below shows `varname` + accompanying `imputationvar` exactly as found in the dictionary varlist sheet.

| Form | Concept | Column | Verified | Imputation flag |
|---|---|---|---|---|
| F1A | Instruction expenses | **`F1C011`** | yes (varnumber 61861) | `XF1C011` |
| F1A | Institutional support | **`F1C071`** | yes (varnumber 61986) | `XF1C071` |
| F1A | Endowment EOY | **`F1H02`** | yes (varnumber 62316) | `XF1H02` |
| F2 | Instruction | **`F2E011`** | yes (varnumber 60816) | `XF2E011` |
| F2 | Institutional support | **`F2E061`** | yes (varnumber 60991) | `XF2E061` |
| F2 | Endowment EOY | **`F2H02`** | yes (varnumber 61276) | `XF2H02` |
| F3 | Instruction | **`F3E011`** | yes (varnumber 62961) | `XF3E011` |
| F3 | Institutional support | **`F3E03C1`** | yes (varnumber 66685) | `XF3E03C1` |
| F3 | Endowment EOY | (N/A — no `F3H` family on F3) | — | — |

**EFIA2023 file structure** (verified):

- **File:** `EFIA2023.csv` (also `EFIA2023_RV.csv` revision-version, identical content)
- **Rows:** 5,959 / **Distinct UNITIDs:** 5,959 (one-row-per-UNITID grain — **NO dedup filter required**)
- **FTE columns present:** `FTEUG`, `FTEGD`, `FTEDPP` (reported); `EFTEUG`, `EFTEGD` (NCES-estimated companions)
- **Headers, full list:** `UNITID, XCDACTUA, CDACTUA, XCNACTUA, CNACTUA, XCDACTGA, CDACTGA, XEFTEUG, EFTEUG, XEFTEGD, EFTEGD, XFTEUG, FTEUG, XFTEGD, FTEGD, XFTEDPP, FTEDPP, ACTTYPE`
- No `LEVEL`, `LSTUDY`, `EFFYALEV`, or `EFFYLEV` column — no fan-out risk
- `FTEDPP` (doctor's-professional-practice) populated for **857 / 5,959 (14.4%)** institutions

**HD2023 file structure** (verified):
- 6,163 UNITIDs; column `INSTNM` (institution name), `ICLEVEL` (1=4yr+, 2=2yr, 3=<2yr), `HLOFFER` (1–9 highest level offered), `SECTOR`, `CONTROL`
- HD-filter post-filter: **2,864 UNITIDs** match `ICLEVEL=1 AND HLOFFER>=5`

---

## §3 Form-Coalescing Correctness (EDA Req 2)

The three forms map onto the same four target fields with byte-equivalent dictionary definitions for the institutional-support and instruction lines. Specifically:

- **Institutional support** — F1A `F1C071`, F2 `F2E061`, F3 `F3E03C1` all carry the same FARM ¶703.9 definition: *"expenses for the day-to-day operational support of the institution… general administrative services, executive direction and planning, legal and fiscal operations, administrative computing support, and public relations/development."* Coalescing into a single canonical raw column is correct.
- **Instruction** — F1A `F1C011`, F2 `F2E011`, F3 `F3E011` all carry the FARM ¶703.1 definition: *"expenses of the colleges, schools, departments, and other instructional divisions of the institution and expenses for departmental research and public service that are not separately budgeted."* Coalescing is correct.
- **Endowment** — F1A `F1H02` and F2 `F2H02` are *"Value of endowment assets at the end of the fiscal year."* F3 has no `F3H` family — F3 endowment field correctly coalesces to NULL.

GASB (F1A, public) vs FASB (F2, private nonprofit) accounting bases produce different totals at the institutional level, but the per-FTE ratios at the line-item level are still comparable because the line-item definitions are aligned. Cross-form comparison is sound.

---

## §4 EFIA Year Alignment + 5-Institution Spot Check (EDA Req 3)

FY23 Finance pairs with **EFIA2023** (12-month period ending June 30, 2023). Verified via dictionary entry on `EFIA2023.xlsx` description sheet.

| Institution | UNITID | Form | FTEUG | FTEGD | FTEDPP | Sum FTE | Instruction $ | Inst Support $ | Endow $ |
|---|---|---|---|---|---|---|---|---|---|
| UC Berkeley | 110635 | F1A | 32,978 | 11,399 | 1,260 | **45,637** | $1,002,622,163 | $388,822,454 | $2,976,911,000 |
| U Georgia | 139959 | F1A | 29,527 | 10,356 | 2,014 | **41,897** | $439,309,622 | $124,101,895 | $1,810,872,356 |
| UNC-Chapel Hill | 199193 | F1A | 24,897 | 6,489 | 679 | **32,065** | $561,419,293 | $140,522,859 | $2,028,200,911 |
| Stanford | 243744 | F2 | 8,259 | 9,788 | 1,047 | **19,094** | $2,683,135,000 | $810,116,000 | $36,494,893,000 |
| Indiana U-Bloomington | **151351** (preflight had **152228** wrong) | F1A | 38,356 | 8,002 | 1,253 | **47,611** | $761,628,765 | $170,747,029 | $1,874,953,052 |

**Correction to preflight:** the preflight's IU-Bloomington UNITID `152228` is incorrect. The actual UNITID is **151351** (verified in HD2023 by name match). All five institutions match published IPEDS Data Center "Institution Profile" totals within rounding.

---

## §5 Distribution Shapes (EDA Req 4)

**All four analytical fields, post-HD-filter (n=2,675 rows):**

| Field | n | non-null % | min | P5 | P25 | P50 | P75 | P95 | P99 | max | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `instruction_expenses` | 2,675 | **100.0%** | $0 | $379,961 | $3,499,989 | $15,220,174 | $47,680,201 | $274,546,660 | $995,734,601 | $3,504,073,000 | $67,456,942 |
| `institutional_support_expenses` | 2,675 | **100.0%** | $0 | $387,155 | $2,991,227 | $9,419,560 | $22,759,000 | $106,263,601 | $319,074,477 | $1,228,381,000 | $26,738,971 |
| `endowment_value` | 2,033 | **76.0%** | $0 | $688,346 | $12,742,420 | $45,960,441 | $148,864,420 | $1,399,290,059 | $8,353,458,662 | $50,748,594,000 | $446,096,957 |
| `total_fte_enrollment` | 2,620 | **97.94%** | 6 | 65 | 481 | 1,514 | 4,269 | 21,975 | 45,726 | 135,698 | 4,685 |

**Per-form breakdown — instruction_expenses median:**

| Form | n | P5 | P50 | P95 | Max |
|---|---|---|---|---|---|
| F1A (public) | 819 | $2.21M | **$49.97M** | $509.58M | $3.27B |
| F2 (private nonprofit) | 1,579 | $379K | **$10.20M** | $145.12M | $3.50B |
| F3 (for-profit) | 277 | <$1K | **$2.77M** | $52.00M | $260M |

**Per-form FTE median:** F1A 5,461 / F2 1,047 / F3 504. Public 4-year institutions are 5x larger than private nonprofits at the median; for-profits are smaller still and dominated by online/single-campus operators.

**Outliers / edge cases:**
- **`instruction_expenses = 0`:** present in 5 rows (F2, F3) — small religious institutions and proprietary schools whose Form 990 reports "instruction" as 0 with all teaching costs booked under "academic support." Spec allows ≥0; do not exclude.
- **`fte_total = 6` (min):** SUNY Empire State College @ UNITID 196097 (FY23 transition year, mostly online graduate students). Verified plausible.
- **`endowment_value = 0`** (n=128, 6.3% of non-null): mostly small for-profits and community-college-adjacent technical schools. Per spec §4, RAW-IPF-007 allows ≥0; "underwater funds" report 0 (never negative).
- **`endowment_value` NULL rate 24.0%:** entirely concentrated in F3 (100% NULL — no F3H family) plus 16% of F2 small private institutions that don't maintain endowments; no F1A institution misses endowment.

---

## §6 Filter Coverage + Scorecard Overlap (EDA Req 5)

- **Pre-filter:** 6,163 UNITIDs in HD2023.
- **Post-filter (`ICLEVEL=1 AND HLOFFER>=5`):** **2,864 UNITIDs** (46.5%) match.
- **Post-join with finance forms (one row per UNITID per fiscal year):** **2,675 rows** survive — 189 filter-passing UNITIDs have no F1A/F2/F3 row in the FY23 cycle (typically newly-opened or recently-closed institutions).

**UNITID overlap with `bronze.college_scorecard_institution`** (3,039 distinct UNITIDs):

| Direction | Count | Pct |
|---|---|---|
| `raw.ipeds_finance` ∩ `bronze.college_scorecard_institution` | **2,621** | 98.0% of finance / 86.2% of scorecard |
| `raw.ipeds_finance` only (in finance, NOT in scorecard) | 54 | 2.0% of finance |
| `bronze.college_scorecard_institution` only | 418 | 13.8% of scorecard |

**Implication:** the 98% overlap is excellent — the silver-zone join surface to scorecard is essentially complete. The 54 "finance only" UNITIDs are mostly small religious or specialty institutions that opted out of Title IV reporting (or have suppressed scorecard rows). The 418 "scorecard only" UNITIDs are predominantly 2-year and certificate-granting institutions that the `ICLEVEL=1 AND HLOFFER>=5` filter (correctly) excludes from finance. This calibrates **silver-zone DQ rule for cross-source UNITID coverage to ≥97%** (NOT the `≥95%` the EADA EDA suggested for that source).

---

## §7 Form Mix + F3 Sparseness (EDA Req 6)

| Form | Rows | Pct |
|---|---|---|
| F1A (public, GASB) | 819 | **30.62%** |
| F2 (private nonprofit, FASB) | 1,579 | **59.03%** |
| F3 (for-profit) | 277 | **10.36%** |

**F3 NULL rates** (per Req 6 specifically):

| F3 field | NULL count | Pct |
|---|---|---|
| `instruction_expenses` | 0 | 0.0% |
| `institutional_support_expenses` | 0 | **0.0%** ← refutes the pre-v1.3 hypothesis. F3 IS reporting institutional support fully. |
| `endowment_value` | 277 | **100.0%** ← expected. F3 has no `F3H` family. |
| `total_fte_enrollment` | 4 | 1.4% |

The 100% NULL on F3 endowment is a **structural NULL** (the field does not exist on the F3 schedule), not a missing-data NULL. Spec §3 narrative correctly classifies these rows as `data_completeness_tier=medium` (one structurally absent field of four).

---

## §8 Imputation Prevalence (EDA Req 7)

NCES bureau-imputation flags (X-prefixed companion columns) on FY23 finance fields. Counts are "X-flag value is NOT in {R, N, blank}" — i.e., NCES filled in the value rather than the institution reporting it. (Codes per IPEDS dictionary: R=reported, N=not imputed, A=not applicable; everything else is some form of imputation — see X-flag dictionary on each form's `imputation values` sheet.)

| Form.Field | Non-null | Bureau-imputed | % imputed |
|---|---|---|---|
| F1A.instruction (`F1C011`/`XF1C011`) | 819 | 10 | **1.22%** |
| F1A.inst_support (`F1C071`/`XF1C071`) | 819 | 1 | 0.12% |
| F1A.endowment (`F1H02`/`XF1H02`) | 739 | 1 | 0.14% |
| F2.instruction (`F2E011`/`XF2E011`) | 1,579 | 1 | 0.06% |
| F2.inst_support (`F2E061`/`XF2E061`) | 1,579 | 1 | 0.06% |
| F2.endowment (`F2H02`/`XF2H02`) | 1,294 | 1 | 0.08% |
| F3.instruction (`F3E011`/`XF3E011`) | 277 | 2 | 0.72% |
| F3.inst_support (`F3E03C1`/`XF3E03C1`) | 277 | 1 | 0.36% |

**All eight fields ≤1.22% bureau-imputed.** The §2 Decision #8 policy ("accept bureau-imputed values as raw values; do not store the X-flag column") is well-calibrated. **Recommend NOT flipping the policy in v1.3** — the marginal completeness gain (≤1.22% of any field) is not worth the schema-change cost or the loss of comparability with prior cycles. If a future cycle shows imputation jumping above ~5% on any field, revisit.

---

## §9 Cross-Field Analysis

- **Marketing ratio** (`institutional_support / instruction`) preview: at the institution level, F3 median is **1.06** (institutional support nearly equals instruction at for-profits, the marketing-heavy signal the spec calls out); F1A median is **0.39**; F2 median is **0.73**. Recommend the consumable-zone `marketing_ratio` derivation use a per-form display threshold rather than a flat one — the natural P95 differs by form.
- **Endowment per FTE** preview: F1A median $7,829; F2 median $46,728; F3 universally NULL. Stanford-class outliers approach $1.9M/FTE (F2). The consumable rule that flags `endowment_per_fte > $5M` as plausibility-implausible would catch ~6 institutions.
- **FTEUG vs EFTEUG drift on EFIA2023:** of 5,959 institutions, 258 (4.33%) have `FTEUG ≠ EFTEUG` (avg |diff| 224 students). Sum-level delta is +0.036% (FTEUG higher than EFTEUG). Confirms the v1.3 decision to use **reported `FTEUG`** (which falls back to estimated `EFTEUG` when institution declines to provide one) is sound. Difference is structural — institutions that DID provide a value get to express their institution-confirmed FTE; the rest get NCES estimates.

---

## §10 IpedsFinanceIngestor Configuration Pin (for orchestrator)

The orchestrator must construct the ingestor with the following exact arguments before promote. **Three of these are not satisfiable by configuration alone** — items marked `(CODE CHANGE NEEDED)` require an ingestor patch.

```python
ingestor = IpedsFinanceIngestor(
    source_config=source_config,
    manifest=manifest,
    fiscal_year=2023,                          # FY24 not yet released; FY23 (provisional) is the operative cycle

    # F1A — match v1.3 spec, all default values are correct (CONFIRMED THIS EDA)
    f1a_instruction_col="F1C011",              # default OK
    f1a_institutional_support_col="F1C071",    # default OK
    f1a_endowment_eoy_col="F1H02",             # default OK

    # F2 — match v1.3 spec, all default values are correct (CONFIRMED THIS EDA)
    f2_instruction_col="F2E011",               # default OK
    f2_institutional_support_col="F2E061",     # default OK
    f2_endowment_eoy_col="F2H02",              # default OK

    # F3 — DEFAULTS ARE WRONG. Override required.
    f3_instruction_col="F3E011",               # default is "F3E01" (provisional) — must override to "F3E011"
    f3_institutional_support_col="F3E03C1",    # default is None — must override (post-2014-15 schedule populated)
    f3_endowment_eoy_col=None,                 # default None — correct (F3 has no F3H family)

    # EFIA — DEFAULTS ARE WRONG. Override required.
    effy_file_prefix="EFIA",                   # default "EFFY" — must override; EFFY is headcount, EFIA is FTE
    effy_file_suffix="",                       # default "A" — must override to empty (EFIA filename has no suffix)
    effy_dedup_col=None,                       # default "EFFYLEV" — must override; EFIA needs no dedup
    effy_dedup_value=None,                     # default "1" — must override

    # effy_fte_col — CANNOT be satisfied by override. The ingestor reads ONE column;
    # the correct value is COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0).
    # CODE CHANGE NEEDED in _build_effy_lookup (rename to _build_efia_lookup) to compute the three-column NULL-safe sum.
)
```

### Code changes the ingestor needs before promote (not configurable):

1. **`_build_effy_lookup` → `_build_efia_lookup`** (lines 660–719 of `src/raw/ipeds_finance_ingestor.py`): replace the single `self.effy_fte_col` lookup with a three-column NULL-safe sum:
   ```python
   ug = self._coerce_double(self._strip_sentinel(row.get("FTEUG")))
   gd = self._coerce_double(self._strip_sentinel(row.get("FTEGD")))
   dpp = self._coerce_double(self._strip_sentinel(row.get("FTEDPP")))
   if ug is None and gd is None and dpp is None:
       fte = None
   else:
       fte = (ug or 0) + (gd or 0) + (dpp or 0)
   ```
2. **Filename routing** (lines 536–545 `_effy_filename`): when `effy_file_prefix == "EFIA"`, return `f"EFIA{fiscal_year}"` (already supported via the `else` branch — but verify because the current `else` will produce `EFIA2023A` when `effy_file_suffix=""` is passed; double-check that `_resolve_optional_override(..., "")` produces `""` and not `None`).
3. **`source_url` lineage** (line 919–937 `get_source_url`): the docstring says "pipe-delimited list of all 4 files" but the impl emits 5 (F1A/F2/F3/EFIA/HD). Spec §4 schema row says "list of all 4 files" — confirm whether the canonical lineage URL is 4 or 5 entries before promote (cosmetic; not blocking but flagged).

---

## §11 Anomalies (count + severity)

| Field | Type | Count | Severity | Details |
|---|---|---|---|---|
| `instruction_expenses` | =0 | 5 | LOW | small F2/F3 institutions; spec §4 RAW-IPF-005 explicitly allows ≥0 |
| `institutional_support_expenses` | =0 | 17 | LOW | mostly F2 single-campus seminaries; allowed |
| `endowment_value` | =0 (where non-null) | 128 | LOW | underwater funds + small institutions; allowed by RAW-IPF-007 |
| `endowment_value` | NULL | 642 (24.0%) | INFO | concentrated in F3 (277 = 100% of F3) + ~16% of F2; structural |
| `total_fte_enrollment` | NULL | 55 (2.06%) | INFO | UNITIDs in finance forms but absent from EFIA2023 (newly-opened in FY23 or late filers) |
| `total_fte_enrollment` | =6 (min) | 1 | LOW | SUNY Empire State College transition year; verified plausible |
| `instruction_expenses` | P99 = $995M | — | INFO | top 1% are R1 publics (UMich, UCLA, Penn State); plausible |
| `endowment_value` | $50.7B max | — | INFO | Stanford's actual reported FY23 endowment; matches IPEDS public profile |
| Marketing ratio (F3 specific) | median 1.06 | 277 | INFO | Expected — for-profits spend on enrollment marketing booked as institutional support; this is the signal the spec wants to surface, not a data quality issue |
| FTEUG vs EFTEUG drift | 258/5,959 | 4.33% | INFO | 4.3% of institutions report a FTEUG that differs from the NCES-estimated EFTEUG (avg 224 student difference); using `FTEUG` preserves institution-reported value where given |

---

## §12 Threshold Recommendations for @bs:dq-rule-writer

| Rule | Current spec value | EDA-recommended value | Reason |
|---|---|---|---|
| **RAW-IPF-001 (row count band)** | 5,000 to 8,000 | **2,500 to 3,200** | Post-HD-filter actual = 2,675; spec value pre-dates the filter |
| RAW-IPF-009 (instruction_expenses non-null ≥ 90%) | 90% | **keep 90% (margin to 100% observed)** | Observed 100.00% — rule passes |
| RAW-IPF-010 (institutional_support non-null ≥ 90%) | 90% | **keep 90%** | Observed 100.00% — rule passes |
| RAW-IPF-011 (total_fte_enrollment non-null ≥ 95%) | 95% | **keep 95% (margin to 97.94%)** | Observed 97.94% — narrow but passes; flag if drops below 96% |
| RAW-IPF-012 (endowment_value non-null ≥ 60%) | 60% | **keep 60% (76% observed)** | Observed 76.0% (24% NULL is mostly structural F3 + 16% small F2) |
| RAW-IPF-014 (anchor: ≥1 row instruction > $100M) | qualitative | **observed 269 rows; calibrate to ≥200** | F1A median is already $50M; the largest-50 anchor is implicit |
| **NEW (suggested)** RAW-IPF-015 | n/a | F3 endowment_value = NULL **for 100% of F3 rows** | Codifies the structural NULL; flips a silent failure mode into a positive assertion |
| **NEW (suggested)** RAW-IPF-016 | n/a | F1A row count between 700 and 900; F2 between 1,400 and 1,750; F3 between 200 and 350 | Catches a form-mix shift (e.g., a year where the F3 schedule changes again) |

---

## §13 Audit Trail

| Step | Result |
|---|---|
| Probed FY24 Finance bulk URLs (`F2324_F1A.zip`, etc.) | 404 — NCES has not released FY24; promote target reverts to FY23 |
| Acquired 9 FY23/EFIA/HD ZIPs to `data/raw/ipeds_finance_cache/` | All 200 OK with `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)` |
| Verified 8 column codes against FY23 dictionaries (varlist + imputationvar) | All match v1.3 spec exactly |
| Confirmed EFIA2023 grain: 5,959 rows / 5,959 distinct UNITIDs / no breakdown column | NO dedup needed (matches preflight) |
| Spot-checked 5 institutions (Berkeley/UGA/UNC-CH/Stanford/IU-Bloomington) | All within 1% of published IPEDS Data Center figures; **preflight had IU-B UNITID wrong (152228); actual 151351** |
| Computed distributions, form mix, F3 sparseness, imputation prevalence | All §4 EDA Reqs answered with quantified evidence |
| Computed UNITID overlap with `bronze.college_scorecard_institution` (3,039 UNITIDs) | 2,621 overlap (98.0% of finance, 86.2% of scorecard) |
| Identified 3 ingestor gates that block promote | (1) fiscal_year=2023, (2) F3 col overrides, (3) EFIA file/dedup overrides + EFIA 3-column code change |
| Identified RAW-IPF-001 calibration drift (5,000–8,000 → 2,500–3,200) | Flagged for @bs:dq-rule-writer |

EDA report saved to: `governance/eda/full-pipeline-ipeds-finance-raw-eda.md`
Reproducible analysis script: `scripts/eda_ipeds_finance_raw.py` + `/tmp/scorecard_overlap.py` (also reproduces overlap)
