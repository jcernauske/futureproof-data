## Temporal Design: silver-base-bls-ooh
**Date:** 2026-04-07
**Agent:** @temporal-modeler
**Domain:** U.S. Labor Market -- Occupation-Level Employment Projections (BLS OOH)
**Spec:** docs/specs/silver-base-bls-ooh.md
**Zone:** Silver (Base)

### Assessment Summary

No bitemporal modeling required. The current schema is appropriate for a single-snapshot projection cycle. The existing `source_load_date` and `ingested_at` metadata columns, combined with Iceberg snapshot-based transaction time, provide sufficient temporal traceability. No schema changes are needed.

### Valid Time Design

**Current state:** There is no explicit valid time modeled in the schema, and none is needed.

The BLS 2024-2034 Employment Projections represent a single point-in-time projection cycle. All 832 rows share the same implicit validity window (the 2024-2034 projection horizon). The projection cycle is encoded in the semantics of the columns (`employment_current` = base year 2024, `employment_projected` = target year 2034) rather than as explicit date fields.

Adding `valid_from`/`valid_to` columns would be inappropriate because:
1. The validity period is uniform across all rows -- it carries zero discriminating information.
2. The source data does not contain these fields; adding them would fabricate metadata.
3. Hardcoding dates (e.g., valid_from=2024-01-01, valid_to=2034-12-31) would create a maintenance burden on the next projection cycle with no queryable benefit.

**Wage data temporal nuance:** The `median_annual_wage` field reflects the most recent BLS Occupational Employment and Wage Statistics survey, which may lag the projection base year by 1-2 years. This is a provenance characteristic, not a temporal modeling concern. It should be documented in the data contract and MCP metadata but does not warrant separate valid time columns.

### Transaction Time Strategy

Transaction time is handled automatically by Iceberg snapshots. The strategy is straightforward:

| Event | Snapshot Action | Notes |
|-------|----------------|-------|
| Initial Silver load | New snapshot | Baseline state of 832 occupation records |
| Pipeline re-run (same source data) | No new snapshot | Idempotent promote pattern produces 0 new rows |
| Mid-cycle BLS correction (rare) | New snapshot | Previous version preserved via Iceberg time travel |
| New projection cycle (biennial) | New snapshot (full replace) | Entire table replaced; prior cycle recoverable via Iceberg time travel |

The `ingested_at` timestamp records when each row was written to Silver. The `source_load_date` records when the source data entered the Raw zone. Together with Iceberg snapshots, these provide a complete transaction time audit trail without explicit bitemporal columns.

### Correction/Amendment Handling

The domain context confirms that BLS Employment Projections have no formal amendment mechanism. Per the domain context: "Each new projection cycle replaces all prior data. There is no amendment mechanism -- the entire dataset is recomputed."

Mid-cycle corrections are documented as "very rare." When they occur, the pipeline handles them via:
1. New source file is ingested into `raw.bls_ooh` (new Iceberg snapshot in Raw).
2. Silver transformer re-runs, producing a new Iceberg snapshot in `base.bls_ooh`.
3. The prior Silver snapshot is preserved and recoverable via Iceberg time travel.
4. No supersession metadata is needed because corrections are full-table replacements, not row-level amendments.

This is the same pattern established in the Raw zone temporal assessment.

### Point-in-Time Query Support

Iceberg time travel supports "what did we know on date X?" queries without any schema changes:

```sql
-- What was the projected growth for Software Developers as of 2026-04-07?
SELECT soc_code, occupation_title, employment_change_pct, growth_category
FROM base.bls_ooh
AT (TIMESTAMP => '2026-04-07T00:00:00')
WHERE soc_code = '15-1252';

-- Compare two Silver snapshots (e.g., before and after a correction)
-- Query snapshot 1 and snapshot 2 separately via Iceberg time travel
```

No additional columns or structures are needed to enable these queries.

### Schema Changes

None required. The current 25-column physical model is appropriate for the single-snapshot use case.

