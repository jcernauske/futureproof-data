# feature-tree-horizon-map — Completion Report

**Spec:** `docs/specs/feature-tree-horizon-map.md`
**Status:** COMPLETE
**Date:** 2026-04-29
**Branch:** `career-path-enhancements`

## What shipped

Replaced `/branch-tree`'s React Flow dendrogram with a 3-lane horizon map of clickable chips, bucketed by **how much more education each branch requires relative to the student's current build**. Lanes: **Lateral** (same degree or less), **Step Up** (one credential more), **Long Climb** (two or more credentials more).

The chat column from `feature-tree-as-map.md` is unchanged. Bidirectional flash binding from chat → chip preserved via the relocated `branchFlashPulse` keyframe and the `chip-${to_soc}` className contract.

## Why

The just-shipped `feature-tree-as-map.md` solved orientation by demoting the tree to a context rail and putting Gemma in the foreground — but kept the React Flow dendrogram. With ~22 L1 branches and dense child rows, the dendrogram required aggressive `fitView` zoom-out: nodes rendered ~5px tall, only one branch fit in viewport, and the bidirectional flash highlight silently failed because matched nodes landed off-screen.

The new horizon map flattens to L1 chips capped at 6 per lane, so every chip that *could* flash is in viewport. Resolves the pan-to-flash problem by architecture, not by adding a pan mechanism.

## Files

**Created (4):**
- `frontend/src/data/horizonLayout.ts` — pure-function lane assignment + chip helpers (`assignLane`, `eduRank`, `relatednessTier`, `sortBranchesInLane`, `bucketBranches`, `dominantStatDelta`, `truncateTitle`).
- `frontend/src/components/tree/BranchHorizonMap.tsx` — composes 3 lane rows + the "Hide supplemental" toggle + per-lane `+N more` expand.
- `frontend/src/components/tree/BranchHorizonChip.tsx` — single chip: title, dominant stat-delta badge, experience badge, unlock footer, relatedness color bar.
- `frontend/src/styles/horizonMap.css` — lane / chip / overflow / filter / empty-state styling + relocated `branchFlashPulse` keyframe.

**Modified (4):**
- `frontend/src/screens/BranchTreeScreen.tsx` — dropped `flowNodeMap` cascade, drawer mount, and L0/L2/L3 candidate set; added `chipBranchMap`; re-keyed `highlightCandidates` to L1-only chip ids; routed scope/title lookups through the new map.
- `frontend/src/i18n/strings.ts` — removed `tree.seeData` / `tree.hideData`; added 22 new keys EN+ES (lane labels + subtitles + empty-state copy + filter toggle + experience/level-unknown badges).
- `frontend/src/screens/BranchTreeScreen.test.tsx` — re-mocked `BranchHorizonMap`; added `makeBranches` fixture; re-baselined `region-branch-horizon` testid + `chip-branch-${soc}` selectors.
- `DESIGN.md` — replaced "Tree-as-map node scale" entry with "Horizon Map" entry.

**Deleted (8):**
- `frontend/src/components/tree/BranchTreeFlow.tsx`
- `frontend/src/data/treeFlowLayout.ts`
- `frontend/src/components/tree/flow/Flow{Root,BranchLabel,Career,Endpoint}Node.tsx` (4 files)
- `frontend/src/components/tree/TreeNodeDetailPanel.tsx` + `.test.tsx`
- `frontend/src/styles/reactflow-dark.css`

## Tests

- 76 new tests across 3 files: `horizonLayout.test.ts` (37), `BranchHorizonChip.test.tsx` (24), `BranchHorizonMap.test.tsx` (15).
- `BranchTreeScreen.test.tsx` re-baselined: 18 tests, all green.
- Full vitest suite: **748 / 759 passing**. The 11 failures match exactly the documented pre-existing failures from `feature-tree-as-map.md` §7 verification — 9 in `CompareView.test.tsx`, 2 in `PentagonOverlay.test.tsx`. Verified via `git stash` during Step 3 — they fail identically without this spec's changes.
- Backend pytest: 1232 / 1232 passing (sentinel only — backend untouched).

## Verification (Step 7)

