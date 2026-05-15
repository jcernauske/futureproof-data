# Conditional Build Loading Screen — Cloud vs Local

**Status:** Proposed
**Scope:** Frontend only — one file, one conditional.
**Touches:** `frontend/src/screens/BuildResultsScreen.tsx`

---

## Problem

The `/set-your-course` → `/my-build` transition currently blocks behind a full-screen `BuildLoadingScreen` until the SSE stream emits `done`. Before we supported `gemma4:e4b` on Ollama, the page rendered as soon as the `skeleton` event arrived and subsequent events (`boss_narrative`, `skill_recs`, `skill_pool`, `guidance`) streamed into the live UI through existing inline placeholders. The full-screen loader was added because cumulative E4B latency made that streaming-in behavior look broken on local hardware.

That justification doesn't apply on OpenRouter, where Gemma-26B is fast enough that streaming-into-UI feels alive. We want the old behavior back — but only on cloud.

---

## Change

In `BuildResultsScreen.tsx`, replace the loader gate (currently around line 733):

**Before:**
```tsx
{(isBuilding || !build) ? ( <BuildLoadingScreen ... /> ) : ( <ResultsPage /> )}
```

**After:**
```tsx
const showLoadingScreen = error
  ? true                                  // errors always go through the loader's retry UI
  : inferenceBackend === "openrouter"
    ? !build                              // cloud: gate only until skeleton arrives
    : (isBuilding || !build);             // ollama / unknown: keep full-stream gate

{showLoadingScreen ? ( <BuildLoadingScreen ... /> ) : ( <ResultsPage /> )}
```

`inferenceBackend` is already read at `BuildResultsScreen.tsx:146` via `useInferenceStore`, which polls `/health` (no new wiring needed).

### Why the three branches

- **`error` → loader.** `BuildLoadingScreen` owns the retry/back UI. Without this branch, a late-stream failure on cloud (after `skeleton`) would leave the user on a partial page with no error visible.
- **`openrouter` → `!build`.** Hide the loader the moment `skeleton` arrives. Subsequent events flow into the rendered page through existing `updateBuild` / `setFights` / `skillPoolLoading` paths.
- **`ollama` / `unknown` → unchanged.** Byte-identical to today's behavior. Treating `"unknown"` (pre-`/health`) as Ollama-safe is the conservative default.

---

## Out of Scope

- No backend changes. `/health` already exposes `inference_backend`.
- No new env vars, feature flags, or user-facing toggles.
- No changes to `BuildLoadingScreen`, the SSE protocol, or the fallback-to-blocking-POST path.
- Reachability (`model_reachable: false`) handling is unchanged.

---

## Verification

Manual, end-to-end:

1. **Cloud** — `INFERENCE_BACKEND=openrouter`, restart backend, hard-refresh frontend. Loader appears briefly through the skeleton round-trip, then the results page renders with empty narrative / skill / guidance surfaces that fill in incrementally as events arrive.
2. **Local** — `INFERENCE_BACKEND=ollama`, restart backend. Full loader stays mounted through `done` event. Unchanged from today.
3. **Error path** — kill backend mid-stream. After fallback POST also fails, loader returns with retry button regardless of backend.

No new automated tests required. Existing pytest / vitest / ruff / mypy / tsc suites are untouched.

---

## Risk

**Blast radius:** one file, one render condition. Ollama UX is byte-identical to today.

**Largest risk:** the results page has grown since the loader was added — some surface (`PentagonChart`, `BossBand`, `FinancesCard`, `GemmaSummary`, etc.) may now assume a fully-populated `build` and break/look ugly on cloud while events stream in. Mitigation: the cloud verification step is a visual audit; any broken surface can be fixed in isolation without affecting local. The presence of `skillPoolLoading` and per-fight narrative merge logic is a strong tell that partial-state rendering still works, but isn't a guarantee.

**Cosmetic cost:** empty narrative / skill cards become visible on cloud for the few seconds while events arrive. This is the intent of the change, but if a placeholder looks ugly, it'll be seen.

---

## Rollback

One-line revert. Restore the original gate:

```tsx
{(isBuilding || !build) ? ( <BuildLoadingScreen ... /> ) : ( <ResultsPage /> )}
```

`useInferenceStore` continues to power unrelated cloud-vs-local behavior (Ask Gemma starters, InferenceBadge). Reverting only this conditional restores the current full-gate experience on both backends — no other code touched, no migration, no data implication.
