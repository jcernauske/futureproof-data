# CDE/PII Tagging Report: raw-ingest-anthropic-economic-index

**Date:** 2026-04-16
**Agent:** @cde-tagger
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Primary tagging doc:** `governance/cde-tagging/raw-anthropic-economic-index.md`
**Registry entry:** `governance/cde-registry/raw-anthropic-economic-index-cdes.md`
**PII scan:** `governance/pii/raw-anthropic-economic-index-pii-scan.md` (verdict: CLEAN — zero PII across 31,734 rows / 6 source CSVs)
**Contracts target:**
- `governance/data-contracts/raw-anthropic-economic-index.yaml` (CREATE, Bronze) — @doc-generator
- `governance/data-contracts/base-anthropic-observed-exposure.yaml` (CREATE, Silver) — @doc-generator
- `governance/data-contracts/consumable-ai-exposure.yaml` (UPDATE, Gold additive, v1.0.0 -> v1.1.0 MINOR) — @doc-generator

## Domain Context Referenced

- `governance/domain-context.md` §1627–1840 "Anthropic Economic Index" — empirical counterpart to Karpathy theoretical scoring; Canonical Concept Map names `observed_exposure_pct`, `automation_pct`, `augmentation_pct`, `soc_code`, `source_release` as CORE priority; zero-PII posture declared.
- `governance/pii/raw-anthropic-economic-index-pii-scan.md` — CLEAN; all fields Level 1 (Public) or Level 2 (Internal — pipeline metadata). No RLS, masking, encryption-beyond-baseline.
- `governance/eda/raw-anthropic-economic-index-eda.md` — 4,082 Bronze rows; 510/832 target SOC coverage (61.3%); sum-of-global-shares aggregation strategy confirmed.
- `docs/specs/three-signal-ai-exposure-composite.md` — downstream consumer; blends Karpathy × Anthropic `observed_exposure_pct` × velocity into `stat_res_composite` + `boss_ai_score_composite`.
- **Applicable regulations:** None mandatory. EEOC advisory only. CC-BY 4.0 licensing requirement drives `anthropic_source_release` CDE status.

## Columns Flagged as CDE (18 total across 3 zones)

### Bronze — `raw.anthropic_economic_index` (6 of 12)

| Column | Rationale |
|--------|-----------|
| `task_id` | Part of composite dedup grain [task_id, soc_code]. O*NET external standard. Stable provenance key. |
| `soc_code` | Governed project-wide CDE (BT-027). Composite dedup grain. FK to base.bls_ooh. |
| `task_pct` | Per-(task, SOC) global share, P0 SUM~100 invariant. Single highest-criticality business column — directly aggregated to Silver observed_exposure_pct feeding S4 composite. |
| `automation_pct` | Anthropic v2: (directive + feedback_loop) * 100. MCP triple input. P1 invariant with augmentation. |
| `augmentation_pct` | Anthropic v2: (task_iteration + validation + learning) * 100. Co-equal to automation_pct per v2 methodology. |
| `source_release` | CC-BY 4.0 license-critical attribution + reproducibility provenance. |

### Silver — `base.anthropic_observed_exposure` (8 of 10)

| Column | Rationale |
|--------|-----------|
| `record_id` | Deterministic grain hash (aoe:*). Dedup grain. |
| `soc_code` | Primary key + sole JOIN key to consumable.ai_exposure. |
| `observed_exposure_pct` | The new empirical signal. SUM(task_pct) per SOC. S4 composite input. MCP response. |
| `automation_pct` | SOC-level volume-weighted mean; MCP triple; Gold promotion. |
| `augmentation_pct` | SOC-level volume-weighted mean; MCP triple. |
| `task_count` | Aggregation confidence signal (range 1-141; median 4). Low-evidence badge input. |
| `soc_match` | Gate flag for Gold promotion; threshold re-baselined 80%->60% per EDA. |
| `source_release` | Aliased to anthropic_source_release in Gold; carries attribution. |

### Gold — `consumable.ai_exposure` additive (4 of 4)

