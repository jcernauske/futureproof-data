# Feature: Save + Wrapped Share Experience (Screen 9)

## Claude Code Prompt

```
Read the spec at docs/specs/screen-save-wrapped.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, DuckDB build persistence, Playwright rendering pipeline, API design, state management)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 mockups and propose the premium implementation
   - Visionary validates: Wrapped frame designs (1080×1920 story format), Brightpath token usage, frame-to-frame transitions, share/download UX
   - Cross-reference DESIGN.md (source of truth)
   - Writes to §3 with any enhancements or adjustments

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code
   - Backend: rewrite builds.py to use DuckDB instead of flat JSON files (see §4 Build Persistence)
   - Backend: implement Wrapped frame HTML templates + Playwright rendering endpoint
   - Frontend: implement save confirmation, Wrapped story viewer, download/share buttons
   - Use Brightpath design tokens exclusively
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - Wrapped viewer: frame navigation, frame content, download triggers
   - Save flow: build persisted, confirmation shown
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance
   - Confirm: Wrapped frames match design system on dark background, correct fonts/colors at 1080×1920
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
   - Generate report to reports/screen-save-wrapped-YYYY-MM-DD.md
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
| Created | 2026-04-15 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-15 (post-arch-review patches) |
| Blocked By | F5 (branch tree) |
| Related Specs | `screen-branch-tree` (F5), `screen-menu-compare-chat` (F7, not started) |

---

## §1 Feature Description

### Overview

Build Screen 9 of the FutureProof flow: save the build and generate a Spotify Wrapped-style multi-frame story sequence optimized for Instagram Stories (1080×1920). This is the viral growth mechanic — the student taps through their build story, screenshots or downloads individual frames, shares to Stories, and their friends see "Steady Bold Turtle 🐢 just speced ISU Business" and want to try it themselves.

The screen has two distinct parts:
1. **Save confirmation** — the build is persisted, the student sees a success state with their build summary
2. **Wrapped story viewer** — a tappable multi-frame story sequence they can screenshot/download/share

### Emotional Target

**Proud ownership.** The student has been through the full experience — reveal, boss fights, skill crafting, branch tree. Now they own it. The Wrapped frames turn their build into a shareable identity artifact. "I'm Steady Bold Turtle 🐢" is the social currency.

### Problem Statement

The student has a complete Build with stats, gauntlet results, crafted skills, and branches. They need to:

1. **Save the build** to their profile (persisted by profile name, retrievable later)
2. **See their story** as a tappable multi-frame sequence
3. **Download individual frames** as 1080×1920 PNGs for Instagram Stories
4. **Share the sequence** or individual frames via native share sheet (mobile) or download (desktop)
5. **Navigate to the post-build hub** (Screen 10 / F7) for compare, chat, or new build

### Core Loop Integration

The social loop from PRD v8: Student builds → shares Wrapped frames → caption: "I'm Steady Bold Turtle 🐢" → friend sees it → "what name did you get?" → friend opens FutureProof → repeat.

The CTA frame includes the FutureProof URL. The identity frame is designed to trigger "what did you get?" curiosity.

### Success Criteria

- [ ] Build saves on navigation to Screen 9 (auto-save, not a separate action)
- [ ] Save confirmation shows build summary: profile name, school, career, W/L/D tally
- [ ] 6-frame Wrapped story sequence renders in a tappable viewer
- [ ] Frame 1 (Identity): profile name + emoji + school + major
- [ ] Frame 2 (Pentagon): five-stat radar chart with values
- [ ] Frame 3 (Boss Scorecard): 5 boss results + Final Boss verdict
- [ ] Frame 4 (Comparative Insight): standout stat contextualized
- [ ] Frame 5 (Risk Highlight): biggest risk boss identified
- [ ] Frame 6 (CTA): "See where your path leads → futureproof.app"
- [ ] Each frame downloadable as 1080×1920 PNG
- [ ] "Download All" option creates all 6 frames
- [ ] Backend renders frames via Playwright (HTML template → PNG screenshot)
- [ ] Tappable viewer: tap right to advance, tap left to go back, progress dots at top
- [ ] CTA to advance: "Done" → Screen 10 (menu/compare/chat, F7)
- [ ] All Brightpath design tokens used in frame templates
- [ ] Responsive: story viewer works on both mobile (native feel) and desktop (centered card)
- [ ] All tests pass

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Server-side Playwright rendering for PNGs | Instagram Stories requires 1080×1920 image files. HTML-to-canvas client-side (html2canvas) is unreliable with custom fonts, gradients, and SVG. Playwright (headless Chromium) on the backend produces pixel-perfect screenshots from styled HTML templates. | html2canvas (font rendering issues, gradient artifacts), Canvas API (no HTML layout engine), pre-rendered static templates (can't personalize), pyppeteer (unmaintained) |
| 2 | 6 frames, not 1 combined image | The story format (tap to advance) matches Instagram Stories UX. Each frame is self-contained and shareable individually. A single combined image would be too dense and doesn't match the platform format. | Single share card (too dense, no story feel), 3 frames (too sparse), video (scope too large for hackathon) |
| 3 | Auto-save on navigation, not explicit save button | The student has already committed by going through the full flow. Making them tap "Save" is friction with no benefit. Save happens automatically when they reach Screen 9. | Explicit save button (unnecessary friction), save after each screen (premature — build isn't complete until after gauntlet) |
| 4 | Frame templates are HTML files, not React components | The Playwright rendering pipeline needs standalone HTML files it can screenshot. They use the same Brightpath CSS variables but don't need React, Framer Motion, or any JS framework. | React components rendered by Playwright (heavier, more dependencies), SVG-only frames (no HTML layout flexibility), inline styles only (hard to maintain) |
| 5 | Download as individual PNGs, not a zip | Students screenshot individual frames to share on Stories. A zip file doesn't match the use case. "Download All" saves each frame individually to the downloads folder. | Zip file (extra step to extract), combined PDF (wrong format), video export (scope) |

### Constraints

- **Playwright is a required (not optional) backend dependency.** It pulls in a headless Chromium binary (~150–280MB). Documented in README as a setup step: `pip install -e .[dev] && playwright install chromium`. No graceful degradation — if Playwright is unavailable, the render endpoint returns 500 and the feature is considered broken. (This is a hackathon trade-off; see §5 C5 resolution.)
- Frame rendering adds 1–3 seconds per frame (Playwright launch + screenshot). Pre-render all 6 frames when the build completes, or render on demand with a loading state.
- The Wrapped endpoint (`GET /build/{build_id}/wrapped`) currently returns 501. This spec implements it.
- Frame templates need the Brightpath fonts (Fredoka, Nunito, Space Mono) available to Playwright. Embed fonts as base64 `@font-face` in each template for offline-safe rendering.

---

## §3 UI/UX Design

> Author: @fp-design-visionary. Source of truth: `DESIGN.md`.
> All tokens cited by exact CSS variable name or Tailwind class. Pixel values assume 1080×1920 for rendered frames and 16px base for the in-app viewer.

### Emotional Target — Proud Ownership

The student has earned this. They walked through character select, school, effort, reveal, the gauntlet, the branch tree. Now they get a trophy case. Not a receipt. Not a dashboard. A trophy case.

Every frame needs to feel like the student could frame it on their wall. The student is not "viewing their results" — they are **being handed an identity artifact**. The Wrapped sequence is the payoff for the whole flow, and Frame 1 is the moment where they see their name with their emoji at 136px and feel "that's me. That's the bear I built."

When their friend sees this on Instagram Stories at 1am, the name "Steady Bold Turtle 🐢" should read as a badge of identity, not a label on a chart. The friend should think *what did I get?* before they finish reading the caption.

### Hero Moment per Frame (the photographable centerpiece)

| Frame | Hero | Why it's the hero |
|-------|------|-------------------|
| 1 Identity | Profile name set 140px in Fredoka 700, emoji 160px above | This is the viral trigger. Everything else serves it. |
| 2 Pentagon | The radar polygon, 720px across, filled with a multi-stat gradient | It's the literal shape of the build. Screenshot-worthy. |
| 3 Boss Scorecard | The giant verdict line ("SOLID BUILD") 88px Fredoka | The emotional summary of the gauntlet. |
| 4 Comparative Insight | The stat value, 240px Space Mono 700 in stat color | A single number that makes the student proud. |
| 5 Risk Highlight | The boss emoji 180px with a glow halo | The villain of the story gets a portrait. |
| 6 CTA | The fake button "futureproof.app" pulsing with a thrive halo | The viewer's eye must land here. |

---

### Phase 1: Save Confirmation (in-app, desktop + mobile)

**Emotion:** *relief and pride.* The student sees their build commit to the system. This is a breath before the trophy case.

**Timing:** Minimum 1.5s, maximum 2.2s if frames are still rendering (see Loading state below). Crossfades to Phase 2.

**Surface:** Full viewport. Background = the app's ambient gradient + noise overlay (DESIGN.md "Surface Treatments"). No header dimming — the AppHeader stays in its Screen 9 state (visible, profile name in `text-secondary`).

**Composition (vertical stack, centered, 480px max-width column):**

```
                          ┌───────────────┐
                          │    (glow)     │
                          │       🐢       │   ← 88px emoji, --shadow-glow-thrive halo
                          │    (glow)     │
                          └───────────────┘
                                ◯
                              ✓ check      ← 32px circle, --color-accent-thrive fill
                                            --shadow-glow-thrive, scales in

                           Build saved      ← Fredoka 700, --text-display (36px),
                                              --color-text-primary
                                              gradient underline 1px → thrive to insight

                     Steady Bold Turtle       ← --text-subheading, --color-text-secondary
               ISU Business · Financial Analyst

                        3W · 1D · 1L          ← --text-data-lg (24px), Space Mono 700
                                              wins in --color-accent-thrive
                                              draws in --color-accent-caution
                                              losses in --color-accent-alert

                 ────────────────────         ← 60px wide, --color-border-subtle

                  Opening your wrapped…       ← --text-small, --color-text-muted
                                              shimmer: opacity 0.4 → 0.8 → 0.4 over 2s
