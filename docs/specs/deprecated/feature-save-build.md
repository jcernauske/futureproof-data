# Feature: Auto-Save Session & Build Versioning

## Claude Code Prompt

```
Read the spec at docs/specs/feature-save-build.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (session persistence, build versioning, DuckDB schema, resume flow)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION (UI only — resume landing + inline slider rebuild)
   - Invoke @fp-design-visionary to propose the resume experience and inline slider rebuild UI
   - Visionary writes to §3 (UI/UX Design)
   - §3 becomes the pixel-perfect implementation target

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x)
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. DESIGN AUDIT
   - Invoke @design-builder for mechanical token/pattern compliance on resume UI
   - Writes findings to §8 (Design Audit section)
   - If CHANGES REQUIRED: route to implementer via §10 Discussion

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review
   - Generate report to reports/feature-save-build-YYYY-MM-DD.md
```

---

## Status: DEPRECATED 2026-05-03

> **Deprecated for the hackathon.** Auto-save and build versioning are nice-to-haves that don't appear in the demo path. Builds are already addressable by URL; that's enough for submission. If multi-build session management becomes a real user need post-hackathon, write fresh against actual usage signal.

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @design-builder checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-23 |
| Author | Jeff + Claude Code |
| Spec Version | 2.0 |
| Last Updated | 2026-05-03 (DEPRECATED — out of hackathon scope; URL-addressable builds are sufficient) |
| Blocked By | — |
| Related Specs | `feature-resolution-cache.md` (DEPRECATED) |

---

## §1 Feature Description

### Overview

Auto-save the student's entire journey — from character creation through boss fights — so they can close the browser and return exactly where they left off. Every screen transition and every in-screen action (skill applied, slider moved, fight resolved) saves automatically. No explicit "Save Build" button. For the hackathon, all users are treated as the same student (single active session).

When a student adjusts effort/loans sliders after completing a build, a new versioned build is created (linked to the original via `parent_build_id`) rather than mutating the original, enabling side-by-side comparison.

### Problem Statement

Today, all session state lives in Zustand stores with no persistence (except `hasSeenStatTutorial` in localStorage). If a student refreshes the browser or closes the tab mid-flow, everything is lost — character name, school selection, major resolution, build results, gauntlet progress, applied skills. The student must start over from scratch.

The only persistence path is an explicit "Save Build" button at `/save` that writes the completed Build to DuckDB. But by that point the student has already navigated the entire flow. If they leave after the 3rd boss fight with 2 skills applied and 2 remaining, that progress is gone.

Students need:
- Automatic persistence at every step — no save button required
- Resume exactly where they left off on return (same screen, same state)
- Partial gauntlet progress preserved (e.g., 3 fights done, 2 skills applied, 2 remaining in pool)
- Effort/loans adjustments that create new builds for comparison, not destroy the original

### Success Criteria

- [ ] New `student_sessions` DuckDB table stores the full session state as a singleton row
- [ ] `POST /session/checkpoint` accepts screen name + store snapshots, upserts the session
- [ ] `GET /session` returns the full session state (or 404 if no active session)
- [ ] `DELETE /session` clears the session (used by "Start Over")
- [ ] Frontend calls checkpoint after every screen transition (fire-and-forget, non-blocking)
- [ ] Frontend calls checkpoint after every in-screen action (skill apply, fight resolve, slider change)
- [ ] On app load, frontend calls `GET /session` — if exists, hydrates all stores and routes to `last_screen`
- [ ] If student is mid-gauntlet (e.g., fight 3 of 5), resume shows fight 3, not fight 1
- [ ] If student has applied 1 of 3 skills, the remaining 2 are still in the pool on resume
- [ ] Build object captures `home_state` and `animal_emoji` from the profile
- [ ] Adjusting effort/loans creates a new build version linked via `parent_build_id`
- [ ] New `POST /build/{build_id}/rebuild` endpoint creates versioned build with fresh Gemma narratives
- [ ] "Start Over" clears session and all stores, returns to landing

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Single-student session (singleton row) | Hackathon scope — no auth, no multi-user. One active session at a time. Post-hackathon can add profile IDs. | localStorage UUID, URL-based sessions |
| 2 | Server-side session in DuckDB, not localStorage | Survives incognito, device switches, and browser data clears. Single source of truth. Frontend stores are just hot copies. | localStorage only (fragile), IndexedDB (overkill) |
| 3 | Checkpoint = full store snapshot, not incremental deltas | Simple to implement, simple to resume. Each checkpoint is a complete picture — no delta replay needed. Cost is small (~5-20KB per checkpoint). | Incremental deltas (complex, error-prone reconstruction) |
| 4 | Fire-and-forget checkpoint saves | Saving must never block navigation or UI. If a checkpoint fails, the student doesn't notice — they just lose that one save point. | Blocking saves (stuttery UX), queued writes (complex) |
| 5 | Version builds on slider change (new build, not mutation) | Preserves original narratives and boss results; enables comparison. | Mutate in-place (loses original), deterministic rescore only (stale narratives) |
| 6 | Add `parent_build_id` to Build model | Lightweight lineage — links versions without a separate table. | Separate `build_versions` table (over-engineered) |
| 7 | Add `home_state` and `animal_emoji` to Build | Build should be self-contained — captures the full character. | Separate profile table (unnecessary for hackathon) |
| 8 | Gauntlet `selectedSkillIds` serialized as array | Zustand store uses `Set<string>` which can't be JSON-serialized. Convert to array on save, back to Set on hydrate. | Exclude from session (loses partial skill selection state) |

