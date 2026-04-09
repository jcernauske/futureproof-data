# Lineage Audit Trail: silver-base-college-scorecard

**Agent:** @lineage-tracker
**Timestamp:** 2026-04-06T20:00:00Z
**Spec:** docs/specs/silver-base-college-scorecard.md
**Lineage File:** governance/lineage/silver-base-college-scorecard-20260406T200000Z.json

## Pre-existing Lineage

- **Bronze lineage exists:** Yes (`governance/lineage/raw-ingest-college-scorecard-20260406T031047Z.json`)
- **Silver lineage existed:** No -- this is the first capture

## Transformations Captured

| # | Transformation | Type | Source Field(s) | Target Field |
|---|---------------|------|-----------------|--------------|
| 1 | CIP code normalization | DERIVED | cipcode | cipcode |
| 2 | CIP family extraction | DERIVED | cipcode | cip_family |
| 3 | CIP family name lookup | DERIVED | cipcode | cip_family_name |
| 4 | Institution control mapping | DERIVED | control | institution_control |
| 5 | Small cohort flag | DERIVED | ipedscount1 | small_cohort_flag |
| 6 | Record ID grain hash | DERIVED | unitid, cipcode, credlev | record_id |
| 7 | Ingested_at timestamp | DERIVED | (generated) | ingested_at |
| 8 | Column rename: instnm | DIRECT | instnm | institution_name |
| 9 | Column rename: cipdesc | DIRECT | cipdesc | program_name |
| 10 | Column rename: credlev | DIRECT | credlev | credential_level |
| 11 | Column rename: creddesc | DIRECT | creddesc | credential_description |
| 12 | Column rename: earn_mdn_hi_1yr | DIRECT | earn_mdn_hi_1yr | earnings_1yr_median |
| 13 | Column rename: earn_mdn_hi_2yr | DIRECT | earn_mdn_hi_2yr | earnings_2yr_median |
| 14 | Column rename: debt_all_stgp_eval_mdn | DIRECT | debt_all_stgp_eval_mdn | debt_median |
| 15 | Column rename: ipedscount1 | DIRECT | ipedscount1 | completions_count_1 |
| 16 | Column rename: ipedscount2 | DIRECT | ipedscount2 | completions_count_2 |
| 17 | Column rename: load_date | DIRECT | load_date | source_load_date |
| 18 | Direct copy: unitid | DIRECT | unitid | unitid |

## Dropped Fields

| Field | Reason |
|-------|--------|
| md_earn_wne | 100% null at field-of-study grain (user-confirmed) |
| source_url | Raw metadata not needed in Silver |
| source_method | Raw metadata not needed in Silver |

## Runtime Metrics Captured

- **Rows read from Bronze:** 69,947
- **Rows transformed:** 69,947
- **Rows skipped (null grain):** 0
- **Rows promoted to Silver:** 69,947
- **Dedup skipped:** 0
- **Snapshot ID:** 8709179988001255822

## Verification Checklist

- [x] Every output field has column lineage traced to source field(s)
- [x] All 18 output fields accounted for in columnLineage
- [x] All 3 dropped fields documented with justification
- [x] Runtime metrics (row counts, snapshot ID) included in run facets
- [x] Spec reference points to correct spec file
- [x] Agent attribution recorded (@primary-agent performed the transformation)
- [x] Source code location recorded (src/silver/college_scorecard_transformer.py)
- [x] Input schema matches raw.college_scorecard Iceberg table
- [x] Output schema matches base.college_scorecard physical model
- [x] Transformation types correctly classified (DIRECT vs DERIVED)

## Naming Decisions

- **Job name:** `silver.transform-college-scorecard` -- follows `{zone}.{action}-{source}` convention
- **Input dataset:** `raw.college_scorecard` -- matches Bronze Iceberg table identifier
- **Output dataset:** `base.college_scorecard` -- matches Silver Iceberg table identifier (uses `base` namespace per Brightsmith convention for Silver zone modeled tables)

## Notes

- The `control` field is listed in the input schema. The spec notes this field requires a raw schema update to include CONTROL from the source CSV. The transformer handles it gracefully (maps to null if not present in Bronze).
- The promote pattern noted a minor `table.identifier` attribute issue during execution, but the promotion completed successfully with all 69,947 rows written and snapshot ID captured.
- End-to-end lineage chain is now complete: ed.gov CSV -> raw.college_scorecard (Bronze lineage) -> base.college_scorecard (this Silver lineage).
