# Doc Generator Audit Trail — mcp-bea-rpp

**Date:** 2026-04-11
**Agent:** @doc-generator
**Spec:** `docs/specs/mcp-bea-rpp.md`
**Zone:** MCP (AI-Ready — read-only tool layer)
**Pipeline stage:** Post-implementation documentation (runs after CDE tagging, DQ rule authoring, MCP tool implementation, and data-analyst EDA sign-off)

---

## Scope

Documented the two MCP tools exposed by spec `mcp-bea-rpp` over the Gold table `consumable.regional_price_parities`:

1. `get_regional_price_parity(state, verified_only?)` — point lookup by state, 14 response fields
2. `compare_purchasing_power(salary, state_a, state_b, verified_only?)` — two-row side-by-side comparison with derived arithmetic, 19 response fields

Both tools inherit the `partial_verification` quality tier from the backing Gold contract verbatim — no new transformations, no Iceberg DML, a thin read + arithmetic layer.

## Files Produced

| Path | Type | Action | Notes |
|---|---|---|---|
| `governance/data-contracts/mcp-bea-rpp.yaml` | Data contract | CREATED | MCP tool contract covering both tools. Status: `draft` pending staff-engineer sign-off. |
| `governance/data-dictionary.json` | Data dictionary | UPDATED | Added two top-level entries: `mcp.get_regional_price_parity` (14 field entries) and `mcp.compare_purchasing_power` (19 field entries). Total 33 new field entries. |
| `governance/audit-trail/2026-04-11-doc-generator-mcp-bea-rpp.md` | Audit trail | CREATED | This file. |

## Files Referenced (Read-Only)

| Path | Purpose |
|---|---|
| `docs/specs/mcp-bea-rpp.md` | Authoritative spec — tool signatures, response schemas, null-case responses, Bronze Condition 7 mandate, acceptance criteria |
| `governance/cde-tagging/mcp-bea-rpp.md` | 24 CDEs / 0 PII across 33 response fields — embedded verbatim into the contract |
| `governance/data-contracts/consumable-regional-price-parities.yaml` | Parent Gold contract — source of backing-table schema and every carry-forward CDE rationale |
| `governance/dq-rules/mcp-bea-rpp.json` | 16 MCP-BEA interface contract rules (14 P0 + 2 P1) — referenced from both tools |
| `governance/dq-rules/gold-regional-price-parities.json` | 55 Gold DQ rules — referenced as the backing-table DQ floor |
| `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl` | 65-case eval set — verified line count (`wc -l` returns 65, exceeds the 50-case minimum) |
| `governance/business-glossary.json` | Confirmed BT-098..BT-107 all present and approved/auto-approved |
| `governance/cde-tagging/mcp-ai-exposure.yaml` (existing precedent) | Naming convention precedent — MCP contracts are named after the spec slug, not the backing Iceberg table |
| `governance/lineage/mcp-bea-rpp-20260411.json` | Lineage reference confirmed present |
| `src/mcp_server/futureproof_server.py` | Confirmed both tool handlers registered (`_handle_get_regional_price_parity` line 434; `_handle_compare_purchasing_power` line 554) |

---

## Key Decisions Made

### 1. Single contract file covering both tools

**Decision:** Place both tools in one contract file (`mcp-bea-rpp.yaml`), not one per tool.

**Rationale:** Matches the precedent set by `governance/data-contracts/mcp-ai-exposure.yaml` (single tool under one spec file) and reflects the semantic reality that both tools are exposed by a single spec, share the same backing Gold table, share the same quality tier, share the same DQ rule set, and share the same Bronze Condition 7 closure. Splitting would duplicate all of that metadata and create two places for the Condition 7 closure record. The file uses a `tools:` list so each tool has its own complete sub-contract (input schema, response schema, response-field CDE table, null-case list, CDE summary).

### 2. Contract naming: `mcp-bea-rpp.yaml` not `consumable-regional-price-parities-mcp.yaml`

**Decision:** Use the spec slug as the filename.

