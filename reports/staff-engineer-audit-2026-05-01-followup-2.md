# FutureProof Staff Engineering Audit — 2026-05-01 Follow-up #2

*Reviewer: Staff Engineer (15 YOE, production incident survivor)*
*Date: 2026-05-01 (second follow-up; previous: `staff-engineer-audit-2026-05-01-followup.md`)*
*Branch: `career-path-enhancements`*
*Scope: verify the two follow-up commits (`9010c4f` P1 SOC fullmatch, `799b1e3` M2 build_id deps), then look for fresh hazards a Google reviewer would spot in the first 30 seconds of close reading.*

> **What this audit is and isn't.** Per the user's brief, in-flight EADA / IPEDS Finance pipeline work is excluded entirely (ingestors, silver, gold, tests, governance, specs, MCP/build wiring orphan status, and the bundled stat-filter scope in `799b1e3`). Working-tree hygiene and the prior-audit "orphan dataset" finding are also retired. This pass focuses on (a) whether the two declared fixes are real and (b) what's *new* on the surface that wasn't on my radar yet.

---

## Executive Summary

**Both declared fixes landed correctly.** Commit `9010c4f` swaps `re.match` → `re.fullmatch` on `_SOC_PATTERN` at `backend/app/models/api.py:162`, with a dedicated comment explaining why and **two real new parametrize cases** (`branch_target_trailing_newline` testing `"11-3021\n"`, `branch_target_leading_whitespace` testing `" 11-3021"`). I verified both would fail under regression: revert the diff to `match` and the trailing-newline case flips to 200/404. Not theater. Commit `799b1e3` changes the FutureScreen tree-fetch effect deps from `[build, retryCount]` to `[build?.build_id, retryCount]` at line 253, with a useful inline comment. The bundled stat-filter scope is acknowledged out-of-scope per the brief.

**Test surface is healthy.**
- Backend: **1,280/1,280 passed in 4.84s** (matches the brief's number exactly).
- Frontend: **766/766 passed in 15.79s** across 62 files (the brief said 746; actual is 766 — even better. FutureScreen file is 16/16 as expected).
- TypeScript: **clean** (`npx tsc --noEmit` exit 0). One transient TS6133 stale-cache warning resolved on second run; not a real finding.

**Two new findings worth flagging before a Google reviewer opens the router directory:**

- **🟠 P1 — `GET /branches/{soc}` accepts unvalidated SOC.** Same class of issue as the original S3 (unauthenticated endpoint accepting arbitrary user input that flows to a DuckDB lookup), but on a *different* router that the audit-driven fix never touched. The path parameter `soc: str` flows straight into `branch_tree.get_branches(soc) → mcp_client.call("get_career_branches", {"soc_code": soc})`. Like S3, it's not exploitable today (the MCP server's `query_iceberg_simple` parameterizes the query) but the validator is missing at the same boundary the previous audit closed elsewhere. Inconsistent posture is the kind of detail a Google reviewer who reads the security narrative in the README and then opens `routers/branches.py` will spot.

- **🟠 P1 — `GET /tree/{build_id}?max_depth=…` is unbounded.** No upper bound on `max_depth`. The `build_tree` recursion is gated by a `seen` SOC set so it can't loop forever, but a request to `/tree/<bid>?max_depth=999` will exhaust *every reachable distinct SOC* before returning, and each level fans out via `_fetch_raw_branches` (DuckDB call). On a real database this is a single-request CPU-and-DB-time amplifier on an unauthenticated endpoint. Trivial fix: `max_depth: int = Query(3, ge=1, le=4)` — the frontend only ever calls depth=2 or 3.

**Carryovers (still open, still flagged in prior audits):**

- **🟡 M1 (now P2 in this audit, Finding 3):** sync `builds.load_build` is called inside the `async def chat_ask` handler at `routers/ask_gemma_router.py:34`. `_execute_one` → `_db.execute_one` is a sync DuckDB call. Same class as S2, just on a different sync surface. `load_build` is fast (single PK SELECT) so impact is small, but the same blocking-the-event-loop reasoning that drove S2 applies here. Pattern is widespread: `routers/builds_collection.py:53`, `routers/builds.py:222/375/385/388/394/405/453`, `routers/reports.py:14/25` all do the same. If S2 was worth fixing, the rest are too — at minimum on the chat path, since that handler also `await`s LLM calls and any blocking on the way in delays the entire chat round-trip.

