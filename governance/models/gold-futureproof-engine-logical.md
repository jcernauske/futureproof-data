# Logical Model: gold-futureproof-engine

**Status:** APPROVED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Domain:** Education / Career Guidance
**Spec:** docs/specs/gold-futureproof-engine.md
**Conceptual Model:** governance/models/gold-futureproof-engine-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-09
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)
**Upstream Models:** gold-career-outcomes-college-scorecard-logical, gold-occupation-profiles-bls-ooh-logical, gold-onet-profiles-logical, crosswalk-cip-soc-logical

---

```mermaid
erDiagram
    PROGRAM_CAREER_PATH {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        identifier cipcode NK
        text program_name
        identifier cip_family
        text cip_family_name
        identifier soc_code NK
        text occupation_title
        text soc_major_group_name
    }
    PENTAGON_STATS {
        identifier grain_ref PK
        numeric stat_ern
        numeric stat_roi
        numeric stat_res
        numeric stat_grw
        numeric stat_hmn
    }
    BOSS_FIGHT_PROFILE {
        identifier grain_ref PK
        numeric boss_ai_score
        numeric boss_loans_score
        numeric boss_market_score
        numeric boss_burnout_score
        numeric boss_ceiling_score
    }
    PROGRAM_CONTEXT {
        identifier grain_ref PK
        numeric earnings_1yr_median
        numeric earnings_1yr_p25
        numeric earnings_1yr_p75
        numeric debt_median
        numeric debt_to_earnings_annual
        text confidence_tier_program
    }
    OCCUPATION_CONTEXT {
        identifier grain_ref PK
        numeric median_annual_wage
        text growth_category
        numeric employment_current
        text education_level_name
        text top_5_activities
        text top_human_activities
        text burnout_drivers
        numeric time_pressure
        numeric work_hours
    }
    DATA_QUALITY {
        identifier grain_ref PK
        text match_quality
        numeric stats_available_count
        numeric bosses_available_count
        text overall_confidence
    }
    PIPELINE_METADATA {
        identifier grain_ref PK
        timestamp promoted_at
    }
    CAREER_BRANCH {
        identifier record_id PK
        identifier soc_code NK
        text source_title
        identifier related_soc_code NK
        text related_title
        numeric best_index
        text relatedness_tier
        boolean is_primary
    }
    SOURCE_STATS {
        identifier branch_ref PK
        numeric source_grw
        numeric source_hmn
        numeric source_burnout
        numeric source_wage
    }
    RELATED_STATS {
        identifier branch_ref PK
        numeric related_grw
        numeric related_hmn
        numeric related_burnout
        numeric related_wage
        text related_growth_category
        text related_education_level
    }
    STAT_DELTAS {
        identifier branch_ref PK
        numeric grw_delta
        numeric hmn_delta
        numeric burnout_delta
        numeric wage_delta
        boolean branch_has_full_data
    }
    BRANCH_METADATA {
        identifier branch_ref PK
        timestamp promoted_at
    }
    PROGRAM_CAREER_PATH ||--o| PENTAGON_STATS : "scored by"
    PROGRAM_CAREER_PATH ||--o| BOSS_FIGHT_PROFILE : "challenged by"
    PROGRAM_CAREER_PATH ||--o| PROGRAM_CONTEXT : "contextualized by"
    PROGRAM_CAREER_PATH ||--o| OCCUPATION_CONTEXT : "described by"
    PROGRAM_CAREER_PATH ||--|| DATA_QUALITY : "qualified by"
    PROGRAM_CAREER_PATH ||--|| PIPELINE_METADATA : "tracked by"
    CAREER_BRANCH ||--o| SOURCE_STATS : "profiled (source)"
    CAREER_BRANCH ||--o| RELATED_STATS : "profiled (target)"
    CAREER_BRANCH ||--|| STAT_DELTAS : "compared by"
    CAREER_BRANCH ||--|| BRANCH_METADATA : "tracked by"
```

---

## Design Rationale: Two Denormalized Tables

The conceptual model identifies 11 entities across two product tables. Following the established Gold zone pattern from `consumable.career_outcomes` and `consumable.occupation_profiles`, each product table flattens its constituent entities into a single wide denormalized row. The logical model groups attributes by conceptual entity to preserve semantic clarity while acknowledging the physical denormalization.

This is appropriate because:
1. The Gold consumable layer optimizes for the primary query patterns (school + major + career = outcomes; occupation + branch = comparison)
2. All conceptual entities within each table resolve to 1:1 or 1:0..1 per row at their respective grains
3. Downstream consumers (Gemma agent, pentagon visualization, boss fights, branch trees) expect flat tables
4. Cross-source joins are fully resolved at this layer -- no further joins needed at query time

---

## Grain and Uniqueness

### Table 1: consumable.program_career_paths