```

**Motion choreography:**
1. `t=0ms` — screen fades in (300ms ease, `transitions.fade`).
2. `t=120ms` — emoji scale-in (`transitions.scaleIn`, `springs.bouncy`, from scale 0.8). The glow halo animates from opacity 0 to 0.35 concurrently.
3. `t=320ms` — check circle pops in on top of the emoji's lower-right quadrant with `springs.bouncy`, scale 0 → 1. The check mark itself strokes in via SVG `pathLength` 0 → 1 over 250ms.
4. `t=480ms` — "Build saved" slides up 12px and fades in (`transitions.fadeInUp`).
5. `t=620ms` — metadata line (name + school + career) fades in.
6. `t=760ms` — tally line: each segment (W / D / L) counts up from 0 over 600ms with Space Mono 700. Counting uses easeOut, not springs (counters should feel mechanical, not bouncy — see Stage 2 Reveal stat counters pattern).
7. `t=1400ms` — "Opening your wrapped…" fades in with the breathing shimmer.
8. `t=1500ms` (minimum) — if frames are ready, crossfade (400ms, `transitions.fade`) into Phase 2. If not ready, the shimmer continues until they are, then crossfade.

**Why it works:** The emoji-plus-check combo is the "save committed" signal without needing a word for it. The metadata ties the student's identity to their choices ("Steady Bold Turtle · ISU Business"). The tally previews the trophy case. The shimmer converts "waiting" into "anticipation."

---

### Phase 2: Wrapped Story Viewer (in-app)

**Emotion:** *curated reveal.* Each frame is handed to the student one at a time. They control pacing. They feel like a curator, not a consumer.

#### Desktop layout (≥ tablet breakpoint, 768px+)

```
┌──────────────────────────────────────────────────────────────┐
│  AppHeader (56px, normal Screen 9 state)                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                                                              │
│          ● ● ● ○ ○ ○   ← progress dots, top of stage        │
│      ┌────────────────────┐                                  │
│      │                    │                                  │
│      │                    │                                  │
│      │                    │                                  │
│      │    FRAME PNG       │   ← 9:16 card, 360w × 640h       │
│      │   (1080×1920       │      rounded-xl (20px)           │
│      │    source)         │      shadow-lg                    │
│      │                    │      border-subtle                │
│      │                    │                                  │
│      │                    │                                  │
│      │            3 / 6   │   ← frame counter, bottom-right  │
│      └────────────────────┘                                  │
│                                                              │
│   [Download this frame]  [Download all]    [ Done → ]        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

