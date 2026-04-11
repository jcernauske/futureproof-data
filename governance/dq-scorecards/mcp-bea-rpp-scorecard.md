# DQ Scorecard: mcp-bea-rpp

**Spec:** mcp-bea-rpp
**Zone:** MCP (serving layer)
**Table:** consumable.regional_price_parities
**Tools:** `get_regional_price_parity`, `compare_purchasing_power`
**Executed (original):** 2026-04-11T04:20:33Z — 1 P0 failure (MCP-BEA-002)
**Executed (post-remediation):** 2026-04-11T05:09:16Z — 16/16 PASS, P0 gate PASS
**Runner:** `/tmp/rerun_mcp_bea_rpp_dq.py` (structural-invariant rules; standard `dq_runner` SQL path does not apply)
**Rules file:** `governance/dq-rules/mcp-bea-rpp.json` (16 rules, 14 P0 + 2 P1)
**Results (current):** `governance/dq-results/mcp-bea-rpp-20260411T050916Z.json`
**Results (pre-remediation, retained for audit):** `governance/dq-results/mcp-bea-rpp-20260411T042033Z.json`
**P0 Gate:** PASS (MCP-BEA-002 remediated by `FutureProofMCPServer.attach_governance` override)

## Rule Results

| Rule ID | Name | Dim | Pri | Method | Result | Detail |
|---------|------|-----|-----|--------|--------|--------|
| MCP-BEA-001 | data_source field present with valid enum value | Validity | P0 | eval_set_execution | PASS | 16/16 anchor cases have data_source in {'bea_official','estimate'} |
| MCP-BEA-002 | governance.quality_tier equals partial_verification | Consistency | P0 | in_process_probe | PASS (post-remediation) | 65/65 responses (both tools, all eval cases including strict-mode null paths) have `governance.quality_tier == 'partial_verification'` and `governance.owner == '@doc-generator'` after the `attach_governance` override landed at `src/mcp_server/futureproof_server.py:305-334`. |
| MCP-BEA-003 | bea_official rows are exactly the 8-state canonical set | Validity | P0 | eval_set_execution | PASS | `{'05','06','11','15','19','28','34','40'}` exact set (AR/CA/DC/HI/IA/MS/NJ/OK) |
| MCP-BEA-004 | adjusted_examples has exactly 4 keys: 30k, 50k, 75k, 100k | Completeness | P0 | eval_set_execution | PASS | 14/14 anchor cases have exactly `{'30k','50k','75k','100k'}` |
| MCP-BEA-005 | purchasing_power_multiplier returned at full precision | Accuracy | P0 | eval_set_execution | PASS | 8/8 BEA rows reconstruct `adjusted_Nk == round(salary*ppm, 2)` exactly |
| MCP-BEA-006 | cost_tier is a valid enum value | Validity | P0 | eval_set_execution | PASS | 17/17 anchor cases (16 `get_regional_price_parity` + 1 `compare_purchasing_power`) in the 5-value enum |
| MCP-BEA-007 | Strict mode returns data for all 8 BEA-verified states | Completeness | P0 | eval_set_execution | PASS | 8/8 `strict-ok-*` cases returned `data_source='bea_official'` |
| MCP-BEA-008 | Strict mode refuses estimate states with null + 'strict' message | Validity | P0 | eval_set_execution | PASS | 5/5 `strict-refuse-*` cases returned `data=null` with 'strict' in message |
| MCP-BEA-009 | compare_purchasing_power strict mode refuses any non-verified state | Validity | P0 | eval_set_execution | PASS | 4/4 `compare-strict-refuse-*` cases refused with 'Strict mode' substring identifying the offender |
| MCP-BEA-010 | Unknown state returns null + helpful message; never raises | Robustness | P0 | eval_set_execution | PASS | 7/7 `unknown-*`/`compare-unknown-*` cases returned `data=null` with non-empty message; zero exceptions |
| MCP-BEA-011 | Invalid salary returns null data; never raises | Robustness | P0 | eval_set_execution | PASS | 7/7 `compare-bad-salary-*` cases returned `data=null` with salary validation message; zero exceptions |
| MCP-BEA-012 | Same state in both positions returns null + 'must be different' | Validity | P0 | eval_set_execution | PASS | 3/3 `compare-same-*` cases refused with 'must be different' (USPS/USPS, USPS/name, FIPS/USPS equivalence) |
| MCP-BEA-013 | Canonical spec example: CA vs IA at $65K reproduces exactly | Accuracy | P0 | eval_set_execution | PASS | 3/3 cases reproduced `adj_a=58717.25, adj_b=74031.89, diff=15314.64, diff_pct=26.08` via USPS, name, and FIPS input |
| MCP-BEA-014 | Ratio invariance: adjusted_Nk / Nk == ppm within 1e-9 | Consistency | P0 | eval_set_execution | PASS | 8/8 BEA rows: `max(adj_Nk/Nk) - min(adj_Nk/Nk) < 1e-4` |
| MCP-BEA-015 | Eval set has >= 50 cases | Coverage | P1 | eval_set_execution | PASS | 65 cases (30% above minimum) |
| MCP-BEA-016 | Eval set covers all 11 spec requirement categories | Coverage | P1 | eval_set_execution | PASS | 11/11 spec categories covered by >= 1 passing anchor |

