# Landing Visual Critique — 2026-04-18

**Reviewer:** @fp-design-visionary (review mode)
**Surface:** http://localhost:5174/ — production build of `docs/specs/landing-page-and-design-polish.md`
**Feedback that triggered this review:** "pretty ugly, looks amateurish, can be vastly improved."

---

## Verdict: POLISH THE VISION

The direction is right. The execution is under-ambitious in three specific ways and over-literal in a fourth. Fix the pentagon scale, fix the hero type clamp, fix the screenshot-pending fallback, and differentiate the nine sections so they stop reading as a WordPress template. That's a two-day polish pass, not a rebuild.

If only one thing gets done this week: **fix the screenshot-pending fallback.** That single issue is responsible for ~60% of the "empty/amateurish" feel because six of the nine sections currently render as near-void rectangles until the screenshot capture lands.

---

## §1. The honest diagnosis

Open the page. What does a judge actually see?

**At 1440×900 (above the fold)** — `/tmp/landing-review/desktop-fold.png`. A 320px pentagon drifting in a huge dark void. Beneath it, a four-line wordmark (`A college degree isn't / a destination. / It's a starting / position.`) because the 96px hero clamp forces the line to break at "destination" on a 900px-max headline in a 1440 viewport. Small green "Start" pill. Data footer in a micro-font at 45% opacity that reads as noise. There is no secondary demo link, even though the spec ratified one — it got dropped silently. The pentagon is small enough that it reads as a decorative favicon, not a hero. **This fold does not look like a launch; it looks like a teaser for something that hasn't been finished.**

**Scroll to the second section (Problem)** — `/tmp/landing-review/sec-landing-section-problem.png`. This is actually fine. Typographic receipts hit — `82% exposed to AI` in insight-purple, `$400/hour counselor` in alert-amber both show up and land. **This section is the strongest on the page.**

**How It Works** — `/tmp/landing-review/sec-landing-section-how.png`. Three identical cards, each containing a huge empty `bg-bp-surface` rectangle labelled `SCREENSHOT PENDING CAPTURE` in 11px Space Mono at 60% opacity. The actual copy (STATS / GAUNTLET / BRANCHES) is strong, but the card composition is 60% empty skeleton. **This section will look fine after Shots 1–3 land, but in the meantime it is the second-worst section on the page and there is no design treatment preventing it from looking broken.**

**Receipts** — `/tmp/landing-review/sec-landing-section-receipts.png`. Left column has the four-line receipt stack in stat colors — that part works. Right column is a huge 9:16 portrait rectangle of `SCREENSHOT PENDING CAPTURE`. The `shadow-glow-insight` that was supposed to sit behind it is either invisible or getting clipped by the `-z-10` + rounded mask. **The whole right half reads as empty. The receipt stat-colors look lonely without a visual anchor opposite.**

**Ollama** — `/tmp/landing-review/sec-landing-section-ollama.png`. This is genuinely strong. The terminal SVG with the green prompts and ready-at-:5173 line has the only piece of earned texture on the entire page. But it is surrounded by empty dark space — there is no `desktop-ambient-glow-thrive` behind it, no scanline, no laptop illustration (the probe fails — `plush-laptop.svg` never got made, so the layout falls back to `col-span-8` and the right third of the section is empty). **This section is the highest-craft thing on the page but it's sitting in a blank room.**

**CTA Rail** — `/tmp/landing-review/sec-landing-section-cta-rail.png`. A 40px headline, a subhead, and the same Start button from the hero. **Zero visual reward for the scroll.** No constellation callback, no receipt callback, no stat-color echo. This is the conversion moment and it has nothing to make the scroll feel earned.

**Data Sources** — `/tmp/landing-review/sec-landing-section-data.png`. Seven-row dataset table styled as a receipt. Competent. The column alignment is weak on desktop — "Rows" center-crushes between Source and Powers because of the `grid-cols-[2fr_auto_1.2fr]` weighting. The `hover:border-l-accent-insight` exists but the rows have no persistent stat-color mark, so at rest every row looks identical. **Acceptable but not memorable.**

