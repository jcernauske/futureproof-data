# Audit Trail: doc-generator / onet-experience data dictionary

**Date:** 2026-04-16
**Agent:** @doc-generator (bs:doc-generator)
**Spec:** `docs/specs/onet-experience-requirements.md`
**File updated:** `governance/data-dictionary.json`

## Summary

Added 32 new column entries across the three zones introduced by the
`onet-experience-requirements` spec, plus logged the 4 additive Gold columns
into the existing `consumable.career_branches` table entry.

| Zone | Table | Action | Columns Added |
|------|-------|--------|---------------|
| Bronze | `raw.onet_experience` | NEW table entry | 17 |
| Silver | `base.onet_experience_profiles` | NEW table entry | 11 |
| Gold | `consumable.career_branches` | EXTENDED (inserted 4 columns before `promoted_at`) | 4 |
| **Total** | | | **32** |

All existing entries in `data-dictionary.json` were preserved unchanged. The
final table count in `tables` is 32 (up from 30).

## Cross-References Applied

- **BT-117 (Related Work Experience)** — 7 references across the new entries:
  all RW-derived Silver columns (experience_category_median,
  experience_years_typical, experience_category_mode, experience_distribution)
  plus Gold related_experience_years, source_experience_years,
  experience_delta_years.
- **BT-118 (Experience Tier)** — 2 references: Silver experience_tier and
  Gold related_experience_tier, which is the pattern required by the spec
  (derived classification attached to the tier-valued columns only).
- **BT-027 (SOC Code)** — applied to raw.onet_experience.onet_soc_code and
  base.onet_experience_profiles.bls_soc_code, matching the cross-file
  convention established in the other raw.onet_* / base.onet_* entries.
- **BT-056 (Content Model Element ID)** — applied to element_id (consistent
  with the other O*NET tables).
- **BT-063 (Multi-Detail Aggregation)** — applied to
  base.onet_experience_profiles.onet_details_averaged, matching
  base.onet_activity_profiles precedent.
- **BT-064 (Suppress Flag)** and **BT-015 / BT-016 / BT-017 / BT-026** —
  applied to utility/metadata columns per existing conventions.

## CDE Flag Distribution

Matches `governance/cde-tagging/onet-experience-cde-tags.md` exactly:

| Zone | CDE-flagged fields |
|------|--------------------|
| Raw | onet_soc_code, element_id, scale_id (3 of 17) |
| Silver | bls_soc_code, experience_years_typical, experience_tier (3 of 11) |
| Gold | related_experience_years, related_experience_tier, source_experience_years, experience_delta_years (4 of 4 new) |
| **Total** | **10** |

No PII flagged anywhere — all 32 entries carry `is_pii: false`, consistent
with the spec §CDE & PII Assessment and `governance/pii-scans/onet-experience-pii-scan.md`.

## Derivation Descriptions

Added `derivation_description` on 7 derived fields per the user request:

| Zone | Column | What the derivation describes |
|------|--------|------------------------------|
| Silver | experience_category_median | Weighted-median walk with tie-break rule (spec §Zone 2 step 2 + open-decisions approval) |
| Silver | experience_years_typical | Category-to-midpoint map + multi-detail average (spec §Zone 2 steps 3 & 5) |
| Silver | experience_tier | Four-bucket threshold rule (spec §Zone 2 step 4 + open-decisions approval) |
| Silver | experience_category_mode | Argmax over RW distribution |
| Silver | experience_distribution | JSON encoding of the full RW distribution |
| Gold | related_experience_tier | Pass-through from Silver via LEFT JOIN on related_soc_code |
| Gold | experience_delta_years | NULL-propagating CASE WHEN expression (spec §Zone 3 + open-decisions approval) |

All derivation descriptions cite `docs/specs/onet-experience-requirements.md`
and, where relevant, `governance/approvals/onet-experience-requirements-open-decisions.md`
(the human-approved open-decisions file for tier thresholds, the "Over 10 years"
midpoint, and multi-detail aggregation, all approved 2026-04-16).

## Observed Ranges / EDA Citations

The `notes` field on each Raw column carries real-data ranges from
`governance/eda/raw-onet-experience-eda.md` (EDA 2026-04-16, 35,998 rows, 878
distinct O*NET-SOC codes). Specific numbers pinned in the dictionary:

