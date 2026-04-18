# Feature: Landing Page + Design Polish (The Constellation)

## Claude Code Prompt

```
Read the spec at docs/specs/landing-page-and-design-polish.md in its entirety.
Also read reports/design-vision-2026-04-17.md — it is the source material for §3.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 (route changes, component boundaries, React Router migration, build/bundle impact, asset delivery, prefers-reduced-motion handling)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes)
   - Writes findings to §5
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to formalize §3 by copying the per-section specs from reports/design-vision-2026-04-17.md §2 into this spec, validated against DESIGN.md.
   - §3 becomes the pixel-perfect implementation target.
   - The vision is already drafted in the source report. This step is ratification + any deltas the visionary wants to tighten.

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code.
   - Implement landing sections A–I as new components under frontend/src/components/landing/.
   - Move in-app LandingScreen from "/" to "/app" (or chosen alternate) and wire marketing Landing to "/".
   - Apply the 3 in-app polish items exactly as specified in §4.
   - Use Brightpath design tokens exclusively — no hardcoded colors, spacing, or typography. New marketing-only type scale goes in tailwind.config.ts per §4.
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer
   - Component tests for each landing section (render, copy, accessibility identifiers, motion-reduced variant)
   - Route test confirming "/" renders Marketing Landing, "/app" renders in-app LandingScreen
   - Update the two existing at-risk tests per §4 Authorized Test Modifications

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for Brightpath token compliance across all new components
   - Confirm: zero hardcoded colors/spacing/fonts, new marketing type tokens applied correctly, prefers-reduced-motion respected, mobile responsive, 16 anti-patterns from §2 absent
   - Writes findings to §8

6. CODE REVIEW
   - Invoke @faang-staff-engineer for implementation + tests
   - Writes findings to §8
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Lighthouse audit against staging deploy — record scores in §9
   - Log results to §9

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/landing-page-and-design-polish-YYYY-MM-DD.md
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary formalizing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build + Lighthouse |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-17 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-17 |
| Blocked By | **Week-1 voice fixes from `reports/hackathon-ship-plan-2026-04-17.md`** — screenshot capture (§4.2 of design report) depends on voice-compliant Gemma output + in-app vocabulary fixes. Do not begin the week-2 screenshot capture phase of this spec until the ship plan's P0 copy items have landed. |
| Related Specs | `docs/specs/completed/screen-career-pick-reveal.md` (owns RevealScreen.tsx), `docs/specs/completed/screen-landing-profile.md` (owns in-app LandingScreen.tsx), `docs/specs/completed/feature-project-scaffolding.md` (app routing/chrome) |

---

## §1 Feature Description

### Overview

Ship the public marketing landing page ("The Constellation") as a new route in the existing frontend React app, plus two targeted in-app polish changes that raise the cinematic ceiling of the demo video. One Full-weight pipeline, one deliverable surface, one asset (plush-laptop illustration) with a documented fallback.

### Problem Statement

FutureProof has no marketing landing page. The hackathon submission (Gemma 4 Good, deadline 2026-05-18) will direct Kaggle judges, press, and students somewhere when they want to learn what this is before touching the live app. Today that "somewhere" doesn't exist. The in-app LandingScreen is the first screen of the app, not a marketing surface.

Three secondary problems:

1. **In-app LandingScreen feels small** compared to what the marketing surface will present — 28px/40px headline against the marketing surface's 96px reads as a summary, not a landing. Demo video cuts look weak.
2. **Stage 2 Reveal motion is rushed** — 1.4s rapid-fire, no breath between beats. The signature moment of the product reads as hurried in recorded video.
3. **No screenshot capture convention exists** — week 2 of the ship plan captures 6 hero shots for landing/Kaggle/video, but without composition rules they read as casual product stills instead of intentional marketing assets.

This spec fixes all four problems in one coordinated pass, gated on the week-1 voice fixes landing clean.

### Success Criteria

- [ ] Marketing Landing page accessible at route `/` on staging deploy
- [ ] In-app LandingScreen moves to `/app` (or chosen alternate) with all existing flows intact — no dead links from elsewhere in the app
- [ ] All 9 landing sections (A–I) implemented per §3 using only Brightpath tokens and the two new marketing-scale tokens declared in §4
- [ ] Zero hardcoded colors, spacing, or typography values in any new component (enforced by @fp-design-auditor)
- [ ] Mobile-responsive across all sections at 375px viewport minimum — cards stack, split layouts collapse, type scales drop
- [ ] `prefers-reduced-motion` respected on every landing animation (twinkle, ambient-breathe, reveals, hover states)
- [ ] In-app `LandingScreen.tsx` headline bumped to `text-hero` (48px) / `text-[56px]` tablet / `text-[64px]` desktop; `gradient-tagline` treatment preserved
- [ ] Stage 2 Reveal sequence in `RevealScreen.tsx` retimed to 3.7s total per §4 sequence spec; demo capture shows cinematic pacing
- [ ] 6 hero screenshots captured per §3.4 composition rules (Reveal, Gauntlet reroll, Branch Tree, Receipt panel, Wrapped frame, Compare view)
- [ ] Plush-laptop illustration produced OR fallback decision made and Section E treatment adjusted accordingly
- [ ] Lighthouse scores ≥95 on Performance, Accessibility, Best Practices, SEO on the production build of the landing page
- [ ] Zero reference to the 16 named hackathon visual anti-patterns in §2
- [ ] All tests pass (frontend vitest, backend pytest untouched)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Landing page lives as a new React route at `/` inside the existing frontend app; in-app LandingScreen moves to `/app` | One Vite build, one deploy, one design system. Matches "The Constellation" thesis that marketing and product are the same night sky. | (a) Separate `frontend-landing/` Vite project — doubles deploy surface, weakens coherence story. (b) Next.js subproject for SEO — new framework, 4-week runway can't absorb the learning cost. |
| 2 | One combined spec for landing + in-app polish + screenshots + asset work | All four items are gated on the same week-1 voice fixes and share the same 4-week calendar. Splitting multiplies coordination cost. | Split into `landing-page-marketing.md` + `in-app-design-polish.md`. Adds two ARCH REVIEWs and two VERIFICATIONs for work that trivially fits in one. |
| 3 | New marketing-only type scale (`text-marketing-hero` 96px, `text-marketing-section` 64px) extends DESIGN.md rather than replaces `text-hero` | In-app max stays at 48px. Marketing gets billboard scale. Post-hackathon, fold into DESIGN.md under a "Marketing Surface Tokens" section. | (a) Raise in-app `text-hero` to 96px — breaks in-app hierarchy. (b) Inline 96px as a one-off — violates token discipline. |
| 4 | `gradient-tagline` treatment is **in-app only**, removed from marketing hero | A gradient headline at 96px reads as noisy; at 48px (in-app) reads warm. Size changes what a gradient does. | Apply `gradient-tagline` to both surfaces — marketing hero loses impact. |
| 5 | Marketing `Start ✦` CTA opens the live app in a new tab (Option A) | Judge can A/B compare landing and app by tabbing. No custom transition to engineer. P2 work we can afford to cut. | (b) Same-tab navigation with fade-through-black — 600ms motion that's easy to get wrong. |
| 6 | Hero is still, not cinematic — one image (PentagonGlow 320px + 7s drift), one headline, one button | Three seconds of judge attention held by stillness. Matches voice guide "brevity is the flex." | Scroll-jacked cinematic hero with 3D pentagon + particle burst — hackathon trope, motion-over-substance. |
| 7 | Terminal in Section E is SVG, not PNG | Real text, copy-pasteable, zoomable, no "looks fake" risk | PNG screenshot of iTerm2 — resolution-bound, less credible, harder to iterate |
| 8 | Ollama claim deliberately scoped to deployment: "when a school runs FutureProof on Ollama, no student data leaves the building" | Per ship plan §6 risk 2, the live cloud demo runs OpenRouter. Landing must not overclaim. | "No student data leaves the building" unscoped — would contradict the cloud-demo architecture |
| 9 | Branch Tree capture convention is documented in §4.2 but **is not code** | It's a composition rule applied at screenshot time, not a render change. Keeping it as code would waste cycles. | Add a `?demo=true` URL flag that composes the tree for capture — unnecessary engineering |
| 10 | If plush-laptop illustration can't be delivered in ≤4 hours, fall back to extending the terminal full-width | Asset work is the only new illustration in scope. An off-brand stock laptop is worse than no laptop. | Ship with whatever illustration we can find — brand dilution |

### Constraints

**Technical:**
- React Router already mounted via `BrowserRouter`. Adding a route is mechanical.
- PentagonGlow component already ships and is reused, not reimplemented.
- No new runtime dependencies. No SSR. No Next.js.
- Prerendering / SSG not in scope — CSR is adequate for Lighthouse targets on a simple page.
- Assets served from `frontend/public/` via Vite's static handling.

**Business / schedule:**
- Hard deadline: 2026-05-18 (hackathon submission).
- Runway: 4 weeks, 1 day as of 2026-04-17.
- Week-1 voice fixes block week-2 screenshot capture. Do not capture screenshots against a voice-non-compliant app.
- Design auditor (@fp-design-auditor) must approve before screenshots are captured — captures compound any uncaught token drift.

**Scope constraints (Out of Scope):**
- **Kaggle writeup, demo video production, social launch cards** — tracked in `reports/hackathon-ship-plan-2026-04-17.md`, not this spec. This spec produces the landing page the video ends on and the screenshots the Kaggle gallery uses; it does not produce the video or the writeup.
- **Domain acquisition / DNS / TLS** — tracked as open question Q1 in the ship plan; spec assumes staging deploy (futureproof-staging.example or similar) works.
- **Analytics / marketing instrumentation** — no GA4, no Segment, no pixel trackers. Out of scope for hackathon.
- **Newsletter / waitlist form** — PRD §Does Not Ship.
- **Localization / i18n** — English only.
- **Server-side rendering** — Vite CSR is sufficient for judging.
- **Blog / content pages beyond the single landing page** — scope creep.
- **`/api/landing` endpoint or any backend change** — landing is static content, no backend touches.
- **Mobile native app** — PRD §Does Not Ship.
- **Voice fixes from the copywriter audit** — owned by the ship plan's week-1 sprint, this spec depends on them but doesn't include them.

---

## §3 UI/UX Design

> @fp-design-visionary formalizes this section in step 2 of the Claude Code Prompt.
>
> **Source of truth:** `reports/design-vision-2026-04-17.md` §2 (landing sections A–I with ASCII wireframes and token tables), §3 (in-app polish specs), §4 (screenshots strategy), §5 (visual coherence plan), §6 (anti-patterns), §7 (extensions flagged).
>
> When the visionary fills this section, copy the per-section ASCII wireframes and token tables verbatim from the report and validate each line against `DESIGN.md`. Flag any token that doesn't exist in DESIGN.md as an explicit extension per §7 of the report.

### Sections in Scope

- **Section A** — Above the fold (hero). PentagonGlow 320px + 96px headline + single CTA + data footer. Source: design report §2.2.
- **Section B** — The Problem. Typography-only, centered. Source: §2.3.
- **Section C** — How It Works. Three-card grid with hero screenshots. Source: §2.4.
- **Section D** — Receipts Story. 7-col typography / 5-col screenshot split. Source: §2.5.
- **Section E** — Run It Yourself (Ollama). Three-column terminal / text / laptop. Source: §2.6.
- **Section F** — Live Demo / CTA Rail. Centered, narrow, mirror of hero CTA. Source: §2.7.
- **Section G** — Data Sources. 7-row dataset table as receipt panel. Source: §2.8.
- **Section H** — Team / About. Centered paragraph, no image. Source: §2.9.
- **Section I** — Footer. Wordmark + nav + disclaimer + data-line repeat. Source: §2.10.

### In-App Polish Specs (Detailed in §4 below)

1. In-app LandingScreen headline size bump.
2. Stage 2 Reveal motion sequence retime.
3. Branch Tree screenshot capture convention (documentation only, no code change).

### Brightpath Token Usage

All sections use existing DESIGN.md tokens except the two new marketing-scale tokens introduced in §4. The visionary must name every token used per section in the token table.

### Libraries

- **PentagonGlow** (existing in-app component, reused)
- **Framer Motion** for `whileInView` reveals, springs, stagger
- **React Router** for the new route
- **shadcn/ui** not needed — landing is typography + cards + one table, composed directly

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Hero CTA | `landing-hero-cta` | button (link wrapped) | "Start your first FutureProof build" |
| Hero secondary link | `landing-hero-demo-link` | link | "Watch the 3-minute demo" |
| Section C card 1 | `landing-how-stats-card` | article | (visible heading) |
| Section C card 2 | `landing-how-gauntlet-card` | article | (visible heading) |
| Section C card 3 | `landing-how-branches-card` | article | (visible heading) |
| Section D screenshot | `landing-receipts-screenshot` | img | "Expanded stat receipt panel showing raw inputs, thresholds, and source datasets" |
| Section E terminal | `landing-ollama-terminal` | figure | "Terminal showing ollama pull gemma4:e4b and local launch commands" |
| Section E laptop illustration (or fallback) | `landing-ollama-laptop` | img | "Laptop displaying FutureProof's pentagon constellation" |
| Section F CTA | `landing-cta-rail` | button (link wrapped) | "Start your first FutureProof build" |
| Section G row (per dataset) | `landing-data-row-{source}` | row | (visible content) |
| Footer nav items | `landing-footer-{name}` | link | (visible label) |

Reduced motion variants must be tested for every `whileInView` reveal, the hero drift, twinkle field, ambient breathe, and card hover elevations.

---

## §4 Technical Specification

### Architecture Overview

Landing page is a new top-level route `/` rendered by a new page component `frontend/src/pages/Landing.tsx` (new `pages/` directory — first use, chosen to semantically distinguish marketing-surface composition from in-app `screens/` flow). Page composes 9 section components under `frontend/src/components/landing/` (directory already exists with `PentagonGlow.tsx` and `PentagonGlow.test.tsx`). In-app LandingScreen route moves from `/` to `/app`. All other in-app routes remain unchanged.

Two in-app polish changes are surgical edits to existing components: `frontend/src/screens/LandingScreen.tsx` (headline type scale) and `frontend/src/screens/RevealScreen.tsx` (Stage 2 Reveal motion timing).

New marketing-only typography tokens are added to `frontend/tailwind.config.ts`. The existing `frontend/src/index.css` `gradient-tagline` utility is untouched — it remains in-app-only by discipline (not by technical constraint).

Plush-laptop illustration lives in `frontend/public/assets/` if produced; otherwise Section E terminal extends full-width per the fallback decision.

No backend changes. No new API endpoints. No Pydantic models. No data-pipeline changes. No MCP changes.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/App.tsx` | Modify | Replace `"/"` → `<LandingScreen />` with `"/"` → `<Landing />` (new) and `"/app"` → `<LandingScreen />` (in-app landing). |
| `frontend/src/pages/Landing.tsx` | Create | Marketing landing page component. Composes the 9 section components. No logic — only layout and scroll context. |
| `frontend/src/components/landing/HeroSection.tsx` | Create | Section A per §3. PentagonGlow 320px + 96px headline + CTA + data footer. |
| `frontend/src/components/landing/ProblemSection.tsx` | Create | Section B per §3. Typography-only, centered 8-col. Two inline typographic receipts (`text-accent-insight`, `text-accent-alert`). |
| `frontend/src/components/landing/HowItWorksSection.tsx` | Create | Section C per §3. Three-card grid, screenshot slots. Accepts screenshot image paths as props (decoupled for easy re-capture). |
| `frontend/src/components/landing/ReceiptsSection.tsx` | Create | Section D per §3. 7/5 split, screenshot right with `shadow-glow-insight` radial glow behind. |
| `frontend/src/components/landing/OllamaSection.tsx` | Create | Section E per §3. Three-column: SVG terminal / text / laptop illustration (or fallback). |
| `frontend/src/components/landing/TerminalSVG.tsx` | Create | Inline SVG terminal with typing animation (opt-in, respects `prefers-reduced-motion`). |
| `frontend/src/components/landing/CTARailSection.tsx` | Create | Section F per §3. Centered narrow, mirrors hero CTA. |
| `frontend/src/components/landing/DataSourcesSection.tsx` | Create | Section G per §3. 7-row dataset table styled as receipt panel. |
| `frontend/src/components/landing/TeamSection.tsx` | Create | Section H per §3. Centered paragraph, inline links. |
| `frontend/src/components/landing/LandingFooter.tsx` | Create | Section I per §3. Wordmark + 2 nav rows + disclaimer + data-line echo. |
| `frontend/src/components/landing/HeroSection.test.tsx` | Create | Component test: renders headline, CTA, data footer; passes axe check; reduced-motion variant tested. |
| `frontend/src/components/landing/ProblemSection.test.tsx` | Create | Component test: renders all paragraphs, typographic receipts are inline spans, axe check. |
| `frontend/src/components/landing/HowItWorksSection.test.tsx` | Create | Component test: renders three cards, each with caption/heading/body; passes axe check. |
| `frontend/src/components/landing/ReceiptsSection.test.tsx` | Create | Component test: renders split layout, screenshot alt text present. |
| `frontend/src/components/landing/OllamaSection.test.tsx` | Create | Component test: terminal + text + laptop (or fallback), terminal commands copy-pasteable, axe. |
| `frontend/src/components/landing/DataSourcesSection.test.tsx` | Create | Component test: 7 rows rendered with correct counts from §4 Content Ground Truth. |
| `frontend/src/components/landing/LandingFooter.test.tsx` | Create | Component test: all links render with correct hrefs, disclaimer text matches voice guide. |
| `frontend/src/pages/Landing.test.tsx` | Create | Page-level test: renders all 9 sections in order, scroll-linked motion doesn't throw, `prefers-reduced-motion` variant tested. |
| `frontend/src/App.test.tsx` | Create | Route test: `/` renders Marketing `Landing`, `/app` renders in-app `LandingScreen`. (New file — no App-level test exists today.) |
| `frontend/src/screens/LandingScreen.tsx` | Modify | Bump headline size: `text-hero` mobile / `text-[56px]` tablet / `text-[64px]` desktop. Keep `gradient-tagline` span on "starting position." |
| `frontend/src/screens/LandingScreen.test.tsx` | Modify | Update size assertion to reflect new headline tokens. **Authorized** — see §4 Authorized Test Modifications. |
| `frontend/src/screens/RevealScreen.tsx` | Modify | Retime Stage 2 Reveal to 3.7s total per the sequence spec below. |
| `frontend/src/screens/RevealScreen.test.tsx` | Modify | Update any motion-timing assertions to match the new 3.7s sequence. **Authorized.** |
| `frontend/tailwind.config.ts` | Modify | Add `text-marketing-hero` (96px / 72px / 48px responsive) and `text-marketing-section` (64px / 56px / 40px responsive) type scales. |
| `frontend/src/index.css` | Modify | If any new utility classes are needed for marketing-only treatments, add them under a `/* Marketing surface */` comment. Do NOT modify `gradient-tagline`. |
| `frontend/public/assets/plush-laptop.svg` | Create | New illustration asset for Section E. If production slips past 4 hours, this file is not created and Section E falls back per §2 Decision 10. |
| `frontend/public/assets/screenshots/landing/` | Create (directory) | Container for the 6 hero screenshots captured in week 2. Filenames: `01-reveal.png`, `02-gauntlet-reroll.png`, `03-branch-tree.png`, `04-receipt-panel.png`, `05-wrapped-frame.png`, `06-compare-view.png`. Produced outside code review but referenced by the landing components. |

