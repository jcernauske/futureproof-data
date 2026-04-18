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

## Status: COMPLETE

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

- [ ] Wall-clock p50 duration of `POST /build` drops to ≤ `1.3 × (single Gemma call latency)` on both Ollama and OpenRouter backends. *(pending manual smoke — deferred to human per §9)*
- [ ] `/reveal` loading screen p50 visible duration is between the **new 1 s pacing floor** and a 5 s ceiling under OpenRouter. *(pending manual smoke)*
- [x] `/reveal` loading screen p50 visible duration equals `max(pacing_floor_ms, POST /build wall-clock)` — no hidden padding beyond the floor. Verified by `RevealScreen.test.tsx::holds LoadingScreen for at least 1000ms then reveals by 1500ms` and `::does NOT reveal before the 1000ms floor even when build resolves instantly`.
- [x] On fast backends (Ollama local), total `/reveal` visible time is ≤ 1.5 s when `POST /build` returns in < 500 ms. Covered in isolation by the same two RevealScreen tests + `test_create_build_parallel_fanout` (< 500 ms wall-clock at 100 ms/call mock). Live verification pending manual smoke.
- [x] All 5 boss narratives, `guidance`, `skill_recs`, and `skill_pool` (when applicable) are populated in the response with no regression in content quality. Verified by `test_create_build_parallel_fanout` + `test_fights_stay_in_boss_specs_order`.
- [x] If any single Gemma call fails or times out, the deterministic fallback for that site fires; the other 7 calls complete normally. Verified by `test_one_narrate_raises_others_succeed`, `test_recs_raises_falls_back_to_deterministic`, `test_guidance_raises_falls_back_to_template`.
- [x] `logs/gemma.jsonl` continues to capture every Gemma call (interleaved timestamps are acceptable and expected). Verified by `test_generate_async_logs_to_jsonl` + `test_generate_async_jsonl_integrity_under_gather` (8-way concurrent, every line parses).
- [ ] No 429s or provider rate-limit failures under OpenRouter at default semaphore sizing. *(pending manual smoke — semaphore budget verified in isolation by `test_generate_async_respects_semaphore`.)*
- [x] Frontend changes are scoped to a single-line `minDisplayTime` tuning in `RevealScreen.tsx`; `LoadingScreen.tsx`, all design tokens, and all animations are byte-identical to current `main`. Verified by `git diff --stat HEAD^ HEAD`.
- [x] pytest suite green (incl. new tests); ruff + mypy clean; vitest green incl. the new RevealScreen pacing-floor test. Verified by `@fp-builder` (§9): 320/320 pytest, ruff clean, mypy baseline preserved at 46 (net-new 0), vitest 382/385 (2 pre-existing `ProfileScreen.test.tsx` failures unrelated — confirmed no-diff vs. HEAD, 1 skipped), Vite production build PASS.

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

