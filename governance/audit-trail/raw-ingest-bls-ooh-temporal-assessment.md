## Audit Trail: Temporal Assessment for raw-ingest-bls-ooh
**Timestamp:** 2026-04-07
**Agent:** @temporal-modeler
**Spec:** docs/specs/raw-ingest-bls-ooh.md
**Zone:** Raw (Bronze)

### Action
Assessed temporal modeling needs for the `raw.bls_ooh` Bronze table.

### Decision
No bitemporal modeling required. Snapshot replacement model with Iceberg time travel is sufficient for the Raw zone. No schema changes needed.

### Inputs Reviewed
- Raw spec: `docs/specs/raw-ingest-bls-ooh.md`
- Domain context: `governance/domain-context.md` (BLS OOH Temporal Patterns, Amendment/Correction Patterns sections)
- Gold temporal assessment: `governance/audit-trail/gold-career-outcomes-college-scorecard-temporal-assessment.md` (for precedent)

### Key Rationale

1. **Snapshot replacement model** -- BLS Employment Projections are released biennially as a complete dataset replacement. There are no incremental updates, deltas, or amendment records. Each release covers a full 10-year projection window (currently 2023-2033) and supersedes the prior cycle entirely.

2. **No valid time range in raw data** -- The source data does not contain explicit validity periods. The projection cycle (2023-2033) is implicit in the column headers and applies uniformly to all ~832 rows. Modeling valid_from/valid_to at the raw zone would be fabricating metadata not present in the source.

3. **Transaction time via Iceberg snapshots** -- Each ingest run creates a new Iceberg snapshot. If BLS releases a corrected file mid-cycle (documented as "very rare" in domain context), the correction creates a new snapshot and the prior version is recoverable via Iceberg time travel. This is sufficient for the Raw zone.

4. **Dedup on soc_code** -- The spec defines a single-column dedup grain. Combined with full table replacement, this means each snapshot contains exactly one record per occupation. No temporal versioning is needed within a snapshot.

5. **Domain context confirms simplicity** -- The domain context Amendment/Correction Patterns section states: "Each new projection cycle replaces all prior data. There is no amendment mechanism -- the entire dataset is recomputed."

### Recommendations for Silver/Gold Zones

While the Raw zone requires no temporal modeling, downstream zones should consider:

- **Projection cycle dimension**: If multiple projection cycles are retained in Silver (e.g., 2023-2033 and future 2025-2035), add a `projection_cycle` column (e.g., "2023-2033") to distinguish vintages. This is NOT needed for MVP per the user-confirmed full-replace strategy.
- **Wage data temporal lag**: Median wage data reflects the most recent BLS OEWS survey, which may lag the projection base year by 1-2 years. Silver/Gold consumers should document this provenance gap rather than model it temporally.
- **Cross-source temporal alignment**: When joining BLS projections (biennial, 10-year horizon) with College Scorecard data (annual snapshot) in Silver, temporal vintage alignment should be documented but does not require bitemporal schema -- both sources use full-replace models.

### Future Triggers for Re-Assessment
- Multi-cycle retention requirement (retaining 2023-2033 alongside 2025-2035)
- SOC 2028 migration requiring crosswalk between old and new SOC codes with temporal validity
- User request for projection accuracy analysis (comparing prior projections to actuals)

### Artifacts Produced
- This audit trail entry

### Trade-offs Considered
- Adding `projection_cycle` column to raw schema now vs. deferring: chose to defer. The raw zone should mirror the source faithfully, and the projection cycle is not a field in the source XLSX. Adding it is a Silver zone concern if multi-cycle retention is needed.
- Modeling base year (2023) and target year (2033) as explicit date columns vs. relying on column semantics: chose column semantics. The column names `employment_current` and `employment_projected` already encode this meaning, and hardcoding dates would break on the next projection cycle without providing queryable benefit.
