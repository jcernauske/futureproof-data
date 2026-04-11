# CDE/PII Tagging: mcp-bea-rpp

**Spec:** `docs/specs/mcp-bea-rpp.md`
**Parent Specs:** `docs/specs/gold-regional-price-parities.md`, `docs/specs/silver-base-bea-rpp.md`, `docs/specs/raw-ingest-bea-rpp.md`
**Zone:** MCP (AI-Ready — read-only tool layer)
**Date:** 2026-04-11
**Agent:** @cde-tagger
**Gold Source Table:** `consumable.regional_price_parities` (15 columns, 51 rows)
**Upstream tagging:**
- `governance/cde-tagging/gold-regional-price-parities.md` (Gold, **13 CDE / 0 PII** across 15 columns)
- `governance/cde-tagging/silver-base-bea-rpp.md` (Silver, 8 CDE / 0 PII)
- `governance/cde-tagging/raw-ingest-bea-rpp.md` (Bronze, 4 CDE / 0 PII)
- `governance/pii-scans/gold-regional-price-parities.md` — NO PII, k-anonymity floor ~584,000 unchanged

---

## Scope

This spec exposes two read-only MCP tools over the Gold table `consumable.regional_price_parities`:

1. `get_regional_price_parity(state, verified_only?)`
2. `compare_purchasing_power(salary, state_a, state_b, verified_only?)`

No new columns are introduced at the MCP zone. The tool response contracts project, rename, bundle, and (in tool 2) derive scalar values from the stored Gold columns. Per Brightsmith no-propagation policy, CDE flags do **not** automatically carry over from Gold — each response field is re-evaluated against its role in the MCP wire contract. In this spec, the re-evaluation re-affirms every Gold CDE that appears in a response and additionally flags the two derived compare-tool fields that represent student-facing adjusted salary figures.

### Response-field counting convention

- **`adjusted_examples`** in Tool 1 is counted as a single struct field (it bundles the four Gold `adjusted_Nk` columns behind one wire name). The four leaves are tagged collectively through the struct.
- **`state_a` / `state_b`** in Tool 2 are counted as flattened leaves (each has 6 sub-fields), because each leaf exists independently on the wire and needs its own CDE flag.
- **`governance.*`** envelope fields are counted as top-level response fields (framework-added metadata), per the MCP framework contract pattern.

Under this convention:
- Tool 1 `get_regional_price_parity` — **14 response fields**
- Tool 2 `compare_purchasing_power` — **19 response fields**

---

## Domain Context Referenced

- `governance/domain-context.md` §BEA RPP — regulatory posture (none), PII expectations (none), canonical concept map
- `governance/cde-tagging/gold-regional-price-parities.md` — Gold CDE baseline (13 of 15 columns flagged)
- `governance/pii-scans/gold-regional-price-parities.md` — NO PII decision, k-anonymity ~584,000
- `docs/specs/mcp-bea-rpp.md` §MCP Tools, §Implementation Notes — response schemas, rename (`verification_status` → `data_source`), bundling (`adjusted_30k/50k/75k/100k` → `adjusted_examples`), derivations in compare tool
- `docs/specs/mcp-bea-rpp.md` §Bronze Staff Review Conditions — explicit mandate that `verification_status` survive into the wire contract (surfaced as `data_source`)

**Applicable regulations:** NONE. BEA RPPs are U.S. Government aggregate economic statistics in the public domain. No HIPAA / FERPA / GLBA / SOX / GDPR / CCPA / CPRA / PCI DSS exposure at MCP zone. The wire contract returns only state-level aggregates and deterministic scalar derivations of them.

**PII expectations:** NONE. Every response field is either a state-level public jurisdiction identifier, a state-level macroeconomic aggregate, a lossy generalization of such, a deterministic function of a national salary anchor times a state-level multiplier, or framework-level operational metadata. k-anonymity floor is ~584,000 at the finest grain (Wyoming, the smallest state).