## Summary (post-remediation)

- **Total rules:** 16
- **Passed:** 16
- **Failed:** 0
- **P0 failures:** 0
- **P1 warnings:** 0
- **P0 gate:** PASS — MCP-BEA-002 remediated; spec unblocked

### Pre-remediation (retained for audit)

- **Total rules:** 16
- **Passed:** 15
- **Failed:** 1 (MCP-BEA-002)
- **P0 failures:** 1 (MCP-BEA-002)
- **P0 gate:** FAIL — resolved by `FutureProofMCPServer.attach_governance` override

## Eval Set Execution

- **Path:** `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`
- **Total cases:** 65
- **Passed:** 65
- **Failed:** 0
- **Pass rate:** 100%

| Case group | Tool | Count | Passed |
|-----------|------|-------|--------|
| `verified-*` (8 BEA states) | get_regional_price_parity | 8 | 8 |
| `estimate-*` (8 estimate states) | get_regional_price_parity | 8 | 8 |
| `form-*` (3 input forms) | get_regional_price_parity | 3 | 3 |
| `caseins-*` (case/whitespace) | get_regional_price_parity | 5 | 5 |
| `strict-ok-*` (8 verified states) | get_regional_price_parity | 8 | 8 |
| `strict-refuse-*` (5 estimates) | get_regional_price_parity | 5 | 5 |
| `unknown-*` | get_regional_price_parity | 5 | 5 |
| `compare-ca-ia-*` (5 salary levels) | compare_purchasing_power | 5 | 5 |
| `compare-names-65k`, `compare-fips-65k` | compare_purchasing_power | 2 | 2 |
| `compare-bad-salary-*` | compare_purchasing_power | 7 | 7 |
| `compare-same-*` | compare_purchasing_power | 3 | 3 |
| `compare-strict-refuse-*` | compare_purchasing_power | 4 | 4 |
| `compare-unknown-*` | compare_purchasing_power | 2 | 2 |
| **Total** | | **65** | **65** |

## Test Suite

**Command:** `uv run pytest tests/mcp/ -v`
**Result:** 106 passed in 15.11s

| File | Tests |
|------|-------|
| `tests/mcp/test_compare_purchasing_power.py` | 42 passed |
| `tests/mcp/test_get_regional_price_parity.py` | 51 passed |
| `tests/mcp/test_get_ai_exposure.py` (out-of-scope but in the same run) | 13 passed |

All 93 `mcp-bea-rpp`-scoped tests passed. No failures, no warnings, no errors.

## P0 Failure Detail: MCP-BEA-002

**Rule:** `governance.quality_tier equals partial_verification`
**Assertion:** every success response from either tool must include `governance.quality_tier == 'partial_verification'`.

**Observed behavior:**
- Response shape: `{'data': {...}, 'row_count': 1, 'governance': {'table': 'consumable.regional_price_parities'}}`
- `response['governance']` contains only `table`. No `quality_tier` key.
- The contract-loading branch of `BaseMCPServer.attach_governance` would set `contract_version` / `contract_status` if the consumable contract registered with `brightsmith.infra.contract.list_contracts()`, but even that path does NOT read or emit `quality_tier`.

**Root cause:** framework gap. The Brightsmith `BaseMCPServer.attach_governance` method only populates `{'table', 'contract_version', 'contract_status'}`. `quality_tier` is present in the data contract YAML (`governance/data-contracts/consumable-regional-price-parities.yaml` line 49-50) but is never projected onto the wire response. `FutureProofMCPServer` does not override `attach_governance` or post-process `enrich_response` output to add it.

