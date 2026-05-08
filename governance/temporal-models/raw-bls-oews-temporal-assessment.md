# Temporal Assessment: bronze.bls_oews / base.bls_oews / consumable.occupation_profiles (OEWS columns)

**Date:** 2026-05-06
**Agent:** @temporal-modeler
**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Domain:** U.S. Labor Market — Occupation-Level Wage Distribution
**Zone Coverage:** `bronze.bls_oews` -> `base.bls_oews` -> `consumable.occupation_profiles` (4 OEWS columns) -> `consumable.program_career_paths` (threaded)
**Verdict:** NON_TEMPORAL

---

## TL;DR

The BLS OEWS ingest is a single-vintage annual snapshot — 831 detailed-SOC rows for the May 2024 reference period, all carrying the same `source_load_date`, no within-vintage amendment stream, no per-row effective dating. **No bitemporal modeling, no SCD2, no `valid_from`/`valid_to` columns, no supersession metadata, no point-in-time query support is required at any zone for the hackathon scope.** Iceberg snapshots provide all necessary transaction-time history for free.

This matches the precedent set by `governance/temporal/raw-ingest-bea-rpp.md` (single-year reference table, full-replace) and `governance/temporal-models/raw-ipeds-finance-temporal-assessment.md` (single-fiscal-year snapshot, NOT APPLICABLE). It is simpler than IPEDS Finance because there is no fiscal-year dimension column; the reference period is fixed by the load.

The domain context explicitly authorizes skipping bitemporal modeling — see `governance/domain-context.md` §"Temporal Patterns (BLS OEWS)" (lines 2672-2686): *"Treat as a non-temporal snapshot table for now."*

---

## Question 1: Is the current single-vintage schema sufficient for the Hackathon scope?

**Yes.** The schema declared in the spec (Zone 1 §"Raw Schema", Zone 2 §"Silver Schema", Zone 3 NestedField additions to `occupation_profiles` and `program_career_paths`) is sufficient as written.

### Why the spec schema is enough

| Concern | Spec carries it? | Source |
|---|---|---|
| Reference-period stamp | `source_load_date` (Bronze + Silver) | Spec Zone 1 §"Raw Schema", Zone 2 §"Silver Schema" |
| Wall-clock ingest stamp | `ingested_at` (Bronze + Silver) | Same |
| Source URL provenance | `source_url`, `source_method` | Spec Zone 1 §"Raw Schema" |
| Per-row valid-time interval | NOT NEEDED | All 831 rows share the May 2024 reference period — there is no per-row variation to model. |
| Per-row amendment marker | NOT NEEDED | BLS does not emit per-cell corrections; revisions are republished as a complete file. |
| Supersession metadata | NOT NEEDED | Refresh-on-publish strategy is full-replace per Iceberg snapshot. |

### What `source_load_date` is and is not

`source_load_date` is **provenance** — it stamps each row with the BLS publication date for the reference period. It is structurally analogous to `data_year` in BEA RPP (single value across the entire current load). It is **not** a valid-time dimension:

- It is constant across all 831 rows in the current load.
- It carries no `valid_to` counterpart.
- No consumer queries across distinct values of `source_load_date` (because there is only one).
- It identifies "which BLS release this row came from," i.e., load-batch identity.

This matches the BEA RPP precedent's reasoning verbatim: *"`data_year` identifies the BEA publication year, not a validity window... It is semantically equivalent to 'which BEA release this row came from' — i.e., provenance"* (`governance/temporal/raw-ingest-bea-rpp.md` lines 44-52).

### Iceberg snapshots cover transaction time

The single Iceberg snapshot produced at initial load is sufficient. Time-travel queries (`AT (TIMESTAMP => '<ts>')`) can recover the May 2024 vintage from any future point if a downstream consumer wants the pre-refresh view. **No schema work is needed to enable this** — it is native Iceberg behavior.

---

## Question 2: Do downstream consumers need historical wage tracking?

**No — explicitly out of scope by the spec.**

The spec's §"Future Enhancements" enumerates exactly what is in and out of scope. Item #3 (verbatim) parks year-over-year wage tracking as an explicit non-goal:

> *"3. **OEWS time series:** Track year-over-year wage changes per SOC -> 'wage momentum' signal for GRW stat."*

Item #1 (the only ERN-touching enhancement) is also future:

> *"1. **ERN stat v2:** Incorporate OEWS wage spread (p75 - p25) as a 'ceiling potential' signal."*

This is a **single-vintage range-display feature**, not a longitudinal feature. The two consuming Gold tables and their downstream surfaces all read the current vintage and only the current vintage:

| Consumer | What it consumes | Cross-vintage need? |
|---|---|---|
| `consumable.occupation_profiles` (4 new OEWS columns: `wage_p10/p25/p75/p90`) | Current vintage only | NO |
| `consumable.program_career_paths` (threaded through engine) | Current vintage only | NO |
| API model `CareerOutcome.wage_p10/p25/p75/p90` | Current vintage only | NO |
| `CareerCard` "typical range" row | Current vintage only | NO |
| `FinancesCard` "Career salary range" row | Current vintage only | NO |
| ERN stat (today) | NOT consumed by ERN today (Future Enhancement §1) | NO |

No MCP tool accepts an `as_of_date` parameter. No comparison surface (CompareSchoolsPanel, MiniCompareStrip, ExplainStatReceipt) reaches across OEWS vintages — they all read the live `program_career_paths` table. The spec's stat-display blast-radius audit (§"Stat-Display Blast-Radius Audit") confirms exactly two surfaces gain a wage row, and both render only current-vintage values.

**Conclusion:** Hackathon scope reads at most one OEWS vintage at a time. No historical tracking, no point-in-time replay, no longitudinal join.

---

## Question 3: Upgrade path if a future May 2025 vintage lands

**Recommendation: append-with-`reference_period`, partition the Bronze and Silver tables on a new `reference_period` column (e.g., string `"May 2024"`, `"May 2025"`), and have downstream consumers select `WHERE reference_period = (SELECT MAX(reference_period) FROM base.bls_oews)`. Do NOT adopt SCD2.**

This recommendation is informed by:

- The BEA RPP temporal strategy's "post-hackathon append-with-year" appendix (`governance/temporal/raw-ingest-bea-rpp.md` lines 109-123), which is the closest precedent in this repo.
- The domain context's explicit guidance: *"If a future requirement demands year-over-year wage-trend analysis, add a `reference_period` dimension (string, e.g., 'May 2024') and stop replacing — but that decision is out-of-scope for v1 and should not drive the v1 model."* (`governance/domain-context.md` line 2677.)

### Trigger conditions (when to upgrade)

Adopt the append-with-`reference_period` pattern only when one of the following lands as a real downstream requirement:

1. A "wage momentum" signal (Future Enhancements §3) is implemented in GRW or ERN.
2. A UI surface needs year-over-year wage delta per SOC.
3. A regulatory/audit requirement to reproduce past CareerCard renderings emerges.

If none of these exist, keep replacing on refresh — Iceberg time travel suffices for any ad-hoc historical lookup.

### Schema and pipeline changes required at upgrade time

These are **not implemented now**. They are recorded so a future spec can pick them up.

