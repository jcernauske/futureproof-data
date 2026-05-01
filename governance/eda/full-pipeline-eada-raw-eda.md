# EDA Report: raw.eada (full-pipeline-eada)

**Source:** EADA Athletics Disclosure Survey, U.S. Dept. of Education / Office of Postsecondary Education
**Date:** 2026-04-30
**Agent:** @bs:data-analyst (FutureProof: @fp-data-reviewer surrogate)
**Spec:** `docs/specs/full-pipeline-eada.md` §3 + §4
**Reporting cycle analyzed:** Academic year 2022–2023 (file `EADA_2022-2023.zip`, member `InstLevel.xlsx`)
**Cached file (CSV):** `/Users/jcernauske/code/bright/futureproof-data/data/raw/eada_cache/eada_2022.csv`
**Source method:** `bulk_csv_download` (downloaded live from `https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_2022-2023.zip`)
**Record count:** 2,040 institutions
**Field count:** 168 columns

---

## Acquisition

The Custom Data Cutting Tool front-end at `https://ope.ed.gov/athletics/` does not expose the bulk endpoint in its visible HTML, but the SPA backend does, and it is unauthenticated. Pinned for the ingestor:

| Endpoint | Returns |
|---|---|
| `GET https://ope.ed.gov/athletics/api/dataFiles/years` | JSON: `[2003, 2004, …, 2024]` |
| `GET https://ope.ed.gov/athletics/api/dataFiles/fileList` | JSON: every available zip with `FileName`, `Year`, `Format`, `LinkName`, `Description` |
| `GET https://ope.ed.gov/athletics/api/dataFiles/file?fileName=<FileName>` | The zip itself, `application/octet-stream` |

The User-Agent header `FutureProof/0.1 (jeff@hyenastudios.com)` was accepted on every endpoint. There are two file packages per year:

1. `EADA_<YYYY-YYYY>.zip` (~12 MB) — contains both `InstLevel.xlsx` (institution-level totals) and `Schools.xlsx` (per-team rows), plus SAS, SPSS, and Word codebook variants.
2. `EADA_All_Data_Combined_<YYYY-YYYY>_SAS_SPSS_EXCEL.zip` — bundled multi-format institution-only file.

We cached `EADA_2022-2023.zip` and extracted both members under `data/raw/eada_cache/`.

---

## Domain Context

**Identified Domain:** U.S. higher-education intercollegiate athletics financial reporting.
**Primary Entities:** Postsecondary institutions (UNITID-keyed) that operate at least one intercollegiate athletics program and receive federal Title IV funds (§485g of the Higher Education Act mandates the disclosure).
**Grain:** One row per UNITID per academic reporting year (institution-totals file).
**Companion grain:** `Schools.xlsx` is `(UNITID, SPORTSCODE)` per academic reporting year.
**Temporal Pattern:** Annual snapshot keyed to the full academic year (Jul–Jun). Submitted by Oct 15 of the year following the reporting cycle (e.g., 2022–23 data was due Oct 15, 2023; published Mar 2024).
**Domain Vocabulary:** EADA, IPEDS UNITID, NCAA D1-FBS / D1-FCS / D1 / D2 / D3, NAIA, NJCAA, CCCAA, NWAC, NCCAA, USCAA, FTE coach, head coach, assistant coach, "operating expenses," "grand total expense / revenue," recruiting expenses, athletically related student aid.
**Taxonomy/Codes Found:**
- `ClassificationCode` (1..N) and `classification_name` — 19 distinct conference/division values; see distribution below.
- `sector_cd` / `sector_name` — IPEDS 9-sector taxonomy (`Public, 4-year or above`, `Private nonprofit, 4-year or above`, etc.).
- `SPORTSCODE` (per-team file only) — 37 distinct values (1..37), each a sport (Baseball, Basketball, etc.). The codebook `SchoolsDoc2023.doc` is the source of truth.
- IPEDS UNITID — primary FK to all IPEDS data.

---

## Key Findings

