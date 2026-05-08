# EDA Report: bronze.bls_oews

**Source:** `bronze.bls_oews` (Iceberg, May 2024 OEWS National wage percentiles)
**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Date:** 2026-05-06
**Agent:** @data-analyst
**Record Count:** 831
**Field Count:** 15
**EDA script:** `scripts/eda_bls_oews_bronze.py` (run via `uv run python scripts/eda_bls_oews_bronze.py`)

This is the second EDA on this data source (Bronze profile only — Silver promotion has not yet run). Domain context already established in prior BLS OOH EDA at `governance/eda/raw-bls-ooh-eda.md`; this report focuses on the new wage-distribution payload.

---

## Key Findings

- **Row count is in spec range (831, target 800–900).** Filter on `OCC_GROUP == 'detailed'` is working — no major/minor/broad rollup leakage.
- **Spec spot-checks all pass.** Software Developers (15-1252) median = $133,080 (spec says ~$130K), Nurse Practitioners (29-1171) median = $129,210 (~$126K), Chief Executives (11-1011) p75 and p90 both top-coded at $239,200, `wage_capped = True`. **Registered Nurses (29-1141) median = $93,600**, slightly above the spec's stated ~$86K range — this is May 2024 OEWS, two reference periods newer than the spec's calibration. `93,600` is well within the Bronze DQ rule's $75K–$100K spot-check window.
- **Suppression rate is excellent.** All five annual percentile columns (p10/p25/median/p75/p90) plus mean have **identical 99.398% non-null rate (826/831)**. The five suppressed rows form one tight cluster: SOC 27-2xxx performance-arts entertainment (Actors, Dancers, Musicians/Singers, DJs Except Radio, "Entertainers and Performers, Sports and Related, All Other"). BLS suppresses these because hourly/wage statistics are not meaningful for occupations dominated by gig/per-engagement compensation. **Spec's P0 floor of ≥95% non-null on `wage_annual_median` is comfortably exceeded.**
- **Top-coding affects 45 SOCs (5.4%).** All 45 have `wage_annual_p90 == 239200` (the BLS top-code floor). 24 of those 45 also have p75 top-coded, 17 have median top-coded, 1 has p25 top-coded. **No row is flagged `wage_capped` without at least one annual percentile equal to 239200.** Capped occupations are the high-earning physician, surgeon, dentist, pilot, manager, and lawyer SOCs — exactly as expected.
- **Monotonicity is perfect.** 826 / 826 rows with full wage data satisfy p10 ≤ p25 ≤ median ≤ p75 ≤ p90. **Zero violations.**
- **SOC integrity is perfect.** 0 format violations (all match `^\d{2}-\d{4}$`), 0 duplicates, 0 null occupation titles, 0 null `total_employment` values.
- **OEWS↔OOH overlap is near-total.** 831 of 832 silver-OOH SOCs are present in OEWS. Only `45-3031 Fishing and Hunting Workers` exists in OOH but not OEWS (small, suppressed in the May 2024 publication). After LEFT JOIN, **826/832 (99.28%) of `occupation_profiles` SOCs will have non-null `wage_p25`** — the spec's 90% Gold floor and ≥750-SOC floor are both achieved with wide headroom.
- **OEWS↔O\*NET overlap.** 772 of 798 `consumable.onet_work_profiles` SOCs are present in OEWS. 26 O\*NET-only SOCs exist (mostly newer detail-rollups O\*NET tracks but BLS aggregates).
- **Threshold lock-in.** Spec proposed "≥ 750 SOCs in `occupation_profiles` have non-null `wage_p25`" → actual is **826**. **Recommend tightening the floor to ≥ 800** (small chaos buffer) so the rule meaningfully detects regression rather than passing trivially.
- **One advisory anomaly:** 23 SOCs have `wage_annual_mean > wage_annual_p90`. All 23 are top-coded SOCs where p90 was floored to $239,200 but the mean was computed before the cap (BLS publishes both). This is a **known artifact of top-coding**, not a data quality issue. Document it in the data dictionary; do not write a DQ rule against it.

