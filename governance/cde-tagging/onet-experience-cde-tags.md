# CDE/PII Tagging Report: onet-experience-requirements

**Date:** 2026-04-16
**Agent:** bs:cde-tagger
**Spec:** `docs/specs/onet-experience-requirements.md` (§CDE & PII Assessment, lines 411-440)
**PII scan:** `governance/pii-scans/onet-experience-pii-scan.md` (verdict: NO PII DETECTED, all 17 Raw columns Level 1 Public)

## Summary

Applied explicit `is_cde` / `is_pii` tags on every physical column of the three data contracts associated with this spec, following the authoritative disposition table in §CDE & PII Assessment. No PII was found anywhere in any zone; all `is_pii` flags are `false` across all 32 columns tagged. CDE flags were applied at P0 (business-critical) severity for 3 Raw columns, 3 Silver columns, and all 4 new Gold columns — matching the spec table exactly.

## Contracts Modified / Created

| Contract | Path | Action | Schema Version |
|----------|------|--------|----------------|
| `raw.onet_experience` | `governance/data-contracts/raw-onet-experience.yaml` | CREATED | N/A (Bronze — no version tracking) |
| `base.onet_experience_profiles` | `governance/data-contracts/base-onet-experience-profiles.yaml` | CREATED | 1.0.0 (new) |
| `consumable.career_branches` | `governance/data-contracts/consumable-career-branches.yaml` | UPDATED (4 new fields, additive) | 1.1.0 -> 1.2.0 |

## Columns Flagged as CDE

### Raw — `raw.onet_experience` (3 of 17 fields CDE-tagged)

| Column | Rationale |
|--------|-----------|
| `onet_soc_code` | Grain key; FK to `raw.onet_occupations`; cross-source bridge to BLS SOC via 6-digit truncation. Feeds Silver aggregation to `base.onet_experience_profiles` and Gold join onto `consumable.career_branches`. |
| `element_id` | Silver filter key. Transformation selects `element_id = '3.A.1'` (Related Work Experience) before weighted-median computation. An incorrect value drops rows from the filter and deflates coverage. |
| `scale_id` | Silver filter key. Transformation selects `scale_id = 'RW'` before weighted-median computation. Controlled vocabulary enforced by DQ rule `scale_id IN ('RL','RW','PT','OJ')`. |

### Silver — `base.onet_experience_profiles` (3 of 11 fields CDE-tagged)

| Column | Severity | Rationale |
|--------|----------|-----------|
| `bls_soc_code` | P0 | Natural key; primary join key to Gold `career_branches` (joined twice — for source and related SOC). Every experience-gated branch rendering depends on this join. |
| `experience_years_typical` | P0 | Primary experience metric. Feeds `related_experience_years`, `source_experience_years`, the NULL-propagating `experience_delta_years`, and the MCP / `career_tree.py` experience filter. |
| `experience_tier` | P0 | Cross-boundary classifier driving career-tree gating UX, decade bucketing ('Your 20s' / 'Your 30s' / 'Your 40s'), and 'Unlocks at 8+ years' badges. Thresholds human-approved 2026-04-16. |

### Gold — `consumable.career_branches` (4 of 4 new fields CDE-tagged)

| Column | Severity | Rationale |
|--------|----------|-----------|
| `related_experience_years` | P0 | Shown directly to users; feeds default-view filter on the branching career tree. |
| `related_experience_tier` | P0 | Drives UX gating + decade bucketing. |
| `source_experience_years` | P0 | Required input to NULL-propagating `experience_delta_years` derivation; anchors user's current career stage. |
| `experience_delta_years` | P0 | Primary default-view threshold (branch visible iff delta <= 5 years). Single most consequential gate on what appears by default in the career-tree UI. |

## Columns Flagged as PII

**None.** PII risk formally declared NONE in spec §CDE & PII Assessment and independently confirmed by `bs:pii-scanner` — see `governance/pii-scans/onet-experience-pii-scan.md`. O*NET ETE publishes exclusively occupation-level aggregate statistics under CC BY 4.0; no respondent-level microdata exists anywhere in this pipeline.

| Column | Table | Rationale |
|--------|-------|-----------|
| _(none)_ | _(none)_ | All 32 tagged fields classified `is_pii: false`. |

