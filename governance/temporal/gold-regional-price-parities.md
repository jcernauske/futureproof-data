# Temporal Strategy: gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @temporal-modeler
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Parent Temporal Decisions:**
- `governance/temporal/silver-base-bea-rpp.md`
- `governance/temporal/raw-ingest-bea-rpp.md`
**Domain:** Education / Career Guidance — state-level cost-of-living reference
**Zone Coverage:** `consumable.regional_price_parities` (Gold)
**Decision:** SKIP bitemporal modeling. Inherit Silver/Bronze full-table replacement supersession unchanged. Collapse Silver's two-column batch stamp (`ingested_at` + `source_load_date`) into a single Gold promote batch stamp (`promoted_at`).

---

## TL;DR

Gold adds **no new temporal dimensions** over Silver. The Bronze → Silver decision — static single-year reference, `data_year` as provenance (not valid time), full-table replacement supersession, no SCD2, no effective-dating — **propagates cleanly into Gold** because the Silver → Gold transformation is a pure row-shaping operation: 2 verbatim carry-forwards (`verification_status`, `data_year`) plus 5 deterministic derivations (`cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`). None of those add temporal semantics.

Gold introduces **one new lineage batch column** (`promoted_at`, the Gold promotion timestamp) and **drops two Silver lineage columns** (`ingested_at`, `source_load_date`). This is an intentional simplification: the Silver two-stamp pair carried both the Bronze load batch and the Silver promote batch separately, which was necessary to trace across the Bronze → Silver boundary. At the Gold layer, the relevant batch for a Gold consumer is the Gold promote itself; the prior layers' batches are reachable via OpenLineage edges, not via in-row columns.

**No bitemporal modeling. No SCD2. No effective-dating. No new temporal DQ rules.** The Gold spec already contains the correct temporal invariants.

---

## Carry-Forward from Silver (and transitively from Bronze)

| Silver decision (from `governance/temporal/silver-base-bea-rpp.md`) | Gold status |
|---|---|
| Skip bitemporal modeling | **Inherited.** Gold adds no valid-time columns. |
| Skip SCD2 / effective-dating | **Inherited.** Gold does not introduce `valid_from` / `valid_to` / `is_current`. |
| Supersession grain = entire table | **Inherited.** Gold is a 1:1 state-level projection of Silver; replacing Silver replaces Gold. |
| `data_year` is provenance, not a temporal dimension | **Inherited.** `data_year` passes through verbatim as an `int` column with constant value `2024`. |
| `verification_status` is per-row provenance, not a temporal attribute | **Inherited.** Carried forward verbatim per Bronze staff-review Condition 7. |
| Full-replace on refresh / restatement / DQ correction | **Inherited.** Gold is rebuilt in full every time Silver is rebuilt. No merge, no upsert. |
| Point-in-time queries via Iceberg time travel, not schema machinery | **Inherited.** Applies identically to `consumable.regional_price_parities`. |
| Batch stamps are lineage metadata, not event times | **Inherited.** The Gold-specific `promoted_at` column follows the same posture. |

The Silver document is authoritative for the bitemporal posture; this Gold document records the unchanged propagation and the one Gold-specific schema change (collapsing the two Silver batch stamps into a single `promoted_at`).

---

## Valid Time

**Not modeled.** Same rationale as Silver and Bronze — see `governance/temporal/silver-base-bea-rpp.md` §"Valid Time" and `governance/temporal/raw-ingest-bea-rpp.md` §"Valid Time".

The Gold transformation (spec §"Gold Transformations") introduces:

- `cost_tier` — a deterministic CASE expression over `rpp_all_items`. Classification, not temporal.
- `adjusted_30k` / `adjusted_50k` / `adjusted_75k` / `adjusted_100k` — deterministic arithmetic derivations from `purchasing_power_multiplier`. Arithmetic, not temporal.
- `promoted_at` — Gold promote batch stamp. Batch metadata, not temporal (see §"Transaction Time" below).

None of these carry a validity window. None partition rows into versions. None require `valid_from` / `valid_to` support. The Gold projection is a pure function of the Silver row plus a static CASE expression and four constants (30000, 50000, 75000, 100000), so it cannot add temporal semantics that Silver did not already have.

