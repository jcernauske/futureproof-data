# Refactor: Remove Confirmed Dead Frontend Code (and Linked Pure-Dead Backend Code)

## Claude Code Prompt

```
Read the spec at docs/specs/refactor-remove-dead-frontend-code.md in its entirety.

This is a deletion-only refactor. No new features. No behavior change for any live user flow.
The dead code was confirmed by a staff-engineer audit and a Codex verification pass — see §2 Decision Log.

Execute the following workflow (Standard template):

1. IMPLEMENTATION
   - Delete every file in §4 "File Changes" with action = Delete.
   - Apply every section-deletion in §4 "Section Deletions" exactly as specified.
   - Do NOT delete anything that is not in §4. If you find adjacent dead code, log it in §10 — do not act.
   - Do NOT touch anything in §4 "Out of Scope (Explicitly Keep Live)".
   - After deletions, run:
     * Backend: cd backend && ruff check . && mypy app/ && pytest
     * Frontend: cd frontend && npx tsc --noEmit && npx vitest run
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). After 3 failures, set status BLOCKED and escalate.
   - Log every deletion to §6.

2. TESTING
   - Invoke @test-writer to verify §4 Testing Impact Analysis is correct.
   - For each test file in "Authorized Test Modifications" — confirm the test is deleted (not silently skipped).
   - Run the full backend pytest suite and full frontend vitest suite.
   - Every "Confirmed Safe" test in §4 must still pass. If any fail, STOP and escalate.

3. CODE REVIEW
   - Invoke @faang-staff-engineer to review the diff.
   - Reviewer must verify: (a) no live import path is severed, (b) no behavior change in the live /set-your-course flow, (c) no test was silently disabled.
   - Writes findings to §8.

4. VERIFICATION
   - Invoke @fp-builder for full build verification (ruff + mypy + pytest + tsc + vitest + Vite production build).
   - Log results to §9.

5. COMPLETION
   - Update Status to COMPLETE.
   - Generate report to reports/refactor-remove-dead-frontend-code-2026-04-26.md.
```

---

## Status: DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-26 |
| Author | Jeff + Claude (staff-engineer audit) |
| Spec Version | 1.0 |
| Last Updated | 2026-04-26 |
| Blocked By | — |
| Related Specs | `spike-analyze-orphan-api-endpoints.md` (API-surface decisions tracked separately) |

---

## §1 Feature Description

### Overview
Delete confirmed dead code identified by a staff-engineer audit (verified by Codex). Targets the legacy `/school` workflow (replaced by `/set-your-course`), the Rich-CLI spike remnants, and a small set of orphan frontend exports.

### Problem Statement
The `localization-support` branch carries ~1,500–2,500 LOC of confirmed-dead code from two superseded surfaces:

1. The `/school` entry flow (`SchoolMajorScreen` + `MajorInput` + `CorrectionChips` + supporting components and hook) — replaced by the live `SetYourCourseScreen` flow.
2. The Rich CLI proof-of-concept — already archived under `archive/spikes/cli/`, but its backend dependencies (`resolve_major`, `MajorMatch`) and a stale `rich` dep linger in the live tree.

Plus a handful of frontend orphan exports (`rescoreBuild`, `rebuildWithSliders`, `frontend/src/lib/api.ts`, `ScreenshotWithFallback`, `PlaceholderScreen`) with zero callers.

Carrying this code costs us:
- **Cognitive load** for every contributor reading `frontend/src/components/school/` or `backend/app/services/intent.py`.
- **Test maintenance** — `backend/tests/services/test_intent.py` is 1,200+ lines, mostly testing dead public functions.
- **False signals** to future audits and to Gemma/Claude Code when generating new code that mirrors dead patterns.

