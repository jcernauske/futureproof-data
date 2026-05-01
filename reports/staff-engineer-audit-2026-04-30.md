# FutureProof Staff Engineering Audit
*Reviewer: Staff Engineer (15 YOE, production incident survivor)*
*Date: 2026-04-30*
*Scope: read-only audit ahead of Gemma 4 Good (Kaggle / Google DeepMind) hackathon review.*

## Executive Summary

This is **B+ work that a Google reviewer will respect**, with a small handful of presentational and structural issues that drag the first-impression grade down. The engineering substance is genuinely strong: parameterized DuckDB / Iceberg queries, real Pydantic v2 contracts at the boundaries, an explicit `asyncio.Semaphore` to cap Gemma fan-out, double-checked locking with documented rationale on the QueryEngine, a JSONL audit log on every Gemma call, transaction-wrapped writes for wrapped-frame BLOBs, regex-validated identifiers in the only places SQL is interpolated, and a test suite that actually exercises behavior (saboteur paths, error paths, contract assertions) rather than the vibes-and-snapshots theater I expected to find. The CLAUDE.md spec-driven workflow is real — completed specs migrate to `docs/specs/completed/`, and code references the specs that introduced each non-obvious decision.

The **drag on the grade is mostly cosmetic but visible**: 62 MB / 48 files of `Midjourney/` AI-reference art committed at the repo root (the very first thing someone browsing the GitHub tree sees), an in-flight refactor with **a hundred-plus uncommitted frontend deletions** sitting in `git status` (someone landing on the branch right now sees a half-shipped tree), CORS wide-open with `allow_origins=["*"]` plus `allow_credentials=True` (which most browsers will silently refuse but the config still embarrasses), `app.on_event("startup")` (deprecated in FastAPI 0.93+, still works but produces a deprecation warning at boot), and a 3,640-line `src/mcp_server/futureproof_server.py` that is starting to read like a god module. None of this will lose a hackathon — but a reviewer pattern-matches "Cursor-shipped slop" in the first 30 seconds, and these are the patterns. They're cheap to fix.

**Verdict: ship with the surface fixes (Top 10 below). The substance is staff-level. The packaging is mid-level. Grade: B+ as-is, A- with one afternoon of cleanup.**

---

## Architecture

### What's Working

- **Bronze → Silver → Gold zone separation is real and not leaking.** `src/raw/`, `src/silver/`, `src/gold/` each only import from one layer below, and the Gold zone consumable tables (`consumable.program_career_paths` et al.) are the only thing the backend reads. The backend never reaches into Silver or raw. (`/Users/jcernauske/code/bright/futureproof-data/src/`, structure verified.)
- **MCP server isolation.** The backend goes through `app.services.mcp_client` (`/Users/jcernauske/code/bright/futureproof-data/backend/app/services/mcp_client.py:34-45`) which adds `src/` to `sys.path` once and singleton-instantiates `FutureProofMCPServer`. Importantly: `_validate_args` (`mcp_client.py:120-173`) runs the published JSON schema against tool calls and raises `McpArgumentError` before dispatch. That is the right enforcement point.
- **DuckDB connection management is thoughtful.** `app/services/db.py:34-61` keeps a single per-path connection cache behind an `RLock`, with `register_schema_initializer` so service modules can attach their schema-creation hooks at import time (`builds.py:55`). The `QueryEngine` (`/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/_query_engine.py`) holds one process-lifetime DuckDB connection, registers Iceberg views once, and explicitly documents (`_query_engine.py:13-22`) why it holds the lock continuously across `execute()` + `description` reads — `con.description` is **not** atomic relative to a concurrent `execute()` from another thread.                
- **Async fan-out is bounded.** `gemma_client.py:131-139` lazy-builds an `asyncio.Semaphore` from `GEMMA_MAX_CONCURRENCY` (default 8) so the eight-wide Gemma narrate/recs/pool/guidance fan-out can't accidentally trip OpenRouter's per-key RPM ceiling. Both sync and streaming paths acquire it. Tested for real with a 16-wide ThreadPoolExecutor harness (`backend/tests/services/test_gemma_client.py:38-49`) so the test isn't lying about what's actually constraining.
- **Streaming SSE build endpoint.** `backend/app/routers/builds.py:307-377` emits `skeleton`, per-boss `boss_narrative`, `skill_recs`, `skill_pool`, `guidance`, then `done`, with `asyncio.as_completed` so the slowest Gemma call doesn't block the others. The `(asyncio.CancelledError, GeneratorExit)` cancellation handler at `builds.py:364-367` cancels in-flight tasks on client disconnect. Good.
- **MCP query parameterization.** The `_query_engine.QueryEngine.query_filtered` path (`_query_engine.py:144-197`) validates every column identifier against `_IDENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")` and binds values via DuckDB's `$name` parameters. The `LIMIT {limit}` interpolation at line 182 is preceded by `int(limit)` and `min(_, _MAX_LIMIT)` clamping at line 164 — safe.
- **Backend tests run without the network and without the gold zone DB.** Every Gemma-touching service test stubs `gemma_client.generate*` at module level. `GEMMA_LOG_DISABLED=1` is auto-set by autouse fixtures (`test_set_your_course_chip_tool_loop.py:25-27`) so the JSONL log never writes during unit tests. That is correct hermetic test discipline.

