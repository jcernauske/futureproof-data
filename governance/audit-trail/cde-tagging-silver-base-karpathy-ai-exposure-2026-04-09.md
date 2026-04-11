# CDE/PII Tagging Audit: silver-base-karpathy-ai-exposure
**Date:** 2026-04-09
**Agent:** @cde-tagger
**Spec:** raw-ingest-karpathy-ai-exposure (Silver zone section)
**Table:** base.karpathy_ai_exposure
**Contract:** governance/data-contracts/silver-base-karpathy-ai-exposure.yaml

## Domain Context Referenced

- governance/domain-context.md -- Karpathy AI Exposure section (added 2026-04-09)
- PII Assessment: No PII. Entirely occupation-level aggregate data from public BLS sources scored by an LLM.
- Regulatory context: No specific regulatory mandate (unlike BCBS 239 for financial data). CDEs identified based on downstream business criticality to the FutureProof career guidance product -- specifically the RES stat (AI Resilience) and Fight AI boss in the pentagon/gauntlet model.
- Karpathy data is LLM-generated estimates, not empirical measurements. Quality tier: Medium.

## Columns Flagged as CDE

| Column | Rationale |
|--------|-----------|
| record_id | Deterministic grain hash required for idempotent pipeline re-runs and lineage tracing. Stable row identifier for Gold zone promotion. |
| soc_code | Primary cross-source join key. Grain of the table. Bridges Karpathy data to BLS OOH, O*NET, and College Scorecard via CIP-SOC crosswalk. Without it, exposure scores cannot populate stat_res or boss_ai_score. |
| exposure_score | Primary analytical payload. Directly derives stat_res (MIN(11 - score, 10)) and boss_ai_score (MAX(score, 1)) in Gold. Completes the fifth stat in the FutureProof pentagon. |
| rationale | Display field for MCP and Fight AI boss narrative. Domain context identifies this as "the single most valuable field for LLM-to-user communication." Without it, scores lack interpretability. |
| bls_match | Data quality gate -- Gold filters on bls_match = true. A systematic error would produce an empty Gold table, breaking the entire RES stat pipeline. DQ P0 gate requires >= 90% true rate. |
| soc_resolved_method | Provenance field documenting SOC resolution strategy. Distribution is itself a DQ metric. Downstream consumers may weight confidence based on resolution method. |

## Columns Flagged as PII

None. Domain context confirms no PII in this dataset. All fields are occupation-level aggregates from public BLS sources scored by an LLM. No individual-level data exists.

## Columns Evaluated -- Not Flagged

| Column | Reason Not Critical |
|--------|---------------------|
| slug | Provenance field retained from Bronze. Not a join key at Silver -- soc_code has taken over. Not consumed by downstream business processes. |
| occupation_title | Display label only at Silver. soc_code is the authoritative join key. Not critical for analytical or regulatory purposes at this zone. |
| category | Project-specific taxonomy (not standard BLS). Display grouping only. Not a join key, analytical input, or decision driver. |
| source_load_date | Pipeline metadata. Not consumed by business processes or analytical outputs. |
| ingested_at | Pipeline metadata. Not consumed by business processes or analytical outputs. |

## CDE Count

- Total columns: 11
- Flagged as CDE: 6
- Flagged as PII: 0
- Not flagged: 5

## No Backward Propagation Note

CDE flags on this Silver table are independent of the Bronze (raw.karpathy_ai_exposure) contract. The Bronze contract flags slug and occupation_title as CDEs because they serve different roles at that zone (slug is the grain, occupation_title is the fallback SOC resolution key). At Silver, soc_code has replaced both of those roles.
