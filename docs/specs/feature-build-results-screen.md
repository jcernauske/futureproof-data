# Feature: Build Results Screen

## Claude Code Prompt

```
Read the spec at docs/specs/feature-build-results-screen.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, routing, state management, API integration)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes — gauntlet/skill APIs consumed as-is)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to propose the premium version of the Build Results screen
   - Visionary fills §3 with layout, interactions, Brightpath token usage, responsive behavior
   - Special focus: hero identity with avatar overlap, path+institution grid, pentagon+legend elevation card, sealed-reveal boss bands with VS overlay, victory bar verdict
   - Cross-reference DESIGN.md (source of truth) for tokens, typography, motion presets
   - §3 becomes the pixel-perfect implementation target

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code
   - Implement BuildResultsScreen as a single scrollable page
   - Reuse existing components: PentagonChart, useHorizonPick, HorizonPicture
   - Implement sealed-reveal boss bands with VS overlay, NOT expandable cards or sequential phases
   - Wire up reroll via existing rerollFight() API client
   - Use Brightpath design tokens exclusively — no hardcoded colors, spacing, or typography
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - BuildResultsScreen: renders all sections, nav guard, loading state, error state
   - Campus hero: random image renders, hero identity with avatar below banner
   - Boss bands: all 5 render, sealed-reveal triggers, VS overlay, result words correct
   - Reroll flow: skill selection, API call, result update, Gemma narrative refresh
   - Verdict badge: updates after reroll
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for Brightpath token compliance
   - Confirm: dark backgrounds, stat colors per DESIGN.md, correct fonts, token-only colors, responsive behavior, animation springs
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
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review
   - Generate report to reports/feature-build-results-screen-YYYY-MM-DD.md
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
| Created | 2026-04-21 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-21 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/screen-career-pick-reveal.md`, `docs/specs/completed/screen-boss-gauntlet.md`, `docs/specs/completed/feature-horizon-footer.md`, `docs/specs/feature-multi-cip-resolution.md` |

---

## §1 Feature Description

### Overview

Consolidate the current multi-screen post-selection flow (`/reveal` → `/gauntlet`) into a single scrollable Build Results screen at `/my-build`. The student picks their school, major, and career on SetYourCourseScreen, taps "Spec my build," and lands on one page that shows everything: campus hero banner with character identity, pentagon stats with plain-English explanations, all five boss fight results with inline reroll capability, and a verdict badge — ending with a save CTA.

### Problem Statement

The current flow requires navigating through 4+ separate screens (reveal → gauntlet → branches → save) after selecting a school and career. User feedback says there are too many screens and it takes too long to see the full picture. Students lose context switching between screens, and the sequential boss fight presentation (one-at-a-time with dramatic entrances) prioritizes spectacle over information density. For a hackathon demo and first-time student users, a single consolidated view delivers the "wow" moment faster.

### Success Criteria

- [ ] New route `/my-build` renders a single scrollable page with all build results
- [ ] Campus hero banner displays a rotating campus illustration (random on each load from 48 available in `frontend/public/campus/`) with 180px 3-stop gradient fade. Future: match illustration to selected school.
- [ ] Hero identity renders below banner with -48px overlap: 120px circular avatar with emoji-specific background color (EMOJI_BG lookup), character name at 40px Fredoka, subtitle at 18px weight 600. No salary pill in hero.
- [ ] "Your Path" card displays CIP program (emoji + title + code), SOC career (emoji + title + code + wage), and mini stat bars in 2-column grid
- [ ] "About the School" institution card displays school name, Gemma-written narrative, and "Written by Gemma" tag
- [ ] Path + institution cards render in a 2-column grid (`1fr 1.6fr`, collapses at 900px)
- [ ] Pentagon chart and stat legend render side-by-side in an elevation card wrapper with pentagon sticky on desktop
- [ ] Stat info popover system works (? buttons on each stat, inline popover with definition/source)
- [ ] Pentagon vertex glow animation fires on stat legend row hover
- [ ] All five boss fight results display as sealed-reveal boss bands with VS overlay animation
- [ ] Sealed state shows boss identity but hides result (desaturated portrait, "AWAITING" label, sealedPulse animation)
- [ ] VS overlay plays: player-vs-boss collision animation (96px portraits slam in, "VS" text, collision emoji, 5 dust puffs, boss-colored energy burst, 1200ms hold)
- [ ] Reveal queue processes one-at-a-time via center-third viewport trigger (`rootMargin '-33% 0px -33% 0px'`) with fast-scroll skip protection
- [ ] Result words display as VICTORY/DEFEATED/STANDOFF with micro-animations (winPulse, loseShake, drawWobble)
- [ ] Boss bands show dual edge stripes (left=boss color, right=result color) and result-tinted borders
- [ ] Reroll mechanic works inline: 3-column skill grid with EQUIPPED badge, skill-stat-badges with stat colors
- [ ] Reroll hides after success, tracks rescored state via `data-rescored` attribute
- [ ] Gemma narrative updates post-reroll to acknowledge skill impact
- [ ] Verdict section shows "CAREER READINESS" label with verdict words (DOMINANT BUILD/SOLID BUILD/MIXED BUILD/VULNERABLE BUILD) and subtitles
- [ ] Victory bar shows 5 cells (decisive=thrive, skill-assisted=insight, draw=caution at 40%, loss=bg-deep+border) with legend
- [ ] Verdict tally shows "X of 5 victories (Y decisive + Z skill-assisted)" with dynamic narrative
- [ ] Rescored wins shown as insight/purple in victory bar, not thrive/green
- [ ] "Save This Build" button navigates to `/save`
- [ ] SetYourCourseScreen "Spec my build" button navigates to `/my-build` instead of `/reveal`
- [ ] Navigation guard redirects to `/set-your-course` if session state is missing
- [ ] Screen works on both desktop and mobile viewports

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | New route `/my-build` instead of reusing `/reveal` | Clean break — old flow remains functional for backwards compat. No bookmark breakage. | Reuse `/reveal` (simpler routing but breaks existing links); `/build-results` (longer URL) |
| 2 | Sealed-reveal boss bands with VS overlay | Each boss starts sealed (identity visible, result hidden). When scrolled to center-third of viewport, a VS overlay plays (player vs boss collision), then reveals result. This preserves the dramatic tension of the gauntlet while keeping all 5 fights on one scrollable page. One-at-a-time reveal queue prevents overlap. Fast-scroll skip protection ensures no stuck states. | All 5 visible immediately (loses tension); Expandable cards (less cinematic); Sequential pages (current flow, rejected as too many screens) |
| 3 | Campus hero banner + hero identity below | Banner is the atmosphere shot; character identity sits below with -48px overlap and horizontal flex layout. No frosted-glass overlay on the banner itself — cleaner separation of concerns, and the identity section works better at different viewports. | Frosted-glass overlay centered on banner (fights busy illustration for legibility); No hero image (functional but cold) |
| 4 | Reroll inline within boss bands | Students can improve results without leaving context. 3-column skill grid with EQUIPPED badges and stat-colored skill badges. Reroll section hides after success. `data-rescored` attribute tracks which wins came from skills for victory bar coloring. | Separate reroll modal (more code, less inline); No rerolls on this screen (simplest but removes key interactive element) |
| 5 | POST `/build` on screen entry (same as current RevealScreen) | The build endpoint already pre-calculates gauntlet results server-side. No backend changes needed. | Separate API calls for stats vs. gauntlet (more network requests, more loading states) |
| 6 | Gemma narrative updates post-reroll | After a reroll, the narrative should acknowledge the skill impact to reinforce the student's action. Backend already returns new `narrative` field on reroll response. | Static narrative (doesn't acknowledge reroll — feels disconnected) |

### Constraints

- No backend changes — all APIs exist (`POST /build`, `POST /build/{id}/reroll`)
- Must follow Brightpath design system (dark-first, plush, cinematic)
- Campus images are 1400/2048px wide WebP/AVIF — landscape aspect ratio dictates hero banner proportions

### Out of Scope

- **Gemma-typed campus backgrounds** — Future: Gemma classifies college type (HBCU, Ivy League, Urban, etc.) and selects a campus image from a corresponding subdirectory. Requires new Gemma call + image directory restructuring.
- **Removing old `/reveal` + `/gauntlet` screens** — Leave as dead code for now. Clean up in a follow-up spec once the new flow is validated.
- **Branch tree integration** — The branch tree remains at `/branches` as a separate screen. No inline branch visualization on this screen.
- **Wrapped/share frames** — "Save This Build" navigates to `/save`, which handles wrapped frame rendering. No inline frame rendering on this screen.
- **StatTutorial overlay** — The existing first-time tutorial overlay on RevealScreen is not carried over. May revisit in a future spec.

---

## §3 UI/UX Design

> **@fp-design-visionary fills this section.** This is the pixel-perfect implementation target.
> **Canonical mockup:** `docs/mockups/build-results-screen.html`

**Status:** COMPLETE
**Author:** @fp-design-visionary
**Date:** 2026-04-21

---

### Emotional Target

The Build Results screen is a **trophy case**. The student just committed to a school, major, and career -- this is where we show them the full picture of that choice. The emotion sequence across the scroll is:

1. **Arrival** (Campus Hero + Hero Identity) -- Pride and belonging. "That's my campus. That's my character. I'm here."
2. **Context** (Your Path + Institution Background) -- Grounding and trust. "I can see exactly what I chose, and Gemma knows about my school."
3. **Understanding** (Pentagon + Stat Legend) -- Clarity and curiosity. "Oh, so THAT's what my stats mean."
4. **Tension and Relief** (Boss Bands) -- Playful stakes with dramatic reveal. "The seal breaks... VS... did I win?"
5. **Resolution** (Verdict + Victory Bar) -- Earned satisfaction. "I know where I stand."
6. **Ownership** (Save CTA) -- Agency. "I want to keep this."

The single-scroll page trades the old multi-screen forced pacing for **comprehension**. The student sees their entire build on one page, like a character sheet in a tabletop RPG. The spectacle lives in the scroll-triggered sealed-reveal animations on the boss bands, not in forced page transitions.

---

### Page Layout Architecture

The page uses a **content-column** pattern (NOT a 12-column grid). See mockup `.content-column` at lines 264-271.

```css
.content-column {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 16px;
}
@media (min-width: 768px) { .content-column { padding: 0 24px; } }
@media (min-width: 1200px) { .content-column { max-width: 1280px; padding: 0 32px; } }
```

