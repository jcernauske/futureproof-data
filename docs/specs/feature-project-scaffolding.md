# Feature: Project Scaffolding

## Claude Code Prompt

```
Read the spec at docs/specs/feature-project-scaffolding.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (project structure, stack decisions, module boundaries)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes in this spec)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 and confirm the design system integration approach
   - Visionary validates that Brightpath tokens, fonts, and base styling are correctly wired
   - Writes to §3 confirmation or adjustments

3. IMPLEMENTATION
   - Initialize the React/Vite frontend app in frontend/
   - Initialize the FastAPI backend app in backend/
   - Wire Brightpath design system (tokens.css, tailwind.config.ts, motion.ts already exist)
   - Install all dependencies
   - Create the minimal shell: one route on backend, one page on frontend, design system rendering
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write baseline tests
   - Backend: health check endpoint test, app factory test
   - Frontend: App renders test, design tokens load test
   - Run ALL tests to catch issues

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance on the shell page
   - Confirm: dark background, correct fonts loading, tokens accessible via Tailwind classes

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review project structure, dependency choices, configuration
   - Writes findings to §8

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/feature-project-scaffolding-YYYY-MM-DD.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @design-builder checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-04 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-04 |
| Blocked By | — |
| Related Specs | — |

---

## §1 Feature Description

### Overview

Initialize the FutureProof project with a working React/Vite frontend and FastAPI backend, with the Brightpath design system fully wired in, linting/formatting/type-checking configured, and test frameworks operational. This is the foundation every subsequent spec builds on.

### Problem Statement

The project currently has design system tokens (CSS variables, Tailwind config, Framer Motion presets) and agent definitions, but no runnable application. No `package.json`, no `pyproject.toml`, no app entry points. Before any feature work can begin, the project needs a working shell that proves the stack is wired together.

### Success Criteria

- [x] `cd frontend && npm run dev` starts a Vite dev server showing a Brightpath-styled page
- [x] `cd backend && uvicorn app.main:app --reload` starts a FastAPI server with a working `/health` endpoint
- [x] Frontend loads Fredoka, Nunito, and Space Mono fonts from Google Fonts
- [x] Frontend renders with `#1B1D30` background and `#F5F0E8` text (Brightpath dark theme)
- [x] All Brightpath Tailwind utility classes work (e.g., `bg-bp-deep`, `text-accent-thrive`, `font-display`)
- [x] `cd backend && ruff check .` passes with zero errors
- [x] `cd backend && mypy app/` passes with zero errors
- [x] `cd backend && pytest` passes (at least 1 test)
- [x] `cd frontend && npx tsc --noEmit` passes with zero errors
- [x] `cd frontend && npx vitest run` passes (at least 1 test)
- [x] `cd frontend && npx vite build` produces a production build with zero errors
- [x] Frontend has path alias `@/` pointing to `src/`
- [x] Backend has Pydantic v2 `BaseModel` available and a health response model demonstrating it
- [x] CORS is configured on the backend to allow frontend dev server origin

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | React 19 + Vite 6 + TypeScript 5 | Matches CLAUDE.md stack spec. Vite is fastest DX for hackathon pace. | Next.js (too heavy for this, SSR not needed for hackathon demo) |
| 2 | FastAPI + uv for backend | Matches CLAUDE.md spec. uv is fast, modern Python packaging. | Poetry (slower), pip (no lockfile) |
| 3 | Python 3.11+ minimum | Matches CLAUDE.md. Good typing support, stable. | 3.12 (fine but 3.11 is safer for dependency compat) |
| 4 | Tailwind CSS (version matching existing config) | Matches CLAUDE.md. Existing tailwind.config.ts already built. | Force upgrade (risk breaking existing config) |
| 5 | shadcn/ui initialized but no components yet | Foundation for later specs. Don't install components we don't need yet. | Install all shadcn components upfront (wasteful) |
| 6 | Zustand for state management | Lightweight, matches CLAUDE.md recommendation. Install now, use in Spec 1+. | Redux (overkill), Context (insufficient for save slots) |
| 7 | TanStack Query for server state | Matches CLAUDE.md. Install now, use when API calls begin. | SWR (similar but TanStack has better DevTools) |
| 8 | DuckDB Python client for backend | Gold zone data store per architecture. Install now, use in data pipeline specs. | SQLite (doesn't match architecture), Postgres (overkill for MVP) |
| 9 | Single `app/` package in backend | Simple flat structure to start. Routers, services, models directories under app/. | Separate packages per domain (premature for hackathon) |
| 10 | Preserve existing files | tokens.css, tailwind.config.ts, motion.ts already exist and are correct. Don't overwrite. | Regenerate from scratch (wasteful, risk regression) |

### Constraints

- Must preserve existing `frontend/src/styles/tokens.css`, `frontend/tailwind.config.ts`, and `frontend/src/styles/motion.ts` — these are already built and correct.
- Must work on macOS (Jeff's dev machine) and Linux (CI/deployment).
- Backend must be runnable without Ollama/Gemma (those come in later specs).
- No database setup required yet — DuckDB is installed as a dependency but no tables created.

---

## §3 UI/UX Design

> @fp-design-visionary: Confirm the design system integration approach below. The shell page is minimal — it proves the tokens work, not a real screen.

### Shell Page (Frontend Smoke Test)

The shell page is NOT a real FutureProof screen. It's a design system proof-of-life that shows:

1. **Fonts loaded correctly** — Fredoka for display, Nunito for body, Space Mono for data
2. **Background color** — `bg-bp-deep` (#1B1D30) fills the viewport
3. **Text colors** — primary, secondary, muted all rendering correctly
4. **Accent colors** — all six accent colors visible
5. **A sample Framer Motion animation** — one element using `springs.bouncy` to prove motion.ts is wired

```
┌─────────────────────────────────────────────────────────────┐
│  bg-bp-void (#12131F) — full viewport                       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  bg-bp-deep (#1B1D30) — main content area             │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  "FutureProof" — font-display (Fredoka), white  │  │  │
│  │  │  text-hero size                                  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  "A college degree isn't a destination."               │  │
│  │  — font-body (Nunito), text-secondary                  │  │
│  │                                                       │  │
│  │  "It's a starting position."                           │  │
│  │  — font-body (Nunito), text-primary, bold              │  │
│  │                                                       │  │
│  │  "$48,200" — font-data (Space Mono), accent-caution    │  │
│  │                                                       │  │
│  │  ┌──────────────────────────────────────────┐         │  │
│  │  │  Six accent color swatches in a row       │         │  │
│  │  │  ● thrive  ● alert  ● caution            │         │  │
│  │  │  ● insight  ● info  ● empathy            │         │  │
│  │  └──────────────────────────────────────────┘         │  │
│  │                                                       │  │
│  │  ┌──────────────────────────────┐                     │  │
│  │  │  Animated card (Framer Motion)│ ← bounces in       │  │
│  │  │  bg-bp-surface, rounded-xl    │    on page load     │  │
│  │  │  shadow-glow-thrive          │                     │  │
│  │  │  "Design system active ✦"    │                     │  │
│  │  └──────────────────────────────┘                     │  │
│  │                                                       │  │
│  │  API Status: ● Connected (green) / ● Disconnected     │  │
│  │  — fetches /health from backend                       │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Cozy Quest Design References

- Background: `bg-bp-void` for outermost, `bg-bp-deep` for main content
- Text: `text-primary` (#F5F0E8) for main text, `text-secondary` (#C4BFB0) for subtitle
- Typography: `font-display` for title, `font-body` for body, `font-data` for numbers
- Card: `bg-bp-surface`, `rounded-xl`, `shadow-glow-thrive`
- Animation: `springs.bouncy` from motion.ts for the card entrance

### Design Vision Confirmation

**Reviewer:** @fp-design-visionary
**Status:** APPROVED
**Reviewed:** 2026-04-04

The shell page is not a real FutureProof screen, and it should not try to be one. Its job is simple and critical: prove that the Brightpath design system is alive and breathing. Here is what I validated and where the spec needs minor clarification.

**1. Token Chain: CORRECT**

The three-layer wiring is sound: `tokens.css` (CSS custom properties in `@layer base`) -> `tailwind.config.ts` (maps `var(--token-name)` to Tailwind utilities) -> components (use Tailwind classes). This is the canonical approach for a token-driven system on Tailwind v3. The `@layer base` directive in tokens.css requires that `@tailwind base` appears in the root CSS file -- the architect already flagged this and the implementer must ensure `index.css` imports tokens.css and includes all three Tailwind directives in the correct order.

**2. Font Names: CLARIFICATION NEEDED**

The CLAUDE.md system prompt references "Fredoka One" but the actual design system proposal, tokens.css, and tailwind.config.ts all correctly use **`Fredoka`** (the variable-weight font, not the single-weight "Fredoka One" which is a different Google Fonts entry). The spec's success criteria at line 103 correctly says "Fredoka" -- good. The Google Fonts `<link>` in `index.html` MUST request `Fredoka` (variable, weights 300-700), NOT `Fredoka+One`. The correct Google Fonts URL pattern is:

```
https://fonts.googleapis.com/css2?family=Fredoka:wght@300;400;500;600;700&family=Nunito:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap
```

Include `font-display: swap` via the `&display=swap` parameter. Preload the stylesheet in `<head>` with `rel="preconnect"` to `fonts.googleapis.com` and `fonts.gstatic.com` for faster loading.

**3. Tailwind Class Names: ONE AMBIGUITY TO RESOLVE**

The wireframe and design references use shorthand labels like `text-primary` and `text-secondary`. In the actual Tailwind config, text colors live under `colors.text`, so the generated utility classes are `text-text-primary`, `text-text-secondary`, and `text-text-muted`. This double-`text` pattern is ugly but correct for Tailwind v3. The implementer must use:

| Wireframe Label | Actual Tailwind Class |
|---|---|
| `bg-bp-deep` | `bg-bp-deep` (correct as-is) |
| `bg-bp-void` | `bg-bp-void` (correct as-is) |
| `bg-bp-surface` | `bg-bp-surface` (correct as-is) |
| `text-primary` | `text-text-primary` |
| `text-secondary` | `text-text-secondary` |
| `text-muted` | `text-text-muted` |
| `text-accent-thrive` | `text-accent-thrive` (correct as-is) |
| `font-display` | `font-display` (correct as-is) |
| `font-body` | `font-body` (correct as-is) |
| `font-data` | `font-data` (correct as-is) |
| `shadow-glow-thrive` | `shadow-glow-thrive` (correct as-is) |
| `rounded-xl` | `rounded-xl` (correct as-is) |

The background colors (`bg-bp-*`) and accent colors (`text-accent-*`) are fine because they are namespaced under `bp` and `accent` respectively. Only the text colors have the collision because Tailwind's `text-` prefix meets the `text` color group name.

**4. Framer Motion Integration: CORRECT**

Importing springs and transitions from `@/styles/motion` is the right pattern. The `@/` path alias must resolve in both `tsconfig.json` (for TypeScript) and `vite.config.ts` (for Vite's bundler). The shell page should use `springs.bouncy` for the animated card entrance -- this proves the import chain works end-to-end. The motion.ts file is well-structured with typed exports that will serve every screen from Character Select through Compare.

**5. Dark-First Aesthetic: CORRECT**

The shell page wireframe correctly layers `bg-bp-void` as the outermost canvas with `bg-bp-deep` for the main content area. This creates the depth-layering effect that makes Brightpath feel like a night sky -- not a dark mode toggle, but a world that was always dark and warm. The accent color swatches will pop against this background exactly as intended. The `shadow-glow-thrive` on the animated card will create the characteristic Brightpath "light in the darkness" effect.

**6. What Makes This Shell Page Work as a Proof-of-Life**

The wireframe covers every axis of the design system:
- Three font families rendered visibly (Fredoka display, Nunito body, Space Mono data number)
- Background depth layering (void -> deep -> surface on the card)
- All six accent colors as swatches
- A Framer Motion spring animation (bouncy card entrance)
- A glow shadow (shadow-glow-thrive)
- An API health check indicator (proves frontend-backend connection)

This is exactly the right scope. It does not try to be a screen -- it tries to prove that every token is wired and every font is loaded. When this page renders correctly, the design system is ready for Screen 1.

**Verdict: APPROVED with the font name and text class clarifications noted above.**

### Responsive Behavior

- Centers content with max-width 800px on desktop
- Stacks naturally on mobile (no special handling needed for the shell page)

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Main content | `main` | landmark | "FutureProof design system shell" |
| API status | `api-status` | status | "Backend API connection status" |

---

## §4 Technical Specification

### Architecture Overview

This spec creates the two application entry points (frontend and backend) and wires the existing design system tokens into a runnable app. No business logic, no data pipeline, no Gemma integration.

```
future_proof/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   └── health.py        # GET /health
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── health.py        # HealthResponse Pydantic model
│   │   └── services/
│   │       └── __init__.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # pytest fixtures (FastAPI TestClient)
│   │   └── test_health.py       # Health endpoint test
│   ├── pyproject.toml           # uv project config
│   └── ruff.toml                # Ruff linting config
├── frontend/
│   ├── index.html               # Vite entry HTML (loads Google Fonts)
│   ├── package.json             # npm dependencies
│   ├── tsconfig.json            # TypeScript config
│   ├── tsconfig.node.json       # TypeScript node config (Vite)
│   ├── vite.config.ts           # Vite config with React plugin and @/ alias
│   ├── postcss.config.js        # PostCSS for Tailwind
│   ├── tailwind.config.ts       # EXISTING — do not overwrite
│   ├── src/
│   │   ├── main.tsx             # React entry point
│   │   ├── App.tsx              # Shell page component
│   │   ├── App.test.tsx         # Shell page test
│   │   ├── index.css            # Tailwind directives + tokens import
│   │   ├── vite-env.d.ts        # Vite type declarations
│   │   ├── styles/
│   │   │   ├── tokens.css       # EXISTING — do not overwrite
│   │   │   └── motion.ts        # EXISTING — do not overwrite
│   │   ├── components/          # Empty — ready for Spec 1+
│   │   ├── hooks/               # Empty — ready for Spec 1+
│   │   ├── lib/                 # Empty — ready for Spec 1+
│   │   └── types/               # Empty — ready for Spec 1+
│   └── vitest.config.ts         # Vitest config
└── CLAUDE.md                    # EXISTING — do not overwrite
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/pyproject.toml` | Create | Python project config with FastAPI, Pydantic, DuckDB, uvicorn, pytest, ruff, mypy deps |
| `backend/ruff.toml` | Create | Ruff linting configuration |
| `backend/app/__init__.py` | Create | Empty init |
| `backend/app/main.py` | Create | FastAPI app factory with CORS middleware |
| `backend/app/routers/__init__.py` | Create | Empty init |
| `backend/app/routers/health.py` | Create | GET /health endpoint |
| `backend/app/models/__init__.py` | Create | Empty init |
| `backend/app/models/health.py` | Create | HealthResponse Pydantic v2 model |
| `backend/app/services/__init__.py` | Create | Empty init |
| `backend/tests/__init__.py` | Create | Empty init |
| `backend/tests/conftest.py` | Create | TestClient fixture |
| `backend/tests/test_health.py` | Create | Health endpoint test |
| `frontend/package.json` | Create | npm project with React, Vite, Tailwind, Framer Motion, etc. |
| `frontend/index.html` | Create | Vite entry with Google Fonts preload |
| `frontend/tsconfig.json` | Create | TypeScript config with strict mode and path aliases |
| `frontend/tsconfig.node.json` | Create | TypeScript config for Vite/node files |
| `frontend/vite.config.ts` | Create | Vite config with React plugin and `@/` alias |
| `frontend/postcss.config.js` | Create | PostCSS with Tailwind and autoprefixer |
| `frontend/vitest.config.ts` | Create | Vitest config with jsdom and path aliases |
| `frontend/src/main.tsx` | Create | React 19 entry point |
| `frontend/src/App.tsx` | Create | Shell page component with design system proof |
| `frontend/src/App.test.tsx` | Create | Basic render test |
| `frontend/src/index.css` | Create | Tailwind directives + tokens.css import |
| `frontend/src/vite-env.d.ts` | Create | Vite client type reference |
| `frontend/src/components/.gitkeep` | Create | Placeholder |
| `frontend/src/hooks/.gitkeep` | Create | Placeholder |
| `frontend/src/lib/.gitkeep` | Create | Placeholder |
| `frontend/src/types/.gitkeep` | Create | Placeholder |

### Data Model Changes

**Backend — HealthResponse (Pydantic v2):**

```python
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str  # "ok"
    project: str  # "futureproof"
    version: str  # "0.1.0"
```

### Service Changes

**Backend — FastAPI app factory (`app/main.py`):**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health

def create_app() -> FastAPI:
    app = FastAPI(
        title="FutureProof API",
        version="0.1.0",
        description="AI Career Impact Tool — Backend API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
            "http://localhost:4173",  # Vite preview
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)

    return app

app = create_app()
```

**Backend — Health router (`app/routers/health.py`):**

```python
from fastapi import APIRouter
from app.models.health import HealthResponse

router = APIRouter(tags=["system"])

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        project="futureproof",
        version="0.1.0",
    )
```

**Frontend — Key dependencies (package.json):**

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "framer-motion": "^11.0.0",
    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.0.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "vitest": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "jsdom": "^25.0.0"
  }
}
```

> Note: Tailwind version should match what tailwind.config.ts expects. The existing config uses `satisfies Config` from `tailwindcss` — verify compatibility. If the existing config is Tailwind v3 syntax, use v3. Do not force v4 if the config was written for v3.

**Backend — pyproject.toml key dependencies:**

```toml
[project]
name = "futureproof-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "duckdb>=1.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]
```

### Testing Impact Analysis

> No existing tests to break — this is the first spec.

#### Existing Tests at Risk

None — no tests exist yet.

#### Authorized Test Modifications

None — no tests exist yet.

#### Confirmed Safe

N/A — first spec.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/test_health.py` | `test_health_returns_ok` | GET /health returns 200 with status "ok" |
| P0 | `backend/tests/test_health.py` | `test_health_response_model` | Response matches HealthResponse schema |
| P0 | `frontend/src/App.test.tsx` | `renders FutureProof title` | App component renders without crashing, shows title text |
| P1 | `frontend/src/App.test.tsx` | `renders with dark background` | Root element has the expected dark background class |

