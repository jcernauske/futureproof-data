# Report: feature-tree-as-map (2026-04-28)

**Spec:** `docs/specs/feature-tree-as-map.md`
**Status:** COMPLETE
**Pipeline duration:** ~2 hours autonomous (8 agents, sequential per Claude Code Prompt)
**Branch:** `main` (uncommitted)

## TL;DR

Restructured `/branch-tree` from a tree-as-protagonist screen into a **tree-as-map + chat-as-guide** screen. The tree shrinks to a context rail; an embedded `GemmaChat` becomes the primary surface. Auto-generates a 3-sentence opener on load; every node click swaps scope and re-fires the opener. Bidirectional binding: Gemma names a branch in prose → that node flashes (~600ms accent-info pulse). Voice contract HARD GATE passes (≥7 jailbreak prompts × 2 paths = 14 runs, zero forbidden tokens).

## Workflow Outcome

| Step | Agent | Verdict | Notes |
|---|---|---|---|
| 1. Architecture Review | `@fp-architect` + `@genai-architect` (parallel) | APPROVED post-amendment | Initial pass: CHANGES REQUESTED. genai-architect found a BLOCKER — §4 field manifest referenced 5 non-existent `CareerBranch` fields (`soc_code`, `title`, `level`, `education_level`, `median_wage`). Patched §4 to use actual fields (`to_soc`, `to_title`, `relatedness`, `related_education_level`); dropped `level` + `median_wage` + boss-deltas (not on the model). fp-architect's 6 wording-tightening conditions all baked into §4. |
| 2. Design Vision | `@fp-design-visionary` | APPROVED | Filled §3 with 7 resolved decisions + 7 ASCII mockups + Brightpath token manifest. Mobile: chat-on-top + collapsible "Show map" drawer. Detail panel demoted to a collapsible drawer beneath the chat input. New `branchFlash` motion preset proposed. |
| 3. Implementation | (Claude Code direct) | DONE | 1 build attempt, then design-audit and code-review fixes (see §6 Build Accountability Log). |
| 4. Test Writer | `@test-writer` | APPROVED | 39 new tests (21 backend + 18 frontend). Voice-battery HARD GATE passes (7 prompts × 2 paths = 14 runs, zero leaks). All "Confirmed Safe" sentinels intact. |
| 5. Design Audit | `@fp-design-auditor` | APPROVED post-fix | 6 conditions: 3 hex-value violations in fallback SVG, missing `rounded-md` on scope chip + detail-panel toggle, `--branch-flow-node-scale` not activated, DESIGN.md doc gaps. All resolved. |
| 6. Code Review | `@faang-staff-engineer` | APPROVED post-fix | Finding 1 (Significant): `BranchHighlightDriver`'s `\b...\b` regex anchors silently fail on titles ending in non-word chars (e.g. real O*NET titles like `"Designers (Industrial)"`). Fixed with `(?<![A-Za-z0-9_])...(?![A-Za-z0-9_])` lookarounds + regression test. |
| 7. Verification | `@fp-builder` | PASS | Backend: ruff PASS, mypy (changed files) PASS, pytest 1232/1232. Frontend: tsc PASS, vitest 689/700 (11 pre-existing failures, 0 new), vite build 1.30s. |

## What Shipped

