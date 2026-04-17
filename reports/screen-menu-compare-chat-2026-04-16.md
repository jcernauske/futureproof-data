# Screen 10 — Menu / Compare / Chat — Completion Report

**Spec:** `docs/specs/screen-menu-compare-chat.md`
**Date:** 2026-04-16
**Status:** COMPLETE

## What Shipped

The post-build hub: where students land after saving a build and where the product loop closes (build → fight → branch → save → **compare/chat/new** → build again).

- **Saved Builds list** — DuckDB-backed via new `GET /builds?profile_name=X` endpoint. Save Slot Card per DESIGN.md with mini pentagon, W/L/D, date, most-recent highlight.
- **Risk-focused Compare** — never declares a winner. Per-boss headlines with `accent-caution` left border + italic kicker ("Your builds disagree here.") on divergent rows. Pentagon overlay with 2–3 colored shapes at 20% fill opacity (visionary's revision from spec's 25%) and sequential `springs.smooth` draw-in. Auto-loaded Gemma comparison narrative.
- **Ask Gemma** chat panel — slide-out (360px desktop / full-width mobile) with starter pills, async dots, multi-turn history. Cancellation-safe via `sessionRef` token (won't write phantom messages if the user closes mid-request).
- **New Build** flow — `resetInputs()` clears school/major/effort/loans, preserves profile and tutorial state, navigates to `/school`.

## Architecture Decisions Locked

- New router file `backend/app/routers/builds_collection.py` exposes `GET /builds` and `POST /builds/compare`. Replaces the typo route `POST /build/s/compare` (removed).
- Chat reuses the existing `POST /build/{id}/chat` from `guidance_router.py` — no new backend service.
- All endpoints reuse existing service functions (`builds.list_builds`, `builds.compare_builds`, `guidance.chat_with_context`).

## Files Changed

### Backend (4 files)
- `backend/app/routers/builds_collection.py` — NEW (`GET /builds`, `POST /builds/compare`)
- `backend/app/routers/builds.py` — removed buggy `/s/compare` route
- `backend/app/main.py` — mounted new router
- `backend/tests/routers/test_builds_collection.py` — NEW (9 tests)

### Frontend (15 files, 11 new)
- `frontend/src/screens/MenuScreen.tsx` — NEW
- `frontend/src/components/menu/{BuildCard,MiniPentagon,CompareView,RiskHeadlineCard,PentagonOverlay,GemmaChat,ChatMessage}.tsx` — 7 NEW
- 5 component test files — NEW (32 tests)
- `frontend/src/api/menu.ts` + `mockMenu.ts` — NEW
- `frontend/src/api/build.ts` — added `getBuild()`
- `frontend/src/store/buildInputStore.ts` — added `resetInputs()`
- `frontend/src/App.tsx` — added `/menu` route

## Verification Results

| Check | Result |
|-------|--------|
| Backend ruff | PASS |
| Backend mypy (new file) | PASS — 0 errors in `builds_collection.py` |
| Backend pytest | PASS — 276/276 |
| Frontend TypeScript | PASS |
| Frontend vitest | 323 / 325 — 2 failures are pre-existing in `ProfileScreen.test.tsx`, verified by stash. 32 new tests all pass. |
| Vite production build | PASS — 641 modules, 689 kB |

## Review Outcomes

| Stage | Verdict | Notes |
|-------|---------|-------|
| Architecture (@fp-architect) | APPROVED | Three contract reconciliations applied to §4 (compare path, chat location, builds list endpoint). |
| Design Vision (@fp-design-visionary) | APPLIED | Refinements: 20% overlay opacity, italic divergence kicker, sequential pentagon draw-in. |
| Design Audit (@fp-design-auditor) | PASS WITH MINOR ISSUES → APPROVED | Both FAILs fixed (MiniPentagon 0.18→0.15; `#6bc494` deferred per Button.tsx convention). All MINOR items applied. |
| Code Review (@faang-staff-engineer) | CHANGES REQUIRED → APPROVED | 2 HIGH (cancellation in GemmaChat + MenuScreen), 2 MEDIUM (CompareView empty guard, snapshot history), 2 LOW (max_length, exception chain) all fixed. 4 LOW deferred as polish. |
| Verification (@fp-builder) | ALL PASSED | No new failures. Same 2 pre-existing ProfileScreen test failures observed. |

## Known Follow-ups (not blocking)

- Add `--color-accent-thrive-hover` token to eliminate `#6bc494` literal across the project (currently in `Button.tsx` and `GemmaChat.tsx`).
- Consolidate `buildInputStore.reset()` and `resetInputs()` (currently identical bodies).
- Pre-existing `ProfileScreen.test.tsx` failures predate this work — owner unknown.
- Stretch goal: "Download Report" button calling `GET /build/{id}/report`. Not implemented; backend ready.

## Test Coverage Snapshot

41 new tests (32 frontend + 9 backend) covering: P0 + P1 from §4 testing impact analysis, plus saboteur paths (no profile guard, getBuild rejection, whitespace submit, unknown ID 404, missing body 422, summary-chat failure fallback).
