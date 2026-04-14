# Brightpath Design System Audit Report

**Date:** 2026-04-13
**Auditor:** @design-builder (Claude Code)
**Design System:** DESIGN.md (Brightpath)
**Files Audited:** 16

---

## Summary

Audited all frontend implementation files against DESIGN.md: 4 infrastructure files (tokens.css, motion.ts, index.css, tailwind.config.ts), 6 component files, 4 screen files, 1 test file, and 1 entry file. Token infrastructure is excellent — tokens.css, motion.ts, and tailwind.config.ts are fully compliant with DESIGN.md. Component and screen files have several violations, primarily around Button spec deviations, missing secondary button hover styles, TextInput background color, and inconsistent use of font-family tokens where the type scale mandates specific fonts. No hardcoded hex values found in component/screen files — all colors reference tokens.

---

## frontend/src/styles/tokens.css

### PASS
- All background hex values match DESIGN.md exactly (lines 16-20)
- All accent hex values match DESIGN.md exactly (lines 26-31)
- All stat color hex values match DESIGN.md exactly (lines 37-41)
- All text color hex values match DESIGN.md exactly (lines 47-50)
- All boss color hex values match DESIGN.md exactly (lines 56-60)
- All border rgba values match DESIGN.md exactly (lines 66-68)
- All state rgba values match DESIGN.md exactly (lines 74-79)
- All font family definitions match DESIGN.md (lines 84-86)
- Full type scale matches DESIGN.md 1:1, including the CTA size token (lines 89-103)
- Line heights defined (lines 106-109)
- Border radii match DESIGN.md exactly (lines 115-119)
- All shadow tokens match DESIGN.md exactly (lines 125-133)
- Spacing scale matches DESIGN.md exactly (lines 139-149)
- Transition durations match DESIGN.md exactly (lines 156-158)
- Breakpoint reference values match DESIGN.md exactly (lines 164-168)

### FAIL
- None

### WARNINGS
- Line 2: Comment says "Generated from: docs/design-system-proposal.md" — should reference DESIGN.md as the canonical source. Non-blocking.
- Line 107: `--leading-snug: 1.2` — DESIGN.md type scale uses 1.2 for title/heading/display but also 1.15 for display specifically. The token name is generic; consider separate line-height tokens per type level. Non-blocking.

---

## frontend/tailwind.config.ts

### PASS
- All background color mappings use CSS variables correctly (lines 20-26)
- All accent color mappings correct (lines 28-34)
- All stat color mappings correct (lines 36-41)
- All text color mappings correct (lines 43-48)
- All boss color mappings correct (lines 50-56)
- Border color mappings correct, including DEFAULT alias (lines 57-59)
- State color mappings correct (lines 61-67)
- Focus ring mapping correct (lines 69-71)
- Font families match DESIGN.md (lines 72-75)
- Full type scale with correct sizes and line-heights (lines 77-92)
- Border radii match DESIGN.md exactly (lines 93-99)
- Shadow tokens reference CSS variables correctly (lines 100-110)
- Spacing scale matches DESIGN.md (lines 112-123)
- Breakpoints match DESIGN.md (lines 124-130)
- Transition durations match DESIGN.md (lines 131-135)

### FAIL
- None

### WARNINGS
- DESIGN.md Tailwind classes use `text-text-primary`, `bg-bp-void`, etc. The Tailwind config structure produces these correctly. No issues.

---

## frontend/src/styles/motion.ts

### PASS
- `springs.bouncy` matches DESIGN.md: stiffness 300, damping 20 (line 17)
- `springs.smooth` matches DESIGN.md: stiffness 200, damping 25 (line 20)
- `springs.gentle` matches DESIGN.md: stiffness 150, damping 30 (line 23)
- `springs.snappy` matches DESIGN.md: stiffness 400, damping 25 (line 26)
- `stagger.fast` = 0.05 (50ms) matches DESIGN.md (line 35)
- `stagger.normal` = 0.08 (80ms) matches DESIGN.md (line 38)
- `stagger.slow` = 0.1 (100ms) matches DESIGN.md (line 41)
- `transitions.fadeInUp` uses y:24 and smooth spring, matches DESIGN.md (lines 50-54)
- `transitions.scaleIn` uses scale:0.8 and bouncy spring, matches DESIGN.md (lines 57-61)
- `transitions.fade` uses 300ms ease-out, matches DESIGN.md (lines 64-67)
- `transitions.press` uses scale 0.97 and snappy spring, matches DESIGN.md (lines 70-74)
- `staggerContainer` and `staggerItem` variants match DESIGN.md spec (lines 82-101)
- `scaleItem` uses scale 0.85 and bouncy spring, matches DESIGN.md (lines 104-111)
- Stage 2 reveal sequence timing matches DESIGN.md exactly (lines 118-145)
- Boss fight sequences match DESIGN.md (lines 148-174)
- Branch tree timing matches DESIGN.md exactly (lines 177-207)

