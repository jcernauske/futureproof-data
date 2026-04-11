# Lineage Tracker Audit — mcp-bea-rpp

**Date:** 2026-04-11
**Agent:** @lineage-tracker
**Spec:** docs/specs/mcp-bea-rpp.md
**MCP Server:** src/mcp_server/futureproof_server.py (`FutureProofMCPServer`)
**State Normalizer:** src/mcp_server/_state_input.py (`normalize_state_input`, `FIPS_TO_STATE_NAME`)
**Contract YAML:** governance/data-contracts/consumable-regional-price-parities.yaml
**Lineage Artifact:** governance/lineage/mcp-bea-rpp-20260411.json

---

## Scope

MCP zone (Zone 5) tool-registration lineage for the two BEA RPP tools added to `FutureProofMCPServer`:

1. `get_regional_price_parity` — point-lookup tool, single state -> single response
2. `compare_purchasing_power` — two-state comparison tool, two rows + per-request derivations

Both tools are read-only layers over `consumable.regional_price_parities` (Gold, 51 rows, 15 columns). Neither tool writes data; neither materializes new columns. Lineage is tool-registration-level per the Brightsmith MCP convention — inputs are Gold tables + in-code support modules + contract YAML; outputs are tool response schemas with column-level field provenance.

One OpenLineage file contains **two** `COMPLETE` events — one per tool — matching the pattern set by `mcp-ai-exposure-20260409T230000Z.json` and keeping each tool's schema/lineage independently reviewable.

## Inputs Captured

Shared across both tools:

1. **brightsmith / consumable.regional_price_parities** — the 15-column Gold source table. For tool 1, 13 columns are read (record_id and promoted_at excluded). For tool 2, the same 13 columns are physically read via `_fetch_rpp_row` (which shares `RPP_QUERY_FIELDS`) but only 6 per-side fields are surfaced; the other 7 are documented as `excludedFields` on the tool 2 output.

2. **brightsmith / mcp._state_input** — the in-code state normalization module. Modeled as a named input (matching the precedent of `silver._us_state_reference` in the Silver lineage and `gold._cost_tier` in the Gold lineage) so `data.state_fips` on tool 1 has a traceable non-Gold provenance for the normalization step. Exposes `normalize_state_input` and `FIPS_TO_STATE_NAME`.

3. **brightsmith / governance.data_contracts.consumable_regional_price_parities** — the top-level contract YAML read by `FutureProofMCPServer.attach_governance` to inject `governance.quality_tier` and `governance.owner`. Modeled as a named input so those two response fields have traceable provenance. Cached on the server instance, so tool 2's read is a cache hit.

Tool 2 only:

4. **brightsmith / mcp._tool_input.salary** — the user-supplied salary argument. Modeled as a named input with a single `salary` field so that `data.salary`, `data.state_{a,b}.adjusted_salary`, `data.difference`, and `data.difference_pct` have traceable non-Gold provenance. This is a request-scoped value, not a persistent dataset, but modeling it explicitly keeps the derivation lineage honest: those five output fields are NOT sourced from Gold alone.

## Jobs

Two jobs, one per tool, both in the `brightsmith` namespace:

- **`mcp.register-get-regional-price-parity`** (runId `b3e8d4c1-5a29-4f07-8d6b-9f1c3a7e2d48`)
- **`mcp.register-compare-purchasing-power`** (runId `c4f9e5d2-6b3a-4018-9e7c-0a2d4b8f3e59`)

Both jobs' `sourceCodeLocation` is `src/mcp_server/futureproof_server.py`. Naming follows the precedent set by `mcp.register-get-ai-exposure` in the existing `mcp-ai-exposure` lineage file.

## Outputs Captured

- **brightsmith / mcp.get_regional_price_parity** — 14 output fields (10 data + 1 row_count + 3 governance), each with column-level lineage.
- **brightsmith / mcp.compare_purchasing_power** — 19 output fields (1 salary + 6*2 per-side + 2 derived top-level + 1 row_count + 3 governance), each with column-level lineage.

## Column Mapping Summary — Tool 1: `get_regional_price_parity`

