# FutureProof Design System Proposal

> **This is the original design proposal — the "why" behind Brightpath.** It captures the vision, emotional framework, and design rationale. For the authoritative spec (exact tokens, component specs, motion values), see **`DESIGN.md`** at the project root. Where this document and DESIGN.md conflict, DESIGN.md wins.

## Design System Name: **Brightpath**

Not "Cozy Quest." Here's why.

FutureProof is not a farming simulator. It's not a casual hangout. It is a *career RPG with real stakes* dressed in plush fur and soft lighting. The student sitting down with this tool is facing one of the most expensive, consequential decisions of their life -- and they're probably terrified. The design system's job is to make that terror feel like an adventure.

"Brightpath" captures the soul: *there IS a path forward, and it's lit up for you.* The branches glow. The futures illuminate. The darkness isn't scary -- it's the unknown, and you're about to map it.

The aesthetic reference isn't Animal Crossing (no stakes, pure vibes) or Stardew Valley (grind loops). It's **Pixar meets Studio Ghibli meets your favorite RPG character screen.** Think: the warmth and emotional intelligence of *Inside Out*, the lush dark environments of *Spirited Away*'s spirit world, and the satisfying progression of seeing a character level up in *Pokemon* or *Fire Emblem*.

Warm. Rich. Dark. Cinematic. Data-dense but never clinical. A world you want to spend time in, exploring your own future.

---

## Emotional Framework

Every screen must answer one question: *what should the student FEEL right now?*

| Screen | Primary Emotion | Secondary Emotion | Design Implication |
|--------|----------------|-------------------|-------------------|
| Character Select | Playful ownership | "This is ME" | Immediate tactile delight. The student claims an identity before anything serious happens. Low stakes, high charm. |
| School + Major | Curious anticipation | Slight nervous energy | The search feels weighty but not overwhelming. The starter bear watches, waiting. Momentum builds. |
| Effort Slider | Honest self-reflection | Empowered vulnerability | This is the most emotionally delicate screen. "How much can you give?" must feel compassionate, not judgmental. The stat preview shifting in real-time gives them agency. |
| Stage 2 Reveal | Awe + pride | "I can see myself" | The signature emotional beat. The scruffy starter BECOMES someone. This must feel like a transformation -- like watching your Pokemon evolve. Cinematic. The pentagon blooms. |
| Boss Gauntlet | Tension + excitement | Humor softens the blows | Boss fights are the reality check, but they should feel like a game, not a lecture. Losses sting but never devastate. Historical parallels reframe loss as shared human experience. |
| Branch Tree | Wonder + clarity | The "zoom out" moment | THE emotion. The student sees their future branching outward across the entire screen. This is the telescope moment. The fog lifts. Multiple futures are visible simultaneously. This must take the breath away. |
| Save + Share | Proud ownership | Social identity | "I got Doctor Bear." The character card is an identity artifact. Sharing it should feel like showing off your Hogwarts house, not a career planning PDF. |
| Compare | Informed confidence | Decisive clarity | The anxiety of "which school?" transforms into "which branches do I want?" Side-by-side comparison makes the invisible tradeoffs visible. This is empowerment through data. |

---

## Visual Philosophy

### The Thesis

FutureProof exists in the space between a game and a decision tool. Push too far toward "game" and judges won't take it seriously. Push too far toward "tool" and students won't engage with it. The visual language must hold both: **serious enough that a school counselor would show it to parents, playful enough that a 17-year-old sends it to their group chat.**

### The Three Pillars

**1. Cinematic Dark**
Dark backgrounds aren't just aesthetic -- they're functional. Dark creates focus. On a dark canvas, the glowing branch tree, the bright stat pentagons, and the plush characters POP. Every accent color reads as light in the darkness. The student's future is literally being illuminated.

The darkness is NOT brooding, dystopian, or edgy. It's the darkness of a movie theater before the film starts. The darkness of a planetarium. Rich, velvet, safe. You're in the dark because the show is about to begin.

**2. Plush Materiality**
Everything in this world has a softness to it. The characters are plush toys. The boss monsters are plush toys. Even the UI elements have a subtle softness -- rounded corners, gentle shadows, smooth gradients. Nothing is hard, sharp, or clinical.

This softness does psychological work: it makes a terrifying topic (your entire career) feel approachable. A spreadsheet of salary data is intimidating. A plush bear with the same data rendered as glowing stats on a pentagon? That's something you want to interact with.

**3. Progressive Illumination**
The design metaphor that ties everything together: *you start in the dark, and things light up as you go.* The character select is warm and inviting. The school selection adds a glow. The effort slider shifts the brightness of stat previews in real-time. The Stage 2 reveal is a burst of light. The boss fights flicker between tension and resolution. And the branch tree -- the culmination -- is an entire constellation of futures lighting up across the screen.

This isn't decorative. It's narrative design. The student's journey through FutureProof is a journey from uncertainty to clarity, and the light levels reflect that.

---

## Color Palette

### Background System

The backgrounds are layered indigo-navy. Not pure black (too harsh). Not grey (too corporate). Indigo carries warmth and depth -- it's the color of a night sky just after sunset. There are enough things happening in the sky to feel alive.

| Token | Hex | Usage | Feeling |
|-------|-----|-------|---------|
| `bg-void` | `#12131F` | Deepest background, behind branch tree | The infinite canvas. Space. |
| `bg-deep` | `#1B1D30` | Primary page background | The "home" darkness. Comfortable and grounding. |
| `bg-mid` | `#232545` | Card backgrounds, elevated surfaces | Lifted. Present. Where content lives. |
| `bg-surface` | `#2D3060` | Interactive surface, hover states | Active. Touchable. "I can interact with this." |
| `bg-raised` | `#3A3D75` | Tooltips, popovers, active states | Highest elevation. The spotlight. |

### Accent System

Each accent color carries specific semantic meaning across the entire product. These are the lights in the darkness.

| Token | Hex | Semantic Role | Where It Appears |
|-------|-----|---------------|-----------------|
| `accent-thrive` | `#7DD4A3` | Growth, success, wins, positive stats | Win states, high stats, positive branch outcomes, CTA buttons, "thrive" moments |
| `accent-alert` | `#F4A97E` | Warning, losses, negative outcomes | Boss fight losses, low stats, debt warnings, negative branch indicators |
| `accent-caution` | `#F2D477` | Draw states, moderate outcomes, attention | Draw states, medium stats, effort slider midpoint, "watch this" indicators |
| `accent-insight` | `#B8A9E8` | AI, intelligence, data, analysis | AI-related content, stat calculations, Gemma outputs, skill tree nodes, RES stat |
| `accent-info` | `#7BB8E0` | Neutral information, navigation, system | Links, info tooltips, navigation elements, secondary actions |
| `accent-empathy` | `#E88BA9` | Human connection, HMN stat, emotional content | HMN stat highlights, burnout content, the human side of career decisions |

