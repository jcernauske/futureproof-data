# Audit Trail: @dq-rule-writer — mcp-bea-rpp

**Date:** 2026-04-11
**Agent:** @dq-rule-writer
**Spec:** `docs/specs/mcp-bea-rpp.md`
**Zone:** MCP (AI-Ready)
**Artifact produced:** `governance/dq-rules/mcp-bea-rpp.json` (16 rules)

---

## Scope

This run writes MCP-zone **interface contract rules** for the `mcp-bea-rpp`
spec. The MCP zone does NOT introduce new data — it is a read-only tool layer
over the already-signed-off `consumable.regional_price_parities` Gold table
(55 Gold DQ rules, contract status ACTIVE). Data-quality of the underlying
table is already covered; these 16 rules cover only the wire-level guarantees
the Gold rules cannot see:

1. Tool response schema invariants (fields present, correct types, enum values)
2. Strict mode (`verified_only=true`) positive and refusal behavior
3. Input validation (unknown state, invalid salary, same-state rejection)
4. Arithmetic invariants (canonical spec example, ratio invariance)
5. Eval set coverage guarantees

These rules are inherited alongside — not replacing — the 55 rules in
`governance/dq-rules/gold-regional-price-parities.json`.

---

## Evidence sources read

| Source | Purpose |
|---|---|
| `docs/specs/mcp-bea-rpp.md` | Spec requirements, acceptance criteria, response schemas |
| `governance/eda/mcp-bea-rpp-eda.md` | Primary evidence — 65/65 eval pass, byte-for-byte Gold parity, exhaustive 51-state strict-mode sweep, arithmetic reproduction table, input-edge matrix |
| `governance/dq-rules/gold-regional-price-parities.json` | Parent rule set (55 rules) — verified no overlap with MCP interface layer |
| `governance/dq-rules/mcp-ai-exposure.json` | Format reference for sibling MCP-zone rule file |
| `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` | Authoritative eval case ID list (65 cases) |
| `governance/approvals/raw-ingest-bea-rpp-staff-review.md` | Bronze Condition 7 requirements closed by this spec |

---

## Rules written (16 total)

### P0 — response schema invariants (6)

| Rule | Category | Verification |
|---|---|---|
| MCP-BEA-001 | interface_contract | Every success response carries `data_source IN ('bea_official','estimate')` — closes Bronze Condition 7 at the wire. 16 eval cases. |
| MCP-BEA-002 | interface_contract | Every success response carries `governance.quality_tier == 'partial_verification'`. Pytest suite is ground truth; eval cases do not assert framework-injected field (per EDA lines 319-326). |
| MCP-BEA-003 | interface_contract | Every `bea_official` row has `state_fips` in the canonical 8-state set {AR,CA,DC,HI,IA,MS,NJ,OK}. EDA exhaustive 51-state sweep confirms. 16 eval cases. |
| MCP-BEA-004 | interface_contract | `adjusted_examples` has EXACTLY 4 keys: 30k, 50k, 75k, 100k. 14 eval cases. |
| MCP-BEA-005 | interface_contract | `purchasing_power_multiplier` returned at full precision (not rounded to 4 decimals) — verified by reproducing all 4 adjusted_Nk values from `round(salary*ppm,2)` for the 8 BEA rows. |
| MCP-BEA-006 | interface_contract | `cost_tier` IN the 5-value enum. 17 eval cases. |

### P0 — strict mode invariants (3)

| Rule | Category | Verification |
|---|---|---|
| MCP-BEA-007 | strict_mode | 8/8 BEA states succeed under `verified_only=true`. Eval cases `strict-ok-{ar,ca,dc,hi,ia,ms,nj,ok}`. |
| MCP-BEA-008 | strict_mode | Estimate states refuse with null + message containing 'strict' + state name. 5 eval cases; 43/43 exhaustive coverage pinned by pytest. |
| MCP-BEA-009 | strict_mode | `compare_purchasing_power` refuses when either state is estimate. 4 eval cases covering offender in pos a, pos b, and both verified-vs-estimate configurations. |

### P0 — input validation invariants (3)