### Success Criteria
- [ ] Every file/section in §4 is deleted.
- [ ] `cd frontend && npx tsc --noEmit` is clean.
- [ ] `cd frontend && npx vitest run` — all tests pass; no test silently skipped.
- [ ] `cd backend && ruff check . && mypy app/ && pytest` — all green.
- [ ] `cd frontend && npm run build` — Vite production build succeeds.
- [ ] No route, component, hook, API client, or service that powers the live `/set-your-course → /career-pick → /build → /menu` flow is touched.
- [ ] CLAUDE.md lines 29 and 92 updated to remove stale `backend/cli.py` references.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Pure-deletion spec — no refactor, no rename, no consolidation | Audit produced a confirmed-dead list. Mixing refactor with deletion expands review scope and risk. | Combine with code consolidation in `services/intent.py` — rejected, too much surface for one spec. |
| 2 | Defer all four registered-but-uncalled API endpoints (`/intent/`, `/intent/confirm`, `/builds/compare/report`, `/build/{id}/report`, `/profile/lookup`, `/build/{id}/rescore`, `/build/{id}/gauntlet`) to a separate spec | Per CLAUDE.md "no path is out of scope" — registered endpoints are public surface. They could be probed by judges, beta testers, or external scripts. Cleanup needs an explicit decision, not a quiet delete. | Bundle into this spec — rejected, conflates pure-dead-code with API-surface decisions. |
| 3 | Keep `services/intent.py` underscore helpers (`_get_school_cips`, `_derive_intent_seed`, `_promote_to_leaf_cip`, etc.) | They are reused by the live `set_your_course.py`. Codex verified. | Move helpers into `set_your_course.py` — rejected, separate refactor. |
| 4 | Delete `rich` from `backend/pyproject.toml` AND `backend/Dockerfile`. Regenerate lockfile. | Codex flagged that `rich` lives in two places. Dropping only one would leave the dep half-installed. | Leave `rich` "in case" — rejected, no live code imports it. |
| 5 | Delete `scripts/yaml_regression.py` + `tests/scripts/test_yaml_regression.py` together with `intent.resolve_intent` removal | Per CLAUDE.md "no YAML lookups" feedback memory. The regression script tests behavior we no longer want. | Keep them and stub out — rejected, perpetuates dead code. |
| 6 | `services/intent.py` `resolve_intent` + `confirm_intent` + `_intent_cache` removal happens in this spec, NOT in the API spec | The router (`routers/intent.py`) is API-surface (deferred). But the underlying service functions are pure-dead in our import graph the moment the router goes. The API spec (spec 2) decides if router goes. If yes, this spec wires up the service deletion via §10 hand-off. | Defer service deletion too — rejected, creates a two-step removal where one step is mechanical. |

**Update:** Decision 6 creates a dependency on spec 2's outcome. **Resolution:** This spec assumes the API spec recommends removing the legacy `/intent/` and `/intent/confirm` endpoints. If the API spec recommends KEEPING them, the items in §4 marked `[CONDITIONAL — pending API spec verdict]` are dropped from this spec's scope. See §10 for hand-off.

### Constraints
- The branch (`localization-support`) currently has many uncommitted changes (see `git status` in CLAUDE prompt). This spec must be committed in isolation — do not bundle with localization work.
- The CLAUDE.md "no path is out of scope" rule applies: every deletion must be re-verified against the live frontend at the moment of execution, not against a stale grep.
- No test may be silently disabled. If a test fails after a deletion, the test is either deleted in §4 or the deletion is wrong.

---

## §3 UI/UX Design

**SKIPPED** — backend + dead-frontend deletion only. No live UI changes.

---

## §4 Technical Specification

### Architecture Overview
Pure deletion. No new modules, no schema changes, no service additions.

### File Changes — Frontend (Delete entire file)

| File | Action | Justification |
|------|--------|---------------|
| `frontend/src/screens/SchoolMajorScreen.tsx` | Delete | Only registered at `App.tsx:28` (`<Route path="/school">`). No `navigate("/school")` anywhere. Replaced by `SetYourCourseScreen`. |
| `frontend/src/screens/SchoolMajorScreen.test.tsx` | Delete | Tests for the deleted screen. |
| `frontend/src/components/school/MajorInput.tsx` | Delete | Only consumer is `SchoolMajorScreen.tsx:182`. Calls legacy `POST /intent/` + `POST /intent/confirm`. |
| `frontend/src/components/school/MajorInput.test.tsx` | Delete | Tests for the deleted component. |
| `frontend/src/components/school/CorrectionChips.tsx` | Delete | `grep -rn "CorrectionChips"` returns only its own definition. Zero importers. |
| `frontend/src/components/school/CareerList.tsx` | Delete | Only importer is `CollapsibleCareerSection.tsx`, which is itself dead. |
| `frontend/src/components/school/CollapsibleCareerSection.tsx` | Delete | Zero importers. |
| `frontend/src/components/ui/BuildSummaryBar.tsx` | Delete | Only consumer is `SchoolMajorScreen.tsx:152`. |
| `frontend/src/hooks/useSessionResume.ts` | Delete | Defined and exported, zero callers. Session restore is write-only in the live flow. |
| `frontend/src/screens/PlaceholderScreen.tsx` | Delete | Only consumer is the dead `/build` placeholder route at `App.tsx:39-44` ("F3 — coming"). |
| `frontend/src/components/landing/ScreenshotWithFallback.tsx` | Delete | Zero importers. |
| `frontend/src/lib/api.ts` | Delete | Zero importers. Live API base lookup is inline in `frontend/src/api/client.ts:1`. |
| `frontend/src/api/session.ts` | Delete | `getSession` only consumed by `useSessionResume` (deleted above). |

