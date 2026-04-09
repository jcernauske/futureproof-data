# Audit Trail: Physical Model — crosswalk-cip-soc

**Agent:** @semantic-modeler
**Spec:** docs/specs/crosswalk-cip-soc.md
**Stage:** Physical (Stage 3 of 3)
**Mode:** Greenfield
**Date:** 2026-04-08
**Status:** PROPOSED (pending human review)

## Stage Progression

| Stage | Date | Status | Artifact |
|-------|------|--------|----------|
| Conceptual | 2026-04-08 | APPROVED | governance/models/crosswalk-cip-soc-conceptual.md |
| Logical | 2026-04-08 | APPROVED | governance/models/crosswalk-cip-soc-logical.md |
| Physical | 2026-04-08 | PROPOSED | governance/models/crosswalk-cip-soc-physical.md |

## Artifacts Produced

- `governance/models/crosswalk-cip-soc-physical.md` — Physical model for both Bronze (raw.cip_soc_crosswalk) and Silver (base.cip_soc_crosswalk) tables

## Key Decisions

### 1. Two tables documented in one physical model

This spec covers both Bronze and Silver zones. Rather than producing separate physical model files, both tables are documented in a single artifact. This matches the spec's "single spec covers both" approach and avoids fragmenting the data flow documentation.

### 2. All VARCHAR types (no numeric columns)

Unlike BLS OOH (which has BIGINT/DOUBLE employment and wage columns), the crosswalk table is entirely identifiers, text labels, boolean flags, and pipeline metadata. All non-boolean, non-temporal columns map to VARCHAR. This is appropriate for a taxonomy bridge table.

### 3. No partitioning

At 3,000-5,000 rows, the table is tiny. A single Parquet data file per Iceberg snapshot is sufficient. No partitioning, bucketing, or sort order enforcement at the Iceberg level.

### 4. Composite natural key in grain ID

The `compute_grain_id` call uses both `cipcode` and `soc_code` as grain fields with prefix `xw`. This differs from BLS OOH (single field: soc_code, prefix: ooh) and College Scorecard (three fields: unitid+cipcode+credlev, prefix: cs). The composite key correctly represents the many-to-many grain.

### 5. EXISTS over JOIN for match flag derivation

Documented explicit use of EXISTS/IN rather than LEFT JOIN for the three match flag lookups. College Scorecard has multiple rows per CIP (one per school x credential), so a LEFT JOIN would cause row multiplication. This was an open decision in the logical model, now resolved with specific implementation guidance.

### 6. Bronze CIP format handling

Explicitly documented that openpyxl may return CIP codes as floats when parsing the XLSX. The ingestor must format them as strings with XX.XXXX zero-padding. This implements the project-wide rule from CLAUDE.md.

### 7. O*NET column name mismatch documented

Resolved logical model open issue #3 by documenting the exact column name (`bls_soc_code`, not `soc_code`) in the derivation rules, source-to-target mapping, and implementation notes.

## Alternatives Considered

### Partitioning by cip_family or soc_major_group
Rejected. The table is too small to benefit from partitioning. Any partition would have fewer than 300 rows, creating overhead without performance benefit. Full table scans are expected and efficient at this scale.

### Storing match flags as a bitmask instead of three BOOLEANs
Rejected. Three explicit BOOLEANs are more readable, easier to filter on individually, and align with the logical model. A bitmask would save negligible space and complicate downstream queries.

### Adding soc_major_group_name (like BLS OOH has)
Rejected per logical model decision #7. The crosswalk source file does not provide major group names, and deriving them requires a lookup table not part of this spec. Downstream Gold products can join to base.bls_ooh for display labels.

## Convention Sources

Physical model conventions were aligned with the approved `silver-base-bls-ooh-physical.md` model:
- Same column definition table format (DuckDB Type, Nullable, Default, Constraint, Business Term, Is CDE, Is PII)
- Same PyIceberg schema definition pattern
- Same DDL documentation style (reference only, with promote() note)
- Same traceability table structure (Logical to Physical)
- Same Iceberg table properties