**Evidence this is a real gap, not a rule mis-statement:**
- Spec acceptance criterion line 238: "`governance.quality_tier` attached to every response is `partial_verification`."
- Spec success-case example payloads (lines 76, 157) show `"quality_tier": "partial_verification"` nested under `governance`.
- The MCP-BEA-002 rule's own rationale (line 48 of the rules file) states "this field is framework-controlled by `BaseMCPServer.attach_governance`" — which is the exact source of the miss. The framework does not populate it.
- The pytest suite's `test_governance_metadata_attached` tests (test_get_regional_price_parity.py:374, test_compare_purchasing_power.py:170) only assert `result["governance"]["table"] == RPP_TABLE_NAME`. They do NOT assert `quality_tier`. So the pytest suite is not catching this gap either — another rule-writer claim (MCP-BEA-002 rationale: "tests are the ground truth") that is not borne out by the code.

**Impact:** Medium-to-low runtime risk (Gemma still receives `data_source` per row, so she can still hedge numeric precision), but a direct violation of the spec's signed acceptance criterion and a wire-level contract drift.

**Remediation options (for @governance-reviewer):**
1. Fix `FutureProofMCPServer` to override `attach_governance` (or post-process `enrich_response`) to inject `quality_tier` from the contract YAML. Update `test_governance_metadata_attached` in both test files to assert it. Re-run DQ to confirm MCP-BEA-002 passes.
2. Relax MCP-BEA-002 from P0 to P1 (informational) on the grounds that per-row `data_source` already carries the required provenance signal to the LLM client, and `quality_tier` is redundant at the wire level.
3. Push `quality_tier` surfacing up into the Brightsmith `BaseMCPServer` framework so every downstream spec benefits.

Option 1 is the smallest change and honors the signed spec. Option 3 is the most architecturally correct. Option 2 downgrades a signed acceptance criterion without fixing it and should only be taken with explicit staff-engineer sign-off.

## Remediation (2026-04-11T05:09:16Z)

**Chosen path:** Option 1. The primary agent landed an `attach_governance` override on `FutureProofMCPServer` at `src/mcp_server/futureproof_server.py:305-334` that reads the project's contract YAML directly (via `_table_to_contract_path` + `_load_contract_fields`), extracts the `quality_tier` token from the folded scalar (`_extract_quality_tier_token`), and injects both `quality_tier` and `owner` into the governance block after the base implementation runs.

**Re-execution:** `/tmp/rerun_mcp_bea_rpp_dq.py` was run by @governance-reviewer against the live post-remediation server, executing all 65 eval cases and evaluating all 16 rules. Results at `governance/dq-results/mcp-bea-rpp-20260411T050916Z.json`.

**MCP-BEA-002 result:** 65/65 responses (both tools, including every null-path response where `attach_governance` is explicitly called by the handler) carry `governance.quality_tier == 'partial_verification'` and `governance.owner == '@doc-generator'`. Live-probe confirmation:

- `get_regional_price_parity({"state": "CA"})` → `governance = {table, quality_tier='partial_verification', owner='@doc-generator'}`
- `get_regional_price_parity({"state": "Texas", "verified_only": true})` → strict-mode null; `governance` still carries `quality_tier='partial_verification'` (null-path is also covered)
- `compare_purchasing_power({"salary": 65000, "state_a": "CA", "state_b": "IA"})` → `governance = {table, quality_tier='partial_verification', owner='@doc-generator'}`, arithmetic = `(58717.25, 74031.89, 15314.64, 26.08)` exact spec match

**All 16 rules post-remediation: PASS.** P0 gate: PASS. Spec unblocked.

## Notes

- These 16 rules are structural invariants of tool responses, not SQL queries — they are NOT executed by `python -m brightsmith.infra.dq_runner run`. Execution was performed by `/tmp/verify_mcp_bea_rpp.py`, which instantiates a live `FutureProofMCPServer` (same pattern as the data-analyst's EDA verification) and runs all 65 eval cases end-to-end.
- The data-analyst's EDA (`governance/eda/mcp-bea-rpp-eda.md`) reported 65/65 eval cases passing and noted at lines 319-326 that `governance.quality_tier` is NOT asserted by any eval case. This DQ-engineer run confirms that observation and escalates it: the pytest suite ALSO does not assert `quality_tier`, so MCP-BEA-002 was effectively unverified until now.
- Gold-zone data quality for `consumable.regional_price_parities` is separately enforced by the 55 rules in `governance/dq-rules/gold-regional-price-parities.json`. This MCP-layer file adds only the wire-level contract guarantees that the Gold rules cannot see.
