# MCP Engineer Audit — mcp-bea-rpp

- **Date:** 2026-04-10
- **Agent:** @mcp-engineer
- **Spec:** `docs/specs/mcp-bea-rpp.md`
- **Zone:** MCP (AI-Ready)
- **Parent specs:** raw-ingest-bea-rpp, silver-base-bea-rpp, gold-regional-price-parities

## Summary

Implemented the two MCP tools required by spec `mcp-bea-rpp` —
`get_regional_price_parity` and `compare_purchasing_power` — as a thin
read-only layer over the governed Gold table
`consumable.regional_price_parities` (51 rows, ACTIVE contract as of
2026-04-11). No new data, no transformations; every tool response
carries full-precision values and governance metadata so the Gemma
agent can both reconstruct arithmetic and hedge numeric precision.

## Files Modified / Created

### Created

- `src/mcp_server/_state_input.py` — pure state input normalizer
  (`normalize_state_input`) accepting FIPS / USPS / full name, case
  insensitive, whitespace tolerant. Derives `USPS_TO_FIPS` (51 entries)
  and `STATE_NAME_TO_FIPS` (51 lowercase entries) from the canonical
  `silver._us_state_reference.FIPS_TO_USPS`. Also declares
  `FIPS_TO_STATE_NAME` (51 entries, matches the Gold `state_name`
  column exactly). A `_self_check()` runs at import time and verifies:
  (1) 51-entry counts, (2) bidirectional consistency between
  `FIPS_TO_USPS` and `USPS_TO_FIPS`, (3) all `STATE_NAME_TO_FIPS` values
  are valid FIPS codes, (4) all name keys are lowercase.
- `tests/mcp/test_get_regional_price_parity.py` — 49 tests covering
  input normalization, all 8 BEA-verified states (exact cost_tier +
  adjusted_50k), response shape, full-precision `purchasing_power_multiplier`,
  strict-mode pass and refusal, null cases, and query delegation.
- `tests/mcp/test_compare_purchasing_power.py` — 44 tests covering
  canonical CA vs IA at $65K spec arithmetic, common salary levels,
  salary validation (negative / zero / >10M / string / None / bool /
  NaN / inf), same-state rejection (across input forms), unknown
  state rejection, strict-mode pass + mixed-provenance refusal, and
  no-data guards.
- `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` — 65 mechanically
  verifiable cases. Each case has `question`, `tool`, `input`,
  `expected_output`, and a `verification_key` of dotted-path assertions
  that an evaluator can check deterministically. All 65 cases pass
  when executed against the live `FutureProofMCPServer` bound to the
  real Iceberg Gold table.

### Modified

- `src/mcp_server/futureproof_server.py` — registered two new tools in
  `get_tools()` alongside the existing `get_ai_exposure`, added
  handlers `_handle_get_regional_price_parity` and
  `_handle_compare_purchasing_power`, and added helpers
  `_fetch_rpp_row`, `_rpp_row_to_payload`, `_validate_salary`,
  `_compact_side`.

## Design Decisions

1. **Keep MCP concerns out of `src/silver/`.** The spec's
   implementation note suggests extending `_us_state_reference.py` with
   the reverse lookups, but putting MCP-facing normalizer logic in a
   Silver module would couple layers. The Silver module remains the
   canonical source of truth for the 51-entry closed set; the new
   `src/mcp_server/_state_input.py` imports `FIPS_TO_USPS` from it and
   derives the reverse lookups there. The `_self_check()` cross-validates
   against the Silver constant at import time, so drift fails loudly.

