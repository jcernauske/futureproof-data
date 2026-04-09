# Audit Trail: Gold Occupation Profiles EDA

**Date:** 2026-04-07
**Agent:** @data-analyst
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Action:** Pre-implementation EDA on Silver `base.bls_ooh` to validate Gold derivation design

## What Was Analyzed

- Silver table `base.bls_ooh` (832 rows, 25 fields) via DuckDB + Iceberg
- All Gold-specific derivations computed in preview: GRW score, market score, wage percentiles, wage tiers, confidence tiers, data completeness
- 3 golden dataset values independently verified
- Edge cases, boundary values, and null-handling behavior tested

## Key Findings

1. GRW score distribution validates spec design (mean 5.321, all 10 buckets populated)
2. Market score distribution healthy (stddev 1.607, 9 of 10 buckets populated)
3. **SPEC ERROR FOUND:** Golden dataset #3 (29-1215 Family Medicine Physicians) incorrectly stated as null-wage; actual wage = $238,380
4. **CRITICAL:** Null wages in PERCENT_RANK window corrupt percentile positions; must filter before ranking
5. 3 null-wage occupations overlap with catchall flag; confidence tier logic must check wage first
6. DuckDB ROUND uses standard rounding (half up), not banker's rounding
7. data_completeness produces only {0.75, 1.0}, not the full theoretical range

## Threshold Recommendations

- GRW mean target: widen from 5.5-6.5 to 4.5-6.5
- Market score bucket 10: will be empty; do not require
- Confidence tier counts: high=735, medium=74, low=23
- Wage tier null count: exactly 23

## Artifacts Produced

- EDA report: `governance/eda/gold-occupation-profiles-eda.md`

## Decisions

| Decision | Rationale |
|----------|-----------|
| Recommend 29-1211 as replacement for golden dataset #3 | 29-1215 has wage data in actual BLS dataset; 29-1211 Anesthesiologists is a clean null-wage candidate |
| Recommend widening GRW mean threshold | Distribution is left-skewed by declining occupations; strict 5.5-6.5 would fail |
| Flag education_code=6 small tier | Only 6 occupations; percentile within tier has very coarse resolution |
