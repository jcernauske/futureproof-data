# FutureProof Staff Engineering Audit — 2026-05-01

*Reviewer: Staff Engineer (15 YOE, production incident survivor)*
*Date: 2026-05-01 (one day after the 2026-04-30 audit)*
*Branch: `career-path-enhancements`*
*Scope: read-only follow-on audit ahead of Gemma 4 Good (Kaggle / Google DeepMind) hackathon review.*

> **Read this first.** The 2026-04-30 audit at `reports/staff-engineer-audit-2026-04-30.md` did the heavy lifting and tracked 11 Top-10 + bonus items through `tech-debt-hackathon-hardening` and its `-followup`. That audit's substance still holds — DuckDB parameterization, the QueryEngine concurrency comment, the Gemma fan-out semaphore, the JSONL audit log, transaction-wrapped wrapped-frame writes, the in-process MCP isolation. **I'm not re-litigating any of it.** This audit covers the new surface that landed since: the `/future` screen + `BranchTreeFlow` + `EducationFilterRow` + `SelectedNodeCard`, the new branch-scope context-builder in `ask_gemma.py` (case 3 is the new one), the EADA + IPEDS Finance ingestors, and — more importantly — what's still uncommitted on this branch.

---

## Executive Summary

The new code is **substantively good** in the same way the old code was substantively good — Pydantic at the boundaries, parameterized SQL, sensible logging, real test coverage with negative assertions, a defensive `try/except` around the new MCP enrichment call in `ask_gemma._context_for_branch` Case 3. The `/future` screen is a real piece of work (672 lines, react-flow-driven, with a debounced selection, a flash-highlight driver, an education filter that preserves the root, an empty-state overlay with a one-tap clear, a mobile bottom-sheet with visualViewport-aware keyboard handling). The new `EadaIngestor` and `IpedsFinanceIngestor` carry the kind of EDA-pinned-constants discipline that makes future cycle drift a parameter change instead of a code change. Tests are not theater.

**The drag on the grade is two things, both packaging, both visible in the first 30 seconds:**

1. **Nothing is committed.** The hardening, hardening-followup, EADA, IPEDS Finance, `/future` screen, ErrorBoundary, education filter, `ask_gemma` branch-scope work, intent.py hardening, and lifespan migration — **all of it sits in `git status` as uncommitted modifications and untracked files.** A reviewer who clicks the GitHub "Code" tab sees `925f887 feat: career-path enhancements + leaderboard rank estimator + i18n parity` as the latest commit, with **none** of the audit-driven work the prior audit document claims is "DONE." The previous audit's "Status: COMPLETE" annotations are factually accurate about the *code state on disk* but factually misleading about the *commit history* — the work is real, it's just not in git.
2. **The `tech-debt-hackathon-hardening*` specs and `refactor-remove-dead-frontend-code.md` are still in `docs/specs/` (active), not `docs/specs/completed/`.** Their internal status fields say `COMPLETE`, but they have not been moved.

**Verdict: A- in code substance, B in packaging discipline.** Same root cause as the prior audit's drag (uncommitted in-flight refactor) — the same thing has now happened *to the cleanup that was supposed to fix the prior occurrence of it*. **Commit and ship before submission. The work is done; ship it.**

I found exactly one new substantive issue worth fixing before submission: a synchronous, untimed `mcp_client.call("get_occupation_data", ...)` in `_context_for_branch` Case 3 (`ask_gemma.py:1175`) that runs inside the `async def chat_ask` event-loop path. It's wrapped in `try/except` so it can't crash the request, but it blocks the event loop on every L2-endpoint chat-opener — the new `/future` screen's primary new path. **🟠 Serious; fix is one line.**

---

## What Changed Since 2026-04-30

