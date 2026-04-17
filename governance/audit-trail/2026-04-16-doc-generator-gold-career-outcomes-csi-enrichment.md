# Audit: @doc-generator — Gold career-outcomes CSI enrichment (data dictionary)

**Date:** 2026-04-16
**Agent:** @doc-generator
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 3 — Gold enrichment)
**Parent table:** `consumable.career_outcomes`
**Artifact updated:** `governance/data-dictionary.json`
**Contract version:** bumped to 1.1.0 (minor) upstream by @cde-tagger
**Row count:** 69,947 (preserved; LEFT JOIN enrichment)

## Entries added (6 net-new columns)

| # | Column | Type | is_cde | BT | Source |
|---|--------|------|--------|-----|--------|
| 1 | `net_price_annual` | DOUBLE | **true** | BT-111 | `base.college_scorecard_institution.net_price_annual` (LEFT JOIN on unitid) |
| 2 | `cost_of_attendance_annual` | DOUBLE | **true** | BT-110 | `base.college_scorecard_institution.cost_of_attendance_annual` (LEFT JOIN on unitid) |
| 3 | `net_price_4yr` | DOUBLE | false | BT-113 | `base.college_scorecard_institution.net_price_4yr` (LEFT JOIN on unitid) |
| 4 | `tuition_in_state` | DOUBLE | false | BT-115 | `base.college_scorecard_institution.tuition_in_state` (LEFT JOIN on unitid) |
| 5 | `tuition_out_of_state` | DOUBLE | false | BT-115 | `base.college_scorecard_institution.tuition_out_of_state` (LEFT JOIN on unitid) |
| 6 | `room_board_on_campus` | DOUBLE | false | BT-116 | `base.college_scorecard_institution.room_board_on_campus` (LEFT JOIN on unitid) |

All 6 added between `outcome_completeness` and `source_load_date`, matching the physical-model field-ID ordering (32–37).

## Entries updated (1 in-place re-source)

- **`institution_control`** — re-sourced from `base.college_scorecard_institution` (was `base.college_scorecard`); nullable relaxed `false -> true`; business term assigned **BT-114** (previously `Pending`); `notes` rewritten to remove the "pending Bronze re-ingest" caveat; DQ rules extended to include GLD-CSI-007 (active) and GLD-CSI-009 (enum); GLD-CO-039 retained for historical tracking. Observed coverage 97.42% from EDA.

## Table-level metadata updated

- `description` — appended reference to institution-level cost enrichment as of 2026-04-16
- `source` — now `base.college_scorecard (Silver zone) + base.college_scorecard_institution (Silver zone, LEFT JOIN on unitid)`
- `enrichment_spec_reference` — new field, `docs/specs/raw-ingest-college-scorecard-institution.md`
- `last_updated` — bumped `2026-04-06 -> 2026-04-16`
- `record_count` — unchanged at 69,947 (verified by EDA)

## Cross-artifact CDE-count reconciliation

| Artifact | CDE count on `consumable.career_outcomes` | Aligned |
|----------|-------------------------------------------|---------|
| `governance/data-dictionary.json` (this update) | **13** (11 pre-existing + 2 new) | — |
| `governance/data-contracts/consumable-career-outcomes.yaml` `cde_summary.cde_count` | **13** | yes |
| `governance/data-contracts/consumable-career-outcomes.yaml` `cde_summary.cde_columns` length | **13** | yes |
| `governance/cde-registry/gold-career-outcomes-college-scorecard-cdes.md` §Summary | **13** | yes |
| `governance/models/gold-career-outcomes-college-scorecard-physical.md` is_cde=true column count | **13** (fields 32, 33 + 11 pre-existing) | yes |

All four governance artifacts agree: **13 CDE columns**, **0 PII columns**.

## Judgment calls documented

1. **institution_control DQ-rule list** — retained the legacy `GLD-CO-039` alongside new `GLD-CSI-007` / `GLD-CSI-009`, per registry guidance that GLD-CO-039 is "historical tracking" and GLD-CSI-007 is "the active completeness rule." No deletion of historical rules.
2. **tuition_in_state / tuition_out_of_state observed ranges** — reused the Bronze combined-range figure ($600–$69,330) from BT-115; the EDA does not break out Gold-zone per-field min/max for tuition variants, so the Bronze range is the best-available observed-range anchor. Out-of-state entry additionally includes the Harvard/MIT/Princeton/Stanford/Yale spot-check values from `eda-gold-csi-join-stats.json`.
3. **room_board_on_campus null explanation** — surfaced the "legitimately null at institutions without on-campus housing" caveat in both the plain-English description and `observed_range`, to forestall false-positive reads of the 10.98% null rate by downstream consumers.
4. **net_price_4yr observed_range** — used Silver-zone figures (from BT-113 definition) rather than post-JOIN Gold figures; the Silver range is the same mathematical object (annual × 4) and was computed on the full 2,233-institution non-null set, which is statistically preferable to the 2,352-matched Gold subset.

## Files not touched (verified)

- No `governance/data-dictionaries/*.md` file exists for Gold career-outcomes (the Gold dictionary lives only in the root `data-dictionary.json`). No markdown dictionary to update.
- Contract, registry, physical model — already updated upstream by @cde-tagger and @semantic-modeler; this pass only aligns the dictionary to them.

## Completion status

- Data dictionary JSON: **valid** (parsed as JSON, 37 columns, 13 CDE on `consumable.career_outcomes`)
- Cross-artifact CDE count: **13 everywhere** (contract, registry, dictionary, physical model)
- PII count: **0 everywhere** (unchanged)
- Ready for @governance-reviewer-post and @staff-engineer gates
