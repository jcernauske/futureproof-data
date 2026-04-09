# Audit Trail: Semantic Modeler - crosswalk-cip-soc Logical Model

**Agent:** @semantic-modeler
**Spec:** docs/specs/crosswalk-cip-soc.md
**Stage:** Logical Model (Stage 2 of 3)
**Mode:** Greenfield
**Date:** 2026-04-08
**Prior Stage:** Conceptual Model (APPROVED)

## Action

Produced the logical model for base.cip_soc_crosswalk, building on the approved conceptual model.

**Artifact:** `governance/models/crosswalk-cip-soc-logical.md` (Status: PROPOSED)

## Key Modeling Decisions

1. **Single denormalized table.** All 8 conceptual entities flatten into one 14-attribute table. CIP Family and SOC Major Group are substring derivations, Data Availability is computed from cross-table lookups, and external entities are referenced via EXISTS only. Follows the established Silver Base pattern.

2. **Composite natural key (cipcode, soc_code).** This is the first Silver Base table with a multi-field natural key. The many-to-many grain requires both fields to identify a unique row. Surrogate key uses prefix 'xw'.

3. **Three CDEs identified:** cipcode, soc_code, match_quality. The taxonomy codes are CDEs because they are the join keys connecting the entire pipeline. match_quality is a CDE because it drives downstream confidence scoring.

4. **EXISTS over JOIN for flag derivation.** College Scorecard has multiple rows per CIP (one per school x credential), so EXISTS prevents row multiplication. BLS OOH and O*NET are 1:1 but EXISTS is used consistently across all three.

5. **All fields NOT NULL.** Source data has no missing values, derived fields are deterministic, and invalid rows are rejected by validation rather than stored with nulls.

6. **No CIP Family Name or SOC Major Group Name.** Unlike base.bls_ooh, this table omits human-readable classification labels because the crosswalk source doesn't provide them and deriving them requires lookup tables outside this spec's scope.

## Alternatives Considered

- **Separate dimension tables for CIP and SOC:** Rejected because the crosswalk source provides minimal attributes (code + title only), and the Silver Base pattern favors denormalization. The existing base.college_scorecard and base.bls_ooh tables already serve as the authoritative CIP and SOC dimension sources.

- **LEFT JOIN instead of EXISTS for match flags:** Rejected because College Scorecard's one-to-many relationship with CIP codes would fan out crosswalk rows. EXISTS returns a clean boolean per row.

- **Including CIP Family Name and SOC Major Group Name:** Deferred. Would require lookup tables not defined in this spec. Downstream Gold products can join to base.bls_ooh or base.college_scorecard for display labels.

## Business Terms Referenced

| Term ID | Name | Usage |
|---------|------|-------|
| BT-003 | CIP Code | cipcode attribute |
| BT-004 | Program Name | cip_title attribute |
| BT-005 | CIP Family | cip_family attribute |
| BT-015 | Record ID | record_id attribute |
| BT-016 | Source Load Date | source_load_date attribute |
| BT-017 | Ingestion Timestamp | ingested_at attribute |
| BT-027 | SOC Code | soc_code attribute |
| BT-028 | Occupation Title | soc_title attribute |
| BT-029 | SOC Major Group | soc_major_group attribute |
| BT-073 | CIP-SOC Crosswalk | Overall entity |
| BT-074 | No Match Sentinel | Filtering rule (soc_code = 99-9999 exclusion) |
| BT-075 | Join-Readiness Flag | has_scorecard_match, has_bls_match, has_onet_match |
| BT-076 | Match Quality | match_quality attribute |

## Stage Progression

| Stage | Status | Date |
|-------|--------|------|
| Conceptual | APPROVED | 2026-04-08 |
| Logical | PROPOSED | 2026-04-08 |
| Physical | Pending | -- |

## Next Step

Awaiting human review and approval of the logical model. Upon approval, the physical model (Stage 3) will be produced with DuckDB-specific types, DDL, and partitioning decisions.
