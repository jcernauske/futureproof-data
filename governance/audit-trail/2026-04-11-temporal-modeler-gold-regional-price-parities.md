# Audit Trail: @temporal-modeler — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @temporal-modeler
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Zone:** Gold (Consumable)
**Table:** `consumable.regional_price_parities`
**Output:** `governance/temporal/gold-regional-price-parities.md`
**Parent Temporal Decisions:**
- `governance/temporal/silver-base-bea-rpp.md` (2026-04-10)
- `governance/temporal/raw-ingest-bea-rpp.md` (2026-04-10)

---

## Session Summary

Third and final temporal-modeler pass for the BEA RPP ingest chain. Carries forward the bitemporal posture established at Bronze (2026-04-10) and extended at Silver (2026-04-10) into the Gold consumable layer. One intentional schema simplification at Gold: the Silver two-column batch-stamp pair (`ingested_at` + `source_load_date`) collapses to a single Gold `promoted_at`. No new temporal dimensions, no SCD2, no effective-dating, no new DQ rules.

---

## Inputs Read

- `docs/specs/gold-regional-price-parities.md` — Gold spec (238 lines). Confirmed `promoted_at` is the only Gold-specific batch column, confirmed `data_year` carries through, confirmed `verification_status` carries through per Bronze staff-review Condition 7, confirmed no joins, confirmed no valid-time columns.
- `governance/temporal/silver-base-bea-rpp.md` — parent Silver temporal strategy (246 lines). Confirmed full inheritance pattern from Bronze, confirmed the Silver `ingested_at` / `source_load_date` pair semantics, confirmed the supersession grain = full table.
- `governance/temporal/raw-ingest-bea-rpp.md` — grandparent Bronze temporal strategy (244 lines). Confirmed the root bitemporal skip decision, the replacement-supersession model, the `data_year = provenance not dimension` framing, and the live-API refresh as a full-replace event.

---

## Key Decisions

### 1. Inherit bitemporal-skip decision unchanged

Gold adds **no new temporal dimensions** over Silver. The Silver → Gold transformation is a pure row-shaping operation: 2 verbatim carry-forwards (`verification_status`, `data_year`) plus 5 deterministic derivations (`cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`). None add temporal semantics. No `valid_from` / `valid_to`. No SCD2. No effective-dating. Directly propagates Silver §"Valid Time" and Bronze §"Valid Time".

**Rationale captured in output document §"Valid Time".**

### 2. Collapse Silver batch stamps to a single Gold `promoted_at`

Silver carries a two-column batch-stamp pair (`source_load_date` from Bronze `load_date`, and `ingested_at` from the Silver promote timestamp). Gold intentionally drops both and replaces them with a single `promoted_at`, matching the spec text in §"Gold Transformations" item 4:

> "Provenance columns — `promoted_at` (Gold promotion timestamp) replaces Silver's `ingested_at`/`source_load_date`. `data_year` carries forward as provenance, not a temporal dimension."

This is the one Gold-specific schema change vs. the Silver inheritance pattern. Five rationales captured in the output document §"Why Gold Drops `ingested_at` / `source_load_date`":

1. Gold consumers (MCP tools, frontend salary toggle) do not correlate a Gold row to a specific Silver or Bronze batch inside a query.
2. OpenLineage edges already carry the cross-zone batch identity.
3. Iceberg snapshot history already carries the per-row cross-zone batch identity (time travel on Silver/Bronze using `promoted_at` as a correlating timestamp).
4. The Gold layer is the consumer surface; keeping Gold columns narrow and free of pipeline-internal plumbing has a non-trivial value.
5. Symmetry with the rest of the 14 business-facing Gold columns — two carry-forward lineage columns would dilute consumer-visible signal by ~13%.

The collapse is non-destructive: every piece of information dropped is still recoverable via Iceberg time travel on the Silver table or via the OpenLineage facet graph. This is explicitly documented so that a future schema-migration PR cannot accidentally re-add the columns without consulting @temporal-modeler.