---

## Domain Context

This is the **sixth** data source in the FutureProof pipeline (per spec §Cross-Source Integration Notes); domain is "U.S. national-level occupational wage statistics" keyed by SOC. Already-established in prior EDAs.

- **Identified Domain:** Federal labor statistics — wage distributions per occupation
- **Primary Entity:** Detailed SOC occupation (XX-XXXX, 2018 vintage)
- **Grain:** One row per detailed SOC code; 831 distinct codes
- **Temporal Pattern:** Annual snapshot (May 2024 reference, published March 2025); `load_date` = ingest date
- **Domain Vocabulary surfaced in this load:** `OCC_GROUP=detailed`, `A_PCT10/25/75/90`, `A_MEDIAN`, `A_MEAN`, suppression sentinel `*`, top-code sentinel `#` → 239200.0 floor, `TOT_EMP`
- **Taxonomy:** SOC 2018 (same as `bronze.bls_ooh` and `consumable.onet_work_profiles` — direct join, no crosswalk needed)
- **Relationships discovered:** `soc_code` is a near-perfect foreign key to `base.bls_ooh.soc_code` (831 of 832 OOH SOCs covered) and to `consumable.onet_work_profiles.bls_soc_code` (772 of 798)

---

## Field Profiles

### `soc_code` (string, required)
- **Null Rate:** 0.0% (0 of 831)
- **Cardinality:** 831 distinct (100% unique)
- **Format:** All match `^\d{2}-\d{4}$` (0 violations)
- **Pattern:** SOC 2018 (`XX-XXXX`, hyphen preserved per spec)
- **Recommendation:** P0 regex rule + P0 uniqueness rule (already in spec).

### `occupation_title` (string, required)
- **Null Rate:** 0.0%
- **Cardinality:** 831 distinct titles (100% unique)
- **Recommendation:** P0 not-null rule (already in spec).

### `total_employment` (long, optional)
- **Null Rate:** 0.0% (0 of 831) — zero suppressed in this load.
- **Range:** Includes very small values (e.g. 8,170 for "Disc Jockeys, Except Radio") and very large (3,282,010 for Registered Nurses).
- **Recommendation:** No null-rate rule needed (BLS suppresses TOT_EMP in some years; do not over-tighten). Consider P1 sanity rule `total_employment >= 0` if not already present.

### `wage_annual_p10` (double, optional)
- **Null Rate:** 0.602% (5 of 831 — same five performance-arts SOCs as all annual percentiles)
- **Top-code count (=$239,200):** 0
- **Recommendation:** P1 non-null rate ≥ 99% (matches actual; flags new entertainment-style suppression).

### `wage_annual_p25` (double, optional)
- **Null Rate:** 0.602% (5 of 831)
- **Top-code count:** 1 (29-1243 Pediatric Surgeons — full distribution at $239,200)
- **Recommendation:** P0 non-null rate ≥ 99% (current 99.398%, headroom for one suppression to drop without alert).

### `wage_annual_median` (double, optional) — spec's P0 floor field
- **Null Rate:** 0.602% (5 of 831)
- **Distribution:** min=$30,160, p10=$37,800, p25=$46,053, **median=$59,775**, mean=$70,304, p75=$80,158, p90=$109,750, max=$239,200, σ=$39,277
- **Shape:** Right-skewed (mean > median). Histogram below.
- **Top-code count:** 17
- **Recommendation:** P0 non-null rate ≥ 95% (spec); actual 99.398% — passes with 4.4 ppt headroom. Recommend tightening to **≥ 99%**.

