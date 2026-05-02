# FutureProof Staff Engineering Audit — 2026-05-01 Follow-up

*Reviewer: Staff Engineer (15 YOE, production incident survivor)*
*Date: 2026-05-01 (same-day follow-up to `staff-engineer-audit-2026-05-01.md`)*
*Branch: `career-path-enhancements`*
*Scope: verify that S2/S3 fixes landed correctly, that test coverage isn't theater, and that what a Google reviewer sees in the first 30 seconds matches the work claimed.*

> **What this audit is and isn't.** The prior audit (`reports/staff-engineer-audit-2026-05-01.md`) flagged S1 (nothing committed), S2 (sync DuckDB inside async chat path), and S3 (unbounded `target_id` flowing to a parameterized DuckDB lookup). The user has confirmed S1 was resolved by landing the four commits below and explicitly asked me to drop S1. This pass focuses on whether S2 and S3 are *actually* fixed — not just compile-clean — and whether the new `/future` surface and the EADA + IPEDS Finance pipelines hold up under a reviewer's snap judgment.

---

## Executive Summary

**The audit-driven hardening shipped, and shipped well.** S2 and S3 are correctly fixed at the right layers, the test surface added for them would absolutely catch a regression (no theater), and the four expected commits — `b2f5ea0`, `0269d43`, `52af9ea`, `eac01d8` — are all present on the branch with substantive contents. The three specs (`tech-debt-hackathon-hardening.md`, `-followup.md`, `refactor-remove-dead-frontend-code.md`) have moved to `docs/specs/completed/` with `Status: COMPLETE` markers.

**Test runs from this audit:**
- `backend/`: **1,278 passed in 4.96s** (full backend suite)
- Pipeline (`uv run pytest`): **1,795 passed, 1 deselected in 56.89s**
- Frontend (`npx vitest run`): **746/746 passed**
- TypeScript (`npx tsc --noEmit`): **clean**

That's 3,819 tests green across three runtimes on the day of submission. A Google reviewer will see this and move on.

**One real new finding (P1):** the `_SOC_PATTERN` regex in `backend/app/models/api.py` uses `re.compile(r"^\d{2}-\d{4}$").match(...)` instead of `fullmatch` (or `\Z`-anchoring). Python's `$` matches before a single trailing `\n`, so `target_id="11-3021\n"` passes validation. Probably benign in practice — DuckDB with a parameterized query just won't match anything — but it's a correctness gap in a security-critical validator and the test surface didn't catch it. Two-character fix.

**Two coverage gaps worth flagging (P2):** (a) the IPEDS Finance ingestor (1,117 lines), `silver/ipeds_finance_base.py`, `silver/eada_base.py`, and `gold/ipeds_finance_profile.py` ship with **zero direct test coverage** — `test_eada_ingestor.py` is the only test for the entire commit. (b) Neither of the two new pipelines is wired into the MCP server, the build flow, or the chat path; they're orphan datasets. Not a bug, but a reviewer who reads the commit message ("feeds the Gold zone") will wonder why nothing reads from it. The submission narrative should be honest about what's plumbed-through vs. ingested-but-not-yet-consumed.

**Carryovers from prior audit (verified, unchanged):** M1 (LRU on `get_occupation_data` in chat path) — open and *more* relevant now that `/future` makes Case 3 the primary path. M2 (useEffect deps on `build` object) — the new `FutureScreen.tsx` repeats the same pattern at line 232 (`}, [build, retryCount]`). M3 (`_render_locks` and `_builds` unbounded) — unchanged. M4 (`ask_gemma.py` is 1,396 lines) — unchanged. None are blockers.

**Verdict: A− in code substance, A− in packaging.** The hardening cycle landed cleanly; the spec discipline visible in `git log` will read well to Google. Ship it.

---

## What I Verified

### S2 — sync DuckDB call inside async `chat_ask` (claimed FIXED)

**Verified: actually fixed.**

