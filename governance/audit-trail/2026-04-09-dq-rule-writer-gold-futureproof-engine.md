# Audit Trail: DQ Rule Writer - gold-futureproof-engine

**Agent:** @dq-rule-writer
**Spec:** docs/specs/gold-futureproof-engine.md
**Date:** 2026-04-09
**Zone:** Gold (Consumable)
**Tables:** consumable.program_career_paths, consumable.career_branches
**Output:** governance/dq-rules/gold-futureproof-engine.json

---

## Summary

Wrote 45 DQ rules (GLD-FE-001 through GLD-FE-045) covering two Gold consumable tables. All rules set to PROPOSED status pending approval.

### Rule Breakdown by Table

| Table | Rules |
|-------|-------|
| consumable.program_career_paths | 31 rules (GLD-FE-001 through GLD-FE-031) |
| consumable.career_branches | 14 rules (GLD-FE-032 through GLD-FE-045) |

### Rule Breakdown by Dimension

| Dimension | Count |
|-----------|-------|
| Uniqueness | 4 (P0) |
| Volume | 2 (P0) |
| Validity | 21 (P0: 17, P1: 2, P2: 1) |
| Coverage | 3 (P1) |
| Completeness | 3 (P0: 2, P1: 1) |
| Consistency | 8 (P0: 5, P1: 3) |
| Referential Integrity | 3 (P0) |

### Rule Breakdown by Priority

| Priority | Count |
|----------|-------|
| P0 | 33 |
| P1 | 10 |
| P2 | 2 |

---

## Consumable Pattern Evaluation (CONS-*)

### CONS-GRAIN-UNIQUE (P0, mandatory)
- **WRITTEN:** GLD-FE-001 (program_career_paths: unitid x cipcode x soc_code), GLD-FE-032 (career_branches: soc_code x related_soc_code)
- **Justification:** Both tables have declared grains that must be unique after dedup/enrichment.

### CONS-IMPOSSIBLE-VALUE (P0, mandatory)
- **WRITTEN:** GLD-FE-006 through GLD-FE-015 (all stat and boss score ranges 1-10), GLD-FE-036 (career_branches score ranges), GLD-FE-037 (delta ranges -9 to +9)
- **Justification:** Domain context and derivation formulas mathematically constrain all scores to 1-10 and deltas to -9/+9.

### CONS-CROSS-TABLE (P1)
- **WRITTEN:** GLD-FE-004, GLD-FE-005 (CIP prefix coverage), GLD-FE-030, GLD-FE-031, GLD-FE-043 (referential integrity), GLD-FE-029 (match_quality vs stat nulls)
- **Justification:** This is a cross-source join spec with 5 source tables. Cross-table consistency is critical.

### CONS-GOLDEN-DATASET (P0, mandatory)
- **DEFERRED:** GLD-FE-044. Golden dataset does not yet exist at governance/golden-datasets/gold-futureproof-engine-golden.json.
- **Justification:** @primary-agent has not yet created the golden dataset. EDA provides the ISU Business Admin trace with expected values that will be formalized. Rule will be activated when golden dataset is created.

### CONS-COLLISION-RESOLVED (P0, mandatory)
- **NOT APPLICABLE.** This spec does not use ConceptNormalizer or concept normalization maps. It is a cross-source join spec using deterministic keys (CIP prefix, SOC codes). No collision resolution is performed.

### CONS-COVERAGE-FLOOR (P1)
- **NOT APPLICABLE.** No concept normalization mappings are in use. CIP prefix join coverage is tracked by GLD-FE-004 and GLD-FE-005 instead.

---

## Adversarial Pattern Evaluation (ADV-*)

### ADV-GRAIN-UNIQUE
- **WRITTEN:** GLD-FE-001, GLD-FE-032 (covered under CONS-GRAIN-UNIQUE above)

### ADV-FK-VALID
- **WRITTEN:** GLD-FE-030 (soc_code -> crosswalk), GLD-FE-031 (unitid -> career_outcomes), GLD-FE-043 (career_branches -> career_transitions)

