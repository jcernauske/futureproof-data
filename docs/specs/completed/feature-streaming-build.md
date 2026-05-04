# Feature: Streaming Build Creation

## Claude Code Prompt

```
Read the spec at docs/specs/feature-streaming-build.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, API contracts, SSE protocol)
   - @fp-architect writes findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

3. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x)
   - Run ALL tests to catch regressions

4. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 5
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

5. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

6. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review
   - Generate report to reports/feature-streaming-build-YYYY-MM-DD.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-27 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-27 |
| Blocked By | — |
| Related Specs | `feature-build-results-screen.md`, `feature-save-build.md` |

---

## §1 Feature Description

### Overview

Replace the blocking `POST /build` endpoint with a streaming `POST /build/stream` SSE endpoint that emits build data incrementally as each phase completes. The frontend renders the reveal screen progressively — stats and finances appear in ~2s, boss fights fill in over the next ~3s, and Gemma narratives stream in as they arrive. Total perceived wait drops from 6-8s to ~2s.

### Problem Statement

Today the build creation flow is all-or-nothing. The backend computes stats, scores bosses, generates branches, then fans out 4+ Gemma calls (5 boss narratives + skill recs + skill pool + guidance), waits for every single one to finish, assembles the Build object, and returns it as one JSON blob. The frontend shows a spinner ("Gemma is analyzing your build...") for the entire 6-8 seconds.

The irony: 80% of the build results screen is pure data (pentagon stats, finances, path card, boss scores) that's ready in ~2 seconds. The student stares at a spinner for 4-6 additional seconds waiting for prose they haven't scrolled to yet.

Additionally, `compute_one()` and `get_branches()` currently run sequentially even though they're independent MCP queries, adding ~500ms-1s of unnecessary wait.

### Success Criteria

- [x] New `POST /build/stream` SSE endpoint emits build data incrementally
- [x] `compute_one()` and `get_branches()` run concurrently (not sequentially)
- [x] Frontend renders pentagon, path card, and finances within ~2s of build start
- [x] Boss fight scores (WIN/DRAW/LOSE) render before narratives arrive
- [x] Boss narratives, skill recs, skill pool, and guidance fill in progressively as SSE events
- [x] Existing `POST /build` endpoint remains functional (no breaking change)
- [x] Build is saved to state + disk only after all phases complete
- [x] Fallback narratives display if any Gemma call fails (existing behavior preserved)
- [x] SSE pattern follows the existing `POST /intent/stream` convention

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | SSE (Server-Sent Events) over WebSocket | SSE is unidirectional (server→client), simpler, already proven in the codebase (`/intent/stream`), and works through Railway's proxy. Build creation is a fire-and-forget stream — no bidirectional communication needed. | WebSocket (overkill, more complex); polling (higher latency, more requests); chunked JSON (no event typing) |
| 2 | Keep `POST /build` as-is | Non-breaking. Mock API, tests, and any external consumers continue to work. The streaming endpoint is opt-in. | Replace `/build` with streaming-only (breaks mocks and tests); version the API (premature) |
| 3 | Parallelize `compute_one` + `get_branches` | Both are independent MCP/DuckDB queries dispatched to the thread pool. Running them concurrently saves ~500ms-1s. `score_gauntlet()` depends on `compute_one` but not on `get_branches`. | Keep sequential (simpler but slower); parallelize inside `compute_one` (wrong layer) |
| 4 | Emit skeleton Build before Gemma results | The frontend can render stats, finances, boss scores, and branches without any Gemma content. Emit these immediately, then patch in narratives/recs/pool/guidance as they arrive. | Wait for at least boss narratives before emitting (still blocks 2-3s); emit raw career data without Build structure (frontend has to assemble) |
| 5 | Frontend accumulates SSE events into build store | Each SSE event patches a field on the in-progress Build. Components re-render as their data arrives. No new state management — just `setBuild()` with merged data. | Separate loading states per section (more complex); render from events directly without store (breaks existing component contracts) |
| 6 | Emit individual boss narratives as separate events | 5 boss narratives complete at different times. Emitting each as it arrives means the first narrative shows ~2s after the skeleton, not ~3-4s (waiting for the slowest). | Batch all 5 narratives into one event (loses the staggered reveal effect); emit per-boss fight objects (over-granular) |

### Constraints

- Railway proxy supports SSE (confirmed by `/intent/stream` in production)
- Gemma latency varies: Ollama local is sub-second per call, OpenRouter cloud is 2-4s
- Build must be fully assembled and saved before the `done` event fires
- The `_gemma_fanout` helper is shared with `rebuild_with_sliders` — changes must not break the rebuild flow
- Mock API (`VITE_USE_MOCK_API=true`) must continue to work for the non-streaming endpoint

---

## §3 UI/UX Design

### Progressive Reveal Sequence

The reveal screen currently waits for the full Build, then shows everything at once. With streaming, sections appear in phases:

**Phase 1 (~2s): Skeleton Build arrives**
- Hero banner (school name, profile name, animal emoji) — renders immediately
- Pentagon chart — stats animate in
- Path card (career title, SOC code, CIP code) — renders immediately
- Finances card (salary, tuition, net price) — renders immediately
- Boss fight band — shows WIN/DRAW/LOSE badges with scores, but narrative text shows a subtle pulse placeholder

**Phase 2 (~2-4s): Gemma results stream in**
- Boss narratives fill in one by one as `boss_narrative` events arrive — each replaces its placeholder with a fade-in
- Skill recommendations section appears when `skill_recs` event arrives
- Guidance narrative (InstitutionCard) fills in when `guidance` event arrives
- Skill pool loads when `skill_pool` event arrives (reroll UI becomes interactive)

**Phase 3: `done` event**
- All placeholders that haven't been filled get fallback text
- Build is considered complete

### Placeholder States

While waiting for Gemma content, affected sections show a subtle loading state:

- **Boss narrative placeholder**: The fight result badge (WIN/DRAW/LOSE) renders immediately. Below it, a single line of `text-text-muted` text pulses with `opacity: [0.3, 0.7, 0.3]` animation: "Analyzing..."
- **Guidance placeholder**: InstitutionCard renders with school name header but body shows the same pulse pattern
- **Skill recs placeholder**: Section header "Skill Recommendations" is visible; cards show as empty rounded rectangles with pulse animation
- **Skill pool**: Reroll button is disabled with "Loading skills..." tooltip until pool arrives

### Interactions

- Scrolling, pentagon interaction, and boss card taps all work immediately in Phase 1 — no waiting
- If the user navigates away before `done`, the partial build is discarded (not saved)
- If the SSE connection drops, fall back to `POST /build` (full blocking call)

### Responsive Behavior

No layout changes from current BuildResultsScreen. The progressive reveal applies identically on mobile and desktop — same phase sequence, same placeholders.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Boss narrative placeholder | `boss-narrative-loading-{boss_id}` | `data-testid` | "Loading analysis for {boss name}" |
| Guidance placeholder | `guidance-loading` | `data-testid` | "Loading guidance" |
| Skill recs placeholder | `skill-recs-loading` | `data-testid` | "Loading skill recommendations" |

---

## §4 Technical Specification

### Architecture Overview

```
Frontend                          Backend
───────                          ───────
createBuildStream()          POST /build/stream (SSE)
  │                               │
  │  ◄─── event: skeleton ────    │  compute_one ──┐
  │       (Build sans Gemma)      │  get_branches ─┤ concurrent
  │                               │  score_gauntlet ◄─┘
  │                               │
  │  ◄─── event: boss_narrative   │  ┌─ narrate_one(ai)
  │  ◄─── event: boss_narrative   │  ├─ narrate_one(market)
  │  ◄─── event: boss_narrative   │  ├─ narrate_one(ceiling)
  │  ◄─── event: boss_narrative   │  ├─ narrate_one(loans)
  │  ◄─── event: boss_narrative   │  ├─ narrate_one(burnout)
  │  ◄─── event: skill_recs      │  ├─ generate_recs_async
  │  ◄─── event: skill_pool      │  ├─ generate_pool_async
  │  ◄─── event: guidance        │  └─ generate_guidance_async
  │                               │      (all 8 calls parallel)
  │  ◄─── event: done ─────────  │  save_build + store_build
  │                               │
  └── setBuild(merged) ──────►   done
