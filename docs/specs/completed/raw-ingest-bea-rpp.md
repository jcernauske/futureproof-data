# Spec: raw-ingest-bea-rpp

**Status:** COMPLETE
**Zone:** Raw → Silver → Gold → MCP
**Primary Agent:** @primary-agent
**Created:** 2026-04-09

---

## Problem Statement

Ingest Bureau of Economic Analysis (BEA) Regional Price Parities to enable FutureProof's "What does this salary mean where you live?" feature. A $50K national average salary buys vastly different lifestyles in California (RPP 110.7) vs. Iowa (RPP 87.8). Without this adjustment, every salary figure in the product is misleading for students who plan to live in a specific state.

This is a tiny reference table — 51 rows (50 states + DC), one index per row. The math is simple: `national_salary × (100 / state_RPP) = local purchasing power`. The pipeline produces a Gold consumable table and an MCP tool that Gemma calls when presenting salary data to students.

This also enables the **Fight Location Lock** boss from the PRD (Tier 3 stretch): a boss that tests whether the career's salary actually provides a good life in the student's home state.

## Source Data

- **Source:** U.S. Bureau of Economic Analysis (BEA), Regional Economic Accounts
- **Dataset:** Regional Price Parities by State — All Items (table SARPP)
- **Year:** 2024 (most recent available, released February 2026)
- **Method:** BEA API (preferred) or manual CSV download from BEA Interactive Data Application
- **API endpoint:** `https://apps.bea.gov/api/data/?&UserID={API_KEY}&method=GetData&datasetname=Regional&TableName=SARPP&LineCode=1&Year=2024&GeoFips=STATE&ResultFormat=JSON`
- **Fallback:** Manual download from BEA Interactive Data Application at `https://apps.bea.gov/itable/?ReqID=70&step=1` → table SARPP → All Items → 2024 → CSV export to `data/raw/bea_cache/bea_rpp_2024.csv`
- **API key:** Free registration at `https://apps.bea.gov/API/signup/` — key goes in `.env` as `BEA_API_KEY`
- **Entities:** 51 rows (50 states + District of Columbia)
- **Size:** Trivial (~5KB)
- **License:** U.S. Government Work — public domain
- **Update cadence:** Annual (released each February for the prior year)

### What RPPs Measure

Regional Price Parities measure differences in price levels across states for a given year, expressed as a percentage of the overall national price level (national = 100.0). An RPP of 110.7 (California) means prices are 10.7% higher than the national average. An RPP of 87.8 (Iowa) means prices are 12.2% lower.

### Key 2024 Values (for DQ validation)

| State | RPP | Notes |
|-------|-----|-------|
| California | 110.7 | Highest state |
| Hawaii | 110.0 | Second highest |
| District of Columbia | 109.9 | Not a state but included |
| New Jersey | 108.8 | Third highest state |
| Arkansas | 86.9 | Lowest |
| Mississippi | 87.0 | Second lowest |
| Iowa | 87.8 | Third lowest (tied) |
| Oklahoma | 87.8 | Third lowest (tied) |

## Success Criteria

- [ ] Raw data lands in Iceberg table `raw.bea_rpp`
- [ ] All 51 geographic entities ingested (50 states + DC)
- [ ] Silver base table `base.bea_rpp` produced with state FIPS codes and abbreviations
- [ ] Gold consumable table `consumable.regional_price_parities` produced with purchasing power adjustment fields
- [ ] MCP tool `get_regional_price_parity(state)` queryable by Gemma agent
- [ ] DQ rules written and passing at each zone
- [ ] Data contract produced
- [ ] Business glossary terms defined

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: raw.bea_rpp

- **Grain:** One row per geographic entity (GeoFips)
- **Dedup grain:** [geo_fips]
- **Expected rows:** 51

### Ingestor

- **Class:** `BeaRppIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/bea_rpp_ingestor.py`
- **Implementation notes:**
  - Attempt BEA API call first (requires `BEA_API_KEY` in `.env`)
  - API returns JSON with `BEAAPI.Results.Data` array, each element has: `GeoFips`, `GeoName`, `TimePeriod`, `DataValue`, `CL_UNIT`, `UNIT_MULT`
  - `DataValue` is the RPP index as a string (e.g., "110.7") — parse to float
  - If API call fails (no key, rate limited, timeout), fall back to reading CSV from `data/raw/bea_cache/bea_rpp_2024.csv`
  - Filter to `LineCode=1` (All Items) — exclude sub-components like Goods, Services, Rents
  - Filter to state-level GeoFips only (2-digit codes 01-56, plus 11 for DC) — exclude metro areas if present
  - Set `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)`

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| geo_fips | string | yes | 2-digit state FIPS code (e.g., "06" for California, "19" for Iowa) |
| geo_name | string | yes | State name (e.g., "California", "Iowa") |
| rpp_all_items | double | yes | Regional Price Parity index, All Items (national = 100.0) |
| data_year | int | yes | Year of the RPP estimate (2024) |
| source_url | string | yes | BEA API URL or manual download path |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_method | string | yes | "bea_api" or "csv_cache" |
| load_date | date | yes | Date of load |