### Stat Colors

Each of the five stats gets its own color identity within the pentagon chart and wherever stats appear.

| Stat | Hex | Rationale |
|------|-----|-----------|
| ERN (Earning Power) | `#F2D477` | Gold. Money. Universal. |
| ROI (Return on Investment) | `#7DD4A3` | Green. Growth. Returns. |
| RES (AI Resilience) | `#B8A9E8` | Purple. The AI/tech color. |
| GRW (Growth) | `#7BB8E0` | Blue. Expansive. Upward. |
| HMN (Human Edge) | `#E88BA9` | Pink. Warm. Human. |

### Text System

| Token | Hex | Usage |
|-------|-----|-------|
| `text-primary` | `#F5F0E8` | Primary body text. Warm white, not blue-white. |
| `text-secondary` | `#C4BFB0` | Secondary labels, descriptions. |
| `text-muted` | `#8A8595` | Tertiary info, disabled states, fine print. |
| `text-inverse` | `#1B1D30` | Text on light/accent backgrounds. |

### Boss Fight Colors

Each boss monster has a signature color that appears in its fight sequence.

| Boss | Hex | Reasoning |
|------|-----|-----------|
| Fight AI | `#B8A9E8` | Purple. The AI color. |
| Fight Student Loans | `#F4A97E` | Orange-amber. Debt burns. |
| Fight the Market | `#7BB8E0` | Ice blue. The market is cold. |
| Fight Burnout | `#E88BA9` | Pink-red. Burnout is emotional. |
| Fight the Ceiling | `#C4BFB0` | Muted grey-beige. The ceiling is invisible. |
| Fight the Future | Shifts through all five | The final boss contains all threats. |

---

## Typography System

### Font Families

| Role | Font | Weight(s) | Feeling | Why This Font |
|------|------|-----------|---------|--------------|
| Display / Headlines | **Fredoka** (variable) | 600 (SemiBold), 700 (Bold) | Rounded, friendly, confident. Not childish -- approachable. | Fredoka's rounded terminals soften every headline. It reads as "game UI" without being cartoonish. The variable weight axis gives us flexibility without loading multiple files. |
| Body / UI | **Nunito** | 400 (Regular), 600 (SemiBold), 700 (Bold) | Clean, warm, readable. The workhorse. | Nunito's rounded terminals match Fredoka's personality but it's optimized for body text legibility. The x-height is generous. It reads beautifully at small sizes on screen. |
| Data / Monospace | **Space Mono** | 400 (Regular), 700 (Bold) | Technical, precise, serious. The data voice. | When FutureProof shows hard numbers -- salary, debt, percentages, stat values -- Space Mono signals "this is real data." The contrast with Fredoka/Nunito creates a clear hierarchy: friendly world, serious numbers. |

### Type Scale

Using a 1.25 ratio (major third), base 16px.

| Token | Size | Line Height | Font | Weight | Usage |
|-------|------|-------------|------|--------|-------|
| `text-hero` | 48px / 3rem | 1.1 | Fredoka | 700 | Screen titles, branch tree header |
| `text-display` | 36px / 2.25rem | 1.15 | Fredoka | 700 | Section headers, boss fight names |
| `text-heading` | 28px / 1.75rem | 1.2 | Fredoka | 600 | Card titles, stat labels |
| `text-subheading` | 22px / 1.375rem | 1.3 | Nunito | 700 | Sub-sections, career titles |
| `text-body` | 16px / 1rem | 1.5 | Nunito | 400 | Default body text |
| `text-body-bold` | 16px / 1rem | 1.5 | Nunito | 600 | Emphasized body text |
| `text-small` | 14px / 0.875rem | 1.4 | Nunito | 400 | Captions, metadata |
| `text-micro` | 12px / 0.75rem | 1.3 | Nunito | 600 | Badges, labels, tiny UI |
| `text-data` | 16px / 1rem | 1.4 | Space Mono | 400 | Salary figures, percentages |
| `text-data-large` | 24px / 1.5rem | 1.2 | Space Mono | 700 | Hero stat numbers |
| `text-data-small` | 13px / 0.8125rem | 1.3 | Space Mono | 400 | Stat deltas, small data |

---

## Visual Language

### Shapes and Edges

**Border Radius Philosophy:** Everything is rounded. Nothing in this world has a sharp corner.

| Element | Radius | Token |
|---------|--------|-------|
| Large cards, panels | 20px | `radius-xl` |
| Standard cards, buttons | 14px | `radius-lg` |
| Input fields, chips | 10px | `radius-md` |
| Small badges, pills | 6px | `radius-sm` |
| Circles (avatars, stats) | 9999px | `radius-full` |

**Why fully rounded?** Sharp corners subconsciously signal "tool" or "enterprise." Rounded corners signal "game" and "approachable." Every major gaming interface -- Nintendo, PlayStation, mobile games -- uses rounded corners extensively. FutureProof should feel like it belongs in that world.

### Elevation and Depth

Rather than traditional box-shadows (which feel flat and corporate), Brightpath uses **layered glow shadows** that pick up the ambient accent colors.

| Level | Shadow | Token | Usage |
|-------|--------|-------|-------|
| 0 | None | `shadow-none` | Flat elements |
| 1 | `0 2px 8px rgba(27, 29, 48, 0.5)` | `shadow-sm` | Subtle lift |
| 2 | `0 4px 16px rgba(27, 29, 48, 0.6)` | `shadow-md` | Cards |
| 3 | `0 8px 32px rgba(27, 29, 48, 0.7)` | `shadow-lg` | Modals, popovers |
| Glow | `0 0 20px rgba(accent, 0.3)` | `shadow-glow` | Active/focus states, branch highlights |

### Texture and Surface

**No flat design.** Surfaces should feel like they have subtle materiality:

- Background surfaces get a very subtle noise texture (opacity 2-4%) to prevent that "flat CSS" look. This is the difference between a dark void and a dark velvet curtain.
- Cards use subtle inner gradients (lighter at top edge, darker at bottom) to create dimensionality.
- The branch tree background gets a barely-visible radial gradient emanating from the center bear, reinforcing the "illumination from within" metaphor.

