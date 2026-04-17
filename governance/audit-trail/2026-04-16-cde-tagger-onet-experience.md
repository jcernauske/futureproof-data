# Audit Trail: CDE/PII Tagging — onet-experience-requirements

**Date:** 2026-04-16
**Agent:** bs:cde-tagger
**Spec:** `docs/specs/onet-experience-requirements.md`

## Decisions

- Applied per-field `is_cde` / `is_pii` flags verbatim from spec §CDE & PII Assessment (lines 411-440).
- Three zone-aligned contracts materialized: Raw (CREATED), Silver (CREATED), Gold (UPDATED additively).
- All P0 (business-critical) classification on the 6 Silver + Gold CDEs; Raw CDEs tagged at grain/filter-key criticality.

## Flagged as CDE

| Zone | Column | Severity | Reason |
|------|--------|----------|--------|
| Raw | `onet_soc_code` | P0 | Grain key; FK bridge to BLS SOC |
| Raw | `element_id` | P0 | Silver filter key (`3.A.1`) |
| Raw | `scale_id` | P0 | Silver filter key (`RW`) |
| Silver | `bls_soc_code` | P0 | Natural key; Gold join key |
| Silver | `experience_years_typical` | P0 | Primary metric |
| Silver | `experience_tier` | P0 | Career-tree gating classifier |
| Gold | `related_experience_years` | P0 | UI-visible + default-view input |
| Gold | `related_experience_tier` | P0 | UX gating + decade bucketing |
| Gold | `source_experience_years` | P0 | Delta-derivation input |
| Gold | `experience_delta_years` | P0 | Default-view threshold (<=5) |

## Evaluated — Not Flagged

- Raw (14): `element_name`, `category`, `data_value`, `n`, `standard_error`, `lower_ci_bound`, `upper_ci_bound`, `recommend_suppress`, `date`, `domain_source`, `ingested_at`, `source_url`, `source_method`, `load_date` — structural, statistical, provenance, or pipeline-metadata fields.
- Silver (8): `record_id`, `experience_category_median`, `experience_category_mode`, `experience_distribution`, `onet_details_averaged`, `suppress_flag`, `source_load_date`, `ingested_at` — internal derivations or pipeline metadata.

## PII Determinations

All 32 tagged fields → `is_pii: false`. Confirmed by `governance/pii-scans/onet-experience-pii-scan.md` (verdict: NO PII DETECTED; all Level 1 Public; CC BY 4.0 source).

## Contract Changes

- `governance/data-contracts/raw-onet-experience.yaml` — created (17 columns, 3 CDE).
- `governance/data-contracts/base-onet-experience-profiles.yaml` — created (11 columns, 3 CDE; version 1.0.0).
- `governance/data-contracts/consumable-career-branches.yaml` — updated additively (4 new columns, all 4 CDE; version bumped 1.1.0 -> 1.2.0; `version_history` entry added; `base.onet_experience_profiles` appended to `lineage.source_tables`).

## Output Report

`governance/cde-tagging/onet-experience-cde-tags.md`

## Spec Compliance

Per-row fidelity verified against spec §CDE & PII Assessment. All `✅` / `❌` marks from the spec table materialized 1:1 onto the YAML column entries. No deviations.