---

## Tool 1: `get_regional_price_parity` — Response Field CDE/PII Table

**Total response fields: 14**

| # | Response field | Type | Gold source | is_cde | is_pii | Carry-forward / rationale |
|---|---|---|---|---|---|---|
| 1 | `data.state_name` | string | `state_name` (passthrough) | **true** | false | Carry-forward from Gold CDE. Primary human-readable display label served to Gemma for every MCP response. Fallback identifier when user passes state by full name via tool input normalization. |
| 2 | `data.state_abbr` | string | `state_abbr` (passthrough) | **true** | false | Carry-forward from Gold CDE. The identifier the frontend widget and URL query strings use. Round-trip target for user state selection. |
| 3 | `data.state_fips` | string | `state_fips` (passthrough) | **true** | false | Carry-forward from Gold CDE. ANSI/FIPS primary key. Anchors the underlying Gold row lookup and is returned on the wire for consumer-side joins back to any other state-indexed product table. |
| 4 | `data.census_region` | string | `census_region` (passthrough) | **true** | false | Carry-forward from Gold CDE. Four-valued Census Bureau enum driving frontend regional comparison views and stretch-goal Fight Location Lock boss. Consumer-facing on the wire. |
| 5 | `data.rpp_all_items` | double | `rpp_all_items` (passthrough) | **true** | false | Carry-forward from Gold CDE. The entire analytical payload of the table. Directly displayed by Gemma (e.g., "California's RPP is 110.7"). Wrong value here mis-states every salary adjustment for that state. Highest-criticality field in the wire contract. |
| 6 | `data.purchasing_power_multiplier` | double | `purchasing_power_multiplier` (passthrough) | **true** | false | Carry-forward from Gold CDE. Consumer-side users of this tool (including tool 2 itself) use this value to recompute adjusted salary at arbitrary anchors beyond the four pre-materialized examples. P0 inverse invariant DQ at the Gold tier guards correctness; the wire contract just projects it. |
| 7 | `data.cost_tier` | string | `cost_tier` (passthrough) | **true** | false | Carry-forward from Gold CDE. Drives frontend color coding, boss-fight difficulty, and Gemma narrative prompts per spec. No substitute wire field encodes tier. |
| 8 | `data.adjusted_examples` | struct<30k:double, 50k:double, 75k:double, 100k:double> | bundles `adjusted_30k` / `adjusted_50k` / `adjusted_75k` / `adjusted_100k` | **true** | false | Carry-forward from Gold CDE — **all four Gold `adjusted_Nk` columns are CDE and the bundling into a struct on the wire does not dilute that**. This is the display-ready salary adjustment value set Gemma and the frontend consume directly. P0 DQ at Gold pins each leaf within 1 cent of the formula; the MCP handler is a pure projection + bundle. NOT individual earnings data — state-level reference values at fixed national anchors. |
| 9 | `data.data_source` | string | **renamed from `verification_status`** | **true** | false | **Carry-forward from Gold CDE under the Bronze Condition 7 rename mandate.** `verification_status` in Gold is the CDE; on the MCP wire it is renamed to `data_source` for Gemma-facing clarity. The rename does not change the governance status — the same 2-valued enum ('bea_official' vs. 'estimate') that gates Gemma's numeric-precision hedging in Gold continues to gate it here. Bronze staff-review Condition 7 (MCP half) is closed by this field. |
| 10 | `data.data_year` | int | `data_year` (passthrough) | **true** | false | Carry-forward from Gold CDE. Provenance-critical temporal dimension surfaced to Gemma so it can caveat stale vintages. RPPs re-publish annually and mis-labeled vintage silently stales every downstream salary number. |
| 11 | `row_count` | int | framework envelope | false | false | Response envelope counter. Always 1 for a single-state lookup (or absent in null-case responses). Operational observability only — not a decision input, not consumer-facing beyond the debug layer, not derived from a CDE source column. |
| 12 | `governance.table` | string | framework envelope | false | false | Framework-added metadata identifying the Gold source (`consumable.regional_price_parities`). Constant across all responses — not a per-row decision input. |
| 13 | `governance.quality_tier` | string | framework envelope | false | false | Framework-added metadata. Constant `partial_verification` per Gold contract. Not a per-row decision input; Gemma uses the per-row `data_source` field to hedge precision, not this envelope. |
| 14 | `governance.owner` | string | framework envelope | false | false | Framework-added metadata. Constant `@data-steward`. Operational accountability label, not a decision input. |

