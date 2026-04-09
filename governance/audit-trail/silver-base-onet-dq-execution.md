# DQ Execution: silver-base-onet

- **Agent:** @dq-engineer
- **Timestamp:** 2026-04-09T00:49:39Z
- **Run ID:** 4060c827
- **Spec:** silver-base-onet

## Execution Summary

- **Rules executed:** 37
- **Rules passed:** 37
- **Rules failed:** 0
- **Rules errored:** 0
- **P0 gate:** PASS

## Rule Breakdown by Priority

| Priority | Total | Passed | Failed |
|----------|-------|--------|--------|
| P0       | 24    | 24     | 0      |
| P1       | 9     | 9      | 0      |
| P2       | 2     | 2      | 0      |
| P3       | 2     | 2      | 0      |

## Tables Validated

| Table | Rules | All Pass |
|-------|-------|----------|
| base.onet_occupations | 7 | Yes |
| base.onet_activity_profiles | 8 | Yes |
| base.onet_context_profiles | 10 | Yes |
| base.onet_career_transitions | 12 | Yes |

## Key Validations Confirmed

- **Grain integrity:** All 4 tables have unique keys with zero duplicates
- **Volume:** onet_occupations=798, activity_profiles=31,734, context_profiles=44,118, career_transitions=15,944
- **Referential integrity:** All FK relationships validated (activity->occupations, context->occupations, transitions->occupations for both source and target)
- **Value ranges:** Importance 1.0-5.0, CX context 1.0-5.0, CT context 1.0-3.0, best_index 1-20
- **Completeness:** Zero NULLs across all required fields in all 4 tables
- **Business rules:** No self-references in transitions, correct tier/flag derivations, 9 burnout elements confirmed, CXP/CTP scale rows excluded

## Regressions

No previous runs exist for silver-base-onet. This is the baseline run.

## Notes

- Non-blocking error during governance DB sync (null `category` column in PyArrow schema). Does not affect rule execution or results.
- All rules transitioned from proposed -> approved -> active during this run.

## Artifacts

- Results: `governance/dq-results/silver-base-onet-20260409T004939Z.json`
- Scorecard: `governance/dq-scorecards/silver-base-onet-scorecard.md`
