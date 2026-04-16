# Feature: Boss Gauntlet + Next Steps (Screen 7)

## Claude Code Prompt

```
Read the spec at docs/specs/screen-boss-gauntlet.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, routing, state management, API integration)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes — gauntlet/skill APIs exist and are consumed as-is)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 mockups and propose the premium implementation
   - Visionary validates Brightpath token usage, boss fight animation sequences, reroll interaction flow, responsive behavior
   - Cross-reference DESIGN.md (source of truth) and docs/mockups/brightpath-design-system-v2.html (visual proof)
   - Special focus: boss fight entrance choreography, win/lose/draw result animations, reroll flow transitions, structural loss emotional weight
   - Writes to §3 with any enhancements or adjustments

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code
   - Implement all components as React with Framer Motion animations
   - Wire up API calls to FastAPI endpoints via apiPost/apiGet helpers (or mock handlers if APIs unavailable)
   - Use Brightpath design tokens exclusively — no hardcoded colors, spacing, or typography
   - The boss fight sequence is cinematic — each fight should feel like an encounter, not a data table row
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - Each component: renders, interactions work, state updates correctly
   - Boss fight sequence: correct fight order, result animations fire, narrative renders
   - Reroll flow: skill selection, equip, rescore, result change
   - Structural loss: renders when pool exhausted
   - Next Steps: renders four sections, markdown content
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance across all components
   - Confirm: dark backgrounds, boss colors per DESIGN.md, correct fonts, token-only colors, responsive behavior, animation springs
   - Confirm: boss fight entrance sequence matches DESIGN.md "Boss Fight Entrance" choreography
   - Writes findings to §8

6. CODE REVIEW
   - Invoke @faing-staff-engineer to review implementation + tests
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
   - Generate report to reports/screen-boss-gauntlet-YYYY-MM-DD.md
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
| Created | 2026-04-14 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-14 |
| Blocked By | B1 (FastAPI routers — DONE), F3 (career pick + reveal — DONE) |
| Related Specs | `screen-career-pick-reveal` (F3, IMPLEMENTATION), `screen-branch-tree` (F5, not started) |

---

## §1 Feature Description

### Overview

Build Screen 7 of the FutureProof flow: the boss gauntlet, the reroll mechanic, and the post-gauntlet Next Steps checklist. This is the product's core interactive system — the student fights five bosses representing real career threats, gets opportunities to improve losing outcomes by equipping skills, encounters structural loss messaging when gaps can't be fixed, and leaves with a concrete action checklist they can print and bring to a counselor or parent.

The gauntlet is a sequential experience, not a dashboard. Each boss fight is its own encounter: entrance animation, result revelation, narrative coaching, and (on loss/draw) the reroll flow. After all five fights resolve, a Final Boss verdict summarizes the gauntlet, and Gemma generates the Next Steps checklist.

### Emotional Target

**Tension + fun.** Boss fights are funny-scary, not terrifying. Losses teach; wins celebrate. The reroll mechanic transforms passive scorecard reading into an interactive coaching moment. Structural loss is the most honest thing the product says — and the moment the student might consider a different build.

### Problem Statement

The student has completed the reveal screen (Screen 6) and has a full Build object with pentagon stats, career detail, and Gemma's Take narrative. The build already includes a pre-computed `gauntlet` (5 fight results) and a `skill_pool` (personalized reroll skills). The student now needs to:

1. **Experience each boss fight sequentially** — not as a data table, but as a cinematic encounter with entrance animation, result reveal, and coaching narrative
2. **Interact with losing fights** via the reroll mechanic — browse available skills, equip them, see the fight rescore live, and experience the outcome flip
3. **Hit structural loss** when the skill pool is exhausted — the gap isn't fixable, and that's the most important signal
4. **See the Final Boss verdict** — the aggregate assessment of the build
5. **Read the Next Steps checklist** — Gemma-generated, RPG-free, actionable, data-grounded

### CLI → Frontend Mapping

| CLI Function | This Spec | What It Does |
|---|---|---|
| `_run_gauntlet_interactive()` | Gauntlet sequence | Sequential boss fights with reroll loops |
| `_display_boss_fight()` | BossFightCard component | Single fight: result, narrative, reroll trigger |
| `_reroll_loop()` | RerollFlow component | Skill browse → equip → rescore → result change |
| `_display_structural_loss()` | StructuralLoss component | Pool exhausted messaging |
| `_display_gauntlet_summary()` | GauntletSummary component | Final Boss verdict + W/L/D tally |
| `_display_next_steps()` | NextSteps component | Post-gauntlet action checklist |

### Key Design Decision: Pre-Computed vs. Live API

The Build object returned from the F3 reveal already contains `gauntlet` (all 5 fight results with narratives) and `skill_pool` (all reroll skills). The frontend does NOT need to call the gauntlet API to get initial fight results — they're already in the store.

The frontend DOES call APIs for:
- **Reroll rescore** (`POST /build/{id}/reroll`) — when the student equips skills and wants to rescore a fight
- **Next Steps** (`POST /build/{id}/next-steps`) — when the gauntlet completes, fetch the action checklist

This means the boss fight sequence can be entirely offline/animated from pre-computed data. Only the reroll interaction and next steps require live API calls. This is important for latency — the cinematic sequence is never waiting on Gemma.

### Success Criteria

- [ ] Sequential boss fight experience: 5 fights presented one at a time, not as a grid/table
- [ ] Each fight shows: boss emoji + name, result (win/lose/draw pill), raw score context, and coaching narrative
- [ ] Boss fight entrance animation per DESIGN.md: vignette → boss bounces in → result reveal
- [ ] Win animation: green burst (scale pulse)
- [ ] Lose animation: screen shake
- [ ] Draw animation: caution glow pulse
- [ ] Boss colors per DESIGN.md boss color tokens (🤖 purple, 💰 amber, 📈 blue, 🔥 pink, 📊 muted)
- [ ] On loss or draw: reroll CTA appears ("Equip skills to fight again")
- [ ] Reroll flow: skill cards with stat deltas, equip toggle, "Rescore" button
- [ ] Reroll rescore calls `POST /build/{id}/reroll` and shows result change animation
- [ ] Skills are build-wide: equipping a skill for Fight AI shows its delta impact on all subsequent fights
- [ ] Structural loss renders when the skill pool for a boss is exhausted and result is still lose/draw
- [ ] "Skip" option on every reroll — student can accept the loss and move to the next fight
- [ ] Final Boss (Fight the Future ⚔️) verdict renders after all 5 fights with aggregate W/L/D
- [ ] "Next Steps" button triggers `POST /build/{id}/next-steps` API call
- [ ] Next Steps checklist renders four markdown sections with the RPG-free checklist
- [ ] Next Steps has a loading state (Gemma inference takes 2-5s)
- [ ] CTA to advance to Screen 8 (branch tree): "See Where This Path Leads →"
- [ ] Receipt ("?") icons on every boss fight score expand to show fight provenance
- [ ] Header dimmed to 60% during gauntlet per DESIGN.md cinematic states
- [ ] All Brightpath design tokens used — zero hardcoded colors/spacing/fonts
- [ ] Framer Motion animations per DESIGN.md boss fight entrance + motion.ts presets
- [ ] Responsive: desktop primary, mobile functional
- [ ] All tests pass

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Sequential fight presentation, not grid | Each fight is an encounter with its own emotional arc. A grid reduces the gauntlet to a data table. The CLI proved sequential works — students engage more when they don't see all results at once. | Grid of 5 cards (no drama), accordion (collapsed fights feel hidden), tabbed (arbitrary division) |
| 2 | Pre-computed gauntlet, live reroll | The Build object already has gauntlet results and skill_pool from the F3 build orchestration. No reason to re-call the gauntlet API. Rerolls are the only live API calls — they mutate the build server-side. | Lazy-load each fight (unnecessary latency), re-fetch entire gauntlet (redundant), client-side reroll (loses server state) |
| 3 | Reroll loop is per-fight, not batch | Student processes one loss at a time. Equip skills, see the result change, move to next fight. Batch reroll ("equip all skills, then rescore everything") loses the teaching moment per fight. | Batch equip (loses per-fight coaching), auto-equip best skills (removes student agency), no reroll (passive scorecard) |
| 4 | Structural loss is an explicit state, not hidden | When the pool is exhausted and the result is still a loss, the product says so directly. This is not a failure state — it's the most important coaching signal. The messaging is empowering and honest, not doom. | Hide the exhaustion (dishonest), keep looping with no skills (confusing), auto-advance (student misses the insight) |
| 5 | Next Steps loads after gauntlet, not pre-fetched | The Next Steps call uses the final state of the build (including any rerolled fights and crafted skills). Pre-fetching before the gauntlet would miss reroll outcomes. | Pre-fetch with build data (misses rerolls), skip Next Steps entirely (loses the real-world deliverable) |
| 6 | Header dims during gauntlet | DESIGN.md specifies 60% header dimming during boss fights. This creates a cinematic focus — the gauntlet owns the screen. Header re-brightens after gauntlet completes. | Full header (competes with boss fights), hidden header (disorienting), no change (misses the cinematic opportunity) |
| 7 | Fight the Future is presentation-only | The Final Boss is a composite verdict from the 5 mini-boss results. There's no separate scoring or reroll for the Final Boss. It's the gauntlet summary, delivered with boss fight gravitas. | Scorable Final Boss (redundant with mini-bosses), skip Final Boss (loses the narrative capstone) |
| 8 | Progress indicator shows fight count | "Fight 2 of 5" keeps the student oriented without spoiling upcoming bosses. The progress element is minimal — this isn't a wizard. | No progress (student doesn't know how many remain), boss names listed (spoils sequence), progress bar (wizard feel) |

### Constraints

- The Build object from F3 contains `gauntlet.fights[]` and `skill_pool[]`. Both are pre-computed — the gauntlet sequence reads from store, not from fresh API calls.
- Reroll API (`POST /build/{id}/reroll`) requires `boss_id` and `skill_ids[]`. Returns a single `BossFightResult` with updated scores. The caller must update the fight in the local `gauntlet.fights[]` array and recompute W/L/D totals.
- Next Steps API (`POST /build/{id}/next-steps`) returns `{ checklist: string }` — a markdown string with four `##` sections.
- Skills are build-wide: equipping a skill mutates the career stats server-side. All subsequent fights that share affected stats will see different raw scores on rescore. The frontend must reflect this.
- The Zustand `buildStore` already has the `Build` object. This spec adds gauntlet-specific state (current fight index, reroll state, next steps content).

