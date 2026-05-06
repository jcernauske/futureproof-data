# Feature: Scope-Aware Ask Gemma Starter Chips

## Claude Code Prompt

```
Read the spec at docs/specs/feature-scope-aware-ask-chips.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (GemmaChat prop threading, tool enablement, scope-chip mapping)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION (UI spec)
   - Invoke @fp-design-visionary to refine the chip row UX per §3
   - Visionary writes to §3: chip visual treatment per scope, responsive behavior, empty-state stagger
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

5. DESIGN AUDIT (UI spec)
   - Invoke @fp-design-auditor for mechanical token/pattern compliance against Brightpath design system
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
   - Generate report to reports/feature-scope-aware-ask-chips-2026-05-05.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-05 |
| Author | Jeff + Claude Code (product partner) |
| Spec Version | 1.0 |
| Last Updated | 2026-05-05 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-ask-gemma.md`, `docs/specs/completed/feature-gemma-trace.md` |

---

## §1 Feature Description

### Overview

Make the Ask Gemma starter chips scope-aware so different pages and entry points show different canned prompts. Today every `<GemmaChat>` instance renders the same hardcoded `STARTERS` array regardless of whether the student opened chat from the build results page, a stat tap, a boss fight, or the compare view. This spec adds a `starters` prop to `GemmaChat` so parent screens pass scope-appropriate chips, and defines the chip sets for each scope kind.

### Problem Statement

The current STARTERS are build-scoped questions about salary geography and career branches. They render even when chat opens from:
- A **stat tap** — where the student wants to understand a specific stat, not ask about salary in different states
- A **boss fight** — where the student wants to understand why they won/lost, not explore career branches
- The **compare view** — where the student is deciding between two builds, not exploring one
- A **skill recommendation** — where the student wants to know how to learn the skill

This mismatch means the chips are noise in most contexts, so students ignore them and face an empty text field. Scope-aware chips teach students what's answerable and reduce friction at the moment of highest curiosity.

Additionally, `get_task_breakdown` is excluded from the Ask Gemma tool set despite rich O*NET data being available (798 occupations with day-to-day activities, burnout drivers, human-edge tasks). Adding it enables the highest-leverage new chips: "What does a day look like?" and outcome-aware boss explanations.

### Success Criteria

- [ ] `GemmaChat` accepts an optional `starters` prop; when provided, it renders those instead of the hardcoded `STARTERS`
- [ ] When `starters` is omitted or empty, the existing `STARTERS` array renders (backwards-compatible)
- [ ] BuildResultsScreen passes build-scope starters when opening chat via the bottom-bar "Ask Gemma" button
- [ ] BuildResultsScreen passes stat-scope starters when opening chat via a stat tap (not the explain-this receipt flow — the general "Ask about this stat" flow)
- [ ] BuildResultsScreen passes boss-scope starters when opening chat via a boss fight tap
- [ ] BuildResultsScreen passes skill-scope starters when opening chat via a skill recommendation tap
- [ ] CompareView passes compare-scope starters when opening chat
- [ ] `get_task_breakdown` is added to `_TOOLS` in `backend/app/services/ask_gemma.py`
- [ ] MenuScreen (my-build) continues rendering the existing `STARTERS` unchanged
- [ ] FutureScreen (branch tree) continues rendering with no starters (embedded variant with openerPrompt)
- [ ] All existing GemmaChat tests pass without modification

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Add optional `starters` prop to `GemmaChat` rather than deriving chips from `scope.kind` internally | Parent screens have the context to pick the right chips (boss outcome, stat code, skill title). GemmaChat stays a dumb renderer. | GemmaChat reads scope internally — rejected because boss-outcome-aware chips need fight result data GemmaChat doesn't have |
| 2 | Keep existing `STARTERS` as the default fallback | MenuScreen passes no scope — its GemmaChat must keep working. The hardcoded starters are proven to trigger 2-3 tool calls per chip (good for demo/judges). | Remove STARTERS entirely — rejected, they're the right chips for my-build's general chat |
| 3 | Add `get_task_breakdown` to `_TOOLS` | Powers "What does a day look like?" (build-scope) and outcome-aware boss explanations. 798 occupations with full O*NET profiles already in gold zone. Low risk — tool is read-only, schema is stable. | Keep it excluded — rejected, the data is there and the chips are thin without it |
| 4 | Do NOT add `get_ai_exposure` to `_TOOLS` | RES stat and Fight AI boss already embed the exposure score. The task-level AI breakdown that matters lives in `get_task_breakdown`. Adding both creates redundant tool calls. | Add both — rejected, `get_ai_exposure` data is already in the build context |
| 5 | Starters are frontend-only — no backend chip catalog for Ask Gemma | Unlike career-pick chips (which have elevation heuristics and need SOC/CIP context from the backend), Ask Gemma starters are static per scope kind. No backend round-trip needed. | Backend `GET /chat/starters?scope=...` — rejected as over-engineering for static strings |
| 6 | Boss-scope chips are outcome-aware (different labels for WIN/LOSE/DRAW) | "Why did I win?" vs "What makes this hard?" matches the emotional state. BuildResultsScreen already has the fight result when opening chat. | Single generic "Tell me about this boss" — rejected, misses the emotional beat |

