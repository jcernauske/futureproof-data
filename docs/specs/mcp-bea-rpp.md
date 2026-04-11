# Spec: mcp-bea-rpp

**Status:** READY
**Zone:** MCP (AI-Ready)
**Primary Agent:** @primary-agent
**Created:** 2026-04-11
**Parent Specs:** raw-ingest-bea-rpp, silver-base-bea-rpp, gold-regional-price-parities

---

## Problem Statement

Expose `consumable.regional_price_parities` to the Gemma agent through two MCP tools so Gemma can adjust every salary figure it presents to a student to the student's selected state. Without this, every salary number in the product is misleading for students who plan to live in a specific state.

Additionally, this spec closes **Bronze Condition 7 (MCP half)** per `governance/approvals/raw-ingest-bea-rpp-staff-review.md`:

1. Every tool response must include a per-row `verification_status` (surfaced as `data_source` in the payload) so Gemma can hedge numeric precision when the underlying value is an estimate.
2. A strict mode (`verified_only: true`) on both tools must refuse to return rows where `verification_status='estimate'`, returning a structured `null` result instead.

This is a thin read-only tool layer over a well-governed Gold table. No transformations. No new data. Direct query passthrough with schema-enforced response contracts.

## Gold Input

| Gold Table | Rows | Status |
|---|---|---|
| consumable.regional_price_parities | 51 | COMPLETE (gold-regional-price-parities signed off 2026-04-11, contract status ACTIVE) |

## MCP Tools

### Tool 1: `get_regional_price_parity`

