# Audit Trail: Business Glossary — gold-onet-profiles
**Date:** 2026-04-08
**Agent:** @data-steward
**Spec:** docs/specs/gold-onet-profiles.md
**Mode:** Greenfield
**Domain:** U.S. Occupational Information (O*NET Task-Level Work Analysis)

## New Terms Proposed (7)

| Term ID | Term | Source | Category | Status | Rationale |
|---------|------|--------|----------|--------|-----------|
| BT-066 | HMN Score (Human Edge) | project-specific | derived | PROPOSED | Novel FutureProof metric — ratio of human-intensive activity importance to total activity importance, mapped to 1-10 scale. Backs HMN pentagon stat. |
| BT-067 | Human-Intensive Activity | project-specific | classification | PROPOSED | Static classification of ~14 of 41 O*NET work activities as hard for AI to replicate. Most subjective decision in pipeline — flagged for adversarial audit. |
| BT-068 | Burnout Score | project-specific | derived | PROPOSED | Novel FutureProof metric — normalized weighted average of 9 burnout-relevant Work Context elements, mapped to 1-10 scale. Backs Burnout boss fight. |
| BT-069 | Burnout Driver | project-specific | derived | PROPOSED | Top 3 contributing context elements to burnout score. Powers Gemma narrative. |
| BT-070 | Work Profile | project-specific | entity | PROPOSED | Occupation-level Gold data product consolidating activity + context data into one consumable row. |
| BT-071 | Work Profile Confidence Tier | project-specific | classification | PROPOSED | 3-level quality tier (high/medium/low) distinct from BT-024 (career outcomes, 4 levels) and BT-052 (occupation profiles, 3 levels with different criteria). |
| BT-072 | Activity Importance Mean | project-specific | derived | PROPOSED | Mean of all 41 IM values per occupation — summary statistic for activity intensity. |

## Existing Terms Updated (used_in_models)

| Term ID | Term | Added Model |
|---------|------|-------------|
| BT-015 | Record ID | gold-onet-profiles |
| BT-016 | Source Load Date | gold-onet-profiles |
| BT-026 | Promotion Timestamp | gold-onet-profiles |
| BT-027 | SOC Code | gold-onet-profiles |
| BT-054 | FutureProof Stat Mapping | gold-onet-profiles |
| BT-055 | O*NET-SOC Code | gold-onet-profiles |
| BT-056 | Content Model Element ID | gold-onet-profiles |
| BT-057 | Work Activity Importance | gold-onet-profiles |
| BT-058 | Work Context Value | gold-onet-profiles |
| BT-059 | Burnout Element | gold-onet-profiles |
| BT-060 | Career Transition (Similarity) | gold-onet-profiles |
| BT-061 | Relatedness Tier | gold-onet-profiles |
| BT-062 | Suppress Flag | gold-onet-profiles |
| BT-064 | Data Completeness Tier (O*NET) | gold-onet-profiles |

## Approval Notes

All 7 new terms are **project-specific** (invented by this project). Per governance rules, project-specific terms require human approval regardless of the REQUIRE_HUMAN_APPROVAL setting. None of these terms come from external or domain standards — they are novel FutureProof metrics and classifications.

The external/domain-standard terms referenced by this spec (SOC Code, O*NET-SOC Code, Content Model Element ID, Work Activity Importance, Work Context Value, Relatedness Tier) were already defined and auto-approved in the silver-base-onet glossary pass. Only their used_in_models arrays were updated.

## Ambiguities Found

None. All terms have clear, non-overlapping definitions. The three confidence tier terms (BT-024, BT-052, BT-071) are distinct concepts with different criteria and different Gold tables — no collision.

## Validation

Glossary validated successfully: `uv run python3 -m brightsmith.infra.glossary_validator validate` -> PASS