### Content Ground Truth (Data Sources Table — Section G)

Rows ordered as in the design report §2.8:

| SOURCE | ROWS | POWERS |
|--------|-----:|--------|
| College Scorecard (Field of Study) | 69,947 | ERN, ROI, Loans |
| BLS Occupational Outlook | 832 | Growth, Ceiling |
| O*NET Task & Work Context | 798 | HMN, Burnout |
| Karpathy AI Exposure | 815 | RES, Fight AI |
| Anthropic Economic Index | 587 | AI velocity |
| BEA Regional Price Parities | 51 | Geo adjustment |
| CIP-SOC Crosswalk | 626,406 | The core query |

**Note:** Karpathy count is **815** per `docs/specs/completed/three-signal-ai-exposure-composite-v3.md`, not the 342 / 389 figures in stale CLAUDE.md / PRD. This spec uses **815**. Ship-plan P0 item "fix stale row counts in CLAUDE.md / PRD" is a precondition for landing copy review; if CLAUDE.md still says 342 when this spec reaches ARCH REVIEW, flag the divergence and cite `three-signal-ai-exposure-composite-v3.md` as the authoritative source.

Dataset count is **7**, not 6, since Anthropic Economic Index is shipped (`docs/specs/completed/ingest-anthropic-economic-index.md`). The hero's "7 public datasets" line and the footer's data-line echo both reflect this.