### Constraints

- DuckDB single-writer: all writes go through `_conn_lock` RLock (existing pattern)
- Checkpoint payloads are ~5-20KB JSON — well within DuckDB's VARCHAR capacity
- `gauntletStore.selectedSkillIds` is a `Set<string>` — must serialize as `string[]` and reconstruct on hydrate
- Session is a singleton: `session_id = 'current'` hardcoded for hackathon. Post-hackathon, replace with profile UUID.
- Build IDs are slug-based. Versioned builds get their own slug+counter — no special versioning in the ID scheme

---

## §3 UI/UX Design

> @fp-design-visionary fills this section. Skeleton below for context.

### Expected Screens/Components

**1. Resume Landing (on app load when session exists)**
- Student opens app → `GET /session` returns active session
- Brief "Welcome back" moment showing character name + emoji + where they left off
- "Continue" button → routes to `last_screen` with all stores hydrated
- "Start Over" button → `DELETE /session`, clear stores, go to landing

**2. Inline Slider Rebuild (on BuildResultsScreen)**
- "Adjust effort & loans" expands an inline panel (no navigation away)
- Student adjusts sliders → preview via existing `POST /build/{id}/rescore`
- "Lock in new build" → `POST /build/{id}/rebuild` creates versioned build
- New build loads with "Compare to original" chip

**3. Removal of explicit "Save Build" button**
- The `/save` screen's save action becomes unnecessary — build is always saved
- The wrapped/share flow at `/save` remains but doesn't need a "save" step first

### Interactions

[To be filled by @fp-design-visionary]

### Responsive Behavior

[To be filled by @fp-design-visionary]

### Brightpath Design References

[To be filled by @fp-design-visionary]

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Resume continue button | resume-continue | button | Continue where you left off |
| Resume start over button | resume-start-over | button | Start a new build from scratch |
| Rebuild confirm button | rebuild-confirm | button | Lock in new build with updated effort and loans |

---

## §4 Technical Specification

### Architecture Overview

Three new components, plus additions to existing models:

1. **`student_sessions` DuckDB table** — singleton row capturing the full session state
2. **Session service + router** — CRUD for the session (checkpoint, load, clear)
3. **Frontend hydration** — on app load, check for session and resume
4. **Build model additions** — `parent_build_id`, `home_state`, `animal_emoji`
5. **`/rebuild` endpoint** — creates versioned build on slider change

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (Zustand stores)                                │
│                                                          │
│  profileStore ──┐                                        │
│  buildInputStore ├─── checkpoint ──→ POST /session/checkpoint
│  buildStore ────┤      (fire &                           │
│  gauntletStore ──┘      forget)     ┌──────────────────┐ │
│                                     │ student_sessions │ │
│  On load: GET /session ←────────────│  (singleton row) │ │
│    → hydrate stores                 │  last_screen     │ │
│    → navigate(last_screen)          │  profile_data    │ │
│                                     │  build_input_data│ │
│                                     │  build_id        │ │
│                                     │  gauntlet_data   │ │
│                                     └──────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/sessions.py` | Create | Session CRUD: save_checkpoint, load_session, clear_session |
| `backend/app/routers/sessions.py` | Create | `GET /session`, `POST /session/checkpoint`, `DELETE /session` |
| `backend/app/models/api.py` | Modify | Add `CheckpointRequest`, `RebuildRequest`, `SessionResponse` models |
| `backend/app/models/career.py` | Modify | Add `parent_build_id`, `home_state`, `animal_emoji` to `Build`; add `parent_build_id`, `effort`, `loan_pct` to `BuildSummary` |
| `backend/app/services/builds.py` | Modify | Add `parent_build_id` column to schema; update `save_build`, `list_builds`, `build_from_parts` |
| `backend/app/routers/builds.py` | Modify | Wire `home_state`/`animal_emoji` into `create_build`; add `POST /{build_id}/rebuild`; call `sessions.save_checkpoint` after build creation |
| `backend/app/routers/gauntlet.py` | Modify | Call `sessions.save_checkpoint` after reroll/wrapup mutations |
| `backend/app/main.py` | Modify | Mount sessions router |
| `frontend/src/api/session.ts` | Create | `getSession()`, `saveCheckpoint()`, `clearSession()` API calls |
| `frontend/src/api/build.ts` | Modify | Add `rebuildWithSliders()` API call |
| `frontend/src/hooks/useSessionResume.ts` | Create | On-mount hook: calls `GET /session`, hydrates stores, returns `{resumeScreen, isLoading}` |
| `frontend/src/screens/LandingScreen.tsx` | Modify | Use `useSessionResume` — if session exists, show resume UI instead of normal landing |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Replace navigate-to-adjust with inline slider + rebuild flow; fire checkpoint after actions |
| `frontend/src/screens/ProfileScreen.tsx` | Modify | Fire checkpoint on "Let's go" |
| `frontend/src/screens/SchoolMajorScreen.tsx` | Modify | Fire checkpoint on school select, major confirm, slider confirm |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Fire checkpoint on CIP commit, career outcomes loaded |
| `frontend/src/screens/GauntletScreen.tsx` | Modify | Fire checkpoint after each fight resolve and skill apply |
| `frontend/src/store/buildStore.ts` | Modify | Add `hydrateFromSession()` method |
| `frontend/src/store/profileStore.ts` | Modify | Add `hydrateFromSession()` method |
| `frontend/src/store/buildInputStore.ts` | Modify | Add `hydrateFromSession()` method |
| `frontend/src/store/gauntletStore.ts` | Modify | Add `hydrateFromSession()` method; handle Set↔Array conversion |
| `frontend/src/types/build.ts` | Modify | Add `parent_build_id`, `home_state`, `animal_emoji` to `Build` type |
| `frontend/src/types/session.ts` | Create | `SessionResponse`, `CheckpointPayload` types |

### Data Model Changes

**New DuckDB table: `student_sessions`**

```sql
CREATE TABLE IF NOT EXISTS student_sessions (
    session_id VARCHAR PRIMARY KEY,       -- 'current' (singleton for hackathon)
    last_screen VARCHAR NOT NULL,         -- route path: '/profile', '/school', '/set-your-course', etc.
    profile_data VARCHAR,                 -- JSON: { profileName, animalEmoji, animalName, homeState }
    build_input_data VARCHAR,             -- JSON: { school, programs, major, effort, loans, phase, initialResolution, currentResolution }
    build_id VARCHAR,                     -- FK to builds.build_id (null until build created)
    gauntlet_data VARCHAR,                -- JSON: { phase, currentFightIndex, fightPhase, selectedSkillIds: string[] }
    tiered_careers_data VARCHAR,          -- JSON: TieredCareers (cached between career pick and build)
    selected_career_data VARCHAR,         -- JSON: CareerOutcome (the chosen SOC)
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
)
```

**Build model additions** (`backend/app/models/career.py`):

```python
class Build(BaseModel):
    # ... existing fields ...
    parent_build_id: str | None = None
    home_state: str | None = None
    animal_emoji: str | None = None
```

**BuildSummary additions** (`backend/app/models/career.py`):

```python
class BuildSummary(BaseModel):
    # ... existing fields ...
    parent_build_id: str | None = None
    effort: str = "balanced"
    loan_pct: float = 1.0
```

**New request/response models** (`backend/app/models/api.py`):

```python
class CheckpointRequest(BaseModel):
    screen: str                                    # route path: '/profile', '/school', etc.
    profile_data: dict | None = None               # profileStore snapshot
    build_input_data: dict | None = None           # buildInputStore snapshot
    build_id: str | None = None                    # current build ID (once created)
    gauntlet_data: dict | None = None              # gauntletStore snapshot
    tiered_careers_data: dict | None = None         # tiered careers (pre-build)
    selected_career_data: dict | None = None        # selected CareerOutcome