#### Test Data Requirements

- Backend: FastAPI TestClient (from httpx)
- Frontend: jsdom environment via vitest, @testing-library/react

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED
**Reviewed:** 2026-04-04
**Reviewer:** @fp-architect

#### Findings

**1. Project Structure -- Backend**

The flat `app/` structure with `routers/`, `models/`, `services/` is the right call for a hackathon MVP. I have seen teams waste days on hexagonal architecture that they never need. This gives you exactly three places to look for things, and you can draw the dependency graph on a napkin: `routers -> services -> models`. When (if) complexity grows, you split by domain later. No objections.

The app factory pattern (`create_app()`) is correct and important -- it makes `conftest.py` trivial and means you can spin up isolated app instances in tests without module-level side effects. Good.

One note: the spec shows `app = create_app()` at module level in `main.py`. That is the standard uvicorn pattern and it works. Just be aware that if you later add startup/shutdown lifespan events, you will want to use FastAPI's `lifespan` parameter on the factory, not `@app.on_event` (which is deprecated). Not a concern for this spec, but worth documenting for future spec authors.

**2. Stack Decisions**

| Decision | Assessment |
|----------|-----------|
| React 19 + Vite 6 | Sound. React 19 is stable, Vite 6 is current. No concerns. |
| TypeScript 5.6+ | Fine. Strict mode in tsconfig is the right default. |
| Tailwind v3 (not v4) | Correct decision. The existing `tailwind.config.ts` uses `satisfies Config` from the `tailwindcss` package and the v3 `content` array pattern. Tailwind v4 uses a completely different CSS-first config approach. Forcing v4 would break the existing config. Staying on v3.4.x is the right call. |
| FastAPI + uv | No concerns. uv is fast, lockfile is deterministic. |
| Pydantic v2 | Correct. The `HealthResponse` model is trivial but proves the pattern. |
| DuckDB as install-only dep | Fine -- install now, use later. Zero cost to carry. |
| Zustand + TanStack Query | Good separation of client state vs server state. Installing now with no usage is harmless and avoids a re-scaffold later. |
| shadcn/ui initialized but empty | Correct approach. shadcn copies components into your tree, so there is nothing to install upfront -- just the CLI config. |