- **🟡 P2 — `error` state in `FutureScreen.tsx:241` uses an English literal `"Failed to load tree"`** that bypasses i18n (`useT`). The user-facing label uses `t("tree.loadError")` correctly; this is the secondary detail string. Minor, but the codebase otherwise routes every visible string through `useT`. A reviewer running the app in `es` (or Jeff's wife's deaf-education users) sees a Spanish primary line followed by an English secondary line.

- All the prior-audit M-class items (M3 module-level dicts, M4 `ask_gemma.py` is 1,396 lines) are unchanged.

**Verdict: A− → A−.** The fix cycle was clean, fast, and tested. No regressions. The two new P1s are real but tiny — the SOC validator pattern is a literal copy-paste of the existing fix to one new endpoint, and the `max_depth` bound is a one-line `Query(...)` change. Both are 5-minute, ship-before-submission fixes.

---

## What I Verified

### P1 (prior audit) — SOC `fullmatch` (claimed FIXED)

**Verified: actually fixed.**

- `backend/app/models/api.py:162` — `if not _SOC_PATTERN.fullmatch(self.target_id or ""):`. The diff also kept the regex object cached at module scope (line 106). Inline comment at lines 159-161 explains the `re.match` vs `fullmatch` newline trap explicitly — useful future-Jeff documentation.
- `backend/tests/routers/test_ask_gemma_router.py:646-665` — two new parametrize cases:
  - `branch_target_trailing_newline` → `"11-3021\n"`, expects 422.
  - `branch_target_leading_whitespace` → `" 11-3021"`, expects 422.
- Test ids list at lines 675-676 has the two new ids in the same order. No ordering drift.

**Regression-resistance check:** if a future change reverts the diff back to `re.match`, the trailing-newline case asserts `resp.status_code == 422`, which becomes `200` (because `_validate_cardinality` returns and downstream resolution fires). The leading-whitespace case is double-protection — `re.match` would already reject it, but pinning the contract explicitly is the right call. No theater.

### M2 (prior audit) — `useEffect` deps on `build` object (claimed FIXED)

**Verified: actually fixed.**

- `frontend/src/screens/FutureScreen.tsx:253` — `}, [build?.build_id, retryCount]);`
- The 3-line comment at lines 250-252 ("Depend on build_id (stable string), not the build object — a store refactor that returned a new object identity for the same logical build would otherwise refetch the tree on every change.") is the right commit-message-style note that survives in the source.
- The bundled stat-filter feature work in the same commit (StatFilterRow imports, `filterTreeByStats`, multi-filter empty-state label, "AND semantic" tests at `FutureScreen.test.tsx:684`) is in-scope-for-the-feature, out-of-scope-for-me-per-the-brief. I did not flag it.

### Test totals (claimed)