Returns the RPP record for a single state. Accepts the state as a 2-letter abbreviation, a full name, or a 2-digit FIPS code — Gemma will receive user input in any of those forms.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "state": {
      "type": "string",
      "description": "US state identifier. Accepts: 2-letter USPS abbreviation (e.g., 'CA'), full state name (e.g., 'California'), or 2-digit FIPS code (e.g., '06'). Case-insensitive for abbreviations and names. Includes District of Columbia as 'DC' / 'District of Columbia' / '11'."
    },
    "verified_only": {
      "type": "boolean",
      "description": "If true, refuse to return rows where verification_status='estimate'. Defaults to false. Strict mode for regulated contexts where only BEA-authoritative values are acceptable.",
      "default": false
    }
  },
  "required": ["state"]
}
```

**Success response:**
```json
{
  "data": {
    "state_name": "California",
    "state_abbr": "CA",
    "state_fips": "06",
    "census_region": "West",
    "rpp_all_items": 110.7,
    "purchasing_power_multiplier": 0.9033,
    "cost_tier": "very_high",
    "adjusted_examples": {
      "30k": 27100.27,
      "50k": 45167.12,
      "75k": 67750.68,
      "100k": 90334.24
    },
    "data_source": "bea_official",
    "data_year": 2024
  },
  "row_count": 1,
  "governance": {
    "table": "consumable.regional_price_parities",
    "quality_tier": "partial_verification",
    "owner": "@data-steward"
  }
}
```

**Null-case responses:**

- **Unknown state:**
  ```json
  {"data": null, "message": "Unknown state: 'Xanadu'. Expected a US state (50 states + DC) by USPS abbreviation, full name, or FIPS code."}
  ```

- **Strict mode refuses estimate row:**
  ```json
  {"data": null, "message": "Regional price parity for 'Texas' is currently an estimate (data_source=estimate) and strict mode is enabled. Disable verified_only to proceed with the estimate."}
  ```

- **Missing state_fips entirely (should never happen for the 51-state set, but guard anyway):**
  ```json
  {"data": null, "message": "No regional price parity data available for 'XX'"}
  ```

### Tool 2: `compare_purchasing_power`

Convenience tool for the "What if I move?" scenario — computes adjusted salary at a user-supplied national figure for two states and returns a side-by-side comparison.

**Input schema:**
```json
{
  "type": "object",
  "properties": {
    "salary": {
      "type": "number",
      "description": "National salary in US dollars (e.g., 65000). Must be positive and less than 10,000,000."
    },
    "state_a": {
      "type": "string",
      "description": "First state — same format as get_regional_price_parity.state"
    },
    "state_b": {
      "type": "string",
      "description": "Second state — same format as get_regional_price_parity.state"
    },
    "verified_only": {
      "type": "boolean",
      "description": "If true, both state_a and state_b must have data_source='bea_official'; otherwise returns null with a message.",
      "default": false
    }
  },
  "required": ["salary", "state_a", "state_b"]
}
```

**Success response:**
```json
{
  "data": {
    "salary": 65000.0,
    "state_a": {
      "state_name": "California",
      "state_abbr": "CA",
      "adjusted_salary": 58717.25,
      "cost_tier": "very_high",
      "purchasing_power_multiplier": 0.9033,
      "data_source": "bea_official"
    },
    "state_b": {
      "state_name": "Iowa",
      "state_abbr": "IA",
      "adjusted_salary": 74031.89,
      "cost_tier": "very_low",
      "purchasing_power_multiplier": 1.1390,
      "data_source": "bea_official"
    },
    "difference": 15314.64,
    "difference_pct": 26.08
  },
  "row_count": 2,
  "governance": {
    "table": "consumable.regional_price_parities",
    "quality_tier": "partial_verification",
    "owner": "@data-steward"
  }
}
```

**Null-case responses:** Same family as `get_regional_price_parity`, plus:

- **Invalid salary:** `{"data": null, "message": "salary must be a positive number less than 10,000,000; got -5"}`
- **Same state twice:** `{"data": null, "message": "state_a and state_b must be different states; got 'CA' and 'CA'"}`
- **Strict mode with mixed provenance:** `{"data": null, "message": "Strict mode requires both states to be BEA-official; 'Texas' is currently an estimate"}`

## Implementation Notes

- **State input normalization** — use the same allow-lists Silver uses (`src/silver/_us_state_reference.py`): `FIPS_TO_USPS`, `FIPS_TO_CENSUS_REGION`, and the canonical state-name list. Extend with a reverse lookup `USPS_TO_FIPS` and `STATE_NAME_TO_FIPS` (case-insensitive). Input normalization must be a pure function, unit-testable.

- **Response computation** — query `consumable.regional_price_parities` with filter `state_fips = normalized_fips`, return columns (`state_name`, `state_abbr`, `state_fips`, `census_region`, `rpp_all_items`, `purchasing_power_multiplier`, `cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`, `verification_status`, `data_year`). The `adjusted_examples` struct is built client-side in the MCP handler from the 4 columns. The `data_source` field in the response is renamed from `verification_status` for Gemma-facing clarity.

- **compare_purchasing_power arithmetic** — `adjusted_salary = round(salary × purchasing_power_multiplier, 2)`. Use Python's built-in `round()` (banker's rounding) to match Gold and DuckDB semantics. `difference = state_b.adjusted_salary - state_a.adjusted_salary`. `difference_pct = round(difference / state_a.adjusted_salary × 100, 2)`.

- **Server registration** — add both tools to `src/mcp_server/futureproof_server.py::FutureProofMCPServer.get_tools()`. Follow the existing `get_ai_exposure` pattern exactly.

- **Input validation** — reject empty strings, non-string state inputs, negative or non-numeric salary values. Return structured null responses, never raise.

## DQ Rules

N/A at MCP zone — DQ is covered by the 55 Gold rules on `consumable.regional_price_parities`. The MCP tool inherits those guarantees.

## Eval Set

Per Brightsmith MCP pipeline rules, eval sets are required for MCP specs. Target: ≥ 50 mechanically verifiable Q&A cases at `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`.

Eval set must cover:
1. **All 8 BEA-verified states** with full expected response payloads (cost_tier, adjusted_50k, verification_status='bea_official')
2. **Sample of estimated states** (at least 5) verifying data_source='estimate'
3. **All 3 input forms** for a representative state (e.g., 'CA', 'California', '06' all return California)
4. **Case-insensitive** input forms ('ca', 'CALIFORNIA')
5. **Strict mode positive cases** — verified_only=true returns data for bea_official states
6. **Strict mode refusal cases** — verified_only=true returns null for estimate states
7. **Unknown state** rejection: 'Xanadu', 'Puerto Rico' (not in the 51-set), empty string, null
8. **compare_purchasing_power** success cases at common salary levels ($30K, $50K, $75K, $100K, $65K)
9. **compare_purchasing_power** salary validation (negative, zero, > 10M, non-numeric)
10. **compare_purchasing_power** same-state rejection
11. **compare_purchasing_power** strict mode mixed-provenance refusal

Each eval case must include: `question` (natural language), `tool`, `input`, `expected_output`, `verification_key` (the minimal set of fields that must match for the case to pass).

## Agent Workflow (MCP Zone — minimal)

1. @governance-reviewer — pre-implementation review
2. @mcp-engineer — implement the two tools
3. @primary-agent — update `src/mcp_server/futureproof_server.py` and register tools
4. @doc-generator — update MCP documentation
5. @governance-reviewer — post-implementation review
6. @staff-engineer — final sign-off

## Governance Artifacts

- [ ] Approvals: `governance/approvals/mcp-bea-rpp-{pre,post,staff}-review.md`
- [ ] Eval set: `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` (≥ 50 cases)
- [ ] Tests: `tests/mcp/test_get_regional_price_parity.py` and `tests/mcp/test_compare_purchasing_power.py`
- [ ] Updated MCP server: `src/mcp_server/futureproof_server.py`

## Bronze Staff Review Conditions

- **Condition 7 (MCP half)** — **implemented here.**
  - `verification_status` from Gold is surfaced as `data_source` in every tool response
  - `verified_only: true` mode refuses to return `estimate` rows, returning a structured null response with a clear message
  - Eval set includes explicit strict-mode refusal cases

## Acceptance Criteria

- [ ] Both tools registered in `FutureProofMCPServer.get_tools()`
- [ ] Input normalization handles FIPS / USPS abbr / full name, case-insensitive
- [ ] All 8 BEA-verified states return correct cost_tier + adjusted_Nk matching the Gold spot-check table
- [ ] Strict mode refuses all 43 estimated states with a structured null response
- [ ] Strict mode returns all 8 verified states successfully
- [ ] `compare_purchasing_power` math matches `round(salary × ppm, 2)` exactly for CA vs IA at $65K → $58,717.25 vs $74,031.89 (pre-computed in the spec's success example)
- [ ] Unknown state returns null with a helpful error message, never raises
- [ ] Eval set has ≥ 50 cases, all passing against the live MCP server
- [ ] Test suite ≥ 20 tests (MCP zone minimum is 10)
- [ ] `governance.quality_tier` attached to every response is `partial_verification`

## Estimated Effort

~1-2 hours. Thin tool layer over a working Gold table. Most time is the eval set and input-normalization tests.

---

*— End of Spec —*
