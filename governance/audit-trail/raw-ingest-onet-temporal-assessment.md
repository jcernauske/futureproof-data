## Audit Trail: Temporal Assessment for raw-ingest-onet
**Timestamp:** 2026-04-07
**Agent:** @temporal-modeler
**Spec:** docs/specs/raw-ingest-onet.md
**Zone:** Raw (Bronze)

### Action
Assessed temporal modeling needs for the 5 O*NET Bronze tables: `raw.onet_occupations`, `raw.onet_task_statements`, `raw.onet_work_activities`, `raw.onet_work_context`, `raw.onet_related_occupations`.

Note: Career Changers Matrix and Career Starters Matrix do not exist in O*NET 30.2 (confirmed by EDA and domain context). Those 2 of the original 7 planned tables are excluded from this assessment.

### Decision
No bitemporal modeling required. The existing `ingested_at` timestamp and `load_date` columns are sufficient for the Raw zone. No schema changes needed. Bitemporal modeling is deferred to Silver/Gold zones per Brightsmith convention.

### Inputs Reviewed
- Raw spec: `docs/specs/raw-ingest-onet.md`
- Domain context: `governance/domain-context.md` (O*NET Temporal Patterns, Amendment/Correction Patterns, Entity Lifecycle Events sections)
- EDA report: `governance/eda/raw-onet-eda.md` (confirmed actual table structure and data characteristics)
- Prior temporal assessments for precedent: `governance/audit-trail/raw-ingest-bls-ooh-temporal-assessment.md`, `governance/audit-trail/gold-career-outcomes-college-scorecard-temporal-assessment.md`

### Key Rationale

1. **Point-in-time release model** -- O*NET publishes numbered releases (currently 30.2) as complete database snapshots. Each release is a full replacement, not an incremental update. There are no deltas, amendment records, or correction notices. This is the same pattern as College Scorecard (annual full replace) and BLS OOH (biennial full replace).

2. **No valid time range in raw data** -- The `date` field present on Task Statements, Work Activities, and Work Context rows represents when O*NET collected the survey data for that specific data point, not a validity period. Dates span 21 years (12/2004 to 12/2025) within a single release because not all occupations are re-surveyed simultaneously. This field is informational metadata, not a temporal dimension. Modeling `valid_from`/`valid_to` in the Raw zone would fabricate metadata not present in the source.

3. **Transaction time via Iceberg snapshots** -- Each ingest run creates a new Iceberg snapshot. If O*NET publishes a corrected release (e.g., 30.2.1), the correction creates a new snapshot and the prior version is recoverable via Iceberg time travel. The existing `ingested_at` and `load_date` columns provide adequate provenance tracking within the Bronze zone.

4. **Grain-based dedup handles re-runs** -- Each table has a defined grain (e.g., `onet_soc_code x element_id x scale_id` for Work Activities). Combined with full table replacement on new releases, this means each snapshot contains exactly one record per grain key. No temporal versioning is needed within a snapshot.

5. **Domain context confirms simplicity** -- The domain context Amendment/Correction Patterns section states: "O*NET publishes ~2-4 releases per year. Each release may add new occupations, update survey data, or correct errors." and "When O*NET re-surveys an occupation, the new ratings replace the old ones. Old data is not preserved within the database." There is no source-level correction tracking to model.

6. **Survey date is NOT valid time** -- This is the most important design decision. The `date` field (e.g., "07/2019" for one occupation, "12/2025" for another) reflects data collection provenance. All data in O*NET 30.2 is considered "current" by O*NET regardless of when individual surveys were conducted. Treating the date as valid time would misrepresent the source semantics -- it would imply that a 2019-surveyed occupation's ratings expired or were superseded, which is not how O*NET works. The data is considered valid until replaced by a new release.

### Temporal Concerns Identified (All Deferred to Silver/Gold)

While no action is needed in the Raw zone, two temporal concerns are documented for downstream agents:

1. **Uneven data freshness across occupations** -- Within a single O*NET release, survey dates range from 2004 to 2025. Occupations with pre-2015 data may have less accurate ratings for rapidly evolving fields (e.g., tech occupations). The Gold zone should consider exposing the survey date as a freshness indicator so downstream consumers (including FutureProof's stat calculations) can assess data currency. This is a data quality/transparency concern, not a temporal modeling concern.

2. **Release version tracking for multi-release retention** -- If the pipeline ever retains multiple O*NET releases simultaneously (e.g., 30.1 alongside 30.2 for change detection), a `release_version` dimension would be needed in Silver. For MVP with single-release full replacement, this is not required. The O*NET release version (30.2) is captured implicitly via the source URL and Iceberg snapshot metadata.

3. **Cross-source temporal alignment** -- When O*NET data (quarterly releases) is joined with BLS OOH (biennial projections) and College Scorecard (annual snapshot) in Silver/Gold, temporal vintage alignment should be documented. All three sources use full-replace models with different cadences. This is a Gold zone documentation concern, not a Raw zone schema concern.

### Recommendations for Silver/Gold Zones

- **Silver**: If multiple O*NET releases are retained, add a `release_version` column (e.g., "30.2"). NOT needed for MVP.
- **Silver**: Preserve the raw `date` field as `survey_date` metadata for freshness tracking. Do not promote it to a valid-time column.
- **Gold**: Consider a `data_freshness_flag` (e.g., "current" for post-2019, "aging" for 2015-2019, "stale" for pre-2015) based on the survey date. This helps FutureProof users understand the reliability of occupation-level stats.
- **Gold**: Document the temporal vintage mismatch across the three sources (College Scorecard annual, BLS OOH biennial, O*NET quarterly) so downstream consumers understand that cross-source joins combine data from different measurement periods.

### Future Triggers for Re-Assessment
- Multi-release retention requirement (retaining 30.1 alongside 30.2 for change analysis)
- SOC 2028 migration requiring crosswalk between old and new SOC code versions with temporal validity
- User request for occupation-level change tracking ("how did this occupation's ratings change between releases?")
- Addition of time-series data sources (e.g., BLS OEWS wage time series) that would require genuine bitemporal modeling

### Artifacts Produced
- This audit trail entry

### Trade-offs Considered
- Adding `release_version` column to raw schema now vs. deferring: chose to defer. The raw zone should mirror the source faithfully. O*NET does not include a release version field in its data files -- the version is encoded in the ZIP file name and download URL. Adding it is a Silver zone enrichment if multi-release retention is needed.
- Modeling the `date` field as a valid-time dimension vs. treating as metadata: chose metadata. The domain context explicitly advises: "All data in a given O*NET release is considered current regardless of individual survey dates." Promoting `date` to valid time would misrepresent the source semantics.
- Adding a `snapshot_id` or `release_id` foreign key for cross-table temporal coherence: deferred. All 5 tables are ingested from the same ZIP archive in a single pipeline run, so they share the same `ingested_at` and `load_date`. Iceberg snapshot IDs already provide this coherence. A redundant column would add no value in the Raw zone.
