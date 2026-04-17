# Spec B1: FastAPI Router Wiring

**Spec ID:** B1
**File:** `docs/specs/fastapi-router-wiring.md`
**Scope:** Wire FastAPI routers to the existing service layer. No new business logic — this is plumbing.
**Depends on:** Nothing (first backend spec)
**Blocked by this:** Every frontend spec (F1–F7), B2

-----

## What This Spec Does

Creates FastAPI router modules that expose the existing service layer as a JSON API. Every endpoint calls an existing service function and returns an existing Pydantic model (or a thin wrapper). The CLI (`backend/cli.py`) is the reference implementation — every CLI function maps to one or more endpoints.

This spec also creates the `intent.py` service to extract the Gemma intent resolution logic currently embedded in `cli.py._prompt_major_gemma_intent()` into a proper service module. This is the only piece of "new" code, and it's a refactor, not new business logic.

-----

## Guiding Principles

1. **No new business logic.** Routers are pass-through. If a router needs to orchestrate multiple service calls, that orchestration already exists in `cli.py` — extract it into a service function if it isn't one already.
2. **Pydantic models are the API contract.** `backend/app/models/career.py` defines all response shapes. Routers return these models directly. FastAPI serializes them.
3. **CORS enabled.** The React frontend runs on a different port during development. Add `CORSMiddleware` with permissive origins for dev, configurable for production.
4. **Consistent error handling.** Every endpoint returns structured error responses, not bare 500s. Use FastAPI's `HTTPException` with meaningful detail strings.
5. **No auth.** Profile names are the identity layer. No tokens, no sessions, no middleware.

-----

## File Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, CORS, router includes
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── profile.py             # POST /profile, GET /profile/{name}, POST /profile/reroll
│   │   ├── schools.py             # GET /schools, GET /schools/{unitid}/programs
│   │   ├── intent.py              # POST /intent
│   │   ├── builds.py              # POST /build, POST /build/{id}/save, POST /builds/compare
│   │   ├── gauntlet.py            # POST /build/{id}/gauntlet, POST /build/{id}/reroll
│   │   ├── guidance.py            # POST /build/{id}/guidance, POST /build/{id}/chat, POST /build/{id}/next-steps
│   │   ├── branches.py            # GET /branches/{soc}, GET /tree/{soc}
│   │   ├── skills.py              # POST /build/{id}/skill-recs, GET /build/{id}/skill-pool
│   │   ├── wrapped.py             # GET /build/{id}/wrapped
│   │   └── reports.py             # GET /build/{id}/report
│   ├── services/
│   │   ├── intent.py              # NEW — extracted from cli.py
│   │   └── ... (all 16 existing services unchanged)
│   └── models/
│       ├── career.py              # UNCHANGED — existing Pydantic models
│       └── api.py                 # NEW — request body models for POST endpoints
```

-----

## New File: `backend/app/models/api.py`

Request body models for POST endpoints. These are thin — they capture what the frontend sends, not what the service returns.

```python
from pydantic import BaseModel
from typing import Optional


class IntentRequest(BaseModel):
    """POST /intent"""
    school_name: str
    unitid: int
    major_text: str
    programs: list[dict]  # school's program list from GET /schools/{unitid}/programs


class IntentConfirmRequest(BaseModel):
    """POST /intent/confirm"""
    school_name: str
    unitid: int
    major_text: str
    matched_cip: str
    matched_title: str


class BuildRequest(BaseModel):
    """POST /build"""
    profile_name: str
    school_name: str
    unitid: int
    cipcode: str
    cip_title: str
    major_text: str
    effort: str  # "working" | "balanced" | "all_in"
    loan_pct: float  # 0.0 | 0.25 | 0.50 | 0.75 | 1.0
    selected_soc: str  # SOC code of the career the student picked
    selected_title: str  # occupation title


class RerollRequest(BaseModel):
    """POST /build/{id}/reroll"""
    boss_id: str  # which boss fight to rescore
    skill_ids: list[str]  # IDs of skills to apply from the pool


class ChatRequest(BaseModel):
    """POST /build/{id}/chat"""
    message: str
    history: list[dict] = []  # prior turns: [{"role": "user"|"assistant", "content": "..."}]