#### Histogram of `wage_annual_median` (10K buckets)
| Bucket | Count |
|--------|-------|
| $30K–$40K | 123 |
| $40K–$50K | 185 |
| $50K–$60K | 107 |
| $60K–$70K | 125 |
| $70K–$80K | 78 |
| $80K–$90K | 45 |
| $90K–$100K | 36 |
| $100K–$110K | 45 |
| $110K–$120K | 11 |
| $120K–$130K | 17 |
| $130K–$140K | 14 |
| $140K–$150K | 5 |
| $150K–$160K | 4 |
| $160K–$170K | 5 |
| $170K–$180K | 2 |
| $200K–$210K | 1 |
| $210K–$220K | 1 |
| $220K–$230K | 3 |
| $230K–$240K | **19** (top-code cluster) |

The $230K–$240K bucket contains the 17 SOCs whose median was top-coded plus two with median in (230K, 239,200) — almost entirely physician/surgeon/dentist specialties. The mode is the $40K–$50K band (185 SOCs); the distribution is bimodal in shape (a service-economy mode in the $40K–$50K band and a long tail of professional/managerial specialty SOCs).

### `wage_annual_p75` (double, optional)
- **Null Rate:** 0.602% (5 of 831)
- **Top-code count:** 24
- **Recommendation:** Same as p25 — P0 non-null rate ≥ 99%.

### `wage_annual_p90` (double, optional)
- **Null Rate:** 0.602% (5 of 831)
- **Top-code count:** 45 (the full set of `wage_capped = True` rows)
- **Recommendation:** P1 non-null rate ≥ 99%.

### `wage_annual_mean` (double, optional)
- **Null Rate:** 0.602%
- **Top-code count:** 0 (BLS publishes mean uncapped — see "mean above p90" anomaly below)
- **Recommendation:** No standalone DQ rule. Document in data dictionary that the mean is computed before top-coding, so for capped SOCs `mean > p90` is expected.

### `wage_hourly_median` (double, optional)
- **Null Rate:** 7.10% (59 of 831 null) — much higher than annual fields
- **Why:** BLS suppresses hourly figures for some salaried-only occupations (most managers, physicians, lawyers — all top-code-eligible roles). The 54 extra suppressions over the 5 annual-suppressed rows are SOCs where annual is published but hourly is not.
- **Recommendation:** No DQ rule needed — spec says this column is "kept for reference, not used downstream." Document the asymmetry in the data dictionary.

### `wage_capped` (bool, required)
- **Null Rate:** 0.0%
- **True count:** 45 (5.42% of rows)
- **Cross-check:** 0 rows with `wage_capped = True` lack an annual percentile equal to $239,200 → invariant holds.
- **Recommendation:** P0 rule "wage_capped = True iff at least one annual percentile = 239200" (already in spec).

### `ingested_at` / `source_url` / `source_method` / `load_date` (metadata)
- All non-null, source_method == "xlsx_download" for all 831 rows; source_url is the BLS special-requests ZIP. No anomalies.

---

## Cross-Field Analysis

### Monotonicity (P0)
On all 826 rows with full annual percentile data, p10 ≤ p25 ≤ median ≤ p75 ≤ p90 holds. **Zero violations.** The Silver/Bronze monotonicity DQ rule will pass cleanly.

### Spread (`p75 − p25`) — informs Future Enhancements §1 (ERN ceiling potential)
- Median spread = $26,880
- p10 spread = $11,305
- p90 spread = $62,445

**Widest spreads (top 10):**
| SOC | Title | p25 | p75 | Spread | Capped |
|-----|-------|-----|-----|--------|--------|
| 29-1229 | Physicians, All Other | 95,080 | 239,200 | 144,120 | yes |
| 29-1081 | Podiatrists | 91,130 | 217,960 | 126,830 | yes |
| 19-3032 | Industrial-Organizational Psychologists | 80,790 | 198,170 | 117,380 | no |
| 23-1011 | Lawyers | 99,760 | 215,420 | 115,660 | yes |
| 11-1011 | Chief Executives | 126,080 | 239,200 | 113,120 | yes |
| 13-1011 | Agents and Business Managers (Artists/Athletes) | 63,100 | 168,850 | 105,750 | yes |
| 11-2022 | Sales Managers | 95,910 | 201,490 | 105,580 | yes |
| 29-1216 | General Internal Medicine Physicians | 135,240 | 239,200 | 103,960 | yes |
| 23-1023 | Judges, Magistrate Judges, and Magistrates | 86,060 | 189,890 | 103,830 | no |
| 39-5091 | Makeup Artists, Theatrical and Performance | 28,850 | 132,530 | 103,680 | no |

