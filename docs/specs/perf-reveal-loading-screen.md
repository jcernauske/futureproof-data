# Performance: `/reveal` loading screen — parallelize Gemma fan-out

## Claude Code Prompt

```
Read the spec at docs/specs/perf-reveal-loading-screen.md in its entirety.

This is a Standard-weight performance spec. Backend is parallelization (asyncio.gather fan-out); frontend is a single-line numeric tuning of `minDisplayTime` on RevealScreen. No schema changes, no new public API surface, no visual redesign. Architecture Review, Design Vision, and Design Audit are SKIPPED (see §3 — numeric tuning, not a visual redesign).

Execute the following workflow:

1. IMPLEMENTATION
   - Implement §4 Technical Specification as written (backend parallelization + the single-line frontend `minDisplayTime` change).
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: update only the tests listed under "Authorized Test Modifications".
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human via §10 Discussion.
   - Log all work to §6 Implementation Log.
   - Run backend (ruff + mypy + pytest) to verify build.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). After 3: escalate via §10.

2. TESTING
   - Invoke @test-writer to review §4 Testing Impact Analysis and implement every "New Tests Required" entry in priority order (P0 first).
   - Backend tests: pytest in backend/tests/.
   - Frontend tests: vitest in frontend/ — @test-writer must add the RevealScreen pacing-floor coverage listed in §4.
   - Run the full pytest + vitest suites to catch regressions.
   - If still broken after 3 attempts: escalate via §10.

3. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests. This spec touches concurrency, asyncio, and an LLM fan-out — that is exactly their remit. Pay special attention to:
     * race conditions between fallback text and real Gemma responses
     * exception propagation through asyncio.gather (return_exceptions semantics)
     * semaphore leakage on exception paths
     * any regression in logs/gemma.jsonl ordering or completeness
   - Reviewer writes findings to §8 Code Review.
   - If APPROVED: proceed to step 4.
   - If CHANGES REQUIRED: route back to implementer via §10.
   - If BLOCKER: STOP, alert human.

4. VERIFICATION
   - Invoke @fp-builder to run full build verification.
   - Backend: ruff check, mypy, pytest.
   - Frontend: TypeScript, vitest, Vite production build — one-line `RevealScreen.tsx` change plus new vitest coverage.
   - Log results to §9 Verification.
   - Run the manual latency smoke listed in §9 under both INFERENCE_BACKEND=ollama and INFERENCE_BACKEND=openrouter. Smoke includes confirming the relaxed pacing floor is honored (no 2 s hold on fast backends).
   - If all green: mark status COMPLETE.

5. COMPLETION
   - Update top-level Status to COMPLETE.
   - Check off all Success Criteria in §1.
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review.
   - Generate report to reports/perf-reveal-loading-screen-YYYY-MM-DD.md.
   - Move this file to docs/specs/completed/.
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-17 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.1 |
| Last Updated | 2026-04-18 |
| Blocked By | — |
| Related Specs | `docs/specs/cloud-gemma-deployment.md`, `docs/specs/screen-career-pick-reveal.md` |

---

## §1 Feature Description

### Overview

Parallelize the up-to-eight sequential Gemma LLM calls inside `POST /build` so the `/reveal` loading screen shrinks from 10–30 s today to ≤5 s, without removing the loading screen (the loading screen is a kept pacing beat, not a bug). In addition, relax the 2 s `minDisplayTime` floor in `RevealScreen.tsx` to a shorter pacing-beat minimum so the perf win is actually visible to the user on fast backends.

### Problem Statement

The `/reveal` loading screen is currently shown for far longer than its intended pacing beat. Tracing `backend/app/routers/builds.py:56-103` shows the endpoint fires up to **8 Gemma calls sequentially**:

- 5× boss narrative calls inside `boss_fights.run_gauntlet` (`backend/app/services/boss_fights.py:661-677`, a sequential `for fight in fights` loop)
- 1× `skill_recs.generate_recs` (`backend/app/services/skill_recs.py`)
- 1× `skill_pool.generate_pool` (`backend/app/services/skill_pool.py`, skipped if all bosses win)
- 1× `guidance.generate_guidance` (`backend/app/services/guidance.py:122-139`)

At typical latencies — ~500 ms per call on local Ollama, ~2–4 s per call on the OpenRouter demo path — the sequential fan-out produces 4–32 s of wall-clock time on the loading screen. The frontend 2-second `minDisplayTime` (`frontend/src/screens/RevealScreen.tsx:68`) is a floor, not a ceiling, and does not help — and once the backend is fast, that floor actively masks the perf win. This spec drops the floor from 2000 ms to 1000 ms (see Decision #8) so the screen still feels intentional but no longer holds users back.

The calls are almost all independent: grep verified that `skill_recs`, `skill_pool`, and `guidance` read `fight.result`, `fight.label`, and `fight.reason` only — never `fight.narrative`. This means every Gemma call after scoring can fan out in parallel in a single `asyncio.gather`.

Jeff likes the loading screen as an atmospheric beat. This spec shortens the wait, it does not eliminate it; a 1 s minimum display floor (relaxed from 2 s) keeps the screen a pacing beat instead of a flash, while letting the perf win actually reach users.

### Success Criteria

- [ ] Wall-clock p50 duration of `POST /build` drops to ≤ `1.3 × (single Gemma call latency)` on both Ollama and OpenRouter backends.
- [ ] `/reveal` loading screen p50 visible duration is between the **new 1 s pacing floor** and a 5 s ceiling under OpenRouter.
- [ ] `/reveal` loading screen p50 visible duration equals `max(pacing_floor_ms, POST /build wall-clock)` — no hidden padding beyond the floor.
- [ ] On fast backends (Ollama local), total `/reveal` visible time is ≤ 1.5 s when `POST /build` returns in < 500 ms.
- [ ] All 5 boss narratives, `guidance`, `skill_recs`, and `skill_pool` (when applicable) are populated in the response with no regression in content quality.
- [ ] If any single Gemma call fails or times out, the deterministic fallback for that site fires; the other 7 calls complete normally.
- [ ] `logs/gemma.jsonl` continues to capture every Gemma call (interleaved timestamps are acceptable and expected).
- [ ] No 429s or provider rate-limit failures under OpenRouter at default semaphore sizing.
- [ ] Frontend changes are scoped to a single-line `minDisplayTime` tuning in `RevealScreen.tsx`; `LoadingScreen.tsx`, all design tokens, and all animations are byte-identical to current `main`.
- [ ] pytest suite green (incl. new tests); ruff + mypy clean; vitest green incl. the new RevealScreen pacing-floor test.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Wrap the existing **sync** `gemma_client.generate` with `asyncio.to_thread` at the call sites instead of introducing an async OpenAI client | Smallest blast radius: no SDK swap, no retooling of `gemma_client` logging, retry, fallback, and config-resolution code. `asyncio.to_thread` is stdlib since 3.9 and this project is 3.11+. | (a) Rewrite `gemma_client` around `AsyncOpenAI` — bigger refactor, forces every synchronous caller (CLI harness, tests, scripts/) to change. Rejected. (b) `concurrent.futures.ThreadPoolExecutor` directly — works but reinvents what `asyncio.to_thread` already does. Rejected. |
| 2 | Split `boss_fights.run_gauntlet` into **`score_gauntlet` (sync, pure)** and **`attach_narratives` (async, fan-out)** | The scoring loop is cheap deterministic Python (~ms). The narrative loop is the slow LLM loop. Separating them makes each testable in isolation and lets `attach_narratives` share the `asyncio.gather` with the other Gemma calls. | Keep a single `run_gauntlet` with an internal async path — obscures the cost model and makes the sync callers (any that exist today) regress subtly. Rejected. |
| 3 | Run **all 8 Gemma calls in a single `asyncio.gather`** rather than staged waves | Verified via grep that `skill_recs`, `skill_pool`, and `guidance` read only `fight.result`/`label`/`reason` — never `fight.narrative`. All 8 calls depend only on the synchronous `score_gauntlet` output + `get_branches` result, both of which are cheap and resolved before the gather. | Two-stage gather (narratives first, then recs/pool/guidance) — safer but adds one extra round-trip of latency for no correctness gain. Rejected. |
| 4 | **Drop the redundant `compute_pentagon`** in `/build` by adding a `compute_one(unitid, cipcode, soc_code, …)` helper to `stat_engine` | `/career-pick` has already run `compute_pentagon` via `/build/outcomes`, and the user's selection comes back carrying the SOC. `/build` today re-runs the full per-school-major pentagon then `next()`-filters to the single SOC — wasted MCP round-trip and wasted CPU. | Accept the already-computed `CareerOutcome` in the `BuildRequest` body — trusts the client, larger wire payload. Rejected per approved plan. |
| 5 | Add an **`asyncio.Semaphore` in `gemma_client`** with default `GEMMA_MAX_CONCURRENCY=8` | OpenRouter enforces per-key RPM; eight simultaneous 26B-MoE calls from one demo machine can trip it. A module-level semaphore inside `gemma_client` guarantees every call site shares the budget and the guard cannot be forgotten at a new call site. | Put the semaphore in `builds.py` — callers would have to remember it every time. Rejected. |
| 6 | **Do not** add streaming (SSE) to `/build` | Streaming would require adding a streaming variant to `gemma_client`, a FastAPI `StreamingResponse` endpoint, an EventSource on the frontend, and a new loading-screen rendering model. Large spec on its own. | Ship streaming together with parallelism — too big, two risks in one PR. Rejected. |
| 7 | **Do not** add hover-prefetch on `/career-pick` | Hiding the loading screen is explicitly against Jeff's design intent. | Fire `/build` on hover/focus — rejected per product direction. |
| 8 | **Relax `minDisplayTime` from 2000 ms to 1000 ms** in `RevealScreen.tsx` | The 2 s floor was sized for the old 10–30 s backend where "the screen feels intentional" was the binding constraint. Once `/build` is ≤5 s (and ≤1 s on Ollama), the 2 s floor actively masks the perf win. 1 s keeps the loading screen longer than one full message-rotation (2 s per message means we clip mid-message — acceptable; the message is still legible) and longer than the emoji-float cycle feels abrupt, without gating users. Exact value TBD during implementation based on motion feel; 1000 ms is the recommendation, and anything in the 800–1200 ms band is acceptable without a spec amendment. | (a) Drop the floor entirely — rejected, makes the screen a flash on Ollama. (b) Make the floor adaptive (e.g., ramp down only on success, keep 2 s on error) — rejected, adds logic for no real win. (c) 500 ms — rejected as too short; cuts off the first message before it's readable. |

### Constraints

- Python 3.11+ (per `backend/pyproject.toml`) — `asyncio.to_thread` and modern asyncio semantics available.
- `gemma_client.generate` remains **sync**; every existing sync caller (CLI harness, scripts, tests) keeps working unchanged.
- `logs/gemma.jsonl` must continue to record every call, in any order. Timestamps preserve causality.
- Frontend scope is limited to a **single numeric change** on `frontend/src/screens/RevealScreen.tsx:68` (per §3 and Decision #8). `LoadingScreen.tsx`, all Brightpath tokens, and all animations are byte-identical to current `main`. Any other frontend diff is out of scope for this spec.
- Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` must be verified end-to-end before completion.

