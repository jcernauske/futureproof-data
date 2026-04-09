# Chaos Monkey After-Action Report: silver-base-bls-ooh

**Spec:** silver-base-bls-ooh
**Table:** base.bls_ooh (832 rows)
**Agent:** @chaos-monkey
**Date:** 2026-04-07
**Runner:** governance/chaos-manifests/silver_bls_ooh_chaos_runner.py
**Manifest JSON:** governance/chaos-manifests/silver-base-bls-ooh-manifest.json

## Executive Summary

5-cycle adversarial hardening completed against `base.bls_ooh` with escalating corruption rates (5%-10%). All 10 DQ dimensions were injected in every cycle. Of 36 DQ rules, 22 fired at least once across the 5 cycles (61.1% rule activation rate). 14 rules never fired, indicating they are either robust to the corruption types injected or are testing dimensions that the chaos monkey's corruption strategies do not sufficiently stress.

The detection rate scaled from 25.0% at 5% corruption to 38.9% at 10% corruption, confirming that higher corruption rates expose more rule boundaries. The P0 gate correctly failed in all 5 cycles.

## Cycle Results

| Cycle | Rate | Corruptions | Rules Fired | Rules Silent | Detection Rate |
|-------|------|-------------|-------------|--------------|----------------|
| 1 | 5% | 11 | 9/36 | 27/36 | 25.0% |
| 2 | 6% | 11 | 11/36 | 25/36 | 30.6% |
| 3 | 7% | 11 | 11/36 | 25/36 | 30.6% |
| 4 | 8% | 18 | 12/36 | 24/36 | 33.3% |
| 5 | 10% | 21 | 14/36 | 22/36 | 38.9% |

## Dimensions Injected (All 10 in Every Cycle)

| Dimension | Strategy | Target Fields |
|-----------|----------|---------------|
| Completeness | Null required fields | record_id, soc_code, occupation_title, soc_major_group, soc_major_group_name, broad_occupation_flag, catchall_flag, median_wage_capped, wage_available, source_load_date, ingested_at |
| Validity | Bad formats, out-of-range codes | soc_code (format), growth_category, education_code, work_experience_code, training_code, soc_major_group, employment fields (negative), median_annual_wage (out of range) |
| Uniqueness | Exact duplicate rows | soc_code grain duplicates |
| Consistency | Contradictory field combos | soc_major_group vs soc_code prefix, soc_major_group_name mismatch, growth_category vs employment_change_pct, wage_available vs median_annual_wage, median_wage_capped contradiction, education_level_name vs education_code, broad_occupation_flag wrong |
| Accuracy | Plausible but wrong values | Swapped employment_current/projected, wage off by 10x, wrong occupation titles |
| Reasonableness | Extreme outliers | Wages ($1, $5M, -$50K), employment (500M+), change_pct (-200%, 1000%), openings (50M+) |
| Freshness | Stale/future timestamps | source_load_date (2030, 2015), ingested_at (2035, 1970) |
| Volume | Row count inflation | Mass-duplicated rows (832 + ~83 extras) |
| Referential Integrity | Orphan SOC codes | Valid-format SOC codes from invalid major groups (12, 14, 20, 90-98 ranges) |
| Coverage | Missing SOC major groups | Removed all rows for 3 major groups per cycle |

## Rules That Fired (22/36)

Rules that detected corruption in at least one cycle:

| Rule ID | Cycles Fired | Notes |
|---------|-------------|-------|
| SLV-OOH-001 | 1,2,3,4,5 | Fired every cycle |
| SLV-OOH-002 | 4,5 | Triggered at higher rates |
| SLV-OOH-003 | 1,2,3,4,5 | Fired every cycle |
| SLV-OOH-006 | 1,3,4,5 | Fired most cycles |
| SLV-OOH-007 | 1,2,3,4,5 | Fired every cycle |
| SLV-OOH-009 | 2,4 | Intermittent |
| SLV-OOH-010 | 2,5 | Intermittent |
| SLV-OOH-011 | 1,2,3,4,5 | Fired every cycle |
| SLV-OOH-013 | 3 | Fired once |
| SLV-OOH-015 | 5 | Fired at 10% only |
| SLV-OOH-017 | 5 | Fired at 10% only |
| SLV-OOH-019 | 2,3 | Intermittent |
| SLV-OOH-021 | 2,3,5 | Intermittent |
| SLV-OOH-022 | 2,3 | Intermittent |
| SLV-OOH-023 | 1,2,3,4,5 | Fired every cycle |
| SLV-OOH-024 | 1 | Fired at 5% only |
| SLV-OOH-025 | 4 | Fired once |
| SLV-OOH-027 | 1 | Fired once |
| SLV-OOH-030 | 4 | Fired once |
| SLV-OOH-032 | 4,5 | Triggered at higher rates |
| SLV-OOH-033 | 5 | Fired at 10% only |
| SLV-OOH-036 | 1,2,3,4,5 | Fired every cycle |

