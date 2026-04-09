## Temporal Design: gold-occupation-profiles-bls-ooh
**Date:** 2026-04-07
**Agent:** @temporal-modeler
**Domain:** U.S. Labor Market -- Occupation-Level Employment Projections (BLS OOH)
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Zone:** Gold (Consumable)

### Assessment Summary

No bitemporal modeling required. The `consumable.occupation_profiles` table is a single-snapshot projection of the BLS 2024-2034 Employment Projections data, fully replaced on each refresh cycle. The existing `source_load_date` and `promoted_at` metadata columns, combined with Iceberg snapshot-based transaction time, provide sufficient temporal traceability. The spec's decision to mark @temporal-modeler as SKIP is correct. No schema changes are needed.

### 1. Temporal Characteristics of the Data

This Gold table inherits the temporal characteristics assessed at the Silver layer (see `governance/audit-trail/silver-base-bls-ooh-temporal-assessment.md`), with additional Gold-specific considerations:

**Point-in-time projections, not time-series.** All 832 rows share the same implicit validity window: the BLS 2024-2034 projection cycle. The projection horizon is encoded semantically in column names (`employment_current` = base year 2024, `employment_projected` = target year 2034) rather than as explicit date fields. Adding `valid_from`/`valid_to` columns would be inappropriate at the Gold layer for the same reasons identified at Silver: the validity period is uniform across all rows, carries zero discriminating information, and would fabricate metadata not present in the source.

**Derived fields inherit the source temporal characteristic.** All Gold-specific derivations (grw_score, market_score, wage_percentile_overall, wage_percentile_education_tier, wage_tier, confidence_tier, data_completeness) are deterministic, stateless transformations of the Silver snapshot. They do not introduce any new temporal dimension. The same Silver input always produces the same Gold output. The derivations are point-in-time computations (percentile ranks, piecewise linear mappings, bucket assignments) that are meaningful only within the context of a single projection cycle.

**Wage data temporal nuance carries forward.** The `median_annual_wage` field reflects the most recent BLS Occupational Employment and Wage Statistics survey, which may lag the projection base year by 1-2 years. The Gold derivations that depend on wage data (wage_percentile_overall, wage_percentile_education_tier, wage_tier) inherit this lag. This is a provenance concern documented in the data contract, not a temporal modeling concern.

### 2. Refresh Strategy

Full table replace is the correct strategy for this Gold product. Rationale:

| Consideration | Assessment |
|---------------|------------|
| BLS publication model | Each projection cycle replaces all prior data. No row-level amendments. |
| Grain stability | Grain is `soc_code` (one row per occupation). 832 rows. No append logic needed. |
| Derived field determinism | All Gold derivations are deterministic from Silver input. Re-running the transformer on the same Silver data produces identical output. |
| Idempotency | The Brightsmith `promote()` pattern handles idempotent writes. Re-promotion of unchanged data produces no new Iceberg snapshot. |
| Table size | 832 rows. Full replace is computationally trivial. No benefit from incremental updates. |

The Iceberg snapshot strategy for this Gold table:

| Event | Snapshot Action | Notes |
|-------|----------------|-------|
| Initial Gold promotion | New snapshot | Baseline state of 832 occupation profiles |
| Pipeline re-run (same Silver data) | No new snapshot | Idempotent promote pattern produces 0 new rows |
| Silver data correction (rare) | New snapshot | Re-promotion after Silver correction. Previous Gold version preserved via Iceberg time travel. |
| New projection cycle (biennial) | New snapshot (full replace) | Entire Gold table replaced. Prior version recoverable via Iceberg time travel. |
| Score formula change (e.g., GRW breakpoints adjusted) | New snapshot | Same Silver data, different Gold derivations. Previous scoring preserved via Iceberg time travel. |

### 3. source_load_date and promoted_at -- Temporal Context Provided

These two metadata columns provide the complete temporal audit trail needed for this Gold product:

**`source_load_date` (DATE, NOT NULL)** -- Carried from `base.bls_ooh`. Records when the BLS source data entered the Raw zone. All 832 rows share the same value in a given load. This field answers: "When was this BLS data acquired?" It provides source provenance and enables staleness detection (DQ freshness rule: source_load_date within 400 days of current date).

**`promoted_at` (TIMESTAMP, NOT NULL)** -- Generated at Gold promotion time. Records when each row was written to `consumable.occupation_profiles`. This field answers: "When was this Gold product last built?" It provides pipeline recency context for downstream consumers (Gemma agent, FutureProof frontend) and enables detection of stale Gold products.

**Together with Iceberg snapshots,** these two fields establish a three-layer temporal trace:
1. `source_load_date` -- when the data was acquired from BLS (source provenance)
2. `promoted_at` -- when the Gold product was built (pipeline recency)
3. Iceberg snapshot timestamp -- when the data was written to the Iceberg table (transaction time, automatic)

No additional temporal columns are needed. A `projection_cycle` column is not warranted for a single-cycle dataset (see Section 5 for multi-cycle discussion).

### 4. Would Bitemporal Modeling Be Needed in Future?

Not for the foreseeable use cases. The analysis below considers scenarios that might trigger bitemporal requirements:

**Scenario A: BLS publishes the next projection cycle (expected ~2026, covering 2026-2036).**
This is the most likely trigger for temporal design evolution. However, it does not require bitemporal modeling. It requires a decision between full table replace (Option A) and adding a `projection_cycle` dimension (Option B), as documented in the Silver temporal assessment. The Gold table should follow whatever strategy Silver adopts.

