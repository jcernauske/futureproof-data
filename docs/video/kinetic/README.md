# Kinetic Typography Clips — FutureProof Video Intro

Nine HTML files. Eight typography beats from Scenes 0–1, plus the AI Wave
smash cut at Beat 0e. Each file auto-plays on load, runs to completion, and
holds the final frame indefinitely so you can stop the recording cleanly.

Specs: `docs/specs/video1.md` (typography beats),
`docs/specs/video-ai-wave.md` (AI Wave smash cut).
Source script: `docs/video/futureproof-video-script-v1.md`.

---

## Deliberate Brightpath Deviation

**The intro is built in a different visual register than the rest of the app.**
Brightpath's warm palette (Fredoka display type, gold/orange/green accents)
belongs to Scene 2 onward, when the FutureProof product reveals. The intro is
meant to feel like the world *before* FutureProof: cold, anxious, editorial.
Think New York Times "The Daily" social cards, The Atlantic's data covers, or
Adam Curtis intertitles — not a friendly SaaS onboarding flow.

That visual contrast — cold serious editorial → warm illuminated Brightpath —
is itself a narrative beat. When Scene 2 hits and the first product UI fades in,
the audience should feel the temperature shift.

**Intro register (these 8 files only):**

| | Intro | Brightpath (Scene 2+) |
|---|---|---|
| Typeface | Inter, weights 400/500/700/900 | Fredoka display, Nunito body |
| Background | `#0F1117` (cold dark, slightly darker than `--color-bg-deep`) | `--color-bg-deep` `#1B1D30` |
| Body text | `#E5E7EB` cold off-white | `--color-text-primary` warm off-white |
| Strong text | `#FFFFFF` pure white | varied accent colors |
| Accent | `#DC2626` cold red — single accent for whole intro | full palette: thrive/caution/alert/insight/empathy |

**Red is used sparingly.** All hierarchy in the intro comes from size and
weight. The red accent only fires at the five moments where the script lands
emotionally:

- `beat-0c` — "anxiety level."
- `beat-0h` — "preying on" + the strikethrough line itself
- `beat-1abcd` — "as a teenager." (the visual climax of the entire intro)
- `beat-1gh` — "fixed this for kids."

In `beat-0h`, "**marketing to**" is intentionally **white**, not red. The swap
from honest red to neutral white mirrors the editorial softening the script is
calling out.

The font and color shift between intro and product reveal is deliberate. Do
not "fix" it back to Brightpath consistency.

---

## Files

| File | Beat | Duration (after pre-roll) | VO |
|---|---|---|---|
| `beat-0b-age-of-ai.html` | 0b | 6s | "In 2026, Gemma, Gemini, Claude and Opus ushered us into the Age of AI." |
| `beat-0c-anxiety-level.html` | 0c | 6s + infinite pulse hold | "As the father of 3 teenagers, this has not helped my anxiety level." |
| `beat-0e-ai-wave.html` | 0e | 24s — anchored to video timeline (see below) | (silent — five article-headline cuts) |
| `beat-0f-not-easy-before.html` | 0f | 6s | "And it's not like it was easy before." |
| `beat-0h-marketing-strikethrough.html` | 0h | 8s — signature beat | "And the colleges? They're preying on / marketing to the innocence of kids." |
| `beat-0j-where-does-that-leave.html` | 0j | 6s | (silent) |
| `beat-1abcd-amazing-but-teenager.html` | 1a–1d | 22s — 4 sequential states | "AI is amazing. But… 4 months… 4 years… as a teenager." |
| `beat-1ef-but-heres-the-thing.html` | 1e–1f | 8s | "But here's the thing. There is data that can help kids make better choices." |
| `beat-1gh-hard-to-find.html` | 1g–1h | 12s | "Hard to find. Hard to combine. Almost impossible to interpret. Which is why nobody's fixed this for kids." |

Every file starts with **2 seconds of pure black** before the first text appears.
That pre-roll gives you margin to start the QuickTime recording without clipping
the opening text. Trim it off in iMovie when placing the clip.

After the timed animation completes, the final frame is held with
`animation-fill-mode: forwards`. You can leave the page open as long as you want;
nothing will reset until you reload.

---

## Recording Setup

1. Open **Chrome** (not Safari — fewer font-rendering surprises).
2. Open the HTML file by double-clicking, or drag it onto Chrome:
   `file:///Users/.../docs/video/kinetic/beat-0b-age-of-ai.html`
3. Press `Ctrl+Cmd+F` to enter full-screen.
4. Open **QuickTime Player → File → New Screen Recording** (or use Shift+Cmd+5).
5. Set the recording region to **just the Chrome window**, or use Cmd+5 to select
   the entire screen if Chrome fills it.
6. Microphone: **None**. Audio is recorded separately for the voiceover track.

The HTML stage is built at 1920×1080. On a Retina display, full-screen Chrome
will render at the native resolution; the stage is centered with letterboxing
above/below if your screen is wider than 16:9.

---

## Recording Procedure

For each beat:

1. Start the QuickTime recording.
2. Switch to Chrome and press **Cmd+R** to reload the page — this restarts the
   animation from time zero.