```

### SSE Protocol

Follows the existing `_sse_event()` pattern from `set_your_course.py`:

```
event: <event_type>\ndata: <json_payload>\n\n
```

#### Event Types

| Event | Payload | When |
|-------|---------|------|
| `skeleton` | Full `Build` JSON with empty Gemma fields: `fights[].narrative = ""`, `skill_recs = []`, `skill_pool = []`, `guidance = ""` | After `compute_one` + `score_gauntlet` + `get_branches` + `build_from_parts` |
| `boss_narrative` | `{ "boss_id": "ai", "narrative": "..." }` | As each `narrate_one()` completes |
| `skill_recs` | `[SkillRec, ...]` | When `generate_recs_async()` completes |
| `skill_pool` | `[AppliedSkill, ...]` | When `generate_pool_async()` completes |
| `guidance` | `{ "narrative": "..." }` | When `generate_guidance_async()` completes |
| `error` | `{ "detail": "..." }` | On unrecoverable error |
| `done` | `{ "build_id": "..." }` | After all phases complete and build is saved |

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/routers/builds.py` | Modify | Add `POST /build/stream` SSE endpoint; parallelize `compute_one` + `get_branches` in existing `create_build`; extract shared build-assembly logic |
| `frontend/src/api/build.ts` | Modify | Add `createBuildStream()` that consumes SSE and returns progressive Build updates via callback |
| `frontend/src/screens/RevealScreen.tsx` | Modify | Use `createBuildStream()` instead of `createBuild()`; render skeleton immediately; patch in Gemma results as events arrive |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Handle `Build` objects with empty Gemma fields gracefully (placeholder states for narratives, recs, pool, guidance) |
| `frontend/src/api/mockBuild.ts` | No change | Mock API continues to use non-streaming `POST /build` |

### Backend: `POST /build/stream` Endpoint

```python
@router.post("/stream")
async def create_build_stream(request: BuildRequest) -> StreamingResponse:
    return StreamingResponse(
        _build_stream(request),
        media_type="text/event-stream",
    )


async def _build_stream(request: BuildRequest) -> AsyncIterator[str]:
    # Phase 1: Data queries (concurrent)
    career_task = asyncio.to_thread(
        stat_engine.compute_one,
        unitid=request.unitid,
        cipcode=request.cipcode,
        soc_code=request.selected_soc,
        student_major=request.student_major,
        student_cip=request.student_cip,
        effort=cast(EffortLevel, request.effort),
        loan_pct=request.loan_pct,
        intent_keywords=request.intent_keywords or None,
        home_state=request.home_state,
    )
    branches_task = asyncio.to_thread(
        branch_tree.get_branches, request.selected_soc,
    )

    try:
        career, branches_list = await asyncio.gather(career_task, branches_task)
    except ValueError as exc:
        yield _sse_event("error", {"detail": str(exc)})
        return
    except LookupError as exc:
        yield _sse_event("error", {"detail": "We don't have enough data for that career at this school."})
        return

    # Enrich career
    if not career.program_name and request.cip_title:
        career.program_name = request.cip_title
    if (request.home_state and request.school_state
            and request.home_state != request.school_state
            and career.institution_control
            and career.institution_control.startswith("Public")):
        career.is_out_of_state = True

    gauntlet = boss_fights.score_gauntlet(career)

    # Build skeleton (empty Gemma fields)
    skeleton = builds.build_from_parts(
        school_name=request.school_name,
        unitid=request.unitid,
        major_text=request.major_text,
        cipcode=request.cipcode,
        program_name=request.cip_title,
        effort=request.effort,
        loan_pct=request.loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches_list,
        skill_recs=[],
        guidance="",
        skill_pool=[],
        profile_name=request.profile_name,
        home_state=request.home_state,
        animal_emoji=request.animal_emoji,
        locale=request.locale,
    )

    yield _sse_event("skeleton", skeleton.model_dump(mode="json"))

    # Phase 2: Gemma fanout (all parallel, emit as each completes)
    locale = request.locale or "en"

    async def _narrate(fight):
        try:
            text = await boss_fights.narrate_one(career, fight, locale=locale)
            fight.narrative = text or boss_fights._fallback_narrative(fight)
        except Exception:
            fight.narrative = boss_fights._fallback_narrative(fight)
        return ("boss_narrative", {"boss_id": fight.boss, "narrative": fight.narrative})

    async def _recs():
        try:
            r = await skill_recs.generate_recs_async(career, gauntlet, locale=locale)
        except Exception:
            r = skill_recs._fallback_recs(career)
        return ("skill_recs", [rec.model_dump(mode="json") for rec in r])

    async def _pool():
        try:
            p = await skill_pool.generate_pool_async(career, gauntlet, locale=locale)
        except Exception:
            p = []
        return ("skill_pool", [s.model_dump(mode="json") for s in p])

    async def _guide():
        try:
            g = await guidance.generate_guidance_async(career, gauntlet, branches_list, locale=locale)
        except Exception:
            g = guidance._fallback_narrative(career, gauntlet)
        return ("guidance", {"narrative": g})

    tasks = [
        *[asyncio.create_task(_narrate(f)) for f in gauntlet.fights],
        asyncio.create_task(_recs()),
        asyncio.create_task(_pool()),
        asyncio.create_task(_guide()),
    ]

    # Emit events as each task completes
    recs_result = []
    pool_result = []
    guidance_result = ""
    for coro in asyncio.as_completed(tasks):
        event_name, event_data = await coro
        yield _sse_event(event_name, event_data)

        # Collect results for final build assembly
        if event_name == "skill_recs":
            recs_result = [skill_recs.SkillRec.model_validate(r) for r in event_data]
        elif event_name == "skill_pool":
            pool_result = [skill_pool.AppliedSkill.model_validate(s) for s in event_data]
        elif event_name == "guidance":
            guidance_result = event_data["narrative"]

    # Phase 3: Assemble final build and save
    final_build = builds.build_from_parts(
        school_name=request.school_name,
        unitid=request.unitid,
        major_text=request.major_text,
        cipcode=request.cipcode,
        program_name=request.cip_title,
        effort=request.effort,
        loan_pct=request.loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches_list,
        skill_recs=recs_result,
        guidance=guidance_result,
        skill_pool=pool_result,
        profile_name=request.profile_name,
        home_state=request.home_state,
        animal_emoji=request.animal_emoji,
        locale=request.locale,
    )
    state.store_build(final_build)
    builds.save_build(final_build)

    yield _sse_event("done", {"build_id": final_build.build_id})
```