- `n` sample size: observed 13 to 98, median 23, mean 25.23
- `data_value`: observed 0.0 to 100.0 (max 100.0 on RL, 95.83 on RW)
- `standard_error`: 23.9% null (correlates 1:1 with Occupational Expert rows)
- CI bounds: 52.75% null (paired)
- `recommend_suppress`: 3 values (N=26,524 / Y=864 / n/a=8,610)
- `scale_id`: RL=10,536, RW=9,658, PT=7,902, OJ=7,902
- 754 of 878 occupations (85.9%) have no single RW category above 50%
  (motivates weighted-median-walk logic in Silver)

## Schema Extension

None. The existing dictionary schema (with `type`, `description`, `is_cde`,
`cde_rationale`, `is_pii`, `nullable`, `source_column`, `business_term`,
`dq_rules`, `lineage`, `last_updated`, `updated_by`, `notes`) was sufficient
for all 32 entries. The `derivation_description` field was already in use by
other specs so no schema extension was required. The existing singular
`business_term` convention was preserved (the user request used
`related_business_terms` plural but the on-disk schema uses `business_term`
string — I matched the existing pattern to avoid fragmenting the dictionary).

## Lineage References

| Zone | Lineage file referenced |
|------|------------------------|
| Raw | `governance/lineage/onet-experience-raw-20260417-010651.json` (exists on disk) |
| Silver | `governance/lineage/onet-experience-silver-{timestamp}.json` (placeholder — file will be written by `bs:lineage-tracker` at Phase 3 step 20) |
| Gold | `governance/lineage/onet-experience-gold-{timestamp}.json` (placeholder — file will be written by `bs:lineage-tracker` at Phase 4 step 27) |

The Silver and Gold lineage paths use `{timestamp}` placeholders per the
pattern established in the spec §Governance Artifacts > Lineage section,
which enumerates three explicit OpenLineage events (one per transformation
boundary). Downstream `bs:lineage-tracker` invocations will produce files
matching this pattern and the dictionary entries can be patched with the
concrete timestamped paths in a subsequent doc-generator cycle.

## Judgment Calls

1. **Plural vs. singular business term field.** The user request said
   "related_business_terms (BT-117 / BT-118 where relevant)" but the existing
   `data-dictionary.json` schema uses a singular `business_term` string on
   every entry (verified via 355 occurrences and 0 occurrences of the plural).
   I preserved the existing schema. Where a field is genuinely associated
   with both BT-117 (as the RW source measure) and BT-118 (as the tier
   classification), I picked the primary one for the `business_term` field
   and mentioned the other in the description body — experience_tier uses
   BT-118 because the tier classification IS what the field represents, and
   related_experience_tier (Gold) does the same. experience_years_typical
   uses BT-117 because it is the RW-derived scalar.

2. **Experience_category_mode cross-link.** Not strictly derived in the spec
   §Zone 2 step list (the spec shows it in the Silver Schema table as
   "Most common category (highest percent)"). I wrote an explicit
   derivation_description anyway to keep the audit trail explicit for every
   derived Silver field.

3. **`notes` field on new Raw columns.** Existing raw.onet_* entries use
   `notes` sparingly. I populated `notes` on every Raw column with concrete
   EDA-derived ranges because the user specifically requested "populate
   observed_range or similar field if the dictionary schema supports it" —
   the schema supports `notes`, so I used that. No new fields were added to
   the dictionary schema.

4. **Gold column insertion point.** Placed the 4 new experience columns
   immediately after `branch_has_full_data` and before `promoted_at` — that
   is, between the pre-existing "data completeness" flag and the pipeline
   metadata timestamp. This matches the contract YAML ordering
   (`governance/data-contracts/consumable-career-branches.yaml` places the
   Experience block after all delta columns and before the pipeline
   metadata), preserving a consistent column order across dictionary and
   contract.

## Verification

JSON parse valid. Post-edit counts:

- `tables`: 32 (was 30)
- `raw.onet_experience.columns`: 17
- `base.onet_experience_profiles.columns`: 11
- `consumable.career_branches.columns`: 34 (was 30; +4 experience columns)
- BT-117 references (new entries only): 7
- BT-118 references (new entries only): 2
- CDE-flagged (new entries only): 10 (3 Raw + 3 Silver + 4 Gold)
- PII-flagged (new entries only): 0
- `derivation_description` entries (new): 7

File:
`/Users/jcernauske/code/bright/futureproof-data/governance/data-dictionary.json`
