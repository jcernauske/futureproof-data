# Career Description on Sparkle Panel + My Build PDF — Completion Report

**Spec:** `docs/specs/feature-career-description-on-pdf.md`
**Status:** COMPLETE
**Branch:** `grad-school-suggestion`
**Completed:** 2026-05-07

## What shipped

A single Gemma-generated `{summary, tasks[], anchor_tier}` payload powers both the per-career sparkle (✦) panel header card on `/set-your-course` and a new "About this career" section on page 1 of the My Build PDF. The student-visible text equals the printed text by construction: the same `CareerDescription` is stored on `Build.career_description` and rendered by both surfaces.

### Key behaviors

- **Eager generation at build-spawn time.** Joins `_gemma_fanout`'s existing `asyncio.gather` at all three spawn entry points (`create_build`, `_build_stream`, `rebuild_with_sliders`). Failure is non-fatal — the build still succeeds with `career_description=None`.
- **Lazy fallback at PDF export.** When `Build.career_description` is `None`, the PDF endpoint fetches within a 12s timeout and persists via `state.update_build` so the next export skips the call entirely. Failure is silent — PDF still renders, section omitted.
- **Single-flight per `(soc, _PROMPT_VERSION)`.** Concurrent sparkle clicks for the same hot SOC dedupe to one Gemma call (`dict[tuple[str, str], asyncio.Future[CareerDescription]]`). On failure the entry is evicted so the next request retries.
- **Tiered anchor fallback (A → B → C → D).** Tier A: full O*NET activity importance scores. Tier B: BLS occupation summary only (24 partial-tier SOCs — paramedics, EMTs, financial analysts). Tier C: occupation title + SOC major group only (33 SOCs missing entirely from `onet_work_profiles`). Tier D: malformed SOC → raise. Tier B/C generations carry an explicit "AI-inferred from..." disclaimer chip on the panel header card and an italic line in the PDF.
- **Class-aware retry decision tree.** Empty-string transport failure → retry once with original prompt. Non-empty + parse failure → retry with "Output ONLY valid JSON" reminder. Non-empty + voice failure → retry with "Do not use the words: <list>" reminder. Two consecutive failures of any combination → `CareerDescriptionUnavailable`.
- **Voice validation reuse.** Promoted `pdf_questions._has_forbidden_term` to public `pdf_copy.contains_forbidden_term(text, terms)`. Both call sites (PDF questions + career description) now share one source of truth.
- **MCP tool extension.** `get_task_breakdown` now returns `description` and `multi_detail_flag` fields, required for Tier B and Tier A multi-detail prompt scaffolding respectively.

## Files changed (15)

### Backend (10)

- `backend/app/services/career_description.py` — **new** (~600 LOC). Single-flight cache, retry decision tree, three system prompts, two disclaimers, anchor tier ladder, `CareerDescriptionUnavailable` exception, `clear_cache()` test helper.
- `backend/app/services/pdf_copy.py` — promoted `contains_forbidden_term(text, terms)` as public; added `_forbidden_re` LRU.
- `backend/app/services/pdf_questions.py` — switched to import the public helper.
- `backend/app/services/pdf_export.py` — added `_about_this_career_section(build)` rendered between verdict line and pentagon on page 1.
- `backend/app/models/career.py` — added `AnchorTier` literal, `CareerDescription` Pydantic model, `Build.career_description: CareerDescription | None = None`.
- `backend/app/routers/careers.py` — added `GET /careers/{soc_code}/description` endpoint with 502/422 error mapping.
- `backend/app/routers/builds.py` — eager fetch joins `_gemma_fanout`'s gather at all three spawn sites; tuple return updated; final-build commit picks up the description.
- `backend/app/routers/pdf_export.py` — lazy fallback with `wait_for(timeout=12.0)` and `state.update_build` persist.
- `src/mcp_server/futureproof_server.py` — added `description` and `multi_detail_flag` to `TASK_BREAKDOWN_RESPONSE_FIELDS`.
- `backend/ruff.toml` — E501 suppression for `career_description.py` (matches sibling Gemma-prompt files).

### Frontend (5)

- `frontend/src/types/build.ts` — added `AnchorTier`, `CareerDescription`, `Build.career_description?` field.
- `frontend/src/api/careers.ts` — added `fetchCareerDescription(socCode, occupationTitle)`.
- `frontend/src/store/careerDescriptionStore.ts` — **new**. Single-flight client cache (`getCachedCareerDescription`, `loadCareerDescription`, `clearCareerDescriptionCache`).
- `frontend/src/screens/SetYourCourseScreen.tsx` — sparkle click triggers cache-first fetch; passes `careerDescription` prop into `GemmaChat`.
- `frontend/src/components/menu/GemmaChat.tsx` — accepts `careerDescription?: CareerDescription | "loading" | "error" | null`; renders header card with three states (skeleton, populated with optional Tier B/C disclaimer, error → omit).

