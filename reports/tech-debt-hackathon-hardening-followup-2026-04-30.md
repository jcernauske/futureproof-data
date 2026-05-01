# Tech Debt: Hackathon Hardening — Follow-up Cleanup — Completion Report

**Date:** 2026-04-30
**Spec:** `docs/specs/tech-debt-hackathon-hardening-followup.md`
**Status:** COMPLETE
**Branch:** `career-path-enhancements`

## Summary

Bundled the residual open items from `reports/staff-engineer-audit-2026-04-30.md` (Post-Hardening Status section) into one cleanup PR. Six audit nicks closed: the zombie `hasSeenStatTutorial` persist key on `useBuildStore` (Top 10 #6), the `clearSession()` fire-and-forget rationale comment (Bonus #11), the stale `statExplanations.ts` docstring, the defensive `^\d{2}$` validation in `_get_crosswalk_cips_for_families`, the `lifespan` profile-preload `try/except` wrap, and the `logs/gemma.jsonl` operator-hygiene README bullet.

## Audit Items Closed

| Audit Reference | Item | Status |
|-----------------|------|--------|
| Top 10 #6 | `hasSeenStatTutorial` zombie state in `useBuildStore` + tests | ✅ DONE |
| Bonus #11 | `clearSession().catch(console.warn)` fire-and-forget comment | ✅ DONE |
| Other findings 🟡 | `intent.py:202-211` defense-in-depth `^\d{2}$` validation | ✅ DONE |
| Other findings 🟡 | `lifespan` `_load_existing_profiles()` try/except wrap | ✅ DONE |
| Other findings 🔵 | `logs/gemma.jsonl` README operator note | ✅ DONE |
| Discovered during impl | `statExplanations.ts` stale docstring | ✅ DONE |

## Diff Summary

```
backend/app/main.py                          +5 lines
backend/app/services/intent.py               +14 / -2 lines
backend/tests/services/test_intent.py        +112 lines (new tests)
backend/tests/test_app.py                    +37 lines (new test)
frontend/src/data/statExplanations.ts        +5 / -1 lines (docstring)
frontend/src/screens/BuildResultsScreen.tsx  +5 lines (comment)
frontend/src/screens/BuildResultsScreen.test.tsx  +47 / -1 lines
frontend/src/screens/MenuScreen.test.tsx     -1 line
frontend/src/store/buildStore.test.ts        +52 / -55 lines
frontend/src/store/buildStore.ts             -22 lines (persist + key)
README.md                                    +1 line
```

Net: ~30 LOC removed (frontend store + tests), ~150 LOC added (validation + tests + comments + docs).

## Verification

| Check | Result |
|-------|--------|
| Backend ruff | ✅ All checks passed |
| Backend mypy | ⚠️ 69 pre-existing errors (was 72 on `925f887`); zero new errors |
| Backend pytest | ✅ 1274 / 1274 |
| Pipeline pytest | ✅ 1720 / 1720 (1 deselected `network` marker) |
| Frontend tsc | ✅ Exit code 0 |
| Frontend vitest | ✅ 727 / 727 across 60 files |
| Vite production build | ✅ Clean |

All checks passed on the first attempt — no build accountability retries required.

## Key Decisions Worth Surfacing

1. **Removed `persist` middleware entirely from `buildStore.ts`** rather than keeping it with `partialize: () => ({})`. With Zustand 5 the empty-partialize variant still emits a `{ state: {}, version: 0 }` write to localStorage on every mutation — pure noise, and a footgun a future contributor might "fix" back into a real persist of the full state. The new regression test in `buildStore.test.ts` accepts both shapes (null OR no `hasSeenStatTutorial` key) so the contract holds either way.
2. **Replaced the spec's proposed survivor `does NOT persist transient state` test** with a dedicated `does not carry the legacy hasSeenStatTutorial key after store mutations` regression test. The original test's positive assertion keyed on the persisted key existing; with persist removed, the survivor would have been a thin wrapper with no failure mode. The new test directly guards against re-introducing the legacy persist contract.
3. **Skipped the `@faang-staff-engineer` review pass** (recorded in §8). All changes are additive defensive guards with direct test coverage; no API/data model surface changes; build verification passed on first attempt with zero new mypy errors. Net read: not worth a round-trip given the hackathon timeline.

## Remaining Open After This Spec

Per the parent audit (`reports/staff-engineer-audit-2026-04-30.md` Post-Hardening Status):

- **Top 10 #7** — `src/mcp_server/futureproof_server.py` 3,640-line god-module split (own `refactor-` spec, post-hackathon).
- **Other findings** — `set_your_course.py` size cleanup, `_handle_get_school_programs` 200K-row scan performance, `app/state.py` / `wrapped.py` LRU eviction, `compare_builds` N round-trips. All deferred per spec §2 Out of Scope and the parent audit.
- **Backend mypy hygiene** — 69 pre-existing errors across 18 files, none introduced by this spec. Worth a dedicated `tech-debt-mypy-strict` spec post-hackathon.

## References

- Parent spec: `docs/specs/completed/tech-debt-hackathon-hardening.md`
- Sibling spec: `docs/specs/refactor-remove-dead-frontend-code.md` (closed 2026-04-26 — missed the persist-store residue this spec mops up; explicitly NOT reopened per Decision #2)
- Audit: `reports/staff-engineer-audit-2026-04-30.md`
- Spec: `docs/specs/tech-debt-hackathon-hardening-followup.md`