### FAIL
- None

### WARNINGS
- None

---

## frontend/src/index.css

### PASS
- Google Fonts import includes correct weights: Fredoka 400-700, Nunito 400/600/700/800, Space Mono 400/700 (line 1)
- tokens.css imported correctly (line 2)
- Body uses `var(--color-bg-void)` and `var(--color-text-primary)` (lines 10-11)
- `stat-label-fade` animation: 1s ease-out, matches DESIGN.md (lines 19-22)
- `vertex-glow-pulse` animation: 4s ease-in-out infinite, matches DESIGN.md (lines 30-33)
- `ambient-breathe` animation: 6s ease-in-out infinite, matches DESIGN.md (lines 40-43)
- `twinkle` animation: 4s ease-in-out infinite, opacity 0.05 to 0.45, matches DESIGN.md (lines 62-65)
- Star element: 2px dimensions, uses `var(--color-text-primary)` and `var(--radius-full)`, matches DESIGN.md (lines 67-75)
- Noise overlay: fixed, 2.5% opacity, SVG fractal noise, matches DESIGN.md (lines 78-87)
- Gradient tagline uses accent-thrive to accent-info gradient (lines 90-95)

### FAIL
- None

### WARNINGS
- Line 52: Ambient glow uses hardcoded rgba values `rgba(125,212,163,0.06)`, `rgba(184,169,232,0.04)`, `rgba(123,184,224,0.03)` instead of referencing accent token variables with opacity. These are thrive/insight/info colors at very low opacity for a decorative gradient, so using CSS variables with opacity modifiers would be more maintainable but is not strictly a violation since DESIGN.md describes this as a "thrive + insight + info blend" without specifying exact implementation. Non-blocking.

---

## frontend/src/components/ui/Button.tsx

### PASS
- Uses `rounded-lg` (14px), matches DESIGN.md Buttons spec (line 29)
- Uses `font-body`, matches DESIGN.md "All buttons: font-body" (line 29)
- Primary variant uses `bg-accent-thrive`, matches DESIGN.md (line 14)
- Primary variant uses `text-text-inverse`, matches DESIGN.md (line 14)
- Primary variant uses `text-cta` (17px), matches DESIGN.md (line 14)
- Primary variant uses `font-bold` (700), matches DESIGN.md (line 14)
- Primary hover adds `shadow-glow-thrive`, matches DESIGN.md (line 14)
- Press feedback uses `scale: 0.97`, matches DESIGN.md (line 34)
- Uses `springs.snappy` for press transition, matches DESIGN.md (line 35)
- Uses `transition-all duration-normal`, matches DESIGN.md (line 29)

### FAIL
- **Primary button height**: Expected `48px` (h-12) per DESIGN.md Buttons table, no explicit height set. Relies on padding instead. Line 14 uses `py-4` (16px top + bottom = 32px padding) which with text-cta (17px) yields approximately correct height, but DESIGN.md specifies explicit 48px height.
- **Primary button padding**: Expected `0 28px` per DESIGN.md Buttons table, found `px-10` (40px) at line 14. DESIGN.md specifies 28px horizontal padding.
- **Primary hover darkening**: DESIGN.md specifies hover darkens to `#6bc494`. No darken effect implemented — only glow shadow is added. Line 14.
- **Secondary variant wrong**: DESIGN.md specifies Secondary as `transparent` background with `accent-info` text, height 44px, padding `0 24px`. Implementation at line 16 uses `bg-bp-surface` background and `text-text-secondary` text — this matches neither the background nor the text color per DESIGN.md.
- **Missing button variants**: DESIGN.md defines Ghost, Danger, and Icon variants. Only Primary and Secondary are implemented. Lines 6, 12-17.

### WARNINGS
- Hover uses `scale: 1.02` (line 33) which is not in DESIGN.md — DESIGN.md only specifies press at 0.97, no hover scale.

---

## frontend/src/components/ui/TextInput.tsx