class CompareRequest(BaseModel):
    """POST /builds/compare"""
    build_ids: list[str]  # 2-3 build IDs to compare


class ProfileLookupRequest(BaseModel):
    """POST /profile/lookup (fuzzy search)"""
    name_query: str
```

-----

## New Service: `backend/app/services/intent.py`

Extracts the Gemma intent resolution pipeline from `cli.py._prompt_major_gemma_intent()`. The CLI currently runs three Gemma calls inline (intent resolution → audit → optional clarification). This service encapsulates that flow.

### Functions to Extract

```python
async def resolve_intent(
    major_text: str,
    school_name: str,
    unitid: int,
    programs: list[dict],
    gemma_client: GemmaClient,
    mcp_client: MCPClient,
) -> IntentResult:
    """
    Maps free-text major input to a CIP code.
    
    Returns IntentResult with:
    - matched_cip: str
    - matched_title: str
    - confidence: str ("high" | "medium" | "low")
    - careers_preview: list[str]  # top 3-5 career titles for confirmation
    - audit_flag: str | None  # "adversarial" | "joke" | "vague" | None
    - audit_message: str | None  # Gemma's audit response if flagged
    - needs_clarification: bool
    - alternatives: list[dict] | None  # if clarification needed
    """
    # 1. Call Gemma for intent resolution (match major_text → CIP)
    # 2. Call Gemma for audit (adversarial/joke detection)
    # 3. If ambiguous, return needs_clarification=True with alternatives
    # 4. Look up career previews from crosswalk for the matched CIP
    pass


async def confirm_intent(
    matched_cip: str,
    school_name: str,
    unitid: int,
    cache: dict,
) -> None:
    """Cache a confirmed intent mapping for instant re-resolution."""
    pass
```

### New Pydantic Model: `IntentResult`

Add to `backend/app/models/career.py`:

```python
class IntentResult(BaseModel):
    matched_cip: str
    matched_title: str
    confidence: str  # "high" | "medium" | "low"
    careers_preview: list[str]
    audit_flag: str | None = None
    audit_message: str | None = None
    needs_clarification: bool = False
    alternatives: list[dict] | None = None
```

### Extraction Rules

- Read `cli.py._prompt_major_gemma_intent()` line by line.
- Every Gemma prompt string, every response parser, every fallback — moves into `intent.py`.
- The CLI's Rich console output (prompts, tables, confirmations) stays in the CLI. Only the data flow moves.
- The cache dict is currently in-memory in the CLI. For the API, use a module-level dict (sufficient for hackathon; no Redis needed).
- If the CLI uses `gemma_client` directly for intent resolution, the service wraps those same calls.

-----

## Router Specifications

### `routers/profile.py`

Spec B2 defines the profile service. This router is the API surface for it.

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `POST` | `/profile` | `profile.generate_name()` | — (no body) | `{"profile_name": str, "animal_emoji": str}` | Auto-generates name, collision-checked |
| `POST` | `/profile/reroll` | `profile.generate_name()` | `{"current_name": str}` | `{"profile_name": str, "animal_emoji": str}` | Same as generate but excludes current |
| `POST` | `/profile/lookup` | `profile.lookup(name_query)` | `ProfileLookupRequest` | `{"profile_name": str, "builds": list}` or 404 | Case-insensitive fuzzy match |

### `routers/schools.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `GET` | `/schools?q={query}` | `school_lookup.search_schools(query)` | Query param `q` | `list[SchoolMatch]` | Fuzzy search, return top 10 |
| `GET` | `/schools/{unitid}/programs` | `school_lookup.get_programs(unitid)` | Path param | `list[Program]` | Programs offered by this school |

### `routers/intent.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `POST` | `/intent` | `intent.resolve_intent()` | `IntentRequest` | `IntentResult` | Gemma maps major text → CIP. Returns match + audit + preview. |
| `POST` | `/intent/confirm` | `intent.confirm_intent()` | `IntentConfirmRequest` | `{"cached": true}` | Cache confirmed mapping |