---

## §3 UI/UX Design

> @fp-design-visionary fills this section with the premium implementation target.
> Cross-reference DESIGN.md and docs/mockups/brightpath-design-system-v2.html

### Screen 7: Boss Gauntlet

**Emotion arc:** Anticipation → tension → relief/pride (per fight) → empowerment (next steps).

**Layout:** Full viewport, single column, centered content, max-width 640px. The gauntlet owns the screen — header dims to 60% per DESIGN.md cinematic states.

**Overall structure:** The gauntlet is a state machine with these phases:

```
INTRO → FIGHT_1 → FIGHT_2 → FIGHT_3 → FIGHT_4 → FIGHT_5 → FINAL_BOSS → NEXT_STEPS → COMPLETE
```

Each FIGHT_N phase has sub-states: `entrance → result → (reroll_flow?) → resolved`.

### Gauntlet Intro

**Duration:** 1.5s, auto-advances. Sets the mood.

**Elements:**
- Background: `bg-void` with ambient glow dimming to 40% opacity (the lights go down).
- Step indicator: Space Mono 11px, `text-muted`, uppercase, letter-spacing 2px — "THE GAUNTLET"
- Title: Fredoka 700, `text-display` (36px), `text-primary` — "5 threats stand between you and your future."
- Profile emoji: 60px, centered, subtle pulse animation (`springs.gentle`).
- Fight count preview: 5 small circles (12px), `bg-surface`, spaced `space-2`, in a horizontal row. Each represents a fight — they'll fill with result colors as fights resolve.

**Animation:** Title fades in (`transitions.fadeInUp`, delay 0.3s), circles stagger in (`stagger.fast`). After 1.5s, auto-advance to Fight 1 with a crossfade.

### Individual Boss Fight

Each fight has four visual phases:

#### Phase 1: Boss Entrance (0.8s)

- **Vignette:** Radial gradient overlay from transparent center to `rgba(18, 19, 31, 0.7)` edges. Fades in over 0.3s per `bossFight.vignette` in motion.ts.
- **Boss card:** Centered vertically and horizontally.
  - Boss emoji: 80px, centered. Drops in from y:-60 with `springs.bouncy` per `bossFight.bossEntrance`.
  - Boss name: Fredoka 700, `text-display` (36px), boss color (per DESIGN.md boss colors). Fades in at t=0.3s.
  - Boss subtitle: Nunito 400, `text-body` (16px), `text-secondary`. Describes what the boss tests:
    - 🤖 Fight AI: "How safe is this career from automation?"
    - 💰 Fight Student Loans: "Can your earnings handle the debt?"
    - 📈 Fight the Market: "Is this field growing or shrinking?"
    - 🔥 Fight Burnout: "How sustainable is this work long-term?"
    - 📊 Fight the Ceiling: "How high can your earnings go?"
  - Ambient glow: Radial gradient in boss color at 15% opacity behind the emoji. Breathing animation (4s cycle).
- **Fight progress:** At top of screen. The 5 circles from intro — resolved fights show result color fills (thrive=win, alert=lose, caution=draw), current fight circle pulses in boss color, future fights remain `bg-surface`.

#### Phase 2: Result Reveal (0.6s)

After the boss entrance settles (0.5s pause for drama):

- **Result pill:** Appears below the boss subtitle. Uses pill component from DESIGN.md:
  - WIN: `pill-thrive` — "WIN ✦"
  - LOSE: `pill-alert` — "LOSS"
  - DRAW: `pill-caution` — "DRAW"
  - UNKNOWN: `pill-info` — "NO DATA"

- **Result animation:**
  - WIN: `bossFight.winBurst` — scale pulse 1 → 1.15 → 1 on the boss emoji. Green glow burst on the result pill. Confetti-like particle burst (3-4 small thrive-colored dots that scale up and fade, 0.6s).
  - LOSE: `bossFight.loseShake` — x shake on the entire fight card. Alert glow flash on background. Boss emoji dims slightly (opacity 0.7 → 1 over 0.5s).
  - DRAW: Caution glow pulse on the result pill (opacity 0.5 → 1 → 0.5, 1s, once). Boss emoji wobbles (rotate -3deg → 3deg → 0, 0.4s).
  - UNKNOWN: Subtle fade-in only, `text-muted` pill.

- **Score context:** Below the result pill. Space Mono, `text-data-sm` (13px), `text-muted`.
  - Format: "Score: {raw_score} (win ≥ {threshold_win}, draw ≥ {threshold_draw})"
  - Receipt "?" icon: 16px circle, `bg-surface`, `text-muted`. Tap to expand fight receipt (ReceiptPanel component from F3).

- **Coaching narrative:** Below score context. Nunito 400, `text-body` (16px), `text-primary`. The Gemma-generated narrative (3-4 sentences). Container: `bg-mid`, 1px `border-subtle`, `radius-lg`, padding `space-4`. Left border accent: 3px solid boss color. Fades in at t=0.3s after result pill.

#### Phase 3: Reroll Flow (conditional — loss or draw only)

If the fight result is LOSE or DRAW, the reroll flow appears below the narrative after a 0.5s delay.

**Reroll CTA:**
- Container: `bg-mid`, `border-subtle`, `radius-xl`, padding `space-6`.
- Heading: Fredoka 600, `text-heading` (28px), `text-primary` — "Equip skills to fight again"
- Subtitle: Nunito 400, `text-small` (14px), `text-secondary` — "Pick skills that boost your stats, then rescore the fight."

**Skill cards:**
- Grid: 1 column. Gap: `space-3` (12px). Each skill is a selectable card.
- **Skill card:**
  - Base: `bg-surface`, 1px `border-subtle`, `radius-lg`, padding `space-4`. Flex row layout.
  - Left zone (content):
    - Skill title: Nunito 700, `text-body` (16px), `text-primary` — e.g., "Data Analytics Minor"
    - Rationale: Nunito 400, `text-small` (14px), `text-secondary` — e.g., "Learn to direct AI analysis tools instead of competing with them."
    - Stat delta pills: Flex row of small pills. Each delta: `pill-thrive` for positive, `pill-alert` for negative. Space Mono, `text-data-sm`. E.g., `RES +2` `HMN +1`.
  - Right zone: Checkbox/toggle indicator. Unselected: `bg-deep`, 24px circle, `border-subtle`. Selected: `bg-accent-thrive`, checkmark icon, `shadow-glow-thrive`.
  - **Selected state:** Card gets `border-default`, `bg-raised`, subtle thrive glow (`shadow-glow-thrive` at 50% intensity).
  - **Already-crafted skills:** Not shown in the pool. Filtered client-side by checking against `build.skills_crafted[].id`.

- **Entrance:** Skills stagger in with `stagger.normal` (80ms), `staggerItem` variant.

**Reroll action bar:**
- Fixed at bottom of the reroll container (not viewport — scrolls with content).
- Left: Ghost button — "Accept result" (skip reroll, move to next fight). Nunito 700, `text-secondary`.
- Right: Primary button — "Rescore Fight ✦" — disabled until at least 1 skill is selected.
- Disabled state: `state-disabled` overlay per DESIGN.md.
- Skill count badge on Rescore button: e.g., "(2 equipped)" in `text-micro`, `text-muted`.

**Rescore animation:**
When the student taps "Rescore Fight":
1. Button enters loading state (spinner, label changes to "Rescoring...").
2. API call: `POST /build/{id}/reroll` with `{ boss_id, skill_ids }`.
3. On response, the fight result area re-animates:
   - Old result pill crossfades out (opacity → 0, 200ms).
   - New result pill crossfades in (opacity 0 → 1, 200ms, slight scale bounce).
   - If result improved (LOSE→DRAW, LOSE→WIN, DRAW→WIN):
     - Flash: boss card border briefly glows thrive (0.4s pulse).
     - Score context updates to show new raw score.
     - Delta annotation: Space Mono, `text-data-sm`, `text-accent-thrive` — e.g., "↑ Score: 8 → 14"
     - Gemma reroll commentary replaces the original narrative if provided by the API.
   - If result unchanged:
     - Score context updates to new raw score.
     - No celebration animation.
     - Subtitle: Nunito 400, `text-small`, `text-secondary` — "Skills equipped, but the gap remains. Try more?"