### PASS
- Uses `font-body` and `text-body` (16px), matches DESIGN.md Input spec (line 8)
- Uses `text-text-primary` for text color, matches DESIGN.md (line 8)
- Uses `px-4 py-3` — 16px horizontal and 12px vertical, matches DESIGN.md padding `12px 16px` (line 8)
- Uses `rounded-md` (10px), matches DESIGN.md `radius-md` (line 8)
- Uses `border border-border-subtle`, matches DESIGN.md (line 8)
- Uses `transition-colors duration-normal`, appropriate for input states (line 8)
- Uses `placeholder:text-text-muted`, appropriate (line 8)

### FAIL
- **Input background color**: Expected `bg-bp-deep` (`#1B1D30`) per DESIGN.md Input spec, found `bg-bp-mid` (`#232545`) at line 8. DESIGN.md clearly states input background is `bg-deep`.
- **Focus border color**: Expected `accent-info` (`#7BB8E0`) per DESIGN.md Input Focus spec, found `focus:border-border-strong` at line 8. DESIGN.md specifies `border-color: accent-info` on focus, not `border-strong`.
- **Focus ring missing**: DESIGN.md specifies `box-shadow: 0 0 0 3px rgba(123, 184, 224, 0.15)` on focus. No focus ring/shadow implemented. Line 8.
- **Input height missing**: DESIGN.md specifies `height: 48px`. No explicit height set. Line 8.

### WARNINGS
- No label element rendered — DESIGN.md specifies input labels with `14px`, `weight 600`, `text-secondary`, `margin-bottom: 6px`. The `label` prop only sets `aria-label`, not a visible label. This may be intentional depending on usage context.

---

## frontend/src/components/ui/StatBadge.tsx

### PASS
- Uses `font-data` for stat abbreviation and value, appropriate per DESIGN.md (lines 15, 21)
- Uses `text-text-muted` for the label text (line 33)
- Uses `springs.snappy` for value animation, appropriate micro-interaction (line 25)
- Animation pattern (fade + slide) is clean and consistent with design system motion philosophy

### FAIL
- None

### WARNINGS
- Uses `text-sm` (Tailwind default 14px/0.875rem) and `text-xs` (12px/0.75rem) — these happen to align with DESIGN.md `text-small` and `text-micro` respectively, but using the design system token names (`text-small`, `text-micro`) would be more explicit.

---

## frontend/src/components/ui/BuildSummaryBar.tsx

### PASS
- Uses `bg-bp-mid` for background (line 15)
- Uses `text-text-primary`, `text-text-muted`, `text-text-secondary` correctly (lines 21, 24, 26)
- Uses `springs.smooth` for entrance animation (line 18)

### FAIL
- **Non-existent Tailwind class**: `rounded-bp-sm` at line 15 is not a valid Tailwind class. The design system defines `rounded-sm` (6px). The `rounded-bp-sm` pattern does not exist in tailwind.config.ts. This will produce no border-radius.

### WARNINGS
- Uses `text-sm` (line 15) instead of the design-system-specific `text-small`. While equivalent, it's less explicit.
- `font-semibold` (weight 600) used at line 21 — no explicit DESIGN.md guidance for this component, but generally acceptable.

---

## frontend/src/components/ui/SegmentedControl.tsx

### PASS
- Uses `bg-bp-surface` for container background (line 46)
- Uses `text-text-primary` and `text-text-secondary` for selected/unselected states (lines 64-66)
- Uses `springs.snappy` for the animated indicator, matches micro-interaction spring (line 74)
- Uses `duration-fast` (150ms) for transition, matches DESIGN.md (line 63)
- Keyboard navigation implemented (ArrowRight/Down, ArrowLeft/Up) (lines 32-42)
- ARIA radiogroup pattern implemented correctly (lines 47-49, 58-60)

### FAIL
- **Non-existent Tailwind class**: `rounded-bp-md` at lines 46, 63, 72. Not a valid Tailwind class — should be `rounded-md`. This will produce no border-radius.
- **Non-existent Tailwind class**: `rounded-bp-sm` at lines 63, 72. Not a valid Tailwind class — should be `rounded-sm`. This will produce no border-radius.

### WARNINGS
- Uses `text-sm` (lines 78-79) instead of design system `text-small`/`text-micro`. Non-blocking.
- Uses `text-xs` (line 83) instead of `text-micro`. Non-blocking.
- This component is not explicitly defined in DESIGN.md, so it's a net-new pattern (drift).

---

## frontend/src/components/landing/PentagonGlow.tsx