### `routers/builds.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `POST` | `/build` | Orchestration (see below) | `BuildRequest` | `Build` | The big one. Creates a full build. |
| `POST` | `/build/{id}/save` | `builds.save_build(build)` | Path param (build in memory) | `{"build_id": str, "path": str}` | Persist to disk |
| `GET` | `/build/{id}` | `builds.load_build(id)` | Path param | `Build` | Load a saved build |
| `POST` | `/builds/compare` | `builds.compare_builds(ids)` | `CompareRequest` | Compare result dict | Risk comparison data |

**`POST /build` orchestration** — mirrors `cli.py._build_full()`:

```python
# 1. stat_engine.compute_pentagon(unitid, cipcode, selected_soc, effort, loan_pct)
# 2. career_tiering.tier_careers(outcomes, school_name, cip_title) 
# 3. Student has already picked a career (selected_soc in request body)
# 4. boss_fights.run_gauntlet(career)
# 5. branch_tree.get_branches(selected_soc)
# 6. skill_recs.generate_recs(career, gauntlet)
# 7. skill_pool.generate_pool(career, gauntlet)
# 8. guidance.generate_guidance(career, gauntlet, school_name)
# 9. Assemble Build model
```

**Design decision:** The frontend calls `POST /build` after the student has already picked a career from the tiered list. The tiering happens as part of the stat engine response — the frontend needs career outcomes + tiers to show the picker. So `POST /build` actually needs to be split:

| Step | Endpoint | What Happens |
|---|---|---|
| 1. Compute outcomes | `POST /build/outcomes` | `stat_engine.compute_pentagon()` → returns all `CareerOutcome[]` for this school+major+effort+loan |
| 2. Tier outcomes | `POST /build/tier` | `career_tiering.tier_careers(outcomes)` → returns tiered grouping |
| 3. Create build | `POST /build` | Student picked a career → gauntlet + branches + skills + guidance → returns full `Build` |

This matches the UX flow: Screen 4 (sliders) → Screen 5 (career pick from tiers) → Screen 6 (reveal). The frontend needs outcomes before the student picks.

**Revised router:**

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `POST` | `/build/outcomes` | `stat_engine.compute_pentagon()` | `{unitid, cipcode, effort, loan_pct}` | `list[CareerOutcome]` | All career outcomes for this school+major |
| `POST` | `/build/tier` | `career_tiering.tier_careers()` | `{outcomes: list, school_name: str, cip_title: str}` | `{"common": list, "less_common": list, "stretch": list}` | Gemma-tiered grouping |
| `POST` | `/build` | Full build assembly | `BuildRequest` | `Build` | Gauntlet + branches + skills + guidance |
| `POST` | `/build/{id}/save` | `builds.save_build()` | — | `{"build_id": str}` | Persist |
| `GET` | `/build/{id}` | `builds.load_build()` | — | `Build` | Load saved |
| `POST` | `/builds/compare` | `builds.compare_builds()` | `CompareRequest` | Compare result | Risk comparison |

### `routers/gauntlet.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `POST` | `/build/{id}/gauntlet` | `boss_fights.run_gauntlet()` | Build from memory/disk | `GauntletResult` | Run all 6 boss fights |
| `POST` | `/build/{id}/reroll` | `skill_pool.apply_skills()` + `boss_fights.rescore_fight()` | `RerollRequest` | `BossFightResult` | Rescore one fight after equipping skills |

**Note:** The gauntlet is already run as part of `POST /build`. This standalone endpoint exists for the case where the frontend needs to re-run or the build was loaded from save without gauntlet data. In practice, the primary reroll flow uses `POST /build/{id}/reroll`.

### `routers/guidance.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `POST` | `/build/{id}/guidance` | `guidance.generate_guidance()` | Build from memory | `{"narrative": str, "receipts": dict}` | Gemma's Take |
| `POST` | `/build/{id}/chat` | `guidance.chat_with_context()` | `ChatRequest` | `{"response": str}` | Ask Gemma (multi-turn) |
| `POST` | `/build/{id}/next-steps` | `next_steps.generate_next_steps()` | Build from memory | `{"checklist": str}` | Post-gauntlet action items |

