# Logical Model: silver-base-onet-experience

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** Occupational Characteristics and Career Pathways
**Spec:** docs/specs/onet-experience-requirements.md
**Conceptual Model:** governance/models/silver-base-onet-experience-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-16
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)
**Human Approvals Referenced:** governance/approvals/onet-experience-requirements-open-decisions.md (tier thresholds, 10+ midpoint, multi-detail aggregation -- approved 2026-04-16)

---

```mermaid
erDiagram
    ONET_EXPERIENCE_PROFILES {
        identifier record_id PK
        identifier bls_soc_code NK
        numeric experience_category_median
        numeric experience_years_typical
        text experience_tier
        numeric experience_category_mode
        text experience_distribution
        numeric onet_details_averaged
        boolean suppress_flag
        date source_load_date
        timestamp ingested_at
    }

    ONET_OCCUPATIONS {
        identifier bls_soc_code PK
    }

    ONET_CAREER_TRANSITIONS {
        identifier bls_soc_code FK
        identifier related_bls_soc_code FK
    }

    ONET_EXPERIENCE_PROFILES ||--|| ONET_OCCUPATIONS : "characterizes"
    ONET_OCCUPATIONS ||--o{ ONET_CAREER_TRANSITIONS : "transitions from"
    ONET_OCCUPATIONS ||--o{ ONET_CAREER_TRANSITIONS : "transitions to"
    ONET_EXPERIENCE_PROFILES ||--o{ ONET_CAREER_TRANSITIONS : "gates"
```

---

## Grain and Uniqueness

| Table | Grain Fields | Surrogate Key | Expected Rows |
|-------|-------------|---------------|---------------|
| onet_experience_profiles | bls_soc_code | record_id (prefix `exp`) | ~867 |

Surrogate key computation: `compute_grain_id(row, ['bls_soc_code'], prefix='exp')`. Zero duplicates enforced on the grain field at promote-time.

---

## Table: onet_experience_profiles

Typical prior work experience required to enter an occupation, summarized at BLS SOC granularity. One row per occupation with RW (Related Work Experience) coverage in O*NET. Backs the experience-gating feature on the Gold `consumable.career_branches` table.

### Attributes

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from `bls_soc_code` using `compute_grain_id(row, ['bls_soc_code'], prefix='exp')`. Stable across pipeline re-runs. Format: `exp-<16 hex chars>`. |
| bls_soc_code | BT-027 | identifier | NOT NULL | true | false | 6-digit BLS SOC code (XX-XXXX), truncated from O*NET-SOC. Single-field natural key. Primary join key for `base.onet_occupations`, `base.onet_career_transitions`, `base.bls_ooh`, and the CIP-SOC crosswalk. |
| experience_category_median | BT-117 | numeric | NOT NULL | false | false | Weighted median RW category (1-11) computed from the percent frequency distribution. Internal derivation intermediate retained for auditability. Tie-breaking at 50% cumulative frequency picks the lower-numbered category. |
| experience_years_typical | BT-117 | numeric | NOT NULL | true | false | Primary scalar summary. Midpoint years for the median category using the human-approved midpoint table (category 11 = 12 years). Range: 0.0 to 12.0. Drives Gold `related_experience_years` / `source_experience_years` and all downstream frontend gating. |
| experience_tier | BT-118 | text | NOT NULL | true | false | Four-value classifier: `entry` (0-1y), `early` (1-4y), `mid` (4-8y), `senior` (>8y). Thresholds human-approved 2026-04-16. Drives the UX gating decision in `career_tree.py` and decade bucketing in the frontend. |
| experience_category_mode | -- | numeric | NOT NULL | false | false | Most common RW category (the category with highest percent frequency). Range: 1-11. Diagnostic field; not used in scoring. Useful for detecting bimodal distributions when compared with `experience_category_median`. |
| experience_distribution | BT-117 | text | NOT NULL | false | false | JSON object mapping RW category (1-11) to percent frequency, e.g. `{"1": 5.2, "7": 45.3, "8": 30.1, ...}`. Preserves full source distribution for downstream analysts who need to recompute alternative summaries. |
| onet_details_averaged | BT-063 | numeric | NOT NULL | false | false | Count of O*NET detail codes (XX-XXXX.XX) that contributed to this BLS-level aggregate. 1 for single-detail occupations, 2+ for multi-detail (e.g., `15-1252.00` + `15-1252.01`). Human-approved aggregation is unweighted average. |
| suppress_flag | BT-062 | boolean | NOT NULL | false | false | True if `recommend_suppress = "Y"` in ANY Bronze row contributing to this aggregate. Signals unreliable estimate. Expected very low true rate (<1%). |
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. |