---

## Transaction Time

**Handled entirely by Iceberg snapshots on `consumable.regional_price_parities`.** No transaction-time columns are added.

### Snapshot Strategy (Gold)

Mirrors Silver exactly, with the additional dependency that a Gold rebuild follows every Silver rebuild:

| Event | Bronze action | Silver action | Gold action | Rationale |
|---|---|---|---|---|
| Initial load (2024) | New Bronze snapshot | New Silver snapshot (full rebuild) | New Gold snapshot (full rebuild) | Baseline state. |
| Annual refresh (2025, 2026, ...) | New Bronze snapshot | New Silver snapshot | New Gold snapshot | Replacement propagates top to bottom. |
| Live BEA API refresh replaces CSV-cache estimates | New Bronze snapshot | New Silver snapshot | New Gold snapshot | See `verification_status` implication below. |
| BEA methodology restatement | New Bronze snapshot | New Silver snapshot | New Gold snapshot | Full-replace semantics preserved at every zone. |
| DQ correction (e.g., fix a wrong state row) | New Bronze snapshot | New Silver snapshot | New Gold snapshot | Corrections flow Bronze → Silver → Gold only. |

The Gold `promote` step is idempotent (spec §"Technical Design — Idempotent: Yes"); re-running against an unchanged Silver produces 0 new Gold rows, which means **no unnecessary Gold snapshot is created** when Silver did not change. This is the correct behavior under a full-replacement model.

### Gold-Specific Batch Stamp: `promoted_at`

The Gold spec schema (§"Gold Schema (15 columns)") declares exactly one batch-stamp column:

| Column | Source | Semantics | Use |
|---|---|---|---|
| `promoted_at` | `CURRENT_TIMESTAMP` at Gold promote | Timestamp the Gold row was written | Lineage only — traces a Gold row to the Gold promote batch that produced it. |

**`promoted_at` is a batch stamp, not an event time, not a valid time, not a transaction time.** Downstream agents and consumers MUST NOT:

- Use `promoted_at` in `WHERE` filters as if it were an event time.
- Use it for windowing, effective-dating, or "as of" logic.
- Compute consumer SLAs off it without coordinating with the data contract (freshness SLA is annual, governed by the contract, not by timestamp arithmetic).

All 51 rows in a given Gold snapshot share an identical `promoted_at` value because the promote is a single batch — the same invariant Bronze and Silver honor one and two layers up.

### Why Gold Drops `ingested_at` / `source_load_date`

Silver carries a **two-column** batch-stamp pair:

- `source_load_date` — the Bronze load date, passed through verbatim. Traces a Silver row to the Bronze batch.
- `ingested_at` — the Silver promote timestamp. Traces a Silver row to the Silver batch.

This pair is necessary at Silver because the Silver layer straddles the Bronze/Silver boundary and a lineage consumer may need to resolve either side without consulting the metastore.

At Gold, the spec (§"Gold Transformations" item 4) intentionally collapses this to a **single** batch-stamp column, `promoted_at`:

> "Provenance columns — `promoted_at` (Gold promotion timestamp) replaces Silver's `ingested_at`/`source_load_date`. `data_year` carries forward as provenance, not a temporal dimension."

The rationale for the collapse:

1. **Gold consumers do not need in-row Silver/Bronze batch identity.** The MCP tools (`get_regional_price_parity`, `compare_purchasing_power`) and the frontend salary toggle read Gold rows one state at a time and present display-ready numbers. None of these consumers correlates a Gold row to a specific Silver batch or Bronze batch inside a query.
2. **OpenLineage edges already carry the cross-zone batch identity.** The Bronze → Silver → Gold lineage graph is captured by @lineage-tracker via OpenLineage facets on each promote run. A lineage-aware consumer asks OpenLineage; it does not join on in-row batch columns.
3. **Iceberg snapshot history already carries the per-row cross-zone batch identity.** If a consumer later needs to answer "which Bronze load produced the Gold row I saw on 2026-05-01?", the answer is found by time-travelling `base.bea_rpp` and `raw.bea_rpp` to the matching timestamp, not by reading Silver columns at the Gold grain.
4. **The Gold layer is the consumer surface.** Gold columns cost display surface, contract surface, and schema-migration surface in a way Silver columns do not. Dropping the two Silver-only batch stamps from Gold keeps the consumer schema narrow and free of pipeline-internal plumbing. Gold keeps exactly the provenance it needs (`data_year`, `verification_status`, `promoted_at`) and no more.
5. **Symmetry with the rest of the Gold schema.** The rest of the Gold schema is 14 business-facing columns; adding two carry-forward lineage columns would dilute that by ~13% without buying any consumer-visible value.

