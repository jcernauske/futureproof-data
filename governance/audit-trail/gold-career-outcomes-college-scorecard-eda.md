# Audit Trail: Gold Career Outcomes EDA

**Agent:** @data-analyst
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Step:** 6 (EDA on Silver base data for Gold thresholds)
**Timestamp:** 2026-04-06
**Session:** gold-career-outcomes-eda

## Dataset Analyzed

- **Table:** base.college_scorecard (Silver zone)
- **Location:** data/silver/iceberg_warehouse/base/college_scorecard/data/00000-0-fc47f753-104a-409b-bc99-5fb735f9d2a8.parquet
- **Row Count:** 69,947
- **Column Count:** 18

## Actions Taken

1. Read Gold spec, logical model, and Silver EDA for context
2. Profiled null rates and outcome completeness patterns across 3 core outcome fields
3. Computed CIP family non-null counts to identify which families get null percentile bands
4. Simulated percentile band computations (PERCENTILE_CONT p25/p50/p75) for all 45 CIP families
5. Computed debt-to-earnings ratio distribution and tier breakdown
6. Computed earnings growth rate distribution and negative rate
7. Derived confidence tier distribution from small_cohort_flag + data availability
8. Simulated PERCENT_RANK for CIP family earnings rank
9. Profiled program value index distribution
10. Identified all outliers against spec-defined ranges
11. Verified p25 <= p75 invariant (0 violations)
12. Documented institution_control 100% NULL status (inherited from Silver)

## Artifacts Produced

- **EDA Report:** governance/eda/gold-career-outcomes-eda.md
- **Audit Trail:** governance/audit-trail/gold-career-outcomes-college-scorecard-eda.md

## Key Findings

1. Debt-to-earnings "Low" tier is the plurality at 69.23%, contradicting spec expectation of "Moderate"
2. 52.75% of rows will be "insufficient" confidence tier (within spec range of 50-55%)
3. 44.2% of earnings growth rates are negative (expected, cross-cohort data)
4. 7 CIP families will receive null 1yr percentile bands (36 rows, 0.05%)
5. Zero outliers outside the 0.01-10.0 debt-to-earnings range
6. 15 outliers (0.068%) outside the -0.5 to 2.0 earnings growth range
7. institution_control is 100% NULL (blocking issue inherited from Bronze)
8. "medium" confidence tier is unexpectedly small at 1.79%

## Decisions Made

- Recommended correcting the spec's DTE tier distribution expectation ("Low" is plurality, not "Moderate")
- Recommended 12 P0 hard constraints, 14 P1 soft constraints, 4 P2 informational rules
- Flagged institution_control as blocking for Gold NOT NULL constraint
- Documented 4 single-member CIP families where PERCENT_RANK = 0.0 by definition

## Downstream Impact

- @dq-rule-writer: 30 threshold recommendations with supporting evidence
- @primary-agent: institution_control handling decision needed before transformer implementation
- Spec update recommended: DTE tier distribution expectation
