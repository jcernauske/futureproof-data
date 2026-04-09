# Logical Model: gold-onet-profiles

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Domain:** Occupation Work Characteristics and Career Mobility
**Spec:** docs/specs/gold-onet-profiles.md
**Conceptual Model:** governance/models/gold-onet-profiles-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-08
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)
**Source Models:** governance/models/silver-base-onet-logical.md, governance/models/gold-occupation-profiles-bls-ooh-logical.md

---

```mermaid
erDiagram
    WORK_PROFILE {
        identifier record_id PK
        identifier bls_soc_code NK
        text primary_title
        text description
        boolean multi_detail_flag
        text data_completeness_tier
    }
    HUMAN_EDGE_ASSESSMENT {
        identifier bls_soc_code PK
        numeric hmn_score
        numeric hmn_score_rounded
        text top_human_activities
        numeric human_activity_count
    }
    BURNOUT_ASSESSMENT {
        identifier bls_soc_code PK
        numeric burnout_score
        numeric burnout_score_rounded
        text burnout_drivers
        numeric time_pressure
        numeric work_hours
        numeric consequence_of_error
    }
    ACTIVITY_PROFILE_SUMMARY {
        identifier bls_soc_code PK
        numeric activity_importance_mean
        text top_5_activities
        boolean activity_profile_available
    }
    CONTEXT_PROFILE_SUMMARY {
        identifier bls_soc_code PK
        boolean context_profile_available
    }
    DATA_QUALITY_CONTEXT {
        identifier bls_soc_code PK
        text confidence_tier
        numeric suppress_pct_activities
        numeric suppress_pct_context
    }
    FUTUREPROOF_STAT_MAPPING_WP {
        identifier bls_soc_code PK
        text backs_stats
        text backs_bosses
    }
    PIPELINE_METADATA_WP {
        identifier bls_soc_code PK
        date source_load_date
        timestamp promoted_at
    }
    CAREER_TRANSITION {
        identifier record_id PK
        identifier bls_soc_code NK
        text source_title
        identifier related_bls_soc_code NK
        text related_title
        numeric best_index
        text relatedness_tier
        boolean is_primary
        text relationship_type
        boolean source_has_work_profile
        boolean related_has_work_profile
    }
    FUTUREPROOF_STAT_MAPPING_CT {
        identifier bls_soc_code_pair PK
        text backs_feature
    }
    PIPELINE_METADATA_CT {
        identifier bls_soc_code_pair PK
        date source_load_date
        timestamp promoted_at
    }
    WORK_PROFILE ||--o| HUMAN_EDGE_ASSESSMENT : "scored by"
    WORK_PROFILE ||--o| BURNOUT_ASSESSMENT : "scored by"
    WORK_PROFILE ||--o| ACTIVITY_PROFILE_SUMMARY : "summarized by"
    WORK_PROFILE ||--o| CONTEXT_PROFILE_SUMMARY : "summarized by"
    WORK_PROFILE ||--|| DATA_QUALITY_CONTEXT : "qualified by"
    WORK_PROFILE ||--|| FUTUREPROOF_STAT_MAPPING_WP : "powers"
    WORK_PROFILE ||--|| PIPELINE_METADATA_WP : "tracked by"
    CAREER_TRANSITION }o--|| WORK_PROFILE : "transitions from"
    CAREER_TRANSITION }o--o| WORK_PROFILE : "transitions to"
    CAREER_TRANSITION ||--|| FUTUREPROOF_STAT_MAPPING_CT : "powers"
    CAREER_TRANSITION ||--|| PIPELINE_METADATA_CT : "tracked by"
```

---

## Design Rationale: Two Denormalized Tables

This spec produces two Gold tables at different grains. Following the established Gold zone pattern from `consumable.occupation_profiles` and `consumable.career_outcomes`, each table is a single denormalized surface optimized for the primary query pattern. The logical model groups attributes by conceptual entity to preserve semantic clarity while acknowledging the physical denormalization.

**Table 1: consumable.onet_work_profiles** (one row per occupation)
- All conceptual entities (Work Profile, Human Edge Assessment, Burnout Assessment, Activity Profile Summary, Context Profile Summary, Data Quality Context, FutureProof Stat Mapping) are flattened into a single row because all resolve to 1:1 or 1:0..1 per bls_soc_code.
- Dataset size (798 rows) does not benefit from normalization.
- Downstream consumers (Gemma agent, pentagon stats, boss fights) expect a single flat table per occupation.

**Table 2: consumable.career_transitions** (one row per occupation pair)
- Different grain (bls_soc_code x related_bls_soc_code), different row count (15,944), different consumers (Stage 3 branching).
- Cross-references Table 1 via has_work_profile flags but is not subordinate to it.

---

## Table 1: consumable.onet_work_profiles

### Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per occupation (bls_soc_code) |
| **Natural key fields** | `bls_soc_code` |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'wp') |
| **Uniqueness constraint** | Zero duplicates on bls_soc_code. Enforced at promote time. |
| **Expected cardinality** | 798 rows (all Silver base.onet_occupations rows carried forward; no rows added or dropped) |
| **Source tables** | `base.onet_occupations`, `base.onet_activity_profiles`, `base.onet_context_profiles` |

### Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The `NK` marker denotes natural key components.

#### Occupation Identity (Carried from Silver)

These attributes are carried forward from Silver `base.onet_occupations` without transformation.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key (bls_soc_code) using `compute_grain_id()` with prefix 'wp'. Prefix distinguishes from Silver's 'on' prefix. |
| bls_soc_code | BT-027 | identifier | NOT NULL | true | false | 6-digit BLS SOC code in XX-XXXX format. Single-field natural key. Primary join key to consumable.occupation_profiles. Carried from Silver verbatim. |
| primary_title | BT-028 | text | NOT NULL | false | false | Occupation title from O*NET. Carried from Silver verbatim. |
| description | BT-028 | text | NOT NULL | false | false | Occupation description from O*NET. Carried from Silver verbatim. |
| multi_detail_flag | BT-063 | boolean | NOT NULL | false | false | True for 76 BLS SOCs with multiple O*NET detailed codes aggregated. Carried from Silver verbatim. |
| data_completeness_tier | BT-064 | text | NOT NULL | false | false | "full" or "partial". Classifies O*NET data coverage. Carried from Silver verbatim. Input to confidence_tier derivation. |

#### Human Edge Assessment (Derived)

HMN scoring derived from pivoting Silver activity profiles. Null for 24 partial-data occupations without activity profiles.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| hmn_score | BT-066 | numeric | NULLABLE | true | false | Human Edge stat on 1-10 scale. Derived from the ratio of human-intensive activity importance to total activity importance (see Derivation Rules). Null for 24 occupations without activity profiles. Backs the HMN pentagon stat. |
| hmn_score_rounded | BT-066 | numeric | NULLABLE | false | false | Integer 1-10 for pentagon display. ROUND(hmn_score). Null if hmn_score is null. |
| top_human_activities | BT-067 | text | NULLABLE | false | false | JSON array of the top 5 human-intensive activities by importance for this occupation. Each entry contains activity name and importance value. Powers Gemma's "human edge" narrative. Null if no activity profile. |
| human_activity_count | BT-067 | numeric | NULLABLE | false | false | Count of the 41 work activities classified as human-intensive for this occupation (static classification -- same activities for all occupations, but the count reflects how many have non-trivial importance). Null if no activity profile. |

#### Burnout Assessment (Derived)

Burnout risk scoring derived from pivoting Silver context profiles. Null for same 24 partial-data occupations.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| burnout_score | BT-068 | numeric | NULLABLE | true | false | Burnout risk on 1-10 scale. Derived from normalized average of 9 burnout-relevant Work Context elements (see Derivation Rules). Higher = more burnout risk. Null for 24 occupations without context profiles. Backs the Burnout boss fight. |
| burnout_score_rounded | BT-068 | numeric | NULLABLE | false | false | Integer 1-10 for boss fight display. ROUND(burnout_score). Null if burnout_score is null. |
| burnout_drivers | BT-069 | text | NULLABLE | true | false | JSON array of the top 3 burnout-contributing context elements with their normalized values. Powers Gemma's burnout narrative. Null when burnout_score is null. |
| time_pressure | BT-059 | numeric | NULLABLE | false | false | Individual burnout element: Time Pressure (CX scale, 1-5). Direct from Silver context profile for element 4.C.3.d.1. Null if no context profile. |
| work_hours | BT-059 | numeric | NULLABLE | false | false | Individual burnout element: Duration of Typical Work Week (CT scale, 1-3). Direct from Silver context profile for element 4.C.3.d.8. Null if no context profile. |
| consequence_of_error | BT-059 | numeric | NULLABLE | false | false | Individual burnout element: Consequence of Error (CX scale, 1-5). Direct from Silver context profile for element 4.C.3.a.1. Null if no context profile. |

#### Activity Profile Summary (Derived)

Summary statistics from pivoting Silver activity profiles.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| activity_importance_mean | BT-072 | numeric | NULLABLE | false | false | Arithmetic mean of all 41 IM importance values for this occupation. Measures overall "activity intensity." Null when no activity profile data. |
| top_5_activities | BT-057 | text | NULLABLE | false | false | JSON array of the 5 highest-importance activities (name + importance value). Powers Gemma career descriptions. Null if no activity profile. |
| activity_profile_available | BT-064 | boolean | NOT NULL | false | false | True if base.onet_activity_profiles has rows for this SOC. False for 24 partial-data occupations. |

#### Context Profile Summary (Derived)

Availability flag for context profile data.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| context_profile_available | BT-064 | boolean | NOT NULL | false | false | True if base.onet_context_profiles has rows for this SOC. False for same 24 partial-data occupations. |

#### Data Quality Context (Derived)

