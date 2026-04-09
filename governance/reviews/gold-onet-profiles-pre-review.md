## Governance Review: gold-onet-profiles
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-08
**Verdict:** APPROVED

### Checklist Results

#### Spec Completeness

- [x] **Clear problem statement and success criteria** -- Problem statement (lines 10-11) identifies the two Gold data products. Success criteria (lines 257-267) list 11 verifiable items including row counts, score ranges, JSON validity, grain integrity, and DQ expectations.
- [x] **Input data sources identified with paths** -- Four Silver tables listed (lines 19-27): base.onet_occupations, base.onet_activity_profiles, base.onet_context_profiles, base.onet_career_transitions. Row counts provided.
- [x] **Output artifacts defined with paths and formats** -- Two Iceberg tables defined: consumable.onet_work_profiles (798 rows) and consumable.career_transitions (15,944 rows). Schemas fully specified with types, sources, and required flags.
- [x] **Transformations described** -- Table 1 transformations (lines 188-198) detail 8 steps including pivot, classify, join, compute. Table 2 transformations (lines 234-241) detail 6 steps. Both include module paths and function signatures.
- [x] **Zone assignment correct** -- Gold (consumable) zone. Correct for derived, business-ready data products.
- [x] **Primary implementation agent identified** -- @primary-agent (line 6, line 278).
- [x] **DQ rule categories specified** -- Lines 299-315 detail expected DQ rules for both tables including score ranges, null counts, JSON validity, grain uniqueness, row counts, and distribution checks.
- [x] **CDE mapping impact assessed** -- CDE fields (bls_soc_code, hmn_score, burnout_score) are implied. @cde-tagger is in the workflow (step 12).
- [x] **Lineage scope defined** -- @lineage-tracker is in the workflow (step 11). Lineage artifact path specified (line 346).
- [x] **Breaking changes flagged** -- N/A (greenfield, no existing tables).
- [x] **Testing approach defined** -- Golden dataset (lines 319-324) specifies 4 verification cases with expected derivation chains: Software Developers (15-1252), Registered Nurses (29-1141), a low-HMN occupation, and career transitions for Software Developers.

#### Data Model Gate (Greenfield Mode -- BLOCKING)

- [ ] **Business terms in glossary** -- PARTIAL. Existing glossary has Silver-era O*NET terms (O*NET-SOC Code, Content Model Element ID, Work Activity Importance, Work Context Value, Burnout Element, Career Transition, Relatedness Tier, Suppress Flag, Multi-Detail Aggregation, Data Completeness Tier, Importance Rank). Gold-specific terms NOT YET ADDED: HMN Score, Burnout Score, Confidence Tier (O*NET variant), Human-Intensive Activity, Work Profile, Career Transition Graph. @data-steward must add these before modeling begins.
- [ ] **Conceptual model** -- DOES NOT EXIST. governance/models/gold-onet-profiles-conceptual.md not found.
- [ ] **Logical model** -- DOES NOT EXIST. governance/models/gold-onet-profiles-logical.md not found.
- [ ] **Physical model** -- DOES NOT EXIST. governance/models/gold-onet-profiles-physical.md not found.

**Model Gate Status:** Models are NOT required to exist at pre-implementation review time for greenfield specs. The pipeline ordering shows data-steward (step 2) and semantic-modeler (steps 3-5) come AFTER this governance review. The gate becomes blocking at the boundary between semantic-modeler-physical and primary-agent -- implementation MUST NOT begin until all three models are approved. This is correctly encoded in the pipeline-state (primary-agent requires semantic-modeler-physical).

#### Agent Workflow

- [x] **All mandatory agents present** -- The 15-step workflow includes all required agents: governance-reviewer (pre+post), data-steward, semantic-modeler (3 stages), data-analyst, dq-rule-writer, primary-agent, dq-engineer, chaos-monkey, lineage-tracker, cde-tagger, doc-generator, staff-engineer.
- [x] **Adversarial auditor included** -- Correctly marked RUN. The HMN/Burnout formulas are subjective derivations that need scrutiny. Good call.
- [x] **Skip justifications valid:**
  - entity-resolver SKIP: Valid. Single-source Gold at BLS SOC granularity, no cross-source entity matching needed.
  - pii-scanner SKIP: Valid. Aggregated occupation-level statistics, no individual-level data.
  - temporal-modeler SKIP: Valid. Single-snapshot O*NET data with full table replace strategy.

