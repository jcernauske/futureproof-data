# Spec: gold-regional-price-parities

**Status:** READY
**Zone:** Gold (Consumable)
**Primary Agent:** @primary-agent
**Created:** 2026-04-11
**Parent Specs:** docs/specs/raw-ingest-bea-rpp.md, docs/specs/silver-base-bea-rpp.md

---

## Problem Statement

Produce the Gold consumable table `consumable.regional_price_parities` — the business-ready, display-ready reference for salary purchasing power adjustment across FutureProof. This is the table Gemma's MCP tools read from and the frontend queries for every screen that shows a salary number.

Silver (`base.bea_rpp`) already carries the core analytical payload (`rpp_all_items`, `purchasing_power_multiplier`, `verification_status`). Gold adds the three consumer conveniences:

1. **Cost tier classification** — 5-bucket enum (`very_high`, `high`, `average`, `low`, `very_low`) for boss-fight difficulty selection and frontend color coding.
2. **Pre-computed salary adjustments** — `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k` at the four common salary levels the UI displays. Avoids client-side math and makes the data immediately displayable.
3. **verification_status carry-forward** — explicitly preserved from Silver per Bronze staff-review Condition 7, so Gemma can hedge numeric precision when surfacing `estimate` rows.

No joins. No cross-source work. This is the Gold layer in "pure shaping" mode: Silver → Gold is a row-for-row promote with 4 derived columns and 1 carry-forward.

## Silver Input

| Silver Table | Rows | Status |
|---|---|---|
| base.bea_rpp | 51 | COMPLETE (silver-base-bea-rpp signed off 2026-04-10) |

**Data provenance caveat (inherited from Bronze):** 8 of 51 rows have spec-verified 2024 BEA values. 43 are primary-agent estimates pending a live BEA API refresh. Gold quality tier remains `partial_verification`.

## Gold Output

| Gold Table | Grain | Source | Rows | FutureProof Use |
|---|---|---|---|---|
| **consumable.regional_price_parities** | state_fips | base.bea_rpp | 51 | Salary purchasing power adjustment for every career the student sees. Powers MCP tools `get_regional_price_parity` and `compare_purchasing_power`. Enables frontend salary toggle and (stretch) Fight Location Lock boss. |

---

## Technical Design

### Table: consumable.regional_price_parities

- **Grain:** One row per state (`state_fips`)
- **Dedup grain:** `[state_fips]`
- **Promote pattern:** `compute_grain_id(row, ['state_fips'], prefix='rpc')`
- **Idempotent:** Yes. Re-running produces 0 new rows.

### Gold Transformations

1. **Silver passthrough** — carry forward `state_fips`, `state_name`, `state_abbr`, `census_region`, `rpp_all_items`, `purchasing_power_multiplier`, `verification_status`, `data_year` verbatim.

2. **cost_tier classification** — 5-bucket enum derived from `rpp_all_items`:

```sql
cost_tier = CASE
  WHEN rpp_all_items >= 108.0 THEN 'very_high'    -- CA, HI, DC, NJ, NY, MA, WA, ...
  WHEN rpp_all_items >= 103.0 THEN 'high'         -- CT, MD, CO, ...
  WHEN rpp_all_items >= 97.0  THEN 'average'      -- FL, IL, OR, VA, ...
  WHEN rpp_all_items >= 91.0  THEN 'low'          -- TX, GA, TN, NC, ...
  ELSE                             'very_low'     -- AR, MS, IA, OK, WV, ...
END
```

Breakpoints are inclusive on the lower bound, exclusive on the upper bound (standard left-closed convention).

3. **Salary adjustment examples** — pre-compute display-ready values at four common salary levels:

| Field | Derivation |
|---|---|
| `adjusted_30k` | `30000.0 × purchasing_power_multiplier` |
| `adjusted_50k` | `50000.0 × purchasing_power_multiplier` |
| `adjusted_75k` | `75000.0 × purchasing_power_multiplier` |
| `adjusted_100k` | `100000.0 × purchasing_power_multiplier` |

Stored as `double`. Rounded to 2 decimal places at write time (cents precision — sub-cent precision is false precision for a state-level index).

4. **Provenance columns** — `promoted_at` (Gold promotion timestamp) replaces Silver's `ingested_at`/`source_load_date`. `data_year` carries forward as provenance, not a temporal dimension.

### Gold Schema (15 columns)

