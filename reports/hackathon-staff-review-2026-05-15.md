# Hackathon Submission Review — 2026-05-15

*Reviewer: Staff Engineer (15 YOE)*
*Submission target: Gemma 4 Good Hackathon (Kaggle / Google DeepMind), deadline 2026-05-18*

## Verdict

**Ship-with-fixes.** This is a meaty, thoughtful submission. The deterministic-vs-Gemma split is real, the eval is honest (including the 4.5% hallucination rate they didn't bury), tool-call fallback ladders are documented, secrets handling is clean, and the hosted demo is live and reachable. I came in expecting smoke — there isn't much. **But there are two issues that will burn a judge in under five minutes if they exercise the published install path:** (1) every Iceberg metadata file and the catalog SQLite database have the original author's absolute filesystem path baked in, so a `git clone` to anywhere except `/Users/jcernauske/code/bright/futureproof-data` produces a process that boots clean but returns empty result sets the moment a tool query runs, and (2) `GET /builds` on the hosted demo returns every other visitor's builds without any scope. Neither is hard to mitigate before the deadline. Everything else on the P0/P1 list is fixable in hours, not days. Fix the path-baking story (or warn loudly in the README), close `/builds`, and this is a confident submit.

---

## P0 — Must fix before submission

1. **Iceberg catalog has the author's absolute path baked into every row**
   - `data/catalog/catalog.db` and every `data/{bronze,silver,gold}/iceberg_warehouse/.../metadata/*.metadata.json` file embed the string `/Users/jcernauske/code/bright/futureproof-data/...` as the table location. Confirmed by `strings data/catalog/catalog.db | grep jcernauske` and by sampling a Gold metadata.json — both have hardcoded absolute paths. The `backend/Dockerfile` openly acknowledges this and works around it by setting `WORKDIR /Users/jcernauske/code/bright/futureproof-data` inside the container, but no such workaround exists for a local clone.
   - **Blast radius:** A judge who runs the Quickstart (`git clone … && cd futureproof-data && ./scripts/setup.sh && ./scripts/dev.sh`) will get a clean boot, a green `/health`, and a Gemma reachable badge — but the *first* `/intent/stream` or `/build` call will fail to resolve any table data. `_query_engine._ensure_initialized` silently swallows per-table registration failures (`src/mcp_server/_query_engine.py:112-117`), so the failure mode is "empty result sets and zero career rows" rather than a clear error. That's a 3am-page failure mode in a Quickstart context.
   - **Suggested fix:** Either (a) ship a one-shot `scripts/relativize_iceberg_paths.py` invoked at the end of `setup.sh` that rewrites every metadata.json and the catalog.db to use `$REPO_ROOT`, or (b) prominently warn in the README Quickstart that the local-install path must match `/Users/jcernauske/...` *or* add a symlink, or (c) rebuild the catalog at install time from the on-disk metadata files via a `pyiceberg` script (slower, but path-portable).

2. **`GET /builds` returns every visitor's builds with no scoping**
   - `backend/app/routers/builds_collection.py:22-27` exposes `list_builds(profile_name?)` with `profile_name` purely optional. Anyone hitting `https://futureproof.hyenastudios.com/api/builds` (or whatever the proxy path is) gets every build every visitor has ever created — school choice, profile_name, animal_emoji, career_title, ERN/ROI/RES/GRW/AURA, win/loss/draw counts. Even without strict PII, that's cross-tenant data exposure, and the README at line 393 explicitly promises "no PII collection" which a judge will read as "my session is private from other users."
   - **Blast radius:** A curious judge runs `curl https://.../builds` and sees the build history of every prior test user including any internal demo runs. Reputation hit.
   - **Suggested fix:** Make `profile_name` required (FastAPI `Query(..., min_length=1, max_length=200)`), and have the router 422 when missing. The frontend already passes it. Bonus: combine with an opaque per-profile token stored in localStorage so guessable profile names like `dancing-happy-bear` aren't enumerable.

3. **Build IDs are sequential and globally enumerable; any build is publicly readable by ID**
   - `backend/app/services/builds.py:174-187` (`_next_id_for`) generates IDs like `iu-b-marketing-001`, `iu-b-marketing-002`, … `GET /build/{build_id}` (`backend/app/routers/builds.py:585-595`) and `POST /chat/ask` (`ask_gemma_router.py:51-70`) will happily serve any build whose ID is guessed. There's no concept of ownership.
   - **Blast radius:** A judge who notices their build_id ends in `-007` immediately tries `-001` and reads someone else's full build (school, major, debt assumptions, narrative). This is the same privacy issue as #2 but reachable from the public API even after #2 is fixed.
   - **Suggested fix:** Append a 6-8 char random suffix to the deterministic slug (e.g. `iu-b-marketing-001-x7k9`). Still human-readable for the compare flow, no longer enumerable. Pair with a session cookie or `X-Profile-Token` header check for `GET /build/{id}` and `POST /chat/ask`.

4. **`set_your_course.handle_chip_dispatch` 500 leaks the exception type to the client**
   - `backend/app/routers/set_your_course.py:84-90` catches every exception and re-raises as `HTTPException(500, detail="chip dispatch failed")`. That detail is fine, but the streaming sibling at line 51-57 leaks `{"message": "stream failed — try again."}` only after first running an unbounded `set_your_course.stream_initial_resolution` whose internal Gemma calls or MCP dispatch can leak provider names / model tags in the error path. Less of a security issue, more of a "did we just tell the judge our backend stack" smell.
   - **Blast radius:** Minor info-disclosure if a judge intentionally fuzzes `/intent/stream`. Not the lede; flagging because it's adjacent to the bigger issues here.
   - **Suggested fix:** Wrap `set_your_course.stream_initial_resolution` calls in the same `except Exception as exc` shape as the chip endpoint; log the full exception with `logger.exception` (already done) but emit only a sanitized `"message": "stream failed — try again."` to the client.

5. **README claim vs reality: "12 tools, 11 in active use" is misleading on Ollama (E4B)**
   - README §"Function calling" (line 350-365) lists 11 of 12 tools as actively used, with the 12th (`get_ai_exposure`) marked "registered, not in use." That's accurate for the OpenRouter / 26B path. On the Ollama / E4B path, `ask_skip_tool_calling=True` is hard-coded in `gemma_client.runtime_profile()` (line 124), so free-form Ask the Guide on E4B issues *zero* tool calls — it falls through to single-shot `generate_async` (`ask_gemma.py:4105-4112`). README line 493 *does* acknowledge "function calling is unreliable" on E4B, but the headline tool inventory table doesn't reflect that the "Gemma-callable" half of the deterministic-vs-Gemma split essentially turns off on the local-first deployment story they're pitching to schools.
   - **Blast radius:** A judge running the Ollama track demo will not see Gemma issue a tool call for Ask the Guide, contradicting the prominent "11 in active product use" framing. They'll either think the system is broken or that the README oversold.
   - **Suggested fix:** Add one sentence to the "Function calling" section: "On Ollama with `gemma4:e4b`, free-form Ask the Guide skips the tool loop entirely (single-shot generation with full build context) because E4B's tool-call reliability is low; deterministic explain-stat receipts still fire tool calls via the registry dispatch path on both runtimes." That matches what's actually shipping.

---

## P1 — Should fix if there's time

1. **`_query_engine._ensure_initialized` silently skips broken table registrations**
   - `src/mcp_server/_query_engine.py:112-117` does `except Exception … logger.debug(…) … continue`. If a metadata path is bad (which happens in the P0-#1 scenario), every affected table is silently dropped from `_views`. `main.py:79-101` does a single warmup query against `consumable.occupation_profiles` and reports the view count — but a partial registration failure still passes the warmup if `occupation_profiles` happens to load and the rest don't.
   - **Suggested fix:** Promote the per-table skip to `logger.warning` and add a startup-time assertion that the 10 Gold consumable tables are all present in `_views`. Fail fast at boot rather than discover the gap one request at a time.

2. **`profile_name` filter on `GET /builds` doesn't validate format**
   - Even after the P0-#2 fix, `profile_name` is currently `str | None = Query(default=None, max_length=200)` (`builds_collection.py:24`). The animal-themed name format is well-defined (`adjective verb animal`) but nothing enforces it server-side. An attacker can pass `'; DROP TABLE builds; --` — DuckDB parameterized queries will handle it safely, but you don't want it in logs either.
   - **Suggested fix:** `pattern=r"^[a-z]+(?:[- ][a-z]+)*$"` on the Query parameter so anything weird returns 422 before it reaches the DB.

3. **`_log_exchange` writes full Gemma prompts + responses to `logs/gemma.jsonl` on every call**
   - `backend/app/services/gemma_client.py:479-494` appends the full message history (including system prompt with the student's school, major, career, all stat scores) to disk by default. `GEMMA_LOG_STDOUT=1` is set in the Dockerfile but doesn't suppress disk writes — disk is still authoritative. On Railway with ephemeral disk this is fine, on a school's own hardware running Ollama this is the student data the local-first pitch promised never leaves the building, written to local disk under the project root.
   - **Suggested fix:** Add an `INFERENCE_LOG_FULL_MESSAGES` env var (default false in prod, true in dev) so the disk log gets the slim version when running on a school's machine. Update the privacy section of the README accordingly.

4. **CORS allows credentials with wildcard methods/headers**
   - `backend/app/main.py:114-120` sets `allow_origins` from env (good), but `allow_credentials=True` with `allow_methods=["*"]` and `allow_headers=["*"]`. Modern browsers reject wildcard + credentials together so this is more sloppiness than vulnerability, but a tightening pass before submission would be cheap.
   - **Suggested fix:** Explicit method list (`["GET","POST","DELETE","OPTIONS"]`) and an explicit header allowlist. Or set `allow_credentials=False` since the app doesn't use cookies/auth.

5. **`f"SUBSTR(cipcode, 1, 2) = '{p}'"` in `intent.py:222` interpolates user-shaped data into SQL**
   - It's safe today because `_CIP_FAMILY_PREFIX_PATTERN.fullmatch(head)` gates the loop two lines above — only two-digit numeric prefixes get through. But if anyone ever weakens that regex it becomes injection. The parameterized-query helper on the same connection (`query_sql(sql, params)`) would work here. No reason to interpolate.
   - **Suggested fix:** `WHERE cipcode LIKE $prefix || '%'` with each prefix as a separate param, or build an `IN ($p0,$p1,...)` clause with bound parameters.

6. **`compute_one` fetches every career path and filters in Python**
   - `stat_engine.py:807-846` calls `compute_pentagon` (which calls `get_career_paths` and returns every row) and then iterates to find the one selected SOC. For a popular school+major, that's ~10-30 rows fetched to use one. Not catastrophic, but it doubles the wall clock of `/build` versus a tool that filters server-side.
   - **Suggested fix:** Add a `soc_code` filter to the `get_career_paths` MCP handler so `compute_one` can request exactly the row it needs. Worth ~200-400ms on the build path.

7. **Prefetch cache grows unbounded if `consume()` never matches**
   - `backend/app/services/prefetch.py:74` is a module-level dict, evicted only on `start()` calls via `_evict_expired()`. If a user prefetches and then closes the tab, the entry hangs around until the next user triggers a prefetch (which only evicts entries older than `TTL_SECONDS=300`). Under judge-level traffic this won't matter; under any real traffic it's a slow leak.
   - **Suggested fix:** Schedule `_evict_expired` on a `BackgroundTasks` timer or fold it into the `lifespan` heartbeat.

8. **Dockerfile pins Gemma library installs via raw `pip install` outside `backend/pyproject.toml`**
   - `backend/Dockerfile:30-33` installs `fastapi 'uvicorn[standard]' pydantic duckdb jinja2 openai python-dotenv pyyaml` plus brightsmith with no version pins. This is divergent from the locked `backend/uv.lock` that's checked in. If pip resolves a different `openai` major version next week, hosted demo behavior could drift from local.
   - **Suggested fix:** `pip install -e ./backend` (already line 45) should install the full pinned set from `pyproject.toml` — drop lines 30-33 entirely. Or copy `backend/uv.lock` and use `uv pip install --frozen` for reproducibility.

9. **`_load_major_to_cip_lookup` (YAML lookup) is still wired into `_handle_get_career_paths`**
   - `src/mcp_server/futureproof_server.py:3482-3484` falls back to YAML `_find_major_intent` when no `student_cip` is provided. Per MEMORY.md, the user has explicitly asked for "no YAML lookups" as a resolution strategy. The new `/set-your-course` flow always provides `student_cip` so this rarely fires, but the CLI and the legacy `/school` flow still hit it. If `student_cip` is missing from a future code path (refactor, bug), the YAML lookup quietly substitutes.
   - **Suggested fix:** Either remove `_find_major_intent` entirely and return an explicit "missing student_cip" error, or rip the legacy fallback per the noted preference and let CLI / legacy callers fail loudly so they can be fixed.

10. **`_evict_expired` and `_log_lock` aren't tested under concurrent prefetch**
    - Not a P1 blocker, just a flag — the threading discipline in `_query_engine` and `gemma_client._log_lock` is real and considered, but I don't see a stress test that proves it holds under the actual fanout the build endpoint runs (8 Gemma calls + 8 MCP calls + 1 prefetch consume). If a judge runs the live demo concurrently from multiple tabs, you'll find out the hard way.

---

## P2 — Nice to have / post-hackathon

1. **`scripts/dev.sh` doesn't propagate child SIGTERM cleanly** — `kill -TERM "$BE_PID" "$FE_PID"` kills the wrapper subshells but not the uvicorn/vite grandchildren. On Ctrl-C from a judge's terminal you often get orphaned uvicorn processes that hold port 8000. Move to `set -m` + `kill -- -$$` (process group), or use `wait -n` semantics.

2. **`@router.get("/")` for school search has trailing-slash sensitivity** — `backend/app/routers/schools.py:8` mounts `GET /` on the `/schools` prefix, so the canonical URL is `GET /schools/`. FastAPI 307-redirects `/schools` → `/schools/`, but the Railway edge can mangle this when the proxy strips `Host` — the Dockerfile CMD's `--proxy-headers` mitigation handles HTTPS, but not the trailing-slash 307 quirk. Either drop the trailing slash in the route definition or pin `redirect_slashes=False` on `FastAPI(…)`.

3. **`logs/gemma.jsonl` is checked in via `.gitignore` exclusion?** — `git ls-files logs/` to confirm. If logs are accidentally committed, the prompt history (including school + major combos from your wife / kids per CLAUDE.md context) ships to GitHub.

4. **Iceberg `.metadata.json` files store relative-looking paths in some manifests** — Worth a one-pass audit before submission. Most are absolute; a few may also store relative paths that work by accident on the dev machine.

5. **Kaggle writeup says "9 MCP tools"; README says "12 registered, 11 in active use"** — `docs/kaggle/FutureProof-kaggle-final.md:43` and README §"How Gemma 4 is used" disagree. Pick one and propagate (12 is the truth — confirmed by `grep -c "ToolDef(" src/mcp_server/futureproof_server.py`).

6. **README §"Project structure"** lists `docs/futureproof_hackathon_prd_v8.md` (line 275) but that file doesn't exist in `docs/` — directory has spec files but no PRD with that name. Minor README-claim-vs-reality.

7. **`backend/data/futureproof.duckdb` build store is single-writer** — Documented in the Dockerfile comments (line 61-66), but the README doesn't say this. If a judge ever tries scale-out, they'll see immediate I/O exceptions. Worth one line in the README's deployment section.

8. **`compute_pentagon` raises `ValueError` with the MCP error message as the detail string** — `stat_engine.py:773-776`. Whatever the MCP handler returns ends up in the user-visible 422. Today that's fine (those messages are intentionally student-readable), but a hardening pass would scrub any internal field names from the message.

9. **`README.md` claim "8 GB RAM minimum" (line 199)** is optimistic for the local Ollama path; `gemma4:e4b` is ~4.5B params at fp16, expect ≥10GB resident with KV cache. Worth bumping to "12 GB recommended."

10. **`backend/app/routers/health.py:_probe_model` uses `httpx.AsyncClient` per call** — Each `/health` poll opens and closes a fresh HTTP client. Under Railway's liveness probe cadence this is fine, but pre-warm a module-level client if `/health` is ever hammered by the live demo's status badge.

---

## What's actually good

Grudgingly, this is a strong codebase. Things I won't touch:

- **The deterministic-vs-Gemma split is real, not marketing.** `stat_engine.py` actually scores; Gemma actually narrates. The "model never invents the score" claim survives reading the code.
- **`gemma_client.py` is the most defensively written file in the repo.** Three-tier tool-call fallback (native → content-JSON parse → re-prompt), tail-latency hedging, runtime profile that downshifts on compact local models, JSONL audit log under a lock, semaphore-bounded fanout. This is staff-level work.
- **CIP/SOC handling is rigorous.** `_CIPCODE_PATTERN`, the `CIP-family vs leaf` distinction, the substitution caveat tracking through `substitution_applied` / `data_caveat` — exactly the discipline this domain requires.
- **The DuckDB persistence layer is conservatively done** — single connection, RLock, parameterized everywhere I checked, schema initializer pattern, `_add_column_if_missing` idempotence for the migration story.
- **`_query_engine.py` lazy view registration with RLock-protected `con.description` reads** — the comment explaining why `description` isn't atomic is the kind of thing you write after a bug, not before. Respect.
- **Eval is honest.** The 4.5% hallucination flagged, the `MIT 6.830` mis-attribution called out, the methodology iteration history preserved across v1/v2/v3. Judges will read this as engineering discipline.
- **Secrets hygiene is clean.** `.env` is in both `.gitignore` and `.dockerignore`, no real keys in repo, `OPENROUTER_API_KEY` only loaded via `_resolve_config`, the template uses `sk-or-v1-REPLACE_ME`.
- **Deployment lives.** Both the YouTube demo link and the hosted demo URL respond 200.
- **Spec discipline pays off in the diff.** Recent commits (`fix(my-build):`, `feat(ask-gemma):`, `feat(inference):`) tie back to specs in `docs/specs/`. The §1-§11 structure is followed.

---

## Claims-vs-reality audit

| Claim | Source | Code reality | Verdict |
|---|---|---|---|
| "12 tools, 11 in active use" | README §"Function calling" | `grep -c "ToolDef("` in `futureproof_server.py` returns 12; `_TOOLS` in `ask_gemma.py:94-110` lists 9 (8 in chat tool loop + the eleventh `get_school_programs` invoked directly; `get_ai_exposure` excluded as documented) | **Mostly accurate.** Tool inventory matches; "in active product use" is honest if you count both Gemma-callable and direct-backend-callable. Misses the E4B caveat that free-form Ask the Guide skips tools entirely (see P0-#5). |
| "9 MCP tools" | Kaggle final, line 43 | Same as above — actually 12 registered | **Drift between README (12) and Kaggle (9).** Pick one before submission. |
| "215 labeled cases, Ollama + gemma4:e4b" | README §Evaluation | `reports/eval-v3-2026-05-13.md` exists; table sums to 100+20×5+15 = 215 | **Accurate.** |
| "21 distinct Gemma call sites" | README line 425 | `eval/instrumentation/call_site_map.py` has 21 entries (`grep -E '^\s*\".*\":'` returns 21) | **Accurate.** |
| "100/100 field accuracy on career_intent" | README + Kaggle eval section | Both report this with the same 5 OOD examples (`deaf education → 13.1003`, etc.) | **Trust the v3 report; I didn't re-run it.** Numbers self-consistent across surfaces. |
| "Same codebase runs on a school's own hardware via Ollama — no per-query cost, no student data leaves the building" | README §The problem + §Why local-first matters | `gemma_client.py` routes by `INFERENCE_BACKEND` env var, both paths fully implemented. **BUT** `logs/gemma.jsonl` is appended with full prompts including school + major on every call (`gemma_client.py:479-494`). Student data does not leave the building, but it is written to disk on the building's machine. | **Mostly accurate; tiny privacy nuance.** See P1-#3 — a sentence in the README acknowledging the disk log keeps the claim airtight. |
| "No login, no account, no analytics tracking, no PII collection" | README §Privacy line 393 | True for the input side. But `GET /builds` without auth (P0-#2) and enumerable build_ids (P0-#3) mean *other* visitors' builds — including their typed `major_text` and `school_name` — are readable. | **Inaccurate as written.** Either lock down the endpoints or rephrase the privacy claim. |
| "Switching between cloud and local Gemma 4 is one environment variable" | README §"Why this stack" line 100 | True — `INFERENCE_BACKEND=ollama|openrouter` in `.env` and `_resolve_config()` does the right thing. | **Accurate.** |
| "Brightsmith pipeline produces 66 Iceberg tables across 10 namespaces" | README §"Iceberg tables by zone" | `strings data/catalog/catalog.db | grep -c brightsmith` would confirm; spot-check shows tables in `raw`, `bronze`, `base`, `consumable`, `governance`, `shadow_*`, `silver`, `gold`, `mcp` — 9 namespaces visible. Couldn't confirm the exact 66 count in this pass, but the table breakdown in the README sums to 66 and the per-namespace counts look proportionate. | **Plausible.** A judge won't audit this. Worth one-line confirming the count via `pyiceberg catalog.list_tables(ns)` count before submission. |
| "Hosted demo at futureproof.hyenastudios.com" | README hero badge | `curl -sI` returns 200, content-type text/html. | **Live.** |
| "3-minute walkthrough video at youtu.be/8g5cm3v2oTQ" | README hero badge | `curl -sI` returns 303 (YouTube redirect, normal). | **Live.** |
| "Apache 2.0, weights subject to Google Gemma Terms" | README §License | `LICENSE` is Apache 2.0; `LICENSE_SOURCES.md` lists dataset licenses including O*NET CC BY 4.0 and Anthropic Economic Index CC BY 4.0. | **Accurate and properly attributed.** |
| "ollama pull gemma4:e4b … 8 GB RAM minimum" | README §Prerequisites | E4B is 4.5B params; 8 GB is tight with KV cache. Most realistic floor is 10-12 GB. | **Marginally optimistic.** Bump to 12 GB recommended. |
| "Iceberg via DuckDB on the Brightsmith Gold zone gives reproducible scores with full data lineage" | README §"Why this stack" | Reproducibility holds *only* if you can resolve the metadata paths. The hardcoded `/Users/jcernauske/...` in catalog.db and metadata.json files means reproducibility breaks the moment the repo lives at a different absolute path. | **Conditionally accurate.** See P0-#1. |
| "Three-tier fallback: native tool calling → content-JSON extraction → re-prompt" | README §Roadmap line 493 | `gemma_client._fallback_prompt_for_json` and `_try_parse_json_from_content` both exist and are wired in. | **Accurate.** |
| "215 labeled cases produce three real findings" — including "the production prompt explicitly asks for school-attributed rationales; Gemma follows that 5% of the time" | README §Evaluation | I didn't audit the eval harness against the prompt this pass, but the finding is reported with internal consistency (5% specific in title + 5% in rationale = 42% total school-named, matching the table line 444). | **Plausible, self-consistent.** Defer to `eval-v3-2026-05-13.md`. |
| "Spanish and Arabic top-three home languages" | README §Multilingual + Kaggle line 37 | Frontend has `i18n/` directory with localization assets. Backend `gemma_language_instruction(locale)` is wired through every Gemma call site I checked. | **Implemented as described.** |

---

## Bottom line

The submission is real. The deterministic-vs-Gemma architecture is the kind of thing this hackathon is asking for, and the eval is the kind of self-critical engineering judges remember. The two issues that matter — path-baked Iceberg metadata blocking local reproducibility and unauthenticated `/builds` + enumerable build_ids leaking cross-tenant data — are both fixable in a focused half-day. Everything else on P1/P2 is polish.

The CEO said use AI. AI did 80% of this. The other 20% — the paths the README promised but the catalog.db doesn't support, the privacy claim the routers don't enforce — is the part that needs human eyes before submission. That's what I'm here for. Ship it after the P0 list.
