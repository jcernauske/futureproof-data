# Feature: Onboarding Screens (Landing + School/Major + Character Select)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-onboarding-screens.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, routing, state management)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes — school list is mock data for this spec)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 mockups and propose the premium implementation
   - Visionary validates Brightpath token usage, animation sequences, responsive behavior
   - Writes to §3 with any enhancements or adjustments
   - Reference the approved HTML mockups at /mnt/user-data/outputs/futureproof-landing-v1.html, futureproof-school-major-v2.html, futureproof-character-select-v1.html

3. IMPLEMENTATION
   - Implement all three screens as React components with Framer Motion animations
   - Wire up client-side routing (React Router)
   - Create shared state store (Zustand) for build data
   - Use Brightpath design tokens exclusively — no hardcoded colors, spacing, or typography
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - Each screen: renders, interactions work, state updates correctly
   - Routing: navigation between screens works
   - Store: build state persists across screen transitions
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance across all three screens
   - Confirm: dark backgrounds, correct fonts, token-only colors, responsive behavior, animation springs
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
   - Generate report to reports/feature-onboarding-screens-YYYY-MM-DD.md
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
| Created | 2026-04-08 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-08 |
| Blocked By | — |
| Related Specs | feature-project-scaffolding (COMPLETE) |

---

## §1 Feature Description

### Overview

Build the first three screens of the FutureProof onboarding flow: a landing/hero page, a school + major selection screen, and a character select screen. These are the entry point to the entire product — the screens a student sees when they first land on FutureProof from a shared link or direct visit.

### Problem Statement

The app shell exists (Spec 0) but has no real screens. Students need a clear, engaging entry flow that hooks them emotionally and captures the inputs needed to generate their build (school, major, character). This is also the first real test of the Brightpath design system with production components, and the first screen flow that will appear in the hackathon demo video.

### Revised Screen Order

The original PRD had Character Select as Screen 1 (before school/major). This spec implements a revised order based on design review:

1. **Landing/Hero** — 5-second hook, one CTA. Establishes what FutureProof is.
2. **School + Major** — Intent-driven entry. The student's real question ("where does ISU Business lead?") comes first.
3. **Character Select** — Reward/personalization layer. Now feels earned — "you told us your path, now claim your character."

This order solves the cold-traffic problem (a student landing from a shared card link needs context before picking an animal) and mirrors how RPGs actually work (you see the world, then you create your character for it).

### Success Criteria

- [ ] Landing page renders with animated pentagon, tagline, CTA, and Ollama footer
- [ ] School search with autocomplete dropdown (mock data: 20-30 schools)
- [ ] Major selection grid populates after school is selected (mock data: 8-12 majors per school)
- [ ] Character select: 8 emoji animals in a grid, selectable
- [ ] Accessory pills: toggleable, multiple select, shown on character preview
- [ ] Skin tone swatches: selectable (persists in build state)
- [ ] Live character preview on right column updates with selections
- [ ] Navigation between all three screens via React Router
- [ ] Build state (school, major, animal, accessories, skin tone) persists in Zustand store across screens
- [ ] Progress bar updates across screens (0% landing → 33% school → 50% character → continues in future specs)
- [ ] Back navigation works on each screen
- [ ] All three screens are responsive (desktop primary, mobile functional)
- [ ] All Brightpath design tokens used — zero hardcoded colors/spacing/fonts
- [ ] Framer Motion animations: page transitions, hover states, selection feedback
- [ ] All tests pass (component renders, interactions, routing, store)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | School + Major before Character Select | Cold traffic needs context before animal selection. Intent-driven entry ("what happens with my ISU degree?") before personalization. | Original PRD order (character first) — creates a "what is this?" moment for new visitors |
| 2 | Landing page as separate screen, not integrated | 5-second hook + single CTA keeps the entry clean. Judges hitting the URL immediately understand the product. | Combined landing + school input on one page — too busy, dilutes the hook |
| 3 | Emoji animals instead of rendered art | Zero asset pipeline. Renders everywhere. Kids think in emoji. Midjourney assets are post-hackathon. | CSS-drawn characters (fragile, inconsistent), placeholder silhouettes (no personality) |
| 4 | Mock school data for this spec | Data pipeline is running separately. Frontend shouldn't block on it. Mock data shape matches Scorecard schema so swapping to real data is a config change. | Wait for pipeline — creates unnecessary coupling |
| 5 | Zustand for build state | Lightweight, no boilerplate, works with React 19. Build data is the core state object for the entire app. | React context (verbose for this use case), Jotai (similar but less ecosystem) |
| 6 | Skin tone is identity signal, not visual change | Emojis don't change color with a slider. Skin tone persists in build state for the character card (post-hackathon: rendered art will use it). For MVP: it's an inclusion gesture that carries through to the share card metadata. | Drop it entirely (loses inclusion signal), apply emoji skin tone modifiers (limited to human emojis, not animals) |