If Silver adopts Option B (add `projection_cycle`), the Gold table would also gain a `projection_cycle` column, and the grain would change from `soc_code` to `(soc_code, projection_cycle)`. All derived fields (grw_score, market_score, wage percentiles) would be computed within each projection cycle independently. This is a schema evolution, not bitemporal modeling.

**Scenario B: BLS issues a mid-cycle correction.**
Very rare per the domain context. Handled entirely by Iceberg snapshots: the pipeline re-runs, creates a new snapshot, and the prior version is recoverable via time travel. No row-level supersession metadata is needed because corrections are full-table replacements.

**Scenario C: GRW score formula is revised (e.g., breakpoints adjusted after user feedback).**
This is a Gold-layer change, not a source data change. The pipeline would re-run on the same Silver data with new derivation logic, producing a new Iceberg snapshot. The prior scoring is recoverable via time travel. No bitemporal columns needed.

**Scenario D: Cross-source temporal alignment (BLS + College Scorecard + O*NET).**
BLS projections are biennial; College Scorecard is annual; O*NET updates vary. These temporal vintages do not align precisely, but all use full-replace models. The cross-source Gold product (the CIP-SOC crosswalk join) should document temporal vintage alignment in its data contract (e.g., "combines 2024-2034 BLS projections with 2022-2024 College Scorecard cohort data"). This is a provenance documentation concern, not a bitemporal modeling concern.

**Conclusion:** Full bitemporal modeling (explicit `valid_from`/`valid_to` columns combined with Iceberg transaction time) is not warranted for this data source at any foreseeable stage. The projection cycles do not overlap, there is no row-level amendment mechanism, and the `projection_cycle` dimension (if adopted later) achieves the same queryability with less complexity.

### 5. Recommended Approach for the Next Projection Cycle Update

When BLS publishes the next projection cycle (expected ~2026), the Gold table should follow the Silver layer's strategy. The recommendation from the Silver temporal assessment applies directly:

**For MVP (current state): Stay with full table replace (Option A).**
- Simplest implementation. Matches the BLS publication model.
- Prior cycle recoverable via Iceberg time travel.
- The physical model specifies `write.metadata.previous-versions-max = 10`, which retains 10 snapshots -- sufficient to cover several projection cycles via time travel.

**When the second cycle arrives: Evaluate Option B (add `projection_cycle` dimension).**
- Add a `projection_cycle` VARCHAR column (e.g., "2024-2034") to both Silver and Gold schemas via Iceberg schema evolution.
- Gold grain changes from `soc_code` to `(soc_code, projection_cycle)`.
- All derived fields (grw_score, market_score, wage percentiles) must be recomputed within each cycle independently, since percentile ranks are relative to the population in that cycle.
- Enables trend analysis: "How did the GRW score for Software Developers change between the 2024-2034 and 2026-2036 projection cycles?"
- DQ rules would need updating for the new grain and for multi-cycle row count expectations.

**Gold-specific considerations for multi-cycle support:**
- `wage_percentile_overall` and `wage_percentile_education_tier` must be computed per cycle, not across cycles. Mixing cycles in a single PERCENT_RANK window would be meaningless.
- `market_score` depends on `openings_score` (PERCENT_RANK of `openings_annual_avg`), which also must be computed per cycle.
- `confidence_tier` logic is cycle-independent (based on flags and wage availability), so it would not change.
- The `backs_stats` and `backs_bosses` static fields are cycle-independent.
- A new derived field (e.g., `grw_score_delta`) could compare the same occupation's score across cycles, but this is a future product decision.

**SOC 2028 taxonomy revision:** Anticipated to coincide with a future projection cycle. When adopted, SOC codes may be reassigned, split, merged, or renumbered. This is an entity resolution problem, not a temporal modeling problem. The `broad_occupation_flag` hardcoded list and SOC major group lookup will need review. BLS publishes a crosswalk between old and new SOC codes that would need to be ingested as a reference dimension.

### Schema Changes

None required. The current 31-column physical model is appropriate for the single-snapshot use case.

### Future Triggers for Re-Assessment

1. Decision to retain multiple projection cycles side-by-side (triggers Option B -- add `projection_cycle` column).
2. SOC 2028 adoption requiring temporal crosswalk between old and new code versions.
3. Requirement for projection accuracy analysis (comparing prior projections to observed actuals).
4. Change to GRW score or market score formulas that creates a need to track scoring methodology versions.
5. Cross-source Gold product (CIP-SOC join) temporal vintage alignment requirements.

### Artifacts Produced

- This audit trail entry: `governance/audit-trail/gold-occupation-profiles-bls-ooh-temporal-assessment.md`

### Trade-offs Considered

- **Adding `projection_cycle` now vs. deferring:** Deferred. A column with the same value ("2024-2034") for all 832 rows provides no discriminating information. Better to add it when the second cycle arrives and the column becomes meaningful. Adding it later via Iceberg schema evolution is non-breaking.
- **Adding `data_vintage` or `scoring_version` columns for Gold-specific versioning:** Deferred. The `promoted_at` timestamp combined with Iceberg time travel is sufficient to identify which version of the Gold derivations was active at any point. A separate versioning scheme would add complexity without clear benefit in the MVP.
- **Snapshot retention policy:** The physical model specifies 10 snapshots retained. For a biennial projection cycle, this covers approximately 20 years of history if the pipeline runs once per cycle, or fewer if there are mid-cycle re-promotions. This is adequate. If the team needs longer retention, increase `write.metadata.previous-versions-max`.
- **Per-cycle vs. cross-cycle percentile ranks:** When multi-cycle support is added, percentile ranks must be computed per cycle (not pooled across cycles). Pooling would distort rankings as wage and employment distributions shift between cycles. This is a future implementation detail, not a current schema concern.
