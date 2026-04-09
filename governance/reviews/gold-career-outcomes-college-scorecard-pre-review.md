# Governance Review: gold-career-outcomes-college-scorecard

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-06
**Verdict:** APPROVED

---

## Pre-Implementation Checklist Results

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement (lines 9-11) is specific and tied to the FutureProof product query pattern. 11 success criteria are measurable and testable. |
| 2 | Input data sources identified with paths | PASS | Source table `base.college_scorecard` (Silver zone), 69,947 rows, grain unitid x cipcode x credlev. |
| 3 | Output artifacts defined with paths and formats | PASS | Target: `consumable.career_outcomes` Iceberg table. Module: `src/gold/college_scorecard_career_outcomes.py`. All governance artifact paths listed in Governance Artifacts section (lines 214-225). |
| 4 | Transformations described (what changes, why) | PASS | 11 transformation steps listed (lines 128-139) with clear ordering. Derivation formulas specified for all computed fields. Window function semantics documented. |
| 5 | Zone assignment correct (Gold / Consumable) | PASS | Gold zone is correct -- this is a derived, consumer-facing data product with business logic (percentile bands, ratios, tiers). |
| 6 | Primary implementation agent identified | PASS | @primary-agent identified. Full 15-step agent workflow documented (lines 162-177). |
| 7 | DQ rule categories specified or acknowledged | PASS | 12 expected DQ rule areas documented (lines 193-202) with specific thresholds and distributions from EDA. Rules deferred to @dq-rule-writer with EDA evidence. |
| 8 | CDE mapping impact assessed | PASS | @cde-tagger listed in workflow step 12. New fields (debt_to_earnings_annual, confidence_tier, percentile bands, etc.) will need CDE/PII classification. |
| 9 | Lineage scope defined | PASS | @lineage-tracker listed in workflow step 11. Lineage artifact path specified. Source-to-target field mapping is implicit in the schema tables (Source column). |
| 10 | Breaking changes to existing schemas flagged | PASS | No breaking changes -- this is a greenfield table. @cab-agent correctly listed as skippable for new tables. |
| 11 | Testing approach defined | PASS | Golden dataset with 3 independently verifiable values specified (lines 206-209). DQ rule execution required. Chaos monkey 5-cycle hardening included. |

---

## Data Model Gate (Greenfield -- Gold Zone)

This is a greenfield spec (target table `consumable.career_outcomes` does not exist). Per the silver-gold-pipeline workflow, the 3-stage data modeling progression is required BEFORE implementation.

| # | Gate Item | Status | Notes |
|---|-----------|--------|-------|
| 1 | Business terms identified by @data-steward | NOT YET (expected) | @data-steward is step 2 in the workflow. Gold-specific terms (debt-to-earnings ratio, confidence tier, earnings percentile band, program value index, etc.) need to be proposed. The existing glossary has 17 Silver-era terms (BT-001 through BT-017). |
| 2 | Conceptual model exists | NOT YET (expected) | @semantic-modeler is steps 3-5. No Gold models exist in `governance/models/` yet. |
| 3 | Logical model exists | NOT YET (expected) | Same as above. |
| 4 | Physical model exists | NOT YET (expected) | Same as above. |

**Model Gate Verdict:** These artifacts are produced during the pipeline workflow (steps 2-5), which runs AFTER governance-reviewer-pre approval. The pre-review verifies that the spec defines these artifacts as required deliverables and that the workflow includes the correct agent sequence. Both conditions are met. The model gate will be enforced at post-implementation review.

---

## Spec Completeness Assessment

### Schema Completeness: PASS

The schema defines 30 fields across 6 categories (Identity, Core Outcomes, Percentile Bands, Financial Ratios, Relative Position, Data Quality Context, Metadata). Each field has type, source/derivation, required flag, and descriptive notes. Derivation formulas are explicit and unambiguous.

### Transformation Clarity: PASS