### DQ Rules (Bronze)

- Row count: exactly 51 (P0)
- RPP range: 80.0 ≤ rpp_all_items ≤ 130.0 (P0 — no state should be outside this range)
- RPP non-null: 100% (P0)
- geo_fips uniqueness (P0)
- geo_name non-null: 100% (P0)
- Spot check: California RPP between 108.0 and 115.0 (P0 — sanity guard against stale/wrong data)
- Spot check: Arkansas RPP between 84.0 and 90.0 (P0)
- data_year = 2024 for all rows (P0)
- geo_fips format: 2-digit numeric string (P1)

---

## Zone 2: Silver (Normalize + Model)

### Iceberg Table: base.bea_rpp

- **Grain:** One row per state (state_fips)
- **Dedup grain:** [state_fips]
- **Promote pattern:** `compute_grain_id(row, ['state_fips'], prefix='rpp')`

### Silver Transformations

1. **State FIPS normalization:** Validate as 2-digit string, zero-padded. Confirm all 50 states + DC present.

2. **Add state abbreviation:** Derive 2-letter USPS state abbreviation from FIPS code (static lookup — AL, AK, AZ, ..., WY, DC). This is the field the frontend will use for display and the field the user's state selection maps to.

3. **Add state region:** Derive Census region (Northeast, Midwest, South, West) from FIPS code. Useful for regional comparisons in the frontend.

4. **RPP passthrough:** `rpp_all_items` carried verbatim. No rescaling — this is already on a national=100 scale.

5. **Purchasing power multiplier:** Pre-compute `purchasing_power_multiplier = 100.0 / rpp_all_items`. This is the factor you multiply a national salary by to get local purchasing power. California: `100 / 110.7 = 0.9034` (salary buys 90.3% as much). Iowa: `100 / 87.8 = 1.1390` (salary buys 113.9% as much).

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `rpp`) |
| state_fips | string | yes | 2-digit FIPS code, zero-padded |
| state_name | string | yes | Full state name |
| state_abbr | string | yes | 2-letter USPS abbreviation (derived) |
| census_region | string | yes | Northeast, Midwest, South, West (derived) |
| rpp_all_items | double | yes | RPP index (national = 100.0) |
| purchasing_power_multiplier | double | yes | `100.0 / rpp_all_items` — multiply national salary by this |
| data_year | int | yes | Year of RPP estimate |
| source_load_date | date | yes | |
| ingested_at | timestamp | yes | Silver promotion timestamp |

### DQ Rules (Silver)

- Row count: exactly 51 (P0)
- state_abbr non-null, 2 characters, all uppercase (P0)
- purchasing_power_multiplier range: 0.7 ≤ x ≤ 1.3 (P0 — no state should be outside this)
- purchasing_power_multiplier × rpp_all_items ≈ 100.0 within tolerance 0.01 (P0 — inverse invariant)
- census_region values IN ('Northeast', 'Midwest', 'South', 'West') (P0)
- All 4 census regions represented (P0)
- state_fips uniqueness (P0)

### Business Glossary Terms

| Term ID | Name | Definition |
|---------|------|-----------|
| BT-098 | Regional Price Parity (RPP) | A BEA index measuring the price level of goods and services in a state relative to the national average (set to 100.0). An RPP of 110 means prices are 10% higher than national average. Used to adjust national salary figures to local purchasing power. Source: BEA Regional Economic Accounts, annual. |
| BT-099 | Purchasing Power Multiplier | The factor by which a national salary is multiplied to reflect local purchasing power in a given state. Derived as `100 / RPP`. A multiplier of 0.90 means $50K nationally buys only $45K worth of goods locally. A multiplier of 1.14 means $50K buys $57K worth. |

---

## Zone 3: Gold (Consumable Product)

### Iceberg Table: consumable.regional_price_parities

- **Grain:** One row per state
- **Dedup grain:** [state_fips]
- **Promote pattern:** `compute_grain_id(row, ['state_fips'], prefix='rpc')`

### Gold Transformations