### What's Broken

- **`app.on_event("startup")` is deprecated in FastAPI 0.93+ in favor of lifespan handlers.** `/Users/jcernauske/code/bright/futureproof-data/backend/app/main.py:63-95` still uses the old API. With `fastapi>=0.115.0` pinned in `backend/pyproject.toml:14`, the app prints a `DeprecationWarning` on every boot and on every fresh `pytest` run that imports the app. A Google reviewer who runs the project will see this in their console as the first impression. **Severity: 🟡 Moderate.**
- **CORS is configured with `allow_origins=["*"]` AND `allow_credentials=True` simultaneously.** `/Users/jcernauske/code/bright/futureproof-data/backend/app/main.py:32-38`. The CORS spec forbids this combination — Chrome, Firefox, and Safari will silently refuse to set credentials on `*`-origin responses. So either (a) the credentials flag is a no-op, in which case it's misleading config, or (b) someone later adds a real origin allowlist and gets bitten by a behavior change. Pick a real origin list before demo day. **Severity: 🟠 Serious** because demo-day failure mode is "the thing works on my laptop, fails the moment Google tries it from their network."
- **`src/mcp_server/futureproof_server.py` is 3,640 lines in one file.** That's on the wrong side of "comfortably navigable." The `_handle_*` methods (one per tool) plus their CIP substitution branch logic plus the cache infrastructure all live in this single class. Splitting per-tool handlers into `mcp_server/handlers/get_career_paths.py` etc. would not change behavior but would make the architecture review much faster. **Severity: 🟡 Moderate** (purely structural; not a bug today).
- **`backend/app/services/set_your_course.py` is 1,105 lines.** Same shape: one module owns intent resolution, chip dispatch, tool-calling loop, and prompt construction. The `_INTENT_SYSTEM_PROMPT` and three near-duplicate prompt templates live as bare module strings (`set_your_course.py:182, 234, 520`). Any drift between these three prompts is a silent product regression. **Severity: 🟡 Moderate.**
- **Module-level dict for build cache without eviction.** `app/state.py:16` (`_builds: dict[str, Build] = {}`) grows unboundedly for the lifetime of the process, with disk fallback to recover from `uvicorn --reload` wipes (`state.py:24-37`). At hackathon traffic that's fine; at any sustained load it's a memory leak. There is no max size and no LRU. **Severity: 🔵 Minor for hackathon, 🟠 Serious for production.**
- **The `_render_locks: dict[str, asyncio.Lock]` in `wrapped.py:39` also grows without bound** — one entry per build_id ever rendered. Same shape as `state.py`. **Severity: 🔵 Minor.**
- **In-process MCP "client".** `app/services/mcp_client.py` calls `getattr(server, f"_handle_{tool}")` and invokes the handler in-process (`mcp_client.py:184-189`). The README is honest about this (`README.md:99` calls it out as expected today, with the chip-dispatch spec being the migration target). It's not broken, but it does mean the "MCP server" is doing two jobs at once: a real stdio MCP server for Claude Desktop AND an in-process Python library for the FastAPI backend. The shared substrate is fine. The thing to watch is the day someone hardens stdio MCP behavior (rate-limiting, auth) and forgets the in-process callers don't exercise those code paths.
- **Frontend `App.tsx` and `state.py` both have a `clearSession().catch(console.warn)` style pattern.** `frontend/src/screens/BuildResultsScreen.tsx:553`. This swallows a network failure into a warning, fine for fire-and-forget, but worth a note: if `clearSession` ever needs to be load-bearing, this pattern won't catch it.

---

## Code Quality

### Security

