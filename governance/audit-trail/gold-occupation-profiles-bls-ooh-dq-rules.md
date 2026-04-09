# Audit Trail: DQ Rule Writing for gold-occupation-profiles-bls-ooh

**Date:** 2026-04-07
**Agent:** @dq-rule-writer
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Zone:** Gold (Consumable)
**Table:** consumable.occupation_profiles
**Output:** governance/dq-rules/gold-occupation-profiles-bls-ooh.json

---

## Evidence Sources Read

1. **Domain context:** governance/domain-context.md -- read for BLS OOH domain-specific edge cases, SOC taxonomy rules, wage top-coding, N/A wage handling
2. **EDA report (primary):** governance/eda/gold-occupation-profiles-eda.md -- full Gold pre-implementation profiling with threshold recommendations for all derived fields
3. **Logical model:** governance/models/gold-occupation-profiles-bls-ooh-logical.md -- constraints, derivation rules, nullability semantics, CDE flags
4. **Physical model:** governance/models/gold-occupation-profiles-bls-ooh-physical.md -- CHECK constraints, NOT NULL columns, column types, PyIceberg schema
5. **Gold spec:** docs/specs/gold-occupation-profiles-bls-ooh.md -- DQ rules section, derivation formulas, golden dataset expectations
6. **Existing Gold DQ rules (format reference):** governance/dq-rules/gold-career-outcomes-college-scorecard.json -- 42 rules, naming conventions (GLD-CO-NNN prefix)
7. **Silver BLS OOH DQ rules:** governance/dq-rules/silver-base-bls-ooh.json -- 25 rules validating source data
8. **Consumable patterns template:** Not found at governance/dq-rule-templates/consumable-patterns.json (directory does not exist). Evaluated all 6 patterns from memory of the Brightsmith framework specification.
9. **Adversarial patterns template:** Not found at governance/dq-rule-templates/adversarial-patterns.json (directory does not exist). Evaluated all adversarial questions from the DQ rule writer protocol.

---

## Consumable Pattern Evaluation (MANDATORY)

### CONS-GRAIN-UNIQUE (P0, mandatory)
**Decision:** RULE WRITTEN (GLD-OP-001)
Grain is soc_code (one row per occupation). EDA confirms 832 distinct soc_code values across 832 rows (100% unique). Silver DQ rule SLV-OOH-001 validates the same constraint at the source layer. Hard constraint.

### CONS-IMPOSSIBLE-VALUE (P0, mandatory)
**Decision:** RULES WRITTEN (multiple)
Domain constraints addressed:
- grw_score range 1.0-10.0 -- GLD-OP-005
- grw_score_rounded range 1-10 -- GLD-OP-007
- market_score range 1.0-10.0 -- GLD-OP-009
- market_score_rounded range 1-10 -- GLD-OP-011
- wage_percentile_overall range 0.0-1.0 -- GLD-OP-013
- wage_percentile_education_tier range 0.0-1.0 -- GLD-OP-015
- wage_tier value set (5 values) -- GLD-OP-017
- confidence_tier value set (3 values) -- GLD-OP-021
- data_completeness value set ({0.75, 1.0}) -- GLD-OP-028
- backs_stats = 'ERN,GRW' -- GLD-OP-025
- backs_bosses = 'Market,Ceiling' -- GLD-OP-026
- SOC major group valid codes -- GLD-OP-041
- growth_category valid values -- GLD-OP-042
- education_code range 1-8 -- GLD-OP-047
- median_annual_wage range 25K-250K -- GLD-OP-043
- employment_change_pct range -50 to +60 -- GLD-OP-044

### CONS-CROSS-TABLE (P1)
**Decision:** SKIP -- documented rationale
This spec produces a single table (consumable.occupation_profiles). The other existing Gold table (consumable.career_outcomes) uses a different grain (unitid x cipcode x credential_level) and different data source (College Scorecard). The CIP-to-SOC crosswalk has not been implemented yet, so no cross-table relationships exist. When the crosswalk Gold spec lands, cross-table rules will be needed.

### CONS-GOLDEN-DATASET (P0, mandatory)
**Decision:** DEFERRED (GLD-OP-048)
Checked governance/golden-datasets/ -- no file at governance/golden-datasets/gold-occupation-profiles-bls-ooh-golden.json. The golden dataset must be created by @primary-agent with at least 3 independently verifiable derivation chains.

**SPEC ERROR DOCUMENTED:** The spec's golden dataset #3 references 29-1215 (Family Medicine Physicians) claiming it has null wage fields. EDA proves 29-1215 has median_annual_wage = $238,380 and wage_available = True, giving confidence_tier = "high". EDA recommends using 29-1211 (Anesthesiologists) instead, which genuinely has null wages and confidence_tier = "low".