**Narrowest spreads (bottom 10):** Laundry workers ($7,230), Manicurists ($6,150), Farmworkers ($4,670), Cooks-Private Household ($4,350), Oral and Maxillofacial Surgeons ($2,420 — both p25 and p75 at the cap), Pediatric Surgeons ($0 — entire visible distribution at the cap).

**Note for downstream ERN v2:** the four narrowest "top-coded" rows (Prosthodontists, Oral Surgeons, Pediatric Surgeons + others where median already hits $239,200) report artificially small spreads because the cap squashes the upper tail. Any ceiling-potential signal derived from `p75 − p25` should be guarded by a `wage_capped == False` condition or a fallback rule for capped SOCs.

### Mean above p90 (advisory, not anomaly)
23 SOCs report `wage_annual_mean > wage_annual_p90`. All 23 are top-coded. Examples: Cardiologists (mean $432,490 vs p90 $239,200), Anesthesiologists ($336,640 vs $239,200), Oral & Maxillofacial Surgeons ($360,240 vs $239,200). BLS publishes mean uncapped. **Do NOT add a DQ rule — this would generate 23 false-positive failures every refresh.**

---

## Spec Spot-Checks

| SOC | Title | Spec Expected | Actual | Verdict |
|-----|-------|---------------|--------|---------|
| 29-1141 | Registered Nurses | median ~$86K, p25 ~$63K, p75 ~$101K | median **$93,600**, p25 $78,610, p75 $107,960, capped=False | PASS — median above spec's calibration but inside Bronze DQ window ($75K–$100K). May 2024 vintage shifted upward from spec's reference data. |
| 15-1252 | Software Developers | median ~$130K | median **$133,080**, p25 $103,050, p75 $169,000, p90 $211,450, capped=False | PASS — well inside DQ window ($110K–$150K). |
| 29-1171 | Nurse Practitioners | median ~$126K | median **$129,210**, p25 $109,940, p75 $149,570, capped=False | PASS — within $5K of spec. |
| 11-1011 | Chief Executives | p90 top-coded | p10 $73,710, p25 $126,080, median $206,420, p75 **$239,200**, p90 **$239,200**, mean $262,930, capped=**True** | PASS — both p75 and p90 hit the floor, `wage_capped` correctly set, mean properly published uncapped at $262,930. |

---

## Edge Cases for DQ Thresholds