This collapse is **non-destructive**. Every piece of information dropped from the Gold row is still recoverable — either from Silver via Iceberg time travel (using `promoted_at` as the correlating timestamp to find the matching Silver snapshot) or from the OpenLineage facet graph emitted by @lineage-tracker on each promote.

The Silver `ingested_at` and `source_load_date` columns remain in `base.bea_rpp` unchanged; only the Gold table omits them. Silver-layer consumers that need them still have them.

---

## Supersession Grain

**Inherited from Silver (and transitively Bronze): the entire table.** When Silver is replaced, Gold is replaced. When Bronze is replaced, Silver is replaced, and Gold follows. There is no independent Gold supersession path.

### Live BEA API Refresh — Supersession Implication

Same mechanics as Silver, extended by one layer.

**Current state (2026-04-11):** 8 of 51 Gold rows have `verification_status = 'bea_official'`; 43 have `verification_status = 'estimate'`. The carry-forward is driven entirely by the Silver row's `verification_status` value. The P0 DQ rule `COUNT(*) WHERE verification_status='bea_official' = 8` is asserted at the Gold layer too (spec §"DQ Rules (Gold) — P0 — verification_status carry-forward").

**Post-refresh state (when live BEA API lands):** All 51 Silver rows flip to `bea_official`. Gold is rebuilt from the new Silver snapshot; all 51 Gold rows carry `verification_status = 'bea_official'`. The Gold DQ rule flips from `= 8` to `= 51` in the same commit that flips the Silver rule. The Bronze deferral (staff-review Condition 6) closes at both Silver and Gold simultaneously.

**Key temporal point:** The refresh is **not a merge** at any zone. It is a **full-table replacement** of `consumable.regional_price_parities`, driven by a full-table replacement of `base.bea_rpp`, driven by a full-table replacement of `bronze.bea_rpp`. There is no row-level supersession, no `is_superseded` flag, no "prior verification" history preserved in-table at Gold. Mechanically:

1. Bronze re-ingests all 51 rows from the live BEA API. New Bronze snapshot.
2. Silver `promote` runs against the new Bronze snapshot. Every row's content-hash changes, so all 51 Silver rows are rewritten. New Silver snapshot.
3. Gold `promote` runs against the new Silver snapshot. Every row's `rpp_all_items`, `purchasing_power_multiplier`, `cost_tier`, and four `adjusted_Nk` values are recomputed; every row's `record_id` content-hash changes; all 51 Gold rows are rewritten. New Gold snapshot.
4. Iceberg time travel on `consumable.regional_price_parities` recovers the pre-refresh Gold state (8 verified + 43 estimated) without any schema change.

The Bronze → Silver replacement semantics therefore **propagate cleanly one more layer**. The refresh is indistinguishable (at the supersession-grain level) from any other annual full-replace event. No schema migration, no correction-tracking columns, no `effective_from` gymnastics at Gold. The only operational change is the hard-coded `= 8` literal in the Gold DQ rule, which flips in lock-step with the Silver rule.

This is the correct behavior for a static reference table in "pure shaping" Gold mode and is a direct consequence of the Bronze decision to model supersession at the full-table grain. If Bronze had chosen row-level SCD2 supersession, the Gold refresh would require a more complex migration; because Bronze chose replacement, Gold inherits zero migration cost — exactly the same property Silver inherited.

### cost_tier Boundary Drift — NOT a Temporal Concern

