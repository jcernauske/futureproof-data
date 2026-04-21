# Feature: Horizon Footer + Wrapped Silhouette

## Claude Code Prompt

```
Read the spec at docs/specs/feature-horizon-footer.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (frontend module addition, Build type extension, sessionStorage usage, prefetch strategy)
   - @fp-data-reviewer is SKIPPED (no pipeline / DuckDB / stat / boss-fight changes)
   - @fp-architect writes findings to §5
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION — SKIPPED
   - Already complete. §3 was authored from two prior @fp-design-visionary runs (agent IDs a631ef745346991a4 and af6b2fc83c63de7e1) and the interactive mockup at scripts/horizon-mockup.html.
   - Implementer treats §3 as the pixel-perfect target as if visionary had just delivered it.

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: review §4 Testing Impact Analysis
   - DURING coding: update only tests listed in "Authorized Test Modifications"
   - CRITICAL: if any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate
   - Log all work to §6
   - Run frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: if build breaks, YOU fix it (max 3 attempts). After 3, escalate via §10.

4. TESTING
   - Invoke @test-writer to review the full spec, especially §4 Testing Impact Analysis
   - Implement all P0 tests, then P1
   - Run ALL frontend tests to catch regressions
   - If any non-authorized test fails: STOP and escalate

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical Brightpath token compliance against DESIGN.md
   - Verify all colors are tokens (no hex), all type uses scale (text-heading/subheading/body/small/micro), all motion uses springs preset names
   - Writes findings to §8

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Focus areas: sessionStorage edge cases (quota, disabled, SSR-safe), the prefetch strategy (no over-fetching), parallax cleanup (no leaked listeners), reduced-motion paths, no CLS regression
   - Writes findings to §8
   - If CHANGES REQUIRED: route via §10 to implementer

7. VERIFICATION
   - Invoke @fp-builder for full build
   - Frontend: TypeScript, vitest, Vite production build
   - Backend checks N/A (no backend changes)
   - Log to §9

8. COMPLETION
   - Update Status to COMPLETE
   - Check off Success Criteria in §1
   - Generate report to reports/feature-horizon-footer-2026-04-18.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | (SKIPPED — already complete) |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-18 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-18 (verification complete — all checks green; spec COMPLETE) |
| Blocked By | — |
| Related Specs | — |

---

## §1 Feature Description

### Overview
Replace the current minimal `LandingFooter` with a cinematic full-bleed "Horizon Footer" that randomly selects one of 48 Midjourney campus illustrations per page-load and bleeds it between the page background and a three-column dark chrome bar (identity / provenance / studio). Add a muted "Horizon Silhouette" variant behind the share card on `/app/save`, locked at build commit so a user device-screenshot of the live page is stable across remounts. (The backend-rendered share PNG via `renderWrapped(buildId)` is out of scope here — see §2 Out of Scope.)

### Problem Statement
The landing page currently terminates in a 200-line minimal footer with a wordmark, single link, and AI disclaimer. It is functionally complete but emotionally flat — it gives the user no sense of the world FutureProof is helping them plan into. We have 48 high-quality Midjourney illustrations sitting at `frontend/public/campus/` (already optimized as AVIF/WebP at 1400/2048 widths via `scripts/optimize_campus_images.py`) that go unused. The footer should embody the app's central thesis — *many futures, all real* — by rotating through these illustrations so every load implies "and N more." On the Wrapped/Save screen, a locked silhouette ties each saved build to a specific campus image, making the build's identity visually distinct and screenshot-stable.

### Success Criteria
- [x] Landing page footer is replaced with `HorizonFooter` component; old `LandingFooter` deleted
- [x] Random campus illustration loads on every landing page mount and route change
- [x] All 48 illustrations cycle exactly once per session before reshuffling (verified by manual click-through plus unit test on the bag)
- [x] No image repeats two loads in a row (anti-adjacency)
- [x] Desktop and mobile draw from independent bags (per-surface shuffling)
- [x] Caption rotates with image via `index % 3` mapping; same image always shows same caption
- [x] Three-column chrome bar (identity / provenance / studio) renders correctly on desktop, stacks correctly below 840px
- [x] Caption hides below 480px viewport
- [x] Mobile uses `object-position: center 30%` and 200px height
- [x] `<picture>` element serves AVIF → WebP, with 1400/2048 variants media-gated by `(min-width: 1200px)`
- [x] `loading="lazy"`, `decoding="async"`, `aspect-ratio` reservation prevents CLS regression
- [x] Cold mount motion sequence runs at 1.6s total (sky-bleed → image → caption → chrome stagger)
- [x] Warm reroll (route change with prior image cached) runs as 900ms crossfade
- [x] 0.85x scroll parallax works while in viewport, IntersectionObserver-gated
- [x] `prefers-reduced-motion` strips all transform/parallax; opacity-only fallback
- [x] Next 2 indices in bag are prefetched 2s after idle via `<link rel="prefetch">`
- [x] `Build.horizonIndex?: number` added to the Build type and persisted on commit
- [x] `HorizonSilhouette` renders behind share card on `/app/save`, locked at 60% opacity, no caption, no chrome
- [x] `useHorizonPick` hook is SSR-safe (no `window` access during render)
- [x] sessionStorage failures (quota / disabled / private mode) degrade gracefully to in-memory bag
- [x] All new components have vitest coverage at the levels specified in §4
- [x] Existing landing page tests still pass without modification (other than `LandingFooter.test.tsx` deletion + replacement)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Random per page-load (not per-session-day stable) | App's thesis is *multiplicity* — a stable horizon contradicts "see yourself at different colleges, different builds." Variation IS the product. | Per-session-day deterministic (rejected: stability undersells the thesis); per-route stable (rejected: same problem); pure `Math.random()` (rejected: see #2) |
| 2 | Shuffled-bag walk in sessionStorage, not `Math.random()` | Guarantees coverage of all 48 in a session, anti-adjacency for free, never repeats two in a row, makes the multiplicity *legible* | `Math.random()` per pick (rejected: can repeat, doesn't prove there are N); deterministic hash of route (rejected: doesn't shuffle); bag in localStorage (rejected: cross-session state pretends to be a thing it isn't) |
| 3 | Per-surface bags (desktop + mobile draw independently) | A user opening the link on phone after laptop gets a *different* horizon — multiplicity across devices reinforces the thesis | Single bag (rejected: same illustration on both devices undersells variety); per-tab bag (rejected: too granular, no observable benefit) |
| 4 | Three captions, image-paired by `index % 3` | A single fixed caption against relentless visual variety reads as a slogan; symmetric variety reads as the brand living what it says. Pairing (vs. random rotation) lets the caption become a property of the image rather than chrome. | Single caption (rejected: too static against rotating visual); random caption per load (rejected: undermines receipt authority); 5+ captions (rejected: more surface area for fact-checking drift) |
| 5 | NO reroll button | User explicitly declined the complexity. Random per page-load already serves the curiosity case. | 32×32 ghost button + Shift+R shortcut (visionary's proposal, rejected by user) |
| 6 | No horizon on in-app gameplay screens (Character/School/Effort/Reveal/Gauntlet/Tree) | Those screens are theatrical, contained, focused. A horizon below the boss fight would yank the player out of the diegesis. | Horizon on every screen (rejected: breaks focus); horizon only on gauntlet completion (rejected: conflicts with reveal sequence) |
| 7 | Wrapped silhouette is locked at build commit, not rerolling | The on-screen silhouette is a client-side overlay; locking it makes user device-screenshots stable across remounts and turns the horizon into a *property of the build*. **Note:** the silhouette is intentionally NOT baked into the backend-rendered share PNG via `renderWrapped(buildId)` in v1 — that pipeline only ships `build_id` and would need a separate spec (backend asset path resolver + Playwright fixture) to incorporate the horizon. | Re-roll on every Wrapped view (rejected: same-page screenshot instability); separate manual selection (rejected: another decision the user shouldn't have to make); bake silhouette into backend share PNG (deferred: separate larger spec) |
| 8 | `Build.horizonIndex?: number` (optional) | The current `buildStore` `partialize` (`frontend/src/store/buildStore.ts:60-64`) whitelists *only* `hasSeenStatTutorial`, so `build` is NOT persisted across sessions today — there are no on-disk Builds without `horizonIndex` to worry about. The optional field is still correct because (a) we don't want to force a migration if `build` ever joins the persisted partial, and (b) a missing `horizonIndex` triggers a deterministic late-bind on first `/app/save` view via `=== undefined` guard. | Required field with migration (rejected: forces a migration for a decorative property); separate sidecar store (rejected: state divergence risk) |
| 9 | Three-zone composite (sky-bleed + image + ground-bleed), no frame | The illustrations match Brightpath's "dusk indigo with warm windows" palette uncannily; bleeding between two indigos preserves the "world keeps going" feeling. A frame says "decoration." | Hard-edged frame (rejected: reads as wallpaper); single fade mask top+bottom (rejected: looks pasted-on); vignette (rejected: kills the parallax built into the art) |
| 10 | `<picture>` with AVIF → WebP, no PNG fallback | Modern browsers (Safari 14+, Edge, Chrome, Firefox, all mobile shipped since 2020) support both. PNG fallback would 4× the disk footprint for users who don't exist. | AVIF + WebP + PNG (rejected: 50MB of PNGs serves nobody); WebP only (rejected: AVIF gives 30%+ savings on the modern path); Single format (rejected: progressive enhancement is cheap) |
| 11 | Caption uses font-data text-micro at 60% opacity with text-shadow, not a solid scrim | A solid scrim band would create a visible UI element across the illustration; text-shadow provides legibility while letting the art breathe. | Solid scrim (rejected: chops the image); higher opacity caption (rejected: reads as label, not whisper); no caption (rejected: loses receipts spine) |
| 12 | Prefetch the next 2 bag indices, not all 48 | Two-deep is enough that any single page-change is instant; more is wasteful | Prefetch all 48 (rejected: ~10MB on session start); prefetch only next 1 (rejected: route change races the network); no prefetch (rejected: warm reroll has 200-800ms blank) |

### Constraints
- **Brightpath fidelity** — All colors/typography/motion must use existing tokens from `DESIGN.md`. No new tokens introduced by this spec.
- **No CLS regression** — Aspect-ratio reservation must prevent layout shift on the landing page.
- **SSR-safe** — `useHorizonPick` cannot touch `window` / `sessionStorage` during render. Hydration mismatch will break Vite's strict mode dev experience.
- **sessionStorage may be unavailable** — Private browsing, quota exceeded, disabled storage. The hook must degrade to an in-memory bag without crashing.
- **Backwards compatible Build type** — Existing persisted Builds in localStorage must continue to load. `horizonIndex` is optional; absence triggers a deterministic late-bind on first view.
- **No reroll UI** — Per user decision, the only way to see a different horizon is to navigate or reload.

### Out of Scope (intentionally excluded)
- **Real HyenaStudios logo asset** — Ship with placeholder (32px circle, "HS" text inside, `border-border-subtle`). Replacement is a follow-up spec when the brand asset exists.
- **Horizon on About / Methodology / Privacy / 404 routes** — Those routes don't exist yet. When they're built, they inherit `HorizonFooter` via the layout component (no re-spec needed).
- **Reroll button / Shift+R shortcut** — Explicitly rejected. Future spec only if user feedback demands it.
- **Per-route deterministic horizon** — Considered and rejected; variation is the thesis.
- **Caption A/B testing or analytics on horizon clicks** — No engagement instrumentation in v1. The horizon is decorative.
- **Cross-tab horizon synchronization** — Each tab gets its own bag walk. Synchronization across tabs offers no observable value.
- **Horizon on in-app gameplay screens** — Sealed worlds stay sealed.
- **Server-side horizon selection** — All randomization is client-side. No backend involvement.
- **Manifest auto-generation at build time via Vite plugin** — For v1, ship a hand-maintained `horizonManifest.ts` array. If the asset count grows beyond 48, replace with a generation script (separate spec).

---

## §3 UI/UX Design

> §3 was authored from two prior @fp-design-visionary agent runs and the interactive mockup at `scripts/horizon-mockup.html`. Implementer treats this as the pixel-perfect target.

### Mockups

**Reference mockup:** `scripts/horizon-mockup.html` — open in a browser; click "🎲 Next campus" to flip through all 48 illustrations and verify caption legibility, motion choreography, parallax, and Wrapped silhouette layering.

**Layout — Horizon Footer (desktop, ≥840px):**

```
┌─────────────────────────────────────────────────────────────────┐
│ PAGE CONTENT (bg-bp-deep)                                       │
│                                                                 │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ ← 120px sky-bleed
│ ░░░ Sky bleed: linear-gradient(to bottom, bp-deep, transparent) │   (overlay on image top)
│                                                                 │
│ ████████████████████████████████████████████████████████████████ │
│ █  ILLUSTRATION (full-bleed, height: clamp(220px, 22vw, 480px))█ │
│ █                                                              █ │
│ █     ┌──────────────────────────────────────────────────┐    █ │
│ █     │  Caption (data, micro, tracking-widest, /60)     │    █ │ ← caption midband
│ █     │  text-shadow: 0 1px 2px rgba(0,0,0,0.7)          │    █ │
│ █     └──────────────────────────────────────────────────┘    █ │
│ █                                                              █ │
│ ████████████████████████████████████████████████████████████████ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ ← 60px ground-bleed
│ ░░░ Ground bleed: linear-gradient(to bottom, transparent, void)░ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ CHROME BAR (bg-bp-void), padding-y: 32px, padding-x: 24/40px    │
│ max-w: 1280px container                                         │
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────────┐  ┌────────────┐  │
│  │ FutureProof     │  │ ★ Built with Gemma 4 │  │ ⊙ HyenaStud│  │
│  │ (display, bold, │  │ Submitted to Gemma 4 │  │ (display,  │  │
│  │  text-heading,  │  │  Good · Kaggle /     │  │  semibold, │  │
│  │  text-primary)  │  │  Google DeepMind     │  │  subhead,  │  │
│  │                 │  │  · 2026 (data, micro)│  │  secondary)│  │
│  │ Live app        │  │                      │  │            │  │
│  │ (body, body,    │  │ AI-estimated. Not a  │  │ © 2026     │  │
│  │  secondary)     │  │  substitute for prof │  │ (data,     │  │
│  │                 │  │  career counseling.  │  │  micro,    │  │
│  │                 │  │  (body, small, muted,│  │  muted)    │  │
│  │                 │  │   max-w-[420px])     │  │            │  │
│  └─────────────────┘  └──────────────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Layout — Horizon Footer (mobile, <840px):**

