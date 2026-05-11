# Spec: `gemma-model-profiles`

**Spec ID:** B3
**Author:** Jeff (via Claude Desktop)
**Status:** ⬜ Not started
**Depends On:** B1 (`fastapi-router-wiring`)
**Priority:** High — must ship before frontend screens that call Gemma surfaces

---

## §1 Problem Statement

FutureProof has 10 distinct Gemma integration surfaces. On the 26B A4B model (cloud or beefy local hardware), all 10 can run concurrently with acceptable latency. On the E4B model (the Ollama demo target — a MacBook with 24 GB unified memory), parallel Gemma calls saturate the model and produce visible UI stalls. Students click away before results return.

The app needs to be model-aware: detect which Gemma variant is active, apply a pre-configured feature profile that prioritizes the highest-value Gemma surfaces and falls back to deterministic logic for the rest, and expose a settings UI so power users can override the defaults.

This is also a hackathon differentiator: "We didn't just ship Ollama support — we shipped intelligent degradation that makes the local experience feel fast."

---

## §2 Design Decisions

**DD-1: Model profiles, not manual toggles.** The system ships two named profiles (`26b` and `e4b`) with sensible defaults. Users can override individual toggles, but the profiles do the thinking for them.

**DD-2: E4B parallelism cap.** E4B profile caps concurrent Gemma calls at 2 (via `OLLAMA_NUM_PARALLEL`). If the UI fires a new interaction while both slots are occupied, the lowest-priority in-flight or queued call is cancelled and its surface immediately shows the deterministic fallback. The user never waits.

**DD-3: Deterministic-first on E4B.** Every Gemma surface already has a fallback path (spike validated this). The E4B profile simply makes fallback the *default* for low-priority surfaces, with Gemma available as an opt-in toggle.

