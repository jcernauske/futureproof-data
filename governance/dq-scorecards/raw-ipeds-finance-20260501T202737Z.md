# DQ Scorecard - raw-ipeds-finance

- **Spec:** `full-pipeline-ipeds-finance`
- **Table:** `bronze.ipeds_finance`
- **Snapshot:** `2955168649587464831`
- **Rules file:** `governance/dq-rules/raw-ipeds-finance.json`
- **Executed at:** 2026-05-01T20:27:37.062247+00:00
- **Executed by:** @dq-engineer
- **Row count:** 2675

## Summary

- **Overall pass:** True
- **P0 gate:** PASS (12/12 passed)
- **P1:** 2/2 passed

## Results

| rule_id | priority | dimension | status | expected | actual | notes |
|---|---|---|---|---|---|---|
| RAW-IPF-001 | P0 | volume | PASS | result = 0 | 0 | Row count between 2,500 and 3,200 |
| RAW-IPF-002 | P0 | completeness | PASS | result_count = 0 | 0 rows | unitid non-null (100%) |
| RAW-IPF-003 | P0 | uniqueness | PASS | result_count = 0 | 0 rows | unitid uniqueness (dedup grain) |
| RAW-IPF-004 | P0 | validity | PASS | result_count = 0 | 0 rows | report_form in {F1A, F2, F3} |
| RAW-IPF-005 | P0 | validity | PASS | result_count = 0 | 0 rows | instruction_expenses >= 0 where non-null |
| RAW-IPF-006 | P0 | validity | PASS | result_count = 0 | 0 rows | institutional_support_expenses >= 0 where non-null |
| RAW-IPF-007 | P0 | validity | PASS | result_count = 0 | 0 rows | endowment_value >= 0 where non-null |
| RAW-IPF-008 | P0 | validity | PASS | result_count = 0 | 0 rows | total_fte_enrollment > 0 where non-null |
| RAW-IPF-009 | P0 | completeness | PASS | result = 0 | 0 | instruction_expenses non-null >= 90% |
| RAW-IPF-010 | P0 | completeness | PASS | result = 0 | 0 | institutional_support_expenses non-null >= 90% |
| RAW-IPF-011 | P0 | completeness | PASS | result = 0 | 0 | total_fte_enrollment non-null >= 95% |
| RAW-IPF-012 | P1 | completeness | PASS | result = 0 | 0 | endowment_value non-null >= 60% |
| RAW-IPF-013 | P0 | consistency | PASS | result = 0 | 0 | fiscal_year is single value across all rows |
| RAW-IPF-014 | P1 | validity | PASS | result = 0 | 0 | Spot check: at least one row instruction_expenses > $100M (large R1 anchor) |

## Gate Decision

**bronze.ipeds_finance is CLEARED for chaos-monkey hardening.** All 14 rules pass; no P0 violations.