A natural worry at the Gold layer is: if a state's `rpp_all_items` shifts across a refresh (e.g., a state goes from 102.9 to 103.1), its `cost_tier` flips from `average` to `high`. Is this a temporal event that needs tracking?

**No.** A `cost_tier` flip under the replacement model is just a cell value change, indistinguishable from an `rpp_all_items` change. It is recoverable via Iceberg time travel on the Gold table (query `FOR SYSTEM_TIME AS OF` a pre-refresh timestamp), and it is reported by snapshot diffing out-of-band, not by any schema feature. No SCD2 is required, no `cost_tier_changed_at` column is required, no `previous_cost_tier` carry-forward is required. If a consumer later needs to alert on cost_tier flips, that is an alerting concern on the Gold snapshot diff, not a schema concern in `consumable.regional_price_parities`.

The cost_tier breakpoint boundaries (`>= 108`, `>= 103`, `>= 97`, `>= 91`, `< 91`) are a spec decision, not a temporal decision, and their stability across years is a spec/chaos concern, not a temporal-modeler concern.

### NOT Gold-Specific: multi-year history

If the product later needs multi-year RPP trends, the migration to append-with-year happens **at Bronze first**, per `governance/temporal/raw-ingest-bea-rpp.md` §"Alternative (post-hackathon / production)". Silver follows mechanically. Gold follows mechanically after that: repartition by `data_year`, flip the `COUNT(DISTINCT data_year) = 1` rule to `>= 1`, add a `data_year = MAX(data_year)` filter to the MCP query layer (not the Gold transformer). No Gold-specific temporal decisions required in advance. See the Silver temporal document for the Silver handoff; Gold piggybacks on the same non-breaking migration story.

---

## Point-in-Time Query Support

**Inherited from Silver.** `consumable.regional_price_parities` supports Iceberg time-travel queries identically to `base.bea_rpp` and `raw.bea_rpp`:

```sql
-- "What did consumable.regional_price_parities look like on 2026-03-01?"
SELECT state_fips, state_abbr, rpp_all_items, purchasing_power_multiplier,
       cost_tier, adjusted_50k, verification_status
FROM consumable.regional_price_parities
FOR SYSTEM_TIME AS OF TIMESTAMP '2026-03-01 00:00:00'
WHERE state_fips = '06';

-- "Show me the pre-live-API Gold state of CA" (after the refresh has happened)
SELECT verification_status, rpp_all_items, cost_tier, adjusted_50k
FROM consumable.regional_price_parities
FOR SYSTEM_TIME AS OF TIMESTAMP '<pre-refresh timestamp>'
WHERE state_fips = '06';

-- "Did any state's cost_tier flip across the last refresh?"
-- Compare two snapshots of the Gold table at different timestamps via a self-join
-- using Iceberg snapshot history. No schema feature required.
```

No schema feature supports these queries; Iceberg alone does. No MCP tool, frontend view, or downstream consumer currently requires point-in-time replay on `consumable.regional_price_parities`. The MCP tools (`get_regional_price_parity`, `compare_purchasing_power`) and the frontend salary toggle query the current snapshot only.

---

## Schema Impact

**No new temporal columns** beyond what the Gold spec already specifies.

Columns in `consumable.regional_price_parities` relevant to this temporal decision:

| Column | Role in temporal model |
|---|---|
| `data_year` | Provenance (single-year constant). NOT a temporal dimension. Carried from Silver. |
| `promoted_at` | Batch stamp (Gold promote time). Lineage only. New in Gold. Replaces Silver's `ingested_at` + `source_load_date` pair. |
| `verification_status` | Provenance (per-row verification state). NOT a temporal dimension; see supersession implication above. Carried from Silver per Bronze staff-review Condition 7. |
| `cost_tier` | Derived classification. NOT a temporal dimension. Purely a function of current `rpp_all_items`. |
| `adjusted_30k` / `adjusted_50k` / `adjusted_75k` / `adjusted_100k` | Derived arithmetic. NOT temporal. Purely functions of current `purchasing_power_multiplier`. |

Columns intentionally **not** present at Gold (dropped from Silver on purpose):

