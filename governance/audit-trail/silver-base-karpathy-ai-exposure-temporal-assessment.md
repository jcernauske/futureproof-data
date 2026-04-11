## Temporal Design: silver-base-karpathy-ai-exposure
**Date:** 2026-04-09
**Agent:** @temporal-modeler
**Domain:** AI Exposure Scoring -- LLM-Generated Occupation Risk Estimates (Karpathy)
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Zone:** Silver (Base)

### Assessment Summary

No bitemporal modeling required. This is a static reference dataset -- a single LLM scoring run producing one exposure score per occupation. The existing `source_load_date` and `ingested_at` metadata columns, combined with Iceberg snapshot-based transaction time, provide sufficient temporal traceability. No schema changes are needed.

### Valid Time Design

**Current state:** There is no explicit valid time modeled in the schema, and none is needed.

The Karpathy AI Exposure dataset is a point-in-time snapshot of LLM-generated scores. All 419 Silver rows (342 Bronze rows expanded via broad SOC code expansion and title matching) share the same implicit validity window: the moment the LLM scored BLS occupation descriptions. There is no temporal dimension within the data itself -- no time series, no reporting periods, no validity ranges.

Adding `valid_from`/`valid_to` columns would be inappropriate because:
1. The dataset has no inherent temporal grain. Every row was scored in the same LLM run.
2. There is no defined expiration for these scores. They remain current until replaced by a new scoring run.
3. The source data contains no date fields beyond ingestion metadata. Adding validity dates would fabricate information.

### Transaction Time Strategy

Transaction time is handled automatically by Iceberg snapshots. The strategy is straightforward:

| Event | Snapshot Action | Notes |
|-------|----------------|-------|
| Initial Silver load | New snapshot | Baseline state of ~419 occupation-level exposure scores |
| Pipeline re-run (same source data) | No new snapshot | Idempotent promote pattern produces 0 new rows |
| Karpathy updates scores on GitHub | New snapshot (full replace) | Entire table replaced; prior version recoverable via Iceberg time travel |
| Re-scoring with Gemma (post-hackathon) | New snapshot (full replace) | New model replaces all scores; prior Karpathy scores preserved in snapshot history |

The `ingested_at` timestamp records when each row was written to Silver. The `source_load_date` records when the source data entered the Raw zone. Together with Iceberg snapshots, these provide a complete transaction time audit trail without explicit bitemporal columns.

### Correction/Amendment Handling

The domain context confirms there is no amendment pattern for this data. Per the domain context: "Scores do not get corrected or amended -- the entire dataset is replaced on refresh."

This is the simplest possible correction model: full-table replacement. When it occurs:
1. New source files are fetched and ingested into `bronze.karpathy_ai_exposure` (new Iceberg snapshot in Bronze).
2. Silver transformer re-runs, producing a new Iceberg snapshot in `base.karpathy_ai_exposure`.
3. The prior Silver snapshot is preserved and recoverable via Iceberg time travel.
4. No supersession metadata is needed because there are no row-level amendments.

### Point-in-Time Query Support

Iceberg time travel supports "what did we know on date X?" queries without any schema changes:

```sql
-- What was the AI exposure score for Financial Analysts before the re-scoring?
SELECT soc_code, occupation_title, exposure_score, rationale
FROM base.karpathy_ai_exposure
AT (TIMESTAMP => '2026-04-09T00:00:00')
WHERE soc_code = '13-2051';

-- Compare Karpathy scores vs. future Gemma scores
-- Query the pre-Gemma snapshot and the post-Gemma snapshot separately
```

No additional columns or structures are needed to enable these queries.

### Schema Changes

None required. The current 11-column schema is appropriate for the static reference use case.

### Refresh Strategy

The data contract specifies event-driven refresh with no fixed cadence. Two trigger events are defined:

1. **Karpathy source update:** If the `karpathy/jobs` GitHub repository publishes new scores, re-ingest and full-replace.
2. **Gemma re-scoring (post-hackathon):** When the project re-generates AI exposure scores using Gemma with O*NET task-level data, the entire table is replaced. The pipeline architecture (Bronze, Silver, Gold) stays identical -- only the source data changes.

In both cases, the refresh is a full-table replacement. No merge, upsert, or slowly-changing-dimension logic is needed.

### Cross-Source Temporal Alignment

When `base.karpathy_ai_exposure` is joined downstream with `base.bls_ooh` and `consumable.program_career_paths`:
- Karpathy scores are static (single LLM run, no temporal vintage).
- BLS OOH projections are biennial (2024-2034 cycle).
- College Scorecard is annual (most recent cohorts, reflecting outcomes ~2-4 years prior).
- These temporal vintages do not need alignment because the AI exposure score is a structural assessment of occupation characteristics, not a time-sensitive measurement.
- Temporal provenance should be documented in the Gold zone data contract (e.g., "AI exposure scores are LLM-generated estimates from Karpathy's 2025 scoring run; they do not have a defined temporal validity window").

### Future Triggers for Re-Assessment

1. Introduction of multiple scoring models (e.g., retaining both Karpathy and Gemma scores side-by-side). This would require a `scoring_model` or `scoring_version` dimension column and a grain change from `soc_code` to `(soc_code, scoring_version)`.
2. Addition of time-series AI exposure data (e.g., quarterly re-scoring to track exposure trends over time). This would introduce genuine valid time and warrant bitemporal modeling.
3. Requirement to track score provenance across multiple LLM runs with different rubrics or models.

### Trade-offs Considered

- **Adding a scoring_version column now vs. deferring:** Deferred. A single-value column ("karpathy-gemini-flash-2025") across all 419 rows provides no discriminating information. Better to add it when a second scoring model arrives and the column becomes meaningful.
- **Explicit valid_from/valid_to vs. no valid time:** Chose no valid time. These scores have no defined expiration or validity window. Adding dates would fabricate temporal semantics that do not exist in the source data.
- **SCD Type 2 vs. full replace:** Chose full replace. The domain context explicitly states event-driven full replacement with no amendment pattern. SCD Type 2 would add complexity with no benefit for a dataset that is wholly replaced on each refresh.

### Artifacts Produced

- This audit trail entry: `governance/audit-trail/silver-base-karpathy-ai-exposure-temporal-assessment.md`