4. Skill pool refreshes: crafted skills are removed from the available list.
5. If skills remain for this boss, the reroll flow stays visible (student can equip more and rescore again).
6. If no skills remain for this boss and result is still LOSE/DRAW → structural loss (see below).

**Structural loss:**
When the skill pool for this boss is exhausted and the fight result is still LOSE or DRAW:

- Reroll skill cards fade out (opacity → 0, 300ms).
- Structural loss card fades in:
  - Container: `bg-mid`, 1px `border-border-strong`, `radius-xl`, padding `space-6`.
  - Left border accent: 3px solid `accent-alert`.
  - Icon: ⚠️ at 32px, centered above text.
  - Message: Nunito 400, `text-body-lg` (18px), `text-primary` — "Every available skill for this fight has been equipped, and the result is still a loss. That's the most important signal this tool can give you: the gap isn't a skill-tree problem. It's structural to this school + major + career combination. Worth taking seriously."
  - Sub-message: Nunito 400, `text-small` (14px), `text-secondary` — "This doesn't mean the path is wrong — it means this specific risk needs a different strategy. Your Next Steps checklist will address this."
- CTA: Primary button — "Continue →" to advance to the next fight.

#### Phase 4: Resolved → Advance

After a fight is resolved (win with no reroll needed, reroll completed, reroll skipped, or structural loss acknowledged):

- Primary button at bottom: "Next Fight →" (fights 1-4) or "See the Verdict →" (fight 5).
- Current fight's progress circle fills with result color.
- Page crossfades to the next fight (`transitions.fade`, 300ms).

### Fight the Future (Final Boss)

After all 5 fights resolve, the Final Boss appears. This is presentation-only — no scoring, no reroll.

- **Entrance:** All 5 progress circles are filled. They pulse once in sequence (stagger 100ms), then converge toward center (translateX toward center, 0.5s). Background glow intensifies with all 5 boss colors blended.
- **Boss emoji:** ⚔️ at 100px. `bossFight.bossEntrance` animation. The emoji has a shifting glow that cycles through all 5 boss colors (CSS animation, 8s cycle).
- **Boss name:** Fredoka 700, `text-display` (36px), `text-primary` — "Fight the Future"
- **Verdict:** The gauntlet verdict string. Fredoka 600, `text-heading` (28px). Color based on verdict:
  - "DOMINANT BUILD": `text-accent-thrive`
  - "SOLID BUILD": `text-accent-thrive`
  - "MIXED BUILD": `text-accent-caution`
  - "VULNERABLE BUILD": `text-accent-alert`
  - Fallback: `text-secondary`
- **Scorecard:** 5 small fight result cards in a horizontal row (or 2-3 column grid on mobile).
  - Each card: boss emoji (24px) + boss name (Nunito 600, `text-small`) + result pill (small). Background: boss color at 8% opacity.
  - Cards stagger in: `stagger.normal`.
- **Tally:** Space Mono 700, `text-data` (16px), `text-secondary` — "3 wins · 1 draw · 1 loss"
- **Skills crafted summary:** If any skills were crafted during rerolls, show a collapsed section: "Skills equipped: {count}" with an expand toggle showing the list. Each skill: title + delta pills.

**CTA:** Primary button — "Your Next Steps ✦"

### Next Steps

After the student taps "Your Next Steps", the screen transitions to the post-gauntlet checklist.

**Loading state:**
- While `POST /build/{id}/next-steps` is in flight:
- Background settles to `bg-deep` (header un-dims to normal).
- Centered: Nunito 400, `text-body-lg`, `text-primary` — "Gemma is writing your action plan..."
- Profile emoji at 48px, floating animation.
- Minimum display: 1.5s (prevents flash).

**Content:**
- Step indicator: Space Mono 11px, `text-muted`, uppercase, letter-spacing 2px — "YOUR NEXT STEPS"
- Intro: Nunito 400, `text-body-lg` (18px), `text-secondary` — "No more bosses. No more stats. Here's what you actually do next."
- Four sections rendered from the markdown `checklist` string:
  - "Questions to Ask Your Guidance Counselor"
  - "Questions to Ask College Recruiters"
  - "Things to Verify on Your Own"
  - "Points to Discuss with Your Parents"
- Each section:
  - Header: Fredoka 600, `text-heading` (28px), `text-primary`. Section icon emoji: 🎓 / 🏫 / 🔍 / 👪
  - Content: Nunito 400, `text-body` (16px), `text-primary`. Numbered items. Rendered from markdown with proper line breaks and emphasis.
  - Container: `bg-mid`, 1px `border-subtle`, `radius-xl`, padding `space-6`. Margin-bottom `space-4`.
- Sections stagger in: `stagger.normal` (80ms).

**Error state:**
If the Next Steps API fails:
- Show fallback message: "Gemma couldn't generate your action plan right now. You can still explore your branches and compare builds."
- "Try Again" secondary button.
- "Continue →" primary button (advances without next steps).

**CTA area:**
- Primary button: "See Where This Path Leads →" — advances to Screen 8 (branch tree, F5).
- Secondary button: "Save & Share" — jumps to Screen 9 (save/wrapped, F6).
- Ghost button: "Back to My Build" — returns to Screen 6 (reveal).

### Shared Elements

**Header:** Dimmed to 60% during boss fights (per DESIGN.md cinematic states). Un-dims on Next Steps and CTA screens. Profile name in `text-muted` at 40% opacity. Back arrow dimmed.

**Progress:** The 5-circle progress indicator persists through the gauntlet. Position: fixed at top of content area (below header), centered. Circles are 12px, gap `space-2`. Fill colors: `accent-thrive` (win), `accent-alert` (lose), `accent-caution` (draw), `accent-info` (unknown), `bg-surface` (upcoming), boss color pulse (current).

**Page transitions:** AnimatePresence with crossfade between fights. Enter: opacity 0→1, 200ms. Exit: opacity 1→0, 150ms. No translateY — fights happen in place, not sliding.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Gauntlet intro | `region-gauntlet-intro` | status | "The gauntlet begins" |
| Fight progress | `nav-fight-progress` | navigation | "Boss fight progress: {n} of 5" |
| Fight card | `region-fight-{boss_id}` | article | "{Boss label}: {result}" |
| Result pill | `badge-result-{boss_id}` | status | "{result} — score {raw_score}" |
| Coaching narrative | `region-narrative-{boss_id}` | article | "Coach's analysis of {boss label}" |
| Receipt trigger | `btn-receipt-fight-{boss_id}` | button | "View scoring details for {boss label}" |
| Receipt panel | `panel-receipt-fight-{boss_id}` | region | "Scoring details for {boss label}" |
| Skill card | `card-skill-{skill_id}` | checkbox | "{skill title}: {stat deltas}" |
| Skill card group | `group-skills-{boss_id}` | group | "Available skills for {boss label}" |
| Accept result button | `btn-accept-{boss_id}` | button | "Accept result and continue" |
| Rescore button | `btn-rescore-{boss_id}` | button | "Rescore fight with equipped skills" |
| Structural loss | `region-structural-loss-{boss_id}` | alert | "Structural loss — all skills exhausted" |
| Next fight button | `btn-next-fight` | button | "Next fight" / "See the verdict" |
| Final Boss verdict | `region-final-boss` | article | "Fight the Future: {verdict}" |
| Fight scorecard | `region-scorecard` | list | "Boss fight scorecard" |
| Next Steps button | `btn-next-steps` | button | "Generate your next steps" |
| Next Steps loading | `region-next-steps-loading` | status | "Generating your action plan" |
| Next Steps section | `region-checklist-{section}` | article | "{section title}" |
| Advance to branches CTA | `btn-branches` | button | "See where this path leads" |

---

## §4 Technical Specification

### Architecture Overview

Screen 7 is the most interactive screen in the product. It reads pre-computed fight data from the Zustand store, presents a sequential cinematic experience, and makes live API calls only for rerolls (mutating server state) and next steps (Gemma inference). The component tree is deeper than previous screens because the gauntlet is a state machine with per-fight sub-states.

The gauntlet does NOT re-fetch the Build object from the API. The pre-computed `gauntlet.fights[]` and `skill_pool[]` are read from the `buildStore` and updated in place as rerolls occur. This means the Zustand store is the source of truth during the gauntlet — server state is updated via reroll API calls, but the frontend drives the presentation.

### API Endpoints Consumed

| Endpoint | Method | Request | Response | Used By |
|---|---|---|---|---|
| `/build/{build_id}/reroll` | POST | `RerollRequest { boss_id: string, skill_ids: string[] }` | `BossFightResult` (updated fight) | Reroll rescore — student equips skills, fight rescores live |
| `/build/{build_id}/next-steps` | POST | `{}` (empty body) | `{ checklist: string }` | Next Steps — post-gauntlet Gemma-generated action checklist |

