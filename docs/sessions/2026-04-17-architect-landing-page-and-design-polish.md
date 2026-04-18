# Session: Architect Review — landing-page-and-design-polish

| Field | Value |
|-------|-------|
| Session ID | 2026-04-17-architect-landing-page-and-design-polish |
| Timestamp | 2026-04-17 |
| Agent | @fp-architect |
| Spec | docs/specs/landing-page-and-design-polish.md |
| Step | 1 of 8 (ARCHITECTURE REVIEW) |
| Verdict | CHANGES REQUESTED |

## Actions Taken

1. Read the full spec in `docs/specs/landing-page-and-design-polish.md` (555 lines).
2. Updated spec top-level Status `DRAFT` → `ARCH REVIEW` and `Last Updated` in Metadata.
3. Traced the route cutover through the frontend codebase:
   - `frontend/src/App.tsx` — current root routes
   - `frontend/src/screens/LandingScreen.tsx` — in-app landing (moves to /app)
   - `frontend/src/screens/RevealScreen.tsx` — Stage 2 Reveal motion inspection
   - `frontend/src/styles/motion.ts` — `stage2Reveal` shared config
   - `frontend/tailwind.config.ts` — existing type scale tokens
   - `frontend/src/components/ui/AppHeader.tsx` — discovered pathname-based landing detection
   - `frontend/src/screens/PlaceholderScreen.tsx` — found hardcoded `to="/"` back link
   - `frontend/src/screens/{Menu,Profile,SchoolMajor}Screen.tsx` — found 3 hardcoded `navigate("/")` profile-guard redirects
   - `frontend/src/screens/{Landing,Reveal}Screen.test.tsx` — confirmed Authorized Test Modifications scope
4. Cross-referenced the 342/815 Karpathy row-count claim against `CLAUDE.md` (no longer tracks counts per commit 45dcb16), `reports/three-signal-ai-exposure-composite-2026-04-16.md` (815 confirmed), `domain/sources/karpathy_ai_exposure.yaml` and `LICENSE_SOURCES.md` (still reference 342 as raw source count).
5. Wrote findings into §5 of the spec under the `@fp-architect Review` subsection: 10 findings (1 sound category with 9 items, 9 concerns, 0 blockers), 8 conditions (6 required, 2 recommended).

## Decisions Made

**Verdict: CHANGES REQUESTED.** Route topology, component decomposition, pages/ vs. screens/ boundary, marketing-only type tokens, and zero-backend scoping are all architecturally sound. But the cutover from `/` → `/app` leaves four in-app navigation sites still pointing at `/` (which will silently redirect users to the marketing page), AppHeader uses `pathname === "/"` to identify landing mode and will leak in-app chrome onto the marketing surface, the Stage 2 Reveal beat table doesn't reconcile with the existing delays in `RevealScreen.tsx`, and Decision 3 ("in-app max stays at 48px") contradicts the spec's own tablet/desktop 56/64px sizes for the in-app LandingScreen.

Not a rejection — these are correctable without architectural rework. The required fixes are file-level updates and a clearer beat table. Once those land, the spec is ready for DESIGN VISION step.

## Key Findings

### Sound (9 items)
- Route topology and cutover plan
- `pages/` vs `screens/` boundary convention
- Component decomposition into `frontend/src/components/landing/*`
- Marketing type-scale tokens in tailwind.config.ts (not inline)
- `gradient-tagline` in-app only, preserved untouched
- Screenshot paths as props (decoupled from capture timing)
- SVG terminal over PNG (a11y + zoom)
- No pipeline / MCP / backend touches (correctly scoped)
- Testing Impact Analysis rigor
- Pre-existing ProfileScreen F1 failures correctly acknowledged

### Concerns (9 items)
1. **Four dead in-app `/` navigation sites** post-cutover (PlaceholderScreen, MenuScreen, ProfileScreen, SchoolMajorScreen) — REQUIRED FIX
2. **AppHeader `isLanding = pathname === "/"`** — will leak in-app header onto marketing, or lose header affordances on new `/app` — REQUIRED FIX
3. **Stage 2 Reveal beat table** — "~1.4s total current" claim is inaccurate (actual ~3.4s), beats don't map cleanly to existing delays — REQUIRED FIX
4. **Decision 3 contradicts §1/§4 sizes** — "in-app max 48px" vs. text-[56px]/text-[64px] — REQUIRED FIX
5. **Karpathy 342 vs 815 reconciliation** — doc cleanup followup, not a blocker
6. **Screenshot asset format** — PNG at 1920×1200 endangers Lighthouse ≥95 — recommended WebP fix
7. **`prefers-reduced-motion` pattern unspecified** — prescribe `useReducedMotion()` from Framer Motion — REQUIRED FIX
8. **Ollama claim scoping** — §10 flagged correctly; architect re-reviews in step 2 once Design Visionary fills §3 — REQUIRED HAND-OFF
9. **Plush-laptop fallback** — clean Decision 10, no action needed

### Blockers
None.

## Artifacts Produced

- `docs/specs/landing-page-and-design-polish.md` — §5 @fp-architect Review populated, top-level Status updated to `ARCH REVIEW`, Metadata `Last Updated` revised.

## Next Step

Because verdict is CHANGES REQUESTED, next step is escalation to the human per the Claude Code Prompt. The spec does NOT advance to DESIGN VISION until the 6 required conditions in §5 Conditions are addressed.