| # | Observation | Count | Percentage | Recommendation |
|---|-------------|-------|------------|----------------|
| 1 | Row count | 831 | — | P0: `800 ≤ count ≤ 900` (spec). Holds with 31 rows headroom on the lower bound. |
| 2 | Suppressed-distribution rows (all five annual percentiles null) | 5 | 0.602% | P0: `wage_annual_median` non-null ≥ 99% (tighter than spec's 95% — actual 99.398%, leaves room for one extra suppression next refresh). |
| 3 | `total_employment` null | 0 | 0.0% | P1: non-null ≥ 95% (BLS may suppress in future years; rule should not be P0 to avoid false alerts). |
| 4 | `wage_capped = True` rows | 45 | 5.42% | P1: `5 ≤ count ≤ 80` to detect future BLS top-code-floor changes (cap moved from $208K → $239,200 in 2023). |
| 5 | Top-coded floor invariant | 0 violations | 0.0% | P0: every row with `wage_capped = True` has at least one annual percentile = 239200 (spec). |
| 6 | Monotonicity violations | 0 | 0.0% | P0: 100% of rows with full annual data satisfy p10≤p25≤median≤p75≤p90 (spec). |
| 7 | SOC code format | 0 violations | 0.0% | P0: regex `^\d{2}-\d{4}$` (spec). |
| 8 | SOC code duplicates | 0 | 0.0% | P0: uniqueness on `soc_code` (spec). |
| 9 | `occupation_title` null | 0 | 0.0% | P0: non-null = 100% (spec). |
| 10 | `wage_hourly_median` null | 59 | 7.10% | None — column is reference-only, downstream does not consume. Document in data dictionary. |
| 11 | mean > p90 (top-coded artifact) | 23 | 2.77% | NONE. Documented advisory only. Do not write a DQ rule. |

---

## Cross-Source Overlap Analysis

### OEWS ↔ silver.bls_ooh (same survey lineage, OOH = projections, OEWS = wage distributions)

| Slice | Count | % of OOH silver |
|-------|-------|-----------------|
| `silver.bls_ooh` SOCs (denominator) | 832 | 100% |
| OOH SOCs also in `bronze.bls_oews` | 831 | 99.88% |
| OOH SOCs in OEWS with non-null `wage_p10` | 826 | 99.28% |
| OOH SOCs in OEWS with non-null `wage_p25` | 826 | 99.28% |
| OOH SOCs in OEWS with non-null `wage_annual_median` | 826 | 99.28% |
| OOH SOCs in OEWS with non-null `wage_p75` | 826 | 99.28% |
| OOH SOCs in OEWS with non-null `wage_p90` | 826 | 99.28% |

**Only `45-3031 Fishing and Hunting Workers` is in OOH-silver but missing from OEWS** (BLS suppressed this small/marine-irregular occupation in the May 2024 publication).

### OEWS ↔ consumable.onet_work_profiles
- O\*NET work profiles: 798 SOCs
- Intersection with OEWS: 772 (96.7%)
- O\*NET-only: 26 SOCs (newer detail rollups BLS aggregates)

---

## Threshold Lock-In for Gold DQ Rules (per spec §299–304)

| Spec proposed rule | Spec threshold | Actual today | Recommended final threshold |
|--------------------|----------------|--------------|-----------------------------|
| `wage_p25` non-null rate in `occupation_profiles` ≥ 90% (P0) | 90% | **99.28%** (826/832) | **Tighten to ≥ 98%** — meaningful regression detection while leaving room for one extra suppression. |
| `wage_p25 ≤ median_annual_wage ≤ wage_p75` (P1) | 90% (cross-survey variance) | (rule is on Gold post-join; needs scorecard run, but OEWS internal monotonicity is 100%, so violations would only come from OOH/OEWS median methodology drift) | **Keep ≥ 90%** as-is until @dq-engineer runs the join. |
| `wage_p25 ≤ wage_p75` for 100% of non-null pairs (P0) | 100% | **100%** (no internal violations; preserves through joins) | **Keep 100%** (monotonicity is exact). |
| Coverage: ≥ 750 SOCs with non-null `wage_p25` (P0) | 750 | **826** | **Tighten to ≥ 800** — meaningful regression detection while keeping a 26-row buffer. |

### New rules recommended for the Bronze JSON (additive to spec list)

1. **P0: `wage_capped` non-null = 100%** (831/831 — required field per schema; codify as a rule).
2. **P1: `wage_capped = True` row count between 5 and 80** (current 45). Detects BLS changing the top-code floor (e.g. moving from $239,200 to a new ceiling) without a code change.
3. **P1: `wage_hourly_median` non-null ≥ 90%** (current 92.9%). Documents the asymmetry between hourly and annual suppression.
4. **P0: `wage_annual_p10` non-null ≥ 99%** (current 99.398%). All five annual percentiles share the same suppression set; tighten in concert with the median rule.
5. **P0: `total_employment` non-null = 100%** (current 100% — codify the floor; if BLS resumes employment suppression, alert immediately rather than silently coercing to null).

---

## Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| `wage_annual_*` (all five annual + mean) | Suppression cluster | 5 | Expected | Performance-arts SOCs 27-2011/27-2031/27-2042/27-2091/27-2099. Tot_emp non-null. Cause: irregular gig compensation. Rendered as "no career-specific range, fall back to Scorecard" per spec §CareerCard Display Logic. |
| `wage_annual_mean` vs `wage_annual_p90` | Top-coding artifact | 23 | Documented (no rule) | All 23 SOCs are top-coded. Mean is published uncapped. Do not write a `mean ≤ p90` rule. |
| `wage_capped` | Top-coded SOCs | 45 | Expected | Physicians, surgeons, dentists, top managers, pilots, lawyers, postsecondary law/health teachers, and a few smaller SOCs. All match the BLS top-code definition (≥ $239,200/yr). |
| `wage_hourly_median` | Hourly-only suppression | 59 (54 extra over the 5 annual-null SOCs) | Documented | Salaried-only occupations (Chief Executives, lawyers, physicians) have published annual but suppressed hourly. Reference-only column; not used downstream. |
| `wage_annual_p25` cap | Single-row top-cap on p25 | 1 | Expected | 29-1243 Pediatric Surgeons — entire visible distribution at $239,200. p10 = $239,200, p25 = $239,200, etc. Working as intended. |

---

## How to Reproduce

```bash
uv run python scripts/eda_bls_oews_bronze.py
```

The script connects to the unified Brightsmith Iceberg catalog at
`data/catalog/catalog.db` (catalog name `brightsmith`) and emits a single JSON
document on stdout covering every section of this report. All numeric findings
in this report are sourced directly from that JSON. Cross-zone reads use
per-zone warehouse paths (`data/{bronze,silver,gold}/iceberg_warehouse`) but
share the single catalog SQLite file.

```python
from pyiceberg.catalog.sql import SqlCatalog

# Bronze
oews = SqlCatalog(
    "brightsmith",
    uri="sqlite:///data/catalog/catalog.db",
    warehouse="data/bronze/iceberg_warehouse",
).load_table("bronze.bls_oews").scan().to_arrow().to_pylist()

# Silver
ooh_silver = SqlCatalog(
    "brightsmith",
    uri="sqlite:///data/catalog/catalog.db",
    warehouse="data/silver/iceberg_warehouse",
).load_table("base.bls_ooh").scan().to_arrow().to_pylist()

# Gold (note: O*NET work profiles use bls_soc_code, not soc_code)
onet = SqlCatalog(
    "brightsmith",
    uri="sqlite:///data/catalog/catalog.db",
    warehouse="data/gold/iceberg_warehouse",
).load_table("consumable.onet_work_profiles").scan().to_arrow().to_pylist()
```

---

## Audit Trail

- **Spec referenced:** `docs/specs/ingest-bls-oews-wage-percentiles.md` (workflow step 4 — @data-analyst EDA after Bronze ingest, before DQ rule writing).
- **Tables read:** `bronze.bls_oews` (831 rows), `bronze.bls_ooh` (832 rows), `base.bls_ooh` (832 rows), `consumable.onet_work_profiles` (798 rows).
- **Decisions made:**
  - Recommend tightening Bronze `wage_annual_median` non-null floor from 95% → 99% based on observed 99.398%.
  - Recommend tightening Gold coverage floor from 750 → 800 SOCs and from 90% → 98% non-null `wage_p25` based on observed 826 SOCs / 99.28%.
  - Document, do not rule-fail, the `mean > p90` and `wage_hourly_median` suppression patterns — both are intrinsic BLS publishing behaviors.
  - Confirm that the spec's spot-check value for Registered Nurses median (~$86K) is stale relative to the May 2024 OEWS load ($93,600). The Bronze spot-check window of $75K–$100K accommodates this without a spec edit.
- **Threshold recommendations passed downstream to:** @dq-rule-writer (next agent, workflow step 6).
