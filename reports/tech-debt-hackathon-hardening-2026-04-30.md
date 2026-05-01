# Tech Debt: Hackathon Hardening — Spec Completion Report

**Spec:** `docs/specs/tech-debt-hackathon-hardening.md`
**Driving audit:** `reports/staff-engineer-audit-2026-04-30.md`
**Completed:** 2026-04-30
**Status:** COMPLETE
**Hackathon deadline:** 2026-05-18 (18 days remaining)

## TL;DR

Six audit findings (Top 10 items #3, #4, #5, #8, #9, #10) addressed in one PR. CORS no longer echoes arbitrary origins. FastAPI startup hook migrated to `lifespan` (no boot-time `DeprecationWarning`). Top-level React `ErrorBoundary` catches render-time crashes with a Brightpath-styled fallback. Three bare `except` blocks in `intent.py` now log DuckDB outages with full stack traces. README documents the no-auth-by-design posture. `.DS_Store` confirmed not tracked. All success criteria met.

## What Shipped

### Backend
- **`backend/app/main.py`** — env-driven CORS allowlist (`CORS_ALLOWED_ORIGINS`, default `http://localhost:5173,http://localhost:4173`); `lifespan` async context manager replaces `@app.on_event("startup")`; same Iceberg-warming behavior at the same severity preserved 1:1; empty-env values fall back to dev defaults with a startup `WARNING` if the parsed list ends up empty.
- **`backend/app/services/intent.py`** — three DuckDB-query helpers (`_get_school_cips`, `_get_crosswalk_cips_for_families`, `_get_career_titles_for_cip`) now `logger.warning(..., exc_info=True)` before returning `[]`. `KeyboardInterrupt` / `SystemExit` propagate per Decision #7.
- **`backend/app/services/guidance.py`** — pre-existing ruff failures fixed in scope (added `from typing import Any`; reformatted three long lines).

### Frontend
- **`frontend/src/components/ui/ErrorBoundary.tsx`** (NEW) — React class component, `getDerivedStateFromError` + `componentDidCatch`, Brightpath fallback (`role="alert"`, `aria-live="assertive"`, refresh + back-to-home buttons, DEV-gated stack details). Inline tokens only — no design-system imports per Decision #5.
- **`frontend/src/App.tsx`** — `<ErrorBoundary>` wraps `<BrowserRouter>` so a router-itself failure also catches.

### Docs
- **`README.md`** — new "Security & Deployment" section between "Setup" and "MCP Server". States the no-auth-by-design posture, names reverse-proxy options for public-internet deployments, explains the CORS choice.

## Tests

| Layer | New Tests | Total After | All Pass |
|---|---|---|---|
| Backend (`pytest`) | +12 | 1269 | ✅ |
| Frontend (`vitest`) | +10 | 710 | ✅ |
| Pipeline (`pytest -m "not network"`) | 0 | 1720 | ✅ |

Notable defensive tests added by the test-writer pass beyond the spec's "New Tests Required" list:
- **`KeyboardInterrupt` propagation pins** in `test_intent.py` — pin Decision #7 against future "tighten the safety net" refactors that would re-broaden to `except BaseException`.
- **Empty-input short-circuit pin** at `_get_crosswalk_cips_for_families` — protects against a refactor that reorders the early-return below the try block and starts spamming WARNs.
- **Production-mode `console.error` leak pin** in `ErrorBoundary.test.tsx` — ensures Vite-built bundles for prod don't leak `[ErrorBoundary]` component stacks to the browser console.

## Build Verification

| Check | Result |
|---|---|
| `cd backend && ruff check .` | PASS |
| `cd backend && mypy app/` | 69 errors (all pre-existing; net delta from this spec: −3) |
| `cd backend && pytest` | 1269/1269 PASS |
| `cd frontend && npx tsc --noEmit` | PASS |
| `cd frontend && npx vitest run` | 710/710 PASS |
| `cd frontend && npx vite build` | PASS (built in 1.29s) |
| `uv run ruff check src/ tests/` | PASS |
| `uv run pytest -m "not network"` | 1720/1720 PASS |

## Audit Items Addressed

| # | Audit Finding | Where Fixed |
|---|---|---|
| 3 | `allow_origins=["*"]` + `allow_credentials=True` | `backend/app/main.py:32-34, 80-86` |
| 4 | `.DS_Store` tracked in repo root | Already untracked at start of session — verified `git ls-files \| grep -i ds_store` returns empty |
| 5 | `@app.on_event("startup")` deprecated | `backend/app/main.py:37-69, 77` |
| 8 | `intent.py` bare-except silences DuckDB outages | `backend/app/services/intent.py:189-194, 219-224, 306-311` |
| 9 | No top-level React `ErrorBoundary` | `frontend/src/components/ui/ErrorBoundary.tsx` + `App.tsx:39-47` |
| 10 | No documented deployment posture | `README.md:19-28` |

## Audit Items Explicitly Out of Scope

- #1 (`Midjourney/` cleanup) — already complete before this spec began.
- #2 (109-file `refactor-prune-deprecated-build-flow`) — separate in-flight refactor, ships as its own PR.
- #6 (`hasSeenStatTutorial` zombie state) — covered by `docs/specs/refactor-remove-dead-frontend-code.md`.
- #7 (`futureproof_server.py` 3,640-line split) — punted to post-hackathon per audit's own guidance.

## Code Review

@faang-staff-engineer flagged two CHANGES REQUIRED in Round 1; both resolved in a single follow-up turn:

1. 🔴 **`text-display-sm` is not a defined Tailwind utility** (defeats the "looks like FutureProof" recovery surface). Fixed: `text-display-sm` → `text-heading` at `ErrorBoundary.tsx:60`.
2. 🟠 **`_parse_cors_origins()` returned `[]` for `CORS_ALLOWED_ORIGINS=""`** — silent demo-killer same shape as the audited bug. Fixed: empty values fall back to `DEFAULT_DEV_ORIGINS`; all-stripped non-empty path emits a `WARNING` so misconfiguration is visible in `logs/`.

## Risks Tracked, Not Fixed

- **`_load_existing_profiles()` not in try/except inside lifespan.** Behaviorally identical to prior `on_event` code per Decision #6, but `lifespan` startup-exception semantics are stricter — flag for next pass.
- **intent.py logging fixes ops-visibility but not user-visibility.** Frontend silence on degraded results is by design per `feedback_no_substitution_caveat`; revisit if it becomes a real-world problem.
- **`ErrorBoundary` wrapping in `App.tsx` is not integration-tested.** Mitigated by static review and unit tests; spec author marked the integration test P2 and that call was respected.

## Files Touched

```
README.md
backend/app/main.py
backend/app/services/guidance.py
backend/app/services/intent.py
backend/tests/test_app.py
backend/tests/services/test_intent.py            (NEW)
frontend/src/App.tsx
frontend/src/components/ui/ErrorBoundary.tsx     (NEW)
frontend/src/components/ui/ErrorBoundary.test.tsx (NEW)
docs/specs/tech-debt-hackathon-hardening.md
```

## Next Steps

The other in-flight pre-submission work (`docs/specs/refactor-prune-deprecated-build-flow.md`) remains the long pole before hackathon submission. With this spec landed, the repo's first-impression surface no longer drags the audit's "B+ engineering substance" grade down — the remaining audit items are deferred-by-design or covered by other specs.
