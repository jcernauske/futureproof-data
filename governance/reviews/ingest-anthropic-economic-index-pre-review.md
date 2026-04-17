## Governance Review: ingest-anthropic-economic-index
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Verdict:** CHANGES REQUESTED

---

### Scope of This Review

This review evaluates the spec at `docs/specs/ingest-anthropic-economic-index.md` for readiness to enter the Bronze (Raw) ingestor implementation phase. The spec also describes Silver and Gold stages, but per the reviewer's instructions this run focuses on the Bronze gate. Silver/Gold sections are reviewed for internal consistency and traceability but are not gated here.

---

### Pre-Implementation Checklist Results

| Check | Status | Notes |
|---|---|---|
| Clear problem statement | PASS | Observed AI exposure signal needed for S4 three-signal composite. Purpose is well-defined. |
| Success criteria measurable | PARTIAL | Bullets are mostly binary (table lands, columns populated); two quantitative thresholds present (SOC join coverage >= 80%, row count 3000-5000). Missing: explicit row count target for Bronze table and explicit measurable coverage for task_pct non-null. |
| Input data sources identified with paths | PASS | HuggingFace `Anthropic/EconomicIndex`, primary release `release_2026_03_24/`, explicit fallback releases listed, clone script provided. |
| Output artifacts defined (paths + formats) | PASS | Iceberg table `raw.anthropic_economic_index`, file-level source CSVs enumerated, downstream tables named. |
| Transformations described | PASS (Bronze) / AMBIGUOUS (Silver) | Bronze is a straight CSV-join-on-task_id ingest. Silver aggregation formula is explicitly flagged as "Clarification needed" in the spec (sum vs mean for `task_pct`). Acceptable for Bronze gate but MUST be resolved before Silver. |
| Zone assignment correct | PASS | Bronze = raw per-task HuggingFace CSV data; Silver = SOC aggregation; Gold = merge into existing consumable.ai_exposure. Aligns with Brightsmith zone architecture. |
| Primary implementation agent identified | ADVISORY | Spec lists `@fp-data-reviewer` as Primary Agent, but the Agent Workflow section invokes `@data-analyst` for EDA and uses general implementation for the ingestor build. Primary Agent field should be the builder (general Claude Code) or `@primary-agent` per convention used by raw-ingest-karpathy-ai-exposure. This is organizational, not blocking. |
| DQ rule categories specified | PASS (Bronze) | 5 Bronze rules listed with P0/P1 severity. Silver (5 rules) and Gold (3 rules) also specified. Path `governance/dq-rules/raw-anthropic-economic-index.json` declared. |
| CDE mapping impact assessed | FAIL | No explicit CDE/PII assessment in the spec. While PII expectations are low (task IDs, SOC codes, aggregate percentages), the spec does not name @cde-tagger or call out which fields become CDEs. `task_id`, `soc_code`, and `task_pct` are candidate CDEs by analogy with `raw.karpathy_ai_exposure` (slug, soc_code, exposure_score are all is_cde=true). Required before data contract creation. |
| Lineage scope defined | FAIL | The spec does not mention OpenLineage events, @lineage-tracker invocation, or which transformations require lineage artifacts. Every comparable Bronze spec in this repo (raw-ingest-karpathy-ai-exposure, raw-ingest-college-scorecard, raw-bea-rpp) produced a `governance/lineage/` entry. Must be added to the workflow. |
| Breaking changes flagged | PARTIAL | Spec notes that `consumable.ai_exposure` gains new columns via schema evolution. It does NOT flag that this is a schema-additive change requiring a contract version bump on `governance/data-contracts/consumable-ai-exposure.yaml`, nor does it specify whether the existing MCP contract `mcp-ai-exposure.yaml` needs bumping. Must be stated. |
| Testing approach defined | FAIL | No test plan. No pytest file paths, no fixture strategy, no chaos-manifest mention. Peer spec raw-ingest-karpathy-ai-exposure specifies test locations and chaos monkey engagement. Required addition. |

---

### Data Model Gate (Bronze zone)

Per governance rules: **Bronze zone specs skip the 3-stage model gate** — raw tables use physical-only models (data lands as-is). The HuggingFace CSV files land 1:1 with a join on `task_id`. No conceptual/logical/physical trio required for Bronze. This gate is **N/A** for this review.

Note: when this spec advances to Silver (`base.anthropic_observed_exposure`), the 3-stage gate WILL apply. The spec currently does not acknowledge this. A sub-spec or follow-on stage should invoke @semantic-modeler before Silver implementation.

---

