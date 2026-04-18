# Design Vision — Gemma 4 Good Submission

*Date: 2026-04-17 · Deadline: 2026-05-18 · Runway: 4 weeks, 1 day*
*Author: fp-design-visionary*
*Grounding: `DESIGN.md`, `docs/reference/voice-guide.md`, `frontend/src/screens/LandingScreen.tsx`, `frontend/src/components/landing/PentagonGlow.tsx`, three prior reports (marketing-landing-scope, in-app-copy-audit, hackathon-ship-plan)*

---

## 1. Executive Summary — The One Visual Idea

**The Constellation.**

FutureProof's signature asset is a night-sky metaphor that already lives in the in-app Brightpath system: radial gradients over `bg-void`, twinkling 2px stars, `ambient-breathe` glow, pentagon as a constellation. The landing page is **that constellation, zoomed out** — the in-app pentagon is one point of light among many. As the visitor scrolls, the camera pans across the night sky and each section illuminates a different constellation: the five stats, the five bosses, the branching tree, the Ollama rig.

**Why this carries the submission:**

1. **It's already built.** `PentagonGlow.tsx` ships. The twinkle animation ships. The ambient-breathe gradient ships. We extend the system, we don't invent one.
2. **It earns continuity.** A judge clicks from landing to app and the camera simply pushes in — same sky, same indigo, same warm-white typography. No "marketing vs. product" seam.
3. **It's restrained.** One metaphor, consistently applied. Not a catalog of animated gradients.
4. **It rhymes with the thesis.** "A college degree isn't a destination. It's a starting position." A starting position implies a map. The constellation *is* the map.

**What it is not:** scroll-jacked full-screen cinematics, 3D renders, particle physics demos, "stunning animations" as substance replacement. Those are hackathon tropes that read as compensating. FutureProof has receipts. The design should sit quietly on top of them.

**Leverage triage:** given 4 weeks, the design budget goes to (a) the landing page's above-the-fold, (b) the branch-tree screenshot composition, and (c) one 6-second Stage-2 Reveal polish pass for the demo video. Nothing else moves.

---

## 2. Landing Page — Section-by-Section Design Spec

**Global decisions first, then per-section.**

### 2.1 Global: the Landing Page Rulebook

