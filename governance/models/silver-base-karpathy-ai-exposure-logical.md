# Logical Model: silver-base-karpathy-ai-exposure

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Silver (Base)
**Domain:** AI Occupation Exposure Assessment
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 2: Silver)
**Conceptual Model:** governance/models/silver-base-karpathy-ai-exposure-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-09
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

```mermaid
erDiagram
    KARPATHY_AI_EXPOSURE {
        identifier record_id PK
        identifier soc_code NK
        text slug
        text occupation_title
        text category
        numeric exposure_score
        text rationale
        boolean bls_match
        text soc_resolved_method
        date source_load_date
        timestamp ingested_at
    }
```

---

## Design Rationale: Single Denormalized Table

The conceptual model identifies 4 entities (AI Exposure Assessment, Occupation Identity, SOC Resolution, BLS Occupation). Per the Silver Base zone pattern, the first three are flattened into a single denormalized `base.karpathy_ai_exposure` table. BLS Occupation is an external reference entity and is not stored in this table.

This is appropriate because:
1. All conceptual relationships resolve to 1:1 or 1:0..1 per row -- no many-to-many relationships exist at this grain
2. The source dataset is a single flat table (scores joined with occupation metadata) with one assessment per occupation
3. Silver Base tables are designed as wide, query-ready fact tables for downstream Gold zone consumption
4. This matches the established pattern from `base.bls_ooh` and `base.college_scorecard` (single denormalized table with conceptual entities as attribute groups)

---

## Grain and Uniqueness

| Property | Value |
|----------|-------|
| **Grain** | One row per occupation: a single SOC code after normalization, broad code expansion, and deduplication |
| **Natural key fields** | `soc_code` (for rows where SOC is non-null) |
| **Surrogate key** | `record_id` (deterministic hash of natural key via `compute_grain_id()` with prefix 'kai') |
| **Uniqueness constraint** | Zero duplicates on soc_code where non-null. Rows with null soc_code (unresolved) are allowed as exceptions to the grain uniqueness. |
| **Expected cardinality** | ~500+ rows (342 Bronze rows, minus SOC duplicates, plus broad code expansion to detailed codes) |

---

## Attribute Definitions

Attributes are grouped by the conceptual entity they originate from. The `NK` marker denotes natural key components.

### AI Exposure Assessment (Core Analytical Payload)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| exposure_score | BT-094 | numeric | NOT NULL | true | false | AI exposure score on a 0-10 integer scale. LLM-generated estimate of how much current AI will reshape this occupation. Higher = more exposed. Carried verbatim from Bronze -- no rescaling in Silver. Observed range in data: 1-10 (no zeros). Mode at 7 (20.5%). Backs the RES stat and boss_ai_score in Gold zone. |
| rationale | BT-095 | text | NOT NULL | false | false | 2-3 sentence LLM-generated explanation of the key factors driving the exposure score. Length range 297-587 characters. All 342 unique. Display field for the FutureProof frontend Fight AI boss narrative. Carried verbatim from Bronze. |

### Occupation Identity

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| record_id | BT-015 | identifier | NOT NULL | false | false | Deterministic surrogate key computed from the natural key (soc_code) using `compute_grain_id()` with prefix 'kai'. Format: `kai-<16 hex chars>`. Stable across pipeline re-runs. |
| soc_code | BT-027 | identifier | NULLABLE | true | false | SOC occupation code in XX-XXXX format. Natural key for non-null rows. Null for occupations where SOC could not be resolved (soc_resolved_method = "unresolved"). Primary join key to base.bls_ooh and downstream consumable tables. |
| slug | -- | text | NOT NULL | false | false | Karpathy's kebab-case occupation identifier (e.g., "financial-analysts"). Retained for provenance and traceability back to the source dataset. Was the Bronze grain; superseded by soc_code in Silver. |
| occupation_title | BT-028 | text | NOT NULL | false | false | Karpathy's occupation title from the BLS occupation listing. Used for title-based SOC resolution when soc_code is null in Bronze. |
| category | -- | text | NOT NULL | false | false | One of 25 Karpathy BLS category groupings (kebab-case, e.g., "business-and-financial", "healthcare"). Not a standard BLS taxonomy. Classification attribute for analysis and display. |