Quality classification and suppression metrics. confidence_tier is required on every row (no nulls).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| confidence_tier | BT-071 | text | NOT NULL | false | false | Three-level data quality classification: "high" (full data, low suppression), "medium" (full data, elevated suppression), "low" (partial data). Every row receives a tier. See Derivation Rules. |
| suppress_pct_activities | BT-062 | numeric | NULLABLE | false | false | Percentage of activity profile rows with suppress_flag = True for this occupation. Null if no activity profile. Input to confidence_tier. |
| suppress_pct_context | BT-062 | numeric | NULLABLE | false | false | Percentage of context profile rows with suppress_flag = True for this occupation. Null if no context profile. Input to confidence_tier. |

#### FutureProof Stat Mapping (Static)

Documentation metadata declaring which FutureProof game-system elements this data product backs.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| backs_stats | BT-054 | text | NOT NULL | false | false | Comma-separated list of FutureProof pentagon stats. Always "HMN" for all rows in this table. |
| backs_bosses | BT-054 | text | NOT NULL | false | false | Comma-separated list of boss fights. Always "AI,Burnout" for all rows in this table. |

#### Pipeline Metadata

Pipeline infrastructure fields. source_load_date carried from Silver; promoted_at generated at promotion time.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the raw zone. Pipeline metadata carried from Silver. |
| promoted_at | BT-026 | timestamp | NOT NULL | false | false | Timestamp when the row was promoted to the Gold zone consumable table. Generated at promotion time. |

---

## Table 2: consumable.career_transitions

### Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per occupation pair (bls_soc_code x related_bls_soc_code) |
| **Natural key fields** | `bls_soc_code`, `related_bls_soc_code` |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'tr') |
| **Uniqueness constraint** | Zero duplicates on (bls_soc_code, related_bls_soc_code). No self-references. Enforced at promote time. |
| **Expected cardinality** | 15,944 rows (carried from Silver, enriched) |
| **Source tables** | `base.onet_career_transitions`, `base.onet_occupations`, `consumable.onet_work_profiles` |

### Attribute Definitions

#### Career Transition Identity (Carried + Enriched)

Core transition fields carried from Silver, enriched with titles from base.onet_occupations.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the composite natural key (bls_soc_code, related_bls_soc_code) using `compute_grain_id()` with prefix 'tr'. |
| bls_soc_code | BT-027 | identifier | NOT NULL | true | false | Source occupation SOC code. Part of composite natural key. Carried from Silver verbatim. |
| source_title | BT-028 | text | NOT NULL | false | false | Source occupation title. Enriched by joining base.onet_occupations on bls_soc_code. |
| related_bls_soc_code | BT-027 | identifier | NOT NULL | true | false | Related/target occupation SOC code. Part of composite natural key. Carried from Silver verbatim. |
| related_title | BT-028 | text | NOT NULL | false | false | Related occupation title. Enriched by joining base.onet_occupations on related_bls_soc_code. |

#### Similarity Classification (Carried from Silver)

Relatedness measures and classification carried from Silver without transformation.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| best_index | BT-061 | numeric | NOT NULL | false | false | Similarity rank (1 = most similar). Integer 1-20. Carried from Silver verbatim. |
| relatedness_tier | BT-061 | text | NOT NULL | false | false | Three-level classification: "Primary-Short" (index 1-5), "Primary-Long" (6-10), "Supplemental" (11-20). Carried from Silver verbatim. |
| is_primary | BT-061 | boolean | NOT NULL | false | false | True for Primary-Short or Primary-Long. Convenience flag. Carried from Silver verbatim. |
| relationship_type | BT-060 | text | NOT NULL | false | false | Always "similarity". Indicates these are skill-similarity relationships, not observed career transitions. Carried from Silver verbatim. |

#### Work Profile Availability (Derived)

Cross-table reference flags indicating whether each occupation in the pair has a full work profile in consumable.onet_work_profiles.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_has_work_profile | BT-070 | boolean | NOT NULL | false | false | True if bls_soc_code exists in consumable.onet_work_profiles with full data (activity_profile_available = True). Derived by cross-table lookup. |
| related_has_work_profile | BT-070 | boolean | NOT NULL | false | false | True if related_bls_soc_code exists in consumable.onet_work_profiles with full data (activity_profile_available = True). Derived by cross-table lookup. |

#### FutureProof Stat Mapping (Static)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| backs_feature | BT-054 | text | NOT NULL | false | false | FutureProof feature backed by this data. Always "Stage3Branching" for all rows. |

#### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the raw zone. Pipeline metadata carried from Silver. |
| promoted_at | BT-026 | timestamp | NOT NULL | false | false | Timestamp when the row was promoted to the Gold zone consumable table. Generated at promotion time. |

---

## Attribute Summary

### Table 1: consumable.onet_work_profiles

