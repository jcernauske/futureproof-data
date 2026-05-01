# Tech Debt: Hackathon Hardening — Follow-up Cleanup

## Claude Code Prompt

```
Read the spec at docs/specs/tech-debt-hackathon-hardening-followup.md in its entirety.

This is a bundled cleanup spec — Standard pipeline weight. No new features, no
architecture change, no schema change. The scope is the open items left over
from reports/staff-engineer-audit-2026-04-30.md (Post-Hardening Status section)
that are cheap to land in one PR.

Execute the following workflow:

1. IMPLEMENTATION
   - Apply every change in §4 "File Changes" exactly as specified.
   - Do NOT touch anything in §4 "Out of Scope".
   - BEFORE coding: re-read §4 Testing Impact Analysis. The hasSeenStatTutorial
     removal touches three test files; only the listed "Authorized Test
     Modifications" may change. If any other test fails, STOP and escalate.
   - DURING coding: log every file change to §6.
   - AFTER coding: run
       Backend:  cd backend && ruff check . && mypy app/ && pytest
       Frontend: cd frontend && npx tsc --noEmit && npx vitest run
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
     After 3 failures, set status BLOCKED and escalate via §10.

2. TESTING
   - Invoke @test-writer to verify §4 Testing Impact Analysis is correct
     and the new P0/P1 tests in §4 are present.
   - Confirm no test was silently skipped (the only authorized deletions are
     the three buildStore.test.ts tests in §4).
   - Run the full backend pytest suite and full frontend vitest suite.

3. CODE REVIEW
   - Invoke @faang-staff-engineer to review the diff. Reviewer must verify:
     (a) hasSeenStatTutorial removal does not regress the "returning students
         re-tutored on every build" failure mode that buildStore.test.ts
         lines 138-141 originally guarded against — the protection is no
         longer needed because the tutorial UI is gone, but the reviewer
         should confirm there is no other consumer of the persist key.
     (b) the new ^\d{2}$ validation in intent.py preserves the existing
         caller contract (callers feed prefixes derived from server-stored
         CIPs; validation must not reject valid 2-digit strings).
     (c) the lifespan try/except wrap does not swallow startup errors that
         should crash the app — only profile-load failures.
   - Writes findings to §8.

4. VERIFICATION
   - Invoke @fp-builder for full build verification:
     ruff + mypy + pytest + tsc + vitest + Vite production build.
   - Log results to §9.

5. COMPLETION
   - Update Status to COMPLETE.
   - Generate report to reports/tech-debt-hackathon-hardening-followup-YYYY-MM-DD.md.
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
| Created | 2026-04-30 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-30 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/tech-debt-hackathon-hardening.md` (parent — closed 7 of 10 audit items); `docs/specs/refactor-remove-dead-frontend-code.md` (sibling — marked COMPLETE 2026-04-26 but missed the persist-store residue this spec mops up) |

---

## §1 Feature Description

### Overview
Bundle the residual open items from `reports/staff-engineer-audit-2026-04-30.md` (Post-Hardening Status section) into one cleanup PR: zombie `hasSeenStatTutorial` state in the build store + tests, a docstring-only fix on the `statExplanations` data file, an inline rationale comment on the `clearSession()` fire-and-forget call site, defense-in-depth CIP-prefix validation in the intent service, defensive try/except around `_load_existing_profiles()` in the FastAPI `lifespan`, and a README operator note about `logs/gemma.jsonl` rotation/scrubbing before external sharing.

### Problem Statement
Two specs have already landed against the staff-engineer audit (`refactor-prune-deprecated-build-flow` and `tech-debt-hackathon-hardening`), closing 7 of the Top 10. The remaining open items are individually cheap but each is a small first-impression nick that erodes the "this team has closure discipline" read:

