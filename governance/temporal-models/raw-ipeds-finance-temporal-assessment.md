# Temporal Assessment: bronze.ipeds_finance

**Date:** 2026-04-30
**Agent:** @temporal-modeler
**Spec:** `docs/specs/full-pipeline-ipeds-finance.md`
**Domain:** Higher Education Outcomes / Institutional Finance
**Verdict:** NOT APPLICABLE

---

## Summary

`bronze.ipeds_finance` does not require bitemporal modeling, SCD2, or temporal versioning at the Bronze layer. The ingest is a single-year point-in-time snapshot. No temporal-modeler design work is required for this spec.

---

## Temporal Grain

**Grain:** Single-year snapshot (point-in-time).

- **Valid time:** Implicit in the `fiscal_year` column. For this spec, `fiscal_year = 2023` for all rows — the IPEDS Finance Survey FY23 publication cycle (provisional release Sep 2024).
- **Transaction time:** Iceberg snapshot at ingest. Given the one-and-done nature of this spec, only one Iceberg snapshot is expected (the initial load); corrections in scope reduce to a re-ingest, which would create a new snapshot per Brightsmith convention.
- **Cadence at the source:** Per `governance/domain-context.md`, IPEDS Finance is annual with a publication lag of approximately year+2. FY24 was confirmed unavailable from NCES at spec time (HTTP 404 on F2324 bulk URLs as of 2026-04-30).

---

## Why No SCD2 / No Temporal Versioning at Bronze

`docs/specs/full-pipeline-ipeds-finance.md` §2 Decision 6 ("Most-recent vintage only — single-year") explicitly scopes multi-year IPEDS Finance and SCD2 history out. There is:

- No second vintage in scope to evolve against.
- No within-fiscal-year amendment stream from NCES for this spec to model (NCES re-publishes the entire fiscal-year file rather than emitting per-cell corrections).
- No need for `valid_from` / `valid_to` columns at Bronze — the snapshot's `fiscal_year` is the entire valid-time signal.
- No need for an `is_correction` / `corrects_record` pattern — re-ingest replaces, with Iceberg time travel preserving the prior snapshot.

A single Iceberg snapshot at load time, recoverable via standard `AT (TIMESTAMP => ...)` time travel, is sufficient.

---

## Forward-Looking Note (Out of Scope for This Spec)

If a future spec extends `bronze.ipeds_finance` to multi-year history (e.g., a longitudinal endowment-trend or marketing-ratio-trend product on `consumable.institution_aura`), the following adjustments will be needed:

| Concern | Current State | Future-Multi-Year Adjustment |
|---|---|---|
| Partition key | Implicit single-year | Partition by `fiscal_year` — natural and already a column |
| Primary record key | `record_id = 'ipf-' + UNITID` | Must incorporate year, e.g., `record_id = 'ipf-' + UNITID + '-' + fiscal_year` — current scheme would collide on second-vintage ingest |
| SCD strategy | None | SCD2 with `valid_from = fiscal_year start`, `valid_to = next fiscal_year start - 1`, `is_current` flag |
| Late-arriving restatements | Re-ingest replaces single row | Need supersession metadata (`supersedes_record_id`, `superseded_at`) and a corrections snapshot strategy |
| Iceberg snapshots | One per ingest | One per fiscal-year ingest; corrections create additional snapshots within the same `fiscal_year` partition |

These are notes for a hypothetical future spec, not implementation work for the current spec.

---

## Decision Log

- **2026-04-30** — Reviewed spec §2 Decision 6 and `governance/domain-context.md` IPEDS Finance section (entry dated 2026-04-30). Confirmed single-year, single-vintage scope. No bitemporal schema, no SCD2, no supersession metadata required at Bronze. Verdict: NOT APPLICABLE. Forward-looking notes recorded for any future multi-year extension.