### Illustration and Art Style

All rendered art (Midjourney bears, boss monsters) follows the **plush toy** aesthetic:

- Matte fabric texture, not glossy or shiny
- Soft studio lighting, key light from upper left
- Dark navy background matching `bg-deep` (`#1B1D30`)
- Button eyes with single highlight dot
- Accessories are miniaturized and toylike
- Boss monsters are funny-scary: plush toys of threatening concepts

The gap between "rendered 3D plush art" and "2D web UI" is bridged by:
- Keeping the UI colors identical to the art backgrounds
- Using the same rounded, soft visual language in UI components
- Matching the warm lighting direction in CSS gradients

### Iconography

Icons should be **rounded line icons** with 2px stroke weight. Not filled, not sharp. The line style matches the plush softness -- think Phosphor Icons (rounded variant) or Lucide Icons with their rounded option.

Specific icon treatments:
- Stat icons: Custom, simple, geometric. A coin for ERN. An arrow-loop for ROI. A shield for RES. A sprout for GRW. A heart-hand for HMN.
- Boss icons: Stylized versions of the boss monsters, reduced to simple iconic forms.
- Navigation: Standard rounded line icons from the icon library.

---

## Motion and Animation

### Philosophy

Animation in FutureProof is not decorative -- it's **narrative.** Every animation tells the student something: "this changed," "you progressed," "this is important." If an animation doesn't communicate, cut it.

The animation personality is **bouncy and organic** -- like a plush toy that's been gently tossed. Not robotic. Not linear. Things overshoot slightly and settle. Things bounce into place. This matches the plush materiality.

### Spring Configurations

Using Framer Motion spring physics (not CSS timing functions) for all meaningful animations.

| Token | Config | Feel | Usage |
|-------|--------|------|-------|
| `spring-bouncy` | `{ stiffness: 300, damping: 20 }` | Playful pop, noticeable overshoot | Character reveals, boss entrance, stat number counters, branch node activation |
| `spring-smooth` | `{ stiffness: 200, damping: 25 }` | Confident settle, gentle overshoot | Page transitions, card entrances, panel expansions |
| `spring-gentle` | `{ stiffness: 150, damping: 30 }` | Slow and graceful, minimal overshoot | Background shifts, ambient glow changes, branch tree initial render |
| `spring-snappy` | `{ stiffness: 400, damping: 25 }` | Quick and responsive, slight bounce | Button press, toggle, slider thumb, micro-interactions |

### Timing Principles

| Principle | Implementation |
|-----------|---------------|
| **Stagger children** | When multiple elements appear (stat bars, skill list, branch nodes), they stagger in with 50-80ms delays. Creates rhythm. |
| **Enter from below** | Content entering the viewport slides up 20-30px and fades in. Universal entrance. |
| **Scale from center** | Important reveals (bear evolution, pentagon chart, boss monster) scale from 0.8 to 1.0 with spring-bouncy. |
| **Glow before reveal** | Before a major reveal, a subtle ambient glow appears 200ms ahead. Builds anticipation. |
| **Numbers count up** | All data numbers (salary, percentages, stat values) animate from 0 to final value over 800ms with spring-bouncy easing. |
| **Color transitions** | Background hue shifts and accent color changes use 300ms ease-out. Smooth, never jarring. |

### Key Animation Sequences

**Stage 2 Reveal (the money shot for the video):**
1. Screen darkens slightly (200ms)
2. Subtle glow pulses from center (300ms)
3. Silhouette of starter bear fades (200ms)
4. Evolved bear scales up from 0.85 with spring-bouncy, glow intensifies
5. Career title types in letter by letter (Fredoka, 40ms per character)
6. Pentagon chart draws from center outward, each axis extending with spring-smooth (staggered 100ms)
7. Stat numbers count up simultaneously
8. Skill badges cascade in from below (stagger 60ms)

**Boss Fight Entrance:**
1. Screen edges darken (vignette effect, 300ms)
2. Boss name types in with impact (Fredoka Bold, white, center screen)
3. Boss monster bounces in from above with spring-bouncy
4. Stats being tested highlight and pulse
5. Tension beat (400ms pause)
6. Result: win (green burst, confetti particles) or lose (screen shake 3px, red flash, then a compassionate recovery animation)

**Branch Tree Illumination:**
1. Stage 2 bear settles at center, glowing softly
2. Branch lines draw outward from center, like roots growing (500ms per tier, staggered)
3. Silhouetted bears at endpoints fade in as branches reach them
4. Ambient particles drift along branch lines
5. On tap: selected branch glows accent-thrive, stats panel slides in from right

---

## Component Patterns

### Cards

The primary container for content. Multiple variants, all sharing the same DNA.

```
Base Card:
  background: bg-mid (#232545)
  border: 1px solid rgba(255, 255, 255, 0.06)
  border-radius: radius-xl (20px)
  padding: 24px
  shadow: shadow-md
  transition: all 200ms ease-out

Hover State:
  background: bg-surface (#2D3060)
  border: 1px solid rgba(255, 255, 255, 0.1)
  shadow: shadow-lg
  transform: translateY(-2px)

Active/Selected:
  border: 1px solid accent-thrive (#7DD4A3) at 40% opacity
  shadow: shadow-glow with accent-thrive
```

**Card Variants:**
- **Character Card** -- larger, centered bear image, name below. Used in character select grid.
- **Stat Card** -- compact, stat icon + value + label. Used in pentagon breakdown.
- **Boss Card** -- boss icon, name, win/lose result, brief narrative. Used in gauntlet results.
- **Branch Card** -- silhouette, branch name, mini stat preview. Used in branch tree endpoints.
- **Save Slot Card** -- bear thumbnail, school/major, date. RPG save file aesthetic.

### Buttons

| Variant | Style | Usage |
|---------|-------|-------|
| Primary | `bg: accent-thrive`, `text: text-inverse`, `radius: radius-lg`, bold, 48px height | Main CTAs: "Build my character," "Fight the Bosses," "See your build" |
| Secondary | `bg: transparent`, `border: 1px solid accent-info`, `text: accent-info`, 44px height | Secondary actions: "Compare," "Save," navigation |
| Ghost | `bg: transparent`, `text: text-secondary`, no border, 40px height | Tertiary: "Back," "Skip," subtle navigation |
| Danger | `bg: accent-alert at 15%`, `text: accent-alert`, 44px height | Delete save slot, destructive actions |
| Icon | `bg: bg-surface`, circular, 40px, icon centered | Accessory toggles, close buttons |

