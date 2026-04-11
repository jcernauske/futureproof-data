## Governance Review: silver-base-karpathy-ai-exposure
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** CHANGES REQUESTED

### Checklist Results

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement in parent spec is clear: normalize SOC codes and produce base.karpathy_ai_exposure with grain on soc_code. Success criteria line 39 covers Silver. |
| 2 | Input data sources identified with paths | PASS | Source is bronze.karpathy_ai_exposure (342 rows). Cross-reference table base.bls_ooh identified for title matching and SOC validation. |
| 3 | Output artifacts defined with paths and formats | PASS | Output table: base.karpathy_ai_exposure. Silver schema defined (10 fields). Promote pattern specified with grain_id prefix 'kai'. |
| 4 | Transformations described (what changes, why) | PARTIAL | 6 transformations described (SOC normalization, null SOC resolution, SOC cross-validation, duplicate SOC handling, exposure passthrough, rationale passthrough). However, broad SOC code expansion is NOT described despite the principal architect's zone transition review explicitly flagging this as the highest-risk transformation. |
| 5 | Zone assignment correct (Silver/Base) | PASS | Correct: this is a normalization + cross-validation step, appropriate for Silver/Base zone. |
| 6 | Primary implementation agent identified | PASS | @primary-agent identified in agent workflow (step 8). |
| 7 | DQ rule categories specified | PASS | 5 Silver DQ rules specified with priority levels (P0/P1). |
| 8 | CDE mapping impact assessed | PASS | Acknowledged in governance artifacts checklist (step 12 in agent workflow). |
| 9 | Lineage scope defined | PASS | Lineage capture listed in governance artifacts. Transformations are enumerable. |
| 10 | Breaking changes to existing schemas flagged | PASS | No breaking changes -- new table. |
| 11 | Testing approach defined | PARTIAL | No explicit Silver test plan. Bronze had 34 tests; Silver testing approach is not specified. |

### Data Model Gate (Base zone -- BLOCKING)

This is a Silver/Base zone spec creating a new table. The 3-stage data modeling progression applies. This is **Greenfield Mode** (table does not exist yet).

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Business terms in governance/business-glossary.json | PASS | BT-080 (AI Exposure Score) and BT-081 (AI Exposure Rationale) exist with status "proposed". Terms are well-defined with appropriate caveats about LLM-generated scores. |
| 2 | Business terms APPROVED by human | FAIL | Both BT-080 and BT-081 have approval_status "proposed", not "approved". REQUIRE_HUMAN_APPROVAL is true per CLAUDE.md. These terms require human approval before models can proceed. |
| 3 | Conceptual model exists | FAIL | No file at governance/models/silver-base-karpathy-ai-exposure-conceptual.md |
| 4 | Logical model exists | FAIL | No file at governance/models/silver-base-karpathy-ai-exposure-logical.md |
| 5 | Physical model exists | FAIL | No file at governance/models/silver-base-karpathy-ai-exposure-physical.md |
| 6 | Models include Mermaid erDiagram | N/A | Models do not yet exist |

**Data Model Gate Status:** EXPECTED FAILURE -- models are created by @semantic-modeler (Step 3) and @data-steward (Step 2) AFTER this pre-implementation review. The pipeline workflow places governance-reviewer pre-review at Step 1, before modeling begins. This is by design -- the pre-review confirms the spec is complete enough for modeling to proceed, not that models already exist. The models will be verified at post-implementation review (Step 7).

