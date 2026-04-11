# DQ Execution: silver-base-karpathy-ai-exposure

**Date:** 2026-04-09
**Agent:** @dq-engineer
**Spec:** silver-base-karpathy-ai-exposure
**Run ID:** e830d061
**Table:** base.karpathy_ai_exposure (419 rows)

## Actions Taken

1. Approved all 23 PROPOSED rules (SLV-KAI-001 through SLV-KAI-023) to APPROVED status
2. Executed all 23 rules against real Iceberg data in `base.karpathy_ai_exposure`
3. All 23 rules passed and transitioned from APPROVED to ACTIVE status
4. Generated scorecard to `governance/dq-scorecards/silver-base-karpathy-ai-exposure-scorecard.md`

## Results Summary

| Metric | Value |
|--------|-------|
| Total rules | 23 |
| Passed | 23 |
| Failed | 0 |
| Errored | 0 |
| P0 gate | PASS |
| Score | 100% |

## Priority Breakdown

| Priority | Count | Passed | Failed |
|----------|-------|--------|--------|
| P0 | 19 | 19 | 0 |
| P1 | 4 | 4 | 0 |

## Dimensions Covered

- **Uniqueness:** grain (soc_code), record_id (2 rules)
- **Validity:** SOC format, exposure score range/integer, enum, record_id format, rationale length (6 rules)
- **Completeness:** exposure_score, slug, occupation_title, category, source_load_date, ingested_at (6 rules)
- **Consistency:** null SOC implies unresolved, bls_match consistency, distribution checks (5 rules)
- **Referential integrity:** BLS match rate, cross-table join validation (2 rules)
- **Volume:** row count 380-500 range (1 rule)
- **Cross-table:** SLV-KAI-022 joins base.karpathy_ai_exposure with base.bls_ooh (1 rule)

## Regressions

No prior runs exist for this spec. This is the baseline execution.

## Notes

- Governance DB sync encountered a non-blocking schema error (ArrowInvalid: Column 'category' is declared non-nullable but contains nulls in governance.dq_rule_results table). This does not affect the DQ results themselves -- the file-based results were saved successfully.
- All rule statuses transitioned: PROPOSED -> APPROVED -> ACTIVE in a single session.

## Artifacts

- Results: `governance/dq-results/silver-base-karpathy-ai-exposure-20260409T202607Z.json`
- Scorecard: `governance/dq-scorecards/silver-base-karpathy-ai-exposure-scorecard.md`
- Rules: `governance/dq-rules/silver-base-karpathy-ai-exposure.json`
