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
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/screen-menu-compare-chat-YYYY-MM-DD.md
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
| Spec Version | 1.0 |
| Last Updated | 2026-04-15 |
| Blocked By | F6 (save/wrapped) |
| Related Specs | `screen-save-wrapped` (F6) |

---

## §1 Feature Description

### Overview

Build Screen 10 of the FutureProof flow: the post-build hub. This is where the student lands after saving their build. It's the home screen for return visits — the place where multiple builds are managed, compared, and explored further. Three major features: risk-focused build comparison, freeform Ask Gemma chat, and the new build loop.

This is the last frontend screen in the core flow. After this, the product loop is complete: build → fight → branch → save → compare → build again.

### Emotional Target

**Informed confidence.** The anxiety of "what should I major in?" has been replaced by data-backed tradeoff analysis. The student has builds, they have stats, they have boss fight results. Now they compare with clarity, ask follow-up questions, and make their decision.

### Problem Statement

The student has completed one or more builds. They need to:

1. **See their saved builds** in a list — profile name, school, career, stats summary, W/L/D tally
2. **Compare 2-3 builds** via a risk-focused tradeoff screen — not a stat table, but "Build A survives AI but gets crushed by loans. Build B is the opposite."
3. **Ask Gemma** freeform questions with full build context — multi-turn chat panel
4. **Start a new build** — back to school+major selection with the same profile
5. **View any build's detail** — tap a saved build to see its reveal screen
6. **(If time permits) Download a counselor report** — markdown report as PDF

### Success Criteria

- [ ] Saved builds list shows all builds for the current profile via DuckDB `list_builds(profile_name)`
- [ ] Each build card: school, career, profile emoji, pentagon mini-chart, W/L/D, created date
- [ ] Tap a build card → navigate to reveal screen for that build
- [ ] Compare mode: select 2-3 builds → risk comparison screen
- [ ] Risk comparison: boss fight tradeoff headlines, not raw stat columns
- [ ] Pentagon overlay: 2-3 stat shapes overlaid on one chart with build colors
- [ ] Gemma comparison summary: tradeoff analysis, never declares a winner
- [ ] Ask Gemma: chat panel with full build context, multi-turn history
- [ ] Ask Gemma: message input, send button, streaming or chunked response display
- [ ] "New Build" button → navigate to school+major screen (keep profile, fresh build inputs)
- [ ] Header in hub mode: home icon (left), profile name (center), "New Build" pill (right) per DESIGN.md
- [ ] All Brightpath design tokens used
- [ ] Responsive: desktop primary, mobile functional
- [ ] All tests pass

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Risk comparison shows tradeoffs, never winners | The stakes of comparing schools are too real to gamify. "Build A wins" is irresponsible. "Build A survives AI but gets crushed by loans" lets the student decide. Intentional design restraint — also a Kaggle writeup angle. | Declare a winner (irresponsible), pure stat table (cold, no insight), weighted score (false precision) |
| 2 | Pentagon overlay for visual comparison | Overlaying 2-3 stat shapes on one chart instantly shows where builds diverge. More intuitive than side-by-side charts or stat tables. | Side-by-side pentagons (harder to compare), bar charts (loses the pentagon identity), radar overlay with no chart (confusing) |
| 3 | Ask Gemma is a side panel, not a full screen | The chat panel should be accessible while looking at build details or comparison results. A side panel keeps context visible. On mobile, it becomes a bottom sheet. | Full-screen chat (loses context), modal (blocks interaction), inline chat bubbles in each section (fragmented) |
| 4 | Chat carries full build context in every message | Gemma needs to know the student's school, major, stats, boss results, skills, and branches to give useful answers. Context rides in every API call — no "what build are you asking about?" confusion. | Ask student to select a build first (friction), partial context (worse answers), summarized context (loses detail) |
| 5 | New Build keeps profile, clears build inputs | The student's identity (profile name, emoji) persists. Starting a new build means picking a new school+major, not re-creating their profile. | Clear everything (lose profile), fork from current build (confusing), duplicate build (not what they want) |
| 6 | Saved builds from DuckDB, not in-memory store | F6 implemented DuckDB persistence for builds. This screen reads from DuckDB via the list/load APIs. The Zustand store holds the *active* build; the saved builds list comes from the backend. | Read from Zustand (only has current build), local storage (unreliable), flat files (replaced by F6) |