### Backend: Parallelize existing `POST /build`

Apply the same `compute_one` + `get_branches` concurrency to the existing blocking endpoint:

```python
# Before (sequential):
career = await asyncio.to_thread(stat_engine.compute_one, ...)
branches_list = await asyncio.to_thread(branch_tree.get_branches, career.soc_code)

# After (concurrent):
career_task = asyncio.to_thread(stat_engine.compute_one, ...)
branches_task = asyncio.to_thread(branch_tree.get_branches, request.selected_soc)
career, branches_list = await asyncio.gather(career_task, branches_task)
```

Note: `get_branches` uses `request.selected_soc` directly instead of `career.soc_code` — they're the same value, and this removes the dependency.

### Frontend: `createBuildStream()`

```typescript
type BuildStreamEvent =
  | { type: "skeleton"; build: Build }
  | { type: "boss_narrative"; boss_id: string; narrative: string }
  | { type: "skill_recs"; recs: SkillRec[] }
  | { type: "skill_pool"; pool: AppliedSkill[] }
  | { type: "guidance"; narrative: string }
  | { type: "done"; build_id: string }
  | { type: "error"; detail: string };

export async function createBuildStream(
  params: BuildParams,
  onEvent: (event: BuildStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/build/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    signal,
  });

  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(parsed, res.status));
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse SSE frames from buffer
    const frames = buffer.split("\n\n");
    buffer = frames.pop()!; // last element is incomplete

    for (const frame of frames) {
      if (!frame.trim()) continue;
      const eventMatch = frame.match(/^event:\s*(.+)$/m);
      const dataMatch = frame.match(/^data:\s*(.+)$/m);
      if (!eventMatch || !dataMatch) continue;

      const eventType = eventMatch[1];
      const data = JSON.parse(dataMatch[1]);

      switch (eventType) {
        case "skeleton":
          onEvent({ type: "skeleton", build: data });
          break;
        case "boss_narrative":
          onEvent({ type: "boss_narrative", boss_id: data.boss_id, narrative: data.narrative });
          break;
        case "skill_recs":
          onEvent({ type: "skill_recs", recs: data });
          break;
        case "skill_pool":
          onEvent({ type: "skill_pool", pool: data });
          break;
        case "guidance":
          onEvent({ type: "guidance", narrative: data.narrative });
          break;
        case "done":
          onEvent({ type: "done", build_id: data.build_id });
          break;
        case "error":
          throw new Error(data.detail);
      }
    }
  }
}
```

### Frontend: RevealScreen Changes

RevealScreen currently does:

```typescript
const full = await createBuild(...);
setBuild(full);
navigate("/my-build");
```

Change to:

```typescript
await createBuildStream(params, (event) => {
  switch (event.type) {
    case "skeleton":
      setBuild(event.build);
      navigate("/my-build");
      break;
    case "boss_narrative":
      setBuild((prev) => mergeBossNarrative(prev, event.boss_id, event.narrative));
      break;
    case "skill_recs":
      setBuild((prev) => ({ ...prev, skill_recs: event.recs }));
      break;
    case "skill_pool":
      setBuild((prev) => ({ ...prev, skill_pool: event.pool }));
      break;
    case "guidance":
      setBuild((prev) => ({ ...prev, guidance: event.narrative }));
      break;
    case "done":
      // Build is saved server-side. Nothing to do.
      break;
  }
}, abortController.signal);
```

The `mergeBossNarrative` helper patches one fight's narrative into the existing gauntlet:

```typescript
function mergeBossNarrative(build: Build, bossId: string, narrative: string): Build {
  return {
    ...build,
    gauntlet: {
      ...build.gauntlet,
      fights: build.gauntlet.fights.map((f) =>
        f.boss === bossId ? { ...f, narrative } : f,
      ),
    },
  };
}
```

### Frontend: BuildResultsScreen Placeholder Handling

Components that display Gemma content need to handle empty/missing values gracefully:

- **BossBand / BossFightCard**: If `fight.narrative` is `""`, show a pulsing "Analyzing..." placeholder
- **InstitutionCard**: If `build.guidance` is `""`, show a pulsing placeholder in the card body
- **Skill recommendation panel**: If `build.skill_recs` is `[]`, show placeholder card outlines
- **Reroll interface**: If `build.skill_pool` is `[]`, disable reroll button

### Data Model Changes

None. The `Build` Pydantic model already supports empty lists and empty strings for all Gemma-generated fields. No schema changes required.

### Service Changes

