# Audit Trail — lineage-tracker — Gold CSI enrichment of `consumable.career_outcomes`

- **Agent:** @lineage-tracker
- **Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 3)
- **Event:** CSI enrichment re-promote of `consumable.career_outcomes`
- **Timestamp:** 2026-04-16T16:30:00Z
- **Event file:** `governance/lineage/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T163000Z.json`

## What was captured

- **1 COMPLETE run event** with `runId` `b4a1f8c2-7e36-4d91-a0bf-2c5d3e9a1f48`.
- **2 inputs** named (confirming spec's "TWO Silver inputs" requirement):
  1. `brightsmith.base.college_scorecard` — primary grain driver, unchanged.
  2. `brightsmith.base.college_scorecard_institution` — NEW secondary input.
- **1 output:** `brightsmith.consumable.career_outcomes` — 69,947 rows, 37 columns.
- **37 columnLineage entries** — one per output field.
- **Schema evolution noted:** field IDs 32–37 added; field ID 4 (`institution_control`) re-sourced in place.
- **Supersession:** previous single-input event `c7e29a14-5b83-4d1f-a6c0-8f2d4e7b3a91` (2026-04-06) declared as the superseded predecessor via `brightsmith_supersedes` facet. Predecessor file retained for audit / time-travel.

## Naming decisions

- **Job name:** kept as `gold.transform-career-outcomes` (same transformer, same output). A renamed job would have broken lineage continuity with the superseded event.
- **Event filename:** added `-csi-enrichment-` segment to distinguish from the 2026-04-06 event while preserving the `gold-career-outcomes-college-scorecard-` prefix.
- **SHA evidence:** recorded `sourceCodeSha256` for the transformer, runner, spec, and both upstream Silver transformers. Matches the hashes recorded in `governance/pipeline-state/raw-ingest-college-scorecard-institution-pipeline.json` for the `primary-agent` step (`2d4ef12c...`).

## Runtime metrics — provenance

The framework's `BaseIngestor.ingest()` auto-emit path does not cover Gold overwrite promotes; runtime event emission is not yet wired for this path. Metrics captured here are a mix of:

- **Verified** (from scorecard / pipeline-state): row count 69,947, CSI coverage 95.45%, institution_control coverage 97.42%, unmatched UNITID 207, DQ 51/51 PASS, schema field IDs 32–37.
- **Approximated** (labelled in the event): `approxDurationMs` = 42s bracketed from primary-agent completed_at (16:16:09Z) → dq-engineer completed_at (16:22:42Z); wider than actual single-invocation time but honest upper bound. Reason is stated in `runtimeApproximationReason` facet so a future @governance-reviewer can see why exact wall-clock isn't present.

## Ambiguity / interpretation decisions

1. **Does the Gold job belong to the career-outcomes spec or the CSI spec?** Both. The `specReference` points at the CSI spec (which drove this re-promote) and the `supersedes` facet points at the event that belonged to the career-outcomes spec. Either spec file can locate the lineage from its namespace.
2. **`institution_control` lineage:** pre-enrichment sourced from `base.college_scorecard`; post-enrichment sourced from `base.college_scorecard_institution`. Recorded only the post-enrichment source in `columnLineage.fields.institution_control.inputFields` with a `changeNote` explaining the re-source — the historical source is documented in the superseded event.
3. **ROI driver:** recorded in the `debt_median` description that it remains the active ROI driver for this spec; migration to `net_price_annual` happens in the follow-up `roi-formula-cost-of-attendance` spec.

## Verification performed

- JSON parses successfully (Python `json.load`).
- Both input datasets present and named.
- Output row count matches spec invariant (69,947).
- Output field count = 37 (30 original + 1 re-sourced + 6 new).
- Column lineage coverage: 37/37.
- All 6 NEW fields reference `base.college_scorecard_institution` as input.
- `institution_control` (re-sourced field ID 4) references the institution input.
- `brightsmith_supersedes` facet names the prior event and its runId.

## Not in scope for this event

- Not verified against runtime `governance.lineage_events` Iceberg table — that table is not yet populated for Gold overwrite promotes per framework note.
- `pipeline_gate complete` was NOT run per the user's instruction.