| Check | Result |
|-------|--------|
| Backend ruff | ✅ Pass |
| Backend mypy | ✅ Pass (71 pre-existing errors on main, zero backend files in this diff) |
| Backend pytest | ✅ Pass (1232 / 1232) |
| Frontend tsc --noEmit | ✅ Pass (exit 0) |
| Frontend vitest | ✅ Pass (748 / 759, 11 pre-existing failures unchanged) |
| Frontend Vite production build | ✅ Pass (540 modules, 1.18s) |

## Spec evolution

The spec went through three substantive revisions during execution:

1. **Architect re-review (5 conditions, all CLOSED):** drawer fate, `flowNodeMap` cascade, dead-code deletions for `treeFlowLayout.ts` + four `Flow*Node.tsx` files + `reactflow-dark.css`, and an explicit Out-of-Scope bullet for L2/L3 title flashes.

2. **Implementation-time spec corrections (D#16, D#17):** while grounding code against the actual API contract, three field-semantic mismatches surfaced. Data source for chips is `build.branches`, not `treeData.tree.children` (different shape entirely). `relatedness_tier` is not on the API contract — re-derived in TS from `relatedness` (which is `best_index`). `related_experience_tier` is the silver-zone column name; the API surfaces it as `experience_tier`. Side correction: the within-lane tiebreak sort is `relatedness ASC` not DESC (since `relatedness` is `best_index` where 1 = most related). Codified as Decisions 16 + 17.

3. **Step 5 + Step 6 minor fixes (8 changes):** 4 design-audit CSS token fixes (border-radius tokens, eyebrow color, lane accent radius, missing shadow); 4 code-review fixes (deselect-on-filter `useEffect`, collapse-button overflow gate, `useMemo` dep narrowings).

## Out of scope (deliberate)

- **Detail drawer ("See data for {branch}")** — removed entirely (D#13 reverses `feature-tree-as-map.md` D#3). Chat is the deeper-data path now; `get_occupation_data(soc)` is the tool.
- **L2/L3 title flashes** — candidate set is L1-only. Gemma quoting a sub-specialization or terminal credential won't flash any chip. Acceptable v1 trade; future `feature-horizon-flash-aliasing.md` (TBD) can alias L2/L3 → parent L1 if needed.
- **Tree depth restoration (L2/L3 navigation)** — chip-driven descent only. Future `feature-horizon-drill-down.md` (TBD).
- **Re-bucketing for advanced students** — Master's-level builds will see most things in Lateral or Step Up. Acceptable for v1; future `feature-horizon-rebalance.md` (TBD).
- **Auto-pan-to-flash** — resolved by architecture (cap-at-6 means every chip is in viewport).
- **Mobile horizon-map redesign** — inherited drawer pattern from `feature-tree-as-map.md` unchanged.

## Voice contract

Untouched. Backend services, MCP tool allowlist, `_BRANCH_VOICE_APPENDIX`, `_OPENER_PROMPT_BRANCH`, and the entire 18-prompt voice battery + 7 branch jailbreaks remain green as a sentinel.

## Next steps

None — spec is COMPLETE. The four UX/perf nits raised by the code reviewer (Findings 1, 2, 3, 4) all landed in this commit before ship.

## Agent pipeline

| Step | Agent | Result |
|------|-------|--------|
| 1. Architecture Review | `@fp-architect` | APPROVED (after one round of CHANGES REQUESTED + 5 spec edits) |
| 2. Design Vision | `@fp-design-visionary` | Mockup approved by Jeff 2026-04-29 |
| 3. Implementation | Claude Code (general) | All file changes per §4; 8 files deleted, 4 created, 4 modified |
| 4. Testing | `@test-writer` | 76 new tests, all green |
| 5. Design Audit | `@fp-design-auditor` | CHANGES REQUIRED (4 minor CSS token fixes) → Resolved |
| 6. Code Review | `@faang-staff-engineer` | APPROVED (4 minor UX/perf nits) → All folded in |
| 7. Verification | `@fp-builder` | GREEN |
| 8. Completion | (this report) | COMPLETE |

## Hackathon scope sanity

All work is frontend presentation-layer. Zero backend changes. Zero schema changes. Zero MCP tool changes. The spec's "no backend changes" constraint held end-to-end.

The student-facing change is a substantially better tree column on `/branch-tree`: 3 named lanes instead of one dense dendrogram, every chip in viewport, every flash visible, and personalization via the build's edu rank baked into the lane vocabulary itself.
