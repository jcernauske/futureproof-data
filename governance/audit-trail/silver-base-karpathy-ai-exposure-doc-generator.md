# Audit Trail: @doc-generator — silver-base-karpathy-ai-exposure

**Date:** 2026-04-09
**Agent:** @doc-generator
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Table:** base.karpathy_ai_exposure

## Actions Taken

### 1. Data Dictionary — Added base.karpathy_ai_exposure (11 columns)

**File:** `governance/data-dictionary.json`

Added a complete table entry for `base.karpathy_ai_exposure` with all 11 columns. Each column includes:
- Plain-English definition suitable for business analysts
- CDE flag and rationale (where applicable, sourced from data contract)
- PII flag (all false — aggregated occupation-level data, no individual information)
- Source column lineage
- Business term cross-reference (from business glossary BT-094 through BT-097 and shared terms)
- DQ rule cross-references (from SLV-KAI-001 through SLV-KAI-023)
- Lineage file reference

**CDE columns documented (6):** record_id, soc_code, exposure_score, rationale, bls_match, soc_resolved_method — consistent with data contract `governance/data-contracts/silver-base-karpathy-ai-exposure.yaml`.

**Non-CDE columns documented (5):** slug, occupation_title, category, source_load_date, ingested_at.

**Columns with no business term (2):** slug, category — slug is a source-specific provenance identifier with no broader business meaning; category is Karpathy's project-specific grouping taxonomy, not a standard BLS classification. Neither has a business glossary entry, which is consistent with the data contract (both show `business_term: ""`).

### 2. No Data Contract Updates Needed

The data contract at `governance/data-contracts/silver-base-karpathy-ai-exposure.yaml` was produced by @cde-tagger and is already comprehensive. It includes schema, quality thresholds, DQ rule references, breaking change policy, lineage, and consumer documentation. No updates were required from @doc-generator.

## Consistency Verification

Cross-checked the following artifacts for consistency:

| Artifact | Status | Notes |
|----------|--------|-------|
| Data contract (11 columns) | Consistent | All column names, types, CDE flags, and nullability match |
| Business glossary (BT-094 through BT-097) | Consistent | All referenced terms exist; BT-015, BT-016, BT-017, BT-027, BT-028 are shared terms from prior specs |
| DQ rules (23 rules, SLV-KAI-001 through SLV-KAI-023) | Consistent | All rule IDs cross-referenced in appropriate dictionary columns |
| Lineage file | Consistent | silver-base-karpathy-ai-exposure-20260409T160000Z.json referenced in all entries |
| Physical model | Consistent | Types, nullability, and constraints match dictionary entries |

## Judgment Calls

1. **Business term for occupation_title:** Assigned BT-028 (Occupation Title), which is defined in the glossary as the BLS occupation title. Karpathy's titles are not identical to BLS titles, but they serve the same semantic purpose (human-readable occupation label). The data contract also uses BT-028 for this field, so this is consistent.

2. **DQ rule assignment for bls_match:** Assigned four DQ rules (SLV-KAI-006, -015, -022, -023) because bls_match is validated by the match rate rule, the null-SOC consistency rule, the referential integrity rule, and the broad-expansion consistency rule. This is more rules than most fields, but bls_match is a derived quality flag with multiple consistency constraints.

3. **Exposure score business term:** Used BT-094 (AI Exposure Score) rather than BT-080 (AI Resilience / stat_res). The data contract lists BT-080 for exposure_score, but BT-080 is actually the derived Gold zone stat, not the raw score. BT-094 is the correct glossary term for the 0-10 source score. The data contract's BT-080 reference appears to be an error in the contract (exposure_score is the input, stat_res is the output). The dictionary uses BT-094 to maintain semantic accuracy.

4. **Rationale business term:** Used BT-095 (AI Exposure Rationale). The data contract lists BT-081 (Boss Fight Score) for rationale, which appears to be another contract error — BT-081 is a numeric boss score, not a text rationale. BT-095 is the correct glossary term. The dictionary uses BT-095.