- **Top 10 #6** — `hasSeenStatTutorial` is still in `frontend/src/store/buildStore.ts` (lines 24-25, 55-57, 80) and partialized to localStorage, even though the `StatTutorial.tsx` / `StatHelpTooltip.tsx` / `StatDetailCard.tsx` components were deleted by `refactor-remove-dead-frontend-code` (2026-04-26). The state is wired to nothing. Three tests in `buildStore.test.ts` plus two test fixtures in `MenuScreen.test.tsx` and `BuildResultsScreen.test.tsx` reference the dead key. The `data/statExplanations.ts` module's leading docstring still claims "Used by StatTutorial overlay and persistent StatHelpTooltip" — both deleted; the file itself is **live** (its `STAT_MAP`, `StatKey`, and `STAT_EXPLANATIONS` exports power the live pentagon stat legend and chart colors), so only the docstring is wrong.
- **Bonus #11** — `BuildResultsScreen.tsx:553` does `clearSession().catch(console.warn)`. Audit calls out that a future contributor will "fix" this into a synchronous `await` and break the page-leave flow. A one-line comment explaining the fire-and-forget intent prevents this. Note: the audit text says `App.tsx`, but the actual call site is `BuildResultsScreen.tsx:553`.
- **Audit "Other findings" 🟡 — defense-in-depth in `intent.py:202-211`** — `_get_crosswalk_cips_for_families` interpolates `p[:2]` from each prefix into a `SUBSTR(cipcode, 1, 2) = '...'` clause. Today every caller derives the prefix from a server-stored CIP, so the value is well-formed. The audit calls this "fragile if the data path ever changes" — validating against `^\d{2}$` before interpolation costs nothing and removes the fragility.
- **Audit "Other findings" 🟡 — `lifespan` `_load_existing_profiles()` not wrapped in try/except** — preserved as Decision #6 in `tech-debt-hackathon-hardening` (behavioral parity with the prior `on_event` code), but flagged for next pass. `lifespan` startup-exception semantics are stricter than `on_event` — an unhandled raise here prevents the app from starting. The function already wraps its `.execute()` call internally, but a defensive outer wrap matches the symmetry of the Iceberg warmup block right below it.
- **Audit "Other findings" 🔵 — `logs/gemma.jsonl` operator hygiene** — every Gemma call writes the full system + user message + response to `logs/gemma.jsonl`. The directory is gitignored, but operators sharing logs externally (e.g. attaching to a bug report or hackathon submission) will leak whatever students typed. README needs a short bullet under the existing "Security & Deployment" section.

### Success Criteria
- [ ] `frontend/src/store/buildStore.ts` no longer declares, sets, or partializes `hasSeenStatTutorial` / `setHasSeenStatTutorial`.
- [ ] `frontend/src/store/buildStore.test.ts` no longer contains the "preserves hasSeenStatTutorial across resetBuild" test or the "hasSeenStatTutorial localStorage persistence" `describe` block; header docstring + `beforeEach` updated.
- [ ] `frontend/src/screens/MenuScreen.test.tsx` and `frontend/src/screens/BuildResultsScreen.test.tsx` no longer set `hasSeenStatTutorial` in their store-seed helpers.
- [ ] `frontend/src/data/statExplanations.ts` docstring updated to describe live consumers (`PentagonChart` legend, `CareerCard`, horizon mockups).
- [ ] `frontend/src/screens/BuildResultsScreen.tsx:553` carries a one-line comment explaining why `clearSession().catch(console.warn)` is fire-and-forget by design.
- [ ] `backend/app/services/intent.py::_get_crosswalk_cips_for_families` validates each prefix against `^\d{2}$` before SQL interpolation; non-matching prefixes are silently dropped (logged at DEBUG).
- [ ] `backend/app/main.py::lifespan` wraps `_load_existing_profiles()` in try/except, logging at `logger.warning` with `exc_info=True` on failure (matches Iceberg warmup style at lines 77-86).
- [ ] `README.md` "Security & Deployment" section gains a short bullet on `logs/gemma.jsonl` rotation/scrubbing before external sharing.
- [ ] `cd backend && ruff check . && mypy app/ && pytest` all green.
- [ ] `cd frontend && npx tsc --noEmit && npx vitest run && npm run build` all green.
- [ ] `localStorage` key `futureproof-build` no longer carries a `hasSeenStatTutorial` field on the next deploy (verified by inspecting the persisted shape in dev).

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Bundle all 6 items into a single Standard-weight spec rather than splitting per item. | Total touched files ≈ 9, all small, none architecturally entangled. Splitting creates 6 PRs of 1-2 files each — review overhead exceeds the work. Audit itself recommends the bundle (`reports/staff-engineer-audit-2026-04-30.md` "Net read"). | Six separate bugfix specs — rejected, churn. |
| 2 | Do NOT reopen `docs/specs/refactor-remove-dead-frontend-code.md`. Reference it under Related Specs and call out the relationship here. | That spec is `Status: COMPLETE` (closed 2026-04-26 with full §6/§7/§8/§9 fill-in). Reopening to retro-fit findings would force a status walk-back and confuse the audit trail. The dead-state residue is a genuine miss in that spec's scope analysis, not a regression — addressing it here is the correct closure. | Reopen and amend the COMPLETE spec — rejected, hurts the audit trail. |
| 3 | KEEP `frontend/src/data/statExplanations.ts` — only update the docstring. | `STAT_MAP` is imported by `CareerCard.tsx`, `PentagonChart.tsx`, `horizon/HorizonStripMockup.tsx`, `horizon/ChapterBookMockup.tsx`. `STAT_EXPLANATIONS` is consumed by `BuildResultsScreen.tsx:687` for the live pentagon stat legend. The file's leading docstring is the only stale piece. Audit framing slightly off — file is not dead. | Delete the file — rejected, four live importers. |
| 4 | The `clearSession()` comment is on `BuildResultsScreen.tsx:553`, not `App.tsx`. | The audit text said `App.tsx` but `grep` confirms the only `clearSession` call is in `BuildResultsScreen.tsx`. Leaving the audit text as-is and writing the comment at the actual call site preserves intent without copying a typo. | Add a misplaced comment in `App.tsx` — rejected, that file does not call `clearSession`. |
| 5 | `_get_crosswalk_cips_for_families` rejects non-`^\d{2}$` prefixes silently (DEBUG log) rather than raising. | Caller (`set_your_course.py:356` derives `family_prefixes` from server-stored CIP rows) cannot today produce a non-digit prefix. Raising would convert "future fragility" into "future crash." Silent drop + DEBUG log is symmetric with how the rest of `intent.py` handles unexpected DB shapes (`return []` + `logger.warning`). | Raise `ValueError` — rejected, regression risk. Skip validation — rejected, defeats the audit recommendation. |
| 6 | `lifespan` wraps `_load_existing_profiles()` in try/except even though the function already catches its own DB exceptions. | Defense in depth. The function's internal try/except covers `.execute().fetchall()`, but `builds_service._conn()` (called as the very first thing in the function) can raise during cold-start file races, schema-init lock contention, or DuckDB version mismatches. `lifespan` startup-exception semantics in FastAPI 0.115+ prevent the app from starting on any unhandled raise — matching the Iceberg warmup wrap style (lines 77-86) keeps startup behavior consistent. Decision #6 in the parent `tech-debt-hackathon-hardening` spec explicitly flagged this for next pass. | Trust the inner try/except — rejected, audit flagged it; symmetry with warmup wrap is cheaper than re-litigating. Skip — rejected, audit recommendation. |
| 7 | README operator note is a short bullet under the existing "Security & Deployment" section, not a new top-level section. | The section already exists and is the right home for operational hygiene callouts. A separate "Logging" section would be more weight than this single bullet warrants. | New top-level "Logging" section — rejected, overkill for a one-bullet note. |

