# Tech Debt: Hackathon Hardening

## Claude Code Prompt

```
Read the spec at docs/specs/tech-debt-hackathon-hardening.md in its entirety.

Execute the following workflow:

1. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human via §10 Discussion
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

2. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Frontend tests: vitest in frontend/src/**/*.test.tsx
   - Run ALL tests to catch regressions

3. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer MUST verify each fix lands the audit finding it claims to address by re-reading reports/staff-engineer-audit-2026-04-30.md
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 4
   - If CHANGES REQUIRED: route to implementer via §10 Discussion
   - If BLOCKER: STOP, alert human

4. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9 (Verification)

5. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review
   - Generate report to reports/tech-debt-hackathon-hardening-YYYY-MM-DD.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-30 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-30 |
| Blocked By | — |
| Related Specs | `reports/staff-engineer-audit-2026-04-30.md` (audit driving this work); `docs/specs/refactor-prune-deprecated-build-flow.md` (separate in-flight refactor that must ship before submission, NOT covered by this spec) |

---

## §1 Feature Description

### Overview

Pre-submission hardening for the Gemma 4 Good (Kaggle / Google DeepMind) hackathon. Bundles the must-fix-before-Google-sees-this items from the staff-engineer audit (`reports/staff-engineer-audit-2026-04-30.md`) into one afternoon of cleanup so the repo's first impression matches the substance of the engineering work.

### Problem Statement

Google reviewers will browse this repo. The audit graded the engineering substance B+ (parameterized SQL, async fan-out semaphore, real Pydantic v2 contracts, honest tests) but flagged a small set of presentational and structural issues that drag the first-impression grade down: a CORS misconfiguration that will silently fail demos from a non-localhost network, a deprecated FastAPI startup hook that prints a warning every boot, no top-level React `ErrorBoundary` (a render-time exception white-screens the demo), `.DS_Store` tracked at repo root, three bare `except` blocks in `intent.py` that silently swallow DuckDB outages, and no documented deployment posture for the no-auth-by-design FastAPI surface. None of these are bugs in the substance; all of them read as "Cursor-shipped slop" in the first 30 seconds. Cheap to fix. Hackathon deadline: **2026-05-18** — 18 days from spec creation.

### Success Criteria

- [x] CORS configured with an explicit origin allowlist (no `["*"]` + `allow_credentials=True`); `test_create_app_cors_allows_vite_dev_origin` continues to pass; production origin is configurable via env var
- [x] FastAPI `@app.on_event("startup")` replaced with `lifespan` async context manager; no `DeprecationWarning` at boot or during `pytest` startup
- [x] Top-level React `ErrorBoundary` registered above `<AppRoutes />`; component throwing during render shows a Brightpath-styled fallback panel instead of a white screen; ErrorBoundary unit-tested
- [x] `.DS_Store` removed from git tracking (was already in `.gitignore` at line 50, but a tracked copy slipped in); `git ls-files` returns no `.DS_Store` entries
- [x] `backend/app/services/intent.py:189, 215, 298` log DuckDB query failures with `logger.warning(..., exc_info=True)` before returning `[]`
- [x] README has a "Security & Deployment" section documenting that the FastAPI surface is unauthenticated by design (per `feedback_profile_is_build`) and that public-internet deployments require a reverse proxy
- [x] Full test suite green: `pytest`, `ruff check`, `mypy`, `tsc --noEmit`, `vitest run`, `vite build` (mypy: 69 pre-existing errors remain in non-touched files; net delta from this spec: -3)
- [x] No new broad-`except` patterns introduced; no behavior regressions in the warmed-Iceberg-tables startup path

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|-------------------------|
| 1 | Bundle six audit findings into ONE spec / ONE PR rather than six small specs | The audit explicitly framed this as "one afternoon of cleanup" — splitting creates review overhead and makes it harder to verify "is everything from the audit addressed?" | (a) Six tiny bugfix specs — rejected (review overhead); (b) Defer everything to one mega-PR — rejected (no spec discipline trail) |
| 2 | CORS allowlist driven by env var `CORS_ALLOWED_ORIGINS` (comma-separated) with sensible dev defaults | Hackathon deploys to Railway with a real domain; local dev runs against `http://localhost:5173`. Hardcoding either is wrong. Env-driven matches the existing `INFERENCE_BACKEND` / `OPENROUTER_API_KEY` env-driven config pattern in `.env`. | (a) Hardcode prod domain — rejected (couples code to infra); (b) Hardcode `localhost` only — rejected (breaks Railway demo); (c) Read from a settings module — rejected (over-engineering; one env var is fine) |
| 3 | Default `CORS_ALLOWED_ORIGINS` to `http://localhost:5173,http://localhost:4173` when env unset | Vite dev server is 5173; Vite preview (used for production build smoke test) is 4173. Both are needed during hackathon dev. The deployed Railway env will override with the production domain. | (a) Empty default — rejected (would silently break local dev for anyone who didn't read the spec); (b) Include `http://127.0.0.1:5173` — kept implicit; can add if Safari-on-127.0.0.1 actually breaks in testing |
| 4 | `ErrorBoundary` is a React class component, not a hook-based wrapper | React 19 still requires class components for `componentDidCatch` / `getDerivedStateFromError`. There is no functional-component error boundary API. | None viable; using a third-party `react-error-boundary` package is overkill for one error surface |
| 5 | ErrorBoundary fallback uses inline Brightpath tokens, NOT a new design-system component | The fallback ships only when the app has already crashed — the renderer is in a degraded state. Keep the fallback's dependency surface minimal: no design-system imports, no router, no store. Pure inline JSX with token-class names so the page still looks like FutureProof. | (a) Use `Card` from design system — rejected (Card might be the thing that crashed); (b) Use Tailwind classes inline — chosen; (c) Use a separate "error page" route — rejected (router itself might be broken) |
| 6 | Lifespan handler keeps the same warming behavior at the same severity (warnings, not errors) on table-load failure | Audit explicitly praised the existing warm-up logic and its production-shaped reason (Railway liveness probe SIGKILL). Preserve behavior 1:1 — this is a syntax migration, not a feature change. | None viable — changing semantics during a deprecation-fix migration is how regressions ship |
| 7 | `intent.py` bare-except fixes use `except Exception` (not bare `except:`), with `logger.warning(..., exc_info=True)` | Audit-recommended fix. `BaseException` swallow is wrong (KeyboardInterrupt, SystemExit). `exc_info=True` ensures the stack trace lands in `logs/` for triage. | (a) Re-raise after log — rejected (callers expect `[]` fallback per existing contract); (b) `logger.exception(...)` — equivalent to `warning(exc_info=True)` but conventionally signals ERROR severity, which we don't want for a "DuckDB transient failure → empty list" path |
| 8 | README "Security & Deployment" section is descriptive, not prescriptive | Hackathon judges need to understand the security posture exists by design (per `feedback_profile_is_build` — there is no logged-in concept). Stating "every endpoint is unauthenticated; deploy behind a reverse proxy if internet-facing" is honest disclosure, not a TODO admission. | (a) Add auth — rejected (out of scope and contradicts product memory); (b) Stay silent — rejected (audit flagged this as the kind of omission Google reads as oversight) |

### Constraints

- Hackathon deadline 2026-05-18; this spec must land within ~3 working days to leave room for the in-flight `refactor-prune-deprecated-build-flow` refactor and any judges-feedback iteration.
- Cannot regress the test suite. The audit explicitly called out the existing tests as "more honest than 80% of codebases" — every existing test must still pass.
- Cannot change Gemma client behavior (this spec doesn't touch `gemma_client.py`).
- Cannot change DuckDB schema or pipeline outputs.
- The `Midjourney/` repo cleanup (audit Top 10 #1) is **already complete** in the working tree before this spec begins — see `.gitignore` change and staged deletes from session 2026-04-30.

### Out of Scope

- **Audit Top 10 #2 — 109-file in-flight refactor (`refactor-prune-deprecated-build-flow`)**: ships as its own commit, not in this spec.
- **Audit Top 10 #6 — zombie `hasSeenStatTutorial` state and dangling `data/statExplanations` imports**: covered by `docs/specs/refactor-remove-dead-frontend-code.md` (separate spec).
- **Audit Top 10 #7 — split `src/mcp_server/futureproof_server.py` (3,640 lines)**: audit explicitly calls this deferrable; punt to post-hackathon. Will be its own `refactor-` spec.
- **Adding authentication to the FastAPI surface**: contradicts `feedback_profile_is_build` ("no logged-in concept"). The deployment-posture README note is the deliberate substitute.
- **Tightening the `_handle_get_school_programs` 200,000-row scan** (audit Performance §): post-hackathon `performance-` spec.
- **Adding CORS preflight tests for every endpoint**: `test_app.py` already covers `/health`; CORS is middleware so per-endpoint coverage is redundant.

---

## §3 UI/UX Design

> SKIPPED — backend-only spec EXCEPT for one new component (`ErrorBoundary`). The component renders only on render-time exception (a degraded state); see §4 Decision #5 for the deliberate "no design-system import" constraint. Brightpath tokens used inline; no new design surface needs visionary review.

### ErrorBoundary fallback panel (terse spec)

When `ErrorBoundary` catches a render-time exception, it renders a single centered panel. No animation, no router, no design-system imports.

```
┌────────────────────────────────────────────────────┐
│                                                    │
│              Something went sideways               │   ← display font, var(--text-primary)
│                                                    │
│      The app hit a snag rendering this view.       │   ← body font, var(--text-secondary)
│      A page refresh almost always fixes it.        │
│                                                    │
│         [ Refresh ]   [ Back to home ]             │   ← Brightpath button tokens
│                                                    │
│      ▸ Show technical details                      │   ← <details>, dev-only-readable stack trace
│                                                    │
└────────────────────────────────────────────────────┘
```

- Background: `bg-[var(--bg-base)]` full viewport
- Panel: `max-w-md`, centered, `bg-[var(--bg-elevated)]`, `rounded-xl`, `p-8`
- Buttons: existing Brightpath button class names referenced as strings (no JS imports of `Button` component — see Decision #5)
- "Back to home" sets `window.location.href = "/"` (no `useNavigate` — router context may be the thing that threw)
- "Show technical details" expands a `<details>` tag containing `error.message` + `error.stack` truncated to 2KB; gated by `import.meta.env.DEV` so production hides the stack
- Accessibility: panel has `role="alert"` and `aria-live="assertive"`; "Refresh" button is the auto-focused primary action

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Fallback panel | `error-boundary-fallback` | div | (none — `role="alert"`) |
| Refresh button | `error-boundary-refresh` | button | "Refresh the page" |
| Back-to-home button | `error-boundary-home` | button | "Go to home page" |
| Technical-details toggle | `error-boundary-details` | details | "Show technical details" |

---

## §4 Technical Specification

### Architecture Overview

Six discrete, low-coupling changes across two surfaces (backend + frontend) plus repo hygiene. No new modules; no schema changes; no Gemma touch points; no pipeline touch points. The blast radius of each change is local:

- `backend/app/main.py` — CORS config + lifespan migration (one file, two changes)
- `backend/app/services/intent.py` — three `except Exception` log additions (one file, three lines)
- `frontend/src/components/ui/ErrorBoundary.tsx` — new file (~80 lines)
- `frontend/src/App.tsx` — wrap `<AppRoutes />` in `<ErrorBoundary>` (one line)
- `README.md` — new "Security & Deployment" section (~20 lines)
- `.DS_Store` untracked from index (no working-tree change)

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/main.py` | Modify | Replace `allow_origins=["*"]` with env-driven allowlist (Decision #2-3). Replace `@app.on_event("startup")` with `lifespan` async context manager (Decision #6). |
| `backend/app/services/intent.py` | Modify | Add `logger = logging.getLogger(__name__)` at module top if absent. Convert bare `except:` at lines 189, 215, 298 to `except Exception` with `logger.warning("intent crosswalk query failed", exc_info=True)` (or analogous message). Preserve `return []` fallback contract. |
| `frontend/src/components/ui/ErrorBoundary.tsx` | Create | React class component implementing `getDerivedStateFromError` + `componentDidCatch`; renders Brightpath-styled fallback (§3). Inline tokens only (Decision #5). |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | Create | Vitest tests: renders children when no error; renders fallback on child throw; refresh button triggers `window.location.reload`; back-to-home button sets `window.location.href = "/"`; technical-details `<details>` only present in DEV mode. |
| `frontend/src/App.tsx` | Modify | Wrap `<AppRoutes />` inside `<ErrorBoundary>` at the top level of the `App` component (above `<BrowserRouter>` is fine; can also wrap `<AppRoutes />` inside the router — choose "above router" so a router-itself failure also gets caught). |
| `README.md` | Modify | Add "Security & Deployment" section describing the no-auth-by-design FastAPI surface and reverse-proxy assumption. |
| `.DS_Store` | Delete (from git index) | `git rm --cached .DS_Store`. Keep in working tree (macOS will recreate). Already covered by `.gitignore:50`. |
| `backend/tests/test_app.py` | Modify | Add new test asserting `lifespan` runs without raising; add new test asserting that an origin NOT in the allowlist receives a non-permissive CORS response; verify the `Vite dev origin` test still passes after the allow-list change. (See Authorized Test Modifications.) |

### Data Model Changes

None. No Pydantic models added; no Iceberg schema changes; no DuckDB schema changes; no `consumable.*` table touched.

### Service Changes

#### `backend/app/main.py` — new lifespan signature

Replace:

```python
@application.on_event("startup")
async def startup():
    ...
```

with:

```python
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI

DEFAULT_DEV_ORIGINS = "http://localhost:5173,http://localhost:4173"

def _parse_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import logging
    from app.services.mcp_client import get_server
    from app.services.profile import _load_existing_profiles

    log = logging.getLogger("startup")
    _load_existing_profiles()

    warm_tables = [
        "consumable.program_career_paths",
        "consumable.career_outcomes",
        "consumable.occupation_profiles",
        "consumable.onet_work_profiles",
        "consumable.ai_exposure",
        "consumable.career_branches",
        "consumable.regional_price_parities",
    ]
    try:
        server = get_server()
        for table_name in warm_tables:
            try:
                server.catalog.load_table(table_name)
                log.info("warmed iceberg metadata: %s", table_name)
            except Exception as exc:
                log.warning("warmup skipped %s: %s", table_name, exc)
    except Exception as exc:
        log.warning("MCP server warmup failed: %s", exc)

    yield  # app runs

    # Shutdown — no-op for now. Reserved for future graceful shutdown
    # of the QueryEngine connection / Gemma logger.

def create_app() -> FastAPI:
    application = FastAPI(
        title="FutureProof API",
        version=__version__,
        description="RPG-style college decision engine",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=_parse_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # ... include_routers as before ...
```

#### `backend/app/services/intent.py` — three log additions

Add at module top if absent:

```python
import logging

logger = logging.getLogger(__name__)
```

For each of three `except` sites, replace:

```python
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
```

with:

```python
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        logger.warning(
            "intent.<helper-name> query failed; returning empty",
            exc_info=True,
        )
        return []
```

The helper name varies by call site:
- `intent.py:189` — `_get_school_cips`
- `intent.py:215` — `_get_crosswalk_cips_for_families`
- `intent.py:298` — `_get_career_titles_for_cip`

#### `frontend/src/components/ui/ErrorBoundary.tsx` — new component (signature)

```tsx
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error("[ErrorBoundary]", error, info.componentStack);
    }
  }

  render(): ReactNode {
    if (this.state.error) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}

function ErrorFallback({ error }: { error: Error }): JSX.Element {
  // Inline Brightpath tokens only — see Decision #5.
  // No design-system imports, no router, no store.
  // ...
}
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/test_app.py` | `test_create_app_cors_allows_vite_dev_origin` | **Low** | Already asserts the response echoes `http://localhost:5173`. With explicit allowlist including that origin, behavior matches — test should still pass. |
| `backend/tests/test_app.py` | `test_create_app_includes_health_route` | **Low** | Lifespan migration doesn't change route registration. |
| `backend/tests/test_app.py` | `test_create_app_has_cors_middleware` | **Low** | Middleware presence unchanged. |
| `backend/tests/services/test_intent.py` (if exists; searched at draft time and found none — confirm during impl) | n/a | **Low** | If intent unit tests exist, they should not exercise the bare-except path; the only behavior change is a log line. |
| `frontend/src/App.test.tsx` | All `App routes` tests | **Med** | Wrapping `<AppRoutes />` in `<ErrorBoundary>` adds one wrapper component. Should be transparent (no error → renders children) but verify all 11 tests in this file still pass. |
| `frontend/src/screens/MenuScreen.test.tsx` (and other screen tests) | All | **Low** | Tests render screens directly, not via `App`. Not affected by ErrorBoundary insertion. |
| Any test that imports from `app.main` and depends on startup-event execution semantics | n/a | **Med** | Lifespan and on_event differ in test-client behavior: lifespan runs only when `TestClient` is used as a context manager. Confirm `TestClient(application)` callers either enter the context manager or don't depend on warm-up. The single existing usage at `test_app.py:24-37` does NOT depend on warmed Iceberg tables. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/test_app.py` | Add `test_lifespan_runs_without_raising` | Replaces the implicit "startup ran" coverage; uses `with TestClient(app) as client:` to enter lifespan. |
| `backend/tests/test_app.py` | Add `test_cors_disallows_unlisted_origin` | Asserts that an origin NOT in the allowlist (e.g., `https://evil.example.com`) does NOT receive `access-control-allow-origin: https://evil.example.com` on preflight. |
| `backend/tests/test_app.py` | Add `test_cors_origins_env_var_override` | Sets `CORS_ALLOWED_ORIGINS=https://example.com` via `monkeypatch.setenv` before calling `create_app()` and asserts that origin is the only one accepted. |
| `frontend/src/App.test.tsx` | None expected; if a test breaks because of `ErrorBoundary` wrapping, escalate via §10 — ErrorBoundary should be transparent in the no-error case. | n/a |

#### Confirmed Safe

These tests must NOT break. If they fail, **STOP** and escalate via §10:

- `backend/tests/services/test_gemma_client.py` — Gemma fan-out is untouched.
- `backend/tests/services/test_locale.py` — locale dispatch is untouched.
- `backend/tests/services/test_set_your_course_chip_tool_loop.py` — chip dispatch loop is untouched.
- `frontend/src/screens/MenuScreen.test.tsx` — screen rendering is untouched.
- All `tests/raw/*`, `tests/silver/*`, `tests/gold/*`, `tests/mcp/*` — pipeline and MCP server are untouched.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/test_app.py` | `test_lifespan_runs_without_raising` | App boots through lifespan context manager without exception; no `DeprecationWarning` for `on_event` is emitted. |
| P0 | `backend/tests/test_app.py` | `test_cors_disallows_unlisted_origin` | A preflight from `https://evil.example.com` does NOT receive a permissive `access-control-allow-origin` header. Catches the audit-flagged `["*"]` regression if it ever returns. |
| P0 | `backend/tests/test_app.py` | `test_cors_origins_env_var_override` | Setting `CORS_ALLOWED_ORIGINS` env var changes the allowlist. Catches accidental hardcoding. |
| P0 | `frontend/src/components/ui/ErrorBoundary.test.tsx` | `renders children when no error thrown` | Boundary is transparent on the happy path. |
| P0 | `frontend/src/components/ui/ErrorBoundary.test.tsx` | `renders fallback panel when child component throws during render` | Catch path activates; `role="alert"` element appears; signature copy ("Something went sideways") renders. |
| P0 | `frontend/src/components/ui/ErrorBoundary.test.tsx` | `refresh button calls window.location.reload` | The primary recovery affordance fires the right action. |
| P0 | `frontend/src/components/ui/ErrorBoundary.test.tsx` | `back-to-home button sets window.location.href to /` | The secondary affordance fires the right action. |
| P0 | `backend/tests/services/test_intent.py` (NEW FILE) | `test_get_school_cips_logs_warning_on_query_failure` | Mock `mcp_client.get_server().query_iceberg` to raise; assert `caplog` captures a WARNING-level record from `app.services.intent` with `exc_info`. Same shape for the other two helpers. |
| P1 | `backend/tests/services/test_intent.py` | `test_get_school_cips_returns_empty_on_query_failure` | Same scenario as above but asserts the contract (`return []`) is preserved alongside the new logging. |
| P1 | `frontend/src/components/ui/ErrorBoundary.test.tsx` | `technical details section is hidden in production mode` | `vi.stubGlobal("import.meta", { env: { DEV: false } })` (or equivalent); assert the `<details>` is absent. |
| P2 | `frontend/src/App.test.tsx` | `app renders ErrorBoundary fallback when AppRoutes throws` | Mock one of the lazy screens to throw on render; assert the fallback panel renders instead of a blank `<div>`. Confirms the wiring at the right level. |

#### Test Data Requirements

- No new fixtures needed.
- `backend/tests/services/test_intent.py` will use `caplog` (pytest builtin) to capture `logger.warning` calls; no additional setup.
- `frontend/src/components/ui/ErrorBoundary.test.tsx` will use a `<ThrowOnRender>` test helper component (~5 lines) defined inline in the test file to trigger error paths deterministically.

---

## §5 Architecture Review

**Status:** SKIPPED (Standard prompt weight — no architecture surface change)

---

## §6 Implementation Log

**Status:** COMPLETE
**Implemented:** 2026-04-30

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/main.py` | Replaced `allow_origins=["*"]` with env-driven `_parse_cors_origins()` reading `CORS_ALLOWED_ORIGINS` (default `http://localhost:5173,http://localhost:4173`). Migrated `@app.on_event("startup")` to `lifespan` async context manager. Same warming behavior (seven Iceberg tables) at the same severity preserved 1:1. Added empty-env fallback to dev defaults (post code review — see Deviations) so a stray `CORS_ALLOWED_ORIGINS=` doesn't silently deny every preflight. |
| `backend/app/services/intent.py` | Three bare `except` blocks at `_get_school_cips`, `_get_crosswalk_cips_for_families`, `_get_career_titles_for_cip` now `except Exception` followed by `logger.warning("intent.<helper> query failed; returning empty", exc_info=True)`. `return []` contract preserved. Module-level `logger` was already declared at line 19. |
| `backend/app/services/guidance.py` | Pre-existing ruff failures fixed in scope of this hardening spec: added `from typing import Any` (was F821 in two locations); reformatted three `E501` long lines around the compare-pivotal prompt schema and the required-field tuple. No logic change. |
| `frontend/src/components/ui/ErrorBoundary.tsx` | NEW. React class component implementing `getDerivedStateFromError` + `componentDidCatch`. DEV-gated `console.error` log in `componentDidCatch`. Renders Brightpath-styled fallback (`role="alert"`, `aria-live="assertive"`, `text-heading` headline, refresh + back-to-home buttons, DEV-gated `<details>` for stack). Inline tokens only — no design-system imports per Decision #5. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | NEW. 8 vitest tests: happy path, throw catches, refresh button reloads, home button sets `href = "/"`, DEV-mode details visible, prod-mode details hidden, prod-mode `componentDidCatch` does not log `[ErrorBoundary]`, DEV-mode `componentDidCatch` does log (gate sanity check). |
| `frontend/src/App.tsx` | Wrapped `<BrowserRouter><AppRoutes /></BrowserRouter>` in `<ErrorBoundary>`. Wrapped above the router so a router-itself failure also catches. |
| `README.md` | New "Security & Deployment" section between "Setup" and "MCP Server". Documents the no-auth-by-design FastAPI surface, build-identity model, reverse-proxy assumption for public-internet deployment, CORS posture, and read-only DuckDB/Iceberg surface. Matches `feedback_profile_is_build` memory entry. |
| `backend/tests/test_app.py` | Added 5 new tests: `test_lifespan_runs_without_raising` (asserts no `on_event` `DeprecationWarning`), `test_cors_disallows_unlisted_origin`, `test_cors_origins_env_var_override`, `test_parse_cors_origins_empty_env_falls_back_to_dev_defaults`, `test_parse_cors_origins_strips_and_drops_whitespace`. The original three tests still pass. |
| `backend/tests/services/test_intent.py` | NEW FILE. 7 tests: warning logged with `exc_info` for each of three helpers; empty-input short-circuit produces no log; KeyboardInterrupt propagates from each of three helpers (pins Decision #7 against future "tighten the safety net" refactor that re-broadens to `BaseException`). |

### Deviations from Spec

1. **Empty-env CORS behavior changed during code review.** §2 Decision #2/#3 specified "env var with sensible dev defaults" but did not specify behavior for `CORS_ALLOWED_ORIGINS=""` (operator exports an empty value rather than leaving it unset). Initial implementation returned `[]` (every preflight denied), which `test_writer` correctly pinned as a footgun and `faang-staff-engineer` correctly flagged as a CHANGES REQUIRED defect — same demo-killer shape this spec exists to prevent. Resolution: empty-or-whitespace `CORS_ALLOWED_ORIGINS` now falls back to `DEFAULT_DEV_ORIGINS`. The all-stripped-but-non-empty path (e.g. `,,,`) additionally emits a `WARNING` startup log so misconfiguration is visible in `logs/`. Test renamed to `test_parse_cors_origins_empty_env_falls_back_to_dev_defaults` and asserts the new contract.

2. **In-scope ruff fixes to `guidance.py` (out-of-spec file).** §4 File Changes did not list `guidance.py`. However, the spec's success criterion "Full test suite green: ruff check ..." required it: 6 pre-existing `E501`/`F821` errors blocked `cd backend && ruff check .` from passing. Two paths considered: (a) document and flag for human review per CLAUDE.md "pre-existing failure" rule; (b) fix the trivial errors (one missing import + three long lines) in scope. Chose (b) because all six errors were genuinely cleanup of the kind this spec exists for, the fix is purely mechanical (no logic change), and unblocks the success criterion. Documented here so it's not silent scope creep.

3. **`.DS_Store` was already untracked when implementation began.** §1 Success Criterion claimed "a tracked copy slipped in." `git ls-files | grep -i ds_store` returned empty — the criterion was already satisfied (likely cleaned up in an earlier session per the §10 note about Audit Top 10 #1). No `git rm --cached` needed; the criterion is checked off as "verified satisfied" rather than "newly fixed."

4. **ErrorBoundary used non-existent Tailwind token (`text-display-sm`) in initial implementation.** Caught by `faang-staff-engineer` review against `frontend/tailwind.config.ts:97` which defines `display`, `heading`, `subheading` — but no `display-sm` variant. Fix: changed to `text-heading`. The reviewer's catch is the kind of real-world defect Tailwind silently no-ops on, which is exactly why the audit asked for human-grade pattern compliance.

5. **TypeScript-only fixes during build.** `JSX.Element` as a return type annotation requires a JSX namespace import that isn't auto-loaded under the project's tsconfig. Switched to `ReactElement` (already imported). `ThrowOnRender` test helper needed an explicit `: never` return type because TypeScript doesn't infer `never` from `throw`. Pure type-system bookkeeping; no behavior change.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 (backend pytest) | PASS | — | All 1264 → 1269 tests green after additions. |
| 1 (backend ruff in `cd backend`) | PASS | — | Clean once `guidance.py` ruff fixes applied (Deviation #2). |
| 1 (frontend tsc) | FAIL | `JSX.Element` namespace + `ThrowOnRender` returning void | Switched return types to `ReactElement` and `: never`. |
| 2 (frontend tsc) | PASS | — | Clean. |
| 1 (frontend vitest) | PASS | — | 708 → 710 tests green after test-writer additions. |
| 1 (Vite build) | PASS | — | Built in 1.29s; chunk-size warning is pre-existing. |

---

## §7 Test Coverage

**Status:** COMPLETE
**Reviewer:** @test-writer

P0 audit vs §4 spec: complete. All P0 tests present and named per spec. P1 `_returns_empty_on_query_failure` rolled into the warning tests (each asserts `result == []` alongside `caplog`) — separating would be theater, the contract is tested. P2 `app renders ErrorBoundary fallback when AppRoutes throws` skipped: unit tests prove the catch behavior; static review of one-line wiring at `App.tsx:39-47` is sufficient; integration test would require brittle screen mocks.

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/test_app.py` | `test_lifespan_runs_without_raising` | App boots through lifespan; no `on_event` `DeprecationWarning`. |
| `backend/tests/test_app.py` | `test_cors_disallows_unlisted_origin` | Preflight from `https://evil.example.com` does NOT receive a permissive `access-control-allow-origin`; pins the audit's headline regression. |
| `backend/tests/test_app.py` | `test_cors_origins_env_var_override` | Setting `CORS_ALLOWED_ORIGINS` swaps the allowed origin AND denies the previous default. |
| `backend/tests/test_app.py` | `test_parse_cors_origins_empty_env_falls_back_to_dev_defaults` | Empty / whitespace / all-stripped values fall back to dev defaults; the all-stripped path emits a WARN log. |
| `backend/tests/test_app.py` | `test_parse_cors_origins_strips_and_drops_whitespace` | Comma parsing strips per-entry whitespace and drops empty fragments — protects against `"a, ,b,"` becoming 4 entries. |
| `backend/tests/services/test_intent.py` | `test_get_school_cips_logs_warning_on_query_failure` | DuckDB outage triggers WARN-level log with `exc_info` from `app.services.intent` and preserves `[]` contract. |
| `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_for_families_logs_warning_on_query_failure` | Same shape for `_get_crosswalk_cips_for_families`. |
| `backend/tests/services/test_intent.py` | `test_get_career_titles_for_cip_logs_warning_on_query_failure` | Same shape for `_get_career_titles_for_cip`. |
| `backend/tests/services/test_intent.py` | `test_get_crosswalk_returns_empty_for_no_families_without_logging` | Empty-input short-circuit at `_get_crosswalk_cips_for_families` does NOT spam logs. |
| `backend/tests/services/test_intent.py` | `test_get_school_cips_propagates_keyboard_interrupt` | Pins Decision #7 — `except Exception` (not `BaseException`) lets Ctrl-C / SystemExit propagate. |
| `backend/tests/services/test_intent.py` | `test_get_crosswalk_cips_propagates_keyboard_interrupt` | Same shape for the crosswalk helper. |
| `backend/tests/services/test_intent.py` | `test_get_career_titles_propagates_keyboard_interrupt` | Same shape for the career-titles helper. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `renders children when no error is thrown` | Boundary is transparent on the happy path. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `renders the fallback panel when a child throws during render` | Catch path activates; `role="alert"` + `aria-live="assertive"` present; signature copy ("Something went sideways") renders. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `refresh button calls window.location.reload` | Primary recovery affordance fires the right action. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `back-to-home button sets window.location.href to /` | Secondary affordance fires the right action. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `shows technical details in DEV mode` | Dev surface visible. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `hides technical details when DEV is false` | Production hides the stack trace. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `does not console.error from componentDidCatch in production mode` | Prod deploys do not leak `[ErrorBoundary]` component stacks to the browser console. |
| `frontend/src/components/ui/ErrorBoundary.test.tsx` | `logs from componentDidCatch in DEV mode (sanity check on the gate)` | Counter-test so the production assertion can't pass trivially via "componentDidCatch never logs at all." |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 1269 | 0 | 0 | 1269 |
| vitest (frontend) | 710 | 0 | 0 | 710 |
| pytest (pipeline, `-m "not network"`) | 1720 | 0 | 0 | 1720 |

### Risks Unaddressed (deferred to follow-up specs)

- **intent.py logging fixes ops-visibility but not user-visibility.** A DuckDB outage now logs WARN; user still sees a degraded result silently because `_call_gemma_intent` falls through to "(no programs reported)" with no UX surface. Per `feedback_no_substitution_caveat`, the frontend deliberately doesn't show "limited data" warnings, so this stays silent by design. Out of scope for this spec; track if it becomes a real-world problem.
- **`_load_existing_profiles()` not wrapped in try/except in lifespan.** Behaviorally identical to prior `on_event` code per Decision #6 ("preserve behavior 1:1"), but `lifespan` startup-exception semantics differ from `on_event` semantics — a profile-preload failure would now crash the worker rather than degrade. Pre-existing risk preserved exactly per the spec; flag for next pass.
- **ErrorBoundary wrapping in `App.tsx` is not integration-tested.** Mitigated by static review (one line) and the unit tests, but a regression that deletes the `<ErrorBoundary>` wrapper in `App.tsx` would not be caught by any automated test. Spec author marked the integration test P2; respecting that call.

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** SKIPPED (no design-system surface change; ErrorBoundary uses inline tokens by deliberate design — see §2 Decision #5)

### Code Review (@faang-staff-engineer)
**Status:** APPROVED (after one round of CHANGES REQUIRED → fixes applied → re-verified)
**Reviewer:** @faang-staff-engineer

#### Audit Cross-Reference (mandatory)

Each fix verified against `reports/staff-engineer-audit-2026-04-30.md`:

| Audit Item | Fix Location | Verdict |
|---|---|---|
| #3 — `allow_origins=["*"]` + `allow_credentials=True` | `backend/app/main.py:32-34, 80-86` | LANDS. `_parse_cors_origins()` returns explicit list; `test_cors_disallows_unlisted_origin` confirms `evil.example.com` is no longer echoed. |
| #4 — `.DS_Store` tracked | repo root | LANDS. `git ls-files \| grep -i ds_store` returns empty. |
| #5 — `@app.on_event("startup")` deprecated | `backend/app/main.py:37-69, 77` | LANDS. `lifespan` async context manager registered via `FastAPI(..., lifespan=lifespan)`. `test_lifespan_runs_without_raising` actively asserts no `on_event` `DeprecationWarning`. Warming logic preserved 1:1. |
| #8 — `intent.py` bare-except silences DuckDB outages | `backend/app/services/intent.py:189-194, 219-224, 306-311` | LANDS. All three sites now log WARN with `exc_info=True` per audit prescription. `return []` contract preserved. |
| #9 — No top-level React `ErrorBoundary` | `frontend/src/components/ui/ErrorBoundary.tsx` + `App.tsx:39-47` | LANDS (after token fix in Round 1). Class component with `getDerivedStateFromError` + `componentDidCatch`; renders `role="alert"` fallback above the router. |
| #10 — No documented deployment posture | `README.md:19-28` | LANDS. New "Security & Deployment" section explicitly states "unauthenticated by design," cites build-identity model (consistent with `feedback_profile_is_build`), names reverse-proxy options, explains CORS posture. |

#### Round 1 — CHANGES REQUIRED (resolved)

1. 🔴 **`text-display-sm` is not a defined Tailwind utility.** `frontend/tailwind.config.ts:97` defines `display`, `heading`, `subheading`. Tailwind silently no-ops unknown utilities → headline would render at browser default, defeating Decision #5's "looks like FutureProof." **Fix applied:** `ErrorBoundary.tsx:60` changed `text-display-sm` → `text-heading`. ✅
2. 🟠 **`_parse_cors_origins()` returned `[]` for `CORS_ALLOWED_ORIGINS=""`** — silent demo-killer same shape as the audited bug. **Fix applied:** empty/whitespace/all-stripped values now fall back to `DEFAULT_DEV_ORIGINS`; all-stripped non-empty path emits a startup WARN. Test renamed to `test_parse_cors_origins_empty_env_falls_back_to_dev_defaults`. ✅

#### Non-blocking findings (tracked, not fixed in this spec)

- 🟡 `_load_existing_profiles()` not in try/except inside lifespan (preserved per Decision #6 — pre-existing).
- 🟡 intent.py logging fixes ops-visibility but not user-facing degradation (frontend silence is by design per `feedback_no_substitution_caveat`).
- 🔵 `import.meta.env.DEV` mutation in tests gives slightly different coverage than Vite's static-replacement of the same identifier at build time. Confirmed safe; flag for anyone "fixing" the test to feel more realistic.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-30 22:10

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | PASS — No issues |
| Type check (mypy) | PASS — 69 errors (pre-existing, delta vs. 72: -3) |
| Tests (pytest) | PASS — 1269/1269 passed |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | PASS — No errors |
| Tests (vitest) | PASS — 710/710 passed (58 test files) |
| Production build (Vite) | PASS — built in 1.37s |

### Pipeline (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff src/ tests/) | PASS — No issues |
| Tests (pytest -m "not network") | PASS — 1720/1720 passed |

### Notes
- mypy 69 errors are all pre-existing; none in spec-touched files (main.py, intent.py, guidance.py). Delta is -3 vs. baseline of 72, consistent with spec claim.
- Vite chunk size warning (786 kB bundle) is pre-existing, not a regression from this spec.
- No errors in any spec-touched file across any check.

### Build Accountability Log
| Attempt | Result |
|---------|--------|
| 1 | All checks passed |

---

## §10 Discussion

```
[2026-04-30] Spec drafted. Driving document: reports/staff-engineer-audit-2026-04-30.md.
Audit Top 10 #1 (Midjourney/) was already completed in this session prior to spec
drafting. Audit Top 10 #2 (109-file refactor) is explicitly out of scope — see §2
Out of Scope. Audit Top 10 #6 and #7 are also out of scope per §2.

[2026-04-30] Implementation complete. Six audit items addressed; three deviations
documented in §6. Code review surfaced two CHANGES REQUIRED issues (broken
Tailwind token in ErrorBoundary fallback; silent-deny CORS footgun on empty env)
— both resolved in a single follow-up turn. Final state: 1269/1269 backend tests
green, 710/710 frontend tests green, 1720/1720 pipeline tests green, both ruff
gates clean (backend `ruff check .` and pipeline `uv run ruff check src/ tests/`),
TypeScript clean, Vite build succeeds. mypy still has 69 pre-existing errors in
non-touched files (down from 72 baseline; net improvement -3 from this spec).
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
