# Brightpath Design System

The single source of truth for FutureProof's visual language. Everything in this file maps directly to implemented tokens, Tailwind config, and motion presets. If it's not here, it's not part of the system.

**Name:** Brightpath
**Aesthetic:** Cinematic dark. Plush materiality. Progressive illumination.
**Reference:** Pixar warmth, Studio Ghibli lush environments, RPG character screen progression.

---

## Design Philosophy

Three pillars drive every visual decision:

1. **Cinematic Dark** — Dark backgrounds create focus. Accent colors read as light in darkness. The student's future is literally being illuminated. Not brooding or edgy — the darkness of a planetarium before the show begins.

2. **Plush Materiality** — Everything is soft. Rounded corners, gentle shadows, smooth gradients. The plush aesthetic makes a terrifying topic (career planning) feel approachable. A plush bear with glowing stats is inviting; a spreadsheet is not.

3. **Progressive Illumination** — The design metaphor: you start in the dark, and things light up as you go. Character select is warm. School selection adds glow. The Stage 2 reveal is a burst of light. The branch tree is a constellation of illuminated futures.

---

## Color Tokens

### Backgrounds

Night-sky indigo, not black. Not grey. Indigo carries warmth and depth.

| Token | CSS Variable | Hex | Tailwind | Usage |
|-------|-------------|-----|----------|-------|
| bg-void | `--color-bg-void` | `#12131F` | `bg-bp-void` | Deepest canvas, branch tree backdrop |
| bg-deep | `--color-bg-deep` | `#1B1D30` | `bg-bp-deep` | Primary page background |
| bg-mid | `--color-bg-mid` | `#232545` | `bg-bp-mid` | Card backgrounds, elevated surfaces |
| bg-surface | `--color-bg-surface` | `#2D3060` | `bg-bp-surface` | Interactive surfaces, hover states |
| bg-raised | `--color-bg-raised` | `#3A3D75` | `bg-bp-raised` | Tooltips, popovers, active states |

### Accents

Each accent carries specific semantic meaning. These are the stars in the night sky.

| Token | CSS Variable | Hex | Tailwind | Semantic Role |
|-------|-------------|-----|----------|---------------|
| thrive | `--color-accent-thrive` | `#7DD4A3` | `text-accent-thrive` | Growth, wins, CTAs, positive outcomes |
| alert | `--color-accent-alert` | `#F4A97E` | `text-accent-alert` | Warnings, losses, debt, negative outcomes |
| caution | `--color-accent-caution` | `#F2D477` | `text-accent-caution` | Draw states, moderate outcomes, attention |
| insight | `--color-accent-insight` | `#B8A9E8` | `text-accent-insight` | AI, intelligence, data, analysis |
| info | `--color-accent-info` | `#7BB8E0` | `text-accent-info` | Navigation, links, neutral information |
| empathy | `--color-accent-empathy` | `#E88BA9` | `text-accent-empathy` | Human connection, emotional content |

### Stat Colors

One color per pentagon axis. These are accent aliases with stat-specific semantics.

| Stat | CSS Variable | Hex | Tailwind | Rationale |
|------|-------------|-----|----------|-----------|
| ERN (Earning Power) | `--color-stat-ern` | `#F2D477` | `text-stat-ern` | Gold. Money. |
| ROI (Return on Investment) | `--color-stat-roi` | `#7DD4A3` | `text-stat-roi` | Green. Growth. Returns. |
| RES (AI Resilience) | `--color-stat-res` | `#B8A9E8` | `text-stat-res` | Purple. The AI/tech color. |
| GRW (Growth Potential) | `--color-stat-grw` | `#7BB8E0` | `text-stat-grw` | Blue. Expansive. Upward. |
| HMN (Human Edge) | `--color-stat-hmn` | `#E88BA9` | `text-stat-hmn` | Pink. Warm. Human. |

### Text

Warm white, never blue-white.

| Token | CSS Variable | Hex | Tailwind | Usage |
|-------|-------------|-----|----------|-------|
| primary | `--color-text-primary` | `#F5F0E8` | `text-text-primary` | Primary body text |
| secondary | `--color-text-secondary` | `#C4BFB0` | `text-text-secondary` | Labels, descriptions |
| muted | `--color-text-muted` | `#8A8595` | `text-text-muted` | Disabled, fine print |
| inverse | `--color-text-inverse` | `#1B1D30` | `text-text-inverse` | Text on accent backgrounds |

### Boss Colors

Each boss monster has a signature hue for its fight sequence.

| Boss | CSS Variable | Hex | Tailwind | Reasoning |
|------|-------------|-----|----------|-----------|
| Fight AI | `--color-boss-ai` | `#B8A9E8` | `text-boss-ai` | Purple. The AI color. |
| Student Loans | `--color-boss-loans` | `#F4A97E` | `text-boss-loans` | Amber. Debt burns. |
| The Market | `--color-boss-market` | `#7BB8E0` | `text-boss-market` | Ice blue. Cold market. |
| Burnout | `--color-boss-burnout` | `#E88BA9` | `text-boss-burnout` | Pink-red. Emotional. |
| The Ceiling | `--color-boss-ceiling` | `#C4BFB0` | `text-boss-ceiling` | Muted grey-beige. Invisible. |
| The Future | Shifts through all five | — | — | Final boss contains all threats. |

### Borders

Soft white at low opacity. Never solid colored borders.

| Token | CSS Variable | Value | Tailwind |
|-------|-------------|-------|----------|
| subtle | `--color-border-subtle` | `rgba(255, 255, 255, 0.06)` | `border-border-subtle` |
| default | `--color-border-default` | `rgba(255, 255, 255, 0.1)` | `border-border` |
| strong | `--color-border-strong` | `rgba(255, 255, 255, 0.2)` | `border-border-strong` |

### States

Background washes for interactive states. Semantic aliases that prevent raw `rgba()` values from scattering through the codebase.

| Token | CSS Variable | Value | Usage |
|-------|-------------|-------|-------|
| loading | `--color-state-loading` | `rgba(184, 169, 232, 0.15)` | Loading state background wash (insight-tinted) |
| success | `--color-state-success` | `rgba(125, 212, 163, 0.15)` | Success flash background (thrive-tinted) |
| error | `--color-state-error` | `rgba(244, 169, 126, 0.15)` | Error state background (alert-tinted) |
| disabled | `--color-state-disabled` | `rgba(138, 133, 149, 0.3)` | Disabled element overlay (muted at 30%) |
| active | `--color-state-active` | `rgba(125, 212, 163, 0.1)` | Persistent selected/active background (subtler than success) |
| focus-ring | `--color-focus-ring` | `rgba(123, 184, 224, 0.4)` | Accessibility focus ring (info at 40%) |

---

## Typography

### Font Families

| Role | Font | Tailwind | Weights | Purpose |
|------|------|----------|---------|---------|
| Display / Headlines | **Fredoka** (variable) | `font-display` | 400, 500, 600, 700 | Rounded, friendly, confident. Game UI without being cartoonish. |
| Body / UI | **Nunito** | `font-body` | 400, 600, 700, 800 | Clean, warm, readable. Generous x-height. The workhorse. |
| Data / Monospace | **Space Mono** | `font-data` | 400, 700 | Technical, precise. Signals "this is real data." |

Google Fonts import:
```
Fredoka:wght@400;500;600;700
Nunito:wght@400;600;700;800
Space Mono:wght@400;700
```

### Type Scale

1.25 ratio (major third), base 16px.

| Token | CSS Variable | Size | Line Height | Font | Weight | Tailwind | Usage |
|-------|-------------|------|-------------|------|--------|----------|-------|
| hero | `--text-hero` | 48px / 3rem | 1.1 | Fredoka | 700 | `text-hero` | Screen titles |
| title | `--text-title` | 40px / 2.5rem | 1.2 | Fredoka | 700 | `text-title` | Landing tagline |
| display | `--text-display` | 36px / 2.25rem | 1.15 | Fredoka | 700 | `text-display` | Section headers, boss names |
| heading | `--text-heading` | 28px / 1.75rem | 1.2 | Fredoka | 600 | `text-heading` | Card titles, stat labels |
| subheading | `--text-subheading` | 22px / 1.375rem | 1.3 | Nunito | 700 | `text-subheading` | Sub-sections, career titles |
| body-lg | `--text-body-lg` | 18px / 1.125rem | 1.5 | Nunito | 400 | `text-body-lg` | Landing subtitle |
| body | `--text-body` | 16px / 1rem | 1.5 | Nunito | 400 | `text-body` | Default body text |
| body-sm | `--text-body-sm` | 15px / 0.9375rem | 1.5 | Nunito | 400 | `text-body-sm` | Mobile subtitle |
| cta | `--text-cta` | 17px / 1.0625rem | 1.4 | Nunito | 700 | `text-cta` | CTA button text |
| small | `--text-small` | 14px / 0.875rem | 1.4 | Nunito | 400 | `text-small` | Captions, metadata |
| micro | `--text-micro` | 12px / 0.75rem | 1.3 | Nunito | 600 | `text-micro` | Badges, labels, tiny UI |
| stat-label | `--text-stat-label` | 10px / 0.625rem | 1.3 | Nunito | 600 | `text-stat-label` | Pentagon stat labels |
| data-lg | `--text-data-large` | 24px / 1.5rem | 1.2 | Space Mono | 700 | `text-data-lg` | Hero stat numbers |
| data | `--text-data` | 16px / 1rem | 1.4 | Space Mono | 400 | `text-data` | Salary figures, percentages |
| data-sm | `--text-data-small` | 13px / 0.8125rem | 1.3 | Space Mono | 400 | `text-data-sm` | Stat deltas, small data |

### Line Heights

Line-height tokens pair with the type scale above. `leading-normal` is the body default; use the others where the scale's per-token line-height isn't enough (tight headlines, breathing pull quotes).

| Token | CSS Variable | Value | Tailwind | Usage |
|-------|-------------|-------|----------|-------|
| tight | `--leading-tight` | 1.1 | `leading-tight` | Hero/display headlines, screen intros |
| snug | `--leading-snug` | 1.2 | `leading-snug` | Large titles, multi-line section headers |
| relaxed | `--leading-relaxed` | 1.4 | `leading-relaxed` | Reasoning card paragraphs, long captions |
| normal | `--leading-normal` | 1.5 | `leading-normal` | Body default (applied on `<body>`) |

---

## Spacing

4px base unit. Use Tailwind spacing utilities directly.

| Token | CSS Variable | Value | Tailwind |
|-------|-------------|-------|----------|
| space-1 | `--space-1` | 4px | `p-1`, `m-1`, `gap-1` |
| space-2 | `--space-2` | 8px | `p-2`, `m-2`, `gap-2` |
| space-3 | `--space-3` | 12px | `p-3`, `m-3`, `gap-3` |
| space-4 | `--space-4` | 16px | `p-4`, `m-4`, `gap-4` |
| space-5 | `--space-5` | 20px | `p-5`, `m-5`, `gap-5` |
| space-6 | `--space-6` | 24px | `p-6`, `m-6`, `gap-6` |
| space-8 | `--space-8` | 32px | `p-8`, `m-8`, `gap-8` |
| space-10 | `--space-10` | 40px | `p-10`, `m-10`, `gap-10` |
| space-12 | `--space-12` | 48px | `p-12`, `m-12`, `gap-12` |
| space-16 | `--space-16` | 64px | `p-16`, `m-16`, `gap-16` |
| space-20 | `--space-20` | 80px | `p-20`, `m-20`, `gap-20` |

---

## Border Radii

Everything is rounded. Nothing in this world has a sharp corner.

| Token | CSS Variable | Value | Tailwind | Usage |
|-------|-------------|-------|----------|-------|
| sm | `--radius-sm` | 6px | `rounded-sm` | Small badges, pills |
| md | `--radius-md` | 10px | `rounded-md` | Input fields, chips |
| lg | `--radius-lg` | 14px | `rounded-lg` | Standard cards, buttons |
| xl | `--radius-xl` | 20px | `rounded-xl` | Large cards, panels |
| full | `--radius-full` | 9999px | `rounded-full` | Circles, avatars, stat dots |

---

## Elevation & Shadows

Layered glow shadows, not traditional box-shadows. Shadows pick up ambient accent colors.

