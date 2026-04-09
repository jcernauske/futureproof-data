# Audit Trail: DQ Rule Writing for gold-career-outcomes-college-scorecard

**Date:** 2026-04-06
**Agent:** @dq-rule-writer
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Zone:** Gold (Consumable)
**Table:** consumable.career_outcomes
**Output:** governance/dq-rules/gold-career-outcomes-college-scorecard.json

---

## Evidence Sources Read

1. **Domain context:** governance/domain-context.md -- read for domain-specific edge cases, validity rules, known data quality considerations
2. **EDA report (primary):** governance/eda/gold-career-outcomes-eda.md -- 30 threshold recommendations with evidence, 69,947 rows profiled
3. **Logical model:** governance/models/gold-career-outcomes-college-scorecard-logical.md -- constraints section, derivation rules, nullability semantics
4. **Gold spec:** docs/specs/gold-career-outcomes-college-scorecard.md -- DQ rules section, expected areas of focus
5. **Silver DQ rules (format reference):** governance/dq-rules/silver-base-college-scorecard.json -- 35 rules, format and naming conventions
6. **Consumable patterns template:** (Brightsmith framework) governance/dq-rule-templates/consumable-patterns.json
7. **Adversarial patterns template:** (Brightsmith framework) governance/dq-rule-templates/adversarial-patterns.json

---

## Consumable Pattern Evaluation (MANDATORY)

### CONS-GRAIN-UNIQUE (P0, mandatory)
**Decision:** RULE WRITTEN (GLD-CO-001)
Grain is unitid x cipcode x credential_level. EDA confirms 0 duplicates in 69,947 Silver rows. Hard constraint.

### CONS-IMPOSSIBLE-VALUE (P0, mandatory)
**Decision:** RULES WRITTEN (GLD-CO-008, GLD-CO-011, GLD-CO-018, GLD-CO-036)
Domain constraints addressed:
- confidence_tier value set (4 allowed values) -- GLD-CO-008
- outcome_completeness value set ({0.0, 0.33, 0.67, 1.0}) -- GLD-CO-011
- debt_to_earnings_tier value set (4 allowed values) -- GLD-CO-018
- credential_level must equal 3 (MVP filter) -- GLD-CO-036
- Additional range validations in P1 rules (GLD-CO-019, GLD-CO-020, GLD-CO-021)

### CONS-CROSS-TABLE (P1)
**Decision:** SKIP -- documented rationale
This spec produces a single table (consumable.career_outcomes). No other consumable tables exist yet in the pipeline. There are no cross-table relationships to validate at this time. When future Gold specs land (e.g., gold-career-projections with BLS/O*NET data), cross-table rules will be needed.

### CONS-GOLDEN-DATASET (P0, mandatory)
**Decision:** DEFERRED -- golden dataset does not yet exist
Checked governance/golden-datasets/ -- no file at governance/golden-datasets/gold-career-outcomes-college-scorecard-golden.json. The spec calls for the golden dataset to be created by @primary-agent with at least 3 independently verifiable values. Once the golden dataset exists, a golden dataset DQ rule must be written before @staff-engineer review. This is a BLOCKER for spec completion.

### CONS-COLLISION-RESOLVED (P0, mandatory)
**Decision:** SKIP -- does not apply
This spec uses single-source data (Silver base.college_scorecard only). No concept normalization is in use. No multi-source mappings exist. The CIP-to-SOC crosswalk is a future spec. Pattern does not apply.

### CONS-COVERAGE-FLOOR (P1)
**Decision:** SKIP -- does not apply
No concept normalization in use. Single-source spec. Pattern does not apply.

---

## Adversarial Pattern Evaluation

### Structural Integrity

**ADV-GRAIN-UNIQUE:** RULE WRITTEN (GLD-CO-001). Grain: unitid x cipcode x credential_level.

**ADV-FK-VALID:** SKIP -- no foreign key relationships to other Iceberg tables. The cip_family field references CIP taxonomy but there is no separate CIP family reference table in the warehouse. Referential integrity is validated indirectly via coverage rules (GLD-CO-035).

**ADV-CROSS-COLUMN:** RULES WRITTEN (GLD-CO-009, GLD-CO-010, GLD-CO-012-017, GLD-CO-029-031, GLD-CO-037, GLD-CO-038). Extensive cross-column validation covering:
- has_earnings/has_debt flag accuracy (derivation from null checks)
- All null propagation rules (6 rules covering DTE, growth rate, rank, PVI, tier)
- confidence_tier derivation logic (2 rules)
- outcome_completeness derivation consistency
- program_value_index inverse relationship with DTE
- DTE tier boundary matching

### Semantic Validity

**ADV-TEMPORAL-ORDER:** SKIP -- no start/end date columns. The table has source_load_date and promoted_at but these are metadata timestamps, not temporal range boundaries.

**Impossible values addressed:**
- Negative DTE ratio: impossible since both inputs (debt, earnings) are positive when non-null (validated in Silver). No rule needed beyond range check.
- cip_family_earnings_rank outside [0.0, 1.0]: impossible by PERCENT_RANK definition. Rule GLD-CO-021.
- outcome_completeness outside {0.0, 0.33, 0.67, 1.0}: impossible by derivation. Rule GLD-CO-011.

