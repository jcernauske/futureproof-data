# Audit Trail: DQ Rule Writing for gold-onet-profiles

**Date:** 2026-04-08
**Agent:** @dq-rule-writer
**Spec:** gold-onet-profiles
**Zone:** Gold (Consumable)
**Tables:** consumable.onet_work_profiles, consumable.career_transitions
**Evidence:** governance/eda/gold-onet-profiles-eda.md
**Output:** governance/dq-rules/gold-onet-profiles.json

---

## Summary

Wrote 44 DQ rules (GLD-ONP-001 through GLD-ONP-044) across two consumable tables. 43 rules are in PROPOSED status; 1 is DEFERRED (golden dataset verification). All thresholds are evidence-based, citing the EDA report and logical model.

---

## Mandatory Pattern Evaluation (consumable-patterns.json)

### CONS-GRAIN-UNIQUE (P0, mandatory) -- RULE WRITTEN
- **Work profiles:** GLD-ONP-001 (bls_soc_code uniqueness)
- **Career transitions:** GLD-ONP-029 (bls_soc_code x related_bls_soc_code uniqueness)
- Evidence: EDA confirms 0 duplicates on both grains.

### CONS-IMPOSSIBLE-VALUE (P0, mandatory) -- RULES WRITTEN
- GLD-ONP-005: hmn_score range 1.0-10.0
- GLD-ONP-007: burnout_score range 1.0-10.0
- GLD-ONP-032: No self-references in career transitions
- GLD-ONP-016/017/018: Burnout element value ranges
- GLD-ONP-021/022: Suppression percentage ranges 0-100

### CONS-CROSS-TABLE (P1) -- RULE WRITTEN
- GLD-ONP-039: career_transitions FK to onet_work_profiles
- This spec produces two related tables sharing bls_soc_code as a join key.

### CONS-GOLDEN-DATASET (P0, mandatory) -- DEFERRED
- GLD-ONP-044: Golden dataset not yet created.
- File governance/golden-datasets/gold-onet-profiles-golden.json does not exist.
- Spec identifies candidates: Software Developers (15-1252), Registered Nurses (29-1141), low-HMN occupation.
- **Requires human override to skip. Deferred to @primary-agent implementation phase.**

### CONS-COLLISION-RESOLVED (P0, mandatory) -- DOES NOT APPLY
- This is a single-source spec (O*NET only). No concept normalization maps multiple source codes to canonical concepts. No collision resolution is needed.

### CONS-COVERAGE-FLOOR (P1) -- DOES NOT APPLY
- No concept normalization in use. Coverage is addressed by entity coverage rules (GLD-ONP-042, GLD-ONP-043).

---

## Adversarial Pattern Evaluation (adversarial-patterns.json)

### ADV-GRAIN-UNIQUE -- RULES WRITTEN
- GLD-ONP-001 (work profiles), GLD-ONP-029 (career transitions)

### ADV-FK-VALID -- RULES WRITTEN
- GLD-ONP-039: career_transitions.bls_soc_code -> onet_work_profiles.bls_soc_code
- GLD-ONP-033: Title non-null check (validates join to base.onet_occupations succeeded)

### ADV-TEMPORAL-ORDER -- DOES NOT APPLY
- No start/end date columns. Single-snapshot data.

### ADV-ENTITY-COVERAGE -- RULES WRITTEN
- GLD-ONP-042: All 798 occupations in work profiles
- GLD-ONP-043: All 798 source SOCs in career transitions

### ADV-PERIOD-COVERAGE -- DOES NOT APPLY
- No temporal grain. Single-snapshot data.

### ADV-VALUE-RANGE -- RULES WRITTEN
- GLD-ONP-005: hmn_score 1.0-10.0
- GLD-ONP-007: burnout_score 1.0-10.0
- GLD-ONP-016: time_pressure 1-5
- GLD-ONP-017: work_hours 1-3
- GLD-ONP-018: consequence_of_error 1-5
- GLD-ONP-037: best_index 1-20

### ADV-DISTRIBUTION-VARIANCE -- RULES WRITTEN
- GLD-ONP-010: hmn_score std dev > 1.0 (post-rescale)
- GLD-ONP-011: burnout_score std dev > 0.5