### Stage 2 Reveal Motion Sequence (In-App Polish §3.2)

Current sequence in `frontend/src/screens/RevealScreen.tsx` + related motion configs. Total duration ~1.4s. Target: **3.7s total** with two new "breath" holds.

```
Beat  | t=     | Duration | What                          | Motion
------+--------+----------+-------------------------------+-------------------------
1     | 0.0s   | 0.8s     | Glow pulse                    | springs.gentle
2     | 0.5s   | 0.6s     | Bear reveal                   | springs.bouncy
3     | 1.1s   | 0.4s     | HOLD — ambient breathe only   | (none — passive)
4     | 1.5s   | 0.6s     | Pentagon draw (axes stagger)  | springs.smooth, 100ms stagger
5     | 2.1s   | 0.3s     | HOLD — pentagon at rest       | (none — passive)
6     | 2.4s   | 0.5s     | Title reveal                  | springs.smooth, y:16→0 fade
7     | 2.5s   | 0.8s/ea  | Stat numbers count up         | 80ms stagger per stat
END   | 3.7s   |          |                               |
```

The two holds (beats 3 and 5) are the critical delta. Existing beats keep their springs; only the delays between them extend. Implement by updating the Framer Motion `variants` or keyframe definitions in `RevealScreen.tsx` (and any shared motion config the component imports — audit the imports as part of implementation).

