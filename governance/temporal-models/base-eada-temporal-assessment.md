# Temporal Design: base.eada (Silver Zone)

**Date:** 2026-04-30
**Agent:** @temporal-modeler
**Spec:** docs/specs/full-pipeline-eada.md (§5 Silver Zone)
**Domain:** Higher-education athletics finance (EADA — Equity in Athletics Disclosure Act)

---

## Verdict: NOT APPLICABLE

Bitemporal modeling is **not applicable** to `base.eada` for this spec. No bitemporal columns, no SCD2 history, no supersession metadata, and no Iceberg snapshot strategy beyond the default per-load behavior are required.

---

## Rationale

### 1. Single-year scope

`bronze.eada` carries a single survey year (`reporting_year = 2022`). With one temporal point, there is no valid-time interval to model — `valid_from` / `valid_to` would degenerate to a constant pair on every row, adding storage and query cost with zero information gain.

### 2. Spec explicitly forbids multi-year history

Spec §5 (Silver Zone) lists multi-year SCD2 / bitemporal history as **OUT OF SCOPE**. Adding `valid_from`, `valid_to`, `is_current`, or `superseded_by` columns would violate the spec's scope boundary and require a CAB decision plus a new spec to introduce.

### 3. No corrections or amendments in scope

EADA submissions can be re-published by the Department of Education (institutions occasionally restate prior-year disclosures), but:
- This spec ingests only the 2022 vintage as published at the time of the bronze pull.
- There is no correction-handling requirement in §5.
- Re-pulls of the same vintage are handled by Iceberg's default snapshot-per-write semantics — no application-level supersession metadata is needed.

### 4. Transaction time is sufficient via Iceberg defaults

Any operational need to answer "what did we know on date X?" for `base.eada` is satisfied by Iceberg snapshot time travel on the table itself. No custom snapshot strategy, no `recorded_at` column, and no audit columns beyond the standard Brightsmith load-metadata fields are required for a single-vintage table.

### 5. Reporting-year is a dimensional attribute, not a temporal axis

`reporting_year` should be carried as a normal `INTEGER` column on `base.eada` for filterability and future multi-year extension, but it is treated as **dimensional**, not as the start/end of a validity interval. When/if a future spec adds 2023+ vintages, that spec will revisit this assessment and introduce SCD2 if (and only if) restatement semantics are in scope at that time.

---

## Schema Implication

`base.eada` should include `reporting_year INTEGER NOT NULL` as a plain column (sourced from `bronze.eada.reporting_year`). It should **not** include:

- `valid_from` / `valid_to`
- `is_current` / `effective_from` / `effective_to`
- `superseded_by` / `corrects_record` / `is_correction`
- Any custom transaction-time columns beyond Brightsmith load metadata

---

## Iceberg Snapshot Strategy

Default Brightsmith behavior applies: one snapshot per pipeline write. No correction-driven snapshots, no compaction-tier rules specific to temporality. If 2022 data is re-pulled, the resulting overwrite produces a new snapshot and the prior snapshot remains queryable via Iceberg time travel — sufficient for any reproducibility requirement in this spec's scope.

---

## Re-evaluation Triggers

This assessment must be revisited when **any** of the following becomes true:

1. A new spec adds a second EADA vintage (2023, 2024, ...) to `base.eada` or to a Gold-zone consumer that joins across years.
2. A spec introduces correction/restatement handling for EADA submissions.
3. A Gold-zone consumer needs as-of-date queries against EADA finance figures (e.g., "what did the 2022 men's basketball expense look like as of our Q3 2024 publish?").
4. CIP-SOC or institution dimension tables that join to EADA acquire SCD2 semantics that propagate downstream.

Until one of those triggers fires, `base.eada` remains a non-temporal Silver-zone table.

---

## Coordination

- **@semantic-modeler** owns non-temporal schema design for `base.eada` (column types, naming, FK relationships to institution registry).
- **@entity-resolver** owns institution matching against the IPEDS/UNITID registry — orthogonal to this assessment.
- **@dq-author** writes DQ rules; no temporal-coverage rules are needed for a single-vintage table beyond a `reporting_year = 2022` invariant.

---

## Audit Trail Reference

Decision: bitemporal modeling NOT APPLICABLE for `base.eada` under spec `docs/specs/full-pipeline-eada.md` §5.
Rationale: single-vintage scope (2022 only); multi-year SCD2 explicitly out-of-scope; no in-scope correction semantics; Iceberg defaults sufficient.
Trade-offs considered: pre-emptive SCD2 columns rejected — premature complexity, violates spec scope, and risks locking in a schema before correction semantics are understood.