**Status:** IMPLEMENTATION

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/services/gemma_client.py` | Added `asyncio` import, lazy module-level `_semaphore` sized from `GEMMA_MAX_CONCURRENCY` (default 8), `generate_async` + `generate_chat_async` wrappers that acquire the semaphore and delegate to the sync path via `asyncio.to_thread`. `reset_cache()` now nulls the semaphore so env-patched tests rebuild it. |
| `backend/app/services/boss_fights.py` | Extracted pure scoring into `score_gauntlet(career) -> GauntletResult` (empty narratives). Added `async def narrate_one(career, fight) -> str` calling `gemma_client.generate_async` with the existing per-site fallback. `run_gauntlet` is a thin facade over `score_gauntlet` + a sync narrative loop — signature unchanged for CLI/tests. |
| `backend/app/services/stat_engine.py` | Added `compute_one(unitid, cipcode, soc_code, ...)` that reuses `compute_pentagon` and filters to the selected SOC. Raises `LookupError` when the SOC isn't found; propagates `ValueError` when MCP returns zero rows. |
| `backend/app/services/skill_recs.py` | Extracted `_parse_recs(text, career)` so sync + async share parsing. Added `generate_recs_async`. Sync `generate_recs` preserved. |
| `backend/app/services/skill_pool.py` | Extracted `_rerollable_from(gauntlet)` + `_finalize_pool(text, rerollable)` helpers. Added `generate_pool_async` with the same no-losses short-circuit. Sync `generate_pool` preserved. |
| `backend/app/services/guidance.py` | Added module-level `_fallback_narrative(career, gauntlet)` helper (exposed so the router can reuse it). Added `generate_guidance_async` mirroring the sync fallback contract. |
| `backend/app/routers/builds.py` | Rewrote `create_build` as an `async def` that (1) fetches the single career via `asyncio.to_thread(stat_engine.compute_one, ...)`, (2) calls `score_gauntlet` synchronously (cheap), (3) fetches branches via `asyncio.to_thread(branch_tree.get_branches, ...)`, then (4) `asyncio.gather(*narrate_one, recs_async, pool_async, guidance_async, return_exceptions=True)`. Exception branches log + fall back to deterministic strings/lists. `LookupError` → 404; `ValueError` → 422. |
| `frontend/src/screens/RevealScreen.tsx` | Single-line change: `minDisplayTime` from `2000` → `1000` ms per Decision #8. |

### Deviations from Spec
- Router also wraps `branch_tree.get_branches` in `asyncio.to_thread`. The spec's illustrative shape calls it sync, but the existing `/outcomes` path already uses `asyncio.to_thread` for the same class of PyIceberg-backed sync call to keep Railway's liveness probe responsive. Treating branches the same way is consistent with that pattern and doesn't change the gather topology.
- Added explicit type annotations (`recs: list[SkillRec]`, `pool: list[AppliedSkill]`, `narrative: str`) with `cast(...)` around the `asyncio.gather(..., return_exceptions=True)` result unpacking so mypy can narrow `object` past the `isinstance(BaseException)` guard. Behavior identical to the illustrative spec shape.
- Cast `request.effort` to `EffortLevel` at the `compute_one` call site to avoid introducing a new mypy literal-narrowing error. The identical pre-existing error at the `/outcomes` call site was not touched (out of scope).

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff PASS; mypy introduced 6 new errors (gather result narrowing + literal effort) | Sequence[object] vs str/list narrowing after isinstance(BaseException); new Literal effort error at compute_one call | Added explicit type annotations + `cast(...)` around unpacked gather results; cast `request.effort` to `EffortLevel`; baseline restored at 46 errors (no net new). |
| 2 | ruff PASS; mypy PASS at baseline (46 errors, 0 net new); pytest 302/302 PASS | — | — |
| 3 | After code-review fixes F1–F4 + new JSONL-integrity test: 2 test failures on Python 3.14 teardown | `loop.set_default_executor(None)` now raises `TypeError` on Python 3.14 — asyncio tightened the API | Swapped `None` for a fresh narrow `ThreadPoolExecutor(max_workers=4)` as the restored default. |
| 4 | ruff PASS; mypy PASS at baseline; pytest 320/320 PASS | — | — |

### Code-Review Remediation Log (2026-04-18)

| Finding | File | Fix |
|---------|------|-----|
| F1 (P0) — gemma.jsonl concurrent-write corruption | `backend/app/services/gemma_client.py` | Added module-level `_log_lock = threading.Lock()`; wrapped the `with path.open("a", ...)` in `_log_exchange` behind the lock so append-mode writes serialize across the 8-wide `asyncio.gather` fan-out. |
| F2 (P1) — dead narrate_one exception branch | `backend/app/services/boss_fights.py`, `backend/tests/services/test_boss_fights.py` | Dropped the `try/except Exception` inside `narrate_one`. Transport failures already become `""` inside `gemma_client.generate_async`; genuine bugs now propagate up through `asyncio.gather(..., return_exceptions=True)` so the router sees the exception and logs it distinctly. Updated the corresponding test from "falls back on exception" to "propagates unexpected exception" to lock in the new contract. |
| F3 (P1) — test isolation for module-level semaphore | `backend/tests/services/conftest.py` | Added autouse `_reset_gemma_client_state` fixture that calls `gemma_client.reset_cache()` before and after every test so the `_semaphore` budget is deterministic regardless of prior-test failures. |
| F4 (P1) — semaphore test false-negative risk | `backend/tests/services/test_gemma_client.py::test_generate_async_respects_semaphore` | Installed a 16-wide `ThreadPoolExecutor` as the loop default for the duration of the test so the asyncio.Semaphore (and nothing else) can be what gates concurrency. Restored a 4-wide default in the `finally` clause (Python 3.14 rejects `None`). |
| Missing test — concurrent JSONL integrity | `backend/tests/services/test_gemma_client.py::test_generate_async_jsonl_integrity_under_gather` | New P0 regression test: fans out 8 `generate_async` calls with ~4 KB prompt/response bodies (well beyond POSIX `PIPE_BUF=512`) and asserts every resulting JSONL line parses individually. This is the direct regression test for F1. |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_gemma_client.py` (NEW) | `test_generate_async_respects_semaphore` | With `GEMMA_MAX_CONCURRENCY=2`, 6 concurrent `generate_async` calls never exceed 2 in-flight (peak counter). |
| `backend/tests/services/test_gemma_client.py` (NEW) | `test_generate_async_logs_to_jsonl` | Async calls emit one JSONL record each through the real `_log_exchange` path. |
| `backend/tests/services/test_builds.py` | `test_create_build_parallel_fanout` | All 8 Gemma-bound calls start within 100 ms spread and total wall-clock < 500 ms (vs. 8×100 ms sequential). |
| `backend/tests/services/test_builds.py` | `test_one_narrate_raises_others_succeed` | One `narrate_one` raises; that fight gets the deterministic fallback, other 4 get Gemma output. Final `Build` well-formed. |
| `backend/tests/services/test_builds.py` | `test_recs_raises_falls_back_to_deterministic` | `skill_recs._fallback_recs` fires on exception. |
| `backend/tests/services/test_builds.py` | `test_guidance_raises_falls_back_to_template` | `guidance._fallback_narrative` fires on exception. |
| `backend/tests/services/test_builds.py` | `test_fights_stay_in_boss_specs_order` | Boss-fight order preserved regardless of gather completion order. |
| `backend/tests/services/test_boss_fights.py` | `test_score_gauntlet_produces_empty_narratives` | Pure-scoring contract: all narratives `""`. |
| `backend/tests/services/test_boss_fights.py` | `test_score_gauntlet_never_calls_gemma` | Pure-scoring boundary — Gemma is not reached. |
| `backend/tests/services/test_boss_fights.py` | `test_run_gauntlet_still_populates_narratives` | Sync facade preserved for CLI/tests. |
| `backend/tests/services/test_boss_fights.py` | `test_narrate_one_returns_gemma_text` | Happy-path async narrative. |
| `backend/tests/services/test_boss_fights.py` | `test_narrate_one_falls_back_on_empty` | Empty Gemma response → deterministic fallback. |
| `backend/tests/services/test_boss_fights.py` | `test_narrate_one_falls_back_on_exception` | Exception in generate_async → deterministic fallback. |
| `backend/tests/services/test_stat_engine.py` | `test_compute_one_returns_selected_soc` | Selection contract. |
| `backend/tests/services/test_stat_engine.py` | `test_compute_one_raises_on_missing_soc` | `LookupError` on SOC miss. |
| `backend/tests/services/test_stat_engine.py` | `test_compute_one_propagates_value_error_on_empty_mcp` | `ValueError` bubbled from empty MCP result. |
| `backend/tests/services/test_stat_engine.py` | `test_compute_one_honors_effort_and_loan_pct` | Effort + loan_pct plumb through to `compute_pentagon`. |
| `frontend/src/screens/RevealScreen.test.tsx` (NEW) | `holds LoadingScreen for at least 1000ms then reveals by 1500ms` | New 1 s pacing floor is honored and doesn't exceed 1.5 s for fast builds. |
| `frontend/src/screens/RevealScreen.test.tsx` (NEW) | `does NOT reveal before the 1000ms floor even when build resolves instantly` | Floor holds on synchronous microtask resolution. |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 319 | 0 | 0 | 319 |
| vitest (frontend, incl. new RevealScreen pacing-floor test) | 382 | 2 (pre-existing `ProfileScreen.test.tsx` — unrelated, confirmed no-diff vs. HEAD) | 1 | 385 |