### File Changes — Backend (Delete entire file)

| File | Action | Justification |
|------|--------|---------------|
| `backend/app/routers/intent.py` | Delete `[CONDITIONAL — pending API spec verdict]` | Legacy `POST /intent/` + `POST /intent/confirm`. No frontend caller. Replaced by `/intent/stream` + `/intent/chip` + `/intent/commit` in `set_your_course.py`. |
| `scripts/yaml_regression.py` | Delete | Imports `app.services.intent.resolve_intent`. Per "no YAML lookups" memory, the regression target is intentionally removed. |
| `tests/scripts/test_yaml_regression.py` | Delete | Tests for the deleted script. |

### File Changes — Section Deletions (file stays, sections removed)

| File | Section | Justification |
|------|---------|---------------|
| `frontend/src/App.tsx` | Line 5 (`import SchoolMajorScreen`) and line 28 (`<Route path="/school" element={<SchoolMajorScreen />} />`) | Drops with `SchoolMajorScreen.tsx`. |
| `frontend/src/App.tsx` | Lines 39-44 (`<Route path="/build" element={<PlaceholderScreen label="Career reveal — coming in F3" />} />` and the `import PlaceholderScreen` line) | Drops with `PlaceholderScreen.tsx`. F3 shipped long ago. |
| `frontend/src/components/ui/AppHeader.tsx` | Line 18 (`isSchool` constant), line 63 (`pathname.startsWith("/school")` branch in `getPhaseAccent`), lines 75-83 (`isSchool` branch in `handleBack`) | All three reference the deleted `/school` route. |
| `frontend/src/api/gauntlet.ts` | Lines 42-51 (`rescoreBuild` export) | Zero callers. |
| `frontend/src/api/build.ts` | Lines 98-107 (`rebuildWithSliders` export) | Zero callers. The live "adjust" flow goes through `/set-your-course` + `createBuild`. |
| `frontend/src/screens/MenuScreen.test.tsx` | Line 287 — fix stale test name `'"New Build" calls resetInputs() then navigates to /school (P1)'` (assertion already checks `/profile`) | Pure docs drift. |
| `backend/app/services/intent.py` | Line 23 (`_intent_cache` dict + writes) and lines 504-697 (`resolve_intent` and `confirm_intent`) `[CONDITIONAL — pending API spec verdict]` | Public functions only consumed by the dead `routers/intent.py`. Underscore helpers below them stay live (used by `set_your_course.py`). |
| `backend/app/services/school_lookup.py` | Lines 108-279 (`_normalize`, `_exact_match`, `_substring_match`, `_yaml_lookup`, `_gemma_fallback`, `resolve_major`) | Only callers are the archived CLI and the tests below. `search_schools` (lines 37–105) is alive via `routers/schools.py` — keep. |
| `backend/app/models/career.py` | Lines 58-67 (`MajorMatch` class) | Only consumer is the deleted `school_lookup.resolve_major`. |
| `backend/app/models/api.py` | Lines 17-38 (`IntentRequest`, `IntentConfirmRequest`) `[CONDITIONAL — pending API spec verdict]` | Only used by the deleted `routers/intent.py`. |
| `backend/app/main.py` | Line 13 (`from app.routers import intent`) and the `application.include_router(intent.router, …)` line `[CONDITIONAL — pending API spec verdict]` | Drops with `routers/intent.py`. |
| `backend/pyproject.toml` | Line 27 (`"rich>=13.7"`) | No live consumer in `backend/app/`. |
| `backend/Dockerfile` | Line 32 (`rich` in the pip install list) | Drops with the pyproject entry. |
| `backend/uv.lock` (or equivalent lockfile) | Regenerate after `rich` removal | — |
| `CLAUDE.md` | Line 29 (`backend/cli.py # Interactive CLI harness (when built)` in the monorepo tree diagram) | File does not exist; CLI is archived. |
| `CLAUDE.md` | Line 92 (`The backend and CLI read these from data/futureproof.duckdb`) | Update to "The backend reads these from `data/futureproof.duckdb`." CLI is archived. |