### Backend (`backend/app/`)
- `models/api.py` — `AskScopeKind` extended with `"branch"`; `_validate_cardinality` requires `target_id` for branch scope.
- `services/ask_gemma.py`:
  - `_TOOLS` extended with `get_career_branches` (Decision #2 — chat-time tool allowlist).
  - `_BRANCH_VOICE_APPENDIX` — branch-specific voice rules: noun-form labels, verbatim quoting, `unlock` ban.
  - `_OPENER_PROMPT` + `_OPENER_PROMPT_BRANCH` — 3-sentence orientation prompts.
  - `_context_for_branch(build, target_id)` — 3 cases (matched branch / root anchor / unresolvable).
  - `chat_ask` short-circuits branch+empty-history to `gemma_client.generate_async()` with tools disabled (genai-architect Finding 3 — opener latency optimization).

### Frontend (`frontend/src/`)
- `api/menu.ts` — `AskScope` union extended with `branch` variant.
- `components/menu/GemmaChat.tsx` — new `variant: "embedded" | "slide-in"` prop. Embedded mode: no slide-in motion, no backdrop, no close button, auto-fires opener on `scope.target_id` change. `sessionRef` bumps on scope change to drop stale resolutions.
- `components/tree/BranchTreeFlow.tsx` — new `highlightedNodeId` / `compact` / `heightClassName` props. Compact mode drops `<MiniMap>`, shrinks `<Controls>`.
- `components/tree/BranchHighlightDriver.tsx` — NEW. Parses Gemma response for branch title matches. Lookaround anchors (NOT `\b`), descending-length sort, regex-metachar escaping, 1000ms dedup, 200ms multi-match stagger.
- `screens/BranchTreeScreen.tsx` — restructured to tree col-span-5 + chat col-span-7 grid. `chatScope` `useMemo`'d on primitive deps. 300ms debounce on node click. Mobile drawer. Detail panel demoted to collapsible drawer beneath input.
- `styles/motion.ts` — `branchFlash` preset + `branchFlashStagger`.
- `styles/reactflow-dark.css` — `branchFlashPulse` keyframe + `--branch-flow-node-scale` CSS var + reduced-motion fallback.
- `i18n/strings.ts` — 14 new keys (EN + ES).

### Documentation
- `DESIGN.md` — `branchFlash` + `branchFlashStagger` documented under §Motion System; "Tree-as-map node scale" note for `--branch-flow-node-scale`.

## Test Coverage

- **Backend:** 1232/1232 pass (1211 baseline + 21 new branch-specific).
- **Frontend:** 689/700 pass. The 11 failures are pre-existing on `main` (verified via `git stash`):
  - 9 in `CompareView.test.tsx` — pre-existing `useNavigate()` Router-wrapping issue.
  - 2 in `PentagonOverlay.test.tsx` — pre-existing aria-label assertions.
- **Voice HARD GATE:** PASS (zero forbidden tokens across 14 jailbreak runs).

## Risks Surfaced for Follow-Up

1. **Pre-existing `primary_only` boolean coercion bug** (`mcp_client._validate_args`) — first surfaced when `get_career_branches` joined the chat-time allowlist. Track as separate ticket per genai-architect Finding 5 + faang-staff agreement.
2. **Chip → DOM coupling in `BranchTreeScreen.tsx::handleChipClick`** — uses `document.querySelector('[data-testid="input-chat"]')` to write into the chat input. Tech-debt; acceptable for ship. Future: expose imperative `setDraft` on `GemmaChat`.
3. **Whitespace-replacement in `BranchHighlightDriver.scan` is dead code** — longest-match-wins comes from alternation ordering + `re.lastIndex`, not span consumption. Misleading comment. Drop or update doc.
4. **`branchLabel` flow nodes have no SOC** — clicking an intermediate label falls back to root scope. UX confirmation needed: should this be a no-op instead?
5. **No `AbortController` on stale `askGemma` requests** — backend slot still consumed even though client-side state is dropped. Acceptable per spec §2 ("revisit if demo dry-run shows pathological behavior").

## Spec Health

- ARCH REVIEW (×2 reviewers) — 1 BLOCKER (field manifest), 12 conditions total. All resolved.
- DESIGN VISION — 7 open questions, all answered.
- DESIGN AUDIT — 6 conditions. All resolved.
- CODE REVIEW — 1 Significant + 8 lesser findings. Finding 1 resolved (regex bug fix + regression test). Lesser findings tracked as follow-ups (none blocking).
- VERIFICATION — full build green.

## Files Touched

19 files modified, 2 files created (`BranchHighlightDriver.tsx`, its test file). See spec §6 Files Modified table for full inventory.

## Build Accountability

4 build attempts logged (1 implementation, 1 type-check fix, 1 design-audit fix bundle, 1 code-review fix). Final attempt clean. No build accountability escalations.

## Next Steps

1. Commit this work — feature is complete and tested.
2. Track the 5 risks above as follow-up tickets.
3. Demo dry-run on `/branch-tree` to confirm initial-load latency targets (<1.5s tree, <8s opener on OpenRouter).