### Out of Scope (future specs)

- **Streaming Gemma responses over SSE** — deferred per Decision #6.
- **Hover-prefetch on `/career-pick`** — deferred per Decision #7.
- **Native `AsyncOpenAI` migration** — deferred per Decision #1.
- **Progressive reveal UI** (render pentagon + stats before Gemma completes) — a frontend rearchitecture; out of scope.

---

## §3 UI/UX Design

### Scope

Single-line numeric tuning in `frontend/src/screens/RevealScreen.tsx:68` — the `minDisplayTime` promise timeout drops from `2000` to `1000` ms. No component changes, no route changes, no token changes, no new animations, no markup changes.

### Component contract

| Component | Status |
|-----------|--------|
| `frontend/src/components/LoadingScreen.tsx` | Byte-identical to current `main`. Props, animation tokens, copy, and pacing all unchanged. |
| `frontend/src/screens/RevealScreen.tsx` | Single numeric change on line 68. Reveal staggers (2.0s–3.7s) after `LoadingScreen` unmounts are unchanged. |
| Brightpath tokens (`--color-state-success`, `--color-state-loading`, motion tokens in `motion.ts`) | Untouched. |

### Motion feel

The existing `LoadingScreen` animations continue to run at their current speeds:

- Emoji float — 3 s period — clipped at ~1/3 cycle on fast Ollama runs; the float still reads as motion because the first third is the largest amplitude delta.
- Message rotation — 2 s per message — on fast backends the user sees only the first message; acceptable because the first message is the highest-signal one ("Forging your future self…" or equivalent).
- Dot pulse — continuous loop — reads fine at any duration ≥ 300 ms.
- Glow gradient — ambient CSS animation — unaffected.