### Constraints

- No backend calls in this spec — all data is mock/static. Backend integration comes in a later spec.
- No effort slider screen — that's the next spec after this one.
- No Gemma integration — these screens are pure frontend.
- School coverage: mock 20-30 recognizable schools with 8-12 majors each. Enough to demonstrate the flow.

---

## §3 UI/UX Design

> @fp-design-visionary fills this section with the premium implementation target.
> Reference mockups: futureproof-landing-v1.html, futureproof-school-major-v2.html, futureproof-character-select-v1.html

### Screen 1: Landing / Hero

**Layout:** Full viewport, centered content, single column. No max-width constraint on the outer container — content centered within.

**Elements (top to bottom):**
- Subtle noise texture overlay (opacity 2-3%) on `bg-void` background
- Twinkling star particles (CSS animated, 10-14 dots, randomized positions/delays)
- Ambient radial glow behind the pentagon (thrive + insight + caution blend, pulsing)
- `FUTUREPROOF` brand mark — Fredoka 700, 13px, `text-muted`, letter-spacing 3px, uppercase
- Pentagon radar chart (220×220 SVG):
  - 3-tier grid lines (rgba white at 4%, 3%, 2.5%)
  - 5 axis lines from center
  - Animated stat shape: stroke-dasharray draw-in over 2s with 0.5s delay
  - 5 stat dots at vertices: fade-in staggered 200ms apart starting at 2.2s
  - Stat labels (ERN, ROI, RES, GRW, HMN) in Space Mono 9px, stat colors, 50% opacity
- Tagline: Fredoka 700, clamp(28px, 5vw, 46px), `text-primary`. "A college degree isn't a destination." + line break + "It's a " + gradient-highlighted "starting position."
- Subtitle: Nunito 400, clamp(15px, 2vw, 18px), `text-secondary`, max-width 520px
- CTA button: Fredoka 600, 18px, `accent-thrive` bg, `text-inverse` color, 18px/44px padding, `radius-lg`, glow shadow. Hover: translateY(-3px), stronger glow. Contains sparkle ✦ with pulse animation.
- Subtle horizontal divider line (120px, gradient to transparent)
- Footer: Nunito 13px, `text-muted`. Ollama equity message with `accent-thrive` span.

**Animations:**
- Stars: individual CSS `twinkle` keyframes with randomized durations (3-5s) and delays
- Pentagon: stat shape draws in via stroke-dashoffset animation (2s ease-out, 0.5s delay)
- Stat dots: scale from 0 to 3.5r, staggered 200ms apart
- Ambient glow: subtle scale pulse (1 → 1.05) over 6s
- CTA sparkle: opacity + scale pulse over 2s

**Responsive:**
- Desktop: full viewport centered
- Mobile: same layout, tagline scales down via clamp(), padding reduces to 2rem

### Screen 2: School + Major Selection

**Layout:** Two-column grid on desktop (1fr 1fr, 64px gap). Left: form. Right: character preview. On mobile: single column, preview above form.

**Left column — Form:**
- Step indicator: Space Mono 11px, `text-muted`, letter-spacing 2px, uppercase — "STEP 1 OF 3"
- Screen title: Fredoka 700, 36px, `text-primary` — "Where are you headed?"
- Subtitle: Nunito 16px, `text-secondary` — explains what happens next
- **School search input:**
  - Empty state: 56px height, `bg-deep`, 1px border `rgba(255,255,255,0.08)`, `radius-lg`, search icon left-padded. Placeholder in `text-muted`.
  - Focus state: border changes to `accent-info`, 3px box-shadow ring at 12% opacity
  - Autocomplete dropdown: `bg-raised`, `radius-lg`, `shadow-lg`. Items 14px/20px padding with school name (Nunito 600, 15px) and meta line (city/state in `text-muted` 13px). Hover: `bg-surface`. Selected: left border 3px `accent-thrive`.
  - Selected state: input replaced by chip — `bg-mid`, border `rgba(accent-thrive, 0.25)`, `radius-lg`. Green dot (8px, thrive glow) + school name (Nunito 600, 15px) + close button (20px circle).