The Campus Hero Banner is the one full-bleed element (no max-width). The Hero Identity and all subsequent sections live inside `.content-column`. The page background is `bg-deep` (#1B1D30) with the standard Brightpath layered radial gradient and noise texture.

**Scroll structure:** Single continuous scroll. Sections separated by `48px` vertical gaps on desktop (`margin-top: 48px`), `32px` on mobile. First section below hero identity uses `32px` gap (desktop) / `24px` (mobile). See mockup `.section` at lines 273-276.

---

### Section 1: Campus Hero Banner + Hero Identity

**What it is:** Two-part arrival moment. The banner is a full-bleed panoramic campus illustration with a tall gradient fade. The hero identity sits *below* the banner (not overlaid on it) with a -48px negative margin overlap, showing a circular avatar with the character emoji and the character name/subtitle beside it in a horizontal flex layout.

**Why this changed from the earlier frosted-glass overlay:** The overlay approach fights busy campus illustrations for legibility. Separating the banner (atmosphere) from the identity (data) gives each room to breathe. The -48px overlap creates visual continuity without collision.

**How it feels:** Like the title card of a Pixar movie -- establishing shot, then the character steps forward.

#### Desktop Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   [Full-bleed campus illustration, 280px tall]                          │
│   Night-themed cartoon campus panorama from /campus/ pool               │
│                                                                         │
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
│  ← gradient fade 180px, 3-stop: transparent → rgba(27,29,48,0.5) → #1B │
└─────────────────────────────────────────────────────────────────────────┘
 ┌──────┐
 │ 🐢   │  Snappy Purple Turtle
 │(120px)│  Studying Computer Science at Illinois State University
 └──────┘
   ↑ -48px overlap into banner
```

#### Banner Specifications

See mockup `.campus-hero` at lines 170-197.

| Property | Value | Token / Class |
|----------|-------|---------------|
| Container height | 280px desktop, 200px mobile | See mockup line 178 |
| Container width | Full viewport bleed | `w-full` (no max-width) |
| Container position | `relative`, `overflow-hidden` | |
| Image display | `<picture>` with AVIF/WebP, same pattern as `HorizonPicture` | |
| Image selection | **Rotating on load**: pick a random illustration from the 48 sets in `frontend/public/campus/`. Each set has 1400px + 2048px in WebP + AVIF. Use `Math.random()` index at component mount. Future: match to selected school. | See `getCampusImages()` utility |
| Image fit | `object-cover object-[center_40%]` | Vertically centers on building tops |
| Bottom gradient | **180px** 3-stop linear gradient | See mockup `.gradient-fade` lines 188-197: `transparent 0%, rgba(27,29,48,0.5) 35%, #1B1D30 100%` |
| Animation | `heroFadeIn` 0.8s ease-out | See mockup line 1560 |

#### Hero Identity Specifications

See mockup `.hero-identity` at lines 199-261 and `.character-avatar`, `.character-text`, `.character-name`, `.character-subtitle`.

| Property | Value | Token / Class |
|----------|-------|---------------|
| Container | Horizontal flex below banner | `position: relative; z-index: 2; max-width: 1280px; margin: -48px auto 0; padding: 0 32px; display: flex; align-items: center; gap: 24px` |
| Avatar size | 120px circle (80px mobile) | `.character-avatar` lines 212-225 |
| Avatar background | **Emoji-specific color** from EMOJI_BG lookup | See mockup JS at lines 1816-1834. Maps emoji to accent token (e.g. turtle=`accent-info`, bear=`accent-caution`, fox=`accent-insight`) |
| Avatar border | `2px solid border-default` | |
| Avatar glow | `0 0 30px 6px rgba(125,212,163,0.15), 0 0 60px 12px rgba(184,169,232,0.08)` | |
| Emoji size | 80px (40px mobile) | `.character-emoji` line 228 |
| Name | `font-display` (Fredoka), weight 700, **40px** (28px mobile), `text-primary` | `.character-name` lines 238-245 |
| Subtitle | `font-body` (Nunito), weight **600**, **18px** (16px mobile), `text-secondary` | `.character-subtitle` lines 246-254. Format: "Studying {major} at {school}" |
| **No salary pill** | Salary does not appear in the hero identity | Salary appears in the path card instead |

**EMOJI_BG lookup table** (see mockup JS lines 1816-1825):

| Emoji | Background Color |
|-------|-----------------|
| Bear | `accent-caution` (yellow) |
| Bunny | `accent-insight` (purple) |
| Turtle | `accent-info` (blue) |
| Chipmunk | `accent-thrive` (green) |
| Fox | `accent-insight` (purple) |
| Owl | `accent-caution` (yellow) |
| Penguin | `accent-info` (blue) |
| Cat | `accent-alert` (coral) |

#### Animation Sequence

| Step | Delay | Property | Detail |
|------|-------|----------|--------|
| 1. Campus image | 0ms | opacity 0 to 1 | `heroFadeIn` 0.8s ease-out (mockup line 1560) |
| 2. Hero identity container | 300ms | `simpleFade` 0.3s ease-out | Mockup line 209 |
| 3. Avatar emoji | 500ms | scale 0.8 to 1, opacity 0 to 1 | `emojiBounce` cubic-bezier(0.34, 1.56, 0.64, 1) (mockup line 1562) |
| 4. Character name | 650ms | opacity 0, y: 8 to visible | `fadeInUp` 0.4s ease-out (mockup line 244) |
| 5. Subtitle | 750ms | `simpleFade` 0.3s ease-out | Mockup line 253 |

#### Accessibility

- Banner container: `role="img"`, `aria-label="Campus atmosphere"` (see mockup line 1626)
- Campus image: `role="presentation"`, `alt=""` (decorative)

---

### Section 2: Your Path + Institution Background

**What it is:** A two-column grid inserted between the hero identity and the stats section. Left column: "Your Path" card showing the CIP program and SOC career with mini stat bars. Right column: "About the School" institution card with a Gemma-written narrative about the school.

**Why it exists:** The old flow jumped straight from the hero to the pentagon. Students had no context about what they actually picked -- the CIP code, the SOC code, the wage. This section grounds the build in concrete facts before the abstract stats appear. The institution narrative (written by Gemma) adds warmth and credibility -- it says "we know about your school, specifically."

See mockup `.path-institution-grid` at lines 306-316.

#### Desktop Wireframe

```
┌──────────────────────────┬─────────────────────────────────────────┐
│  YOUR PATH               │  ABOUT THE SCHOOL                       │
│                          │                                          │
│  🎓 Computer Science     │  Illinois State University               │
│     CIP 11.0701          │                                          │
│                          │  Illinois State University is a public    │
│  💻 Software Developers  │  research institution in Normal,         │
│     SOC 15-1252          │  Illinois, founded in 1857...             │
│     $127,260 / yr        │                                          │
│                          │  The Computer Science program lives in    │
│  ERN ████░░  8           │  the School of Information Technology...  │
│  ROI ███░░░  6           │                                          │
│  RES ███░░░  7           │  ✦ Written by Gemma                      │
│  GRW █████░  9           │                                          │
│  HMN ██░░░░  5           │                                          │
└──────────────────────────┴─────────────────────────────────────────┘
```

#### Grid Specifications

| Property | Value | Reference |
|----------|-------|-----------|
| Grid | `grid-template-columns: 1fr 1.6fr; gap: 24px; align-items: start` | Mockup `.path-institution-grid` lines 307-311 |
| Collapse | Single column at 900px | Mockup line 312-316 |

#### Path Card Specifications

See mockup `.path-card` at lines 319-414.

| Property | Value |
|----------|-------|
| Background | `bg-mid` (#232545) |
| Border | `1px solid border-subtle` |
| Radius | `radius-xl` (20px) |
| Padding | 24px |
| Label | "Your Path" -- section label pattern (`font-data`, 11px, weight 700, `letter-spacing: 2px`, uppercase, `accent-info`) |
| Program entry | Emoji (28px) + title (`font-display`, 16px, weight 600) + CIP code (`font-data`, 11px, `text-muted`) |
| Career entry | Emoji (28px) + title + SOC code + wage (`font-data`, 14px, weight 700, `stat-ern` color) |
| Entry divider | `border-bottom: 1px solid border-subtle` between entries |
| Stat bars | 2-column grid (`1fr 1fr`, collapses to 1 column at 480px), `gap: 6px 16px`, separated from entries by `border-top` + 16px padding-top |

**Stat bar row** (see mockup `.stat-bar-row` at lines 382-414):

| Property | Value |
|----------|-------|
| Layout | `display: flex; align-items: center; gap: 8px` |
| Label | `font-data`, 11px, weight 700, uppercase, stat color, `width: 28px` |
| Track | `flex: 1; height: 4px; border-radius: full; background: bg-deep` |
| Fill | stat color, `opacity: 0.8`, width = `(value/10)*100%`, animated via `transition: width 0.4s ease-out` |
| Value | `font-data`, 11px, `text-secondary`, `width: 16px; text-align: right` |

#### Institution Card Specifications

See mockup `.institution-card` at lines 417-458.

| Property | Value |
|----------|-------|
| Background | `bg-mid` (#232545) |
| Border | `1px solid border-subtle` |
| Radius | `radius-xl` (20px) |
| Padding | 24px |
| Label | "About the School" -- section label pattern |
| School name | `font-display`, 22px, weight 700, `text-primary` |
| Narrative | `font-body`, 15px, `line-height: 1.65`, `text-secondary`. Paragraphs separated by 12px margin-bottom |
| Gemma tag | `font-data`, 11px, `text-muted`, `letter-spacing: 0.5px`, with `✦` glyph prefix. Reads "✦ Written by Gemma" |

#### Animation

Entire grid fades in with `sectionFadeIn` (0.5s, `animation-delay: 0.2s`). See mockup line 1649.

---

### Section 3: Build Stats (Pentagon + Stat Legend)

**What it is:** The pentagon chart and stat legend rendered **side-by-side** inside a single elevation card wrapper. The pentagon is sticky on desktop so it stays visible as the student scrolls through the legend rows. Each legend row has a ? button that opens an inline stat info popover with the stat definition and data source.

**Why this replaces the old separate Pentagon + StatExplainerCard sections:** The old design had the pentagon above and five separate horizontal stat cards below. That created a disconnect -- you could not see the pentagon while reading about a stat. The side-by-side layout keeps the shape visible as context while the legend explains each axis. The sticky pentagon means it follows you down the page. The popover system replaces the old source text that was always visible (visual clutter) with on-demand detail.

See mockup `.pentagon-section` at lines 461-477.

#### Desktop Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Build Stats                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────┐  ┌──────────────────────────────────────────┐   │  │
│  │  │   Pentagon    │  │  ● ERN  Earning Power         [?]  8/10 │   │  │
│  │  │   (320x320)   │  │  Brief explanation of ERN score...       │   │  │
│  │  │   Sticky on   │  │  ──────────────────────────────────────  │   │  │
│  │  │   desktop at  │  │  ● ROI  Return on Investment  [?]  6/10 │   │  │
│  │  │   50vh-160px  │  │  Brief explanation of ROI score...       │   │  │
│  │  │              │  │  ──────────────────────────────────────  │   │  │
│  │  │              │  │  ● RES  AI Resilience          [?]  7/10 │   │  │
│  │  │              │  │  Brief explanation of RES score...       │   │  │
│  │  │              │  │  ──────────────────────────────────────  │   │  │
│  │  │              │  │  ● GRW  Growth Potential       [?]  9/10 │   │  │
│  │  │              │  │  Brief explanation of GRW score...       │   │  │
│  │  │              │  │  ──────────────────────────────────────  │   │  │
│  │  │              │  │  ● HMN  Human Edge             [?]  5/10 │   │  │
│  │  │              │  │  Brief explanation of HMN score...       │   │  │
│  │  └──────────────┘  └──────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Elevation Card Wrapper

See mockup `.elevation-card` at lines 297-303.

| Property | Value |
|----------|-------|
| Background | `bg-mid` (#232545) |
| Border | `1px solid border-subtle` |
| Radius | `radius-xl` (20px) |
| Padding | 32px (20px mobile) |

#### Pentagon Specifications

See mockup `.pentagon-chart` at lines 468-472.

| Property | Value |
|----------|-------|
| SVG size | 320x320 viewBox (see mockup line 1696) |
| Position | `position: sticky; top: calc(50vh - 160px); align-self: flex-start` on desktop |
| Position (mobile) | `position: static` (stacks above legend) |
| Flex layout | Pentagon and legend side by side: `display: flex; gap: 48px; align-items: flex-start; flex-wrap: wrap` |
| Legend | `flex: 1; min-width: 240px` |

**Component reuse:** Reuse `PentagonChart` with `animated={true}`, `delay={0.3}`.

#### Stat Legend Row

See mockup `.stat-row` at lines 480-531.

| Property | Value |
|----------|-------|
| Layout | `display: flex; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px solid border-subtle` |
| Hover | `background: rgba(255,255,255,0.04); border-radius: 8px; padding: 14px 12px; margin: 0 -12px` |
| Stat dot | 12px circle, stat color background |
| Stat abbreviation | `font-data`, 12px, `text-muted`, `width: 32px` |
| Stat name | `font-display`, weight 600, 15px, `text-primary` |
| Stat explanation | `font-body`, 13px, `line-height: 1.5`, `text-secondary`, `margin-top: 4px` |
| Score value | `font-data`, weight 700, 18px, stat color. Denominator: 13px, weight 400, opacity 0.45 |

#### Pentagon Vertex Glow on Hover

See mockup `vertex-glow-pulse` keyframe at lines 499-503 and JS at lines 1970-1976.

When a stat legend row is hovered, the corresponding vertex glow circle on the pentagon SVG gains the `vertex-glow-active` class, animating `r` from 10 to 18 and `opacity` from 0.2 to 0.5 over 0.8s ease-in-out infinite.

#### Stat Info Popover System

See mockup `.stat-info-trigger`, `.stat-info-popover` at lines 534-616 and JS at lines 1979-2034.

**Trigger button:**

| Property | Value |
|----------|-------|
| Size | 18x18px circle |
| Border | `1.5px solid border-default` |
| Content | "?" character, `font-body`, 11px, weight 700 |
| Default state | `opacity: 0.6` |
| Hover | `opacity: 1; border-color: border-strong; background: rgba(255,255,255,0.04)` |
| Expanded state | `border-color: accent-info; color: accent-info; background: rgba(123,184,224,0.08)` |
| ARIA | `aria-expanded`, `aria-controls="info-{stat}"`, `aria-label="What is {StatName}?"` |

**Popover:**

| Property | Value |
|----------|-------|
| Position | Inline below the stat name row (relative, not absolute) |
| Background | `bg-raised` (#3A3D75) |
| Border | `1px solid border-default` + `3px left border` in stat color (via `--popover-accent` CSS variable) |
| Radius | `radius-lg` (14px) |
| Padding | 20px |
| Shadow | `shadow-lg` |
| Enter animation | `popoverIn` 180ms cubic-bezier(0.34, 1.4, 0.64, 1): translateY(-6px) to 0 with opacity |
| Exit animation | `popoverOut` 150ms ease-in: reverse of enter |
| Title | `font-display`, 14px, weight 600, `text-primary` |
| Body | `font-body`, 14px, `line-height: 1.5`, `text-secondary` |
| Source | `font-data`, 11px, `text-muted`, `letter-spacing: 0.5px`, `margin-top: 10px` |

**Behavior:** Only one popover open at a time. Clicking a ? button while another is open closes the old one first. Clicking anywhere else on the page or pressing Escape closes the active popover.

**Stat definitions** (see mockup JS lines 1979-1985):

| Stat | Definition | Source |
|------|-----------|--------|
| ERN | Measures how your expected salary compares to graduates from similar programs nationally, based on median earnings 1 and 4 years after graduation. | College Scorecard |
| ROI | Compares what you'll earn against what you'll owe. Factors in tuition, typical debt load, and expected starting salary to estimate how quickly the degree pays for itself. | College Scorecard |
| RES | Estimates how resistant this career is to AI automation, based on task-level analysis of which job activities current AI systems can perform. | Karpathy AI Exposure Index |
| GRW | Projects how fast this occupation is expected to add jobs over the next decade, relative to the national average across all occupations. | BLS Occupational Outlook Handbook |
| HMN | Measures how much of this job relies on interpersonal skills, empathy, creativity, and other distinctly human capabilities that AI struggles to replicate. | O*NET Work Context |

#### Section Heading

| Property | Value |
|----------|-------|
| Text | "Build Stats" |
| Font | `font-display`, weight 700, 32px (26px mobile), `text-primary` |

#### Animation

Section fades in with `sectionFadeIn` (0.5s, `animation-delay: 0.4s`). See mockup line 1691.

---

### Section 4: Boss Fight Results (The Gauntlet)

**What it is:** Five boss fight bands displayed in a vertical stack with 48px gap and `scroll-snap-type: y proximity`. Each boss band starts in a **sealed state** (boss identity visible, result hidden). When the student scrolls a band into the center third of the viewport, a **VS overlay** plays (player portrait slams in from left, boss from right, collision emoji, dust puffs, energy burst), then the seal breaks to reveal the result with micro-animations.

**Why this replaces the old expandable card approach:** The expandable card approach (collapsed by default, click to expand) was information-dense but emotionally flat. The sealed-reveal system preserves the dramatic tension of the original gauntlet ("did I win?") while keeping all five fights on one scrollable page. The student controls the pacing by scrolling, and the one-at-a-time reveal queue prevents animation overlap. Fast-scroll skip protection ensures no stuck states.

**How it feels:** Like scrolling through a battle report in a game where each encounter unseals as you reach it. The VS collision is the moment of impact. The result reveal is the payoff. You never wait -- if you scroll fast, the animations skip gracefully.

See mockup `.boss-bands` at lines 628-633 and `renderBossBands()` JS at lines 2053-2149.

#### Desktop Wireframe (After Reveal)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  The Gauntlet                                                           │
│  5 fights. Your stats vs. real-world threats.                           │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  ┃  🤖  Snappy vs. AI                              VICTORY          ┃  │
│  ┃      How safe is this career from automation?    Your stats held  ┃  │
│  ┃                                                                    ┃  │
│  ┃  ┌──────────────────────────────────────────────────────────────┐ ┃  │
│  ┃  │ ┃ Software development scores well against AI automation... │ ┃  │
│  ┃  └──────────────────────────────────────────────────────────────┘ ┃  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  ┃  💸  Snappy vs. Student Loans                    DEFEATED         ┃  │
│  ┃      Can your earnings handle the debt?          This one got you ┃  │
│  ┃      ┌─────────────────┐                                          ┃  │
│  ┃      │ 3 skills avail. │                                          ┃  │
│  ┃      └─────────────────┘                                          ┃  │
│  ┃  ┌──────────────────────────────────────────────────────────────┐ ┃  │
│  ┃  │ ┃ Your debt-to-earnings ratio is 1.8x...                    │ ┃  │
│  ┃  └──────────────────────────────────────────────────────────────┘ ┃  │
│  ┃  ┌──────────────────────────────────────────────────────────────┐ ┃  │
│  ┃  │  Equip Skills                                                │ ┃  │
│  ┃  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐   │ ┃  │
│  ┃  │  │ Part-time Work │ │ Scholarship    │ │ Financial Lit. │   │ ┃  │
│  ┃  │  │ ERN +1  ROI +2 │ │ ROI +2         │ │ ROI +1         │   │ ┃  │
│  ┃  │  │     EQUIPPED   │ │                │ │                │   │ ┃  │
│  ┃  │  └────────────────┘ └────────────────┘ └────────────────┘   │ ┃  │
│  ┃  │                                                              │ ┃  │
│  ┃  │  [Accept Result]                   [Rescore Fight ✦]        │ ┃  │
│  ┃  │                                    Attempt 1/3               │ ┃  │
│  ┃  └──────────────────────────────────────────────────────────────┘ ┃  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 ...                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Section Heading

| Property | Value |
|----------|-------|
| Heading | "The Gauntlet" -- `font-display`, 32px, weight 700, `text-primary` |
| Subtitle | "5 fights. Your stats vs. real-world threats." -- `font-body`, 16px, `text-secondary`, `margin-top: 4px` |

See mockup `.gauntlet-intro`, `.gauntlet-subtitle` at lines 619-627.

#### Boss Band Container

See mockup `.boss-bands` at lines 628-633.

| Property | Value |
|----------|-------|
| Layout | `display: flex; flex-direction: column; gap: 48px` |
| Scroll snap | `scroll-snap-type: y proximity` |
| Each band | `scroll-snap-align: center` |

#### Boss Band Card

See mockup `.boss-band` at lines 636-647.

| Property | Value |
|----------|-------|
| Background | `bg-mid` (#232545) |
| Radius | `radius-xl` (20px) |
| Padding | 24px (18px mobile) |
| Overflow | hidden |
| Min height | 140px |
| Data attributes | `data-boss="{bossId}"`, `data-result="{win|lose|draw}"` |

#### Sealed State

See mockup `.sealed-overlay` at lines 661-721 and `.sealed-shimmer` at lines 724-747.

Before the center-third viewport trigger fires, each boss band displays a **sealed overlay** that covers the actual content:

| Element | Specification |
|---------|--------------|
| Sealed overlay | Absolute positioned over entire card. Shows: desaturated boss portrait (64px, `filter: saturate(0.3) brightness(0.7)`), boss name in `text-secondary`, boss subtitle in `text-muted`, and "AWAITING" status label (`font-data`, 11px, weight 700, `letter-spacing: 1.5px`, uppercase, `text-muted`, `opacity: 0.6`) |
| Sealed pulse | Boss portrait pulses opacity between 0.7 and 0.85 on a 2s ease-in-out infinite loop (`sealedPulse` keyframe, mockup lines 695-698) |
| Sealed shimmer | When the card enters the viewport edge (visibility observer, `threshold: 0.1`), a shimmer sweep plays across the card: `linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 45%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.05) 55%, transparent 100%)` translating from -100% to 200% over 0.6s. See mockup lines 740-747 |
| Hold beat | Before VS fires, the card scales to `1.02` for 200ms (`sealed-hold` class, mockup lines 750-762) |
| Pre-trigger border | `1px solid border-subtle` (neutral, no colored stripes visible) |

Boss portrait gradient backgrounds per boss (see mockup lines 690-694):
- AI: `linear-gradient(135deg, rgba(184,169,232,0.30) 0%, rgba(184,169,232,0.12) 100%)`
- Loans: `linear-gradient(135deg, rgba(244,169,126,0.30) 0%, rgba(244,169,126,0.12) 100%)`
- Market: `linear-gradient(135deg, rgba(123,184,224,0.30) 0%, rgba(123,184,224,0.12) 100%)`
- Burnout: `linear-gradient(135deg, rgba(232,139,169,0.30) 0%, rgba(232,139,169,0.12) 100%)`
- Ceiling: `linear-gradient(135deg, rgba(196,191,176,0.30) 0%, rgba(196,191,176,0.12) 100%)`

#### VS Overlay

See mockup `.vs-overlay` at lines 949-1143 and `playVS()` JS at lines 2156-2189.

When the center-third observer fires (`rootMargin: '-33% 0px -33% 0px'`, `threshold: 0.5`), the VS overlay plays:

| Phase | Timing | What Happens |
|-------|--------|-------------|
| 1. Hold beat | 0ms | Card gains `sealed-hold` class, scales to 1.02 |
| 2. VS overlay appears | 200ms | `sealed-triggered` + `vs-active` classes added. Sealed overlay fades out (`opacity: 0`). VS overlay fades in (`opacity: 1`) |
| 3. Player portrait slams in | 200ms | From `translateX(-40px) scale(0.6)` to `translateX(0) scale(1)` with cubic-bezier(0.34, 1.56, 0.64, 1) |
| 4. Boss portrait slams in | 230ms | Same animation, 30ms delay |
| 5. "VS" text appears | 300ms | scale 0.8 to 1, opacity 0 to 1 |
| 6. Collision emoji | 380ms | `collisionSlam` keyframe: scale 0 to 1.3 to 1.0 to 0.6 with fade |
| 7. Dust puffs (5x) | 450-550ms | Each puff drifts in a different direction, grows and fades. See mockup `dustPuff1`-`dustPuff5` keyframes at lines 1052-1056 |
| 8. Energy burst | 500ms | Boss-colored radial gradient (120px circle) scales from 0 to 2.5 with fade. See mockup `vsBurst` at lines 1114-1118 |
| 9. VS overlay fades out | 1200ms | `vs-done` class: overlay `opacity: 0` over 120ms |
| 10. Content reveals | 1350ms | `revealed` class: portrait, info, result zone, narrative, and reroll section all transition in with staggered delays (0ms, 80ms, 180ms, 320ms, 460ms) |
| 11. Result micro-animation | 1600ms | `winPulse` / `loseShake` / `drawWobble` fires 250ms after reveal |

**VS overlay layout:**
- 96px player portrait (left) + "VS" text + collision emoji (center) + 96px boss portrait (right)
- 72px portraits on mobile
- Player name and boss shortName below portraits (`font-body`, weight 600, 13px, `text-secondary`)
- Background: `bg-void` (#12131F)

See mockup `.vs-portrait` at lines 973-996.

**Player portrait:** Uses `accent-info` gradient background (same as existing player color).

#### Reveal Queue

See mockup `initGauntletReveals()` JS at lines 2151-2268.

| Behavior | Implementation |
|----------|---------------|
| One-at-a-time | `currentlyAnimating` tracks the active band. New triggers are pushed to `pendingQueue`. When current finishes, next in queue starts |
| Center-third trigger | `IntersectionObserver` with `threshold: 0.5` and `rootMargin: '-33% 0px -33% 0px'` |
| Fast-scroll skip | If a band leaves the center-third while still animating (`vs-active` or `sealed-hold` but NOT `revealed`), it immediately skips to the revealed state via `skipToRevealed()`. All timeouts are cleared, classes are set directly |
| Visibility shimmer | Separate observer (`threshold: 0.1`, `rootMargin: '0px'`) adds `sealed-visible` class to trigger the shimmer sweep when a card first enters viewport edge |

#### Dual Edge Stripes

See mockup lines 789-816.

| Stripe | Position | Color |
|--------|----------|-------|
| Left stripe (boss color) | `left: 0; width: 4px; border-radius: xl 0 0 xl` | Boss-colored linear gradient from 70% opacity (top) to 15% opacity (bottom) |
| Right stripe (result color) | `right: 0; width: 4px; border-radius: 0 xl xl 0` | Result-colored gradient + `box-shadow: -8px 0 24px` inward glow |

Result colors for right stripe:
- Win: `rgba(125,212,163,...)` (thrive)
- Lose: `rgba(244,169,126,...)` (alert)
- Draw: `rgba(242,212,119,...)` (caution)

Stripes are hidden (`opacity: 0`) before trigger, visible only after `sealed-triggered` class is added.

#### Result-Tinted Borders and Hover Glow

See mockup lines 774-787.

After reveal, the card border changes based on result:
- Win: `1px solid rgba(125,212,163,0.18)`
- Lose: `1px solid rgba(244,169,126,0.20)`
- Draw: `1px solid rgba(242,212,119,0.18)`

On hover after reveal:
- Win: `box-shadow: 0 8px 32px rgba(27,29,48,0.5), 0 0 24px rgba(125,212,163,0.10)`
- Lose: `box-shadow: ... rgba(244,169,126,0.10)`
- Draw: `box-shadow: ... rgba(242,212,119,0.10)`

#### Result Display

See mockup `.result-zone`, `.result-word`, `.result-flavor` at lines 897-925.

| Property | Value |
|----------|-------|
| Result words | **VICTORY** (win), **DEFEATED** (lose), **STANDOFF** (draw) -- NOT "WIN"/"LOSE"/"DRAW" pills |
| Result font | `font-display`, weight 700, 22px, uppercase, `letter-spacing: 1px` |
| Win color | `accent-thrive` + `text-shadow: 0 0 20px rgba(125,212,163,0.3)` |
| Lose color | `accent-alert` + `text-shadow: 0 0 20px rgba(244,169,126,0.25)` |
| Draw color | `accent-caution` + `text-shadow: 0 0 20px rgba(242,212,119,0.25)` |
| Flavor text | Below result word: "Your stats held strong" (win), "This one got you" (lose), "A narrow escape" (draw). `font-body`, 12px, `text-muted` |

#### Result Micro-Animations

See mockup keyframes at lines 928-947.

| Animation | Applied To | Keyframes |
|-----------|-----------|-----------|
| `winPulse` | Card (`box-shadow`) | 0% transparent → 50% `0 0 32px rgba(125,212,163,0.25)` → 100% transparent. 0.6s ease-in-out |
| `loseShake` | `.result-word` element | X translations: 0 → -3px → 3px → -2px → 1px → 0. 0.4s ease-in-out |
| `drawWobble` | `.result-word` element | Rotations: 0 → 1.5deg → -1.5deg → 0. 0.4s ease-in-out |

#### Boss Header Row

See mockup `.boss-header` at lines 853-859.

| Property | Value |
|----------|-------|
| Layout | `display: flex; align-items: center; gap: 16px; position: relative; z-index: 1` |
| Boss portrait | 64px (52px mobile), rounded `radius-lg`, boss-colored gradient background + 1px border + `0 0 20px` glow. See mockup `.boss-portrait` at lines 862-882 |
| Boss name | `font-display`, weight 600, 20px, boss color. **Format: "{PlayerFirstName} vs. {Boss}"**. Uses `PLAYER.name.split(' ')[0]` for the first name |
| Boss subtitle | 14px, `text-muted`, `margin-top: 2px` |
| Skill count badge | For lose/draw fights: `font-data`, 11px, weight 700, `accent-thrive` color, `rgba(125,212,163,0.12)` background, `radius-full` pill. Shows "{N} skill(s) available". See mockup `.skill-count-badge` at lines 1248-1258 |
| Result zone | Right-aligned, flex-shrink 0 |

#### Narrative Panel

See mockup `.narrative-panel` at lines 1146-1162.

| Property | Value |
|----------|-------|
| Background | `rgba(27,29,48,0.6)` |
| Border-left | `3px solid` in boss color (per `data-boss` attribute) |
| Radius | `radius-lg` (14px) |
| Padding | 20px |
| Margin-top | 16px |
| Text | `font-body`, 15px, `text-primary`, `line-height: 1.65` |

#### Reroll Section

See mockup `.reroll-section` at lines 1165-1309.

| Property | Value |
|----------|-------|
| Container | `margin-top: 16px; padding: 16px; background: rgba(45,48,96,0.35); border-radius: radius-lg; border: 1px solid border-subtle` |
| Header | "Equip Skills" -- `font-display`, weight 600, 15px, `text-secondary`, `margin-bottom: 12px` |
| Skill grid | **3-column grid** (`grid-template-columns: repeat(3, 1fr); gap: 10px`). Collapses to 2 columns at 680px, 1 column at 440px. See mockup `.skill-grid` at lines 1179-1185 |

**Skill card** (see mockup `.skill-card` at lines 1186-1231):

| Property | Value |
|----------|-------|
| Background | `bg-mid` (#232545) |
| Border | `1px solid border-default` |
| Radius | `radius-lg` (14px) |
| Padding | `12px 14px` |
| Min-height | 72px |
| Hover | `border-color: border-strong; background: rgba(45,48,96,0.5); transform: translateY(-1px)` |
| Selected state | `border-color: rgba(125,212,163,0.5); background: rgba(125,212,163,0.06); box-shadow: 0 0 16px rgba(125,212,163,0.12), inset 0 0 12px rgba(125,212,163,0.04)` |
| **EQUIPPED badge** | When selected: `::after` pseudo-element, absolute top-right, `font-data`, 10px, weight 700, `accent-thrive` color, `rgba(125,212,163,0.15)` background, `radius-full` pill. Text: "EQUIPPED" |
| Skill title | `font-display`, weight 600, 14px, `text-primary`, `padding-right: 60px` (room for EQUIPPED badge) |

**Skill stat badges** (see mockup `.skill-stat-badge` at lines 1237-1245):

| Property | Value |
|----------|-------|
| Font | `font-data`, 11px, weight 700, `letter-spacing: 0.3px` |
| Padding | `2px 8px` |
| Radius | `radius-full` |
| Color | **Stat-specific**: uses `STAT_COLORS` lookup (e.g. ERN badge = `#F2D477` text on `rgba(242,212,119,0.15)` background) |
| Layout | `display: flex; flex-wrap: wrap; gap: 6px` |

**Reroll actions** (see mockup `.reroll-actions` at lines 1259-1265):

| Property | Value |
|----------|-------|
| Layout | `display: flex; align-items: center; justify-content: space-between; margin-top: 14px; gap: 12px` |
| "Accept Result" | Ghost button (left-aligned) |
| "Rescore Fight" | Primary button with ✦ glyph, disabled when no skills selected |
| Attempt counter | `font-data`, 12px, `text-muted`, right-aligned, `margin-top: 8px`. Format: "Attempt 1/3" |

**Reroll success behavior** (see mockup `rescoreFight()` JS at lines 2295-2333):

1. Button shows loading spinner + "Rescoring..." text, disabled
2. Narrative panel dims to 60% opacity
3. After 1500ms simulated API call:
   - Result word updates to "VICTORY" with win color
   - Flavor text updates to "Your stats held strong"
   - `data-result` attribute changes to "win"
   - Narrative text cross-fades to updated content
   - Reroll section fades out (`opacity: 0; transform: translateY(-8px)`) then `display: none` after 300ms
   - **`data-rescored="true"` attribute set on the band** -- this is how the verdict tracks skill-assisted wins
   - `thriveGlowPulse` animation plays on the card (0.8s)
   - `updateVerdict()` called to recalculate and re-render the verdict

#### Accessibility

- Each boss band: `role="region"`, `aria-label` with boss name and result
- Result word: communicates result semantically
- Skill cards: `cursor: pointer`, `user-select: none`
- Reroll button: `aria-label="Rescore fight with equipped skills"`

---

### Section 5: Verdict Badge

**What it is:** A full-width verdict card showing the overall gauntlet result with a "CAREER READINESS" label, verdict word with subtitle, a 5-cell victory bar, a victory legend, a tally line, and a dynamic narrative.

**Why this replaces the old star-flanked verdict:** The old design used decorative star glyphs and a simple tally string. The new design adds a victory bar that visually shows *how* you won (decisive vs. skill-assisted) and a narrative that changes based on the win composition. The `data-rescored` attribute tracking means rescored wins show as purple/insight in the victory bar, not green/thrive -- this distinguishes "you had this" from "you built this."

See mockup `.verdict-section` at lines 1319-1451 and `updateVerdict()` JS at lines 2342-2421.

#### Desktop Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                     CAREER READINESS                              │  │
│  │                                                                    │  │
│  │                      SOLID BUILD                                  │  │
│  │                  Strong across the board                          │  │
│  │                                                                    │  │
│  │              ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐                  │  │
│  │              │████│ │████│ │████│ │░░░░│ │    │                  │  │
│  │              │grn │ │grn │ │grn │ │ylw │ │ bg │                  │  │
│  │              └────┘ └────┘ └────┘ └────┘ └────┘                  │  │
│  │                                                                    │  │
│  │               ● Decisive   ● Skill-assisted   ● Unresolved       │  │
│  │                                                                    │  │
│  │                     3 of 5 victories                               │  │
│  │                                                                    │  │
│  │          You won 3 fights decisively. The remaining               │  │
│  │          challenges might be worth exploring — equip               │  │
│  │          skills above to see what's possible.                     │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Verdict Badge Specifications

See mockup `.verdict-badge` at lines 1323-1348.

| Property | Value |
|----------|-------|
| Container | Full width (not max-width 400px like old spec), `text-align: center` |
| Background | `bg-mid` (#232545) |
| Radius | `radius-xl` (20px) |
| Padding | 32px (24px mobile) |
| Label | "CAREER READINESS" -- `font-data`, 11px, weight 700, `letter-spacing: 2px`, uppercase, `text-muted`, `margin-bottom: 12px` |
| Verdict word | `font-display`, weight 700, 32px (24px mobile). Color per tier |
| Verdict subtitle | `font-body`, 16px, `text-secondary`, `margin-top: 4px` |
| Animation | `verdictScaleIn` 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) |

**Verdict tiers** (see mockup `VERDICT_TIERS` JS at lines 2336-2340):

| Tier | Word | Subtitle | Color | Border | Glow |
|------|------|----------|-------|--------|------|
| DOMINANT | "DOMINANT BUILD" | "Unstoppable" | `accent-thrive` | `rgba(125,212,163,0.3)` | `0 0 20px rgba(125,212,163,0.15)` |
| SOLID | "SOLID BUILD" | "Strong across the board" | `accent-thrive` | `rgba(125,212,163,0.25)` | `0 0 16px rgba(125,212,163,0.10)` |
| MIXED | "MIXED BUILD" | "Real strengths, real challenges" | `accent-caution` | `rgba(242,212,119,0.25)` | `0 0 16px rgba(242,212,119,0.10)` |
| VULNERABLE | "VULNERABLE BUILD" | "Eyes open" | `accent-alert` | `rgba(244,169,126,0.25)` | `0 0 16px rgba(244,169,126,0.10)` |

#### Victory Bar

See mockup `.victory-bar`, `.victory-cell` at lines 1374-1401.

| Property | Value |
|----------|-------|
| Layout | `display: flex; gap: 6px; max-width: 320px; margin: 20px auto 0` |
| Cell count | Always 5 cells |
| Cell height | 12px |
| Cell radius | `radius-full` |
| Cell order | Raw wins first, then equipped wins, then draws, then losses |

**Cell types:**

| Type | Class | Style |
|------|-------|-------|
| Decisive win | `.raw` | `background: accent-thrive; box-shadow: 0 0 8px rgba(125,212,163,0.25)` |
| Skill-assisted win (rescored) | `.equipped` | `background: accent-insight; box-shadow: 0 0 8px rgba(184,169,232,0.25)` |
| Draw | `.draw-cell` | `background: accent-caution; opacity: 0.4` |
| Loss | `.loss` | `background: bg-deep; border: 1px solid border-default` |

#### Victory Legend

See mockup `.victory-legend` at lines 1404-1428.

| Property | Value |
|----------|-------|
| Layout | `display: flex; justify-content: center; gap: 16px; margin-top: 10px; flex-wrap: wrap` |
| Items | Only show types that exist in the current tally |
| Item layout | 8px color dot + `font-data`, 11px, `text-muted` |
| Legend labels | "Decisive" (thrive/green), "Skill-assisted" (insight/purple), "Unresolved" (bg-deep with border) |

#### Verdict Tally

See mockup `.verdict-tally` at lines 1430-1439.

| Property | Value |
|----------|-------|
| Font | `font-data`, 13px, `text-secondary`, `margin-top: 16px` |
| Format | `"{totalWins} of 5 victories"` -- wins colored with `accent-thrive` |
| With equipped | Appends `"({rawWins} decisive + {equippedWins} skill-assisted)"` -- equipped count colored `accent-insight` |

#### Verdict Narrative

See mockup `.verdict-narrative` at lines 1442-1451 and `updateVerdict()` JS at lines 2405-2415.

| Property | Value |
|----------|-------|
| Font | `font-body`, 15px, `text-secondary`, `line-height: 1.6` |
| Max width | 520px, centered |
| Margin-top | 16px |

**Dynamic narrative rules:**

| Condition | Narrative |
|-----------|----------|
| All 5 decisive (no equipped) | "You won every fight decisively. This path plays to your strengths." |
| Some decisive, no equipped | "You won {N} fight(s) decisively. The remaining challenges might be worth exploring -- equip skills above to see what's possible." |
| Mixed decisive + equipped | "You won {rawWins} fight(s) decisively. {equippedWins} more victory/victories came from skills you chose to invest in -- that's not a shortcut, that's a plan." |
| All equipped, zero raw | "Every victory here came from skills you'd need to build. The path is absolutely doable -- but it asks you to grow." |
| Zero wins | "This path has real challenges -- but now you can see them. That's the first step to beating them." |

**Dynamic update:** After any reroll that changes results, the verdict re-derives tier, rebuilds victory bar cells, updates tally text, and selects the appropriate narrative. The badge re-triggers `verdictScaleIn` animation (reset via `style.animation = 'none'` + offsetHeight + re-set). See mockup JS lines 2416-2421.

#### Rescore Tracking

The key mechanism: when a reroll succeeds, the boss band gets `data-rescored="true"`. The `updateVerdict()` function checks this attribute to distinguish raw wins from equipped wins:

```javascript
bands.forEach(b => {
  const r = b.dataset.result;
  if (r === 'win') {
    if (b.dataset.rescored === 'true') equippedWins++;
    else rawWins++;
  }
  else if (r === 'lose') losses++;
  else if (r === 'draw') draws++;
});
```

This means rescored wins always appear as `accent-insight` (purple) in the victory bar, never `accent-thrive` (green). The distinction is meaningful: "you had this" vs. "you built this."

---

### Section 6: Save CTA

**What it is:** A full-width primary button at the bottom of the scroll.

**Why it works:** After seeing everything, the student's natural next action is "I want to keep this." The button is warm and inviting, not urgent. It says "Save This Build" because the language of saving fits the RPG metaphor -- you save your game.

See mockup `.save-section` at lines 1453-1489.

#### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│              ┌─────────────────────────────────┐                        │
│              │       Save This Build           │                        │
│              └─────────────────────────────────┘                        │
│                                                                         │
│                  Want to explore career branches?                        │
│                  [See the Branch Tree →]                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Specifications

| Property | Value | Token / Class |
|----------|-------|---------------|
| Section spacing | `margin-top: 48px; margin-bottom: 64px` desktop, `32px / 48px` mobile | |
| Primary button | `accent-thrive` bg, `text-inverse`, 48px height, `rounded-lg`, `font-body` weight 700, 17px | See mockup `.save-btn` lines 1461-1477 |
| Button width | `max-width: 480px; width: 100%` | Centered via `display: inline-flex` in centered container |
| Button text | "Save This Build" | |
| Button action | `navigate("/save")` | |
| Hover | `#6bc494` bg, `shadow-glow-thrive`, `translateY(-1px)` | |
| Press | `scale(0.97)` | |
| Branch tree link | `font-body`, 14px, `accent-info`, no underline. Underline on hover, color lightens to `#9cd0ef`. `margin-top: 14px` | See mockup `.branch-link` lines 1480-1489 |
| Branch tree action | `navigate("/branches")` | |

#### Animation

Section fades in with `sectionFadeIn`, `animation-delay: 1.2s`.

---

### States

#### Loading State

See mockup `.loading-state` at lines 1492-1541.

While `POST /build` is in flight:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                         [Campus hero placeholder]                       │
│                         (bg-bp-surface shimmer)                         │
│                                                                         │
│─────────────────────────────────────────────────────────────────────────│
│                                                                         │
│                              🐢                                         │
│                          (emoji float)                                  │
│                                                                         │
│                    Gemma is analyzing your build...                      │
│                                                                         │
│                       [Spinner, 32px]                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

- Campus hero placeholder: `bg-bp-surface` with CSS shimmer animation (gradient sweep left-to-right, 1.5s, infinite). Height matches banner (280px desktop, 200px mobile).
- Loading emoji: 56px, `emojiFloat` animation (translateY 0 to -8px, 2s ease-in-out infinite), `margin-top: -40px`
- Loading text: 16px, `text-secondary`
- Spinner: 32px, `border: 3px solid bg-surface; border-top-color: accent-insight`, rotates via `spin` keyframe

#### Error State

See mockup `.error-state` at lines 1543-1557.

If `POST /build` fails:

- Error container: centered, `bg-bp-mid`, `rounded-xl`, `p-8`, `border border-border-subtle`, `max-w-md mx-auto`, `mt-20`
- Error icon: `accent-alert`, 48px, centered
- Error text: 16px, `text-secondary`, `line-height: 1.5`, `margin-bottom: 24px`
- "Try Again" button: Primary variant
- "Go Back" button: Ghost variant, navigates to `/set-your-course`
- Background: standard `bg-deep` -- no campus hero, no shimmer

#### Reroll In Progress

When a single boss fight is being rescored:

- The specific boss band shows "Rescore Fight" button in loading state (spinner replaces text, disabled)
- Narrative panel dims to 60% opacity
- All other boss bands remain fully interactive
- After completion: thrive glow pulse on card, reroll section hides

#### Mobile Responsive

| Breakpoint | Behavior |
|------------|----------|
| Desktop (1200px+) | Full layout as wireframed. Content column at 1280px max-width with 32px padding. |
| Tablet (768-1199px) | Same layout, 24px padding. Pentagon stacks above legend (flex-wrap). |
| Mobile (<768px) | Campus hero 200px. Hero identity: 80px avatar, 28px name, 16px subtitle, 16px gap, -32px overlap. Pentagon stacks above legend (`position: static`). Path/institution grid collapses to single column. Boss portraits 52px. VS portraits 72px. Skill grid 2-column at 680px, 1-column at 440px. Verdict word 24px. All section gaps 32px. Save section `mt-32px mb-48px`. |

---

### Component Summary

| Component | File | New/Reuse | Notes |
|-----------|------|-----------|-------|
| `CampusHeroBanner` | `components/build-results/CampusHeroBanner.tsx` | New | Full-bleed hero with `HorizonPicture` pattern, gradient fade only (no overlay) |
| `HeroIdentity` | `components/build-results/HeroIdentity.tsx` | New | Horizontal flex: circular avatar with EMOJI_BG + name/subtitle. -48px overlap |
| `PathCard` | `components/build-results/PathCard.tsx` | New | CIP program + SOC career entries with mini stat bars |
| `InstitutionCard` | `components/build-results/InstitutionCard.tsx` | New | School name + Gemma narrative + "Written by Gemma" tag |
| `StatBarRow` | `components/build-results/StatBarRow.tsx` | New | Mini stat bar (label + track + fill + value) for path card |
| `StatInfoPopover` | `components/build-results/StatInfoPopover.tsx` | New | Inline popover with stat definition, source, stat-colored left border |
| `SealedOverlay` | `components/build-results/SealedOverlay.tsx` | New | Desaturated boss portrait, name, "AWAITING" label, sealedPulse animation |
| `VSOverlay` | `components/build-results/VSOverlay.tsx` | New | Player vs boss collision: portraits slam in, VS text, dust puffs, energy burst |
| `BossBand` | `components/build-results/BossBand.tsx` | New | Full boss band: sealed state → VS → reveal → narrative + reroll. Replaces BossSummaryCard |
| `VictoryBar` | `components/build-results/VictoryBar.tsx` | New | 5-cell bar with decisive/skill-assisted/draw/loss coloring + legend |
| `VerdictBadge` | `components/build-results/VerdictBadge.tsx` | New | Verdict display with victory bar, tally, dynamic narrative. Replaces old simple badge |
| `SkillStatBadge` | `components/build-results/SkillStatBadge.tsx` | New | Stat-colored pill badge for skill bonuses (e.g. "ERN +1") |
| `PentagonChart` | `components/PentagonChart.tsx` | Reuse | Existing, pass `highlightStat` for hover. Wrapped in elevation card with sticky positioning |
| `GemmaThinking` | `components/ui/GemmaThinking.tsx` | Reuse | Loading state |
| `GemmaSpinner` | `components/ui/GemmaSpinner.tsx` | Reuse | Loading state |
| `Button` | `components/ui/Button.tsx` | Reuse | Primary and Ghost variants |

**Removed from old spec:** `StatExplainerCard` (replaced by stat legend rows inside the pentagon elevation card), `BossSummaryCard` (replaced by `BossBand`), `RerollFlow` reuse (reroll is now built into `BossBand` directly), `SkillCard` reuse (replaced by inline skill cards with EQUIPPED badge), `PageContainer` grid variant (replaced by content-column pattern).

---

### Scroll-Based Animation Strategy

The page uses CSS `animation-delay` with `sectionFadeIn` keyframes for scroll-triggered sections (see mockup `.anim-section` at lines 1576-1578). Boss bands use `IntersectionObserver` for the sealed-reveal system rather than Framer Motion's `whileInView`.

```css
@keyframes sectionFadeIn {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}
.anim-section {
  animation: sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) both;
}
```

Boss band reveals use two `IntersectionObserver` instances (see mockup `initGauntletReveals()` at lines 2151-2268):
1. **Visibility observer** (`threshold: 0.1`): adds `sealed-visible` class for shimmer
2. **Center-third observer** (`threshold: 0.5`, `rootMargin: '-33% 0px -33% 0px'`): triggers VS overlay and reveal

The `once: true` semantic is handled by checking for `revealed` / `vs-active` / `sealed-hold` classes before re-triggering.

**Reduced motion:** All animations respect `prefers-reduced-motion: reduce`. When reduced motion is preferred, all elements render at their final state (opacity 1, y 0, scale 1) with no spring animations or VS overlays. The `useReducedMotion()` hook from Framer Motion gates all animation props. Boss bands skip directly to revealed state.

---

### Summary of Brightpath Token Usage

| Category | Tokens Used |
|----------|-------------|
| Backgrounds | `bg-void` (VS overlay), `bg-deep` (page, stat bar tracks, loss cells), `bg-mid` (cards, bands, badges), `bg-surface` (loading placeholder, hover), `bg-raised` (popovers) |
| Stat colors | `stat-ern`, `stat-roi`, `stat-res`, `stat-grw`, `stat-hmn` (text, fill, stat bar fill, skill stat badges, popover accent borders) |
| Boss colors | `boss-ai`, `boss-loans`, `boss-market`, `boss-burnout`, `boss-ceiling` (portraits, left stripes, narrative borders, VS energy bursts) |
| Accent semantics | `accent-thrive` (VICTORY, decisive wins, CTA, EQUIPPED badge, skill selection glow), `accent-alert` (DEFEATED, VULNERABLE verdict), `accent-caution` (STANDOFF, MIXED verdict, draws at 40% opacity), `accent-info` (section labels, links, player portrait, emoji BG for turtle/penguin), `accent-insight` (skill-assisted wins, Gemma tag, loading spinner, equipped verdict cells) |
| Text | `text-primary` (names, narrative body), `text-secondary` (subtitles, descriptions, stat explanations), `text-muted` (codes, sources, sealed status, attempt counters), `text-inverse` (on CTA) |
| Borders | `border-subtle` (cards at rest, sealed state), `border-default` (skill cards, loss cells, avatar, popover trigger), `border-strong` (skill card hover, popover trigger hover) |
| Shadows | `shadow-lg` (popovers), `shadow-glow-thrive/caution/alert` (verdict badge per tier), boss portrait glows (`0 0 20px` at 20% opacity) |
| Typography | `font-display` / Fredoka (headings, names, boss labels, verdict word, skill titles), `font-body` / Nunito (narratives, explanations, subtitles, result flavor), `font-data` / Space Mono (scores, labels, badges, tallies, codes, popover sources) |
| Motion | `heroFadeIn`, `emojiBounce`, `fadeInUp`, `simpleFade`, `sectionFadeIn` (page-level); `sealedPulse`, `sealedShimmer`, collision/dust/burst keyframes, `winPulse`/`loseShake`/`drawWobble` (boss bands); `popoverIn`/`popoverOut` (stat info); `verdictScaleIn`, `thriveGlowPulse` (verdict) |

---

## §4 Technical Specification

### Architecture Overview

This is a frontend-only change. A new screen component (`BuildResultsScreen`) consumes the existing `POST /build` and `POST /build/{id}/reroll` endpoints. It reuses existing components (PentagonChart, StatDetailCard) and hooks (useHorizonPick). The screen replaces the navigation target of SetYourCourseScreen's "Spec my build" button, routing to `/my-build` instead of `/reveal`. A new route is added to `App.tsx`.

No backend changes. No pipeline changes. No new API endpoints.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/BuildResultsScreen.tsx` | Create | New consolidated build results screen |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Create | Tests for BuildResultsScreen |
| `frontend/src/components/build-results/CampusHeroBanner.tsx` | Create | Full-bleed campus hero banner with gradient fade (no character overlay) |
| `frontend/src/components/build-results/HeroIdentity.tsx` | Create | Horizontal flex: circular avatar with EMOJI_BG + name/subtitle, -48px overlap |
| `frontend/src/components/build-results/PathCard.tsx` | Create | CIP program + SOC career entries with mini stat bars |
| `frontend/src/components/build-results/InstitutionCard.tsx` | Create | School name + Gemma narrative + "Written by Gemma" tag |
| `frontend/src/components/build-results/StatBarRow.tsx` | Create | Mini stat bar row for path card |
| `frontend/src/components/build-results/StatInfoPopover.tsx` | Create | Inline stat info popover with definition/source |
| `frontend/src/components/build-results/SealedOverlay.tsx` | Create | Desaturated boss portrait with AWAITING label and sealedPulse |
| `frontend/src/components/build-results/VSOverlay.tsx` | Create | Player-vs-boss collision animation overlay |
| `frontend/src/components/build-results/BossBand.tsx` | Create | Full boss band: sealed → VS → reveal → narrative + reroll |
| `frontend/src/components/build-results/VictoryBar.tsx` | Create | 5-cell bar with decisive/skill-assisted/draw/loss coloring + legend |
| `frontend/src/components/build-results/VerdictBadge.tsx` | Create | Verdict badge with victory bar, tally, dynamic narrative |
| `frontend/src/components/build-results/SkillStatBadge.tsx` | Create | Stat-colored pill badge for skill bonuses |
| `frontend/src/App.tsx` | Modify | Add `/my-build` route pointing to BuildResultsScreen |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Change "Spec my build" navigation target from `/reveal` to `/my-build` |

### Data Model Changes

None. All types already exist in `frontend/src/types/build.ts`:
- `Build` — full build result including gauntlet, career, skills
- `BossFightResult` — individual boss fight with result, narrative, reroll state
- `GauntletResult` — all fights + verdict
- `AppliedSkill` — skill pool items for reroll
- `PentagonStats` — five stat values

### Service Changes

No new backend services. Frontend changes only:

**New Components:**

```typescript
// frontend/src/components/build-results/CampusHeroBanner.tsx
interface CampusHeroBannerProps {}
export function CampusHeroBanner(props: CampusHeroBannerProps): JSX.Element;
// Full-bleed banner with campus image + 180px gradient fade. No character overlay.

// frontend/src/components/build-results/HeroIdentity.tsx
interface HeroIdentityProps {
  profileName: string;
  animalEmoji: string;
  schoolName: string;
  programName: string;
}
export function HeroIdentity(props: HeroIdentityProps): JSX.Element;
// Horizontal flex with -48px overlap: 120px circular avatar (EMOJI_BG lookup) + name + subtitle

// frontend/src/components/build-results/PathCard.tsx
interface PathCardProps {
  programName: string;
  cipCode: string;
  careerName: string;
  socCode: string;
  medianWage: number | null;
  stats: PentagonStats;
}
export function PathCard(props: PathCardProps): JSX.Element;
// Left column: CIP program + SOC career + mini stat bars

// frontend/src/components/build-results/InstitutionCard.tsx
interface InstitutionCardProps {
  schoolName: string;
  narrative: string; // Gemma-written institution narrative
}
export function InstitutionCard(props: InstitutionCardProps): JSX.Element;
// Right column: school name + narrative paragraphs + "Written by Gemma" tag

// frontend/src/components/build-results/StatInfoPopover.tsx
interface StatInfoPopoverProps {
  stat: string; // 'ern' | 'roi' | 'res' | 'grw' | 'hmn'
  isOpen: boolean;
  onClose: () => void;
}
export function StatInfoPopover(props: StatInfoPopoverProps): JSX.Element;
// Inline popover with definition, source, stat-colored left border

// frontend/src/components/build-results/BossBand.tsx
interface BossBandProps {
  fight: BossFightResult;
  buildId: string;
  playerEmoji: string;
  playerName: string;
  skillPool: AppliedSkill[];
  onRerollComplete: (updatedFight: BossFightResult) => void;
  onSkillsConsumed: (usedSkillIds: string[]) => void;
}
export function BossBand(props: BossBandProps): JSX.Element;
// Full band: sealed overlay → VS overlay → revealed content (header, narrative, reroll)

// frontend/src/components/build-results/VSOverlay.tsx
interface VSOverlayProps {
  playerEmoji: string;
  playerName: string;
  bossEmoji: string;
  bossShortName: string;
  bossId: string;
  isActive: boolean;
}
export function VSOverlay(props: VSOverlayProps): JSX.Element;
// Player-vs-boss collision: portraits slam in, VS text, collision emoji, 5 dust puffs, energy burst

// frontend/src/components/build-results/VerdictBadge.tsx
interface VerdictBadgeProps {
  rawWins: number;
  equippedWins: number;
  losses: number;
  draws: number;
}
export function VerdictBadge(props: VerdictBadgeProps): JSX.Element;
// Full verdict: CAREER READINESS label, verdict word+subtitle, victory bar, legend, tally, narrative

// frontend/src/components/build-results/VictoryBar.tsx
interface VictoryBarProps {
  rawWins: number;
  equippedWins: number;
  draws: number;
  losses: number;
}
export function VictoryBar(props: VictoryBarProps): JSX.Element;
// 5-cell bar with color coding + legend below
```

**Existing APIs consumed (no changes):**

```typescript
// frontend/src/api/build.ts
createBuild(params: BuildParams): Promise<Build>;

// frontend/src/api/gauntlet.ts
rerollFight(buildId: string, bossId: BossId, skillIds: string[]): Promise<BossFightResult>;
```

**Existing hooks consumed (no changes):**

```typescript
// frontend/src/hooks/useHorizonPick.ts
useHorizonPick(surface: HorizonSurface): HorizonPick | null;
```

**Store interactions:**

```typescript
// frontend/src/store/buildStore.ts — read build, gauntlet, skill_pool
// frontend/src/store/buildInputStore.ts — read school, major, effort, loans, selectedCareer
// frontend/src/store/profileStore.ts — read profileName, animalEmoji
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `commit_navigates_to_reveal` | High | Navigation target changing from `/reveal` to `/my-build` |
| `frontend/src/screens/RevealScreen.test.tsx` | All tests | Low | RevealScreen itself unchanged, but no longer primary entry point |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `redirects to /reveal when build is null` | Low | Guard still references `/reveal`, which still exists |
| `frontend/src/screens/MenuScreen.test.tsx` | `tap build card → navigate to /reveal` | Low | MenuScreen still navigates to `/reveal` for now |
| `frontend/src/screens/SaveWrappedScreen.test.tsx` | `redirects to /reveal when build is null` | Low | Guard still references `/reveal`, which still exists |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/screens/SetYourCourseScreen.test.tsx` — `commit_navigates_to_reveal` | Update expected navigation target from `/reveal` to `/my-build` | SetYourCourseScreen now navigates to `/my-build` |

#### Confirmed Safe

All existing tests for screens NOT modified by this spec:
- `frontend/src/screens/RevealScreen.test.tsx` — screen unchanged, route still exists
- `frontend/src/screens/BranchTreeScreen.test.tsx` — unchanged
- `frontend/src/screens/MenuScreen.test.tsx` — unchanged
- `frontend/src/screens/SaveWrappedScreen.test.tsx` — unchanged
- `frontend/src/screens/ProfileScreen.test.tsx` — unchanged
- `frontend/src/screens/CareerPickScreen.test.tsx` — unchanged
- `frontend/src/screens/LandingScreen.test.tsx` — unchanged
- `frontend/src/screens/SchoolMajorScreen.test.tsx` — unchanged
- `frontend/src/hooks/useHorizonPick.test.ts` — hook unchanged
- `frontend/src/components/StatTutorial.test.tsx` — component unchanged
- `frontend/src/components/horizon/HorizonFooter.test.tsx` — component unchanged

If any of these fail, STOP and escalate.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `renders_loading_state` | Shows loading indicator while POST /build is in flight |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `renders_full_build_results` | All sections render: hero, hero identity, path card, institution card, pentagon+legend, boss bands, verdict, save CTA |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `nav_guard_redirects_when_no_session` | Redirects to `/set-your-course` when school/major/career missing |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `reroll_updates_fight_result` | Reroll flow: select skill (EQUIPPED badge) → rescore → result updates, reroll section hides, data-rescored set |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `verdict_updates_after_reroll` | Verdict badge recalculates with rescored wins shown as insight/purple in victory bar |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `hero_identity_renders_with_emoji_bg` | Hero identity shows avatar with emoji-specific background color, name at 40px, subtitle |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `all_five_boss_bands_render` | All 5 boss bands render in sealed state initially |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `save_button_navigates_to_save` | "Save This Build" button navigates to `/save` |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `path_card_shows_cip_soc_wage` | Path card displays program name, CIP code, career name, SOC code, and wage |
| P1 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `stat_info_popover_opens_closes` | Clicking ? button opens popover with definition and source; clicking again closes |
| P2 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `skill_pool_depletes_after_reroll` | Skills consumed by reroll are removed from available pool |
| P2 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `error_state_shows_retry` | Error on build creation shows retry option |
| P2 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `victory_bar_shows_correct_cell_types` | Victory bar renders 5 cells with correct classes (raw/equipped/draw-cell/loss) |

#### Test Data Requirements

- Mock `createBuild` API response with full `Build` object (reuse pattern from `RevealScreen.test.tsx`)
- Mock `rerollFight` API response with updated `BossFightResult`
- Mock `useHorizonPick` to return deterministic campus image pick
- Zustand store mocks for `buildInputStore`, `buildStore`, `profileStore` (patterns exist in current test files)
- `prefers-reduced-motion` mock for animation tests (exists at `@/test/mocks/prefers-reduced-motion`)

---

## §5 Architecture Review

### @fp-architect Review
**Status:** COMPLETE
**Reviewed:** 2026-04-21

#### System Context

This feature sits entirely in the frontend layer. It introduces a new `/my-build` route that consolidates the existing `/reveal` and `/gauntlet` screens into a single scrollable page. The data flow is: `SetYourCourseScreen` navigates to `BuildResultsScreen`, which calls `createBuild` on mount (same as current `RevealScreen`), then renders stats, gauntlet results, and reroll inline. No Brightsmith pipeline zones are touched, no MCP tools are modified, no backend endpoints change. The feature reads from `buildInputStore`, `buildStore`, and `profileStore` (all Zustand), and consumes `POST /build` and `POST /build/{id}/reroll` via existing API clients.

#### Data Flow Analysis

1. **SetYourCourseScreen -> BuildResultsScreen:** `useSetYourCourse.commit()` currently navigates to `/reveal` (line 522 of `useSetYourCourse.ts`). The spec correctly identifies this as the change point. The commit function writes `currentResolution` fields into `buildInputStore` via `setMajor()` before navigating. BuildResultsScreen will read these same fields. The data handoff is clean.

2. **BuildResultsScreen -> POST /build:** The spec says BuildResultsScreen calls `createBuild` on entry, same as RevealScreen. The actual `createBuild` function signature in `frontend/src/api/build.ts` takes 12 positional arguments (profileName, schoolName, unitid, cipcode, cipTitle, majorText, effort, loanPct, selectedSoc, selectedTitle, studentMajor?, studentCip?), NOT a `BuildParams` object as the spec claims at line 1267. This is a minor documentation mismatch -- the implementation will call the real function, not a fictional params object.

3. **Reroll flow:** `rerollFight(buildId, bossId, skillIds)` in `frontend/src/api/gauntlet.ts` returns `Promise<BossFightResult>`. The spec's `BossBandProps.onRerollComplete` callback receives `BossFightResult`. This contract aligns perfectly.

4. **Store reads:** All three stores have the fields the spec expects:
   - `profileStore`: `profileName` (string|null), `animalEmoji` (string|null) -- confirmed
   - `buildInputStore`: `school`, `effort`, `loans`, `currentResolution` -- confirmed
   - `buildStore`: `build` (Build|null), `selectedCareer` (CareerOutcome|null) -- confirmed

#### Contract Review

**Component interfaces vs. types:** All prop interfaces in section 4 align with the types in `frontend/src/types/build.ts`:
- `BossBandProps.fight: BossFightResult` -- matches type at lines 96-109
- `BossBandProps.skillPool: AppliedSkill[]` -- matches type at lines 148-160, and `Build.skill_pool` at line 178
- `VerdictBadgeProps` takes `rawWins/equippedWins/losses/draws` as numbers -- derived from `GauntletResult.fights`, which is correct
- `PathCardProps.stats: PentagonStats` -- matches type at lines 6-12
- `PentagonChart` already accepts `highlightStat` prop -- confirmed at line 11 of `PentagonChart.tsx`

**API client signatures:** The spec at line 1267 claims `createBuild(params: BuildParams)` but the real signature is 12 positional args. The spec at line 1270 claims `rerollFight(buildId, bossId, skillIds)` which matches exactly.

#### Findings

##### Sound

- **Frontend-only scope is genuine.** No backend changes needed. Both `POST /build` and `POST /build/{id}/reroll` exist and return the exact types the spec consumes. The `Build` type has every field needed for all six screen sections (hero, path, stats, gauntlet, verdict, save).
- **Store architecture is correct.** The three Zustand stores provide all data the screen needs. The navigation guard checking for missing session state (school/major/career) is the right pattern -- matches existing guards in BranchTreeScreen and SaveWrappedScreen.
- **Skill pool filtering is well-designed.** `AppliedSkill.targets: BossId[]` provides the per-boss filter. The `onSkillsConsumed` callback allows the parent to track consumed skills across bands, preventing double-use. This matches the existing pattern in `GauntletScreen.tsx` (lines 80-88).
- **Campus images confirmed.** 48 sets exist in `frontend/public/campus/` with 1400px + 2048px in both WebP and AVIF. The spec's claim of "48 available" is accurate.
- **Routing addition is clean.** Adding `/my-build` to `App.tsx` alongside the existing `/reveal` route is a safe parallel addition. Old routes remain functional per the spec's out-of-scope decision.
- **Component decomposition is well-bounded.** 13 new components in `components/build-results/` with clear single responsibilities. No circular dependencies visible in the prop interfaces.
- **Testing impact analysis is thorough.** The spec correctly identifies `SetYourCourseScreen.test.tsx` navigation target as the only existing test at risk and authorizes the specific modification.

##### Concerns

- **InstitutionCard narrative source is undefined.** The spec defines `InstitutionCardProps.narrative` as a "Gemma-written institution narrative" (line 1204), and section 3 describes it as "Gemma knows about my school" with paragraphs about the specific institution. However, the `Build` type has no `institution_narrative` field. The closest field is `Build.guidance` (line 176 of `build.ts`, line 280 of `career.py`), which is a general build narrative about the career path, not a school-specific narrative. **Impact:** The implementer will either need to repurpose `guidance` (which changes its meaning) or leave the institution card empty. **Recommendation:** Either (a) use `Build.guidance` and relabel the card as "About This Build" / "Gemma's Take" instead of "About the School," or (b) acknowledge this requires a backend change to add an institution narrative field, which contradicts the "no backend changes" constraint. Option (a) is the pragmatic hackathon choice.

- **`createBuild` signature mismatch in spec.** Line 1267 shows `createBuild(params: BuildParams)` but the actual function at `frontend/src/api/build.ts` lines 98-127 takes 12 positional arguments. **Impact:** Minimal -- the implementer will see the real signature and use it. **Recommendation:** Correct the spec to show the actual signature, or note that the implementation should follow the existing `RevealScreen.tsx` call pattern (lines 83-100).

- **`useSetYourCourse.commit()` navigation target is in the hook, not the screen.** The spec says to modify SetYourCourseScreen to change the navigation target (line 1155), but the actual `navigate("/reveal")` call is at line 522 of `useSetYourCourse.ts`, not in the screen file. **Impact:** If the implementer only modifies `SetYourCourseScreen.tsx`, the navigation will not change. **Recommendation:** Add `frontend/src/hooks/useSetYourCourse.ts` to the File Changes table as a Modify target (change `navigate("/reveal")` to `navigate("/my-build")` at line 522).

- **2800px campus image variant exists but is not mentioned.** The glob shows one image set has a 2800px variant alongside the 1400/2048 pair. The spec only mentions 1400/2048. **Impact:** Negligible -- the `<picture>` element will just use the two standard sizes. But the `getCampusImages()` utility should be aware of the inconsistency if it tries to enumerate image sets programmatically.

##### Blockers

None.

#### Verdict
- [x] APPROVED

#### Conditions
1. **Add `useSetYourCourse.ts` to File Changes table** -- the navigate target lives at line 522 of this hook file, not in `SetYourCourseScreen.tsx`. Both files need modification.
2. **Resolve InstitutionCard narrative source** before implementation begins -- decide whether to repurpose `Build.guidance` with a relabeled card title, or accept that this card will need a different data source. The implementer should not be left guessing about where the narrative comes from.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline/data changes)

---

## §6 Implementation Log

**Status:** COMPLETE
**Implemented:** 2026-04-21

### Files Modified
| File | Change Summary |
|------|---------------|
| `frontend/src/screens/BuildResultsScreen.tsx` | New screen: single-page build results with hero, stats, gauntlet, verdict, save CTA |
| `frontend/src/components/build-results/bossData.ts` | Constants: boss metadata, emoji BGs, stat colors, verdict tiers, result colors |
| `frontend/src/components/build-results/CampusHeroBanner.tsx` | Full-bleed campus hero with gradient fade |
| `frontend/src/components/build-results/HeroIdentity.tsx` | Character identity with emoji avatar, name, subtitle |
| `frontend/src/components/build-results/PathCard.tsx` | CIP program + SOC career + mini stat bars |
| `frontend/src/components/build-results/InstitutionCard.tsx` | School name + Gemma narrative + attribution |
| `frontend/src/components/build-results/StatBarRow.tsx` | Mini stat bar for path card |
| `frontend/src/components/build-results/StatInfoPopover.tsx` | Inline popover with stat definition/source |
| `frontend/src/components/build-results/SkillStatBadge.tsx` | Stat-colored pill badge for skill bonuses |
| `frontend/src/components/build-results/SealedOverlay.tsx` | Sealed state with desaturated portrait + AWAITING |
| `frontend/src/components/build-results/VSOverlay.tsx` | Player vs boss collision animation |
| `frontend/src/components/build-results/BossBand.tsx` | Full boss band: sealed → VS → reveal → reroll |
| `frontend/src/components/build-results/VictoryBar.tsx` | 5-cell bar with decisive/equipped/draw/loss coloring |
| `frontend/src/components/build-results/VerdictBadge.tsx` | Verdict display with victory bar, tally, narrative |
| `frontend/src/App.tsx` | Added `/my-build` route |
| `frontend/src/hooks/useSetYourCourse.ts` | Changed nav target from `/reveal` to `/my-build` |
| `frontend/src/hooks/useSetYourCourse.test.ts` | Updated nav expectations to `/my-build` |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | Updated nav expectation to `/my-build` |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | 24 new tests |

### Deviations from Spec
1. **InstitutionCard narrative uses `Build.guidance`** — no `institution_narrative` field exists on the Build type. Repurposed general guidance narrative (Gemma-written) for the institution card per architect review condition #2.
2. **Navigation target change is in `useSetYourCourse.ts`** not `SetYourCourseScreen.tsx` — per architect review condition #1.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | — |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| BuildResultsScreen.test.tsx | renders_loading_state | Loading indicator, emoji, "Gemma is analyzing" text |
| BuildResultsScreen.test.tsx | renders_full_build_results | All sections: hero, path, institution, pentagon, 5 boss bands, verdict, save |
| BuildResultsScreen.test.tsx | nav_guard_redirects_when_no_session | Redirects to /set-your-course when session state missing (3 sub-tests) |
| BuildResultsScreen.test.tsx | reroll_updates_fight_result | Skill select → rescore → result updates to VICTORY |
| BuildResultsScreen.test.tsx | verdict_updates_after_reroll | Tally recalculates from 3 to 4 victories |
| BuildResultsScreen.test.tsx | hero_identity_renders_with_emoji_bg | Avatar emoji, profile name, subtitle |
| BuildResultsScreen.test.tsx | all_five_boss_bands_render | 5 role=region elements with correct aria-labels |
| BuildResultsScreen.test.tsx | save_button_navigates_to_save | navigate("/save") on click |
| BuildResultsScreen.test.tsx | branch_tree_link | navigate("/branches") on click |
| BuildResultsScreen.test.tsx | path_card_shows_cip_soc_wage | CIP, SOC, wage display + null wage shows N/A |
| BuildResultsScreen.test.tsx | stat_info_popover_opens_closes | ? button toggle, popover content, aria-expanded |
| BuildResultsScreen.test.tsx | error_state_shows_retry | Error message, retry, go back |
| BuildResultsScreen.test.tsx | victory_bar_shows_correct_cell_types | 3 raw, 1 draw-cell, 1 loss |
| + 11 more | edge cases | Unmount safety, stat legend, institution card, createBuild args, etc. |

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
**Status:** CHANGES REQUIRED
**Reviewer:** Staff Engineer (15 YOE) | 2026-04-21

#### Summary

Look, I love Claude, BUT... this is actually pretty solid work for 80% of the surface area. The unmount guard via `cancelledRef`, the IntersectionObserver cleanup, the timeout cleanup on unmount -- someone (or something) was thinking about lifecycle. The test suite is thorough with 24 tests covering P0-P2 priorities. That said, I found two serious issues and one moderate issue that need fixing before this ships.

#### Findings

**[S1] Silent swallow on reroll failure -- BossBand.tsx:107**
Severity: SERIOUS

The `catch {}` block in `handleRescore` silently eats reroll errors. User clicks "Rescore Fight", the network call fails, and... nothing happens. No feedback. They'll click it again, and again. This is a 3am support ticket factory.

```tsx
// Current (line 107)
} catch {
  // Keep current state on failure
}
```

Fix: Show the user something went wrong. At minimum, set a local error state and render it:
```tsx
const [rescoreError, setRescoreError] = useState<string | null>(null);
// ...
} catch {
  setRescoreError("Rescore failed -- try again");
}
```
Then render `rescoreError` near the rescore button. Clear it on the next attempt.

Route: @implementation

**[S2] IntersectionObserver recreated on every state change -- BuildResultsScreen.tsx:166-214**
Severity: SERIOUS

The observer `useEffect` has `vsActiveBands` and `revealedBands` in its dependency array. These are Sets that change every time a band animates. Each change disconnects both observers and creates new ones, re-observing all elements. With 5 boss bands animating in sequence, this fires repeatedly during the scroll-reveal cascade. Works in dev with 5 bands; would be a performance concern at scale and causes unnecessary DOM thrash now.

Fix: Move the state reads for `vsActiveBands`/`revealedBands` inside the observer callback using refs, so the effect only depends on `[build, fights]`:
```tsx
const vsActiveBandsRef = useRef(vsActiveBands);
vsActiveBandsRef.current = vsActiveBands;
const revealedBandsRef = useRef(revealedBands);
revealedBandsRef.current = revealedBands;
```
Then read from refs inside the observer callback instead of the closure values.

Route: @implementation

**[M1] `triggerReveal` captures stale `revealedBands`/`vsActiveBands` -- BuildResultsScreen.tsx:153-163**
Severity: MODERATE

`triggerReveal` is a `useCallback` with `revealedBands`, `vsActiveBands`, `vsDoneBands` in its deps. These are recreated as new `Set` objects on every state update, causing `triggerReveal` to be a new function reference each render. This feeds into the observer effect (S2 above), compounding the observer recreation problem. Same fix applies -- use refs for the guard checks.

Route: @implementation (same fix as S2)

#### What's Good

- Unmount safety via `cancelledRef` is correct and tested (line 724-766 in tests)
- Timeout cleanup on unmount (line 217-221) prevents leaked timers
- `skipToRevealed` fast-scroll handler is a nice touch -- prevents animation pile-up
- Nav guard with session hint for UX continuity
- Test coverage is genuinely comprehensive: loading, error, reroll, verdict recalc, unmount race
- `availableSkillPool` is correctly memoized with consumed skill tracking
- No XSS concerns: React's JSX escaping handles all user input (names, narratives); no `dangerouslySetInnerHTML`

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-21 00:35

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | PASS (pre-existing failures, not caused by this spec) | 47 errors in 18 files — confirmed identical on HEAD before this spec's changes (0 backend files modified by this spec) |
| Tests (pytest) | PASS | 1703 passed, 1 deselected |

#### mypy Note
47 mypy errors exist across 18 backend files (`app/models/`, `app/routers/`, `app/services/`). These are pre-existing: verified by stashing all working-tree changes and re-running mypy against HEAD, which produced the identical error count. This spec introduced zero backend file changes.

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 615 passed, 1 skipped (616 total), 58 test files |
| Production build (Vite) | PASS | 695 modules transformed, built in 1.44s |

### Build Accountability Log
| Attempt | Result |
|---------|--------|
| 1 | All checks passed |

---

## §10 Discussion

```
[2026-04-21] @faang-staff-engineer → @implementation
Code review complete. 2 SERIOUS + 1 MODERATE findings.
S1: Add error feedback to reroll catch block in BossBand.tsx.
S2+M1: Refactor IntersectionObserver effect to use refs for vsActiveBands/revealedBands
instead of closure state, eliminating observer recreation on every animation tick.
See §8 Code Review for details and fixes.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