### Data Model Changes

None. Static content only.

### Service Changes

None. Landing is pure React + static assets.

### Testing Impact Analysis

> Before finalizing, I searched `frontend/src/screens/*.test.tsx` and `frontend/src/components/landing/` for existing tests. Two existing screen tests will need updates; everything else is new.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/LandingScreen.test.tsx` | Any test asserting specific headline size classes (e.g., `text-heading`, `text-title`) | High | Headline size bump changes the class tokens from `text-heading tablet:text-title` to `text-hero tablet:text-[56px] desktop:text-[64px]`. Any snapshot or className assertion will break. |
| `frontend/src/screens/RevealScreen.test.tsx` | Any test asserting Stage 2 Reveal timing (delays, durations) | High | Motion retime changes delays and introduces two new beats. Tests that assert specific `transition.delay` values or component-visible timestamps will break. |
| `frontend/src/App.test.tsx` (if exists — audit in ARCH REVIEW) | Route rendering | High | Moving in-app LandingScreen from `/` to `/app` changes route behavior. No App-level test exists today, so this becomes **New Tests Required** rather than at-risk. |
| `frontend/src/screens/ProfileScreen.test.tsx` | 2 known pre-existing failures (F1 spec) | Low | Unrelated to this spec. Do not touch. Document as pre-existing in §9 Verification. |
| `frontend/src/components/landing/PentagonGlow.test.tsx` | PentagonGlow render behavior | Low | Reuse adds no new assertions against the component itself. Should stay green. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/screens/LandingScreen.test.tsx` | Update headline className / size assertions to match the new `text-hero tablet:text-[56px] desktop:text-[64px]` token chain | Headline size bump is a spec-sanctioned change |
| `frontend/src/screens/RevealScreen.test.tsx` | Update Stage 2 Reveal motion timing assertions to match the 3.7s total sequence (beats 1–7 per §4) | Motion retime is a spec-sanctioned change |

