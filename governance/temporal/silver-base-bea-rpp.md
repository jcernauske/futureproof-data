# Temporal Strategy: silver-base-bea-rpp

**Date:** 2026-04-10
**Agent:** @temporal-modeler
**Spec:** `docs/specs/silver-base-bea-rpp.md`
**Parent Temporal Decision:** `governance/temporal/raw-ingest-bea-rpp.md`
**Domain:** Education / Career Guidance — state-level cost-of-living reference
**Zone Coverage:** `base.bea_rpp` (Silver)
**Decision:** SKIP bitemporal modeling. Inherit Bronze full-table replacement supersession unchanged.

---

## TL;DR

Silver adds **no new temporal dimensions** over Bronze. The Bronze temporal decision — static single-year reference, `data_year` as provenance (not valid time), full-table replacement supersession, no SCD2, no effective-dating — **propagates cleanly into Silver** because the Silver transformation is a pure row-shaping operation with zero temporal semantics added.

Silver introduces **one new lineage batch column** (`ingested_at`, the Silver promote timestamp) and **renames one existing batch column** (`source_load_date`, inherited from Bronze `load_date`). Both are batch provenance, not event time, not valid time, not transaction time. Iceberg snapshots continue to handle transaction time for free.

**No bitemporal modeling. No SCD2. No effective-dating. No new temporal DQ rules.** The Silver spec already contains the correct temporal invariants.

---

## Carry-Forward from Bronze

| Bronze decision (from `governance/temporal/raw-ingest-bea-rpp.md`) | Silver status |
|---|---|
| Skip bitemporal modeling | **Inherited.** Silver adds no valid-time columns. |
| Skip SCD2 / effective-dating | **Inherited.** Silver does not introduce `valid_from`/`valid_to`/`is_current`. |
| Supersession grain = entire table | **Inherited.** Silver is a 1:1 state-level projection of Bronze; replacing Bronze replaces Silver. |
| `data_year` is provenance, not a temporal dimension | **Inherited.** `data_year` passes through verbatim as an `int` column with constant value `2024`. |
| `ingested_at` / `load_date` are batch stamps | **Inherited and extended.** See "Silver-Specific Batch Stamps" below. |
| Full-replace on refresh / restatement / DQ correction | **Inherited.** Silver is rebuilt in full every time Bronze is rebuilt. No merge, no upsert. |
| Point-in-time queries via Iceberg time travel, not schema machinery | **Inherited.** Applies identically to `base.bea_rpp`. |

The Bronze document is authoritative; this Silver document records the unchanged propagation and the two Silver-specific details (batch timestamps and the `verification_status` supersession implication).

---

## Valid Time

**Not modeled.** Same rationale as Bronze — see `governance/temporal/raw-ingest-bea-rpp.md` §"Valid Time".

The Silver transformation (spec §"Silver Transformations") introduces:

- `state_abbr` (static FIPS → USPS lookup — structural, not temporal)
- `census_region` (static FIPS → Census lookup — structural, not temporal)
- `purchasing_power_multiplier` (`100.0 / rpp_all_items` — arithmetic, not temporal)
- `verification_status` (allow-list lookup on `state_fips` — provenance, not temporal)

None of these additions carry a validity window. None partition rows into versions. None require `valid_from`/`valid_to` support. The Silver projection is a pure function of the Bronze row plus three static lookup tables, so it cannot add temporal semantics that Bronze did not already have.

---

## Transaction Time

**Handled entirely by Iceberg snapshots on `base.bea_rpp`.** No transaction-time columns are added.

### Snapshot Strategy (Silver)

Mirrors Bronze exactly, with the additional dependency that a Silver rebuild follows every Bronze rebuild:

| Event | Bronze action | Silver action | Rationale |
|---|---|---|---|
| Initial load (2024) | New Bronze snapshot | New Silver snapshot (full rebuild) | Baseline state. |
| Annual refresh (2025, 2026, ...) | New Bronze snapshot (full replace) | New Silver snapshot (full rebuild) | Bronze supersession propagates. |
| Live BEA API refresh replaces CSV-cache estimates | New Bronze snapshot (full replace) | New Silver snapshot (full rebuild) | See `verification_status` implication below. |
| BEA methodology restatement | New Bronze snapshot (full replace) | New Silver snapshot (full rebuild) | Full replace semantics preserved. |
| DQ correction (e.g., fix a wrong state row) | New Bronze snapshot (full replace) | New Silver snapshot (full rebuild) | Corrections flow Bronze → Silver only. |

