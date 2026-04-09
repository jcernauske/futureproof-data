# Chaos Monkey After-Action Report: silver-base-onet

**Spec:** silver-base-onet
**Tables:** base.onet_occupations (798), base.onet_activity_profiles (31,734), base.onet_context_profiles (44,118), base.onet_career_transitions (15,944)
**Agent:** @chaos-monkey
**Date:** 2026-04-08
**Runner:** governance/chaos-manifests/silver_onet_chaos_runner.py
**Manifest JSON:** governance/chaos-manifests/silver-base-onet-manifest.json

## Executive Summary

3-cycle adversarial hardening completed (early exit at cycle 3 due to stability) against 4 Silver O*NET tables with escalating corruption rates (5%-7%). All 10 DQ dimensions were injected in every cycle across all 4 tables. Of 37 DQ rules, 32 fired in every cycle (86.5% rule activation rate). 5 rules never fired. The detection rate was stable at 86.5% across all 3 cycles, and the same set of 32 rules fired every time, triggering the early exit condition (no new gaps for 2 consecutive cycles).

The P0 gate correctly failed in all 3 cycles. This is a strong result -- 86.5% rule activation means the DQ rule set has broad coverage across the corruption types injected.

## Cycle Results

| Cycle | Rate | Corruptions | Rules Fired | Rules Silent | Detection Rate | Exit |
|-------|------|-------------|-------------|--------------|----------------|------|
| 1 | 5% | 2,860 | 32/37 | 5/37 | 86.5% | -- |
| 2 | 6% | 3,430 | 32/37 | 5/37 | 86.5% | -- |
| 3 | 7% | 4,003 | 32/37 | 5/37 | 86.5% | Early exit (stable) |

## Dimensions Injected (All 10 in Every Cycle)

| Dimension | Strategy | Target Tables | Target Fields |
|-----------|----------|---------------|---------------|
| Completeness | Null required fields | All 4 | bls_soc_code, record_id, primary_title, description, data_completeness_tier, element_id, scale_id, context_value, relatedness_tier, best_index |
| Validity | Bad formats, out-of-range values | All 4 | bls_soc_code (drop dash, wrong length, alpha, O*NET format), importance > 5, context_value > 5 (CX) / > 3 (CT), best_index > 20, invalid scale_id (IM/LV/CXP/CTP), invalid relatedness_tier, invalid data_completeness_tier, invalid relationship_type |
| Uniqueness | Exact duplicate grain rows | All 4 | Grain duplicates per table |
| Consistency | Contradictory field combos | All 4 | data_completeness_tier vs has_* flags, onet_detail_count vs onet_detail_codes, multi_detail_flag wrong, is_high_importance vs importance threshold, is_burnout_element vs element_id, self-references in transitions, relatedness_tier vs best_index, is_primary vs tier |
| Accuracy | Plausible but wrong values | All 4 | Plausible wrong SOC codes, shifted importance values, shifted context_value, shifted best_index |
| Reasonableness | Extreme outliers | All 4 | onet_detail_count (0/-1/500/999), onet_details_averaged (0/-1/100/500), context_value (-10/50/100/999), best_index (0/-10/50/999) |
| Freshness | Stale/future timestamps | All 4 | source_load_date (2030, 2018), ingested_at (2035) |
| Volume | Row count inflation | All 4 | Mass-duplicated rows across all tables |
| Referential Integrity | Orphan SOC codes | All 4 | bls_soc_code from invalid major groups (60, 90, 92, 98), related_bls_soc_code orphans in career_transitions |
| Coverage | Missing SOC groups/codes | All 4 | Removed all rows for 3 SOC major groups (occupations) + 5 specific SOC codes per child table |

## Rules That Fired (32/37)

All 32 rules fired consistently in every cycle:

| Rule ID | Cycle 1 | Cycle 2 | Cycle 3 | Notes |
|---------|---------|---------|---------|-------|
| SLV-ONET-001 | FAIL (3) | FAIL (5) | FAIL (6) | Scaled with rate |
| SLV-ONET-002 | FAIL (71) | FAIL (70) | FAIL (72) | Stable |
| SLV-ONET-003 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-004 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-005 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-007 | FAIL (3) | FAIL (5) | FAIL (4) | Scaled with rate |
| SLV-ONET-010 | FAIL (2120) | FAIL (2131) | FAIL (2154) | Scaled with rate |
| SLV-ONET-011 | FAIL (125) | FAIL (128) | FAIL (182) | Scaled with rate |
| SLV-ONET-013 | FAIL (373) | FAIL (424) | FAIL (453) | Scaled with rate |
| SLV-ONET-015 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-016 | FAIL (203) | FAIL (239) | FAIL (254) | Scaled with rate |
| SLV-ONET-017 | FAIL (168) | FAIL (200) | FAIL (226) | Scaled with rate |
| SLV-ONET-020 | FAIL (2951) | FAIL (2974) | FAIL (2993) | High count |
| SLV-ONET-021 | FAIL (252) | FAIL (318) | FAIL (339) | Scaled with rate |
| SLV-ONET-022 | FAIL (104) | FAIL (123) | FAIL (166) | Scaled with rate |
| SLV-ONET-024 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-025 | FAIL (111) | FAIL (111) | FAIL (138) | Stable then scaled |
| SLV-ONET-026 | FAIL (246) | FAIL (288) | FAIL (309) | Scaled with rate |
| SLV-ONET-027 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-028 | FAIL (230) | FAIL (282) | FAIL (323) | Scaled with rate |
| SLV-ONET-030 | FAIL (1051) | FAIL (1070) | FAIL (1080) | High count |
| SLV-ONET-031 | FAIL (21) | FAIL (32) | FAIL (33) | Scaled with rate |
| SLV-ONET-032 | FAIL (96) | FAIL (110) | FAIL (142) | Scaled with rate |
| SLV-ONET-033 | FAIL (22) | FAIL (22) | FAIL (28) | Scaled with rate |
| SLV-ONET-034 | FAIL (44) | FAIL (50) | FAIL (58) | Scaled with rate |
| SLV-ONET-035 | FAIL (125) | FAIL (150) | FAIL (144) | Scaled with rate |
| SLV-ONET-036 | FAIL (129) | FAIL (139) | FAIL (144) | Scaled with rate |
| SLV-ONET-037 | FAIL (1) | FAIL (1) | FAIL (1) | Binary |
| SLV-ONET-038 | FAIL (19) | FAIL (17) | FAIL (15) | Decreasing (random) |
| SLV-ONET-039 | FAIL (83) | FAIL (105) | FAIL (119) | Scaled with rate |
| SLV-ONET-040 | FAIL (16) | FAIL (27) | FAIL (34) | Scaled with rate |
| SLV-ONET-041 | FAIL (147) | FAIL (159) | FAIL (198) | Scaled with rate |

