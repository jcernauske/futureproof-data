## Audit Trail: Temporal Assessment for raw-ingest-karpathy-ai-exposure
**Timestamp:** 2026-04-09
**Agent:** @temporal-modeler
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Zone:** Bronze (Raw)

### Action
Assessed temporal modeling needs for the `bronze.karpathy_ai_exposure` table (342 rows).

### Decision
No bitemporal modeling required. This is a static reference table from a single LLM scoring run. Model as a snapshot table with full-replace semantics. No schema changes needed.

### Inputs Reviewed
- Spec: `docs/specs/raw-ingest-karpathy-ai-exposure.md`
- Domain context: `governance/domain-context.md` (Karpathy AI Exposure section, Temporal Strategy subsection)
- EDA report: `governance/eda/raw-karpathy-ai-exposure-eda.md` (referenced via domain context)
- Prior temporal assessments for pattern consistency: `governance/audit-trail/raw-ingest-bls-ooh-temporal-assessment.md`

### Key Rationale

1. **Static snapshot from single scoring run** -- The dataset is the output of a single LLM scoring pass (Gemini Flash via OpenRouter) over 342 BLS occupation descriptions. There is no temporal dimension in the data itself -- no time-series, no versioning, no effective dates. All 342 scores were produced in a single session and represent a point-in-time opinion, not a measurement that evolves.

2. **No valid time in the data** -- The only temporal fields in the Bronze schema are `ingested_at` (pipeline metadata timestamp) and `load_date` (pipeline metadata date). Neither represents a real-world validity period. The exposure scores do not have a "valid from" or "valid to" -- they are static assessments with no defined expiration.

3. **No amendment or correction pattern** -- The domain context explicitly states: "Scores do not get corrected or amended -- the entire dataset is replaced on refresh." There is no mechanism for partial updates, individual score corrections, or versioned amendments. This eliminates the need for correction tracking, supersession metadata, or merge/upsert logic.

4. **Event-driven full-replace refresh** -- The user confirmed the refresh strategy is event-driven (re-ingest when Karpathy updates or when the project re-scores with a different model post-hackathon), not scheduled. When a refresh occurs, it will be a full table replacement. Iceberg snapshot history will preserve the prior version automatically.

5. **Transaction time via Iceberg snapshots is sufficient** -- Each ingest creates a new Iceberg snapshot. If a future re-scoring replaces the data, the original Karpathy scores remain accessible via Iceberg time travel to the pre-replacement snapshot. This provides adequate auditability without explicit bitemporal schema design.

6. **Single-row-per-occupation grain** -- The spec defines a dedup grain of `[slug]` with exactly one row per occupation. Combined with full-replace semantics, there is never more than one version of a score within a single snapshot. No temporal versioning is needed within a snapshot.

### Why Bitemporal Modeling Is Not Applicable

| Bitemporal Concern | Applicability | Reason |
|-------------------|---------------|--------|
| Valid time range (valid_from/valid_to) | Not applicable | Scores have no real-world validity period. They are static opinions, not time-bounded facts. |
| Transaction time tracking | Handled by Iceberg | Snapshot history covers when data was recorded/replaced. No explicit columns needed. |
| Amendments/corrections | Not applicable | No partial correction mechanism. Full replacement only. |
| Point-in-time queries | Handled by Iceberg | "What scores did we have before re-scoring?" answered by Iceberg time travel. |
| Slowly changing dimensions | Not applicable | No SCD needed for hackathon MVP. If multiple scoring models are retained simultaneously in future, revisit. |
| Supersession metadata | Not applicable | No record-level supersession. Entire dataset is replaced atomically. |

### Recommendations for Silver/Gold Zones

- **Silver (`base.karpathy_ai_exposure`)**: Same conclusion -- static reference table. No temporal columns beyond `source_load_date` and `ingested_at` (both pipeline metadata). The `soc_resolved_method` field tracks resolution provenance, not temporal state.
- **Gold (`consumable.ai_exposure`)**: Same conclusion -- static derived table. The `stat_res` and `boss_ai_score` derivations are deterministic transformations of the static exposure score. No temporal modeling needed.
- **Backfill of engine tables**: The backfill of `consumable.program_career_paths` and `consumable.career_branches` is a one-time join enrichment, not a temporal operation. It creates a new Iceberg snapshot of those tables with the AI fields populated, which is standard snapshot behavior.

### Future Triggers for Re-Assessment

- Post-hackathon re-scoring with Gemma or another model (may want to retain both Karpathy and Gemma scores side-by-side, which would require a `scoring_model` dimension rather than full replacement)
- If multiple scoring runs are retained for comparison (score averaging, confidence intervals), temporal versioning at the scoring-run level would be needed
- If Karpathy begins publishing versioned scores with timestamps, valid time modeling would become relevant

### Artifacts Produced
- This audit trail entry

### Trade-offs Considered
- Adding a `scoring_model` or `score_version` column to the Bronze schema now (anticipating post-hackathon re-scoring) vs. deferring: chose to defer. The spec explicitly scopes this as hackathon MVP with a single source. Adding anticipatory versioning columns to the raw zone would introduce schema elements not present in the source data. This is a Silver/Gold concern if multi-model scoring is implemented.
- Modeling exposure scores as temporal facts with `valid_from = scoring_date` and `valid_to = next_scoring_date` vs. treating as static: chose static. The scores do not have a natural validity period -- they represent a single opinion, not a time-bounded measurement. Fabricating validity periods would be misleading.