- **Major selection grid:**
  - Appears after school is selected (animated slide-down with `spring-smooth`)
  - 2-column grid, 10px gap
  - Cards: `bg-mid`, 1px border `rgba(255,255,255,0.06)`, `radius-lg`, 14px/18px padding
  - Card content: major name (Nunito 600, 14px) + grads/yr (Space Mono 10px, `text-muted`)
  - Hover: `bg-surface`, border brightens, translateY(-1px)
  - Selected: `bg-surface`, border `rgba(accent-thrive, 0.35)`, subtle glow, 2px green top bar
- CTA: same style as landing. Text: "See your build ✦"
- CTA hint below: Nunito 13px, `text-muted` — "Next: customize your character, then see your stats"

**Right column — Character preview:**
- Ambient glow (radial gradient, pulsing)
- Emoji character: 120px font-size, float animation (translateY 0 → -6px, 3s), drop-shadow
- Green radial platform glow below (140×10px ellipse)
- Accessory badges: 32px circles, `bg-mid`, border, emoji 14px (show selected accessories)
- Label: character name (Fredoka 600, 18px) + school/major context (Space Mono 11px, `text-muted`)
- Evolution hint: arrow → dimmed/filtered emoji silhouette → "Who will you become?" italic label. Entire hint at 35% opacity.

**Responsive:**
- Desktop: two-column grid
- Mobile (<900px): single column, preview stacks above form (order: -1), emoji scales to 80px, major grid goes single column

### Screen 3: Character Select

**Layout:** Two-column grid (same as Screen 2). Left: picker controls. Right: live preview.

**Left column — Picker:**
- Step indicator: "STEP 2 OF 3"
- Screen title: "Choose your character"
- Subtitle: "Pick an animal and make it yours."
- **Animal grid:**
  - 4×2 grid, 12px gap
  - Cards: `bg-mid`, 1px border, `radius-xl`, 16px/8px padding, centered content
  - Each card: emoji (44px) + name label (Nunito 600, 12px, `text-muted`, lowercase)
  - Hover: `bg-surface`, translateY(-3px), emoji scale 1.1
  - Selected: `bg-surface`, border `rgba(accent-thrive, 0.4)`, glow, green bottom bar (24×3px), emoji scale 1.15, name becomes `text-primary`
  - Animals: 🐻 bear, 🐰 bunny, 🦊 fox, 🐢 turtle, 🐿️ squirrel, 🦉 owl, 🐱 cat, 🦌 deer
- **Accessory pills:**
  - Flex wrap, 10px gap
  - Pill: `bg-mid`, 1px border, `radius-full`, 8px/16px padding, emoji (16px) + label (13px, `text-muted`)
  - Hover: `bg-surface`, `text-secondary`
  - Selected: `rgba(accent-thrive, 0.1)` bg, border `rgba(accent-thrive, 0.3)`, `text-primary`
  - Accessories: 👓 glasses, 🧕 hijab, ♿ wheelchair, 🦻 hearing aid, 🏳️‍🌈 pride pin, 🦿 prosthetic, 🎒 backpack, 🧢 cap
- **Skin tone swatches:**
  - Horizontal row, 8px gap
  - 28px circles with skin tone colors: #FDDBB4, #E8B98D, #C4956A, #A0714F, #6B4423, #3C2415
  - Hover: scale 1.15
  - Selected: 2px border `accent-thrive`, glow, scale 1.1
- CTA: "Build my character ✦"
- CTA hint: "Next: set your effort level, then see your stats"

**Right column — Live preview:**
- Same structure as Screen 2 preview but larger: emoji at 160px, stronger glow (350px diameter)
- Float animation (4s cycle, -8px)
- Accessory badges update in real-time as pills are toggled (40px circles, `bg-mid`)
- Preview info: animal name (Fredoka 700, 22px), school/major (Space Mono 11px), "Waiting to be built..." (Nunito 14px, `text-secondary`)

