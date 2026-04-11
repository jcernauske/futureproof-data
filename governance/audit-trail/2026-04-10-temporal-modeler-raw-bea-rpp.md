# Audit Trail: @temporal-modeler — raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @temporal-modeler
**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Target table:** `raw.bea_rpp` (Bronze) → `base.bea_rpp` (Silver) → `consumable.regional_price_parities` (Gold)
**Artifact produced:** `governance/temporal/raw-ingest-bea-rpp.md`

---

## Summary

Documented the explicit decision to **skip bitemporal modeling** for the BEA RPP pipeline. This is a static single-year reference table. No valid-time dimension exists in the data; no per-row amendments are published by BEA; no downstream consumer requires point-in-time query support beyond what Iceberg snapshot time travel already provides.

The temporal design is being recorded explicitly (rather than simply omitted) so that @dq-rule-writer and the Silver/Gold @primary-agent have a canonical artifact to cite in their own deliverables, and so that any future agent who questions the absence of SCD2 / effective-dating columns has a clear rationale on file.

---

## Inputs Reviewed

| File | Purpose |
|------|---------|
| `docs/specs/raw-ingest-bea-rpp.md` | Authoritative spec. Read fully. Key signals: annual cadence, 51 rows, `data_year = 2024` constant, freshness SLA "Static for hackathon". |
| `governance/domain-context.md` (BEA RPP section, lines 1395-1570) | Domain authority. Read Temporal Patterns (1421-1433), Amendment / Correction Patterns (1431-1433), Data Provenance Caveat (1435-1462), Known Edge Cases (1465-1474). |

The domain context was unambiguous and explicitly directed @temporal-modeler to skip complex temporal modeling (line 1427: "@temporal-modeler can SKIP complex temporal modeling for this source. Document the skip."). This audit trail and the accompanying temporal strategy document are that documented skip.

---

## Decisions

### D1. Skip bitemporal modeling

**Decision:** No `valid_from` / `valid_to` columns. No SCD2. No effective-dating. No correction-tracking columns (`is_correction`, `corrects_record`).

**Rationale:**
- BEA publishes one RPP value per state per calendar year, with no intra-year variation and no per-row amendments.
- Mid-year revisions, when they occur (~every 5 years on methodology updates), replace the full historical series — so even the amendment case collapses to "full refresh", which is indistinguishable at the row level from a normal annual load.
- No downstream consumer (MCP tools, Gold transformer, Gemma agent) asks "what did this state's RPP look like on date X?". The product is single-year-only.
- The domain-context author already surveyed this and directed the skip.

**Trade-off considered:** Adding a minimal `valid_from` / `valid_to` pair "just in case" a future consumer wants temporal queries. Rejected because (a) YAGNI, (b) the columns would be degenerate (valid_from = 2024-01-01, valid_to = 2024-12-31, constant across the table), and (c) Iceberg snapshot time travel already provides the escape hatch at zero schema cost.

### D2. Supersession grain = full table

**Decision:** On refresh (new `data_year`, revised BEA publication, or live BEA API replacing current CSV-cache estimates), the entire 51-row table is replaced in a new Iceberg snapshot. Prior years are NOT retained as additional rows in the active table.

**Rationale:**
- Only the most recent year is needed for the FutureProof purchasing-power feature.
- MCP tool signatures (`get_regional_price_parity(state)`, `compare_purchasing_power(salary, state_a, state_b)`) have no `as_of_date` parameter.
- Iceberg snapshot history already preserves replaced rows — replacement does not destroy them, it only removes them from the active query surface.
- DQ rules remain simple: `row_count = 51`, `data_year = <current>`, `state_fips uniqueness`.
- Matches BEA's own release model (one active year at a time).

**Alternative considered:** Append-with-year partitioning. Rejected for the hackathon MVP but documented as a non-breaking migration path for production: partition by `data_year`, update DQ row-count rule from `= 51` to `= 51 × N_years`, add `WHERE data_year = MAX(data_year)` to Silver → Gold transformer. This migration does not change the MCP contract.

**Trade-off considered:** Preserving multi-year history from day one (append mode) to avoid a later migration. Rejected because (a) no consumer needs it today, (b) the migration is straightforward and non-breaking, and (c) the "estimates-in-place" provenance caveat (43 of 51 current rows are placeholder values) means retaining the current load as permanent history would be actively misleading — a live BEA API refresh that corrects estimates should cleanly supersede, not leave a ghost historical row.

### D3. `data_year` is provenance, not a temporal dimension

**Decision:** Treat `data_year` as a provenance/batch-identifier column, same semantic class as `source_method`, `source_url`, `load_date`, `ingested_at`. Do not model it as a slowly-changing dimension key, do not partition by it (for the MVP), do not filter by it in consumer queries (all rows share the same value).

**Rationale:**
- All 51 rows in the current load carry the identical value (`2024`).
- It has no `data_year_from` / `data_year_to` counterpart.
- It identifies the BEA publication batch, not a validity window.
- The domain context author is explicit on this point (line 1427).

