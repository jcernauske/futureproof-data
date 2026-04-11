# Governance Review: raw-ingest-karpathy-ai-exposure (Pre-Implementation)

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** APPROVED (with ADVISORY notes)

## Pre-Implementation Checklist

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement is precise — identifies the missing RES stat and Fight AI boss as the gap. 10 success criteria are specific and measurable. |
| 2 | Input data sources identified with paths | PASS | Two source files (scores.json, occupations.csv) with GitHub raw URLs, fallback cache path, license assessment, and scoring methodology documented. Known limitations explicitly called out — excellent provenance. |
| 3 | Output artifacts defined with paths and formats | PASS | Iceberg tables named at every zone: raw.karpathy_ai_exposure, base.karpathy_ai_exposure, consumable.ai_exposure. Governance artifacts listed with full paths (9 items). |
| 4 | Transformations described (what changes, why) | PASS | Bronze: join scores.json + occupations.csv on slug. Silver: SOC normalization, null SOC resolution via title match, BLS cross-validation, duplicate SOC handling. Gold: RES score inversion (MIN(11 - exposure, 10)), boss score floor (MAX(exposure, 1)). Each transformation includes rationale. |
| 5 | Zone assignment correct | PASS | Multi-zone spec (Raw -> Silver -> Gold -> MCP). Zone assignments are correct — raw ingest of external data, normalization at Silver, business derivation at Gold, tool exposure at MCP. |
| 6 | Primary implementation agent identified | PASS | @primary-agent listed. Full 15-step agent workflow defined with clear ordering. |
| 7 | DQ rule categories specified | PASS | Detailed per-zone DQ rules: Bronze (9 rules), Silver (5 rules), Gold (7 rules). Severity levels (P0/P1) assigned to each. Cross-validation against existing BLS data included. |
| 8 | CDE mapping impact assessed | PASS | @cde-tagger is step 12 in the workflow. soc_code is an obvious CDE candidate (already tagged in existing tables). exposure_score and stat_res are new CDEs to assess. |
| 9 | Lineage scope defined | PASS | Lineage event path defined. Multi-zone transformations create a clear lineage chain: GitHub -> raw -> base -> consumable -> backfill into existing tables. |
| 10 | Breaking changes to existing schemas flagged | PASS | No breaking changes. Existing consumable tables (program_career_paths, career_branches) already have stat_res and boss_ai_score columns — they are null placeholders being backfilled. This is a data-level change, not a schema change. |
| 11 | Testing approach defined | PASS (implicit) | Not a standalone section, but success criteria, DQ rules, and cross-validation checks define the testing surface. Staff engineer minimum of 10 tests for Raw zone applies. |

### Data Model Gate

This is a multi-zone spec covering Bronze, Silver, and Gold.

- **Bronze zone:** SKIPPED — Bronze specs use physical-only models. The raw schema in the spec serves as the physical model. Correct per framework.
- **Silver zone (base.karpathy_ai_exposure):** Data models (conceptual, logical, physical) are listed in the governance artifacts section with paths at `governance/models/silver-base-karpathy-ai-exposure-{conceptual,logical,physical}.md`. These do not exist yet, which is correct — they will be produced by @semantic-modeler (step 7 in workflow). For greenfield Silver tables, models must be complete BEFORE implementation of the Silver transformer. The workflow correctly places @semantic-modeler before the Silver build step.
- **Gold zone (consumable.ai_exposure):** Same pattern — models listed at `governance/models/gold-ai-exposure-{conceptual,logical,physical}.md`. @semantic-modeler produces these before Gold implementation. Correct.

**Gate status:** Models will be required before Silver/Gold implementation proceeds. The Bronze ingest can begin immediately. The workflow ordering enforces this correctly.

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | **Missing domain source YAML.** No `domain/sources/karpathy_ai_exposure.yaml` exists yet. Other sources (college_scorecard, bls_ooh, onet, cip_soc_crosswalk) all have their source YAML files. @primary-agent should create this during implementation and register it in `domain/manifest.yaml`. | @primary-agent creates during implementation. Not blocking. |
| 2 | ADVISORY | **Spec title says "raw-ingest" but scope is full pipeline.** The spec covers Bronze through MCP (5 zones) including backfill of existing Gold tables. The naming convention "raw-ingest-*" suggests a Bronze-only scope. Prior multi-zone specs (e.g., crosswalk-cip-soc) used zone-neutral naming. This is a cosmetic issue — the spec content is clear about its full scope. | No action required. The spec is internally consistent about scope despite the name. |
| 3 | ADVISORY | **No explicit "Testing Approach" section.** Consistent with project convention (prior specs also omit this). The DQ rules and success criteria define the testing surface. Staff engineer will enforce the 10-test minimum for Raw zone. | @primary-agent should plan for 10+ tests at each zone level. |
| 4 | ADVISORY | **Business glossary terms pre-declared in spec.** The spec defines BT-080 and BT-081 with full definitions inline. This is good for clarity but @data-steward normally discovers and proposes these. The term IDs (080, 081) should be verified against the glossary to avoid collisions — current glossary may already use these IDs. | @data-steward should verify BT-080 and BT-081 are not already allocated before adding. |
| 5 | ADVISORY | **Backfill scope for existing Gold tables.** The spec modifies the join chain for consumable.program_career_paths and consumable.career_branches. These are existing COMPLETE specs. The backfill is additive (LEFT JOIN, filling null columns), not destructive, so no CAB review is needed. However, the re-promotion should re-run existing DQ rules for those tables to confirm no regressions. | @dq-engineer should re-run existing Gold DQ rules after backfill. |
| 6 | ADVISORY | **Inverse invariant DQ rule has an edge case.** The Gold DQ rule "stat_res + boss_ai_score = 11 for all rows where exposure_score >= 1" is correct. For exposure_score = 0: stat_res = 10 (capped) and boss_ai_score = 1 (floored), so 10 + 1 = 11 still holds. The invariant actually holds for ALL rows, not just exposure_score >= 1. The "where exposure_score >= 1" filter is unnecessary but harmless. | No action needed — the filter is conservative, not wrong. |