### ADV-CROSS-COLUMN
- **WRITTEN:** GLD-FE-023 (boss_loans = 11 - stat_roi), GLD-FE-024 (boss_loans null propagation), GLD-FE-025 (stat_ern null propagation), GLD-FE-029 (scorecard_only vs stat nulls), GLD-FE-038 (delta null propagation), GLD-FE-039 (branch_has_full_data consistency)

### ADV-TEMPORAL-ORDER
- **NOT APPLICABLE.** No temporal ordering constraints. Both tables are point-in-time snapshots with no start/end dates.

### ADV-VALUE-RANGE
- **WRITTEN:** GLD-FE-006 through GLD-FE-015 (stat/boss ranges), GLD-FE-036/037 (branch scores/deltas), GLD-FE-045 (wage_delta)
- **CONSIDERED BUT NOT WRITTEN:** earnings and wage absolute ranges. These are already validated upstream. Adding redundant range checks here would be test theater.

### ADV-DISTRIBUTION-VARIANCE
- **CONSIDERED BUT NOT WRITTEN.** EDA reports distributions (stat_ern centered 5-6, stat_roi skewed 8-10, etc.) but these are informational P3 monitors, not actionable DQ rules. Distribution shifts are expected as upstream data refreshes. A rule with a tight distribution tolerance would create false positives.

### ADV-ENTITY-COVERAGE
- **WRITTEN:** GLD-FE-004, GLD-FE-005 (CIP prefix coverage >= 90% distinct, >= 95% rows)

### ADV-PERIOD-COVERAGE
- **NOT APPLICABLE.** Single-snapshot pipeline with no temporal periods.

---

## Key Threshold Decisions

| Rule | Threshold | EDA Evidence |
|------|-----------|-------------|
| GLD-FE-003 (row count) | 580K-700K | EDA observed 626,406. Spec estimate of 150K-500K was pre-EDA. Widened per EDA recommendation. |
| GLD-FE-004 (CIP coverage distinct) | >= 90% | EDA: 91.0% (355/390). 35 unmatched are XX.99/XX.00 catch-alls. |
| GLD-FE-005 (CIP coverage rows) | >= 95% | EDA: 97.1%. Unmatched = 2,008 rows (2.9%). |
| GLD-FE-017 (match_quality full) | >= 90% | EDA: 93.2%. Strong BLS/O*NET SOC coverage. |
| GLD-FE-019 (confidence high) | >= 25% | EDA: 33.9%. Driven by Scorecard earnings availability. |
| GLD-FE-021 (stats >= 2) | >= 90% | EDA: 94.4% have 2+ stats. |
| GLD-FE-040 (branch_has_full_data) | >= 95% | EDA: 96.5%. Strong SOC coverage in BLS/O*NET. |

## Rules Considered But Not Written

1. **occupation_title NOT NULL enforcement (P0):** The logical model declares occupation_title as NOT NULL, but EDA found 22 SOC codes with no title from either BLS or O*NET. Excluded from GLD-FE-026 NOT NULL rule. This gap should be resolved in the transformer (use SOC code as fallback title, or handle null gracefully). Flagged for @primary-agent.

2. **stat_ern/stat_roi completeness percentage rules:** EDA shows 41.4% and 37.6% computable. These low rates are driven entirely by Scorecard privacy suppression (64% earnings null), not pipeline bugs. Writing a rule with a threshold below 50% would be uninformative. The stats_available_count distribution rule (GLD-FE-021) covers this indirectly.

3. **Earnings range checks on program_career_paths:** earnings_1yr_median, debt_median, etc. are carried from career_outcomes which already has DQ rules on ranges. Redundant validation would be test theater.

4. **best_index range check (career_branches):** EDA shows range 1-75. This is carried from career_transitions which validates it upstream. Not duplicated.

---

## Execution Status

Rules are PROPOSED. Execution will be performed by @dq-engineer after @primary-agent implements the transformer and populates the warehouse tables.