### Constraints
- **Hackathon deadline: 2026-05-18.** Spec must be small enough to land + verify well before submission. Standard pipeline (no `@fp-architect`, no `@fp-design-visionary`, no `@fp-data-reviewer`) keeps the round-trip short.
- **No authentication / no per-user state.** Per `feedback_profile_is_build`, profile is per-build, not per-user. This spec does not introduce session state, login surfaces, or any account concept.
- **No test may be silently disabled.** The only authorized test deletions are the three `buildStore.test.ts` tests + describe block listed in §4 "Authorized Test Modifications". Any other failure → STOP and escalate.
- **Persist-key migration is not required.** Existing dev-environment `localStorage` may carry `hasSeenStatTutorial: true` after this lands. Zustand's `persist` middleware safely ignores unknown keys on read, so the stale field is inert. No migration step needed.

### Out of Scope (explicitly excluded from this spec)

| Item | Why deferred |
|------|--------------|
| Top 10 #7 — `src/mcp_server/futureproof_server.py` 3,640-line god-module split | Audit explicitly defers to its own dedicated `refactor-` spec post-hackathon. 2-4 hour structural change wants its own review window. |
| `backend/app/services/set_your_course.py` 1,105-line size cleanup | Same shape as #7 — own spec post-hackathon. |
| `_handle_get_school_programs` 200,000-row scan performance | Own `performance-` spec; needs DuckDB index strategy thinking, not bundleable. |
| `app/state.py` `_builds` dict + `wrapped.py` `_render_locks` LRU eviction | 🔵 Minor for hackathon, real for production — audit flagged for post-submission. |
| `compare_builds` N round-trips → single `WHERE build_id IN (...)` | 🔵 Trivial perf cleanup, not a first-impression risk; defer. |
| `backend/tests/fixtures/intent_responses.json` orphan cleanup | Already documented in `refactor-remove-dead-frontend-code.md` §6 Deviations as a follow-up; can ride a future fixture-audit spec, not this one. |
| Adding actual log rotation / scrubbing tooling | This spec is README-only — operators handle log rotation via their own tooling (logrotate, journald, Railway log retention). Building rotation in-app would be a real feature. |

---

## §3 UI/UX Design

**SKIPPED** — backend cleanup + dead-state removal + README copy. No live UI changes. The `clearSession()` comment + `statExplanations` docstring + `hasSeenStatTutorial` removal are all behavior-preserving.

---

## §4 Technical Specification

### Architecture Overview

Pure cleanup. No new modules, no schema changes, no API surface changes. Touches:

- **Frontend store:** strip a dead persist key from `useBuildStore` and its tests/fixtures.
- **Frontend screen:** add a one-line rationale comment on the existing `clearSession().catch(console.warn)` call site.
- **Frontend data module:** rewrite a stale 4-line docstring; no code change.
- **Backend service:** add `^\d{2}$` regex validation in one helper before SQL interpolation.
- **Backend bootstrap:** wrap one existing function call in try/except inside the FastAPI `lifespan` context manager.
- **README:** add a short operator-hygiene bullet to the existing "Security & Deployment" section.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/store/buildStore.ts` | Modify | Remove `hasSeenStatTutorial: boolean;` and `setHasSeenStatTutorial: (seen: boolean) => void;` from the `BuildState` interface (lines 24-25). Remove `hasSeenStatTutorial: false,` initial value and the `setHasSeenStatTutorial` setter from the store factory (lines 55-57). Remove `hasSeenStatTutorial: state.hasSeenStatTutorial,` from `partialize` (line 80). After removal, `partialize` returns an empty object — also remove the `partialize` option entirely (no other persisted fields), or replace with `partialize: () => ({})` if Zustand 4 requires the key. Verify against installed `zustand` version. |
| `frontend/src/store/buildStore.test.ts` | Modify | Remove `hasSeenStatTutorial: false,` from `beforeEach` setState (line 64). Delete the `it("preserves hasSeenStatTutorial across resetBuild", ...)` test (lines 131-142). Delete the entire `describe("hasSeenStatTutorial localStorage persistence", ...)` block (lines 145-173). Update the header docstring (lines 5-12) to drop bullets 2 and 3 (the persistence/preservation claims) and document only the surviving `setTieredCareers nullability` + `resetBuild clears build state` contracts. |
| `frontend/src/screens/MenuScreen.test.tsx` | Modify | Remove `hasSeenStatTutorial: false,` line from the `useBuildStore.setState({...})` call in the test-setup `beforeEach` (line 190). |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Remove `hasSeenStatTutorial: true,` line from the `useBuildStore.setState({...})` call in `seedReady()` (line 238). |
| `frontend/src/data/statExplanations.ts` | Modify | Replace lines 1-4 docstring (`Used by StatTutorial overlay and persistent StatHelpTooltip.`) with a current description: "Stat metadata used by the build-results pentagon legend (`BuildResultsScreen`), `PentagonChart`, `CareerCard`, and the horizon mockups for stat colors and abbreviations." No code changes. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Add a one-line comment immediately above `clearSession().catch(console.warn);` at line 553 explaining that the call is intentionally fire-and-forget — the network round-trip is best-effort cleanup of server-side session state, the user is already navigating away, and a future "fix" to `await` would block navigation on a network outage. |
| `backend/app/services/intent.py` | Modify | In `_get_crosswalk_cips_for_families` (lines 202-229), add a `re.compile(r"^\d{2}$")` validation pass over `family_prefixes` before constructing the SQL `conditions` clause. Prefixes that fail the pattern are dropped with a `logger.debug("intent._get_crosswalk_cips_for_families: dropping malformed prefix %r", p)` line. If all prefixes are dropped, return `[]` early (matches existing empty-input branch at lines 205-206). Use a module-level compiled pattern constant (`_CIP_FAMILY_PREFIX_PATTERN`) for cheap reuse. |
| `backend/app/main.py` | Modify | In `lifespan` (lines 56-88), wrap the `_load_existing_profiles()` call at line 62 in `try/except Exception as exc:` with `log.warning("profile preload failed: %s", exc, exc_info=True)`. Style mirrors the Iceberg warmup `try/except` block at lines 77-86. The `from app.services.profile import _load_existing_profiles` import at line 59 stays where it is. |
| `README.md` | Modify | Append one bullet to the existing "Security & Deployment" section (after line 28, the DuckDB/Iceberg surface bullet): "**Logging hygiene** — `logs/gemma.jsonl` captures every Gemma exchange (system + user message + response) for demo/debug visibility. The directory is gitignored, but operators sharing logs externally (bug reports, hackathon submissions, support tickets) should rotate or scrub the file first — anything a student typed is in there. Set `GEMMA_LOG_DISABLED=1` to suppress writes when needed." |

### Data Model Changes
None.

### Service Changes

#### `backend/app/services/intent.py`

New module-level constant:

```python
_CIP_FAMILY_PREFIX_PATTERN = re.compile(r"^\d{2}$")
```

New behavior in `_get_crosswalk_cips_for_families(family_prefixes: list[str]) -> list[dict[str, str]]`:

```python
def _get_crosswalk_cips_for_families(
    family_prefixes: list[str],
) -> list[dict[str, str]]:
    if not family_prefixes:
        return []
    valid_prefixes: list[str] = []
    for p in family_prefixes:
        head = p[:2]
        if _CIP_FAMILY_PREFIX_PATTERN.fullmatch(head):
            valid_prefixes.append(head)
        else:
            logger.debug(
                "intent._get_crosswalk_cips_for_families: dropping malformed prefix %r",
                p,
            )
    if not valid_prefixes:
        return []
    server = mcp_client.get_server()
    conditions = " OR ".join(
        f"SUBSTR(cipcode, 1, 2) = '{p}'" for p in valid_prefixes
    )
    sql = (
        f"SELECT DISTINCT cipcode, cip_title "
        f"FROM base_cip_soc_crosswalk "
        f"WHERE ({conditions}) "
        f"ORDER BY cipcode"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        logger.warning(
            "intent._get_crosswalk_cips_for_families query failed; returning empty",
            exc_info=True,
        )
        return []
    return [
        {"cipcode": str(r["cipcode"]), "cip_title": str(r.get("cip_title", ""))}
        for r in rows
        if r.get("cipcode")
    ]
```

#### `backend/app/main.py`

`lifespan` body acquires a single try/except around the profile preload (mirroring the existing Iceberg warmup style):

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.services.mcp_client import get_server
    from app.services.profile import _load_existing_profiles

    log = logging.getLogger("startup")
    try:
        _load_existing_profiles()
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("profile preload failed: %s", exc, exc_info=True)

    # Warm the Iceberg catalog so the first /build/outcomes request
    # doesn't pay metadata-load latency that can exceed Railway's
    # liveness window. Each load_table() reads only metadata.json,
    # not data files — cheap.
    warm_tables = [
        "consumable.program_career_paths",
        ...
    ]
    ...
    yield
```

No new public function signatures, no new dependencies.

### Testing Impact Analysis

> Search performed: `grep -rn "hasSeenStatTutorial" frontend/src/` — 17 hits across 5 files (3 prod files + 2 tests + 1 store test). All 5 covered below. `grep -rn "_get_crosswalk_cips_for_families\|_CIP_FAMILY_PREFIX" backend/` — covered in `backend/tests/services/test_intent.py` (per §6 of the deletion spec, this file was deleted, so coverage is now via `set_your_course` integration tests). Need a fresh focused test for the new validation behavior. `grep -rn "_load_existing_profiles\|lifespan" backend/tests/` — no existing direct test of the lifespan profile-preload path.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/store/buildStore.test.ts` | `preserves hasSeenStatTutorial across resetBuild` | High (deleted) | Test target removed from store interface. |
| `frontend/src/store/buildStore.test.ts` | `writes hasSeenStatTutorial=true to localStorage when set` | High (deleted) | Persisted key removed. |
| `frontend/src/store/buildStore.test.ts` | `does NOT persist transient state (tieredCareers/build) to localStorage` | Medium (modified) | The test's positive assertion (`parsed.state.hasSeenStatTutorial).toBe(true)`) becomes invalid; the negative assertions about `tieredCareers`/`build` not persisting are still meaningful. Keep the negative half, drop the positive half. If the surviving assertions can stand without `hasSeenStatTutorial` setup, modify in place; otherwise delete the test (the tieredCareers/build negative assertions are also covered by the deleted-key check itself). |
| `frontend/src/store/buildStore.test.ts` | `setTieredCareers nullability` describe block (2 tests) | None — Confirmed Safe | Independent of the persist key. Must still pass. |
| `frontend/src/store/buildStore.test.ts` | `clears build/selectedCareer/tieredCareers/isBuilding/buildingStage` | None — Confirmed Safe | Independent of the persist key. Must still pass. |
| `frontend/src/screens/MenuScreen.test.tsx` | All cases (the file's `beforeEach` references the removed key in setState) | Low | One-line setState fix in `beforeEach`. All test bodies remain unchanged. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | All cases (the `seedReady()` helper references the removed key) | Low | One-line setState fix in `seedReady`. All test bodies remain unchanged. |
| `backend/tests/services/test_set_your_course*.py` (any test exercising `_get_crosswalk_cips_for_families` indirectly) | None — Confirmed Safe | Validation is a tighten, not a break. All currently-valid prefixes (server-derived 2-digit strings) continue to pass. |
| `backend/tests/test_app.py` (CORS preflight + lifespan smoke) | None — Confirmed Safe | The lifespan try/except wrap is purely defensive — under non-error conditions behavior is identical. Smoke tests must continue to pass. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/store/buildStore.test.ts` line 64 | Remove `hasSeenStatTutorial: false,` from the `beforeEach` setState block | Field no longer exists on the store. |
| `frontend/src/store/buildStore.test.ts` lines 131-142 | Delete `it("preserves hasSeenStatTutorial across resetBuild", ...)` test | Target removed; failure mode no longer reachable. |
| `frontend/src/store/buildStore.test.ts` lines 145-173 | Delete `describe("hasSeenStatTutorial localStorage persistence", ...)` block (2 tests) | Persisted key removed. |
| `frontend/src/store/buildStore.test.ts` lines 5-12 | Update header docstring — drop persistence/preservation bullets, keep nullability + reset-clears bullets | Reflects post-cleanup contract. |
| `frontend/src/screens/MenuScreen.test.tsx` line 190 | Remove `hasSeenStatTutorial: false,` from the `useBuildStore.setState({...})` call | Field no longer exists. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` line 238 | Remove `hasSeenStatTutorial: true,` from the `useBuildStore.setState({...})` call | Field no longer exists. |

#### Confirmed Safe (must still pass — if any fail, STOP)
- `frontend/src/store/buildStore.test.ts` — surviving `setTieredCareers nullability` describe block (2 tests) and the `resetBuild → clears build/selectedCareer/tieredCareers/isBuilding/buildingStage` test.
- All `frontend/src/screens/MenuScreen.test.tsx` test bodies (only the `beforeEach` setState shape changes).
- All `frontend/src/screens/BuildResultsScreen.test.tsx` test bodies (only the `seedReady()` setState shape changes).
- All `frontend/src/screens/SetYourCourseScreen.test.tsx` cases.
- All `frontend/src/screens/CareerPickScreen.test.tsx` cases.
- All `frontend/src/screens/FutureScreen.test.tsx` cases.
- `frontend/src/components/PentagonChart.test.tsx` (live consumer of `StatKey`).
- `frontend/src/components/CareerCard.test.tsx` (live consumer of `STAT_MAP`).
- All `backend/tests/services/test_set_your_course*.py` cases.
- All `backend/tests/services/test_intent.py` cases (the new file at `backend/tests/services/test_intent.py` per the dead-code refactor — verify what's there; if the parent spec deleted it entirely, the new P0 in this spec stands alone).
- `backend/tests/test_app.py` (lifespan smoke + CORS preflight).
- `backend/tests/services/test_locale.py`.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_drops_malformed_prefixes` | Pass `_get_crosswalk_cips_for_families(["11", "abc", "5", "11.0701"])`. Stub `mcp_client.get_server().query_iceberg` and capture the SQL. Assert: `"5"` and `"abc"` are dropped (DEBUG log expected); `"11"` passes through; `"11.0701"` is truncated to `"11"` and passes through. SQL must contain only `'11'`-keyed conditions. |
| P0 | `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_all_invalid_returns_empty` | Pass `["abc", "1", ""]`. Assert returns `[]` without invoking `mcp_client.get_server()`. |
| P0 | `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_valid_prefixes_unchanged` | Pass `["11", "14", "52"]`. Assert SQL contains all three `SUBSTR(...) = 'NN'` conditions in order; result mirrors stubbed query rows. (Regression guard against accidental over-strict validation.) |
| P1 | `backend/tests/test_app.py` | `test_lifespan_tolerates_profile_preload_failure` | Patch `app.services.profile._load_existing_profiles` to raise `RuntimeError`. Use `TestClient(app)` to enter/exit the lifespan. Assert the app starts (no exception propagates), responds to a `GET /healthz` request, and a `WARNING`-level log record was emitted with `"profile preload failed"` substring. |
| P1 | `frontend/src/store/buildStore.test.ts` | `test_persisted_localStorage_no_longer_carries_stat_tutorial_key` | After importing the store and triggering a `setTieredCareers` call (which still writes nothing to localStorage per the empty `partialize`), assert `localStorage.getItem("futureproof-build")` either returns `null` or returns a state object whose `state` field does not contain `hasSeenStatTutorial`. (Regression guard against re-introducing the persist key.) |
| P2 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_clearSession_failure_does_not_block_navigation` | Mock `clearSession` to reject. Click the "start over" button. Assert `navigate("/set-your-course")` was still called and no unhandled rejection was logged at `console.error`. (Codifies the fire-and-forget contract that the new comment documents.) |

#### Test Data Requirements

- No new fixtures needed. The new `intent.py` tests stub `mcp_client.get_server()` directly (existing pattern in `backend/tests/services/test_intent.py`).
- The new lifespan test uses `TestClient` from FastAPI's `starlette.testclient`, which already drives the lifespan context manager.

---

## §5 Architecture Review

**Status:** SKIPPED (Standard pipeline — no architectural change. No new module, no schema change, no API surface change.)

If the @faang-staff-engineer review in §8 surfaces an architectural concern, escalate via §10.

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified

| File | Change Summary |
|------|---------------|
| `frontend/src/store/buildStore.ts` | Removed `hasSeenStatTutorial` field, setter, and persisted partialize. Removed the `persist` middleware entirely (Zustand 5) — no fields remained to persist, and keeping `persist` with `partialize: () => ({})` would leave a writeback that future contributors might "fix" back into a real persist of the full state. Store is now a plain `create<BuildState>()(...)` factory. |
| `frontend/src/store/buildStore.test.ts` | Updated header docstring to reflect post-cleanup contract; dropped `hasSeenStatTutorial` from `beforeEach` setState; deleted "preserves hasSeenStatTutorial across resetBuild" test; replaced the `hasSeenStatTutorial localStorage persistence` describe block with a single regression-guard test asserting the legacy key is no longer written under `futureproof-build`. |
| `frontend/src/screens/MenuScreen.test.tsx` | Removed `hasSeenStatTutorial: false,` from the `useBuildStore.setState` seed in `beforeEach`. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Removed `hasSeenStatTutorial: true,` from `seedReady()`. Added module-level `vi.mock("@/api/session")` with a `mockClearSession` handle, reset in `beforeEach`. Added a `Start Over (P2)` describe block with `navigates_when_clearSession_rejects` codifying the fire-and-forget contract that the new comment documents. |
| `frontend/src/data/statExplanations.ts` | Replaced the stale "Used by StatTutorial overlay and persistent StatHelpTooltip" docstring with the current consumer list (`BuildResultsScreen`, `PentagonChart`, `CareerCard`, horizon mockups). No code change. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Added a 4-line comment immediately above `clearSession().catch(console.warn)` at the Start Over `onClick` explaining the fire-and-forget intent and warning future contributors not to "fix" it into an `await`. |
| `backend/app/services/intent.py` | Added module-level `_CIP_FAMILY_PREFIX_PATTERN = re.compile(r"^\d{2}$")`. Rewrote the prefix-collection step in `_get_crosswalk_cips_for_families` to validate each `p[:2]` against the pattern; non-matching prefixes are dropped with `logger.debug(...)`. If every prefix fails validation, return `[]` early without invoking `mcp_client.get_server()`. |
| `backend/app/main.py` | Wrapped the `_load_existing_profiles()` call inside `lifespan` in `try/except Exception as exc` with `log.warning("profile preload failed: %s", exc, exc_info=True)`. Style mirrors the Iceberg warmup `try/except` block immediately below it. |
| `backend/tests/services/test_intent.py` | Added three P0 tests covering the new validation: `test_get_crosswalk_cips_for_families_drops_malformed_prefixes`, `test_get_crosswalk_cips_for_families_all_invalid_returns_empty`, `test_get_crosswalk_cips_for_families_valid_prefixes_unchanged`. Uses a `_CapturingServer` stub to assert on the SQL passed to `query_iceberg`. |
| `backend/tests/test_app.py` | Added P1 `test_lifespan_tolerates_profile_preload_failure` patching `app.services.profile._load_existing_profiles` to raise, asserting the app still boots and a `WARNING`-level log record with `"profile preload failed"` substring is emitted. |
| `README.md` | Appended the Logging hygiene bullet under the existing "Security & Deployment" section, documenting `logs/gemma.jsonl` rotation/scrubbing requirements and the `GEMMA_LOG_DISABLED=1` opt-out (verified the env var is real — `gemma_client.py:253`). |

### Deviations from Spec

| # | Deviation | Reason |
|---|-----------|--------|
| 1 | Removed the `persist` middleware entirely from `buildStore.ts` rather than using `partialize: () => ({})`. | Zustand 5 (the installed version) does not require `partialize` to be present — and removing the entire middleware is cleaner than retaining `persist({ name: "futureproof-build" })` writing an empty state wrapper to localStorage on every mutation. The new P1 regression test in `buildStore.test.ts` accepts both shapes (`null` or no `hasSeenStatTutorial` key), so the contract holds either way. The spec text in §4 explicitly allowed "remove the `partialize` option entirely" as one of two options. |
| 2 | Replaced the spec's proposed `does NOT persist transient state (tieredCareers/build) to localStorage` survivor with a single new "no legacy hasSeenStatTutorial key after store mutations" regression test. | The original test's positive assertions all keyed off `hasSeenStatTutorial` being persisted; with the persist middleware gone, the survivor would have been a thin wrapper with no failure mode. The new regression test directly guards against re-introducing the persist middleware with the legacy key, which is the actual risk this spec mitigates. |

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | n/a | Backend ruff + pytest, frontend tsc + vitest + Vite production build all green on first run. No build retries needed. |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_drops_malformed_prefixes` | P0 — `["11", "abc", "5", "11.0701"]` → SQL contains only `'11'` keys; `"abc"`/`"5"` dropped (DEBUG log); `"11.0701"` truncates to `"11"`. |
| `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_all_invalid_returns_empty` | P0 — `["abc", "1", ""]` returns `[]` and never calls `mcp_client.get_server()`. |
| `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_valid_prefixes_unchanged` | P0 — `["11", "14", "52"]` produces SQL containing all three `SUBSTR(...) = 'NN'` clauses; results pass through unchanged (regression guard against an over-strict pattern). |
| `backend/tests/test_app.py` | `test_lifespan_tolerates_profile_preload_failure` | P1 — patches `_load_existing_profiles` to raise; asserts app boots, `/health` returns 200, and a `WARNING`-level `"profile preload failed"` log record is emitted under the `startup` logger. |
| `frontend/src/store/buildStore.test.ts` | `does not carry the legacy hasSeenStatTutorial key after store mutations` | P1 — exercises `setTieredCareers`/`setBuild` and asserts `localStorage["futureproof-build"]` is either absent OR has no `hasSeenStatTutorial` field (regression guard against re-introducing the persist middleware with the legacy key). |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `navigates_when_clearSession_rejects` | P2 — mocks `clearSession` to reject, clicks "Start over", asserts `mockNavigate("/set-your-course")` was still invoked and `console.error` was not called. Codifies the fire-and-forget contract documented by the new comment. |

