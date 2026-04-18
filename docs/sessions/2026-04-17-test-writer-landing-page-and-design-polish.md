# Session — test-writer — landing-page-and-design-polish (step 4 TESTING)

- **Session ID:** 2026-04-17-test-writer-landing-page-and-design-polish
- **Timestamp:** 2026-04-17
- **Agent:** @test-writer
- **Spec:** `docs/specs/landing-page-and-design-polish.md`
- **Step:** 4 — TESTING (following step 3 IMPLEMENTATION by Claude Code general)

## Objective

Execute step 4 of the spec: write component + page-level vitest coverage for the nine new marketing landing sections, the Ollama claim scoping assertion (architect re-review hand-off from §5 Condition 8), the Karpathy 815-count guard, and the RevealScreen reduced-motion fallback. Do not duplicate the 7 P0 route/header/profile-guard tests that were already written into `App.test.tsx` during step 3.

## Context Read (in order)

1. `docs/specs/landing-page-and-design-polish.md` — full spec (1515 lines), with emphasis on §3.4–§3.12 copy ground truth, §3.15 accessibility identifiers, §4 Testing Impact Analysis, and §5 Architect concerns/conditions.
2. `frontend/src/pages/Landing.tsx` — 9-section composer.
3. All 9 new landing components: `HeroSection`, `ProblemSection`, `HowItWorksSection`, `ReceiptsSection`, `OllamaSection`, `TerminalSVG`, `CTARailSection`, `DataSourcesSection`, `TeamSection`, `LandingFooter`.
4. `frontend/src/test/mocks/prefers-reduced-motion.ts` — the shared reduced-motion helper (used across all new tests).
5. `frontend/src/test-setup.ts` — `IntersectionObserver` + `ResizeObserver` stubs (whileInView tests render cleanly without extra setup).
6. `frontend/src/App.test.tsx` — 7 pre-existing P0 tests (route cutover + AppHeader marketing-safe branch + 3 profile-guard redirects). Not duplicated.
7. `frontend/src/screens/RevealScreen.tsx` + `.test.tsx` — expanded (not replaced) with one reduced-motion test.
8. Pre-existing test baseline run via `npx vitest run` — confirmed 335 pass / 2 fail / 337 total before any new work.

## Actions Taken

### New test files created

| File | New tests | Copy/behavior guards |
|------|----------:|----------------------|
| `frontend/src/pages/Landing.test.tsx` | 3 (1 skipped) | 9-section ordering, `<main id="landing-root">` anchor, P2 axe skipped with rationale |
| `frontend/src/components/landing/HeroSection.test.tsx` | 5 | Copy ground truth, CTA href/aria, demo link aria, reduced-motion drift suspension, motion-enabled smoke |
| `frontend/src/components/landing/ProblemSection.test.tsx` | 7 | §3.5 copy (all 3 paragraphs + headline), two typographic-receipt accent tokens, section landmark |
| `frontend/src/components/landing/HowItWorksSection.test.tsx` | 7 | Section headline, 3 card identifiers as `<article>`, STATS/GAUNTLET/BRANCHES copy, screenshot alt + lazy-load attrs, ordering |
| `frontend/src/components/landing/ReceiptsSection.test.tsx` | 4 | Headline/lead/kicker, screenshot alt (spec-exact), 4 receipt lines in order, accent-token colors |
| `frontend/src/components/landing/OllamaSection.test.tsx` | 7 | Headline, real-text commands, terminal aria, **scoped Ollama claim (ARCHITECT RE-REVIEW gate — positive + negative assertion)**, body copy, laptop default render, onerror fallback |
| `frontend/src/components/landing/DataSourcesSection.test.tsx` | 6 | Headline, 7 row identifiers in order, **canonical counts (incl. Karpathy 815, NOT 342)**, POWERS column, footnote |
| `frontend/src/components/landing/LandingFooter.test.tsx` | 9 | Footer landmark + bg token, wordmark, 7 identifiers exist with hrefs, `/app` internal destination, external links have target=_blank + noopener/noreferrer + HTTPS, disclaimer voice-guide exact, data-line echo, primary + secondary nav ordering |

### Expanded files