| Silver column | Reason for omission at Gold |
|---|---|
| `source_load_date` | Bronze load date; Gold consumers do not need in-row Bronze batch identity. Recoverable via Iceberg time travel on `base.bea_rpp` or OpenLineage edges. |
| `ingested_at` | Silver promote timestamp; Gold consumers do not need in-row Silver batch identity. Same recovery paths. |

The temporal-modeler adds nothing on top of what the Gold spec already contains.

---

## Temporal DQ Rules

### Rules the Gold spec already contains that enforce the temporal posture

The spec's existing P0 DQ rules already cover the temporal model correctly (spec §"DQ Rules (Gold)"):

- `data_year = 2024` — single-year constancy, mirror of Silver and Bronze.
- `COUNT(DISTINCT data_year) = 1` — hardens the supersession-by-replacement contract at the Gold layer. Propagates the linchpin rule from Silver.
- `row count: exactly 51` — asserts full-replacement grain.
- `state_fips non-null + uniqueness` — asserts one-row-per-state invariant under replacement.
- `verification_status values IN ('bea_official', 'estimate')` — bounds the verification domain.
- `COUNT(*) WHERE verification_status='bea_official' = 8` — pins the current verification state (flips to `= 51` in lock-step with Silver after live-API refresh).
- `Every 'bea_official' row's state_fips IN the 8-state canonical set` — guards the allow-list against drift.
- `Passthrough integrity: every Gold row's rpp_all_items equals the Silver row for the same state_fips` (production_only) — asserts that the Gold replacement is a faithful projection of the Silver replacement, which is the cross-zone expression of the replacement-supersession contract.
- `record_id non-null + uniqueness` — asserts grain under replacement.

**P1:**

- `promoted_at non-null` — already present; asserts the Gold batch stamp is populated. Gold's only Gold-specific batch-stamp rule.

### Additional temporal DQ rules proposed by this document

**None.**

All temporal invariants relevant to the Gold layer are already encoded in the spec. No further rules are warranted because:

1. Gold does not introduce a valid-time dimension, so no window rules apply.
2. Gold does not introduce SCD2, so no "exactly one `is_current`" rules apply.
3. `promoted_at` is a batch stamp, not an event time; staleness rules belong in the data contract SLA, not DQ. The spec already places freshness in the contract (annual refresh, static for hackathon).
4. The supersession-grain invariant is already covered by `row_count = 51`, `COUNT(DISTINCT data_year) = 1`, and the passthrough-integrity rule.
5. The verification-state supersession is already covered by the three `verification_status` rules above.
6. The `cost_tier` classification check (spec §"P0 — cost_tier — classification check") asserts the CASE expression is applied consistently; no temporal rule is needed because `cost_tier` is not temporal.
7. The `adjusted_Nk` arithmetic checks assert deterministic math; no temporal rule is needed because the math is not temporal.

If @dq-rule-writer is tempted to add a new temporal rule at Gold, the default answer is "no" — escalate to @temporal-modeler instead. The same default applies at Bronze and Silver.

### Rules @dq-rule-writer should explicitly NOT add at Gold

Same exclusion list as the Silver temporal document, re-asserted at the Gold grain, plus two Gold-specific entries:

| Rule type | Why to skip at Gold |
|---|---|
| `valid_from <= valid_to` | No valid-time columns exist. |
| `no overlapping validity windows per state` | Same reason. |
| `exactly one is_current=true per state` | No SCD2. |
| `data_year strictly monotone on refresh` | Replacement model — old year is gone from the active table. Iceberg snapshot diffing handles this out-of-band. |
| `promoted_at within last N days` | Freshness SLA is annual; belongs in the contract, not DQ. |
| `promoted_at = CURRENT_TIMESTAMP` on every query | Breaks point-in-time replay. Omit. |
| `promoted_at > source_load_date` | The column doesn't exist at Gold; writing a rule against a non-existent column would fail at plan time. |
| `Gold promoted_at > Silver ingested_at` (cross-zone) | Tautologically true (Gold promote follows Silver promote) and useless. Belongs in OpenLineage sanity checks, not Gold DQ. |
| `cost_tier changed_at tracking` | No `cost_tier` history column; cost_tier is a pure function of current `rpp_all_items`. Iceberg time travel answers the "did it flip?" question out-of-band. |
| `adjusted_Nk historical drift` | Same — pure function of current `purchasing_power_multiplier`. Iceberg time travel suffices. |