**Responsive:**
- Same breakpoint behavior as Screen 2

### Shared Elements

**Progress bar:** Fixed top, 3px height, `bg-mid` track. Fill: linear-gradient `accent-thrive` → `accent-info`. Width by screen: 0% landing, 33% school/major, 50% character select.

**Back link:** Absolute positioned, top-left. Nunito 14px, `text-muted`, flex with chevron-left SVG icon. Hover: `text-secondary`.

**Page transitions:** Framer Motion AnimatePresence. Enter: opacity 0→1 + translateY 20→0, `spring-smooth`. Exit: opacity 1→0, 200ms.

### Cozy Quest / Brightpath Design References

- Backgrounds: `bg-void` (landing, deepest), `bg-deep` (page default), `bg-mid` (cards), `bg-surface` (hover/selected), `bg-raised` (dropdowns)
- Accents: `accent-thrive` (CTAs, selected states, positive), `accent-info` (focus rings, links), stat colors for pentagon
- Typography: Fredoka (display/titles), Nunito (body/UI), Space Mono (data/metadata)
- Radii: `radius-lg` (buttons, cards, inputs), `radius-xl` (large cards, animal grid), `radius-full` (pills, swatches)
- Shadows: `shadow-lg` (dropdowns), glow shadows for selected/active states
- Springs: `spring-smooth` (page transitions, reveals), `spring-bouncy` (selection feedback), `spring-snappy` (button press)
- Libraries: Framer Motion (animations), React Router (routing), Zustand (state)

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Landing CTA | `btn-start` | button | "Start building your future" |
| School search | `input-school-search` | input | "Search for your school" |
| School autocomplete | `listbox-schools` | listbox | "School search results" |
| Major grid | `grid-majors` | grid | "Available majors" |
| Major card | `major-{slug}` | button | Major name |
| Animal grid | `grid-animals` | radiogroup | "Choose your animal character" |
| Animal card | `animal-{name}` | radio | Animal name |
| Accessory pill | `acc-{name}` | checkbox | Accessory name |
| Skin tone swatch | `tone-{index}` | radio | "Skin tone {index}" |
| Character select CTA | `btn-build` | button | "Build my character" |
| Progress bar | `progress-onboarding` | progressbar | "Onboarding progress" |
| Back link | `link-back` | link | "Go back" |

---

## §4 Technical Specification

### Architecture Overview

This spec introduces the first real React components, client-side routing, and a Zustand state store. All three screens are pure frontend — no backend API calls. School and major data is mocked locally with a shape that matches the eventual College Scorecard data products, making the swap to real data a straightforward change.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/App.tsx` | Modify | Replace shell content with React Router outlet |
| `frontend/src/main.tsx` | Modify | Wrap app in BrowserRouter |
| `frontend/src/stores/buildStore.ts` | Create | Zustand store for build state (school, major, animal, accessories, skinTone) |
| `frontend/src/types/build.ts` | Create | TypeScript types for build state, school, major, animal, accessory |
| `frontend/src/data/mockSchools.ts` | Create | Mock school + major data (20-30 schools, 8-12 majors each) |
| `frontend/src/data/animals.ts` | Create | Animal species list with emoji and name |
| `frontend/src/data/accessories.ts` | Create | Accessory list with emoji, name, and category |
| `frontend/src/pages/LandingPage.tsx` | Create | Landing/hero screen |
| `frontend/src/pages/SchoolMajorPage.tsx` | Create | School + major selection screen |
| `frontend/src/pages/CharacterSelectPage.tsx` | Create | Character select screen |
| `frontend/src/components/PentagonChart.tsx` | Create | SVG pentagon radar chart (reusable — used on landing and later screens) |
| `frontend/src/components/ProgressBar.tsx` | Create | Fixed top progress bar |
| `frontend/src/components/BackLink.tsx` | Create | Back navigation component |
| `frontend/src/components/SchoolSearch.tsx` | Create | School search input with autocomplete dropdown |
| `frontend/src/components/MajorGrid.tsx` | Create | Major selection grid |
| `frontend/src/components/AnimalGrid.tsx` | Create | Animal species selection grid |
| `frontend/src/components/AccessoryPills.tsx` | Create | Accessory toggle pills |
| `frontend/src/components/SkinToneSwatches.tsx` | Create | Skin tone selection swatches |
| `frontend/src/components/CharacterPreview.tsx` | Create | Right-column character preview (shared between Screen 2 and 3) |
| `frontend/package.json` | Modify | Add dependencies: react-router-dom, zustand |

### Data Model

```typescript
// types/build.ts

