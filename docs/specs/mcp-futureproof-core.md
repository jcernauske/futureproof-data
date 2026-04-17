# Spec: mcp-futureproof-core

**Status:** COMPLETE
**Zone:** MCP
**Primary Agent:** @primary-agent (mcp-engineer)
**Created:** 2026-04-11

---

## Problem Statement

Register the remaining 5 MCP tools that expose FutureProof's core Gold data products to the Gemma agent. The MCP server currently has 3 tools (`get_ai_exposure`, `get_regional_price_parity`, `compare_purchasing_power`). The 5 tools in this spec complete the Gemma function-calling surface defined in the charter and hackathon PRD.

Without these tools, Gemma cannot execute its primary workflow: student selects school + major → Gemma calls data retrieval tools → Gemma synthesizes career analysis. The entire agent loop is blocked.

## What Ships

5 new tools registered on `FutureProofMCPServer`, all following the established pattern: query Gold Iceberg table → return results with governance metadata via `enrich_response()` / `attach_governance()`.

| # | Tool | Gold Table | Input | Returns |
|---|------|-----------|-------|---------|
| 1 | `get_school_programs(school_name)` | `consumable.career_outcomes` | School name (fuzzy) or unitid | All programs at that school with earnings, debt, ROI, confidence tier |
| 2 | `get_career_paths(unitid, cipcode)` | `consumable.program_career_paths` | unitid + cipcode | All career outcomes for that school+major with 5-stat pentagon + boss scores |
| 3 | `get_occupation_data(soc_code)` | `consumable.occupation_profiles` | SOC code | BLS occupation data: wage, growth, education, employment |
| 4 | `get_task_breakdown(soc_code)` | `consumable.onet_work_profiles` | SOC code | O*NET task data: work activities, human-edge activities, burnout drivers |
| 5 | `get_career_branches(soc_code)` | `consumable.career_branches` | SOC code | Stage 3 branching paths with stat deltas for each target occupation |

After this spec, the MCP server exposes **8 tools total** — the complete Gemma function-calling surface.

---

## Tool 1: `get_school_programs(school_name)`

**Purpose:** Student types a school name → Gemma retrieves all programs (majors) offered at that school with their outcome data. This powers Screen 2 (School + Major selection) and gives Gemma context for the entire session.

**Gold Table:** `consumable.career_outcomes`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "school_name": {
      "type": "string",
      "description": "Institution name to search for (e.g., 'Indiana State', 'Harvard', 'University of Michigan'). Performs case-insensitive substring match against institution_name. Can also accept a numeric unitid for exact lookup."
    },
    "min_confidence": {
      "type": "string",
      "description": "Minimum confidence_tier to include. One of: 'high', 'medium', 'low', 'insufficient'. Defaults to 'insufficient' (return all). Set to 'medium' or 'high' to filter out suppressed programs.",
      "default": "insufficient"
    }
  },
  "required": ["school_name"]
}
```

**Response Fields:**
```
unitid, institution_name, institution_control, cipcode, program_name,
cip_family_name, earnings_1yr_median, earnings_1yr_p25, earnings_1yr_p75,
debt_median, debt_to_earnings_annual, debt_to_earnings_tier,
program_value_index, confidence_tier, has_earnings, has_debt,
outcome_completeness
```

**Handler Logic:**
1. If `school_name` is numeric (all digits), treat as `unitid` exact match
2. Otherwise, case-insensitive `ILIKE '%{school_name}%'` against `institution_name`
3. Apply `min_confidence` filter (tier ordering: high > medium > low > insufficient)
4. Return up to 500 rows (safety limit — largest schools have ~142 programs)
5. Sort by `program_name ASC`
6. If zero results, return structured null with message "No programs found for '{school_name}'"
7. If multiple schools match (e.g., "Michigan" matches 3+ campuses), return all matches — let Gemma disambiguate with the student

**Edge Cases:**
- "University of Michigan" matches Ann Arbor, Dearborn, Flint — return all, Gemma asks which campus
- Numeric unitid lookup returns exactly one school's programs
- School exists but all programs are suppressed and `min_confidence='high'` → return structured null

---

## Tool 2: `get_career_paths(unitid, cipcode)`

**Purpose:** The core query. Student has selected a school and major → Gemma retrieves all career outcomes with the full pentagon and boss fight profile. This powers Screens 4-6 (Stage 2 Reveal, Boss Gauntlet, Branch Tree).

**Gold Table:** `consumable.program_career_paths`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "unitid": {
      "type": "integer",
      "description": "IPEDS institution identifier (6-digit, e.g., 151801 for Indiana State University). Get this from get_school_programs results."
    },
    "cipcode": {
      "type": "string",
      "description": "CIP program code in XX.XX format (e.g., '52.02' for Business Administration). Get this from get_school_programs results."
    }
  },
  "required": ["unitid", "cipcode"]
}
```