| Decision | Value | Rationale |
|---|---|---|
| Background | `bg-bp-void` (#12131F) with the **existing** layered radial gradient from `DESIGN.md §Surface Treatments → Background Gradient`, flipped to read top-to-bottom as the visitor scrolls | Re-use. One system. |
| Width system | `max-w-[1280px]` container, 12-column grid via existing `PageContainer` pattern. Landing uses `bleed` variant at section breaks, `centered` inside sections | Ships already. |
| Section rhythm | Each section = one full viewport on desktop (≥720px tall), never more than 1 screenful of content | Reads as chapters, not as a pitch deck scroll |
| Section boundaries | Never hard cuts. Each section fades into the next via a thin (1px) horizontal line at `border-subtle` (rgba 255,255,255,0.06) offset by a subtle gradient wash underneath | Preserves "cinematic dark" continuity |
| Type — hero | `font-display` (Fredoka 700), `text-[72px] desktop:text-[96px]` (new scale; see §Extensions), line-height 1.05, `text-text-primary` | Landing gets ONE size bigger than in-app title (48px) because marketing headlines breathe; in-app never does |
| Type — sectionhead | `font-display` (Fredoka 700), `text-title` (40px) → `text-heading` (28px) on mobile | Already tokenized |
| Type — body | `font-body` (Nunito 400), `text-body-lg` (18px), `text-text-secondary`, max-width 62ch | Reading-ergonomic; matches in-app |
| Type — data/receipts | `font-data` (Space Mono 400), `text-data-sm` (13px) and `text-data` (16px), `text-text-muted` for labels, stat colors for values | Mirrors in-app receipt panels exactly |
| Motion philosophy | **No scroll-jacking.** Natural scroll. Each section reveals its content via `whileInView` using `springs.smooth` + `stagger.normal` (80ms). One section-level hero animation (the constellation pan in §A). Everything else is understated | Voice guide: "brevity is the flex." Applies to motion too |
| CTA rule | Exactly ONE primary button style on the page. Hero has it. Footer has it. No secondary accent colors for buttons anywhere else | Prevents fintech-landing bloat |
| Mobile | All sections stack. No horizontal carousels. Hero constellation scales to 320px × 320px. Grid becomes single-column below 768px | Ships with current `PageContainer` conventions |

**Accessibility/performance guardrails the design is built around:**
- Noise overlay + ambient glow use `pointer-events: none` and respect `prefers-reduced-motion` (twinkle, breathe, particles pause). Already in `index.css` — landing inherits.
- Hero image is SVG + CSS, not video. Lighthouse-friendly.
- First meaningful paint: hero headline + CTA. Constellation animation can start mid-paint without blocking.

---

### 2.2 Section A — Above the Fold (Hero)

**The emotion: arrival at a planetarium before the show begins.** The visitor lands in the same dark indigo as the app. Something glows at the center of the screen. One line of text, unambiguous. One button, also unambiguous. Nothing else demands attention. Three seconds of judge attention is held by stillness, not by motion.

**ASCII wireframe (desktop, 1440px viewport):**

```
┌────────────────────────────────────────────────────────────────────────┐
│ [twinkling stars scattered across the viewport, 0.05→0.45 opacity]     │
│                                                                         │
│                                                                         │
│                                                                         │
│                   ·   ERN                                              │
│                                                                         │
│                  HMN  ◯  ROI      ←  Pentagon-Constellation             │
│                        ·              (320px, PentagonGlow              │
│                                        component + scale + breathing    │
│                  GRW     RES           glow at 6s cycle)                │
│                                                                         │
│                                                                         │
│      A college degree isn't a destination.                             │
│      It's a starting position.                                         │
│                                                                         │
│      See where your degree actually leads. 700K rows of public data,   │
│      zero admissions brochure.                                         │
│                                                                         │
│                   ┌──────────────────────────┐                         │
│                   │   Start  ✦               │   Watch the 3-min demo →│
│                   └──────────────────────────┘                         │
│                                                                         │
│                                                                         │
│                                                                         │
│      700K rows   ·   280 DQ rules   ·   7 public datasets              │
│      Every number has a receipt.                                        │
│                                                                         │
│   [↓ scroll indicator: thin 1px line fading down, 0.15 opacity]        │
└────────────────────────────────────────────────────────────────────────┘
```

**Component-by-component spec:**

| Element | Token / spec | Motion | Copy |
|---|---|---|---|
| Background | `bg-bp-void` + layered radial gradient per DESIGN.md §Surface Treatments | `ambient-breathe` (6s) inherited | — |
| Twinkle field | `.star` dots, ~40 scattered across viewport, 2px, `twinkle` animation (4s), 0.05→0.45 opacity | Inherited | — |
| Pentagon-Constellation | `<PentagonGlow size={320} />` reused from `frontend/src/components/landing/` | Existing internal animation: vertex glows cycle at 4s stagger, particle motion, axis breathing. Outer container gets one additional 7s vertical drift (y: 0 → -10 → 0) — matches in-app | — |
| Headline | `font-display`, `text-[72px] desktop:text-[96px]` (Extension — see §9), weight 700, `text-text-primary`, line-height 1.05, letter-spacing -0.02em, center-aligned, max-w: 900px | Stagger child, delay 0.2s, `springs.smooth`, fadeInUp (y:24) | "A college degree isn't a destination.<br/>It's a starting position." — note: **remove the current `gradient-tagline` span treatment**. The headline lands harder as a single color. See §9 for rationale. |
| Subhead | `font-body` (Nunito), `text-body-lg` (18px), `text-text-secondary`, max-w: 560px, center-aligned, line-height 1.5 | Stagger child, delay 0.35s | "See where your degree actually leads. 700K rows of public data, zero admissions brochure." (from copywriter audit P1) |
| Primary CTA button | `accent-thrive` background, `text-inverse` text, height 56px (one size up from in-app 48px — marketing CTAs deserve presence), padding 0 32px, `rounded-lg`, `font-body` weight 700, `text-cta` (17px). Sparkle `✦` post-label at 0.7 opacity | Stagger child, delay 0.5s. On hover: `shadow-glow-thrive`, darken to #6bc494. On press: `scale(0.97)` | "Start ✦" |
| Secondary link | `text-accent-info`, `text-body` (16px), underlined on hover only, no box | Inline with CTA, `gap-6` between | "Watch the 3-min demo →" |
| Data footer | `font-data`, `text-micro` (12px), `text-text-muted`, opacity 0.45, tracking wide, center-aligned, absolute bottom-8 | Stagger child, delay 0.7s | "700K rows · 280 DQ rules · 7 public datasets · Every number has a receipt." **Note:** corrected to 7 datasets per the marketing-scope claims audit (Anthropic Economic Index is shipped). |
| Scroll cue | 1px vertical line, 32px tall, `border-subtle` opacity 0.3 → 0 gradient, fades in at 1.5s | Gentle bobbing (y: 0 → 4 → 0, 2s infinite) | — |

**The magic of this hero:**

1. **The pentagon is doing the work of five images.** It's the product's radar chart *and* the marketing logomark *and* the scroll indicator (when it drifts upward 10px, the eye follows downward). One asset, three jobs.
2. **The headline reads in 1.5 seconds.** 11 words, two sentences, one idea. A judge in scrub mode gets the thesis before their thumb leaves the trackpad.
3. **There is no "feature carousel" or "trusted by" logo band.** The entire above-the-fold is: one image, one sentence, one button, one receipt line. Everything else trusts the scroll.
4. **The CTA verb earned its place.** "Start" not "Try", not "Get started", not "Launch your future." One word. The copywriter's P2 — promoted to the landing page's P0, because it's the most-seen button on the entire submission surface.

**Video-composition note:** this hero is also the video's closing frame. When the voice-over says "start" the button gets a subtle `shadow-glow-thrive` pulse. The pentagon continues to breathe. End card = landing hero with no cursor. The video ends in the same frame that begins the product.

---

### 2.3 Section B — The Problem (Why This Exists)

**The emotion: being told the thing no one told you.** The visitor has already scrolled once. They don't need another glow. They need a sentence that names a truth the admissions website omitted.

**Layout:** centered single-column, typography only. No imagery. 8-column span on desktop, full-width on mobile. Vertical padding: 160px top, 160px bottom (both reduce proportionally on mobile).

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                                                                         │
│   Your college probably isn't going to mention the ceiling.            │
│                                                                         │
│                                                                         │
│   Admissions brochures tell you about the first job. They don't tell   │
│   you what the tenth one pays, or which careers are 82% exposed to AI, │
│   or whether your major survives the next decade of automation.        │
│                                                                         │
│   Your guidance counselor has 400 other students and a quarter-hour    │
│   with you.                                                             │
│                                                                         │
│   A private-school senior with a $400/hour counselor gets a different  │
│   answer than a first-gen community-college student. That's the gap    │
│   FutureProof closes.                                                   │
│                                                                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Motion | Notes |
|---|---|---|---|
| Section headline | `font-display` weight 700, `text-[56px] desktop:text-[64px]` (new scale — see §9), `text-text-primary`, max-w: 960px, line-height 1.15, letter-spacing -0.01em | `whileInView`, fade + y:32, `springs.smooth`, delay 0 | "Your college probably isn't going to mention the ceiling." |
| Body | `font-body` 400, `text-body-lg` (18px), `text-text-secondary`, max-w: 62ch (~620px), line-height 1.6, vertical gap between paragraphs 28px | `whileInView`, stagger children at `stagger.slow` (100ms) | Verbatim from marketing report §2 Section B |
| Highlighted stat inline | The "82% exposed to AI" phrase gets wrapped in `<span>` with `text-accent-insight` and `font-data` weight 700 at same size — a typographic receipt | Inherits paragraph reveal | Voice-guide earned swagger: a number sits inside the sentence |
| Dollar figure inline | "$400/hour counselor" gets `text-accent-alert` (debt-amber) + `font-data` weight 700 | Same | Same rationale |

**The magic here:**

- **Two typographic receipts per paragraph, max.** Not more. The *absence* of highlights in the rest of the body is what makes the highlights pop.
- **No illustration.** Every hackathon submission over-illustrates the problem section. FutureProof lets silence do it. A 56px headline on a black screen is an image.
- **The headline is a quote from the voice guide itself.** "Your college probably isn't going to mention the ceiling" is literally the example line in `docs/reference/voice-guide.md`. Using it here is a signal to the judge who reads both — we're the system we wrote.

---

### 2.4 Section C — How It Works (The Core Loop)

**The emotion: recognition.** By the end of this section the visitor understands exactly what the product does. Three beats: stats, bosses, branches. Each beat gets one sentence and one image.

**Layout:** three-column grid on desktop (each card spans 4 cols), stacked on tablet/mobile. Section headline full-width above. This is the only section with a card grid — everywhere else is typography.

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   Three things happen when you spec a build.                           │
│                                                                         │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│   │                  │  │                  │  │                  │     │
│   │  [Reveal shot]   │  │ [Gauntlet shot]  │  │ [Branch tree     │     │
│   │  pentagon +      │  │  boss mid-reroll │  │  shot] — 15      │     │
│   │  Gemma's Take    │  │  skill card      │  │  paths lit       │     │
│   │                  │  │  equipped        │  │                  │     │
│   │                  │  │                  │  │                  │     │
│   └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│                                                                         │
│   You see the stats.      You fight the bosses.   You see the branches.│
│                                                                         │
│   Five numbers, one to    Fight AI, Student      A degree isn't one    │
│   ten. Every stat has a   Loans, the Market,     job. Tap any career   │
│   tappable receipt.       Burnout, the Ceiling.  and the tree unfolds. │
│                                                                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Motion | Copy |
|---|---|---|---|
| Section headline | `font-display` 700, `text-title` (40px), `text-text-primary`, max-w: 720px, center-aligned, margin-bottom 80px | `whileInView` fade+y, delay 0 | "Three things happen when you spec a build." |
| Card | `bg-bp-mid`, `border border-subtle`, `rounded-xl` (20px), padding 32px, aspect ratio 4:5 on desktop (taller than wide — reads as a "frame"), aspect 16:10 on mobile | `whileInView` scaleIn (0.95→1, opacity 0→1), `springs.smooth`, stagger 120ms between cards | — |
| Screenshot inside card | Full-bleed within card padding; 16:10 aspect; `rounded-lg` (14px); subtle drop shadow `shadow-md` | On card hover (desktop): `translateY(-3px)`, screenshot brightens slightly via 2% brightness filter | See §4 Screenshot Strategy for exact shots |
| Card caption label | `font-data` 11px, weight 700, letter-spacing 2px, uppercase, `text-accent-info`, margin 16px 0 8px | Inherits card reveal | "STATS" / "GAUNTLET" / "BRANCHES" — three words |
| Card heading | `font-display` weight 600, `text-heading` (28px), `text-text-primary`, margin-bottom 12px | Inherits | "You see the stats." / "You fight the bosses." / "You see the branches." |
| Card body | `font-body` 400, `text-body` (16px), `text-text-secondary`, line-height 1.5 | Inherits | Trimmed from marketing report §2 Section C — ~40 words per card |

**The magic here:**

1. **The three captions form a spine:** *see / fight / see*. Read vertically, the page reveals its own metaphor: observation → action → observation. The RPG loop in three verbs.
2. **The cards breathe.** On hover, `translateY(-3px)` + shadow upgrade (already in DESIGN.md §Components → Cards). Desktop only. Mobile respects reduced-motion.
3. **One sparkle rule holds.** No card has a ✦. Sparkles belong on CTAs and the hero. Card decoration would dilute both.
4. **The screenshots earn the screens.** See §4 for capture instructions. They're not product-demo stills — they're composed, intentional, one-truth-per-frame.

---

### 2.5 Section D — The Receipts Story

**The emotion: "oh, they're serious."** This is the section where a skeptical judge inspects the claim. The design makes the inspection easy.

**Layout:** split layout, asymmetric. Left column (7 cols) = typography. Right column (5 cols) = a single hero-sized screenshot of an expanded receipt panel from the live app. Stacked on tablet/mobile with screenshot below text.

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   Every number is tappable.          ┌──────────────────────────┐      │
│                                      │                          │      │
│   Your stats aren't vibes. Tap any   │ [Expanded receipt panel  │      │
│   number and you get the raw         │  screenshot from live    │      │
│   inputs, the thresholds, the        │  app — stat card with    │      │
│   source datasets, and the exact     │  receipt opened, raw     │      │
│   computation that produced it.      │  inputs visible]         │      │
│                                      │                          │      │
│   700,000 cross-source rows.         │                          │      │
│   280 data quality rules.            │                          │      │
│   Seven data contracts.              │                          │      │
│   A chaos-monkey-hardened pipeline   │                          │      │
│   that catches its own mistakes      │                          │      │
│   before they reach you.             │                          │      │
│                                      │                          │      │
│   Your college brochure didn't       │                          │      │
│   do that.                           └──────────────────────────┘      │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Motion | Copy |
|---|---|---|---|
| Section headline | `font-display` 700, `text-title` (40px) | whileInView fade+y | "Every number is tappable." |
| Lead paragraph | `font-body` 400, `text-body-lg` (18px), `text-text-secondary` | Stagger child | First paragraph from marketing report §2 Section D |
| Receipt stat block | `font-data` 700, `text-data-lg` (24px), stat color per line, stacked tightly (line-height 1.3) | Stagger children, stat colors activate one-by-one at 120ms intervals | "700,000 cross-source rows." etc. — each line its own element |
| Kicker line | `font-body` 400, `text-body` (16px), `text-text-muted`, italic | Final stagger child | "Your college brochure didn't do that." — one-time use per voice guide |
| Right-column screenshot | Full-bleed within 5-col span, 9:16 aspect (portrait — it's a panel), `rounded-xl` (20px), `shadow-lg`, subtle 1px border `border-default` | whileInView scaleIn (0.9→1), `springs.bouncy` (deliberate — this is the "proof" moment, a subtle overshoot communicates confidence) | Capture from live app — see §4 |
| Glow behind screenshot | Absolute-positioned `shadow-glow-insight` radial blur (rgba(184, 169, 232, 0.2), 120px blur), -z-10 | Inherits | Subtle — communicates "this is data/intelligence" |

**The magic here:**

- **Each data line illuminates separately.** 120ms stagger means the eye reads "700,000 rows" → "280 rules" → "seven contracts" as sequential beats, not a list. Same rhythm as reading out loud.
- **The screenshot is the proof, not the hero.** It sits on the right with a soft glow — present, but never the first thing you read. The words make the claim; the screenshot settles the argument.
- **"Your college brochure didn't do that" is italic body text, not a pull-quote.** The voice-guide example works because it's dry. Treating it as a call-out treatment (40px centered all-caps) would undercut it. Italic 16px body is the correct register.

---

### 2.6 Section E — Run It Yourself (Gemma + Ollama)

**The emotion: technical credibility.** The Ollama track is won or lost in this section. Judges reading the Ollama track submission need to feel that this isn't a marketing claim, it's a config flag.

**Layout:** three-column on desktop — terminal screenshot (5 cols) / text (4 cols) / laptop illustration (3 cols). On tablet, collapses to stacked: text first, terminal below, laptop stat-block at bottom. On mobile, single column.

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   Any school can run this on their own hardware.                       │
│   Forever. At zero cost.                                                │
│                                                                         │
│   ┌──────────────────────┐  FutureProof runs on         [ · · · · · ]  │
│   │ $ ollama pull        │  Gemma 4 through Ollama.     [ · · · ·   ]  │
│   │   gemma4:e4b         │  Flip one environment        [ ·         ]  │
│   │ ✓ complete            │  variable and the whole      [            ]  │
│   │                      │  stack — stats, fights,      [ Laptop art  ]  │
│   │ $ INFERENCE_BACKEND= │  Gemma's coaching, the       [ w/ pentagon ]  │
│   │   ollama npm run dev │  branch tree — works on a    [ drawing on  ]  │
│   │ ✓ ready at :5173     │  school's own server.        [ the screen  ]  │
│   │                      │                              [            ]  │
│   │ (blinking cursor)    │  No cloud bill. No student   [            ]  │
│   └──────────────────────┘  data leaves the building.   └────────────┘  │
│                             No ongoing cost.                            │
│                                                                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Motion | Copy |
|---|---|---|---|
| Section headline | `font-display` 700, `text-title` (40px), `text-text-primary`, max-w: 760px | whileInView fade+y | "Any school can run this on their own hardware. Forever. At zero cost." |
| Terminal screenshot | Actual SVG-rendered terminal (not PNG). Dark `bg-bp-void` with 3 traffic-light dots (grey — not colored, no OS-branding), `font-data` (Space Mono), 14px, green prompt (`accent-thrive`), warm-white text. 4:3 aspect. `rounded-lg` with `border-default` | whileInView. Typing animation optional — 2.5s sequence typing `ollama pull`, pause, typing `INFERENCE_BACKEND=ollama`. Respects `prefers-reduced-motion`. | Literal commands: `ollama pull gemma4:e4b` → `INFERENCE_BACKEND=ollama npm run dev`. Green checkmarks. Honest to `gemma_client.py` |
| Body column | `font-body` 400, `text-body-lg` (18px), `text-text-secondary`, line-height 1.6. Three short paragraphs. | Stagger children | From marketing report §2 Section E. **Critical claim edit:** "When a school runs FutureProof on Ollama, no student data leaves the building" (per ship plan §6 risk 2 — scoped to deployment) |
| Laptop illustration | Simple plush-illustration style per `DESIGN.md §Illustration Style`. Matte-dark laptop, pentagon constellation glowing on screen. 1 asset, reusable in README + video thumb | whileInView scaleIn, `springs.smooth` | — |
| Glow treatment | Subtle `shadow-glow-thrive` behind the terminal (green, subtle — local = thrive green) | Inherits | Communicates "this works, locally, now" |

**The magic here:**

1. **The terminal is SVG, not a PNG.** Every character is real text. Copy-pasteable. Zoomable. No "looks fake" risk.
2. **The green checkmark is `accent-thrive` — the same green as WIN states in-app.** A judge cross-referencing the system would clock it. Small, deliberate.
3. **The laptop illustration is NEW asset work** — but low-effort. One plush-style laptop with the pentagon on-screen. ~2 hours in Figma or equivalent. It's the visual that anchors "any school" = a real machine, not an abstraction.
4. **"Forever. At zero cost." on its own line.** Sentence fragments carry weight. Matches the voice guide's "short sentences, concrete nouns."
5. **The claim has been scoped.** This is the language fix the ship plan §5 calls out: never claim the live cloud demo runs on Ollama. The copy says "can run" and "when a school runs," not "runs." Video Scene 5 proves it on a second machine.

---

### 2.7 Section F — Live Demo / CTA Rail

**The emotion: "okay, I want to try it."** This is the conversion moment. It mirrors the hero CTA intentionally. Repetition is the mechanic.

**Layout:** centered, narrow. Max-width 640px. Minimal.

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                                                                         │
│              Spec your first build.                                     │
│                                                                         │
│              Takes about two minutes. No signup, no email. You'll      │
│              get a three-word name and emoji — that's your identity.   │
│                                                                         │
│                   ┌──────────────────────────┐                         │
│                   │   Start  ✦               │                         │
│                   └──────────────────────────┘                         │
│                                                                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Motion | Copy |
|---|---|---|---|
| Headline | `font-display` 700, `text-title` (40px) | whileInView fade+y | "Spec your first build." |
| Body | `font-body` 400, `text-body-lg` (18px), `text-text-secondary` | Stagger child | From marketing report §2 Section F |
| CTA button | Identical to hero CTA — same size, same label, same glow on hover | whileInView scaleIn | "Start ✦" |

**The magic here:** it's the shortest section on the page. One sentence, one paragraph, one button. The visitor arrives here if the rest worked. If they don't click, nothing more we put here would have changed that.

---

### 2.8 Section G — Data Sources (Transparency Block)

**The emotion: proof.** This is the longest-to-read section. It's OK. Judges that care will read it; the rest will scroll past and the design doesn't punish them.

**Layout:** centered, max-width 960px. The dataset table is the hero — styled as a receipt panel, not a slick feature-grid.

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   How we know.                                                          │
│                                                                         │
│   Every number FutureProof shows you traces back to one of these       │
│   public datasets. Click any row to see how it flows through the       │
│   pipeline.                                                             │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐ │
│   │ SOURCE                              ROWS      POWERS             │ │
│   │ ─────────────────────────────────────────────────────────────── │ │
│   │ College Scorecard (Field of Study)  69,947   ERN, ROI, Loans   │ │
│   │ BLS Occupational Outlook            832      Growth, Ceiling   │ │
│   │ O*NET Task & Work Context           798      HMN, Burnout      │ │
│   │ Karpathy AI Exposure                815      RES, Fight AI     │ │
│   │ Anthropic Economic Index            587      AI velocity       │ │
│   │ BEA Regional Price Parities         51       Geo adjustment    │ │
│   │ CIP-SOC Crosswalk                   626,406  The core query    │ │
│   └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│   * Composite AI exposure blends Gemma 4 task-level scoring, Karpathy's│
│     job-description baseline, and Anthropic's observed adoption share. │
│     Gemma scores 1.75 points more conservatively than Karpathy on      │
│     average across 372 overlapping occupations.                         │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Motion | Notes |
|---|---|---|---|
| Section headline | `font-display` 700, `text-title` (40px) | whileInView fade+y | "How we know." — three words, period, voice guide compliant |
| Lead | `font-body` 400, `text-body-lg` (18px), `text-text-secondary` | Stagger | Verbatim from marketing report |
| Table container | `bg-bp-mid`, `border border-subtle`, `rounded-xl` (20px), padding 24px, subtle inner border treatment per receipt-panel pattern | whileInView scaleIn, `springs.smooth` | — |
| Table header row | `font-data` 11px, letter-spacing 2px, uppercase, `text-accent-info`, border-bottom 1px `border-subtle` | — | "SOURCE · ROWS · POWERS" |
| Table body row | `font-body` 15px `text-text-primary` for source name / `font-data` 15px `text-text-secondary` right-aligned for rows / `font-body` 14px `text-text-muted` for powers | Stagger rows at `stagger.fast` (50ms) | 7 rows with correct counts (Anthropic = 7th per claims audit) |
| Row hover | Background shifts to `bg-bp-surface`, left-border 3px `accent-insight` — reuses the List Item pattern from DESIGN.md | 150ms transition | Click → opens receipt panel modal (stretch; for demo just link out to Brightsmith repo) |
| Footnote | `font-body` 400, `text-small` (14px), `text-text-muted`, italic, max-w: 720px, margin-top 24px | whileInView fade | From marketing report — the Karpathy divergence finding is load-bearing for the Kaggle writeup too |

**The magic here:** **the table IS the receipt panel.** Same bg, same border-radius, same row pattern as in-app. A judge clicking from here into the app's stat receipt sees the pattern echo immediately. Continuity by repetition.

---

### 2.9 Section H — Team / About

**The emotion: credibility without showboat.** One paragraph. No headshot unless absolutely necessary.

**Layout:** centered, narrow (max-w 640px), typography only.

**Spec:**

| Element | Token / spec | Motion | Copy |
|---|---|---|---|
| Headline | `font-display` 700, `text-heading` (28px), `text-text-primary` | whileInView fade+y | "Who built this." |
| Body | `font-body` 400, `text-body-lg` (18px), `text-text-secondary`, line-height 1.6 | Stagger | From marketing report §2 Section H |
| Inline links | `text-accent-info`, underlined on hover | — | Brightsmith link, etc. |

No glow, no illustration. Restraint is the point.

---

### 2.10 Section I — Footer

**The emotion: quiet completion.** Three rows: nav, disclaimer line, tiny data repeat.

**Layout:** full-bleed, `bg-bp-deep` (one tier lighter than the section above it — a barely-visible boundary), padding 64px 32px.

**Wireframe:**

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  FutureProof          Live app · Kaggle · GitHub · Video · Brightsmith │
│                       Voice guide · Disclaimers                         │
│                                                                         │
│  AI-estimated. Not a substitute for professional career counseling.    │
│                                                                         │
│  700K rows · 280 DQ rules · 7 public datasets · Every number has a     │
│  receipt.                                                               │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

**Spec:**

| Element | Token / spec | Copy |
|---|---|---|
| Wordmark | `font-display` 700, `text-heading` (28px), `text-text-primary` | "FutureProof" |
| Nav row | `font-body` 400, `text-body` (16px), `text-text-secondary`, inline links, gap-6 | Per marketing report |
| Disclaimer | `font-body` 400, `text-small` (14px), `text-text-muted` | Voice-compliant — calm, specific. Not scared. |
| Data line repeat | `font-data` 400, `text-micro` (12px), opacity 0.4 | Echo of the hero's data footer. Visual rhyme. |

---

## 3. In-App Polish — What's Worth Doing in 4 Weeks

The copywriter owns voice drift. I own visual drift. Here's the ruthless triage: **three visual changes earn their spot. Everything else waits.**

### 3.1 P0 Visual — Landing Screen Headline (In-App)

**What:** The in-app `LandingScreen.tsx` uses `font-display text-heading tablet:text-title` (28px/40px). The marketing landing uses 96px. The gap is too wide — the in-app Landing feels small by comparison, especially in a demo video that cuts from the marketing page to the app.

**Proposal:** Bump in-app landing headline to `text-hero` (48px) on mobile, `text-[56px]` on tablet, `text-[64px]` on desktop. Still smaller than the marketing hero (that's right; marketing is a billboard, in-app is a doorway), but large enough to feel like a real landing, not a summary.

**Leverage:** 30-minute CSS change. Every demo capture of Screen 1 now looks intentional. The video's opening shot is improved.

**Token usage:** `font-display`, weight 700, new size, existing color (`text-text-primary` and the existing `gradient-tagline` span treatment — keep it in-app, it's the in-app landing's signature. Marketing loses the gradient; in-app keeps it.)

**Risk:** the gradient-tagline span currently spans "starting position." If we keep that, we maintain visual DNA between the in-app and marketing landing surfaces without the marketing surface copying the treatment verbatim. Deliberate asymmetry = deliberate hierarchy.

### 3.2 P0 Visual — Stage 2 Reveal Sequence Re-timing

**What:** DESIGN.md §Motion System → Key Animation Sequences describes the Stage 2 Reveal as:
1. Glow pulse (0.8s)
2. Bear reveal (delay 0.5s)
3. Pentagon draw (delay 1.0s)
4. Title reveal (delay 1.4s)
5. Stat numbers count up

If the video is going to land this beat at all — and it has to, it's the product's signature moment — the sequence needs a breath between beats 3 and 4. Right now it reads as a 1.4-second rapid-fire. The pentagon lands and the title is there before the student can register the pentagon has settled.

**Proposal:** Extend the sequence to 2.4 seconds:
1. Glow pulse (0.0s → 0.8s)
2. Bear reveal (delay 0.5s, duration 0.6s, `springs.bouncy`)
3. **Hold 0.4s** — new. Nothing moves. The bear sits. The ambient breathe continues. This is the "ownership" beat.
4. Pentagon draw (delay 1.5s, duration 0.6s, `springs.smooth`, axes stagger 100ms)
5. **Hold 0.3s** — new. Pentagon sits at rest.
6. Title reveal (delay 2.4s, duration 0.5s)
7. Stat numbers count up (delay 2.5s, duration 0.8s per number, stagger 80ms)

Total: 3.7s. Feels cinematic instead of rushed. The video cuts on beat 6 — the title — which is the strongest frame of the sequence.

**Leverage:** 1-hour change in `frontend/src/screens/RevealScreen.tsx` motion configs. Visible in every demo capture AND in the Kaggle cover screenshot (if we use the reveal frame there — see §4). Extremely high leverage.

**Token usage:** `springs.bouncy` for bear, `springs.smooth` for pentagon, existing delay system. Only thing extending is the *wait* between beats.

### 3.3 P1 Visual — Branch Tree Screen Composition

**What:** The Branch Tree is *the product*. DESIGN.md §Emotional Framework literally calls it "WONDER" in all caps. For the video and the landing-page Section C card, this screen needs to be captured in a specific state that maximizes the visual payoff.

**The current render** (per `BranchTreeScreen.tsx`) renders a root + up to 3 levels + stat deltas. Good. But the composition in screenshots is likely "tree on left, detail panel on right" — which is a dashboard frame, not a constellation frame.

**Proposal:** For demo capture (not a code change — a *capture* convention): the Branch Tree hero shot shows the detail panel closed, all branches lit, particle drift active, ambient glow alive. Frame it full-bleed, centered on the root career. Let the tree be the image. The detail-panel-open state is a secondary capture used later in the video, not the hero.

**Leverage:** 0 code. A capture rule. The ship plan's week-2 screenshot capture already exists — we just specify how.

### 3.4 Skip List — What's Not Worth the 4-Week Spend

Everything else. Specifically:

- **Boss fight transition polish** — the gauntlet already works. Any polish here is invisible outside actual gameplay. The video doesn't need more than the existing animations.
- **Onboarding micro-animations** — Profile, SchoolMajor, EffortLoans already animate per the existing motion system. Good enough.
- **Menu/Compare screen chrome** — not on the demo critical path.
- **Custom boss illustrations** — PRD §Does Not Ship. Don't go near.
- **New illustration work beyond the laptop in Section E** — cost/benefit fails.

**Hard rule:** if it's not visible in the 3-minute video OR in one of the 6-8 landing screenshots, it does not get design attention between 2026-04-17 and 2026-05-18.

---

## 4. Screenshots Strategy

Week 2 of the ship plan captures screenshots "against the voice-compliant app." The ship plan correctly gates this on the week-1 voice fixes. Here's the composition and selection plan for the **six hero shots** that power the landing page + Kaggle gallery + README + video thumbnails.

### 4.1 Composition Rules (Apply to Every Shot)

1. **Device chrome: none.** No browser bar, no phone bezel, no "device mockup." These scream hackathon. The app IS dark and plush already; framing it in a fake MacBook screen would dilute that.
2. **Aspect: 16:10 for landscape shots, 9:16 for portrait shots.** Matches the card aspect in landing Section C and the receipt panel in Section D.
3. **Corners: rounded.** Apply `rounded-xl` (20px) at capture or via post-processing. Echoes in-app card DNA.
4. **Border: 1px `border-subtle` (rgba 255,255,255,0.06).** Keeps the image from floating unanchored.
5. **Shadow: `shadow-lg` in post (0 8px 32px rgba(27, 29, 48, 0.7)).** Grounds the image.
6. **Resolution: capture at 2560×1600 (retina). Downsample to 1920×1200 for web.** Lighthouse-friendly, still pixel-perfect on 4K monitors.
7. **Cursor: not visible in hero shots.** The UI sells itself. Cursor appears only in video, not in stills.
8. **Glow preservation: do not crop tight.** The ambient glow and vertex halos extend 40-60px outside the ostensible "content." Crop with breathing room or lose the visual DNA.
9. **Browser: Chrome at 1440×900 minimum viewport.** Use DevTools device toolbar set to a clean 1440×900. No extensions visible.
10. **Seed data: deterministic.** Each shot uses a specific school+major so we can re-capture if needed. Listed below.

### 4.2 The Six Hero Shots

#### Shot 1 — The Reveal (pentagon + Gemma's Take)

**State:** Post-voice-fix `RevealScreen.tsx`. Stanford CS, All-in effort, 100% loans — the single highest-variance build for visual impact.

**Why Stanford CS:** the pentagon pops. ERN high (gold vertex bright), RES moderate (purple present), HMN lower (pink recedes). The asymmetry reads as "real data" — a balanced pentagon reads as fake.

**Capture state:** Tutorial dismissed (not showing "?"), Gemma's Take fully rendered, receipt panel closed, scroll position at top.

**Composition:** Frame the pentagon + the first paragraph of Gemma's Take. Crop below the first career card.

**Used for:** Landing Section C tile 1, Kaggle cover, video thumbnail, Wrapped share frame seed.

#### Shot 2 — The Gauntlet Mid-Reroll

**State:** `GauntletScreen.tsx` showing a LOSE boss fight with the RerollFlow panel open, one skill card already equipped (glowing).

**Why mid-reroll:** it's the product's most unique mechanic. Any screenshot of a boss in its default state reads like "generic RPG card." Mid-reroll shows the interaction state — the skill pool, the "rescore fight" button, the delta preview.

**Seed:** Illinois State Marketing, Fight AI fight (LOSE by default). Equip one skill (e.g., "Data analytics minor"). Let the stat delta render.

**Composition:** 16:10 landscape. Boss card centered, reroll panel visible to the right, skill card highlighted with `shadow-glow-thrive` active.

**Used for:** Landing Section C tile 2, video Scene 4, Kaggle gallery.

#### Shot 3 — The Branch Tree (15 Paths Lit)

**State:** `BranchTreeScreen.tsx` at full render — all branches drawn, endpoint silhouettes fading in, particle drift active, detail panel closed.

**Seed:** Indiana University Bloomington Marketing → a SOC with rich branches (Marketing Managers or similar). Per the reports directory, IUB Marketing already has report data we know works.

**Why this seed:** we need a tree with 10+ endpoints to make the "constellation" read. A spartan tree with 3 branches looks incomplete.

**Composition:** Full-viewport landscape, 16:10. Root node centered slightly left, branches radiating right. No sidebar, no chrome. The tree IS the image.

**Used for:** Landing Section C tile 3, **Kaggle cover B-side**, video Scene 6, README hero below the fold.

**This is the most important single screenshot on the entire submission.** Double the capture attempts. Try lights-on (all endpoints illuminated) AND lights-staggered (branches at 0.7s into the reveal animation, some endpoints still dark). The staggered state conveys motion even in a still.

#### Shot 4 — The Receipt Panel Expanded

**State:** `RevealScreen.tsx` or `CareerDetail.tsx` with a single stat (ROI) receipt panel expanded. Raw inputs visible. Source citation visible. Computation steps visible.

**Seed:** ISU Financial Analyst build.

**Why:** this is the visual proof for Section D. The "every number has a receipt" claim has to be backed by a shot of an actual receipt.

**Composition:** 9:16 portrait. The receipt panel IS the image. Minor context above (the stat name and current value). Everything below the panel cropped.

**Used for:** Landing Section D right column, Kaggle gallery.

#### Shot 5 — Wrapped Share Frame

**State:** `SaveWrappedScreen.tsx` rendering a single frame from the wrapped sequence. Specifically the **stats frame** (pentagon + "Strong build. Wins across every fight." verdict), not the title frame.

**Seed:** any completed build with a clean pentagon. Stanford CS or similar.

**Why:** the PRD's social loop bets on Wrapped. Landing doesn't link to Wrapped but a Wrapped frame in the Kaggle gallery demonstrates the share mechanic exists and is polished.

**Composition:** Native Wrapped aspect (likely 9:16 or 1:1 per the existing pipeline).

**Used for:** Kaggle gallery, social launch post.

#### Shot 6 — Compare View

**State:** `MenuScreen.tsx → CompareView.tsx` with two builds side-by-side: Stanford CS vs Millikin Drama.

**Why that pair:** the gap between these two is the equity spine made visible. Stanford CS pentagon is robust; Millikin Drama pentagon has real structural loss on Fight Student Loans. The contrast IS the product thesis.

**Composition:** 16:10 landscape. Two pentagons visible, Risk Headline Card showing where they disagree.

**Used for:** Kaggle writeup (equity spine illustration), NOT on landing (too much info for a landing card).

### 4.3 Landing Page Composition of Screenshots

How they're combined on the page:

- **Section C (cards)** — Shots 1, 2, 3 in 4:5 aspect ratio cards, evenly spaced, 3-up on desktop, stacked on mobile. Cropped to fit the 4:5 frame if needed.
- **Section D (receipts)** — Shot 4 in 9:16 portrait on right column. Glow behind.
- **Nowhere else.** Shots 5 and 6 are Kaggle/social/video only. The landing does not need a gallery page — that's hackathon-gallery-trope energy.

### 4.4 Alternative States — Don't Capture

Skip these. They're either not on the critical path or they risk looking hackathon-amateur:

- Loading states (already tested — don't need screenshots)
- Error states (same)
- Empty Menu screen (doesn't sell the product)
- Profile Screen (nothing visual sells here)
- SchoolSearch autocomplete (functional, not signature)

---

## 5. Visual Coherence Plan — Landing → App Transition

The judge's eye has to move from `futureproof.app` (landing) to the live app (whatever domain) without experiencing a stylistic seam. Here's how that happens.

### 5.1 Three Shared Visual Invariants

These MUST be identical between the two surfaces:

1. **Background color and gradient.** Both surfaces start at `bg-bp-void` (#12131F) with the identical layered radial gradient from DESIGN.md §Surface Treatments. No landing-specific gradient. Same CSS variable references.
2. **Typography stack.** Fredoka / Nunito / Space Mono. Same weights. Same Google Fonts import string.
3. **Primary CTA button DNA.** `accent-thrive` background, `text-inverse` text, `rounded-lg`, weight 700, Nunito. Only the size differs (marketing 56px height, in-app 48px height). The *color, radius, weight* are identical.

### 5.2 One Deliberate Difference

**Hero type scale.** Marketing hero is 96px. In-app landing hero is 48-64px (proposal above). The difference communicates surface role: a billboard vs. a doorway. This is the visual equivalent of the register shift in the voice guide between marketing and in-app copy.

### 5.3 The Transition Moment

When the visitor clicks "Start ✦" on the landing page:

**Option A (recommended):** the CTA click opens the live app in a new tab. Landing sits behind. No transition to engineer. Simple. Judge can A/B compare landing and app by tabbing.

**Option B:** same-tab navigation with a fade-through-black (600ms, `springs.gentle`). Higher effort, easy to get wrong.

**Recommendation: Option A for the demo.** The judge reads the landing, clicks, sees the app, comes back. No custom transition needed. This is a P2-cut we can afford.

### 5.4 Cross-Surface Signatures

Elements that SHOULD repeat — a judge crossing surfaces should recognize them:

| Element | Landing use | In-app use |
|---|---|---|
| Pentagon-Constellation | Hero visual | Reveal screen centerpiece, Compare screen, Menu build cards |
| Twinkling stars | Hero background | Every page's ambient layer |
| Ambient-breathe glow | Hero background | Every page |
| Receipt table pattern | Section G data table | In-app stat receipt panels |
| Space Mono data treatment | Data footers, Section D stat lines | Every stat value, every salary figure, every year count |
| `accent-thrive` green | One button on the page (`Start ✦`) | WIN pill, ROI stat, primary CTAs throughout |
| Section label pattern (`font-data` 11px, 2px tracking, uppercase, `accent-info`) | Section C card labels | Every in-app section header |

### 5.5 The "Judge's Eye" Test

A judge opens landing, reads for 20 seconds, clicks Start, sees the in-app Landing. They should be unable to tell me where the marketing surface ends and the product surface begins — *except* via typographic scale (the marketing is the billboard). That is the coherence target.

---

## 6. Hackathon Visual Risk Anti-Patterns

The most dangerous outcome isn't a bad submission — it's a submission that looks like every other submission. These are the tropes to actively refuse.

### 6.1 Named Anti-Patterns (Do Not Do)

| Trope | Why it kills us | Alternative |
|---|---|---|
| Stock photo of diverse students on laptops | Signals "generic edtech startup pitch." Judges have seen it 500 times. | No students. Plush bear in-app. Pentagon constellation on landing. |
| Purple-to-pink neon gradient on hero | The default Unsplash hackathon aesthetic. | Dark indigo + warm whites + single-hue accent glows. |
| Generic "fintech pentagon" (thin lines, minimal fill, crisp edges) | Reads as Bloomberg Terminal tile. Cold. | Our pentagon has soft radial fills, glow halos, floating particles, stat-colored vertices — it's a constellation, not a chart. |
| "Watch the magic happen" animated hero | Over-promises, motion-over-substance. | Still hero + one subtle 7s drift + existing twinkle field. Motion earns its place via the internal Stage 2 Reveal inside the app. |
| AI-generated illustration of a student graduating | Recognizable AI-illustration tell, undermines a "powered by AI" pitch. | Only the plush laptop in Section E is new illustration work. Everything else is UI screenshots or typography. |
| Long "how it works" infographic with numbered steps and arrows | Pitch-deck energy. | Three cards in Section C. That's the infographic. |
| "Join 10,000 students" social-proof counter | We haven't launched. | We have 700K rows of public data. That's the proof. |
| Founder headshot wall / "Meet the team" | N/A for one-builder submission. | Single paragraph in Section H. No photo. |
| Animated SVG line drawings of laptops/graduation caps | Looks like a Canva template. | One plush-style laptop in Section E. Done. |
| "Powered by" logo band (OpenAI, Stripe, etc.) | Hackathon trope that dilutes. We're powered by Gemma and Ollama — that lives in Section E. | Section E does the work. No logo band. |
| Scroll-jacked parallax | Adds complexity, breaks accessibility, reads as "we wanted to be fancy." | Natural scroll. `whileInView` triggers. Spring physics on reveals. |
| Confetti / particle burst on CTA hover | Infantilizing (voice guide anti-pattern applied to motion). | Hover = `shadow-glow-thrive` pulse. Matter-of-fact. |
| Large dollar-sign iconography | "Make money with your degree" pitch. | ROI is an acronym on the pentagon. Salaries are Space Mono numbers in the body. |
| "Get started in 60 seconds" countdown timer | Fake urgency — voice guide anti-pattern. | "Takes about two minutes." Stated once, accurately. |
| ALL CAPS SECTION HEADLINES | Voice guide anti-pattern. | Fredoka 700 at 40-96px is emphasis enough. |
| Emoji as section markers ("💡 How It Works") | Edtech trope. | `font-data` section labels: "HOW IT WORKS". |
| "As seen in" press logos fake / real | We're not seen anywhere yet. Don't pretend. | — |

### 6.2 The Meta-Rule

If a submission could be swapped for another Gemma 4 Good submission by changing the logo and the headline, it failed. Every pixel of FutureProof should be *illegible* outside the Brightpath system. A judge who's seen 30 submissions should recognize ours as *specifically* ours from a thumbnail.

**Test:** if we posted the hero image with no logo, would someone who used the app recognize it? If the pentagon-constellation + indigo + Fredoka hero tagline is ours, unrecognizable anywhere else, we win. If it looks like any other "AI-powered career planner" submission, we lose the format war.

---

## 7. Extensions Flagged (Not in DESIGN.md Yet)

Three items in this vision extend the current system. Listing them explicitly so the design auditor knows what to whitelist and what to update DESIGN.md with after the hackathon.

### 7.1 Marketing-Hero Type Scale

| Token | Value | Purpose |
|---|---|---|
| `text-marketing-hero` | 96px desktop / 72px tablet / 48px mobile, Fredoka 700, line-height 1.05, letter-spacing -0.02em | Landing page hero headline only |
| `text-marketing-section` | 64px desktop / 56px tablet / 40px mobile, Fredoka 700, line-height 1.15, letter-spacing -0.01em | Landing section headlines (B, others can use existing `text-title` at 40px) |

**Not used in-app.** In-app max stays at `text-hero` (48px).

**Why extension not in core:** DESIGN.md is in-app-first. Marketing is a secondary surface with different rules. Post-hackathon, fold these in under a new "Marketing Surface Tokens" section.

### 7.2 Removed In-App Treatment: `gradient-tagline` on Marketing

The in-app landing headline uses a `gradient-tagline` span (from `index.css`). The marketing landing deliberately does NOT use this treatment. Reason: a gradient headline at 96px reads as noisy; at 48px (in-app) it reads as warm. Size changes what a gradient does.

This is a rule to document, not a new token.

### 7.3 New Illustration Asset: Plush Laptop

One new asset: a plush-style rendered laptop with the pentagon constellation visible on-screen. Matches `DESIGN.md §Illustration Style` — matte fabric, soft studio lighting, dark navy background, button eyes not applicable (no character).

**Effort estimate:** 2-4 hours in Figma or a similar tool by someone who can draw a plush laptop. If nobody on the team can, fallback to a cleanly-rendered dark-UI laptop illustration from a stock illustration library that matches the palette — but I'd rather skip the section's right-column illustration entirely and extend the terminal screenshot full-width than ship an off-brand asset.

**Fallback decision:** if the plush laptop isn't achievable in <4 hours, **extend the terminal to span the right column** and drop the laptop. Section E reads fine with just terminal + text.

---

## 8. 4-Week Design Punch List — Calendar Slot

Merged with the ship plan's week structure. **Design items only** — the ship plan's voice/writeup/video items sit alongside, not replaced.

### Week 1 (2026-04-20 → 2026-04-26) — Foundation

| Item | Effort | Owner | Slot |
|---|---|---|---|
| Ratify this design vision with the human builder | 1 hour | Jeff | Mon |
| In-app LandingScreen headline size bump (§3.1) | 0.5 hour | Claude Code | Mon |
| Stage 2 Reveal motion re-timing (§3.2) | 1 hour | Claude Code | Tue |
| Design review: verify both above land cleanly pre-screenshot-capture | 0.5 hour | fp-design-visionary (me) | Wed |
| Build Section A hero component (landing) + PentagonGlow reuse validation | 1 day | Jeff + frontend dev | Wed-Thu |
| Verify `prefers-reduced-motion` across all new landing animations | 1 hour | Claude Code | Fri |

**Week 1 design deliverable:** landing page hero section rendered in a staging branch. Pentagon, headline, CTA all working. Responsive.

### Week 2 (2026-04-27 → 2026-05-03) — Screenshots + Middle Sections

| Item | Effort | Owner | Slot |
|---|---|---|---|
| Build Sections B-F of landing page (typography, card grid, split layout, Ollama, CTA) | 2.5 days | Jeff + frontend dev | Mon-Wed |
| Capture Shot 1 (Reveal) per §4 | 0.5 hour | Jeff | Wed (post-voice-fix) |
| Capture Shot 2 (Gauntlet reroll) per §4 | 0.5 hour | Jeff | Wed |
| Capture Shot 3 (Branch Tree — the important one; 2-3 attempts) | 1 hour | Jeff | Thu |
| Capture Shot 4 (Receipt panel) per §4 | 0.5 hour | Jeff | Thu |
| Capture Shot 5 (Wrapped frame) per §4 | 0.5 hour | Jeff | Fri |
| Capture Shot 6 (Compare view) per §4 | 0.5 hour | Jeff | Fri |
| Plush laptop illustration OR fallback decision per §7.3 | 2-4 hours | Jeff + design | Thu |
| Kaggle cover image composition (reusing hero + Shot 3 branch tree as alternate) | 2 hours | Jeff + design | Fri |

**Week 2 design deliverable:** complete landing page on staging, all 6 screenshots captured, Kaggle cover ready.

### Week 3 (2026-05-04 → 2026-05-10) — Polish + Sections G-I

| Item | Effort | Owner | Slot |
|---|---|---|---|
| Build Sections G (data table), H (team), I (footer) | 0.5 day | Jeff + frontend dev | Mon |
| Design review pass: full page on staging, desktop + mobile | 1 hour | fp-design-visionary | Tue |
| Fix design-review findings (expected: minor — spacing, border alignment, motion timing) | 0.5 day | frontend dev | Tue-Wed |
| Lighthouse pass — target 95+ on Performance, Accessibility, Best Practices, SEO | 0.5 day | Jeff | Wed |
| fp-design-auditor mechanical compliance review against DESIGN.md | 0.5 day | fp-design-auditor | Thu |
| Fix any mechanical compliance findings (missing tokens, hardcoded colors, etc.) | 0.5 day | Claude Code | Thu-Fri |
| Video thumbnail design (uses Shot 3 Branch Tree + minimal typography) | 1 hour | Jeff + design | Fri |

**Week 3 design deliverable:** landing page production-ready, Lighthouse passed, design-audit passed.

### Week 4 (2026-05-11 → 2026-05-18) — Submission Buffer

| Item | Effort | Owner | Slot |
|---|---|---|---|
| Final landing page QA on production domain | 1 hour | Jeff | Mon |
| Cross-browser check: Chrome, Safari, Firefox, mobile Safari/Chrome | 1 hour | Jeff | Mon |
| Social launch card graphics (Twitter, LinkedIn, Bluesky) — reuse Shot 1 or Shot 3 with tagline overlay | 1 hour | Jeff + design | Tue |
| Final video thumbnail / poster frame | 0.5 hour | Jeff | Wed |
| **Design buffer** — catch anything that broke | 1 day | fp-design-visionary | Thu-Fri |

**Week 4 design deliverable:** nothing new. Polish only.

---

## 9. Risks I'm Flagging

1. **The plush laptop asset is the only real new illustration work.** If nobody can deliver it in 4 hours, §7.3 has a fallback. But be honest in week 1: decide plush-laptop-or-fallback Monday week 2. Don't let it slip.

2. **Screenshot capture depends on voice fixes landing.** Per the ship plan, this is already called out. I'm echoing: if Gemma prompts aren't rewritten by end of week 1, the week-2 screenshot pass captures wrong-voice copy and has to be re-shot. Treat the Friday week 1 gauntlet playthrough as a **capture blocker check** — not just a voice check.

3. **Hero constellation motion might feel underwhelming on first paint.** The PentagonGlow component's internal animations take 4-7 seconds to fully cycle. A judge in scrub mode might see a "static hero." The 7s vertical drift I specified helps. If it still feels dead, add ONE more subtle thing: 2-3 extra particles that drift into the pentagon frame from outside the viewport. Don't add rotation, don't add pulse, don't add zoom. Particles only.

4. **Desktop-vs-mobile divergence on the landing page.** Mobile has to work. Judges may check on a phone. The type scales drop cleanly; the 3-up card grid stacks; the split Section D stacks. Test each in Chrome DevTools device toolbar before shipping. Do NOT design mobile as an afterthought — design auditor will catch that.

5. **Section E terminal animation could look hokey.** If the typing animation reads as "corporate AI demo," kill it. The static terminal is stronger than a bad typing effect. Fallback: just show the completed state with a subtle blinking cursor at the end.

6. **The branch tree hero shot is load-bearing for the entire submission.** If we can't capture one that reads as "constellation, not graph," the Section C card grid loses its payoff and the video's climax weakens. Allocate 2-3 captures across different seed data if the first attempt doesn't land.

---

## 10. One-Sentence Summary

The landing page is the in-app night sky zoomed out, built from components that already exist in `frontend/src/`, and the product's premium feel comes from ruthless restraint — one metaphor, five stats, five bosses, seven datasets, zero hackathon tropes.

---

*End of design vision.*