**Button Animation:**
- Press: scale to 0.97 (spring-snappy), background darkens 10%
- Release: scale back to 1.0 (spring-snappy)
- Focus ring: 2px offset ring in accent-info with glow

### Inputs

```
Text Input:
  background: bg-deep (#1B1D30)
  border: 1px solid rgba(255, 255, 255, 0.1)
  border-radius: radius-md (10px)
  padding: 12px 16px
  font: Nunito 16px
  color: text-primary
  height: 48px

Focus:
  border-color: accent-info (#7BB8E0)
  shadow: 0 0 0 3px rgba(123, 184, 224, 0.15)

School Search (special):
  Larger (56px height), with search icon
  Autocomplete dropdown matches bg-raised
  Results show school name + location in text-secondary
```

### The Pentagon Radar Chart

The five-stat pentagon is a recurring element. It must be instantly recognizable and beautiful.

- Filled polygon with gradient from center (darker) to edges (stat colors blend)
- Each axis line draws from center to vertex, colored by its stat
- Vertex dots are 8px circles in the stat color, with subtle glow
- Stat labels sit outside each vertex in `text-small` Nunito
- Stat values appear next to labels in `text-data` Space Mono
- On reveal: polygon draws from center outward with spring-smooth
- On compare: two pentagons overlay with 60% opacity each, colors visually blending at overlap

### Modals and Overlays

```
Modal:
  background: bg-mid
  border-radius: radius-xl
  max-width: 560px
  padding: 32px
  shadow: shadow-lg
  backdrop: rgba(18, 19, 31, 0.85) with backdrop-blur(8px)
  enters: scale from 0.95, opacity from 0, spring-smooth
```

### The Effort Slider

This is a custom component, not a standard range input.

- Track: 4px height, bg-deep, radius-full
- Fill: gradient from accent-info (low effort) to accent-thrive (high effort)
- Thumb: 24px circle, bg-raised with white border, shadow-glow
- Labels below: "Working two jobs" (left), "Full focus" (right), in text-muted Nunito
- Current label above thumb updates dynamically: "Part-time focus" / "Full focus" etc.
- Stat preview area updates in real-time as thumb moves -- numbers count smoothly

---

## The Eight Screens

### Screen 1: Character Select

**Emotional Target:** Playful delight. "This is going to be fun."

**Layout:** Centered content, generous whitespace. Animal species grid (3 across, 2 rows for 6 species) with large, clickable character portraits. Selected animal scales up and glows. Below: accessory tray as a horizontal scrollable row of toggleable pills/icons.

**Key Design Notes:**
- The background is warmer here than other screens. Subtle warm gradient overlay on bg-deep.
- Animal portraits are large enough to see personality -- minimum 140px rendered.
- Accessories toggle on/off with spring-snappy animation. Selected accessories appear on the character preview in real-time.
- The CTA ("Let's build your future") sits at the bottom with a subtle star/sparkle icon. This is the first button press -- it should feel ceremonial.
- No stats visible yet. No school. Just pure character creation joy. Let them play first.

### Screen 2: School + Major Selection

**Emotional Target:** Curious anticipation. "This is getting real."

**Layout:** Two-column on desktop. Left: school search + major picker stacked vertically. Right: the starter character standing in a "waiting" pose, slightly animated (subtle breathing/swaying). Below the character: a ghosted preview of the evolution silhouette.

**Key Design Notes:**
- School search is the hero input -- large, prominent, with smooth autocomplete.
- As the student types, results filter with 150ms debounce. Each result shows school name, city/state, and a small data confidence indicator.
- Major selection appears after school is selected, as an animated reveal (slide down, spring-smooth).
- The starter character on the right is not decorative -- it's the student's avatar, wearing their chosen accessories, watching. This creates emotional continuity from Screen 1.
- When both school and major are selected, the silhouette preview below the character subtly pulses, hinting at the evolution to come.

### Screen 3: Effort Slider

**Emotional Target:** Honest self-reflection with compassion.

**Layout:** Centered, single-column, focused. The slider is the hero. Above: the question in text-display Fredoka. Below: a live stat preview panel showing how ERN and ROI shift as the slider moves.

**Key Design Notes:**
- This screen must not feel judgmental. The label "How much time will you have to focus on school?" is carefully worded -- it's about time, not ability or desire.
- The slider has three labeled positions (visible tick marks): 25th percentile ("Working to support myself"), 50th ("Balanced"), 75th ("Full focus on school"). But it's a continuous slider, not three fixed stops.
- The stat preview below shows ERN and ROI values (Space Mono) updating smoothly in real-time as the slider moves. A mini pentagon preview hints at the full reveal coming next.
- Background: slightly darker than Screen 2, building toward the reveal.

### Screen 4: Stage 2 Reveal + Stats

**Emotional Target:** Awe. Pride. "That's ME."

**Layout:** Full viewport reveal. The evolved bear takes center stage -- large, cinematic, with a subtle glow behind. Below: the five-stat pentagon chart. Below that: career title, salary range, skill recommendations.

**Key Design Notes:**
- This is the first "wow" moment. The animation sequence (described in Motion section) must be polished to demo-video quality.
- The bear fills roughly the top 40% of the viewport. Not a thumbnail -- this is a hero image moment.
- The pentagon chart sits centered below the bear, generously sized (300px+ diameter on desktop).
- Career title appears in text-display Fredoka: "Financial Analyst Bear" -- the identity claim.
- Salary range in text-data-large Space Mono. This is the first hard number. Make it prominent.
- Skill recommendations appear as a horizontal row of pill badges below the stats, each showing the stat it boosts in the stat's color.
- CTA: "Fight the Bosses" -- styled as a challenge, perhaps with a subtle shield/sword icon. The transition from this screen's warmth to the boss gauntlet's tension is a key tonal shift.

### Screen 5: Boss Gauntlet

**Emotional Target:** Tension, excitement, humor. "Did I win??"

**Layout:** Full viewport per boss fight. One boss at a time, sequential. Boss monster centered-upper, result below, narrative and historical parallel at bottom.