| Rule | Category | Verification |
|---|---|---|
| MCP-BEA-010 | input_validation | Unknown state → null + helpful message, never raises. 7 eval cases (5 unknown-* + 2 compare-unknown-*). Defense-in-depth edges (int, float, list, None, tab whitespace, DC lowercase) pinned by pytest per EDA 'Untested Input Shapes'. |
| MCP-BEA-011 | input_validation | Invalid salary (negative/zero/>1e7/non-numeric/None/NaN/inf/bool) → null data, never raises. 7 eval cases. NaN/inf/False pinned by pytest per EDA Recommendations #2-3. |
| MCP-BEA-012 | input_validation | Same state (post-normalization) → null + 'must be different'. 3 eval cases covering USPS-same, USPS-vs-name equivalence, FIPS-vs-USPS equivalence. |

### P0 — arithmetic invariants (2)

| Rule | Category | Verification |
|---|---|---|
| MCP-BEA-013 | arithmetic | Canonical spec example — CA vs IA at $65K returns exactly 58717.25 / 74031.89 / 15314.64 / 26.08. 3 eval cases (USPS, name, FIPS input forms). |
| MCP-BEA-014 | arithmetic | Ratio invariance — `adjusted_Nk/Nk` stable across 30k/50k/75k/100k within 1e-4. 8 eval cases (all BEA rows). |

### P1 — coverage rules (2)

| Rule | Category | Verification |
|---|---|---|
| MCP-BEA-015 | coverage | Eval set has >= 50 cases. Current: 65 (30% above minimum). |
| MCP-BEA-016 | coverage | Eval set covers all 11 spec requirement categories. EDA coverage table confirms every category at or above the spec minimum. |

---

## Threshold justification

Every threshold is 100% (P0) or a fixed minimum count (P1 coverage rules).
There are no probabilistic thresholds because:

- All 65 eval cases pass (65/65 per EDA line 228).
- The 51-state strict-mode sweep is exhaustive — 8/8 success, 43/43 refusal,
  zero cross-contamination (EDA lines 180-188).
- The arithmetic cases are byte-for-byte reproducible at full ppm precision
  (EDA lines 52-60 and arithmetic reproduction table lines 195-209).

These are hard invariants, not statistical expectations — if any rule ever
returns non-zero violations, the MCP layer is broken and the response is
incorrect for a user.

---

## Execution note — rules are NOT SQL over Iceberg

These rules are NOT executed by `python -m brightsmith.infra.dq_runner`
because they are contracts on tool RESPONSES, not rows in a table. Each rule
carries a `verification_method` field ("eval_set_execution" or
"in_process_probe") and a list of anchor `eval_case_ids` that exercise it.

Ground truth for these rules lives in two places:

1. **Eval set execution** — `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`, 65
   cases, verified 65/65 PASS against the live `FutureProofMCPServer` per
   `governance/eda/mcp-bea-rpp-eda.md` (lines 220-230).
2. **Pytest suite** — `tests/mcp/test_get_regional_price_parity.py` (42 tests)
   and `tests/mcp/test_compare_purchasing_power.py` (28 tests), 70 total
   functions exercising exhaustive 51-state strict-mode, framework governance
   fields, defense-in-depth input edges, and arithmetic reproduction.

Every one of the 16 rules is ALREADY verified by one or both of these
mechanisms at the time of writing.

---

## Rules considered but NOT written

### Gold-layer data quality (out of scope)

The 55 rules in `governance/dq-rules/gold-regional-price-parities.json`
already cover:

- 51-row state completeness
- `data_year = 2024` freshness
- `state_fips` primary-key uniqueness
- `rpp_all_items` range checks and column nullability
- `cost_tier` enum enforcement at the row level
- `verification_status` 2-value enum at the row level
- `purchasing_power_multiplier` precision and range
- All four `adjusted_Nk` computations matching `round(rpp * Nk / 100, 2)`

These are enforced at the Iceberg layer and inherited transitively. Writing
duplicate MCP-layer rules would add noise without new guarantees.

### Defense-in-depth edges: pytest, not eval

