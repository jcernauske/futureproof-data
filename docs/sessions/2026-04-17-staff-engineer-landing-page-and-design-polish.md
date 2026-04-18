# Session: Staff Engineer Code Review — landing-page-and-design-polish

**Session ID:** 2026-04-17-staff-engineer-landing-page-and-design-polish
**Timestamp:** 2026-04-17
**Agent:** @faang-staff-engineer
**Spec:** `docs/specs/landing-page-and-design-polish.md` (Step 6: CODE REVIEW)

## Scope

Reviewed the Phase 1–3 implementation + 48-test Phase 4 coverage for the marketing
landing page (9 sections), the `App.tsx` router split, the `AppHeader` marketing
early-return refactor, the RevealScreen delay retime, and the four profile-guard
redirect updates. Focus: security, performance, error-handling, architecture,
test integrity. Ignored style/formatting (covered by @fp-design-auditor in Step 5).

## Files Reviewed

- `frontend/src/App.tsx` (router split + AppRoutes export)
- `frontend/src/App.test.tsx`
- `frontend/src/pages/Landing.tsx` + `Landing.test.tsx`
- `frontend/src/components/landing/` — all 9 sections + TerminalSVG + tests
- `frontend/src/components/ui/AppHeader.tsx` (isMarketing early-return)
- `frontend/src/screens/RevealScreen.tsx` (delay retime)
- `frontend/src/screens/LandingScreen.tsx` (headline token chain)
- `frontend/src/screens/{Menu,Profile,SchoolMajor,Placeholder}Screen.tsx` (/app redirects)
- `frontend/src/test/mocks/prefers-reduced-motion.ts`
- `frontend/src/test-setup.ts` (IntersectionObserver stub)
- `frontend/tailwind.config.ts` (4 new fontSize tokens)
- `frontend/src/index.css` (terminal-cursor keyframes)

## Actions Taken

1. Read spec §6 Implementation Log + §7 Test Coverage + §8 Design Audit to understand
   the 7 documented deviations and the design auditor's 15 compliance checks.
2. Read all new landing components + tests for real-world correctness (not token
   compliance).
3. Verified `AppRoutes` is only imported by `App.test.tsx` (no HMR/build risk).
4. Verified external URLs in LandingFooter via curl:
   - `https://www.kaggle.com/competitions/gemma-4-good` → **404**
   - `https://github.com/jcernauske/futureproof-data` → **404**
   - `https://github.com/jcernauske/brightsmith` → **404**
5. Verified in-page anchor targets (`#video`, `#voice`, `#disclaimers`) do not exist
   anywhere in `frontend/src` via Grep.
6. Verified `frontend/public/` directory does not exist — all landing screenshots
   + plush-laptop asset will 404 at production render until Week 2.
7. Spot-checked test integrity — 48 new tests are substantive, not smoke/theater.
   Negative-regex assertion in OllamaSection and 342/815 positive+negative
   assertion in DataSourcesSection are legitimate regression guards.
8. Compared marketing-landing data footer copy ("700K rows · 280 DQ rules · 7 public
   datasets") vs in-app LandingScreen ("700K+ data points · 280+ quality rules ·
   6 public datasets") — drift confirmed.

## Findings Summary

**10 findings total, 0 blockers, 2 🟠 serious, 1 🟡 moderate, 4 🔵 minor, 3 "sound"/positive.**

The two Serious findings are both judge-facing at the 2026-05-18 hackathon deadline:

- **Finding 1:** Every external footer link points at a 404. Kaggle, both GitHub
  repos, and three in-page anchors (#video, #voice, #disclaimers) have no
  destinations.
- **Finding 2:** Marketing landing and in-app landing show different "ground truth"
  numbers 30 seconds apart. Directly contradicts the "every number has a receipt"
  promise.

## Decisions Made

- **Verdict: CHANGES REQUIRED.** Findings 1 and 2 block VERIFICATION advancement.
  Findings 3–6 are either spec-documented Week-2 operational (3) or tiny polish
  (4, 6); addressed in §10 Discussion as recommended but non-blocking.
- Wrote findings directly into §8 Code Review subsection using the spec's existing
  Sound/Concerns/Blockers template.
- Added a remediation list to §10 Discussion with explicit (a)/(b) options for
  Finding 1 so the implementer can re-roll without a second round of scoping.
- **Did not** advance spec status to VERIFICATION; left at CODE REVIEW pending
  re-review after implementer fixes.

## Artifacts Produced

- `docs/specs/landing-page-and-design-polish.md` §8 Code Review subsection filled
  in with Status, Findings (Sound/Concerns/Blockers), and Verdict.
- `docs/specs/landing-page-and-design-polish.md` §10 Discussion updated with
  remediation list + required-vs-recommended split.
- This session log.

## Handoff

Implementer (Claude Code general) needs to:
1. Decide on Finding 1 Option (a) create destinations or (b) remove the dead links.
2. Reconcile copy-drift in Finding 2 — update LandingScreen.tsx:104–106.
3. Re-run `@faang-staff-engineer` for a second-pass review of the two fixes.
4. Findings 3–6 can be batched into the fix pass or deferred to §11 follow-ups
   at the implementer's discretion — flag in §10 Discussion which path was taken.
