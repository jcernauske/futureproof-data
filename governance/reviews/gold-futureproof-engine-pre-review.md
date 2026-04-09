## Governance Review: gold-futureproof-engine
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** APPROVED

### Summary

This spec builds the unified cross-source Gold product that is the culmination of the FutureProof pipeline: two consumable tables (`consumable.program_career_paths` and `consumable.career_branches`) that join College Scorecard, BLS OOH, O*NET, and the CIP-SOC crosswalk into a single queryable surface. The spec is comprehensive, well-structured, and implementation-ready. It correctly identifies and resolves the CIP granularity mismatch (4-digit vs 6-digit) that was surfaced by the crosswalk EDA, consolidating the addendum fix into the main spec.

### Pre-Implementation Checklist

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement clearly defines the unified cross-source join. 12 success criteria defined. |
| 2 | Input data sources identified with paths | PASS | 4 Gold tables + 1 Silver crosswalk explicitly listed with grain, key fields, and CIP format noted. |
| 3 | Output artifacts defined with paths and formats | PASS | 2 tables defined: `consumable.program_career_paths` (unitid x cipcode x soc_code) and `consumable.career_branches` (soc_code x related_soc_code). Module path: `src/gold/futureproof_engine.py`. |
| 4 | Transformations described | PASS | 15-step transformation for Table 1, 6-step for Table 2. Join chain, dedup strategy, stat derivations, and match_quality logic all specified with formulas. |
| 5 | Zone assignment correct | PASS | Gold (Consumable) zone. Correct for a derived, business-ready data product. |
| 6 | Primary implementation agent identified | PASS | @primary-agent at step 8 of workflow. |
| 7 | DQ rule categories specified | PASS | Extensive DQ rule categories for both tables: row counts, grain uniqueness, CIP coverage, stat ranges, placeholder nulls, match_quality distribution, confidence tier distribution, null propagation, deltas. |
| 8 | CDE mapping impact assessed | PASS | Implicit via governance artifacts checklist. New CDEs include the five stats (ERN, ROI, RES, GRW, HMN) and five boss scores. @cde-tagger is in the workflow. |
| 9 | Lineage scope defined | PASS | Full join chain from 4 Gold + 1 Silver sources through transformations to 2 output tables. @lineage-tracker at step 11. |
| 10 | Breaking changes flagged | PASS | No breaking changes -- both tables are new (greenfield). |
| 11 | Testing approach defined | PASS | Golden dataset with 3 verifiable scenarios: ISU Business Admin join chain, poor ROI verification, and career branch delta verification. |

### Greenfield Data Model Gate

| # | Item | Status | Notes |
|---|------|--------|-------|
| G1 | Business terms identified | NOT YET | @data-steward is step 2 in workflow. Expected to run after this review approves. New terms needed: stat_ern, stat_roi, stat_res, stat_grw, stat_hmn, boss scores, match_quality, overall_confidence, etc. |
| G2 | Conceptual model exists | NOT YET | @semantic-modeler is step 3. Blocked on data-steward completing. |
| G3 | Logical model exists | NOT YET | @semantic-modeler is step 4. Blocked on conceptual approval. |
| G4 | Physical model exists | NOT YET | @semantic-modeler step 5. Blocked on logical approval. |
| G5 | Mermaid erDiagram blocks | NOT YET | Will be verified at model creation time. |

**Gate assessment:** This is a greenfield Gold spec. The data modeling progression (business terms, conceptual, logical, physical) has not yet started, which is correct -- those steps come AFTER this pre-implementation review in the pipeline workflow (steps 2-5). The spec correctly sequences them. The pre-implementation review validates that the spec is ready for the modeling pipeline to begin, not that models already exist. Models must be APPROVED before @primary-agent begins implementation at step 8.

### Agent Workflow Review

