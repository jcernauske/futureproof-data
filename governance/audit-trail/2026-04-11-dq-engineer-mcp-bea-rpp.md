# DQ Engineer — mcp-bea-rpp verification

**Date:** 2026-04-11
**Agent:** @dq-engineer
**Spec:** `mcp-bea-rpp`
**Rules file:** `governance/dq-rules/mcp-bea-rpp.json` (16 rules: 14 P0 + 2 P1)
**Results file:** `governance/dq-results/mcp-bea-rpp-20260411T042033Z.json`
**Scorecard:** `governance/dq-scorecards/mcp-bea-rpp-scorecard.md` (canonical) and `mcp-bea-rpp-20260411T042033Z.md` (timestamped)

## Task

Verify the 16 MCP interface contract rules for `mcp-bea-rpp`. These rules are structural invariants of tool responses, not SQL rules — the standard `dq_runner` SQL path does not apply. Verification is done via (a) re-running the pytest suite and (b) re-executing the 65-case eval set against the live `FutureProofMCPServer`, then mapping each rule's anchor cases onto the execution results.

## Actions

1. Loaded and inventoried the 16 rule definitions and 65 eval cases. Cross-referenced each rule's `eval_case_ids` against actual file contents — every anchor case exists.
2. Ran `uv run pytest tests/mcp/ -v`. Result: **106 passed in 15.11s** (51 `test_get_regional_price_parity`, 42 `test_compare_purchasing_power`, 13 `test_get_ai_exposure` out-of-scope).
3. Wrote `/tmp/verify_mcp_bea_rpp.py` (based on `scripts/dq_mcp_manual.py` server-bootstrap pattern) to:
   a. Instantiate `FutureProofMCPServer` against the real `data/catalog/catalog.db` warehouse.
   b. Execute all 65 eval cases end-to-end, asserting each case's `verification_key` (deep-get dotted-path equalities plus `message_contains` substring checks, mirroring the data-analyst's EDA protocol).
   c. For each of the 16 rules, apply both the anchor-case pass/fail filter AND a rule-specific structural check beyond verification_key (e.g., BEA-003 checks the exact FIPS set, BEA-005 reconstructs `round(salary*ppm, 2)` from the full-precision ppm, BEA-014 checks ratio invariance across 4 salary levels).
   d. Emit the per-rule result JSON to `governance/dq-results/mcp-bea-rpp-{timestamp}.json`.
4. Re-executed the eval set against the live server: **65/65 PASS**. Zero exceptions, zero verification_key mismatches.
5. Evaluated the 16 rule anchors. **15/16 PASS, 1 FAIL (MCP-BEA-002)**.
6. Wrote canonical and timestamped scorecards documenting each rule's verification method, anchor cases, and pass/fail detail.

## Results

### Eval set (65/65 PASS)

Every one of the 65 eval cases passed its `verification_key` assertions against the live `FutureProofMCPServer`. This is the same result the data-analyst reported in `governance/eda/mcp-bea-rpp-eda.md`; re-execution confirms no regression.

### Pytest suite (106/106 PASS)

```
tests/mcp/test_compare_purchasing_power.py 42 passed
tests/mcp/test_get_regional_price_parity.py 51 passed
tests/mcp/test_get_ai_exposure.py 13 passed (out-of-scope but in the same run)
======= 106 passed in 15.11s =======
```

### Rule results (15/16 PASS, 1 P0 FAIL)

| Rule ID | Priority | Result | Summary |
|---------|----------|--------|---------|
| MCP-BEA-001 | P0 | PASS | 16/16 anchors have `data_source` in enum |
| **MCP-BEA-002** | **P0** | **FAIL** | `governance.quality_tier` is `None` on every response |
| MCP-BEA-003 | P0 | PASS | `bea_official` fips set exactly equals `{'05','06','11','15','19','28','34','40'}` |
| MCP-BEA-004 | P0 | PASS | 14/14 `adjusted_examples` have exactly 4 keys |
| MCP-BEA-005 | P0 | PASS | 8/8 BEA rows: full-precision ppm reconstructs `adjusted_Nk` exactly |
| MCP-BEA-006 | P0 | PASS | 17/17 anchors have `cost_tier` in enum |
| MCP-BEA-007 | P0 | PASS | 8/8 strict-ok cases |
| MCP-BEA-008 | P0 | PASS | 5/5 strict-refuse cases |
| MCP-BEA-009 | P0 | PASS | 4/4 compare strict-refuse cases |
| MCP-BEA-010 | P0 | PASS | 7/7 unknown-state cases, zero exceptions |
| MCP-BEA-011 | P0 | PASS | 7/7 invalid-salary cases, zero exceptions |
| MCP-BEA-012 | P0 | PASS | 3/3 same-state cases |
| MCP-BEA-013 | P0 | PASS | 3/3 canonical CA-vs-IA @ $65K cases |
| MCP-BEA-014 | P0 | PASS | 8/8 BEA rows have ratio invariance within 1e-4 |
| MCP-BEA-015 | P1 | PASS | 65 cases (>= 50) |
| MCP-BEA-016 | P1 | PASS | 11/11 spec categories covered |

