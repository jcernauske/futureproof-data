## Temporal Assessment: gold-onet-profiles
**Date:** 2026-04-08
**Agent:** @temporal-modeler
**Spec:** docs/specs/gold-onet-profiles.md
**Decision:** SKIP CONFIRMED -- No temporal modeling required.

### Rationale

Both Gold tables produced by this spec (consumable.onet_work_profiles and consumable.career_transitions) operate on a single-snapshot, full-table-replace pattern. There are no bitemporal requirements.

**Evidence reviewed:**

1. **Spec design:** Both tables are derived from a single O*NET release (30.2). The pipeline performs a full table replacement on each run. There is no incremental append, no amendment tracking, and no slowly-changing dimension behavior.

2. **Domain temporal patterns (governance/domain-context.md):** The O*NET temporal patterns section confirms:
   - O*NET publishes numbered releases as complete databases, not incremental updates.
   - The `date` field on individual rows is informational metadata (survey collection date), not a temporal dimension for time-series analysis.
   - All data in a given O*NET release is considered "current" regardless of individual survey dates.
   - The recommendation is to treat each release as a full replacement.

3. **No amendment/correction mechanism:** O*NET does not have a mid-cycle correction pattern. New data arrives only via new numbered releases, which are full replacements.

4. **Gold zone transformation nature:** These tables are derived aggregates (pivoted scores, enriched graphs). They are recomputed from Silver on each run. There is no state to track across runs, no corrections to preserve, and no valid-time ranges to model.

5. **Upstream Silver pattern:** The Silver O*NET tables (base.onet_occupations, base.onet_activity_profiles, base.onet_context_profiles, base.onet_career_transitions) also follow the single-snapshot pattern, confirmed in the raw-ingest-onet temporal assessment.

### What would change this assessment

If FutureProof adds support for tracking changes across O*NET releases (e.g., "how has the HMN score for Software Developers changed from O*NET 29.0 to 30.2?"), then:
- Silver tables would need a release_version dimension.
- Gold tables would need valid_from/valid_to columns tied to O*NET release dates.
- Iceberg snapshots would preserve each release's computed scores.

This is explicitly noted as a future consideration, not a current requirement.

### Schema impact

None. No temporal columns added. No Iceberg snapshot strategy beyond the default (one snapshot per pipeline run).