| # | Item | Status | Notes |
|---|------|--------|-------|
| W1 | @governance-reviewer (pre) | PASS | Step 1. This review. |
| W2 | @data-steward | PASS | Step 2. Business terms. |
| W3 | @semantic-modeler (conceptual) | PASS | Step 3. With human approval gate. |
| W4 | @semantic-modeler (logical) | PASS | Step 4. With human approval gate. |
| W5 | @data-analyst (EDA) | PASS | Step 6. Validates CIP prefix join coverage and stat distributions. |
| W6 | @dq-rule-writer | PASS | Step 7. Gold DQ rules. |
| W7 | @semantic-modeler (physical) | ADVISORY | Step 5 in spec workflow, but pipeline-state has it after logical. See Issue #2. |
| W8 | @primary-agent | PASS | Step 8. Implementation. |
| W9 | @dq-engineer | PASS | Step 9. Execute rules, produce scorecard. |
| W10 | @chaos-monkey | PASS | Step 10. 5-cycle hardening. |
| W11 | @lineage-tracker | PASS | Step 11. OpenLineage capture. |
| W12 | @doc-generator | PASS | Step 12. Dictionary + contracts. |
| W13 | @governance-reviewer (post) | PASS | Step 13. Post-implementation check. |
| W14 | @staff-engineer | PASS | Step 14. Final review. Last gate. |

**Conditionally skippable agents:**

| Agent | Spec Decision | Governance Assessment |
|-------|---------------|----------------------|
| @entity-resolver | SKIP -- deterministic key joins (CIP prefix, SOC codes) | ACCEPTABLE. No fuzzy matching in this spec. Joins use LEFT(5) prefix and exact SOC matches. |
| @pii-scanner | SKIP -- aggregated public statistics | ACCEPTABLE. All source data is public federal statistics (College Scorecard, BLS, O*NET). No individual-level data. |
| @temporal-modeler | SKIP -- single-snapshot, full table replace | ACCEPTABLE. No temporal dimension in this spec. |
| @adversarial-auditor | RUN | CORRECT. Cross-source join is the highest-risk transformation in the pipeline. Must verify CIP prefix coverage, null propagation, dedup correctness. |

**Workflow gap (minor):** The spec workflow (steps 1-14) does not include @cde-tagger as an explicit step, but the pipeline-state JSON does include it. The spec lists @doc-generator for "Dictionary + contracts" which in practice includes CDE tagging as a prerequisite. The Brightsmith reference workflow has @cde-tagger at step 13 before @doc-generator at step 14. The pipeline-state correctly models this dependency. No action required -- the pipeline-state is authoritative for execution order.

**Workflow gap (minor):** The spec does not list @cab-agent, but pipeline-state includes `cab-review` as skippable. This is correct -- new tables skip CAB review per Brightsmith rules.

### Insight Traceability

Two insight reports exist that are relevant to this spec:

**1. `governance/insights/silver-to-gold-insights.md` (College Scorecard)**
- Recommended CIP-SOC crosswalk integration (P0 priority) -- ADDRESSED by this spec's crosswalk join
- Recommended `consumable.career_outcomes` as Tier 1 product -- ALREADY BUILT (prerequisite)
- Noted institution_control is 100% null -- spec does not depend on this field, no issue
- Noted 2yr vs 1yr earnings cohort caveat -- spec uses only 1yr earnings, acceptable