**Tool 1 totals:**
- Response fields evaluated: **14**
- CDE-flagged: **10** (fields 1-10)
- PII-flagged: **0**
- Non-CDE fields: **4** (`row_count` + the three `governance.*` envelope fields)
- Gold CDE columns exposed through this tool: **all 13** — the 8 Silver-passthrough Gold CDEs (`state_fips`, `state_name`, `state_abbr`, `census_region`, `rpp_all_items`, `purchasing_power_multiplier`, `verification_status`, `data_year`) + `cost_tier` + the four `adjusted_Nk` columns (bundled into the single CDE struct `adjusted_examples`). The two Gold non-CDE columns (`record_id`, `promoted_at`) are not exposed on the wire.

---

## Tool 2: `compare_purchasing_power` — Response Field CDE/PII Table

**Total response fields: 19**

| # | Response field | Type | Gold source | is_cde | is_pii | Carry-forward / rationale |
|---|---|---|---|---|---|---|
| 1 | `data.salary` | double | **user input (echoed)** | **true** | false | Student-facing salary figure being compared. Echoing it back into the response is load-bearing: Gemma narrates "at $65,000 …" using the echoed value and the adjusted_salary figures below derive from it. Wrong echo would desynchronize the narrative from the derivation. Flagged as MCP-origin CDE because it is a student-facing salary figure in the wire contract. Not PII — user-supplied anchor, not observed individual earnings tied to an identified subject at the MCP tier. |
| 2 | `data.state_a.state_name` | string | `state_name` (passthrough) | **true** | false | Carry-forward from Gold CDE. Display label for the first comparison state. |
| 3 | `data.state_a.state_abbr` | string | `state_abbr` (passthrough) | **true** | false | Carry-forward from Gold CDE. Frontend identifier for the first comparison state. |
| 4 | `data.state_a.adjusted_salary` | double | **derived at tool-call time**: `round(salary × purchasing_power_multiplier, 2)` | **true** | false | **New MCP-origin CDE flag.** This is THE student-facing adjusted salary figure — the whole purpose of the tool. Wrong value here misleads the student. Derived live per request from the user-supplied `salary` and the Gold-stored `purchasing_power_multiplier` (itself a Gold CDE). The acceptance criteria pin the CA vs. IA at $65K case to $58,717.25 / $74,031.89, and the eval set covers success cases at $30K / $50K / $75K / $100K / $65K. Not PII — state-level reference computation at a user-supplied anchor, not observed individual earnings. |
| 5 | `data.state_a.cost_tier` | string | `cost_tier` (passthrough) | **true** | false | Carry-forward from Gold CDE. Drives frontend color coding / narrative tone for state_a in the comparison UI. |
| 6 | `data.state_a.purchasing_power_multiplier` | double | `purchasing_power_multiplier` (passthrough) | **true** | false | Carry-forward from Gold CDE. Returned so consumers can verify the derivation of `adjusted_salary` and re-apply it at alternate anchors client-side. |
| 7 | `data.state_a.data_source` | string | **renamed from `verification_status`** | **true** | false | Carry-forward from Gold CDE under the same rename mandate as tool 1 field 9. Per-state provenance Gemma uses to hedge numeric precision in the side-by-side comparison. Bronze staff review Condition 7 (MCP half) requires this for each compared state. |
| 8 | `data.state_b.state_name` | string | `state_name` (passthrough) | **true** | false | Carry-forward from Gold CDE. Same rationale as field 2, for the second comparison state. |
| 9 | `data.state_b.state_abbr` | string | `state_abbr` (passthrough) | **true** | false | Carry-forward from Gold CDE. Same rationale as field 3. |
| 10 | `data.state_b.adjusted_salary` | double | **derived at tool-call time**: `round(salary × purchasing_power_multiplier, 2)` | **true** | false | **New MCP-origin CDE flag.** Same rationale as field 4, for the second comparison state. |
| 11 | `data.state_b.cost_tier` | string | `cost_tier` (passthrough) | **true** | false | Carry-forward from Gold CDE. Same rationale as field 5. |
| 12 | `data.state_b.purchasing_power_multiplier` | double | `purchasing_power_multiplier` (passthrough) | **true** | false | Carry-forward from Gold CDE. Same rationale as field 6. |
| 13 | `data.state_b.data_source` | string | **renamed from `verification_status`** | **true** | false | Carry-forward from Gold CDE. Same rationale as field 7, for the second comparison state. |
| 14 | `data.difference` | double | **derived at tool-call time**: `state_b.adjusted_salary − state_a.adjusted_salary` | **true** | false | **New MCP-origin CDE flag.** This is the headline dollar-figure answer to the "What if I move?" user question. Directly displayed in the frontend and narrated by Gemma. Wrong value here is the single most visible failure mode of the tool. Not PII — arithmetic difference of two state-level reference computations. |
| 15 | `data.difference_pct` | double | **derived at tool-call time**: `round(difference / state_a.adjusted_salary × 100, 2)` | false | false | Percentage form of `difference`. Derived purely from `difference` and `state_a.adjusted_salary`, both already flagged CDE. Useful for narrative framing ("26% more purchasing power") but a pure scalar function of fields already governed as CDE. Flagging is optional; omitted here to keep the CDE set tight per the CDE principle that derived-from-CDE scalars do not require independent flagging unless they are themselves decision inputs. The decision input is `difference`; `difference_pct` is presentation. |
| 16 | `row_count` | int | framework envelope | false | false | Response envelope counter. Always 2 for a successful comparison. Operational only. |
| 17 | `governance.table` | string | framework envelope | false | false | Framework metadata, constant `consumable.regional_price_parities`. |
| 18 | `governance.quality_tier` | string | framework envelope | false | false | Framework metadata, constant `partial_verification`. |
| 19 | `governance.owner` | string | framework envelope | false | false | Framework metadata, constant `@data-steward`. |