1. **Spec column names are wrong.** The §3 working assumptions (`EXP_TOTAL_TOTAL`, `REV_TOTAL_TOTAL`, `RECRUITEXP_TOTAL_TOTAL`) **do not exist** in `InstLevel.xlsx`. The actual institution-level grand-total columns are `GRND_TOTAL_EXPENSE`, `GRND_TOTAL_REVENUE`, and `RECRUITEXP_TOTAL` (no `_TOTAL` suffix on recruiting). The ingestor must be re-pinned before raw promotion.
2. **The institution-totals file is a separate file**, not a marker subset of a mixed file. The §4 "filter to institution-total rows by SPORT_CODE NULL" model is the wrong mental model entirely. There is no in-pipeline filter needed when we read `InstLevel.xlsx`. The `Schools.xlsx` per-team file (17,886 rows × 129 cols) is a separate artifact and is **not** ingested. RAW-EAD-012 (post-filter row count within 1% of distinct UNITIDs) becomes a trivial pass under this model.
3. **Zero suppression-sentinel hits in the institution-totals file.** All three monetary fields are 100% non-null with no `-1`, `-2`, or blank values across 2,040 rows. EADA's suppression sentinels are a per-sport phenomenon (in `Schools.xlsx`) where small programs have privacy-suppressed roster counts; institution grand totals are always populated. **This invalidates the threshold structure of RAW-EAD-007/008/009 (95%/95%/80% completeness)** — those rules will never bind on the institution file.
4. **17.8% of institutions report exactly `$0` for recruiting expenses.** These are real zeros (mostly NJCAA Division II/III and CCCAA programs that don't recruit off-campus), not suppressions. RAW-EAD-006 (`recruiting_expenses ≥ 0`) is the right rule; any rule expecting recruiting > 0 would be wrong.
5. **D1-FBS anchors confirmed for RAW-EAD-011.** 60 institutions exceed $100M total expense; the top 5 are Ohio State ($234M), USC ($212M), Notre Dame ($204M), Michigan ($202M), Texas ($199M). RAW-EAD-011 passes with margin.
6. **UNITID overlap with `bronze.college_scorecard_institution` is only 74.5%.** 521 of 2,040 EADA institutions (25.5%) are missing from College Scorecard. **These are almost entirely 2-year community/junior colleges** (NJCAA-I: 168, NJCAA-II: 118, CCCAA: 95, NJCAA-III: 90, NWAC: 10, USCAA: 7, etc.). College Scorecard is 4-year-skewed by design. **This is a major calibration signal for BSE-EAD-009** (currently `fte_source_available coverage ≥ 95%` at base) — the actual coverage will likely be ~75% against College Scorecard, and IPEDS Finance has a similar 4-year skew. The base threshold needs revision.
7. **Reporting year has no in-file column.** The academic year is encoded only in the filename (`EADA_2022-2023.zip` → 2022–23). The convention adopted: stamp `reporting_year = academic_year_start` (e.g., 2022 for the 2022–23 cycle), matching the College Scorecard / IPEDS finance year convention.

---

## EadaIngestor Configuration Pin

**This is the BLOCKING gate output. The orchestrator must update `EadaIngestor`'s constants to these values before the ingestor runs.**

```python
# Override these via EadaIngestor.__init__ kwargs OR overwrite the class
# constants directly. Source-of-truth is this EDA report; the EADA codebook
# member InstlevelDataDoc2023.doc inside EADA_2022-2023.zip is the
# upstream authority.

INSTITUTION_TOTAL_FILTER_COLUMN = None   # NO IN-PIPELINE FILTER NEEDED.
INSTITUTION_TOTAL_FILTER_VALUE  = None   # The institution-totals file
                                         # (InstLevel.xlsx) is already
                                         # one-row-per-UNITID by construction.

DEFAULT_EXP_COLUMN        = "GRND_TOTAL_EXPENSE"   # was EXP_TOTAL_TOTAL
DEFAULT_REV_COLUMN        = "GRND_TOTAL_REVENUE"   # was REV_TOTAL_TOTAL
DEFAULT_RECRUITING_COLUMN = "RECRUITEXP_TOTAL"     # was RECRUITEXP_TOTAL_TOTAL

UNITID_COLUMN  = "unitid"            # lowercase in EADA, NOT "UNITID"
INSTNM_COLUMN  = "institution_name"  # NOT "INSTNM"

DEFAULT_REPORTING_YEAR = 2022        # academic year start of 2022-23 cycle
```

**Required code change in `EadaIngestor`:**
- The current `_is_institution_total()` filter is no longer needed *for the canonical input* (`InstLevel.xlsx`). Recommend the orchestrator construct the ingestor with `institution_total_filter_column=None`, then have `_is_institution_total()` short-circuit to `True` when `self.filter_column is None`. The fallback path (mixed-file ingestion of `Schools.xlsx`-style data) can keep the SPORTSCODE-based filter for safety against future EADA format changes.
- The ingestor currently reads CSV. Either (a) extend it to extract `InstLevel.xlsx` from the zip via `openpyxl` + write the institution-only CSV at fetch time (recommended — keeps the `csv_cache` contract), or (b) cache the converted CSV at `data/raw/eada_cache/eada_<year>.csv` (which we have already written for 2022) and let the existing CSV reader pick it up. Option (b) is what is in place today; the ingestor will work as-is once the column constants are updated.

**RAW-EAD-012 amendment recommendation:** The "post-filter row count within 1% of distinct UNITIDs" rule is now a tautology (no filter is applied). Either drop RAW-EAD-012, or re-target it as "row count == file row count" (a weaker conservation check). Defer to @bs:dq-rule-writer.

---

## Field Profiles

### Identity fields

#### `unitid` (LowerCase. NOT `UNITID`.)
- **Type:** integer-like string in CSV; coerce to `long`
- **Null Rate:** 0% (0/2,040)
- **Cardinality:** 2,040 distinct (100% unique — confirms grain)
- **Pattern:** 6-digit IPEDS UNITIDs, no leading zeros in this cycle. The ingestor's `_coerce_long` already handles quoted/zero-padded variants from older cycles.

#### `institution_name` (NOT `INSTNM`.)
- **Type:** STRING
- **Null Rate:** 0%
- **Examples:** `Alabama A & M University`, `Ohio State University-Main Campus`

#### `classification_name` (sector context — useful but not in raw schema)
- **Top values:**

| Count | Classification |
|---:|---|
| 235 | NCAA Division III with football |
| 217 | NJCAA Division I |
| 177 | NCAA Division III without football |
| 156 | NCAA Division II with football |
| 155 | NAIA Division I |
| 138 | NJCAA Division II |
| 134 | NCAA Division II without football |
| 131 | NCAA Division I-FCS |
| 127 | NCAA Division I-FBS |
| 110 | CCCAA |
| 99  | NJCAA Division III |
| 96  | NCAA Division I without football |
| 75  | NAIA Division II |
| 64  | Other |
| 47  | USCAA |
| 33  | NWAC |
| 28  | NCCAA Division II |
| 11  | NCCAA Division I |
| 7   | Independent |

### Monetary fields

#### `GRND_TOTAL_EXPENSE` (raw column, → `total_athletic_expenses`)
- **Type:** DOUBLE
- **Null Rate:** 0% (0/2,040). Zero suppression sentinels.
- **Distribution (USD):**

| Stat | Value |
|---|---:|
| min | $11,532 |
| p5  | $245,129 |
| p25 | $1,208,147 |
| p50 | $3,452,941 |
| p75 | $8,696,542 |
| p95 | $44,300,839 |
| p99 | $160,420,147 |
| max | $234,409,941 (Ohio State) |
| mean | $11,594,802 |

- **Histogram:**

| Bucket | Count |
|---|---:|
| <$100K | 22 |
| $100K–500K | 199 |
| $500K–1M | 220 |
| $1M–5M | 807 |
| $5M–10M | 344 |
| $10M–50M | 360 |
| $50M–100M | 28 |
| $100M–200M | 56 |
| $200M–500M | 4 |
| ≥$500M | 0 |

- **Outliers / tail:** 60 rows above $100M (D1 power conferences). 0 rows below $0. 0 rows at $0.

#### `GRND_TOTAL_REVENUE` (raw column, → `total_athletic_revenue`)
- **Type:** DOUBLE
- **Null Rate:** 0% (0/2,040)
- **Distribution (USD):**

| Stat | Value |
|---|---:|
| min | $11,532 |
| p5  | $248,700 |
| p25 | $1,248,072 |
| p50 | $3,577,777 |
| p75 | $9,002,831 |
| p95 | $44,777,300 |
| p99 | $166,886,577 |
| max | $261,353,404 |
| mean | $11,957,926 |

- **Histogram:**

| Bucket | Count |
|---|---:|
| <$100K | 19 |
| $100K–500K | 190 |
| $500K–1M | 222 |
| $1M–5M | 790 |
| $5M–10M | 359 |
| $10M–50M | 370 |
| $50M–100M | 28 |
| $100M–200M | 53 |
| $200M–500M | 9 |
| ≥$500M | 0 |

- **Notable invariant:** for every row, `GRND_TOTAL_REVENUE == GRND_TOTAL_EXPENSE` is approximately true (revenue ≈ expense within rounding). EADA requires institutions to report revenues at least equal to expenses (any deficit is conventionally booked as institutional support); the dataset is "balanced" at the grand-total level. **Therefore the spec's `BSE-EAD-010` ("athletic_subsidy_ratio P50 > 0") is unlikely to hold in raw EADA terms** — at the GRND_TOTAL level the ratio is near zero everywhere. To capture the "athletics loses money" insight the consumable layer needs to subtract `direct institutional support` (a separate category not in the grand total). Flag for @bs:dq-rule-writer review.

#### `RECRUITEXP_TOTAL` (raw column, → `recruiting_expenses`)
- **Type:** DOUBLE
- **Null Rate:** 0% (0/2,040)
- **Zero rate:** 17.8% (363 institutions report exactly $0)
- **Distribution (USD):**

| Stat | Value |
|---|---:|
| min | $0 |
| p5  | $0 |
| p25 | $2,910 |
| p50 | $28,298 |
| p75 | $88,449 |
| p95 | $878,902 |
| p99 | $3,166,132 |
| max | $7,455,849 |
| mean | $191,524 |

- **Histogram:**

| Bucket | Count |
|---|---:|
| <$100K | 1,586 |
| $100K–500K | 284 |
| $500K–1M | 78 |
| $1M–5M | 88 |
| $5M–10M | 4 |
| ≥$10M | 0 |

- **Edge case:** the 363 zeros concentrate in NJCAA II/III, CCCAA, NWAC. They are real reported zeros (the institutions don't have a recruiting budget), not nulls.

---

## Cross-Field Analysis

- **Revenue ≈ Expense at the grand-total level** (see above). Implications for BSE-EAD-007 and BSE-EAD-010.
- **Recruiting expenses are a tiny fraction of total expense** at p50 (~0.8%); for D1-FBS top schools they reach 1–4%. No correlation issue.
- **`EFTotalCount` (enrollment FTE) is in the EADA file itself** as columns `EFMaleCount`, `EFFemaleCount`, `EFTotalCount`. **This is a meaningful finding for §5 (Base):** EADA already carries an FTE-equivalent enrollment count, so the planned LEFT JOIN to `base.ipeds_finance` for FTE could be supplemented or replaced by an in-EADA value, eliminating the 25.5% missing-from-scorecard issue. EADA's `EFTotalCount` is "12-month enrollment count from IPEDS" and is exactly the value used as the FTE denominator in Knight Commission per-FTE calculations. Recommend @bs:semantic-modeler reconsider the FTE source: use EADA's `EFTotalCount` directly instead of an external join.

---

## Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|---|---:|---:|---|
| Total rows in 2022–23 institution file | 2,040 | 100% | RAW-EAD-001 (1,800–2,300) holds with margin. |
| `unitid` non-null and unique | 2,040 | 100% | RAW-EAD-002 + RAW-EAD-003 hold trivially. |
| `total_athletic_expenses` non-null | 2,040 | 100% | RAW-EAD-007 (≥95% non-null) trivially holds; **threshold is set far below observed reality, consider tightening to ≥99%.** |
| `total_athletic_revenue` non-null | 2,040 | 100% | RAW-EAD-008 (≥95% non-null) trivially holds; consider ≥99%. |
| `recruiting_expenses` non-null | 2,040 | 100% | RAW-EAD-009 (≥80% non-null) **trivially holds — threshold is dangerously loose.** Consider ≥99%. |
| `recruiting_expenses == $0` | 363 | 17.8% | These are real zeros. Do NOT add a ">0" rule. RAW-EAD-006 (≥0) is correct. |
| `total_athletic_expenses > $100M` | 60 | 2.9% | RAW-EAD-011 holds with margin. |
| `total_athletic_expenses == 0` | 0 | 0% | A future zero would indicate a data error; consider a P1 rule "expense > $0". |
| `unitid` overlap with `bronze.college_scorecard_institution` | 1,519 / 2,040 | 74.5% | **BSE-EAD-009 (95% threshold) is unrealistic against the closest available proxy.** Drop to ~75% or switch FTE source to in-EADA `EFTotalCount` (see Cross-Field). |
| `unitid` overlap with `consumable.career_outcomes` | DEFERRED | n/a | TBD on consumable build (table does not yet exist). |

---

## Anomalies

| Field | Type | Count | Severity | Details |
|---|---|---:|---|---|
| All three monetary columns | Spec-mismatch | 2,040 | **BLOCKING** | Spec's `EXP_TOTAL_TOTAL` / `REV_TOTAL_TOTAL` / `RECRUITEXP_TOTAL_TOTAL` do not exist. Use `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL`. |
| `unitid`, `institution_name` | Case mismatch | 2,040 | **BLOCKING** | Spec assumed `UNITID` / `INSTNM`; EADA uses lowercase `unitid` and `institution_name`. |
| `SPORT_CODE` | Column does not exist | 0 | **BLOCKING** | The institution-totals file (`InstLevel.xlsx`) does not contain SPORTSCODE at all. The per-team file (`Schools.xlsx`) does, but spelled `SPORTSCODE`. The "filter on SPORT_CODE IS NULL" model in the spec is incorrect. Use the institution-totals file directly. |
| Reporting-year column | Absent | n/a | Medium | No `YEAR` or `REPORT_YEAR` column. Year is encoded only in the filename. Pin `reporting_year` from the cache filename or constructor argument. RAW-EAD-010 (single-value rule) holds trivially because the ingestor stamps the constant. |
| `RECRUITEXP_TOTAL == $0` | Zero rate | 363 | Low | Real zeros, not suppressions. Document in @bs:domain-context to prevent future false-positive DQ rules. |
| Revenue ≈ Expense identity | Structural | ~2,040 | Medium | Grand totals balance by EADA convention; this means BSE-EAD-010 ("subsidy ratio P50 > 0") will not behave as the spec author imagined. Defer to @bs:dq-rule-writer. |
| 25.5% missing from College Scorecard | Coverage gap | 521 | High | Concentrated in 2-year colleges. BSE-EAD-009 threshold is wrong; either lower it, switch FTE source, or restrict population to 4-year. |

---

## Risks / Gates for Raw Promotion

The orchestrator must do **all of the following** before running `EadaIngestor.ingest()`:

1. **Update column constants** in `EadaIngestor` per the "EadaIngestor Configuration Pin" section above (or pass them as `__init__` kwargs).
2. **Set `institution_total_filter_column=None`** so the ingestor short-circuits the per-team filter. Confirm `_is_institution_total()` returns `True` when `self.filter_column is None`. **This requires a small code change** — current code does `row.get(self.filter_column)` which will raise `TypeError` on `None`. Recommend:

   ```python
   def _is_institution_total(self, row: dict) -> bool:
       if self.filter_column is None:
           return True
       cell = row.get(self.filter_column)
       ...
   ```

3. **Confirm input-source contract.** The cached `eada_2022.csv` at `data/raw/eada_cache/eada_2022.csv` is what the existing CSV-only ingestor will read. If a future spec amendment wires the bulk-zip-fetch path, point it at `https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_2022-2023.zip` and have the ingestor extract `InstLevel.xlsx` in-memory.
4. **Document RAW-EAD-007/008/009 threshold tightening recommendation** in the @bs:dq-rule-writer brief — current thresholds are far below observed reality.
5. **Hold BSE-EAD-009 until base ships** — the 95% cross-source threshold is incompatible with the 74.5% measured overlap against `bronze.college_scorecard_institution`. @bs:semantic-modeler should consider switching the FTE source to EADA's in-file `EFTotalCount`. Flagged separately in the §5 review.
6. **Hold BSE-EAD-010** — the "subsidy P50 > 0" plausibility rule will fail because EADA grand totals balance by construction. The signal lives in `direct_institutional_support` (a column we are not currently ingesting). Defer.

---

## Audit Trail

- Acquired `EADA_2022-2023.zip` from `https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_2022-2023.zip` at 2026-04-30, ~11.7 MB, HTTP 200.
- Cached zip + extracted `InstLevel.xlsx` (1.5 MB), `Schools.xlsx` (5.8 MB), and converted `InstLevel.xlsx` → CSV at `data/raw/eada_cache/eada_2022.csv` (2,040 rows × 168 cols).
- Confirmed `dataFiles` API surface is unauthenticated and stable; ingestor docstring should cite all three endpoints (`years`, `fileList`, `file?fileName=`).
- Compared 2,040 EADA UNITIDs against 3,039 distinct UNITIDs in `bronze.college_scorecard_institution` (DuckDB scan over the Iceberg parquet). Overlap = 1,519 (74.5%). The 521 missing institutions skew heavily 2-year (>80% of the missing).
- `base.ipeds_finance` was the spec's intended FTE source but does not yet exist; flagged.
- `consumable.career_outcomes` overlap is **deferred** until the consumable zone is built.
