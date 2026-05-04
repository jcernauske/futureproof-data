# Spike: Analyze Orphan API Endpoints (Decide Keep vs. Remove)

## Claude Code Prompt

```
Read the spec at docs/specs/spike-analyze-orphan-api-endpoints.md in its entirety.

This is an ANALYSIS spike — output is a written recommendation, NOT a code change.
Do NOT delete or modify any router, service, model, or test as part of executing this spec.

Execute the following workflow:

1. INVESTIGATION
   - For each endpoint listed in §4 "Endpoints Under Review":
     a. Confirm zero frontend callers (re-grep at execution time, not relying on prior audit).
     b. Search `archive/spikes/cli/` for callers (the archived CLI may still consume them).
     c. Search `scripts/` for callers (one-off operational scripts).
     d. Search `docs/`, `README.md`, `docs/specs/completed/`, `docs/futureproof_vision_roadmap.md`,
        and the Kaggle submission materials for documented promises that the endpoint exists.
     e. Search the OpenAPI surface (`backend/app/main.py` registration + any generated `openapi.json`)
        to confirm the endpoint is publicly exposed.
     f. Check git history (`git log --all -p -- backend/app/routers/<file>.py`) for any indication
        the endpoint is used by an external system Jeff mentioned (demo script, beta-tester landing,
        Kaggle reviewer instructions).
   - For each endpoint, fill in §6 "Per-Endpoint Findings" with the data above and a recommendation.

2. RECOMMENDATION
   - Write §7 "Final Recommendation" — for each endpoint, one of:
     * REMOVE — no callers, no documented promise, no demo dependency. Cleanup goes in spec
       `refactor-remove-dead-frontend-code.md` (CONDITIONAL items there are gated on this verdict).
     * KEEP — has a real consumer or a documented external promise. Justify.
     * KEEP-AND-DOCUMENT — endpoint is intentionally public surface (e.g., MCP-callable, demo URL)
       but undocumented. File a follow-up to add docs.
   - Surface any second-order cleanup the recommendation enables or blocks.

3. HUMAN REVIEW
   - Set status to AWAITING HUMAN REVIEW.
   - Do NOT proceed to deletion. Jeff makes the call.

4. HAND-OFF (only after Jeff approves)
   - For each REMOVE verdict, file the deletion items in spec `refactor-remove-dead-frontend-code.md`'s
     §4 (or open a new spec if the deletions are large enough to warrant it).
   - Mark this spec COMPLETE.

NO CODE CHANGES IN THIS SPEC. If you catch yourself editing a router, stop.
```

---

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-26 |
| Author | Jeff + Claude (staff-engineer audit + Codex verification) |
| Spec Version | 1.1 |
| Last Updated | 2026-05-03 (re-verified — endpoints 1 & 2 already removed in dead-code cleanup pass; rescoreBuild frontend export also gone; endpoints 3-7 verdicts re-confirmed and approved by Jeff) |
| Blocked By | — |
| Related Specs | `refactor-remove-dead-frontend-code.md` (completed; handled endpoints 1 & 2 indirectly via MajorInput.tsx + intent.py removal) |

---

## §1 Feature Description

### Overview
Investigate seven backend HTTP endpoints that have **zero callers from the live frontend** but are **still registered in `backend/app/main.py`** and therefore present on the public OpenAPI surface. Decide for each: REMOVE, KEEP, or KEEP-AND-DOCUMENT.

### Problem Statement
A staff-engineer audit (verified by Codex) flagged these endpoints as having no frontend caller:

1. `POST /intent/` (legacy) — `backend/app/routers/intent.py`
2. `POST /intent/confirm` (legacy) — `backend/app/routers/intent.py`
3. `GET /build/{id}/report` — `backend/app/routers/reports.py`
4. `GET /builds/compare/report` — `backend/app/routers/reports.py`
5. `POST /profile/lookup` — `backend/app/routers/profile.py`
6. `POST /build/{id}/rescore` — `backend/app/routers/gauntlet.py`
7. `POST /build/{id}/gauntlet` — `backend/app/routers/gauntlet.py`

