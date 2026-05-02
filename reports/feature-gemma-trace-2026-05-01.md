# feature-gemma-trace — Completion Report

**Spec:** `docs/specs/feature-gemma-trace.md`
**Status:** COMPLETE
**Completed:** 2026-05-01

## What Shipped

A live, animated rendering of Gemma's multi-turn function-calling chain inside the Ask Gemma chat. The backend already produced this data — `generate_with_tools_loop` runs up to 3 turns of tool dispatch with 5 MCP tools — but the frontend was throwing the tool-call log away. This spec wires it up: opt-in callbacks emit per-turn events from the loop, an SSE endpoint streams them to the chat, and a new `<GemmaTrace>` component renders the rows live with a pedagogical-default / engineering-on-expand interaction pattern.

The result: judges watching the demo see Gemma reasoning in real time the way they recognize from Claude.ai / Cursor / ChatGPT, with the option to drill into args + result JSON to verify it's real function calling.

## How It Was Built

| Step | Outcome |
|------|---------|
| §5 Architecture Review (`@fp-architect`) | rev 1 → CHANGES REQUESTED (7 conditions: turn-index race, callback emission scope, exception handling, cancellation, backpressure, helper extraction completeness, missing test files). rev 1.1 → APPROVED. |
| §5 Architecture Review (`@genai-architect`) | rev 1 → CHANGES REQUESTED (2 required: symmetric callback emission, parser forward-compat; 3 recommended). rev 1.1 → APPROVED. |
| §3 Design Vision (`@fp-design-visionary`) | Pixel-perfect §3 spec landed with rail / header / row / engineering view / state matrix / motion presets / icon set / token references. 3 token additions proposed (`--color-bg-recessed`, `gemma-trace-pulse` keyframe, JSON theme). |
| Phase A (Backend, ~1 day) | 9 files changed (gemma_client, ask_gemma, ask_gemma_router, _sse helper, models/api, builds router, set_your_course router + tests). 1337 backend tests pass, 0 NEW mypy errors, ruff clean. |
| Phase B (Frontend, ~1.5 days) | 16 files changed (types, 6 icons + index, toolLabels + test, tokens.css + tailwind, index.css keyframe, menu.ts + stream test, GemmaTrace + test, GemmaChat integration + test, 3 screen test mocks). 773 frontend tests pass, tsc clean, Vite build green. |
| §8 Design Audit (`@fp-design-auditor`) | rev 1 → CHANGES REQUIRED (5 failures: focus ring, resolution-swap motion, header crossfade, custom opacity duration, live-region role). rev 2 → APPROVED. |
| §8 Code Review (`@faang-staff-engineer`) | APPROVED (no Critical/Significant; one Minor + 3 follow-ups). Queue lifecycle, backpressure handling, no-op verification, fallback correctness all PASS. |
| §9 Verification (`@fp-builder`) | ALL PASSED. ruff: clean. mypy: 0 new errors. pytest: 1337/1337. tsc: clean. vitest: 773/773. Vite: built in 1.58s. |

## Key Engineering Decisions

- **Symmetric one-place emission (Decision #12).** Both `on_turn_start` and `on_turn_event` callbacks fire from inside `_tools_loop_inner`. No router-side dispatch wrapper. Future callers of the loop (e.g. `feature-agentic-school-research.md` if revived) get both events for free.
- **`dispatch_index` row-correlation key (Decision #13).** Per-dispatch monotonic counter (= `len(tool_call_log)` at dispatch time). Unique even when Gemma issues parallel tool calls in one outer LLM turn. Both SSE event types carry it as their `turn` field.
- **Bounded queue, lossless (Decision #14).** `asyncio.Queue(maxsize=256)` with documented bound: max_turns(3) × max_tools(~5) × event_pairs(2) ≈ 30. ~8× headroom; bound structurally unreachable under the configured loop limits.
- **Forward-compat SSE parser (Decision #15).** `parseSSEFrame` returns `null` (never throws) on unknown event types. The reader loop continues. This is the seam that lets a future backend version add new event types without breaking older frontend bundles.
- **Silent visual fallback (Decision #7).** If SSE fails (HTTP error or thrown), `askGemmaStream` falls back to the existing `askGemma` and synthesizes turn_start + turn_complete pairs from `AskResponse.tool_calls`. `<GemmaTrace>` renders the two feeds identically. No error toast.

## Files Changed

**Backend (9):**
- `app/services/gemma_client.py` — `dispatch_index` + `tool_result_preview` on `ToolCallTurn`; `on_turn_start` + `on_turn_event` callbacks; `_invoke_callback` shim
- `app/services/_sse.py` — NEW shared `sse_event` helper
- `app/routers/builds.py` + `set_your_course.py` — both consume the shared helper now
- `app/models/api.py` — `TraceEventPayload`, `TraceTurnStart/Complete/FinalText/Done` + `TraceEvent` discriminated union; `AskResponse.tool_calls` enriched
- `app/services/ask_gemma.py` — `chat_ask_stream` async generator with bounded queue, try/except boundary, try/finally cancellation
- `app/routers/ask_gemma_router.py` — `POST /chat/ask/stream` endpoint
- 3 new test files (`test_sse.py`, `test_ask_gemma_stream.py`); test additions to `test_gemma_client.py`, `test_ask_gemma_router.py`

**Frontend (16):**
- `src/types/gemmaTrace.ts` — NEW types
- `src/components/menu/icons/` — NEW directory: 6 in-house SVG primitives + registry (`IconCareerCompass`, `IconBriefcaseStack`, `IconMapPin`, `IconScale`, `IconBranch`, `IconWrench`)
- `src/components/menu/toolLabels.ts` + `.test.ts` — NEW
- `src/styles/tokens.css` + `tailwind.config.ts` + `src/index.css` — `--color-bg-recessed` token + `gemma-trace-pulse` keyframe + `bg-bp-recessed` utility
- `src/api/menu.ts` — `parseSSEFrame`, `askGemmaStream`, fallback synthesis
- `src/api/menu.stream.test.ts` — NEW
- `src/components/menu/GemmaTrace.tsx` + `.test.tsx` — NEW
- `src/components/menu/GemmaChat.tsx` + `.test.tsx` — integrated
- 3 screen test mocks updated

## Test Counts

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 1337 | 0 | 0 | 1337 |
| vitest (frontend) | 773 | 0 | 0 | 773 |

## Build Verification

- ruff: clean
- mypy: 0 new errors (69 pre-existing in untouched modules — out of scope per `@fp-builder`'s baseline)
- tsc --noEmit: clean
- Vite production build: 1.58s, 729 modules transformed, 1,028 kB JS (304 kB gzipped), 81 kB CSS (15 kB gzipped)

## Known Follow-ups

- Live demo verification under both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` (Success Criterion left unchecked — manual step before judging).
- Code review's Minor finding: optional router-level catch-all for defense-in-depth around `chat_ask_stream` (non-blocking; the generator already cannot raise past its boundary per the C3 contract).
- DESIGN.md formal addition of the "Brightpath JSON / Data Preview Theme" subsection (the implementation uses the proposed values; the auditor accepted the deferred documentation).

## Hackathon Context

This was the cinematic move for the Gemma 4 Good hackathon (deadline 2026-05-18). Gemma's multi-turn function calling was already running in production but invisible to the user. Surfacing it as a recognizable agentic-AI demo pattern converts invisible work into a load-bearing demo moment without any new LLM capability investment. The component is built reusable so future surfaces (`feature-agentic-school-research.md`, build-creation trace) can drop it in.
