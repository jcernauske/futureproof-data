# Logical Model: silver-base-bls-ooh

**Status:** APPROVED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** Occupational Employment Projections
**Spec:** docs/specs/silver-base-bls-ooh.md
**Conceptual Model:** governance/models/silver-base-bls-ooh-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-07
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    BLS_OOH {
        identifier record_id PK
        identifier soc_code NK
        text occupation_title
        identifier soc_major_group
        text soc_major_group_name
        boolean broad_occupation_flag
        boolean catchall_flag
        numeric employment_current
        numeric employment_projected
        numeric employment_change
        numeric employment_change_pct
        numeric openings_annual_avg
        text growth_category
        numeric median_annual_wage
        boolean median_wage_capped
        boolean wage_available
        text education_typical
        numeric education_code
        text education_level_name
        text work_experience
        numeric work_experience_code
        text training_typical
        numeric training_code
        date source_load_date
        timestamp ingested_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies 5 entities (Occupation, SOC Major Group, Employment Projection, Compensation, Entry Requirements). Per the Silver Base zone pattern, these are flattened into a single denormalized `base.bls_ooh` table. The conceptual entities inform attribute grouping below but do not produce separate tables.

This is appropriate because:
1. The source data is already at the occupation grain with all attributes in a single row (832 rows)
2. Silver Base tables are designed as wide, query-ready fact tables for downstream Gold zone consumption
3. All conceptual relationships resolve to 1:1 or 1:0..1 per occupation row -- no many-to-many relationships exist at this grain
4. This matches the established pattern from `base.college_scorecard` (single denormalized table with conceptual entities as attribute groups)

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per occupation: a single SOC code in the BLS Employment Projections |
| **Natural key fields** | `soc_code` |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'ooh') |
| **Uniqueness constraint** | Zero duplicates on soc_code. Enforced at load time. |
| **Expected cardinality** | 832 rows |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The `NK` marker denotes natural key components.

### Occupation (Core Identity)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | -- | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key (soc_code) using `compute_grain_id()` with prefix 'ooh'. Stable across pipeline re-runs. |
| soc_code | BT-027 | identifier | NOT NULL | true | false | SOC occupation code in XX-XXXX format. Single-field natural key. Primary join key for O*NET and CIP-SOC crosswalk. |
| occupation_title | BT-028 | text | NOT NULL | false | false | Official BLS occupation name. Each SOC code maps to exactly one title. Used for catchall_flag derivation (substring match on "all other"). |

### SOC Major Group (Classification)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| soc_major_group | BT-029 | identifier | NOT NULL | false | false | 2-digit SOC major group code derived from first 2 characters of soc_code. One of 22 valid codes. Used for aggregation and fallback grouping when detailed crosswalk matches fail. |
| soc_major_group_name | BT-030 | text | NOT NULL | false | false | Human-readable label for the SOC major group (e.g., "Computer and Mathematical" for code 15). Derived via lookup from the 22-group SOC taxonomy. |

### Classification Flags (Occupation Qualifiers)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| broad_occupation_flag | BT-040 | boolean | NOT NULL | false | false | True for 7 SOC codes that represent rolled-up/broad occupation categories aggregating multiple O*NET detailed codes. These require special handling in the CIP-SOC crosswalk (lower-confidence joins). |
| catchall_flag | BT-043 | boolean | NOT NULL | false | false | True for 70 occupations with "all other" in the title (case-insensitive), indicating BLS residual categories. Career guidance from catchall occupations should carry lower confidence. |

### Employment Projection

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| employment_current | BT-031 | numeric | NULLABLE | true | false | Current employment count (actual workers, already converted from thousands in Bronze). Base year of projection cycle. Positive when present. |
| employment_projected | BT-032 | numeric | NULLABLE | true | false | Projected employment count at end of 10-year projection horizon (actual workers). Positive when present. |
| employment_change | BT-033 | numeric | NULLABLE | true | false | Absolute change in employment (projected minus current). Can be negative for declining occupations (232 of 832 expected to decline). |
| employment_change_pct | BT-034 | numeric | NULLABLE | true | false | Percentage change in employment over the projection cycle. Can be negative. Backs the GRW stat in Gold zone. Input for growth_category derivation. |
| openings_annual_avg | BT-035 | numeric | NULLABLE | false | false | Projected annual average job openings (growth + replacement). Non-negative. Four very small occupations show zero due to BLS rounding. |
| growth_category | BT-041 | text | NULLABLE | false | false | Derived categorical classification bucketing employment_change_pct into six human-readable tiers. Null only when employment_change_pct is null. See Derivation Rules. |

