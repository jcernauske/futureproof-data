# Lineage Tracker Audit Trail: gold-futureproof-engine

**Agent:** @lineage-tracker
**Spec:** docs/specs/gold-futureproof-engine.md
**Timestamp:** 2026-04-09T12:00:00Z
**Lineage File:** governance/lineage/gold-futureproof-engine-20260409T120000Z.json

## Transformations Captured

### Event 1: consumable.program_career_paths (626,406 rows)

**Job:** gold.transform-program-career-paths
**Inputs:** 4 Gold tables + 1 Silver crosswalk
**Transformation type:** Cross-source join with stat derivation and dedup

Captured lineage for all 40 output columns:
- 14 DERIVED fields (record_id, soc_code, occupation_title, stat_ern, stat_roi, stat_res, boss_ai_score, boss_loans_score, boss_ceiling_score, match_quality, stats_available_count, bosses_available_count, overall_confidence, promoted_at)
- 25 DIRECT carry fields from upstream Gold/Silver sources
- 1 field (confidence_tier_program) renamed from career_outcomes.confidence_tier

Key lineage decisions:
- **CIP prefix join:** Documented the critical LEFT(crosswalk.cipcode, 5) join that bridges XX.XX (Scorecard) to XX.XXXX (crosswalk) format. This is the core cross-source join enabling 91% CIP code coverage.
- **match_quality derivation:** Documented that this is derived at Gold time from join success flags, NOT from crosswalk Silver has_scorecard_match (which is FALSE for all rows due to strict 6-digit matching).
- **stat_ern blended source:** Documented dual-source derivation (60% program earnings rank from Scorecard, 40% wage percentile from BLS).
- **Dedup strategy:** Documented ROW_NUMBER partitioned by grain fields ordered by stat_richness DESC.
- **Placeholder fields:** Documented stat_res and boss_ai_score as null placeholders pending Karpathy integration.

### Event 2: consumable.career_branches (15,944 rows)

**Job:** gold.transform-career-branches
**Inputs:** 3 Gold tables (career_transitions, occupation_profiles, onet_work_profiles)
**Transformation type:** 1:1 enrichment with stat lookups and delta computation

Captured lineage for all 24 output columns:
- 7 DERIVED fields (record_id, grw_delta, hmn_delta, burnout_delta, wage_delta, branch_has_full_data, promoted_at)
- 16 DIRECT carry fields (8 from career_transitions, 4 source stats, 4 related stats + 2 related context fields from occupation_profiles/onet_work_profiles lookups)
- Field renames: bls_soc_code -> soc_code, related_bls_soc_code -> related_soc_code

Key lineage decisions:
- **Dual lookup pattern:** Source and related occupations both look up stats from the same two tables (occupation_profiles, onet_work_profiles) but keyed by different SOC codes. Documented both lookup paths.
- **Null-safe deltas:** Documented that all 4 delta fields are null if either side of the subtraction is null.

## Completeness Verification

- All 5 input datasets documented with schemas
- All 64 output columns (40 + 24) have column-level lineage
- Every derived field has transformation description and type
- Agent attribution recorded for both events
- Spec reference linked in both run facets
- Runtime metrics captured (row counts, field counts)

## Naming Decisions

- Job names follow `gold.transform-{table-name}` pattern consistent with other Gold lineage files
- Dataset names use `consumable.{table_name}` for Gold zone, `base.{table_name}` for Silver zone
- Run IDs are unique UUIDs per event (2 events in this file)
