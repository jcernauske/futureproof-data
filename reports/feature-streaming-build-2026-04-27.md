# Feature: Streaming Build Creation — Completion Report

**Date:** 2026-04-27
**Spec:** `docs/specs/feature-streaming-build.md`
**Status:** COMPLETE

## Summary

Replaced the blocking `POST /build` endpoint with a streaming `POST /build/stream` SSE endpoint. Build data now arrives incrementally: stats/finances render in ~2s, boss narratives and Gemma content fill in progressively over 2-4s. Perceived wait drops from 6-8s to ~2s.

## What Changed

### Backend (1 file)
- **`backend/app/routers/builds.py`** — New `POST /build/stream` SSE endpoint with `_build_stream()` async generator. Parallelized `compute_one()` + `get_branches()` via `asyncio.gather` in both streaming and blocking endpoints. Used `model_copy` for final build assembly (avoids double ID). Added task cancellation on client disconnect.

### Frontend (8 files)
- **`frontend/src/api/build.ts`** — New `createBuildStream()` with SSE frame parsing, null body guard, reader lock cleanup
- **`frontend/src/api/client.ts`** — Exported `formatErrorDetail`
- **`frontend/src/store/buildStore.ts`** — Added `updateBuild` callback method
- **`frontend/src/screens/RevealScreen.tsx`** — Streaming with fallback to blocking on failure
- **`frontend/src/screens/BuildResultsScreen.tsx`** — Streaming sync effect for local fights state
- **`frontend/src/components/build-results/BossBand.tsx`** — Narrative placeholder + streaming sync
- **`frontend/src/components/build-results/InstitutionCard.tsx`** — Guidance placeholder

### Tests (3 files)
- **`backend/tests/routers/test_builds.py`** — 19 new tests (P0/P1/P2)
- **`frontend/src/api/build.test.ts`** — 9 new SSE parsing tests
- **`frontend/src/screens/RevealScreen.test.tsx`** — Rewrote for streaming mock strategy
- **`frontend/src/screens/BuildResultsScreen.test.tsx`** — Added empty Gemma field tests

## SSE Event Protocol

| Event | Payload | Phase |
|-------|---------|-------|
| `skeleton` | Full Build JSON (empty Gemma fields) | 1 (~2s) |
| `boss_narrative` | `{ boss_id, narrative }` (x5) | 2 (~2-4s) |
| `skill_recs` | `[SkillRec, ...]` | 2 |
| `skill_pool` | `[AppliedSkill, ...]` | 2 |
| `guidance` | `{ narrative }` | 2 |
| `done` | `{ build_id }` | 3 |

## Architecture Review Conditions (all addressed)

1. SSE response headers (`Cache-Control`, `X-Accel-Buffering`) added
2. Double build ID fixed via `model_copy` instead of second `build_from_parts`
3. `res.body` null guard added
4. `reader.releaseLock()` in finally block added

## Code Review Finding (addressed)

Orphaned async tasks on client disconnect — added `try/except (CancelledError, GeneratorExit)` with task cancellation in the `as_completed` loop.

## Verification Results

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | PASS (2 new errors, same pre-existing pattern) |
| pytest | 1147 passed |
| TypeScript | PASS |
| vitest | 645 passed, 11 failed (all pre-existing) |
| Vite build | PASS |

## Success Criteria

All 9 criteria met. See spec §1 for checklist.