| Property | Value |
|----------|-------|
| **Grain** | One row per institution x program x occupation (unitid x cipcode x soc_code) |
| **Natural key fields** | `unitid`, `cipcode`, `soc_code` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['unitid', 'cipcode', 'soc_code'], prefix='pcp')`) |
| **Uniqueness constraint** | Zero duplicates on (unitid, cipcode, soc_code). Enforced at promote time after dedup. |
| **Expected cardinality** | 150,000-500,000 rows (CIP prefix fan-out from 4 Gold + 1 Silver source tables) |
| **Dedup strategy** | CIP prefix join may produce duplicate (unitid, cipcode, soc_code) rows when the same SOC appears via multiple 6-digit crosswalk CIPs. Keep one row per grain, preferring the row with the most non-null stat values. |

### Table 2: consumable.career_branches

| Property | Value |
|----------|-------|
| **Grain** | One row per occupation pair (soc_code x related_soc_code) |
| **Natural key fields** | `soc_code`, `related_soc_code` |
| **Surrogate key** | `record_id` (deterministic hash via `compute_grain_id(row, ['soc_code', 'related_soc_code'], prefix='br')`) |
| **Uniqueness constraint** | Zero duplicates on (soc_code, related_soc_code). 1:1 enrichment of career_transitions. |
| **Expected cardinality** | 15,944 rows (same as source career_transitions) |

---

## Join Chain (Table 1: program_career_paths)

The cross-source join chain resolves four Gold tables and one Silver table into the unified program-career row. This is the most complex join in the FutureProof pipeline.

| Step | Join | Type | Left Key | Right Key | Notes |
|------|------|------|----------|-----------|-------|
| 1 | career_outcomes as base | -- | -- | -- | Start with College Scorecard Gold. Grain: unitid x cipcode x credlev. |
| 2 | cip_soc_crosswalk | INNER | `career_outcomes.cipcode` | `LEFT(crosswalk.cipcode, 5)` | CIP prefix match (BT-086). Truncates 6-digit crosswalk CIP to match 4-digit Scorecard CIP. Fan-out: one Scorecard row produces N rows (one per mapped SOC). Programs with no crosswalk match are filtered out (~9% of CIPs, ~3% of rows). |
| 3 | occupation_profiles | LEFT | `crosswalk.soc_code` | `occupation_profiles.soc_code` | Adds BLS data (GRW, market, wage, education). LEFT JOIN preserves rows without BLS coverage. |
| 4 | onet_work_profiles | LEFT | `crosswalk.soc_code` | `onet_work_profiles.bls_soc_code` | Adds O*NET data (HMN, burnout, activities). LEFT JOIN preserves rows without O*NET coverage. |
| 5 | Dedup on grain | -- | -- | -- | Collapse to (unitid, cipcode, soc_code). Prefer row with most non-null stats when duplicates exist from multiple 6-digit CIP matches to the same SOC. |

### Join Chain (Table 2: career_branches)

| Step | Join | Type | Left Key | Right Key | Notes |
|------|------|------|----------|-----------|-------|
| 1 | career_transitions as base | -- | -- | -- | Start with career transitions Gold. Grain: soc_code x related_soc_code. |
| 2 | occupation_profiles (source) | LEFT | `career_transitions.soc_code` | `occupation_profiles.soc_code` | Source occupation BLS stats. |
| 3 | onet_work_profiles (source) | LEFT | `career_transitions.soc_code` | `onet_work_profiles.bls_soc_code` | Source occupation O*NET stats. |
| 4 | occupation_profiles (related) | LEFT | `career_transitions.related_soc_code` | `occupation_profiles.soc_code` | Target occupation BLS stats. |
| 5 | onet_work_profiles (related) | LEFT | `career_transitions.related_soc_code` | `onet_work_profiles.bls_soc_code` | Target occupation O*NET stats. |

---

## Attribute Definitions: Table 1 (consumable.program_career_paths)

Attributes are grouped by the conceptual entity they originate from. `NK` denotes natural key components.

### Program Career Path (Core Identity)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from (unitid, cipcode, soc_code) via `compute_grain_id()` with prefix 'pcp'. |
| unitid | BT-001 | numeric | NOT NULL | true | false | IPEDS institution identifier. 6-digit integer. Carried from career_outcomes. |
| institution_name | BT-002 | text | NOT NULL | false | false | Official institution name from IPEDS. Carried from career_outcomes. |
| cipcode | BT-003 | identifier | NOT NULL | true | false | CIP program code in XX.XX format (4-digit Scorecard granularity). Always string, never float. Carried from career_outcomes. |
| program_name | BT-004 | text | NOT NULL | false | false | Human-readable program description. Carried from career_outcomes. |
| cip_family | BT-005 | identifier | NOT NULL | false | false | 2-digit CIP family prefix. Carried from career_outcomes. |
| cip_family_name | BT-006 | text | NOT NULL | false | false | Human-readable CIP family label. Carried from career_outcomes. |
| soc_code | BT-027 | identifier | NOT NULL | true | false | SOC occupation code in XX-XXXX format. Carried from cip_soc_crosswalk. |
| occupation_title | BT-028 | text | NOT NULL | false | false | Official occupation name. Sourced from occupation_profiles (preferred) or onet_work_profiles (fallback). |
| soc_major_group_name | BT-030 | text | NULLABLE | false | false | SOC major group label. Carried from occupation_profiles. Null if BLS join fails. |

### Pentagon Stats (1-10 Scale)

All pentagon stats are integer-domain values on a 1-10 scale. Null propagation rules are specified per attribute.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| stat_ern | BT-078 | numeric | NULLABLE | true | false | Earning Power score (1-10). Blended from program-level earnings rank and occupation-level wage percentile. See ERN derivation. |
| stat_roi | BT-079 | numeric | NULLABLE | true | false | Return on Investment score (1-10). Inverse mapping of debt-to-earnings ratio. See ROI derivation. |
| stat_res | BT-080 | numeric | NULLABLE | false | false | AI Resilience score (1-10). PLACEHOLDER: always null in MVP. Pending Karpathy integration. |
| stat_grw | BT-047 | numeric | NULLABLE | true | false | Growth score (1-10). Carried directly from occupation_profiles.grw_score_rounded. Null if BLS join fails. |
| stat_hmn | BT-066 | numeric | NULLABLE | true | false | Human Edge score (1-10). Carried directly from onet_work_profiles.hmn_score_rounded. Null if O*NET join fails. |

### Boss Fight Profile (1-10 Scale)

All boss scores are integer-domain values on a 1-10 scale. Higher score means a stronger boss (worse for the student).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| boss_ai_score | BT-083 | numeric | NULLABLE | false | false | AI Boss strength (1-10). PLACEHOLDER: always null in MVP. Same dependency as stat_res. |
| boss_loans_score | BT-084 | numeric | NULLABLE | true | false | Student Loans Boss strength (1-10). Exact inverse of stat_roi: `11 - stat_roi`. Null when stat_roi is null. |
| boss_market_score | BT-051 | numeric | NULLABLE | true | false | Market Boss strength (1-10). Carried from occupation_profiles.market_score_rounded. Null if BLS join fails. |
| boss_burnout_score | BT-068 | numeric | NULLABLE | true | false | Burnout Boss strength (1-10). Carried from onet_work_profiles.burnout_score_rounded. Null if O*NET join fails. |
| boss_ceiling_score | BT-085 | numeric | NULLABLE | true | false | Ceiling Boss strength (1-10). Derived from wage percentile within education tier. See Ceiling derivation. |

### Program Context (College Scorecard)

Financial context from the career_outcomes Gold table. These are the raw inputs that feed ERN and ROI derivations.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| earnings_1yr_median | BT-009 | numeric | NULLABLE | true | false | Median 1-year post-completion earnings. Carried from career_outcomes. Subject to privacy suppression. |
| earnings_1yr_p25 | BT-018 | numeric | NULLABLE | false | false | 25th percentile earnings (effort slider: low focus). Carried from career_outcomes. |
| earnings_1yr_p75 | BT-018 | numeric | NULLABLE | false | false | 75th percentile earnings (effort slider: high focus). Carried from career_outcomes. |
| debt_median | BT-011 | numeric | NULLABLE | true | false | Median cumulative federal loan debt at completion. Carried from career_outcomes. |
| debt_to_earnings_annual | BT-019 | numeric | NULLABLE | true | false | Ratio of debt to 1-year earnings. Key affordability metric and input to stat_roi derivation. Carried from career_outcomes. |
| confidence_tier_program | BT-024 | text | NULLABLE | false | false | Scorecard-level confidence tier (high/medium/low/insufficient). Carried from career_outcomes. Null only if career_outcomes source is missing this field. |

### Occupation Context (BLS + O*NET)

Occupation-level descriptive context carried from upstream Gold tables. All nullable because LEFT JOINs may fail.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| median_annual_wage | BT-036 | numeric | NULLABLE | true | false | BLS median annual wage for the occupation. Carried from occupation_profiles. |
| growth_category | BT-041 | text | NULLABLE | false | false | BLS growth classification (declining_fast through booming). Carried from occupation_profiles. |
| employment_current | BT-031 | numeric | NULLABLE | false | false | Current employment count. Carried from occupation_profiles. |
| education_level_name | BT-039 | text | NULLABLE | false | false | Typical entry-level education requirement. Carried from occupation_profiles. |
| top_5_activities | BT-063 | text | NULLABLE | false | false | JSON string: top 5 work activities by importance. Carried from onet_work_profiles. |
| top_human_activities | BT-063 | text | NULLABLE | false | false | JSON string: top activities with highest human edge. Carried from onet_work_profiles. |
| burnout_drivers | BT-068 | text | NULLABLE | false | false | JSON string: top burnout-contributing work conditions. Carried from onet_work_profiles. |
| time_pressure | BT-068 | numeric | NULLABLE | false | false | Individual burnout element: time pressure score. Carried from onet_work_profiles. |
| work_hours | BT-068 | numeric | NULLABLE | false | false | Duration of typical work week. Carried from onet_work_profiles. |

### Data Quality (Derived)

Quality classification mandatory on every row. No nulls in this group.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| match_quality | BT-093 | text | NOT NULL | true | false | Classification of cross-source join success: 'full', 'partial_no_onet', 'partial_no_bls', 'scorecard_only'. Derived at Gold time from actual join results, NOT from upstream crosswalk Silver flags. |
| stats_available_count | BT-087 | numeric | NOT NULL | false | false | Count of non-null pentagon stats (0-5). Maximum 4 in MVP since stat_res is always null. |
| bosses_available_count | BT-088 | numeric | NOT NULL | false | false | Count of non-null boss fight scores (0-5). Maximum 4 in MVP since boss_ai_score is always null. |
| overall_confidence | BT-089 | text | NOT NULL | true | false | Synthesized quality tier: 'high', 'medium', or 'low'. Derived from stats_available_count and match_quality. |

### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| promoted_at | BT-026 | timestamp | NOT NULL | false | false | Timestamp when the row was promoted to the Gold consumable table. Generated at promotion time. |

---

## Attribute Definitions: Table 2 (consumable.career_branches)

### Career Branch (Core Identity)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from (soc_code, related_soc_code) via `compute_grain_id()` with prefix 'br'. |
| soc_code | BT-027 | identifier | NOT NULL | true | false | Source occupation SOC code (XX-XXXX). Carried from career_transitions. |
| source_title | BT-028 | text | NOT NULL | false | false | Source occupation title. Carried from career_transitions. |
| related_soc_code | BT-027 | identifier | NOT NULL | true | false | Branch target occupation SOC code (XX-XXXX). Carried from career_transitions. |
| related_title | BT-028 | text | NOT NULL | false | false | Branch target occupation title. Carried from career_transitions. |
| best_index | BT-060 | numeric | NOT NULL | false | false | Similarity rank (1 = most similar branch). Carried from career_transitions. |
| relatedness_tier | BT-061 | text | NOT NULL | false | false | Primary-Short / Primary-Long / Supplemental. Carried from career_transitions. |
| is_primary | BT-060 | boolean | NOT NULL | false | false | True for top 10 branches by similarity. Carried from career_transitions. |

### Source Stats (Source Occupation Profile)

Stats for the originating occupation, pulled from occupation_profiles and onet_work_profiles.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_grw | BT-047 | numeric | NULLABLE | false | false | Source occupation GRW score (1-10). Carried from occupation_profiles.grw_score_rounded via LEFT JOIN on soc_code. |
| source_hmn | BT-066 | numeric | NULLABLE | false | false | Source occupation HMN score (1-10). Carried from onet_work_profiles.hmn_score_rounded via LEFT JOIN on soc_code. |
| source_burnout | BT-068 | numeric | NULLABLE | false | false | Source occupation Burnout score (1-10). Carried from onet_work_profiles.burnout_score_rounded via LEFT JOIN on soc_code. |
| source_wage | BT-036 | numeric | NULLABLE | false | false | Source occupation median annual wage. Carried from occupation_profiles.median_annual_wage via LEFT JOIN on soc_code. |

### Related Stats (Branch Target Occupation Profile)

Stats for the branch target occupation, pulled from the same upstream tables via the related_soc_code key.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| related_grw | BT-047 | numeric | NULLABLE | false | false | Target occupation GRW score (1-10). Carried from occupation_profiles.grw_score_rounded via LEFT JOIN on related_soc_code. |
| related_hmn | BT-066 | numeric | NULLABLE | false | false | Target occupation HMN score (1-10). Carried from onet_work_profiles.hmn_score_rounded via LEFT JOIN on related_soc_code. |
| related_burnout | BT-068 | numeric | NULLABLE | false | false | Target occupation Burnout score (1-10). Carried from onet_work_profiles.burnout_score_rounded via LEFT JOIN on related_soc_code. |
| related_wage | BT-036 | numeric | NULLABLE | false | false | Target occupation median annual wage. Carried from occupation_profiles.median_annual_wage via LEFT JOIN on related_soc_code. |
| related_growth_category | BT-041 | text | NULLABLE | false | false | Target occupation growth classification. Carried from occupation_profiles.growth_category. |
| related_education_level | BT-039 | text | NULLABLE | false | false | Target occupation typical education requirement. Carried from occupation_profiles.education_level_name. |

### Stat Deltas (Derived Comparisons)

Computed differences between source and target occupation stats. Positive values mean the branch target scores higher.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| grw_delta | BT-091 | numeric | NULLABLE | false | false | `related_grw - source_grw`. Positive = branch target grows faster. Null if either side is null. |
| hmn_delta | BT-091 | numeric | NULLABLE | false | false | `related_hmn - source_hmn`. Positive = more human edge at target. Null if either side is null. |
| burnout_delta | BT-091 | numeric | NULLABLE | false | false | `related_burnout - source_burnout`. Positive = more burnout risk at target. Null if either side is null. |
| wage_delta | BT-091 | numeric | NULLABLE | false | false | `related_wage - source_wage`. Positive = higher pay at target. Null if either side is null. |
| branch_has_full_data | BT-092 | boolean | NOT NULL | false | false | True if the related occupation has both BLS occupation_profiles data AND O*NET onet_work_profiles data. Derived from join success on the related_soc_code side. |

### Branch Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| promoted_at | BT-026 | timestamp | NOT NULL | false | false | Timestamp when the row was promoted to the Gold consumable table. Generated at promotion time. |

---

## Attribute Summary

### Table 1: consumable.program_career_paths

| Count | Category |
|-------|----------|
| 40 | Total attributes |
| 3 | Natural key components (unitid, cipcode, soc_code) |
| 1 | Surrogate key (record_id) |
| 15 | CDE attributes |
| 0 | PII attributes |
| 28 | Nullable attributes |
| 12 | NOT NULL attributes |
| 11 | Derived at this layer |
| 28 | Carried from upstream (via join chain) |
| 1 | Pipeline metadata (promoted_at) |

### Table 2: consumable.career_branches

| Count | Category |
|-------|----------|
| 23 | Total attributes |
| 2 | Natural key components (soc_code, related_soc_code) |
| 1 | Surrogate key (record_id) |
| 2 | CDE attributes |
| 0 | PII attributes |
| 14 | Nullable attributes |
| 9 | NOT NULL attributes |
| 5 | Derived at this layer |
| 17 | Carried from upstream (via join chain) |
| 1 | Pipeline metadata (promoted_at) |

---

## Type Domain Definitions

Consistent with the established Gold zone convention from gold-occupation-profiles-bls-ooh-logical.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure, count, ratio, rank, score, or code. May be aggregated. | DOUBLE (monetary, ratios, percentiles), BIGINT (counts, unitid), INTEGER (scores 1-10, counts 0-5) |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

All derivation rules are null-safe. Null inputs propagate to null outputs unless otherwise specified.

### Surrogate Keys

| Attribute | Table | Rule | Source Attributes |
|-----------|-------|------|-------------------|
| record_id | program_career_paths | `compute_grain_id(row, ['unitid', 'cipcode', 'soc_code'], prefix='pcp')` | unitid, cipcode, soc_code |
| record_id | career_branches | `compute_grain_id(row, ['soc_code', 'related_soc_code'], prefix='br')` | soc_code, related_soc_code |

### ERN Score Derivation (Piecewise Blend)

Blends program-level earnings position with occupation-level wage position to produce a 1-10 integer score.

| Step | Computation | Source | Null Handling |
|------|------------|--------|---------------|
| 1 | `scorecard_percentile = career_outcomes.cip_family_earnings_rank` | BT-022 | 0.0-1.0 rank of this program within its CIP family |
| 2 | `occupation_wage_percentile = occupation_profiles.wage_percentile_overall` | BT-048 | 0.0-1.0 rank among all occupations with wage data |
| 3 | `raw_ern = 0.6 * scorecard_percentile + 0.4 * occupation_wage_percentile` | Blend | 60% school-specific, 40% career-level |
| 4 | `stat_ern = ROUND(1.0 + 9.0 * raw_ern)` | Scale to 1-10 | Null if either input is null |

**Design rationale:** The 60/40 weighting captures the school premium -- a Stanford CS grad's ERN is pulled up by Stanford's strong earnings data, while a weaker program's ERN is pulled down even though the underlying occupation pays well everywhere. This is an open decision awaiting human confirmation.

### ROI Score Derivation (Piecewise Linear)

Maps debt-to-earnings ratio inversely to a 1-10 scale via piecewise linear interpolation.

| Input Range (debt_to_earnings_annual) | Output Range (stat_roi) | Interpolation | Rationale |
|---------------------------------------|------------------------|---------------|-----------|
| <= 0.25 | 10 (cap) | Fixed | Excellent ROI -- very low debt relative to earnings |
| 0.25 to 0.75 | 10 to 8 | `10 - (dte - 0.25) / (0.75 - 0.25) * 2` | Strong ROI |
| 0.75 to 1.5 | 8 to 5 | `8 - (dte - 0.75) / (1.5 - 0.75) * 3` | Average range |
| 1.5 to 2.5 | 5 to 3 | `5 - (dte - 1.5) / (2.5 - 1.5) * 2` | Concerning |
| 2.5 to 4.0 | 3 to 1 | `3 - (dte - 2.5) / (4.0 - 2.5) * 2` | Poor ROI |
| > 4.0 | 1 (floor) | Fixed | Very poor -- debt massively exceeds earnings |

Null if debt_to_earnings_annual is null. Output is rounded to integer (1-10).

**Thresholds source:** Department of Education Gainful Employment guidance. Open decision awaiting human confirmation.

### Boss Loans Score Derivation

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| boss_loans_score | `11 - stat_roi` | stat_roi | Null if stat_roi is null |

Exact inverse of ROI: excellent ROI (10) means easy boss (1); terrible ROI (1) means devastating boss (10).

### Boss Ceiling Score Derivation

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| boss_ceiling_score | `ROUND(10.0 - 9.0 * wage_percentile_education_tier)` | occupation_profiles.wage_percentile_education_tier (BT-049) | Null if wage_percentile_education_tier is null |

Low earner within education tier (percentile near 0) gets strong boss (score near 10 -- the ceiling is real). High earner (percentile near 1) gets weak boss (score near 1 -- already past the ceiling). Open decision: simplified formula, more sophisticated version would use BLS experience-level salary data.

### Placeholder Stats

| Attribute | Rule | Status |
|-----------|------|--------|
| stat_res | Always null | Placeholder -- requires Karpathy AI Exposure Scores + task-level Gemma scoring (separate spec) |
| boss_ai_score | Always null | Placeholder -- same dependency as stat_res |

### Carried Stats (Verbatim from Upstream)

| Attribute | Source Table | Source Attribute | Join Key |
|-----------|-------------|-----------------|----------|
| stat_grw | occupation_profiles | grw_score_rounded | soc_code |
| stat_hmn | onet_work_profiles | hmn_score_rounded | soc_code = bls_soc_code |
| boss_market_score | occupation_profiles | market_score_rounded | soc_code |
| boss_burnout_score | onet_work_profiles | burnout_score_rounded | soc_code = bls_soc_code |

### Match Quality Derivation (Gold-Time)

Derived from actual join success, NOT from upstream crosswalk Silver's `has_scorecard_match` flag (which is FALSE for all rows due to CIP granularity mismatch at the Silver layer).

| Value | Condition | Business Meaning |
|-------|-----------|------------------|
| 'full' | BLS join succeeded AND O*NET join succeeded | Full cross-source coverage -- all possible stats computable |
| 'partial_no_onet' | BLS join succeeded AND O*NET join failed | Missing HMN, burnout stats. GRW, market, ceiling available. |
| 'partial_no_bls' | BLS join failed AND O*NET join succeeded | Missing GRW, market, ceiling stats. HMN, burnout available. |
| 'scorecard_only' | BLS join failed AND O*NET join failed | Only program-level data (ERN, ROI). No occupation-level stats. |

Where "BLS join succeeded" = occupation_profiles row exists for this soc_code; "O*NET join succeeded" = onet_work_profiles row exists for this soc_code.

**Expected distribution:** Majority 'full' (~76.6% based on crosswalk EDA coverage estimates).

### Stats Available Count Derivation

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| stats_available_count | Count of non-null values in (stat_ern, stat_roi, stat_res, stat_grw, stat_hmn) | All five stat fields | Never null (0-5 integer). Maximum 4 in MVP since stat_res is always null. |

### Bosses Available Count Derivation

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| bosses_available_count | Count of non-null values in (boss_ai_score, boss_loans_score, boss_market_score, boss_burnout_score, boss_ceiling_score) | All five boss fields | Never null (0-5 integer). Maximum 4 in MVP since boss_ai_score is always null. |

### Overall Confidence Derivation

Evaluated top-to-bottom; first matching condition wins. Every row receives a tier.

| Tier Value | Condition | Business Interpretation |
|------------|-----------|------------------------|
| 'high' | stats_available_count >= 4 AND match_quality = 'full' | Strong data coverage across all sources |
| 'medium' | stats_available_count >= 2 AND match_quality IN ('partial_no_onet', 'partial_no_bls') | Partial cross-source coverage; some stats available |
| 'low' | stats_available_count < 2 OR match_quality = 'scorecard_only' | Minimal data; program-level only or very sparse |

### Stat Delta Derivations (Table 2)

All deltas are simple arithmetic differences. Null if either operand is null.

| Attribute | Rule | Source Attributes |
|-----------|------|-------------------|
| grw_delta | `related_grw - source_grw` | related_grw, source_grw |
| hmn_delta | `related_hmn - source_hmn` | related_hmn, source_hmn |
| burnout_delta | `related_burnout - source_burnout` | related_burnout, source_burnout |
| wage_delta | `related_wage - source_wage` | related_wage, source_wage |

**Range constraints:** Integer deltas (grw, hmn, burnout) range from -9 to +9. Wage delta has no fixed range but should be reasonable (within typical occupation wage bounds).

### Branch Has Full Data Derivation

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| branch_has_full_data | True if the related occupation has both an occupation_profiles row AND an onet_work_profiles row | related_grw IS NOT NULL (proxy for BLS) AND related_hmn IS NOT NULL (proxy for O*NET) | Never null (boolean) |

### Pipeline Metadata

| Attribute | Rule | Source |
|-----------|------|--------|
| promoted_at | Current timestamp at promotion time | Generated by promote() function |

---

## Nullability Semantics

Null values in this model carry specific business meaning, reflecting the cross-source join nature of the data.

### Table 1: program_career_paths

| Pattern | Business Meaning |
|---------|-----------------|
| soc_major_group_name IS NULL | BLS occupation_profiles did not join for this SOC code (LEFT JOIN miss). |
| stat_ern IS NULL | Either scorecard earnings rank or occupation wage percentile is missing. Incomplete data for blended score. |
| stat_roi IS NULL | Debt-to-earnings ratio unavailable (privacy suppression or missing debt/earnings data). |
| stat_res IS NULL | Always null in MVP. Placeholder for Karpathy integration. |
| stat_grw IS NULL | BLS occupation_profiles did not join for this SOC code, or occupation has no growth data. |
| stat_hmn IS NULL | O*NET onet_work_profiles did not join for this SOC code. |
| boss_ai_score IS NULL | Always null in MVP. Placeholder. |
| boss_loans_score IS NULL | Propagated from null stat_roi. |
| boss_market_score IS NULL | BLS occupation_profiles did not join or market score unavailable. |
| boss_burnout_score IS NULL | O*NET onet_work_profiles did not join or burnout score unavailable. |
| boss_ceiling_score IS NULL | Occupation lacks wage_percentile_education_tier (no wage data or education code unavailable). |
| earnings_1yr_median IS NULL | Privacy suppression in College Scorecard (small cohort). |
| Occupation context fields IS NULL | LEFT JOIN to occupation_profiles or onet_work_profiles failed for this SOC code. |

### Table 2: career_branches

| Pattern | Business Meaning |
|---------|-----------------|
| source_* stats IS NULL | Source occupation lacks BLS or O*NET coverage. |
| related_* stats IS NULL | Target occupation lacks BLS or O*NET coverage. |
| *_delta IS NULL | Either source or target stat is null, preventing comparison. |

**Key invariant:** match_quality, stats_available_count, bosses_available_count, and overall_confidence are NEVER null. Every row is classified.

---

## Constraints and Invariants

### Hard Constraints (DQ P0 -- block promotion if violated)

| Constraint | Rule | Table | Scope |
|------------|------|-------|-------|
| Grain uniqueness (T1) | Zero duplicates on (unitid, cipcode, soc_code) | program_career_paths | Table-wide |
| Grain uniqueness (T2) | Zero duplicates on (soc_code, related_soc_code) | career_branches | Table-wide |
| Record ID uniqueness | Zero duplicates on record_id | Both tables | Table-wide |
| Pentagon stat range | 1 <= stat_ern, stat_roi, stat_grw, stat_hmn <= 10 for all non-null rows | program_career_paths | Row-level |
| Boss score range | 1 <= boss_loans_score, boss_market_score, boss_burnout_score, boss_ceiling_score <= 10 for all non-null rows | program_career_paths | Row-level |
| stat_res always null | stat_res IS NULL for all rows | program_career_paths | Table-wide |
| boss_ai_score always null | boss_ai_score IS NULL for all rows | program_career_paths | Table-wide |
| Loans-ROI inverse | boss_loans_score = 11 - stat_roi for all rows where both are non-null | program_career_paths | Row-level |
| match_quality valid values | match_quality IN ('full', 'partial_no_onet', 'partial_no_bls', 'scorecard_only') | program_career_paths | Row-level |
| overall_confidence valid values | overall_confidence IN ('high', 'medium', 'low') | program_career_paths | Row-level |
| stats_available_count range | 0 <= stats_available_count <= 5 | program_career_paths | Row-level |
| bosses_available_count range | 0 <= bosses_available_count <= 5 | program_career_paths | Row-level |
| Integer delta range | -9 <= grw_delta, hmn_delta, burnout_delta <= 9 for all non-null rows | career_branches | Row-level |
| Row count T1 | 150,000 <= row_count <= 500,000 | program_career_paths | Table-wide |
| Row count T2 | row_count = 15,944 | career_branches | Table-wide |

### Soft Constraints (DQ P1 -- warn but allow promotion)

| Constraint | Rule | Table | Expected |
|------------|------|-------|----------|
| CIP prefix coverage | >= 90% of career_outcomes distinct cipcode values present in output | program_career_paths | ~91% |
| Full match majority | >= 70% of rows have match_quality = 'full' | program_career_paths | ~76.6% |
| High confidence majority | >= 50% of rows have overall_confidence = 'high' | program_career_paths | Majority expected |
| Stats available 4+ | >= 60% of rows have stats_available_count >= 4 | program_career_paths | Based on full match rate |
| Branch full data | >= 70% of career_branches rows have branch_has_full_data = true | career_branches | Based on BLS+O*NET coverage |

---

## Traceability: Conceptual to Logical

### Table 1: program_career_paths

| Conceptual Entity | Logical Attribute Group | Attributes | Notes |
|-------------------|------------------------|------------|-------|
| Program Career Path | Program Career Path (core identity) | record_id, unitid, institution_name, cipcode, program_name, cip_family, cip_family_name, soc_code, occupation_title, soc_major_group_name | Central entity. Three natural key fields. |
| Program Identity | Absorbed into Program Career Path | unitid, institution_name, cipcode, program_name, cip_family, cip_family_name | Flattened into the core identity group. |
| CIP Family | Absorbed into Program Career Path | cip_family, cip_family_name | Denormalized into the row. |
| CIP-SOC Bridge | Not persisted as attributes | -- | The bridge is a join strategy (BT-086), not stored data. Its effect is captured by the soc_code field and match_quality derivation. |
| Occupation Identity | Absorbed into Program Career Path | soc_code, occupation_title, soc_major_group_name | Flattened into the core identity group. |
| Pentagon Stats | Pentagon Stats | stat_ern, stat_roi, stat_res, stat_grw, stat_hmn | Separate logical group for derivation clarity. |
| Boss Fight Profile | Boss Fight Profile | boss_ai_score, boss_loans_score, boss_market_score, boss_burnout_score, boss_ceiling_score | Separate logical group for derivation clarity. |
| Program Context | Program Context | earnings_1yr_median, earnings_1yr_p25, earnings_1yr_p75, debt_median, debt_to_earnings_annual, confidence_tier_program | Raw inputs for ERN and ROI derivations. |
| Occupation Context | Occupation Context | median_annual_wage, growth_category, employment_current, education_level_name, top_5_activities, top_human_activities, burnout_drivers, time_pressure, work_hours | Descriptive attributes from BLS + O*NET. |
| Data Quality Assessment | Data Quality | match_quality, stats_available_count, bosses_available_count, overall_confidence | All NOT NULL. Mandatory quality classification. |

### Table 2: career_branches

| Conceptual Entity | Logical Attribute Group | Attributes | Notes |
|-------------------|------------------------|------------|-------|
| Career Branch | Career Branch (core identity) | record_id, soc_code, source_title, related_soc_code, related_title, best_index, relatedness_tier, is_primary | Central entity with two natural key fields. |
| Occupation Identity (source) | Absorbed into Source Stats | source_grw, source_hmn, source_burnout, source_wage | Stats for the originating occupation. |
| Occupation Identity (target) | Absorbed into Related Stats | related_grw, related_hmn, related_burnout, related_wage, related_growth_category, related_education_level | Stats for the branch target occupation. |
| Stat Delta Profile | Stat Deltas | grw_delta, hmn_delta, burnout_delta, wage_delta, branch_has_full_data | Computed differences plus data completeness flag. |

---

## Source Field Mapping

### Table 1: program_career_paths

| Logical Attribute | Source Table | Source Field | Transformation |
|-------------------|-------------|-------------|----------------|
| unitid | consumable.career_outcomes | unitid | Verbatim |
| institution_name | consumable.career_outcomes | institution_name | Verbatim |
| cipcode | consumable.career_outcomes | cipcode | Verbatim (4-digit XX.XX) |
| program_name | consumable.career_outcomes | program_name | Verbatim |
| cip_family | consumable.career_outcomes | cip_family | Verbatim |
| cip_family_name | consumable.career_outcomes | cip_family_name | Verbatim |
| soc_code | base.cip_soc_crosswalk | soc_code | Verbatim (via CIP prefix join) |
| occupation_title | consumable.occupation_profiles / consumable.onet_work_profiles | occupation_title | Prefer occupation_profiles; fallback to onet_work_profiles |
| soc_major_group_name | consumable.occupation_profiles | soc_major_group_name | Verbatim (nullable via LEFT JOIN) |
| earnings_1yr_median | consumable.career_outcomes | earnings_1yr_median | Verbatim |
| earnings_1yr_p25 | consumable.career_outcomes | earnings_1yr_p25 | Verbatim |
| earnings_1yr_p75 | consumable.career_outcomes | earnings_1yr_p75 | Verbatim |
| debt_median | consumable.career_outcomes | debt_median | Verbatim |
| debt_to_earnings_annual | consumable.career_outcomes | debt_to_earnings_annual | Verbatim |
| confidence_tier_program | consumable.career_outcomes | confidence_tier | Verbatim (renamed for disambiguation) |
| median_annual_wage | consumable.occupation_profiles | median_annual_wage | Verbatim |
| growth_category | consumable.occupation_profiles | growth_category | Verbatim |
| employment_current | consumable.occupation_profiles | employment_current | Verbatim |
| education_level_name | consumable.occupation_profiles | education_level_name | Verbatim |
| top_5_activities | consumable.onet_work_profiles | top_5_activities | Verbatim |
| top_human_activities | consumable.onet_work_profiles | top_human_activities | Verbatim |
| burnout_drivers | consumable.onet_work_profiles | burnout_drivers | Verbatim |
| time_pressure | consumable.onet_work_profiles | time_pressure | Verbatim |
| work_hours | consumable.onet_work_profiles | work_hours | Verbatim |

### Table 2: career_branches

| Logical Attribute | Source Table | Source Field | Transformation |
|-------------------|-------------|-------------|----------------|
| soc_code | consumable.career_transitions | soc_code | Verbatim |
| source_title | consumable.career_transitions | source_title | Verbatim |
| related_soc_code | consumable.career_transitions | related_soc_code | Verbatim |
| related_title | consumable.career_transitions | related_title | Verbatim |
| best_index | consumable.career_transitions | best_index | Verbatim |
| relatedness_tier | consumable.career_transitions | relatedness_tier | Verbatim |
| is_primary | consumable.career_transitions | is_primary | Verbatim |
| source_grw | consumable.occupation_profiles | grw_score_rounded | Via LEFT JOIN on soc_code |
| source_hmn | consumable.onet_work_profiles | hmn_score_rounded | Via LEFT JOIN on soc_code = bls_soc_code |
| source_burnout | consumable.onet_work_profiles | burnout_score_rounded | Via LEFT JOIN on soc_code = bls_soc_code |
| source_wage | consumable.occupation_profiles | median_annual_wage | Via LEFT JOIN on soc_code |
| related_grw | consumable.occupation_profiles | grw_score_rounded | Via LEFT JOIN on related_soc_code |
| related_hmn | consumable.onet_work_profiles | hmn_score_rounded | Via LEFT JOIN on related_soc_code = bls_soc_code |
| related_burnout | consumable.onet_work_profiles | burnout_score_rounded | Via LEFT JOIN on related_soc_code = bls_soc_code |
| related_wage | consumable.occupation_profiles | median_annual_wage | Via LEFT JOIN on related_soc_code |
| related_growth_category | consumable.occupation_profiles | growth_category | Via LEFT JOIN on related_soc_code |
| related_education_level | consumable.occupation_profiles | education_level_name | Via LEFT JOIN on related_soc_code |

---

## Open Decisions (Awaiting Human Confirmation)

These design decisions from the spec are reflected in this logical model but flagged for explicit human approval:

1. **ERN 60/40 weighting** -- program earnings rank (60%) vs. occupation wage percentile (40%). Captured in the ERN derivation rule.
2. **ROI piecewise breakpoints** -- thresholds based on Gainful Employment guidance. Captured in the ROI derivation rule.
3. **Ceiling boss simplified formula** -- uses wage_percentile_education_tier directly. A more sophisticated approach would use BLS experience-level salary data.
4. **RES stat and AI Boss as null placeholders** -- the model includes them at 0-fill (always null) so the schema is complete for the target state.
5. **CIP prefix match breadth** -- the 4-digit join is coarser than the crosswalk was designed for. Accepted for hackathon; post-hackathon may use 6-digit CIP enrichment or Gemma filtering.
