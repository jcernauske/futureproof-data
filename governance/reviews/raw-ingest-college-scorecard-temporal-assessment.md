## Temporal Assessment: raw-ingest-college-scorecard
**Date:** 2026-04-05
**Agent:** @temporal-modeler
**Domain:** Higher Education Outcomes (College Scorecard)
**Zone:** Bronze (raw ingest)

### Finding: No Temporal Modeling Required

This dataset is a single point-in-time snapshot of the Department of Education's "Most Recent Cohorts" College Scorecard data. All 69,947 rows share the same ingested_at timestamp (2026-04-06). There is no time-series dimension within the dataset.

**Bitemporal modeling is not applicable at the Bronze zone.** The data has no valid time range to model -- it represents a single release of aggregate institutional/program outcomes.

### Earnings Windows Are Cross-Sectional, Not Longitudinal

The `earn_mdn_hi_1yr` and `earn_mdn_hi_2yr` columns come from different cohort measurement windows. They are parallel measurements of different graduate cohorts, not the same individuals tracked over time. The 44.2% incidence of 2yr < 1yr values is expected behavior, not an anomaly. These columns must NOT be modeled as a time series.

### Silver Zone Considerations

If FutureProof ingests multiple annual Scorecard releases in the future, the Silver zone will need:

- **Period disambiguation** -- a release_year or data_vintage column to distinguish which annual release each row came from
- **Version tracking** -- use `load_date` (or an equivalent ingestion timestamp) to identify the refresh cycle
- **SCD Type 2 consideration** -- track institution/program-level changes across releases at the (unitid, cipcode) grain, if year-over-year analysis becomes a requirement

Per the domain context, the current recommendation is full table replace for MVP, with SCD Type 2 deferred to a future iteration.

### Recommendation

Treat as a snapshot. No temporal schema changes required for Bronze. If annual refreshes are implemented, use `load_date` for version tracking and revisit temporal modeling at the Silver zone boundary.

### Snapshot Strategy (Current State)

| Event | Action | Notes |
|-------|--------|-------|
| Initial load (current) | Single Iceberg snapshot | Baseline state, no prior versions |
| Future annual refresh | New snapshot, full table replace | Previous version recoverable via Iceberg time travel |
| Mid-cycle correction | New snapshot | Rare; no detection mechanism currently exists |
