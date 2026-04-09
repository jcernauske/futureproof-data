# Governance Review: raw-ingest-onet (Pre-Implementation)

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-07
**Verdict:** APPROVED (with ADVISORY notes for human awareness)

## Pre-Implementation Checklist

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement is thorough — explains why 7 of 40 files were chosen, maps each to FutureProof features. 9 success criteria are specific and measurable. |
| 2 | Input data sources identified with paths | PASS | Source URL, format (tab-delimited ZIP), version (O*NET 30.2), license (CC BY 4.0), fallback path, and access method all documented. |
| 3 | Output artifacts defined with paths and formats | PASS | All 7 Iceberg tables named with `raw.*` prefix. 9 governance artifacts listed with full paths. |
| 4 | Transformations described (what changes, why) | PASS | Bronze zone — no transformations. Spec explicitly states data lands as-is. SOC codes preserved in XX-XXXX.XX format, suppress/relevance flags preserved. |
| 5 | Zone assignment correct (Raw/Bronze) | PASS | Correct. Raw ingestion of external data, no business logic applied. Multi-table pattern is new but zone-appropriate. |
| 6 | Primary implementation agent identified | PASS | @primary-agent listed as implementor. Full 12-step agent workflow defined. |
| 7 | DQ rule categories specified or acknowledged | PASS | Detailed per-table DQ focus areas covering: format validation, null rates, referential integrity, value ranges, distribution checks, self-reference detection, and row-count-to-index consistency. Thorough for a spec that defers actual rule writing to @dq-rule-writer. |
| 8 | CDE mapping impact assessed | PASS | @cde-tagger is step 9 in the workflow. O*NET-SOC code is an obvious CDE candidate. The spec does not pre-declare CDEs, which is correct — @cde-tagger discovers these. |
| 9 | Lineage scope defined | PASS | 7 lineage events (one per table). Spec notes that BaseIngestor auto-emits runtime lineage, consistent with bronze pipeline docs. |
| 10 | Breaking changes to existing schemas flagged | PASS | All 7 tables are new — no breaking changes to existing schemas. |
| 11 | Testing approach defined | PASS (implicit) | Not explicitly called out as a section, but success criteria reference DQ rules, EDA report, and dedup verification. Staff engineer minimum of 10 tests for Raw zone applies. See ADVISORY #3. |

### Data Model Gate