---

## Attribute Summary

| Category | Count |
|----------|-------|
| Total attributes | 11 |
| Primary key | 1 (record_id) |
| Natural key | 1 (bls_soc_code) |
| CDE | 3 (bls_soc_code, experience_years_typical, experience_tier) |
| PII | 0 |
| Nullable | 0 |
| NOT NULL | 11 |
| Derived at this layer | 8 (record_id, experience_category_median, experience_years_typical, experience_tier, experience_category_mode, experience_distribution, onet_details_averaged, suppress_flag) |
| Carried from upstream | 1 (source_load_date) |
| Generated at write | 1 (ingested_at) |
| Cross-referenced (FK) | 1 (bls_soc_code to onet_occupations.bls_soc_code) |

---

## Type Domain Definitions

Aligned with the existing O*NET Silver models. Physical model maps these to DuckDB + PyIceberg types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR / StringType |
| text | A human-readable label, description, or structured string (JSON). Not used for joins. | VARCHAR / StringType |
| numeric (counts/categories) | Small positive integer. | INTEGER / IntegerType |
| numeric (ratings/averages) | Continuous value with decimal precision from averaging. | DOUBLE / DoubleType |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN / BooleanType |
| date | A calendar date without time component. | DATE / DateType |
| timestamp | A point in time with timezone context. | TIMESTAMP / TimestampType |

---

## Foreign Key Relationships

| Source Table | Source Column | Target Table | Target Column | Cardinality | Enforcement |
|-------------|-------------|-------------|--------------|-------------|-------------|
| onet_experience_profiles | bls_soc_code | onet_occupations | bls_soc_code | one-to-one-or-zero | Referential integrity DQ rule |

Every `bls_soc_code` in `onet_experience_profiles` must exist in `onet_occupations`. The reverse is not required -- some occupations may lack RW coverage in O*NET and therefore have no experience profile.

**Gold-zone consumers (documented; enforced in Gold DQ rules, not Silver):**

| Gold Column | Joins To |
|-------------|----------|
| consumable.career_branches.soc_code | onet_experience_profiles.bls_soc_code (as `source_experience_years`) |
| consumable.career_branches.related_soc_code | onet_experience_profiles.bls_soc_code (as `related_experience_years`) |

---

## Derivation Lineage

All 8 derived attributes originate from Bronze table `raw.onet_experience` filtered to `scale_id = 'RW'` and `element_id = '3.A.1'`. The derivation chain is:

```
raw.onet_experience                              (~35,881 rows, 4 scales)
  |-- WHERE scale_id = 'RW' AND element_id = '3.A.1'
  |   (Related Work Experience only; ~11,176 rows at O*NET-SOC x category grain)
  |
  |-- Group by onet_soc_code (O*NET detail level)
  |   Compute weighted median category and mode per detail
  |   Convert median category to midpoint years
  |
  |-- Truncate onet_soc_code -> bls_soc_code (first 7 chars)
  |
  |-- Group by bls_soc_code (BLS level)
  |   Unweighted average of experience_years_typical across details
  |   Merge distribution dicts by averaging
  |   Logical OR on suppress_flag across contributing details
  |
  v
base.onet_experience_profiles                    (~867 rows)
```

### Derivation Rules