### File Changes — Backend Tests (sections removed)

| File | Section | Justification |
|------|---------|---------------|
| `backend/tests/services/test_intent.py` | Entire file (1,200+ lines) `[CONDITIONAL — pending API spec verdict]` | All tests target `resolve_intent` / `confirm_intent`. The underscore helpers they indirectly cover are also tested via `set_your_course` integration tests — verify coverage is not lost (see §4 New Tests Required). |
| `backend/tests/services/test_school_lookup.py` | Lines 158-310 (`test_resolve_major_*` block) | Tests for the deleted `resolve_major`. The `search_schools` / `get_programs` test block above stays. |

### Out of Scope (Explicitly Keep Live)

The audit identified several files that LOOK like `/school` workflow but are still live via `SetYourCourseScreen.tsx:11-onwards`. **Do NOT touch:**

- `frontend/src/components/school/SchoolSearch.tsx` — used by `SetYourCourseScreen.tsx:363`
- `frontend/src/components/school/EffortLoansPanel.tsx` — used by `SetYourCourseScreen.tsx:719`
- `frontend/src/components/school/AskGemmaChip.tsx` — used by `SetYourCourseScreen`
- `frontend/src/components/school/CipPicker.tsx` — used by `SetYourCourseScreen`
- `frontend/src/components/school/CommunitySuggestions.tsx` — used by `SetYourCourseScreen`
- `frontend/src/components/school/CareerListSkeleton.tsx` — used by `SetYourCourseScreen`
- `frontend/src/components/school/SealedBuildContext.tsx` — used by `SetYourCourseScreen`
- `frontend/src/api/intent.ts` — `streamIntent`, `dispatchChip`, `commitResolution` are used by `useSetYourCourse.ts`
- `backend/app/routers/schools.py` and the `search_schools` / `get_programs` halves of `services/school_lookup.py` — `SetYourCourseScreen` calls `GET /schools/?q=` and `GET /schools/{unitid}/programs`
- `backend/app/services/major_lookup.py` — used indirectly by live `intent.py` underscore helpers
- All underscore helpers in `backend/app/services/intent.py` — used by `set_your_course.py`

### Data Model Changes
None.

### Service Changes
None — only deletions.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Risk | Reason |
|-----------|------|--------|
| `frontend/src/screens/SchoolMajorScreen.test.tsx` | High (deleted) | File is deleted with its target. |
| `frontend/src/components/school/MajorInput.test.tsx` | High (deleted) | File is deleted with its target. |
| `backend/tests/services/test_intent.py` | High (deleted, conditional) | File is deleted with `resolve_intent` / `confirm_intent` if API spec approves. |
| `backend/tests/services/test_school_lookup.py` | Medium (partial) | Lines 158-310 deleted; `search_schools` block stays. |
| `tests/scripts/test_yaml_regression.py` | High (deleted) | File is deleted with `scripts/yaml_regression.py`. |
| `frontend/src/screens/MenuScreen.test.tsx` | Low | Test name string fix on line 287 (assertion already correct). |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` (and other live-flow tests) | None — Confirmed Safe | These exercise the live flow. If any fail, deletion was wrong. |
| `backend/tests/services/test_set_your_course.py` | None — Confirmed Safe | Same. |
| `backend/tests/routers/test_*.py` for `/schools`, `/builds`, `/career-pick`, `/profile`, `/intent/stream`, `/intent/chip`, `/intent/commit` | None — Confirmed Safe | Live API surface. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/screens/SchoolMajorScreen.test.tsx` | Delete file | Target deleted. |
| `frontend/src/components/school/MajorInput.test.tsx` | Delete file | Target deleted. |
| `backend/tests/services/test_intent.py` | Delete file `[CONDITIONAL]` | Target deleted (if API spec approves). |
| `backend/tests/services/test_school_lookup.py` | Delete `test_resolve_major_*` block (lines 158-310) | Target deleted. |
| `tests/scripts/test_yaml_regression.py` | Delete file | Target deleted. |
| `frontend/src/screens/MenuScreen.test.tsx:287` | Update test name string from `…navigates to /school (P1)` → `…navigates to /profile (P1)` | Assertion already checks `/profile`. Pure name drift. |

