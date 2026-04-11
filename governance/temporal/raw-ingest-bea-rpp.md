# Temporal Strategy: raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @temporal-modeler
**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Domain:** Education / Career Guidance — state-level cost-of-living reference
**Zone Coverage:** `raw.bea_rpp` → `base.bea_rpp` → `consumable.regional_price_parities`
**Decision:** SKIP bitemporal modeling. Static single-year reference table.

---

## TL;DR

BEA Regional Price Parities is a **static single-year reference table**. There is no valid-time dimension to model, no amendment stream to preserve, and no point-in-time query requirement. The `data_year` column is **provenance**, not a temporal dimension. Downstream agents (@dq-rule-writer, @primary-agent for Silver/Gold, @semantic-modeler) should treat this source as a flat lookup dimension keyed by `state_fips`.

**No bitemporal modeling. No SCD2. No effective-dating. No history preservation for the hackathon MVP.**

---

## Grain

| Zone | Table | Grain | Dedup Key |
|------|-------|-------|-----------|
| Raw (Bronze) | `raw.bea_rpp` | One row per geographic entity (GeoFips) per load | `[geo_fips]` |
| Silver | `base.bea_rpp` | One row per state | `[state_fips]` |
| Gold | `consumable.regional_price_parities` | One row per state | `[state_fips]` |

**Effective temporal grain:** one row per `state_fips`, snapshot-per-year. All 51 rows in the current load carry the identical `data_year = 2024`.

---

## Valid Time

**Not modeled.** There is no `valid_from` / `valid_to` column.

Rationale (from `governance/domain-context.md`, BEA RPP → Temporal Patterns):

> "BEA publishes one RPP per state per calendar year. This ingest loads `data_year = 2024` only; all 51 rows carry the identical year. There is no within-year variation, no monthly/quarterly cadence, no intra-year revisions published mid-year."

> "Model as a static reference table keyed by `state_fips`, with `data_year` as a load-time column, not a time-series dimension. No slowly-changing-dimension handling required for the hackathon MVP. @temporal-modeler can SKIP complex temporal modeling for this source."

The domain context is explicit and authoritative; this document records the decision and cites it.

### Why `data_year` is NOT valid time

`data_year` identifies the BEA publication year, not a validity window:

- It is constant across the entire table (all 51 rows = 2024).
- It does not partition rows into overlapping versions.
- It carries no `valid_to` counterpart.
- It is semantically equivalent to "which BEA release this row came from" — i.e., provenance.

A valid-time dimension would require at minimum two columns (`valid_from`, `valid_to`) and a reason to query across versions. Neither exists here.

### Why there is no amendment stream

From domain context (BEA RPP → Amendment / Correction Patterns):

> "None observed. BEA does occasionally revise historical RPP series when it updates its underlying price index methodology (typically every ~5 years), but within a given publication year the data is static. A revision, when it occurs, replaces the entire historical series rather than emitting per-row amendments. For this pipeline, revisions are handled via full refresh — no merge, no upsert, no correction-tracking columns needed."

Full-refresh revisions are indistinguishable (at the row level) from a fresh annual load. There is no per-row amendment to track, so there is no justification for `corrects_record`, `is_correction`, or supersession metadata columns on the fact rows.

---

## Transaction Time

**Handled entirely by Iceberg snapshots.** No transaction-time columns are required on the table schema.

### Snapshot Strategy

| Event | Snapshot Action | Rationale |
|-------|----------------|-----------|
| Initial load (2024) | New snapshot | Baseline state |
| Annual refresh (2025, 2026, ...) | New snapshot (full replace) | See supersession section below |
| Live BEA API replaces current CSV-cache estimates | New snapshot (full replace) | Same supersession behavior as an annual refresh |
| BEA methodology restatement | New snapshot (full replace) | Domain context: "replaces the entire historical series" |
| DQ correction (e.g., fix a wrong state row) | New snapshot (full replace) | Corrections are applied by re-running the ingest, not by targeted updates |

Iceberg time travel is sufficient to answer "what did we know on date X?" without any additional schema machinery. If a downstream consumer ever needs to see a prior snapshot (e.g., to compare the current load to the pre-live-API estimates load), they query the Iceberg snapshot history for `raw.bea_rpp`.

### `ingested_at` and `load_date`

Both columns are **batch stamps**, not event times:

> (domain context) "All 51 rows share identical `ingested_at` and `load_date` values because the load is a single batch. These columns are load-batch identifiers, not per-row event times. Do not model `ingested_at` as an event-time column. Treat it as provenance metadata."

Downstream agents should NOT use these columns for temporal filtering, windowing, or effective-dating logic.

---

## Supersession Grain

**Supersession grain: the entire table.** When a new `data_year` arrives (or a revised load of the current year arrives), the full 51-row table is replaced in a new Iceberg snapshot.