Per **CLAUDE.md "no path is out of scope" rule**, registered API endpoints are public surface. They could be consumed by:
- The archived CLI (`archive/spikes/cli/`)
- One-off scripts under `scripts/`
- External demo flows pointed at by the Kaggle submission, the README, or the marketing landing
- Beta testers probing the API directly
- MCP-server or Gemma function-calling integrations that bypass the frontend
- Future planned features documented in `docs/specs/` or the vision roadmap

A "delete because the React app doesn't call it" decision is wrong if any of the above is true. This spike collects the evidence to make the call rigorously.

### Success Criteria
- [ ] §6 "Per-Endpoint Findings" is filled in for all 7 endpoints with caller search results across:
  - frontend (`frontend/src/`)
  - archived CLI (`archive/spikes/cli/`)
  - scripts (`scripts/`)
  - docs (`docs/`, `README.md`, vision roadmap, Kaggle materials)
  - git history (last 90 days)
- [ ] §7 "Final Recommendation" gives a one-word verdict (REMOVE / KEEP / KEEP-AND-DOCUMENT) per endpoint with justification
- [ ] No code is changed by this spec
- [ ] Status set to AWAITING HUMAN REVIEW when investigation is complete

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Analysis-only spec, no code changes | Removing public API surface without explicit human approval violates the "no path is out of scope" rule. Different risk profile than pure-dead-code deletion. | Bundle into `refactor-remove-dead-frontend-code.md` — rejected, conflates risk classes. |
| 2 | Investigate all 7 endpoints in one spec | They share the same risk profile (registered-but-uncalled-by-frontend). One investigation, one decision pass. | Seven separate specs — rejected, ceremony overhead. |
| 3 | Search the archived CLI for callers | Per CLAUDE.md, the CLI is archived but `archive/spikes/cli/cli.py` still imports backend services. It may also call HTTP endpoints. | Treat archived = dead — rejected, would miss the case where the CLI is the only consumer. |
| 4 | Search `docs/`, README, Kaggle materials for documented promises | Removing an endpoint a judge or external user has been told about is a footgun. | Trust the import graph alone — rejected. |
| 5 | Output classification: REMOVE / KEEP / KEEP-AND-DOCUMENT (no fourth option) | Forces a clean decision. KEEP-AND-DOCUMENT covers the case where the endpoint is real public API but the docs lie. | Add MAYBE / DEFER — rejected, defers the decision. |

### Constraints
- This spec **must not modify any code under `backend/app/routers/`, `backend/app/services/`, or `backend/app/models/`**.
- It may modify only this spec file (filling in §6 and §7) and `docs/sessions/` (logging).
- Investigation must use the working tree at execution time, not the audit snapshot. Codebases drift.

---

## §3 UI/UX Design

**SKIPPED** — backend analysis only.

---

## §4 Technical Specification

### Endpoints Under Review

| # | Method | Path | Router File | Status from Audit | Why Suspected Dead |
|---|--------|------|-------------|-------------------|--------------------|
| 1 | POST | `/intent/` | `backend/app/routers/intent.py` | No frontend caller | Replaced by `/intent/stream` + `/intent/chip` + `/intent/commit` in `routers/set_your_course.py` |
| 2 | POST | `/intent/confirm` | `backend/app/routers/intent.py` | No frontend caller | Same — superseded by the `set_your_course` family |
| 3 | GET | `/build/{id}/report` | `backend/app/routers/reports.py` | No frontend caller | No `getBuildReport`-shaped function in `frontend/src/api/` |
| 4 | GET | `/builds/compare/report` | `backend/app/routers/reports.py` | No frontend caller | Frontend has `compareBuilds` (`POST /builds/compare`) but no caller for the markdown-report variant |
| 5 | POST | `/profile/lookup` | `backend/app/routers/profile.py` | No frontend caller | Frontend uses `POST /profile` and `POST /profile/reroll` only |
| 6 | POST | `/build/{id}/rescore` | `backend/app/routers/gauntlet.py` | No frontend caller | Frontend `rescoreBuild` export exists but is itself dead (zero callers) |
| 7 | POST | `/build/{id}/gauntlet` | `backend/app/routers/gauntlet.py` | No frontend caller | The build orchestration runs the gauntlet inline; the standalone endpoint is unused |

