# Feature: Chip Dispatch via Real Gemma Tool Calling Against the MCP Server

**Spec:** `docs/specs/feature-chip-dispatch-mcp-tool-calling.md`
**Status:** COMPLETE
**Date:** 2026-04-20
**Author:** Jeff Cernauske + Claude Code

---

## Summary

Replaced `handle_chip_dispatch`'s manual `_prefetch_career_paths` → string-interpolation pattern with a real Gemma → MCP tool-calling loop. This is row 0 of the Gemma tool-calling migration (the project's first real tool-calling integration).

Gemma now receives `get_career_paths` as a callable tool schema and decides whether/when to invoke it. The MCP server handles the query in-process. The multi-turn loop supports up to 3 turns with a hard 30-second wall-time ceiling enforced via `asyncio.wait_for`.

## What Changed

### `backend/app/services/gemma_client.py`
- Added `ToolCallTurn` dataclass for structured tool-call logging
- Added `generate_with_tools_loop()` — multi-turn Gemma tool-calling loop with:
  - `asyncio.wait_for` on both inference and dispatch calls (hard wall-time cap)
  - Semaphore acquired once per loop (not per turn)
  - Graceful handling of malformed tool calls, dispatch errors, transport errors
- Added `_one_tool_turn()` helper for single Gemma inference with tool schema

### `backend/app/services/mcp_client.py`
- Added `get_tool_openai_schema()` — returns OpenAI-compatible tool definition
- Added `_validate_args()` — schema validation with int/float coercion
- Added `_INTERNAL_PASSTHROUGH_KEYS` allowlist for `student_cip`, `intent_keywords`
- Added `call_async()` — async variant using `asyncio.to_thread`
- Added `McpArgumentError` exception class

### `backend/app/services/set_your_course.py`
- Rewrote `handle_chip_dispatch` to use `generate_with_tools_loop`
- Deleted `_prefetch_career_paths` and `_format_prefetch_block`
- Dispatch closure injects `student_cip` from request context (preserves CIP substitution)
- `tool_call_made` derived from tool_call_log (requires successful dispatch)
- `confirmed_focus` gated on `tool_call_made` (Gemma must actually call a tool)

### `backend/tests/services/test_set_your_course_chip_tool_loop.py` (new)
- 9 P0 tests covering: tool dispatch, no-tool-call path, loop cap, wall time cap, malformed tool call, dispatch error, confirmed_focus invariant, short-circuit paths

### `backend/tests/services/test_gemma_client.py`
- 5 new tests for `generate_with_tools_loop`: single-turn, two-turn, dispatch error, turn cap, transport error

### `docs/specs/feature-gemma-tool-calling-migration.md`
- Promoted from placeholder to real spec. Row 0 marked shipped. Key finding: pre-inject is genuinely better for rows 1-5.

## Code Review

**Reviewer:** @faang-staff-engineer
**Verdict:** CHANGES REQUIRED → All resolved

| Finding | Severity | Resolution |
|---------|----------|------------|
| S1: Wall-time cap not enforced mid-turn | Serious | Wrapped `_one_tool_turn` and `dispatch` in `asyncio.wait_for(timeout=remaining)` |
| M1: Ollama thinking-mode fragility | Moderate | TODO added to `_one_tool_turn` docstring |
| B1: `tool_choice` only set on turn 0 | Minor | Set `"auto"` unconditionally |
| B2: Unknown keys pass through validation | Minor | Allowlist: `_INTERNAL_PASSTHROUGH_KEYS` |

## Build Verification

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | 46 errors (all pre-existing) |
| pytest | 1100 passed, 5 failed (all pre-existing) |
| TypeScript | PASS |
| vitest | 588 passed |
| Vite build | PASS |

## Spike Results (Ollama)

- 20 chip-dispatch-shaped scenarios
- 90% success rate (18/20 valid tool calls)
- Avg latency: 26,803ms, P50: 24,367ms
- Gemma 4 on Ollama handles function calling via OpenAI-compat endpoint

## Key Design Decisions

1. **In-process dispatch only** — stdio transport deferred (low demo ROI vs. implementation cost)
2. **3 turns / 30s hard wall-time cap** — enforced via `asyncio.wait_for`, not just loop-top check
3. **`student_cip` injected by dispatch closure** — not in published schema, passes through allowlist
4. **`confirmed_focus` requires tool evidence** — only set when Gemma actually called a tool successfully
5. **Pre-inject stays for rows 1-5** — deterministic data needs don't benefit from tool-calling overhead