### Source, License, and Provenance

| Check | Status | Notes |
|---|---|---|
| Source citation present | PASS | HuggingFace `Anthropic/EconomicIndex` with specific release folder. |
| License identified | PASS | CC-BY declared in spec header and reviewer context. |
| Attribution obligation documented | FAIL | CC-BY requires visible attribution of the source dataset wherever the derived data is published (MCP outputs, user-facing copy, data contracts). The spec does not describe: (a) where attribution text will live, (b) whether a `source_attribution` or `license` column will be carried in the Bronze table, (c) whether the data contract will include a `license` and `attribution` field. The Karpathy precedent in this repo does NOT cleanly solve this either — Karpathy is not under CC-BY. This is the first CC-BY source in the pipeline; set the precedent explicitly. |
| Provenance fields on Bronze schema | PASS | `source_release`, `ingested_at`, `load_date` are on the schema. Recommend also adding `source_url` (the HuggingFace dataset URL) and `license` (literal "CC-BY") as carried fields for audit traceability, matching the Karpathy pattern. |
| Release version tracking | PASS | `source_release` field is on the schema and called out in success criteria. Fallback releases are listed. |
| PII expectations | PASS | No PII expected (O*NET task IDs, SOC codes, aggregate Claude usage percentages). Spec does not explicitly state this — recommend a one-line "No PII" declaration for the @pii-scanner handoff. |

---

### Bronze Build Readiness Checks

These are the specific items an ingestor author needs to start coding:

| Question | Answer in spec? | Notes |
|---|---|---|
| What is the grain? | YES | "One row per O*NET task" |
| What is the dedup grain? | YES | `[task_id]` |
| Expected row count range? | YES | ~3,500 tasks; DQ rule bounds 3000-5000 |
| What source files are read? | YES | 3 CSVs named: `onet_task_mappings.csv`, `task_pct_v2.csv`, `automation_vs_augmentation_by_task.csv` |
| Exact source column names? | NO | Spec says "columns: `task_id`, `soc_code`, `task_statement`, etc." but "etc." is load-bearing here. Actual HuggingFace CSV headers have not been verified. EDA step in workflow will resolve, but the spec should make clear the ingestor must NOT be hand-authored with guessed columns — it must be written AFTER EDA. |
| Ingestor class name and file location? | YES | `AnthropicEconomicIndexIngestor` at `src/raw/anthropic_economic_index_ingestor.py` |
| BaseIngestor extension? | YES | Declared. |
| Fallback behavior if primary release missing? | YES | Fall back to `release_2026_01_15` or `release_2025_03_27`. |
| Fallback behavior if HuggingFace unreachable? | NO | No local cache strategy (unlike Karpathy's `data/raw/karpathy_cache/`). git clone can fail behind corporate networks; git-lfs can fail silently when quota is exceeded. Spec should state: (a) whether we commit a snapshot to a local cache, (b) how an offline run is supposed to succeed for tests. |
| Join logic between the 3 CSVs? | YES | Join on `task_id`. Output one row per task. |
| Null handling for soc_code? | PARTIAL | Schema marks `soc_code` as `required: no`. DQ rule sets ">= 90% non-null coverage". Good. Does not specify what "broad vs detailed" SOC code handling does in Bronze — the spec defers this to Silver (acceptable). |

---

### Cross-Spec Consistency

| Check | Status | Notes |
|---|---|---|
| S4 `three-signal-ai-exposure-composite` references this spec | PASS | The blocking spec exists; it references an Anthropic observed exposure signal. This Bronze spec is the unblocker. |
| Naming consistency with Silver/Gold | ADVISORY | Bronze table: `raw.anthropic_economic_index`. Silver: `base.anthropic_observed_exposure`. The Silver name drops "economic_index" and adds "observed_exposure". Both names are reasonable but they diverge — downstream engineers will grep for "anthropic" and find two different conventions. Either acceptable; note for post-review consistency. |
| Contract naming matches file layout | PASS | `governance/data-contracts/base-anthropic-observed-exposure.yaml` and `consumable-ai-exposure.yaml` referenced in File Changes. Consistent with existing contract filename patterns. |
| No Bronze contract listed | FAIL | The File Changes table lists contracts for Silver (new) and Gold (modified) but does NOT list a Bronze contract `governance/data-contracts/raw-anthropic-economic-index.yaml`. Every prior Bronze spec in this repo produced a raw contract (see `raw-karpathy-ai-exposure.yaml`, `raw-bea-rpp.yaml`, `raw-college-scorecard.yaml`). This is a governance gap. |

---

### Issues Found

| # | Severity | Description | Resolution Required |
|---|---|---|---|
| 1 | CHANGES REQUESTED | No Bronze data contract listed in File Changes. | Add `governance/data-contracts/raw-anthropic-economic-index.yaml` to File Changes and to the workflow (@cde-tagger produces). |
| 2 | CHANGES REQUESTED | No CDE/PII tagging step in Agent Workflow. | Add a step invoking @cde-tagger to flag `task_id`, `soc_code`, `task_pct`, `automation_pct` as CDEs. Add explicit "No PII" declaration for @pii-scanner. |
| 3 | CHANGES REQUESTED | No lineage step in Agent Workflow. | Add a step invoking @lineage-tracker to emit OpenLineage events for the Bronze ingest (inputs: 3 CSVs; output: raw.anthropic_economic_index). |
| 4 | CHANGES REQUESTED | CC-BY attribution obligation not addressed in artifacts. | Decide and document: (a) carry a `license` literal field in Bronze schema, (b) populate `license` and `attribution` in the data contract YAML, (c) document where end-user attribution appears when this data flows to MCP outputs. This is the first CC-BY source — set the precedent. |
| 5 | CHANGES REQUESTED | No offline/cached fallback strategy. | Either declare "HuggingFace must be reachable" with a skip-on-offline test marker, or specify a local cache path analogous to `data/raw/karpathy_cache/`. The ingestor must not silently produce an empty Iceberg table when `git lfs pull` fails. |
| 6 | CHANGES REQUESTED | Testing approach not defined. | Add a §Testing or "Tests Required" subsection: list pytest file paths (e.g., `tests/raw/test_anthropic_economic_index_ingestor.py`), fixture strategy (sample CSVs under `tests/fixtures/`), and chaos manifest expectations. |
| 7 | ADVISORY | Silver aggregation formula is explicitly marked "Clarification needed". | Acceptable for Bronze gate — the EDA step in the workflow is specifically designed to resolve this. But downstream Silver pre-implementation review WILL block until the sum-vs-mean question is resolved with data evidence in §EDA Results. |
| 8 | ADVISORY | Primary Agent is `@fp-data-reviewer` but that agent's role in this repo is pipeline-quality review, not implementation. | Change to `@primary-agent` or general Claude Code for the implementation phase, matching the raw-ingest-karpathy-ai-exposure convention. Organizational only. |
| 9 | ADVISORY | Breaking change impact on `consumable-ai-exposure.yaml` not called out. | Add a note that schema evolution on `consumable.ai_exposure` requires a contract version bump and that downstream MCP contract `mcp-ai-exposure.yaml` must be re-verified. |
| 10 | ADVISORY | Silver/Gold 3-stage data model gate not mentioned. | When Silver stage enters its own pre-implementation review, @semantic-modeler MUST produce conceptual, logical, and physical models for `base.anthropic_observed_exposure`. Add a forward reference so future-you remembers. |
| 11 | ADVISORY | Naming divergence between `anthropic_economic_index` (Bronze) and `anthropic_observed_exposure` (Silver). | Both are fine. Document the rationale in the spec so downstream engineers don't assume a typo. |

---

### Decision Rationale

The spec is **implementable-in-principle** — the source, grain, schema, and join logic are clear enough that a Bronze ingestor can be built after EDA confirms actual CSV column names. The Silver and Gold stages have a clearly-flagged ambiguity (aggregation formula) but that ambiguity is explicitly punted to the EDA step, which is a legitimate pattern in Brightsmith.

However, the spec is **missing six governance artifacts** that every prior Bronze spec in this project has produced:

1. A Bronze data contract entry
2. A CDE/PII tagging workflow step
3. A lineage tracking workflow step
4. CC-BY attribution handling (first-of-its-kind for this repo)
5. An offline/cache fallback strategy
6. A testing plan

Missing any one of these would be a CHANGES REQUESTED. Missing all six is a pattern of the spec being written from a data-engineering perspective only, with the governance scaffolding elided. None are fundamental design problems — all are additive updates to the spec text. There is no reason to REJECT.

**Verdict: CHANGES REQUESTED.** Resolve items 1-6 in the spec before implementation begins. Items 7-11 are advisory and can be addressed in-flight or deferred to Silver review.

---

### Re-Review Path

Once the spec author updates §File Changes, §Agent Workflow, §Success Criteria (attribution and offline), and adds a §Testing and §Governance section, ping @governance-reviewer for a delta re-review. Expected turnaround: single pass since no design changes are required.

---

*— End of Review —*
