# DQ Execution: raw-ingest-onet

**Date:** 2026-04-08
**Agent:** @dq-engineer
**Spec:** raw-ingest-onet
**Run ID:** 88582a2d

## Summary

Executed 40 DQ rules across 5 O*NET raw tables against the persistent Iceberg warehouse at `data/bronze/iceberg_warehouse`, catalog at `data/catalog/catalog.db`.

## Tables Populated

Prior to DQ execution, the 5 O*NET tables were ingested into the `raw` namespace:

| Table | Rows | Source File |
|-------|------|-------------|
| raw.onet_occupations | 1,016 | Occupation Data.txt |
| raw.onet_task_statements | 18,796 | Task Statements.txt |
| raw.onet_work_activities | 73,308 | Work Activities.txt |
| raw.onet_work_context | 297,676 | Work Context.txt |
| raw.onet_related_occupations | 18,460 | Related Occupations.txt |

Data source: O*NET 30.2 cached files at `data/raw/onet_cache/`.

## Execution Results

- **Rules Total:** 40
- **Rules Passed:** 40
- **Rules Failed:** 0
- **Rules Errored:** 0
- **P0 Gate:** PASS

### Priority Breakdown

| Priority | Total | Passed | Failed |
|----------|-------|--------|--------|
| P0 | 28 | 28 | 0 |
| P1 | 12 | 12 | 0 |

### Dimensions Covered

- Validity: 15 rules (SOC format, scale ranges, code sets, index ranges, self-references)
- Completeness: 5 rules (not-null on grain/required fields, category population)
- Uniqueness: 4 rules (grain uniqueness per table)
- Referential Integrity: 5 rules (cross-table SOC code joins)
- Consistency: 2 rules (is_primary vs index, 20 rows per occupation)
- Volume: 5 rules (row count ranges per table)
- Freshness: 1 rule (load_date within 30 days)

## Rule Lifecycle

All 40 rules advanced from APPROVED to ACTIVE status on first successful execution against real Iceberg data.

## Regressions

No previous DQ runs exist for this spec. This is the initial execution baseline.

## Artifacts

- DQ results: `governance/dq-results/raw-ingest-onet-20260408T032233Z.json`
- DQ scorecard: `governance/dq-scorecards/raw-ingest-onet-scorecard.md`
- DQ rules: `governance/dq-rules/raw-ingest-onet.json` (40 rules, all ACTIVE)

## Notes

- Career Changers Matrix and Career Starters Matrix files do not exist in O*NET 30.2; no tables or rules for these per domain-context.md recommendation.
- Governance DB sync had a non-critical error (Arrow nullable column issue in governance.dq_rule_results table schema). DQ results were successfully written to the file-based results store. This is a pre-existing issue in the governance DB schema, not related to the O*NET DQ execution.
