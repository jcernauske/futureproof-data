# Feature: /future Tree Enhancements (9-feature bundle) — Completion Report

**Status:** COMPLETE
**Date:** 2026-05-01
**Branch:** career-path-enhancements
**Spec:** `docs/specs/feature-future-tree-enhancements.md`
**Hackathon deadline:** 2026-05-18

## What Shipped

Eight in-scope enhancements from the original 11-item brainstorm. Three items were cut/deferred (documented in §10 of the spec) and stayed out of scope.

| Tier | Enhancement | Status |
|------|------------|--------|
| T1.1 | Edge labels with the dominant delta as a pill | Shipped |
| T1.2 | Four "tour" chips above the tree (silent flash) | Shipped |
| T1.3 | Mini-compare delta strip on SelectedNodeCard | Shipped |
| T1.4 | Selection breadcrumb with ghost-state persistence | Shipped |
| T2.1 | SURVIVES boss-outcome filter row (3 chips) | Shipped |
| T2.2 | Relatedness gradient on edges (rank 1..20) | Shipped |
| T2.3 | "What it takes" 3-bullet block on SelectedNodeCard | Shipped |
| T3.1 | Stage axis labels (ghost watermarks) | Shipped |
| T2.4 | "Make this my path" CTA | Cut (§10) |
| T3.2 | "What changed?" return banner | Cut (§10) |
| T3.3 | Task-overlap chip via MCP | Deferred post-hackathon (§10) |

## Agent Pipeline Results

| Step | Agent | Verdict |
|------|-------|---------|
| Architecture review | @fp-architect | APPROVED |
| Data review | @fp-data-reviewer | CHANGES REQUESTED → all 5 changes incorporated into spec + code |
| Design vision | @fp-design-visionary | All 8 enhancements LOCKED in §3 |
| Copy | @fp-copywriter | 49 keys × en/es/ar in §3 Copy Bundle |
| Implementation | Claude Code | 5 PRs landed across PR1–PR5 |
| Tests | @test-writer | 50+ tests added across 6 files |
| Design audit | @fp-design-auditor | CHANGES REQUIRED → 6 violations all fixed |
| Code review | @faang-staff-engineer | CHANGES REQUIRED → 1 blocker + 3 serious all fixed |
| Verification | @fp-builder | TS error in new test file → fixed; final state green |

## Code Footprint

**Backend (3 lines of net logic + serialization extension):**
- `backend/app/services/career_tree.py` — `TreeNode.relatedness: int | None` field added; populated from `as_int(row.get("best_index"))`
- `backend/app/routers/branches.py` — `_node_to_dict` serializes 3 new fields (`experience_years`, `experience_tier`, `relatedness`)

**Frontend (10 new files + extensions to 4 existing):**
- New: `data/edgeLabel.ts`, `data/tourRanking.ts`, `data/bossFilter.ts`
- New: `components/tree/MiniCompareStrip.tsx`, `TourChipRow.tsx`, `Breadcrumb.tsx`, `BossFilterRow.tsx`, `WhatItTakes.tsx`, `StageAxisLabels.tsx`, `flow/EdgeWithLabel.tsx`
- Extended: `types/tree.ts` (3 fields), `data/treeFlowLayout.ts` (relatedness gradient + edge data routing), `components/tree/SelectedNodeCard.tsx` (strip + bullets), `components/tree/BranchTreeFlow.tsx` (custom edge type + StageAxisLabels mount), `screens/FutureScreen.tsx` (orchestration)
- `i18n/strings.ts` — 49 net-new keys × 3 locales = 147 entries

## Test Coverage