### SOC Resolution (Provenance Metadata)

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| bls_match | BT-097 | boolean | NOT NULL | false | false | True if soc_code was found in base.bls_ooh. False if the SOC code is valid but absent from our BLS data (SOC vintage mismatch or different BLS snapshot). Used as the Gold zone filter: only bls_match = true rows are promoted to consumable.ai_exposure. |
| soc_resolved_method | BT-096 | text | NOT NULL | false | false | Enum describing how the SOC code was determined. Valid values: "direct" (SOC present in source), "title_match" (resolved from occupation title), "broad_expansion" (propagated from broad code to detailed codes), "unresolved" (no SOC determined). Expected distribution: ~70% direct, ~15% broad_expansion, ~10% title_match, ~5% unresolved. |

### Pipeline Metadata

| Attribute | Business Term | Type Domain | Nullable | Is CDE | Is PII | Description |
|-----------|--------------|-------------|----------|--------|--------|-------------|
| source_load_date | BT-016 | date | NOT NULL | false | false | Date the source data was loaded into the Bronze zone. Represents data fetch date. Renamed from Bronze `load_date`. |
| ingested_at | BT-017 | timestamp | NOT NULL | false | false | Timestamp when the row was written to the Silver zone base table. Generated at transformation time. Used for pipeline auditing and data freshness tracking. |

---

## Attribute Summary

| Count | Category |
|-------|----------|
| 11 | Total attributes |
| 1 | Natural key components (soc_code) |
| 1 | Surrogate key (record_id) |
| 2 | CDE attributes (soc_code, exposure_score) |
| 0 | PII attributes |
| 1 | Nullable attributes (soc_code) |
| 10 | NOT NULL attributes |
| 3 | Derived attributes (record_id, bls_match, soc_resolved_method) |

---

## Type Domain Definitions

These are logical type categories, not physical implementations. Physical model will map these to DuckDB types.

| Domain | Semantics | Physical Expectation |
|--------|-----------|---------------------|
| identifier | A code or key used for lookup or joins. Not aggregated. | VARCHAR |
| text | A human-readable label or description. Not used for joins. | VARCHAR |
| numeric | A quantitative measure or code. May be aggregated (measures) or used for lookup (codes). | INTEGER (scores/codes) |
| boolean | A true/false flag derived from business rules or source data. | BOOLEAN |
| date | A calendar date without time component. | DATE |
| timestamp | A point in time with timezone context. | TIMESTAMP |

---

## Derivation Rules

| Derived Attribute | Rule | Source Attributes |
|-------------------|------|-------------------|
| record_id | `compute_grain_id(row, ['soc_code'], prefix='kai')` | soc_code |
| soc_code (normalized) | Validate XX-XXXX format, strip whitespace, confirm hyphen at position 3. For null-SOC Bronze rows: attempt title-based match against base.bls_ooh. For broad codes: expand to constituent detailed codes. | raw.soc_code, occupation_title, base.bls_ooh |
| bls_match | `soc_code IN (SELECT soc_code FROM base.bls_ooh)` | soc_code, base.bls_ooh |
| soc_resolved_method | Classification based on SOC resolution path: "direct" if SOC present in source and matches detailed code; "title_match" if resolved via title lookup; "broad_expansion" if propagated from broad to detailed; "unresolved" if null SOC after all resolution attempts | soc_code (raw), resolution logic |
| source_load_date | `CAST(raw_load_date AS DATE)` | load_date (raw) |
| ingested_at | `CURRENT_TIMESTAMP` | -- |

---

## Nullability Semantics

Null values in this model carry specific business meaning:

| Pattern | Business Meaning |
|---------|-----------------|
| soc_code IS NULL | Occupation could not be resolved to a SOC code after all resolution attempts (title match and broad expansion both failed). soc_resolved_method will be "unresolved". Row is preserved for completeness but will not join downstream. Expected: ~5% of rows (those from the 52 null-SOC Bronze rows that could not be title-matched). |

All other attributes are NOT NULL. The simplicity of the nullability model (only one nullable field) reflects the nature of this dataset: the exposure assessment data is complete for every occupation, and the only uncertainty is in SOC code resolution.