The Silver `promote` step is idempotent (spec §"Technical Design — Idempotent: Yes"); re-running against an unchanged Bronze produces 0 new Silver rows, which means **no unnecessary Silver snapshot is created** when Bronze did not change. This is the correct behavior under a full-replacement model.

### Silver-Specific Batch Stamps

The Silver spec adds two batch-stamp columns in the schema (§"Silver Schema"):

| Column | Source | Semantics | Use |
|---|---|---|---|
| `source_load_date` | `bronze.bea_rpp.load_date` (passthrough, renamed) | Date the Bronze load ran | Lineage only — traces a Silver row to the Bronze batch that produced it. |
| `ingested_at` | `CURRENT_TIMESTAMP` at Silver promote | Timestamp the Silver row was written | Lineage only — traces a Silver row to the Silver promote that produced it. |

**Both columns are batch stamps, not event times, not valid times, not transaction times.** Downstream agents MUST NOT:

- Use `source_load_date` or `ingested_at` in `WHERE` filters as if they were event times.
- Use either column for windowing, effective-dating, or "as of" logic.
- Compute SLAs off these columns without coordinating with the data contract (freshness SLA is annual, governed by the contract, not by timestamp arithmetic).

`ingested_at` is new in Silver. Bronze already has its own `ingested_at`; the Silver `ingested_at` is a distinct column at a distinct grain (the Silver promote, not the Bronze ingest). All 51 rows in a given Silver snapshot share identical `source_load_date` and identical `ingested_at` values because the promote is a single batch — the same invariant Bronze honors one layer up.

The Bronze document already establishes this posture (`governance/temporal/raw-ingest-bea-rpp.md` §"`ingested_at` and `load_date`"); the Silver `ingested_at` simply extends that posture to the Silver batch.

---

## Supersession Grain

**Inherited from Bronze: the entire table.** When Bronze is replaced, Silver is replaced. There is no independent Silver supersession path.

### Live BEA API Refresh — Supersession Implication

This is the one Silver-specific supersession behavior worth documenting explicitly.

**Current state (2026-04-10):** 8 of 51 Silver rows have `verification_status = 'bea_official'`; 43 have `verification_status = 'estimate'`. The 8-row allow-list is hard-coded in the Silver transformer (spec §"Silver Transformations" item 8) and asserted by the P0 DQ rule `COUNT(*) WHERE verification_status='bea_official' = 8`.

**Post-refresh state (when live BEA API lands):** All 51 rows become `bea_official`. The Silver transformer's allow-list flips to "all 51 codes", the DQ rule flips from `= 8` to `= 51`, and the Bronze deferral (staff-review Condition 6) closes.

**Key temporal point:** The refresh is **not a merge**. It is a **full-table replacement** of `base.bea_rpp`, driven by a full-table replacement of `bronze.bea_rpp`. There is no row-level supersession, no `is_superseded` flag, no "prior verification" history preserved in-table. Mechanically:

1. Bronze re-ingests all 51 rows from the live BEA API. New Bronze snapshot.
2. Silver `promote` runs against the new Bronze snapshot. Because `rpp_all_items` values shift for the previously-estimated 43 states, every row's `record_id` content-hash changes, so all 51 Silver rows are rewritten.
3. New Silver snapshot. All 51 rows carry `verification_status = 'bea_official'`.
4. Iceberg time travel on `base.bea_rpp` recovers the pre-refresh state (8 verified + 43 estimated) without any schema change.

The Bronze replacement semantics therefore **propagate cleanly**: the refresh is indistinguishable (at the supersession-grain level) from any other annual full-replace event. No schema migration, no correction-tracking columns, no `effective_from` gymnastics. The only operational change is two hard-coded values: the allow-list in the transformer and the `= 8` literal in the DQ rule.

This is the correct behavior for a static reference table and is a direct consequence of the Bronze decision to model supersession at the full-table grain. If Bronze had chosen row-level SCD2 supersession, the refresh would require a more complex migration; because Bronze chose replacement, Silver inherits zero migration cost.

### NOT Silver-Specific: multi-year history

If the product later needs multi-year RPP trends, the migration to append-with-year happens **at Bronze first**, per `governance/temporal/raw-ingest-bea-rpp.md` §"Alternative (post-hackathon / production)". Silver follows mechanically: repartition by `data_year`, flip the `COUNT(DISTINCT data_year) = 1` rule to `>= 1`, add a `latest_year` filter to the Gold transformer. No Silver-specific temporal decisions required in advance.

