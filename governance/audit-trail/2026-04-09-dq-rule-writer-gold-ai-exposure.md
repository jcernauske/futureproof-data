# Audit Trail: DQ Rule Writer - gold-ai-exposure

**Date:** 2026-04-09
**Agent:** @dq-rule-writer
**Spec:** gold-ai-exposure
**Zone:** Gold (Consumable)
**Table:** consumable.ai_exposure
**Output:** governance/dq-rules/gold-ai-exposure.json

---

## Evidence Sources

- **EDA Report:** governance/eda/gold-ai-exposure-eda.md (389 rows, 9 fields, 0 anomalies)
- **Physical Model:** governance/models/gold-ai-exposure-physical.md (PROPOSED)
- **Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 3: Gold DQ Rules section)
- **Domain Context:** governance/domain-context.md (Karpathy AI Exposure section)

## Rules Written (15 total)

| Rule ID | Name | Dimension | Priority | Evidence |
|---------|------|-----------|----------|----------|
| GLD-AIE-001 | Grain uniqueness: soc_code | Uniqueness | P0 | 389 distinct of 389 rows (EDA) |
| GLD-AIE-002 | Record ID uniqueness and not null | Uniqueness | P0 | Deterministic SHA-256 hash, 0 collision risk for 389 rows |
| GLD-AIE-003 | Row count within expected range (370-409) | Volume | P0 | 389 rows, +/-5% per EDA recommendation |
| GLD-AIE-004 | stat_res range: 1-10 | Validity | P0 | EDA actual range 1-10, physical model CHECK constraint |
| GLD-AIE-005 | boss_ai_score range: 1-10 | Validity | P0 | EDA actual range 1-10, physical model CHECK constraint |
| GLD-AIE-006 | exposure_score range: 0-10 | Validity | P0 | EDA actual 1-10, model allows 0-10 per rubric, defensive |
| GLD-AIE-007 | Inverse invariant: stat_res + boss_ai_score = 11 | Consistency | P0 | 0 violations in 389 rows (EDA) |
| GLD-AIE-008 | Rationale non-null | Completeness | P0 | 0 nulls in 389 rows (EDA) |
| GLD-AIE-009 | Rationale minimum length >= 100 chars | Validity | P1 | Min length 297 chars (EDA), 100 char floor from Silver |
| GLD-AIE-010 | Cross-validation: soc_code in occupation_profiles | Referential Integrity | P0 | 389/389 found (EDA) |
| GLD-AIE-011 | SOC code format: XX-XXXX | Validity | P0 | All validated (EDA), physical model CHECK |
| GLD-AIE-012 | All required fields non-null | Completeness | P0 | 0% null across all fields (EDA), all NOT NULL in model |
| GLD-AIE-013 | stat_res derivation consistency | Consistency | P0 | Formula verified against all 389 rows (EDA) |
| GLD-AIE-014 | boss_ai_score derivation consistency | Consistency | P0 | Formula verified against all 389 rows (EDA) |
| GLD-AIE-015 | Coverage: ai_exposure as % of occupation_profiles | Coverage | P2 | 46.8% coverage (EDA), floor at 40% |

## Consumable Pattern Evaluation (CONS-*)

| Pattern ID | Pattern Name | Rule Written? | Disposition |
|------------|-------------|---------------|-------------|
| CONS-GRAIN-UNIQUE | One value per entity-metric-period | Yes: GLD-AIE-001 | Grain is soc_code. 389 distinct of 389. |
| CONS-IMPOSSIBLE-VALUE | Values violating domain constraints | Yes: GLD-AIE-004, GLD-AIE-005, GLD-AIE-006 | stat_res [1,10], boss_ai_score [1,10], exposure_score [0,10]. Domain context confirms ranges. |
| CONS-CROSS-TABLE | Cross-table consistency | Yes: GLD-AIE-010 | Cross-validated against consumable.occupation_profiles. |
| CONS-GOLDEN-DATASET | Independently verifiable values | DEFERRED | No golden dataset exists at governance/golden-datasets/gold-ai-exposure-golden.json. Requires @primary-agent to create. Human override required to skip permanently. |
| CONS-COLLISION-RESOLVED | No duplicate concepts after collision resolution | N/A | This is a single-source spec. No concept normalization occurs at Gold level. Broad expansion is handled at Silver. No collision resolution needed in Gold. |
| CONS-COVERAGE-FLOOR | Mapped concepts cover >= threshold of base rows | N/A | No concept normalization in use at Gold level. GLD-AIE-015 tracks coverage as an informational metric instead. |

## Adversarial Pattern Evaluation (ADV-*)

### Structural Integrity

| Question | Answer | Rule |
|----------|--------|------|
| What is the declared grain? | soc_code (one row per occupation) | GLD-AIE-001 |
| What foreign keys exist? | soc_code -> consumable.occupation_profiles.soc_code | GLD-AIE-010 |
| What columns are derived? | stat_res from exposure_score, boss_ai_score from exposure_score | GLD-AIE-013, GLD-AIE-014, GLD-AIE-007 |

### Semantic Validity

| Question | Answer | Rule |
|----------|--------|------|
| What values are impossible? | stat_res or boss_ai_score outside [1,10]; exposure_score outside [0,10] | GLD-AIE-004, GLD-AIE-005, GLD-AIE-006 |
| What cross-column relationships must hold? | stat_res + boss_ai_score = 11 (for exposure >= 1); stat_res = MIN(11 - exposure, 10); boss_ai = MAX(exposure, 1) | GLD-AIE-007, GLD-AIE-013, GLD-AIE-014 |
| What temporal ordering is required? | None. promoted_at is a pipeline timestamp, not domain temporal data. Static snapshot dataset. | N/A |

### Distribution Expectations

| Question | Answer | Rule |
|----------|--------|------|
| Expected row count range? | 370-409 (389 +/- 5%) | GLD-AIE-003 |
| Expected value distribution? | exposure_score mean 5.20, median 5.0, IQR [3,7]. Roughly symmetric with slight right skew. | Tracked by range rules. No distributional DQ rule written -- the dataset is too small (389 rows) for meaningful statistical monitoring. |
| Expected temporal coverage? | N/A. Static snapshot, no time dimension. | N/A |

### Coverage Guarantees

| Question | Answer | Rule |
|----------|--------|------|
| Are all expected entities present? | 389 occupations (bls_match=true subset). | GLD-AIE-003 |
| Are all expected time periods covered? | N/A. Not a temporal dataset. | N/A |
| Are all expected metrics populated? | stat_res and boss_ai_score are 100% non-null. | GLD-AIE-012 |

## Rules Considered but Not Written

| Candidate | Reason Not Written |
|-----------|-------------------|
| Category cardinality check | 24 distinct values per EDA. Not a constrained enum -- Karpathy's categorization, not a standard taxonomy. Would create a brittle rule. |
| Promoted_at recency check | Static snapshot dataset with event-driven refresh. No meaningful freshness SLA to enforce. |
| Score distribution symmetry check | stat_res and boss_ai_score are mirror distributions by construction. Already validated by the inverse invariant (GLD-AIE-007) and derivation consistency rules (GLD-AIE-013, GLD-AIE-014). A separate distributional check would be redundant. |
| Occupation_title uniqueness | Not a model constraint (soc_code is the grain). Titles could theoretically differ from occupation_profiles titles. Not worth enforcing. |
| Golden dataset verification | Deferred -- no golden dataset exists yet. See CONS-GOLDEN-DATASET above. |

## Execution Results

Pending -- rules have not yet been executed. The consumable.ai_exposure table must be promoted before rules can run.