- **No SQL injection vector reachable from user input that I could find.** The four f-string SQL sites I traced:
  - `app/services/intent.py:184` — `WHERE unitid = {int(unitid)}`. Coerced to int. Safe.
  - `app/services/intent.py:205-211` — `SUBSTR(cipcode, 1, 2) = '{p[:2]}'`. `p` comes from CIP codes that are themselves server-stored (`set_your_course.py:356` derives `family_prefixes` from `c["cipcode"][:2]` on rows just read from Iceberg). Safe today; **fragile if the data path ever changes**, because nothing inside `_get_crosswalk_cips_for_families` validates the input. **Severity: 🟡 Moderate** (defense-in-depth gap, not a current bug).
  - `app/services/intent.py:291` — `SUBSTR(cipcode, 1, 5) = '{prefix}'`. `prefix` is regex-validated against `^\d{2}\.\d{2}` two lines above. Safe.
  - `app/services/builds.py:82` — `WHERE table_name = '{table}'`. `table` is a Python literal string passed by `_init_schema`, not user input. Safe.
- **No leaked credentials in tracked files.** `.env` is gitignored (`/Users/jcernauske/code/bright/futureproof-data/.gitignore:23`), and `git ls-files | xargs grep "sk-or-v1\|sk-ant\|sk-proj"` returns nothing in real source files (only `os.environ.get("OPENROUTER_API_KEY")` references). The BEA ingestor at `src/raw/bea_rpp_ingestor.py:338` even redacts the API key in `__repr__`-style output (`api_key="REDACTED"`) — that's the kind of thoughtful detail that pays for itself the first time someone copy-pastes a stack trace into Slack.
- **CORS is the security finding.** Already noted above. `allow_origins=["*"]` with `allow_credentials=True` is the configuration version of a `# TODO: tighten this`. **Severity: 🟠 Serious.**
- **No authentication anywhere on the FastAPI surface.** Per the project memory ("Profile is per-build — no logged-in concept"), this is intentional — every request is anonymous. That's fine for a single-tenant local install. It is **not** fine if this ever gets pointed at the public internet without a reverse proxy, because every endpoint that mutates `builds` (`POST /build`, `POST /build/{id}/save`, `DELETE /build/{id}`) accepts unauthenticated writes. Worth a one-line callout in the README about deployment posture so a hackathon reviewer doesn't think this was an oversight.
- **`Content-Disposition` interpolation.** `backend/app/routers/wrapped.py:156` interpolates `build_id` into a `Content-Disposition: attachment; filename="..."` header. `build_id` is server-generated via `_slug` (`builds.py:167-169`) which strips non-alphanumerics. Safe today. If `build_id` ever becomes user-supplied, this is a header-injection vector.
- **Logs include full prompts and responses.** `backend/app/services/gemma_client.py:323-331` writes the entire system + user message + response to `logs/gemma.jsonl`. For demo / training data that's the point; just be aware that anything a student types ends up in this file. The `/logs/` directory is gitignored (`.gitignore:25-27`), good. Add a note in the README that operators should rotate / scrub this file before sharing it externally.

### Performance