**SKIPPED** — Bronze zone specs use physical-only models. The 7 table schemas defined in the spec serve as the physical model. No conceptual/logical modeling required. This is correct per the Brightsmith framework ("Bronze zone specs skip this gate").

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | **Missing domain source YAML** — No `domain/sources/onet.yaml` exists yet. Both College Scorecard and BLS OOH had their source YAML files created alongside or before their specs. The @primary-agent should create this as part of implementation, and it should be registered in `domain/manifest.yaml`. | @primary-agent should create `domain/sources/onet.yaml` during implementation and add O*NET to `domain/manifest.yaml` sources list. Not blocking — this is implementation work, not spec work. |
| 2 | ADVISORY | **Multi-table ingestor pattern is an open decision** — The spec explicitly flags this as needing human input (Open Decision #1). Brightsmith's BaseIngestor is one-ingestor-per-table. The spec offers two options: (a) single class with per-file dispatch, or (b) 7 thin subclasses sharing a common parent. Either is acceptable architecturally. The @primary-agent and @staff-engineer will resolve this during implementation. | Human should indicate preference before implementation begins, or delegate to @primary-agent's judgment. |
| 3 | ADVISORY | **No explicit "Testing Approach" section** — The prior BLS OOH spec also omitted this, so this is consistent with project convention. However, the Brightsmith framework mandates a minimum of 10 tests for Raw zone specs, and the staff engineer will enforce this. The spec's success criteria implicitly cover the testing surface (schema validation, dedup, format preservation, metadata fields, DQ rule execution). | @primary-agent should plan for 10+ unit/integration tests. Not blocking at pre-implementation. |
| 4 | ADVISORY | **Work Context "category" column documentation** — The spec correctly notes Work Context has an extra `Category` column that Work Activities does not (line 215, table 4 schema). The `category` field is typed as `int` and marked optional. Worth confirming during EDA that this field is indeed integer-typed in the source data (some O*NET categorical fields use string labels). | @data-analyst should verify category field type during EDA. |
| 5 | ADVISORY | **Chaos monkey included in workflow** — The agent workflow (step 7) includes @chaos-monkey with 5-cycle adversarial hardening. The prior BLS OOH spec's workflow did not include this step, but the bronze pipeline workflow document does list it. The spec is being more thorough than precedent, which is good. Just noting for awareness that this adds implementation time. | No action needed. |

## Spec Quality Assessment

### Strengths

1. **Excellent problem-to-feature mapping.** The "What O*NET Feeds in FutureProof" table (lines 16-27) directly connects each file to specific product features (stats, boss fights, branching). This is the best feature-justification table in any spec in the project so far.

2. **Tiered prioritization.** Splitting the 7 files into Tier 1 (stats/bosses) and Tier 2 (branching) makes implementation priority clear and provides a natural fallback if time is constrained.

3. **Thorough schema definitions.** All 7 tables have complete schemas with types, required flags, and explanatory notes. The Work Context schema correctly includes the `category` column that distinguishes it from the otherwise-identical Work Activities structure.

4. **Clear grain definitions.** Every table has its grain explicitly stated: single-key (onet_soc_code), composite two-key (onet_soc_code x task_id, onet_soc_code x related_onet_soc_code), and composite three-key (onet_soc_code x element_id x scale_id). This is critical for dedup and DQ validation.

5. **SOC code format alignment documented.** The "Cross-Source Integration Notes" section (lines 306-317) thoroughly addresses the O*NET XX-XXXX.XX vs BLS XX-XXXX format difference, explains the .XX suffix semantics, and correctly defers normalization to Silver zone. This is exactly the level of cross-source awareness needed.

6. **Expected row counts with tolerances.** Row count estimates per table with notes on variability (career matrices: ~7,000-9,000). The open decision on tolerance bands (5% vs 15%) is appropriately flagged for human input.

7. **DQ rules are comprehensive for pre-EDA.** Referential integrity checks (all SOC codes exist in occupations table), value range checks (IM 1-5, LV 0-7), self-reference detection (source != related in career matrices), and distribution checks (recommend_suppress mostly "N") — these go well beyond the typical pre-EDA stub.

### Minor Observations

- The `date` field in task_statements, work_activities, and work_context is typed as `string` rather than `date`. This is correct for Bronze zone — the raw value should land as-is, and Silver can parse it. No issue here.
- The `is_primary` boolean on related_occupations is a derived field (inferred from index position). This is a minor transformation in Bronze, but it is deterministic and schema-preserving. Acceptable.

## Cross-Reference Verification

| Check | Result |
|-------|--------|
| Spec references correct zone (Raw/Bronze) | PASS |
| Pipeline state file exists (`governance/pipeline-state/raw-ingest-onet-pipeline.json`) | PASS |
| Pipeline state shows governance-reviewer-pre as NOT_STARTED | PASS |
| Agent workflow matches bronze pipeline template | PASS (includes chaos-monkey, which is in the template) |
| Governance artifact paths follow project convention | PASS |
| No conflicts with existing tables | PASS (all 7 table names are new) |
| SOC code format documented and deferred to Silver | PASS |

## Decision Rationale

This spec is **approved for implementation**. It is the most thorough raw ingest spec in the project to date, covering 7 tables with complete schemas, grain definitions, DQ focus areas, cross-source integration notes, and a well-prioritized feature mapping.

The five advisory items are all implementation-time concerns, not spec-blocking gaps:
- The missing domain source YAML is standard implementation work
- The multi-table ingestor pattern is an explicitly flagged open decision (appropriate to resolve during implementation)
- The testing approach is implied by success criteria and framework minimums
- The category column type is a minor EDA verification item
- The chaos monkey inclusion is a positive addition to quality

No CHANGES REQUESTED or REJECTED items were found. The spec meets all pre-implementation governance requirements for a Bronze zone ingest.

**REQUIRE_HUMAN_APPROVAL is TRUE.** This review is the governance reviewer's recommendation. The human owner should review the three Open Decisions (multi-table pattern, EDA format, row count tolerances) before or during implementation.

---

*Reviewed against: Brightsmith bronze-pipeline.md workflow, futureproof-data CLAUDE.md, prior specs (raw-ingest-college-scorecard, raw-ingest-bls-ooh), and governance reviewer pre-implementation checklist.*