### Constraints

- Compare API (`POST /builds/compare`) expects a list of build_ids and returns stat rows + boss rows. The risk-focused framing is a frontend treatment of this data.
- Chat API (`POST /build/{id}/chat`) expects `{ message, history }` and returns `{ response }`. Multi-turn history is maintained client-side.
- The builds list API is `list_builds(profile_name)` from the DuckDB-backed builds service. Returns `BuildSummary[]`.
- The header switches to "hub mode" on this screen per DESIGN.md: home icon (left), profile name (center), "New Build" pill (right).

---

## §3 UI/UX Design

> @fp-design-visionary fills this section with the premium implementation target.
> Cross-reference DESIGN.md

### Screen 10: Post-Build Hub

**Layout:** Single column, max-width 800px, centered. Three sections stacked vertically: saved builds, compare, and actions. Ask Gemma is a slide-out panel (right on desktop, bottom sheet on mobile).

**Header:** Hub mode per DESIGN.md — home icon (left), profile name + emoji (center, `text-secondary`), "New Build" pill button (right, `accent-info` border, `text-small`).

### Saved Builds List

- Section label: Space Mono 11px, `text-muted`, uppercase, letter-spacing 2px — "YOUR BUILDS"
- Build cards use the **Save Slot Card** pattern from DESIGN.md:
  - Horizontal layout: emoji (36px) + info column + date.
  - Info: build label (Fredoka 600, 16px, `accent-thrive` for most recent, `text-primary` for others), meta line (Nunito 13px, `text-secondary` — "{school} · {career}").
  - Right side: mini pentagon (40×40px, no labels, just the shape) + W/L/D tally (Space Mono 11px, `text-muted`).
  - Date: Space Mono 11px, `text-muted`.
  - Card: `bg-mid`, 1px `border-subtle`, `radius-lg`, padding 16px 20px.
  - Hover: `bg-surface`, `translateX(4px)`.
  - Tap: navigate to `/reveal` with that build loaded.