**3. Module Boundaries and CORS**

The CORS config allowing `localhost:5173` and `localhost:4173` is correct for dev. Two observations:

- The `allow_methods=["*"]` and `allow_headers=["*"]` wildcards are fine for a hackathon. In production you would tighten these, but that is not this spec's problem.
- There is no mention of environment-based CORS origin configuration. For the hackathon demo, hardcoded origins are acceptable. If a deployment spec comes later, CORS origins should come from environment variables. Flag this as a future concern, not a blocker.

**4. Dependency Versions**

Backend versions look reasonable:
- `fastapi>=0.115.0` -- current stable is in the 0.115.x range, fine.
- `pydantic>=2.10.0` -- current, no concerns.
- `duckdb>=1.1.0` -- current stable, fine.
- `httpx>=0.27.0` for test client -- correct, this is what FastAPI's `TestClient` needs.
- `pytest-asyncio>=0.24.0` -- note that the health endpoint is `async def` but is being tested via `TestClient` which is synchronous. pytest-asyncio is not strictly needed for this spec but is a reasonable forward-looking install.

Frontend versions look reasonable:
- `framer-motion: ^11.0.0` -- compatible with the existing `motion.ts` which imports `Transition` and `Variants` types from `framer-motion`. Verified the import types exist in v11. Good.
- `vitest: ^2.0.0` -- current stable, pairs well with Vite 6.
- `@testing-library/react: ^16.0.0` -- compatible with React 19.
- `jsdom: ^25.0.0` -- current, no concerns.
- `zod: ^3.23.0` -- not used in this spec but reasonable forward install for form validation in later specs.
- `clsx + tailwind-merge` -- standard combo for conditional class composition. Good.

