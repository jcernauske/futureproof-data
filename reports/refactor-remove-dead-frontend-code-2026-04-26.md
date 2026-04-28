# Refactor: Remove Dead Frontend + Backend Code — Completion Report

**Date:** 2026-04-26
**Branch:** `dead-code-prune`
**Spec:** `docs/specs/refactor-remove-dead-frontend-code.md`
**Companion Spec:** `docs/specs/spike-analyze-orphan-api-endpoints.md`

## Summary

Deleted ~5,350 lines of confirmed-dead code across 34 files. All CONDITIONAL items were executed after the API spike analysis recommended REMOVE for all 7 orphan endpoints.

## What Was Removed

### Frontend (16 files deleted, 6 files modified)
- **`/school` flow:** `SchoolMajorScreen`, `MajorInput`, `CorrectionChips`, `CareerList`, `CollapsibleCareerSection`, `BuildSummaryBar` — replaced by `SetYourCourseScreen`
- **Orphan exports:** `rescoreBuild` (zero importers), `rebuildWithSliders` (zero importers), `ScreenshotWithFallback` (zero importers), `PlaceholderScreen` (dead `/build` route), `useSessionResume` (zero callers), `lib/api.ts` (zero importers)
- **Dead session function:** `getSession` removed from `session.ts` (live exports `saveCheckpoint` + `clearSession` kept)
- **Route cleanup:** `/school` and `/build` placeholder routes removed from `App.tsx`
- **AppHeader cleanup:** `/school` branch in `getPhaseAccent`, `isSchool` const, `handleBack` school logic

### Backend (3 files deleted, 9 files modified)
- **Legacy intent router:** `routers/intent.py` (31 LOC) — `POST /intent/` and `POST /intent/confirm`
- **Dead service functions:** `resolve_intent`, `confirm_intent`, `_intent_cache` from `services/intent.py` (198 LOC)
- **Dead resolution flow:** `resolve_major`, `_normalize`, `_exact_match`, `_substring_match`, `_yaml_lookup`, `_gemma_fallback` from `services/school_lookup.py` (171 LOC)
- **Dead models:** `MajorMatch` from `career.py`, `IntentRequest` + `IntentConfirmRequest` from `api.py`
- **Dead dep:** `rich>=13.7` from `pyproject.toml` and `Dockerfile`
- **CLAUDE.md:** Removed stale `cli.py` tree reference, updated Gold zone text

### Tests (3 files deleted, 2 files modified)
- `test_intent.py` (1,331 LOC) — all tests targeted deleted functions
- `test_yaml_regression.py` (198 LOC) — tested deleted `resolve_intent`
- `test_school_lookup.py` — `TestResolveMajor` block (144 LOC) removed; `TestSearchSchools` + `TestGetPrograms` intact

### Scripts
- `scripts/yaml_regression.py` (863 LOC) — per "no YAML lookups" memory

## Build Results

| Check | Result |
|-------|--------|
| ruff (backend) | PASS (1 pre-existing E501) |
| mypy (backend) | PASS (10 pre-existing errors, same as main) |
| pytest (backend) | 1,121 passed |
| pytest (pipeline) | 1,698 passed |
| tsc (frontend) | Clean |
| vitest (frontend) | 640 passed |
| Vite build | Clean (700 modules) |

## Code Review

**Verdict:** APPROVED by @faang-staff-engineer. All 8 verification checklist items passed. Three minor findings addressed:
1. Reverted accidental `catalog.db` binary diff
2. Removed stale `getSession` mock from `App.test.tsx`
3. Orphaned `intent_responses.json` fixture logged for follow-up

## Deviations from Spec

1. **`session.ts` partially kept.** Spec said fully delete; `saveCheckpoint` + `clearSession` are live. Only `getSession` removed.
2. **Import cleanup beyond §4 scope.** Removed newly-orphaned imports (`os`, `major_lookup`, `IntentResult`, `MajorMatch`, `Iterable`, `gemma_client`, `_GEMMA_RESOLVE_SYSTEM`) — mechanical follow-ups, not new scope.

## Follow-up Candidates

- Remove orphaned `backend/tests/fixtures/intent_responses.json`
- Endpoints 3–7 from the API spike (reports, profile/lookup, rescore, gauntlet) need a separate cleanup spec
- Stale `getSession` mock in `App.test.tsx` — cleaned in this pass