2. **Full-precision `purchasing_power_multiplier` in the response.**
   Per pre-review Advisory #1, the spec's 4-decimal display value
   (`0.9033`) would strand the caller from reconstructing the adjusted
   salary — any rounded multiplier × salary would drift from the
   Gold-precomputed `adjusted_Nk` columns. The handlers return the raw
   double (`0.9033423667570009` for CA, `1.1389521640091116` for IA),
   and the eval set's `verification_key` entries also assert full
   precision (Advisory #2). The 4-decimal value in the spec's success
   example is treated as a display concern for any downstream UI, not
   as the wire format.

3. **`adjusted_examples` struct built client-side in the handler.** The
   four Gold columns (`adjusted_30k/50k/75k/100k`) are collapsed into a
   single struct keyed by `"30k" / "50k" / "75k" / "100k"` for a more
   LLM-legible payload. The original four column names do not appear
   on the wire.

4. **`verification_status` -> `data_source` rename.** Done in
   `_rpp_row_to_payload`. The Gold column keeps its semantic name;
   the Gemma-facing payload uses `data_source` to cue the LLM that the
   field is about provenance, not DQ rule status.

5. **Salary validation rejects `bool` explicitly.** Python's `bool` is a
   subclass of `int`, so `True` would otherwise silently coerce to
   `$1` through `isinstance(raw, (int, float))`. `_validate_salary`
   checks `isinstance(raw, bool)` before the numeric branch and
   returns the structured null.

6. **NaN and inf rejected.** `_validate_salary` filters `value != value`
   and `± inf` so pathological float inputs never reach the arithmetic.

7. **Same-state rejection happens after normalization.** `CA` vs
   `California` vs `06` all normalize to FIPS `06`, and the handler
   rejects after comparing normalized FIPS codes, so every equivalent
   pair is caught regardless of input form. The error message echoes
   the original raw inputs for caller debugging.

8. **Strict mode refusal identifies the offending state.** In
   `compare_purchasing_power` with `verified_only=true`, the first
   state in `(state_a, state_b)` whose `verification_status ==
   'estimate'` is named in the refusal message. This matches the
   spec's success example and avoids ambiguous "one of these two
   states" language.

9. **No `_fetch_rpp_row` error re-raising.** Iceberg query errors are
   swallowed into `None` and surfaced as the standard "No regional
   price parity data available" message. The tool never raises —
   every failure mode returns a structured null.

## Verification Evidence

### Full test suite

```
uv run pytest
... 1089 passed, 1 deselected in 19.13s
```

### MCP-only test suite

```
uv run pytest tests/mcp/ -q
... 106 passed in 15.36s
```

Test count breakdown:

- `tests/mcp/test_get_regional_price_parity.py` — 49 tests
- `tests/mcp/test_compare_purchasing_power.py` — 44 tests
- `tests/mcp/test_get_ai_exposure.py` — 13 tests (pre-existing)

MCP-zone minimum is 10 tests. Delivered: 93 new MCP tests.

### Live spot-check against the real Gold table

Executed the handlers with a live catalog bound to
`data/gold/iceberg_warehouse`. Results:

- All 8 BEA-verified states return the exact `cost_tier` +
  `adjusted_50k` values from the Gold spot-check table:

  | USPS | cost_tier   | adjusted_50k | data_source   |
  |------|-------------|--------------|---------------|
  | AR   | very_low    | 57537.4      | bea_official  |
  | CA   | very_high   | 45167.12     | bea_official  |
  | DC   | very_high   | 45495.91     | bea_official  |
  | HI   | very_high   | 45454.55     | bea_official  |
  | IA   | very_low    | 56947.61     | bea_official  |
  | MS   | very_low    | 57471.26     | bea_official  |
  | NJ   | very_high   | 45955.88     | bea_official  |
  | OK   | very_low    | 56947.61     | bea_official  |

- Strict mode across all 51 states in the Gold table:
  - 8 verified rows returned (matches `BEA_VERIFIED_FIPS`)
  - 43 estimated rows refused with structured null + strict-mode message
- `compare_purchasing_power(salary=65000, state_a='CA', state_b='IA')`:
  - `state_a.adjusted_salary = 58717.25`
  - `state_b.adjusted_salary = 74031.89`
  - `difference = 15314.64`
  - `difference_pct = 26.08`
  - `state_a.purchasing_power_multiplier = 0.9033423667570009` (full precision)
  - `state_b.purchasing_power_multiplier = 1.1389521640091116` (full precision)
- Unknown state `'Xanadu'` returns structured null with
  `"Unknown state: 'Xanadu'. Expected a US state..."`.

### Eval set

- Path: `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`
- Count: 65 cases (spec minimum: 50)
- By tool: `get_regional_price_parity` — 42,
  `compare_purchasing_power` — 23
- Live execution: **65 / 65 passed** against the real Gold table

Coverage matrix (all spec-required categories present):

| # | Category                                               | Cases |
|---|--------------------------------------------------------|-------|
| 1 | All 8 BEA-verified states, full payload                | 8     |
| 2 | Sample of 8 estimated states                           | 8     |
| 3 | All 3 input forms for California (FIPS / USPS / name)  | 3     |
| 4 | Case-insensitive input forms                           | 5     |
| 5 | Strict mode positive (8 verified states)               | 8     |
| 6 | Strict mode refusal (5 estimated states)               | 5     |
| 7 | Unknown / rejected state input                         | 5     |
| 8 | compare success at $30K, $50K, $65K, $75K, $100K       | 5     |
| 8a| compare success via state names and FIPS              | 2     |
| 9 | compare salary validation                              | 7     |
|10 | compare same-state rejection                          | 3     |
|11 | compare strict mixed-provenance refusal               | 4     |
|12 | compare unknown state rejection                        | 2     |
| — | **Total**                                              | 65    |

### Lint

```
uv run ruff check src/mcp_server/ tests/mcp/test_compare_purchasing_power.py tests/mcp/test_get_regional_price_parity.py
All checks passed!
```

## Acceptance Criteria — Status

- [x] Both tools registered in `FutureProofMCPServer.get_tools()`
- [x] Input normalization handles FIPS / USPS abbr / full name,
      case-insensitive
- [x] All 8 BEA-verified states return correct cost_tier + adjusted_Nk
      matching the Gold spot-check table
- [x] Strict mode refuses all 43 estimated states with a structured null
- [x] Strict mode returns all 8 verified states successfully
- [x] `compare_purchasing_power` math matches `round(salary * ppm, 2)`
      exactly for CA vs IA at $65K → $58,717.25 vs $74,031.89
- [x] Unknown state returns null with a helpful message, never raises
- [x] Eval set has ≥ 50 cases, all passing against the live MCP server
- [x] Test suite ≥ 20 tests (delivered 93 new MCP tests)
- [x] `governance` metadata attached to every response (via
      `attach_governance` / `enrich_response`)

## Assumptions / Notes

- `governance.quality_tier = 'partial_verification'` is set by the Gold
  contract layer via `attach_governance` — this MCP code does not hard-
  code the tier and instead trusts the contract metadata, so any future
  promotion of the RPP contract to `verified` will propagate to MCP
  responses automatically without code changes.
- The spec's Texas estimate example uses `purchasing_power_multiplier:
  1.0266940451745379`. The corresponding ESTIMATE_TX_ROW fixture in
  tests uses that value; the live-server eval cases read live Gold data
  and so are immune to any fixture drift.
- One pre-existing ruff warning (`pytest` unused in the older
  `tests/mcp/test_get_ai_exposure.py`) was left alone — outside this
  spec's scope.
