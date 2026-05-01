# Report: Prune Deprecated Build-Flow Routes

**Spec:** `docs/specs/completed/refactor-prune-deprecated-build-flow.md`
**Status:** COMPLETE
**Date:** 2026-04-30
**Author:** Jeff Cernauske + Claude Code (auto-mode)
**Pipeline:** ARCH REVIEW → IMPLEMENTATION → TESTING → DESIGN AUDIT → CODE REVIEW → VERIFICATION → COMPLETION

---

## Why this happened

The primary build flow had been rerouted from `/set-your-course → /career-pick → /reveal → /my-build` to a direct `/set-your-course → /my-build` jump (`useSetYourCourse.ts:527`). The old screens, routes, and a 290-line `CareerDetail.tsx` component sat off the main path — some fully unreachable, some still serving as broken back-nav targets that triggered three-hop guard cascades.

This was discovered while shipping `feature-compare-schools-for-career.md`, where the original by-SOC compare trigger was placed inside `CareerDetail.tsx`, only to discover at QA time that `CareerDetail` was on a dead route. Rather than tack the cleanup onto that feature, this is its own refactor pass with explicit per-surface architect sign-off before deletion.

## What shipped

### Files deleted (8)

- `frontend/src/components/CareerDetail.tsx` + `.test.tsx`
- `frontend/src/screens/RevealScreen.tsx` + `.test.tsx`
- `frontend/src/screens/CareerPickScreen.tsx` + `.test.tsx`
- `frontend/src/screens/LandingScreen.tsx` + `.test.tsx`

### Migrations into `FinancesCard.tsx`

| Affordance | Status |
|------------|--------|
| Cost-basis ROI receipt (`RoiReceipt`, ~110 lines) | Migrated as a local function inside a new `<ReceiptPanel id="roi" label={t("build.roi.label")}>` |
| `DebtVsMedianIndicator` | Migrated as a local function rendered under a new "Modeled debt" Row |
| P25/P75 salary band | Migrated as a `subtitle` slot on the median-salary Row |
| Top-5 activities list | Deleted (visionary's `/my-build` redesign deliberately omits this) |
| AI exposure paragraph | Deleted (already covered by RES stat popover in `BuildResultsScreen`) |
| Substitution notice | Deleted (binding `feedback_no_substitution_caveat` user-memory rule) |

### Nav redirects (6 + 1 drive-by)

`navigate("/reveal", …)` → `navigate("/my-build", …)`:
- `BranchTreeScreen.tsx:133, :546`
- `GauntletScreen.tsx:118, :255`
- `SaveWrappedScreen.tsx:60`
- (`CareerPickScreen.tsx:172` was deleted along with the file)

Drive-by per architect's resolution #7: `MenuScreen.tsx:41`'s no-profile bounce changed from `/app` to `/set-your-course` (one hop saved).

### Route table

`App.tsx`:
- `/career-pick` route deleted
- `/reveal` route deleted
- `/app` replaced with `<Navigate to="/set-your-course" replace />` (marketing CTAs at `/app` continue to resolve)
- `/menu` redirect untouched (was already inline)

### AppHeader cleanup (code-review Finding 1)

Removing `/app` as a real mounted route revealed a pre-existing dead branch in `AppHeader.tsx`. Cleaned up in the same pass:
- Deleted `isLanding` declaration and its 23-line conditional Start-button block
- Simplified three `!isLanding && !isGauntletFight` to `!isGauntletFight`
- Removed now-unused `apiPost`, `setProfile`, `starting`/`setStarting`, `ProfileResponse` interface
- Reduced `getPhaseAccent` predicate to live `/my-build` check only

### i18n

Added 6 new keys to en/es/ar locales:
- `build.modeledDebt`
- `build.roi.label`
- `build.roi.strong`
- `build.roi.moderate`
- `build.roi.challenging`
- `build.roi.insufficientData`

## Tests

- 17 net-new tests added (14 in `FinancesCard.test.tsx`, 3 P1 regression tests in `App.test.tsx`)
- 14 existing tests refactored to use `makeCareer()` fixture helper
- 5 nav-target assertions updated across `BranchTreeScreen`, `SaveWrappedScreen`, `MenuScreen`, `SetYourCourseScreen`
- Final results:
  - **pytest (backend):** 1252 passed, 0 failed
  - **vitest (frontend):** 824 passed, 11 failed (pre-existing in `CompareView.test.tsx` and `PentagonOverlay.test.tsx`, verified via stash test), 1 skipped
  - **tsc --noEmit:** clean
  - **Vite production build:** succeeds; bundle reduced ~147 kB from prior baseline

## Pipeline runs

| Step | Agent | Verdict |
|------|-------|---------|
| ARCH REVIEW | `@fp-architect` | APPROVED |
| IMPLEMENTATION | Claude Code (auto) | shipped |
| TESTING | `@test-writer` | 17 added, 0 failed |
| DESIGN AUDIT | `@fp-design-auditor` | CHANGES REQUIRED → addressed (F4, F6 fixed; F1-F3 deferred as pre-existing token debt; F5 deferred for follow-up i18n spec) |
| CODE REVIEW | `@faang-staff-engineer` | CHANGES REQUIRED → addressed (Findings 1, 2, 5 fixed; 3, 4 deferred per reviewer's discretion) |
| VERIFICATION | `@fp-builder` | PASS (pre-existing failures documented) |

## Follow-ups

1. **`RoiReceipt` body copy i18n** (~12 strings inside the disclosure) — small follow-up spec post-hackathon.
2. **Pre-existing `Row` token debt** (`fontSize: 11`, raw rgba border) — small `tech-debt-financescard-tokens.md` spec.
3. **`CompareView.test.tsx` + `PentagonOverlay.test.tsx` `<MemoryRouter>` wrapper** — small unrelated test fix.
4. **Backend `ruff` and `mypy` errors in other in-progress spec work** (feature-language-mode, feature-compare-schools-for-career) — clear as those specs land.

## Notes

The two-pass (audit → migrate → delete) structure was load-bearing. Without the architect's per-affordance sign-off, three live affordances would have been wholesale-deleted with the rest of `CareerDetail`, and the AI exposure paragraph would have been redundantly migrated next to the RES stat popover that already says the same thing in different copy.