- **Stage:** `--color-bg-void` (#12131F). The global ambient gradient continues beneath, but the stage dims it by overlaying a `radial-gradient(ellipse 70% 50% at 50% 40%, rgba(18,19,31,0) 0%, rgba(18,19,31,0.55) 100%)` so the frame card sits in a pool of darker light. This is the "theater" — the frame is lit, the rest is recessed.
- **Frame card container:** 360×640px (9:16). Positioned in the vertical center of the stage minus 40px (bias toward the top so the action bar sits comfortably below without crowding). `background: --color-bg-deep` (shows through before the `<img>` loads). `border-radius: --radius-xl` (20px). `border: 1px solid --color-border-default`. `box-shadow: --shadow-lg` plus a soft `0 0 60px rgba(125, 212, 163, 0.08)` ambient halo — a breath of thrive light, not a glow, so the card feels "presented" without screaming.
- **Frame image:** `<img>` fills the card, `object-fit: cover`, `border-radius: inherit`. The PNG is 1080×1920 source, so it downsamples to 3x retina inside a 360×640 container — always crisp.
- **Progress dots:** anchored 16px above the card, centered. See *Progress Dot Animation* below.
- **Frame counter:** absolute-positioned inside the card, `bottom: 14px; right: 16px`. Space Mono 400, 11px, `--color-text-muted`. Sits on top of any frame content. For frames where the bottom-right would clash with content (e.g., the CTA frame's fake button), the counter shifts to `bottom: 14px; left: 16px` automatically — always in a corner, always readable.
- **Action bar (below card, 32px gap):** horizontal flex, centered, 16px gap.
  - Primary: "Download this frame" — standard Primary button from DESIGN.md (height 48px, `--color-accent-thrive` background, `--color-text-inverse` text, `--radius-lg`). Icon: download glyph (Lucide `download`) 16px, 8px left of label.
  - Secondary: "Download all" — Secondary button (height 44px, transparent background, `--color-accent-info` text, 1px info-tinted border).
  - Ghost: "Done →" — Ghost button (height 40px, transparent, `--color-text-secondary`). Anchors the far right with a 40px separator from the Secondary button.

#### Mobile layout (< tablet breakpoint)

The stage becomes the full viewport. The frame card expands to fill width minus 20px margin, with 9:16 aspect ratio preserved. Progress dots sit in a safe-area-inset row at the top of the viewport. The action bar becomes a fixed bottom bar:

```
┌─────────────────────────┐
│ ● ● ● ○ ○ ○              │  ← 12px top-safe-area-inset padding
├─────────────────────────┤
│                         │
│                         │
│      FRAME PNG          │  ← fills 9:16 within viewport minus bars
│   (the whole screen     │     rounded-xl, border-subtle
│    is basically the     │
│    frame)               │
│                         │
│              3 / 6      │
│                         │
├─────────────────────────┤
│ [Download] [All] [Done] │  ← fixed bottom, 64px + safe-area-inset
└─────────────────────────┘
```

- Bottom bar uses `--color-bg-deep` at 92% opacity with a 1px `--color-border-subtle` top border. No backdrop-filter — relying on compositor-dependent blur is fragile on Android Chrome. Solid-ish fill is fine.
- Button labels shorten on mobile: "Download", "All", "Done". Icons-only would be cleaner but first-time users need labels.
- Tap targets: every button is minimum 44×44px.

#### Progress Dot Animation (the 4px → 20px pill transition)

This is the viewer's single most important chrome element. Six indicators, top of stage.

**Base state per dot:**
- Size: `4px × 4px` (fully round, `--radius-full`).
- Color: `--color-bg-surface` (future), `--color-text-secondary` (past), `--color-accent-thrive` (current).
- Gap between dots: `6px` (margins). Row centers horizontally.
- Container: `display: flex; align-items: center; gap: 6px`.

**Current-frame expansion:**
- When a dot becomes current, it animates from `width: 4px, height: 4px, border-radius: 9999px` to `width: 20px, height: 4px, border-radius: 9999px` (stays a fully-rounded pill, just horizontally stretched).
- Motion: `springs.snappy` (`{ stiffness: 400, damping: 25 }`). ~180ms perceived.
- Concurrently, the dot's color crossfades from whatever it was (future `--color-bg-surface` on forward nav, past `--color-text-secondary` on back nav) to `--color-accent-thrive`. 250ms ease.
- When the dot stops being current (user taps forward), it snaps back to 4px and transitions to `--color-text-secondary` (past) using `springs.smooth` so it feels like it "settled back down."

**Why a pill, not a fill bar:** A filling-up progress bar inside the pill would feel like a timer (implies auto-advance). We deliberately do NOT auto-advance — the student controls pacing. A static pill says "you are here" without promising "time is running out."

**Framer Motion variant (illustrative):**

```tsx
const dotVariants = {
  past: { width: 4, backgroundColor: "var(--color-text-secondary)", transition: springs.smooth },
  current: { width: 20, backgroundColor: "var(--color-accent-thrive)", transition: springs.snappy },
  future: { width: 4, backgroundColor: "var(--color-bg-surface)", transition: springs.smooth },
};
```

#### Tap Zone Feedback

Left 30% of the frame card = "previous," right 70% = "next." No visible buttons — matches Instagram Stories muscle memory. But "no visible buttons" doesn't mean "no feedback."

- **Invisible by default.** The tap zones are transparent overlays on the frame card.
- **On tap (pointerdown):** a subtle glow overlay flashes. Right-side tap: a gradient wash `radial-gradient(circle at 85% 50%, rgba(125, 212, 163, 0.10) 0%, transparent 50%)` fades in over 60ms, then out over 220ms. Left-side tap: same gradient mirrored on the left side. The glow color matches `--color-accent-thrive` forward, `--color-text-secondary` at 10% opacity backward (so going back feels slightly less celebratory, subtly biasing forward progression).
- **No ripple.** Material ripples break the plush aesthetic. A warm gradient wash is the right metaphor — like a breath passing through.
- **Keyboard focus:** arrow left / arrow right navigate. Space advances. Escape triggers "Done →". When keyboard-navigating, each frame card gets a visible focus ring using `--color-focus-ring` (info at 40%).
- **Edge behavior:** tapping right on frame 6 → no-op plus a subtle shake (`transitions.press` on the action bar's Done button to direct attention). Tapping left on frame 1 → no-op plus a gentle bounce of the frame card (`transform: translateX(-6px)` then `0` over 200ms).

#### Frame-to-Frame Transition Choreography

Not just a slide. The incoming frame's content has a staggered micro-reveal so it never feels like a static slideshow.

**Outgoing frame:**
- Slides horizontally `translateX: 0 → ±100%` (forward: -100%, back: +100%) over 280ms, `springs.smooth`.
- Concurrently fades `opacity: 1 → 0.4` (not to 0 — a ghost of it is still visible at the edge during the exchange).

**Incoming frame:**
- Enters from the opposite side with `translateX: ±100% → 0` over 280ms, `springs.smooth`.
- **Opacity: 1 from t=0.** The frame image itself is fully opaque immediately — we don't fade a trophy in.
- **But the frame image has no interior animation** because it's a PNG. So we layer a **top-to-bottom "illumination wipe"** on top of the incoming frame: a gradient overlay `linear-gradient(180deg, rgba(125, 212, 163, 0.0) 0%, rgba(125, 212, 163, 0.14) 50%, rgba(125, 212, 163, 0.0) 100%)` that animates from `translateY: -100% → 100%` over 480ms starting at `t=120ms` (so it begins after the slide has settled most of the way). The effect: the new frame appears to "wake up" — a soft pass of light rolls across it once. Then it sits still.
- The progress dot for the new current frame expands simultaneously with the slide (not after).

**Why this matters:** without the illumination wipe, the sequence feels like an image carousel. With it, each frame feels *activated*. The student tapped, and the frame responded.

**Direction asymmetry:** going backward, the illumination wipe uses `--color-text-secondary` at 6% opacity (not thrive). Forward = celebratory. Backward = reflective. Subtle, but the student's subconscious picks it up.

#### Loading State (Playwright render in progress)

First-visit rendering can take 6–18 seconds. This is a critical UX problem — we cannot show a blank stage for 12 seconds.

**Strategy: preview the trophy case while it develops.**

During `POST /build/{id}/wrapped/render`:

1. The Phase 1 save confirmation stays visible until it completes OR up to 2.2s max.
2. After 2.2s, crossfade to Phase 2 layout but with the frame card in a **"developing" state**:
   - Frame card container: same 360×640 dimensions, same shadow.
   - **Inside the card:** a centered vertical stack:
     - Profile emoji at 64px (pulled from `profileStore`), subtle thrive glow.
     - "Developing your wrapped…" in Fredoka 600, 20px, `--color-text-primary`.
     - A darkroom metaphor: beneath the emoji, a Space Mono 11px line counter that advances as frames come in: "Frame 1 of 6 · Frame 2 of 6 · Frame 3 of 6 · …" Each count crossfades when the next arrives.
     - Subtle "film grain" shimmer — the noise overlay at 4% opacity animated slowly.
   - Progress dots are visible but all rendered in `--color-text-muted` at 50% opacity (no current, no thrive). They light up as each frame completes rendering (dot N turns `--color-bg-surface` as soon as frame N's PNG URL is available).
   - Action bar buttons are disabled (text at 40% opacity, no hover state, `cursor: not-allowed`).
3. The backend ideally streams availability — either by polling `GET /build/{id}/wrapped` every 800ms or via SSE. The moment frame 0 is available, the card content crossfades out and frame 0's image fades in with the "illumination wipe." Each subsequent frame is pre-loaded in the background so taps don't re-trigger network.
4. If rendering exceeds 20 seconds, show a soft retry button below the card: "Something's taking a while. Retry?" Ghost button style, `--color-accent-caution` text.

**Why the darkroom metaphor:** "Developing" is an analog photography term. It makes a technical wait feel like anticipation — the student is watching their own story come into being. This is thematically aligned with the "trophy case" emotional target. Do NOT use a spinner. Do NOT use a progress bar filling up. Spinners say "computer working." The darkroom says "your film is coming out."

#### Error State (Playwright rendering fails)

If the `POST /wrapped/render` call returns non-200 or the subsequent `GET /wrapped` shows zero frames after 30s:

- Frame card content switches to an "error" composition:
  - Emoji at 64px (dimmed to `--color-text-muted`).
  - Fredoka 600, 22px, `--color-accent-alert` — "Your wrapped didn't develop."
  - Nunito 400, 14px, `--color-text-secondary` — "We couldn't render your story right now, but your build is safely saved."
  - Primary button inside the card: "Try again" — calls render endpoint fresh.
  - Secondary ghost button: "Skip to menu →" — navigates to `/menu` (Screen 10).
- Action bar below: only "Done →" is enabled.
- Progress dots: hidden (replaced by the error composition inside the card).
- No full-screen takeover, no modal. The error is contained inside the frame card so the student doesn't feel like the whole app broke.

#### Empty / Edge Cases

- **No crafted skills on Frame 5:** the "But you fought back:" subsection is hidden; the risk description gets a 20px bottom margin to rebalance. See Frame 5 variant spec below.
- **Clean sweep (all wins):** Frame 5 switches to the "CLEAN SWEEP" variant (see Frame 5 below).
- **Missing percentile data on Frame 4:** fall back to "Your strongest stat" with no percentile line. See Frame 4 variant spec.
- **Missing profile emoji:** fall back to a generic ✦ glyph in `--color-accent-thrive`. Never show an empty square.

---

### The 6 Wrapped Frames — Rendered at 1080×1920

**Shared canvas rules:**
- Canvas: 1080 × 1920 px, `background: --color-bg-deep` (#1B1D30).
- **Background treatment:** the page gradient from DESIGN.md "Background Gradient" is embedded at reduced intensity (replace the 0.5/0.35/0.6/0.25 alphas with 0.30/0.22/0.38/0.18 — the frames are small on a phone screen, so we don't need the full cinematic depth of the app). Noise SVG overlay at 2% opacity (not 2.5%), because compression on Instagram Stories crushes noise and we want it barely surviving.
- **Safe margins:** 72px top, 72px bottom, 72px left/right. Instagram's UI chrome (profile pill top-left, reply bar bottom) eats roughly 220px top and 180px bottom on most phones. We don't push critical content into those zones — so while the canvas is 1920 tall, the "safe zone" for hero content is roughly 240–1740 (a 1500px vertical band).
- **Wordmark footer (frames 1, 6 only):** "FUTUREPROOF" in Space Mono 700, 20px, letter-spacing 6px, `--color-text-muted`, 100px from bottom, centered. Frames 2–5 omit the wordmark to keep content focus.
- **Profile footer (frames 2–5):** profile emoji at 36px + profile name in Nunito 600, 18px, `--color-text-muted`, 90px from bottom, centered horizontally as a single inline-flex row with 10px gap. This is the persistent identity signature — "Steady Bold Turtle made this."
- **Fonts:** Fredoka 400/500/600/700, Nunito 400/600/700/800, Space Mono 400/700. All embedded as base64 `@font-face` in each template (WOFF2). No `@import`, no external CDN.
- **Renderer-safe constraints:** no `backdrop-filter`, no `filter: blur()` on dynamic content (static pre-rendered glows as radial gradients only), no `mix-blend-mode` beyond `normal`, no CSS `@property` registrations, no container queries. All rendered glows are solid radial gradients positioned with `background-image`.

---

#### Frame 1: Identity — the viral hook

**Emotion:** *"that's me."*

This is the single most important frame. The entire social loop depends on it. Someone sees "Steady Bold Turtle 🐢" on Instagram and thinks *what bear did I get?*

**Layout at 1080×1920 (y-axis from top):**

```
y=140    ┌─ "FUTUREPROOF" Space Mono 700, 20px, tracking 6px, --color-text-muted, centered

y=320    ┌─ Label row "JUST SPEC'D" Space Mono 700, 22px, tracking 4px,
         │   --color-accent-info, centered. A 1px hairline to the left and right
         │   of the label, 48px long each, --color-border-subtle, vertical center 18px.

y=440    ┌─ Emoji medallion. Emoji 160px centered.
         │   Behind the emoji: three layered radial halos (all positioned absolute,
         │   stacked z-below the emoji, centered on emoji center):
         │     • 360px diameter, radial-gradient from rgba(125,212,163,0.35) to transparent
         │     • 520px diameter, radial-gradient from rgba(184,169,232,0.18) to transparent
         │     • 720px diameter, radial-gradient from rgba(123,184,224,0.10) to transparent
         │   Result: a warm corona (thrive → insight → info) behind the emoji.
         │
y=680    │   ↓ emoji occupies roughly y=440..y=640 (200px slot for 160px emoji + padding)

y=740    ┌─ Profile name — the hero.
         │   "Steady Bold Turtle" in Fredoka 700, 140px, line-height 1.0,
         │   --color-text-primary, centered, max-width 920px.
         │   Text treatment: a linear-gradient fill clipped to text —
         │   background-image: linear-gradient(135deg, #F5F0E8 0%, #F5F0E8 45%,
         │                                            #7DD4A3 72%, #B8A9E8 100%);
         │   background-clip: text; -webkit-background-clip: text;
         │   color: transparent;
         │   The gradient starts as pure warm-white, transitions into thrive, then insight.
         │   Emotional read: the name is "lit up from within" by the Brightpath palette.
         │
         │   If the name is two words (e.g., "Steady Bold"), render on one line.
         │   If three words (e.g., "Steady Bold Turtle"), render on two lines:
         │     line 1: "Steady Bold" at 140px
         │     line 2: "Turtle" at 140px
         │     … actually no — render ALL three on two lines with line 2 containing
         │     just the animal noun. The animal is the punchline. See "name breaking rule" below.
         │
         │   Rendered emoji appears INLINE at the end of the last line, same vertical
         │   center as the baseline, at 120px. So: "Steady Bold\nTurtle 🐢" with the
         │   turtle emoji sized slightly smaller than the text cap height for optical balance.

y=1060   ┌─ Divider: 80px × 1px, --color-border-strong, centered.

y=1120   ┌─ "just speced" Fredoka 500, 44px, --color-text-secondary, centered.

y=1200   ┌─ School + major combined line.
         │   "ISU Business" in Fredoka 700, 72px, --color-text-primary, centered.
         │   Below (y=1300): "Financial Analyst" in Nunito 700, 40px,
         │   --color-text-secondary, centered.

y=1450   ┌─ Stat preview strip (optional but powerful):
         │   5 small stat dots (12px circles in stat colors) with stat abbreviations
         │   below (Space Mono 700, 16px, --color-text-muted), arranged in a
         │   horizontal row, centered, 40px gap between stats.
         │   ERN · ROI · RES · GRW · HMN — gives the frame a hint of "there's more
         │   where this came from" without showing full stats (that's Frame 2's job).

y=1720   ┌─ Ambient base glow:
         │   A radial-gradient ellipse at bottom center:
         │   background-image: radial-gradient(ellipse 800px 300px at 50% 100%,
         │                                      rgba(125,212,163,0.18) 0%, transparent 70%);
         │   Reads as "the floor glowing under the character." Anchors the frame.

y=1820   ┌─ FUTUREPROOF wordmark (Space Mono 700, 20px, tracking 6px,
         │   --color-text-muted), centered.
```

**Name breaking rule:** the `profile_name` in the build store comes as a single string like "Steady Bold Turtle". Algorithm: if 1 word → single line. If 2 words → single line. If 3 words → first two on line 1, last word on line 2, emoji inline with last word. If 4+ words → chunks of 2 per line. This keeps the animal noun + emoji as the punchline on its own line when possible.

**Type treatment — the gradient fill:** this is the craftsmanship detail. A flat white profile name would be "fine." A gradient-filled profile name (warm-white → thrive → insight) makes it feel like the name is *made of light*. It's the difference between a nameplate and a neon sign. The gradient must be subtle enough to read as "premium type styling" and not as "rainbow text" — hence 45% of the gradient stays in warm-white before the accents enter.

**Hero moment verdict:** the profile name, at 140px with gradient fill, against the emoji corona above it. This is the screenshot. Everything else defers.

---

#### Frame 2: Pentagon — the stat showcase

**Emotion:** *"look at the shape of me."*

The pentagon radar chart is a literal portrait of the build. Its silhouette is unique to this student's stats. The goal is to render it BIG enough that the shape itself is unmistakable at a glance on a phone screen.

**Layout at 1080×1920:**

```
y=160    ┌─ Section label "MY STATS" Space Mono 700, 22px, tracking 4px,
         │   --color-accent-info, centered, with hairlines each side as Frame 1.

y=260    ┌─ Profile name reprise: "Steady Bold Turtle 🐢" in Fredoka 600, 36px,
         │   --color-text-secondary, centered. This is the "who this belongs to" line.

y=380    ┌─ Pentagon SVG, 720 × 720px, centered (so roughly y=380..y=1100).
         │
         │   Grid: 4 concentric pentagons at 100%, 80%, 60%, 40% of max radius,
         │         stroke --color-text-muted at 12% opacity, 1.5px stroke-width.
         │   Axes: 5 radial lines from center, stroke --color-text-muted at 18% opacity.
         │
         │   Filled polygon: the five stat values mapped to radius (value/10 × maxRadius).
         │   Fill: radial-gradient from --color-bg-surface at center to a blend
         │   of accent-thrive + accent-insight at 42% opacity at edge.
         │   Stroke: 3px --color-accent-thrive at 70% opacity.
         │
         │   Vertex dots: 12px filled circles in stat color (ERN caution,
         │   ROI thrive, RES insight, GRW info, HMN empathy) at each polygon vertex.
         │   Each vertex has a 28px radial-gradient halo at 28% opacity underneath
         │   (pre-rendered, not animated).
         │
         │   Stat labels: OUTSIDE each vertex, 28px offset from the point.
         │   Abbreviation in Space Mono 700, 22px, stat color.
         │   Value below: Space Mono 700, 42px, stat color. Pentagon labels
         │   should align radially — left-vertices right-justify, right-vertices
         │   left-justify, top vertex centered above.

y=1180   ┌─ Five-stat pill row, centered, 16px gap.
         │   Each pill: 140px × 64px, rounded-full (--radius-full),
         │   background --color-bg-mid, 1px --color-border-subtle border.
         │   Each pill contains (horizontal flex, 10px gap, padded 20px):
         │     • 8px stat-color dot
         │     • Stat abbreviation (Space Mono 700, 20px, stat color)
         │     • Value (Space Mono 700, 28px, --color-text-primary)
         │
         │   Variant: if a stat is >= 8, pill gets a subtle stat-color glow
         │   (box-shadow 0 0 32px stat-color at 18% opacity — rendered as
         │   a layered background radial-gradient for renderer safety).
         │   This highlights strengths without needing a separate emphasis.

y=1320   ┌─ Insight line: the highest stat gets a small callout.
         │   Fredoka 600, 32px, highest-stat color, centered.
         │   Pattern: "{stat name} is your superpower."
         │   e.g., "AI Resilience is your superpower."

y=1480   ┌─ Spec card: three lines of Nunito, 22px, 14px gap.
         │   Line 1: school name, --color-text-primary, Fredoka 700, 32px.
         │   Line 2: career title, --color-text-secondary, Fredoka 500, 26px.
         │   Line 3: salary readout, Space Mono 700, 28px, --color-stat-ern —
         │           "$73k · starting · national median".
         │   These three lines live in the lower third and tie the pentagon
         │   shape to the real-world career it represents.

y=1790   ┌─ Profile footer (per shared spec): 🐢 · Steady Bold Turtle
```

**Why this beats "pentagon in the middle, stat list at the bottom":** we keep the pentagon as the silhouette hero but contextualize it with a three-line spec card at the bottom — naming the school, career, and salary. Without that, the frame is pretty but disconnected from the student's actual decision. With it, the frame says: *"this shape is what ISU Business → Financial Analyst looks like for me."*

**Hero moment:** the pentagon itself, especially the filled polygon's characteristic shape. Screenshot-worthy.

---

#### Frame 3: Boss Scorecard — the gauntlet verdict

**Emotion:** *"I fought five bosses. Here's the scoreboard."*

**Layout at 1080×1920:**

```
y=140    ┌─ Section label "BOSS GAUNTLET" with hairlines.

y=240    ┌─ Verdict line — THIS is the hero of this frame.
         │   Fredoka 700, 88px, line-height 1.0, verdict color, centered.
         │   max-width 920px. If wraps, 2 lines max.
         │   Content is the gauntlet verdict string from the build. Examples:
         │     • "SOLID BUILD with a gap." — --color-accent-thrive
         │     • "STRONG SPINE but watch the market." — --color-accent-caution
         │     • "ROUGH GAUNTLET — brave choices ahead." — --color-accent-alert
         │     • "PERFECT RUN." — --color-accent-thrive (for 5W)
         │   Text treatment: split into two type weights — the verdict phrase
         │   in uppercase ("SOLID BUILD") gets the verdict color at 100%;
         │   the qualifier ("with a gap.") in --color-text-secondary at 80% opacity.
         │   This draws the eye first to the verdict, then to the caveat.

y=520    ┌─ Tally bar: a 3-segment rounded pill, 680px × 64px, centered.
         │   Segments proportional to W / D / L counts.
         │   Segment colors: wins --color-accent-thrive at 22% fill,
         │   draws --color-accent-caution at 22%, losses --color-accent-alert at 22%.
         │   Segment text (centered in segment):
         │     "3 WINS" in Space Mono 700, 24px, --color-accent-thrive.
         │     "1 DRAW" same pattern in caution.
         │     "1 LOSS" same pattern in alert.
         │   Divider between segments: 1px --color-border-strong.
         │   If a count is 0, its segment has 0 width (collapses cleanly).

y=660    ┌─ The 5 boss rows, vertically stacked, 60px row height, 24px gap.
         │   Total block: y=660 to y=1380 (720px for 5 × 60 + 4 × 24 = 396px actual,
         │   so actually block height ~420px, center vertically in the slot).
         │
         │   Each row is a horizontal flex, 880px wide, centered:
         │
         │   ┌─────────────────────────────────────────────────────────┐
         │   │ [🤖] [Boss name Fredoka 700 34px]         [WIN pill]    │
         │   └─────────────────────────────────────────────────────────┘
         │
         │   • Boss emoji: 56px, left-aligned, in a 64px circle with boss-color
         │     background at 15% opacity, 1px boss-color border at 40% opacity.
         │   • Boss name: Fredoka 700, 34px, --color-text-primary.
         │     If result is LOSS, name color shifts to --color-accent-alert at 85%.
         │     If DRAW, name stays primary but prepended with an "≈" glyph.
         │   • Result pill: right-aligned, 140×56px, rounded-full.
         │     Win pill: --color-accent-thrive at 18% bg, --color-accent-thrive text,
         │               Space Mono 700, 22px, "WIN" centered.
         │     Loss pill: accent-alert at 18% bg, alert text, "LOSS".
         │     Draw pill: accent-caution at 18% bg, caution text, "DRAW".
         │
         │   Row backgrounds: each row has a subtle color tint.
         │     Win row: background linear-gradient(90deg, rgba(125,212,163,0.06) 0%,
         │                                              rgba(125,212,163,0.0) 60%).
         │     Loss row: same pattern with alert color.
         │     Draw row: same with caution color.
         │   This gives each row a soft left-edge glow in its result color
         │   WITHOUT needing a border — keeps the plush aesthetic.

y=1440   ┌─ 80px × 1px divider, --color-border-subtle, centered.

y=1500   ┌─ "FINAL BOSS" label: Space Mono 700, 22px, tracking 4px,
         │   --color-boss-ai (or boss-specific color for The Future), centered.

y=1560   ┌─ Final Boss name: Fredoka 700, 52px, --color-text-primary, centered.
         │   e.g., "The Future" with 🔮 inline 48px.

y=1650   ┌─ Final Boss verdict: Nunito 600, 26px, --color-text-secondary,
         │   centered, max-width 860px. The 1-sentence Gemma narrative from
         │   the final boss fight. No quotes.

y=1790   ┌─ Profile footer.
```

**Hero moment:** the verdict line at 88px. It's the single sentence that captures the entire gauntlet experience. Fredoka at that size with a color that matches the emotional read is what makes this frame photographable.

---

#### Frame 4: Comparative Insight — the standout stat

**Emotion:** *"I'm good at something specific."*

This frame takes one data point and makes it the entire story. Pure signal, no noise.

**Computed insight source:** the stat where the student's value is highest in absolute terms (ties broken by lowest AI exposure risk, so RES > others when tied). If percentile data is available from the distribution of this stat across all careers in the same CIP code, we cite it. If not, we use a flat framing.

**Layout at 1080×1920:**

```
y=160    ┌─ Section label "STANDOUT" with hairlines, in stat color
         │   (e.g., --color-stat-res purple if the standout is RES).

y=300    ┌─ Stat-specific icon, rendered as SVG, 180 × 180px, centered.
         │   Stat color fill at 100%.
         │   Behind the icon: concentric radial halos in stat color:
         │     • 280px halo at 30% stat color
         │     • 420px halo at 18% stat color
         │     • 600px halo at 8% stat color
         │   Result: the icon looks like it's burning with stat-colored light.
         │
         │   Icon mapping (per DESIGN.md "Custom stat icons"):
         │     ERN → coin   ROI → arrow-loop   RES → shield
         │     GRW → sprout HMN → heart-hand
         │   SVG embedded inline (not external file).

y=640    ┌─ Stat full name: Fredoka 700, 64px, stat color, centered.
         │   e.g., "AI Resilience"

y=740    ┌─ THE NUMBER. This is the hero.
         │   Space Mono 700, 240px, line-height 1.0, stat color, centered.
         │   Treatment: the number has a subtle gradient fill from
         │   stat-color at top 100% to stat-color at bottom 70% opacity —
         │   so it looks like it's catching light from above.
         │   Below the number, a "/ 10" suffix in Space Mono 400, 80px,
         │   --color-text-muted, inline to the right, baseline aligned with
         │   the number's midheight. "8" feels huge, "/ 10" feels small —
         │   compositional drama.

y=1120   ┌─ Thin gradient rule: 360px × 2px, linear-gradient from
         │   transparent → stat color → transparent, centered.

y=1200   ┌─ Percentile claim (if data available):
         │   Nunito 700, 36px, --color-text-primary, centered, max-width 880px.
         │   e.g., "Higher than 73% of Business paths."
         │   The "73%" is in stat color, Space Mono 700, 42px.
         │
         │   Fallback (no percentile data):
         │   "Your strongest stat." (Nunito 700, 36px, --color-text-primary).
         │   No number, no percentile. Never fake data.

y=1310   ┌─ Contextual explainer: Nunito 500, 26px, --color-text-secondary,
         │   centered, max-width 820px, line-height 1.35.
         │   One sentence. Examples:
         │     RES: "This career depends on skills AI can't easily replicate."
         │     ERN: "Your path clears six figures faster than most."
         │     ROI: "You recoup your tuition in record time."
         │     GRW: "This field is expanding — you're getting in early."
         │     HMN: "You'll spend your career helping real people."

y=1500   ┌─ Career context: small, understated.
         │   "Built at ISU Business · Financial Analyst"
         │   Nunito 600, 22px, --color-text-muted, centered.
         │   A micro-byline that anchors the stat to the build.

y=1790   ┌─ Profile footer.
```

**Hero moment:** the 240px number. At that size, in a stat color, glowing from its own icon's halo above it — it's a trophy. The student sees "8" and reads "I earned that."

---

#### Frame 5: Risk Highlight — the villain portrait

**Emotion:** *"here's what I need to watch out for — but I see it clearly."*

Loss is contemplative, not punishing (per design principles). This frame names the risk with weight but frames it as "a known thing I can plan around," not "a thing I failed at."

**Computed source:** the boss fight with the worst result. Prefer LOSS > DRAW > WIN. Ties broken by `risk_score` descending. If all 5 are wins → CLEAN SWEEP variant.

**Layout at 1080×1920 (default — loss or draw):**

```
y=160    ┌─ Section label "BIGGEST RISK" in --color-accent-alert,
         │   hairlines each side, centered.

y=280    ┌─ Boss portrait medallion.
         │   Boss emoji at 180px, centered.
         │   Behind: three layered halos in BOSS color (the specific boss color,
         │   e.g., --color-boss-loans amber for Student Loans):
         │     • 360px at 40% boss color
         │     • 520px at 22% boss color
         │     • 720px at 10% boss color
         │   A subtle 4% opacity noise overlay on top of the halos to give
         │   the boss a "villain atmospheric fog" texture.
         │
         │   Boss takes y=280..y=560 slot (280px for 180px emoji + padding).

y=620    ┌─ Boss name: Fredoka 700, 80px, boss color, centered.
         │   e.g., "STUDENT LOANS" in uppercase. The uppercase treatment
         │   makes it feel named, labeled, confronted.

y=740    ┌─ Result pill: LOSS or DRAW, large format.
         │   Pill: 200px × 68px, rounded-full, centered.
         │   LOSS: background accent-alert at 18%, border 1px accent-alert at 50%,
         │         text Space Mono 700, 28px, accent-alert — "LOSS".
         │   DRAW: same pattern in caution.
         │   Pill has a subtle glow (box-shadow 0 0 40px accent-alert at 15%),
         │   rendered as a layered radial-gradient background for renderer safety.

y=860    ┌─ Narrative block.
         │   Nunito 500, 32px, --color-text-primary, line-height 1.4,
         │   centered, max-width 880px, 2-3 sentences.
         │   This is the 2-sentence Gemma-generated risk narrative from the
         │   gauntlet, slightly extended for this frame. Example:
         │
         │     "Business majors graduate with $28k median debt. At Financial
         │      Analyst's starting salary, you'll need five years to clear it —
         │      if nothing else goes wrong."
         │
         │   This paragraph is the meat of the frame. It's compassionate truth.
         │   No blame, no doom. Just facts framed with care.

y=1180   ┌─ "BUT YOU FOUGHT BACK" bridge label (only if crafted skills exist
         │   for this boss):
         │   Space Mono 700, 20px, tracking 3px, --color-accent-thrive,
         │   centered, 36px vertical padding above and below.

y=1270   ┌─ Crafted skills row: 2–3 pills horizontally, centered, 16px gap.
         │   Each pill: height 56px, padding 0 24px, rounded-full,
         │   background --color-bg-mid, 1px --color-border-subtle,
         │   content: Fredoka 600, 22px, --color-text-primary + tiny ✦
         │   prefix glyph in accent-thrive.
         │   e.g., "✦ Budgeting 101", "✦ Income-Driven Repayment".

y=1450   ┌─ Forward-looking line (optional — skip if no crafted skills):
         │   Nunito 600, 24px, --color-accent-thrive, centered, max-width 820px.
         │   "You've already started building your defenses."
         │   Emotional balance: the risk is real, but the student is equipped.

y=1620   ┌─ Historical parallel (optional — pulls from boss narrative):
         │   Small italic line, Nunito 400 italic, 20px, --color-text-muted,
         │   centered, max-width 800px.
         │   e.g., "Everyone who took on this fight came out the other side."
         │   This is the "contemplative loss" cue — historical parallel,
         │   not punishment.

y=1790   ┌─ Profile footer.
```

**CLEAN SWEEP variant (all 5 fights won):**

```
y=160    ┌─ Label "CLEAN SWEEP" in --color-accent-thrive, hairlines.

y=280    ┌─ Victory medallion.
         │   Five boss emojis arranged in a pentagonal formation
         │   around a central ✦ glyph at 140px:
         │                    🤖
         │                 💰     📉
         │                    ✦
         │                 😮‍💨     🧱
         │   Each boss emoji: 88px with thrive-tinted halo (boss-color normally,
         │   but tinted toward thrive — each halo is blended:
         │   radial-gradient(boss-color at 25% → accent-thrive at 15% → transparent).
         │   Center ✦: --color-accent-thrive, 140px, with a massive 800px thrive halo.
         │
         │   Slot: y=280..y=920.

y=960    ┌─ "You beat them all." Fredoka 700, 88px, --color-text-primary, centered.
         │   "all" in --color-accent-thrive.

y=1120   ┌─ Tally: "5 WINS · 0 LOSSES" Space Mono 700, 40px,
         │   --color-accent-thrive, centered.

y=1240   ┌─ Gemma narrative: the Perfect Run verdict line, 28px Nunito 500,
         │   --color-text-primary, centered, max-width 880px.

y=1500   ┌─ "Rare. Most builds don't pull this off."
         │   Nunito 600, 26px, --color-text-secondary, centered, italic.
         │   Celebrates rarity without sounding boastful — frames the
         │   accomplishment as genuinely uncommon, which it is.

y=1790   ┌─ Profile footer.
```

**Hero moment (default):** the boss emoji medallion with the layered boss-color halo. At 180px with a 720px color corona behind it, the villain looks like it has real weight and gravity. It's a portrait, not an icon.

**Hero moment (clean sweep):** the pentagonal formation of bosses around the central ✦. It's a trophy constellation.

---

#### Frame 6: CTA — the viral hook

**Emotion:** *"I want to try this."* (from the perspective of the friend who sees it)

This is the only frame designed for a non-student viewer. Frame 1 has already done the "what name did you get?" work. Frame 6 delivers the URL with aspirational framing.

**Layout at 1080×1920:**

```
y=140    ┌─ "FUTUREPROOF" Space Mono 700, 22px, tracking 8px,
         │   --color-text-primary, centered. Slightly brighter than the
         │   footer version — this frame wants to be recognized as the brand
         │   call-to-action.

y=300    ┌─ Headline (the poetic hook):
         │   "See where your path leads."
         │   Fredoka 700, 96px, line-height 1.0, --color-text-primary, centered,
         │   max-width 940px. Two lines: "See where your" / "path leads."
         │   Text treatment: same gradient fill as Frame 1's profile name
         │   (warm-white → thrive → insight), but with the gradient
         │   concentrated on the word "path" so it catches the eye.
         │   Implementation: split the sentence into spans, apply the gradient
         │   only to the span containing "path leads".

y=560    ┌─ Subhead:
         │   "Build your own career profile in 2 minutes."
         │   Nunito 500, 36px, --color-text-secondary, centered,
         │   max-width 880px, line-height 1.35.

y=720    ┌─ Example path preview (the proof):
         │   A miniature "build card" showing what the viewer could get.
         │   Container: 720px × 280px, --color-bg-mid background,
         │   --radius-xl, 1px --color-border-subtle, centered.
         │   Padding: 40px.
         │
         │   Inside:
         │     • Animal emoji 80px, left-aligned, with thrive halo.
         │     • Right of emoji (flex row, 24px gap):
         │       — Line 1: "Your school → Your career" Nunito 700, 24px,
         │                 --color-text-primary.
         │       — Line 2: 5 stat dots (8px each) with abbreviations below
         │                 in Space Mono 400, 14px, --color-text-muted.
         │       — Line 3: "Fight five bosses. See where the branches lead."
         │                 Fredoka 500, 20px, --color-text-secondary.
         │
         │   This card signals "here's what you get" without showing anyone
         │   specific's build. It's aspirational, not prescriptive.

y=1060   ┌─ THE CTA — the fake button that has to feel tappable.
         │
         │   This is a PNG. There is no click event. But to the Instagram
         │   viewer, it has to LOOK like something they can tap.
         │
         │   Button geometry:
         │   • 540px wide × 120px tall, centered horizontally.
         │   • --radius-lg: 20px (slightly more than DESIGN.md's 14px because
         │     at 1080×1920 scale, 14px looks too sharp).
         │   • Background: linear-gradient(135deg, --color-accent-thrive 0%,
         │                                       #6bc494 50%,
         │                                       --color-accent-thrive 100%).
         │     This light-to-deeper-to-light gradient gives the button a
         │     sense of dimensional "roundness" — it reads as a physical
         │     object, not a rectangle. This is the key trick.
         │
         │   Shadow stack (all rendered as background layers, NOT box-shadow,
         │   because Instagram compression crushes soft shadows):
         │   • Outer halo: a 720 × 200 radial-gradient behind the button in
         │     rgba(125,212,163,0.28), blurred by being a large gradient ellipse.
         │   • Inner rim: a 1px inset border at rgba(255,255,255,0.35) top edge
         │     only (top 2px of the button is lighter — looks like a highlight).
         │   • Drop shadow: pseudo-element below the button,
         │     240 × 40 ellipse gradient, rgba(18,19,31,0.4) center → transparent.
         │     Gives the button a "lifted" appearance.
         │
         │   Button text:
         │   "futureproof.app" in Fredoka 700, 54px, --color-text-inverse
         │   (#1B1D30 — our dark canvas color, which against thrive green
         │   reads as "brand-confident text on a button" rather than stark black).
         │   Centered horizontally and vertically within the button.
         │
         │   Secondary tap-affordance cue: a small arrow glyph ( →  ) in
         │   Fredoka 700, 54px, 32px to the right of the text, same dark color.
         │   The arrow does three things: (1) indicates forward motion,
         │   (2) signals "this is a link," (3) fills the right-side empty
         │   space so the button doesn't feel text-left-heavy.

y=1260   ┌─ Two-line supporting bait (below the button):
         │   Line 1 (Nunito 700, 28px, --color-text-primary, centered):
         │     "Free. No signup. 2 minutes."
         │   Line 2 (Nunito 500, 22px, --color-text-muted, centered):
         │     "Powered by public data. Runs on any school's laptop."
         │
         │   Line 1 removes friction objections. Line 2 adds credibility.

y=1450   ┌─ Who made it attribution (the social proof):
         │   "Made by Steady Bold Turtle 🐢" Nunito 600, 26px,
         │   --color-text-secondary, centered, max-width 700px.
         │   This closes the loop with Frame 1 — the friend sees
         │   "Steady Bold Turtle made this" and thinks "and now I want my own."

y=1620   ┌─ Tiny trust row: three micro-badges in a horizontal row, centered.
         │   Each badge: Space Mono 400, 13px, --color-text-muted, icon + label.
         │   • ✓ "Public data"
         │   • ✓ "Open source"
         │   • ✓ "Private"
         │   These answer the "is this a scam?" subconscious check that
         │   a viral screenshot always triggers.

y=1800   ┌─ "FUTUREPROOF" wordmark Space Mono 700, 20px, tracking 6px,
         │   --color-text-muted, centered.
```

**Making the fake button feel tappable:**

The viewer is going to see this on Instagram. They can't tap it. But if it LOOKS tappable, they'll (a) screenshot it, (b) remember the URL, (c) type it into their browser later, or (d) swipe up for the story's real link.

Six craftsmanship moves that sell "tappable":

1. **Dimensional gradient:** the 135deg linear-gradient from thrive → deeper-thrive → thrive creates a subtle "curved metal surface" read. It looks like a physical object with a highlight, not a rectangle filled with color.
2. **Top-edge rim highlight:** 2px of `rgba(255,255,255,0.35)` at the button's top edge simulates the way real buttons catch light. This is the single most important detail — it's what your eye uses to register "3D object" vs. "flat image."
3. **Drop shadow ellipse:** the button "floats" above a soft shadow ellipse. Floating objects read as interactive.
4. **Outer halo:** the thrive-tinted halo at 28% opacity behind the button reads as "this thing is active / glowing." Hover states bleed into static design here.
5. **The trailing arrow:** → tells the eye "this goes somewhere." Buttons without directional hints feel stuck. Buttons with them feel like doors.
6. **Dark text on bright fill:** text-inverse (#1B1D30) on accent-thrive is the highest-contrast combination in our palette. High contrast = important = tappable.

**Hero moment:** the CTA button itself, with its corona halo. The viewer's eye naturally lands there because it's the brightest, warmest object in the frame.

---

### Frame Transitions (in-app viewer recap)

Detailed above under "Phase 2 → Frame-to-Frame Transition Choreography." Summary:

| Aspect | Spec |
|--------|------|
| Duration | 280ms per direction |
| Motion | `springs.smooth` on transform, ease-out on opacity |
| Outgoing frame | translateX to ±100% + opacity to 0.4 |
| Incoming frame | translateX from ∓100% + opacity 1 from t=0 |
| Illumination wipe | linear gradient overlay, translateY -100%→100%, 480ms, starts at t=120ms |
| Forward wipe color | rgba(125, 212, 163, 0.14) — thrive |
| Backward wipe color | rgba(196, 191, 176, 0.06) — text-secondary at low alpha |
| Progress dot transition | concurrent with slide, `springs.snappy` |
| Edge behavior | no-op + 6px shake |
| Auto-advance | Never |

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Save confirmation | `region-save-confirm` | status | "Build saved successfully" |
| Story viewer | `region-wrapped-viewer` | article | "Your build story — frame {n} of 6" |
| Frame | `frame-{n}` | img | Description of frame content |
| Progress dots | `nav-frame-progress` | navigation | "Story progress: frame {n} of 6" |
| Tap back zone | `btn-frame-back` | button | "Previous frame" |
| Tap forward zone | `btn-frame-forward` | button | "Next frame" |
| Download frame | `btn-download-frame` | button | "Download this frame as image" |
| Download all | `btn-download-all` | button | "Download all 6 frames" |
| Done CTA | `btn-done` | button | "Continue to menu" |

---

## §4 Technical Specification

### Architecture Overview

This spec has three major parts: (1) replacing the spike's flat-file JSON build persistence with DuckDB, (2) a backend Playwright rendering pipeline that turns HTML templates into 1080×1920 PNGs, and (3) a frontend story viewer with save confirmation and download functionality.

### Backend: Build Persistence (DuckDB)

The spike's `builds.py` saves builds as flat JSON files at `backend/data/builds/{build_id}.json`. This is replaced with a DuckDB table. DuckDB is already in the stack — Brightsmith uses it for Gold zone serving.

**File:** `backend/app/services/builds.py` (rewrite)

**DuckDB database:** `backend/data/futureproof.duckdb` — single file, same `data/` directory. Application state, not pipeline output.

#### Model Schema Changes

The `Build` and `BuildSummary` Pydantic models in `backend/app/models/career.py` gain a `profile_name` field. It **must be optional with a default of `""`** for backward compatibility with existing serialized builds (fixtures, in-flight DuckDB rows from this migration, and the frontend `Build` type):

```python
class Build(BaseModel):
    ...
    profile_name: str = ""   # NEW — set by create_build router from BuildRequest.profile_name

class BuildSummary(BaseModel):
    ...
    profile_name: str = ""   # NEW — denormalized, same value as the parent Build
    draws: int = 0           # NEW — add to match the `builds` DuckDB table and enable full W/L/D compare
```

The `create_build` router (`backend/app/routers/builds.py`) must set `build.profile_name = request.profile_name` on the Build object before calling `save_build()`. This removes the currently-dropped `profile_name` from `BuildRequest` and makes it flow end-to-end.

**Table: `builds`**

| Column | Type | Notes |
|--------|------|-------|
| build_id | VARCHAR | Primary key. Human-readable slug. |
| profile_name | VARCHAR | Profile name for lookup/filtering. |
| created_at | VARCHAR | ISO timestamp. |
| school_name | VARCHAR | Denormalized for list/compare queries. |
| major_text | VARCHAR | Denormalized. |
| career_title | VARCHAR | Denormalized. |
| ern | INTEGER | Denormalized for fast compare. |
| roi | INTEGER | |
| res | INTEGER | |
| grw | INTEGER | |
| hmn | INTEGER | |
| wins | INTEGER | |
| losses | INTEGER | |
| draws | INTEGER | |
| data | VARCHAR | Full Build JSON via `build.model_dump_json()`. |

**Key operations:**
```python
def save_build(build: Build) -> None:
    """Upsert build into DuckDB. Replaces any existing row with same build_id.

    Reads `profile_name` from `build.profile_name` — does NOT take it as a
    separate argument. Single source of truth: the Build model.
    """

def load_build(build_id: str) -> Build:
    """Load build by ID. Deserialize from data column.

    Raises:
        FileNotFoundError: if no row exists with that build_id. This
            preserves the contract expected by `app.state.get_build()`,
            which catches `FileNotFoundError` as its cache-miss signal.
            Do NOT let `duckdb.CatalogException` or a bare `None` leak
            out — wrap and re-raise as `FileNotFoundError`.
    """

def list_builds(profile_name: str | None = None) -> list[BuildSummary]:
    """List builds, optionally filtered by profile. Uses denormalized columns — no JSON parsing.

    When `profile_name` is None, returns all builds (matches current
    CLI behavior). When provided, returns only that profile's builds
    (used by profile.py service).
    """

def compare_builds(build_ids: list[str]) -> dict:
    """Compare 2-3 builds. Uses denormalized stat columns."""
```

**Contract preserved:** `load_build` raises `FileNotFoundError` on miss. `state.py:32` currently catches this and falls back gracefully; that code does NOT need to change. The DuckDB implementation must translate `duckdb.CatalogException` (or an empty fetchone result) into `FileNotFoundError` at the service boundary.

**Why DuckDB over flat files:** proper queries for list/compare/lookup-by-profile without globbing the filesystem, atomic writes (no partial JSON corruption), denormalized stat columns enable fast compare queries without deserializing every build, already a dependency, single file with zero config.

**Table: `wrapped_frames`**

| Column | Type | Notes |
|--------|------|-------|
| build_id | VARCHAR | FK to builds. |
| frame_index | INTEGER | 0-5. |
| png_data | BLOB | Rendered PNG binary. |
| rendered_at | VARCHAR | ISO timestamp. |

Wrapped frame PNGs are stored in DuckDB as BLOBs rather than on the filesystem. This keeps everything in one file and simplifies cleanup (delete build → delete frames via FK).

### Backend: Wrapped Rendering Pipeline

#### HTML Frame Templates

6 standalone HTML files in `backend/templates/wrapped/`:

| File | Frame | Content |
|------|-------|---------|
| `frame-identity.html` | 1 | Profile name, emoji, school, major |
| `frame-pentagon.html` | 2 | Pentagon radar chart (SVG) + stat pills |
| `frame-bosses.html` | 3 | Boss results + verdict + tally |
| `frame-insight.html` | 4 | Standout stat + contextual insight |
| `frame-risk.html` | 5 | Biggest risk boss + crafted skills |
| `frame-cta.html` | 6 | CTA with URL |

Each template:
- Uses Jinja2 or simple string substitution for build data
- Includes Brightpath CSS variables inline (no external stylesheet dependency)
- Embeds fonts via `@font-face` with base64-encoded WOFF2 or Google Fonts `@import`
- Fixed `<body>` size: `width: 1080px; height: 1920px`
- No JavaScript — pure HTML/CSS for Playwright screenshot

#### Playwright Rendering Service

**File:** `backend/app/services/wrapped_renderer.py`

```python
async def render_frames(build: Build, profile_name: str, animal_emoji: str) -> list[Path]:
    """Render all 6 Wrapped frames as 1080×1920 PNGs.
    
    Returns list of file paths to rendered PNGs in a temp directory.
    Playwright launches Chromium once, renders all 6 frames in the same
    browser context, then closes.
    """
```

- Uses `playwright` (Python async API) — not `pyppeteer` (unmaintained)
- Launches headless Chromium once per render batch
- Sets viewport to 1080×1920
- For each frame: loads template HTML with build data injected → `page.screenshot(type='png')`
- Saves PNGs to a temp directory, returns paths
- Cleanup: PNGs are ephemeral — served via the API, then deleted after a TTL

**Dependency:** `playwright` added to `pyproject.toml`. Requires `playwright install chromium` during setup (documented in README).

#### API Contract

**Pydantic response models** (add to `backend/app/models/career.py`, or a new `backend/app/models/wrapped.py`):

```python
class WrappedFrameInfo(BaseModel):
    """Metadata for a single rendered Wrapped frame."""
    index: int = Field(..., ge=0, le=5)
    url: str  # Relative path — frontend composes full URL via getFrameUrl()

class WrappedResponse(BaseModel):
    """GET /build/{build_id}/wrapped response."""
    frames: list[WrappedFrameInfo]

class RenderResponse(BaseModel):
    """POST /build/{build_id}/wrapped/render response."""
    status: Literal["ok", "cached"]  # "ok" = freshly rendered, "cached" = already existed
    frame_count: int
```

**Endpoints:**

| Endpoint | Method | `response_model` | Description |
|---|---|---|---|
| `GET /build/{build_id}/wrapped` | GET | `WrappedResponse` | Returns URLs to pre-rendered frame PNGs. 404 if build doesn't exist. 409 if frames not yet rendered (call `/render` first). |
| `GET /build/{build_id}/wrapped/{frame_index}` | GET | `Response(media_type="image/png")` — raw binary, not a Pydantic model | Serves individual frame PNG from the `wrapped_frames.png_data` BLOB. Must set `Content-Type: image/png` and `Content-Disposition: attachment; filename=futureproof-{build_id}-frame-{index}.png` to make the browser download link work. 404 if frame doesn't exist. |
| `POST /build/{build_id}/wrapped/render` | POST | `RenderResponse` | Triggers rendering of all 6 frames. Idempotent — if frames already exist and `build.created_at <= wrapped_frames.rendered_at`, returns `{"status": "cached", "frame_count": 6}` without re-rendering. |

**Flow:**
1. Frontend navigates to Screen 9.
2. Frontend calls `POST /build/{id}/wrapped/render` to trigger rendering.
3. Backend renders 6 frames, stores PNGs in `backend/data/wrapped/{build_id}/`.
4. Frontend calls `GET /build/{id}/wrapped` to get frame URLs.
5. Frontend loads each frame as `<img>` in the story viewer.
6. "Download" buttons trigger browser download of the PNG URL.

**Caching:** Rendered frames are stored in the `wrapped_frames` DuckDB table as BLOBs. If frames already exist for a build_id, skip re-rendering. Re-render if the build has been modified (check `build.created_at` against `wrapped_frames.rendered_at`).

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/career.py` | Modify | Add `profile_name: str = ""` to `Build` and `BuildSummary`; add `draws: int = 0` to `BuildSummary`. Add `WrappedFrameInfo`, `WrappedResponse`, `RenderResponse` Pydantic models (see §4 API Contract). |
| `backend/app/services/builds.py` | Rewrite | Replace flat JSON persistence with DuckDB (`builds` table + `wrapped_frames` table). `save_build(build)` takes only the Build (reads `build.profile_name`). `load_build` raises `FileNotFoundError` on miss. `list_builds(profile_name=None)` supports optional filter. |
| `backend/app/services/profile.py` | Modify | **Rewrite `_load_existing_profiles()` and `_get_builds_for_profile()`** to query the DuckDB `builds` table instead of globbing `backend/data/builds/*.json`. Both currently assume flat JSON — if left unchanged, the startup hook registers no profiles and profile lookup silently returns empty. `_get_builds_for_profile(normalized_name)` should delegate to `builds.list_builds(profile_name=normalized_name)`. |
| `backend/app/routers/builds.py` | Modify | In `create_build`, set `build.profile_name = request.profile_name` before calling `save_build`. Drop the currently-dropped plumbing that silently discards `profile_name`. |
| `backend/app/routers/wrapped.py` | Rewrite | Replace 501 stub with the three endpoints in §4 API Contract, using the new Pydantic response models. |
| `backend/app/services/wrapped_renderer.py` | Create | Playwright rendering service (`render_frames(build, profile_name, animal_emoji)`). |
| `backend/templates/wrapped/frame-*.html` | Create | 6 HTML frame templates (identity, pentagon, bosses, insight, risk, cta). |
| `backend/pyproject.toml` | Modify | Add `playwright` to dependencies. |
| `backend/app/state.py` | No change | The existing `FileNotFoundError` catch at `state.py:32` is preserved by the new `load_build` contract. |
| `frontend/src/screens/SaveWrappedScreen.tsx` | Create | Screen 9 top-level: save confirmation → wrapped viewer |
| `frontend/src/components/wrapped/WrappedViewer.tsx` | Create | Tappable story viewer: frame display, tap zones, progress dots |
| `frontend/src/components/wrapped/WrappedFrame.tsx` | Create | Single frame display (img element with loading state) |
| `frontend/src/components/wrapped/FrameProgressDots.tsx` | Create | 6-dot progress indicator |
| `frontend/src/components/wrapped/SaveConfirmation.tsx` | Create | Brief save success display |
| `frontend/src/api/wrapped.ts` | Create | API client for wrapped endpoints (with mock fallback) |
| `frontend/src/api/mockWrapped.ts` | Create | Mock handler returning placeholder frame data |
| `frontend/src/types/build.ts` | Modify | Add `profile_name?: string` to the TypeScript `Build` / `BuildSummary` types to mirror backend model changes. |
| `frontend/src/App.tsx` | Modify | Add route: `/save` |

### Frontend: Data Flow

No new Zustand store needed. The save/wrapped screen reads from `buildStore` (Build object) and `profileStore` (profile name, emoji).

1. On mount: auto-save via `POST /build/{build_id}/save` (already exists).
2. Show save confirmation (1.5s).
3. Trigger frame rendering: `POST /build/{build_id}/wrapped/render`.
4. Fetch frame URLs: `GET /build/{build_id}/wrapped`.
5. Display story viewer with frame images.

### API Client

```typescript
// api/wrapped.ts

import { apiPost, apiGet } from "@/api/client";
import { mockRenderWrapped, mockGetWrapped } from "@/api/mockWrapped";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

interface WrappedFrame {
  index: number;
  url: string;
}

interface WrappedResponse {
  frames: WrappedFrame[];
}

export async function renderWrapped(buildId: string): Promise<void> {
  if (USE_MOCK) { mockRenderWrapped(); return; }
  await apiPost(`/build/${buildId}/wrapped/render`);
}

export async function getWrapped(buildId: string): Promise<WrappedResponse> {
  if (USE_MOCK) return mockGetWrapped();
  return apiGet<WrappedResponse>(`/build/${buildId}/wrapped`);
}

export function getFrameUrl(buildId: string, frameIndex: number): string {
  const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  return `${base}/build/${buildId}/wrapped/${frameIndex}`;
}
```

### Routing Addition

```
/save  → SaveWrappedScreen     (Screen 9)
```

Navigation guard: `/save` requires a `build` object in `buildStore`. If missing, redirect to `/reveal`.

### Mock Fallback

When `VITE_USE_MOCK_API=true`, the mock returns 6 placeholder frame objects. The actual PNG images won't be available in mock mode — the viewer shows colored placeholder rectangles with frame labels (frame 1: "Identity", frame 2: "Pentagon", etc.) using the Brightpath color scheme. This lets frontend development proceed without Playwright installed.

### Service Changes

- **New dependency:** `playwright` in `backend/pyproject.toml`. Requires `playwright install chromium`.
- **New directory:** `backend/templates/wrapped/` for HTML frame templates.
- **DuckDB rewrite:** `backend/app/services/builds.py` replaces flat JSON file persistence with DuckDB tables (`builds` + `wrapped_frames`).
- **Router update:** `backend/app/routers/wrapped.py` replaces the 501 stub with real endpoints.
- **Router update:** `backend/app/routers/builds.py` updated to pass `profile_name` to save operations.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `App.test.tsx` | Routing tests | Medium | New `/save` route |

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `screens/SaveWrappedScreen.test.tsx` | shows save confirmation | Save confirmation renders with build summary |
| P0 | `screens/SaveWrappedScreen.test.tsx` | transitions to wrapped viewer | After delay, story viewer appears |
| P0 | `components/wrapped/WrappedViewer.test.tsx` | renders 6 frames | All 6 frame images (or placeholders) present |
| P0 | `components/wrapped/WrappedViewer.test.tsx` | tap advances frame | Tap right zone → frame index increments |
| P0 | `components/wrapped/WrappedViewer.test.tsx` | tap back goes to previous | Tap left zone → frame index decrements |
| P1 | `components/wrapped/FrameProgressDots.test.tsx` | shows correct active dot | Current frame dot highlighted |
| P1 | `components/wrapped/WrappedViewer.test.tsx` | download button triggers fetch | Download click → frame URL fetched |
| P1 | `screens/SaveWrappedScreen.test.tsx` | handles render API error | Error → fallback message + retry |
| P2 | `api/wrapped.test.ts` | mock returns valid shape | Mock handler returns WrappedResponse |
| P2 | Backend: `test_wrapped_renderer.py` | renders frame to PNG | Template + build data → valid PNG file |
| P0 | Backend: `test_builds_duckdb.py` | save and load build | Save build → load by ID → matches original |
| P0 | Backend: `test_builds_duckdb.py` | list builds by profile | Save 3 builds → list by profile_name → returns all 3 |
| P1 | Backend: `test_builds_duckdb.py` | compare builds | Save 2 builds → compare → stat rows correct |
| P1 | Backend: `test_builds_duckdb.py` | upsert overwrites | Save build twice with same ID → only 1 row |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED (after spec patches 2026-04-15)
**Reviewed:** 2026-04-15
**Resolved:** 2026-04-15

#### Resolution Log (2026-04-15)

Human (Jeff) directed spec author (Claude Code) to apply patches for C1–C4, C7, C8 and explicitly rejected C5. Patches applied:

- **C1 — APPLIED.** §4 now specifies `profile_name: str = ""` on both `Build` and `BuildSummary`, and `draws: int = 0` added to `BuildSummary` to match the DuckDB `builds` table schema.
- **C2 — APPLIED.** §4 `save_build` signature is now `save_build(build: Build)`. Reads `build.profile_name` internally; router sets it before calling.
- **C3 — APPLIED.** §4 File Changes table now lists `backend/app/services/profile.py` with an explicit directive to rewrite `_load_existing_profiles()` and `_get_builds_for_profile()` to query DuckDB. Also added `backend/app/routers/builds.py` (to plumb `profile_name` from `BuildRequest` onto `Build`) and noted `state.py` requires no change because the `FileNotFoundError` contract is preserved.
- **C4 — APPLIED.** §4 `load_build` docstring now explicitly mandates `FileNotFoundError` on miss and requires wrapping `duckdb.CatalogException`. `state.py:32` is unchanged.
- **C5 — REJECTED by human.** Playwright stays a hard, required dependency. §2 Constraints updated to make this explicit ("no graceful degradation — if Playwright is unavailable, the render endpoint returns 500 and the feature is considered broken"). Hackathon trade-off accepted; schools that can't install Chromium lose the Wrapped feature.
- **C7 — APPLIED.** §4 API Contract now defines `WrappedFrameInfo`, `WrappedResponse`, and `RenderResponse` Pydantic models and binds them via `response_model`. The PNG-serving endpoint correctly returns a raw `Response(media_type="image/png")` with `Content-Disposition` attachment headers.
- **C8 — APPLIED.** All "Puppeteer" references outside this §5 review section have been normalized to "Playwright". §5 text retained as-is for historical record.

With all required conditions resolved and C5 explicitly waived, the verdict is flipped to APPROVED. Proceed to Step 2 (Design Vision).

---

#### Original Review

#### System Context

Screen 9 sits at the end of the core flow (after branches/Screen 8) and touches three layers: (1) backend persistence (replacing flat JSON with DuckDB for builds), (2) a new backend rendering pipeline (Playwright + HTML templates to PNG), and (3) a frontend story viewer consuming those PNGs. This feature does NOT touch the Brightsmith pipeline, Gold zone, MCP tools, or Gemma roles. It is purely application-layer state management + a rendering side-channel. That boundary is clean.

#### Data Flow Analysis

**Save flow:** Frontend `buildStore.build` --> `POST /build/{id}/save` --> `state.py` in-memory lookup --> `builds.save_build()` (currently flat JSON, proposed DuckDB) --> persisted row in `backend/data/futureproof.duckdb` `builds` table.

**Wrapped render flow:** Frontend `POST /build/{id}/wrapped/render` --> backend loads Build from DuckDB --> injects data into 6 Jinja2/string HTML templates --> Playwright screenshots each at 1080x1920 --> PNGs stored as BLOBs in `wrapped_frames` table --> Frontend `GET /build/{id}/wrapped` returns frame metadata --> Frontend `GET /build/{id}/wrapped/{index}` serves individual PNGs as `image/png`.

**Profile name flow:** `BuildRequest.profile_name` (already exists in `api.py` line 42) --> `create_build` router --> currently DROPPED -- `build_from_parts()` does not accept `profile_name`, and `Build` model has no `profile_name` field. The spec proposes adding it to `Build`. The profile service's `_load_existing_profiles()` and `_get_builds_for_profile()` currently scan JSON files for `profile_name` -- these must be rewritten to query DuckDB.

**Pipeline DB vs App DB separation:** Pipeline DuckDB lives at `data/futureproof.duckdb` (Gold zone, read-only from backend). App DuckDB proposed at `backend/data/futureproof.duckdb`. Different directories, different files, different purposes. This separation is correct and important -- app state must never pollute pipeline products.

#### Contract Review

**Pydantic models:**
- `Build` model (line 174 of `career.py`) needs `profile_name: str` added. This is a schema change to a core model that crosses every API boundary. The spec acknowledges this but does not specify: is `profile_name` required or optional? Given that builds created before this change have no `profile_name`, it must be `profile_name: str = ""` (optional with default) for backward compatibility.
- `BuildSummary` (line 194) also needs `profile_name` for the list/compare views.
- The spec's DuckDB `builds` table schema includes `draws` but the current `BuildSummary` does not have `draws`. Either add it to `BuildSummary` or drop it from the table.

**API contracts:**
- `GET /build/{id}/wrapped` returns `{ frames: [{ index, url }] }` -- well-typed, clean.
- `GET /build/{id}/wrapped/{frame_index}` returns raw PNG binary -- correct for image serving. Must set `Content-Type: image/png` and use `StreamingResponse` or `FileResponse`.
- `POST /build/{id}/wrapped/render` returns `{ status, frame_count }` -- fine as a trigger. No Pydantic response model specified -- should define one.

**Function signature changes:** The spec says `save_build(build, profile_name)` takes two args. Currently `save_build(build)` takes one. If `profile_name` is added to the `Build` model itself, the function should stay as `save_build(build)` and read `build.profile_name`. Having it as a separate parameter creates confusion about where the canonical `profile_name` lives.

#### Findings

##### Sound

- **App DB / Pipeline DB separation** is exactly right. `backend/data/futureproof.duckdb` for app state, `data/futureproof.duckdb` for Gold zone products. No cross-contamination risk.
- **DuckDB over flat JSON files** is the correct call. The current `list_builds()` globs the filesystem and deserializes every JSON file. The current `_get_builds_for_profile()` in `profile.py` does the same. DuckDB gives indexed queries, atomic writes, and a single file. Already a dependency. No new infrastructure.
- **Denormalized stat columns** in the `builds` table for fast compare/list queries without JSON parsing -- good design for the access patterns described.
- **Playwright over pyppeteer** is correct. Playwright is actively maintained, handles font embedding reliably, and has built-in browser management.
- **No new Zustand store** is correct. `buildStore` has the Build, `profileStore` has the profile name and emoji. The save/wrapped screen reads both. No new state to manage.
- **HTML templates as standalone files** (not React components) for Playwright rendering is the right separation. No framework dependency in the render path.
- **Mock fallback** for frontend development without Playwright installed keeps the two workstreams independent.
- **Existing route prefix structure** is respected: wrapped router already mounts at `prefix="/build"` in `main.py` (line 46), so `/{build_id}/wrapped` paths are consistent.

##### Concerns

- **C1 -- `profile_name` on `Build` model must be optional with default.** The spec says Build "gains a `profile_name` field" but does not specify the default. Existing serialized builds (in the current flat JSON files, in test fixtures, in the frontend's `Build` type) have no `profile_name`. It must be `profile_name: str = ""` to avoid breaking deserialization of existing builds. **Impact:** Every `Build.model_validate()` call on existing data will throw `ValidationError` if the field is required. **Recommendation:** Spec should mandate `profile_name: str = ""` on `Build` and `profile_name: str = ""` on `BuildSummary`.

- **C2 -- `save_build` signature inconsistency.** The spec defines `save_build(build: Build, profile_name: str)` but if `profile_name` is on the `Build` model, this is redundant and creates ambiguity (which source wins?). **Impact:** Confusion during implementation, potential for the two values to diverge. **Recommendation:** Keep signature as `save_build(build: Build)` and read `build.profile_name` inside the function. The router's `create_build` should set `profile_name` on the Build before passing it in.

- **C3 -- `profile.py` depends on flat JSON files.** Two functions in `profile.py` scan `backend/data/builds/*.json`: `_load_existing_profiles()` (line 151) and `_get_builds_for_profile()` (line 179). The spec does not mention updating these. Once builds move to DuckDB, these functions will return empty results. **Impact:** Profile lookup will stop returning existing builds. The startup hook `_load_existing_profiles()` will find no profiles. **Recommendation:** Spec should explicitly list `profile.py` as a file requiring updates -- both functions must query the `builds` DuckDB table instead of globbing JSON files.

- **C4 -- `state.py` disk fallback needs updating.** `state.py` line 32 imports `load_build` from `builds.py` and catches `FileNotFoundError`. After the DuckDB rewrite, `load_build` may raise `duckdb.CatalogException` or return None instead of raising `FileNotFoundError`. **Impact:** Cache misses will raise unhandled exceptions instead of gracefully falling back. **Recommendation:** Either preserve the `FileNotFoundError` contract in the new `load_build` (recommended -- raise `FileNotFoundError` when row not found, even with DuckDB backend) or update `state.py` to catch the appropriate exception.

- **C5 -- Playwright as a required backend dependency.** Playwright pulls in Chromium (~150-280MB). For a hackathon project targeting zero-cost school deployment on Ollama hardware, this is a meaningful addition to the deployment footprint. The spec does not address graceful degradation -- what happens if Playwright is not installed? The render endpoint should return a clear error, and the frontend should handle it (show "rendering unavailable" rather than crashing). **Impact:** Schools that cannot install Chromium (restricted environments) lose the entire Wrapped feature. **Recommendation:** (a) Make `playwright` an optional dependency (`pip install futureproof-backend[wrapped]`), (b) the render endpoint should check for Playwright availability at call time and return 503 with a clear message if missing, (c) the frontend already has mock placeholders -- use those as the degraded experience.

- **C6 -- BLOB storage for PNGs in DuckDB.** Storing six 1080x1920 PNGs (~200-500KB each, so 1-3MB per build) as BLOBs in DuckDB is functional but atypical. For a hackathon with low build volume, this is fine. At scale (thousands of builds), the DuckDB file grows by gigabytes. The spec mentions "simplifies cleanup (delete build -> delete frames via FK)" but DuckDB does not enforce foreign keys by default. **Impact:** Low risk at hackathon scale. At production scale (unlikely before deadline), the database file balloons. **Recommendation:** Acceptable for the hackathon. Document that this is a known scaling limitation. If FK-based cascading delete is desired, it must be implemented in application code, not relied upon from DuckDB.

- **C7 -- Missing Pydantic response models for wrapped endpoints.** The spec defines the JSON shapes inline (`{ frames: [...] }`, `{ status, frame_count }`) but does not define Pydantic models for them. Every other router in this project uses typed response models. **Impact:** No type safety on the response boundary, inconsistent with existing patterns. **Recommendation:** Define `WrappedFrameInfo`, `WrappedResponse`, and `RenderResponse` Pydantic models in `career.py` or a new `wrapped.py` models file.

- **C8 -- The spec references both "Puppeteer" and "Playwright" inconsistently.** Section headers say "Puppeteer Rendering Service," decision D1 says "Server-side Puppeteer rendering," but the implementation notes say "use `playwright` not `pyppeteer`." The final notes (section 11) confirm Playwright. **Impact:** Implementer confusion. **Recommendation:** Search-and-replace all "Puppeteer" references in the spec to "Playwright" for consistency.

##### Blockers

None. The architecture is sound. The concerns above are all addressable without fundamental redesign.

#### Verdict (original, superseded by Resolution Log above)
- [x] CHANGES REQUESTED → **now APPROVED** (see Resolution Log at top of §5)

#### Conditions

1. **C1 (Required):** Specify `profile_name: str = ""` as the field definition on both `Build` and `BuildSummary` models, ensuring backward compatibility with existing serialized builds.
2. **C2 (Required):** Change `save_build` signature to `save_build(build: Build)` (no separate `profile_name` argument). Read from `build.profile_name`.
3. **C3 (Required):** Add `backend/app/services/profile.py` to the file changes table. Both `_load_existing_profiles()` and `_get_builds_for_profile()` must be updated to query DuckDB instead of scanning JSON files.
4. **C4 (Required):** Specify the exception contract for the new `load_build()` -- either preserve `FileNotFoundError` or update `state.py` to match.
5. **C7 (Required):** Define Pydantic response models for the three wrapped endpoints, consistent with the pattern used by all other routers.
6. **C5 (Recommended):** Make Playwright an optional dependency and add graceful degradation when it is unavailable.
7. **C8 (Recommended):** Normalize all "Puppeteer" references to "Playwright" throughout the spec.

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

- **DESIGN.md is the source of truth** for all visual decisions. The Wrapped frames use Brightpath tokens but at 1080×1920 scale — sizes should be proportionally larger than the web viewport versions.
- **Frame templates are standalone HTML** — no React, no JS framework. They must render correctly in headless Chromium via Playwright. Embed all CSS inline or in a `<style>` block. No external stylesheet dependencies.
- **Fonts must be available to Playwright.** Either embed as base64 `@font-face` in each template, or use Google Fonts `@import` (requires network in headless mode). Base64 embedding is more reliable for local/offline deployment.
- **The story viewer mimics Instagram Stories UX.** Tap right = next, tap left = back, progress dots at top, no visible buttons in the frame area. The download/done buttons live below the frame on desktop or in a fixed bottom bar on mobile.
- **The social loop depends on Frame 1 (Identity).** "I'm Steady Bold Turtle 🐢" triggers "what name did you get?" The profile name must be the visual centerpiece of this frame.
- **Frame 4 (Comparative Insight) requires a computed insight.** If percentile data isn't available, fall back to "Your strongest stat" — don't show a percentile claim without data to back it.
- **Frame 5 (Risk Highlight) adapts.** If the student won all fights, show a "CLEAN SWEEP" celebration instead of a risk highlight.
- **Playwright > pyppeteer.** Playwright is better maintained, has built-in browser install, and handles fonts more reliably. Use `playwright` not `pyppeteer`.
- **Mock mode shows placeholder frames.** The frontend can be fully developed and tested without Playwright installed — mock frames are colored rectangles with frame labels.
- **DuckDB replaces flat JSON files for build persistence.** The spike's `builds.py` used filesystem glob patterns and JSON read/write. This spec rewrites it to use DuckDB with a `builds` table (denormalized stat columns for fast queries) and a `wrapped_frames` table (PNG BLOBs). The database file lives at `backend/data/futureproof.duckdb`. All existing `save_build`, `load_build`, `list_builds`, `compare_builds` function signatures are preserved — only the implementation changes. The `Build` model gains a `profile_name` field (noted as missing by the F3 architect review).

---
