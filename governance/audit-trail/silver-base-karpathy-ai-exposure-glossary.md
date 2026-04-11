# Business Glossary Stewardship: silver-base-karpathy-ai-exposure

**Date:** 2026-04-09
**Agent:** @data-steward
**Mode:** Greenfield
**Domain:** Education / Career Guidance (AI Exposure Analysis)
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 2: Silver)

---

## Critical Issue Found: Duplicate Term IDs (BT-080, BT-081)

The glossary contained **duplicate term_id entries** for BT-080 and BT-081. Two different specs created terms with the same IDs:

| Term ID | First Entry (gold-futureproof-engine) | Second Entry (raw-ingest-karpathy-ai-exposure) |
|---------|--------------------------------------|----------------------------------------------|
| BT-080 | AI Resilience (stat_res) -- the derived pentagon stat | AI Exposure Score (Karpathy) -- the source metric |
| BT-081 | Boss Fight Score -- the general boss fight concept | AI Exposure Rationale -- the LLM explanation field |

These are **distinct concepts** that were assigned colliding IDs. The second set was appended without checking the existing glossary for ID conflicts.

### Resolution

- Renumbered the Karpathy source data terms to **BT-094** and **BT-095**
- BT-080 (AI Resilience) and BT-083 (Boss AI Score) definitions updated from "PLACEHOLDER" language to reflect that the Karpathy source data now provides their derivation inputs
- Updated all related_terms cross-references between the four terms
- Updated used_in_models on BT-080 and BT-083 to include "gold-ai-exposure"

## New Terms Proposed

| Term ID | Term | Source | Category | Status | Rationale |
|---------|------|--------|----------|--------|-----------|
| BT-094 | AI Exposure Score (Karpathy) | project-specific | metric | PROPOSED | Source metric (0-10) from Karpathy's scoring pipeline. Feeds BT-080 (stat_res) and BT-083 (boss_ai_score) at Gold. |
| BT-095 | AI Exposure Rationale | project-specific | descriptive | PROPOSED | LLM-generated explanation. Display field for Fight AI boss narrative. |
| BT-096 | SOC Resolution Method | project-specific | classification | PROPOSED | Silver-zone classification of how each row's SOC code was determined (direct, title_match, broad_expansion, unresolved). |
| BT-097 | BLS Match Flag | project-specific | derived | PROPOSED | Boolean flag indicating whether a row's SOC code exists in base.bls_ooh. Filter criterion at Gold promotion. |

## Updated Terms

| Term ID | Term | Change |
|---------|------|--------|
| BT-080 | AI Resilience (stat_res) | Definition updated from "PLACEHOLDER" to derivation formula. related_terms now includes BT-094. used_in_models includes gold-ai-exposure. |
| BT-083 | Boss AI Score | Definition updated from "PLACEHOLDER" to derivation formula. related_terms now includes BT-094. used_in_models includes gold-ai-exposure. |

## Existing Terms Referenced by Silver Model

| Term ID | Term | Already In Glossary |
|---------|------|-------------------|
| BT-027 | SOC Code | Yes (auto-approved, external-standard) |
| BT-028 | Occupation Title | Yes (auto-approved, external-standard) |
| BT-080 | AI Resilience (stat_res) | Yes (proposed, project-specific) |
| BT-083 | Boss AI Score | Yes (proposed, project-specific) |

## Approval Assessment

All four new terms (BT-094 through BT-097) are **project-specific** -- they are pipeline concepts invented by this project, not drawn from external or domain standards. Per governance rules:

- `REQUIRE_HUMAN_APPROVAL = true` (per CLAUDE.md)
- Project-specific terms **always** require human approval regardless of the REQUIRE_HUMAN_APPROVAL toggle
- All four terms are set to `approval_status: "proposed"` and require human review before @semantic-modeler can reference them in conceptual models

**No terms qualify for auto-approval.** The Karpathy AI Exposure Score, while based on an external dataset, is not from a recognized standard or taxonomy -- it is an LLM-generated metric from a personal project. The scoring methodology, scale definition, and terminology are all project-specific.

## Ambiguities Found

1. **BT-094 category classification:** The spec calls this a "Business Glossary Term" but it sits between "metric" (a numeric measurement) and "measurement" (an observed value). Classified as "metric" because it is a scored estimate, not a direct measurement. However, the spec's own glossary table (Zone 2, line 155) defined it with the name "AI Exposure Score (Karpathy)" which matches the original BT-080 duplicate -- confirming the spec was written assuming these would be BT-080/BT-081, not knowing those IDs were already taken.

2. **Exposure Score vs. AI Resilience relationship:** BT-094 (exposure, 0-10) and BT-080 (resilience, 1-10) are mathematically linked but semantically opposite. Exposure measures vulnerability; resilience measures resistance. The glossary now correctly models these as separate terms with a related_terms link, not as the same concept.

## Spec Term ID Mapping Update Needed

The spec at `docs/specs/raw-ingest-karpathy-ai-exposure.md` (lines 155-158) references BT-080 and BT-081 for the Karpathy terms. These references are now stale and should be updated to BT-094 and BT-095 when the spec is next edited. This is non-blocking -- the glossary is the authoritative source, not the spec's inline table.

---

**Next step:** Human must approve BT-094, BT-095, BT-096, and BT-097 before @semantic-modeler (Step 3) can proceed.
