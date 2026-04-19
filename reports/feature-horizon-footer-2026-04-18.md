# Feature Report: Horizon Footer + Wrapped Silhouette
**Date:** 2026-04-18
**Spec:** `docs/specs/feature-horizon-footer.md`
**Status:** COMPLETE

---

## What Shipped

The minimal landing-page footer (`LandingFooter`) was replaced with a cinematic full-bleed `HorizonFooter` that randomly draws from a shuffled bag of 48 Midjourney campus illustrations (AVIF/WebP, served via `<picture>` with 1400/2048 width variants) and bleeds them between the page background and a three-column dark chrome bar (FutureProof identity / Gemma provenance / HyenaStudios studio). Bag state is persisted in sessionStorage (versioned key `fp.horizon.bag.v1.{surface}`) so all 48 illustrations cycle exactly once per session before reshuffling; per-surface bags keep desktop and mobile independent. A muted `HorizonSilhouette` variant was added to `/app/save`, rendering the campus illustration at 60% opacity behind the share card and locked to `Build.horizonIndex` — a new optional field committed on first save — so user device-screenshots of the live Wrapped page are stable across remounts. Motion sequences (cold 1.6s, warm 900ms crossfade), 0.85x scroll parallax (IntersectionObserver + RAF, both torn down on unmount), and `prefers-reduced-motion` opacity-only fallback all shipped. Two code-review Majors were resolved before verification: the in-memory bag fallback now correctly survives the setItem-throws / getItem-succeeds-but-empty race, and SaveWrappedScreen no longer pollutes the shared desktop bag on remounts where `horizonIndex` is already locked.

---

## File Inventory

| File | Action |
|------|--------|
| `frontend/src/components/horizon/horizonManifest.ts` | Created |
| `frontend/src/components/horizon/horizonCaptions.ts` | Created |
| `frontend/src/hooks/useHorizonPick.ts` | Created |
| `frontend/src/components/horizon/HorizonFooter.tsx` | Created |
| `frontend/src/components/horizon/HorizonSilhouette.tsx` | Created |
| `frontend/src/hooks/useHorizonPick.test.ts` | Created |
| `frontend/src/components/horizon/HorizonFooter.test.tsx` | Created |
| `frontend/src/components/horizon/HorizonSilhouette.test.tsx` | Created |
| `frontend/src/types/build.ts` | Modified — added `horizonIndex?: number` |
| `frontend/src/screens/SaveWrappedScreen.tsx` | Modified — HorizonSilhouette overlay + drawAndPersist commit |
| `frontend/src/pages/Landing.tsx` | Modified — HorizonFooter replaces LandingFooter |
| `frontend/src/pages/Landing.test.tsx` | Modified — section-order assertion updated (`horizon-footer`) |
| `frontend/src/screens/SaveWrappedScreen.test.tsx` | Modified — 5 new tests added |
| `frontend/src/components/landing/LandingFooter.tsx` | Deleted |
| `frontend/src/components/landing/LandingFooter.test.tsx` | Deleted |

---

## Test Coverage Delta

**Net new tests: +65** (439 baseline → 504 final)

| Suite | Tests Added | File |
|-------|-------------|------|
| `useHorizonPick.test.ts` | 28 | Hook: bag mechanics, anti-adjacency, sessionStorage fallback, SSR-safety, prefetch, drawAndPersist |
| `HorizonFooter.test.tsx` | 16 | Layout/structure, caption pairing, `<picture>` asset delivery, cleanup |
| `HorizonSilhouette.test.tsx` | 9 | Locked-index stability, opacity, a11y, asset delivery, out-of-range handling |
| `SaveWrappedScreen.test.tsx` | +5 new | horizonIndex commit, locked-at-commit guard, z-index layering, phase-gated render |
| Fix-pass additions | +7 additional in hook + SaveWrapped test files | Major #1 regression, drawAndPersist, __resetInMemoryBagsForTesting, Major #2 regression |

1 pre-existing skip remains (unrelated). 0 regressions.

---

## Pipeline Outcomes

| Stage | Agent | Verdict | Notes |
|-------|-------|---------|-------|
| Architecture Review | @fp-architect | CHANGES REQUESTED → resolved | 4 documentation/correctness patches applied to spec before implementation; no structural rewrites. No blockers. |
| Design Vision | @fp-design-visionary | SKIPPED | §3 was authored from two prior visionary runs + interactive mockup. |
| Data Review | @fp-data-reviewer | SKIPPED | No pipeline / DuckDB / stat / boss-fight changes. |
| Implementation | Claude Code | COMPLETE | 2 build attempts (tsc noUncheckedIndexedAccess; vitest section-id assertion). |
| Testing | @test-writer | COMPLETE | 58 tests added (+7 in fix-pass = 65 net). 1 documented jsdom limitation (reduced-motion ON-path). |
| Design Audit | @fp-design-auditor | CHANGES REQUESTED → resolved | 3 Minor FAILs (raw rgba in gradient mid-stops, inline color style). All fixed in single fix-pass via `color-mix()` + Tailwind opacity utility. |
| Code Review | @faang-staff-engineer | CHANGES REQUIRED → resolved | 2 Major (safeReadBag fallback correctness; unconditional desktop-bag draw in SaveWrappedScreen) + 5 Minor. All resolved in single fix-pass. Build stayed green throughout. |
| Verification | @fp-builder | ALL PASSED | tsc: 0 errors. vitest: 504 pass / 1 skip / 0 fail. Vite: built in 1.29s. Chunk-size warning on main bundle (pre-existing). |

---

## Known Follow-Ups (all out of scope per §2)

- **Real HyenaStudios logo asset** — studio column ships a 32px "HS" placeholder circle with `border-border-subtle`. Replace when brand asset exists.
- **Silhouette in backend-rendered share PNG** — the downloadable share PNG from `renderWrapped(build.build_id)` intentionally does not include the silhouette in v1. Carrying it in requires a backend asset path resolver + Playwright fixture (separate spec).
- **Vite plugin manifest auto-generation** — `horizonManifest.ts` is hand-maintained at 48 entries. If asset count grows beyond 48, replace with a generation script (separate spec). Array reordering changes caption pairings (`index % 3`); a header comment in the manifest warns future maintainers.
