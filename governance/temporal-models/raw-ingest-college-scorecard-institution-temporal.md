## Temporal Design: raw-ingest-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @temporal-modeler
**Domain:** Higher Education Outcomes — Institution-Level Cost of Attendance and Net Price
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Bitemporal Required:** NO
**Decision:** SKIP bitemporal modeling. Use standard Iceberg snapshot metadata only.

---

### Temporal Characteristics

| Characteristic | Assessment |
|---------------|-----------|
| Data shape | Single point-in-time snapshot (Most-Recent-Cohorts-Institution.csv) |
| Time-series dimension in source | None — no date/period columns in the source data |
| Valid time indicators | None — the source reports "the most recent reporting year available" with no embedded year field |
| Grain | One row per institution (UNITID), 3,039 rows, all sharing the same load event |
| Refresh cadence (current spec) | One-shot ingest. No incremental, no scheduled refresh in scope. |
| Amendment mechanism in source | Annual full-file replacement by the Department of Education. No in-period corrections. |
| Supersession semantics | None within a snapshot. Future annual files supersede the entire previous file. |

The data describes cost structure *as of now* from the publisher's perspective, with no historical or valid-time dimension surfaced in the file itself. There is no business requirement — current or foreseeable within this spec — to answer "what did we know about institution X's cost on date Y?" or "what was institution X's cost during period P?"

---

### Valid Time Design

**No explicit valid time columns required.**

The source data does not carry a valid-from / valid-to period. Adding synthetic valid-time columns would be fabricating a semantic we cannot honor from the source. The publisher's intent is "current cost snapshot" — a single implicit validity period equal to the current reporting year.

---

### Transaction Time Strategy

**Standard Iceberg snapshot metadata is sufficient.**

The Bronze schema already specifies:

| Field | Type | Role |
|-------|------|------|
| `ingested_at` | timestamp | Transaction-time marker — when the row was written to Iceberg |
| `load_date` | date | Coarse-grained load partition marker |
| `source_url` | string | Provenance of the download |
| `source_method` | string | "bulk_csv_download" |

These fields, combined with Iceberg's native snapshot history, provide full provenance for the initial load. Each Iceberg snapshot created by this ingestor represents a full-table write; there is no need for per-row supersession metadata, `corrects_record` references, or amendment flags.

---

### Correction / Amendment Handling

**Not applicable for this spec.**

The spec defines a single initial load. If a data quality correction is needed (e.g., re-downloading the file, fixing a parse bug), the standard Brightsmith pattern applies:

1. Re-run the ingestor
2. Iceberg creates a new snapshot
3. Previous snapshot remains recoverable via Iceberg time travel

No application-level supersession columns are required to support this.

---

### Point-in-Time Query Support

**Not required by any downstream consumer.**

- `consumable.career_outcomes` (Gold) LEFT JOINs `base.college_scorecard_institution` on `unitid` and reads "current cost" only.
- The ROI formula `earnings / (net_price_annual × 4 × loan_pct)` consumes a single current value per institution.
- The MCP server, backend services, and CLI never ask "what was the cost on date X."

If, at some future point, a consumer needs to see prior-snapshot state, Iceberg time travel (`AT (SNAPSHOT => ...)` or `AT (TIMESTAMP => ...)`) is available natively without any schema change.

---

### Schema Changes

**None required.** The Bronze and Silver schemas as specified already contain the necessary provenance fields:

- Bronze: `ingested_at`, `source_url`, `source_method`, `load_date`
- Silver: `source_load_date`, `ingested_at`

No additional columns for valid time, supersession, correction linkage, or amendment tracking are needed for this spec.

---

### Future Considerations

If an annual refresh pipeline is built later, the design decision must be revisited. Two options should be weighed at that point:

| Option | When To Pick | Implication |
|--------|--------------|-------------|
| **SCD Type 1 (overwrite, current-state only)** | If consumers only ever need "current cost" and historical cost changes are uninteresting | Simplest. Lose year-over-year comparisons in the data itself, but Iceberg time travel preserves prior snapshots for audit. |
| **SCD Type 2 (add valid_from / valid_to per institution-year)** | If consumers need to compare cost trends over time or answer "what did ROI look like in cohort year N" | Requires schema evolution: add `valid_from`, `valid_to`, `is_current` columns. Each annual load produces a bitemporal delta instead of a full overwrite. |

**Recommended trigger for reassessment:** When any spec requests year-over-year cost trend analysis, cohort-historical ROI, or "cost at time of matriculation" semantics. Until then, annual full-replace (Type 1) remains the right pattern.

---

### Recommendation

**Standard Iceberg metadata is sufficient for this spec.** No bitemporal schema. No valid-time columns. No supersession metadata. Skip @temporal-modeler work beyond this assessment and proceed directly to DQ rule authoring and Silver transform implementation.

---

### Trade-offs Considered

| Trade-off | Resolution |
|-----------|------------|
| Add synthetic valid-time columns defensively? | Rejected. Fabricating validity periods the source does not support invites false confidence and downstream confusion. |
| Add `effective_date` pinned to `load_date`? | Rejected. `load_date` already carries this meaning for provenance. Duplicating it as `effective_date` implies validity semantics the source does not guarantee. |
| Model annual refresh support now? | Rejected. YAGNI for the hackathon MVP. Reassess when a refresh spec is authored. |
| Track supersession at row level (e.g., `is_current`, `superseded_at`)? | Rejected. With a single snapshot and annual full-replace, Iceberg snapshot history is the correct supersession mechanism, not per-row flags. |

---

*— End of Temporal Assessment —*
