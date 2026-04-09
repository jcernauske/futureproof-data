# Lineage Audit Trail: gold-onet-profiles

**Agent:** @lineage-tracker
**Spec:** docs/specs/gold-onet-profiles.md
**Timestamp:** 2026-04-08T18:00:00Z
**Lineage File:** governance/lineage/gold-onet-profiles-20260408T180000Z.json

## Transformations Captured

Two OpenLineage run events were produced, one per Gold table in the spec.

### Event 1: consumable.onet_work_profiles

- **Job:** gold.transform-onet-work-profiles
- **Inputs:** 3 Silver tables (base.onet_occupations, base.onet_activity_profiles, base.onet_context_profiles)
- **Output:** consumable.onet_work_profiles (27 columns, 798 rows)
- **Column lineage:** All 27 output fields have full lineage records
  - 6 DIRECT carries from base.onet_occupations (bls_soc_code, primary_title, description, multi_detail_flag, data_completeness_tier, source_load_date)
  - 17 DERIVED fields (record_id, hmn_score, hmn_score_rounded, top_human_activities, human_activity_count, burnout_score, burnout_score_rounded, burnout_drivers, time_pressure, work_hours, consequence_of_error, top_5_activities, activity_profile_available, context_profile_available, confidence_tier, backs_stats, backs_bosses)
  - 3 AGGREGATION fields (activity_importance_mean, suppress_pct_activities, suppress_pct_context)
  - 1 metadata field (promoted_at)

### Event 2: consumable.career_transitions

- **Job:** gold.transform-career-transitions
- **Inputs:** 2 Silver tables + 1 Gold table (base.onet_career_transitions, base.onet_occupations, consumable.onet_work_profiles)
- **Output:** consumable.career_transitions (14 columns, 15,944 rows)
- **Column lineage:** All 14 output fields have full lineage records
  - 5 DIRECT carries from base.onet_career_transitions (bls_soc_code, best_index, relatedness_tier, is_primary, relationship_type)
  - 1 DIRECT carry from base.onet_career_transitions (source_load_date)
  - 4 DERIVED fields via join (source_title, related_title, source_has_work_profile, related_has_work_profile)
  - 2 DERIVED fields (record_id, backs_feature)
  - 1 metadata field (promoted_at)

## Cross-table Dependency

Event 2 (career_transitions) depends on Event 1 (onet_work_profiles). This dependency is captured via consumable.onet_work_profiles appearing as an input to Event 2. The work profile availability flags (source_has_work_profile, related_has_work_profile) are derived from the activity_profile_available field in Event 1's output.

## Naming Decisions

| Entity | Name | Rationale |
|--------|------|-----------|
| Job 1 | gold.transform-onet-work-profiles | Follows zone.verb-noun pattern from existing lineage files |
| Job 2 | gold.transform-career-transitions | Same pattern; matches output table name |
| Dataset names | Use Iceberg namespace.table format | Consistent with all other lineage files in the project |

## Key Derivation Chains Documented

1. **HMN Score:** base.onet_activity_profiles.importance + element_id -> human_ratio (per occupation) -> min/max rescale across 774 occupations -> hmn_score (1-10)
2. **Burnout Score:** base.onet_context_profiles.context_value + scale_id + is_burnout_element -> normalize CX/CT -> average -> burnout_score (1-10)
3. **Confidence Tier:** data_completeness_tier + suppress_pct_activities + suppress_pct_context -> priority-based tier assignment
4. **Work Profile Flags:** consumable.onet_work_profiles.activity_profile_available -> source_has_work_profile / related_has_work_profile

## Interpretation Notes

- The HMN score uses min/max rescaling (Phase 2 in the code), not the simple ratio formula originally proposed in the spec. The code computes human_ratio first, then rescales across all occupations so the full 1-10 range is used. This is documented in the lineage.
- Burnout element IDs in the code use the is_burnout_element flag from Silver rather than hardcoded IDs. The BURNOUT_ELEMENT_IDS constant in the code serves as documentation only. The lineage references is_burnout_element as the operative input field.
- The career_transitions transformer reads the full consumable.onet_work_profiles table but only uses bls_soc_code and activity_profile_available. The input schema in the lineage event reflects only the consumed fields.