**Rationale:** Gold/Consumable zone contracts are named after their target Iceberg namespace (`consumable-<table>.yaml`) per the project convention documented in `governance/data-contracts/consumable-regional-price-parities.yaml`. MCP contracts exist in a different zone — they do not own an Iceberg namespace — so they are named after the spec slug. The existing `mcp-ai-exposure.yaml` file established this precedent. This decision avoids creating ambiguity between the Gold contract (which owns `consumable.regional_price_parities`) and the MCP contract (which exposes tools over it).

### 3. verification_status → data_source rename documented at three layers

**Decision:** Document the Gold→MCP rename in three explicit places inside the contract:
1. As a `rename_note` key on every affected response field (3 total: Tool 1 `data.data_source`, Tool 2 `data.state_a.data_source`, Tool 2 `data.state_b.data_source`)
2. As a `cde_summary.cde_fragment.rename_documentation` top-level list entry
3. As the `bronze_condition_7` closure evidence record

**Rationale:** The rename is load-bearing — it closes Bronze staff-review Condition 7 (MCP half), and it is the one place where the MCP wire name diverges from the Gold column name. If a future contract-diff tool tries to correlate response fields back to Gold columns by name equality, the rename will look like a missing column. Documenting it in three places (field-local, cross-field summary, and governance-condition closure) makes it impossible to miss regardless of where the diff tool starts. The rename is also flagged in the data dictionary via a `rename_note` key on each of the three affected columns.

### 4. `difference_pct` left explicitly non-CDE

**Decision:** Do NOT flag `compare_purchasing_power.data.difference_pct` as CDE, despite it being a directly-displayed tool output.

**Rationale:** Per the CDE tagging artifact's explicit decision (`governance/cde-tagging/mcp-bea-rpp.md` §Decision Notes on Derived Fields), `difference_pct` is a pure scalar function of `difference` and `state_a.adjusted_salary`, both already CDE. The CDE principle is that derived-from-CDE scalars do not require independent flagging unless they themselves drive a distinct decision. The decision input here is `difference` (the dollar figure); `difference_pct` is presentation. I preserved this decision verbatim in the contract and in the data dictionary, and added the rationale to both so a future reviewer can trace the choice back to its source. If downstream product evolution makes `difference_pct` the primary answer (e.g., a comparison-ranking screen keyed on percentage), this decision should be revisited.

### 5. `adjusted_examples` counted as a single struct field, not 4 leaves

**Decision:** In Tool 1, `adjusted_examples` is a single entry with one `is_cde: true` flag — the four adjusted_Nk leaves are documented as the struct's `derived_from` list but NOT flagged independently.

**Rationale:** Matches the counting convention established in the CDE tagging artifact (`§Response-field counting convention`) — the struct bundles the four Gold columns behind one wire name, and a consumer parsing the wire sees one field. Counting the four leaves independently would inflate Tool 1's response-field count from 14 to 17 and break the parity with the CDE tagging artifact's summary. The struct-level CDE flag covers all four leaves collectively, and the `derived_from` list captures the mapping back to Gold columns for lineage tooling.

Contrast: in Tool 2, `state_a` and `state_b` are each counted as 6 flattened leaves because each leaf exists independently on the wire and needs its own CDE flag.

### 6. `data.salary` echo flagged as MCP-origin CDE

**Decision:** Flag the echoed user-input `salary` as CDE in Tool 2.

**Rationale:** Echoed user inputs are usually not CDE-worthy — they are pass-through data with no governance impact. But this echo is load-bearing: Gemma's narrative quotes the echoed value ("at $65,000, California equals...") and the two `adjusted_salary` figures in the same response are derived from it. A wrong echo would desynchronize the narrative from the derivation, which is a decision-affecting error at the wire level. This matches the CDE tagging artifact's Tool 2 field 1 flag and the CDE principle that student-facing financial figures in wire contracts are decision inputs. Explicitly NOT PII — the user-supplied anchor arrives at the MCP tier disconnected from subject identity; the tool does not persist, log, or correlate it.

### 7. 16 MCP-BEA interface rules referenced by ID, not embedded

**Decision:** Reference the 16 rules in `governance/dq-rules/mcp-bea-rpp.json` by ID only; do not embed the full rule bodies in the contract.

