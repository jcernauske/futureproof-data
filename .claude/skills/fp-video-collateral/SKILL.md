---
name: fp-video-collateral
description: Build self-contained 1920×1080 HTML "scene" files for the FutureProof demo video. Renders in Chrome at fixed dimensions, autoplays entrance + idle animations, holds final frame indefinitely so the user can record cleanly. This skill creates the screens only — it does NOT record, narrate, or edit. Use for new video beats, title cards, lower-thirds, end cards, callouts, transition slides, or any other on-screen graphic destined for the hackathon submission. Triggers on "video collateral", "video scene", "video screen", "title card", "end card", "lower third", "make a screen for the video", "build a beat for", "render a slide for", "make a video frame for", "scene for beat", "kinetic clip for".
---

# fp-video-collateral

Build a single self-contained 1920×1080 HTML file that renders cleanly in Chrome's app mode and screen-records frame-perfect via `scripts/record_title_card.py`. Every output of this skill lives in `docs/video/kinetic/` and follows the conventions established by `brand-reveal-v2.html` (Brightpath register) and `scene-1-planning.html` (intro/editorial register).

**Scope:** screen creation only. Recording, narration, video assembly, music, and final iMovie/DaVinci edit are the user's job — never write recording instructions, never invoke the recorder script unprompted, never give "how to capture this" tips unless the user asks.

---

## Step 1 — Read the script and find the beat

Before you write a line of HTML, open the canonical script:

- `docs/video/futureproof-video-script-v1.md` — the 3:00 working draft, beat boundaries and voiceover lines
- `docs/specs/video1.md` — typography-beat spec for Scenes 0–1 (intro register)
- `docs/specs/video-ai-wave.md` — AI Wave smash-cut spec
- `docs/video/kinetic/README.md` — file index, register notes, and recording setup the user already has

Identify which beat the user is asking about, what voiceover sits on top of it, what visually precedes and follows it, and **which visual register** the beat belongs to (Step 2). If the user's ask doesn't map to an existing beat, ask them which beat ID it should be filed under or which existing scene it should sit between.

---

## Step 2 — Pick the visual register

The video has two deliberately distinct registers. Pick the wrong one and the cut between scenes will break.