| Surface | Lines | Status in git |
|---|---|---|
| `backend/app/main.py` (lifespan + CORS hardening) | modified | uncommitted |
| `backend/app/services/intent.py` (defense-in-depth + log warnings) | modified | uncommitted |
| `backend/app/services/guidance.py` (compare pivotal formatting) | modified | uncommitted |
| `backend/app/services/ask_gemma.py` (new branch scope, Case 3 enrichment) | 1,396 lines (+78 in diff) | uncommitted |
| `backend/tests/services/test_ask_gemma.py` (+ branch off-build test) | +49 lines | uncommitted |
| `backend/tests/test_app.py` (lifespan + CORS env tests) | +179 lines | uncommitted |
| `backend/tests/services/test_intent.py` | NEW, 249 lines | untracked |
| `frontend/src/screens/FutureScreen.tsx` | NEW, 672 lines | untracked |
| `frontend/src/components/tree/BranchTreeFlow.tsx` + `flow/` (3 nodes) | NEW, ~250 lines | untracked |
| `frontend/src/components/tree/SelectedNodeCard.tsx` | NEW, 111 lines | untracked |
| `frontend/src/components/tree/FutureChatSheet.tsx` | NEW, 126 lines | untracked |
| `frontend/src/components/tree/EducationFilterRow.tsx` | NEW, 68 lines | untracked |
| `frontend/src/components/ui/ErrorBoundary.tsx` | NEW, 105 lines | untracked |
| `frontend/src/data/educationFilter.ts` + tests | NEW, 80 + 227 lines | untracked |
| `frontend/src/data/treeFlowLayout.ts` | NEW, 261 lines | untracked |
| `frontend/src/styles/reactflow-dark.css` | NEW | untracked |
| `frontend/src/store/buildStore.ts` (persist middleware removed) | modified | uncommitted |
| `frontend/src/screens/BuildResultsScreen.tsx` (clearSession comment + see-future button) | modified | uncommitted |
| `frontend/src/App.tsx` (ErrorBoundary registered, /future route) | modified | uncommitted |
| `src/raw/eada_ingestor.py` | NEW, 631 lines | untracked |
| `src/raw/ipeds_finance_ingestor.py` | NEW, 1,117 lines | untracked |
| `tests/raw/test_eada_ingestor.py` + fixture | NEW, 753 lines | untracked |
| `scripts/ingest_eada.py`, `scripts/ingest_ipeds_finance.py`, et al. | NEW | untracked |
| `docs/specs/full-pipeline-eada.md`, `full-pipeline-ipeds-finance.md` | NEW | untracked |
| `docs/specs/tech-debt-hackathon-hardening.md` (Status: COMPLETE) | NEW | untracked |
| `docs/specs/tech-debt-hackathon-hardening-followup.md` (Status: COMPLETE) | NEW | untracked |
| `governance/...` (40+ EADA + IPEDS audit-trail files) | NEW | untracked |
| `reports/tech-debt-hackathon-hardening-2026-04-30.md` and `-followup` | NEW | untracked |

That's a *lot* of work. None of it is in `git log`.

---

## Findings

### 🔴 Critical

**None.**

### 🟠 Serious

#### S1 — Nothing from the post-audit hardening is committed.
**Impact:** A Google reviewer who lands on `https://github.com/<owner>/futureproof-data/tree/main` (or even `tree/career-path-enhancements`) sees the last commit as `925f887 feat: career-path enhancements + leaderboard rank estimator + i18n parity`. They do not see:
- the `lifespan` migration off `app.on_event("startup")`,
- the env-driven CORS allowlist,
- the `intent.py` `^\d{2}$` defense-in-depth + log-warning hardening,
- the top-level React `ErrorBoundary`,
- the new `/future` screen and `BranchTreeFlow`,
- the EADA + IPEDS Finance ingestors,
- the README "Security & Deployment" section.

The prior audit document claims these are DONE. They are done **on disk**, in the working tree of the local checkout. They are not in `git log`. A reviewer who reads the audit document and then fails to find any of the named commits will draw exactly the conclusion you don't want them to draw: that the team writes status updates that don't reflect reality.

**Location:** `git status` (top-level).