**2. `governance/insights/silver-bls-ooh-to-gold-insights.md` (BLS OOH)**
- Recommended `consumable.occupation_profiles` as Tier 1 product -- ALREADY BUILT (prerequisite)
- Identified 23 null-wage occupations risk -- spec handles via LEFT JOIN and null propagation in stat derivations
- Identified 70 catchall + 7 broad occupation risk -- spec's match_quality and confidence_tier handle this implicitly through the join success flags
- Recommended cross-source integration via crosswalk (Tier 3 Product #5) -- this spec IS that product

Both insight reports' core recommendations are addressed by this spec or its prerequisites. DQ rules must validate these at post-implementation. No CHANGES REQUESTED for insight traceability.

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | The spec's agent workflow numbering (steps 1-14) differs slightly from the Brightsmith reference workflow ordering. Specifically, the spec places @semantic-modeler physical model at step 5 (between logical model and EDA), but the Brightsmith reference workflow places physical model generation at step 7 (after DQ rules are written). The pipeline-state JSON has physical model depending only on logical model, which is more permissive. | No block. The pipeline-state is the authoritative execution order. The spec workflow is descriptive, not prescriptive for ordering. Physical model after logical is correct regardless of exact position. |
| 2 | ADVISORY | The pipeline-state JSON includes `entity-resolver`, `pii-scanner`, and `temporal-modeler` as NOT_STARTED with `skippable: false`, but the spec marks them as SKIP. The pipeline-state should mark these as skippable or pre-skip them with justification. | No block. Skip justifications are documented in the spec. Pipeline-state should be updated when these agents are formally skipped during execution. |
| 3 | ADVISORY | The `adversarial-auditor` step in pipeline-state depends on `chaos-monkey`, but the spec does not list @adversarial-auditor as a separate step. The spec's step 10 (@chaos-monkey, 5-cycle hardening) and the "Conditionally Skippable" section's decision to RUN @adversarial-auditor suggest these are meant to be the same hardening activity. | No block. Clarify during execution whether adversarial-auditor is a separate agent run or part of chaos-monkey's output. |
| 4 | ADVISORY | The spec defines `stat_ern` and `stat_roi` as `int` type but the derivation formulas produce `ROUND(1.0 + 9.0 * raw_ern)` which could be float depending on implementation. Ensure the transformer casts to int after rounding. | No block. Implementation detail for @primary-agent. |
| 5 | ADVISORY | Five open decisions are flagged for human approval. With REQUIRE_HUMAN_APPROVAL = true, these should be resolved before or during implementation. The spec correctly identifies them but does not block on them pre-implementation. | No block. Open decisions are design choices, not governance gaps. Human should review before @primary-agent begins. |

### Governance Artifacts Checklist

The spec explicitly lists all expected governance artifacts with paths:

| Artifact | Path | Status |
|----------|------|--------|
| Business glossary | `governance/business-glossary.json` | EXISTS (will be updated) |
| Conceptual model | `governance/models/gold-futureproof-engine-conceptual.md` | NOT YET (step 3) |
| Logical model | `governance/models/gold-futureproof-engine-logical.md` | NOT YET (step 4) |
| Physical model | `governance/models/gold-futureproof-engine-physical.md` | NOT YET (step 5) |
| EDA report | `governance/eda/gold-futureproof-engine-eda.md` | NOT YET (step 6) |
| DQ rules | `governance/dq-rules/gold-futureproof-engine.json` | NOT YET (step 7) |
| DQ scorecard | `governance/dq-scorecards/gold-futureproof-engine-scorecard.md` | NOT YET (step 9) |
| Chaos manifest | `governance/chaos-manifests/gold-futureproof-engine-chaos.md` | NOT YET (step 10) |
| Golden dataset | `governance/golden-datasets/gold-futureproof-engine-golden.json` | NOT YET (step 8) |
| Lineage | `governance/lineage/gold-futureproof-engine-{timestamp}.json` | NOT YET (step 11) |
| Data contracts (2) | `governance/data-contracts/consumable-program-career-paths.yaml`, `consumable-career-branches.yaml` | NOT YET (step 12) |
| Staff review | `governance/reviews/gold-futureproof-engine-staff-review.md` | NOT YET (step 14) |

All expected artifacts are accounted for. This is comprehensive.

### Decision Rationale

**APPROVED.** This spec is well-prepared for implementation. The key factors:

1. **Completeness:** The spec defines both output tables with full schemas (40+ fields for Table 1, 20+ fields for Table 2), detailed transformation steps, stat derivation formulas with explicit breakpoints, match_quality and confidence tier logic, dedup strategy, and row count estimates.

2. **Risk awareness:** The CIP granularity mismatch is the central technical risk and is thoroughly addressed. The spec consolidates the addendum fix, documents the 91% coverage rate from EDA evidence, explains the cardinality impact, and flags the trade-off as an open decision for human review.

3. **Governance completeness:** All 12 governance artifacts are listed with paths. The agent workflow includes all mandatory agents plus justified skips for 3 optional agents. The pipeline-state file exists and is correctly initialized.

4. **DQ coverage:** DQ rule categories are specified for both tables, covering grain uniqueness, row counts, stat ranges, placeholder nulls, match quality distributions, and null propagation. This is sufficient guidance for @dq-rule-writer.

5. **Golden dataset:** Three independently verifiable scenarios defined, including a full join chain trace (ISU Business Admin through CIP prefix matching to Financial Analyst).

6. **Addendum consolidated:** The CIP granularity fix from `gold-futureproof-engine-addendum-cip-fix.md` has been fully integrated into the main spec (revised 2026-04-09). The addendum can be treated as historical context.

The five ADVISORY items are all minor -- workflow ordering nuances, type casting details, and pipeline-state metadata that will be corrected during execution. None represent governance gaps.

**Next step:** @data-steward (step 2) should identify business terms for the new fields introduced by this spec (stat_ern, stat_roi, stat_res, stat_grw, stat_hmn, boss scores, match_quality, overall_confidence, stats_available_count, bosses_available_count, etc.).