---

## Traceability: Conceptual to Logical

| Conceptual Entity | Logical Attributes | Notes |
|-------------------|--------------------|-------|
| AI Exposure Assessment | exposure_score, rationale | Core analytical payload. Carried verbatim from Bronze. No transformation applied. |
| Occupation Identity | record_id, soc_code, slug, occupation_title, category | soc_code is the natural key (grain change from slug). slug retained for provenance. category is a classification attribute. |
| SOC Resolution | bls_match, soc_resolved_method | Captures provenance of SOC assignment and cross-validation result against BLS. |
| BLS Occupation (external) | -- | Not stored in this table. Referenced via bls_match flag. |
| (Pipeline Metadata) | source_load_date, ingested_at | Not a conceptual entity -- pipeline infrastructure. |

---

## Cross-Source Integration

This table joins downstream via soc_code:

| Attribute | Integration Role |
|-----------|-----------------|
| soc_code | Primary join key to base.bls_ooh, consumable.occupation_profiles, consumable.program_career_paths, consumable.career_branches |
| bls_match | Filter: only true rows are promoted to Gold consumable.ai_exposure |
| slug | Traceability back to Karpathy source dataset |

---

## Modeling Decisions

1. **Single denormalized table.** All three internal conceptual entities flatten into one table. The 1:1 cardinalities make separate tables unnecessary. This matches the BLS OOH and College Scorecard Silver patterns.

2. **soc_code as nullable natural key.** Unlike base.bls_ooh (where soc_code is NOT NULL), this table allows null SOC codes for unresolved occupations. This is a design trade-off: we preserve completeness (all Karpathy occupations are represented) at the cost of a weaker grain constraint. The uniqueness constraint applies only to non-null soc_code values.

3. **record_id computed from soc_code, not slug.** The surrogate key uses the Silver grain (soc_code), not the Bronze grain (slug). For unresolved rows with null SOC, a fallback grain computation is needed (e.g., using slug as the hash input). This must be specified in the physical model.

4. **exposure_score typed as numeric (integer), not text.** The score is a quantitative measure on an ordinal scale. It is used in arithmetic derivations in Gold (MIN(11 - score, 10) for RES, MAX(score, 1) for boss). Integer typing enables these computations without casting.

5. **soc_resolved_method as a 4-value enum.** The spec defines exactly four resolution outcomes. This is modeled as a constrained text domain rather than separate boolean flags (is_direct, is_title_match, etc.) because the values are mutually exclusive -- every row has exactly one resolution method.

6. **No Karpathy cross-validation fields carried to Silver.** Bronze includes median_pay_annual, num_jobs_2024, and entry_education from occupations.csv for cross-validation purposes. These are not included in the Silver schema because: (a) the cross-validation was completed at Bronze (perfect wage alignment confirmed by EDA), (b) these fields duplicate data already in base.bls_ooh, and (c) carrying them forward would create data redundancy and maintenance burden.

7. **CDE assignments are minimal.** Only soc_code (join key) and exposure_score (the primary analytical measure driving Gold stats) are CDEs. The rationale is a display field, not a computed input. The bls_match flag is derived, not source data.

---

## Open Issues

| # | Issue | Impact | Resolution Path |
|---|-------|--------|----------------|
| 1 | slug and category have no business glossary terms | These are source-specific identifiers/classifications. slug is the Bronze grain key; category is Karpathy's non-standard grouping. | @data-steward may propose terms if these fields are referenced in downstream models or contracts. Low priority since they are not CDEs or join keys. |
| 2 | record_id computation for null-soc_code rows | The grain key is soc_code, but ~5% of rows have null SOC. compute_grain_id needs a fallback input. | Physical model must specify: use slug as the hash input when soc_code is null. This preserves determinism while accommodating the null-grain edge case. |
| 3 | Exact row count after expansion is unknown until implementation | EDA estimates ~500+ but the actual count depends on how many detailed codes each broad code fans out to in base.bls_ooh. | @primary-agent will determine exact count during Silver transformation. DQ rules should use a range (e.g., 400-700) rather than a point estimate. |
