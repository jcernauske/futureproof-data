## Temporal Design: silver-base-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @temporal-modeler
**Domain:** Higher Education Outcomes — Institution-Level Cost of Attendance and Net Price
**Upstream Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Bronze Temporal Assessment:** governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md
**Bitemporal Required:** NO
**Decision:** SKIP bitemporal modeling at Silver. Inherit snapshot semantics from Bronze. Standard provenance metadata is sufficient.

---

### Purpose

This is a confirming assessment for the Silver-layer table `base.college_scorecard_institution`. It reaffirms and inherits the conclusions of the Bronze temporal assessment. No new temporal characteristics are introduced by the Silver transform, so no new temporal modeling work is required.

---

### Inherited Temporal Characteristics

Silver consumes the Bronze table one-to-one on UNITID with cleaning, typing, and null normalization. None of the Silver transform steps introduce a time-series dimension, amendment tracking, or valid-time semantics.

| Characteristic | Silver Assessment | Inherited From Bronze? |
|---------------|-------------------|-----------------------|
| Data shape | Single point-in-time snapshot (Most-Recent-Cohort) | Yes |
| Time-series dimension | None | Yes |
| Valid time indicators | None surfaced by source | Yes |
| Grain | One row per institution (UNITID) | Yes |
| Refresh cadence (current spec) | One-shot transform, no incremental | Yes |
| Amendment mechanism | Full-file replacement upstream; Iceberg snapshot replacement downstream | Yes |
| Supersession semantics | None within a snapshot | Yes |

No Silver-specific temporal behaviors emerge from the clean/type/normalize operations.

---

### Valid Time Design

**No explicit valid time columns at Silver.** Consistent with Bronze, the source does not carry a `valid_from` / `valid_to` period, and fabricating one at Silver would invent a semantic the upstream data cannot honor.

---

### Transaction Time Strategy

**Standard Iceberg snapshot metadata is sufficient.** The Silver schema preserves the provenance fields:

| Field | Type | Role |
|-------|------|------|
| `source_load_date` | date | Carries forward the Bronze `load_date` for lineage |
| `ingested_at` | timestamp | Silver write transaction-time marker |

Combined with native Iceberg snapshot history on `base.college_scorecard_institution`, this provides full transaction-time provenance without any bitemporal columns.

---

### Correction / Amendment Handling

**Not applicable for this spec.** Corrections follow the same pattern documented in the Bronze assessment: re-run the upstream ingestor, re-run the Silver transform, Iceberg creates a new snapshot, prior snapshot is recoverable via time travel. No per-row supersession flags or `corrects_record` linkage are introduced at Silver.

---

### Point-in-Time Query Support

**Not required by any downstream consumer.** Gold (`consumable.career_outcomes`) LEFT JOINs Silver on `unitid` and reads current cost-of-attendance fields only. No downstream service asks "what did we know about institution X's cost on date Y?" If that need ever arises, native Iceberg time travel is available against the Silver snapshot history without schema change.

---

### Schema Changes

**None required beyond what the Silver spec already defines.** The Silver table carries `source_load_date` and `ingested_at` for provenance. No additional columns for valid time, supersession, correction linkage, or amendment tracking are required for this spec.

---

### Future Trigger for Reassessment

The Silver-layer reassessment trigger mirrors Bronze:

- If an annual refresh pipeline is added for College Scorecard institution data, the SCD approach must be revisited at both Bronze and Silver.
- **SCD Type 1 (overwrite-current-state):** Correct if consumers only need current cost; Iceberg snapshots preserve audit history for free.
- **SCD Type 2 (valid_from / valid_to per institution-year):** Required if any spec requests year-over-year cost trends, cohort-historical ROI, or "cost at time of matriculation" semantics. Silver would gain `valid_from`, `valid_to`, `is_current` columns and the transform would produce a bitemporal delta per annual load.

Until a refresh spec is authored, annual full-replace remains the correct pattern and no work is needed at Silver.

---

### Recommendation

**No temporal modeling work needed at Silver.** The Bronze assessment governs. Proceed directly to DQ rule authoring, entity resolution review, and Silver transform implementation. This document exists to formally record the inheritance so the audit trail is complete and the Silver-layer decision is explicit rather than implicit.

---

### Trade-offs Considered

| Trade-off | Resolution |
|-----------|------------|
| Introduce valid-time columns at Silver even though Bronze has none? | Rejected. Silver should not fabricate semantics absent from upstream. |
| Add `is_current` / `effective_from` at Silver as forward-compatible scaffolding? | Rejected. YAGNI. Adding SCD columns that are always trivially `TRUE` / `load_date` creates maintenance burden and false affordance without solving a real query need. |
| Skip the Silver assessment document because Bronze already covered it? | Rejected. Explicit inheritance recorded here makes future reassessment easier and keeps the governance trail complete per zone. |

---

### Audit Trail

- Bronze assessment referenced: `governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md`
- Silver spec referenced: `docs/specs/silver-base-college-scorecard.md` (institution-scope portion)
- Decision: NO bitemporal schema at Silver. Inherit from Bronze.
- Reassessment trigger: annual refresh pipeline or any consumer need for year-over-year / cohort-historical cost analysis.

---

*— End of Silver Temporal Assessment —*