## Rules That NEVER Fired (14/36)

These rules passed in all 5 cycles despite active corruption injection:

| Rule ID | Possible Explanation |
|---------|---------------------|
| SLV-OOH-004 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-005 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-008 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-012 | Threshold may be too loose for the corruption rate applied |
| SLV-OOH-014 | Threshold may be too loose for the corruption rate applied |
| SLV-OOH-016 | May check a nullable field where nulls are expected |
| SLV-OOH-018 | May check a nullable field where nulls are expected |
| SLV-OOH-020 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-026 | May use a threshold that tolerates the corruption level |
| SLV-OOH-028 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-029 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-031 | May use a threshold that tolerates the corruption level |
| SLV-OOH-034 | May check a field/condition not targeted by corruption strategies |
| SLV-OOH-035 | May check a field/condition not targeted by corruption strategies |

## Gap Analysis

### Gaps Identified

1. **14 rules never activated** -- These rules either (a) check conditions that the chaos monkey's corruption strategies do not target, (b) have thresholds that tolerate the 5-10% corruption rate, or (c) check for conditions that cannot be triggered by cell-level corruption (e.g., cross-table referential integrity checks, pattern-based checks on fields we did not corrupt).

2. **Detection rate ceiling at 38.9%** -- Even at 10% corruption, only 14/36 rules fired. This is expected for a well-designed rule set: many rules check orthogonal dimensions, and cell-level corruption at 5-10% may not violate aggregate threshold rules (e.g., a rule checking that "exactly 7 broad occupation flags" might still pass if the corrupted rows happen to not change the flag count materially).

3. **Consistency dimension partially covered** -- The growth_category vs employment_change_pct mismatch, wage_available contradiction, and broad_occupation_flag corruption were injected, but it is unclear which specific rules caught these vs the other dimension corruptions. The information barrier prevents mapping rules to dimensions.

### Recommendations for @dq-rule-writer

1. **Review the 14 never-fired rules** -- Verify these rules are testing real data conditions. If they only check invariants that hold even under corruption (e.g., "column exists" or "data type is correct"), they may need tighter thresholds or should be reclassified as structural checks rather than DQ rules.

2. **Consider adding rules for:**
   - SOC major group name referential integrity (does name match the lookup for the 2-digit code?)
   - Growth category consistency (does the category match the employment_change_pct bucket?)
   - Education level name consistency (does name match education_code lookup?)
   - wage_available flag consistency (does it match median_annual_wage IS NOT NULL?)
   - These are Silver-specific derived field consistency checks that are prime targets for corruption.

3. **Tighten thresholds on aggregate rules** -- If any of the 14 unfired rules use percentage-based thresholds (e.g., ">= 95%"), corruption at 5-10% may not breach them. Consider whether these thresholds should be tighter for a 832-row table.

## Safety Verification

- All corruptions applied to shadow_base.bls_ooh only (never real base.bls_ooh)
- Shadow table cleaned up after each cycle
- CHAOS_MONKEY_ENABLED=true and GRIST_ENV=dev verified at startup
- Complete manifest JSON recorded at governance/chaos-manifests/silver-base-bls-ooh-manifest.json

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Chaos runner script | governance/chaos-manifests/silver_bls_ooh_chaos_runner.py |
| JSON manifest (all 5 cycles) | governance/chaos-manifests/silver-base-bls-ooh-manifest.json |
| This report | governance/chaos-manifests/silver-base-bls-ooh-chaos.md |
| DQ results (per cycle) | governance/dq-results/silver-base-bls-ooh-*.json (5 files) |