### PASS
- Uses CSS variable references for stat colors: `var(--color-stat-ern)`, etc. (lines 4-8, 67-71)
- Uses `font-data` and `text-stat-label` for axis labels, matches DESIGN.md Pentagon spec (line 23)
- Uses `tracking-widest` for uppercase label spacing (line 23)
- Uses `stat-label-fade` class from index.css (line 23)
- Vertex dots use correct stat colors (lines 67-71)
- Vertex dot animation: opacity pulse, 4s duration, matches DESIGN.md `vertex-glow-pulse` concept (line 74)
- 6s bobbing animation for the pentagon container (line 17)
- SVG grid rings use rgba white at low opacity, consistent with DESIGN.md Pentagon grid spec (lines 45-47)
- SVG axis lines use rgba white at low opacity (lines 50-54)

### FAIL
- **Hardcoded rgba in SVG filter**: Line 34 uses `drop-shadow(0 0 40px rgba(125,212,163,0.12))` — hardcoded thrive color. Should reference the token or use a consistent approach.
- **Grid ring opacity values differ from spec**: DESIGN.md Pentagon spec says grid stroke is `text-muted at 15% opacity`. Implementation uses `rgba(255,255,255,0.06)`, `rgba(255,255,255,0.04)`, `rgba(255,255,255,0.03)` at lines 45-47. These are white at 3-6% opacity, not muted at 15%. Different base color (white vs. `#8A8595`) and different opacity.
- **Axis line opacity differs from spec**: DESIGN.md says axes use `text-muted at 20% opacity`. Implementation uses `rgba(255,255,255,0.05)` at lines 50-54 — white at 5%, not muted at 20%.
- **Vertex dot radius**: DESIGN.md says 5px radius. Implementation uses `r="3.5"` at line 73 (3.5px radius). The spec also calls for 10px glow circles at 20% opacity, which are not rendered.

### WARNINGS
- The SVG gradient uses hardcoded rgba stops at lines 38-40 rather than CSS variable references. SVG gradients have limited CSS variable support, so this is a known constraint.
- This is a decorative/landing-page pentagon, not the full data pentagon — some spec deviations may be intentional for the simplified hero version.

---

## frontend/src/components/landing/PentagonGlow.test.tsx

### PASS
- Test file, not subject to design audit.

### FAIL
- N/A

### WARNINGS
- None

---

## frontend/src/components/school/SchoolSearch.tsx

### PASS
- Uses `bg-bp-surface`, `text-text-primary`, `font-body`, `text-body` for input (line 134)
- Uses `rounded-bp-md` for border radius (see FAIL below)
- Uses `border-border-subtle` for default border (line 134)
- Uses `focus:border-accent-insight` — close to DESIGN.md focus color (DESIGN.md says `accent-info` but `accent-insight` is a reasonable alternative for the school search context)
- Uses `placeholder:text-text-muted` (line 134)
- Uses `transition-colors duration-normal` (line 134)
- Dropdown uses `bg-bp-raised`, `border-border-subtle`, `shadow-lg` (line 153)
- Selected state uses `bg-bp-surface`, `border-border-subtle` (line 105)
- Uses `springs.smooth` for selected state entrance (line 108)
- Uses `text-text-muted` for clear button, `hover:text-text-secondary` (line 115)
- Uses `duration-fast` for transitions (lines 115, 165)
- Highlighted dropdown item uses `bg-accent-insight/15` — follows the 15% accent opacity pill pattern (line 167)
- Error text uses `text-text-muted` (line 184)

### FAIL
- **Non-existent Tailwind class**: `rounded-bp-md` at lines 105, 134, 153. Should be `rounded-md`. This will produce no border-radius.
- **Input focus color**: Line 134 uses `focus:border-accent-insight` — DESIGN.md Input Focus spec says `border-color: accent-info`. Insight (purple) is used instead of info (blue).
- **Input background**: Line 134 uses `bg-bp-surface` (`#2D3060`) — DESIGN.md Input spec says `background: bg-deep (#1B1D30)`.

### WARNINGS
- No focus ring shadow implemented (DESIGN.md specifies `0 0 0 3px rgba(123, 184, 224, 0.15)`).

---

## frontend/src/components/school/MajorInput.tsx

