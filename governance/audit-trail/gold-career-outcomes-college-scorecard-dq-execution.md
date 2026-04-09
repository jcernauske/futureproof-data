# Audit Trail: DQ Execution — gold-career-outcomes-college-scorecard

**Agent:** @dq-engineer
**Date:** 2026-04-06
**Spec:** gold-career-outcomes-college-scorecard
**Run ID:** 71fa5e3a

## Actions Taken

1. Read DQ rules from `governance/dq-rules/gold-career-outcomes-college-scorecard.json` (42 rules)
2. Advanced all 42 rules from PROPOSED to APPROVED status
3. Executed all 42 rules against persistent Iceberg warehouse (`data/`) via `dq_runner run`
4. Generated scorecard from real execution results via `dq_runner scorecard`

## Execution Summary

| Metric | Value |
|--------|-------|
| Total Rules | 42 |
| Passed | 42 |
| Failed | 0 |
| Errored | 0 |
| P0 Gate | PASS |

### Breakdown by Priority

| Priority | Count | Passed | Failed |
|----------|-------|--------|--------|
| P0 | 24 | 24 | 0 |
| P1 | 14 | 14 | 0 |
| P2 | 4 | 4 | 0 |

## P0 Rules (All Passing)

- GLD-CO-001: Grain uniqueness (unitid x cipcode x credential_level) -- 0 duplicates
- GLD-CO-002: Record ID uniqueness -- 0 duplicates or nulls
- GLD-CO-003: Row count within 59,455-80,439 range -- PASS
- GLD-CO-004/005/006: Percentile band ordering (p25 <= p75) -- 0 violations across all 3 band pairs
- GLD-CO-007/008: confidence_tier NOT NULL and valid value set -- 0 violations
- GLD-CO-009/010: has_earnings / has_debt accuracy -- 100% match
- GLD-CO-011: outcome_completeness value set -- exactly {0.0, 0.33, 0.67, 1.0}
- GLD-CO-012-017: Null propagation for all derived financial metrics -- 0 violations
- GLD-CO-018: debt_to_earnings_tier value set -- all within {Low, Moderate, High, Very High}
- GLD-CO-029/030: Confidence tier derivation logic -- 0 violations
- GLD-CO-031: outcome_completeness consistency -- 0 violations
- GLD-CO-032/033: NOT NULL field completeness -- 0 violations
- GLD-CO-036: MVP credential level filter (=3) -- 0 violations
- GLD-CO-038: DTE tier boundary accuracy -- 0 violations

## Regression Check

This is the first DQ execution for this spec. No prior results to compare against.

## Notable Observations

- GLD-CO-039 (P2): institution_control is 100% NULL as expected (known Bronze blocking issue). Tracked, not blocking.
- Governance DB sync failed with a non-blocking PyArrow error (nullable column schema mismatch in governance tracking table). Results were saved to the JSON results file successfully.

## Artifacts Produced

- Results: `governance/dq-results/gold-career-outcomes-college-scorecard-20260407T025612Z.json`
- Scorecard: `governance/dq-scorecards/gold-career-outcomes-college-scorecard-scorecard.md`