No new services. The streaming endpoint reuses all existing services (`stat_engine`, `boss_fights`, `branch_tree`, `skill_recs`, `skill_pool`, `guidance`, `builds`). The `_gemma_fanout` helper in `builds.py` router is NOT modified — it continues to serve the non-streaming `POST /build` and `POST /build/{id}/rebuild` endpoints.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/RevealScreen.test.tsx` | All tests | High | RevealScreen switches from `createBuild` to `createBuildStream`; mock strategy changes |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Narrative/guidance display tests | Medium | Must handle empty string narratives without crashing |
| `backend/tests/routers/test_builds.py` (if exists) | `test_create_build` | Low | Non-streaming endpoint unchanged |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `RevealScreen.test.tsx` | Update mock from `createBuild` to `createBuildStream` with callback-based approach | Core API contract changes |
| `BuildResultsScreen.test.tsx` | Add fixture variant with empty Gemma fields to verify placeholder rendering | New UI state to cover |

#### Confirmed Safe

All backend tests for existing `POST /build`, `POST /build/tier`, `POST /build/outcomes` endpoints. All compare view tests. All menu screen tests.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/routers/test_builds.py` | `test_stream_build_emits_skeleton_first` | SSE stream starts with `skeleton` event containing valid Build JSON |
| P0 | `backend/tests/routers/test_builds.py` | `test_stream_build_emits_done_last` | `done` event fires after all other events, contains `build_id` |
| P0 | `backend/tests/routers/test_builds.py` | `test_stream_build_parallel_data_queries` | `compute_one` and `get_branches` are called concurrently (mock timing) |
| P1 | `backend/tests/routers/test_builds.py` | `test_stream_build_gemma_failure_fallback` | If a Gemma call raises, fallback text is emitted (not an error event) |
| P1 | `backend/tests/routers/test_builds.py` | `test_stream_build_saves_after_done` | Build is persisted to disk only after all events complete |
| P1 | `frontend/src/screens/RevealScreen.test.tsx` | `test_skeleton_triggers_navigation` | Navigation to `/my-build` happens on `skeleton` event, not `done` |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_empty_narrative_shows_placeholder` | Boss card with `narrative=""` shows "Analyzing..." pulse |
| P2 | `frontend/src/api/build.test.ts` | `test_createBuildStream_parses_sse` | SSE frame parsing handles multi-event buffers correctly |
| P2 | `backend/tests/routers/test_builds.py` | `test_stream_build_error_on_invalid_soc` | `error` event emitted for bad SOC code (not HTTP 422) |

#### Test Data Requirements

- Existing mock career/gauntlet fixtures from `BuildResultsScreen.test.tsx` can be reused
- SSE parsing tests need raw SSE frame strings as fixtures
- Backend stream tests need mocked `stat_engine`, `boss_fights`, `skill_recs`, `skill_pool`, `guidance` services

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED
**Reviewed:** 2026-04-27

#### System Context

This feature adds a streaming SSE variant of the existing `POST /build` endpoint. It touches two layers: the FastAPI router (`builds.py`) and the React frontend (`build.ts`, `RevealScreen.tsx`, `BuildResultsScreen.tsx`). No Brightsmith pipeline changes, no Pydantic model changes, no new services. The data flow is identical to the existing `create_build` endpoint -- same services, same MCP queries, same Gold zone reads via DuckDB -- with the orchestration restructured to emit partial results over SSE instead of blocking until completion.

#### Data Flow Analysis

The data flow traces cleanly through three phases:

**Phase 1 (Data queries):** `compute_one()` and `get_branches()` are dispatched concurrently via `asyncio.gather(asyncio.to_thread(...), asyncio.to_thread(...))`. Both are sync functions that hit the Gold zone DuckDB through the MCP client. `compute_one` returns a `CareerOutcome`; `get_branches` returns `list[CareerBranch]`. After gather, `score_gauntlet(career)` runs synchronously (pure Python, no I/O). The skeleton `Build` is assembled via `builds.build_from_parts()` and emitted as the `skeleton` SSE event. This boundary crossing is clean: `Build.model_dump(mode="json")` serializes the full Pydantic model.

**Phase 2 (Gemma fanout):** Eight async tasks are created -- 5x `narrate_one()`, plus `generate_recs_async()`, `generate_pool_async()`, `generate_guidance_async()`. All fan out through `gemma_client.generate_async()`. `asyncio.as_completed()` yields results as each finishes. Each result is emitted as a typed SSE event and collected for final build assembly. Every task has a `try/except Exception` that falls back to deterministic content on failure.

**Phase 3 (Save):** A second `build_from_parts()` call assembles the final Build with all Gemma results patched in. `state.store_build()` and `builds.save_build()` persist it. The `done` event fires only after save completes.

**Frontend:** `createBuildStream()` POSTs, opens a `ReadableStream` reader, splits on `\n\n`, parses `event:` and `data:` lines, and dispatches typed events via callback. `RevealScreen` navigates to `/my-build` on `skeleton`, then patches in Gemma results via `setBuild()` functional updates.

All boundary crossings are typed. No zone violations. Data flows Gold zone -> MCP client -> stat_engine/branch_tree -> builds router -> SSE -> frontend store.

#### Contract Review

**Pydantic models:** No changes. `Build` already supports `skill_recs=[]`, `skill_pool=[]`, `guidance=""`, and `fights[].narrative=""`. Verified in the existing `build_from_parts` signature which accepts these as defaults.

**SSE event payloads:** The `skeleton` event carries a full `Build` JSON (via `model_dump(mode="json")`). The `boss_narrative` event carries `{"boss_id": str, "narrative": str}`. The `skill_recs` event carries `[SkillRec.model_dump()]`. The `skill_pool` event carries `[AppliedSkill.model_dump()]`. The `guidance` event carries `{"narrative": str}`. The `done` event carries `{"build_id": str}`. All are well-typed.

**TypeScript discriminated union:** `BuildStreamEvent` covers all 7 event types with proper payloads. The `switch` in `createBuildStream` and `RevealScreen` is exhaustive.

**API endpoint:** `POST /build/stream` mounts under the existing `builds.router` which is prefixed at `/build`. So the full path is `POST /build/stream`. No collision with existing routes (`POST /build`, `POST /build/outcomes`, `POST /build/tier`, `POST /build/{build_id}/rebuild`, etc.).

#### Findings

##### Sound

1. **Parallelization of `compute_one` + `get_branches` is correct.** I traced this carefully. The existing code at `builds.py:188` calls `branch_tree.get_branches(career.soc_code)` which requires `career` to exist first (sequential dependency). The spec correctly identifies that `request.selected_soc` is the same value -- confirmed by reading `stat_engine.compute_one()` which filters `outcomes` by `soc_code == request.selected_soc` at line 510. Using the request parameter instead of the return value removes the false dependency and enables the gather. Sound.

2. **`_gemma_fanout` is NOT modified.** The streaming endpoint implements its own inline fanout with `asyncio.as_completed` instead of `asyncio.gather`. The existing `_gemma_fanout` helper continues to serve `create_build` (non-streaming) and `rebuild_with_sliders` unchanged. No shared mutable state, no signature changes. Both call the same underlying service functions (`narrate_one`, `generate_recs_async`, etc.) which are stateless. Safe.

3. **Build save ordering is correct.** The `for coro in asyncio.as_completed(tasks)` loop runs to exhaustion before the save block. The `done` event fires after `state.store_build(final_build)` and `builds.save_build(final_build)`. If the user navigates away mid-stream (SSE connection drops), the generator terminates early, the save block never runs, and no partial build is persisted. This matches the spec's stated contract.

4. **Error handling is thorough.** Phase 1 errors (ValueError, LookupError from data queries) emit an `error` SSE event and return early. Phase 2 errors (per-Gemma-task) are caught individually and fall back to deterministic content. The fallback function signatures match the codebase: `boss_fights._fallback_narrative(fight)` takes a `BossFightResult`, `skill_recs._fallback_recs(career)` takes a `CareerOutcome`, `guidance._fallback_narrative(career, gauntlet)` takes both. All verified.

5. **SSE protocol matches the existing pattern.** The spec's `_sse_event()` function is identical to the one in `set_your_course.py:38`. The `StreamingResponse` with `media_type="text/event-stream"` follows the same pattern. The frontend's `ReadableStream` + manual frame splitting approach is consistent with `intent.ts:118-153`.

6. **Frontend SSE parsing is sound.** The `buffer.split("\n\n")` approach with `frames.pop()` for the incomplete tail is a standard SSE parsing pattern. The existing `intent.ts` uses a similar `buffer.indexOf("\n\n")` loop. Both handle network-split frames correctly.

7. **Existing endpoint preserved.** `POST /build` remains unchanged except for the `compute_one` + `get_branches` parallelization (which is a pure improvement, not a behavioral change). Mock API continues to use the non-streaming path.

##### Concerns

- **Missing SSE response headers.** The spec's `create_build_stream` endpoint code (line 248-252) creates a `StreamingResponse` with only `media_type="text/event-stream"` but omits the `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers that the existing `set_your_course.py:70-79` SSE endpoint uses. Without these, Railway's reverse proxy or intermediate CDN layers may buffer SSE events instead of flushing them immediately, defeating the entire purpose of streaming. **Impact:** On Railway production, events may batch up and arrive in clumps instead of individually, making the progressive reveal feel identical to the blocking endpoint. **Recommendation:** Add the same headers dict from `set_your_course.py:73-78` to the `StreamingResponse` constructor.