### D4. `ingested_at` and `load_date` are batch stamps

**Decision:** Explicitly flag these two columns as batch stamps (not per-row event times) so downstream agents do not accidentally use them for temporal filtering or windowing.

**Rationale:** Both columns carry identical values across all 51 rows of a given load. They are load-batch identifiers. Per domain context line 1429: "Do not model `ingested_at` as an event-time column. Treat it as provenance metadata."

### D5. Point-in-time queries handled by Iceberg snapshots, not schema

**Decision:** If a future consumer ever asks "what did we know on date X?", the answer is `SELECT ... FOR SYSTEM_TIME AS OF TIMESTAMP ...` against the Iceberg table, not any bespoke schema feature.

**Rationale:** Iceberg time travel is free and requires zero schema changes. Building an in-table versioning scheme to duplicate what Iceberg already provides would be pure overhead.

### D6. One new temporal-flavored DQ rule

**Decision:** Recommend @dq-rule-writer add exactly one new rule beyond what the spec already lists:

- `COUNT(DISTINCT data_year) = 1` (P0) on `raw.bea_rpp` and `base.bea_rpp`.

**Rationale:** This hardens the supersession contract. If an accidental append (e.g., from a mis-configured ingestor run, or a future append-with-year migration that wasn't fully propagated) produces a second year, this rule fires immediately. It also forces any future change to the supersession model to be an explicit decision (rewrite the rule) rather than a silent drift.

All other spec DQ rules are retained as-is. No additional temporal rules (e.g., `valid_from <= valid_to`, SCD2 invariants, staleness windows) are recommended. See the temporal strategy document for the full list of rules explicitly NOT recommended and why.

---

## Domain-Specific Considerations

- **Estimates-in-place provenance caveat:** 43 of the 51 current rows are primary-agent-generated placeholder values, per the Data Provenance Caveat in domain-context.md (lines 1435-1462). When the live BEA API replaces these estimates, the domain-context author explicitly classifies this as a **data correction, not a schema change** (line 1461). The supersession-by-replacement strategy handles this cleanly: the new snapshot fully supersedes the estimates, Iceberg time travel preserves them for audit, and no amendment-tracking columns are needed.
- **Iowa / Oklahoma tie at 87.8:** Not a temporal concern but worth flagging — any temporal uniqueness rule keyed on `(state_fips, rpp_all_items)` would false-positive because two distinct states share a value. Keep uniqueness scoped to `state_fips` only.
- **DC at FIPS 11:** Not a temporal concern, but the full-table replacement supersession ensures that any refresh that accidentally drops DC would be caught by the spec's `row_count = 51` rule immediately, not silently drift into a 50-row table over time.
- **BEA methodology restatements (~5 year cadence):** When BEA revises the underlying price index methodology and republishes prior years, we will absorb this as a full-table refresh of the current `data_year`. No per-row amendment machinery is needed. If and when the product adopts multi-year trends, the methodology restatement becomes a more significant event (it invalidates the whole historical series), and the append-with-year migration plan would need to add a `methodology_version` provenance column. Out of scope for the MVP; noted here for future reference.

---

## Scope Boundaries Respected

Per the temporal-modeler role definition, this decision covers ONLY temporal design. The following were explicitly NOT touched:

- DQ rule thresholds or content (beyond the one recommended addition) — @dq-rule-writer owns.
- Non-temporal schema design (column types, business glossary mappings, derived fields) — @semantic-modeler owns.
- Entity resolution (state-level identity is stable; there are no lifecycle events to model) — @entity-resolver would also skip this source.
- Data value transformations (purchasing_power_multiplier, cost_tier, adjusted_*k fields) — @primary-agent owns.
- Concept mapping decisions (state_fips → state_abbr lookup) — @semantic-modeler owns.
- Data contract SLA phrasing — @data-contract-author owns.

---

## Artifacts Produced

| Path | Purpose |
|------|---------|
| `governance/temporal/raw-ingest-bea-rpp.md` | Canonical temporal strategy document for the spec. |
| `governance/audit-trail/2026-04-10-temporal-modeler-raw-bea-rpp.md` | This audit trail. |

---

## Handoff

**To @dq-rule-writer (Silver + Gold):** Read `governance/temporal/raw-ingest-bea-rpp.md` §"Temporal DQ Rules". The only additional rule is `COUNT(DISTINCT data_year) = 1` (P0). Do not add bitemporal DQ rules.

**To @primary-agent (Silver build + Gold build):** Read the temporal strategy document. Use full-table overwrite semantics on writes to `base.bea_rpp` and `consumable.regional_price_parities`. Do not add effective-dating columns. Carry `data_year` through unchanged.

**To @semantic-modeler:** Model as an independent single-year reference dimension. No temporal keys.

**To @data-contract-author:** Freshness SLA = annual. No point-in-time replay SLA.

**To @mcp-engineer:** MCP tools remain as specified — no `as_of_date` parameter needed.

---

*— End of Audit Trail —*
