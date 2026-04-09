# Audit Trail: Physical Model for gold-onet-profiles

**Agent:** @semantic-modeler
**Spec:** gold-onet-profiles
**Stage:** Physical Model (Stage 3 of 3)
**Mode:** Greenfield
**Date:** 2026-04-08
**Status:** AUTO-APPROVED (physical models proceed directly to implementation)

---

## Stage Progression

| Stage | Status | Timestamp | Notes |
|-------|--------|-----------|-------|
| Conceptual (Stage 1) | PROPOSED | 2026-04-08 | Pending human review |
| Logical (Stage 2) | PROPOSED | 2026-04-08 | Pending human review |
| Physical (Stage 3) | AUTO-APPROVED | 2026-04-08 | Does not require human gate |

## Artifacts Produced

- `governance/models/gold-onet-profiles-physical.md` -- Physical model with DuckDB types, PyIceberg schemas, implementation guide

## Key Design Decisions

### 1. HMN Score Min/Max Rescaling (Design Change)

The EDA (governance/eda/gold-onet-profiles-eda.md) found the original formula produces a compressed 3.46-4.94 range on a 1-10 scale. The physical model documents the approved design change:

```
hmn_score = 1.0 + 9.0 * (human_ratio - observed_min) / (observed_max - observed_min)
```

Clamped to [1.0, 10.0]. This preserves relative ordering while producing meaningful differentiation.

**Alternative considered:** Absolute importance sums instead of ratios. Rejected because ratios normalize across occupations with different overall activity intensity, providing a fairer comparison.

### 2. Corrected Human-Intensive Activity Element IDs

The EDA corrected 13 of 14 element IDs from the spec. The physical model documents the corrected IDs as an implementation constant (HUMAN_INTENSIVE_ELEMENT_IDS). This is critical -- the spec explicitly warned IDs needed validation.

### 3. Burnout Elements by Flag, Not Hardcoded Names

The EDA found 3 element name mismatches between the spec and actual data (element IDs are correct). The physical model instructs the implementer to use `is_burnout_element = true` from Silver context profiles rather than hardcoding names, for robustness.

### 4. VARCHAR for JSON Columns

Chose VARCHAR over DuckDB JSON type for top_human_activities, top_5_activities, and burnout_drivers. Consistent with the established pattern in consumable.career_outcomes and more portable across Iceberg readers.

### 5. No Partitioning

798 rows (Table 1) and 15,944 rows (Table 2) are too small to benefit from partitioning. Single Parquet file per table is optimal.

### 6. Two-Phase HMN Computation

The physical model explicitly documents that HMN score computation requires two passes: first compute all human_ratios, then find min/max across the cohort, then rescale. This cannot be done in a single-pass per-occupation loop.

## Dependencies

- Logical model: governance/models/gold-onet-profiles-logical.md (all attributes mapped 1:1)
- EDA report: governance/eda/gold-onet-profiles-eda.md (corrected element IDs, score distributions)
- DQ rules: governance/dq-rules/gold-onet-profiles.json (physical constraints aligned)
- Pattern: governance/models/gold-occupation-profiles-bls-ooh-physical.md (promote pattern, schema format)

## Next Step

@primary-agent implements the two transformers:
1. `src/gold/onet_work_profiles.py` (must run first)
2. `src/gold/onet_career_transitions.py` (depends on Table 1)