**Response Fields:**
```
unitid, institution_name, cipcode, program_name, cip_family_name,
soc_code, occupation_title, soc_major_group_name,
stat_ern, stat_roi, stat_res, stat_grw, stat_hmn,
boss_ai_score, boss_loans_score, boss_market_score, boss_burnout_score, boss_ceiling_score,
earnings_1yr_median, earnings_1yr_p25, earnings_1yr_p75,
debt_median, debt_to_earnings_annual,
median_annual_wage, growth_category, employment_current, education_level_name,
top_5_activities, top_human_activities, burnout_drivers,
match_quality, stats_available_count, bosses_available_count, overall_confidence
```

**Handler Logic:**
1. Query `consumable.program_career_paths` filtered by `unitid` AND `cipcode`
2. Return all matching rows (one per career outcome / SOC code)
3. Sort by `stats_available_count DESC, occupation_title ASC` (best-data careers first)
4. No row limit — a school+major combo typically produces 5-20 career paths
5. If zero results, return structured null with message "No career paths found for unitid={unitid}, cipcode='{cipcode}'. This program may not have crosswalk coverage."
6. Include `confidence_tier_program` from the Scorecard side so Gemma can caveat earnings data

**This is the tool that fires the entire product loop.** Gemma calls `get_school_programs` to find the unitid + cipcode, then calls `get_career_paths` to get the full pentagon and boss data for every career that school+major leads to.

---

## Tool 3: `get_occupation_data(soc_code)`

**Purpose:** Deep-dive on a specific occupation's BLS profile. Gemma calls this when generating detailed career descriptions ("What the job looks like today") or when a student taps a specific career in the results.

**Gold Table:** `consumable.occupation_profiles`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "soc_code": {
      "type": "string",
      "description": "Standard Occupational Classification code in XX-XXXX format (e.g., '13-2051' for Financial analysts). Get this from get_career_paths results."
    }
  },
  "required": ["soc_code"]
}
```

**Response Fields:**
```
soc_code, occupation_title, soc_major_group, soc_major_group_name,
median_annual_wage, wage_percentile_overall, wage_percentile_education_tier,
employment_current, employment_projected, employment_change_pct,
growth_category, grw_score, grw_score_rounded,
market_score, market_score_rounded,
education_level_name, education_level_code,
work_experience, training_typical,
broad_occupation_flag, catchall_flag,
median_wage_capped
```

**Handler Logic:**
1. Query `consumable.occupation_profiles` filtered by `soc_code`
2. Return single row (grain is one per SOC)
3. If not found, return structured null with message "No occupation data for SOC code '{soc_code}'"

---

## Tool 4: `get_task_breakdown(soc_code)`

**Purpose:** O*NET task-level data for "Which tasks AI is eating" and "What the human edge looks like." Gemma calls this when generating the per-career detail view and when computing Fight Burnout context.

**Gold Table:** `consumable.onet_work_profiles`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "soc_code": {
      "type": "string",
      "description": "Standard Occupational Classification code in XX-XXXX format (e.g., '13-2051'). Uses bls_soc_code field in the O*NET table."
    }
  },
  "required": ["soc_code"]
}
```

**Response Fields:**
```
bls_soc_code, occupation_title,
hmn_score, hmn_score_rounded,
burnout_score, burnout_score_rounded,
top_5_activities, top_human_activities,
activity_summary, context_summary,
burnout_drivers,
time_pressure, work_hours, consequence_of_error,
contact_with_others, deal_with_unpleasant
```

**Handler Logic:**
1. Query `consumable.onet_work_profiles` filtered by `bls_soc_code = soc_code`
2. Return single row
3. If not found, return structured null with message "No O*NET task data for SOC code '{soc_code}'"
4. Note: The JSON fields (`top_5_activities`, `top_human_activities`, `burnout_drivers`) are stored as strings in Gold — return them as-is, Gemma parses them