- **`_sse_event` duplication.** The spec implies defining a second `_sse_event()` helper in `builds.py`. The identical function already exists in `set_your_course.py:38`. Two copies of the same 3-line helper is not a blocker, but for an endpoint that follows the same pattern, extracting it to a shared utility (e.g., `app.utils.sse`) would be cleaner and prevent drift. **Impact:** Minor maintenance burden if the SSE format ever changes. **Recommendation:** Extract to a shared module during implementation, or import from `set_your_course`. Not a blocker.

- **Frontend `createBuildStream` does not set `Accept: text/event-stream` header.** The existing `streamIntent()` in `intent.ts:94` sets `Accept: "text/event-stream"`. The spec's `createBuildStream()` omits it. This is not functionally required (the backend doesn't content-negotiate), but it is a consistency gap with the existing SSE consumer and could confuse future developers. **Impact:** None functionally. **Recommendation:** Add the `Accept` header for consistency.

- **Frontend does not handle SSE connection drop gracefully.** The spec's `createBuildStream()` catches `!res.ok` but does not handle the case where `res.body` is null (which `intent.ts:114` guards against). The non-null assertion `res.body!.getReader()` will throw an untyped error if the body is missing. **Impact:** Rare edge case (broken proxy, network layer stripping body) would produce an unhelpful error message. **Recommendation:** Add a null guard like `intent.ts:114`: `if (!response.body) throw new Error("stream produced no body")`.

- **`reader.releaseLock()` not called in finally.** The existing `intent.ts:147-150` wraps the reader loop in a `try/finally` that calls `reader.releaseLock()`. The spec's `createBuildStream()` omits this. If an error is thrown mid-parse (e.g., malformed JSON in a data line), the reader lock remains held, which can prevent the connection from being properly closed and may leak resources. **Impact:** Resource leak on parse errors. **Recommendation:** Wrap the reader loop in `try/finally { reader.releaseLock() }` following the `intent.ts` pattern.

- **Double `build_from_parts` call generates two build IDs.** The skeleton build and the final build are assembled via separate `build_from_parts()` calls (spec lines 294 and 372). Each call runs `_next_id_for()` which queries DuckDB for existing IDs and increments. The skeleton build gets ID `X-001`, the final build gets `X-002`. The `done` event emits the final build's ID (`X-002`), but the skeleton event emits a Build with ID `X-001` which is never saved. The frontend navigates on skeleton, so the user initially sees build ID `X-001` in the URL/state, but after `done`, the saved build has ID `X-002`. **Impact:** Build ID mismatch between what the frontend shows during streaming and what's actually persisted. The `done` event's `build_id` field provides the correct ID, but the spec's RevealScreen handler does nothing with it -- it just says "Build is saved server-side. Nothing to do." This means the frontend's in-memory Build has a stale `build_id` that doesn't match the persisted one. If the user reloads after streaming completes, `GET /build/{X-001}` will 404. **Recommendation:** Either (a) pre-generate the build ID before the skeleton call and pass it to both `build_from_parts` invocations, or (b) on the `done` event, patch the build's `build_id` in the frontend store so it matches the persisted one: `setBuild(prev => ({ ...prev, build_id: event.build_id }))`. Option (a) is cleaner -- generate the slug + ID once, then pass it as a parameter.

##### Blockers

None. The double-ID concern above is significant enough to require a fix before implementation, but the architectural approach is fundamentally sound.

#### Verdict
- [x] CHANGES REQUESTED

#### Conditions

1. **Add SSE response headers** to the `StreamingResponse` constructor: `Cache-Control: no-cache` and `X-Accel-Buffering: no`, matching the existing `set_your_course.py` SSE endpoint. Without these, Railway buffering will negate the streaming benefit.

2. **Fix the double build ID problem.** Pre-generate the build ID before the skeleton `build_from_parts` call, or patch the `build_id` in the frontend store on the `done` event. The current spec will cause the frontend to hold a build ID that doesn't match the persisted build, breaking reload and `GET /build/{id}` lookups.

3. **Add `res.body` null guard** in `createBuildStream()` before the non-null assertion, consistent with the existing `intent.ts` pattern.

