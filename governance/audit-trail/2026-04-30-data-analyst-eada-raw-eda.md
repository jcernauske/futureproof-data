# 2026-04-30 — @bs:data-analyst — EADA Raw EDA (BLOCKING gate)

**Spec:** `docs/specs/full-pipeline-eada.md` §3 + §4 (Raw)
**Agent:** @bs:data-analyst (FutureProof: @fp-data-reviewer surrogate)
**Outcome:** EDA produced. **BLOCKING gate cleared with caveats** — orchestrator must update `EadaIngestor` column constants before raw promotion.

## Datasets analyzed
- `EADA_2022-2023.zip` from `https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_2022-2023.zip` (HTTP 200, 11.7 MB)
- `InstLevel.xlsx` (2,040 institution rows × 168 cols) — converted to CSV at `data/raw/eada_cache/eada_2022.csv`.
- `Schools.xlsx` (17,886 per-team rows × 129 cols) — examined for SPORTSCODE marker; not ingested.
- `bronze.college_scorecard_institution` (3,039 distinct UNITIDs) — UNITID-overlap comparator.

## Key findings
1. **Spec column names are wrong.** `EXP_TOTAL_TOTAL` / `REV_TOTAL_TOTAL` / `RECRUITEXP_TOTAL_TOTAL` do not exist. Pinned `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL` instead. Identity columns are `unitid` / `institution_name` (lowercase), not `UNITID` / `INSTNM`.
2. **Institution totals live in a separate file.** `InstLevel.xlsx` is one row per UNITID by construction. The "filter on `SPORT_CODE NULL`" model is incorrect; pinned `INSTITUTION_TOTAL_FILTER_COLUMN=None`.
3. **Bulk download endpoint discovered:** `https://ope.ed.gov/athletics/api/dataFiles/file?fileName=<FileName>` (unauthenticated, accepts custom User-Agent).
4. **Suppression sentinels never observed at institution level** — all three monetary fields 100% non-null across 2,040 rows. RAW-EAD-007/008/009 thresholds (95/95/80%) are far below observed reality.
5. **D1-FBS anchors confirmed** — Ohio State $234M, USC $212M, Notre Dame $204M. RAW-EAD-011 passes with margin.
6. **UNITID overlap with `bronze.college_scorecard_institution`: 74.5%.** 521 of 2,040 EADA institutions are missing from College Scorecard, almost entirely 2-year colleges (NJCAA + CCCAA + NWAC). **BSE-EAD-009's 95% threshold is unrealistic.**
7. **Revenue ≈ Expense at GRND_TOTAL level** by EADA reporting convention. **BSE-EAD-010 ("subsidy P50 > 0") will fail.** The signal lives in `direct_institutional_support`, which is not in the raw schema.
8. **EADA carries `EFTotalCount` natively** — recommend @bs:semantic-modeler reconsider FTE source for base zone.

## Threshold recommendations (with evidence)
- RAW-EAD-007/008/009: tighten from 95/95/80 → 99/99/99 (observed: 100/100/100). Defer final decision to @bs:dq-rule-writer.
- RAW-EAD-012: post-filter conservation rule is now tautological. Drop or repurpose.
- BSE-EAD-009: drop from 95% to ~75%, OR switch FTE source to in-EADA `EFTotalCount`.
- BSE-EAD-010: defer until `direct_institutional_support` is in scope.

## Artifacts produced
- `governance/eda/full-pipeline-eada-raw-eda.md` (306 lines, includes "EadaIngestor Configuration Pin" section)
- Appended provisional EADA section to `governance/domain-context.md`
- Cached:
  - `data/raw/eada_cache/EADA_2022-2023.zip` (11.7 MB)
  - `data/raw/eada_cache/eada_2022_instlevel.xlsx` (1.5 MB)
  - `data/raw/eada_cache/eada_2022_schools.xlsx` (5.8 MB)
  - `data/raw/eada_cache/eada_2022.csv` (2,041 lines incl. header)

## Gates flagged for orchestrator (before running ingestor)
1. Update `EadaIngestor` column constants per the EDA's "EadaIngestor Configuration Pin" section.
2. Apply the small `_is_institution_total()` short-circuit when `filter_column is None`.
3. Tighten RAW-EAD-007/008/009 thresholds in DQ rule writer's brief.
4. Hold BSE-EAD-009 and BSE-EAD-010 for base-zone re-review.

## Deferred
- UNITID overlap with `consumable.career_outcomes` — table does not yet exist.
- UNITID overlap with `base.ipeds_finance` — table does not yet exist.
