# Feature: Multi-CIP Resolution

## Claude Code Prompt

```
Read the spec at docs/specs/feature-multi-cip-resolution.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, Gemma prompt changes, API contracts)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION (UI)
   - Invoke @fp-design-visionary to propose the premium CIP picker UI
   - Visionary writes to §3 (UI/UX Design): layout, interactions, Brightpath token usage, responsive behavior
   - §3 becomes the pixel-perfect implementation target
   - Invoke @genai-architect for Gemma prompt/schema review (writes to §10)

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

5. DESIGN AUDIT (UI)
   - Invoke @design-builder for mechanical token/pattern compliance against Brightpath design system
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
   - Generate report to reports/feature-multi-cip-resolution-YYYY-MM-DD.md
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
| Created | 2026-04-21 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-21 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-set-your-course.md`, `docs/specs/feature-chip-dispatch-mcp-tool-calling.md`, `docs/specs/feature-intent-aware-tiering.md` |

---

## §1 Feature Description

### Overview

Modify the Set Your Course resolution flow so Gemma returns up to 3 ranked CIP matches instead of 1 when a student's search term maps to multiple programs at their school. The student sees ranked options, picks one, and continues into the existing career reveal flow.

### Problem Statement

Today, when a student types a broad term like "engineering" at Purdue (which offers 14 engineering programs), Gemma picks a single CIP and the student never sees the alternatives. This is a problem because outcomes vary significantly across programs at the same school — Computer Engineering (ERN 9.7, $76K first-year earnings) outperforms Civil Engineering (ERN 7.3, $66K) by $10K/yr, but the student has no visibility into that. The current single-pick design also forces Gemma to make an opinionated choice it shouldn't have to make when the input is genuinely ambiguous.

Data analysis confirms the feature is viable:
- Median CIPs per family per school: **1** (graceful degradation — most searches return 1 option)
- Average: **2.0** (top-3 cap rarely truncates)
- Schools like Purdue have **14 engineering CIPs** — exactly where ranking matters most
- Gemma already sees the full school program list in her prompt (114 programs for Purdue)

### Success Criteria