**Business term approval is the blocking item.** BT-080 and BT-081 must be approved before @semantic-modeler can build models that reference them, and models must exist before @primary-agent implements the Silver transformer.

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | **Broad SOC code expansion strategy is absent from Silver spec.** The principal architect's zone transition review (2026-04-09) explicitly flagged that 46 broad SOC codes (XX-XXX0) need an expansion strategy. The domain context says "propagate to all detailed codes under prefix" but the Silver spec section (Zone 2, lines 103-155) does not describe this transformation. The Silver schema, DQ rules, expected row count, and soc_resolved_method enum do not account for it. The architect recommended adding `soc_resolved_method = 'broad_expansion'` as a fourth category and updating expected row count from 342 to ~500+. This was flagged as Advisory 1 (RECOMMENDED) but it directly affects grain definition, row count, schema design, and DQ rules -- all items that must be settled before implementation. | Update Zone 2 spec section to: (a) add broad-to-detailed SOC code expansion as transformation #3.5 (between cross-validation and duplicate handling), (b) add `soc_resolved_method = 'broad_expansion'` value, (c) update expected row count to reflect expansion, (d) add DQ rule for post-expansion grain uniqueness on soc_code. |
| 2 | CHANGES REQUESTED | **Missing rationale minimum length DQ rule.** Both the principal architect and the zone transition review flagged that the rationale field is a user-facing display field (Fight AI boss narrative) and currently only has a null check. A degenerate short rationale would pass DQ but produce a bad UX. The architect recommended >= 100 chars. | Add Silver DQ rule: rationale length >= 100 characters (P1). |
| 3 | ADVISORY | **Business glossary terms BT-080 and BT-081 are "proposed" not "approved".** REQUIRE_HUMAN_APPROVAL is true. These must be approved before @semantic-modeler builds conceptual models referencing them. This is expected at this pipeline stage -- @data-steward (Step 2) handles approval. Not a spec defect, but a sequencing dependency that must be tracked. | @data-steward must obtain human approval for BT-080 and BT-081 before Step 3 begins. |
| 4 | ADVISORY | **Silver DQ rule for bls_match threshold (>= 90%) may need recalibration after broad code expansion.** If 46 broad codes fan out to ~200+ detailed codes, many of those detailed codes WILL exist in base.bls_ooh (which has 832 occupations). The 90% threshold was calibrated against 342 rows. After expansion to ~500+ rows, the match rate will change. | Recalibrate bls_match threshold after expansion strategy is formalized. |
| 5 | ADVISORY | **Deployment constraint not documented.** The architect noted that consumable.ai_exposure and consumable.program_career_paths must be promoted atomically or sequentially with no consumer reads between them. This is a Gold/backfill concern but should be noted in the spec to prevent downstream issues. | Document atomic promotion constraint in Zone 4 section. |

### Decision Rationale

The Silver zone spec is well-structured with clear transformations, a complete schema, and appropriate DQ rules for the core normalization work. However, the principal architect's zone transition review explicitly identified the broad SOC code expansion strategy as the "biggest structural challenge for Silver" and provided specific remediation steps. The spec has not been updated to incorporate this guidance.

This is not a minor gap. The broad code expansion changes:
- **Grain cardinality:** Row count goes from ~342 to ~500+ (the spec still says grain is "one row per occupation (soc_code)" with no acknowledgment of expansion)
- **Schema:** The `soc_resolved_method` enum needs a fourth value ('broad_expansion')
- **DQ rules:** Post-expansion grain uniqueness is not validated; bls_match threshold may need recalibration
- **Duplicate handling:** Transformation #4 (duplicate SOC handling) must run AFTER broad expansion, not before, or the dedup logic will incorrectly resolve conflicts

Without the expansion strategy formalized in the spec, @semantic-modeler cannot produce accurate models, @dq-rule-writer cannot write complete rules, and @primary-agent cannot implement correctly.

The rationale minimum length DQ rule (Issue #2) is a lower-risk gap but was explicitly called out by the principal architect as a "What's Missing for Production" item. Adding it is straightforward and prevents a user-facing quality issue.

**Verdict: CHANGES REQUESTED.** Issues #1 and #2 must be resolved in the spec before implementation proceeds. The spec author should update Zone 2 (lines 103-155) to incorporate the principal architect's Advisory 1 and Advisory 2 from the zone transition review. Once updated, this review can be re-run.

### Dependencies for Next Steps

After spec updates are made:
1. @data-steward (Step 2): Approve BT-080, BT-081 in business glossary
2. @semantic-modeler (Step 3): Create conceptual, logical, physical models (requires approved glossary terms and finalized spec)
3. @primary-agent (Step 8): Implement Silver transformer (requires approved models and finalized spec)