One compatibility note: The spec lists `@types/react: ^19.0.0` and `@types/react-dom: ^19.0.0`. These exist and are correct for React 19. Just ensure the installer resolves actual published versions (they are available on npm). No blocker.

**5. Existing File Preservation**

This is the most load-bearing constraint in the spec. Three files must not be overwritten:

| File | Why it matters |
|------|---------------|
| `frontend/src/styles/tokens.css` | 155 lines of CSS custom properties. Source of truth for the entire design system. Uses `@layer base` which requires Tailwind's `@tailwind base` directive to be present in the root CSS. |
| `frontend/tailwind.config.ts` | Maps CSS custom properties to Tailwind utility classes. Written for Tailwind v3 (`satisfies Config` pattern, `content` array). |
| `frontend/src/styles/motion.ts` | Framer Motion spring/variant presets. Imports from `framer-motion` types. The file's usage comment references the `@/styles/motion` path alias, which means the `@/` path alias in `tsconfig.json` and `vite.config.ts` is load-bearing for this file to be importable. |

The `index.css` file that the spec will create must include `@import './styles/tokens.css'` (or equivalent) AND the three Tailwind directives (`@tailwind base; @tailwind components; @tailwind utilities;`). The `@layer base` in `tokens.css` will only work if `@tailwind base` is processed. The spec does not explicitly spell out the `index.css` contents, but the intent is clear. Implementation should ensure the import order is correct: import `tokens.css` before or alongside the Tailwind directives so that the `@layer base` block is included during Tailwind's base layer processing.

