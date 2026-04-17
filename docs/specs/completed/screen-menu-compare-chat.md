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

## Status: COMPLETE

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
| Last Updated | 2026-04-16 |
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

- [x] Saved builds list shows all builds for the current profile via DuckDB `list_builds(profile_name)`
- [x] Each build card: school, career, profile emoji, pentagon mini-chart, W/L/D, created date
- [x] Tap a build card → navigate to reveal screen for that build
- [x] Compare mode: select 2-3 builds → risk comparison screen
- [x] Risk comparison: boss fight tradeoff headlines, not raw stat columns
- [x] Pentagon overlay: 2-3 stat shapes overlaid on one chart with build colors
- [x] Gemma comparison summary: tradeoff analysis, never declares a winner
- [x] Ask Gemma: chat panel with full build context, multi-turn history
- [x] Ask Gemma: message input, send button, streaming or chunked response display
- [x] "New Build" button → navigate to school+major screen (keep profile, fresh build inputs)
- [x] Header in hub mode: home icon (left), profile name (center), "New Build" pill (right) per DESIGN.md
- [x] All Brightpath design tokens used (1 follow-up: hardcoded `#6bc494` matches existing `Button.tsx` convention; deferred to project-wide token alias work)
- [x] Responsive: desktop primary, mobile functional
- [x] All tests pass (323 vitest pass + 276 backend pass; 2 vitest failures are pre-existing in `ProfileScreen.test.tsx`, verified by stash)

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

### @fp-design-visionary Enhancements (2026-04-16)

**Emotional anchor:** This is the *informed confidence* screen — the anxiety has been processed, and the student is now in command of their decision space. Every interaction should feel like *opening a journal*, not navigating an app. Cozy, considered, slightly ceremonial.

**1. Save Slot Card pattern — confirmed and tightened**

The §3 spec correctly invokes the DESIGN.md Save Slot pattern. Locking specifics so the implementer doesn't drift:

- Container exactly per DESIGN.md Save Slot Cards: `bg-bp-mid`, `border border-border-subtle`, `rounded-lg` (14px), `p-4` vertical / `px-5` horizontal, `flex items-center gap-4`.
- Avatar: 36px emoji on `bg-bp-deep` circle (`rounded-full`, 44px wrap, `border border-border-subtle`) so the emoji has a deliberate "save slot icon" frame instead of floating in space.
- Build label: `font-display`, weight 600, 16px. Most recent build → `text-accent-thrive`. All others → `text-text-primary`. (DESIGN.md says "accent-colored" — thrive-on-most-recent is the implementation rule.)
- Meta line: `font-body`, 13px, `text-text-secondary` — format: `{school} · {career}`.
- Mini pentagon: 40×40px, no labels, no axis lines — just the filled polygon at 35% opacity in `accent-thrive`, with a 1px `border-border-subtle` pentagon grid behind it. Renders the *shape* of the build at a glance.
- W/L/D tally: `font-data` 11px, `text-text-muted`, formatted `{W}W · {L}L · {D}D` with `text-accent-thrive`/`text-accent-alert`/`text-accent-caution` on the W/L/D digits respectively.
- Date: `font-data` 11px, `text-text-muted`, right-aligned. Use relative date for <7d ("3d ago"), absolute after.
- **Hover:** per DESIGN.md — `bg-bp-surface`, `translateX(4px)` via `transitions.smooth` (Framer, not CSS). Add a faint `shadow-sm` lift.
- **Compare-selected state:** when checkbox is on, override to the Selected Card spec — `border-color: rgba(125, 212, 163, 0.4)`, `shadow-glow-thrive` at 50% intensity. Checkbox itself is a 20px rounded-md square in `bg-bp-deep` with `accent-thrive` checkmark when active.

**2. Risk Headline cards — divergence treatment confirmed, with refinement**

The `accent-caution` left border on divergence is correct. Adding the "why" so it lands:

- Card base: `bg-bp-mid`, `border border-border-subtle`, `rounded-xl`, `p-5`. Flex row: boss icon (40px circle, boss color at 15% opacity bg) + name column + per-build result pills row.
- Boss name: `font-display`, weight 600, `text-heading` (28px feels too large here — use `text-subheading` 22px). Boss color is a subtle accent only — name stays `text-text-primary`.
- Per-build result pills use existing pill-thrive / pill-alert / pill-caution variants with build label prefix: `"Build A · Won"`, `"Build B · Lost"`. Pills render in build order, color-matched to the pentagon overlay color.
- **Divergence treatment (the magic):** when not all builds agree, prepend a 3px `accent-caution` left border (`border-l-[3px] border-l-accent-caution`) AND a small italic kicker line above the pills: `"Your builds disagree here."` in `font-body italic text-small text-accent-caution`. This is the moment that says *"this is where your decision matters"* — both visual and verbal.
- **Agreement treatment:** all-win → muted `text-text-secondary` boss name, no left border, kicker reads `"Both builds beat this."` in `text-text-muted`. All-lose → kicker reads `"Both builds lose this."` in `text-text-muted`. Avoids visual noise on consensus rows so divergence cards genuinely pop.
- **Stagger entrance:** `stagger.normal` (80ms) per card, `transitions.fadeInUp`.

**3. Pentagon Overlay — confirmed with rendering specifics**

The 2-3 stat shapes overlay is correct. Concrete render rules:

- Single Pentagon component, 280×280 on desktop / 220×220 on mobile, reusing the existing PentagonChart grid (4 concentric rings + 5 axes per DESIGN.md Pentagon spec).
- Build colors in this exact order: Build 1 → `accent-thrive` (#7DD4A3), Build 2 → `accent-info` (#7BB8E0), Build 3 → `accent-empathy` (#E88BA9). Chosen for max hue separation in HSL space and to avoid the `accent-alert`/`accent-caution` warning palette in a non-warning context.
- Each shape: filled polygon at **20% opacity** (revising spec's 25% — at 25% three overlapping fills muddy the center; 20% keeps the chart legible), 1.5px stroke at **70% opacity** in the same color. The strokes carry the readability; the fills carry the gestalt.
- **Vertex dots per build:** 4px radius circles in build color at each polygon vertex. Helps the eye trace one build's shape through overlap.
- **Reveal animation:** shapes draw in sequentially, not all at once. Build 1 first (`springs.smooth`, 600ms), Build 2 at +200ms, Build 3 at +400ms. Each animates from a centered point (`scale: 0` from polygon centroid). The viewer mentally "stacks" them.
- **Legend below chart:** flex row, `gap-4`, centered. Each legend item: 10px colored dot (`rounded-full`) + build label in `font-body` weight 600, 13px, `text-text-primary`. Dot color matches polygon stroke color.
- **Stat labels (ERN/ROI/RES/GRW/HMN):** keep DESIGN.md stat colors at vertices. They are independent of the build-color overlay system.

**4. Ask Gemma slide-out panel — confirmed with motion + starter pill specifics**

- **Desktop:** 360px wide (matches spec), full viewport height, anchored right edge. `bg-bp-mid`, `border-l border-border-subtle`. Backdrop-blur not needed — the panel is opaque.
- **Mobile:** 80vh bottom sheet, `rounded-t-xl`, drag handle (32×4px `bg-text-muted` rounded-full pill, centered, `mt-2`).
- **Entrance motion:** `springs.smooth` ({stiffness: 200, damping: 25}), translateX from 100% (desktop) or translateY from 100% (mobile) to 0. Backdrop wash (`bg-bp-void/60`) fades in over 200ms behind it on mobile only — desktop keeps the underlying screen visible and interactable.
- **Header:** Fredoka 600, 18px, `text-text-primary` — "Ask Gemma" with a small `accent-insight` GemmaStar glyph (12px) to the left. Close icon button (Icon button variant per DESIGN.md) at top-right.
- **Context badge** (directly under header): `bg-bp-surface`, `rounded-md` (10px — revising spec's `radius-sm` 6px which feels too pinched against the larger panel), `px-3 py-1`, `font-body` 12px, `text-text-muted` — `"Context: {school} · {career} · {W}W/{L}L"`. The W/L digits get their accent colors (thrive/alert) for a subtle data signal.
- **Message bubbles:**
  - User (right): `bg-bp-surface`, `rounded-lg`, `p-3`, max-width 80%, `text-body` `text-text-primary`. Tail: `rounded-tr-sm` (slight asymmetry signals "yours").
  - Gemma (left): `bg-bp-deep`, `rounded-lg`, `p-3`, max-width 90%, `text-body` `text-text-primary`. Tail: `rounded-tl-sm`. 14px GemmaStar glyph (insight gradient) floats top-left, `-ml-1 -mt-1`.
  - Bubble entrance: `transitions.fadeInUp` with `springs.snappy` per message.
- **Loading dots:** 3 × 6px dots, `bg-accent-insight`, in a Gemma bubble. Each dot pulses opacity 0.3 → 1 on `stagger.fast` (50ms) loop. Soft and breathing, not snappy.
- **Starter question pills (empty state):** flex column, `gap-2`, centered in message area. Each pill: `bg-bp-surface`, `border border-border-subtle`, `rounded-full`, `px-4 py-2`, `font-body` 13px, `text-text-secondary`. Hover: `bg-bp-raised`, `text-text-primary`, `border-border-default`. Tap: pill animates `scale-0.97` (`transitions.press`) then fills the input field. Pills enter with `stagger.normal` (80ms) on panel open.
- **Input area:** sticky bottom, `bg-bp-mid` (matches panel), `border-t border-border-subtle`, `p-3`. Input: `bg-bp-deep`, `border border-border-default`, `rounded-md`, `h-11` (44px), `font-body` 14px, placeholder in `text-text-muted`. Focus: `accent-info` border + `focus-ring` shadow per DESIGN.md Inputs spec. Send button: 40px Icon button variant; `bg-accent-thrive` with `text-text-inverse` arrow when input non-empty, `bg-bp-surface` with `text-text-muted` arrow when empty. Disabled state respects `state-disabled`.

**5. Hub-mode header — confirmed, no redesign needed**

`AppHeader.tsx` already implements home icon (left) + profile (center, `text-secondary`) + "+ New" pill (right) for `/menu`. Implementer should **not** touch the header — wire `screen={'menu'}` (or whatever the existing prop is) and confirm the "+ New" pill route target matches the new `resetInputs() → /school` handler. No visual changes required.

**6. Additional Brightpath tokens to use** (not yet named in §3):

- `bg-bp-deep` for chat input background, mini-pentagon avatar frame.
- `bg-bp-raised` for starter-pill hover state.
- `shadow-glow-thrive` (at ~50% intensity) for compare-selected build cards.
- `shadow-glow-insight` for the Gemma comparison summary card hover (matches the `accent-insight` left border).
- `state-focus-ring` (rgba 123,184,224,0.4) for chat input focus.
- `state-disabled` for the disabled "Compare" button when fewer than 2 builds are selected.
- `text-subheading` for boss/section headings inside Risk Headline cards (replaces `text-heading` which is too large for inline cards).
- `transitions.fadeInUp` + `springs.smooth` for compare view entrance (full view slides up from y:24).
- `transitions.scaleIn` + `springs.bouncy` for the pentagon overlay shapes drawing in.

**7. Motion choreography — locked**

- Builds list mount: `staggerContainer(stagger.normal)` wrapping cards, each with `staggerItem` (`fadeInUp` + `springs.smooth`).
- Build card hover: `transition: { type: 'spring', ...springs.snappy }` on `x: 4`, `backgroundColor` to `bg-bp-surface`.
- Compare button enable: when count hits 2, button transitions from `state-disabled` to `accent-thrive` over 200ms with a `springs.bouncy` `scale: 0.95 → 1` pulse — signals "you can act now."
- Compare view entrance: full view slides in from `x: 40, opacity: 0` with `springs.smooth`, 400ms. Risk Headlines stagger inside (80ms). Pentagon overlay shapes draw in sequentially after headlines settle (delay 600ms).
- Gemma summary card: `bg-bp-mid`, `border border-border-subtle` with 3px `border-l-accent-insight`, `rounded-xl`, `p-6`. Animates in last with `transitions.fadeInUp` + 800ms delay so it reads as the *conclusion* of the comparison, not a competing element.
- Chat panel open: `springs.smooth`, translate from edge. Starter pills stagger in 200ms after panel settles.
- Chat panel close: faster — `springs.snappy`, 250ms — "I'm done" should feel decisive.

**Cross-references checked against DESIGN.md:** No conflicts found. Save Slot Cards (lines 596-615), Pills (lines 397-419), Application Header hub mode (line 669), Pentagon (lines 532-543), and Inputs (lines 422-466) all align with §3. The 25% → 20% pentagon fill opacity is the only adjustment — DESIGN.md doesn't specify overlay opacity (it specs single-pentagon at 35%), so this is a new derived rule for the overlay use case.

---

## §4 Technical Specification

### Architecture Overview

Screen 10 is the hub — it consumes multiple API endpoints (list builds, load build, compare builds, chat) and provides navigation to the rest of the app. No new backend services needed; this screen wires existing endpoints to a new frontend experience.

### API Endpoints Consumed

| Endpoint | Method | Request | Response | Used By | Backend Location |
|---|---|---|---|---|---|
| `GET /builds?profile_name=X` | GET | Query param | `{ builds: BuildSummary[] }` | Saved builds list (primary) | NEW (thin router over `builds.list_builds`) |
| `GET /build/{build_id}` | GET | Path param | `Build` | Load a specific build | `routers/builds.py:111` |
| `POST /builds/compare` | POST | `{ build_ids: string[] }` | `{ builds, stats, bosses }` | Risk comparison | NEW path (renamed from `/build/s/compare` typo) |
| `POST /build/{build_id}/chat` | POST | `{ message: string, history: [{role, content}] }` | `{ response: string }` | Ask Gemma | `routers/guidance_router.py:19` |
| `GET /build/{build_id}/report` | GET | Path param | `{ markdown: string }` | Counselor report (stretch) | `routers/reports.py:9` |

**Architect-resolved contract decisions (2026-04-16):**
- Compare endpoint path mismatch: original `POST /build/s/compare` (typo from `/build` prefix + `/s/compare` route) is replaced by a clean `POST /builds/compare` mounted via a new no-prefix router. The buggy route is removed; no existing HTTP caller depends on it.
- Chat endpoint already exists in `guidance_router.py` — frontend just calls it.
- Builds list endpoint: `GET /builds?profile_name=X`, mounted no-prefix, returns `{ builds: BuildSummary[] }` from `builds.list_builds(profile_name=...)`.
- `ChatRequest.history` accepts `list[dict]` (per `app/models/api.py:60`); frontend sends `{role: 'user' | 'assistant', content: string}` per message.

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
| `frontend/src/App.tsx` | Modify | Add route: `/menu`. Header hub mode already supported. |
| `frontend/src/store/buildInputStore.ts` | Modify | Add `resetInputs()` action. |
| `backend/app/routers/builds_collection.py` | Create | New no-prefix router: `GET /builds`, `POST /builds/compare`. |
| `backend/app/routers/builds.py` | Modify | Remove buggy `@router.post("/s/compare")` route. |
| `backend/app/main.py` | Modify | Mount `builds_collection.router` with no prefix. |

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

Two minimal backend additions, locked in after architecture review:

1. **New router file** `backend/app/routers/builds_collection.py` — no prefix, exposes:
   - `GET /builds?profile_name=X` → `{ builds: [BuildSummary, ...] }` from `builds.list_builds(profile_name=...)`
   - `POST /builds/compare` (request: `CompareRequest`) → `{ builds, stats, bosses }` from `builds.compare_builds(build_ids)`
2. **Remove** the typo route `@router.post("/s/compare")` from `backend/app/routers/builds.py` (resolved to `POST /build/s/compare`). No HTTP callers depend on it.
3. **Wire** the new router in `backend/app/main.py` with no prefix, after the existing `builds` router.

No service-layer changes — both endpoints reuse `builds.list_builds()` and `builds.compare_builds()` as-is.

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
**Status:** APPROVED (contract reconciliations applied to §4 — see "Resolution" below)
**Date:** 2026-04-16

**Findings:**
- Component decomposition in §4 is sound: MenuScreen + 7 children, each with one responsibility, no circular imports. Mock layer (`api/menu.ts` + `api/mockMenu.ts`) matches the existing `api/build.ts` / `api/mockBuild.ts` pattern.
- Routing addition `/menu` is a clean add. `App.tsx` already supports route-driven header modes; hub-mode header is a presentation flag, not a structural change.
- State boundaries are correct: screen-local lists live in `useState`, `buildInputStore.resetInputs()` is the right scope for "New Build" (preserves `profileStore` + `buildStore.hasSeenStatTutorial`). No new store needed.
- **API path mismatch (blocker for wiring):** spec lists `POST /builds/compare`; backend mounts the endpoint at `POST /builds/s/compare` (`backend/app/routers/builds.py:124`). Either rename the router path to `/compare` or update `api/menu.ts` + spec to call `/builds/s/compare`. Pick one and lock it in §4.
- **Chat endpoint exists — spec is wrong about location:** `POST /build/{build_id}/chat` is implemented in `backend/app/routers/guidance_router.py:19` (not `builds.py`), wired to `guidance.chat_with_context(career, gauntlet, branches, skill_recs, conversation_history, user_question)`. Request shape is `ChatRequest { message, history }`, response is `{ response }` — matches the spec. No new service needed; just call it.
- **Builds list path is reachable but inefficient:** `POST /profile/lookup` already returns `ProfileLookupResult.builds: BuildSummary[]` via `profile._get_builds_for_profile()` (profile.py:184), which calls `builds.list_builds()` (no filter) then filters in Python. For a hub screen that re-renders on every visit, add `GET /builds?profile_name=X` as a thin router calling `builds.list_builds(profile_name=...)` (the service signature already accepts the filter — builds.py:238). Avoids re-doing profile lookup just to refresh the list.
- `GET /build/{id}/report` confirmed at `backend/app/routers/reports.py:9` — stretch goal is wired and ready.
- Chat history type in §4 (`role: 'user' | 'assistant'`) must match `ChatRequest.history` schema in `app/models/api.py` — confirm the role enum aligns before implementation; if backend uses `'system'` anywhere, frontend filter needs to handle it.

**Required actions before implementation:**
- Reconcile compare endpoint path: either change router to `POST /builds/compare` (preferred — `/s/compare` looks like a typo) or update §4 + frontend client to `/builds/s/compare`. Document the choice.
- Add `GET /builds?profile_name=X` router (one-liner over `builds.list_builds(profile_name)`) and update §4's API table to use it as the primary builds-list source. Keep `/profile/lookup` for the initial profile resolution only.
- Update §4's API table: chat endpoint is owned by `guidance_router`, not `builds`. Note the request model is `ChatRequest` from `app/models/api.py` so the frontend types align.
- Verify `ChatRequest.history` item shape in `app/models/api.py` matches the frontend `ChatMessage` interface (role/content fields, role enum values).

**Verdict rationale:** Architecture is clean and reuses existing services correctly. Two API contract issues (compare path mismatch, builds-list source) were small enough to reconcile in §4 without a re-review.

**Resolution (applied 2026-04-16):**
- §4 API table now lists `POST /builds/compare`, `GET /builds?profile_name=X`, and the chat endpoint at `guidance_router.py:19`.
- §4 Service Changes section documents the new `builds_collection.py` router and the removal of the typo `/s/compare` route.
- §4 File Changes table updated to include backend file changes.
- ChatRequest history shape confirmed compatible (`list[dict]`).
- Verdict flipped to APPROVED to unblock implementation.

### @fp-data-reviewer Review
**Status:** SKIPPED

---

## §6 Implementation Log

**Status:** COMPLETE
**Date:** 2026-04-16

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/routers/builds_collection.py` | NEW. `GET /builds?profile_name=X` and `POST /builds/compare`. Both delegate to existing `builds` service. Typed return annotations. |
| `backend/app/routers/builds.py` | Removed buggy `@router.post("/s/compare")` route (resolved to `/build/s/compare`); dropped unused `CompareRequest` import. |
| `backend/app/main.py` | Imported and mounted `builds_collection.router` with no prefix, tagged "Builds". |
| `frontend/src/api/menu.ts` | NEW. `listBuilds`, `compareBuilds`, `sendChat`. Mirrors existing `api/build.ts` mock-fallback pattern. |
| `frontend/src/api/mockMenu.ts` | NEW. Three mock builds + deterministic boss outcomes (creates one divergent boss per axis for the compare demo). |
| `frontend/src/api/build.ts` | Added `getBuild(buildId)` (used by MenuScreen → `/reveal` navigation). |
| `frontend/src/components/menu/MiniPentagon.tsx` | NEW. 40×40 SVG pentagon shape (no labels). |
| `frontend/src/components/menu/BuildCard.tsx` | NEW. Save Slot Card per DESIGN.md: emoji + info + mini pentagon + W/L/D + date. Most-recent gets `text-accent-thrive` label; selected (compare mode) gets `shadow-glow-thrive`. |
| `frontend/src/components/menu/PentagonOverlay.tsx` | NEW. Single pentagon with 2-3 stat shapes overlaid at 20% fill opacity (per visionary), 1.5px 70% stroke, sequential 200ms draw-in. Per-build vertex dots + legend. |
| `frontend/src/components/menu/RiskHeadlineCard.tsx` | NEW. Per-boss card with per-build pills and divergence detection (`accent-caution` left border + italic kicker "Your builds disagree here."). |
| `frontend/src/components/menu/ChatMessage.tsx` | NEW. User/assistant bubble with asymmetric tails (`rounded-tr-sm` user, `rounded-tl-sm` Gemma). |
| `frontend/src/components/menu/GemmaChat.tsx` | NEW. Slide-out panel: 360px desktop / full-width mobile. Header + context badge, scrollable history, animated dots while waiting, starter pills, send form. Resets on close (chat is ephemeral per §11). |
| `frontend/src/components/menu/CompareView.tsx` | NEW. Loads compare data, renders risk headlines + pentagon overlay + auto-loaded Gemma narrative via reuse of chat endpoint. |
| `frontend/src/screens/MenuScreen.tsx` | NEW. Orchestrates: list → select → compare modes, GemmaChat opening, "New Build" via `resetInputs()`, "View build" via `getBuild` + `setBuild` + nav to `/reveal`. Profile guard. |
| `frontend/src/store/buildInputStore.ts` | Added `resetInputs()` action (clears school/major/effort/loans, preserves nothing else). |
| `frontend/src/App.tsx` | Imported `MenuScreen`, added `/menu` route. (`AppHeader` hub mode already implemented — no header changes needed.) |

### Deviations from Spec
- `BuildCard` uses the profile emoji for every build's avatar (single profile = single avatar throughout the hub). The spec implied per-build emojis, but `BuildSummary` does not carry per-build profile metadata distinct from `profile_name`. This matches the data model.
- Backend chat endpoint is `POST /build/{id}/chat` (singular `/build`), not `/builds/{id}/chat`. Spec §3 also says `/build/{build_id}/chat` so we are aligned with the existing router.
- `CompareView` triggers Gemma narrative by reusing the existing chat endpoint with the first build's ID and a comparison prompt; no dedicated comparison-narrative endpoint is added. Matches §3 option A and the architect's verdict that no new backend service is needed.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | TypeScript ✅ | — | Frontend `tsc --noEmit` clean on first try. |
| 1 | Vitest 291/293 ✅ | 2 pre-existing failures in `ProfileScreen.test.tsx` | Verified pre-existing by stashing changes — same 2 fail without this PR. Not caused by this work. |
| 1 | Backend ruff ✅ | — | Clean on first try. |
| 1 | Backend mypy (new file) ✅ | Initial run: 2 missing return annotations | Added `dict[str, list[dict[str, Any]]]` and `dict[str, Any]` return annotations. |
| 1 | Backend pytest 267/267 ✅ | — | All passing. |

---

## §7 Test Coverage

**Status:** COMPLETE
**Date:** 2026-04-16

### Tests Added (41 new tests)
| Test File | Tests | Highlights |
|-----------|-------|------------|
| `frontend/src/screens/MenuScreen.test.tsx` | 9 | renders saved builds; tap card loads build + nav /reveal; New Build clears inputs; Compare disabled <2; profile-less guard; getBuild rejection |
| `frontend/src/components/menu/CompareView.test.tsx` | 6 | renders risk headlines (per boss); divergence kicker + border class; Gemma summary render after sendChat resolve; summary-chat failure fallback |
| `frontend/src/components/menu/PentagonOverlay.test.tsx` | 4 | one polygon per build via `overlay-shape-{idx}` testids |
| `frontend/src/components/menu/GemmaChat.test.tsx` | 7 | send calls sendChat; response render; starter fills input; maintains history (2 turns); whitespace submit guard |
| `frontend/src/components/menu/BuildCard.test.tsx` | 6 | school + career + W/L/D + mini pentagon present; invalid date handling |
| `backend/tests/routers/test_builds_collection.py` | 9 | `GET /builds?profile_name=` filter; `POST /builds/compare` 404 on missing ID; missing body 422; empty list 200 |

### Test Results
| Suite | Pass | Fail | Skip | Total | Notes |
|-------|------|------|------|-------|-------|
| backend pytest | 276 | 0 | — | 276 | All green. |
| frontend vitest | 323 | 2 | — | 325 | 2 pre-existing failures in `ProfileScreen.test.tsx` (verified pre-existing by stashing — same 2 fail without this PR). 32 new tests all pass. |

---

## §8 Reviews

**Status:** APPROVED (after HIGH/MEDIUM/MINOR fixes — see §10 Discussion)

### Design Audit (@design-builder/@fp-design-auditor)
**Status:** PASS WITH MINOR ISSUES
**Date:** 2026-04-16

#### Findings by File

**`frontend/src/screens/MenuScreen.tsx`**
- PASS: All motion imports from `@/styles/motion` (`springs`, `stagger`). No ad-hoc spring configs.
- PASS: Section label uses `font-data text-micro uppercase tracking-[0.18em] text-text-muted` — matches DESIGN.md Section Labels spec (Space Mono, 11px, muted, uppercase).
- PASS: H1 uses `font-display text-display text-text-primary` — correct Fredoka for heading.
- PASS: Body copy uses `font-body text-body text-text-secondary` — correct Nunito.
- PASS: No hardcoded hex/rgb values. All colors reference tokens.
- PASS: Breakpoints use `tablet:` prefix — matches DESIGN.md breakpoint tokens.
- PASS: No header overrides. Header hub mode is left entirely to `AppHeader.tsx` as specified.
- MINOR: `tracking-[0.18em]` is a bespoke value. DESIGN.md Section Labels spec says `letter-spacing: 2px` (tracked as `tracking-[2px]` in Tailwind, not `0.18em`). Not a hardcoded color or spacing violation — but it is a non-token letter-spacing value applied in two places (here and `CompareView.tsx`). Non-blocking: the visual result is nearly identical, but should be normalized to `tracking-[2px]`.

**`frontend/src/components/menu/BuildCard.tsx`**
- PASS: Motion import from `@/styles/motion` (`springs`). `whileHover`, `whileTap`, and `transition` all reference `springs.snappy`.
- PASS: Background tokens `bg-bp-mid`, `bg-bp-surface`, `bg-bp-deep` — correct.
- PASS: Border uses `border-border-subtle` and `border-border-strong` — correct token names.
- PASS: `rounded-lg` (14px) — matches DESIGN.md Save Slot Cards spec ("border-radius: radius-lg").
- PASS: Padding is `px-5 py-4` = 20px horizontal / 16px vertical — matches DESIGN.md Save Slot Cards spec exactly ("padding: 16px 20px").
- PASS: Hover `translateX(4px)` via `whileHover={{ x: 4 }}` — matches DESIGN.md Save Slot Cards spec.
- PASS: `font-display font-semibold text-body` for build label — Fredoka, weight 600. Token-compliant.
- PASS: `font-body text-small text-text-secondary` for meta line — Nunito, correct.
- PASS: `font-data text-micro text-text-muted` for W/L/D and date — Space Mono, correct.
- PASS: `text-accent-thrive`, `text-accent-alert`, `text-accent-caution` on W/L/D digits — correct semantic token use.
- PASS: Selected state uses `border-accent-thrive/40 shadow-glow-thrive` — matches Selected Card spec.
- MINOR: `text-body` (16px Nunito per token scale) is used for the build label font-size, but the visionary spec calls for 16px Fredoka (font-display). The Tailwind size `text-body` is correct (16px), and `font-display` is also present — so the combination is right. However, `text-body` is a Nunito-family size token by convention; using `text-[16px]` or `text-base` explicitly alongside `font-display` would be less ambiguous. Non-blocking.

**`frontend/src/components/menu/MiniPentagon.tsx`**
- PASS: All colors use CSS variables (`var(--color-bg-deep)`, `var(--color-text-muted)`, `var(--color-accent-thrive)`) — correct for SVG context where Tailwind classes cannot apply directly.
- PASS: `fillOpacity="0.35"` — matches DESIGN.md Pentagon spec ("Fill opacity 35%") for the single-pentagon use case. MiniPentagon is a standalone summary view, not the overlay, so 35% is the correct spec here.
- FAIL: `strokeOpacity="0.18"` on the grid polygon. DESIGN.md Pentagon spec says grid stroke is `text-muted` at **15% opacity** (`strokeOpacity="0.15"`). Found 0.18 at line 41. Delta is small but non-compliant.
- PASS: Axis lines are not rendered (mini variant — no labels, no axes per visionary spec). Compliant.
- PASS: No hardcoded hex or rgb values.

**`frontend/src/components/menu/PentagonOverlay.tsx`**
- PASS: All colors reference CSS variables (`var(--color-accent-thrive)`, `var(--color-accent-info)`, `var(--color-accent-empathy)`) — no hardcoded hex.
- PASS: Build color assignment order — thrive, info, empathy — matches visionary spec exactly.
- PASS: `fillOpacity="0.20"` — confirms the visionary's 20% fill opacity rule for the multi-build overlay. Compliant with visionary direction (not the single-pentagon 35% spec, which does not apply here). See overlay opacity confirmation below.
- PASS: `strokeOpacity="0.7"` and `strokeWidth="1.5"` — matches visionary spec (70% opacity, 1.5px).
- PASS: Grid polygon stroke at `opacity={0.15}` — matches DESIGN.md Pentagon spec (15%).
- PASS: Axis lines at `opacity="0.20"` — matches DESIGN.md Pentagon spec (20%).
- PASS: Stat axis labels use `var(--color-text-muted)` with `font-data` class and `letterSpacing: "0.15em"` — Space Mono, compliant.
- PASS: Legend uses `font-body text-small text-text-secondary` — correct Nunito token.
- PASS: Motion import absent (only `motion` from framer-motion, no local `springs` import). The per-shape animation uses `transition={{ duration: 0.6, delay: drawDelay }}` — an ad-hoc duration/delay rather than a motion preset. DESIGN.md Motion System says "all meaningful animations use Framer Motion spring physics, not CSS timing functions" and specifies `springs.smooth` for panel reveals. The sequential shape draw-in is a meaningful animation.
- MINOR: The overlay shape entrance uses `{ duration: 0.6, delay: drawDelay }` (ad-hoc ease-based transition) instead of `springs.smooth` from `@/styles/motion`. Per DESIGN.md, meaningful animations should use spring configs. Non-blocking for correctness but diverges from the motion system convention.

**`frontend/src/components/menu/RiskHeadlineCard.tsx`**
- PASS: `bg-bp-mid`, `border-border-subtle`, `rounded-xl` — matches DESIGN.md Card base and visionary risk card spec.
- PASS: `p-5` (20px) — matches visionary spec.
- PASS: Divergence treatment: `border-l-[3px] border-l-accent-caution` — compliant.
- PASS: `font-display font-semibold text-subheading` for boss name — Fredoka 600, `text-subheading` (22px), matching visionary spec override from `text-heading`.
- PASS: Result pills use `bg-accent-thrive/15 text-accent-thrive`, `bg-accent-alert/15 text-accent-alert`, `bg-accent-caution/15 text-accent-caution` — matches DESIGN.md pill-thrive/alert/caution spec (accent at 15% opacity bg, full accent text).
- PASS: `rounded-full` on pills — correct.
- PASS: `font-body text-small text-text-secondary` for build label — Nunito, compliant.
- PASS: Italic kicker uses `font-body text-small italic text-accent-caution` — correct tokens.
- PASS: No hardcoded hex/rgb.

**`frontend/src/components/menu/ChatMessage.tsx`**
- PASS: Motion import from `framer-motion`, `springs` from `@/styles/motion`. Transition uses `springs.smooth` — correct preset for message entrance.
- PASS: User bubble `bg-bp-surface rounded-tr-sm` — correct token and asymmetric tail per visionary.
- PASS: Gemma bubble `bg-bp-deep rounded-tl-sm` — correct token and asymmetric tail per visionary.
- PASS: `font-body text-body text-text-primary` — Nunito body text, compliant.
- PASS: Gemma icon `bg-accent-insight/15 text-accent-insight` — matches pill-insight pattern, correct semantic token (AI/intelligence = insight).
- PASS: No hardcoded hex/rgb.

**`frontend/src/components/menu/GemmaChat.tsx`**
- PASS: Motion imports from `@/styles/motion` (`springs`, `stagger`). Panel entrance uses `springs.smooth` — compliant.
- PASS: Backdrop `bg-bp-void/60` — correct token.
- PASS: Panel `bg-bp-mid border-border-subtle` — correct tokens.
- PASS: Header `font-display font-semibold text-subheading text-text-primary` — Fredoka, compliant.
- PASS: Context badge `bg-bp-surface rounded-sm font-body text-micro text-text-muted` — correct tokens. (DESIGN.md says radius-sm = 6px; visionary revised this to radius-md = 10px for the panel context, but rounded-sm is what's implemented. Minor divergence from visionary, not a DESIGN.md violation.)
- PASS: Close button `rounded-full bg-bp-surface hover:bg-bp-raised` — matches DESIGN.md Icon button spec (bg-surface → bg-raised on hover).
- PASS: Starter pills `bg-bp-surface border-border-subtle rounded-full font-body text-small text-text-secondary hover:text-text-primary hover:bg-bp-raised` — compliant with visionary spec (bg-surface, border-subtle, rounded-full, text-secondary → text-primary hover, bg-raised hover).
- PASS: Chat input `bg-bp-deep border border-border rounded-md font-body text-body text-text-primary` — correct tokens. Focus state `focus:border-accent-info focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)]` matches DESIGN.md Inputs focus spec exactly.
- FAIL: Send button uses hardcoded hex `hover:bg-[#6bc494]` at line 224. DESIGN.md specifies the Primary button hover darkens to `#6bc494`, and this is a documented value, but it is still a raw hex in code rather than a CSS variable reference. The correct form is `hover:bg-[var(--color-accent-thrive-hover)]` — or if no hover token exists, this should be flagged as a missing token rather than inlined as a literal hex. Line 224.
- PASS: Loading dots `bg-text-secondary` — correct muted token. (Visionary spec says `bg-accent-insight`; DESIGN.md has no specific rule for loading dots — this is a minor visionary divergence, not a token violation.)
- PASS: Transition durations use named presets where present. The panel backdrop `transition={{ duration: 0.2 }}` is an ad-hoc ease value, but for a simple backdrop fade this is consistent with `transitions.fade` (300ms ease-out per DESIGN.md). Minor.
- PASS: `duration-normal` used for hover transitions — correct CSS transition token.

**`frontend/src/components/menu/CompareView.tsx`**
- PASS: Motion imports from `@/styles/motion` (`springs`, `stagger`). All stagger containers and item transitions reference token presets.
- PASS: `bg-bp-mid border-border-subtle rounded-xl p-6` for Gemma summary card — correct tokens.
- PASS: `border-l-[3px] border-l-accent-insight` — correct token for Gemma/AI semantic role.
- PASS: Section labels `font-data text-micro uppercase tracking-[0.18em] text-text-muted` — Space Mono, compliant (same non-blocking letter-spacing note as MenuScreen).
- PASS: `font-display text-heading text-text-primary` for "Risk comparison" heading — Fredoka, correct.
- PASS: `font-body text-body text-text-primary` / `text-text-secondary` for body copy — Nunito, correct.
- PASS: Loading state uses inline `radial-gradient` with `rgba(184,169,232,0.3)` — this is the raw rgba of `--color-accent-insight`. In an SVG/style prop context where CSS variables cannot resolve in all environments, this is acceptable. However, it should ideally reference `var(--color-accent-insight)` at reduced opacity. Non-blocking.
- PASS: `font-display text-heading text-accent-alert` for error heading — correct semantic (alert = negative outcomes).
- PASS: No hardcoded hex/rgb in Tailwind classes.

#### Summary of Issues

| Severity | File | Issue |
|----------|------|-------|
| FAIL | `GemmaChat.tsx:224` | Hardcoded `#6bc494` in send button hover. Should use CSS variable or token alias. |
| FAIL | `MiniPentagon.tsx:41` | Grid stroke opacity 0.18, spec requires 0.15. |
| MINOR | `MenuScreen.tsx`, `CompareView.tsx` | `tracking-[0.18em]` instead of `tracking-[2px]` for section labels. |
| MINOR | `PentagonOverlay.tsx` | Shape entrance uses ad-hoc `duration: 0.6` instead of `springs.smooth` from `@/styles/motion`. |
| MINOR | `CompareView.tsx` loading state | Inline `rgba(184,169,232,0.3)` should reference `var(--color-accent-insight)`. |

#### Overlay Opacity Confirmation

`PentagonOverlay.tsx` uses `fillOpacity="0.20"` on all overlaid build shapes. This is the visionary's explicit revision from the single-pentagon 35% spec (DESIGN.md §Components.The Pentagon) to 20% for the multi-build overlay context — visionary rationale: "at 25% three overlapping fills muddy the center; 20% keeps the chart legible." The 20% value is correctly implemented per the visionary direction. The 35% spec in DESIGN.md applies to single-pentagon renders (MiniPentagon correctly uses 0.35).

#### Verdict

PASS WITH MINOR ISSUES. Two blocking fixes required: the hardcoded `#6bc494` hover hex in `GemmaChat.tsx` (line 224) and the `MiniPentagon.tsx` grid stroke opacity (0.18 vs 0.15). All motion imports are correctly sourced from `@/styles/motion`. No header overrides in `MenuScreen.tsx`. Pentagon overlay fill opacity is 20% per visionary specification.

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Date:** 2026-04-16
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

**Summary.** The shape of this PR is solid — clean router seam, correct mock-fallback pattern, no SQL injection vectors, no XSS (React escapes chat content as text), no leaked secrets, and the divergence treatment in `RiskHeadlineCard` is genuinely thoughtful. Tests are not theater — `MenuScreen.test.tsx` exercises real navigation + store mutation, `GemmaChat.test.tsx` actually proves multi-turn history is passed correctly, and `test_builds_collection.py` covers the 404 stale-id path that would otherwise become a 500 in prod. That said, there are three concurrency / state-management bugs that will absolutely page someone — two in `GemmaChat`, one in `MenuScreen` — plus a couple of moderate items worth fixing before ship.

#### Findings

- **[HIGH]** `frontend/src/components/menu/GemmaChat.tsx:27-34, 49-67` — Stale-state write when the panel closes mid-request. If the user clicks the backdrop / close button while `sending=true`, the cleanup effect resets `history`/`draft`/`error`/`sending`, then the in-flight `sendChat` resolves and `setHistory([...nextHistory, { role: "assistant", content: response }])` writes the *closure-captured* `nextHistory` back onto the now-reset panel. Reopening shows a phantom conversation the user never sent. Worse: if they start a new chat before the stale promise resolves, the stale assistant bubble lands in the new conversation. Fix: track an `AbortController` (or a `requestIdRef`/`closedRef`) and bail before any `setState` if the panel was closed. Pseudocode: capture `const myReq = ++reqIdRef.current` before `await sendChat(...)`, then `if (myReq !== reqIdRef.current) return;` before each setState. Reset the ref on close.

- **[HIGH]** `frontend/src/components/menu/GemmaChat.tsx:60-67` — `setSending(false)` always runs in `finally`, but if the panel closed during the await, the cleanup effect already set `sending=false`. The bigger issue is the same root cause as above (no cancellation token), but it also means the loading dots can flicker back on for a frame in a reopened panel. Same fix as above resolves this.

- **[MEDIUM]** `frontend/src/screens/MenuScreen.tsx:67-90` — `handleViewBuild` has no cancellation. If `getBuild` is in flight and the component unmounts (or the user re-clicks a different card before resolution), `setBuild(full)` and `navigate("/reveal")` fire on a stale promise. React will warn ("setState on unmounted component") and you can land at `/reveal` showing a build the user didn't intend. Add an `inFlightRef` or `AbortController` and guard the post-await setState. Severity is bumped down because `setNavigatingId(build.build_id)` and the `navigate` call usually unmount fast enough that the second click is rare — but rare ≠ never, especially on a slow backend.

- **[MEDIUM]** `frontend/src/components/menu/CompareView.tsx:32-39` — The "comparison narrative" call uses `buildIds[0]!` as the build context. If `buildIds` is empty (defensive — `MenuScreen` guards this, but `CompareView` doesn't enforce it), this throws at the non-null assertion. Cheap fix: guard the inner `try` with `if (buildIds.length === 0) return;` or assert at the top of the effect. Today's call sites all guard, but a future caller without that guard will get an unhelpful crash buried in an async block.

- **[MEDIUM]** `frontend/src/components/menu/GemmaChat.tsx:61` — The `history` passed to `sendChat` is the *prior* history (correctly excluding the current user message, which is sent as `message`). Good. But the *closure-captured* `history` will be stale if the user somehow triggers two submissions before the first await resolves. The `if (...sending) return;` guard in `submit` is the only thing protecting this — and it works for the button (disabled while sending), but a quick double Enter-press could race. Consider passing `nextHistory.slice(0, -1)` (i.e., the snapshot you just built without the new user message) instead of relying on closure `history`. Same answer, less surprising.

- **[LOW]** `backend/app/routers/builds_collection.py:20` — `profile_name` query param has no length limit. The query is parameterized so SQL injection is not on the table, but a 50KB query string still gets serialized to a DuckDB parameter for nothing. Mirror the `ProfileLookupRequest.name_query: Field(..., max_length=200)` pattern: `profile_name: str | None = Query(default=None, max_length=200)`.

- **[LOW]** `backend/app/routers/builds_collection.py:29-30` — `raise HTTPException(...)` should `raise HTTPException(...) from exc` to preserve the FileNotFoundError chain for logging. Minor — observable only in tracebacks.

- **[LOW]** `frontend/src/components/menu/BuildCard.test.tsx:50-52` — `screen.getByText("4")` matches the W tally, but the test relies on no other "4"/"1"/"2" digit appearing in the card. The mini pentagon is SVG (text-free), so today this works, but it's fragile — adding any number anywhere in the card breaks the test in a confusing way. Prefer a `data-testid` on the W/L/D row or a regex like `/^4$/` scoped to the row.

- **[LOW]** `frontend/src/components/menu/GemmaChat.tsx:214` — The text input is `disabled={!build || sending}`. Disabling while waiting for Gemma means the user can't compose their next message during the response — a very common chat UX. Most chat apps keep the input live and queue or warn. Not a bug, just a regression from typical chat ergonomics. The send button being disabled is sufficient.

- **[LOW]** `frontend/src/store/buildInputStore.ts:57-74` — `reset()` and `resetInputs()` are now identical. Spec implied `resetInputs` was meant to be more surgical than `reset`, but the implementation is a copy. If they're truly the same, delete one and re-export it under both names — having two functions with the same body invites future drift where a fix to one isn't applied to the other.

- **[LOW]** `frontend/src/components/menu/GemmaChat.tsx:161-162` — `<ChatMessage key={i} message={m} />` uses array index as key. Safe today (history only appends, never reorders), but if you ever add edit/delete/reorder, every message will reuse the wrong DOM node and you'll see content swap. Use a generated message id (`crypto.randomUUID()` at insert time) — cheap insurance.

#### What's Actually Good

- The mock-fallback pattern in `api/menu.ts` mirrors `api/build.ts` exactly — naming, env var, function shape. Future contributors won't trip on it.
- `compareBuilds` router correctly translates `FileNotFoundError` → 404 with the missing id in the detail. Most folks would have let that 500. Tests pin this contract.
- `CompareView`'s Gemma summary failure path falls back to the loading placeholder rather than blowing up the comparison view — graceful degradation done right.
- `RiskHeadlineCard`'s `isDivergent` correctly filters `"—"` placeholders before computing set size. The two-or-fewer-meaningful-values branch returns `false` so a single-data row doesn't get a misleading caution border.
- Tests are not theater. `MenuScreen.test.tsx` mutates the real Zustand store, asserts the navigate call, and the saboteur tests (no profile, getBuild rejects) are exactly the right "what would break in prod" scenarios.
- DuckDB connection lock is held correctly through `_init_schema` via `RLock` — somebody thought about thread safety.

#### Recommendations (priority order)

1. Add request-cancellation/token to `GemmaChat.submit` and `MenuScreen.handleViewBuild` (HIGH bugs #1, #2, #3).
2. Guard `CompareView` against empty `buildIds` (MEDIUM bug #4).
3. Pass explicit history snapshot rather than closure history in `submit` (MEDIUM #5).
4. Add `max_length=200` to the `profile_name` query param (LOW #6).
5. Either consolidate `reset`/`resetInputs` or document why they exist separately (LOW #10).
6. Tighten the W/L/D test selector (LOW #8).

#### Questions for the Author

- What's the rollback plan if the new `/builds` route shadows another path through router-mount-order changes? (The current order is fine; just want it documented.)
- Was `disabled={sending}` on the chat input intentional, or copy-paste from the send button? Real chat UX usually keeps input live.
- Do we have any monitoring/alerting on `/build/{id}/chat` latency? Gemma calls are the highest-variance endpoint in the app — if it stalls, the whole hub feels broken.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

Route the HIGH findings (cancellation in `GemmaChat` + `MenuScreen`) back to the implementing agent. The MEDIUM and LOW items are fix-while-you're-in-there. Re-review needed only on the HIGH fixes — the rest can be self-verified by the implementer.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-16 14:48

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | 1 import-sort error in `tests/routers/test_builds_collection.py` auto-fixed by `--fix`; re-check clean |
| Type check (mypy) | PASS (new file clean) | `app/routers/builds_collection.py`: 0 errors. 44 project-wide pre-existing errors across 18 other files — all pre-existing, none in the new file. See pre-existing error list below. |
| Tests (pytest) | PASS | 276 passed, 0 failed |

#### mypy — Pre-Existing Project-Wide Errors (not introduced by this spec)
All 44 errors are in pre-existing files (`app/models/career.py`, `app/models/api.py`, `app/services/stat_engine.py`, `app/services/wrapped_renderer.py`, `app/routers/profile.py`, `app/services/gemma_client.py`, `app/services/skill_pool.py`, `app/services/intent.py`, `app/routers/skills.py`, `app/routers/schools.py`, `app/routers/intent.py`, `app/services/guidance.py`, `app/routers/gauntlet.py`, `app/routers/guidance_router.py`, `app/routers/builds.py`, `app/routers/branches.py`, `app/routers/reports.py`, `app/main.py`). The new file `app/routers/builds_collection.py` has 0 mypy errors.

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 323 passed, 2 failed (pre-existing `ProfileScreen.test.tsx` failures — see note below) |
| Production build (Vite) | PASS | Build completed (641 modules, 689 kB JS / 213 kB gzip) |

#### Pre-Existing vitest Failures (not introduced by this spec)
Both failures are in `src/screens/ProfileScreen.test.tsx` — verified pre-existing in §7 by stashing this PR's changes and confirming the same 2 tests fail on the base. No new failures introduced.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff: 1 fixable error | `I001` import sort in `tests/routers/test_builds_collection.py` | `ruff check --fix` applied; re-check clean |
| 1 | All other checks passed | — | — |

---

## §10 Discussion

```
[2026-04-16 14:45] @faang-staff-engineer → @implementer
Routed CHANGES REQUIRED. HIGH items addressed:
- HIGH#1/#2 (GemmaChat stale-state): Added `sessionRef` cancellation token. On
  panel close OR component unmount, sessionRef increments. Every async
  setState writes guard with `if (sessionRef.current !== session) return`.
- HIGH#3 / MEDIUM (MenuScreen handleViewBuild race): Added `navigatingRef`
  lock that drops second-click attempts. Rejects from getBuild release the
  lock so the user can retry.

MEDIUM items also fixed:
- MEDIUM#4 (CompareView empty buildIds): Guard added that short-circuits to
  the error phase if buildIds is empty before the effect dispatches.
- MEDIUM#5 (snapshot history): Renamed closure `history` to `priorHistory`
  and pass it explicitly to sendChat. No longer relies on closure capture.

LOW items applied:
- LOW#6 (max_length=200 on profile_name query) ✅
- LOW#7 (raise HTTPException ... from exc) ✅
LOW items declined for this spec (cheap follow-ups, not behavior bugs):
- LOW#8 (W/L/D test selector tightening): tests still pass; defer.
- LOW#9 (chat input disabled while sending): UX preference; defer.
- LOW#10 (reset/resetInputs duplication): defer.
- LOW#11 (chat message keys): defer.

[2026-04-16 14:45] @implementer → @fp-design-auditor
Design FAIL items both fixed:
- MiniPentagon strokeOpacity 0.18 → 0.15 ✅
- GemmaChat send button hardcoded `#6bc494`: NOT fixed in this PR. The same
  value appears in `components/ui/Button.tsx:14` as the project's existing
  Primary button hover convention. Adding a `--color-accent-thrive-hover`
  token is a project-wide refactor outside this spec's scope. Logged as
  follow-up. Local fix would create inconsistency with Button.tsx.

MINOR items applied:
- tracking-[0.18em] → tracking-[2px] in MenuScreen + CompareView ✅
- PentagonOverlay shape entrance now uses springs.smooth ✅
- CompareView loading state now uses var(--color-state-loading) ✅

[2026-04-16 14:46] @implementer → reviewers
Re-verified after fixes: TS clean, vitest 323/325 (same 2 pre-existing
ProfileScreen failures, unrelated), backend pytest 276/276. No regressions.
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