**Trade-off considered:** Keeping the Silver batch stamps at Gold would have made a tiny class of cross-zone lineage joins possible without consulting OpenLineage or Iceberg metadata. Rejected because (a) no current consumer needs such joins, (b) the Gold layer is the consumer-visible schema and should prioritize consumer simplicity, and (c) the spec explicitly chose the collapse.

### 3. `promoted_at` is a batch stamp, not an event time

All 51 rows in a given Gold snapshot share an identical `promoted_at` value because the promote is a single batch — mirroring the Bronze `ingested_at` / `load_date` posture and the Silver `ingested_at` / `source_load_date` posture one and two layers up.

Downstream agents must not use `promoted_at` in `WHERE` filters as if it were an event time, must not use it for windowing or effective-dating, and must not compute SLAs off it without coordinating with the data contract (freshness SLA is annual and lives in the contract).

**Defense documented in output document §"Transaction Time — Gold-Specific Batch Stamp: `promoted_at`" and in handoff notes to @doc-generator, @adversarial-auditor, and @data-contract-author.**

### 4. cost_tier boundary flips are NOT temporal events

Anticipated confusion: when a state's `rpp_all_items` shifts across a refresh (e.g., 102.9 → 103.1), `cost_tier` flips from `average` to `high`. Explicitly ruled this **not** a temporal event at the schema level. It is a cell value change, indistinguishable from an `rpp_all_items` change, recoverable via Iceberg time travel on the Gold table. No SCD2 column required, no `cost_tier_changed_at` column required, no `previous_cost_tier` carry-forward required.

**Documented in output document §"Supersession Grain — cost_tier Boundary Drift — NOT a Temporal Concern".**

This also pre-empts a tempting @chaos-monkey miscategorization: boundary chaos at `rpp = 108.0 / 103.0 / 97.0 / 91.0` is a classification concern, routed to cost_tier tests, not temporal tests. Handoff note to @chaos-monkey explicitly says so.

### 5. `adjusted_Nk` columns are NOT temporal

Same reasoning as cost_tier: pure deterministic functions of the current `purchasing_power_multiplier`. No history column, no "historical drift" DQ rule. Iceberg time travel suffices for "what did adjusted_50k look like last month?" queries.

### 6. No new temporal DQ rules

Every temporal invariant relevant to Gold is already in the spec (§"DQ Rules (Gold)"):

- `data_year = 2024`
- `COUNT(DISTINCT data_year) = 1` (the linchpin replacement-supersession rule, propagated from Silver)
- `row_count = 51`
- `state_fips uniqueness`
- All three `verification_status` rules (allow-list, `= 8` count, 8-state canonical set)
- Passthrough integrity (Gold → Silver join on `state_fips` asserting `rpp_all_items` equality)
- `promoted_at non-null` (P1)

No additional rules warranted. Consistent with the Silver and Bronze "propose none" outcomes.

**Documented in output document §"Temporal DQ Rules — Additional temporal DQ rules proposed by this document — None".**

### 7. Explicit forbidden-rules list at Gold

Extended the Silver forbidden-rules list with two Gold-specific entries:

- `promoted_at > source_load_date` — the `source_load_date` column doesn't exist at Gold; the rule would fail at plan time.
- `Gold promoted_at > Silver ingested_at` (cross-zone) — tautological (Gold promote follows Silver promote) and useless. Belongs in OpenLineage sanity checks, not Gold DQ.
- `cost_tier changed_at tracking` — no history column exists; Iceberg time travel answers the question out-of-band.
- `adjusted_Nk historical drift` — same reasoning.

**Documented in output document §"Temporal DQ Rules — Rules @dq-rule-writer should explicitly NOT add at Gold".**

---

## Cross-Zone Propagation Check

Verified all inherited Silver decisions survive the Gold projection:

| Silver decision | Gold status | Notes |
|---|---|---|
| Skip bitemporal | Inherited | Gold adds zero temporal columns. |
| Skip SCD2 | Inherited | No `valid_from`/`valid_to`/`is_current`. |
| Supersession grain = full table | Inherited | Gold is rebuilt in full every time Silver is rebuilt. |
| `data_year` = provenance | Inherited | Carried verbatim as `int` 2024. |
| Full-replace on refresh / restatement / DQ correction | Inherited | Propagates one more layer. |
| Point-in-time via Iceberg only | Inherited | Gold supports `FOR SYSTEM_TIME AS OF` identically. |
| Batch stamps are lineage metadata, not event times | Inherited | `promoted_at` follows the same posture. |
| `verification_status` is per-row provenance, not temporal | Inherited | Carried forward per Bronze Condition 7. |

