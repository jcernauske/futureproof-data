## DQ Scorecard: gold-ai-exposure
**Spec:** gold-ai-exposure
**Date:** 2026-04-09
**Agent:** @dq-engineer
**Overall Score:** 15/15 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-09T21:27:59.880405+00:00)
**Run ID:** abd0ef16

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| GLD-AIE-001 |  | P0 | The declared grain is one row per soc_code. Any duplicate indicates a promote or transformer failure. Maps to patterns CONS-GRAIN-UNIQUE and ADV-GRAIN-UNIQUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-002 |  | P0 | Surrogate key record_id (computed via compute_grain_id with prefix 'aie') must be non-null and unique. Duplicate or null record_id indicates a grain hash collision or derivation bug. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-003 |  | P0 | Gold table must contain 389 +/- 5% rows (370-409). Row count is determined by Silver rows where bls_match=true. Maps to ADV-ENTITY-COVERAGE. | PASS | actual=0.0, threshold=result = 0.0 |
| GLD-AIE-004 |  | P0 | stat_res (AI Resilience) must be an integer in [1, 10]. Derived as MIN(11 - exposure_score, 10). Values outside this range indicate a derivation bug. Maps to CONS-IMPOSSIBLE-VALUE and ADV-VALUE-RANGE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-005 |  | P0 | boss_ai_score (Fight AI boss strength) must be an integer in [1, 10]. Derived as MAX(exposure_score, 1). Values outside this range indicate a derivation bug. Maps to CONS-IMPOSSIBLE-VALUE and ADV-VALUE-RANGE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-006 |  | P0 | exposure_score (original Karpathy score) must be an integer in [0, 10]. Passthrough from Silver. Physical model CHECK constraint. Maps to CONS-IMPOSSIBLE-VALUE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-007 |  | P0 | For all rows where exposure_score >= 1, stat_res + boss_ai_score must equal 11. This invariant is guaranteed by the derivation math: (11 - x) + x = 11. Any violation indicates a derivation bug. Maps to ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-008 |  | P0 | rationale is a required display field for the Fight AI boss narrative in the FutureProof frontend. Must be non-null and non-empty. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-009 |  | P1 | Rationale text should be substantive (at least 100 characters). Short rationales would indicate truncation or corruption. Maps to ADV-VALUE-RANGE. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-010 |  | P0 | Every soc_code in ai_exposure must exist in consumable.occupation_profiles. These tables must be joinable for downstream backfill into program_career_paths and career_branches. Maps to ADV-FK-VALID. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-011 |  | P0 | Every soc_code must match the SOC standard format XX-XXXX. This is the primary join key for occupation_profiles and downstream tables. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-012 |  | P0 | All 9 columns in consumable.ai_exposure are NOT NULL per the physical model. Any null value indicates a transformer or promote failure. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-013 |  | P0 | stat_res must equal MIN(11 - exposure_score, 10) for every row. Validates the derivation formula was applied correctly, not just the output range. Maps to ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-014 |  | P0 | boss_ai_score must equal MAX(exposure_score, 1) for every row. Validates the derivation formula was applied correctly, not just the output range. Maps to ADV-CROSS-COLUMN. | PASS | actual=0, threshold=result_count = 0.0 |
| GLD-AIE-015 |  | P2 | ai_exposure should cover at least 40% of occupation_profiles SOC codes. Current coverage is 46.8% (389/832). A drop below 40% would indicate significant data loss. Tracked for monitoring. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 15 | 15 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

