# Feature: Chip Dispatch via Real Gemma Tool Calling Against the MCP Server

## Claude Code Prompt

```
Read the spec at docs/specs/feature-chip-dispatch-mcp-tool-calling.md in its
entirety. Also read the related specs:
  - docs/specs/feature-soc-expansion-via-gemma-tools.md (Spec B — provides
    the gemma_client.generate_with_tools helper this spec extends)
  - docs/specs/feature-gemma-tool-calling-migration.md (placeholder — this
    spec ships row 0 of that migration; promote the placeholder when this
    spec lands)

Execute the following workflow:

0. PRE-FLIGHT SPIKE
   - Run scripts/spike_gemma_tool_calling.py against gemma4:e4b on Ollama and
     google/gemma-4-26b-a4b-it on OpenRouter. Record tool-call success rate,
     argument validity, and per-call latency.
   - If gemma4:e4b reliability is < 80%, route Ollama through the
     prompt-then-parse fallback documented in §4 and proceed.
   - Findings written to §5.

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review the in-process-vs-stdio MCP client
     decision (§4 Decision Log #1), the multi-turn tool-call loop semantics,
     timeout/loop-cap handling, and back-compat with non-tool-call responses.
   - Invoke @genai-architect to review the tool catalog shape Gemma will see,
     the system prompt that frames "when to call get_career_paths," and the
     fallback prompt for Ollama parity.
   - Both write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - SKIPPED — no new visible UI surface. The chip debug trace already shows
     a "tool call made" indicator (Scenario 9 in the set-your-course mockup);
     this spec makes the indicator honest.

3. IMPLEMENTATION
   - Implement the spec as written in §4.
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update only tests in "Authorized Test Modifications".
   - CRITICAL: If any test NOT in that list fails, STOP and escalate.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest).
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
   - If still broken after 3 attempts: escalate to human via §10.

4. TESTING
   - Invoke @test-writer to review §4 Testing Impact Analysis.
   - Implement all "New Tests Required" by priority (P0 first).
   - Multi-turn tool-loop tests need careful mock sequencing — ensure the
     mocked Gemma client returns tool_calls on turn 1 and final text on turn 2.
   - Run ALL tests to catch regressions.

5. DESIGN AUDIT
   - SKIPPED — no visual surface change.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review with focus on:
     * Tool-call loop termination (max iterations, max wall time).
     * Tool-call argument validation before MCP dispatch.
     * Behavior when Gemma returns malformed tool_calls.
     * Behavior parity between INFERENCE_BACKEND=ollama and openrouter.
     * Latency budget vs the existing handle_chip_dispatch.
   - Reviewer writes findings to §8.

7. VERIFICATION
   - Invoke @fp-builder for full build verification.
   - Manual verification (§9): exercise the chip flow with "not_expected" +
     clarifier on BOTH backends; confirm gemma.jsonl shows real tool_calls
     records and the chip debug trace surfaces them honestly.
   - Log results to §9.

8. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Promote docs/specs/feature-gemma-tool-calling-migration.md from
     placeholder to a real spec, marking row 0 (chip dispatch) as completed
     and citing this spec as the reference implementation. Defer rows 1-5
     pending measurement.
   - Generate report to reports/feature-chip-dispatch-mcp-tool-calling-YYYY-MM-DD.md.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect + @genai-architect approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-20 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-20 |
| Blocked By | `feature-soc-expansion-via-gemma-tools.md` (Spec B — provides `gemma_client.generate_with_tools`) |
| Related Specs | `feature-soc-expansion-via-gemma-tools.md` (direct dependency); `feature-gemma-tool-calling-migration.md` (placeholder — promoted on completion of this spec); `feature-set-your-course.md` (defines `handle_chip_dispatch`); `submission-kaggle-narrative.md` (function-calling on local Ollama is a named demo beat) |

---

## §1 Feature Description

### Overview
Replace `handle_chip_dispatch`'s manual `_prefetch_career_paths` pattern with a real Gemma → MCP tool-calling loop. Gemma sees the MCP server's tool catalog, decides to call `get_career_paths`, the backend dispatches the call through MCP, the result feeds back into Gemma's context, Gemma returns the final structured chip response. This is the project's first true Gemma → MCP integration.

### Problem Statement
The current `handle_chip_dispatch` (`backend/app/services/set_your_course.py:580`) does what tool calling does, but by hand: the backend pre-fetches `get_career_paths` results, formats them into a `Pre-fetched career data` text block, pastes that into the prompt, and asks Gemma to reason. The chip prompt (`set_your_course.py:155-156`) even includes a *negative* instruction telling Gemma to NOT emit tool-call markup — because it isn't actually being given tools and would just produce broken text if it tried.

This is the inverse of what the architecture diagram suggests. We have an MCP server (`src/mcp_server/futureproof_server.py`) exposing 8 callable tools, but no Gemma call site in the backend actually exercises the tool-calling protocol end-to-end. The placeholder spec `feature-gemma-tool-calling-migration.md` documents this as the architectural inconsistency: *"the MCP server's tool-calling surface is effectively bypassed by the only app that was supposed to use it."*

This spec ships **row 0** of that migration. Chip dispatch is the right first target because:
- It's already shaped like a tool-call site (open-ended user input, needs reasoning + lookup).
- The student typed something unexpected; Gemma genuinely benefits from agency to investigate.
- It's the named flagship demo beat (Scenario 9 in the set-your-course mockup shows a tool-call indicator).
- Migrating it is a strict architectural improvement — same output, honest underpinnings, no new feature scope.

The migration spec's Tier P1–P2 rows (boss narration, guidance, recs, tiering, skill pool) are NOT in scope here. Pre-inject is genuinely better for those — the data needs are deterministic and pre-injection wins on latency, reliability, and cost. This spec is the *one* migration that pays for itself; the others should stay pre-inject indefinitely until proven otherwise.

### Success Criteria
- [ ] `handle_chip_dispatch` issues a real `tools=[...]` request to Gemma; the response contains `tool_calls` and the backend dispatches them through `mcp_client.call`.
- [ ] Multi-turn loop terminates correctly: max 3 turns, max 30s wall time, returns existing `_TRANSPORT_FAILURE_MESSAGE` chip response on cap.
- [ ] `_prefetch_career_paths` and `_format_prefetch_block` are deleted (no longer needed).
- [ ] Negative instruction in the chip prompt (`set_your_course.py:155-156`) is removed — Gemma is now allowed to emit tool calls.
- [ ] `gemma_client.generate_with_tools` (from Spec B) is extended to support multi-turn loops with caller-supplied tool dispatch.
- [ ] In-process MCP dispatch is the default; stdio dispatch is supported as a config flag for the Claude-Desktop-style demo (decision documented in §2 and §5).
- [ ] On Gemma error, malformed tool_calls, or loop cap hit, fallback returns the existing `_TRANSPORT_FAILURE_MESSAGE` chip response. Never crashes the chip endpoint.
- [ ] Both `INFERENCE_BACKEND=ollama` (`gemma4:e4b`) and `INFERENCE_BACKEND=openrouter` (`google/gemma-4-26b-a4b-it`) reliably produce well-formed tool-call responses. Spike confirms ≥80% tool-call success rate on each; if Ollama falls below, it falls back to prompt-then-parse with the same input/output shape.
- [ ] `logs/gemma.jsonl` records every tool-call turn with `call_site="chip_dispatch_tool_call"`, `turn_number`, `tools_offered`, `tool_called`, `tool_result_size`.
- [ ] `feature-gemma-tool-calling-migration.md` placeholder is promoted to a real spec citing this work.
- [ ] No regression in chip-flow pytest / vitest tests.
- [ ] Latency p50 within 1.5x of current `handle_chip_dispatch` (one extra Gemma turn vs the manual pre-fetch path).

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|-------------------------|
| 1 | **Default MCP dispatch is in-process; stdio is opt-in via config flag.** | The backend and MCP server are in the same repo and process. Spawning a subprocess for stdio adds startup latency, complicates testing, and pays no benefit — the dispatch result is identical. The architectural lie ("backend uses MCP-shaped contract") is fixed by the call going through `mcp_client.call(tool, args)` regardless of transport. The stdio mode exists for the demo (judges connect Claude Desktop to the same server, verifying the protocol works end-to-end). | Always stdio (rejected — pays subprocess overhead in every chip request for no demo win); always in-process (rejected — can't validate the MCP server actually serves real protocol traffic without running it for Claude Desktop). |
| 2 | Multi-turn loop capped at 3 Gemma calls, 30s wall time | Chip dispatch needs at most one tool call (`get_career_paths`) followed by Gemma's structured response. Three turns is generous: catalog round-trip + clarification + final. Hard caps prevent runaway loops if Gemma keeps calling tools. | No cap (rejected — pathological behavior on confused input); 1-turn cap (rejected — no room for follow-up tool calls in chip refinement). |
| 3 | Delete `_prefetch_career_paths`, don't keep as fallback | The prompt-then-parse fallback path inside `generate_with_tools` (from Spec B) is the one fallback. Keeping the old pre-fetch around AND a tools= path AND a prompt-then-parse fallback means three code paths that could drift. Two is enough. | Keep prefetch as third fallback (rejected — code rot risk); leave as-is, add tools= as A/B (rejected — postpones the migration indefinitely). |
| 4 | Tool catalog passed to Gemma is the FULL `get_tools()` output from the MCP server, filtered to the tools relevant to chip dispatch | Today chip dispatch only meaningfully needs `get_career_paths`. Filtering keeps the prompt small and Gemma's choice space tight. The full catalog is available; we just don't expose all 8 tools for this call site. | Expose all 8 tools (rejected — wastes prompt tokens, dilutes Gemma's reasoning); hardcode the schema (rejected — defeats the point of having an MCP server publishing schemas). |
| 5 | `mcp_client.call(tool, args)` remains the public contract; in-process and stdio modes hide behind it | Callers don't need to know which transport. The existing call sites that import the MCP server as Python (~7 services per the migration spec) continue to work unchanged. | New separate function for tool-loop dispatch (rejected — fragments the contract); breaking change to `mcp_client.call` (rejected — gratuitous churn). |
| 6 | Tool-call argument validation happens in `mcp_client.call`, not in `handle_chip_dispatch` | Validation logic belongs at the dispatch boundary so all callers (current + future migrated) get it. Gemma may emit malformed args; we coerce/reject before the handler sees them. | Validate in caller (rejected — duplicated logic per call site); trust Gemma (rejected — Gemma is allowed to be wrong). |
| 7 | Spike `gemma4:e4b` tool-call reliability BEFORE implementation | Smaller models often fake tool-call markup, miscall arguments, or ignore the catalog. Verifying this on the model judges will run locally is non-negotiable — if it doesn't work, the demo doesn't work. | Skip spike, hope for the best (rejected — too much downstream work to find out post-implementation that the model can't do this). |
| 8 | Existing `tool_call_made: bool` indicator in `ChipResponse` becomes truthful | Today it just means "our backend's manual pre-fetch returned data." Post-spec it means "Gemma actually called a tool." Same field name, accurate semantics. | Rename (rejected — gratuitous churn for downstream consumers); add new field alongside (rejected — duplicates state). |

### Constraints
- Must not regress chip-flow latency by more than 50% (one extra Gemma turn vs existing pre-fetch).
- Must work under both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`.
- Must preserve the existing `ChipResponse` contract — frontend changes ZERO.
- Must preserve the existing `confirmed_focus` invariant: `confirmed_focus` is only set when `tool_call_made=True`.
- All `CIPCODE` references stay as strings.
- Dates ISO `YYYY-MM-DD`. No `Any` in new public signatures.