- Backend: **1,280/1,280 passed in 4.84s** ✓ (matches the brief).
- Frontend: **766/766 passed in 15.79s across 62 files** ✓ (slightly *more* than the brief's 746 — extra coverage somewhere).
- FutureScreen file: **16/16 passed**, including 3 new stat-filter tests, 2 new card-swap tests, 1 navigation-guard test, 1 error-state test.
- TypeScript: clean.

---

## New Findings

### 🟠 P1 — Finding 1: `GET /branches/{soc}` is the missing twin of the S3 fix

**Impact:** The original S3 fix anchored the SOC validator on `POST /chat/ask`. But there's a *second* unauthenticated endpoint that accepts an arbitrary string and routes it into the same parameterized DuckDB lookup — and it has no validator at all. A request like `curl http://localhost:8000/branches/$(python -c 'print("A"*1024)')` reaches `mcp_client.call("get_career_branches", {"soc_code": "AAAA..."})`. The MCP server's `query_iceberg_simple` parameterizes the query so this isn't a SQL injection, but the same defense-in-depth argument that justified S3 applies: arbitrary unauthenticated input shouldn't reach the data layer. A reviewer who reads the README's "Security & Deployment" section and then opens `routers/branches.py` will see asymmetry — `chat_ask` validates SOC, `get_branches` doesn't.

**Location:** `backend/app/routers/branches.py:9-11`.

```python
@router.get("/branches/{soc}")
async def get_branches(soc: str):
    return branch_tree.get_branches(soc)
```

**The Problem:** No length cap, no shape check, no validator. The corresponding test surface in `tests/routers/` (if any) doesn't exercise malformed input. Defense-in-depth is uneven across the surface area.

**The Fix:**
```python
from fastapi import APIRouter, HTTPException, Path
import re

_SOC_PATTERN = re.compile(r"\A\d{2}-\d{4}\Z")  # or import from models.api


@router.get("/branches/{soc}")
async def get_branches(soc: str = Path(..., max_length=7)):
    if not _SOC_PATTERN.fullmatch(soc):
        raise HTTPException(
            status_code=422,
            detail="soc must match SOC pattern \\d{2}-\\d{4}",
        )
    return branch_tree.get_branches(soc)
```

Better yet, lift `_SOC_PATTERN` from `models/api.py` into a shared validator module and reuse it. Add two parametrize tests mirroring the chat_ask suite.

**Severity rationale:** 🟠 not 🔴 because the parameterized DuckDB call makes the immediate downstream call benign. But it's *exactly* the same posture gap S3 was, just on a different endpoint, and shipping a security fix that's inconsistent across the surface is itself a finding. ~10 minutes including the test.

---

### 🟠 P1 — Finding 2: `/tree/{build_id}?max_depth=…` has no upper bound

**Impact:** `GET /tree/{build_id}` accepts `max_depth: int = 3` with no validation. The frontend only calls it with `max_depth=2` (`FutureScreen.tsx:230`) or `max_depth=3` (the default), but the endpoint is reachable by any unauthenticated client. A request to `/tree/<bid>?max_depth=20` will recurse via `career_tree.build_tree.expand` and call `_fetch_raw_branches` (DuckDB) once per distinct SOC reachable from the root within 20 hops. The `seen` set prevents infinite loops on cycles, but it doesn't bound the *fan-out*. On a fully populated branches table, this is single-request CPU and DB amplification on an unauthenticated endpoint.

**Location:** `backend/app/routers/branches.py:14-15`.

```python
@router.get("/tree/{build_id}")
async def get_tree(build_id: str, max_depth: int = 3):
```

**The Problem:** Combined with Finding 1, an attacker can mint adversarial `/tree/?max_depth=999` requests, each potentially fanning out to thousands of DB calls. Even ignoring adversarial use, a typo in a future client call could chew through resources unintentionally.

**The Fix:**
```python
from fastapi import Query

@router.get("/tree/{build_id}")
async def get_tree(
    build_id: str,
    max_depth: int = Query(3, ge=1, le=4),
):
```

`le=4` covers every realistic frontend call (depth=2 for `/future`, depth=3 elsewhere) with one node of headroom. Returns 422 on out-of-range automatically — no handler change needed.

**Severity rationale:** 🟠 — combined with Finding 1 this is the second unauthenticated DoS amplifier on the same router. One-line fix.

---

### 🟡 P2 — Finding 3: `chat_ask` handler still has sync DuckDB on the way in

**Impact:** `routers/ask_gemma_router.py:34` — `loaded = [builds.load_build(bid) for bid in request.scope.build_ids]` — is a sync DuckDB SELECT inside an `async def` handler. The same event-loop-blocking reasoning that justified S2 applies. `load_build` is fast (single-row PK lookup, sub-1ms on a hot connection), but the chat handler is the highest-latency path in the app (LLM round-trip), and any synchronous wait at the entry blocks the entire event loop for that duration. With 4 build_ids in a `compare` scope, that's 4 sequential blocking SELECTs.

**Location:** `backend/app/routers/ask_gemma_router.py:34`. Same pattern in `builds_collection.py:33,53`, `builds.py:222,375,385,388,394,405,453`, `reports.py:14,25`.

**The Problem:** S2 fixed `_context_for_branch`'s sync DuckDB call but missed the entry-point sync calls on the same handler. The fix posture is asymmetric — same handler, two different blocking patterns, only one fixed.

**The Fix:** Wrap each sync DB call with `asyncio.to_thread`, the same primitive used in S2:
```python
import asyncio

loaded = await asyncio.gather(*[
    asyncio.to_thread(builds.load_build, bid)
    for bid in request.scope.build_ids
])
```

Bonus: this also parallelizes the up-to-4 lookups for compare scope.

**Severity rationale:** 🟡 not 🟠 because the call is fast and impact is bounded by max 4 build_ids. Pattern-completeness finding more than a hot bug. Worth doing for defense-in-depth on the chat handler at minimum.

---

### 🟡 P2 — Finding 4: i18n bypass in FutureScreen error state

**Impact:** `frontend/src/screens/FutureScreen.tsx:241` sets `setError("Failed to load tree")` — a hardcoded English string. The user-facing primary line uses `t("tree.loadError")` correctly (`tree.tsx:678`), but the `error` secondary line at `:682` renders the raw `error` state without going through `useT`. A user with `locale=es` sees the localized headline followed by an English subtitle.

**Location:** `frontend/src/screens/FutureScreen.tsx:241`.

```tsx
} catch (err) {
  if (cancelled) return;
  setError("Failed to load tree");  // <- bypasses i18n
```

**The Problem:** Inconsistent with the rest of the screen (every other visible string flows through `useT`). `setError` should hold a key (or be removed entirely if `tree.loadError` is sufficient). The current code also stores the error message in state, which is fine, but if the `error` slot is going to render to the user, it needs to be localizable.

**The Fix:** Either (a) drop the secondary error display and rely on `tree.loadError` alone, or (b) add a `tree.loadErrorDetail` key and use `t("tree.loadErrorDetail")`:
```tsx
setError("tree.loadErrorDetail");
// ...later
{error && <p>{t(error)}</p>}
```

**Severity rationale:** 🟡 — small, but the codebase has otherwise-disciplined i18n hygiene; this is the lone leak in a recently-shipped screen.

---

## Carryovers (Verified Unchanged)

| ID | Item | Status |
|---|---|---|
| **M1** | LRU on `get_occupation_data` Case 3 in chat path | Open. Same as prior audit. |
| **M3** | `_render_locks` (`routers/wrapped.py:39`), `_builds` (`state.py:16`) — module-level unbounded dicts | Open. Pre-existing. |
| **M4** | `ask_gemma.py` is 1,396 lines | Unchanged. Same line count. Not blocking. |
| Prior-audit P2 Finding 2 | IPEDS Finance test coverage | Excluded per brief (in-flight). |
| Prior-audit P2 Finding 3 | EADA + IPEDS Finance orphan datasets | Excluded per brief (in-flight). |

---

## What's Actually Good (Acknowledging Solid Work)

- **The two follow-up commits are textbook.** Each fixes one thing, has a substantive commit message that names the audit finding, includes the comment in the source, and adds tests that would actually catch a regression. `9010c4f` is 5 lines of behavior change + 22 lines of test = 26 lines, no scope creep. `799b1e3`'s actual M2 fix is one dependency-array change with a 3-line explanatory comment. (The bundled stat-filter scope in `799b1e3` is out-of-scope per the brief — I'd note for the future that bundling unrelated work into a "fix:" commit is the kind of thing that bites you in `git blame` later, but the user is aware.)
- **The new SOC test cases use the right kind of inline comments.** "Trailing newline — re.match would accept this because `$` matches before a trailing \n. fullmatch closes the gap." That's a mid-2030s engineer reading this in five years and immediately understanding why. Good comments.
- **`_context_for_branch`'s three-case structure is clean.** Case 1 (matched branch) → Case 2 (root SOC) → Case 3 (off-tree, calls `get_occupation_data`). Each path has a coherent shape; the helper-bracketed contract for Gemma is consistent across all three. The Case 3 fallback (true thin-data block when `get_occupation_data` returns nothing) is the right "fail honestly, don't fabricate" posture.
- **The async/await chain through `chat_ask → ask_gemma.chat_ask → _context_for_branch → mcp_client.call_async → asyncio.to_thread`** is consistent end-to-end. No mixed sync/async on the path that S2 fixed. The one remaining sync call (Finding 3) is at the *entry*, not in the body that was the focus of S2.
- **FutureScreen test file has 16 substantive tests** — happy path, navigation guard, mobile sheet behavior, card swap, education filters (4 cases), stat filters (3 cases including the AND semantic), error state. The "AND semantic" test (`FutureScreen.test.tsx:684`) is the kind of test most teams skip because the feature "obviously works"; that someone wrote it is a good sign.
- **The README's Security & Deployment section** ("**unauthenticated by design**") is the right kind of honest framing for a hackathon submission. CORS allowlist via env, the explicit "no per-user authorization layer" disclaimer, and the explanation of *why* (no logged-in user concept) all read well.
- **Reduced-motion handling** — `frontend/src/index.css` has 6 distinct `@media (prefers-reduced-motion: reduce)` blocks, and the test setup has a dedicated mock for it. Not directly tested in the new FutureScreen surface (the `motion.span` loading emoji has `repeat: Infinity`), but the global stylesheet handles the override.

