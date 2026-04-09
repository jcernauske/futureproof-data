# Audit Trail: O*NET Raw Ingest EDA

**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-onet.md`
**Timestamp:** 2026-04-07
**Action:** Exploratory Data Analysis on O*NET 30.2 database (Bronze zone profiling)

## Dataset Analyzed

O*NET 30.2 Database downloaded from `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip`. Five of 7 target files were present in the archive. Two files (Career Changers Matrix, Career Starters Matrix) were not found in the ZIP or as separate downloads.

## Key Findings

1. **Two of 7 files missing from source.** Career Changers Matrix and Career Starters Matrix are not in the O*NET 30.2 text ZIP archive. The corresponding ingestors will fail at runtime.
2. **Related Occupations schema changed.** Column `Related Index` in spec is actually named `Index` in the file. New `Relatedness Tier` column exists with values Primary-Short/Primary-Long/Supplemental. Ingestor will skip 100% of rows due to the column name mismatch.
3. **Work Context row count is 6x spec estimate** (297,676 vs ~49,000) due to CXP/CTP category-percentage rows. Not a bug -- the spec underestimated.
4. **Occupation Data has 1,016 rows, not ~886.** O*NET 30.2 has more occupations than the spec estimated.
5. **93 "All Other" and Military occupations** have no data in any file beyond Occupation Data. This is expected -- O*NET does not survey residual categories.
6. **16 occupations have partial Work Context** (57 rows instead of 338, missing CXP/CTP percentage data).
7. **All referential integrity checks pass** -- no orphan SOC codes in any child table.
8. **All SOC codes pass XX-XXXX.XX format validation** -- 0 invalid across all files.

## Anomalies Discovered

- 1,063 Work Activities rows (1.5%) have recommend_suppress="Y"
- 1,094 Work Activities rows (1.5%) have not_relevant="Y" (only on LV scale)
- 7,484 Work Context rows (2.5%) have recommend_suppress="Y"
- 1,190 Task Statements (6.3%) have null Incumbents Responding (all Analyst/Analyst-Transition sources)

## Domain Discovery

- O*NET uses extended SOC codes (XX-XXXX.XX) vs BLS 6-digit (XX-XXXX)
- 76 BLS SOCs map to multiple O*NET detailed codes
- 4 distinct Work Context scale types (CX, CXP, CT, CTP) with different ranges
- 2 Work Activities scale types (IM: Importance 1-5, LV: Level 0-7)
- Domain sources: Incumbent (survey), Occupational Expert (panel), Analyst (derived), Analyst - Transition (recently recoded)

## Threshold Recommendations

Detailed threshold recommendations provided in the EDA report at `governance/eda/raw-onet-eda.md` for all 5 available tables. Key thresholds:
- IM scale: [1.0, 5.0]
- LV scale: [0.0, 7.0]
- CX scale: [1.0, 5.0]
- CXP/CTP: [0.0, 100.0]
- CT scale: [1.0, 3.0]
- Related Occupations Index: [1, 20], exactly 20 per occupation

## Artifacts Produced

- `governance/eda/raw-onet-eda.md` -- Comprehensive EDA report covering all 7 tables
- `governance/audit-trail/raw-ingest-onet-eda.md` -- This audit trail entry
- `data/raw/onet_cache/` -- 5 cached source files for offline access