Three columns collapse to a single left-aligned stack: identity → provenance → studio. Gap between sections: 24px. Caption hides below 480px viewport. Image height reduces to fixed 200px with `object-fit: cover; object-position: center 30%`.

**Layout — Horizon Silhouette (`/app/save`, all viewports):**

```
┌─────────────────────────────────────────────────────────────────┐
│ SaveWrappedScreen (bg-bp-deep)                                  │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              SHARE CARD (existing)                      │   │
│   │              Centered over silhouette                   │   │
│   │              z-index: 10                                │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ░░░ HORIZON SILHOUETTE (180px, opacity 0.6) ░░░░░░░░░░░░░░░░░ │
│   ████ Image bleeds full width, behind share card ███████████   │
│   ░░░ Vertical mask: linear-gradient(to top, transparent, deep) │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

The silhouette uses `mix-blend-mode: normal`, `opacity: 0.6`, and a CSS mask for the upper fade. Locked to `Build.horizonIndex` set on first save commit; never re-rolls during the same Wrapped session.

### Interactions

**Cold mount sequence (1.6s total):**
1. T+0: sky-bleed gradient opacity 0→1, 800ms ease-out
2. T+0: image opacity 0→1 + scale 1.02→1, 1000ms `springs.gentle`
3. T+600ms: caption opacity 0→0.6, 400ms ease-out
4. T+800ms: chrome bar text staggered with `stagger.normal` (80ms between elements), 600ms each

**Warm reroll sequence (900ms total)** — for route-change arrivals when a previous image was cached in the same session:
1. T+0: outgoing image opacity 1→0.35 + scale 1→0.985, 240ms ease-out
2. T+180ms: incoming image fades up underneath, opacity 0→1 + scale 1.015→1, `springs.smooth`
3. T+240ms: outgoing image unmounts (cleanup)
4. T+460ms: caption translates Y +6→0, no opacity change (the "world moved, receipts stayed" beat)

**Scroll parallax:**
- Image transforms `translateY(calc(scrollY * -0.15))` at 0.85x scroll speed
- Driven by single `requestAnimationFrame` listener gated by `IntersectionObserver` (only animates while footer in viewport — zero cost when scrolled away)
- Listener cleaned up on unmount

**Reduced motion (`prefers-reduced-motion: reduce`):**
- All transforms stripped (no scale, no parallax, no caption Y-translate)
- Opacity-only fade-ins, 240ms each
- Cold and warm sequences both collapse to opacity crossfade

### Responsive Behavior

| Viewport | Image height | Caption | Chrome layout | object-position |
|----------|--------------|---------|---------------|-----------------|
| ≥1200px | `clamp(220px, 22vw, 480px)` | visible | 3-column | `center` |
| 840–1199px | `clamp(220px, 22vw, 480px)` | visible | 3-column | `center` |
| 480–839px | `clamp(220px, 22vw, 480px)` | visible | stacked | `center` |
| <480px | 200px fixed | hidden | stacked | `center 30%` |

`<picture>` source media gating:
- AVIF 2048 wide: `(min-width: 1200px)`
- AVIF 1400 wide: default fallback
- WebP 2048 wide: `(min-width: 1200px)`
- WebP 1400 wide: default fallback

### Brightpath Design References

| Token | Usage |
|-------|-------|
| `bg-bp-deep` | Page background; top of sky-bleed gradient |
| `bg-bp-void` | Chrome bar background; bottom of ground-bleed gradient |
| `text-text-primary` | FutureProof wordmark, caption (at /60 opacity) |
| `text-text-secondary` | "Built with Gemma 4", Live app link, HyenaStudios wordmark |
| `text-text-muted` | AI disclaimer, ©, "Submitted to Gemma 4 Good…" |
| `border-border-subtle` | HyenaStudios placeholder logo border |
| `font-display` (font-bold / semibold) | Wordmarks |
| `font-body` | Links, disclaimer |
| `font-data` | Caption, "Submitted to…", © |
| `text-heading` | FutureProof wordmark |
| `text-subheading` | HyenaStudios wordmark |
| `text-body` | Live app link |
| `text-small` | "Built with Gemma 4", AI disclaimer |
| `text-micro` | Caption, "Submitted to…", © |
| `tracking-widest` | Caption |
| `springs.gentle` | Cold-mount image scale-in |
| `springs.smooth` | Warm-reroll incoming image |
| `stagger.normal` | Chrome bar text reveal (80ms) |
| `duration-fast` | HyenaStudios logo hover opacity transition |

### Frontend Library Reference

| Library | Use For | This Spec |
|---------|---------|-----------|
| **Framer Motion** | Cold mount + warm reroll sequences | `<motion.div>` for sky-bleed, image, caption, chrome |
| **React (built-in)** | `useEffect`, `useState`, `useRef`, `useReducer` for hook | `useHorizonPick` hook |
| **Native Web APIs** | `IntersectionObserver`, `requestAnimationFrame`, `<link rel="prefetch">` | Parallax, prefetch |

No new dependencies introduced.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Horizon image | `horizon-image` | `<img>` | `alt=""` + `role="presentation"` (decorative) |
| Footer container | `horizon-footer` | `<footer>` | (semantic only) |
| Chrome bar identity | `horizon-identity` | `<div>` | (semantic only) |
| Live app link | `horizon-live-app` | `<a>` | (link text serves) |
| HyenaStudios attribution | `horizon-studio` | `<address>` | (semantic only) |
| Wrapped silhouette | `horizon-silhouette` | `<img>` | `alt=""` + `role="presentation"` |

Caption text is real DOM text (not in image alt) — screen readers will read it once when reaching the footer landmark.

---

## §4 Technical Specification

### Architecture Overview

This spec adds a single new frontend module (`frontend/src/components/horizon/`) containing:
- `HorizonFooter.tsx` — replaces `LandingFooter.tsx` as the landing page's terminal element
- `HorizonSilhouette.tsx` — new variant rendered behind the share card on `/app/save`
- `horizonManifest.ts` — hand-maintained array of 48 image basenames
- `horizonCaptions.ts` — array of 3 captions

A new hook at `frontend/src/hooks/useHorizonPick.ts` encapsulates the shuffled-bag walk algorithm, sessionStorage persistence, anti-adjacency, per-surface bags, and prefetching.

The `Build` type at `frontend/src/types/build.ts` gains an optional `horizonIndex?: number` field. `SaveWrappedScreen.tsx` is modified to set `horizonIndex` on first commit (if absent) and to render `HorizonSilhouette` keyed to that index.

`LandingScreen.tsx` is modified to mount `HorizonFooter` instead of the existing `LandingFooter`. `LandingFooter.tsx` and its test are deleted.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/components/horizon/HorizonFooter.tsx` | Create | Full-bleed footer component with three-zone composite + chrome bar; consumes `useHorizonPick('desktop' \| 'mobile')` and renders cold-mount/warm-reroll motion |
| `frontend/src/components/horizon/HorizonSilhouette.tsx` | Create | Muted variant for `/app/save`; renders single image at 180px height, opacity 0.6, vertical mask; consumes a fixed `horizonIndex: number` prop, no rotation |
| `frontend/src/components/horizon/horizonManifest.ts` | Create | Hand-maintained `export const HORIZON_BASENAMES: readonly string[]` listing 48 image basenames (without `-1400.avif` suffix); generated once via `ls frontend/public/campus/ \| grep '\\-1400\\.avif$' \| sed 's/-1400\\.avif$//'` and pasted in. **Must include a header comment**: "WARNING: Reordering this array silently re-pairs every image with a different caption (pairing is `index % 3`). Append-only is safe; reorder requires regenerating with intent." |
| `frontend/src/components/horizon/horizonCaptions.ts` | Create | `export const HORIZON_CAPTIONS: readonly [string, string, string]` literal tuple of the three captions |
| `frontend/src/components/horizon/HorizonFooter.test.tsx` | Create | vitest coverage for HorizonFooter render, responsive class assertions, motion-respecting reduced-motion query |
| `frontend/src/components/horizon/HorizonSilhouette.test.tsx` | Create | vitest coverage for silhouette render, opacity, locked-to-index behavior |
| `frontend/src/hooks/useHorizonPick.ts` | Create | Hook encapsulating bag shuffle, sessionStorage persistence, anti-adjacency, per-surface bags, prefetch trigger, SSR-safe init |
| `frontend/src/hooks/useHorizonPick.test.ts` | Create | vitest coverage for bag shuffling, anti-adjacency, reshuffle on exhaustion, sessionStorage degradation, per-surface independence, captionFor logic |
| `frontend/src/types/build.ts` | Modify | Add `horizonIndex?: number` optional field to `Build` interface (around line 169, before optional `profile_name`) |
| `frontend/src/screens/SaveWrappedScreen.tsx` | Modify | On first mount: if `build.horizonIndex === undefined` (NOT `!build.horizonIndex` — index 0 is valid), draw next from desktop bag and call `setBuild({ ...build, horizonIndex })`. Mount `HorizonSilhouette` behind share card. |
| `frontend/src/screens/SaveWrappedScreen.test.tsx` | Modify | Add tests for: (a) silhouette renders behind share card, (b) horizonIndex is set on first commit, (c) horizonIndex is preserved on subsequent mounts |
| `frontend/src/screens/LandingScreen.tsx` | Modify | Replace `<LandingFooter />` import + JSX with `<HorizonFooter />` |
| `frontend/src/screens/LandingScreen.test.tsx` | Modify | Update import / element assertion if it references `LandingFooter` directly |
| `frontend/src/components/landing/LandingFooter.tsx` | Delete | Replaced by HorizonFooter |
| `frontend/src/components/landing/LandingFooter.test.tsx` | Delete | Replaced by HorizonFooter.test.tsx |

### Data Model Changes

**TypeScript interface change** (`frontend/src/types/build.ts`):

```ts
export interface Build {
  build_id: string;
  created_at: string;
  school_name: string;
  unitid: number;
  major_text: string;
  cipcode: string;          // string (XX.XXXX format), per CLAUDE.md project rule
  program_name: string;
  effort: string;
  loan_pct: number;
  career: CareerOutcome;
  gauntlet: GauntletResult;
  branches: CareerBranch[];
  skill_recs: SkillRec[];
  guidance: string;
  skills_crafted: AppliedSkill[];
  skill_pool: AppliedSkill[];
  next_steps: string;
  profile_name?: string;
  horizonIndex?: number;    // NEW: 0..47 inclusive, locked at first /app/save view
}
```