1. **All Silver fields carried forward.**

2. **Cost tier classification:** Categorize states into cost tiers for boss fight and display:

```
cost_tier = CASE
  WHEN rpp_all_items >= 108.0 THEN 'very_high'    -- CA, HI, DC, NJ, NY, MA, WA, ...
  WHEN rpp_all_items >= 103.0 THEN 'high'          -- CT, MD, CO, ...
  WHEN rpp_all_items >= 97.0  THEN 'average'       -- FL, IL, OR, VA, ...
  WHEN rpp_all_items >= 91.0  THEN 'low'           -- TX, GA, TN, NC, ...
  ELSE                             'very_low'      -- AR, MS, IA, OK, WV, ...
END
```

3. **Salary adjustment examples:** Pre-compute display-ready examples at common salary levels:

| Field | Type | Derivation |
|-------|------|-----------|
| adjusted_30k | double | `30000 × purchasing_power_multiplier` |
| adjusted_50k | double | `50000 × purchasing_power_multiplier` |
| adjusted_75k | double | `75000 × purchasing_power_multiplier` |
| adjusted_100k | double | `100000 × purchasing_power_multiplier` |

These are convenience fields for the frontend — avoids client-side math and makes the data immediately displayable.

### Gold Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `rpc`) |
| state_fips | string | yes | 2-digit FIPS code |
| state_name | string | yes | Full state name |
| state_abbr | string | yes | 2-letter USPS abbreviation |
| census_region | string | yes | Northeast, Midwest, South, West |
| rpp_all_items | double | yes | RPP index (national = 100.0) |
| purchasing_power_multiplier | double | yes | Salary adjustment factor |
| cost_tier | string | yes | very_high / high / average / low / very_low |
| adjusted_30k | double | yes | $30K adjusted for local purchasing power |
| adjusted_50k | double | yes | $50K adjusted |
| adjusted_75k | double | yes | $75K adjusted |
| adjusted_100k | double | yes | $100K adjusted |
| data_year | int | yes | Year of RPP estimate |
| promoted_at | timestamp | yes | Gold promotion timestamp |

### DQ Rules (Gold)

- Row count: exactly 51 (P0)
- cost_tier values IN ('very_high', 'high', 'average', 'low', 'very_low') (P0)
- All 5 cost tiers represented (P1 — soft, distribution may not hit all 5)
- adjusted_50k = 50000 × purchasing_power_multiplier within tolerance $1 (P0 — computation check)
- state_fips uniqueness (P0)
- Cross-check: California adjusted_50k < 50000 (P0 — high cost state, purchasing power is below national)
- Cross-check: Iowa adjusted_50k > 50000 (P0 — low cost state, purchasing power is above national)

### Data Contract: consumable.regional_price_parities

| Property | Value |
|----------|-------|
| Owner | @data-steward |
| SLA | Annual refresh when BEA publishes new RPPs (each February) |
| Freshness | Static for hackathon. Yearly refresh post-hackathon. |
| Quality tier | High (government statistical data, not LLM-generated) |
| Consumers | Gemma MCP agent, frontend salary display, Fight Location Lock boss (stretch) |
| Row count guarantee | Exactly 51 |
| Null guarantee | 0% nulls on all fields |

---

## Zone 4: MCP (Tool Interface)

### New MCP Tool: `get_regional_price_parity(state)`

Exposes `consumable.regional_price_parities` to the Gemma agent.

**Input:** `state` (string — accepts state abbreviation "CA", full name "California", or FIPS code "06")

**Returns:**
```json
{
  "state_name": "California",
  "state_abbr": "CA",
  "rpp_all_items": 110.7,
  "purchasing_power_multiplier": 0.9034,
  "cost_tier": "very_high",
  "adjusted_examples": {
    "30k": 27101,
    "50k": 45168,
    "75k": 67752,
    "100k": 90336
  }
}
```

**Usage in Gemma guidance:** When presenting salary data, Gemma calls this tool with the student's state and adjusts all salary figures: "The median salary for this career is $65,000 nationally. In California, that's equivalent to about $58,700 in purchasing power — prices are about 11% higher than the national average."

### New MCP Tool: `compare_purchasing_power(salary, state_a, state_b)`

Convenience tool for the "What if I move?" scenario.

**Input:** `salary` (double), `state_a` (string), `state_b` (string)

**Returns:**
```json
{
  "salary": 65000,
  "state_a": {
    "state_name": "California",
    "adjusted_salary": 58722,
    "cost_tier": "very_high"
  },
  "state_b": {
    "state_name": "Iowa",
    "adjusted_salary": 74032,
    "cost_tier": "very_low"
  },
  "difference": 15310,
  "difference_pct": 26.1
}
```

