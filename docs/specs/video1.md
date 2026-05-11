# Spec: video-kinetic-typography-intro

**Status:** Ready for Implementation
**Type:** Video asset generation (kinetic typography HTML)
**Owner:** Claude Code
**Created:** 2026-05-08

---

## Problem Statement

Build kinetic typography HTML clips for the FutureProof hackathon video intro (Scenes 0–1). Each HTML file plays automatically on load, runs to completion in a fixed time, and is screen-recorded via QuickTime to produce a video clip that drops into iMovie alongside screenshot smash cuts and voiceover.

The intro is ~1:42 of runtime split across 8 typography beats, interspersed with 3 screenshot smash cuts handled separately in iMovie. This spec covers only the typography beats — not the smash cuts.

## Why This Matters

- Video is 30% of judging weight
- Kinetic typography is the visual backbone of the intro
- Visual consistency with the FutureProof app (same design tokens) reinforces product credibility
- HTML approach gives precise, reproducible timing that Keynote can't match

## Out of Scope

- Smash cut sequences (handled in iMovie with screenshot images)
- Voiceover recording (separate iMovie track)
- Music (separate iMovie track)
- Scene 2 onward (separate spec post-intro lock)

---

## Deliverables

8 standalone HTML files, one per typography beat. Each file:
- Runs full-screen at 1920×1080
- Auto-plays on page load (no user interaction)
- Black background (`#1B1D30` — bg-void token)
- Uses Brightpath design tokens for colors and typography
- Holds the final frame indefinitely after animations complete (so QuickTime recording captures cleanly)
- Includes a 2-second pre-roll black frame so screen recording start doesn't clip the first text appearance

## File Structure

Create directory: `docs/video/kinetic/`

Files:
docs/video/kinetic/
├── _shared/
│   ├── tokens.css          # Copy of frontend/src/styles/tokens.css
│   ├── fonts/              # Local copies of Fredoka, Nunito, Space Mono
│   └── base.css            # Shared base styles (background, fonts, typography scale)
├── beat-0b-age-of-ai.html
├── beat-0c-anxiety-level.html
├── beat-0f-not-easy-before.html
├── beat-0h-marketing-strikethrough.html
├── beat-0j-where-does-that-leave.html
├── beat-1abcd-amazing-but-teenager.html  # Combined beat (4 builds in one file)
├── beat-1ef-but-heres-the-thing.html
├── beat-1gh-hard-to-find.html
└── README.md               # Recording instructions for Jeff

## Design System Constraints

**MUST use Brightpath tokens.** Read `frontend/src/styles/tokens.css` and `DESIGN.md` first. Use CSS custom properties throughout — zero raw hex codes.

**Colors (use existing tokens):**
- Background: `var(--bg-void)` = `#1B1D30`
- Body text: `var(--text-primary)` = `#F5F0E8`
- Emphasis (bold/highlighted words): `var(--accent-thrive)` for hopeful, `var(--accent-alert)` for heavy hits
- Strikethrough word: `var(--accent-alert)`
- Replacement word: `var(--text-primary)`
- Stat hits (the big number reveals): `var(--accent-caution)` (gold/yellow)

**Typography (use existing tokens):**
- Display weight (large emphasis): Fredoka, 800 weight
- Body weight (running text): Nunito, 400-700
- Stat hits (big numbers): Fredoka, 900, monospace alignment via Space Mono fallback for numerals
- Base scale: 60-72pt for body text, 120-180pt for emphasis, 200pt+ for stat hits
- Line height: 1.2 for display, 1.4 for body

**Layout:**
- Center-aligned vertically and horizontally
- Max-width 1200px on text container
- Generous letter-spacing on small caps if used (`0.05em`)
- No drop shadows, no borders, no decorative elements — text on black, period

## Animation Timing Source of Truth

Each beat has exact timing pulled from the script. **Do not interpret or "improve" timing — match these numbers precisely.**

| File | Beat | Timing | Hold final frame |
|---|---|---|---|
| `beat-0b-age-of-ai.html` | 0b | 0:00–0:06 (text appears 0:00, holds through 0:06) | Yes, until ~0:08 in recording |
| `beat-0c-anxiety-level.html` | 0c | 0:00–0:06 (then hold for the silence drop in iMovie) | Yes, indefinitely |
| `beat-0f-not-easy-before.html` | 0f | 0:00–0:06 | Yes |
| `beat-0h-marketing-strikethrough.html` | 0h | 0:00–0:08 (most complex animation) | Yes |
| `beat-0j-where-does-that-leave.html` | 0j | 0:00–0:06 | Yes |
| `beat-1abcd-amazing-but-teenager.html` | 1a–1d | 0:00–0:22 (4 sequential text builds) | Yes |
| `beat-1ef-but-heres-the-thing.html` | 1e–1f | 0:00–0:08 | Yes |
| `beat-1gh-hard-to-find.html` | 1g–1h | 0:00–0:12 | Yes |