**Rationale:** The contract lists all 16 rule IDs under `quality.mcp_rule_ids` and assigns priority counts (14 P0, 2 P1). The rules themselves live in the DQ rule file where they can be updated independently. This matches the Gold contract's handling of GLD-RPP-* rules — reference by ID, never embed. The contract also cross-references individual rules on affected response fields (e.g., `dq_rules: [MCP-BEA-001, MCP-BEA-003, MCP-BEA-007, MCP-BEA-008]` on `data.data_source`) so lineage tooling can trace which rules apply to which fields. Every rule ID in the file is now referenced at least once (zero orphans).

### 8. No MCP-zone SQL DQ rules — explicitly noted

**Decision:** Document explicitly that there are no MCP-zone SQL DQ rules executed by `python -m brightsmith.infra.dq_runner`.

**Rationale:** MCP tools are not Iceberg tables — they are Python tool handlers. The 16 MCP-BEA rules are structural invariants of the wire contract verified at two places: (1) the 65-case eval set executed against the live `FutureProofMCPServer`; (2) the 70-function pytest suite (42 tests for Tool 1 + 28 tests for Tool 2). The contract's `quality` section notes this split explicitly and points to the eval set + pytest paths. Data-quality of the underlying Gold table is covered by the 55 Gold rules, which the MCP contract references via `quality.backing_table_dq_rules`.

### 9. Business term references limited to BT-098..BT-107

**Decision:** Reference exactly the 10 business terms that appear in the parent Gold contract and that map to response fields: BT-098 through BT-107. Do not reference any BT ID outside this range.

**Rationale:** The hard constraint in the task was "no phantom BT IDs — reference only BT-098..BT-107 which are confirmed present." I verified via `grep` on `governance/business-glossary.json` that all 10 terms are present and approved/auto-approved, then referenced each on its matching response field and in the contract's top-level `business_terms_referenced` list. No BT IDs outside this range appear anywhere in the contract or in the data dictionary entries.

---

## Verification Checks Performed

### 1. YAML parses cleanly

```
$ uv run python -c "import yaml; d=yaml.safe_load(open('governance/data-contracts/mcp-bea-rpp.yaml')); ..."
OK
tools: 2
tool1 fields: 14
tool2 fields: 19
total cde: 24
mcp rules: 16
bt_count: 10
quality_tier starts with: partial_verification — in
```

### 2. JSON parses cleanly and field counts match the CDE tagging artifact

```
$ python3 -c "import json; d=json.load(open('governance/data-dictionary.json')); ..."
JSON OK
tool1 fields: 14
tool2 fields: 19
tool1 cde: 10
tool2 cde: 14
tool1 pii: 0
tool2 pii: 0
tool1 missing derived_from: []
tool2 missing derived_from: []
total dict tables: 30
```

Counts match the CDE tagging artifact's summary table exactly:

| Metric | CDE artifact | Contract | Dictionary | Match? |
|---|---|---|---|---|
| Tool 1 response fields | 14 | 14 | 14 | yes |
| Tool 1 CDE flags | 10 | 10 | 10 | yes |
| Tool 1 PII flags | 0 | 0 | 0 | yes |
| Tool 2 response fields | 19 | 19 | 19 | yes |
| Tool 2 CDE flags | 14 | 14 | 14 | yes |
| Tool 2 PII flags | 0 | 0 | 0 | yes |
| Combined CDE flags | 24 | 24 | 24 | yes |
| Combined PII flags | 0 | 0 | 0 | yes |

### 3. Quality tier matches Gold exactly

Gold contract `quality_tier` value starts with `partial_verification — carried forward from Silver and Bronze...`. MCP contract `quality_tier` value starts with `partial_verification — inherited verbatim from Gold...`. Both tools pin `governance.quality_tier == 'partial_verification'` on every response via MCP-BEA-002. Match confirmed.

### 4. All 16 MCP-BEA rules referenced (zero orphans)

Rule IDs in `governance/dq-rules/mcp-bea-rpp.json`:
```
MCP-BEA-001, MCP-BEA-002, MCP-BEA-003, MCP-BEA-004,
MCP-BEA-005, MCP-BEA-006, MCP-BEA-007, MCP-BEA-008,
MCP-BEA-009, MCP-BEA-010, MCP-BEA-011, MCP-BEA-012,
MCP-BEA-013, MCP-BEA-014, MCP-BEA-015, MCP-BEA-016
```

