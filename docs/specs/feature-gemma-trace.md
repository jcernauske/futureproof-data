# Feature: Visible Gemma Tool-Call Trace in Ask Gemma Chat

## Claude Code Prompt

```
Read the spec at docs/specs/feature-gemma-trace.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 (event-emitter callback design,
     SSE event schema, request-scoped queue pattern, fallback path,
     impact on existing callers of generate_with_tools_loop).
   - Invoke @genai-architect ad-hoc to review the SSE event schema +
     callback signature for downstream extensibility (this trace
     primitive is intended to be reused by feature-agentic-school-
     research.md if/when revived; the contract has to hold).
   - This spec does NOT touch Bronze/Silver/Gold pipelines, ingestors,
     or DuckDB Gold-zone tables. SKIP @fp-data-reviewer.
   - Both reviewers write findings to §5 (Architecture Review).
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to propose the premium <GemmaTrace>
     component (live-streaming row reveals, per-tool iconography,
     pedagogical-default / engineering-on-expand interaction pattern,
     loading + complete + error states).
   - Visionary writes to §3 (UI/UX Design).
   - §3 becomes the pixel-perfect implementation target.
   - Reference Brightpath tokens by name. No hardcoded colors/spacing.

3. IMPLEMENTATION
   - Implement Phases A → B in order, as defined in §4.
   - BEFORE coding: review §4 Testing Impact Analysis thoroughly.
   - DURING coding: update only tests listed in "Authorized Test
     Modifications".
   - CRITICAL: If any test NOT in "Authorized Test Modifications"
     fails, STOP and escalate to human via §10.
   - Log all work to §6 (Implementation Log) with phase tags.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest)
     at the end of each phase.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3
     attempts). Otherwise escalate via §10.

4. TESTING
   - Invoke @test-writer to review the full spec.
   - @test-writer MUST review §4 Testing Impact Analysis.
   - Implement all tests listed in "New Tests Required" by priority.
   - Backend tests: pytest in backend/tests/.
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x).
   - Run ALL tests including the existing
     test_set_your_course.py / test_soc_expansion.py callers of
     generate_with_tools_loop / generate_with_tools — they must NOT
     break (the new callback param is opt-in).

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical Brightpath token/pattern
     compliance on <GemmaTrace> + GemmaChat integration.
   - Writes findings to §8 (Design Audit).
   - If CHANGES REQUIRED: route to implementer via §10.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
   - Particular attention to:
     * Request-scoped queue lifecycle (no leaks if client disconnects
       mid-stream)
     * SSE backpressure / cancellation handling
     * Existing-caller no-op verification (callback param defaults to
       None)
     * Fallback path correctness when SSE connection fails
   - Writes findings to §8 (Code Review).
   - If APPROVED: proceed to step 7. If CHANGES REQUIRED: route to
     originator via §10. If BLOCKER: STOP, alert human.

7. VERIFICATION
   - Invoke @fp-builder to run full build verification.
   - Backend: ruff check, mypy, pytest.
   - Frontend: TypeScript, vitest, Vite production build.
   - Log results to §9 (Verification).
   - If all green: mark status COMPLETE.

8. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Check off all completed Success Criteria in §1.
   - Update §6 Implementation Log, §7 Test Coverage, §8 Reviews.
   - Generate report to reports/feature-gemma-trace-YYYY-MM-DD.md.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-01 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.1 |
| Last Updated | 2026-05-01 (rev 1.1 — addressed @fp-architect C1–C7 and @genai-architect Items A, B, C, D from §5 review. Unified turn-index scheme via new `dispatch_index` field + symmetric `on_turn_start` callback fired from inside the loop. Added try/except + try/finally cancellation to `chat_ask_stream`. Picked backpressure strategy (b): bounded queue maxsize=256. Added second `_sse_event` extraction site (`set_your_course.py`). Expanded Testing Impact Analysis with three previously-missed test files. Added forward-compat parser requirement for unknown SSE event types. Added sync-callback ergonomics. Item E deferred to research-spec kickoff.) Earlier same date: Testing Impact Analysis expanded — screen tests at chat mount points need mock extension; `/branches` consolidated into `/future`; `BranchTreeScreen.test.tsx` removed from Test Impact Analysis. |
| Blocked By | — |
| Related Specs | `docs/specs/feature-agentic-school-research.md` (parked DRAFT — will reuse `<GemmaTrace>` if revived), `docs/specs/feature-ask-gemma.md` (existing chat surface), `docs/specs/cloud-gemma-deployment.md` (OpenRouter backend) |

---

## §1 Feature Description

### Overview
Surface Gemma's existing multi-turn function-calling chain as a live, animated trace in the Ask Gemma chat (`GemmaChat.tsx`). The backend already runs `generate_with_tools_loop` with five MCP tools per chat turn; the frontend currently throws away the tool-call log. This spec emits per-turn events from the loop via an opt-in callback, streams them over SSE to the chat, and renders them through a new reusable `<GemmaTrace>` component with hybrid pedagogical/engineering labels. No new Gemma capability, no new tools — only making the existing reasoning legible.

### Problem Statement
The Gemma 4 Good hackathon (deadline 2026-05-18, 17 days from today) judges on Gemma 4 capability. Multi-turn function calling is Gemma 4's headline feature, and FutureProof already does it in production: `backend/app/services/ask_gemma.py:302` calls `gemma_client.generate_with_tools_loop` with up to five MCP tools (`get_career_paths`, `get_occupation_data`, `get_regional_price_parity`, `compare_purchasing_power`, `get_career_branches`) and `max_turns=3`. The router returns the tool-call log in `AskResponse.tool_calls`. **The frontend literally ignores it** — `backend/app/models/api.py:189` reads: *"The frontend ignores `tool_calls`; it exists for telemetry and the routing/E2E test that asserts dispatch fired."*

So the wedge already exists. Gemma is doing impressive function-calling work and we are hiding it from both students and judges. The judge demo shows a chat that responds — they have no signal it is anything more than a wrapper. Making the chain visible converts invisible work into a recognizable agentic-AI demo pattern (Claude.ai, ChatGPT, Cursor all do this) without any new LLM capability investment.

This spec is the structural primitive on which a future `feature-web-search-in-chat.md` spec can layer additional tools (web_search, fetch_url) — but those are out of scope here. This spec is purely transparency.

### Success Criteria
- [x] When a student sends a message via Ask Gemma chat, the chat UI shows tool-call rows appearing **live** as Gemma issues each call — not collected at the end.
- [x] Each rendered row shows a pedagogical label by default (e.g. "Looking up career outcomes for IU Bloomington Marketing") with per-tool iconography. Click-to-expand reveals engineering detail: tool name, full args JSON, result preview JSON, duration ms.
- [x] All five tools in `ask_gemma._TOOLS` have entries in `TOOL_LABEL_MAP` with `{label, icon, hint}`.
- [x] If the SSE connection fails mid-stream, the chat falls back to the existing non-streaming `POST /chat/ask` and renders the trace post-hoc from `AskResponse.tool_calls`. **No visible error; the chat keeps working.** Same `<GemmaTrace>` component renders both feeds.
- [x] If a tool dispatch errors mid-chain, the chain row renders with an error pill but subsequent turns continue to render. The chat continues to render Gemma's final text.
- [x] If `tool_call_log` is empty (Gemma answered from context with no tool call), `<GemmaTrace>` is omitted entirely — no empty trace section, no header.
- [x] Existing callers of `generate_with_tools_loop` (`set_your_course.py`, `chat_ask`) and `generate_with_tools` (`soc_expansion.py`) are NOT modified at the call-site level. Both new callback parameters (`on_turn_start`, `on_turn_event`) default to `None` and are no-ops when unset. Existing tests pass unchanged except where the spec's Authorized Test Modifications table calls for compatibility tweaks (e.g., `**kwargs` audits on `fake_loop` patch signatures per C7).
- [x] `dispatch_index` field on `ToolCallTurn` is monotonically unique per dispatch (Decision #13). With parallel tool calls in one outer LLM turn, each appended `ToolCallTurn` has a distinct `dispatch_index`; SSE `turn` fields use it; `<GemmaTrace>` correlates rows by it. Verified by `test_dispatch_index_unique_across_parallel_calls`.
- [x] On client disconnect mid-stream, `loop_task` is cancelled within ~100ms and the Gemma semaphore is released before the wall-time cap (≤30s). Verified by `test_stream_cancelled_when_client_disconnects` (P0).
- [x] Frontend SSE parser silently skips unknown event types (returns null, never throws). Adding new SSE event types in a future spec does NOT break older frontend bundles. Verified by `test_unknown_event_type_returns_null_not_throw`.
- [x] `logs/gemma.jsonl` continues to record every Gemma call (existing telemetry contract). _(Verified by code inspection — `_log_tool_turn` continues to fire from inside the loop unchanged; the new callbacks fire after logging, never replace it.)_
- [ ] Behavior is identical under `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`. Demo path verified on both. _(Pending live demo verification — the loop's backend abstraction has no per-backend code path for the trace; verification is a manual demo step before judging.)_
- [x] `<GemmaTrace>` is a self-contained, reusable component with documented props — `feature-agentic-school-research.md` (parked) or future build-creation trace can drop it in without modification.
- [x] No new env vars, no new feature flag — pure UI surfacing of existing data, always-on.
- [x] Existing chat tests in `test_ask_gemma.py`, `test_ask_gemma_router.py`, `GemmaChat.test.tsx` continue to pass (with authorized minor mods documented in §4 Testing Impact Analysis).

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Surface scoped to **only** `GemmaChat.tsx` | Single demo move judges immediately recognize from Claude.ai / ChatGPT / Cursor. Backend already returns the data. One frontend integration vs. six. Fits the 17-day window comfortably with room to follow up. | Universal trace across all 14 Gemma services rejected (5–7 days, more risk). Build-creation trace deferred to a future spec; that surface already streams via SSE so adding the trace is a smaller follow-up once `<GemmaTrace>` exists. |
| 2 | **Live streaming via SSE** (not post-hoc reveal) | The cinematic shot is judges watching Gemma reason in real time. Post-hoc reveal looks like a UI gimmick. Build creation flow already proves the SSE pattern works (`routers/builds.py:226–377`). | Post-hoc-only rejected (loses the "watching Gemma work" magic). WebSockets rejected (heavier dependency, no benefit over SSE for unidirectional push). Polling rejected (laggy, wastes requests). |
| 3 | Backend capture pattern: **opt-in `on_turn_event` callback parameter on `generate_with_tools_loop`**, fired per turn | Cleanest minimal-blast-radius option. Existing callers pass nothing → no behavior change. Router provides a callback that pushes to a request-scoped `asyncio.Queue` which the SSE response drains. | Global wrapper around `gemma_client.generate*` rejected (touches every call site, unrelated risk). File-tail of `logs/gemma.jsonl` rejected (coupled to logger, no per-request filtering, racy). Per-router context manager rejected (boilerplate at every call site). |
| 4 | Hybrid **pedagogical-default + engineering-on-expand** labels | Two audiences served by one component. Students see "Looking up career outcomes for IU Bloomington Marketing"; judges click to see `get_career_paths(school_id="...", student_cip="52.1401")`. Lossless and friendly. | Pure engineering labels rejected (alienates students, jargon-y). Pure pedagogical rejected (judges can't verify Gemma is really doing function calling). |
| 5 | Translation layer (tool_name → label/icon) lives in **TypeScript**, not the backend payload | Cleaner separation. Frontend i18n compatible (translates per locale alongside `i18n/strings.ts`). No Gemma fingerprints in the user-friendly labels. Backend stays a faithful telemetry source. | Backend-rendered labels rejected (couples render concerns to API, blocks future i18n). Hardcoded labels in the component rejected (untestable per-key, harder to maintain). |
| 6 | `<GemmaTrace>` is **reusable** (built generic) even though only used in chat for v1 | Future surfaces (web-search-in-chat, build-creation trace, /my-build research) get the component for free. Marginal cost now (a few extra props), zero cost at integration time later. | Chat-specific component rejected (would need rewrite for any future surface; we'd regret it within the hackathon). |
| 7 | Failure modes are **silent visually**, never error toasts | The chat must continue to work even if streaming or a tool call fails. Trace is supplementary information; chat answer is primary. An error toast on a Gemma feature during the demo would be devastating. | User-visible error states rejected (UX cost > information value; backend logs are the right surface for failures). |
| 8 | **No new env var, no feature flag** | This is pure UI surfacing of data the backend already produces. Nothing to gate. Always-on simplifies code and demos. | Behind a flag rejected (no value to gating; flag-pollution real cost). |
| 9 | The new SSE endpoint is **`POST /chat/ask/stream`** (twin of existing `POST /chat/ask`), not a replacement | Existing `POST /chat/ask` stays untouched as the fallback path. Chat tries `/stream` first, falls back to `/ask` on connection failure. Same `AskRequest` body. | Replacing `/chat/ask` with SSE rejected (breaking change to existing tests and any future API consumer; fallback would need a separate endpoint anyway). |
| 10 | `ToolCallTurn` gains a new field `tool_result_preview: str` (truncated to 500 chars) | Engineering-detail expansion needs the actual result, not just `tool_result_size_bytes`. 500 chars is enough for a meaningful preview, small enough to keep `logs/gemma.jsonl` lean. | Adding full result rejected (oversized log records, PII risk if results grow). Returning size only rejected (engineering view is then useless, breaks the hybrid label promise). |
| 11 | SSE event schema mirrors the build-stream pattern exactly: `event: <name>\ndata: <json>\n\n` | Frontend already has a working consumer pattern at `frontend/src/api/build.ts:188+` (fetch + ReadableStream + decoder). Reusing the pattern means less new client code. | EventSource API rejected (POST body required for `AskRequest`; EventSource is GET-only). |
| 12 | **Both `turn_start` and `turn_complete` originate from inside `_tools_loop_inner`** via TWO callbacks (`on_turn_start`, `on_turn_event`) — not a router-side dispatch wrapper | Symmetric one-place emission. Any future caller of `generate_with_tools_loop` (e.g. `feature-agentic-school-research.md`'s `research_job.py`) gets both events for free without re-implementing a `_wrap_dispatch` shim. Eliminates the two-layer asymmetry flagged by @fp-architect (C1) and @genai-architect (Item A) during arch review. | Single-callback with `phase: "start"\|"complete"` field rejected — the "start" fire would carry empty `duration_ms`/`result_preview`/`error`, awkward shape. Router-side `_wrap_dispatch` (original spec) rejected — forced every reuse caller to repeat the pattern. |
| 13 | **Single per-dispatch index** (`dispatch_index`) is the unique key for SSE row correlation; loop's existing `turn_number` (outer LLM turn) preserved as a separate field on `ToolCallTurn` | Fixes C1 / Item A correctness defect: with parallel tool calls in one outer LLM turn, multiple `ToolCallTurn`s share `turn_number`, so the frontend can't pair `turn_start` ↔ `turn_complete` rows. `dispatch_index = len(tool_call_log)` at the moment of dispatch is monotonic across the entire chat turn — guaranteed unique, guaranteed ordering. SSE event `turn` fields use `dispatch_index`; the loop's `turn_number` stays for telemetry continuity (existing log records reference it). Also subsumes @genai-architect's Item C (parallel-call safety) — no separate `call_index` field needed. | Keeping `turn_number` as the SSE key rejected (race / wrong-pairing). Adding both `turn_number` AND `call_index` to SSE events rejected (two fields where one suffices). |
| 14 | **Bounded queue, lossless** — `asyncio.Queue[TraceEvent]` with `maxsize=256`; documented bound `max_turns(3) × max_tools_per_turn(~5) × event_pairs(2) = ~30` worst case | Fixes C5: original spec had a 64-cap with `await queue.put(...)` which BLOCKS on full (not raises), and the spec's "wrap in try/except" addressed raise-not-block. Worst-case event volume is ~30, so 256 is ~8× headroom; lossless trace preserved. | `put_nowait` + drop-on-full rejected (loses trace events visibly during the demo for no real-world benefit; the bound is not actually reachable). Unbounded queue rejected (no cap on memory; bad practice). |
| 15 | **Frontend SSE parser must return `null` (never throw) for unknown event types** | Forward-compat seam. Future event types (`thinking`, `final_text_delta`, `tool_partial_result`) added by later specs must not break the older deployed frontend. Verified by a dedicated vitest. Per @genai-architect Item B. | Throwing on unknown rejected (any future schema additive evolution becomes a breaking change). Strict version field on every event rejected (overkill for hackathon scope; discriminator union already gives per-event extensibility). |

### Constraints
- **Hackathon deadline 2026-05-18.** ~16 calendar days from spec draft. Spec sized for ~2.5 days of build.
- **Existing Gemma callers must not regress.** `set_your_course.py`, `soc_expansion.py`, all narrative generators using `generate*` — none touched.
- **`logs/gemma.jsonl` discipline preserved.** Every Gemma call still logged, no double-logging from the new callback.
- **Both inference backends supported.** Ollama and OpenRouter.
- **Brightpath design system** for all new UI. Dark-first. No hardcoded tokens.
- **No backend persistence.** Trace events live only in the request-scoped queue; nothing is written to DuckDB or anywhere else for v1. (`feature-agentic-school-research.md` may add persistence later if revived; this spec deliberately doesn't.)

### Out of Scope
- **Trace in any surface other than the Ask Gemma chat.** Build creation, /my-build, Set Your Course chip flow, boss narratives, wrapped frames — all deferred. The reusable component exists, but integration is not in this spec.
- **New tools.** No `web_search`, no `fetch_url`, no anything. Pure surfacing of existing five-tool registry.
- **Trace persistence / history.** Each chat session's trace is ephemeral. No "view previous Gemma sessions" feature.
- **Retroactive trace** for messages sent before this feature shipped. Only new chat turns get trace.
- **Server-driven label translation / i18n for trace.** v1 ships English-only labels in `TOOL_LABEL_MAP`. Localization comes when `i18n/strings.ts` does for the trace.
- **Streaming Gemma's *text* response token-by-token.** This spec streams tool-call EVENTS only. The final text answer arrives as one `final_text` event when Gemma finishes. Token streaming is a separate (much larger) feature.
- **Non-tool Gemma calls** (boss narratives, skill recs, etc.) — these don't go through `generate_with_tools_loop`, so the callback doesn't apply. Surfacing them is a separate "universal Gemma activity feed" spec, deferred.
- **Authentication / per-user trace.** No per-user state in this app per `feedback_profile_is_build.md`.
- **Tool-call replay / re-run from the trace.** Read-only display.

---

## §3 UI/UX Design

### Scope
- A new `<GemmaTrace>` component rendered inline within Gemma's chat response in `GemmaChat.tsx`. Position: between the chat user-message and Gemma's final-text response (or above the response). Visionary owns final placement.
- **Single-component change reaches three routes for free** because `GemmaChat` is mounted on each: `/my-build` (`BuildResultsScreen`), `/future` (`FutureScreen` — the consolidated career-tree surface; `/branches` is now a `Navigate` redirect to `/future` per `App.tsx:35`), and `/builds` (`MenuScreen`, plus embedded `CompareView` with compare-scope chat). All three surfaces inherit the trace behavior automatically — no per-route integration work, but per-route tests need mock updates (see §4 Testing Impact Analysis).
- Trace is opt-in by data: if `events` is empty (Gemma answered from context, no tool calls), component returns null — no header, no skeleton.
- Three states: **streaming** (events arriving live, more expected), **complete** (`done` event received, final text rendered), **fallback-mode** (post-hoc render from non-streaming response — visually identical to complete; no "fallback" badge).

### Design Intent

The emotion is **confident agentic-AI legibility**. The student should feel "Gemma is doing real work for me, and I can watch it happen." The judge should feel "this is the same agentic pattern I see in Claude.ai/Cursor, and I can drill in to verify it's real function calling, not generated text dressed up as tool calls."

`<GemmaTrace>` sits visually between two existing Gemma family members:

- The **Reasoning Card** (insight-striped surface, Gemma's voice talking out loud) is its container metaphor — same `border-left: 3px solid accent-insight` stripe says "this is Gemma's." Same right family.
- The **Tool-Call Indicator** chip (`⚙` glyph, info-tinted, `font-data`) is its row vocabulary — each row is a sibling of that chip, given a label, an icon, a status, and a click affordance.

`<GemmaTrace>` is the **multi-row, live-streaming, expandable cousin**. The student sees pedagogical sentences with friendly icons; the judge clicks and gets engineering detail in monospace + syntax-highlighted JSON. One component, two readings.

### Visual Spec — Container

The trace is **a contained insight-striped surface** that sits inline inside Gemma's chat bubble, above the final-text answer. It is **not** a card — chat bubbles are already cards; nesting a card inside a card reads as bureaucratic. It's a **rail**: a left-striped block with rows.

```
margin-top:    space-3                            /* 12px below the user's question echo / above the final text */
margin-bottom: space-4                            /* 16px gap to the final-text answer below */
padding:       space-3 space-4 space-3 space-4   /* 12px / 16px — generous on the left for the stripe to breathe */
background:    rgba(27, 29, 48, 0.5)             /* bg-deep @ 50% — half a step down from bg-mid; subtle dent inside the chat bubble. PROPOSED TOKEN: --color-bg-recessed (see Brightpath References) */
border:        1px solid border-subtle            /* rgba(255, 255, 255, 0.06) */
border-left:   3px solid accent-insight           /* THE Gemma stripe — identical to Reasoning Card */
border-radius: radius-lg                          /* 14px — slightly tighter than the parent chat-bubble's radius-xl so the trace nests visually */
shadow:        none                               /* recessed surface, no lift */
```

The stripe is the load-bearing identity choice. Anywhere the student sees a 3px `accent-insight` left edge, they are looking at Gemma's voice. The trace inherits that contract.

When the chat bubble is on the right (user) the trace is never rendered there. When the bubble is on the left (Gemma) the trace renders **above** the answer text, both inside the same bubble container.

### Visual Spec — Header

There is **a single header line** above the row list, mirroring the `GemmaThinking` attribution pattern. It does not say "Gemma's reasoning" or "Tool calls" — those words don't exist for the student. It says what Gemma is doing right now or what Gemma did.

```
display:       flex
align-items:   center
gap:           space-2                /* 8px between sparkle and text */
margin-bottom: space-3                /* 12px breathing room to row list */
font-family:   font-body              /* Nunito */
font-size:     text-small             /* 14px */
font-weight:   400
color:         text-secondary         /* #C4BFB0 — matches GemmaThinking attribution exactly */
```

Anatomy left-to-right: `<GemmaStar size={12} />` (existing primitive — info→insight gradient sparkle) + label text.

**Header copy by mode** (spec-locked — these strings ship; no paraphrasing):

| Mode | Streaming with ≥1 unresolved row | All rows resolved (Complete or Fallback) |
|------|-------------------------------|-------------------------------------------|
| Singular (1 row total) | `Gemma is looking something up…` | `Gemma checked one source.` |
| Plural (≥2 rows total) | `Gemma is looking things up…` | `Gemma checked {n} sources.` |

The streaming copy uses present-continuous (matches Gemma Interactions message conventions: in-flight = "Gemma is …ing"). The complete copy uses past tense (matches: resolved = "Gemma matched / found"). The word "sources" is intentional — friendlier than "tools" for students, accurate enough that judges still recognize it as tool-call vocabulary.

The header line itself is **never a toggle** — clicking it does nothing. Per-row expansion is the only interactive contract. Keeps the affordance map clean: header = label, row = button.

### Visual Spec — Row Default View

Each row is a **single-line clickable list item** with four zones, left to right: icon, pedagogical label, status pill, duration. The whole row is the click target.

```
display:        flex
align-items:    center
gap:            space-3                /* 12px between icon, label, status, duration */
min-height:     40px                   /* roomy enough for thumbs on mobile, dense enough to stack 3 rows in a desktop bubble without dominating */
padding:        space-2 space-2        /* 8px / 8px — minimal; the rail's 16px parent padding does the outer breathing */
border-top:     1px solid border-subtle /* first row: none */
border-radius:  radius-sm              /* 6px — only the hover/active background needs rounding; the row outline itself sits flush */
cursor:         pointer
transition:     background 150ms ease-out, color 150ms ease-out
```

**Row states:**

| State | Background | Affordances |
|-------|-----------|-------------|
| Default (resolved, idle) | transparent | hover-ready, click expands |
| Hover | `rgba(255, 255, 255, 0.04)` (the same wash used by Ghost Button hover) | cursor: pointer, label brightens to `text-primary` |
| In-progress (unresolved) | `--color-state-loading` (existing token: `rgba(184, 169, 232, 0.15)` — insight @ 15%) on the row only, full-width inside the rail | NOT clickable (`pointer-events: none`, no hover affordance, expansion disabled until resolved) |
| Expanded | `bg-mid` (`#232545`) — one step lifted from the rail's recessed background; signals "you opened this" | chevron rotated 90°, engineering panel rendered below |
| Error (resolved with error) | transparent (same as default — no red row, never punishing per Decision #7) | hover-ready, click expands; error indicator lives in the status pill |

**Row gap (between rows):** the `border-top: 1px solid border-subtle` creates the visual rule. No vertical gap between rows — they stack flush, separated only by the hairline. This is the List Item pattern from DESIGN.md (`border-bottom: 1px solid border-subtle` on rows in dropdowns and Path Cards). Same family.

**Expansion indicator:** a `▸` chevron glyph at the **far right**, after the duration micro-text. `font-data`, `text-micro` (12px), `text-muted`, `transition: transform 150ms ease-out`. Rotates `0deg → 90deg` on expand. Borrowed verbatim from the Disclosure Toggle primitive — same chevron, same rotation, same vibe ("more exists if wanted").

**Zone widths (desktop ≤640px chat-bubble width):**

```
┌──────────────────────────────────────────────────────────────────┐
│ [icon 20px] [pedagogical label, flex-1, truncate] [pill] [dur] [▸]│
│   gap-3        gap-3                              gap-3  gap-2 gap-2│
└──────────────────────────────────────────────────────────────────┘
```

The pedagogical label gets `flex: 1` and `min-width: 0` with `text-overflow: ellipsis` + `overflow: hidden` + `white-space: nowrap`. **It truncates with ellipsis at the end if the bubble is narrow.** The full sentence is preserved in the row's `aria-label`, the `title` attribute (browser tooltip), and visible in the engineering view's tool-name + args section. Truncation never hides information — it just defers it to expand or hover.

### Visual Spec — Row Engineering View

When a row is expanded, an inline panel slides open **below the row**, inside the same rail. It is the engineering view: tool name, args JSON, result preview JSON, full duration. Three audiences served — for the judge this is the verification surface ("yes, Gemma is really doing function calling"); for the implementer it doubles as a debugging tool; for the curious student it satisfies the "wait, what just happened" instinct without requiring a dev console.

```
margin-top:    space-2                /* 8px below the row */
margin-bottom: space-2                /* 8px above the next row's hairline */
padding:       space-3 space-4        /* 12px / 16px */
background:    bg-mid                 /* #232545 — one tier UP from the rail's recessed bg, not down — opening a row "lifts a card out" */
border:        1px solid border-subtle
border-radius: radius-md              /* 10px — input-field family; signals "data inside, not chrome" */
font-family:   font-data              /* Space Mono — entire panel is data-font; all human prose is in the row above */
overflow-x:    auto                   /* horizontal scroll for long JSON on mobile per Responsive Behavior */
```

**Panel anatomy (top-to-bottom, each row separated by `space-3` margin):**

1. **Tool-name field** — the canonical raw identifier.
   ```
   text-style:  font-data, text-data-sm (13px), font-weight: 700
   color:       accent-info  /* matches the Tool-Call Indicator chip color exactly */
   prefix:      "tool: " in text-muted, normal weight
   example:     tool: get_career_paths
   ```

2. **Args block** — labeled, syntax-highlighted JSON.
   ```
   label:       "args" in text-stat-label (10px Nunito 600 uppercase) text-muted, letter-spacing 1px, margin-bottom space-1
   body:        font-data, text-data-sm (13px), line-height 1.4
   indentation: 2 spaces (JSON.stringify with indent=2)
   max-height:  none (let JSON expand; the panel itself horizontal-scrolls if needed)
   ```
   Syntax theme: see "Brightpath JSON Theme" in §3 Brightpath References below. Keys in `text-secondary`, string values in `accent-thrive`, number values in `accent-caution`, boolean/null in `accent-insight`, brackets/punctuation in `text-muted`.

3. **Result preview block** — labeled, same syntax theme.
   ```
   label:       "result preview" in text-stat-label text-muted (matches "args" label exactly)
   body:        font-data, text-data-sm (13px)
   if truncated (≤500 chars per Decision #10): trailing "…" in text-muted, then on a new line:
                "(truncated to 500 chars · {full_size_bytes} bytes total)" in font-body text-micro text-muted italic
   if error:    label changes to "error" in accent-alert; body shows the error string in text-data-sm accent-alert (no JSON parsing). Result preview block is omitted entirely on error rows.
   ```

4. **Footer row** — full duration + correlation key (left-to-right, separated by middot in `text-muted`).
   ```
   text-style:  font-data, text-micro (12px)
   color:       text-muted
   format:      "238 ms · step {dispatch_index + 1} of {total}"
   ```
   Including the step index here gives the judge the explicit pairing back to the row above ("step 2 of 3") — important when multiple rows are expanded and the eye needs to map detail back to summary.

**Expansion entrance:** `<Collapsible>` content uses Framer Motion `height: auto` with `springs.smooth` (200/25). Opacity fades `0 → 1` over the same duration. The chevron in the parent row rotates synchronously. **Reduced-motion:** instant height swap, no opacity ramp, chevron snaps.

**No syntax-highlighting library dependency.** The five tools have small, deterministic arg shapes (≤6 keys, all strings/ints) and the result_preview is bounded to 500 chars. A 30-line `<JsonHighlight>` helper that walks the parsed object once and emits styled `<span>`s per token type is sufficient and keeps the bundle clean. If parsing fails (degenerate result), fall back to plain `text-secondary` monospace — never crash.

### Visual Spec — Icons

Five 16×16px stroked SVG icons, one per tool, authored in-house under `frontend/src/components/menu/icons/`. **No new icon-library dependency.** The Brightpath system already commits to in-house SVG primitives (`GemmaStar`, `GemmaSpinner`); a five-icon set fits that pattern exactly and keeps stroke weights, optical sizing, and the `currentColor` contract uniform with the rest of the visual language.

**Shared icon spec:**

```
viewBox:      0 0 16 16
size:         16px (configurable via prop, default 16)
stroke:       1.5px, currentColor
fill:         none (line icons — match the visual weight of GemmaStar's outlined sparkle)
stroke-linecap:  round
stroke-linejoin: round
color (default): accent-info  /* matches Tool-Call Indicator chip */
color (in-progress): accent-insight  /* the "Gemma is working" purple, syncs with the in-progress wash */
color (error): text-muted  /* errors are signaled by the status pill, not by re-coloring the icon — keeps the row scannable as "which tool" first, "what happened" second */
```

**The five tools and their commissioned icons** (each named to read at 16px without a label):

| Tool | Icon name | What the glyph looks like | Why it works |
|------|-----------|---------------------------|--------------|
| `get_career_paths` | `IconCareerCompass` | A four-pointed compass rose — N/S/E/W spokes radiating from a small filled center dot | Career *paths* — directionality. A compass says "navigation through possibility." The four spokes echo Gemma's `✦` four-pointed sparkle so it feels family. |
| `get_occupation_data` | `IconBriefcaseStack` | A briefcase silhouette with a small horizontal divider line across the body suggesting "layered records" | Occupation = the job. The briefcase is the universally-recognized job glyph. The divider line whispers "data record" without becoming a chart icon. |
| `get_regional_price_parity` | `IconMapPin` | A standard map-pin teardrop with a small inner ring | Regional = geography. A pin places the cost-of-living lookup geographically. The inner ring keeps it from reading as a generic location ping. |
| `compare_purchasing_power` | `IconScale` | A two-pan balance scale, beam horizontal, two dishes hanging | Compare = balancing two things against each other. The scale is the canonical comparison glyph; works equally well for "two states" or "two careers" if the tool ever generalizes. |
| `get_career_branches` | `IconBranch` | A short trunk that splits into two upward branches, mirroring the branch-tree wordless metaphor | Career *branches* — direct visual language match to the product's signature screen (Branch Tree). When a judge sees this icon they immediately know "Gemma is querying the branch tree data." Conceptual continuity. |

**Fallback icon** for any unknown tool name (defensive — should never appear in v1, but `feature-agentic-school-research.md` may add tools later): `IconWrench` — a generic line-drawn wrench. Echoes the `⚙` glyph in the existing Tool-Call Indicator. Color stays `accent-info`.

**Rendering contract:** each icon is a stateless React component that takes `{ size?: number; className?: string }` and uses `currentColor` for stroke, so it inherits color from the row's text-color cascade. No icon ever has a hardcoded color.

### State 1 — Streaming

The cinematic shot. New rows appear top-down as `turn_start` events arrive. Each row materializes in its in-progress state, then resolves in place when its matching `turn_complete` arrives.

**Per-event motion:**

1. **`turn_start` arrives →** new row mounts at the bottom of the list with the `transitions.fadeInUp` preset (opacity 0 + y:24 → visible, `springs.smooth` 200/25). The label is the pedagogical sentence; the icon color is `accent-insight`; the row background is the in-progress wash (`--color-state-loading`); no status pill yet, no duration, no chevron.

2. **In-progress shimmer (the long-shimmer-safe treatment):** a single, slow, gentle pulse on the icon and the row background — not a sweep, not a sheen. The icon opacity breathes `0.6 ↔ 1.0` on a **2.4s ease-in-out infinite** cycle. Defined as a new keyframe `gemma-trace-pulse` and a utility class `.animate-gemma-trace-pulse` (PROPOSED ADDITION to DESIGN.md keyframe table — see Brightpath References below). The breathing rate is intentionally slower than `card-breathe` (4s) and `chip-pulse-caution` (1.6s) so it never competes for attention — at 0.3s it reads as a gentle heartbeat, at 30s it reads as patient waiting. Reduced-motion: opacity holds at 0.85, no animation.

3. **`turn_complete` arrives →** the row resolves in place over a single coordinated 240ms transition:
   - Row background fades from `--color-state-loading` → transparent
   - Icon color crossfades from `accent-insight` → `accent-info` (success) or stays `accent-insight` then transitions to `text-muted` (error)
   - Status pill fades in (`opacity 0 → 1`, `springs.snappy` 400/25)
   - Duration micro-text fades in synchronously with the pill
   - Chevron fades in last (50ms after duration), signaling "now this is interactive"
   - The shimmer animation stops on the next animation frame after the pill's opacity reaches 1

   No layout shift during the swap — the row's height, gap, and zone widths are stable across in-progress and resolved states. The status pill and duration occupy reserved space (`min-width` set to the widest expected pill) that's invisible during in-progress.

4. **Status pill / pip:** a small `Pills / Badges` family member, sized down for the row context.
   ```
   display:       inline-flex
   align-items:   center
   gap:           space-1                /* 4px */
   padding:       2px space-2            /* 2px / 8px — smaller than the standard pill (5px / 14px) */
   font-family:   font-body              /* Nunito */
   font-size:     text-micro             /* 12px */
   font-weight:   600
   border-radius: radius-full
   ```

   | Variant | Background | Text/Glyph | Copy |
   |---------|-----------|-----------|------|
   | success | `rgba(125, 212, 163, 0.15)` (`pill-thrive` background) | `accent-thrive` | `◆ done` (filled-diamond glyph from the Feasibility Glyph convention — "the result is here") |
   | error | `rgba(244, 169, 126, 0.15)` (`pill-alert` background) | `accent-alert` | `◇ retry` (open-diamond — "the result isn't here, but the chat continues") |

   The pill text is **two characters of glyph + 4 characters of label**. Tight on purpose. The student doesn't need a verbose status; they need a glance-readable pip. The error pill is **`retry`** rather than `failed` because the next thing that happens — Gemma keeps reasoning, sometimes calls a different tool, sometimes answers from context — is conceptually a retry from the system's perspective. `failed` would imply finality; `retry` signals "this didn't return data and Gemma moved on." If a judge clicks the row, the engineering view has the actual error string in `accent-alert`.

5. **Duration micro-text:**
   ```
   font-family:  font-data        /* Space Mono — Brightpath's "this is real data" signal, exactly as advertised in the type-scale rationale */
   font-size:    text-data-sm     /* 13px */
   font-weight:  400
   color:        text-muted       /* faint, right-aligned */
   format:       "{n} ms" — integer, space, "ms" lowercase. Examples: "238 ms", "1240 ms", "12 ms"
   ```
   Always `ms`, never `s` even for long durations — keeps the visual rhythm uniform and the unit comparison effortless.

**Long-shimmer behavior:** at 5s, 10s, 30s elapsed, the row visually does not change. The icon continues breathing on its 2.4s cycle. The wall-time cap (≤30s) is enforced by the backend, not the component — when the cap fires, a `final_text` event arrives carrying the `chat_unavailable` message, the trace stays exactly as-is (rows in their last known state), and the final-text renders below. The unresolved row is **never auto-resolved by the frontend**; the contract is "the backend tells us what happened, we render what the backend tells us." A row that stayed in-progress is honest evidence that something hung.

**Stagger between consecutive `turn_start` events:** the natural cadence (1–4s between Gemma's tool calls) is its own stagger — there is no artificial delay added by Framer Motion. If two `turn_start` events arrive within the same animation frame (parallel tool calls in one outer LLM turn), each row uses the same `transitions.fadeInUp` preset; React Flow's natural mount ordering provides the visual stagger. This avoids artificial-feeling delays during fast Gemma responses.

### State 2 — Complete

`done` event has arrived. All rows are resolved. The header copy swaps from streaming present-continuous (`Gemma is looking things up…`) to past tense (`Gemma checked 3 sources.`). The header swap uses a 200ms opacity crossfade — gentle enough to not pull attention, present enough to confirm "the work finished."

Final-text renders **below** the trace, with `space-4` (16px) gap between the trace's bottom border and the first character of the answer. The trace **persists, fully expanded as a row list, above the answer for the lifetime of the chat session** — it does not collapse into a "Used 3 tools" one-liner. The reasoning behind that choice:

1. The trace is the demo. Hiding it after completion defeats the cinematic purpose.
2. The chat is short-form by nature — a typical Gemma answer is 1–4 sentences. The trace adds 3 rows × 40px = 120px above it. That's not bulky; it's framing.
3. Per-row engineering-view expansion remains live for the entire session. A judge can scroll back to a previous turn and click a row to verify Gemma's tool calls there too.

**Per-row interactivity in Complete state:** identical to the resolved-row state during streaming. Hover, click-to-expand, chevron rotation, engineering panel — all behave the same. The component does not differentiate "this row resolved 200ms ago" from "this row resolved 30 minutes ago." Stateless after resolution.

### State 3 — Fallback (post-hoc)

Visually **identical** to State 2 (Complete). Same header, same row list, same expansion behavior, same engineering view. **No "fallback" indicator visible to the user** — silent per Decision #7.

The only behavioral difference: rows are mounted in their resolved state immediately, with **no streaming entrance animation**. The trace renders all rows synchronously in their final form. Header reads in past tense from the start (`Gemma checked 3 sources.`), since there was never a streaming phase from the user's perspective.

This visual parity is a hard contract. If the SSE path ever diverges visually from the fallback path, the demo becomes brittle ("what happened, did something break?"). Both paths render through the same component with the same `mode="complete"` (or equivalent) prop. The streaming entrance is gated on `mode === "live"` and the row's `inProgress` flag — fallback rows arrive with `inProgress: false` and skip the animation branch entirely.

### Motion Presets

All motion uses **named Brightpath presets** from `frontend/src/styles/motion.ts`. No custom durations, no custom easings.

| Animation | Preset | Source |
|-----------|--------|--------|
| Row entrance (streaming, `turn_start`) | `transitions.fadeInUp` (opacity 0 + y:24 → visible, `springs.smooth`) | DESIGN.md Motion System → Common Transitions |
| In-progress icon + row pulse | `gemma-trace-pulse` keyframe (2.4s ease-in-out infinite, opacity 0.6 ↔ 1.0) | NEW — see Brightpath References below |
| Status pill + duration fade-in (resolution swap) | `springs.snappy` on opacity 0 → 1, 240ms total coordinated swap | DESIGN.md Motion System → Spring Configurations |
| Chevron rotation (expand/collapse) | `transition-fast` (150ms ease-out) on `transform` | DESIGN.md Transitions & Timing |
| Engineering panel height (expand/collapse) | `springs.smooth` on `height: 0 ↔ auto` + opacity 0 ↔ 1 | DESIGN.md Motion System → Spring Configurations |
| Header copy swap (streaming → complete) | 200ms opacity crossfade | DESIGN.md Transitions & Timing → `transition-normal` |
| Hover background fill | `transition-fast` on `background` | DESIGN.md Transitions & Timing |

**Reduced motion:** the component fully respects `prefers-reduced-motion: reduce` (DESIGN.md global contract — "All animations respect prefers-reduced-motion: reduce — keyframes hold at their resting frame"). Specifically:

- `transitions.fadeInUp` collapses to instant opacity-only (no y-translate)
- `gemma-trace-pulse` holds at opacity 0.85 (no breathing)
- Resolution-swap pill/duration fade-in becomes instant
- Chevron rotation becomes instant
- Engineering panel height swap becomes instant (no spring, no opacity ramp)

### Final-Text Relationship

The trace and the final-text answer **coexist**, both inside the same chat bubble container. Order top-to-bottom:

```
┌─ Gemma chat bubble (existing, unchanged) ─────────────────────┐
│                                                                │
│   ┌─ <GemmaTrace> rail ──────────────────────────────────┐   │
│   │ ✦  Gemma checked 3 sources.                          │   │
│   │                                                        │   │
│   │ [compass] Looking up career outcomes at IU…  ◆ done  238 ms ▸ │
│   │ [briefcase] Pulling BLS data for Marketing…  ◆ done  412 ms ▸ │
│   │ [pin] Checking cost-of-living for Indiana…   ◆ done   89 ms ▸ │
│   └────────────────────────────────────────────────────────┘   │
│                                                                │
│   Marketing graduates from IU Bloomington typically             │
│   land in roles like Brand Manager and Marketing Analyst…      │
│   {final-text answer in existing chat-bubble typography}        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

- The trace is **always above** the final text. Reading order matches reasoning order: Gemma looked up sources → Gemma synthesized an answer.
- Gap between trace bottom border and final-text first character: `space-4` (16px). Visual breathing room without disconnecting them.
- Per-row engineering expansion pushes the final text down. The chat scroll position should not auto-jump on expand — the user is reading the answer, the click was deliberate. (Implementation note for §4: don't `scrollIntoView` on expand.)
- If the trace is omitted (empty `events` per Scope), the final text renders in its existing position with no layout shift relative to non-trace messages. Adding `<GemmaTrace>` is purely additive when present, invisible when absent.

### Per-row visual structure
- Pedagogical label (default view): friendly sentence built from `TOOL_LABEL_MAP[tool_name].label` + `hint` template substituted with args. Example: tool=`get_career_paths`, args={school_id="iu-b", student_cip="52.1401"} → "Looking up career outcomes at Indiana University Bloomington for Marketing."
- Per-tool icon from `TOOL_LABEL_MAP[tool_name].icon` (visionary owns icon set selection / commission).
- Status indicator: in-progress shimmer / success pip / error pill.
- Duration (faint, right-aligned): "238 ms".
- Click anywhere on row → expand engineering detail: monospace `tool_name`, syntax-highlighted args JSON, syntax-highlighted truncated result JSON, full duration ms.

### Row Correlation Key
- `<GemmaTrace>` correlates `turn_start` and `turn_complete` events by their `turn` field, which is the backend's per-dispatch monotonic `dispatch_index` (Decision #13). One row per unique `turn`. A `turn_complete` swaps its matching `turn_start` row from in-progress → resolved. If a `turn_complete` arrives without a prior `turn_start` (degenerate stream), render it as a resolved row immediately.

### Long-shimmer Edge Case (Gemma transport failure)
Per @fp-architect M3: if Gemma's transport fails partway through a turn, the user sees the in-progress shimmer until the wall-time cap (≤30s) before the `chat_unavailable` fallback text appears. The visionary's "streaming" state visual must remain non-jarring at extended shimmer durations (no aggressive looping animation that becomes annoying after 5–10s). Suggest: gentle, slow pulse rather than a tight shimmer.

### Brightpath References

All visual values use existing Brightpath tokens by name. Three small additions are proposed where the system did not yet have a token for a need that was previously one-off; each is named and tabled here so `@fp-design-auditor` can track them and DESIGN.md can absorb them in a follow-up edit.

**Existing tokens used (no additions needed):**

| Use | Token |
|-----|-------|
| Rail border-left stripe | `accent-insight` (`#B8A9E8`) |
| Rail border ring | `border-subtle` (`rgba(255, 255, 255, 0.06)`) |
| Rail radius | `radius-lg` (14px) |
| Row hairline divider | `border-subtle` |
| Row in-progress wash | `--color-state-loading` (`rgba(184, 169, 232, 0.15)`) |
| Row hover background | `rgba(255, 255, 255, 0.04)` (Ghost Button hover wash — already in system) |
| Row expanded background (engineering panel parent row) | `bg-mid` (`#232545`) |
| Engineering panel background | `bg-mid` (`#232545`) |
| Engineering panel border | `border-subtle` |
| Engineering panel radius | `radius-md` (10px) |
| Header sparkle | `<GemmaStar size={12} />` (existing primitive) |
| Header text | `font-body`, `text-small` (14px), `text-secondary` |
| Pedagogical label text | `font-body`, `text-body-sm` (15px), `text-secondary` (default), `text-primary` (hover) |
| Tool name (engineering view) | `font-data`, `text-data-sm` (13px), 700, `accent-info` |
| JSON body (engineering view) | `font-data`, `text-data-sm` (13px), 400 |
| Args/result block labels | `font-body`, `text-stat-label` (10px), 600, uppercase, letter-spacing 1px, `text-muted` |
| Engineering footer (duration + step ref) | `font-data`, `text-micro` (12px), `text-muted` |
| Status pill — success | `pill-thrive` colorway (background `rgba(125,212,163,0.15)`, text `accent-thrive`) |
| Status pill — error | `pill-alert` colorway (background `rgba(244,169,126,0.15)`, text `accent-alert`) |
| Duration micro-text | `font-data`, `text-data-sm` (13px), `text-muted` |
| Chevron glyph | `▸`, `font-data`, `text-micro`, `text-muted` |
| Icon stroke color (default) | `accent-info` |
| Icon stroke color (in-progress) | `accent-insight` |
| Icon stroke color (error) | `text-muted` |
| Row entrance motion | `transitions.fadeInUp` |
| Resolution swap motion | `springs.snappy` on opacity |
| Expand/collapse motion | `springs.smooth` on height + opacity |
| Hover/chevron transition | `transition-fast` (150ms ease-out) |
| Header copy crossfade | `transition-normal` (200ms ease-out) |
| Focus ring (every clickable row + chevron + JSON copy actions) | `--color-focus-ring` (3px outline, 2px offset — global rule) |

**Proposed additions to DESIGN.md** (each is a NEW token; the implementer should add these to DESIGN.md and the Tailwind config alongside this feature, NOT inline-hack them):

| Token | Value | Rationale | Where added in DESIGN.md |
|-------|-------|-----------|--------------------------|
| `--color-bg-recessed` | `rgba(27, 29, 48, 0.5)` (bg-deep @ 50% over the parent surface) | The trace rail and the Reasoning Card both want a surface that reads as "recessed inside a chat bubble / inside a container" — currently both compute it inline as `rgba(27, 29, 48, 0.6)` / `0.5`. Promoting it to a token unifies them and gives future inset surfaces a name. | Backgrounds table, between `bg-deep` and `bg-mid` |
| `gemma-trace-pulse` keyframe + `.animate-gemma-trace-pulse` utility | `@keyframes { 0%, 100% { opacity: 0.6 } 50% { opacity: 1.0 } }`, 2.4s ease-in-out infinite, with reduced-motion override holding at opacity 0.85 | The in-progress row pulse needs a slower, gentler cadence than any existing keyframe. `card-breathe` (4s) is too slow and too loud (box-shadow), `chip-pulse-caution` (1.6s) is too fast for 30s tolerance, `gemma-shimmer` (320ms) is one-shot. The in-progress trace state needs its own named keyframe so other Gemma touchpoints (future "Gemma is generating an action plan" inline pulses) can reuse it. | CSS Keyframe Animations table, between `gemma-shimmer` and `chip-pulse-caution` |
| Brightpath JSON Theme | Six color roles: key=`text-secondary`, string=`accent-thrive`, number=`accent-caution`, boolean/null=`accent-insight`, brackets/punctuation=`text-muted`, error=`accent-alert` | DESIGN.md does not currently define a JSON or code-syntax theme. The trace's engineering view, the planned Reasoning Card debug overlay, and any future `feature-agentic-school-research.md` payload preview all need the same token mapping or they'll drift. Documenting it once now prevents three-way divergence later. | NEW subsection under Components, after "Tool-Call Indicator", titled "JSON / Data Preview Theme" |

If `@fp-design-auditor` rejects any proposed addition, the implementer falls back to inline values that match the proposed token's value byte-for-byte, and the auditor + visionary route the addition through a follow-up DESIGN.md edit before this spec ships. The values themselves are not negotiable; the question is only whether they get a token name.

### Responsive Behavior
- Desktop chat-bubble width (≤640px): rows stack vertically inside the bubble. Pedagogical label truncates with ellipsis; full text available via `title` attribute, `aria-label`, and the engineering view.
- Mobile (full-width chat bubble): identical row structure. Engineering-view expansion may horizontal-scroll for long arg/result JSON — that's acceptable per Decision #6's portability contract (the engineering view is the judge surface; a horizontal scroll on mobile is a fair tradeoff against shrinking the data font).
- The trace rail itself never shrinks below `min-height: 56px` (header + one row's worth of breathing room) so an empty-but-present trace does not collapse to a hairline. (Reminder: empty-events trace returns null entirely per Scope — this min-height guards transient one-row mid-render states.)
- Row min-height (`40px`) is tuned to hit the iOS Human Interface Guidelines 44pt target when the icon, label, pill, and duration are stacked together (the `space-2` row padding adds `8px × 2 = 16px` vertical, putting the effective tap-target at 56px).

### Accessibility

The accessibility identifiers and ARIA contract below are spec contracts established during architecture review — preserve verbatim. Design-specific notes follow.

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Trace root | `gemma-trace` | region | "Gemma's reasoning steps for this answer" (visionary may revise) |
| Chain row list | `gemma-trace-rows` | list | "Tools Gemma used" |
| Each row | `gemma-trace-row-{turn}` | listitem | "Step {turn+1}: {pedagogical label}, {status}" |
| Row expand toggle | `gemma-trace-expand-{turn}` | button | "Show technical detail for step {turn+1}" |
| Engineering detail panel | `gemma-trace-detail-{turn}` | region | `aria-expanded` toggled |
| Streaming live region | `gemma-trace-live` | status | `aria-live=polite` so screen readers announce new rows |

**Design-specific accessibility notes:**

- The whole row is the click target (per Visual Spec — Row Default View) but the **`<button>` semantic role** lives on a single inner element wrapping the row contents — not on `<div>`s with `role="button"`. The chevron is decorative (`aria-hidden="true"`), the icon is decorative (`aria-hidden="true"`), the pedagogical label is the accessible name, and the status pill text is appended to the label via the row's `aria-label` ("Step 2: Looking up career outcomes at IU Bloomington for Marketing, done in 238 ms"). Screen-reader users get the full sentence; sighted users get the truncated visual + tooltip.
- The in-progress row is **not focusable** (`tabindex={-1}`, `aria-disabled="true"`) — there's nothing to expand yet. Once resolved, focusability returns (`tabindex={0}`).
- The header line (`✦ Gemma is looking things up…`) is **not** in the live region. Only new resolved rows announce. Streaming starts/completes are otherwise too chatty for screen readers.
- Live-region announcements include the duration: "Step 1 of 3: Gemma looked up career outcomes at Indiana University Bloomington for Marketing — done in 238 milliseconds." Spelling out "milliseconds" in the announcement (not the visible "ms") matches assistive-tech reading conventions.
- The engineering panel is `role="region"` with `aria-labelledby` pointing to the parent row's label element. The JSON preview uses `<pre><code>` so screen readers can navigate it as a code block; readers that announce code-block boundaries will identify it as engineering detail rather than prose.
- Focus order on expand: focus stays on the row's button (does not jump into the engineering panel). The panel is reachable via `Tab` after the row. On collapse, focus returns to the row button. Standard Collapsible semantics.

### Frontend Library Reference
- **Framer Motion** for row entrance, status resolution swap, expand/collapse height animation.
- **shadcn/ui** for the expand/collapse mechanism (`Collapsible` component already in use elsewhere).
- No React Flow, no Recharts.

---

## §4 Technical Specification

### Architecture Overview

The feature has a tight backend → frontend seam:

1. **`gemma_client.generate_with_tools_loop`** gains an optional `on_turn_event` callback parameter. When set, fired once per turn with a `ToolCallTurn`. Existing callers pass nothing → unchanged behavior. The `ToolCallTurn` dataclass also gains a new field `tool_result_preview: str` (≤500 chars) so the trace can show what Gemma actually got back.

2. **`backend/app/services/ask_gemma.py`** gains a new `chat_ask_stream` async-generator coroutine that mirrors `chat_ask` but yields events as they happen. Internally, it constructs a request-scoped `asyncio.Queue[TraceEvent]`, passes a callback that puts events on the queue, and concurrently awaits `generate_with_tools_loop` while draining the queue and yielding events. On loop completion, yields the `final_text` and a `done` event.

3. **`backend/app/routers/ask_gemma_router.py`** gains a new endpoint `POST /chat/ask/stream` that wraps `chat_ask_stream` in a `StreamingResponse` with `text/event-stream`, using the existing `_sse_event` formatter (extracted to a shared helper since this is its second consumer). The existing `POST /chat/ask` endpoint is untouched.

4. **`AskResponse.tool_calls` shape is enriched** to include args + result_preview per row (currently only `tool / ok / duration_ms`). This powers the post-hoc fallback path: same `<GemmaTrace>` consumes either live SSE events or the enriched tool_calls list.

5. **Frontend `frontend/src/api/menu.ts`** gains an `askGemmaStream` function that POSTs to `/chat/ask/stream`, consumes the SSE stream via `fetch` + `ReadableStream` + `TextDecoder` (same pattern as `frontend/src/api/build.ts:188+`), and exposes events via an async iterator or callback. On connection failure, falls back to the existing `askGemma` and reconstructs trace events from `AskResponse.tool_calls`.

6. **Frontend `<GemmaTrace>` component** is a new reusable component under `frontend/src/components/menu/`. Takes `events: GemmaTraceEvent[]` (a live-updated array) and `mode: "live" | "complete"`. Renders rows, handles per-row expand. Pure presentation — no API calls.

7. **`GemmaChat.tsx` integration** swaps the `askGemma` call for `askGemmaStream`, accumulates events in local state as they arrive, and renders `<GemmaTrace>` above Gemma's final response message.

The contract is: the trace component cares only about the event shape; the API layer chooses live or post-hoc; the backend cares only about emitting events when asked. Each layer is independently testable and replaceable.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/gemma_client.py` | Modify | Add two fields to `ToolCallTurn` dataclass: `tool_result_preview: str = ""` and `dispatch_index: int = 0` (per-dispatch monotonic — see Decision #13). Add TWO optional kwargs to `generate_with_tools_loop`: `on_turn_start: Callable[[int, str, dict[str, Any]], Awaitable[None] \| None] \| None = None` and `on_turn_event: Callable[[ToolCallTurn], Awaitable[None] \| None] \| None = None`. Inside `_tools_loop_inner`, immediately before `await asyncio.wait_for(dispatch(fn_name, fn_args), ...)` at line 1069, capture `dispatch_index = len(tool_call_log)` and fire `on_turn_start(dispatch_index, fn_name, fn_args)`. After `tool_call_log.append(ToolCallTurn(..., dispatch_index=dispatch_index))` at line 1090, fire `on_turn_event(turn_obj)`. Both callback invocations: (a) wrapped in `try/except Exception` — exception is logged at WARNING and swallowed so loop continues (per Decision #14: trace is supplementary, never breaks Gemma); (b) detect sync vs async via `asyncio.iscoroutine` on the return value (per Item D: cleaner test fixtures). Populate `tool_result_preview` (≤500 chars) from the truncated result string already computed for logging. |
| `backend/app/services/ask_gemma.py` | Modify | Add `chat_ask_stream(...) -> AsyncIterator[TraceEvent]` coroutine. Same setup as `chat_ask` (system prompt, tool schemas, dispatch). Builds request-scoped `asyncio.Queue[TraceEvent]` with `maxsize=256` (Decision #14). Schedules `generate_with_tools_loop` as a task, passing BOTH `on_turn_start` (enqueues `TraceTurnStart`) and `on_turn_event` (enqueues `TraceTurnComplete`). While loop runs, drain queue and yield events. Wraps drain loop in `try/finally`: cancels `loop_task` and awaits its completion via `asyncio.gather(..., return_exceptions=True)` to ensure no orphaned Gemma work / leaked semaphore on client disconnect (C4). After drain completes, awaits `loop_task` inside `try/except Exception` (C3): on exception, yields `TraceFinalText(chat_unavailable)` + `TraceDone` and returns. Also updates `chat_ask` to populate enriched `TraceEventPayload` shape in `AskResponse.tool_calls` so the fallback path has the same data. |
| `backend/app/routers/ask_gemma_router.py` | Modify | Add `POST /chat/ask/stream` endpoint. Mirrors existing `chat_ask` setup (load builds via `asyncio.to_thread(builds.load_build)`), then wraps `ask_gemma.chat_ask_stream(...)` in `StreamingResponse(media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`. Uses shared `sse_event` helper. |
| `backend/app/services/_sse.py` | Create | Extract `sse_event(event: str, data: Any) -> str` into a shared helper (see service-changes section). Single source of truth for the SSE format. |
| `backend/app/routers/builds.py` | Modify | Replace local `_sse_event` definition (lines 226–228) with `from app.services._sse import sse_event`. Update call sites accordingly. |
| `backend/app/routers/set_your_course.py` | Modify | (C6) Replace local `_sse_event` definition (lines 38–41 — byte-identical to the one in `builds.py`) with `from app.services._sse import sse_event`. Update call sites accordingly. |
| `backend/app/models/api.py` | Modify | (a) Update `AskResponse.tool_calls` element schema (currently `dict[str, Any]`) — add new `TraceEventPayload` Pydantic model with `turn`, `tool`, `args`, `result_preview`, `duration_ms`, `error` fields, and type `tool_calls: list[TraceEventPayload]`. Update the docstring at line 186–190 to reflect that the frontend NOW reads tool_calls. (b) Add `TraceEvent` discriminated-union model used by the SSE wire format. |
| `backend/app/services/ask_gemma.py` | (already in row above) | (Documenting again here since it changes both behavior and exports — `chat_ask` builds the enriched `AskResponse.tool_calls` from `tool_call_log` so the fallback path has the same data the streaming path emits.) |
| `frontend/src/api/menu.ts` | Modify | Add `askGemmaStream(request: AskRequest, onEvent: (e: GemmaTraceEvent) => void): Promise<{response: string, events: GemmaTraceEvent[]}>`. POSTs to `/chat/ask/stream`, consumes `fetch().body.getReader()`, parses SSE lines, dispatches per-event callbacks. On connection failure (HTTP error or thrown), catches, falls back to existing `askGemma`, synthesizes events from `tool_calls` array, fires onEvent for each in order, returns final shape. |
| `frontend/src/types/gemmaTrace.ts` | Create | TypeScript types: `GemmaTraceEvent` (discriminated union: `turn_start`, `turn_complete`, `final_text`, `done`), `TraceMode`, `ToolLabel`. Mirrors backend `TraceEvent` shape. |
| `frontend/src/components/menu/GemmaTrace.tsx` | Create | The reusable trace component. Props: `events: GemmaTraceEvent[]`, `mode: "live" \| "complete"`. Internal state: per-row expanded flags. Handles all three states from §3. |
| `frontend/src/components/menu/GemmaTrace.test.tsx` | Create | vitest covering: empty events → null, streaming state row reveal, complete state, fallback-mode (post-hoc), per-row expand, error pill rendering, accessibility identifiers. |
| `frontend/src/components/menu/toolLabels.ts` | Create | `TOOL_LABEL_MAP: Record<string, ToolLabel>` for the 5 tools in `ask_gemma._TOOLS`. Each entry: `{label, icon, hint}`. `hint` is a template-string function that takes args and returns the pedagogical sentence. Single source of truth for label translation. |
| `frontend/src/components/menu/toolLabels.test.ts` | Create | vitest covering: every tool name in `_TOOLS` has a label entry; hint templates render correctly with realistic args; unknown tool names fall back to a sane default ("Gemma is consulting a tool"). |
| `frontend/src/components/menu/GemmaChat.tsx` | Modify | Swap the `askGemma` call for `askGemmaStream`. Add local state `traceEvents: GemmaTraceEvent[]` accumulating as events arrive. Render `<GemmaTrace events={traceEvents} mode={isStreaming ? "live" : "complete"} />` above Gemma's response message in the chat bubble. Visionary owns exact placement. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | Modify | Add tests for trace rendering integration. Update existing `askGemma`-mocking tests to also cover `askGemmaStream` happy path. Per "Authorized Test Modifications" in §4. |
| `frontend/src/i18n/strings.ts` | Modify | Add any user-visible static strings introduced by `<GemmaTrace>` (header text if any, accessibility labels). Visionary owns final copy. |
| `backend/tests/services/test_gemma_client.py` | Modify | Add tests for `on_turn_event` callback firing per turn, with correct `ToolCallTurn` shape. Verify default `None` is no-op. Verify `tool_result_preview` is populated and truncated. |
| `backend/tests/services/test_ask_gemma.py` | Modify | Add tests for `chat_ask_stream` happy path, partial-stream + transport failure, tool-error mid-chain. Existing tests for `chat_ask` must continue to pass. |
| `backend/tests/services/test_ask_gemma_stream.py` | Create | Dedicated tests for the new generator: event ordering, final_text + done emission, queue lifecycle, cancellation when client disconnects. |
| `backend/tests/routers/test_ask_gemma_router.py` | Modify | Add tests for `POST /chat/ask/stream` endpoint: SSE format, all event types, content-type headers, 404 on bad build_id, error mid-stream behavior. Existing `POST /chat/ask` tests unchanged. |
| `backend/tests/services/test_sse.py` | Create | Unit tests for the extracted `_sse_event` helper — JSON serialization, event-name escaping, default-encoder behavior. |

### Data Model Changes

#### Backend — `gemma_client.py`

```python
@dataclass(frozen=True)
class ToolCallTurn:
    turn_number: int                  # outer LLM-turn index — preserved for telemetry continuity
    tool_name: str
    tool_args: dict[str, Any]
    tool_result_size_bytes: int
    tool_result_preview: str = ""     # NEW — truncated to 500 chars
    duration_ms: int = 0
    error: str | None = None
    dispatch_index: int = 0           # NEW — per-dispatch monotonic; unique key for SSE row correlation (Decision #13)
```

Note on field ordering: defaults are added in trailing positions only. Existing kwargs-style construction across call sites and tests stays compiling without modification (verified: `gemma_client.py:1090`, `tests/services/test_set_your_course_chip_tool_loop.py:103`, `tests/routers/test_ask_gemma_router.py:718` all use kwargs).

Updated signature (TWO new opt-in callbacks per Decision #12 — symmetric one-place emission):

```python
TurnStartCallback = Callable[[int, str, dict[str, Any]], Awaitable[None] | None]
TurnEventCallback = Callable[[ToolCallTurn], Awaitable[None] | None]


async def generate_with_tools_loop(
    *,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    dispatch: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]],
    max_turns: int = 3,
    max_wall_time_s: float = 30.0,
    temperature: float = 0.0,
    max_tokens: int = 600,
    extra: dict[str, Any] | None = None,
    on_turn_start: TurnStartCallback | None = None,   # NEW — fires before dispatch await
    on_turn_event: TurnEventCallback | None = None,   # NEW — fires after tool_call_log.append
) -> tuple[str, list[ToolCallTurn]]: ...
```

Emission contract (clarifies C2 — fires only on appended `ToolCallTurn`s, never on final-text or transport-error branches):

- `on_turn_start(dispatch_index, fn_name, fn_args)` is fired inside `_tools_loop_inner` **immediately before** `await asyncio.wait_for(dispatch(fn_name, fn_args), ...)` at line 1069. `dispatch_index = len(tool_call_log)` captured at that instant — guaranteed unique even with parallel tool calls in one outer LLM turn.
- `on_turn_event(turn_obj)` is fired **immediately after** `tool_call_log.append(ToolCallTurn(..., dispatch_index=dispatch_index))` at line 1090. The appended turn carries the same `dispatch_index` so consumers can pair start↔complete by that key.
- Both callbacks are skipped on the transport-error branch (line 1030) and the plain-text-only branch (line 1043) — those branches do not append a `ToolCallTurn`. Final-text is surfaced via the loop's `(text, log)` return tuple, not the callback.

Callback invocation discipline (per Decision #14 + Item D):

- Each invocation is wrapped in `try/except Exception`. Exception is logged at WARNING level (`logger.warning("on_turn_*  callback raised: %s", exc)`) and swallowed — the loop continues, telemetry continues, the user-visible chat answer is not affected.
- The invocation shim accepts both async and sync callables: if the callback's return value is `inspect.iscoroutine(...)` truthy, it is awaited; otherwise discarded. This lets test fixtures use simple list-append spies without `async def` boilerplate.

Reasoning: a slow consumer should not stall Gemma; a broken callback should degrade gracefully to the post-hoc fallback path. The existing `_log_tool_turn` continues to fire unchanged — `logs/gemma.jsonl` discipline is preserved regardless of callback state.

#### Backend — `models/api.py`

```python
class TraceEventPayload(BaseModel):
    """One enriched tool-call entry for AskResponse.tool_calls — also
    the wire payload of `turn_complete` SSE events."""
    turn: int                         # dispatch_index — see Decision #13
    tool: str                         # raw tool name (e.g. "get_career_paths")
    args: dict[str, Any]
    result_preview: str               # truncated to 500 chars; "" on error
    duration_ms: int
    error: str | None = None


class AskResponse(BaseModel):
    """POST /chat/ask response body. ``tool_calls`` carries the
    enriched per-turn payload that powers <GemmaTrace>'s post-hoc
    (fallback) render. The frontend reads this when SSE is unavailable."""
    response: str
    tool_calls: list[TraceEventPayload] = Field(default_factory=list)


# SSE wire-format models (returned as JSON in `data:` field of each SSE frame).
# In ALL events, the `turn` field carries the per-dispatch monotonic
# `dispatch_index` (Decision #13). This is the unique key the frontend
# uses to correlate `turn_start` ↔ `turn_complete` rows. NOT the loop's
# outer LLM turn_number (which can be shared by parallel tool calls).

class TraceTurnStart(BaseModel):
    type: Literal["turn_start"] = "turn_start"
    turn: int                         # = dispatch_index at the moment Gemma issued the call
    tool: str
    args: dict[str, Any]


class TraceTurnComplete(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    turn: int                         # = dispatch_index of the matching turn_start
    tool: str
    args: dict[str, Any]
    result_preview: str
    duration_ms: int
    error: str | None = None


class TraceFinalText(BaseModel):
    type: Literal["final_text"] = "final_text"
    response: str


class TraceDone(BaseModel):
    type: Literal["done"] = "done"


TraceEvent = Annotated[
    TraceTurnStart | TraceTurnComplete | TraceFinalText | TraceDone,
    Field(discriminator="type"),
]
```

Note: `turn_start` is emitted **before** the tool dispatches (so the UI shows the in-progress shimmer with the right label); `turn_complete` after dispatch returns (so the UI swaps to resolved state). Both originate from inside the loop now (Decision #12), guaranteeing single-source emission. `final_text` carries Gemma's text answer. `done` is the trailer event signaling EOF — frontend can stop reading here. `final_text` and `done` are separate so the chat can render the final answer the moment Gemma finishes, before formally closing the SSE stream.

#### Frontend — `types/gemmaTrace.ts`

```typescript
export type ToolLabel = {
  label: string;                              // "Career outcomes lookup"
  icon: string;                               // icon identifier
  hint: (args: Record<string, unknown>) => string;  // pedagogical sentence builder
};

// `turn` in turn_start / turn_complete is the backend's dispatch_index
// (per-dispatch monotonic). Use it as the unique correlation key.
export type GemmaTraceEvent =
  | { type: "turn_start"; turn: number; tool: string; args: Record<string, unknown> }
  | { type: "turn_complete"; turn: number; tool: string; args: Record<string, unknown>;
      result_preview: string; duration_ms: number; error: string | null }
  | { type: "final_text"; response: string }
  | { type: "done" };

export type TraceMode = "live" | "complete";
```

#### Frontend SSE Parser — Forward-Compat Requirement (Decision #15, Item B)

`parseSSEFrame(frame: string): GemmaTraceEvent | null` MUST return `null` (not throw, not propagate) for any SSE frame whose `data` JSON has a `type` value not present in the `GemmaTraceEvent` discriminated union. This is a hard requirement, not a "nice to have":

- It is the only seam that lets a future backend version add new event types (`thinking`, `final_text_delta`, `tool_partial_result`) without breaking already-deployed frontend bundles.
- The reader loop in `askGemmaStream` MUST continue reading after receiving `null` from `parseSSEFrame` — it MUST NOT abort the stream or trigger fallback. Unknown events are silently skipped; known events continue to dispatch.
- This is enforced by a dedicated vitest in `frontend/src/api/menu.test.ts` (or `menu.stream.test.ts`): `test_unknown_event_type_returns_null_not_throw`. See §4 New Tests Required.

#### No DuckDB / Iceberg / pipeline schema changes.
This spec touches no Bronze/Silver/Gold tables. No CIPCODE handling needed. No PrivacySuppressed handling needed.

### Service Changes

#### `backend/app/services/_sse.py` (new shared helper)

```python
"""Shared SSE wire-format helper. Used by build creation, set-your-course
intent stream, and ask-gemma-stream. Single source of truth for
`event:` / `data:` framing."""

from __future__ import annotations
import json
from typing import Any


def sse_event(event: str, data: Any) -> str:
    """Format a single SSE frame. JSON-encodes data with default=str
    for datetime/UUID safety. Always terminates with a blank line."""
    payload = json.dumps(data, default=str, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
```

Three router modules import this: `routers/builds.py` (replacing local `_sse_event` at lines 226–228), `routers/set_your_course.py` (replacing local `_sse_event` at lines 38–41 — verified byte-identical body), and the new `routers/ask_gemma_router.py` consumer.

#### `backend/app/services/ask_gemma.py` — new generator

```python
async def chat_ask_stream(
    *,
    scope: AskScope,
    builds: list[Build | None],
    message: str,
    history: list[dict[str, Any]],
    locale: AppLocale | None,
) -> AsyncIterator[TraceEvent]:
    """Streaming variant of chat_ask. Yields TraceEvent objects in
    order: zero or more (turn_start, turn_complete) pairs, exactly one
    final_text, exactly one done.

    On Gemma transport failure or any uncaught loop exception: yields
    the final_text with the chat_unavailable fallback string, then
    done. NEVER raises past the generator boundary (C3).

    On client disconnect: cancels the in-flight loop_task and waits
    for it to settle so the Gemma semaphore is released promptly (C4).
    """
    # Setup identical to chat_ask (system prompt, tool schemas, dispatch).
    ...

    # Bounded queue (Decision #14). maxsize=256 gives ~8x headroom over
    # the worst-case event count: max_turns(3) * max_tools_per_turn(~5)
    # * 2 events per dispatch = ~30. Bound is documented & not reachable
    # under the configured loop limits.
    queue: asyncio.Queue[TraceEvent] = asyncio.Queue(maxsize=256)

    async def on_start(dispatch_index: int, name: str, args: dict[str, Any]) -> None:
        # Fired by the loop right before each `await dispatch(...)`.
        # Both events originate from the loop now (Decision #12) — no
        # router-side dispatch wrapper.
        await queue.put(TraceTurnStart(
            turn=dispatch_index,
            tool=name,
            args=args,
        ))

    async def on_turn(turn: ToolCallTurn) -> None:
        # Fired by the loop right after tool_call_log.append. Carries
        # the same dispatch_index that on_start emitted, so the
        # frontend correlates start ↔ complete by `turn`.
        await queue.put(TraceTurnComplete(
            turn=turn.dispatch_index,
            tool=turn.tool_name,
            args=turn.tool_args,
            result_preview=turn.tool_result_preview,
            duration_ms=turn.duration_ms,
            error=turn.error,
        ))

    loop_task = asyncio.create_task(gemma_client.generate_with_tools_loop(
        system=system, user=user_msg, tools=tool_schemas,
        dispatch=mcp_client.call_async,    # plain dispatch — no wrapper
        max_turns=3, max_wall_time_s=30.0,
        temperature=_TEMPERATURE, max_tokens=1200,
        extra=extra,
        on_turn_start=on_start,
        on_turn_event=on_turn,
    ))

    text = ""
    try:
        # Drain queue until loop_task completes (C4: try/finally below
        # guarantees cancellation if the SSE client disconnects, which
        # raises GeneratorExit at the active `yield ev`).
        while not loop_task.done() or not queue.empty():
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.05)
                yield ev
            except asyncio.TimeoutError:
                continue

        # Loop is done — collect its return. Wrapped in try/except per
        # C3: ANY exception (transport, callback bug, programmer error)
        # collapses to the fallback final_text + done. Generator never
        # raises past its boundary.
        try:
            text, _log = await loop_task
        except Exception as exc:
            logger.warning("chat_ask_stream: loop_task raised — %s", exc)
            text = ""

        if not text:
            text = fallback_text("chat_unavailable", normalize_locale(locale))

        yield TraceFinalText(response=text)
        yield TraceDone()
    finally:
        # C4: client disconnect path. If the SSE consumer aborts mid-
        # stream, FastAPI calls aclose() on this generator, which
        # raises GeneratorExit at the active `yield ev` and bypasses
        # the try-block exit. The finally MUST cancel loop_task and
        # wait for it to settle so the Gemma semaphore is released
        # immediately rather than after the wall-time cap (≤30s).
        if not loop_task.done():
            loop_task.cancel()
            await asyncio.gather(loop_task, return_exceptions=True)
```

**Note on emission origin (Decision #12):** Both `turn_start` and `turn_complete` are now emitted from inside `_tools_loop_inner` via the new `on_turn_start` and `on_turn_event` callbacks. No router-side `_wrap_dispatch` is needed. The `dispatch` callable passed to the loop is the plain `mcp_client.call_async`. Future callers of `generate_with_tools_loop` (e.g. `feature-agentic-school-research.md`'s `research_job.py`) get both events for free without re-implementing a dispatch wrapper.

**Note on `turn_start` placement:** The loop fires `on_turn_start(dispatch_index, name, args)` inside `_tools_loop_inner` immediately BEFORE the awaited tool call. This is intentional — the user sees "Looking up X…" the moment Gemma decides to call the tool, not after the result lands. The `turn_complete` callback fires once the loop appends the full `ToolCallTurn` to the log, carrying the matching `dispatch_index`.

`chat_ask` is updated to populate the enriched `TraceEventPayload` shape in `AskResponse.tool_calls` (currently it returns the lossy summary at lines 323–330). The `turn` field on each entry is `ToolCallTurn.dispatch_index`. This is what the fallback path consumes.

#### `backend/app/routers/ask_gemma_router.py` — new endpoint

```python
@router.post("/chat/ask/stream")
async def chat_ask_stream(request: AskRequest) -> StreamingResponse:
    """SSE variant of /chat/ask. Streams TraceEvent frames as Gemma
    works, finishing with `final_text` then `done`. Falls back is the
    client's job (frontend retries against /chat/ask on connection
    failure)."""
    try:
        loaded = await asyncio.gather(*(
            asyncio.to_thread(builds.load_build, bid)
            for bid in request.scope.build_ids
        ))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def _stream() -> AsyncIterator[str]:
        async for ev in ask_gemma.chat_ask_stream(
            scope=request.scope, builds=loaded,
            message=request.message, history=request.history,
            locale=request.locale,
        ):
            yield sse_event(ev.type, ev.model_dump(mode="json"))

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

#### `frontend/src/api/menu.ts` — new client

```typescript
export async function askGemmaStream(
  request: AskRequest,
  onEvent: (event: GemmaTraceEvent) => void,
): Promise<{ response: string; events: GemmaTraceEvent[] }> {
  // Try SSE endpoint first
  try {
    const res = await fetch(`${API_BASE}/chat/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);

    const collected: GemmaTraceEvent[] = [];
    let response = "";
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let done = false;

    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        buffer += decoder.decode(value, { stream: true });
        // Parse SSE frames: split on "\n\n", each frame has "event:" + "data:"
        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const event = parseSSEFrame(frame);  // returns GemmaTraceEvent | null
          if (event) {
            collected.push(event);
            onEvent(event);
            if (event.type === "final_text") response = event.response;
          }
        }
      }
    }

    return { response, events: collected };
  } catch (err) {
    // Fallback: non-streaming endpoint, synthesize events from tool_calls
    console.warn("[gemma-trace] streaming failed, falling back", err);
    const resp = await askGemma(request);
    const events = synthesizeEventsFromToolCalls(resp.tool_calls);
    for (const ev of events) onEvent(ev);
    onEvent({ type: "final_text", response: resp.response });
    onEvent({ type: "done" });
    return { response: resp.response, events: [...events,
      { type: "final_text", response: resp.response },
      { type: "done" },
    ] };
  }
}
```

`synthesizeEventsFromToolCalls(tool_calls: TraceEventPayload[])` produces a `turn_start` + `turn_complete` pair per entry.

### Gemma-Touching Discipline (per `SPEC_GUIDELINES.md`)

This spec modifies `gemma_client.generate_with_tools_loop`. Discipline checklist:

- **Fallback per call site:** All existing callers (`set_your_course.py`, `ask_gemma.py`'s existing `chat_ask`, `soc_expansion.py`) pass no `on_turn_start` and no `on_turn_event` — both default to `None` — no behavior change. New `chat_ask_stream` falls back to chat_unavailable string on transport failure (same as existing `chat_ask`) AND on any uncaught loop exception per C3. Frontend `askGemmaStream` falls back to non-streaming `askGemma` on connection failure AND silently skips unknown SSE event types per Decision #15. Three layers of graceful degradation.
- **`logs/gemma.jsonl` telemetry preserved:** `_log_tool_turn` continues to fire from inside the loop unchanged. The new `on_turn_event` callback fires *after* logging — never replaces it. The new `on_turn_start` callback fires *before* dispatch — also never touches the log. No double-log, no missed log.
- **Both backends:** No backend-specific behavior; the loop already abstracts Ollama vs OpenRouter. SSE works for both. Phase B exit verifies a real chat session on each backend.
- **Concurrency + cancellation:** The new endpoint creates one bounded `asyncio.Queue(maxsize=256)` and one Gemma task per request. No shared state across requests. The existing semaphore in `gemma_client._get_semaphore()` continues to throttle concurrent Gemma calls. Per C4, `chat_ask_stream`'s `try/finally` block guarantees `loop_task.cancel()` + `asyncio.gather(..., return_exceptions=True)` on client disconnect — the semaphore is released within ~100ms rather than after the wall-time cap (≤30s).
- **Rate limits:** Cloud demo behavior unchanged (no new Gemma call sites; one stream = one existing call). A cancelled stream still releases the rate-limit slot promptly (per C4).
- **Callback discipline:** Both callbacks invocations in `_tools_loop_inner` are wrapped in `try/except Exception`. Async vs sync return values are auto-detected via `asyncio.iscoroutine` (Item D). A broken callback degrades gracefully — the loop continues, telemetry continues, the user sees the answer.

### Testing Impact Analysis

> Searched `backend/tests/` and `frontend/src/` for tests touching the modified files. Findings below.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_loop_*` (multiple) | Med | Adding two new dataclass fields (`tool_result_preview`, `dispatch_index` — both with defaults) and two new optional kwargs (`on_turn_start`, `on_turn_event` — both default `None`). Tests that construct `ToolCallTurn` literals via kwargs are unaffected by the new defaulted fields but should add `dispatch_index=N` where the test asserts on it. Tests that just call the loop with kwargs are safe. |
| `backend/tests/services/test_ask_gemma.py` | `test_tool_loop_dispatches_to_mcp` and similar | Med | `chat_ask` now produces enriched `tool_calls` payload (was lossy summary). Tests that assert exact `tool_calls` shape need updates. Tests asserting just dispatch fired are safe. |
| `backend/tests/routers/test_ask_gemma_router.py` | All existing `POST /chat/ask` tests | **Med** | (Updated per C7.) Two attention points: (a) `ToolCallTurn(...)` literal at line 718 — requires `dispatch_index` only if the test asserts on it (default 0 satisfies otherwise); the new `tool_result_preview` field has a default so kwargs construction stays compiling. (b) `generate_with_tools_loop` is patched at lines 155, 406, 438, 486, 734, 795 — patches replace the function, so the new kwargs-only `on_turn_start` / `on_turn_event` parameters cause no breakage as long as the patch's `fake_loop` accepts `**kwargs`. **Verify each `fake_loop` signature explicitly.** Any test asserting on the prior lossy `AskResponse.tool_calls` shape needs migration to the enriched `TraceEventPayload` shape. |
| `backend/tests/services/test_set_your_course.py` | All | Low | `set_your_course.py` itself is not behaviorally changed; only the local `_sse_event` is replaced with an import (C6). Loop signature change is additive (kwarg-only params with defaults). Tests should pass unchanged. **VERIFY explicitly during Phase A.** |
| `backend/tests/services/test_set_your_course_chip_tool_loop.py` | All | **Med** | (Added per C7.) Constructs `ToolCallTurn(...)` literal at line 103 via kwargs — both new fields have defaults so the literal stays compiling. Patches `generate_with_tools_loop` extensively; verify the `fake_loop` signatures accept `**kwargs` for the new optional callbacks. Should pass unchanged once that compatibility is verified. |
| `backend/tests/services/test_ask_gemma_voice.py` | All | **Med** | (Added per C7.) Patches `generate_with_tools_loop` at lines 234, 280, 435, 501. The system prompt voice contract is unchanged by this spec, so the voice assertions hold. Verify each `fake_loop` accepts `**kwargs` so the new opt-in callbacks don't trigger TypeError. Should pass unchanged. |
| `backend/tests/services/test_soc_expansion.py` | All | Low | `soc_expansion.py` uses `generate_with_tools` (not `_loop`), which is also unchanged. **VERIFY explicitly during Phase A.** |
| `backend/tests/routers/test_builds.py` (if exists) | All | Low | `_sse_event` extracted to a helper, but the import is a one-line change. Any test mocking `builds._sse_event` needs to patch the new import path (`app.services._sse.sse_event`). |
| `backend/tests/routers/test_set_your_course.py` (if exists) | All | Low | (Added per C6.) Same as `test_builds.py` above — the `_sse_event` helper extraction is a one-line import change. Any test patching the local `_sse_event` must update the import path. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | All | Med | Chat now uses `askGemmaStream` instead of `askGemma`. Tests mocking `askGemma` need to also mock `askGemmaStream` (or the fallback path will be exercised in tests, which is acceptable). |
| `frontend/src/components/menu/AskGemmaFab.test.tsx` | All | Low | FAB doesn't make API calls directly. Should pass unchanged. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | All chat-touching tests (`askGemma` mock at line 63) | Med | `GemmaChat` is mounted on `/my-build` and these tests mock `askGemma` at the `@/api/menu` boundary. Component now calls `askGemmaStream` first; without a matching mock the SSE fallback path is exercised — works, but is extra surface. Mock should be extended to cover both. |
| `frontend/src/screens/FutureScreen.test.tsx` | All chat-touching tests (`askGemma` mock at line 16) | Med | `GemmaChat` is mounted on `/future` (the consolidated career-tree surface — `/branches` redirects here per `App.tsx:35`). Auto-opener fires `askGemma` on mount + on selectedRef changes; both paths now go through `askGemmaStream`. Mock must cover both. |
| `frontend/src/components/menu/CompareView.test.tsx` | All chat-touching tests (`askGemma` mock at line 29) | Med | `CompareView` is embedded in `MenuScreen` (`/builds`) and mounts its own `GemmaChat` with compare-scope (2–4 builds). Mock must cover `askGemmaStream`. |
| `frontend/src/screens/MenuScreen.test.tsx` | All | **Low** | MenuScreen.test.tsx mocks `sendChat` (different function — see `api/menu.ts:159`), not `askGemma`. The `GemmaChat` mount in MenuScreen ultimately calls `askGemma` → `askGemmaStream`, but the test does not currently intercept that path. Should pass without modification; verify and only patch if a test actually exercises chat send. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_gemma_client.py` | Add `tool_result_preview=""` (and optionally `dispatch_index=N` where the test asserts on it) to existing `ToolCallTurn(...)` constructions only when needed for assertion correctness — both fields have defaults, so most tests stay unchanged. Add new tests for both callback parameters: `on_turn_start` and `on_turn_event` default-None no-op; both fire in the right order; both tolerate raise; both accept sync OR async callables (Item D). Update assertions on loop signature if any test asserts the kwargs list. | Dataclass field + new params. Defaults preserve compatibility; explicit additions only where test logic requires them. |
| `backend/tests/services/test_ask_gemma.py` | Update tests that assert exact `AskResponse.tool_calls` shape to expect the enriched `TraceEventPayload` shape (turn / tool / args / result_preview / duration_ms / error). Tests that just check dispatch fired or response text should not need changes. | Shape is intentionally enriched for the fallback path; the existing tests' assertion of a lossy shape was a workaround we're now correcting. |
| `backend/tests/routers/test_ask_gemma_router.py` | (Added per C7.) (a) `ToolCallTurn(...)` literal at line 718 — only update if a test asserts on the `dispatch_index` field; otherwise default `0` covers it. The new `tool_result_preview` field has a default `""`. (b) For each patch site (155/406/438/486/734/795), audit the `fake_loop` callable signature: if it uses `**kwargs`, no change needed; if it lists params explicitly, add `on_turn_start=None, on_turn_event=None` so the loop's call site doesn't TypeError. (c) Any test asserting the prior `tool_calls` lossy shape migrates to the enriched `TraceEventPayload` shape. | C7 expanded scope. Required: `fake_loop` signatures must tolerate the two new opt-in kwargs the production caller will now pass through `chat_ask_stream`. |
| `backend/tests/services/test_set_your_course_chip_tool_loop.py` | (Added per C7.) Audit `fake_loop` patch signatures at all `generate_with_tools_loop` patch sites for `**kwargs` tolerance (or add explicit `on_turn_start=None, on_turn_event=None` params). The `ToolCallTurn(...)` literal at line 103 only needs updates if the test asserts on the new fields — defaults satisfy otherwise. | Mirrors C7 treatment. Required to keep the test suite green when production callers add the new kwargs. |
| `backend/tests/services/test_ask_gemma_voice.py` | (Added per C7.) Audit `fake_loop` patch signatures at lines 234/280/435/501 for `**kwargs` tolerance (or add explicit `on_turn_start=None, on_turn_event=None`). System prompt voice assertions are unchanged by this spec — those tests hold without modification. | C7. Required for kwargs compatibility only; voice contract is untouched. |
| `backend/tests/routers/test_builds.py` (and any other test importing `_sse_event` from builds.py) | Update import to `from app.services._sse import sse_event`. | Helper extraction. One-line import change. |
| `backend/tests/routers/test_set_your_course.py` (and any other test importing `_sse_event` from set_your_course.py) | (Added per C6.) Update import to `from app.services._sse import sse_event`. | Second helper extraction site. One-line import change. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | Replace `askGemma` mocks with `askGemmaStream` mocks. Add a test that exercises the fallback path (mock `askGemmaStream` to throw / fail-stream → assert fallback to `askGemma` happens and trace renders post-hoc). | Chat now consumes the streaming variant; existing tests need to track that. Fallback path needs a specific test. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Extend the `@/api/menu` mock at line 63 to include `askGemmaStream: (...args) => mockAskGemmaStream(...args)`. Default the new mock to a happy-path SSE-equivalent response so existing assertions (which check the chat sent the right scope payload) keep passing. | `/my-build` mounts `GemmaChat`; without the new mock, every existing chat-send test exercises the SSE fallback path. Functional but slow and noisy. |
| `frontend/src/screens/FutureScreen.test.tsx` | Extend the `@/api/menu` mock at line 16 with `askGemmaStream`. Default to happy-path SSE-equivalent response. Verify existing tests around auto-opener firing + selectedRef change debounce still assert correct call cadence against the new function. | `/future` mounts `GemmaChat` with node-scoped chat. Auto-opener fires on mount AND on selectedRef changes; debounce assertions matter for hackathon demo correctness. |
| `frontend/src/components/menu/CompareView.test.tsx` | Same pattern — extend the `@/api/menu` mock at line 29 with `askGemmaStream`. Verify the existing `compare`-scope routing test (around line 352) still asserts the right scope payload reaches the new function. | Compare flow under `/builds` mounts its own `GemmaChat`; existing test asserts the `compare` scope (2–4 build_ids) is passed correctly through to the chat client. |

Any test failure NOT in this table is a regression — STOP and escalate per CLAUDE.md.

#### Confirmed Safe

These tests must NOT break:
- All voice/contract tests in `backend/tests/services/test_gemma_voice_contract.py` — system prompt is unchanged. (`test_ask_gemma_voice.py` was MOVED to "At Risk" per C7 due to its `generate_with_tools_loop` patch sites — voice assertions hold, but the patch's `fake_loop` signatures need a `**kwargs` audit.)
- All tests in `backend/tests/services/test_soc_expansion.py` — `soc_expansion.py` uses `generate_with_tools` (not `_loop`), unchanged.
- `backend/tests/services/test_set_your_course.py` — tests the service's own behavior; loop signature change is additive (kwarg-only with defaults). (`test_set_your_course_chip_tool_loop.py` was MOVED to "At Risk" per C7 due to its loop patch sites and `ToolCallTurn` literal.)
- All tests in `backend/tests/services/test_career_pick_qna.py`, `test_career_tiering.py`, `test_skill_pool.py`, `test_next_steps.py`, `test_boss_fights.py`, `test_branch_tree.py`, `test_guidance.py`, `test_skill_recs.py`, `test_wrapped_renderer.py`, `test_intent.py`, `test_community_suggestions.py` — these services don't touch the loop.
- All pipeline tests in `tests/raw/`, `tests/silver/`, `tests/gold/`, `tests/mcp/` — this spec doesn't touch the pipeline.
- All build-creation tests using SSE (`test_builds.py` if testing `_build_stream`) — only the import path changed; behavior is identical.
- All frontend chat tests other than `GemmaChat.test.tsx` (`AskGemmaFab.test.tsx`, etc.).

If any of these break: STOP, escalate, do not "fix" silently.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_event_default_is_noop` | Loop with no `on_turn_event` passed behaves identically to current behavior. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_start_default_is_noop` | (Added — symmetric to event default.) Loop with no `on_turn_start` passed behaves identically to current behavior. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_event_fires_per_turn` | Mock callback receives one call per appended `ToolCallTurn`, in order. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_start_fires_before_dispatch` | (Added per Decision #12.) Mock callback fires BEFORE `dispatch(...)` returns — verified by recording the order of `on_turn_start` invocation vs. dispatch's coroutine progress (e.g. dispatch sleeps; assert on_turn_start ran first). |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_dispatch_index_unique_across_parallel_calls` | (Added per Decision #13 / C1.) Stub `_one_tool_turn` to return MULTIPLE tool calls in a single outer LLM turn (parallel-call case). Assert each appended `ToolCallTurn` has a distinct, monotonically-increasing `dispatch_index` even though they share `turn_number`. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_start_and_event_share_dispatch_index` | (Added per Decision #13.) For each dispatch, assert the `dispatch_index` passed to `on_turn_start` equals `ToolCallTurn.dispatch_index` passed to `on_turn_event`. This is the contract the frontend relies on for row pairing. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_event_callback_failure_does_not_break_loop` | Callback that raises is caught, warning logged, loop continues to completion. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_on_turn_start_callback_failure_does_not_break_loop` | (Added — symmetric.) Same coverage for `on_turn_start`. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_callback_accepts_sync_callable` | (Added per Item D.) Pass a plain `def` callable (returning `None`) for both `on_turn_start` and `on_turn_event`; loop completes without TypeError; sync callbacks are recorded. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_tool_result_preview_truncated` | Result preview field is truncated to 500 chars; `tool_result_size_bytes` reflects full size. |
| P0 | `backend/tests/services/test_sse.py` | `test_sse_event_format` | Output is exactly `event: <name>\ndata: <json>\n\n`. |
| P0 | `backend/tests/services/test_sse.py` | `test_sse_event_default_str_encoder` | datetime / UUID values serialize via default=str without raising. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_emits_turn_start_then_complete` | One tool call → events in order: turn_start, turn_complete, final_text, done. The `turn` field on both events matches `dispatch_index = 0`. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_loop_exception_falls_back_to_chat_unavailable` | (Added per C3.) Patch `gemma_client.generate_with_tools_loop` to raise `RuntimeError`. Assert the generator yields `TraceFinalText(chat_unavailable_localized)` + `TraceDone` and never raises past the boundary. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_cancelled_when_client_disconnects` | (Promoted from P1 per C4.) Start the stream, drive one turn_start through the queue, then call `aclose()` on the generator. Assert: (a) `loop_task` is cancelled within ~100ms (not after wall-time cap), (b) `loop_task.cancelled()` is True, (c) `await asyncio.gather(loop_task, return_exceptions=True)` does not hang. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_no_tools_called_emits_only_final_and_done` | Gemma answers from context (no tool calls) → events: final_text, done. No turn_start, no turn_complete. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_tool_error_emits_complete_with_error` | Tool dispatch errors → turn_complete carries `error` field, then final_text continues. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_transport_failure_emits_fallback_final_text` | Gemma loop returns ("", []) → final_text is `chat_unavailable` localized string, done emitted. |
| P0 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_queue_drained_after_loop_completes` | After loop_task done, any remaining queue events are yielded before EOF. |
| P0 | `backend/tests/routers/test_ask_gemma_router.py` | `test_chat_ask_stream_endpoint_returns_sse` | Endpoint returns `text/event-stream` content-type, no-cache headers. |
| P0 | `backend/tests/routers/test_ask_gemma_router.py` | `test_chat_ask_stream_emits_all_event_types` | Real-shape integration test: parse the SSE stream and assert every expected event type fires. |
| P0 | `backend/tests/routers/test_ask_gemma_router.py` | `test_chat_ask_stream_404_on_bad_build` | Bad build_id → 404 (mirrors existing /chat/ask behavior). |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_empty_events_renders_null` | events=[] → component returns null, no DOM. |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_streaming_state_shows_pending_for_unresolved_rows` | After turn_start with no matching turn_complete → row visible with in-progress indicator. |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_complete_state_shows_resolved_rows` | After turn_complete → row resolved with success/error pill, duration shown. |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_error_row_shows_error_pill_and_continues` | turn_complete with error → row shows error pill; subsequent rows still render. |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_click_to_expand_shows_engineering_view` | Click row → engineering detail panel reveals tool name, args JSON, result_preview JSON. |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_unknown_tool_falls_back_to_default_label` | Tool name not in `TOOL_LABEL_MAP` → renders default label, doesn't crash. |
| P0 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_accessibility_identifiers_present` | All identifiers from §3 accessibility table render with correct aria-labels. |
| P0 | `frontend/src/components/menu/toolLabels.test.ts` | `test_all_chat_tools_have_label_entries` | Every tool name in the canonical 5-tuple has an entry. |
| P0 | `frontend/src/components/menu/toolLabels.test.ts` | `test_hint_templates_handle_realistic_args` | For each tool, sample args produce a coherent pedagogical sentence. |
| P0 | `frontend/src/components/menu/toolLabels.test.ts` | `test_unknown_tool_returns_default_label` | Unknown tool name → returns `{label: "...", icon: "...", hint: ...}` default. |
| P0 | `frontend/src/api/menu.test.ts` (or new `menu.stream.test.ts`) | `test_askGemmaStream_happy_path_parses_sse_frames` | Mock fetch returning canned SSE bytes → events arrive in order via callback. |
| P0 | `frontend/src/api/menu.test.ts` (or new) | `test_askGemmaStream_falls_back_on_http_error` | Mock fetch returning 5xx → fallback to askGemma fires, events synthesized from tool_calls. |
| P0 | `frontend/src/api/menu.test.ts` (or new) | `test_askGemmaStream_falls_back_on_thrown_error` | Mock fetch throwing → same fallback. |
| P0 | `frontend/src/api/menu.test.ts` (or new) | `test_unknown_event_type_returns_null_not_throw` | (Added per Decision #15 / Item B.) Feed `parseSSEFrame` an SSE frame with `data: {"type":"thinking","text":"..."}`. Assert: returns `null`, does NOT throw, does NOT propagate. The reader loop continues — no fallback triggered, no stream abort. Subsequent known events still dispatch correctly. |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `test_chat_renders_trace_when_tool_calls_present` | Mocked askGemmaStream emitting tool events → `<GemmaTrace>` visible above response. |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `test_chat_omits_trace_when_no_tool_calls` | Mocked askGemmaStream emitting only final_text + done → no `<GemmaTrace>` in DOM. |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `test_chat_falls_back_to_post_hoc_trace_on_stream_failure` | askGemmaStream's fallback path exercised → trace still renders, message arrives. |
| P1 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_framer_motion_does_not_throw_with_rapid_events` | Burst 10 events in <100ms → no React render warnings, all rows present. |
| P1 | `frontend/src/components/menu/GemmaTrace.test.tsx` | `test_rows_correlate_by_dispatch_index_with_parallel_calls` | (Added per Decision #13.) Feed the component a stream where two `turn_start` events fire (`turn=0`, `turn=1`) BEFORE either `turn_complete` arrives. Then a `turn_complete{turn=1}` arrives, then `turn_complete{turn=0}`. Assert: row[0] correlates to dispatch_index 0 (resolves second), row[1] correlates to dispatch_index 1 (resolves first). No row mispairing. |
| P2 | `backend/tests/services/test_ask_gemma_stream.py` | `test_stream_back_pressure_under_bounded_queue` | (Reframed per Decision #14 / C5.) Push 32 events through a single chat turn; assert the queue's `maxsize=256` never blocks (logs no warning), all events are emitted in order, and no event is lost. Validates the documented bound. |

#### Test Data Requirements

- **Fixture: `mock_gemma_loop_emits_events`** — monkeypatches `gemma_client.generate_with_tools_loop` to call `on_turn_event` with scripted `ToolCallTurn` instances and return scripted `(text, log)`.
- **Fixture: `canned_sse_bytes`** — TextEncoder-encoded byte stream of realistic SSE frames for the frontend client tests.
- **Fixture: `mock_mcp_dispatch`** — async mock for tool dispatch in `test_ask_gemma_stream.py` so we don't hit the real MCP server.
- No real LLM calls in CI. All tests use mocks.
- No new fixture data files required — all fixtures are constructed inline.

### Phasing — Implementation Order

Each phase ships independently green (lint + types + tests + build).

**Phase A — Backend (~1 day)**
- Update `ToolCallTurn` (add `tool_result_preview`, `dispatch_index` — both with defaults per Decision #13)
- Add `on_turn_start` AND `on_turn_event` params to `generate_with_tools_loop` per Decision #12; populate them inside `_tools_loop_inner` (start fires before `await dispatch(...)` at line 1069 with `dispatch_index = len(tool_call_log)`; event fires after `tool_call_log.append(...)` at line 1090). Both callbacks: try/except wrapped, `asyncio.iscoroutine` sync/async branching per Item D.
- Extract `_sse_event` to `app.services._sse.sse_event`; update BOTH `routers/builds.py` import AND `routers/set_your_course.py` import per C6.
- Add `TraceEvent` discriminated union and `TraceEventPayload` to `models/api.py`; enrich `AskResponse.tool_calls` shape (turn field carries dispatch_index).
- Implement `ask_gemma.chat_ask_stream(...)` generator with try/finally cancellation (C4) + try/except on `await loop_task` (C3) + bounded queue maxsize=256 (C5).
- Add `POST /chat/ask/stream` endpoint.
- All P0 backend tests pass; existing backend tests still pass after authorized mods (audit fake_loop signatures for **kwargs tolerance per C7).
- Phase exit: manual `curl -N -X POST .../chat/ask/stream -d '{...}'` shows SSE frames arriving live, including `dispatch_index` correlation across parallel tool calls (use a stub/forced multi-call test).

**Phase B — Frontend (~1.5 days)**
- `frontend/src/types/gemmaTrace.ts`
- `frontend/src/components/menu/toolLabels.ts` + tests (5 entries)
- `frontend/src/api/menu.ts` adds `askGemmaStream` + fallback + tests
- `frontend/src/components/menu/GemmaTrace.tsx` + tests (all states from §3)
- `frontend/src/components/menu/GemmaChat.tsx` integrates `askGemmaStream` and renders `<GemmaTrace>`
- `frontend/src/i18n/strings.ts` updated for any new visible copy
- @fp-design-visionary §3 implemented to spec
- All P0 + P1 frontend tests pass; existing chat tests still pass after authorized mods
- Phase exit: live demo — open chat, ask "What's the median earnings for Marketing at IU?" → see tool-call rows reveal live → see response. Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` verified end-to-end.

---

## §5 Architecture Review

### @fp-architect Review (rev 1.1)
**Status:** REVIEWED
**Reviewed:** 2026-05-01
**Re-reviewed:** 2026-05-01

#### Re-Review Findings

Rev 1.1 was assessed strictly against the seven CHANGES REQUESTED conditions (C1–C7) from the rev 1.0 review, plus a check for new issues introduced by the rev 1.1 deltas. Rev 1.0 minor items (M-series) were not re-litigated per re-review charter. M3 was documented in §3 (Long-shimmer Edge Case); M1 was subsumed by C2. M2/M4/M5 remain as documented quality notes — not blockers.

| # | Condition | Rev 1.1 Resolution | Status |
|---|-----------|--------------------|--------|
| C1 | Unify turn-number scheme; pair `turn_start`/`turn_complete` correctly under parallel calls | Decision #13 adds `dispatch_index: int = 0` to `ToolCallTurn`. Decision #12 adopts symmetric two-callback emission from inside `_tools_loop_inner`. SSE `turn` field on both `TraceTurnStart` (line 395) and `TraceTurnComplete` (line 402) carries `dispatch_index`. New tests `test_dispatch_index_unique_across_parallel_calls` and `test_on_turn_start_and_event_share_dispatch_index` lock the contract. Frontend §3 Row Correlation Key explicitly correlates by this field. Verified in §4 Service Changes lines 513-534 — `on_start` enqueues `TraceTurnStart(turn=dispatch_index, ...)`, `on_turn` enqueues `TraceTurnComplete(turn=turn.dispatch_index, ...)`. Both sides agree. | **PASS** |
| C2 | Resolve §4 row 274 contradiction — callback firing semantics | The "Emission contract" subsection at lines 352-356 explicitly states: callbacks fire ONLY on appended `ToolCallTurn`s; transport-error branch (line 1030) and plain-text-only branch (line 1043) do not fire callbacks; final-text is surfaced via the loop's `(text, log)` return tuple. The File Changes row text was rewritten (line 287) to match. No remaining contradiction. | **PASS** |
| C3 | `chat_ask_stream` must not raise past the generator boundary | Lines 562-566 wrap `await loop_task` in `try/except Exception`. On exception: logs warning, falls through to fallback `TraceFinalText(chat_unavailable) + TraceDone`. Docstring at line 499 explicitly states "NEVER raises past the generator boundary (C3)". New P0 test `test_stream_loop_exception_falls_back_to_chat_unavailable` (line 768) covers it. | **PASS** |
| C4 | Cancel `loop_task` on client disconnect; release Gemma semaphore promptly | Lines 573-582 show `try/finally` block. On `aclose()` from FastAPI, `GeneratorExit` raises at active `yield ev`, finally fires `loop_task.cancel()` + `await asyncio.gather(loop_task, return_exceptions=True)`. Test `test_stream_cancelled_when_client_disconnects` promoted to P0 (line 769) with explicit assertions for cancellation latency (~100ms vs the 30s wall-time cap). Success Criteria line 142 codifies the ~100ms expectation. | **PASS** |
| C5 | Pick a backpressure strategy and document it | Option (b) chosen — `maxsize=256` on the bounded queue. Decision #14 documents the bound: max_turns(3) × max_tools_per_turn(~5) × event_pairs(2) = ~30 worst case, so 256 = ~8× headroom. Lossless trace preserved. P2 test reframed to `test_stream_back_pressure_under_bounded_queue` validating that the bound never blocks under realistic load. Reasonable choice given the per-request bound is structurally not reachable. | **PASS** |
| C6 | Second `_sse_event` copy in `set_your_course.py` | File Changes table row at line 292 explicitly adds `routers/set_your_course.py` (lines 38-41) — byte-identical extraction to `app.services._sse.sse_event`. Service Changes section line 480 confirms the three consumer modules. Single source of truth restored. | **PASS** |
| C7 | Three missing test files added to Testing Impact Analysis | All three files (`test_set_your_course_chip_tool_loop.py`, `test_ask_gemma_voice.py`, `test_ask_gemma_router.py`) appear in "Existing Tests at Risk" (lines 706-709) with explicit Med risk and rationale, and have entries in "Authorized Test Modifications" (lines 726-728) covering the `ToolCallTurn` literal at line 718, the six `generate_with_tools_loop` patch sites in `test_ask_gemma_router.py`, and the `**kwargs` audit requirement for each `fake_loop` patch. The two files that previously appeared in "Confirmed Safe" are explicitly noted as MOVED (lines 741, 743). The implementer now has an exhaustive inventory. | **PASS** |

##### New Issues Introduced by Rev 1.1

None of significance.

The `dispatch_index` field is added in trailing position (line 324) preserving kwargs construction across all existing call sites (verified at line 327: `gemma_client.py:1090`, `tests/services/test_set_your_course_chip_tool_loop.py:103`, `tests/routers/test_ask_gemma_router.py:718` all use kwargs). The two new callbacks are kwarg-only with default `None`, so existing `set_your_course.py:834` and `ask_gemma.py:302` call sites need zero changes. The sync-vs-async detection via `asyncio.iscoroutine` on the return value (rather than `iscoroutinefunction` on the callable) is the more robust choice — it correctly handles `functools.partial(async_fn)` and other wrapped callables that `iscoroutinefunction` misses. The `try/finally` cancellation pattern at lines 573-582 is the canonical async-generator cleanup idiom.

One forward-compatibility detail worth confirming during implementation but NOT blocking: the spec at line 614 uses `ev.model_dump(mode="json")` to serialize each `TraceEvent` for the SSE wire — this includes the discriminator `type` field on the inner JSON payload AS WELL AS using it as the SSE `event:` name. That double-naming is intentional (matches the existing pattern in `routers/builds.py`) and the frontend `parseSSEFrame` per Decision #15 will use the JSON `data.type` field for routing. Consistent. No action.

#### Verdict (rev 1.1)
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All seven CHANGES REQUESTED conditions are cleanly resolved. The architectural seam (opt-in dual-callback emission from inside the loop, request-scoped bounded queue, typed discriminated-union SSE events, dual-feed `<GemmaTrace>` consumer) is now correct and extensible. The reuse path for `feature-agentic-school-research.md` is unblocked — its `research_job.py` can subscribe to both `on_turn_start` and `on_turn_event` without rebuilding a dispatch wrapper. Proceed to Step 2 (Design Vision).

---

#### Original Findings (rev 1.0)

> Preserved verbatim for audit trail. Superseded by the rev 1.1 re-review above. All seven conditions (C1–C7) listed below were addressed in rev 1.1 — see the table above for resolution mapping.

**Status (rev 1.0):** CHANGES REQUESTED
**Reviewed:** 2026-05-01

#### System Context
This spec sits between the FastAPI router layer and the existing Gemma tool-loop primitive. It does not touch Brightsmith zones (Bronze/Silver/Gold), DuckDB, MCP tool definitions, or any pipeline contracts — confirmed. The data flow added is: `_tools_loop_inner` → opt-in callback → request-scoped `asyncio.Queue` → `chat_ask_stream` async generator → FastAPI `StreamingResponse` → frontend `fetch().body.getReader()` → `<GemmaTrace>` props. Three contract surfaces are touched: (a) the `ToolCallTurn` dataclass shape, (b) the `generate_with_tools_loop` signature, (c) the `AskResponse.tool_calls` element schema. All three are additive in shape (default-valued field, default-None kwarg, dict→typed-model with same keys plus enrichment).

#### Data Flow Analysis
- **Bronze/Silver/Gold:** unchanged — no MCP tool surface change, no new DuckDB query.
- **Gemma loop boundary:** new `on_turn_event` callback fires after `tool_call_log.append(...)` at `gemma_client.py:1090`. Logging contract preserved — `_log_tool_turn` still fires unchanged (line 1099 in tool-dispatch branch; lines 1032 transport-error, 1045 plain-text branches do NOT append a `ToolCallTurn`). One callback call per appended `ToolCallTurn`, never per `_log_tool_turn`. The spec text at §4 row 274 is internally inconsistent with §4 line 330 — see C2.
- **Service → router boundary:** `chat_ask_stream` yields typed `TraceEvent` discriminated-union models. Router serializes via `model_dump(mode="json")` and frames via the new shared `sse_event(...)`. Clean.
- **Router → frontend boundary:** SSE frames over `text/event-stream`. Mirrors the working pattern at `routers/builds.py:226`. Headers correct for both Ollama-local and OpenRouter-cloud paths (`Cache-Control: no-cache` + `X-Accel-Buffering: no`).
- **Frontend fallback:** `askGemmaStream` catches transport failure, calls `askGemma`, synthesizes `turn_start`+`turn_complete` pairs from `AskResponse.tool_calls`. Same `<GemmaTrace>` consumes both. Contract holds.

#### Contract Review
- `TraceEvent` discriminated union via `Annotated[T1 | T2 | T3 | T4, Field(discriminator="type")]` with `Literal["..."] = "..."` is the correct Pydantic v2 idiom.
- `AskResponse.tool_calls: list[TraceEventPayload]` — the prior shape was `list[dict[str, Any]]` populated with the lossy `{tool, ok, duration_ms}` summary at `ask_gemma.py:323-330`. The new typed shape adds `turn`, `args`, `result_preview`, `error` (renames `ok` → `error is None` semantically). Old test consumers reading `["ok"]` will break — partially flagged in Authorized Test Modifications, but see C7 for tests the spec missed.
- `ToolCallTurn` adds `tool_result_preview: str = ""` with a default. Backward-compatible for callers that construct via kwargs but NOT for callers that construct positionally. None of the existing call sites construct positionally — verified via grep (`gemma_client.py:1090` uses kwargs; `tests/services/test_set_your_course_chip_tool_loop.py:103` uses kwargs; `tests/routers/test_ask_gemma_router.py:718` uses kwargs).

#### Findings

##### Sound
- **Brightsmith zones untouched.** Confirmed no Bronze/Silver/Gold/MCP changes; @fp-data-reviewer skip is correct.
- **`_sse_event` extraction is byte-identical.** Verified `routers/builds.py:226-228` matches the proposed `sse_event` body exactly (`json.dumps(data, default=str, ensure_ascii=False)` + same f-string). No behavioral drift risk.
- **SSE event schema extensibility holds.** The discriminated union is open under addition — `feature-agentic-school-research.md` can add new variants without breaking existing consumers.
- **Fallback path shape parity.** `synthesizeEventsFromToolCalls` produces `turn_start + turn_complete` pairs in array order; `<GemmaTrace>` is order-driven. Live and post-hoc feeds render identically.
- **Loop signature change is kwarg-only and defaulted.** `set_your_course.py:834` and the existing `ask_gemma.py:302` call with kwargs only and don't pass `on_turn_event` — verified no-op by inspection.
- **Endpoint mirrors existing 404 contract.** `POST /chat/ask/stream` raises `HTTPException(404)` on `FileNotFoundError` from `builds.load_build`, matching existing `POST /chat/ask`.
- **Both backends supported.** `_tools_loop_inner` already abstracts Ollama (line 1247) vs OpenRouter (line 1189). Callback fires from the shared dispatch loop — no per-backend code path.
- **`logs/gemma.jsonl` discipline preserved.** Callback fires AFTER `_log_tool_turn`; no double-log, no skip.

##### Concerns

- **C1 (Significant) — `turn_start` vs `turn_complete` use INCOMPATIBLE turn-number schemes.** In `_tools_loop_inner` the loop variable `turn` (line 998) is the OUTER for-loop index, and a single outer turn can dispatch MULTIPLE tools because the inner loop iterates `for tc in response_tool_calls:` (line 1057). So two `ToolCallTurn`s appended in the same outer turn share the same `turn_number`. Meanwhile, the spec's `_wrap_dispatch` uses a local `_turn_counter` that increments per dispatch (one per `ToolCallTurn`). When Gemma returns parallel tool calls in one turn, the frontend cannot correlate `turn_start{turn=N}` to `turn_complete{turn=N}` — the start counter is per-dispatch (0,1,2,...) and the complete counter is per-LLM-turn (0,0,0). Rows pair wrong, render wrong order, or render duplicates. Today the loop drops tools after first dispatch via `tool_dispatched = True` (line 1112), so multi-call cases are rare, but the data path supports them. **Impact:** latent UI corruption; also blocks the `feature-agentic-school-research.md` reuse case since that spec explicitly handles parallel calls. **Recommendation:** unify on a single per-dispatch index. Either (a) add `dispatch_index: int` to `ToolCallTurn` and use it for the SSE `turn` field on BOTH events, or (b) emit `turn_start` from a NEW callback `on_dispatch_start: Callable[[int, str, dict[str, Any]], Awaitable[None]] | None = None` fired right before `await dispatch(...)` at gemma_client.py:1069 with index `len(tool_call_log)`. Then `turn_complete` carries `len(tool_call_log) - 1` post-append. Both sides agree. (@genai-architect independently caught this same defect — see their finding #1.)

- **C2 (Significant) — Spec internal inconsistency on which turns emit.** §4 row 274 says callback fires "after each turn (both tool-dispatch turns and final-text turns)." §4 line 330 says "fired exactly once per `ToolCallTurn` appended to `tool_call_log`." These contradict: the final-text-only turn (line 1043 branch) and transport-error turn (line 1030 branch) do NOT append a `ToolCallTurn`. **Recommendation:** strike the parenthetical at §4 row 274. Contract is "one callback per appended `ToolCallTurn`." Final-text and transport-error are surfaced via the `(text, log)` return tuple, not the callback — `chat_ask_stream` already converts those into `TraceFinalText` separately.

- **C3 (Significant) — `loop_task` exception leaks past `chat_ask_stream`'s "Never raises" contract.** Spec §4 line 451: *"Never raises."* But §4 line 505 does `text, _log = await loop_task` with no try/except. `generate_with_tools_loop` returns `("", [])` on transport failure but can RAISE if (a) `_dispatch` / `_wrap_dispatch` raises an unhandled exception, (b) `on_turn`'s `await queue.put(...)` deadlocks then is cancelled, (c) any uncovered code path in `_tools_loop_inner`. If it raises, the SSE generator propagates the exception mid-stream — `final_text` and `done` never fire. The frontend's `askGemmaStream` will see a malformed stream and trigger fallback (works), but server-side this is a 500. **Recommendation:** wrap `await loop_task` in `try/except Exception`; on exception yield `TraceFinalText(chat_unavailable) + TraceDone`, log warning. Mirrors `ask_gemma.chat_ask`'s defensive pattern.

- **C4 (Significant) — Client disconnect leaks `loop_task` and stalls the queue callback.** When the SSE client disconnects, FastAPI calls the generator's `aclose()`, which raises `GeneratorExit` at the active `yield ev`, exiting the `while` loop. But `loop_task` is NOT cancelled — Gemma keeps running, callbacks keep firing, `await queue.put(...)` eventually blocks at maxsize=64. The Gemma loop then stalls because the callback await never returns. The Gemma semaphore (line 959) is held until the wall-time cap (30s). P1 test `test_stream_cancelled_when_client_disconnects` is listed but the implementation in §4 doesn't include cancellation logic. **Impact:** under demo conditions (student closes chat tab mid-response), the next chat request can stall up to 30s waiting for the orphaned semaphore. **Recommendation:** wrap the drain loop in `try/finally: loop_task.cancel(); await asyncio.gather(loop_task, return_exceptions=True)`. Spec must show the finally block explicitly. Promote the test to P0.

- **C5 (Significant) — Backpressure handling is incorrect as specified.** The spec's `on_turn` does `await queue.put(TraceTurnComplete(...))`. If the queue is full (maxsize=64), `queue.put` BLOCKS — it does not raise. The spec's claim at §4 line 330 ("Failure of the callback must NOT break the loop — wrap in try/except and log a warning") addresses RAISE, not BLOCK. With max ~3 turns × ~5 parallel calls = ~15 events per chat, queue overflow is theoretically impossible — but the P2 test `test_stream_back_pressure_queue_full_recovers` acknowledges the case. **Recommendation:** either (a) change to `queue.put_nowait(...)` and on `QueueFull` log + drop the event (degrade visible trace, keep loop alive), OR (b) raise `maxsize` to 256+ with documented "max event count is bounded by max_turns × max_tools_per_turn." Pick one and update §4.

- **C6 (Significant) — Spec misses `routers/set_your_course.py:38` — a SECOND copy of `_sse_event`.** The spec extracts the helper from `routers/builds.py:226-228` only. But `routers/set_your_course.py:38-41` has a byte-identical second copy (verified — same `json.dumps(data, default=str, ensure_ascii=False)` + same f-string). If the goal is "single source of truth," both must be replaced. **Recommendation:** add `routers/set_your_course.py` to the File Changes table as a one-line import update. Verify any tests for that router still work post-extraction.

- **C7 (Significant) — Three test files NOT in the Testing Impact Analysis touch the changed surface.** Spec lists `test_gemma_client.py`, `test_ask_gemma.py`, `test_set_your_course.py`, `test_soc_expansion.py`, plus screen tests. Missing:
  - `backend/tests/services/test_set_your_course_chip_tool_loop.py` — constructs `ToolCallTurn(...)` literal at line 103 (kwargs, so default `tool_result_preview=""` will satisfy it; verify no asserts on field count). Patches `generate_with_tools_loop` at multiple lines.
  - `backend/tests/services/test_ask_gemma_voice.py` — patches `generate_with_tools_loop` at lines 234, 280, 435, 501. Spec's "Confirmed Safe" list mentions this file but should also verify `fake_loop` signatures don't reject the new kwarg (kwargs-only so likely safe — but flag it).
  - `backend/tests/routers/test_ask_gemma_router.py` — constructs `ToolCallTurn(...)` literal at line 718; patches `generate_with_tools_loop` at lines 155, 406, 438, 486, 734, 795. The spec's Authorized Test Modifications says "Existing `POST /chat/ask` tests unchanged" — incorrect: `ToolCallTurn(...)` literal at line 718 needs `tool_result_preview` added (or relies on the default — verify), and any test asserting `AskResponse.tool_calls` shape will need the enriched-payload migration.
  
  **Recommendation:** add these three files to the "Existing Tests at Risk" table with explicit assessment. The implementer needs an exhaustive list — surprises here will trip the "any unauthorized test failure = STOP" rule.

##### Minor

- **M1 — Spec wording at §4 row 274** ("after each turn (both tool-dispatch turns and final-text turns)") should be tightened per C2.
- **M2 — `await queue.get()` 50ms poll wastes CPU.** A cleaner pattern: have the loop_task add a `done_callback` that pushes a sentinel (`None`) onto the queue, then drain with `await queue.get()` until sentinel. Eliminates the 20Hz idle spin and the 50ms latency floor. Not blocking — works as written.
- **M3 — On Gemma transport failure** (`_log` returns empty), the user sees the in-progress shimmer until the wall-time cap (≤30s) before the `chat_unavailable` fallback text appears. Acceptable, worth noting in §3 so the visionary's "streaming" state design accommodates a long shimmer.
- **M4 — `asyncio.gather(*(asyncio.to_thread(builds.load_build, bid) ...))` runs synchronously before the SSE stream opens.** Latency cost is minor (one fs read per build, <50ms total). Matches existing `/chat/ask`. No change.
- **M5 — `AskResponse.tool_calls` shape change is a typed-consumer breaking change.** All current consumers are internal. Worth a one-line note in the spec for any future external API contract.
- **M6 — Sync vs async callback ergonomics.** @genai-architect raised that `on_turn_event: Callable[[ToolCallTurn], Awaitable[None]]` requires async-only callables, which makes test fixtures awkward. An `iscoroutinefunction` branch in the invocation shim costs ~3 lines and makes test authoring cleaner. Not required for correctness — recommend adopting their suggestion.

##### Blockers
None.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED — must fix before implementation)

1. **Fix C1 (turn-number scheme).** Add `dispatch_index: int` to `ToolCallTurn` (or use the `on_dispatch_start` two-callback approach), and have BOTH `turn_start` and `turn_complete` use that single per-dispatch counter for the SSE `turn` field. Spec §4 must show the unified scheme in the data model + the new `_wrap_dispatch` / callback bodies. The frontend's row-correlation logic in `<GemmaTrace>` correlates by this index — call it out in §3. (@genai-architect's finding #1 is the same defect; coordinate the fix.)
2. **Fix C2 (spec internal inconsistency).** Strike "(both tool-dispatch turns and final-text turns)" at §4 row 274. State explicitly: callback fires once per `ToolCallTurn` appended to `tool_call_log`, never on the final-text or transport-error branches.
3. **Fix C3 (loop_task exception handling).** §4 `chat_ask_stream` body must wrap `await loop_task` in try/except and yield `TraceFinalText(chat_unavailable) + TraceDone` on any exception. Document: "Never raises past the generator boundary."
4. **Fix C4 (client-disconnect cancellation).** `chat_ask_stream` must use `try/finally: loop_task.cancel(); await asyncio.gather(loop_task, return_exceptions=True)` around the drain loop. Show explicitly in §4. Promote `test_stream_cancelled_when_client_disconnects` from P1 to P0.
5. **Fix C5 (backpressure).** Pick option (a) `put_nowait` + drop on QueueFull, OR (b) raise maxsize to 256 with documented bound. Update §4 callback body to show the chosen strategy.
6. **Fix C6 (second `_sse_event` copy).** Add `routers/set_your_course.py:38-41` to File Changes — replace with import from `app.services._sse`. Single source of truth.
7. **Fix C7 (missing test files).** Add `test_set_your_course_chip_tool_loop.py`, `test_ask_gemma_voice.py`, `test_ask_gemma_router.py` to the Testing Impact Analysis tables with explicit Authorized Test Modifications entries. Inventory exhaustively so the implementer doesn't trip the "unauthorized failure = STOP" rule.

Once these seven conditions are addressed in §4 (and §3 for C1's UI implication), I expect to APPROVE on re-review. The architecture is fundamentally sound — the seam choice (opt-in callback on the existing loop), the SSE pattern reuse, the typed event union, and the dual-feed `<GemmaTrace>` consumer are all the right calls. The issues are correctness defects in the proposed implementation sketch, not architectural mistakes. Per CLAUDE.md escalation rules, CHANGES REQUESTED (Significant) requires STOP and human alert before proceeding to Step 2.

### @genai-architect Review (rev 1.1)
**Status:** REVIEWED
**Re-reviewed:** 2026-05-01

#### Re-Review Findings

**Item A — Symmetric one-place emission: PASS**

Decision #12 and the revised §4 spec text together constitute a clean resolution. Both `on_turn_start` and `on_turn_event` now fire from inside `_tools_loop_inner`. The emission contract at §4 (Data Model Changes) is explicit: `on_turn_start(dispatch_index, fn_name, fn_args)` fires immediately before `await asyncio.wait_for(dispatch(...))` at line 1069; `on_turn_event(turn_obj)` fires immediately after `tool_call_log.append(...)` at line 1090. Both callbacks share the same `dispatch_index` (captured as `len(tool_call_log)` before the append), which is the pairing key the frontend uses.

The `on_turn_start` signature `(dispatch_index: int, name: str, args: dict[str, Any])` is adequate for the `research_job.py` "mark step in-progress" use case. The three arguments are exactly what that caller needs: the stable row key, the tool being called, and the arguments for a meaningful progress label. The fact that `dispatch_index` is computed before any mutation of `tool_call_log` ensures it is stable across the async gap between start and complete.

The dispatch-raises scenario was an open question going into this re-review. Reading the `chat_ask_stream` implementation in §4 Service Changes: `on_turn_start` is fired (via its callback slot in `_tools_loop_inner`) before `dispatch` is awaited. If `dispatch` then raises, the loop's error-handling path appends a `ToolCallTurn` with `error` populated (and `duration_ms` set). That append fires `on_turn_event`, which puts a `TraceTurnComplete` with `error != None` onto the queue. So `on_turn_event` WILL receive the error-bearing turn — the frontend receives both start and complete for the failing dispatch, and renders an error pill on that row. The `chat_ask_stream` service body confirms this: the `try/except Exception` at the `await loop_task` site catches any exception that escapes past the tool-level error handling, and yields `TraceFinalText(chat_unavailable) + TraceDone`. No orphaned `turn_start` without a matching `turn_complete`. The error surface is fully accounted for.

One implementation note: the spec says both callbacks are wrapped in `try/except Exception`, and the exception is logged at WARNING and swallowed. The spec also notes that the invocation shim uses `asyncio.iscoroutine` on the return value. This is workable — `asyncio.iscoroutine(result)` correctly distinguishes a coroutine object (needs awaiting) from None (discard). The distinction from `iscoroutinefunction` is that it checks the return value rather than the callable itself, which handles the `Callable[..., Awaitable[None] | None]` type correctly: a sync callable returns None, an async callable returns a coroutine. The implementer should be aware that this check happens post-call, meaning a sync callable IS called before the check — which is correct behavior here.

**Item B — Forward-compat parser requirement: PASS**

Decision #15 and the "Frontend SSE Parser — Forward-Compat Requirement" subsection in §4 are explicit and strong. The spec uses mandatory language throughout: "MUST return `null` (not throw, not propagate)", "MUST continue reading after receiving `null`", "MUST NOT abort the stream or trigger fallback." The section names the specific future event types this protects against (`thinking`, `final_text_delta`, `tool_partial_result`) and explains WHY the requirement exists, which makes it actionable for both the implementer and a future code reviewer.

The requirement is enforced at two levels: the parser contract (return null, never throw) and the reader loop contract (continue after null). Both are now in the spec. The test `test_unknown_event_type_returns_null_not_throw` listed in New Tests Required correctly validates both levels per its description: "returns null, does NOT throw, does NOT propagate... The reader loop continues — no fallback triggered, no stream abort. Subsequent known events still dispatch correctly." This is precisely what was missing in rev 1.0, and it is correctly specified now.

**Item C — `dispatch_index` as substitute for `call_index`: PASS with a noted trade-off**

The author's argument is sound for this spec's scope. `dispatch_index = len(tool_call_log)` at the moment of dispatch is monotonically unique across the entire chat turn, including the parallel-calls case where multiple `ToolCallTurn`s share `turn_number`. The P0 test `test_dispatch_index_unique_across_parallel_calls` verifies the parallel case explicitly.

The question I raised was whether a future "summarize this turn" UI would need to group events by outer LLM turn. That grouping IS still achievable with the current design: `ToolCallTurn.turn_number` is preserved on the dataclass for telemetry continuity, even though SSE events use `dispatch_index`. A future UI that wants outer-turn grouping can read `turn_number` from the `TraceTurnComplete` payload — or, if needed, the spec can add `outer_turn` to the SSE payload as an additive field. The discriminated union pattern makes such additions non-breaking. The subsumption is clean; `call_index` as a separate field would have been redundant given that `turn_number` already provides the grouping anchor.

**Item D — Sync callback support: PASS**

The type signatures `TurnStartCallback = Callable[[int, str, dict[str, Any]], Awaitable[None] | None]` and `TurnEventCallback = Callable[[ToolCallTurn], Awaitable[None] | None]` correctly express the intent: the callable may return either a coroutine (async def) or None (def). The `Awaitable[None] | None` return annotation is accurate — a sync callable's `None` return satisfies this union. The spec's description of the invocation shim ("detect sync vs async via `asyncio.iscoroutine` on the return value") is the right implementation approach for this annotation. The P0 test `test_callback_accepts_sync_callable` completes the specification by requiring both sync and async callables to be exercised without TypeError. The coverage is complete.

One minor note: `Callable[..., Awaitable[None] | None]` appears in prose, but the actual type aliases use explicit arg-list forms. The explicit-arg-list forms in the aliases are correct and preferred over `...` for type safety. No issue.

**New contract issues introduced in rev 1.1: NONE**

Surveying the rev 1.1 changes for issues not present in rev 1.0:

- The removal of `_wrap_dispatch` from `chat_ask_stream` and the substitution of plain `mcp_client.call_async` as the `dispatch` argument is clean. The loop's existing timeout logic (`asyncio.wait_for(dispatch(...), ...)`) still applies to the plain callable. No behavioral change at that boundary.
- The `asyncio.Queue(maxsize=256)` with `await queue.put(...)` (rather than `put_nowait`) means a full queue blocks the callback — but the documented worst-case bound of ~30 events against a 256-cap makes this unreachable in practice. The bound is documented and the test `test_stream_back_pressure_under_bounded_queue` (P2) validates it. Acceptable.
- The `try/finally` in `chat_ask_stream` correctly handles the `GeneratorExit` path (client disconnect) without introducing any new exception surface. `asyncio.gather(loop_task, return_exceptions=True)` in the finally block is the correct idiom for awaiting a cancelled task without propagating its `CancelledError`.
- The `on_start` closure inside `chat_ask_stream` puts `TraceTurnStart` using the callback's `dispatch_index` argument. The `on_turn` closure puts `TraceTurnComplete` using `turn.dispatch_index`. These are the same value, captured at the same point (`len(tool_call_log)` before append). The pairing contract is correct.

#### Original Findings (rev 1.0 — superseded)

**1. `ToolCallTurn` dataclass shape and callback signature richness**

The current seven-field shape (`turn_number`, `tool_name`, `tool_args`, `tool_result_size_bytes`, `tool_result_preview`, `duration_ms`, `error`) is adequate for this spec and for the agentic-school-research reuse case. `feature-agentic-school-research.md` defines its own `ToolCallRecord` with an identical field set (`turn_index`, `tool_name`, `arguments`, `result_preview`, `result_size_bytes`, `duration_ms`, `error`), which confirms the shape will transfer cleanly. One minor naming divergence to note: the loop uses `turn_number`; the research spec uses `turn_index`. Not a breaking issue now since `ResearchJob` defines its own internal model, but worth standardizing before the research spec is implemented.

One forward-compatibility gap worth a zero-cost fix: **there is no `call_index` or `parallel_call_index` field**. Gemma 4 does support parallel tool calls (multiple `tool_use` content blocks in a single model turn), and `generate_with_tools_loop` would need to handle them in a single iteration. If that ever occurs, two `ToolCallTurn` objects could share the same `turn_number`, making ordering ambiguous in the trace. Adding an `call_index: int = 0` field now (defaulting to 0 so all existing callers are unaffected) would let a future implementer set it without a breaking schema change. Low-cost, good insurance.

The `on_turn_event: Callable[[ToolCallTurn], Awaitable[None]] | None` signature is appropriate. One ergonomics note: the spec requires callers to pass async-only callables. A sync callback (e.g. a unit-test spy using a plain list append) requires wrapping. Adding `asyncio.iscoroutinefunction`-branching inside the loop's invocation shim so it handles both `async def` and `def` callbacks costs ~3 lines and makes test fixtures cleaner. Not required for correctness, but recommended before the first test author hits it.

**2. Turn-start emission point and the two-callback asymmetry**

The spec emits `turn_start` from `_wrap_dispatch` in `chat_ask_stream` (router-adjacent layer) and `turn_complete` from `on_turn_event` inside the loop. This is a genuine architectural smell, not a cosmetic one. The consequence is exactly as stated in the review prompt: any future caller who wants `turn_start` semantics must independently replicate the dispatch-wrapping pattern. The agentic-school-research spec is the next concrete consumer, and it uses `generate_with_tools_loop` directly from `research_job.py` — a background job runner with no SSE layer. If that spec ever wants a `turn_start` event (e.g. to update job state in DuckDB as Gemma works), it would have to build its own `_wrap_dispatch` wrapper from scratch.

The cleanest correction is a second callback parameter: `on_turn_start: Callable[[int, str, dict[str, Any]], Awaitable[None]] | None = None`, fired inside `_tools_loop_inner` immediately before `dispatch(name, args)` is awaited, carrying `(turn_number, tool_name, tool_args)`. This eliminates the two-layer emission entirely. Both `turn_start` and `turn_complete` then originate from one place (the loop), the dispatch wrapper in `chat_ask_stream` is simplified to a pass-through, and future callers get both events for free.

If accepting a second parameter is considered too much change for this spec, an acceptable middle path is the `phase: Literal["start", "complete"]` field on `ToolCallTurn` itself, with the loop firing the callback twice per turn (once pre-dispatch, once post-dispatch). This is slightly odd semantically since the "start" fire lacks `duration_ms`, `tool_result_preview`, and `error` (they are only available post-dispatch), but the shape would remain a single type. On balance the two-parameter approach is cleaner. **This is a CHANGES REQUESTED item — it is a foreseeable breaking-change point if left unaddressed before the agentic-school-research spec is revived.**

**3. SSE event union and forward compatibility**

The discriminated union (`TraceTurnStart | TraceTurnComplete | TraceFinalText | TraceDone`) with `Literal["turn_start"] = "turn_start"` discriminators is idiomatic Pydantic v2. The backend union is correctly typed.

The critical forward-compatibility gap is on the **frontend parser**. The spec's `parseSSEFrame` returns `GemmaTraceEvent | null`, but the spec does not state what happens when the `type` field is an unrecognized string. If the implementation throws or returns null-with-a-logged-error, unknown event types from a future backend version will silently drop, which is the correct behavior. If the implementation throws or propagates the error up the read loop, a backend that emits a new `thinking` event type would break an older frontend. The spec must explicitly require `parseSSEFrame` to return `null` for unknown `type` values (not throw). This is a **one-line requirement addition** to the spec and a correspondingly simple implementation constraint. Without it, the forward-compatibility claim is unverified.

Regarding versioning: an explicit `v` field or `schema-version` SSE header is overkill for a 17-day hackathon. The discriminator pattern already provides per-event forward compatibility if the parser is spec'd correctly (see above). Not flagging this as a required change.

The `final_text` event carries the full response string in one payload. The schema is compatible with a future token-streaming addition. Adding `final_text_delta` events (carrying incremental `text: string` chunks) would not conflict with the existing `final_text` event, since the discriminator field cleanly separates them. Consumers that know only `final_text` would receive a `null` from `parseSSEFrame` for each `final_text_delta` frame and skip them gracefully — provided the forward-compat parser requirement above is implemented. The schema is fine as-is for this extension path.

**4. Frontend `TOOL_LABEL_MAP` scalability**

`Record<string, ToolLabel>` is the correct shape for a 5-tool registry today. The `test_unknown_tool_returns_default_label` test correctly establishes the forward-compat seam: unknown tools fall back to a default label and do not crash. This is the right design.

At 10+ tools (agentic-school-research adds `web_search` and `fetch_url`; future specs could add more), the static record remains maintainable — it is a flat key-value map, not a class hierarchy. The `hint` field as a function `(args: Record<string, unknown>) => string` is flexible enough to handle any future tool's argument shape without schema changes.

The spec does not need a backend-provided "tool catalog" endpoint for the hackathon. The static map with a graceful unknown-tool fallback is sufficient, and the default fallback test ensures it degrades cleanly when `<GemmaTrace>` is reused with tools outside the current five. If the agentic-school-research spec is revived, adding `web_search` and `fetch_url` entries to `TOOL_LABEL_MAP` is a two-entry addition, not a refactor.

**5. Reusability claim assessment against `feature-agentic-school-research.md`**

The claim in Decision #6 holds for the frontend `<GemmaTrace>` component: it is prop-driven (`events: GemmaTraceEvent[]`, `mode: "live" | "complete"`), produces no API calls, and the agentic-school-research spec defines a nearly identical tool-call chain display in its `ResearchChain.tsx`. A revived research spec could compose `<GemmaTrace>` as its chain renderer, or align the `ResearchToolCallView` API shape to match `GemmaTraceEvent` so the same component handles both surfaces.

The reusability gap is on the **backend callback contract**. The agentic-school-research spec explicitly notes it does NOT plan live SSE streaming of tool calls (§2 Out of Scope: "Real-time streaming of tool calls to frontend (SSE / WebSocket). Polling at /my-build load is sufficient"). So `research_job.py` will not use the SSE queue pattern. It will use `on_turn_event` to persist each `ToolCallRecord` to DuckDB as Gemma works, which is a clean use of the callback. However, it will have no way to emit `turn_start` events (per finding #2 above), meaning `ResearchChain.tsx` will always render in post-hoc mode (all rows resolved at once when polling returns). That is acceptable per the research spec's own decisions, but it is a gap relative to the "live chain" the research spec's §3 Loading state describes (animated row reveals transitioning from skeleton to resolved). If that animation is ever wanted, the two-callback fix (finding #2) is the unlock. Calling this out as a documented gap, not a blocker.

One concrete incompatibility: the agentic-school-research spec defines `ToolCallRecord.turn_index` (0-based) and `ResearchToolCallView.turn` (also 0-based), while `ToolCallTurn.turn_number` is the loop's field name. Before integrating, the field name should be standardized to `turn_index` across both the `ToolCallTurn` dataclass and all SSE event payloads, OR the research spec's models should alias it. Minor, but flag it now before both specs have tests that assert the field name.

#### Summary of Actionable Items (rev 1.0)

| # | Item | Cost | Required? |
|---|------|------|-----------|
| A | Add `on_turn_start` callback (or `phase` field) to eliminate two-layer emission asymmetry | ~15 lines in `gemma_client.py`, simplifies `_wrap_dispatch` | **Yes — CHANGES REQUESTED** |
| B | Spec `parseSSEFrame` must return `null` for unknown event types (not throw) | One sentence in spec + one line in implementation | **Yes — forward-compat is otherwise unverified** |
| C | Add `call_index: int = 0` to `ToolCallTurn` for parallel-tool-call safety | One field with a default; zero existing-caller impact | Recommended, not required |
| D | Allow sync callbacks via `asyncio.iscoroutinefunction` branching in the loop's callback invocation | ~3 lines | Recommended, not required |
| E | Standardize `turn_number` vs `turn_index` naming before research spec is revived | Rename in `ToolCallTurn` + SSE payload fields | Deferred to research spec kick-off |

Items A and B should be addressed in this spec before implementation begins. Items C and D are low-cost improvements worth doing in the same pass. Item E is explicitly deferred.

#### Verdict (rev 1.0)
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

Items A (turn-start emission model) and B (forward-compat parser requirement) are Significant issues that should be resolved before Phase A implementation begins. Neither requires a rearchitecture — they are small, targeted additions. Once addressed, this contract is extensible and the reuse claim holds.

---

#### Verdict (rev 1.1)
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All four items are resolved. Items A and B — both required — are correctly addressed by Decision #12 (symmetric one-place emission from inside `_tools_loop_inner`) and Decision #15 (explicit parser forward-compat requirement with mandatory reader-loop continuation). Items C and D — both recommended — are correctly adopted: `dispatch_index` cleanly subsumes the `call_index` concern while preserving outer-turn grouping capability via the retained `turn_number` field; sync callback support is correctly typed and tested. No new contract issues were introduced. Item E remains deferred per the original recommendation. Ready to proceed to Step 2 (Design Vision).

### @fp-data-reviewer Review
**Status:** SKIPPED — this spec does not modify Bronze/Silver/Gold pipelines, ingestors, transformers, Iceberg tables, stat formulas, or boss-fight data.

---

## §6 Implementation Log

**Status:** PHASES A + B COMPLETE — awaiting design audit + code review

### Files Modified

| File | Phase | Change Summary |
|------|-------|----------------|
| `backend/app/services/gemma_client.py` | A | Added `tool_result_preview: str = ""` and `dispatch_index: int = 0` to `ToolCallTurn` (trailing-position defaults). Added `on_turn_start` and `on_turn_event` opt-in callbacks to `generate_with_tools_loop` (default None). Added `_invoke_callback` shim — wraps every callback in try/except, detects sync vs async via `asyncio.iscoroutine(result)`. Inside `_tools_loop_inner`: captures `dispatch_index = len(tool_call_log)` before each `await dispatch(...)`, fires `on_turn_start(dispatch_index, fn_name, fn_args)` immediately before, populates `tool_result_preview` (≤500 chars) on the appended `ToolCallTurn`, fires `on_turn_event(turn_obj)` after append. Added `_TOOL_RESULT_PREVIEW_MAX = 500` constant. |
| `backend/app/services/_sse.py` | A | NEW. Shared `sse_event(event, data)` helper with the canonical `event:` / `data:` / `\\n\\n` framing. Single source of truth for the three router consumers (builds, set_your_course, ask_gemma_router). |
| `backend/app/routers/builds.py` | A | Removed local `_sse_event`; imports `sse_event` from `app.services._sse`. Renamed all call sites from `_sse_event` → `sse_event`. Removed unused `import json`. |
| `backend/app/routers/set_your_course.py` | A | Removed local `_sse_event`; imports `sse_event` from `app.services._sse`. Renamed all call sites. Removed unused `import json` and `from typing import Any`. |
| `backend/app/models/api.py` | A | Replaced `AskResponse.tool_calls: list[dict[str, Any]]` with `list[TraceEventPayload]` — enriched per-turn shape (`turn` = dispatch_index, `tool`, `args`, `result_preview`, `duration_ms`, `error`). Updated docstring noting frontend now consumes `tool_calls` for the `<GemmaTrace>` post-hoc fallback render. Added new SSE wire-format models: `TraceTurnStart`, `TraceTurnComplete`, `TraceFinalText`, `TraceDone`, plus the `TraceEvent` discriminated-union alias (`Annotated[T1\|T2\|T3\|T4, Field(discriminator="type")]`). Added `Annotated` import. |
| `backend/app/services/ask_gemma.py` | A | Imports `TraceDone, TraceEvent, TraceEventPayload, TraceFinalText, TraceTurnComplete, TraceTurnStart` from `app.models.api`. Updated `chat_ask` to populate `AskResponse.tool_calls` with the enriched `TraceEventPayload` shape (was the lossy `{tool, ok, duration_ms}` summary). Added `chat_ask_stream(...) -> AsyncIterator[TraceEvent]`: bounded queue `maxsize=256` (Decision #14), `on_turn_start` and `on_turn_event` callbacks enqueue typed events, drain loop interleaves with loop_task done-checks at 50ms poll, `try/except Exception` on `await loop_task` (C3) + `try/finally: loop_task.cancel(); asyncio.gather(...)` on cleanup (C4). Branch-opener path short-circuits to `final_text + done`. Added `_branch_opener_text` and `_build_context_block` helpers, extracted from `chat_ask` so both entry points share one implementation. |
| `backend/app/routers/ask_gemma_router.py` | A | Added `POST /chat/ask/stream` endpoint. Loads builds via `asyncio.gather(asyncio.to_thread(builds.load_build, bid))` (mirrors `/chat/ask`). Wraps `ask_gemma.chat_ask_stream` in `StreamingResponse(media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`. Inner `_stream` async-generator uses shared `sse_event` helper. 404 on `FileNotFoundError`. Catches `SkillNotFoundError` mid-stream (since headers are already sent) and yields a final `error` + `done` frame. |
| `backend/tests/services/test_sse.py` | A | NEW. 4 tests covering SSE format (exact `event:\\ndata:\\n\\n`), `default=str` encoder for datetime/UUID, non-ASCII preservation, JSON-parseability of the data line. |
| `backend/tests/services/test_ask_gemma_stream.py` | A | NEW. 8 tests covering: turn_start→turn_complete→final_text→done ordering, no-tool path emits only final_text+done, tool error preserves error pill in turn_complete + chat continues, transport failure → chat_unavailable fallback, loop_task exception → boundary defense (C3), queue drained after loop completes, **client-disconnect cancellation** (C4 — promoted to P0), bounded queue under 32-event load (C5 / Decision #14). Self-contained Build fixture (no DB write) so tests run as pure unit tests. |
| `backend/tests/services/test_gemma_client.py` | A | Added 11 new tests: `test_on_turn_event_default_is_noop`, `test_on_turn_start_default_is_noop`, `test_on_turn_event_fires_per_turn`, `test_on_turn_start_fires_before_dispatch`, `test_dispatch_index_unique_across_parallel_calls`, `test_on_turn_start_and_event_share_dispatch_index`, `test_on_turn_event_callback_failure_does_not_break_loop`, `test_on_turn_start_callback_failure_does_not_break_loop`, `test_callback_accepts_sync_callable` (Item D), `test_tool_result_preview_truncated`. Added `_MultiToolCallResponse` stub class for the parallel-call test. |
| `backend/tests/routers/test_ask_gemma_router.py` | A | Updated 2 existing assertions to enriched `TraceEventPayload` shape (was `{tool, ok, duration_ms}` — now `{turn, tool, args, result_preview, duration_ms, error}`). Added 3 new tests: `test_chat_ask_stream_endpoint_returns_sse` (content-type + headers), `test_chat_ask_stream_emits_all_event_types` (full SSE round-trip with parsed events), `test_chat_ask_stream_404_on_bad_build`. Added local `_parse_sse_events` helper. |
| `frontend/src/types/gemmaTrace.ts` | B | NEW. `GemmaTraceEvent` discriminated union (turn_start / turn_complete / final_text / done) mirroring backend wire-format models. `TraceMode` ("live" / "complete"). `ToolLabel` interface for the per-tool translation entry. |
| `frontend/src/components/menu/icons/` | B | NEW directory. 6 in-house SVG primitives (no new icon-library dependency, matches GemmaStar/GemmaSpinner pattern): `IconCareerCompass`, `IconBriefcaseStack`, `IconMapPin`, `IconScale`, `IconBranch`, `IconWrench` (fallback). All 16×16 viewBox, 1.5px stroke, currentColor inheritance. `index.ts` exports a `TRACE_ICONS` registry + `resolveTraceIcon(id)` helper that falls back to `IconWrench` for unknown ids. |
| `frontend/src/components/menu/toolLabels.ts` | B | NEW. `TOOL_LABEL_MAP: Record<string, ToolLabel>` for all 5 tools in `_TOOLS`. Each entry has `{label, icon, hint(args)}`. `hint` builders take the raw args and produce a pedagogical sentence — for `get_career_paths`, "Looking up career outcomes for {major}.", etc. `DEFAULT_TOOL_LABEL` + `resolveToolLabel(name)` provide the unknown-tool forward-compat seam. |
| `frontend/src/components/menu/toolLabels.test.ts` | B | NEW. 5 tests covering: every tool in the canonical 5-tuple has an entry, hint templates produce coherent sentences with realistic args, hint templates never crash on empty args, `resolveToolLabel` returns the default for unknown tool names. |
| `frontend/src/styles/tokens.css` | B | Added `--color-bg-recessed: rgba(27, 29, 48, 0.5)` token (per visionary §3 Brightpath References). Recessed inset surface used by the trace rail. |
| `frontend/tailwind.config.ts` | B | Added `bp.recessed: var(--color-bg-recessed)` to expose `bg-bp-recessed` Tailwind utility. |
| `frontend/src/index.css` | B | Added `@keyframes gemma-trace-pulse` (2.4s ease-in-out infinite, opacity 0.6 ↔ 1.0) + `.animate-gemma-trace-pulse` utility + `prefers-reduced-motion` override (holds at opacity 0.85). Slower than `card-breathe` (4s) and `chip-pulse-caution` (1.6s) so it remains patient at 0.3s AND at 30s durations. |
| `frontend/src/api/menu.ts` | B | Added `TraceEventPayload` interface (mirrors backend); updated `AskResponse.tool_calls` type from `{tool, ok, duration_ms}[]` to `TraceEventPayload[]`. Added `parseSSEFrame(frame): GemmaTraceEvent \| null` — returns null (never throws) on unknown event types per Decision #15. Added `synthesizeEventsFromToolCalls` helper for the post-hoc fallback render. Added `askGemmaStream(scope, message, history, onEvent, locale)`: POSTs to `/chat/ask/stream`, consumes via `fetch().body.getReader()`, parses SSE frames, dispatches per-event callback. On HTTP error or thrown exception, silently falls back to `askGemma` and synthesizes events from `tool_calls`. |
| `frontend/src/api/menu.stream.test.ts` | B | NEW. 9 tests covering: `parseSSEFrame` for each event type, **`test_unknown_event_type_returns_null_not_throw`** (Item B contract), malformed JSON → null, missing event/data → null, `askGemmaStream` happy-path SSE parsing, http-error fallback to `askGemma`, thrown-error fallback, mid-stream unknown event silently skipped. |
| `frontend/src/components/menu/GemmaTrace.tsx` | B | NEW. The reusable trace component. ~400 lines. Implements §3 visual spec: rail container with `accent-insight` left stripe, header with GemmaStar + spec-locked copy ("Gemma is looking things up…" / "Gemma checked N sources."), per-row icon + pedagogical label + status pill (`◆ done` / `◇ retry`) + duration micro-text + chevron. Click-to-expand engineering view (raw tool name in `accent-info`, args + result preview JSON pretty-printed via `safeFormatJson` helper, footer with duration + "step N of M" correlation reference). All 3 states (streaming / complete / fallback). `rowsFromEvents` correlates by `dispatch_index` (Decision #13). Empty events → returns null. Local `<TraceRow>`, `<StatusPill>`, `<EngineeringDetail>`, `<JsonHighlight>`-style helpers. |
| `frontend/src/components/menu/GemmaTrace.test.tsx` | B | NEW. 14 tests covering empty events → null, no-tool-calls scenario, streaming state shows pending row + disabled expand, complete state shows resolved row + duration, plural / singular header copy, error pill rendering + chat continues, click-to-expand reveals engineering view, collapse on second click, unknown tool falls back to default label, all §3 accessibility identifiers + aria-labels, **dispatch_index parallel-call correlation** (Decision #13 contract), fallback visual parity. |
| `frontend/src/components/menu/GemmaChat.tsx` | B | Integration. Imports `askGemmaStream` and `<GemmaTrace>`. Added `traces: Map<number, GemmaTraceEvent[]>` state (per-assistant-message-index). Added `liveEventsRef` for accumulating events. Both the `submit` flow and the embedded-mode auto-opener call `askGemmaStream` instead of `askGemma`, passing an `onEvent` callback that appends to the live ref + flushes into state. Added `renderMessageWithTrace` helper that renders `<GemmaTrace events={events} mode="complete" />` above each assistant message. While sending, an additional `<GemmaTrace events={liveEvents} mode="live" />` renders adjacent to the typing indicator. Updated reset effects to clear the trace map. Both panel variants (slide-in + embedded) updated. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | B | Added `mockAskGemmaStream` mock + `streamImpl(events)` helper that fires events into `onEvent` and returns `{response, events}`. `beforeEach` resets the new mock + sets a default happy-path impl. Updated 6 existing scope-bound tests to assert against `mockAskGemmaStream` instead of `mockAskGemma` (and use `streamImpl(...)` for canned responses). Added 3 new integration tests: `test_chat_renders_trace_when_tool_calls_present`, `test_chat_omits_trace_when_no_tool_calls`, `test_chat_falls_back_to_post_hoc_trace_on_stream_failure`. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | B | Per Authorized Test Modifications (§4 / C7). Added `mockAskGemmaStream` to the `@/api/menu` mock with happy-path default impl. Added `mockAskGemmaStream.mockClear()` to `beforeEach`. Updated 4 existing scope-routing test assertions (per-stat / per-boss / per-skill / FAB) to assert against `mockAskGemmaStream` instead of `mockAskGemma`. |
| `frontend/src/screens/FutureScreen.test.tsx` | B | Same treatment as BuildResultsScreen.test.tsx — added `mockAskGemmaStream` to the mock with happy-path default impl. (Existing tests use the auto-opener path and mock `askGemma` directly; the streaming default impl satisfies them with no further changes.) |
| `frontend/src/components/menu/CompareView.test.tsx` | B | Same treatment — added `mockAskGemmaStream` to the mock; updated the compare-scope dispatch test assertion to point at `mockAskGemmaStream`. |

### Deviations from Spec

None. Implementation follows §4 exactly.

### Build Accountability Log
| Attempt | Phase | Result | Error | Fix Applied |
|---------|-------|--------|-------|-------------|
| 1 | A — pytest first run | Failed | 9 tests in new files: (a) router test asserted `done_data == {}` but Pydantic emits `{"type": "done"}`; (b) 8 stream tests built `Build` fixture with wrong field set + DuckDB lock conflict | Updated assertion to `{"type": "done"}`; rebuilt fixture with required-field set per `Build.model_fields` introspection and direct constructor (no DB write) |
| 2 | A — pytest second run | All 1337 backend tests pass | — | — |
| 1 | A — ruff first run | 1 line-length error in `ask_gemma.py:533` (89 > 88) + 1 import-sort issue auto-fixed | Split the long f-string into two assignments |
| 2 | A — ruff second run | All checks passed | — | — |
| 1 | A — mypy first run | 70 errors total — only 1 NEW from changes (`_branch_opener_text` passed `str \| None` to `_context_for_branch`) | Added `assert scope.target_id is not None` (mirrors the existing pattern in `chat_ask`) |
| 2 | A — mypy second run | 0 NEW errors from changed files; 28 pre-existing errors in untouched code paths (unchanged from baseline) | Pre-existing — out of scope |

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added
| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | | | | |
| pytest (pipeline) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor) — rev 2 re-audit
**Status:** REVIEWED — rev 1 changes addressed
**Reviewed:** 2026-05-02
**Re-reviewed:** 2026-05-01

#### Re-Audit Findings

All five rev 1 failures were re-examined against the rev 2 implementation of `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/menu/GemmaTrace.tsx`.

- **F1 — PASS.** Line 283: `focus:outline-none focus-visible:ring-[3px] focus-visible:ring-focus-ring focus-visible:ring-offset-2`. Correct pseudo-class (`:focus-visible`), correct thickness (3px per DESIGN.md §Focus States), correct token (`focus-ring`), correct offset (2px). W2 also resolved: `min-h-[40px]` → `min-h-10` (Tailwind spacing token `10` = 40px).

- **F2 — PASS.** Lines 319–348: `<AnimatePresence initial={false}>` wraps `<motion.span key="resolved" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={springs.snappy} className="contents">` containing `<StatusPill>`, the duration `<span>`, and the chevron `<span>`. `springs.snappy` = `{ stiffness: 400, damping: 25 }` per DESIGN.md §Motion System. `className="contents"` is correct — `display: contents` removes the wrapper's box so the three children participate directly in the parent flex row, while Framer Motion still composites opacity on the element. Entrance animation fires once on mount when `row.resolved` transitions from null to object.

- **F3 — PASS.** Lines 155–166: `<AnimatePresence mode="wait" initial={false}>` wraps `<motion.span key={header} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2, ease: "easeOut" }}>`. Key is the header string itself, so the crossfade fires on every copy change (streaming → complete). 200ms ease-out matches the spec mandate.

- **F4 — PASS.** Line 364: `opacity: springs.smooth` on the engineering panel `motion.div` transition config. Both axes (`height` and `opacity`) now use the named Brightpath spring `springs.smooth` = `{ stiffness: 200, damping: 25 }`. No custom duration values remain.

- **F5 — PASS.** Lines 175–182: dedicated `<span data-testid="gemma-trace-live" role="status" aria-live="polite" className="sr-only">{header}</span>` is a sibling of `<header>` inside the wrapper `<div>`, not inside the header landmark. The `<header>` element no longer carries `aria-live`. Screen readers get the header text via the `role="status"` live region without conflicting with the implicit `banner` role of `<header>`. Duplicated text (visible animated span + sr-only span) is intentional and correct — the sr-only text is visually hidden and announced on update only.

No new compliance issues introduced by the rev 2 changes. The `className="contents"` pattern (F2) does not break layout — it is a standard CSS technique for transparent wrapper elements in flex containers. The sr-only duplicate text (F5) does not create an A11y regression — `sr-only` elements are not exposed as visible content and the duplication is the intended pattern for live regions that mirror visible copy.

---

#### Original Findings (rev 1)

##### `frontend/src/styles/tokens.css`

**PASS**
- `--color-bg-recessed: rgba(27, 29, 48, 0.5)` added at line 25, positioned in the Backgrounds block between `--color-bg-deep` and the Accents section, with a comment citing the spec. Value matches §3 Brightpath References exactly.

---

##### `frontend/src/index.css`

**PASS**
- `@keyframes gemma-trace-pulse` added at lines 288–291: `0%, 100% { opacity: 0.6 }` / `50% { opacity: 1.0 }` — duration, easing, and repeat values all match the spec.
- `.animate-gemma-trace-pulse` utility added: `animation: gemma-trace-pulse 2.4s ease-in-out infinite`. Correct.
- `@media (prefers-reduced-motion: reduce)` override holds opacity at `0.85` and disables animation — matches spec contract exactly.
- Keyframe positioned after `gemma-shimmer` and before `chip-pulse-caution`, consistent with the proposed DESIGN.md insertion point.

---

##### `frontend/tailwind.config.ts`

**PASS**
- `bp.recessed: "var(--color-bg-recessed)"` added at line 42, generating `bg-bp-recessed`. Correctly references the new CSS variable. Token is available throughout the Tailwind utility namespace.

---

##### `frontend/src/components/menu/icons/` (all six icons)

**PASS**
- All six icons (`IconCareerCompass`, `IconBriefcaseStack`, `IconMapPin`, `IconScale`, `IconBranch`, `IconWrench`) use `viewBox="0 0 16 16"`, `strokeWidth="1.5"`, `stroke="currentColor"`, `fill="none"`, `strokeLinecap="round"`, `strokeLinejoin="round"`, and `aria-hidden="true"`. All match the shared icon spec.
- Props interface is `{ size?: number; className?: string }` with `size` defaulting to `16`. `currentColor` inheritance is correct — no hardcoded stroke or fill colors on any path/line/circle. Center-dot fills use `fill="currentColor"` which correctly inherits from the cascade.
- No icon-library dependency introduced.

---

##### `frontend/src/components/menu/GemmaTrace.tsx`

**PASS**
- Rail container (line 140): `bg-bp-recessed border border-border-subtle rounded-lg overflow-hidden` — correct tokens. `rounded-lg` = 14px, `border-border-subtle` = `rgba(255,255,255,0.06)`.
- Rail left stripe (line 145): `borderLeft: "3px solid var(--color-accent-insight)"` — CSS variable by name, not hex. Correct.
- Header typography (line 155): `font-body text-small text-text-secondary` — matches §3 (`font-body`, `text-small` 14px, `text-secondary`).
- Header sparkle (line 154): `<GemmaStar size={12} />` — matches spec exactly.
- Row hairline divider (line 240): `border-t border-border-subtle` — correct token.
- Row in-progress background (line 230): `bg-state-loading` — maps to `var(--color-state-loading)` (`rgba(184,169,232,0.15)`) per tailwind.config.ts. Correct.
- Row expanded background (line 232): `bg-bp-mid` — correct token (`#232545`).
- Row hover background (line 233): `hover:bg-white/[0.04]` — spec explicitly documents `rgba(255,255,255,0.04)` as the Ghost Button hover wash, an accepted inline value per §3 Brightpath References table.
- Row button radius (line 255): `rounded-sm` = 6px per DESIGN.md. Correct.
- Row hover/chevron transition (line 256, 301): `transition-colors duration-fast` / `transition-transform duration-fast` — `duration-fast` = 150ms ease-out. Matches `transition-fast` spec.
- Icon color states (lines 267–270): `text-accent-insight` (in-progress), `text-text-muted` (error), `text-accent-info` (default) — all match §3 Brightpath References.
- In-progress pulse (lines 267, 280): `.animate-gemma-trace-pulse` — correctly references the new keyframe utility.
- Pedagogical label typography (line 278): `font-body text-body-sm` — `text-body-sm` = 15px, `font-body` = Nunito. Matches spec.
- Duration micro-text (line 293): `font-data text-data-sm text-text-muted` — matches spec (`font-data`, 13px, `text-muted`).
- Chevron (lines 299–305): `▸` glyph, `font-data text-micro text-text-muted`, `transition-transform duration-fast`, `rotate-90` on expand — all correct tokens.
- Status pill shape (lines 351–363): `px-2 py-[2px] rounded-full font-body text-micro font-semibold` — `rounded-full`, `font-body`, `text-micro` (12px), weight 600. Correct.
- Status pill colors — success (line 356): `bg-accent-thrive/15 text-accent-thrive` — generates `rgba(125,212,163,0.15)` + `accent-thrive`. Correct.
- Status pill colors — error (line 355): `bg-accent-alert/15 text-accent-alert` — generates `rgba(244,169,126,0.15)` + `accent-alert`. Correct.
- Engineering panel (lines 396–399): `bg-bp-mid border border-border-subtle rounded-md font-data` — `bg-bp-mid` (#232545), `border-subtle`, `rounded-md` (10px), `font-data`. All correct.
- Tool-name field (lines 401–403): `font-data text-data-sm`, `text-text-muted` prefix, `font-bold text-accent-info` tool name — matches spec (`font-data`, 13px, 700, `accent-info`).
- Args/result block labels (lines 407, 417, 426): `font-body text-stat-label font-semibold uppercase tracking-[1px] text-text-muted / text-accent-alert` — `font-body`, `text-stat-label` (10px), weight 600, uppercase. Correct. (See W3 on `tracking-[1px]`.)
- Args/result JSON body (lines 410, 420, 429): `font-data text-data-sm leading-relaxed` — correct font and size.
- Engineering footer (line 435): `font-data text-micro text-text-muted` — matches spec.
- Engineering panel height expansion (line 323): `height: springs.smooth` — correct spring token.
- No hex colors anywhere in GemmaTrace.tsx. No inline rgba values except the documented `white/[0.04]` Ghost Button wash.
- Accessibility identifiers: `gemma-trace` (region), `gemma-trace-rows` (list), `gemma-trace-row-{turn}` (motion.li — implicit listitem), `gemma-trace-expand-{turn}` (button with `aria-expanded`, `aria-controls`), `gemma-trace-detail-{turn}` (region), `gemma-trace-live` (aria-live=polite) — all spec-mandated identifiers present.

**FAIL**

- **F1 — Focus ring: wrong pseudo-class and wrong thickness** (`GemmaTrace.tsx` line 257): Implementation uses `focus:ring-2 focus:ring-focus-ring`. DESIGN.md §Focus States requires `:focus-visible` (not `:focus`) and **3px** ring thickness (not 2px, which is what Tailwind `ring-2` produces). Expected: `focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-focus-ring focus-visible:outline-offset-2` or equivalent `focus-visible:ring-[3px]` variant. Found: `focus:ring-2 focus:ring-focus-ring` (wrong pseudo-class, wrong thickness).

- **F2 — Status pill / duration / chevron: no entrance animation on resolution swap** (`GemmaTrace.tsx` lines 288–307): Spec mandates status pill, duration, and chevron "fade in (`opacity 0 → 1`, `springs.snappy` 400/25)" when a row resolves. The implementation conditionally renders these elements with no `AnimatePresence` wrapping and no `motion` component — they mount synchronously. Expected: `<AnimatePresence>` + `<motion.span>` (or similar) with `initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={springs.snappy}` on the resolved-state group. Found: plain `{row.resolved !== null ? (...) : null}` with no animation.

- **F3 — Header copy crossfade: no transition on text swap** (`GemmaTrace.tsx` lines 149–158): Spec mandates a "200ms opacity crossfade" (`transition-normal`) when header copy swaps from streaming to complete. Implementation renders a plain `<span>{header}</span>` — the string change is a direct re-render with no fade. Expected: `<AnimatePresence mode="wait">` with `<motion.span key={header} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2, ease: 'easeOut' }}>`. Found: no crossfade.

- **F4 — Engineering panel opacity: custom duration instead of Brightpath spring** (`GemmaTrace.tsx` line 322): `opacity: { duration: 0.18, ease: "easeOut" }` is a hardcoded 180ms tween. Spec mandates "opacity fades `0 → 1` over the same duration" as the `springs.smooth` height spring — no custom durations per §3 Motion Presets Critical Rules. Expected: `opacity: springs.smooth`. Found: `opacity: { duration: 0.18, ease: "easeOut" }`.

- **F5 — Live region element: missing `role="status"`** (`GemmaTrace.tsx` lines 150–153): Spec accessibility table specifies `gemma-trace-live | status | aria-live=polite`. Implementation places `aria-live="polite"` on the `<header>` element, which has an implicit `role="banner"` in landmark contexts. Missing explicit `role="status"`. Expected: a child element with `data-testid="gemma-trace-live" role="status" aria-live="polite"`, separate from the header landmark. Found: `aria-live="polite"` directly on `<header>` with no `role="status"`.

**WARNINGS**

- **W1 — Row entrance animation: inline values instead of named preset** (`GemmaTrace.tsx` lines 221–225): `initial: { opacity: 0, y: 24 }, animate: { opacity: 1, y: 0 }, transition: springs.smooth` is semantically identical to `transitions.fadeInUp` from `motion.ts` but does not reference it by name. Using `...transitions.fadeInUp` would make future changes to that preset propagate automatically. Non-blocking.

- **W2 — `min-h-[40px]` arbitrary value when spacing token exists** (`GemmaTrace.tsx` line 259): Tailwind spacing token `10` = 40px, so `min-h-10` is the token-backed equivalent of `min-h-[40px]`. Value is correct; the arbitrary form bypasses the token. Non-blocking.

- **W3 — `tracking-[1px]` arbitrary value: no tracking token in design system** (`GemmaTrace.tsx` lines 407, 417, 426): DESIGN.md and tailwind.config.ts do not define a `1px` letter-spacing token. The arbitrary class is the only way to achieve the spec-mandated `letter-spacing: 1px`. This is a pre-existing gap in the design system — the same value appears throughout DESIGN.md (Card Label, etc.) without a named token. Recommend adding a `tracking` token to DESIGN.md and tailwind.config.ts in a follow-up design system edit. Non-blocking.

- **W4 — `py-[2px]` arbitrary value: no 2px spacing step in system** (`GemmaTrace.tsx` line 352): The Brightpath spacing scale starts at `space-1` (4px). The spec-mandated `2px` vertical padding on the status pill cannot be expressed with an existing spacing token. Arbitrary value is correct and necessary. Non-blocking.

- **W5 — Brightpath JSON Theme not yet added to DESIGN.md**: The §3 proposed "JSON / Data Preview Theme" subsection (key=`text-secondary`, string=`accent-thrive`, number=`accent-caution`, boolean/null=`accent-insight`, brackets/punctuation=`text-muted`, error=`accent-alert`) is not yet in DESIGN.md. The implementation renders plain monospace text without per-token JSON highlighting (the `safeFormatJson` helper outputs uncolored `<pre><code>` text). This is acceptable for v1 per the spec's own note. Non-blocking. Recommend adding the subsection to DESIGN.md and implementing `<JsonHighlight>` before this spec ships.

---

##### `frontend/src/components/menu/GemmaChat.tsx` (integration scope only)

**PASS**
- `renderMessageWithTrace` (lines 283–294): `<GemmaTrace events={events!} mode="complete" />` above `<ChatMessage>` — correct prop interface, placement above the assistant message per spec.
- `renderSendingRow` live-trace mount (lines 315–317): `<GemmaTrace events={liveEvents!} mode="live" />` above the typing indicator — correct prop interface and placement.
- New integration code introduces no hex colors, no inline rgba values, no arbitrary spacing values outside the pre-existing send button (which is out of scope).

**WARNINGS**
- **W6 — Pre-existing `hover:bg-[#6bc494]` on send button** (`GemmaChat.tsx` lines 432, 579): Out of scope for this audit (pre-existing, not introduced by this spec). Flagged for completeness — this hex is the DESIGN.md-documented Primary Button hover darken. Should be tokenized in a future design-system cleanup.

---

#### Notes

1. **Proposed tokens not yet in DESIGN.md**: `--color-bg-recessed` and `gemma-trace-pulse` are correctly added to their target files (`tokens.css`, `index.css`, `tailwind.config.ts`). DESIGN.md itself has not been updated to absorb them into the Backgrounds table or CSS Keyframes table. A follow-up edit should add both, plus the JSON / Data Preview Theme subsection, before marking the spec COMPLETE.

2. **F1–F5 are all frontend-only, no backend changes required.** F1 is a class-name swap on one element. F2–F3 require adding `AnimatePresence` wrappers. F4 is a one-line fix on the opacity transition config. F5 is adding `role="status"` to one element.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED

### Code Review (@faang-staff-engineer)
**Status:** REVIEWED
**Reviewed:** 2026-05-01

Look, I love Claude, BUT... I came in expecting to find a leaked task or a deadlock-on-disconnect. I did not. The four high-risk areas the spec called out (request-scoped queue lifecycle, SSE backpressure / cancellation, existing-caller no-op, fallback parity) are all implemented correctly. The `try/finally` cancellation in `chat_ask_stream` actually does what the comment says it does, the `_invoke_callback` short-circuit is in the right place, and the `**kwargs`-absorbing patch sites for the existing tests mean the new optional callbacks didn't break anything I could find. The new Pydantic SOC-pattern validator on `AskScope.target_id` is the kind of belt-and-braces input validation I'd actually push for in review, and it was already there from a prior audit. I went looking for problems and came back with two minor notes and some "if this ever changes, watch out" thinking-out-loud. Verdict is APPROVED — proceed to Verification.

#### Findings

##### 1. Request-scoped queue lifecycle (no leaks if client disconnects mid-stream)

**PASS — Critical path is correct.** `backend/app/services/ask_gemma.py:484–520`.

- The `try/finally` around the drain loop fires on `GeneratorExit` from `aclose()`. The finally block calls `loop_task.cancel()` then `await asyncio.gather(loop_task, return_exceptions=True)`. This is the canonical pattern — `gather` with `return_exceptions=True` swallows the resulting `CancelledError` from the cancelled task without re-raising it, which is exactly what you want here. A bare `await loop_task` would re-raise `CancelledError` and cascade out of the generator's finally; this implementation correctly avoids that trap.
- Semaphore release: `generate_with_tools_loop` holds the semaphore via `async with sem:` at `backend/app/services/gemma_client.py:1006`. When `loop_task.cancel()` propagates `CancelledError` into the awaited inner coroutine, the `async with` block's `__aexit__` releases the semaphore as the exception unwinds. Verified by `test_stream_cancelled_when_client_disconnects` at `backend/tests/services/test_ask_gemma_stream.py:378–438`, which asserts `loop_finished.wait()` resolves within 500ms (the `_slow_loop` would otherwise sleep 30s).
- Reference cycles: the closures `on_start` / `on_turn` (`ask_gemma.py:446–463`) capture `queue` (a local), not `loop_task` (which doesn't exist when the closures are defined). `loop_task` captures the closures via the `on_turn_start` / `on_turn_event` kwargs on the inner `_tools_loop_inner`. The closures don't capture `loop_task`. No cycle. Once the generator is `aclose()`d and `loop_task.cancel()` runs, all references release as the stack unwinds. No leak across requests.
- One nitpick on the wall-clock claim in §3 / Decision #14 ("released within ~100ms"): the actual disconnect-to-release latency is bounded by `_TRACE_DRAIN_POLL_S = 0.05` (the wait_for window — the generator finishes its current `wait_for` cycle before `aclose()` resumes the finally) plus Gemma's own task-cancellation cycle (typically immediate). 100ms is a reasonable ceiling; the test only asserts <500ms which is generous. Not an issue, just noting the claim is observational not enforced.

##### 2. SSE backpressure / cancellation handling

**PASS with minor note on the 50ms latency floor — Significant only if the spec's "live" feel becomes a complaint, otherwise Minor.** `backend/app/services/ask_gemma.py:442–495`.

- `asyncio.Queue(maxsize=256)` with documented worst-case ~30 events: the bound is genuinely unreachable under `max_turns=3` and the loop's existing `tool_dispatched = True` short-circuit at `gemma_client.py:1173` (which drops tools after first dispatch in subsequent turns). Even pathological behavior is bounded by Gemma's tool-call token budget at `max_tokens=1200` per turn; you'd run out of tokens before you'd run out of queue slots. 256 is plenty.
- `await queue.put(...)` blocks on full. Could the consumer stop reading mid-stream and back-pressure the producer? In principle, yes — if the SSE consumer's TCP buffer fills, the StreamingResponse `yield` stalls, the drain loop stops calling `queue.get()`, and `loop_task`'s callback `await queue.put()` would block once 256 events are queued. In practice this can't happen because: (a) FastAPI / Starlette will detect the broken pipe and call `aclose()` on the generator long before the queue fills, which triggers the finally-block cancellation and unblocks the `put`; (b) max event count is ~30 << 256. The tail risk would be a working TCP connection to a consumer that's intentionally not reading — that's a malicious client, and the wall-time cap (`max_wall_time_s=30.0`) bounds it anyway. Acceptable.
- The 50ms drain poll (`asyncio.wait_for(queue.get(), timeout=0.05)` at `ask_gemma.py:490–495`) does create a worst-case 50ms latency floor on the LAST event after a quiet period — i.e. when the loop sleeps then enqueues the final event right after a `TimeoutError` cycle, the consumer waits up to 50ms for the next poll. For chat with sub-second tool calls this is invisible; for a tool that returns instantly between long Gemma calls it adds up to 50ms latency to that one frame. The cleaner pattern (mentioned as M2 in @fp-architect's rev 1.0 review) is a `loop_task.add_done_callback(lambda _: queue.put_nowait(_SENTINEL))` to wake the drain immediately. Not blocking — works as written, matches the build SSE stream's drain pattern at `routers/builds.py`, and 50ms is below human perception. Worth a follow-up if SSE feels laggy in demos, otherwise leave it.

##### 3. Existing-caller no-op verification

**PASS — exhaustively verified.** Three call sites of `generate_with_tools_loop` confirmed kwarg-only with no callback args:

- `backend/app/services/set_your_course.py:834–844` — kwargs only, no `on_turn_start` / `on_turn_event`. Defaults to `None`. No behavior change.
- `backend/app/services/ask_gemma.py:313–323` (legacy `chat_ask` non-streaming) — kwargs only, no callback args. No behavior change.
- (The streaming `chat_ask_stream` at `ask_gemma.py:466–481` is the new caller and correctly passes both callbacks.)

The `_invoke_callback` shim at `gemma_client.py:956–968` correctly short-circuits on `callback is None` BEFORE entering the try/except block. Verified by the two no-op tests at `tests/services/test_gemma_client.py:1024` and `:1048` — both call the loop with no callbacks and assert clean execution. The `if callback is None: return` is a single comparison and an early return; no measurable cost when the callback isn't passed.

`ToolCallTurn` field-ordering: both new fields (`tool_result_preview`, `dispatch_index`) are added in trailing positions with defaults (`gemma_client.py:932–941`). Audited every existing `ToolCallTurn(...)` construction:
- `gemma_client.py:1147` (production path, the loop itself) — uses kwargs, all fields supplied including new ones. OK.
- `tests/services/test_set_your_course_chip_tool_loop.py:103` — kwargs. OK.
- `tests/services/test_set_your_course.py:321` — kwargs. OK.
- `tests/routers/test_ask_gemma_router.py:718, 802, 914` — all kwargs. OK.
- `tests/services/test_ask_gemma_stream.py:114, 208, 337, 463` — kwargs. OK.

No positional construction anywhere. Field-count assertions: I grepped for `len(turn.__annotations__)` and similar shape-asserts; none exist. Adding the two defaulted fields is genuinely additive.

The six `fake_loop` patch signatures in `test_ask_gemma_router.py` (`:151, :403, :435, :474, :715, :799, :882, :910, :975`) all use `(**kwargs: Any)` — they absorb the new `on_turn_start` / `on_turn_event` kwargs without TypeError. This is the precondition the spec called out in C7 and it's met.

##### 4. Fallback path correctness when SSE connection fails

**PASS — both fallback branches are correct.** `frontend/src/api/menu.ts:338–430`.

- **HTTP-error fallback** (status != 200, !res.body): the explicit `throw new Error(...)` at `menu.ts:372` jumps to the catch block at `:408`, which calls `askGemma(...)` and synthesizes events from `tool_calls`. Final event sequence is `synthetic[] + final_text + done` — identical shape to the live path. Verified by `test_askGemmaStream_falls_back_on_http_error` at `menu.stream.test.ts:129–175`.
- **Thrown-error fallback** (network failure): `fetch` throws → catch block fires → same fallback path. Verified by `test_askGemmaStream_falls_back_on_thrown_error` at `menu.stream.test.ts:177–202`.
- **Synthetic event shape parity** (Decision #7, silent visual parity): `synthesizeEventsFromToolCalls` at `menu.ts:296–318` produces exactly one `turn_start` + one `turn_complete` per `TraceEventPayload`, in array order, using the same `turn` (= dispatch_index) field. The `<GemmaTrace>` row-correlation at `frontend/src/components/menu/GemmaTrace.tsx` correlates by that same field. Both feeds render identically. Confirmed via `test_chat_falls_back_to_post_hoc_trace_on_stream_failure` at `GemmaChat.test.tsx:687`.
- **`reader.releaseLock()` in finally** at `menu.ts:399–405`: wrapped in its own try/catch that swallows. If the reader was already released by a prior abort (e.g. the runtime closed the underlying stream), the redundant `releaseLock()` would normally throw `TypeError: Releasing a locked ReadableStreamDefaultReader`. The catch handles it. Disconnect mid-frame is also handled — the `for` loop over `frames` (after `buffer.split("\n\n")`) never sees the partial frame because `frames.pop()` puts the trailing partial back into `buffer`, and the next `reader.read()` either resumes or returns `done: true`.

##### 5. Security / input validation baseline

**PASS — no new attack surface.**

- The endpoint is unauthenticated (no auth on the existing `/chat/ask` either; per `feedback_profile_is_build.md` "no logged-in concept"). This is consistent with the existing pattern, not a new gap.
- Input validation: `AskScope` at `backend/app/models/api.py:109–173` has tight Pydantic validators — bounded `build_ids` length (1–4), enum-checked `target_id` for stat/boss, length-capped (64) for skill, **regex-validated SOC pattern with `fullmatch` for branch** (the `fullmatch` choice is correct — `re.match(...$)` would allow trailing newlines through and `target_id` flows into a parameterized DuckDB lookup). The 422 fires before the handler runs. Good defense.
- `AskRequest.message` is bounded at 2000 chars. `history` is unbounded `list[dict[str, Any]]` — that's a pre-existing gap in `/chat/ask`, not introduced by this spec, so it's out of scope. Worth flagging in a future spec but not this review.
- No SQL injection vectors introduced. Tool args go through `mcp_client.call_async` which uses parameterized DuckDB queries upstream.
- No secrets / PII logged in the new code paths. `_log_tool_turn` continues unchanged; no new fields added to the JSONL log records that would surface secrets.

##### 6. Concurrency / per-request state

**PASS — request-scoped state is genuinely request-scoped.**

- `queue = asyncio.Queue(maxsize=256)` at `ask_gemma.py:442–444` is a local variable in the `chat_ask_stream` coroutine. Each request gets its own queue. No cross-request leakage.
- The two callback closures (`on_start`, `on_turn`) close over the request's queue. They live and die with the generator. No globals.
- The Gemma module-level semaphore (`gemma_client._semaphore` at `:131`) is correctly shared (intentionally — concurrency throttling is its job). The streaming endpoint participates in the same budget as every other Gemma call site.
- `loop_task` is a per-request `asyncio.Task`. Cancelled in finally on disconnect. No orphan.

##### 7. Error handling / unhandled exceptions

**PASS with one Minor finding.**

- `chat_ask_stream` boundary defense at `ask_gemma.py:500–504` correctly wraps `await loop_task` in `try/except Exception` and falls through to the `chat_unavailable` fallback. Verified by `test_stream_loop_exception_falls_back_to_chat_unavailable`.
- The router's `_stream` async-generator at `ask_gemma_router.py:84–100` catches `SkillNotFoundError` and yields a final `error` + `done` frame. This is the right pattern for mid-stream errors when headers are already sent.
- **🟡 Minor — `_stream` doesn't catch other exceptions.** The `ask_gemma_router.py:84` generator catches `SkillNotFoundError` only. Any other exception that escapes `chat_ask_stream` (which is supposed to never raise per C3) would propagate up. The `chat_ask_stream` generator's boundary defense is solid (try/except around `await loop_task` + try/finally for cancellation), so the only realistic escape paths are: (a) Pydantic `model_dump(mode="json")` raising on a non-serializable field — extremely unlikely given the typed event union; (b) the closures themselves raising before reaching the loop. Neither is a realistic concern. But "extremely unlikely" is the kind of thing that becomes a 3am page. Adding a bare `except Exception` around the `async for` loop in `_stream` that yields one `error` frame + closes would be cheap insurance. Not blocking — the inner contract is sound — but worth a follow-up.

##### 8. Architecture consistency

**PASS — fits the existing SSE pattern in `routers/builds.py`.**

- Wire format: identical `event:\ndata:\n\n` framing via the new shared `_sse.sse_event` helper. Both `routers/builds.py` and `routers/set_your_course.py` were correctly migrated to import from `_sse.py` (the C6 fix). One source of truth restored.
- Headers: `Cache-Control: no-cache` + `X-Accel-Buffering: no` matches the build stream. Right call for proxies.
- The `StreamingResponse(_stream(), media_type="text/event-stream", ...)` boilerplate at `ask_gemma_router.py:102–109` mirrors `routers/builds.py` exactly.
- Discriminated union event pattern with `Literal["..."]` discriminators is correct Pydantic v2.

##### 9. Test quality

**PASS — tests catch the regressions they claim to catch.**

Spot-checked the highest-stakes tests:
- `test_stream_cancelled_when_client_disconnects` at `test_ask_gemma_stream.py:378` actually exercises `aclose()` on a generator with an in-flight `loop_task` and asserts the loop's `try/finally` fires within 500ms. If C4's cancellation was missing or wrong (e.g. `await loop_task` instead of `asyncio.gather`), this test would hang or raise `CancelledError`. Real coverage.
- `test_stream_loop_exception_falls_back_to_chat_unavailable` at `:286` raises a synchronous exception from the patched `_fake_loop` and asserts the boundary defense fires. If C3's try/except was missing, this would propagate. Real coverage.
- `test_dispatch_index_unique_across_parallel_calls` at `test_gemma_client.py:1138` uses a `_MultiToolCallResponse` stub that returns 3 tool calls in one outer LLM turn, and asserts `[t.dispatch_index for t in log] == [0, 1, 2]`. If the dispatch_index logic regressed (e.g. accidentally used `turn` as the key), this would fail. Real coverage of the C1 fix.
- `test_unknown_event_type_returns_null_not_throw` at `menu.stream.test.ts:73` tries to parse a `thinking` frame and asserts `null` was returned, not thrown. Decision #15's forward-compat seam is locked.
- `test_stream_back_pressure_under_bounded_queue` at `test_ask_gemma_stream.py:446` pushes 32 events through the queue. Doesn't exercise the actual blocking case (256 events), but the production-realistic load is what matters; the bound itself is unreachable by design.

Not coverage theater. The tests target real failure modes and would actually fail if the corresponding code paths regressed.

#### What's Actually Good

- The `dispatch_index` design (Decision #13). Using `len(tool_call_log)` captured before append as the per-dispatch monotonic key is genuinely clever — it's stable across the start↔complete async gap, it's unique under parallel calls, and it requires zero new state. The kind of thing 15 years of experience teaches you to look for.
- The `try/finally` + `asyncio.gather(..., return_exceptions=True)` pattern is the canonical idiom and it's used correctly. Most implementations get this slightly wrong (bare `await loop_task` re-raises CancelledError, or `loop_task.cancel()` without awaiting leaks the task).
- The `_invoke_callback` shim's `if callback is None: return` placement BEFORE the try/except is the right call — zero overhead in the hot path when the callback isn't set.
- Decision #15's forward-compat parser is the kind of contract that pays off three releases later. Locking it via a dedicated test is the move.
- The router-level `_sse_event` consolidation cleanup (C6) — eliminating the second byte-identical copy in `set_your_course.py` — is the kind of "while we're here" refactor that prevents future drift.
- The Pydantic SOC-pattern validator's `fullmatch` instead of `match` (already in place from a prior audit, but worth saying) closes the trailing-newline bypass that `re.match(..., r"...$")` allows. Correct.

#### Required Changes

None. The Minor finding about `_stream`'s exception handler is a follow-up improvement, not a blocking change.

#### Recommendations (non-blocking, follow-up backlog)

1. Consider replacing the 50ms drain poll with a `loop_task.add_done_callback` sentinel-pusher pattern. Eliminates the worst-case 50ms latency floor on the last event in a quiet queue and stops the 20Hz idle spin. Cosmetic for chat-scale; principled improvement.
2. Add a bare `except Exception` around the `async for ev in ask_gemma.chat_ask_stream(...)` loop in `routers/ask_gemma_router.py:_stream` that yields one `error` frame + `done`. Cheap belt-and-braces against any future regression in `chat_ask_stream`'s boundary defense.
3. (Pre-existing, out of scope but flag for backlog) `AskRequest.history: list[dict[str, Any]]` is unbounded. A malicious client could submit a 10MB history blob. Not introduced by this spec but worth a defensive size cap in a future hardening pass.

#### Questions for the Author

(Real questions, not gotchas — these are things a future reviewer or on-call engineer should know the answer to.)

- Have you load-tested the `/chat/ask/stream` endpoint with concurrent students? The semaphore caps Gemma calls at 8 (`GEMMA_MAX_CONCURRENCY`), but the FastAPI worker count + the per-request queue + the 30s wall-time cap together set the actual concurrency ceiling. Demo with 5 simultaneous judges should be fine; a class of 30 hammering the demo may not.
- What's the alerting story when `chat_ask_stream` falls through to `chat_unavailable` repeatedly? The fallback is silent on the wire (good, per Decision #7) — but is there a server-side metric / log alert when the rate exceeds X%? Not in this spec, but the JSONL log records every call; that's the surface.
- The `parseSSEFrame` returning `null` for unknown types is correct, but if a future backend version routinely emits unknown types (say, 40% of frames), older frontends will silently render an incomplete trace. That's the right tradeoff but a deployment-coordination thing — worth a note in any future spec that adds new event types ("test against this version's frontend before rollout").

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

This is great AI-generated code. It just needs... well, actually, I went looking for what it needs and came back nearly empty-handed. The spec's rev 1.0 → rev 1.1 process caught the issues that would have mattered (the C1 dispatch_index correctness defect was the most important catch, and the C4 cancellation hole was the second). By the time the implementation landed, the architectural seams were correct. The implementer executed against the rev 1.1 spec faithfully — no deviations, no shortcuts in the cancellation path, no swallowed errors that should have surfaced. Proceed to Verification.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-05-01 00:18 (@fp-builder independent re-run)

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | PASS | 0 new errors from this spec's changes. Baseline (pre-spec stash): 69 errors in 18 files. Post-spec: 69 errors in 18 files. Net delta: 0. All 69 are pre-existing across untouched modules (stat_engine, sessions, wrapped_renderer, sessions router, schools router, profile router, skill_pool, intent, skills router, guidance, gauntlet, guidance_router, branches router, reports router). Out of scope per §6. |
| Tests (pytest) | PASS | 1337 passed, 0 failed |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (`npx tsc --noEmit` clean) |
| Tests (vitest) | PASS | 773 passed, 0 failed — 66 test files |
| Production build (Vite) | PASS | 729 modules transformed. dist/index.html 1.81 kB, dist/assets/index-CE3Xis5T.css 81.38 kB (gzip 15.21 kB), dist/assets/index-CcsTgld6.js 1,028.79 kB (gzip 304.78 kB). Built in 1.58s. |

### Build Accountability Log
| Attempt | Result |
|---------|--------|
| 1 | All checks passed — no fixes required |

---

## §10 Discussion

```
[2026-05-01] Claude Code → @fp-architect, @genai-architect
Spec revised to rev 1.1. All seven CHANGES REQUESTED conditions from
@fp-architect (C1–C7) and both required items from @genai-architect
(A, B) plus the two recommended items (C, D) addressed. Item E
(turn_number/turn_index naming) deferred to research-spec kickoff per
@genai-architect's recommendation.

Summary of changes (see updated §2 Decisions #12–#15, §3 Row
Correlation Key, and §4 Data Model + Service Changes):

- C1 + A: Symmetric one-place emission — both `on_turn_start` and
  `on_turn_event` callbacks now fire from inside `_tools_loop_inner`.
  Single per-dispatch index `dispatch_index` (added field on
  `ToolCallTurn`, default 0) is the unique key for SSE row
  correlation. Router-side `_wrap_dispatch` removed; `chat_ask_stream`
  passes `mcp_client.call_async` directly. Future callers of the loop
  get both events for free.
- C2: §4 row 274 contradiction resolved. Callbacks fire ONLY on
  appended `ToolCallTurn`s. Final-text and transport-error branches
  do not fire callbacks (those are surfaced via the loop's return
  tuple).
- C3: `chat_ask_stream`'s `await loop_task` is wrapped in
  try/except Exception; on any exception, yields
  `TraceFinalText(chat_unavailable) + TraceDone`. Generator never
  raises past its boundary.
- C4: Drain loop wrapped in try/finally; on client disconnect,
  loop_task is cancelled and awaited via
  `asyncio.gather(..., return_exceptions=True)`. Test
  `test_stream_cancelled_when_client_disconnects` promoted from P1
  to P0.
- C5: Bounded queue `maxsize=256` (Decision #14). 8x headroom over
  worst-case event count (~30 = max_turns × max_tools × event_pairs).
  Lossless trace; bound documented; bound not reachable.
- C6: `routers/set_your_course.py:38-41` added to File Changes —
  second byte-identical copy of `_sse_event` extracted to
  `app.services._sse.sse_event` along with the `builds.py` copy.
- C7: Three test files added to Existing Tests at Risk +
  Authorized Test Modifications:
  `test_set_your_course_chip_tool_loop.py`, `test_ask_gemma_voice.py`,
  `test_ask_gemma_router.py` (which had been listed as "Low / no
  modification" but contains a `ToolCallTurn` literal at line 718 and
  six `generate_with_tools_loop` patch sites).
- Item B: New Decision #15 — `parseSSEFrame` MUST return null (never
  throw) on unknown event types. New P0 vitest:
  `test_unknown_event_type_returns_null_not_throw`.
- Item C: Subsumed by `dispatch_index`. No separate `call_index` field
  needed — `dispatch_index` provides both ordering AND uniqueness.
- Item D: Both callbacks now accept sync OR async callables via
  `asyncio.iscoroutine`-style branching in the loop's invocation
  shim. New P0 test: `test_callback_accepts_sync_callable`.
- Item E: Deferred. Will reconcile `turn_number` (loop) vs
  `turn_index` (research spec) when research spec is unparked.

Status returned to ARCH REVIEW. Re-review requested before Step 2
(Design Vision). All §5 verdicts above are marked superseded.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
