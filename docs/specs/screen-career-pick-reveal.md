# Feature: Career Pick + Reveal (Screens 5 & 6)

## Claude Code Prompt

```
Read the spec at docs/specs/screen-career-pick-reveal.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, routing, state management, API integration)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes — backend API contracts are defined)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 mockups and propose the premium implementation
   - Visionary validates Brightpath token usage, animation sequences, responsive behavior
   - Cross-reference DESIGN.md (source of truth) and docs/mockups/brightpath-design-system-v2.html (visual proof)
   - Writes to §3 with any enhancements or adjustments

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code
   - Implement all components as React with Framer Motion animations
   - Wire up API calls to FastAPI endpoints (or mock handlers if B1 not complete)
   - Use Brightpath design tokens exclusively — no hardcoded colors, spacing, or typography
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - Each component: renders, interactions work, state updates correctly
   - API integration: loading states, error states, happy path
   - Tutorial overlay: shows on first build, skips on subsequent
   - Pentagon animation: renders correctly with mock data
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance across all components
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
   - Generate report to reports/screen-career-pick-reveal-YYYY-MM-DD.md
```

---

## Status: IMPLEMENTATION

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
| Created | 2026-04-13 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-13 |
| Blocked By | B1 (FastAPI routers), F2 (school/major/sliders) |
| Related Specs | `feature-onboarding-screens` (F1, DRAFT), `screen-school-major-sliders` (F2, not started) |

---

## §1 Feature Description

### Overview

Build Screens 5 and 6 of the FutureProof flow: the tiered career picker and the stat reveal. This is where the app stops asking questions and starts showing answers. The student picks a career from Gemma-tiered options (Common / Less Common / Stretch), watches a personalized loading sequence, then gets their first look at the five-stat pentagon, Gemma's Take narrative, and career detail. On their first build, a stat tutorial overlay walks them through each stat before the full reveal lands.

This is the emotional pivot of the product — the "Stage 2 Reveal" moment in DESIGN.md's emotional framework. The design targets **awe + pride**. Everything before this was input. Everything after is consequence.

### Problem Statement

The student has selected a school, major, effort level, and loan percentage. The backend has computed career outcomes from the data pipeline and Gemma has tiered them. The student now needs to:

1. **Choose a career to build around** from a meaningful grouping (not a flat list of 15+ crosswalk matches)
2. **Wait through computation** (stat engine + boss fights + branches + guidance — multiple backend calls) without feeling abandoned
3. **Understand their stats** the first time they see a pentagon (the tutorial)
4. **Read Gemma's coaching narrative** before seeing raw numbers
5. **See the full reveal** — animated pentagon, career title, salary, ROI, and key data points

### CLI → Frontend Mapping

| CLI Function | This Spec | What It Does |
|---|---|---|
| `_prompt_tiered_career_pick()` | Screen 5: Career Pick | Gemma-tiered career menu (Common / Less Common / Stretch) |
| `_build_full()` | Loading state between Screen 5 → 6 | Orchestrates: stat_engine → career_tiering → boss_fights → branch_tree → skill_recs → skill_pool → guidance |
| `_display_build()` | Screen 6: Reveal + Stats | Renders Gemma's Take → pentagon → career header |

### Success Criteria