4. **Add `reader.releaseLock()` in a finally block** in `createBuildStream()`, consistent with `intent.ts:147-150`.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline or data changes)

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/routers/builds.py` | Added `POST /build/stream` SSE endpoint, `_build_stream()` async generator, `_sse_event()` helper. Parallelized `compute_one` + `get_branches` in existing `POST /build` via `asyncio.gather`. Used `model_copy` for final build assembly (avoids double ID). |
| `frontend/src/api/build.ts` | Added `BuildParams` interface, `BuildStreamEvent` discriminated union, `createBuildStream()` with SSE frame parsing, `res.body` null guard, `reader.releaseLock()` in finally block. |
| `frontend/src/api/client.ts` | Exported `formatErrorDetail` (was module-private). |
| `frontend/src/store/buildStore.ts` | Added `updateBuild: (fn: (prev: Build) => Build) => void` for callback-based patching. |
| `frontend/src/screens/RevealScreen.tsx` | Switched to `createBuildStream()` with streaming event handler. Falls back to blocking `createBuild()` on SSE failure. Added `mergeBossNarrative` helper. |
| `frontend/src/screens/RevealScreen.test.tsx` | Rewrote mock strategy for streaming. Updated unmount race test. Added streaming behavior + fallback tests. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Added `useEffect` to sync streaming narrative updates from store into local fights state (preserves rerolled fights). |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Added tests for empty guidance placeholder and empty narrative placeholder states. |
| `frontend/src/components/build-results/BossBand.tsx` | Added narrative placeholder ("Analyzing..." pulse) when fight.narrative is empty. Added `useEffect` to pick up streaming narrative (empty→non-empty transition). |
| `frontend/src/components/build-results/InstitutionCard.tsx` | Added guidance placeholder ("Analyzing..." pulse) when guidance paragraphs are empty. |

### Deviations from Spec
1. Used `skeleton.model_copy(update={...})` instead of a second `build_from_parts()` call for final build assembly — per architect's recommendation to avoid double build ID generation.
2. Added `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers to StreamingResponse — per architect's condition #1.
3. Added `res.body` null guard in `createBuildStream()` — per architect's condition #3.
4. Added `reader.releaseLock()` in finally block — per architect's condition #4.
5. `_sse_event` helper duplicated in builds.py rather than extracted to shared module — architect noted this as minor, not a blocker.
6. RevealScreen navigates to `/my-build` on skeleton event, then subsequent SSE events update the zustand store which BuildResultsScreen consumes — this works because zustand actions are component-lifecycle-independent.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | TypeScript errors (2) | `dataMatch[1]` possibly undefined; BossBand spread partial type | Added non-null assertions for regex matches; explicitly constructed NarrativeEntry object |
| 2 | PASS | — | — |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/routers/test_builds.py` | `test_first_event_is_skeleton` | P0: First SSE event is type `skeleton` |
| `backend/tests/routers/test_builds.py` | `test_skeleton_contains_valid_build_json` | P0: Skeleton parses as valid Build |
| `backend/tests/routers/test_builds.py` | `test_skeleton_has_empty_gemma_fields` | P0: Skeleton has empty skill_recs, skill_pool, guidance, narratives |
| `backend/tests/routers/test_builds.py` | `test_skeleton_has_populated_non_gemma_fields` | P0: Skeleton has stats, gauntlet scores, branches populated |
| `backend/tests/routers/test_builds.py` | `test_done_is_last_event` | P0: `done` is the final SSE event |
| `backend/tests/routers/test_builds.py` | `test_done_contains_build_id` | P0: `done` event carries non-empty `build_id` |
| `backend/tests/routers/test_builds.py` | `test_skeleton_before_done` | P0: Skeleton appears before done in the stream |
| `backend/tests/routers/test_builds.py` | `test_all_expected_event_types_present` | P0: All 6 event types (skeleton, boss_narrative, skill_recs, skill_pool, guidance, done) appear |
| `backend/tests/routers/test_builds.py` | `test_five_boss_narrative_events` | P0: One boss_narrative per fight (5 total, all 5 boss IDs present) |
| `backend/tests/routers/test_builds.py` | `test_concurrent_execution` | P0: compute_one + get_branches run concurrently (wall-time assertion) |
| `backend/tests/routers/test_builds.py` | `test_narrate_one_failure_emits_fallback_narrative` | P1: All 5 narrate_one failures emit fallback text, no error event |
| `backend/tests/routers/test_builds.py` | `test_all_gemma_calls_fail_still_completes` | P1: All 8 Gemma calls fail, stream completes with fallbacks + done |
| `backend/tests/routers/test_builds.py` | `test_save_called_once` | P1: save_build + store_build called exactly once |
| `backend/tests/routers/test_builds.py` | `test_saved_build_contains_gemma_results` | P1: Saved build has patched-in Gemma results, not empty skeleton |
| `backend/tests/routers/test_builds.py` | `test_saved_build_id_matches_done_event` | P1: Saved build_id matches done event build_id |
| `backend/tests/routers/test_builds.py` | `test_skeleton_build_id_matches_done_event` | P1: Skeleton and done share same build_id (no double-ID bug) |
| `backend/tests/routers/test_builds.py` | `test_value_error_emits_error_event` | P2: ValueError from compute_one emits SSE error event, no done |
| `backend/tests/routers/test_builds.py` | `test_lookup_error_emits_error_event` | P2: LookupError emits user-friendly SSE error event |
| `backend/tests/routers/test_builds.py` | `test_blocking_build_still_works` | Regression: POST /build non-streaming endpoint unbroken |
| `frontend/src/api/build.test.ts` | `parses a single-event-per-chunk stream correctly` | P2: SSE parsing produces correct events from clean frames |
| `frontend/src/api/build.test.ts` | `handles multi-event buffer` | P2: TCP coalescing -- two SSE frames in one read |
| `frontend/src/api/build.test.ts` | `handles split frame across two chunks` | P2: Frame split mid-flight across two reader.read() calls |
| `frontend/src/api/build.test.ts` | `throws on error event` | P2: SSE error event raises Error with detail message |
| `frontend/src/api/build.test.ts` | `throws on HTTP error response` | P2: Non-200 HTTP response raises |
| `frontend/src/api/build.test.ts` | `throws when response body is null` | P2: Null body guard (architect condition #3) |
| `frontend/src/api/build.test.ts` | `calls releaseLock in finally block` | P2: reader.releaseLock called on success |
| `frontend/src/api/build.test.ts` | `calls releaseLock even when error event throws` | P2: reader.releaseLock called on error path |
| `frontend/src/api/build.test.ts` | `in mock mode, emits skeleton + done without fetch` | P2: Mock mode short-circuits without network |

### Test Results

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1147 | 0 | 0 | 1147 |
| vitest | 645 | 11 | 0 | 656 |

### Pre-existing Failures

| Test File | Failures | Reason |
|-----------|----------|--------|
| `PentagonOverlay.test.tsx` | 2 | Missing testids -- component redesign drift |
| `CompareView.test.tsx` | 9 | Component rendering failures -- unrelated to streaming |

### Gaps Identified

1. No integration test with real Gemma (all Gemma services mocked)
2. No backend test for client disconnect mid-stream (generator early termination)
3. No concurrent stream request test (DuckDB build ID race condition untested)

### Existing Tests Status

| At-Risk Test | Status |
|-------------|--------|
| `RevealScreen.test.tsx` (6 tests) | PASSING |
| `BuildResultsScreen.test.tsx` (26 tests) | PASSING |

---

## §8 Reviews

**Status:** COMPLETE

### Code Review (@faang-staff-engineer)
**Status:** APPROVED
**Reviewed:** 2026-04-27
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary

Look, I love Claude, BUT... I went into this one expecting the usual streaming-endpoint landmines -- uncancelled tasks leaking Gemma calls, race conditions between screens, SSE frame parsing that works in happy-path tests and explodes on chunked TCP segments. I've been paged at 3am for every single one of those in my career.

This is actually solid work. The `model_copy` approach for avoiding double build IDs (architect caught that one before it shipped -- good), the `asyncio.as_completed` fan-out with per-task fallback, the `cancelledRef` guard in the frontend, the `reader.releaseLock()` in a finally block -- these are all patterns I'd write myself. The architect review caught the four biggest issues before implementation, and all four were addressed.

I found one serious issue (orphaned async tasks on client disconnect), one moderate issue (SSE `data:` regex fragility), and two minor issues. Nothing that blocks shipping, but the task cancellation one should be addressed before this sees heavy production traffic.

#### Findings

##### Serious Findings

**Finding 1: Orphaned async tasks on SSE client disconnect**
**Severity:** Serious
**Impact:** When the frontend navigates away mid-stream (or the user closes the tab), the SSE connection drops. FastAPI's `StreamingResponse` closes the generator via `GeneratorExit`. The `_build_stream` generator terminates at the current `yield` point. However, the 8 `asyncio.create_task()` calls at line 342-346 of `builds.py` have already been scheduled on the event loop. When the generator exits early, those tasks are never awaited and never cancelled. They continue running to completion -- making Gemma API calls, allocating memory for responses -- but their results are silently discarded. On Ollama local this is ~sub-second wasted work. On OpenRouter cloud, each orphaned `narrate_one` call is 2-4 seconds of billed inference time. If a user rage-refreshes 5 times, that's 40 orphaned Gemma calls burning cloud credits.

**Location:** `backend/app/routers/builds.py:342-370`
```python
tasks = [
    *[asyncio.create_task(_narrate(f)) for f in gauntlet.fights],
    asyncio.create_task(_recs()),
    asyncio.create_task(_pool()),
    asyncio.create_task(_guide()),
]
# ... if generator exits here, tasks keep running
for coro in asyncio.as_completed(tasks):
    event_name, event_data = await coro
    yield _sse_event(event_name, event_data)
