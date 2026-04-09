# Audit Trail: Logical Model — gold-futureproof-engine

**Agent:** @semantic-modeler
**Spec:** gold-futureproof-engine
**Stage:** 2 of 3 (Logical Model)
**Mode:** Greenfield
**Timestamp:** 2026-04-09
**Status:** PROPOSED (pending human approval)

## Inputs Read

- `docs/specs/gold-futureproof-engine.md` — full spec with schema, derivation rules, join chain
- `governance/models/gold-futureproof-engine-conceptual.md` — approved conceptual model (Stage 1)
- `governance/models/gold-occupation-profiles-bls-ooh-logical.md` — reference logical model (style, format, conventions)
- `governance/business-glossary.json` — business term IDs BT-001 through BT-093

## Artifacts Produced

- `governance/models/gold-futureproof-engine-logical.md` — logical model covering both tables

## Key Modeling Decisions

1. **Two tables, one model file.** Both `consumable.program_career_paths` (40 attributes) and `consumable.career_branches` (23 attributes) are documented in a single logical model since they share a spec and upstream source chain. Each table has its own grain, attribute definitions, and derivation rules sections.

2. **Attribute grouping follows conceptual entities.** Pentagon Stats, Boss Fight Profile, Program Context, Occupation Context, and Data Quality are documented as separate logical attribute groups even though they flatten into a single physical table per the Gold zone denormalization pattern.

3. **CIP-SOC Bridge is a join strategy, not persisted attributes.** The conceptual model elevates the CIP Prefix Match (BT-086) as a named entity. At the logical level, this becomes the join chain documentation and the match_quality derivation rule -- there are no bridge-specific columns in the output.

4. **All derivation rules documented with full piecewise formulas.** ERN (60/40 blend with scale mapping), ROI (6-segment piecewise linear), Loans (inverse of ROI), Ceiling (single formula from wage_percentile_education_tier), match_quality (CASE on join success), overall_confidence (tiered from stats count + match quality), and all stat deltas.

5. **Placeholder fields explicitly modeled.** stat_res and boss_ai_score are documented with "always null" derivation rules and linked to their business terms (BT-080, BT-083). This preserves schema completeness for the target state while communicating current MVP limitations.

6. **Dedup strategy documented at grain level.** The CIP prefix join fan-out produces duplicate (unitid, cipcode, soc_code) rows. The logical model specifies: keep one row per grain, prefer the row with the most non-null stat values.

7. **match_quality derived at Gold time.** Explicitly documents that the upstream crosswalk Silver's `has_scorecard_match` flag must NOT be used (it is FALSE for all rows due to CIP granularity mismatch). Instead, match_quality is derived from whether the BLS and O*NET LEFT JOINs produced non-null results.

## Alternatives Considered

- **Separate model files per table:** Rejected because the tables share a spec, upstream sources, and join chain. A single file provides better traceability.
- **Normalizing occupation context into a separate entity:** Rejected because the Gold zone pattern is denormalized flat tables. The logical groups provide semantic structure without physical normalization.
- **Including cip_family_earnings_rank and wage_percentile_overall as persisted fields:** Rejected because they are intermediate derivation inputs used only to compute stat_ern. They can be computed inline. The spec does not include them in the output schema.

## Stage Progression

| Stage | Status | Date |
|-------|--------|------|
| Conceptual | PROPOSED | 2026-04-09 |
| Logical | PROPOSED | 2026-04-09 |
| Physical | Not started | -- |
