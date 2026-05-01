# Audit Trail: `raw.ipeds_finance` EDA (BLOCKING gate before raw promote)

**Date:** 2026-04-30
**Agent:** @bs:data-analyst
**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` (v1.3) §4 EDA Requirements 1–7
**Output:** `governance/eda/full-pipeline-ipeds-finance-raw-eda.md`

## What was analyzed and why

The orchestrator gated raw promote on confirming all v1.3-locked column codes against live IPEDS dictionaries, computing distributions, form mix, HD-filter coverage, scorecard UNITID overlap, F3 sparseness, and bureau-imputation prevalence — all on the most-recent fully-published Finance cycle. The pre-flight (`raw-ingest-ipeds-finance-preflight.md`) had already locked the column codes against FY22, but the full evidence run on FY23 was the BLOCKING gate.

## Datasets pulled

- **From IPEDS Data Center** (`https://nces.ed.gov/ipeds/datacenter/data/`): FY23 finance forms (`F2223_F1A.zip`, `F2223_F2.zip`, `F2223_F3.zip`), dictionaries (`*_Dict.zip`), `EFIA2023.zip`, `HD2023.zip`. All 200 OK. Cached to `data/raw/ipeds_finance_cache/`.
- **FY24 attempted, all 404:** NCES has not yet published FY24 Finance. Promote target reverts to **FY23 (provisional)**.
- **From local Iceberg:** `bronze.college_scorecard_institution` parquet (3,039 distinct UNITIDs) for cross-source overlap.

## Key findings (BLOCKING resolutions)

1. **All 8 column codes verified at byte level** against FY23 dictionary varlist sheets (`F1C011`, `F1C071`, `F1H02`, `F2E011`, `F2E061`, `F2H02`, `F3E011`, `F3E03C1`) — each entry confirms the matching `XF*` imputation flag companion.
2. **EFIA2023 grain confirmed: 5,959 rows / 5,959 distinct UNITIDs** with no `LEVEL`/`LSTUDY`/`EFFYALEV` breakdown column. **NO dedup filter required.** Refutes the v1.2 fan-out concern (which was real for `EFFY*` but not for `EFIA`).
3. **`FTE_TOTAL` and `FTE` do not exist in any IPEDS file.** The total FTE must be computed as the NULL-safe sum `COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0)`. Current ingestor reads a single column — code change required.
4. **5-institution spot check passes:** Berkeley/UGA/UNC-CH/Stanford match published values within 1%. **Preflight had IU-Bloomington UNITID wrong (152228 → actual 151351)**; corrected and verified 47,611 total FTE on 38,356/8,002/1,253 UG/GD/DPP breakdown.
5. **Post-HD-filter row count = 2,675** (NOT 5,000–8,000 as RAW-IPF-001 says). The 5,000–8,000 band is a v1.0/v1.1 artifact pre-dating the `ICLEVEL=1 AND HLOFFER>=5` filter narrowing.
6. **UNITID overlap with `bronze.college_scorecard_institution` = 98.0%** of finance / 86.2% of scorecard (2,621 / 2,675). Excellent silver-zone join surface.
7. **Form mix:** F1A 30.6% / F2 59.0% / F3 10.4% (831/1579/277 rows). F3 endowment 100% structurally NULL (expected); F3 institutional support **0% NULL** (post-2014-15 schedule populated; refutes pre-v1.3 hypothesis).
8. **Imputation prevalence ≤1.22% on every field.** §2 Decision #8 (accept bureau-imputed values) is well-calibrated. Recommend NOT flipping in v1.3.
9. **Marketing ratio (institutional_support / instruction) median by form:** F1A 0.39, F2 0.73, **F3 1.06** — for-profits' marketing-heavy spend pattern is exactly the signal the consumable `marketing_ratio` is designed to surface, not a data quality issue.

## Gates the orchestrator must close before running the ingestor

1. **Configuration overrides (BLOCKING):**
   - `fiscal_year=2023` (NOT 2024 — FY24 not released)
   - `f3_instruction_col="F3E011"` (NOT default `"F3E01"`)
   - `f3_institutional_support_col="F3E03C1"` (NOT default `None`)
   - `effy_file_prefix="EFIA"` (NOT default `"EFFY"`)
   - `effy_file_suffix=""` (NOT default `"A"`)
   - `effy_dedup_col=None`, `effy_dedup_value=None` (no dedup needed for EFIA)

2. **Code change (BLOCKING):** `_build_effy_lookup` (rename to `_build_efia_lookup`, lines 660–719 of `src/raw/ipeds_finance_ingestor.py`) must compute the three-column NULL-safe sum `FTEUG+FTEGD+FTEDPP` instead of reading a single `effy_fte_col`.

3. **DQ rule recalibration (NON-BLOCKING):** RAW-IPF-001 row-count band needs revision from `5,000–8,000` to `2,500–3,200` before running DQ rules.

## Threshold recommendations for @bs:dq-rule-writer

See §12 of the EDA report for the complete table. Highlights:
- RAW-IPF-001: revise to `2,500–3,200`
- RAW-IPF-009/010/011/012: hold current thresholds; all pass with margin
- NEW RAW-IPF-015 (suggested): codify F3 endowment_value = NULL for all F3 rows (structural assertion)
- NEW RAW-IPF-016 (suggested): per-form row-count bounds catching future form-mix shifts

## Decisions made

- **FY23 not FY24** as the immediate promote target. NCES hasn't released FY24 Finance.
- **Refute pre-v1.3 hypothesis** that F3 omits institutional support — `F3E03C1` is 100% populated.
- **Hold §2 Decision #8** (accept bureau-imputed values). Imputation rate ≤1.22% across all fields; flipping the policy is not warranted.

## Artifacts produced

- `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` (full EDA report)
- `governance/domain-context.md` (added IPEDS Finance section + revision-history row)
- `scripts/eda_ipeds_finance_raw.py` (reproducible analysis script)
- `data/raw/ipeds_finance_cache/` (cached 9 source files for promote)
- This audit-trail entry