| Count | Category |
|-------|----------|
| 26 | Total attributes |
| 1 | Natural key component (bls_soc_code) |
| 1 | Surrogate key (record_id) |
| 4 | CDE attributes (bls_soc_code, hmn_score, burnout_score, burnout_drivers) |
| 0 | PII attributes |
| 13 | Nullable attributes |
| 13 | NOT NULL attributes |
| 16 | Derived attributes (record_id, hmn_score, hmn_score_rounded, top_human_activities, human_activity_count, burnout_score, burnout_score_rounded, burnout_drivers, time_pressure, work_hours, consequence_of_error, activity_importance_mean, top_5_activities, activity_profile_available, context_profile_available, confidence_tier, suppress_pct_activities, suppress_pct_context, backs_stats, backs_bosses) |
| 4 | Carried from Silver verbatim (primary_title, description, multi_detail_flag, data_completeness_tier) |
| 2 | Pipeline metadata (source_load_date carried, promoted_at new) |

### Table 2: consumable.career_transitions

| Count | Category |
|-------|----------|
| 14 | Total attributes |
| 2 | Natural key components (bls_soc_code, related_bls_soc_code) |
| 1 | Surrogate key (record_id) |
| 2 | CDE attributes (bls_soc_code, related_bls_soc_code) |
| 0 | PII attributes |
| 0 | Nullable attributes |
| 14 | NOT NULL attributes |
| 4 | Derived attributes (record_id, source_has_work_profile, related_has_work_profile, backs_feature) |
| 8 | Carried/enriched from Silver (source_title, related_title, best_index, relatedness_tier, is_primary, relationship_type, bls_soc_code, related_bls_soc_code) |
| 2 | Pipeline metadata (source_load_date carried, promoted_at new) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR |
| text | A human-readable label, description, or JSON-encoded structure. Not used for joins. | VARCHAR |
| numeric | A quantitative measure, count, ratio, rank, or score. May be aggregated. | DOUBLE (scores, ratios, percentages), INTEGER (counts, ranks) |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

All derivation rules are null-safe. Null inputs propagate to null outputs unless otherwise specified.

### Surrogate Keys

| Attribute | Table | Rule | Source Attributes |
|-----------|-------|------|-------------------|
| record_id | Work Profiles | `compute_grain_id(row, ['bls_soc_code'], prefix='wp')` | bls_soc_code |
| record_id | Career Transitions | `compute_grain_id(row, ['bls_soc_code', 'related_bls_soc_code'], prefix='tr')` | bls_soc_code, related_bls_soc_code |

### Carried from Silver (no transformation)

| Attribute | Table | Source | Rule |
|-----------|-------|--------|------|
| bls_soc_code | Work Profiles | base.onet_occupations.bls_soc_code | Verbatim |
| primary_title | Work Profiles | base.onet_occupations.primary_title | Verbatim |
| description | Work Profiles | base.onet_occupations.description | Verbatim |
| multi_detail_flag | Work Profiles | base.onet_occupations.multi_detail_flag | Verbatim |
| data_completeness_tier | Work Profiles | base.onet_occupations.data_completeness_tier | Verbatim |
| source_load_date | Work Profiles | base.onet_occupations.source_load_date | Verbatim |
| bls_soc_code | Career Transitions | base.onet_career_transitions.bls_soc_code | Verbatim |
| related_bls_soc_code | Career Transitions | base.onet_career_transitions.related_bls_soc_code | Verbatim |
| best_index | Career Transitions | base.onet_career_transitions.best_index | Verbatim |
| relatedness_tier | Career Transitions | base.onet_career_transitions.relatedness_tier | Verbatim |
| is_primary | Career Transitions | base.onet_career_transitions.is_primary | Verbatim |
| relationship_type | Career Transitions | base.onet_career_transitions.relationship_type | Verbatim |
| source_load_date | Career Transitions | base.onet_career_transitions.source_load_date | Verbatim |

### Enriched from Silver (join-derived)

| Attribute | Table | Source | Rule |
|-----------|-------|--------|------|
| source_title | Career Transitions | base.onet_occupations.primary_title | JOIN base.onet_occupations ON career_transitions.bls_soc_code = occupations.bls_soc_code |
| related_title | Career Transitions | base.onet_occupations.primary_title | JOIN base.onet_occupations ON career_transitions.related_bls_soc_code = occupations.bls_soc_code |

### HMN Score Derivation (1-10 Scale)

The Human Edge stat measures how much an occupation depends on distinctly human skills. The derivation is a 4-step process applied per occupation.

**Step 1: Classify activities (static, same for all occupations)**