**Tool 2 totals:**
- Response fields evaluated: **19**
- CDE-flagged: **14** (fields 1-14)
- PII-flagged: **0**

---

## Decision Notes on Derived Fields

The spec identifies three derived fields in `compare_purchasing_power` computed at tool-call time:

1. **`state_a.adjusted_salary` / `state_b.adjusted_salary`** — flagged **CDE**. These are student-facing adjusted salary figures in the wire contract. They are the primary analytical answer of the tool and the value pinned by the CA-vs-IA acceptance criterion. Derivation semantics (`round(salary × ppm, 2)` using Python built-in `round`'s banker's rounding) is pinned in the spec's Implementation Notes to match DuckDB and Gold rounding. Incorrect values here are the worst-case failure mode of the tool.

2. **`difference`** — flagged **CDE**. Headline dollar-figure answer to "What if I move?", directly displayed and narrated by Gemma.

3. **`difference_pct`** — **not flagged** CDE. Pure scalar function of `difference` and `state_a.adjusted_salary`, both already CDE. Presentation/narrative field, not an independent decision input. Per the CDE principle that derived-from-CDE scalars do not require independent flagging unless they themselves drive a distinct decision, this field is intentionally left un-flagged. If downstream product evolution makes `difference_pct` the primary answer (e.g., a comparison ranking screen keyed on percentage rather than absolute dollars), this decision should be revisited.

