## CDE/PII Tagging Audit: silver-base-onet
**Date:** 2026-04-08
**Agent:** @cde-tagger
**Spec:** silver-base-onet
**Physical Model:** governance/models/silver-base-onet-physical.md
**PII Scan:** governance/reviews/silver-base-onet-pii-scan.md
**Domain Context:** governance/domain-context.md

### Domain Context Referenced

O*NET is a federal occupational data source published by the U.S. Department of Labor. All data is aggregated occupation-level statistics from anonymized surveys -- no individual-level data exists. The domain context identifies SOC codes as the critical cross-source join key linking O*NET to BLS OOH and College Scorecard via the CIP-SOC crosswalk. The FutureProof pipeline consumes O*NET data for three Gold zone outputs: HMN (Human Edge) stat from Work Activities importance ratings, Burnout boss fight from Work Context values, and Stage 3 career branching from Related Occupations similarity.

### Columns Flagged as CDE

| Column | Table | Rationale |
|--------|-------|-----------|
| bls_soc_code | base.onet_occupations | Natural key and primary crosswalk anchor linking O*NET to BLS OOH and College Scorecard. All downstream Gold joins key on this field. |
| data_completeness_tier | base.onet_occupations | Determines whether Gold zone can produce full stats or must apply partial-data handling. Incorrect classification silently corrupts Gold outputs. |
| bls_soc_code | base.onet_activity_profiles | FK join key for linking activity importance to occupations. HMN stat and AI boss fight depend on correct occupation assignment. |
| element_id | base.onet_activity_profiles | Identifies which of 41 Work Activity dimensions a row measures. HMN stat selects specific elements; wrong IDs corrupt the score. |
| importance | base.onet_activity_profiles | Primary numeric input to HMN stat and AI exposure analysis. Directly backs activity-level importance scores. |
| bls_soc_code | base.onet_context_profiles | FK join key for linking context measurements to occupations. Burnout boss fight depends on correct occupation assignment. |
| element_id | base.onet_context_profiles | Identifies which of 57 Work Context dimensions a row measures. Burnout score filters on 9 specific burnout-relevant elements. |
| context_value | base.onet_context_profiles | Primary numeric input to Burnout boss fight. Directly backs work environment risk assessment. |

**Total CDEs: 8 across 3 tables (matches physical model)**

### Columns Flagged as PII

None. PII scan confirmed zero PII across all 4 tables (92,594 rows scanned). All data is aggregated federal occupation-level statistics.

### Columns Evaluated -- Not Flagged

| Column | Table | Reason Not Critical/Sensitive |
|--------|-------|-------------------------------|
| record_id | base.onet_occupations | Technical surrogate key; not consumed by business processes |
| primary_title | base.onet_occupations | Display label; bls_soc_code is the authoritative identifier |
| description | base.onet_occupations | Narrative text; not a computational input to downstream stats |
| onet_detail_codes | base.onet_occupations | Traceability metadata; not used in Gold zone computations |
| onet_detail_count | base.onet_occupations | Metadata count; derived from onet_detail_codes |
| multi_detail_flag | base.onet_occupations | Convenience flag derived from onet_detail_count |
| has_work_activities | base.onet_occupations | Boolean availability flag; not a stat input |
| has_work_context | base.onet_occupations | Boolean availability flag; not a stat input |
| has_tasks | base.onet_occupations | Boolean availability flag; not a stat input |
| has_related | base.onet_occupations | Boolean availability flag; not a stat input |
| source_load_date | base.onet_occupations | Pipeline metadata |
| ingested_at | base.onet_occupations | Pipeline metadata |
| record_id | base.onet_activity_profiles | Technical surrogate key |
| element_name | base.onet_activity_profiles | Display label; element_id is the authoritative identifier |
| importance_rank | base.onet_activity_profiles | Derived from importance; recomputable |
| is_high_importance | base.onet_activity_profiles | Convenience threshold flag derived from importance |
| onet_details_averaged | base.onet_activity_profiles | Transparency metadata |
| suppress_flag | base.onet_activity_profiles | Quality signal; not a stat input |
| source_load_date | base.onet_activity_profiles | Pipeline metadata |
| ingested_at | base.onet_activity_profiles | Pipeline metadata |
| record_id | base.onet_context_profiles | Technical surrogate key |
| element_name | base.onet_context_profiles | Display label; element_id is the authoritative identifier |
| scale_id | base.onet_context_profiles | Scale metadata for interpreting context_value |
| is_burnout_element | base.onet_context_profiles | Convenience filter derived from element_id mapping |
| onet_details_averaged | base.onet_context_profiles | Transparency metadata |
| suppress_flag | base.onet_context_profiles | Quality signal; not a stat input |
| source_load_date | base.onet_context_profiles | Pipeline metadata |
| ingested_at | base.onet_context_profiles | Pipeline metadata |
| record_id | base.onet_career_transitions | Technical surrogate key |
| bls_soc_code | base.onet_career_transitions | Join key but career transitions table has no CDEs per physical model -- Stage 3 branching is supplemental to core stats |
| related_bls_soc_code | base.onet_career_transitions | Target occupation key; same reasoning as above |
| best_index | base.onet_career_transitions | Relatedness metric; career transitions are supplemental to core FutureProof stats |
| relatedness_tier | base.onet_career_transitions | Derived tier from best_index; supplemental |
| is_primary | base.onet_career_transitions | Convenience filter derived from relatedness_tier |
| relationship_type | base.onet_career_transitions | Constant value ("similarity"); no variability |
| source_load_date | base.onet_career_transitions | Pipeline metadata |
| ingested_at | base.onet_career_transitions | Pipeline metadata |
