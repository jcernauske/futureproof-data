# Spec: silver-base-bea-rpp

**Status:** READY
**Zone:** Silver
**Primary Agent:** @primary-agent
**Created:** 2026-04-10
**Parent Spec:** docs/specs/raw-ingest-bea-rpp.md

---

## Problem Statement

Promote `bronze.bea_rpp` (51 rows: 50 states + DC) to a clean, purpose-shaped Silver base table `base.bea_rpp` that is immediately consumable by Gold (`consumable.regional_price_parities`), the MCP tools (`get_regional_price_parity`, `compare_purchasing_power`), and the frontend salary-adjustment display.

The Silver layer adds the three derivations the frontend and Gemma actually query by:

1. **USPS state abbreviation** — the 2-letter code the frontend uses for display and state-selection mapping (e.g., `"CA"`, `"IA"`).
2. **Census region** — Northeast / Midwest / South / West, for regional comparisons.
3. **Purchasing power multiplier** — pre-computed `100.0 / rpp_all_items`, the factor by which a national salary is scaled to local purchasing power. Pre-computed here so every downstream consumer reads the same value.

No joins, no concept normalization, no cross-source work. This is the smallest Silver transformation in the project.

## Bronze Input

| Bronze Table | Rows | Status |
|-------------|------|--------|
| bronze.bea_rpp | 51 | COMPLETE (raw-ingest-bea-rpp signed off 2026-04-10) |

**Data provenance caveat (inherited from Bronze):** 8 of 51 RPP values are BEA-verified (CA, HI, DC, NJ, AR, MS, IA, OK). 43 are primary-agent estimates pending a live BEA API refresh. Silver MUST NOT claim more verification than Bronze has. Quality tier remains `partial_verification`.

## Silver Output

| Silver Table | Grain | Source | Rows | FutureProof Use |
|-------------|-------|--------|------|-----------------|
| **base.bea_rpp** | state_fips | bronze.bea_rpp | 51 | Salary purchasing power adjustment for every career the student sees. Joined at query time by the student's selected state (not by SOC/CIP). |

---

## Technical Design

### Table: base.bea_rpp

- **Grain:** One row per state (`state_fips`)
- **Dedup grain:** `[state_fips]`
- **Promote pattern:** `compute_grain_id(row, ['state_fips'], prefix='rpp')`
- **Idempotent:** Yes. Re-running produces 0 new rows.

### Silver Transformations

1. **state_fips normalization** — carry `geo_fips` through as `state_fips`; validate 2-digit zero-padded string. Confirm all 51 expected codes present (50 states + `11` for DC).

2. **state_name passthrough** — `geo_name` → `state_name`, no changes.

3. **state_abbr derivation** — static FIPS → 2-letter USPS lookup. The lookup must be an in-code constant (structural, not entity-specific data) or loaded from a governance file. All 51 values are a fixed property of US geography and do not violate the "no hardcoded entity data" rule. If using an in-code constant, document that exception in `governance/exceptions/` if required by the project convention.

4. **census_region derivation** — static FIPS → Census region lookup (`Northeast`, `Midwest`, `South`, `West`). Use the standard U.S. Census Bureau assignment. Note: DC sits in `South` under the Census mapping despite its Northeast-like RPP; this is a documented quirk, not a bug.

5. **rpp_all_items passthrough** — `rpp_all_items` carried verbatim. No rescaling. Already on national=100 scale.

6. **purchasing_power_multiplier** — pre-compute `100.0 / rpp_all_items`. Store as double. Acts as the single source of truth for salary adjustment across the rest of the pipeline.

7. **data_year passthrough** — constant `2024` for the current vintage.

8. **verification_status derivation** — per-row label with values `{bea_official, estimate}`. Derived from a hard-coded allow-list of the 8 BEA-verified `state_fips` codes: `{'06', '15', '11', '34', '05', '28', '19', '40'}` (CA, HI, DC, NJ, AR, MS, IA, OK). All 43 other rows get `estimate`. This column exists so the Gold contract, the MCP tool response, and any downstream consumer can surface data provenance on a per-row basis — closes Bronze HIGH-3 per `governance/approvals/raw-ingest-bea-rpp-staff-review.md` Ruling 2 / Condition 6. When the live BEA API refresh lands, the allow-list becomes all 51 codes and every row becomes `bea_official`.