| Field | Type | Required | Notes |
|---|---|---|---|
| record_id | string | yes | `compute_grain_id(row, ['state_fips'], prefix='rpc')` |
| state_fips | string | yes | 2-digit FIPS code, zero-padded |
| state_name | string | yes | Full state name |
| state_abbr | string | yes | 2-letter USPS abbreviation |
| census_region | string | yes | Northeast / Midwest / South / West |
| rpp_all_items | double | yes | RPP index (national = 100.0) |
| purchasing_power_multiplier | double | yes | `100.0 / rpp_all_items` |
| cost_tier | string | yes | very_high / high / average / low / very_low |
| adjusted_30k | double | yes | `30000 × purchasing_power_multiplier`, rounded to 2 decimals |
| adjusted_50k | double | yes | `50000 × purchasing_power_multiplier`, rounded to 2 decimals |
| adjusted_75k | double | yes | `75000 × purchasing_power_multiplier`, rounded to 2 decimals |
| adjusted_100k | double | yes | `100000 × purchasing_power_multiplier`, rounded to 2 decimals |
| verification_status | string | yes | `bea_official` or `estimate` — carried forward from Silver per Bronze Condition 7 |
| data_year | int | yes | Year of RPP estimate (2024) |
| promoted_at | timestamp | yes | Gold promotion timestamp |

### DQ Rules (Gold)

**P0 — structural and referential:**
- Row count: exactly 51
- state_fips non-null + uniqueness + canonical 51-member FIPS set
- state_name, state_abbr, census_region non-null + inherited bijections
- rpp_all_items non-null + range [70.0, 130.0]
- purchasing_power_multiplier non-null + range [0.7, 1.3]
- Inverse invariant: `abs(purchasing_power_multiplier × rpp_all_items − 100.0) ≤ 0.01`
- Passthrough integrity: every Gold row's `rpp_all_items` equals the Silver row for the same `state_fips` (join against `base.bea_rpp`) — evaluation_mode: production_only

**P0 — cost_tier:**
- cost_tier values IN (`very_high`, `high`, `average`, `low`, `very_low`)
- cost_tier classification check: for every row, verify `cost_tier` matches the CASE expression applied to `rpp_all_items`
- All 5 cost tiers are expected but only 4 may materialize with the current estimates — P1 (soft distribution)

**P0 — adjusted salary columns:**
- Each `adjusted_Nk` non-null
- Each `adjusted_Nk` within 1 cent of `N × 1000 × purchasing_power_multiplier` (rounded to 2 decimals)
- California (`state_fips='06'`) `adjusted_50k < 50000.0` (high-cost sanity — purchasing power is below national)
- Iowa (`state_fips='19'`) `adjusted_50k > 50000.0` (low-cost sanity — purchasing power is above national)

**P0 — verification_status carry-forward:**
- verification_status values IN (`bea_official`, `estimate`)
- `COUNT(*) WHERE verification_status='bea_official' = 8`
- Every `bea_official` row's `state_fips` IN the 8-state canonical set

**P0 — temporal and grain:**
- data_year = 2024
- COUNT(DISTINCT data_year) = 1
- record_id non-null + uniqueness

**P0 — spot checks (all 8 BEA-verified states):**

| state_fips | state_abbr | cost_tier | rpp | adjusted_50k (±0.01) |
|---|---|---|---|---|
| 06 | CA | very_high | 110.7 | 45167.12 |
| 15 | HI | very_high | 110.0 | 45454.55 |
| 11 | DC | very_high | 109.9 | 45495.91 |
| 34 | NJ | very_high | 108.8 | 45955.88 |
| 05 | AR | very_low | 86.9  | 57537.40 |
| 28 | MS | very_low | 87.0  | 57471.26 |
| 19 | IA | very_low | 87.8  | 56947.61 |
| 40 | OK | very_low | 87.8  | 56947.61 |

**P1:**
- source table freshness (base.bea_rpp load date within 400 days)
- promoted_at non-null
- cost_tier distribution: at least 3 distinct tiers present (soft — exact distribution depends on estimate values)

### Data Contract: consumable.regional_price_parities