Expected golden dataset entries documented in the deferred rule for @primary-agent reference:
1. Software Developers (15-1252): grw_score = 8.3700, wage_tier = very_high, confidence_tier = high
2. Registered Nurses (29-1141): grw_score = 6.4625, market_score = 7.8082, confidence_tier = high
3. Anesthesiologists (29-1211): all wage fields null, confidence_tier = low, grw_score = 5.825

This is a BLOCKER for spec completion.

### CONS-COLLISION-RESOLVED (P0, mandatory)
**Decision:** SKIP -- does not apply
This spec uses single-source data (Silver base.bls_ooh only). No concept normalization is in use. No multi-source mappings exist. The CIP-to-SOC crosswalk is a future spec. Pattern does not apply.

### CONS-COVERAGE-FLOOR (P1)
**Decision:** SKIP -- does not apply
No concept normalization in use. Single-source spec. Pattern does not apply.

---

## Adversarial Pattern Evaluation

### Structural Integrity

**ADV-GRAIN-UNIQUE:** RULE WRITTEN (GLD-OP-001). Grain: soc_code. Record ID uniqueness: GLD-OP-002.

**ADV-FK-VALID:** No foreign key relationships to other Iceberg tables in this spec. The table references base.bls_ooh (Silver), but this is a source lineage relationship, not a runtime FK. No cross-table FK rules written.

**ADV-CROSS-COLUMN:** RULES WRITTEN (extensive):
- grw_score_rounded = ROUND(grw_score) -- GLD-OP-008
- market_score_rounded = ROUND(market_score) -- GLD-OP-012
- wage_tier null iff wage_available = False -- GLD-OP-019
- confidence_tier = 'low' iff wage_available = False -- GLD-OP-024
- wage_percentile null iff wage_available = False -- GLD-OP-030
- data_completeness = count non-null core fields / 4 -- GLD-OP-054
- data_completeness = 0.75 iff 23 null-wage rows -- GLD-OP-029
- soc_major_group = soc_code[:2] -- GLD-OP-040
- wage_available = (median_annual_wage IS NOT NULL) -- GLD-OP-049
- grw_score vs growth_category alignment -- GLD-OP-038
- market_score formula consistency -- GLD-OP-039

### Semantic Validity

**ADV-TEMPORAL-ORDER:** SKIP -- no start/end date columns. The table has source_load_date and promoted_at but these are metadata timestamps, not temporal range boundaries. No temporal ordering to validate.

**Impossible values addressed:**
- Negative employment counts: GLD-OP-050
- Negative openings: GLD-OP-051
- Scores outside 1-10: GLD-OP-005, GLD-OP-007, GLD-OP-009, GLD-OP-011
- Percentiles outside 0-1: GLD-OP-013, GLD-OP-015
- Invalid enum values: GLD-OP-017, GLD-OP-021, GLD-OP-042

**Cross-column relationships validated:**
- GRW score aligns monotonically with growth_category (GLD-OP-038)
- Market score matches 0.6*grw + 0.4*openings formula (GLD-OP-039)
- All null propagation rules enforce derivation correctness (GLD-OP-019, GLD-OP-024, GLD-OP-030)
- data_completeness derivation accuracy (GLD-OP-054)

### Distribution Expectations

**ADV-VALUE-RANGE:** RULES WRITTEN
- GRW score mean 4.5-6.5 (GLD-OP-032)
- Market score stddev > 1.0 (GLD-OP-034)
- Median wage range $25K-$250K (GLD-OP-043)
- Employment change pct range -50 to +60 (GLD-OP-044)

**ADV-DISTRIBUTION-VARIANCE:** RULES WRITTEN
- GRW bucket coverage >= 8/10 (GLD-OP-033)
- Market bucket coverage >= 7/10 (GLD-OP-035)
- Confidence tier exact counts (GLD-OP-036)
- Wage tier distribution alignment (GLD-OP-037)

### Coverage Guarantees

**ADV-ENTITY-COVERAGE:** RULE WRITTEN
- All 22 SOC major groups represented (GLD-OP-053)

**ADV-PERIOD-COVERAGE:** SKIP -- single snapshot, no temporal grain. BLS Employment Projections is a single release per biennial cycle.

---

## Rules Written Summary

| Priority | Count | Rule IDs |
|----------|-------|----------|
| P0 | 31 | GLD-OP-001 through GLD-OP-031, GLD-OP-040, GLD-OP-041, GLD-OP-042, GLD-OP-048, GLD-OP-049, GLD-OP-054 |
| P1 | 23 | GLD-OP-032 through GLD-OP-039, GLD-OP-043 through GLD-OP-047, GLD-OP-050 through GLD-OP-053 |
| **Total** | **54** | |

### By Dimension

