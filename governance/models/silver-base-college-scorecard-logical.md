# Logical Model: silver-base-college-scorecard

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** Higher Education Outcomes
**Spec:** docs/specs/silver-base-college-scorecard.md
**Conceptual Model:** governance/models/silver-base-college-scorecard-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-06
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    COLLEGE_SCORECARD {
        identifier record_id PK
        identifier unitid NK
        text institution_name
        text institution_control
        identifier cipcode NK
        text program_name
        identifier cip_family
        text cip_family_name
        numeric credential_level NK
        text credential_description
        numeric earnings_1yr_median
        numeric earnings_2yr_median
        numeric debt_median
        numeric completions_count_1
        numeric completions_count_2
        boolean small_cohort_flag
        date source_load_date
        timestamp ingested_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies 8 entities (Institution, Academic Program, CIP Family, Credential Type, Program Offering, Earnings 1yr, Earnings 2yr, Debt Outcome, Completions Measure). Per the Silver Base zone pattern, these are flattened into a single denormalized `base.college_scorecard` table. The conceptual entities inform attribute grouping below but do not produce separate tables.

This is appropriate because:
1. The source data is already at the program-offering grain with all attributes in a single row
2. Silver Base tables are designed as wide, query-ready fact tables for downstream Gold zone consumption
3. No many-to-many relationships exist at this grain -- all conceptual entities resolve to 1:1 or 1:0..1 per row

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per program offering: a specific academic program at a specific institution at a specific credential level |
| **Natural key fields** | `unitid` + `cipcode` + `credential_level` |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'cs') |
| **Uniqueness constraint** | Zero duplicates on natural key. Enforced at load time. |
| **Expected cardinality** | 69,947 rows (MVP) |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The `NK` marker denotes natural key components.

### Program Offering (Core Identity)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key (unitid + cipcode + credential_level) using `compute_grain_id()` with prefix 'cs'. Stable across pipeline re-runs. |

### Institution

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| unitid | BT-001 | identifier | NOT NULL | true | false | IPEDS 6-digit institution identifier. Part of the natural key. Authoritative, stable across reporting years. |
| institution_name | BT-002 | text | NOT NULL | false | false | Official institution name as reported to IPEDS. Multi-campus systems may share the same name across distinct UNITIDs. |
| institution_control | *pending* | text | NOT NULL | false | false | Type of institutional governance: Public, Private nonprofit, or Private for-profit. Sourced from the CONTROL field (1=Public, 2=Private nonprofit, 3=Private for-profit). Required for Gold zone segmentation by institution type. **Note:** No business term exists yet -- @data-steward should propose one (suggested: BT-018). |

### Academic Program

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| cipcode | BT-003 | identifier | NOT NULL | false | false | CIP code in normalized XX.XXXX format (dot inserted at position 2). Classifies the academic program. Part of the natural key. |
| program_name | BT-004 | text | NOT NULL | false | false | Human-readable description of the academic program corresponding to its CIP code. 1:1 mapping with cipcode. |

### CIP Family

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| cip_family | BT-005 | identifier | NOT NULL | false | false | 2-digit CIP family code derived from the first two characters of the normalized cipcode. Represents broad discipline area (e.g., 52 = Business). |
| cip_family_name | BT-006 | text | NOT NULL | false | false | Human-readable label for the CIP family (e.g., "Business, Management, Marketing, and Related Support Services"). Derived via CIP taxonomy lookup. |

