# Audit Trail: Silver EDA for base.karpathy_ai_exposure

**Date:** 2026-04-09
**Agent:** @data-analyst
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 2: Silver)
**Action:** Silver-focused EDA on bronze.karpathy_ai_exposure (342 rows)

## What Was Analyzed

Performed Silver-zone EDA on bronze.karpathy_ai_exposure to provide threshold evidence for Silver DQ rules. The Silver table (base.karpathy_ai_exposure) does not exist yet -- analysis was performed on Bronze data with predictions about Silver transformation outcomes.

## Key Findings

1. **Predicted Silver row count: ~412** (342 Bronze + 110 from broad code expansion - 40 broad codes replaced + 4 broad-to-broad matches kept). Within physical model's 400-700 range.

2. **50 broad SOC codes identified (not 46 as previously stated).** 40 expand to 110 detailed BLS codes. 4 match BLS exactly as broad-to-broad. 6 have no BLS match at all (these are major-group-level codes like XX-X000).

3. **Zero duplicate SOC codes after expansion.** No overlaps between direct codes and expanded codes. Dedup logic is defensive only.

4. **Title matching yields ~28 resolvable out of 52 null-SOC occupations.** Zero exact matches. All rely on substring/fuzzy matching. 24 occupations are fully unresolvable.

5. **BLS match rate predicted at ~98% of non-null SOC rows.** Well above the 90% threshold.

6. **soc_resolved_method distribution differs from spec.** Spec predicted 70/15/10/5%. Actual: ~59% direct, ~27% broad_expansion, ~7% title_match, ~7% unresolved.

## Threshold Recommendations

- Row count: 380-500 (tighter than physical model's 400-700)
- bls_match >= 90% (non-null SOC): confirmed with evidence (~98% predicted)
- Rationale >= 250 chars: all pass (minimum observed: 297)
- Grain uniqueness: 0 duplicates predicted
- Exposure score 0-10: all in range 1-10 (0 valid but absent)

## Artifacts Produced

- `governance/eda/silver-base-karpathy-ai-exposure-eda.md`

## Decisions

- Recommended transformer check BLS for exact broad code match BEFORE attempting prefix expansion (4 broad-to-broad cases)
- Recommended conservative title matching with human review flags (no exact matches exist)
- Recommended tightening row count DQ range from 400-700 to 380-500