---

## Point-in-Time Query Support

**Inherited from Bronze.** `base.bea_rpp` supports Iceberg time-travel queries identically to `raw.bea_rpp`:

```sql
-- "What did base.bea_rpp look like on 2026-03-01?"
SELECT state_fips, state_abbr, rpp_all_items, purchasing_power_multiplier, verification_status
FROM base.bea_rpp
FOR SYSTEM_TIME AS OF TIMESTAMP '2026-03-01 00:00:00'
WHERE state_fips = '06';

-- "Show me the pre-live-API state of CA" (after the refresh has happened)
SELECT verification_status, rpp_all_items
FROM base.bea_rpp
FOR SYSTEM_TIME AS OF TIMESTAMP '<pre-refresh timestamp>'
WHERE state_fips = '06';
```

No schema feature supports these queries; Iceberg alone does. No MCP tool, Gold consumer, or downstream agent currently requires point-in-time replay on `base.bea_rpp`.

---

## Schema Impact

**No new temporal columns** beyond what the Silver spec already specifies.

Columns in `base.bea_rpp` relevant to this temporal decision:

| Column | Role in temporal model |
|---|---|
| `data_year` | Provenance (single-year constant). NOT a temporal dimension. |
| `source_load_date` | Batch stamp (Bronze load date, passed through). Lineage only. |
| `ingested_at` | Batch stamp (Silver promote time). Lineage only. New in Silver. |
| `verification_status` | Provenance (per-row verification state). NOT a temporal dimension; see supersession implication above. |

The temporal-modeler adds nothing on top of what the Silver spec already contains.

---

## Temporal DQ Rules

### Rules the Silver spec already contains that enforce the temporal posture

The spec's existing P0 DQ rules already cover the temporal model correctly:

- `data_year = 2024` — single-year constancy, mirror of Bronze `RAW-BEA-010`.
- `COUNT(DISTINCT data_year) = 1` — hardens the supersession-by-replacement contract (spec §"DQ Rules (Silver)"). Already cites the Bronze temporal document.
- `row count: exactly 51` — asserts full-replacement grain.
- `state_fips uniqueness` — asserts one-row-per-state invariant under replacement.
- `verification_status values IN ('bea_official','estimate')` — bounds the verification domain.
- `COUNT(*) WHERE verification_status='bea_official' = 8` — pins the current verification state (flips to `= 51` after live-API refresh).
- `Every 'bea_official' row must have state_fips IN {'06','15','11','34','05','28','19','40'}` — guards the allow-list against drift.

### Additional temporal DQ rules proposed by this document

**None.**

All temporal invariants relevant to the Silver layer are already encoded in the spec. The one "temporal-flavored" rule the Bronze document introduced (`COUNT(DISTINCT data_year) = 1`) is already carried into the Silver spec and labeled with its Bronze temporal-document citation. No further rules are warranted because:

1. Silver does not introduce a valid-time dimension, so no window rules apply.
2. Silver does not introduce SCD2, so no "exactly one `is_current`" rules apply.
3. `source_load_date` and `ingested_at` are batch stamps, not event times, so staleness rules would fire 11 months of 12 and belong in the data contract SLA, not DQ.
4. The supersession-grain invariant is already covered by `row_count = 51` and `COUNT(DISTINCT data_year) = 1`.
5. The verification-state supersession is already covered by the three `verification_status` rules above.

If @dq-rule-writer is tempted to add a new temporal rule, the default answer is "no" — escalate to @temporal-modeler instead.

### Rules @dq-rule-writer should explicitly NOT add

Same exclusion list as the Bronze temporal document, re-asserted at the Silver grain:

| Rule type | Why to skip at Silver |
|---|---|
| `valid_from <= valid_to` | No valid-time columns exist. |
| `no overlapping validity windows per state` | Same reason. |
| `exactly one is_current=true per state` | No SCD2. |
| `data_year strictly monotone on refresh` | Replacement model — old year is gone from the active table. Iceberg snapshot diffing handles this out-of-band. |
| `ingested_at within last N days` | Freshness SLA is annual; belongs in the contract, not DQ. |
| `source_load_date = CURRENT_DATE` on every query | Breaks point-in-time replay. Omit. |
| `ingested_at > source_load_date` | Tautologically true (Silver promote follows Bronze ingest) and useless — asserts nothing about the data. |

---

## Handoff Notes for Downstream Agents