| Response Field | Type | Source | Notes |
|---|---|---|---|
| data.state_name | DIRECT | consumable.regional_price_parities.state_name | passthrough |
| data.state_abbr | DIRECT | consumable.regional_price_parities.state_abbr | passthrough |
| data.state_fips | DIRECT | consumable.regional_price_parities.state_fips + mcp._state_input.normalize_state_input | lookup key + passthrough |
| data.census_region | DIRECT | consumable.regional_price_parities.census_region | passthrough |
| data.rpp_all_items | DIRECT | consumable.regional_price_parities.rpp_all_items | passthrough |
| data.purchasing_power_multiplier | DIRECT | consumable.regional_price_parities.purchasing_power_multiplier | full-precision passthrough |
| data.cost_tier | DIRECT | consumable.regional_price_parities.cost_tier | passthrough (already derived at Gold) |
| data.adjusted_examples | DIRECT (BUNDLED) | consumable.regional_price_parities.{adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k} | struct-reshape with short keys, no value mutation |
| data.data_source | DIRECT (RENAMED) | consumable.regional_price_parities.verification_status | **Bronze Condition 7** wire-level rename |
| data.data_year | DIRECT | consumable.regional_price_parities.data_year | passthrough |
| row_count | DERIVED (framework) | — | always 1 on success |
| governance.table | DERIVED (framework) | governance.data_contracts.consumable_regional_price_parities.table | contract-sourced |
| governance.quality_tier | DERIVED (framework) | governance.data_contracts.consumable_regional_price_parities.quality_tier | contract-sourced, token-extracted |
| governance.owner | DERIVED (framework) | governance.data_contracts.consumable_regional_price_parities.owner | contract-sourced |

Excluded Gold columns (tool 1): `record_id`, `promoted_at` — both pipeline metadata.

**Gold column coverage for tool 1: 13 of 15 columns read, 9 data response fields + struct (from 4 more) + 3 framework-injected governance fields.**

## Column Mapping Summary — Tool 2: `compare_purchasing_power`

| Response Field | Type | Source | Notes |
|---|---|---|---|
| data.salary | DIRECT | mcp._tool_input.salary | echo of validated user input |
| data.state_a.state_name | DIRECT | consumable.regional_price_parities.state_name | passthrough (state_a row) |
| data.state_a.state_abbr | DIRECT | consumable.regional_price_parities.state_abbr | passthrough (state_a row) |
| data.state_a.adjusted_salary | **DERIVED** | mcp._tool_input.salary + consumable.regional_price_parities.purchasing_power_multiplier | `round(salary * ppm_a, 2)` banker's rounding |
| data.state_a.cost_tier | DIRECT | consumable.regional_price_parities.cost_tier | passthrough (state_a row) |
| data.state_a.purchasing_power_multiplier | DIRECT | consumable.regional_price_parities.purchasing_power_multiplier | full-precision passthrough (state_a row) |
| data.state_a.data_source | DIRECT (RENAMED) | consumable.regional_price_parities.verification_status | **Bronze Condition 7** rename (state_a row) |
| data.state_b.* | same as state_a.* | (state_b row) | mirror |
| data.difference | **DERIVED** | mcp._tool_input.salary + consumable.regional_price_parities.purchasing_power_multiplier (both rows) | `round(state_b.adjusted_salary - state_a.adjusted_salary, 2)` |
| data.difference_pct | **DERIVED** | mcp._tool_input.salary + consumable.regional_price_parities.purchasing_power_multiplier (both rows) | `round(difference / state_a.adjusted_salary * 100, 2)` with div-by-zero guard |
| row_count | DERIVED (framework) | — | always 2 on success |
| governance.{table, quality_tier, owner} | DERIVED (framework) | governance.data_contracts.consumable_regional_price_parities.{table, quality_tier, owner} | contract-sourced |