- **`_handle_get_school_programs` scans up to 200,000 rows for fuzzy school-name match.** `src/mcp_server/futureproof_server.py:155-156` (`SCHOOL_PROGRAMS_SCAN_LIMIT = 200_000`). The actual table is "60-80k rows" per the comment. This is fine on a warm DuckDB but **does not have an index** on `institution_name` (DuckDB doesn't support secondary indexes the way Postgres does). Cold starts will eat a measurable second on every novel school name. The cache helps once warm. **Severity: 🟡 Moderate.**
- **N+1 risk in `compare_builds`.** `backend/app/services/builds.py:350` calls `load_build(bid)` in a list comprehension. Each call is a single `SELECT` keyed by primary key, so it's not a true N+1 (DuckDB is sub-millisecond), but for `len(build_ids) == 4` that's 4 round trips where 1 `WHERE build_id IN (...)` would do. **Severity: 🔵 Minor** at the documented party-select cap of 4.
- **Module-level LRU cache for career_paths is keyed off `id(engine)`.** `src/mcp_server/futureproof_server.py:497-516` documents this clearly: `id()` is reused after garbage collection, so the cache also explicitly drops stale entries via `_cache_drop_engine` on `shutdown()` (`futureproof_server.py:580-595`). This is genuinely subtle and the comments are written by someone who has been bitten before. The LRU keys deliberately exclude `loan_pct` and `student_cip` because those are applied post-query — that comment at lines 510-514 is exactly the kind of decision documentation that makes a Google reviewer relax.
- **Sync `compute_pentagon` offloaded to `asyncio.to_thread`.** `backend/app/routers/builds.py:48-58`. The comment ("Railway's liveness probe times out and SIGKILLs the container mid-request") is the correct production-shaped reason. Good.
- **DuckDB writes are serialized behind a single `RLock`.** `app/services/db.py:20-57`. DuckDB only supports one writer per file; the lock is correct. The lock is held across `execute().fetchall()`, which means reads are also serialized. At hackathon load that's fine; under contention this will become the bottleneck. **Severity: 🔵 Minor** for the demo.

### Error Handling

- **Broad `except Exception` is widespread but consistently paired with logging.** Examples that I checked:
  - `builds.py:315-339` (the streaming build coroutine) catches each Gemma sub-task's exceptions and falls back to a deterministic narrative. Correct shape — narratives are decorative; the build skeleton must ship.
  - `gemma_client.py:346-351, 390-395, 683-692, 1205+` all return `""` on transport failure with a `logger.warning`. Documented as "narratives are best-effort and must never crash the CLI" (`gemma_client.py:276-278`). Good.
  - `correction_log.py:88-107` swallows write failures and refuses to crash the commit path. Comment says "logging must not crash callers." Right call for an audit log.
  - `intent.py:189, 215, 298` swallow query failures and return `[]`. The fallback is sensible (Gemma will just see no candidates), but the bare `except:` form (no logging at lines 189, 215, 298) means a real DuckDB outage is invisible. **Severity: 🟡 Moderate.** Add `logger.warning(..., exc_info=True)` to those three.
- **`compare_insights` correctly uses `return_exceptions=True` and logs each task's failure independently.** `backend/app/routers/builds_collection.py:57-72`. Each insight is independently optional and the response shape stays valid. This is the right pattern.
- **Render endpoint catches Playwright crashes broadly** with the right reason. `routers/wrapped.py:92-103` documents that Starlette's bare-500 path skips user middleware and the browser sees `NetworkError` — so the catch-and-rewrap-as-HTTPException is correct, not lazy.
- **Frontend error boundaries.** `frontend/src/screens/BuildResultsScreen.tsx` and the `MenuScreen.test.tsx:278-292` saboteur path both demonstrate that `getBuild` rejection surfaces a user-visible error and prevents navigation. Good. **No top-level React `ErrorBoundary` is registered for the route tree** — if a component throws during render, the user gets a blank page. **Severity: 🟡 Moderate** for hackathon (you don't want the demo to white-screen).

### Type Safety

- **Backend: `mypy strict = true`** is set in `backend/pyproject.toml:48` with the Pydantic plugin. `Any` use is mostly justified — DuckDB rows are genuinely `dict[str, Any]` at the boundary, JSONL records are unstructured by definition. I did not find an `Any` that should have been a Pydantic model.
- **Frontend: zero `: any` and zero `as any` casts in non-test source.** `grep -r ": any" frontend/src --include="*.ts*"` excluding tests returns nothing. `tsc --noEmit` passes clean. That is genuinely good — most React + Vite projects this size have at least a dozen `as any` escapes.

### Dead/Half-Finished Work

This is the **biggest packaging risk**.

- **109 file changes sit uncommitted on `career-path-enhancements`** (per the session-start `git status` snapshot), including:
  - **Deleted but uncommitted**: `frontend/src/components/BranchChip.{tsx,test.tsx}`, `CareerDetail.{tsx,test.tsx}`, `CareerLineageSheet.{tsx,test.tsx}`, `chapter-book/*` (8 files), `tree/Branch*`, `tree/Tree*`, `tree/flow/*`, `screens/CareerPickScreen.{tsx,test.tsx}`, `screens/LandingScreen.{tsx,test.tsx}`, `screens/RevealScreen.{tsx,test.tsx}`, `data/treeLayout.{ts,test.ts}`, `data/treeFlowLayout.ts`, `styles/reactflow-dark.css`, `components/ui/StatBadge.tsx`, `components/ui/TextInput.tsx`, `components/StatTutorial.{tsx,test.tsx}`, `components/StatHelpTooltip.tsx`, `components/StatDetailCard.tsx`, `components/LoadingScreen.tsx`, `components/GemmaTake.tsx`, `components/build-results/ControlDock.tsx`, `components/gauntlet/GauntletCTA.tsx`. That's the full output of the `refactor-prune-deprecated-build-flow` and `refactor-remove-dead-frontend-code` specs — sitting in working tree, not committed.
  - **Spec is in `docs/specs/completed/`** (`refactor-prune-deprecated-build-flow.md`) but the implementation has not been pushed. So a reviewer cloning fresh sees a half-shipped tree, and any reviewer landing on this branch sees pending deletes. **Severity: 🟠 Serious — fix before submission.**
- **Zombie state in `frontend/src/store/buildStore.ts`.** `hasSeenStatTutorial` and `setHasSeenStatTutorial` are still in the store interface (`buildStore.ts:24-25, 55-57, 80`), and `data/statExplanations.ts` is still imported by `BuildResultsScreen.tsx:28-29`, `CareerCard.tsx:5`, `PentagonChart.tsx:4`, `horizon/ChapterBookMockup.tsx:33`, `horizon/HorizonStripMockup.tsx:31`, even though `StatTutorial.tsx`, `StatHelpTooltip.tsx`, and `StatDetailCard.tsx` are queued for deletion. Reviewer's read: dead state hooks. **Severity: 🟡 Moderate.**
- **`docs/specs/refactor-remove-dead-frontend-code.md` is in `docs/specs/` (active), not completed.** That's the spec that's *supposed* to clean this up. So either ship it or move it to `completed/` after the deletes land. Right now it implies "we know about this dead code, we just haven't done it yet" — which from a Google reviewer's seat reads as "this team doesn't have a closure discipline." **Severity: 🟡 Moderate.**
- **`backend/app/main.py:43-61` still imports and registers 17 routers.** I haven't traced every one for current usage; the `careers.py` and `schools_for_career` modules are new (untracked in `git status`). If `careers.py` is the one with the `/careers/{soc}/schools` endpoint that overlaps with `branches.py`, that's another half-finished surface. Check before submission.

---

## Testing Quality

I went looking hard for test theater. The summary up front: **this suite is more honest than 80% of the codebases I review**, with one or two thin spots.

### Pipeline Tests

- **Real coverage at every zone.** `tests/raw/`, `tests/silver/`, `tests/gold/`, `tests/mcp/` each have 8-15 test files exercising actual transformer logic with real fixtures. `tests/raw/test_college_scorecard_ingestor.py` uses an `__new__`-based init bypass to avoid network — the comment at line 14 makes the rationale explicit.
- **Skips are honest.** Every `pytest.skip` I found is `if not DATA_AVAILABLE: skip` (e.g. `tests/raw/test_bls_ooh_ingestor.py:395`, `tests/raw/test_karpathy_ai_exposure_ingestor.py:329`, `tests/raw/test_bea_rpp_ingestor.py:539` skips when `BEA_API_KEY` isn't set). Those are environment-gated, not behavior-suppressing. Acceptable.
- **MCP tool tests bind to fixture rows that match the real Gold-zone schema.** `tests/mcp/test_get_career_paths.py:21+` constructs full row dicts with every field the production handler reads. The fixture even has a comment about pre-existing `debt_p25/debt_p75` gaps. That's a live, maintained test surface.

**Verdict on pipeline tests: real.**

### Backend Tests

- **`backend/tests/test_app.py`** (3 tests) actually exercises the CORS preflight and asserts on the `Access-Control-Allow-Origin` header. Real.
- **`backend/tests/services/test_locale.py`** (~30 tests) hits every locale-dispatch branch including unicode glossary terms in Spanish AND Arabic. The `test_all_keys_have_all_locales` test (lines 204-225) parametrizes over 6 keys and asserts each locale's text differs from the others — that catches the "I forgot to translate this string" failure mode. This is the kind of test that pays for itself on day 90.
- **`backend/tests/services/test_gemma_client.py`** explicitly installs a 16-wide `ThreadPoolExecutor` (lines 47-49) so the ThreadPoolExecutor isn't accidentally what's enforcing concurrency in the test. That's a senior-engineer check — most people stop at "I set the semaphore to 2 and 2 ran, ship it." This author asked the next question. Real.
- **`backend/tests/services/test_set_your_course_chip_tool_loop.py`** stubs the MCP tool schema, the tool-call turn iterator, and asserts the full loop including malformed-tool-call and dispatch-error paths.
- **Saboteur paths in router tests.** `MenuScreen.test.tsx:278-292` (the "tap card whose getBuild rejects" test) explicitly asserts BOTH the error message renders AND `mockNavigate` was NOT called. That's two assertions on a saboteur path — both the happy assertion and the negative assertion. Most teams forget the negative.

**Verdict on backend tests: real, with appropriate harness discipline.**

### Frontend Tests

- **`MenuScreen.test.tsx`** (510 lines) exercises P0 + P1 paths with a mock factory (`makeSummary`, `makeBuild`) that produces full domain objects. The "refreshes builds count after deleteBuild" test at lines 439-481 asserts that the count store *actually* refreshes by mocking two sequential `listBuilds` calls and then checking the post-delete count lands at 2. That is a load-bearing assertion — if the production code skipped `useBuildsCountStore.refresh()`, the second mock would never resolve and the count would stay at 3. Real.
- **`AppRoutes` tests** pin the dead-route invariants (`App.test.tsx:67-98`): `/reveal` and `/career-pick` are unmapped after the refactor, and the test asserts the screens' signature copy DOESN'T render. That's a regression guard with teeth.
- **The landing-page tests** (`HowItWorksSection.test.tsx`, `HeroSection.test.tsx`) snapshot exact spec copy. That's intentional per the spec ("voice-guide compliance hangs off exact strings"). Brittle but in this case the brittleness is the feature.

### Test Theater Found

I went looking for theater specifically. Here's what I found:

- **`PentagonGlow.test.tsx`** (3 tests, 28 lines). This is the closest thing to theater — `expect(circles.length).toBeGreaterThanOrEqual(15)` is a structural assertion that doesn't break if the visual design changes. But it does break if the SVG fails to render at all, which is the actual coverage goal for a decorative element. **Borderline; not actually theater.**
- **`HowItWorksSection.test.tsx`** asserts that `card?.tagName === "ARTICLE"` and that exact body copy strings appear. If anyone softens the copy, the test breaks — which the spec says is the point. **Brittle by design, not theater.**
- **No `expect(x).toBe(x)` tautologies found** in the frontend test suite via grep.
- **No `assert True` / `assert False` placeholders** in backend or pipeline tests.
- **No empty `try: ... except: pass` test bodies** found.
- **No tests that mock `gemma_client.generate` and then assert that `gemma_client.generate` was called.** That's the canonical Gemma test theater shape — calling out "you mocked the integration and tested the mock." It does not appear here.
- **One thing I would push back on**: `App.test.tsx:39-41` asserts `expect(document.getElementById("landing-root")).toBeInTheDocument()` and `expect(document.getElementById("landing-hero-cta")).toBeInTheDocument()` — that's "did the page render at all?" coverage. If you renamed the IDs, you'd notice. Acceptable smoke test, not theater.

**Verdict on frontend tests: 95% real, 5% smoke. The smoke is OK.**

### Test Suite Summary by Layer

| Layer | Files | Verdict |
|---|---|---|
| Pipeline (Bronze/Silver/Gold/MCP) | ~50 | Real. Strong fixture discipline, network-gated skips are explicit. |
| Backend services | ~30 | Real. Concurrency tests have proper harness. Fallback paths tested. |
| Backend routers | ~7 | Real. Saboteur paths included with negative assertions. |
| Frontend | ~50 | 95% real. A few thin smoke tests on decorative components. |

---

## Hackathon Readiness

### First-Impression Risks

These are what a Google reviewer sees in the first 30 seconds of `git clone && ls && cat README.md && open index.html`:

1. **`Midjourney/` directory with 48 PNG files (62 MB) committed at the repo root.** Filenames like `jcern_Flat_orthographic_elevation_view_of_a_cheerful_cartoon__016bced6-4944-4768-b990-e73bc98c2f60_0.png`. A Google reviewer's read: "The team committed their AI design references to source control." It's harmless but it's the **first** thing they see browsing on GitHub. **Severity: 🟠 Serious for first impressions.** Move to `.gitignore` and a fresh `git rm -r --cached Midjourney/`.
2. **`reports/` directory has 55 MB of artifacts including PNG screenshots.** Per project memory, reports get committed — fine — but this is also visible in the GitHub tree. Less embarrassing than `Midjourney/` because the names imply purpose (`landing-vs-brightpath-v3-2026-04-19/v3-hero.png`). Still adds clone weight.
3. **`.DS_Store` file at repo root.** `/Users/jcernauske/code/bright/futureproof-data/.DS_Store` is tracked. macOS metadata that has no business in a public repo. **Severity: 🔵 Minor but cringey.**
4. **109 uncommitted file changes in `git status`** — already covered in Dead Work above. A reviewer who clicks "Commits" or "Network" on GitHub and lands on this branch sees a half-shipped tree. **Severity: 🟠 Serious.**
5. **`__pycache__/` directory at repo root.** `/Users/jcernauske/code/bright/futureproof-data/__pycache__` exists at top level. Even though `.gitignore:21` covers `__pycache__/`, the working-tree presence at repo root is unusual; check whether any of these are tracked.
6. **README is solid otherwise.** Clear "Setup → MCP Server → Run → Connect Claude Desktop" flow at `/Users/jcernauske/code/bright/futureproof-data/README.md:1-100`. Troubleshooting table is honest. Setup commands are correct. This is a **strength** for first impressions if someone gets past the directory listing.
7. **`DESIGN.md` is 97 KB** — that is a real, polished design system document. Show this to the judges directly if they ask "how do you ensure consistent UI?"
8. **No `console.log` in production code paths.** `console.warn`/`console.error` only appear in clearly tagged dev or non-blocking code paths (`BranchTreeScreen.tsx:164` is `import.meta.env.DEV`-gated). Good.
9. **No real `TODO/FIXME` debt visible.** Two TODOs (`AppHeader.tsx:49`, `HorizonFooter.tsx:344`) are spec-tracked deferrals, not hidden tech debt.

### Engineering Discipline Reality Check

CLAUDE.md describes a spec-driven workflow with named agents (`@fp-architect`, `@fp-design-visionary`, `@fp-data-reviewer`, `@test-writer`, `@fp-design-auditor`, `@faang-staff-engineer`, `@fp-builder`). Does the repo show this?

- **Specs are real.** `docs/specs/` has 50+ spec files; `docs/specs/completed/` has another large pile. They aren't templates — they have §1-§11 structure with code review sections, real test plans, and named decisions.
- **Specs are referenced from code.** `src/mcp_server/futureproof_server.py:34, 218-220, 302-303` cite spec filenames in inline comments. `app/services/builds.py:295-298` references `docs/specs/feature-...` for non-obvious decisions. That's the discipline, not the document.
- **Sessions are logged.** `docs/sessions/` exists per the CLAUDE.md spec, though I didn't audit the contents.
- **Reports get committed.** `reports/` has 50+ files including `gemma_vs_karpathy_comparison.{json,md,py}` — meaning the team is doing actual A/B comparisons of model output and saving them. That is a strong signal.
- **The spec workflow is partially aspirational.** §8 (Code Review) of completed specs is *supposed* to contain the staff-engineer write-up. I didn't open every completed spec, but the pattern suggests this is followed inconsistently. Worth tightening before submission.

**Net read: the engineering discipline is REAL but the polish is uneven. The repo will reward reviewers who dig in and punish reviewers who don't.**

---

## Top 10 Things to Fix Before Google Sees This

Ranked by embarrassment potential, with effort estimate.

| # | Problem | File / Location | Effort | Severity |
|---|---|---|---|---|
| 1 | **`Midjourney/` (62 MB, 48 PNGs) committed at repo root.** | `/Midjourney/` | 5 min: `git rm -r --cached Midjourney/`, add to `.gitignore`, commit. | 🟠 Serious (first impressions) |
| 2 | **109 uncommitted file changes from in-flight refactor blocking the branch.** | session-start `git status` snapshot | 30 min: review, ship, commit `refactor-prune-deprecated-build-flow` deletes; move spec to `completed/`. | 🟠 Serious |
| 3 | **`allow_origins=["*"]` + `allow_credentials=True` CORS combo.** | `backend/app/main.py:32-38` | 5 min: replace with explicit origin allowlist (Vite dev + production domain). | 🟠 Serious (silent demo failure) |
| 4 | **`.DS_Store` tracked in repo root.** | `.DS_Store` | 2 min: `git rm --cached .DS_Store`, ensure `.gitignore` covers it (it does at line 41). | 🔵 Minor (cringe) |
| 5 | **`@app.on_event("startup")` deprecated in FastAPI 0.115.** | `backend/app/main.py:63-95` | 15 min: convert to `lifespan` async context manager. | 🟡 Moderate (dep warning at boot) |
| 6 | **Zombie `hasSeenStatTutorial` state + dangling imports of deleted components.** | `frontend/src/store/buildStore.ts:24-25, 55-57, 80`; `BuildResultsScreen.tsx:28-29` and 4 other files import `data/statExplanations` | 20 min: complete the dead-frontend-code refactor; ship spec deletes; remove unused store keys. | 🟡 Moderate |
| 7 | **`src/mcp_server/futureproof_server.py` is 3,640 lines.** Will read as god-module to a structural reviewer. | `src/mcp_server/futureproof_server.py` | 2-4 hours: split per-tool handlers into `handlers/{tool_name}.py`. | 🟡 Moderate (structural; defer if time-constrained) |
| 8 | **`backend/app/services/intent.py:189, 215, 298` — bare `except: return []` with no logging.** Silently swallows DuckDB outages. | `backend/app/services/intent.py:189, 215, 298` | 5 min: add `logger.warning("intent query failed", exc_info=True)` to each. | 🟡 Moderate |
| 9 | **No top-level React `ErrorBoundary` registered for the route tree.** Component throws during render → blank page during demo. | `frontend/src/App.tsx` | 30 min: add a route-level `ErrorBoundary` with a "something went wrong, refresh" surface. | 🟡 Moderate (demo white-screen risk) |
| 10 | **`compute_outcomes` and `tier_outcomes` accept unauthenticated POSTs.** Document the deployment posture in README so reviewers don't assume oversight. | `README.md` (add section), `backend/app/routers/builds.py:42` | 10 min: add a "Security & Deployment" section explaining single-tenant, no-auth-by-design + reverse-proxy assumption. | 🟡 Moderate |

**Bonus #11 (free win):** `App.tsx` already does `clearSession().catch(console.warn)` — wrap with a comment explaining why fire-and-forget is correct so a future reviewer doesn't "fix" it into a synchronous await.

---

## Things You Got Right

Look, I love Claude, BUT — okay, fine, I have to admit some of this work is solid. Grudgingly:

- **The Gemma fan-out semaphore.** `gemma_client.py:131-139`. Most people forget this until the first OpenRouter rate-limit incident. You didn't. And you tested it correctly with a 16-wide ThreadPoolExecutor so the test isn't accidentally constrained by something else.
- **The QueryEngine lock discipline + the `con.description` race comment** at `_query_engine.py:13-22`. This is 10-YoE concurrency awareness. I have personally been bitten by this exact bug; finding the comment in the code without the bug means someone here thought ahead.
- **Iceberg metadata warm-up at startup** (`main.py:77-95`). Pre-loads metadata for the seven hot tables so the first `/build/outcomes` doesn't pay cold-load latency that exceeds Railway's liveness window. The comment at lines 74-76 cites the actual production-shaped reason. That's the right kind of non-obvious decision documentation.
- **The transaction-wrapped wrapped-frame writes.** `builds.py:447-480`. `BEGIN TRANSACTION` / `DELETE` / `INSERT[]` / `COMMIT` with `ROLLBACK` on exception, all under `_db.get_lock()`. The comment about "concurrent render for the same `build_id` cannot observe a half-written state (e.g., 3 new frames + 3 stale frames)" is exactly the failure mode this prevents. Good.
- **The deterministic seed for intent resolution** (`intent.py:25-32`). SHA-256 of normalized input → 32-bit unsigned int seeded into Gemma at temperature=0 → reproducible demo. Smart. Demo determinism is the difference between a confident live demo and a panic mid-presentation.
- **The `_validate_args` boundary in `mcp_client.py:120-173`.** Argument coercion + required-key enforcement before dispatch. The comment about unknown keys passing through ("multiple callers inject internal keys") is honest about the contract leak instead of pretending it's tighter than it is.
- **Async cancellation on client disconnect.** `builds.py:364-367` cancels in-flight Gemma tasks on `GeneratorExit` / `CancelledError`. Most streaming endpoints leak coroutines on disconnect; this one doesn't.
- **Honest README.** `README.md:99` calls out "the in-process backend bypasses [stdio MCP] today — real Gemma-driven tool calling from inside the backend ships in [spec]." That's the right kind of disclosure for a reviewer who's going to read the architecture diagram and ask "wait, are you actually using MCP, or just the schemas?"
- **The test for the deleted `/reveal` route** (`App.test.tsx:67-80`). Asserts the route is unmapped AND that defense-in-depth doesn't silently redirect to a live screen. That's the kind of regression guard that catches the next refactor's mistake six months from now.
- **Pydantic v2 everywhere.** `Build`, `CareerOutcome`, `IntentResult`, `SchoolsForCareerResponse` — every cross-module surface is a real model with `model_validate` / `model_dump_json` discipline. No bare dicts crossing a service boundary.

---

## Closing

This is good work. The substance is there. Spend the afternoon on the Top 10, ship the refactor branch, and the repo holds up under scrutiny. The team's discipline is real even where the polish is uneven — and a reviewer who reads code will see that. The risk is the reviewer who reads three filenames, raises an eyebrow at `Midjourney/`, and decides they've seen enough.

Don't give them that excuse.