**DD-4: Settings page is informational + toggles.** No model switching from the UI (that's an env var / Ollama concern). The settings page shows the active model, provider, and parallelism as read-only, plus the feature toggle grid.

**DD-5: Two always-on surfaces.** Intent resolution and SOC expansion cannot be disabled — they gate the core build flow. Everything else is toggleable.

**DD-6: Cancel-and-fallback, not queue-and-wait.** When a user clicks through the UI faster than Gemma can respond on E4B, the pending Gemma call is cancelled and the deterministic fallback renders immediately. The app should never feel like it's waiting.

---

## §3 Success Criteria

1. A full build on E4B completes with no user-perceptible stall (< 2s per screen transition for deterministic surfaces).
2. Settings page correctly displays active model, provider, and `OLLAMA_NUM_PARALLEL` value.
3. Toggling a Gemma feature off causes that surface to use its deterministic fallback on the next invocation — no restart required.
4. On E4B, clicking through screens faster than Gemma responds never blocks the UI; cancelled calls degrade gracefully.
5. On 26B, all surfaces are on by default and the parallelism display is hidden/grayed.
6. Profile defaults survive server restart (persisted in config, not in-memory only).

---

## §4 Gemma Surface Inventory & Priority Matrix

### Highest Priority (core build flow)

| Surface | Service | 26B Default | E4B Default | Lockable? | Fallback |
|---|---|---|---|---|---|
| Intent resolution (Set Your Course) | `cli.py` / intent router | ✅ On | ✅ On | 🔒 Always on | Deterministic CIP match from school programs + crosswalk keyword search |
| SOC expansion | `stat_engine.py` | ✅ On | ✅ On | 🔒 Always on | Title keyword match against candidate SOC pool |
| Build skeleton & career outcomes | `stat_engine.py` | ✅ On | ⬜ Off | Toggleable | Already deterministic — Gemma only adds prose |
| Skill pool generation | `skill_pool.py` | ✅ On | ✅ On | Toggleable | Existing static/default skill pool |
| Skill recommendations | `skill_recs.py` | ✅ On | ✅ On | Toggleable | Existing `_fallback_recs(career)` |

### Medium Priority (narrative polish)

| Surface | Service | 26B Default | E4B Default | Lockable? | Fallback |
|---|---|---|---|---|---|
| Compare insights / PDF insights | `builds.py`, `report_gen.py` | ✅ On | ⬜ Off | Toggleable | Compare winners/losers, stat deltas, existing PDF copy templates |
| Boss fight narratives | `boss_fights.py` | ✅ On | ⬜ Off | Toggleable | Existing `_fallback_narrative(fight)` — upgrade with career-specific numbers |
| Guidance / "Gemma's Take" | `guidance.py` | ✅ On | ⬜ Off | Toggleable | Existing `guidance._fallback_narrative(career, gauntlet)` |

### Low Priority (cut for E4B)

| Surface | Service | 26B Default | E4B Default | Lockable? | Fallback |
|---|---|---|---|---|---|
| Ask Gemma chat | `guidance.chat_with_context()` | ✅ On | ⬜ Off | Toggleable | Canned/explain actions with deterministic responses; general chat shows "limited mode" |
| Career description | `career_description.get_or_generate` | ✅ On | ⬜ Off | Toggleable | O*NET top activities list as plain bullets |
| Explain stat receipts | `receipts.py` | ✅ On | ⬜ Off | Toggleable | Template-based receipt from score components |
| Career-pick Q&A chips | Gemma canned questions | ✅ On | ⬜ Off | Toggleable | Existing fallback templates per chip |

**Summary:** 26B = 12/12 on. E4B = 4/12 on (2 locked + 2 toggleable).

---

## §5 UI/UX

### Settings Entry Point

A gear icon (⚙️) in the header bar, available from any screen. Tapping opens a slide-over panel (not a full page — the student should feel like they're adjusting a dial, not leaving the experience).

### Settings Panel Layout

**Section 1: Model Info (read-only)**

```
┌─────────────────────────────────────┐
│  🧠 Gemma Model                     │
│                                     │
│  Model:     gemma-4-e4b             │
│  Provider:  Ollama (local)          │
│  Parallel:  2                       │
│                                     │
│  ───────────────────────────────     │
│  Profile: E4B (optimized for speed) │
└─────────────────────────────────────┘
```

When 26B is active, the "Parallel" row shows "—" (grayed out) since 26B handles concurrency natively.

**Section 2: Gemma Features (toggles)**

Grouped by priority tier with a subtle divider. Each toggle shows the surface name and a one-line description. Locked surfaces (intent resolution, SOC expansion) show a lock icon and are non-interactive.

Toggle states: On (green) = Gemma generates. Off (muted) = deterministic fallback.

A "Reset to profile defaults" link at the bottom restores the active profile's default toggle states.

### E4B Cancel-and-Fallback UX

When a Gemma call is in-flight and the user navigates away (clicks a button, advances to the next screen), the pending call is cancelled. The surface that would have received the Gemma response instead shows its deterministic fallback with no loading spinner and no error state. From the student's perspective, the app just works — some text is templated rather than AI-generated, but the flow never stalls.

If Gemma returns before the user navigates, the AI-generated content replaces the fallback with a subtle fade transition (no flash, no layout shift).

---

## §6 Technical Spec

### New Files

| File | Purpose |
|---|---|
| `backend/app/services/model_profile.py` | Profile definitions, active profile detection, toggle state management |
| `backend/app/services/gemma_queue.py` | Concurrency-aware request queue with priority-based cancellation |
| `frontend/src/stores/settingsStore.ts` | Zustand store for settings panel state + toggle overrides |
| `frontend/src/components/SettingsPanel.tsx` | Settings slide-over component |

### Modified Files

| File | Change |
|---|---|
| `backend/app/services/gemma_client.py` | Add `is_surface_enabled(surface_id: str) -> bool` check; integrate with `gemma_queue.py` for concurrency control |
| `backend/app/models/career.py` | Add `GemmaProfile` and `GemmaSurfaceConfig` Pydantic models |
| All 10 Gemma surface call sites | Wrap each call: `if model_profile.is_enabled(surface_id): await gemma_call() else: fallback()` |
| `frontend/src/components/Header.tsx` | Add settings gear icon |

### `model_profile.py` Core Logic

```python
from enum import Enum
from pydantic import BaseModel

class GemmaModelSize(str, Enum):
    E4B = "e4b"
    A4B_26B = "26b-a4b"
    UNKNOWN = "unknown"

class SurfaceConfig(BaseModel):
    surface_id: str
    enabled: bool
    locked: bool = False  # True = always on, can't toggle
    priority: int  # 1=highest, 3=lowest — used for cancellation ordering

class GemmaProfile(BaseModel):
    model_size: GemmaModelSize
    max_parallel: int
    surfaces: dict[str, SurfaceConfig]

# Detect active model from Ollama /api/tags or INFERENCE_BACKEND env
def detect_active_model() -> GemmaModelSize: ...

# Return the profile with user overrides applied
def get_active_profile() -> GemmaProfile: ...

# Check if a specific surface should use Gemma
def is_surface_enabled(surface_id: str) -> bool: ...

# User toggles a surface on/off
def set_surface_override(surface_id: str, enabled: bool) -> None: ...

# Reset all overrides to profile defaults
def reset_to_defaults() -> None: ...
```

### Surface IDs (canonical keys)

```python
SURFACE_INTENT_RESOLUTION = "intent_resolution"       # 🔒 locked
SURFACE_SOC_EXPANSION = "soc_expansion"                # 🔒 locked
SURFACE_BUILD_SKELETON = "build_skeleton"
SURFACE_SKILL_POOL = "skill_pool"
SURFACE_SKILL_RECS = "skill_recs"
SURFACE_COMPARE_INSIGHTS = "compare_insights"
SURFACE_BOSS_NARRATIVES = "boss_narratives"
SURFACE_GUIDANCE = "guidance"
SURFACE_ASK_GEMMA = "ask_gemma"
SURFACE_CAREER_DESCRIPTION = "career_description"
SURFACE_EXPLAIN_RECEIPTS = "explain_receipts"
SURFACE_CAREER_QA_CHIPS = "career_qa_chips"
```

### `gemma_queue.py` Concurrency Control

```python
import asyncio

class GemmaQueue:
    """Priority-aware concurrency limiter for Gemma calls."""

    def __init__(self, max_parallel: int = 2):
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._in_flight: dict[str, asyncio.Task] = {}

    async def submit(
        self,
        surface_id: str,
        priority: int,
        coro,
        fallback_fn,
    ):
        """Submit a Gemma call. If at capacity, cancel lowest-priority
        in-flight task and return its fallback. If this call IS the
        lowest priority, skip Gemma entirely and return fallback."""
        ...

    def cancel_surface(self, surface_id: str):
        """Cancel an in-flight call (e.g., user navigated away).
        The caller should render the deterministic fallback."""
        ...
```

For 26B profile, `max_parallel` is set high enough to be effectively unlimited (e.g., 10). The queue logic still runs but never triggers cancellation.

### API Endpoints

| Endpoint | Method | Service Call | Returns |
|---|---|---|---|
| `/settings/profile` | `GET` | `model_profile.get_active_profile()` | `GemmaProfile` (model, provider, parallel, all surface configs) |
| `/settings/surface/{surface_id}` | `PATCH` | `model_profile.set_surface_override(id, enabled)` | `SurfaceConfig` (updated) |
| `/settings/reset` | `POST` | `model_profile.reset_to_defaults()` | `GemmaProfile` (reset) |

### Frontend TypeScript Types

```typescript
interface GemmaProfile {
  model_size: "e4b" | "26b-a4b" | "unknown";
  provider: "ollama" | "openrouter";
  max_parallel: number;
  surfaces: Record<string, SurfaceConfig>;
}

interface SurfaceConfig {
  surface_id: string;
  enabled: boolean;
  locked: boolean;
  priority: number;
  label: string;       // human-readable name
  description: string; // one-liner
  tier: "highest" | "medium" | "low";
}
```

### Zustand Store

```typescript
// frontend/src/stores/settingsStore.ts
interface SettingsState {
  profile: GemmaProfile | null;
  isOpen: boolean;
  toggleSurface: (surfaceId: string) => Promise<void>;
  resetToDefaults: () => Promise<void>;
  fetchProfile: () => Promise<void>;
  openSettings: () => void;
  closeSettings: () => void;
}
```

---

## §7 Model Detection Logic

On backend startup (and exposed via `GET /settings/profile`):

1. Check `INFERENCE_BACKEND` env var. If `openrouter`, model size comes from `OPENROUTER_MODEL` string (parse for `e4b`, `26b`, `31b`).
2. If `ollama`, query `GET http://localhost:11434/api/tags` → find the loaded model name → parse size variant.
3. If detection fails, default to `UNKNOWN` and apply the E4B profile (conservative).
4. Read `OLLAMA_NUM_PARALLEL` from env (default 1 if unset). Display in settings.

---

## §8 E4B Behavioral Rules

**Rule 1: Max 2 concurrent Gemma calls.** Enforced by `GemmaQueue` semaphore.

**Rule 2: Priority-based cancellation.** When a third Gemma call is requested and both slots are full, the lowest-priority in-flight call is cancelled. Priority order (1 = highest, never cancelled):

1. Intent resolution, SOC expansion (locked — always win)
2. Skill pool, Skill recs
3. Build skeleton prose, Boss narratives, Guidance
4. Compare insights, Ask Gemma, Career description, Receipts, Q&A chips

**Rule 3: Navigate-away cancellation.** When the frontend detects screen transition while Gemma calls are in-flight for the current screen, it fires `cancel_surface(id)` for each. The backend cancels the asyncio tasks. The frontend renders deterministic fallback immediately — no spinner, no error, no flash.

**Rule 4: Late arrival replacement.** If Gemma returns *after* the fallback is displayed but *before* the user leaves the screen, the AI content fades in to replace the fallback (300ms Framer Motion crossfade). No layout shift.

**Rule 5: Intent resolution gets JSON-only mode on E4B.** No rich streaming prose — just the structured CIP match JSON. For "not expected" results, prefer deterministic clarification options first; Gemma only if the deterministic path yields zero matches.

---

## §9 Test Matrix

| Scenario | Expected Behavior | Profile |
|---|---|---|
| Boot with E4B Ollama, no overrides | 4 surfaces on, 8 off, parallel = 2 | E4B |
| Boot with 26B OpenRouter, no overrides | 12 surfaces on, parallel display hidden | 26B |
| Toggle boss narratives on (E4B) | Boss fights use Gemma narratives on next gauntlet | E4B |
| Toggle guidance off (26B) | Guidance falls back to `_fallback_narrative` | 26B |
| Fire 3 Gemma calls simultaneously (E4B) | Lowest-priority call cancelled, fallback rendered | E4B |
| Navigate away during in-flight Gemma call | Call cancelled, fallback shown, no spinner | E4B |
| Gemma returns after fallback displayed | AI content fades in (300ms), no layout shift | E4B |
| Reset to defaults after overrides | All toggles return to profile defaults | Both |
| Ollama not running | Detection fails → UNKNOWN → E4B profile applied | — |
| Toggle locked surface (intent resolution) | Toggle is non-interactive, lock icon displayed | Both |
| `OLLAMA_NUM_PARALLEL` unset | Display shows "1" | E4B |
| All surfaces manually enabled on E4B | Works, but queue cancellation fires frequently — user's choice | E4B |

---

## §10 Design Decisions Log

| Decision | Rationale | Alternative Considered |
|---|---|---|
| Two named profiles, not per-surface config | Students don't know which surfaces matter. Profiles are opinionated. | Flat toggle list with no grouping — too much cognitive load |
| Cancel lowest-priority, not FIFO | Preserves the most important Gemma outputs | FIFO queue — would cancel intent resolution if it came in third |
| Settings as slide-over, not full page | Student shouldn't feel like they left the experience | Full settings page — breaks flow |
| Read-only model info | Switching models is an infra concern, not a UI concern | Model selector dropdown — wrong abstraction layer |
| Conservative default (E4B profile on detection failure) | Better to be fast with fallbacks than to stall on a slow model | Default to 26B — risks timeouts on weak hardware |
| Persist overrides to config file, not just memory | Overrides survive server restart; important for school deployments | In-memory only — lost on restart |

---

## §11 Claude Code Prompt

```
Read the spec at docs/specs/gemma-model-profiles.md in full.

Implement in this order:

1. Create backend/app/services/model_profile.py:
   - GemmaModelSize enum, SurfaceConfig model, GemmaProfile model
   - PROFILES dict with "e4b" and "26b-a4b" default configurations
   - detect_active_model() — check INFERENCE_BACKEND env, query Ollama /api/tags if needed
   - get_active_profile() — return profile with any user overrides applied
   - is_surface_enabled(surface_id) — single bool check used by all services
   - set_surface_override() / reset_to_defaults() — persist to config JSON file
   - Surface ID constants as module-level strings

2. Create backend/app/services/gemma_queue.py:
   - GemmaQueue class with asyncio.Semaphore
   - submit(surface_id, priority, coro, fallback_fn) — priority-based cancellation
   - cancel_surface(surface_id) — cancel in-flight task by surface
   - Initialize with max_parallel from active profile

3. Update backend/app/services/gemma_client.py:
   - Import model_profile and gemma_queue
   - Add surface-aware wrapper: check is_surface_enabled() before calling Gemma
   - Route all Gemma calls through GemmaQueue.submit()

4. Update all 10 Gemma surface call sites in the service layer:
   - Each call site should use the pattern:
     if model_profile.is_surface_enabled(SURFACE_ID):
         result = await gemma_queue.submit(SURFACE_ID, priority, gemma_coro, fallback_fn)
     else:
         result = fallback_fn()
   - Locate each by searching for gemma_client calls in:
     cli.py, stat_engine.py, skill_pool.py, skill_recs.py, builds.py,
     report_gen.py, boss_fights.py, guidance.py, career_description.py,
     receipts.py, and any career Q&A chip handlers

5. Add 3 FastAPI endpoints to the router (after B1 is wired):
   - GET /settings/profile
   - PATCH /settings/surface/{surface_id}
   - POST /settings/reset

6. Add GemmaProfile and SurfaceConfig to backend/app/models/career.py

7. Test: run `uv run python backend/cli.py` with INFERENCE_BACKEND=ollama
   and verify that disabled surfaces return fallback content instantly.

Do NOT modify the frontend — that is a separate spec.
Reference gemma_client.py for the existing inference backend pattern.
Reference the PRD at docs/futureproof_hackathon_prd_v8.md for service layer details.
```