| Token | CSS Variable | Value | Tailwind | Usage |
|-------|-------------|-------|----------|-------|
| sm | `--shadow-sm` | `0 2px 8px rgba(27, 29, 48, 0.5)` | `shadow-sm` | Subtle lift |
| md | `--shadow-md` | `0 4px 16px rgba(27, 29, 48, 0.6)` | `shadow-md` | Cards |
| lg | `--shadow-lg` | `0 8px 32px rgba(27, 29, 48, 0.7)` | `shadow-lg` | Modals, popovers |
| glow-thrive | `--shadow-glow-thrive` | `0 0 20px rgba(125, 212, 163, 0.3)` | `shadow-glow-thrive` | Active/selected states |
| glow-alert | `--shadow-glow-alert` | `0 0 20px rgba(244, 169, 126, 0.3)` | `shadow-glow-alert` | Warning glow |
| glow-caution | `--shadow-glow-caution` | `0 0 20px rgba(242, 212, 119, 0.3)` | `shadow-glow-caution` | Attention glow |
| glow-insight | `--shadow-glow-insight` | `0 0 20px rgba(184, 169, 232, 0.3)` | `shadow-glow-insight` | AI/data glow |
| glow-info | `--shadow-glow-info` | `0 0 20px rgba(123, 184, 224, 0.3)` | `shadow-glow-info` | Info/focus glow |
| glow-empathy | `--shadow-glow-empathy` | `0 0 20px rgba(232, 139, 169, 0.3)` | `shadow-glow-empathy` | Human/emotional glow |

---

## Transitions & Timing

### CSS Transitions

For simple hover/focus states. Springs (below) handle meaningful animations.

| Token | CSS Variable | Duration | Tailwind |
|-------|-------------|----------|----------|
| fast | `--transition-fast` | 150ms ease-out | `duration-fast` |
| normal | `--transition-normal` | 200ms ease-out | `duration-normal` |
| slow | `--transition-slow` | 300ms ease-out | `duration-slow` |

---

## Breakpoints

| Token | Width | Tailwind Prefix |
|-------|-------|-----------------|
| mobile | 480px | `mobile:` |
| tablet | 768px | `tablet:` |
| desktop | 1200px | `desktop:` |
| wide | 1440px | `wide:` |
| ultra | 1920px | `ultra:` |

---

## Grid System

Every page is laid out on a **12-column responsive grid**. Column count is fixed at 12 at every breakpoint; responsive behavior comes from how content spans those columns.

### Tokens

| Token | CSS Variable | Value | Usage |
|-------|--------------|-------|-------|
| columns | `--layout-grid-columns` | 12 | Fixed at every breakpoint |
| gutter.mobile | `--layout-grid-gutter-mobile` | 16px | Gap + outer padding on mobile (<768) |
| gutter.tablet | `--layout-grid-gutter-tablet` | 24px | Gap + outer padding at ≥768 |
| gutter.desktop | `--layout-grid-gutter-desktop` | 32px | Gap + outer padding at ≥1200 |
| container.tablet | `--layout-container-max-tablet` | 720px | Max container width at ≥768 |
| container.desktop | `--layout-container-max-desktop` | 1024px | Max container width at ≥1200 |
| container.wide | `--layout-container-max-wide` | 1200px | Max container width at ≥1440 |
| container.ultra | `--layout-container-max-ultra` | 1280px | Max container width at ≥1920 |

### Column Span Conventions

| Pattern | Mobile | Tablet | Desktop+ |
|---------|--------|--------|----------|
| Single-column readable (forms, long-form) | `col-span-12` | `col-span-12` | `col-span-8 col-start-3` |
| Full-bleed visualization | `col-span-12` | `col-span-12` | `col-span-12` |
| Main + sidebar | stacked | stacked | `col-span-8` + `col-span-4` |
| Three-up cards | stacked | `col-span-6` (2-up, wraps) | `col-span-4` (3-up) |

### Implementation

Every screen wraps content in `<PageContainer>` (`frontend/src/components/ui/PageContainer.tsx`). Three variants:

| Variant | Purpose |
|---------|---------|
| `centered` | Single-column readable content. Wraps children in `col-span-12 desktop:col-span-8 desktop:col-start-3`. Used for forms (SchoolMajor), identity (Profile), hero (Landing). |
| `grid` | Exposes the raw 12-col grid. Children pick their own spans. Used for multi-column layouts (CareerPick tiers, BranchTree with sidebar, Reveal pentagon+stats, Gauntlet). |
| `bleed` | Responsive container max-width only, no grid layer. For full-bleed content (SaveWrapped viewer). |

Tailwind's native `container` utility is configured in `tailwind.config.ts` with the breakpoint-indexed max-widths and padding above. Gutters are available as `gap-grid-mobile`, `gap-grid-tablet`, `gap-grid-desktop` utilities.

See also: §Breakpoints for viewport definitions and §Spacing for the 4px-base spacing scale.

---

## Surface Treatments

### Background Gradient

The page background is not flat. It uses layered radial gradients over the void color:

```css
background-image:
  radial-gradient(ellipse 80% 60% at 20% 10%, rgba(45, 48, 96, 0.5) 0%, transparent 70%),
  radial-gradient(ellipse 60% 50% at 80% 35%, rgba(58, 61, 117, 0.35) 0%, transparent 65%),
  radial-gradient(ellipse 70% 40% at 50% 70%, rgba(35, 37, 69, 0.6) 0%, transparent 60%),
  radial-gradient(ellipse 50% 50% at 10% 90%, rgba(58, 61, 117, 0.25) 0%, transparent 55%),
  linear-gradient(180deg, #12131F 0%, #1B1D30 30%, #181A2E 60%, #12131F 100%);
```

### Noise Texture

A subtle SVG noise overlay at 2.5% opacity prevents the "flat CSS" look. Implemented as a fixed `::before` pseudo-element or a `.noise-overlay` div. See `index.css`.

### Ambient Glow

A breathing radial gradient (thrive + insight + info blend) that pulses on a 6s cycle. Creates a sense of life in the background. See `.ambient-glow` in `index.css`.

### Twinkling Stars

Small 2px dots with a `twinkle` animation (4s cycle, opacity 0.05 to 0.45). Scattered in backgrounds to reinforce the night-sky metaphor. See `.star` in `index.css`.

---

## Motion System

All meaningful animations use Framer Motion spring physics, not CSS timing functions. Import from `@/styles/motion`.

### Spring Configurations

| Token | Config | Feel | Usage |
|-------|--------|------|-------|
| `springs.bouncy` | `{ stiffness: 300, damping: 20 }` | Playful pop, noticeable overshoot | Character reveals, boss entrance, stat counters, branch node activation |
| `springs.smooth` | `{ stiffness: 200, damping: 25 }` | Confident settle, gentle overshoot | Page transitions, card entrances, panel expansions |
| `springs.gentle` | `{ stiffness: 150, damping: 30 }` | Slow and graceful, minimal overshoot | Background shifts, ambient glows, branch tree initial render |
| `springs.snappy` | `{ stiffness: 400, damping: 25 }` | Quick and responsive, slight bounce | Button press, toggle, slider thumb, micro-interactions |

### Stagger Delays

| Token | Delay | Usage |
|-------|-------|-------|
| `stagger.fast` | 50ms | Stat bars, skill badges, rapid lists |
| `stagger.normal` | 80ms | Card grids, branch nodes, standard lists |
| `stagger.slow` | 100ms | Branch tree tiers, boss fight sequence, cinematic reveals |

### Common Transitions

| Token | Animation | Spring | Usage |
|-------|-----------|--------|-------|
| `transitions.fadeInUp` | opacity 0 + y:24 -> visible | smooth | Standard element entrance |
| `transitions.scaleIn` | opacity 0 + scale:0.8 -> visible | bouncy | Bears, pentagons, boss monsters |
| `transitions.fade` | opacity 0 -> visible | 300ms ease-out | Background shifts, ambient changes |
| `transitions.press` | scale to 0.97 on tap | snappy | Button press feedback |

### Reusable Variants

| Variant | Description | Usage |
|---------|-------------|-------|
| `staggerContainer(delay, amount)` | Container that staggers children | Wrap any list/grid of animated children |
| `staggerItem` | Child that fades up (y:20) | Individual items in staggered lists |
| `scaleItem` | Child that scales in (0.85) | Grid reveals, card grids |

### Key Animation Sequences

**Stage 2 Reveal (the signature moment):**
1. Glow pulse (0.8s) — subtle ambient glow before bear appears
2. Bear reveal (delay 0.5s) — scale from 0.85, bouncy spring
3. Pentagon draw (delay 1.0s) — scale from center, smooth spring
4. Title reveal (delay 1.4s) — fade up, smooth spring
5. Stat numbers count up simultaneously

**Boss Fight Entrance:**
1. Vignette darkening (0.3s)
2. Boss bounces in from above (y:-60, bouncy spring)
3. Win: green burst (scale pulse 1 -> 1.15 -> 1, 0.4s)
4. Lose: screen shake (x: 0, -3, 3, -3, 3, 0, 0.3s)

**Branch Tree Illumination:**
1. Root glow starts (t=0)
2. Branch lines begin drawing (t=0.3s)
3. Branch label nodes pop in (t=0.8s, stagger 0.1s)
4. Career progression nodes appear (t=1.5s)
5. Endpoint silhouettes fade in (t=2.2s)
6. Particles begin drifting (t=3.0s)
7. Total duration: 3.5s

**Branch Flash (tree-as-map):**
- `branchFlash` preset (`frontend/src/styles/motion.ts`) and matching CSS keyframe `branchFlashPulse` in `reactflow-dark.css`. Fires when Gemma names a branch in chat on `/branch-tree`.
- Scale `1 → 1.06 → 1` over 600ms, glow `accent-info` rgba(123, 184, 224, 0 → 0.55 → 0). Times `[0, 0.42, 1]`. Attentional, not celebratory — the metaphor is a soft pulse like a nav reveal.
- `branchFlashStagger = 0.2` (200ms) between multi-match highlights when one Gemma response names several branches.
- Reduced-motion: 80ms opacity blink (no scale, no glow). Defined inline at the keyframe in `reactflow-dark.css`.

**Tree-as-map node scale:** the `--branch-flow-node-scale` CSS variable in `reactflow-dark.css` controls the React Flow node scale when the tree is rendered as a context rail (the `/branch-tree` tree-as-map view). Default `1.0`; the screen wrapper sets `0.85` to dial down visual weight without forking the flow-node components. Activated by `data-compact="true"` on the `BranchTreeFlow` wrapper.

### CSS Keyframe Animations

For effects that don't need spring physics. Defined in `index.css`:

| Animation | Duration | Usage |
|-----------|----------|-------|
| `stat-label-fade` | 1s ease-out | Pentagon stat labels fading in |
| `vertex-glow-pulse` | 4s ease-in-out infinite | Pentagon vertex glow dots |
| `ambient-breathe` | 6s ease-in-out infinite | Background ambient glow (absolute-positioned translate + scale) |
| `twinkle` | 4s ease-in-out infinite | Star particles |
| `card-breathe` | 4s ease-in-out infinite | Insight glow pulse on Gemma Match Card + Reasoning Card (`box-shadow` 24 → 36px at `rgba(184, 169, 232, 0.12 → 0.25)`) |
| `card-breathe-caution` | 4s ease-in-out infinite | Caution variant of card glow (low-confidence match card) |
| `card-breathe-info` | 4s ease-in-out infinite | Info variant of card glow |
| `landing-pending-dot` | 2s ease-in-out infinite | Landing screenshot-pending dot pulse |
| `terminal-cursor-blink` | 1s steps(2, end) infinite | Canonical caret/cursor blink — terminal cursor, streaming cursor, input caret. Utility class `.animate-terminal-cursor`. Never add a second blink keyframe. |
| `gemma-shimmer` | 320ms ease-out forwards | One-shot insight-gradient sweep across a *single* sentence the moment it arrives in a Reasoning Card. Fires per sentence, settles, does not loop. Paired with a text-opacity ramp 0.6 → 1.0 on the sentence element so the eye reads "this sentence just got real." Utility class `.animate-gemma-shimmer`. |
| `chip-pulse-caution` | 1.6s ease-in-out infinite | Low-confidence pulse on a primary Chip. Smaller glow radius than `card-breathe-caution` — tuned for chip-sized surfaces. Utility class `.animate-chip-pulse-caution`. |
| `heroFadeIn` | 0.8s ease-out | Campus Hero Banner fade-in on page load. Simple `opacity: 0 → 1`. |
| `sealedPulse` | 2s ease-in-out infinite | Sealed boss portrait breathing — `opacity: 0.7 ↔ 0.85`. Signals "this fight is waiting." |
| `sealedShimmer` | 0.6s ease-out forwards | One-shot light sweep across a sealed Boss Band on viewport entry. `translateX(-100%) → translateX(200%)`. Fires once, does not loop. |
| `collisionSlam` | 0.4s bouncy, delay 0.18s | VS collision emoji (💥) — `scale(0) → 1.3 → 1.0 → 0.6`. Fires during VS overlay. |
| `dustPuff1–5` | 0.6–0.7s ease-out, delays 0.25–0.35s | Five unique drift keyframes for VS dust puffs (💨). Each translates ±45–60px in a different direction, scales 0.3 → 1.2–1.6, fades out. |
| `vsBurst` | 0.35s ease-out, delay 0.3s | Boss-colored energy burst during VS — `scale(0) → scale(2.5)`, fades out. 120px radial gradient in boss color. |
| `winPulse` | 0.6s ease-in-out | Green glow pulse on win — `box-shadow: 0 → 32px → 0` at `rgba(125,212,163,0.25)`. Utility class `.anim-win-pulse`. |
| `loseShake` | 0.4s ease-in-out | Horizontal shake on loss — `translateX(0, -3, 3, -2, 1, 0)`. Applied to `.result-word`. Utility class `.anim-lose-shake`. |
| `drawWobble` | 0.4s ease-in-out | Rotation wobble on draw — `rotate(0° → 1.5° → -1.5° → 0°)`. Applied to `.result-word`. Utility class `.anim-draw-wobble`. |
| `verdictScaleIn` | 0.5s bouncy | Verdict Badge entrance — `scale(0.85) → scale(1)`, `opacity: 0 → 1`. Bouncy cubic-bezier(0.34, 1.56, 0.64, 1). |
| `popoverIn` | 180ms bouncy | Stat Info Popover entrance — `translateY(-6px) → 0`, `opacity: 0 → 1`. cubic-bezier(0.34, 1.4, 0.64, 1). |
| `popoverOut` | 150ms ease-in | Stat Info Popover exit — reverse of `popoverIn`. |