**P0 gate: FAIL** (1 P0 failure — MCP-BEA-002)

## Finding: MCP-BEA-002 is a legitimate P0 failure

**What the rule asserts:** every success response from either tool must include `governance.quality_tier == 'partial_verification'`.

**What actually happens:** the `governance` block on every response contains only `{'table': 'consumable.regional_price_parities'}`. `quality_tier` is never populated.

**Root cause:** framework gap. `brightsmith.mcp.base_mcp_server.BaseMCPServer.attach_governance` only emits `{'table', 'contract_version', 'contract_status'}`. There is no code path in the framework that reads `quality_tier` from the data-contract YAML and projects it onto the wire. `FutureProofMCPServer` does not override `attach_governance` or post-process `enrich_response` output to add it.

**Why this was not caught earlier:**
- The data-analyst's EDA explicitly noted at lines 319-326 that eval cases do NOT assert `governance.quality_tier` (and deferred verification to the pytest suite).
- The rule's own rationale claimed "this field is framework-controlled by `BaseMCPServer.attach_governance`" and "the pytest suite is the ground truth." BOTH claims are false: the framework does not populate it, and the pytest suite's `test_governance_metadata_attached` tests only assert `result["governance"]["table"] == RPP_TABLE_NAME` (test_get_regional_price_parity.py:374-379, test_compare_purchasing_power.py:170-176). `quality_tier` is not asserted anywhere in the test suite.
- Conclusion: MCP-BEA-002 was effectively unverified until this DQ-engineer run. The rule fires the first time it is actually executed.

**Spec authority:** `docs/specs/mcp-bea-rpp.md` line 238 is an explicit signed acceptance criterion: "`governance.quality_tier` attached to every response is `partial_verification`." Example response payloads at spec lines 76 and 157 show the field under `governance`. The wire contract is real.

**Impact assessment:**
- **Runtime / Gemma:** medium-to-low. Per-row `data_source` ('bea_official' | 'estimate') is still emitted correctly (MCP-BEA-001 PASS), so the LLM client CAN still hedge numeric precision on a per-row basis. `quality_tier` is a contract-level redundancy signal.
- **Governance / spec conformance:** HIGH. A signed P0 acceptance criterion is not being met. Letting the spec complete without fixing this would mean signing off on a wire contract that the server does not honor.

## Escalation to @governance-reviewer

**P0 gate: FAIL.** Spec `mcp-bea-rpp` MUST NOT be marked complete until MCP-BEA-002 is resolved. Options (in order of preference):

1. **Fix the server.** Override `FutureProofMCPServer.attach_governance` (or post-process `enrich_response` output) to inject `quality_tier` from the contract YAML. Update `test_governance_metadata_attached` in both test files to assert the new field. Re-run DQ; MCP-BEA-002 will PASS. Smallest change; honors the signed spec.
2. **Push the fix into the framework.** Add `quality_tier` surfacing to Brightsmith `BaseMCPServer.attach_governance` so every downstream spec benefits. Architecturally cleanest but touches the upstream framework.
3. **Downgrade MCP-BEA-002 from P0 to P1** (informational only) on the grounds that per-row `data_source` already carries the provenance signal. This downgrades a signed acceptance criterion without fixing it and should only happen with explicit staff-engineer sign-off.

The dq-engineer recommends option 1 or 2. Option 3 should require staff-engineer approval documented in `governance/approvals/`.

## Artifacts

- `governance/dq-results/mcp-bea-rpp-20260411T042033Z.json` — per-rule JSON results with full response payloads
- `governance/dq-scorecards/mcp-bea-rpp-scorecard.md` — canonical scorecard
- `governance/dq-scorecards/mcp-bea-rpp-20260411T042033Z.md` — timestamped snapshot
- `/tmp/verify_mcp_bea_rpp.py` — ephemeral verification script (not committed; DQ-engineer scripts for structural-invariant rules are one-shot — the pytest suite is the durable guarantee)