All 16 appear in the contract's `quality.mcp_rule_ids` list. Rules MCP-BEA-001 through MCP-BEA-013 additionally appear on individual field `dq_rules` lists in the data dictionary. Rules MCP-BEA-014 (ratio invariance), MCP-BEA-015 (eval set size), and MCP-BEA-016 (eval set category coverage) are referenced at the tool level (MCP-BEA-014 is also referenced on `data.adjusted_examples`). No orphans.

### 5. Eval set exists with correct case count

```
$ wc -l data/ai_ready/eval/mcp-bea-rpp-eval.jsonl
      65 data/ai_ready/eval/mcp-bea-rpp-eval.jsonl
```

65 cases, exceeds the 50-case minimum required by MCP-BEA-015. Referenced in the contract as `quality.eval_set` with `eval_cases: 65`.

### 6. BT-098..BT-107 all present in business glossary

Verified via grep that all 10 term IDs are present in `governance/business-glossary.json` with approval status `approved` or `auto-approved`. No BT ID outside this range is referenced anywhere in the produced artifacts. No phantom BT IDs.

### 7. Every field has a `derived_from` pointer

Both tools in the data dictionary have zero fields missing `derived_from`. Fields that pass through a Gold column point to the column name; fields that are framework envelope point to `"MCP framework (BaseMCPServer...)"`; derived fields point to a list of source fields.

### 8. data_source rename documented in 3 places

- `mcp-bea-rpp.yaml` field-local `rename_note` on Tool 1 `data.data_source`
- `mcp-bea-rpp.yaml` field-local `rename_note` on Tool 2 `data.state_a.data_source`
- `mcp-bea-rpp.yaml` field-local `rename_note` on Tool 2 `data.state_b.data_source`
- `mcp-bea-rpp.yaml` top-level `cde_summary.cde_fragment.rename_documentation` list
- `mcp-bea-rpp.yaml` top-level `bronze_condition_7` closure record
- `data-dictionary.json` `mcp.get_regional_price_parity.columns.data.data_source.rename_note`
- `data-dictionary.json` `mcp.compare_purchasing_power.columns.data.state_a.data_source.rename_note`
- `data-dictionary.json` `mcp.compare_purchasing_power.columns.data.state_b.data_source.rename_note`

Impossible to miss regardless of which tool starts the diff.

---

## Conflicts Encountered

**None.** The CDE tagging artifact, the Gold contract, the DQ rule file, the eval set, the business glossary, and the MCP server code are all internally consistent. Every carry-forward from Gold matched the parent contract verbatim; every new MCP-origin CDE flag had explicit justification in the CDE tagging artifact; the rename mandate was identical across the spec, CDE tagging, and DQ rule files. No interpretation calls were required beyond the ones documented above in Key Decisions.

## Bronze Condition 7 — Closure Status

| Layer | Status | Evidence |
|---|---|---|
| Bronze | Declared | `governance/approvals/raw-ingest-bea-rpp-staff-review.md` |
| Silver | `verification_status` column introduced (Condition 6) | `governance/data-contracts/silver-base-bea-rpp.yaml` |
| Gold | Forward-only obligation to MCP declared | `governance/data-contracts/consumable-regional-price-parities.yaml` §staff_review_conditions.condition_7_carry_forward_to_mcp |
| MCP | **CLOSED** by this contract | `governance/data-contracts/mcp-bea-rpp.yaml` §bronze_condition_7 |

The full Bronze → Silver → Gold → MCP chain is now closed for Condition 7. No further forward-only obligations exist for this condition.

## Status Progression

- **2026-04-11:** Contract created at status `draft`. Data dictionary updated. Audit trail written.
- **Pending:** @staff-engineer sign-off to flip contract status to `active`.

---

## Handoff

- **To @governance-reviewer:** The contract is ready for post-implementation review. All CDE / PII / DQ / business-term cross-references are complete and zero orphans verified. The `bronze_condition_7` section provides the explicit closure record the reviewer needs to discharge the forward-only obligation inherited from the Gold contract.
- **To @staff-engineer:** The contract is status `draft` pending final sign-off. Flip to `active` after approval and log the transition in `governance/audit-trail/`.

*— End of audit trail —*
