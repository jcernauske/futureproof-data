# Audit Trail: silver-base-bls-ooh Logical Model

**Agent:** @semantic-modeler
**Date:** 2026-04-07
**Spec:** docs/specs/silver-base-bls-ooh.md
**Stage:** Logical (Stage 2 of 3)
**Mode:** Greenfield
**Prior Stage:** Conceptual (APPROVED)

## Action

Proposed logical model for `base.bls_ooh` Silver table.

## Artifact Produced

- `governance/models/silver-base-bls-ooh-logical.md` (Status: PROPOSED)

## Key Decisions

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Single denormalized table (25 attributes) | All conceptual relationships are 1:1 or 1:0..1. Matches College Scorecard Silver pattern. Silver Base tables are wide, query-ready fact tables. | Separate tables per conceptual entity -- rejected because it adds join complexity with no normalization benefit at this grain. |
| 2 | Original BLS text labels preserved alongside coded integers | Provides auditability (text), filterability (code), and consistency (normalized name). Three representations serve different consumers. | Drop original text labels (keep only codes + normalized names) -- rejected because it loses traceability to Bronze source. |
| 3 | Employment fields marked NULLABLE despite full current coverage | Defensive design for future BLS cycles that may have partial data. Schema evolution is expensive; nullable fields are cheap. | NOT NULL with defaults -- rejected because a default value (e.g., 0) would mask genuinely missing data. |
| 4 | 5 CDE attributes: soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage | These drive downstream Gold stats (ERN, GRW) and the CIP-SOC crosswalk. Other fields are important but not critical data elements. | Include openings_annual_avg as CDE -- not selected because it is not a primary input to any current Gold stat. |
| 5 | No projection_cycle attribute | Single snapshot dataset. Temporal dimension not needed until multiple cycles are retained. source_load_date provides pipeline-level temporal context. | Add projection_cycle as a constant string attribute -- considered but adds no value for a single-cycle dataset. |

## Inputs Used

- Approved conceptual model: `governance/models/silver-base-bls-ooh-conceptual.md`
- Spec schema section: `docs/specs/silver-base-bls-ooh.md`
- Business glossary terms BT-027 through BT-046: `governance/business-glossary.json`
- College Scorecard logical model (pattern reference): `governance/models/silver-base-college-scorecard-logical.md`

## Open Issues Forwarded

1. Three original BLS text label fields (education_typical, work_experience, training_typical) lack business glossary terms. Low priority -- coded versions have terms.
2. Pipeline metadata fields (record_id, source_load_date, ingested_at) may reuse College Scorecard terms (BT-015/016/017) or need BLS-specific terms. @data-steward to decide.

## Next Step

Human approval of logical model, then advance to physical model (Stage 3).
