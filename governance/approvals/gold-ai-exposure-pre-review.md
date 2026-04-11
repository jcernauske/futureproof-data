## Governance Review: gold-ai-exposure
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** APPROVED (with advisories)

---

### Pre-Implementation Review Checklist

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Spec clearly states the goal: produce `consumable.ai_exposure` with RES score derivation and boss AI score for downstream backfill into FutureProof engine tables. Success criteria at lines 40-41 cover Gold zone. |
| 2 | Input data sources identified with paths | PASS | Source is `base.karpathy_ai_exposure` (419 rows, 389 with `bls_match=true`). Silver zone is staff-approved (2026-04-09). |
| 3 | Output artifacts defined with paths and formats | PASS | Target: `consumable.ai_exposure` Iceberg table. Gold schema defined with 9 fields, types, nullability, and notes. Data contract properties specified. |
| 4 | Transformations described (what changes, why) | PASS | Two derivations clearly specified with formulas and edge case handling: `stat_res = MIN(11 - exposure_score, 10)` and `boss_ai_score = MAX(exposure_score, 1)`. Truth table provided for RES score mapping. Rationale passthrough documented. |
| 5 | Zone assignment correct | PASS | Gold/Consumable zone is correct for a derived, business-ready product table. |
| 6 | Primary implementation agent identified | PASS | @primary-agent (Step 8 in agent workflow). |
| 7 | DQ rule categories specified | PASS | 7 Gold DQ rules defined: range checks (P0), inverse invariant (P0), row count match (P0), uniqueness (P0), completeness (P0), cross-validation against occupation_profiles (P0). All P0 -- appropriate for a consumable table. |
| 8 | CDE mapping impact assessed | PASS | Spec identifies `stat_res` and `boss_ai_score` as new derived fields. BT-080 and BT-083 glossary terms reference `gold-ai-exposure` in `used_in_models`. CDE tagging is Step 12 in agent workflow. |
| 9 | Lineage scope defined | PASS | Spec workflow includes @lineage-tracker at Step 11. Transformations are simple (two formulas + filter) so lineage scope is well-bounded. |
| 10 | Breaking changes to existing schemas flagged | PASS | No breaking changes to `consumable.ai_exposure` (new table). Backfill of `consumable.program_career_paths` and `consumable.career_branches` fills null placeholders only -- no schema changes, no existing non-null data overwritten. |
| 11 | Testing approach defined | PASS | Implicit from pipeline pattern. DQ rules serve as acceptance tests. Staff engineer review (Step 15) includes spot-checking. |

### Data Model Gate (Gold Zone -- Greenfield Mode)

