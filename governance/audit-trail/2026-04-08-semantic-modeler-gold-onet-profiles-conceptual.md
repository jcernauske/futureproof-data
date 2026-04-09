# Audit Trail: Conceptual Model for gold-onet-profiles

**Date:** 2026-04-08
**Agent:** @semantic-modeler
**Spec:** docs/specs/gold-onet-profiles.md
**Mode:** Greenfield
**Stage:** 1 of 3 (Conceptual)
**Status:** PROPOSED -- awaiting human approval

## Artifact Produced

- `governance/models/gold-onet-profiles-conceptual.md`

## Inputs Consulted

- Spec: `docs/specs/gold-onet-profiles.md`
- Business glossary: `governance/business-glossary.json` (BT-054, BT-055, BT-056, BT-057, BT-058, BT-059, BT-060, BT-061, BT-062, BT-063, BT-064, BT-066, BT-067, BT-068, BT-069, BT-070, BT-071, BT-072)
- Prior Gold conceptual model: `governance/models/gold-occupation-profiles-bls-ooh-conceptual.md` (pattern reference)
- Silver conceptual model: `governance/models/silver-base-onet-conceptual.md` (upstream reference)

## Key Decisions

1. **Two central entities rather than one.** Work Profile and Career Transition are modeled as peer entities with a reference relationship, not a parent-child. Rationale: different grains (single SOC vs. SOC pair), different consumers (stat engine vs. Stage 3 branching), different row counts (798 vs. 15,944).

2. **HMN and Burnout as separate entities.** Although they will be columns in the same physical table, they represent distinct business concepts backed by different source data (activity profiles vs. context profiles) and feeding different FutureProof elements (HMN stat vs. Burnout boss). Follows the pattern from BLS OOH Gold where Growth Assessment and Wage Position were separated.

3. **Occupation Identity as shared dimension.** Both Gold tables reference the same occupation dimension via bls_soc_code. Modeled as a single shared entity rather than duplicating it per table.

4. **Nullable assessments (zero-or-one cardinality).** HMN and Burnout assessments use optional cardinality because 24 of 798 occupations lack the source data. This is consistent with how Wage Position was modeled in the BLS OOH Gold conceptual model.

5. **Cross-table reference relationship.** Career Transition references Work Profile via has_work_profile flags. This directional dependency drives the build order (Table 1 before Table 2).

## Alternatives Considered

- **Single entity for both scores:** Considered combining HMN and Burnout into a single "Occupation Scoring" entity. Rejected because they have different source data, different null patterns (though currently identical), and back different FutureProof elements. Separation is clearer for business stakeholders.

- **Career Transition as subordinate to Work Profile:** Considered modeling transitions as a child of Work Profile. Rejected because transitions exist independently of work profiles (they come from Silver career_transitions, not from the work profile computation). The reference relationship correctly captures that transitions *check* work profiles but do not *derive from* them.

## Next Steps

- Human reviews and approves/rejects the conceptual model
- If approved: proceed to Stage 2 (Logical Model)
- If rejected: incorporate feedback and revise