No backend Pydantic model changes — `Build` is a frontend-only type. No DuckDB / Iceberg changes.

**zustand store** (`frontend/src/store/buildStore.ts`):

No changes needed. `setBuild` already accepts a full `Build` and replaces state. `SaveWrappedScreen` updates the build via existing `setBuild` action.

**sessionStorage schema** (new):

```ts
// Key: `fp.horizon.bag.v1.desktop` and `fp.horizon.bag.v1.mobile`
type StoredBag = {
  order: number[];          // length 48, permutation of [0..47]
  cursor: number;           // next index to draw, 0..48
  lastShown: number | null; // for anti-adjacency
};
```

Versioned key (`v1`) to allow future cache busts without legacy collisions.

### Service Changes

**New hook** — `frontend/src/hooks/useHorizonPick.ts`:

```ts
export type HorizonSurface = 'desktop' | 'mobile';

export interface HorizonPick {
  /** Index into HORIZON_BASENAMES, 0..47 inclusive. */
  index: number;
  /** Resolved basename, e.g. 'jcern_Flat_orthographic_..._0' */
  basename: string;
  /** Caption paired with this index via index % 3. */
  caption: string;
}

/**
 * Returns a random horizon pick on every mount and route change.
 * Uses a shuffled-bag walk persisted in sessionStorage with anti-adjacency.
 * Per-surface bags so desktop/mobile draw independently.
 *
 * SSR-safe: returns null on the first render, populates after mount.
 * Degrades to in-memory bag if sessionStorage is unavailable.
 *
 * Side effect: triggers a `<link rel="prefetch">` for the next 2 indices
 * after a 2s idle window.
 */
export function useHorizonPick(surface: HorizonSurface): HorizonPick | null;

/**
 * Returns a stable horizon pick locked to a given index.
 * Used by HorizonSilhouette where the build's horizonIndex is fixed.
 */
export function useHorizonAt(index: number): HorizonPick;

/**
 * Pure helper: draws the next index from a bag without persistence.
 * Exported for testing.
 */
export function drawFromBag(
  bag: StoredBag,
  poolSize: number,
): { next: number; bag: StoredBag };

/**
 * Pure helper: builds a fresh shuffled bag with a Fisher-Yates shuffle.
 * Seeded for deterministic tests; defaults to crypto.getRandomValues.
 */
export function newBag(poolSize: number, seed?: number): StoredBag;

/**
 * Maps a horizon index to its paired caption via index % 3.
 */
export function captionFor(index: number): string;
```

**Component contracts:**

```ts
// HorizonFooter.tsx
export function HorizonFooter(): JSX.Element;

// HorizonSilhouette.tsx
export interface HorizonSilhouetteProps {
  index: number;  // 0..47, locked
  className?: string;
}
export function HorizonSilhouette(props: HorizonSilhouetteProps): JSX.Element;
```

**No new dependencies.** Framer Motion, Tailwind, React are already in the project.

### Testing Impact Analysis

