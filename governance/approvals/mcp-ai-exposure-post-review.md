## Governance Review: mcp-ai-exposure
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** APPROVED

### Checklist Results

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Lineage event exists | PASS | `governance/lineage/mcp-ai-exposure-20260409T230000Z.json` -- OpenLineage COMPLETE event with column-level lineage for all 7 response fields. Input: consumable.ai_exposure (9 fields). Output: mcp.get_ai_exposure (7 fields). 2 excluded fields (record_id, promoted_at) documented with rationale. |
| 2 | DQ rules exist | PASS | `governance/dq-rules/mcp-ai-exposure.json` -- 5 rules (4 P0, 1 P1) covering eval pass rate, tool liveness, null handling, response completeness, response time. |
| 3 | DQ execution against real data | PASS | `governance/dq-results/mcp-ai-exposure-20260410T003001Z.json` -- 5/5 rules passed. Executed via manual runner (MCP-layer rules require tool invocation, not SQL). |
| 4 | P0 gate | PASS | `p0_gate: "PASS"` in latest results. 0 P0 failures. |
| 5 | DQ scorecard from real execution | PASS | `governance/dq-scorecards/mcp-ai-exposure-scorecard.md` -- scorecard references actual execution results (62/62 eval cases, 5/5 null cases, 7/7 fields, 157ms max latency). |
| 6 | CDE/PII tags on data contract | PASS | `governance/data-contracts/mcp-ai-exposure.yaml` -- 5 CDEs tagged (soc_code, exposure_score, stat_res, boss_ai_score, rationale) with rationale. 0 PII fields. `contains_pii: false`. |
| 7 | Data dictionary entries | PASS | `governance/data-dictionary.json` has `mcp.get_ai_exposure` entry with all 7 columns documented, including type, description, is_cde, is_pii, nullable, source_column, dq_rules, and lineage references. |
| 8 | Data contract exists | PASS | `governance/data-contracts/mcp-ai-exposure.yaml` -- status: draft, version: 1.0.0. References backing table contract at `governance/data-contracts/consumable-ai-exposure.yaml`. |
| 9 | Audit trail entries | PASS | Two audit trail files: `governance/audit-trail/mcp-ai-exposure-2026-04-09.json` (agent decisions) and `governance/audit-trail/mcp-ai-exposure-dq-2026-04-09.json` (DQ execution log). |
| 10 | Schema matches spec | PASS | Tool exposes 7 fields matching spec definition: soc_code, occupation_title, exposure_score, stat_res, boss_ai_score, rationale, category. Input schema requires soc_code (string, XX-XXXX format). |
| 11 | Data models (Base/Consumable only) | N/A | MCP zone -- no 3-stage modeling required. |
| 12 | No orphaned artifacts | PASS | All governance artifacts reference `consumable.ai_exposure` (table exists) and `mcp.get_ai_exposure` (tool registered in `src/mcp_server/futureproof_server.py`). Field names are consistent across all artifacts. |
| 13 | Consistency across artifacts | PASS | Lineage, data contract, data dictionary, and DQ rules all reference the same 7 field names with consistent types. CDE flags are consistent between contract and dictionary (5 CDEs: soc_code, exposure_score, stat_res, boss_ai_score, rationale). |
| 14 | Contract verification | ADVISORY | `python3 -m brightsmith.infra.contract verify mcp-ai-exposure` returns "Cannot load table: Empty namespace identifier". This is an infrastructure limitation affecting ALL contracts in the project (none can load tables), not specific to this spec. The contract YAML is well-formed and complete. |
| 15 | Insight traceability | N/A | No insight reports reference the MCP AI exposure zone transition. The existing insight reports (`silver-to-gold-insights.md`, `silver-bls-ooh-to-gold-insights.md`) cover College Scorecard and BLS OOH pipelines respectively. |
| 16 | Pre-review advisories resolved | PASS | All 3 pre-review advisories addressed: (1) eval set produced with 62 cases exceeding 50-case minimum, (2) row count settled at 389 (consistent across all artifacts), (3) MCP server placed at `src/mcp_server/` to avoid import conflict with `mcp` package. |
| 17 | Tests exist | PASS | `tests/mcp/test_get_ai_exposure.py` -- 13 tests across 5 test classes (registration, valid lookup, null cases, query errors, query delegation). All passing. |
| 18 | Eval set exists | PASS | `data/ai_ready/eval/mcp-ai-exposure-eval.json` -- 62 cases across 5 categories (34 point_lookup, 8 comparison, 5 ranking, 7 aggregation, 8 edge_case). 100% pass rate. |

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Contract verification tool (`brightsmith.infra.contract verify`) fails with "Empty namespace identifier" for all contracts in the project. This is a framework infrastructure issue, not a spec-level governance gap. The contract YAML file is well-formed with all required fields. | No action required for this spec. Framework-level issue to track separately. |

### Decision Rationale

All post-implementation governance requirements are met. The MCP tool implementation at `src/mcp_server/futureproof_server.py` is a clean, read-only passthrough from `consumable.ai_exposure` with proper null handling and governance metadata attachment. The full artifact chain is present and internally consistent:

- **Lineage:** Column-level OpenLineage event documents all 7 response fields as DIRECT passthrough from Gold, with 2 excluded fields documented.
- **DQ:** 5 rules written, all 5 executed and passing (including 62/62 eval cases at 100% pass rate, well above the 80% threshold).
- **CDE/PII:** 5 CDEs tagged with rationale on the data contract. No PII (public BLS occupation data).
- **Data Dictionary:** Full entry for `mcp.get_ai_exposure` with all 7 columns documented.
- **Audit Trail:** Agent decisions and DQ execution both logged.
- **Tests:** 13 unit tests covering registration, valid lookups, null cases, error handling, and query delegation.

The single advisory (contract verification infrastructure) is non-blocking and affects the entire project, not this spec specifically.

**APPROVED.** This spec is complete. All zones (Raw through MCP) of the Karpathy AI Exposure pipeline have passed governance review.