Any test failure outside these two files halts implementation per agent-delegation rules.

#### Confirmed Safe

Must NOT break. If they do, STOP and escalate:

- `frontend/src/components/landing/PentagonGlow.test.tsx` — component is reused, not modified
- `frontend/src/screens/SchoolMajorScreen.test.tsx`, `CareerPickScreen.test.tsx`, `GauntletScreen.test.tsx`, `BranchTreeScreen.test.tsx`, `MenuScreen.test.tsx`, `SaveWrappedScreen.test.tsx` — not touched by this spec
- All backend tests under `backend/tests/` — this spec doesn't touch backend
- All pipeline tests under `tests/` — this spec doesn't touch the data pipeline

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `frontend/src/pages/Landing.test.tsx` | `renders all 9 sections in order` | DOM contains a hero, problem, how-it-works, receipts, ollama, cta-rail, data-sources, team, footer in that order |
| P0 | `frontend/src/App.test.tsx` | `marketing Landing is rendered at /` | React Router resolves `/` to `<Landing />` |
| P0 | `frontend/src/App.test.tsx` | `in-app LandingScreen is rendered at /app` | React Router resolves `/app` to `<LandingScreen />` |
| P0 | `frontend/src/components/landing/HeroSection.test.tsx` | `renders headline, CTA, and data footer` | All three critical elements render with expected copy |
| P0 | `frontend/src/components/landing/HeroSection.test.tsx` | `CTA has correct aria-label and href to /app` | Accessibility + destination correct |
| P0 | `frontend/src/components/landing/DataSourcesSection.test.tsx` | `renders 7 dataset rows with correct counts` | Verifies 69,947 / 832 / 798 / 815 / 587 / 51 / 626,406 — catches future count drift |
| P0 | `frontend/src/components/landing/OllamaSection.test.tsx` | `terminal commands are real text, not images` | SVG terminal contains actual text nodes for `ollama pull gemma4:e4b` and `INFERENCE_BACKEND=ollama` |
| P1 | `frontend/src/components/landing/HeroSection.test.tsx` | `respects prefers-reduced-motion` | Pentagon drift + twinkle field pause when media query matches |
| P1 | `frontend/src/components/landing/HowItWorksSection.test.tsx` | `renders three cards with captions, headings, bodies` | Structure and copy correct |
| P1 | `frontend/src/components/landing/ReceiptsSection.test.tsx` | `screenshot has descriptive alt text` | Accessibility |
| P1 | `frontend/src/components/landing/ProblemSection.test.tsx` | `inline typographic receipts use correct accent tokens` | Voice-guide receipts discipline |
| P1 | `frontend/src/components/landing/LandingFooter.test.tsx` | `all footer links have correct hrefs` | Kaggle / GitHub / Brightsmith / Video links resolve |
| P2 | `frontend/src/pages/Landing.test.tsx` | `axe accessibility check passes with zero violations` | Lighthouse a11y target ≥95 |
| P2 | `frontend/src/components/landing/OllamaSection.test.tsx` | `falls back gracefully when plush-laptop asset is missing` | Per §2 Decision 10 |