---

## What a Google Reviewer Sees in 30 Seconds

1. `git log --oneline -3` shows two same-day fixes (`9010c4f`, `799b1e3`) on top of the prior audit (`eac01d8`). **Reads as: "team audits → fixes → commits → moves on"** — exactly the loop a senior reviewer wants to see.
2. `git show 9010c4f` shows a 5-line src change + 22 lines of test, with a substantive commit message. **Reads as: "they don't ship code without a test."**
3. `cd backend && pytest -q` — 1,280 passed in 4.84s. `npx vitest run` — 766 passed in 15.79s. `npx tsc --noEmit` — clean. **Reads as: "fast, comprehensive, no flakes."**
4. Open `backend/app/models/api.py`, see the `_SOC_PATTERN.fullmatch` line with the comment about Python's `$` newline behavior. **Reads as: "they understand the language they're writing in."**
5. Open `backend/app/routers/branches.py`. **Sees `soc: str` with no validator.** This is the trip-wire — they'll ask why this endpoint isn't held to the same standard as `chat_ask`. ~5 minute fix per Finding 1; do it before submission.
6. Try a `curl` (because they will): `curl 'http://localhost:8000/tree/<bid>?max_depth=20'`. Either it crushes the server or returns an enormous response. Either outcome is a finding. ~1 minute fix per Finding 2.