### `routers/branches.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `GET` | `/branches/{soc}` | `branch_tree.get_branches()` | Path param | `list[CareerBranch]` | Stage 3 branches for a career |
| `GET` | `/tree/{soc}` | `career_tree.build_tree()` | Path param + query params | Nested tree dict | Multi-level tree expansion |

### `routers/skills.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `GET` | `/build/{id}/skill-recs` | `skill_recs.generate_recs()` | Build from memory | `list[SkillRec]` | Post-build recommendations |
| `GET` | `/build/{id}/skill-pool` | `skill_pool.generate_pool()` | Build from memory | `list[AppliedSkill]` | Reroll skill options |

### `routers/wrapped.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `GET` | `/build/{id}/wrapped` | Puppeteer render pipeline | Build from memory | `{"frames": list[str]}` | URLs to rendered frame PNGs |

**Implementation note:** Puppeteer rendering is a separate concern. This router is a placeholder — the endpoint exists so the frontend can call it, but the Puppeteer pipeline is out of scope for B1. Return a stub response with frame template URLs for now. The real rendering ships with F6.

### `routers/reports.py`

| Method | Path | Service Call | Request | Response | Notes |
|---|---|---|---|---|---|
| `GET` | `/build/{id}/report` | `report_gen.generate_report()` | Build from memory | `{"markdown": str}` | Markdown build report |
| `GET` | `/builds/compare/report` | `report_gen.generate_comparison_report()` | Query params: build IDs | `{"markdown": str}` | Comparison report |

-----

## Build State Management

The CLI keeps builds in memory as Python objects. The API needs the same capability — a build created by `POST /build` must be accessible by subsequent calls to `/build/{id}/gauntlet`, `/build/{id}/reroll`, etc.

### Approach: In-Memory Build Store

```python
# backend/app/state.py
from backend.app.models.career import Build

_builds: dict[str, Build] = {}

def store_build(build: Build) -> str:
    _builds[build.build_id] = build
    return build.build_id

def get_build(build_id: str) -> Build | None:
    return _builds.get(build_id)

def update_build(build_id: str, build: Build) -> None:
    _builds[build_id] = build
```

This is a module-level dict. Sufficient for hackathon (single server process). Builds persist across requests but not across server restarts — that's what `POST /build/{id}/save` (disk persistence via `builds.py`) is for.

**On server startup**, optionally load saved builds from the `builds/` directory into the store.

-----

## `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import (
    profile, schools, intent, builds, gauntlet,
    guidance, branches, skills, wrapped, reports,
)

app = FastAPI(
    title="FutureProof API",
    version="0.1.0",
    description="RPG-style college decision engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/profile", tags=["Profile"])
app.include_router(schools.router, prefix="/schools", tags=["Schools"])
app.include_router(intent.router, prefix="/intent", tags=["Intent"])
app.include_router(builds.router, prefix="/build", tags=["Builds"])
app.include_router(gauntlet.router, prefix="/build", tags=["Gauntlet"])
app.include_router(guidance.router, prefix="/build", tags=["Guidance"])
app.include_router(branches.router, tags=["Branches"])
app.include_router(skills.router, prefix="/build", tags=["Skills"])
app.include_router(wrapped.router, prefix="/build", tags=["Wrapped"])
app.include_router(reports.router, tags=["Reports"])


@app.get("/health")
async def health():
    return {"status": "ok"}