**Key Design Notes:**
- Each boss fight is a self-contained mini-scene. The background shifts to the boss's signature color (at very low opacity over bg-void) to set the mood.
- Boss entrance animation (described in Motion section) is the visual hook. The boss must feel like it has *personality*.
- Win state: the bear stands triumphant, boss deflates/crumbles (comical), green burst, confetti.
- Lose state: the bear stumbles back (not defeated -- surprised), the boss looms (not terrifying -- smug). Then the historical parallel slides in from below: "You're not alone. When ATMs replaced bank tellers..." This reframes loss as shared human experience, not personal failure.
- Draw state: both bear and boss wobble, yellow stalemate visual. "It's complicated."
- The Final Boss (Fight the Future) gets a special treatment: it assembles from pieces of all mini bosses, shape-shifting. The final scorecard shows all results at once -- a comprehensive report card.
- Between each boss: a brief transition (400ms) that maintains momentum. No screen-clearing. The gauntlet should feel like a GAUNTLET -- rapid, sequential, exciting.

### Screen 6: The Branch Tree

**Emotional Target:** WONDER. The telescope moment. The gasp.

This is the screen that wins the hackathon. It gets disproportionate design attention below in its own section.

### Screen 7: Save + Share

**Emotional Target:** Proud ownership. Social anticipation.

**Layout:** The character card preview takes center stage -- a large, polished preview of the shareable image. Flanked by: build name input (editable, with a fun default like "Build #1: Doctor Bear"), save button, and the download/share button.

**Key Design Notes:**
- The character card preview is rendered at actual aspect ratio (9:16 for stories) in a phone-shaped frame, giving the student a preview of exactly what they'll share.
- "Download Your Card" button is primary, prominent, accent-thrive. This is the viral moment.
- Below the card: two secondary CTAs. "Create Another Build" (leads to character select) and "Compare Your Builds" (leads to compare, only appears if 2+ builds saved).
- Save slots appear below as small RPG-style save cards. Each shows the bear thumbnail, school, major, date. Like a classic RPG save screen.

### Screen 8: Compare Builds

**Emotional Target:** Informed confidence. Decisiveness.

**Layout:** Side-by-side (2 builds) or three-across (3 builds) on desktop. Each column shows: bear portrait, school/major, mini pentagon, boss scorecard, and branch tree thumbnail.

**Key Design Notes:**
- The pentagons overlay when a "Compare Stats" toggle is activated -- both pentagons render on the same chart with transparency, making differences immediately visible.
- Boss scorecards use simple win/lose/draw icons aligned in rows for instant visual comparison.
- Branch tree thumbnails are miniaturized versions of the full tree -- just the shape, enough to see "this build branches more" or "this build has longer branches." Tapping a thumbnail opens the full branch tree.
- A Gemma-generated comparison summary sits at the bottom in a special card with accent-insight border: "Michigan's Creative Director branch has the highest Ceiling of any path across your builds, but Kelley's marketing branches offer stronger AI Resilience at every level."
- Stat deltas shown in Space Mono with green/red coloring: "+2 ERN" or "-1 RES." Instant readability.

---

## The Branch Tree -- Deep Design

This is THE visual. The one that appears in the video. The one judges remember. It must be cinematic, interactive, and emotionally resonant.

### Layout Architecture

**Horizontal tree, growing left to right.**

Why horizontal, not vertical? Three reasons:
1. **Web viewports are wider than tall.** A horizontal tree uses the full width of a desktop browser. A vertical tree wastes horizontal space.
2. **Left-to-right maps to time.** The left is now (Stage 2). The right is the future (Stage 3 endpoints). This is intuitive -- timelines read left to right in Western cultures.
3. **The video reveal.** When the camera "pulls back" to reveal the tree, a horizontal spread across a wide viewport is more cinematic than a vertical drop.

### Visual Structure

```
[Stage 2 Bear]----+----[Node: Stay Technical]----[Node: Sr. Analyst]----[Silhouette: Quant]
                   |                                                     [Silhouette: Portfolio Mgr]
                   |
                   +----[Node: Go Management]----[Node: Team Lead]------[Silhouette: VP Finance]
                   |                                                     [Silhouette: CFO]
                   |
                   +----[Node: Pivot Lateral]----[Node: Consultant]-----[Silhouette: Strategy Dir]
                   |
                   +----[Node: Specialize]-------[Node: Healthcare Fin]-[Silhouette: Hospital CFO]
```

### Node Types

**Root Node (Stage 2 Bear):**
- The fully rendered Stage 2 bear, 120px, centered vertically on the left edge.
- Warm glow emanating outward. This is the "sun" that the branches grow from.
- Career title below in text-heading Fredoka.

**Branch Label Nodes:**
- The fork points: "Stay Technical," "Go Management," etc.
- Styled as rounded pills: bg-surface, text-primary, radius-full, 36px height.
- On hover: subtle glow in the branch's dominant stat color.

**Career Progression Nodes:**
- Individual career steps: "Sr. Analyst," "Team Lead," etc.
- Smaller pills: bg-mid, text-secondary, radius-lg, 28px height.
- Connected by branch lines.

**Endpoint Nodes (Stage 3 Silhouettes):**
- Silhouetted bear outlines at each terminal branch.
- 80px, dark silhouette against bg-void, subtle ambient glow.
- On hover: silhouette brightens, mini stat preview appears.
- On click: full stat panel slides in from the right.

### Branch Lines

The lines connecting nodes are not boring straight lines. They are **smooth bezier curves** with:
- 2px stroke width in a gradient from the Stage 2 bear's glow to the endpoint's stat color.
- Subtle animated particles flowing along the lines (very sparse, 2-3 particles per branch, slow drift). Like energy flowing along the path.
- On branch selection: the selected branch line thickens to 3px and glows (shadow-glow in accent-thrive). Unselected branches dim to 30% opacity.

### The Reveal Animation

This is the most important animation in the entire product. In the demo video, this is the moment.

1. **Starting state:** Stage 2 bear alone on the left, full viewport is dark (bg-void).
2. **Beat 1 (0-300ms):** Subtle glow begins emanating from the bear. Warm. Organic.
3. **Beat 2 (300-800ms):** First branch lines begin drawing outward from the bear, like roots growing. The lines draw with an organic easing -- fast at first, then gently decelerating. Each main branch starts simultaneously but reaches different lengths at different times.
4. **Beat 3 (800-1500ms):** Branch label nodes pop in at the first fork points with spring-bouncy. Staggered 100ms.
5. **Beat 4 (1500-2200ms):** Secondary branch lines continue drawing. Career progression nodes appear with spring-smooth.
6. **Beat 5 (2200-3000ms):** Endpoint silhouettes fade in at the terminal positions. Each one gets a brief 150ms pulse of ambient glow as it appears.
7. **Beat 6 (3000-3500ms):** Particles begin drifting along the branch lines. The full tree is visible. The viewport is alive.