### ADV-CROSS-COLUMN -- RULES WRITTEN
- GLD-ONP-009: hmn_score and burnout_score null in same rows
- GLD-ONP-012: hmn_score_rounded = ROUND(hmn_score)
- GLD-ONP-013: burnout_score_rounded = ROUND(burnout_score)
- GLD-ONP-027: activity_profile_available consistent with data_completeness_tier
- GLD-ONP-038: is_primary consistent with relatedness_tier

---

## Normalization Pattern Evaluation (normalization-patterns.json)

All patterns (NORM-CONFIDENCE-RANGE, NORM-COVERAGE-FLOOR, NORM-TIER1-APPROVED) DO NOT APPLY. This is a single-source spec with no concept normalization.

## Collision Pattern Evaluation (collision-patterns.json)

All patterns (COLLISION-UNIQUE-PER-GRAIN, COLLISION-RULES-APPLIED) DO NOT APPLY. No collision resolution in this spec.

---

## Adversarial Protocol Questions

### Structural Integrity
1. **Declared grain?** Work profiles: bls_soc_code. Career transitions: bls_soc_code x related_bls_soc_code. Rules: GLD-ONP-001, GLD-ONP-029.
2. **Foreign keys?** career_transitions -> onet_work_profiles (bls_soc_code). Rule: GLD-ONP-039. Also implicit FK to base.onet_occupations validated by title non-null (GLD-ONP-033).
3. **Derived columns?** hmn_score_rounded from hmn_score (GLD-ONP-012), burnout_score_rounded from burnout_score (GLD-ONP-013), is_primary from relatedness_tier (GLD-ONP-038), activity_profile_available from data_completeness_tier (GLD-ONP-027).

### Semantic Validity
4. **Impossible values?** Negative scores, scores outside 1-10, self-referencing transitions, suppression percentages outside 0-100. All covered by rules.
5. **Cross-column relationships?** hmn/burnout null correlation (GLD-ONP-009), rounded score consistency (GLD-ONP-012/013), tier/boolean consistency (GLD-ONP-027/038).
6. **Temporal ordering?** Not applicable -- single-snapshot data.

### Distribution Expectations
7. **Expected row count range per entity?** Work profiles: 1 row per SOC (exactly 798). Career transitions: 14-75 per source SOC (EDA). Exact count rule: GLD-ONP-031.
8. **Value distribution?** HMN std > 1.0 (GLD-ONP-010), burnout std > 0.5 (GLD-ONP-011).
9. **Temporal coverage?** Not applicable -- single snapshot.

### Coverage Guarantees
10. **All expected entities present?** GLD-ONP-042 (798 in work profiles), GLD-ONP-043 (798 sources in transitions).
11. **All time periods covered?** Not applicable.
12. **All metrics populated?** Completeness rules (GLD-ONP-006/008 for score nulls, GLD-ONP-023/040 for required fields).

---

## Design Notes

### HMN Score Rescaling
The original EDA found hmn_score compressed to 3.46-4.94 (1.5 points on a 10-point scale). A design change was approved to use min/max rescaling: `hmn_score = 1.0 + 9.0 * (human_ratio - observed_min) / (observed_max - observed_min)`, clamped to [1.0, 10.0]. DQ rules validate the 1-10 range (GLD-ONP-005) and meaningful spread (GLD-ONP-010, std > 1.0).

### 24 Partial-Data Occupations
24 occupations in base.onet_occupations have data_completeness_tier='partial' and lack both activity and context profiles. These produce null hmn_score and burnout_score. DQ rules enforce exact null counts (GLD-ONP-006/008) and null correlation (GLD-ONP-009).

### Rules Not Written (and why)
- **Activity importance mean range rule:** Considered but not written. activity_importance_mean is a simple average of 41 values each in 1-5 range, so it's bounded by 1-5 by construction. The range check adds no value beyond what the source data already guarantees.
- **Transition count per SOC rule:** Considered but not written as a hard constraint. EDA shows 14-75 transitions per SOC with most at 20. The variation is legitimate (some occupations have fewer similar occupations). The exact row count rule (GLD-ONP-031) is sufficient.
- **multi_detail_flag distribution rule:** Considered but not written. The 76 true / 722 false split is informational and carried directly from Silver. A change in this distribution would indicate a Silver change, not a Gold bug.

---

## Execution Results

Execution DEFERRED. Tables do not yet exist (spec status: DRAFT, pending @primary-agent implementation). Rules will be executed by @dq-engineer after implementation.