| File | Change |
|------|--------|
| `frontend/src/screens/RevealScreen.test.tsx` | Added `import { setReducedMotion, resetReducedMotion }` from the shared helper; wired `resetReducedMotion()` into `beforeEach`/`afterEach`; added a new `describe("RevealScreen — prefers-reduced-motion")` block with one test asserting observable end-state (title, pentagon cell, stat cards, Gemma's Take, career detail, Fight bosses CTA all present at t=0). Pre-existing 3 tests (nav guard, unmount race safety, grid layout) left unmodified. |

### Test hygiene decisions

- **No per-file `matchMedia` reimplementation.** Every test imports `resetReducedMotion` / `setReducedMotion` from `@/test/mocks/prefers-reduced-motion` per the spec's hard-rule #4.
- **No `MemoryRouter` in section tests.** Section components do not use `useNavigate` / `useLocation` — wrapping them in a router would add noise.
- **No backend mocks.** Landing is static content; `spec §4 Service Changes: None`.
- **Assert OBSERVABLE behavior, not Framer Motion internals.** Where reduced-motion changes `transition.delay`, assert on the visible end-state at t=0, not on the delay number itself — Framer Motion re-writes those values internally.
- **No `TaskCreate` / TodoWrite usage.** This was a single linear test-writing pass; task-list overhead would have been noise.

## Test Results

Ran `npx vitest run` with all changes in place:

```
Test Files  1 failed | 43 passed (44)
Tests  2 failed | 383 passed | 1 skipped (386)
```

**Delta from pre-spec baseline:**

| Before spec | After step 3 + step 4 | Delta |
|------------:|----------------------:|------:|
| 335 pass    | 383 pass              | +48   |
| 2 fail      | 2 fail (same F1)      | 0     |
| 0 skip      | 1 skip (P2 axe)       | +1    |
| 337 total   | 386 total             | +49   |

The 2 remaining failures are exactly the 2 pre-existing ProfileScreen F1 failures (`renders profile name`, `reroll swaps name`) — confirmed via grep of the vitest output. They are explicitly **out of scope** for this spec per §4 Testing Impact Analysis and were not touched.

## Decisions + Rationale

1. **P2 axe test skipped, not implemented.** `@axe-core/react` is not a project dependency. Per the spec's Hard Rule #5 ("do not install new dependencies for a P2 test"), left as `it.skip` with an inline comment deferring to Lighthouse ≥95 Accessibility in §9.

2. **Reduced-motion assertion strategy for RevealScreen.** Spec says "Do not assert specific `transition.delay` values." So the test asserts the OBSERVABLE end state: title renders, Fight bosses CTA renders, stat cards render — all at t=0 with no fake-timer advance. This tests the user-visible reduced-motion contract without coupling to Framer Motion's internals.

3. **Ollama claim negative assertion uses regex.** The architect re-review hand-off requires that the bare phrase `No student data leaves the building.` never appears as a standalone sentence. Implemented as a regex check for `(?:^|\.\s+|\.\s*\n\s*)No student data leaves the building\.` — matches period-space + claim or start-of-string + claim, which would fire if someone dropped the "When a school runs FutureProof on Ollama," clause.

4. **Karpathy 815 guarded positive + negative.** Per §5 Concern 5, the stale 342 count lives in other docs. The test positively asserts `815` and negatively asserts `342` on the Karpathy row specifically, so a future search-and-replace mistake fails loudly.

5. **OllamaSection laptop fallback test stubs `globalThis.Image`.** The component probes the asset via `new Image()` + `.onerror`. jsdom's Image doesn't actually load assets, so a `FailingImage` stub with a `src` setter that queues a microtask onerror fires the real fallback path. After the microtask flushes, the `landing-ollama-laptop` element unmounts — asserted via `waitFor`.

6. **No expansion of App.test.tsx.** Reviewed the 7 existing tests; they already cover the route cutover (/, /app), the AppHeader marketing-safe branch (null on `/`, Start ✦ on `/app`), and the three profile-guard redirects (/menu, /profile, /school → /app). No identified gap.

## Escalations

**None.** No real bugs in the implementation. No blockers. Scope guard held: did not cross from testing into implementation.

## Artifacts Produced

- 8 new test files (7 component + 1 page): listed above
- 1 expanded test file: `frontend/src/screens/RevealScreen.test.tsx` (+1 test, +1 describe block, shared-helper imports)
- Spec §7 Test Coverage populated with Tests Added table, Existing Tests Status, Test Results, Gaps Identified
- Spec Status updated: `TESTING → DESIGN AUDIT`
- Metadata `Last Updated` refreshed to `2026-04-17 (testing complete; §7 logged; advancing to DESIGN AUDIT)`

## Next Step

@fp-design-auditor owns step 5 — mechanical token/pattern compliance against Brightpath (DESIGN.md) across all 9 new components and the 3 in-app polish items. Findings go in §8. Screenshots are captured AFTER the auditor approves — they compound any uncaught token drift.