| Derived Attribute | Rule | Source |
|-------------------|------|--------|
| record_id | `compute_grain_id(row, ['bls_soc_code'], prefix='exp')` | bls_soc_code |
| bls_soc_code | `onet_soc_code[:7]` (truncate O*NET-SOC XX-XXXX.XX to BLS SOC XX-XXXX) | raw.onet_experience.onet_soc_code |
| experience_category_median | Weighted median of RW categories using `data_value` (percent frequency) as weights. Find the category where cumulative frequency first reaches 50%. Tie-break: pick lower-numbered category. Compute at O*NET-SOC detail level, then carry median-years through BLS aggregation. | raw.onet_experience.category, raw.onet_experience.data_value (WHERE scale_id = 'RW') |
| experience_years_typical | Map `experience_category_median` to midpoint years using the approved table (see §Midpoint Mapping below). For multi-detail BLS SOCs, take unweighted average of midpoint values across contributing details. | experience_category_median |
| experience_tier | `CASE WHEN years <= 1 THEN 'entry' WHEN years <= 4 THEN 'early' WHEN years <= 8 THEN 'mid' ELSE 'senior' END` using the human-approved thresholds. | experience_years_typical |
| experience_category_mode | `ARGMAX(data_value)` over categories for a given O*NET-SOC. For multi-detail, pick the category with highest total `data_value` across details (tie-break: lower-numbered). | raw.onet_experience.category, raw.onet_experience.data_value |
| experience_distribution | JSON object: for each RW category 1-11, compute the average `data_value` across contributing O*NET details. Stored as a JSON string. | raw.onet_experience.category, raw.onet_experience.data_value |
| onet_details_averaged | `COUNT(DISTINCT onet_soc_code)` per bls_soc_code group | raw.onet_experience.onet_soc_code |
| suppress_flag | `MAX(CASE WHEN recommend_suppress = 'Y' THEN 1 ELSE 0 END) = 1` (logical OR across contributing rows) | raw.onet_experience.recommend_suppress |
| source_load_date | `CAST(raw_load_date AS DATE)` | raw.onet_experience.load_date |
| ingested_at | `CURRENT_TIMESTAMP` generated at Silver write time | -- |

### Midpoint Mapping (Human-Approved)

Source of approval: `governance/approvals/onet-experience-requirements-open-decisions.md` Decision 2.

| RW Category | Description | Midpoint Years |
|-------------|-------------|----------------|
| 1 | None | 0.0 |
| 2 | Up to and including 1 month | 0.0 |
| 3 | Over 1 month, up to and including 3 months | 0.17 |
| 4 | Over 3 months, up to and including 6 months | 0.38 |
| 5 | Over 6 months, up to and including 1 year | 0.75 |
| 6 | Over 1 year, up to and including 2 years | 1.5 |
| 7 | Over 2 years, up to and including 4 years | 3.0 |
| 8 | Over 4 years, up to and including 6 years | 5.0 |
| 9 | Over 6 years, up to and including 8 years | 7.0 |
| 10 | Over 8 years, up to and including 10 years | 9.0 |
| 11 | Over 10 years | **12.0** (human-approved) |

### Tier Thresholds (Human-Approved)

Source of approval: `governance/approvals/onet-experience-requirements-open-decisions.md` Decision 1.

| Tier | Range | SQL |
|------|-------|-----|
| `entry`  | 0 ≤ years ≤ 1  | `years <= 1` |
| `early`  | 1 < years ≤ 4  | `years > 1 AND years <= 4` |
| `mid`    | 4 < years ≤ 8  | `years > 4 AND years <= 8` |
| `senior` | years > 8      | `years > 8` |

---

## Transformation Rules

### Filtering (Bronze -> Silver)

| Filter | Effect |
|--------|--------|
| `scale_id = 'RW'` | Restricts to Related Work Experience. Excludes RL (Education), PT (On-Site Training), OJ (On-the-Job Training). |
| `element_id = '3.A.1'` | Restricts to the single element carrying the RW distribution. |
| Exclude occupations with zero RW rows | Occupations without RW coverage produce no Silver row (absent, not null). |