### PASS
- Uses `bg-bp-surface`, `text-text-primary`, `font-body`, `text-body` for input (line 175)
- Uses `border-border-subtle` for default border (line 175)
- Uses `focus:border-accent-insight` for focus state (line 175)
- Uses `placeholder:text-text-muted` (line 175)
- Uses `transition-colors duration-normal` (line 175)
- Uses `springs.smooth` for card animations (lines 228, 296, 320, 369)
- Match card uses `bg-bp-raised`, `border border-accent-insight/20`, `shadow-glow-insight` (line 224)
- Confirm button uses `bg-accent-thrive`, `hover:shadow-glow-thrive` (line 272)
- "Not quite" button uses `bg-bp-surface`, `hover:bg-bp-mid` (line 279)
- Thinking dots use `bg-accent-insight`, appropriate for AI/data context (line 203)
- Audit fail card uses `border-accent-caution/30` (line 292)
- Audit fail button uses `bg-accent-caution text-text-inverse` (line 304)
- Uses `text-text-primary`, `text-text-secondary`, `text-text-muted` correctly throughout
- Uses `font-display` for headings (lines 153, 107 in SchoolMajorScreen)
- Uses `font-data` for CIP code display (line 243)
- Program list uses `bg-bp-surface`, `border-border-subtle` (line 410)
- Program items use `hover:bg-bp-mid hover:text-text-primary` (line 415)

### FAIL
- **Non-existent Tailwind class**: `rounded-bp-md` at lines 175, 183, 272, 279, 304, 334, 340, 410. Should be `rounded-md`. This will produce no border-radius.
- **Non-existent Tailwind class**: `rounded-bp-lg` at lines 224, 292, 317. Should be `rounded-lg`. This will produce no border-radius.
- **Input background**: Line 175 uses `bg-bp-surface` — DESIGN.md Input spec says `background: bg-deep`.
- **Input focus color**: Line 175 uses `focus:border-accent-insight` — DESIGN.md says `accent-info`.
- **Confirm button text color**: Line 272 uses `text-text-primary` (`#F5F0E8`) — DESIGN.md Primary Button spec says `text-inverse` (`#1B1D30`). White text on green is different from the spec's dark text on green.

### WARNINGS
- Heading uses `text-xl` (line 153) which is not a defined token in DESIGN.md type scale. Closest would be `text-subheading` (22px/1.375rem) or `text-heading` (28px/1.75rem). `text-xl` is Tailwind's default 20px.

---

## frontend/src/components/school/EffortLoansPanel.tsx

### PASS
- Uses `font-display` for headings (lines 105, 126)
- Uses `text-text-primary` for headings (lines 105, 126)
- Uses `text-text-muted` for descriptions (lines 109, 130)
- Uses `text-stat-ern` and `text-stat-roi` for stat colors (lines 118, 141)
- Uses `font-data` for stat displays (lines 118, 141)
- Uses `bg-bp-raised` for stat preview panel (line 149)
- Uses `bg-border-subtle` for divider (line 159)
- Uses `springs.snappy` for layout animation (line 151)
- CTA button uses `bg-accent-thrive` (line 172)
- CTA uses `hover:shadow-glow-thrive` (line 172)
- CTA uses `transition-shadow duration-normal` (line 172)
- CTA uses `springs.snappy` for press animation (line 175)

### FAIL
- **Non-existent Tailwind class**: `rounded-bp-md` at lines 149, 172. Should be `rounded-md`. This will produce no border-radius.
- **CTA button text color**: Line 172 uses `text-text-primary` (`#F5F0E8`) — DESIGN.md Primary Button spec says `text-inverse` (`#1B1D30`). Same issue as MajorInput confirm button.
- **CTA button font**: Line 172 uses `font-display` — DESIGN.md Buttons spec says all buttons use `font-body` (Nunito), weight 700. `font-display` is Fredoka.
- **CTA button text size**: Line 172 uses `text-lg` (18px) — DESIGN.md Buttons spec says CTA text is `text-cta` (17px).
- **CTA whileTap scale**: Line 174 uses `scale: 0.98` — DESIGN.md specifies `scale(0.97)` for button press feedback.
- **Panel entrance animation**: Line 101 uses `{ duration: 0.3, ease: "easeOut" }` CSS-style transition. DESIGN.md recommends springs for meaningful animations (this is a panel entrance, which should use `springs.smooth` per the fadeInUp transition).

### WARNINGS
- Heading uses `text-lg` (18px, lines 105, 126) — not a DESIGN.md type scale token. Closest is `text-body-lg` (18px/1.125rem) but that has different semantics. For a question heading, `text-subheading` (22px) per DESIGN.md "Question: font-display, weight 600, 22px" (Effort Slider spec) would be more appropriate.