#### Test Data Requirements

- `frontend/src/test/mocks/landing-screenshots/` — six placeholder PNGs (or use actual captured screenshots if Week 2 capture is complete before tests run). Placeholders document the dimensions expected.
- `prefers-reduced-motion` media query mock via `matchMedia` — standard vitest pattern, reuse from existing screen tests.

### Screenshot Capture (Week 2 — Operational, Not Code)

The six hero screenshots are captured per `reports/design-vision-2026-04-17.md` §4.2, using the composition rules in §4.1. Captures happen **after** week-1 voice fixes ship and **after** @fp-design-auditor approves the landing components.

Capture checklist (tracked as §1 Success Criteria):

1. Shot 1 — Reveal (Stanford CS, All-in, 100% loans)
2. Shot 2 — Gauntlet mid-reroll (Illinois State Marketing, Fight AI, skill equipped)
3. Shot 3 — Branch Tree (Indiana University Bloomington Marketing, all endpoints lit) — **2-3 attempts**
4. Shot 4 — Receipt panel (ISU Financial Analyst, ROI expanded)
5. Shot 5 — Wrapped frame (stats frame from any clean build, Stanford CS recommended)
6. Shot 6 — Compare view (Stanford CS vs Millikin Drama)

Composition rules verbatim from design report §4.1: no device chrome, 16:10 or 9:16 aspect, `rounded-xl` corners, 1px `border-subtle`, `shadow-lg` in post, 2560×1600 retina capture → 1920×1200 web, no cursor, glow preservation with 40–60px breathing room, Chrome at 1440×900, deterministic seed data.