Total: ~3.5 seconds from empty to full tree. This is the "gasp" moment.

### Interaction Model

- **Default state:** All branches visible at medium opacity. No branch selected.
- **Hover on branch:** Branch line brightens, nodes along that branch glow. Other branches dim slightly.
- **Click on endpoint silhouette:** Selected branch fully illuminates. A detail panel slides in from the right (40% viewport width) showing:
  - Branch name and path description
  - Full stat pentagon for this branch endpoint
  - Boss fight results (recalculated for this branch)
  - Skill unlock requirements (read-only text list)
  - Cost to unlock (grad school, certifications, years)
- **Click another endpoint:** Panel content cross-fades (200ms) to the new branch. Previously selected branch dims, new one illuminates.
- **Close panel:** Panel slides out right. All branches return to default state.

### Responsive Considerations

On smaller viewports (tablet, mobile), the horizontal tree won't fit. The responsive strategy:
- **Desktop (1200px+):** Full horizontal tree as described. This is the demo-video target.
- **Tablet (768-1199px):** Tree zooms to fit, with pinch-to-zoom enabled. Detail panel becomes a bottom sheet instead of right panel.
- **Mobile (below 768px):** Tree collapses into a vertical list of branches, each expandable. The tree visualization becomes a simplified vertical timeline. Less cinematic, still functional.

---

## Boss Fights -- Deep Design

### Visual Language of Tension

The boss fights must feel like mini-games within the larger RPG flow. They borrow visual language from classic RPG battle screens while maintaining the plush softness.

**The Battle Arena:**
- Background shifts to bg-void with the boss's signature color as a subtle radial gradient from center (at 8% opacity).
- Vignette effect around the viewport edges (darker corners) creates focus.
- The bear appears on the left side, slightly smaller than its Stage 2 reveal (showing vulnerability).
- The boss monster appears on the right, slightly above the bear (showing threat).

**Visual Language of Tension:**
- Viewport very subtly pulses at the boss's color (opacity oscillates 0% to 4% and back, 2-second cycle). Barely perceptible but creates unease.
- The stat(s) being tested float between the combatants, highlighted in their stat colors. These are the battleground.
- A brief "calculating" moment (800ms) where the stats shimmer -- building suspense before the result.

**Visual Language of Resolution:**

*Win:*
- Boss crumbles/deflates with a comical "poof" (spring-bouncy, scale to 0)
- Green burst of particles from the bear's position
- Bear bounces once (spring-bouncy)
- "WIN" in text-display Fredoka, accent-thrive, scales in from center
- Brief victory stat summary

*Lose:*
- Bear stumbles back (translate-x 20px left, spring-smooth)
- Boss grows slightly (scale to 1.1, spring-bouncy)
- Screen shakes (3px random transform, 300ms)
- Red flash on viewport edges (accent-alert at 10% opacity, 200ms)
- Then: the recovery. The bear straightens up. The historical parallel slides in from below.
- "This happened before..." in text-subheading, accent-info. Compassionate, not crushing.
- Historical parallel card with a warm border (accent-empathy)

*Draw:*
- Both combatants wobble (rotate 3deg back and forth, 3 cycles, spring-smooth)
- Yellow shimmer (accent-caution particles)
- "DRAW" in text-display, accent-caution
- "It's complicated" narrative from Gemma

### The Final Boss: Fight the Future

Special treatment. This is the gauntlet's climax.

