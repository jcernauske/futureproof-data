# Logical Model: gold-ai-exposure

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Gold (Consumable)
**Domain:** AI Exposure and Resilience Scoring
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 3: Gold)
**Conceptual Model:** governance/models/gold-ai-exposure-conceptual.md
**Author:** @semantic-modeler
**Date:** 2026-04-09
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)
**Source Model:** governance/models/silver-base-karpathy-ai-exposure-logical.md

---

```mermaid
erDiagram
    AI_EXPOSURE_PROFILE {
        identifier record_id PK
        identifier soc_code NK
        text occupation_title
        integer exposure_score
        text rationale
        text category
    }
    RESILIENCE_SCORING {
        identifier soc_code PK
        integer stat_res
        integer boss_ai_score
    }
    PIPELINE_METADATA {
        identifier soc_code PK
        timestamp promoted_at
    }
    AI_EXPOSURE_PROFILE ||--|| RESILIENCE_SCORING : "derives"
    AI_EXPOSURE_PROFILE ||--|| PIPELINE_METADATA : "tracked by"
```

---

## Entity: AI Exposure Profile

The central entity carrying the Karpathy AI exposure assessment for a single occupation.

| Attribute | Domain | Key | Nullable | Business Term | Is CDE | Is PII | Description |
|-----------|--------|-----|----------|---------------|--------|--------|-------------|
| record_id | identifier | PK | NOT NULL | BT-015 | false | false | Deterministic grain hash with prefix 'aie'. Stable across re-runs. |
| soc_code | identifier | NK | NOT NULL | BT-027 | true | false | SOC occupation code in XX-XXXX format. Natural key. Non-null guaranteed by bls_match=true filter. |
| occupation_title | text | -- | NOT NULL | BT-028 | false | false | Karpathy's occupation title. Carried from Silver. |
| exposure_score | integer | -- | NOT NULL | BT-094 | true | false | Original Karpathy 0-10 AI exposure score. Preserved for transparency. Input to stat_res and boss_ai_score derivations. |
| rationale | text | -- | NOT NULL | BT-095 | false | false | LLM-generated 2-3 sentence explanation of the exposure score. Display field for Fight AI boss narrative. |
| category | text | -- | NOT NULL | -- | false | false | Karpathy's BLS category grouping (e.g., "business-and-financial"). Carried from Silver. |

---

## Entity: Resilience Scoring

Derived gameplay stats computed from the exposure score.

| Attribute | Domain | Key | Nullable | Business Term | Is CDE | Is PII | Description |
|-----------|--------|-----|----------|---------------|--------|--------|-------------|
| soc_code | identifier | PK | NOT NULL | BT-027 | true | false | Foreign key to AI Exposure Profile. |
| stat_res | integer | -- | NOT NULL | BT-080 | true | false | AI Resilience stat, 1-10. Formula: MIN(11 - exposure_score, 10). Higher = more resilient. Backs RES pentagon stat. |
| boss_ai_score | integer | -- | NOT NULL | BT-083 | true | false | Fight AI boss strength, 1-10. Formula: MAX(exposure_score, 1). Higher = harder fight. Backs AI boss. |

### Derivation Rules

| Derived Attribute | Formula | Domain Constraint | Invariant |
|-------------------|---------|-------------------|-----------|
| stat_res | MIN(11 - exposure_score, 10) | 1 <= stat_res <= 10 | stat_res + boss_ai_score = 11 when exposure_score >= 1 |
| boss_ai_score | MAX(exposure_score, 1) | 1 <= boss_ai_score <= 10 | Floor of 1 ensures every boss has minimum strength |

---

## Entity: Pipeline Metadata

| Attribute | Domain | Key | Nullable | Business Term | Is CDE | Is PII | Description |
|-----------|--------|-----|----------|---------------|--------|--------|-------------|
| soc_code | identifier | PK | NOT NULL | BT-027 | true | false | Foreign key to AI Exposure Profile. |
| promoted_at | timestamp | -- | NOT NULL | BT-026 | false | false | Timestamp when the row was promoted to the Gold zone. |

---

## Filter Logic (Silver to Gold)

| Filter | Logic | Effect |
|--------|-------|--------|
| BLS match | WHERE bls_match = true | Drops ~30 rows where SOC code not found in base.bls_ooh |
| Non-null SOC | WHERE soc_code IS NOT NULL | Drops rows with unresolved SOC (subset of bls_match=false) |

Combined effect: ~419 Silver rows reduce to ~389 Gold rows. Only occupations joinable to the FutureProof BLS data are promoted.

---

## Continuity with Silver Logical Model

| Silver Attribute | Gold Disposition | Notes |
|-----------------|-----------------|-------|
| record_id | Re-keyed | New prefix 'aie' (Silver uses 'kai'). Different grain after filtering. |
| soc_code | Carried | Natural key. Now guaranteed non-null. |
| slug | Dropped | Provenance field not needed in consumable. |
| occupation_title | Carried | Verbatim. |
| category | Carried | Verbatim. |
| exposure_score | Carried + input to derivation | Verbatim. Also feeds stat_res and boss_ai_score formulas. |
| rationale | Carried | Verbatim. Display field. |
| bls_match | Consumed as filter | Used as WHERE clause, not carried forward. |
| soc_resolved_method | Dropped | Provenance field not needed in consumable. |
| source_load_date | Dropped | Pipeline metadata not needed in consumable. |
| ingested_at | Replaced by promoted_at | Gold uses its own promotion timestamp. |
| -- (new) | stat_res derived | New field: MIN(11 - exposure_score, 10). |
| -- (new) | boss_ai_score derived | New field: MAX(exposure_score, 1). |