**Not consumed (already in store from F3):**
- `POST /build/{build_id}/gauntlet` — gauntlet is pre-computed in the Build object
- `GET /build/{build_id}/skill-pool` — skill pool is pre-computed in the Build object

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/GauntletScreen.tsx` | Create | Screen 7 top-level: gauntlet state machine, fight sequencer, next steps section |
| `frontend/src/components/gauntlet/GauntletIntro.tsx` | Create | Intro card with title, progress circles, auto-advance |
| `frontend/src/components/gauntlet/BossFightCard.tsx` | Create | Single boss fight: entrance animation, result reveal, narrative, reroll trigger |
| `frontend/src/components/gauntlet/FightProgress.tsx` | Create | 5-circle progress indicator (resolved/current/upcoming) |
| `frontend/src/components/gauntlet/RerollFlow.tsx` | Create | Skill browse, equip toggle, rescore button, result change animation |
| `frontend/src/components/gauntlet/SkillCard.tsx` | Create | Individual skill option: title, rationale, delta pills, select toggle |
| `frontend/src/components/gauntlet/StructuralLoss.tsx` | Create | Pool exhausted messaging |
| `frontend/src/components/gauntlet/FinalBoss.tsx` | Create | Fight the Future verdict, scorecard, tally, crafted skills summary |
| `frontend/src/components/gauntlet/NextSteps.tsx` | Create | Post-gauntlet checklist renderer (markdown → styled sections) |
| `frontend/src/components/gauntlet/GauntletCTA.tsx` | Create | Post-gauntlet navigation: branches, save/share, back to build |
| `frontend/src/api/gauntlet.ts` | Create | API client functions for reroll + next-steps (with mock fallback) |
| `frontend/src/api/mockGauntlet.ts` | Create | Mock handlers returning realistic reroll + next-steps shapes |
| `frontend/src/store/gauntletStore.ts` | Create | Gauntlet-specific state: current fight index, phase, reroll state, next steps content |
| `frontend/src/data/bossMetadata.ts` | Create | Static boss metadata: emoji, color token, subtitle text, result messages |
| `frontend/src/App.tsx` | Modify | Add route: `/gauntlet` |

### Data Model Additions

No new TypeScript types needed — all types (`BossFightResult`, `GauntletResult`, `AppliedSkill`, `BossId`) already exist in `types/build.ts` from F3.

New static data file:

```typescript
// data/bossMetadata.ts

import type { BossId } from "@/types/build";

interface BossMetadata {
  id: BossId;
  label: string;
  emoji: string;
  subtitle: string;
  colorToken: string;      // Tailwind class for boss color
  glowToken: string;       // Tailwind class for boss glow shadow
  bgWash: string;          // CSS rgba for boss card bg wash
}

export const BOSS_ORDER: BossId[] = ["ai", "loans", "market", "burnout", "ceiling"];

export const BOSS_METADATA: Record<BossId, BossMetadata> = {
  ai: {
    id: "ai",
    label: "Fight AI",
    emoji: "🤖",
    subtitle: "How safe is this career from automation?",
    colorToken: "text-boss-ai",
    glowToken: "shadow-glow-insight",
    bgWash: "rgba(184, 169, 232, 0.08)",
  },
  loans: {
    id: "loans",
    label: "Fight Student Loans",
    emoji: "💰",
    subtitle: "Can your earnings handle the debt?",
    colorToken: "text-boss-loans",
    glowToken: "shadow-glow-alert",
    bgWash: "rgba(244, 169, 126, 0.08)",
  },
  market: {
    id: "market",
    label: "Fight the Market",
    emoji: "📈",
    subtitle: "Is this field growing or shrinking?",
    colorToken: "text-boss-market",
    glowToken: "shadow-glow-info",
    bgWash: "rgba(123, 184, 224, 0.08)",
  },
  burnout: {
    id: "burnout",
    label: "Fight Burnout",
    emoji: "🔥",
    subtitle: "How sustainable is this work long-term?",
    colorToken: "text-boss-burnout",
    glowToken: "shadow-glow-empathy",
    bgWash: "rgba(232, 139, 169, 0.08)",
  },
  ceiling: {
    id: "ceiling",
    label: "Fight the Ceiling",
    emoji: "📊",
    subtitle: "How high can your earnings go?",
    colorToken: "text-boss-ceiling",
    glowToken: "shadow-glow-info",
    bgWash: "rgba(196, 191, 176, 0.08)",
  },
};

export const RESULT_COLORS = {
  win: "accent-thrive",
  lose: "accent-alert",
  draw: "accent-caution",
  unknown: "accent-info",
} as const;

export const VERDICT_COLORS: Record<string, string> = {
  DOMINANT: "text-accent-thrive",
  SOLID: "text-accent-thrive",
  MIXED: "text-accent-caution",
  VULNERABLE: "text-accent-alert",
};

/**
 * Map a verdict string to a color token.
 * Matches on the first word of the verdict.
 */
export function getVerdictColor(verdict: string): string {
  const firstWord = verdict.split(" ")[0]?.toUpperCase() ?? "";
  return VERDICT_COLORS[firstWord] ?? "text-text-secondary";
}
```

### Zustand Store Addition

```typescript
// store/gauntletStore.ts

import { create } from "zustand";
import type { AppliedSkill, BossFightResult, BossId } from "@/types/build";

type GauntletPhase =
  | "intro"
  | "fighting"
  | "final_boss"
  | "next_steps_loading"
  | "next_steps"
  | "complete";

type FightPhase =
  | "entrance"
  | "result"
  | "reroll"
  | "structural_loss"
  | "resolved";

interface GauntletState {
  // Sequencing
  phase: GauntletPhase;
  currentFightIndex: number;
  fightPhase: FightPhase;
  setPhase: (phase: GauntletPhase) => void;
  setCurrentFightIndex: (index: number) => void;
  setFightPhase: (phase: FightPhase) => void;
  advanceFight: () => void;

  // Reroll
  selectedSkillIds: Set<string>;
  isRescoring: boolean;
  toggleSkill: (skillId: string) => void;
  clearSelectedSkills: () => void;
  setIsRescoring: (rescoring: boolean) => void;

  // Next Steps
  nextStepsContent: string | null;
  nextStepsError: boolean;
  setNextStepsContent: (content: string) => void;
  setNextStepsError: (error: boolean) => void;

  // Reset
  resetGauntlet: () => void;
}

export const useGauntletStore = create<GauntletState>()((set, get) => ({
  phase: "intro",
  currentFightIndex: 0,
  fightPhase: "entrance",
  setPhase: (phase) => set({ phase }),
  setCurrentFightIndex: (currentFightIndex) => set({ currentFightIndex }),
  setFightPhase: (fightPhase) => set({ fightPhase }),
  advanceFight: () => {
    const { currentFightIndex } = get();
    if (currentFightIndex < 4) {
      set({
        currentFightIndex: currentFightIndex + 1,
        fightPhase: "entrance",
        selectedSkillIds: new Set(),
      });
    } else {
      set({ phase: "final_boss" });
    }
  },

  selectedSkillIds: new Set(),
  isRescoring: false,
  toggleSkill: (skillId) =>
    set((state) => {
      const next = new Set(state.selectedSkillIds);
      if (next.has(skillId)) {
        next.delete(skillId);
      } else {
        next.add(skillId);
      }
      return { selectedSkillIds: next };
    }),
  clearSelectedSkills: () => set({ selectedSkillIds: new Set() }),
  setIsRescoring: (isRescoring) => set({ isRescoring }),

  nextStepsContent: null,
  nextStepsError: false,
  setNextStepsContent: (nextStepsContent) =>
    set({ nextStepsContent, nextStepsError: false }),
  setNextStepsError: (nextStepsError) => set({ nextStepsError }),

  resetGauntlet: () =>
    set({
      phase: "intro",
      currentFightIndex: 0,
      fightPhase: "entrance",
      selectedSkillIds: new Set(),
      isRescoring: false,
      nextStepsContent: null,
      nextStepsError: false,
    }),
}));
```

### API Client

```typescript
// api/gauntlet.ts

import { apiPost } from "@/api/client";
import { mockRerollFight, mockGetNextSteps } from "@/api/mockGauntlet";
import type { BossFightResult, BossId } from "@/types/build";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function rerollFight(
  buildId: string,
  bossId: BossId,
  skillIds: string[],
): Promise<BossFightResult> {
  if (USE_MOCK) return mockRerollFight(bossId, skillIds);
  return apiPost<BossFightResult>(`/build/${buildId}/reroll`, {
    boss_id: bossId,
    skill_ids: skillIds,
  });
}

export async function getNextSteps(
  buildId: string,
): Promise<string> {
  if (USE_MOCK) return mockGetNextSteps();
  const res = await apiPost<{ checklist: string }>(`/build/${buildId}/next-steps`);
  return res.checklist;
}
```

### Routing Addition

```
/gauntlet  → GauntletScreen     (Screen 7)
```

Navigation guard: `/gauntlet` requires a `build` object in the `buildStore` with a populated `gauntlet.fights[]` array. If missing, redirect to `/reveal`. This prevents navigating to the gauntlet without a computed build.

### Reroll State Management

The reroll flow mutates both server and client state:

1. Student selects skill(s) → `gauntletStore.selectedSkillIds` updates.
2. Student taps "Rescore" → API call `POST /build/{id}/reroll` with `{ boss_id, skill_ids }`.
3. API returns updated `BossFightResult`.
4. Client updates `buildStore.build.gauntlet.fights[]` — replace the fight at matching `boss` index.
5. Client moves selected skills from `build.skill_pool` to `build.skills_crafted`.
6. Client recomputes W/L/D totals on `build.gauntlet` (wins, losses, draws, unknown, verdict).
7. `gauntletStore.selectedSkillIds` clears.
8. Component re-renders with new fight result.

The Zustand `buildStore.setBuild()` replaces the entire Build object. A helper function handles the fight update + skill transfer + total recomputation:

```typescript
// In GauntletScreen.tsx or a custom hook

