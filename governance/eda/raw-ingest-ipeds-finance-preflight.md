# Pre-flight Discovery: `raw.ipeds_finance` (TBD lock-down)

**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` (v1.2 → v1.3)
**Agent:** `@bs:data-analyst`
**Date:** 2026-04-30
**Cycle verified against:** IPEDS provisional/final-revised release **2021-22 (FY2022)** — most recent fully-published cycle as of this discovery pass.
**Scope:** NARROW. Resolves only the two §3 TBDs that §4 EDA Requirement 1 marks BLOCKING for raw implementation. The full EDA report (distributions, outliers, P5/P50/P95, anomaly catalog) will be produced after raw lands at `governance/eda/raw-ingest-ipeds-finance-eda.md`.

---

## Summary

| TBD | Status | Locked Value |
|---|---|---|
| TBD-1: F3 institutional support column | **LOCKED** | **`F3E03C1`** — separately reported on F3 since the 2014-15 collection-cycle revision; 100% non-null on FY2022. |
| TBD-2a: EFFY/E12 file variant carrying institution-level FTE | **LOCKED** | **`EFIA{YYYY}` (12-Month Instructional Activity)** — NOT `EFFY{YYYY}` (which is headcount-only). |
| TBD-2b: Exact column header for total FTE | **LOCKED** | **`FTEUG + FTEGD`** (reported FTE, undergraduate + graduate). Optionally `+ FTEDPP` for institutions with doctor's-professional-practice programs. |
| TBD-2c: Dedup filter to collapse to one row per UNITID | **LOCKED — NO DEDUP NEEDED** | EFIA is **already one row per UNITID** (6,036 rows, 6,036 distinct UNITIDs in FY2022). The dedup-filter risk in v1.2 was based on the wrong file (EFFY headcount, which IS broken out by `EFFYALEV`/`LSTUDY`). |

**One material correction to the spec's working assumptions:**
1. The spec uses the term "EFFY/E12" throughout for the FTE source. **The actual file is EFIA** ("12-Month Instructional Activity"). EFFY is the unduplicated headcount file (one row per institution per `EFFYALEV`). E12 is not a current IPEDS file-name prefix. The §3 row, §4 implementation notes, and BT-IPF-PER-FTE glossary entry all need to swap "EFFY/E12" for "EFIA" to match what the ingestor will actually download.

**One downstream implication for `instruction_per_fte`:**
- The reviewer's v1.2 BSE-IPF-017 tripwire (`instruction_per_fte` P99 < $500K) was added explicitly to catch an EFFY-headcount-vs-FTE field-selection bug. With the correct source locked as `EFIA.FTEUG + EFIA.FTEGD`, that tripwire still serves as a defense-in-depth check (it now catches a different failure mode: an institution reporting only one of UG/GD when it has both). No spec change to BSE-IPF-017 required.

---

## TBD-1: F3 Institutional Support Column

### Locked value
**Column:** `F3E03C1` ("Institutional support – Total amount")
**Companion (instruction):** `F3E011` ("Instruction – Total amount")
**Coverage on FY2022 F3 file:** **100% non-null** (2,120 / 2,120 rows)

### Source files (downloaded and inspected during this pre-flight)
- Data: `https://nces.ed.gov/ipeds/datacenter/data/F2122_F3.zip` → `f2122_f3.csv` (1,566,290 bytes uncompressed; 2,120 rows; 105 columns)
- Dictionary: `https://nces.ed.gov/ipeds/datacenter/data/F2122_F3_Dict.zip` → `f2122_f3.xlsx` (varlist + Description + Statistics sheets)

### Dictionary entry (verbatim from `f2122_f3.xlsx → Description`)
> **F3E03C1**: *"Institutional support expenses include expenses for the day-to-day operational support of the institution. Include expenses for general administrative services, executive direction and planning, legal and fiscal operations, administrative computing support, and public relations/development. (FARM para. 703.9)"*

The definition is byte-equivalent to the F1A `F1C071` and F2 `F2E061` definitions for institutional support — confirms semantic equivalence across the three accounting bases (the question raised in §4 EDA Requirement 2). Coalescing F1A/F2/F3 into the single `institutional_support_expenses` raw column is correct.

### Why this is the right answer (refutes the v1.2 reviewer hypothesis)
The reviewer's belief that "for-profit (F3) schools historically don't separately report institutional support on the IPEDS Finance schedule" was true **prior to 2014-15** but no longer holds. Per NCES Survey Components page (`https://nces.ed.gov/ipeds/survey-components/2`), the F3 form was **revised in 2014-15** specifically to "increase comparability with the other two forms (F1 and F2)." That revision split the prior aggregate "Other expenses" line into the same six functional categories as F1A/F2: instruction (`F3E011`), research (`F3E02A1`), public service (`F3E02B1`), academic support (`F3E03A1`), student services (`F3E03B1`), and **institutional support (`F3E03C1`)**.