class SessionResponse(BaseModel):
    session_id: str
    last_screen: str
    profile_data: dict | None = None
    build_input_data: dict | None = None
    build_id: str | None = None
    build: dict | None = None                      # full Build object if build_id exists
    gauntlet_data: dict | None = None
    tiered_careers_data: dict | None = None
    selected_career_data: dict | None = None
    created_at: str
    updated_at: str

class RebuildRequest(BaseModel):
    effort: str = "balanced"
    loan_pct: float = 1.0
```

**BuildRequest additions** (`backend/app/models/api.py`):

```python
class BuildRequest(BaseModel):
    # ... existing fields ...
    home_state: str | None = None
    animal_emoji: str | None = None
```

**DuckDB schema migration** (`backend/app/services/builds.py`):

```python
def _init_schema(connection: duckdb.DuckDBPyConnection) -> None:
    # Existing builds table — add parent_build_id column
    connection.execute("""
        CREATE TABLE IF NOT EXISTS builds (
            build_id VARCHAR PRIMARY KEY,
            profile_name VARCHAR,
            created_at VARCHAR,
            school_name VARCHAR,
            major_text VARCHAR,
            career_title VARCHAR,
            ern INTEGER, roi INTEGER, res INTEGER, grw INTEGER, hmn INTEGER,
            wins INTEGER, losses INTEGER, draws INTEGER,
            parent_build_id VARCHAR,
            data VARCHAR
        )
    """)
    _add_column_if_missing(connection, "builds", "parent_build_id", "VARCHAR")
    # ... existing wrapped_frames unchanged ...
```

`home_state` and `animal_emoji` live inside the `data` JSON blob. Only `parent_build_id` needs a dedicated column for query filtering.

### Service Changes

**`backend/app/services/sessions.py`** (NEW):

```python
def save_checkpoint(request: CheckpointRequest) -> None:
    """Upsert the singleton session row with current state."""

def load_session() -> SessionResponse | None:
    """Load the active session. Returns None if no session exists."""

def clear_session() -> None:
    """Delete the active session (Start Over)."""
```

Uses the same DuckDB connection pattern as `builds.py` — shared `_conn()` via the same `backend/data/futureproof.duckdb` file. Schema initialized in its own `_init_session_schema()` called from `_conn()`.

**`backend/app/services/builds.py`** (MODIFIED):

- `save_build()` — include `parent_build_id` in INSERT
- `list_builds()` — include `parent_build_id` in SELECT; read `effort`/`loan_pct` from `data` JSON
- `build_from_parts()` — accept `parent_build_id` parameter
- `_add_column_if_missing()` — new helper for safe schema migration

**`backend/app/routers/builds.py`** (MODIFIED):

New endpoint `POST /build/{build_id}/rebuild`:

```python
@router.post("/{build_id}/rebuild")
async def rebuild_with_sliders(build_id: str, request: RebuildRequest):
    """Create a new build version with different effort/loans.
    
    Copies school/major/career selection from the original build,
    recomputes stats with new sliders, runs fresh gauntlet + Gemma
    narratives, persists as a new build linked via parent_build_id.
    """
    original = state.get_build(build_id)
    if original is None:
        raise HTTPException(status_code=404)

    career = stat_engine.recompute_for_sliders(
        career=original.career,
        original_effort=original.effort,
        new_effort=request.effort,
        new_loan_pct=request.loan_pct,
    )
    gauntlet = boss_fights.score_gauntlet(career)
    branches = original.branches  # reuse — branches don't depend on sliders

    # Fan out 8 Gemma calls (same pattern as create_build)
    # ... narratives, skill_recs, skill_pool, guidance ...

    build = builds.build_from_parts(
        school_name=original.school_name,
        unitid=original.unitid,
        major_text=original.major_text,
        cipcode=original.cipcode,
        program_name=original.program_name,
        effort=request.effort,
        loan_pct=request.loan_pct,
        career=career,
        gauntlet=gauntlet,
        branches=branches,
        skill_recs=recs,
        guidance=narrative,
        skill_pool=pool,
        profile_name=original.profile_name,
        parent_build_id=original.build_id,
    )
    build.home_state = original.home_state
    build.animal_emoji = original.animal_emoji

    state.store_build(build)
    builds.save_build(build)
    return build
```

### Frontend Session Integration

**Checkpoint trigger pattern** (used in every screen):

```typescript
import { saveCheckpoint } from "../api/session";
import { useProfileStore } from "../store/profileStore";
import { useBuildInputStore } from "../store/buildInputStore";
import { useBuildStore } from "../store/buildStore";
import { useGauntletStore } from "../store/gauntletStore";