| Concern | Current (v1, this spec) | Future-multi-vintage |
|---|---|---|
| Reference-period column | `source_load_date` (date) | Add `reference_period` (string, e.g., `"May 2024"`) — load-time column promoted to a partition key |
| Bronze grain | One row per detailed SOC, current vintage | One row per `(reference_period, soc_code)` |
| Silver grain | `[soc_code]` | `[reference_period, soc_code]` |
| Bronze/Silver record key | `compute_grain_id(row, ['soc_code'], prefix='oews')` | `compute_grain_id(row, ['reference_period', 'soc_code'], prefix='oews')` — current scheme would collide on second-vintage ingest |
| Iceberg write mode | Full-table overwrite | Partition-overwrite by `reference_period` (idempotent re-loads of any single vintage; new vintages append) |
| Iceberg partitioning | None / unpartitioned | Partition `bronze.bls_oews` and `base.bls_oews` by `reference_period` |
| DQ row-count rule | `800 <= count <= 900` | `800 <= count_per_reference_period <= 900` and `count_distinct(reference_period) = N_expected_vintages` |
| Gold join semantics | `LEFT JOIN base.bls_oews oews ON op.soc_code = oews.soc_code` | `LEFT JOIN base.bls_oews oews ON op.soc_code = oews.soc_code AND oews.reference_period = (SELECT MAX(reference_period) FROM base.bls_oews)` — keeps `consumable.occupation_profiles` single-vintage even after multi-vintage Bronze/Silver |
| API contract | Unchanged | Unchanged — selection of "current vintage" is internal to the Gold transformer |
| MCP tool signatures | Unchanged | Unchanged for the default case. If an `as_of_period` parameter is added later, it would be additive (optional argument). |
| Top-code floor drift | N/A | Document the cap floor per `reference_period` in the data dictionary — domain context §"Temporal Patterns (BLS OEWS)" warns about the 2023 $208K -> $239,200 jump and notes year-over-year wage-distribution trend analyses must account for this discontinuity. |

### Why NOT SCD2

SCD2 (`valid_from`/`valid_to`/`is_current`) is the wrong pattern even in the multi-vintage case, for the same reasons given in the BEA RPP precedent (`governance/temporal/raw-ingest-bea-rpp.md` lines 125-132):

- BLS does not amend individual SOC values mid-vintage. There is no within-vintage fact evolution to track.
- Cross-vintage comparisons are cleanly expressed by `reference_period`, which is a discrete attribute, not a continuous interval.
- SCD2 overhead (closing out old rows, maintaining `is_current`) buys nothing over partition-by-`reference_period`.

### Why NOT bitemporal (`valid_from`/`valid_to` plus transaction time)

Bitemporal modeling is justified when (a) facts have explicit per-row validity windows in the real world, and (b) corrections to historical facts must be preserved alongside the originals so a query can ask "what did we know on date X?" across both axes. OEWS satisfies neither:

- Each row's "real-world validity" is the entire reference period (May 2024) — there is no per-SOC variability.
- BLS corrections, when they happen, replace the entire vintage file rather than emitting per-cell amendments. There is no per-row correction signal to preserve.
- Iceberg snapshots already preserve full transaction-time history, so the second axis of bitemporality is provided by the storage layer at zero modeling cost.

### Migration is non-breaking for downstream consumers

If the future migration is implemented as recommended (Gold transformer hard-codes "select MAX(reference_period)"), then:

- The existing API contract (`CareerOutcome.wage_p10/p25/p75/p90`) is unchanged.
- The existing frontend types are unchanged.
- The existing CareerCard / FinancesCard rendering logic is unchanged.
- Existing DQ rules on `consumable.occupation_profiles` (`wage_p25` non-null >= 90%, monotonicity, >= 750-SOC coverage) continue to apply, evaluated against the latest vintage only.

The only callers that need to change are (a) Bronze + Silver ingest code, (b) Bronze + Silver DQ rules, and (c) any future consumer that explicitly opts in to multi-vintage queries (Future Enhancements §3 wage-momentum signal). This containment is the main reason to prefer append-with-`reference_period` over a more invasive bitemporal scheme.

---

## Verdict and Handoff

**Verdict: NON_TEMPORAL.** No bitemporal schema, no SCD2, no supersession metadata, no point-in-time query support is required at any zone for the spec `docs/specs/ingest-bls-oews-wage-percentiles.md` as written.

### Handoff Notes for Downstream Agents

