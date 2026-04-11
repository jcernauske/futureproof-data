# Audit Trail: CDE/PII Tagging — mcp-bea-rpp

**Date:** 2026-04-11
**Agent:** @cde-tagger
**Spec:** `docs/specs/mcp-bea-rpp.md`
**Zone:** MCP (AI-Ready — read-only tool layer over Gold)
**Gold Source Table:** `consumable.regional_price_parities` (15 columns, 51 rows)
**Output artifact:** `governance/cde-tagging/mcp-bea-rpp.md`

---

## Inputs Consulted

| Artifact | Purpose |
|---|---|
| `docs/specs/mcp-bea-rpp.md` | Tool schemas, response payload shapes, rename of `verification_status` → `data_source`, bundling of `adjusted_30k/50k/75k/100k` → `adjusted_examples`, `compare_purchasing_power` derivation formulas, Bronze Condition 7 MCP-half mandate |
| `governance/cde-tagging/gold-regional-price-parities.md` | Gold CDE baseline (13 CDE / 0 PII of 15 columns) for carry-forward evaluation |
| `governance/cde-tagging/silver-base-bea-rpp.md` | Silver CDE baseline (full lineage context) |
| `governance/cde-tagging/raw-ingest-bea-rpp.md` | Bronze CDE baseline (full lineage context) |
| `governance/pii-scans/gold-regional-price-parities.md` | NO-PII decision, k-anonymity floor ~584,000 |
| `governance/domain-context.md` §BEA RPP | Regulatory posture (none), PII expectations (none) |
| `governance/approvals/raw-ingest-bea-rpp-staff-review.md` §Condition 7 | Explicit mandate that per-row verification provenance survive into MCP tool responses |

---

## Method

Per Brightsmith no-propagation policy, CDE flags do not automatically carry forward from Gold to MCP. Each MCP response field was re-evaluated against its role in the wire contract. Because MCP introduces no new columns — only projections, renames, struct bundling, and live-derived scalars — the evaluation largely re-affirms Gold CDE decisions but also adds four new MCP-origin CDE flags for the compare-tool derived fields and the echoed salary input.

The response-field counting convention used:

- `adjusted_examples` in Tool 1 counted as **1 struct field** (bundles 4 Gold `adjusted_Nk` leaves behind one wire name)
- `state_a` / `state_b` in Tool 2 counted as **flattened leaves** (each has 6 sub-fields)
- `governance.*` envelope fields counted as top-level response fields

Under this convention:
- Tool 1 `get_regional_price_parity` — 14 response fields
- Tool 2 `compare_purchasing_power` — 19 response fields

---

## Decision Log

### Tool 1: `get_regional_price_parity` (14 response fields)

| Response field | Decision | Origin | Notes |
|---|---|---|---|
| `data.state_name` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_abbr` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_fips` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.census_region` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.rpp_all_items` | CDE=true, PII=false | carry-forward | Gold CDE passthrough — highest-criticality field |
| `data.purchasing_power_multiplier` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.cost_tier` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.adjusted_examples` (struct) | CDE=true, PII=false | carry-forward | All 4 Gold `adjusted_Nk` CDEs bundled; the struct inherits the flags of its leaves |
| `data.data_source` | **CDE=true**, PII=false | **carry-forward under rename** | Gold `verification_status` renamed per Bronze Condition 7 MCP-half mandate |
| `data.data_year` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `row_count` | CDE=false, PII=false | framework envelope | Operational counter |
| `governance.table` | CDE=false, PII=false | framework envelope | Constant metadata |
| `governance.quality_tier` | CDE=false, PII=false | framework envelope | Constant metadata |
| `governance.owner` | CDE=false, PII=false | framework envelope | Constant metadata |

**Tool 1: 10 CDE-flagged / 0 PII-flagged / 4 non-CDE of 14 response fields.**

### Tool 2: `compare_purchasing_power` (19 response fields)

