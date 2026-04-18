# Perf: `/reveal` loading screen — parallelize Gemma fan-out

**Spec:** `docs/specs/completed/perf-reveal-loading-screen.md`
**Completed:** 2026-04-18
**Status:** COMPLETE

## TL;DR

`POST /build` was firing up to 8 Gemma calls sequentially, producing 4–32 s of loading-screen time on the hot path. We fanned out all 8 calls in a single `asyncio.gather` and relaxed the frontend `minDisplayTime` floor from 2000 ms → 1000 ms. Expected p50 `/build` drops to roughly one Gemma round-trip instead of eight.

## What shipped

### Backend

- **`gemma_client.py`** — new `generate_async` / `generate_chat_async` that wrap the existing sync client through `asyncio.to_thread`. Lazy module-level `asyncio.Semaphore` sized from `GEMMA_MAX_CONCURRENCY` (default 8) keeps OpenRouter rate-limits sane. New `threading.Lock` around the `gemma.jsonl` append prevents 4 KB+ records from interleaving bytes under the 8-wide fan-out (POSIX write atomicity only holds up to `PIPE_BUF=512` on macOS).
- **`boss_fights.py`** — extracted pure scoring into `score_gauntlet(career) -> GauntletResult` (empty narratives); added `async def narrate_one(career, fight) -> str` that surfaces real bugs up through the router's `return_exceptions=True` gate while still flattening transport errors to the deterministic fallback. Sync `run_gauntlet` preserved as a facade for the CLI + tests.
- **`stat_engine.py`** — new `compute_one(*, unitid, cipcode, soc_code, …)` so `/build` stops re-running the full per-school-major pentagon and then `next()`-filtering to one SOC.
- **`skill_recs.py` / `skill_pool.py` / `guidance.py`** — async siblings of each `generate_*` that share the parsing helpers with the sync path. `skill_pool_async` preserves the "no losses/draws → return `[]`" short-circuit. `guidance._fallback_narrative` promoted to module-level so the router can reuse it.
- **`routers/builds.py`** — `create_build` is now `async def`. Pipeline: `asyncio.to_thread(compute_one)` → `score_gauntlet` (inline, cheap) → `asyncio.to_thread(branch_tree.get_branches)` → `asyncio.gather(*narrate_one[5], recs_async, pool_async, guidance_async, return_exceptions=True)` → per-site fallback on any `BaseException` → assemble + persist `Build`.

### Frontend

- **`RevealScreen.tsx:68`** — single-line change: `minDisplayTime` `2000` → `1000`. The LoadingScreen, its tokens, and all animations are byte-identical to `main` per spec §3.

## Tests added

Backend (P0 + P1 from §4, plus one concurrent-write regression test added during code review):

- `test_gemma_client.py::test_generate_async_respects_semaphore` — 6 concurrent calls at `GEMMA_MAX_CONCURRENCY=2` never exceed peak-2 in-flight. Installs a 16-worker executor so the semaphore (not the thread pool) is what's gating.
- `test_gemma_client.py::test_generate_async_logs_to_jsonl` — each async call appends exactly one JSONL record through the real `_log_exchange` path.
- `test_gemma_client.py::test_generate_async_jsonl_integrity_under_gather` — 8 concurrent calls with ~4 KB prompts + response bodies; every resulting JSONL line parses with `json.loads()`.
- `test_boss_fights.py::TestScoreAndNarrateSplit::*` + `TestNarrateOne::*` — split scoring/narrative contracts, sync-facade preservation, async narrate_one happy path + fallback-on-empty + propagation-of-unexpected-exception.
- `test_builds.py::TestCreateBuildParallelFanout::test_create_build_parallel_fanout` — all 8 async tasks start within a 100 ms window and total wall-clock < 500 ms (vs. 8 × 100 ms serial).
- `test_builds.py::TestCreateBuildPartialFailureFallback::*` — one narrate raises → other 4 produce real content + deterministic fallback for the failing one; `recs` exception → fallback recs; `guidance` exception → fallback template.
- `test_builds.py::TestCreateBuildPreservesFightOrder::test_fights_stay_in_boss_specs_order` — boss-fight order stays `BOSS_SPECS` even when slowest narrative finishes last.
- `test_stat_engine.py::TestComputeOne::*` — selection contract, `LookupError` on SOC miss, `ValueError` propagation, effort/loan_pct plumbing.