type AnimalSpecies = 'bear' | 'bunny' | 'fox' | 'turtle' | 'squirrel' | 'owl' | 'cat' | 'deer';

type AccessoryId = 'glasses' | 'hijab' | 'wheelchair' | 'hearing-aid' | 'pride-pin' | 'prosthetic' | 'backpack' | 'cap';

interface School {
  id: string;           // UNITID from College Scorecard
  name: string;
  city: string;
  state: string;
  majors: Major[];
}

interface Major {
  id: string;           // CIP code
  name: string;
  gradsPerYear: number; // Mock for now, will come from Scorecard
}

interface BuildState {
  // Screen 2 inputs
  school: School | null;
  major: Major | null;

  // Screen 3 inputs
  animal: AnimalSpecies;
  accessories: AccessoryId[];
  skinTone: string;     // hex color

  // Future screens will add:
  // effortSlider: number (0-1)
  // stats: Stats
  // bossResults: BossResults
  // etc.
}
```

### Zustand Store

```typescript
// stores/buildStore.ts

interface BuildStore extends BuildState {
  setSchool: (school: School | null) => void;
  setMajor: (major: Major | null) => void;
  setAnimal: (animal: AnimalSpecies) => void;
  toggleAccessory: (id: AccessoryId) => void;
  setSkinTone: (hex: string) => void;
  reset: () => void;
}
```

### Routing

```
/           → LandingPage
/school     → SchoolMajorPage
/character  → CharacterSelectPage
/effort     → (future spec)
/build      → (future spec)
```

### Service Changes

- Install `react-router-dom` (v7) and `zustand` (v5)
- No backend changes in this spec

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/App.test.tsx` | App renders test | High | App.tsx is being completely rewritten to use Router |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `App.test.tsx` | Rewrite to test router renders landing page | App.tsx now renders a Router outlet instead of shell content |

#### Confirmed Safe

- All backend tests (no backend changes in this spec)
- `frontend/src/styles/` files (no changes to design tokens)

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `pages/LandingPage.test.tsx` | renders landing page | Pentagon, tagline, CTA button present |
| P0 | `pages/SchoolMajorPage.test.tsx` | renders school search | Search input present, accepts input |
| P0 | `pages/SchoolMajorPage.test.tsx` | school selection flow | Search → autocomplete → select → chip appears → majors shown |
| P0 | `pages/CharacterSelectPage.test.tsx` | renders animal grid | All 8 animals present and selectable |
| P0 | `pages/CharacterSelectPage.test.tsx` | animal selection updates preview | Click animal → preview emoji changes |
| P1 | `pages/CharacterSelectPage.test.tsx` | accessory toggle | Toggle pill → badge appears in preview |
| P1 | `stores/buildStore.test.ts` | store state management | Set school/major/animal, toggle accessories, reset |
| P1 | `components/SchoolSearch.test.tsx` | autocomplete filtering | Type query → results filter → select result |
| P1 | `components/PentagonChart.test.tsx` | renders SVG | Pentagon SVG renders with stat labels |
| P2 | `App.test.tsx` | routing between screens | Navigate landing → school → character via CTA clicks |

#### Test Data Requirements

- Mock school data fixture (3-5 schools with majors) for component tests
- Zustand store can be tested directly without rendering components

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
**Status:** SKIPPED (mock data only, no pipeline changes)

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
[Filled in by @design-builder — Brightpath token compliance, dark-first enforcement, responsive behavior, animation springs]

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
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

**Context for agents:** The three HTML mockups in /mnt/user-data/outputs/ are the approved visual direction. They use the Brightpath design system tokens faithfully. The implementation should match these mockups closely while adding the interactivity, state management, and animations described in §3. The mockups show the "selections made" state — agents must also implement empty states, loading states, and transitions between states.

**Mock data note:** The mock school dataset should include recognizable schools across tiers (Ivy League, state flagships, regional state schools, community colleges) to demonstrate the school-specific tailoring concept. Include ISU (Indiana State University) as it's used in all PRD examples. Mock majors should reflect programs those schools actually offer.

---