---

## Tool 5: `get_career_branches(soc_code)`

**Purpose:** Stage 3 branching paths. Given a career (SOC code), what are the related careers a person could transition to, and how do the stats shift? Powers Screen 6 (Branch Tree).

**Gold Table:** `consumable.career_branches`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "soc_code": {
      "type": "string",
      "description": "Source occupation SOC code in XX-XXXX format (e.g., '13-2051' for Financial analysts). Returns all branching career paths from this starting position."
    },
    "primary_only": {
      "type": "boolean",
      "description": "If true, return only primary branches (top 10 most related). Defaults to true.",
      "default": true
    }
  },
  "required": ["soc_code"]
}
```

**Response Fields:**
```
soc_code, source_title,
related_soc_code, related_title,
best_index, relatedness_tier, is_primary,
source_grw, source_hmn, source_burnout, source_wage,
related_grw, related_hmn, related_burnout, related_wage,
related_growth_category, related_education_level,
grw_delta, hmn_delta, burnout_delta, wage_delta,
stat_res (source), boss_ai_score (source),
stat_res_delta,
branch_has_full_data
```

**Handler Logic:**
1. Query `consumable.career_branches` filtered by `soc_code`
2. If `primary_only=true` (default), filter to `is_primary = true`
3. Sort by `best_index ASC` (most related first)
4. Return up to 20 rows (safety limit)
5. If zero results, return structured null with message "No career branches found for SOC code '{soc_code}'. This occupation may not have transition data in O*NET."

---

## Gemma Agent Workflow (Complete)

With all 8 tools live, Gemma's function-calling workflow for the core product loop is:

```
Student: "Indiana State University, Business Administration"

1. Gemma calls get_school_programs("Indiana State")
   → Returns 69 programs at ISU with earnings/debt data
   → Gemma identifies cipcode "52.02" for Business Administration

2. Gemma calls get_career_paths(151801, "52.02")
   → Returns ~8-15 career paths with full pentagon + boss scores
   → Financial Analyst (13-2051), Marketing Coordinator, Operations Manager, etc.

3. For each career, Gemma can optionally deep-dive:
   a. get_occupation_data("13-2051") → BLS salary, growth, education details
   b. get_task_breakdown("13-2051") → O*NET tasks, human edge, burnout profile
   c. get_ai_exposure("13-2051") → Karpathy score + rationale
   d. get_career_branches("13-2051") → Stage 3 branching paths

4. For salary context:
   get_regional_price_parity("IN") → Iowa purchasing power adjustment

5. For comparing two schools:
   compare_purchasing_power(48000, "IN", "CA") → ISU vs UCLA salary reality

6. Gemma synthesizes all retrieved data into:
   - Five-stat pentagon
   - Boss fight narratives
   - Branch tree with stat deltas
   - "What to do in school" playbook
   - Empowerment-framed guidance