- [x] Career picker renders three tiers (Common / Less Common / Stretch) with career cards
- [x] Each career card shows: occupation title, emoji indicator, median salary (Space Mono), stat preview pills
- [x] Student can pick any career from any tier — tiers are guidance, not gates
- [x] Picking a career triggers the build orchestration API call
- [x] Personalized loading screen shows profile name + emoji + animated progress messages
- [x] Loading screen cycles through contextual messages (not a spinner)
- [x] First-build stat tutorial overlay activates automatically (stored in localStorage/Zustand)
- [x] Tutorial highlights each stat one at a time: highlight → plain-English explanation → next
- [x] Tutorial has a "Skip" option and a "Got it" button on the last stat
- [x] "?" icon persists on each stat for return visits (tap to see explanation)
- [x] Gemma's Take narrative renders above the pentagon (4-6 sentences, coaching tone)
- [x] Pentagon radar chart animates in with the Stage 2 Reveal sequence from DESIGN.md
- [x] Career detail section shows: title, salary range, ROI indicator, key data points
- [x] Receipts ("?") icons on every data point expand to show provenance
- [x] "Fight the Bosses →" CTA advances to Screen 7 (F4)
- [x] Loading, error, and empty states all handled gracefully
- [x] All Brightpath design tokens used — zero hardcoded colors/spacing/fonts
- [x] Framer Motion animations per DESIGN.md Stage 2 Reveal sequence
- [x] Responsive: desktop primary, mobile functional
- [ ] All tests pass

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Gemma's Take leads before pentagon | Spike analysis proved coaching narrative → numbers is better than numbers first. Student gets the "so what" before the raw data. | Pentagon first (cold data without context), interleaved (too busy) |
| 2 | Tiered career picker, not flat list | 15+ crosswalk matches is overwhelming. Gemma tiering transforms a data dump into guided exploration. Validated in spike. | Flat sorted list (data dump), top-3 only (hides options), search (students don't know what to search for) |
| 3 | Personalized loading, not spinner | Build orchestration takes 2-5 seconds (stat engine + boss fights + branches + guidance). Contextual messages with the student's profile name keep engagement during the wait. | Spinner (anxiety), progress bar (implies predictable duration), skeleton screen (nothing to skeleton yet) |
| 4 | Stat tutorial on first build only | Students need to understand the five-stat system to interpret their pentagon. After the first build, they know. Persistent "?" icons give access later. | Always show tutorial (annoying on repeat), never show (stats are opaque), tooltip on hover (mobile-hostile) |
| 5 | Tiers are guidance not gates | Student can pick any career from any tier. "Stretch" doesn't mean "impossible" — it means "less typical from this program." Avoids limiting student aspiration. | Locked tiers (gates feel punitive), hidden tiers (loses the tiering value), separate pages per tier (too many clicks) |
| 6 | Pentagon animates with DESIGN.md Stage 2 Reveal sequence | This is THE cinematic moment — the signature animation. The 5-step sequence (glow → bear → pentagon → title → stat count-up) is already specified in DESIGN.md. | Instant render (no drama), simple fade (underwhelming), CSS-only animation (no spring physics) |
| 7 | Mock API handlers as fallback | If B1 (FastAPI router wiring) isn't complete, components use mock API handlers that return realistic data shaped to the Pydantic contracts. Swap is a single import change. | Block on B1 (delays frontend), inline mock data (no API integration pattern to swap later) |

### Constraints

- Backend API calls require B1 (FastAPI router wiring) to be complete for real data. Mock handlers ship in this spec as fallback.
- Career outcomes data comes from the backend — frontend does not compute stats.
- Pentagon chart component was created in F1 spec (reused here with real data and the full animation sequence).
- The stat tutorial is a frontend-only concern — no backend state for "has seen tutorial."

---

## §3 UI/UX Design

> @fp-design-visionary fills this section with the premium implementation target.
> Cross-reference DESIGN.md and docs/mockups/brightpath-design-system-v2.html

### Screen 5: Career Pick

**Emotion:** Curious anticipation → empowered choice.

**Layout:** Single column, centered, max-width 720px. Header visible with back arrow + profile name.

**Elements (top to bottom):**

- Step indicator: Space Mono 11px, `text-muted`, letter-spacing 2px, uppercase — "CHOOSE YOUR PATH"
- Screen title: Fredoka 700, `text-display` (36px), `text-primary` — "Where could this degree take you?"
- Subtitle: Nunito 400, `text-body-lg` (18px), `text-secondary` — "Gemma analyzed your program and grouped career paths by how common they are for graduates like you."

- **Tier sections:** Three collapsible sections, all expanded by default.

  **Tier header:**
  - Label: Fredoka 600, `text-heading` (28px), `text-primary`
  - Count badge: `bg-surface`, `rounded-full`, Space Mono `text-data-sm`, `text-muted` — "(4 paths)"
  - Tier description: Nunito 400, `text-small` (14px), `text-secondary`
    - Common: "Where most graduates from this program end up."
    - Less Common: "Realistic paths that take more intention."
    - Stretch: "Possible but atypical — these take extra work to reach."

  **Career cards within tier:**
  - Grid: 1 column on mobile, 2 columns on tablet+. Gap: `space-3` (12px).
  - Card base: `bg-mid`, 1px `border-subtle`, `radius-xl`, padding `space-6` (24px). Hover per DESIGN.md card spec (bg-surface, border-default, shadow-lg, translateY(-2px)).
  - Selected: thrive border glow per DESIGN.md selected card spec.
  - Card content:
    - Top row: occupation title (Nunito 700, `text-body-lg`, `text-primary`) + emoji indicator (from backend, e.g., 💻 🏥 📊)
    - Salary line: Space Mono 400, `text-data`, `text-stat-ern` — "$62,000/yr median"
    - Stat preview pills: 5 small pills in a flex row. Each pill: `bg-surface`, `rounded-sm`, padding 2px 8px. Stat abbreviation (Space Mono, `text-micro`, stat color) + value (Space Mono, `text-micro`, `text-secondary`). Example: `ERN 7` `ROI 5` `RES 4` `GRW 6` `HMN 8`
    - Data completeness indicator: if `data_caveat` exists on the CareerOutcome, show a subtle ⚠️ + `text-muted` note

  **Card selection behavior:**
  - Tap selects (deselects previous). Selected card gets thrive border + glow.
  - On select: card does a subtle `springs.snappy` scale pulse (1 → 1.02 → 1).

- **CTA area (bottom):**
  - Fixed to bottom of viewport on mobile, inline on desktop.
  - Primary button: "See my build ✦" — disabled until a career is selected. Disabled state per DESIGN.md (state-disabled overlay).
  - Below CTA: Nunito 13px, `text-muted` — "You can always come back and pick a different path."

**Entrance animation:**
- Tier headers stagger in: `transitions.fadeInUp`, `stagger.normal` (80ms).
- Career cards within each tier stagger: `stagger.fast` (50ms).
- Total entrance: ~600ms for a full set of 12-15 cards.

### Loading Screen (Between Screen 5 → 6)

**Emotion:** Anticipation building. The machine is working *for you*.

**Layout:** Full viewport, centered content, single column. No header — this is a cinematic interstitial.

**Elements:**

- Background: `bg-void` with ambient glow (stronger than default — `accent-thrive` + `accent-insight` at 25% opacity).
- Profile emoji: 80px, centered, floating animation (translateY 0 → -8px, 3s cycle).
- Loading message: Fredoka 600, `text-heading` (28px), `text-primary`, centered.
  - Messages rotate every 2 seconds with a crossfade (opacity 0 → 1 → 0, 300ms transitions):
    1. "Specing {profile_name} {emoji}..."
    2. "Crunching salary data..."
    3. "Sizing up the bosses..."
    4. "Mapping your branches..."
    5. "Asking Gemma for advice..."
    6. "Almost there..."
  - Messages are contextual — they reference what the backend is actually doing.
- Progress dots: 5 dots (6px circles), `bg-surface`, spaced `space-2`. Fill to `accent-thrive` as stages complete. Pulse animation on the active dot.
- Subtle star particles in background (CSS `twinkle` animation from DESIGN.md).

**Behavior:**
- Appears immediately after career pick CTA.
- Stays until the build orchestration API resolves.
- Minimum display time: 2 seconds (prevents flash if API is fast).
- On API success: loading screen fades out (opacity 1 → 0, 400ms), reveal screen fades in.
- On API error: loading message changes to "Something went wrong — let's try again" with a retry button (secondary style).

### Screen 6: Reveal + Stats

**Emotion:** Awe + pride. THE cinematic moment.

**Layout:** Single column, centered, max-width 800px. Generous vertical spacing between sections.

**The Stage 2 Reveal Sequence (from DESIGN.md):**

This is a choreographed animation sequence. Each step delays from the previous:

1. **Ambient glow pulse (t=0, 0.8s):** Background radial glow intensifies — `accent-thrive` at 30% → 50% over 0.8s, then settles to 25%. Sets the stage.

2. **Character reveal (t=0.5s):** Profile emoji at 120px, `transitions.scaleIn` with `springs.bouncy`. Drop shadow glow in stat colors. Float animation begins after landing.

3. **Career title + salary (t=0.9s):** `transitions.fadeInUp`, `springs.smooth`.
   - Career title: Fredoka 700, `text-display` (36px), `text-primary`.
   - "at {school_name}" subtitle: Nunito 400, `text-body`, `text-secondary`.
   - Salary: Space Mono 700, `text-data-lg` (24px), `text-stat-ern` — "$62,000/yr median".

4. **Pentagon radar chart (t=1.4s):** `transitions.scaleIn` from center, `springs.smooth`.
   - Reuse `PentagonChart.tsx` from F1 with full animation.
   - Grid lines draw in first (stroke-dashoffset, 1.5s).
   - Stat shape draws in (stroke-dashoffset, 2s, 0.3s delay after grid).
   - Vertex dots scale in (stagger 150ms apart, `springs.bouncy`).
   - Stat labels fade in (`stat-label-fade` keyframe, 1s).
   - Stat value numbers count up from 0 simultaneously (Space Mono, stat color, 1.2s duration).

5. **Gemma's Take (t=2.2s):** `transitions.fadeInUp`, `springs.smooth`.

**After the reveal sequence settles:**

**Gemma's Take section:**
- Section label: Space Mono 11px, `text-accent-insight`, letter-spacing 2px, uppercase — "GEMMA'S TAKE"
- Insight icon: `accent-insight` small icon (💡 or custom) to the left of the label.
- Narrative text: Nunito 400, `text-body-lg` (18px), `text-primary`, max-width 640px. 4-6 sentences. Coaching tone.
- Container: `bg-mid`, 1px `border-subtle`, `radius-xl`, padding `space-6`. Left border accent: 3px solid `accent-insight`.
- Receipt icon: "?" circle (20px, `bg-surface`, `text-muted`) at top-right of container. Tap to expand provenance.

**Pentagon detail section (below narrative):**
- Pentagon chart at larger size (280×280 on desktop, 220×220 mobile).
- Stat detail cards: 5 cards in a responsive grid (1 column mobile, 5 columns desktop as a row). Each card:
  - Stat icon (custom per DESIGN.md iconography section)
  - Stat abbreviation: Space Mono 700, `text-data`, stat color.
  - Stat name: Nunito 600, `text-small`, `text-secondary` — e.g., "Earning Power"
  - Stat value: Space Mono 700, `text-data-lg`, stat color — e.g., "7"
  - "?" receipt icon: `bg-surface`, 16px circle, `text-muted`. Tap expands stat provenance.
  - Bar indicator: 4px height, `bg-surface` track, stat-color fill at value/10 width.

**Career detail section:**
- Card: `bg-mid`, `border-subtle`, `radius-xl`, padding `space-6`.
- Sections within:
  - **Salary range:** Space Mono — 25th / median / 75th percentile with effort level highlighted.
  - **ROI indicator:** Computed debt-to-earnings with loan % context. Color-coded (thrive if good, caution if moderate, alert if poor).
  - **Top activities:** Bulleted list from O*NET `top_5_activities`. Nunito 400, `text-small`, `text-secondary`.
  - **AI exposure headline:** RES stat contextualized — "This career has moderate AI exposure" with `accent-insight` highlight.
  - **Substitution notice:** If `substitution_applied` is true on the CareerOutcome, show a subtle info banner explaining that broad CIP data was used. `bg-surface`, `accent-info` left border, `text-small`.

**CTA area:**
- Primary button: "Fight the Bosses →" — Fredoka 600, primary style per DESIGN.md.
- Below: Nunito 13px, `text-muted` — "5 bosses stand between you and your future."

### Stat Tutorial Overlay (First Build Only)

**Trigger:** Activates automatically when the pentagon animation completes on the student's first-ever build. Checked via `hasSeenStatTutorial` flag in Zustand store (persisted to localStorage).

**Layout:** Semi-transparent backdrop (`rgba(18, 19, 31, 0.85)` with `backdrop-blur(8px)`) over the reveal screen. The pentagon remains visible and centered. A spotlight effect highlights each stat vertex in sequence.

**Sequence (5 steps, one per stat):**

For each stat:
1. The corresponding pentagon vertex glows brightly (stat color at full opacity, glow shadow).
2. All other vertices dim to 20% opacity.
3. A tooltip card appears near the highlighted vertex:
   - Card: `bg-raised`, `radius-lg`, padding `space-4`, `shadow-lg`, max-width 280px.
   - Stat name: Fredoka 600, `text-heading`, stat color — e.g., "Earning Power"
   - Stat abbreviation: Space Mono, `text-data-sm`, `text-muted` — "(ERN)"
   - Plain-English explanation: Nunito 400, `text-body-sm`, `text-primary` — from PRD v8 stat table:
     - ERN: "Based on what graduates of this program at this school actually earn."
     - ROI: "Compares your expected earnings to your student debt. Your loan percentage drives this."
     - RES: "How exposed is this career to AI automation? Higher means the work needs humans."
     - GRW: "Is this field growing or shrinking? Based on 10-year job projections."
     - HMN: "How much does this job depend on uniquely human skills?"
   - Data source: Space Mono, `text-micro`, `text-muted` — e.g., "Source: College Scorecard + BLS"
4. Navigation: "Next →" link (Nunito 600, `text-accent-info`) and step dots (1-5).
5. On the last stat (HMN): "Next →" becomes "Got it ✦" (primary button style).

**Skip:** "Skip tutorial" text link in the top-right of the overlay. Nunito 400, `text-small`, `text-muted`. Sets `hasSeenStatTutorial = true` and dismisses.

**Transition between stats:** Tooltip card crossfades (opacity + translateY, `springs.smooth`). Vertex glow transitions smoothly.

**After tutorial:** Overlay fades out (300ms), full reveal screen is interactive. `hasSeenStatTutorial` set to `true`.

### Persistent Stat Help ("?" icons)

After the tutorial (or on subsequent builds), each stat on the pentagon and in the stat detail cards has a small "?" icon. Tapping opens a compact tooltip with the same plain-English explanation + data source. Tooltip uses the same card styling as the tutorial but positioned as a standard popover (DESIGN.md modal spec, but smaller: max-width 280px).

### Receipts

Every numeric data point has a "?" receipt icon. Tapping expands an inline collapsible showing:
- Raw data inputs used
- Thresholds applied
- Source datasets
- Computation method

Receipt expansion: height animates from 0, `springs.smooth`. Content fades in (200ms delay).

Styling: `bg-surface`, 1px `border-subtle`, `radius-md`, padding `space-3`. Content in Space Mono `text-data-sm`, `text-muted`.

### Shared Elements

**Header:** Visible. Back arrow (left). Profile name in `text-secondary` (center — post-reveal brightness per DESIGN.md header spec). Right zone empty.

**Progress bar:** Fill at ~60% on Screen 5 (career pick), ~70% on Screen 6 (reveal). Continues the gradient from F1/F2.

**Page transitions:** Framer Motion AnimatePresence. Enter: opacity 0→1 + translateY 20→0, `springs.smooth`. Exit: opacity 1→0, 200ms.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Tier section | `section-tier-{common\|less-common\|stretch}` | region | "Common career paths" / etc. |
| Career card | `career-{soc-code}` | radio | Occupation title |
| Career card group | `group-career-picker` | radiogroup | "Career path options" |
| Career pick CTA | `btn-build-career` | button | "Build your career path" |
| Loading screen | `region-loading` | status | "Building your career profile" |
| Stat tutorial overlay | `dialog-stat-tutorial` | dialog | "Learn about your stats" |
| Tutorial next button | `btn-tutorial-next` | button | "Next stat" / "Got it" |
| Tutorial skip | `btn-tutorial-skip` | button | "Skip tutorial" |
| Pentagon chart | `svg-pentagon` | img | "Five-stat radar chart showing your career stats" |
| Stat detail card | `stat-{ern\|roi\|res\|grw\|hmn}` | article | "{Stat Name}: {value} out of 10" |
| Stat help trigger | `btn-stat-help-{stat}` | button | "Learn about {Stat Name}" |
| Receipt trigger | `btn-receipt-{id}` | button | "View data source for {label}" |
| Receipt panel | `panel-receipt-{id}` | region | "Data provenance for {label}" |
| Gemma's Take | `region-gemma-take` | article | "Gemma's career analysis" |
| Fight bosses CTA | `btn-fight-bosses` | button | "Fight the Bosses" |

---

## §4 Technical Specification

### Architecture Overview

This spec introduces the first real API-consuming screens. The career picker calls the build/tiering endpoint; the loading screen orchestrates the full build pipeline; the reveal screen displays the Build object. This is also the first screen to use the full Stage 2 Reveal animation sequence and the stat tutorial system.

The Pentagon chart component from F1 is reused here with real data and the full animation sequence.

### API Endpoints Consumed

| Endpoint | Method | Request | Response | Used By |
|---|---|---|---|---|
| `/build` | POST | `{ unitid, cipcode, effort, loan_pct }` | `{ outcomes: CareerOutcome[], tiers: { common: [...], less_common: [...], stretch: [...] } }` | Career picker — populates tier sections |
| `/build` | POST | `{ unitid, cipcode, effort, loan_pct, selected_soc }` | `Build` (full build object) | Loading screen — triggers full orchestration |
| (alternative) `/build/{id}/guidance` | POST | `{ build_id }` | `{ narrative: str }` | If guidance is fetched separately |

**Note:** The exact endpoint shape depends on B1 (FastAPI router wiring). The proposed API table in PRD v8 shows `POST /build` returning outcomes + tiers. A second call with `selected_soc` triggers the full build. If B1 implements this differently, the API layer abstraction (see below) absorbs the difference.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/CareerPickPage.tsx` | Create | Screen 5: tiered career picker |
| `frontend/src/pages/RevealPage.tsx` | Create | Screen 6: stat reveal with Gemma's Take |
| `frontend/src/components/CareerTierSection.tsx` | Create | Collapsible tier section with career cards |
| `frontend/src/components/CareerCard.tsx` | Create | Individual career option card |
| `frontend/src/components/LoadingScreen.tsx` | Create | Personalized loading interstitial |
| `frontend/src/components/StatTutorial.tsx` | Create | First-build stat tutorial overlay |
| `frontend/src/components/StatDetailCard.tsx` | Create | Individual stat card with value + bar + receipt |
| `frontend/src/components/GemmaTake.tsx` | Create | Gemma's Take narrative container |
| `frontend/src/components/CareerDetail.tsx` | Create | Career detail section (salary, ROI, activities, AI exposure) |
| `frontend/src/components/ReceiptPanel.tsx` | Create | Expandable data provenance panel |
| `frontend/src/components/StatHelpTooltip.tsx` | Create | Persistent "?" stat explanation popover |
| `frontend/src/api/build.ts` | Create | API client functions for build endpoints (with mock fallback) |
| `frontend/src/api/mockBuild.ts` | Create | Mock API handlers returning realistic Build/CareerOutcome shapes |
| `frontend/src/data/statExplanations.ts` | Create | Plain-English stat explanations + data sources (from PRD v8) |
| `frontend/src/stores/buildStore.ts` | Modify | Add: `selectedCareer`, `build` (Build object), `hasSeenStatTutorial`, `isLoading`, `loadingStage` |
| `frontend/src/types/build.ts` | Modify | Add TypeScript types matching Pydantic models: `CareerOutcome`, `PentagonStats`, `Build`, `BossFightResult`, `GauntletResult`, `CareerBranch`, `AppliedSkill` |
| `frontend/src/App.tsx` | Modify | Add routes: `/career-pick`, `/reveal` |

### Data Model Additions

```typescript
// types/build.ts — additions (shapes match Pydantic models in backend/app/models/career.py)

interface PentagonStats {
  ern: number | null;  // 1-10
  roi: number | null;
  res: number | null;
  grw: number | null;
  hmn: number | null;
}

interface BossScores {
  fight_ai: number | null;
  fight_loans: number | null;
  fight_market: number | null;
  fight_burnout: number | null;
  fight_ceiling: number | null;
}

interface CareerOutcome {
  stats: PentagonStats;
  bosses: BossScores;
  soc_code: string;
  occupation_title: string;
  median_annual_wage: number | null;
  debt_to_earnings_annual: number | null;
  top_5_activities: string[];
  burnout_drivers: string[];
  substitution_applied: boolean;
  data_caveat: string | null;
}

interface TieredCareers {
  common: CareerOutcome[];
  less_common: CareerOutcome[];
  stretch: CareerOutcome[];
}

interface BossFightResult {
  boss: string;
  result: 'win' | 'lose' | 'draw';
  raw_score: number;
  threshold_win: number;
  threshold_draw: number;
  reason: string;
  narrative: string | null;
  rerolled: boolean;
  reroll_count: number;
  original_result: string | null;
}

interface GauntletResult {
  fights: BossFightResult[];
  wins: number;
  losses: number;
  draws: number;
  verdict: string;
}

interface CareerBranch {
  from_soc: string;
  to_soc: string;
  to_title: string;
  delta_ern: number | null;
  delta_roi: number | null;
  delta_res: number | null;
  delta_grw: number | null;
  delta_hmn: number | null;
  unlock: string | null;
}

interface AppliedSkill {
  id: string;
  title: string;
  rationale: string;
  targets: string[];
  delta_ern: number;
  delta_roi: number;
  delta_res: number;
  delta_grw: number;
  delta_hmn: number;
  delta_burnout_raw: number;
  delta_ceiling_raw: number;
}

interface Build {
  build_id: string;
  profile_name: string;
  school_name: string;
  unitid: string;
  major_text: string;
  cipcode: string;
  effort: string;          // 'working' | 'balanced' | 'all_in'
  loan_pct: number;        // 0 | 25 | 50 | 75 | 100
  career: CareerOutcome;
  gauntlet: GauntletResult;
  branches: CareerBranch[];
  skill_recs: string[];
  guidance: string;         // Gemma's Take narrative
  skills_crafted: AppliedSkill[];
  skill_pool: AppliedSkill[];
  next_steps: string;
}
```

### Zustand Store Additions

```typescript
// stores/buildStore.ts — additions

interface BuildStore {
  // ... existing from F1/F2 ...

  // Screen 5
  tieredCareers: TieredCareers | null;
  selectedCareer: CareerOutcome | null;
  setTieredCareers: (tiers: TieredCareers) => void;
  setSelectedCareer: (career: CareerOutcome | null) => void;

  // Loading
  isBuilding: boolean;
  buildingStage: number;  // 0-5 maps to loading messages
  setIsBuilding: (building: boolean) => void;
  setBuildingStage: (stage: number) => void;

  // Screen 6
  build: Build | null;
  setBuild: (build: Build) => void;

  // Tutorial
  hasSeenStatTutorial: boolean;
  setHasSeenStatTutorial: (seen: boolean) => void;
}
```

`hasSeenStatTutorial` is persisted to localStorage via Zustand's `persist` middleware (already set up in F1 if not, add here).

### API Client

```typescript
// api/build.ts

import { mockGetTieredCareers, mockCreateBuild } from './mockBuild';

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === 'true';

export async function getTieredCareers(
  unitid: string,
  cipcode: string,
  effort: string,
  loanPct: number
): Promise<TieredCareers> {
  if (USE_MOCK) return mockGetTieredCareers(unitid, cipcode, effort, loanPct);
  const res = await fetch('/api/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ unitid, cipcode, effort, loan_pct: loanPct }),
  });
  if (!res.ok) throw new Error(`Build failed: ${res.status}`);
  const data = await res.json();
  return data.tiers;
}

