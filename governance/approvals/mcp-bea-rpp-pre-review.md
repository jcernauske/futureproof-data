## Governance Review: mcp-bea-rpp
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-10
**Verdict:** APPROVED (with 2 advisories to resolve during implementation)

---

### Scope Recap

`mcp-bea-rpp` is a thin read-only MCP tool layer over the Gold table
`consumable.regional_price_parities` (51 rows, contract ACTIVE, 55 DQ rules,
partial_verification tier). Two tools are defined:

1. `get_regional_price_parity(state, verified_only=false)` — single-state lookup,
   accepts USPS abbreviation, full name, or FIPS code.
2. `compare_purchasing_power(salary, state_a, state_b, verified_only=false)` —
   side-by-side adjusted-salary comparison.

This spec closes **Bronze staff-review Condition 7 (MCP half)** per
`governance/approvals/raw-ingest-bea-rpp-staff-review.md` lines 153, 185:
every response surfaces per-row `verification_status` as `data_source`, and
`verified_only=true` refuses to return `estimate` rows with a structured null.

This also closes the final link in the BEA RPP Bronze → Silver → Gold → MCP
chain.

---

### Pre-Implementation Checklist

| # | Item | Status |
|---|------|--------|
| 1 | Clear problem statement and success criteria | PASS — spec § "Problem Statement" ties both tools to product need and names Condition 7 closure |
| 2 | Input data sources identified with paths | PASS — `consumable.regional_price_parities` (51 rows, Gold contract ACTIVE) |
| 3 | Output artifacts defined with paths and formats | PASS — two JSON response schemas, three null-case variants, `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` target, `src/mcp_server/futureproof_server.py` touchpoint |
| 4 | Transformations described (what/why) | PASS — direct query passthrough plus client-side `adjusted_examples` struct and `compare_purchasing_power` arithmetic; no table transforms |
| 5 | Zone assignment correct (MCP / AI-Ready) | PASS |
| 6 | Primary implementation agent identified | PASS — @mcp-engineer + @primary-agent for server registration |
| 7 | DQ rule categories specified | N/A at MCP zone — spec correctly declares inheritance from Gold's 55 rules |
| 8 | CDE mapping impact assessed | PASS — no new fields; tool response fields (`data_source`, `purchasing_power_multiplier`, `adjusted_*`, `cost_tier`, `state_*`) are all already CDE-flagged in `consumable-regional-price-parities.yaml` |
| 9 | Lineage scope defined | PASS — MCP-zone lineage is tool-registration level; spec names only the Gold table as input |
| 10 | Breaking changes flagged | PASS — additive only; no existing MCP surface is being modified (the `get_ai_exposure` tool on `FutureProofMCPServer` is untouched) |
| 11 | Testing approach defined | PASS — test files named at `tests/mcp/test_get_regional_price_parity.py` and `tests/mcp/test_compare_purchasing_power.py`, minimum 20 tests, eval set ≥ 50 cases |
| 12 | Data Model Gate | N/A — MCP zone skips the 3-stage data modeling progression; Gold zone already has approved conceptual/logical/physical models |
| 13 | Condition 7 (MCP half) implementation plan explicit | PASS — spec § "Bronze Staff Review Conditions" names both requirements and § "Eval Set" requires refusal coverage |
| 14 | Pure-function state normalization (FIPS/USPS/full-name) unit-testable | PASS — spec calls out `src/silver/_us_state_reference.py` reuse and names new reverse lookups (`USPS_TO_FIPS`, `STATE_NAME_TO_FIPS`) |
| 15 | Input validation for salary (negative, zero, >10M, non-numeric) defined | PASS |
| 16 | Same-state rejection for `compare_purchasing_power` defined | PASS |
| 17 | Response `governance.quality_tier` matches Gold contract | PASS — spec pins `partial_verification`, matching `consumable-regional-price-parities.yaml` line 49 |

---

### Sanity-Check Results

#### 1. Arithmetic reproducibility — PASS (with Advisory #1)

Silver stores `purchasing_power_multiplier` as a full-precision double computed
as `100.0 / rpp_all_items` (confirmed at
`src/silver/bea_rpp_transformer.py:133`). The Gold contract carries the column
forward unchanged. Recomputed using the actual Silver formula:

| State | rpp_all_items | Exact ppm | 65K × ppm | round(,2) |
|---|---|---|---|---|
| CA | 110.7 | 0.9033423667570009 | 58717.2538... | **58717.25** |
| IA | ~87.80 | 1.1389521640091116 | 74031.8906... | **74031.89** |

These match the spec's `compare_purchasing_power` success example exactly
($58,717.25 for CA, $74,031.89 for IA, difference $15,314.64, difference_pct
26.08%).