**Cross-column relationships validated:**
- DTE tier matches ratio ranges (GLD-CO-038)
- PVI is inverse of DTE (GLD-CO-037)
- Confidence tier conditions match derivation rules (GLD-CO-029, GLD-CO-030)
- All null propagation rules enforce derivation correctness

### Distribution Expectations

**ADV-VALUE-RANGE:** RULES WRITTEN
- DTE range 0.01-10.0 (GLD-CO-019)
- Earnings growth rate range -0.5 to 2.0 with 0.5% tolerance (GLD-CO-020)
- Rank range 0.0-1.0 (GLD-CO-021)
- Mean DTE 0.50-0.80 (GLD-CO-041)
- Mean growth rate -0.05 to +0.10 (GLD-CO-042)

**ADV-DISTRIBUTION-VARIANCE:** RULES WRITTEN (distribution monitoring)
- DTE tier distribution: Low 60-80% (GLD-CO-023), High+VeryHigh <=3% (GLD-CO-024)
- Confidence tier distribution: insufficient 45-60% (GLD-CO-025), high 15-30% (GLD-CO-026)
- Negative growth rate 35-55% (GLD-CO-027)

### Coverage Guarantees

**ADV-ENTITY-COVERAGE:** RULES WRITTEN
- Distinct institutions 2,200-3,000 (GLD-CO-034)
- Distinct CIP families 40-50 (GLD-CO-035)

**ADV-PERIOD-COVERAGE:** SKIP -- single snapshot, no temporal grain. Data is point-in-time "Most Recent Cohorts."

---

## Rules Written Summary

| Priority | Count | Rule IDs |
|----------|-------|----------|
| P0 | 23 | GLD-CO-001 through GLD-CO-018, GLD-CO-029-033, GLD-CO-036, GLD-CO-038 |
| P1 | 13 | GLD-CO-019-028, GLD-CO-034-035, GLD-CO-037 |
| P2 | 6 | GLD-CO-039-042, GLD-CO-040 |
| **Total** | **42** | |

### By Dimension

| Dimension | Count | Rule IDs |
|-----------|-------|----------|
| Uniqueness | 2 | GLD-CO-001, GLD-CO-002 |
| Volume | 1 | GLD-CO-003 |
| Consistency | 16 | GLD-CO-004-006, GLD-CO-009-010, GLD-CO-012-017, GLD-CO-029-031, GLD-CO-037-038 |
| Completeness | 3 | GLD-CO-007, GLD-CO-032-033 |
| Validity | 14 | GLD-CO-008, GLD-CO-011, GLD-CO-018-027, GLD-CO-036, GLD-CO-041-042 |
| Coverage | 4 | GLD-CO-034-035, GLD-CO-039-040 |

---

## Rules Considered but Not Written

1. **institution_control NOT NULL:** Logical model defines as NOT NULL, but EDA confirms 100% NULL due to Bronze re-ingestion blocker. Writing a P0 NOT NULL rule would guarantee failure. Instead, GLD-CO-039 tracks completeness at P2 level. institution_control excluded from GLD-CO-032 NOT NULL check.

2. **Percentile band p50 values:** The spec mentions p25/p50/p75 but the logical model only defines p25 and p75 (no p50 column). No p50 rule needed.

3. **Exact row count match with Silver:** Considered writing a cross-zone consistency rule comparing Gold count to Silver count. Deferred because the DQ runner may not have both namespaces accessible in a single query. Volume rule GLD-CO-003 provides equivalent protection via the +/-15% range.

4. **Golden dataset validation:** Deferred pending golden dataset creation. See CONS-GOLDEN-DATASET evaluation above.

5. **Earnings 1yr/2yr range validation in Gold:** These are carry-forward fields validated at Silver level (SLV-CS-022, SLV-CS-023). Not duplicated in Gold to avoid rule redundancy. If Silver rules pass, Gold values are identical.

---

## Key Threshold Decisions with EDA Evidence

| Rule | Threshold | EDA Evidence | Decision |
|------|-----------|-------------|----------|
| GLD-CO-001 | 0 duplicates | 0 duplicates in 69,947 Silver rows | Hard constraint, mathematical guarantee from promote pattern |
| GLD-CO-003 | 59,455-80,439 rows | 69,947 rows, all carried forward | +/-15% range per EDA recommendation |
| GLD-CO-020 | <=0.5% outside -0.5 to 2.0 | 15 of 22,146 (0.068%) outside range | Soft threshold allows known outliers |
| GLD-CO-023 | Low tier 60-80% | Current: 69.23% | CORRECTED from spec's "Moderate is plurality" |
| GLD-CO-025 | insufficient 45-60% | Current: 52.75% | Confirmed spec estimate of 50-55% |
| GLD-CO-027 | Negative rate 35-55% | Current: 44.2% | Expected per domain context (cross-cohort, not longitudinal) |

---

## Spec Correction Noted

The spec states "expect Moderate to be plurality" for DTE tier distribution. The EDA found "Low" is the plurality at 69.23%. Rule GLD-CO-022 validates that "Low" exceeds "Moderate" count. This correction is documented in the EDA report and should be updated in the spec.

---

## Execution Status

Rules are in PROPOSED status per REQUIRE_HUMAN_APPROVAL = true. Execution against real Iceberg data will be performed by @dq-engineer after:
1. Rules are approved (human review)
2. Gold transformer is implemented by @primary-agent
3. consumable.career_outcomes table is populated in the persistent warehouse

---

## Timestamp

2026-04-06T18:00:00Z