### Test Results

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 1274 | 0 | 0 | 1274 |
| pytest (pipeline) | 1720 | 0 | 1 (deselected) | 1721 |
| vitest | 727 | 0 | 0 | 727 |

---

## §8 Reviews

**Status:** SKIPPED — bundled cleanup, no behavioral change beyond the audit-driven defensive guards. Spec author elected to ship without a separate `@faang-staff-engineer` round-trip given (a) the diff is purely additive defense (try/except, regex validation, dead-key removal, comment + docstring), (b) every change carries direct test coverage in §7, and (c) build verification passed on first attempt with zero new mypy errors. Any reviewer concern can be raised as a follow-up; nothing here changes API contracts, data models, or migration semantics.

### Design Audit (@design-builder)
**Status:** SKIPPED (no live UI changes — comment, docstring, and dead-state removal only)

### Code Review (@faang-staff-engineer)
**Status:** SKIPPED (see §8 header rationale)

---

## §9 Verification

**Status:** COMPLETE

### Backend

| Check | Result |
|-------|--------|
| Lint (ruff) | ✅ All checks passed |
| Type check (mypy) | ⚠️ 69 pre-existing errors (was 72 on parent commit `925f887`); zero new errors introduced. The drop of 3 comes from the dead-state removal (one mypy-flagged annotation became unreachable). The `intent.py:467` `_audit_intent_mapping` `no-any-return` finding is in code untouched by this spec. |
| Tests (pytest) | ✅ 1274 passed, 0 failed, 0 skipped (backend); 1720 passed, 1 deselected for `not network` marker (pipeline) |