| Agent | What to do |
|---|---|
| @primary-agent (Bronze) | Implement the spec's Zone 1 schema verbatim. No `valid_from`/`valid_to`/`is_correction`/`corrects_record`/`reference_period` columns. `source_load_date` and `ingested_at` are batch stamps, not per-row event times. |
| @primary-agent (Silver) | Use full-table overwrite semantics (mirror `src/silver/bls_ooh_transformer.py` and `src/silver/bea_rpp_transformer.py` per spec Zone 2). No merge/upsert. `compute_grain_id(row, ['soc_code'], prefix='oews')` is correct for v1 — would need to incorporate `reference_period` only at the future-multi-vintage upgrade. |
| @primary-agent (Gold) | LEFT JOIN as specified. No "select MAX(...)" filter needed today (only one vintage exists). The future-migration version of this query is recorded above for reference. |
| @dq-rule-writer | Do NOT add bitemporal DQ rules (`valid_from <= valid_to`, `no overlapping windows`, `exactly one is_current=true`). All temporal posture is covered by the spec's existing rules (row count, monotonicity, top-code consistency). One optional addition: a `COUNT(DISTINCT source_load_date) = 1` rule to harden the single-vintage contract — same hardening role as the BEA RPP `data_year cardinality = 1` rule. |
| @semantic-modeler | Model `base.bls_oews` as a flat occupation-keyed reference dimension. Do not introduce a temporal dimension or fact-vs-dimension distinction on it. |
| @lineage-tracker | Standard SchemaFacet + DatasourceDatasetFacet for all four lineage events enumerated in the spec. No temporal facets required. No SymlinksDatasetFacet for vintage-partitioning until the future migration. |
| @data-contract-author / @doc-generator | Freshness SLA = annual, matching BLS OEWS publication cadence (~March of the year following the May reference period). No point-in-time replay SLA. The contract version bumps already specified by the spec (1.0.0 -> 1.1.0 on `consumable-occupation-profiles`, 1.1.0 -> 1.2.0 on `consumable-program-career-paths`) need no temporal-related additions. |
| @mcp-engineer | MCP tools do NOT need an `as_of_period` parameter. Single-vintage lookup only. |

---

## Decision Log

| Decision | Rationale | Source |
|---|---|---|
| Verdict NON_TEMPORAL | Single-vintage annual snapshot; no per-row valid-time variation; no per-cell amendments | `governance/domain-context.md` §"Temporal Patterns (BLS OEWS)" lines 2672-2686; spec §"Update cadence: Annual" |
| Spec schema sufficient as written | All needed provenance (`source_load_date`, `ingested_at`, `source_url`, `source_method`) already declared; no temporal dimensions are needed at v1 | Spec Zone 1 §"Raw Schema", Zone 2 §"Silver Schema" |
| No historical tracking required for downstream consumers | Future Enhancements §3 (OEWS time series) and §1 (ERN v2 from OEWS spread) are explicitly out of scope | Spec §"Future Enhancements" items 1 and 3 |
| Recommended future upgrade path: append-with-`reference_period` | Matches BEA RPP precedent's post-hackathon recommendation; non-breaking for current API/frontend; compatible with Iceberg partition-overwrite semantics | `governance/temporal/raw-ingest-bea-rpp.md` lines 109-123; `governance/domain-context.md` line 2677 |
| Reject SCD2 even at upgrade time | No within-vintage fact evolution; cross-vintage comparison is a discrete attribute, not a validity interval | `governance/temporal/raw-ingest-bea-rpp.md` lines 125-132 |
| Reject full bitemporal modeling | No per-row validity windows; no per-cell amendment stream; transaction time is already covered by Iceberg snapshots | This document §"Why NOT bitemporal" |
| Optional v1 hardening rule: `COUNT(DISTINCT source_load_date) = 1` | Forces an explicit decision when the supersession model changes (mirrors BEA RPP `data_year cardinality = 1` rule) | `governance/temporal/raw-ingest-bea-rpp.md` lines 198-204 |

---

## References

- Spec: `docs/specs/ingest-bls-oews-wage-percentiles.md`
- Domain context: `governance/domain-context.md` §"Domain Context: BLS OEWS" (line 2579) and §"Temporal Patterns (BLS OEWS)" (lines 2672-2686)
- EDA: `governance/eda/raw-bls-oews-eda.md`
- Precedent (annual snapshot, single vintage, NOT APPLICABLE): `governance/temporal/raw-ingest-bea-rpp.md`
- Precedent (single fiscal-year snapshot, NOT APPLICABLE): `governance/temporal-models/raw-ipeds-finance-temporal-assessment.md`

*— End of Temporal Assessment —*
