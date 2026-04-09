# Audit Trail: @doc-generator for gold-onet-profiles

**Spec:** gold-onet-profiles
**Agent:** @doc-generator
**Date:** 2026-04-08
**Zone:** Gold (Consumable)
**Tables:** consumable.onet_work_profiles, consumable.career_transitions

---

## Actions Taken

### 1. Data Dictionary Update

**File:** `governance/data-dictionary.json`

Added two new table entries for the Gold O*NET data products. This brings the total to 4 consumable-zone tables in the data dictionary (career_outcomes, occupation_profiles, onet_work_profiles, career_transitions).

**consumable.onet_work_profiles (27 columns):**

| Column | Type | Is CDE | Source |
|--------|------|--------|--------|
| record_id | VARCHAR | false | Derived (compute_grain_id, prefix 'wp') |
| bls_soc_code | VARCHAR | true | base.onet_occupations.bls_soc_code (verbatim) |
| primary_title | VARCHAR | false | base.onet_occupations.primary_title (verbatim) |
| description | VARCHAR | false | base.onet_occupations.description (verbatim) |
| multi_detail_flag | BOOLEAN | false | base.onet_occupations.multi_detail_flag (verbatim) |
| data_completeness_tier | VARCHAR | false | base.onet_occupations.data_completeness_tier (verbatim) |
| hmn_score | DOUBLE | true | Derived (human_ratio formula) |
| hmn_score_rounded | INTEGER | false | Derived (ROUND of hmn_score) |
| top_human_activities | VARCHAR | false | Derived (top 5 human-intensive by importance) |
| human_activity_count | INTEGER | false | Derived (count of human-intensive activities) |
| burnout_score | DOUBLE | true | Derived (normalized average of 9 burnout elements) |
| burnout_score_rounded | INTEGER | false | Derived (ROUND of burnout_score) |
| burnout_drivers | VARCHAR | true | Derived (top 3 burnout contributors) |
| time_pressure | DOUBLE | false | base.onet_context_profiles (element 4.C.3.d.1) |
| work_hours | DOUBLE | false | base.onet_context_profiles (element 4.C.3.d.8) |
| consequence_of_error | DOUBLE | false | base.onet_context_profiles (element 4.C.3.a.1) |
| activity_importance_mean | DOUBLE | false | Derived (AVG of 41 activity importance values) |
| top_5_activities | VARCHAR | false | Derived (top 5 by importance rank) |
| activity_profile_available | BOOLEAN | false | Derived (EXISTS check) |
| context_profile_available | BOOLEAN | false | Derived (EXISTS check) |
| confidence_tier | VARCHAR | false | Derived (from completeness + suppression) |
| suppress_pct_activities | DOUBLE | false | Derived (suppression percentage) |
| suppress_pct_context | DOUBLE | false | Derived (suppression percentage) |
| backs_stats | VARCHAR | false | Static constant ('HMN') |
| backs_bosses | VARCHAR | false | Static constant ('AI,Burnout') |
| source_load_date | DATE | false | base.onet_occupations.source_load_date (verbatim) |
| promoted_at | TIMESTAMP | false | Generated at promotion time |

**CDE columns (4 total):** bls_soc_code, hmn_score, burnout_score, burnout_drivers

**consumable.career_transitions (14 columns):**

| Column | Type | Is CDE | Source |
|--------|------|--------|--------|
| record_id | VARCHAR | false | Derived (compute_grain_id, prefix 'tr') |
| bls_soc_code | VARCHAR | true | base.onet_career_transitions.bls_soc_code (verbatim) |
| source_title | VARCHAR | false | base.onet_occupations.primary_title (joined) |
| related_bls_soc_code | VARCHAR | true | base.onet_career_transitions.related_bls_soc_code (verbatim) |
| related_title | VARCHAR | false | base.onet_occupations.primary_title (joined) |
| best_index | INTEGER | false | base.onet_career_transitions.best_index (verbatim) |
| relatedness_tier | VARCHAR | false | base.onet_career_transitions.relatedness_tier (verbatim) |
| is_primary | BOOLEAN | false | base.onet_career_transitions.is_primary (verbatim) |
| relationship_type | VARCHAR | false | base.onet_career_transitions.relationship_type (verbatim) |
| source_has_work_profile | BOOLEAN | false | Derived (lookup in onet_work_profiles) |
| related_has_work_profile | BOOLEAN | false | Derived (lookup in onet_work_profiles) |
| backs_feature | VARCHAR | false | Static constant ('Stage3Branching') |
| source_load_date | DATE | false | base.onet_career_transitions.source_load_date (verbatim) |
| promoted_at | TIMESTAMP | false | Generated at promotion time |

