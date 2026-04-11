# Audit Trail: Semantic Modeler -- gold-futureproof-engine-backfill-ai

**Date:** 2026-04-09
**Agent:** @semantic-modeler
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 4: Backfill)
**Mode:** Backfill (physical -> logical)

## Actions Taken

1. Read existing Gold transformer at `src/gold/futureproof_engine.py` to understand current schema and join chain.
2. Read existing physical model at `governance/models/gold-futureproof-engine-physical.md` to identify placeholder fields.
3. Read existing logical model at `governance/models/gold-futureproof-engine-logical.md` to understand entity groupings.
4. Read `consumable.ai_exposure` physical model at `governance/models/gold-ai-exposure-physical.md` for source schema.
5. Cross-referenced business glossary terms BT-080, BT-083, BT-087, BT-088, BT-089.
6. Produced physical model: `governance/models/gold-futureproof-engine-backfill-ai-physical.md` (PROPOSED).
7. Produced logical model: `governance/models/gold-futureproof-engine-backfill-ai-logical.md` (PROPOSED).

## Artifacts Produced

| Artifact | Path | Status |
|----------|------|--------|
| Physical model | governance/models/gold-futureproof-engine-backfill-ai-physical.md | PROPOSED |
| Logical model | governance/models/gold-futureproof-engine-backfill-ai-logical.md | PROPOSED |

## Key Decisions

### 1. program_career_paths: No schema evolution needed
The existing Iceberg schema already defines stat_res (field 13) and boss_ai_score (field 16) as nullable INTEGER. The backfill only changes data values, not schema.

### 2. career_branches: Schema evolution required (6 new columns)
Unlike program_career_paths, career_branches had no placeholder columns for AI stats. Added: source_res, source_ai_boss, related_res, related_ai_boss, res_delta, ai_boss_delta. Naming follows existing convention (source_X, related_X, X_delta).

### 3. match_quality derivation unchanged
Per spec, AI exposure is supplemental enrichment. The existing match_quality taxonomy (full/partial_no_onet/partial_no_bls/scorecard_only) remains, as it describes cross-source join success for core BLS+ONET data.

### 4. LEFT JOIN pattern preserved
Consistent with all existing joins in the FutureProof engine. Unmatched SOCs get NULL for AI fields.

## Alternatives Considered

- **INNER JOIN for ai_exposure**: Rejected. Would drop ~10-20% of rows where SOC is not in Karpathy's 342 scored occupations. Inconsistent with existing LEFT JOIN pattern.
- **Add has_ai flag to match_quality**: Deferred. The spec says match_quality is unchanged. Could be added in a future iteration if AI coverage becomes a first-class quality signal.
- **stat_res_delta naming for career_branches**: Considered `stat_res_delta` for consistency with the stat name, but followed the shorter `res_delta` pattern to match existing `grw_delta`, `hmn_delta`, `burnout_delta` style.

## Stage Progression

| Stage | Status | Timestamp |
|-------|--------|-----------|
| Physical model (Stage 1 in backfill) | PROPOSED | 2026-04-09 |
| Logical model (Stage 2 in backfill) | PROPOSED | 2026-04-09 |
| Conceptual model (Stage 3 in backfill) | Not produced -- scoped to physical+logical per task | -- |
