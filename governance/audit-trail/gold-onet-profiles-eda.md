# Audit Trail: Gold O*NET Profiles EDA

**Spec:** gold-onet-profiles
**Agent:** @data-analyst
**Timestamp:** 2026-04-08
**Action:** Pre-implementation EDA on Silver source tables

## Datasets Analyzed

- base.onet_occupations (798 rows)
- base.onet_activity_profiles (31,734 rows)
- base.onet_context_profiles (44,118 rows)
- base.onet_career_transitions (15,944 rows)

## Key Findings

1. All row counts match spec expectations
2. **CRITICAL:** Spec's human-intensive activity element IDs are wrong for 13 of 14 activities. Corrected mapping provided in EDA report.
3. **CRITICAL:** HMN score formula produces compressed range (3.46-4.94) on 1-10 scale. Requires formula redesign decision.
4. Burnout score distribution is healthy (3.48-8.32, std=0.778)
5. 24 partial-data occupations confirmed -- will have null scores
6. Suppression rates negligible (1 activity row, 18 context rows)
7. Career transitions: 0 self-references, 0 duplicates, full referential integrity
8. Burnout element names in spec don't match data (IDs correct, use is_burnout_element flag)

## Threshold Recommendations

- HMN/Burnout null count: exactly 24
- Confidence tiers: 773 high, 1 medium, 24 low
- Career transitions: 15,944 rows, 0 self-refs, 0 dupes

## Artifacts Produced

- EDA report: `governance/eda/gold-onet-profiles-eda.md`
- Audit trail: `governance/audit-trail/gold-onet-profiles-eda.md`

## Decisions Requiring Human Approval

1. HMN score formula redesign (compressed range problem)
2. Corrected element ID mapping for human-intensive activities