The 1 s floor guarantees at least one full emoji-float half-cycle and one message rendering, which is the minimum for the screen to feel intentional rather than flashed.

### Agent workflow exclusions

This spec does **not** invoke `@fp-design-visionary` or `@fp-design-auditor`:

- `@fp-design-visionary` — only triggered for new screens, components, or animations. A numeric timeout change is not a design decision in the Brightpath sense.
- `@fp-design-auditor` — only triggered when Brightpath tokens, component patterns, or motion tokens change. None of those change here.

If the implementer's subjective read is that the 1 s floor looks wrong in practice, they may tune within 800–1200 ms (per Decision #8) without a spec amendment. Values outside that band require updating Decision #8 before shipping.

---

## §4 Technical Specification

### Architecture Overview

**Backend.** Inside `POST /build`, the orchestration in `backend/app/routers/builds.py:56-103` is rewritten as an `async def` function that:

1. Calls the **new** `stat_engine.compute_one(...)` to fetch a single `CareerOutcome` for the selected SOC — replacing the current `compute_pentagon(...)` + `next(...)` pattern.
2. Calls the **new** `boss_fights.score_gauntlet(career)` — the pure-Python scoring loop, returns a `GauntletResult` with empty `fight.narrative` strings.
3. Calls `branch_tree.get_branches(career.soc_code)` — unchanged, fast MCP fetch.
4. Fans out all Gemma work in a single `asyncio.gather`:
   - 5× `boss_fights.narrate_one(career, fight)` — new per-fight async helper
   - 1× `skill_recs.generate_recs_async(career, gauntlet)` — new async wrapper
   - 1× `skill_pool.generate_pool_async(career, gauntlet)` — new async wrapper (still internally short-circuits when `gauntlet.losses == 0 and gauntlet.draws == 0`)
   - 1× `guidance.generate_guidance_async(career, gauntlet, branches)` — new async wrapper
