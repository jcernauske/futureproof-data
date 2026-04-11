## Audit Trail: EDA for gold-futureproof-engine-backfill-ai

**Timestamp:** 2026-04-09
**Agent:** @data-analyst
**Spec:** raw-ingest-karpathy-ai-exposure (Zone 4: Backfill)
**Action:** Exploratory data analysis of backfill coverage

### Datasets Analyzed
- consumable.ai_exposure (389 rows)
- consumable.program_career_paths (626,406 rows)
- consumable.career_branches (15,944 rows)

### Key Findings
1. SOC match rate between program_career_paths and ai_exposure is 57.4% (rows), significantly below the spec's expected 80-90%.
2. The gap is structural: Karpathy scored 342 BLS OOH occupations, but the crosswalk maps to 634 distinct SOC codes. Education occupations (group 25) are the largest gap.
3. stat_res and boss_ai_score are currently 100% null as expected.
4. Post-backfill stat_res null rate will be 42.6%, not 10-20% as spec estimated.
5. 134,114 rows (21.4%) will achieve the full 5/5 stat pentagon.
6. career_branches stat_res_delta computable for only 25.7% of rows.
7. ai_exposure data quality is clean: inverse invariant holds for all 389 rows, no edge cases.

### Threshold Recommendations
- Accept 40-45% null rate for stat_res post-backfill (warn > 50%)
- Accept 20-25% full pentagon rate (stats_available_count=5)
- Accept 25-30% career_branches delta coverage

### Artifacts Produced
- `governance/eda/gold-futureproof-engine-backfill-ai-eda.md`