All 11 transformations are well-specified:
- Percentile bands: DuckDB window functions with PERCENTILE_CONT, partitioned by cip_family. Minimum 3 non-null values per CIP family per field (below threshold = null). This is well-documented in lines 146-153.
- Financial ratios: Null-safe division with explicit null propagation rules.
- Confidence tier: 4-tier bucketing with clear criteria table (lines 106-113).
- Debt-to-earnings tier: 4-tier bucketing with explicit thresholds based on DoE guidance (lines 115-124).

### Dropped Fields: PASS

3 Silver fields explicitly dropped with justification (lines 155-159): completions_count_2 (redundant), credential_description (redundant with credential_level), ingested_at (replaced by promoted_at). All justifications are reasonable.

### Golden Dataset Plan: PASS

3 independently verifiable values planned: CS program (high earnings), nursing program (moderate earnings), business program (DTE ratio math). Each must be traceable from Silver source row through Gold derivation to expected output.

---

## Alignment with Governance Artifacts

### Alignment with Domain Context (`governance/domain-context.md`): PASS

- The spec correctly reflects the Higher Education Outcomes domain.
- The spec respects the cohort measurement window semantics (1yr and 2yr are different cohorts).
- The spec's DTE thresholds reference the Gainful Employment rules mentioned in domain context (lines 131).
- PII assessment is consistent: no PII expected, @pii-scanner correctly marked SKIP.
- CIP code format (XX.XX vs XX.XXXX) is acknowledged in the Future Integration Notes.

### Alignment with Silver-to-Gold Insight Report (`governance/insights/silver-to-gold-insights.md`): PASS with ADVISORY

The spec aligns strongly with the insight report's Tier 1 Product #1 (consumable.career_outcomes). Specific verification criteria from the insight report are reflected in the spec:

| Insight Report Criterion | Spec Coverage | Status |
|--------------------------|---------------|--------|
| Row count = 69,947 (1:1 with Silver) | Spec line 34: "~69,947 (all rows carried forward; exclusion flags applied, not row drops)" | PASS |
| Grain uniqueness (unitid x cipcode x credlev) | Spec success criteria line 19 + DQ rules line 193 | PASS |
| DTE computable for exactly 21,763 rows | Not explicitly stated in spec but derivable from null propagation rules | PASS |
| Percentile bands: p25 <= p50 <= p75 | DQ rules line 197 | PASS |
| Percentile bands null for < 3 non-null values | Spec lines 150-153 + DQ rules line 198 | PASS |
| Confidence tier distribution (~52.7% insufficient) | DQ rules line 196 | PASS |
| DTE tier distribution (~69% Low) | DQ rules line 195 | PASS |

**ADVISORY:** The insight report identifies 7 specific CIP families (28, 32, 33, 34, 35, 48, 53) that should have null percentile bands due to < 3 non-null values. The spec states the minimum threshold rule but does not enumerate these 7 families. The @dq-rule-writer should include a rule verifying these specific families have null bands.

**ADVISORY:** The insight report recommends considering renaming `earnings_growth_rate` to `cohort_earnings_differential` to avoid implying individual progression. The Silver architecture review (line 196) echoes this recommendation. The spec retains the name `earnings_growth_rate`. This is a design choice, not a governance violation, but the MCP layer documentation must include the cohort caveat prominently.

### Alignment with Silver Architecture Review (`governance/reviews/silver-architecture-review.md`): PASS with ADVISORY