5. Attaches narratives to fights (by boss_id), assembles the `Build`, stores, persists, and returns.

`gemma_client` grows a module-level `asyncio.Semaphore` used by every new `*_async` wrapper. Existing sync `generate`/`generate_chat` entry points are unchanged and continue to be used by the CLI harness, scripts, and tests.

**Frontend.** `frontend/src/screens/RevealScreen.tsx:68` — the `minDisplayTime` promise timeout drops from `2000` to `1000` ms (Decision #8). No other frontend code changes. The loading-screen UI, tokens, animations, and reveal stagger are byte-identical to current `main`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/routers/builds.py` | Modify | Rewrite `create_build` as `async def`; replace sequential calls with `compute_one` + `score_gauntlet` + `asyncio.gather` fan-out. |
| `backend/app/services/boss_fights.py` | Modify | Extract pure scoring into `score_gauntlet(career) -> GauntletResult`. Extract per-fight narrative into `narrate_one(career, fight) -> str` (async). Keep `run_gauntlet` as a thin sync facade over `score_gauntlet` + a sync narrative loop for CLI/test callers. |
| `backend/app/services/stat_engine.py` | Modify | Add `compute_one(unitid, cipcode, soc_code, effort, loan_pct, student_major) -> CareerOutcome`. Reuse the existing MCP fetch path but filter MCP args to a single SOC where the MCP tool supports it; otherwise call the existing path and filter in memory. |
| `backend/app/services/gemma_client.py` | Modify | Add module-level `_semaphore: asyncio.Semaphore` sized from `GEMMA_MAX_CONCURRENCY` env (default `8`). Add `generate_async(...)` and `generate_chat_async(...)` that acquire the semaphore, then call the existing sync `generate` / `generate_chat` via `asyncio.to_thread`. No change to sync entry points. |
| `backend/app/services/skill_recs.py` | Modify | Add `generate_recs_async(career, gauntlet)` that delegates to `gemma_client.generate_async`. Keep existing sync `generate_recs` for CLI/test compatibility. |
| `backend/app/services/skill_pool.py` | Modify | Add `generate_pool_async(career, gauntlet)` with identical semantics (including the short-circuit when no losses/draws). Keep sync `generate_pool`. |
| `backend/app/services/guidance.py` | Modify | Add `generate_guidance_async(career, gauntlet, branches)` delegating to `gemma_client.generate_async`. Keep sync `generate_guidance`. |
| `backend/tests/services/test_boss_fights.py` | Modify | Update to cover the new `score_gauntlet` / `narrate_one` split. Existing sequential-narrative tests stay but now target `run_gauntlet` explicitly. (Authorized — see §4 Testing Impact Analysis.) |
| `backend/tests/services/test_builds.py` | Modify | Update to exercise the async `create_build` path. (Authorized.) |
| `backend/tests/services/test_stat_engine.py` | Modify | Add coverage for `compute_one`. Existing `compute_pentagon` tests untouched. (Authorized.) |
| `backend/tests/services/test_gemma_client.py` | Create | New test file for semaphore + async wrappers if one does not exist; otherwise add to the existing module. |
| `backend/tests/routers/test_builds_router.py` | Modify (if exists) or Create | Integration-style test: mock `gemma_client.generate_async` with timestamp recording; assert overlap of call intervals. |
| `frontend/src/screens/RevealScreen.tsx` | Modify | Change the `minDisplayTime` promise timeout on line 68 from `2000` to `1000` ms. No other changes. |
| `frontend/src/screens/RevealScreen.test.tsx` | Modify (if exists) or Create | Add `test_reveal_honors_relaxed_pacing_floor` per §4 Testing Impact Analysis. Authorized — see "New Tests Required". |

### Data Model Changes

None. All Pydantic models (`CareerOutcome`, `GauntletResult`, `BossFightResult`, `CareerBranch`, `Build`, `BuildRequest`, `SkillRec`) keep their current fields.

### Service Changes

New public function signatures (authoritative — exact type annotations):

```python
# backend/app/services/stat_engine.py
def compute_one(
    *,
    unitid: int,
    cipcode: str,
    soc_code: str,
    effort: str,
    loan_pct: float,
    student_major: str | None,
) -> CareerOutcome: ...
```

```python
# backend/app/services/boss_fights.py
def score_gauntlet(career: CareerOutcome) -> GauntletResult:
    """Pure-Python scoring. Returns a GauntletResult with empty fight.narrative strings."""

async def narrate_one(career: CareerOutcome, fight: BossFightResult) -> str:
    """Generate a single boss narrative via gemma_client.generate_async.
    On failure, returns the deterministic fallback (current _fallback_narrative)."""

def run_gauntlet(career: CareerOutcome, *, with_narratives: bool = True) -> GauntletResult:
    """Unchanged public signature. Now implemented as score_gauntlet + a sync narrative loop.
    Preserved for CLI harness, scripts/, and existing tests."""
```

```python
# backend/app/services/gemma_client.py
async def generate_async(
    *,
    system: str,
    user: str,
    max_tokens: int = 500,
    temperature: float = 0.7,
    model: str | None = None,
) -> str:
    """Acquire the module semaphore, then call generate() via asyncio.to_thread.
    Returns empty string on failure (same contract as generate())."""

async def generate_chat_async(
    *,
    system: str,
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.7,
    model: str | None = None,
) -> str: ...
```

```python
# backend/app/services/skill_recs.py
async def generate_recs_async(
    career: CareerOutcome, gauntlet: GauntletResult
) -> list[SkillRec]: ...

# backend/app/services/skill_pool.py
async def generate_pool_async(
    career: CareerOutcome, gauntlet: GauntletResult
) -> list[SkillRec]: ...

# backend/app/services/guidance.py
async def generate_guidance_async(
    career: CareerOutcome,
    gauntlet: GauntletResult,
    branches: list[CareerBranch],
) -> str: ...
```

Semaphore configuration:

```python
# backend/app/services/gemma_client.py (module scope)
_MAX_CONCURRENCY: int = int(os.environ.get("GEMMA_MAX_CONCURRENCY", "8"))
_semaphore: asyncio.Semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
```

Router rewrite shape (illustrative — not prescriptive on imports/ordering):

```python
# backend/app/routers/builds.py (excerpt)
@router.post("")
async def create_build(request: BuildRequest) -> Build:
    try:
        career = stat_engine.compute_one(
            unitid=request.unitid,
            cipcode=request.cipcode,
            soc_code=request.selected_soc,
            effort=request.effort,
            loan_pct=request.loan_pct,
            student_major=request.student_major,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    gauntlet = boss_fights.score_gauntlet(career)
    branches = branch_tree.get_branches(career.soc_code)

    narrative_tasks = [boss_fights.narrate_one(career, f) for f in gauntlet.fights]
    recs_task = skill_recs.generate_recs_async(career, gauntlet)
    pool_task = skill_pool.generate_pool_async(career, gauntlet)
    guidance_task = guidance.generate_guidance_async(career, gauntlet, branches)

    results = await asyncio.gather(
        *narrative_tasks, recs_task, pool_task, guidance_task,
        return_exceptions=True,
    )
    narratives = results[: len(gauntlet.fights)]
    recs, pool, narrative = results[len(gauntlet.fights):]

    for fight, text in zip(gauntlet.fights, narratives):
        fight.narrative = (
            text if isinstance(text, str) and text
            else boss_fights._fallback_narrative(fight)
        )
    if isinstance(recs, BaseException): recs = skill_recs._fallback_recs(career, gauntlet)
    if isinstance(pool, BaseException): pool = []
    if isinstance(narrative, BaseException):
        narrative = guidance._fallback_narrative(career, gauntlet)

    build = builds.build_from_parts(
        school_name=request.school_name,
        unitid=request.unitid,
        major_text=request.major_text,
        cipcode=request.cipcode,
        program_name=request.cip_title,
        effort=request.effort,
        loan_pct=request.loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=recs,
        guidance=narrative,
        skill_pool=pool,
        profile_name=request.profile_name,
    )
    state.store_build(build)
    builds.save_build(build)
    return build
```

Exact fallback symbol names (`_fallback_recs`, `_fallback_narrative`) must be verified/refactored during implementation — current private helpers may need to be exposed as module-level callables.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_boss_fights.py` | Any test asserting call count / call order of `gemma_client.generate` | High | Sequential loop changes to concurrent fan-out via `run_gauntlet` (sync) and `narrate_one` (async). Call ordering assertions break. |
| `backend/tests/services/test_builds.py` | Any test constructing `create_build` synchronously or asserting sequential call order | High | `create_build` becomes `async def` and uses `asyncio.gather`. Sync tests must be adapted to `pytest.mark.asyncio` or `asyncio.run`. |
| `backend/tests/services/test_stat_engine.py` | Tests for `compute_pentagon` | Low | `compute_pentagon` signature and behavior unchanged. New `compute_one` is additive. |
| `backend/tests/services/test_branch_tree.py` | All | None (Confirmed Safe) | No signature change to `get_branches`. |
| `backend/tests/services/test_career_tree.py` | All | None (Confirmed Safe) | Untouched. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_boss_fights.py::test_run_gauntlet_*` | Update to assert the sync `run_gauntlet` facade still produces correct results; split out new tests targeting `score_gauntlet` and `narrate_one` separately. | The sequential narrative loop moves from `run_gauntlet` to `narrate_one`; existing tests were validating both concerns together. |
| `test_builds.py::test_create_build_*` | Convert to `pytest.mark.asyncio` where needed; update Gemma mocks to support both sync and async call surfaces. | `create_build` is now async. |
| `test_stat_engine.py` | Add a new test module section for `compute_one`. | Additive coverage. |
| `RevealScreen.test.tsx` (vitest, if it exists) | Any test that hard-codes the 2000 ms `minDisplayTime` floor — update to 1000 ms. | Decision #8 relaxes the floor. |

#### Confirmed Safe

These tests must NOT break. If any fail during implementation, STOP and escalate via §10:

- `backend/tests/services/test_branch_tree.py` (all)
- `backend/tests/services/test_career_tree.py` (all)
- `backend/tests/services/test_profile.py` (all, if present)
- `backend/tests/services/test_receipts.py` (all, if present)
- `backend/tests/routers/test_wrapped_router.py` (if present) — unrelated router.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_builds.py` | `test_create_build_parallel_fanout` | Mock `gemma_client.generate_async` with per-call `asyncio.sleep` + timestamp recording. Assert all 8 calls start within <100 ms of each other (proof of parallelism, not sequential). |
| P0 | `backend/tests/services/test_builds.py` | `test_create_build_partial_failure_fallback` | One Gemma call raises; assert `return_exceptions=True` path fires that site's deterministic fallback and the other 7 produce real content. Final `Build` is well-formed. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_generate_async_respects_semaphore` | Set `GEMMA_MAX_CONCURRENCY=2`, fire 6 concurrent `generate_async` calls with a slow mock — assert at most 2 are mid-flight at any time. |
| P0 | `backend/tests/services/test_boss_fights.py` | `test_score_gauntlet_produces_empty_narratives` | `score_gauntlet(career).fights[*].narrative == ""` — pure scoring contract. |
| P0 | `backend/tests/services/test_boss_fights.py` | `test_run_gauntlet_still_populates_narratives` | Sync facade contract unchanged for CLI consumers. |
| P0 | `backend/tests/services/test_stat_engine.py` | `test_compute_one_returns_selected_soc` | Given a known (unitid, cipcode, soc_code), returns exactly that `CareerOutcome`. |
| P0 | `backend/tests/services/test_stat_engine.py` | `test_compute_one_raises_on_missing_soc` | Raises `LookupError` (or whatever `compute_one`'s contract chooses) when the SOC is not a valid outcome for the program. |
| P1 | `backend/tests/services/test_gemma_client.py` | `test_generate_async_logs_to_jsonl` | Verify `logs/gemma.jsonl` still gets one record per async call (uses tmp-path fixture + `GEMMA_LOG_DISABLED` unset). |
| P1 | `backend/tests/services/test_builds.py` | `test_create_build_preserves_fight_order` | Boss-fight-result ordering in the final `Build` matches `BOSS_SPECS` iteration order regardless of which Gemma narrative finishes first. |
| P2 | `backend/tests/services/test_builds.py` | `test_create_build_latency_budget` | With Gemma mocks at 100 ms each, assert total wall-clock < 300 ms (well below 8 × 100 ms). Not a hard CI gate — tagged `@pytest.mark.slow`. |
| P1 | `frontend/src/screens/RevealScreen.test.tsx` | `test_reveal_honors_relaxed_pacing_floor` | Mock `createBuild` to resolve in 200 ms; assert `LoadingScreen` is mounted for ≥ 1000 ms and ≤ 1500 ms. Validates the new floor and that no hidden padding beyond the floor exists. |
| P2 | `frontend/src/screens/RevealScreen.test.tsx` | `test_reveal_waits_for_slow_build` | Mock `createBuild` to resolve in 3000 ms; assert `LoadingScreen` unmounts within ~50 ms of `createBuild` resolving (i.e. backend latency drives, not the floor). |

#### Test Data Requirements

- Use existing `CareerOutcome` fixtures in `backend/tests/services/conftest.py` (confirmed present in `git status`).
- Mock `gemma_client.generate_async` (new) with `pytest-asyncio` and `unittest.mock.AsyncMock`.
- Mock the MCP path used by `compute_one` the same way existing `compute_pentagon` tests mock it — extend the conftest if the fixture is not reusable.
- Record-timestamp fixture: a small `RecordingMock` that appends `(call_args, perf_counter())` tuples and sleeps a configurable duration. Lives in `conftest.py`.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** SKIPPED — Standard-weight spec, no new architectural surface (no new modules, no API changes, no schema changes).

### @fp-data-reviewer Review
**Status:** SKIPPED — no data pipeline, crosswalk, or stat formula changes. Only call-graph re-ordering and a redundant-fetch elimination.

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
_None yet._

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

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
| vitest (frontend, incl. new RevealScreen pacing-floor test) | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder / @fp-design-auditor)
**Status:** SKIPPED — per §3 and Decision #8, frontend change is a numeric tuning (`minDisplayTime: 2000 → 1000`), not a visual redesign. No Brightpath tokens, components, or motion tokens change.

### Code Review (@faang-staff-engineer)
**Status:** PENDING

#### Findings
_Filled in by reviewer._

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff check backend/) | |
| Type check (mypy backend/app/) | |
| Tests (pytest backend/) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript (tsc --noEmit) | |
| Tests (vitest run) | |
| Production build (vite build) | |

### Manual Latency Smoke
Record p50 wall-clock for `POST /build` under each backend by running the `/reveal` flow three times back-to-back and averaging:

| Scenario | Target | Actual |
|----------|--------|--------|
| INFERENCE_BACKEND=ollama, `/build` p50 | < 2 s | |
| INFERENCE_BACKEND=ollama, `/reveal` loading p50 | 1.0–1.5 s (new 1 s floor governs) | |
| INFERENCE_BACKEND=openrouter, `/build` p50 | < 5 s | |
| INFERENCE_BACKEND=openrouter, `/reveal` loading p50 | 1.0–5.0 s | |
| `logs/gemma.jsonl` last N lines show overlapping `started_at` timestamps | yes | |
| OpenRouter 429 count during smoke | 0 | |
| On a fast Ollama run (`/build` ~400 ms), `/reveal` visible time ≤ 1.5 s (Decision #8 honored) | yes | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[placeholder — add timestamped messages between agents here]
```

---

## §11 Final Notes

**Human Review:** PENDING

_Final thoughts, lessons learned, follow-up items go here at COMPLETE time._