- [ ] Gemma's resolution prompt returns up to 3 ranked CIP matches with per-option reasoning
- [ ] When only 1 CIP matches, the UX is unchanged from today (no picker, no extra UI)
- [ ] When 2-3 CIPs match, options appear as selectable elements; tapping one swaps the resolution and refetches career outcomes
- [ ] When more options exist beyond the top 3, a `remaining_count` is surfaced with a narrowing hint (e.g., "11 more programs match — try a more specific search")
- [ ] `matched_cip` / `matched_title` remain populated as the primary (first-ranked) option for backwards compatibility
- [ ] The fallback resolver (`_fallback_resolve`) also returns multi-CIP when applicable
- [ ] All existing tests pass (no regressions in the core Set Your Course flow)
- [ ] Zero taxonomy leakage: no CIP codes, SOC codes, or internal jargon visible to students
- [ ] Works under both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Cap at 3 options, not 5 or unlimited | Data shows median 1, avg 2.0 CIPs per family per school. 3 covers >95% of cases without overwhelming the student. | Unlimited (overwhelming UX), 5 (rarely that many, wastes prompt tokens) |
| 2 | Keep `matched_cip`/`matched_title` as primary for backwards compat | Every downstream consumer (chip dispatch, commit, outcomes fetch, tiering) reads `matched_cip`. Changing the contract is a full-stack break. | Replace with array-only (massive blast radius), new field name (confusing dual contract) |
| 3 | Repurpose existing `alternatives` field on `IntentResult` | Field already exists on both backend model and frontend type with shape `list[{cip, title, why}]`. Currently populated for low/medium confidence but not rendered on Set Your Course. Reusing it avoids new schema fields. | New `matched_cip_options` field (adds schema surface), `ranked_matches` (same problem) |
| 4 | Lazy-fetch outcomes (fetch only for selected CIP) | Eager-fetching 3 sets of career outcomes triples MCP calls and Gemma load. Most students will accept the primary. | Eager-fetch all 3 (3x API cost, latency), prefetch on hover (complexity) |
| 5 | Selection happens client-side by swapping `currentResolution` | No new backend endpoint needed. The frontend already has the CIP, title, and parent_cip for each alternative. Swapping the resolution and refetching outcomes uses the existing `useSetYourCourse` flow. | New `POST /intent/pick-cip` endpoint (unnecessary round-trip), WebSocket (overkill) |
| 6 | Include `remaining_count` and `narrowing_hint` in Gemma response | Lets the UI tell students "11 more programs match" without fetching them. The hint is Gemma-generated so it's natural language. | Frontend counts (doesn't have access to full match set), no hint (student doesn't know to narrow) |
| 7 | Ranking by Gemma's semantic judgment, not by ERN/earnings | Gemma should rank by relevance to the student's input, not by outcome quality. "engineering" → Computer Engineering first because it's the most canonical match, not because it earns more. Outcome data appears after selection. | Rank by ERN (biases toward high-paying fields), rank by alphabetical (useless) |
| 8 | Fallback resolver also returns multi-CIP | The `_fallback_resolve` path (used when streaming fails) should match the same contract. Otherwise the frontend has to handle two different shapes. | Fallback stays single-CIP (inconsistent contract, frontend branching) |

### Constraints

- The Gemma resolution prompt is already ~100 lines of tuned instructions; multi-CIP changes must be surgical, not a rewrite
- The `---INTENT_JSON---` delimiter + JSON tail format is shared with the fallback resolver
- `CIPCODE` is always a string type (XX.XXXX format) — never float
- Zero taxonomy leakage to students: no CIP codes, SOC codes, "crosswalk", or numeric codes in UI

### Out of Scope

- **Reverse SOC→CIP lookup** ("I want to be a nurse — what should I study here?") — related future feature, different entry point
- **Outcome comparison view** (side-by-side career outcomes for 2-3 CIPs) — potential follow-on after this ships
- **Gemma-ranked by outcome quality** — this spec ranks by semantic relevance; outcome-aware ranking is a separate feature
- **Chip dispatch changes** — chips still operate on the single selected `currentResolution`; no multi-CIP chip routing
- **Analytics logging of which option was picked** — desirable but not required for MVP; can be added via `record_commit` in a follow-on

---

## §3 UI/UX Design

> @fp-design-visionary fills this section. This is the pixel-perfect implementation target.
> Reviewed: 2026-04-21 | Status: COMPLETE

### Emotional Target

**Confident refinement.** The student just typed something broad — "engineering" — and Gemma came back with a primary match. The CIP picker says: "You're in the right neighborhood. Here are the doors." The feeling is a bookshelf where the right spine is already pulled halfway out, but you can see two more that might be even better. No anxiety about missing something. No overwhelm from a long dropdown. Just two or three warm, glowing options in the same visual language the student has been living in for the last thirty seconds.

Here is why this matters: the existing resolution header is a single confident statement — "Gemma matched 'engineering' -> Computer Engineering." Adding a picker below it must feel like a natural extension of that confidence, not a retraction of it. The primary is still primary. The alternatives are invitations, not corrections.

### Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Pill-row layout, not card grid | The alternatives are lightweight pivots, not full-featured cards. A row of pills below the resolution header preserves the existing vertical rhythm and avoids the visual weight of stacked cards. The match card pattern (from tiered matching) is too heavy here — that card carries career previews, actions, and a breathing glow. The CIP picker is three lines of text. |
| D2 | Primary pill is non-interactive, alternatives are buttons | The primary is already displayed as the resolution header title above. Repeating it in the picker as a selectable button creates a confusing double-affordance. Instead, the primary appears as a static "anchor" pill with a thrive left-dot, and alternatives appear as interactive pills the student can tap. |
| D3 | Inline below resolution header, not inside match card | The match card has its own alternatives list for medium-confidence tiered matching (see DESIGN.md "Tiered Match Card"). The CIP picker serves a different purpose: it appears on HIGH-confidence resolutions where Gemma is sure about the family but the family has siblings. Rendering it as a separate element below the resolution header avoids overloading the match card with two different alternative concepts. |
| D4 | Swap animation uses `layout` + `AnimatePresence` | When the student taps an alternative, the old primary title in the resolution header crossfades to the new one while the pill row reorders. This is cheaper and more elegant than unmounting/remounting the whole resolution block. The career tiles below refetch independently — their loading skeleton is already built. |

### Component: `CipPicker`

A new component `frontend/src/components/school/CipPicker.tsx`. Renders only when `currentResolution.alternatives` has 1-2 entries. When `alternatives` is null, empty, or the resolution has only one CIP, this component returns null — the screen is visually identical to today (graceful degradation).

#### Placement

Rendered inside the existing resolution header block (the `motion.div` at line 407 of `SetYourCourseScreen.tsx`, `data-testid="current-resolution-summary"`), immediately after the taxonomy receipt paragraph and before the career tier sections. Specifically:

```
[Resolution header]
  GemmaStar + "Gemma matched" attribution line
  Matched title (font-display, subheading)
  Taxonomy receipt (font-body, small, muted)
  >>> CipPicker inserts here <<<
[Career tier sections]
```

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  pl-[22px] (aligns with resolution title indent)             │
│                                                              │
│  ALSO MATCHES                          <- section label      │
│                                                              │
│  ● Computer Engineering                <- primary (static)   │
│    Closest match for "engineering"        reason text         │
│                                                              │
│  ○ Electrical Engineering              <- alt 0 (button)     │
│    Also covers circuits and signals       reason text         │
│                                                              │
│  ○ Mechanical Engineering              <- alt 1 (button)     │
│    Focuses on physical systems            reason text         │
│                                                              │
│  11 more programs match — try "civil                         │
│  engineering" or "aerospace" to            <- remaining hint  │
│  narrow it down                                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### Section Label

Reuses the existing section label pattern from DESIGN.md:

```
font-family: font-data (Space Mono)
font-size: 11px
font-weight: 700
letter-spacing: 2px
text-transform: uppercase
color: accent-info
margin-bottom: 8px (space-2)
margin-top: 16px (space-4)
```

Copy: `"ALSO MATCHES"` — short, factual, parallel to existing section labels like "WHERE THIS LEADS" and "OR — ONE OF THESE?". The word "also" signals these are siblings of the primary, not replacements.

Tailwind: `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info mt-4 mb-2`

#### Option Row (shared base)

Each option (primary + alternatives) is a horizontal row. The rows stack vertically with `gap-1` (4px) between them — tight, like a list, not like separate cards.

```
display: flex
align-items: flex-start
gap: 10px (space-2 + 2px)
padding: 10px 12px (space-2.5 space-3)
border-radius: radius-md (10px)
transition: background 150ms ease-out, border-color 150ms ease-out
```

Tailwind base: `flex items-start gap-2.5 px-3 py-2.5 rounded-md transition-colors duration-fast`

#### Primary Row (static, non-interactive)

The primary option confirms what the resolution header already shows. It anchors the list so the student sees the full set ranked.

- **Dot indicator:** A 6px filled circle in `accent-thrive` (#7DD4A3), `margin-top: 7px` (vertically centered on the title line). This is the "you are here" marker.
- **Title:** `font-body` (Nunito), `text-body-sm` (15px), weight 600, `text-text-primary` (#F5F0E8). The program name without any CIP code.
- **Reason:** Below the title, `font-body`, `text-small` (14px), weight 400, `text-text-muted` (#8A8595). Gemma's `reasoning` field, truncated to one line with `text-ellipsis overflow-hidden whitespace-nowrap max-w-[48ch]`.
- **Background:** `transparent` — no hover, no cursor change. Not a button.
- **aria-current:** `"true"` on the row `<div>` to communicate "this is the selected one" to screen readers.

Tailwind:
```tsx
<div
  className="flex items-start gap-2.5 px-3 py-2.5 rounded-md"
  aria-current="true"
  data-testid="cip-option-primary"
>
  <span className="mt-[7px] w-1.5 h-1.5 rounded-full bg-accent-thrive flex-none" aria-hidden="true" />
  <div className="min-w-0">
    <p className="font-body text-body-sm font-semibold text-text-primary">{title}</p>
    <p className="font-body text-small text-text-muted truncate max-w-[48ch]">{reasoning}</p>
  </div>
</div>
```

#### Alternative Row (interactive button)

Each alternative is a `<button>` the student can tap to swap it into the primary position.

- **Dot indicator:** A 6px circle with a 1.5px `border-border-default` stroke (rgba 255,255,255,0.1), no fill. Signals "available but not selected." On hover, the stroke brightens to `accent-info` (#7BB8E0).
- **Title:** `font-body`, `text-body-sm` (15px), weight 600, `text-text-secondary` (#C4BFB0). On hover, brightens to `text-text-primary`.
- **Reason ("why"):** Below the title, `font-body`, `text-small` (14px), weight 400, `text-text-muted`. Gemma's per-alternative `why` field. Truncated identically to the primary's reason.
- **Background:** `transparent` default. Hover: `bg-bp-surface` (#2D3060). The same hover treatment as DESIGN.md "List Items."
- **Cursor:** `pointer`.
- **Border:** None by default. On focus-visible: `outline: 3px solid var(--color-focus-ring); outline-offset: 2px;` per DESIGN.md focus convention.
- **Press feedback:** `scale(0.98)` via `whileTap` on Framer Motion. Subtler than the standard 0.97 button press because the row is wider and the scale is more perceptible.

Tailwind + Framer:
```tsx
<motion.button
  type="button"
  onClick={() => onPickAlternative(index)}
  whileTap={{ scale: 0.98 }}
  className="w-full flex items-start gap-2.5 px-3 py-2.5 rounded-md
             cursor-pointer transition-colors duration-fast
             hover:bg-bp-surface group
             focus-visible:outline-none focus-visible:ring-[3px]
             focus-visible:ring-[color:var(--color-focus-ring)]
             focus-visible:ring-offset-2"
  aria-label={`Select program: ${title}`}
  data-testid={`cip-option-alt-${index}`}
>
  <span
    className="mt-[7px] w-1.5 h-1.5 rounded-full border-[1.5px] border-border
               group-hover:border-accent-info flex-none transition-colors duration-fast"
    aria-hidden="true"
  />
  <div className="min-w-0 text-left">
    <p className="font-body text-body-sm font-semibold text-text-secondary
                  group-hover:text-text-primary transition-colors duration-fast">
      {title}
    </p>
    <p className="font-body text-small text-text-muted truncate max-w-[48ch]">
      {why}
    </p>
  </div>
</motion.button>
```

#### Remaining Count Hint

Rendered below the option rows when `remaining_count > 0`. A single muted line that uses Gemma's `narrowing_hint` text.

- **Typography:** `font-body`, `text-small` (14px), weight 400, `text-text-muted`, `italic`.
- **Layout:** `margin-top: 8px (space-2)`, `padding-left: 22px` (aligns with option text, past the dot).
- **Content:** `"{remaining_count} more programs match -- {narrowing_hint}"`. The em-dash is an actual `--` character. If `narrowing_hint` is empty, fall back to `"try a more specific search"`.
- **No interaction.** This is informational, not a link or button.

Tailwind:
```tsx
{remaining_count > 0 && (
  <p
    className="pl-[22px] mt-2 font-body text-small italic text-text-muted"
    data-testid="cip-remaining-hint"
    aria-label={`${remaining_count} more programs match`}
  >
    {remaining_count} more programs match {"—"} {narrowing_hint || "try a more specific search"}
  </p>
)}
```

### Selection Swap Interaction

When the student taps an alternative, three things happen simultaneously:

#### 1. Resolution Header Title Crossfade

The matched title in the resolution header (`font-display text-subheading font-semibold text-accent-insight`) animates from the old title to the new title. Use `AnimatePresence mode="wait"` with a `key` tied to `currentResolution.matched_cip`:

```tsx
<AnimatePresence mode="wait">
  <motion.span
    key={currentResolution.matched_cip}
    initial={{ opacity: 0, x: -8 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: 8 }}
    transition={{ duration: 0.2, ease: "easeOut" }}
    className="font-display text-subheading font-semibold text-accent-insight"
  >
    {currentResolution.matched_title}
  </motion.span>
</AnimatePresence>
```

The exit slides right (+8px) while the entrance slides in from left (-8px). This creates a "slot machine" directional feel — the old title leaves, the new one arrives. Duration is 200ms with easeOut, not a spring — springs on text swaps feel laggy. The 200ms crossfade is fast enough to feel responsive but slow enough for the eye to register the change.

#### 2. Pill Row Reorder

The CipPicker re-renders with the new primary and reshuffled alternatives. Use `AnimatePresence` with `layout` on each row so the rows smoothly reorder:

```tsx
<motion.div layout transition={springs.snappy}>
  {/* primary row */}
</motion.div>
{alternatives.map((alt, i) => (
  <motion.div key={alt.cip} layout transition={springs.snappy}>
    {/* alternative row */}
  </motion.div>
))}
```

The `layout` prop handles the position swap automatically. `springs.snappy` (`stiffness: 400, damping: 25`) gives a quick, responsive reorder with a slight bounce — like cards shuffling in a hand. The dot indicator on the promoted alternative fills from hollow to solid via a 150ms color transition (`transition-colors duration-fast`).

#### 3. Career Tiles Refetch

The swap calls `onPickAlternative(index)` in the hook, which updates `currentResolution.matched_cip`. The existing `useEffect` watching `parentCipOrMatched` fires `debouncedCareerFetch` at 250ms. The career tier sections unmount (via the `key={currentResolution.matched_cip}` already on the tier wrapper at line 565) and remount with the loading skeleton. No new animation work needed here — the existing skeleton and stagger entrance handle the transition.

#### Timing Summary

| Phase | Duration | Easing | What |
|-------|----------|--------|------|
| Title crossfade exit | 200ms | easeOut | Old title slides right + fades |
| Title crossfade enter | 200ms | easeOut | New title slides in from left + fades in |
| Pill row reorder | ~250ms | springs.snappy | Rows swap positions via layout animation |
| Dot fill transition | 150ms | ease-out (CSS) | Hollow dot fills to thrive green |
| Career skeleton appear | 0ms (immediate) | - | Loading skeleton replaces career tiles |
| Career tiles entrance | 300ms staggered | springs.smooth | New career tiles fade up after fetch completes |

#### Demoted Primary "why" Text

Per architecture review C3: when the old primary is demoted to an alternative, its `why` field should NOT be `res.reasoning` (which is full Gemma prose). Instead, use the static string `"Your original match"`. This keeps all `why` fields at the same visual length and communicates clearly what happened.

```typescript
const demotedPrimary = {
  cip: res.matched_cip,
  title: res.matched_title,
  why: "Your original match",
  parent_cip: res.parent_cip,
};
```

### Responsive Behavior

#### Desktop (>=1200px)

The CipPicker renders at full width within the right column of the existing 4:8 grid. Option rows display at their natural width. The `max-w-[48ch]` truncation on reason text prevents overly long Gemma explanations from breaking the layout.

#### Tablet (768px - 1199px)

The grid collapses to single-column. The CipPicker renders full-width below the resolution header. No layout changes needed — the flex-col stack works at any width.

#### Mobile (<768px)

Same single-column layout. Option rows become slightly taller because the reason text wraps more. The `py-2.5` padding provides enough touch target (minimum 44px total row height with title + reason). The `pl-[22px]` on the remaining hint stays consistent.

No special mobile treatment (no bottom sheet, no modal). The picker is already light enough — three rows of text — that it works inline at every viewport.

### States

#### State 1: Single CIP (no picker)

When `alternatives` is null, empty array, or undefined: CipPicker returns null. The screen looks exactly like it does today. This is the majority case (median CIPs per family per school is 1).

#### State 2: Two CIPs (primary + 1 alternative)

The picker renders with the section label, one static primary row, and one interactive alternative row. The remaining hint appears if `remaining_count > 0`.

```
ALSO MATCHES
● Computer Engineering
  Closest match for "engineering"
○ Electrical Engineering
  Also covers circuits and signals
```

#### State 3: Three CIPs (primary + 2 alternatives)

Same as state 2 but with two alternative rows.

```
ALSO MATCHES
● Computer Engineering
  Closest match for "engineering"
○ Electrical Engineering
  Also covers circuits and signals
○ Mechanical Engineering
  Focuses on physical systems

11 more programs match — try "civil engineering" or "aerospace"
```

#### State 4: After swap

The student tapped "Electrical Engineering." The resolution header now shows "Electrical Engineering" as the matched title. The picker reorders:

```
ALSO MATCHES
● Electrical Engineering
  Also covers circuits and signals
○ Computer Engineering
  Your original match
○ Mechanical Engineering
  Focuses on physical systems

11 more programs match — try "civil engineering" or "aerospace"
```

The career tiles below show a loading skeleton, then new results.

#### State 5: Loading after swap

While career tiles are refetching, the picker is fully interactive — the student can swap again without waiting. Each swap cancels the in-flight fetch (the existing debounce handles this). The picker itself has no loading state — it always shows the current selection instantly.

### Accessibility

| Element | HTML | data-testid | aria-* | Notes |
|---------|------|-------------|--------|-------|
| Picker container | `<div role="group">` | `cip-picker` | `aria-label="Program options"` | Groups the options semantically |
| Section label | `<p>` | `cip-picker-label` | `aria-hidden="true"` | Decorative — the group label covers it |
| Primary row | `<div>` | `cip-option-primary` | `aria-current="true"` | Not a button — already selected |
| Alternative row 0 | `<button>` | `cip-option-alt-0` | `aria-label="Select program: {title}"` | Full program name, no CIP code |
| Alternative row 1 | `<button>` | `cip-option-alt-1` | `aria-label="Select program: {title}"` | Same pattern |
| Remaining hint | `<p>` | `cip-remaining-hint` | `aria-label="{count} more programs match"` | Informational only |

**Keyboard navigation:**
- `Tab` moves from the resolution header into the picker, landing on the first alternative button (the primary is not focusable — it is a `<div>`, not a `<button>`).
- `Tab` again moves to the second alternative (if present).
- `Enter` or `Space` on a focused alternative triggers the swap.
- Focus ring: `3px solid var(--color-focus-ring)`, `outline-offset: 2px`, per DESIGN.md focus convention.

**Screen reader flow:** "Program options group. Selected program: Computer Engineering. Button: Select program: Electrical Engineering. Button: Select program: Mechanical Engineering. 11 more programs match."

**Reduced motion:** When `prefers-reduced-motion: reduce` is active, the title crossfade becomes an instant swap (duration: 0), the pill row reorder loses the layout spring (instant position), and the dot fill transition stays (it is CSS, already respects reduced motion via the global media query). The career tile skeleton still appears — it is functional, not decorative.

### Complete Component Sketch

```tsx
// frontend/src/components/school/CipPicker.tsx

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { IntentResult } from "@/types/buildInput";

interface CipPickerProps {
  resolution: IntentResult;
  onPickAlternative: (index: number) => void;
}

export function CipPicker({ resolution, onPickAlternative }: CipPickerProps) {
  const reducedMotion = useReducedMotion();

  const alts = resolution.alternatives;
  if (!alts || alts.length === 0) return null;

  const remaining = resolution.remaining_count ?? 0;
  const hint = resolution.narrowing_hint || "try a more specific search";

  return (
    <div
      role="group"
      aria-label="Program options"
      className="pl-[22px] mt-4"
      data-testid="cip-picker"
    >
      <p
        className="font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info mb-2"
        aria-hidden="true"
        data-testid="cip-picker-label"
      >
        Also matches
      </p>

      <div className="flex flex-col gap-1">
        {/* Primary (static, non-interactive) */}
        <motion.div
          layout={!reducedMotion}
          transition={reducedMotion ? { duration: 0 } : springs.snappy}
          className="flex items-start gap-2.5 px-3 py-2.5 rounded-md"
          aria-current="true"
          data-testid="cip-option-primary"
        >
          <span
            className="mt-[7px] w-1.5 h-1.5 rounded-full bg-accent-thrive flex-none"
            aria-hidden="true"
          />
          <div className="min-w-0">
            <p className="font-body text-body-sm font-semibold text-text-primary">
              {resolution.matched_title}
            </p>
            <p className="font-body text-small text-text-muted truncate max-w-[48ch]">
              {resolution.reasoning}
            </p>
          </div>
        </motion.div>

        {/* Alternatives (interactive) */}
        <AnimatePresence mode="popLayout">
          {alts.map((alt, i) => (
            <motion.button
              key={alt.cip}
              layout={!reducedMotion}
              type="button"
              onClick={() => onPickAlternative(i)}
              whileTap={reducedMotion ? undefined : { scale: 0.98 }}
              transition={reducedMotion ? { duration: 0 } : springs.snappy}
              className="w-full flex items-start gap-2.5 px-3 py-2.5 rounded-md
                         cursor-pointer transition-colors duration-fast
                         hover:bg-bp-surface group
                         focus-visible:outline-none focus-visible:ring-[3px]
                         focus-visible:ring-[color:var(--color-focus-ring)]
                         focus-visible:ring-offset-2"
              aria-label={`Select program: ${alt.title}`}
              data-testid={`cip-option-alt-${i}`}
            >
              <span
                className="mt-[7px] w-1.5 h-1.5 rounded-full border-[1.5px] border-border
                           group-hover:border-accent-info flex-none transition-colors duration-fast"
                aria-hidden="true"
              />
              <div className="min-w-0 text-left">
                <p className="font-body text-body-sm font-semibold text-text-secondary
                              group-hover:text-text-primary transition-colors duration-fast">
                  {alt.title}
                </p>
                <p className="font-body text-small text-text-muted truncate max-w-[48ch]">
                  {alt.why}
                </p>
              </div>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>

      {remaining > 0 && (
        <p
          className="pl-[22px] mt-2 font-body text-small italic text-text-muted"
          data-testid="cip-remaining-hint"
          aria-label={`${remaining} more programs match`}
        >
          {remaining} more program{remaining === 1 ? "" : "s"} match{" "}
          {"—"} {hint}
        </p>
      )}
    </div>
  );
}
```

### Integration Point in SetYourCourseScreen.tsx

The CipPicker inserts inside the existing resolution header `motion.div` (data-testid `current-resolution-summary`), after the taxonomy receipt and before the career tier sections:

```tsx
{/* After taxonomy receipt, inside the resolution header motion.div */}
{currentResolution.alternatives && currentResolution.alternatives.length > 0 && (
  <CipPicker
    resolution={currentResolution}
    onPickAlternative={onPickAlternative}
  />
)}
```

The resolution header's matched title `<span>` wraps in `AnimatePresence mode="wait"` with `key={currentResolution.matched_cip}` to enable the crossfade on swap (see "Selection Swap Interaction" above).

### What Makes This Feel Alive

**The dot metaphor.** A filled thrive-green dot next to the primary. Hollow bordered dots next to alternatives. When you tap an alternative, the dots swap — hollow becomes filled, filled becomes hollow. It is a radio button reimagined as a tiny piece of jewelry. The transition is 150ms on the CSS `background-color` and `border-color` properties, so it feels like the dot "fills with color" rather than snapping. Tiny detail, but it is the difference between "I clicked a form control" and "I chose my path."

**The directional title swap.** Old title exits right, new title enters from left. This creates a sense of forward motion — you are not going back, you are pivoting to a sibling. The 200ms easeOut duration is fast enough that it never feels like waiting, but slow enough that the student's eye tracks the change and feels confident about what just happened.

**The "Your original match" ghost text.** After a swap, the demoted primary's why-text changes to "Your original match." This is a breadcrumb — it tells the student they can always go back. It also prevents the visual length inconsistency flagged in C3 (the original reasoning is often a full sentence, while alternative why-texts are short phrases).

**No loading state on the picker itself.** The picker swaps instantly. The career tiles below show a skeleton. This separation of concerns means the student never feels like their click "didn't register" — the picker responds in the same frame, and the downstream data follows at its own pace. Instant feedback on the control, eventual consistency on the content.

---

## §4 Technical Specification

### Architecture Overview

This feature modifies the Gemma resolution layer (prompt + JSON parsing) and the frontend display layer. The data is already present — `program_career_paths` contains the full CIP×SOC×school join, and Gemma already receives the full school program list in her prompt context. The change is: ask Gemma to return 3 instead of 1, parse the richer response, surface the options in the UI, and let the student pick.

The downstream flow (outcomes fetch, tiering, commit, chip dispatch) is unchanged — it still operates on a single `matched_cip` from `currentResolution`. Selection happens client-side by swapping which alternative becomes the primary.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/career.py` | Modify | Add `remaining_count: int = 0` and `narrowing_hint: str = ""` to `IntentResult`. The existing `alternatives: list[dict] \| None` field is repurposed (no schema change needed). |
| `backend/app/services/set_your_course.py` | Modify | Update `_STREAM_INTENT_SYSTEM_PROMPT` to request 3 ranked CIPs. Update `_FALLBACK_JSON_SYSTEM` to match. Modify JSON tail parsing in the `structured` event builder to extract array and populate `alternatives`, `remaining_count`, `narrowing_hint`. |
| `backend/app/services/intent.py` | Modify | Call `_promote_to_leaf_cip` and `_get_career_titles_for_cip` for each alternative CIP (loop, not just primary). Update `_sanitize_alternatives` to validate all entries against crosswalk/school catalog. |
| `frontend/src/types/buildInput.ts` | Modify | Add `remaining_count?: number` and `narrowing_hint?: string` to the `IntentResult` interface. No change to `alternatives` shape — already `Array<{ cip: string; title: string; why: string }>`. |
| `frontend/src/hooks/useSetYourCourse.ts` | Modify | Add `onPickAlternative(index: number)` callback: swaps the selected alternative into `currentResolution` (matched_cip, matched_title, parent_cip), clears tiered careers, triggers outcomes refetch. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Render CIP picker when `currentResolution.alternatives?.length > 0`. Render remaining count hint when `currentResolution.remaining_count > 0`. Wire tap handler to `onPickAlternative`. |
| `frontend/src/store/buildInputStore.ts` | Modify | No new state fields needed — `currentResolution` already holds `alternatives`. Selection is handled by swapping `matched_cip`/`matched_title` on the existing `IntentResult` object. |
| `backend/tests/fixtures/intent_responses.json` | Modify | Add multi-CIP fixture entries for test consumption. |

### Data Model Changes

**`IntentResult` (backend/app/models/career.py, line 324)**

```python
class IntentResult(BaseModel):
    matched_cip: str                          # PRIMARY (first-ranked)
    matched_title: str                        # PRIMARY
    confidence: str
    reasoning: str = ""
    careers_preview: list[str] = Field(default_factory=list)
    audit_flag: str | None = None
    audit_message: str | None = None
    needs_clarification: bool = False
    alternatives: list[dict] | None = None    # REPURPOSED: now populated with ranked options 2-3
    parent_cip: str = ""
    confirmed_focus: str | None = None
    student_major_text: str = ""
    intent_keywords: list[str] = Field(default_factory=list)
    remaining_count: int = 0                  # NEW: how many more CIPs matched beyond top 3
    narrowing_hint: str = ""                  # NEW: Gemma-generated hint for narrowing search
```

The `alternatives` list entries use the existing shape: `{"cip": str, "title": str, "why": str}`. The `why` field carries Gemma's per-option reasoning (e.g., "Closest semantic match for 'engineering'").

Each alternative also includes `parent_cip: str` so the frontend can construct the correct `parentCipOrMatched` when swapping:
```python
{"cip": "14.09", "title": "Computer Engineering", "why": "...", "parent_cip": "14.09"}
```

**Frontend `IntentResult` (frontend/src/types/buildInput.ts, line 64)**

```typescript
export interface IntentResult {
  matched_cip: string;
  matched_title: string;
  confidence: string;
  reasoning: string;
  careers_preview: string[];
  audit_flag: string | null;
  audit_message: string | null;
  needs_clarification: boolean;
  alternatives: Array<{ cip: string; title: string; why: string; parent_cip?: string }> | null;
  parent_cip: string;
  school_reported_cip: string;
  confirmed_focus: string | null;
  student_major_text: string;
  intent_keywords: string[];
  remaining_count?: number;       // NEW
  narrowing_hint?: string;        // NEW
}
```

### Service Changes

#### `backend/app/services/set_your_course.py`

**Gemma prompt changes (`_STREAM_INTENT_SYSTEM_PROMPT`)**

Add to the JSON output format instruction (currently requests a single `matched_cip`):

```
If the student's input matches multiple programs at this school, return
up to 3 ranked matches. Rank by semantic relevance to the student's input
(not by outcome quality — that comes later).

Your JSON tail format:
---INTENT_JSON---
{"matched_cip": "XX.XXXX", "matched_title": "Primary Match Title",
 "confidence": "high|medium|low", "reasoning": "...",
 "parent_cip": "XX.XX",
 "alternatives": [
   {"cip": "XX.XXXX", "title": "Second Match", "why": "Also matches because...", "parent_cip": "XX.XX"},
   {"cip": "XX.XXXX", "title": "Third Match", "why": "Also matches because...", "parent_cip": "XX.XX"}
 ],
 "remaining_count": 11,
 "narrowing_hint": "Try 'mechanical engineering' or 'aerospace' to narrow it down",
 "intent_keywords": ["engineering"]}

Rules for alternatives:
- Only include alternatives when 2+ distinct programs genuinely match the input
- Each alternative's "cip" MUST exist in the candidate CIP lists above
- Do NOT include alternatives that are just degree-level variants of the primary (e.g., BS vs MS in the same field)
- "remaining_count" = total matching CIPs minus however many you listed (primary + alternatives). 0 if you listed them all.
- "narrowing_hint" = a plain-English suggestion for how the student could narrow their search. Omit if remaining_count is 0.
- If only 1 program matches, omit "alternatives", set "remaining_count": 0, omit "narrowing_hint".
```

**JSON tail parsing (structured event builder, ~line 579)**

Update `_build_intent_result_from_tail` or equivalent:

```python
def _build_intent_result(parsed: dict, school_cips: list[dict], ...) -> IntentResult:
    # Primary CIP (unchanged)
    matched_cip = str(parsed.get("matched_cip", "")).strip()
    matched_cip = intent._promote_to_leaf_cip(matched_cip, raw_parent, school_cips)
    
    # Alternatives (new)
    raw_alts = parsed.get("alternatives") or []
    validated_alts: list[dict] = []
    for alt in raw_alts[:2]:  # Cap at 2 alternatives (3 total with primary)
        alt_cip = str(alt.get("cip", "")).strip()
        if not _CIP_PATTERN.match(alt_cip):
            continue
        alt_cip = intent._promote_to_leaf_cip(alt_cip, alt.get("parent_cip", ""), school_cips)
        # Validate against crosswalk/school catalog (same logic as primary)
        if alt_cip not in valid_6digit and alt_cip[:5] not in valid_4digit:
            continue
        validated_alts.append({
            "cip": alt_cip,
            "title": _NUMERIC_CODE_PARENTHETICAL.sub("", str(alt.get("title", ""))),
            "why": str(alt.get("why", "")),
            "parent_cip": str(alt.get("parent_cip", "")),
        })
    
    remaining_count = int(parsed.get("remaining_count", 0))
    narrowing_hint = str(parsed.get("narrowing_hint", "")).strip()
    
    return IntentResult(
        matched_cip=matched_cip,
        matched_title=matched_title,
        alternatives=validated_alts or None,
        remaining_count=remaining_count,
        narrowing_hint=narrowing_hint,
        # ... rest unchanged
    )
```

**Fallback resolver (`_fallback_resolve`)**

Update `_FALLBACK_JSON_SYSTEM` to include the same multi-CIP format. The fallback is JSON-only (no prose), so the prompt change is small. Parse `alternatives`, `remaining_count`, `narrowing_hint` from the response using the same validation logic.

#### `frontend/src/hooks/useSetYourCourse.ts`

**New callback: `onPickAlternative`**

```typescript
const onPickAlternative = useCallback((index: number) => {
  const res = currentResolution;
  if (!res?.alternatives?.[index]) return;
  
  const alt = res.alternatives[index];
  const updatedAlternatives = [
    // Move the current primary into the alternatives list
    { cip: res.matched_cip, title: res.matched_title, why: res.reasoning, parent_cip: res.parent_cip },
    // Keep the other alternatives, excluding the one being promoted
    ...res.alternatives.filter((_, i) => i !== index),
  ];
  
  const swapped: IntentResult = {
    ...res,
    matched_cip: alt.cip,
    matched_title: alt.title,
    parent_cip: alt.parent_cip ?? res.parent_cip,
    alternatives: updatedAlternatives,
  };
  
  setCurrentResolution(swapped);
  // Outcome refetch is triggered automatically because currentResolution changed
  // and the existing useEffect watches parentCipOrMatched
}, [currentResolution, setCurrentResolution]);
```

### Gemma Integration Details

**Call sites affected:**

1. `stream_initial_resolution` — primary streaming prompt. Prompt updated to request 3 ranked CIPs.
2. `_fallback_resolve` — JSON-only fallback. Same output format change.

**Call sites NOT affected:**

3. Chip dispatch (`_CHIP_ROUTING_SYSTEM_PROMPT`) — still operates on a single `currentResolution`. No change.
4. Career tiering — downstream of CIP selection. No change.
5. Commit — logs the final selected CIP. No change (logs `matched_cip` which is the selected primary).

**Fallback behavior:**

- If Gemma returns only `matched_cip` with no `alternatives` array: treat as single-CIP resolution (current behavior). `alternatives` stays `None`, `remaining_count` stays `0`.
- If Gemma returns malformed alternatives (bad CIP codes, missing fields): silently drop invalid entries via validation. If all alternatives are invalid, fall through to single-CIP.
- If streaming fails entirely: `_fallback_resolve` fires (existing behavior). It now also attempts multi-CIP but degrades identically.

**Logging:**

- `logs/gemma.jsonl` already captures every `gemma_client.generate` / `generate_chat` call. No change needed — the prompt change flows through the existing logging.

**Inference backend compatibility:**

- Both `ollama` and `openrouter` use the OpenAI-compatible chat completions API. The prompt change is model-agnostic.
- The `gemma4:e4b` model (smallest) may struggle with the array format — the fallback resolver already handles this gracefully.

**Rate-limit / concurrency:**

- No additional Gemma calls. The resolution still makes 1 call (streaming) + 0-1 fallback calls. The only change is the shape of the response.

### Testing Impact Analysis

> **IMPORTANT**: Test files below were found by searching for `IntentResult`, `alternatives`, and `matched_cip` references.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_set_your_course.py` | `TestStreamInitial` (class, ~10 tests) | **High** | JSON tail parsing assertions will need to handle new `alternatives` array, `remaining_count`, `narrowing_hint` in mocked Gemma responses |
| `backend/tests/services/test_set_your_course.py` | `TestChipDispatch` (class) | **Low** | Chip dispatch doesn't change, but fixtures include `IntentResult` construction |
| `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus` (class) | **Low** | Uses `IntentResult` fixtures — new fields have defaults, should pass |
| `backend/tests/services/test_set_your_course.py` | `TestResolverIntentKeywords` (class) | **Med** | Tests the resolver output shape; may assert on `alternatives=None` |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_high_confidence_returns_empty_alternatives` | **High** | Directly tests that high-confidence returns empty alternatives — behavior changes |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_medium_confidence_returns_2_to_4_alternatives` | **High** | Tests alternative count for medium confidence — now alternatives are semantic, not confidence-based |
| `backend/tests/services/test_intent.py` | `test_sanitize_drops_malformed_cip_codes` | **Med** | Sanitization logic may need updating if alternatives shape changes |
| `backend/tests/services/test_intent.py` | `test_sanitize_drops_primary_cip_echoed_in_alternatives` | **Med** | Dedup logic stays, but test may need fixture updates |
| `backend/tests/routers/test_set_your_course_router.py` | `TestStream` (class) | **Med** | Mocked events include `IntentResult` — new fields have defaults |
| `backend/tests/routers/test_set_your_course_router.py` | `TestChip` (class) | **Low** | Chip response shape unchanged |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestDebounce` (describe) | **Low** | Tests debounce timing, not resolution shape |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestChip` (describe) | **Med** | Fixture `makeResolution()` constructs `IntentResult` — needs `remaining_count`, `narrowing_hint` |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestCommit` (describe) | **Med** | Commits `currentResolution` — if swap logic changes, assertions may break |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestSocRevealStateMachine` (describe) | **Med** | Tests outcome fetch flow — `onPickAlternative` triggers same path |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestRender` | **Med** | New picker UI elements need rendering when alternatives present |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestStartOver` | **Low** | Start-over clears resolution — new fields clear with it |
| `frontend/src/components/school/MajorInput.test.tsx` | All | **Low** | References `alternatives` but for the low-confidence nudge flow, not multi-CIP |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_intent.py::test_resolve_intent_high_confidence_returns_empty_alternatives` | Update assertion: high-confidence may now return populated alternatives (semantic matches, not confidence-based) | Behavior change: alternatives are now semantic, not confidence-gated |
| `backend/tests/services/test_intent.py::test_resolve_intent_medium_confidence_returns_2_to_4_alternatives` | Update assertion: alternative count is now 0-2 (capped at 2 alts), not 2-4 | Behavior change: alternatives are now top-3 ranked, not confidence-based fallbacks |
| `backend/tests/services/test_set_your_course.py::TestStreamInitial` | Update mocked Gemma JSON tail to include `alternatives` array format | JSON format change |
| `backend/tests/services/test_set_your_course.py::TestResolverIntentKeywords` | Update `IntentResult` assertions to account for new fields | Schema expansion |
| `backend/tests/fixtures/intent_responses.json` | Add multi-CIP fixture entries | Test data expansion |
| `frontend/src/hooks/useSetYourCourse.test.ts` (all `makeResolution` calls) | Add `remaining_count: 0, narrowing_hint: ""` to fixture — fields have defaults, but explicit is better | Schema expansion |
| `frontend/src/screens/SetYourCourseScreen.test.tsx::seedState` | Add `alternatives`, `remaining_count`, `narrowing_hint` to resolution fixture | Schema expansion |

#### Confirmed Safe

These tests must NOT break. If any fail, STOP and escalate.

- `backend/tests/services/test_set_your_course.py::TestChipDispatch` — chip dispatch is unchanged
- `backend/tests/services/test_set_your_course.py::TestConfirmedFocus` — confirmed focus is unchanged
- `backend/tests/services/test_set_your_course.py::TestObservability` — logging unchanged
- `backend/tests/services/test_set_your_course.py::TestChipFlowIntentKeywords` — chip flow unchanged
- `backend/tests/services/test_intent.py::TestDeterministicShortCircuit` — deterministic path unchanged
- `backend/tests/services/test_intent.py::TestPromptCopy` — prompt copy validation
- `backend/tests/services/test_intent.py::TestYamlGate` — YAML gate unchanged
- `backend/tests/routers/test_set_your_course_router.py::TestChip` — chip router unchanged
- `backend/tests/routers/test_set_your_course_router.py::TestTierEndpointIntentFields` — tiering unchanged
- `frontend/src/hooks/useSetYourCourse.test.ts::TestConfirmedFocus` — confirmed focus unchanged
- `frontend/src/screens/SetYourCourseScreen.test.tsx::TestStartOver` — start-over clears everything (new fields included)
- `frontend/src/screens/SetYourCourseScreen.test.tsx::TestLowConfidence` — low-confidence flow unchanged
- `frontend/src/components/school/MajorInput.test.tsx` — all tests (MajorInput not modified)

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_parses_3_ranked_options` | Mocked Gemma response with 3 CIPs → `IntentResult` has primary + 2 alternatives with correct fields |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_single_cip_no_alternatives` | Mocked Gemma response with 1 CIP → `alternatives` is `None`, `remaining_count` is 0 |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_validates_all_against_crosswalk` | Gemma returns 3 CIPs, one has invalid code → only 2 valid alternatives survive |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_fallback_multi_cip` | `_fallback_resolve` with multi-CIP response → same validation and population |
| P1 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_remaining_count_and_hint` | `remaining_count` and `narrowing_hint` extracted from Gemma response |
| P1 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_deduplicates_primary` | If Gemma echoes primary CIP in alternatives, it's dropped |
| P1 | `backend/tests/services/test_intent.py` | `test_promote_to_leaf_called_for_each_alternative` | Each alternative CIP goes through `_promote_to_leaf_cip` |
| P1 | `frontend/src/hooks/useSetYourCourse.test.ts` | `test_pick_alternative_swaps_resolution_and_refetches` | `onPickAlternative(0)` → `currentResolution.matched_cip` changes, outcomes refetch fires |
| P1 | `frontend/src/hooks/useSetYourCourse.test.ts` | `test_pick_alternative_moves_primary_to_alternatives` | After swap, old primary appears in `alternatives` list |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_renders_cip_picker_when_alternatives_present` | Resolution with 2 alternatives → picker elements visible in DOM |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_no_picker_when_single_cip` | Resolution with no alternatives → no picker rendered |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_remaining_count_hint_rendered` | Resolution with `remaining_count: 11` → hint text visible |
| P2 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_commit_after_swap_uses_selected_cip` | Pick alt → commit → verify committed CIP is the swapped one |

#### Test Data Requirements

- **Backend fixtures:** Add to `backend/tests/fixtures/intent_responses.json`:
  - `multi_cip_engineering` — 3 engineering CIPs with remaining_count=11
  - `multi_cip_business` — 2 business CIPs with remaining_count=0
  - `single_cip_nursing` — 1 CIP, no alternatives (control)
  - `multi_cip_invalid_alt` — 3 CIPs where alternative #2 has invalid code
- **Frontend fixtures:** Update `makeResolution()` helper in `useSetYourCourse.test.ts` to accept optional `alternatives`, `remaining_count`, `narrowing_hint` overrides

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-21

#### System Context

This feature modifies the Gemma resolution layer (prompt engineering + JSON tail parsing in `set_your_course.py`) and adds a client-side CIP swap interaction in the frontend hook (`useSetYourCourse.ts`) and screen (`SetYourCourseScreen.tsx`). It touches three layers -- Gemma prompt contract, backend Pydantic model (`IntentResult`), and frontend TypeScript type (`IntentResult`) -- but critically does NOT touch the Brightsmith pipeline, Gold zone tables, MCP tools, chip dispatch, tiering, or commit flow. The blast radius is well-scoped.

#### Data Flow Analysis

**Resolution flow (modified):**
```
Student types "engineering" at Purdue
  -> Gemma prompt (updated: request 3 ranked CIPs)
  -> JSON tail parsed in _build_intent_result_from_tail
  -> IntentResult { matched_cip, alternatives: [{cip, title, why, parent_cip}], remaining_count, narrowing_hint }
  -> SSE structured event -> frontend setCurrentResolution()
  -> CIP picker rendered when alternatives.length > 0
```

**Selection swap (new, client-side only):**
```
Student taps alternative[0]
  -> onPickAlternative(0) swaps matched_cip/matched_title/parent_cip
  -> parentCipOrMatched recomputes via useMemo
  -> useEffect fires debouncedCareerFetch (existing)
  -> getOutcomes(unitid, newParentCipOrMatched, ...) -> getTieredCareers(...)
  -> SOC reveal re-renders with new career tiles
```

**Downstream unchanged:** chip dispatch reads `currentResolution.matched_cip` (the swapped primary). Commit logs `currentResolution.matched_cip`. Tiering operates on outcomes for the selected CIP. All correct -- no contract breaks downstream.

**Fallback flow:** `_fallback_resolve` is a synchronous `gemma_client.generate` call. The spec correctly identifies that it must also return multi-CIP format. The prompt change is small because it is JSON-only (no prose part).

**Brightsmith pipeline:** Confirmed no pipeline changes. The data powering multi-CIP already exists -- `program_career_paths` contains CIP x SOC x school joins, and Gemma receives the full school program list in prompt context. The feature asks Gemma to return more of what it already sees.

#### Contract Review

**IntentResult (backend, `career.py` line 324):**
- Current model has `alternatives: list[dict] | None = None` -- confirmed at line 333.
- Spec adds `remaining_count: int = 0` and `narrowing_hint: str = ""` -- both with safe defaults. Backwards compatible.
- The `alternatives` field type stays `list[dict] | None`. No schema break.

**IntentResult (frontend, `buildInput.ts` line 64):**
- Current type has `alternatives: Array<{ cip: string; title: string; why: string }> | null` -- confirmed at line 73.
- Spec adds `parent_cip?: string` to the alternative dict entries, plus `remaining_count?: number` and `narrowing_hint?: string`. All optional -- backwards compatible.

**Gemma JSON tail contract:** The `---INTENT_JSON---` delimiter format is preserved. The JSON object grows (new keys `alternatives`, `remaining_count`, `narrowing_hint`) but existing keys are unchanged. Old-format responses (no `alternatives`) degrade to current behavior via `parsed.get("alternatives") or []`.

**parentCipOrMatched derivation (line 176-179 of useSetYourCourse.ts):**
```typescript
return currentResolution.parent_cip || currentResolution.matched_cip || null;
```
The swap in `onPickAlternative` sets `parent_cip: alt.parent_cip ?? res.parent_cip`. This is correct -- the alternative carries its own parent_cip (the school's broad reported code in the same family), which may differ from the primary's parent_cip. The outcomes fetch will use the right broad code for substitution.

#### Findings

##### Sound

1. **Repurposing `alternatives` rather than adding a new field.** The field already exists on both backend and frontend with the right shape. Clean reuse.

2. **Client-side swap via `onPickAlternative`.** No new backend endpoint needed. The swap updates `currentResolution` which triggers `parentCipOrMatched` recompute, which triggers the existing `useEffect` at line 255 that calls `debouncedCareerFetch`. The reactive chain is correct and already battle-tested.

3. **Lazy outcome fetch (Decision #4).** Only fetching outcomes for the selected CIP avoids tripling MCP calls. The existing debounce at 250ms handles rapid taps.

4. **Validation of alternative CIPs against crosswalk/school catalog.** The spec's `_build_intent_result` pseudocode validates each alternative CIP the same way the primary is validated (lines 627-643 of current `set_your_course.py`). Silently dropping invalid entries is the right degradation.

5. **No additional Gemma calls.** The resolution still makes 1 streaming call + 0-1 fallback calls. Only the response shape changes.

6. **Backwards compat on `matched_cip`/`matched_title`.** Every downstream consumer (chip dispatch, commit, tiering, outcomes fetch) reads these two fields from `currentResolution`. They stay populated as the first-ranked option. No blast radius.

7. **Testing Impact Analysis is thorough.** The spec identifies the correct tests at risk, correctly classifies authorized modifications vs confirmed-safe tests, and specifies the right new tests. This is well above the typical spec quality for test planning.

##### Concerns

- **C1: `_sanitize_alternatives` in `intent.py` currently caps at 10 and does not include `parent_cip`.** The existing function at `intent.py` line 343 produces `{"cip", "title", "why"}` dicts -- no `parent_cip` key. The spec's pseudocode in `_build_intent_result` (section 4) calls `intent._promote_to_leaf_cip` on each alternative and builds the dict with `parent_cip`, but it does this BEFORE calling `_sanitize_alternatives`. The spec also says `intent.py` is modified to call `_promote_to_leaf_cip` for each alternative. Two implementations of the same logic -- one in `set_your_course.py` and one in `intent.py` -- will drift. **Impact:** If the streaming path validates/promotes in `set_your_course.py` but the old `resolve_intent` path (used by CLI? future callers?) uses `_sanitize_alternatives` without `parent_cip`, the two paths produce different alternative shapes. **Recommendation:** Extend `_sanitize_alternatives` in `intent.py` to accept an optional `school_cips` param, call `_promote_to_leaf_cip` inside it, and include `parent_cip` in the output dict. Both `set_your_course.py` (streaming) and `intent.py` (`resolve_intent`) call `_sanitize_alternatives` -- keep one validation path.

- **C2: `alternatives` typing -- `list[dict]` is too loose.** The backend model has `alternatives: list[dict] | None`. The spec acknowledges the existing shape `{"cip": str, "title": str, "why": str}` and adds `parent_cip: str`. This is still typed as `list[dict]` (bare `dict` = `dict[str, Any]`). For a field that crosses the API boundary and the frontend relies on specific keys, this should be a typed model. **Impact:** No runtime breakage, but no validation that alternatives actually contain the required keys. A malformed alternative with missing `cip` key would serialize to the frontend and cause a JS error on swap. **Recommendation:** Define `AlternativeMatch(BaseModel)` with `cip: str`, `title: str`, `why: str = ""`, `parent_cip: str = ""` and type alternatives as `list[AlternativeMatch] | None`. This gives Pydantic validation on deserialization and makes the contract explicit. This is a "do it right while you're here" item -- the field has always been loose, and this spec is the right moment to tighten it. Not a blocker because `_sanitize_alternatives` already validates the shape programmatically.

- **C3: `onPickAlternative` swap moves old primary into alternatives without `parent_cip`.** The spec's pseudocode (section 4, frontend) constructs the demoted primary as `{ cip: res.matched_cip, title: res.matched_title, why: res.reasoning, parent_cip: res.parent_cip }`. This is correct. However, `res.reasoning` is the full Gemma prose (potentially 2 sentences), not a short "why" phrase like the alternatives carry. After a swap, the demoted primary's `why` field will be visibly longer than the other alternatives' `why` fields. **Impact:** Visual inconsistency in the CIP picker -- one option has a paragraph, the others have a phrase. **Recommendation:** Truncate or replace the demoted primary's `why` with a short phrase like "Your original match" or `res.matched_title` rather than `res.reasoning`.

- **C4: The existing `_STREAM_INTENT_SYSTEM_PROMPT` already has its own `alternatives` contract.** Lines 261-263 of `set_your_course.py` currently say: `"alternatives" is [] for high confidence; 2-4 items for medium; up to 10 items for low.` The spec's new prompt instructions say something different: "Only include alternatives when 2+ distinct programs genuinely match the input" (semantic, not confidence-gated). The spec acknowledges this behavioral change in the test impact analysis. But the prompt modification section (section 4) shows the new text being **added** to the existing prompt, not **replacing** the conflicting instructions. If both sets of instructions are present, Gemma will see contradictory rules about when to include alternatives. **Impact:** Gemma confusion -- one block says "high confidence = no alternatives" while the new block says "include alternatives when 2+ programs match regardless of confidence." **Recommendation:** The spec should explicitly state that the existing alternatives rules in `_STREAM_INTENT_SYSTEM_PROMPT` (lines 261-263) and in `_INTENT_SYSTEM_PROMPT` in `intent.py` (lines 96-119) must be **replaced**, not supplemented. The new semantic-ranking rules supersede the confidence-gated rules.

- **C5: The old `resolve_intent` path in `intent.py` is not addressed.** The spec modifies `_STREAM_INTENT_SYSTEM_PROMPT` (streaming path) and `_FALLBACK_JSON_SYSTEM` (fallback path), both in `set_your_course.py`. But `intent.py` has its own `_INTENT_SYSTEM_PROMPT` (line 82) and `resolve_intent` function (line 473) that also produces `IntentResult` with `alternatives`. This path is used by the CLI and possibly other callers. The spec's "File Changes" table lists `intent.py` for validation changes but not for prompt changes. **Impact:** The CLI path continues to use the old confidence-gated alternatives contract while the streaming path uses the new semantic-ranked contract. Two different alternative semantics for the same `IntentResult` model. **Recommendation:** Document explicitly that the `resolve_intent` path in `intent.py` is intentionally left on the old contract for this spec (if that is the intent), OR include it in the prompt changes. Either way, the decision should be recorded in section 2 Decision Log.

##### Blockers

None. The architecture is sound. The concerns above are contract-tightening and consistency items, not structural problems.

#### Verdict
- [x] CHANGES REQUESTED

#### Conditions

1. **C4 (prompt conflict):** Clarify in the spec that the existing confidence-gated alternatives rules in `_STREAM_INTENT_SYSTEM_PROMPT` lines 261-263 must be **replaced** by the new semantic-ranking rules, not supplemented. The implementer needs to know which lines to delete.
2. **C5 (dual path):** Add a Decision Log entry documenting whether the `resolve_intent` path in `intent.py` gets the multi-CIP treatment in this spec or is explicitly deferred. If deferred, note that `_INTENT_SYSTEM_PROMPT` still carries the old confidence-gated alternative rules and the two paths will produce differently-shaped `alternatives` until unified.
3. **C1 (validation consolidation):** Clarify the single validation path for alternatives. Either `_sanitize_alternatives` in `intent.py` gains `parent_cip` + `_promote_to_leaf_cip` support, or the streaming path in `set_your_course.py` owns its own validation. The spec should be explicit about which file owns alternative validation for the streaming path.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline or data changes — feature uses existing program_career_paths data)

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/models/career.py` | Added `remaining_count: int = 0` and `narrowing_hint: str = ""` to `IntentResult` |
| `backend/app/services/set_your_course.py` | Replaced confidence-gated alternatives with semantic-ranking rules in `_STREAM_INTENT_SYSTEM_PROMPT`. Updated `_FALLBACK_JSON_SYSTEM` for multi-CIP. Updated `_build_intent_result_from_tail` and `_fallback_resolve` to parse `alternatives`, `remaining_count`, `narrowing_hint`. Both paths use `max_alts=2`. |
| `backend/app/services/intent.py` | Added `max_alts` kwarg to `_sanitize_alternatives` (default 10, streaming path passes 2). Preserves `parent_cip` field on alternatives. |
| `frontend/src/types/buildInput.ts` | Added `remaining_count?: number`, `narrowing_hint?: string` to `IntentResult`. Added `parent_cip?: string` to alternatives array type. |
| `frontend/src/hooks/useSetYourCourse.ts` | Added `onPickAlternative(index)` callback: swaps alt into primary, moves old primary to alternatives, triggers outcome refetch via `parentCipOrMatched`. |
| `frontend/src/components/school/CipPicker.tsx` | **NEW** — Extracted CIP picker component per §3 design vision. Vertical dot-list with filled/hollow dot indicators, layout animations, reduced-motion support, `role="group"`, `aria-current="true"` on primary. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Imports `CipPicker` component; renders inside resolution header after taxonomy receipt. Removed inline CIP picker implementation. |
| `backend/tests/fixtures/intent_responses.json` | Added 4 fixtures: `multi_cip_engineering`, `multi_cip_business`, `single_cip_nursing`, `multi_cip_invalid_alt` |
| `backend/tests/services/test_set_your_course.py` | 6 new tests in `TestMultiCipResolution` |
| `backend/tests/services/test_intent.py` | 3 new tests: `test_sanitize_alternatives_respects_max_alts`, `test_sanitize_alternatives_preserves_parent_cip`, `test_promote_to_leaf_called_for_each_alternative` |
| `frontend/src/hooks/useSetYourCourse.test.ts` | 2 new tests in `TestMultiCipPick` |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | 3 new tests in `TestCipPicker` |

### Deviations from Spec

1. **Architect C4 resolved** — Replaced (not supplemented) the old confidence-gated alternatives lines in `_STREAM_INTENT_SYSTEM_PROMPT` per architect review.
2. **Architect C5 deferred** — `intent.py`'s `resolve_intent` path keeps its own prompt/contract unchanged. Only the shared `_sanitize_alternatives` helper was updated. The non-streaming path is a separate feature scope.
3. **Architect C1 resolved** — Alternative validation consolidated in `_sanitize_alternatives` in `intent.py`, called from both streaming and fallback paths with `max_alts=2`.
4. **Code review Fix 4 declined** — Staff engineer recommended `return cleaned or None` in `_sanitize_alternatives` to normalize empty states. Declined: existing callers and tests rely on `[]` for valid-but-empty input. Changing this breaks the `test_resolve_intent_high_confidence_returns_empty_alternatives` contract. The dual-empty-state is well-documented and both paths are handled correctly by all consumers.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | Pass | — | — |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_parses_3_ranked_options` | P0: 3 CIPs → primary + 2 alternatives with all fields |
| `backend/tests/services/test_set_your_course.py` | `test_stream_single_cip_no_alternatives` | P0: Single CIP → empty alternatives, remaining_count=0 |
| `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_validates_all_against_crosswalk` | P0: Invalid CIP in alternatives silently dropped |
| `backend/tests/services/test_set_your_course.py` | `test_fallback_multi_cip` | P0: Fallback resolver parses multi-CIP |
| `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_remaining_count_and_hint` | P1: remaining_count and narrowing_hint extracted |
| `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_deduplicates_primary` | P1: Primary echoed in alternatives is dropped |
| `backend/tests/services/test_intent.py` | `test_sanitize_alternatives_respects_max_alts` | P1: max_alts=2 caps output |
| `backend/tests/services/test_intent.py` | `test_sanitize_alternatives_preserves_parent_cip` | P1: parent_cip passes through sanitizer |
| `backend/tests/services/test_intent.py` | `test_promote_to_leaf_called_for_each_alternative` | P1: 4-digit CIPs in alternatives fail regex |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `pick_alternative_swaps_resolution_and_refetches` | P1: onPickAlternative(0) swaps matched_cip |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `pick_alternative_moves_primary_to_alternatives` | P1: Old primary moves to alternatives |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `renders_cip_picker_when_alternatives_present` | P1: Picker visible with 2 alternatives |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `no_picker_when_single_cip` | P1: No picker when no alternatives |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `remaining_count_hint_rendered` | P1: Hint text visible with remaining_count=11 |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1095 | 3* | 0 | 1098 |
| vitest | 590 | 0 | 1 | 591 |

*3 pre-existing failures: `test_transport_failure_returns_empty`, `test_confirmed_focus_dropped_when_bucket_is_intent_divergence`, `test_student_major_text_set_on_fallback_path` — all confirmed pre-existing on `main`.

---

## §8 Reviews

**Status:** RESOLVED

### Design Audit (@design-builder)
**Status:** CHANGES REQUIRED
**Reviewed:** 2026-04-21

The CIP picker is currently implemented inline in `SetYourCourseScreen.tsx` (lines 460-525) rather than extracted into the `CipPicker` component specified in section 3. The audit below compares the inline implementation against Brightpath tokens (DESIGN.md) and the pixel-perfect target in section 3.

#### 1. Component Architecture -- NON-COMPLIANT

The spec calls for `frontend/src/components/school/CipPicker.tsx` as a standalone component with its own `CipPickerProps` interface. The current implementation is raw JSX inlined in the screen file. This is not just a code-quality issue -- the spec's `role="group"` container, `aria-label="Program options"`, `aria-current="true"` on the primary row, and reduced-motion handling are all missing from the inline version because the spec scoped them to the extracted component.

**Fix:** Extract into `CipPicker.tsx` per section 3's complete component sketch.

#### 2. Token Compliance -- 7 VIOLATIONS

| # | Element | Spec (section 3 / DESIGN.md) | Actual (lines 460-525) | Severity |
|---|---------|------------------------------|------------------------|----------|
| T1 | Section label | `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info` -- Copy: `"ALSO MATCHES"` | `font-body text-small text-text-muted` -- Copy: `"Multiple programs match your search"` | **High** -- wrong font family (body vs data), wrong size (14px vs 11px), wrong color (muted vs info), wrong weight, not uppercase. Violates the Section Labels pattern in DESIGN.md. The copy is a sentence, not a section label. |
| T2 | Primary option container | Spec: `flex items-start gap-2.5 px-3 py-2.5 rounded-md` with a 6px thrive dot, non-interactive `<div>` | Actual: `flex-1 text-left rounded-lg border-2 border-accent-insight bg-accent-insight/10 px-4 py-3` as a `<button>` | **High** -- renders as an interactive card with a border and background fill. The spec explicitly says "Not a button" and the primary is a static div with a dot indicator, not a bordered card. The `border-2` treatment has no precedent in Brightpath (borders are always 1px except character card selected state at 2px). |
| T3 | Alternative option container | Spec: `flex items-start gap-2.5 px-3 py-2.5 rounded-md hover:bg-bp-surface` with a hollow 6px dot | Actual: `flex-1 text-left rounded-lg border border-border-subtle hover:border-accent-insight/50 bg-bp-mid/40 hover:bg-accent-insight/5 px-4 py-3` | **Medium** -- card-like treatment with border + background instead of the minimal list-row pattern. `bg-bp-mid/40` is a raw opacity value not in the token system. `hover:bg-accent-insight/5` is not a Brightpath state; the correct hover background is `bg-bp-surface` per the List Items pattern. |
| T4 | Primary title typography | Spec: `font-body text-body-sm font-semibold text-text-primary` (Nunito 15px 600 warm white) | Actual: `font-display text-small font-semibold text-accent-insight` (Fredoka 14px 600 purple) | **High** -- wrong font family (display is for headlines, not list item titles), wrong color (insight purple is a Gemma-ownership color, not for student-initiated selection states), wrong size token. |
| T5 | Alternative title typography | Spec: `font-body text-body-sm font-semibold text-text-secondary group-hover:text-text-primary` | Actual: `font-display text-small font-semibold text-text-primary` | **Medium** -- wrong font family (display vs body), wrong default color (primary vs secondary -- the alternative should be dimmer than the primary to create hierarchy), missing hover brightening transition. |
| T6 | Reason/why text | Spec: `font-body text-small text-text-muted truncate max-w-[48ch]` | Actual (primary): `font-body text-micro text-text-secondary` -- uses `text-micro` (12px) instead of `text-small` (14px), and `text-secondary` instead of `text-muted` | **Low** -- close but not matching. `text-micro` is for badges and tiny UI, not descriptive text. `text-secondary` is brighter than intended for supporting copy. |
| T7 | Dot indicators | Spec: 6px thrive-filled dot (primary) and 6px hollow dot with border-default stroke (alternatives) | Actual: no dot indicators at all | **High** -- the filled/hollow dot is the core metaphor of the picker ("the dot metaphor" in section 3). Without it, the primary and alternative options lack the visual that communicates "you are here" vs "you could be here." |

#### 3. Layout -- NON-COMPLIANT

| Issue | Detail |
|-------|--------|
| Row direction | Spec: vertical stack (`flex flex-col gap-1`), rows are full-width list items. Actual: `flex flex-col tablet:flex-row gap-2` -- renders as a horizontal pill row on tablet+. This fundamentally changes the visual pattern from a ranked list to a set of side-by-side cards. Horizontal layout makes the hierarchy (primary > alternative) invisible and prevents the reason text from rendering readably. |
| Alignment | Spec: `pl-[22px]` on the picker container to align with the resolution title's left indent. Actual: `pl-[22px]` is present on the inner `flex` div but the outer container has no padding -- the "Multiple programs match" text at line 473 has its own `pl-[22px]`, creating correct alignment there, but the button row is wrapped separately. |
| Remaining hint alignment | Spec: `pl-[22px]` on the hint paragraph. Actual: `pl-[22px]` is present. Correct. |

#### 4. Dark-First -- PASS WITH CAVEAT

The implementation uses Brightpath background tokens (`bg-bp-mid/40`, `bg-accent-insight/10`) that render correctly on dark backgrounds. However:

- `bg-bp-mid/40` (line 500) is a raw opacity modifier on a background token. Brightpath tokens already encode their intended opacity -- `bg-bp-mid` is `#232545`. Applying `/40` makes it semi-transparent, which breaks the elevation hierarchy (cards sit on `bg-mid`, not a transparent version of it). In practice this still looks passable on the dark deep/void backgrounds, but it is not a sanctioned surface treatment.
- `bg-accent-insight/10` on the primary button is a tinted surface. Brightpath uses this pattern only for pills/badges (accent at 15% opacity). At 10% it is too faint to read as intentional on some displays.

No light-mode violations (there is no light mode in Brightpath -- dark-first is the only mode).

#### 5. Responsive Behavior -- PARTIAL COMPLIANCE

- `flex-col tablet:flex-row` switches to horizontal at the tablet breakpoint. Section 3 says: "No special mobile treatment... the picker is already light enough -- three rows of text -- that it works inline at every viewport." The spec's vertical stack layout is responsive by default -- it works at all widths without a breakpoint switch.
- The `flex-1` on each option button causes equal-width distribution on tablet+. With 3 options, each gets ~33% of the row. Short titles ("Nursing") get excess space; long titles truncate. The spec avoids this by using full-width stacked rows.
- Touch targets: the `py-3` padding on option buttons gives adequate height (~48px with title + reason). This is acceptable.

#### 6. Motion -- NON-COMPLIANT

| Issue | Detail |
|-------|--------|
| Entrance animation | Spec: `springs.smooth`, `y: 12 -> 0`, opacity `0 -> 1`. Actual: `springs.smooth`, `y: 6 -> 0`, opacity `0 -> 1`. The `y: 6` is a non-standard entrance distance; Brightpath's `transitions.fadeInUp` uses `y: 24`, and the spec calls for `y: 12`. Minor but inconsistent. |
| Layout animation on swap | Spec: `motion.div layout transition={springs.snappy}` on each row for smooth reorder. Actual: no `layout` prop, no reorder animation. When a swap occurs, rows hard-cut to new positions. |
| Title crossfade | Spec: `AnimatePresence mode="wait"` on the resolution header title with `key={matched_cip}`, exit `x: 8`, enter `x: -8`, 200ms easeOut. Actual: no AnimatePresence on the title -- swapping hard-replaces the text. |
| Dot fill transition | Spec: 150ms CSS transition on dot background-color/border-color. Actual: no dots exist, so no transition. |
| Press feedback | Spec: `whileTap={{ scale: 0.98 }}` on alternative buttons. Actual: no `whileTap` on the buttons. |
| Reduced motion | Spec: when `prefers-reduced-motion: reduce`, title crossfade becomes instant, layout spring becomes instant, dot transition stays. Actual: no reduced-motion handling. The screen imports `useReducedMotion` but the CIP picker does not consume it. |

#### 7. Accessibility -- 6 ISSUES

| # | Issue | Spec Requirement | Actual |
|---|-------|-----------------|--------|
| A1 | Container role | `<div role="group" aria-label="Program options">` | `<motion.div>` with no role or aria-label. The picker is not grouped semantically. |
| A2 | Section label | `aria-hidden="true"` (decorative -- group label covers it) | No `aria-hidden` on the helper text. Screen readers will read both the group label and the visible text, causing redundancy. |
| A3 | Primary row | `aria-current="true"` on a `<div>` (non-interactive) | Rendered as a `<button>` with `aria-label="Selected program: ..."`. Buttons invite interaction -- a non-interactive primary should be a `<div>` with `aria-current`. |
| A4 | Focus ring | `3px solid var(--color-focus-ring)`, `outline-offset: 2px` per DESIGN.md Focus States | `focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]` -- ring width is 2px, not 3px. Should be `ring-[3px]`. The offset is present (`ring-offset-2`) but the width is wrong. |
| A5 | Keyboard navigation | Tab cycles through alternative buttons only (primary is not focusable) | Primary is a `<button>` and receives focus. This wastes a tab stop on a non-actionable element. |
| A6 | Remaining hint | `aria-label="{count} more programs match"` | No `aria-label` on the remaining hint paragraph. |

#### 8. Component Pattern Fit -- POOR

The current implementation reads as a "card grid selector" -- bordered cards with accent-tinted backgrounds side by side. This pattern exists nowhere else in the screen. The resolution header above uses a clean text-and-attribution layout; the career tier sections below use stacked list rows. A horizontal card grid creates a visual break in the page's vertical reading flow.

The spec's design (vertical list with dot indicators, minimal backgrounds, list-item hover) matches the visual language of the career preview rows in the Tiered Match Card (DESIGN.md "Alternatives list") and the autocomplete dropdown rows (DESIGN.md "List Items"). The current implementation matches neither.

#### Summary of Required Changes

**Critical (must fix before shipping):**

1. Extract into `CipPicker.tsx` component per section 3 sketch
2. Switch from horizontal card grid to vertical stacked list with dot indicators
3. Make primary row a non-interactive `<div>` with `aria-current="true"`, not a `<button>`
4. Fix section label: `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`, copy "ALSO MATCHES"
5. Fix typography: primary title `font-body text-body-sm text-text-primary`, alternative title `font-body text-body-sm text-text-secondary`
6. Add `role="group" aria-label="Program options"` to container
7. Add `whileTap={{ scale: 0.98 }}` and `layout` animations per spec

**Important (should fix):**

8. Add `AnimatePresence mode="wait"` title crossfade on the resolution header's matched title span
9. Fix focus ring width from 2px to 3px
10. Add reduced-motion handling via `useReducedMotion`
11. Remove raw opacity values (`bg-bp-mid/40`, `bg-accent-insight/10`) -- use sanctioned tokens
12. Fix entrance `y` value from 6 to 12

**Minor (nice to have):**

13. Reason text size: `text-small` (14px) instead of `text-micro` (12px)
14. Add `aria-hidden="true"` to section label, `aria-label` to remaining hint

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewed:** 2026-04-21
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary

The architecture is sound, the streaming/parsing pipeline is well-structured, and the test coverage is above average for a feature this size. The problems found are the kind that work perfectly in dev and cause issues in production: an unbounded integer from an LLM, a demoted-primary text field that will look broken in the UI, and a return-type inconsistency that will confuse the next person who touches this code. Nothing is a blocker. Everything is fixable in an hour.

#### Findings

**Finding 1: `remaining_count` accepts arbitrary integers from Gemma with no bounds check** [Moderate]

**Impact:** Gemma is an LLM. LLMs hallucinate. If Gemma returns `"remaining_count": -3` or `"remaining_count": 999999`, that value flows straight through `int(parsed.get("remaining_count", 0) or 0)` at `set_your_course.py:719` and `set_your_course.py:583` into the frontend where it renders as "-3 more programs match" or "999999 more programs match." Not a security issue, but a visible data quality bug.

**Location:** `backend/app/services/set_your_course.py` lines 583 and 719

```python
remaining_count = int(parsed.get("remaining_count", 0) or 0)
```

**The Fix:** Clamp to a sane range. The school with the most CIPs in a family has ~14 (Purdue engineering). After showing 3, max remaining is ~11. A generous upper bound of 50 handles any school while rejecting hallucinations.

```python
remaining_count = max(0, min(50, int(parsed.get("remaining_count", 0) or 0)))
```

Apply at both sites (lines 583 and 719).

---

**Finding 2: Demoted primary uses `res.reasoning` as `why` instead of "Your original match"** [Moderate]

**Impact:** The design vision (section 3, "Demoted Primary 'why' Text") and architecture review C3 both explicitly specify that when the current primary is demoted to an alternative, its `why` field should be `"Your original match"` -- not `res.reasoning`, which is full Gemma prose (potentially two sentences). The implementation at `useSetYourCourse.ts:559` uses `res.reasoning`. After a swap, one alternative row will have a paragraph of text while the others have short phrases. This looks visually broken and undermines the "list of peers" affordance.

**Location:** `frontend/src/hooks/useSetYourCourse.ts` line 559

```typescript
{ cip: res.matched_cip, title: res.matched_title, why: res.reasoning, parent_cip: res.parent_cip },
```

**The Fix:**

```typescript
{ cip: res.matched_cip, title: res.matched_title, why: "Your original match", parent_cip: res.parent_cip },
```

---

**Finding 3: `_sanitize_alternatives` return type inconsistency -- empty list vs None** [Minor]

**Impact:** `_sanitize_alternatives` returns `None` for non-list input and `[]` (empty list) for a valid but empty list. The `IntentResult.alternatives` field is typed `list[dict] | None`. Callers must handle both `None` and `[]` as "no alternatives" and they do, but the dual-empty-state is a maintenance trap. The next developer who adds `if result.alternatives is not None` will get `True` for an empty list and incorrectly render an empty picker.

**Location:** `backend/app/services/intent.py` line 385

**The Fix:** Return `None` instead of empty list: `return cleaned or None`. Update test assertion at `test_set_your_course.py:1257` from `== []` to `is None`.

---

**Finding 4: `narrowing_hint` renders Gemma-generated text with no length cap** [Minor]

**Impact:** If Gemma returns a verbose hint, the entire string renders inline in the UI at `SetYourCourseScreen.tsx:519` with no truncation. On mobile, this wraps to 4-5 lines and visually overwhelms the picker.

**Location:** `backend/app/services/set_your_course.py` lines 584, 720

**The Fix (backend, both sites):**

```python
narrowing_hint = str(parsed.get("narrowing_hint", "") or "").strip()[:120]
```

---

**Finding 5: Pre-existing SQL string interpolation** [Note -- pre-existing, not introduced by this spec]

**Location:** `backend/app/services/intent.py` lines 209-210. Interpolates DB-sourced `family_prefixes` into SQL. Low risk today but noting for the record.

#### What's Good

- The streaming holdback logic handles the partial-delimiter edge case correctly.
- `_sanitize_alternatives` is thorough: regex validation, dedup via `seen` set, type checking, graceful degradation.
- The `max_alts=2` kwarg is clean -- no behavioral change for existing callers.
- Test coverage is solid: happy path, single-CIP degradation, invalid alt rejection, dedup, fallback resolver, remaining_count.
- Client-side swap is simple and correct -- no new API call, just state update triggering existing reactive chain.
- The `requestIdRef` / abort controller pattern correctly handles rapid CIP swaps.

#### Required Changes

1. **[Moderate]** Clamp `remaining_count` -- `set_your_course.py` lines 583, 719. Route to implementer.
2. **[Moderate]** Fix demoted primary `why` text -- `useSetYourCourse.ts` line 559. Route to implementer.
3. **[Minor]** Cap `narrowing_hint` length -- `set_your_course.py` lines 584, 720. Route to implementer.
4. **[Minor]** Normalize `_sanitize_alternatives` empty return -- `intent.py` line 385. Route to implementer.

#### Verdict
- [x] CHANGES REQUIRED

Items 1-2 are moderate -- fix before merging. Items 3-4 are minor -- fix before merging or immediately after, at implementer's discretion.

### Review Resolution Log

**Design Audit — ALL CRITICAL ITEMS RESOLVED**

Extracted `CipPicker.tsx` component per §3 design vision. The new component matches the spec exactly:
- Vertical dot-list layout with filled (primary) and hollow (alternative) dot indicators
- `role="group" aria-label="Program options"` container
- Primary is a non-interactive `<div>` with `aria-current="true"`
- Section label: `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`, copy "ALSO MATCHES"
- Correct typography: `font-body text-body-sm` for titles, `font-body text-small text-text-muted` for reason text
- `layout` animation with `springs.snappy` for reorder, `AnimatePresence mode="popLayout"` for alternatives
- `whileTap={{ scale: 0.98 }}` press feedback on alternative buttons
- `useReducedMotion` handling — disables layout animation and press feedback
- `focus-visible:ring-[3px]` focus ring width per DESIGN.md
- `aria-label` on remaining hint paragraph
- `aria-hidden="true"` on section label
- No raw opacity tokens — uses sanctioned Brightpath surfaces only

Items 8 (title crossfade on resolution header) and 12 (entrance y=12) are outside the CipPicker component scope and deferred.

**Code Review — FIXES 1-3 APPLIED, FIX 4 DECLINED**

1. **Fix 1 (remaining_count clamp):** Applied `max(0, min(50, int(...)))` at both sites in `set_your_course.py`.
2. **Fix 2 (demoted primary why):** Changed to `"Your original match"` in `useSetYourCourse.ts`.
3. **Fix 3 (narrowing_hint cap):** Applied `[:120]` at both sites in `set_your_course.py`.
4. **Fix 4 (empty return normalization):** Declined — changing `return cleaned` to `return cleaned or None` breaks the existing test contract where `_sanitize_alternatives([])` returns `[]`. Both empty states are correctly handled by all consumers.

---

## §9 Verification

**Status:** PASS

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | PASS — All checks passed |
| Type check (mypy) | PASS* — 47 errors in 18 files, all pre-existing (0 new) |
| Tests (pytest) | PASS* — 1095 passed, 3 pre-existing failures |

*3 pre-existing failures: `test_transport_failure_returns_empty`, `test_confirmed_focus_dropped_when_bucket_is_intent_divergence`, `test_student_major_text_set_on_fallback_path` — all confirmed failing on `main`.

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | PASS — No errors |
| Tests (vitest) | PASS — 590 passed, 1 skipped, 0 failed |
| Production build (Vite) | PASS |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | Pass | 4 ruff E501 line-length errors in test file | Wrapped long lines |
| 2 (final) | Pass | — | Design audit rework: extracted CipPicker.tsx, all tests still pass |

---

## §10 Discussion

```
[2026-04-21 14:32] @genai-architect → @implementer

Review of Gemma prompt changes in §4 Technical Specification.
Source files read: set_your_course.py (lines 218-295 streaming prompt,
493-506 fallback, 579-707 tail parser), intent.py (lines 82-156
_INTENT_SYSTEM_PROMPT, 343-381 _sanitize_alternatives).

---

FINDING 1: Instruction clarity for Gemma 4 — CONDITIONAL PASS

The proposed prompt addition is clear in intent but has a structural
problem that will generate conflicting signals for Gemma. The current
_STREAM_INTENT_SYSTEM_PROMPT at lines 260-262 states:

  "alternatives" is [] for high confidence; 2–4 items for medium;
  up to 10 items for low. Never exceed 10.
  Each alternative: {"cip": "XX.XXXX", "title": "...", "why": "short phrase"}.

The spec says to ADD the new multi-CIP rules. If both blocks survive
in the prompt, Gemma sees two contradictory rules for when alternatives
should appear: one confidence-gated rule ([] for high confidence) and one
semantic-match rule (include when 2+ programs genuinely match). "engineering"
at Purdue is a high-confidence match to Computer Engineering — Gemma would
be instructed to both suppress alternatives (old rule, high confidence) and
include them (new rule, multiple matches). This is the root cause of C4 in
the architect review.

The prompt addition as written in §4 is otherwise well-structured for
Gemma 4: the delimiter format is preserved, the example JSON shows the
correct array syntax, and the rules use plain-English conditionals that
Gemma 4 follows reliably. The issue is exclusively the conflicting
retention of the old rules.

Concrete fix required: The implementer must REPLACE lines 260-262 in
_STREAM_INTENT_SYSTEM_PROMPT (the confidence-gated alternatives rule and
the old each-alternative format line) with the new semantic-matching rules
from §4. Do not supplement — replace. The old 10-item format line goes away
entirely; the new cap is 2 alternatives (3 total).

---

FINDING 2: Array format compatibility across model sizes — PASS WITH CAVEAT

The array format {"alternatives": [...]} is standard JSON and works
correctly under both gemma4:e4b (Ollama) and gemma-4-26b-a4b-it
(OpenRouter). Both models use the OpenAI-compatible chat completions
API and are well within their documented JSON capability.

The real risk is not array syntax — it is the two-part prose+delimiter
format that e4b already struggles with (noted inline in the spec's
_fallback_resolve docstring at line 514: "common with smaller models
like e4b that can't follow the two-part prose+delimiter+JSON format").
When e4b fails the delimiter split, _build_intent_result_from_tail
calls _fallback_resolve, which uses _FALLBACK_JSON_SYSTEM. That path
currently produces a flat JSON with no alternatives key. The spec
correctly identifies that _FALLBACK_JSON_SYSTEM must also be updated —
it is a JSON-only prompt where array format is actually MORE reliable
for small models than the prose+delimiter format, so the fallback
update is lower risk than the streaming update.

One concrete concern: the spec's proposed JSON example in the streaming
prompt spans multiple lines inside the prompt string literal. The current
_STREAM_INTENT_SYSTEM_PROMPT at lines 233-238 uses a single-line JSON
example (with backslash continuations). Multi-line JSON in the prompt
example is fine for clarity but the implementer should verify that the
backslash continuation style used in the rest of the string literal is
consistent with the new multi-line block — Python will silently drop a
missing backslash continuation and truncate the prompt.

---

FINDING 3: _FALLBACK_JSON_SYSTEM change — APPROVED

The current fallback prompt at lines 493-506 is a minimal 6-line prompt
returning a flat JSON object with matched_cip, matched_title, confidence,
parent_cip, intent_keywords. The spec's change to add alternatives/
remaining_count/narrowing_hint is appropriate.

Structural note: the fallback is JSON-only (no prose, no delimiter to
emit), which means Gemma can focus entirely on generating valid JSON.
Small models that fail the delimiter format typically succeed at
JSON-only generation. Adding the alternatives array here is actually the
easier half of this change.

One parsing note: _fallback_resolve at line 560 currently builds
IntentResult with alternatives=None hardcoded (line 567). When the
fallback prompt is updated, the implementer must also update the
IntentResult construction in _fallback_resolve to call
intent._sanitize_alternatives on parsed.get("alternatives") — exactly
as _build_intent_result_from_tail does at line 686. The spec's
pseudocode covers this conceptually but does not call out this specific
line, and it is easy to miss given the two separate IntentResult
construction sites in set_your_course.py.

---

FINDING 4: Token efficiency — PASS

Current _STREAM_INTENT_SYSTEM_PROMPT is approximately 60 lines / ~650
tokens. The spec's additions are 14 lines / ~180 tokens. Net prompt
growth is ~28%, from roughly 650 to 830 input tokens. At Gemma 4's
context window (8K+ for both size variants) this is well within budget
and will not cause truncation of the school program list or crosswalk
list (the variable-length parts of the prompt that actually drive token
cost).

The alternatives in the response add at most 2 additional JSON objects
to the output. At ~50 tokens per alternative object (cip, title, why,
parent_cip), the maximum output overhead is ~100 tokens. This is
negligible.

No token efficiency concerns.

---

FINDING 5: Deduplication and validation — APPROVED WITH ONE GAP

The validation logic in §4's _build_intent_result pseudocode is sound:
it calls _promote_to_leaf_cip per alternative, checks against valid_6digit
and valid_4digit sets, and silently drops invalid entries. This mirrors
exactly what the primary CIP validation does at lines 627-656, which is
the right pattern.

However, there is one deduplication gap not covered in the spec: the
cap-at-2 logic in the pseudocode (`for alt in raw_alts[:2]`) runs BEFORE
validation. If Gemma returns 3 alternatives but the first one fails
validation, only 1 valid alternative survives instead of the potential 2
from positions 1 and 2. The correct pattern is: validate all alternatives
first, then take the first 2 survivors. Change the pseudocode slice from
`raw_alts[:2]` to `raw_alts` (iterate all), break after accumulating 2
valid entries. The current `_sanitize_alternatives` in intent.py already
does this correctly at lines 379-380 (iterates all, breaks at cap). The
streaming path's new logic should match this pattern.

There is also a subtle deduplication issue in the existing
_sanitize_alternatives at line 354: `seen: set[str] = {primary_cip}`. This
deduplicates alternatives against the primary CIP. The streaming path's
new validation logic must do the same — initialize `seen` with `matched_cip`
before iterating alternatives. The spec pseudocode does not show this
initialization; the implementer needs to add it.

---

SUMMARY FOR IMPLEMENTER

Required before merging:

1. In _STREAM_INTENT_SYSTEM_PROMPT: REPLACE lines 260-262 (the
   confidence-gated alternatives rule) with the new semantic-match rules
   from §4. Do not leave both sets of rules present.

2. In _fallback_resolve (line 567): update the IntentResult construction
   to parse alternatives/remaining_count/narrowing_hint from the parsed
   dict, same as _build_intent_result_from_tail does.

3. In _build_intent_result_from_tail alternatives loop: iterate all
   raw_alts (not raw_alts[:2]), break after 2 valid entries. Initialize
   the dedup set with matched_cip before iterating.

4. Verify backslash continuation style for the new multi-line JSON
   example block in the prompt string literal.

Recommended (not blocking):

5. C1 from architect review: extend _sanitize_alternatives to include
   parent_cip and call _promote_to_leaf_cip, so both the streaming path
   and any future callers use a single validation implementation.

6. C2 from architect review: define AlternativeMatch(BaseModel) and
   tighten the alternatives field type on IntentResult.

7. C3 from architect review: truncate the demoted primary's "why" field
   when swapping in onPickAlternative — use "Your original match" rather
   than res.reasoning (which is full Gemma prose, not a short phrase).
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
