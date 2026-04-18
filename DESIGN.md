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

### CSS Keyframe Animations

For effects that don't need spring physics. Defined in `index.css`:

| Animation | Duration | Usage |
|-----------|----------|-------|
| `stat-label-fade` | 1s ease-out | Pentagon stat labels fading in |
| `vertex-glow-pulse` | 4s ease-in-out infinite | Pentagon vertex glow dots |
| `ambient-breathe` | 6s ease-in-out infinite | Background ambient glow |
| `twinkle` | 4s ease-in-out infinite | Star particles |

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

**Zones:**
- **Attribution:** Static GemmaStar icon (14px, info-to-insight gradient) + "Gemma matched `"{input}"`" in `text-small text-text-muted`, raw text in `font-semibold text-text-secondary`
- **Title:** `font-display text-subheading font-semibold`. Slides in from x:-8 and brightens from `text-muted` to `text-primary` over 400ms. CIP code below in `font-data text-data-sm text-text-muted`.
- **Career preview:** Section label pattern ("WHERE THIS LEADS"). Career rows: `font-body text-body-sm font-semibold text-text-secondary`, info-colored arrow prefix. Hover: `bg-surface`, text brightens. Stagger at `stagger.fast` (50ms).
- **Warning (conditional):** `border-t border-border-subtle`, `text-small text-accent-caution italic`
- **Actions:** Primary button ("That's right") + Ghost button ("Not quite") per Button spec. Delayed entrance at 700ms.

**Low confidence variant:**
- Glow shifts to caution: pulses between `0 0 24px rgba(242, 212, 119, 0.10)` and `0 0 36px rgba(242, 212, 119, 0.22)`
- Caution pill badge ("best guess") on metadata row next to CIP code
- Confirm button label changes to "Close enough"
- "Not quite" button text brightens to `text-primary`

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

### Boss Cards

Grid of boss fight previews.

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