function applyRerollResult(
  build: Build,
  bossId: BossId,
  newFight: BossFightResult,
  craftedSkillIds: string[],
): Build {
  // Replace the fight
  const updatedFights = build.gauntlet.fights.map((f) =>
    f.boss === bossId ? newFight : f,
  );

  // Move skills from pool to crafted
  const craftedSkills = build.skill_pool.filter((s) => craftedSkillIds.includes(s.id));
  const remainingPool = build.skill_pool.filter((s) => !craftedSkillIds.includes(s.id));

  // Recompute totals
  const wins = updatedFights.filter((f) => f.result === "win").length;
  const losses = updatedFights.filter((f) => f.result === "lose").length;
  const draws = updatedFights.filter((f) => f.result === "draw").length;
  const unknown = updatedFights.filter((f) => f.result === "unknown").length;

  return {
    ...build,
    gauntlet: {
      ...build.gauntlet,
      fights: updatedFights,
      wins,
      losses,
      draws,
      unknown,
      verdict: deriveVerdict(wins, losses, draws, unknown),
    },
    skill_pool: remainingPool,
    skills_crafted: [...build.skills_crafted, ...craftedSkills],
  };
}

function deriveVerdict(wins: number, losses: number, draws: number, unknown: number): string {
  const scored = wins + losses + draws;
  if (scored === 0) return "Insufficient data to score the gauntlet.";
  if (losses === 0 && wins >= 3) return "DOMINANT BUILD — strong across the board.";
  if (wins > losses) {
    if (losses === 0) return "SOLID BUILD with minor soft spots.";
    return "SOLID BUILD with a gap.";
  }
  if (wins === losses) return "MIXED BUILD — wins and losses cancel out; play to strengths.";
  return "VULNERABLE BUILD — losses outweigh wins; active mitigation required.";
}
```

### Skill Pool Filtering

Available skills for a specific fight are filtered by:
1. `skill.targets` includes the current `boss_id`
2. `skill.id` is NOT in `build.skills_crafted[].id` (already equipped in a previous reroll)

When the filtered list is empty and the fight result is still LOSE or DRAW, the structural loss state triggers.

### Next Steps Markdown Rendering

The `checklist` string from the API is markdown with `##` headers and numbered items. The NextSteps component should parse this into four sections and render each in a styled container. A simple split on `## ` headings is sufficient — no markdown library needed for the four-section format.

```typescript
function parseNextStepsSections(markdown: string): Array<{ title: string; content: string }> {
  const sections: Array<{ title: string; content: string }> = [];
  const parts = markdown.split(/^## /m).filter(Boolean);
  for (const part of parts) {
    const newlineIdx = part.indexOf("\n");
    if (newlineIdx === -1) continue;
    const title = part.slice(0, newlineIdx).trim();
    const content = part.slice(newlineIdx + 1).trim();
    sections.push({ title, content });
  }
  return sections;
}
```

### Service Changes

- No backend changes in this spec.
- No new npm dependencies. Framer Motion already installed from F1/F3.
- The `ReceiptPanel` component from F3 is reused for fight receipts.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `App.test.tsx` | Routing tests | Medium | New `/gauntlet` route being added |
| `store/buildStore.test.ts` | Build state tests | Low | Build object shape unchanged, but `setBuild` is called more frequently during rerolls |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `App.test.tsx` | Add route assertion for `/gauntlet` | New route |

#### Confirmed Safe

- All backend tests (no backend changes)
- F1/F2/F3 component tests (no modifications to those components)
- Design token files (no changes)
- `buildStore.test.ts` (Build shape unchanged)
- `api/build.test.ts` (existing API client untouched)

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `screens/GauntletScreen.test.tsx` | renders gauntlet intro | Intro title, progress circles, auto-advance |
| P0 | `screens/GauntletScreen.test.tsx` | renders sequential fights | First fight appears after intro, correct boss order |
| P0 | `screens/GauntletScreen.test.tsx` | advances through fights | Tap "Next Fight" → next boss appears |
| P0 | `components/gauntlet/BossFightCard.test.tsx` | renders fight result | Boss emoji, name, result pill, narrative present |
| P0 | `components/gauntlet/BossFightCard.test.tsx` | win animation triggers | Win result → green burst class/animation applied |
| P0 | `components/gauntlet/BossFightCard.test.tsx` | loss shows reroll CTA | Lose result → "Equip skills" section appears |
| P0 | `components/gauntlet/RerollFlow.test.tsx` | renders available skills | Skills with matching `targets` appear as selectable cards |
| P0 | `components/gauntlet/RerollFlow.test.tsx` | skill selection updates store | Tap skill → `selectedSkillIds` updates |
| P0 | `components/gauntlet/RerollFlow.test.tsx` | rescore button disabled without selection | No skills selected → button disabled |
| P0 | `components/gauntlet/RerollFlow.test.tsx` | rescore calls API | Tap rescore → API call with boss_id + skill_ids |
| P0 | `components/gauntlet/StructuralLoss.test.tsx` | renders structural loss message | Pool exhausted + loss → structural loss card appears |
| P0 | `components/gauntlet/FinalBoss.test.tsx` | renders verdict and scorecard | Verdict text, 5 fight result cards, tally |
| P0 | `components/gauntlet/NextSteps.test.tsx` | renders four sections | Four section headers from markdown, numbered items |
| P1 | `components/gauntlet/RerollFlow.test.tsx` | crafted skills excluded from pool | Skills in `skills_crafted` don't appear in available list |
| P1 | `components/gauntlet/RerollFlow.test.tsx` | result change animates | Rescore with improved result → new pill + delta annotation |
| P1 | `components/gauntlet/FightProgress.test.tsx` | progress circles reflect results | Resolved fights show correct color fills |
| P1 | `components/gauntlet/NextSteps.test.tsx` | loading state renders | API in flight → loading indicator |
| P1 | `components/gauntlet/NextSteps.test.tsx` | error state renders retry | API failure → error message + retry button |
| P1 | `components/gauntlet/SkillCard.test.tsx` | renders skill with deltas | Title, rationale, stat delta pills present |
| P1 | `store/gauntletStore.test.tsx` | fight sequencing | advanceFight increments index, transitions to final_boss at index 5 |
| P1 | `store/gauntletStore.test.tsx` | skill selection toggle | toggleSkill adds/removes from set |
| P2 | `api/gauntlet.test.ts` | mock reroll returns valid shape | Mock handler returns BossFightResult matching type |
| P2 | `api/gauntlet.test.ts` | mock next steps returns markdown | Mock handler returns string with four ## sections |
| P2 | `screens/GauntletScreen.test.tsx` | draw shows reroll CTA | Draw result also triggers reroll flow |
| P2 | `screens/GauntletScreen.test.tsx` | gauntlet redirects without build | No build in store → redirect to /reveal |

#### Test Data Requirements

- Mock `Build` fixture with gauntlet containing a mix of win/lose/draw results (at least 1 win, 1 lose, 1 draw)
- Mock `skill_pool` with at least 3 skills per losing boss
- Mock `BossFightResult` for reroll response with improved result (e.g., lose → draw)
- Mock `BossFightResult` for reroll response with unchanged result
- Mock next steps markdown string with four `##` sections and numbered items
- Empty skill pool scenario for structural loss testing

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED
**Reviewed:** 2026-04-14

#### System Context

Screen 7 is a purely frontend feature that sits between the Reveal screen (F3/Screen 6) and the Branch Tree (F5/Screen 8). It reads pre-computed gauntlet data from the Zustand `buildStore`, orchestrates a sequential cinematic boss fight experience, and makes two live API calls: `POST /build/{id}/reroll` (gauntlet router) and `POST /build/{id}/next-steps` (guidance router). No Brightsmith pipeline zones are touched. No new backend code is required. No Gold zone tables are read. No Gemma roles are invoked directly from the frontend -- the backend services handle Gemma calls for reroll rescoring and next-steps generation.

This is a clean frontend-only spec consuming well-established API contracts.

#### Data Flow Analysis

**Initial gauntlet data:** `Build.gauntlet.fights[]` and `Build.skill_pool[]` are populated during the F3 build orchestration and stored in the Zustand `buildStore`. The gauntlet screen reads these from the store -- no API call. This is correct and eliminates latency during the cinematic sequence.

**Reroll flow:**
1. Student selects skills from `build.skill_pool` (filtered by `skill.targets` containing current `boss_id`, excluding already-crafted skills)
2. Frontend calls `POST /build/{build_id}/reroll` with `{ boss_id: string, skill_ids: string[] }`
3. Backend (`gauntlet.py:21-60`): validates skills exist in `build.skill_pool`, applies skill deltas to career stats via `skill_pool.apply_skills()`, rescores the single fight via `boss_fights.rescore_fight()`, updates `build.gauntlet.fights[]`, recomputes W/L/D totals, extends `build.skills_crafted`, mutates `build.career`, persists to state store, returns single `BossFightResult`
4. Frontend receives `BossFightResult`, replaces the fight in local `buildStore`, moves skills from `skill_pool` to `skills_crafted`, recomputes W/L/D totals locally

**Next steps flow:**
1. Frontend calls `POST /build/{build_id}/next-steps` (guidance router)
2. Backend calls `next_steps.generate_next_steps(build)` -- Gemma inference
3. Returns `{ checklist: string }` -- markdown with `##` sections
4. Frontend parses and renders four sections

All boundary crossings are typed. The API contracts match existing backend implementations.

#### Contract Review

**RerollRequest (Pydantic):** `{ boss_id: str, skill_ids: list[str] }` -- matches what the spec's `api/gauntlet.ts` sends as `{ boss_id: bossId, skill_ids: skillIds }`. Aligned.