---

## PII Decisions

**Zero PII across both tools.** The NO-PII decision from `governance/pii-scans/gold-regional-price-parities.md` carries forward intact to the MCP wire contract because:

1. Every passthrough field is a state-level public jurisdiction identifier or macroeconomic aggregate.
2. `cost_tier` is a 5-bucket lossy generalization of a non-PII aggregate and strictly *increases* k-anonymity.
3. `adjusted_examples` bundles four reference values at fixed national anchors — NOT observed individual earnings data.
4. `adjusted_salary` (tool 2) is a reference computation at a user-supplied anchor multiplied by a non-PII state-level multiplier — NOT observed individual earnings of any identified subject. The user-supplied `salary` input arrives at the MCP tier disconnected from subject identity; the tool does not persist, log, or correlate it with any identifier, and the wire contract returns only the computation.
5. `difference` / `difference_pct` are arithmetic differences of two such reference computations.
6. `data_source` (renamed `verification_status`) is a row-level provenance enum with two values — carries no personal information.
7. `row_count` and `governance.*` are framework operational metadata.

k-anonymity floor remains ~584,000 (Wyoming). No regulatory framework is triggered. Sensitivity classification is `public` across the full wire contract.

**0 of 14 tool 1 response fields flagged PII.**
**0 of 19 tool 2 response fields flagged PII.**

---

## Bronze Condition 7 (MCP half) — explicit confirmation

Bronze staff review Condition 7 requires that per-row verification provenance survive into every MCP tool response so that Gemma can hedge numeric precision for estimated values. This tagging confirms:

- Tool 1 field 9 `data.data_source` is CDE-flagged and is the carry-forward of Gold `verification_status`.
- Tool 2 field 7 `data.state_a.data_source` and field 13 `data.state_b.data_source` are both CDE-flagged and both are carry-forwards of Gold `verification_status`.

All three fields preserve the 2-valued Gold enum `'bea_official' | 'estimate'` verbatim — only the wire name changes. The rename is documented in the spec's Implementation Notes and does not alter governance status.

---

## Summary

| Metric | Tool 1 | Tool 2 | Combined |
|---|---|---|---|
| Response fields evaluated | **14** | **19** | 33 |
| CDE-flagged response fields | **10** | **14** | 24 |
| PII-flagged response fields | **0** | **0** | **0** |
| Carry-forward from Gold CDE | 10 | 10 | 20 |
| New MCP-origin CDE flags | 0 | 4 (`salary` echo, `state_a.adjusted_salary`, `state_b.adjusted_salary`, `difference`) | 4 |
| Framework envelope fields (not CDE) | 4 (`row_count`, 3 × `governance.*`) | 4 (same) | 8 |
| `data_source` CDE-flagged as carry-forward of `verification_status` | **CONFIRMED** (field 9) | **CONFIRMED** (fields 7, 13) | 3 instances |
| Regulatory frameworks triggered | None | None | None |
| Sensitivity classification | `public` | `public` | `public` |

---

## Handoff to @doc-generator

If/when MCP tool response contracts are materialized into a data-contract-style YAML artifact under `governance/data-contracts/mcp-bea-rpp.yaml`, each response field listed above should carry the `is_cde`, `cde_rationale`, `is_pii`, and `pii_rationale` flags exactly as decided here. The rename `verification_status → data_source` must be explicit in the contract so downstream governance tooling can trace the wire name back to the Gold column and its Bronze Condition 7 mandate.

## Handoff to @governance-reviewer

All flags are justified by either (a) direct carry-forward from an already-reviewed Gold CDE, (b) explicit spec language (Bronze Condition 7, acceptance criteria pinning CA-vs-IA adjusted salary values, tool purpose statement), or (c) the standard CDE principle for student-facing financial figures on the wire. No backward propagation. No forward propagation from Gold was assumed — every carry-forward was explicitly re-justified against the field's role in the MCP wire contract.