**Team** — `/tmp/landing-review/sec-landing-section-team.png`. One centered paragraph. Restraint is the register. **Fine. Leave it.**

**Footer** — `/tmp/landing-review/sec-landing-footer.png`. One link, two disclaimer lines, one data line. Correct per the staff-engineer scope reduction. **Fine. Leave it.**

**Severity ranking** (worst offender first):
1. **Hero** — the signature moment is visually underweight; pentagon too small, headline mis-clamped, demo link missing.
2. **Receipts section right column** — hero screenshot slot empty, insight glow invisible.
3. **How It Works cards** — 3× empty skeleton dominates.
4. **Ollama section** — strong centerpiece, zero atmosphere around it.
5. **CTA Rail** — zero visual earned.
6. **Data Sources** — competent, not memorable.
7. **Problem, Team, Footer** — fine as shipped.

Secondary structural problem: every section uses `border-t border-border-subtle py-16 tablet:py-20 desktop:py-32`. Nine sections, nine identical boundaries, nine identical rhythms. The page reads as a scroll of equal-weight slabs, and that is the single biggest reason it *feels* amateurish even when individual moments are competent.

---

## §2. Root causes

**The vision was under-ambitious in three specific places:**

1. **The screenshot-pending state was never designed.** My §3 ratified `<ScreenshotWithFallback>` rendering `bg-bp-surface` with a "pending capture" label. That is what ships if screenshots are late. It should have been a first-class surface treatment — a stat-constellation placeholder, an animated receipt mockup, anything with craft. Shipping skeletons in six of nine sections is a choice. I did not design that choice.
2. **Section rhythm was ratified as "all identical, for continuity."** The rulebook (spec §3.3) explicitly made every section use the same border + padding. I wrote that rule. That rule produced a WordPress-template scroll. Continuity should come from palette and type, not from every boundary being a carbon copy.
3. **The atmospheric layer stopped at the hero.** Hero gets ambient glow + twinkle field + pentagon drift. Every other section gets flat void. I ratified section-specific atmosphere as "scope creep" — it is not, it is the thing that separates a planetarium from a slideshow.

**The implementation translated the wireframe literally in a fourth place:**

4. **ASCII wireframes encode layout, not atmosphere.** The implementation matches my wireframes to the pixel. The receipts-section right-column screenshot is exactly a rectangle because the wireframe said `[Expanded receipt panel screenshot]` inside a box. The glow I described in the token table (`Absolute-positioned shadow-glow-insight radial blur, -z-10, offset behind screenshot`) shipped as `absolute inset-0 -z-10 shadow-glow-insight rounded-xl blur-xl opacity-60` — which with rounded-xl and blur-xl blends into the background because the glow is sitting *inside* the same bounding rect as the screenshot. The spec didn't say "the glow should visibly extend 80–120px beyond the screenshot edges." So it doesn't.

**Where each root cause applies:**

- Hero: cause 1 (pentagon should have been 420–480px, not 320 — the spec clamped it small to match the hero constellation in-app) + cause 4 (wireframe drew a small pentagon, implementation shipped a small pentagon).
- How It Works: cause 1 (placeholder state) + cause 3 (three cards on a flat void plane — no card-level atmosphere).
- Receipts: cause 1 + cause 4 (glow bounding rect).
- Ollama: cause 3 (no atmospheric anchor around the terminal).
- CTA Rail: cause 2 (identical section shell, nothing earned) + cause 3 (no callback visual).
- Data Sources: cause 2 (identical shell).

---

## §3. The improvement plan

Twenty-three specific changes, covering all nine sections. Effort in hours. Priority: P0 = must fix before next external demo; P1 = should fix this week; P2 = polish.

### Hero (Section A)