### Credential Type

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| credential_level | BT-007 | numeric | NOT NULL | false | false | Integer code indicating the credential type (3 = Bachelor's Degree in MVP). Part of the natural key. Full range: 1-8 for future credential levels. |
| credential_description | BT-008 | text | NOT NULL | false | false | Human-readable label for the credential level (e.g., "Bachelor's Degree"). 1:1 mapping with credential_level. |

### Earnings 1yr

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| earnings_1yr_median | BT-009 | numeric | NULLABLE | true | false | Median earnings (high estimate) of graduates 1 year after completion. Cohort-level aggregate, not individual data. Null when privacy-suppressed (cohort too small). Suppresses independently from 2yr -- 3,050 rows have 1yr data without 2yr data. |

### Earnings 2yr

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| earnings_2yr_median | BT-010 | numeric | NULLABLE | true | false | Median earnings (high estimate) of graduates 2 years after completion. Different cohort from 1yr (not longitudinal). Null when privacy-suppressed. 5,535 rows have 2yr data without 1yr data. 2yr may be lower than 1yr -- this is expected, not anomalous. |

### Debt Outcome

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| debt_median | BT-011 | numeric | NULLABLE | true | false | Median cumulative federal loan debt at program completion, all student groups evaluated. Null when privacy-suppressed. |

### Completions Measure

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| completions_count_1 | BT-012 | numeric | NULLABLE | false | false | IPEDS-reported completions count (first major measurement window). Drives the small cohort flag. Highly correlated with completions_count_2 (r=0.984) but not identical. |
| completions_count_2 | BT-012 | numeric | NULLABLE | false | false | IPEDS-reported completions count (second major measurement window). Supplementary to completions_count_1. |
| small_cohort_flag | BT-014 | boolean | NOT NULL | false | false | Derived: True when `completions_count_1` is not null and `completions_count_1 < 30`. Indicates outcome data is likely privacy-suppressed and should be interpreted with caution. Programs are flagged, not excluded. |

### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the raw zone. Represents data fetch date, not outcome measurement date. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. Generated at transformation time. Used for pipeline auditing and data freshness tracking. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 18 | Total attributes |
| 3 | Natural key components (unitid, cipcode, credential_level) |
| 1 | Surrogate key (record_id) |
| 4 | CDE attributes (unitid, earnings_1yr_median, earnings_2yr_median, debt_median) |
| 0 | PII attributes |
| 5 | Nullable attributes (earnings_1yr_median, earnings_2yr_median, debt_median, completions_count_1, completions_count_2) |
| 13 | NOT NULL attributes |
| 3 | Derived attributes (record_id, small_cohort_flag, cip_family) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR or BIGINT depending on content |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure or count. May be aggregated. | DOUBLE (monetary), BIGINT (counts), INTEGER (codes) |
| boolean | A true/false flag derived from business rules. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | `compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='cs')` | unitid, cipcode, credential_level |
| cipcode (normalized) | Insert dot at position 2 of raw 4-digit CIP code: `raw[:2] + '.' + raw[2:]` | raw cipcode |
| cip_family | First 2 characters of normalized cipcode (before the dot) | cipcode |
| cip_family_name | Lookup cip_family against CIP 2020 taxonomy | cip_family |
| small_cohort_flag | `completions_count_1 IS NOT NULL AND completions_count_1 < 30` | completions_count_1 |
| institution_control | Map raw CONTROL integer to text: 1='Public', 2='Private nonprofit', 3='Private for-profit' | raw CONTROL field |

---

## Nullability Semantics

Null values in this model carry specific business meaning related to privacy suppression (BT-013):

| Pattern | Business Meaning |
|---------|-----------------|
| earnings_1yr_median IS NULL | 1-year earnings suppressed for privacy (cohort too small) or data not yet available |
| earnings_2yr_median IS NULL | 2-year earnings suppressed for privacy (different cohort from 1yr) |
| debt_median IS NULL | Debt data suppressed for privacy |
| completions_count_1 IS NULL | Completions count not reported for this measurement window |
| completions_count_2 IS NULL | Completions count not reported for this measurement window |
| Both earnings NULL | Most common pattern (56.1% of rows). Small programs with insufficient cohort sizes. |
| One earnings NULL, other present | 12.3% of rows. Independent suppression across measurement windows confirms separate entity modeling in conceptual model. |

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | `institution_control` has no business term in the glossary | Cannot assign BT-XXX reference. Glossary has 17 terms (BT-001 through BT-017) but none for institution control type. | @data-steward should propose BT-018 "Institution Control Type" before physical model. |
| 2 | CONTROL field not in raw Iceberg table | Silver transformer cannot source institution_control from `raw.college_scorecard`. Requires raw schema update or direct CSV read. | Spec notes option (a) preferred: update raw ingestor to include CONTROL field. |
| 3 | small_cohort_flag derivation when completions_count_1 is NULL | Spec says `completions_count_1 < 30` implies True, but if count is NULL, the flag behavior is ambiguous. | Proposed: NULL completions -> small_cohort_flag = True (conservative, assumes suppression likely). Needs human confirmation. |

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attributes | Notes |
|-------------------|--------------------|-------|
| Institution | unitid, institution_name, institution_control | Flattened into main table. unitid is part of natural key. |
| Academic Program | cipcode, program_name | Flattened. cipcode is part of natural key. |
| CIP Family | cip_family, cip_family_name | Derived from cipcode. Kept as attributes for query convenience. |
| Credential Type | credential_level, credential_description | Flattened. credential_level is part of natural key. Only value 3 in MVP. |
| Program Offering | record_id (+ natural key composite) | The grain entity. Represented by the row itself, not separate attributes beyond the key. |
| Earnings 1yr | earnings_1yr_median | Single nullable attribute. Independent suppression from 2yr. |
| Earnings 2yr | earnings_2yr_median | Single nullable attribute. Independent suppression from 1yr. |
| Debt Outcome | debt_median | Single nullable attribute. |
| Completions Measure | completions_count_1, completions_count_2, small_cohort_flag | Two count windows plus derived flag. |
| (Pipeline Metadata) | source_load_date, ingested_at | Not a conceptual entity -- pipeline infrastructure. |
