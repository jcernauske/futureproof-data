# Feature: Menu + Compare + Chat (Screen 10)

## Claude Code Prompt

```
Read the spec at docs/specs/screen-menu-compare-chat.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, routing, state management, API integration)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 mockups and propose the premium implementation
   - Visionary validates: risk comparison layout, pentagon overlay rendering, chat panel UX, Brightpath token usage, responsive behavior
   - Cross-reference DESIGN.md (source of truth)
   - Writes to §3 with any enhancements or adjustments

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code
   - Implement all components as React with Framer Motion animations
   - Wire up API calls to FastAPI endpoints via apiPost/apiGet helpers (or mock handlers)
   - Use Brightpath design tokens exclusively
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - Menu: saved builds list, navigation to sub-screens
   - Compare: build selection, risk tradeoff display, pentagon overlay
   - Chat: message send, response render, conversation history
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance
   - Confirm: dark backgrounds, correct fonts, token-only colors, responsive behavior, save slot card styling per DESIGN.md
   - Writes findings to §8

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Writes findings to §8
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9

8. COMPLETION
   - Update THIS SPEC's Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/screen-menu-compare-chat-YYYY-MM-DD.md
   
   **CRITICAL: Update the PRD**
   - Open `docs/futureproof_hackathon_prd_v8.md`
   - Find the Frontend Specs table in the "Spec Backlog" section
   - Change F7 `screen-menu-compare-chat` status from "⬜ Not started" to "✅ Complete"
   - Save the PRD file
   
   This ensures the project status remains accurate across sessions.
```

---

## Status: DRAFT

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
| Created | 2026-04-15 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.1 |
| Last Updated | 2026-04-16 |
| Blocked By | F6 (save/wrapped) — **NOW COMPLETE** |
| Related Specs | `screen-save-wrapped` (F6, complete) |

---

## §1 Feature Description

### Overview

Build Screen 10 of the FutureProof flow: the post-build hub. This is where the student lands after saving their build. It's the home screen for return visits — the place where multiple builds are managed, compared, and explored further. Three major features: risk-focused build comparison, freeform Ask Gemma chat, and the new build loop.

This is the **last frontend screen** in the core flow. After this, the product loop is complete: build → fight → branch → save → compare → build again.

### Emotional Target

**Informed confidence.** The anxiety of "what should I major in?" has been replaced by data-backed tradeoff analysis. The student has builds, they have stats, they have boss fight results. Now they compare with clarity, ask follow-up questions, and make their decision.

### Problem Statement

The student has completed one or more builds. They need to:

1. **See their saved builds** in a list — profile name, school, career, stats summary, W/L/D tally
2. **Compare 2-3 builds** via a risk-focused tradeoff screen — not a stat table, but "Build A survives AI but gets crushed by loans. Build B is the opposite."
3. **Ask Gemma** freeform questions with full build context — multi-turn chat panel
4. **Start a new build** — back to school+major selection with the same profile
5. **View any build's detail** — tap a saved build to see its reveal screen
6. **(Stretch) Download a counselor report** — markdown report as PDF (S3 in PRD backlog)

### Core Loop Integration

The menu screen is the hub that closes the loop:
- From Screen 9 (Save + Wrapped) → Done → `/menu`
- From `/menu` → tap a build → `/reveal` (view that build)
- From `/menu` → "New Build" → `/school` (fresh build flow with same profile)
- From `/menu` → "Compare" → compare view (inline, not a separate route)
- From `/menu` → "Ask Gemma" → chat panel (slide-out, not a separate route)

### Success Criteria

