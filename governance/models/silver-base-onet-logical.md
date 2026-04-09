# Logical Model: silver-base-onet

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** Occupational Characteristics and Career Pathways
**Spec:** docs/specs/silver-base-onet.md
**Conceptual Model:** governance/models/silver-base-onet-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-08
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    ONET_OCCUPATIONS {
        identifier record_id PK
        identifier bls_soc_code NK
        text primary_title
        text description
        text onet_detail_codes
        numeric onet_detail_count
        boolean multi_detail_flag
        boolean has_work_activities
        boolean has_work_context
        boolean has_tasks
        boolean has_related
        text data_completeness_tier
        date source_load_date
        timestamp ingested_at
    }

    ONET_ACTIVITY_PROFILES {
        identifier record_id PK
        identifier bls_soc_code FK
        identifier element_id NK
        text element_name
        numeric importance
        numeric importance_rank
        boolean is_high_importance
        numeric onet_details_averaged
        boolean suppress_flag
        date source_load_date
        timestamp ingested_at
    }

    ONET_CONTEXT_PROFILES {
        identifier record_id PK
        identifier bls_soc_code FK
        identifier element_id NK
        text element_name
        identifier scale_id
        numeric context_value
        boolean is_burnout_element
        numeric onet_details_averaged
        boolean suppress_flag
        date source_load_date
        timestamp ingested_at
    }

    ONET_CAREER_TRANSITIONS {
        identifier record_id PK
        identifier bls_soc_code FK
        identifier related_bls_soc_code FK
        numeric best_index
        text relatedness_tier
        boolean is_primary
        text relationship_type
        date source_load_date
        timestamp ingested_at
    }

    ONET_OCCUPATIONS ||--o{ ONET_ACTIVITY_PROFILES : "rated on"
    ONET_OCCUPATIONS ||--o{ ONET_CONTEXT_PROFILES : "measured by"
    ONET_OCCUPATIONS ||--o{ ONET_CAREER_TRANSITIONS : "transitions from"
    ONET_OCCUPATIONS ||--o{ ONET_CAREER_TRANSITIONS : "transitions to"
```

---

## Design Rationale: Four Separate Tables

Unlike the BLS OOH model (single denormalized table with 1:1 entities), this model requires four separate tables because:

1. **Different grains.** Occupations are keyed by bls_soc_code alone, while Activity Profiles and Context Profiles are keyed by bls_soc_code x element_id, and Career Transitions by bls_soc_code x related_bls_soc_code. These are genuinely different units of analysis.
2. **Different row counts.** ~867 occupations, ~35,500 activity profiles, ~49,400 context profiles, ~17,000 career transitions. Denormalizing would create massive redundancy.
3. **Different downstream consumers.** Activity Profiles feed HMN stat, Context Profiles feed Burnout boss fight, Career Transitions feed Stage 3 branching. Each Gold consumer joins to only the table it needs.
4. **Star-like topology.** Occupations is the central dimension; the other three are fact-like tables referencing it via bls_soc_code.

---

## Grain and Uniqueness

| Table | Grain Fields | Surrogate Key | Expected Rows |
|-------|-------------|---------------|---------------|
| onet_occupations | bls_soc_code | record_id (prefix 'on') | ~867 |
| onet_activity_profiles | bls_soc_code, element_id | record_id (prefix 'wa') | ~35,547 |
| onet_context_profiles | bls_soc_code, element_id | record_id (prefix 'wc') | ~49,419 |
| onet_career_transitions | bls_soc_code, related_bls_soc_code | record_id (prefix 'ct') | ~16,000-18,000 |

All surrogate keys are computed via `compute_grain_id(row, grain_fields, prefix=...)`. Zero duplicates enforced on grain fields at load time.

---

## Table 1: onet_occupations

Master O*NET occupation reference at BLS SOC granularity (XX-XXXX). Aggregated from one or more O*NET detailed codes (XX-XXXX.XX).

### Attributes

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from bls_soc_code using `compute_grain_id()` with prefix 'on'. Stable across pipeline re-runs. |
| bls_soc_code | BT-027 | identifier | NOT NULL | true | false | 6-digit BLS SOC code (XX-XXXX), truncated from O*NET-SOC. Single-field natural key. Primary join key for BLS OOH and CIP-SOC crosswalk. |
| primary_title | BT-028 | text | NOT NULL | false | false | Title of the .00 base code, or first detailed code's title if no .00 exists. Human-readable occupation name. |
| description | -- | text | NOT NULL | false | false | Description of the .00 base code. Provides the occupation's functional summary from O*NET. |
| onet_detail_codes | BT-055 | text | NOT NULL | false | false | JSON array of all O*NET-SOC codes (XX-XXXX.XX) that map to this BLS SOC. Preserves full O*NET lineage. |
| onet_detail_count | BT-063 | numeric | NOT NULL | false | false | Count of O*NET detailed codes mapping to this BLS SOC. 1 for simple mapping, 2+ for multi-detail. |
| multi_detail_flag | BT-063 | boolean | NOT NULL | false | false | True when onet_detail_count > 1. Exactly 76 BLS SOCs have this flag set. Signals that numeric ratings in child tables are averaged across details. |
| has_work_activities | BT-064 | boolean | NOT NULL | false | false | True if ANY O*NET detail code for this BLS SOC has Work Activities data in Bronze. |
| has_work_context | BT-064 | boolean | NOT NULL | false | false | True if ANY O*NET detail code for this BLS SOC has Work Context data in Bronze. |
| has_tasks | BT-064 | boolean | NOT NULL | false | false | True if ANY O*NET detail code for this BLS SOC has Task Statements in Bronze. |
| has_related | BT-064 | boolean | NOT NULL | false | false | True if ANY O*NET detail code for this BLS SOC has Related Occupations in Bronze. |
| data_completeness_tier | BT-064 | text | NOT NULL | true | false | "full" (all 4 data types present), "partial" (some present), "none" (excluded from Silver). Valid values: {"full", "partial"}. |
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. |

---

## Table 2: onet_activity_profiles

Work Activity importance ratings per occupation at BLS SOC granularity. Backs the HMN (Human Edge) stat. One row per occupation per Generalized Work Activity, IM (Importance) scale only.

### Attributes

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from bls_soc_code + element_id using `compute_grain_id()` with prefix 'wa'. |
| bls_soc_code | BT-027 | identifier | NOT NULL | true | false | 6-digit BLS SOC code. FK to onet_occupations.bls_soc_code. Every value must exist in the parent table. |
| element_id | BT-056 | identifier | NOT NULL | true | false | Content Model element ID (e.g., "4.A.1.a.1"). Part of composite natural key. Exactly 41 distinct values. |
| element_name | -- | text | NOT NULL | false | false | Human-readable activity name (e.g., "Getting Information"). Denormalized from Bronze for query convenience. |
| importance | BT-057 | numeric | NOT NULL | true | false | IM scale data_value, averaged across O*NET details if multi-detail. Range: 1.0-5.0. Primary input for HMN scoring. |
| importance_rank | BT-065 | numeric | NOT NULL | false | false | Rank of this activity within the occupation (1 = most important, 41 = least). Derived by ranking importance descending within each bls_soc_code. |
| is_high_importance | -- | boolean | NOT NULL | false | false | True if importance >= 3.5. Convenience threshold flag identifying activities in the top ~40% of the 1-5 scale. |
| onet_details_averaged | BT-063 | numeric | NOT NULL | false | false | Count of O*NET detail codes that contributed to this importance value. 1 for most occupations, 2+ for multi-detail BLS SOCs. |
| suppress_flag | BT-062 | boolean | NOT NULL | false | false | True if recommend_suppress = "Y" in ANY contributing Bronze row. Signals unreliable data. Less than 3% expected True. |
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. |

---

## Table 3: onet_context_profiles

Work Context point estimates per occupation at BLS SOC granularity. Backs the Burnout boss fight. One row per occupation per Work Context element, CX/CT scales only.

### Attributes

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from bls_soc_code + element_id using `compute_grain_id()` with prefix 'wc'. |
| bls_soc_code | BT-027 | identifier | NOT NULL | true | false | 6-digit BLS SOC code. FK to onet_occupations.bls_soc_code. Every value must exist in the parent table. |
| element_id | BT-056 | identifier | NOT NULL | true | false | Content Model element ID (e.g., "4.C.3.d.1"). Part of composite natural key. Exactly 57 distinct values. |
| element_name | -- | text | NOT NULL | false | false | Human-readable context dimension name (e.g., "Time Pressure"). Denormalized from Bronze. |
| scale_id | -- | identifier | NOT NULL | false | false | Scale identifier: "CX" (point estimate, 55 elements) or "CT" (category, 2 elements). Determines the valid range of context_value. |
| context_value | BT-058 | numeric | NOT NULL | true | false | CX scale: 1.0-5.0. CT scale: 1.0-3.0. Averaged across O*NET details if multi-detail. Primary input for Burnout scoring. |
| is_burnout_element | BT-059 | boolean | NOT NULL | false | false | True for the ~9 burnout-relevant Work Context elements. Enables the Burnout boss fight formula to weight these elements most heavily. Subject to human approval of the element list. |
| onet_details_averaged | BT-063 | numeric | NOT NULL | false | false | Count of O*NET detail codes that contributed to this context value. 1 for most occupations, 2+ for multi-detail BLS SOCs. |
| suppress_flag | BT-062 | boolean | NOT NULL | false | false | True if recommend_suppress = "Y" in ANY contributing Bronze row. Less than 3% expected True. |
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. |

---

## Table 4: onet_career_transitions

Career similarity graph at BLS SOC granularity. Each row is a directional relationship: "from this occupation, these are the most similar careers." Backs Stage 3 career branching.

### Attributes

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from bls_soc_code + related_bls_soc_code using `compute_grain_id()` with prefix 'ct'. |
| bls_soc_code | BT-027 | identifier | NOT NULL | false | false | Source occupation: 6-digit BLS SOC code. FK to onet_occupations.bls_soc_code. |
| related_bls_soc_code | BT-027 | identifier | NOT NULL | false | false | Target occupation: 6-digit BLS SOC code. FK to onet_occupations.bls_soc_code. Must differ from bls_soc_code (no self-references). |
| best_index | BT-061 | numeric | NOT NULL | false | false | Best (lowest) relatedness index across O*NET detail pairings. Range: 1-20. Lower = more similar. |
| relatedness_tier | BT-061 | text | NOT NULL | false | false | "Primary-Short" (index 1-5), "Primary-Long" (index 6-10), "Supplemental" (index 11-20). Tier of the best_index row. |
| is_primary | -- | boolean | NOT NULL | false | false | True when relatedness_tier is "Primary-Short" or "Primary-Long". Convenience flag for filtering to closest career paths. |
| relationship_type | BT-060 | text | NOT NULL | false | false | Always "similarity" for this source. Future-proofed for post-hackathon transition data (would be "transition"). |
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. |

---

## Attribute Summary

| Table | Total | Natural Key | Surrogate Key | CDE | PII | Nullable | NOT NULL | Derived |
|-------|-------|-------------|---------------|-----|-----|----------|----------|---------|
| onet_occupations | 14 | 1 (bls_soc_code) | 1 (record_id) | 2 | 0 | 0 | 14 | 7 |
| onet_activity_profiles | 11 | 2 (bls_soc_code, element_id) | 1 (record_id) | 3 | 0 | 0 | 11 | 4 |
| onet_context_profiles | 11 | 2 (bls_soc_code, element_id) | 1 (record_id) | 3 | 0 | 0 | 11 | 3 |
| onet_career_transitions | 9 | 2 (bls_soc_code, related_bls_soc_code) | 1 (record_id) | 0 | 0 | 0 | 9 | 3 |
| **Total** | **45** | | | **8** | **0** | **0** | **45** | **17** |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure, count, or code. May be aggregated (measures) or used for lookup (codes). | INTEGER (counts/ranks), DOUBLE (ratings/averages) |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Foreign Key Relationships

| Source Table | Source Column | Target Table | Target Column | Cardinality | Enforcement |
|-------------|-------------|-------------|--------------|-------------|-------------|
| onet_activity_profiles | bls_soc_code | onet_occupations | bls_soc_code | many-to-one | Referential integrity DQ rule |
| onet_context_profiles | bls_soc_code | onet_occupations | bls_soc_code | many-to-one | Referential integrity DQ rule |
| onet_career_transitions | bls_soc_code | onet_occupations | bls_soc_code | many-to-one | Referential integrity DQ rule |
| onet_career_transitions | related_bls_soc_code | onet_occupations | bls_soc_code | many-to-one | Referential integrity DQ rule |

**Cross-source join (not enforced as FK):**

| Source Table | Source Column | Target Table | Target Column | Notes |
|-------------|-------------|-------------|--------------|-------|
| onet_occupations | bls_soc_code | base.bls_ooh | soc_code | O*NET has ~867 vs BLS OOH 832, partial overlap. Not a strict FK. |

---

## Derivation Rules

### Table 1: onet_occupations

| Derived Attribute | Rule | Source |
|-------------------|------|--------|
| record_id | `compute_grain_id(row, ['bls_soc_code'], prefix='on')` | bls_soc_code |
| bls_soc_code | Truncate O*NET-SOC code to first 7 characters (XX-XXXX): `onet_soc_code[:7]` | raw.onet_occupations.onetsoc_code |
| primary_title | Title from the .00 base code. If no .00 code exists for a BLS SOC, use the first detailed code's title (alphabetically by O*NET-SOC). | raw.onet_occupations.title |
| description | Description from the .00 base code. If no .00 code exists, use the first detailed code's description. | raw.onet_occupations.description |
| onet_detail_codes | JSON array of all O*NET-SOC codes mapping to this BLS SOC, sorted ascending: `json_array(sorted(onet_soc_codes))` | raw.onet_occupations.onetsoc_code |
| onet_detail_count | `len(onet_detail_codes)` | onet_detail_codes |
| multi_detail_flag | `onet_detail_count > 1` | onet_detail_count |
| has_work_activities | `EXISTS(SELECT 1 FROM raw.onet_work_activities WHERE onet_soc_code LIKE bls_soc_code || '%')` | raw.onet_work_activities |
| has_work_context | `EXISTS(SELECT 1 FROM raw.onet_work_context WHERE onet_soc_code LIKE bls_soc_code || '%')` | raw.onet_work_context |
| has_tasks | `EXISTS(SELECT 1 FROM raw.onet_task_statements WHERE onet_soc_code LIKE bls_soc_code || '%')` | raw.onet_task_statements |
| has_related | `EXISTS(SELECT 1 FROM raw.onet_related_occupations WHERE onet_soc_code LIKE bls_soc_code || '%')` | raw.onet_related_occupations |
| data_completeness_tier | If all 4 has_* flags are True: "full". If any but not all: "partial". If none: "none" (excluded from Silver). | has_work_activities, has_work_context, has_tasks, has_related |

### Table 2: onet_activity_profiles

| Derived Attribute | Rule | Source |
|-------------------|------|--------|
| record_id | `compute_grain_id(row, ['bls_soc_code', 'element_id'], prefix='wa')` | bls_soc_code, element_id |
| bls_soc_code | Truncate O*NET-SOC to XX-XXXX | raw.onet_work_activities.onetsoc_code |
| importance | `AVG(data_value)` grouped by bls_soc_code, element_id WHERE scale_id = 'IM' | raw.onet_work_activities.data_value |
| importance_rank | `RANK() OVER (PARTITION BY bls_soc_code ORDER BY importance DESC)` | importance |
| is_high_importance | `importance >= 3.5` | importance |
| onet_details_averaged | `COUNT(DISTINCT onet_soc_code)` per bls_soc_code, element_id group | raw.onet_work_activities.onetsoc_code |
| suppress_flag | `MAX(CASE WHEN recommend_suppress = 'Y' THEN 1 ELSE 0 END) = 1` (logical OR across contributing rows) | raw.onet_work_activities.recommend_suppress |

### Table 3: onet_context_profiles

| Derived Attribute | Rule | Source |
|-------------------|------|--------|
| record_id | `compute_grain_id(row, ['bls_soc_code', 'element_id'], prefix='wc')` | bls_soc_code, element_id |
| bls_soc_code | Truncate O*NET-SOC to XX-XXXX | raw.onet_work_context.onetsoc_code |
| context_value | `AVG(data_value)` grouped by bls_soc_code, element_id WHERE scale_id IN ('CX', 'CT') | raw.onet_work_context.data_value |
| scale_id | Carried from Bronze. Each element_id maps to exactly one scale_id (CX or CT). | raw.onet_work_context.scale_id |
| is_burnout_element | `element_id IN ('4.C.3.d.1', '4.C.3.d.8', '4.C.3.a.1', '4.C.3.d.3', '4.C.3.b.2', '4.C.3.d.4', '4.C.3.d.5', '4.C.3.b.7', '4.C.3.d.7')` (9 elements, subject to human approval) | element_id |
| onet_details_averaged | `COUNT(DISTINCT onet_soc_code)` per bls_soc_code, element_id group | raw.onet_work_context.onetsoc_code |
| suppress_flag | `MAX(CASE WHEN recommend_suppress = 'Y' THEN 1 ELSE 0 END) = 1` | raw.onet_work_context.recommend_suppress |

### Table 4: onet_career_transitions

| Derived Attribute | Rule | Source |
|-------------------|------|--------|
| record_id | `compute_grain_id(row, ['bls_soc_code', 'related_bls_soc_code'], prefix='ct')` | bls_soc_code, related_bls_soc_code |
| bls_soc_code | Truncate source O*NET-SOC to XX-XXXX | raw.onet_related_occupations.onetsoc_code |
| related_bls_soc_code | Truncate related O*NET-SOC to XX-XXXX | raw.onet_related_occupations.related_onetsoc_code |
| best_index | `MIN(related_index)` grouped by bls_soc_code, related_bls_soc_code | raw.onet_related_occupations.related_index |
| relatedness_tier | Tier of the row with best_index: index 1-5 = "Primary-Short", 6-10 = "Primary-Long", 11-20 = "Supplemental" | best_index |
| is_primary | `relatedness_tier IN ('Primary-Short', 'Primary-Long')` | relatedness_tier |
| relationship_type | Static value: "similarity" | N/A |

---

## Transformation Rules

### Filtering

| Table | Filter | Effect |
|-------|--------|--------|
| onet_occupations | Exclude 93 "All Other"/Military occupations with data_completeness_tier = "none" | Removes occupations with zero data in all Bronze child tables |
| onet_activity_profiles | WHERE scale_id = 'IM' (Importance scale only) | Excludes LV (Level) scale rows, cutting Bronze data approximately in half |
| onet_activity_profiles | Exclude occupations not in onet_occupations | Removes profiles for the 93 structurally empty occupations |
| onet_context_profiles | WHERE scale_id IN ('CX', 'CT') (point estimate scales only) | Excludes CXP/CTP category-percentage rows (~82% of Bronze Work Context data) |
| onet_context_profiles | Exclude occupations not in onet_occupations | Removes profiles for the 93 structurally empty occupations |
| onet_career_transitions | Exclude self-references: bls_soc_code != related_bls_soc_code | Removes relationships that emerge from BLS-level aggregation where two O*NET details of the same BLS SOC relate to each other |
| onet_career_transitions | Exclude relationships where either SOC is in the excluded 93 set | Removes transitions to/from structurally empty occupations |
| onet_career_transitions | Deduplicate after BLS-level aggregation: keep row with MIN(related_index) per (bls_soc_code, related_bls_soc_code) | Resolves duplicates when multiple O*NET detail pairings produce the same BLS-level pair |

### Aggregation

| Table | Aggregation | Strategy |
|-------|-------------|----------|
| onet_occupations | O*NET-SOC (XX-XXXX.XX) to BLS SOC (XX-XXXX) | Group by 6-digit prefix. Titles/descriptions from .00 base code. Detail codes collected into JSON array. |
| onet_activity_profiles | Multiple O*NET details to single BLS SOC per element | Unweighted AVG of IM data_value. Logical OR on suppress_flag. COUNT DISTINCT on contributing detail codes. |
| onet_context_profiles | Multiple O*NET details to single BLS SOC per element | Unweighted AVG of CX/CT data_value. Logical OR on suppress_flag. COUNT DISTINCT on contributing detail codes. |
| onet_career_transitions | Multiple O*NET detail pairings to single BLS SOC pair | Keep MIN(related_index) as best_index. Tier derived from best_index. |

---

## Nullability Semantics

All 45 attributes across all 4 tables are NOT NULL. This is possible because:

| Pattern | Reason |
|---------|--------|
| All identifier/key fields | Grain fields and surrogate keys are always present by construction. |
| All rating values (importance, context_value) | O*NET provides complete ratings for all occupation-element combinations in the retained scales. Rows with missing data are not present in Bronze. |
| All derived flags | Computed from present data; flags default to False when conditions are not met. |
| All metadata fields | source_load_date and ingested_at are always populated by the pipeline. |

If a row exists in these Silver tables, it has complete data. Rows with missing source data are simply not present (e.g., a Work Context element not measured for an occupation would not produce a row in onet_context_profiles).

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Table | Logical Attributes | Notes |
|-------------------|--------------|-------------------|-------|
| Occupation | onet_occupations | record_id, bls_soc_code, primary_title, description, onet_detail_codes, onet_detail_count, multi_detail_flag, has_work_activities, has_work_context, has_tasks, has_related, data_completeness_tier, source_load_date, ingested_at | Central dimension. 14 attributes covering identity, aggregation metadata, data completeness, and pipeline metadata. |
| Activity Profile | onet_activity_profiles | record_id, bls_soc_code, element_id, element_name, importance, importance_rank, is_high_importance, onet_details_averaged, suppress_flag, source_load_date, ingested_at | Fact-like table. 11 attributes. Composite grain: bls_soc_code x element_id. |
| Context Profile | onet_context_profiles | record_id, bls_soc_code, element_id, element_name, scale_id, context_value, is_burnout_element, onet_details_averaged, suppress_flag, source_load_date, ingested_at | Fact-like table. 11 attributes. Composite grain: bls_soc_code x element_id. Has scale_id to distinguish CX from CT ranges. |
| Career Transition | onet_career_transitions | record_id, bls_soc_code, related_bls_soc_code, best_index, relatedness_tier, is_primary, relationship_type, source_load_date, ingested_at | Graph edge table. 9 attributes. Composite grain: bls_soc_code x related_bls_soc_code. Self-referencing via onet_occupations. |
| (Pipeline Metadata) | all tables | source_load_date, ingested_at | Not a conceptual entity -- pipeline infrastructure present on every table. |

---

## Cross-Source Integration

This model provides the O*NET occupation characteristics that enrich the BLS employment projections with work activity profiles, environmental context, and career pathway data.

| Attribute | Cross-Source Role |
|-----------|------------------|
| onet_occupations.bls_soc_code | Joins to base.bls_ooh.soc_code for employment projections, wages, and entry requirements |
| onet_career_transitions.bls_soc_code | Both columns join to base.bls_ooh.soc_code for enriching career paths with employment data |
| onet_career_transitions.related_bls_soc_code | Same as above |
| onet_occupations.bls_soc_code | Joins through CIP-SOC crosswalk (future spec) to base.college_scorecard.cipcode |

---

## CDE Justification

| CDE Attribute | Table | Justification |
|--------------|-------|---------------|
| bls_soc_code | onet_occupations | Grain key and primary cross-source join key linking O*NET to BLS OOH and CIP-SOC crosswalk |
| data_completeness_tier | onet_occupations | Drives downstream data quality decisions -- consumers must know if occupation data is full or partial |
| bls_soc_code | onet_activity_profiles | Grain key and FK enabling HMN stat computation |
| element_id | onet_activity_profiles | Grain key identifying the specific work activity being measured |
| importance | onet_activity_profiles | Primary measurement backing the HMN (Human Edge) stat in Gold zone |
| bls_soc_code | onet_context_profiles | Grain key and FK enabling Burnout scoring |
| element_id | onet_context_profiles | Grain key identifying the specific work context dimension |
| context_value | onet_context_profiles | Primary measurement backing the Burnout boss fight in Gold zone |

Career Transitions has no CDE attributes because it does not directly back a FutureProof stat score -- it enables branching navigation, which is a UI/game feature rather than a quantitative data product.

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | Burnout element IDs need validation against actual Bronze data | The 9 proposed element IDs are from O*NET Content Model documentation and may have minor format differences in the actual data. | @primary-agent validates IDs during implementation. If any ID does not match, adjust the is_burnout_element derivation rule. |
| 2 | description attribute has no business glossary term | Carried from O*NET occupation descriptions. Low priority -- not used in downstream scoring. | @data-steward may propose a term if needed for Gold zone consumers. |
| 3 | element_name, scale_id, is_high_importance, is_primary, relationship_type have no business glossary terms | Supplementary/convenience attributes that are derivations of or lookups on existing BT terms. | @data-steward to decide if standalone terms are needed. Low priority. |

---

## Modeling Decisions

1. **Four separate tables matching conceptual entities.** Unlike BLS OOH (single table, all 1:1 relationships), this model has genuinely different grains requiring separate tables. The star topology with onet_occupations as the hub mirrors the source data structure and enables targeted Gold zone joins.

2. **All attributes NOT NULL.** O*NET provides complete data for all retained scales and elements. The Silver transformation excludes entire rows (via filtering) rather than producing rows with null values. This simplifies downstream consumption -- if a row exists, all fields are populated.

3. **CDE assignments focused on grain keys and primary measurements.** bls_soc_code and element_id are CDEs because they are the join/filter keys that make cross-source integration work. importance and context_value are CDEs because they are the primary numeric inputs to Gold zone stat formulas. Derived convenience flags (is_high_importance, is_primary, multi_detail_flag) are not CDEs because they are recomputable from the primary measurements and keys.

4. **onet_detail_codes as JSON text, not a separate table.** The O*NET detail codes for each BLS SOC are stored as a JSON array in the occupations table rather than in a separate bridge table. This is appropriate because: (a) the detail codes are lineage metadata, not a joinable dimension; (b) the maximum cardinality is small (2-5 codes per BLS SOC); (c) a separate table would add complexity for a rarely-queried field.

5. **scale_id preserved on context_profiles but not activity_profiles.** Activity profiles contain only IM scale data (the LV scale is filtered out in Bronze-to-Silver), so no scale_id is needed. Context profiles retain both CX and CT scales, which have different value ranges (1-5 vs 1-3), so scale_id is needed for correct interpretation of context_value.

6. **relationship_type as a static field on career_transitions.** Currently always "similarity", but included to future-proof for post-hackathon transition data from Career Changers/Starters matrices (which do not exist in O*NET 30.2). When transition data becomes available, this field distinguishes the two relationship types without schema changes.

7. **Unweighted averaging for multi-detail aggregation.** Employment-weighted averaging would be more accurate but requires BLS employment data mapped to O*NET detail codes, which is not readily available. The unweighted approach is documented in the onet_details_averaged field so downstream consumers can assess aggregation quality.