## Tests added (38)

| Surface | New | Notes |
|---------|-----|-------|
| `backend/tests/services/test_career_description.py` | 19 | Tier A/B/C/D anchor selection; single-flight cache; transport/parse/voice retry tree with strengthened-prompt assertions; length and task-count bounds. |
| `backend/tests/routers/test_careers_router.py` | 4 | Endpoint happy / unavailable (502) / invalid SOC (422) / missing query param (422). |
| `backend/tests/routers/test_pdf_export.py` | 3 | Lazy persist via `state.update_build`; lazy failure renders without section; lazy-persist-uses-update-build path. |
| `backend/tests/services/test_pdf_export.py` | 4 | Section rendered when populated; skipped when missing; Tier B/C disclaimer present; Tier A no disclaimer. |
| `backend/tests/services/test_builds.py` | 3 | Eager spawn attaches; eager `CareerDescriptionUnavailable` → `None`; unexpected exception → `None`. (Plus harness updated to expect 9-coroutine fan-out.) |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | 2 | Sparkle click dispatches fetch; cache hit skips re-fetch. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | 3 | Populated card renders; loading skeleton; error sentinel omits card. |

## Final verification (per `@fp-builder` 2026-05-07 23:40)

| Check | Result | Notes |
|-------|--------|-------|
| Backend ruff | PASS | (3 round-1 fixes) |
| Backend mypy | PASS | 11 pre-existing errors in `routers/builds.py`; net **−1** vs. pre-spec baseline. No new errors introduced. |
| Backend pytest | PASS | **1793 / 0 / 0 / 1793** |
| Frontend tsc | PASS | (4 round-2 fixes for `AskScope.career` `build_ids` literal-tuple type) |
| Frontend vitest | PASS | **871 / 0 / 0 / 871** |
| Frontend Vite build | PASS | 891 modules, 1.60s |

## Reviews

| Stage | Reviewer | Verdict |
|-------|----------|---------|
| Architecture | `@fp-architect` | CHANGES REQUESTED → spec amended → conditions resolved |
| Data | `@fp-data-reviewer` | CHANGES REQUESTED → spec amended → conditions resolved (tier ladder adopted) |
| Design Vision | `@fp-design-visionary` | DELIVERED (§3 filled with Brightpath spec for both surfaces) |
| Voice | `@fp-copywriter` | DELIVERED (3 system prompts + 2 disclaimers in §10) |
| Design Audit | `@fp-design-auditor` | **APPROVED** — every token validated against DESIGN.md; no new fonts, colors, or hardcoded values. |
| Code Review | `@faang-staff-engineer` | **APPROVED** — 4 moderate non-blocking findings logged for post-hackathon. |

## Architectural conflict resolved

The architect's §5 condition 7 ("raise CareerDescriptionUnavailable when both lists are empty, without invoking Gemma") was rejected in favor of the data reviewer's tiered-fallback recommendation (Tier A → B → C → D). The data reviewer demonstrated that 7% of student paths — including paramedics, EMTs, cardiologists, financial analysts, special-education teachers — would silently lose the "About this career" section under the binary-raise contract. Project rule "no path is out of scope" governs.

## Code review findings (all moderate, non-blocking)

1. **Eager fanout has no top-level `wait_for`.** Decision row 15 explicitly waives this; row 8's "8s budget" claim is now stale. Reconcile in spec post-hackathon.
2. **`_resolve_future` catches `BaseException`.** Anti-pattern that converts CancelledError to a regular future exception. Only matters at shutdown.
3. **Failure-eviction defeats the rate-limit guard under sustained outage.** Add a short negative-cache TTL post-hackathon.
4. **Frontend cache is keyed on SOC alone vs backend `(soc, prompt_version)`.** Bumping `_PROMPT_VERSION` won't invalidate FE caches until reload. Acceptable for hackathon.

## Out of scope (deferred)

- Surfacing `CareerDescription` on `BuildResultsScreen` or `FutureScreen` (data lives on Build; cheap follow-up).
- Pre-warming the cache for popular SOCs at server startup.
- Persisting the SOC cache to disk across restarts.
- Localization to non-`en` locales.
- Editing the description after generation.