### Aggregation (O*NET detail -> BLS SOC)

| Attribute | Method |
|-----------|--------|
| experience_years_typical | Unweighted mean across details (human-approved Decision 3) |
| experience_category_median | Recomputed at O*NET detail level; not aggregated (the BLS-level median category is inferred from the aggregated years value via the inverse midpoint table) |
| experience_category_mode | Category with highest aggregate `data_value` across details |
| experience_distribution | Per-category average of `data_value` across details |
| suppress_flag | Logical OR across details |
| onet_details_averaged | Count of distinct contributing O*NET-SOC codes |

---

## Nullability Semantics

All 11 attributes are NOT NULL. Rationale:

| Pattern | Reason |
|---------|--------|
| Identifier/key fields | Grain and surrogate keys always present by construction. |
| Derived scalars (years, tier, category fields) | O*NET RW data is complete for all occupations with any RW coverage; occupations without coverage are excluded entirely rather than producing rows with null values. |
| Distribution JSON | Always populated (empty-distribution edge case produces no row per the test matrix). |
| Provenance fields | `onet_details_averaged >= 1` by construction; `suppress_flag` defaults to `false`. |
| Metadata | `source_load_date` carried from Bronze; `ingested_at` generated at write time. |

If a row exists in `onet_experience_profiles`, all fields are populated. Occupations with no RW data in Bronze simply do not appear -- this is documented as expected behavior for downstream joiners.

---

## Traceability: Conceptual to Logical

| Conceptual Entity / Attribute | Logical Table | Logical Attributes | Notes |
|-------------------------------|--------------|-------------------|-------|
| Experience Profile | onet_experience_profiles | All 11 attributes | Full entity realized in a single table. |
| Experience Profile > Occupation Identifier | onet_experience_profiles | bls_soc_code | Single-field natural key. |
| Experience Profile > Experience Years Typical | onet_experience_profiles | experience_years_typical | Scalar summary; primary Gold join input. |
| Experience Profile > Experience Tier | onet_experience_profiles | experience_tier | Classifier. |
| Experience Profile > Experience Distribution | onet_experience_profiles | experience_distribution, experience_category_median, experience_category_mode | Distribution JSON plus two scalar summaries for quick access. |
| Experience Profile > Provenance (suppression) | onet_experience_profiles | suppress_flag | Logical OR across contributing details. |
| Experience Profile > Provenance (detail count) | onet_experience_profiles | onet_details_averaged | Count of contributing O*NET detail codes. |
| Experience Tier (classifier) | -- | (enum values on experience_tier) | Not a separate table; see conceptual Modeling Decision 2. |
| Occupation | -- | (external FK to onet_occupations.bls_soc_code) | Defined in silver-base-onet. |
| Career Transition | -- | (external -- gated at Gold via career_branches) | Defined in silver-base-onet. |

---

## CDE Justification

| CDE Attribute | Justification |
|--------------|---------------|
| bls_soc_code | Grain key and primary cross-source join key. Same rationale as every other BLS-SOC-keyed Silver table. |
| experience_years_typical | Primary scalar measurement. Feeds Gold `related_experience_years` / `source_experience_years` / `experience_delta_years` and the frontend `max_experience_years` filter. Cross-boundary measurement. |
| experience_tier | Drives the UX gating decision in `backend/app/services/career_tree.py` (`max_experience_years` filter) and the frontend decade bucketing. Cross-boundary classifier. |

Non-CDE attributes are either internal derivation intermediates (`experience_category_median`, `experience_category_mode`), provenance (`experience_distribution`, `onet_details_averaged`, `suppress_flag`), or pipeline metadata (`source_load_date`, `ingested_at`). The CDE tagging matches §CDE & PII Assessment in the spec.

---

## Open Issues

None. All prior open decisions resolved in `governance/approvals/onet-experience-requirements-open-decisions.md` before this model was authored.
