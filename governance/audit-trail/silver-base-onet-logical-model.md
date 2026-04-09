# Audit Trail: silver-base-onet Logical Model

**Agent:** @semantic-modeler
**Spec:** silver-base-onet
**Stage:** Logical Model (Stage 2 of 3)
**Date:** 2026-04-08
**Mode:** Greenfield
**Prior Stage:** Conceptual Model (APPROVED)

## Decision Log

### 1. Four Separate Tables (Not Denormalized)

**Decision:** Model as 4 distinct tables rather than a single denormalized table.
**Rationale:** Unlike BLS OOH (single table, all 1:1 relationships at the same grain), this model has 4 distinct grains: bls_soc_code alone (occupations), bls_soc_code x element_id (activity and context profiles), and bls_soc_code x related_bls_soc_code (transitions). Row counts range from ~867 to ~49,400. Denormalization would create massive redundancy.
**Alternatives Considered:** Single wide table (rejected -- different grains make this impossible without artificial duplication).

### 2. All Attributes NOT NULL

**Decision:** Every attribute across all 45 fields is NOT NULL.
**Rationale:** O*NET provides complete data for all retained scales and elements. The Silver transformation excludes entire rows rather than producing rows with null fields. This simplifies downstream consumption.
**Alternatives Considered:** Defensive nullability on rating fields (rejected -- source data is complete for retained scales; nullable fields without actual nulls add unnecessary complexity).

### 3. CDE Assignments

**Decision:** 8 CDEs total: bls_soc_code and data_completeness_tier on occupations; bls_soc_code, element_id, and primary measurement (importance/context_value) on activity and context profiles. Zero CDEs on career transitions.
**Rationale:** CDEs are limited to grain keys (which enable cross-source joins) and primary measurements (which back Gold zone stats). Career transitions enable UI navigation, not quantitative stat computation.
**Alternatives Considered:** Marking best_index as CDE (rejected -- it drives sorting, not a stat formula).

### 4. JSON Array for O*NET Detail Codes

**Decision:** Store onet_detail_codes as a JSON text array on the occupations table.
**Rationale:** Detail codes are lineage metadata with low cardinality (2-5 per BLS SOC). A separate bridge table would add complexity for a rarely-queried field.
**Alternatives Considered:** Separate onet_occupation_details bridge table (rejected -- over-normalized for the use case).

### 5. Burnout Element IDs

**Decision:** Include 9 proposed element IDs as the is_burnout_element derivation set, subject to validation against actual Bronze data during implementation.
**Rationale:** The element IDs are from O*NET Content Model documentation. Format differences may exist in the actual data. The derivation rule is a simple IN-list that can be adjusted without schema changes.
**Alternatives Considered:** Separate burnout element reference table (rejected -- the set is small and static; a flag is simpler).

### 6. Unweighted Averaging for Multi-Detail Aggregation

**Decision:** Use unweighted arithmetic mean when averaging importance and context values across multiple O*NET detail codes for the same BLS SOC.
**Rationale:** Employment-weighted averaging would be more accurate but requires BLS employment data mapped to O*NET detail codes, which is not readily available. The onet_details_averaged field documents how many codes contributed, allowing downstream consumers to assess quality.
**Alternatives Considered:** Employment-weighted average (rejected -- data not available); median (rejected -- with 2-3 detail codes, median and mean are nearly identical).

## Stage Progression

| Stage | Status | Timestamp |
|-------|--------|-----------|
| Conceptual Model | APPROVED | 2026-04-08 |
| Logical Model | PROPOSED | 2026-04-08 |
| Physical Model | PENDING | -- |

## Artifacts Produced

- `governance/models/silver-base-onet-logical.md` (PROPOSED)

## Human Feedback Incorporated

- Conceptual model was approved without modification. Logical model maintains all conceptual decisions and extends with attribute-level detail.
