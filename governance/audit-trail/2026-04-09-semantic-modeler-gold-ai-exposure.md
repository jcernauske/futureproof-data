# Audit Trail: Semantic Modeler -- gold-ai-exposure

**Date:** 2026-04-09
**Agent:** @semantic-modeler
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md (Zone 3: Gold)
**Mode:** Greenfield
**Config:** REQUIRE_HUMAN_APPROVAL = true (per CLAUDE.md)

## Stage Progression

| Stage | Artifact | Status | Timestamp |
|-------|----------|--------|-----------|
| 1. Conceptual | governance/models/gold-ai-exposure-conceptual.md | PROPOSED | 2026-04-09 |
| 2. Logical | governance/models/gold-ai-exposure-logical.md | PROPOSED | 2026-04-09 |
| 3. Physical | governance/models/gold-ai-exposure-physical.md | PROPOSED | 2026-04-09 |

All three stages produced. All PROPOSED pending human review per REQUIRE_HUMAN_APPROVAL = true.

## Key Modeling Decisions

1. **Simple three-entity conceptual model.** This is a small derivation table (~389 rows, 9 columns). Decomposed into AI Exposure Profile (source data), Resilience Scoring (derived stats), and Occupation Identity. Intentionally minimal compared to the occupation profiles model which has 7 entities for a much richer table.

2. **No Data Quality Context or Stat Mapping entities.** Unlike gold-occupation-profiles-bls-ooh, this table has no null complexity (bls_match filter ensures completeness) and always backs exactly RES + AI Boss. Adding these entities would be over-engineering for a simple derivation table.

3. **Filter at Gold, not Silver.** Followed Brightsmith pattern: Silver preserves all rows (including unmatched SOC codes) for auditability; Gold applies the business filter (bls_match=true only).

4. **Prefix 'aie' for record_id.** Consistent with spec. Distinct from Silver's 'kai' prefix since the grain changes after filtering.

5. **exposure_score range 0-10 (not 1-10).** Physical model preserves the original Karpathy range. The derived fields (stat_res, boss_ai_score) use 1-10 with appropriate floor/cap formulas.

## Business Glossary Terms Referenced

| Term ID | Name | Status |
|---------|------|--------|
| BT-015 | Record ID | approved |
| BT-026 | Promoted At | approved |
| BT-027 | SOC Code | approved |
| BT-028 | Occupation Title | approved |
| BT-080 | AI Resilience (stat_res) | approved |
| BT-083 | Boss AI Score | approved |
| BT-094 | AI Exposure Score (Karpathy) | approved |
| BT-095 | AI Exposure Rationale | approved |

## Patterns Followed

- Followed gold-occupation-profiles-bls-ooh model structure for formatting, metadata headers, and column definition tables
- Followed silver-base-karpathy-ai-exposure model set for source-to-target traceability
- Physical model Mermaid diagram includes description + logical attribute mapping per convention

## Alternatives Considered

1. **Including bls_match as a carried field.** Rejected -- after filtering to bls_match=true only, the field would be a constant (always true) with no analytical value.

2. **Including slug for provenance.** Rejected -- slug is a source system identifier (Karpathy's kebab-case key). The consumable product should use SOC codes, which are the standard taxonomy. Slug is preserved in Silver for audit trail.

3. **Adding a confidence_tier field.** Rejected -- unlike BLS OOH data which has variable completeness (23 occupations missing wages), this table has uniform completeness after the bls_match filter. A confidence tier would be "medium" for every row (reflecting the LLM-generated nature of the scores) with no variation.