- `backend/app/services/ask_gemma.py:933` — `async def _context_for_branch(build: Build, target_id: str) -> str:` is correctly `async`.
- `backend/app/services/ask_gemma.py:240` — call site is `context_block = await _context_for_branch(builds[0], scope.target_id)`.
- `backend/app/services/ask_gemma.py:1175` — Case 3 lookup is `occ_result = await mcp_client.call_async("get_occupation_data", {"soc_code": target_id})`.
- `backend/app/services/mcp_client.py:192-194` — `call_async` is `return await asyncio.to_thread(call, tool, args)`. This is the right primitive — DuckDB runs in the default thread executor, the event loop is unblocked.
- `backend/app/services/ask_gemma.py:338` — `_dispatch` (the tool-loop adapter) is also `async` and `await`s `call_async`. Consistent with the broader path.

**Other potential sync-DuckDB sneaks:** I grepped `mcp_client.call(` across `ask_gemma.py` and `ask_gemma_router.py`; only the two `call_async` sites came back. No direct `duckdb.connect` or `con.execute` in either file. No regression surface I can find.

### S3 — unbounded `target_id` flowing to DuckDB (claimed FIXED)

**Verified: fixed at the right layer, with one regex correctness gap (see P1 below).**

- `backend/app/models/api.py:106` — `_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")` is at module scope, compiled once.
- `backend/app/models/api.py:158-162` — branch-scope branch in the `model_validator` rejects non-matching `target_id` with `ValueError`. Pydantic v2 turns model-validator `ValueError`s into 422s.
- `backend/app/models/api.py:163-169` — `kind="skill"` enforces `len(target_id) <= 64`.
- `backend/app/routers/ask_gemma_router.py:29` — handler signature is `async def chat_ask(request: AskRequest) -> AskResponse:`. FastAPI parses `AskRequest` (which contains `AskScope`) before invoking the handler, so a malformed `target_id` returns 422 before any service code runs. **Bypass surface: none.**

**Tests** (`backend/tests/routers/test_ask_gemma_router.py:589-676`): seven parametrized cases, including:
- `branch_target_freeform_string` — `"definitely not a soc"`
- `branch_target_no_hyphen` — `"113021"`
- `branch_target_short_prefix` — `"1-3021"`
- `branch_target_injection_shape` — `"11-3021; DROP TABLE careers;"`

Each asserts status code 422 and a substring in the response body. If the validator regressed (regex stripped, branch case removed, etc.), every one of these would flip from 422 to 200 or 404 and the test would fail. Not theater.

### Test surface for `_context_for_branch` async conversion (claimed added)

**Verified: real.** `backend/tests/services/test_ask_gemma.py` has six branch tests, all converted to `@pytest.mark.asyncio` + `async def`. The off-build target test at line 805 mocks `ask_gemma.mcp_client.call_async` (an `async def fake_mcp_call_async`) — not `call`. If someone reverted `_context_for_branch` to call sync `mcp_client.call`, this test would hang or time out because the mock wouldn't be installed on the right symbol. Real coverage.

The `_assert_no_forbidden_outside_helpers` checks at the end of each branch test are also real assertions — they parse the rendered context block and verify no boss-fight or pentagon-stat leak terms appear outside `[helper: …]` brackets. That's a content-safety contract the test pins.

### Specs moved to `docs/specs/completed/` (claimed)

**Verified.**
- `docs/specs/completed/tech-debt-hackathon-hardening.md` — `## Status: COMPLETE` at line 51.
- `docs/specs/completed/tech-debt-hackathon-hardening-followup.md` — present.
- `docs/specs/completed/refactor-remove-dead-frontend-code.md` — `## Status: COMPLETE` at line 46.

None remain under the active `docs/specs/` directory.

### Four commits landed (claimed)

**Verified.** `git log --oneline -5`:
```
eac01d8 docs(reports): add staff engineer audit 2026-05-01 + close out 2026-04-30
52af9ea feat(pipeline): add EADA + IPEDS Finance ingestors
0269d43 feat: add /future screen with education filters + branch chat scope
b2f5ea0 chore: land hackathon hardening + cleanup follow-up
925f887 feat: career-path enhancements + leaderboard rank estimator + i18n parity
```