```

-----

## Endpoint Summary (Complete)

Final count: **20 endpoints** (including health check).

| # | Method | Path | Router | Service |
|---|---|---|---|---|
| 1 | `GET` | `/health` | main | — |
| 2 | `POST` | `/profile` | profile | `profile.generate_name()` |
| 3 | `POST` | `/profile/reroll` | profile | `profile.generate_name()` |
| 4 | `POST` | `/profile/lookup` | profile | `profile.lookup()` |
| 5 | `GET` | `/schools?q=` | schools | `school_lookup.search_schools()` |
| 6 | `GET` | `/schools/{unitid}/programs` | schools | `school_lookup.get_programs()` |
| 7 | `POST` | `/intent` | intent | `intent.resolve_intent()` |
| 8 | `POST` | `/intent/confirm` | intent | `intent.confirm_intent()` |
| 9 | `POST` | `/build/outcomes` | builds | `stat_engine.compute_pentagon()` |
| 10 | `POST` | `/build/tier` | builds | `career_tiering.tier_careers()` |
| 11 | `POST` | `/build` | builds | Full build assembly |
| 12 | `POST` | `/build/{id}/save` | builds | `builds.save_build()` |
| 13 | `GET` | `/build/{id}` | builds | `builds.load_build()` |
| 14 | `POST` | `/builds/compare` | builds | `builds.compare_builds()` |
| 15 | `POST` | `/build/{id}/gauntlet` | gauntlet | `boss_fights.run_gauntlet()` |
| 16 | `POST` | `/build/{id}/reroll` | gauntlet | `skill_pool.apply_skills()` + rescore |
| 17 | `POST` | `/build/{id}/guidance` | guidance | `guidance.generate_guidance()` |
| 18 | `POST` | `/build/{id}/chat` | guidance | `guidance.chat_with_context()` |
| 19 | `POST` | `/build/{id}/next-steps` | guidance | `next_steps.generate_next_steps()` |
| 20 | `GET` | `/branches/{soc}` | branches | `branch_tree.get_branches()` |
| 21 | `GET` | `/tree/{soc}` | branches | `career_tree.build_tree()` |
| 22 | `GET` | `/build/{id}/skill-recs` | skills | `skill_recs.generate_recs()` |
| 23 | `GET` | `/build/{id}/skill-pool` | skills | `skill_pool.generate_pool()` |
| 24 | `GET` | `/build/{id}/wrapped` | wrapped | Puppeteer (stub) |
| 25 | `GET` | `/build/{id}/report` | reports | `report_gen.generate_report()` |
| 26 | `GET` | `/builds/compare/report` | reports | `report_gen.generate_comparison_report()` |

-----

## Execution Checklist

Claude Code should execute in this order:

1. **Read `backend/cli.py`** — understand every service call, every Gemma prompt, every data flow.
2. **Read `backend/app/models/career.py`** — understand all Pydantic models.
3. **Read each service in `backend/app/services/`** — understand function signatures and return types.
4. **Create `backend/app/models/api.py`** — request body models.
5. **Create `backend/app/services/intent.py`** — extract intent resolution from CLI.
6. **Create `backend/app/state.py`** — in-memory build store.
7. **Create `backend/app/routers/__init__.py`** — empty.
8. **Create each router file** — one at a time, in the order listed above.
9. **Create `backend/app/main.py`** — FastAPI app with all router includes.
10. **Verify** — `uvicorn backend.app.main:app --reload` starts without errors. Hit `/health` and `/docs`.

### What NOT to Do

- Do not modify any existing service file. If a service function's signature doesn't match what the router needs, add a thin wrapper in the router or in a new service — do not change the original.
- Do not modify `backend/app/models/career.py` except to add `IntentResult`. Existing models are the contract.
- Do not add authentication, rate limiting, or database connections. This is hackathon plumbing.
- Do not implement the Puppeteer rendering pipeline. Stub the endpoint.
- Do not create tests in this spec. Tests come with the frontend specs that exercise the API.

-----

## Acceptance Criteria

- [x] `uvicorn backend.app.main:app` starts without import errors
- [x] `/health` returns `{"status": "ok"}`
- [x] `/docs` shows all 26 endpoints with correct request/response schemas
- [x] `GET /schools?q=iowa` returns school matches (calls existing `school_lookup.search_schools`)
- [ ] `POST /intent` with a school + major text returns an `IntentResult` (requires Gemma/Ollama running)
- [ ] `POST /build/outcomes` returns `CareerOutcome[]` for a valid school+CIP
- [ ] `POST /build` assembles a full `Build` object and stores it in memory
- [ ] `POST /build/{id}/reroll` rescores a fight after applying skills
- [ ] `POST /build/{id}/chat` returns a Gemma response with build context
- [x] Profile endpoints work (B2 implemented alongside B1)
- [x] CORS headers present on all responses

-----

*— End of Spec B1 —*
