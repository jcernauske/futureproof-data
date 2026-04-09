## Governance Review: silver-base-onet
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-08
**Verdict:** APPROVED

### Pre-Implementation Checklist Results

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement identifies the 5-to-4 Bronze-to-Silver transformation, the SOC normalization challenge, and 13 testable success criteria. |
| 2 | Input data sources identified with paths | PASS | 7 Bronze tables listed with row counts and status (5 present, 2 missing). Missing tables (Career Changers/Starters) are documented with fallback strategy. |
| 3 | Output artifacts defined with paths and formats | PASS | 4 Silver tables defined with grain, schema, estimated row counts, and FutureProof use case. |
| 4 | Transformations described (what changes, why) | PASS | Each table has detailed transformation rules: SOC truncation, multi-detail aggregation, scale filtering, dedup, self-reference removal. All "why" rationale is documented. |
| 5 | Zone assignment correct (Silver/Base) | PASS | Silver base zone. Correct for cleaned, modeled data derived from Bronze. |
| 6 | Primary implementation agent identified | PASS | @primary-agent listed in spec header and workflow step 8. |
| 7 | DQ rule categories specified | PASS | Detailed DQ rules section with specific thresholds per table and cross-table referential integrity rules. |
| 8 | CDE mapping impact assessed | PASS | @cde-tagger listed as step 12 in workflow. New fields (bls_soc_code, element_id, importance, context_value, is_burnout_element, etc.) will need CDE assessment. |
| 9 | Lineage scope defined | PASS | @lineage-tracker listed as step 11. Lineage path documented in governance artifacts section. Transformations to capture: SOC truncation, multi-detail averaging, scale filtering, self-reference removal. |
| 10 | Breaking changes to existing schemas flagged | PASS | Greenfield spec -- no existing tables to break. CAB review step included but expected to skip (new tables). |
| 11 | Testing approach defined | PASS | Success criteria are testable. DQ rules define specific numeric thresholds. Chaos monkey (5-cycle adversarial hardening) included. |

### Data Model Gate (Greenfield Mode)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| M1 | Business terms identified | PENDING | No O*NET Silver-specific terms exist in `governance/business-glossary.json` yet. The glossary has BLS/College Scorecard terms (BT-001 through BT-054) but no terms for: Work Activity Importance, Work Context Point Estimate, Burnout Element, Career Transition, Multi-Detail Aggregation, Relatedness Tier, etc. This is EXPECTED -- @data-steward runs at step 2, after this review. |
| M2 | Conceptual model exists | PENDING | `governance/models/silver-base-onet-conceptual.md` does not exist. Expected -- produced at step 3. |
| M3 | Logical model exists | PENDING | `governance/models/silver-base-onet-logical.md` does not exist. Expected -- produced at step 4. |
| M4 | Physical model exists | PENDING | `governance/models/silver-base-onet-physical.md` does not exist. Expected -- produced at step 7. |
| M5 | Models include Mermaid erDiagram | PENDING | Models do not yet exist. |