9. **Provenance columns** — `source_load_date` (from Bronze `load_date`) and `ingested_at` (Silver promotion timestamp).

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | `compute_grain_id(row, ['state_fips'], prefix='rpp')` |
| state_fips | string | yes | 2-digit FIPS code, zero-padded |
| state_name | string | yes | Full state name |
| state_abbr | string | yes | 2-letter USPS abbreviation (derived) |
| census_region | string | yes | Northeast / Midwest / South / West (derived) |
| rpp_all_items | double | yes | RPP index (national = 100.0) |
| purchasing_power_multiplier | double | yes | `100.0 / rpp_all_items` |
| verification_status | string | yes | `bea_official` for 8 spec-verified states, `estimate` for the other 43. Closes Bronze HIGH-3 / staff-review Ruling 2. |
| data_year | int | yes | Year of RPP estimate (2024) |
| source_load_date | date | yes | Bronze load_date passthrough |
| ingested_at | timestamp | yes | Silver promotion timestamp |

### DQ Rules (Silver)

- Row count: exactly 51 (P0)
- state_fips non-null and uniqueness (P0)
- state_abbr non-null, exactly 2 characters, all uppercase, values in the canonical USPS 51-member set (P0)
- census_region values IN `('Northeast', 'Midwest', 'South', 'West')` (P0)
- All 4 census regions represented (P0)
- purchasing_power_multiplier range: `0.7 ≤ x ≤ 1.3` (P0)
- Inverse invariant: `purchasing_power_multiplier × rpp_all_items ≈ 100.0` within tolerance `0.01` (P0)
- rpp_all_items passthrough invariant: every Silver row's `rpp_all_items` equals the Bronze row's value for the same `state_fips` (P0 — referential integrity to source)
- record_id non-null and uniqueness (P0)
- data_year = 2024 (P0 — mirror of Bronze RAW-BEA-010)
- state_fips bijection with state_name (P1)
- state_fips bijection with state_abbr (P1)
- `COUNT(DISTINCT data_year) = 1` — hardens the supersession-by-replacement contract from `governance/temporal/raw-ingest-bea-rpp.md` (P0)
- verification_status values IN `('bea_official', 'estimate')` (P0)
- `COUNT(*) WHERE verification_status='bea_official' = 8` (P0) — enforces the current Bronze verification state. When the live BEA API refresh lands, this rule flips to `= 51` and the deferred condition closes.
- Every `bea_official` row must have `state_fips` IN `{'06','15','11','34','05','28','19','40'}` (P0)

### Spot checks — all 8 BEA-verified states (P0)

| state_fips | state_abbr | census_region | rpp_all_items | purchasing_power_multiplier (±0.001) | verification_status |
|---|---|---|---|---|---|
| 06 | CA | West | 110.7 | 0.9034 | bea_official |
| 15 | HI | West | 110.0 | 0.9091 | bea_official |
| 11 | DC | South (documented Census quirk) | 109.9 | 0.9099 | bea_official |
| 34 | NJ | Northeast | 108.8 | 0.9191 | bea_official |
| 05 | AR | South | 86.9 | 1.1507 | bea_official |
| 28 | MS | South | 87.0 | 1.1494 | bea_official |
| 19 | IA | Midwest | 87.8 | 1.1390 | bea_official |
| 40 | OK | South | 87.8 | 1.1390 | bea_official |

---

## Business Glossary Terms

Already present after the Bronze spec run:

- **BT-098** Regional Price Parity (RPP)
- **BT-099** Purchasing Power Multiplier
- **BT-100** State FIPS Code
- **BT-101** State Name
- **BT-102** RPP Data Year

New terms to add during this Silver spec:

- **BT-103** USPS State Abbreviation — Two-letter uppercase postal abbreviation assigned by the United States Postal Service for each state and the District of Columbia (e.g., `CA`, `IA`, `DC`). Used as the frontend display identifier and the state-selection key in the MCP tool signatures.
- **BT-104** Census Region — One of four U.S. Census Bureau groupings (Northeast, Midwest, South, West) used to aggregate states for regional comparisons. DC is placed in `South` by Census convention.

---

## Agent Workflow (Silver Greenfield)