## Rules That NEVER Fired (5/37)

These 5 rules passed in all 3 cycles despite active corruption injection:

| Rule ID | All Cycle Values | Possible Explanation |
|---------|-----------------|---------------------|
| SLV-ONET-006 | 0, 0, 0 | May check a condition that the corruption strategies do not target (e.g., a specific structural invariant) |
| SLV-ONET-012 | 0, 0, 0 | May check a field/condition not targeted, or uses a threshold that tolerates 5-7% corruption |
| SLV-ONET-014 | 0, 0, 0 | May check a nullable field where nulls are expected, or an aggregate that is robust to cell-level corruption |
| SLV-ONET-023 | 0, 0, 0 | May check a condition that holds even under corruption (e.g., data type enforcement, schema-level check) |
| SLV-ONET-029 | 0, 0, 0 | May check an aggregate or cross-table condition not stressed by the injection patterns used |

## Gap Analysis

### Strengths

1. **86.5% rule activation rate** -- 32 of 37 rules fired, indicating the DQ rule set has broad coverage across the 10 corruption dimensions.

2. **Consistent activation across rates** -- The same 32 rules fired at 5%, 6%, and 7% corruption, meaning even the lowest rate was sufficient to trigger them. This shows tight thresholds.

3. **Scaling behavior** -- Most rules showed increasing failure values as the corruption rate escalated, confirming the rules are proportional detectors rather than binary pass/fail on irrelevant conditions.

4. **Binary rules remain stable** -- Rules 003, 004, 005, 015, 024, 027, 037 consistently returned value=1 across all cycles, suggesting they detect structural violations (existence checks, format validation) that trigger at any corruption level.

5. **Early stability** -- The system reached equilibrium in cycle 1, with no new rules firing in cycles 2 or 3. This is a sign of a mature rule set.

### Gaps Identified

1. **5 rules never activated** -- SLV-ONET-006, 012, 014, 023, 029 returned value=0 in all cycles. These rules either (a) check conditions not targeted by the corruption strategies, (b) have thresholds that tolerate the corruption levels used, or (c) check structural invariants that hold regardless of cell-level corruption.

2. **No escalation beyond cycle 1** -- No additional rules were triggered at higher rates, which could mean the 5 unfired rules have very different activation conditions (cross-dataset checks, pattern-based validations, or checks on fields/tables not corrupted).

### Recommendations for @dq-rule-writer

1. **Review the 5 never-fired rules** -- Verify SLV-ONET-006, 012, 014, 023, 029 are testing real data conditions. If they check invariants that hold even under corruption, consider whether they need tighter thresholds or should be reclassified as structural/schema checks.

2. **Consider adding rules for:**
   - **CXP/CTP scale filtering** -- We injected CXP/CTP scale values that should not exist in Silver. If no rule checks for only CX/CT scales, one should be added.
   - **Self-reference detection** -- We injected bls_soc_code == related_bls_soc_code in career_transitions. If no rule checks for this, it is a gap.
   - **Burnout element consistency** -- We flipped is_burnout_element flags. If no rule validates these against the known burnout element ID list, one should be added.
   - **Detail count vs detail codes list consistency** -- We set onet_detail_count to values mismatching the JSON array length in onet_detail_codes.
   - **Structurally empty occupations** -- We set all has_* flags to False. If no rule checks that at least one flag is True, Silver could contain empty occupations.

## Safety Verification

- All corruptions applied to shadow_base.* tables only (never real base.* tables)
- Shadow tables cleaned up after each cycle and at completion
- CHAOS_MONKEY_ENABLED=true and GRIST_ENV=dev verified at startup
- Complete manifest JSON recorded at governance/chaos-manifests/silver-base-onet-manifest.json

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Chaos runner script | governance/chaos-manifests/silver_onet_chaos_runner.py |
| JSON manifest (all 3 cycles) | governance/chaos-manifests/silver-base-onet-manifest.json |
| This report | governance/chaos-manifests/silver-base-onet-chaos.md |