| Review Condition | Spec Response | Status |
|------------------|---------------|--------|
| institution_control is 100% NULL (Condition #1) | Spec marks institution_control as `required: no` (line 53). Carried from Silver as-is. | PASS -- correctly handled as nullable |
| Documentation drift (Condition #2) | Not addressed in this spec. Pre-existing Silver issue. | ADVISORY -- recommend cleanup before Gold implementation begins |
| SLV-CS-028 DQ rule fix (Condition #3) | Not in scope for this spec. Silver-layer issue. | ADVISORY -- tracked separately |
| Rename earnings_growth_rate (Condition #4) | Spec retains original name. | ADVISORY -- design choice, not blocking |

---

## Conditionally Skippable Agents Assessment

| Agent | Decision | Justification Reference | Governance Compliance |
|-------|----------|------------------------|----------------------|
| @entity-resolver | SKIP | Single-source data, no cross-source entity matching | PASS -- justified. No second data source exists yet. |
| @pii-scanner | SKIP | "governance/domain-context.md PII section: 'No personal data expected'" | PASS -- correctly references governance artifact. All data is aggregate statistics. |
| @temporal-modeler | SKIP | Single snapshot, no temporal versioning. Full table replace strategy. | PASS -- justified. No multi-year data exists. |
| @adversarial-auditor | SKIP | First Gold spec, will audit holistically when cross-source integration lands | PASS -- reasonable deferral. Note: this differs from the pipeline state JSON which lists adversarial-auditor as a non-skipped step. The pipeline state should be updated to reflect this skip decision. |

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | The insight report identifies 7 CIP families (28, 32, 33, 34, 35, 48, 53) with < 3 non-null earnings values. The spec defines the < 3 threshold rule but does not enumerate the specific families. @dq-rule-writer should include a rule verifying null bands for these 7 families. | No -- @dq-rule-writer will have access to EDA findings. |
| 2 | ADVISORY | `earnings_growth_rate` naming is flagged by both the insight report and Silver architecture review as potentially misleading (cohort difference, not longitudinal growth). Spec retains the name. | No -- design choice. MCP layer must document the caveat. |
| 3 | ADVISORY | `institution_control` is 100% NULL in Silver. The Gold spec correctly marks it as optional (required: no) and carries it forward. However, any analysis involving institution type segmentation will produce empty results until the Bronze re-ingestion occurs. | No -- correctly handled. Known gap tracked in Silver architecture review. |
| 4 | ADVISORY | Pipeline state JSON lists @adversarial-auditor as a non-skipped step, but the spec marks it as SKIP. These should be reconciled during implementation. | No -- pipeline state can be updated when skip is formally registered. |
| 5 | ADVISORY | BT-003 (CIP Code) glossary definition says "XX.XXXX" format but Silver data uses XX.XX. This is a pre-existing documentation drift issue from the Silver zone. The Gold spec correctly uses XX.XX in its schema (line 54). | No -- pre-existing issue tracked in Silver architecture review. |
| 6 | ADVISORY | The spec's agent workflow (lines 162-177) lists 15 steps, while the pipeline state JSON has 19 steps (includes entity-resolver, pii-scanner, temporal-modeler, adversarial-auditor as separate entries). The spec lists 4 of these as SKIP. Both representations are consistent when skip decisions are accounted for. | No -- informational only. |

---

## Decision Rationale

**APPROVED.** This spec is implementation-ready. The rationale:

1. **Completeness:** All 11 pre-implementation checklist items pass. The spec defines clear inputs, outputs, transformations, success criteria, and a testing approach.

2. **Schema rigor:** 30 fields are fully specified with types, derivations, nullability, and business context. The percentile band implementation is well-documented with minimum sample size requirements and null propagation rules.

3. **Governance alignment:** The spec references the correct source table, uses the idempotent promote pattern, defines grain fields for dedup, and plans all required governance artifacts (glossary terms, 3-tier models, DQ rules, golden dataset, data contract, lineage, CDE tags).

4. **Insight report alignment:** The spec directly implements the insight report's Tier 1 Product #1, with verification criteria that match the insight report's expectations for row counts, distributions, and threshold behaviors.

5. **Known gaps are correctly scoped:** institution_control (100% NULL) is carried as nullable, not blocked on. CIP format mismatch (XX.XX vs XX.XXXX) is deferred to future crosswalk integration. Both are pre-existing Silver issues, not Gold spec defects.

6. **Conditionally skippable agents** have specific governance artifact references justifying each skip decision.

The 6 ADVISORY issues are all non-blocking: 3 are pre-existing Silver documentation drift, 2 are design choices with adequate mitigation (naming, MCP caveats), and 1 is a pipeline state reconciliation that happens during implementation.

**This spec may proceed to Step 2 (@data-steward).**