`b2f5ea0` carries the lifespan migration, env-driven CORS, intent.py hardening, ErrorBoundary, buildStore persist removal, spec moves, and reports. `0269d43` carries `/future` (the 672-line `FutureScreen.tsx`, `BranchTreeFlow.tsx`, `FutureChatSheet.tsx`, `SelectedNodeCard.tsx`, `EducationFilterRow.tsx`, `treeFlowLayout.ts`, `educationFilter.ts`, `flow/Flow*Node.tsx`, the dark React Flow CSS) **and** the S2/S3 backend fixes folded in — `model_validator` SOC regex, `_context_for_branch` made async, the new tests. Diff is `+2,936 / −28` across 23 files. `52af9ea` carries the EADA (`raw + silver`) and IPEDS Finance (`raw + silver + gold`) ingestors plus the governance bundle (40+ files). `eac01d8` carries the audit reports.

The commit *contents* match the commit *messages*. No ghost commits. No "lazy fix" patterns where the message claims more than the diff delivers.

---

## Findings

### 🟠 P1 — Finding 1: SOC regex anchoring lets a trailing newline through

**Impact:** Defense-in-depth gap in the validator that closed S3. A `target_id` of `"11-3021\n"` (or any other valid SOC followed by a single `\n`) passes Pydantic validation and reaches the DuckDB lookup. In practice, DuckDB with a parameterized query won't find a match — it's not exploitable today. But the validator's contract is "only literal SOC strings" and the regex doesn't enforce that. If a future change ever interpolates the value into log output, a CSV column header, or a downstream string, the trailing newline carries through.

**Location:** `backend/app/models/api.py:106` and `:158-162`.

```python
_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")
...
if self.kind == "branch":
    if not _SOC_PATTERN.match(self.target_id or ""):
        raise ValueError(
            "branch target_id must match SOC pattern \\d{2}-\\d{4}"
        )
```

**The Problem:** Python's `re` engine: `^pat$` with `re.match` matches a string with a single trailing `\n` because `$` matches at the position before a final newline. Demonstrated:
```
>>> import re
>>> re.compile(r"^\d{2}-\d{4}$").match("11-3021\n")
<re.Match object; span=(0, 7), match='11-3021'>
```

The seven router tests don't include a `\n` case — `"definitely not a soc"`, `"113021"`, `"1-3021"`, and `"11-3021; DROP TABLE careers;"` all fail for unrelated reasons.

**The Fix (one of two):**
```python
# Option A — use fullmatch instead of match
if not _SOC_PATTERN.fullmatch(self.target_id or ""):

# Option B — anchor with \A and \Z so newlines are rejected
_SOC_PATTERN = re.compile(r"\A\d{2}-\d{4}\Z")
```
Either is fine. Option A is the idiomatic Python answer and reads clearer at the call site. Add one parametrize case to `test_branch_scope_validation`: `target_id="11-3021\n"` expects 422.

**Severity rationale:** 🟠 not 🔴 because the parameterized DuckDB lookup makes the immediate downstream call benign. It's a correctness gap in a validator we explicitly added for a security purpose, and it's exactly the kind of detail a Google reviewer who happens to be a Python person will spot. Two-character fix.

### 🟡 P2 — Finding 2: IPEDS Finance commit ships without test coverage

**Impact:** The `52af9ea feat(pipeline): add EADA + IPEDS Finance ingestors` commit adds 1,117 lines in `src/raw/ipeds_finance_ingestor.py`, plus `src/silver/ipeds_finance_base.py` (14 KB), `src/silver/eada_base.py` (the EADA silver layer), and `src/gold/ipeds_finance_profile.py` (13 KB). The only test in the commit is `tests/raw/test_eada_ingestor.py` (753 lines, tests the EADA *raw* ingestor only). A grep of `tests/` for `ipeds_finance` returned nothing. A grep for `eada` returned only the raw test.

**Location:** Files added without companion tests:
- `src/raw/ipeds_finance_ingestor.py` (1,117 lines)
- `src/silver/ipeds_finance_base.py` (~390 lines)
- `src/silver/eada_base.py` (silver layer)
- `src/gold/ipeds_finance_profile.py` (~360 lines)

