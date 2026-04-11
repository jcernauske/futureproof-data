# Data Steward Assessment: gold-futureproof-engine-backfill-ai

**Agent:** @data-steward
**Date:** 2026-04-09
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 4: Backfill)
**Scope:** AI Exposure backfill into consumable.program_career_paths and consumable.career_branches

---

## Assessment: No New Business Terms Required

The AI exposure backfill introduces no new business concepts that are not already covered by approved glossary terms. All four relevant terms were defined during the Karpathy AI Exposure spec and the original FutureProof Engine spec:

| Term ID | Name | Status | Covers |
|---------|------|--------|--------|
| BT-080 | AI Resilience (stat_res) | **Approved** | The pentagon stat derived from exposure_score inversion. Definition already specifies the formula `MIN(11 - exposure_score, 10)` and the relationship to BT-094. |
| BT-083 | Boss AI Score | **Approved** | The Fight AI boss strength derived from exposure_score floor. Definition already specifies `MAX(exposure_score, 1)` and the invariant `stat_res + boss_ai_score = 11`. |
| BT-094 | AI Exposure Score (Karpathy) | **Approved** | The source 0-10 score from Karpathy's LLM scoring pipeline. Definition includes methodology caveats and source attribution. |
| BT-095 | AI Exposure Rationale | **Approved** | The LLM-generated explanation text carried as a display field. |

### Why No New Terms

The backfill populates existing placeholder fields and adds derivative columns (source_res, related_res, res_delta, source_ai_boss, related_ai_boss, ai_boss_delta) that are compositional applications of BT-080, BT-083, and BT-091 (Stat Delta). These are not new business concepts -- they are the same concepts applied to the career branch context, following the exact naming pattern already established by source_grw/related_grw/grw_delta.

The `res_delta` and `ai_boss_delta` columns on career_branches are covered by BT-091 (Stat Delta), which was defined as a general concept: "The arithmetic difference between the same stat measured on two related occupations in a career branch pair." The definition explicitly lists deltas as a category, not as individual terms per stat.

---

## Existing Term Coverage Confirmation

| Backfill Element | Covered By | Notes |
|-----------------|------------|-------|
| stat_res on program_career_paths | BT-080 | Was already documented as placeholder; now populated |
| boss_ai_score on program_career_paths | BT-083 | Was already documented as placeholder; now populated |
| source_res on career_branches | BT-080 | Same concept applied to source occupation |
| related_res on career_branches | BT-080 | Same concept applied to target occupation |
| source_ai_boss on career_branches | BT-083 | Same concept applied to source occupation |
| related_ai_boss on career_branches | BT-083 | Same concept applied to target occupation |
| res_delta on career_branches | BT-091 | Follows existing delta pattern (grw_delta, hmn_delta, etc.) |
| ai_boss_delta on career_branches | BT-091 | Follows existing delta pattern |
| stats_available_count range 0-5 | BT-087 | Definition already says "how many of the five pentagon stats are non-null"; range expansion is implicit |
| bosses_available_count range 0-5 | BT-088 | Same -- definition covers 0-5 range |
| Pentagon completion (5/5) | BT-077 | Five-Stat Pentagon definition already lists all 5 stats including RES |
| Gauntlet completion (5/5) | BT-081 | Boss Fight Score definition already lists all 5 bosses including AI |

---

## Superseded DQ Rules

The backfill invalidates 4 DQ rules from the original `gold-futureproof-engine.json` rule set. These rules enforced the placeholder state and must be replaced:

| Superseded Rule | Original Assertion | Replacement |
|----------------|-------------------|-------------|
| GLD-FE-010 | `stat_res IS NULL` for 100% of rows | Replaced by GLD-BF-001: `stat_res` range 1-10 where non-null |
| GLD-FE-011 | `boss_ai_score IS NULL` for 100% of rows | Replaced by GLD-BF-002: `boss_ai_score` range 1-10 where non-null |
| GLD-FE-020 | `stats_available_count` range 0-4 | Replaced by GLD-BF-003: range 0-5 |
| GLD-FE-022 | `bosses_available_count` range 0-4 | Replaced by GLD-BF-004: range 0-5 |

The supersession chain is documented in `governance/dq-rules/gold-futureproof-engine-backfill-ai.json` under the `supersedes` key.

---

## Recommendation

**Proceed with modeling and implementation.** No glossary updates are needed. The existing approved terms (BT-080, BT-083, BT-094, BT-095) and the existing proposed terms (BT-087, BT-088, BT-091) fully cover the backfill scope.