- Empty state: if no builds saved (shouldn't happen at this point, but defensive): "No builds yet. Start your first one!" with CTA.
- Stagger entrance: `stagger.normal` (80ms).

### Compare Mode

Triggered by a "Compare Builds" secondary button below the builds list. Requires 2-3 builds.

**Build selection:**
- Checkboxes appear on each build card.
- Selected cards get thrive border glow.
- "Compare" primary button appears when 2-3 builds are selected. Disabled otherwise.
- Tap "Compare" → comparison view slides in.

**Comparison view:**

Not a stat table. A risk-focused tradeoff experience.

- **Section 1: Risk Headlines**
  - For each boss fight, show which builds win/lose/draw.
  - Format: headline cards, one per boss.
  - Each card: Boss emoji + boss name (Fredoka 600, `text-heading`) + per-build result pills.
  - Highlight divergence: when builds disagree (one wins, one loses), the card gets a subtle `accent-caution` left border — "This is where your decision matters."
  - When all builds agree (all win or all lose), muted treatment — `text-secondary`, no accent border.

- **Section 2: Pentagon Overlay**
  - Single pentagon chart with 2-3 stat shapes overlaid.
  - Each build gets a color: first build = `accent-thrive`, second = `accent-info`, third = `accent-empathy`.
  - Shapes are semi-transparent (fill opacity 25%) so overlaps are visible.
  - Legend below: colored dot + build label for each.

- **Section 3: Gemma Comparison Summary**
  - Triggered automatically when compare view opens.
  - API: use the existing chat endpoint with a comparison prompt, OR a dedicated comparison narrative (backend `builds.compare_builds()` + Gemma summary).
  - Content: 4-6 sentence tradeoff analysis. "Build A optimizes for earning power at the cost of AI resilience. Build B is the opposite — it's more automation-proof but the earnings ceiling is lower. Neither is wrong — it depends on which risk you're more willing to live with."
  - Container: `bg-mid`, `border-subtle`, `radius-xl`, padding `space-6`. Left border: 3px solid `accent-insight`.
  - Section label: "GEMMA'S COMPARISON" (Space Mono, `text-accent-insight`).

- **Back button:** Ghost button "← Back to builds" returns to the saved builds list.

### Ask Gemma Panel

A freeform chat panel with full build context.

**Trigger:** "Ask Gemma" secondary button in the actions area. Opens the panel.

**Desktop layout:** Slide-in panel from right, 360px wide, full height. Build content remains visible on the left. Panel: `bg-mid`, 1px `border-subtle` on left edge.

**Mobile layout:** Bottom sheet, slides up to 80% viewport height. Drag handle at top.

**Panel content:**

- Header: Fredoka 600, `text-heading`, `text-primary` — "Ask Gemma". Close button (icon, top-right).
- Context badge: `bg-surface`, `radius-sm`, padding 4px 10px. Nunito 12px, `text-muted` — "Context: {school} · {career} · {W}W/{L}L"
- Message area: scrollable, flex-grow. Messages stack vertically.
  - User messages: right-aligned, `bg-surface`, `radius-lg`, padding `space-3`. Nunito 400, `text-body`, `text-primary`. Max-width 80%.
  - Gemma responses: left-aligned, `bg-deep`, `radius-lg`, padding `space-3`. Nunito 400, `text-body`, `text-primary`. Max-width 90%. Small Gemma icon (insight-colored) to the left.
  - Loading: animated dots (3 dots, stagger pulse) in a response bubble while waiting for API.
- Input area: fixed at bottom of panel.
  - Text input: `bg-deep`, `border-default`, `radius-md`, height 44px. Placeholder: "Ask anything about your build..."
  - Send button: icon button, `accent-thrive` background when input non-empty, `bg-surface` when empty.
- Conversation history maintained in component state. Sent to API with every message.
- Suggested starter questions (shown when chat is empty):
  - "What internships should I look for?"
  - "Is this career better in-state or out-of-state?"
  - "What if I add a minor?"
  - Each as a tappable pill: `bg-surface`, `border-subtle`, `radius-full`, Nunito 13px, `text-secondary`. Tap fills the input.

**API:** `POST /build/{build_id}/chat` with `{ message: string, history: [{ role, content }] }`. Returns `{ response: string }`.

### Actions Area

Below the saved builds list:

- Primary button: "New Build ✦" — clears `buildInputStore`, navigates to `/school`.
- Secondary button: "Compare Builds" — enters compare selection mode (disabled if < 2 builds).
- Secondary button: "Ask Gemma" — opens the chat panel with the most recent build's context.
- Ghost button (if time permits): "Download Report" — triggers `GET /build/{id}/report`, displays or downloads the markdown.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Builds list | `region-saved-builds` | list | "Your saved builds" |
| Build card | `card-build-{id}` | listitem / button | "{school} — {career}" |
| Compare select checkbox | `check-compare-{id}` | checkbox | "Select {build label} for comparison" |
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

---

## §4 Technical Specification

### Architecture Overview

Screen 10 is the hub — it consumes multiple API endpoints (list builds, load build, compare builds, chat) and provides navigation to the rest of the app. No new backend services needed; this screen wires existing endpoints to a new frontend experience.

### API Endpoints Consumed

| Endpoint | Method | Request | Response | Used By |
|---|---|---|---|---|
| `GET /profile/lookup` | POST | `{ name_query: string }` | `ProfileLookupResult` with `builds: BuildSummary[]` | Saved builds list |
| `GET /build/{build_id}` | GET | Path param | `Build` | Load a specific build for viewing |
| `POST /builds/compare` | POST | `{ build_ids: string[] }` | `{ builds, stats, bosses }` | Risk comparison data |
| `POST /build/{build_id}/chat` | POST | `{ message: string, history: [] }` | `{ response: string }` | Ask Gemma |
| `GET /build/{build_id}/report` | GET | Path param | `{ markdown: string }` | Counselor report download (stretch) |

**Note:** The builds list could also come from a new `GET /builds?profile_name=X` endpoint backed by the DuckDB `list_builds()` function. If the profile lookup endpoint doesn't return builds, add a lightweight list endpoint.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/MenuScreen.tsx` | Create | Screen 10 top-level: saved builds list, actions, header hub mode |
| `frontend/src/components/menu/BuildCard.tsx` | Create | Save slot card per DESIGN.md: emoji, info, mini pentagon, W/L/D, date |
| `frontend/src/components/menu/MiniPentagon.tsx` | Create | 40×40 pentagon shape (no labels, just the filled polygon) |
| `frontend/src/components/menu/CompareView.tsx` | Create | Risk comparison: boss headlines, pentagon overlay, Gemma summary |
| `frontend/src/components/menu/RiskHeadlineCard.tsx` | Create | Per-boss comparison card with per-build result pills |
| `frontend/src/components/menu/PentagonOverlay.tsx` | Create | Pentagon chart with 2-3 overlaid stat shapes |
| `frontend/src/components/menu/GemmaChat.tsx` | Create | Ask Gemma slide-out panel: messages, input, history, starter questions |
| `frontend/src/components/menu/ChatMessage.tsx` | Create | Individual message bubble (user or Gemma) |
| `frontend/src/api/menu.ts` | Create | API client for list builds, compare, chat (with mock fallback) |
| `frontend/src/api/mockMenu.ts` | Create | Mock handlers for builds list, compare data, chat response |
| `frontend/src/App.tsx` | Modify | Add route: `/menu`. Update header to support hub mode. |

### Data Flow

**Builds list:** On mount, fetch saved builds via the profile name from `profileStore`. Store the list in component state (not Zustand — this is screen-local data that refreshes on navigation).

**Compare:** When the student selects 2-3 builds and taps Compare, call `POST /builds/compare` with the selected build_ids. Store the comparison result in component state. Optionally trigger a Gemma comparison narrative via the chat endpoint with a comparison prompt.

**Chat:** Conversation history maintained in component state as `Array<{ role: 'user' | 'assistant', content: string }>`. Each new message sends the full history to the API. Gemma's response is appended to history.

**New Build:** Clears `buildInputStore` (school, major, effort, loans) but preserves `profileStore` (profile name, emoji) and `buildStore.hasSeenStatTutorial`. Navigates to `/school`.

**View Build:** Loads the selected build into `buildStore` and navigates to `/reveal`.

### Zustand Store Changes

No new store. Minor changes:

- `buildInputStore`: add a `resetInputs()` action that clears school/major/effort/loans without touching other stores. Used by "New Build".
- `buildStore`: `setBuild()` already exists — used when loading a saved build for viewing.

### Routing Addition

```
/menu  → MenuScreen     (Screen 10)
```

No navigation guard — the menu is always accessible if a profile exists. If no profile in `profileStore`, redirect to `/`.

### Chat History Type

```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}
```

Maintained in component state. Not persisted — chat history resets when the panel closes or the student navigates away. This matches the PRD: the chat is a conversation, not a log.

### Service Changes

- No backend changes in this spec. All endpoints already exist.
- Possible addition: `GET /builds?profile_name=X` endpoint if the profile lookup doesn't return a builds list conveniently. This would be a one-line router addition calling `builds.list_builds(profile_name)`.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `App.test.tsx` | Routing tests | Medium | New `/menu` route + header hub mode |

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `screens/MenuScreen.test.tsx` | renders saved builds | Build cards appear for each saved build |
| P0 | `screens/MenuScreen.test.tsx` | tap build card loads build | Card tap → buildStore updated + navigate to /reveal |
| P0 | `components/menu/CompareView.test.tsx` | renders risk headlines | Boss cards with per-build results |
| P0 | `components/menu/CompareView.test.tsx` | highlights divergence | Builds disagree on a boss → accent border |
| P0 | `components/menu/PentagonOverlay.test.tsx` | renders multiple shapes | 2-3 overlaid polygon fills present |
| P0 | `components/menu/GemmaChat.test.tsx` | sends message | Type + send → API called with message + history |
| P0 | `components/menu/GemmaChat.test.tsx` | renders response | API response → Gemma bubble appears |
| P1 | `components/menu/GemmaChat.test.tsx` | starter questions fill input | Tap starter → input populated |
| P1 | `components/menu/GemmaChat.test.tsx` | maintains history | Send 2 messages → history has 4 entries (2 user + 2 assistant) |
| P1 | `components/menu/BuildCard.test.tsx` | renders build summary | School, career, W/L/D, mini pentagon present |
| P1 | `screens/MenuScreen.test.tsx` | new build clears inputs | Tap "New Build" → buildInputStore cleared, navigate to /school |
| P1 | `screens/MenuScreen.test.tsx` | compare disabled with < 2 builds | Compare button disabled when fewer than 2 builds saved |
| P2 | `components/menu/CompareView.test.tsx` | Gemma summary renders | Comparison narrative container present |
| P2 | `api/menu.test.ts` | mock returns valid shapes | Mock handlers return correct types |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING

### @fp-data-reviewer Review
**Status:** SKIPPED

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

- **DESIGN.md is the source of truth** for all visual decisions. Read it before writing any UI code.
- **The compare screen never declares a winner.** This is a deliberate design restraint. The Prestige Check concept from the memory notes reinforces this: "the stakes of comparing schools are too real to gamify." The risk comparison shows tradeoffs — which bosses each build wins/loses — and lets the student decide. Gemma's comparison summary highlights what each build optimizes for and what it sacrifices, never which is "better."
- **Header switches to hub mode.** DESIGN.md specifies: home icon (left), profile name (center, `text-secondary`), "New Build" pill button (right). This is a distinct header state from the linear flow screens.
- **Save slot cards per DESIGN.md.** Horizontal layout: avatar + info + date. Hover slides right 4px. The card style is specified in DESIGN.md's Components section under "Save Slot Cards."
- **Ask Gemma is the 10th Gemma integration surface.** It carries full build context in every API call. This is a strong demo moment for the hackathon video — a student asking a specific follow-up question and getting a data-grounded answer.
- **Chat history is ephemeral.** Not persisted between sessions. The chat panel is a conversation tool, not a log. History rides in the API request so Gemma has multi-turn context.
- **Pentagon overlay uses semi-transparent fills.** 2-3 build shapes on one chart, each at 25% fill opacity. Overlapping regions show the blend. Legend below maps colors to builds.
- **New Build preserves profile, clears inputs.** `profileStore` stays. `buildInputStore` resets (school, major, effort, loans). `buildStore.hasSeenStatTutorial` stays true. Navigate to `/school`.
- **Builds list comes from DuckDB.** F6 implemented DuckDB persistence. This screen calls the list/load APIs to get saved builds. The Zustand `buildStore` holds only the *active* build.
- **Report download is stretch.** The backend `report_gen.py` and `reports.py` router already work. If time permits, add a "Download Report" button that calls `GET /build/{id}/report` and renders the markdown or triggers a download. Don't block the spec on this — it's S3 in the PRD backlog.

---
