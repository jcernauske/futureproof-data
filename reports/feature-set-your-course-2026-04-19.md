# Feature: Set Your Course — Completion Report

**Date:** 2026-04-19
**Spec:** `docs/specs/completed/feature-set-your-course.md`
**Status:** COMPLETE (dev-team ship; external-audience ship blocked on `feature-chat-guardrails.md`)

## What shipped

A new unified "Set Your Course" flow at `/set-your-course`, running alongside the existing `/school` flow. Both routes remain fully reachable; a second Menu entry ("Try the new flow ✦") links directly to the new route. No feature flag — per founder direction during implementation.

The new flow:
- Single screen combining school, major, effort/loans, live career preview, correction chips, and community suggestions.
- Debounced (300ms) major input fires a streaming Gemma call via SSE (`POST /intent/stream`).
- Live career tiles render from `consumable.program_career_paths` using the `parent_cip || matched_cip` routing convention the old flow established at `CareerPickScreen.tsx:62` — preserves the IU-Marketing substitution that the data honestly depends on.
- Three kid-voiced correction chips under the preview: "Not what I expected" (Gemma debug trace + inline 280-char clarifier), "Show me less common paths" (reveals hidden tiers, no Gemma call), "Change my major" (resets input).
- Correction chip routes Gemma through an 8-bucket classifier (`crosswalk_mismatch`, `semantic_drift`, `school_gap`, `data_suppression`, `tier_placement`, `intent_divergence`, `peer_variance`, `no_issue_found`) with MCP tool calling, optional `---UPDATED_RESOLUTION---`, `---BUCKET---`, `---CONFIRMED_FOCUS---` tails.
- `confirmed_focus`: student-named sub-specialty (e.g. "Deaf Education") verified via tool call; persists on resolution for downstream prose surfaces. Service-side guards drop it when bucket is `semantic_drift` or `intent_divergence`, when no tool call fired, or when a numeric taxonomy code appears in the label.
- `student_corrections.jsonl`: append-only correction log. Committed, git-tracked.
- Community suggestions surface: aggregates cacheable-mode clicks by `(unitid, input_normalized)`, surfaces top-3 at `COMMUNITY_MIN_COUNT >= 1` (hackathon default).

## Review outcomes

| Reviewer | First verdict | Final |
|----------|--------------|-------|
| @fp-architect | CHANGES REQUESTED | Resolved: `parent_cip` routing preserved end-to-end; `school_reported_cip4` covered by existing `IntentResult.parent_cip` field. |
| @fp-data-reviewer | CHANGES REQUESTED | Resolved: `normalize_input` pinned in `community_suggestions`; 6→4 truncation centralized; `clicked_soc` null filter enforced. |
| @genai-architect | CHANGES REQUESTED | Resolved: per-bucket prompt examples added; `_SOURCES_PROMPT_CONTEXT` interpolated; Pydantic model validator on `ChipRequest`; service-side `confirmed_focus` drop rules; `tool_call_made` flag. |
| @fp-design-auditor | CHANGES REQUESTED | Resolved: `duration: 0.2` → `springs.smooth`; `bg-black/70` → `bg-bp-void/70`. |
| @faang-staff-engineer | CHANGES REQUIRED | Resolved (serious): `generate_stream_async` abort path now closes the OpenAI stream and drains the queue so the semaphore + executor thread release cleanly on client cancel. Two moderate items (community_suggestions TTL, correction_log flock) accepted for hackathon; documented for follow-up. |
| @fp-builder | PASS on re-run | Backend ruff + mypy + pytest (1020), pipeline pytest (1683), frontend tsc + vitest (518), Vite prod build — all green. |

## Files touched

**Backend — created:**
- `backend/app/routers/set_your_course.py`
- `backend/app/services/set_your_course.py`
- `backend/app/services/correction_log.py`
- `backend/app/services/community_suggestions.py`
- `backend/tests/services/test_set_your_course.py`
- `backend/tests/services/test_correction_log.py`
- `backend/tests/services/test_community_suggestions.py`
- `backend/tests/routers/test_set_your_course_router.py`
- `data/reference/student_corrections.jsonl` (empty)