---

## Handoff Notes for Downstream Agents

| Agent | What to know |
|---|---|
| @dq-rule-writer (Gold) | The spec already contains every temporal-flavored rule needed. Do NOT add more. Do NOT weaken `COUNT(DISTINCT data_year) = 1` — it is the linchpin of the inherited replacement contract. Keep the `verification_status` carry-forward rules verbatim (all three). |
| @primary-agent (Gold build) | Use full overwrite semantics. No merge, no upsert. Gold `promote` reads the entire Silver snapshot and rewrites the entire Gold table. `promoted_at` is a batch stamp — write it as a load-batch constant (single `CURRENT_TIMESTAMP` evaluation per promote), not a per-row clock. All 51 rows in a given Gold snapshot share the identical `promoted_at`. |
| @primary-agent (Gold build) — NOTE on dropped columns | Do NOT carry `ingested_at` or `source_load_date` from Silver to Gold. The spec intentionally drops them. If a future spec change wants them back, that is a schema-migration decision, not a temporal decision. |
| @semantic-modeler | Model `consumable.regional_price_parities` as an independent reference dimension, not a fact table. `data_year` remains a scalar attribute, not a dimension key. `cost_tier` is a categorical attribute, not a slowly-changing dimension. |
| @data-analyst (Gold EDA) | Do not compute "over time" statistics across data_year — only one year exists. Do not compute cost_tier flip frequency — only one snapshot exists. Focus EDA on cost_tier distribution, adjusted_Nk arithmetic, and verification_status carry-forward counts. |
| @entity-resolver | `state_fips` is canonical and temporally stable. No temporal ER considerations. Expected SKIP per spec §"Agent Workflow". |
| @pii-scanner | No PII. No temporal PII considerations. Expected SKIP per spec. |
| @chaos-monkey | Primary temporal attack surface: (a) silent drift from full-replace to partial-merge during an ops incident (same as Silver), (b) misuse of `promoted_at` as an event-time filter by a well-meaning consumer, (c) an off-by-epsilon cost_tier boundary flip near refresh time being misread as a temporal event. The `COUNT(DISTINCT data_year) = 1` rule, the passthrough-integrity rule, and this document's explicit batch-stamp labeling are the defenses. Boundary chaos at `rpp = 108.0`, `103.0`, `97.0`, `91.0` is a classification concern, not a temporal concern — route to cost_tier tests, not temporal tests. |
| @lineage-tracker | OpenLineage facets: add `promoted_at` to the `SchemaFacet`. Do NOT add `ingested_at` / `source_load_date` facets at Gold — they are not Gold columns. The Silver → Gold edge is a full-refresh edge (`overwrite` disposition), not an incremental merge. Cross-zone batch correlation (Gold `promoted_at` → Silver `ingested_at` → Bronze `load_date`) is carried by the OpenLineage parent-run chain, not by in-row columns on the Gold table. |
| @cde-tagger | `data_year`, `promoted_at` are provenance/lineage metadata, not CDEs. `verification_status` is a provenance attribute, not a CDE. `cost_tier`, `adjusted_30k/50k/75k/100k`, `purchasing_power_multiplier`, `rpp_all_items`, `state_abbr`, `census_region` are the real CDE candidates at Gold. |
| @data-contract-author | Freshness SLA = annual, matching BEA publication cadence. No point-in-time replay SLA. Quality tier = `partial_verification`, inherited from Silver/Bronze. Reference the `verification_status` column in the quality section, not the temporal section. Document the Gold-specific collapse of `ingested_at`/`source_load_date` into `promoted_at` as a schema-simplification note, not a quality note. |
| @mcp-engineer | MCP tools do NOT need an `as_of_date` parameter on Gold queries. Single-year lookup only. Propagate `verification_status` to the MCP response envelope (Bronze staff-review Condition 7 carry-forward obligation to `mcp-bea-rpp`, explicitly forward-only per spec §"Bronze Staff Review Conditions — Condition 7"). |
| @doc-generator | When generating the Gold data dictionary, explicitly label `promoted_at` as "batch lineage stamp, not event time" so downstream consumers cannot misread it. Label `data_year` as "provenance, single-year constant". Label `verification_status` as "per-row provenance, not temporal". |
| @adversarial-auditor | Primary temporal attack surface at Gold: (a) a well-meaning consumer filters on `promoted_at` expecting event-time semantics (defense: this document + data dictionary labeling), (b) a schema-migration PR re-adds `ingested_at` / `source_load_date` to Gold, breaking the deliberate collapse (defense: this document records the intentional drop), (c) a future spec adds `cost_tier_changed_at` or similar SCD2 machinery without consulting @temporal-modeler (defense: this document's explicit SCD2-not-applicable statement). |

---

## Decision Log

| Decision | Rationale | Source |
|---|---|---|
| Inherit Silver/Bronze "skip bitemporal" decision unchanged | Gold transformation is a pure row-shaping operation (2 carry-forwards + 5 deterministic derivations) with zero added temporal semantics | `governance/temporal/silver-base-bea-rpp.md`, `governance/temporal/raw-ingest-bea-rpp.md` |
| Treat `promoted_at` as a Gold-promote batch stamp | New column at the Gold batch grain; same provenance-not-event-time semantics as Silver `ingested_at` one layer up | Spec §"Gold Schema" + Silver temporal doc §"Silver-Specific Batch Stamps" |
| Collapse Silver's two-column batch stamp (`ingested_at` + `source_load_date`) into a single Gold `promoted_at` | Gold consumers do not need in-row Bronze/Silver batch identity; OpenLineage edges and Iceberg time travel cover all lineage recovery; the Gold schema stays narrow and free of pipeline-internal plumbing | Spec §"Gold Transformations" item 4 + this document §"Why Gold Drops `ingested_at` / `source_load_date`" |
| Treat `cost_tier` as non-temporal | Deterministic CASE expression over current `rpp_all_items`; no history column needed; Iceberg time travel answers "did it flip?" out-of-band | Spec §"Gold Transformations" item 2 + this document §"cost_tier Boundary Drift — NOT a Temporal Concern" |
| Treat `adjusted_Nk` as non-temporal | Deterministic arithmetic over current `purchasing_power_multiplier`; same reasoning as cost_tier | Spec §"Gold Transformations" item 3 |
| Propose no new temporal DQ rules | Every temporal invariant is already in the spec; additional rules would be redundant, vacuous, or conflict with replacement supersession | Spec §"DQ Rules (Gold)" |
| Document the live-API refresh as a full-replace event at all three zones | Propagates Bronze/Silver replacement semantics cleanly through Gold; avoids any row-level supersession machinery | Spec §"Bronze Staff Review Conditions" + Silver temporal doc §"Supersession Grain" |
| Defer append-with-year migration discussion to Bronze | The migration decision lives at Bronze; Silver and Gold follow mechanically | Bronze temporal doc §"Alternative (post-hackathon / production)" |
| Explicitly forbid cross-zone temporal DQ rules at Gold (e.g., "Gold promoted_at > Silver ingested_at") | Tautological and useless; belongs in OpenLineage sanity checks | This document §"Rules @dq-rule-writer should explicitly NOT add at Gold" |

---

## References

- Parent temporal decisions:
  - `governance/temporal/silver-base-bea-rpp.md`
  - `governance/temporal/raw-ingest-bea-rpp.md`
- Spec (this layer): `docs/specs/gold-regional-price-parities.md`
- Spec (parent Silver): `docs/specs/silver-base-bea-rpp.md`
- Spec (parent Bronze): `docs/specs/raw-ingest-bea-rpp.md`
- Bronze staff review (Condition 6/7): `governance/approvals/raw-ingest-bea-rpp-staff-review.md`
- Domain context: `governance/domain-context.md` — BEA RPP section, Temporal Patterns
- Audit trail: `governance/audit-trail/2026-04-11-temporal-modeler-gold-regional-price-parities.md`

*— End of Temporal Strategy —*
