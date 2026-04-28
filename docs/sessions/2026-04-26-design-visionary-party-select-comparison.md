# Session Log: Design Vision — Party Select Comparison

| Field | Value |
|-------|-------|
| Session ID | 2026-04-26-design-visionary-party-select |
| Timestamp | 2026-04-26 |
| Agent | @fp-design-visionary |
| Spec | `docs/specs/feature-party-select-comparison.md` |

## Actions Taken

1. Read the HTML mockup at `mockups/party-select.html` (2070 lines) — studied every CSS rule, HTML structure, and JS behavior
2. Read `DESIGN.md` (full Brightpath design system) for token reference — colors, typography, spacing, radii, shadows, motion system, components
3. Read existing implementation files:
   - `frontend/src/components/menu/CompareView.tsx` — current compare screen (to be redesigned)
   - `frontend/src/components/menu/PentagonOverlay.tsx` — existing SVG pentagon (3-color BUILD_COLORS array)
   - `frontend/src/components/menu/RiskHeadlineCard.tsx` — existing boss row component
   - `frontend/src/styles/motion.ts` — Framer Motion spring configs and presets
   - `frontend/src/api/menu.ts` — current TypeScript types for compare API
4. Wrote comprehensive section 3 (UI/UX Design) with 14 sub-sections covering every component, token, animation, responsive breakpoint, and interaction
5. Updated spec status from ARCH REVIEW to DESIGN VISION

## Artifacts Produced

- `docs/specs/feature-party-select-comparison.md` section 3 — complete implementable component spec

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| 4th build color = accent-empathy (#E88BA9, pink) | Completes the four-accent cycle without introducing new tokens. Pink reads distinctly against green, blue, and gold on dark backgrounds. |
| BUILD_COLORS array uses modulo cycling | Safety net for any N>4 edge case. Colors are thrive, info, caution, empathy — same order as existing 3-color array plus pink. |
| Breathe animations use CSS keyframes, not Framer Motion | Ambient loops are not "meaningful" animations per DESIGN.md distinction. CSS keyframes are more performant for infinite cycles. |
| Below-fold sections use `whileInView` instead of absolute delays | Avoids timing all 22+ elements against a single clock. Scroll-triggered entrances feel more alive and are more performant. |
| Gemma text renders as plain paragraphs, no inline color parsing | The mockup shows aspirational colored spans, but parsing Gemma's prose for color application is fragile and out of scope for MVP. Documented as future enhancement. |
| Money Insight callout + Gemma's Take both have independent skeleton loading | Two-phase loading model: data renders immediately, Gemma fills in async. Each zone transitions independently. |
| No horizontal scroll on mobile boss grid | Constrained to viewport width. Even with 4 builds at 375px, each outcome cell gets ~94px which fits a 12px pill. |