All eight Silver decisions carry through unchanged. The only delta is the one Gold-specific schema simplification (two-column batch stamp → single-column).

---

## Domain-Specific Temporal Considerations

BEA RPP is a static single-year reference for Education / Career Guidance. No fiscal quarters, no encounter dates, no measurement timestamps. `data_year` is a scalar provenance attribute, not a dimension. The domain context (`governance/domain-context.md` §BEA RPP → Temporal Patterns) explicitly authorizes @temporal-modeler to SKIP bitemporal modeling for this source; this Gold pass follows through.

No Gold-specific domain temporal considerations introduced. Gold is the consumer-facing layer for MCP tools (`get_regional_price_parity`, `compare_purchasing_power`) and the frontend salary toggle; none of those consumers carry temporal parameters.

---

## Trade-offs Considered and Rejected

1. **Keep Silver batch stamps at Gold.** Rejected — see Decision 2 above. Consumer-schema simplicity wins over a hypothetical lineage-join convenience that no current consumer uses.
2. **Add a `cost_tier_previous` carry-forward column.** Rejected — no consumer needs it, and Iceberg time travel recovers prior cost_tier values without a schema column. Any alerting on cost_tier flips is a snapshot-diff concern, not a schema concern.
3. **Add a `data_year_history` array column.** Rejected — the append-with-year migration is deferred to post-hackathon and lives at Bronze first, per the parent Bronze temporal decision. Gold follows mechanically when the time comes.
4. **Add a P1 "promoted_at within last 400 days" freshness rule.** Rejected — freshness SLA is annual and belongs in the data contract, not DQ. A 400-day rule would fire reliably on stale hackathon data and add noise without signal. The spec's P1 "source table freshness (base.bea_rpp load date within 400 days)" rule already covers this at the upstream side.
5. **Add a cross-zone `Gold promoted_at > Silver ingested_at` DQ rule.** Rejected — tautologically true and useless. Cross-zone batch-ordering sanity is an OpenLineage concern, not a Gold-table DQ concern.

---

## Artifacts Produced

- `governance/temporal/gold-regional-price-parities.md` — Gold temporal strategy document (carry-forward from Silver, one schema simplification, no new DQ rules).
- `governance/audit-trail/2026-04-11-temporal-modeler-gold-regional-price-parities.md` — this file.

## Artifacts Referenced but Not Modified

- `docs/specs/gold-regional-price-parities.md`
- `governance/temporal/silver-base-bea-rpp.md`
- `governance/temporal/raw-ingest-bea-rpp.md`

## No Changes Proposed To

- Spec schema (already correct)
- Spec DQ rules (already correct)
- Silver temporal strategy
- Bronze temporal strategy
- Domain context

---

## Next Agents

Per spec §"Agent Workflow (Gold Greenfield)":

- @adversarial-auditor — skeptical audit of Gold artifacts including this temporal doc. Primary temporal attack surfaces flagged in the handoff notes.
- @lineage-tracker — OpenLineage capture. Note: do NOT add `ingested_at` / `source_load_date` facets at Gold; they are not Gold columns. The Silver → Gold edge is `overwrite` disposition.
- @cde-tagger — CDE mapping. `data_year`, `promoted_at` are metadata, not CDEs. `cost_tier`, `adjusted_Nk`, `purchasing_power_multiplier`, `rpp_all_items`, `state_abbr`, `census_region` are the real CDE candidates.
- @doc-generator — Gold contract, dictionary, glossary BT-106/107. Must label `promoted_at` as "batch lineage stamp, not event time" in the data dictionary.

@temporal-modeler can be marked SKIP in the remaining workflow (spec §"Agent Workflow" item 12 already anticipates this).

---

*— End of Audit Trail —*
