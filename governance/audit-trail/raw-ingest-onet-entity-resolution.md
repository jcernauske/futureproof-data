# Audit Trail: Entity Resolution -- raw-ingest-onet
**Date:** 2026-04-07
**Agent:** @entity-resolver
**Spec:** raw-ingest-onet
**Entity Type:** Occupation (O*NET-SOC Code)

---

## Decision Log

### Decision 1: No entity resolution required within O*NET
- **Rationale:** O*NET-SOC codes are authoritative federal identifiers defined by DOL/ETA as extensions of the OMB/BLS SOC taxonomy. Each of the 1,016 occupations has a unique O*NET-SOC code in XX-XXXX.XX format with 100% format validation, 1:1 code-to-title mapping, and zero orphan references across all 5 present tables. No variant spellings, no ambiguous identifiers, no deduplication needed.
- **Confidence:** 1.0
- **Method:** Authoritative identifier verification (full dataset per EDA)

### Decision 2: O*NET-to-BLS SOC bridging is deterministic, not entity resolution
- **Rationale:** The mapping from O*NET XX-XXXX.XX to BLS XX-XXXX is a simple string truncation (first 7 characters). 867 codes have .00 suffix (1:1 to BLS). 149 codes across 76 BLS SOCs have non-.00 suffixes (N:1 to BLS). This is a deterministic operation, not a probabilistic match. The N:1 aggregation strategy for the 76 split SOCs is a modeling decision for the Silver zone, not an identity resolution problem.
- **Confidence:** 1.0
- **Method:** Domain knowledge of O*NET-SOC and BLS SOC taxonomy relationship

### Decision 3: 93 "All Other" / Military occupations are structurally empty, not unresolved
- **Rationale:** 93 O*NET occupations (all .00 suffix) exist in the master Occupation Data table but have zero rows in all child tables. These include 74 "All Other" residual categories and 19 military occupations (55-xxxx). O*NET cannot survey these. They are not unresolved or ambiguous -- they are structurally empty by design. Silver zone should flag with `has_onet_data = false`, not treat as a resolution failure.
- **Confidence:** 1.0
- **Method:** Cross-table referential analysis + domain knowledge of SOC residual codes

### Decision 4: 29 partial-data occupations are a completeness issue, not an identity issue
- **Rationale:** 29 occupations have Task Statements and Related Occupations but no Work Activities or Work Context. These are recently added or reclassified occupations with incomplete survey coverage. Their O*NET-SOC codes are valid and properly referenced. Silver zone should flag with `onet_data_completeness = "partial"`.
- **Confidence:** 1.0
- **Method:** EDA cross-table analysis

### Decision 5: Entity registry deferred to Silver zone (consistent with BLS OOH precedent)
- **Rationale:** No entity registry entries are needed at Raw zone. O*NET-SOC codes are authoritative and require no resolution. Entity registry will be created when the Silver zone implements cross-source joins (O*NET to BLS, CIP to SOC). This is consistent with Decision 5 from the BLS OOH entity resolution.
- **Confidence:** 1.0
- **Method:** Precedent from raw-ingest-bls-ooh entity resolution assessment

### Decision 6: SOC 2028 flagged as future lifecycle event
- **Rationale:** SOC taxonomy revisions occur approximately every 10 years. SOC 2028 is anticipated next. When released, O*NET-SOC codes may change, requiring entity lifecycle events. No action needed now. This is a reaffirmation of the same flag raised in the BLS OOH assessment.
- **Confidence:** 0.8 (timing and scope of SOC 2028 are estimates)
- **Method:** Domain knowledge of SOC revision cycle

---

## Resolution Statistics
- Total entities processed: 1,016 occupations
- Exact matches (authoritative ID): 1,016 (100%)
- Fuzzy matches required: 0
- Flagged for review: 0
- Cross-source bridging analyzed: 1,016 O*NET codes mapped to 867 BLS SOC codes (deterministic)

---

## Artifacts Produced
- `governance/reviews/raw-ingest-onet-entity-resolution.md` -- Entity resolution assessment report

## References
- Spec: `docs/specs/raw-ingest-onet.md`
- EDA: `governance/eda/raw-onet-eda.md`
- Domain context: `governance/domain-context.md` (O*NET sections, particularly "SOC Code Cross-Source Bridging")
- Prior entity resolution: `governance/reviews/raw-ingest-bls-ooh-entity-resolution.md`