### Gemma-Touching Work

None. This spec does not touch `gemma_client.generate` or `gemma_client.generate_chat`. Landing is static.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline/data changes)

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §3/§4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest |  |  |  |  |
| vitest |  |  |  |  |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** PENDING
#### Findings
[Filled in by @fp-design-auditor — Brightpath token compliance, new marketing-scale token correctness, prefers-reduced-motion coverage, mobile responsiveness, zero occurrence of the 16 anti-patterns in §2]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] BLOCKER

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — security, performance, error handling, architecture, test quality]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) |  |
| Type check (mypy) |  |
| Tests (pytest) |  |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript (`tsc --noEmit`) |  |
| Tests (vitest) |  |
| Production build (Vite) |  |

### Lighthouse (Production build on staging)
| Category | Score | Target |
|----------|------:|-------:|
| Performance |  | ≥95 |
| Accessibility |  | ≥95 |
| Best Practices |  | ≥95 |
| SEO |  | ≥95 |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[Spec draft complete 2026-04-17 — Claude Code → Jeff]
Drafted from reports/design-vision-2026-04-17.md (design report, source of truth for §3)
with cross-references to reports/hackathon-ship-plan-2026-04-17.md (week-1 voice fixes
as blocking precondition), reports/marketing-landing-scope-2026-04-17.md (copy ground
truth for all 9 sections), and reports/in-app-copy-audit-2026-04-17.md (voice-guide
compliance inputs).

