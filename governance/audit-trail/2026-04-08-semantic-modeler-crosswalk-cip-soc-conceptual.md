# Audit Trail: Conceptual Model for crosswalk-cip-soc

**Date:** 2026-04-08
**Agent:** @semantic-modeler
**Spec:** docs/specs/crosswalk-cip-soc.md
**Stage:** Conceptual (Stage 1 of 3)
**Mode:** Greenfield
**Status:** PROPOSED (awaiting human approval)

## Artifact Produced

- `governance/models/crosswalk-cip-soc-conceptual.md`

## Business Terms Referenced

| Term ID | Name | Source |
|---------|------|--------|
| BT-003 | CIP Code | business-glossary.json |
| BT-005 | CIP Family | business-glossary.json |
| BT-027 | SOC Code | business-glossary.json |
| BT-029 | SOC Major Group | business-glossary.json |
| BT-073 | CIP-SOC Crosswalk | business-glossary.json (added by @data-steward this session) |
| BT-074 | No Match Sentinel | business-glossary.json (added by @data-steward this session) |
| BT-075 | Join-Readiness Flag | business-glossary.json (added by @data-steward this session) |
| BT-076 | Match Quality | business-glossary.json (added by @data-steward this session) |

## Key Modeling Decisions

1. **Crosswalk Mapping as first-class associative entity.** The CIP-SOC pairing is not just a junction table -- it carries derived attributes (match flags, match quality) and represents a meaningful business assertion about program-to-occupation preparation pathways. This is the central entity of the model.

2. **Data Availability separated from Mapping identity.** Join-readiness flags and match quality are modeled as a distinct entity because they are assessed properties that may change as upstream Silver tables evolve, while the mapping itself is a static reference from NCES/BLS.

3. **External reference entities for downstream tables.** College Scorecard, BLS OOH, and O*NET are shown as external entities the crosswalk links to, not duplicated models. This preserves modeling boundaries between specs.

4. **No weighting or probability modeling.** All CIP-SOC pairings are treated equally. No "primary vs. secondary occupation" concept. This follows the source data design -- the NCES crosswalk does not assign weights.

5. **No temporal modeling.** Static reference mapping updated on ~10-year taxonomy cycles. Pipeline metadata timestamps are operational, not business dimensions.

## Alternatives Considered

- **Flattening CIP/SOC into mapping attributes:** Rejected because the many-to-many cardinality is the defining characteristic of this dataset. Separate entities make the fan-out pattern explicit.
- **Modeling match quality as a separate lookup/dimension:** Considered but rejected at conceptual level. Match quality is a derived property of each mapping, not an independent reference table. It belongs with Data Availability.
- **Including Gold-zone weighting in conceptual model:** Deferred. The spec explicitly notes that empirical employment weights (e.g., from Census data) are a future Gold enrichment. The conceptual model should not pre-commit to a design that the spec does not cover.

## Next Step

Awaiting human approval of the conceptual model. Upon approval, Stage 2 (Logical Model) will proceed.
