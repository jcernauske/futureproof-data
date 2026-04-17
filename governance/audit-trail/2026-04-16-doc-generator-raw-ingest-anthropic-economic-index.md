# Audit Trail: @doc-generator — raw-ingest-anthropic-economic-index

**Agent:** @doc-generator
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Date:** 2026-04-16
**Status:** Complete

## Summary

Produced governance documentation for the Anthropic Economic Index ingest:
three data contracts (two new Bronze/Silver, one modified Gold with a minor
version bump), the new project-root `LICENSE_SOURCES.md` ledger, and data
dictionary entries for all 26 new/modified fields across Bronze, Silver,
and Gold.

## Artifacts Produced

### Data contracts (3)

| Action | Path | Notes |
|--------|------|-------|
| CREATE | `governance/data-contracts/raw-anthropic-economic-index.yaml` | Bronze. 12 columns (6 CDE, 0 PII). Includes `license:` block with CC-BY 4.0 + attribution + URL + `requires_citation: true`. |
| CREATE | `governance/data-contracts/base-anthropic-observed-exposure.yaml` | Silver. 10 columns (8 CDE, 0 PII). Inherits CC-BY 4.0 via source_release; license block notes derivative status. |
| MODIFY | `governance/data-contracts/consumable-ai-exposure.yaml` | Gold. Bumped 1.0.0 -> **1.1.0** (MINOR, additive). Added 4 new nullable columns. Existing columns untouched. Added `license.mixed_sources: true` block listing Karpathy/Gemma/Anthropic components separately. Added S4 and MCP-attribution-footer consumers. |

### Attribution ledger (1)

| Action | Path | Notes |
|--------|------|-------|
| CREATE | `/Users/jcernauske/code/bright/futureproof-data/LICENSE_SOURCES.md` | New project-root file. Consolidates all 7 external data sources (College Scorecard Field of Study, College Scorecard Institution, BLS OOH, O*NET, CIP-SOC Crosswalk, Karpathy, BEA RPP) plus new Anthropic Economic Index section. Adds a "Policy: Adding a New Source" section so future ingests have a procedural standard. |

### Data dictionary (3 changes to `governance/data-dictionary.json`)

| Action | Entry | Notes |
|--------|-------|-------|
| ADD | `raw.anthropic_economic_index` | 12 column entries. Plain-English definitions for task_id, task_statement, soc_code, soc_title, task_pct (incl. the fan-out-split explanation), automation_pct, augmentation_pct, source_release, ingested_at, source_url, source_method, load_date. |
| ADD | `base.anthropic_observed_exposure` | 10 column entries: record_id, soc_code, soc_title, observed_exposure_pct, automation_pct, augmentation_pct, task_count, soc_match, source_release, promoted_at. |
| MODIFY | `consumable.ai_exposure` | Updated description to reflect v1.1.0 Anthropic additive. Bumped `version` field to `1.1.0`. Added 4 new column entries: observed_exposure_pct, automation_pct, anthropic_task_count, anthropic_source_release. Existing column entries untouched. |

**Total new/modified fields: 26** (12 Bronze + 10 Silver + 4 Gold) — matches the CDE tagging summary.

## Decisions / Interpretation Calls

1. **Version bump to 1.1.0 (not 1.0.1 or 2.0.0).** Per the contract's own semver policy (see `breaking_changes.policy` on the existing v1.0.0 contract): "Column added triggers a minor bump (NON-BREAKING)." All four additions are nullable, no existing columns are modified, no grain change. MINOR is the correct ticker.

2. **`license.mixed_sources: true` on the Gold contract.** `consumable.ai_exposure` now blends Karpathy (MIT), the project-owned Gemma rescore, and Anthropic (CC-BY 4.0). Rather than attach a single `license:` block (which would imply one license governs the whole table — wrong), I used a `mixed_sources` structure that lists each component and which fields it covers. This lets downstream tooling (MCP attribution, published analyses) pick the right attribution string based on which field is being surfaced.

3. **`automation_pct` / `augmentation_pct` units are 0-100, not 0-1.** The CDE tagging document and the original spec both noted a units ambiguity. The as-built ingestor and the revised DQ rules (SLV-AOE-011, GLD-AIE-ANT-005, revised 2026-04-17) converged on 0-100 percent units, consistent with every other `_pct` field in the project and with `observed_exposure_pct`. I documented this convention in all three contracts and in the data dictionary.

4. **`anthropic_task_count` description flags NULL semantics explicitly.** When a SOC has no Anthropic coverage, all four additive Gold columns are NULL. The plain-English definition calls this out so a business user reading the data dictionary understands why ~39% of rows will have NULLs here.

5. **LICENSE_SOURCES.md includes a "Policy: Adding a New Source" section.** Not strictly required by the spec, but since this file did not exist before, I used the opportunity to set a procedural standard for future ingests — the file will be much more valuable as a living ledger if contributors know exactly what to do when adding a source.

6. **DQ rule references on each field.** I linked each column in the contracts and dictionary entries to its specific DQ rule IDs (e.g., `RAW-AEI-001`, `SLV-AOE-002`, `GLD-AIE-ANT-004`). This matches the pattern used on the BEA RPP contract and supports the governance completeness checklist.

## Conflicts / Conventions Reconciled

- **Spec Silver schema says `source_release: string`, but sibling Silver contracts use `varchar`.** I used `varchar` in the Silver contract to match the project convention (base.karpathy_ai_exposure, consumable.ai_exposure). No semantic difference in the target Iceberg type system.
- **Spec Gold schema adds `automation_pct` only (no `augmentation_pct`).** I preserved that spec decision at Gold. Silver still carries `augmentation_pct` explicitly per the spec and per CDE tagging guidance — if the future S4 spec extends Gold to add `augmentation_pct`, no additional tagging work is required.
- **`task_pct` units: Bronze spec says "percent units (0-100)"; no Silver rescaling.** Confirmed consistent across Bronze/Silver/Gold — all three zones use 0-100 percent units for observed_exposure_pct, automation_pct, augmentation_pct.
- **Gold contract `dq_rules` block already points at `governance/dq-rules/gold-ai-exposure.json`.** I added a sibling `additive_rule_files:` array pointing at `gold-ai-exposure-anthropic.json` to preserve the pre-existing sign-off on the base file.

## Quality Self-Check

- [x] All 3 YAML contracts parse cleanly (validated with `yaml.safe_load`).
- [x] `governance/data-dictionary.json` parses cleanly (validated with `json.load`).
- [x] Every new/modified field has a plain-English description aimed at a business analyst, with zero raw schema jargon.
- [x] Every CDE flag in the contracts matches the CDE tagging document (18 of 26 fields CDE).
- [x] No PII flags — consistent with `governance/pii/raw-anthropic-economic-index-pii-scan.md`.
- [x] CC-BY 4.0 license block present on Bronze with all four required fields (type, attribution, url, requires_citation).
- [x] LICENSE_SOURCES.md includes the exact spec-required Anthropic block plus 6 additional sources.
- [x] Gold version bumped 1.0.0 -> 1.1.0 with version history comment.
