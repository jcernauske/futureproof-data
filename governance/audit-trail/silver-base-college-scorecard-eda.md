# Audit Trail: Silver EDA — base.college_scorecard

**Date:** 2026-04-06
**Agent:** @data-analyst
**Spec:** docs/specs/silver-base-college-scorecard.md
**Zone:** Silver (Step 6 of greenfield workflow)
**Output:** governance/eda/silver-college-scorecard-eda.md

## What Was Analyzed

Profiled `raw.college_scorecard` from the Bronze zone parquet (69,947 rows, 16 columns) from the perspective of the Silver base table transformations. Also examined:
- `tests/raw/college_scorecard_sample.csv` (50 rows, for CONTROL field format)
- `tests/raw/college_scorecard_columns.txt` (full source CSV column listing)
- `src/raw/college_scorecard_ingestor.py` (CONTROL field handling)

## Key Findings

1. **CRITICAL: CIP code CHECK constraint mismatch.** Physical model CHECK `^\d{2}\.\d{4}$` expects XX.XXXX (7 chars) but data produces XX.XX (5 chars) after transformation. All 69,947 rows would be rejected. Must fix to `^\d{2}\.\d{2}$`.

2. **CRITICAL: CONTROL column missing from parquet.** Ingestor schema includes field 17 (control) but existing parquet files do not contain this column. Blocks Silver transformer.

3. **HIGH: CONTROL derivation assumes integer input.** Physical model says `{1: 'Public', ...}[int(raw_control)]` but source CSV stores CONTROL as text labels ("Public", etc.). Derivation must be updated.

4. **INFO: small_cohort_flag True for 75.52% of rows.** 52,826 of 69,947 programs have completions_count_1 IS NULL or < 30. Only 24.48% will be unflagged.

5. **INFO: Earnings suppression differs between 1yr and 2yr for 12.27% of rows.** 8,585 rows have different null/present status. Rules must not assume joint suppression.

## Threshold Recommendations

Provided 18 specific DQ threshold recommendations with supporting evidence:
- Row count: 60,000-80,000
- Grain uniqueness: 0 duplicates (hard constraint)
- Null rates: earnings at 65-70%, completions at 12%
- CIP format: `^\d{2}\.\d{2}$` (corrected from physical model)
- small_cohort_flag True rate: 70-80%
- All range constraints: 0 violations in current data

## Blocking Issues Identified

| Issue | Blocks | Resolution Required |
|-------|--------|---------------------|
| CIP CHECK constraint wrong | DQ rule writing, transformer implementation | Fix physical model CHECK |
| CONTROL missing from parquet | Silver transformer | Re-run raw ingestor |
| CONTROL derivation assumes integers | Silver transformer | Update derivation expression |