**The Fix:**
Commit and push, in coherent units. Suggested split (do NOT bundle in one giant commit):
1. `chore: add tech-debt-hackathon-hardening + followup` — `backend/app/main.py`, `intent.py`, `guidance.py` formatting, `buildStore.ts`, `App.tsx`, `BuildResultsScreen.tsx`, `ErrorBoundary.tsx`, README, related tests, both spec files, both reports. Move both specs to `docs/specs/completed/`.
2. `feat: add /future screen with education filters and branch chat scope` — `FutureScreen.tsx`, `BranchTreeFlow.tsx`, `flow/*.tsx`, `EducationFilterRow.tsx`, `SelectedNodeCard.tsx`, `FutureChatSheet.tsx`, `educationFilter.ts`, `treeFlowLayout.ts`, `reactflow-dark.css`, related tests, `ask_gemma.py` branch scope additions, `i18n/strings.ts` keys, App.tsx route registration.
3. `feat(pipeline): add EADA + IPEDS Finance ingestors` — `src/raw/eada_ingestor.py`, `src/raw/ipeds_finance_ingestor.py`, `scripts/ingest_*.py`, `tests/raw/test_eada_ingestor.py`, fixtures, both specs (move to `completed/` only after the spec workflow is fully run — they look like they're still in active execution per the governance/ directory contents).
4. Move `refactor-remove-dead-frontend-code.md` to `completed/` if its scope is finished, or leave it active and label clearly.

Severity 🟠 because this is the exact pattern the prior audit's #2 finding flagged ("109 file changes from in-flight refactor blocking the branch") — **the same hygiene issue has recurred while shipping the cleanup that was supposed to fix it**. A repeat of the same mistake is a stronger reviewer signal than a single occurrence.

---

#### S2 — Synchronous DuckDB call inside `async def chat_ask` blocks the event loop.
**Impact:** Every Ask Gemma request whose `scope.kind == "branch"` and whose `target_id` is neither on `build.branches` nor the root SOC (i.e. an L2 endpoint clicked from the new `/future` tree) runs `mcp_client.call("get_occupation_data", {"soc_code": target_id})` **synchronously** inside the FastAPI async handler. The call goes through `_query_engine.QueryEngine.query_filtered` which acquires the engine-wide `RLock` and runs a DuckDB SELECT — milliseconds when warm, but it holds the asyncio event loop for the entire duration. Under any concurrent traffic on `/chat/ask`, this serializes every other in-flight chat request behind the lookup. The same module already shows the right pattern: `mcp_client.call_async` exists at `mcp_client.py:192` precisely for this — it wraps `call` in `asyncio.to_thread`.

**Location:** `backend/app/services/ask_gemma.py:1173-1187`
```python
occ_row: dict[str, Any] | None = None
try:
    occ_result = mcp_client.call(
        "get_occupation_data", {"soc_code": target_id}
    )
    candidate = occ_result.get("data") if isinstance(occ_result, dict) else None
    if isinstance(candidate, dict):
        occ_row = candidate
except Exception:  # noqa: BLE001 — MCP outage falls through to stub
    logger.warning(
        "get_occupation_data lookup failed for %s in branch context",
        target_id,
        exc_info=True,
    )
    occ_row = None
```

**The Problem:** `chat_ask` is `async def` (line 210). It calls `_context_for_branch` synchronously (line 240). `_context_for_branch` Case 3 calls `mcp_client.call`, which runs DuckDB on the calling thread. On the FastAPI event loop, that's the only thread that matters — every other coroutine on this worker waits. This is the textbook "blocking I/O in async" foot-gun. The compounding factor: `/future` is the *new* primary path that exercises this code, and L2 endpoint clicks are exactly the case that hits Case 3.

**The Fix:** Make `_context_for_branch` `async` (or split out an async branch for Case 3) and use the existing `mcp_client.call_async`:
```python
async def _context_for_branch(build: Build, target_id: str) -> str:
    ...
    # Case 3 (line 1175):
    occ_result = await mcp_client.call_async(
        "get_occupation_data", {"soc_code": target_id}
    )
    ...
```
Then update `chat_ask` to `await _context_for_branch(...)`. The other context builders are pure-Python lookups against in-memory `Build` data and stay sync — no need to touch them.

**Severity:** 🟠 — single-user demo won't notice; even small concurrent load (Google reviewer + a beta tester at the same time) starts to. Cheap fix.

---

#### S3 — `target_id` for branch scope is unbounded user input flowing to a DuckDB lookup.
**Impact:** `AskScope.target_id` for `kind="branch"` is documented as "No whitelist on the value — open-ended SOC codes; existence is checked at the service layer" (`api.py:111-115`). The service layer "check" is the `mcp_client.call` in the issue above — it takes any string and runs `query_iceberg_simple(filters={"soc_code": target_id})`. The query is parameterized (verified — `_query_engine.py` binds via DuckDB `$name`), so this is **not** SQL injection. But there's also no length cap, no character-set restriction, and no auth on the endpoint, so `POST /chat/ask` accepts unbounded `target_id` strings as a free-roaming parameterized DuckDB SELECT trigger. At hackathon scale this is a non-issue; in the wild it's an unauthenticated denial-of-service amplifier (any adversary can hammer `/chat/ask` with `target_id`-rotating payloads to keep DuckDB busy and the asyncio loop blocked, see S2).

**Location:** `backend/app/models/api.py:118` (no validator on `target_id` for branch scope), `backend/app/services/ask_gemma.py:1175` (the call site).

**The Fix:** Add a SOC-code shape validator on `AskScope.target_id` when `kind == "branch"`. SOC codes follow `\d{2}-\d{4}` exactly; reject everything else with a 422 from the model validator before the handler runs.
```python
_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")
# inside _validate_cardinality, after the existing branch checks:
if self.kind == "branch":
    if not _SOC_PATTERN.match(self.target_id or ""):
        raise ValueError("branch target_id must match SOC pattern \\d{2}-\\d{4}")
```
Same applies to `kind="skill"`, where `target_id` is a free-form `AppliedSkill.id` — currently any string passes the validator and the lookup eats it. Cheap defense-in-depth.

**Severity:** 🟠 — production-shaped, not hackathon-shaped, but the README's "Security & Deployment" section already acknowledges the unauthenticated posture. Tightening the input shape is consistent with that posture and costs five lines.

---

### 🟡 Moderate

#### M1 — `_context_for_branch` Case 3 is silently a network-amplification surface.
The MCP call in S2/S3 fires on every chat-opener for every L2 endpoint click. `/future` is mounted on the build-results path, the chat sheet auto-opens on selection, and the opener path bypasses Gemma's tool loop entirely (`ask_gemma.py:261-282`). So for a 12-branch tree with 5 L2 endpoints each, a student rapidly clicking through endpoints fires 60+ DuckDB lookups in quick succession — each one synchronous on the event loop. The `NODE_DEBOUNCE_MS = 300` debounce on the frontend (`FutureScreen.tsx:73`) cuts this somewhat, but not by enough; the debounce throttles the *latest selection*, not the *opener fan-out*. There is no caching on the get_occupation_data result inside the chat path. Combined with S2, a single user's tree exploration session can sustainedly block the event loop.

**Location:** `backend/app/services/ask_gemma.py:1168-1187` + `frontend/src/screens/FutureScreen.tsx:271-276`.

**The Fix:**
1. Async-ify per S2.
2. Add a small process-local LRU on `(soc_code,) → occ_row` keyed by the same TTL as the `program_career_paths` LRU. The data is essentially static; per-process cache is cheap.

**Severity:** 🟡 — would matter in staging load tests; demo audience is small enough that it shouldn't manifest. Worth fixing because the screen is the *new* primary surface a reviewer will click on.

---

#### M2 — `useEffect` deps in `FutureScreen.tsx` use `build` (object identity) without memoization.
**Impact:** Two effects depend on `build`:
- Line 200-202: `if (!build) navigate("/my-build", { replace: true });` — if `build` reference changes between renders for any reason (a store update that produced a new object identity), the redirect logic re-runs but the `build` truthy check guards it, so no harm.
- Line 206-232: the tree fetch effect. This fires `fetchTree` whenever `build` reference changes. If the build store ever produces a new object identity for the same conceptual build (e.g. an `updateBuild` callback that returns a new object even when nothing material changed), the tree refetches.

**Location:** `frontend/src/screens/FutureScreen.tsx:200, 232`.

**The Fix:** Depend on `build?.build_id` (a stable string), not `build` (the whole object). Same shape as the existing `[build, retryCount]` — replace with `[build?.build_id, retryCount]`. The route guard effect can stay on `[build, navigate]`; the fetch is the load-bearing one.

**Severity:** 🟡 — likely benign today because `useBuildStore` only swaps the build reference on real updates. Latent foot-gun if anyone refactors the store to return new objects more aggressively.

---

#### M3 — `_render_locks` and `_builds` module-level dicts (still) grow unbounded.
**Impact:** Same finding as the prior audit (`app/state.py:16`, `wrapped.py:39`). Still open. Not new — calling it out only because it remains the most production-shaped issue in the backend.

**Severity:** 🟡 — same as before. Not a hackathon risk; would matter in production.

---

#### M4 — `ask_gemma.py` is now 1,396 lines and growing.
The branch scope and Case 3 enrichment added 78 lines. The module already has 6 distinct context-builders (`_context_for_stat`, `_context_for_boss`, `_context_for_skill`, `_context_for_build`, `_context_for_branch`, `_context_for_compare`), each 80-200 lines, each with its own narrow responsibility. The shared-state surface is small (helper formatters, alias dicts, `_SYSTEM_BASE`), so the module would split cleanly into `ask_gemma/__init__.py` (`chat_ask` orchestrator) + `ask_gemma/contexts/{stat,boss,skill,build,branch,compare}.py`. Same shape as the prior audit's #7 (`futureproof_server.py` god-module split) — same prescription: post-hackathon refactor spec, not now.

**Location:** `backend/app/services/ask_gemma.py`.

**Severity:** 🟡 — structural; not a bug today. Defer per the same logic that defers #7.

---

#### M5 — `governance/` directory grew by ~40 untracked files since the prior audit.
EADA + IPEDS Finance pipeline runs produced governance artifacts (audit-trail, dq-rules, dq-scorecards, lineage, models, pii-scans, eda) — all good outputs of the Brightsmith workflow. None are committed. If the pipeline workflow fully runs and writes these as artifacts of the work, they should land with the corresponding spec implementation commits (per S1). Otherwise a reviewer sees a `governance/` directory that's half-tracked, half-not — looks unfinished even when it isn't.

**Location:** Top-level `git status`.

**Severity:** 🟡 — cosmetic / packaging.

---

### 🔵 Minor

#### m1 — `treeFlowLayout.ts:14-20` `STAT_COLORS` dict has unused `as const` typing relative to its `Record<string, string>` annotation.
Not actually an issue — just noting that `dominantStatColor` does `STAT_COLORS[maxStat] ?? "#F2D477"` to defend against a key miss that the typing already prevents (`maxStat` is constrained by `STAT_KEYS`). Defensive `??` is fine. Skip.

#### m2 — `FutureScreen.tsx:421-436` — the `filterEmptyLabel` Oxford-comma branch handles a "rare path" (3 filters active) the comment notes is functionally equivalent to no-filter and shouldn't fire there. Defensive code with a clear comment. Fine. Skip.

#### m3 — `BranchTreeFlow.tsx:88` — `fitViewOptions={{ padding: 0.12, minZoom: 0.7, maxZoom: 1.0 }}` plus separate `minZoom={0.4} maxZoom={2.5}` on the `<ReactFlow>`. The two zoom ranges interact at fit-view time vs. user-pan time. Worth a one-line comment that those are intentionally different — "fitView uses the tighter range so the auto-fit looks tight; user pan/zoom uses the looser range so they can drill in." Easy clarification, not a bug.

#### m4 — `ErrorBoundary.tsx:42` — `error.stack ?? error.message ?? ""` is shown via `<details>` only when `import.meta.env.DEV` is true. Production renders no stack (good). Dev renders 2 KB max (good). Fine.

#### m5 — `ipeds_finance_ingestor.py:200` carries the comment "post-2014-15 schedule" for `F3E03C1` — this is the kind of EDA-pinned constant comment that pays for itself. Same shape across the file. Strength, not a finding.

---

## Testing Quality

I went looking again. **The new tests are real.**

### Backend (`backend/tests/`)
- `test_intent.py` (NEW, 249 lines, 11 test cases) — the audit-driven contract tests for the `intent.py` defense-in-depth. The `_BoomServer` / `_BaseExceptionServer` / `_CapturingServer` stubs are clean. The test `test_get_school_cips_propagates_keyboard_interrupt` is the kind of test most teams forget — explicitly asserting that `KeyboardInterrupt` (a `BaseException`, not `Exception`) propagates through the `except Exception` guard. That's the test that catches the next refactor's "let me just broaden the safety net to BaseException" move. **Real.**
- `test_app.py` additions (+4 tests) — `test_lifespan_runs_without_raising` records `DeprecationWarning` and asserts no `on_event` warning leaked, which catches any regression to the legacy startup hook. `test_cors_disallows_unlisted_origin` asserts the negative — the rejected origin does NOT come back in `Access-Control-Allow-Origin`. `test_lifespan_tolerates_profile_preload_failure` patches `_load_existing_profiles` to raise and asserts the app still serves `/health` 200. `test_parse_cors_origins_strips_and_drops_whitespace` catches the `"a, ,b,"` parsing trap. All four are real defense-in-depth tests.
- `test_ask_gemma.py` addition: `test_context_for_branch_off_build_target_enriched_via_mcp` mocks `mcp_client.call`, asserts that the title surfaces in plain prose, the "2-step" framing appears, and the forbidden tokens (education level, growth category) live inside `[helper: ...]` spans not in the prose surface. The voice-contract assertion via `_assert_no_forbidden_outside_helpers` is doing real work.

### Frontend (`frontend/src/`)
- `educationFilter.test.ts` (NEW, 19 test cases) — exercises every branch of `nodeMatchesFilter`, `nodeMatchesAny`, `filterTreeByEducation`. Real assertions; no theater.
- `FutureScreen.test.tsx` (NEW, 583 lines, 20 test cases) — mocks `BranchTreeFlow` (correct, since React Flow needs `ResizeObserver` + `getBoundingClientRect` that jsdom doesn't implement), mocks `getTree`, mocks `askGemma`. Tests cover the route guard, the depth=2 fetch shape, the tree-node click → card swap with debounce, the bottom-sheet expand-on-select, and the education filter empty-state with `onClear`. The fixture `makeMixedEducationTree` includes one Bachelor's, one Master's, one Doctoral L1 — the filter tests assert that toggling one chip hides exactly the other two. **Real test discipline.**
- `SelectedNodeCard.test.tsx` (NEW, 12 test cases) — exercises the `treeNodeToCareerOutcome` adapter and the `hideNullStats` prop forwarding.
- `ErrorBoundary.test.tsx` (NEW, 10 test cases) — mocks `console.error` so output stays readable, swaps `window.location` with descriptors so `reload()` and `href` setter both get spied. Tests both the happy path (renders children when no throw) and the saboteur path (renders fallback when child throws). The `setHref` spy via `Object.defineProperty` getter/setter is the right shape — most teams just do `Object.defineProperty(window, "location", ...)` without the getter/setter and lose the actual `href` value.

### Pipeline (`tests/raw/`)
- `test_eada_ingestor.py` (NEW, 753 lines, dozens of test classes) — tests `_coerce_long`, `_strip_sentinel`, `_coerce_double`, `_is_institution_total`, `eada_fte_headcount` column parameterization, `reporting_year` stamping, schema shape (11 fields, post-Option-C amendment). The `test_legitimate_zero_preserved` test catches a real failure mode — `0` is a real recruiting-expenses value for 363 institutions and must NOT be sentinel-scrubbed. **Real.**

### Theater Search

I went looking specifically for theater shapes:
- `expect(x).toBe(x)` tautologies — none found.
- Tests that mock a function and then assert that mock was called without verifying anything about the call shape — none found in the new tests.
- `assert True` / `assert not False` placeholders — none.
- `try: ... except: pass` test bodies — none.
- Snapshot-only tests for non-design code — none in the new code.

The closest thing to a thin test is `test_get_crosswalk_returns_empty_for_no_families_without_logging` (`test_intent.py:90-98`), which asserts that the empty-input short-circuit doesn't emit a warning. That's a real assertion (catches a regression where someone adds a `logger.debug` to the empty-list path), even if the test body is short. Acceptable.

**Verdict on new tests: 100% real.** The `test_writer` agent's discipline is holding.

---

## What's Actually Good

Grudgingly. Look, I love Claude, BUT — fine, here's what's right:

- **The `intent.py` `^\d{2}$` defense-in-depth + `KeyboardInterrupt`-propagation tests** are exactly the right shape. The `_CIP_FAMILY_PREFIX_PATTERN.fullmatch(head)` validation paired with the `except Exception` (not `BaseException`) catch is the same pattern, applied twice, with tests that pin both halves. The test `test_get_school_cips_propagates_keyboard_interrupt` is what catches a future refactor that "tightens" the safety net into `except BaseException`. 10-YoE thinking.
- **`ask_gemma._context_for_branch` Case 3 is honest** about what it can and can't do — when the MCP call fails, it falls through to a thin-data stub that points Gemma at `get_occupation_data` for the root SOC and instructs her not to fabricate. The `_helper(...)` wrap on every internal annotation paired with the system prompt's "never reproduce verbatim" rule is the right architecture for keeping voice-contract violations out of the user-visible response. The voice-contract test (`_assert_no_forbidden_outside_helpers`) makes the contract tooled rather than aspirational.
- **The `EducationFilter` design preserves the root.** `filterTreeByEducation` (`educationFilter.ts:67`) does `if (filters.size === 0) return tree;` — empty filter set is unfiltered, not all-filtered-out (the easy bug). Root is always preserved. The empty-state overlay is positioned so the root stays visible underneath with `pointer-events-none` on the container and `pointer-events-auto` on just the clear button so React Flow's pan/zoom under the overlay still works on empty space. That's UX detail that most engineers don't sweat — it saves the demo when filters hide the whole tree.
- **`FutureChatSheet.tsx`'s `visualViewport`-aware keyboard handling** (`FutureChatSheet.tsx:40-57`). When the mobile keyboard pops up, the sheet's `--future-sheet-vh` CSS var recomputes from `window.visualViewport.height` so the input doesn't slide under the keyboard. Most React component libraries do not handle this correctly. This one does.
- **`treeFlowLayout.ts` slot/rank discipline.** The comment at lines 39-42 documents *why* the per-slot spacing is 48 instead of the original 80 — the old spacing produced a 4800px column that fitView could only render at ~0.10 zoom. That's a real production-shaped reason in the code, not just a magic number. The `place(rank, slot, direction)` indirection so the same layout algorithm produces LR (desktop) and TB (mobile) is the right abstraction.
- **`ErrorBoundary.tsx` inlines its tokens by deliberate design.** Comment at line 39: "Inline Brightpath tokens only — no design-system imports, no router, no store. Anything we depend on here might be the thing that crashed." That is exactly the right reasoning for an error boundary. The `autoFocus` on the refresh button is the small accessibility detail that pays off the first time a screen-reader user trips the boundary.
- **`buildStore.ts` persist-middleware removal is clean.** The diff drops the `zustand/middleware` import, the `persist(...)` wrapper, the `partialize`, the `name`. Nothing left behind. The accompanying test changes drop the legacy seed lines for `hasSeenStatTutorial` and add a regression guard. Mechanical refactor done right.
- **`EadaIngestor`'s Ellipsis-sentinel pattern** (`eada_ingestor.py:171-244`) for the filter-column / filter-value parameters lets a caller explicitly pass `None` to mean "no filter applied" without colliding with "use class default." Same pattern reused in `IpedsFinanceIngestor` for the F3 / EFIA optional columns. Cleanly distinguishes the three states: "default", "explicitly disabled", "explicitly overridden." Most ingestors I review have a footgun here.
- **`IpedsFinanceIngestor` correctly prefers cache zip → cache CSV → bulk URL** (`ipeds_finance_ingestor.py:540-590`) and handles the IPEDS revised-data convention (`_rv` suffix wins over the original — `_parse_zip_bytes` line 627-630). The comment at line 627 explains why. Comment at line 604 ("first bytes != b'PK\\x03\\x04'") catches the IPEDS-Datacenter-returns-an-HTML-error-page-with-a-zip-content-type case I have personally been bitten by.
- **The `lifespan` migration is correct.** `_load_existing_profiles()` is wrapped in `try/except` per the prior audit's recommendation. The Iceberg warmup is independently wrapped. Both failure modes log a warning and let the app boot. Test `test_lifespan_tolerates_profile_preload_failure` pins it.

---

## Recommendations

In priority order:

1. **Commit and push (S1).** This is the only thing that matters before a Google reviewer touches this repo. Split into 3-4 coherent commits per the suggestion in S1 above. Move the two hardening specs and `refactor-remove-dead-frontend-code.md` into `docs/specs/completed/` as part of those commits.
2. **Fix S2 + S3 together.** Async-ify `_context_for_branch` for Case 3 + add the SOC-shape validator on `AskScope.target_id`. That's two files, ~10 lines of diff, ~3 tests. Do it before submission — both are surgical and the new `/future` screen is exactly the surface a reviewer will click on first.
3. **Add the LRU on `get_occupation_data` results inside the chat path (M1).** Same diff as S2; piggyback. The data is essentially static at hackathon timescale; an LRU of 256 entries is overkill but trivially cheap.
4. **Fix the `useEffect` dep on `build` → `build?.build_id` (M2).** One-line frontend change.
5. **Defer:** the prior audit's #7 (god-module split for `futureproof_server.py`), the new M4 (god-module split for `ask_gemma.py`), the prior audit's M3 (`_render_locks` / `_builds` LRU), the prior audit's `set_your_course.py` size cleanup. All explicitly post-hackathon scope per the prior audit's own guidance.

---

## Questions for the Author

- **Why the long delay between hardening landing on disk and being committed?** If there's a reason (e.g. waiting on a build to settle, waiting on the EADA spec to finish so it can ship in one commit), a one-line note in the README or in the spec's status field would dispel the "oh, they forgot" reading.
- **Is `/future` reachable from the demo flow?** I see the "see future" button added to `BuildResultsScreen.tsx:854-865` (uncommitted) — assuming yes. Worth confirming the demo script touches it, because if the reviewer never lands on `/future`, the new `BranchTreeFlow` work stays invisible.
- **Has anyone load-tested `/chat/ask` with the new branch scope, especially the L2-endpoint click path?** The S2 issue is small-N invisible; load tests are the cheapest way to expose it.
- **Has the EADA / IPEDS Finance pipeline been promoted past `raw`?** The governance directories suggest the data-analyst / dq / chaos work has run, but the audit-trail filenames imply the pipeline state is mid-flight. If `consumable.institution_aura` (the spec's terminal target) hasn't shipped, the spec is honest-DRAFT and the work is incremental, which is fine — just say so in the spec status header.

---

## Where I Stopped

I covered:
- All `git status` modified backend files (`main.py`, `intent.py`, `guidance.py`, `ask_gemma.py`)
- All `git status` modified backend tests (`test_app.py`, `test_ask_gemma.py`, `test_intent.py`)
- All `git status` modified frontend files (`App.tsx`, `buildStore.ts`, `BuildResultsScreen.tsx`, `CareerCard.tsx`, `statExplanations.ts`, `BuildResultsScreen.test.tsx`, `MenuScreen.test.tsx`, `buildStore.test.ts`, `i18n/strings.ts`, `test-setup.ts`)
- All untracked frontend files in `components/tree/`, `components/ui/`, `data/educationFilter.ts`, `data/treeFlowLayout.ts`, `screens/FutureScreen.tsx`, `styles/reactflow-dark.css`
- New ingestors: `EadaIngestor` (full) and `IpedsFinanceIngestor` (init + fetch + zip parsing; skipped the rest of `flatten` + transformer surfaces because the patterns are consistent with EADA)
- New ingest scripts (`scripts/ingest_eada.py` skimmed; `scripts/ingest_ipeds_finance.py` not opened)
- New specs (`full-pipeline-eada.md`, `full-pipeline-ipeds-finance.md`, `tech-debt-hackathon-hardening*.md`) — read top-of-file Claude Code Prompt + status sections only
- New `/future` test surfaces (`FutureScreen.test.tsx` first 200 lines, `educationFilter.test.ts`, `ErrorBoundary.test.tsx`, `SelectedNodeCard.test.tsx`)
- The `mcp_client._validate_args` boundary (re-verified its enforcement against the new chat-path callers)
- `models/api.py` validators for `AskScope` (which surfaced S3)

I did NOT re-cover:
- The unchanged production paths the prior audit already covered (Gemma fan-out semaphore, QueryEngine concurrency, transaction-wrapped wrapped-frame writes, JSONL audit log, etc.)
- The full `IpedsFinanceIngestor.flatten` body past line 900 (skimmed; no findings)
- `governance/` artifacts (skimmed only — pipeline-output, not source-of-truth)
- The 1,105-line `set_your_course.py` (already covered in prior audit; status unchanged)
- The 3,640-line `futureproof_server.py` (already covered in prior audit; status unchanged — deferred per the prior audit's own guidance)

---

## Closing

The code is good. The work is real. The discipline is real. The team has been busy.

The packaging — for the second audit cycle in a row — is the drag. The first 30 seconds a Google reviewer spends on this repo is `git log` and `ls`. Right now `git log` shows none of the audit-driven hardening, none of the new pipeline ingestors, and none of the new `/future` surface. The prior audit's first finding ("109 file changes from in-flight refactor blocking the branch") has recurred at exactly the moment it was supposed to be solved — the cleanup that addressed it is itself uncommitted.

This is fixable in one afternoon. Commit. Push. Move the two hardening specs into `completed/`. Fix S2 (10 lines) and S3 (5 lines). Then the substance carries the review.

Look, I love Claude, BUT — okay, fine, the substance is genuinely good. **A- on what shipped, B on whether anyone outside this checkout can see that it shipped. Land the commits and it's an A.**

Don't make the reviewer guess.