Frontend:

- `RevealScreen.test.tsx::holds LoadingScreen for at least 1000ms then reveals by 1500ms` — new 1 s floor honored; 1.5 s ceiling for fast builds.
- `RevealScreen.test.tsx::does NOT reveal before the 1000ms floor even when build resolves instantly` — floor holds under synchronous microtask resolution.

Also added an autouse `_reset_gemma_client_state` conftest fixture so the module-level semaphore rebuilds between every test — keeps the budget deterministic regardless of prior failures.

## Verification

| Check | Result |
|-------|--------|
| `ruff check app/ tests/` | PASS |
| `mypy app/` | PASS at baseline (46 errors — identical to HEAD; net-new from this spec: 0) |
| `pytest -q` | **320 passed** (previous 302 + 18 new) |
| `tsc --noEmit` | PASS |
| `vitest run` | 382 pass + **2 pre-existing ProfileScreen failures** (unrelated, no-diff vs. HEAD) + 1 skip |
| `vite build` | PASS (657 modules, 1.20 s) |
| Manual latency smoke (Ollama + OpenRouter) | **Deferred to human** — requires live INFERENCE_BACKEND runs. Automated unit tests cover fan-out correctness, fallback contracts, JSONL integrity, and the 1 s pacing floor in isolation. |

## Code review highlights (faang-staff-engineer)

Initial verdict: CHANGES REQUIRED. Four blocking findings + a missing test, all resolved:

- **F1 (P0)** — `gemma.jsonl` concurrent-write corruption. Fixed with `threading.Lock` around the append.
- **F2 (P1)** — dead router fallback branch. Removed the `try/except` inside `narrate_one` so the router's `isinstance(BaseException)` branch is the single fallback gate; renamed the corresponding test to `test_narrate_one_propagates_unexpected_exception`.
- **F3 (P1)** — module semaphore leaked across tests on failure. Fixed with the autouse conftest fixture.
- **F4 (P1)** — semaphore test could pass for the wrong reason on CI runners with small default executors. Fixed by installing a 16-worker pool for the duration of the test.
- **Missing test** — no concurrent-write regression test. Added `test_generate_async_jsonl_integrity_under_gather` with 4 KB records.

Re-review verdict: **APPROVED**.

## Deferred follow-ups (P2 from code review)

- **F5** — empty-`skill_pool`-by-design vs. empty-by-failure are indistinguishable to the frontend. Future: add a `skill_pool_status` field on `Build`.
- **F6** — `compute_one` still pulls the full per-program MCP row set and filters in memory. Future: add a `soc_code` filter to the `get_career_paths` MCP tool for a single-row fetch.
- **F8** — three `_private_underscore` cross-module imports remain (`boss_fights._fallback_narrative`, `skill_recs._fallback_recs`). Pure rename — can land in a follow-up cleanup PR.
- **F9** — one-line semaphore-scope comment clarifying the budget is "live Gemma requests" not "active worker threads".
- **F10** — defensive length assertion after the gather unpack.

## Files touched

Backend:

- `backend/app/routers/builds.py`
- `backend/app/services/boss_fights.py`
- `backend/app/services/gemma_client.py`
- `backend/app/services/guidance.py`
- `backend/app/services/skill_pool.py`
- `backend/app/services/skill_recs.py`
- `backend/app/services/stat_engine.py`
- `backend/tests/services/conftest.py`
- `backend/tests/services/test_boss_fights.py`
- `backend/tests/services/test_builds.py`
- `backend/tests/services/test_gemma_client.py` (new)
- `backend/tests/services/test_stat_engine.py`

Frontend:

- `frontend/src/screens/RevealScreen.tsx`
- `frontend/src/screens/RevealScreen.test.tsx` (new)

Docs:

- `docs/specs/perf-reveal-loading-screen.md` → `docs/specs/completed/perf-reveal-loading-screen.md`
- `reports/perf-reveal-loading-screen-2026-04-18.md` (this file)
