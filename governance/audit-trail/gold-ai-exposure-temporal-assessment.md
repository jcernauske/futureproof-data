## Temporal Design: gold-ai-exposure
**Date:** 2026-04-09
**Agent:** @data-analyst
**Domain:** Education / Career Guidance (AI Exposure sub-domain)
**Spec:** gold-ai-exposure
**Zone:** Gold (Consumable)
**Decision:** Static snapshot. No temporal modeling required.

### Assessment Summary

No bitemporal modeling required. The `consumable.ai_exposure` table is a static, single-snapshot derivation of Karpathy's AI exposure scores for 389 BLS-matched occupations. The table is fully replaced on each pipeline run via the Brightsmith idempotent promote pattern. The `promoted_at` timestamp combined with Iceberg snapshot-based transaction time provides sufficient temporal traceability.

### 1. Temporal Characteristics of the Data

**Static scoring, not time-series.** The exposure scores were generated as a one-time LLM assessment by Andrej Karpathy. There is no temporal dimension in the source data -- no date of assessment, no validity period, no version number. All 389 rows share the same implicit temporal context: "Karpathy's 2024 AI exposure assessment."

**Derived fields are deterministic and stateless.** Both Gold-specific derivations (stat_res, boss_ai_score) are pure functions of exposure_score:
- `stat_res = MIN(11 - exposure_score, 10)`
- `boss_ai_score = MAX(exposure_score, 1)`

These computations introduce no new temporal dimension. The same input always produces the same output.

### 2. Refresh Strategy

**Event-driven full replace.** The table is refreshed only when:

| Event | Action | Notes |
|-------|--------|-------|
| Initial Gold promotion | New Iceberg snapshot | Baseline 389 rows |
| Pipeline re-run (same Silver data) | No new snapshot | Idempotent promote skips unchanged rows |
| Silver data correction | New snapshot (full replace) | Prior version preserved via Iceberg time travel |
| New AI exposure assessment (hypothetical) | New snapshot (full replace) | Would require new Raw ingest + Silver processing first |

There is no incremental update pattern. The table is small (389 rows) and fully replaceable at negligible cost.

### 3. Temporal Metadata Provided

**`promoted_at` (TIMESTAMP, NOT NULL)** -- Generated at Gold promotion time. Records when each row was written to `consumable.ai_exposure`. Combined with Iceberg snapshots, this establishes a two-layer temporal trace:

1. `promoted_at` -- when the Gold product was built (pipeline recency)
2. Iceberg snapshot timestamp -- when the data was written (transaction time, automatic)

No `source_load_date` is carried to Gold (it exists at Silver). This is acceptable because all 389 rows originate from the same single load event, and the promoted_at timestamp provides sufficient recency context for downstream consumers.

### 4. Why Bitemporal Modeling Is Not Needed

| Scenario | Assessment |
|----------|-----------|
| Source data versioning | Karpathy's scores are a single static dataset. No versioned releases. |
| Mid-cycle corrections | If scores are corrected, the pipeline re-runs and Iceberg time travel preserves the prior version. No row-level supersession metadata needed. |
| Multiple assessment vintages | Hypothetical. If a second AI exposure assessment is produced (different model, different year), the decision would be: replace or add a `vintage` column. For a single-source 389-row table, full replace is appropriate. Revisit if this scenario materializes. |
| Cross-source temporal alignment | ai_exposure joins to occupation_profiles via soc_code. Both are static snapshots with no temporal alignment concerns at the current single-vintage stage. |

### 5. Future Triggers for Re-Assessment

1. A second AI exposure assessment from a different source or model version (would require a `vintage` or `assessment_date` column).
2. Requirement to track exposure score changes over time (would require temporal grain expansion).
3. SOC 2028 taxonomy revision requiring crosswalk between old and new SOC codes.

### Schema Changes

None required. The current 9-column physical model is appropriate for the static snapshot use case.
