# Audit Trail: @semantic-modeler — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @semantic-modeler
**Spec:** docs/specs/gold-regional-price-parities.md
**Zone:** Gold (Consumable)
**Mode:** Greenfield (target table does not yet exist in Iceberg catalog; no source code in `src/gold/` for this spec)
**Artifacts produced:**
- `governance/models/gold-regional-price-parities-conceptual.md`
- `governance/models/gold-regional-price-parities-logical.md`
- `governance/models/gold-regional-price-parities-physical.md`

---

## Inputs consulted

| Source | Purpose |
|--------|---------|
| `docs/specs/gold-regional-price-parities.md` | Authoritative requirement: 15 columns, grain, dedup, derivations, DQ spot checks |
| `governance/models/silver-base-bea-rpp-conceptual.md` | Parent conceptual model — entity structure to carry forward and rename |
| `governance/models/silver-base-bea-rpp-logical.md` | Parent logical model — attribute definitions, type domains, constraints |
| `governance/models/silver-base-bea-rpp-physical.md` | Parent physical model — Iceberg schema patterns, promote pattern, DDL style, and the canonical column types for the 8 passthrough columns |
| `governance/business-glossary.json` (BT-098 through BT-107) | Verified all 10 business term IDs exist with authoritative definitions before referencing them by ID in the models |
| `governance/models/gold-occupation-profiles-bls-ooh-{conceptual,logical,physical}.md` (format reference only) | Structural template for Gold-zone model artifacts in this project |

## Mode detection

Target table `consumable.regional_price_parities` does not yet exist in the Iceberg catalog and there is no `src/gold/regional_price_parities.py` (or equivalent) under `src/gold/`. This is a **Greenfield** modeling run: Conceptual → Logical → Physical, top-down, before any transformer code is written. The `**Mode: Greenfield**` header is stamped on all three artifacts.

## Stage 1: Conceptual model

### Entities chosen

Eight entities total:

1. **State Cost-of-Living Reference** — the anchor consumable entity (renamed from Silver's `State` for Gold clarity)
2. **State Identity** — dimensional context (FIPS, name, abbreviation, Census region)
3. **Census Region** — retained as a dependent external taxonomy; collapsed into State Identity at logical flattening
4. **RPP Measurement** — raw payload (rpp_all_items + purchasing_power_multiplier)
5. **Cost Tier** *(new in Gold)* — dependent enum taxonomy derived from rpp_all_items
6. **Adjusted Salary** *(new in Gold)* — dependent measure group of four pre-computed benchmark evaluations
7. **Verification Status** — carried forward from Silver per Bronze Condition 7
8. **Reference Vintage** — data_year single-vintage entity

### Key conceptual decisions

- **Cost Tier modeled as a dependent entity, not a plain attribute.** The tier is a classification taxonomy with a closed enum and governance-frozen breakpoints. Modeling it as an entity makes the "breakpoint change = breaking change" governance contract visible at the conceptual level. This was explicitly requested in the task brief.
- **Adjusted Salary modeled as a dependent measure group, not four unrelated attributes.** The four benchmarks share a formula, a vintage, a unit, and a rounding rule. They exist as a display contract with the frontend. Grouping them clarifies extensibility (future benchmarks extend the group) and documents that client-side math on intermediate salaries is disallowed.
- **State Cost-of-Living Reference as the anchor (not `State`).** Silver used `State` as its anchor; Gold's anchor is the enriched consumable profile. Rename clarifies zone semantics.
- **Census Region edge preserved in the diagram but collapsed into State Identity at logical flattening.** Documentation device, no structural impact.
- **Verification Status remains a first-class entity.** Matches Silver's treatment; the Condition 7 carry-forward obligation makes the entity status load-bearing.
- **No edges to the SOC/CIP join graph.** Gold BEA RPP is orthogonal to every other Gold product. Integration is query-time, not pipeline-time. The conceptual model contains zero cross-source edges.

### Business glossary cross-references

All entities and their anchoring business terms (BT-098 through BT-107) were verified against `governance/business-glossary.json` before being referenced by ID. The models store IDs only; the glossary is the authoritative source of definitions.

## Stage 2: Logical model

### Single denormalized table

Per the Gold Consumable zone pattern, all eight conceptual entities flatten into a single denormalized table with 15 columns. Every relationship is 1:1 per row; normalization would add joins with no analytic value.

### 15-column ordering (confirmed against spec)

The order was taken verbatim from the spec's "Gold Schema (15 columns)" table and preserved through logical and physical models:

```
 1. record_id                    (derived at Gold, prefix 'rpc')
 2. state_fips                   (passthrough)
 3. state_name                   (passthrough)
 4. state_abbr                   (passthrough)
 5. census_region                (passthrough)
 6. rpp_all_items                (passthrough)
 7. purchasing_power_multiplier  (passthrough)
 8. cost_tier                    (derived at Gold, frozen CASE)
 9. adjusted_30k                 (derived at Gold)
10. adjusted_50k                 (derived at Gold)
11. adjusted_75k                 (derived at Gold)
12. adjusted_100k                (derived at Gold)
13. verification_status          (carry-forward, Condition 7)
14. data_year                    (passthrough)
15. promoted_at                  (generated at Gold)
```

Ordering rationale: identity (1-5) → measurement (6-7) → derivations (8-12) → provenance qualifier (13) → vintage (14) → infrastructure metadata (15). Derivations grouped together so a consumer scanning left-to-right sees the raw RPP, then everything it powers, then the provenance flag.

### Dedup grain and surrogate key prefix

- **Dedup grain:** `['state_fips']` — matches Silver; Gold grain is identical to Silver grain.
- **Surrogate key prefix:** `rpc` (Regional Price parities Consumable) — distinct from Silver's `rpp` prefix. Decision rationale: keeping hash namespaces separate across zones makes accidental record_id collisions between Silver and Gold structurally impossible, and the prefix also signals "consumable" vs. "base" at a glance. This deliberately diverges from the first impulse of reusing Silver's `rpp` prefix.

### Cost Tier as inline CASE vs. lookup table

**Decision: inline CASE expression, frozen in this model. No lookup table.**

Alternatives considered:
- **Two-column lookup table `cost_tier_breakpoints(tier, lower_bound)`** — rejected. Range-joins on continuous columns are more expensive and less auditable than a CASE. Lookup tables also invite the false impression that breakpoints are editable data.
- **Reference enum table `cost_tier_enum(tier, description)`** — rejected. Downstream consumers bind to the five literal values in code, not to a table. Adding a reference table would change no consumer code.

The frozen CASE uses left-closed breakpoints at 108, 103, 97, 91 exactly as specified. Any change requires a new spec.

### Adjusted Salary as four sibling columns vs. STRUCT vs. MAP

**Decision: four sibling DOUBLE columns. No struct, no map.**

Alternatives considered and rejected:
- **STRUCT<k30:DOUBLE, k50:DOUBLE, k75:DOUBLE, k100:DOUBLE>** — rejected because:
  1. Consumers read scalar doubles; struct access adds `.field` at every read site.
  2. DQ rule expression is simpler against flat columns.
  3. Current benchmark set is closed and small (4 values); structs pay off with many or variable-cardinality fields.
  4. Backwards-compatible with the existing MCP tool contract being developed in parallel.
- **MAP<INTEGER, DOUBLE>** — rejected because:
  1. A map semantically invites arbitrary keys, which contradicts the "closed display contract" intent.
  2. Iceberg/DuckDB map access for range queries is inconsistent across engines.
  3. DQ rules on map values are awkward to express.
  4. The whole point of pre-computing is to prevent client-side math; a map opens the door.

Extension path: a future `adjusted_150k` is an additive column at position 13, backwards-compatible with every existing consumer.

### Rounding mode

Python banker's rounding (IEEE 754 round-half-to-even) via `round()` / `numpy.round()` / DuckDB `round()`. All three agree. The ±0.01 cents tolerance in the derivation-correctness DQ rules absorbs any residual float imprecision.

## Stage 3: Physical model

### Iceberg schema

15-column Iceberg schema with NestedField IDs 1-15 matching the spec's column order exactly. All columns `required=True` (NOT NULL). Mirror of types to Silver for the 8 passthrough columns. New columns:
- `cost_tier` → `VARCHAR` / `StringType`
- `adjusted_30k/50k/75k/100k` → `DOUBLE` / `DoubleType`
- `promoted_at` → `TIMESTAMP` / `TimestampType`

### Partition strategy: unpartitioned

Same rationale as Silver: 51 rows is smaller than any reasonable partition boundary. There is no sensible partition dimension (region/vintage/verification/cost_tier all produce small skewed groups). Sort order `state_fips ASC` gives natural index-like lookup.

### Sort order: `state_fips ASC`

Matches Silver. Natural key, most common lookup dimension, least surprising default.

### DDL CHECK constraints

Defense-in-depth: the DDL includes a multi-branch CHECK constraint for `cost_tier` that re-encodes the frozen CASE, and four CHECK constraints for the `adjusted_Nk` columns that re-verify the `round(N*1000*multiplier, 2)` formula with a ±0.01 tolerance. These fire at the database level even if the transformer or DQ engine somehow bypass the derivation logic.

### Idempotent promote pattern

`brightsmith.infra.promote.promote()` with `dedup_on=['state_fips']`. The `record_id` is a deterministic pure function of `state_fips` with prefix `rpc`, so re-running produces identical hashes. Only `promoted_at` is non-deterministic; it is metadata and never a join key.

Full Python reference implementation included in the physical model, showing the transformer as a 7-step function: select Silver columns → derive cost_tier → derive four adjusted_Nk → set promoted_at → compute record_id → reorder to match SCHEMA → promote.

### Future BEA refresh path — schema stable

Documented that when the live BEA API refresh lands, the Silver `verification_status` flip from 8/51 to 51/51 `bea_official` propagates through Gold with **zero schema changes**. The Gold DQ rule `COUNT(bea_official) = 8` updates to `= 51` in lockstep. This is the intended behavior of the Condition 7 carry-forward.

## Design decisions log

| # | Decision | Alternatives considered | Rationale |
|---|----------|------------------------|-----------|
| 1 | Mode: Greenfield | Backfill | Target table does not exist; no source code; top-down C→L→P is correct |
| 2 | Cost Tier as dependent entity (conceptual) / single column (physical) | Plain attribute | Entity status makes governance-frozen breakpoints visible; single-column flatten keeps implementation simple |
| 3 | Cost Tier via inline CASE | Lookup table, reference enum table | CASE is deterministic, auditable, faster than range joins, and breakpoints are frozen |
| 4 | Adjusted Salary as dependent measure group (conceptual) / four sibling columns (physical) | STRUCT, MAP | Closed display contract; scalar consumer access; simpler DQ rules; additive extension path |
| 5 | Surrogate key prefix `rpc`, not Silver's `rpp` | Reuse Silver's prefix | Hash namespace separation across zones; zone signaling |
| 6 | Dedup grain `['state_fips']` | `['state_fips', 'data_year']` | Single-vintage invariant means data_year is redundant for dedup |
| 7 | `purchasing_power_multiplier` carried from Silver, not recomputed | Recompute at Gold | Silver is single source of truth; recomputing risks formula drift |
| 8 | `rpp_all_items` carried from Silver, not rescaled | Rescale | Same reason |
| 9 | `promoted_at` as single Gold timestamp; drop Silver's `source_load_date` + `ingested_at` | Forward both Silver timestamps | Gold consumable contract is "when was this promoted"; full ingest chain is infra concern tracked in OpenLineage |
| 10 | 15 columns NOT NULL | Nullable adjusted_Nk | No rows have missing multiplier; 0% nulls is the contract |
| 11 | DOUBLE for all numeric (not DECIMAL) | DECIMAL(10,2) for adjusted_Nk | RPP is approximate; DECIMAL adds false precision; matches Silver |
| 12 | data_year as INTEGER (not DATE) | DATE | Calendar-year filter value; inherits Silver decision |
| 13 | Unpartitioned | Partition by region, vintage, verification | 51 rows is smaller than any partition; no dimension makes sense |
| 14 | Sort order `state_fips ASC` | state_abbr, rpp_all_items | Natural key; matches Silver |
| 15 | Rounding: banker's rounding | round-half-up | Python default matches DuckDB; spec spot-checks stable under both |
| 16 | DDL CHECK for cost_tier CASE correctness | Rely on DQ only | Defense-in-depth against transformer bypass |
| 17 | CDE flags: 8 columns CDE | 4 columns CDE (match Silver literally) | Adjusted Salary columns inherit CDE through derivation from purchasing_power_multiplier |
| 18 | No PII | — | State-level geographic data is not personal |

## Stage progression and approval

REQUIRE_HUMAN_APPROVAL is understood to be **true** for this project (CLAUDE.md specifies it for governance gates). All three model artifacts are marked `Status: PROPOSED` and `Approval: Pending human review (REQUIRE_HUMAN_APPROVAL = true)`. Stages do not auto-advance; implementation agents cannot proceed until a human sets the status to APPROVED on each artifact. Per agent scope, all three artifacts were produced in a single run — approval is the gating event, not production.

## Scope compliance

- Did NOT implement the schema in DuckDB or Iceberg.
- Did NOT write DQ rules (the physical model references expected DQ rule IDs only as alignment documentation).
- Did NOT set CDE tags in `governance/data-contracts/` — the models mirror values expected from @cde-tagger.
- Did NOT create lineage records.
- Did NOT write code in `src/gold/`.
- Did produce all three model artifacts even though the spec is mechanically small.

## Open issues carried to implementation

1. **Rounding mode agreement** between Python transformer, DuckDB CHECK, and DQ engine — all three use banker's rounding by default; ±0.01 tolerance absorbs residual imprecision. No action required, but the transformer test suite should include a deliberate half-cent case.
2. **Cost Tier distribution P1 rule** — current estimates may leave `high` or `average` empty. Full 5-tier coverage becomes a hard expectation only after the BEA refresh. P1 DQ rule "at least 3 distinct tiers" is the interim contract.
3. **Future benchmark expansion** — `adjusted_150k` etc. is an additive column path with no structural changes. Not required for this spec.

---

*— End of audit entry —*
