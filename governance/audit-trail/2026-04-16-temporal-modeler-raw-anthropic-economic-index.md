# Audit Trail: Temporal Modeling — raw-ingest-anthropic-economic-index

**Agent:** @temporal-modeler
**Date:** 2026-04-16
**Spec:** docs/specs/raw-ingest-anthropic-economic-index.md
**Artifact:** governance/temporal/raw-anthropic-economic-index-temporal.md

## Verdict

TRIVIAL (release-stamp sufficient). No SCD-2. No bitemporal schema. Keep existing `source_release` + `ingested_at` + Iceberg snapshots.

## Key Decisions

1. **SCD-2 rejected.** Data is whole-file, release-versioned, whole-file-replaceable. Per-row `valid_from` / `valid_to` would fabricate precision the source does not expose. Iceberg snapshot history already provides release-over-release recovery.
2. **Release swap = full overwrite, new Iceberg snapshot.** Matches Anthropic's own publication semantics (immutable releases). Preserves `soc_code` grain in Silver and `soc_code` grain in Gold.
3. **Iceberg snapshot tagging recommended.** Tag each post-swap snapshot with the release name (e.g. `release_2025_03_27`). Cheap named-pointer alternative to Iceberg branching, which is overkill for current access patterns.
4. **Schema additions (minor):**
   - Silver: add `ingested_at` (propagate from Bronze).
   - Gold: add `anthropic_ingested_at` (companion to already-planned `anthropic_source_release`).
   Both additive, nullable, no grain impact.
5. **Downstream regression gate.** Release swaps change `observed_exposure_pct`, `automation_pct`, and downstream `stat_res` / `boss_ai_score`. Gate swaps with drift check reusing the existing `AI_EXPOSURE_AB_OVERRIDE` env-var override pattern in `src/gold/ai_exposure_transformer.py`.

## Rationale — Why Release-Stamp Is Enough

`(source_release, ingested_at)` functionally encodes the same information SCD-2 would:

- `source_release` = business-effective-date proxy (which Anthropic world-view).
- `ingested_at` = system-effective timestamp (when we recorded it).

No downstream consumer (Gold `consumable.ai_exposure`, MCP `get_ai_exposure`, S4 composite) asks a question that requires per-row bitemporal reconstruction. All queries are either "current" or "as-of Iceberg snapshot."

## Trade-offs Considered

| Option | Decision |
|--------|----------|
| SCD-2 on Silver (valid_from/valid_to/is_current per (SOC, release)) | Rejected — row explosion without query benefit |
| Keep multiple releases co-resident in Silver | Rejected — breaks soc_code grain |
| Synthetic valid_from/valid_to from release ordering | Rejected — irregular cadence makes valid_to lie |
| Drop source_release, rely only on Iceberg snapshots | Rejected — release provenance is a business fact (CC-BY attribution) |
| Iceberg branches per release | Rejected for now — tagging is sufficient; branch if concurrent multi-release query becomes a requirement |
| Full overwrite vs. append on release swap | Overwrite — matches upstream publication semantics |

## Scope Boundaries Observed

- No schema changes proposed beyond the two additive timestamp fields.
- No DQ rules authored (deferred to @dq-rule-writer).
- No lineage edits (deferred to @lineage-tracker).
- No entity-resolution or concept-mapping decisions.
- No modifications to the spec itself.

## Files Written

- `governance/temporal/raw-anthropic-economic-index-temporal.md` (temporal design)
- `governance/audit-trail/2026-04-16-temporal-modeler-raw-anthropic-economic-index.md` (this file)