### Investigation Procedure (per endpoint)

For each endpoint, run these checks and record results in §6:

1. **Frontend callers** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" frontend/`
2. **Archived CLI callers** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" archive/`
3. **Scripts callers** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" scripts/`
4. **Documentation references** — `rg -nS "<endpoint-path>" docs/ README.md` plus a search of `docs/futureproof_vision_roadmap.md` and `docs/futureproof_hackathon_prd.md`
5. **OpenAPI surface** — confirm registration in `backend/app/main.py`; if a generated `openapi.json` is committed, confirm presence
6. **Git history** — `git log --all --oneline --since="90 days ago" -- <router-file>` to spot recent activity
7. **Tests** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" backend/tests/` to know what test cleanup follows
8. **External integrations** — check `src/mcp_server/` and any Gemma function-calling configs for indirect callers

### File Changes
**None.** This spec writes only to itself.

### Data Model Changes
None.

### Service Changes
None.

### Testing Impact Analysis
**N/A** — analysis only. Any tests touched by the eventual deletion will be tracked in the spec that does the deletion.

---

## §5 Architecture Review

**Status:** SKIPPED (analysis spike, no architectural change)

---

## §6 Per-Endpoint Findings

**Status:** COMPLETE

### Endpoint 1: `POST /intent/` — **ALREADY REMOVED (2026-05-03 verification)**
> Re-verified 2026-05-03: `backend/app/routers/intent.py` no longer exists; `MajorInput.tsx` no longer exists; `/intent` prefix in `main.py:113` now routes to `set_your_course.router`. The dead-code cleanup pass (commit `b2f5ea0` / `d3d8d9c`) handled this. **No further action needed.**
- **Router:** `backend/app/routers/intent.py` (deleted)
- **Frontend callers:** Only `frontend/src/components/school/MajorInput.tsx:49` — dead code being deleted in `refactor-remove-dead-frontend-code.md`. Zero live callers.
- **Archived CLI callers:** `archive/spikes/cli/cli.py:609` references the intent system prompt but imports `intent.resolve_intent` as a Python function — it does not HTTP-call `/intent/`. No HTTP caller.
- **Scripts callers:** `scripts/yaml_regression.py` imports `intent.resolve_intent` directly (Python import, not HTTP call).
- **Documentation references:** PRD v8 line 521 lists `POST /intent` in the endpoint table. `docs/reference/archive/full-vision-report.md:784` lists it. Multiple completed specs reference it historically (`bugfix-broad-cip-substitution-and-intent.md`, `feature-gemma-tiered-matching.md`, `screen-school-major-sliders.md`). All describe the pre-SetYourCourse design that has been superseded.
- **OpenAPI surface:** Registered at `backend/app/main.py:42` (`intent.router` under `/intent` prefix).
- **Git history (last 90d):** 2 commits — `1e3a726` (refactor boss fight generation) and `ead552d` (initial router wiring). Neither adds a new caller.
- **Tests:** `backend/tests/services/test_intent.py` (1,200+ lines) tests the service functions. No router-level test for `POST /intent/` exists. The live intent surface is tested via `backend/tests/routers/test_set_your_course_router.py`.
- **External integrations:** None in `src/mcp_server/` or `domain/` configs.
- **Notes:** The live flow uses `/intent/stream` + `/intent/chip` + `/intent/commit` (routed via `set_your_course.py`). This legacy endpoint was the synchronous predecessor. PRD v8 references are historical — the design evolved.
- **Recommendation:** **REMOVE**