---

## frontend/src/screens/LandingScreen.tsx

### PASS
- Uses `bg-bp-void` for page background (line 58)
- Includes `noise-overlay` div (line 59)
- Includes `ambient-glow` div (line 60)
- Star elements use `star` class from index.css (line 66)
- Stars have varied animation delays and durations for natural feel (lines 31-34)
- Uses `font-display` for wordmark and heading (lines 82, 94)
- Uses `text-small` for wordmark (line 82)
- Uses `text-text-muted` for wordmark (line 82)
- Uses `tracking-[0.15em] uppercase` for wordmark section label style (line 82)
- Heading uses `text-heading tablet:text-title` — responsive scaling (line 94)
- Heading uses `text-text-primary` (line 94)
- Uses `gradient-tagline` class from index.css (line 97)
- Subtitle uses `font-body`, `text-body-sm tablet:text-body-lg` — responsive (line 102)
- Subtitle uses `text-text-secondary` (line 102)
- Error text uses `text-accent-alert` (line 122)
- Footer uses `font-data`, `text-micro`, `text-text-muted` (line 129)
- Uses `springs.smooth` for stagger item transitions (line 25)
- Stagger timing: 0.15s between children, 0.05s initial delay (line 17)
- Button component used for CTA (line 112)

### FAIL
- **Heading font-weight**: Line 94 uses `font-semibold` (600) — DESIGN.md type scale says `title` and `heading` are Fredoka weight 700 (`font-bold`). The heading should be weight 700.

### WARNINGS
- Stagger delay (0.15s = 150ms, line 17) is between DESIGN.md `stagger.slow` (100ms) and none of the defined stagger tokens. Could use `stagger.slow` for consistency.
- The `leading-snug` class at line 94 maps to Tailwind's default 1.375, but DESIGN.md `--leading-snug` is 1.2. Since tokens.css defines `--leading-snug: 1.2` but Tailwind's built-in `leading-snug` is 1.375, there may be a mismatch unless Tailwind's `lineHeight` is extended.

---

## frontend/src/screens/ProfileScreen.tsx

### PASS
- Uses `bg-bp-deep` for page background (line 117)
- Includes `noise-overlay` (line 118)
- Uses `font-body text-subheading text-text-secondary` for intro text (line 128)
- Uses `font-display` for profile name heading (line 166)
- Uses `text-display tablet:text-hero` — responsive type scale (line 166)
- Uses `text-text-primary` for name (line 166)
- Uses `leading-tight` — matches DESIGN.md hero line-height 1.1 (line 166)
- Uses `springs.bouncy` for emoji and name reveal with staggered delays (lines 161, 169)
- Reroll button uses `text-accent-info`, `border-accent-info/30`, `bg-transparent` — close to Secondary button spec (line 185)
- Reroll button uses `rounded-lg` (line 185)
- Reroll button uses `springs.snappy` for press (line 191)
- Uses `border-border-subtle` for horizontal rule (line 206)
- "Already have a name?" uses `text-text-muted`, `hover:text-text-secondary` — Ghost button behavior (line 221)
- Uses `duration-normal` for transition (line 222)
- Suggestion card uses `bg-accent-caution/[0.08]` and `border-accent-caution/[0.15]` — follows accent-at-opacity pill pattern (line 259)
- Error card uses `bg-accent-alert/[0.08]` and `border-accent-alert/[0.15]` (line 277)
- Uses `springs.smooth` for entrance animations (line 108)
- Uses `font-body text-small` consistently for secondary text (lines 178, 203, 221, 260, 278)
- Button component used for primary CTA (line 212)

### FAIL
- **Hardcoded radial-gradient rgba**: Line 143 uses `rgba(125,212,163,0.08)` — hardcoded thrive color in inline style. Should reference token or use Tailwind utility.
- **Reroll dice spin spring mismatch**: Line 195 uses `{ type: "spring", stiffness: 300, damping: 15 }` — damping 15 does not match any DESIGN.md spring preset (bouncy=20, smooth=25, gentle=30, snappy=25). Custom spring not in design system.
- **Reroll button padding/height**: Line 185 uses `px-5 py-3` — DESIGN.md Secondary button spec says height 44px and padding `0 24px`. `py-3` is 12px vertical = 24px total, plus text = ~38px, not 44px. `px-5` is 20px, not 24px.