The spec's `adjusted_examples` block for CA at $30K/$50K/$75K/$100K
(27100.27 / 45167.12 / 67750.68 / 90334.24) also reproduces exactly from
`round(N × 0.9033423667570009, 2)`. The value 0.9033423667570009 is the exact
IEEE-754 double result of `100.0 / 110.7`, identical to what Silver stores.

**However**, the response payload displays `"purchasing_power_multiplier":
0.9033` — a 4-decimal truncation. A naive consumer (including an over-literal
eval verifier) that multiplies `65000 × 0.9033` gets **58,714.50**, which does
not match the `adjusted_salary` of 58,717.25. See Advisory #1.

The user's sanity-check observation is correct: `65000 × 0.9033 = 58,714.50`
(displayed ppm) vs `65000 × 0.9033423667570009 = 58,717.25` (full-precision
ppm). The spec's arithmetic is internally consistent **only if** the response
returns full precision in `purchasing_power_multiplier`. The spec must be
explicit about this.

#### 2. Reuse of state-reference lookups — PASS

Spec § "Implementation Notes" correctly points at
`src/silver/_us_state_reference.py` (`FIPS_TO_USPS`, `FIPS_TO_CENSUS_REGION`).
The spec adds two new reverse lookups (`USPS_TO_FIPS`, `STATE_NAME_TO_FIPS`)
but does not duplicate the 51-entry canonical tables. The import-time
`_self_check()` already cross-validates against the Bronze ingestor's
`VALID_STATE_FIPS`, so extending with reverse lookups is structurally safe
provided they are derived from the existing forward dicts (not hand-rolled).
The post-review must verify the reverse lookups are derived, not duplicated.

#### 3. Eval set covers strict-mode refusal explicitly — PASS

Spec § "Eval Set" item 6 names "Strict mode refusal cases — verified_only=true
returns null for estimate states" and item 11 names "strict mode mixed-
provenance refusal" for `compare_purchasing_power`. This satisfies Condition
7's eval-traceability requirement.

#### 4. No new PII or quality guarantees beyond Gold — PASS

Spec introduces no new columns, no new derivations, no new persisted data, and
no quality claims beyond the Gold contract's `partial_verification` tier. No
PII is added — the Gold contract lists zero PII columns. No CDE flags are
added — all response fields are already CDE-flagged at Gold.

#### 5. DQ N/A at MCP zone — PASS

Spec correctly declares DQ inheritance from Gold's 55 rules. No MCP-zone DQ
rules are needed; the MCP tool is a read-only passthrough over the Gold table
whose data quality is already guarded by GLD-RPP-001 through GLD-RPP-055
(including GLD-RPP-036 and GLD-RPP-037, which pin the 8-state BEA-verified
set that strict mode refuses to escape).

---

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | **Display precision of `purchasing_power_multiplier` in the response is ambiguous.** Spec shows `0.9033` in the success-response example, but the `adjusted_salary` value (`58717.25`) only reproduces from the full-precision column value (`0.9033423667570009`). A Gemma consumer or eval verifier that naively recomputes `salary × displayed_ppm` will get `58,714.50`, a $2.75 mismatch. The spec must pick one: (a) return `purchasing_power_multiplier` at full precision so the arithmetic is reconstructable, or (b) keep 4-decimal display and explicitly document that `adjusted_salary` is authoritative and `purchasing_power_multiplier` is display-only (not to be used for client-side math). The `mcp-ai-exposure` precedent returns raw Gold values without rounding, which favors option (a). **Recommended: option (a) — return full-precision `purchasing_power_multiplier` in the response. The eval set `verification_key` entries for `purchasing_power_multiplier` must use the full-precision value, not `0.9033`.** Not spec-blocking; @mcp-engineer must resolve before writing eval cases. | Resolve during implementation. Post-review will verify the chosen option and that eval cases use the corresponding precision. |
| 2 | ADVISORY | **Eval file extension mismatch with prior precedent.** The prior MCP eval file is `data/ai_ready/eval/mcp-ai-exposure-eval.json` (a single JSON array). This spec targets `mcp-bea-rpp-eval.jsonl` (JSON-Lines, one case per line). JSONL is the more standard eval format and is strictly better for streaming/incremental verification, so this is an improvement — but the project now has two different eval formats. No action required for this spec, but a future cleanup could migrate the AI exposure eval to `.jsonl` for uniformity. | None. Informational. |

No CHANGES REQUESTED. No REJECTED items.

---

### Decision Rationale

This is a textbook thin MCP layer over a well-governed Gold table:

- **Gold dependency is rock-solid.** The Gold contract is ACTIVE with 55 DQ
  rules, signed off 2026-04-11, all 51 rows structurally valid, 8 rows
  BEA-verified and pinned by P0 rules (GLD-RPP-036, GLD-RPP-037).
  `consumable-regional-price-parities.yaml` lines 546–577 explicitly document
  the forward-only Condition 7 obligation that this spec implements.

- **Condition 7 (MCP half) is implemented cleanly.** Both requirements
  — `data_source` in every response row, `verified_only` strict mode refusing
  estimates — are explicit in the spec's tool signatures, response schemas,
  null-case examples, acceptance criteria, and eval-set coverage list. The
  allow-list enforcement is structurally inherited from Gold's GLD-RPP-037,
  so strict mode cannot drift from the canonical 8-state set without also
  failing Gold DQ.

- **No new governance surface.** No new fields, no new PII, no new CDE flags,
  no new DQ rules, no new data contracts, no schema changes, no lineage
  transformations beyond tool registration. The MCP tool response fields are
  all already CDE-flagged in the Gold contract. DQ is correctly declared N/A.

- **Arithmetic is correct.** The spec's success-example figures
  ($58,717.25 for CA at $65K, $74,031.89 for IA at $65K, $15,314.64 difference,
  26.08% difference_pct) reproduce exactly from the full-precision
  `purchasing_power_multiplier` values stored at Silver. The CA
  `adjusted_examples` block at $30K/$50K/$75K/$100K also reproduces exactly.
  The only wrinkle is Advisory #1 — display-precision ambiguity for the
  response's `purchasing_power_multiplier` field — which is an implementation
  clarification, not a math error.

- **State-reference lookups are reused correctly.** Spec points at
  `src/silver/_us_state_reference.py` and adds reverse lookups as extensions,
  not duplications. The existing import-time structural self-check against the
  Bronze ingestor's `VALID_STATE_FIPS` remains intact and will catch drift.

- **Eval set requirements are complete.** The 11 coverage categories in
  § "Eval Set" include all 3 input forms, case-insensitive variants, both
  strict-mode positive and refusal paths, salary validation, same-state
  rejection, and mixed-provenance refusal — the spec cannot be implemented
  without producing the Condition 7 evidence.

- **Pipeline chain closure.** Bronze (COMPLETE), Silver (COMPLETE), Gold
  (COMPLETE + contract ACTIVE) lead naturally to this thin MCP layer. Once
  this spec lands, the full BEA RPP chain Bronze → Silver → Gold → MCP is
  closed, and Bronze staff-review Condition 7 is fully discharged across all
  four zones.

**Verdict: APPROVED for implementation.** Advisory #1 must be resolved by
@mcp-engineer before writing the eval set — the post-review will verify the
chosen precision is consistent across the tool response, the test suite, and
the eval verification keys.

---

### Post-Review Checklist (forward-looking reminder for @governance-reviewer)

At post-implementation, verify:

- [ ] Both tools registered in `FutureProofMCPServer.get_tools()` following the `get_ai_exposure` pattern
- [ ] `data_source` field present in every non-null response row, derived from `verification_status`
- [ ] `verified_only=true` refuses all 43 estimate states with structured null + clear message
- [ ] `verified_only=true` returns all 8 BEA-verified states correctly
- [ ] State normalization handles FIPS, USPS, full name, case-insensitive; reverse lookups (`USPS_TO_FIPS`, `STATE_NAME_TO_FIPS`) derived (not duplicated) from the existing forward dicts in `_us_state_reference.py`
- [ ] Advisory #1 resolved: either full-precision `purchasing_power_multiplier` in the response, or explicit documentation that the displayed value is not to be used for client-side arithmetic
- [ ] Eval set exists at `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` with ≥ 50 cases covering all 11 categories in § "Eval Set"
- [ ] Test suite has ≥ 20 tests at `tests/mcp/test_get_regional_price_parity.py` and `tests/mcp/test_compare_purchasing_power.py`
- [ ] Every response includes `governance.quality_tier = 'partial_verification'`
- [ ] CA at $65K returns exactly `58717.25`; IA at $65K returns exactly `74031.89`; difference exactly `15314.64`; difference_pct exactly `26.08`
- [ ] Audit-trail entry in `governance/audit-trail/` for @mcp-engineer's implementation decisions
- [ ] Condition 7 status in `consumable-regional-price-parities.yaml` updated from "FORWARD-ONLY OBLIGATION" to "DISCHARGED" (or a new audit note added referencing this spec)
- [ ] No new DQ rules introduced (MCP zone inherits from Gold)
- [ ] No new CDE flags introduced (tool response fields already flagged at Gold)
- [ ] `domain/manifest.yaml` updated if a new spec entry is needed