14 of the 41 Generalized Work Activities are classified as "human-intensive" based on requiring judgment, creativity, interpersonal skill, or physical presence. The classification list (Open Decision #1, pending human approval):

| Element ID | Activity Name | Category |
|-----------|--------------|----------|
| 4.A.4.a.1 | Guiding, Directing, and Motivating Subordinates | Leadership |
| 4.A.4.a.2 | Coaching and Developing Others | Mentorship |
| 4.A.4.a.4 | Resolving Conflicts and Negotiating with Others | Judgment |
| 4.A.4.a.5 | Performing for or Working Directly with the Public | Physical/Social |
| 4.A.4.a.8 | Establishing and Maintaining Interpersonal Relationships | Relationship |
| 4.A.4.b.4 | Developing and Building Teams | Leadership |
| 4.A.4.b.5 | Training and Teaching Others | Interpersonal |
| 4.A.4.b.6 | Selling or Influencing Others | Persuasion |
| 4.A.4.a.1 | Coordinating the Work and Activities of Others | Coordination |
| 4.A.2.b.2 | Thinking Creatively | Creativity |
| 4.A.2.b.4 | Making Decisions and Solving Problems | Judgment |
| 4.A.1.e.2 | Performing General Physical Activities | Physical |
| 4.A.3.a.3 | Handling and Moving Objects | Physical |
| 4.A.3.b.5 | Assisting and Caring for Others | Empathy |

**Note:** Element IDs must be validated against actual Silver data at implementation time. The spec flags that some IDs may be incorrect -- the element_name field is authoritative.

**Step 2: Compute importance sums**

For each occupation with activity profile data:
- `human_importance_sum` = SUM(importance_value) WHERE element_id IN human_intensive_list
- `total_importance_sum` = SUM(importance_value) for all 41 activities

**Step 3: Compute ratio**

- `human_ratio` = human_importance_sum / total_importance_sum (range: 0.0-1.0)

**Step 4: Map to 1-10 scale**

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| hmn_score | `1.0 + 9.0 * human_ratio` | All 41 activity importance values | Null if occupation has no activity profile (24 rows) |
| hmn_score_rounded | `ROUND(hmn_score)` (standard rounding, 0 decimal places) | hmn_score | Null if hmn_score is null |

**Scale interpretation:**
- HMN 10.0 = all of the occupation's important activities are human-intensive
- HMN 5.5 = roughly equal human and automatable importance
- HMN 1.0 = all important activities are automatable

### Top Human Activities Derivation

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| top_human_activities | JSON array of top 5 human-intensive activities ranked by importance_value DESC. Each entry: `{"activity": element_name, "importance": importance_value}`. If fewer than 5 human-intensive activities have data, include all available. | base.onet_activity_profiles WHERE element_id IN human_intensive_list | Null if no activity profile |

### Human Activity Count Derivation

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| human_activity_count | COUNT of the 14 human-intensive element IDs that have rows in the activity profile. In practice, this is always 14 when activity data is present (all occupations are rated on all 41 activities). | base.onet_activity_profiles WHERE element_id IN human_intensive_list | Null if no activity profile |

### Burnout Score Derivation (1-10 Scale)

Combines 9 burnout-relevant Work Context elements into a single burnout risk score. The derivation is a 3-step process.

**Step 1: Retrieve the 9 burnout elements**

| Element ID | Element Name | Scale | Range | Burnout Direction |
|-----------|-------------|-------|-------|-------------------|
| 4.C.3.d.1 | Time Pressure | CX | 1-5 | Higher = more stress |
| 4.C.3.d.8 | Duration of Typical Work Week | CT | 1-3 | Higher = longer hours |
| 4.C.3.a.1 | Consequence of Error | CX | 1-5 | Higher = more pressure |
| 4.C.3.d.3 | Pace Determined by Speed of Equipment | CX | 1-5 | Higher = less autonomy |
| 4.C.3.a.2.b | Frequency of Decision Making | CX | 1-5 | Higher = cognitive load |
| 4.C.3.b.4 | Importance of Being Exact or Accurate | CX | 1-5 | Higher = precision pressure |
| 4.C.3.b.7 | Responsibility for Outcomes and Results | CX | 1-5 | Higher = stakes pressure |
| 4.C.3.d.4 | Importance of Repeating Same Tasks | CX | 1-5 | Higher = monotony |
| 4.C.3.a.2.a | Responsibility for Others' Health and Safety | CX | 1-5 | Higher = stakes pressure |

**Step 2: Normalize each element to 0-1 scale**

| Scale Type | Normalization Formula |
|-----------|----------------------|
| CX (1-5) | `normalized = (value - 1.0) / 4.0` |
| CT (1-3) | `normalized = (value - 1.0) / 2.0` |

**Step 3: Compute burnout score**

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| burnout_score | `1.0 + 9.0 * MEAN(normalized values for all 9 elements)` Equal weighting (Open Decision #2, pending human approval). | 9 burnout element context_values | Null if occupation has no context profile (24 rows) |
| burnout_score_rounded | `ROUND(burnout_score)` (standard rounding, 0 decimal places) | burnout_score | Null if burnout_score is null |

**Scale interpretation:**
- Burnout 10.0 = maximum on all burnout indicators
- Burnout 5.5 = moderate burnout risk
- Burnout 1.0 = minimum burnout risk

### Burnout Drivers Derivation

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| burnout_drivers | JSON array of the top 3 burnout elements ranked by normalized_value DESC. Each entry: `{"element": element_name, "value": normalized_value}`. | 9 burnout element normalized values | Null if burnout_score is null |

### Individual Burnout Element Extraction

Direct extraction of specific context values from Silver. No transformation except pivot.

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| time_pressure | context_value WHERE element_id = '4.C.3.d.1' | base.onet_context_profiles | Null if no context profile |
| work_hours | context_value WHERE element_id = '4.C.3.d.8' | base.onet_context_profiles | Null if no context profile |
| consequence_of_error | context_value WHERE element_id = '4.C.3.a.1' | base.onet_context_profiles | Null if no context profile |

### Activity Profile Summary Derivation

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| activity_importance_mean | `MEAN(importance_value) for all 41 activities` | base.onet_activity_profiles | Null if no activity profile |
| top_5_activities | JSON array of 5 highest-importance activities ranked by importance_value DESC. Each entry: `{"activity": element_name, "importance": importance_value}`. | base.onet_activity_profiles | Null if no activity profile |
| activity_profile_available | `True if COUNT(*) > 0 in base.onet_activity_profiles for this bls_soc_code, else False` | base.onet_activity_profiles | Never null (always True or False) |

### Context Profile Summary Derivation

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| context_profile_available | `True if COUNT(*) > 0 in base.onet_context_profiles for this bls_soc_code, else False` | base.onet_context_profiles | Never null (always True or False) |

### Confidence Tier Derivation

Evaluated top-to-bottom; first matching condition wins. Every row receives a tier (no nulls).

| Tier Value | Condition | Business Interpretation |
|------------|-----------|------------------------|
| "high" | data_completeness_tier = "full" AND suppress_pct_activities < 5.0 AND suppress_pct_context < 5.0 | Full O*NET coverage with minimal data quality flags. Highest guidance quality. |
| "medium" | data_completeness_tier = "full" AND (suppress_pct_activities >= 5.0 OR suppress_pct_context >= 5.0) | Full O*NET coverage but elevated suppression rates in underlying ratings. Scores are present but may have reduced precision. |
| "low" | data_completeness_tier = "partial" | Partial O*NET coverage. HMN and/or Burnout scores may be null. Weakest data for FutureProof. |

**Distribution expectation:** "high" is the majority (occupations with full data and low suppression). "low" count: approximately 24 (the partial-data occupations). "medium" depends on actual suppression rates.

**Null handling for suppress_pct fields in tier logic:** When data_completeness_tier = "partial", the suppress_pct fields may be null (no profile data to compute suppression for). The tier evaluates to "low" on the data_completeness_tier check before reaching the suppression conditions.

### Suppress Percentage Derivation

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| suppress_pct_activities | `100.0 * COUNT(WHERE suppress_flag = True) / COUNT(*) for this bls_soc_code` | base.onet_activity_profiles | Null if no activity profile (24 rows) |
| suppress_pct_context | `100.0 * COUNT(WHERE suppress_flag = True) / COUNT(*) for this bls_soc_code` | base.onet_context_profiles | Null if no context profile (24 rows) |

### Work Profile Availability Flags (Career Transitions)

Cross-table derivation: Table 2 checks Table 1 for work profile existence.

| Attribute | Rule | Source | Null Condition |
|-----------|------|--------|----------------|
| source_has_work_profile | `True if bls_soc_code EXISTS in consumable.onet_work_profiles WHERE activity_profile_available = True` | consumable.onet_work_profiles | Never null (always True or False) |
| related_has_work_profile | `True if related_bls_soc_code EXISTS in consumable.onet_work_profiles WHERE activity_profile_available = True` | consumable.onet_work_profiles | Never null (always True or False) |

### Static Fields

| Attribute | Table | Rule | Value |
|-----------|-------|------|-------|
| backs_stats | Work Profiles | Static string, same for all 798 rows | "HMN" |
| backs_bosses | Work Profiles | Static string, same for all 798 rows | "AI,Burnout" |
| backs_feature | Career Transitions | Static string, same for all 15,944 rows | "Stage3Branching" |

### Pipeline Metadata

| Attribute | Table | Rule | Source |
|-----------|-------|------|--------|
| promoted_at | Both tables | Current timestamp at promotion time | Generated by promote() function |

---

## Nullability Semantics

Null values in this model carry specific business meaning:

### Table 1: consumable.onet_work_profiles

| Pattern | Business Meaning | Affected Rows |
|---------|-----------------|---------------|
| hmn_score IS NULL | Occupation lacks O*NET activity profile data (partial-data occupation). Cannot compute Human Edge. | 24 |
| hmn_score_rounded IS NULL | Propagated from hmn_score null. | 24 |
| top_human_activities IS NULL | Same 24 occupations. No activity data to rank. | 24 |
| human_activity_count IS NULL | Same 24 occupations. | 24 |
| burnout_score IS NULL | Occupation lacks O*NET context profile data. Cannot compute burnout risk. | 24 |
| burnout_score_rounded IS NULL | Propagated from burnout_score null. | 24 |
| burnout_drivers IS NULL | Same 24 occupations. | 24 |
| time_pressure IS NULL | Same 24 occupations. No context profile to extract from. | 24 |
| work_hours IS NULL | Same 24 occupations. | 24 |
| consequence_of_error IS NULL | Same 24 occupations. | 24 |
| activity_importance_mean IS NULL | Same 24 occupations. | 24 |
| top_5_activities IS NULL | Same 24 occupations. | 24 |
| suppress_pct_activities IS NULL | Same 24 occupations. No activity rows to measure suppression. | 24 |
| suppress_pct_context IS NULL | Same 24 occupations. No context rows to measure suppression. | 24 |

**Key invariant:** The same 24 partial-data occupations have ALL nullable fields as null. There is no case where an occupation has activity data but not context data, or vice versa, in the current O*NET 30.2 dataset. confidence_tier = "low" if and only if data_completeness_tier = "partial". When confidence_tier = "low", all score fields are guaranteed null.

### Table 2: consumable.career_transitions

All 14 attributes are NOT NULL. Every career transition row has complete data because:
- Source and related SOC codes are required by the Silver grain
- Titles come from inner joins to base.onet_occupations (all SOCs in career transitions exist in occupations)
- Similarity fields are carried from Silver which enforces completeness
- Work profile availability flags default to False (not null) when a SOC is not found

---

## Dropped Fields (from Silver, with justification)

### From base.onet_occupations

| Silver Attribute | Dropped? | Justification |
|-----------------|----------|---------------|
| record_id (prefix 'on') | Recomputed | Prefix changes from Silver's 'on' to Gold's 'wp' to distinguish zones. |
| onet_soc_codes | Dropped | O*NET detail codes not needed by Gold consumers. BLS SOC code is the join key. Available in Silver if needed. |
| detail_count | Dropped | Subsumed by multi_detail_flag boolean. Count available in Silver. |
| ingested_at | Dropped | Silver metadata replaced by promoted_at in Gold. |

### From base.onet_activity_profiles / base.onet_context_profiles

These Silver tables are pivoted (many-to-one aggregation), not carried. The 41 activity rows and 57 context rows per occupation are collapsed into summary fields on a single work profile row.

| Silver Attribute | Gold Disposition | Notes |
|-----------------|-----------------|-------|
| element_id | Absorbed | Used as filter/group key during pivot. Not persisted in Gold. |
| element_name | Absorbed | Used for JSON array content (activity names). Not a standalone Gold field. |
| importance_value | Absorbed | Aggregated into hmn_score, activity_importance_mean, top_5_activities. |
| importance_rank | Absorbed | Used for top-5 ranking. Not persisted separately in Gold. |
| context_value | Absorbed | Aggregated into burnout_score, individual elements. |
| scale_id | Absorbed | Used for normalization logic (CX vs CT). Not persisted in Gold. |
| suppress_flag | Absorbed | Aggregated into suppress_pct_activities / suppress_pct_context. |
| burnout_flag | Absorbed | Used as element filter for burnout derivation. Not persisted in Gold. |
| ingested_at | Dropped | Silver metadata replaced by promoted_at in Gold. |

### From base.onet_career_transitions

| Silver Attribute | Dropped? | Justification |
|-----------------|----------|---------------|
| record_id (prefix 'on') | Recomputed | Prefix changes from Silver's 'on' to Gold's 'tr'. |
| ingested_at | Dropped | Silver metadata replaced by promoted_at in Gold. |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attribute Group | Table | Attributes | Notes |
|-------------------|------------------------|-------|------------|-------|
| Occupation Identity | Occupation Identity | Work Profiles | record_id, bls_soc_code, primary_title, description, multi_detail_flag, data_completeness_tier | Core identity. bls_soc_code is the natural key. |
| Human Edge Assessment | Human Edge Assessment | Work Profiles | hmn_score, hmn_score_rounded, top_human_activities, human_activity_count | Derived from pivoting 41 activity rows per occupation. |
| Burnout Assessment | Burnout Assessment | Work Profiles | burnout_score, burnout_score_rounded, burnout_drivers, time_pressure, work_hours, consequence_of_error | Derived from pivoting 9 burnout-relevant context elements. |
| Work Profile (activity summary) | Activity Profile Summary | Work Profiles | activity_importance_mean, top_5_activities, activity_profile_available | Activity data availability and summary stats. |
| Work Profile (context summary) | Context Profile Summary | Work Profiles | context_profile_available | Context data availability flag. |
| Data Quality Context | Data Quality Context | Work Profiles | confidence_tier, suppress_pct_activities, suppress_pct_context | Derived from completeness tier and suppression rates. |
| FutureProof Stat Mapping | FutureProof Stat Mapping (WP) | Work Profiles | backs_stats, backs_bosses | Static: "HMN" and "AI,Burnout". |
| Career Transition | Career Transition Identity + Similarity Classification + Work Profile Availability | Career Transitions | record_id, bls_soc_code, source_title, related_bls_soc_code, related_title, best_index, relatedness_tier, is_primary, relationship_type, source_has_work_profile, related_has_work_profile | Enriched from Silver with titles and work profile flags. |
| FutureProof Stat Mapping | FutureProof Stat Mapping (CT) | Career Transitions | backs_feature | Static: "Stage3Branching". |
| (Pipeline Metadata) | Pipeline Metadata | Both tables | source_load_date, promoted_at | Not a conceptual entity -- pipeline infrastructure. |

---

## Continuity with Silver Logical Model

This logical model builds on the Silver O*NET logical model (`governance/models/silver-base-onet-logical.md`):

### base.onet_occupations -> consumable.onet_work_profiles

| Silver Attribute | Gold Disposition | Gold Attribute | Change |
|-----------------|-----------------|----------------|--------|
| record_id (prefix 'on') | Recomputed | record_id (prefix 'wp') | Prefix changes to distinguish zones |
| bls_soc_code | Carried | bls_soc_code | Verbatim |
| primary_title | Carried | primary_title | Verbatim |
| description | Carried | description | Verbatim |
| multi_detail_flag | Carried | multi_detail_flag | Verbatim |
| data_completeness_tier | Carried | data_completeness_tier | Verbatim |
| onet_soc_codes | Dropped | -- | Not needed by Gold consumers |
| detail_count | Dropped | -- | Subsumed by multi_detail_flag |
| source_load_date | Carried | source_load_date | Verbatim |
| ingested_at | Dropped | -- | Replaced by promoted_at |

### base.onet_activity_profiles -> consumable.onet_work_profiles (pivot aggregation)

| Silver Table | Gold Derivation | Gold Attributes |
|-------------|-----------------|-----------------|
| 41 rows per occupation | Pivoted to 1 row | hmn_score, hmn_score_rounded, top_human_activities, human_activity_count, activity_importance_mean, top_5_activities, activity_profile_available, suppress_pct_activities |

### base.onet_context_profiles -> consumable.onet_work_profiles (pivot aggregation)

| Silver Table | Gold Derivation | Gold Attributes |
|-------------|-----------------|-----------------|
| 57 rows per occupation (9 burnout-relevant) | Pivoted to 1 row | burnout_score, burnout_score_rounded, burnout_drivers, time_pressure, work_hours, consequence_of_error, context_profile_available, suppress_pct_context |

### base.onet_career_transitions -> consumable.career_transitions (enrichment)

| Silver Attribute | Gold Disposition | Gold Attribute | Change |
|-----------------|-----------------|----------------|--------|
| record_id (prefix 'on') | Recomputed | record_id (prefix 'tr') | Prefix changes |
| bls_soc_code | Carried | bls_soc_code | Verbatim |
| related_bls_soc_code | Carried | related_bls_soc_code | Verbatim |
| best_index | Carried | best_index | Verbatim |
| relatedness_tier | Carried | relatedness_tier | Verbatim |
| is_primary | Carried | is_primary | Verbatim |
| relationship_type | Carried | relationship_type | Verbatim |
| source_load_date | Carried | source_load_date | Verbatim |
| ingested_at | Dropped | -- | Replaced by promoted_at |
| -- | New (enriched) | source_title | Joined from base.onet_occupations |
| -- | New (enriched) | related_title | Joined from base.onet_occupations |
| -- | New (derived) | source_has_work_profile | Cross-table lookup to Table 1 |
| -- | New (derived) | related_has_work_profile | Cross-table lookup to Table 1 |
| -- | New (static) | backs_feature | "Stage3Branching" |

---

## Open Decisions Affecting This Model

Three spec-level decisions that affect score derivation are flagged for human approval. The logical model documents the proposed approach for each; the implementing agent should use the approved version.

| # | Decision | Proposed Approach | Impact on Logical Model |
|---|----------|-------------------|------------------------|
| 1 | Human-intensive activity classification | 14 activities classified as human-intensive (see HMN derivation table above) | Changes which activities contribute to human_importance_sum. Directly affects hmn_score for all 774 scored occupations. |
| 2 | Burnout weighting | All 9 elements equally weighted (simple average) | Changing to differential weights would modify the burnout_score formula from MEAN to WEIGHTED_MEAN. The logical attribute definition is agnostic -- the derivation rule section would change. |
| 3 | HMN formula (ratio vs. absolute) | Ratio-based: human_importance_sum / total_importance_sum | Changing to absolute would modify hmn_score to use only the human_importance_sum, removing the normalization. This would favor occupations with high overall activity importance. |

---

## Cross-Table Join Keys

| From Table | To Table | Join Key | Cardinality | Purpose |
|-----------|----------|----------|-------------|---------|
| consumable.onet_work_profiles | consumable.occupation_profiles | bls_soc_code = soc_code | 1:0..1 | Complementary Gold products at same grain. Together provide all pentagon stats. |
| consumable.career_transitions | consumable.onet_work_profiles | bls_soc_code | Many:1 | Source occupation work profile |
| consumable.career_transitions | consumable.onet_work_profiles | related_bls_soc_code = bls_soc_code | Many:0..1 | Related occupation work profile (may not exist) |
| consumable.career_transitions | consumable.occupation_profiles | bls_soc_code = soc_code | Many:0..1 | Source occupation BLS profile |
| consumable.career_transitions | consumable.occupation_profiles | related_bls_soc_code = soc_code | Many:0..1 | Related occupation BLS profile |

**Note:** The join between onet_work_profiles and occupation_profiles is not used in this spec but is the design intent for downstream unified products. Both tables are at the same SOC-code grain and are designed to be joined.
