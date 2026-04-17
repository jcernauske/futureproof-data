# Audit Trail: bs:data-analyst — raw.onet_experience EDA

**Agent:** bs:data-analyst
**Date:** 2026-04-16
**Spec:** `docs/specs/onet-experience-requirements.md`
**Zone:** Bronze (Zone 1)
**Step:** Agent Workflow Phase 2, step 5 — EDA on `raw.onet_experience`

## What Was Analyzed

- Table: `raw.onet_experience` (physically at `data/bronze/iceberg_warehouse/bronze/onet_experience/`)
- Scope: All 35,998 rows ingested by `OnetExperienceIngestor` in the current Bronze load.
- Method: DuckDB directly against the Iceberg data parquet (the namespace entry was not registered in the SQL catalog at ingest time; disk layout is Iceberg-correct but `catalog.load_table("bronze.onet_experience")` raised `NoSuchTableError`). Reading the Parquet data file directly returns the full table because the ingestor wrote a single snapshot.

## Key Findings

1. **Row count: 35,998** — within P0 Bronze rule `30,000 ≤ count ≤ 45,000`.
2. **4 scales (RL, RW, PT, OJ) all present for every one of 878 distinct O*NET-SOC codes.**
3. **765 distinct BLS SOC codes** (after 7-char truncation) — **this will be the Silver row count**, not the spec's 867.
4. **Spec drafting errors discovered:** (a) spec says OJ has 11 categories; observed is 9, for every occupation; (b) spec's "~1,016 occupations" comes from Occupation Data, not from the ETE file (878); (c) the RW P1 row-count band (11,000-12,000) is based on the wrong occupation count — observed RW rows = 9,658 (878 × 11).
5. **Spot checks confirmed:** 11-1011.00 (CEOs) weighted median cat = 11 → senior; 41-2031.00 (Retail) weighted median cat = 5 → entry (bimodal distribution, 39.75% at cat 1 + 32.02% at cat 5); 15-1252.00 (Software Developers) weighted median cat = 9 → mid.
6. **Edge cases:** 0 occupations with all RW rows suppressed; 0 occupations with single-category 100%; 754 / 878 (85.9%) of occupations have no single RW category above 50% — weighted-median logic is mandatory.
7. **Suppression rate: 2.4% overall** (2.2% on RW). `recommend_suppress='n/a'` corresponds 1:1 with Occupational Expert source (8,610 rows).
8. **Data integrity clean:** 0 `data_value` out-of-range, 0 format violations, 0 per-group sum outliers (max |dev| 0.03 from 100).

## Deliverables Produced

- `governance/eda/raw-onet-experience-eda.md` — full EDA report (~360 lines).
- `docs/sessions/eda-raw-onet-experience-stats.json` — raw stats dump consumed by the report.
- `scripts/eda_raw_onet_experience.py` — reproducible EDA query script.

## Threshold Recommendations for bs:dq-rule-writer

- Bronze `row_count`: `30,000 ≤ count ≤ 45,000` (P0, observed 35,998).
- Bronze `rw_row_count`: **rewrite to `9,000 ≤ count ≤ 12,500`** (P1; spec's 11,000-12,000 is wrong).
- Bronze `categories_by_scale`: **rewrite OJ from 11 to 9** (RL=12, RW=11, PT=9, OJ=9).
- Bronze `data_value_range`: `0.0 ≤ data_value ≤ 100.0` (P0, 0 violations).
- Bronze `per_group_sum`: `|SUM - 100| ≤ 0.1` (P1, 0 violations at even 0.05).
- Bronze `suppression_rate`: `Y rate ≤ 0.05` (P1, observed 0.024).
- Bronze `recommend_suppress_values`: `IN ('N','Y','n/a')` (P0).
- Bronze `domain_source_values`: `IN ('Incumbent','Occupational Expert')` (P0) — narrower than other O*NET files.
- Bronze `element_id_values`: `IN ('2.D.1','3.A.1','3.A.2','3.A.3')` (new P0 recommendation).
- Silver `row_count`: **rewrite from `800-900` to `720-810`** (observed 765 BLS SOCs).
- Silver spot-check `11-1011 tier = senior` — confirmed safe.
- Silver spot-check `41-2031 tier = entry` — confirmed safe. **Do NOT write a `median_category ≤ 3` rule** for 41-2031 (actual = 5).
- Silver spot-check `15-1252 tier = mid` — new recommendation (not in spec but low-risk).

## Data Quality Red Flags

**None blocking.** The three delta items above are spec threshold updates, not data integrity violations. The ingested data itself is clean.

## Cross-Agent Handoffs

- **bs:dq-rule-writer (next step):** Use the threshold recommendations above. Spec's Bronze P0/P1 list needs threshold revisions per findings 3, 4, 5.
- **bs:domain-context:** Document the ETE methodology (two `domain_source` values, 4 scales with specific element IDs, rolling annual survey update cadence).
- **bs:semantic-modeler (already ran; Silver model):** Row count expectation in the Silver physical model may need updating from ~867 to ~765.
- **bs:chaos-monkey:** The "all RW rows suppressed" and "single-category 100%" edge cases have zero real-data triggers. Synthesize them.
