# Audit Trail: Physical Model -- gold-occupation-profiles-bls-ooh

**Agent:** @semantic-modeler
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Stage:** Physical Model (Stage 3 of 3)
**Timestamp:** 2026-04-07
**Mode:** Greenfield
**Prior Stage:** Logical Model (APPROVED)

---

## Stage Progression

| Stage | Status | Date | Notes |
|-------|--------|------|-------|
| Conceptual | APPROVED | 2026-04-07 | 7 entities identified, single denormalized table pattern confirmed |
| Logical | APPROVED | 2026-04-07 | 30 attributes defined, 12 derived, all derivation rules specified |
| Physical | PROPOSED | 2026-04-07 | 31 columns (30 attributes + promoted_at), PyIceberg schema, DDL, promote pattern |

## Decisions Made

### 1. Column count: 31 (not 30)

The logical model documents 30 attributes. The physical model has 31 columns because the logical attribute count includes all 30 fields. The mismatch is cosmetic -- the logical model counts promoted_at as an attribute (30 total), and the physical NestedField IDs run 1-31 because all 30 logical attributes plus the generated promoted_at timestamp are each assigned unique field IDs. Actually both models agree at 30 data attributes + promoted_at = 31 NestedField entries total. The NestedField count matches the column count exactly.

### 2. Sort order: soc_code ASC

Chose `soc_code ASC` over alternatives considered:
- **soc_major_group ASC, soc_code ASC** -- would cluster by major group but adds no benefit over soc_code ASC since SOC codes already sort by major group lexicographically (15-XXXX naturally clusters before 29-XXXX).
- **median_annual_wage DESC** -- optimizes wage-based queries but the primary access pattern is SOC code lookups, not wage scans.
- **No sort** -- at 832 rows, sort order is near-irrelevant for performance; chose soc_code ASC for consistency with Silver and readability.

### 3. Partition strategy: None

832 rows is too small for partitioning to provide benefit. A single Parquet file will be sub-megabyte. Matches the Silver source table's partition strategy.

### 4. PyIceberg type mappings

All type mappings follow established patterns from the Silver BLS OOH physical model and the Gold career outcomes physical model:
- Rounded scores (`grw_score_rounded`, `market_score_rounded`) use `IntegerType` per the spec's `int` type, not `LongType`.
- Employment counts use `LongType` (inherited from Silver).
- Categorical codes (`education_code`, etc.) use `IntegerType` (inherited from Silver).
- All continuous derived fields (scores, percentiles, completeness) use `DoubleType`.

### 5. growth_category NOT NULL

The logical model marks growth_category as NOT NULL. Silver marks it nullable. The Gold model follows the logical model because all 832 rows currently have non-null employment_change_pct, which guarantees non-null growth_category. Documented as an accepted risk for future data changes.

### 6. Confidence tier three-level vs four-level

Explicitly documented the difference between this model's 3-tier confidence (BT-052: high/medium/low) and the career outcomes model's 4-tier confidence (BT-024: high/medium/low/insufficient). Different business terms, different derivation logic.

## Alternatives Considered

| Alternative | Considered For | Outcome | Rationale |
|-------------|---------------|---------|-----------|
| Separate tables for wage position and growth assessment | Physical schema | Rejected | 1:1 cardinality at occupation grain; denormalized single table is the Gold zone pattern |
| Persisting openings_score as a column | Physical schema | Rejected | Intermediate calculation with no direct consumer; can be recomputed from openings_annual_avg |
| Using TimestamptzType for promoted_at | PyIceberg schema | Rejected | Existing pattern uses TimestampType; consistency with career outcomes model takes precedence |
| Adding employment_change from Silver | Physical schema | Rejected | Spec explicitly drops it as redundant with employment_change_pct |

## References

- Approved logical model: `governance/models/gold-occupation-profiles-bls-ooh-logical.md`
- Spec: `docs/specs/gold-occupation-profiles-bls-ooh.md`
- Pattern reference: `governance/models/gold-career-outcomes-college-scorecard-physical.md`
- Silver source physical model: `governance/models/silver-base-bls-ooh-physical.md`
- Existing Gold transformer (pattern): `src/gold/college_scorecard_career_outcomes.py`