### WARNINGS
- Emoji sizes `text-5xl tablet:text-6xl` (line 158) — not DESIGN.md tokens, but emoji sizing is not covered by the type scale.
- The reroll animation exit `scale: 0.95` (line 154) is close to but not exactly `press.whileTap.scale: 0.97`. It's an exit animation though, not a press.

---

## frontend/src/screens/SchoolMajorScreen.tsx

### PASS
- Uses `bg-bp-deep` for page background (line 82)
- Includes `noise-overlay` (line 83)
- Uses `springs.smooth` for entrance animation (line 103)
- Uses `font-display text-xl text-text-primary` for heading (line 107)
- Delegates to child components for school/major/effort UI
- Uses `AnimatePresence` for phase transitions (lines 88, 119, 131)

### FAIL
- **Non-existent heading size**: Line 107 uses `text-xl` (Tailwind default 20px) — not a DESIGN.md type scale token. Should use `text-subheading` (22px) or `text-heading` (28px).

### WARNINGS
- None

---

## frontend/src/screens/PlaceholderScreen.tsx

### PASS
- Uses `bg-bp-deep` for background (line 5)
- Uses `font-body text-heading text-text-secondary` for label (line 6)
- Uses `font-body text-body text-accent-thrive` for link (line 9)
- Uses `underline underline-offset-4` for link styling (line 9)

### FAIL
- None

### WARNINGS
- None

---

## frontend/src/App.tsx

### PASS
- Routing structure, no design concerns.

### FAIL
- None

### WARNINGS
- None

---

## frontend/src/main.tsx

### PASS
- Entry point, imports index.css correctly. No design concerns.

### FAIL
- None

### WARNINGS
- None

---

## Token Gap Analysis

### Tokens in DESIGN.md missing from implementation
- **Application Header component**: DESIGN.md defines a full header spec (fixed, frosted glass, three-zone layout). No header component exists in the codebase.
- **Card component**: DESIGN.md defines a comprehensive Card component with base, hover, selected states. No generic Card component exists.
- **Pills/Badges component**: DESIGN.md defines pill variants for each accent. No dedicated pill component exists (though StatBadge partially covers this).
- **Modal component**: DESIGN.md defines modal specs. No Modal component exists.
- **Character Select Card**: DESIGN.md defines this component. Not yet implemented.
- **Save Slot Card**: DESIGN.md defines this component. Not yet implemented.
- **Boss Card**: DESIGN.md defines this component. Not yet implemented.
- **Section Labels component**: DESIGN.md defines uppercase section markers. Pattern used inline but no component.
- **Surface treatments (Background Gradient)**: DESIGN.md specifies a multi-layer radial gradient background. LandingScreen uses `bg-bp-void` flat color instead.
- **Ghost button variant**: Defined in DESIGN.md, not implemented in Button.tsx.
- **Danger button variant**: Defined in DESIGN.md, not implemented in Button.tsx.
- **Icon button variant**: Defined in DESIGN.md, not implemented in Button.tsx.
- **Large input variant**: DESIGN.md defines 56px height, 18px font, radius-lg for school search. SchoolSearch uses standard sizing.

### Tokens in implementation missing from DESIGN.md
- **`rounded-bp-sm`, `rounded-bp-md`, `rounded-bp-lg`**: Used throughout components but not defined in tailwind.config.ts or DESIGN.md. These classes will not produce any styling.
- **SegmentedControl component**: Not defined in DESIGN.md. Implementation drift.
- **BuildSummaryBar component**: Not defined in DESIGN.md. Implementation drift.

---

## Final Verdict

**CHANGES REQUESTED**

The token infrastructure (tokens.css, tailwind.config.ts, motion.ts, index.css) is excellent and fully compliant. However, the component layer has systemic issues that need addressing before the design system can be considered properly implemented.

---

## Prioritized Fix List

### P0 — Broken Styling (classes that produce no CSS output)

| # | Issue | Files | Lines |
|---|-------|-------|-------|
| 1 | `rounded-bp-sm` is not a valid Tailwind class — replace with `rounded-sm` | BuildSummaryBar.tsx, SegmentedControl.tsx | 15, 63, 72 |
| 2 | `rounded-bp-md` is not a valid Tailwind class — replace with `rounded-md` | SegmentedControl.tsx, EffortLoansPanel.tsx, SchoolSearch.tsx, MajorInput.tsx | 46, 105, 134, 149, 153, 172, 175, 183, 272, 279, 304, 334, 340, 410 |
| 3 | `rounded-bp-lg` is not a valid Tailwind class — replace with `rounded-lg` | MajorInput.tsx | 224, 292, 317 |