3. Wait for the beat duration in the table above, plus 2–3 seconds of held
   final frame.
4. Stop the QuickTime recording.

The 2-second pre-roll black at the start of each clip means you don't have to
hit the reload at the exact moment you start recording — pre-roll covers any
sloppiness.

---

## Post-Recording

1. QuickTime saves the .mov to `~/Movies/` (or `~/Desktop/` depending on settings).
2. Open the clip in QuickTime and use **Edit → Trim** to remove the dead
   pre-recording space (everything before the cursor reload moment is fine to keep
   — the on-screen black covers it).
3. Drag the .mov into iMovie at the correct timeline position.
4. Align the start of the visible text with the corresponding voiceover phrase.
   The 2-second black pre-roll gives you slack on either side.

---

## Beat-Specific Notes

### `beat-0h-marketing-strikethrough.html` — the signature beat

This is the most complex animation. The viewer needs to:
1. Read "**preying on** the innocence of kids." (preying is in red)
2. See the red strikethrough draw across "preying on."
3. See "**marketing to**" type in WHITE above the struck-through phrase.

The white-on-red contrast makes the editorial softening visible. If the
strikethrough is hitting before the audience can read the line, slow your
recording down — the animation is timed at exactly the values in the spec, so
adjust by trimming the trailing hold rather than re-timing the animation.

### `beat-1abcd-amazing-but-teenager.html` — the climax

This beat is 22 seconds long and contains the visual climax of the entire intro:
the word "**teenager**" rendered in red at 280px (the largest text in the
entire intro). Make sure your recording captures the full hold — the negative
space around "teenager" is part of the impact.

"amazing", "4 months", and "4 years" all stay white at heavier weight or larger
size. Red is reserved for the climax word only.

### `beat-0c-anxiety-level.html` — pulses indefinitely

After the initial 6-second build, "anxiety level." (red) continues to pulse
(scale 1.0 → 1.025 → 1.0 over 1.6s, infinite) so the silence-drop in iMovie has
visual life. Record at least 8–10 seconds beyond the build so iMovie has enough
material to hold during the silence cue.

### `beat-0e-ai-wave.html` — long pre-roll, then five smash cuts

Unlike the other beats, this one's animation delays are anchored to the **video
timeline**, not file-relative. The page sits black for the first 16 seconds,
then fires:

- 0:16.0 → `01-goldman.png` (Goldman Sachs — How Will AI Affect the Global Workforce?)
- 0:16.7 → `02-worklytics.png` (Worklytics — AI Adoption Benchmarks 2025)
- 0:17.4 → `03-mckinsey-40.png` (McKinsey — 40% by 2030)
- 0:18.1 → `04-mckinsey-57.png` (McKinsey — November 2025 bombshell, 57%)
- 0:18.8 → `05-fortune-altman.png` (Fortune — Sam Altman / "AI washing"). Held
  0.9s as the punchline — slightly longer than the rest.
- 0:19.7 → smooth fade to black over ~4s, finishing at 0:24.0.

Recording: load the file, reload, and walk away. Don't stop early — the fade
is part of the beat. The cuts use `steps(1)` so transitions are hard, not
crossfaded.

Image assets live at `video/images/ai-wave/` at the project root. The HTML
references them via relative paths (`../../../video/images/ai-wave/...`); if
you move either side, fix both.

---

## Troubleshooting

**Fonts look wrong / not Inter.** The Inter .woff2 files in `_shared/fonts/`
must be present. They're loaded via `@font-face` with `font-display: block`,
which means the browser will hide text until the font is loaded — so a flash of
the wrong font shouldn't happen. If you see the system font, the .woff2 files
are missing or the path is broken; check the browser DevTools network tab.

The folder also contains older Fredoka / Nunito / Space Mono .woff2 files left
over from the original Brightpath-styled draft. Those are no longer referenced
by any CSS and exist only because the spec asked for them. They are harmless.

**Animation timing feels off.** All timings are CSS-based with `animation-delay`,
which is deterministic. If a beat looks wrong, compare to the spec
(`docs/specs/video1.md`) — if the file matches the spec exactly and the timing
still feels wrong, that's a content issue, not an implementation issue.

**Recording shows a gray flash on reload.** Chrome briefly shows a white/gray
frame between page-clear and page-render. The 2-second pre-roll black covers
this — make sure to trim the clip start in iMovie or QuickTime.

---

## File Locations

```
docs/video/kinetic/
├── _shared/
│   ├── tokens.css           # Brightpath design tokens (kept for reference; not consumed in intro)
│   ├── base.css             # Inter @font-face + cold palette + animation primitives
│   └── fonts/               # Inter 400/500/700/900 (and unused Brightpath fonts from earlier draft)
├── beat-0b-age-of-ai.html
├── beat-0c-anxiety-level.html
├── beat-0e-ai-wave.html
├── beat-0f-not-easy-before.html
├── beat-0h-marketing-strikethrough.html
├── beat-0j-where-does-that-leave.html
├── beat-1abcd-amazing-but-teenager.html
├── beat-1ef-but-heres-the-thing.html
├── beat-1gh-hard-to-find.html
└── README.md  ← you are here
```