### Endpoint 2: `POST /intent/confirm` — **ALREADY REMOVED (2026-05-03 verification)**
> Re-verified 2026-05-03: same as Endpoint 1 — file deleted. **No further action needed.**
- **Router:** `backend/app/routers/intent.py` (deleted)
- **Frontend callers:** Only `frontend/src/components/school/MajorInput.tsx:87` — dead code being deleted. Zero live callers.
- **Archived CLI callers:** None. The CLI imported the service function directly.
- **Scripts callers:** None.
- **Documentation references:** Same as endpoint 1 — completed specs reference it historically. `full-vision-report.md:784`. `feature-gemma-tiered-matching.md` describes its role in the old flow. All superseded.
- **OpenAPI surface:** Registered at `backend/app/main.py:42` (same router as `POST /intent/`).
- **Git history (last 90d):** Same 2 commits as endpoint 1.
- **Tests:** `backend/tests/services/test_intent.py` tests `confirm_intent`. No router-level test.
- **External integrations:** None.
- **Notes:** The live confirmation flow uses `POST /intent/commit` via `set_your_course.py`.
- **Recommendation:** **REMOVE**

### Endpoint 3: `GET /build/{id}/report`
- **Router:** `backend/app/routers/reports.py`
- **Frontend callers:** Zero. No `getBuildReport` or `/report` call in `frontend/src/api/`.
- **Archived CLI callers:** Zero.
- **Scripts callers:** Zero.
- **Documentation references:** `docs/specs/deprecated/screen-menu-compare-chat-updated.md:245` lists "Download Report" as "stretch — show only if time permits." `docs/specs/completed/fastapi-router-wiring.md:46,89` describes initial wiring. Both are historical.
- **OpenAPI surface:** Registered at `backend/app/main.py:59` (`reports.router`).
- **Git history (last 90d):** 1 commit — `ead552d` (initial wiring). No subsequent activity.
- **Tests:** `backend/tests/services/test_report_gen.py` tests the service layer (`generate_build_report`). No router-level test.
- **External integrations:** None.
- **Notes:** The `report_gen` service still has value (tested, functional). But the HTTP endpoint has zero callers and was only ever a "stretch" feature. The service can exist without the router.
- **Recommendation:** **REMOVE**