**The Problem:** A reviewer who reads the commit message — "631-line ingestor with EDA-pinned constants … 753-line test surface" for EADA — will assume similar discipline applied to IPEDS Finance. It didn't. The 1,117-line ingestor has the most complex logic in the commit (cache-zip → cache-CSV → bulk-URL fallback chain, the `_rv` revised-data convention, the "HTML error page with zip content-type" defensive path) and zero unit tests. Pipeline-level governance artifacts (DQ rules, scorecards, lineage) are present, but those don't exercise the parser code paths.

**The Fix:**
- Add `tests/raw/test_ipeds_finance_ingestor.py` that at minimum covers the `_rv` priority logic, the HTML-zip-content-type defensive branch, and the legitimate-zero preservation case.
- Add `tests/silver/test_ipeds_finance_base.py` and `tests/silver/test_eada_base.py` (even smoke-level fixture round-trips).
- Add `tests/gold/test_ipeds_finance_profile.py` that asserts the gold model's parquet output schema.

**Severity rationale:** 🟡 not 🟠 because pipeline governance artifacts and DQ rules cover *runtime* correctness on real data, which is itself a real signal. But "1,117 lines added, 0 unit tests added" is a story a reviewer can tell, and it doesn't match the commit-message framing.

### 🟡 P2 — Finding 3: New EADA + IPEDS Finance pipelines are orphan datasets

**Impact:** Neither pipeline is wired into the MCP server, the build flow, the chat path, or any consumer. Greps of `src/mcp_server/`, `backend/app/`, and `src/gold/` for the actual table/module names came back empty (after filtering "readable" false positives). A reviewer who sees "feeds the Gold zone" in the commit message and pulls the thread will find that nothing on the consumer side reads from it.

**Location:** Search target — `consumable.eada_*` and `consumable.ipeds_finance_*` references in `src/mcp_server/futureproof_server.py` and `backend/app/services/builds.py`. No hits.

**The Problem:** Either the submission narrative should say "EADA + IPEDS Finance ingest is plumbed into the bronze-silver-gold layers as a separate workstream and will be wired in post-hackathon" — which is honest and fine — or one of the existing MCP tools (`get_school_programs`, say) should pull from one of the new gold tables before submission. Right now the commit message implies a connection that the code doesn't make. That's the kind of thing that reads as theater on close reading even when it isn't.

**The Fix:** Pick one. If shipping as-is, add a one-line note to the submission narrative or the README's data sources table acknowledging that EADA + IPEDS Finance are ingested but not yet consumed. If wiring in, it's a small change to `futureproof_server.py` to add a `get_institution_finance_summary(unitid)` tool and add it to the `get_school_programs` join.

**Severity rationale:** 🟡 — packaging/narrative concern, not a code concern. The pipeline code itself is good.

### 🟡 P2 — Finding 4: M1 (chat-path LRU) is now more relevant, not less

**Impact:** Each `/future` L2 click that's not on `build.branches` triggers a fresh `get_occupation_data` DuckDB lookup inside `_context_for_branch` Case 3 (`ask_gemma.py:1175`). Before `/future` shipped, this path was theoretical (Case 3 only fired on hand-crafted off-tree SOC inputs). Now `/future` materializes Case 3 as the primary user path — every L2 endpoint click hits it.

**Location:** `backend/app/services/ask_gemma.py:1173-1187`.

**The Problem:** No cache, no in-flight de-dupe. A student who clicks back and forth between two L2 endpoints will hit DuckDB twice for the same SOC. The lookup is fast (sub-100ms on a hot connection), but it's the same query being re-run.

**The Fix:** Wrap `mcp_client.call_async` for `get_occupation_data` in a small `cachetools.TTLCache` (1 minute, 256 entries) keyed on `soc_code`. Or call `functools.lru_cache(maxsize=128)` on a sync wrapper, then `await asyncio.to_thread(...)` on it. Either is ~10 lines.

**Severity rationale:** 🟡 — perf hygiene, not correctness. Carry-over from prior audit; status changed from "theoretical" to "actually in the hot path" because of `/future`.

### 🟡 P2 — Finding 5: M2 (useEffect deps on `build` object) reproduced in `FutureScreen.tsx`