All animations respect `prefers-reduced-motion: reduce` — keyframes hold at their resting frame and background gradients collapse. New keyframes must include the reduced-motion override at the point of definition, not in a component.

### VS Overlay

Full-card overlay that plays a "player vs. boss" confrontation animation before revealing the boss fight result. Fires when a Boss Band enters the center third of the viewport.

**Container:**
```
position: absolute, inset: 0, z-index: 10
display: flex, align-items: center, justify-content: center, gap: 32px
background: bg-void
border-radius: radius-xl
opacity: 0
pointer-events: none
transition: opacity 0.15s ease-out
```

**Portraits:** 96px square (mobile: 72px), `radius-xl` (mobile: `radius-lg`). Player uses info gradient, boss uses boss-color gradient. Same gradient pattern as Boss Portrait: `linear-gradient(135deg, rgba({color}, 0.30), rgba({color}, 0.12))` with 1px border and 20px glow.

**Portrait entrances:**
- Player slides from left: `translateX(-40px) scale(0.6)` → `translateX(0) scale(1)`, bouncy cubic-bezier
- Boss slides from right: `translateX(40px) scale(0.6)` → `translateX(0) scale(1)`, bouncy cubic-bezier, 30ms delay

**"VS" text:** `font-display`, 700, 32px (mobile: 26px), `text-primary`, `letter-spacing: 4px`, `text-shadow: 0 0 24px rgba(245,240,232,0.15)`. Scales from 0.8 → 1, 100ms delay.

**Names:** `font-body`, 600, 13px (mobile: 12px), `text-secondary`, centered, truncated at 120px. Player shows full character name; boss shows `shortName` (see Boss Naming Pattern).

**Collision (💥):** `collisionSlam` keyframe — `scale(0) → scale(1.3) → scale(1.0) → scale(0.6)`, 0.4s, delay 0.18s, bouncy cubic-bezier. Positioned absolute center.

**Dust puffs (💨):** 5 particles, each with a unique drift keyframe:
- Each drifts in a different direction: `translate(±45–60px, ±35–55px)`
- Scale: 0.3 → 1.2–1.6
- Duration: 0.6–0.7s, delays: 0.25–0.35s
- Peak opacity: 0.5–0.7

**Boss-colored energy burst:** `::before` pseudo-element, 120px radial gradient of boss color at 20% opacity. `vsBurst` keyframe: `scale(0) → scale(2.5)`, 0.35s ease-out, delay 0.3s.

**Total sequence:** ~1.5s from VS-active to overlay fadeout. Overlay fades out via `opacity: 0` over 0.12s when `.vs-done` class is added.

### Scroll-Snap Gauntlet

The scroll-driven reveal system for Boss Bands. Cards are laid out vertically and animate sequentially as the user scrolls.

**Container:**
```
display: flex
flex-direction: column
gap: 48px
scroll-snap-type: y proximity
```

**Cards:** `scroll-snap-align: center`

**Dual IntersectionObserver pattern:**
1. **Visibility observer** (threshold: 0.1, rootMargin: '0px'): Fires the sealed shimmer animation when a card first enters the viewport edge. Adds `.sealed-visible` class.
2. **Center-third observer** (threshold: 0.5, rootMargin: '-33% 0px -33% 0px'): Fires the VS trigger when a card reaches the middle third of the viewport. Calls `requestReveal()`.

**Animation queue:** One animation plays at a time. If a card triggers while another is animating, it enters a `pendingQueue` and plays when the current animation completes. Sequential, never overlapping.

**Fast-scroll protection:** If a card leaves the viewport while mid-animation (`.vs-active` or `.sealed-hold` but not `.revealed`), it immediately skips to the revealed state — classes `.sealed-triggered`, `.vs-done`, `.revealed` are applied synchronously, and the card is removed from the pending queue.

---

## Brand / Wordmark

The **FutureProof wordmark** is the product's signature — a warm-white wordmark preceded by a lavender sparkle glyph. It reads as "a proper noun, lit from the side." No other wordmark treatment is official.

### Anatomy

```
✦ FutureProof
└┬┘ └────┬────┘
 │       └── Wordmark: font-display, weight 600, letter-spacing -0.01em, text-text-primary (#F5F0E8)
 └────────── Glyph: ✦ (U+2726 Black Four Pointed Star), text-accent-insight (#B8A9E8), 6px right margin
```