| Response field | Decision | Origin | Notes |
|---|---|---|---|
| `data.salary` | **CDE=true**, PII=false | **MCP-origin** | Echoed user input — narrative-coupled to derived adjusted_salary values |
| `data.state_a.state_name` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_a.state_abbr` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_a.adjusted_salary` | **CDE=true**, PII=false | **MCP-origin (derived)** | `round(salary × ppm, 2)` computed at tool-call time. Student-facing primary answer. |
| `data.state_a.cost_tier` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_a.purchasing_power_multiplier` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_a.data_source` | **CDE=true**, PII=false | **carry-forward under rename** | Gold `verification_status` renamed per Bronze Condition 7 |
| `data.state_b.state_name` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_b.state_abbr` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_b.adjusted_salary` | **CDE=true**, PII=false | **MCP-origin (derived)** | Same as state_a.adjusted_salary |
| `data.state_b.cost_tier` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_b.purchasing_power_multiplier` | CDE=true, PII=false | carry-forward | Gold CDE passthrough |
| `data.state_b.data_source` | **CDE=true**, PII=false | **carry-forward under rename** | Gold `verification_status` renamed per Bronze Condition 7 |
| `data.difference` | **CDE=true**, PII=false | **MCP-origin (derived)** | Headline dollar-figure answer to the "What if I move?" scenario |
| `data.difference_pct` | CDE=false, PII=false | derived | Pure scalar function of two already-CDE fields; presentation-only, not an independent decision input |
| `row_count` | CDE=false, PII=false | framework envelope | Operational counter |
| `governance.table` | CDE=false, PII=false | framework envelope | Constant metadata |
| `governance.quality_tier` | CDE=false, PII=false | framework envelope | Constant metadata |
| `governance.owner` | CDE=false, PII=false | framework envelope | Constant metadata |

**Tool 2: 14 CDE-flagged / 0 PII-flagged / 5 non-CDE of 19 response fields.**

### Fields intentionally NOT flagged

| Field | Tool | Reason |
|---|---|---|
| `data.difference_pct` | tool 2 | Pure scalar function (%) of `difference` and `state_a.adjusted_salary`, both already CDE. Presentation/narrative framing, not an independent decision input. If product pivots to a percentage-keyed ranking view, revisit. |
| `row_count` | both | Framework envelope counter. Operational observability only. |
| `governance.table`, `governance.quality_tier`, `governance.owner` | both | Framework metadata. Constants across all responses for this spec. Gemma uses per-row `data_source` (not envelope `quality_tier`) to hedge numeric precision. |

### Bronze Condition 7 (MCP half) verification

Bronze staff review Condition 7 explicitly required that per-row verification provenance survive into every MCP tool response so Gemma can hedge numeric precision for estimated values. This tagging confirms **data_source is CDE-flagged as a carry-forward of verification_status in all 3 places it appears**:

1. Tool 1 `data.data_source`
2. Tool 2 `data.state_a.data_source`
3. Tool 2 `data.state_b.data_source`

All three preserve the Gold 2-valued enum `'bea_official' | 'estimate'` verbatim. The wire rename `verification_status → data_source` is documented in the spec's Implementation Notes and does not alter governance status.

### PII decisions (all 33 response fields across both tools)

Delegated to `governance/pii-scans/gold-regional-price-parities.md` (NO PII decision) and extended to the two MCP-origin derivation families:

- **Echoed `salary`** (tool 2 field 1): user-supplied anchor, not observed individual earnings tied to any identified subject; the MCP tier does not persist or correlate it with identifiers.
- **`adjusted_salary`** (tool 2, both states): scalar product of a user-supplied anchor and a non-PII state-level multiplier — NOT observed individual earnings of any identified subject.
- **`difference` / `difference_pct`**: arithmetic difference and ratio of two such non-PII reference computations.

All other fields are state-level public jurisdiction identifiers or macroeconomic aggregates inherited from Gold. k-anonymity floor unchanged at ~584,000 (Wyoming). No regulatory framework (HIPAA / FERPA / GLBA / SOX / GDPR / CCPA / CPRA / PCI DSS) triggered. Sensitivity classification `public` across both wire contracts.

**0 of 14 tool 1 response fields flagged PII.**
**0 of 19 tool 2 response fields flagged PII.**
**0 of 33 combined wire response fields flagged PII.**

---

## Summary

| Metric | Tool 1 | Tool 2 | Combined |
|---|---|---|---|
| Response fields evaluated | 14 | 19 | 33 |
| CDE-flagged | **10** | **14** | 24 |
| PII-flagged | **0** | **0** | **0** |
| Carry-forward from Gold CDE | 10 | 10 | 20 |
| New MCP-origin CDE flags | 0 | 4 | 4 |
| Framework envelope (not CDE) | 4 | 4 | 8 |
| Derived-but-not-flagged | 0 | 1 (`difference_pct`) | 1 |
| `data_source` CDE-flagged as carry-forward of `verification_status` | CONFIRMED (1) | CONFIRMED (2) | 3 instances |
| Regulatory frameworks triggered | None | None | None |
| Sensitivity classification | `public` | `public` | `public` |

---

## Handoff

**@doc-generator:** If MCP response contracts are materialized into a YAML artifact under `governance/data-contracts/mcp-bea-rpp.yaml`, embed the per-field flags as decided. Preserve the rename `verification_status → data_source` explicitly so downstream tooling can trace wire names back to Gold columns and the Bronze Condition 7 mandate.

**@governance-reviewer:** All flags are justified by either (a) carry-forward from an already-reviewed Gold CDE, (b) explicit spec language (Bronze Condition 7 MCP-half mandate, CA-vs-IA $65K acceptance criteria, tool-purpose statement), or (c) the standard CDE principle for student-facing financial figures on the wire. No backward propagation. No forward propagation was silently assumed — every carry-forward was explicitly re-justified against the field's role in the MCP wire contract. The single intentional non-flag (`difference_pct`) is documented with its forward-looking revisit condition.