- The Final Boss assembles on-screen from fragments of all previous bosses (the robot's arm, the bill creature's envelope, the ice wall's frost). It's a chimera of all career threats.
- The fight tests the composite -- all stats are on the field.
- The result is a SCORECARD, not a single win/lose. A grid showing all 5 mini-boss results plus the composite grade.
- The scorecard is designed as a "character sheet" -- parchment-style card (bg-raised with slight warm tint), RPG-formatted, with iconographic win/lose/draw indicators.

---

## Character System -- Deep Design

### The Animal Species

6-8 species for MVP. Each should have a distinct personality archetype that students project onto, but none should feel "better" or "for" a specific career.

| Species | Personality Vibe | Why It Works |
|---------|-----------------|-------------|
| Bear | Sturdy, reliable, warm | The flagship. Universal appeal. The "default" without feeling generic. |
| Bunny | Quick, adaptable, alert | Energy and agility. Appeals to students who see themselves as nimble. |
| Fox | Clever, strategic, sharp | The thinker. Appeals to students who pride themselves on strategy. |
| Turtle | Steady, wise, patient | The long game. Appeals to students who value persistence over speed. |
| Squirrel | Energetic, resourceful, social | The hustler. Appeals to students who are always doing five things at once. |
| Owl | Observant, analytical, calm | The scholar. Appeals to students who lean into study and knowledge. |
| Cat | Independent, creative, curious | The creative. Appeals to students who chart their own path. |
| Deer | Gentle, community-minded, graceful | The helper. Appeals to students drawn to service and care professions. |

### Evolution Visual Language

**Stage 1 (Student):**
- Small in frame (70% of the render area). Scruffy fur (visible texture variation). Oversized backpack. Wide, uncertain eyes. Slight head tilt. Posture is slightly slouched. Color palette is muted -- the bear hasn't "bloomed" yet.
- The energy is: "I'm here. I don't know what's next. But I'm here."

**Stage 2 (Post-Grad Career):**
- 20-30% larger in frame. Clean, groomed fur. Career-specific gear (miniaturized, toylike). Standing straight. Eyes confident with a subtle sparkle. A warm backlight glow in the career's dominant stat color. The bear has *arrived.*
- The energy is: "I know who I am now. I'm ready."

**Stage 3 (Branch Silhouettes):**
- Not fully rendered art -- CSS/design treatment.
- Dark silhouette of an evolved bear outline against bg-void.
- Subtle ambient glow at the edges (in the branch's dominant stat color, very low opacity).
- On reveal (tap/click): the silhouette brightens, a mini pentagon appears beside it, stats visible.
- The energy is: "I could become this. What would that look like?"
- The silhouettes create INTRIGUE. They're possibilities, not certainties. The mystery is the point.

### Accessories and Inclusion

The accessory system is the inclusion layer. Every animal can be anyone.

**Accessory Categories:**
- Mobility: wheelchair, prosthetic limb, cane
- Sensory: hearing aid, glasses, sunglasses
- Cultural: hijab, yarmulke, turban, bindi
- Identity: pride pin, trans flag pin, binder
- Expression: different fur/skin tones (continuous slider, not preset options)

**Design Rules:**
- Accessories persist through evolution. Student bear's hijab appears on the career bear.
- Accessories are rendered as overlays on the base character art. They should feel integrated, not slapped on.
- No accessory changes the character's capabilities or stats. Ever. They are pure identity expression.
- The fur/skin color slider produces a warm spectrum (not neon or unnatural).

---

## Dark Mode Philosophy

FutureProof is dark-first. There is no light mode. The darkness is the design.

### Why Dark Only

1. **Cinematic framing.** The rendered Midjourney bears, the glowing branch tree, the boss fight arenas -- all of these look dramatically better against dark backgrounds. Light backgrounds would wash out every visual element.
2. **Focus and immersion.** Dark UIs reduce visual noise and draw attention to content. The student's focus should be on their bear, their stats, their branches -- not the chrome around them.
3. **The "telescope" metaphor.** FutureProof is looking into the future. The future is dark until you illuminate it. Light mode would undermine the core visual metaphor.
4. **Demo video.** Screen recordings of dark UIs look dramatically better in video than light UIs. For a hackathon where 30% of judging is the video, this matters.

### What Kind of Dark

Not all dark modes are created equal.

**Not this:** Pure black (#000000) backgrounds with bright white text. This is "dark mode for battery savings" -- it's high-contrast and fatiguing. OLED dark mode.

**Not this:** Dark grey (#1a1a1a) with blue accents. This is "corporate dark mode" -- it's the VS Code aesthetic. Professional but emotionally empty.

**This:** Deep indigo-navy (#1B1D30) with warm white text (#F5F0E8) and multi-colored accents. This is "night sky dark mode" -- it's rich, warm, and alive. The indigo undertone prevents the coldness that pure grey/black creates. The warm white text prevents the clinical feeling that blue-white (#ffffff) creates. The colored accents are stars in the sky.

### Dark Mode Rules

- Never use pure black (#000000) anywhere. The deepest color is bg-void (#12131F).
- Never use pure white (#ffffff) for text. The brightest text is text-primary (#F5F0E8), which has a warm yellow-cream undertone.
- All accent colors are calibrated for WCAG AA contrast against bg-deep. Most achieve AAA.
- Borders between elevation layers use rgba white at 4-10% opacity, not solid colors. This creates soft separation without harsh lines.
- Gradients in backgrounds always move from darker to slightly less dark -- never from dark to light.

---

## Responsive Strategy

### Priority Order

1. **Desktop (1440px target, 1200px minimum):** The hackathon demo viewport. Every design decision optimizes for this first. The branch tree spreads wide. The compare screen goes three-across. The boss fights are cinematic.
2. **Tablet (768-1199px):** Functional and attractive. Branch tree scales or restructures. Compare goes two-across.
3. **Mobile (below 768px):** Students WILL access this on phones. It must work. But it doesn't need to be the cinematic experience. Branch tree becomes a vertical list. Compare becomes sequential.

### Breakpoint Tokens

| Token | Value | Target |
|-------|-------|--------|
| `bp-mobile` | 480px | Small phones |
| `bp-tablet` | 768px | Tablets, small laptops |
| `bp-desktop` | 1200px | Standard desktop |
| `bp-wide` | 1440px | Wide desktop (demo target) |
| `bp-ultra` | 1920px | Large monitors |

### Layout Strategy

**Desktop:** Max content width 1280px, centered. Branch tree is full-width (no max-width constraint). Side panels for detail views.

**Tablet:** Single column with full-width cards. Branch tree uses pinch/zoom. Detail panels become bottom sheets.

**Mobile:** Single column, stacked. Branch tree collapses to a list. Pentagon chart scales down to 200px. Boss fights retain the one-at-a-time sequential flow (works well on mobile). Character card preview scales down.

### Container Spacing

| Token | Mobile | Tablet | Desktop |
|-------|--------|--------|---------|
| `space-page-x` | 16px | 24px | 32px |
| `space-page-y` | 16px | 24px | 32px |
| `space-section` | 24px | 32px | 48px |
| `space-card-gap` | 12px | 16px | 20px |
| `space-inline` | 8px | 8px | 8px |

---

## Frontend Stack Recommendations

### Core

| Library | Version | Purpose |
|---------|---------|---------|
| **React** | 19 | UI framework |
| **TypeScript** | 5.x | Type safety |
| **Vite** | 6.x | Build tool, dev server |
| **Tailwind CSS** | 4.x | Utility-first CSS with design tokens |

### UI Components

| Library | Purpose | Why This One |
|---------|---------|-------------|
| **shadcn/ui** | Base component primitives | Unstyled, accessible, composable. We theme everything to Brightpath. No vendor lock-in -- the components live in our codebase. |
| **Radix UI** | Accessible primitives (under shadcn) | Rock-solid accessibility. Handles focus traps, keyboard nav, screen readers. |

### Visualization

| Library | Purpose | Why This One |
|---------|---------|-------------|
| **React Flow** | Branch tree (Screen 6) | Purpose-built for node-based diagrams with pan/zoom. Handles the tree layout, edge rendering, node positioning, and interaction model. Custom node components give us full visual control. |
| **Recharts** | Pentagon radar chart | Simple, declarative, React-native. The RadarChart component does exactly what we need for the five-stat pentagon. |

### Animation

| Library | Purpose | Why This One |
|---------|---------|-------------|
| **Framer Motion** | All meaningful animations | Spring physics, layout animations, gesture handling, AnimatePresence for enter/exit. The boss fight sequences, stage reveals, and branch tree illumination all need springs, not CSS timing functions. |

### Fonts

| Font | Source | Loading Strategy |
|------|--------|-----------------|
| **Fredoka** (variable) | Google Fonts | `font-display: swap`, preloaded in `<head>`. Variable weight 300-700. |
| **Nunito** | Google Fonts | `font-display: swap`, preloaded. Weights: 400, 600, 700. |
| **Space Mono** | Google Fonts | `font-display: swap`. Weights: 400, 700. |

### Utilities

| Library | Purpose |
|---------|---------|
| **clsx** or **tailwind-merge** | Conditional class composition |
| **Zustand** | Lightweight state management (build data, save slots) |
| **TanStack Query** | Server state (Gemma/API calls with caching) |
| **Zod** | Runtime type validation for API responses |

---

## Design Tokens

The complete token set, ready for implementation in Tailwind config and/or CSS custom properties.

### Colors

```css
:root {
  /* Backgrounds */
  --color-bg-void: #12131F;
  --color-bg-deep: #1B1D30;
  --color-bg-mid: #232545;
  --color-bg-surface: #2D3060;
  --color-bg-raised: #3A3D75;

  /* Accents */
  --color-accent-thrive: #7DD4A3;
  --color-accent-alert: #F4A97E;
  --color-accent-caution: #F2D477;
  --color-accent-insight: #B8A9E8;
  --color-accent-info: #7BB8E0;
  --color-accent-empathy: #E88BA9;

  /* Stats */
  --color-stat-ern: #F2D477;
  --color-stat-roi: #7DD4A3;
  --color-stat-res: #B8A9E8;
  --color-stat-grw: #7BB8E0;
  --color-stat-hmn: #E88BA9;

  /* Text */
  --color-text-primary: #F5F0E8;
  --color-text-secondary: #C4BFB0;
  --color-text-muted: #8A8595;
  --color-text-inverse: #1B1D30;

  /* Boss Colors */
  --color-boss-ai: #B8A9E8;
  --color-boss-loans: #F4A97E;
  --color-boss-market: #7BB8E0;
  --color-boss-burnout: #E88BA9;
  --color-boss-ceiling: #C4BFB0;

  /* Borders */
  --color-border-subtle: rgba(255, 255, 255, 0.06);
  --color-border-default: rgba(255, 255, 255, 0.1);
  --color-border-strong: rgba(255, 255, 255, 0.2);
}
```

### Typography

```css
:root {
  /* Font Families */
  --font-display: 'Fredoka', sans-serif;
  --font-body: 'Nunito', sans-serif;
  --font-data: 'Space Mono', monospace;

  /* Font Sizes */
  --text-hero: 3rem;          /* 48px */
  --text-display: 2.25rem;    /* 36px */
  --text-heading: 1.75rem;    /* 28px */
  --text-subheading: 1.375rem;/* 22px */
  --text-body: 1rem;          /* 16px */
  --text-small: 0.875rem;     /* 14px */
  --text-micro: 0.75rem;      /* 12px */
  --text-data-large: 1.5rem;  /* 24px */
  --text-data: 1rem;          /* 16px */
  --text-data-small: 0.8125rem;/* 13px */

  /* Line Heights */
  --leading-tight: 1.1;
  --leading-snug: 1.2;
  --leading-normal: 1.5;
  --leading-relaxed: 1.4;
}
```

### Spacing

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
}
```

### Radii

```css
:root {
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --radius-full: 9999px;
}
```

### Shadows

```css
:root {
  --shadow-sm: 0 2px 8px rgba(27, 29, 48, 0.5);
  --shadow-md: 0 4px 16px rgba(27, 29, 48, 0.6);
  --shadow-lg: 0 8px 32px rgba(27, 29, 48, 0.7);
  --shadow-glow-thrive: 0 0 20px rgba(125, 212, 163, 0.3);
  --shadow-glow-alert: 0 0 20px rgba(244, 169, 126, 0.3);
  --shadow-glow-caution: 0 0 20px rgba(242, 212, 119, 0.3);
  --shadow-glow-insight: 0 0 20px rgba(184, 169, 232, 0.3);
  --shadow-glow-info: 0 0 20px rgba(123, 184, 224, 0.3);
  --shadow-glow-empathy: 0 0 20px rgba(232, 139, 169, 0.3);
}
```

### Motion

```css
:root {
  /* Framer Motion springs (used in JS, documented here for reference) */
  --spring-bouncy-stiffness: 300;
  --spring-bouncy-damping: 20;
  --spring-smooth-stiffness: 200;
  --spring-smooth-damping: 25;
  --spring-gentle-stiffness: 150;
  --spring-gentle-damping: 30;
  --spring-snappy-stiffness: 400;
  --spring-snappy-damping: 25;

  /* CSS transitions (for simple hover/focus states) */
  --transition-fast: 150ms ease-out;
  --transition-normal: 200ms ease-out;
  --transition-slow: 300ms ease-out;

  /* Stagger delays */
  --stagger-fast: 50ms;
  --stagger-normal: 80ms;
  --stagger-slow: 100ms;
}
```

### Breakpoints

```css
:root {
  --bp-mobile: 480px;
  --bp-tablet: 768px;
  --bp-desktop: 1200px;
  --bp-wide: 1440px;
  --bp-ultra: 1920px;
}
```

---

## Tailwind Configuration Sketch

```typescript
// tailwind.config.ts (key sections)
export default {
  theme: {
    extend: {
      colors: {
        bg: {
          void: '#12131F',
          deep: '#1B1D30',
          mid: '#232545',
          surface: '#2D3060',
          raised: '#3A3D75',
        },
        accent: {
          thrive: '#7DD4A3',
          alert: '#F4A97E',
          caution: '#F2D477',
          insight: '#B8A9E8',
          info: '#7BB8E0',
          empathy: '#E88BA9',
        },
        stat: {
          ern: '#F2D477',
          roi: '#7DD4A3',
          res: '#B8A9E8',
          grw: '#7BB8E0',
          hmn: '#E88BA9',
        },
        text: {
          primary: '#F5F0E8',
          secondary: '#C4BFB0',
          muted: '#8A8595',
          inverse: '#1B1D30',
        },
      },
      fontFamily: {
        display: ['Fredoka', 'sans-serif'],
        body: ['Nunito', 'sans-serif'],
        data: ['Space Mono', 'monospace'],
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '14px',
        xl: '20px',
      },
      boxShadow: {
        sm: '0 2px 8px rgba(27, 29, 48, 0.5)',
        md: '0 4px 16px rgba(27, 29, 48, 0.6)',
        lg: '0 8px 32px rgba(27, 29, 48, 0.7)',
      },
    },
  },
}
```

---

## Summary: What Brightpath Is

Brightpath is a design system for a product that sits at the intersection of game, tool, and telescope. It is:

- **Dark and cinematic** because the student is looking into the future, and the future starts dark until you illuminate it.
- **Warm and plush** because the decisions being made are terrifying, and the design must make them feel safe to explore.
- **Data-dense but never clinical** because every stat, every salary figure, every boss fight result is backed by real data, but the data is rendered through the lens of play and personality.
- **Progressive in its illumination** because the student starts not knowing, and ends seeing their entire branching future lit up across the screen.

The branch tree is the product. The bears are the hook. The data is the spine. Brightpath is the skin that makes all three feel like they belong in the same world.

*A college degree isn't a destination. It's a starting position. Brightpath lights the way forward.*