```

---

## Implementation Notes

### Pattern to Follow

All 5 tools follow the same pattern established by `get_ai_exposure` and `get_regional_price_parity`:

1. Register `ToolDef` in `get_tools()` with name, description, input_schema, handler
2. Handler validates input, queries Gold Iceberg via `self.query_iceberg_simple()`, returns via `self.enrich_response()` on success or `self.attach_governance()` on null
3. Governance metadata auto-attached to all responses
4. Tests in `tests/mcp/test_{tool_name}.py`
5. Eval cases in `data/ai_ready/eval/mcp-{tool_name}-eval.jsonl`

### Input Validation

- SOC codes: strip whitespace, validate XX-XXXX format before querying
- `school_name`: strip whitespace, reject empty strings
- `unitid`: validate positive integer
- `cipcode`: validate XX.XX format

### Search Behavior for `get_school_programs`

This is the only tool with fuzzy matching. The others are all exact-key lookups. The fuzzy match uses `ILIKE` against `institution_name` — this is simple and sufficient for the hackathon. Post-hackathon, a dedicated search index (Elasticsearch, pg_trgm) would be more robust.

Multi-campus ambiguity (e.g., "University of Michigan" → Ann Arbor, Dearborn, Flint) is handled by returning all matches and letting Gemma disambiguate in conversation with the student.

---

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent (mcp-engineer) — Implement 5 tool handlers + tests + eval cases
3. @data-analyst — Verify eval cases against Gold tables
4. @dq-rule-writer — Interface contract rules for each tool
5. @dq-engineer — Execute rules
6. @lineage-tracker — OpenLineage events for tool registrations
7. @cde-tagger — CDE mapping for response fields
8. @doc-generator — MCP tool contract + data dictionary entries
9. @governance-reviewer — Post-implementation check
10. @staff-engineer — Final review

## Governance Artifacts

- [ ] Tests: `tests/mcp/test_get_school_programs.py`, `test_get_career_paths.py`, `test_get_occupation_data.py`, `test_get_task_breakdown.py`, `test_get_career_branches.py`
- [ ] Eval cases: `data/ai_ready/eval/mcp-core-eval.jsonl`
- [ ] DQ rules: `governance/dq-rules/mcp-futureproof-core.json`
- [ ] MCP tool contract: `governance/data-contracts/mcp-futureproof-core.yaml`
- [ ] Data dictionary entries for all response fields
- [ ] Lineage events
- [ ] Approval chain: pre-review → post-review → staff-engineer

## Estimated Effort

5 tools, all following established patterns. The only novel work is the fuzzy search logic for `get_school_programs`.

| Step | Estimate |
|------|----------|
| 5 tool handlers | 2-3 hours |
| Tests (5 files) | 2-3 hours |
| Eval cases | 1 hour |
| DQ rules + governance | 1-2 hours |
| **Total** | **~6-9 hours** |

---

## KNOWN BLOCKER: `/bs:serve` Manifest Loader

`/bs:serve` cannot start due to two Brightsmith framework issues:

1. **`domain_loader.py` KeyError on `table:`** — `domain/sources/onet.yaml` uses `tables:` (plural, multi-table source). The loader hard-requires singular `table:` and crashes with `KeyError: 'table'`.
2. **`_load_zone_registry()` shape mismatch** — expects flat `pipeline.silver.module` but `domain/manifest.yaml` uses nested list-of-steps with per-table entries (6 Silver transformers, 7 Gold transformers). The registry finds zero modules.

These are Brightsmith framework bugs, not FutureProof data issues. The manifest shape is correct for a multi-source domain — the loader hasn't been updated to support it.

### Hackathon Workaround

**Bypass `/bs:serve` entirely.** The MCP tool handlers in `src/mcp_server/futureproof_server.py` query Gold Iceberg tables directly via `query_iceberg_simple()`. They do not depend on the manifest loader or zone registry.

Create a lightweight startup script that instantiates `FutureProofMCPServer` directly:

```python
# scripts/serve_mcp.py
"""Hackathon MCP server launcher — bypasses /bs:serve manifest loader."""
from mcp_server.futureproof_server import FutureProofMCPServer

server = FutureProofMCPServer(
    project_root=".",
    warehouse_path="data/warehouse",
)
server.start()  # or server.run() depending on BaseMCPServer interface
```

This gives the Gemma agent the same tool interface — all 8 tools, governance metadata, Iceberg queries — without going through the broken manifest loader.

**The `@primary-agent` implementing this spec should:**
1. Build all 5 tool handlers in `futureproof_server.py` (same pattern as existing tools)
2. Write tests against the handlers directly (not through `/bs:serve`)
3. Create `scripts/serve_mcp.py` as the hackathon-mode launcher
4. Verify all 8 tools respond correctly via the launcher
5. Do NOT attempt to fix `domain_loader.py` or `manifest.yaml` — that's a post-hackathon Brightsmith framework fix

### Post-Hackathon Fix (Brightsmith Repo)

File two issues against `brightsmith`:
1. `domain_loader.py` should support `tables:` (plural) for multi-table sources like O*NET
2. `_load_zone_registry()` should support the nested list-of-steps pipeline shape that multi-source domains naturally produce

Once fixed, `/bs:serve` will work natively and `scripts/serve_mcp.py` can be retired.

---

## After This Spec

With all 8 MCP tools live (via `scripts/serve_mcp.py`), the data pipeline is **complete**. The next workstream is:

1. **Frontend** — React/Vite, Brightpath design system, all 8 screens
2. **Gemma agent integration** — wire function calling to MCP tools
3. **Ollama local deployment** — verify same codebase runs locally
4. **Video production**
5. **Submission package**

---

*— End of Spec —*