**6. What is Missing (non-blocking)**

- **No `.gitignore` pattern.** The spec does not mention creating `.gitignore` files. The implementer should create them for both `backend/` and `frontend/` directories, or a root-level one covering `node_modules/`, `dist/`, `.venv/`, `__pycache__/`, `.mypy_cache/`. Minor but important for a clean repo.
- **No environment variable pattern.** Fine for scaffolding, but the moment you need API keys or Ollama URLs, you will want this. Not this spec's job.
- **No root-level task runner.** With two separate directories (`cd backend && ...`, `cd frontend && ...`), a Makefile or justfile would reduce friction. Nice-to-have for a future spec.

**7. Risk Assessment**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Tailwind v4 accidentally installed instead of v3 | HIGH | Pin `tailwindcss: ^3.4.0` in package.json (spec already does this) |
| `@/` path alias not wired in both tsconfig and vite.config | MEDIUM | Success criteria covers this; test should verify import resolution |
| tokens.css import order breaks `@layer base` | LOW | Implementer must ensure correct CSS import ordering |
| Missing .gitignore pollutes repo | LOW | Implementer should add .gitignore (minor deviation from spec is acceptable) |

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

**Summary:** This is a clean, well-scoped scaffolding spec. The stack choices are consistent with CLAUDE.md, the dependency versions are compatible with existing files, and the flat backend structure is appropriate for the project's current stage. The existing file preservation constraints are clearly stated and the success criteria are testable. The spec does what scaffolding specs should do: get out of the way so real feature work can begin.

