# Entity Resolution Assessment: gold-onet-profiles

**Date:** 2026-04-08
**Agent:** @entity-resolver
**Spec:** docs/specs/gold-onet-profiles.md
**Decision:** SKIP CONFIRMED

## Rationale

This Gold spec produces two tables from O*NET Silver data exclusively:

1. **consumable.onet_work_profiles** (798 rows) -- derived from base.onet_occupations, base.onet_activity_profiles, and base.onet_context_profiles
2. **consumable.career_transitions** (15,944 rows) -- derived from base.onet_career_transitions joined to base.onet_occupations

All four source tables originate from a single source system (O*NET) and share the same entity key: `bls_soc_code` (6-digit BLS Standard Occupational Classification code). Entity identity was already resolved during the Silver zone processing (spec: silver-base-onet), where O*NET's 8-digit detail codes were aggregated to BLS 6-digit SOC granularity.

### Why Entity Resolution Is Not Needed

| Criterion | Assessment |
|-----------|-----------|
| Cross-source matching | Not applicable. Single source (O*NET). |
| Ambiguous identifiers | Not applicable. bls_soc_code is a standardized, stable identifier. |
| Name-based matching | Not applicable. All joins are on bls_soc_code, not on name strings. |
| Entity lifecycle events | Not applicable. No mergers, splits, or reclassifications occur in this transformation. |
| Fuzzy matching | Not applicable. All joins are exact key matches. |

### Joins in This Spec

Both tables use exact-key joins on `bls_soc_code` against `base.onet_occupations`. These are deterministic lookups within a single source system, not cross-source entity resolution. The career_transitions table also joins on `related_bls_soc_code` to the same occupations table -- again, an exact key lookup within one source.

### Future Note

Cross-source entity resolution WILL be needed when O*NET data (keyed on bls_soc_code) is joined to BLS OOH data (keyed on soc_code) or College Scorecard data (keyed on cipcode via CIP-SOC crosswalk). That resolution belongs to the crosswalk spec (crosswalk-cip-soc) and any future unified Gold product, not to this single-source spec.

## Resolution Statistics

- Total entities requiring resolution: 0
- Exact matches: N/A
- High confidence matches: N/A
- Flagged for review: N/A
- Skip justified: Yes