---

## Zone 5: Fight Location Lock Boss (Stretch Goal)

If time allows, this data powers the Tier 3 boss from the PRD. The boss tests whether the career's salary provides a good life in the student's home state.

**Boss formula (draft):**
```
location_lock_score = f(occupation_wage, student_state_rpp, occupation_geographic_concentration)
```

A high-paying career in a high-cost state where the industry is geographically concentrated (e.g., tech in CA, finance in NY) means the student is "location locked" — they can't move to a cheaper state without leaving the industry. A career with similar pay across many states (e.g., nursing, teaching) has low location lock.

This requires BLS geographic wage data (not in scope for this spec) to compute properly. For the hackathon, the RPP data alone enables the frontend purchasing power display without the full boss implementation.

---

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implement ingestor (BEA API fetch + CSV fallback)
3. @data-analyst — EDA (minimal — 51 rows, well-understood data)
4. @domain-context — Synthesize BEA RPP methodology context
5. @dq-rule-writer — Write DQ rules for all zones
6. @dq-engineer — Execute rules
7. @semantic-modeler — Conceptual → logical → physical models
8. @primary-agent — Build Silver + Gold transformers
9. @data-contract-author — Data contract
10. @lineage-tracker — OpenLineage capture
11. @cde-tagger — CDE mapping
12. @doc-generator — Data dictionary entries
13. @governance-reviewer — Post-implementation check
14. @staff-engineer — Final review

## Governance Artifacts

- [ ] EDA report: `governance/eda/raw-bea-rpp-eda.md`
- [ ] Domain context: `governance/domain-context.md` (append BEA RPP section)
- [ ] DQ rules: `governance/dq-rules/raw-ingest-bea-rpp.json`, `governance/dq-rules/silver-base-bea-rpp.json`, `governance/dq-rules/gold-regional-price-parities.json`
- [ ] Models: `governance/models/silver-base-bea-rpp-{conceptual,logical,physical}.md`, `governance/models/gold-regional-price-parities-{conceptual,logical,physical}.md`
- [ ] Data contract: `governance/data-contracts/consumable-regional-price-parities.md`
- [ ] Lineage: `governance/lineage/raw-ingest-bea-rpp-{timestamp}.json`
- [ ] Business glossary updates: BT-098, BT-099
- [ ] Data dictionary entries

## Cross-Source Integration Notes

This is the fifth data source in the FutureProof pipeline:

1. **College Scorecard** (COMPLETE) — program-level outcomes, CIP codes
2. **BLS OOH** (COMPLETE) — occupation projections, SOC codes
3. **O*NET** (COMPLETE) — task-level occupation data, SOC codes
4. **Karpathy AI Exposure** (COMPLETE) — AI exposure scores, SOC codes
5. **BEA Regional Price Parities** (this spec) — state-level cost of living, state FIPS codes

Join topology:
```
BEA RPP (state_fips / state_abbr)
  → consumable.regional_price_parities
    → MCP tool: get_regional_price_parity(state)
    → MCP tool: compare_purchasing_power(salary, state_a, state_b)
    → Frontend: salary adjustment display
    → (Stretch) Fight Location Lock boss
```

**Note:** This table does NOT join to the other Gold tables by SOC or CIP code. It joins at query time based on the student's selected state — a frontend/agent concern, not a pipeline join. The pipeline just produces the reference table; Gemma applies it when presenting salary data.

## Estimated Effort

Smallest pipeline in the project. 51 rows, no cross-source joins, no complex transformations.

| Step | Estimate |
|------|----------|
| Bronze ingest (BEA API + fallback) | 1 hour |
| Silver + Gold transforms | 1 hour |
| MCP tools | 30 minutes |
| DQ rules + governance | 1 hour |
| **Total** | **~3-4 hours** |

---

## Frontend Integration Notes (For Future Spec)

When the frontend is built, every screen that displays a salary figure should include an option to adjust for local purchasing power:

- **Screen 4 (Stage 2 Reveal):** "Median salary: $52,000 nationally" → toggle → "In California: ~$47,000 purchasing power"
- **Screen 6 (Branch Tree):** Each branch node's ERN stat can be adjusted by state
- **Screen 8 (Compare):** Side-by-side salary comparison can factor in where each student plans to live

The student selects their state once (during onboarding or as a setting) and all salary figures adjust automatically. This is a frontend concern, not a pipeline concern — the MCP tool provides the data, the frontend applies it.

---

*— End of Spec —*
