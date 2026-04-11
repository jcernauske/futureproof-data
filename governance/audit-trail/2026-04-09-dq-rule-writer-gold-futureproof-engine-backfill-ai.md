# DQ Rule Writer Audit Trail: gold-futureproof-engine-backfill-ai

**Date:** 2026-04-09
**Agent:** @dq-rule-writer
**Spec:** gold-futureproof-engine-backfill-ai
**Evidence:** governance/eda/gold-futureproof-engine-backfill-ai-eda.md
**Physical Model:** governance/models/gold-futureproof-engine-backfill-ai-physical.md
**Domain Context:** governance/domain-context.md
**Output:** governance/dq-rules/gold-futureproof-engine-backfill-ai.json

---

## Summary

Wrote 20 DQ rules for the AI exposure backfill into consumable.program_career_paths (626K rows) and consumable.career_branches (15,944 rows). This backfill populates stat_res, boss_ai_score, and related fields by joining to consumable.ai_exposure.

Key EDA findings that shaped thresholds:
- SOC match rate: 57.4% (not 80-90% as originally estimated)
- Post-backfill stat_res null rate: 42.6% (not 10-20%)
- Inverse invariant: 100% hold in source data (389/389 rows)
- career_branches delta coverage: 25.7% (both SOCs matched)

---

## Rules Written

| Rule ID | Priority | Dimension | Table | Description |
|---------|----------|-----------|-------|-------------|
| GLD-BF-001 | P0 | Validity | PCP | stat_res range 1-10 where non-null |
| GLD-BF-002 | P0 | Validity | PCP | boss_ai_score range 1-10 where non-null |
| GLD-BF-003 | P0 | Consistency | PCP | stat_res + boss_ai_score = 11 |
| GLD-BF-004 | P1 | Completeness | PCP | stat_res null rate 40-45% |
| GLD-BF-005 | P0 | Consistency | PCP | stat_res/boss_ai_score null agreement |
| GLD-BF-006 | P0 | Validity | PCP | stats_available_count range 0-5 |
| GLD-BF-007 | P0 | Validity | PCP | bosses_available_count range 0-5 |
| GLD-BF-008 | P0 | Consistency | PCP | stats_available_count >= 1 when stat_res non-null |
| GLD-BF-009 | P0 | Consistency | PCP | bosses_available_count >= 1 when boss_ai_score non-null |
| GLD-BF-010 | P1 | Coverage | PCP | stats_available_count=5 at 20-25% |
| GLD-BF-011 | P0 | Volume | PCP | Row count unchanged (580K-700K) |
| GLD-BF-012 | P0 | Volume | CB | Row count unchanged (15,944 exact) |
| GLD-BF-013 | P0 | Validity | CB | AI stat ranges 1-10 (all 4 columns) |
| GLD-BF-014 | P0 | Consistency | CB | res_delta = related_res - source_res |
| GLD-BF-015 | P0 | Consistency | CB | ai_boss_delta = related_ai_boss - source_ai_boss |
| GLD-BF-016 | P0 | Validity | CB | AI deltas range -9 to +9 |
| GLD-BF-017 | P0 | Consistency | CB | AI delta null when operand null |
| GLD-BF-018 | P0 | Consistency | CB | source/related AI stat pair null agreement |
| GLD-BF-019 | P0 | Consistency | CB | Inverse invariant on both sides |
| GLD-BF-020 | P2 | Coverage | CB | Delta coverage 22-32% |

---

## Superseded Rules

| Old Rule | Old Name | Superseded By | Reason |
|----------|----------|---------------|--------|
| GLD-FE-010 | stat_res is 100% null (placeholder) | GLD-BF-001 | Backfill populates stat_res for ~57.4% of rows |
| GLD-FE-011 | boss_ai_score is 100% null (placeholder) | GLD-BF-002 | Backfill populates boss_ai_score for ~57.4% of rows |
| GLD-FE-020 | stats_available_count range 0-4 (MVP) | GLD-BF-006 | Range extends to 0-5 with stat_res populated |
| GLD-FE-022 | bosses_available_count range 0-4 (MVP) | GLD-BF-007 | Range extends to 0-5 with boss_ai_score populated |