- [ ] Saved builds list shows all builds for the current profile via `list_builds(profile_name)`
- [ ] Each build card: school, career, profile emoji, mini pentagon, W/L/D tally, created date
- [ ] Tap a build card → navigate to reveal screen for that build
- [ ] Compare mode: select 2-3 builds → risk comparison view
- [ ] Risk comparison: boss fight tradeoff headlines, not raw stat columns
- [ ] Pentagon overlay: 2-3 stat shapes overlaid on one chart with build colors
- [ ] Gemma comparison summary: tradeoff analysis, **never declares a winner**
- [ ] Ask Gemma: chat panel with full build context, multi-turn history
- [ ] Ask Gemma: message input, send button, response display
- [ ] "New Build" button → navigate to `/school` (keep profile, fresh build inputs)
- [ ] Header in hub mode per DESIGN.md: home icon (left), profile name (center), "New Build" pill (right)
- [ ] All Brightpath design tokens used
- [ ] Responsive: desktop primary, mobile functional
- [ ] All tests pass (backend + frontend)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Risk comparison shows tradeoffs, never winners | The stakes of comparing schools are too real to gamify. "Build A wins" is irresponsible. "Build A survives AI but gets crushed by loans" lets the student decide. **Intentional design restraint** — also a Kaggle writeup angle. | Declare a winner (irresponsible), pure stat table (cold, no insight), weighted score (false precision) |
| 2 | Pentagon overlay for visual comparison | Overlaying 2-3 stat shapes on one chart instantly shows where builds diverge. More intuitive than side-by-side charts or stat tables. | Side-by-side pentagons (harder to compare), bar charts (loses the pentagon identity), radar overlay with no chart (confusing) |
| 3 | Ask Gemma is a side panel, not a full screen | The chat panel should be accessible while looking at build details or comparison results. A side panel keeps context visible. On mobile, it becomes a bottom sheet. | Full-screen chat (loses context), modal (blocks interaction), inline chat bubbles in each section (fragmented) |
| 4 | Chat carries full build context in every message | Gemma needs to know the student's school, major, stats, boss results, skills, and branches to give useful answers. Context rides in every API call — no "what build are you asking about?" confusion. | Ask student to select a build first (friction), partial context (worse answers), summarized context (loses detail) |
| 5 | New Build keeps profile, clears build inputs | The student's identity (profile name, emoji) persists. Starting a new build means picking a new school+major, not re-creating their profile. | Clear everything (lose profile), fork from current build (confusing), duplicate build (not what they want) |
| 6 | Saved builds from DuckDB, not in-memory store | F6 implemented DuckDB persistence for builds. This screen reads from DuckDB via the list/load APIs. The Zustand store holds the *active* build; the saved builds list comes from the backend. | Read from Zustand (only has current build), local storage (unreliable), flat files (replaced by F6) |
| 7 | Compare is inline view, not separate route | Compare mode is a UI state within the menu screen, not a separate `/compare` route. Keeps navigation simple and allows easy back-to-list without router complexity. | Separate `/compare` route (over-engineered for hackathon), modal (too cramped for the comparison content) |

### Constraints

- Compare API (`POST /builds/compare`) expects a list of build_ids and returns stat rows + boss rows. The risk-focused framing is a frontend treatment of this data.
- Chat API (`POST /build/{id}/chat`) expects `{ message, history }` and returns `{ response }`. Multi-turn history is maintained client-side.
- The builds list comes from the DuckDB-backed builds service via `list_builds(profile_name)`. Returns `BuildSummary[]`.
- The header switches to "hub mode" on this screen per DESIGN.md: home icon (left), profile name (center), "New Build" pill (right).
- The compare screen **never declares a winner**. This is a product principle (PRD v8 + Prestige Check concept). Gemma's summary highlights tradeoffs, not rankings.

---

## §3 UI/UX Design

> @fp-design-visionary fills this section with the premium implementation target.
> Cross-reference DESIGN.md (source of truth).

### Screen Layout

**Desktop:** Single column, max-width 800px, centered. Three sections stacked vertically: (1) saved builds list, (2) actions row, (3) compare view (when active). Ask Gemma is a slide-out panel from the right.

**Mobile:** Same stacked layout, full width with 16px padding. Chat panel becomes a bottom sheet (80% viewport height).

### Header (Hub Mode)

Per DESIGN.md Screen 10 spec:
- **Left zone:** Home icon (ghost icon button) — navigates to `/` (landing)
- **Center zone:** Profile name + emoji, Nunito 600, 14px, `text-secondary`
- **Right zone:** "New Build" pill button — `accent-info` border, Nunito 13px, `text-small`

The header is the only element that distinguishes hub mode from the linear flow.

---

### Saved Builds List

**Section label:** "YOUR BUILDS" — Space Mono 700, 11px, `text-muted`, uppercase, letter-spacing 2px, margin-bottom 16px.

**Build cards use the Save Slot Card pattern** from DESIGN.md:

```
┌─────────────────────────────────────────────────────────────┐
│  🐻  │  Build #1: Financial Analyst              │ ▲ │ 3W/1D/1L  │  Apr 12  │
│ 36px │  ISU Business                             │40px│ Space     │  Space   │
│      │  Fredoka 600, 16px, accent-thrive         │pent│ Mono 11px │  Mono    │
│      │  Nunito 13px, text-secondary              │    │ text-muted│  11px    │
└─────────────────────────────────────────────────────────────┘
```

- **Container:** `bg-mid`, 1px `border-subtle`, `radius-lg`, padding 16px 20px
- **Layout:** horizontal flex, gap 16px
- **Avatar:** 36px emoji (from build's profile)
- **Info column:** build label (Fredoka 600, 16px — `accent-thrive` for most recent, `text-primary` for others), meta line (Nunito 13px, `text-secondary` — "{school} · {career}")
- **Mini pentagon:** 40×40px, no labels, just the filled polygon shape in `accent-thrive` at 40% fill
- **W/L/D tally:** Space Mono 700, 11px, `text-muted`
- **Date:** Space Mono 400, 11px, `text-muted`

**States:**
- **Hover:** `bg-surface`, `translateX(4px)`, border shifts to `border-default`
- **Compare-selected:** thrive border glow (`border-color: rgba(125, 212, 163, 0.4)`, `shadow-glow-thrive`)

**Interactions:**
- **Tap card:** Load that build into `buildStore`, navigate to `/reveal`
- **In compare mode:** checkbox appears, tap toggles selection

**Empty state (defensive):** "No builds yet. Start your first one!" with "Build Now" CTA button. (Shouldn't happen on this screen — the student arrives via `/save` which requires a build.)

**Entrance animation:** `stagger.normal` (80ms) with `transitions.fadeInUp`.

---

### Actions Row

Below the builds list, horizontal flex, gap 12px:

| Button | Type | Label | State | Action |
|--------|------|-------|-------|--------|
| Primary | Primary | "New Build ✦" | Always enabled | Clear `buildInputStore`, navigate to `/school` |
| Secondary | Secondary | "Compare Builds" | Disabled if < 2 builds | Enter compare selection mode |
| Secondary | Secondary | "Ask Gemma ✨" | Enabled if ≥ 1 build | Open chat panel with most recent build's context |
| Ghost | Ghost | "Download Report" | Stretch — show only if time permits | Trigger `GET /build/{id}/report` |

Button sizes per DESIGN.md: Primary 48px height, Secondary 44px, Ghost 40px.

---

### Compare Mode

**Selection phase:**

When student taps "Compare Builds":
1. Checkboxes appear on each build card (left side, 20px checkbox, `accent-thrive` when checked)
2. A selection counter appears: "Select 2-3 builds" (Nunito 14px, `text-secondary`, centered above the list)
3. Selected cards get thrive border glow
4. A floating action bar appears at bottom: "Compare (2)" primary button (disabled until 2+ selected), "Cancel" ghost button

**Comparison view (inline, not a separate route):**

When student taps "Compare" with 2-3 builds selected, the saved builds list crossfades (`transitions.fade`) to the comparison view:

**Section 1: Pentagon Overlay**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                    ╱╲                                   │
│                   ╱  ╲                                  │
│                  ╱    ╲                                 │
│                 ╱      ╲                                │
│                ╱   ◯    ╲     ← 2-3 overlaid shapes     │
│               ╱──────────╲                              │
│              ╱            ╲                             │
│                                                         │
│    ● Build A (thrive)  ● Build B (info)  ● Build C     │
│                        (empathy)                        │
└─────────────────────────────────────────────────────────┘
```

- SVG pentagon, 280×280px, centered
- Grid lines: 4 concentric pentagons at 100%, 80%, 60%, 40% — stroke `text-muted` at 15%
- Axes: 5 radial lines — stroke `text-muted` at 20%
- **Overlaid stat shapes:** Each build gets a polygon in its color:
  - Build 1: `accent-thrive` (#7DD4A3)
  - Build 2: `accent-info` (#7BB8E0)
  - Build 3: `accent-empathy` (#E88BA9)
  - Fill: 25% opacity. Stroke: 2px, 70% opacity.
- **Legend:** Below the pentagon, horizontal flex, gap 24px. Each: colored dot (12px) + build label (Nunito 14px, `text-secondary`)
- Stat labels (ERN, ROI, etc.) outside vertices, Space Mono 11px, stat color

**Section 2: Risk Headlines**

One card per boss, stacked vertically, gap 12px:

```
┌─────────────────────────────────────────────────────────┐
│ ┃  🤖 Fight AI                                          │
│ ┃  ─────────────────────────────────────────────────    │
│ ┃  Build A: [LOSE]    Build B: [LOSE]                   │
│                                                         │
│    Both builds lose. AI exposure is a shared risk.      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ┃  💰 Fight Student Loans                               │
│ ┃  ─────────────────────────────────────────────────    │
│ ┃  Build A: [WIN]     Build B: [LOSE]     ← DIVERGENCE │
│                                                         │
│    This is where your decision matters.                 │
└─────────────────────────────────────────────────────────┘
```

- **Card:** `bg-mid`, 1px `border-subtle`, `radius-lg`, padding 16px 20px
- **Boss row:** emoji (28px) + boss name (Fredoka 600, 18px, `text-primary`)
- **Result pills:** per DESIGN.md pill patterns — WIN (`pill-thrive`), LOSE (`pill-alert`), DRAW (`pill-caution`)
- **Divergence indicator:** When builds disagree (one wins, one loses), the card gets a 3px left border in `accent-caution` and a one-liner: "This is where your decision matters." (Nunito 13px, `text-accent-caution`, italic)
- **Agreement indicator:** When all builds agree, muted treatment — no special border, optional one-liner: "All builds {win/lose}. This risk is shared." (Nunito 13px, `text-muted`)

**Section 3: Gemma Comparison Summary**

Triggered when comparison view mounts. API call: `POST /build/{build_id}/chat` with a comparison prompt that includes both builds' data, OR use the output from `builds.compare_builds()` formatted as a prompt.

```
┌─────────────────────────────────────────────────────────┐
│  GEMMA'S COMPARISON                                     │
│  Space Mono 11px, text-accent-insight, uppercase        │
├┃────────────────────────────────────────────────────────┤
│┃                                                        │
│┃  Build A (Financial Analyst) optimizes for earning     │
│┃  power at the cost of AI resilience. Build B           │
│┃  (Software Developer) is the opposite — it's more      │
│┃  automation-proof but the earnings ceiling is lower.   │
│┃                                                        │
│┃  Neither is wrong — it depends on which risk you're    │
│┃  more willing to live with.                            │
│┃                                                        │
└─────────────────────────────────────────────────────────┘
```

- **Container:** `bg-mid`, 1px `border-subtle`, `radius-xl`, padding 24px, 3px left border in `accent-insight`
- **Section label:** "GEMMA'S COMPARISON" — Space Mono 700, 11px, `text-accent-insight`, uppercase, letter-spacing 2px
- **Content:** Nunito 400, 16px, `text-primary`, line-height 1.6
- **Loading state:** animated shimmer (3 lines of `bg-surface` blocks with opacity 0.3→0.7→0.3 breathing animation)
- **Error state:** "Gemma couldn't analyze this comparison. You can still see the stats above." (Nunito 14px, `text-muted`)

**Back button:** Ghost button "← Back to builds" at top-left of comparison view — returns to saved builds list.

---

### Ask Gemma Panel

**Trigger:** "Ask Gemma ✨" button in actions row, OR a "Ask about this" link in the comparison view.

**Desktop layout:** Slide-in panel from right, 400px wide, full viewport height minus header. `bg-mid`, 1px `border-subtle` on left edge. Content has `bg-deep` message area.

**Mobile layout:** Bottom sheet, drags up to 85% viewport height. Drag handle (40px × 4px, `bg-surface`, centered) at top.

**Panel structure:**

```
┌────────────────────────────────────────────┐
│  Ask Gemma                          [✕]    │  ← Header row
├────────────────────────────────────────────┤
│  Context: ISU Business · Financial Analyst │  ← Context badge
│           3W / 1D / 1L                     │
├────────────────────────────────────────────┤
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │ What internships should I look for?  │  │  ← Starter question
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ Is this career better in-state?      │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │ What if I add a minor?               │  │
│  └──────────────────────────────────────┘  │
│                                            │
│            (empty conversation)            │
│                                            │
├────────────────────────────────────────────┤
│  [  Ask anything about your build...   ]   │  ← Input
│                                       [→]  │  ← Send button
└────────────────────────────────────────────┘
```

**Header:** Fredoka 600, 20px, `text-primary` — "Ask Gemma". Close button (×, ghost icon, top-right).

**Context badge:** `bg-surface`, `radius-sm`, padding 8px 12px. Nunito 12px, `text-muted`. Shows: "{school} · {career} · {W}W/{D}D/{L}L".

**Message area:** scrollable, flex-grow. Messages stack vertically, gap 12px.

- **User messages:** right-aligned, `bg-surface`, `radius-lg` (top-right corner = `radius-sm` for speech-bubble feel), padding 12px 16px. Nunito 400, 15px, `text-primary`. Max-width 85%.
- **Gemma responses:** left-aligned, `bg-void`, `radius-lg` (top-left corner = `radius-sm`), padding 12px 16px. Nunito 400, 15px, `text-primary`. Max-width 90%. Small Gemma icon (✨, `text-accent-insight`, 14px) above the bubble.
- **Loading:** 3 animated dots (4px circles, `text-muted`, stagger pulse 0.2s) in a response bubble position.

**Starter questions (shown when conversation is empty):**
- "What internships should I look for?"
- "Is this career better in-state or out-of-state?"
- "What if I add a minor?"
- "How do I improve my AI resilience?"

Each as a tappable pill: `bg-surface`, 1px `border-subtle`, `radius-full`, padding 10px 16px, Nunito 13px, `text-secondary`. Hover: `border-default`, `text-primary`. Tap fills the input with the question text.

**Input area:** fixed at bottom, padding 16px.
- Text input: `bg-void`, 1px `border-default`, `radius-md`, height 48px, padding 0 16px. Nunito 15px, `text-primary`. Placeholder: "Ask anything about your build..." (`text-muted`). Focus: `border-color: accent-info`, `shadow: 0 0 0 3px rgba(123, 184, 224, 0.15)`.
- Send button: 48px × 48px, `radius-md`. When input empty: `bg-surface`, `text-muted`, disabled. When input has text: `bg-accent-thrive`, `text-inverse`, enabled. Icon: arrow-up glyph.

**API:** `POST /build/{build_id}/chat` with `{ message: string, history: [{ role: 'user' | 'assistant', content: string }] }`. Returns `{ response: string }`.

**Conversation history:** Maintained in component state as `ChatMessage[]`. Each new message appends to history, sends full history to API. History is **ephemeral** — resets when panel closes or student navigates away.

---

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Builds list | `region-saved-builds` | list | "Your saved builds" |
| Build card | `card-build-{id}` | listitem / button | "{school} — {career}" |
| Compare checkbox | `check-compare-{id}` | checkbox | "Select {build label} for comparison" |
| Compare button | `btn-compare` | button | "Compare selected builds" |
| Compare view | `region-compare` | article | "Risk comparison of {n} builds" |
| Risk headline card | `card-risk-{boss}` | article | "{boss}: {divergence summary}" |
| Pentagon overlay | `svg-pentagon-overlay` | img | "Pentagon overlay comparing {n} builds" |
| Gemma summary | `region-gemma-compare` | article | "Gemma's comparison analysis" |
| Ask Gemma button | `btn-ask-gemma` | button | "Open chat with Gemma" |
| Chat panel | `dialog-chat` | dialog | "Ask Gemma about your build" |
| Chat input | `input-chat` | textbox | "Type a question" |
| Chat send | `btn-chat-send` | button | "Send message" |
| Starter question | `btn-starter-{n}` | button | Question text |
| New build button | `btn-new-build` | button | "Start a new build" |
| Back to builds | `btn-back-builds` | button | "Back to saved builds" |
| Home icon | `btn-home` | button | "Go to home" |

---

## §4 Technical Specification

### Architecture Overview

Screen 10 is the hub — it consumes multiple API endpoints (list builds, load build, compare builds, chat) and provides navigation to the rest of the app. No new backend services needed; this screen wires existing endpoints to a new frontend experience.

### API Endpoints Consumed

| Endpoint | Method | Request | Response | Used By |
|---|---|---|---|---|
| `GET /builds` | GET | Query param `profile_name` | `BuildSummary[]` | Saved builds list |
| `GET /build/{build_id}` | GET | Path param | `Build` | Load a specific build for viewing |
| `POST /builds/compare` | POST | `{ build_ids: string[] }` | `{ builds, stats, bosses }` | Risk comparison data |
| `POST /build/{build_id}/chat` | POST | `{ message: string, history: [] }` | `{ response: string }` | Ask Gemma |
| `GET /build/{build_id}/report` | GET | Path param | `{ markdown: string }` | Counselor report download (stretch) |

**Note:** If `GET /builds?profile_name=X` doesn't exist yet, add a one-line router endpoint that calls `builds.list_builds(profile_name)`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/MenuScreen.tsx` | Create | Screen 10 top-level: saved builds list, actions, compare view, header hub mode |
| `frontend/src/components/menu/BuildCard.tsx` | Create | Save slot card per DESIGN.md: emoji, info, mini pentagon, W/L/D, date |
| `frontend/src/components/menu/MiniPentagon.tsx` | Create | 40×40 pentagon shape (no labels, just the filled polygon) |
| `frontend/src/components/menu/CompareView.tsx` | Create | Risk comparison: selection phase, boss headlines, pentagon overlay, Gemma summary |
| `frontend/src/components/menu/RiskHeadlineCard.tsx` | Create | Per-boss comparison card with per-build result pills |
| `frontend/src/components/menu/PentagonOverlay.tsx` | Create | Pentagon chart with 2-3 overlaid stat shapes |
| `frontend/src/components/menu/GemmaChat.tsx` | Create | Ask Gemma slide-out panel: messages, input, history, starter questions |
| `frontend/src/components/menu/ChatMessage.tsx` | Create | Individual message bubble (user or Gemma) |
| `frontend/src/api/menu.ts` | Create | API client for list builds, compare, chat (with mock fallback) |
| `frontend/src/api/mockMenu.ts` | Create | Mock handlers for builds list, compare data, chat response |
| `frontend/src/stores/buildInputStore.ts` | Modify | Add `resetInputs()` action to clear school/major/effort/loans |
| `frontend/src/components/AppHeader.tsx` | Modify | Add hub mode state: home icon (left), profile (center), "New Build" pill (right) |
| `frontend/src/App.tsx` | Modify | Add route: `/menu` |
| `backend/app/routers/builds.py` | Modify | Add `GET /builds?profile_name=X` endpoint if not present |

### Data Flow

**Builds list:**
1. On mount, read `profile_name` from `profileStore`
2. Fetch `GET /builds?profile_name={name}`
3. Store result in component state as `savedBuilds: BuildSummary[]`
4. Render build cards

**Compare:**
1. Student selects 2-3 builds via checkboxes
2. Tap "Compare" → call `POST /builds/compare` with selected `build_ids`
3. Store comparison result in component state
4. Render comparison view (pentagon overlay, risk headlines)
5. Trigger Gemma summary via `POST /build/{id}/chat` with a comparison prompt

**Chat:**
1. Student taps "Ask Gemma" → panel opens
2. Conversation history initialized as `[]`
3. Student types message + sends
4. API call: `POST /build/{id}/chat` with `{ message, history }`
5. Response appended to history, rendered as Gemma bubble
6. Repeat

**New Build:**
1. Student taps "New Build ✦"
2. Call `buildInputStore.resetInputs()` — clears school, major, effort, loans
3. `profileStore` unchanged (profile name, emoji persist)
4. `buildStore.hasSeenStatTutorial` unchanged (stays true)
5. Navigate to `/school`

**View Build:**
1. Student taps a build card
2. Call `GET /build/{build_id}`
3. Store result in `buildStore` via `setBuild(build)`
4. Navigate to `/reveal`

### Zustand Store Changes

**`buildInputStore`** — add:
```typescript
resetInputs: () => void  // clears school, major, effort, loans to initial state
```

**`buildStore`** — no changes (use existing `setBuild`).

**`profileStore`** — no changes (read `profile_name`, `profile_emoji`).

### Routing Addition

```
/menu  → MenuScreen     (Screen 10)
```

**Navigation guard:** If `profileStore.profile_name` is empty, redirect to `/`. Otherwise, render the menu.

### Chat History Type

```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;  // ISO string, optional for display
}
```

Maintained in `GemmaChat` component state. Not persisted — history resets when panel unmounts.

### Service Changes

**Backend — minor:**
- If `GET /builds?profile_name=X` doesn't exist, add:
```python
@router.get("/builds")
async def list_builds_by_profile(profile_name: str) -> list[BuildSummary]:
    return builds_service.list_builds(profile_name)
```

No other backend changes. All endpoints already exist from F6 and earlier specs.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `App.test.tsx` | Routing tests | Medium | New `/menu` route |
| `AppHeader.test.tsx` | Header states | Medium | New hub mode |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `App.test.tsx` | Add `/menu` route assertion | New route added |
| `AppHeader.test.tsx` | Add hub mode props | New header state |

#### Confirmed Safe

All other tests should NOT break. If any fail, STOP and escalate.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `screens/MenuScreen.test.tsx` | renders saved builds | Build cards appear for each saved build |
| P0 | `screens/MenuScreen.test.tsx` | tap build card loads build | Card tap → buildStore updated + navigate to /reveal |
| P0 | `screens/MenuScreen.test.tsx` | new build clears inputs | Tap "New Build" → buildInputStore.resetInputs called, navigate to /school |
| P0 | `components/menu/CompareView.test.tsx` | renders risk headlines | Boss cards with per-build results |
| P0 | `components/menu/CompareView.test.tsx` | highlights divergence | Builds disagree on a boss → caution border |
| P0 | `components/menu/PentagonOverlay.test.tsx` | renders multiple shapes | 2-3 overlaid polygon fills present |
| P0 | `components/menu/GemmaChat.test.tsx` | sends message | Type + send → API called with message + history |
| P0 | `components/menu/GemmaChat.test.tsx` | renders response | API response → Gemma bubble appears |
| P1 | `components/menu/GemmaChat.test.tsx` | starter questions fill input | Tap starter → input populated |
| P1 | `components/menu/GemmaChat.test.tsx` | maintains history | Send 2 messages → history has 4 entries (2 user + 2 assistant) |
| P1 | `components/menu/BuildCard.test.tsx` | renders build summary | School, career, W/L/D, mini pentagon present |
| P1 | `screens/MenuScreen.test.tsx` | compare disabled with < 2 builds | Compare button disabled when fewer than 2 builds saved |
| P1 | `screens/MenuScreen.test.tsx` | compare selection mode | Tap "Compare" → checkboxes appear on cards |
| P2 | `components/menu/CompareView.test.tsx` | Gemma summary renders | Comparison narrative container present |
| P2 | `api/menu.test.ts` | mock returns valid shapes | Mock handlers return correct types |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline/data changes)

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

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

**Context for agents:**

- **DESIGN.md is the source of truth** for all visual decisions. Read it before writing any UI code. DESIGN.md wins over existing code.

- **The compare screen never declares a winner.** This is a deliberate design restraint — the stakes of comparing schools are too real to gamify. "Build A wins" is irresponsible. "Build A survives AI but gets crushed by loans" lets the student decide. Gemma's comparison summary highlights what each build optimizes for and what it sacrifices, **never which is "better."** This is also a Kaggle writeup angle: intentional design restraint as a product differentiator.

- **Header switches to hub mode.** DESIGN.md specifies: home icon (left), profile name (center, `text-secondary`), "New Build" pill button (right). This is a distinct header state from the linear flow screens (Screens 2-9).

- **Save slot cards per DESIGN.md.** Horizontal layout: avatar + info + date. Hover slides right 4px. The card style is specified in DESIGN.md's Components section under "Save Slot Cards."

- **Ask Gemma is the 10th Gemma integration surface.** It carries full build context in every API call. This is a strong demo moment for the hackathon video — a student asking a specific follow-up question and getting a data-grounded answer.

- **Chat history is ephemeral.** Not persisted between sessions. The chat panel is a conversation tool, not a log. History rides in the API request so Gemma has multi-turn context, but resets when the panel closes.

- **Pentagon overlay uses semi-transparent fills.** 2-3 build shapes on one chart, each at 25% fill opacity. Overlapping regions show the blend. Legend below maps colors to builds.

- **New Build preserves profile, clears inputs.** `profileStore` stays (profile name, emoji). `buildInputStore` resets (school, major, effort, loans). `buildStore.hasSeenStatTutorial` stays true. Navigate to `/school`.

- **Builds list comes from DuckDB.** F6 implemented DuckDB persistence. This screen calls `GET /builds?profile_name=X` (or equivalent) to get saved builds. The Zustand `buildStore` holds only the *active* build being viewed.

- **Report download is stretch.** The backend `report_gen.py` already works. If time permits, add a "Download Report" ghost button. Don't block the spec on this — it's S3 in the PRD backlog.

- **This is the last frontend spec.** Once F7 ships, all 10 screens are complete. The core product loop (build → fight → branch → save → compare → build again) is fully functional.

---