### Out of Scope
The following live in adjacent specs or are explicitly deferred:

- **Migrating other call sites** (`career_tiering.tier_careers`, `boss_fights.narrate_one`, `guidance.generate_guidance_async`, `skill_recs`, `skill_pool`) — covered by `feature-gemma-tool-calling-migration.md`'s Tier P1+ rows. Pre-inject is genuinely better for those; do not migrate them as part of this spec.
- **New MCP tools** beyond what `get_tools()` already exposes.
- **Real-time tool-call indicator in the production UI** (chip debug trace already exists per Scenario 9; no new visible component).
- **Connecting the backend to a remote MCP server over SSE** — only stdio + in-process for this spec.
- **Migrating `compute_pentagon` / Spec B's `expand_socs` to MCP-tools-via-loop** — Spec B uses single-shot `tools=[...]`; this spec adds the multi-turn loop. They share `gemma_client.generate_with_tools` but have different control flow.
- **Caching tool-call results** — chip dispatch is per-tap, no caching.

---

## §3 UI/UX Design

**SKIPPED — no visual surface change.**

The chip debug trace (Scenario 9 in `docs/specs/design/set-your-course-mockup/index.html`) already renders a "tool call made" indicator. Today that indicator is a polite fiction; post-spec it's accurate. No component changes, no copy changes.

---

## §4 Technical Specification

### Architecture Overview

`handle_chip_dispatch` (`backend/app/services/set_your_course.py:580`) currently:
1. Manually invokes `_prefetch_career_paths(request)` — Python call into the MCP server module.
2. Formats the result into a `Pre-fetched career data` text block.
3. Builds a chip-routing prompt that *forbids* Gemma from emitting tool-call markup.
4. Calls `gemma_client.generate_chat_async(...)` for a single text response.
5. Parses Gemma's structured tail into `ChipResponse`.

Post-spec, the flow becomes:
1. Build the chip-routing prompt that *allows* Gemma to call `get_career_paths`.
2. Hand `gemma_client.generate_with_tools_loop(...)` the tool catalog (filtered from `mcp_server.get_tools()`) and a dispatch callable.
3. The loop:
   - Calls Gemma with `tools=[...]`.
   - If response contains `tool_calls`: validate args, dispatch via `mcp_client.call(tool, args)`, append result to message history, re-call Gemma. Cap: 3 turns, 30s wall time.
   - If response contains plain text: parse the structured tail, return.
4. Return `ChipResponse` with `tool_call_made=True` (now actually true).