### Compensation

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| median_annual_wage | BT-036 | numeric | NULLABLE | true | false | Median annual wage in dollars. Null for 23 occupations where BLS does not report wage data (elected officials, self-employed-dominated fields). Backs the ERN stat in Gold zone. |
| median_wage_capped | BT-037 | boolean | NOT NULL | false | false | True if BLS top-coded the wage at $239,200. Currently 0 True values in the interactive export. Preserved for future data source changes. |
| wage_available | BT-042 | boolean | NOT NULL | false | false | Derived convenience flag: True when median_annual_wage is not null. 809 True, 23 False expected. |

### Entry Requirements

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| education_typical | -- | text | NULLABLE | false | false | Typical entry-level education label as reported by BLS (original text). Supplementary to the coded/normalized fields. |
| education_code | BT-038 | numeric | NULLABLE | false | false | BLS education level code (1-8). 1=Doctoral, 2=Master's, 3=Bachelor's, 4=Associate's, 5=Postsecondary nondegree, 6=Some college, 7=High school, 8=No formal credential. |
| education_level_name | BT-039 | text | NULLABLE | false | false | Normalized education level label derived from education_code via lookup. Ensures consistent labeling across the pipeline. |
| work_experience | -- | text | NULLABLE | false | false | Work experience requirement label as reported by BLS (original text). Supplementary to the coded field. |
| work_experience_code | BT-044 | numeric | NULLABLE | false | false | BLS work experience code (1-3). 1=5+ years, 2=Less than 5 years, 3=None. 86.1% of occupations are code 3. |
| training_typical | -- | text | NULLABLE | false | false | Typical on-the-job training label as reported by BLS (original text). Supplementary to the coded field. |
| training_code | BT-045 | numeric | NULLABLE | false | false | BLS training code (1-6). 1=Internship/residency, 2=Apprenticeship, 3=Long-term OJT, 4=Moderate-term OJT, 5=Short-term OJT, 6=None. |

### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | -- | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. Represents data fetch date, not outcome measurement date. Renamed from Bronze `load_date`. |
| ingested_at | -- | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. Generated at transformation time. Used for pipeline auditing and data freshness tracking. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 25 | Total attributes |
| 1 | Natural key components (soc_code) |
| 1 | Surrogate key (record_id) |
| 4 | CDE attributes (soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage) |
| 0 | PII attributes |
| 12 | Nullable attributes |
| 13 | NOT NULL attributes |
| 7 | Derived attributes (record_id, soc_major_group, soc_major_group_name, broad_occupation_flag, catchall_flag, growth_category, wage_available, education_level_name) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure, count, or code. May be aggregated (measures) or used for lookup (codes). | BIGINT (counts), DOUBLE (monetary/pct), INTEGER (codes) |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | `compute_grain_id(row, ['soc_code'], prefix='ooh')` | soc_code |
| soc_major_group | First 2 characters of soc_code: `soc_code[:2]` | soc_code |
| soc_major_group_name | Lookup soc_major_group against the 22-group SOC taxonomy table (see spec) | soc_major_group |
| broad_occupation_flag | `soc_code IN ('13-1020','13-2020','29-2010','31-1120','39-7010','47-4090','51-2090')` | soc_code |
| catchall_flag | `LOWER(occupation_title) LIKE '%all other%'` | occupation_title |
| growth_category | Bucket employment_change_pct: `< -10` = declining_fast, `[-10, -1)` = declining, `[-1, 1)` = stable, `[1, 10)` = growing, `[10, 20)` = growing_fast, `>= 20` = booming, null when pct is null | employment_change_pct |
| wage_available | `median_annual_wage IS NOT NULL` | median_annual_wage |
| education_level_name | Lookup education_code against 8-row education level table: 1=Doctoral or professional degree, 2=Master's degree, 3=Bachelor's degree, 4=Associate's degree, 5=Postsecondary nondegree award, 6=Some college no degree, 7=High school diploma or equivalent, 8=No formal educational credential | education_code |

---

## Nullability Semantics

Null values in this model carry specific business meaning:

| Pattern | Business Meaning |
|---------|-----------------|
| median_annual_wage IS NULL | BLS does not report wage data for this occupation (23 occupations: elected officials, self-employed-dominated fields). Not a data quality issue -- a real absence. |
| wage_available = False | Same 23 occupations. Convenience filter so consumers don't need null checks. |
| growth_category IS NULL | employment_change_pct is null (insufficient data for projection). |
| employment_* fields NULL | Extremely rare -- source data is comprehensive for all 832 occupations in the current cycle. Nullable as a defensive measure against future data changes. |
| education_code / work_experience_code / training_code NULL | BLS did not classify this occupation's entry requirements. Defensive nullability; current data has full coverage. |
| education_typical / work_experience / training_typical NULL | Original BLS text label not available. Mirrors nullability of the corresponding code field. |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attributes | Notes |
|-------------------|--------------------|-------|
| Occupation | record_id, soc_code, occupation_title, broad_occupation_flag, catchall_flag | Central entity. soc_code is the natural key. Classification flags are qualifiers on the occupation record per conceptual decision 7. |
| SOC Major Group | soc_major_group, soc_major_group_name | Derived from soc_code. Kept as attributes for aggregation and fallback grouping. Parallels CIP Family in College Scorecard. |
| Employment Projection | employment_current, employment_projected, employment_change, employment_change_pct, openings_annual_avg, growth_category | 1:1 with Occupation. growth_category is derived from employment_change_pct. |
| Compensation | median_annual_wage, median_wage_capped, wage_available | 1:0..1 with Occupation (23 nulls). wage_available is a convenience flag derived from wage nullity. |
| Entry Requirements | education_typical, education_code, education_level_name, work_experience, work_experience_code, training_typical, training_code | 1:1 with Occupation. Each dimension has both a BLS text label and a coded integer, plus a normalized label for education. |
| (Pipeline Metadata) | source_load_date, ingested_at | Not a conceptual entity -- pipeline infrastructure. |

---

## Cross-Source Integration

This table is the SOC-side anchor for the CIP-to-SOC crosswalk. Key attributes that serve the crosswalk:

| Attribute | Crosswalk Role |
|-----------|---------------|
| soc_code | Primary join key (SOC side of CIP-SOC bridge) |
| broad_occupation_flag | Signals lower-confidence crosswalk joins (7 codes that fan out to multiple O*NET children) |
| catchall_flag | Signals lower-confidence career guidance (70 residual categories) |
| soc_major_group | Enables fallback grouping when detailed crosswalk matches fail |

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | education_typical, work_experience, and training_typical have no business glossary terms | These are original BLS text labels carried forward from Bronze. The coded and normalized versions (BT-038/BT-039, BT-044, BT-045) have terms. | @data-steward may propose terms if these labels are needed in downstream models. Low priority since the coded versions are the primary consumption path. |
| 2 | record_id, source_load_date, and ingested_at have no business glossary terms | Pipeline metadata fields. College Scorecard model uses BT-015/BT-016/BT-017 for equivalent fields. | Reuse BT-015 (record_id), BT-016 (source_load_date), BT-017 (ingested_at) if these are cross-model pipeline terms, or propose BLS-specific terms. @data-steward to decide. |

---

## Modeling Decisions

1. **Single denormalized table.** All five conceptual entities flatten into one table. The 1:1 and 1:0..1 cardinalities make separate tables unnecessary. This matches the College Scorecard Silver pattern.

2. **Original BLS text labels preserved alongside codes.** The spec includes both `education_typical` (BLS text) and `education_code` (integer) plus `education_level_name` (normalized text). All three are kept because: (a) the original label provides auditability back to the source, (b) the code enables numeric filtering and ordering, (c) the normalized name ensures consistent labeling across the pipeline.

3. **Employment fields are nullable despite current full coverage.** The current dataset has no null employment values, but the fields are marked NULLABLE as a defensive measure. If a future BLS projection cycle excludes certain occupations or has partial data, the schema accommodates this without migration. This follows the same defensive nullability pattern as the spec.

4. **CDE assignments follow the conceptual model.** soc_code (the grain key and crosswalk anchor), employment_current, employment_projected, employment_change_pct, and median_annual_wage are CDEs because they drive downstream Gold zone stats (ERN, GRW) and the CIP-SOC crosswalk. openings_annual_avg is not a CDE because it is not currently used as a primary input to any Gold stat.

5. **No projection_cycle attribute.** The current dataset is a single snapshot (2024-2034). Temporal tracking will be added if multiple projection cycles are retained. source_load_date serves as the pipeline-level temporal marker. This mirrors the College Scorecard decision.