- **Glyph:** `✦` — the same sparkle used for the Gemma-star motif elsewhere in the product. Always `--color-accent-insight` (#B8A9E8). Never any other color, never swapped for a different glyph.
- **Wordmark:** Always the single token `FutureProof` (PascalCase, no space). Always `--color-text-primary` warm white. Never green, never `accent-thrive`, never italicized.
- **Pairing:** Glyph + wordmark are inseparable. Do not show the wordmark without the glyph in top-nav/footer/chrome chrome contexts.

### Sizes

| Size | Font Size | Weight | Glyph Size | Usage |
|------|-----------|--------|------------|-------|
| sm | `text-body-sm` (15px) | 600 | matches text | Compact chrome: in-app top nav (AppHeader) |
| md | `text-body-lg` (18px) | 600 | matches text | Default: marketing top nav, mockup chrome |
| lg | `text-heading` (28px) | 700 | matches text | Footer identity, large-format chrome |

Letter-spacing is `-0.01em` at every size. Line-height collapses to `1` so the baseline aligns with the glyph cleanly.

### Implementation

Use the `<Wordmark />` component (`frontend/src/components/ui/Wordmark.tsx`) — never inline the treatment. A single source prevents the kind of drift the pre-systematization wordmark had (three call sites, three different colors, no glyph).

```tsx
import { Wordmark } from "@/components/ui/Wordmark";

<Wordmark size="sm" />   // AppHeader
<Wordmark size="md" />   // LandingTopNav
<Wordmark size="lg" />   // HorizonFooter
```

---

## Focus States

Every interactive element (buttons, chips, inputs, textareas, disclosure toggles, links, clickable rows) must show a visible focus ring on `:focus-visible`. The ring is a high-contrast info-tinted outline — it's the only accessibility token that trumps aesthetics.

**Global convention:**
```css
button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
[role="button"]:focus-visible {
  outline: 3px solid var(--color-focus-ring);  /* rgba(123, 184, 224, 0.4) */
  outline-offset: 2px;
}
```

- **Ring color:** `--color-focus-ring` — the info accent at 40% opacity. Never swap to another color. Consistent across light and dark surfaces.
- **Offset:** 2px. Prevents the ring from blending into rounded-card borders.
- **Thickness:** 3px. Meets WCAG 2.2 focus-visible contrast minimums against every background token.

**Input-specific override:** `.input-field:focus-within` swaps the ring for a glowing box-shadow (`0 0 0 3px var(--color-focus-ring)` + border-color shift to `accent-info`). Same visual weight, inset to the field's rounded rectangle. See the Inputs spec below.

**Never** disable focus rings on custom controls. If a ring clashes with an animation, change the animation — not the ring.

---

## Components

### Buttons

All buttons: `font-body`, `font-weight: 700`, `rounded-lg`, press feedback `scale(0.97)`.

| Variant | Background | Text Color | Height | Padding | Usage |
|---------|-----------|------------|--------|---------|-------|
| **Primary** | `accent-thrive` (#7DD4A3) | `text-inverse` | 48px | 0 28px | Main CTAs: "Build My Future" |
| **Secondary** | transparent | `accent-info` | 44px | 0 24px | Secondary: "Compare Builds" |
| **Ghost** | transparent | `text-secondary` | 40px | 0 16px | Tertiary: "Go Back" |
| **Danger** | `accent-alert` at 15% opacity | `accent-alert` | 44px | 0 24px | Destructive: "Delete Save" |
| **Icon** | `bg-surface` | `text-primary` | 40px | 0 | Circular. Close buttons, toggles. |

**Hover states:**
- Primary: darken to `#6bc494`, add `shadow-glow-thrive`
- Secondary: add `rgba(123, 184, 224, 0.1)` background
- Ghost: text brightens to `text-primary`, add `rgba(255, 255, 255, 0.05)` background
- Danger: background opacity increases to 25%
- Icon: background shifts to `bg-raised`

### Cards

The primary content container. All cards share base DNA.

**Base Card:**
```
background: bg-mid (#232545)
border: 1px solid border-subtle (rgba 255,255,255,0.06)
border-radius: radius-xl (20px)
padding: 24px
shadow: shadow-md
transition: all 200ms ease-out
```

**Hover:**
```
background: bg-surface (#2D3060)
border-color: border-default (rgba 255,255,255,0.1)
shadow: shadow-lg
transform: translateY(-2px)
```

**Selected:**
```
border-color: rgba(125, 212, 163, 0.4)
shadow: 0 0 20px rgba(125, 212, 163, 0.15)
```

**Card typography:**
- Label: `font-data`, 11px, `text-muted`, uppercase, letter-spacing 1px
- Title: `font-display`, weight 600, 20px
- Description: `font-body`, 14px, `text-secondary`
- Stat value: `font-data`, weight 700, 24px

**Card variants:**
- **Career Card** — label + title + description + stat pills
- **Selected Card** — thrive border glow, title in accent-thrive
- **Boss Result Card** — boss name + result description + win/lose pill
- **Character Card** — large emoji/portrait, name, vibe text. 2px transparent border, selected = thrive border + glow + scale(1.08)
- **Save Slot Card** — horizontal layout: avatar + info (name, meta) + date. Hover slides right 4px.

### Pills / Badges

Inline status indicators. Each accent color has a pill variant.

```
display: inline-flex
align-items: center
gap: 6px
font-size: 13px
font-weight: 600
padding: 5px 14px
border-radius: radius-full
```

| Variant | Background | Text Color | Usage |
|---------|-----------|------------|-------|
| pill-thrive | `rgba(125, 212, 163, 0.15)` | accent-thrive | Win states |
| pill-alert | `rgba(244, 169, 126, 0.15)` | accent-alert | Lose states |
| pill-caution | `rgba(242, 212, 119, 0.15)` | accent-caution | Draw states |
| pill-insight | `rgba(184, 169, 232, 0.15)` | accent-insight | AI-related |
| pill-info | `rgba(123, 184, 224, 0.15)` | accent-info | Stage indicators |
| pill-empathy | `rgba(232, 139, 169, 0.15)` | accent-empathy | Human edge |

**Pattern:** accent color at 15% opacity for background, full accent for text.

**Feasibility glyph convention:** When a pill is used to classify a target (e.g., "is this career reachable from this school"), prefix the label with a semantic glyph. Pills without these glyphs are decorative; pills with them are taxonomic and must follow the convention.

| Glyph | Name | Semantic |
|-------|------|----------|
| `◆` | filled diamond | Present / reachable. The thing exists here. Pair with `pill-thrive` or `pill-caution`. |
| `◇` | open diamond | Absent / unreachable. The thing isn't here. Pair with `pill-alert` or `pill-empathy`. |

Examples: `◆ direct hit`, `◆ Through Business program`, `◇ not here`. The glyph carries the meaning; the color carries the temperature.

### Inputs

**Standard Input:**
```
background: bg-deep (#1B1D30)
border: 1px solid border-default
border-radius: radius-md (10px)
padding: 12px 16px
font: Nunito 16px
color: text-primary
height: 48px
```

**Focus:**
```
border-color: accent-info (#7BB8E0)
box-shadow: 0 0 0 3px rgba(123, 184, 224, 0.15)
```

**Large variant (school search):**
```
height: 56px
font-size: 18px
border-radius: radius-lg (14px)
search icon: text-muted, left-aligned inside input
```

**Input label:**
```
font-family: font-body (Nunito)
font-size: 14px
font-weight: 600
color: text-secondary
margin-bottom: 6px
```

**Autocomplete Dropdown:**
```
background: bg-mid
border: 1px solid border-default
border-radius: radius-lg (14px)
shadow: shadow-lg
max-height: 320px
overflow: hidden (outer), overflow-y auto (inner)
margin-top: 4px
```

Each dropdown row:
```
padding: 12px 18px
display: flex
justify-content: space-between
align-items: center
border-bottom: 1px solid border-subtle (last row: none)
border-left: 3px solid transparent (reserves space)
transition: background 150ms ease-out
```

- **School name**: `font-body`, weight 600, 15px, `text-primary`
- **City, State**: `font-data`, 11px, `text-muted`, right-aligned

States follow the **List Item** pattern below.

### List Items

Reusable interaction pattern for any selectable row in a list (dropdowns, program pickers, branch lists, save slots).

```
padding: 12px 18px
display: flex
justify-content: space-between
align-items: center
border-bottom: 1px solid border-subtle (last row: none)
cursor: pointer
transition: background 150ms
```

**Default:** transparent background
**Hover:** `background: bg-surface`
**Highlighted / Selected:** `background: rgba(125, 212, 163, 0.1)`, `border-left: 3px solid accent-thrive`

### Gemma Interactions

A family of primitives that give every Gemma touchpoint the same visual grammar — same icon, same gradient, same attribution font. Whenever Gemma is called, compose from this family rather than styling ad hoc.

**Shared tokens:**
- Attribution color ramp: `accent-info` → `accent-insight` linear gradient (info→insight). Used on every Gemma mark.
- Attribution typography: `font-body` Nunito, `text-small` (14px), `text-secondary`. Never Fredoka — Fredoka is for headlines.
- Surface tint for glows and washes: `rgba(184, 169, 232, x)` (insight at low alpha).

**Primitives:**

| Primitive | File | Usage |
|-----------|------|-------|
| `GemmaStar` | `components/ui/GemmaStar.tsx` | Static four-pointed star, 14px default. Attribution prefix on any line that names Gemma ("Gemma matched…", "Let's find the right one"). |
| `GemmaSpinner` | `components/ui/GemmaSpinner.tsx` | Animated star inside a rotating ring + crosshair with a breathing insight glow. 28–40px. The universal "Gemma is working" mark. |
| `GemmaThinking` | `components/ui/GemmaThinking.tsx` | Composed inline status: `GemmaSpinner` + attribution text ("Gemma is …ing …"). `gap-3`, `font-body text-small text-text-secondary`. The canonical in-flight indicator — reuse for every inline Gemma call (see `/school` major input). |

**Usage pattern — thinking state:**
```tsx
<AnimatePresence>
  {phase === "thinking" && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.4 }}  // collapse into resulting card
      transition={{ duration: 0.25, ease: "easeIn" }}
    >
      <GemmaThinking message="Gemma is matching your input..." />
    </motion.div>
  )}
</AnimatePresence>
```

The scale-0.4 exit is the signature "energy transfer" — the spinner collapses and the match card bounces in from its position. Keep this pattern whenever a Gemma call resolves into a card.

**Usage pattern — attribution line:**
```tsx
<div className="flex items-center gap-2">
  <GemmaStar size={14} />
  <span className="text-small text-text-muted">
    Gemma matched "<span className="font-semibold text-text-secondary">{input}</span>"
  </span>
</div>
```

**Message conventions:**
- In-flight: third-person present continuous — "Gemma is matching your input…", "Gemma is writing your action plan…", "Gemma is analyzing your build…"
- Resolved: past tense — "Gemma matched …", "Gemma found …"
- Errors: capability-framed, never blame — "Gemma couldn't match that" (not "Bad input")

### Gemma Match Card

The confirmation card that appears after Gemma resolves free-text input to a CIP program. Shows the matched program, a preview of career outcomes, and confirm/reject actions.

**Container:**
```
background: bg-mid (#232545)
border: 1px solid rgba(255, 255, 255, 0.5)
border-radius: radius-xl (20px)
padding: 24px
glow: breathing animation — box-shadow pulses between
  0 0 24px rgba(184, 169, 232, 0.12) and
  0 0 36px rgba(184, 169, 232, 0.25) on a 4s ease-in-out cycle
```

**Entrance animation:** `springs.bouncy`, scale 0.85 -> 1, opacity 0 -> 1, y 12 -> 0. Spinner collapses (scale 0.4) on exit to transfer energy into the card.

**Color semantics — Gemma matches wear their voice in color:**

| State | Title color | Why |
|-------|-------------|-----|
| Default (high/med confidence) | `accent-insight` | Insight = Gemma's color (same as spinner, glow, RES stat). A Gemma-chosen title looks different from a user-chosen title. |
| Low confidence | `accent-caution` | Matches the caution breathing glow and "best guess" pill. |
| Confirming (320ms flash) | `accent-thrive` | Reward moment. Title flashes green + CTA adds a thrive glow (`0 0 24px rgba(125,212,163,0.45)`) right before handoff. |

This is the pattern for content-level accent use: when a color means something semantically (Gemma, growth, warning), content itself carries it — not just chrome.

**Container edge:** 3px left border in the title's accent color (`accent-insight` default, `accent-caution` low-confidence, `accent-thrive` confirming). Same pattern as `GemmaTake` — a visible "this is Gemma's" stripe on every card Gemma produces.

**Zones:**
- **Attribution:** Static GemmaStar icon (14px, info-to-insight gradient) + "Gemma matched `"{input}"`" in `text-small text-text-muted`, raw user text in `font-semibold text-accent-insight` (or `text-accent-caution` low-confidence). The quoted input echoes the match color — Gemma's voice in the user's own words.
- **Title:** `font-display text-subheading font-semibold`. Slides in from x:-8 and brightens from `text-muted` to the title color above (see table). 400ms transition on entrance, 200ms on confirm flash. CIP code below in `font-data text-data-sm text-text-muted`.
- **Career preview:** Section label pattern ("WHERE THIS LEADS"). Career rows: `font-body text-body-sm font-semibold text-accent-info` by default (tinted, readable) — brighten to `text-primary` on hover. Info-colored arrow prefix. Stagger at `stagger.fast` (50ms).
- **Warning (conditional):** `border-t border-border-subtle`, `text-small text-accent-caution italic`
- **Actions:** Primary button ("That's right") + Ghost button ("Not quite") per Button spec. Delayed entrance at 700ms. On confirm: disable both buttons, set 320ms timer, flash title+CTA to thrive, then hand off.

**Low confidence variant:**
- Glow shifts to caution: pulses between `0 0 24px rgba(242, 212, 119, 0.10)` and `0 0 36px rgba(242, 212, 119, 0.22)`
- Title color: `accent-caution` (see table above)
- Caution pill badge ("best guess") on metadata row next to CIP code
- Confirm button label changes to "Close enough"
- "Not quite" button text brightens to `text-primary`

### Tiered Match Card (Three-Confidence Extension)

Added 2026-04-18 (see `docs/specs/feature-gemma-tiered-matching.md`). The Match Card is now driven by three discrete confidence tiers Gemma self-reports on every response.

| Tier | Routing | Card Variant | Alternatives List |
|------|---------|--------------|-------------------|
| `high` | Match card | Default (insight) — unchanged from above | Never shown |
| `medium` | Match card | Caution variant (rules above) + **inline alternatives list** | 2–4 rows rendered inside the card |
| `low` | Clarify picker | Card never mounts; parent routes to `ClarifyContent` | N/A |

The caution variant block above was previously unreachable (low tier rendered the picker, not the card). It is now **the medium-tier variant**. All of its tokens, glow values, pill copy, and button labels apply to the medium tier — the only addition is the alternatives list block below. The low tier still renders the clarify picker.

**Alternatives list** (medium tier, 2–4 rows):

The list renders *inside* the match card, between the career preview and the actions row. It reuses the career preview's visual grammar — same section-label treatment, same glyph, same accent-info-default / text-primary-on-hover pattern — so the card reads as one coherent Gemma artifact rather than three stacked components.

```
Section top rule:    border-t border-border-subtle, 18px margin-top + 16px padding-top
Section label:       font-data text-[11px] font-bold tracking-[2px] uppercase
                     text-accent-info — "OR — ONE OF THESE?"
Row container:       <ul role="list"> with aria-label="Other close matches"
Row dividers:        border-t border-border-subtle (first row has no rule)
Row button:          py-3 mobile:py-2, px-3, flex-col mobile:flex-row, hover:bg-bp-surface
Row glyph:           ▸ in text-accent-info/60, group-hover text-accent-info
Row title:           font-body text-body-sm font-semibold text-accent-info
                     group-hover text-text-primary, truncated
Row why:             font-body text-small text-text-muted, inline right-aligned on
                     desktop (max-w-[280px] truncate), stacked below title on mobile
Confirm flash:       320ms thrive — title + glyph animate to text-accent-thrive,
                     box-shadow "0 0 24px rgba(125,212,163,0.45)" (literal reuse of
                     primary CTA glow value), backgroundColor holds at bg-surface
Siblings during flash: opacity 0.45 (primary CTA included), disabled state
Entrance:            delay 0.55s, stagger 50ms per row, springs.smooth, y 12 -> 0
```

**Accessibility:**
- `<ul role="list" aria-label="Other close matches">` wraps the rows.
- Each row is a `<button type="button" aria-label="Select {title}">`. CIP is intentionally omitted from the spoken label to keep screen-reader cadence clean.
- During confirm, `disabled` flips on all rows and CTAs — screen readers announce disabled state.
- Keyboard: `Tab` cycles through rows, `Enter`/`Space` confirms.

**Degenerate state:** Medium tier with zero alternatives (Gemma returned an empty or filtered-out list) renders the caution card with the primary match alone, no alternatives section, no top rule. The card is *not* downgraded to insight/high styling — caution honestly reflects Gemma's self-reported confidence even when its alternatives pool was unhelpful.

**Copy:** Section label is `"OR — ONE OF THESE?"` — the `OR` ties it conversationally to the primary pick, the em-dash creates a thoughtful-advisor pause, and the `?` signals invitation rather than catalog. Matches the 2-letterspaced all-caps `font-data` rhythm of the sibling `"WHERE THIS LEADS"` label.

### The Pentagon (Radar Chart)

The five-stat radar chart. Recurring element across multiple screens.

- **Grid:** 4 concentric pentagons at 100%, 80%, 60%, 40% of max radius. Stroke: `text-muted` at 15% opacity.
- **Axes:** 5 lines from center to each vertex. Stroke: `text-muted` at 20% opacity.
- **Filled polygon:** Radial gradient from `bg-surface` (center) to `accent-thrive` at 40% opacity (edge). Fill opacity 35%.
- **Vertex dots:** 5px radius circles in stat color, with 10px glow circles at 20% opacity.
- **Labels:** Outside each vertex. `font-display`, weight 600, 14px, colored by stat.
- **Legend row:** stat dot (12px) + abbreviation (`font-data`, 12px, `text-muted`) + name (`font-display`, 15px) + value (`font-data`, 18px, stat color).
- **Reveal animation:** Pentagon draws from center outward with `springs.smooth`, stagger 100ms per axis.

### The Effort Slider

Custom range input for self-assessment.

- **Track:** 6px height, `bg-deep`, `radius-full`
- **Fill:** Linear gradient from `accent-info` (left/low) to `accent-thrive` (right/high)
- **Thumb:** 28px circle, `bg-raised`, 3px `text-primary` border, `shadow-glow-info`. Hover: `shadow-glow-thrive`.
- **Question:** `font-display`, weight 600, 22px, centered
- **Labels:** "Working to support myself" (left) / "Full focus on school" (right), 13px, `text-muted`
- **Current value:** `font-data`, 14px, weight 700, `accent-thrive`
- **Stats preview:** ERN / ROI / RES values update in real-time. `font-data`, weight 700, 28px, stat colors.

### Boss Cards (Preview Grid)

Grid of boss fight previews shown before the gauntlet begins.

```
background: bg-mid
border: 1px solid border-subtle
border-radius: radius-xl
padding: 24px 20px
text-align: center
```

Each boss card has a radial gradient overlay using its boss color at 8% opacity. Contains:
- **Icon:** 56px circle with boss color at 15% opacity background, centered emoji 28px
- **Name:** `font-display`, weight 600, 16px
- **Description:** 12px, `text-muted`

Hover: `translateY(-3px)`, `border-default`

### Boss Band (Battle Report Card)

The full-width boss fight result card used in the Build Results gauntlet. Replaces the preview grid with detailed per-fight reporting. Each band scrolls into view, plays a VS animation, then reveals the result.

**Container:**
```
background: bg-mid
border-radius: radius-xl
padding: 24px (mobile: 18px)
min-height: 140px
overflow: hidden
position: relative
scroll-snap-align: center
```

**Dual edge stripes** — `::before` (left) and `::after` (right), each 4px wide, absolute top-to-bottom:
- Left stripe = boss color gradient: `rgba({boss-color}, 0.7)` at top → `rgba({boss-color}, 0.15)` at bottom
- Right stripe = result color gradient: `rgba({result-color}, 0.5)` at top → `rgba({result-color}, 0.1)` at bottom, plus inward glow `box-shadow: -8px 0 24px rgba({result-color}, 0.12)`

**Result-tinted borders** (applied after VS reveal):
- Win: `1px solid rgba(125, 212, 163, 0.18)`
- Lose: `1px solid rgba(244, 169, 126, 0.20)`
- Draw: `1px solid rgba(242, 212, 119, 0.18)`

**Result words:** `font-display`, 700, 22px, uppercase, letter-spacing 1px:
- VICTORY: `accent-thrive` + `text-shadow: 0 0 20px rgba(125,212,163,0.3)`
- DEFEATED: `accent-alert` + `text-shadow: 0 0 20px rgba(244,169,126,0.25)`
- STANDOFF: `accent-caution` + `text-shadow: 0 0 20px rgba(242,212,119,0.25)`

**Reveal stagger** (transition-delay after VS completes):
- Portrait: 0ms
- Info: 80ms
- Result zone: 180ms
- Narrative panel: 320ms
- Reroll section: 460ms

**Micro-animations** (fire after reveal):
- `winPulse`: green glow `box-shadow 0 → 32px → 0` at `rgba(125,212,163,0.25)`, 0.6s
- `loseShake`: horizontal shake `translateX(0, -3, 3, -2, 1, 0)`, 0.4s
- `drawWobble`: rotation `0° → 1.5° → -1.5° → 0°`, 0.4s

**Narrative panel** (Gemma's fight analysis):
```
background: rgba(27, 29, 48, 0.6)
border-left: 3px solid {boss-color}
border-radius: radius-lg
padding: 20px
margin-top: 16px
font-size: 15px, line-height: 1.65, text-primary
```

#### Boss Naming Pattern

Two name formats per boss — full name for the card header, short name for the VS overlay.

| Boss | Full Name (card header) | Short Name (VS overlay) |
|------|------------------------|------------------------|
| Fight AI | "{FirstName} vs. AI" | "AI" |
| Student Loans | "{FirstName} vs. Student Loans" | "Student Loans" |
| The Market | "{FirstName} vs. the Market" | "The Market" |
| Burnout | "{FirstName} vs. Burnout" | "Burnout" |
| The Ceiling | "{FirstName} vs. the Ceiling" | "The Ceiling" |

`{FirstName}` is the character's first name (e.g. "Snappy" from "Snappy Purple Turtle"). Articles ("the") appear in the full name only for bosses that read naturally with them. Short names omit the player name and article.

#### Sealed State

The pre-reveal state of a Boss Band before the VS animation triggers. Shows boss identity but hides the fight result.

**Sealed overlay:**
```
position: absolute, inset: 0, z-index: 5
display: flex, align-items: center, gap: 16px
padding: 24px
border-radius: radius-xl
background: bg-mid
transition: opacity 0.15s ease-out
```

**Sealed portrait:** 64px square, `radius-lg`, boss gradient background (`rgba({boss-color}, 0.30)` → `rgba({boss-color}, 0.12)` at 135deg), 1px boss-color border at 25% opacity. Filter: `saturate(0.3) brightness(0.7)`. Animation: `sealedPulse` — opacity oscillates `0.7 ↔ 0.85`, 2s ease-in-out infinite.

**Sealed shimmer:** Light sweep gradient overlay, fires once when the card first enters the viewport (threshold 0.1). `sealedShimmer` keyframe: `translateX(-100%)` → `translateX(200%)`, 0.6s ease-out forwards. Gradient: `transparent → rgba(255,255,255,0.05) → rgba(255,255,255,0.08) → rgba(255,255,255,0.05) → transparent`.

**Sealed hold:** Brief scale-up before VS fires. `transform: scale(1.02)`, 200ms transition with `cubic-bezier(0.34, 1, 0.64, 1)`. Also intensifies the left boss stripe via `filter: brightness(1.5)` on `::before`.

**Pre-trigger:** neutral `border-subtle` border, dual edge stripes at `opacity: 0`. Stripes and result borders only appear after `.sealed-triggered` class is added.

### Campus Hero Banner

Full-bleed atmospheric banner showing the campus image at the top of the Build Results screen. Creates a sense of place before revealing the character.

**Container:**
```
position: relative
width: 100%
height: 280px (mobile: 200px)
overflow: hidden
animation: heroFadeIn 0.8s ease-out both
```

**Image:**
```
width: 100%, height: 100%
object-fit: cover
object-position: center 40%
display: block
```

**Gradient fade** (bottom overlay that blends into the page):
```
position: absolute
bottom: 0, left: 0, right: 0
height: 180px
background: linear-gradient(
  180deg,
  transparent 0%,
  rgba(27, 29, 48, 0.5) 35%,
  #1B1D30 100%
)
pointer-events: none
```

### Character Identity Block

Horizontal identity strip that overlaps the bottom of the Campus Hero Banner. Shows the character avatar, name, and program subtitle.

**Container:**
```
position: relative, z-index: 2
max-width: 1280px
margin: -48px auto 0 (mobile: -32px)
padding: 0 32px (mobile: 0 16px)
display: flex
align-items: center
gap: 24px (mobile: 16px)
```

**Avatar:**
```
width: 120px, height: 120px (mobile: 80px)
border-radius: 50%
border: 2px solid border-default
background: emoji-specific accent color (see EMOJI_BG lookup)
display: flex, align-items: center, justify-content: center
box-shadow:
  0 0 30px 6px rgba(125, 212, 163, 0.15),
  0 0 60px 12px rgba(184, 169, 232, 0.08)
animation: emojiBounce 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.5s both
```

Emoji-to-background-color lookup:

| Emoji | Background |
|-------|-----------|
| Bear | `accent-caution` |
| Bunny | `accent-insight` |
| Turtle | `accent-info` |
| Chipmunk | `accent-thrive` |
| Fox | `accent-insight` |
| Owl | `accent-caution` |
| Penguin | `accent-info` |
| Cat | `accent-alert` |

**Name:** `font-display`, 700, 40px (mobile: 28px), `text-primary`, `line-height: 1.2`
**Subtitle:** `font-body`, 600, 18px (mobile: 16px), `text-secondary`, `text-shadow: 0 1px 3px rgba(18, 19, 31, 0.6)`

### Character Select Cards

Grid of selectable animal characters.

```
background: bg-mid
border: 2px solid transparent
border-radius: radius-xl
padding: 20px 16px
text-align: center
min-width: 140px
```

- **Emoji:** 48px
- **Name:** `font-display`, weight 600, 15px
- **Vibe:** 12px, `text-muted`

**Hover:** `bg-surface`, `scale(1.05)`
**Selected:** `border-color: accent-thrive`, `shadow: 0 0 24px rgba(125, 212, 163, 0.2)`, `scale(1.08)`

### Save Slot Cards

Horizontal RPG save-file layout.

```
background: bg-mid
border: 1px solid border-subtle
border-radius: radius-lg
padding: 16px 20px
display: flex
align-items: center
gap: 16px
```

- **Avatar:** 36px emoji
- **Name:** `font-display`, weight 600, 16px, accent-colored
- **Meta:** 13px, `text-secondary`
- **Date:** `font-data`, 11px, `text-muted`
- **Empty slot:** 40% opacity, dashed border

**Hover:** `bg-surface`, `translateX(4px)`

### Section Labels

Uppercase category markers above section headings.

```
font-family: font-data (Space Mono)
font-size: 11px
font-weight: 700
letter-spacing: 2px
text-transform: uppercase
color: accent-info
margin-bottom: 8px
```

### Path Card

Compact vertical card showing the student's program and primary career outcome with inline stat bars. Used in the Build Results screen alongside the Institution Card.

**Container:**
```
background: bg-mid
border: 1px solid border-subtle
border-radius: radius-xl
padding: 24px
```

**Label:** section-label pattern (`font-data`, 11px, 700, uppercase, `accent-info`, letter-spacing 2px, margin-bottom 16px)

**Path entry row:**
```
display: flex
align-items: flex-start
gap: 12px
padding: 12px 0
border-bottom: 1px solid border-subtle (last entry: none)
```

- **Emoji:** 28px, `line-height: 1`, flex-shrink 0
- **Title:** `font-display`, 600, 16px, `text-primary`, `line-height: 1.3`
- **Code:** `font-data`, 11px, `text-muted`, `letter-spacing: 0.5px`
- **Wage:** `font-data`, 14px, 700, `stat-ern`, margin-top 6px

**Stat bars block:** 2-column grid (mobile: 1-column), `gap: 6px 16px`, `margin-top: 16px`, `padding-top: 16px`, `border-top: 1px solid border-subtle`

### Stat Bar Row

Compact horizontal stat indicator with label, track, fill, and value. Used inside Path Cards and anywhere a dense stat readout is needed.

```
display: flex
align-items: center
gap: 8px
```

- **Label:** `font-data`, 11px, 700, uppercase, stat color, `width: 28px`, flex-shrink 0
- **Track:** `flex: 1`, `height: 4px`, `radius-full`, `background: bg-deep`, `overflow: hidden`
- **Fill:** `height: 100%`, `radius-full`, stat color, `opacity: 0.8`, `transition: width 0.4s ease-out`
- **Value:** `font-data`, 11px, `text-secondary`, `width: 16px`, `text-align: right`, flex-shrink 0

### Institution Card

Gemma-authored narrative card providing context about the student's school. Used in the Build Results screen alongside the Path Card.

**Container:**
```
background: bg-mid
border: 1px solid border-subtle
border-radius: radius-xl
padding: 24px
```

- **Label:** section-label pattern (`font-data`, 11px, 700, uppercase, `accent-info`, letter-spacing 2px, margin-bottom 12px)
- **Name:** `font-display`, 700, 22px, `text-primary`, margin-bottom 16px
- **Narrative:** `font-body`, 15px, `line-height: 1.65`, `text-secondary`. Paragraphs: `margin-bottom: 12px` (last: 0)
- **Gemma tag:** inline-flex, gap 5px, `font-data`, 11px, `text-muted`, `letter-spacing: 0.5px`. Content: "✦ Written by Gemma"

### Victory Bar

Visual summary of gauntlet fight outcomes — 5 cells representing wins (decisive and skill-assisted), draws, and losses.

**Container:**
```
display: flex
gap: 6px
max-width: 320px
margin: 20px auto 0
```

**Cell:**
```
flex: 1
height: 12px
border-radius: radius-full
transition: background, border-color, box-shadow (all 0.3s ease-out)
```

| Cell Type | Class | Background | Extra |
|-----------|-------|-----------|-------|
| Decisive win | `.raw` | `accent-thrive` | `box-shadow: 0 0 8px rgba(125,212,163,0.25)` |
| Skill-assisted win | `.equipped` | `accent-insight` | `box-shadow: 0 0 8px rgba(184,169,232,0.25)` |
| Draw | `.draw-cell` | `accent-caution` | `opacity: 0.4` |
| Loss | `.loss` | `bg-deep` | `border: 1px solid border-default` |

**Legend** (below bar):
```
display: flex, justify-content: center, gap: 16px, margin-top: 10px
```

Each item: 8px dot (`radius-full`, matching cell color) + label (`font-data`, 11px, `text-muted`). Labels: "Decisive", "Skill-assisted", "Unresolved". Only show types that appear in the current result.

### Verdict Badge

Career readiness summary shown after the gauntlet. Displays a tier word, victory bar, tally, and Gemma-authored narrative.

**Container:**
```
background: bg-mid
border-radius: radius-xl
padding: 32px (mobile: 24px)
text-align: center
animation: verdictScaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both
```

**Tier variants** (border + glow):

| Tier | Class | Border | Box Shadow | Color |
|------|-------|--------|-----------|-------|
| Dominant | `.dominant` | `rgba(125,212,163,0.3)` | `0 0 20px rgba(125,212,163,0.15)` | `accent-thrive` |
| Solid | `.solid` | `rgba(125,212,163,0.25)` | `0 0 16px rgba(125,212,163,0.10)` | `accent-thrive` |
| Mixed | `.mixed` | `rgba(242,212,119,0.25)` | `0 0 16px rgba(242,212,119,0.10)` | `accent-caution` |
| Vulnerable | `.vulnerable` | `rgba(244,169,126,0.25)` | `0 0 16px rgba(244,169,126,0.10)` | `accent-alert` |

**Anatomy:**
- **Label:** "CAREER READINESS" — `font-data`, 11px, 700, letter-spacing 2px, uppercase, `text-muted`
- **Word:** `font-display`, 700, 32px (mobile: 24px), tier color. Format: `"{TIER} BUILD"` — e.g. "DOMINANT BUILD", "SOLID BUILD", "MIXED BUILD", "VULNERABLE BUILD"
- **Subtitle:** `font-body`, 16px, `text-secondary`
- **Victory Bar:** (see Victory Bar component above)
- **Tally:** `font-data`, 13px, `text-secondary`. Format: `"{X} of 5 victories (Y decisive + Z skill-assisted)"`. Win counts colored `accent-thrive`, equipped counts colored `accent-insight`.
- **Narrative:** `font-body`, 15px, `text-secondary`, `line-height: 1.6`, `max-width: 520px`, auto-centered. Dynamic copy based on win/loss distribution.

**Entrance:** `verdictScaleIn` — `scale(0.85) → scale(1)`, `opacity 0 → 1`, bouncy cubic-bezier.

### Stat Info Popover

Contextual explanation popover for pentagon stats. Triggered by a "?" button next to each stat name.

**Trigger button:**
```
width: 18px, height: 18px
border-radius: radius-full
border: 1.5px solid border-default
background: transparent
color: text-muted
font-family: font-body
font-size: 11px
font-weight: 700
cursor: pointer
opacity: 0.6
content: "?"
```

**Trigger states:**
- Hover: `opacity: 1`, `border-color: border-strong`, `color: text-secondary`, `background: rgba(255, 255, 255, 0.04)`
- Active (`aria-expanded="true"`): `opacity: 1`, `border-color: accent-info`, `color: accent-info`, `background: rgba(123, 184, 224, 0.08)`

**Popover:**
```
background: bg-raised
border: 1px solid border-default
border-left: 3px solid {stat-color}
border-radius: radius-lg
padding: 20px
box-shadow: shadow-lg
margin-top: 8px
z-index: 50
```

- **Title:** `font-display`, 14px, 600, `text-primary`
- **Body:** `font-body`, 14px, `line-height: 1.5`, `text-secondary`
- **Source:** `font-data`, 11px, `text-muted`, `letter-spacing: 0.5px`, margin-top 10px

**Entrance:** `popoverIn` — `translateY(-6px) → translateY(0)`, `opacity 0 → 1`, 180ms cubic-bezier(0.34, 1.4, 0.64, 1)
**Exit:** `popoverOut` — reverse, 150ms ease-in
**Close on:** click outside, Escape key, or clicking the same trigger again

### Skill Card

Interactive card for equipping skills during boss fight reroll. Shown in a 3-column grid (2-col at 680px, 1-col at 440px) inside the reroll section of a Boss Band.

**Container:**
```
display: flex
flex-direction: column
gap: 6px
padding: 12px 14px
min-height: 72px
background: bg-mid
border: 1px solid border-default
border-radius: radius-lg
cursor: pointer
transition: all 150ms ease-out
user-select: none
position: relative
```

**States:**
- **Hover:** `border-color: border-strong`, `background: rgba(45, 48, 96, 0.5)`, `transform: translateY(-1px)`
- **Selected:** `border-color: rgba(125, 212, 163, 0.5)`, `background: rgba(125, 212, 163, 0.06)`, dual glow: `box-shadow: 0 0 16px rgba(125,212,163,0.12), inset 0 0 12px rgba(125,212,163,0.04)`

**EQUIPPED badge** (selected state, `::after`):
```
position: absolute
top: 8px, right: 8px
font-family: font-data
font-size: 10px
font-weight: 700
letter-spacing: 0.05em
color: accent-thrive
background: rgba(125, 212, 163, 0.15)
padding: 2px 8px
border-radius: radius-full
```

**Title:** `font-display`, 600, 14px, `text-primary`, `padding-right: 60px` (room for badge)

#### Skill Stat Badge

Inline badge showing a stat bonus (e.g. "ERN +1"). Used inside Skill Cards.

```
font-family: font-data
font-size: 11px
font-weight: 700
letter-spacing: 0.3px
padding: 2px 8px
border-radius: radius-full
line-height: 1.4
color: {stat-color}
background: rgba({stat-color}, 0.15)
```

### Application Header

Fixed top bar with frosted glass treatment. Three-zone layout: left (navigation), center (identity), right (contextual actions). The header is the only persistent chrome in the app — it fades in after Screen 1 and adapts per screen.

**Base:**
```
position: fixed
top: 0; left: 0; right: 0
height: 56px
background: rgba(18, 19, 31, 0.92)
backdrop-filter: blur(12px)
border-bottom: 1px solid border-subtle
padding: 0 32px
z-index: 100
```

**Layout:**
```
+----------------------------------------------------------+
| [Left Zone]       [Center Zone]          [Right Zone]     |
+----------------------------------------------------------+
```

- **Left zone:** Back arrow (ghost icon button) during linear flow. Home icon during hub mode (Screen 10+). Empty on screens where back is not possible.
- **Center zone:** Profile name + emoji. `font-body`, `text-small` (14px), weight 600, `text-muted` on Screens 2-5. Brightens to `text-secondary` after the reveal (Screen 6+). On Screen 1: empty or small wordmark.
- **Right zone:** Empty during linear flow. "New Build" pill button appears in hub mode (`accent-info` border, `text-small`).

**Screen states:**

| Screen | Header | Left | Center | Right |
|--------|--------|------|--------|-------|
| 1 Landing | Hidden | — | — | — |
| 2 Profile | Fades in | Empty | Wordmark | Empty |
| 3-5 Input | Visible | Back arrow | Profile name (`text-muted`) | Empty |
| 6 Reveal | Visible | Back arrow | Profile name (`text-secondary`) | Empty |
| 7 Gauntlet | Dimmed (60%) | Back (dimmed) | Profile (dimmed) | Empty |
| 8 Branch Tree | Void-blended | Back arrow | Profile (`text-secondary`) | Empty |
| 9 Save | Visible | Back arrow | Profile (`text-secondary`) | Empty |
| 10 Menu | Visible | Home icon | Profile (`text-secondary`) | "New Build" |

**Cinematic states:**
- **Dimmed (boss gauntlet):** background opacity drops to 60%, border fades to `rgba(255, 255, 255, 0.02)`, profile name opacity 0.4
- **Void-blended (branch tree):** header matches `bg-void` background, content renders underneath (no padding-top offset)

**Entrance animation:** Fades in on Screen 2 with `springs.smooth`, delay 0.3s, from y:-20. The profile name appears in the hero position first — the header echo follows.

**Mobile (below tablet breakpoint):** Same 56px height. Profile name truncates with ellipsis if needed (emoji never truncates). Touch targets minimum 44px. No bottom tab bar — CTAs at bottom of screen content are the forward navigation.

### Modals

```
background: bg-mid
border-radius: radius-xl
max-width: 560px
padding: 32px
shadow: shadow-lg
backdrop: rgba(18, 19, 31, 0.85) with backdrop-blur(8px)
entrance: scale from 0.95, opacity from 0, springs.smooth
```

### Chips

Interactive, selectable category pills — distinct from read-only Pills/Badges. Chips invite the student to redirect, refine, or challenge. The canonical composition is a **chip rail**: one primary chip that opens the hero action, one or more ghost chips for alternates, and an optional dashed separator above. Introduced with the Set Your Course screen — reuse for any "something feel off?" style redirect.

**Base chip:**
```
display: inline-flex
align-items: center
gap: 6px
padding: 10px 18px
border-radius: radius-full
font-family: font-body
font-size: text-small (14px)
font-weight: 600
transition: background, border-color, transform, box-shadow (all fast)
```

**Variants:**

| Variant | Background | Border | Text | Weight | Usage |
|---------|-----------|--------|------|--------|-------|
| **primary** | `rgba(242, 212, 119, 0.12)` (caution @ 12%) | `rgba(242, 212, 119, 0.28)` | `accent-caution` | 700 | Hero redirect ("Not what I expected"). One per rail. Adds `shadow-sm`. |
| **ghost** | transparent | `border-default` | `text-secondary` | 600 | Alternate redirects ("Show me less common paths", "Wrong major"). |

**Hover (primary):** background → `rgba(242, 212, 119, 0.18)`, border → `rgba(242, 212, 119, 0.42)`, add `0 0 20px rgba(242, 212, 119, 0.18)`, `translateY(-1px)`.
**Hover (ghost):** background → `rgba(255, 255, 255, 0.04)`, border → `border-strong`, text → `text-primary`.
**Press:** `scale(0.97)` via `transitions.press`. Applies to all variants.

**Ghost toggled-on ("active"):** For ghost chips that represent a toggleable state (canonical use: "Show me less common paths" reveals/hides stretch tiers). When on:
- Background → `--color-state-active` (thrive @ 10%)
- Border → `rgba(125, 212, 163, 0.28)`
- Prepend a `✓` glyph in `text-accent-thrive` to the label
- `aria-pressed="true"` on the button

Tapping again reverts to default. This is the only chip state that *persists* between interactions — the primary's pulsing, hover, and press are all transient.

**Disabled:** background → `--color-state-disabled`, text → `text-muted`, any prefix glyph desaturates to `text-muted`, `cursor: not-allowed`, no hover. Use `aria-disabled="true"` — **not** the HTML `disabled` attribute — so screen readers still announce the chip and its context.

**Low-confidence state:** Add `.animate-chip-pulse-caution` to the primary chip. Softly pulses its box-shadow to signal "Gemma wasn't sure — worth a look." Paired with the Commit Bar nudge whisper (below).

**A/B label tag:** When comparing copy variants side-by-side, the middle ghost chip can carry a tiny label tag inside it:
```
display: inline-flex
padding: 2px 8px
font-family: font-data
font-size: 10px
letter-spacing: 1px
text-transform: uppercase
border-radius: radius-full
margin-right: space-2
```
Variant colorways: `variant-a` → `accent-info` on `rgba(123, 184, 224, 0.12)`; `variant-b` → `accent-empathy` on `rgba(232, 139, 169, 0.12)`. The chip itself gets an inner-border highlight: `box-shadow: inset 0 0 0 2px rgba(123, 184, 224, 0.35)` (A) or `rgba(232, 139, 169, 0.35)` (B).

**Chip rail separator (`.chip-sep`):** A dashed-feel divider labeled with italic prompt copy ("Something feel off?"). Flex with hairline rules on both sides.
```
display: flex
align-items: center
gap: space-3
margin: space-6 0 space-4
color: text-muted
font-size: text-small
font-style: italic

::before, ::after {
  content: "";
  flex: 1;
  height: 1px;
  background: border-subtle;
}
```

**Mobile:** Chip rail flips to `flex-direction: column; align-items: stretch;` inside `.frame-mobile`. Each chip becomes full-width.

**Inline expansion:** The primary chip can expand in place into a clarifier (below) — it becomes the Clarifier container. Ghost chips stay visible underneath.

### Reasoning Card

Gemma's streaming reasoning surface. Not a chat bubble, not a spinner — the visible channel for "Gemma is thinking out loud, word by word." Use any time Gemma is generating multi-sentence reasoning the student should witness (§5 of Set Your Course: "witnessing thought, not loading").

**Container:**
```
background: rgba(27, 29, 48, 0.6)          /* bg-deep @ 60% */
border: 1px solid border-subtle
border-left: 3px solid accent-insight      /* the "this is Gemma" stripe */
border-radius: radius-xl
padding: space-5
shadow: shadow-md
animation: card-breathe (4s insight pulse — the same keyframe the Match Card uses)
```

**Streaming cadence:** paragraph-by-paragraph, sentence-level. The frontend accumulates streamed deltas into a buffer and flushes a **sentence** to the DOM when the buffer ends with terminal punctuation (`.`, `!`, `?`) or hits 80 characters (whichever first — prevents pathological long-unpunctuated strings). On `\n\n`, the paragraph finalizes. **Not token-by-token** — that reads as "bot," not "thought."

**Sentence states:**

| State | Class | Treatment |
|-------|-------|-----------|
| **arriving** | `.animate-gemma-shimmer` | The sentence *just* flushed into the DOM. A 320ms insight-gradient sweep sweeps left→right once and holds. Sentence text-opacity ramps `0.6 → 1.0` under the sweep — the "text cooling" metaphor. After 320ms the sentence has settled; no animation continues. |
| **settled** | (default paragraph) | Full `text-primary @ 1.0`, `leading-relaxed`. Previously-arrived sentences in the same paragraph are settled as soon as a new sentence starts arriving. |

Paragraph typography: `font-body`, `text-body`, `color: text-primary`, `leading: relaxed`. Paragraphs separate with `space-3` gap.

**Why one-shot-per-sentence and not a continuous loop:** the mockup loops the shimmer because it's static — it has no real sentences arriving. In the shipped product, each sentence sweeps *once* as it lands, then settles. A continuous loop would read as "still loading," defeating the "reasoning is happening" metaphor.

**Streaming cursor (`.cursor-blink`):** A solid insight rectangle that follows the last arriving word.
```
display: inline-block
width: 8px
height: 1.1em
background: accent-insight
vertical-align: text-bottom
margin-left: 2px
animation: terminal-cursor-blink 1.2s ease-in-out infinite
```
Use `.animate-terminal-cursor` with these styles — don't invent a new keyframe. (The 1.2s override is a Set-Your-Course default; standard terminal cursor is 1s.)

**Pairing patterns:**
- Precede with a `GemmaThinking` status line ("Gemma is reading your input…").
- Follow with a `.breadcrumb` echo of the student's clarifier input and/or a `.tool-call` chip when reasoning resolves.

**Accessibility:** `role="status"` + `aria-live="polite"` so screen readers receive each settled paragraph. The arriving paragraph should have `aria-hidden="true"` on the cursor span only.

### Clarifier

A caution-tinted, scoped input that expands out of the primary chip when the student wants to push back on Gemma's match. Desktop renders inline (no modal); mobile renders as a bottom sheet (see Bottom Sheet below).

**Container (inline, desktop):**
```
background: rgba(242, 212, 119, 0.06)
border: 1px solid rgba(242, 212, 119, 0.28)
box-shadow: 0 0 24px rgba(242, 212, 119, 0.14)
border-radius: radius-xl
padding: space-5
display: flex
flex-direction: column
gap: space-4
```

**Anatomy (top to bottom):**
1. **Chip header** — the same sparkle + text from the primary chip ("Not what I expected"), `font-weight: 700`, `text-accent-caution`. Signals "the chip you clicked is now a container."
2. **Label** — `font-body`, `text-small`, weight 700, `text-secondary`. The big ask ("What were you hoping to see?").
3. **Sub** — `text-small`, `text-muted`. One-line clarification ("Name a job, a field, whatever's missing.").
4. **Input** — height min 48px, `bg-deep`, `border-default`, `radius-md`, `text-body`, `color: text-primary`. Focus: `border-accent-info` + 3px focus ring. Placeholder is permissive-framed and italic-muted (e.g. *"e.g. brand manager, UX designer, something with less math…"*). Use a single-line `<input>` on desktop; promote to `<textarea>` on mobile only when the keyboard + autocorrect benefit outweighs the extra vertical budget.
5. **Char count** — `.char-count` — `font-data`, `text-micro`, `text-muted`, right-aligned. Format `{n} / {max}`. 280 is the canonical ceiling (enforced both client-side and Pydantic server-side per spec).
6. **Actions** — right-aligned flex row: Ghost "Cancel" + Primary **"Ask Gemma"** with a `GemmaStar` prefix. On submit the button label morphs to **"Asking…"** with the `GemmaThinking` spinner inline (replacing the star). Labels are spec-locked — don't rephrase.

**Preview stays in view** — the career preview above the clarifier must remain visible. Never turn the clarifier into a modal on desktop.

**Submit choreography (spec-locked):** the clarifier **dismisses immediately** on submit — it does *not* wait for Gemma's first chunk. Desktop inline collapses via `springs.smooth` (~200ms); the bottom sheet slides down. The streaming debug trace replaces the career preview as the student's focal point. Rule from the visionary §4: leaving the clarifier open while streaming creates two competing focus points. Dismiss first, then stream.

**Keyboard:** `Enter` submits if the input is non-empty; `Shift+Enter` inserts a newline (textarea mobile only); `Esc` cancels (reverses the expand and returns the chip to default). Focus lands in the input automatically on open.

### Bottom Sheet

Mobile-native scoped input surface. Slides up from the bottom of the viewport, dims + blurs everything behind it. Use when a desktop inline expansion would overflow a small viewport (the Clarifier's default mobile behavior).

**Shell (the dimmed backdrop region):**
```
position: relative
background: bg-void
border-radius: radius-xl
border: 1px solid border-default
overflow: hidden
```
With a scrim pseudo-element:
```
::after {
  position: absolute; inset: 0;
  background: rgba(18, 19, 31, 0.7);
  backdrop-filter: blur(6px);
  z-index: 1;
}
```
Any content behind the scrim renders at `opacity: 0.35`.

**Sheet:**
```
position: absolute; left: 0; right: 0; bottom: 0
background: bg-mid
border-top: 1px solid border-strong
border-radius: radius-xl radius-xl 0 0
shadow: shadow-lg
padding: space-6 space-5 space-6
z-index: 2
display: flex; flex-direction: column; gap: space-4
```

**Drag handle (`.grab`):**
```
width: 40px
height: 4px
background: rgba(58, 61, 117, 0.6)
border-radius: radius-full
margin: 0 auto space-4
```
Visual only in MVP — not a drag-to-dismiss affordance. Tells the student "this is a sheet, not a modal."

**Primary action (inside the sheet):** full-width, 48px tall, `text-cta` size. Centered content. Below it, a muted centered `.cancel` inline-text line. No secondary button cluster — mobile decisions are binary.

**Entrance:** Slide up from `y: 100%` with `springs.smooth`. Scrim fades in over 200ms.

**Accessibility (required):**
- The sheet itself gets `role="dialog"` + `aria-modal="true"` + an `aria-label` matching the sheet's headline (e.g. "What were you hoping to see?").
- `Escape` dismisses the sheet — reverse of the entrance.
- **Tapping the dimmed scrim behind the sheet acts as Cancel** — dismisses the sheet without submitting. Same effect as tapping the inline `.cancel` text.
- Focus enters the first input or button on mount and is trapped inside the sheet until dismiss. On dismiss, focus returns to the trigger chip.
- The drag handle is `aria-hidden="true"` — it's decorative in MVP (no drag-to-dismiss).

### Commit Bar

Persistent primary-action footer for "make the decision" surfaces (Set Your Course commit, build confirmation, etc.). Distinct from a generic button group — this is the "big yes + soft escape" pairing at the bottom of the screen with an optional whisper of Gemma's unease above it.

**Container (desktop inline):**
```
margin-top: space-8
padding: space-5 space-6
display: flex
align-items: center
justify-content: space-between
gap: space-4
background: bg-deep
border: 1px solid border-subtle
border-radius: radius-xl
```

**Anatomy:**
- **Nudge (optional):** `.nudge` — `font-size: text-small`, italic, `text-muted`, right-aligned, sits inline (left of actions) or above them on mobile. Used only when Gemma's confidence is below the high threshold. Copy is always a question. Visionary-locked default: ***"Want to double-check this first?"*** — never a warning, never blames the student. §8 "whisper, not warning."
- **CTA primary (`.cta-primary`):** 48px tall, 0 space-8 padding, `accent-thrive` background, `text-inverse` label, `text-cta` size, weight 700. Label is spec-locked: **"Yes, continue"** — the "Yes," is a kid-voice cue that reads as confirmatory ("yes, that's me"), not transactional. Don't shorten to "Continue." Hover: add `shadow-glow-thrive`, `translateY(-1px)`. Disabled: `bg-state-disabled`, `text-muted`, `cursor: not-allowed`, `pointer-events: none`.
- **CTA ghost (`.cta-ghost`):** 40px tall, 0 space-4 padding, `text-secondary`, weight 600, `text-small`. Label is spec-locked: **"Start over"**. Hover: text → `text-primary`, `rgba(255, 255, 255, 0.04)` background.

**Mobile (fixed):** The bar pins to the bottom of the viewport.
```
position: absolute; bottom: 0; left: 0; right: 0
margin-top: 0
border-radius: 0
border: none (or border-top only)
background: rgba(27, 29, 48, 0.92)
backdrop-filter: blur(12px)
flex-direction: column
padding: space-3 space-4 calc(space-5)
gap: space-2
```
Nudge goes above actions, centered. Actions span full width, `justify-content: space-between`.

**Never gate the student.** The primary CTA stays *enabled* in low-confidence states — only the nudge changes. The student always retains agency; Gemma only whispers.

**Nudge dismissal rule:** the nudge clears the moment the student taps **any** chip — primary *or* ghost. Tapping any chip satisfies the "worth a double-check?" framing; re-rendering the nudge after a chip would read as nagging. Mount and unmount the nudge via `AnimatePresence` so the disappearance is a gentle fade, not a jump. Also clears on successful commit.

**Accessibility:** the nudge is `aria-describedby`-associated with the primary CTA so screen-reader users hear the context alongside the button, rather than having to locate the nudge line separately.

### Trace / Feasibility List

A structured list that classifies each candidate by reachability. Used after a clarifier resolves, in the debug-trace view. Shares visual DNA with the career preview list but carries right-side feasibility pills and descriptive sub-lines.

**Container:**
```
list-style: none
background: bg-mid
border: 1px solid border-subtle
border-radius: radius-xl
overflow: hidden
```

**Row (`.trace-row`):**
```
padding: space-4 space-5
border-top: 1px solid border-subtle   /* first row: none */
display: grid
grid-template-columns: 1fr auto
gap: space-3
align-items: center
```
Hover: `background: bg-surface`.

**Row content:**
- **Left column** — `.title` in `font-body`, `text-body-sm`, weight 600, `text-accent-info`, with a `→` glyph prefix (also info-colored). `.sub` below in `text-small`, `text-muted`, indented to align under the title.
- **Right column** — a Pill/Badge with the feasibility glyph convention (`◆` reachable / `◇` absent). Accent follows semantics: thrive (direct hit), caution (through another program), alert (not here at all).

**Click behavior is mode-dependent:**

| Mode | Row clickable? | Behavior |
|------|---------------|----------|
| **Preview** (shown under an initial resolution) | No | Rows are read-only. The student commits via the Commit Bar, not by clicking a career. Cursor stays `default`, no hover background. |
| **Debug-trace** (shown after a chip-routed clarifier response) | Yes | Rows are `<button>`s. Click triggers a 180ms thrive flash (title → `accent-thrive`, `bg-[rgba(125,212,163,0.12)]` row background), then the resolution crossfades to that career and the trace dismisses. Same choreography as a community-suggestion click. |

The visual difference is minimal — the same component renders both modes. What changes is the presence of a click target and the cursor affordance.

The list often follows a `.breadcrumb` echo of the student's clarifier and a `.tool-call` chip showing which tool Gemma invoked. Pair in that order: breadcrumb → reasoning card → tool-call → section-label → trace list.

### Community Card

"Where other students landed" — aggregated, opt-in, honest. Shows only career + count. No avatars, no timestamps, no trending indicator. Absence is the default; the card exists to *be honest* about the crowd, not to manufacture social pressure. §6 "honest, not creepy."

**Container:**
```
background: bg-mid
border: 1px solid border-subtle
border-radius: radius-xl
overflow: hidden
```

**Row (`.community-row`):**
```
display: grid
grid-template-columns: 1fr auto
align-items: center
padding: 14px 20px
border-top: 1px solid border-subtle   /* first row: none */
cursor: pointer
transition: background fast
```
Hover: `background: bg-surface`.

- **Title:** `font-body`, `text-body-sm`, weight 600, `text-accent-info`, `→` glyph prefix.
- **Count:** `font-data`, `0.8125rem`, `text-muted`, right-aligned. Format `{n} students`.

**n=1 behavior:** The shipped product renders the n=1 row *plainly* — no special variant, no alert stripe. Per `feature-set-your-course.md` §1, `COMMUNITY_MIN_COUNT` defaults to 1 during the hackathon; raising the threshold to 3 is a post-hackathon env-var change, not a separate visual state.

> **Mockup-only variant — not shipped.** The Set Your Course mockup (`docs/specs/design/set-your-course-mockup/index.html` scenario 11) shows a `.creepy-flag` treatment — `box-shadow: inset 3px 0 0 var(--color-accent-alert)` on the row plus an "⚠ PM concern: does a single-row community read as surveillance?" note. That was a visual argument *against* shipping n=1 at all, staged for the decision review. It is not a product state. Do not implement it in runtime code.

**If the threshold is later raised and the section needs to communicate "count below threshold":** prefer absence over any alert-stripe treatment. Absence is honesty, filler is noise.

### Gap Tile

A caution-striped leave-gesture tile — "this school doesn't offer that path." Reads as *go somewhere else*, not *refine here*. Different from a chip (which refines in place) and different from a confirm dialog (which is a decision, not a redirect). §13 of Set Your Course.

**Container:**
```
margin-top: space-5
padding: space-5 space-6
background: bg-mid
border: 1px solid border-subtle
border-left: 3px solid accent-caution
border-radius: radius-xl
shadow: shadow-md
position: relative
```

**Anatomy:**
- **Icon** — `◇` (open diamond — "this is absent here"), `font-size: 20px`, `accent-caution`, block, margin-bottom space-2.
- **Headline (spec-locked)** — **"This school doesn't offer that path."** `font-display`, `text-subheading`, weight 600, `text-primary`.
- **Body** — `text-body`, `text-secondary`, `leading-relaxed`, margin-bottom space-4. Copy template: ***"`<Career>` typically comes from a `<program_title>` degree. `<School>` doesn't offer that program."*** Interpolate career title and the broader program's human-readable name — **never** the CIP code, which lives only in the destination URL's query string.
- **CTA (spec-locked)** — Secondary button (outline info, see `.btn-secondary`). Label is **"Find schools with this major"** followed by a `▸` glyph (`gap-2`). Navigates to `/discover?cip=<cip4>` — the cip4 value is URL-only, never rendered.
- **Stub note** — optional `.stub-note` meta pill (see Meta Pill Family) below the CTA. Use when the destination is a v0.5 stub (currently the case for `/discover` — see `feature-school-discovery.md`).

**Multi-candidate variant (batched):** when the debug trace surfaces more than one `school_gap` career, **do not render multiple tiles** — render **one tile that batches them.** Replace the headline and body with:
- **Batched headline:** **"These paths aren't at this school."**
- **Batched body:** a single dense comma-separated line of career titles in `font-body`, `text-body-sm`, `text-muted`. No inline feasibility pills.
- **Single CTA:** same "Find schools with this major" label, linking to `/discover?cip=<primary_cip>` where `primary_cip` is the highest-confidence gap target. Don't split into multiple CTAs — the student needs one onward gesture, not a menu.

**Tone:** the caution stripe is the warmth — it says "you're not in the wrong place, you're in a place that doesn't have this." Never use alert-striped tiles for school-gap — alert reads as error, caution reads as redirect.

### Tool-Call Indicator

Chip-sized glyph that announces "Gemma just invoked a tool." Sits inline between reasoning and results. Concrete attribution — makes the model's action legible to the student without opening a dev console.

**Style:**
```
display: inline-flex
align-items: center
gap: 6px
padding: 6px space-3
margin-top: space-3
background: rgba(123, 184, 224, 0.08)
border: 1px solid rgba(123, 184, 224, 0.22)
border-radius: radius-full
font-family: font-data
font-size: text-micro
color: accent-info

::before {
  content: "⚙";
  font-size: 11px;
}
```

**Copy pattern:** past tense, factual. "Gemma looked up career paths for IU · Business/Commerce", "Gemma pulled BLS occupation data for 13-1161". Never marketing-y ("Gemma worked hard!"). Matches the Gemma attribution conventions in the Gemma Interactions spec.

### Breadcrumb Echo

A muted italic line that echoes the student's input back into a downstream view. Tells the student "here's what I'm reasoning about" without repeating the whole clarifier. One line, no wrapping.

```
font-size: text-small
color: text-muted
font-style: italic
margin-bottom: space-4
padding-left: space-2
border-left: 2px solid border-subtle
```

**Copy pattern:** lower-case lead-in + quoted user text. `from your clarifier: "I wanted actual marketing jobs"`. Always quotes the user verbatim — never paraphrased.

### Disclosure Toggle

A lightweight `▸`-prefixed inline expander for optional settings clusters ("Show effort & loans", "Show advanced filters"). Not a button, not an accordion header — a muted hint that more exists if wanted.

```
display: flex
align-items: center
gap: space-2
font-size: text-small
color: text-muted
cursor: pointer
padding: space-2 0

::before {
  content: "▸";
  font-family: font-data;
}

:hover { color: text-secondary; }
```

**Open state:** rotate the `▸` glyph 90° with `transition-fast`. Content reveals below with `springs.gentle`, staggered inputs at `stagger.fast`.

### Meta Pill Family

A unified primitive for **small data-font tagged pills** — the stub-note, the scenario criterion tag, the PM concern note, the A/B chip label. Each of these was styled ad-hoc in the mockup; the shared DNA is `font-data` + `text-micro` + tinted background + tinted border + `radius-full`.

**Base:**
```
display: inline-flex
align-items: center
gap: space-2           /* when prefixed with a glyph */
padding: 4px 10px      /* micro pills: 2px 8px for chip-label */
border-radius: radius-full
font-family: font-data
font-size: text-micro  /* or 10–11px for the smallest variants */
letter-spacing: 0.5px
```

**Colorways (background at 8–12% / border at 22–28% / text at full accent):**

| Variant | Accent | Usage |
|---------|--------|-------|
| `meta-info` | info | Scenario criterion, live data tag, navigational meta |
| `meta-insight` | insight | Stub notes, AI meta, "coming soon" markers |
| `meta-caution` | caution | Warning meta, "review" flags |
| `meta-empathy` | empathy | PM concern notes, human-reviewed meta |

**Don't use for:**
- Interactive status (use Pills / Badges with semantic glyphs).
- Tool-call announcements (use the dedicated Tool-Call Indicator — has `font-data` but also a `⚙` glyph + info background specifically).

The A/B chip label is a compact sub-variant: 2px vertical padding, 8px horizontal, 10px font, text-transform uppercase, inside another chip. Treat as a badge-within-chip, not a standalone meta pill.

### Editorial Chrome

A family of patterns built originally for the Set Your Course mockup showcase but intentionally promoted into the design system because they look *right*. Use in-app when a screen carries a lot of structured, scannable content: settings, the planned comparison screen, post-reveal summary panels, design-review surfaces, and any future changelog / journal view. Editorial chrome is what makes a dense screen feel *curated* instead of *dumped*.

#### Index Rail

Sticky left-side table-of-contents for long vertical screens. A 240px rail that pairs with a scrolling content column on the right.

```
position: sticky
top: space-6
align-self: start
padding: space-5
background: bg-deep
border: 1px solid border-subtle
border-radius: radius-xl
shadow: shadow-md
max-height: calc(100vh - space-10)
overflow-y: auto
```

- **Header** — `font-data`, 11px, weight 700, letter-spacing 2px, uppercase, `accent-info`. The same treatment as section labels.
- **List** — `<ol>` with `list-style: none`, auto-numbered via `counter-reset: idx` + `counter-increment`. Numbers render in `font-data`, 11px, `text-muted`, with `decimal-leading-zero` format ("01", "02", …).
- **Link row** — `display: block`, padding `6px 10px`, `text-small`, `text-secondary`, `radius-sm`. Hover: `background: border-subtle`, text → `text-primary`.

**Responsive:** collapse to `position: static`, full-width, no max-height below 900px. The grid parent swaps from two columns to one.

**In-app reuse targets:** comparison screen (scenarios of saved builds), branch tree full-index, Wrapped/Year-in-Review navigation.

#### Scenario Head

A compact header block that introduces a chunk of content with a taxonomic meta line, a display-font title, a scenario caption, and an optional success criterion pill. Originally the chunk-divider in the mockup — use in-app anywhere a screen needs a big internal chapter break.

```
margin-bottom: space-5
padding-bottom: space-4
border-bottom: 1px solid border-subtle
```

**Anatomy:**
- **Number / meta** — `.scenario-num` — `font-data`, 11px, weight 700, letter-spacing 2px, uppercase, `accent-info`. The "01 · Empty state" treatment. Pattern: `{NN · {CATEGORY}}` with middot separators.
- **Title** — `<h2>` in `font-display`, `text-heading`, weight 600, `text-primary`.
- **Caption** — `.scenario-caption` — `text-body`, `text-secondary`, `leading-relaxed`, `max-width: 80ch`.
- **Criterion** — `.scenario-criterion` (reuse as a Meta Pill `meta-info` variant) — rounded-full, `font-data`, `text-micro`, `accent-info` on `rgba(123, 184, 224, 0.1)` with `rgba(123, 184, 224, 0.25)` border. Copy pattern: `Success: "{criterion}"` or `Decision N: {question}`.

#### Decisions Callout

A structured, caution-striped callout for framed-decision copy — used when the student or reader needs to make an explicit choice before continuing. Bigger than a tile, smaller than a modal.

```
padding: space-6
background: bg-mid
border: 1px solid border-default
border-left: 3px solid accent-caution
border-radius: radius-xl
shadow: shadow-md
```

- **Title** — `<h3>` in `font-display`, `text-subheading`, weight 600, `accent-caution`.
- **List** — ordered list; each `<li>`: `text-body`, `leading-relaxed`, `text-secondary`. Bold the decision name with `text-primary`.
- **Meta** — `.decision-meta` — `text-small`, `text-muted`, italic, displayed on its own line below each decision. Use for context references ("See scenarios 10, 11, 12.").

**In-app reuse targets:** settings with destructive consequences (delete save, change school), build confirmation when a previous save exists, onboarding choice screens.

#### Variant Card

A bordered card used to display side-by-side options for comparison (A vs B). Reuse when the screen needs to present two or three options at once without forcing a selection first.

```
padding: space-5
background: bg-deep
border: 1px solid border-subtle
border-radius: radius-xl
```

- **Label** — `<h5>` — `font-data`, 11px, letter-spacing 1px, uppercase, `accent-info`, margin-bottom space-3. Pattern: `Variant {letter} · {qualifier}`.
- **Preview** — whatever UI the variant actually contains (a chip rail, a card, a copy sample).
- **Body** — `.variant-body` — `text-body-sm`, `text-secondary`, `leading-relaxed`, margin-top space-3. One-paragraph rationale.

Render two or three variants in a CSS grid with `grid-template-columns: 1fr 1fr` (or `1fr 1fr 1fr`) and `gap: space-5`. The mockup's `.sidebyside` class is the canonical layout utility.

**In-app reuse targets:** build comparison (side-by-side pentagons + vibe copy), boss-fight strategy comparisons, A/B branch preview.

#### Viewport Label

A meta-line that precedes a preview frame, describing the viewport or context ("Desktop · 1280 · two frames side-by-side"). Tiny, technical, never styled loud.

```
display: flex
align-items: center
gap: space-2
font-family: font-data
font-size: 11px
letter-spacing: 1.5px
text-transform: uppercase
color: text-muted
margin: space-6 0 space-3
```

A `.dim` inline span downshifts to 10px, `font-body`, lowercase, no letter-spacing — for the secondary qualifier after a middot.

**In-app reuse targets:** developer / admin surfaces, debug traces, any screen showing a preview at an explicit viewport size.

---

## Iconography

Rounded line icons, 2px stroke weight. Not filled, not sharp. Compatible with Lucide Icons (rounded variant) or Phosphor Icons (rounded).

**Custom stat icons:**
- ERN: coin
- ROI: arrow-loop
- RES: shield
- GRW: sprout
- HMN: heart-hand

---

## Illustration Style

All rendered art (bears, boss monsters) follows the **plush toy** aesthetic:

- Matte fabric texture, not glossy
- Soft studio lighting, key light from upper left
- Dark navy background matching `bg-deep` (#1B1D30)
- Button eyes with single highlight dot
- Miniaturized, toylike accessories
- Boss monsters are funny-scary: plush toys of threatening concepts

---

## Implementation Files

| File | Purpose |
|------|---------|
| `frontend/src/styles/tokens.css` | CSS custom properties (source of truth for all token values) |
| `frontend/tailwind.config.ts` | Tailwind theme mapping tokens to utility classes |
| `frontend/src/styles/motion.ts` | Framer Motion springs, stagger delays, animation variants |
| `frontend/src/index.css` | Font imports, keyframe animations, ambient effects |
| `docs/mockups/brightpath-design-system-v3.html` | Interactive visual reference — canonical (open in browser). Includes Grid System demo. v2 retained for history. |

---

## Emotional Framework

Every screen targets a specific emotion. Design decisions serve the emotion first.

| Screen | Primary Emotion | Design Implication |
|--------|----------------|-------------------|
| 01 Character Select | Playful delight | Low stakes, high charm. Warm background. Large portraits. |
| 02 School + Major | Curious anticipation | Search feels weighty but not overwhelming. |
| 03 Effort Slider | Honest reflection | Compassionate, not judgmental. Stats shift in real-time. |
| 04 Stage 2 Reveal | Awe + pride | THE cinematic moment. Bear evolves. Pentagon blooms. |
| 05 Boss Gauntlet | Tension + fun | Funny-scary. Losses teach, wins celebrate. |
| 06 Branch Tree | WONDER | The telescope moment. Futures illuminate across the screen. |
| 07 Save + Share | Proud ownership | Character card as identity artifact. |
| 08 Compare | Informed confidence | Side-by-side pentagons. Anxiety becomes clarity. |
