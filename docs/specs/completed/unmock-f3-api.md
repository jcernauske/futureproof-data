# Spec F3.1: Unmock API — Wire F3 Screens to Live Backend

**Spec ID:** F3.1
**File:** `docs/specs/unmock-f3-api.md`
**Scope:** Remove mock API dependency from F3 screens. Verify frontend ↔ backend integration end-to-end.
**Depends on:** F3 (implemented), B1 (implemented)
**Blocks:** Nothing — all subsequent specs (F4+) inherit the live API pattern.

-----

## What This Spec Does

F3 shipped with `VITE_USE_MOCK_API` defaulting to `true`. The real API client code in `frontend/src/api/build.ts` is already wired to the correct backend endpoints (`/build/outcomes`, `/build/tier`, `/build`). This spec:

1. Flips the default to `false` so the frontend hits the live FastAPI backend
2. Fixes any type mismatches or field mapping issues discovered at integration time
3. Removes `mockBuild.ts` and the mock toggle once live API is verified
4. Adds a `.env` file with `VITE_API_BASE_URL=http://localhost:8000`

-----

## Prerequisites

Before running this spec, the backend must be running:

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start the MCP server (Brightsmith Gold data)
cd ~/code/bright/futureproof-data
uv run python -m brightsmith.mcp_server  # or however MCP starts

# Terminal 3: Start FastAPI
cd ~/code/bright/futureproof-data
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Start frontend dev server
cd ~/code/bright/futureproof-data/frontend
npm run dev
```

Verify backend is alive: `curl http://localhost:8000/health` should return `{"status": "ok"}`.

-----

## Execution Checklist

### Step 1: Flip the toggle

In `frontend/src/api/build.ts`, change:

```typescript
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API !== "false";
```

to:

```typescript
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";
```

This makes live API the default. Developers can still opt into mocks with `VITE_USE_MOCK_API=true` in `.env.local`.

### Step 2: Add `.env` if missing

Create `frontend/.env` (if it doesn't exist):

```
VITE_API_BASE_URL=http://localhost:8000
```

Ensure `frontend/.env` is in `.gitignore`.

### Step 3: Integration smoke test

With all services running, walk the full F3 flow in the browser:

| Step | Action | Expected | Fix If Broken |
|------|--------|----------|---------------|
| 1 | Land on `/career-pick` with school + major in store | `POST /build/outcomes` fires | Check unitid/cipcode being passed from buildInputStore |
| 2 | Outcomes return | `POST /build/tier` fires with the outcomes | Check that outcomes array serializes correctly in TierRequest |
| 3 | Tiers render | Three sections with career cards | Check tier key names (`common`, `less_common`, `stretch`) match backend response |
| 4 | Pick a career, click CTA | `POST /build` fires, loading screen appears | Check all 11 BuildRequest fields are populated from stores |
| 5 | Build returns | Reveal screen renders with pentagon + Gemma's Take | Check Build response shape maps to RevealScreen props |
| 6 | Stat tutorial | Shows on first build, skips on repeat | Frontend-only — should work regardless of API |

### Step 4: Fix type mismatches

If any field mapping issues surface (likely candidates below), fix them in `frontend/src/types/build.ts`:

**Known risk areas** (from arch review C1):
- `CareerOutcome.top_5_activities` — backend returns `list[dict]` with `{activity, score}`, frontend may expect `string[]`
- `CareerOutcome.burnout_drivers` — same pattern
- `CareerOutcome.data_caveat` — backend may return `dict | null`, frontend may expect `string | null`
- `Build.skill_recs` — backend returns `SkillRec[]` objects, check frontend handles the object shape
- `Build.created_at` — backend includes it, frontend may not reference it yet (harmless if unused)

For each mismatch found:
1. Read the actual backend response shape (hit the endpoint with curl or check `/docs`)
2. Update the TypeScript interface to match
3. Update any component that renders the field

### Step 5: Remove mock infrastructure (optional — do if time permits)

Once live API is verified:
- Delete `frontend/src/api/mockBuild.ts`
- Remove mock imports and `USE_MOCK` branches from `frontend/src/api/build.ts`
- Remove `VITE_USE_MOCK_API` references from any docs

If you want to keep mocks for CI/testing where no backend runs, leave them but gate behind `NODE_ENV === 'test'` instead of an env var.

### Step 6: Verify tests still pass

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

Component tests that rely on mock data fixtures (not `mockBuild.ts`) should still pass. Tests that import from `mockBuild.ts` need their imports updated if Step 5 was executed.

-----

## What NOT to Do

- Do not change any backend code. This is frontend-only.
- Do not change component logic or UI. This is an API wiring fix, not a feature change.
- Do not refactor the API client pattern. `apiPost`/`apiGet` in `client.ts` are correct and sufficient.
- Do not add error boundary components or retry logic — that's polish, not integration.

-----

## Acceptance Criteria

- [x] `VITE_USE_MOCK_API` defaults to `false` (live API)
- [x] Career pick screen loads real career outcomes from `/build/outcomes`
- [x] Tiering renders from `/build/tier` response — required `normalizeTiers()` mapping (backend keys differ from spec)
- [x] Full build creation via `POST /build` returns a real `Build` object — verified 2026-04-17 with Ollama (Stanford/CS, 31s round-trip, 731-char Gemma guidance)
- [x] Reveal screen renders with live data (pentagon, Gemma's Take, career detail) — Build response shape matches frontend types (tsc + vitest green)
- [x] No TypeScript errors with real API response shapes
- [x] Frontend tests pass (2 pre-existing failures in ProfileScreen unrelated to F3)
- [x] Frontend production build succeeds

-----

*— End of Spec F3.1 —*
