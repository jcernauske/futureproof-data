# Audit Trail: Logical Model - gold-occupation-profiles-bls-ooh

**Agent:** @semantic-modeler
**Date:** 2026-04-07
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Stage:** 2 of 3 (Logical Model)
**Prior Stage:** Conceptual Model (APPROVED)
**Status:** PROPOSED -- awaiting human approval

## Stage Progression

| Stage | Artifact | Status | Date |
|-------|----------|--------|------|
| 1. Conceptual | governance/models/gold-occupation-profiles-bls-ooh-conceptual.md | APPROVED | 2026-04-07 |
| 2. Logical | governance/models/gold-occupation-profiles-bls-ooh-logical.md | PROPOSED | 2026-04-07 |
| 3. Physical | Pending logical approval | -- | -- |

## Modeling Decisions

### 1. 30 attributes total (18 carried, 12 new)
18 fields carried verbatim from Silver `base.bls_ooh`. 6 Silver fields dropped (employment_change, median_wage_capped, education_typical, work_experience, training_typical, ingested_at) with justification. 12 new derived attributes added in Gold.

### 2. GRW score piecewise function fully specified
All 8 breakpoint segments documented with explicit interpolation formulas, covering the full range from severe decline (<=20%) to exceptional growth (>=50%). Two verification examples from the golden dataset included. National average growth (~4%) maps to approximately 6.0.

### 3. openings_score not persisted
The intermediate openings_score (PERCENT_RANK mapped to 1-10) is computed inline during market_score derivation but not stored. Reduces column count without losing information.

### 4. Entry Requirements separated as logical group
Despite being absorbed into Occupation Profile in the conceptual model, entry requirements are tracked as a separate logical group because education_code serves as partition key for wage_percentile_education_tier.

### 5. CDE count expanded from 5 to 9
Silver had 5 CDEs. Gold adds grw_score, wage_percentile_overall, wage_percentile_education_tier, and market_score -- the derived fields that directly feed FutureProof stats and boss fights.

### 6. growth_category marked NOT NULL
Spec requires this field. Current data has no nulls across all 832 rows. Marked NOT NULL in Gold to match spec, acknowledging this is a tighter constraint than Silver's NULLABLE.

## Alternatives Considered

1. **Persisting openings_score as a column** -- Rejected. No direct consumer use case; can be recomputed from openings_annual_avg if needed. Would add noise to the schema.

2. **Four-level confidence tier (matching career outcomes BT-024)** -- Rejected. Occupation profiles always have employment data, so an "insufficient" level has no rows. Three levels (high/medium/low) are semantically complete for this domain.

3. **Normalizing entry requirements into a separate table** -- Rejected. 832 rows with 1:1 cardinality; no join benefit. Consistent with career outcomes pattern.

## References Used

- Approved conceptual model: governance/models/gold-occupation-profiles-bls-ooh-conceptual.md
- Spec: docs/specs/gold-occupation-profiles-bls-ooh.md
- Business glossary: governance/business-glossary.json (BT-015, BT-016, BT-026, BT-027-BT-054)
- Silver logical model: governance/models/silver-base-bls-ooh-logical.md
- Gold career outcomes logical model: governance/models/gold-career-outcomes-college-scorecard-logical.md (format reference)
