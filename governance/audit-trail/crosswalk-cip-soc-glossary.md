# Audit Trail: Business Glossary Update for crosswalk-cip-soc

**Date:** 2026-04-08
**Agent:** @data-steward
**Spec:** docs/specs/crosswalk-cip-soc.md
**Mode:** Greenfield (Silver zone, covers Bronze + Silver in one spec)
**Domain:** Higher Education Outcomes

## Summary

Added 4 new business terms (BT-073 through BT-076) for the CIP-SOC crosswalk spec. Updated 4 existing terms to reference the crosswalk model.

## New Terms Proposed

| Term ID | Term | Source | Category | Status | Rationale |
|---------|------|--------|----------|--------|-----------|
| BT-073 | CIP-SOC Crosswalk | external-standard | entity | AUTO-APPROVED | Official NCES/BLS publication. The crosswalk table itself is an authoritative federal artifact. |
| BT-074 | No Match Sentinel | domain-standard | classification | AUTO-APPROVED | SOC 99-9999 is a standard convention in the NCES crosswalk file format, not a project invention. |
| BT-075 | Join-Readiness Flag | project-specific | derived | PROPOSED | Pipeline-derived boolean flags (has_scorecard_match, has_bls_match, has_onet_match). Requires human approval. |
| BT-076 | Match Quality | project-specific | classification | PROPOSED | Pipeline-derived categorical classification computed from join-readiness flags. Requires human approval. |

## Existing Terms Updated (used_in_models + related_terms)

| Term ID | Term | Change |
|---------|------|--------|
| BT-003 | CIP Code | Added "crosswalk-cip-soc" to used_in_models; added BT-073 to related_terms |
| BT-005 | CIP Family | Added "crosswalk-cip-soc" to used_in_models |
| BT-027 | SOC Code | Added "crosswalk-cip-soc" to used_in_models; added BT-073 to related_terms |
| BT-029 | SOC Major Group | Added "crosswalk-cip-soc" to used_in_models |

## Terms NOT Added (Already Exist)

| Term ID | Term | Why Not Added |
|---------|------|---------------|
| BT-003 | CIP Code | Already in glossary. Updated used_in_models only. |
| BT-005 | CIP Family | Already in glossary. Updated used_in_models only. |
| BT-027 | SOC Code | Already in glossary. Updated used_in_models only. |
| BT-029 | SOC Major Group | Already in glossary. Updated used_in_models only. |
| BT-004 | Program Name | Already covers cip_title concept. |
| BT-028 | Occupation Title | Already covers soc_title concept. |
| BT-015 | Record ID | Already covers the compute_grain_id concept used in crosswalk. |
| BT-016 | Source Load Date | Already covers source_load_date field. |
| BT-017 | Ingestion Timestamp | Already covers ingested_at field. |

## Approval Decisions

- **BT-073 (CIP-SOC Crosswalk):** Auto-approved. Source is external-standard (official NCES/BLS publication). The authority is the federal government, not this project.
- **BT-074 (No Match Sentinel):** Auto-approved. Source is domain-standard (SOC 99-9999 is a recognized NCES crosswalk convention documented in the crosswalk file itself).
- **BT-075 (Join-Readiness Flag):** Proposed. Source is project-specific (derived flags invented by this pipeline). Requires human approval per Brightsmith governance rules.
- **BT-076 (Match Quality):** Proposed. Source is project-specific (derived classification invented by this pipeline). Requires human approval per Brightsmith governance rules.

## Ambiguities Found

None. All terms are clearly scoped to the crosswalk spec. No conflicting definitions with existing glossary terms.