### Decision: Replace, do not preserve multi-year history (hackathon MVP)

**Recommended choice:** REPLACE. On each refresh, all 51 rows are overwritten. The new snapshot contains exactly 51 rows, all stamped with the new `data_year`. Prior years are NOT retained as additional rows in the active table.

**Rationale:**

1. **Only one year is needed for the product.** The FutureProof purchasing-power feature uses the most recent year to adjust salaries to present-day cost of living. Historical RPP trends are not a hackathon deliverable.
2. **No current consumer queries across years.** The MCP tools (`get_regional_price_parity`, `compare_purchasing_power`) and Gold consumable (`consumable.regional_price_parities`) all assume a single-year lookup keyed by state. There is no "as of date" parameter anywhere in the MCP interface.
3. **Iceberg snapshots already preserve full history.** If a consumer later needs the 2024 values after a 2025 refresh, Iceberg time travel on `raw.bea_rpp` recovers them without any schema change. Replacement does not destroy history; it only removes prior years from the active query surface.
4. **Simplest DQ posture.** DQ rules can assert `row_count = 51` and `data_year = <current year>` without any multi-year branching logic.
5. **Matches domain behavior.** BEA itself publishes one active year at a time and treats new releases as supersession, not append.

**Mechanical implementation:** The ingestor writes all 51 rows per load. The Iceberg write mode is overwrite-by-partition (if partitioning by `data_year`) or full-table overwrite (if unpartitioned). Either produces a new snapshot with the superseding rows.

### Alternative (post-hackathon / production): append-with-year

If and when the product gains a multi-year view (e.g., "RPP trend over 10 years" visualization, or a "historical salary comparison" feature), switch to append-with-year:

- Partition `raw.bea_rpp` and `base.bea_rpp` by `data_year`.
- On refresh, append new `data_year` rows instead of overwriting.
- Active row count becomes `51 × N_years`.
- Add a `data_year = MAX(data_year)` filter to the Silver → Gold transformer, or expose `data_year` as a query parameter in the MCP tools.
- Update DQ row-count rule from `= 51` to `= 51 × N_distinct_years` and add a "most recent year has 51 rows" rule.

From domain context:

> "If the product needs to compare RPP trends across years post-hackathon, switch to an append-with-year strategy and partition by `data_year`. Not required for MVP."

This migration is **non-breaking for the MCP interface** — the current tools continue to work if they always select `WHERE data_year = (SELECT MAX(data_year) FROM base.bea_rpp)`. The only schema change is the partitioning and the DQ row-count rule.

### NOT recommended: SCD2 / effective-dating

SCD2 (with `valid_from`, `valid_to`, `is_current`) is the wrong pattern here even in the append case, because:

- BEA does not amend individual state values mid-year. There is no within-year fact evolution to track.
- Cross-year comparisons are cleanly expressed by `data_year`, which is a discrete attribute, not a continuous interval.
- SCD2 overhead (closing out old rows, maintaining `is_current`) buys nothing over partition-by-year.

---

## Point-in-Time Query Support

**Not required by any current consumer.** None of the following exist in scope:

- No MCP tool accepts an `as_of_date` parameter.
- No Gold consumer joins by historical RPP.
- No regulatory requirement to reproduce past answers.

If a future consumer needs point-in-time answers ("what did we tell the user about CA purchasing power on 2026-03-01?"), the answer is provided by Iceberg snapshot time travel on `raw.bea_rpp` or `consumable.regional_price_parities`, not by any schema feature. Example pattern (illustrative, not implemented):

```sql
-- "What did we know about California's RPP on 2026-03-01?"
SELECT state_abbr, rpp_all_items, purchasing_power_multiplier
FROM base.bea_rpp
FOR SYSTEM_TIME AS OF TIMESTAMP '2026-03-01 00:00:00'
WHERE state_fips = '06';
```

This is the Iceberg-native answer and requires zero schema changes.

---

## Schema Impact

**No new columns. No modifications to the spec schema.**

The spec schema already contains the correct minimal set for a static reference table:

- `data_year` — provenance (single value, currently 2024)
- `ingested_at` — batch stamp (provenance metadata)
- `load_date` — batch stamp (provenance metadata)
- `source_method` — provenance (`bea_api` or `csv_cache`)
- `source_url` — provenance

None of these are temporal dimensions in the bitemporal sense. They are metadata. The temporal-modeler adds nothing on top.

---

## Temporal DQ Rules

### Rules recommended (already in the spec)

The spec's existing DQ rules already cover the temporal posture correctly:

- `data_year = 2024 for all rows` (P0) — asserts single-year constancy
- `row count: exactly 51` (P0) — asserts the full-replacement grain
- `state_fips uniqueness` (P0) — asserts the one-row-per-state invariant under replacement