| Column | Rationale |
|--------|-----------|
| `observed_exposure_pct` | S4 three-signal composite empirical input; MCP triple; Fight AI boss detail panel. Single most consequential Gold additive from this spec. |
| `automation_pct` | MCP triple; "AI is doing the work" narrative in Fight AI detail. |
| `anthropic_task_count` | S4 confidence weighting; "based on N observed tasks" MCP phrase. |
| `anthropic_source_release` | CC-BY 4.0 attribution — surfaced in MCP footer and S4 composite provenance. |

## Columns Flagged as PII

**None.** PII scan verdict CLEAN. All 26 fields tagged in this spec classify as Level 1 (Public) or Level 2 (Internal — pipeline metadata). Anthropic's `filtered` axis removes privacy-sensitive conversations upstream; the release is what's left after that review.

| Column | Table | Rationale |
|--------|-------|-----------|
| (none) | | — |

## Columns Evaluated — Not Flagged

### Bronze (6 of 12)

| Column | Reason Not Critical |
|--------|---------------------|
| `task_statement` | Free-text O*NET task description — descriptive/display only. Stable key is task_id. |
| `soc_title` | Display label; soc_code is authoritative. Matches `consumable.ai_exposure.occupation_title` pattern. |
| `ingested_at` | Bronze batch timestamp. Non-CDE on every sibling Bronze contract. |
| `source_url` | HuggingFace URL; public unauthenticated endpoint. |
| `source_method` | Literal 'hf_git_clone'. Operational provenance only. |
| `load_date` | Date of load. Operational freshness metadata. |

### Silver (2 of 10)

| Column | Reason Not Critical |
|--------|---------------------|
| `soc_title` | Display label. |
| `promoted_at` | Silver promotion timestamp. Pipeline metadata. |

### Gold additive

All 4 new additive columns are CDE. Existing Gold columns (v1.0.0) are not re-evaluated by this spec per no-propagation rule.

## Non-Obvious Decisions

1. **`augmentation_pct` flagged CDE in Bronze + Silver despite no matching Gold column.** Co-equal to automation under v2 methodology; P1 invariant binds them; hedges against S4 Gold-schema extension.
2. **`task_count` / `anthropic_task_count` flagged CDE.** Product-visible confidence signal per domain-context (low-evidence badge use case), not internal metadata.
3. **`source_release` / `anthropic_source_release` flagged CDE at every zone.** CC-BY 4.0 attribution surface. Matches BEA RPP `data_year` precedent.
4. **`task_statement` NOT flagged CDE.** Descriptive/display only; stable key is task_id; MCP should source task text from `consumable.occupation_profiles` instead.
5. **`soc_match` flagged CDE (Silver).** Not a metric but a gate flag whose threshold was explicitly re-baselined during EDA (80%->60%) — governance control boundary.

## Summary Stats

| Metric | Value |
|--------|-------|
| Zones evaluated | 3 (Bronze + Silver + Gold additive) |
| Total columns tagged | 26 |
| Columns flagged CDE | **18** |
| Columns flagged PII | **0** |
| Columns not flagged | 8 (6 Bronze metadata/display + 2 Silver metadata/display) |
| Regulatory frameworks triggered | None (CC-BY 4.0 licensing; EEOC advisory only) |
| Sensitivity classification | Level 1 / Level 2 across all 26 fields |
| CDE density — Bronze | 50.0% (6/12) — typical for business-signal ingests |
| CDE density — Silver | 80.0% (8/10) — narrow schema, every non-metadata column is a formula input |
| CDE density — Gold additive | 100.0% (4/4) — every additive column serves a named consumer surface |

## Downstream Reminder

CDE flags do not propagate. When S4 (`three-signal-ai-exposure-composite.md`) lands and replaces the single-source RES stat with the three-signal composite, @cde-tagger will re-run on the updated `consumable.ai_exposure` (or `consumable.ai_exposure_composite`) and re-evaluate `stat_res`/`boss_ai_score` against the composite formula inputs (which now include the Anthropic fields from this spec as co-inputs).