The two P1s are the only things between here and a clean detailed-reading pass. Both fixes together are <30 minutes including new tests.

---

## Recommendations (Prioritized)

1. **🟠 Fix P1 Finding 1** — add the SOC validator to `routers/branches.py:get_branches`. Lift `_SOC_PATTERN` into a shared module so it's used in both places. Add two parametrize tests mirroring the chat_ask validation suite. ~15 minutes.
2. **🟠 Fix P1 Finding 2** — change `max_depth: int = 3` to `max_depth: int = Query(3, ge=1, le=4)` on `routers/branches.py:get_tree`. Add one test asserting `max_depth=99` returns 422. ~5 minutes.
3. **🟡 P2 Finding 3** — wrap `builds.load_build` in `asyncio.to_thread` for the chat path at minimum. ~5 minutes for the chat path alone, ~30 minutes for the full sweep across all routers.
4. **🟡 P2 Finding 4** — drop the secondary `error` line in FutureScreen, or route it through `useT`. ~2 minutes.
5. Defer M1 (LRU on `get_occupation_data`), M3 (module dicts), M4 (`ask_gemma.py` size). All known.

---

## Questions for the Author

1. Was the omission of the SOC validator on `/branches/{soc}` deliberate (it's a different surface from the chat path) or just out-of-scope for the original S3 fix? If the latter, mirroring the validator there is uncontroversial; if the former, I'd like to know the reasoning.
2. Has `/tree/{build_id}?max_depth=…` been hit with anything other than 2 or 3 in practice? If 4 is realistic for any future use case, the `le=4` cap can stretch.
3. The bundled stat-filter scope in `799b1e3` — was that an intentional "ship together because the deps overlap" call, or did the M2 fix get caught in the middle of the stat-filter work? Asking for `git blame` archaeology purposes; not a finding.

---

## Bottom Line

**Two follow-up commits, both real fixes, both correctly tested, both shipped.** The S2/S3 hardening cycle is now functionally complete on `chat_ask`. The remaining gaps are on a *different* router (`/branches`, `/tree`) that wasn't in the S3 scope but lives on the same unauthenticated surface. Those are 20 minutes of work to close, and they're the only things a careful Google reviewer will land on after `git log` and `pytest` come back clean.

Test discipline is real. Fix discipline is real. Comment-in-source discipline is real. The submission is ready; the two P1s are below the threshold of "don't ship," but above the threshold of "would prefer to fix before submission."

— Staff Engineer (still skeptical, but the bar's getting harder to clear)