| Dimension | Count | Rule IDs |
|-----------|-------|----------|
| Uniqueness | 2 | GLD-OP-001, GLD-OP-002 |
| Volume | 1 | GLD-OP-003 |
| Completeness | 7 | GLD-OP-006, GLD-OP-010, GLD-OP-014, GLD-OP-016, GLD-OP-018, GLD-OP-027, GLD-OP-031 |
| Validity | 23 | GLD-OP-004, GLD-OP-005, GLD-OP-007, GLD-OP-009, GLD-OP-011, GLD-OP-013, GLD-OP-015, GLD-OP-017, GLD-OP-021, GLD-OP-022, GLD-OP-023, GLD-OP-025, GLD-OP-026, GLD-OP-028, GLD-OP-032, GLD-OP-033, GLD-OP-034, GLD-OP-035, GLD-OP-036, GLD-OP-037, GLD-OP-041, GLD-OP-042, GLD-OP-047 |
| Consistency | 20 | GLD-OP-008, GLD-OP-012, GLD-OP-019, GLD-OP-024, GLD-OP-029, GLD-OP-030, GLD-OP-038, GLD-OP-039, GLD-OP-040, GLD-OP-043, GLD-OP-044, GLD-OP-045, GLD-OP-046, GLD-OP-048, GLD-OP-049, GLD-OP-050, GLD-OP-051, GLD-OP-052, GLD-OP-053, GLD-OP-054 |
| Coverage | 1 | GLD-OP-053 |

---

## Rules Considered but Not Written

1. **Exact row count match with Silver:** Considered writing a cross-zone consistency rule comparing Gold count to Silver count via a join. Not written because GLD-OP-003 enforces exact count = 832, which is the Silver count. The DQ runner may not have both namespaces accessible in a single query context.

2. **Wage percentile distinct value count:** EDA shows 748 distinct values (61 tied-wage pairs). Not written because the exact count depends on wage data distribution and tied pairs are valid PERCENT_RANK behavior, not a quality issue.

3. **Record ID format validation (op-XXXX pattern):** Considered but not written. The record_id format is an implementation detail of compute_grain_id(). Uniqueness check (GLD-OP-002) is sufficient.

4. **Openings score intermediate value validation:** The openings_score (1.0 + 9.0 * PERCENT_RANK(openings)) is an intermediate computation not persisted in the table. Cannot validate directly. Market score formula consistency (GLD-OP-039) validates the end result instead.

5. **Education level name consistency with education_code:** These are carried from Silver where a lookup table enforces the mapping. Silver DQ validates this relationship. Not duplicated in Gold.

6. **Promoted_at recency check:** Considered a freshness rule on promoted_at. Not written because promoted_at is generated at promotion time and will always be "now" when the pipeline runs. Source data freshness is tracked via source_load_date at the Silver level.

---

## Key Threshold Decisions with EDA Evidence

| Rule | Threshold | EDA Evidence | Decision |
|------|-----------|-------------|----------|
| GLD-OP-003 | Exactly 832 rows | 832 Silver rows, 1:1 carry-forward | Exact count, not range (unlike career_outcomes which uses +/-15%) because this spec explicitly states no rows added or dropped |
| GLD-OP-032 | GRW mean 4.5-6.5 | Actual: 5.321. Spec target 5.5-6.5 too tight. | Widened per EDA recommendation. Left-skew from declining occupations pulls mean below median (5.562). |
| GLD-OP-035 | Market buckets >= 7/10 | Actual: 9/10 (bucket 10 absent) | Bucket 10 is structurally absent -- no occupation has both top growth AND top openings simultaneously. 7 provides buffer. |
| GLD-OP-036 | Exact tier counts 735/74/23 | EDA: deterministic from input flags + wage availability | Exact counts because the derivation is deterministic CASE logic on boolean inputs. |
| GLD-OP-028 | data_completeness in {0.75, 1.0} | Spec lists {0.0-1.0}; actual only 2 values | Narrowed from spec because 3 of 4 core fields are 100% non-null. Only median_annual_wage contributes variation. |

---

## Spec Corrections Noted

1. **Golden dataset #3 (SPEC ERROR):** Spec claims 29-1215 (Family Medicine Physicians) has null wages. EDA proves median_annual_wage = $238,380 with confidence_tier = "high". Must use 29-1211 (Anesthesiologists) instead.

2. **GRW mean target range:** Spec targets 5.5-6.5 for grw_score mean. EDA shows actual mean = 5.321, below the spec's lower bound. Widened to 4.5-6.5 per EDA recommendation.

3. **Market score bucket 10:** Spec implies all 10 buckets should be populated. EDA confirms bucket 10 is structurally empty (max = 9.239). This is a property of the labor market, not a scoring defect.

4. **data_completeness value set:** Spec lists {0.0, 0.25, 0.5, 0.75, 1.0} as possible values. EDA confirms only {0.75, 1.0} appear in current data because only median_annual_wage is nullable among the 4 core fields.

---

## Execution Status

Rules are in PROPOSED status per REQUIRE_HUMAN_APPROVAL = true. Execution against real Iceberg data will be performed by @dq-engineer after:
1. Rules are approved (human review)
2. Gold transformer is implemented by @primary-agent
3. consumable.occupation_profiles table is populated in the persistent warehouse

---

## Timestamp

2026-04-07T20:00:00Z