### Constraints

- GemmaChat is used by 4 parent screens; changes must be backwards-compatible
- Existing STARTERS must not change (they're calibrated for multi-tool-call demo value)
- Chip text must be under ~50 characters to fit in the pill button without truncation on mobile
- No backend API changes — this is a frontend chip-mapping change plus one backend tool enablement

---

## §3 UI/UX Design

> @fp-design-visionary fills this section BEFORE implementation begins.

### Chip Sets by Scope

#### Build-scope starters (bottom-bar "Ask Gemma" on BuildResultsScreen)

| # | Label | MCP tools likely triggered |
|---|-------|---------------------------|
| 1 | "What does a day look like?" | `get_task_breakdown` |
| 2 | "What can I do in 10 years?" | `get_career_branches` |
| 3 | "How does this pay where I live?" | `get_regional_price_parity`, `compare_purchasing_power` |
| 4 | "Is my school good for this?" | `get_schools_for_career` |

#### Stat-scope starters (tap any pentagon stat on BuildResultsScreen)

| # | Label | MCP tools likely triggered |
|---|-------|---------------------------|
| 1 | "How can I improve this?" | `get_career_branches`, `get_occupation_data` |
| 2 | "How does this compare nationally?" | `get_occupation_data` |

#### Boss-scope starters (tap any boss fight on BuildResultsScreen)

Outcome-aware — `BuildResultsScreen` knows the fight result.

| Outcome | Chip 1 | Chip 2 |
|---------|--------|--------|
| WIN | "Why did I win this?" | — |
| LOSE | "What makes this hard?" | "Who wins this fight?" |
| DRAW | "What tipped the scale?" | "Who wins this fight?" |

MCP tools: `get_occupation_data`, `get_task_breakdown` (chip 1); `get_career_branches`, `get_schools_for_career` (chip 2).

#### Skill-scope starters (tap a skill recommendation on BuildResultsScreen)

| # | Label | MCP tools likely triggered |
|---|-------|---------------------------|
| 1 | "Where do I learn this?" | none (Gemma general knowledge + context) |

#### Compare-scope starters (CompareView chat)

| # | Label | MCP tools likely triggered |
|---|-------|---------------------------|
| 1 | "Which one would you pick?" | none (all data in compare context) |
| 2 | "Where does the cheaper one catch up?" | `get_career_branches` |
| 3 | "What's the real cost difference?" | `get_regional_price_parity`, `compare_purchasing_power` |
| 4 | "Which career is safer long-term?" | `get_career_branches`, `get_occupation_data` |

### Mockups

The chip row layout is identical to the existing STARTERS rendering in `GemmaChat.tsx` (lines 562-593): a vertical stack of pill buttons with staggered fade-in, rendered only when `history.length === 0 && !sending`. No visual changes to the chip component itself.

### Interactions

- Tapping a chip sets it as the draft message (same as today — `setDraft(q)`)
- Student can edit the draft before sending or tap send immediately
- After the first message exchange, chips disappear (same as today)

### Responsive Behavior

No changes — existing chip pills already wrap on narrow viewports.

### Brightpath Design References

- Chip styling: existing `.rounded-full bg-bp-surface border border-border-subtle` classes (unchanged)
- Stagger animation: existing `stagger.normal` timing (unchanged)
- Typography: `font-body text-small text-text-secondary` (unchanged)

### Accessibility

No new accessible elements — the chip buttons already have `data-testid` attributes. The only change is what text appears inside them.

---

## §4 Technical Specification

### Architecture Overview

```
BuildResultsScreen ──┐
  handleAskBuild()    │  passes starters=BUILD_STARTERS
  handleAskStat()     │  passes starters=STAT_STARTERS
  handleAskBoss()     │  passes starters=bossStarters(outcome)
  handleAskSkill()    │  passes starters=SKILL_STARTERS
                      ▼
CompareView ──────────┤  passes starters=COMPARE_STARTERS
                      ▼
MenuScreen ───────────┤  passes nothing → falls back to STARTERS
                      ▼
FutureScreen ─────────┤  passes nothing → openerPrompt auto-fires
                      ▼
              GemmaChat
              ├─ starters prop (string[])
              └─ fallback: existing STARTERS array
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/components/menu/GemmaChat.tsx` | Modify | Add optional `starters?: string[]` prop. When provided and non-empty, render those instead of hardcoded `STARTERS`. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Define scope-specific starter arrays. Pass `starters` to `<GemmaChat>` based on which handler opened chat. Track `chatStarters` in state alongside `chatScope`/`chatChipText`. |
| `frontend/src/components/menu/CompareView.tsx` | Modify | Define `COMPARE_STARTERS` array. Pass `starters` to `<GemmaChat>`. |
| `backend/app/services/ask_gemma.py` | Modify | Add `"get_task_breakdown"` to `_TOOLS` tuple (line 93). |

### Data Model Changes

None. No new Pydantic models, no schema changes, no new tables.

### Service Changes

**Backend** — one-line change:

```python
# backend/app/services/ask_gemma.py, line 93
_TOOLS: tuple[str, ...] = (
    "get_career_paths",
    "get_occupation_data",
    "get_regional_price_parity",
    "compare_purchasing_power",
    "get_career_branches",
    "get_schools_for_career",
    "get_institution_aura",
    "get_task_breakdown",          # NEW
)
```

**Frontend** — `GemmaChat` prop addition:

```typescript
// GemmaChat.tsx — add to GemmaChatProps interface
interface GemmaChatProps {
  // ... existing props ...
  /**
   * Scope-specific starter prompts. When provided and non-empty,
   * these render instead of the hardcoded STARTERS. Parent screens
   * own the mapping from scope to starter text.
   */
  starters?: string[];
}
```

Rendering change in the empty-state block (lines 576-589):

```typescript
const effectiveStarters = starters && starters.length > 0 ? starters : STARTERS;
// ... then map over effectiveStarters instead of STARTERS
```

**BuildResultsScreen** — starter arrays and state threading:

```typescript
const BUILD_STARTERS = [
  "What does a day look like?",
  "What can I do in 10 years?",
  "How does this pay where I live?",
  "Is my school good for this?",
];

const STAT_STARTERS = [
  "How can I improve this?",
  "How does this compare nationally?",
];

function bossStarters(outcome: BossOutcome): string[] {
  const chip1 =
    outcome === "win" ? "Why did I win this?"
    : outcome === "lose" ? "What makes this hard?"
    : "What tipped the scale?";
  const chips = [chip1];
  if (outcome !== "win") {
    chips.push("Who wins this fight?");
  }
  return chips;
}

const SKILL_STARTERS = [
  "Where do I learn this?",
];
```

State: add `chatStarters` alongside `chatScope`:

```typescript
const [chatStarters, setChatStarters] = useState<string[] | undefined>();
```

Each handler sets the starters:

```typescript
// handleAskBuild: setChatStarters(BUILD_STARTERS)
// handleAskStat:  setChatStarters(STAT_STARTERS)
// handleAskBoss:  setChatStarters(bossStarters(result))
// handleAskSkill: setChatStarters(SKILL_STARTERS)
```

Pass to GemmaChat:

```typescript
<GemmaChat
  open={chatOpen}
  build={null}
  scope={chatScope ?? undefined}
  chipText={chatChipText}
  starters={chatStarters}
  openerPrompt={chatOpenerPrompt ?? undefined}
  onClose={closeChat}
/>
```

**CompareView** — starter array:

```typescript
const COMPARE_STARTERS = [
  "Which one would you pick?",
  "Where does the cheaper one catch up?",
  "What's the real cost difference?",
  "Which career is safer long-term?",
];
```

Pass to GemmaChat:

```typescript
<GemmaChat
  open={chatOpen}
  build={null}
  scope={compareScope}
  chipText={compareChipText}
  starters={COMPARE_STARTERS}
  onClose={() => setChatOpen(false)}
/>
```

**MenuScreen** and **FutureScreen** — no changes. They don't pass `starters`, so GemmaChat falls back to the existing `STARTERS` array (MenuScreen) or auto-fires `openerPrompt` with no starters visible (FutureScreen).

### Testing Impact Analysis

> **IMPORTANT**: Before finalizing this section, search the test directories for tests related to files being modified.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/components/menu/GemmaChat.test.tsx` | all | Low | GemmaChat gets a new optional prop; existing tests pass no `starters`, so they use the STARTERS fallback — behavior unchanged |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | all | Low | Starter arrays are new state; existing test scenarios don't assert on starter content |
| `frontend/src/components/menu/CompareView.test.tsx` | all | Low | Same — new prop passed but existing tests don't assert on chip text |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| None | — | No existing tests should need modification |

#### Confirmed Safe

All existing GemmaChat, BuildResultsScreen, CompareView, MenuScreen, and FutureScreen tests should pass without modification. The new prop is optional with a backwards-compatible fallback. If any fail, STOP and escalate.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `renders custom starters when starters prop is provided` | Custom starters render instead of STARTERS |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `renders default STARTERS when starters prop is omitted` | Backwards compatibility — STARTERS still render |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `renders default STARTERS when starters prop is empty array` | Edge case — empty array falls back to STARTERS |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `passes build starters when Ask Gemma button is clicked` | Build-scope chips thread through to GemmaChat |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `passes compare starters to GemmaChat` | Compare-scope chips thread through to GemmaChat |

#### Test Data Requirements

No new fixtures needed. Existing build/compare test data is sufficient.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline or data model changes; tool enablement only)

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

### Design Audit (@fp-design-auditor)
**Status:** PENDING
[Filled in by @fp-design-auditor — Brightpath token compliance, dark-first enforcement, responsive behavior]

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
[2026-05-05 --:--] @product-partner → @human
Proposed chip sets for all scope kinds. See §3 for the full catalog.
Key trade-off: get_task_breakdown enablement is one line but adds a tool
to every Ask Gemma session's schema. Risk is low — tool is read-only,
schema is stable, 798 occupations with full O*NET profiles.
```

---

## §11 Final Notes

**Human Review:** APPROVED 2026-05-05 — closed without running the formal agent pipeline.

The core changes shipped:
- `GemmaChat` accepts an optional `starters?: string[]` prop with backwards-compatible fallback to the default `STARTERS` array (`frontend/src/components/menu/GemmaChat.tsx`).
- `STAT_STARTERS`, `SKILL_STARTERS`, `bossStarters(outcome)`, and `COMPARE_STARTERS` are defined and wired through `BuildResultsScreen.handleAskStat / handleAskBoss / handleAskSkill` and `CompareView`.
- `get_task_breakdown` added to `_TOOLS` in `backend/app/services/ask_gemma.py`.

**Deviations from §3 — superseded by follow-up work:**
- `BUILD_STARTERS` was never added; `handleAskBuild` falls back to the default `STARTERS` array in `GemmaChat`. This is consistent with §2 Decision #2 (the hardcoded STARTERS are calibrated for multi-tool-call demo value, which is exactly the build-scope context).
- §5–§9 review/audit/build sections were not filled in — the implementation landed organically as part of the broader Ask Gemma + scope refactor work that overtook this spec, and the formal agent pipeline was not run.

Tests verified at close: 89/89 frontend chip-related tests pass (GemmaChat + CompareView + BuildResultsScreen); 61/62 backend ask_gemma tests pass (the one failure is an unrelated pre-existing ROI-receipt test on the same surface as the FinancesCard / Loans-boss in-flight work).