**Reroll response:** Backend returns a bare `BossFightResult` (Pydantic model). The TypeScript `BossFightResult` interface in `types/build.ts` matches this shape field-for-field, including `rerolled`, `reroll_count`, `original_result`, `original_raw_score`. Aligned.

**Next-steps response:** Backend returns `{ checklist: string }`. The spec's `getNextSteps()` correctly unwraps `res.checklist`. Aligned.

**Zustand store:** `buildStore.setBuild()` replaces the entire `Build` object. The `applyRerollResult()` helper constructs a new `Build` with updated fights, moved skills, and recomputed totals. This is a clean immutable update pattern. The `gauntletStore` handles UI-only sequencing state (phase, fight index, selected skills) -- correctly separated from domain state in `buildStore`.

**Routing:** Both reroll and next-steps endpoints live under the `/build` prefix (confirmed in `main.py:39-42`). The spec's API paths `/build/${buildId}/reroll` and `/build/${buildId}/next-steps` match the registered routes exactly.

#### Findings

##### Sound

1. **Pre-computed vs. live split is architecturally correct.** Reading gauntlet data from the store for the cinematic sequence and only hitting the API for mutations (reroll) and inference (next steps) is the right call. The cinematic experience never blocks on network.

2. **Store separation is clean.** Domain state (`Build` object with gauntlet, skills, career) lives in `buildStore`. UI sequencing state (fight index, phase, selected skills) lives in `gauntletStore`. Neither store duplicates data from the other.

3. **API contracts are verified against existing backend code.** The `RerollRequest` model, the `BossFightResult` return type, and the `{ checklist: string }` next-steps response all match the backend implementations in `gauntlet.py` and `guidance_router.py`.

4. **The `applyRerollResult()` helper correctly mirrors server-side mutation logic.** Fight replacement, skill transfer, and W/L/D recomputation are all handled. The `deriveVerdict()` function provides a reasonable client-side verdict derivation.

5. **Component tree depth is justified.** The gauntlet is genuinely a state machine with per-fight sub-states. The component decomposition (GauntletScreen > BossFightCard > RerollFlow > SkillCard) follows the state machine structure cleanly.

6. **Mock fallback pattern (`VITE_USE_MOCK_API`) is consistent with existing codebase patterns.** The `apiPost` import from `@/api/client` matches the existing client at `frontend/src/api/client.ts`.

7. **Navigation guard pattern (redirect to `/reveal` if no build) is correct** and consistent with how other screens gate on required state.

8. **`bossMetadata.ts` as a static data file is the right pattern.** Boss display metadata (emoji, color tokens, subtitles) is presentation-layer data that does not belong in the pipeline or backend. Keeping it as a typed constant avoids an unnecessary API call.

##### Concerns

- **Server/client skill_pool divergence:** The backend reroll endpoint (`gauntlet.py:57`) does `build.skills_crafted.extend(picks)` but does NOT remove those skills from `build.skill_pool` server-side. The spec's client-side `applyRerollResult()` DOES remove them from `skill_pool`. This means after a reroll, the server's `skill_pool` still contains previously-used skills, while the client's does not. This is functionally harmless because: (a) the server validates `request.skill_ids` against `build.skill_pool` on each reroll call, and previously-crafted skills will still be found, and (b) the client filters crafted skills out of the UI. However, if a student somehow sends a skill_id that was already crafted, the server would apply it again. **Impact:** Low -- the client correctly prevents re-selection, and double-application would only make stats slightly wrong. **Recommendation:** Note this as a known backend quirk. No spec change needed, but a follow-up backend fix to filter `skill_pool` after crafting would be a good hardening task.

- **`deriveVerdict()` client-side may diverge from server-side.** The spec includes a client-side `deriveVerdict()` function, but the server's `boss_fights.recompute_totals()` also computes the verdict. If the verdict logic ever changes server-side, the client copy would be stale. **Impact:** Cosmetic only during the gauntlet sequence -- the Build object from the server is authoritative for all downstream screens. **Recommendation:** Acceptable for now. If verdict logic becomes complex, consider having the reroll endpoint return the updated verdict string alongside the `BossFightResult`. Not a blocker.

- **`Set<string>` in Zustand store may cause render issues.** The `gauntletStore` uses `selectedSkillIds: Set<string>`. Zustand uses shallow equality by default, and `Set` mutations (add/delete) on the same reference would not trigger re-renders. The spec's `toggleSkill` correctly creates a new `Set` instance via `new Set(state.selectedSkillIds)`, so this is handled. **Impact:** None if implemented as specified. **Recommendation:** The spec is correct as written. Implementers should not deviate from the `new Set()` pattern.

- **File path inconsistency: `store/` vs `stores/`.** The existing codebase uses `frontend/src/store/` (singular) for `profileStore.ts`, `buildInputStore.ts`, `buildStore.ts`. The spec lists the new file as `frontend/src/store/gauntletStore.ts` which matches. Confirmed consistent.

##### Blockers

None.

#### Verdict
- [x] APPROVED

#### Conditions

None. The architecture is clean. The spec correctly consumes existing API contracts, separates domain state from UI sequencing state, and follows established patterns. The concerns noted above are minor and do not block implementation.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline changes — frontend consuming existing API contracts)

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Created
| File | Description |
|------|-------------|
| `frontend/src/data/bossMetadata.ts` | Static boss metadata: emoji, color tokens, subtitles, verdict color helper |
| `frontend/src/store/gauntletStore.ts` | Zustand store: gauntlet phase, fight index, reroll selection, next steps state |
| `frontend/src/api/gauntlet.ts` | API client: rerollFight + getNextSteps with mock fallback |
| `frontend/src/api/mockGauntlet.ts` | Mock handlers returning realistic shapes |
| `frontend/src/components/gauntlet/FightProgress.tsx` | 5-circle progress indicator |
| `frontend/src/components/gauntlet/GauntletIntro.tsx` | Intro card with auto-advance |
| `frontend/src/components/gauntlet/BossFightCard.tsx` | Boss fight: entrance, result, narrative, reroll trigger |
| `frontend/src/components/gauntlet/SkillCard.tsx` | Selectable skill card with stat delta pills |
| `frontend/src/components/gauntlet/RerollFlow.tsx` | Skill browse, equip, rescore button |
| `frontend/src/components/gauntlet/StructuralLoss.tsx` | Pool exhausted messaging |
| `frontend/src/components/gauntlet/FinalBoss.tsx` | Fight the Future verdict + scorecard |
| `frontend/src/components/gauntlet/NextSteps.tsx` | Post-gauntlet markdown checklist renderer |
| `frontend/src/components/gauntlet/GauntletCTA.tsx` | Post-gauntlet navigation CTAs |
| `frontend/src/screens/GauntletScreen.tsx` | Top-level state machine orchestrating gauntlet |

### Files Modified
| File | Change Summary |
|------|---------------|
| `frontend/src/App.tsx` | Added `/gauntlet` route |
| `frontend/src/components/ui/AppHeader.tsx` | Added 60% header dimming + 40% profile name opacity during gauntlet |
| `frontend/src/screens/RevealScreen.tsx` | Changed CTA navigation from `/bosses` to `/gauntlet` |
| `frontend/src/styles/motion.ts` | Fixed `staggerContainer` parameter type (literal → `number`) |

### Deviations from Spec
- Removed `fightIndex` prop from BossFightCard (unused, caused TS error)
- Used mutable array spread for `bossFight.winBurst` and `bossFight.loseShake` animations to satisfy Framer Motion's type requirements with `as const` objects
- Added `rescoreError` state and display per code review finding (not in original spec)
- Added fight-change reset effect in BossFightCard per code review finding
- Added malformed markdown fallback in NextSteps per code review finding
- Used `useBuildStore.getState()` in async handler per code review finding (stale closure fix)

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | FAIL | 8 TS errors: unused imports, readonly array types, stagger literal types | Removed unused imports, spread readonly arrays, widened staggerContainer param type |
| 2 | FAIL | 1 TS error: unused `fightIndex` destructured | Removed `fightIndex` prop entirely |
| 3 | PASS | — | — |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added (72 tests across 6 files)

| Test File | Tests | What It Covers |
|-----------|-------|---------------|
| `store/gauntletStore.test.ts` | 16 | advanceFight sequencing, toggleSkill, phase transitions, resetGauntlet |
| `data/bossMetadata.test.ts` | 13 | BOSS_ORDER, BOSS_METADATA completeness, RESULT_COLORS, getVerdictColor |
| `components/gauntlet/StructuralLoss.test.tsx` | 6 | Message rendering, onContinue, role=alert, aria-labels |
| `components/gauntlet/SkillCard.test.tsx` | 11 | Title/rationale, delta pills, toggle, aria-checked, zero-delta exclusion |
| `components/gauntlet/FightProgress.test.tsx` | 8 | 5 circles, current/resolved/upcoming labels, result colors |
| `components/gauntlet/NextSteps.test.tsx` | 18 | Four sections, CTAs, loading state, error state, null content |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 0 | 0 | 0 | 0 (no backend changes) |
| vitest | 87 | 2 (pre-existing) | 0 | 89 |

**Pre-existing failures:** 2 tests in `ProfileScreen.test.tsx` — Framer Motion splits emoji text across elements. Confirmed failing on clean `main` before gauntlet changes.

---

## §8 Reviews

**Status:** CHANGES REQUIRED