### Additional temporal DQ rules

**None recommended for the hackathon MVP.**

Specifically, @dq-rule-writer should NOT add any of the following, because they would either be vacuous (no multi-year data) or would conflict with the replacement supersession strategy:

| Rule type | Why to skip |
|-----------|-------------|
| `valid_from <= valid_to` | No valid-time columns exist. |
| `no overlapping validity windows per state` | Same reason. |
| `exactly one is_current=true per state` | No SCD2. |
| `data_year strictly monotone on refresh` | Replacement model — old year is gone, so there's nothing to compare against in the active table. (Iceberg snapshot diffing handles this out-of-band.) |
| `ingested_at within last N days` | The spec's freshness SLA is annual. A staleness rule would fire 11 months out of 12 and is better expressed as a contract SLA, not a DQ rule. |
| `load_date = CURRENT_DATE` on every query | This is not a temporal rule; it would break point-in-time query replay. Omit. |

### Rule @dq-rule-writer should ADD (recommended, temporal-flavored)

One rule is worth adding to harden the supersession contract:

- **`data_year` cardinality = 1** (P0): `SELECT COUNT(DISTINCT data_year) = 1`. Asserts that the table is in its single-year replacement state. If an accidental append produces a second year, this fires and the operator is alerted to either complete the migration to append-with-year or roll back. Protects the downstream assumption that `WHERE data_year = 2024` is equivalent to "all rows".

This rule replaces the need for any richer temporal DQ during the MVP and forces an explicit decision if the supersession model ever changes.

---

## Handoff Notes for Downstream Agents

| Agent | What to know |
|-------|--------------|
| @dq-rule-writer (Silver) | Do NOT add bitemporal DQ rules. Add the one `data_year cardinality = 1` rule above. Keep the spec's `data_year = 2024` and `row_count = 51` rules verbatim. |
| @dq-rule-writer (Gold) | Same. The Gold consumable inherits the single-year grain. Do not write any "latest year" rule — in replacement mode, every year is the latest year. |
| @primary-agent (Silver build) | Write `base.bea_rpp` with full overwrite semantics. No merge, no upsert, no effective-dating columns. Carry `data_year` through as-is. |
| @primary-agent (Gold build) | Same. The Gold build is a straight projection + derivation from Silver; no temporal logic required. |
| @semantic-modeler | Model `base.bea_rpp` and `consumable.regional_price_parities` as independent reference dimensions, not fact tables. `data_year` is a scalar attribute, not a dimension key. See domain-context.md line 1570: "Model this table as an independent reference dimension, not a fact table." |
| @lineage-tracker | OpenLineage facets: no temporal facets required beyond the standard `SchemaFacet` and `DatasourceDatasetFacet`. No `SymlinksDatasetFacet` for year-partitioning needed until the append-with-year migration. |
| @data-contract-author | Freshness SLA = annual, matching BEA publication cadence. No point-in-time replay SLA. Quality tier caveats belong in the contract per the existing Data Provenance Caveat (domain-context.md §BEA RPP → Data Provenance Caveat), not in the temporal facet. |
| @mcp-engineer | MCP tools do NOT need an `as_of_date` parameter. Single-year lookup only. |

---

## Decision Log

| Decision | Rationale | Source |
|----------|-----------|--------|
| Skip bitemporal modeling | Static single-year reference table, no valid-time dimension, no amendments | domain-context.md §BEA RPP → Temporal Patterns (lines 1421-1433) |
| Skip SCD2 / effective-dating | No within-year fact evolution; refreshes are full-table replace | Same |
| Supersession grain = full table | Only one year needed; MCP tools assume single-year; Iceberg snapshots preserve history for free | Spec §"Update cadence: Annual"; MCP tool signatures |
| `data_year` is provenance, not a dimension | Constant across the table; identifies publication batch | domain-context.md line 1427 |
| `ingested_at` / `load_date` are batch stamps | All 51 rows share identical values per load | domain-context.md line 1429 |
| Defer append-with-year to post-hackathon | No current consumer needs multi-year; non-breaking migration path documented | Spec §"Freshness: Static for hackathon" |
| Add `COUNT(DISTINCT data_year) = 1` DQ rule | Hardens the supersession contract; forces explicit decision if model changes | Temporal-modeler judgment |

---

## References

- Spec: `docs/specs/raw-ingest-bea-rpp.md`
- Domain context: `governance/domain-context.md` — BEA RPP section (starts line ~1395), Temporal Patterns (lines 1421-1433), Data Provenance Caveat (lines 1435-1462)
- EDA: `governance/eda/raw-bea-rpp-eda.md` (per domain context cross-reference)
- Audit trail: `governance/audit-trail/2026-04-10-temporal-modeler-raw-bea-rpp.md`

*— End of Temporal Strategy —*