**One recommendation (non-blocking):** The implementer should add `.gitignore` files even though the spec does not explicitly list them. Document the deviation in section 6 if added.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline/data changes)

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/pyproject.toml` | Created — uv project config with FastAPI, Pydantic v2, DuckDB, dev tools. Added `[tool.hatch.build.targets.wheel] packages = ["app"]` for hatchling. |
| `backend/ruff.toml` | Created — py311 target, line-length 88, E/F/I rules |
| `backend/app/__init__.py` | Created — `__version__ = "0.1.0"` (single source of truth per code review) |
| `backend/app/main.py` | Created — FastAPI factory with CORS, imports `__version__` |
| `backend/app/routers/health.py` | Created — GET /health endpoint, imports `__version__` |
| `backend/app/models/health.py` | Created — HealthResponse Pydantic v2 model |
| `backend/app/routers/__init__.py` | Created — empty |
| `backend/app/models/__init__.py` | Created — empty |
| `backend/app/services/__init__.py` | Created — empty |
| `backend/tests/__init__.py` | Created — empty |
| `backend/tests/conftest.py` | Created — TestClient fixture |
| `backend/tests/test_health.py` | Created — 5 health endpoint tests |
| `backend/tests/test_app.py` | Created by @test-writer — 3 app factory tests |
| `frontend/package.json` | Created — React 19, Vite 6, Tailwind v3, all deps |
| `frontend/index.html` | Created — Vite entry, Google Fonts, body bg inline style |
| `frontend/tsconfig.json` | Created — strict, @/ path alias |
| `frontend/tsconfig.node.json` | Created — composite, declaration emit for project references |
| `frontend/vite.config.ts` | Created — React plugin, @/ alias |
| `frontend/postcss.config.js` | Created — CJS, Tailwind + autoprefixer |
| `frontend/vitest.config.ts` | Created — jsdom, globals, @/ alias, test-setup |
| `frontend/src/test-setup.ts` | Created — jest-dom/vitest matchers |
| `frontend/src/index.css` | Created — tokens.css import + Tailwind directives |
| `frontend/src/main.tsx` | Created — React 19 createRoot entry |
| `frontend/src/vite-env.d.ts` | Created — Vite client types |
| `frontend/src/App.tsx` | Created — Shell page with Brightpath design system proof |
| `frontend/src/App.test.tsx` | Created — 5 shell page tests |
| `frontend/src/lib/api.ts` | Created — API_BASE_URL from env var (per code review) |
| `frontend/src/styles/motion.ts` | Modified — removed unused `Transition` type import (was breaking tsc strict) |

### Deviations from Spec
1. Added `[tool.hatch.build.targets.wheel] packages = ["app"]` to pyproject.toml — hatchling couldn't find the package without it since the directory is `app/` not `futureproof_backend/`.
2. Changed `tsconfig.node.json` from `noEmit: true` to `emitDeclarationOnly: true` — composite projects can't disable emit (TS6310).
3. Removed unused `Transition` import from `motion.ts` — was failing `noUnusedLocals` in strict mode. This is a minimal bug fix, not an overwrite.
4. Created `frontend/src/lib/api.ts` with `VITE_API_BASE_URL` env var pattern — not in original spec §4 file list, added per @faang-staff-engineer code review (Finding 1).
5. Added `__version__` to `backend/app/__init__.py` — per code review (Finding 2), version string single source of truth.
6. Added `style="background: #12131F"` to `<body>` in index.html — per @design-builder recommendation to prevent white flash.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | FAIL | hatchling: "Unable to determine which files to ship" | Added `[tool.hatch.build.targets.wheel] packages = ["app"]` |
| 2 | FAIL | TS6310: Referenced project may not disable emit | Changed tsconfig.node.json to use `emitDeclarationOnly` |
| 3 | FAIL | TS6196: 'Transition' declared but never used | Removed unused import from motion.ts |
| 4 | PASS | All checks green | — |

---

## §7 Test Coverage

**Status:** COMPLETE
**Reviewed:** 2026-04-04
**Reviewer:** @test-writer

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/test_health.py` | `test_health_returns_ok` | P0: GET /health returns 200 with correct status, project, version fields |
| `backend/tests/test_health.py` | `test_health_response_model` | P0: Response JSON deserializes into HealthResponse Pydantic model |
| `backend/tests/test_health.py` | `test_health_returns_json_content_type` | NEW: Response Content-Type is application/json (frontend fetch depends on this) |
| `backend/tests/test_health.py` | `test_health_post_not_allowed` | NEW: POST /health returns 405 (only GET is defined on the route) |
| `backend/tests/test_health.py` | `test_health_response_has_exactly_three_fields` | NEW: Response has exactly {status, project, version} -- catches accidental API contract changes |
| `backend/tests/test_app.py` | `test_create_app_includes_health_route` | NEW: App factory wires the health router so /health is reachable |
| `backend/tests/test_app.py` | `test_create_app_has_cors_middleware` | NEW: CORS middleware is present on the app |
| `backend/tests/test_app.py` | `test_create_app_cors_allows_vite_dev_origin` | NEW: CORS preflight from localhost:5173 returns correct allow-origin header |
| `frontend/src/App.test.tsx` | `renders FutureProof title` | P0: App renders without crash, shows "FutureProof" text |
| `frontend/src/App.test.tsx` | `renders with dark background` | P1: Main element has bg-bp-deep class (Brightpath dark theme) |
| `frontend/src/App.test.tsx` | `has accessible main landmark with aria-label` | NEW: Main landmark has correct aria-label per accessibility spec |
| `frontend/src/App.test.tsx` | `renders API status indicator` | NEW: API status element exists with correct role and aria-label |
| `frontend/src/App.test.tsx` | `renders all six accent color swatches` | NEW: All six accent colors (thrive, alert, caution, insight, info, empathy) are rendered |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 8 | 0 | 0 | 8 |
| vitest | 5 | 0 | 0 | 5 |