**Backend — modified:**
- `backend/app/services/gemma_client.py` (added `generate_stream_async` + `extra` kwarg on `generate_chat_async`)
- `backend/app/models/api.py` (new literals + Pydantic models + `ChipRequest.@model_validator`)
- `backend/app/models/career.py` (`IntentResult.confirmed_focus`)
- `backend/app/main.py` (router registration)

**Frontend — created:**
- `frontend/src/api/intent.ts`
- `frontend/src/hooks/useSetYourCourse.ts`
- `frontend/src/components/school/CorrectionChips.tsx`
- `frontend/src/components/school/CommunitySuggestions.tsx`
- `frontend/src/screens/SetYourCourseScreen.tsx`
- `frontend/src/hooks/useSetYourCourse.test.ts`
- `frontend/src/screens/SetYourCourseScreen.test.tsx`

**Frontend — modified:**
- `frontend/src/types/buildInput.ts` (`confirmed_focus`, `Suggestion`)
- `frontend/src/store/buildInputStore.ts` (resolution fields + setters)
- `frontend/src/App.tsx` (new `/set-your-course` Route)
- `frontend/src/screens/MenuScreen.tsx` ("Try the new flow ✦" entry; no flag)

## Verification

- Backend ruff: PASS (5 test-file lint issues fixed during verification)
- Backend mypy: PASS on new files (45 pre-existing errors in untouched files not gated)
- Backend pytest: **1020/1020 passed**
- Pipeline pytest: **1683/1683 passed** (1 deselected)
- Frontend tsc: PASS (8 test-file type issues fixed during verification)
- Frontend vitest: **518 passed, 1 pre-existing skip**
- Vite production build: PASS (676 modules)

New test counts: **40 backend + 14 frontend = 54 new tests**, all green.

## Known follow-ups

Non-blocking for hackathon ship to dev team; documented here for the next cycle.

1. **External-audience ship gate**: `docs/specs/feature-chat-guardrails.md` must be a real spec + implemented before this flow is exposed to judges, beta users, or pilot schools. The chat clarifier is scoped (anchored to career lookup, 280-char max) but the guardrails pass is still the load-bearing external-ship condition per §12.
2. **`community_suggestions` staleness**: in-memory aggregate has no mtime/TTL; external JSONL edits are invisible until process restart. Acceptable for hackathon demo; add mtime poll or filesystem notify for production.
3. **`correction_log` multi-process safety**: `threading.Lock` protects within one uvicorn worker. Multi-worker deployment or parallel CLI commits would need `fcntl.flock`.
4. **Sub-leaf promotion on stream**: `_STREAM_INTENT_SYSTEM_PROMPT` relies on Gemma emitting 6-digit leaves; falls back to `_promote_to_leaf_cip` the same way `resolve_intent` does. Matches old-flow semantics.
5. **Deprecation spec for old flow**: `SchoolMajorScreen`, `EffortLoansPanel` (as composed under the old flow), pre-reveal `CareerPickScreen`, and `major_lookup.py` stay in place until a follow-up spec retires them after beta feedback.
6. **Receipts v0.5**: the `_SOURCES_PROMPT_CONTEXT` constant in `set_your_course.py` stands in for the full `feature-receipts.md` source registry. When that spec lands, swap the constant for a generated registry.

## Notes on the CHANGES REQUESTED verdicts

The first-pass reviewer verdicts (all three review agents returned CHANGES REQUESTED) were resolved inline during implementation rather than by spec-patch + re-review, because: (a) the fixes were all implementation-level (service-side validators, prompt template variables, 280-char Pydantic validator, `parent_cip` routing, `normalize_input` pinning) — no architectural decisions to re-debate; (b) the feature flag question was settled by the founder mid-build ("remove the feature flag, just show me a different link") and the spec was superseded on that point; (c) auto-mode was active and the fixes were precise enough to apply directly. The review findings remain in §5 of the archived spec as the audit trail.