1. @governance-reviewer — pre-implementation review
2. @data-steward — confirm BT-103 and BT-104 and any term drift
3. @semantic-modeler — conceptual → logical → physical models
4. @data-analyst — EDA on the transformation shape (verify state_abbr derivation, census region distribution, multiplier numerics)
5. @dq-rule-writer — write rules from EDA evidence
6. @primary-agent — build Silver transformer using the `promote` idempotent pattern
7. @dq-engineer — execute rules against real Iceberg data
8. @chaos-monkey — adversarial hardening
9. @entity-resolver — state FIPS is canonical; skip recommendation documented
10. @pii-scanner — no PII; skip recommendation documented
11. @temporal-modeler — single-vintage static reference; skip recommendation documented
12. @adversarial-auditor — skeptical audit of Silver artifacts
13. @lineage-tracker — OpenLineage capture
14. @cde-tagger — CDE mapping (state_abbr, census_region, purchasing_power_multiplier are strong CDE candidates)
15. @doc-generator — Silver data contract, dictionary entries, glossary terms BT-103/BT-104
16. @governance-reviewer — post-implementation review
17. @staff-engineer — final sign-off

## Governance Artifacts

- [ ] Models: `governance/models/silver-base-bea-rpp-{conceptual,logical,physical}.md`
- [ ] EDA: `governance/eda/silver-base-bea-rpp-eda.md`
- [ ] DQ rules: `governance/dq-rules/silver-base-bea-rpp.json`
- [ ] DQ results: `governance/dq-results/silver-base-bea-rpp-*.json`
- [ ] DQ scorecard: `governance/dq-scorecards/silver-base-bea-rpp-scorecard.md`
- [ ] Chaos report: `governance/chaos-reports/silver-base-bea-rpp-chaos.md`
- [ ] Adversarial audit: `governance/adversarial-audits/silver-base-bea-rpp.md`
- [ ] Entity resolution decision: `governance/entity-resolution/silver-base-bea-rpp.md`
- [ ] PII scan: `governance/pii-scans/silver-base-bea-rpp.md`
- [ ] Temporal strategy: `governance/temporal/silver-base-bea-rpp.md`
- [ ] Lineage: `governance/lineage/silver-base-bea-rpp-{timestamp}.json`
- [ ] CDE tagging: `governance/cde-tagging/silver-base-bea-rpp.md`
- [ ] Data contract: `governance/data-contracts/silver-base-bea-rpp.yaml`
- [ ] Data dictionary updates: 11 columns for `base.bea_rpp`
- [ ] Business glossary updates: BT-103 (USPS State Abbreviation), BT-104 (Census Region), BT-105 (Data Verification Status)
- [ ] Approvals: `governance/approvals/silver-base-bea-rpp-{pre,post,staff}-review.md`

## Bronze Staff Review Conditions

This Silver spec explicitly implements the Bronze staff-engineer ruling at `governance/approvals/raw-ingest-bea-rpp-staff-review.md`:

- **Condition 6 (implemented here):** Per-row `verification_status` column is added as column 11 of `base.bea_rpp` with values `{bea_official, estimate}`, derived from the 8-state allow-list, with a P0 DQ rule `COUNT(*) WHERE verification_status='bea_official' = 8`. Closes the deferral cleanly.
- **Condition 7 (forward-only):** Gold (`consumable.regional_price_parities`) and the MCP tool must propagate `verification_status` downstream. Out of scope here but explicitly documented as a carry-forward requirement for the Gold and MCP specs.

## Inherited Constraints from Bronze

- Quality tier remains `partial_verification` (43/51 estimated rows). Silver cannot claim more verification than Bronze.
- The supersession strategy is full-table replacement on refresh, not SCD2. Silver must honor that.
- When the live BEA API refresh lands post-hackathon, the `verification_status` allow-list becomes all 51 codes and the `= 8` DQ rule flips to `= 51`. The rest of the pipeline is refresh-ready without further schema changes.

## Cross-Source Integration

None. BEA RPP is orthogonal to the SOC/CIP join graph. The Silver table joins at query time by the student's selected state — a frontend/agent concern, not a pipeline join.

## Estimated Effort

Smallest Silver transformation in the project. ~1 hour for the primary-agent build; most of the cycle time is governance artifacts.

---

*— End of Spec —*