Three items worth calling out before ARCH REVIEW:

1. The 815-count claim for Karpathy AI Exposure conflicts with CLAUDE.md (342) and the
   PRD (389). three-signal-ai-exposure-composite-v3.md in completed/ is authoritative.
   Ship plan P0 includes fixing the stale counts; if that hasn't landed before ARCH
   REVIEW, architect should flag it.

2. The Ollama claim "no student data leaves the building" is deliberately scoped to
   deployment mode in §2 Decision 8. Architect should verify the landing copy in §3
   (once formalized by the visionary) stays scoped — this is the single most
   overclaim-prone line on the page.

3. The plush-laptop asset (§4) has a §2 Decision 10 fallback but creates a real Week
   2 Thursday decision point. If Week 1 delivers a clear yes/no on this, Week 2 avoids
   scramble.
```

---

## §11 Final Notes

**Human Review:** PENDING

**Dependencies:** This spec is blocked by the week-1 voice sprint from `reports/hackathon-ship-plan-2026-04-17.md`. Do NOT start ARCH REVIEW until the ship plan's P0 in-app vocabulary fixes have landed and the Gemma system prompts have been rewritten. Capturing screenshots (§4) against a voice-non-compliant app is a waste.

**Follow-ups to new specs (not this one):**
- Video production spec (3-minute demo) — ship plan week 3.
- Kaggle writeup spec — ship plan week 3.
- Social launch card spec — ship plan week 4.
- Domain / deployment spec — depends on ship-plan open question Q1.

**Post-hackathon:**
- Fold `text-marketing-hero` and `text-marketing-section` into DESIGN.md under "Marketing Surface Tokens" section.
- Promote landing page from `/` to a dedicated marketing domain if traffic warrants.
- Revisit the Option B (same-tab fade-through-black) transition as a polish item if the marketing surface continues.