## Beat-by-Beat Specifications

### `beat-0b-age-of-ai.html`

**Duration:** 6 seconds
**VO:** "In 2026, Gemma, Gemini, Claude and Opus ushered us into the Age of AI."

**Animation:**
- 0:00–0:01 — "**In 2026,**" fades in (bold, accent-caution color)
- 0:01–0:02 — "Gemma, Gemini, Claude and Opus" fades in below
- 0:02–0:03 — "ushered us into" fades in below
- 0:03–0:04 — "**the Age of AI.**" fades in below (bold, accent-alert)
- 0:04–0:06 — Hold all four lines on screen
- 0:06+ — Hold indefinitely

**Layout:** Stacked vertically, centered. Each line on its own row.

---

### `beat-0c-anxiety-level.html`

**Duration:** 6 seconds (then iMovie holds the final frame for the 2-second silence drop)
**VO:** "As the father of 3 teenagers, this has not helped my anxiety level."

**Animation:**
- 0:00–0:01 — "As the father of " fades in
- 0:01–0:02 — "**3 teenagers**," appears with slight scale-up (accent-alert color)
- 0:02–0:03 — "this has not helped my" fades in below
- 0:03–0:04 — "**anxiety level.**" fades in (large, accent-alert, slightly larger than other emphasis)
- 0:04–0:06 — Hold; "anxiety level" has a subtle pulse animation (scale 1.0 → 1.02 → 1.0 over 1.5s, infinite)
- 0:06+ — Continue pulsing indefinitely (so the silence-drop in iMovie has visual life)

---

### `beat-0f-not-easy-before.html`

**Duration:** 6 seconds
**VO:** "And it's not like it was easy before."

**Animation:**
- 0:00–0:02 — "And it's not like" fades in (slow, deliberate)
- 0:02–0:04 — "**it was easy before.**" fades in below (bold, slightly larger)
- 0:04–0:06 — Hold
- 0:06+ — Hold indefinitely

---

### `beat-0h-marketing-strikethrough.html`

**Duration:** 8 seconds (most complex beat)
**VO:** "And the colleges? They're preying on the innocence of kids... marketing to the innocence of kids."

**Animation sequence:**
- 0:00–0:01 — "And the colleges?" fades in
- 0:01–0:02 — "They're" fades in below
- 0:02–0:03 — "**preying on**" types in next to "They're" (accent-alert, bold) — use a typewriter effect or sharp fade
- 0:03–0:04 — "the innocence of kids." fades in on next line
- 0:04–0:04.5 — Pause, full sentence visible: "They're **preying on** the innocence of kids."
- 0:04.5–0:05 — Strikethrough line draws across "preying on" left-to-right (animation: 0.4s, accent-alert color, 3px height)
- 0:05–0:06 — "**marketing to**" types in *above* "preying on" (text-primary color, bold) — typewriter or fade
- 0:06–0:08 — Hold final state: "They're [marketing to / ~~preying on~~] the innocence of kids." with both phrases visible, strikethrough struck, replacement above
- 0:08+ — Hold indefinitely

**Implementation note:** This is the signature beat. Spend extra effort on the strikethrough animation feeling crisp. The viewer needs ~1 second to read "preying on the innocence of kids" before the strikethrough hits, or the punchline doesn't land.

---

### `beat-0j-where-does-that-leave.html`

**Duration:** 6 seconds
**VO:** None — silent beat. Pure text.

**Animation:**
- 0:00–0:02 — "So where does that" fades in slowly
- 0:02–0:04 — "leave a kid?" fades in below
- 0:04–0:06 — Hold
- 0:06+ — Hold indefinitely

**Tone:** Quieter than other beats. Slightly smaller text. This is a breath, not a punch.

---

### `beat-1abcd-amazing-but-teenager.html`

**Duration:** 22 seconds (4 sequential text states in one file)
**VO:** "AI is amazing. But it's made it difficult to plan for what the next 4 months will look like... let alone trying to plan the next 4 years... as a teenager."