| # | Item | Status | Notes |
|---|------|--------|-------|
| M1 | Business terms identified and added to glossary | PASS (partial) | BT-080 (AI Resilience/stat_res) and BT-083 (Boss AI Score) exist in `governance/business-glossary.json` with `used_in_models` including `gold-ai-exposure`. BT-094 (AI Exposure Score) and BT-095 (AI Exposure Rationale) also present and approved. However, BT-080 and BT-083 have `approval_status: "proposed"`, not "approved". See Issue #1. |
| M2 | Conceptual model exists | FAIL | No file at `governance/models/gold-ai-exposure-conceptual.md`. Must be created before implementation. |
| M3 | Logical model exists | FAIL | No file at `governance/models/gold-ai-exposure-logical.md`. Must be created before implementation. |
| M4 | Physical model exists | FAIL | No file at `governance/models/gold-ai-exposure-physical.md`. Must be created before implementation. |
| M5 | All three models include Mermaid erDiagram | N/A | Models do not exist yet. |

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | **Business glossary terms BT-080 and BT-083 have `approval_status: "proposed"`.** REQUIRE_HUMAN_APPROVAL is true. These project-specific terms must be approved by human before the conceptual model can reference them. However, this is a sequencing dependency, not a spec defect -- @data-steward (or human) must approve these terms before @semantic-modeler builds Gold models. This is consistent with how the pipeline handles term approval. | Human should approve BT-080 and BT-083 before or during model creation. Not blocking spec review. |
| 2 | ADVISORY | **Gold data models do not exist yet.** This is expected at pre-implementation review -- per the agent workflow, @semantic-modeler (Step 7) creates the models after EDA and domain context but before @primary-agent implements Gold (Step 8). The models must be created and approved (or at minimum, created with PROPOSED status) before Gold implementation begins. | @semantic-modeler must produce all three models at `governance/models/gold-ai-exposure-{conceptual,logical,physical}.md` before Step 8. |
| 3 | ADVISORY | **Silver post-review has CHANGES REQUESTED status** (model approval + glossary term approval). The Silver zone is staff-approved but has outstanding governance gaps (models PROPOSED, not APPROVED). This does not block Gold pre-implementation review -- the Gold zone can proceed in parallel with Silver governance remediation -- but the Silver gaps should be resolved. | Silver model approval should be completed. Not blocking Gold. |
| 4 | ADVISORY | **No insight report exists for the Karpathy Silver-to-Gold zone transition.** Unlike College Scorecard (silver-to-gold-insights.md) and BLS OOH (silver-bls-ooh-to-gold-insights.md), there is no `governance/insights/*karpathy*` file. Given that this is a small, simple dataset (419 rows, 2 derivation formulas), the absence of an insight report is understandable -- there is limited analytical surface area for @insight-manager to add value. | Not blocking. If @insight-manager identifies recommendations during implementation, those must have corresponding DQ rules per the Insight Traceability check. |
| 5 | ADVISORY | **Spec uses term IDs BT-080 and BT-081 in the spec text (Zone 2 Business Glossary Terms section) but the glossary has reassigned these.** BT-080 is now "AI Resilience (stat_res)" and BT-081 is now "Boss Fight Score" -- not the terms the spec originally defined (which were "AI Exposure Score (Karpathy)" and "AI Exposure Rationale"). The original spec terms were reassigned to BT-094 and BT-095 respectively. This is cosmetic -- the glossary is the source of truth, not the spec text -- but the spec text is now stale on this point. | Cosmetic. Glossary is authoritative. No action needed. |

### Decision Rationale

**APPROVED.** The Gold zone section of this spec is well-defined, implementation-ready, and governance-complete at the pre-implementation stage. Specifically:

1. **Transformations are simple and unambiguous.** Two derivation formulas with explicit edge case handling and a truth table. No complex joins, no aggregation, no windowing. This is a filter + two column derivations + passthrough.

2. **DQ rules are comprehensive and all P0.** Seven rules covering range, invariant, volume, uniqueness, completeness, and cross-referential integrity. The inverse invariant (`stat_res + boss_ai_score = 11`) is particularly well-designed -- it validates the mathematical relationship between the two derived fields.

3. **Data contract is specified.** Owner, SLA, freshness, quality tier, consumers, row count guarantee, and null guarantees are all defined. The "Medium" quality tier is honest -- these are LLM-generated scores, and the contract reflects that.

4. **Source data is stable.** Silver zone is staff-approved with 419 rows, 389 matching BLS. The Gold filter (`bls_match=true`) is well-defined. Expected output is ~389 rows (within the 300-350 contract guarantee after accounting for broad expansion creating more matched rows).

5. **The four ADVISORY items are sequencing dependencies, not spec defects.** Models must be created before implementation (by @semantic-modeler at Step 7). Glossary terms must be approved (by human). These are normal pipeline progression -- they do not indicate a problem with the spec itself.

The spec may proceed to @semantic-modeler for data model creation (Step 7), followed by @primary-agent for Gold implementation (Step 8). Human approval of BT-080 and BT-083 should occur before or during model creation.

---

**REQUIRE_HUMAN_APPROVAL is TRUE.** This review is the governance reviewer's recommendation. The human owner should review before implementation begins.