| Property | Value |
|---|---|
| Owner | @data-steward |
| SLA | Annual refresh when BEA publishes new RPPs (each February) |
| Freshness | Static for hackathon. Yearly refresh post-hackathon. |
| Quality tier | `partial_verification` (carries forward from Silver/Bronze — 43/51 rows are estimates) |
| Consumers | MCP tools (`get_regional_price_parity`, `compare_purchasing_power`), frontend salary display, Fight Location Lock boss (stretch) |
| Row count guarantee | Exactly 51 |
| Null guarantee | 0% nulls on all 15 columns |

---

## Bronze Staff Review Conditions

- **Condition 6 (verification_status column)** — discharged at Silver; Gold explicitly preserves the column as column 13 of 15.
- **Condition 7 (Gold carry-forward)** — **implemented here.** The Gold table carries `verification_status` unchanged from Silver with a P0 count-of-8 rule and allow-list subset rule. MCP carry-forward (tool response must include `data_source` per row, strict mode refuses unverified rows) is still forward-only — documented as a carry-forward obligation for `mcp-bea-rpp`.

## Business Glossary Terms

Already present after Bronze + Silver:
- BT-098 Regional Price Parity (RPP)
- BT-099 Purchasing Power Multiplier
- BT-100 State FIPS Code
- BT-101 State Name
- BT-102 RPP Data Year
- BT-103 USPS State Abbreviation
- BT-104 Census Region
- BT-105 Data Verification Status

New terms to add during this Gold spec:
- **BT-106 Cost Tier** — Five-bucket classification of state-level cost of living derived from BEA Regional Price Parities. Values: `very_high` (RPP ≥ 108), `high` (103 ≤ RPP < 108), `average` (97 ≤ RPP < 103), `low` (91 ≤ RPP < 97), `very_low` (RPP < 91). Used for frontend color coding, boss-fight difficulty selection, and broad regional comparisons.
- **BT-107 Adjusted Salary** — A national salary figure multiplied by a state's purchasing power multiplier to yield the equivalent local purchasing power. Derived as `national_salary × (100 / state_RPP)`. Pre-computed at $30K, $50K, $75K, $100K levels in the Gold table so the frontend and Gemma can display values without client-side math.

---

## Agent Workflow (Gold Greenfield)

1. @governance-reviewer — pre-implementation review
2. @data-steward — BT-106, BT-107 entries
3. @semantic-modeler — conceptual → logical → physical
4. @data-analyst — EDA on Gold-derived columns (verify cost_tier distribution, adjusted salary math)
5. @dq-rule-writer — write rules from EDA evidence
6. @primary-agent — build Gold transformer with the idempotent promote pattern
7. @cab-review — greenfield, expected SKIP
8. @dq-engineer — execute rules against real Iceberg data
9. @chaos-monkey — adversarial hardening (focus on cost_tier boundary edges, adjusted_Nk arithmetic, verification_status carry-forward)
10. @entity-resolver — state FIPS canonical, expected SKIP
11. @pii-scanner — no PII, expected SKIP
12. @temporal-modeler — single-vintage static, expected SKIP
13. @adversarial-auditor — skeptical audit of Gold artifacts
14. @lineage-tracker — OpenLineage capture
15. @cde-tagger — CDE mapping
16. @doc-generator — Gold contract, dictionary, glossary BT-106/107
17. @governance-reviewer — post-implementation review
18. @staff-engineer — final sign-off

## Governance Artifacts

- [ ] Models: `governance/models/gold-regional-price-parities-{conceptual,logical,physical}.md`
- [ ] EDA: `governance/eda/gold-regional-price-parities-eda.md`
- [ ] DQ rules: `governance/dq-rules/gold-regional-price-parities.json`
- [ ] DQ results + scorecard
- [ ] Chaos report
- [ ] Adversarial audit
- [ ] Entity resolution / PII / temporal decisions
- [ ] Lineage
- [ ] CDE tagging
- [ ] Data contract: `governance/data-contracts/gold-regional-price-parities.yaml`
- [ ] Data dictionary updates: 15 columns for `consumable.regional_price_parities`
- [ ] Business glossary updates: BT-106, BT-107
- [ ] Approvals: `governance/approvals/gold-regional-price-parities-{pre,post,staff}-review.md`

## Cross-Source Integration

None. Gold BEA RPP is orthogonal to the SOC/CIP join graph. It joins at query time by the student's selected state — a frontend/agent concern, not a pipeline join.

## Estimated Effort

Smallest Gold transformation in the project. The Silver→Gold promote is 4 trivial derivations plus 2 carry-forwards. Most cycle time is governance artifacts.

---

*— End of Spec —*