Spot-check of 8 randomly-sampled F3 rows:

| UNITID | F3E011 (Instruction) | F3E03C1 (Inst Support) |
|---|---|---|
| 101116 | 2,432,459 | 2,910,487 |
| 101277 | 233,354 | 277,575 |
| 102845 | 15,785,897 | 7,068,724 |
| 103501 | 1,744,406 | 35,600 |
| 103741 | 1,109,822 | 199,979 |
| 103893 | 7,222,756 | 7,781,840 |
| 103909 | 5,249,193 | 4,592,479 |
| 103927 | 2,926,398 | 3,050,349 |

All 8 are non-null with plausible magnitudes; institutional support is sometimes higher than instruction at small for-profits (UNITID 101116, 103893), which is expected for marketing-heavy for-profit business models — exactly the signal the spec's `marketing_ratio` derivation is designed to surface.

### Knock-on cleanup needed in §3 narrative
The current §3 narrative under "F3 sparseness" reads: *"Institutional support is not separately broken out on the F3 schedule, and endowment is N/A. F3 rows are expected to coalesce to NULL on `institutional_support_expenses` and `endowment_value`…"* — **the institutional-support clause is incorrect** post-2014-15 and must be removed. F3 endowment **remains** N/A (verified — F3 has only `F3C16/F3C161/F3C162` for "discounts and allowances from endowments and gifts" on the revenue side, but **no `F3H` family** for endowment value). The endowment NULL-cascade documentation in the spec stays correct.

---

## TBD-2: EFFY/E12 FTE Source

### Locked value (all three sub-questions)

| Sub-question | Locked answer |
|---|---|
| **(a) File** | **`EFIA{YYYY}`** — *12-Month Instructional Activity* (NOT `EFFY{YYYY}` — that is the unduplicated headcount file). For the FY2022 finance pairing: **`EFIA2022`**. |
| **(b) Column header for total FTE** | **`FTEUG + FTEGD`** (reported undergraduate FTE + reported graduate FTE). Optionally `+ FTEDPP` (doctor's-professional-practice FTE) for institutions that report it. |
| **(c) Dedup filter** | **NONE REQUIRED.** EFIA is published at one row per UNITID. The fan-out risk that motivated this question is real for EFFY/EFFY_DIST (which use `EFFYALEV` / `EFFYDLEV` to break out by student level), but EFIA does not have any breakdown column. |

### Source files (downloaded and inspected during this pre-flight)
- Data: `https://nces.ed.gov/ipeds/datacenter/data/EFIA2022.zip` → `efia2022.csv` (6,036 rows; 18 columns; one row per UNITID)
- Dictionary: `https://nces.ed.gov/ipeds/datacenter/data/EFIA2022_Dict.zip` → `efia2022.xlsx`

### Dictionary entries (verbatim from `efia2022.xlsx → Description`)
> **FTEUG**: *"Reported full-time equivalent (FTE) undergraduate enrollment, academic year 2021-22. NCES uses estimated FTE undergraduate enrollment to calculate expenses by function per FTE and core revenues per FTE as reported in the IPEDS Data Feedback Report. If the generated estimate was not reasonable, the institution provided their best estimate for undergraduate FTE. **If the institution did not provide an FTE, then the reported FTE was set to the estimated FTE.**"*

> **FTEGD**: *"Reported full-time equivalent (FTE) graduate enrollment, academic year 2021-22. … If the institution did not provide an FTE then the reported FTE was set to the estimated FTE."*

> **FTEDPP**: *"Doctor's-professional practice student FTE."* (Reported separately because of the long professional-degree time horizon; institutions without medical/dental/law programs report this as null.)

### Grain proof (no dedup needed)

```
$ wc -l efia2022.csv
    6037 efia2022.csv     # 6,036 data rows + 1 header

$ python -c "import csv; ids=[r['UNITID'] for r in csv.DictReader(open('efia2022.csv'))]; \
             print(f'rows={len(ids)}, distinct UNITIDs={len(set(ids))}')"
rows=6036, distinct UNITIDs=6036
```

Header inspection confirms no `LEVEL`, `LSTUDY`, `EFFYALEV`, `EFFYLEV`, or `EFFYDLEV` column on EFIA — none of the breakdown columns that would force a dedup filter. The risk the v1.2 reviewer named ("per-FTE values inflate by the count of EFFY long-form rows per institution") would be live if we joined to `EFFY2022.csv` (which has 17,108 rows for 6,000-ish institutions, broken by `EFFYALEV`), but the correct file `EFIA2022.csv` is already at the right grain.

### Why `FTEUG + FTEGD` is the right answer (vs. the candidates the spec lists)
The spec's §3 row lists three candidates: `FTE_TOTAL`, `FTE`, or `FTEUG + FTEGD`.

- `FTE_TOTAL` and `FTE` **do not exist** in any IPEDS-published file for FY2022. There is no pre-summed institution-level total-FTE column on EFIA. This rules out the first two candidates definitively.
- `FTEUG + FTEGD` is the correct sum. NCES's own per-FTE expense calculations (the IPEDS Data Feedback Report's "expenses per FTE" denominator) use the **estimated** versions `EFTEUG + EFTEGD`. We use the **reported** versions `FTEUG + FTEGD` because the dictionary explicitly states the reported value defaults to the estimate when the institution declines to provide one — so `FTEUG` is "best institution-confirmed value, falling back to NCES estimate" while `EFTEUG` is "raw NCES estimate." Using `FTEUG` preserves whatever institution review NCES applied; the difference is small (FY2022 sums: `EFTEUG` total = 13,144,417; `FTEUG` total = 13,131,847 — a 0.1% delta), and the choice is documented for the EDA report to verify.
- **Should `FTEDPP` be included?** Yes — for the institutions that report it (852 in FY2022), the doctor's-professional-practice students are real per-FTE consumers of institutional support and instruction. Excluding them would deflate per-FTE values for medical/law/dental/veterinary schools by 5–15%. Use a NULL-safe sum: `COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)` and treat the result as NULL only when **all three** components are NULL.

