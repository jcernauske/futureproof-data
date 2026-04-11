# Audit Trail: EDA -- raw-karpathy-ai-exposure

**Agent:** @data-analyst
**Timestamp:** 2026-04-09T19:00:00Z
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Dataset:** bronze.karpathy_ai_exposure (342 rows, 13 fields)

## Actions Taken

1. Read the raw-ingest-karpathy-ai-exposure spec to understand expected schema, grain, and DQ thresholds
2. Connected to the Bronze Iceberg table via DuckDB parquet reader
3. Profiled all 13 fields: types, null rates, cardinality, distributions
4. Analyzed exposure score distribution (histogram, percentiles, mean/median/stddev)
5. Analyzed category distribution (25 categories, row counts, avg scores, null SOC rates per category)
6. Performed SOC code coverage analysis: 290/342 with SOC (84.8%), 52 null
7. Identified 46 "broad" SOC codes (XX-XXX0 pattern) that don't match BLS OOH detailed codes
8. Cross-validated median_pay_annual against bronze.bls_ooh.median_annual_wage for 241 matching rows -- zero discrepancies
9. Analyzed slug patterns, rationale length distribution, entry education distribution
10. Computed exposure-pay correlation (r=0.387) and exposure-by-education breakdown
11. Assessed BLS coverage potential: 244 direct match + 351 possible via broad-to-detailed expansion

## Key Findings

- SOC coverage is 84.8%, not the 95% estimated in spec -- threshold must be revised
- 46 broad SOC codes need Silver zone resolution (not anticipated in spec)
- Perfect wage alignment with BLS OOH ($0 diff on all 241 comparable rows)
- Score range is 1-10 (no zeros observed); score 7 is overrepresented at 20.5%
- All required fields (slug, title, category, score, rationale) are 100% non-null
- Grain uniqueness holds: 342 distinct slugs, 342 distinct titles, 290 distinct SOC codes (among non-null)

## Threshold Recommendations

| Rule | Spec Value | Recommended Value | Evidence |
|------|-----------|-------------------|----------|
| SOC coverage | ~95% | >= 84% | 290 of 342 have SOC (84.8%) |
| Score range | 0-10 | 0-10 (keep) | Effective 1-10 but 0 is valid per methodology |
| Wage cross-val diff | >20% | >20% (keep) | 0% divergence -- trivially passes |
| Rationale min length | (none) | 250 chars | Shortest observed is 297 |

## Artifacts Produced

- `governance/eda/raw-karpathy-ai-exposure-eda.md` -- full EDA report
- `governance/audit-trail/raw-karpathy-ai-exposure-eda.md` -- this file