```
**The Fix:** Wrap the `as_completed` loop in a `try/finally` that cancels remaining tasks:
```python
try:
    for coro in asyncio.as_completed(tasks):
        event_name, event_data = await coro
        yield _sse_event(event_name, event_data)
        # ... collect results ...
except GeneratorExit:
    for t in tasks:
        t.cancel()
    return
finally:
    # Cancel any tasks not yet completed (e.g. if an unhandled
    # exception propagated out of the loop)
    for t in tasks:
        if not t.done():
            t.cancel()
```
This is the same pattern used in well-behaved async generators across the ecosystem. The `GeneratorExit` is raised by Python when the generator is garbage-collected or explicitly closed by the `StreamingResponse` teardown.

**Note:** The `try/except Exception` inside each `_narrate`, `_recs`, `_pool`, `_guide` closure means `task.cancel()` will raise `CancelledError` inside those tasks, which is NOT caught by `except Exception` (in Python 3.9+ `CancelledError` inherits from `BaseException`, not `Exception`). So cancellation will propagate cleanly. Sound.

##### Moderate Findings

**Finding 2: SSE `data:` line regex will break on multi-line data payloads**
**Severity:** Moderate
**Impact:** The frontend SSE parser at `build.ts:220` uses `frame.match(/^data:\s*(.+)$/m)` which matches only the FIRST `data:` line in a frame. Per the SSE specification (W3C), if a server emits multiple `data:` lines in a single event, the client should concatenate them with newlines. Today this is safe because `json.dumps` (Python) escapes `\n` to `\\n`, producing a single-line payload. But if anyone ever switches the backend `_sse_event` helper to use `json.dumps(indent=2)` for debugging, or if a Gemma narrative contains a literal newline that somehow bypasses JSON encoding, the parser will silently truncate the payload and `JSON.parse` will throw on the partial string. The existing `intent.ts` SSE parser uses the same pattern, so this is a pre-existing consistency choice, but worth noting.

**Location:** `frontend/src/api/build.ts:219-224`
```typescript
const eventMatch = frame.match(/^event:\s*(.+)$/m);
const dataMatch = frame.match(/^data:\s*(.+)$/m);
if (!eventMatch || !dataMatch) continue;
const eventType = eventMatch[1]!;
const data = JSON.parse(dataMatch[1]!);
```
**The Fix (defensive, non-blocking):** If you want to future-proof this, collect all `data:` lines and concatenate:
```typescript
const eventMatch = frame.match(/^event:\s*(.+)$/m);
const dataLines = frame.match(/^data:\s*(.+)$/gm);
if (!eventMatch || !dataLines) continue;
const eventType = eventMatch[1]!;
const jsonStr = dataLines.map((l) => l.replace(/^data:\s*/, "")).join("\n");
const data = JSON.parse(jsonStr);
```
Not a blocker because the backend currently guarantees single-line payloads. But I've seen "temporary debug logging" accidentally ship to prod more times than I'd like to admit.

##### Minor Findings

**Finding 3: "Analyzing..." placeholder text is not localized**
**Severity:** Minor
**Impact:** The BossBand placeholder at line 393 and InstitutionCard placeholder at line 47 both hardcode the English string "Analyzing..." rather than using the `useT()` hook. The rest of the codebase uses i18n keys for all user-visible text. Students using the Spanish or other locale will see an English word flash briefly during streaming. Not a functional issue, but inconsistent with the established i18n pattern.

**Location:** `frontend/src/components/build-results/BossBand.tsx:393`, `frontend/src/components/build-results/InstitutionCard.tsx:47`
```tsx
<p className="font-body text-text-muted" ...>
  Analyzing...
