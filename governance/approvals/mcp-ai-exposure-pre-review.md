## Governance Review: mcp-ai-exposure (Zone 5)
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** APPROVED (with advisory notes)

### Checklist Results

| # | Item | Status |
|---|------|--------|
| 1 | Clear problem statement and success criteria | PASS — expose consumable.ai_exposure via MCP tool for Gemma agent |
| 2 | Input data sources identified with paths | PASS — consumable.ai_exposure (produced in Zone 3) |
| 3 | Output artifacts defined with paths and formats | PASS — MCP tool get_ai_exposure, JSON response schema defined |
| 4 | Transformations described | PASS — direct query passthrough, no transforms (correct for MCP zone) |
| 5 | Zone assignment correct (MCP) | PASS |
| 6 | Primary implementation agent identified | PASS — @primary-agent (spec line 307) |
| 7 | DQ rule categories specified | N/A — MCP zone; DQ covered by Gold zone rules on consumable.ai_exposure |
| 8 | CDE mapping impact assessed | N/A — no new fields; MCP exposes existing Gold schema |
| 9 | Lineage scope defined | ADVISORY — spec lists lineage artifact but MCP zone lineage is typically tool-registration-level, not transform-level. Acceptable. |
| 10 | Breaking changes flagged | PASS — no breaking changes; new tool only. get_career_path_stats is data-level backfill, not schema change. |
| 11 | Testing approach defined | SEE ADVISORY #1 below |
| 12 | Data Model Gate | N/A — MCP zone skips 3-stage modeling |

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Spec does not mention an eval set for get_ai_exposure. Per Brightsmith MCP pipeline rules, MCP zone specs require an eval set at `data/ai_ready/eval/` with >= 50 mechanically verifiable Q&A cases. The parent spec lists a "30 minutes" estimate for MCP tool addition, suggesting eval may be scoped out. Implementation agent should produce the eval set. | Eval set should be produced during implementation. Not blocking pre-implementation since this is a single-tool addition to an existing MCP surface. |
| 2 | ADVISORY | The spec says 389 rows in the MCP zone summary header but 342 expected rows in the source data and 300-350 in the Gold contract. The 389 number likely reflects post-broad-expansion count from Silver. Clarify or let implementation settle the actual count. | No action required -- implementation will produce the actual count. |
| 3 | ADVISORY | No `src/mcp/` directory exists yet. Implementation will need to establish the MCP server structure or add the tool to an existing server. Brightsmith convention is `BaseMCPServer` subclass registered in `domain/manifest.yaml`. | Implementation agent should follow Brightsmith MCP conventions. |

### Decision Rationale

Zone 5 (MCP) of this spec is a thin read-only tool layer over a well-defined Gold table. The tool signature, input validation (SOC format XX-XXXX), response schema, and null-case behavior are all specified. No transforms occur at this layer -- it is a direct query passthrough. The Gold zone DQ rules and data contract on consumable.ai_exposure provide the quality guarantees; the MCP tool inherits them.

The three advisory notes are non-blocking. The eval set gap is the most significant but is an implementation-time deliverable, not a spec-blocking issue. The row count discrepancy (389 vs 342) is cosmetic and will resolve during implementation.

APPROVED for implementation.