1. **Location:** `HeroSection.tsx:40` (`<PentagonGlow size={320} />`)
   **Current:** 320px pentagon centered in a viewport that is 900px tall minus 128px of vertical padding = ~770px of canvas. The pentagon occupies ~41% of the canvas height and ~22% of the viewport width at 1440px.
   **Target:** `size={440}` on desktop, `size={360}` on tablet, `size={300}` on mobile. Pass as a responsive prop or compute from a `useMediaQuery`. On desktop the pentagon should occupy ~55–60% of the vertical canvas and feel like a planetarium centerpiece, not a logomark.
   **Why:** The pentagon is the product's signature visual. At 320px it reads as decoration. At 440px it reads as arrival.
   **Effort:** S (1h) — the component already takes `size`; needs a responsive wrapper.
   **Priority:** P0.

2. **Location:** `HeroSection.tsx:44` (`text-hero tablet:text-marketing-section desktop:text-marketing-hero`)
   **Current:** On 1440×900, the 96px desktop clamp on a `max-w-[900px]` container breaks "A college degree isn't a destination." onto two lines with an awkward `isn't\na destination.` split. Four total lines of hero text is too many.
   **Target:** Either (a) bump max-w to `max-w-[1040px]` so each sentence fits on one line at 96px, or (b) drop desktop clamp to 80px (`text-marketing-section` desktop = 64px is too small for the hero) with `max-w-[960px]`. I recommend (b) + a `tracking-[-0.025em]` tightening to preserve the billboard read. Each sentence on one line; two lines total.
   **Why:** Three- or four-line headlines dilute the punch. Two lines maximum on the hero.
   **Effort:** XS (15min).
   **Priority:** P0.

3. **Location:** `HeroSection.tsx:63-72` (the CTA row)
   **Current:** One button, no secondary. Spec §3.4 ratified "Watch the 3-min demo →" as a secondary link inline with the CTA, `gap-6`.
   **Target:** Re-add the secondary link exactly as spec'd, even if it points to `#` with an `aria-disabled` state until the demo video exists. Today it's `Start ✦` alone, which looks like a two-thirds-finished hero.
   **Why:** The single-button hero reads as "MVP placeholder." The button + demo-link pairing is a well-established marketing hero pattern and the spec called for it.
   **Effort:** XS (20min).
   **Priority:** P0.

