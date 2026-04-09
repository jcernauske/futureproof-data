## Temporal Assessment: silver-base-college-scorecard
**Date:** 2026-04-06
**Agent:** @temporal-modeler
**Domain:** Higher Education Outcomes (College Scorecard)
**Zone:** Silver (base)
**Spec:** docs/specs/silver-base-college-scorecard.md

### Finding: Snapshot-Only Approach Is Appropriate

Bitemporal modeling (explicit valid time columns plus Iceberg transaction time) is **not required** for this spec. The snapshot-only approach is the correct design for the following reasons.

### Rationale

**1. No valid time dimension exists in the source data.**

The College Scorecard "Most Recent Cohorts" file is a single point-in-time release. All 69,947 rows describe the same reporting vintage. There is no `valid_from` / `valid_to` range to model -- the entire dataset is simultaneously valid as of its release date. The `source_load_date` column in the Silver schema adequately captures the data vintage.

**2. Earnings windows are cross-sectional, not temporal.**

The `earnings_1yr_median` and `earnings_2yr_median` fields come from different cohort measurement windows (different groups of graduates measured at different intervals). They are parallel cross-sectional observations, not a time series of the same individuals. Modeling them with valid time ranges would be semantically incorrect and would mislead downstream consumers into treating them as longitudinal data.

**3. Data refresh strategy is full table replace.**

Per domain context (Question 6) and user confirmation, the MVP refresh strategy is full table replace. When a new annual Scorecard release arrives, the entire `base.college_scorecard` table is overwritten in a new Iceberg snapshot. The previous version is preserved automatically via Iceberg time travel. This is the simplest correct approach and does not require SCD tracking or amendment metadata.

**4. No amendment/correction mechanism exists in source.**

The Department of Education does not publish correction records with supersession metadata. Mid-cycle corrections (rare) are published as a replacement file, indistinguishable from a regular release. There is no correction chain to track, so `is_correction` / `corrects_record` columns would be structurally empty.

### Transaction Time Strategy (Iceberg Snapshots)

Iceberg snapshot-based transaction time is sufficient for all foreseeable needs.

| Event | Snapshot Action | Recovery |
|-------|----------------|----------|
| Initial Silver load | New snapshot | Baseline state |
| Annual data refresh (full replace) | New snapshot | Previous year recoverable via `SELECT * FROM base.college_scorecard AT (TIMESTAMP => '<pre-refresh>')` |
| Mid-cycle DOE correction | New snapshot (same as refresh) | Pre-correction state recoverable via Iceberg time travel |
| Pipeline re-run (idempotent promote) | No new snapshot (0 new rows) | No state change; idempotent by design |

### Point-in-Time Query Support

Even without explicit valid time columns, Iceberg time travel supports the key temporal query:

```sql
-- "What data did we have before the 2027 annual refresh?"
SELECT *
FROM base.college_scorecard
AT (TIMESTAMP => '2027-03-01T00:00:00')
WHERE unitid = 123456;
```

The `source_load_date` column serves as an implicit data vintage marker, enabling consumers to understand which annual release the data represents without requiring full bitemporal machinery.

### Schema Impact

**No temporal columns added.** The spec schema is correct as-is:

- `source_load_date` (date) -- data vintage / release provenance
- `ingested_at` (timestamp) -- Silver zone processing timestamp
- Iceberg snapshots -- transaction time (automatic)

No `valid_from`, `valid_to`, `is_correction`, `corrects_record`, or `supersedes` columns are needed.

### Future Considerations

If the project evolves to require year-over-year program tracking (e.g., "how did median earnings for CS programs change between the 2025 and 2026 releases?"), the following changes would be needed:

1. Shift from full table replace to append-with-vintage (add a `release_year` column)
2. Consider SCD Type 2 on the (unitid, cipcode, credlev) grain to track attribute changes
3. At that point, revisit bitemporal modeling with `valid_from` / `valid_to` representing the reporting period

This is explicitly deferred per domain context and user confirmation. The current snapshot-only design does not preclude this evolution.

### Consistency with Bronze Assessment

This assessment is consistent with the Bronze zone temporal assessment (`governance/reviews/raw-ingest-college-scorecard-temporal-assessment.md`), which also concluded that no temporal modeling is required and recommended snapshot-only treatment with Iceberg time travel for version recovery.

### Decision Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Valid time columns | Not needed | No valid time range in source; single-vintage snapshot |
| Correction metadata | Not needed | DOE does not publish corrections with supersession info |
| SCD tracking | Deferred | Full table replace for MVP; user confirmed |
| Iceberg time travel | Sufficient | Covers version recovery for refreshes and corrections |
| Earnings as time series | Rejected | Cross-sectional cohort windows, not longitudinal |