## Spec Quality Assessment

### Strengths

1. **Exceptional transformation documentation.** The RES score derivation table (Karpathy exposure -> stat_res -> meaning) makes the inversion logic immediately clear. The edge case handling (exposure 0 -> cap at 10) is explicitly worked through. This is the clearest derivation documentation in any spec in the project.

2. **Honest provenance.** The spec carries forward Karpathy's own caveat ("a saturday morning 2 hour vibe coded project") and lists five specific known limitations of LLM-generated scores. This transparency is critical for a data product — consumers know exactly what they are getting.

3. **Cross-validation built in.** Bronze DQ cross-validates median_pay_annual against existing BLS OOH data. Silver cross-validates SOC codes against base.bls_ooh. Gold cross-validates that every soc_code exists in consumable.occupation_profiles. Three layers of cross-source verification.

4. **Null SOC resolution strategy.** The spec defines a clear fallback chain: direct SOC from source -> title-based exact match -> fuzzy match -> unresolved. The soc_resolved_method field preserves provenance of how each SOC was resolved. This is good data engineering.

5. **Data contract is complete.** Owner, SLA, freshness, quality tier, consumers, row count guarantee, and null guarantees are all specified. Quality tier is honestly set to "Medium" given the LLM-generated nature of the data.

6. **Post-hackathon roadmap.** The spec documents how Karpathy's scores will eventually be replaced with Gemma-generated scores using richer inputs (O*NET tasks, Anthropic research). The pipeline architecture stays the same — only the source changes. This validates the pipeline design.

7. **Backfill impact analysis.** Expected coverage (~80-90% of program_career_paths rows) is estimated with clear reasoning (342 of 832 BLS occupations scored, crosswalk filters further). Sets realistic expectations.

## Cross-Reference Verification

| Check | Result |
|-------|--------|
| Spec references correct zones (Raw through MCP) | PASS |
| Pipeline state file exists (`governance/pipeline-state/raw-ingest-karpathy-ai-exposure-pipeline.json`) | PASS |
| Agent workflow matches Brightsmith pipeline template | PASS — all mandatory agents present |
| Governance artifact paths follow project convention | PASS |
| No conflicts with existing tables | PASS — raw.karpathy_ai_exposure, base.karpathy_ai_exposure, consumable.ai_exposure are all new |
| Backfill tables exist and have the target columns | PASS (per spec — stat_res and boss_ai_score are existing null placeholders) |
| SOC code is the join key to existing pipeline | PASS — consistent with BLS OOH and O*NET integration patterns |
| Business glossary term IDs not yet verified for collision | ADVISORY #4 |

## Decision Rationale

This spec is **approved for implementation**. It is a well-structured, multi-zone spec that fills a clear product gap (the missing RES stat and Fight AI boss) with a small, clean dataset (342 rows). The spec demonstrates strong engineering judgment:

- Source data limitations are honestly documented
- Transformations are clearly derived with edge cases handled
- Cross-validation against existing pipeline data is built into every zone
- The backfill approach is additive and non-destructive
- The data contract sets appropriate quality expectations

The six advisory items are all implementation-time concerns:
- Domain source YAML is standard boilerplate created during implementation
- The spec name is cosmetic — content is clear
- Testing approach is implied by DQ rules and staff engineer minimums
- Glossary term ID collision is a simple verification during implementation
- Backfill DQ re-run is standard practice
- The inverse invariant filter is conservative, not wrong

No CHANGES REQUESTED or REJECTED items were found. The spec meets all pre-implementation governance requirements.

**REQUIRE_HUMAN_APPROVAL is TRUE.** This review is the governance reviewer's recommendation. The human owner should review before implementation begins.

**Implementation ordering note:** The Bronze ingest can begin immediately. Silver and Gold implementation must wait for @semantic-modeler to produce the three-stage data models (conceptual, logical, physical) for both base.karpathy_ai_exposure and consumable.ai_exposure.

---

*Reviewed against: Brightsmith CLAUDE.md framework rules, futureproof-data CLAUDE.md project conventions, prior specs (raw-ingest-onet, raw-ingest-bls-ooh, crosswalk-cip-soc), and governance reviewer pre-implementation checklist.*