4. **Location:** `HeroSection.tsx:68` (CTA content `Start <span className="opacity-70">✦</span>`)
   **Current:** The `✦` is a Unicode character rendered as part of the button label. It's a char, not a glyph — different systems render it differently; on macOS Chrome it renders as a thin outlined star that looks almost like an asterisk.
   **Target:** Replace with an inline SVG sparkle (4-point + cross-hair construction) matching the Brightpath illustration style. 16px, 0.7 opacity. Or — and I think this is better — drop the sparkle entirely on the hero and add it only on the CTA Rail button so the second button has a tiny visual differentiator (see #17).
   **Why:** Text-character icons in button labels is a hackathon tell. The current glyph looks slightly broken on 1440px Chrome.
   **Effort:** XS (30min).
   **Priority:** P1.

5. **Location:** `HeroSection.tsx:22-26` (the `<section>` container — no ambient stars visible in shipped build)
   **Current:** The rulebook promises ~40 twinkling stars at 2px with `twinkle` animation. The shipped hero has none visible in any screenshot. Either the `.star` CSS class is not wired, or no `<span class="star">` elements are being injected.
   **Target:** Verify that the global `.ambient-glow` and twinkle field from `index.css` actually render on this route. If `Landing.tsx` is mounted without the ambient layer, inject it: a `<StarField count={42} />` component that renders absolutely-positioned dots with randomized `top/left` in the hero section. Only in the hero — not every section (see #13 for why).
   **Why:** The planetarium promise is that the dark isn't empty. Without stars it's just black.
   **Effort:** S (2h) — component + randomization + a few viewport pins.
   **Priority:** P0.

6. **Location:** `HeroSection.tsx:74-81` (data footer)
   **Current:** `opacity-45` on `text-micro text-text-muted` with `tracking-widest`. On a dark indigo background this is almost unreadable. It reads as noise, not credibility.
   **Target:** Bump to `opacity-70`, and replace the em-dash separators (`·`) with stat-colored dots — one `text-accent-thrive` dot between `700K rows` and `280 DQ rules`, one `text-accent-insight` dot between `280 DQ rules` and `7 public datasets`. Tiny, but it makes the line look *earned* instead of boilerplate.
   **Why:** Receipts are the voice of the product. A receipt you can't read isn't a receipt.
   **Effort:** XS (15min).
   **Priority:** P1.

### Problem (Section B)

7. **Location:** `ProblemSection.tsx:30` (`text-heading tablet:text-title desktop:text-marketing-section`)
   **Current:** 64px desktop is correct per spec, but mobile clamp to `text-heading` = 28px is too small. On a 375×667 mobile the headline is dwarfed by the three paragraphs below it.
   **Target:** Mobile clamp at `text-title` (40px) with `leading-[1.1]`. Tablet stays 40–56px. Desktop stays 64.
   **Why:** The rule I put in the visionary report was "a 56px headline on black is the image." On mobile 28px is not an image, it's a subtitle.
   **Effort:** XS (5min).
   **Priority:** P1.

8. **Location:** `ProblemSection.tsx:36` (`mt-10 tablet:mt-14 space-y-7`)
   **Current:** Paragraphs use `space-y-7` (28px). The spec ratified 28px gap which is correct, but the paragraphs lack any visual rhythm — all three paragraphs look like a wall.
   **Target:** Add a 1px `border-l border-border-subtle pl-6` treatment to the middle paragraph only ("Your guidance counselor has 400 other students..."), so the three-paragraph structure reads as **fact / observation / fact**. Or drop a 24px stat-insight-colored left-border on paragraph 1 where the inline receipt lives, and the same alert-amber border on paragraph 3 where the dollar receipt lives. Paragraph 2 stays neutral.
   **Why:** The section is already the strongest on the page. This is the polish move that turns "strong" into "memorable."
   **Effort:** S (30min).
   **Priority:** P2.

### How It Works (Section C)

9. **Location:** `HowItWorksSection.tsx:88` (card className)
   **Current:** All three cards use identical tokens. Same border, same background, same shadow, same hover.
   **Target:** Give each card a stat-colored accent stripe. Card 1 (STATS) gets a 3px left border in `border-accent-thrive` or an inner top-right accent glow in `shadow-glow-thrive`. Card 2 (GAUNTLET) gets `shadow-glow-alert` (loans-amber is the most iconic boss color). Card 3 (BRANCHES) gets `shadow-glow-insight`. Apply the glow on hover only, or at 40% opacity resting and 100% on hover. The cards already represent three different game mechanics — the visual should echo that.
   **Why:** Three identical cards + three identical screenshots (once captured) + three identical hover elevations = one beat. Differentiating them turns the section into three distinct beats — which is exactly the "three things happen" narrative.
   **Effort:** S (1h).
   **Priority:** P1.

10. **Location:** `ScreenshotWithFallback.tsx:24-37` (the placeholder component)
    **Current:** When the image fails to load, the fallback is a `bg-bp-surface` rectangle with `SCREENSHOT PENDING CAPTURE` in 60% opacity micro-text. This is visible on six sections of the page right now. It looks amateurish because it is a literal "TODO" rectangle.
    **Target:** Replace the fallback with a first-class loading treatment that actually looks like something. Three options, in order of effort:
      - **XS:** Make the fallback a gradient matching the section's tone — card 1 with a thrive-tinted radial gradient, card 2 alert, card 3 insight — plus a centered 48px pentagon skeleton. No text. Reads as "loading," not "TODO."
      - **S:** Render a low-fidelity SVG wireframe of what the screenshot will contain: a pentagon outline for the reveal shot, a boss silhouette for the gauntlet, a branch-tree silhouette for branches.
      - **M:** Generate the screenshots now via Playwright (the capture target exists per the in-app screens), even if final polish comes later. Ship *some* image.
    **Why:** This is the single biggest visual problem on the page. Six sections currently render as empty slabs because of this one component.
    **Effort:** XS (1h) to S (3h) to M (6h).
    **Priority:** P0. The XS fix is a three-hour polish that unblocks the entire page.

11. **Location:** `HowItWorksSection.tsx:85-105` (card reveal)
    **Current:** Cards scale from 0.95 to 1 with `stagger.slow` between them. The scale delta is so small (5%) that it's imperceptible.
    **Target:** Scale from 0.88, y:24, opacity 0 with `springs.bouncy` (not `.smooth`) and stagger at `stagger.slow` (100ms) — the spring overshoot makes the cards feel like they *land*. `.smooth` with 5% scale = a glorified fade-in.
    **Why:** The spec said "scaleIn" and the implementation shipped what amounts to a fade. The overshoot is what sells the "you see / you fight / you see" spine.
    **Effort:** XS (10min — swap spring preset + increase scale delta).
    **Priority:** P1.

### Receipts (Section D)

12. **Location:** `ReceiptsSection.tsx:100-114` (the glow + screenshot)
    **Current:**
    ```tsx
    <div className="absolute inset-0 -z-10 shadow-glow-insight rounded-xl blur-xl opacity-60" />
    ```
    The glow div sits *inside* the same bounding rect as the screenshot and gets clipped by the parent. `shadow-glow-insight` is `0 0 20px rgba(184, 169, 232, 0.3)` — 20px spread is too tight for a hero illumination moment, and it's being blurred again by `blur-xl` which turns a sharp glow into a fog.
    **Target:** Replace with a proper atmospheric glow. The screenshot gets no inside glow; instead, place a `::before` or sibling `<div>` that's `absolute -inset-12 bg-[radial-gradient(ellipse_at_center,rgba(184,169,232,0.35)_0%,transparent_65%)] blur-3xl -z-10`. The glow extends 48px beyond all four sides of the screenshot. This is the "this is data/intelligence" glow I wrote in the original vision — the shipped version is invisible because it's inside the box.
    **Why:** The receipts section is the proof moment. The glow is the thing that makes the screenshot *feel* like proof, not a product shot. Right now the glow might as well not exist.
    **Effort:** XS (20min).
    **Priority:** P0.

13. **Location:** `ReceiptsSection.tsx:80-90` (the four stat-color lines)
    **Current:** Four lines in `text-data-lg` (24px), stat colors, staggered at 100ms. This part is fine.
    **Target:** Add a tiny 6px dot before each line in the same stat color, `vertical-align: middle`, with `animate-pulse` on `animation-delay: ${i * 100}ms` matching the reveal stagger. The dot is the visual echo of the pentagon vertex dots. Same visual DNA as the hero, reused here.
    **Why:** The vertex dots are the product's visual signature. Reusing them here as a list-mark calls back to the hero and ties the sections together.
    **Effort:** XS (15min).
    **Priority:** P2.

### Ollama (Section E)

14. **Location:** `OllamaSection.tsx:54-57` (section shell)
    **Current:** Flat `border-t border-border-subtle` boundary. Terminal sits on the same flat dark plane as everything else.
    **Target:** Add a vignette / scanline ambient layer on this section only. A `::before` pseudo-element with `background: repeating-linear-gradient(transparent, transparent 3px, rgba(125, 212, 163, 0.015) 3px, rgba(125, 212, 163, 0.015) 4px)` and `pointer-events: none` absolutely positioned over the section at z-index behind content. Extremely subtle (1.5% opacity). Reads as "this is the terminal environment," not "this is a paragraph with a code block."
    **Why:** The Ollama section is the track-specific credibility moment and it's sitting in a blank room. The scanline atmosphere turns the whole section into "the local-inference environment" instead of "section five of the marketing page."
    **Effort:** S (45min).
    **Priority:** P0 for the Ollama track submission video composition.

15. **Location:** `OllamaSection.tsx:95-108` (the laptop illustration probe)
    **Current:** The probe for `plush-laptop.svg` fails (asset was never produced). Layout falls back to `col-span-8` for the terminal, and the right third of the section is empty.
    **Target:** Either (a) produce the plush laptop SVG this week — it's explicitly called out as new illustration work in §7.3 of the design-vision report and it's the only bespoke illustration on the landing, or (b) if the asset isn't going to ship in time, replace the laptop slot with a secondary visual that earns its space: a floating "works on M1/M2/M3, 8GB RAM" spec callout in a receipt style (`font-data text-data text-text-secondary` with stat-color dividers). Do NOT ship the empty third.
    **Why:** The spec set up a three-column layout and the third column doesn't render. That's a composition failure that reads as "we ran out of time." Either ship the asset or replace the slot.
    **Effort:** M (4–6h for the SVG) or S (45min for the spec callout fallback).
    **Priority:** P0.

16. **Location:** `TerminalSVG.tsx:11-16` (terminal container)
    **Current:** `shadow-glow-thrive` is applied to a `bg-bp-void` figure. This works. But the terminal border is `border-border` (rgba 255/255/255/0.1) which reads as generic.
    **Target:** Change the terminal border to `border-accent-thrive/30` (30% alpha thrive) — the only terminal on the page, it deserves the green edge. And add an inner `shadow-[inset_0_1px_0_rgba(125,212,163,0.2)]` on the top edge so the terminal has a subtle beveled feel, like it's a real inset panel.
    **Why:** Micro-detail, but the terminal is the section's centerpiece. Every tiny bit of material treatment on it pays off.
    **Effort:** XS (10min).
    **Priority:** P2.

### CTA Rail (Section F)

17. **Location:** `CTARailSection.tsx:31-62` (entire section)
    **Current:** Headline, subhead, button. Identical button to the hero. The section offers no visual reward.
    **Target:** Three moves:
      1. Add a miniature pentagon constellation (PentagonGlow at `size={160}`) positioned absolutely behind the section, offset 20% right, opacity 0.3, no ambient drift — a ghost-echo of the hero.
      2. Change the button label to `Start your build ✦` (slightly longer than the hero, differentiated) to signal "this is the second invitation, not the first."
      3. Add a 1px horizontal rule of stat-color dots above the headline — five dots in the five stat colors, `gap-4`, at `opacity-60`. The rule reads as a mini-pentagon laid flat.
    **Why:** This is the conversion moment. Right now the only visual difference between CTA Rail and the hero is that there's less of it. A second encounter with the signature visual + a differentiated button label = "you've been somewhere."
    **Effort:** S (1h).
    **Priority:** P0.

### Data Sources (Section G)

18. **Location:** `DataSourcesSection.tsx:125` (header row grid template)
    **Current:** `grid-cols-[1fr_auto_1fr] tablet:grid-cols-[2fr_auto_1.2fr]`. The "Rows" column auto-widths and gets crushed between two equally weighted columns.
    **Target:** `grid-cols-[2.2fr_1fr_1.6fr]` on desktop. Gives Source 42%, Rows 19%, Powers 39%. The Rows column gets real real estate so `626,406` doesn't look squeezed against its neighbors.
    **Why:** The rows (the numbers) are the proof. They should be visually weighty.
    **Effort:** XS (5min).
    **Priority:** P1.

19. **Location:** `DataSourcesSection.tsx:139` (dataset row hover)
    **Current:** `border-l-[3px] border-transparent ... hover:border-l-accent-insight`. All rows have an invisible 3px reserved border. At rest, all rows look identical.
    **Target:** Give each row a persistent 3px left border in its *powered stat's* accent color at 40% opacity. Scorecard → `accent-thrive/40` (ERN/ROI are thrive + caution), Karpathy → `accent-insight/40` (RES), BLS → `accent-info/40` (GRW), O*NET → `accent-empathy/40` (HMN), BEA → `accent-caution/40`. Hover brightens to 100%. The table at rest reads as a stat-color legend mapped to datasets — the schema in visual form.
    **Why:** Right now the table is inert. With persistent stat colors, the table becomes a visual key that ties back to the pentagon.
    **Effort:** S (30min — needs a tiny row → color mapping function).
    **Priority:** P1.

20. **Location:** `DataSourcesSection.tsx:165-173` (footnote)
    **Current:** `font-body text-small text-text-muted italic` in `max-w-[720px]` below the table. The Gemma 4 blurb reads as a disclaimer footnote.
    **Target:** Promote this to a pull-line above or beside the table: `font-data text-small text-accent-insight` in a dedicated `border-l border-accent-insight/40 pl-4` block. This is where Gemma earns its on-page presence on the Ollama track — don't bury it.
    **Why:** The Gemma-vs-Karpathy differential is a real insight. Buried footnote = the judge misses it.
    **Effort:** XS (15min).
    **Priority:** P1.

### Team (Section H)

21. **Location:** `TeamSection.tsx:27-52` (entire section)
    **Current:** Centered paragraph, `max-w-[640px]`. The Brightsmith link is the only interactive element. Restraint is the register. This is fine but forgettable.
    **Target:** Keep the restraint. One addition: put a tiny `font-data text-micro text-text-muted tracking-widest uppercase` line above the headline — `BUILT FOR GEMMA 4 GOOD · HACKATHON · 2026`. Reads as a section label per the Section Labels component in DESIGN.md §Components. Ties the team section to the hackathon context explicitly, which is the only credibility move this section needs.
    **Why:** The spec reduced the footer scope (no Kaggle / GitHub / video links until destinations exist), which leaves this section as the only place that names the hackathon. Surface it.
    **Effort:** XS (10min).
    **Priority:** P2.

### Cross-section — structural moves

22. **Location:** All nine sections use `border-t border-border-subtle py-16 tablet:py-20 desktop:py-32`.
    **Current:** Identical boundary + identical vertical padding on every section creates the WordPress-template scroll feel.
    **Target:** Three tiers of section weight:
      - **Tier 1 (Hero + CTA Rail):** Full viewport, no top border.
      - **Tier 2 (Problem + Receipts + Ollama):** `py-32` desktop, `border-t` in `border-border-subtle`, **plus** a 120px `radial-gradient` glow in the section's tone color fading from top-center. Problem = no glow (typography only). Receipts = insight-tinted. Ollama = thrive-tinted. This is the atmospheric layer that's missing.
      - **Tier 3 (How It Works + Data Sources + Team):** `py-24` desktop (slightly tighter), no border-top, but a 1px vertical rule centered at top in `border-border-subtle` that extends 80px down as a visual "these are structural / supporting sections."
    **Why:** Nine sections should feel like a three-act structure with supporting interludes, not nine equal-weight chapters. This is the single biggest move to fix the template feel.
    **Effort:** M (3h — touches every section + needs a section-type abstraction).
    **Priority:** P0.

23. **Location:** `Landing.tsx:17-30` (page root)
    **Current:** Nine section components stacked inside `<main className="min-h-screen bg-bp-void">`. No intermediate atmospheric layers.
    **Target:** Add a single global noise + star layer as a `fixed inset-0 pointer-events-none -z-10` div on the Landing route only. The layer renders:
      1. The radial-gradient stack from `DESIGN.md §Surface Treatments → Background Gradient`.
      2. The 2.5% opacity noise texture.
      3. A fixed twinkle field of ~60 stars scattered across the *entire page* (not just the hero) with `twinkle` animation.
      `useReducedMotion()` suspends the stars. The noise + gradient stay static.
    **Why:** Right now the hero has atmosphere and every subsequent section has void. Making the atmosphere *continuous across the whole scroll* is what differentiates a cinematic dark from "dark mode." The star-field is the visual binding agent.
    **Effort:** M (3h — one component + z-index/pointer-events plumbing + reduced-motion integration).
    **Priority:** P0.

---

## §4. What's actually good

Five things worth keeping. The page isn't all bad.

1. **The `PentagonGlow` component itself** — the reused in-app constellation is the right visual anchor. It's doing the work of five images (logomark, scroll indicator, product signature, marketing asset, video end-card). Everything else in the hero section needs work; the pentagon is not the problem.

2. **The Problem section's typographic receipts** — `82% exposed to AI` in insight-purple and `$400/hour counselor` in alert-amber inline inside body copy is the cleanest voice-guide-surface on the page. Do not change this.

3. **The `useReducedMotion()` pattern** — every section correctly wraps its animations and collapses to a static final state. This is clean implementation work and it should be preserved verbatim when new atmospheric layers are added.

4. **The `ScreenshotWithFallback` probe pattern itself** — the idea is right (probe the image, fall back gracefully). The *fallback treatment* is the problem, not the probe logic. Keep the hook; replace the skeleton.

5. **The TerminalSVG** — the only element on the page with real material craft. Real text, green prompts, green checkmarks that tie to in-app WIN states, blinking cursor. This is what every section should be aspiring to.

6. **The Ollama section copy** — "When a school runs FutureProof on Ollama, no student data leaves the building" — the scoped data-residency line is ship-correct and still punchy. The staff-engineer re-review fix landed clean.

7. **The 7-row dataset table content** — the row counts are accurate (Karpathy at 815, not 342), the "Powers" column maps each dataset to the stat it feeds, the composite AI exposure footnote exists. The data is right. Only the visual treatment needs work (see #18–20).

---

## §5. The question of ambition

**Is this a polished version of a safe design, or an unfinished version of an ambitious design?**

It's an unfinished version of an ambitious design. Three pieces of evidence:

1. **The ambition is clearly articulated.** `reports/design-vision-2026-04-17.md` §1 says *"If a submission could be swapped for another Gemma 4 Good submission by changing the logo and the headline, it failed."* §6.2 says *"Every pixel of FutureProof should be illegible outside the Brightpath system."* The visionary doc set a high bar.

2. **The spec §3 preserved the ambition.** Token tables name every atmosphere (ambient glow, twinkle field, pentagon drift, insight glow behind the receipt screenshot, thrive glow on the terminal). The spec did not shave those off.

3. **The implementation stubbed the atmospheric work.** The star-field is gone. The insight glow behind the receipts is invisible because it's inside the same bounding rect. The terminal has a generic border instead of a thrive edge. The Ollama section has no environmental treatment. The plush laptop asset was never produced. The hero pentagon shipped at the spec's low-end size (320px) instead of the ambitious size (480px).

**So the focus is: finish the atmospheric work that was stubbed.** Specifically:

- Item #23 (global star + noise layer across the whole scroll): the single most ambition-restoring move on the list.
- Item #22 (three-tier section weights): ties the nine-section scroll into a three-act structure.
- Item #12 (extend the insight glow beyond the screenshot bounding rect): makes the proof moment feel like proof.
- Item #14 (scanline / vignette on the Ollama section): gives the track-specific credibility moment an environment.
- Item #1 (scale the hero pentagon up to 440px): lets the signature visual actually dominate the fold.

None of these are new features. None require new dependencies. None require content Jeff doesn't have. They're all finishing moves on a vision that was stopped one draft short.

**The answer to the binary is: polish, but the polish is specifically the atmospheric finish that got cut.** Call it POLISH THE VISION. A two-day pass through P0s 1, 2, 3, 5, 10, 12, 14, 15 (or 15 fallback), 17, 22, 23 gets the page from "pretty ugly, looks amateurish" to "what you were supposed to see on day one."

The P1 items take it one step further. The P2 items are week-three polish that can wait for screenshots to land.

---

## Screenshot references

- Full-page desktop: `/tmp/landing-review/desktop.png`
- Above-the-fold desktop (1440×900): `/tmp/landing-review/desktop-fold.png`
- Full-page tablet: `/tmp/landing-review/tablet.png`
- Full-page mobile: `/tmp/landing-review/mobile.png`
- Per-section crops (9 files): `/tmp/landing-review/sec-landing-section-*.png` + `sec-landing-footer.png`
- Console log (clean): `/tmp/landing-review/console.log`

Console was clean. Every visual issue named in §1 is a design issue, not a runtime bug. The page loads correctly; it just doesn't look good.
