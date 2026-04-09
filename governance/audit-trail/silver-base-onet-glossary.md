# Audit Trail: Business Glossary — silver-base-onet

**Date:** 2026-04-08
**Agent:** @data-steward
**Spec:** silver-base-onet
**Mode:** Greenfield
**Domain:** U.S. Occupational Information — O*NET Content Model

---

## Summary

Identified and proposed 11 new business terms from the silver-base-onet spec, and updated 4 existing terms with `used_in_models` references. Validation passed via `brightsmith.infra.glossary_validator`.

## Existing Terms Updated (used_in_models only)

| Term ID | Term | Change |
|---------|------|--------|
| BT-015 | Record ID | Added "silver-base-onet" to used_in_models |
| BT-016 | Source Load Date | Added "silver-base-onet" to used_in_models |
| BT-017 | Ingestion Timestamp | Added "silver-base-onet" to used_in_models |
| BT-027 | SOC Code | Added "silver-base-onet" to used_in_models |

## New Terms Proposed

| Term ID | Term | Source | Category | Status | Rationale |
|---------|------|--------|----------|--------|-----------|
| BT-055 | O*NET-SOC Code | external-standard | classification | AUTO-APPROVED | O*NET-SOC 2019 taxonomy, authoritative from DOL-ETA. Extended SOC code format (XX-XXXX.XX) is the primary identifier in all O*NET tables. |
| BT-056 | Content Model Element ID | external-standard | classification | AUTO-APPROVED | O*NET Content Model taxonomy. Hierarchical IDs (4.A.x.x.x, 4.C.x.x.x) are the authoritative identifiers for work dimensions. |
| BT-057 | Work Activity Importance | external-standard | measurement | AUTO-APPROVED | O*NET IM scale (1-5). Authoritative measurement from O*NET incumbent/expert surveys. Backs HMN stat. |
| BT-058 | Work Context Value | external-standard | measurement | AUTO-APPROVED | O*NET CX/CT scales. Authoritative point-estimate measurements for work environment dimensions. |
| BT-059 | Burnout Element | project-specific | classification | PROPOSED | Project-invented flag identifying ~9 Work Context elements relevant to burnout risk. Requires human approval for element selection. |
| BT-060 | Career Transition (Similarity) | project-specific | entity | PROPOSED | Project-specific concept: O*NET Related Occupations reframed as career transitions with the caveat that these measure similarity, not observed transitions. |
| BT-061 | Relatedness Tier | external-standard | classification | AUTO-APPROVED | Native O*NET 30.2 column in Related Occupations file. Three-tier classification (Primary-Short, Primary-Long, Supplemental). |
| BT-062 | Suppress Flag | project-specific | derived | PROPOSED | Derived from O*NET recommend_suppress field. Project-specific because it aggregates across multi-detail codes using logical OR. |
| BT-063 | Multi-Detail Aggregation | project-specific | derived | PROPOSED | Project-specific aggregation methodology for rolling up O*NET detail codes to BLS SOC level. |
| BT-064 | Data Completeness Tier (O*NET) | project-specific | classification | PROPOSED | Project-specific three-tier classification of O*NET data coverage per occupation. |
| BT-065 | Importance Rank | project-specific | derived | PROPOSED | Project-derived within-occupation rank of work activity importance. |

## Approval Summary

- **Auto-approved (5 terms):** BT-055, BT-056, BT-057, BT-058, BT-061 -- all sourced from authoritative external standards (O*NET/BLS).
- **Proposed / Requires Human Approval (6 terms):** BT-059, BT-060, BT-062, BT-063, BT-064, BT-065 -- all project-specific terms. Per REQUIRE_HUMAN_APPROVAL = true and Brightsmith rules, project-specific terms always require human review.

## Ambiguities Found

None. All O*NET terms are well-defined by the O*NET Content Model documentation and domain context. The only open decision is the exact list of burnout-relevant elements (BT-059), which the spec proposes 9 elements but notes they need confirmation against actual Bronze data.

## Validation

- `uv run python3 -m brightsmith.infra.glossary_validator validate` -> PASS
- `uv run python3 -m brightsmith.infra.pipeline_gate complete silver-base-onet data-steward --output governance/business-glossary.json` -> COMPLETED
