# Audit Trail: Silver O*NET EDA

**Spec:** silver-base-onet
**Agent:** @data-analyst
**Date:** 2026-04-08
**Action:** Bronze data profiling for Silver transformation thresholds

## What Was Analyzed

Profiled 4 Bronze O*NET tables (raw.onet_occupations, raw.onet_work_activities, raw.onet_work_context, raw.onet_related_occupations) to validate spec assumptions and calibrate Silver DQ thresholds.

## Key Findings

1. **Silver onet_occupations should be 798 rows, not ~867.** At BLS SOC level, only 69 BLS SOCs are truly empty (not 93 as in spec). 24 of the 93 zero-data O*NET codes share a BLS prefix with data-having detailed codes.
2. **4 of 9 burnout element IDs are incorrect.** 4.C.3.d.5 and 4.C.3.d.7 do not exist. 4.C.3.b.2 maps to "Degree of Automation" not "Frequency of Decision Making". 4.C.3.d.4 maps to "Work Schedules" not "Importance of Being Exact or Accurate". "Responsibility for Outcomes and Results" is not an O*NET element name.
3. **343 BLS-level self-references** will emerge in career transitions during aggregation.
4. **15,944 career transition pairs** after full BLS-level processing.
5. **Only 1 suppress=Y on IM scale** (effectively zero). 18 suppress=Y on CX scale (0.04%).

## Threshold Recommendations

- onet_occupations: 798 rows, 76 multi_detail, 24 partial, 774 full
- activity_profiles: 31,734 rows, IM range [1.0, 5.0], suppress < 1%
- context_profiles: 44,118 rows, CX range [1.0, 5.0], CT range [1.0, 3.0]
- career_transitions: 15,944 rows, 0 self-references, best_index [1, 20]

## Artifacts Produced

- `governance/eda/silver-onet-eda.md` -- Full EDA report

## Decisions

- Corrected burnout element IDs documented in EDA for @primary-agent implementation
- Recommended 4.C.3.a.2.a "Impact of Decisions on Co-workers or Company Results" as replacement for nonexistent "Responsibility for Outcomes and Results"