### Edge Cases Covered

- **API contract stability**: `test_health_response_has_exactly_three_fields` catches accidental field additions/removals to the health response
- **Method restriction**: `test_health_post_not_allowed` catches if someone changes the route decorator to accept all methods
- **CORS actual behavior**: `test_create_app_cors_allows_vite_dev_origin` tests a real preflight request rather than just checking config exists
- **Accessibility**: Frontend tests verify aria-labels that screen readers depend on
- **Design system completeness**: Accent color swatch test catches if a color is removed from the shell page

### Gaps Identified

- **Font loading**: Cannot verify Google Fonts actually load in jsdom (no real CSS engine). Would need a browser-level test (Playwright).
- **Framer Motion animation**: The animated card renders in jsdom but the animation does not execute. Would need visual regression testing.
- **CSS custom property values**: jsdom does not compute CSS, so we cannot assert that bg-bp-deep resolves to #1B1D30. Class presence is the best proxy.
- **Frontend API fetch behavior**: App.tsx fetches /health on mount. Testing the connected/disconnected state transitions would require mocking fetch with different responses. Deferred -- the health endpoint itself is thoroughly tested on the backend side.

---

## §8 Reviews

**Status:** COMPLETE

### Design Audit (@design-builder)
**Status:** PASS

**Audit Date:** 2026-04-04

| Check | Result | Notes |
|-------|--------|-------|
| Dark background | PASS | `bg-bp-void` outer, `bg-bp-deep` inner. No light backgrounds. |
| Fonts loading | PASS | Fredoka, Nunito, Space Mono via Google Fonts with preconnect. All three used in shell. |
| Token usage (no hardcoded hex) | PASS | All colors via Tailwind utilities -> CSS vars -> tokens.css. Zero hardcoded values. |
| Text color hierarchy | PASS | `text-text-primary`, `text-text-secondary`, `text-text-muted` used with correct semantic hierarchy. |
| Accent color swatches | PASS | All 6 rendered: thrive, alert, caution, insight, info, empathy. Salary uses caution (appropriate). |
| Motion from presets | PASS | `springs.bouncy` imported from `@/styles/motion`. Not hardcoded. |
| Shadow glow on card | PASS | `shadow-glow-thrive` class on animated card. Maps to correct CSS variable. |
| CSS import chain | PASS | `tokens.css` imported before Tailwind directives in `index.css`. Correct order. |

**Minor observations (non-blocking):**
- `<body>` has no inline background color; brief white flash possible before React hydrates. Recommend `style="background: #12131F"` on body as polish.
- Font loaded as "Fredoka" (variable-weight successor to "Fredoka One" referenced in CLAUDE.md). This is correct modern usage; tokens.css confirms.

**Verdict:** PASS — Full Brightpath token compliance. Shell page is a clean design system proof-of-life.

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
**Reviewed:** 2026-04-05
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary

Look, I love Claude, BUT... this is a scaffold, and even scaffolds can set traps for the people who build on top of them. I went through every file expecting the usual AI-generated landmines and -- I'll grudgingly admit -- this is a reasonably clean foundation. The CORS config is scoped, the test coverage is thoughtful, TypeScript strict mode is on. That said, I found two issues that will absolutely bite someone if left unfixed, and a couple of minor items that will compound as the codebase grows.

#### Findings

**Finding 1: Hardcoded backend URL in App.tsx** [Serious]

**Impact:** The frontend has `http://localhost:8000/health` hardcoded directly in the component. The moment this runs anywhere other than a local dev machine -- staging, preview deploy, a teammate's Docker setup with a different port -- the health check silently fails and shows "Disconnected" with no explanation. Worse, when real API calls get added following this pattern, you'll have hardcoded URLs scattered across dozens of components. I've seen this movie before. It ends with a Friday deploy where someone grep-replaces half the URLs and misses the rest.

**Location:** `frontend/src/App.tsx:18`
```tsx
fetch("http://localhost:8000/health")
```

**The Fix:** Pull the API base URL from a Vite environment variable. Create a shared constant.

```tsx
// src/lib/api.ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
```

```tsx
// In App.tsx
import { API_BASE_URL } from "@/lib/api";
// ...
fetch(`${API_BASE_URL}/health`)
```

Add a `.env.example` (checked in) and `.env` (gitignored):
```
VITE_API_BASE_URL=http://localhost:8000
```

This is exactly the kind of thing that's easy to fix now and painful to fix after 30 files copy-paste the pattern. This is a scaffolding spec -- the whole point is setting patterns others will follow.

**Severity:** Serious

---

**Finding 2: Duplicate version string with no single source of truth** [Moderate]

