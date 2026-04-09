# Lineage Audit Trail: silver-base-onet

**Agent:** @lineage-tracker
**Spec:** docs/specs/silver-base-onet.md
**Timestamp:** 2026-04-08T12:00:00Z
**Output:** governance/lineage/silver-base-onet-20260408T120000Z.json

## Transformations Captured

4 OpenLineage run events produced, one per Silver output table:

| # | Job Name | Inputs | Output | Column Lineage Fields |
|---|----------|--------|--------|-----------------------|
| 1 | silver.transform-onet-occupations | 5 Bronze tables | base.onet_occupations | 14 |
| 2 | silver.transform-onet-activity-profiles | 1 Bronze table | base.onet_activity_profiles | 11 |
| 3 | silver.transform-onet-context-profiles | 1 Bronze table | base.onet_context_profiles | 11 |
| 4 | silver.transform-onet-career-transitions | 1 Bronze table | base.onet_career_transitions | 9 |

## Naming Decisions

- **Job namespace:** `brightsmith` (project standard)
- **Job names:** `silver.transform-onet-{table}` pattern, consistent with `silver.transform-bls-ooh`
- **Dataset names:** Bronze inputs use `bronze.onet_*` (mapped from `raw.onet_*` Iceberg table names). Silver outputs use `base.onet_*` matching the Iceberg namespace.
- **Run IDs:** Deterministic UUIDs for reproducibility (not random UUID v4)
- **Record ID prefixes:** `on` (occupations), `wa` (activity profiles), `wc` (context profiles), `ct` (career transitions) -- matching the code in `src/silver/onet_transformer.py`

## Key Lineage Observations

1. **base.onet_occupations has 5 inputs** -- the only table that reads from all 5 Bronze tables. The 4 child tables (work_activities, work_context, task_statements, related_occupations) are used only for has_* flag derivation (set membership check), not for data values.

2. **raw.onet_task_statements is read but not transformed** -- it contributes only to the has_tasks boolean flag in base.onet_occupations. Task text stays in Bronze for Gemma narrative generation; no Silver task table is produced. This is an intentional spec decision, not a gap.

3. **Multi-detail aggregation** is the dominant transformation pattern across 3 of 4 tables (occupations, activity_profiles, context_profiles). The code uses unweighted arithmetic mean for numeric values and OR-aggregation for boolean flags (suppress_flag).

4. **Burnout element IDs** in the code (BURNOUT_ELEMENT_IDS constant) differ slightly from the spec's proposed IDs -- the EDA corrected several element IDs. The lineage captures the actual implemented IDs from the code, not the spec's proposed IDs.

5. **Career transitions deduplication** reduces rows through 3 mechanisms: SOC truncation to BLS level, self-reference removal, and best-index selection. All 3 are captured in the lineage event.

## Completeness Verification

- Every field in every output schema has a columnLineage entry
- Every transformation type (DIRECT, AGGREGATION, DERIVED) is correctly categorized
- All Bronze input schemas include the fields actually referenced by the transformation code
- The ingested_at field in all 4 tables is documented as having no input fields (generated at transform time)
- The relationship_type field in career_transitions is documented as static/no input (always "similarity")

## Pipeline Gate

Registered completion: `lineage-tracker` -> COMPLETED for spec `silver-base-onet`.