Excluded Gold columns (tool 2): `record_id`, `promoted_at`, `state_fips`, `census_region`, `rpp_all_items`, `data_year`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k` — all documented in `excludedFields` with per-field rationale. Note the four `adjusted_Nk` columns are PHYSICALLY READ by `_fetch_rpp_row` (which shares `RPP_QUERY_FIELDS` with tool 1) but NOT USED by tool 2 — the `adjusted_salary` derivation is per-request from the user-supplied salary, not a lookup into the four frozen anchors.

## Bronze Condition 7 (Wire-Level Carry-Forward)

**Documented at the wire level on BOTH tools.** The `verification_status` column from Gold is renamed to `data_source` on every success response path:

- Tool 1: `data.data_source` ← `consumable.regional_price_parities.verification_status`
- Tool 2 side a: `data.state_a.data_source` ← `consumable.regional_price_parities.verification_status`
- Tool 2 side b: `data.state_b.data_source` ← `consumable.regional_price_parities.verification_status`

Value content is unchanged through the rename — `'bea_official'` remains `'bea_official'`, `'estimate'` remains `'estimate'`. The rename is purely Gemma-facing clarity (`data_source` reads better than `verification_status` for an LLM consumer). Both tools also honor the `verified_only=true` strict-mode branch that refuses rows where `verification_status='estimate'` and returns a structured null response with a clear message.

The rename is captured explicitly in each column's `transformationDescription` and cross-referenced to Bronze staff-review Condition 7 so a future governance reviewer can trace the wire-level implementation back to its Bronze origin without a code dive. The `transformationType` is marked `DIRECT` (not `DERIVED`) because the value content is unchanged — only the field name differs.

## Decisions and Rationale

1. **Two events, not one combined.** Matches the `mcp-ai-exposure-20260409T230000Z.json` precedent of one event per tool and keeps each tool's column lineage independently reviewable. A combined event would conflate the two tools' `excludedFields` and make tool 2's "reads but doesn't use" distinction harder to surface.

2. **`mcp._state_input` modeled as a named input dataset.** Parallels `silver._us_state_reference` in the Silver lineage and `gold._cost_tier` in the Gold lineage. Makes `data.state_fips` on tool 1 a traceable concept — the lookup-key normalization step is a first-class lineage node rather than opaque in-handler code. The normalizer is pure, unit-testable, and critical to the tool's correctness for the three input forms (abbr/name/FIPS), so surfacing it as a named input is the right abstraction.

3. **`governance.data_contracts.consumable_regional_price_parities` modeled as a named input.** The three governance response fields (`table`, `quality_tier`, `owner`) come from the project-local contract YAML, not from the Gold table or the Brightsmith framework defaults. Without this input node, those fields would have empty `inputFields` arrays, which would misrepresent their provenance. The node's schema enumerates exactly the three fields consumed — nothing more.

4. **`mcp._tool_input.salary` modeled as a named input on tool 2.** Tool 2 has five output fields whose lineage cannot be explained by Gold alone: `data.salary`, `data.state_a.adjusted_salary`, `data.state_b.adjusted_salary`, `data.difference`, `data.difference_pct`. Each of these depends on the user-supplied salary. Modeling the salary as a named input lets the column lineage cite it explicitly, keeping the derivation honest. This is the key structural difference from tool 1, which has no per-request derivations.

5. **`adjusted_examples` is marked DIRECT, not DERIVED.** The transformation is pure struct-reshaping with short key renames — no value content is changed, no arithmetic is performed, no rounding is applied. The four Gold values are copied verbatim into a new parent struct. Marking it DERIVED would misrepresent the transformation as something more than a rename. The fact that four source fields collapse into one target field is captured by having four entries in `inputFields`.

6. **`data_source` rename is marked DIRECT, not DERIVED.** Same reasoning — the value is unchanged, only the field name differs. Marking it DERIVED would hide the fact that Bronze Condition 7 is a pure carry-forward with a cosmetic rename, not a value transformation. The `transformationDescription` calls out the rename explicitly and cross-references Bronze Condition 7.

7. **Tool 2's `adjusted_salary` is marked DERIVED.** Unlike the Gold `adjusted_Nk` columns, which are pre-computed at frozen anchors and carried forward verbatim, tool 2's `adjusted_salary` is computed per-request from the user-supplied salary. The `transformationDescription` explicitly notes this is NOT sourced from the Gold `adjusted_Nk` columns — it is a fresh derivation. This matters because a reviewer might otherwise assume tool 2 uses the pre-computed anchors. The four Gold `adjusted_Nk` columns appear in tool 2's `excludedFields` with an explicit "read by shared _fetch_rpp_row but not used" rationale.

8. **`difference` and `difference_pct` cite BOTH `salary` AND `purchasing_power_multiplier` as inputs.** Both derivations ultimately depend on both the user input and both states' Gold multipliers (via the intermediate per-side `adjusted_salary` values). Citing only `salary` would hide the Gold dependency; citing only `purchasing_power_multiplier` would hide the user-input dependency. Both are required for the derivations to be reproducible.

9. **Banker's rounding documented on every DERIVED field.** `adjusted_salary`, `difference`, and `difference_pct` all use Python's built-in `round()`, which implements IEEE 754 round-half-to-even. This matches DuckDB's default `ROUND()` and the Gold transformer's rounding mode, which is load-bearing because the DQ engine enforces `abs(adjusted_Nk - round(N*1000*multiplier, 2)) <= 0.01` on both sides of the engine boundary at Gold. At the MCP layer the rounding mode is equally load-bearing because callers can cross-check `adjusted_salary` against Gold's `adjusted_Nk` at anchor salaries and expect byte-equal results.

10. **State-specific fetched-row semantics in `columnLineage.inputFields`.** OpenLineage column lineage doesn't natively distinguish "the state_a row's state_name" from "the state_b row's state_name" — both trace back to the same Gold column `state_name`. The distinction is captured in the `transformationDescription` ("from the row fetched for state_a's normalized FIPS" vs. "for state_b"). This is the conventional encoding for multi-row tool responses and matches how the framework's base patterns handle repeated point-lookups.

11. **`state_fips` is DIRECT on tool 1 but EXCLUDED on tool 2.** On tool 1 the FIPS value is part of the Gemma-facing payload (so callers can cross-reference the 2-digit code). On tool 2 the compact per-side payload intentionally omits `state_fips` to reduce token footprint; state identity is carried by `state_name` and `state_abbr`. This is a deliberate design choice documented in the spec's example payloads and surfaced in the `excludedFields` rationale.

12. **`excludedFields` is exhaustive on tool 2.** Every Gold column read by `_fetch_rpp_row` but not surfaced in the compact per-side payload gets an explicit `excludedFields` entry with a rationale. This prevents a future reviewer from assuming the omissions were oversights. In particular, the four `adjusted_Nk` exclusions carry the load-bearing note that the per-request derivation intentionally replaces the pre-computed anchors.

13. **Run IDs are UUID v4.** `b3e8d4c1-5a29-4f07-8d6b-9f1c3a7e2d48` for tool 1, `c4f9e5d2-6b3a-4018-9e7c-0a2d4b8f3e59` for tool 2. Distinct so the two events are independently addressable.

## Naming Conventions Applied

- Jobs: `mcp.register-get-regional-price-parity` and `mcp.register-compare-purchasing-power` (zone-dot-verb-subject, matching `mcp.register-get-ai-exposure` precedent; the MCP "verb" is `register` because tool registration is the unit of work for this zone).
- Output datasets: `mcp.get_regional_price_parity` and `mcp.compare_purchasing_power` (zone.tool_name, matching `mcp.get_ai_exposure` precedent — underscores preserved to match the literal MCP tool names registered on the server).
- Input datasets: `consumable.regional_price_parities` (Gold table, matches Gold lineage); `mcp._state_input`, `mcp._tool_input.salary`, `governance.data_contracts.consumable_regional_price_parities` (underscore-prefixed where modeling an in-code module, matching `silver._us_state_reference` and `gold._cost_tier` precedents).
- Run IDs: UUID v4.

## Completeness Check

- [x] Both tools have a dedicated OpenLineage `COMPLETE` event.
- [x] Every user-visible response field on tool 1 (9 data + row_count + 3 governance = 13 named fields; `adjusted_examples` is counted once as a BUNDLED struct) has a `columnLineage.fields` entry.
- [x] Every user-visible response field on tool 2 (1 salary + 12 per-side [6*2] + 2 derived + row_count + 3 governance = 19 named fields) has a `columnLineage.fields` entry.
- [x] All DIRECT passthroughs cite a single Gold source column.
- [x] All BUNDLED fields (tool 1's `adjusted_examples`) cite all four source columns explicitly.
- [x] All RENAMED fields (`data_source`, `data.state_a.data_source`, `data.state_b.data_source`) cite `verification_status` with a `transformationDescription` that calls out Bronze Condition 7 at the wire level.
- [x] All DERIVED fields (tool 2's `adjusted_salary`, `difference`, `difference_pct`) cite both Gold and user-input sources, and document banker's rounding.
- [x] All FRAMEWORK-INJECTED governance fields cite the contract YAML as a named input.
- [x] `excludedFields` is present on both output datasets with per-field rationales.
- [x] Agent attribution is present on both events and cites the spec, Bronze Condition 7 wire-level rename, banker's rounding for tool 2 derivations, and the "reads but doesn't use" semantics for tool 2's `adjusted_Nk` columns.
- [x] Spec reference facet on both events points to `docs/specs/mcp-bea-rpp.md`.
- [x] Source-code location on both jobs points to `src/mcp_server/futureproof_server.py`.
- [x] State normalization module points to `src/mcp_server/_state_input.py`.
- [x] Contract YAML input points to `governance/data-contracts/consumable-regional-price-parities.yaml`.

## Deliverables

- `governance/lineage/mcp-bea-rpp-20260411.json` (2 events: tool 1 with 14 column-lineage entries and 2 excludedFields; tool 2 with 19 column-lineage entries and 10 excludedFields)
- `governance/audit-trail/2026-04-11-lineage-tracker-mcp-bea-rpp.md` (this file)

## Ambiguities / Followups

None. The MCP tool layer is a thin read-only passthrough with exactly one derivation site (tool 2's per-request `adjusted_salary` / `difference` / `difference_pct`), which is fully captured by modeling the user-supplied salary as a named input. The Bronze Condition 7 wire-level rename is documented explicitly on all three response paths (`data_source` on tool 1, `data.state_a.data_source` and `data.state_b.data_source` on tool 2). No interpretation was required beyond the deliberate framing choices documented in the Decisions section.
