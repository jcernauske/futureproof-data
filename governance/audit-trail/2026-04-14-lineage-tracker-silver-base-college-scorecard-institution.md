# Lineage Tracker Audit — silver-base-college-scorecard-institution

**Date:** 2026-04-14T22:00:00Z
**Agent:** @lineage-tracker
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Zone:** Silver (base)
**Artifact:** governance/lineage/silver-base-college-scorecard-institution-20260414T220000Z.json
**Upstream bronze run:** 81ba1e54-0862-441e-b1d0-62fbc014b8f3

## Scope

Captured column-level lineage for the Silver transformer that reads `raw.college_scorecard_institution` (28 fields) and writes `base.college_scorecard_institution` (35 fields).

## Transformations Captured

### DIRECT pass-through (18 fields)

| Target | Source | Notes |
|---|---|---|
| unitid | unitid | Grain key |
| institution_name | instnm | Rename |
| state_abbr | stabbr | Rename |
| tuition_in_state | tuitionfee_in | Rename |
| tuition_out_of_state | tuitionfee_out | Rename |
| room_board_on_campus | roomboard_on | Rename |
| room_board_off_campus | roomboard_off | Rename |
| books_supplies | booksupply | Rename |
| source_load_date | load_date | Rename (Bronze ingest date) |
| costt4_a_raw | costt4_a | Provenance pass-through |
| costt4_p_raw | costt4_p | Provenance pass-through |
| npt4_pub_raw | npt4_pub | Provenance pass-through |
| npt4_priv_raw | npt4_priv | Provenance pass-through |
| npt41_pub_raw..npt45_pub_raw | npt41_pub..npt45_pub | 5 raw public quintile fields |
| npt41_priv_raw..npt45_priv_raw | npt41_priv..npt45_priv | 5 raw private quintile fields |

Total DIRECT: 9 named + 5 public quintile + 5 private quintile = 19 (one more than spec summary because both raw COA fields are DIRECT). Matches transformer code.

### DERIVED (16 fields)

| Target | Sources | Logic |
|---|---|---|
| record_id | unitid | `compute_grain_id(..., GRAIN_FIELDS=['unitid'], prefix='csi')` |
| institution_control | control | `CONTROL_LABELS` map: 1->Public, 2->Private nonprofit, 3->Private for-profit |
| cost_of_attendance_annual | costt4_a, costt4_p | `COALESCE(costt4_a, costt4_p)` — academic-year preferred |
| cost_of_attendance_4yr | costt4_a, costt4_p | `cost_of_attendance_annual * 4` via null-propagating multiply |
| net_price_annual | control, npt4_pub, npt4_priv | `pick_by_control`: control=1 -> pub, control in {2,3} -> priv |
| net_price_4yr | control, npt4_pub, npt4_priv | `net_price_annual * 4` |
| net_price_q1..q5 | control, npt4X_pub, npt4X_priv | Same routing per quintile (5 fields) |
| ingested_at | — | Silver-generated now(UTC), NOT Bronze ingested_at |

## Naming Decisions

- **Job name:** `base.transform-college-scorecard-institution` — Silver zone convention (`base.` prefix matches table namespace `base.college_scorecard_institution`).
- **Input dataset:** `brightsmith.raw.college_scorecard_institution` — matches Bronze output from upstream run.
- **Output dataset:** `brightsmith.base.college_scorecard_institution` — matches Silver physical model field IDs 1-35.
- **Run ID:** UUID v4 (`a3f21c7e-9d48-4b2a-bf6c-1f24e0b1d905`), one per transformer execution.

## Ambiguities & Interpretations

1. **`ingested_at` provenance.** The transformer overwrites bronze `ingested_at` with `datetime.now(tz=utc)` inside `transform_row()`. Modeled as DERIVED with empty inputFields rather than DIRECT from bronze ingested_at, since it represents the Silver-zone processing time, not the Bronze ingest time. Bronze ingest time is still recoverable via `source_load_date`.

2. **Net price routing input cardinality.** `net_price_annual` has three inputs (control, npt4_pub, npt4_priv) because the routing function reads all three even though only one flows to the output per row. Recorded all three as inputFields so impact analysis can trace either pub or priv changes.

3. **Raw pass-through fields preserved across routing.** Both `npt4_pub_raw` and `npt4_priv_raw` are always populated regardless of which was selected by control routing. Noted this in the transformationDescription so auditors understand the full source record is preserved.

4. **`preddeg` NOT in Silver.** Bronze has `preddeg` and `control` as filter/routing fields; Silver keeps only `institution_control` (human-readable). `preddeg` is not propagated because it was already used as a filter upstream (PREDDEG=3 OR ICLEVEL=1) and adds no downstream value. No lineage node created for a dropped field.

5. **Bronze framework metadata fields dropped.** `source_url` and `source_method` from Bronze are NOT carried into Silver. The physical model does not include them. This is expected: the Bronze table retains full source provenance and Silver links back via `record_id` + `source_load_date`.

## Verification Checklist

- [x] Every Silver output field has a lineage entry (35/35)
- [x] Every DIRECT field maps to exactly one Bronze source field
- [x] Every DERIVED field lists all Bronze sources involved in the logic
- [x] Transformation descriptions name the exact function/operation from the transformer code (`compute_grain_id`, `pick_by_control`, `multiply_or_none`, `CONTROL_LABELS`, `COALESCE`)
- [x] Job namespace `brightsmith` matches project convention
- [x] Input/output table names match bronze lineage event and physical model
- [x] Schemas match transformer's `get_silver_schema()` (field IDs 1-35) and bronze output schema
- [x] Run ID is UUID v4, unique per execution
- [x] Spec reference present in run facets
- [x] Agent attribution present with rationale
- [x] Upstream bronze run referenced for cross-zone lineage chaining

## Runtime Metadata Status

This event is a **static template** produced before first transformer run. Missing runtime fields that `emit_complete()` should populate when the transformer executes:

- `snapshot_id` — Iceberg snapshot ID produced by promote()
- `duration_ms` — wall-clock time
- `rows_read`, `rows_transformed`, `rows_skipped_transform`, `promoted`, `skipped_dedup` — actual counts from transform() return
- DQ metrics (once dq-rule-writer adds rules)

**Recommendation:** Silver transformer should be wired to `brightsmith.infra.lineage.emit_start()`/`emit_complete()` (same pattern as BaseIngestor auto-emission) so future runs overwrite this static template with the actual Iceberg lineage event containing runtime metadata. Flag this for implementer.

## Follow-ups for Downstream Agents

- **@governance-reviewer:** This lineage file satisfies the Silver-zone completeness checkbox. Verify DQ rules (@dq-rule-writer) and CDE tags (@cde-tagger) reference the same 35 Silver fields.
- **@dq-rule-writer:** Use the `columnLineage.fields` keys as the canonical Silver field list for rule coverage.
- **@fp-data-reviewer:** Control-routing correctness (pick_by_control) is the highest-risk logic here — recommend a targeted unit test verifying control=1 picks pub, control in {2,3} picks priv, and control outside {1,2,3} returns None.

## Artifacts

- Lineage event: `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/silver-base-college-scorecard-institution-20260414T220000Z.json`
- Source code: `/Users/jcernauske/code/bright/futureproof-data/src/silver/college_scorecard_institution_transformer.py`
- Physical model: `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-college-scorecard-institution-physical.md`
- Upstream Bronze lineage: `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json`