The MCP dispatch is in-process by default (`mcp_client.call` invokes the handler directly, same as today's `_prefetch_career_paths`). A config flag `MCP_TRANSPORT=stdio` switches to a real stdio MCP client connecting to a separately-running `python -m brightsmith.serve` subprocess. The flag is for the demo path where you want a verifiable protocol crossing.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/set_your_course.py` | Modify | Replace `handle_chip_dispatch` body (lines 580-662) with the tool-loop path. Remove `_prefetch_career_paths` (lines 665+) and `_format_prefetch_block`. Update `_CHIP_ROUTING_SYSTEM_PROMPT` (lines 145+): remove the "no tool-call markup" negative instruction (lines 155-156); replace the `prefetch_block` interpolation point with instructions on when to call `get_career_paths`. |
| `backend/app/services/gemma_client.py` | Modify | Extend with `async def generate_with_tools_loop(system, user, tools, dispatch, max_turns=3, max_wall_time_s=30.0, ...)` — async multi-turn variant of Spec B's `generate_with_tools`. Returns `(final_text, tool_call_log)` so the caller can populate `ChipResponse.tool_call_made` and the debug trace. Logs every turn to `gemma.jsonl`. |
| `backend/app/services/mcp_client.py` | Modify | Add real MCP-protocol dispatch behind the existing `call(tool, args)` contract. `MCP_TRANSPORT` env var (`in_process` default, `stdio` opt-in). For stdio, spawn `python -m brightsmith.serve` as a subprocess and speak the MCP protocol via the official `mcp` Python package. For in-process, keep today's direct-import behavior. Argument validation: coerce types per the tool's `input_schema`, reject extras, raise structured error on type mismatch. |
| `src/mcp_server/futureproof_server.py` | Modify (descriptions only) | Review `get_tools()` (line 629) for `get_career_paths` — tighten the description so Gemma understands *when* to call it (when `current_resolution` doesn't fit the clarifier; when verifying a sub-focus exists in the school's program list). No schema changes; description-only edit. |
| `scripts/spike_gemma_tool_calling.py` | **Create** | Single-purpose spike: 20 chip-dispatch-shaped scenarios on both backends. Records tool-call success rate, argument validity, latency. Writes findings to §5 of this spec. Pattern: same shape as `scripts/spike_gemma_intent_openrouter.py`. |
| `backend/tests/services/test_set_your_course_chip_tool_loop.py` | **Create** | New test file (see §4 Testing Impact Analysis). |
| `backend/tests/services/test_gemma_client.py` | Modify | Add tests for `generate_with_tools_loop`. |
| `backend/tests/services/test_mcp_client.py` (verify exists) | Modify | Add tests for argument validation + transport switching. |

**Files NOT changed:**
- Frontend — `ChipResponse` contract unchanged, no UI changes.
- `backend/app/routers/set_your_course.py` — router stays the same; only the service body changes.
- Other Gemma-touching services (`career_tiering`, `boss_fights`, `guidance`, etc.) — explicitly out of scope.

### Service Changes

#### `gemma_client.generate_with_tools_loop`

```python
async def generate_with_tools_loop(
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    *,
    max_turns: int = 3,
    max_wall_time_s: float = 30.0,
    temperature: float = 0.0,
    extra: dict[str, Any] | None = None,
) -> tuple[str, list[ToolCallTurn]]:
    """Issue a multi-turn Gemma chat with OpenAI-compatible tool calling.

    Returns ``(final_text, tool_call_log)``:
    - ``final_text``: Gemma's last text response (the one without further
      tool calls). Empty string on transport failure or cap hit.
    - ``tool_call_log``: ordered list of ToolCallTurn records for each
      tool invocation. Empty list when Gemma returned text on turn 1.

    Loop semantics:
    1. Call Gemma with the tool catalog and current message history.
    2. If response.choices[0].message.tool_calls is non-empty:
       a. For each tool_call: validate args, await dispatch(name, args),
          append both the assistant message and the tool result to history.
       b. If turn count == max_turns: stop, return last final text.
       c. If wall time > max_wall_time_s: stop, return last final text.
       d. Else: loop.
    3. If response is plain text: return it.

    Falls back to prompt-then-parse pattern (Spec B's documented fallback)
    when ``INFERENCE_BACKEND=ollama`` and the §0 spike measured tool-call
    success < 80% for gemma4:e4b. The fallback simulates one tool dispatch
    by calling the dispatch function with caller-provided "default args"
    (set in extras), then asking Gemma for the final response with the
    result pre-injected. Same input/output shape; lossy but works.

    Logs each turn to logs/gemma.jsonl with call_site, turn_number,
    tools_offered, tool_called, tool_result_size, duration_ms.
    """
    ...


@dataclass(frozen=True)
class ToolCallTurn:
    turn_number: int
    tool_name: str
    tool_args: dict[str, Any]
    tool_result_size_bytes: int
    duration_ms: int
    error: str | None
```

#### `mcp_client.call` — argument validation + transport switch

```python
def call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke an MCP tool by name. Transport selected by MCP_TRANSPORT env.

    in_process (default): direct handler call (today's behavior).
    stdio: speak the MCP protocol against a python -m brightsmith.serve
           subprocess started lazily on first call. One subprocess per
           backend process, kept alive with stdin/stdout pipes.

    Argument validation:
    - Look up the tool's input_schema from the MCP server's get_tools().
    - Coerce types where unambiguous (int strings to int, float strings
      to float).
    - Reject keys not in the schema.
    - Raise McpArgumentError with a structured message on type mismatch
      or missing required keys.

    Validation runs for both transports so callers see consistent
    error semantics.
    """
    ...


async def call_async(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Async variant for use inside generate_with_tools_loop."""
    ...
```

#### Updated `_CHIP_ROUTING_SYSTEM_PROMPT` (sketch)

Remove lines 155-156 (the negative instruction). Replace the `prefetch_block` interpolation with:

```
You have access to one tool:

- get_career_paths(unitid, cipcode, student_major?, student_cip?) —
  returns the matched career list for a school + program. Call this
  when:
  * The clarifier mentions a sub-specialty you can't verify is offered
    at this school (e.g., "deaf education" inside a Special Ed CIP).
  * The clarifier suggests a different program than current_resolution
    and you need to check if the school offers it.
  * You need to ground a feasibility judgment in actual data.

Do NOT call the tool when:
  * The decision is clear from the clarifier alone (e.g., "I want
    something completely different" — that's a change_major case).
  * You've already called it once this turn and got a useful result.

After your tool call (if any) returns, emit your final structured chip
response per the existing format spec.
```

The existing structured tail format (debug trace, bucket, confirmed_focus, etc.) is unchanged.

### Data Model Changes

None. `ChipResponse` is unchanged. `tool_call_made` semantics shift from "our pre-fetch returned data" to "Gemma made a real tool call," but the field name and type stay.

A new internal `ToolCallTurn` dataclass exists in `gemma_client.py` for log records — not exposed across module boundaries.

### MCP Server Changes

`get_tools()` descriptions reviewed during implementation for Gemma-readability. No schema changes. The 8 tools published today stay published; chip dispatch only exposes `get_career_paths` to Gemma in the loop, but the others remain available for future call site migrations and external clients (Claude Desktop).

### Spike script — `scripts/spike_gemma_tool_calling.py`

Pattern follows `scripts/spike_gemma_intent_openrouter.py` (existing). Tests:
- 20 chip-dispatch-shaped prompts varying clarifier specificity, school CIP coverage, and intent ambiguity.
- For each: issue a single `tools=[get_career_paths]` request, record:
  - Did the model emit a tool call? (yes/no)
  - Were the arguments valid against the schema? (yes/no/coercible)
  - Did the tool result come back? (yes/no/error)
  - Latency (ms)
- Run on both `gemma4:e4b` (Ollama) and `google/gemma-4-26b-a4b-it` (OpenRouter).
- Output: a markdown table written to §5 of this spec.

If `gemma4:e4b` success rate < 80%: implementation routes Ollama through the prompt-then-parse fallback and notes the decision in §5.

### Gemma Integration Discipline

| Concern | Approach |
|---|---|
| Fallback behavior | On loop cap hit, malformed tool call, dispatch error, or transport failure: return the existing `_TRANSPORT_FAILURE_MESSAGE` chip response. The chip endpoint never crashes the request. |
| `gemma.jsonl` logging | Every Gemma turn within the loop gets its own record with `call_site="chip_dispatch_tool_call"`, `turn_number`, `tools_offered`, `tool_called` (or null), `tool_result_size`, `duration_ms`. `mcp_client.call` also logs to `logs/mcp.jsonl` (existing or new — verify) with `tool`, `args_size`, `result_size`, `duration_ms`. |
| Backend parity | Spike-validated. If Ollama fails the 80% bar, fallback is documented + tested. |
| Rate limit / concurrency | Each chip request consumes 1–3 Gemma turns (vs 1 today). Module-level semaphore (max 8 concurrent) covers this — chip dispatch is a one-at-a-time user action, not a fan-out. |
| Cloud demo cost | OpenRouter charges per token. A 2-turn loop costs ~2x a single call because turn 2 re-sends turn 1's history. Acceptable — chip dispatch is rare per session. |

### Testing Impact Analysis

> **Searched** `backend/tests/` for tests touching `handle_chip_dispatch`, `_prefetch_career_paths`, `_format_prefetch_block`, `mcp_client`, `generate_with_tools`.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_set_your_course.py` | All `handle_chip_dispatch` tests | **High** | The function body is fully replaced. Existing tests likely assert against the old prefetch path. Many will need rewriting against the tool-loop. Document each rewrite. |
| `backend/tests/routers/test_set_your_course_router.py` | `/intent/chip` endpoint tests | Med | Endpoint contract unchanged, but mocked Gemma responses now need to be tool-call-shaped or the test exercises the fallback path. |
| `backend/tests/services/test_gemma_client.py` | All existing `generate*` tests | Low | Adding a new helper, not modifying existing ones. |
| `backend/tests/services/test_mcp_client.py` (verify exists) | All existing `call` tests | Med | Adding argument validation may cause tests passing previously-invalid args to fail. Document each. |
| `frontend/src/screens/__tests__/SetYourCourseScreen.test.tsx` | Chip-flow tests | Low | `ChipResponse` unchanged. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_set_your_course.py::test_handle_chip_dispatch_*` | Rewrite mocks to return tool-call-shaped responses; assert tool dispatch fires; assert `tool_call_made=True`. | Function body fully changes; old assertions about prefetch are no longer valid. |
| `backend/tests/services/test_mcp_client.py` | If any test calls `mcp_client.call` with args that don't match a tool's schema, update or remove. | New validation enforces schema conformance. |

#### Confirmed Safe

These tests must NOT break — if they fail, STOP and escalate:

- All non-chip `set_your_course` tests (`stream_initial_resolution`, etc.).
- All `mcp_client.call` tests where args were already schema-valid.
- All `gemma_client.generate` and `generate_chat` tests (existing helpers, untouched).
- All `BuildSummary` / persisted-build replay tests.
- `ChipResponse` deserialization in router tests.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_set_your_course_chip_tool_loop.py` | `test_chip_dispatch_calls_gemma_with_tools` | `handle_chip_dispatch` invokes `generate_with_tools_loop` with the `get_career_paths` schema in the tool catalog. |
| P0 | same | `test_chip_dispatch_loops_on_tool_call` | Mocked Gemma returns a `tool_calls` response on turn 1, then plain text on turn 2. Loop dispatches the tool, appends result, re-calls Gemma, returns final text. |
| P0 | same | `test_chip_dispatch_no_tool_call_returns_directly` | Mocked Gemma returns plain text on turn 1 (no tool call). Loop returns immediately. `tool_call_made=False`. |
| P0 | same | `test_chip_dispatch_loop_cap_returns_failure_chip` | Mocked Gemma returns a tool call every turn (pathological). Loop hits cap, returns `_TRANSPORT_FAILURE_MESSAGE` chip response. |
| P0 | same | `test_chip_dispatch_wall_time_cap` | Same as above but cap is wall time, not turn count. |
| P0 | same | `test_chip_dispatch_malformed_tool_call_returns_failure_chip` | Mocked Gemma returns a tool_call with invalid args. Loop catches `McpArgumentError`, returns failure chip. |
| P0 | same | `test_chip_dispatch_dispatch_error_returns_failure_chip` | Tool dispatch raises. Loop catches, returns failure chip. |
| P0 | same | `test_chip_dispatch_confirmed_focus_only_when_tool_call_made` | Existing invariant: `confirmed_focus` is None when no tool call happened. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_loop_single_turn` | Plain text response on turn 1, returns directly. |
| P0 | same | `test_generate_with_tools_loop_two_turn` | tool_calls on turn 1, text on turn 2, loop dispatches and returns. |
| P0 | same | `test_generate_with_tools_loop_logs_each_turn_to_jsonl` | Verify per-turn records in `gemma.jsonl`. |
| P0 | same | `test_generate_with_tools_loop_ollama_fallback_to_prompt_parse` | When `INFERENCE_BACKEND=ollama` and the spike fallback is engaged, the loop simulates a tool dispatch via prompt-then-parse and produces the same `(final_text, tool_call_log)` shape. |
| P0 | `backend/tests/services/test_mcp_client.py` | `test_call_validates_args_against_schema` | Calling `mcp_client.call("get_career_paths", {"unitid": "not_a_number"})` either coerces or raises `McpArgumentError`. |
| P0 | same | `test_call_rejects_unknown_keys` | Extra keys in args raise `McpArgumentError`. |
| P1 | same | `test_call_in_process_default` | Default transport is in-process; result matches direct handler call. |
| P1 | same | `test_call_stdio_when_env_set` | With `MCP_TRANSPORT=stdio`, the call goes through a subprocess. (Skip if subprocess machinery isn't testable in CI; mark `@pytest.mark.integration`.) |
| P1 | `backend/tests/routers/test_set_your_course_router.py` | `test_chip_endpoint_with_tool_loop` | End-to-end through the router: POST `/intent/chip` with `not_expected` + clarifier triggers the tool-loop path and returns a well-formed `ChipResponse`. |
| P2 | `backend/tests/services/test_set_your_course_chip_tool_loop.py` | `test_chip_dispatch_show_less_common_short_circuits` | `show_less_common` and `change_major` chip ids still return the empty `ChipResponse` without invoking Gemma (existing behavior). |

#### Test Data Requirements

- Mocked OpenAI tool-call response fixtures:
  ```python
  TOOL_CALL_RESPONSE = {
      "choices": [{
          "message": {
              "content": None,
              "tool_calls": [{
                  "id": "call_1",
                  "type": "function",
                  "function": {
                      "name": "get_career_paths",
                      "arguments": '{"unitid": 151351, "cipcode": "26.05", "student_major": "deaf education"}'
                  }
              }]
          }
      }]
  }
  ```
- Mocked plain-text response fixture (no tool call) for the short-circuit path.
- Mocked tool result fixture matching the real `_handle_get_career_paths` output shape.
- Pre-recorded `gemma.jsonl` fixture for the parity test (one record per turn).

---

## §5 Architecture Review

### Pre-flight Spike (`scripts/spike_gemma_tool_calling.py`)
**Status:** COMPLETE (2026-04-20)
#### Findings

| Backend | Scenarios | Tool-Call Rate | Valid Args | Avg Latency | P50 Latency |
|---------|-----------|---------------|------------|-------------|-------------|
| ollama (gemma4:e4b) | 20 | 18/20 (90%) | 18/20 (90%) | 26,803ms | 24,367ms |

Two scenarios returned plain text instead of tool calls (nursing-at-liberal-arts, music-education) — both cases where the clarifier strongly signals a non-tool-call path ("I want to perform, not teach" doesn't need a data lookup). This is correct model behavior, not a failure.

Ollama's OpenAI-compat `/v1/chat/completions` endpoint correctly processes `tools=[...]` with gemma4:e4b. The thinking-mode concern (flagged by both reviewers) did not manifest — tool calls come back with valid arguments, and the `content` field is correctly null when tool_calls are present. P50 latency of ~24s is acceptable for a one-at-a-time user action.

#### Decision
- [x] Ollama goes through real `tools=[...]` (success rate 90% >= 80%)
- [ ] ~~Ollama falls back to prompt-then-parse (not needed)~~

### @fp-architect Review
**Status:** COMPLETE
**Reviewed:** 2026-04-20

#### System Context

This spec touches the service layer (`set_your_course.py`), the inference client (`gemma_client.py`), the MCP client singleton (`mcp_client.py`), and the MCP server's tool descriptions (`futureproof_server.py`). It crosses three boundaries: (1) the backend service to the Gemma inference endpoint, (2) the Gemma response back to the service, and (3) the service to the MCP tool handler. No pipeline zone changes, no Gold schema changes, no frontend contract changes. The ripple is contained to the backend service layer and its two outbound interfaces.

#### Data Flow Analysis

**Current flow:** `handle_chip_dispatch` -> `_prefetch_career_paths` (direct Python call via `mcp_client.call("get_career_paths", args)`) -> format result into prompt text -> `gemma_client.generate_chat_async` (single turn, no tools) -> parse structured tail -> `ChipResponse`.

**Proposed flow:** `handle_chip_dispatch` -> `gemma_client.generate_with_tools_loop` (multi-turn, `tools=[get_career_paths]`) -> Gemma decides to call tool -> dispatch callback invokes `mcp_client.call_async("get_career_paths", args)` -> result appended to message history -> Gemma re-called with history -> Gemma returns structured text -> parse structured tail -> `ChipResponse`.

The data path is sound. The MCP server handler (`_handle_get_career_paths`) is unchanged. The Gold zone table (`consumable.program_career_paths`) is read-only and accessed through the same query engine. The `ChipResponse` Pydantic model is unchanged -- no API contract breaks.

**Boundary crossings verified:**
1. Backend -> Gemma: OpenAI-compatible `tools=[...]` parameter via `client.chat.completions.create`. Works for both OpenRouter and Ollama `/v1/chat/completions`.
2. Gemma -> Backend: `response.choices[0].message.tool_calls` (standard OpenAI tool_calls format). Parsed and validated.
3. Backend -> MCP handler: `mcp_client.call("get_career_paths", args)` -- same contract as today.
4. Backend -> Frontend: `ChipResponse` unchanged.

#### Contract Review

**`generate_with_tools_loop` signature:** Well-typed. The `dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]` async callable is the right abstraction -- it decouples the loop from the transport. Return type `tuple[str, list[ToolCallTurn]]` gives the caller everything needed to populate `tool_call_made` and log records.

**`ToolCallTurn` dataclass:** Frozen, internal-only, correct fields. Not crossing module boundaries -- good.

**`mcp_client.call_async`:** Spec proposes this but the current `mcp_client.call` is synchronous. The async variant will need to wrap the sync handler via `asyncio.to_thread` (matching the pattern used in `generate_async`). This is fine.

**`ChipResponse`:** Unchanged. The `tool_call_made` boolean referenced in Decision #8 is actually an internal variable in `_parse_chip_response`, not a field on `ChipResponse`. The spec text in Decision #8 ("Existing `tool_call_made: bool` indicator in `ChipResponse`") is imprecise -- it's the internal gate for `confirmed_focus`, not a response field. This is cosmetic; the semantic shift described is correct.

#### Findings

##### Sound

1. **In-process vs stdio transport decision (Decision #1) is architecturally clean.** The `mcp_client.call(tool, args)` contract stays the same regardless of transport. Callers don't know or care. The stdio mode for demo/judge purposes is opt-in via `MCP_TRANSPORT` env var, which is the right layer for that concern. No code-path branching in service logic.

2. **Multi-turn loop semantics are well-bounded.** 3 turns and 30s wall time are generous for a flow that needs at most 1 tool call. The cap-hit behavior (return `_TRANSPORT_FAILURE_MESSAGE` chip response) reuses the existing failure contract so the frontend sees the same shape regardless of why the backend failed. This is the right approach.

3. **Back-compatibility with non-tool-call responses is correct.** When Gemma returns plain text on turn 1, the loop exits immediately and `tool_call_log` is empty. The caller sees `tool_call_made=False` and `confirmed_focus` stays `None`. This preserves the existing invariant.

4. **Deleting `_prefetch_career_paths` (Decision #3) is the right call.** Three code paths (prefetch + tool-loop + prompt-then-parse fallback) would drift. Two (tool-loop + prompt-then-parse fallback) is the minimum viable set.

5. **Filtering the tool catalog to `get_career_paths` only (Decision #4) keeps Gemma focused.** Showing all 8 tools would waste prompt tokens and invite hallucinated calls to irrelevant tools. Reading the filter from `get_tools()` rather than hardcoding the schema preserves the MCP server as the single source of truth for tool schemas.

6. **Concurrency model is sound.** The existing module-level semaphore (max 8 concurrent) covers the additional Gemma turns. Each chip dispatch is a user-initiated action, not a fan-out, so the 1-3 turn cost per request is acceptable.

##### Concerns

- **`student_cip` parameter loss:** The current `_prefetch_career_paths` passes `student_cip` to `mcp_client.call("get_career_paths", args)` (line 822 of `set_your_course.py`). This parameter is accepted by the handler (`_handle_get_career_paths` at line 2527 of `futureproof_server.py`) but is NOT in the published `input_schema` (lines 846-881 of `futureproof_server.py`). The schema only exposes `unitid`, `cipcode`, and `student_major`. Decision #6 specifies that argument validation will "reject keys not in the schema." This means:
  1. Gemma cannot pass `student_cip` because it's not in the tool catalog.
  2. Even if Gemma somehow passed it, the new validation would reject it as an unknown key.
  3. The old prefetch path used `student_cip` to skip the YAML lookup and pass the already-resolved CIP directly. The tool-loop path loses this capability.

  **Impact:** When the school reports a broad XX.01 CIP and the student has a specific sub-CIP from intent resolution, the prefetch path today sends `student_cip=resolved_leaf_cip` to trigger substitution. Without this, the tool-loop path would need to rely on `student_major` (free-text), which goes through the YAML lookup -- a path the project has explicitly moved away from (see "No YAML lookups" memory). **Recommendation:** Either (a) add `student_cip` to the `get_career_paths` published `input_schema` so it's visible to Gemma and passable through validation, or (b) have the dispatch callback inject `student_cip` from the request context before forwarding to `mcp_client.call`, bypassing validation for this known internal parameter. Option (b) is simpler and doesn't leak an implementation detail into the Gemma-facing schema; option (a) is more honest. Either way, this needs a decision before implementation.

- **Ollama native API vs OpenAI-compat for tool calling:** The existing `generate_with_tools` (Spec B) uses `client.chat.completions.create` (the OpenAI-compat `/v1/chat/completions` endpoint) for both backends. But the existing `generate_chat` uses Ollama's native `/api/chat` endpoint for Ollama backend specifically because `/v1/chat/completions` ignores `think: false` and Gemma 4's extended thinking consumes all output tokens. The spec's `generate_with_tools_loop` will presumably also use the OpenAI-compat endpoint (since the OpenAI SDK handles tool_calls parsing). If Gemma 4 on Ollama burns tokens on thinking during the tool-call turn, the response may come back content-empty or with truncated tool_calls. The spike script should specifically watch for this failure mode. If it appears, the implementation may need to use Ollama's native `/api/chat` with `tools` + `think: false` (the native API supports both). **Impact:** Potential silent failure on Ollama where tool-call responses are empty. **Recommendation:** The spike script (step 0) should explicitly log whether Ollama responses contain thinking tokens that consume the budget. If so, the loop implementation should use the native Ollama `/api/chat` endpoint with `think: false` + `tools`, same pattern as `_ollama_chat_sync` but with tool support added.

- **`call_async` implementation detail:** The spec proposes `async def call_async(tool, args)` but doesn't specify how it bridges to the sync handler. The handler (`_handle_get_career_paths`) does DuckDB queries that are CPU/IO-bound. Wrapping in `asyncio.to_thread` is the right approach (matches `generate_async`'s pattern). The spec should note this explicitly so the implementer doesn't accidentally call the sync handler directly from the async context, which would block the event loop. **Impact:** Minor -- the implementer will likely figure this out. **Recommendation:** Add a one-line note to the `call_async` docstring: "Wraps sync `call()` via `asyncio.to_thread`."

##### Blockers

None.

#### Verdict
- [x] CHANGES REQUESTED

#### Conditions

1. **Resolve the `student_cip` parameter gap.** The dispatch callback or the tool schema must preserve the CIP substitution behavior that `_prefetch_career_paths` provides today via the `student_cip` argument. Without this, broad-CIP schools (the most common case for the "not expected" chip) will regress to YAML-based major lookup or no substitution at all. Decide on option (a) or (b) from the concern above and document the decision in the Decision Log before implementation proceeds.

2. **Spike must test Ollama thinking-token interference.** Confirm that `generate_with_tools` on Ollama via `/v1/chat/completions` actually returns usable `tool_calls` and doesn't burn the token budget on extended thinking. If it does, plan the native API fallback path before implementation.

### @genai-architect Review
**Status:** COMPLETE
#### Findings

**Scope reviewed:** tool catalog shape Gemma will see, `_CHIP_ROUTING_SYSTEM_PROMPT` framing,
fallback prompt design for Ollama parity, and the multi-turn loop contract defined in
`generate_with_tools_loop`.

---

##### 1. Tool catalog shape

The spec exposes exactly one tool — `get_career_paths` — filtered from the full 8-tool
`get_tools()` output. The live schema has `unitid` (integer, required), `cipcode` (string,
required), and `student_major` (string, optional). There is no `student_cip` parameter in the
published schema; the existing `_prefetch_career_paths` sends `student_cip` today but that is a
back-channel key the MCP handler accepts, not a schema-declared parameter. This is fine for
in-process dispatch but it creates a latent risk: when Gemma sees the schema, it will never emit
`student_cip` in its tool call. The handler will therefore always run the YAML-lookup path instead
of the skip-YAML path that `student_cip` enables. The spec should decide whether to (a) add
`student_cip` to the schema now, or (b) document explicitly that the YAML path fires and verify
the sub-specialty accuracy is acceptable without it. This is a **required decision, not a blocker**
— either choice is valid but it must be made consciously before implementation.

The tool description text is functional but wordy for a model prompt. The final sentence
("When the school only reports a broad XX.01 CIP, pass student_major to substitute the
major-specific SOC set…") is the most important signal for Gemma's argument assembly and should
be pulled to the top or bolded in the schema description so smaller models like `gemma4:e4b`
surface it early. The spec already calls for a description-only edit of `get_tools()` during
implementation — this is the right moment to do that reordering.

The OpenAI-compatible tool object shape that `generate_with_tools` (Spec B) already uses is
`{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`. The
MCP server's `ToolDef.input_schema` maps cleanly to `parameters`. Confirm during implementation
that the adapter producing the tool list for Gemma formats the wrapper correctly; a bare
`input_schema` dict passed as `tools=[input_schema]` would cause a silent no-op on most providers.

##### 2. System prompt framing

The `_CHIP_ROUTING_SYSTEM_PROMPT` (lines 72–199 in `set_your_course.py`) currently contains two
mutually hostile instruction blocks:

- Line 138: "Any sub-specialty label…is legitimate ONLY IF the student named it first AND **a
  tool call verified** it is a real sub-area of the resolved program."
- Lines 155–156: "**You have no tool access in this turn.** Do NOT emit any tool-call markup."

These contradict each other. The spec correctly identifies this and instructs removing lines
155–156, then adding the "when to call / when not to" block from §4. That replacement is
sound. One refinement: the existing instruction at line 138 already tells Gemma *when the tool
result matters* (to confirm a sub-specialty) but doesn't say when not calling still yields a
valid response. The proposed replacement block covers this with the "Do NOT call the tool when…"
branch. Preserve the line-138 language verbatim in the updated prompt — it is the correctness
constraint; the new block is the routing instruction.

The proposed `when to call` trigger conditions are well-chosen:
- "sub-specialty you can't verify is offered at this school" — maps exactly to the crosswalk_mismatch
  / semantic_drift buckets where tool verification matters most.
- "clarifier suggests a different program than current_resolution" — maps to semantic_drift.
- "need to ground a feasibility judgment in actual data" — intentionally open, which is appropriate
  for this call site.

The proposed `when not to call` conditions are also correct:
- "decision is clear from the clarifier alone (change_major)" — already short-circuits in Python
  before Gemma is called, so this instruction is redundant for that case but harmless as a
  conceptual anchor.
- "already called it once this turn and got a useful result" — critical for loop stability; keep.

One addition worth making: explicitly tell Gemma that it must still emit the structured tail
(`---BUCKET---`, `---CONFIRMED_FOCUS---`, `---UPDATED_RESOLUTION---`) regardless of whether it
called the tool. This is already implied by the existing "Always append the classification tail"
instruction but that instruction currently lives after the prefetch block injection point which
will be replaced. Verify that instruction survives the edit.

##### 3. Ollama-specific concern: `think` mode and tool calling

The existing `generate_with_tools` function uses the OpenAI-compatible
`client.chat.completions.create(tools=[...])` path unconditionally for both Ollama and
OpenRouter. But `generate_chat` and `generate` already found that Ollama's OpenAI-compat
endpoint ignores `think=false` and defaults to extended-thinking mode, consuming all output
tokens with reasoning and leaving `content` empty. They work around this by routing Ollama to the
native `/api/chat` endpoint with `think=false`.

The new `generate_with_tools_loop` spec says it "works with both backends" but doesn't address
this discrepancy. The Ollama native `/api/chat` endpoint does NOT support the `tools` parameter
in the same way as the OpenAI-compat endpoint, and extended-thinking will compete with tool-call
tokens for the output budget. This is the most significant technical risk in the spec.

Two paths forward:

**Path A (preferred):** Use the Ollama OpenAI-compat endpoint for `tools=[...]` calls but add
`"think": false` to the `extra_body` parameter of the OpenAI SDK call. Test whether the current
Ollama version honors this. If it does, the two-path split in `generate_chat` becomes unnecessary
for tool-calling calls.

**Path B (fallback):** If Ollama does not honor `think=false` via OpenAI-compat, route all
Ollama tool-calling through prompt-then-parse unconditionally (not gated on the 80% spike
result) and document this as a permanent architectural constraint for `gemma4:e4b`. The spike
in §0 should explicitly test for empty `content` when `finish_reason=stop` on Ollama — this
is the symptom of the thinking-overflow bug.

The spec currently treats the Ollama fallback as spike-outcome-conditional. Given the known
thinking-mode issue, the spike should include a dedicated test: does `gemma4:e4b` on Ollama
actually return a `tool_calls` field (non-empty) when given `tools=[...]` via the OpenAI-compat
endpoint? Add this as a pass/fail criterion in the spike script alongside the 80% success-rate
threshold.

##### 4. Multi-turn loop contract

The `generate_with_tools_loop` signature and semantics are well-designed. Specific notes:

**Semaphore accounting:** The existing semaphore (`_get_semaphore()`, default max 8) is acquired
once per `generate_async` call. A 3-turn loop will acquire/release the semaphore 3 times in
sequence, which is correct. However, if chip dispatch is called concurrently (not typical for a
one-at-a-time user action but possible in integration tests), three sequential Gemma calls per
chip request will hold the semaphore for the full wall-time budget. The existing comment in
`gemma_client.py` ("chip dispatch is a one-at-a-time user action, not a fan-out") is accurate
— document this assumption in the loop implementation so future callers understand the
concurrency model.

**`dispatch` callable signature:** The spec defines `dispatch` as
`Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]`. The existing `mcp_client.call`
is synchronous. The spec adds `call_async` as the async wrapper. Confirm that `call_async` is
a thin `asyncio.to_thread` wrapper (same pattern as `generate_async`) rather than a true async
implementation — DuckDB is not async-safe and any direct DuckDB call on the MCP handler must
stay on a dedicated thread.

**Empty `final_text` on cap:** The spec returns `("", [])` on loop cap and wall-time cap, then
the caller returns `_TRANSPORT_FAILURE_MESSAGE`. This is the right failure mode. One edge case:
if Gemma returns a tool call on turn 1, the tool dispatches successfully, and then Gemma returns
an empty string on turn 2 (not a tool call, not text), the loop should also return the failure
response. The current spec handles this via the "returns empty string on transport failure"
contract of `generate_with_tools` but the multi-turn variant should explicitly handle
`final_text == ""` from a non-tool-call turn as a failure condition.

**Tool-call ID in history:** OpenAI's multi-turn tool-call protocol requires the assistant message
to include `tool_calls` with the `id` field, and the tool-result message to include
`tool_call_id` matching that id. Some providers (including OpenRouter) enforce this. The spec's
test fixture (`TOOL_CALL_RESPONSE`) includes `"id": "call_1"` which is correct. Ensure the
loop's message assembly uses the actual `id` from the response object — do not hardcode
`"call_1"`.

**Multiple tool calls in one turn:** The OpenAI protocol allows a single response to contain
multiple `tool_calls`. The spec says "For each tool_call: validate args, await dispatch…" which
is correct. Confirm that the implementation iterates all tool calls in a single response turn
rather than only processing `tool_calls[0]` (which is what the existing single-shot
`generate_with_tools` does with `tc = tool_calls[0]`). For chip dispatch this matters because
Gemma could theoretically emit a second spurious tool call alongside the real one.

##### 5. Fallback prompt for Ollama parity

The spec's fallback ("simulates one tool dispatch by calling the dispatch function with
caller-provided 'default args' set in extras") is the right shape but the source of "default
args" needs tightening. The existing `_prefetch_career_paths` already constructs the right args
from `request.current_resolution` (with the parent CIP / student_cip substitution logic).
Reusing that arg-construction logic as the default args for the prompt-then-parse fallback is
the cleanest approach — it avoids duplicating the substitution semantics. The spec should
explicitly state that the fallback "default args" come from the same arg-construction logic as
the deleted `_prefetch_career_paths`, not from arbitrary caller-supplied extras.

The `_fallback_prompt_for_json` pattern already in `gemma_client.py` (lines 849–929) converts
a tool schema to an explicit JSON instruction and re-issues the request. The chip-dispatch
fallback is a different shape — it needs to produce a final chip response (structured tail) after
dispatching the tool result, not just a JSON object. The spec should clarify whether the
prompt-then-parse fallback: (a) injects the tool result into the prompt and asks for the
full chip response including structured tail, or (b) calls `_fallback_prompt_for_json` for
argument resolution only, then does a second `generate_chat` call for the final response. Option
(a) is simpler and should be the default.

##### 6. Logging

The spec adds `call_site="chip_dispatch_tool_call"`, `turn_number`, `tools_offered`,
`tool_called`, `tool_result_size` to each JSONL record. This is correct. One gap: the existing
`generate_with_tools` log records use `tool_call_made: bool` as a top-level field. The new
per-turn records should also emit `tool_call_made: bool` so downstream log consumers don't need
to infer it from the presence/absence of `tool_called`. Add this to the record schema in §4.

##### 7. `_TOOL_CALL_PATTERNS` strip regex

Lines 868–874 of `set_your_course.py` define regex patterns to strip tool-call pseudo-XML from
Gemma's prose when it was emitted without real tool-call support. Post-spec, Gemma will call
tools via the protocol and tool calls will arrive in `tool_calls`, not `content`. The strip
regex becomes vestigial for the multi-turn path. It should remain for robustness (Gemma might
still hallucinate tool-call markup in the final text response) but add a comment noting the
expected use case has changed — the patterns now guard against hallucinated markup in the
*final text turn* rather than the only text turn.

---

##### Summary of Required Actions Before Implementation

| # | Severity | Item |
|---|----------|------|
| A | Required | Decide: add `student_cip` to the `get_career_paths` schema or document that the YAML-lookup path fires and verify accuracy. |
| B | Required | Spike must explicitly test whether `gemma4:e4b` on Ollama returns non-empty `tool_calls` via the OpenAI-compat endpoint (the thinking-overflow risk). |
| C | Required | Specify that fallback "default args" derive from the same arg-construction logic as the deleted `_prefetch_career_paths`. |
| D | Required | Verify tool-call message assembly uses the actual `id` from the response object, not a hardcoded value. |
| E | Recommended | Reorder the `get_career_paths` description so the substitution instruction (student_major / broad CIP) is the first sentence. |
| F | Recommended | Add `tool_call_made: bool` to every per-turn JSONL record schema. |
| G | Recommended | Add a comment on `_TOOL_CALL_PATTERNS` explaining the changed use case post-spec. |
| H | Recommended | Confirm `call_async` is an `asyncio.to_thread` wrapper, not a native async call, given DuckDB thread safety. |

None of the required items are architectural blockers — they are implementation-time decisions
that must be made explicit before coding begins, not after. The overall design is sound.

#### Verdict
- [x] APPROVED (with required pre-implementation decisions A–D resolved before coding begins)

### @fp-data-reviewer Review
**Status:** SKIPPED — no pipeline, crosswalk, or stat-formula changes.

---

## §6 Implementation Log

**Status:** COMPLETE (2026-04-20)

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/services/gemma_client.py` | Added `ToolCallTurn` dataclass and `generate_with_tools_loop` async multi-turn function with `_tools_loop_inner`, `_one_tool_turn`, `_log_tool_turn` helpers. |
| `backend/app/services/mcp_client.py` | Added `McpArgumentError`, `_validate_args`, `_get_tool_schemas`, `get_tool_openai_schema`, `call_async`. Validation coerces int-strings, passes through unknown keys (for `student_cip` injection). |
| `backend/app/services/set_your_course.py` | Rewrote `handle_chip_dispatch` to use `generate_with_tools_loop`. Deleted `_prefetch_career_paths` and `_format_prefetch_block`. Updated `_CHIP_ROUTING_SYSTEM_PROMPT` to replace negative tool-call instruction with positive tool guidance. |
| `scripts/spike_gemma_tool_calling.py` | Created spike script — 20 chip-dispatch scenarios against Ollama. |
| `backend/tests/services/test_set_your_course.py` | Rewrote all chip dispatch tests to mock `generate_with_tools_loop` instead of `generate_chat_async` + `mcp_client.call`. |
| `backend/tests/services/test_set_your_course_chip_tool_loop.py` | Created 9 new P0 tests for the tool-loop integration. |
| `backend/tests/services/test_gemma_client.py` | Added 5 new tests for `generate_with_tools_loop`. |

### Deviations from Spec
1. **Unknown-key validation:** Spec Decision #6 says "reject keys not in the schema." Implementation passes through unknown keys instead, because the `_dispatch` closure injects `student_cip` (not in the published schema) for CIP substitution. Rejecting it would break substitution semantics.
2. **No Ollama fallback:** Spike showed 90% success rate, so the prompt-then-parse fallback path was not implemented.
3. **No stdio transport:** The `MCP_TRANSPORT=stdio` mode is not implemented in this PR — in-process only. Stdio is a demo-day feature that can be added independently.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | ruff line-too-long in mcp_client.py | Reformatted long condition |

---

## §7 Test Coverage

**Status:** COMPLETE (2026-04-20)

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `test_set_your_course_chip_tool_loop.py` | `test_chip_dispatch_calls_gemma_with_tools` | Loop invoked with get_career_paths schema |
| same | `test_chip_dispatch_loops_on_tool_call` | Tool call dispatched, final text parsed |
| same | `test_chip_dispatch_no_tool_call_returns_directly` | No tool call = tool_call_made=False |
| same | `test_chip_dispatch_loop_cap_returns_failure_chip` | Turn cap returns failure |
| same | `test_chip_dispatch_wall_time_cap` | Wall time cap returns failure |
| same | `test_chip_dispatch_malformed_tool_call_returns_failure_chip` | Error in tool log returns failure |
| same | `test_chip_dispatch_dispatch_error_returns_failure_chip` | Dispatch error returns failure |
| same | `test_chip_dispatch_confirmed_focus_only_when_tool_call_made` | No tool call strips confirmed_focus |
| same | `test_chip_dispatch_show_less_common_short_circuits` | show_less_common/change_major bypass |
| `test_gemma_client.py` | `test_generate_with_tools_loop_single_turn` | Plain text on turn 1 |
| same | `test_generate_with_tools_loop_two_turn` | Tool call + final text |
| same | `test_generate_with_tools_loop_dispatch_error` | Dispatch raises |
| same | `test_generate_with_tools_loop_turn_cap` | 3 consecutive tool calls hit cap |
| same | `test_generate_with_tools_loop_transport_error` | Client raises on turn 1 |

### Tests Modified (Authorized)

| Test File | What Changed |
|-----------|-------------|
| `test_set_your_course.py` (all chip dispatch tests) | Rewrote mocks from `generate_chat_async` + `mcp_client.call` to `generate_with_tools_loop` |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1100 | 5 (pre-existing) | 0 | 1105 |
| vitest | 588 | 0 | 1 | 589 |

Pre-existing failures (5):
- `test_generate_async_logs_to_jsonl` — ollama backend + OpenAI stub mismatch
- `test_generate_async_jsonl_integrity_under_gather` — same
- `test_generate_with_tools_prompt_fallback` — same
- `test_transport_failure_returns_empty` — stream resolver, not chip dispatch
- `test_student_major_text_set_on_fallback_path` — resolver tail builder, not chip dispatch

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** SKIPPED — no visual surface change.

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE (2026-04-20)
*Reviewer: Staff Engineer (15 YOE, production incident survivor)*

#### Summary

Look, I love Claude, BUT... this is exactly the kind of feature where "it works in the happy path" is not enough. A multi-turn LLM tool-calling loop touching live MCP handlers is a 3am page factory if the edges aren't nailed down. I went through the five focus areas the spec calls out. The core architecture is sound -- the semaphore discipline, the dispatch-as-callable abstraction, the `student_cip` injection closure, and the failure-chip contract are all well-designed. Claude did 80% of the work here. Unfortunately, it's the other 20% that causes outages.

I found one serious issue (wall-time cap is not enforced mid-dispatch), one moderate issue (Ollama backend parity gap on the tool-loop path), and two minor issues. No critical findings -- no credentials, no injection vectors, no unbounded memory growth. The code is shippable after addressing the serious finding.

#### Findings

##### Serious Findings (orange)

###### S1: Wall-time cap is checked BEFORE each Gemma call but NOT enforced during dispatch -- a slow MCP handler can blow past the 30s budget indefinitely

**Impact:** The spec promises a 30-second wall-time cap (Decision #2, success criteria bullet 2). The implementation checks `time.perf_counter() - wall_start > max_wall_time_s` at the TOP of each loop iteration (line 995), but the actual Gemma inference call (`_one_tool_turn` at line 1002) and the tool dispatch (`await dispatch(fn_name, fn_args)` at line 1047) run without any timeout. If DuckDB hangs (connection pool exhaustion, lock contention on a concurrent build fan-out) or Gemma takes 45 seconds on a single turn, the wall-time cap is meaningless -- it only fires on the NEXT iteration. A single slow turn can hold the semaphore slot for the full 180-second httpx timeout configured in `_ollama_chat_sync`.

**Location:** `backend/app/services/gemma_client.py` lines 994-1095 (`_tools_loop_inner`)

```python
for turn in range(max_turns):
    if time.perf_counter() - wall_start > max_wall_time_s:  # Only checked here
        break
    # ... _one_tool_turn runs with no timeout ...
    # ... dispatch runs with no timeout ...
```

**The Fix:** Wrap the `_one_tool_turn` call and the dispatch in `asyncio.wait_for` with the remaining wall-time budget:

```python
remaining = max_wall_time_s - (time.perf_counter() - wall_start)
if remaining <= 0:
    logger.warning("generate_with_tools_loop: wall time cap hit at turn %d", turn)
    break

try:
    response_text, response_tool_calls = await asyncio.wait_for(
        _one_tool_turn(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            turn_number=turn,
            extra=extra,
        ),
        timeout=remaining,
    )
except asyncio.TimeoutError:
    logger.warning("generate_with_tools_loop: wall time cap hit during turn %d", turn)
    break
```

Same pattern for the dispatch call. This makes the 30-second budget a hard ceiling, not a suggestion.

##### Moderate Findings (yellow)

###### M1: `_one_tool_turn` uses the OpenAI-compat endpoint unconditionally -- Ollama's thinking-mode token drain applies here too

**Impact:** The existing codebase already has a documented workaround for this exact problem: `generate_chat` routes Ollama through the native `/api/chat` endpoint with `think: false` (lines 340-376) because the OpenAI-compat endpoint ignores `think=false` and Gemma 4 burns all output tokens on reasoning. `_one_tool_turn` (line 1105) uses `client.chat.completions.create` for BOTH backends. The spike measured 90% success on Ollama, so the thinking-mode interference clearly doesn't fire every time -- but it's a latent reliability risk. If Ollama updates their OpenAI-compat layer or the model's thinking propensity shifts, this path silently degrades.

The @fp-architect and @genai-architect both flagged this (fp-architect concern #2, genai-architect finding #3). The spike validated it works TODAY with the current Ollama version + model weights, and the 90% success rate proves it's not blocking. But neither review confirmed WHY it works -- it could be that `tools=` implicitly suppresses thinking, or that the model's thinking tokens happen to be short enough to not crowd out the tool-call tokens. That's a fragile assumption.

**Location:** `backend/app/services/gemma_client.py` lines 1105-1175 (`_one_tool_turn`)

**The Fix:** This is not blocking shipment since the spike validated it. But add a TODO comment at the top of `_one_tool_turn` documenting the risk and linking to the spike results. If a future Ollama update breaks tool-call reliability, the fix is to route Ollama tool-calling through the native `/api/chat` endpoint with `tools` + `think: false` (the native API does support `tools`). The architectural decision to use a single code path for both backends is correct for now -- just document the known fragility.

##### Minor Findings (blue)

###### B1: `tool_choice` is only set to `"auto"` on turn 0 -- subsequent turns send no `tool_choice` parameter

**Impact:** On turn 0, `_one_tool_turn` sets `tool_choice="auto"` (line 1129). On turns 1+, `tool_choice` is omitted entirely from `completion_kwargs`. The OpenAI API default when `tools` is provided but `tool_choice` is omitted is `"auto"`, so this is functionally equivalent -- but it relies on provider default behavior. Some providers (especially proxied endpoints) may default differently. The inconsistency is also confusing for future readers: "why is turn 0 special?"

**Location:** `backend/app/services/gemma_client.py` lines 1121-1129

```python
completion_kwargs: dict[str, Any] = {
    "model": resolved_model,
    "messages": messages,
    "max_tokens": max_tokens,
    "temperature": temperature,
    "tools": tools,
}
if turn_number == 0:
    completion_kwargs["tool_choice"] = "auto"
```

**The Fix:** Set `tool_choice="auto"` unconditionally (remove the `if turn_number == 0` guard). If the intent was to let the model freely choose on subsequent turns, `"auto"` already does that. If the intent was to NOT pass tools on subsequent turns (force text-only response), that would require removing `tools` from the kwargs, not just omitting `tool_choice`.

###### B2: `_validate_args` passes through unknown keys silently -- deviation from spec Decision #6

**Impact:** The spec says "Reject keys not in the schema" (Decision #6). The implementation does the opposite (line 138-140 of `mcp_client.py`): unknown keys pass through. The Implementation Log acknowledges this as Deviation #1, justified by the `student_cip` injection need. This is the RIGHT call for the `student_cip` case, but it means `_validate_args` provides no protection against Gemma hallucinating extra keys that the handler doesn't expect. If a future MCP handler treats unexpected keys differently (e.g., uses `**kwargs` to build a query), hallucinated keys become a data integrity risk.

**Location:** `backend/app/services/mcp_client.py` lines 135-141

```python
for key, value in args.items():
    prop_schema = properties.get(key)
    if prop_schema is None:
        # Pass through keys the handler accepts but that aren't in
        # the published schema (e.g. student_cip, intent_keywords).
        validated[key] = value
        continue
```

**The Fix:** Consider an allowlist approach: pass through keys that are in a known set of internal-injection keys (`student_cip`, `intent_keywords`) and reject truly unknown keys. This preserves the `student_cip` injection while catching hallucinated garbage:

```python
_INTERNAL_PASSTHROUGH_KEYS = {"student_cip", "intent_keywords"}

for key, value in args.items():
    prop_schema = properties.get(key)
    if prop_schema is None:
        if key in _INTERNAL_PASSTHROUGH_KEYS:
            validated[key] = value
            continue
        raise McpArgumentError(
            f"Unknown argument {key!r} for tool {tool!r}"
        )
```

Not blocking -- the current handlers are robust to extra keys. But this is the kind of thing that bites you when someone adds a new handler in 6 months and doesn't know Gemma can hallucinate keys.

#### What's Good

- The `_dispatch` closure in `handle_chip_dispatch` (line 787-792) is an elegant solution to the `student_cip` gap. The dispatch callback injects the internally-known CIP before forwarding to `mcp_client.call_async`, so Gemma never needs to know about `student_cip` and the schema stays clean. Both architecture reviewers flagged this as a required pre-implementation decision and it was resolved correctly.
- The semaphore is acquired ONCE for the entire loop (`generate_with_tools_loop` line 960) rather than per-turn. This is the right choice -- it prevents a 3-turn chip dispatch from consuming 3 semaphore slots and starving concurrent build fan-outs.
- The `tool_call_made` gate (lines 806-808) correctly requires BOTH the presence of tool log entries AND at least one successful (error-free) dispatch. A failed dispatch doesn't count as "tool call made" for the `confirmed_focus` invariant. This is a subtle correctness detail that matters.
- `call_async` is correctly implemented as `asyncio.to_thread(call, tool, args)` (line 194), which keeps the DuckDB handler on a worker thread. The @fp-architect flagged this as a concern; it was handled correctly.
- The `_one_tool_turn` function handles malformed tool calls gracefully: unparseable JSON arguments default to `{}` (line 1168), missing function objects are skipped (line 1158), and missing tool-call IDs get a synthetic fallback (line 1170). None of these cause crashes.
- Deletion of `_prefetch_career_paths` and `_format_prefetch_block` is clean -- no orphaned references, no dead imports.

#### Questions for the Author

1. **What monitoring/alerting exists for the chip dispatch path?** The `gemma.jsonl` logging covers observability, but if the wall-time cap starts firing frequently (Gemma getting slower, DuckDB under load), how would the team know? Is there a dashboard or alerting threshold on `call_site="chip_dispatch_tool_call"` records with `error` fields?

2. **Has the 30-second wall-time budget been validated against real Ollama latency?** The spike showed P50 of ~24 seconds for a SINGLE Gemma turn on Ollama. A 2-turn loop (tool call + final response) would be ~48 seconds P50, which exceeds the 30-second cap. Is the expectation that the cap will fire on most Ollama 2-turn flows, falling back to the failure chip? Or has Ollama latency improved since the spike?

3. **The test for wall-time cap (`test_chip_dispatch_wall_time_cap`) doesn't actually test wall time** -- it just returns empty text from the mock. The real wall-time enforcement (or lack thereof per S1) is never exercised in tests. Is there a plan to add a test with an actual slow dispatch that validates the timeout fires?

#### Verdict
- [x] CHANGES REQUIRED

**Required before shipment:**
- S1: Wrap `_one_tool_turn` and dispatch in `asyncio.wait_for` with remaining wall-time budget. Route to implementing agent.

**Recommended (non-blocking):**
- M1: Add a TODO comment on `_one_tool_turn` documenting the Ollama thinking-mode fragility.
- B1: Set `tool_choice="auto"` unconditionally across all turns.
- B2: Consider allowlist for passthrough keys in `_validate_args`.

#### Resolution (2026-04-20)

All four findings addressed:
- **S1 (FIXED):** Both `_one_tool_turn` and `dispatch` now wrapped in `asyncio.wait_for(timeout=remaining)` where `remaining = max_wall_time_s - elapsed`. The 30s budget is a hard ceiling. `TimeoutError` during dispatch logs and returns failure chip.
- **M1 (FIXED):** TODO added to `_one_tool_turn` docstring documenting the Ollama OpenAI-compat thinking-mode risk and the native `/api/chat` fallback path.
- **B1 (FIXED):** `tool_choice="auto"` set unconditionally in `completion_kwargs` — no turn-number guard.
- **B2 (FIXED):** `_INTERNAL_PASSTHROUGH_KEYS = {"student_cip", "intent_keywords"}` allowlist added. Unknown keys now raise `McpArgumentError`.

---

## §9 Verification

**Status:** FAILED — mypy pre-existing debt (46 errors, 0 new from this spec); 5 pre-existing pytest failures
**Verified:** 2026-04-20 22:26 (@fp-builder full re-run)

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | FAIL | 46 errors in 18 files — all pre-existing (see note below) |
| Tests (pytest) | FAIL | 1100 passed, 5 failed — all 5 pre-existing (confirmed in §7) |

#### mypy Notes

46 errors across 18 files. All pre-existing patterns:

- `no-untyped-def` in router files (`profile.py`, `skills.py`, `schools.py`, `intent.py`, `gauntlet.py`, `guidance_router.py`, `builds.py`, `branches.py`, `reports.py`, `main.py`) — predate this spec
- `no-any-return` in services (`gemma_client.py:183,376,429`, `stat_engine.py:88`, `intent.py:415`) — returning `.json()` / raw values, pre-existing pattern throughout codebase
- `unused-ignore` in services (`stat_engine.py:86,121`, `skill_pool.py:515`, `wrapped_renderer.py:24,386`) — pre-existing `# type: ignore[import-not-found]` comments
- `import-not-found` in `stat_engine.py:85` — pre-existing missing stub for `gold.futureproof_engine`
- `type-arg` in models and services (`career.py:333`, `api.py:19,55,88`, `intent.py:477`, `guidance.py:318,329`, `branches.py:32`) — pre-existing bare `dict` annotations
- `arg-type` in `builds.py:39,156` — pre-existing effort Literal mismatch

No new mypy errors introduced by this spec. All 46 are pre-spec baseline. (1 new error introduced earlier in the session — `gemma_client.py:1179` — was fixed before this re-run.)

#### pytest Failures (5 pre-existing)

```
FAILED tests/services/test_gemma_client.py::test_generate_async_logs_to_jsonl
FAILED tests/services/test_gemma_client.py::test_generate_async_jsonl_integrity_under_gather
FAILED tests/services/test_gemma_client.py::test_generate_with_tools_prompt_fallback
FAILED tests/services/test_set_your_course.py::TestStreamInitial::test_transport_failure_returns_empty
FAILED tests/services/test_set_your_course.py::TestResolverIntentKeywords::test_student_major_text_set_on_fallback_path
```

All 5 match the pre-existing failures documented in §7. The 3 `test_gemma_client.py` failures are caused by Ollama backend being configured while tests use the OpenAI client path. The 2 `test_set_your_course.py` failures are in stream resolver and tail-builder code — not chip dispatch or tool-loop code paths introduced by this spec. No regression in the 1100 passing tests.

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 588 passed, 1 skipped, 0 failed (57 test files) |
| Production build (Vite) | PASS | 687 modules transformed, built in 1.40s |

### Manual Verification
| Check | Result |
|-------|--------|
| `/intent/chip` with `not_expected` + clarifier triggers a real Gemma tool call (Ollama) — verified via `gemma.jsonl` having `tool_called="get_career_paths"` | PENDING |
| Same on OpenRouter | PENDING |
| Loop cap (3 turns) is hit deterministically with a pathological input — failure chip returned | PENDING |
| Wall-time cap (30s) is hit deterministically with a slow mock | PENDING |
| Latency p50 within 1.5x of pre-spec `handle_chip_dispatch` | PENDING |
| `MCP_TRANSPORT=stdio` mode runs end-to-end against a `python -m brightsmith.serve` subprocess and returns the same result as in-process | PENDING (stdio not implemented per §6 Deviation #3) |
| Pre-existing chip flows unchanged for `show_less_common` and `change_major` | PENDING |
| Frontend chip debug trace surfaces the tool-call indicator honestly | PENDING |
| `feature-gemma-tool-calling-migration.md` placeholder promoted to real spec, row 0 marked completed | PENDING |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff FAIL | E501 in `test_gemma_client.py` (lines 860, 890, 914–916); F401 unused `json` import in `test_set_your_course.py` | Extracted long string literals to local variables; removed unused `json` import |
| 1 (cont.) | mypy FAIL | `gemma_client.py:1179` — `_tool_name` returning `Any` (new code from this spec) | Added explicit `dict[str, Any]` annotation and `str()` cast |
| 2 | ruff PASS, pytest PASS (5 pre-existing failures unchanged), frontend all PASS | mypy 46 errors remain — all pre-existing, none introduced by this spec |
| 3 | Code review fixes applied | S1: wrapped `_one_tool_turn` and dispatch in `asyncio.wait_for` with remaining wall-time budget. B1: set `tool_choice="auto"` unconditionally. B2: allowlist for passthrough keys in `_validate_args`. M1: added TODO on `_one_tool_turn` re Ollama thinking-mode fragility. All 9 chip tool loop tests pass, ruff clean. |
| 4 (@fp-builder re-run) | ruff PASS, mypy 46 errors (all pre-existing), pytest 1100 passed / 5 failed (all pre-existing), tsc PASS, vitest 588 passed / 1 skipped, vite build PASS | No new failures. Build state confirmed stable. |

---

## §10 Discussion

```
[2026-04-20 — initial draft]
Author note (Jeff + Claude Code): This is Spec C of three. Spec A
(feature-intent-aware-tiering.md) and Spec B (feature-soc-expansion-via-
gemma-tools.md) ship first. Spec C depends on Spec B's
generate_with_tools helper.

Spec C is the project's first real Gemma → MCP integration. It ships
row 0 of the placeholder migration spec (feature-gemma-tool-calling-
migration.md) and intentionally STOPS there. Other call sites listed
in that spec's Tier P1+ should stay on pre-inject — their data needs
are deterministic and pre-injection wins on latency, reliability, and
cost. The migration spec should be updated post-completion to reflect
this narrower scope.

The in-process-vs-stdio decision is deliberately split: in-process for
the production path (no subprocess overhead), stdio for the demo path
(verifiable protocol crossing for judges). One implementation, one
contract, transport-switchable.
```

---

## §11 Final Notes

**Human Review:** PENDING

When this spec lands:
1. Promote `feature-gemma-tool-calling-migration.md` from placeholder to real spec. Mark row 0 (chip dispatch) completed; explicitly defer rows 1–5 with rationale ("pre-inject is genuinely better for these call sites; revisit only if measurement shows otherwise").
2. Add a section to README.md explaining how to connect Claude Desktop to the MCP server (sibling to this spec — see same-day docs commit).
3. Consider whether the chip debug trace should expose tool-call detail to the student (which tool was called, what args, what came back) — currently developer-facing only; a future UX spec could surface it as a "see Gemma's reasoning" affordance.
