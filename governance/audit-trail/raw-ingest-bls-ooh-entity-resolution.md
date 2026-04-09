# Audit Trail: Entity Resolution — raw-ingest-bls-ooh
**Date:** 2026-04-07
**Agent:** @entity-resolver
**Spec:** raw-ingest-bls-ooh
**Entity Type:** Occupation (SOC Code)

---

## Decision Log

### Decision 1: No entity resolution required
- **Rationale:** SOC codes are authoritative federal identifiers assigned by OMB/BLS. Each detailed occupation has exactly one SOC code. The 10-row sample confirms 1:1 mapping between soc_code and occupation_title with zero ambiguity.
- **Confidence:** 1.0
- **Method:** Authoritative identifier verification

### Decision 2: Summary SOC codes are a filtering concern, not an entity resolution concern
- **Rationale:** SOC codes ending in "0000" are major group aggregates. The ingestor filters these at ingestion time. This is grain-level filtering, not identity ambiguity.
- **Confidence:** 1.0
- **Method:** Domain knowledge (BLS SOC structure)

### Decision 3: Cross-source linking strategy documented for Silver zone
- **Rationale:** While BLS OOH requires no resolution internally, the FutureProof pipeline must bridge CIP (College Scorecard) to SOC (BLS/O*NET) via the NCES CIP-SOC crosswalk. This crosswalk is many-to-many with variable confidence. Strategy documented in entity resolution report for Silver zone implementation.
- **Confidence:** 0.9 (strategy is well-understood; implementation details depend on crosswalk table structure)
- **Method:** Domain analysis of taxonomy relationships

### Decision 4: O*NET integration via direct SOC join
- **Rationale:** O*NET uses the same SOC 2018 taxonomy as BLS OOH. Direct join on soc_code with confidence 1.0. Only consideration is O*NET's occasional use of extended detail codes (XX-XXXX.XX) which should be handled by prefix matching.
- **Confidence:** 1.0
- **Method:** Taxonomy version alignment verification

### Decision 5: SOC 2028 flagged as future lifecycle event
- **Rationale:** SOC taxonomy revisions occur approximately every 10 years. SOC 2028 is the anticipated next revision. When released, occupation codes may change, requiring entity lifecycle event handling (mergers, splits, reclassifications). No action needed now.
- **Confidence:** 0.8 (timing and scope of SOC 2028 are estimates)
- **Method:** Domain knowledge of SOC revision cycle

---

## Artifacts Produced
- `governance/reviews/raw-ingest-bls-ooh-entity-resolution.md` — Entity resolution assessment report

## References
- Spec: `docs/specs/raw-ingest-bls-ooh.md`
- EDA: `governance/eda/raw-bls-ooh-eda.md`
- Domain context: `governance/domain-context.md` (BLS OOH section)
- Prior entity resolution: `governance/reviews/raw-ingest-college-scorecard-entity-resolution.md`
