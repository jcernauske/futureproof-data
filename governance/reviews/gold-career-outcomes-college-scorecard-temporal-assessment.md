## Temporal Assessment: gold-career-outcomes-college-scorecard
**Date:** 2026-04-06
**Agent:** @temporal-modeler
**Domain:** Higher Education Outcomes (College Scorecard)
**Zone:** Gold (consumable)
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md

### Finding: No Bitemporal Modeling Required

The `consumable.career_outcomes` Gold table does not require bitemporal schema design. The snapshot-only approach with Iceberg time travel is the correct strategy. This assessment is consistent with the Silver zone temporal assessment and carries forward the same reasoning to the Gold zone.

### Rationale

**1. Source data is a single-vintage snapshot with no valid time range.**

The Gold table is derived entirely from `base.college_scorecard`, which itself is a single point-in-time release of the Department of Education's "Most Recent Cohorts" data. All 69,947 rows share the same data vintage. There is no valid time dimension to model -- no `valid_from` / `valid_to` is meaningful when the entire dataset describes one reporting period.

**2. All derived fields are deterministic transformations of snapshot data.**

The Gold spec adds percentile bands, debt-to-earnings ratios, confidence tiers, and ranking metrics. These are all computed from the Silver base via window functions and arithmetic. None of these derivations introduce a temporal dimension. Given the same Silver input, the Gold output is fully deterministic and reproducible.

**3. Data refresh strategy is full table replace.**

Per domain context (Question 6) and user-confirmed decisions in both the Silver and Gold specs, the refresh strategy is full table replace. When a new annual Scorecard release is ingested, the entire pipeline re-runs: Raw replaces, Silver replaces, Gold replaces. Iceberg time travel preserves all prior states automatically. No SCD tracking, amendment metadata, or supersession chains are needed.

**4. No amendment/correction mechanism propagates to Gold.**

The Department of Education does not publish correction records with supersession metadata. Mid-cycle corrections are indistinguishable from regular releases. Since the Silver zone already handles this via full table replace + Iceberg snapshots, the Gold zone inherits the same treatment with no additional temporal infrastructure.

**5. Earnings measurement windows remain cross-sectional.**

The Gold table carries forward `earnings_1yr_median` and `earnings_2yr_median` from Silver and computes derived metrics (growth rate, percentile bands) from them. These remain parallel cross-sectional measurements from different cohort windows, not a time series. The `earnings_growth_rate` field is clearly documented in the spec as reflecting cohort differences, not individual longitudinal tracking. No temporal modeling would improve the semantic accuracy of this representation.

### Transaction Time Strategy (Iceberg Snapshots)

Iceberg snapshot-based transaction time is sufficient for all Gold zone needs.

| Event | Snapshot Action | Recovery |
|-------|----------------|----------|
| Initial Gold promotion | New snapshot | Baseline consumable state |
| Annual pipeline re-run (new Scorecard release) | New snapshot (full replace) | Previous year recoverable via Iceberg time travel |
| Mid-cycle DOE correction (re-run pipeline) | New snapshot (full replace) | Pre-correction Gold state recoverable via time travel |
| Idempotent re-promotion (no source change) | No new snapshot (0 new rows) | No state change; idempotent by design |
| Derivation logic change (code update + re-run) | New snapshot | Previous derivation recoverable via time travel |

### Point-in-Time Query Support

Iceberg time travel supports the key temporal queries at the Gold level:

```sql
-- "What career outcomes data were we serving before the 2027 refresh?"
SELECT *
FROM consumable.career_outcomes
AT (TIMESTAMP => '2027-03-01T00:00:00')
WHERE cipcode = '11.07';

-- "Did the debt-to-earnings ratios change after we updated our derivation logic?"
SELECT record_id, debt_to_earnings_annual, confidence_tier
FROM consumable.career_outcomes
AT (TIMESTAMP => '<pre-code-change>')
WHERE unitid = 123456;
```

The `source_load_date` column (carried from Silver) serves as an implicit data vintage marker, and `promoted_at` records when the Gold promotion occurred. Together with Iceberg snapshots, these provide full auditability without explicit bitemporal columns.

### Schema Impact

**No temporal columns added.** The spec schema is correct as-is:

- `source_load_date` (date) -- data vintage / release provenance (from Silver)
- `promoted_at` (timestamp) -- Gold zone promotion timestamp
- Iceberg snapshots -- transaction time (automatic)

No `valid_from`, `valid_to`, `is_correction`, `corrects_record`, or `supersedes` columns are needed.

### Future Considerations

When the FutureProof pipeline evolves to support multi-year analysis, temporal modeling may become relevant at two levels:

**1. Year-over-year program outcome tracking.**
If multiple annual Scorecard releases are retained (rather than replaced), the Gold table would need a `release_year` or `data_vintage` column. Derived metrics like "earnings trend over 3 releases" would require explicit valid time modeling. This would likely be a new Gold spec rather than a modification to `consumable.career_outcomes`.

**2. Cross-source temporal alignment.**
When BLS Occupational Outlook Handbook and O*NET data are integrated (per the spec's Future Integration Notes), each source will have its own release cadence and measurement period. The CIP-to-SOC crosswalk join will need to align temporal vintages across sources. At that point, explicit valid time modeling may be necessary to ensure that Scorecard earnings data (2022-2024 cohorts) is correctly aligned with BLS projections (10-year outlook) and O*NET task assessments (periodic updates).

**3. Historical percentile band comparison.**
If users want to see how CIP-family percentile bands shift across releases (e.g., "Did CS earnings outpace Business earnings between 2025 and 2026 releases?"), the Gold table would need to retain multiple vintages. The current full-replace strategy would need to evolve.

All of these are explicitly deferred. The current snapshot-only design does not preclude this evolution.

### Consistency with Silver Assessment

This assessment is fully consistent with the Silver zone temporal assessment (`governance/reviews/silver-base-college-scorecard-temporal-assessment.md`). The Gold zone inherits the Silver zone's temporal characteristics and adds no new temporal dimensions. The same reasoning applies at both layers.

### Decision Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Valid time columns | Not needed | No valid time range; single-vintage snapshot data |
| Correction metadata | Not needed | DOE does not publish corrections with supersession info |
| SCD tracking | Deferred | Full table replace for MVP; user confirmed |
| Iceberg time travel | Sufficient | Covers version recovery for refreshes, corrections, and code changes |
| Bitemporal schema | Not needed | No valid time dimension exists; transaction time via Iceberg is sufficient |
| Derived field temporality | None | All derivations are deterministic functions of snapshot data |
| Cross-source temporal alignment | Deferred | Relevant when BLS/O*NET integration specs land |