#### Pipeline State Consistency

- [x] **Pipeline-state agent ordering matches spec workflow** -- Steps 1-15 in spec align with pipeline DAG dependencies.

**ADVISORY:** Pipeline-state has entity-resolver, pii-scanner, and temporal-modeler as `"skippable": false`. The spec says these should be SKIP. The orchestrator should set these to skipped in the pipeline-state before execution begins, or handle the skip decision at runtime. This does not block the review.

#### Governance Artifacts List

- [x] **All required artifacts identified** -- Lines 337-348 list 12 artifact categories with paths. Includes business glossary, 3 model stages, EDA report, DQ rules, DQ scorecard, chaos manifest, golden dataset, lineage, data contracts (both tables), and staff review.

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Duplicate element ID in HMN activity list: `4.A.4.a.1` appears on both line 111 ("Guiding, Directing, and Motivating Subordinates") and line 119 ("Coordinating the Work and Activities of Others"). The spec acknowledges this on lines 126-127: element IDs need validation against actual Silver data. The implementing agent must resolve the correct ID for "Coordinating the Work and Activities of Others" (likely `4.A.4.b.3`). | @primary-agent must validate all 14 element IDs against base.onet_activity_profiles and log corrections. |
| 2 | ADVISORY | Pipeline-state does not mark entity-resolver, pii-scanner, and temporal-modeler as `"skippable": true`. These are listed as SKIP in the spec but `"skippable": false` in the pipeline JSON. | Orchestrator should update pipeline-state to reflect skip decisions before execution. |
| 3 | ADVISORY | No O*NET Silver-to-Gold insight report exists (governance/insights/ has silver-to-gold-insights.md for College Scorecard and silver-bls-ooh-to-gold-insights.md for BLS OOH, but none for O*NET). Insight reports are recommended but not required for pre-implementation. | Consider having @insight-manager produce one during or after the data-analyst EDA step. |
| 4 | ADVISORY | The spec lists "14 activities" as human-intensive but acknowledges element ID uncertainty. The final count may differ once validated. The adversarial auditor should stress-test both the classification list and the formula's sensitivity to classification changes. | @adversarial-auditor should test: what happens to HMN distribution if 1-2 activities are reclassified? |
| 5 | ADVISORY | Three open design decisions (lines 327-333) require human approval: (1) human-intensive activity classification, (2) burnout weighting, (3) HMN formula approach. These are appropriately flagged. They should be resolved BEFORE the physical model is finalized. | Human must approve these decisions before @semantic-modeler produces the physical model. |

### Decision Rationale

**APPROVED.** The spec is comprehensive and implementation-ready. It meets all pre-implementation governance requirements:

1. **Completeness:** Both tables have fully specified schemas with types, sources, required flags, and derivation logic. Transformations are detailed step-by-step. Success criteria are measurable and specific.

2. **Model Gate:** The greenfield model gate is not violated. Models do not need to exist at this review stage -- the pipeline correctly sequences data-steward and semantic-modeler BEFORE primary-agent. The blocking gate is between physical model approval and implementation start.

3. **DQ Coverage:** The spec identifies specific DQ expectations for both tables, including score range validation, null count expectations, JSON validity, grain uniqueness, and distribution checks. This gives @dq-rule-writer clear guidance.

4. **Risk Awareness:** The spec correctly identifies the most subjective elements (human-intensive activity classification, burnout weighting) and routes them through both human approval and adversarial audit. The golden dataset includes verification cases that exercise the score derivation chain.

5. **Dependencies:** The build order dependency (Table 1 before Table 2) is explicitly stated and the career_transitions table's dependency on onet_work_profiles for the has_work_profile flags is documented.

The five ADVISORY issues are minor and do not block implementation. The duplicate element ID is acknowledged in the spec itself. The pipeline-state inconsistency is an orchestration concern, not a spec completeness issue. The missing insight report is recommended but optional.

**Next steps:** Proceed to @data-steward for business term identification, then @semantic-modeler for the three-stage model progression.
