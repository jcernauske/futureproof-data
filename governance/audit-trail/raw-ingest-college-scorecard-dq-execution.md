# DQ Execution Audit Trail: raw-ingest-college-scorecard

**Agent:** @dq-engineer
**Timestamp:** 2026-04-06T02:58:55Z
**Run ID:** f90a303e
**Spec:** raw-ingest-college-scorecard
**Zone:** Bronze (raw.college_scorecard)

## Execution Summary

| Metric | Value |
|--------|-------|
| Rules executed | 18 |
| Rules passed | 18 |
| Rules failed | 0 |
| Rules errored | 0 |
| P0 gate | PASS |
| Total execution time | ~700ms |

## P0 Rules (all passed)

| Rule ID | Name | Result |
|---------|------|--------|
| RAW-CS-001 | Grain uniqueness: unitid x cipcode x credlev | PASS (0 violations) |
| RAW-CS-002 | unitid not null | PASS (0 violations) |
| RAW-CS-003 | cipcode not null | PASS (0 violations) |
| RAW-CS-004 | credlev not null | PASS (0 violations) |
| RAW-CS-005 | instnm not null | PASS (0 violations) |
| RAW-CS-010 | credlev equals 3 for all rows | PASS (0 violations) |
| RAW-CS-011 | cipcode format: 4-digit numeric string | PASS (0 violations) |
| RAW-CS-016 | Row count within expected range (50k-100k) | PASS (69,947 rows) |

## P1 Rules (all passed)

| Rule ID | Name | Result | Observed Value |
|---------|------|--------|----------------|
| RAW-CS-006 | earn_mdn_hi_1yr null rate | PASS | 44,751 nulls (threshold: <=48,963) |
| RAW-CS-007 | earn_mdn_hi_2yr null rate | PASS | 42,266 nulls (threshold: <=45,466) |
| RAW-CS-008 | debt_all_stgp_eval_mdn null rate | PASS | 44,138 nulls (threshold: <=47,564) |
| RAW-CS-009 | ipedscount1 null rate | PASS | 6,098 nulls (threshold: <=8,394) |
| RAW-CS-012 | earn_mdn_hi_1yr range check | PASS | 0 out-of-range values |
| RAW-CS-013 | earn_mdn_hi_2yr range check | PASS | 0 out-of-range values |
| RAW-CS-014 | debt_all_stgp_eval_mdn range check | PASS | 0 out-of-range values |
| RAW-CS-015 | unitid 6-digit range check | PASS | 0 out-of-range values |
| RAW-CS-017 | load_date freshness (30 days) | PASS | 0 stale rows |
| RAW-CS-018 | Earnings 2yr vs 1yr consistency | PASS | 9,797 rows (threshold: <=12,000) |

## Regression Check

Compared against previous run 7d6ceef1 (2026-04-06T02:57:46Z):
- Previous: 18/18 passed
- Current: 18/18 passed
- No regressions detected. All raw_value observations are consistent between runs.

## Data Source Verification

Queries executed against persistent Iceberg warehouse at `data/` directory (contains raw/, bronze/, catalog/, governance/ subdirectories). Not ephemeral or test data.

## Known Issue

The governance DB sync step failed with `ArrowInvalid: Column 'category' is declared non-nullable but contains nulls`. This is a schema mismatch in the governance Iceberg table (the `category` field in rule results is null for all 18 rules, but the governance DB schema declares it non-nullable). This does not affect the DQ results or scorecard -- only the persistence to the governance Iceberg table. Should be addressed as a framework bug.
