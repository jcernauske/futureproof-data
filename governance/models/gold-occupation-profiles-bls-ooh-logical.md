# Logical Model: gold-occupation-profiles-bls-ooh

**Status:** APPROVED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Domain:** Occupational Employment Projections
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Conceptual Model:** governance/models/gold-occupation-profiles-bls-ooh-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-07
**Approval:** APPROVED by human review (2026-04-07)
**Source Model:** governance/models/silver-base-bls-ooh-logical.md

---

```mermaid
erDiagram
    OCCUPATION_PROFILE {
        identifier record_id PK
        identifier soc_code NK
        text occupation_title
        identifier soc_major_group
        text soc_major_group_name
        boolean broad_occupation_flag
        boolean catchall_flag
    }
    GROWTH_ASSESSMENT {
        identifier soc_code PK
        numeric employment_current
        numeric employment_projected
        numeric employment_change_pct
        numeric openings_annual_avg
        text growth_category
        numeric grw_score
        numeric grw_score_rounded
    }
    WAGE_POSITION {
        identifier soc_code PK
        numeric median_annual_wage
        boolean wage_available
        numeric wage_percentile_overall
        numeric wage_percentile_education_tier
        text wage_tier
    }
    ENTRY_REQUIREMENTS {
        identifier soc_code PK
        numeric education_code
        text education_level_name
        numeric work_experience_code
        numeric training_code
    }
    MARKET_OPPORTUNITY {
        identifier soc_code PK
        numeric market_score
        numeric market_score_rounded
    }
    DATA_QUALITY_CONTEXT {
        identifier soc_code PK
        text confidence_tier
        numeric data_completeness
    }
    FUTUREPROOF_STAT_MAPPING {
        identifier soc_code PK
        text backs_stats
        text backs_bosses
    }
    PIPELINE_METADATA {
        identifier soc_code PK
        date source_load_date
        timestamp promoted_at
    }
    OCCUPATION_PROFILE ||--|| GROWTH_ASSESSMENT : "scored by"
    OCCUPATION_PROFILE ||--o| WAGE_POSITION : "ranked by"
    OCCUPATION_PROFILE ||--|| ENTRY_REQUIREMENTS : "requires"
    OCCUPATION_PROFILE ||--|| MARKET_OPPORTUNITY : "evaluated by"
    OCCUPATION_PROFILE ||--|| DATA_QUALITY_CONTEXT : "qualified by"
    OCCUPATION_PROFILE ||--|| FUTUREPROOF_STAT_MAPPING : "powers"
    OCCUPATION_PROFILE ||--|| PIPELINE_METADATA : "tracked by"
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies 7 entities (Occupation Profile, Growth Assessment, Wage Position, Market Opportunity, Data Quality Context, FutureProof Stat Mapping, SOC Major Group). Following the established Gold zone pattern from `consumable.career_outcomes`, these are flattened into a single denormalized `consumable.occupation_profiles` table in the physical layer. The logical model groups attributes by conceptual entity to preserve semantic clarity while acknowledging the physical denormalization.

This is appropriate because:
1. The Gold consumable layer optimizes for the primary query pattern (SOC code or title = career profile)
2. All conceptual entities resolve to 1:1 or 1:0..1 per row at the occupation grain
3. Dataset size (832 rows) does not benefit from normalization
4. Downstream consumers (Gemma agent, pentagon stats, boss fights) expect a single flat table per occupation

The logical diagram above shows the conceptual entity groups as separate boxes to communicate the distinct business concerns, but all will collapse into a single physical table. Entry Requirements is shown as a separate logical group despite being absorbed into Occupation Profile in the conceptual model, because these fields serve as partition keys for derived computations (wage_percentile_education_tier) and warrant explicit documentation.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per occupation (soc_code) |
| **Natural key fields** | `soc_code` |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'op') |
| **Uniqueness constraint** | Zero duplicates on soc_code. Enforced at promote time. |
| **Expected cardinality** | 832 rows (all Silver base rows carried forward; no rows added or dropped) |
| **Source table** | `base.bls_ooh` (Silver zone) |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The `NK` marker denotes natural key components.

### Occupation Profile (Core Identity + Classification)

These attributes are carried forward from Silver `base.bls_ooh` without transformation. They combine the conceptual entities Occupation Identity and SOC Major Group.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key (soc_code) using `compute_grain_id()` with prefix 'op'. Note: prefix changes from Silver's 'ooh' to Gold's 'op' to distinguish zones. |
| soc_code | BT-027 | identifier | NOT NULL | true | false | SOC occupation code in XX-XXXX format. Single-field natural key. Primary join key for O*NET and CIP-SOC crosswalk. Carried from Silver verbatim. |
| occupation_title | BT-028 | text | NOT NULL | false | false | Official BLS occupation name. Carried from Silver verbatim. |
| soc_major_group | BT-029 | identifier | NOT NULL | false | false | 2-digit SOC major group code derived from first 2 characters of soc_code. One of 22 valid codes. Carried from Silver verbatim. |
| soc_major_group_name | BT-030 | text | NOT NULL | false | false | Human-readable label for the SOC major group. Carried from Silver verbatim. |
| broad_occupation_flag | BT-040 | boolean | NOT NULL | false | false | True for 7 SOC codes representing rolled-up/broad occupation categories. Carried from Silver verbatim. Used in confidence_tier derivation. |
| catchall_flag | BT-043 | boolean | NOT NULL | false | false | True for ~70 occupations with "all other" in the title. Carried from Silver verbatim. Used in confidence_tier derivation. |

### Growth Assessment (Carried + Derived)

Employment projection fields carried from Silver, plus the derived GRW score that maps employment change percentage to the FutureProof 1-10 scale.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| employment_current | BT-031 | numeric | NULLABLE | true | false | Current employment count (actual workers). Carried from Silver verbatim. One of four core fields for data_completeness. |
| employment_projected | BT-032 | numeric | NULLABLE | true | false | Projected employment count at end of 10-year projection horizon. Carried from Silver verbatim. |
| employment_change_pct | BT-034 | numeric | NULLABLE | true | false | Percentage change in employment over the projection cycle. Can be negative. Carried from Silver verbatim. Input to grw_score derivation. One of four core fields for data_completeness. |
| openings_annual_avg | BT-035 | numeric | NULLABLE | false | false | Projected annual average job openings (growth + replacement). Carried from Silver verbatim. Input to market_score derivation. One of four core fields for data_completeness. |
| growth_category | BT-041 | text | NOT NULL | false | false | Bucketed growth classification (declining_fast, declining, stable, growing, growing_fast, booming). Carried from Silver verbatim. |
| grw_score | BT-047 | numeric | NULLABLE | true | false | Growth stat on 1-10 scale. Derived from employment_change_pct via piecewise linear function (see Derivation Rules). Backs the GRW pentagon stat. Null only if employment_change_pct is null (0 rows currently). |
| grw_score_rounded | BT-047 | numeric | NULLABLE | false | false | Integer 1-10 for display. ROUND(grw_score). Null if grw_score is null. |

### Wage Position (Carried + Derived)

Compensation data carried from Silver, plus derived percentile ranks and tier classification. All derived wage fields are null for 23 occupations without wage data.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| median_annual_wage | BT-036 | numeric | NULLABLE | true | false | Median annual wage in dollars. Null for 23 occupations. Carried from Silver verbatim. One of four core fields for data_completeness. Backs the ERN stat. |
| wage_available | BT-042 | boolean | NOT NULL | false | false | True if median_annual_wage is not null. Carried from Silver verbatim. Used in confidence_tier derivation. |
| wage_percentile_overall | BT-048 | numeric | NULLABLE | true | false | 0.0-1.0 rank among all occupations with wage data. Derived via PERCENT_RANK() window on median_annual_wage. Null if wage unavailable (23 rows). Input to wage_tier derivation. |
| wage_percentile_education_tier | BT-049 | numeric | NULLABLE | true | false | 0.0-1.0 rank within same education_code tier. Derived via PERCENT_RANK() window partitioned by education_code, ordered by median_annual_wage. Null if wage unavailable (23 rows). Backs the Ceiling boss fight. |
| wage_tier | BT-050 | text | NULLABLE | false | false | Categorical bucketing of wage_percentile_overall into five tiers: low, below_average, above_average, high, very_high. Null if wage unavailable (23 rows). See Derivation Rules. |

### Entry Requirements (Carried)

Education and training classification fields carried from Silver. Redundant text labels dropped (education_typical, work_experience, training_typical).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| education_code | BT-038 | numeric | NULLABLE | false | false | BLS education level code (1-8). Carried from Silver verbatim. Serves as partition key for wage_percentile_education_tier. |
| education_level_name | BT-039 | text | NULLABLE | false | false | Human-readable education level label. Carried from Silver verbatim. |
| work_experience_code | BT-044 | numeric | NULLABLE | false | false | BLS work experience code (1-3). Carried from Silver verbatim. |
| training_code | BT-045 | numeric | NULLABLE | false | false | BLS training code (1-6). Carried from Silver verbatim. |

### Market Opportunity (Derived)

Composite market health indicator combining growth direction and opportunity volume. Backs the Market boss fight.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| market_score | BT-051 | numeric | NULLABLE | true | false | Combined growth + openings signal on 1-10 scale. Formula: 0.6 * grw_score + 0.4 * openings_score. Null if grw_score or openings_annual_avg is null. |
| market_score_rounded | BT-051 | numeric | NULLABLE | false | false | Integer 1-10 for display. ROUND(market_score). Null if market_score is null. |

### Data Quality Context (Derived)

Quality classification and completeness metrics assigned to every occupation profile. Unlike other derived groups, confidence_tier is required on every row (no nulls).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| confidence_tier | BT-052 | text | NOT NULL | false | false | Three-level data quality classification: "high" (specific occupation with wage data), "medium" (broad or catchall occupation with wage data), "low" (wage data unavailable). Every row receives a tier. |
| data_completeness | BT-053 | numeric | NOT NULL | false | false | Proportion of four core fields (median_annual_wage, employment_current, employment_change_pct, openings_annual_avg) that are non-null. Values: 0.0, 0.25, 0.5, 0.75, 1.0. In practice, 0.0 not expected. |

### FutureProof Stat Mapping (Static)

Documentation metadata declaring which FutureProof game-system elements this data product backs.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| backs_stats | BT-054 | text | NOT NULL | false | false | Comma-separated list of FutureProof pentagon stats this occupation data feeds. Always "ERN,GRW" for this data product. |
| backs_bosses | BT-054 | text | NOT NULL | false | false | Comma-separated list of boss fights this data feeds. Always "Market,Ceiling" for this data product. |

### Pipeline Metadata

Pipeline infrastructure fields. source_load_date carried from Silver; promoted_at generated at promotion time.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the raw zone. Pipeline metadata carried from Silver. |
| promoted_at | BT-026 | timestamp | NOT NULL | false | false | Timestamp when the row was promoted to the Gold zone consumable table. Generated at promotion time. Replaces Silver's ingested_at. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 30 | Total attributes |
| 1 | Natural key component (soc_code) |
| 1 | Surrogate key (record_id) |
| 9 | CDE attributes (soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage, grw_score, wage_percentile_overall, wage_percentile_education_tier, market_score) |
| 0 | PII attributes |
| 13 | Nullable attributes |
| 17 | NOT NULL attributes |
| 12 | Derived attributes (record_id, grw_score, grw_score_rounded, wage_percentile_overall, wage_percentile_education_tier, wage_tier, market_score, market_score_rounded, confidence_tier, data_completeness, backs_stats, backs_bosses) |
| 16 | Carried from Silver (verbatim or with field selection) |
| 2 | Pipeline metadata (source_load_date carried, promoted_at new) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure, count, ratio, rank, or code. May be aggregated. | DOUBLE (monetary, ratios, scores, ranks, percentages), BIGINT (counts), INTEGER (codes) |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

All derivation rules are null-safe. Null inputs propagate to null outputs unless otherwise specified.

### Carried from Silver (no transformation)

| Attribute | Source | Rule |
|-----------|--------|------|
| soc_code | base.bls_ooh.soc_code | Verbatim |
| occupation_title | base.bls_ooh.occupation_title | Verbatim |
| soc_major_group | base.bls_ooh.soc_major_group | Verbatim |
| soc_major_group_name | base.bls_ooh.soc_major_group_name | Verbatim |
| broad_occupation_flag | base.bls_ooh.broad_occupation_flag | Verbatim |
| catchall_flag | base.bls_ooh.catchall_flag | Verbatim |
| employment_current | base.bls_ooh.employment_current | Verbatim |
| employment_projected | base.bls_ooh.employment_projected | Verbatim |
| employment_change_pct | base.bls_ooh.employment_change_pct | Verbatim |
| openings_annual_avg | base.bls_ooh.openings_annual_avg | Verbatim |
| growth_category | base.bls_ooh.growth_category | Verbatim |
| median_annual_wage | base.bls_ooh.median_annual_wage | Verbatim |
| wage_available | base.bls_ooh.wage_available | Verbatim |
| education_code | base.bls_ooh.education_code | Verbatim |
| education_level_name | base.bls_ooh.education_level_name | Verbatim |
| work_experience_code | base.bls_ooh.work_experience_code | Verbatim |
| training_code | base.bls_ooh.training_code | Verbatim |
| source_load_date | base.bls_ooh.source_load_date | Verbatim |

### Surrogate Key

| Attribute | Rule | Source Attributes |
|-----------|------|-------------------|
| record_id | `compute_grain_id(row, ['soc_code'], prefix='op')` | soc_code |

### GRW Score (Piecewise Linear Function)

Maps employment_change_pct to a 1.0-10.0 score using piecewise linear interpolation anchored to BLS growth benchmarks. Null if employment_change_pct is null.

| Input Range (employment_change_pct) | Output Range (grw_score) | Interpolation Formula | Rationale |
|-------------------------------------|--------------------------|----------------------|-----------|
| <= -20.0 | 1.0 (floor) | Fixed | Severe decline |
| -20.0 to -10.0 | 1.0 to 2.5 | 1.0 + (pct - (-20.0)) / ((-10.0) - (-20.0)) * (2.5 - 1.0) | Fast decline |
| -10.0 to -1.0 | 2.5 to 4.0 | 2.5 + (pct - (-10.0)) / ((-1.0) - (-10.0)) * (4.0 - 2.5) | Moderate decline |
| -1.0 to 1.0 | 4.0 to 5.0 | 4.0 + (pct - (-1.0)) / (1.0 - (-1.0)) * (5.0 - 4.0) | Stable |
| 1.0 to 5.0 | 5.0 to 6.5 | 5.0 + (pct - 1.0) / (5.0 - 1.0) * (6.5 - 5.0) | Below-average to average growth |
| 5.0 to 10.0 | 6.5 to 7.5 | 6.5 + (pct - 5.0) / (10.0 - 5.0) * (7.5 - 6.5) | Above-average growth |
| 10.0 to 20.0 | 7.5 to 9.0 | 7.5 + (pct - 10.0) / (20.0 - 10.0) * (9.0 - 7.5) | Strong growth |
| 20.0 to 50.0 | 9.0 to 10.0 | 9.0 + (pct - 20.0) / (50.0 - 20.0) * (10.0 - 9.0) | Exceptional growth |
| >= 50.0 | 10.0 (cap) | Fixed | Capped at maximum |

**Design note:** National average growth (~4%) maps to approximately 6.0, which places "average" slightly above the scale midpoint. This is intentional -- growth is a positive outcome in FutureProof, so the midpoint should represent "below average, not great" rather than "average."

**Verification examples (from spec golden dataset):**
- Software Developers (15-1252): pct=15.8 -> band 10.0-20.0 -> 7.5 + (15.8-10.0)/(20.0-10.0) * 1.5 = 7.5 + 0.87 = **8.37**
- Registered Nurses (29-1141): pct=4.9 -> band 1.0-5.0 -> 5.0 + (4.9-1.0)/(5.0-1.0) * 1.5 = 5.0 + 1.46 = **6.46**

### GRW Score Rounded

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| grw_score_rounded | `ROUND(grw_score)` (standard rounding, 0 decimal places) | grw_score | Null if grw_score is null |

### Wage Percentile Ranks (Window Functions)

| Attribute | Rule | Partition | Order | Null Handling |
|-----------|------|-----------|-------|---------------|
| wage_percentile_overall | `PERCENT_RANK() OVER (ORDER BY median_annual_wage)` | None (all occupations with wage data) | median_annual_wage ASC | Rows with null median_annual_wage excluded from window; result is null for those rows |
| wage_percentile_education_tier | `PERCENT_RANK() OVER (PARTITION BY education_code ORDER BY median_annual_wage)` | education_code | median_annual_wage ASC | Rows with null median_annual_wage excluded from window; result is null for those rows |

**Percentile rank semantics:** PERCENT_RANK returns 0.0 for the lowest value in the partition and 1.0 for the highest. With 809 wage-reporting occupations, the granularity of wage_percentile_overall is approximately 1/808 = 0.00124 per rank step.

### Wage Tier Derivation

Bucketed from wage_percentile_overall. Null if wage_percentile_overall is null.

| Tier Value | Condition | Business Interpretation |
|------------|-----------|------------------------|
| "low" | wage_percentile_overall < 0.25 | Bottom quartile earners |
| "below_average" | 0.25 <= wage_percentile_overall < 0.50 | Below median |
| "above_average" | 0.50 <= wage_percentile_overall < 0.75 | Above median |
| "high" | 0.75 <= wage_percentile_overall < 0.90 | Strong earners |
| "very_high" | wage_percentile_overall >= 0.90 | Top 10% of occupations |
| NULL | wage_percentile_overall IS NULL | Wage data unavailable (23 occupations) |

### Market Score Derivation

Two-step computation combining growth direction (60%) and opportunity volume (40%).

**Step 1: Compute openings_score**

| Attribute | Rule | Null Condition |
|-----------|------|----------------|
| openings_score (intermediate, not persisted) | `1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg)` | Null if openings_annual_avg is null |

Maps the percent rank of annual openings to a 1.0-10.0 scale. The lowest-openings occupation gets 1.0; the highest gets 10.0.

**Step 2: Compute market_score**

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| market_score | `0.6 * grw_score + 0.4 * openings_score` | grw_score, openings_score | Null if either grw_score or openings_annual_avg is null |

**Step 3: Compute market_score_rounded**

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| market_score_rounded | `ROUND(market_score)` | market_score | Null if market_score is null |

**Design note:** A 60/40 weighting means growth direction dominates. An occupation growing at 15% with 200 total annual openings scores lower than one growing at 8% with 100K annual openings. This matches the business insight that labor market size matters for career viability.

### Confidence Tier Derivation

Evaluated top-to-bottom; first matching condition wins. Every row receives a tier (no nulls).

| Tier Value | Condition | Business Interpretation |
|------------|-----------|------------------------|
| "high" | broad_occupation_flag = False AND catchall_flag = False AND wage_available = True | Specific occupation with complete data; highest guidance quality |
| "medium" | (broad_occupation_flag = True OR catchall_flag = True) AND wage_available = True | Broad or catchall occupation with wage data; real data but heterogeneous group |
| "low" | wage_available = False | Wage data unavailable regardless of other flags; weakest data for FutureProof |

**Distribution expectation:** "high" is the majority (occupations with wage data that are neither broad nor catchall). "low" count: exactly 23 (the null-wage occupations).

### Data Completeness Derivation

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| data_completeness | `(CASE WHEN median_annual_wage IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN employment_current IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN employment_change_pct IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN openings_annual_avg IS NOT NULL THEN 1 ELSE 0 END) / 4.0` | median_annual_wage, employment_current, employment_change_pct, openings_annual_avg | Never null (always 0.0-1.0) |

**Value set constraint:** Exactly {0.0, 0.25, 0.5, 0.75, 1.0}. In practice, 0.0 is not expected because all occupations have employment data.

### Static Fields

| Attribute | Rule | Value |
|-----------|------|-------|
| backs_stats | Static string, same for all 832 rows | "ERN,GRW" |
| backs_bosses | Static string, same for all 832 rows | "Market,Ceiling" |

### Pipeline Metadata

| Attribute | Rule | Source |
|-----------|------|--------|
| promoted_at | Current timestamp at promotion time | Generated by promote() function |

---

## Nullability Semantics

Null values in this model carry specific business meaning:

| Pattern | Business Meaning |
|---------|-----------------|
| median_annual_wage IS NULL | BLS does not report wage data for this occupation (23 occupations: elected officials, self-employed-dominated fields). Not a data quality issue -- a real absence. |
| wage_percentile_overall IS NULL | Same 23 occupations. Cannot rank what has no value. |
| wage_percentile_education_tier IS NULL | Same 23 occupations. |
| wage_tier IS NULL | Same 23 occupations. Exact correspondence with wage_available = False. |
| grw_score IS NULL | employment_change_pct is null (0 rows in current data). Defensive nullability for future data changes. |
| grw_score_rounded IS NULL | Propagated from grw_score null. |
| market_score IS NULL | Either grw_score or openings_annual_avg is null. |
| market_score_rounded IS NULL | Propagated from market_score null. |
| employment_current/projected IS NULL | Extremely rare. Defensive nullability. Current data has full coverage. |
| employment_change_pct IS NULL | Insufficient data for projection. Defensive nullability. |
| openings_annual_avg IS NULL | Extremely rare. Defensive nullability. |
| education_code IS NULL | BLS did not classify this occupation's education requirement. Defensive nullability; current data has full coverage. |

**Key invariant:** confidence_tier = "low" if and only if wage_available = False. When confidence_tier = "low", all wage-derived fields (wage_percentile_overall, wage_percentile_education_tier, wage_tier) are guaranteed null. Growth-derived fields (grw_score, market_score) may still have values.

---

## Dropped Fields (from Silver, with justification)

| Silver Attribute | Dropped? | Justification |
|-----------------|----------|---------------|
| employment_change | Dropped | Redundant with employment_change_pct for Gold consumers. Absolute change less useful than percentage for stat scoring. Available in Silver if needed. |
| median_wage_capped | Dropped | All False in current data. The wage_available flag is more useful. Preserved in Silver for lineage. |
| education_typical | Dropped | Redundant with education_level_name (derived from code). Kept the normalized name, dropped the raw label. |
| work_experience | Dropped | Redundant with work_experience_code. Code is sufficient for Gold consumers. |
| training_typical | Dropped | Redundant with training_code. Code is sufficient for Gold consumers. |
| ingested_at | Dropped | Silver metadata replaced by promoted_at in Gold. |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attribute Group | Attributes | Notes |
|-------------------|------------------------|------------|-------|
| Occupation Profile | Occupation Profile (core identity) | record_id, soc_code, occupation_title, soc_major_group, soc_major_group_name, broad_occupation_flag, catchall_flag | Central entity. soc_code is the natural key. SOC Major Group absorbed here. |
| Growth Assessment | Growth Assessment | employment_current, employment_projected, employment_change_pct, openings_annual_avg, growth_category, grw_score, grw_score_rounded | Employment fields carried from Silver. GRW score derived in Gold. |
| Wage Position | Wage Position | median_annual_wage, wage_available, wage_percentile_overall, wage_percentile_education_tier, wage_tier | Wage carried from Silver. Percentile ranks and tier derived in Gold. |
| (Entry Requirements) | Entry Requirements | education_code, education_level_name, work_experience_code, training_code | Absorbed into Occupation Profile in conceptual model but tracked as separate logical group for clarity. |
| Market Opportunity | Market Opportunity | market_score, market_score_rounded | Derived from grw_score and openings_annual_avg. |
| Data Quality Context | Data Quality Context | confidence_tier, data_completeness | Derived from flags and field nullity. Both NOT NULL. |
| FutureProof Stat Mapping | FutureProof Stat Mapping | backs_stats, backs_bosses | Static documentation fields. |
| (Pipeline Metadata) | Pipeline Metadata | source_load_date, promoted_at | Not a conceptual entity -- pipeline infrastructure. |

---

## Continuity with Silver Logical Model

This logical model builds on `governance/models/silver-base-bls-ooh-logical.md`:

| Silver Logical Attribute | Gold Disposition | Gold Attribute | Change |
|-------------------------|-----------------|----------------|--------|
| record_id (prefix 'ooh') | Recomputed | record_id (prefix 'op') | Prefix changes to distinguish zones |
| soc_code | Carried | soc_code | Verbatim |
| occupation_title | Carried | occupation_title | Verbatim |
| soc_major_group | Carried | soc_major_group | Verbatim |
| soc_major_group_name | Carried | soc_major_group_name | Verbatim |
| broad_occupation_flag | Carried | broad_occupation_flag | Verbatim |
| catchall_flag | Carried | catchall_flag | Verbatim |
| employment_current | Carried | employment_current | Verbatim |
| employment_projected | Carried | employment_projected | Verbatim |
| employment_change | Dropped | -- | Redundant with employment_change_pct |
| employment_change_pct | Carried | employment_change_pct | Verbatim |
| openings_annual_avg | Carried | openings_annual_avg | Verbatim |
| growth_category | Carried | growth_category | Verbatim |
| median_annual_wage | Carried | median_annual_wage | Verbatim |
| median_wage_capped | Dropped | -- | All False; wage_available more useful |
| wage_available | Carried | wage_available | Verbatim |
| education_typical | Dropped | -- | Redundant with education_level_name |
| education_code | Carried | education_code | Verbatim |
| education_level_name | Carried | education_level_name | Verbatim |
| work_experience | Dropped | -- | Redundant with work_experience_code |
| work_experience_code | Carried | work_experience_code | Verbatim |
| training_typical | Dropped | -- | Redundant with training_code |
| training_code | Carried | training_code | Verbatim |
| source_load_date | Carried | source_load_date | Verbatim |
| ingested_at | Dropped | promoted_at (new) | Replaced by Gold-zone promotion timestamp |

**New in Gold (12 attributes):**
- 2 growth score attributes (grw_score, grw_score_rounded) -- derived via piecewise linear function
- 3 wage position attributes (wage_percentile_overall, wage_percentile_education_tier, wage_tier) -- derived via window functions and bucketing
- 2 market opportunity attributes (market_score, market_score_rounded) -- derived via composite formula
- 2 data quality attributes (confidence_tier, data_completeness) -- derived via conditional logic
- 2 stat mapping attributes (backs_stats, backs_bosses) -- static documentation
- 1 pipeline metadata attribute (promoted_at) -- generated at promotion time

---

## Constraints and Invariants

### Hard Constraints (DQ P0 -- block promotion if violated)

| Constraint | Rule | Scope |
|------------|------|-------|
| Grain uniqueness | Zero duplicates on soc_code | Table-wide |
| Record ID uniqueness | Zero duplicates on record_id | Table-wide |
| Row count exact | Exactly 832 rows (no rows added or dropped from Silver) | Table-wide |
| GRW score range | 1.0 <= grw_score <= 10.0 for all non-null rows | Row-level |
| GRW score rounded range | 1 <= grw_score_rounded <= 10 for all non-null rows | Row-level |
| GRW score rounded accuracy | grw_score_rounded = ROUND(grw_score) for all rows | Row-level |
| Market score range | 1.0 <= market_score <= 10.0 for all non-null rows | Row-level |
| Market score rounded range | 1 <= market_score_rounded <= 10 for all non-null rows | Row-level |
| Market score rounded accuracy | market_score_rounded = ROUND(market_score) for all rows | Row-level |
| Wage percentile range | 0.0 <= wage_percentile_overall <= 1.0 when non-null | Row-level |
| Wage percentile education range | 0.0 <= wage_percentile_education_tier <= 1.0 when non-null | Row-level |
| Wage percentile null count | Exactly 23 rows where wage_percentile_overall IS NULL | Table-wide |
| Wage tier value set | wage_tier IN ('low', 'below_average', 'above_average', 'high', 'very_high') when non-null | Row-level |
| Wage tier null correspondence | wage_tier IS NULL if and only if wage_available = False | Row-level |
| Confidence tier completeness | confidence_tier IS NOT NULL for every row | Row-level |
| Confidence tier value set | confidence_tier IN ('high', 'medium', 'low') | Row-level |
| Confidence tier low count | Exactly 23 rows where confidence_tier = 'low' | Table-wide |
| Data completeness completeness | data_completeness IS NOT NULL for every row | Row-level |
| Data completeness value set | data_completeness IN (0.0, 0.25, 0.5, 0.75, 1.0) | Row-level |
| Stat mapping completeness | backs_stats IS NOT NULL AND backs_bosses IS NOT NULL for every row | Row-level |
| Stat mapping values | backs_stats = 'ERN,GRW' AND backs_bosses = 'Market,Ceiling' for every row | Row-level |

### Soft Constraints (DQ P1 -- warn but do not block)

| Constraint | Rule | Scope |
|------------|------|-------|
| GRW score mean | Mean grw_score approximately 5.5-6.5 (given national average growth ~4%) | Table-wide |
| GRW score distribution | grw_score_rounded has representation across at least 8 of 10 integer buckets (1-10) | Table-wide |
| Market score dispersion | Standard deviation of market_score > 1.0 (no excessive clustering) | Table-wide |
| Data completeness no zeros | No rows with data_completeness = 0.0 (all occupations have employment data) | Table-wide |
| Null propagation consistency | market_score IS NULL when grw_score IS NULL OR openings_annual_avg IS NULL | Row-level |

---

## Modeling Decisions

1. **Single denormalized table.** All seven conceptual entities flatten into one table. The 1:1 and 1:0..1 cardinalities make separate tables unnecessary. This matches the Gold career outcomes pattern.

2. **Entry Requirements as a separate logical group.** The conceptual model absorbed entry requirements into Occupation Profile, but the logical model separates them because education_code serves as a partition key for wage_percentile_education_tier. Explicit grouping makes this dependency visible.

3. **openings_score not persisted.** The intermediate openings_score (PERCENT_RANK mapped to 1-10) is computed inline during market_score derivation but is not stored as a separate attribute. Persisting it would add a column with no direct consumer use case and could be recomputed from openings_annual_avg if needed. The market_score formula is the authoritative combination.

4. **GRW score piecewise function fully specified.** All 8 breakpoint segments are documented with explicit interpolation formulas and verification examples. This level of detail enables deterministic implementation and golden dataset validation without ambiguity.

5. **CDE assignments expanded for Gold.** Silver had 5 CDEs (soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage). Gold adds 4 more: grw_score, wage_percentile_overall, wage_percentile_education_tier, and market_score. These are the derived fields that directly feed FutureProof stats and boss fights -- the primary analytical output of this data product.

6. **Confidence tier is three-level, not four.** Unlike the career outcomes confidence tier (BT-024) which has four levels (high/medium/low/insufficient), occupation confidence tier (BT-052) uses three levels. There is no "insufficient" level because every occupation has at least employment data -- the worst case is missing wages. This is a distinct business term (BT-052 vs. BT-024) with a different derivation.

7. **growth_category marked NOT NULL.** The spec marks growth_category as "yes" for required. In Silver, growth_category is nullable (null when employment_change_pct is null), but in the current dataset employment_change_pct is never null for any of the 832 occupations, so growth_category is always populated. The Gold model marks it NOT NULL, matching the spec. If future data introduces null employment_change_pct values, this would need to be revisited.

---

## Scope and Boundaries

- This logical model covers the `consumable.occupation_profiles` table in the Gold zone only
- Source is the Silver `base.bls_ooh` table (single-source; no cross-source joins)
- CIP-to-SOC crosswalk integration is a future spec and not modeled here
- O*NET data is a separate future source and not included here
- College Scorecard career outcomes are a separate Gold product and not included here
- The model assumes 832 rows (all occupations from Silver, including broad and catchall categories)
- MCP zone serving is downstream and not part of this model