**Animation sequence:**

**State 1a (0:00–0:04):**
- 0:00–0:02 — "AI is **amazing.**" fades in (centered, large)
- 0:02–0:04 — Hold

**State 1b (0:04–0:10):**
- 0:04–0:05 — Frame clears, "But it's made it difficult to plan" fades in
- 0:05–0:06 — "for what the next" fades in below
- 0:06–0:08 — "**4 months** will look like..." fades in (bold, accent-caution on "4 months")
- 0:08–0:10 — Hold

**State 1c (0:10–0:16):**
- 0:10–0:11 — "...let alone trying to plan" fades in (replacing or below previous, designer's call)
- 0:11–0:13 — "the next **4 years**..." fades in (bold, accent-alert on "4 years" — escalating intensity from 4 months)
- 0:13–0:16 — Hold

**State 1d (0:16–0:22) — THE LANDING:**
- 0:16–0:17 — Frame clears completely
- 0:17–0:19 — "...as a **teenager.**" fades in slowly, large, centered, alone (accent-alert, displays at maximum size used in entire video)
- 0:19–0:22 — Hold (this is the most important word in the video — let it breathe)
- 0:22+ — Hold indefinitely

**Implementation note:** The "teenager" reveal must be the visual climax of the intro. Make it 1.5-2x larger than other emphasis. Center it. Surround it with negative space.

---

### `beat-1ef-but-heres-the-thing.html`

**Duration:** 8 seconds
**VO:** "But here's the thing. There is data that can help kids make better choices."

**Animation:**
- 0:00–0:02 — "But here's the thing." fades in (medium size, calmer than previous beats)
- 0:02–0:03 — Hold
- 0:03–0:04 — Frame clears
- 0:04–0:06 — "There **is** data that can help kids" fades in (emphasis on "is" — accent-thrive color)
- 0:06–0:08 — "make **better choices.**" fades in below (emphasis on "better choices" — accent-thrive)
- 0:08+ — Hold indefinitely

**Tone:** This is the emotional turn. Music in iMovie shifts from drone to investigation. The text should feel calmer, more confident than everything before.

---

### `beat-1gh-hard-to-find.html`

**Duration:** 12 seconds
**VO:** "But it's hard to find. Hard to combine. And almost impossible to interpret. Which is why nobody's fixed this for kids."

**Animation:**

**State 1g (0:00–0:08):**
- 0:00–0:02 — "Hard to **find.**" fades in
- 0:02–0:04 — "Hard to **combine.**" fades in below
- 0:04–0:06 — "Almost impossible to **interpret.**" fades in below
- 0:06–0:08 — Hold all three lines (accent-alert on the bolded words, building intensity)

**State 1h (0:08–0:12):**
- 0:08–0:09 — Frame clears
- 0:09–0:11 — "Which is why nobody's" fades in
- 0:11–0:12 — "**fixed this for kids.**" fades in below (bold, large, accent-alert)
- 0:12+ — Hold indefinitely (this is the last frame before "Until now" pivot to Scene 2 — needs to land hard)

---

## Technical Implementation

### Base HTML Template

Each file should follow this structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>FutureProof Video — [Beat Name]</title>
  <link rel="stylesheet" href="_shared/tokens.css">
  <link rel="stylesheet" href="_shared/base.css">
  <style>
    /* Beat-specific animations */
  </style>
</head>
<body>
  <div class="stage">
    <!-- Pre-roll: 2 seconds of pure black before any animation -->
    <div class="content">
      <!-- Animated text elements -->
    </div>
  </div>
</body>
</html>
```

### Animation Approach

Use **CSS animations with `animation-delay`**, not JavaScript `setTimeout` chains. CSS animations are deterministic and frame-perfect. Example:

```css
.line-1 {
  opacity: 0;
  animation: fadeIn 0.6s ease-out 2.0s forwards;
}
.line-2 {
  opacity: 0;
  animation: fadeIn 0.6s ease-out 3.0s forwards;
}
@keyframes fadeIn {
  to { opacity: 1; }
}
```

The 2-second pre-roll is achieved by setting all animation delays to start at 2s + the beat-relative time. So Beat 0b's first text appears at `animation-delay: 2.0s`, not `0.0s`.

This way QuickTime recording can be sloppy on the start cue — the first 2 seconds are just black, giving you margin.

### Strikethrough Animation Detail

The signature animation in `beat-0h`. Implementation:

```css
.preying {
  position: relative;
  color: var(--accent-alert);
  display: inline-block;
}
.preying::after {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 0;
  height: 3px;
  background: var(--accent-alert);
  transform: translateY(-50%);
  animation: strike 0.4s ease-out 4.5s forwards;
}
@keyframes strike {
  to { width: 100%; }
}
```

Then `.marketing-to` types in via a separate animation that triggers at 5.0s (after the strike completes).

For the typewriter effect on "marketing to", use a width-based reveal with `overflow: hidden` and a steps() timing function:

```css
.marketing-to {
  display: inline-block;
  width: 0;
  overflow: hidden;
  white-space: nowrap;
  animation: typewriter 0.5s steps(12) 5.0s forwards;
}
@keyframes typewriter {
  to { width: 100%; }
}
```

### Fonts

Embed Fredoka, Nunito, and Space Mono as local files in `_shared/fonts/`. Pull from Google Fonts:
- Fredoka: weights 400, 600, 700, 800
- Nunito: weights 400, 600, 700, 900
- Space Mono: weight 400, 700

Reference via `@font-face` declarations in `_shared/base.css`. Do not rely on Google Fonts CDN — local files ensure the fonts load instantly and there's no flash of unstyled text during recording.

### Recording Notes for Jeff

Generate `docs/video/kinetic/README.md` with these instructions:

```markdown
# Recording the Kinetic Typography Clips

## Setup
1. Open Chrome
2. Navigate to the HTML file (e.g. `file:///.../beat-0b-age-of-ai.html`)
3. Press `F11` (Windows) or `Ctrl+Cmd+F` (Mac) for full-screen
4. Open QuickTime Player → File → New Screen Recording
5. Drag selection to Chrome window only (or full screen)
6. Set audio to "None" (we record audio separately)

## Recording
1. Start recording
2. Press Cmd+R in Chrome to reload the page (this restarts the animation)
3. Wait for animation to complete + 2 extra seconds of held final frame
4. Stop recording

## Post-Recording
1. QuickTime saves to ~/Movies/
2. Trim the start of the clip to remove the page-load flash (use QuickTime's Edit → Trim)
3. Drop into iMovie at the appropriate timeline position
4. The 2-second pre-roll black gives you margin to align with the start of the beat
```

---

## Acceptance Criteria

- [ ] All 8 HTML files created in `docs/video/kinetic/`
- [ ] All files use Brightpath design tokens (zero raw hex codes)
- [ ] Each file auto-plays on page load with no user interaction required
- [ ] Each file holds final frame indefinitely after animations complete
- [ ] 2-second black pre-roll on every file
- [ ] Strikethrough animation in `beat-0h` reads cleanly: viewer sees "preying on" for ~1s, then strike, then "marketing to" appears
- [ ] "as a teenager" in `beat-1abcd` is visually larger than any other text in the entire intro
- [ ] All fonts load locally (no CDN dependency)
- [ ] Tested in Chrome at 1920×1080 viewport
- [ ] README.md with recording instructions included

## Test Plan

After Claude Code completes:
1. Open each HTML file in Chrome
2. Verify timing matches script — use a stopwatch
3. Verify visual hierarchy — emphasis words clearly more prominent than body
4. Verify strikethrough animation reads cleanly
5. Verify "teenager" lands as the climax
6. Screen-record one beat with QuickTime, drop into iMovie, confirm dimensions match project

## File Reference

- Brightpath tokens: `frontend/src/styles/tokens.css`
- Design system documentation: `DESIGN.md`
- Video script: `docs/video/futureproof-video-script-v1.md` (will be updated to v2 with locked intro)
- Existing HTML mockups for reference: `docs/mockups/brightpath-design-system-v2.html`

## Out-of-Scope Beats

These are handled in iMovie, not HTML — do NOT generate files for these:
- Beat 0a (cold open black — handled by iMovie black frame)
- Beat 0d (silence drop — handled by iMovie audio cut)
- Beat 0e (Smash Cut #1 — screenshot images in iMovie)
- Beat 0g (Smash Cut #2 — screenshot images + small typography hits, may need separate spec)
- Beat 0i (Smash Cut #3 — screenshot images + small typography hits, may need separate spec)

The typography hits within Smash Cuts 0g and 0i (`$1.8 TRILLION`, `6,000 PROGRAMS`, `95%`, `3-12x`) will be specced separately as static PNG generators if iMovie titles aren't sufficient.