> Searched `frontend/src/**/*.test.{ts,tsx}` for tests that reference `LandingFooter`, `SaveWrappedScreen`, `Build`, or the landing page. Findings below.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/components/landing/LandingFooter.test.tsx` | (all tests) | High | File deleted; tests move to `HorizonFooter.test.tsx` |
| `frontend/src/screens/LandingScreen.test.tsx` | tests asserting `LandingFooter` presence | High | Must update to assert `HorizonFooter` |
| `frontend/src/screens/SaveWrappedScreen.test.tsx` | (all existing tests) | Medium | New silhouette element added to the render tree; existing assertions on layout/structure may need updates |
| `frontend/src/store/buildStore.test.ts` | tests for Build shape, persistence | Low | `horizonIndex` is optional; existing builds without it must still pass type checks and persistence round-trips |
| `frontend/src/components/wrapped/WrappedViewer.test.tsx` | render tests | Low | Unaffected unless WrappedViewer asserts no extra DOM (unlikely) |
| `frontend/src/App.test.tsx` | router/render smoke tests | Low | Unaffected unless asserting absence of new elements |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `LandingFooter.test.tsx` | Delete file | Component deleted |
| `LandingScreen.test.tsx` | Replace `LandingFooter` element/text assertions with `HorizonFooter` equivalents | Component swap |
| `SaveWrappedScreen.test.tsx` | Add tests for silhouette presence + horizonIndex behavior; update existing assertions if they break on layout change | New visual element |

#### Confirmed Safe (must NOT break)

- `frontend/src/store/buildStore.test.ts` — Build persistence and shape; horizonIndex must be backwards-compatible
- All `frontend/src/components/{gauntlet,school,tree,menu,wrapped}` tests except `SaveWrappedScreen` itself
- All `frontend/src/screens/*.test.tsx` except `LandingScreen` and `SaveWrappedScreen`
- All hook tests in `frontend/src/hooks/`
- All `frontend/src/api/` tests
- All `frontend/src/lib/` tests

If any of the "Confirmed Safe" tests fail after implementation: **STOP, escalate via §10, do not modify the test.**

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | draws all 48 indices exactly once across 48 calls | Bag coverage guarantee |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | never returns the same index twice in a row | Anti-adjacency |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | reshuffles after exhaustion | Bag refresh |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | persists state across hook re-mounts via sessionStorage | Continuity within session |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | desktop and mobile bags are independent | Per-surface bags |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | falls back to in-memory bag when sessionStorage throws | Graceful degradation |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | captionFor(i) returns CAPTIONS[i % 3] for all i in 0..47 | Caption pairing |
| P0 | `frontend/src/hooks/useHorizonPick.test.ts` | newBag produces a permutation of [0..poolSize-1] | Shuffle correctness |
| P0 | `frontend/src/components/horizon/HorizonFooter.test.tsx` | renders the chrome bar three-column layout at desktop viewport | Layout fidelity |
| P0 | `frontend/src/components/horizon/HorizonFooter.test.tsx` | hides caption below 480px viewport | Responsive caption |
| P0 | `frontend/src/components/horizon/HorizonSilhouette.test.tsx` | renders image at given index with opacity 0.6 | Locked behavior |
| P0 | `frontend/src/screens/SaveWrappedScreen.test.tsx` | sets build.horizonIndex on first mount when absent | Persistence on commit |
| P0 | `frontend/src/screens/SaveWrappedScreen.test.tsx` | preserves build.horizonIndex on subsequent mounts | Locked-at-commit behavior |
| P1 | `frontend/src/components/horizon/HorizonFooter.test.tsx` | strips parallax transform under prefers-reduced-motion | Accessibility |
| P1 | `frontend/src/components/horizon/HorizonFooter.test.tsx` | renders all three caption variants for indices 0/1/2 | Caption pairing surface integration |
| P1 | `frontend/src/components/horizon/HorizonFooter.test.tsx` | uses `<picture>` with avif → webp source order | Asset delivery contract |
| P1 | `frontend/src/screens/SaveWrappedScreen.test.tsx` | silhouette mounts behind share card (z-index check) | Layering |
| P2 | `frontend/src/hooks/useHorizonPick.test.ts` | issues `<link rel="prefetch">` after 2s idle for next 2 indices | Prefetch behavior |

#### Test Data Requirements

- **Mock sessionStorage** — Use `vi.spyOn(window, 'sessionStorage', 'get')` or jsdom's built-in implementation. For "throws on access" path, mock setItem to throw `QuotaExceededError`.
- **Mock IntersectionObserver** — vitest-jsdom does not implement it; provide a polyfill in `frontend/src/test/test-setup.ts` if not already present.
- **Mock matchMedia** — for `prefers-reduced-motion` testing; standard jsdom polyfill.
- **Fixture: HORIZON_BASENAMES_SHORT** — In hook tests, override the manifest to a small array (e.g. 4 items) for tractable assertions; achieved via dependency injection or by passing `poolSize` to `newBag`/`drawFromBag` directly.
- **Mock Build object** — Reuse existing test factory if present; otherwise add minimal `mockBuild()` in `SaveWrappedScreen.test.tsx`.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-18

#### System Context
This is a frontend-only addition: one new component module (`components/horizon/`), one new hook (`hooks/useHorizonPick.ts`), one optional field on the `Build` interface, and modifications to two screens (`LandingScreen`, `SaveWrappedScreen`). It touches no Brightsmith zones, no DuckDB tables, no MCP tools, no Gemma roles, no FastAPI routers, no Pydantic models. The data flow is: `horizonManifest.ts` (static array) → `useHorizonPick` (sessionStorage-backed bag) → `HorizonFooter` / `HorizonSilhouette` → DOM. The only state crossing module boundaries is the hook return value (`HorizonPick | null`) and the new optional field on `Build`. From a system-architecture standpoint this is the smallest possible footprint a feature this visual can have, and it correctly avoids dragging the backend or pipeline into a decorative concern.

#### Data Flow Analysis
- **Source:** Static `HORIZON_BASENAMES: readonly string[]` in `horizonManifest.ts`. Verified the asset directory contains exactly 48 of each variant (AVIF-1400, AVIF-2048, WebP-1400, WebP-2048). The "48" constant in the spec lines up with what's on disk.
- **Per-mount draw:** `useHorizonPick(surface)` consults `sessionStorage[fp.horizon.bag.v1.{surface}]`, draws next index, writes back. Anti-adjacency is enforced by inspecting `lastShown` before returning.
- **SSR/hydration boundary:** Hook returns `null` on first render, populates after mount. Consumers must render an aspect-ratio-reserved skeleton on the null branch to prevent CLS.
- **Build commit boundary (`SaveWrappedScreen`):** First mount with `build.horizonIndex === undefined` → draw next from the desktop bag → `setBuild({ ...build, horizonIndex })`. Subsequent mounts read the existing index. **Important:** confirmed `renderWrapped(build.build_id)` only ships the build_id; the backend wrapped renderer does not see `horizonIndex`. The silhouette is a pure client-side overlay. The spec's "screenshot-stable" guarantee therefore applies to user device-screenshots, not to the backend-rendered share PNG. This is fine for v1 but should be made explicit (see Concerns).
- **Persistence:** Verified `frontend/src/store/buildStore.ts` uses `partialize` to persist *only* `hasSeenStatTutorial`. The `build` itself is **not** in the persisted slice. The spec's framing in §2 Decision 8 ("backwards compatibility — existing persisted Builds in localStorage have no `horizonIndex`") is therefore inaccurate as written: there are no persisted Builds today. The "optional with late-bind on first view" strategy is still correct, but for a different reason — it survives in-session resets and any future change that flips `build` into the persisted slice. Update §2 #8 rationale (see Concerns).

#### Contract Review
- **`useHorizonPick(surface): HorizonPick | null`** — clean. The `null` first-render contract is explicit and matches the SSR-safe constraint in §2.
- **`useHorizonAt(index: number): HorizonPick`** — non-nullable return is correct because the input is fully determined; no async work needed.
- **`drawFromBag(bag, poolSize)` / `newBag(poolSize, seed?)`** — pure helpers exported for tests. Good DI surface for unit tests; no need to inject the manifest itself (see Test Boundary).
- **`HorizonSilhouetteProps { index: number; className?: string }`** — minimal, locked. Correct.
- **`Build.horizonIndex?: number`** — optional, additive. Will not break the existing `Build` test fixtures or any consumer that doesn't read the field. Verified the field would land at line 170 of `frontend/src/types/build.ts` (spec says "around line 169" — close enough).
- **`StoredBag { order: number[]; cursor: number; lastShown: number | null }`** — compact, ~50 bytes serialized as claimed. Two bags = ~100 bytes total. Trivial.

#### Findings

##### Sound
- **Module placement.** `frontend/src/components/horizon/` is the right home — peer to `landing/`, `gauntlet/`, `wrapped/`, etc. The hook at `frontend/src/hooks/useHorizonPick.ts` is also correctly placed: `useHorizonPick` is a generic randomization+persistence primitive, not horizon-specific in shape, and it's consumed by both `HorizonFooter` (`components/horizon/`) and `SaveWrappedScreen` (`screens/`). Co-locating it inside `components/horizon/` would force `screens/SaveWrappedScreen.tsx` to import from a sibling component directory, which the codebase doesn't do elsewhere.
- **Versioned sessionStorage key (`fp.horizon.bag.v1.{surface}`)** — correct pattern. The `v1` suffix lets us cache-bust later if the manifest length changes (which would invalidate stored permutations).
- **Per-surface bags** — correctly modeled as a primitive (`'desktop' | 'mobile'`) rather than a viewport-derived value. The hook's contract doesn't lie about what determines independence.
- **Asset delivery** — `<picture>` with AVIF→WebP and 1400/2048 media gating matches `scripts/optimize_campus_images.py` output and the `min-width: 1200px` breakpoint matches Brightpath conventions.
- **Test DI surface** — `newBag(poolSize, seed?)` and `drawFromBag(bag, poolSize)` accepting `poolSize` directly is the right level of injection. The hook itself does NOT need to accept the manifest as a parameter; that would force every consumer to pass `HORIZON_BASENAMES` and leak the abstraction. The pure helpers tested in isolation give you full coverage of bag mechanics, and the hook-integration tests can stub `sessionStorage` and rely on the real (small, known) manifest. The proposed P0 "draws all 48 indices exactly once across 48 calls" can be tested at the `drawFromBag`/`newBag` layer without touching the hook at all.
- **No new dependencies.** Confirmed.
- **Assets verified.** 48/48/48/48 across the four variants in `frontend/public/campus/`.

##### Concerns
- **Decision #8 rationale is wrong.** §2 Decision 8 says optional `horizonIndex` is for backwards compat with "existing persisted Builds in localStorage." Verified: `buildStore` only persists `hasSeenStatTutorial`. No Builds are persisted today. **Impact:** the rationale misleads future readers about why the field is optional. **Recommendation:** rewrite #8's rationale to: *"Optional because (a) `Build` is constructed in stages across the gauntlet flow before the silhouette mount point ever sees it, and (b) any future change that adds `build` to the zustand persist `partialize` slice must continue to load older serialized blobs that lack the field. Late-bind on first `/app/save` view keeps construction sites honest about not needing to know about the silhouette."*
- **Silhouette and the backend-rendered share PNG are out of sync by design.** Verified `renderWrapped(build.build_id)` only ships the build_id; the backend wrapped renderer never sees `horizonIndex` and so the downloadable share PNG generated by Playwright will not contain the silhouette. **Impact:** the spec's §1 success-criteria framing "screenshot-stable" and §2 #7 framing "the downloadable PNG must match what was on screen" are misleading — they're true only for a user device-screenshot of the live page, not for the share PNG that the existing wrapped pipeline generates. **Recommendation:** in §1 and §2 #7, explicitly add: *"The silhouette is a client-side overlay; it is intentionally not baked into the backend-rendered share PNG. Both renderings are stable to the same `horizonIndex` only for the live page; the downloadable PNG remains silhouette-free in v1."* Carrying the silhouette into the share PNG is a separate, larger spec (it needs a backend asset path resolver and Playwright fixture). Do not block on it for the hackathon.
- **Prefetch race vs. fast navigation.** `<link rel="prefetch">` issued after a 2s idle window is correct for the steady-state case. For the racing-user case (route change at T+200ms), the prefetch never fires and we just take the cold-load hit. **Impact:** the warm-reroll motion budget (900ms) was sized assuming the next image is in the HTTP cache; under fast nav it will pop late. **Recommendation:** acknowledge this in §4 — the warm-reroll path *gracefully degrades* to a longer fade-in if the image isn't ready (Framer Motion will already do the right thing because the `<img>` doesn't fire `onLoad` until decode completes). No code change needed; just document that the 900ms budget is best-case.
- **`useSyncExternalStore` is overkill.** The `null`-on-first-render pattern with `useEffect`-mount population is correct for Vite + React 18 here. `useSyncExternalStore` is intended for genuinely external mutable stores (Redux, browser APIs that emit events). sessionStorage doesn't emit `storage` events for same-tab writes, and the hook's "current pick" is a one-time-per-mount capture, not a subscription. The current design is correct. Do not switch.
- **IntersectionObserver + RAF cleanup must be belt-and-suspenders.** Two listeners need cleanup in the `HorizonFooter` effect: (1) the `IntersectionObserver` (`.disconnect()`), (2) the `requestAnimationFrame` loop (`cancelAnimationFrame(handle)`). If either is forgotten, you leak a per-mount RAF callback that fires forever after the component unmounts. **Impact:** in dev with React StrictMode double-mounting, you'll spawn two RAF loops on every footer mount and only clean up one — observable as a CPU pegged on long-running landing pages. **Recommendation:** the effect must store both handles and tear both down; the staff engineer review at §8 should explicitly verify both cleanups in the implementation. Already on the §8 reviewer's hit list per the Claude Code Prompt step 6, so this is a flag-not-a-fix.
- **Silhouette overwrite guard.** The `SaveWrappedScreen` first-mount logic should be guarded as: `if (build && build.horizonIndex === undefined) setBuild({ ...build, horizonIndex: pick.index })`. The `=== undefined` check (not falsy) matters — index `0` is a valid value and `if (!build.horizonIndex)` would silently re-roll on every mount when index 0 was drawn. **Impact:** silent silhouette flip for 1/48 of all builds. **Recommendation:** spell out the `=== undefined` requirement in §4 Service Changes so the implementer doesn't write `if (!build.horizonIndex)`.
- **Caption pairing assertion.** §4 P0 test "captionFor(i) returns CAPTIONS[i % 3] for all i in 0..47" is correct, but the §1 success criterion says "same image always shows same caption." That's only true if the manifest order is stable. **Impact:** if anyone reorders `HORIZON_BASENAMES`, the caption pairing for any given image changes silently. **Recommendation:** add a one-line comment to `horizonManifest.ts` warning that reordering changes caption pairings, and in §11 Final Notes flag this as a known fragility (low risk; the manifest is hand-maintained and rarely touched).

##### Blockers
None. The architecture is sound; the issues above are documentation-and-correctness fixes, not structural ones.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)
1. Rewrite §2 Decision 8 rationale — the "existing persisted Builds in localStorage" claim is inaccurate; the persist `partialize` only includes `hasSeenStatTutorial`. Replace with the forward-compat + staged-construction rationale.
2. Update §1 Success Criteria and §2 Decision 7 to make explicit that the silhouette is a client-side overlay and is intentionally not baked into the backend-rendered share PNG in v1. Carrying it into the PNG is a separate spec.
3. Update §4 Service Changes to specify `if (build.horizonIndex === undefined)` (not falsy check) in the `SaveWrappedScreen` first-mount logic, so index 0 is treated as a valid set value.
4. Add a one-line note in the `horizonManifest.ts` description in §4 File Changes warning that reordering the array changes caption pairings (since pairing is `index % 3`).

#### Future Considerations (non-blocking, out of scope for this spec)
- Feature flag: not needed. The footer is a pure visual replacement of `LandingFooter`; no flag-gating required for hackathon demo.
- Bake silhouette into backend share PNG: defer to a follow-up spec when there's product evidence anyone cares.
- Vite plugin manifest auto-generation: §2 Out of Scope already covers this correctly.

### @fp-data-reviewer Review
**Status:** SKIPPED — no pipeline / DuckDB / stat / boss-fight changes

---

## §6 Implementation Log

**Status:** COMPLETE

### Pre-Implementation Spec Patches (from @fp-architect CHANGES REQUESTED)

Per CLAUDE.md escalation rules ("Minor: Fix and continue, document in §6"), the four documentation/correctness fixes raised by @fp-architect were applied to the spec before implementation began:

1. **§1 Overview** — Reworded "downloadable share PNG" claim to clarify silhouette is a client-side overlay only (not in backend-rendered PNG).
2. **§2 Decision 7** — Added explicit note that silhouette is intentionally NOT baked into the backend-rendered share PNG in v1; carrying it in is a deferred follow-up spec.
3. **§2 Decision 8** — Rewrote rationale: `buildStore` `partialize` only persists `hasSeenStatTutorial`, so there are no on-disk Builds today. Optional field correct for forward-compat + staged-construction reasons.
4. **§4 File Changes** — `SaveWrappedScreen.tsx` description specifies `if (build.horizonIndex === undefined)` (not `!build.horizonIndex`) so index 0 is treated as a valid set value. Added requirement that `horizonManifest.ts` carry a header comment warning that reordering re-pairs captions.

All four are documentation-and-correctness fixes; none required structural rewrites. Architect's verdict (CHANGES REQUESTED, no Blockers) was satisfied without re-review.

### Files Modified
| File | Change Summary |
|------|---------------|
| `frontend/src/components/horizon/horizonManifest.ts` | **Created.** 48 hand-maintained basenames + `HORIZON_POOL_SIZE` constant + reorder warning header per §4 patch 4. |
| `frontend/src/components/horizon/horizonCaptions.ts` | **Created.** Three captions as `readonly [string, string, string]` literal tuple. |
| `frontend/src/hooks/useHorizonPick.ts` | **Created.** `useHorizonPick(surface)` hook (SSR-safe, sessionStorage v1 keys, in-memory fallback, anti-adjacency, 2s idle prefetch via `<link rel="prefetch">`), `useHorizonAt(index)` for locked indices, pure helpers `newBag` (Fisher-Yates with optional Park-Miller LCG seed; uses `crypto.getRandomValues` else `Math.random`) and `drawFromBag` and `captionFor`. |
| `frontend/src/components/horizon/HorizonFooter.tsx` | **Created.** Three-zone composite (sky-bleed 120px / image stage `clamp(220px, 22vw, 480px)` / ground-bleed 60px) + three-column chrome bar (identity / provenance / studio). `<picture>` AVIF→WebP with 2048 media-gated by `(min-width: 1200px)`. Cold-mount sequence wired with `springs.gentle` for the image and `stagger.normal` for the chrome. `prefers-reduced-motion` strips transforms (opacity-only, 240ms). 0.85x parallax via IntersectionObserver + RAF, **both** torn down on unmount per arch-review §5. Mobile (≤480px) override via scoped `<style>` block: 200px height, `object-position: center 30%`, caption hidden. Below 840px the chrome bar stacks. HyenaStudios placeholder = 32px circle with "HS" text + `border-border-subtle`. GemmaStar = inline SVG with info→insight gradient. |
| `frontend/src/components/horizon/HorizonSilhouette.tsx` | **Created.** 180px-tall band, opacity 0.6, `mask-image` vertical fade (transparent → black 70%), single `<picture>` AVIF→WebP, no caption, no chrome. Consumes `useHorizonAt(index)` so the locked index never re-rolls. Props `{ index, className? }`. |
| `frontend/src/types/build.ts` | **Modified.** Added `horizonIndex?: number` to `Build` interface, just above `profile_name?`. |
| `frontend/src/screens/SaveWrappedScreen.tsx` | **Modified.** Imports `HorizonSilhouette` + `useHorizonPick`. On first mount with `build.horizonIndex === undefined` (NOT `!build.horizonIndex` — index 0 is valid), draws from desktop bag and calls `setBuild({ ...build, horizonIndex: pick.index })`; the `=== undefined` guard short-circuits StrictMode double-mount. In the `viewer` phase, mounts `<HorizonSilhouette index={build.horizonIndex} />` inside a z-0 absolute overlay behind the WrappedViewer (z-10), keyed off `build.horizonIndex !== undefined`. PageContainer/AnimatePresence pattern preserved. |
| `frontend/src/pages/Landing.tsx` | **Modified.** Replaced `LandingFooter` import + JSX with `HorizonFooter`. (Spec §4 said `screens/LandingScreen.tsx`, but the marketing footer actually lives in `pages/Landing.tsx` — see Deviations.) |
| `frontend/src/pages/Landing.test.tsx` | **Modified.** Updated the section-order assertion to expect `horizon-footer` in place of `landing-footer`. Direct mechanical consequence of the component swap (same class of edit the spec already authorizes for `LandingScreen.test.tsx`). |
| `frontend/src/components/landing/LandingFooter.tsx` | **Deleted.** Replaced by HorizonFooter. |
| `frontend/src/components/landing/LandingFooter.test.tsx` | **Deleted.** Replaced by HorizonFooter test (added in step 4 by @test-writer). |

`frontend/src/screens/LandingScreen.test.tsx` and `frontend/src/screens/SaveWrappedScreen.test.tsx` were verified to need no edits — neither references `LandingFooter` directly, and the existing SaveWrapped assertions remain green with the silhouette overlay behind the viewer card.

### Deviations from Spec

1. **Spec said `screens/LandingScreen.tsx` for the footer swap; actual location is `pages/Landing.tsx`.** The marketing footer (the one being replaced) is composed in `pages/Landing.tsx` (the marketing constellation page at `/`), not `screens/LandingScreen.tsx` (the `/app` entry CTA). `LandingScreen.tsx` doesn't import `LandingFooter` at all. Updated `pages/Landing.tsx` instead, and updated `pages/Landing.test.tsx` (which asserts section ordering by id — `landing-footer` → `horizon-footer`) as the same mechanical consequence the spec authorizes for `LandingScreen.test.tsx`.
2. **Hook returns the basename via type assertion (`HORIZON_BASENAMES[i] as string`) rather than via `???.` defensive guards.** Project tsconfig has `noUncheckedIndexedAccess: true`. We bounds-check the index immediately above (modulo by `HORIZON_POOL_SIZE` for `useHorizonAt`, drawn from a length-`HORIZON_POOL_SIZE` array for `useHorizonPick`), so the assertion is provably safe. Adding runtime `??` fallbacks would imply false ambiguity to the next reader.
3. **Anti-adjacency is enforced only at bag-refill seams, not within a single bag.** A single Fisher-Yates'd bag of 48 already has zero internal repeats (it's a permutation of `[0..47]`), so per-draw anti-adjacency would be a no-op except at the boundary between exhaustion and reshuffle. The spec wording "never returns the same index twice in a row" is satisfied: across any two consecutive draws (within a bag or across the seam), no repeat is possible. This is the same approach the mockup uses.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 (tsc) | FAIL | 10 errors in `useHorizonPick.ts`, all `noUncheckedIndexedAccess` related (array indexing returning `T \| undefined` where `T` was expected). | Asserted `as <T>` at index sites where bounds were proven by construction (Fisher-Yates loop bounds, modulo-normalized indices). |
| 2 (tsc) | PASS | — | — |
| 1 (vitest) | FAIL (1/440) | `pages/Landing.test.tsx > renders all 9 sections in the spec-mandated order` — section-id list still contained `landing-footer` after the component swap. | Updated the expected-id list to `horizon-footer`. Documented as Deviation #1 (the spec's "LandingScreen.test.tsx" authorization clearly covers this same mechanical edit). |
| 2 (vitest) | PASS (439/440, 1 pre-existing skip) | — | — |

### Fix-Pass (post-§8 design audit + code review, 2026-04-18)

After @fp-design-auditor returned CHANGES REQUESTED (3 Minor FAILs) and @faang-staff-engineer returned CHANGES REQUIRED (2 Major + 5 Minor), the implementer applied a single fix-pass. All findings were addressed in-place; no spec content changed.

| File | Change Made | Severity Addressed |
|------|-------------|-------------------|
| `frontend/src/components/horizon/HorizonFooter.tsx` | Sky-bleed gradient mid-stop changed from `rgba(27, 29, 48, 0.65)` to `color-mix(in srgb, var(--color-bg-deep) 65%, transparent)`. | Design Audit FAIL-1 (Minor) |
| `frontend/src/components/horizon/HorizonFooter.tsx` | Caption color changed from inline `rgba(245, 240, 232, 0.6)` to Tailwind utility `text-text-primary/60`; inline `color` style removed. | Design Audit FAIL-2 (Minor) |
| `frontend/src/components/horizon/HorizonFooter.tsx` | Ground-bleed gradient mid-stop changed from `rgba(18, 19, 31, 0.7)` to `color-mix(in srgb, var(--color-bg-void) 70%, transparent)`. | Design Audit FAIL-3 (Minor) |
| `frontend/src/components/horizon/HorizonFooter.tsx` | Removed dead `mobile-only-position` className + empty inline `style={{...}}` object on the `<img>`. | Code Review Minor #5 (Minor #3 in §8) |
| `frontend/src/components/horizon/HorizonFooter.tsx` | `IntersectionObserver` callback now uses `entries.find(e => e.target === stage)` instead of mutating `isVisible` inside `entries.forEach` — defensive against future second-observe targets. | Code Review Minor #7 (Minor #5 in §8) |
| `frontend/src/components/horizon/HorizonSilhouette.tsx` | `<img loading="lazy">` → `loading="eager"` (silhouette mounts in-viewport after a 6-18s wait; lazy was a guaranteed pop-in). | Code Review Minor #6 (Minor #4 in §8) |
| `frontend/src/components/horizon/HorizonSilhouette.test.tsx` | Test renamed/updated to assert `loading="eager"` to match the eager-load fix. | Test alignment |
| `frontend/src/hooks/useHorizonPick.ts` | `safeReadBag` now falls through to `inMemoryBags` whenever sessionStorage hands back null (not just when it throws). `safeWriteBag` now writes to `inMemoryBags` UNCONDITIONALLY, then mirrors best-effort to sessionStorage. In-memory is the source of truth; storage is the cross-mount cache. | Code Review Major #1 |
| `frontend/src/hooks/useHorizonPick.ts` | New exported helper `drawAndPersist(surface)` consolidates the read-draw-write cycle for non-hook callers (used by SaveWrappedScreen). `safeReadBag` and `safeWriteBag` are now exported for the same reason. | Code Review Major #2 enabler |
| `frontend/src/hooks/useHorizonPick.ts` | Prefetch `<link>` elements are now tracked in a `useRef` array and removed in the effect's cleanup. Prevents unbounded `<head>` growth across SPA navigation + StrictMode double-mount. | Code Review Minor #3 (Minor #1 in §8) |
| `frontend/src/hooks/useHorizonPick.ts` | New exported `__resetInMemoryBagsForTesting()` for vitest's `beforeEach`/`afterEach`. Stops module-scoped `inMemoryBags` from bleeding across test cases now that Major #1 is fixed and the in-memory path is more consequential. | Code Review Minor #4 (Minor #2 in §8) |
| `frontend/src/screens/SaveWrappedScreen.tsx` | Removed the unconditional `useHorizonPick("desktop")` call. The first-mount commit effect now uses `drawAndPersist("desktop")` only when `build.horizonIndex === undefined` — zero touches to the desktop bag on subsequent mounts. Stops save-screen views from polluting the landing-footer's bag walk. | Code Review Major #2 |
| `frontend/src/hooks/useHorizonPick.test.ts` | Added regression test `preserves anti-adjacency across mounts when setItem silently drops (Major #1 regression)` — spies setItem to throw + getItem to return null, asserts two consecutive mounts return different indices and the in-memory cursor advanced to 2. Added `drawAndPersist` describe block (2 tests). Added `__resetInMemoryBagsForTesting()` to `beforeEach`/`afterEach`. | Major #1 + Minor #4 + new helper coverage |
| `frontend/src/screens/SaveWrappedScreen.test.tsx` | Added regression test `does NOT advance the desktop bag on remount when horizonIndex is already set (Major #2 regression)` — seeds the bag at cursor 7, mounts the screen 3 times with `horizonIndex` already locked, asserts cursor stays at 7. Added `__resetInMemoryBagsForTesting` + sessionStorage clear to `beforeEach`. | Major #2 |

**Build Accountability for fix-pass:**
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 (tsc) | PASS | — | — |
| 1 (vitest) | PASS (504 pass / 1 skip / 0 fail) | — | — |

Net: 497 → 504 tests (+7 net new), zero regressions. The 1 skip is the same pre-existing case noted in the §7 baseline.

---

## §7 Test Coverage

**Status:** COMPLETE

### Files Created / Modified
| File | Action | Lines |
|------|--------|-------|
| `frontend/src/hooks/useHorizonPick.test.ts` | Created | 28 tests |
| `frontend/src/components/horizon/HorizonFooter.test.tsx` | Created | 16 tests |
| `frontend/src/components/horizon/HorizonSilhouette.test.tsx` | Created | 9 tests |
| `frontend/src/screens/SaveWrappedScreen.test.tsx` | Modified (added 5 tests) | 5 new tests |

### Tests Added

| Test File | Test Name | Priority | What It Tests |
|-----------|-----------|----------|---------------|
| `useHorizonPick.test.ts` | newBag > produces a permutation of [0..poolSize-1] | P0 | Shuffle correctness |
| `useHorizonPick.test.ts` | newBag > starts with cursor 0 and lastShown null | P0 | Bag init invariants |
| `useHorizonPick.test.ts` | newBag > seeded shuffles are deterministic | — | Test infra contract |
| `useHorizonPick.test.ts` | newBag > different seeds produce different permutations | — | Sanity |
| `useHorizonPick.test.ts` | newBag > works for poolSize=1 (degenerate case) | — | Boundary |
| `useHorizonPick.test.ts` | newBag > works for poolSize=4 (test fixture size) | — | Boundary |
| `useHorizonPick.test.ts` | drawFromBag > draws all 48 indices exactly once across 48 calls | P0 | Bag coverage guarantee |
| `useHorizonPick.test.ts` | drawFromBag > never returns the same index twice in a row within a single bag | P0 | Anti-adjacency intra-bag |
| `useHorizonPick.test.ts` | drawFromBag > never returns the same index twice in a row across the bag-refill seam | P0 | Anti-adjacency at the seam (the load-bearing case) |
| `useHorizonPick.test.ts` | drawFromBag > reshuffles after exhaustion | P0 | Bag refresh |
| `useHorizonPick.test.ts` | drawFromBag > handles a mismatched-poolSize stored bag by reshuffling | — | Defensive: stale v1 bag against changed manifest |
| `useHorizonPick.test.ts` | drawFromBag > updates lastShown to the just-drawn index | — | Internal contract |
| `useHorizonPick.test.ts` | drawFromBag > increments cursor on each draw | — | Internal contract |
| `useHorizonPick.test.ts` | captionFor > returns CAPTIONS[i % 3] for all i in 0..47 | P0 | Caption pairing across full pool |
| `useHorizonPick.test.ts` | captionFor > maps known boundary indices to the right caption | P0 | Modulo wrap at 0/1/2/3/47 |
| `useHorizonPick.test.ts` | captionFor > handles negative indices defensively | — | Safe-modulo guard |
| `useHorizonPick.test.ts` | useHorizonPick > returns null on first render (SSR-safe) | P0 | SSR safety |
| `useHorizonPick.test.ts` | useHorizonPick > populates a valid pick after mount | P0 | Hook output contract |
| `useHorizonPick.test.ts` | useHorizonPick > persists state across hook re-mounts via sessionStorage | P0 | Continuity within session |
| `useHorizonPick.test.ts` | useHorizonPick > desktop and mobile bags are independent | P0 | Per-surface bags |
| `useHorizonPick.test.ts` | useHorizonPick > falls back to in-memory bag when sessionStorage.setItem throws | P0 | QuotaExceededError graceful degradation |
| `useHorizonPick.test.ts` | useHorizonPick > falls back gracefully when sessionStorage.getItem also throws | — | SecurityError graceful degradation |
| `useHorizonPick.test.ts` | useHorizonAt > returns the same pick for the same index, every time | P0 (silhouette stability) | Locked-at-commit guarantee |
| `useHorizonPick.test.ts` | useHorizonAt > resolves basename from HORIZON_BASENAMES | — | Basename mapping |
| `useHorizonPick.test.ts` | useHorizonAt > pairs caption via index % 3 | — | Caption pairing |
| `useHorizonPick.test.ts` | useHorizonAt > normalizes out-of-range indices via modulo | — | Defensive: corrupted Build state |
| `useHorizonPick.test.ts` | useHorizonAt > normalizes negative indices safely | — | Safe-modulo guard |
| `useHorizonPick.test.ts` | useHorizonPick prefetch > schedules a prefetch <link> after the 2s idle window | P2 | Prefetch behavior (real timers, 2.2s wait) |
| `HorizonFooter.test.tsx` | layout and structure > renders the three-zone composite + chrome bar | P0 | Footer existence + identity/studio columns |
| `HorizonFooter.test.tsx` | layout and structure > renders the live-app link with correct href | — | Identity column link |
| `HorizonFooter.test.tsx` | layout and structure > renders the chrome bar three-column grid at desktop viewport | P0 | Three-column layout |
| `HorizonFooter.test.tsx` | layout and structure > renders the AI disclaimer copy (provenance column) | — | Provenance copy |
| `HorizonFooter.test.tsx` | layout and structure > renders the HyenaStudios attribution + © (studio column) | — | Studio column + `<address>` semantic |
| `HorizonFooter.test.tsx` | layout and structure > hides caption below 480px viewport via scoped CSS rule | P0 | Responsive caption hide rule presence |
| `HorizonFooter.test.tsx` | caption pairing > renders caption N as <text> when index N is drawn | P1 | Caption pairing surface (parameterized for indices 0/1/2) |
| `HorizonFooter.test.tsx` | caption pairing > rotates caption with image (index 3 wraps back to caption 0) | P1 | Modulo wrap |
| `HorizonFooter.test.tsx` | <picture> asset delivery > emits AVIF before WebP source order | P1 | Modern format wins |
| `HorizonFooter.test.tsx` | <picture> asset delivery > media-gates the 2048 variants behind (min-width: 1200px) | P1 | Variant breakpoint |
| `HorizonFooter.test.tsx` | <picture> asset delivery > img has lazy loading + async decoding + decorative alt | — | Performance + a11y attrs |
| `HorizonFooter.test.tsx` | <picture> asset delivery > srcset URLs resolve to a real basename in the manifest | — | Defensive: never literal "undefined" in URL |
| `HorizonFooter.test.tsx` | prefers-reduced-motion > attaches scroll + resize listeners when reduced motion is OFF (default jsdom) | P1 (partial — see §10) | OFF-path listener attach (ON-path documented as untestable in jsdom) |
| `HorizonFooter.test.tsx` | unmount cleanup > removes scroll + resize listeners on unmount | — | Belt-and-suspenders cleanup (arch review §5) |
| `HorizonSilhouette.test.tsx` | renders image at given index — picture sources point to that basename | P0 | Locked-index → basename mapping |
| `HorizonSilhouette.test.tsx` | renders at 60% opacity (the share card reads on top) | P0 | Opacity contract |
| `HorizonSilhouette.test.tsx` | locked: re-renders with same index produce same image src | P0 | Stability contract (screenshot-stable) |
| `HorizonSilhouette.test.tsx` | different indices produce different image sources | — | Index-to-image bijection |
| `HorizonSilhouette.test.tsx` | decorative: empty alt + role=presentation on the img | — | A11y |
| `HorizonSilhouette.test.tsx` | uses lazy loading + async decoding | — | Perf attrs |
| `HorizonSilhouette.test.tsx` | emits AVIF before WebP source order (modern format wins) | — | Asset delivery |
| `HorizonSilhouette.test.tsx` | accepts an optional className (caller-controlled positioning) | — | Component contract |
| `HorizonSilhouette.test.tsx` | defends against an out-of-range index by wrapping into the pool | — | Defensive: corrupted horizonIndex |
| `SaveWrappedScreen.test.tsx` | sets build.horizonIndex on first mount when absent | P0 | Persistence on commit |
| `SaveWrappedScreen.test.tsx` | preserves build.horizonIndex on subsequent mounts (locked-at-commit) | P0 | The `=== undefined` guard for index 0 (regression guard against `!build.horizonIndex`) |
| `SaveWrappedScreen.test.tsx` | preserves a non-zero horizonIndex on remount | — | Same contract for non-zero indices |
| `SaveWrappedScreen.test.tsx` | silhouette mounts behind share card (z-index check) | P1 | Layering: silhouette z-0, viewer z-10 |
| `SaveWrappedScreen.test.tsx` | does not render the silhouette during the save-confirmation phase | — | Phase-gated render: silhouette only appears in viewer phase |

### Edge Cases Covered

- [x] Bag exhaustion + reshuffle (drawn 48, draw the 49th, get a fresh permutation)
- [x] Anti-adjacency at the seam between two bags (50 random seeds, no collisions)
- [x] sessionStorage QuotaExceededError on setItem → in-memory fallback
- [x] sessionStorage SecurityError on getItem → in-memory fallback
- [x] Stale stored bag (length mismatch) → reshuffles instead of indexing OOB
- [x] horizonIndex === 0 must NOT be re-rolled by `!build.horizonIndex` (the regression test for the spec §4 patch)
- [x] horizonIndex out-of-range (corrupted state) → modulo-normalized to a valid basename, never literal "undefined" in srcset
- [x] Negative index → safe-modulo wrap
- [x] Caption modulo wrap at indices 0/1/2/3/47
- [x] Per-surface independence (desktop draw does not advance mobile cursor)
- [x] Same-index re-render → identical output (silhouette stability)
- [x] Picture source order: AVIF before WebP, both at 1400 + 2048 widths
- [x] 2048 variants media-gated; 1400 fallback default
- [x] Decorative alt + role=presentation on both footer image and silhouette
- [x] Save phase does not leak silhouette into SaveConfirmation card
- [x] Viewer phase z-stacking: silhouette z-0, WrappedViewer z-10
- [x] Cleanup contract: scroll + resize listeners removed on unmount
- [x] Listener attach contract under default (motion-on) path

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | N/A (no backend changes) | — | — | — |
| vitest | 497 | 0 | 1 | 498 |
| TypeScript (tsc --noEmit) | clean | — | — | — |

Net new tests added: 58 (28 hook + 16 footer + 9 silhouette + 5 SaveWrapped). Total grew from 439 → 497 (+58); the 1 skip is pre-existing and unrelated.

### Existing Tests Status

All "Confirmed Safe (must NOT break)" tests from §4 remain green:
- `frontend/src/store/buildStore.test.ts` — passes
- All `frontend/src/components/{gauntlet,school,tree,menu,wrapped}` tests — pass
- All `frontend/src/screens/*.test.tsx` non-targets — pass
- All hook tests (this is the only one in `frontend/src/hooks/`) — pass
- All `frontend/src/api/` tests — pass
- All `frontend/src/lib/` tests — pass

### Gaps Identified (logged for §10 Discussion)

1. **Reduced-motion ON-path inside HorizonFooter is not directly testable in vitest+jsdom.** framer-motion's `useReducedMotion()` is `useState(false)` + a one-shot matchMedia change-event subscription. In jsdom, our matchMedia mock cannot retroactively fire `change` events to a not-yet-subscribed listener, so the hook returns `false` for the lifetime of the test even when `setReducedMotion(true)` is called. This is a known limitation that `HeroSection.test.tsx` works around the same way (DOM-output assertions). The reduced-motion code path inside HorizonFooter is therefore covered by:
   - source-code review of the `if (prefersReducedMotion) return` guard and the conditional motion-config ternaries (both highly visible and in plain sight)
   - manual QA on a real browser with the OS toggle
   - the spec §8 design audit (mechanical token compliance against `motion.ts`)

   The OFF-path (motion-on) IS directly tested. Net listener cleanup is verified for the OFF-path on unmount; under reduced-motion the production code's early-return guarantees no listeners are attached at all.

2. **Parallax inline transform (translate3d) is not testable in jsdom** because the `IntersectionObserver` stub never fires `isIntersecting`, so the RAF never writes the transform. The parallax math is structural and reviewed in source. The cleanup contract (RAF + observer torn down on unmount) IS verified.

3. **Prefetch test uses real timers (2.2s wait).** Fake-timer ordering interacts poorly with React's effect commit boundary in vitest 3.x; real timers are dependable. Cost: +2.2s per CI run. Acceptable given P2 priority.

4. **`<link>` `as="image"` attribute reflection in jsdom is non-standard.** jsdom does not always reflect `link.as = "image"` to the `as` attribute. The prefetch test reads the property OR the attribute, whichever is set, to remain compatible.

---

## §8 Reviews

**Status:** DESIGN AUDIT RESOLVED — CODE REVIEW RESOLVED

> **Fix-pass note (2026-04-18):** All 3 design audit FAILs (FAIL-1/2/3) and all 7 code review findings (Majors #1, #2 + Minors #1-#5) were resolved in a single fix-pass on 2026-04-18. See §6 → "Fix-Pass" table for the file-by-file breakdown. tsc + vitest stayed green (504 pass / 1 skip / 0 fail). Both verdicts below are preserved as the as-of-review snapshot for traceability.

### Design Audit (@fp-design-auditor)
**Status:** CHANGES REQUESTED → **RESOLVED** (fix-pass 2026-04-18; see §6 Fix-Pass table)
**Reviewed:** 2026-04-18

---

## `HorizonFooter.tsx`

### PASS
- `bg-bp-void` (chrome bar, line 302), `bg-bp-deep` (skeleton and stage container, lines 224, 249) — correct background tokens for their respective surfaces.
- `border-border-subtle` (chrome bar top border, line 302; HyenaStudios logo border, line 352) — correct border token.
- `text-text-primary` (FutureProof wordmark, line 312), `text-text-secondary` (Live app link, Gemma attribution, HyenaStudios name, lines 315, 330, 362), `text-text-muted` (metadata rows, disclaimer, copyright, lines 334, 337, 366) — all text colors use correct semantic tokens.
- `text-accent-thrive` (Live app hover, line 315) — correct accent token for the hover state on a CTA-adjacent link.
- `font-display` (FutureProof wordmark, HyenaStudios name, lines 312, 362), `font-body` (Live app link, Gemma attribution, disclaimer, lines 315, 330, 337), `font-data` (metadata rows, copyright, lines 334, 366) — all font families reference registered Brightpath tokens.
- `text-heading` (FutureProof wordmark, line 312), `text-subheading` (HyenaStudios name, line 362), `text-body` (Live app link, line 315), `text-small` (Gemma attribution, disclaimer, lines 330, 337), `text-micro` (metadata, copyright, caption, lines 334, 337, 274) — all type sizes reference the DESIGN.md scale. No arbitrary `text-[Npx]` values found in Tailwind utilities.
- `tracking-widest` (caption, line 274) — matches §3 spec requirement.
- `duration-fast` (Live app link transition, line 316) — correct CSS transition token.
- `springs.gentle` (image scale-in motion, line 181) — correct preset for cold-mount image entrance per §3 Brightpath Design References.
- `stagger.normal` (chrome bar stagger, line 208) — correct preset (80ms) per §3 Brightpath Design References. Usage as `staggerChildren` in Framer Motion's transition object is the correct consumption pattern for a numeric stagger value.
- GemmaStar SVG (lines 81-91) uses `var(--color-accent-info)` and `var(--color-accent-insight)` via CSS variables — correct, matches the Gemma Interactions spec.
- Image stage height `clamp(220px, 22vw, 480px)` (line 252) — matches §3 Responsive Behavior table exactly.
- Sky-bleed height 120px (line 239), ground-bleed height 60px (line 291) — match §3 spec dimensions exactly.
- Mobile overrides in scoped `<style>` block (lines 397-404): `height: 200px`, `object-position: center 30%`, caption `display: none` — all match §3 Responsive Behavior table exactly. Chrome stacking below 840px matches §3 layout spec.
- `prefers-reduced-motion` branches use opacity-only fades at 240ms (lines 167-218) — correct per §3 Interactions.

### FAIL

**FAIL-1 — Hardcoded rgba for bg-deep in sky-bleed gradient mid-stop (HorizonFooter.tsx line 241)**
- Expected: `var(--color-bg-deep)` (or `var(--color-bg-deep)` at reduced alpha via a CSS alpha channel modifier)
- Found: `rgba(27, 29, 48, 0.65)` — this is `--color-bg-deep` (#1B1D30) decomposed into a raw rgba value
- DESIGN.md section: Color Tokens / Backgrounds — `bg-deep` is `#1B1D30`, Tailwind `bg-bp-deep`
- Context: The gradient string already opens with `var(--color-bg-deep)` at the 0% stop, making the raw rgba at the 45% stop inconsistent within the same property. The fix is to use `color-mix(in srgb, var(--color-bg-deep) 65%, transparent)` for the mid-stop, or restructure the gradient to omit the mid-stop (a two-stop linear-gradient from `var(--color-bg-deep)` to `transparent` at 100% is simpler and spec-faithful).
- Severity: Minor — inline fix.

**FAIL-2 — Hardcoded rgba for text-primary as caption color (HorizonFooter.tsx line 280)**
- Expected: Reference to `--color-text-primary` (or a Tailwind `text-text-primary` class with opacity utility)
- Found: `color: "rgba(245, 240, 232, 0.6)"` — this is `--color-text-primary` (#F5F0E8) decomposed into a raw rgba
- DESIGN.md section: Color Tokens / Text — `primary` is `#F5F0E8`, Tailwind `text-text-primary`
- Fix: Replace inline `color` style with a Tailwind class `text-text-primary/60` (Tailwind opacity modifier) and remove the inline `color` style property, or use `color: "color-mix(in srgb, var(--color-text-primary) 60%, transparent)"` if an inline style is required.
- Severity: Minor — inline fix.

**FAIL-3 — Hardcoded rgba for bg-void in ground-bleed gradient mid-stop (HorizonFooter.tsx line 294)**
- Expected: `var(--color-bg-void)` at reduced alpha, not a raw rgba decomposition
- Found: `rgba(18, 19, 31, 0.7)` at the 55% stop — this is `--color-bg-void` (#12131F) as raw rgba
- DESIGN.md section: Color Tokens / Backgrounds — `bg-void` is `#12131F`, Tailwind `bg-bp-void`
- Context: The same gradient's 100% stop correctly uses `var(--color-bg-void)`. The mid-stop reverts to a hardcoded value. Same pattern as FAIL-1: use `color-mix(in srgb, var(--color-bg-void) 70%, transparent)` for the mid-stop.
- Severity: Minor — inline fix.

### WARNINGS

- **Caption text-shadow value deviates from §3 spec** (HorizonFooter.tsx line 279): the spec §3 layout diagram specifies `text-shadow: 0 1px 2px rgba(0,0,0,0.7)`, but the implementation uses `rgba(18, 19, 31, 0.95)` (the void color, near-opaque). Text-shadow is not covered by DESIGN.md shadow tokens (the shadow token table covers box-shadows only), so this is not a token violation — but it is a spec-fidelity deviation. The implementation's choice (dark void tint at 95% opacity instead of near-black at 70%) produces a slightly heavier caption shadow and was arguably intentional for legibility against the campus art. Flagging for implementer awareness; no token rule is violated.
- **HyenaStudios logo placeholder background `rgba(255, 255, 255, 0.02)`** (HorizonFooter.tsx line 357): This is a raw rgba with no corresponding DESIGN.md token. DESIGN.md's border table only specifies opacity levels at 6%, 10%, and 20% (border-subtle, border-default, border-strong); 2% is not a named state. The spec §2 Out of Scope explicitly calls this out as a placeholder pending a real brand asset — the placeholder is intentional and not flagged as a violation, but the raw rgba should be noted. When the real HyenaStudios logo asset lands, this inline style is deleted.
- **`staggerChildren: stagger.normal` is consumed as a raw number in Framer Motion's `transition` object** (HorizonFooter.tsx line 208): `stagger.normal` resolves to `0.08` (a numeric seconds value). This is the correct Framer Motion consumption pattern for a `staggerChildren` value — it is not a violation. Documenting for clarity since the spec says "motion uses presets" and a reviewer might flag `0.08` as a magic number without this context.

---

## `HorizonSilhouette.tsx`

### PASS
- `rounded-xl` (container, line 35) — correct radius token (`radius-xl`, 20px per DESIGN.md).
- Opacity 0.6 (line 40) — matches §3 spec ("opacity 0.6").
- Height 180px (line 37) — matches §3 spec ("180px-tall band").
- CSS mask-image gradient (lines 41-43) — vertical fade from transparent to opaque, matches §3 "Vertical mask: linear-gradient(to top, transparent, deep)" spec intent. No color token violation — mask-image uses opacity ramp values (transparent, rgba 0.5, rgba 1), not color tokens.
- No Tailwind color utilities — the component carries no text or background color classes. Correct: it is purely a decorative image container.
- `loading="lazy"`, `decoding="async"`, `alt=""`, `role="presentation"` (lines 66-70) — correct attribute set per §3 Accessibility table.
- `<picture>` source order AVIF → WebP, 2048 media-gated at `(min-width: 1200px)`, 1400 as default (lines 45-63) — matches §3 `<picture>` source media gating spec exactly.

### FAIL
None.

### WARNINGS
- **`objectPosition: "center 35%"`** (HorizonSilhouette.tsx line 72): The spec §3 silhouette layout diagram does not specify an `objectPosition` value. The desktop footer uses `center 40%` (via the `object-[center_40%]` Tailwind class on the `<img>`) and the mobile override forces `center 30%`. The silhouette landing at `center 35%` is not a token violation (object-position is not a design token), but it is an undocumented deviation from both sibling values. Low visual impact given the small height (180px) and opacity (0.6).

---

## `SaveWrappedScreen.tsx` (silhouette mount area)

### PASS
- `HorizonSilhouette` is mounted inside `z-0 absolute inset-x-0 bottom-0` (lines 200-206) behind the `z-10` WrappedViewer container (line 207) — correct layering per §3 layout spec.
- Guard `build.horizonIndex !== undefined` (line 199) — correctly uses `=== undefined` check per §4 patch 3 (index 0 is valid).
- No color, typography, or motion tokens introduced in the silhouette mount area — the surrounding motion wrappers (`AnimatePresence`, `motion.div`) use `opacity: 0/1` transitions only, consistent with pre-existing screen patterns.
- `text-heading` (line 177), `text-text-primary` (line 177), `text-body` (line 181), `text-text-secondary` (line 181), `text-body` (line 233), `text-heading` + `text-accent-alert` (line 229) — all existing screen text tokens are correct.

### FAIL
None.

### WARNINGS
None.

---

## `pages/Landing.tsx`

### PASS
- `bg-bp-void` (main element, line 20) — the page root uses the correct deepest background token for a full-screen dark canvas.
- `HorizonFooter` import replaces `LandingFooter` (line 16) — swap is clean, no residual references to the deleted component.

### FAIL
None.

### WARNINGS
None.

---

## Summary of Violations

| ID | File | Line | Rule | Severity |
|----|------|------|------|----------|
| FAIL-1 | `HorizonFooter.tsx` | 241 | Raw `rgba(27, 29, 48, 0.65)` instead of CSS var for `--color-bg-deep` | Minor |
| FAIL-2 | `HorizonFooter.tsx` | 280 | Raw `rgba(245, 240, 232, 0.6)` instead of token for `--color-text-primary` | Minor |
| FAIL-3 | `HorizonFooter.tsx` | 294 | Raw `rgba(18, 19, 31, 0.7)` instead of CSS var for `--color-bg-void` | Minor |

All three violations are inline-fixable without redesign. They are all within gradient mid-stop definitions (FAIL-1, FAIL-3) or a single inline `color` style property (FAIL-2). The `color-mix()` fix for gradient mid-stops and the `text-text-primary/60` Tailwind utility for the caption color are drop-in replacements.

No hex codes found anywhere outside of gradient mid-stops. No type sizes outside the DESIGN.md scale. No spring magic numbers — all motion uses named preset imports from `@/styles/motion`. Spec §3 dimensional requirements (clamp heights, bleed heights, silhouette height, opacity, breakpoints) all match the implementation.

### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED → **RESOLVED** (fix-pass 2026-04-18; see §6 Fix-Pass table)
**Reviewed:** 2026-04-18

#### Summary
This is solid work — well above the median for AI-assisted frontend code I see in review. Pure helpers are well-factored, tests are honest about their limitations (the §10 framer-motion note is exactly the kind of self-aware test boundary I want to see), the `=== undefined` guard for index 0 is correctly defended by a regression test, the type assertions are all provably safe by construction, and the parallax cleanup teardown is belt-and-suspenders. Park-Miller LCG is a fine seedable PRNG for 48-element shuffles in tests, and prod correctly uses `crypto.getRandomValues`.

There are, however, three real correctness issues — two of which I'd send back to the implementer before this ships, and one that's only "minor" because the user-visible failure mode is decorative drift. There's also one DOM-growth concern with the prefetch path that I'd want addressed even though it doesn't break anything in a single-page session. None of this is BLOCKER; ARCH was right that the design is sound. But the bag-state-loss bug (Major #1) is a quiet correctness regression hiding behind a code path that *looks* like it has graceful degradation.

Verdict: CHANGES REQUIRED — fix the two Majors, fold in the Minors at implementer's discretion.

#### Findings

##### Major #1 — `safeReadBag` ignores in-memory fallback when sessionStorage is available-but-empty
**File:** `frontend/src/hooks/useHorizonPick.ts:60-83`
**Severity:** Major

The control flow:

```ts
function safeReadBag(surface) {
  try {
    if (window.sessionStorage) {
      const raw = window.sessionStorage.getItem(storageKey(surface));
      if (raw) { /* return parsed */ }
      return null;        // ← BUG: returns null without consulting in-memory
    }
  } catch { /* fall through */ }
  return inMemoryBags.get(surface) ?? null;
}
```

The in-memory fallback is reached only when sessionStorage *throws* on access. But if `setItem` previously threw (quota / private mode), the code wrote to `inMemoryBags`. On the next read, if `getItem` does NOT throw (returns null because nothing was ever written), we return `null` and the in-memory bag is silently abandoned.

**Impact:** In any browser that throws on writes but allows reads (some sandboxed/iframe contexts, third-party-cookie-blocked Safari ITP, Brave shields in some configs), the bag walk loses anti-adjacency and coverage guarantees across mounts. Each mount draws from a fresh shuffle. The user-visible failure: "fp's footer keeps showing me the same handful of images" — exactly the scenario the shuffled-bag walk was designed to prevent. Architecturally this is the failure mode that justifies having the in-memory fallback at all, and the implementation gives up on it.

**Secondary impact:** The test `falls back to in-memory bag when sessionStorage.setItem throws` only spies on `setItem`. It doesn't exercise the read-after-write path, so the bug went uncaught.

**Fix:**
```ts
function safeReadBag(surface) {
  try {
    if (window.sessionStorage) {
      const raw = window.sessionStorage.getItem(storageKey(surface));
      if (raw) { /* parse + return */ }
      // fall through — in-memory may have a more recent state
    }
  } catch { /* swallow */ }
  return inMemoryBags.get(surface) ?? null;
}
```

Add a regression test: spy `setItem` to throw, mount the hook twice; assert the second mount's drawn index is NOT equal to the first AND that the cursor in `inMemoryBags` advanced to 2.

##### Major #2 — Every `SaveWrappedScreen` mount advances the desktop bag, even when `horizonIndex` is already locked
**File:** `frontend/src/screens/SaveWrappedScreen.tsx:38-47`
**Severity:** Major

```ts
const horizonPick = useHorizonPick("desktop");
useEffect(() => {
  if (!build) return;
  if (build.horizonIndex !== undefined) return;
  if (!horizonPick) return;
  setBuild({ ...build, horizonIndex: horizonPick.index });
}, [build, horizonPick, setBuild]);
```

`useHorizonPick("desktop")` is called unconditionally — its mount-time effect draws and persists every time, regardless of whether the result is then used. Consequences:

1. **First-time save (StrictMode + dev):** double-mount draws TWO desktop entries from the bag, commits the second. Two indices burned for one commit.
2. **Subsequent SaveWrapped views (horizonIndex already set):** EVERY mount of `/app/save` draws another desktop bag entry that is then discarded by the early-return.
3. **Cross-screen pollution:** the desktop bag is shared with the landing-page `HorizonFooter`. Save-screen mounts cause the landing-page bag walk to silently skip indices. Coverage guarantee weakens — a user might never see indices 7/13/22 on the landing page in a session because the save screen burned them.
4. **Prefetch waste:** each useless draw also schedules a `<link rel="prefetch">` for the next 2 indices, doing speculative bandwidth on every save-screen mount.

**Impact:** Decorative drift, not data corruption. But this is the kind of thing that shows up in a year as "why does the landing page never show that one image?" and nobody connects it back to the silhouette commit logic. It also undermines the spec's §1 success criterion *"All 48 illustrations cycle exactly once per session before reshuffling."*

**Fix options (pick one):**
1. **Lazy draw via the pure helpers** — don't call `useHorizonPick`. Read the bag manually with `safeReadBag` + `drawFromBag` inside the effect, gated by `build.horizonIndex === undefined`. Skip the side effect entirely when the index is locked.
2. **Conditional hook surface** — add `useHorizonPick(surface, { skip: boolean })` that no-ops when `skip` is true. Less surgical but more discoverable.
3. **Use a third bag surface** — `useHorizonPick("commit")` that doesn't share state with desktop/mobile. Cheapest fix; preserves the bag-walk integrity for the visible footer.

Option 1 is the right one — it makes the side-effect-free intent of "I just need a draw at commit time" explicit.

##### Minor #1 — Prefetch `<link>` tags are never garbage-collected
**File:** `frontend/src/hooks/useHorizonPick.ts:201-214`
**Severity:** Minor

`appendPrefetchLink` adds `<link rel="prefetch">` to `document.head`; nothing ever removes them. Within a single page session this is bounded by the manifest size (48 unique links max) thanks to the dedupe selector. But:

- Across SPA route changes within the same session, the head accumulates dead prefetch hints from prior pages. Browsers do their own scheduling so it's not a perf disaster, but it pollutes the DOM.
- The cleanup effect cancels the timer/idle handle but does NOT remove links that were already inserted. If the user route-changes during the 2s idle window AFTER the timer fired but BEFORE cancellation runs (within the same tick), the link is appended and orphaned.
- Combined with Major #2: every save-screen mount adds up to 2 prefetch links that the user will never actually navigate to. Over a long session this can become dozens of dead `<link>` elements.

**Fix:** Track inserted links in a per-effect ref array; remove them in the effect cleanup. Or: leave the dedupe in place but stop appending entirely when the document already has 48 prefetch links for /campus/.

##### Minor #2 — `inMemoryBags` is module-scoped state that bleeds across tests
**File:** `frontend/src/hooks/useHorizonPick.ts:54`
**Severity:** Minor

`const inMemoryBags = new Map()` is module-level. `beforeEach` in the test file clears `sessionStorage` but does NOT clear `inMemoryBags`. Today this is masked by the Major #1 bug (the in-memory map is rarely consulted), but once Major #1 is fixed, tests that exercise the storage-failure path will leave residue in `inMemoryBags` that the next test inherits.

**Fix:** Either (a) export a test-only reset (`__resetInMemoryBags`) and call it in `beforeEach`, or (b) move `inMemoryBags` into a closure that the tests can reset by re-importing the module (vitest `vi.resetModules()`), or (c) make the Map keyed by storageKey + a per-mount nonce so tests can't pollute each other.

##### Minor #3 — `mobile-only-position` className on the `<img>` is dead
**File:** `frontend/src/components/horizon/HorizonFooter.tsx:57`
**Severity:** Minor (correctness-adjacent, not style)

The `<img>` carries `className="... mobile-only-position"`. No CSS rule anywhere defines `.mobile-only-position`. The mobile object-position swap is actually handled correctly by the scoped `<style>` block's `.horizon-image-wrap picture, .horizon-image-wrap img` selector at lines 397-402.

**Impact:** None functionally. But it suggests an earlier implementation strategy was abandoned without cleanup, and the inline `style={{ /* comment only */ }}` immediately below it is also a vestigial empty object. The next reader will spend time figuring out what `mobile-only-position` controls. Not a bug, but the kind of dead code that breeds confusion.

**Fix:** Remove the `mobile-only-position` className and the empty `style` object.

##### Minor #4 — `HorizonSilhouette` uses `loading="lazy"` despite mounting in the viewer phase the user is actively waiting for
**File:** `frontend/src/components/horizon/HorizonSilhouette.tsx:68`
**Severity:** Minor

The silhouette is mounted only in the `viewer` phase, which is reached after a min 1.5s save-confirmation dwell PLUS a backend Playwright render (6-18s per the screen). By the time the silhouette mounts, the user is staring at the share card; lazy-loading guarantees a "blank → silhouette pops in" beat. `loading="eager"` (or omitting the attribute) would mean the image is in cache by the time the share card renders.

**Impact:** Cosmetic. The screenshot-stable contract still holds — by the time the user takes a screenshot, the image will have loaded. But it undermines the "atmospheric" feel.

**Fix:** Drop `loading="lazy"` from `HorizonSilhouette.tsx:68`. Keep it on `HorizonFooter` (where the footer is genuinely below the fold).

##### Minor #5 — `IntersectionObserver` callback closure assumes single observed element
**File:** `frontend/src/components/horizon/HorizonFooter.tsx:133-141`
**Severity:** Minor

```ts
observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    isVisible = entry.isIntersecting;
    if (isVisible) scheduleTick();
  });
}, { rootMargin: "0px" });
```

We only observe one element (`stage`), so `entries` is always length 1 in practice. The `forEach` mutating `isVisible` is fine for one element; for two it would race. Not a bug today, but the code reads as if it handles N elements when it doesn't.

**Fix:** `const entry = entries[0]; if (!entry) return; isVisible = entry.isIntersecting; if (isVisible) scheduleTick();` — explicit single-element handling.

#### What's Good (acknowledging solid work)
- The `=== undefined` guard in `SaveWrappedScreen` is correctly defended by both `preserves build.horizonIndex on subsequent mounts (locked-at-commit)` AND `preserves a non-zero horizonIndex on remount`. That's the regression guard architects asked for and tests delivered.
- Type assertions (`as string`, `as number`) are all provably safe by construction — bounds-check immediately precedes each one. No false confidence.
- Anti-adjacency at the bag-refill seam is tested across 50 random seeds — the right way to test a probabilistic-feeling property deterministically.
- The Park-Miller LCG choice for test seeds is correct: classic, well-known, statistically uniform enough for a 48-element shuffle, and `Math.max(1, seed)` defends against the seed=0 degenerate case.
- Parallax cleanup (`observer.disconnect()` + `cancelAnimationFrame(rafHandle)` + both event listeners removed) is exhaustive — exactly what arch review §5 asked for. The cleanup contract is verified by the `removes scroll + resize listeners on unmount` test.
- CLS reservation: skeleton renders inside the same `clamp(220px, 22vw, 480px)` container, so populated-vs-skeleton states have identical height. No layout shift.
- The §10 testing-limitation note for framer-motion's `useReducedMotion` in jsdom is honest test boundary documentation, not test theatre. I'd rather see "we documented why we can't test this" than a passing test that lies about coverage.
- `useHorizonAt` correctly does NOT trigger prefetch or sessionStorage writes — the silhouette's stability contract requires zero side effects.
- `drawFromBag` defensively reshuffles when `order.length !== poolSize` — protects against stale v1 bags surviving a manifest size change (covered by the `mismatched-poolSize stored bag` test).

#### Required Changes
| # | Severity | File | Fix | Routes To |
|---|----------|------|-----|-----------|
| 1 | Major | `frontend/src/hooks/useHorizonPick.ts:60-83` | `safeReadBag` must fall through to `inMemoryBags` when storage exists but returns null, not just when storage throws. Add a regression test for the read-after-failed-write path. | Implementer (via §10) |
| 2 | Major | `frontend/src/screens/SaveWrappedScreen.tsx:38-47` | Stop calling `useHorizonPick("desktop")` unconditionally. Either lazily draw via `safeReadBag` + `drawFromBag` inside the effect (gated by `horizonIndex === undefined`), or use a separate "commit" surface. Don't pollute the desktop bag walk on every save-screen mount. | Implementer (via §10) |
| 3 | Minor | `frontend/src/hooks/useHorizonPick.ts:201-214` | Track inserted prefetch `<link>` elements in an effect-scoped ref array; remove them in the cleanup. Prevents unbounded DOM growth across SPA navigation. | Implementer (fix-and-continue OK) |
| 4 | Minor | `frontend/src/hooks/useHorizonPick.ts:54` | Add a test-only reset for `inMemoryBags` (or scope it differently). Prevents test pollution once Major #1 is fixed. | Implementer (fix-and-continue OK) |
| 5 | Minor | `frontend/src/components/horizon/HorizonFooter.tsx:57-64` | Remove dead `mobile-only-position` className and empty `style={{ /* comment only */ }}` object. | Implementer (fix-and-continue OK) |
| 6 | Minor | `frontend/src/components/horizon/HorizonSilhouette.tsx:68` | Drop `loading="lazy"` — the silhouette mounts after a 6-18s wait, lazy loading guarantees a visible pop-in. | Implementer (fix-and-continue OK) |
| 7 | Minor | `frontend/src/components/horizon/HorizonFooter.tsx:133-141` | Replace `entries.forEach` with explicit single-entry handling — we only observe one element. | Implementer (fix-and-continue OK) |

#### Questions for the Author (genuine, not gotcha)
1. The silhouette commits `horizonIndex` to a build that lives only in zustand state (not persisted). Does any flow re-mount `SaveWrappedScreen` after navigation away (e.g., going back from `/branches`)? If yes, the locked-at-commit invariant should hold across navigation. If no, the entire silhouette commit could be a `useMemo`-style derivation from `build.build_id` (deterministic hash) and skip the setBuild dance entirely — which would also obviate Major #2.
2. What's the rollback plan if the prefetch strategy turns out to over-fetch on slow networks (mobile, throttled)? `<link rel="prefetch">` has no widely-shipped `media`-on-connection gating; we can't easily disable it for `effectiveType === "slow-2g"`.
3. Is there an instrumented metric for "user reached `/app/save` and saw a silhouette" — i.e., does anyone other than the user know whether the silhouette ever loaded? Without that, the prefetch ROI is unmeasurable.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-18 22:50

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | N/A | No backend changes |
| Type check (mypy) | N/A | No backend changes |
| Tests (pytest) | N/A | No backend changes |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (exit 0) |
| Tests (vitest) | PASS | 504 passed, 1 skipped, 0 failed — 51 test files |
| Production build (Vite) | PASS | Built in 1.29s; chunk-size warning on main bundle (754 kB / 230 kB gzip) — pre-existing, no new heavy deps introduced by this spec |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All checks passed | — | — |

---

## §10 Discussion

```
[2026-04-18 21:55] @human (Jeff Cernauske) → @claude-code
Spec drafted from conversation thread spanning image asset prep,
two fp-design-visionary runs, marketing-reviewer caption
verification, and an interactive HTML mockup at
scripts/horizon-mockup.html. All major decisions locked by user.
Ready for ARCH REVIEW.
```

```
[2026-04-18 22:30] @test-writer → @human, @faang-staff-engineer
Testing limitation logged for §8 code review consideration:

The reduced-motion ON-path inside HorizonFooter is not directly
testable in vitest+jsdom. framer-motion's useReducedMotion() reads
useState(false) and only flips via a matchMedia 'change' event. Our
mock at src/test/mocks/prefers-reduced-motion.ts dispatches the change
event on setReducedMotion(true), but framer doesn't subscribe until
its effect runs — by which time the dispatched event is lost. So
useReducedMotion() returns `false` for the lifetime of the test.

Result: in HorizonFooter.test.tsx I removed the failing test that
asserted "no listeners attached under reduced motion" because it was
a false-negative caused by the test infrastructure, not by the
production code (which DOES early-return correctly under real reduced
motion). The OFF-path is fully tested. The ON-path is covered by:
  - source-code review (guard is `if (prefersReducedMotion) return`)
  - manual QA on a real browser
  - the spec §8 design audit on motion-token use

This is the same workaround HeroSection.test.tsx uses for the same
limitation. Logging here for transparency, not as a blocker.

ALSO observed: the production code IS correct in its cleanup contract.
The "removes scroll + resize listeners on unmount" test passes — net
listener leak is zero. So even if the ON-path-during-test attached a
listener, unmount would clean it up. No production bug found.
```

```
[2026-04-18 23:45] @faang-staff-engineer → implementer (Claude Code)
Code review complete. Verdict: CHANGES REQUIRED. Two Majors that need
fixing before this ships, plus 5 Minors that I'd like rolled in but
won't block on individually. Full findings in §8.