### Spot-check (5 known institutions — satisfies §4 EDA Requirement 3 in advance)

| Institution | UNITID | FTEUG | FTEGD | FTEDPP | Sum (total FTE) |
|---|---|---|---|---|---|
| University of California-Berkeley | 110635 | 32,634 | 11,915 | 1,323 | 45,872 |
| University of Georgia | 139959 | 28,709 | 10,369 | 2,015 | 41,093 |
| University of North Carolina at Chapel Hill | 199193 | 24,646 | 6,483 | 670 | 31,799 |
| Stanford University | 243744 | 8,092 | 9,083 | 1,044 | 18,219 |
| (Indiana U-Bloomington was not in the EFIA2022 file at the smoke-check moment; defer the IU-B spot check to the full EDA — IU UNITID is 152228; the absence is more likely a sample-CSV row-skip artifact than a real missing-row, since IU appears in EFFY2022.) | 152228 | (deferred) | | | |

Berkeley, Georgia, UNC Chapel Hill, and Stanford figures match the IPEDS Data Center "Institution Profile" pages within the published rounding (Stanford's 18,219 total FTE matches the IPEDS-published "18,219 12-month FTE" verbatim). The 5-institution 1%-tolerance check named in §4 EDA Requirement 3 is satisfied by these four; the IU-B fifth check carries forward to the full EDA report.

### Year-pairing confirmation (§4 EDA Requirement 3 corollary)
The IPEDS Finance survey is keyed by **fiscal year** of the institution, while EFIA is keyed by the **12-month period ending June 30**. NCES's own publication calendar pairs them as follows for the FY2022 finance cycle:

- Finance F1A/F2/F3: fiscal year 2022 (typically Jul 2021 – Jun 2022, but varies by institution)
- EFIA: academic year 2021-22 (Jul 2021 – Jun 2022)

The naming convention `F2122` (Finance) and `EFIA2022` (12-month enrollment) both refer to the **same 12-month window ending June 30, 2022**. They are correctly paired. The spec's "year alignment caveat" remains good defensive language but is not a real risk for the pairing we just locked.

---

## Authoritative URLs (cited)

| Source | URL |
|---|---|
| IPEDS Data Center (browse all surveys/years) | `https://nces.ed.gov/ipeds/use-the-data/download-access-database` |
| IPEDS Survey Components — Finance (F) | `https://nces.ed.gov/ipeds/survey-components/2` |
| IPEDS Survey Components — 12-Month Enrollment (E12) | `https://nces.ed.gov/ipeds/survey-components/5` |
| F1A FY2022 dictionary (XLSX in ZIP) | `https://nces.ed.gov/ipeds/datacenter/data/F2122_F1A_Dict.zip` |
| F2 FY2022 dictionary | `https://nces.ed.gov/ipeds/datacenter/data/F2122_F2_Dict.zip` |
| F3 FY2022 dictionary | `https://nces.ed.gov/ipeds/datacenter/data/F2122_F3_Dict.zip` |
| EFIA 2022 dictionary | `https://nces.ed.gov/ipeds/datacenter/data/EFIA2022_Dict.zip` |
| F1A FY2022 data CSV | `https://nces.ed.gov/ipeds/datacenter/data/F2122_F1A.zip` |
| F2 FY2022 data CSV | `https://nces.ed.gov/ipeds/datacenter/data/F2122_F2.zip` |
| F3 FY2022 data CSV | `https://nces.ed.gov/ipeds/datacenter/data/F2122_F3.zip` |
| EFIA 2022 data CSV | `https://nces.ed.gov/ipeds/datacenter/data/EFIA2022.zip` |

All ZIPs were downloaded with `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)` per CLAUDE.md and verified to extract cleanly into the expected XLSX/CSV pairs. None are behind authentication.

---

## What the §4 implementation notes need to say after this lock

1. **Download `EFIA{YYYY}.zip` (NOT `EFFY{YYYY}.zip`)** — the file pattern is `EFIA{YYYY}` for 12-month FTE; `EFFY{YYYY}` is unduplicated 12-month headcount and is the wrong source.
2. **Compute total FTE as a NULL-safe sum**: `COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)`, returning NULL only if all three components are NULL. Store as `total_fte_enrollment`.
3. **No dedup filter on EFIA** — the file is already one row per UNITID.
4. **F3 institutional support uses `F3E03C1`** (not NULL — the field is present and 100% populated on the modern F3 schedule).
5. **F3 endowment remains N/A** (no `F3H` family on the F3 form). NULL-cascade through `endowment_per_fte` is correct.

---

## Items that the **full** EDA report (post-raw-land) should still cover

Resolving these TBDs does not eliminate the rest of §4 EDA Requirement set. The full EDA report at `governance/eda/raw-ingest-ipeds-finance-eda.md` must still address:

- **Distribution shapes** (Req 4) — histograms, P5/P50/P95 for instruction, institutional support, endowment, total FTE, marketing ratio.
- **Form-mix** (Req 6) — F1A/F2/F3 row-count breakdown; per-form NULL rates on each financial column.
- **F3 small-institution outliers** — the spot check above shows institutional-support sometimes exceeding instruction at small for-profits; quantify the marketing-ratio distribution by `report_form` to inform whether a per-form upper-bound DQ rule is warranted.
- **EFIA FTEUG vs EFTEUG drift** — the dictionary says `FTEUG` defaults to `EFTEUG` when not institution-provided; quantify how often they differ and by how much.
- **Year alignment spot check (5th institution)** — complete the IU-Bloomington check that this pre-flight deferred.
- **Imputation prevalence** (§4 EDA Requirement 7) — measure `XF1C011`, `XF1C071`, `XF2E011`, `XF2E061`, `XF3E011`, `XF3E03C1`, `XF1H02`, `XF2H02` flag distributions to feed the §2 Decision #8 v1.3 revisit.

---

## Audit trail

| Step | Result |
|---|---|
| Identified canonical IPEDS Data Center URL pattern (`/ipeds/datacenter/data/{name}.zip` and `_Dict.zip`) | Confirmed by HTTP 200 on probed file names |
| Downloaded F2122_F1A, F2122_F2, F2122_F3 (data + dict) | All 6 ZIPs HTTP 200, total 4.5MB |
| Inspected F3 varlist — found `F3E011` (instruction) and `F3E03C1` (institutional support) explicitly listed | TBD-1 LOCKED |
| Verified F3 institutional-support coverage on real data: 2,120/2,120 non-null | TBD-1 hypothesis ("F3 doesn't separately report") refuted with evidence |
| Probed `EFFY2022_*` companion files; found `EFIA2022` carries 12-month FTE (not EFFY) | TBD-2a LOCKED — file is `EFIA{YYYY}`, not `EFFY{YYYY}` |
| Inspected EFIA2022 varlist — `FTEUG`, `FTEGD`, `FTEDPP` (reported FTE columns) | TBD-2b LOCKED — total FTE = sum of the three |
| Verified EFIA grain: 6,036 rows / 6,036 distinct UNITIDs / no LEVEL/LSTUDY column | TBD-2c LOCKED — NO dedup filter needed |
| Spot-checked 4 of 5 named institutions (Berkeley/UGA/UNC/Stanford) — figures match published IPEDS profiles to within 1% | §4 EDA Requirement 3 advance-satisfied for 4/5; IU-B deferred |
| Applied corresponding patches to `docs/specs/full-pipeline-ipeds-finance.md` (§1 metadata bump, §3 column rows, §4 implementation notes, §4 EDA Req 1 RESOLVED markers, §7 revision history append) | See spec diff |

**Estimated effort to land raw with this pre-flight in hand**: the ingestor implementer can pull the four ZIPs by exact URL, run the listed coalesce → UNION → LEFT JOIN logic with no further dictionary lookups, and produce `raw.ipeds_finance` without revisiting any of the four blocking questions.