EDA 'Untested Input Shapes' (lines 233-272) enumerates 19 edge cases for
`get_regional_price_parity` and 13 for `compare_purchasing_power` that the
live server handles correctly but the eval set does not enumerate. Rather
than promote each one to its own DQ rule, I folded them into the rationale
of MCP-BEA-010, MCP-BEA-011, and MCP-BEA-012 with explicit references to
the pytest suite. Reasoning: they are minor variants of three behaviors
already pinned at the rule level — wrapping each in its own rule would
inflate the rule count without improving regression coverage.

### Response time / latency SLO

The sibling `mcp-ai-exposure.json` file has a response-time rule (MCP-AIE-005).
I did NOT write one here because:

1. The spec does not declare a latency SLO for `mcp-bea-rpp`.
2. The EDA does not measure response times.
3. Writing a rule with a guessed threshold would violate the "no evidence,
   no threshold" discipline.

If a latency SLO is added to the spec later, a follow-up rule
(MCP-BEA-017) can be added.

### `message_contains` exact wording rules

EDA lines 149-155 explicitly flags that strict-mode eval cases assert only
`message_contains: ["estimate", <state name>]` and `["Strict mode", <state
name>]` — pinning identification WITHOUT freezing exact wording. I honored
this design choice: MCP-BEA-008 and MCP-BEA-009 assert 'strict' (or 'Strict
mode') and the state name appear in the message, but do not pin the full
canonical string. This is the right level of brittleness for natural-language
messages.

---

## Rules that CAN'T be cleanly expressed in this non-SQL format

**None.** All 16 rules are expressible as declarative invariants with a
`verification_method`, `eval_case_ids`, `threshold`, and `rationale`. The
format is intentionally lossier than SQL-over-Iceberg — it names the
verification mechanism rather than embedding it — which is the correct
trade-off for a tool-layer contract file.

The only quasi-exception is MCP-BEA-014 (ratio invariance). Expressing it in
SQL would require a UDF that divides adjusted_Nk by Nk for all 4 struct
members and checks their max-min spread. That SQL exists for the Gold table
(see `gold-regional-price-parities.json` GRP-CONS-*), so this rule is a
wire-level mirror of a Gold-level SQL rule — not a gap.

---

## Framework guard: `category` populated on every rule

The user's hard constraint was "Every rule has `category` populated (avoid
the framework ArrowInvalid)." JSON validation confirms:

```
rules missing category: none
  interface_contract: 6
  strict_mode: 3
  input_validation: 3
  arithmetic: 2
  coverage: 2
```

Every rule ALSO has `severity`, `dimension`, `priority`, `verification_method`,
`eval_case_ids`, `threshold`, `rationale`, `status`, `proposed_by`, and
`proposed_at`, so no downstream framework field is missing either.

---

## Eval set ↔ test suite crosswalk

| Verification mechanism | Cases / tests | Rules covered |
|---|---|---|
| Eval set (65 cases, 65/65 pass) | 65 | MCP-BEA-001, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016 |
| Pytest `test_get_regional_price_parity.py` (42 tests) | 42 | MCP-BEA-002, 008 (full 43/43 refusal sweep), 010 (defense-in-depth edges) |
| Pytest `test_compare_purchasing_power.py` (28 tests) | 28 | MCP-BEA-002, 009 (state_b offender, both-estimate), 011 (NaN/inf/False), 012 (whitespace equivalence) |

**Every rule is covered by at least one mechanism. Most P0 rules are covered
by both.**

---

## Confirmation

- [x] Rule file written: `governance/dq-rules/mcp-bea-rpp.json` (16 rules)
- [x] JSON parses cleanly (`json.load` succeeds)
- [x] Every rule has `category` populated
- [x] Every rule has `verification_method` and `eval_case_ids`
- [x] Every rule cites EDA evidence in `rationale`
- [x] No overlap with the 55 Gold rules in `gold-regional-price-parities.json`
- [x] Every rule is already verified by the eval set, the pytest suite, or both
- [x] Audit trail written (this file)

---

*— End of audit trail —*
