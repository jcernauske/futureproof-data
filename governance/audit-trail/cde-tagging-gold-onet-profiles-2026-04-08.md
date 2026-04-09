# CDE/PII Tagging Audit: gold-onet-profiles

**Date:** 2026-04-08
**Agent:** @cde-tagger
**Spec:** docs/specs/gold-onet-profiles.md
**Tables Tagged:** consumable.onet_work_profiles (27 columns), consumable.career_transitions (14 columns)

## Domain Context Referenced

- governance/domain-context.md: O*NET section -- Regulatory context (DOL/ETA CC BY 4.0 license, OMB SOC taxonomy), PII expectations (no PII -- all occupation-level aggregates from anonymized surveys)
- governance/models/gold-onet-profiles-physical.md: Column definitions, CDE/PII flags from semantic modeler
- docs/specs/gold-onet-profiles.md: HMN score derivation, Burnout score derivation, downstream consumer patterns
- Established CDE patterns from consumable.occupation_profiles contract (gold-occupation-profiles-bls-ooh)

## Tagging Decisions

### Table 1: consumable.onet_work_profiles

#### Columns Flagged as CDE (4 columns)

| Column | Rationale |
|--------|-----------|
| bls_soc_code | Natural key and primary join anchor. Every downstream consumer (Gemma, game engine, career_transitions, crosswalk) queries by this field. Sole grain field; incorrect/missing values sever the occupation-level linkage for HMN stat and AI/Burnout boss fights. |
| hmn_score | Directly backs the HMN pentagon stat (1-10 scale). Primary scored output consumed by game engine for pentagon display, Gemma for human-edge narrative, and AI boss fight context. Incorrect values misrepresent human edge potential to students. |
| burnout_score | Directly backs the Burnout boss fight (1-10 scale). Primary scored output consumed by game engine for boss fight difficulty calibration and Gemma for burnout risk narrative. Incorrect values miscalibrate the Burnout boss fight. |
| burnout_drivers | JSON array of top 3 burnout-contributing elements. Directly consumed by Gemma for burnout narrative -- provides the actionable "why" behind burnout_score. Without this, burnout_score is an opaque number. Consistent with physical model CDE designation. |

#### Columns NOT Flagged as CDE (23 columns)

| Column | Reason Not Critical |
|--------|-------------------|
| record_id | Technical surrogate key. Not consumed by business processes; used only for pipeline infrastructure. |
| primary_title | Display label, but not independently critical since consumable.occupation_profiles carries the authoritative BLS title. |
| description | Informational text. Not used in scoring, joins, or business decisions. |
| multi_detail_flag | Informational flag carried from Silver. Input to confidence_tier but not independently consumed. |
| data_completeness_tier | Input to confidence_tier derivation. Not independently consumed by downstream applications. |
| hmn_score_rounded | Derived from hmn_score via ROUND(). Not independently critical. |
| top_human_activities | Informational detail supporting hmn_score narrative. Not used in scoring or joins. |
| human_activity_count | Always 14 when present. Not independently meaningful for business decisions. |
| burnout_score_rounded | Derived from burnout_score via ROUND(). Not independently critical. |
| time_pressure | Individual burnout element. The composite burnout_score carries the analytical weight. |
| work_hours | Individual burnout element. The composite burnout_score carries the analytical weight. |
| consequence_of_error | Individual burnout element. The composite burnout_score carries the analytical weight. |
| activity_importance_mean | Summary metric. Not directly consumed for scoring or boss fights. |
| top_5_activities | Informational detail for Gemma descriptions. Not independently critical for scoring. |
| activity_profile_available | Informational boolean flag. |
| context_profile_available | Informational boolean flag. |
| confidence_tier | Informational metadata. Not consumed as a primary business metric. |
| suppress_pct_activities | Data quality metadata. |
| suppress_pct_context | Data quality metadata. |
| backs_stats | Static documentation metadata ("HMN"). |
| backs_bosses | Static documentation metadata ("AI,Burnout"). |
| source_load_date | Pipeline metadata. |
| promoted_at | Pipeline metadata. |

#### PII Assessment: NONE

All 27 columns contain occupation-level aggregate data derived from O*NET (anonymized DOL surveys). No personal names, worker identifiers, health records, financial PII, or location data. Confirmed by governance/domain-context.md O*NET PII section.

### Table 2: consumable.career_transitions

#### Columns Flagged as CDE (2 columns)

| Column | Rationale |
|--------|-----------|
| bls_soc_code | Source occupation SOC code and first component of composite natural key. Primary query pattern for Stage 3 branching ("given occupation X, what are related careers?"). Join key to work profiles and occupation profiles. |
| related_bls_soc_code | Related occupation SOC code and second component of composite natural key. Identifies the destination occupation in the branching tree. Join key to retrieve related occupation's HMN/Burnout/growth/wage data. |

#### Columns NOT Flagged as CDE (12 columns)

| Column | Reason Not Critical |
|--------|-------------------|
| record_id | Technical surrogate key. Not consumed by business processes. |
| source_title | Display label enriched from join. Not independently critical for scoring or joins. |
| related_title | Display label enriched from join. Not independently critical for scoring or joins. |
| best_index | Display ordering. The SOC code pair identifies the relationship; best_index is UI ordering. |
| relatedness_tier | Informational classification for UI filtering. Not used in scoring or joins. |
| is_primary | Convenience boolean derived from relatedness_tier. Not independently critical. |
| relationship_type | Static constant ("similarity"). No analytical signal. |
| source_has_work_profile | Informational boolean for UI. Not used in scoring or joins. |
| related_has_work_profile | Informational boolean for UI. Not used in scoring or joins. |
| backs_feature | Static documentation metadata ("Stage3Branching"). |
| source_load_date | Pipeline metadata. |
| promoted_at | Pipeline metadata. |

#### PII Assessment: NONE

All 14 columns contain occupation-level relationship data. SOC codes and titles are public government classifications. No personal data of any kind.

## Deviation from Expected CDEs

The task expected `record_id` to be flagged as CDE (grain key). I did NOT flag record_id as CDE in either table because:
- record_id is a technical surrogate key (SHA-256 hash) used for pipeline infrastructure (deduplication, idempotent promotes)
- No downstream business process, report, or consumer queries by record_id
- The natural keys (bls_soc_code, related_bls_soc_code) serve the grain identification role and ARE flagged as CDE
- This is consistent with the established pattern in consumable.occupation_profiles where record_id is also not CDE

## Alignment with Physical Model

The physical model (governance/models/gold-onet-profiles-physical.md) pre-flagged:
- Table 1: bls_soc_code, hmn_score, burnout_score, burnout_drivers as CDE (4 columns)
- Table 2: bls_soc_code, related_bls_soc_code as CDE (2 columns)

My tagging matches the physical model exactly. The physical model's CDE designations are well-justified by downstream consumer analysis.