function fireCheckpoint(screen: string) {
  const profile = useProfileStore.getState();
  const buildInput = useBuildInputStore.getState();
  const buildStore = useBuildStore.getState();
  const gauntlet = useGauntletStore.getState();

  saveCheckpoint({
    screen,
    profile_data: {
      profileName: profile.profileName,
      animalEmoji: profile.animalEmoji,
      animalName: profile.animalName,
      homeState: profile.homeState,
    },
    build_input_data: {
      phase: buildInput.phase,
      school: buildInput.school,
      programs: buildInput.programs,
      major: buildInput.major,
      effort: buildInput.effort,
      loans: buildInput.loans,
      initialResolution: buildInput.initialResolution,
      currentResolution: buildInput.currentResolution,
    },
    build_id: buildStore.build?.build_id ?? null,
    gauntlet_data: {
      phase: gauntlet.phase,
      currentFightIndex: gauntlet.currentFightIndex,
      fightPhase: gauntlet.fightPhase,
      selectedSkillIds: Array.from(gauntlet.selectedSkillIds),  // Set → Array
    },
    tiered_careers_data: buildStore.tieredCareers ?? null,
    selected_career_data: buildStore.selectedCareer ?? null,
  }).catch(console.warn);  // fire-and-forget
}
```

**Checkpoint save points by screen:**

| Screen | Trigger(s) | What changes in session |
|--------|-----------|------------------------|
| ProfileScreen | "Let's go" clicked | `profile_data`, `last_screen: '/school'` |
| SchoolMajorScreen | School selected | `build_input_data.school` |
| SchoolMajorScreen | Major confirmed | `build_input_data.major` |
| SchoolMajorScreen | "Let's go" (sliders done) | `build_input_data.effort/loans`, `last_screen: '/set-your-course'` |
| SetYourCourseScreen | CIP committed | `build_input_data.resolution` |
| SetYourCourseScreen | Career outcomes loaded | `tiered_careers_data` |
| SetYourCourseScreen | Career selected | `selected_career_data`, `last_screen: '/my-build'` |
| SetYourCourseScreen | "Spec my build" clicked | `build_id` (build now exists), `last_screen: '/my-build'` |
| BuildResultsScreen | Page loads with build | `last_screen: '/my-build'` |
| GauntletScreen | Each fight resolved | `gauntlet_data.currentFightIndex`, fight results in build |
| GauntletScreen | Skill applied (reroll) | `gauntlet_data`, build updated with skill |
| GauntletScreen | Gauntlet complete | `gauntlet_data.phase: 'complete'` |
| BuildResultsScreen | Slider rebuild confirmed | `build_id` (new versioned build) |

**Hydration hook** (`frontend/src/hooks/useSessionResume.ts`):

```typescript
function useSessionResume(): { resumeScreen: string | null; isLoading: boolean } {
  // On mount: GET /session
  // If 200: hydrate all stores from response, return { resumeScreen: last_screen }
  // If 404: return { resumeScreen: null } (fresh start)
  // Hydration includes:
  //   profileStore.setProfile(...)
  //   buildInputStore.setSchool(...), setMajor(...), etc.
  //   buildStore.setBuild(...) (if build_id exists, load from response.build)
  //   gauntletStore: set phase, fightIndex, convert selectedSkillIds array → Set
}
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/routers/test_builds_collection.py` | `test_returns_all_builds_*` | Med | `BuildSummary` gains new fields; assertions on response shape may need updating |
| `backend/tests/routers/test_builds_collection.py` | `_make_build` helper | Med | Uses `build_from_parts` which gains `parent_build_id` parameter |
| `backend/tests/routers/conftest.py` | `isolated_builds_db` | Low | New tables added to schema init — fixture creates fresh DB, so they appear automatically |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/routers/test_builds_collection.py` / `_make_build` | Pass `parent_build_id=None` | New parameter on `build_from_parts` |
| `backend/tests/routers/test_builds_collection.py` | Update `BuildSummary` assertions to include new fields | Model shape changed |

#### Confirmed Safe