### P1 — Wrong Token Values (visually incorrect per DESIGN.md)

| # | Issue | File | Lines | DESIGN.md Section |
|---|-------|------|-------|-------------------|
| 4 | Primary buttons on green bg use `text-text-primary` (white) instead of `text-text-inverse` (dark) | EffortLoansPanel.tsx, MajorInput.tsx | 172, 272 | Buttons > Primary |
| 5 | TextInput background is `bg-bp-mid` instead of `bg-bp-deep` | TextInput.tsx | 8 | Inputs > Standard Input |
| 6 | TextInput focus border is `border-strong` instead of `accent-info` | TextInput.tsx | 8 | Inputs > Focus |
| 7 | SchoolSearch/MajorInput inputs use `bg-bp-surface` instead of `bg-bp-deep` | SchoolSearch.tsx, MajorInput.tsx | 134, 175 | Inputs > Standard Input |
| 8 | SchoolSearch/MajorInput focus border uses `accent-insight` instead of `accent-info` | SchoolSearch.tsx, MajorInput.tsx | 134, 175 | Inputs > Focus |
| 9 | Secondary Button variant is completely wrong (bg-surface + text-secondary vs. transparent + accent-info) | Button.tsx | 15-16 | Buttons > Secondary |
| 10 | CTA button uses `font-display` instead of `font-body` | EffortLoansPanel.tsx | 172 | Buttons |
| 11 | CTA button uses `text-lg` (18px) instead of `text-cta` (17px) | EffortLoansPanel.tsx | 172 | Buttons |
| 12 | CTA whileTap scale is 0.98 instead of 0.97 | EffortLoansPanel.tsx | 174 | Motion > press |
| 13 | Landing heading uses `font-semibold` (600) instead of `font-bold` (700) | LandingScreen.tsx | 94 | Typography > title/heading |

### P2 — Missing Implementations (spec-defined but absent)

| # | Issue | File | DESIGN.md Section |
|---|-------|------|-------------------|
| 14 | No focus ring shadow on any input | TextInput.tsx, SchoolSearch.tsx, MajorInput.tsx | Inputs > Focus |
| 15 | No explicit height on inputs (should be 48px) | TextInput.tsx | Inputs > Standard Input |
| 16 | No explicit height on primary button (should be 48px) | Button.tsx | Buttons > Primary |
| 17 | Primary button hover: no darken to `#6bc494` | Button.tsx | Buttons > Hover states |
| 18 | Primary button padding: 40px instead of 28px horizontal | Button.tsx | Buttons > Primary |
| 19 | Missing Ghost, Danger, Icon button variants | Button.tsx | Buttons |
| 20 | No Application Header component | (missing) | Application Header |
| 21 | School search input should use large variant (56px, 18px, radius-lg) | SchoolSearch.tsx | Inputs > Large variant |

### P3 — Hardcoded Values (maintainability risk)

| # | Issue | File | Lines |
|---|-------|------|-------|
| 22 | Hardcoded `rgba(125,212,163,0.08)` in inline style | ProfileScreen.tsx | 143 |
| 23 | Hardcoded `rgba(125,212,163,0.12)` in SVG filter | PentagonGlow.tsx | 34 |
| 24 | Custom spring `{ stiffness: 300, damping: 15 }` not in design system | ProfileScreen.tsx | 195 |

### P4 — Spec Deviations (non-standard values)

| # | Issue | File | Lines | DESIGN.md Section |
|---|-------|------|-------|-------------------|
| 25 | Pentagon grid ring opacities differ from spec (3-6% vs. 15%) | PentagonGlow.tsx | 45-47 | Pentagon |
| 26 | Pentagon axis line opacity differs from spec (5% vs. 20%) | PentagonGlow.tsx | 50-54 | Pentagon |
| 27 | Pentagon vertex dot radius 3.5px vs. spec 5px, missing 10px glow circles | PentagonGlow.tsx | 73 | Pentagon |
| 28 | `text-xl` used where no DESIGN.md token exists | SchoolMajorScreen.tsx, MajorInput.tsx | 107, 153 | Typography |
| 29 | Effort slider heading uses `text-lg` instead of spec's 22px | EffortLoansPanel.tsx | 105, 126 | Effort Slider |
| 30 | Tailwind `leading-snug` may not map to DESIGN.md `--leading-snug: 1.2` | LandingScreen.tsx | 94 | Typography |