## Columns Evaluated — Not Flagged CDE

### Raw — `raw.onet_experience` (14 of 17 not CDE)

| Column | Reason Not Critical |
|--------|---------------------|
| `element_name` | Display label; `element_id` is the computational key. |
| `category` | Dimensional input to weighted-median; CDE-ness flows through filters + data_value weights, not this dimensional axis. |
| `data_value` | Percent-frequency weight input; structural, mediated by Silver aggregate. |
| `n` | Survey sample size — DQ indicator, not analytical. |
| `standard_error`, `lower_ci_bound`, `upper_ci_bound` | Statistical metadata on the aggregate. |
| `recommend_suppress` | DQ/provenance flag; preserved as Silver `suppress_flag`. |
| `date`, `domain_source` | Provenance classifiers. |
| `ingested_at`, `source_url`, `source_method`, `load_date` | Pipeline metadata. |

### Silver — `base.onet_experience_profiles` (8 of 11 not CDE)

| Column | Reason Not Critical |
|--------|---------------------|
| `record_id` | Technical surrogate key; not consumed by business processes. |
| `experience_category_median` | Internal derivation feeding `experience_years_typical`. |
| `experience_category_mode` | Internal diagnostic (highest-percent category). |
| `experience_distribution` | Optional downstream diagnostic; full RW distribution as JSON. |
| `onet_details_averaged` | Provenance count for multi-detail aggregation audit. |
| `suppress_flag` | DQ marker; excludes from spot-check pass/fail evaluation. |
| `source_load_date`, `ingested_at` | Pipeline metadata. |

### Gold — `consumable.career_branches` (no existing columns re-evaluated)

Per spec §Data Contract Update: "Do not modify existing fields." Existing `consumable.career_branches` CDE flags (from contract v1.1.0) are preserved unchanged. Only the 4 new experience fields were evaluated for this spec.

## Field Counts

| Zone | Contract | Fields Tagged | CDE-Tagged | PII-Tagged |
|------|----------|---------------|------------|------------|
| Bronze (Raw) | `raw-onet-experience.yaml` | 17 | **3** | 0 |
| Silver (Base) | `base-onet-experience-profiles.yaml` | 11 | **3** | 0 |
| Gold (Consumable) | `consumable-career-branches.yaml` (additions) | 4 | **4** | 0 |
| **Total new tags** | | **32** | **10** | **0** |

## Schema Version Bump

`consumable.career_branches` contract bumped from **1.1.0 -> 1.2.0** per spec §Data Contract Update:
- Change type: MINOR (additive only)
- 4 new columns, all nullable (`required: false`)
- No existing columns modified, renamed, or type-changed
- No breaking changes
- `version_history` entry appended to the contract documenting the 2026-04-16 bump

## Spec Citation

Authoritative disposition table: `docs/specs/onet-experience-requirements.md` §CDE & PII Assessment (lines 411-440), which mandates:

> `bs:cde-tagger` must apply these flags to `governance/data-contracts/base-onet-experience-profiles.yaml` and to the addendum in `governance/data-contracts/consumable-career-branches.yaml`.

Per-row fidelity verified: every row in the spec's 3-block disposition table (6 Raw dispositions, 8 Silver dispositions, 4 Gold additive dispositions) is materialized exactly as written onto the corresponding YAML column entry. The 3 Raw CDE flags (`onet_soc_code`, `element_id`, `scale_id`) and 3 Silver CDE flags (`bls_soc_code`, `experience_years_typical`, `experience_tier`) and 4 Gold CDE flags match the spec's `✅` marks 1:1.

## PII Assertion

All `is_pii: false` across all 32 tagged fields. Confirmed by cross-referencing:

1. Spec §CDE & PII Assessment — every row marks `is_pii` = `❌`
2. `governance/pii-scans/onet-experience-pii-scan.md` — "NO PII DETECTED. All 17 columns classify as Level 1 (Public)"
3. Per-column false-positive analysis in the PII scan (column `n` is sample size not identifier; column `date` is publication-wave month not birth date; `domain_source` is role label not person name)

No PII handling, RLS, or column masking required on any zone.