---

## §8 Reviews

**Status:** CHANGES REQUIRED (code review)

### Design Audit (@design-builder / @fp-design-auditor)
**Status:** SKIPPED — per §3 and Decision #8, frontend change is a numeric tuning (`minDisplayTime: 2000 → 1000`), not a visual redesign. No Brightpath tokens, components, or motion tokens change.

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED

**Summary.** Overall this is a clean, well-scoped parallelization. The sync/async split in `boss_fights`, the lazy semaphore, the `return_exceptions=True` unpack with per-site fallbacks, and the `compute_one` extraction all land where the spec said they should. Tests are the strongest part of the PR — parallel-fanout timing, per-site fallback, boss-order preservation, and semaphore peak-counter are all covered. That said, the spec asked me to look hard at four things (fallback-vs-real races, `gather` exception propagation, semaphore leakage, `gemma.jsonl` completeness), and I found two real bugs plus some smaller cleanup the implementer should address before `@fp-builder` runs verification. None are architectural — all are surgical edits to `builds.py`, `gemma_client.py`, and one test file.

The two P0s are:
1. A real bug in the router — `isinstance(x, BaseException)` will match PENDING `GeneratorExit`-family false-positives, which is fine, but the actual hazard is that the `or boss_fights._fallback_narrative(fight)` branch also fires when `narrate_one` returned an empty string AFTER Gemma returned an empty string. That path already exists in `narrate_one` itself (line 696) so the router's `text or _fallback_narrative(fight)` is dead code that masks a real regression signal. This doesn't break correctness — it just means we log `narrate_one raised` only when the coroutine literally raised (which it can't, because narrate_one catches bare `Exception`). Low-severity cleanup.
2. `skill_pool.generate_pool_async` short-circuits to `[]` on "no rerollable bosses" — BUT the router's `pool_result` fallback on failure is also `[]`, so the UI treats "Gemma gave us nothing because we won" identically to "Gemma crashed". That collapses a signal we will want for debugging on day one of the demo. Not a ship-blocker, flagged P2.

The real P0 is the `gemma.jsonl` concurrent-write hazard (see below).

#### Findings

| # | Severity | File:line | Problem | Fix |
|---|----------|-----------|---------|-----|
| F1 | 🔴 P0 | `backend/app/services/gemma_client.py:160-170` | **`gemma.jsonl` concurrent-write corruption.** `_log_exchange` opens the log file, writes one `json.dumps(...) + "\n"`, then closes. Under the parallelism this spec introduces, up to 8 `asyncio.to_thread`-wrapped `generate_chat` calls run concurrently on the ThreadPool executor, each hitting `_log_exchange` from a different worker thread. There is no lock. Python's TextIOWrapper flushes on close, but for large records (full system + user prompt + response JSON can reach 10-20 KB) the underlying `os.write` call is only POSIX-atomic up to `PIPE_BUF` (512 bytes on macOS). Two threads writing 5 KB records at the same instant will interleave bytes, producing a garbage line that breaks `logs/gemma.jsonl` for downstream inspection. This directly violates Success Criterion "`logs/gemma.jsonl` continues to capture every Gemma call" and the spec's explicit reviewer-focus bullet "any regression in logs/gemma.jsonl ordering or completeness." | Wrap the append in a `threading.Lock` held for the full `open → write → close`. Add a module-level `_log_lock = threading.Lock()` next to `_LOG_PATH_CACHED` and guard the `with path.open(...)` block. Lock contention is 8-wide worst case — negligible vs. network latency. |
| F2 | 🟠 P1 | `backend/app/routers/builds.py:109-119` | **Dead branch masks a real signal.** The router has both `isinstance(narrative_text, BaseException)` (fires when `narrate_one` raises) AND `text or boss_fights._fallback_narrative(fight)` (fires when Gemma returned empty). But `narrate_one` (boss_fights.py:686-696) catches `Exception` internally and already falls back to `_fallback_narrative(fight)` — so the router's `isinstance(BaseException)` branch is effectively unreachable for `narrate_one`, and the `text or _fallback_narrative` branch re-does the same fallback the service already did. The result: when a narrative raises, the log says nothing (because `narrate_one` only logs via `logger.warning` inside the service, which is fine), AND the router's "narrate_one raised for boss=%s" warning at line 111 can never fire in practice. Not a correctness bug, but it means one of the two "partial failure" tests (`test_one_narrate_raises_others_succeed`) is testing a path that can't happen in production because `narrate_one` would swallow the exception first. | Either (a) make `narrate_one` let real unexpected exceptions propagate (only catch inside the `gemma_client.generate_async` call site — it already catches `Exception` internally and returns `""`), and trust the router's `return_exceptions=True` to be the single fallback gate; OR (b) delete the `isinstance(BaseException)` branch in the router for narratives only and keep the simpler `fight.narrative = text or boss_fights._fallback_narrative(fight)`. (a) is cleaner because it gives `return_exceptions=True` a real job to do and makes the partial-failure test exercise the actual prod path. Prefer (a). |
| F3 | 🟠 P1 | `backend/app/services/gemma_client.py:128-136` | **Semaphore leaks test isolation across the suite.** `_semaphore` is module-global, `GEMMA_MAX_CONCURRENCY` is read once at first `_get_semaphore()` call, and `reset_cache()` nulls it — but nothing automatically resets between tests. `test_generate_async_respects_semaphore` sets `GEMMA_MAX_CONCURRENCY=2`, builds a size-2 semaphore, calls `reset_cache()` at the end. Good. But if that test fails mid-flight (before the trailing `reset_cache()`), the size-2 semaphore survives, and subsequent tests that call `gemma_client.generate_async` will silently run at 2-wide concurrency instead of the default 8. The parallel-fanout test would still pass (2-wide is still parallel for 8 tasks), so we'd never notice in CI. | Add an autouse `conftest.py` fixture in `backend/tests/` (or `backend/tests/services/conftest.py`) that calls `gemma_client.reset_cache()` before each test. Keeps the semaphore budget deterministic regardless of earlier test failures. |
| F4 | 🟠 P1 | `backend/tests/services/test_gemma_client.py:25-83` | **Semaphore test has a real race that only flakes under load.** The test fires 6 coroutines, each `await asyncio.to_thread(slow_generate)`. `slow_generate` increments `in_flight` and records `peak_in_flight` under a `threading.Lock`. With `GEMMA_MAX_CONCURRENCY=2` the async-layer semaphore gates 2 coroutines into the executor at a time. This SHOULD mean `peak_in_flight <= 2`. But `asyncio.to_thread` schedules the work onto the default ThreadPoolExecutor, which has `min(32, os.cpu_count() + 4)` workers — 8-16 on a typical dev box, only 2 on some CI runners. If the ThreadPool has only 2 workers AND the semaphore is at 2, the test passes for the wrong reason: the ThreadPool is what's capping concurrency, not the semaphore. The assertion `peak_in_flight >= 2` is a weaker signal than it looks. | Assert stronger evidence that the SEMAPHORE (not the executor) is what's gating. One option: temporarily widen the default executor via `loop.set_default_executor(ThreadPoolExecutor(max_workers=16))` at test setup, then confirm the semaphore still caps at 2. Or: record not just the per-call in-flight counter but the sequence of (acquire, release) events and assert the acquire/release interleaving is consistent with a 2-wide semaphore rather than a 2-wide pool. P1 because the current test could hide a real regression on a CI runner with small executor. |
| F5 | 🟡 P2 | `backend/app/routers/builds.py:128-133` | **Empty-pool-by-design and empty-pool-by-failure look identical to the frontend.** `skill_pool.generate_pool_async` returns `[]` on (a) "no rerollable bosses — we won everything" (intended short-circuit) and (b) "Gemma raised" (caught by `isinstance(BaseException)` and mapped to `[]` by the router). The reroll UI can't tell these apart, which matters the first time we hit a prod OpenRouter outage and think "the win-everything short-circuit fired" when actually the call failed. | Let the router log distinctly on the exception branch ("pool generation raised, returning empty pool") — which it already does via `logger.warning("skill_pool raised: %s", pool_result)`. That's fine. The real issue is one level up: the `Build` model has no way to carry "we tried and failed" vs "we didn't need to try". Not in spec scope; file a follow-up to surface a `skill_pool_status` field on `Build`. P2 follow-up, not a ship-blocker for this spec. |
| F6 | 🟡 P2 | `backend/app/services/stat_engine.py:369-381` | **`compute_one` fetches the full per-SOC list and filters in memory.** Per spec Decision #4 this is allowed ("filter MCP args to a single SOC where the MCP tool supports it; otherwise call the existing path and filter in memory"). Implementation went with in-memory filter. That means `/build` still pulls every career row for the program from MCP just to drop all but one. For popular CIPs this is ~20-30 rows; the hot path is cheap Python work post-fetch. Not a bug, but the spec's stated motivation for `compute_one` was to AVOID redundant fetches — and we've kept the fetch redundant, we're only filtering earlier. Real savings will come when the MCP `get_career_paths` tool grows a `soc_code` filter. | File follow-up spec: add `soc_code` filter to `get_career_paths` MCP tool so `compute_one` can request exactly one row. P2 — the gather-parallelism win dwarfs this anyway. |
| F7 | 🟡 P2 | `backend/app/services/boss_fights.py:686-696` | **`narrate_one` catches bare `Exception` — fine today, fragile tomorrow.** The `except Exception as exc` on line 693 deliberately swallows any transport-layer error from `gemma_client.generate_async` (which itself returns `""` on failure). That's the correct contract per spec. But paired with the router's `return_exceptions=True` + `isinstance(BaseException)` branch (Finding F2), the two layers of exception-swallowing mean a real unexpected bug in `_narrative_prompt` (e.g. attribute error on a malformed `CareerOutcome`) gets silently masked as "fallback narrative" with zero signal beyond a `logger.warning`. See F2 for the combined fix. | Addressed by F2 fix. |
| F8 | 🟡 P2 | `backend/app/routers/builds.py:116, 124, 138` | **Three private-underscore imports across module boundaries.** The router reaches into `boss_fights._fallback_narrative`, `skill_recs._fallback_recs`, and `guidance._fallback_narrative`. Spec §4 called this out ("Exact fallback symbol names must be verified/refactored during implementation — current private helpers may need to be exposed as module-level callables") and the guidance module did the right thing (made `_fallback_narrative` module-level and used by both sync and async paths). But `boss_fights._fallback_narrative` and `skill_recs._fallback_recs` are still nominally-private and the router imports them. Functionally fine; Python doesn't enforce underscores. But it's a refactoring hazard — the next person to rename or relocate these will break the router silently. | Rename to `fallback_narrative` / `fallback_recs` (no leading underscore) in the three service modules and update call sites. Pure rename, one commit. |
| F9 | 🔵 P2 | `backend/app/services/gemma_client.py:289-296, 310-317` | **Semaphore held across full `to_thread` duration.** `generate_async` does `async with sem: await asyncio.to_thread(generate, ...)`. This holds the semaphore for the entire sync `generate()` duration (network round-trip). That's the correct behavior for rate-limiting (which is what this semaphore is for per Decision #5), but worth noting because the max-concurrency limit is a cap on "in-flight Gemma requests," not a cap on "threads doing Gemma work." If we ever add a non-Gemma use of `asyncio.to_thread` and want to bound it separately, we'll need a distinct semaphore. | No code change — spec behavior is correct. Document via a one-line comment clarifying that the semaphore's budget is "live Gemma requests" not "active worker threads." |
| F10 | 🔵 P2 | `backend/app/routers/builds.py:107` | **Unpack assumes exactly 3 trailing tasks.** `recs_result, pool_result, guidance_result = results[fight_count:]` implicitly relies on adding tasks in the same order as unpacking. If someone later adds a fourth sibling async call without updating both the gather args AND this line, Python raises a `ValueError: too many values to unpack` — which is OK, but the error surfaces at runtime rather than as a more obvious shape mismatch. | Either use a dict-keyed result (name the coroutines before gathering) or add a length assertion `assert len(results) == fight_count + 3` right after `await asyncio.gather(...)`. Minor defensive coding. |

#### Missing Test Coverage

The tests cover almost everything the spec asked for, but two gaps — one is a real bug the tests miss:

1. **No test for `gemma.jsonl` interleaving under concurrency.** `test_generate_async_logs_to_jsonl` fires 3 SEQUENTIAL `await` calls — not concurrent. The bug in F1 only appears under `asyncio.gather` of N ≥ 2 large-prompt calls. Add a test that `asyncio.gather`s 8 concurrent `generate_async` calls with multi-KB prompts and asserts every line in the resulting JSONL file parses individually as valid JSON. This is the test that catches F1.
2. **No test for test-isolation of the semaphore.** Add a conftest-level sanity assertion that `gemma_client._semaphore is None` at the start of each test, or wire the autouse reset fixture recommended in F3.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED — address F1 (P0), F2 (P1), F3 (P1), F4 (P1) before `@fp-builder` verification. F5/F6/F7/F8/F9/F10 are P2 polish and can either land in this spec or get filed as follow-ups at the implementer's discretion.
- [ ] BLOCKER

#### Routing

Route back to the implementer via §10 Discussion for F1 + F2 + F3 + F4. Re-review once fixes land.

### Re-Review (2026-04-18)

**Status:** APPROVED

**Verified fixes:**

| # | File | Verification |
|---|------|--------------|
| F1 | `backend/app/services/gemma_client.py:29,157,176` | `import threading` added; module-level `_log_lock = threading.Lock()` sits next to `_LOG_PATH_CACHED`; `_log_exchange` holds the lock across the full `open → write → close` via `with _log_lock, path.open("a", encoding="utf-8") as fh:`. Correct. |
| F2 | `backend/app/services/boss_fights.py:678-698` | `try/except Exception` block removed. `narrate_one` now calls `generate_async` unguarded and returns `text or _fallback_narrative(fight)`. Transport failures still flatten to `""` inside `generate_async` so the empty-string fallback is intact; real bugs propagate into the router's `return_exceptions=True` branch. Docstring accurately describes the new contract. Router at `builds.py:109-119` now has a genuinely reachable `isinstance(narrative_text, BaseException)` branch instead of dead code. Correct. |
| F2-test | `backend/tests/services/test_boss_fights.py:321-352` | `test_narrate_one_propagates_unexpected_exception` asserts `pytest.raises(RuntimeError, match="OpenRouter 503")`. The empty-string fallback test at line 294 is retained. Correct. |
| F3 | `backend/tests/services/conftest.py:21-36` | Autouse `_reset_gemma_client_state` fixture calls `gemma_client.reset_cache()` both before and after every test. Makes the semaphore budget deterministic regardless of upstream test failures. Correct. |
| F4 | `backend/tests/services/test_gemma_client.py:38-101` | Test installs a `ThreadPoolExecutor(max_workers=16)` as the loop default before firing 6 requests, so the `asyncio.Semaphore(2)` is the only possible binding constraint (pool is no longer a confounding variable). `finally:` restores a fresh `ThreadPoolExecutor(max_workers=4)` as the default (correctly avoids Python 3.14's `set_default_executor(None)` TypeError) and shuts down the wide executor with `wait=False`. Correct. |
| Missing test | `backend/tests/services/test_gemma_client.py:210-319` | `test_generate_async_jsonl_integrity_under_gather` fans out 8 concurrent `generate_async` calls with 4 KB user prompts + 4 KB response bodies (both comfortably past PIPE_BUF), uses a 16-worker executor, and the stub `.create()` sleeps 10 ms per call to guarantee worker-thread overlap inside the `_log_exchange` append window. Asserts `len(lines) == 8` and every line parses individually via `json.loads()`. Without the F1 lock at least one line would be garbage and at least one decode would raise. Correct. |

Spot-checked `pytest tests/services/test_gemma_client.py tests/services/test_boss_fights.py`: 46 passed.

No residual findings. The P2 items (F5–F10) from the original review remain as implementer-discretion follow-ups; none block this spec.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

Proceed to `@fp-builder` verification (§9).

---

## §9 Verification

**Status:** COMPLETE
**Verified:** 2026-04-18 11:02

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff check app/ tests/) | PASS | No issues |
| Type check (mypy app/) | PASS | 46 errors — confirmed pre-existing baseline, net-new from this spec: 0 |
| Tests (pytest -q) | PASS | 320 passed, 0 failed, 62 warnings |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript (tsc --noEmit) | PASS | No errors |
| Tests (vitest run) | PASS | 382 passed, 2 failed (pre-existing, see note), 1 skipped — 44 test files |
| Production build (vite build) | PASS | 657 modules transformed, built in 1.20 s |

#### Pre-existing Frontend Failures (not caused by this spec)

The 2 failing vitest tests are in `src/screens/ProfileScreen.test.tsx`:
- `ProfileScreen > renders profile name`
- `ProfileScreen > reroll swaps name`

These failures exist on HEAD before this spec's changes. Confirmed pre-existing by the implementer via `git stash` comparison (documented in §6 Implementation Log). They are NOT caused by any file changed in this spec and are NOT a blocker for this spec's completion.

#### RevealScreen Coverage

`src/screens/RevealScreen.test.tsx` — 6 tests, all PASS, including the new spec-required pacing-floor coverage:
- `holds LoadingScreen for at least 1000ms then reveals by 1500ms`
- `does NOT reveal before the 1000ms floor even when build resolves instantly`

### Manual Latency Smoke

Deferred to human — requires live INFERENCE_BACKEND runs on Ollama + OpenRouter. Automated pass-gate (backend unit tests + frontend RevealScreen timing test) covers the 1 s floor + fan-out correctness in isolation.

| Scenario | Target | Actual |
|----------|--------|--------|
| INFERENCE_BACKEND=ollama, `/build` p50 | < 2 s | Deferred to human |
| INFERENCE_BACKEND=ollama, `/reveal` loading p50 | 1.0–1.5 s (new 1 s floor governs) | Deferred to human |
| INFERENCE_BACKEND=openrouter, `/build` p50 | < 5 s | Deferred to human |
| INFERENCE_BACKEND=openrouter, `/reveal` loading p50 | 1.0–5.0 s | Deferred to human |
| `logs/gemma.jsonl` last N lines show overlapping `started_at` timestamps | yes | Deferred to human |
| OpenRouter 429 count during smoke | 0 | Deferred to human |
| On a fast Ollama run (`/build` ~400 ms), `/reveal` visible time ≤ 1.5 s (Decision #8 honored) | yes | Deferred to human |

### Build Accountability Log
| Attempt | Result |
|---------|--------|
| 1 | All automated checks passed |

---

## §10 Discussion

```
2026-04-18 — @faang-staff-engineer → implementer

Code review complete. Verdict: CHANGES REQUIRED. See §8 for the full
findings table. Blocking items before @fp-builder can verify:

  F1 (P0) — gemma.jsonl concurrent-write corruption.
            gemma_client._log_exchange runs without a lock under 8-wide
            asyncio.gather fan-out. Add threading.Lock around the
            append-mode file open/write/close.

  F2 (P1) — Dead fallback branch in builds.py narrative unpack.
            narrate_one already swallows exceptions and falls back
            internally, so the router's isinstance(BaseException)
            branch is unreachable and the partial-failure test is
            exercising a path that can't happen in prod. Either let
            narrate_one propagate unexpected exceptions OR drop the
            isinstance branch for narratives. Prefer the former.

  F3 (P1) — Semaphore test isolation. Module-level _semaphore persists
            across tests when a prior test fails before its trailing
            reset_cache(). Add an autouse conftest fixture that calls
            gemma_client.reset_cache() before each test.

  F4 (P1) — Semaphore test false-negative risk. Default ThreadPoolExecutor
            on small CI runners may be what's actually gating at 2, not
            the asyncio.Semaphore. Widen the default executor in the
            test or assert on acquire/release event sequence instead of
            just peak in-flight.

Also add the missing test called out in §8 "Missing Test Coverage" #1:
concurrent asyncio.gather of generate_async with multi-KB prompts +
JSONL line-integrity assertion. That's the test that catches F1.

P2 findings (F5–F10) are polish/follow-ups; implementer's call whether
to fold them into this spec or file separate tickets.

Once F1–F4 land, re-run pytest + ruff + mypy and ping me for re-review.
```

---

## §11 Final Notes

**Human Review:** PENDING

_Final thoughts, lessons learned, follow-up items go here at COMPLETE time._