### Design Audit (@fp-design-auditor)
**Status:** COMPLETE
**Date:** 2026-04-14
**Auditor:** @fp-design-auditor (Claude Opus 4.6)

#### Overall Verdict: APPROVED with minor issues

The Boss Gauntlet implementation demonstrates strong Brightpath compliance. The design system is used with intentionality and consistency. Five minor deviations documented below; none are blockers.

#### 1. Color Token Compliance -- PASS

All colors reference design tokens via Tailwind utilities or CSS custom properties. Background tokens (`bg-bp-void`, `bg-bp-mid`, `bg-bp-surface`, `bg-bp-raised`), accent tokens, text tokens, border tokens, and boss colors via `var(--color-boss-${fight.boss})` are all correct.

**Minor issue:** `StructuralLoss.tsx:32` hand-rolls a `<motion.button>` with `hover:bg-[#6bc494]` instead of using the shared `<Button>` component. The hex value is correct per DESIGN.md but should use the component.

#### 2. Boss Color Usage -- PASS

All five boss colors correctly mapped in `bossMetadata.ts`: ai=`text-boss-ai`, loans=`text-boss-loans`, market=`text-boss-market`, burnout=`text-boss-burnout`, ceiling=`text-boss-ceiling`. Background washes use correct rgba values at 8% opacity. The Future final boss correctly uses a conic-gradient cycling through all five `--color-boss-*` CSS variables. Boss glow tokens correctly assigned: ai=insight, loans=alert, market=info, burnout=empathy. Ceiling uses `shadow-glow-info` (acceptable -- no ceiling-specific glow token exists in the system).

#### 3. Typography -- PASS

Fredoka (`font-display`) for boss names/headings, Nunito (`font-body`) for body text, Space Mono (`font-data`) for scores/labels. Boss names use `font-display font-bold text-display` (Fredoka 700 36px). Card titles use `font-display font-semibold text-heading` (Fredoka 600 28px). Section labels use `font-data text-[11px] uppercase tracking-[2px]`.

**Minor issue:** Section labels in GauntletIntro and NextSteps use `text-text-muted` instead of `text-accent-info`. DESIGN.md section label spec specifies `color: accent-info`.

#### 4. Type Scale -- PASS

All type scale tokens verified against DESIGN.md and tailwind.config.ts: text-display=36px, text-heading=28px, text-body-lg=18px, text-body=16px, text-small=14px, text-data-sm=13px, text-micro=12px, text-cta=17px. Line heights correct throughout.

#### 5. Spacing -- PASS

All spacing uses 4px-base Tailwind utilities. Card padding `p-6` (24px) matches spec. SkillCard `p-4` (16px). Section gaps `gap-3`/`space-y-4`. CTA margins `mt-10` (40px). No arbitrary spacing values outside the system.

#### 6. Border Radii -- PASS

All radii from token set: panels `rounded-xl` (20px), cards/buttons `rounded-lg` (14px), pills/dots `rounded-full` (9999px).

#### 7. Motion Presets -- PASS

All `bossFight.*` presets from motion.ts used correctly: `bossFight.vignette` for darkening, `bossFight.bossEntrance` for y:-60 bounce-in, `bossFight.winBurst` for scale pulse, `bossFight.loseShake` for x-axis shake. Springs (`smooth`, `bouncy`, `snappy`) and stagger (`fast`, `normal`) used appropriately. `transitions.fadeInUp` and `transitions.fade` applied correctly.

**Minor issue:** RerollFlow container entrance uses CSS `transition` (`delay: 0.5, duration: 0.3`) instead of a spring. DESIGN.md states meaningful animations should use spring physics.

#### 8. Header Dimming -- PASS

AppHeader applies `opacity-60` and `border-[rgba(255,255,255,0.02)]` when `isGauntlet` is true. Matches DESIGN.md cinematic state spec. **Partial:** Profile name opacity ends up at 60% (inherited from header) rather than the specified 40%. Minor deviation.

#### 9. Result Pill Colors -- PASS (minor deviation)

Correct semantic mapping: win=thrive, lose=alert, draw=caution, unknown=info. Pills add a `border-accent-*/30` not in the DESIGN.md pill spec (tasteful enhancement). Background opacity uses `/20` (20%) instead of DESIGN.md-specified 15%. Subtle but technically a deviation. Consistent across BossFightCard and FinalBoss.

#### 10. Responsive Patterns -- PASS

`max-w-[640px]` content constraint. `px-6` mobile padding. FinalBoss scorecard uses `grid-cols-2 tablet:grid-cols-5`. All touch targets minimum 40px. Content stacks naturally via flex-col.

#### Summary of Issues

| # | Severity | Component | Issue |
|---|----------|-----------|-------|
| 1 | LOW | StructuralLoss.tsx | Hand-rolled button; replace with `<Button variant="primary">` |
| 2 | LOW | GauntletIntro, NextSteps | Section label color `text-text-muted` should be `text-accent-info` |
| 3 | LOW | BossFightCard, FinalBoss | Result pill bg opacity `/20` should be `/15` per pill spec |
| 4 | LOW | RerollFlow | Container entrance uses CSS duration; should use `springs.smooth` |
| 5 | LOW | AppHeader | Profile name at 60% opacity during gauntlet; spec says 40% |

**No blockers.** Implementation is well-crafted and faithful to Brightpath. Motion choreography, boss colors, typography, spacing, and radii all come from the token system.

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
**Date:** 2026-04-14
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary

Look, I love Claude, BUT... this is a case where I'd say it did 80% of the work and the other 20% is where the 3am pages live. The overall architecture is solid -- Zustand state machine, pre-computed gauntlet data, two surgical API calls. Good separation of concerns. But I found a silent error swallow that will make debugging in prod impossible, a race condition on the rescore button, a stale closure bug that will cause incorrect builds after reroll, and some missing guard rails that will confuse students. No security blockers -- the API client is clean, no raw HTML injection, buildId goes through fetch (no SQL risk on a frontend). This is good AI-generated code. It just needs... supervision.

#### Findings

##### Finding 1: Silent Error Swallow on Rescore -- Invisible Failures in Prod

**Severity:** SERIOUS

**Impact:** When the reroll API call fails (network error, 500, timeout), the user sees nothing. The button stops spinning, and they're left staring at the reroll panel with no indication anything went wrong. No toast, no error message, no retry prompt. In prod with flaky Gemma inference, this WILL happen. The student will think the app is broken, mash the button, and we'll have no telemetry to debug it.

**Location:** `frontend/src/screens/GauntletScreen.tsx`, lines 179-180

```typescript
    } catch {
      // Keep reroll state on error
    } finally {
```

**The Fix:** Surface the error to the user. At minimum, set an error flag in the gauntlet store and show inline feedback in the RerollFlow component.

```typescript
    } catch (err) {
      // Show error to user -- don't silently swallow
      setRescoreError(true);
    } finally {
```

Add `rescoreError` / `setRescoreError` to gauntletStore and render an inline error message in RerollFlow (e.g., "Rescore failed -- try again or accept the result"). Clear the error flag when the user retries or navigates away.

**Routing:** Implementation agent -- add `rescoreError` state to gauntletStore, render error UI in RerollFlow, clear on retry.

---

##### Finding 2: No Double-Click Guard on Rescore -- Race Condition on State Mutation

**Severity:** SERIOUS

**Impact:** The rescore button has a `loading` prop (`isRescoring`) that disables the visual state, BUT the `handleRescore` callback has no guard against concurrent invocation. If a user double-taps before `setIsRescoring(true)` propagates through React's render cycle, two concurrent `rerollFight` API calls fire. Both will try to `applyRerollResult` to the build, and since `build` is captured in the closure at call time, the second call will overwrite the first call's state mutation. The server-side skill_pool mutation will be applied twice but the client will only reflect one of them, causing a client/server state divergence.

**Location:** `frontend/src/screens/GauntletScreen.tsx`, line 142

```typescript
  const handleRescore = useCallback(async () => {
    if (!currentFight || !currentBossId) return;
    setIsRescoring(true);
```

**The Fix:** Add an early return guard using a ref, or check `isRescoring` from the store at invocation time (not from the stale closure).

```typescript
  const handleRescore = useCallback(async () => {
    if (!currentFight || !currentBossId) return;
    if (useGauntletStore.getState().isRescoring) return; // guard against double-tap
    setIsRescoring(true);
    // ... rest of handler
```

Using `getState()` reads the current Zustand state directly, bypassing React's batched rendering lag.

**Routing:** Implementation agent -- add the guard.

---

##### Finding 3: Stale `build` Reference in Rescore Closure

**Severity:** MODERATE

**Impact:** `handleRescore` captures `build` in its `useCallback` dependency array, but `build` is the React-rendered snapshot from `useBuildStore()`. If the user rerolls fight A, then immediately advances and rerolls fight B, `handleRescore` for fight B could close over the pre-reroll-A version of `build` if React hasn't re-rendered yet. The `applyRerollResult` call would then compute the new build from stale data, potentially reverting the fight A reroll result.

In practice this is unlikely because `advanceFight` triggers a render cycle, but the pattern is fragile and I've seen this exact bug in production at... a company I won't name.

**Location:** `frontend/src/screens/GauntletScreen.tsx`, line 142-193

```typescript
  const handleRescore = useCallback(async () => {
    // ...
    const updatedBuild = applyRerollResult(
      build,  // <-- captured from render, could be stale
      currentBossId,
      newFight,
      skillIds,
    );
```