**Frontend:** 839 vitest tests pass (was 766 before this spec — net +73 tests)
- New: `data/edgeLabel.test.ts` (20), `data/tourRanking.test.ts` (12), `data/bossFilter.test.ts` (13), `components/tree/Breadcrumb.test.tsx` (15)
- Extended: `components/tree/SelectedNodeCard.test.tsx` (+12), `screens/FutureScreen.test.tsx` (+1 — breadcrumb persistence regression that would have caught staff-engineer Finding #1)

**Backend:** 1298 pytest tests pass (was 1295 — net +3 tests)
- Extended: `tests/services/test_career_tree.py` — relatedness propagation (int / float-coerce / null cases)

**Verification (final):** ruff PASS, mypy PASS (no new errors), pytest 1298/1298, TypeScript clean, vitest 839/839, Vite production build PASS.

## Decisions Locked During the Build

These decisions were made by author + agents during execution; all preserved in the spec.

1. **Backend payload extension consolidated into PR1** rather than a standalone PR4. T1.1's priority chain needs `relatedness` and `experience_*` on TreeNode for the priority chain to fire correctly, so the backend extension shipped together with the edge labels.

2. **T2.1 SURVIVES trimmed from 5 → 3 chips** (boss_loans + boss_ceiling dropped) per @fp-data-reviewer. Empirical test against real SOC 15-1252 data showed both resolved to "unknown" for ~100% of non-root nodes — they would have been dead chips that hide every branch.

3. **T2.2 gradient anchored at rank 1..20** instead of 1..50. Real ranks cap at 20 (Silver tier ceiling: Primary-Short 1-5, Primary-Long 6-10, Supplemental 11-20). Null relatedness clamps to rank 20 (most translucent end) per architect recommendation.

4. **T2.4 + T3.2 cut, T3.3 deferred** — confirmed in §11 Open Questions resolution. Out of scope for May 18 hackathon deadline.

5. **Breadcrumb snapshot wipe moved out of the cascade** (staff-engineer Finding #1). The snapshot only clears on user-initiated actions (`handleSelectNode(null)` for pane click, `handleBreadcrumbClick(root)` for root segment click). The auto-drop when a filter hides the selected node no longer cascades into a snapshot wipe — that's what powers the ghost-state UX.

## Outstanding Items / Follow-ups

These were noted by reviewers as nice-to-have but not blockers:

- **FutureScreen test fixtures still set `boss_loans: "win"` / `boss_ceiling: "win"`** (data-reviewer Finding #4 / staff-engineer Finding #5). Not breaking — the chips were trimmed to 3, so the unrealistic loans/ceiling values aren't exercised anywhere. Worth aligning with real backend distribution in a future tidy pass.

- **Missing P1 integration tests** for `tour_chip_flashes_top_3` and `boss_filter_row_renders_3_chips` (staff-engineer Finding #6). The unit-level coverage in `tourRanking.test.ts` and `bossFilter.test.ts` exercises the underlying logic; the missing tests are about the FutureScreen wiring. Added the most important one (`breadcrumb_persists_across_filter_toggle`) explicitly as the regression for Finding #1.

- **T2.4 "Make this my path"** — strongest post-hackathon spec candidate per §10 + author note in §11. Atomic re-root requires a new backend endpoint with chat scope + build identity + stat baseline switching atomically.

- **T3.3 task-overlap chip** — second-strongest post-hackathon candidate. Caching layer + overlap algorithm is its own subspec.

- **T3.2 return banner** — re-evaluate when there's a real `gold.promoted_at` cycle the student would actually notice between visits.

## Files Modified

Summary in spec §6 Implementation Log. Key surfaces:

- `backend/app/services/career_tree.py`, `backend/app/routers/branches.py`
- `frontend/src/types/tree.ts`, `frontend/src/i18n/strings.ts`
- `frontend/src/data/{edgeLabel,tourRanking,bossFilter,treeFlowLayout}.ts`
- `frontend/src/components/tree/{Breadcrumb,BossFilterRow,MiniCompareStrip,SelectedNodeCard,StageAxisLabels,TourChipRow,WhatItTakes}.tsx`
- `frontend/src/components/tree/{BranchTreeFlow,flow/EdgeWithLabel}.tsx`
- `frontend/src/screens/FutureScreen.tsx`
- `frontend/src/styles/reactflow-dark.css` (T1.1 pill styling)
- `frontend/src/api/mockTree.ts` (aligned boss outcomes with real distribution + new fields)
- Test files: 6 new + 4 extended

## Build Accountability

One TypeScript error introduced in the new `edgeLabel.test.ts` (non-null assertion didn't narrow under TS strict mode). Caught by @fp-builder, fixed in two lines, re-verification clean. Zero other build incidents across the whole spec.