### Endpoint 4: `GET /builds/compare/report`
- **Router:** `backend/app/routers/reports.py`
- **Frontend callers:** Zero. Frontend has `compareBuilds` (`POST /builds/compare`) but no caller for the markdown-report variant.
- **Archived CLI callers:** Zero.
- **Scripts callers:** Zero.
- **Documentation references:** Only in `refactor-remove-dead-frontend-code.md` (this investigation's sister spec). Not referenced in PRD, vision, README, or any other spec.
- **OpenAPI surface:** Registered at `backend/app/main.py:59` (same router as endpoint 3).
- **Git history (last 90d):** 1 commit — `ead552d` (initial wiring).
- **Tests:** `backend/tests/services/test_report_gen.py` tests the service. No router-level test.
- **External integrations:** None.
- **Notes:** Even less justification than endpoint 3 — no spec ever planned to use this, even as a stretch goal.
- **Recommendation:** **REMOVE**

### Endpoint 5: `POST /profile/lookup`
- **Router:** `backend/app/routers/profile.py`
- **Frontend callers:** Zero. Frontend uses `POST /profile` (create) and `POST /profile/reroll` only.
- **Archived CLI callers:** Zero.
- **Scripts callers:** Zero.
- **Documentation references:** `docs/reference/archive/full-vision-report.md:783` lists it. `docs/specs/completed/fastapi-router-wiring.md:115,202,391` describes initial wiring. Both are historical.
- **OpenAPI surface:** Registered at `backend/app/main.py:40` (`profile.router` under `/profile` prefix).
- **Git history (last 90d):** 1 commit — `4f63490` (Screen 1/2 implementation).
- **Tests:** No test for this endpoint. The service function `profile.lookup()` may have unit tests but the HTTP path is untested.
- **External integrations:** None.
- **Notes:** Fuzzy name lookup could support a future "find my build" feature but nothing references that plan. The service function (`profile.lookup`) stays even if the endpoint goes — trivial to re-add later (3 lines in the router).
- **Recommendation:** **REMOVE**

### Endpoint 6: `POST /build/{id}/rescore`
> Re-verified 2026-05-03: the `rescoreBuild` export has been deleted from `frontend/src/api/gauntlet.ts`. Endpoint is now even more orphaned (zero callers AND no client export). Verdict stands.
- **Router:** `backend/app/routers/gauntlet.py`
- **Frontend callers:** Originally exported as dead `rescoreBuild` in `frontend/src/api/gauntlet.ts`; that export is now also gone. Zero callers remain anywhere in `frontend/src/`. The `rescore` text matches that surface in a re-grep are state vars (`rescoreError`) and i18n strings, not HTTP calls.
- **Archived CLI callers:** Zero.
- **Scripts callers:** Zero.
- **Documentation references:** `docs/specs/feature-save-build.md:174` ("Student adjusts sliders → preview via existing POST /build/{id}/rescore") — but that spec is DRAFT and was never implemented. `docs/specs/feature-residency-aware-tuition.md:582,597` discusses a residency gap in `recompute_for_sliders` — architectural commentary, not a caller.
- **OpenAPI surface:** Registered at `backend/app/main.py:48` (`gauntlet.router` under `/build` prefix).
- **Git history (last 90d):** 4 commits on `gauntlet.py` — most recent is `8d51d1a` (i18n). None adds a new caller for `/rescore`.
- **Tests:** No router-level test for `/rescore`.
- **External integrations:** None.
- **Notes:** Semantically different from `/reroll` — `/rescore` re-derives stats for different effort/loan sliders, `/reroll` applies skill picks to a boss fight. But the live UI never uses slider-based rescoring. The underlying service function (`stat_engine.recompute_for_sliders`) survives regardless.
- **Recommendation:** **REMOVE**

### Endpoint 7: `POST /build/{id}/gauntlet`
- **Router:** `backend/app/routers/gauntlet.py`
- **Frontend callers:** Zero. No API client function calls this endpoint. The gauntlet runs inline during `POST /build`.
- **Archived CLI callers:** Zero.
- **Scripts callers:** Zero.
- **Documentation references:** PRD v8 line 523 lists it. `docs/reference/archive/application-chrome.md:440` maps `/build/:id/gauntlet` to Screen 7. `docs/specs/completed/fastapi-router-wiring.md:266-269` describes it as a fallback for "re-run or load from save without gauntlet data."
- **OpenAPI surface:** Registered at `backend/app/main.py:48` (same router as endpoint 6).
- **Git history (last 90d):** Same 4 commits as endpoint 6.
- **Tests:** No router-level test for `/gauntlet`.
- **External integrations:** None.
- **Notes:** The original wiring spec explicitly described this as a fallback. The build orchestration always runs the gauntlet inline during `POST /build` — the standalone endpoint was never used by any code path. `boss_fights.run_gauntlet()` and `boss_fights.score_gauntlet()` survive regardless.
- **Recommendation:** **REMOVE**

---

## §7 Final Recommendation

**Status:** COMPLETE

### Summary Table

| # | Endpoint | Verdict | One-Line Justification |
|---|----------|---------|------------------------|
| 1 | `POST /intent/` | **DONE** | Already removed in the dead-code cleanup pass — `intent.py` and `MajorInput.tsx` are gone. |
| 2 | `POST /intent/confirm` | **DONE** | Already removed alongside endpoint 1. |
| 3 | `GET /build/{id}/report` | **REMOVE** | Zero callers anywhere. Was "stretch" in a deprecated spec. Service layer survives. |
| 4 | `GET /builds/compare/report` | **REMOVE** | Zero callers anywhere. No spec ever planned to use it. Service layer survives. |
| 5 | `POST /profile/lookup` | **REMOVE** | Zero callers. Service function stays — trivial to re-add (3 router lines) if needed. |
| 6 | `POST /build/{id}/rescore` | **REMOVE** | Frontend export `rescoreBuild` exists but has zero importers. Live rescoring uses `/reroll`. Service function survives. |
| 7 | `POST /build/{id}/gauntlet` | **REMOVE** | Standalone gauntlet endpoint was a fallback never used — `POST /build` runs gauntlet inline. |

### Second-Order Effects

**Removing endpoints 1 + 2 (`/intent/`, `/intent/confirm`)** unblocks the CONDITIONAL items in `refactor-remove-dead-frontend-code.md`:
- Delete `backend/app/routers/intent.py` (entire file)
- Delete `resolve_intent`, `confirm_intent`, `_intent_cache` from `backend/app/services/intent.py`
- Delete `IntentRequest`, `IntentConfirmRequest` from `backend/app/models/api.py`
- Delete intent router registration from `backend/app/main.py`
- Delete `backend/tests/services/test_intent.py` (entire file, 1,200+ lines)

**Removing endpoints 3 + 4 (`/build/{id}/report`, `/builds/compare/report`)** enables:
- Delete `backend/app/routers/reports.py` (entire file) and its registration in `main.py`
- The `report_gen` service and its tests (`test_report_gen.py`) should **stay** — they're independently tested and may serve future features. Only the HTTP exposure goes.

**Removing endpoint 5 (`/profile/lookup`)** enables:
- Delete the `lookup` route from `backend/app/routers/profile.py` (3 lines)
- Delete `ProfileLookupRequest` from `backend/app/models/api.py`
- The `profile.lookup()` service function should **stay** — it's clean, tested, and trivial to re-expose.

**Removing endpoints 6 + 7 (`/build/{id}/rescore`, `/build/{id}/gauntlet`)** enables:
- Delete the `run_gauntlet` and `rescore_build` route handlers from `backend/app/routers/gauntlet.py` (lines 10-42)
- Delete `RescoreRequest` from `backend/app/models/api.py` (if no other consumer)
- The `reroll_fight`, `fight_wrapup` routes stay live (called by `GauntletScreen` and `BossBand`)
- The service functions (`boss_fights.run_gauntlet`, `stat_engine.recompute_for_sliders`) stay — only the HTTP wrappers go.

**Scope note:** Endpoints 3-7 are NOT in the current `refactor-remove-dead-frontend-code.md` scope. If Jeff approves removal, they need either an addendum to that spec or a new cleanup spec.

---

## §8 Reviews

### Code Review
**Status:** SKIPPED (no code changes in this spec — deletions tracked in the executing refactor)

### Human Review
**Status:** ACCEPTED 2026-05-03 (Jeff Cernauske)

Jeff approved REMOVE verdicts for endpoints 3-7 after re-verification. Endpoints 1 & 2 had already been swept up in the dead-code cleanup pass. Deletions executed inline (lightweight scope: ~5 endpoints, services preserved).

---

## §9 Verification

**Status:** SKIPPED (no code changes — nothing to build)

---

## §10 Discussion

```
[2026-04-26] Spec author → reader
This spec assumes the audit's caller analysis was right about the frontend (Codex re-verified).
The investigation re-runs the search from scratch on every surface (frontend, CLI, scripts, docs,
git, MCP) to catch anything the audit missed.

If, during investigation, you find an endpoint has callers we didn't know about — DO NOT DELETE.
Document the finding in §6 and recommend KEEP. The audit was wrong about that one.
```

---

## §11 Final Notes

**Human Review:** ACCEPTED 2026-05-03 (Jeff Cernauske)

This spec is intentionally the "slow path." The fast path (`refactor-remove-dead-frontend-code.md`) handled
~95% of the cleanup in one pass with low risk. This spike handles the remaining ~5% — public API surface —
with deliberate caution because the cost of removing an endpoint a judge or beta tester depends on is high.

**Execution note (2026-05-03):** Endpoints 1 & 2 had already been removed by the dead-code cleanup pass that
deleted `MajorInput.tsx` and `intent.py`. Endpoints 3-7 were deleted inline immediately following Jeff's
approval. Service-layer functions preserved per §7 second-order analysis.
