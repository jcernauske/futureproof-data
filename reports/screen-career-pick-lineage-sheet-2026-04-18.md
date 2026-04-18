# Report — `/career-pick` Lineage Sheet + Ask-Gemma Chips

**Date:** 2026-04-18
**Spec:** `docs/specs/completed/screen-career-pick-lineage-sheet.md`
**Branch:** `spec/career-pick-lineage-sheet` (parallel worktree, not merged)
**Status:** COMPLETE

## What Shipped

The `/career-pick` screen now shows students where each career path actually leads — not just the first-job snapshot. The top 2/3 is a calm vertical ladder of Common / Less Common / Stretch tiers (2-col card grids). The bottom 1/3 is a new iOS-style `CareerLineageSheet` with three drag-to-resize detents (compact ≈33 vh / medium ≈50 vh / large ≈85 vh) that populates with stage-3 career branches when a student clicks a card.

Inside the sheet, a new Ask-Gemma chip row is always visible. When the student's typed major matches a graduate-track pattern (pre-med, pre-law, pre-vet, pre-dental) AND the expected terminal SOC (physician, lawyer, veterinarian, dentist) isn't on screen, the "Why don't I see [X]?" chip is auto-elevated — styled in Brightpath `accent-alert` with a subtle pulse — as if Gemma read the student's mind. Chip clicks fire `POST /career-pick/ask`, Gemma responds in 4–6 sentences at 6th-grade reading level, and every call lands in `logs/gemma.jsonl` with `call_site="career_pick.ask"` for the audit trail.

No free-form input. Chips only. (§2 Decision #9.)

## Surfaces Touched

**Backend (new):**
- `backend/app/models/career_pick.py` — `CareerPickChip`, `AskCareerPickRequest`, `AskCareerPickResponse`
- `backend/app/services/career_pick_qna.py` — canned-question catalog (7 entries), auto-elevation heuristic, Gemma call with deterministic fallback
- `backend/app/routers/career_pick.py` — `GET /career-pick/chips` + `POST /career-pick/ask`

**Backend (touched):**
- `backend/app/main.py` — register new router
- `backend/app/services/gemma_client.py` — added `extra: dict | None` kwarg to `generate` / `generate_chat` / `generate_async` so call sites can stamp correlation fields onto the shared JSONL record without writing a second record (per code-review F2).

**Frontend (new):**
- `frontend/src/components/CareerLineageSheet.tsx` — the bottom sheet
- `frontend/src/components/BranchChip.tsx` — one branch card
- `frontend/src/components/AskGemmaChipRow.tsx` — chip row with elevated-chip styling + keyboard activation
- `frontend/src/components/AskGemmaResponseCard.tsx` — response card with detent-aware max-height
- `frontend/src/api/careerPick.ts` + `frontend/src/api/mockCareerPick.ts` — chip API + mock
- `frontend/src/api/mockBranches.ts` — branch fixture for `VITE_USE_MOCK_API`
- `frontend/src/types/careerPick.ts` — TS types mirroring backend Pydantic models

**Frontend (touched):**
- `frontend/src/screens/CareerPickScreen.tsx` — outer layout reworked (tiers always `grid-cols-1`, CTA inline, bottom padding reserved for compact detent, chip prefetch on mount, sheet mounted at viewport bottom)
- `frontend/src/components/CareerCard.tsx` — click semantics split: card body → `onExplore` (populates sheet), inline "Pick this path" button → `onSelect` (commits). Fixed HTML-invalid nested interactive elements per code-review F1.
- `frontend/src/components/CareerTierSection.tsx` — added required `onExplore` prop
- `frontend/src/api/tree.ts` — added `getBranchesForSoc(soc)` alongside existing `getTree(buildId)`
- `frontend/src/styles/motion.ts` — 7 new presets (`sheetDetent`, `sheetSnap`, `sheetDragElastic`, `sheetFlingVelocity`, `chipResponseExpand`, `elevatedChipPulse`, `handlePulse`)

## Review Gates

| Gate | Verdict | Notes |
|------|---------|-------|
| @fp-architect | SKIPPED | No new architectural coupling per §2 Decision #1 + spec calibration. |
| @fp-data-reviewer | SKIPPED | No pipeline / stat / crosswalk changes. |
| @fp-design-visionary | APPROVED | §3 authored in full; 7 motion presets defined. |
| @fp-design-auditor | APPROVED (2nd pass) | 6 required fixes landed: F1 GemmaStar on post-click hint, F2 snap-mandatory, F3 right-edge fade-mask, F4 inset insight wash, F5 rounded-full stat pills, F7 detent-aware response max-height, F8 mobile-first padding. |
| @faang-staff-engineer | APPROVED (2nd pass) | 4 serious + 2 moderate findings landed: F1 HTML-invalid nested buttons, F2 duplicate gemma.jsonl records (added `extra` kwarg path on `generate_async`), F3 sheet drag off-screen overshoot, F4 exception-swallowing `ask()`, F5 reduced-motion on peers, F7 DETENT_VH source-of-truth consolidation. Minor follow-ups (F8-F10) accepted as-is. |
| @fp-builder | PASS | ruff clean; mypy baseline (46 pre-existing errors unchanged); pytest 349/349; tsc clean; vitest 430 pass + 2 pre-existing `ProfileScreen.test.tsx` failures on `main`; Vite production build clean. |

## Tests

- **Backend:** 29 new tests — 22 service-level (catalog, heuristic, ask + fallback paths, `extra` kwarg carries call_site + correlation) + 7 router-level (chips, ask 200, unknown chip_id 422, malformed body 422).
- **Frontend:** 45 new tests — 23 CareerLineageSheet (empty/loading/error lifecycle, stale-fetch cancellation, chevron + ArrowKey detents, exported `resolveDetent` pure helper, aria-label/aria-live, auto-promote, chip context forwarding, response swap) + 6 BranchChip + 9 AskGemmaChipRow + 7 AskGemmaResponseCard.
- Total delta: **+74 new tests**, all passing.

## Non-Fixed (follow-up candidates)

- `ProfileScreen.test.tsx` seeded-profile naming — pre-existing failure on `main`. Not this spec.
- `gemma_client.py` has ~46 mypy errors (missing return types, `list[dict]` without type args, etc.) pre-dating this spec. Not in scope here.
- §9 manual smoke deferred to post-merge per parallel-worktree constraint.

## Parallel-Run Discipline

This spec ran concurrently with `docs/specs/feature-gemma-tiered-matching.md` in a sibling worktree. All work committed to `spec/career-pick-lineage-sheet`; no merge to `main`, no push, no PR. The orchestrating session integrates both branches after the companion spec completes.

No `DESIGN.md` or `docs/mockups/brightpath-design-system-v3.html` edits were needed — all Brightpath tokens required already existed, so the append-only parallel constraint on those files was trivially satisfied.

## Commits (in order)

1. `dd0c808` — spec(career-pick): fp-design-visionary fills §3 UI/UX Design
2. `0608718` — spec(career-pick): advance status → IMPLEMENTATION
3. `ae41140` — feat(career-pick): lineage sheet + Ask-Gemma chip row
4. `0b4d0eb` — test(career-pick): 74 new tests for lineage sheet + Ask-Gemma chips
5. `04bdbb8` — fix(career-pick): address fp-design-auditor findings F1-F5, F7, F8
6. `cf13f66` — fix(career-pick): address faang-staff-engineer findings F1-F5, F7

Completion + report commit will follow this file.