- `backend/tests/services/test_stat_engine.py` — stat computation logic unchanged
- `backend/tests/services/test_builds_wrapped.py` — wrapped frame logic unchanged
- `backend/tests/routers/test_wrapped_router.py` — wrapped endpoints unchanged
- `backend/tests/routers/test_set_your_course_router.py` — intent flow unchanged
- `backend/tests/routers/test_career_pick_router.py` — career pick endpoints unchanged
- All pipeline tests in `tests/` — pipeline is not touched

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_sessions.py` | `test_save_and_load_checkpoint` | Round-trip: save checkpoint with all store data, load it back, verify all fields |
| P0 | `backend/tests/services/test_sessions.py` | `test_checkpoint_upserts_not_duplicates` | Second checkpoint overwrites first (singleton behavior) |
| P0 | `backend/tests/services/test_sessions.py` | `test_clear_session` | `clear_session()` removes the row; subsequent `load_session()` returns None |
| P0 | `backend/tests/routers/test_sessions_router.py` | `test_get_session_404_when_empty` | `GET /session` returns 404 with no active session |
| P0 | `backend/tests/routers/test_sessions_router.py` | `test_checkpoint_then_get_session` | POST checkpoint → GET session returns matching data |
| P0 | `backend/tests/services/test_builds.py` | `test_save_load_build_with_parent_id` | `parent_build_id` survives save/load round-trip |
| P0 | `backend/tests/services/test_builds.py` | `test_save_load_build_with_home_state` | `home_state` and `animal_emoji` survive via JSON blob |
| P1 | `backend/tests/routers/test_builds_router.py` | `test_rebuild_creates_new_build` | `POST /rebuild` returns new build with `parent_build_id` pointing to original |
| P1 | `backend/tests/routers/test_builds_router.py` | `test_rebuild_preserves_school_major` | Rebuilt build has same school/major/CIP as original |
| P1 | `backend/tests/routers/test_builds_router.py` | `test_rebuild_applies_new_effort` | Rebuilt build's effort/loan_pct match request |
| P1 | `backend/tests/services/test_sessions.py` | `test_load_session_includes_build` | When `build_id` is set, `load_session` response includes full Build object |
| P1 | `backend/tests/services/test_builds.py` | `test_list_builds_includes_parent_build_id` | `list_builds` returns `parent_build_id` in summaries |
| P1 | `backend/tests/services/test_builds.py` | `test_schema_migration_idempotent` | `_add_column_if_missing` safe on fresh and existing DBs |
| P2 | `backend/tests/routers/test_sessions_router.py` | `test_delete_session` | `DELETE /session` clears and subsequent GET returns 404 |
| P2 | `backend/tests/routers/test_builds_router.py` | `test_rebuild_404_on_missing` | `POST /rebuild` on nonexistent build returns 404 |

#### Test Data Requirements

- Existing `_make_build` helper in `test_builds_collection.py` can be reused/extended
- `isolated_builds_db` fixture handles DB isolation — extend to also clear sessions table
- Gemma calls in `/rebuild` should be mocked (same pattern as existing build tests)
- Session tests need a fixture that provides an isolated DuckDB with the sessions table

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-23

#### System Context

This feature adds a server-side session persistence layer between the existing Zustand stores (frontend) and the existing DuckDB builds database (backend). It touches three layers: a new `student_sessions` DuckDB table for checkpoint storage, new session service + router for CRUD, and frontend hydration logic. It also extends the Build model with lineage tracking (`parent_build_id`) and character fields (`home_state`, `animal_emoji`), and adds a `/rebuild` endpoint that creates versioned builds. The feature does not touch the Brightsmith pipeline, Gold zone, or MCP tools -- it is purely application-layer persistence.

#### Data Flow Analysis

**Checkpoint flow:** Frontend Zustand stores -> `POST /session/checkpoint` -> `sessions.save_checkpoint()` -> DuckDB `student_sessions` table (singleton upsert). Fire-and-forget, non-blocking. Clean and simple.

**Resume flow:** App load -> `GET /session` -> `sessions.load_session()` -> DuckDB read -> if `build_id` exists, also `builds.load_build(build_id)` to inflate the full Build -> return `SessionResponse` with embedded Build -> frontend hydrates all stores -> navigate to `last_screen`. This flow crosses two tables (sessions + builds) but the join is application-level, not a SQL join, which is the right call for DuckDB's single-writer model.

**Rebuild flow:** `POST /build/{build_id}/rebuild` -> load original from `app.state` -> `stat_engine.recompute_for_sliders()` -> `boss_fights.score_gauntlet()` -> fan out Gemma calls -> `builds.build_from_parts(parent_build_id=original.build_id)` -> persist. This mirrors the `create_build` flow closely, which is correct.

**Boundary crossings are well-defined:** Frontend sends typed JSON payloads, backend validates via Pydantic, persists to DuckDB. The Build model's JSON blob strategy (storing `home_state`/`animal_emoji` inside the `data` VARCHAR) is consistent with the existing pattern where `save_build` writes `model_dump_json()` and `load_build` reconstructs via `model_validate_json()`. Only `parent_build_id` gets a dedicated column for query filtering -- sound decision.

#### Contract Review

**CheckpointRequest:** The `dict | None` typing for `profile_data`, `build_input_data`, `gauntlet_data`, `tiered_careers_data`, and `selected_career_data` is too loose. These are unvalidated dicts that get serialized to JSON and stored. On the resume path, they get returned as-is and the frontend trusts them. This is acceptable for hackathon scope since the frontend is both producer and consumer, but it means a malformed checkpoint silently corrupts the session. See Concern #1.

**SessionResponse:** Includes a `build: dict | None` field for the inflated Build. Using `dict` here rather than `Build` means the response shape is uncontracted on the Build portion. Since `Build.model_dump(mode="json")` produces the dict, this works in practice, but it would be cleaner as `Build | None` and let FastAPI serialize it. See Concern #2.

**RebuildRequest:** Clean. `effort: str` and `loan_pct: float` match the existing `RescoreRequest` pattern.

**Build model additions:** `parent_build_id: str | None`, `home_state: str | None`, `animal_emoji: str | None` -- all optional with None defaults, backward compatible. Clean.

**BuildSummary additions:** `parent_build_id: str | None`, `effort: str`, `loan_pct: float` -- these require changes to `list_builds()` to extract `effort`/`loan_pct` from the JSON `data` blob. The spec mentions this but does not show the DuckDB query. DuckDB supports `json_extract_string()` which can pull these from the VARCHAR blob, so this is feasible.

#### Findings

##### Sound

1. **Singleton session design.** `session_id = 'current'` as a hardcoded primary key is exactly right for hackathon scope. The upgrade path to per-student UUIDs is obvious and the spec calls it out.

2. **Full-snapshot checkpoints over incremental deltas.** At 5-20KB per checkpoint, the simplicity wins. No delta replay logic, no ordering bugs, no partial state.

3. **Fire-and-forget checkpoint saves.** Non-blocking saves that fail silently are the correct tradeoff. A missed checkpoint means the student loses one save point, not their entire session.

4. **parent_build_id as a Build field, not a separate table.** Lightweight lineage without over-engineering. The slug-based ID system means versioned builds get their own unique IDs naturally.

5. **Reuse of existing DuckDB connection pattern.** The spec correctly identifies that `sessions.py` should follow the same `_conn()` / `_conn_lock` / `_execute` pattern as `builds.py`. Same DB file, same locking model.

6. **home_state and animal_emoji inside the JSON blob.** Consistent with how every other Build field is persisted. Only `parent_build_id` needs a column because it is queried directly.

7. **Set-to-Array serialization for selectedSkillIds.** Correctly identified as a serialization hazard and handled explicitly.

8. **Testing impact analysis.** Thorough. The authorized test modifications are precise and the "confirmed safe" list is accurate -- those modules are genuinely untouched.

##### Concerns

- **Concern #1 -- Untyped session data blobs.** `CheckpointRequest` uses `dict | None` for five fields that carry structured data (profile, build input, gauntlet, tiered careers, selected career). If the frontend sends a malformed payload (missing key, wrong type), the backend stores it without validation. On resume, the frontend gets back garbage and hydration fails silently. **Impact:** A single bad checkpoint poisons the session; the student sees a broken resume screen with no indication of what went wrong. **Recommendation:** Define lightweight Pydantic models for at least `profile_data` and `gauntlet_data` (the two most structurally critical). `tiered_careers_data` and `selected_career_data` can stay as `dict` since they are opaque pass-throughs that the frontend already knows how to parse. At minimum, add a `try/except` in `load_session` that catches JSON decode failures and returns 404 (treating a corrupt session as "no session") rather than a 500.

- **Concern #2 -- SessionResponse.build typed as dict.** The `build: dict | None` field means FastAPI will not validate or document the Build shape in the OpenAPI schema. Since `load_build()` returns a `Build` Pydantic model, this should be `build: Build | None` so the response contract is explicit and the auto-generated docs are accurate. **Impact:** Weak contract at the API boundary; frontend developers cannot trust the OpenAPI spec for the Build portion of the session response. **Recommendation:** Change `build: dict | None` to `build: Build | None` in `SessionResponse`.

- **Concern #3 -- DuckDB connection sharing between two modules.** Both `sessions.py` and `builds.py` will independently call `duckdb.connect()` on the same file path, each maintaining their own connection cache and lock. DuckDB allows only one write connection at a time per database file. If both modules open separate connections, writes from one module will block or fail when the other holds a write lock. **Impact:** Under concurrent requests (checkpoint fires while a build is being saved), one write will fail with a DuckDB locking error. The fire-and-forget pattern masks this on the checkpoint path, but a failed `save_build` inside `/rebuild` would surface as a 500. **Recommendation:** Either (a) have `sessions.py` import and reuse `builds._conn()` and `builds._conn_lock` (exposing them as module-level helpers), or (b) extract a shared `db.py` module that owns the single connection + lock for `backend/data/futureproof.duckdb`. Option (b) is cleaner and prevents the import direction from creating a coupling between the two service modules.

- **Concern #4 -- Rebuild endpoint duplicates create_build's Gemma fan-out.** The spec shows the `/rebuild` endpoint repeating the 8-way `asyncio.gather` pattern from `create_build` (narratives + skill_recs + skill_pool + guidance). This is ~80 lines of error-handling boilerplate that will drift between the two endpoints over time. **Impact:** Future changes to the Gemma fan-out (new roles, changed fallbacks, timeout handling) must be applied in two places. **Recommendation:** Extract the Gemma fan-out into a shared helper (e.g., `services/gemma_fanout.py` or a private function in `builds.py`) that both `create_build` and `rebuild_with_sliders` call. This is not a blocker -- the duplication works -- but it is a maintenance hazard worth addressing during implementation.

- **Concern #5 -- Checkpoint-after-gauntlet-mutation timing.** The spec says gauntlet.py should "call `sessions.save_checkpoint` after reroll/wrapup mutations." But gauntlet mutations (`/reroll`, `/wrapup`) are backend-initiated state changes on the in-memory Build. The session checkpoint is a frontend-initiated concept (the frontend snapshots its stores). Having the backend call `save_checkpoint` directly means the backend must construct a `CheckpointRequest` from server-side state, which it does not have full visibility into (it does not know `last_screen`, `profile_data`, `build_input_data`, etc.). **Impact:** Backend-initiated checkpoints would save partial/stale session state (only `build_id` and `gauntlet_data` would be current; other fields would be missing or stale from the last frontend checkpoint). **Recommendation:** Keep checkpoints frontend-only. The frontend already fires checkpoints after each fight resolve and skill apply (per the checkpoint trigger table in the spec). Remove the requirement for gauntlet.py to call `save_checkpoint` -- it is redundant with the frontend triggers and architecturally misplaced.

- **Concern #6 -- Missing `hasSeenStatTutorial` in session.** The spec identifies that `hasSeenStatTutorial` is currently in localStorage, but the session checkpoint does not capture it. If a student resumes on a new device or after clearing browser data, they will see the stat tutorial again even though they already completed it. **Impact:** Minor UX annoyance, not a data integrity issue. **Recommendation:** Either add `hasSeenStatTutorial` to the checkpoint payload (inside `build_input_data` or as a top-level boolean), or accept this as a known limitation. Not a blocker.

##### Blockers

None. The architecture is fundamentally sound.

#### Verdict
- [x] CHANGES REQUESTED

#### Conditions

1. **Resolve DuckDB connection sharing (Concern #3).** Extract a shared `db.py` module (or equivalent) so `sessions.py` and `builds.py` share a single DuckDB connection and lock. Two independent connections to the same file will cause write contention under concurrent requests.

2. **Remove backend-initiated checkpoint calls from gauntlet.py (Concern #5).** Checkpoints should be frontend-only. The backend does not have the full store snapshot needed to construct a valid `CheckpointRequest`. The frontend already covers these save points.

3. **Type SessionResponse.build as `Build | None` (Concern #2).** The response contract at the API boundary should be explicit. This is a one-line change that strengthens the contract and the OpenAPI docs.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline/data changes — application-layer persistence only)

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §3/§4 and why]

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
| pytest | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** PENDING
[Filled in by @design-builder — Brightpath token compliance for resume UI]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer]
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
[Reserved for agent-to-agent communication during execution]
```

---

## §11 Final Notes

**Human Review:** PENDING

**Post-hackathon upgrades:**
- Replace singleton `session_id = 'current'` with per-student UUIDs
- Add `feature-resolution-cache.md` for Gemma response caching
- Consider localStorage mirroring for offline-first resilience