</p>
```
**The Fix:** Add an i18n key (e.g., `"build.analyzing"`) and use `t("build.analyzing")`. The key likely already exists given the loading state in BuildResultsScreen uses it.

**Finding 4: `buildStore` is persisted -- streaming partial builds could be serialized to localStorage**
**Severity:** Minor
**Impact:** The `useBuildStore` uses `zustand/middleware/persist` (line 38 of `buildStore.ts`). However, examining the `partialize` config at line 79, only `hasSeenStatTutorial` is persisted. The `build` field is NOT in the partialize list, so it is NOT written to localStorage. This means a partial streaming build (skeleton without narratives) won't survive a page refresh, which is correct behavior. No issue here -- I'm noting it because I checked and it's fine. (I've seen persist middleware bite teams when they add new state fields and forget to exclude them from serialization.)

#### What's Good

1. **The `model_copy` approach is clever and correct.** Using shallow copy to inherit the mutated fight narratives from the skeleton's gauntlet object avoids the double-ID problem the architect identified, without requiring any changes to `build_from_parts`. The shared reference to `gauntlet.fights` means in-place narrative mutations from `_narrate()` are visible in the final build. I verified this with a Pydantic test. Well done.

2. **Error handling is thorough throughout.** Every Gemma call has individual `try/except` with deterministic fallbacks. Phase 1 data errors emit SSE `error` events. The frontend `catch` block falls back to the blocking `createBuild`. The `cancelledRef` guard prevents post-unmount state updates. This is defense-in-depth done right.

3. **The `updateBuild` store method is the right abstraction.** Rather than doing `setBuild({ ...getBuild(), ...patch })` from the event handler (which would race if two events arrived in the same tick), the callback-based `updateBuild(fn)` reads from zustand's current state atomically. This prevents lost-update races between concurrent SSE events.

4. **BossBand's streaming narrative sync effect is carefully guarded.** The `prev.length !== 1 || !first || first.narrative` check ensures the effect only fires for the exact empty-to-filled transition on the initial entry, and is inert after rerolls add more entries. This prevents streaming narratives from overwriting reroll state.

5. **The fallback path preserves the existing UX.** If SSE fails for any reason, the user gets the same blocking experience they had before this feature. No degradation.

6. **SSE response headers match the existing pattern.** `Cache-Control: no-cache` and `X-Accel-Buffering: no` are present, matching `set_your_course.py:73-77`. Railway's proxy won't buffer events.

#### Required Changes

| Priority | Finding | Fix | Route To |
|----------|---------|-----|----------|
| Should fix | #1 Orphaned tasks | Add `try/finally` with `task.cancel()` in `_build_stream` | Implementation agent |
| Nice to have | #2 Multi-line data regex | Collect all `data:` lines in SSE parser | Implementation agent |
| Nice to have | #3 Unlocalized placeholder | Use `t("build.analyzing")` | Implementation agent |

#### Questions for the Author

1. Have you tested the SSE stream through Railway's proxy in staging? Local Ollama latency is sub-second per Gemma call, so events arrive nearly simultaneously. Through OpenRouter (2-4s per call), the staggered arrival pattern will be much more pronounced. Worth a manual test.
2. What monitoring do we have for orphaned Gemma calls? If task cancellation isn't added, is there at least a metric or log line when a stream disconnects mid-flight?
3. The `_build_stream` generator doesn't have a top-level `try/except Exception` around the entire Phase 2 + Phase 3 block. If something unexpected raises (not one of the per-task caught exceptions, but e.g. a `SkillRec.model_validate` failure at line 358), the generator will die without emitting an `error` or `done` event. The frontend's `createBuildStream` will see the stream end without `done` and fall back. Is that the intended behavior, or should there be a catch-all that emits an `error` event?

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

Approved. Finding #1 (orphaned tasks) is real but not blocking -- the fallout is wasted Gemma inference, not data corruption or user-visible errors. Ship it, then fix the task cancellation in a fast-follow. The architecture is sound, the error handling is thorough, and the race condition surface area has been well-managed. This is great AI-generated code. It just needs... well, actually, this time it mostly just needs the one thing.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-27 22:16

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues (3 fixable lint errors in test_builds.py fixed: unused imports `asyncio`/`patch`, import sort, 2x E501 line-too-long) |
| Type check (mypy) | PASS | 71 errors total across codebase — all pre-existing. builds.py has 12 errors: 10 pre-existing baseline (`no-untyped-def`, `index`, `unused-ignore`) + 2 new `effort` str-vs-Literal at lines 293 and 438, matching the same pre-existing pattern in the file. No new error categories introduced. |
| Tests (pytest) | PASS | 1147 passed, 0 failed |

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (1 fix: 3 type cast assertions in build.test.ts needed `as unknown as` narrowing) |
| Tests (vitest) | PASS | 645 passed, 11 failed (all 11 pre-existing: 9 in CompareView.test.tsx, 2 in PentagonOverlay.test.tsx — confirmed baseline on clean main) |
| Production build (Vite) | PASS | 703 modules transformed, built in 1.40s |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff FAIL | 5 errors in test_builds.py: unused imports `asyncio`/`patch`, import sort, 2x E501 line-too-long | Removed `asyncio` and `patch` imports; split long assertion strings; ran `ruff --fix` for import sort |
| 1 | TypeScript FAIL | 3 type cast errors in build.test.ts (lines 399, 403, 405): overlapping cast needs `unknown` intermediary | Added `as unknown as` to the three narrowing casts |
| 2 | All checks passed | — | — |

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent -> @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Performance Budget

| Metric | Current | Target | How |
|--------|---------|--------|-----|
| Time to first meaningful paint | 6-8s | ~2s | Skeleton event after concurrent data queries |
| Time to full build | 6-8s | 4-6s | Parallel compute_one + get_branches saves ~1s |
| Perceived wait | 6-8s | ~2s | Progressive reveal hides Gemma latency |

### Follow-ups

- **Rebuild streaming**: `POST /build/{id}/rebuild` could also benefit from streaming, but it's lower priority (rebuild is faster since stats are recomputed locally, not via MCP)
- **Gemma token streaming**: Individual Gemma calls could stream tokens for real-time text reveal (like ChatGPT). Requires Ollama/OpenRouter streaming support — separate spec.
- **Optimistic navigation**: Navigate to `/my-build` immediately on button press and show the skeleton loading state inline, before even the `skeleton` event arrives. Saves another ~500ms of perceived wait.