---

## Rules Retained Unchanged

The following existing rules remain valid after backfill:
- **GLD-FE-001** (grain uniqueness) -- backfill does not change grain
- **GLD-FE-003** (PCP row count 580K-700K) -- LEFT JOIN preserves rows
- **GLD-FE-021** (stats_available >= 2 for 90%+) -- still valid
- **GLD-FE-034** (CB row count = 15,944) -- LEFT JOIN preserves rows
- **GLD-FE-036** (CB stat ranges for grw/hmn/burnout) -- still valid, extended by GLD-BF-013
- **GLD-FE-037** (CB delta ranges for grw/hmn/burnout) -- still valid, extended by GLD-BF-016
- **GLD-FE-038** (CB delta null consistency for grw/hmn/burnout/wage) -- still valid, extended by GLD-BF-017

---

## Consumable Pattern Evaluation

This backfill modifies existing tables rather than creating new consumable tables. The consumable patterns from `governance/dq-rule-templates/consumable-patterns.json` were evaluated but the template directory does not exist in this project. Pattern evaluation conducted based on established conventions from existing DQ rule files.

| Pattern | Disposition | Notes |
|---------|-------------|-------|
| CONS-GRAIN-UNIQUE | Not applicable | Backfill does not change grain. GLD-FE-001 and GLD-FE-032 remain valid. |
| CONS-IMPOSSIBLE-VALUE | Written | GLD-BF-001, GLD-BF-002, GLD-BF-013, GLD-BF-016 cover impossible values for all new/modified fields. |
| CONS-CROSS-TABLE | Written | GLD-BF-003, GLD-BF-005, GLD-BF-014, GLD-BF-015, GLD-BF-017, GLD-BF-018, GLD-BF-019 validate cross-field consistency. |
| CONS-GOLDEN-DATASET | Deferred | No golden dataset exists at governance/golden-datasets/gold-futureproof-engine-backfill-ai-golden.json. Requires human override. |
| CONS-COLLISION-RESOLVED | Not applicable | No concept normalization in this backfill. ai_exposure values are passthrough. |
| CONS-COVERAGE-FLOOR | Written | GLD-BF-004 (PCP null rate) and GLD-BF-020 (CB delta coverage) serve as coverage floor checks. |

---

## Adversarial Evaluation

### Structural Integrity
- **Grain uniqueness:** Not modified by backfill. GLD-FE-001 (PCP) and GLD-FE-032 (CB) remain valid.
- **Foreign keys:** ai_exposure.soc_code is the new FK. Validated upstream by GLD-AIE-010 (all ai_exposure SOC codes exist in occupation_profiles). PCP/CB join uses LEFT JOIN, so no FK violation is possible on the consumer side.
- **Cross-column derivations:** GLD-BF-008/009 validate counter increments. GLD-BF-014/015 validate delta derivations.

### Semantic Validity
- **Impossible values:** stat_res and boss_ai_score must be 1-10 (GLD-BF-001, GLD-BF-002, GLD-BF-013). No negative resilience possible.
- **Cross-column relationships:** Inverse invariant stat_res + boss_ai_score = 11 (GLD-BF-003, GLD-BF-019). Null agreement (GLD-BF-005, GLD-BF-018).
- **Temporal ordering:** Not applicable -- no temporal fields modified by backfill.

### Distribution Expectations
- **Row count:** GLD-BF-011 (PCP 580K-700K) and GLD-BF-012 (CB 15,944 exact).
- **Value distribution:** stat_res distribution is left-skewed (mean 4.4, median 4.0). Not writing a distribution rule -- the skew is structural (high-exposure occupations dominate the crosswalk). Tracked as informational.
- **Temporal coverage:** Not applicable -- single snapshot.

### Coverage Guarantees
- **Entity coverage:** GLD-BF-004 validates 55-60% of PCP rows receive AI stats (40-45% null rate).
- **Period coverage:** Not applicable -- no temporal dimension.
- **Metric coverage:** GLD-BF-010 validates 20-25% achieve full 5/5 pentagon. GLD-BF-020 validates 22-32% of CB rows get delta.

---

## Execution Status

Pending -- rules must be executed after backfill implementation is complete.