**The Fix:** Read `build` from the store at call time instead of from the closure.

```typescript
  const handleRescore = useCallback(async () => {
    const currentBuild = useBuildStore.getState().build;
    if (!currentBuild || !currentFight || !currentBossId) return;
    // ...
    const updatedBuild = applyRerollResult(
      currentBuild,
      currentBossId,
      newFight,
      skillIds,
    );
```

Then remove `build` from the dependency array. This is the standard Zustand pattern for async handlers.

**Routing:** Implementation agent -- read build from store.getState() in async handlers.

---

##### Finding 4: Unbounded Reroll -- No Max Reroll Count Enforcement on Client

**Severity:** MODERATE

**Impact:** The `BossFightResult` type has a `reroll_count` field, and presumably the backend enforces a limit. But the frontend has zero client-side enforcement. If the backend limit is misconfigured or removed, a student could reroll the same fight indefinitely, consuming the entire skill pool one skill at a time. More practically, the UI gives no indication of how many rerolls remain, which is confusing -- the student doesn't know if they can try again or if this is their last shot.

**Location:** `frontend/src/screens/GauntletScreen.tsx`, `handleRescore` -- no reroll count check.

**The Fix:** At minimum, display the reroll count. Ideally, enforce a client-side max (e.g., 3) as defense-in-depth:

```typescript
const MAX_REROLLS = 3;
// In handleRescore:
if ((currentFight?.reroll_count ?? 0) >= MAX_REROLLS) {
  setFightPhase("structural_loss");
  return;
}
```

**Routing:** Implementation agent -- add reroll count display and optional client-side cap.

---

##### Finding 5: `showResult` and `showNarrative` State Not Reset Between Fights

**Severity:** MODERATE

**Impact:** `BossFightCard` uses local `useState` for `showResult` and `showNarrative`, initialized to `false`. When the component unmounts (fight advances) and remounts for the next fight, React re-initializes these to `false` -- so this works correctly via the `key={fight-${currentBossId}}` on the parent `motion.div`. However, if `AnimatePresence` reuses the component instance (which Framer Motion can do with `mode="wait"`), stale local state could bleed across fights, showing the result instantly without the entrance animation.

This is a known Framer Motion footgun. The current code appears safe because the `key` changes force remounting, but it's fragile -- a refactor that changes the key strategy breaks the entrance sequence silently.

**Location:** `frontend/src/components/gauntlet/BossFightCard.tsx`, lines 63-66

**The Fix:** Reset local state when `fightPhase` changes to "entrance":

```typescript
  useEffect(() => {
    if (fightPhase === "entrance") {
      setShowResult(false);
      setShowNarrative(false);
      setPrevResult(null);
      setScoreImproved(false);
    }
  }, [fightPhase]);
```

**Routing:** Implementation agent -- add reset effect as defensive measure.

---

##### Finding 6: NextSteps Markdown Parsing Trusts LLM Output Structure

**Severity:** MINOR

**Impact:** `parseNextStepsSections` in `NextSteps.tsx` splits on `## ` headings and assumes each section has a newline after the title. If Gemma returns malformed markdown (no `##` headings, extra whitespace, nested headings), the parser returns an empty array and the user sees nothing -- no error, no fallback, just a blank screen with CTA buttons floating in space.

**Location:** `frontend/src/components/gauntlet/NextSteps.tsx`, lines 23-36

**The Fix:** Add a fallback for when parsing yields zero sections:

```typescript
  const sections = parseNextStepsSections(content);
  if (sections.length === 0) {
    // Fallback: render raw content in a single section
    sections.push({ title: "Your Next Steps", content });
  }
```

**Routing:** Implementation agent -- add fallback rendering.

---

#### What's Good

I'll give credit where it's due -- grudgingly.

- **Pre-computed gauntlet is the right call.** The cinematic sequence never blocks on Gemma. I've seen teams make the entire flow dependent on LLM latency and it's a nightmare. This architecture is correct.
- **State machine is clean.** The gauntlet phase + fight phase separation is exactly right. Two orthogonal state dimensions, no conflating.
- **`applyRerollResult` is a pure function.** Immutable update, recomputes derived state (W/L/D), returns a new Build. Testable, predictable. This is how it should be done.
- **Structural loss is an explicit state, not hidden.** Design decision #4 in the spec is correct -- the most important signal is when the gap can't be fixed. The messaging is honest without being demoralizing.
- **No XSS surface.** Markdown content is rendered as text nodes via `whitespace-pre-line`, not `dangerouslySetInnerHTML`. Safe.
- **Mock API is clean.** Proper delay simulation, returns the right shapes, doesn't leak into production code path.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

**Required changes (in priority order):**
1. **SERIOUS:** Surface rescore errors to users (Finding 1) -- route to implementation agent
2. **SERIOUS:** Add double-click guard on rescore (Finding 2) -- route to implementation agent
3. **MODERATE:** Fix stale build reference with `getState()` (Finding 3) -- route to implementation agent
4. **MODERATE:** Add reroll count display/limit (Finding 4) -- route to implementation agent
5. **MODERATE:** Add defensive state reset in BossFightCard (Finding 5) -- route to implementation agent
6. **MINOR:** Add fallback for malformed NextSteps markdown (Finding 6) -- route to implementation agent

#### Questions for the Author

1. What is the backend's max reroll count per fight? The client should know this and enforce it defensively.
2. Is there any request timeout on the `getNextSteps` call? Gemma inference can hang -- what happens if it takes 30s? 60s? The loading state will spin forever.
3. What's the monitoring/alerting story for reroll failures? If Gemma starts returning 500s on rescore, how does the team find out before students report it?
4. The `StructuralLoss` component uses a raw `motion.button` instead of the shared `Button` component. Was that intentional? It creates a maintenance divergence if Button's styles change.

---

## §9 Verification

**Status:** COMPLETE (2026-04-14)

### Backend
| Check | Result |
|-------|--------|
| Lint (ruff) | PASS — All checks passed |
| Type check (mypy) | N/A — 44 pre-existing errors, no backend changes in this spec |
| Tests (pytest) | PASS — 0 collected (no backend changes) |

### Frontend
| Check | Result |
|-------|--------|
| TypeScript | PASS — 0 errors |
| Tests (vitest) | 87 pass, 2 fail (pre-existing ProfileScreen) |
| Production build (Vite) | PASS — 448KB bundle, 846ms build |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | — |

---

## §10 Discussion

```
[2026-04-14 12:00] @faang-staff-engineer → @implementation-agent
Code review complete. Verdict: CHANGES REQUIRED (no blockers).

6 findings: 2 SERIOUS, 3 MODERATE, 1 MINOR. See §8 for full details.

Priority fixes:
1. Surface rescore errors to users (silent catch swallow in handleRescore)
2. Add double-click guard on rescore button (race condition via stale isRescoring)
3. Use getState() for build reference in async handlers (stale closure risk)
4. Add reroll count display/cap (no client-side limit enforcement)
5. Defensive state reset in BossFightCard on entrance phase
6. Fallback rendering for malformed NextSteps markdown

The architecture is sound. These are execution-level fixes, not design rethinks.
```

---

## §11 Final Notes

**Human Review:** PENDING

**Context for agents:**

- **DESIGN.md is the source of truth** for all visual decisions. Read it before writing any UI code. If DESIGN.md and existing code disagree, DESIGN.md wins.
- **The Boss Fight Entrance sequence** is defined in DESIGN.md's "Key Animation Sequences" and implemented in `motion.ts` as `bossFight.*`. Use these presets — do not improvise animation parameters.
- **Boss colors are semantic.** Each boss has a signature hue defined in DESIGN.md's "Boss Colors" table. The fight card, emoji glow, result animations, and progress indicators all use the boss's color token. Never mix boss colors.
- **The gauntlet is pre-computed.** `build.gauntlet.fights[]` and `build.skill_pool[]` are already populated from the F3 build orchestration. The gauntlet screen reads from store — it does NOT call the gauntlet API for initial fight results. Only rerolls and next steps are live API calls.
- **Reroll mutates both server and client state.** The `POST /build/{id}/reroll` API updates the server-side build. The client must also update the local `Build` object in `buildStore` — replace the fight, move skills from `skill_pool` to `skills_crafted`, recompute W/L/D totals.
- **Structural loss is a feature, not a failure.** The "pool exhausted" message is deliberately written. Use it verbatim from the PRD: "Every available skill for this fight has been equipped..." This is the most important coaching moment in the product.
- **Next Steps drops all RPG metaphor.** The checklist is data-grounded, empowering, and respectful of parents. It's the deliverable the student prints and brings to a real-world meeting. Tone matters here.
- **ReceiptPanel from F3** is reused for fight receipts. Each fight score has a "?" icon that expands to show raw score, thresholds, and contributing stats.
- **Header dims during boss fights.** DESIGN.md specifies 60% opacity on the header during the gauntlet. Implement this as a class toggle on the AppHeader component, controlled by the gauntlet phase.
- **Mock API handlers** must return data shaped exactly like the backend models. The reroll mock should return a `BossFightResult` with `rerolled: true`, `reroll_count` incremented, and `original_result` preserved. The next steps mock should return a markdown string with four `##` sections.
- **Emotional target:** This screen alternates between tension (will I win?) and empowerment (I can fight back). The reroll mechanic is the key — it transforms a passive scorecard into an interactive coaching conversation. Losses that flip to wins should feel earned. Structural losses should feel honest, not punitive.

---
