## Temporal Assessment: silver-base-onet
**Date:** 2026-04-08
**Agent:** @temporal-modeler
**Domain:** Education / Career Guidance (O*NET occupation data)
**Decision:** SKIP full bitemporal modeling — single-snapshot pattern confirmed appropriate

### Assessment

O*NET v30.2 is a **release-based snapshot dataset**. All four Silver tables (base.onet_occupations, base.onet_activity_profiles, base.onet_context_profiles, base.onet_career_transitions) represent a single point-in-time view of O*NET's rolling survey data. Updates arrive as full table replacements when a new O*NET release publishes (approximately annual).

**Why bitemporal modeling is not needed:**

1. **No valid time dimension to model.** O*NET survey dates (ranging from 2004 to 2025) are informational metadata about when individual data points were collected, not a temporal dimension that defines fact validity periods. All data in a given O*NET release is considered "current" regardless of individual survey dates.

2. **No amendment/correction mechanism.** O*NET does not issue mid-cycle corrections. Each numbered release (e.g., 30.2) is a complete, self-contained database that replaces the prior release entirely.

3. **No overlapping validity periods.** There is no scenario where two versions of an occupation's activity profile are simultaneously valid for different time ranges.

4. **Full table replace on update.** When O*NET 31.0 (or similar) is released, the pipeline will ingest it as a complete replacement. The prior version can be preserved via Iceberg snapshot if historical comparison is desired, but this is infrastructure-level time travel, not schema-level bitemporality.

### Temporal Tracking Fields Present

All four Silver tables include basic temporal tracking fields, which is sufficient:

| Field | Purpose |
|-------|---------|
| `source_load_date` | Date the raw O*NET data was loaded into Bronze — tracks which O*NET release this data came from |
| `ingested_at` | Timestamp when the Silver record was created — operational metadata |

These fields provide adequate provenance without requiring valid_from/valid_to columns or explicit snapshot versioning in the schema.

### Future Consideration

If FutureProof later needs to track changes across O*NET releases (e.g., "how did the importance of 'Getting Information' change for Software Developers between O*NET 30.2 and 31.0?"), the recommended approach is:

- Add a `release_version` column to each Silver table
- Retain prior release data alongside current release data
- Use release_version as a partition/filter dimension

This would be a schema change requiring a new spec. It is not needed for MVP.

### Recommendation

**Proceed without bitemporal modeling.** The source_load_date and ingested_at fields already present in the spec schemas provide sufficient temporal context for single-snapshot data.