| Agent | What to know |
|---|---|
| @dq-rule-writer (Silver) | The spec already contains every temporal-flavored rule needed. Do NOT add more. Do NOT weaken `COUNT(DISTINCT data_year) = 1` — it is the linchpin of the inherited replacement contract. |
| @dq-rule-writer (Gold) | The Gold consumable inherits the single-year grain and the `verification_status` column. Propagate `COUNT(DISTINCT data_year) = 1` and `verification_status IN (...)` to Gold. Do NOT add "latest year" rules — in replacement mode, every year is the latest year. |
| @primary-agent (Silver build) | Use full overwrite semantics. No merge, no upsert. Silver `promote` reads the entire Bronze snapshot and rewrites the entire Silver table. `source_load_date` and `ingested_at` are batch stamps — write them as load-batch constants, not per-row clocks. |
| @primary-agent (Gold build) | Same. Gold is a straight projection/derivation from Silver; no temporal logic required. Carry `data_year`, `source_load_date`, and `verification_status` through. |
| @semantic-modeler | Model `base.bea_rpp` as an independent reference dimension, not a fact table (per Bronze decision). `data_year` remains a scalar attribute, not a dimension key. |
| @entity-resolver | `state_fips` is canonical and temporally stable. No temporal ER considerations. |
| @pii-scanner | No PII. No temporal PII considerations. |
| @lineage-tracker | OpenLineage facets: add `source_load_date` and `ingested_at` to the `SchemaFacet`. No temporal facets beyond standard. Bronze → Silver edge is a full-refresh edge (`overwrite` disposition), not an incremental merge. |
| @cde-tagger | `data_year`, `source_load_date`, `ingested_at` are provenance/lineage metadata, not CDEs. `verification_status` is a provenance attribute, not a CDE. State_abbr / census_region / purchasing_power_multiplier are the real CDE candidates. |
| @data-contract-author | Freshness SLA = annual, matching BEA publication cadence. No point-in-time replay SLA. The `verification_status` column is the per-row quality carrier — reference it in the contract's quality section, not the temporal section. |
| @mcp-engineer | MCP tools do NOT need an `as_of_date` parameter on Silver queries. Single-year lookup only. Propagate `verification_status` to the MCP response envelope (Bronze staff-review Condition 7). |
| @adversarial-auditor | Primary temporal attack surface: (a) silent drift from full-replace to partial-merge during an ops incident, (b) misuse of `source_load_date` / `ingested_at` as event-time filters by a well-meaning downstream agent. The `COUNT(DISTINCT data_year) = 1` rule and this document's explicit batch-stamp labeling are the defenses. |

---

## Decision Log

| Decision | Rationale | Source |
|---|---|---|
| Inherit Bronze "skip bitemporal" decision unchanged | Silver transformation is a pure row-shaping operation with zero added temporal semantics | `governance/temporal/raw-ingest-bea-rpp.md` |
| Treat `source_load_date` as a Bronze-passthrough batch stamp | Renamed from Bronze `load_date`; semantics unchanged — still a batch identifier, not an event time | Spec §"Silver Schema" + Bronze temporal doc §"`ingested_at` and `load_date`" |
| Treat `ingested_at` as a Silver-promote batch stamp | New column at the Silver batch grain; same provenance-not-event-time semantics as Bronze `ingested_at` | Spec §"Silver Schema" + Bronze temporal doc |
| Propose no new temporal DQ rules | Every temporal invariant is already in the spec; additional rules would be redundant, vacuous, or conflict with replacement supersession | Spec §"DQ Rules (Silver)" |
| Document the live-API refresh as a full-replace event | Propagates Bronze replacement semantics cleanly; avoids any row-level supersession machinery | Spec §"Inherited Constraints from Bronze" + Bronze temporal doc §"Supersession Grain" |
| Defer append-with-year migration discussion to Bronze | The migration decision lives at Bronze; Silver follows mechanically | Bronze temporal doc §"Alternative (post-hackathon / production)" |

---

## References

- Parent temporal decision: `governance/temporal/raw-ingest-bea-rpp.md`
- Spec (this layer): `docs/specs/silver-base-bea-rpp.md`
- Spec (parent Bronze): `docs/specs/raw-ingest-bea-rpp.md`
- Bronze staff review (Condition 6/7): `governance/approvals/raw-ingest-bea-rpp-staff-review.md`
- Domain context: `governance/domain-context.md` — BEA RPP section, Temporal Patterns
- Audit trail: `governance/audit-trail/2026-04-10-temporal-modeler-silver-base-bea-rpp.md`

*— End of Temporal Strategy —*
