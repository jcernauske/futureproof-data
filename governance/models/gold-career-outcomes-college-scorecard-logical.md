# Logical Model: gold-career-outcomes-college-scorecard

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Domain:** Higher Education Outcomes
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Conceptual Model:** governance/models/gold-career-outcomes-college-scorecard-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-06
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)
**Source Model:** governance/models/silver-base-college-scorecard-logical.md

---

```mermaid
erDiagram
    CAREER_OUTCOME {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        text institution_control
        identifier cipcode NK
        text program_name
        identifier cip_family FK
        text cip_family_name
        numeric credential_level NK
        numeric earnings_1yr_median
        numeric earnings_2yr_median
        numeric debt_median
        numeric completions_count
        boolean small_cohort_flag
    }
    EARNINGS_PERCENTILE_BAND {
        identifier cip_family PK
        numeric earnings_1yr_p25
        numeric earnings_1yr_p75
        numeric earnings_2yr_p25
        numeric earnings_2yr_p75
        numeric debt_p25
        numeric debt_p75
    }
    FINANCIAL_ASSESSMENT {
        identifier record_id PK
        numeric debt_to_earnings_annual
        text debt_to_earnings_tier
        numeric earnings_growth_rate
        numeric cip_family_earnings_rank
        numeric program_value_index
    }
    DATA_CONFIDENCE {
        identifier record_id PK
        text confidence_tier
        boolean has_earnings
        boolean has_debt
        numeric outcome_completeness
    }
    PIPELINE_METADATA {
        identifier record_id PK
        date source_load_date
        timestamp promoted_at
    }
    CAREER_OUTCOME ||--o| EARNINGS_PERCENTILE_BAND : "contextualized by CIP family bands"
    CAREER_OUTCOME ||--o| FINANCIAL_ASSESSMENT : "evaluated by affordability metrics"
    CAREER_OUTCOME ||--|| DATA_CONFIDENCE : "qualified by confidence tier"
    CAREER_OUTCOME ||--|| PIPELINE_METADATA : "tracked by metadata"
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies 6 entities (Career Outcome, Program Identity, CIP Family, Earnings Percentile Band, Financial Assessment, Data Confidence). Following the same pattern as the Silver logical model, these are flattened into a single denormalized `consumable.career_outcomes` table in the physical layer. The logical model groups attributes by conceptual entity to preserve semantic clarity while acknowledging the physical denormalization.

This is appropriate because:
1. The Gold consumable layer optimizes for the primary query pattern (school + major = outcomes)
2. All conceptual entities resolve to 1:1 or 1:0..1 per row at the program-offering grain
3. Percentile bands are denormalized onto each row (shared across CIP family) for query convenience
4. Dataset size (70K rows) does not benefit from normalization

The logical diagram above shows the conceptual entity groups as separate boxes to communicate the distinct business concerns, but all will collapse into a single physical table.

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per program offering: a specific academic program at a specific institution at a specific credential level |
| **Natural key fields** | `unitid` + `cipcode` + `credential_level` |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'co') |
| **Uniqueness constraint** | Zero duplicates on natural key. Enforced at promote time. |
| **Expected cardinality** | 69,947 rows (all Silver base rows carried forward) |
| **Source table** | `base.college_scorecard` (Silver zone) |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The `NK` marker denotes natural key components.

### Career Outcome (Core Identity + Outcome Fields)

These attributes are carried forward from Silver `base.college_scorecard` without transformation. They combine the conceptual entities Program Identity, CIP Family, and the core outcome measures from Career Outcome.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key (unitid + cipcode + credential_level) using `compute_grain_id()` with prefix 'co'. Note: prefix changes from Silver's 'cs' to Gold's 'co' to distinguish zones. |
| unitid | BT-001 | identifier | NOT NULL | true | false | IPEDS 6-digit institution identifier. Part of the natural key. Carried from Silver verbatim. |
| institution_name | BT-002 | text | NOT NULL | false | false | Official institution name as reported to IPEDS. Carried from Silver verbatim. |
| institution_control | *pending* | text | NOT NULL | false | false | Type of institutional governance: Public, Private nonprofit, or Private for-profit. Carried from Silver verbatim. |
| cipcode | BT-003 | identifier | NOT NULL | false | false | CIP code in normalized XX.XXXX format. Part of the natural key. Carried from Silver verbatim. |
| program_name | BT-004 | text | NOT NULL | false | false | Human-readable program description corresponding to the CIP code. Carried from Silver verbatim. |
| cip_family | BT-005 | identifier | NOT NULL | false | false | 2-digit CIP family code. Serves dual role: classification context for the program and partition key for percentile band and rank computations. Carried from Silver verbatim. |
| cip_family_name | BT-006 | text | NOT NULL | false | false | Human-readable label for the CIP family. Carried from Silver verbatim. |
| credential_level | BT-007 | numeric | NOT NULL | false | false | Integer code for credential type (3 = Bachelor's in MVP). Part of the natural key. Carried from Silver verbatim. |
| earnings_1yr_median | BT-009 | numeric | NULLABLE | true | false | Median earnings 1 year after completion. Cohort-level aggregate. Null when privacy-suppressed. Carried from Silver verbatim. Feeds percentile bands, debt-to-earnings ratio, earnings rank, and program value index. |
| earnings_2yr_median | BT-010 | numeric | NULLABLE | true | false | Median earnings 2 years after completion. Different cohort from 1yr (not longitudinal). Null when privacy-suppressed. Carried from Silver verbatim. Feeds percentile bands and earnings growth rate. |
| debt_median | BT-011 | numeric | NULLABLE | true | false | Median cumulative federal loan debt at program completion. Null when privacy-suppressed. Carried from Silver verbatim. Feeds percentile bands, debt-to-earnings ratio, and program value index. |
| completions_count | BT-012 | numeric | NULLABLE | false | false | IPEDS completions count (first major measurement window). Renamed from Silver's `completions_count_1` for clarity in the consumable layer. Second major count (`completions_count_2`) is dropped per spec. |
| small_cohort_flag | BT-014 | boolean | NOT NULL | false | false | True when completions_count < 30 or completions data is null. Indicates outcome data may be privacy-suppressed. Carried from Silver verbatim. Feeds confidence tier derivation. |

### Earnings Percentile Band (Derived: CIP-Family Window Aggregates)

These attributes are computed via window functions over the Silver source data, partitioned by CIP family. They represent cross-institution distributional context -- the range of outcomes across all programs in the same discipline.

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| earnings_1yr_p25 | BT-018 | numeric | NULLABLE | true | false | 25th percentile of 1-year median earnings across all institutions in the same CIP family. Null if fewer than 3 non-null values in the CIP family for this field. |
| earnings_1yr_p75 | BT-018 | numeric | NULLABLE | true | false | 75th percentile of 1-year median earnings across all institutions in the same CIP family. Null if fewer than 3 non-null values in the CIP family for this field. |
| earnings_2yr_p25 | BT-018 | numeric | NULLABLE | true | false | 25th percentile of 2-year median earnings across all institutions in the same CIP family. Null if fewer than 3 non-null values. |
| earnings_2yr_p75 | BT-018 | numeric | NULLABLE | true | false | 75th percentile of 2-year median earnings across all institutions in the same CIP family. Null if fewer than 3 non-null values. |
| debt_p25 | BT-018 | numeric | NULLABLE | true | false | 25th percentile of median debt across all institutions in the same CIP family. Null if fewer than 3 non-null values. |
| debt_p75 | BT-018 | numeric | NULLABLE | true | false | 75th percentile of median debt across all institutions in the same CIP family. Null if fewer than 3 non-null values. |

### Financial Assessment (Derived: Affordability and Value Metrics)

These attributes are computed from the core outcome fields. All are null-safe: null when any required input is missing due to privacy suppression (BT-013).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| debt_to_earnings_annual | BT-019 | numeric | NULLABLE | true | false | Debt-to-earnings ratio: debt_median / earnings_1yr_median. Key affordability metric. Values < 1.0 manageable, > 2.0 concerning. Null if either input is null. |
| debt_to_earnings_tier | BT-020 | text | NULLABLE | false | false | Categorical bucketing of the debt-to-earnings ratio. Four tiers: "Low" (< 0.75), "Moderate" (0.75-1.5), "High" (1.5-2.5), "Very High" (>= 2.5). Null if ratio is null. |
| earnings_growth_rate | BT-021 | numeric | NULLABLE | false | false | Cross-cohort earnings differential: (earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median. NOT longitudinal growth -- compares different graduating cohorts. Negative values expected (~44% of programs). Null if either input is null. |
| cip_family_earnings_rank | BT-022 | numeric | NULLABLE | false | false | Relative position within CIP family based on 1-year median earnings. Range 0.0 (lowest) to 1.0 (highest). Computed via PERCENT_RANK window function. Null if earnings_1yr_median is null. |
| program_value_index | BT-023 | numeric | NULLABLE | false | false | ROI proxy: earnings_1yr_median / debt_median. Higher = better value. Mathematical inverse of debt-to-earnings ratio. Null if either input is null. |

### Data Confidence (Derived: Quality Context)

These attributes classify the trustworthiness and completeness of each row. Unlike other derived groups, confidence_tier is required on every row (no nulls).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| confidence_tier | BT-024 | text | NOT NULL | false | false | Four-level data quality classification: "high" (large cohort + earnings + debt), "medium" (large cohort + partial data), "low" (small cohort + some data), "insufficient" (no outcome data). Every row receives a tier. |
| has_earnings | BT-024 | boolean | NOT NULL | false | false | Convenience flag: True if earnings_1yr_median IS NOT NULL OR earnings_2yr_median IS NOT NULL. Enables efficient filtering. |
| has_debt | BT-024 | boolean | NOT NULL | false | false | Convenience flag: True if debt_median IS NOT NULL. Enables efficient filtering. |
| outcome_completeness | BT-025 | numeric | NOT NULL | false | false | Proportion of core outcome fields that are non-null: count of non-null among (earnings_1yr_median, earnings_2yr_median, debt_median) divided by 3. Exact value set: {0.0, 0.33, 0.67, 1.0}. |

### Pipeline Metadata

Pipeline infrastructure fields, not analytical dimensions. Carried from Silver (source_load_date) or generated at promotion time (promoted_at).

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the raw zone. Pipeline metadata carried from Silver. |
| promoted_at | BT-026 | timestamp | NOT NULL | false | false | Timestamp when the row was promoted to the Gold zone consumable table. Generated at promotion time. Replaces Silver's ingested_at. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 30 | Total attributes |
| 3 | Natural key components (unitid, cipcode, credential_level) |
| 1 | Surrogate key (record_id) |
| 4 | CDE attributes (unitid, earnings_1yr_median, earnings_2yr_median, debt_median) -- carried from Silver |
| 6 | CDE attributes (earnings percentile bands) -- new in Gold |
| 1 | CDE attribute (debt_to_earnings_annual) -- new in Gold |
| 0 | PII attributes |
| 16 | Nullable attributes |
| 14 | NOT NULL attributes |
| 17 | Derived attributes (all percentile bands, financial metrics, confidence fields, record_id, has_earnings, has_debt, outcome_completeness) |
| 13 | Carried from Silver verbatim |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR or BIGINT depending on content |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure, count, ratio, or rank. May be aggregated. | DOUBLE (monetary, ratios, ranks), BIGINT (counts), INTEGER (codes) |
| boolean | A true/false flag derived from business rules. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

All derivation rules are null-safe. Null inputs propagate to null outputs unless otherwise specified.

### Carried from Silver (no transformation)

| Attribute | Source | Rule |
|-----------|--------|------|
| unitid | base.college_scorecard.unitid | Verbatim |
| institution_name | base.college_scorecard.institution_name | Verbatim |
| institution_control | base.college_scorecard.institution_control | Verbatim |
| cipcode | base.college_scorecard.cipcode | Verbatim |
| program_name | base.college_scorecard.program_name | Verbatim |
| cip_family | base.college_scorecard.cip_family | Verbatim |
| cip_family_name | base.college_scorecard.cip_family_name | Verbatim |
| credential_level | base.college_scorecard.credential_level | Verbatim |
| earnings_1yr_median | base.college_scorecard.earnings_1yr_median | Verbatim |
| earnings_2yr_median | base.college_scorecard.earnings_2yr_median | Verbatim |
| debt_median | base.college_scorecard.debt_median | Verbatim |
| completions_count | base.college_scorecard.completions_count_1 | Renamed from completions_count_1 to completions_count |
| small_cohort_flag | base.college_scorecard.small_cohort_flag | Verbatim |
| source_load_date | base.college_scorecard.source_load_date | Verbatim |

### Surrogate Key

| Attribute | Rule | Source Attributes |
|-----------|------|-------------------|
| record_id | `compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='co')` | unitid, cipcode, credential_level |

### Percentile Bands (CIP-Family Window Aggregates)

All percentile bands use the same pattern. The minimum sample size is 3 non-null values per CIP family per field. Below that threshold, all bands for that family-field combination are set to null.

| Attribute | Rule | Partition | Order | Minimum Sample |
|-----------|------|-----------|-------|----------------|
| earnings_1yr_p25 | `PERCENTILE_CONT(0.25) OVER (PARTITION BY cip_family)` on earnings_1yr_median | cip_family | N/A (aggregate) | 3 non-null values |
| earnings_1yr_p75 | `PERCENTILE_CONT(0.75) OVER (PARTITION BY cip_family)` on earnings_1yr_median | cip_family | N/A (aggregate) | 3 non-null values |
| earnings_2yr_p25 | `PERCENTILE_CONT(0.25) OVER (PARTITION BY cip_family)` on earnings_2yr_median | cip_family | N/A (aggregate) | 3 non-null values |
| earnings_2yr_p75 | `PERCENTILE_CONT(0.75) OVER (PARTITION BY cip_family)` on earnings_2yr_median | cip_family | N/A (aggregate) | 3 non-null values |
| debt_p25 | `PERCENTILE_CONT(0.25) OVER (PARTITION BY cip_family)` on debt_median | cip_family | N/A (aggregate) | 3 non-null values |
| debt_p75 | `PERCENTILE_CONT(0.75) OVER (PARTITION BY cip_family)` on debt_median | cip_family | N/A (aggregate) | 3 non-null values |

**Percentile band invariant:** For every CIP family where bands are computed, `p25 <= p75` must hold. This is a hard constraint (DQ P0 rule).

**Null exclusion:** Only rows with non-null values for the respective field contribute to the percentile calculation. A CIP family with 10 programs but only 2 with non-null 1yr earnings gets null 1yr bands.

### Financial Ratios

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| debt_to_earnings_annual | `debt_median / earnings_1yr_median` | debt_median, earnings_1yr_median | Null if either input is null |
| debt_to_earnings_tier | Bucketed from debt_to_earnings_annual (see tier rules below) | debt_to_earnings_annual | Null if ratio is null |
| earnings_growth_rate | `(earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median` | earnings_1yr_median, earnings_2yr_median | Null if either input is null |

### Debt-to-Earnings Tier Derivation

| Tier Value | Condition | Business Interpretation |
|------------|-----------|------------------------|
| "Low" | debt_to_earnings_annual < 0.75 | Debt very manageable relative to earnings |
| "Moderate" | 0.75 <= debt_to_earnings_annual < 1.5 | Typical range for most bachelor's programs |
| "High" | 1.5 <= debt_to_earnings_annual < 2.5 | May require extended repayment or income-driven plan |
| "Very High" | debt_to_earnings_annual >= 2.5 | Debt significantly exceeds first-year earnings |
| NULL | debt_to_earnings_annual IS NULL | Insufficient data |

### Relative Position

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| cip_family_earnings_rank | `PERCENT_RANK() OVER (PARTITION BY cip_family ORDER BY earnings_1yr_median)` | earnings_1yr_median, cip_family | Null if earnings_1yr_median is null (excluded from window) |
| program_value_index | `earnings_1yr_median / debt_median` | earnings_1yr_median, debt_median | Null if either input is null |

### Data Confidence

| Attribute | Rule | Source Attributes | Null Condition |
|-----------|------|-------------------|----------------|
| has_earnings | `earnings_1yr_median IS NOT NULL OR earnings_2yr_median IS NOT NULL` | earnings_1yr_median, earnings_2yr_median | Never null (always true or false) |
| has_debt | `debt_median IS NOT NULL` | debt_median | Never null (always true or false) |
| outcome_completeness | `(CASE WHEN earnings_1yr_median IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN earnings_2yr_median IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN debt_median IS NOT NULL THEN 1 ELSE 0 END) / 3.0` | earnings_1yr_median, earnings_2yr_median, debt_median | Never null (0.0 when all three are null) |

### Confidence Tier Derivation

Evaluated top-to-bottom; first matching condition wins.

| Tier Value | Condition | Business Interpretation |
|------------|-----------|------------------------|
| "high" | small_cohort_flag = False AND has_earnings = True AND has_debt = True | Large cohort with complete outcome data |
| "medium" | small_cohort_flag = False AND (has_earnings = True OR has_debt = True) | Large cohort with partial outcome data |
| "low" | small_cohort_flag = True AND (has_earnings = True OR has_debt = True) | Small cohort but some outcome data available |
| "insufficient" | has_earnings = False AND has_debt = False | No outcome data available regardless of cohort size |

### Pipeline Metadata

| Attribute | Rule | Source |
|-----------|------|--------|
| promoted_at | Current timestamp at promotion time | Generated by promote() function |

---

## Nullability Semantics

Null values in this model carry specific business meaning related to privacy suppression (BT-013) and derived field propagation:

| Pattern | Business Meaning |
|---------|-----------------|
| earnings_1yr_median IS NULL | 1-year earnings suppressed for privacy (cohort too small) |
| earnings_2yr_median IS NULL | 2-year earnings suppressed for privacy (different cohort) |
| debt_median IS NULL | Debt data suppressed for privacy |
| completions_count IS NULL | Completions count not reported for this measurement window |
| Percentile bands IS NULL | CIP family has fewer than 3 non-null values for the respective field |
| debt_to_earnings_annual IS NULL | Either debt or 1yr earnings is null (privacy suppression) |
| debt_to_earnings_tier IS NULL | Ratio is null (propagated from inputs) |
| earnings_growth_rate IS NULL | Either 1yr or 2yr earnings is null (privacy suppression or independent suppression) |
| cip_family_earnings_rank IS NULL | 1yr earnings is null (excluded from rank window) |
| program_value_index IS NULL | Either 1yr earnings or debt is null (privacy suppression) |

**Key invariant:** If confidence_tier = "insufficient", then ALL derived financial and percentile-dependent fields for that row are guaranteed null. The converse is not true -- a "medium" confidence row may still have some null derived fields.

---

## Dropped Fields (from Silver, with justification)

| Silver Attribute | Dropped? | Justification |
|-----------------|----------|---------------|
| completions_count_1 | Renamed | Renamed to `completions_count` in Gold for clarity (single completions measure) |
| completions_count_2 | Dropped | Second-major completions not relevant to career outcomes query pattern |
| credential_description | Dropped | Redundant with credential_level (always "Bachelor's Degree" in MVP) |
| ingested_at | Dropped | Silver metadata replaced by `promoted_at` in Gold |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attribute Group | Attributes | Notes |
|-------------------|------------------------|------------|-------|
| Career Outcome | Career Outcome (core) | record_id, earnings_1yr_median, earnings_2yr_median, debt_median, completions_count, small_cohort_flag | Central fact entity. Core outcome measures carried from Silver. |
| Program Identity | Career Outcome (identity) | unitid, institution_name, institution_control, cipcode, program_name, credential_level | Flattened into main table. Three natural key components. |
| CIP Family | Career Outcome (identity) | cip_family, cip_family_name | Carried from Silver. Also serves as partition key for percentile bands and earnings rank. |
| Earnings Percentile Band | Earnings Percentile Band | earnings_1yr_p25, earnings_1yr_p75, earnings_2yr_p25, earnings_2yr_p75, debt_p25, debt_p75 | 6 attributes derived via window functions. Shared value across all rows in same CIP family. |
| Financial Assessment | Financial Assessment | debt_to_earnings_annual, debt_to_earnings_tier, earnings_growth_rate, cip_family_earnings_rank, program_value_index | 5 derived metrics. All null-safe. |
| Data Confidence | Data Confidence | confidence_tier, has_earnings, has_debt, outcome_completeness | 4 attributes. confidence_tier is the only non-null derived field. |
| (Pipeline Metadata) | Pipeline Metadata | source_load_date, promoted_at | Not a conceptual entity -- pipeline infrastructure. |

---

## Continuity with Silver Logical Model

This logical model builds on `governance/models/silver-base-college-scorecard-logical.md`:

| Silver Logical Attribute | Gold Disposition | Gold Attribute | Change |
|-------------------------|-----------------|----------------|--------|
| record_id (prefix 'cs') | Recomputed | record_id (prefix 'co') | Prefix changes to distinguish zones |
| unitid | Carried | unitid | Verbatim |
| institution_name | Carried | institution_name | Verbatim |
| institution_control | Carried | institution_control | Verbatim |
| cipcode | Carried | cipcode | Verbatim |
| program_name | Carried | program_name | Verbatim |
| cip_family | Carried | cip_family | Verbatim |
| cip_family_name | Carried | cip_family_name | Verbatim |
| credential_level | Carried | credential_level | Verbatim |
| credential_description | Dropped | -- | Redundant with credential_level |
| earnings_1yr_median | Carried | earnings_1yr_median | Verbatim |
| earnings_2yr_median | Carried | earnings_2yr_median | Verbatim |
| debt_median | Carried | debt_median | Verbatim |
| completions_count_1 | Renamed | completions_count | Simplified name for consumable layer |
| completions_count_2 | Dropped | -- | Not relevant to career outcomes |
| small_cohort_flag | Carried | small_cohort_flag | Verbatim |
| source_load_date | Carried | source_load_date | Verbatim |
| ingested_at | Dropped | promoted_at (new) | Replaced by Gold-zone promotion timestamp |

**New in Gold (17 attributes):**
- 6 percentile band attributes (derived via window functions)
- 5 financial assessment attributes (derived via arithmetic/window)
- 4 data confidence attributes (derived via conditional logic)
- 1 pipeline metadata attribute (promoted_at)
- 1 surrogate key recomputed with new prefix (record_id)

---

## Constraints and Invariants

### Hard Constraints (DQ P0 -- block promotion if violated)

| Constraint | Rule | Scope |
|------------|------|-------|
| Grain uniqueness | Zero duplicates on (unitid, cipcode, credential_level) | Table-wide |
| Record ID uniqueness | Zero duplicates on record_id | Table-wide |
| Percentile band ordering | earnings_1yr_p25 <= earnings_1yr_p75 (and same for all band pairs) | Per CIP family |
| Confidence tier completeness | confidence_tier IS NOT NULL for every row | Row-level |
| Confidence tier value set | confidence_tier IN ('high', 'medium', 'low', 'insufficient') | Row-level |
| has_earnings accuracy | has_earnings = (earnings_1yr_median IS NOT NULL OR earnings_2yr_median IS NOT NULL) | Row-level |
| has_debt accuracy | has_debt = (debt_median IS NOT NULL) | Row-level |
| Outcome completeness value set | outcome_completeness IN (0.0, 0.33, 0.67, 1.0) | Row-level |
| Row count | Row count within +/- 15% of Silver source (69,947 expected) | Table-wide |

### Soft Constraints (DQ P1 -- warn but do not block)

| Constraint | Rule | Scope |
|------------|------|-------|
| Debt-to-earnings range | 0.01 <= debt_to_earnings_annual <= 10.0 (where non-null) | Row-level |
| Earnings growth range | -0.5 <= earnings_growth_rate <= 2.0 (where non-null) | Row-level |
| Earnings rank range | 0.0 <= cip_family_earnings_rank <= 1.0 (where non-null) | Row-level |
| Percentile band null pattern | Bands null if CIP family has < 3 non-null values for that field | Per CIP family |
| Null propagation consistency | debt_to_earnings_annual IS NULL when debt_median IS NULL OR earnings_1yr_median IS NULL | Row-level |

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | `institution_control` still has no business term (BT-XXX) | Cannot assign BT reference. Inherited from Silver logical model open issue #1. | @data-steward should propose a term before physical model. Does not block logical model approval. |
| 2 | Percentile band behavior for CIP families with exactly 3 data points | With 3 values, the p25 and p75 are mathematically valid but may not be statistically meaningful. | Accepted risk: minimum sample of 3 is per spec. Future iteration may raise threshold based on EDA findings. |

---

## Scope and Boundaries

- This logical model covers the `consumable.career_outcomes` table in the Gold zone only
- Source is the Silver `base.college_scorecard` table (single-source; no cross-source joins)
- CIP-to-SOC crosswalk integration is a future spec and not modeled here
- BLS and O*NET data sources are not included
- The model assumes Bachelor's Degree only (credential_level = 3) per MVP scope, but the grain supports future credential levels
- MCP zone serving is downstream and not part of this model