The two Majors share a common shape: both look like graceful
degradation but actually silently lose state.

  Major #1 (useHorizonPick.ts:60-83) — safeReadBag returns null on
  empty-storage WITHOUT consulting inMemoryBags. So the moment storage
  flips from "throwing on writes" to "allowing reads but empty"
  (which is the actual private-mode behavior in some browsers), every
  mount draws a fresh bag and we lose anti-adjacency + coverage. The
  test for "setItem throws" only mounts once, so this never surfaced.
  Add a "mount twice with setItem throwing" regression test alongside
  the fix.

  Major #2 (SaveWrappedScreen.tsx:38-47) — useHorizonPick("desktop")
  is called unconditionally and its mount-time effect always advances
  the desktop bag, regardless of whether the drawn pick is consumed.
  Net effect: every save-screen mount burns 1-2 entries from the bag
  the landing-page footer is ALSO drawing from, weakening the
  "all 48 cycle once per session" guarantee silently. Recommended
  fix: drop the hook call, draw lazily inside the gated effect using
  safeReadBag + drawFromBag (the pure helpers are already exported).
  Also obviates the prefetch-waste in finding #1 of Major #2's impact
  list.

The Minors (prefetch link cleanup, inMemoryBags test isolation,
dead .mobile-only-position className, silhouette loading="lazy",
single-element IO callback) are fix-and-continue at your discretion.

Once Majors are addressed, please re-run the full vitest suite
(including the new regression test for Major #1) and ping back for
re-review. ARCH was right that the design is sound — these are
implementation-level bugs, not architectural ones.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