**Impact:** `FutureScreen.tsx:232` — `}, [build, retryCount]);` — depends on the entire `build` object reference, not `build.build_id`. If anything in the buildStore re-creates the `build` object (rebuild, refetch, JSON-parse round-trip), the tree fetch effect re-fires and the screen re-loads even though the build_id is unchanged.

**Location:** `frontend/src/screens/FutureScreen.tsx:206-232`.

**The Problem:** Same pattern as the prior audit's M2. A reviewer who reads `FutureScreen.tsx` cold will spot it because the `getTree(build!.build_id, 2)` call inside the effect makes the right dependency obvious — it's `build.build_id`, not `build`.

**The Fix:**
```tsx
const buildId = build?.build_id;
useEffect(() => {
  if (!buildId) return;
  // ...
  getTree(buildId, 2);
  // ...
}, [buildId, retryCount]);
```

**Severity rationale:** 🟡 — same severity as the prior M2.

---

## Carryovers from Prior Audit (Verified Unchanged)

| ID | Item | Status |
|---|---|---|
| **M1** | LRU on `get_occupation_data` in chat path | Open. **Now P2 in this audit (Finding 4)** because `/future` makes Case 3 hot. |
| **M2** | `useEffect` deps on `build` object | Open. **Reproduced in `FutureScreen.tsx` (Finding 5).** |
| **M3** | `_render_locks` (`backend/app/routers/wrapped.py:39`) and `_builds` (`backend/app/state.py:16`) — module-level unbounded dicts | Unchanged. Pre-existing. Not a hackathon-demo blocker; a real concern for a multi-tenant deploy. |
| **M4** | `ask_gemma.py` is 1,396 lines | Unchanged. Same line count as prior audit. Not blocking; readability tax. |

---

## What's Actually Good (Acknowledging Solid Work)

- **The S2 fix uses `asyncio.to_thread`, not `loop.run_in_executor` with custom executors or a shotgun-marriage of sync and async clients.** That's the simplest correct primitive for a sync-DB-call-from-async-handler shape. It's also what I'd write.
- **The S3 fix is at the model boundary, not buried in the service.** That's the right layer — Pydantic 422s before any handler code runs, no bypass surface, no conditional validation. Validators on `model_validator(mode="after")` are exactly where this kind of cross-field check belongs.
- **The seven SOC-validation router tests include an injection-shape case** (`"11-3021; DROP TABLE careers;"`). I appreciate that someone wrote a test that explicitly says "if a SQL-shaped string makes it through, this test fails." That signals defense-in-depth thinking.
- **The `/future` screen is a real piece of work.** 672 lines, 583-line companion test file, debounced selection, flash-highlight driver, education filter that preserves the root, empty-state overlay with a one-tap clear, `visualViewport`-aware mobile bottom-sheet, React Flow with a Brightpath dark theme. The `pointer-events-none` on the empty-state overlay so React Flow's pan/zoom still works underneath is the kind of detail you only get right by actually using the screen.
- **The lifespan migration is right.** `b2f5ea0` migrates `@app.on_event("startup")` to `@asynccontextmanager`-style lifespan handlers. That silences a Pydantic-v2-era DeprecationWarning and lines the app up with FastAPI's recommended pattern. Small change, correct change.
- **Env-driven CORS allowlist in `b2f5ea0`** (`FUTUREPROOF_CORS_ORIGINS`) is the correct posture for a demo that may be deployed to multiple environments. The README adds a Security & Deployment section that documents the unauthenticated demo posture explicitly. That kind of "we know what we shipped and we're not pretending otherwise" framing reads well to reviewers.
- **`intent.py` defense-in-depth on `get_school_cips` / `get_crosswalk`** with `^\d{2}$` family-prefix validation, `KeyboardInterrupt` propagation through the `except Exception` guard, and warning logs on swallow paths — that's mature error-handling discipline.
- **The EADA ingestor's ellipsis-sentinel pattern** on the filter-column / filter-value parameters (default vs. explicitly disabled vs. explicitly overridden) is the right call. Most ingestors collapse those three states into two and create a footgun. Don't see that often.
- **Test counts: 3,819 green tests** across backend (1,278), pipeline (1,795), and frontend (746). On the day of submission. With zero TypeScript errors. That's a good number for a Google reviewer to see.