**Data Model Gate Verdict:** The greenfield gate requires models to be completed and APPROVED before implementation (step 8). The spec correctly sequences @data-steward (step 2), @semantic-modeler conceptual (step 3), logical (step 4), and physical (step 5) BEFORE @primary-agent (step 8). The pipeline state file confirms this dependency chain. The gate is structurally sound; models will be verified at post-implementation review.

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Burnout element IDs (section "Burnout-Relevant Elements") are flagged as tentative -- spec says "exact element IDs need to be confirmed against actual Bronze data." This is appropriate and documented as an open decision. | No block. Agent should validate IDs during implementation. Human approval gate covers this (Open Decision #1). |
| 2 | ADVISORY | The spec lists 7 Bronze input tables but only 5 exist. The 2 missing tables (Career Changers, Career Starters) are documented with the fallback strategy (use Related Occupations instead). | No block. Well-documented mitigation. |
| 3 | ADVISORY | `@adversarial-auditor` appears in the pipeline state file as a separate step after `@chaos-monkey`, but the spec's workflow (step 10) only lists `@chaos-monkey`. The pipeline state includes both. The spec's "Conditionally Skippable Agents" table says `@adversarial-auditor` should RUN. | No block. Both are present in pipeline state. Minor spec/pipeline alignment issue -- does not affect implementation. |
| 4 | ADVISORY | DQ rule for `importance_rank` says "1-41 per occupation, no gaps" and "Rows per occupation: exactly 41." This assumes all 41 Work Activities are rated for every occupation. If some occupations have fewer than 41 activities (due to suppression or missing data), this rule would false-alarm. The spec handles suppressed rows with `suppress_flag` but does not address whether suppressed rows still count toward the 41-per-occupation expectation. | No block. @data-analyst EDA (step 6) should confirm whether all occupations have exactly 41 activity ratings. DQ thresholds should be calibrated from EDA findings. |
| 5 | ADVISORY | The `relatedness_tier` derivation for career transitions references tier values "Primary-Short", "Primary-Long", "Supplemental" but does not specify whether these come from the Bronze data or are derived in Silver from the index ranges. The spec says `relatedness_tier` source is `raw.onet_related_occupations` but also defines the tier logic as "Primary-Short (index 1-5), Primary-Long (index 6-10), Supplemental (index 11-20). Uses tier of best_index row." This should be clarified: is the tier carried from Bronze or derived in Silver from the index? | No block. Implementation should follow the tier derivation logic (index ranges). Both interpretations produce the same result if Bronze already has this mapping. |

### Agent Skip Justifications Review

| Agent | Decision | Justification Quality | Verdict |
|-------|----------|----------------------|---------|
| @entity-resolver | SKIP | Good. O*NET-SOC to BLS-SOC is a deterministic truncation, not fuzzy matching. References the known 76 multi-detail cases. | ACCEPTABLE |
| @pii-scanner | SKIP | Good. Aggregated occupation data from anonymized federal surveys. References: domain-context.md PII section confirms no personal data. | ACCEPTABLE |
| @temporal-modeler | SKIP | Good. Single snapshot, full table replace. No SCD or temporal modeling needed. | ACCEPTABLE |
| @adversarial-auditor | RUN | Correct to run. First multi-source aggregation with complex dedup/filtering logic. | ACCEPTABLE |

### Human Approval Gates Identified

The spec correctly identifies 4 open decisions requiring human approval:

1. **Burnout element selection** (9 proposed elements) -- surfaced for confirmation
2. **Multi-detail aggregation strategy** (unweighted average) -- rationale provided
3. **Task Statements staying in Bronze** -- justified with downstream consumption pattern
4. **Excluding 93 "All Other"/Military occupations** -- cross-referenced with BLS OOH Silver

Additionally, the greenfield workflow requires human approval at:
- Step 2: @data-steward business terms (project-specific terms)
- Step 3: @semantic-modeler conceptual model
- Step 4: @semantic-modeler logical model

Per `REQUIRE_HUMAN_APPROVAL = true` in CLAUDE.md, all approval gates are active.

### Spec Completeness Assessment

**Strengths:**
- All 4 table schemas are fully specified with field names, types, sources, and required flags
- Grain fields are explicitly defined for each table
- Filtering rules are precise and unambiguous (IM-only, CX/CT-only, exclude 93 structurally empty)
- Aggregation strategy is clearly documented (unweighted average for multi-detail, best-index for transitions)
- DQ rules have specific numeric thresholds (importance 1.0-5.0, context CX 1.0-5.0, CT 1.0-3.0, exactly 41 activities, exactly 57 contexts)
- Cross-table referential integrity is explicitly called out
- EDA open questions from Bronze are all answered with Silver decisions
- Deduplication strategy is thorough (BLS-level aggregation + self-reference removal for transitions)
- Row count estimates are provided with derivation logic

**This is one of the most complete Silver specs reviewed in this project.** The level of detail on aggregation rules, scale filtering, and the 4-table design is implementation-ready.

### Decision Rationale

APPROVED because:

1. The spec is complete enough for implementation to proceed through the greenfield pipeline (steps 2-7: business terms, conceptual model, logical model, EDA, DQ rules, physical model)
2. All 4 table schemas are fully defined with grain, fields, types, filtering, and aggregation rules
3. DQ expectations are specific and testable
4. Human approval gates are correctly identified and sequenced
5. Skip justifications are well-reasoned and reference governance artifacts
6. The 5 advisory items are minor and do not block implementation

The greenfield data model gate is structurally satisfied -- models do not exist yet (correct for pre-implementation), and the pipeline state file enforces that models must be produced and approved before @primary-agent runs.