**Impact:** The API version is defined in three places: `pyproject.toml` (`version = "0.1.0"`), `main.py` (`version="0.1.0"`), and `health.py` (`version="0.1.0"`). The tests also assert against the literal string `"0.1.0"`. When someone bumps the version (and they will), they'll update one or two of these and miss the third. The health endpoint will report a stale version, the tests will fail for the wrong reason, and someone will waste 20 minutes figuring out why.

**Location:** `backend/app/main.py:10`, `backend/app/routers/health.py:12`, `backend/tests/test_health.py:12`

**The Fix:** Define the version once and import it everywhere.

```python
# app/__init__.py
__version__ = "0.1.0"
```

```python
# app/main.py
from app import __version__
# ...
application = FastAPI(title="FutureProof API", version=__version__, ...)
```

```python
# app/routers/health.py
from app import __version__
# ...
return HealthResponse(status="ok", project="futureproof", version=__version__)
```

Not a ship-blocker, but it's a scaffolding spec -- this is the pattern everyone will copy. Get it right once now.

**Severity:** Moderate

---

**Finding 3: Health check has no actual health checking** [Minor]

**Impact:** The `/health` endpoint always returns `"ok"` regardless of system state. Right now this is fine -- it's a scaffold. But the spec mentions DuckDB as a dependency, and future specs will add Ollama/Gemma. If the health endpoint doesn't evolve to actually probe dependencies, your load balancer will happily route traffic to a backend that can't reach its database. I'm not saying fix this now. I'm saying: leave a breadcrumb so the next person knows this needs to grow.

**Location:** `backend/app/routers/health.py:9-14`

**The Fix (future):** No code change required now. The pattern should be established early so it's not retrofitted later when DuckDB/Ollama integration lands.

**Severity:** Minor (note for future specs)

---

**Finding 4: No fetch abort/cleanup in useEffect** [Minor]

**Impact:** If the App component unmounts while the health fetch is in-flight (unlikely now, guaranteed later with routing), you get a state update on an unmounted component. In React 19 this is less catastrophic than it used to be, but it's still sloppy -- and this is the pattern future API calls will copy from.

**Location:** `frontend/src/App.tsx:17-24`

**The Fix:**
```tsx
useEffect(() => {
  const controller = new AbortController();
  fetch(`${API_BASE_URL}/health`, { signal: controller.signal })
    .then((res) => {
      if (res.ok) setApiStatus("connected");
      else setApiStatus("disconnected");
    })
    .catch(() => {
      if (!controller.signal.aborted) setApiStatus("disconnected");
    });
  return () => controller.abort();
}, []);
```

**Severity:** Minor

#### What's Actually Good

I'll give credit where it's due. This is a solid scaffold.

- **CORS is properly scoped** to specific localhost origins, not the `allow_origins=["*"]` free-for-all I see in 90% of AI-generated FastAPI code. And it's tested.
- **TypeScript strict mode with `noUncheckedIndexedAccess`** -- most teams don't even know that flag exists. It catches real bugs.
- **mypy strict mode** on the backend. Good.
- **The test suite is genuinely useful** -- testing API contract shape, method restrictions, CORS preflight, content type. These aren't placeholder tests.
- **App factory pattern** (`create_app()`) makes testing clean from day one.
- **Pydantic v2 for the response model** -- correct per stack requirements.
- **Design tokens in CSS custom properties** with Tailwind integration -- the right architecture for a design system.

Claude did 80% of the work here. Unfortunately, it's the other 20% that causes outages.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

**Required Changes (route to implementation agent):**
1. **[Serious]** Extract hardcoded backend URL in `App.tsx` to env variable via `VITE_API_BASE_URL`. Create `src/lib/api.ts` with the constant. This sets the pattern for all future API calls.
2. **[Moderate]** Consolidate version string to single source of truth in `app/__init__.py`. Import in `main.py` and `health.py`.

**Non-blocking recommendations (address in future specs):**
3. Add AbortController cleanup to the health check useEffect.
4. Plan for real dependency health checks when DuckDB/Ollama are integrated.

---

## §9 Verification

**Status:** COMPLETE
**Verified:** 2026-04-04

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | PASS — All checks passed |
| Type check (mypy) | PASS — No issues found in 7 source files |
| Tests (pytest) | PASS — 8 passed in 0.01s |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | PASS — No type errors |
| Tests (vitest) | PASS — 5 tests passed |
| Production build (Vite) | PASS — 387 modules, built in ~1s |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | All 6 checks green after code review fixes |

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Lessons Learned
1. **Hatchling needs explicit package paths** when the directory name doesn't match the project name (app/ vs futureproof_backend/).
2. **TypeScript composite projects can't use noEmit** — must use emitDeclarationOnly instead.
3. **Existing design system files may have latent issues** (unused imports) that only surface under strict TypeScript. Fix minimally.
4. **Set patterns right in scaffolding** — the code review correctly identified that hardcoded URLs and version strings in scaffolding get copy-pasted everywhere.

### Follow-up Items
- Add `.gitignore` files (backend + frontend or root-level)
- Add AbortController cleanup to fetch pattern in App.tsx
- Plan health endpoint evolution when DuckDB/Ollama land
- Consider root-level task runner (Makefile/justfile)