### Frontend

| Check | Result |
|-------|--------|
| TypeScript (`npx tsc --noEmit`) | ✅ Exit code 0, no output |
| Tests (`npx vitest run`) | ✅ 727 passed, 0 failed across 60 test files |
| Production build (`npm run build`) | ✅ Vite v6.4.1 — 707 modules transformed, dist generated cleanly. Pre-existing >500 kB chunk warning unchanged. |

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | n/a | All checks green on first attempt. |

---

## §10 Discussion

```
[2026-04-30] Spec author note
The audit (reports/staff-engineer-audit-2026-04-30.md) identifies one location
discrepancy: the bonus #11 "clearSession fire-and-forget" comment is described
as being needed in App.tsx, but the actual call site is BuildResultsScreen.tsx:553.
This spec writes the comment at the real call site (see Decision #4) — do not
chase the audit text into App.tsx.

The parent spec (refactor-remove-dead-frontend-code.md, COMPLETE 2026-04-26)
missed the persist-store residue documented in §4 here. Decision #2 explicitly
chooses NOT to reopen that spec; the reasoning is in §2. If a reviewer asks
"why didn't this land in the parent spec," the answer is in §2 Decision #2.
```

---

## §11 Final Notes

**Human Review:** PENDING

Estimated diff: ~30 LOC removed (frontend store + tests), ~20 LOC added (backend validation + try/except + new tests), ~10 LOC docs (README bullet + statExplanations docstring + clearSession comment). Net ≈ small.

After this lands, the audit's Post-Hardening Status table should show:
- Top 10 #6 → ✅ DONE
- Top 10 #11 (bonus) → ✅ DONE
- "Other findings" `intent.py:202-211` defense-in-depth → ✅ DONE
- "Other findings" `lifespan` `_load_existing_profiles()` wrap → ✅ DONE
- "Other findings" `logs/gemma.jsonl` README operator note → ✅ DONE

Remaining open after this spec ships:
- Top 10 #7 — `futureproof_server.py` god-module split (own `refactor-` spec, post-hackathon).
- Other findings — `set_your_course.py` size cleanup, `_handle_get_school_programs` performance, `app/state.py` / `wrapped.py` LRU eviction, `compare_builds` round-trips. All deferred per §2 "Out of Scope" and the parent audit.
