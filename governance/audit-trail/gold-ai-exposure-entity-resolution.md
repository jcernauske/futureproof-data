# Entity Resolution Assessment: gold-ai-exposure

**Date:** 2026-04-09
**Agent:** @data-analyst
**Spec:** gold-ai-exposure
**Decision:** SKIP CONFIRMED

## Rationale

The `consumable.ai_exposure` table is a single-source derivation from `base.karpathy_ai_exposure` (Silver). It contains 389 rows at grain=soc_code, all with bls_match=true. No cross-source entity matching occurs at the Gold layer.

### Why Entity Resolution Is Not Needed

| Criterion | Assessment |
|-----------|-----------|
| Cross-source matching | Not applicable. Single source (Karpathy AI exposure via Silver). |
| Ambiguous identifiers | Not applicable. soc_code is a standardized federal taxonomy identifier (SOC XX-XXXX format). |
| Name-based matching | Not applicable. All filtering uses the bls_match boolean flag set at Silver. No fuzzy or name-based joins. |
| Entity lifecycle events | Not applicable. No mergers, splits, or reclassifications in this transformation. |
| Fuzzy matching | Not applicable. No joins at all -- this is a filter + derive operation on a single table. |

### Entity Resolution Already Handled Upstream

SOC code resolution was performed at the Silver layer (spec: silver-base-karpathy-ai-exposure) using three methods:

| Method | Rows | Pct of Gold |
|--------|------|-------------|
| direct | 243 | 62.5% |
| broad_expansion | 110 | 28.3% |
| title_match | 36 | 9.3% |

The 30 rows where resolution failed (soc_resolved_method='unresolved') have bls_match=false and are excluded from Gold by the transformer's filter. Gold receives only successfully resolved SOC codes.

### Cross-Validation

All 389 Gold SOC codes exist in `consumable.occupation_profiles` (832 rows). DQ rule GLD-AIE-010 validates this referential integrity. No orphan SOC codes exist.

## Resolution Statistics

- Total entities requiring resolution: 0
- Exact matches: N/A
- High confidence matches: N/A
- Flagged for review: N/A
- Skip justified: Yes