#### Confirmed Safe (must still pass — if any fail, STOP)
- All `frontend/src/screens/SetYourCourseScreen.test.tsx` cases
- All `frontend/src/screens/CareerPickScreen.test.tsx` cases
- All `frontend/src/screens/BuildResultsScreen.test.*` cases
- All `frontend/src/screens/MenuScreen.test.tsx` cases (other than the line-287 name update)
- All `backend/tests/services/test_set_your_course.py` cases
- All `backend/tests/routers/` cases for live endpoints
- The non-`resolve_major` half of `backend/tests/services/test_school_lookup.py`

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_set_your_course.py` | (verify existing coverage) | Confirm the underscore helpers in `intent.py` (`_derive_intent_seed`, `_promote_to_leaf_cip`, `_get_school_cips`, `_get_crosswalk_cips_for_families`) have integration coverage via `set_your_course` tests. If any helper loses its only coverage when `test_intent.py` is deleted, add a focused unit test. |

#### Test Data Requirements
None new. `backend/tests/fixtures/intent_responses.json` may become orphaned — verify post-deletion and remove if so (log in §6).

---

## §5 Architecture Review

**Status:** SKIPPED (deletion-only refactor, no architectural change)

If the @faang-staff-engineer review in §8 surfaces an architectural concern, escalate via §10.

---

## §6 Implementation Log

**Status:** PENDING

### Files Deleted
| File | LOC | Verified Zero Importers |
|------|-----|------------------------|

### Sections Modified
| File | Section | LOC Removed |
|------|---------|-------------|

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

### Deviations from Spec
[Anything not in §4 — must be approved before deletion.]

---

## §7 Test Coverage

**Status:** PENDING

### Tests Removed
| Test File | Test Name | LOC Removed |
|-----------|-----------|-------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | | | | |
| pytest (pipeline) | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** PENDING

#### Verification Checklist (reviewer must confirm)
- [ ] No live import path is severed by any deletion
- [ ] No file in §4 "Out of Scope" was touched
- [ ] No test was silently disabled or marked `xfail`/`skip` instead of deleted
- [ ] `frontend/src/components/school/` directory still contains the live components listed in "Out of Scope"
- [ ] `backend/app/services/intent.py` still exports the underscore helpers used by `set_your_course.py`
- [ ] `backend/app/services/school_lookup.py` still exports `search_schools` and `get_programs`
- [ ] `backend/Dockerfile` builds (no missing `rich` reference left behind)
- [ ] CLAUDE.md no longer references `backend/cli.py`

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
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[2026-04-26] Spec author → API spec author
The CONDITIONAL items in §4 (legacy `/intent/` router, `IntentRequest`/`IntentConfirmRequest` models,
`_intent_cache` + `resolve_intent` + `confirm_intent` in services/intent.py, and `test_intent.py`)
are blocked on the verdict of `spike-analyze-orphan-api-endpoints.md`. If that spec recommends KEEPING
the legacy router, drop the CONDITIONAL items from this spec's scope and ship only the non-conditional
deletions. If it recommends REMOVING, proceed with the full §4.
```

---

## §11 Final Notes

**Human Review:** PENDING

Estimated LOC removed: ~1,500 (frontend) + ~800–1,300 (backend, depending on conditional items).

Follow-up candidates (NOT in this spec):
- Audit `backend/tests/fixtures/` for orphaned fixtures after this lands.
- Audit `scripts/` (54 entries) for one-shot scripts that have outlived their purpose. Separate spec.
- Audit `src/` (Brightsmith pipeline) for dead pipeline modules. Separate spec.