---

## What a Google Reviewer Sees in 30 Seconds

1. `git log --oneline -5` shows four feat/chore/docs commits on submission day, top one is `eac01d8 docs(reports): add staff engineer audit 2026-05-01 + close out 2026-04-30`. **Reads as: "this team audits itself and acts on the audit."** Strong opening.
2. `cd backend && pytest -q` — 1,278 passed in 5 seconds. **Reads as: "fast, comprehensive test suite, no flakes."** Strong.
3. `npx vitest run` — 746/746 in 16 seconds. `npx tsc --noEmit` clean. **Reads as: "frontend is in shape too."**
4. `uv run pytest -q` — 1,795/1,795 in 57 seconds. **Reads as: "the pipeline is real, not aspirational."**
5. Open `backend/app/models/api.py`, find `_SOC_PATTERN`, see the SOC regex. Open `backend/app/services/ask_gemma.py`, find `_context_for_branch`, see the `async`/`await call_async` chain. **Reads as: "they thought about input validation and event-loop blocking."**
6. Open `docs/specs/completed/tech-debt-hackathon-hardening.md` — `Status: COMPLETE`. **Reads as: "spec-driven workflow with closed-loop status tracking."**

The one thing that bites them in detailed code reading is the regex anchoring (P1 above). Five-minute fix, ten-minute fix with the new test case. Worth doing before submission.

---

## Recommendations (Prioritized)

1. **🟠 Fix P1 SOC regex anchoring** — change `match` to `fullmatch` in `backend/app/models/api.py:159`, add a `\n`-trailing test case to `test_branch_scope_validation`. ~5 minutes including the test. Eliminates the only real correctness gap in the new code.
2. **🟡 Decide on EADA + IPEDS Finance narrative (P2 Finding 3)** — either add a one-liner to README/submission narrative acknowledging "ingested but not yet consumed," or wire one of the gold tables into an existing MCP tool. Either is fine; ambiguity isn't.
3. **🟡 Add minimal IPEDS Finance test coverage (P2 Finding 2)** — at least one test file for the 1,117-line ingestor's `_rv` priority logic and HTML-zip-content-type fallback. The coverage gap is the kind of thing a thorough reviewer pulls on; pre-empting it costs 30 minutes.
4. **🟡 P2 Finding 5 (M2 in `FutureScreen.tsx`)** — change `[build, retryCount]` to `[build?.build_id, retryCount]`. One-line fix, no behavior change, removes a re-fetch foot-gun.
5. Defer M1 (chat-path LRU), M3 (module-level dicts), M4 (`ask_gemma.py` size). All known, all post-hackathon work.

---

## Questions for the Author

1. Is there a planned post-hackathon spec for wiring EADA + IPEDS Finance into the consumer surface? If so, mentioning it in the README's "Future Work" section pre-empts the reviewer question.
2. Was there a reason `_context_for_branch` Case 3's `get_occupation_data` call doesn't memoize? The same SOC will get re-queried on every back-and-forth click on `/future`.
3. Was the IPEDS Finance ingestor's lack of a unit-test file an oversight, or is the dq-rules + governance scorecard treated as the test surface for that one? (Asking because it's a different discipline from the EADA ingestor in the same commit.)
4. Has `/future` been load-tested with a tree of 12+ L1 branches × 4+ L2 endpoints each? The `treeFlowLayout.ts` comment mentions a "12-branch column at ~0.7 zoom" tuning but I don't see a test fixture at that size.

---

## Bottom Line

**S2 and S3 fixes landed correctly and the test surface protects them.** The four expected commits are all present with substantive contents matching their messages. Specs have moved to `completed/`. The full test suite (3,819 tests) is green across all three runtimes.

The regex-anchoring gap is real but small — a 30-minute fix-and-test cycle eliminates it before submission.

**Ship it.** With the P1 fix, this is the strongest the codebase has read since I started auditing it.

— Staff Engineer (still skeptical, slightly less so this week)
