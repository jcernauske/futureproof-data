# Temporal Design: raw.eada (full-pipeline-eada)

**Date:** 2026-04-30
**Agent:** @temporal-modeler
**Domain:** Higher-education athletics disclosure (EADA Athletics Disclosure Survey)
**Spec:** `docs/specs/full-pipeline-eada.md`

---

## Verdict: NOT APPLICABLE

Bitemporal modeling is **not applicable** to `raw.eada` as scoped in this spec. This is a **single-year, point-in-time snapshot** ingest. The spec's Claude Code Prompt OUT OF SCOPE block (line 81) explicitly forbids multi-year SCD2:

> "No multi-year SCD2."

There is therefore no temporal-evolution dimension to model at the bronze zone in this spec.

---

## Temporal Grain

| Dimension | Value |
|-----------|-------|
| Reporting cadence (source) | Annual (per `governance/domain-context.md` EADA section) |
| Reporting year ingested | 2022 (EADA 2022–2023 academic year) |
| Stamp column | `reporting_year = 2022` (constant across all rows in this load) |
| Valid time | Single fixed academic year — not modeled as a range |
| Transaction time | Iceberg snapshot on initial load only |

**Grain:** one row per institution (UNITID) for academic year 2022. No history, no versioning, no amendments handled at bronze.

---

## Bitemporal Status

| Requirement | Status | Rationale |
|-------------|--------|-----------|
| Valid time columns (`valid_from`, `valid_to`) | NOT IMPLEMENTED | Single-year snapshot has no validity range to model. The implicit valid period is the 2022–2023 academic year, captured by `reporting_year`. |
| Transaction time via Iceberg snapshots | DEFAULT BEHAVIOR ONLY | Standard Iceberg snapshot on load. No correction/amendment workflow defined in this spec. |
| SCD2 (slowly changing dimension type 2) | EXPLICITLY OUT OF SCOPE | Spec line 81 forbids it. |
| Supersession metadata (`is_correction`, `corrects_record`, etc.) | NOT IMPLEMENTED | No correction stream in scope. |
| Point-in-time queries | NOT REQUIRED | Single snapshot — there is nothing to time-travel between at the data layer. |

The `record_id` convention (UNITID prefix `ead-`) is single-key and assumes one record per institution per load. This is consistent with single-year scope.

---

## Forward-Looking Note (for a hypothetical future multi-year EADA spec)

If a follow-up spec extends EADA to multi-year coverage, the existing schema is **partially** prepared but will need work:

1. **Partition key:** `reporting_year` is the natural partition key. Already present on the schema as a stamp column — promote it to a partition column when multi-year lands.

2. **Record ID collision:** the current `record_id` format `ead-{UNITID}` is **single-year-only**. Two loads for the same UNITID across different years would collide on `record_id`. A multi-year spec must change the convention to `ead-{reporting_year}-{UNITID}` (or equivalent compound key) before the second year is ingested. This is a breaking change to the bronze contract and must be specced explicitly.

3. **Valid time modeling:** EADA reports describe an academic year (e.g., 2022–07–01 to 2023–06–30). A multi-year spec should add explicit `valid_from` / `valid_to` DATE columns at base, derived from `reporting_year`, so downstream queries can filter by validity period rather than by the stamp column alone.

4. **Amendments:** EADA does occasionally republish prior-year data. A multi-year spec needs an amendment-handling strategy — likely an `is_correction` / `corrects_record` pair plus reliance on Iceberg snapshots for full history. Out of scope here.

5. **Cross-source FTE join:** the spec already cross-joins `base.ipeds_finance` for FTE at base. In a multi-year world, that join must match on (`UNITID`, `reporting_year`) — both base tables would need aligned multi-year coverage.

None of this is required for the current spec. It is documented here so a future temporal-modeler pass has a starting point and does not have to re-derive it.

---

## Decisions Logged

- **Decision:** Skip bitemporal modeling at bronze for this spec.
  **Rationale:** Single-year snapshot scope; multi-year SCD2 explicitly forbidden by the Claude Code Prompt OUT OF SCOPE block.
- **Decision:** Document the `record_id` collision risk as a forward-looking constraint rather than fix it now.
  **Rationale:** Fixing it now would require a schema decision the current spec does not authorize. Better to flag it for the future spec that actually needs multi-year coverage.

---

## Audit Trail

- Spec reference: `docs/specs/full-pipeline-eada.md` §4 (raw.eada schema), Claude Code Prompt OUT OF SCOPE (line 81).
- Domain context: `governance/domain-context.md` (EADA cadence = annual).
- Sibling temporal artifacts (for reference): `governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md`, `silver-base-college-scorecard-institution-temporal.md`.