**CDE columns (2 total):** bls_soc_code, related_bls_soc_code

### 2. Data Contract Validation

**Files:** `governance/data-contracts/consumable-onet-work-profiles.yaml`, `governance/data-contracts/consumable-career-transitions.yaml`

Validated the existing data contracts produced by @cde-tagger. Findings:

- All 27 columns present in work_profiles contract (matches physical model)
- All 14 columns present in career_transitions contract (matches physical model)
- CDE flags consistent between contracts and dictionary
- Quality sections complete with thresholds for completeness, validity, uniqueness, volume, and consistency
- Breaking change policies defined (semantic versioning with 30-day deprecation)
- Consumer sections document downstream consumers (pentagon stats, boss fights, Gemma, crosswalk)
- Lineage references point to correct transformer sources

**Updates made:** Added `dq_rules` metadata (total_rules: 43, pass_rate: 100%, scorecard path) to both contracts.

### 3. README Update

**File:** `README.md`

Added:
- Gold O*NET conceptual, logical, and physical Mermaid diagrams (3 diagram blocks)
- 2 new Gold tables in the Tables section
- 7 new business glossary terms (BT-066 through BT-072) in new "Gold O*NET Terms" subsection
- Updated glossary term count from 65 to 72
- 5 new key design decisions (#16-#20) covering HMN formula, burnout weighting, activity classification, partial-data handling, and career transition semantics

### 4. Cross-Reference Verification

Verified consistency across governance artifacts:

| Artifact | Work Profiles Cols | Career Transitions Cols | Match |
|----------|-------------------|------------------------|-------|
| Physical model | 27 | 14 | Yes |
| Data contract | 27 | 14 | Yes |
| Data dictionary | 27 | 14 | Yes |

- Business term references (BT-015/016/026/027/028/054/057/059/060/061/062/063/064/066-072) verified against `governance/business-glossary.json`
- DQ rule IDs (GLD-ONP-001 through GLD-ONP-043) verified against `governance/dq-rules/gold-onet-profiles.json`
- Lineage file path verified: `governance/lineage/gold-onet-profiles-20260408T180000Z.json`
- DQ scorecard confirms 43/43 rules passing (100%)

---

## Judgment Calls and Interpretation Decisions

1. **burnout_drivers CDE designation:** The data contract and CDE tagger designated burnout_drivers as a CDE with the rationale that it provides the actionable explanation of burnout risk consumed by Gemma. The data dictionary follows this designation. This is a judgment call -- it is a derived JSON array, not a primary metric, but its role in student-facing narrative justifies CDE status.

2. **DQ rule cross-references:** Not every column has a directly mapped DQ rule. For example, description and human_activity_count have no Gold-specific DQ rules because they are validated as part of broader required-fields checks (GLD-ONP-023). The dictionary references the applicable umbrella rules rather than inventing specific mappings.

3. **confidence_tier distribution notes:** The scorecard shows 772 high + 2 medium + 24 low, while the data contract says 773 high + 1 medium + 24 low. The dictionary entry notes both SOC 29-1241 and SOC 51-2061 as edge cases. This discrepancy was documented rather than adjudicated -- the scorecard execution is the source of truth.

---

## Files Modified

| File | Action |
|------|--------|
| `governance/data-dictionary.json` | Added `consumable.onet_work_profiles` (27 cols) and `consumable.career_transitions` (14 cols) |
| `governance/data-contracts/consumable-onet-work-profiles.yaml` | Added dq_rules metadata (total_rules, pass_rate, scorecard) |
| `governance/data-contracts/consumable-career-transitions.yaml` | Added dq_rules metadata (total_rules, pass_rate, scorecard) |
| `README.md` | Added Gold O*NET models (3 diagrams), 2 tables, 7 glossary terms, 5 design decisions |
| `governance/audit-trail/gold-onet-profiles-doc-generator.md` | Created (this file) |
