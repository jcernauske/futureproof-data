# Audit Trail: Conceptual Model — gold-futureproof-engine

**Agent:** @semantic-modeler
**Date:** 2026-04-09
**Spec:** docs/specs/gold-futureproof-engine.md
**Stage:** Conceptual (Stage 1 of 3, Greenfield)
**Status:** PROPOSED — awaiting human approval

## Artifact Produced

- `governance/models/gold-futureproof-engine-conceptual.md`

## Mode Detection

**Greenfield.** Target tables `consumable.program_career_paths` and `consumable.career_branches` do not exist in the Iceberg catalog. No source code exists at `src/gold/futureproof_engine.py`. This is new work.

## Data Patterns That Drove Model Choices

1. **CIP granularity mismatch (spec + crosswalk EDA).** College Scorecard stores 4-digit CIP (XX.XX), crosswalk stores 6-digit (XX.XXXX). Strict matching yields 0% coverage. The spec mandates 4-digit prefix matching, achieving 91% CIP coverage and 97% row coverage. This was elevated to a named entity (CIP-SOC Bridge, BT-086) because it is the critical integration decision.

2. **Cross-source join chain.** This is the first Gold product joining all four data sources. The join chain flows: career_outcomes --> crosswalk (prefix match) --> occupation_profiles + onet_work_profiles. LEFT JOINs on the occupation side mean partial data is expected and must be quality-classified.

3. **Placeholder stats.** RES and AI Boss depend on Karpathy scores not yet ingested. Modeled as entities with explicit placeholder status rather than omitted, to represent the target-state data model.

4. **Fan-out from prefix matching.** One 4-digit CIP matches multiple 6-digit crosswalk entries, each bringing different SOC codes. Dedup on grain (unitid, cipcode, soc_code) is required after the join. Estimated 150K-500K rows.

5. **Two independent product tables.** program_career_paths and career_branches share Occupation Identity as a concept but have independent grains and independent source dependencies. Modeled as peer entities connected through the shared occupation dimension.

## Alternatives Considered

1. **Single flat entity model (no decomposition).** Rejected because the wide table contains seven distinct business concerns (identity, stats, bosses, program context, occupation context, quality, branches). Decomposing into entities at the conceptual level clarifies the business structure even though the physical table will be denormalized.

2. **Omitting placeholder stats from the conceptual model.** Rejected because the pentagon is a five-stat product concept. Modeling only four stats would misrepresent the target state and require a model revision when RES is added.

3. **Modeling the crosswalk join as a simple relationship rather than an entity.** Rejected because the CIP prefix match strategy has its own business term (BT-086), its own coverage metrics, and its own design tradeoffs. It deserves visibility at the conceptual level.

## Business Terms Referenced

BT-001, BT-003, BT-005, BT-006, BT-009, BT-010, BT-019, BT-024, BT-029, BT-030, BT-036, BT-046, BT-047, BT-048, BT-060, BT-061, BT-063, BT-064, BT-066, BT-068, BT-077, BT-078, BT-079, BT-080, BT-081, BT-082, BT-083, BT-084, BT-085, BT-086, BT-087, BT-088, BT-089, BT-090, BT-091, BT-092, BT-093

## Next Step

Awaiting human approval of the conceptual model. Upon APPROVED status, the logical model (Stage 2) will be produced.