export async function createBuild(
  unitid: string,
  cipcode: string,
  effort: string,
  loanPct: number,
  selectedSoc: string
): Promise<Build> {
  if (USE_MOCK) return mockCreateBuild(unitid, cipcode, effort, loanPct, selectedSoc);
  const res = await fetch('/api/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ unitid, cipcode, effort, loan_pct: loanPct, selected_soc: selectedSoc }),
  });
  if (!res.ok) throw new Error(`Build failed: ${res.status}`);
  return res.json();
}
```

### Routing Additions

```
/career-pick  → CareerPickPage     (Screen 5)
/reveal       → RevealPage         (Screen 6)
```

Navigation guard: `/career-pick` requires school + major + effort + loan_pct in store. If missing, redirect to the appropriate earlier screen. `/reveal` requires a `build` object in store. If missing, redirect to `/career-pick`.

### Service Changes

- Add `framer-motion` import for AnimatePresence + motion components (should already be a dependency from F1)
- No backend changes in this spec
- No new npm dependencies beyond what F1/F2 established

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `stores/buildStore.test.ts` | Store state tests | Medium | Store shape is being extended with new fields |
| `App.test.tsx` | Routing tests | Medium | New routes being added |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `buildStore.test.ts` | Extend with new field tests | Store grows to include career pick, build, tutorial state |
| `App.test.tsx` | Add route assertions for `/career-pick` and `/reveal` | New routes |

#### Confirmed Safe

- All backend tests (no backend changes)
- F1/F2 component tests (no modifications to those components)
- Design token files (no changes)

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `pages/CareerPickPage.test.tsx` | renders tiered career list | Three tier sections render with career cards |
| P0 | `pages/CareerPickPage.test.tsx` | career selection updates store | Click career card → selectedCareer updates in store |
| P0 | `pages/CareerPickPage.test.tsx` | CTA disabled without selection | Build button disabled until a career is picked |
| P0 | `pages/RevealPage.test.tsx` | renders reveal with build data | Pentagon, Gemma's Take, career detail all present |
| P0 | `components/LoadingScreen.test.tsx` | renders loading messages | Profile name in message, messages cycle |
| P0 | `components/StatTutorial.test.tsx` | shows on first build | Tutorial appears when hasSeenStatTutorial is false |
| P0 | `components/StatTutorial.test.tsx` | skips on subsequent builds | Tutorial does not appear when hasSeenStatTutorial is true |
| P1 | `components/StatTutorial.test.tsx` | skip button sets flag | Click skip → hasSeenStatTutorial becomes true |
| P1 | `components/StatTutorial.test.tsx` | navigates through all 5 stats | Click next 5 times → reaches "Got it" → dismisses |
| P1 | `components/CareerCard.test.tsx` | renders career data | Title, salary, stat pills present |
| P1 | `components/GemmaTake.test.tsx` | renders narrative | Narrative text and insight label present |
| P1 | `components/ReceiptPanel.test.tsx` | expands on click | Click "?" → receipt content visible |
| P1 | `components/StatDetailCard.test.tsx` | renders stat with bar | Stat name, value, bar indicator present |
| P2 | `api/build.test.ts` | mock API returns valid shapes | Mock handlers return data matching TypeScript types |
| P2 | `pages/CareerPickPage.test.tsx` | handles API error | Error state renders retry option |
| P2 | `pages/RevealPage.test.tsx` | receipt icons present | Every data point has a "?" icon |

#### Test Data Requirements

- Mock `TieredCareers` fixture with 3-4 common, 3 less common, 2 stretch careers
- Mock `Build` fixture with full pentagon stats, gauntlet results, guidance narrative, branches
- Mock career outcome with `substitution_applied: true` for substitution notice test
- Mock career outcome with `data_caveat` for caveat indicator test
- Zustand store can be tested directly; component tests should use a test wrapper that provides store context

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-13

#### System Context

F3 introduces the first real API-consuming frontend screens. It sits at the boundary between the Zustand state layer, the FastAPI backend (B1), and the cinematic reveal animation system. The spec touches three layers: (1) frontend routing and state management, (2) API client abstraction with mock fallback, and (3) TypeScript type definitions that must mirror Pydantic models in `backend/app/models/career.py`. No pipeline or Gold zone changes. No Gemma role changes. The data flow is: existing Zustand store (school/major/effort/loans) -> API call -> backend build orchestration -> Build response -> Zustand store -> reveal components.

#### Data Flow Analysis

**Screen 5 (Career Pick):**
- `buildInputStore` has school, major, effort, loans from F2.
- Frontend calls `POST /build/outcomes` (unitid, cipcode, effort, loan_pct) -> gets `CareerOutcome[]`.
- Then calls `POST /build/tier` (outcomes, school_name, program_name, cipcode) -> gets tiered dict.
- Student selects a career -> stored in new `selectedCareer` state.

**Loading -> Screen 6 (Reveal):**
- Frontend calls `POST /build` (full `BuildRequest`) -> gets `Build` object.
- Build stored in Zustand -> reveal screen renders.

This two-step flow (outcomes+tier, then build) matches the existing backend router layout. The spec's API table in section 4, however, shows a simplified single-endpoint model that does not match the actual backend.

#### Contract Review

Compared the spec's TypeScript interfaces against `backend/app/models/career.py` Pydantic models. Found several misalignments (detailed below).

#### Findings

##### Sound

1. **Mock API fallback pattern.** The `VITE_USE_MOCK_API` env var toggle is clean. A single import change swaps mock for real. This is the right pattern for unblocking frontend work while B1 stabilizes.

2. **Store separation.** Keeping `buildInputStore` (inputs) separate from the new build state (outputs) is correct. Inputs are user-driven; outputs are API-driven. Different lifecycles.

3. **Navigation guards.** The spec correctly requires prerequisite state for each route (`/career-pick` needs school+major+effort+loans, `/reveal` needs a build). This prevents broken deep-links.

4. **Component decomposition.** 13 components is the right granularity. Each has a single responsibility. `CareerTierSection` wraps `CareerCard`s. `RevealPage` composes `GemmaTake`, `StatDetailCard`, `CareerDetail`, `ReceiptPanel`. No god components.

5. **Tutorial as frontend-only state.** `hasSeenStatTutorial` in localStorage-persisted Zustand is the right call. No backend round-trip needed for a UI-only preference.

6. **Reuse of PentagonChart from F1.** Correct architectural choice -- extend existing component with real data binding rather than building a new one.

##### Concerns

- **C1: TypeScript types diverge from Pydantic models in 6 places.**
  The spec's `types/build.ts` interfaces do not match `backend/app/models/career.py` in several fields:

  | Field | Spec (TS) | Pydantic (Python) | Impact |
  |-------|-----------|-------------------|--------|
  | `Build.profile_name` | present | **absent** | Frontend expects a field that the backend does not return |
  | `Build.unitid` | `string` | `int` | Type mismatch -- unitid is numeric everywhere else in the system |
  | `Build.effort` | `string` (loosely typed) | `EffortLevel` (5-value Literal) | Spec shows only 3 values (`working`, `balanced`, `all_in`) but the system has 5 |
  | `Build.program_name` | **absent** | present | Backend returns it, spec omits it |
  | `Build.created_at` | **absent** | present | Backend returns it, spec omits it |
  | `Build.skill_recs` | `string[]` | `list[SkillRec]` (object with title, stat_impact, rationale) | Structural mismatch -- backend returns objects, spec expects strings |
  | `BossScores` keys | `fight_ai`, `fight_loans`, etc. | `ai`, `loans`, etc. | Key name mismatch -- backend uses short keys |
  | `CareerOutcome.top_5_activities` | `string[]` | `list[dict[str, object]]` | Backend returns dicts (activity name + score), not plain strings |
  | `CareerOutcome.burnout_drivers` | `string[]` | `list[dict[str, object]]` | Same as above |
  | `CareerOutcome.data_caveat` | `string \| null` | `dict[str, object] \| null` | Backend returns a dict, not a string |
  | `BossFightResult.boss` | `string` | `BossId` (5-value Literal) | Loose typing vs. constrained Literal |
  | `BossFightResult.narrative` | `string \| null` | `str` (default `""`) | Nullable vs. empty-string default -- minor but affects null checks |
  | `GauntletResult.unknown` | **absent** | present (count of `unknown` outcomes) | Missing field |

  **Impact:** Mock data shaped to the spec will not parse when swapped to real API responses. The entire mock-to-real swap -- the spec's core derisking strategy -- breaks on day one.
  **Recommendation:** Regenerate `types/build.ts` directly from the Pydantic models in `backend/app/models/career.py`. Every interface should be a 1:1 mirror. Use the Pydantic model as the source of truth, not the spec prose.

- **C2: API endpoint signatures do not match existing backend routers.**
  The spec proposes `POST /build` with `{ unitid, cipcode, effort, loan_pct }` returning `{ outcomes, tiers }`. The actual backend has:
  - `POST /build/outcomes` (OutcomesRequest) -> `CareerOutcome[]`
  - `POST /build/tier` (TierRequest with full outcomes list) -> tiered dict
  - `POST /build` (BuildRequest with 11 fields including profile_name, school_name, cip_title, selected_title) -> `Build`

  The spec's simplified API signatures will not work against the real backend. The `getTieredCareers` function needs to make two calls (outcomes then tier), not one. The `createBuild` function is missing required fields (profile_name, school_name, cip_title, selected_title, student_major).
  **Impact:** When `VITE_USE_MOCK_API` is flipped to false, every API call 404s or 422s.
  **Recommendation:** Update `api/build.ts` to match the actual router signatures. `getTieredCareers` should call `/build/outcomes` then `/build/tier`. `createBuild` should send a full `BuildRequest` matching `backend/app/models/api.py`. Document the two-step flow explicitly.

- **C3: Store location inconsistency.**
  The spec references `stores/buildStore.ts` (plural `stores/`), but the existing codebase uses `store/buildInputStore.ts` (singular `store/`). The spec also proposes a new file name (`buildStore.ts`) while the existing file is `buildInputStore.ts`.
  **Impact:** Either the implementer creates a parallel store in a new directory (breaking consistency), or they modify the existing file but the spec's instructions don't match.
  **Recommendation:** Clarify: is this a new store (`store/buildStore.ts`) separate from `store/buildInputStore.ts`, or an extension of the existing store? Given the different lifecycles (inputs vs. outputs), a separate `store/buildStore.ts` in the existing `store/` directory is the right call. State this explicitly and use the `store/` path (singular).

- **C4: `AppliedSkill.targets` typed as `string[]` but Pydantic uses `list[BossId]`.**
  The TS interface shows `targets: string[]` but the backend constrains this to a 5-value union (`"ai" | "loans" | "market" | "burnout" | "ceiling"`). The spec should use a TS union type here for type safety.
  **Impact:** Low -- runtime works, but loses compile-time protection on boss IDs.
  **Recommendation:** Define `type BossId = "ai" | "loans" | "market" | "burnout" | "ceiling"` in `types/build.ts` and use it for `targets` and `BossFightResult.boss`.

- **C5: The `fetch` calls in `api/build.ts` bypass the existing `apiPost` helper.**
  The spec's API client code uses raw `fetch()` instead of the established `apiPost` from `api/client.ts`. The existing helper handles error parsing, base URL configuration, and JSON headers.
  **Impact:** Duplicated error handling logic. If the API base URL changes, the new endpoints break while existing ones work.
  **Recommendation:** Use `apiPost` from `api/client.ts` for all API calls. The mock branch can still short-circuit before calling `apiPost`.

##### Blockers

None. The concerns are all fixable within the spec before implementation begins.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions

1. **Regenerate TypeScript interfaces from Pydantic models (C1).** Every interface in `types/build.ts` must mirror the corresponding Pydantic model in `backend/app/models/career.py` field-for-field, including types, optionality, and default values. Specifically fix: `Build.unitid` (int not string), `Build.skill_recs` (SkillRec objects not strings), `BossScores` keys (drop `fight_` prefix), `CareerOutcome.top_5_activities` and `burnout_drivers` (dict arrays not string arrays), `CareerOutcome.data_caveat` (dict not string), add missing `Build.created_at`, `Build.program_name`, `GauntletResult.unknown`.
2. **Align API client with actual backend router signatures (C2).** Update `api/build.ts` to call `/build/outcomes` then `/build/tier` for tiering, and send a full `BuildRequest` for build creation. Use `apiPost` from `api/client.ts` (C5).
3. **Clarify store file location and naming (C3).** Specify `store/buildStore.ts` (singular `store/` directory, new file separate from `buildInputStore.ts`).

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline changes — frontend consuming existing API contracts)

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
[Filled in by @design-builder — Brightpath token compliance, DESIGN.md Stage 2 Reveal fidelity, responsive behavior, animation springs]

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

**Context for agents:**

- **DESIGN.md is the source of truth** for all visual decisions. Read it before writing any UI code. If DESIGN.md and existing code disagree, DESIGN.md wins.
- **The Stage 2 Reveal sequence** is the signature animation of the entire product. The 5-step choreography (glow → character → pentagon → title → stat count-up) is specified in DESIGN.md's "Key Animation Sequences" section. Match it precisely.
- **Pentagon chart** was created in F1 — reuse it. This spec adds the full animation sequence and real data binding.
- **The stat tutorial** is the student's first encounter with the five-stat system. The plain-English explanations are from PRD v8's stat table. Get the tone right: empowering, not academic.
- **Mock API handlers** must return data shaped exactly like the Pydantic models in `backend/app/models/career.py`. The swap from mock to real API should be a single env var change (`VITE_USE_MOCK_API`).
- **Receipts** are a differentiator — "we show you where every number came from." Implement them on every numeric data point, not just stats.
- **Emotional target:** This screen is the payoff for all the input screens. It should feel like unwrapping a gift, not reading a spreadsheet. The animation sequence, the coaching narrative before raw numbers, the progressive reveal — all serve this emotional target.

---