### Recommendation for Future Multi-Cycle Support

When BLS publishes the next projection cycle (expected ~2026, covering 2026-2036), the team will face a decision point. The three options and their trade-offs:

**Option A: Full table replace (current approach, recommended for MVP)**
- Each projection cycle overwrites the prior cycle entirely.
- Prior cycles are recoverable only via Iceberg time travel (snapshot history).
- Simplest implementation; matches the BLS publication model.
- Limitation: Iceberg snapshot retention is configuration-dependent. If snapshots are expired, prior cycles are lost.

**Option B: Add projection_cycle dimension (recommended if trend analysis is needed)**
- Add a `projection_cycle` VARCHAR column (e.g., "2024-2034") to the schema.
- Each new cycle is appended rather than replacing the prior cycle.
- Grain changes from `soc_code` to `(soc_code, projection_cycle)`.
- Enables trend analysis: "How did the outlook for Registered Nurses change between the 2024-2034 and 2026-2036 cycles?"
- Requires schema evolution (new column, new grain definition, updated DQ rules).
- This is the approach recommended in the domain context for future iterations.

**Option C: Full bitemporal modeling**
- Add `valid_from`/`valid_to` columns representing the projection horizon.
- Combined with Iceberg transaction time, enables full bitemporal queries.
- Overkill for this domain: projection cycles do not overlap, and there is no row-level amendment mechanism. The `projection_cycle` dimension (Option B) achieves the same queryability with less complexity.

**Recommendation:** Stay with Option A for now. When the next projection cycle approaches, implement Option B by adding a `projection_cycle` column via Iceberg schema evolution. Option C is not warranted for this data source.

### SOC Taxonomy Revision Consideration

The domain context notes that SOC 2028 is anticipated. When this occurs:
- SOC codes may be reassigned, split, merged, or renumbered.
- BLS publishes a crosswalk between old and new SOC codes.
- This is an entity resolution and concept normalization problem, not a temporal modeling problem.
- The `broad_occupation_flag` hardcoded list and the SOC major group lookup will need review when SOC 2028 is adopted.

This does not affect the temporal design but is flagged here because it will coincide with a future projection cycle change.

### Cross-Source Temporal Alignment

When `base.bls_ooh` is joined with `base.college_scorecard` via the CIP-SOC crosswalk:
- BLS projections are biennial (2024-2034 cycle).
- College Scorecard is annual (most recent cohorts, reflecting outcomes ~2-4 years prior to release).
- These temporal vintages do not align precisely, but both use full-replace models.
- Temporal alignment should be documented in the Gold zone data contract (e.g., "Career outcomes combine 2024-2034 BLS projections with College Scorecard cohort data from approximately 2022-2024").
- No bitemporal schema is needed to handle this misalignment -- it is a provenance documentation concern.

### Future Triggers for Re-Assessment

1. Decision to retain multiple projection cycles side-by-side (triggers Option B above).
2. SOC 2028 adoption requiring temporal crosswalk between old and new code versions.
3. Requirement for projection accuracy analysis (comparing prior projections to observed actuals).
4. Addition of BLS time-series data (e.g., Current Employment Statistics) that has genuine temporal grain.

### Artifacts Produced

- This audit trail entry: `governance/audit-trail/silver-base-bls-ooh-temporal-assessment.md`

### Trade-offs Considered

- **Adding projection_cycle now vs. deferring:** Deferred. Adding a column that would have the same value ("2024-2034") for all 832 rows provides no discriminating information and adds complexity to the grain definition and DQ rules. Better to add it when the second cycle arrives and the column becomes meaningful.
- **Explicit valid_from/valid_to vs. implicit projection semantics:** Chose implicit. The column names `employment_current` and `employment_projected` already encode the temporal meaning. Explicit date columns would be redundant and would need to be updated with each cycle.
- **Snapshot retention policy:** Not addressed here (infrastructure concern). Recommend configuring Iceberg snapshot retention to keep at least 3 years of history to preserve at least one prior projection cycle via time travel.