| | **Intro register** | **Brightpath register** |
|---|---|---|
| **Beats** | Scene 0, Scene 1 (0:00–0:38) | Scene 2 onward (0:38+), brand reveals, end cards |
| **Mood** | Cold editorial — Atlantic / NYT data cards / Adam Curtis intertitles | Warm cinematic — first color the audience sees after the page-turn |
| **Background** | `#0F1117` flat | Canonical Brightpath gradient (Step 5) |
| **Typeface** | `Inter` 400/500/700/900 | `Fredoka` (display) + `Nunito` (body) |
| **Body color** | `#E5E7EB` cold off-white | `--color-text-primary` `#F5F0E8` warm off-white |
| **Accent** | `#DC2626` cold red, used **sparingly** (only at the script's emotional landings) | Full Brightpath palette; pentagon stat colors for foreshadowing |
| **Reference file** | `docs/video/kinetic/scene-1-planning.html` | `docs/video/kinetic/brand-reveal-v2.html` |
| **Shared CSS** | `<link rel="stylesheet" href="_shared/tokens.css"> <link rel="stylesheet" href="_shared/base.css">` | **Inline everything** — the Brightpath scenes are fully self-contained so they record portably |

The temperature flip between registers (cold editorial → warm Brightpath) is itself a narrative beat per the README. If you find yourself wanting to "harmonize" the registers, stop — the dissonance is the design.

If the user's ask is ambiguous (e.g., "make me a screen showing the four data sources"), pick by the beat number from Step 1: anything in Scenes 0–1 is intro register, anything from Scene 2 onward is Brightpath. Confirm before writing if you're guessing.

---

## Step 3 — Pick a file name and location

All scene files live in `docs/video/kinetic/`. Naming conventions:

- **Intro beats:** `beat-<id>-<slug>.html` — e.g. `beat-0c-anxiety-level.html`. Slug describes the line, not the design.
- **Multi-beat scenes:** `scene-<n>-<slug>.html` — e.g. `scene-1-planning.html`.
- **Brightpath one-offs:** `<purpose>-<vN>.html` if iterating, else just `<purpose>.html` — e.g. `brand-reveal-v2.html`, `end-card.html`, `data-sources-reveal.html`.

If the user is iterating on an existing file, write a new `-v2`, `-v3`, etc. file rather than overwriting. Versioning is cheap and lets the user fall back.

---

## Step 4 — Use the right skeleton

Don't write from scratch. Open the matching reference file and copy its structure:

- **Brightpath:** `docs/video/kinetic/brand-reveal-v2.html`
- **Intro:** `docs/video/kinetic/scene-1-planning.html`

Both reference files follow the same skeleton — only the tokens, animations, and content vary.

### Brightpath skeleton (layers in z-order, lowest first)

```
<body bg #12131F>
  <div class="stage" 1920×1080>
    1. .ambient        — breathing radial glow (Step 5)
    2. .stars          — small dot field with twinkle (Step 6)
    3. (decoration)    — sparkles, pentagon shards, etc. ONLY if the beat needs them
    4. .drift          — tiny rising particles (optional — atmospheric)
    5. .title-block    — the actual content (text, charts, mockups)
    6. .vignette       — soft radial darkening at edges
    7. .noise          — 2.5% SVG turbulence overlay
  </div>
</body>
```

### Intro skeleton

```
<body bg #0F1117>
  <div class="stage" 1920×1080>
    .beat (1..N)       — each .beat is a full-stage absolute layer with
                         opacity:0; staggered @keyframes fadeIn animations
                         drive sequential text reveals
  </div>
</body>
```

Multi-beat intro scenes use `animation-fill-mode: forwards` so the final frame holds indefinitely — the user starts/stops the recording manually, the page never resets until reload.

---

## Step 5 — Background recipe (Brightpath register)

This is the rule that's caught the most drift so far: **the Brightpath video background must match `frontend/src/index.css` lines 12–18 verbatim**, including the `.ambient-glow` from lines 80–94. Copy it; do not "tune slightly warmer for cinematic feel" — the title card got rejected once for that exact reason.

```css
/* Page bg */
background-color: var(--color-bg-void);
background-image:
  radial-gradient(ellipse 80% 60% at 20% 10%, rgba(45, 48, 96, 0.5) 0%, transparent 70%),
  radial-gradient(ellipse 60% 50% at 80% 35%, rgba(58, 61, 117, 0.35) 0%, transparent 65%),
  radial-gradient(ellipse 70% 40% at 50% 70%, rgba(35, 37, 69, 0.6) 0%, transparent 60%),
  radial-gradient(ellipse 50% 50% at 10% 90%, rgba(58, 61, 117, 0.25) 0%, transparent 55%),
  linear-gradient(180deg, #12131F 0%, #1B1D30 30%, #181A2E 60%, #12131F 100%);

/* Ambient breathing glow — small, low-opacity, NO gold */
.ambient {
  position: absolute; top: 50%; left: 50%;
  width: 600px; height: 600px;
  background: radial-gradient(circle,
    rgba(125, 212, 163, 0.06) 0%,    /* thrive */
    rgba(184, 169, 232, 0.04) 25%,   /* insight */
    rgba(123, 184, 224, 0.03) 40%,   /* info */
    transparent 65%);
  transform: translate(-50%, -60%);
  animation: ambient-breathe 6s ease-in-out infinite;
}
@keyframes ambient-breathe {
  0%, 100% { transform: translate(-50%, -60%) scale(1.00); opacity: 0.80; }
  50%      { transform: translate(-50%, -60%) scale(1.08); opacity: 1.00; }
}
```

If the beat needs a hot spotlight under a hero element (rare), add it as a **separate** glow layer scoped to that element — never modify the canonical ambient.

---

## Step 6 — Brand mark recipe (canonical, non-negotiable)

Per `DESIGN.md` section "Brand / Wordmark," the FutureProof brand mark is `✦ FutureProof` — single warm-white token, lavender ✦ glyph (`U+2726 BLACK FOUR POINTED STAR`) to the left, never split-color, never italic.

```html
<div class="brand-row">
  <span class="brand-glyph" aria-hidden="true">&#x2726;</span>
  <span class="wordmark">FutureProof</span>
</div>
```

```css
.brand-glyph {
  font-family: 'Fredoka', sans-serif;
  font-weight: 500;
  color: var(--color-accent-insight);  /* #B8A9E8 — never any other color */
  /* Size matches wordmark cap height: at 200px wordmark, glyph is 140px */
  text-shadow: 0 0 24px rgba(184,169,232,0.55), 0 0 60px rgba(184,169,232,0.30), 0 0 120px rgba(184,169,232,0.18);
  animation: glyph-shimmer 4s ease-in-out infinite;
}
.wordmark {
  font-family: 'Fredoka', sans-serif;
  font-weight: 700;
  color: var(--color-text-primary);  /* #F5F0E8 warm white — never thrive green */
  letter-spacing: -0.025em;
  text-shadow: 0 0 40px rgba(245,240,232,0.18), 0 0 90px rgba(184,169,232,0.18), 0 0 140px rgba(125,212,163,0.12);
}
@keyframes glyph-shimmer {
  0%, 100% { transform: scale(0.96); filter: brightness(0.92); opacity: 0.82; }
  50%      { transform: scale(1.06); filter: brightness(1.28); opacity: 1.00; }
}
```

If the beat does not feature the brand prominently, omit the glyph entirely — the brand mark is too valuable to use as decoration. Use it only when it's the subject.

---

## Step 7 — Animation conventions

Every keyframed motion in a Brightpath video scene should belong to one of these named families. Don't invent new periods unless the beat genuinely demands it.

| Animation | Period | Use |
|---|---|---|
| `ambient-breathe` | 6s | The single canonical background glow (Step 5) |
| `glyph-shimmer` | 4s (hero), 3.6s (smaller / secondary) | The ✦ glyph next to the wordmark and next to "Gemma." Vary the period slightly between instances so they don't lock-step. |
| `twinkle` | 4s, randomized delay per star | Background star field; opacity `0.20 → 0.85`, scale `0.85 → 1.05` |
| `drift-up` | 6s linear | Tiny insight-tinted motes rising from the bottom edge; staggered delays so one is always on screen |
| Entrance fades | 0.7–0.9s `cubic-bezier(0.2, 0.9, 0.3, 1.0)` for normal, `cubic-bezier(0.34, 1.56, 0.64, 1)` for spring/overshoot | One staggered entrance per element type, all with `forwards` so the final frame holds |

**Entrance timing pattern (Brightpath register):**

| t (s) | Element | Animation |
|---|---|---|
| 0.00 | Page background, ambient glow | Already on screen at t=0 (NO fade-in over black — the saturation IS the reveal after the page-turn) |
| 0.20 | Pre-title (e.g., "Introducing") | 0.7s fade + slide-up |
| 0.50 | ✦ glyph | 0.9s spring scale-in (94 → 102 → 100) |
| 0.80 | Wordmark / hero text | Same spring as glyph, slightly delayed |
| 1.40 | Decoration cascade (sparkles, chart elements, etc.) | 90ms stagger between siblings |
| 1.80 | Tagline / supporting copy | 0.8s fade + slide-up |
| 2.20 | Credit row / footer | 0.9s fade |
| 2.50+ | Idle loops take over | `ambient-breathe`, `glyph-shimmer`, `twinkle`, `drift-up` |

Holds 3.0–4.5s of idle is the recommended duration for a static title card. Multi-beat scenes hold their final frame indefinitely.

**Reduced-motion override** (mandatory — Brightpath rule):

```css
@media (prefers-reduced-motion: reduce) {
  .ambient, .star, .brand-glyph, .credit .credit-glyph, .drift {
    animation: none !important;
  }
  /* Plus: set every entrance-animated element to its final state */
  .brand-row, .tagline, .credit, .pre-title { opacity: 1; transform: none; filter: none; }
}
```

---

## Step 8 — Self-contained file rules (Brightpath register)

Brightpath video scenes must be **portable** — droppable into any folder, any browser, any future repo state, and still render identically.

- **Inline every CSS token** as `--color-*` custom properties at the top of the `<style>` block. Do not `@import` the shared `_shared/tokens.css` for Brightpath scenes (the intro scenes can, because they share so much).
- **Inline every animation, keyframe, and override** in the same `<style>` block.
- **Inline SVG only** — no external SVG files, no image assets unless absolutely required (and if required, put them in a sibling `assets/` folder and reference relatively).
- **Google Fonts CDN is the only external dependency allowed** — `<link rel="preconnect">` + `<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Nunito:wght@400;600;700;800&display=swap">`.
- **No JavaScript** unless the beat genuinely cannot be done in CSS (e.g., a typewriter effect that needs precise timing). If you reach for JS, ask the user first.
- **Comment generously** at the top of the file with: timeline, layer order, color choices, and what changed from the previous version.

The intro register can use the shared CSS files (`_shared/tokens.css`, `_shared/base.css`) because every intro scene shares the same palette and primitives. The Brightpath register can't — every Brightpath scene tends to want its own micro-tweaks.

---

## Step 9 — Voice (when text appears on screen)

Defer to the canonical FutureProof voice (`docs/reference/voice-guide.md`) and the script. If you find yourself writing copy:

- **Don't paraphrase voiceover.** On-screen text complements the VO; it doesn't repeat it. If the VO says "$1.8 trillion," the on-screen number can be `$1.8T` — but never the same words.
- **Numbers carry the load** in this video. Whenever a beat is dramatic, see if a single specific number can do the work of a sentence (e.g., "372:1" instead of "the counselor ratio is bad").
- **No marketing fluff.** Voice-guide-banned vocabulary (revolutionizing, unlock, transform, your journey, dream career) never appears on screen.
- **Flag uncertainty.** If you're inventing on-screen text without an explicit script line, say so and ask the user to confirm — copy is the fp-copywriter agent's territory and should usually be delegated.

---

## Step 10 — Hand-off

After writing the file:

1. State the file path you wrote.
2. Describe what's on screen, the entrance timeline (in seconds), and the idle duration.
3. Mention the existing preview helper: `scripts/preview_title_card.sh <path>` opens any file in chromeless app mode.
4. **Do NOT** describe how to record — the user records in Chrome themselves. The recorder script (`scripts/record_title_card.py`) exists if they ask, but don't volunteer it.

If anything in the file should be reviewed by another agent before the user records, name the agent: `fp-design-visionary` for visual taste, `fp-design-auditor` for token compliance, `fp-copywriter` for any on-screen text. Don't auto-spawn them — recommend, then wait.

---

## Common failure modes (from prior collateral work)

- **"Tuning the background warmer for cinematic feel."** Don't. The canonical gradient + the canonical ambient already produce the warmth. Adding extra opacity or hot-spot glows produces a stage-spotlight effect that doesn't match the app and breaks the "page-turn into the actual product world" reading.
- **Splitting the wordmark color** (e.g., `Future` warm-white, `Proof` thrive-green). The brand spec is one warm-white token. Always.
- **Forgetting the ✦ glyph** next to the wordmark in chrome contexts. Glyph + wordmark are inseparable.
- **Decorative sparkles around the wordmark.** Tried once on the title card; user removed them. Decoration cascades must serve a narrative function — pentagon-color shards that foreshadow Beat 8, data-source logos cascading into Gemma at Beat 7. If they're just "magic dust," cut them.
- **Using `caution` (gold `#F2D477`) in the ambient glow.** The app's `.ambient-glow` is thrive + insight + info only. Gold reads as a yellow spotlight and breaks register.
- **Mixing the two registers in one file.** A Brightpath scene with a cold-red `#DC2626` accent is incoherent. If a scene needs to be a transition, build the page-turn in the editor; don't try to crossfade registers inside one HTML file.
- **External assets that won't be on disk a year from now.** Inline SVG, inline CSS, fonts from CDN only.
- **No `prefers-reduced-motion` override.** Every Brightpath surface must respect it. Even video collateral, even though the recording is wall-clock.

---

## Reference files

- `docs/video/kinetic/brand-reveal-v2.html` — canonical Brightpath title card; copy its skeleton
- `docs/video/kinetic/scene-1-planning.html` — canonical multi-beat intro scene
- `docs/video/kinetic/README.md` — file index + register guidance
- `docs/video/futureproof-video-script-v1.md` — the script
- `DESIGN.md` — Brand/Wordmark, Color Tokens, Motion System (sections 0, 1, "Brand / Wordmark", "Background Gradient", "Motion System")
- `frontend/src/index.css` — canonical app background + `.ambient-glow` (lines 12–94) — the source of truth for the gradient recipe
- `frontend/src/styles/tokens.css` — token names + hex values for cross-checking
- `docs/reference/voice-guide.md` — voice rules for any on-screen copy
