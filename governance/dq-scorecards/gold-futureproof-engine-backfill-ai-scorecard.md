## DQ Scorecard: gold-futureproof-engine-backfill-ai
**Spec:** gold-futureproof-engine-backfill-ai
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Overall Score:** 20/20 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-09T23:35:00.382291+00:00)
**Run ID:** 94e7b6d3

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-BF-001 |  | P0 | stat_res (AI Resilience) must be in [1, 10] when populated. Derived from ai_exposure.stat_res via LEFT JOIN on soc_code. Supersedes GLD-FE-010 (placeholder null check). | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-002 |  | P0 | boss_ai_score (Fight AI boss strength) must be in [1, 10] when populated. Derived from ai_exposure.boss_ai_score via LEFT JOIN on soc_code. Supersedes GLD-FE-011 (placeholder null check). | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-003 |  | P0 | The inverse invariant stat_res + boss_ai_score = 11 must hold for all rows where both are populated. This is a mathematical identity guaranteed by the derivation: (11 - x) + x = 11. Any violation indicates the two values were sourced from different rows or corrupted in transit. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-004 |  | P1 | Post-backfill, stat_res should be null for 40-45% of rows. Values outside this range indicate a join problem (too many nulls) or incorrect SOC matching (too few nulls). | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-BF-005 |  | P0 | stat_res and boss_ai_score must always be both null or both non-null. They come from the same LEFT JOIN on soc_code -- if one is populated, the other must be too. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-006 |  | P0 | stats_available_count must be NOT NULL and 0-5 post-backfill. Supersedes GLD-FE-020 which capped at 4 (stat_res was always null in MVP). Now stat_res can be non-null, so count can reach 5. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-007 |  | P0 | bosses_available_count must be NOT NULL and 0-5 post-backfill. Supersedes GLD-FE-022 which capped at 4 (boss_ai_score was always null in MVP). Now boss_ai_score can be non-null, so count can reach 5. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-008 |  | P0 | Any row where stat_res is non-null must have stats_available_count >= 1. If stat_res is populated, the count must reflect it. A count of 0 with a non-null stat_res indicates the recomputation failed to include the AI stat. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-009 |  | P0 | Any row where boss_ai_score is non-null must have bosses_available_count >= 1. If boss_ai_score is populated, the count must reflect it. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-010 |  | P1 | Post-backfill, 20-25% of PCP rows should achieve the full 5/5 stat pentagon. These are rows that had stats_available=4 pre-backfill AND matched ai_exposure. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-BF-011 |  | P0 | Backfill must not add or remove rows from program_career_paths. The LEFT JOIN to ai_exposure should preserve all existing rows. This rule uses the same range as GLD-FE-003 to confirm row count stability. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-BF-012 |  | P0 | Backfill must not add or remove rows from career_branches. The two LEFT JOINs to ai_exposure (source and target) should preserve all existing rows. Matches GLD-FE-034 exact count. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-BF-013 |  | P0 | All four new AI stat columns (source_res, source_ai_boss, related_res, related_ai_boss) must be in [1, 10] when non-null. Extends GLD-FE-036 which covers grw/hmn/burnout but not the new AI columns. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-014 |  | P0 | res_delta must equal related_res minus source_res wherever both sides are non-null. This is the derivation formula per the physical model. Any mismatch indicates a computation bug. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-015 |  | P0 | ai_boss_delta must equal related_ai_boss minus source_ai_boss wherever both sides are non-null. Same derivation pattern as res_delta. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-016 |  | P0 | AI stat deltas must be in [-9, +9] when non-null. Since source and target scores are constrained to [1, 10], the maximum delta is 10-1=9 and minimum is 1-10=-9. Extends GLD-FE-037 which covers grw/hmn/burnout deltas only. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-017 |  | P0 | res_delta must be null if either source_res or related_res is null. Same for ai_boss_delta. Extends GLD-FE-038 which covers existing deltas only. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-018 |  | P0 | source_res and source_ai_boss must be both null or both non-null (same for related_res and related_ai_boss). They come from the same ai_exposure row per join side. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-019 |  | P0 | The inverse invariant stat_res + boss_ai_score = 11 must hold on both the source and related sides of career_branches, wherever both values are non-null. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-BF-020 |  | P2 | Post-backfill, 22-32% of career_branches rows should have a computable res_delta (both source and target SOC matched in ai_exposure). Values outside this range indicate a coverage shift. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 20 | 20 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

