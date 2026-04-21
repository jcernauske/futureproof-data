# Performance: SOC Reveal Frontend Orchestration — Completion Report

**Date:** 2026-04-20
**Spec:** `docs/specs/performance-soc-reveal-frontend.md`
**Status:** COMPLETE

## Summary

Implemented outcomes-first paint for the Set Your Course screen's career reveal flow. Career chips now render as soon as `/build/outcomes` returns, ~2–5 seconds before tier grouping completes. Previously, the user saw a loading skeleton until both outcomes AND tier classification finished.

## What Changed

| File | Change |
|------|--------|
| `frontend/src/hooks/useDebouncedTrigger.ts` | New hook: 250ms debounce with immediate-fire on CIP change |
| `frontend/src/hooks/useSetYourCourse.ts` | `SocRevealState` state machine, AbortController cancellation, monotonic request-ID counter, debounced career fetch |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Three render states: skeleton → ungrouped chips + shimmer → grouped tiers. Removed local orchestration state |
| `frontend/src/api/client.ts` | `apiPost` accepts `AbortSignal` |
| `frontend/src/api/build.ts` | `getOutcomes`/`getTieredCareers` forward `AbortSignal` |
| `backend/app/routers/builds.py` | `is_disconnected()` check before Gemma dispatch on `/build/tier` |

## Performance Results

Measured via `performance.now()` instrumentation on OpenRouter (cloud Gemma 4 26B).

| Run | School | Major | Chips Paint | Tiers Paint | Earlier Feedback |
|-----|--------|-------|-------------|-------------|-----------------|
| 1 | UIUC | pre-med | 5.6s | 7.8s | **2.2s** |
| 2 | Illinois State | deaf ed | 29.5s | 34.2s | **4.8s** |
| 3 | Millikin | acting | 8.6s | 11.1s | **2.5s** |
| 4 | (not recorded) | (not recorded) | 7.1s | 11.1s | **4.0s** |

**Key metric:** chips paint within 5–15ms of outcomes resolving (same React render frame). Pass criterion was ≤200ms.

**Debounce:** stacked typing now produces 1 API call per debounce window instead of N calls per keystroke.

## Test Coverage

- 6 new tests for `useDebouncedTrigger` (timing, immediate-fire, unmount, strict-mode)
- 7 new tests for `useSetYourCourse` (state machine, stale rejection, abort, debounce)
- 2 new tests for `SetYourCourseScreen` (intermediate shimmer, tier headers)
- 3 new tests for `build.ts` (signal forwarding, abort rejection)
- All 588 frontend tests pass, all backend tests pass

## Code Review

Approved by @faang-staff-engineer with two non-blocking recommendations:
1. **Tier-error resilience:** keep showing ungrouped chips if tier call fails instead of switching to full error state (deferred — functional as-is)
2. **`asyncio.to_thread` for tier endpoint:** pre-existing issue, not introduced by this spec

## Follow-ups

- Streaming `/build/tier` (spec Decision #6) — would eliminate remaining perceived wait
- Tier response client-side cache by outcomes hash
- Tier-error fallback state (code review Finding #2)
