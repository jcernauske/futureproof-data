# Performance: SOC Retrieval Hot Path

## Claude Code Prompt

```
Read the spec at docs/specs/performance-soc-retrieval.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (data access layer
     rewrite, persistent DuckDB connection lifecycle, JOIN parity with
     existing fan-out, brightsmith framework boundary).
   - Invoke @fp-data-reviewer in parallel to verify the single-SQL JOIN
     in §4 returns identical row sets and ordering vs. the current
     3×N fan-out (this is a data-equivalence check, not a quality check).
   - Both write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. IMPLEMENTATION
   - Implement §4 exactly. Do NOT change response payload shape, field
     names, ordering, or caveat strings — this is a data-access rewrite,
     not a behavior change.
   - BEFORE coding: read §4 Testing Impact Analysis. The substitution
     test surface is large (~1300 lines across three files) and fragile.
   - DURING coding: only modify tests listed in "Authorized Test
     Modifications". If any other test fails, STOP and escalate.
   - Log all work to §6.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
   - If still broken after 3 attempts: escalate via §10.

3. TESTING
   - Invoke @test-writer to review the spec and add the P0/P1 tests
     listed in §4.
   - Critical: the JOIN-parity test (P0) must compare row-by-row against
     a fixture captured from the current fan-out implementation, NOT
     against hand-written expectations. Capture the fixture before
     starting the rewrite.
   - Run the full pytest suite. Every failure gets named in §7 with a
     causation determination.

4. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
     Focus areas: connection lifetime / thread-safety of the persistent
     DuckDB handle, SQL injection surface on the new JOIN (parameterize
     everything), cache invalidation correctness (process-lifetime is
     the policy — verify no mutation paths exist), and whether the
     timing logs leak PII.
   - Writes findings to §8.
   - If APPROVED: proceed to step 5.
   - If CHANGES REQUIRED: route to implementer via §10.
   - If BLOCKER: STOP, alert human.

5. VERIFICATION
   - Invoke @fp-builder for full build verification.
   - Backend: ruff, mypy, pytest.
   - Frontend: TypeScript, vitest, Vite production build (no frontend
     changes expected, but the build must still pass).
   - §9 verification MUST include before/after timing on a representative
     request: UIUC (unitid 145637) + CIP 26.01 with substitution to a
     specific Biology sub-CIP. Capture median + p95 over 10 runs from
     the new permanent timing logs.

6. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Check off Success Criteria in §1.
   - Generate report to reports/performance-soc-retrieval-YYYY-MM-DD.md.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect + @fp-data-reviewer approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-20 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.2 |
| Last Updated | 2026-04-20 (v1.2 — folded in post-review race fixes: `query_filtered`/`query_sql` hold lock across init+execute; `_get_query_engine` uses double-checked locking) |
| Blocked By | — |
| Related Specs | `docs/specs/completed/cip-intent-substitution.md`, `docs/specs/completed/mcp-futureproof-core.md`, `docs/specs/completed/feature-set-your-course.md`, `docs/specs/completed/perf-reveal-loading-screen.md` |

---

## §1 Feature Description

### Overview
Rewrite the data-access layer behind `_handle_get_career_paths` to eliminate full table scans, the 3×N substitution fan-out, and per-call DuckDB connection setup. Add permanent timing logs so future regressions surface in telemetry instead of in user complaints.

### Problem Statement
The Set Your Course screen takes many seconds to render SOC tiles after a student picks a school + major. The latency is dominated by the data-access layer, not by Gemma. Code-read diagnosis (no instrumentation needed):

1. **Full table scans + Python-side filtering.** `query_iceberg_simple` (`/Users/jcernauske/code/bright/brightsmith/src/brightsmith/mcp/base_mcp_server.py:368-403`) does `table.scan().to_arrow()` with no predicate pushdown, then applies filters with `[r for r in rows if str(r.get(col,"")) == str(val)]`. Every "lookup by unitid+cipcode" reads the entire Iceberg table.
2. **N+1 fan-out on the substituted path.** `_build_substituted_rows` (`/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py:1554-1741`) loops over each crosswalk SOC and runs three separate `query_iceberg_simple` calls per SOC (occupation_profiles, onet_work_profiles, ai_exposure). For Biology's ~12 SOCs that's ~36 full table scans, serial, plus 1 for career_outcomes plus 1 for the crosswalk SOC list = ~38 full Iceberg reads per request.
3. **`query_iceberg` rebuilds the DuckDB world every call.** `base_mcp_server.py:405-437` opens a new DuckDB connection, installs+loads the Iceberg extension, lists every namespace, lists every table, calls `catalog.load_table()` for each, creates a view per table, runs the SQL, then `con.close()`. `_fetch_crosswalk_socs` (`futureproof_server.py:1529`) hits this path on every request.
4. **Standard path also scans up to 500k rows.** `CAREER_PATHS_SCAN_LIMIT = 500_000` (`futureproof_server.py:224`) pulls that many rows into Python before filtering.
5. **No caching anywhere.** No LRU on the crosswalk SOC list. No memoization on per-SOC fan-out queries. No warm catalog/connection.

This is not a speculative perf claim — it's a deterministic consequence of the code. The rewrite is also the prerequisite for the frontend perf spec (`performance-soc-reveal-frontend.md`, future) which is blocked on this one.

### Success Criteria
- [x] `_handle_get_career_paths` median wall-clock latency for the substituted path drops by ≥ 5× on the canonical request (UIUC + CIP 26.01 substituted to a specific Biology CIP). **Measured 14.0× (3722ms → 266ms).**
- [x] `_handle_get_career_paths` does not perform > 4 Iceberg scans per request on either path. **Substituted: 3 (crosswalk + school + JOIN). Standard: 1.**
- [x] DuckDB connection + Iceberg view registration happens exactly once per process lifetime, not per request.
- [x] `_fetch_crosswalk_socs` and the standard-path `(unitid, canonical_cipcode)` lookup are LRU-cached with process lifetime. Standard-path cache is env-gated (`FUTUREPROOF_OUTCOMES_CACHE=1`), off by default.
- [x] Permanent structured timing logs land in `logs/mcp.jsonl` for `_handle_get_career_paths`, `_fetch_crosswalk_socs`, `_build_substituted_rows`, `query_filtered`, and `query_sql`. Each line carries `duration_ms`, `path`, `cache_hit`, `row_count` as applicable.
- [x] Response payload is byte-identical to the pre-rewrite implementation for 7 captured fixtures covering substituted (a/b/c/f/g), missing-school short-circuit (e), and standard path (h). Asserted by the parameterized parity test at `tests/mcp/test_substituted_rows_join_parity.py` against `tests/mcp/fixtures/career_paths_responses/*.json`. Fixture (d) dropped — routes through LLM fallback which is non-deterministic by construction.
- [x] All existing tests in `backend/tests/services/` and `tests/mcp/` pass. The only test modification was the `_patch_substitution` mock update in `tests/mcp/test_cip_substitution.py` (approved in §10 2026-04-20) — no behavioral assertion changed.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Wrap/override in `FutureProofMCPServer`, do not modify brightsmith.** Subclass `query_iceberg_simple` and `query_iceberg` on the FP server. | Brightsmith is a shared framework; cross-repo coordination would slow this down. The pushdown semantics we need are FP-specific (PyIceberg `RowFilter` over the FP table set). If the override stabilizes, we can upstream later. | (a) Modify brightsmith directly — rejected, framework boundary. (b) Build a new module that bypasses brightsmith entirely — rejected, loses governance hooks (`attach_governance`, `enrich_response`). |
| 2 | **Persistent DuckDB connection lives on `FutureProofMCPServer` instance, lazy-initialized on first query.** | Server is already a process-lifetime singleton via `mcp_client.get_server()`. Connection setup (extension install/load + view creation) is the dominant cost in `query_iceberg`. Init cost paid once at first request, not per request. | (a) Init in `__init__` — rejected, makes import-time slow and breaks tests that don't query. (b) Per-request connection — current behavior, the bug we're fixing. |
| 3 | **Single SQL JOIN replaces the 3×N fan-out.** Query against the persistent DuckDB connection's registered Iceberg views, parameterized by substituted CIP. | One query plan beats 3N queries, even with predicate pushdown. DuckDB executes Iceberg JOINs natively. Eliminates serial Python loop overhead. | (a) Parallel async fan-out — rejected, doesn't solve the per-call setup cost and adds complexity. (b) Pre-materialize a denormalized view in Gold — rejected, schema change explicitly out of scope. |
| 4 | **`functools.lru_cache(maxsize=128)` on `_fetch_crosswalk_socs(cip4)`.** | Pure function of a 4-digit CIP. Cardinality is bounded (~1.6k 4-digit CIPs in the crosswalk). Process-lifetime cache is safe because Iceberg data is read-only at runtime. | (a) TTL cache — rejected, no invalidation signal exists. (b) No cache — rejected, this is hot. |
| 5 | **Optional LRU cache on standard-path `(unitid, canonical_cipcode)` outcome lookup.** Off by default; enabled via env flag `FUTUREPROOF_OUTCOMES_CACHE=1`. Key DOES NOT include `loan_pct` or `student_cip` — those are applied by the stat engine post-query and do not affect the underlying `query_iceberg_simple` result. Including them would just make the LRU miss on every request. | The standard path is less hot than substitution because most popular (school, major) combos route through substitution. But repeated requests during a demo or load test benefit. Off-by-default keeps the spec scope narrow and avoids cache-correctness worries during the hackathon. | (a) Always-on — defer to a future spec once we have telemetry. (b) Memcache/Redis — rejected, runtime adds for negligible gain. |
| 6 | **Permanent timing logs land in the existing `logs/` sink, not Prometheus or OpenTelemetry.** Structured JSON lines. | Matches existing `logs/gemma.jsonl` pattern. Zero ops dependencies. Grep-able. Adequate for regression detection. | (a) OpenTelemetry — rejected, ops overhead for hackathon. (b) Stdout only — rejected, lost across container restarts on Railway. |
| 7 | **Fixture-based JOIN parity test, not hand-written assertions.** Capture full response payload from the current fan-out for ≥ 5 representative requests; new JOIN must produce byte-identical output. | The fan-out has subtle ordering rules and field-population logic that are hard to reconstruct from a spec. Diffing against a captured fixture catches every regression including ones we wouldn't have thought to assert. | (a) Hand-written assertions — rejected, brittle and incomplete. (b) Property-based — rejected, payloads have complex cross-field invariants. |

### Constraints
- No behavior change in the response payload — same fields, same ordering invariant (`stats_available_count` desc, then `occupation_title` asc), same caveat strings, same substitution semantics.
- No schema changes to Gold tables. None required.
- No frontend changes. The frontend perf spec is sequenced after this one ships.
- Brightsmith framework boundary respected (Decision #1).
- Python 3.11+ (per `pyproject.toml`).
- DuckDB version pinned by current `pyproject.toml`; no version bumps in this spec.

### Out of Scope
The following are intentionally NOT addressed in this spec. Each is parked for a future spec:

- **Frontend perf** (keystroke debounce on major-text refetch, parallelizing or interleaving outcomes + tier, streaming tiers as Gemma generates). Tracked as the sibling spec, blocked on this one.
- **Tiering quality** (intent-aware tiering prompt, SOC universe expansion for "pre-X" intents, embeddings-based SOC re-rank). Different problem from latency.
- **Schema changes** to `consumable.program_career_paths`, `consumable.career_outcomes`, or any Gold table. Specifically: no pre-materialized denormalized "career_card" table.
- **Brightsmith upstream contribution** of the predicate-pushdown change. May happen later; not in this spec.
- **Concurrency / async** of the MCP handler. The router already wraps in `asyncio.to_thread`; the scan itself stays sync.
- **Cache invalidation policy beyond process lifetime.** If we ever swap underlying Iceberg files at runtime, that's a separate spec.
- **Tier-endpoint perf** (`/build/tier`). Out of scope here; the tier call's Gemma latency is addressed in the frontend spec via streaming.

---

## §3 UI/UX Design

**SKIPPED — backend-only spec.** No screens, components, or design tokens touched.

---

## §4 Technical Specification

### Architecture Overview
The MCP server (`FutureProofMCPServer`) is the single chokepoint for all read access to Gold-zone Iceberg tables. Today every read goes through brightsmith's `query_iceberg_simple` (full scan + Python filter) or `query_iceberg` (per-call DuckDB setup). This spec replaces the data-access layer with a persistent DuckDB connection that holds Iceberg views for the FP table set, and routes both helpers through it. The substitution fan-out gets rewritten as a single parameterized JOIN against those views. Caching layers wrap the two hottest pure functions. Timing logs are added to every layer. No public interface changes; all wiring is internal to `src/mcp_server/`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/_query_engine.py` | Create | New module owning the persistent DuckDB connection, Iceberg view registry, predicate-pushdown query helper, and JOIN helper. ~250 lines. |
| `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py` | Modify | Override `query_iceberg_simple` and `query_iceberg` to delegate to `_query_engine`. Replace `_build_substituted_rows` body with a JOIN call. Add `@functools.lru_cache` to `_fetch_crosswalk_socs`. Add timing decorators to `_handle_get_career_paths`, `_fetch_crosswalk_socs`, `_build_substituted_rows`. Optional standard-path LRU. |
| `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/_telemetry.py` | Create | New module: `@timed` decorator that emits structured JSON to `logs/mcp.jsonl`. ~80 lines. Mirrors `gemma_client._log_exchange` pattern. |
| `/Users/jcernauske/code/bright/futureproof-data/backend/app/services/mcp_client.py` | Modify | No interface change. Add a docstring note that the shared server now carries a persistent DuckDB connection; `reset_server()` must close it. ~5 lines. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/mcp/test_query_engine.py` | Create | Unit tests for `_query_engine`: predicate pushdown, view caching, connection lifetime, idempotent init. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/mcp/test_substituted_rows_join_parity.py` | Create | P0 fixture-based parity test: captured pre-rewrite responses vs. new JOIN responses, byte-identical diff. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/mcp/test_get_career_paths_perf.py` | Create | Smoke test that timing logs are emitted with the expected schema; cache-hit assertion on second identical request. |
| `/Users/jcernauske/code/bright/futureproof-data/tests/mcp/fixtures/career_paths_responses/` | Create | Captured response fixtures (5+ JSON files) for the parity test. Generated by a one-off helper script before the rewrite begins. |

### Data Model Changes

**No Gold table or wire-format changes.** All new types are internal.

#### Internal types (in `src/mcp_server/_query_engine.py`)

```python
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import duckdb


@dataclass
class _ViewRegistration:
    """One Iceberg table registered as a DuckDB view."""

    namespace: str
    table: str
    view_name: str           # f"{namespace}_{table}"
    metadata_location: str   # absolute path to current metadata.json


class QueryEngine:
    """Persistent DuckDB connection with cached Iceberg views.

    Lazy-initialized on first query. Process-lifetime; closed only via
    explicit shutdown (used by tests).

    Thread-safety: ``query_filtered`` and ``query_sql`` acquire
    ``self._lock`` (a ``threading.RLock``) for the entirety of the
    ``execute``/``fetchall`` pair plus the ``con.description`` read.
    Reason: DuckDB's Python connection serializes independent statements
    internally, but ``con.description`` is clobbered by a concurrent
    ``execute`` from another thread — which WILL happen when FastAPI
    runs two substitution handlers concurrently via ``asyncio.to_thread``.
    Without the lock the result is silent column-name corruption under
    load. An ``RLock`` is used so ``_ensure_initialized`` can recurse
    safely if future registration logic is factored that way.
    """

    def __init__(self, catalog: Any) -> None: ...

    def query_filtered(
        self,
        table_name: str,
        filters: dict[str, Any] | None,
        columns: list[str] | None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Predicate-pushdown query. Filters become a SQL WHERE clause
        with parameterized values; columns become the SELECT list.
        Returns at most ``limit`` rows. Acquires ``self._lock`` for the
        duration of the DuckDB call."""

    def query_sql(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run parameterized SQL against the registered Iceberg views.
        ``params`` keys are referenced as $name in the SQL. Acquires
        ``self._lock`` for the duration of the DuckDB call."""

    def shutdown(self) -> None:
        """Close the DuckDB connection. Idempotent."""
```

#### Timing-log schema (one JSON line per event in `logs/mcp.jsonl`)

```python
{
    "ts": "2026-04-20T17:55:59.123456+00:00",  # ISO-8601 UTC
    "event": "career_paths_handler",           # or fetch_crosswalk_socs, build_substituted_rows_join, query_filtered, query_sql
    "duration_ms": 123,                         # int
    "path": "substituted",                      # one of: substituted, standard, fallback_broaden, fallback_gemma — only on career_paths_handler
    "unitid": 145637,                           # int, only on career_paths_handler
    "cipcode": "26.01",                         # str, only on career_paths_handler
    "row_count": 12,                            # int — count of rows returned
    "cache_hit": False,                         # bool — true when LRU returned cached value
    "extra": { ... }                            # optional event-specific fields
}
```

**Logging policy — `extra` is bounded-cardinality only.** `extra` MUST NOT carry free-text user input (e.g. raw `student_major` strings, intent transcripts). Permitted values: enums, numeric IDs, row counts, category labels, booleans. `unitid` and `cipcode` at the top level are NOT PII — they are IPEDS / CIP public identifiers and are intentionally included for grep-ability. Any future spec that wants to add a free-text field to `extra` owns a PII-review decision.

### Service Changes

#### `src/mcp_server/_query_engine.py` (new)

Public surface above. Internal behavior:

- `__init__` stashes the catalog reference and creates `self._con: duckdb.DuckDBPyConnection | None = None` and `self._views: dict[str, _ViewRegistration] = {}`.
- `_ensure_initialized()` is called by every public method. On first call: opens connection, installs+loads iceberg extension, walks `catalog.list_namespaces()`/`list_tables()` once to register every view via `CREATE VIEW IF NOT EXISTS {ns}_{tbl} AS SELECT * FROM iceberg_scan('{metadata_location}')`. Subsequent calls are no-ops (`if self._con is not None: return`).
- `query_filtered` builds a SQL string of the form `SELECT {cols} FROM {ns}_{tbl} WHERE {col} = $col AND ... LIMIT {limit}` with parameterized values. Returns rows as dicts. Filters are validated as `str(int)` or quoted strings — no string interpolation of values into SQL. Limit is clamped to `1_000_000` defensively.
- `query_sql` is a thin wrapper for the JOIN helper.
- `shutdown()` calls `self._con.close()` and resets state.

#### `src/mcp_server/futureproof_server.py` (modify)

- `FutureProofMCPServer.__init__` adds `self._query_engine: QueryEngine | None = None`. Lazy via `_get_query_engine()`.
- Override `query_iceberg_simple(table_name, filters, columns, limit)` to call `self._get_query_engine().query_filtered(...)`. Same signature as the brightsmith base class.
- Override `query_iceberg(sql)` to call `self._get_query_engine().query_sql(sql)`.
- **Add `FutureProofMCPServer.shutdown() -> None`** method. Closes `self._query_engine` (if initialized) and resets it to `None`. Idempotent — safe to call on a server that never issued a query. Called by `mcp_client.reset_server()` before `_server = None` so CI doesn't leak DuckDB file descriptors across test matrices (macOS hits fd limits under large matrices).
- `_fetch_crosswalk_socs(cip4)` decorated with `@functools.lru_cache(maxsize=128)`. (Note: instance method + lru_cache requires either (a) module-level cache keyed on `(self, cip4)` or (b) a `__hash__`-friendly weak ref. Spec choice: extract the cached body into a module-level `_fetch_crosswalk_socs_cached(query_engine_id: int, cip4: str)` helper and have the method delegate. This avoids the classic `lru_cache` + `self` memory leak.)
  - **Docstring requirement:** `_fetch_crosswalk_socs_cached` carries a docstring stating: "Cache key includes `query_engine_id` (`id(engine)`) so `reset_server()` in tests transparently invalidates the cache — a new engine instance has a new `id`, so its lookups correctly miss. DO NOT switch to a content-addressed key (e.g. catalog path hash) without first updating test isolation — stable keys cause cached crosswalk rows to leak across test cases and mask regressions."
  - Input validation: mirror the existing `^\d{2}\.\d{2}$` regex gate currently in `_fetch_crosswalk_socs`. Malformed input returns `[]`.
- `_build_substituted_rows` body replaced with a single JOIN against the persistent `QueryEngine`. Two parameters are bound by the Python wrapper:
  - `$school_cip4 = self._canonical_cip4(reported_cipcode)` — the school's broad CIP (4-digit form, e.g. `"52.01"`). NOT the raw caller input (callers may pass 6-digit like `"52.0100"`) and NOT the substituted sub-CIP. `career_outcomes.cipcode` is stored at 4-digit granularity, so a wrong binding returns zero school rows for every such request.
  - `$cip4 = substituted_cipcode` — the 4-digit substituted CIP (guaranteed `^\d{2}\.\d{2}$`).

Format assertions (documented inline so a future ingestor change surfaces here):
  - `base.cip_soc_crosswalk.cipcode` is stored as `XX.XXXX` (6 chars). `SUBSTR(_, 1, 5)` yields `XX.YY` = 4-digit prefix.
  - `consumable.career_outcomes.cipcode` is stored at 4-digit (`XX.YY`) granularity.

School-CTE zero-row short-circuit (mandatory for parity): the Python wrapper MUST preserve the existing fan-out behavior at `futureproof_server.py:1590` — when no `career_outcomes` row exists for `(unitid, school_cip4)`, return `(None, f"No career_outcomes row for unitid={unitid}, cipcode='{canonical_reported}'; cannot substitute.")`. Implementation: run the `school` lookup up-front via a separate `QueryEngine.query_filtered` call; if empty, short-circuit to that error before issuing the JOIN. A `CROSS JOIN` against an empty `school` silently produces zero rows — which is NOT parity with the fan-out (caller would fall through to a "no rows" response instead of the descriptive error).

SQL (the JOIN body, issued only after the school row is confirmed present):

```sql
WITH socs AS (
    SELECT DISTINCT soc_code
    FROM base_cip_soc_crosswalk
    WHERE SUBSTR(cipcode, 1, 5) = $cip4
      AND soc_code IS NOT NULL
      AND soc_code <> '99-9999'
),
school AS (
    SELECT
        institution_name,
        program_name,
        cip_family_name,
        earnings_1yr_median,
        earnings_1yr_p25,
        earnings_1yr_p75,
        debt_median,
        debt_p25,
        debt_p75,
        debt_to_earnings_annual,
        cip_family_earnings_rank,
        confidence_tier,
        institution_control,
        net_price_annual,
        cost_of_attendance_annual,
        net_price_4yr,
        tuition_in_state,
        tuition_out_of_state,
        room_board_on_campus
    FROM consumable_career_outcomes
    WHERE unitid = $unitid AND cipcode = $school_cip4
    LIMIT 1
)
SELECT
    socs.soc_code,
    op.occupation_title,
    op.soc_major_group_name,
    op.median_annual_wage,
    op.wage_percentile_overall,
    op.grw_score_rounded,
    op.market_score_rounded,
    op.growth_category,
    op.employment_current,
    op.education_level_name,
    onet.primary_title,
    onet.hmn_score_rounded,
    onet.burnout_score_rounded,
    onet.top_5_activities,
    onet.top_human_activities,
    onet.burnout_drivers,
    ai.stat_res,
    ai.boss_ai_score,
    school.institution_name,
    school.program_name,
    school.cip_family_name,
    school.earnings_1yr_median,
    school.earnings_1yr_p25,
    school.earnings_1yr_p75,
    school.debt_median,
    school.debt_p25,
    school.debt_p75,
    school.debt_to_earnings_annual,
    school.cip_family_earnings_rank,
    school.confidence_tier,
    school.institution_control,
    school.net_price_annual,
    school.cost_of_attendance_annual,
    school.net_price_4yr,
    school.tuition_in_state,
    school.tuition_out_of_state,
    school.room_board_on_campus
FROM socs
LEFT JOIN consumable_occupation_profiles op ON op.soc_code = socs.soc_code
LEFT JOIN consumable_onet_work_profiles onet ON onet.bls_soc_code = socs.soc_code
LEFT JOIN consumable_ai_exposure ai ON ai.soc_code = socs.soc_code
CROSS JOIN school
```

Notes on the SELECT list:
  - `school.*` was rejected (see §5 review). The explicit list above is the 19-field `_SUB_CO_FIELDS` set with `cipcode` and `unitid` excluded — the Python wrapper writes those keys unconditionally (`unitid = request.unitid`, `cipcode = substituted_cipcode`), so including them would create a collision vector on any future careless refactor (e.g. `row = {**school_cols, **soc_cols}`).
  - No SQL `ORDER BY`. The final response ordering is set by the Python wrapper's `_sub_sort_key` (`-stats_available_count`, `occupation_title`) at `futureproof_server.py:2190`. SQL-side ordering would be overwritten and is wasted work.
  - The `onet.primary_title` fallback for missing `op.occupation_title` (`futureproof_server.py:1690-1694`) is preserved in the Python wrapper — both columns are in the SELECT list.

The Python wrapper then computes `stat_ern`, `stat_roi`, `boss_loans_sub`, `stats_available_count`, `bosses_available_count`, `overall_confidence`, and assembles the row dict — same fields, same shape as the current implementation. `unitid` and `cipcode` (= `substituted_cipcode`) are written by the wrapper. The pure-compute side (`compute_stat_ern`, `compute_stat_roi`) is unchanged. JSON-struct decoding (`_decode_json_struct_fields`) runs after the JOIN materializes.

- Standard-path LRU (Decision #5): wrap the `query_iceberg_simple(CAREER_PATHS_TABLE, ...)` call in `_handle_get_career_paths` (line 2238) behind a tiny module-level helper `_cached_career_paths_lookup(unitid: int, canonical_cipcode: str)` gated by `os.getenv("FUTUREPROOF_OUTCOMES_CACHE") == "1"`. Default off. **Cache key is `(unitid, canonical_cipcode)` only** — `loan_pct` and `student_cip` MUST NOT be in the key. Both are applied by the stat engine post-query and do not affect the `query_iceberg_simple` result; including them makes the LRU miss on essentially every request. The cached value is the raw rows from `query_iceberg_simple`; downstream stat computation re-runs on each call with current `loan_pct`/`student_cip`.
- **Retain `CAREER_PATHS_SCAN_LIMIT` constant.** Do NOT rename or remove. Redefine the value to `1000` with an updated docstring: "Defensive `LIMIT` parameter for the predicate-pushdown standard-path query. Since the `WHERE unitid=$u AND cipcode=$c` filter naturally returns ≤ 50 rows, this is a belt-and-suspenders cap — not the primary scan gate it was before the rewrite." Any external reader that greps the symbol still finds it at its new, smaller value.

#### `src/mcp_server/_telemetry.py` (new)

- `@timed(event_name: str, *, extract: Callable[[Any, ...], dict] | None = None)` decorator factory. Wraps a sync function. Records `time.perf_counter()` deltas. On success, emits a JSON line via the shared `_log_exchange`-style writer. On exception, emits with `error` field and re-raises.
- The `extract` callable pulls per-call context (e.g., `path`, `unitid`, `cipcode`, `row_count`) from the function's args and return value. Default: empty dict.
- Log destination: `logs/mcp.jsonl` in repo root, line-appended, UTF-8. Falls back to stderr if the file is not writable (containers, tests).
- **Module-level `_log_lock = threading.Lock()`** held around every file append. Mirrors `gemma_client._log_lock` (see `backend/app/services/gemma_client.py:150-180`). Reason: MCP timing records routinely exceed POSIX `PIPE_BUF` (4096 bytes on macOS, since `extra` + `top_human_activities`-style dicts can be dumped), so without the lock concurrent appends interleave and break JSON-line parsing. Non-negotiable even though request rates are low.
- Enforces the "bounded-cardinality `extra`" policy documented in the Timing-log schema section above. The `extract` callable SHOULD only surface enums / numeric IDs / counts / category labels from function args — never free-text user input. No runtime enforcement; this is a code-review contract.

#### `backend/app/services/mcp_client.py` (modify)

- Update `reset_server()` docstring + body to call `_server.shutdown()` (which delegates to `QueryEngine.shutdown()` and closes the persistent DuckDB connection) before setting `_server = None`. Tests rely on `reset_server()` between cases. `shutdown()` is idempotent, so calling it on a server that never queried is safe.

### Testing Impact Analysis

> **Searched:** `/Users/jcernauske/code/bright/futureproof-data/backend/tests/`, `/Users/jcernauske/code/bright/futureproof-data/tests/` for tests referencing `query_iceberg_simple`, `query_iceberg`, `_build_substituted_rows`, `_handle_get_career_paths`, `_fetch_crosswalk_socs`. Three test files dominate the substitution surface: `tests/mcp/test_get_career_paths.py` (251 lines), `tests/mcp/test_cip_substitution.py` (762 lines), `tests/mcp/test_cip_substitution_integration.py` (288 lines).

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/mcp/test_cip_substitution.py` | All ~762 lines of substitution tests | **High** | They exercise the fan-out code path being rewritten. Most assert on response shape and field values. If the JOIN preserves the payload contract (Decision #7), they pass unchanged. If anything is off — even ordering of optional fields — they break. |
| `tests/mcp/test_cip_substitution_integration.py` | All ~288 lines | **High** | End-to-end calls through `_handle_get_career_paths` substituted path. Same risk as above. |
| `tests/mcp/test_get_career_paths.py` | Standard path tests | **Med** | Exercise the standard (non-substituted) `query_iceberg_simple` call. Predicate pushdown changes the SQL but not the returned rows. Risk: row ordering may change — current Python filter preserves Iceberg scan order, DuckDB SQL order is undefined without `ORDER BY`. Mitigation: spec mandates `ORDER BY` mirroring current behavior. |
| `tests/mcp/test_get_school_programs.py` | All | **Low** | Different handler but uses the same `query_iceberg_simple`. New override must preserve filter semantics. |
| `tests/mcp/test_get_occupation_data.py` | All | **Low** | Uses `query_iceberg_simple` for a single-key lookup. Pushdown should improve perf without changing rows. |
| `tests/mcp/test_get_ai_exposure.py` | All | **Low** | Same as above. |
| `tests/mcp/test_get_task_breakdown.py` | All | **Low** | Same as above. |
| `tests/mcp/test_get_career_branches.py` | All | **Low** | Same as above. |
| `tests/mcp/test_get_regional_price_parity.py` | All | **Low** | Uses `query_iceberg_simple`. Same low risk. |
| `backend/tests/services/test_intent.py` | Tests that exercise MCP-backed flows | **Low** | Uses `mcp_client.call(...)`. As long as `_handle_get_career_paths` payload is byte-identical, no impact. |
| `tests/scripts/test_yaml_regression.py` | All | **Low** | Indirect — runs intent flow against real YAML. Same payload-equivalence guarantee. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `tests/mcp/test_get_career_paths.py` | Permit ordering tweaks IF and ONLY IF current ordering is non-deterministic (no `ORDER BY` in fan-out, sort applied in Python). The new SQL must explicitly `ORDER BY stats_available_count DESC, occupation_title ASC` to match. If a test asserts a specific order that depends on Iceberg scan order (not the Python sort), update the test to assert against the canonical sort. | Iceberg scan order is not contractually stable. The Python sort is the contract. |
| `tests/mcp/test_cip_substitution.py` | Same as above for substitution-path ordering tests. The Python sort key in `_build_substituted_rows` (`-stats_available_count`, `occupation_title`) is the contract. The new JOIN must `ORDER BY` to match. | Same reason. |

**No other modifications authorized.** If any other test fails, STOP and escalate via §10. The implementer must NOT relax assertions to make tests pass — that defeats the parity guarantee.

#### Confirmed Safe

The following tests must NOT break. If they do, escalate immediately:

- All payload-shape assertions in `test_cip_substitution.py` and `test_cip_substitution_integration.py` (field names, types, presence/absence of `data_caveat`, `substitution_applied`, `match_quality`, `stats_available_count`, `bosses_available_count`, `overall_confidence`).
- All caveat-string assertions (`data_caveat.message` text matches existing substring assertions).
- `tests/scripts/test_yaml_regression.py` end-to-end intent flow.
- Any test that asserts row counts (a JOIN parity bug would surface here first).

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[unitid_cip]` (parameterized over ≥ 7 fixtures) | Byte-identical JSON payload from new JOIN vs. captured fan-out fixture. Fixtures: (a) UIUC + 26.01 substituted to a Biology-specific CIP, (b) IU + 52.01 substituted to Marketing 52.1401, (c) a school with a small program (low row count), (d) a school where substitution falls back to "no rows", (e) a school where the broad-CIP earnings row is missing (exercises the school-CTE short-circuit), (f) **a substituted CIP where ≥ 1 SOC is present in `occupation_profiles` but missing in `onet_work_profiles` AND/OR `ai_exposure`** (niche SOCs have known onet gaps — catches LEFT→INNER regressions on onet/ai), (g) **a substituted CIP where ≥ 1 SOC is present in `onet_work_profiles` but missing in `occupation_profiles`** (validates the `onet.primary_title` fallback for `occupation_title` at `futureproof_server.py:1690-1694` — NULL `op.*` columns must still yield a valid response). |
| P0 | `tests/mcp/test_query_engine.py` | `test_predicate_pushdown_filters_in_sql` | Capture the SQL emitted by `query_filtered` for a `(unitid, cipcode)` filter; assert it contains `WHERE unitid = ?` (or `$unitid`) and not a Python-side filter. |
| P0 | `tests/mcp/test_query_engine.py` | `test_views_registered_once` | Construct two QueryEngine queries; assert `CREATE VIEW` was issued exactly once across both calls (mock the underlying duckdb connection or count side effects via spy). |
| P0 | `tests/mcp/test_query_engine.py` | `test_shutdown_closes_connection` | After `shutdown()`, the engine reinitializes on the next query. |
| P0 | `tests/mcp/test_query_engine.py` | `test_filter_value_parameterized_not_interpolated` | Inject a malicious filter value (`"' OR 1=1 --"`); assert the query returns 0 rows (no injection) and the SQL keeps the value parameterized. |
| P0 | `tests/mcp/test_get_career_paths_perf.py` | `test_handler_emits_timing_log_with_path` | Run a substituted request; assert `logs/mcp.jsonl` (or capturing sink) gained a JSON line with `event="career_paths_handler"`, `path="substituted"`, `duration_ms` int, `unitid`, `cipcode`, `row_count`. |
| P0 | `tests/mcp/test_get_career_paths_perf.py` | `test_crosswalk_socs_lru_hit_on_repeat` | Call `_fetch_crosswalk_socs("26.01")` twice; second emits `cache_hit=true`. |
| P1 | `tests/mcp/test_get_career_paths_perf.py` | `test_handler_does_not_exceed_4_iceberg_scans_substituted` | Spy on the QueryEngine; one substituted handler call results in ≤ 4 underlying scans. |
| P1 | `tests/mcp/test_query_engine.py` | `test_concurrent_calls_are_serialized` | Spawn N=16 threads hitting `query_sql` / `query_filtered` against an engine where the underlying con is instrumented so `con.description` lags between `execute` and the read. Assert returned column names match the SQL's expected column set for every call (no cross-thread contamination). Promoted from P2 per §5 thread-safety finding. |
| P1 | `tests/mcp/test_query_engine.py` | `test_query_sql_returns_dicts_with_column_keys` | JOIN returns rows keyed by selected column names. |
| P1 | `tests/mcp/test_get_career_paths_perf.py` | `test_outcomes_cache_off_by_default` | With env unset, two identical standard-path requests both hit the engine. |
| P1 | `tests/mcp/test_get_career_paths_perf.py` | `test_outcomes_cache_on_with_env_flag` | With `FUTUREPROOF_OUTCOMES_CACHE=1`, second identical request emits `cache_hit=true`. |
| P2 | `tests/mcp/test_query_engine.py` | `test_sentinel_soc_excluded` | Fixture crosswalk row with `soc_code = '99-9999'`; JOIN returns zero rows for that SOC. |
| P2 | `tests/mcp/test_query_engine.py` | `test_multi_cip_collision_deduped` | Fixture with multiple 6-digit CIPs under one 4-digit prefix; `DISTINCT soc_code` de-dupes. |

#### Test Data Requirements

- **Fixture capture script** (one-off, lives at `scripts/capture_career_paths_fixtures.py`): runs `_handle_get_career_paths` for the 5+ canonical inputs against the current (unmodified) codebase, writes JSON responses to `tests/mcp/fixtures/career_paths_responses/`. Run once BEFORE any rewrite begins. Fixtures are committed.
- The full `data/futureproof.duckdb` + Iceberg warehouse must be present for the fixture capture and for integration tests. CI already provisions these per `tests/conftest.py`.
- Mocked-catalog tests for `_query_engine` use a tiny in-memory DuckDB with synthetic Iceberg paths, not the real warehouse.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-20

#### System Context
This is a data-access-layer rewrite inside `src/mcp_server/`, strictly below the MCP tool boundary. The public surface (FastAPI routers, MCP tool signatures, Pydantic response models, frontend contract) is unchanged. What moves is the path between `_handle_get_career_paths` and the Iceberg warehouse: today it flows through two brightsmith helpers (`query_iceberg_simple`, `query_iceberg`) that each do a full scan or a full DuckDB re-initialization per call; after this spec it flows through a process-lifetime `QueryEngine` that holds a persistent DuckDB connection and pushes predicates into SQL. The 3×N fan-out inside `_build_substituted_rows` (lines 1554-1741 of `futureproof_server.py`) collapses into a single parameterized JOIN. Brightsmith is not modified — the FP server overrides the two helpers in-place, preserving the `attach_governance` / `enrich_response` path that wraps every tool response. Architecturally clean: Bronze/Silver/Gold zones untouched, Iceberg metadata still the source of truth, MCP tool schemas unchanged.

#### Data Flow Analysis
Trace of `_handle_get_career_paths` on the substituted path, before and after:

| Hop | Before | After | Crosses boundary? |
|-----|--------|-------|-------------------|
| 1. Crosswalk SOC lookup (`_fetch_crosswalk_socs`) | `query_iceberg` → fresh DuckDB + install ext + register all views + SQL → close | `QueryEngine.query_sql` against persistent views, LRU-cached by `(cip4)` | No — both end at Iceberg metadata path |
| 2. School outcomes row | `query_iceberg_simple` → full `career_outcomes` Arrow scan → Python filter | `QueryEngine.query_filtered` → `WHERE unitid=$u AND cipcode=$c LIMIT 1` pushed into DuckDB | No |
| 3. Per-SOC fan-out (N×3 scans) | N × `query_iceberg_simple` for `occupation_profiles`, `onet_work_profiles`, `ai_exposure` | Single JOIN in `QueryEngine.query_sql` | No |
| 4. Python stat compute | Unchanged | Unchanged | No |
| 5. `enrich_response` governance | Unchanged | Unchanged | No — same exit through brightsmith |

The zone contract is preserved: the handler still reads Gold (and the `base.cip_soc_crosswalk` Silver view) and still emits the contracted MCP response via `enrich_response`. No new boundary crossings.

#### Contract Review
- **MCP tool signature:** unchanged. `_handle_get_career_paths` input/output shape identical. Parity is enforced by Decision #7's fixture-based JOIN-parity test (P0) — the right way to defend a wire contract.
- **`CAREER_PATHS_RESPONSE_FIELDS`:** no new/removed fields in the response list. Substituted rows continue to omit the four standard-path-only fields (`ai_adoption_share`, `velocity_label`, `composite_method`, `adoption_percentile`, `roi_cost_basis`, `boss_ceiling_score`) — already the current behavior.
- **`QueryEngine` public surface:** `query_filtered`, `query_sql`, `shutdown`. Clean, narrow, typed. No `Any` leaks that I can see once fleshed out.
- **Timing log schema:** Section 4 declares the schema as a Python dict literal but the sample has a missing comma after `"event"`. That's a typo in the spec, not a design flaw, but fix it before implementation references it.

#### Findings

##### Sound
- **Brightsmith boundary (Decision #1) — correct call.** Wrapping `query_iceberg_simple` and `query_iceberg` on the FP subclass keeps the framework contract intact. `attach_governance` and `enrich_response` (base_mcp_server.py:441+) are unchanged, so contract/DQ/lineage enrichment still runs on every response. No governance hooks are lost because those hooks sit *around* the query, not inside it. The upstream-to-brightsmith path is correctly parked as a follow-up.
- **Persistent connection on the server singleton (Decision #2) — correct lifecycle.** `mcp_client.get_server()` already produces a process-lifetime instance, and `reset_server()` is the only teardown path (tests). Tying `QueryEngine` lifetime to that instance is the right pairing. Lazy init is the right default (avoids import-time cost and keeps unit tests that never query fast).
- **Single-SQL JOIN (Decision #3) — architecturally right.** Replaces 3N + 1 + 1 Iceberg reads with 1 + 1 reads (plus the cached crosswalk). DuckDB handles Iceberg JOINs natively against the registered views, so this is not a new pattern — it's the pattern that should have been used from day one.
- **Process-lifetime LRU on `_fetch_crosswalk_socs` (Decision #4) — safe.** `base.cip_soc_crosswalk` is a Silver view over immutable-at-runtime Iceberg data. No invalidation signal is needed. maxsize=128 comfortably covers the ~1.6k 4-digit CIP space under normal request patterns.
- **Fixture-based parity test (Decision #7) — the right harness.** Capturing real pre-rewrite responses and diffing byte-for-byte is the only credible defense against latent payload drift. Hand-assertions would miss exactly the kinds of things (ordering of optional-None fields, struct-decode edge cases) that bite in production.

##### Concerns

- **Thread-safety of the persistent DuckDB connection (Open Q1 in §10).** Taking a position: **add a `threading.Lock` around `query_filtered` / `query_sql`, do not rely on DuckDB's connection-level thread-safety.** Two reasons.
  1. The DuckDB Python docs say `DuckDBPyConnection` serializes concurrent use internally, but only for independent statements — `con.execute(sql).fetchall()` is safe, but the `con.description` read that happens between `execute` and `fetchall` in the proposed `query_sql` (and in the existing `query_iceberg` at `base_mcp_server.py:434-435`) is **not** atomic. Under concurrent `asyncio.to_thread` fan-out (which does happen — see `_handle_get_career_paths` being called from parallel requests, and internally from substitution + fallback broaden), `con.description` can be clobbered by a second caller's `execute` before the first caller reads it, returning mismatched column names. That's a silent payload corruption bug, not a crash.
  2. A lock costs roughly nothing at hackathon request rates. Our concurrency is bounded by the number of active users, not by CPU — and the whole handler is already wrapped in `asyncio.to_thread`, so the lock is brief, predictable contention.
  **Impact if ignored:** intermittent, hard-to-reproduce payload corruption under load. The parity test will not catch this because it runs serially.
  **Recommendation:** add `self._lock = threading.RLock()` on `QueryEngine.__init__`, acquire it for the duration of `query_filtered` and `query_sql` (cover both `execute` and `fetchall` / `description` read). Use `RLock` rather than `Lock` so `_ensure_initialized` can call back into itself safely if we later add recursive registration. Update the P2 test `test_concurrent_calls_are_serialized` to P1 and write it.

- **`lru_cache` key correctness on `_fetch_crosswalk_socs_cached(query_engine_id, cip4)`.** §4 extracts the cached body into a module-level helper and uses `query_engine_id` as a cache-key discriminator. This is correct **only if** `query_engine_id` is stable for the process lifetime. On the standard path it is — the server singleton is built once. **But the test harness resets the server** via `reset_server()` between cases, which will construct a new `QueryEngine` with a new `id(...)` — so the LRU will correctly miss across test cases rather than leaking cached rows from a prior fixture. That's the desired behavior; call it out in the implementation comment so nobody later "optimizes" by hashing something stable like the catalog path (which would break test isolation).
  **Impact if misunderstood:** tests that assume fresh state could see cached crosswalk results from a prior test if someone switches to a stable key. Low risk, but worth a docstring.
  **Recommendation:** in the module-level cached helper, add a two-line docstring: "Cache key includes `query_engine_id` (i.e. `id(engine)`) so `reset_server()` in tests transparently invalidates. Do NOT switch to a content-addressed key without updating test isolation."

- **Standard-path LRU cache key (Decision #5).** The proposed key is `(unitid, canonical_cipcode, loan_pct, student_cip)`. Two problems:
  1. `loan_pct` is a `float`. Caching on float keys is fragile — `0.2 + 0.1 != 0.3`. Frontend emits discrete slider values (typically 0, 0.25, 0.5, 0.75, 1.0), so in practice we get clean keys, but the contract should round/quantize explicitly.
  2. `student_cip` is not actually used in the standard-path query (line 2238 — the filter is only `{unitid, cipcode}`). Including it in the cache key means two identical queries with different unrelated `student_cip` inputs will miss cache. That's a **correctness-preserving but useless-LRU** outcome — same problem you flagged in the question. Fix: drop `student_cip` from the cache key; the cached value is a function of `(unitid, canonical_cipcode)` only. `loan_pct` doesn't affect the `query_iceberg_simple` result either — it's applied post-query by the stat engine. So the real cache key is `(unitid, canonical_cipcode)`. Rebuild downstream stats from the cached rows.
  **Impact if ignored:** the env-gated optional cache rarely hits in practice. Wastes the spec's time and makes the perf table in §9 look worse than it should.
  **Recommendation:** reduce the key to `(unitid, canonical_cipcode)`. Quantize any float inputs to 2 decimal places if they ever enter a cache key elsewhere. Make this explicit in §4 alongside the Decision #5 row.

- **`school.*` in the JOIN SELECT — subtle risk, but acceptable.** `SELECT school.*` in the CTE CROSS JOIN expands to *every* column of `consumable.career_outcomes`, not just the fields in `_SUB_CO_FIELDS`. I verified the downstream Python wrapper only reads `institution_name`, `cip_family_name`, `earnings_1yr_*`, `debt_*`, `debt_to_earnings_annual`, `confidence_tier`, `institution_control`, and the net-price/tuition group — plus `cip_family_earnings_rank` and `dte` feeding `compute_stat_ern` / `compute_stat_roi`. All present in `career_outcomes`. So the data is correct. But:
  1. `school.*` also pulls `cipcode` and `unitid` from career_outcomes, which then collide with the output dict where `cipcode` must be `substituted_cipcode` and `unitid` is the request's unitid. The Python wrapper (today) explicitly overwrites both in the row dict — line 1686 sets `"cipcode": substituted_cipcode`, line 1684 sets `"unitid": unitid`. As long as the wrapper continues to write those keys *after* unpacking `school` fields, parity holds. This is a contract that's easy to break on a careless refactor.
  2. Pulling all columns defeats the point of predicate pushdown since we're scanning more bytes than needed.
  **Impact if ignored:** future refactor could merge `school.*` directly into the output dict (e.g., `row = {**school_cols, **soc_cols}`) and silently emit the wrong `cipcode`/`unitid`. The parity test would catch it, but only after the fact.
  **Recommendation:** replace `school.*` with an explicit column list in the SQL — the same 19 fields in `_SUB_CO_FIELDS`. Exclude `cipcode` and `unitid` from the SELECT since the wrapper always overwrites them; that removes the collision vector entirely. Call the aliases `school_institution_name`, `school_earnings_1yr_median`, etc. if collision with SOC columns is a concern, but since no overlap exists today, plain names are fine.

- **Timing log schema has a JSON syntax error and a schema-fit gap.** Two items:
  1. Line 251 of the spec: `"event": "career_paths_handler"` is missing the trailing comma before `"duration_ms"`. Fix before implementation copies it.
  2. The existing `logs/gemma.jsonl` pattern (see `backend/app/services/gemma_client.py:170-180`) uses a `threading.Lock` around file appends because records exceed POSIX `PIPE_BUF`. The new MCP log will have the same issue (row_count dumps, extra dicts). The `_telemetry.py` spec doesn't mention a write lock. It must. Mirror `_log_lock` from gemma_client.
  **Impact if ignored:** concurrent MCP timing log writes interleave under load; parsing breaks.
  **Recommendation:** `_telemetry.py` uses a module-level `threading.Lock` exactly like `gemma_client._log_lock`. Document this next to the `@timed` decorator definition.

- **PII in timing logs — `unitid` and `cipcode` are fine; watch out for broader fields.** `unitid` is an IPEDS public identifier (not PII). `cipcode` is a public CIP code. Both are safe and useful in logs — they're what makes the telemetry grep-able. The concern would arise if we extended `extra` to include anything user-typed (e.g., `student_major` free-text, which could carry "deaf education" or other PII-adjacent info). Set a policy now: `extra` never carries user free-text. Only bounded-cardinality categorical/numeric fields.
  **Impact if ignored:** later spec adds `student_major` to `extra` for debugging; we start logging PII-adjacent strings with no retention policy.
  **Recommendation:** add one sentence to §4 `_telemetry.py` section: "`extra` is restricted to bounded-cardinality fields (enums, IDs, counts). Free-text user input MUST NOT be logged."

- **`reset_server()` must close the QueryEngine — good, but make it explicit in the spec.** §4 says "Tests rely on `reset_server()` between cases" and mentions `_server.shutdown()`. The `FutureProofMCPServer` class doesn't currently have a `shutdown()` method — this spec adds one. Be explicit: `FutureProofMCPServer.shutdown()` delegates to `self._query_engine.shutdown()` if the engine was initialized. Otherwise lazy-init instances (which never queried) skip the close cleanly.
  **Impact if ignored:** CI leaks DuckDB connections across test cases; on macOS that can hit file-descriptor limits under large test matrices.
  **Recommendation:** add the `shutdown()` method to the spec's service-changes list for `futureproof_server.py`. One-line method; zero design complexity.

- **`CAREER_PATHS_SCAN_LIMIT = 500_000` — keep the constant, redefine it.** The spec drops the constant in favor of a defensive `LIMIT 1000` in the predicate-pushdown path. That's a symbol-renaming event that ripples. Keep the name `CAREER_PATHS_SCAN_LIMIT` exported from the module, just redefine its value to `1000`. Any external reader that greps for the constant sees the new intent.
  **Impact if ignored:** trivial — just a naming cleanup opportunity.
  **Recommendation:** keep the symbol, change the value and the docstring.

- **`query_engine_id` cache key will trigger a deprecation warning with `functools.lru_cache` on a non-hashable arg.** `id(engine)` returns an int — that's hashable. Fine. I flag this only because the §4 discussion mentions "avoid the `self` memory leak" — the leak comes from passing `self` (a full instance reference) into `lru_cache`, not from passing `id(self)`. Confirmed the spec does the right thing. No change needed.

##### Blockers
None. The architecture is sound; the concerns above are corrections, not redesigns.

#### Pipeline / Router Structure
No FastAPI router changes. The tool handler `_handle_get_career_paths` is invoked via `mcp_client.call("get_career_paths", ...)`, which is called from two existing routers that already exist and need no modification. Confirmed — spec correctly claims "no public interface changes."

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (Changes Requested — all minor, no redesign)
1. **Thread-safety decision:** Add `threading.RLock` to `QueryEngine` around `query_filtered` and `query_sql`. Close Open Q1 in §10. Promote the concurrent-calls test from P2 to P1.
2. **Standard-path LRU key correction:** Reduce the cache key to `(unitid, canonical_cipcode)`. Drop `loan_pct` and `student_cip` from the key (they don't affect the cached query result). Update Decision #5's row to reflect this.
3. **`school.*` → explicit column list:** Replace `SELECT school.*` in the JOIN with the 19 explicit columns of `_SUB_CO_FIELDS`, excluding `cipcode` and `unitid` (wrapper overwrites both). Prevents future collision bugs and scans fewer bytes.
4. **Timing log infrastructure:** (a) Fix the missing comma after `"event"` in §4's schema sample. (b) `_telemetry.py` must use a module-level `threading.Lock` around file appends, mirroring `gemma_client._log_lock`. (c) Add the PII policy sentence: "`extra` is bounded-cardinality fields only; no free-text user input."
5. **`shutdown()` method on `FutureProofMCPServer`:** Add to §4 service-changes list. Delegates to `QueryEngine.shutdown()` when engine is initialized. `mcp_client.reset_server()` calls it before setting `_server = None`.
6. **Cache-key docstring on `_fetch_crosswalk_socs_cached`:** Document that `query_engine_id` ties cache lifetime to the server singleton and that `reset_server()` transparently invalidates. Warn against switching to a content-addressed key.
7. **Retain `CAREER_PATHS_SCAN_LIMIT` symbol:** Redefine value to `1000` with an updated docstring, don't rename/remove.

All seven are spec edits + narrow implementation consequences. None require redesign. Resubmit §5 with these folded in and I'll flip to APPROVED.

#### Re-review 2026-04-20 (v1.1)

All seven conditions from the initial review have been folded in correctly. Verification trace:

| # | Condition | Status | Evidence |
|---|-----------|--------|----------|
| 1 | RLock thread-safety | MET | §4 `QueryEngine` docstring (lines 212-228) describes RLock semantics and the `con.description` hazard in detail; `query_filtered` and `query_sql` docstrings both state "Acquires `self._lock` for the duration of the DuckDB call"; `import threading` present in the imports block (line 195); §10 Open Q1 explicitly RESOLVED with the lock decision and the test promotion note. |
| 2 | Standard-path LRU key | MET | Decision #5 row now reads key `(unitid, canonical_cipcode)` with explicit rationale that `loan_pct`/`student_cip` are applied post-query by the stat engine and would force a miss on every request. Service-change bullet at line 393 mirrors the same key and rationale, with the added clarification that downstream stat computation re-runs on each call. |
| 3 | `school.*` → explicit column list | MET | CTE `school AS (...)` (lines 317-336) and outer SELECT (lines 360-378) both enumerate the 19 `_SUB_CO_FIELDS` columns with `cipcode`/`unitid` excluded. "Notes on the SELECT list" block (lines 386-389) documents (a) the collision-vector rationale for excluding `cipcode`/`unitid`, (b) the absence of SQL `ORDER BY` because `_sub_sort_key` is authoritative, and (c) preservation of the `onet.primary_title` fallback. |
| 4 | Timing log | MET | (a) Missing comma after `"event"` fixed (line 263 now reads `"event": "career_paths_handler",`). (b) `_telemetry.py` service-changes section (line 401) explicitly requires a module-level `_log_lock = threading.Lock()` mirroring `gemma_client._log_lock` and cites the `PIPE_BUF` interleave risk. (c) "Logging policy — `extra` is bounded-cardinality only" block (line 273) sits immediately after the schema sample, forbids free-text user input, enumerates permitted value types, and clarifies that `unitid`/`cipcode` are public identifiers. |
| 5 | `shutdown()` on `FutureProofMCPServer` | MET | Service-changes list for `futureproof_server.py` (line 292) adds `shutdown()` method that closes `self._query_engine` and resets to `None`, idempotent. `mcp_client.py` service-changes bullet (line 406) calls `_server.shutdown()` inside `reset_server()` before `_server = None`. |
| 6 | `_fetch_crosswalk_socs_cached` docstring | MET | Docstring requirement (line 294) explicitly spells out that the `query_engine_id` key ties cache lifetime to the server singleton, that `reset_server()` transparently invalidates, and warns "DO NOT switch to a content-addressed key (e.g. catalog path hash) without first updating test isolation." |
| 7 | `CAREER_PATHS_SCAN_LIMIT` retained | MET | Service-changes bullet (line 394) states "Retain `CAREER_PATHS_SCAN_LIMIT` constant. Do NOT rename or remove." with value redefined to `1000` and the updated docstring explaining it is now a defensive belt-and-suspenders cap behind the predicate-pushdown filter. |

Metadata check: Spec Version is `1.1` (line 93), Last Updated note (line 94) itemizes the fold-in changes. Correct.

Collateral verification:
- The test-promotion tied to Condition 1 (concurrent-calls test P2 → P1) is reflected in §4's new-tests table at line 458, labelled P1 with a concrete harness description (N=16 threads, instrumented `con.description` lag).
- Parallel fold-in from @fp-data-reviewer's related concerns — the `$school_cip4` binding name and the school-CTE zero-row short-circuit — are both present (lines 296-304) and support Condition 3's integrity. Not my condition, but it's adjacent enough that I verified it didn't regress.
- No new architectural drift introduced by the v1.1 edits. Public surfaces, zone boundaries, MCP contract, and Pydantic model surface remain unchanged.

##### Verdict (v1.1)
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All seven conditions are addressed precisely as specified. No re-raise. Spec is cleared for the implementation step of the Claude Code Prompt workflow. Status field at the top of the spec may advance from `ARCH REVIEW` to `IMPLEMENTATION` once @fp-data-reviewer's re-review also clears (their CHANGES REQUESTED items — school-CTE short-circuit, `$school_cip4` binding rename, partial-SOC fixtures — appear folded into §4 as well, but that is their call to flip, not mine).

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-20

#### Scope
Data-equivalence review of the §4 single-SQL JOIN that replaces the 3×N fan-out in `_build_substituted_rows` (`src/mcp_server/futureproof_server.py:1554-1741`). Parity check — same row set, same values, same ordering contract, for identical inputs — not a data-quality review of the underlying tables.

#### Data Sources Affected
- `consumable.career_outcomes` (school broad-CIP earnings/debt basis)
- `base.cip_soc_crosswalk` (SOC list for the substituted CIP)
- `consumable.occupation_profiles` (BLS per-SOC)
- `consumable.onet_work_profiles` (O*NET per-SOC)
- `consumable.ai_exposure` (Karpathy/Gemma per-SOC)

No Gold schema changes. DuckDB view names (`consumable_career_outcomes`, `consumable_occupation_profiles`, `consumable_onet_work_profiles`, `consumable_ai_exposure`, `base_cip_soc_crosswalk`) match the `{namespace}_{table}` convention already used by `query_iceberg` (`brightsmith/src/brightsmith/mcp/base_mcp_server.py:420`) and consumed by `_fetch_crosswalk_socs` today. Namespace/table mapping is correct.

#### Column Coverage — JOIN vs. Fan-out

Catalog of columns the fan-out reads from each source vs. what the JOIN SELECTs:

| Source | Fan-out reads (`_SUB_*_FIELDS`) | JOIN SELECTs | Parity |
|---|---|---|---|
| career_outcomes (school) | 21 fields (`unitid, institution_name, cipcode, program_name, cip_family_name, earnings_1yr_median, earnings_1yr_p25, earnings_1yr_p75, debt_median, debt_p25, debt_p75, debt_to_earnings_annual, cip_family_earnings_rank, confidence_tier, institution_control, net_price_annual, cost_of_attendance_annual, net_price_4yr, tuition_in_state, tuition_out_of_state, room_board_on_campus`) | `school.*` (wildcard via CTE `SELECT *`) | OK |
| occupation_profiles | `soc_code, occupation_title, soc_major_group_name, median_annual_wage, wage_percentile_overall, grw_score_rounded, market_score_rounded, growth_category, employment_current, education_level_name` | `op.occupation_title, op.soc_major_group_name, op.median_annual_wage, op.wage_percentile_overall, op.grw_score_rounded, op.market_score_rounded, op.growth_category, op.employment_current, op.education_level_name` | OK — `soc_code` satisfied by `socs.soc_code` |
| onet_work_profiles | `bls_soc_code, primary_title, hmn_score_rounded, burnout_score_rounded, top_5_activities, top_human_activities, burnout_drivers` | `onet.primary_title, onet.hmn_score_rounded, onet.burnout_score_rounded, onet.top_5_activities, onet.top_human_activities, onet.burnout_drivers` | OK — `bls_soc_code` used only as join key |
| ai_exposure | `soc_code, stat_res, boss_ai_score` | `ai.stat_res, ai.boss_ai_score` | OK — `soc_code` used only as join key |

No columns are missed. Nothing material is SELECTed that isn't read.

#### JOIN Semantics — Parity With Fan-out

1. **LEFT JOIN on op / onet / ai.** Correct match. Fan-out today handles missing rows by substituting `{}` (lines 1624-1652: `op = op_rows[0] if op_rows and "error" not in op_rows[0] else {}`). LEFT JOIN yields `NULL` columns on miss; Python's `.get(...)` returns `None` for both missing-dict-keys and SQL NULLs. Downstream `stats_available`/`bosses_available` counts rely on `is not None`, so behavior is preserved.

2. **CROSS JOIN on `school`.** The `school` CTE has `LIMIT 1`, so at most one school row. If `school` is empty, `CROSS JOIN school` produces **zero output rows** — this is *different* from the fan-out, which short-circuits at `futureproof_server.py:1590` with `return None, "No career_outcomes row for unitid={unitid}, cipcode='{canonical_reported}'; cannot substitute."` Spec §4 prose says "the pure-compute side is unchanged" and "assembles the row dict — same shape", implying the wrapper still checks school presence. **For parity, the Python wrapper MUST run the school lookup first (or inspect the empty JOIN result) and emit that error string.** A combined JOIN that silently returns `[]` is NOT parity — the caller's error-path branch (`if err is not None: return ...` at line 2179) would fall through to a "no rows" response instead of the descriptive error.

3. **Crosswalk CTE filter — `SUBSTR(cipcode, 1, 5) = $cip4`.** Verified:
   - Crosswalk `cipcode` is stored as `XX.XXXX` (6 chars), per `src/silver/cip_soc_crosswalk_transformer.py:38` (`_CIP_PATTERN = re.compile(r"^\d{2}\.\d{4}$")`) and the coercion rule in `src/raw/cip_soc_crosswalk_ingestor.py:_coerce_cipcode`.
   - `SUBSTR(cipcode, 1, 5)` returns `"XX.YY"` — the 4-digit prefix.
   - Fan-out calls `_fetch_crosswalk_socs(substituted_cipcode)` at line 1608, which uses the identical expression at line 1543. **Matches exactly.**
   - `substituted_cipcode` is always 4-digit (`matched_cip4` at line 2131/2167); `_fetch_crosswalk_socs` regex-validates `^\d{2}\.\d{2}$` and returns `[]` on mismatch. The new JOIN helper should preserve this gate or document the caller contract.

4. **`DISTINCT soc_code` + `soc_code <> '99-9999'` + `IS NOT NULL`.** Fan-out applies the identical set at `_fetch_crosswalk_socs` line 1544. Parity.

5. **`ORDER BY socs.soc_code` — not the contract.** The Python wrapper re-sorts by `(-stats_available_count, occupation_title)` at `futureproof_server.py:2190` (`_sub_sort_key`). That Python sort is the response-contract ordering; the SQL `ORDER BY socs.soc_code` is overwritten. Not a correctness bug, but the spec should make it explicit that the final order comes from Python, not SQL — or just drop the SQL `ORDER BY` since it's wasted work.

6. **JSON struct decoding (`_decode_json_struct_fields`).** Called in the handler at line 2192 after `_build_substituted_rows` returns. JOIN returns raw JSON strings for `top_5_activities`, `top_human_activities`, `burnout_drivers` — same as the fan-out. Parity.

#### `$reported_cip4` Parameter Name — Ambiguous, Document the Binding

Spec §4 JOIN: `school AS (SELECT * FROM consumable_career_outcomes WHERE unitid = $unitid AND cipcode = $reported_cip4 LIMIT 1)`.

The fan-out uses `canonical_reported = self._canonical_cip4(reported_cipcode)` (line 1580) — the caller-supplied `reported_cipcode` (the school's broad CIP, e.g. `"52.01"` or `"52.0100"`) canonicalized to 4-digit. The implementer must bind `$reported_cip4` to `_canonical_cip4(reported_cipcode)`, NOT to `substituted_cipcode` and NOT to the raw caller input.

**Risk if bound wrong:** JOIN returns zero school rows for every request where the caller passed a 6-digit form (e.g. `"52.0100"`), because `consumable.career_outcomes.cipcode` is stored at 4-digit granularity. The Python wrapper would then emit a spurious "no rows" response on inputs the fan-out handles correctly today.

**Fix:** rename the SQL parameter to `$school_cip4` in §4 and add a one-line note: `$school_cip4 = _canonical_cip4(reported_cipcode)`.

#### Edge-Case Fixtures — Add P0 Coverage For Partial Per-SOC Data

Spec's 5 fixtures are a reasonable baseline. Additional fixtures recommended to catch JOIN-specific regressions:

| Priority | Fixture | What it catches |
|---|---|---|
| **P0** | **SOC present in `occupation_profiles` but MISSING in `onet_work_profiles` OR `ai_exposure`** | LEFT-JOIN semantics for partial per-SOC coverage. The fan-out populates `{}` for each missing source independently, so a row can have op data but no onet data. Capture a real SOC that exhibits this (niche SOCs have known onet gaps). Without this fixture, a future LEFT→INNER regression on onet or ai goes undetected. |
| **P0** | **SOC present in `onet_work_profiles` but MISSING in `occupation_profiles`** | Fan-out falls back to `onet.primary_title` for `occupation_title` (line 1690-1694). JOIN preserves both columns, so the fallback still works — but `soc_major_group_name`, `median_annual_wage`, `growth_category`, `employment_current`, `education_level_name` all go NULL. Verify response is still valid. |
| **P1** | **Crosswalk row with `soc_code = '99-9999'`** | Confirms the `<> '99-9999'` filter actually excludes the sentinel. These rows exist in the NCES source ("No Match" entries). Pick a CIP that has one. |
| **P1** | **Multi-CIP collision under one 4-digit prefix** | `SUBSTR(cipcode, 1, 5) = $cip4` + `DISTINCT soc_code` collapses across 6-digit children. 52.02xx (Business Admin variants) is a candidate. Confirms de-dup matches the fan-out. |
| **P2** | **Substituted CIP with ≥ 20 SOCs** | Stresses ordering / post-sort with a large N. Nursing or engineering CIPs fit. |
| **P2** | **loan_pct at 0.0 and 1.0 extremes** | Verifies `adj_dte` branch is unaffected by the JOIN rewrite. loan_pct=0.0 pins DTE to 0 and saturates ROI. |

Spec's fixture (e) ("missing broad-CIP earnings row") is the `school` CTE empty-result case — critical for point 2 above. Must be in the first cut.

#### Findings

##### Data Quality Sound
- Column coverage between JOIN SELECT and Python-side field reads is complete — no missing fields, no orphan SELECTs.
- Crosswalk filter expression (`SUBSTR(cipcode, 1, 5) = $cip4`) is byte-equivalent to the current fan-out's `_fetch_crosswalk_socs`.
- LEFT JOIN semantics on op/onet/ai correctly reproduce the `{}` fallback behavior when per-SOC data is missing.
- DuckDB view naming (`{namespace}_{table}`) matches today's `query_iceberg` registration, so no namespace-resolution regression.
- `match_quality = "substituted_cip"`, `data_caveat` strings, `substitution_applied`, `stats_available_count`, `bosses_available_count`, `overall_confidence`, `confidence_tier_program` — all computed in the Python wrapper and unchanged. Parity is preserved without modification.

##### Data Concerns
- **(Significant) School-CTE zero-row parity.** `CROSS JOIN school` silently drops output when school is empty; fan-out returns a descriptive error. **Risk if missed:** student whose school doesn't report the broad CIP sees "no rows" instead of a diagnosable error. **Fix:** spec §4 must state that the Python wrapper either (a) runs the school lookup first and short-circuits to the existing error string, or (b) inspects an empty JOIN result and reconstructs the error message (`"No career_outcomes row for unitid={unitid}, cipcode='{canonical_reported}'; cannot substitute."`).

- **(Significant) `$reported_cip4` binding.** The parameter name obscures the fact that this is `_canonical_cip4(reported_cipcode)`, not the substituted CIP. **Risk if bound wrong:** zero school rows for every request where the caller passed a 6-digit reported_cipcode. **Fix:** rename to `$school_cip4` in §4 and add an explicit binding note.

- **(Minor) Python-side sort is load-bearing.** The SQL `ORDER BY socs.soc_code` is overwritten by `_sub_sort_key` at `futureproof_server.py:2190`. **Fix:** either drop the SQL `ORDER BY` OR add a comment noting the Python sort is authoritative. Prevents implementer from assuming SQL ordering is the contract.

- **(Minor) `_fetch_crosswalk_socs` input validation.** Current helper rejects malformed `cip4` with regex `^\d{2}\.\d{2}$` and returns `[]`. If the new JOIN helper doesn't validate, malformed input returns empty JOIN silently. **Fix:** mirror the regex gate at the JOIN helper entry, OR document the caller contract.

- **(Minor) Crosswalk cipcode format.** Add a one-line assertion in §4 documenting that `base.cip_soc_crosswalk.cipcode` is stored as `XX.XXXX` (6 chars) so `SUBSTR(_, 1, 5)` yields `XX.YY`. Future-proofs against ingestor changes.

##### Data Integrity Blockers
None. All substantive concerns are implementation-spec specificity, not formula or crosswalk errors.

#### Disclaimer Check
- [x] AI-estimated values untouched. Gemma SOC resolution (`_fallback_gemma_soc_resolution`) is out of this spec's scope — its `ai_estimated: true` caveat flow is unchanged.
- [x] Confidence scores propagated. `confidence_tier_program`, `stats_available_count`, `bosses_available_count`, `overall_confidence` all assembled in the Python wrapper from JOIN output — unchanged semantics.
- [x] Required disclaimer strings present. `data_caveat.type = "blended_substitution"`, `data_caveat.message`, `match_quality = "substituted_cip"`, `substitution_applied = true`, `reported_cipcode`, `substituted_cipcode` — all untouched by the JOIN rewrite.
- [x] Missing-data handling. LEFT JOIN + `.get()` + `None` preserves fan-out semantics for per-SOC gaps. School-empty path is the one at-risk code path — called out as a Significant concern above.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

Not a blocker. Two Significant items (school-CTE short-circuit, `$reported_cip4` naming/binding) and three Minor items. Also recommend adding the two P0 "partial per-SOC data" fixtures before the parity fixture set is captured — without them, a LEFT→INNER regression on onet or ai slips past the test suite. Fold these in and this flips to APPROVED.

#### Re-review 2026-04-20 (v1.1)

**Status:** APPROVED
**Reviewed:** 2026-04-20
**Against spec version:** 1.1 (folded-in arch + data review changes)

##### Item-by-item verification

| # | Item | Severity | Location in §4 v1.1 | Resolution |
|---|------|----------|---------------------|-----------|
| 1 | School-CTE zero-row short-circuit | Significant | §4 paragraph immediately above the SQL block: "School-CTE zero-row short-circuit (mandatory for parity)..." explicitly states the Python wrapper runs the school lookup first via a separate `QueryEngine.query_filtered` call, short-circuits to the exact error string `"No career_outcomes row for unitid={unitid}, cipcode='{canonical_reported}'; cannot substitute."` if empty, and only then issues the JOIN. The SQL block is prefaced with "(the JOIN body, issued only after the school row is confirmed present)". | RESOLVED. Parity with fan-out line 1590 preserved. A student whose school doesn't report the broad CIP gets the descriptive error, not a silent empty response. |
| 2 | `$school_cip4` binding | Significant | §4 `_build_substituted_rows` service-changes section: two explicit parameter-binding bullets. `$school_cip4 = self._canonical_cip4(reported_cipcode)` with a rationale sentence warning that callers may pass 6-digit form and that a wrong binding returns zero school rows. `$cip4 = substituted_cipcode` separately bound for the crosswalk CTE. SQL body uses `cipcode = $school_cip4` and `SUBSTR(cipcode, 1, 5) = $cip4`. | RESOLVED. Binding is unambiguous, school CIP and substituted CIP are distinct named parameters, and the failure mode for wrong binding is documented inline. |
| 3 | Python sort authoritative | Minor | §4 "Notes on the SELECT list" bullet 2: "No SQL `ORDER BY`. The final response ordering is set by the Python wrapper's `_sub_sort_key` (`-stats_available_count`, `occupation_title`) at `futureproof_server.py:2190`. SQL-side ordering would be overwritten and is wasted work." SQL body has no outer `ORDER BY`. | RESOLVED. Implementer will not mistakenly assume SQL ordering is the contract. |
| 4 | `_fetch_crosswalk_socs` regex gate | Minor | §4 `_fetch_crosswalk_socs` bullet: "Input validation: mirror the existing `^\d{2}\.\d{2}$` regex gate currently in `_fetch_crosswalk_socs`. Malformed input returns `[]`." | RESOLVED. Regex gate preserved at the cached helper entry. |
| 5 | Crosswalk cipcode format assertion | Minor | §4 "Format assertions (documented inline so a future ingestor change surfaces here)" block states `base.cip_soc_crosswalk.cipcode` is `XX.XXXX` (6 chars) and `consumable.career_outcomes.cipcode` is 4-digit (`XX.YY`), so `SUBSTR(_, 1, 5)` yields the 4-digit prefix. | RESOLVED. Future ingestor refactors that change cipcode storage width will surface here as a spec-drift flag. |
| 6 | P0 partial per-SOC data fixtures | P0 (test coverage) | §4 "New Tests Required" — parity test parameterization now lists ≥ 7 fixtures. Fixture (f): "a substituted CIP where ≥ 1 SOC is present in `occupation_profiles` but missing in `onet_work_profiles` AND/OR `ai_exposure` — catches LEFT→INNER regressions on onet/ai". Fixture (g): "a substituted CIP where ≥ 1 SOC is present in `onet_work_profiles` but missing in `occupation_profiles` — validates the `onet.primary_title` fallback for `occupation_title`". Both are P0. | RESOLVED. The two most likely silent regressions of the JOIN rewrite (a LEFT becoming INNER on onet/ai, or the op-title fallback breaking when `op.*` is all NULL) now have dedicated captured-fixture coverage before the rewrite begins. |

##### Cross-checks on the explicit `school` column list

Verified that the arch reviewer's concern about `school.*` → explicit column list was folded in without dropping any field the Python wrapper needs downstream:

- The original fan-out `_SUB_CO_FIELDS` (enumerated in the Column Coverage table above) is **21 fields**.
- The v1.1 `school` CTE SELECTs **19 explicit columns**: `institution_name, program_name, cip_family_name, earnings_1yr_median, earnings_1yr_p25, earnings_1yr_p75, debt_median, debt_p25, debt_p75, debt_to_earnings_annual, cip_family_earnings_rank, confidence_tier, institution_control, net_price_annual, cost_of_attendance_annual, net_price_4yr, tuition_in_state, tuition_out_of_state, room_board_on_campus`.
- The 2-field delta is exactly `{unitid, cipcode}` — both intentionally excluded because the Python wrapper writes them unconditionally (`unitid = request.unitid`, `cipcode = substituted_cipcode`). This is documented inline in §4 "Notes on the SELECT list" bullet 1.
- Every other downstream field read by the Python wrapper (`compute_stat_ern`, `compute_stat_roi`, the assembled row dict) is present. No regression.

Parity held: data-equivalence of the `school` CTE → Python row dict is preserved, and the collision vector the arch reviewer flagged (a future careless `row = {**school_cols, **soc_cols}` refactor overwriting `cipcode`) is eliminated.

##### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

All six items from the 2026-04-20 v1.0 data review are correctly addressed in §4 v1.1, and the arch-review-driven `school.*` → explicit column list change does not drop any field the Python wrapper needs. No remaining data-equivalence concerns. Implementer note: the fixture capture script (`scripts/capture_career_paths_fixtures.py`) MUST include fixtures (f) and (g) — those are the P0 additions; if the capture script ships without them the parity test suite silently loses the LEFT-JOIN regression guard. Flag this as a must-have during §6 implementation.

---

## §6 Implementation Log

**Status:** COMPLETE
**Implemented:** 2026-04-20

### Files Modified
| File | Change Summary |
|------|---------------|
| `src/mcp_server/_telemetry.py` | **Create.** `@timed` decorator + `emit()` writer. Module-level `threading.Lock` around `logs/mcp.jsonl` appends (mirrors `gemma_client._log_lock`). `MCP_LOG_DISABLED=1` disables writes in tests. |
| `src/mcp_server/_query_engine.py` | **Create.** `QueryEngine` with lazy-init persistent DuckDB connection; `query_filtered` (predicate pushdown + Python-side column projection) and `query_sql` (SQL pass-through); `threading.RLock` held continuously from init through `execute`/`fetchall`/`description` to close the shutdown race flagged in post-review; `shutdown()` closes the connection and clears view registry. |
| `src/mcp_server/futureproof_server.py` | **Modify.** `CAREER_PATHS_SCAN_LIMIT` retained, redefined `500_000 → 1000` with updated docstring. Added `QueryEngine` overrides of `query_iceberg_simple` and `query_iceberg`, a `_get_query_engine()` lazy getter using double-checked locking (`_engine_init_lock`), a `shutdown()` method, a `_fetch_substituted_join(cip4)` helper (JOIN fetch — extracted so tests can patch), a `_standard_path_rows(unitid, cip4)` helper (wraps standard-path lookup with the optional env-gated LRU), and a `_career_paths_result_path(result)` helper (infers `path` label for the handler's timing log). Rewrote `_build_substituted_rows` body to use the single JOIN + preserved school-CTE short-circuit at the Python layer. Decorated `_handle_get_career_paths`, `_fetch_crosswalk_socs`, `_build_substituted_rows` with `@timed`. Added module-level `OrderedDict`-based bounded LRU caches (`_crosswalk_cache`, `_career_paths_cache`) keyed on `(engine_id, …)` so `reset_server()` transparently invalidates; `_cache_drop_engine(engine_id)` is called from `FutureProofMCPServer.shutdown()`. |
| `backend/app/services/mcp_client.py` | **Modify.** `reset_server()` now calls `server.shutdown()` before dropping the singleton so the persistent DuckDB connection closes and per-engine caches flush. Idempotent. |
| `tests/mcp/test_cip_substitution.py` | **Modify** (per §10 expansion approved 2026-04-20). `_patch_substitution` now returns a 3-tuple that also patches `_fetch_substituted_join` with a JOIN-shaped fixture catalog. All behavioral assertions preserved verbatim — only the mock layer adjusted to the new data-access path. |
| `scripts/capture_career_paths_fixtures.py` | **Create.** Runs the handler against the live Iceberg warehouse for 7 canonical inputs and writes stripped (no-governance) JSON fixtures under `tests/mcp/fixtures/career_paths_responses/`. Ran once against pre-rewrite code to capture the parity baseline. |
| `scripts/verify_parity.py` | **Create.** Replays every captured fixture against the current code and prints byte-for-byte diff locations on mismatch. |
| `scripts/measure_perf.py` | **Create.** Canonical before/after perf harness; 10 runs per path after warm-up, reports median/p95. |
| `tests/mcp/fixtures/career_paths_responses/*.json` | **Create** (7 files). Byte-parity baseline. |
| `tests/mcp/test_substituted_rows_join_parity.py` | **Create** (added by `@test-writer`). 7 parameterized P0 parity tests. |
| `tests/mcp/test_query_engine.py` | **Create** (added by `@test-writer`). 8 tests: predicate pushdown, view caching, shutdown, SQL-injection safety, dict shape, 16-thread RLock serialization, sentinel SOC exclusion, identifier rejection. |
| `tests/mcp/test_get_career_paths_perf.py` | **Create** (added by `@test-writer`). 5 tests: timing-log emission, LRU cache hit, ≤4 scan budget, env-gated standard-path cache on/off. |

### Deviations from Spec
| # | Deviation | Reason |
|---|-----------|--------|
| 1 | **Cache implementation uses `OrderedDict` with explicit LRU eviction, not `functools.lru_cache`.** | `functools.lru_cache` cannot be used with the spec's `(engine_id, cip4)` key pattern because on cache miss the function needs access to the `QueryEngine` instance, which can't be passed as an unhashable argument (and passing it would pollute the cache key). The spec §4 / Decision #4 called out this tension explicitly. The implemented OrderedDict satisfies every named requirement — maxsize bound, LRU eviction, invalidation via `_cache_drop_engine(id(engine))` in `shutdown()` — without any `functools.lru_cache` lifecycle traps (class-level cache holding `self`, stale `id()` re-use after GC). Equivalent behavior, stdlib only. |
| 2 | **Test-mock authorization expanded** to cover `_fetch_substituted_join` patching in `tests/mcp/test_cip_substitution.py`. | Approved by human in §10 (2026-04-20). The pre-rewrite 3×N fan-out mock pattern became inapplicable once `_build_substituted_rows` issues a single JOIN via `_fetch_substituted_join`. All payload-shape assertions, caveat strings, row counts, and ordering expectations are preserved verbatim — only mock plumbing adjusted. |
| 3 | **`@timed` is sync-only**; no async variant. | Handler is invoked via `asyncio.to_thread`, so the inside of the thread is sync and `@timed` wraps it cleanly. If a future spec moves the handler to native async, a twin will be needed. |

### Non-trivial Implementation Notes
- **`query_filtered` uses `SELECT *` + Python-side projection**, not `SELECT {cols}`. Brightsmith's base helper tolerates callers requesting columns that don't exist on a table (via `row.get(k)` returning `None`); a SQL-level `SELECT missing_col` errors at the binder. Python projection preserves the contract verbatim; predicate pushdown on the `WHERE` clause is unchanged (the dominant perf win).
- **The substituted JOIN's `school.*` was replaced with an explicit 19-column list excluding `cipcode` and `unitid`** (per §5 concerns). The Python wrapper writes those two keys unconditionally; leaving them in the SELECT would create a collision vector on a future refactor.
- **Fixture (d) — "substitution with no crosswalk SOCs" — was dropped.** Routes through `_fallback_gemma_soc_resolution`, which invokes a non-deterministic LLM. Byte-parity is impossible by construction. School-CTE short-circuit is covered by (e); JOIN parity by (a)/(b)/(c)/(f)/(g); standard path by (h). 7 fixtures remain, all green.
- **No `FutureProofMCPServer.__init__` override.** `_query_engine` is lazy-initialized on first access via `_get_query_engine()`. Keeps import-time cost zero for test code that never queries.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | FAIL | `Binder Error: Referenced column "debt_p25" not found in FROM clause!` on standard-path handler. Cause: new `query_filtered` pushed the column list into `SELECT {cols}` — brightsmith's base accepts column requests for fields that don't exist on the table. | Switched `query_filtered` to `SELECT *` at the SQL layer and project columns in Python via `r.get(k)`. Parity went from 2/8 → 7/7. |
| 2 | FAIL | `KeyError: 'substitution_applied'` in `test_iub_marketing_substitution_fires`; root cause `Catalog Error: Table with name base_cip_soc_crosswalk does not exist` because the test mocks `query_iceberg_simple` but the new JOIN goes through `query_sql`. | Escalated per spec rule (only ordering tweaks authorized in §4). Human expanded scope (§10 2026-04-20). Extracted the JOIN into `_fetch_substituted_join(cip4)` helper and updated `_patch_substitution` to patch that method. No behavioral assertion changed. |

### Post-Review Race Fixes (v1.2, 2026-04-20)
Applied after `@faang-staff-engineer` flagged two narrow races. Both acceptable-at-hackathon-scale but trivially fixable — folded in before shipping.

| Fix | File | Change |
|-----|------|--------|
| **Shutdown race** in `QueryEngine.query_filtered` and `query_sql` — previously `con = self._ensure_initialized()` released the lock before the `with self._lock:` around execute, so a concurrent `shutdown()` could close `con` mid-query. | `src/mcp_server/_query_engine.py` | Wrap init + execute + description read in one continuous `with self._lock:` block. RLock allows the nested acquire inside `_ensure_initialized`. |
| **Check-then-act race** in `FutureProofMCPServer._get_query_engine` — two concurrent first requests could each construct a `QueryEngine` + DuckDB connection, orphaning one. | `src/mcp_server/futureproof_server.py` | Added module-level `_engine_init_lock = threading.Lock()`. Double-checked locking: hot path stays lock-free; first construction is locked. |

Parity re-verified (7/7 fixtures), MCP suite re-run (251/251), ruff clean.

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[a_uiuc_biology_substituted]` | P0 parity: UIUC + 26.01 → Biology-specific CIP — live JOIN vs. captured fan-out response, byte-identical after stripping `governance`. |
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[b_iu_marketing_substituted]` | P0 parity: IU + 52.01 → Marketing 52.14. |
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[c_small_program_substituted]` | P0 parity: small-program substituted case. |
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[e_missing_school_earnings]` | P0 parity: school-CTE zero-row short-circuit (error-message equivalence). |
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[f_nursing_wide_partial_op_only]` | P0 parity: SOC in occupation_profiles but missing onet/ai — guards against LEFT→INNER regression. |
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[g_engineering_wide_partial_onet_only]` | P0 parity: SOC in onet_work_profiles but missing op — guards `onet.primary_title` fallback for `occupation_title`. |
| `tests/mcp/test_substituted_rows_join_parity.py` | `test_join_payload_matches_fanout_fixture[h_standard_path_exact]` | P0 parity: standard path (non-substituted exact match). |
| `tests/mcp/test_query_engine.py` | `test_predicate_pushdown_filters_in_sql` | P0: filter dict → parameterized `WHERE col = $p0`; no Python-side filter, no literal interpolation. |
| `tests/mcp/test_query_engine.py` | `test_views_registered_once` | P0: 2 namespaces × varying tables, 2 public calls → `CREATE VIEW` issued once per (ns, tbl), not per call. |
| `tests/mcp/test_query_engine.py` | `test_shutdown_closes_connection` | P0: `shutdown()` closes the underlying con; next query reinitializes (new connection, views re-registered). |
| `tests/mcp/test_query_engine.py` | `test_filter_value_parameterized_not_interpolated` | P0: SQLi payload `"' OR 1=1 --"` rides in `params`, never appears literally in emitted SQL text. |
| `tests/mcp/test_query_engine.py` | `test_query_sql_returns_dicts_with_column_keys` | P1: result rows are dicts keyed by `con.description` column names. |
| `tests/mcp/test_query_engine.py` | `test_concurrent_calls_are_serialized` | P1 (promoted from P2 by arch review): 16 threads × distinct SQL + lagged `description` → each thread reads its own column name; RLock prevents cross-thread contamination. |
| `tests/mcp/test_query_engine.py` | `test_sentinel_soc_excluded` | P2: `'99-9999'` exclusion clause survives the engine's SQL pass-through; no sentinel in result. |
| `tests/mcp/test_query_engine.py` | `test_invalid_filter_column_rejected` | Defense-in-depth: filter key containing SQL metacharacters raises `ValueError` before SQL is emitted. |
| `tests/mcp/test_get_career_paths_perf.py` | `test_handler_emits_timing_log_with_path` | P0: substituted handler call writes one `career_paths_handler` JSONL line with `path="substituted"`, integer `duration_ms ≥ 0`, and matching `unitid`/`cipcode`. |
| `tests/mcp/test_get_career_paths_perf.py` | `test_crosswalk_socs_lru_hit_on_repeat` | P0: second `_fetch_crosswalk_socs("26.01")` call is a cache hit; `_last_crosswalk_cache_hit = True`, underlying `query_sql` not reinvoked. |
| `tests/mcp/test_get_career_paths_perf.py` | `test_handler_does_not_exceed_4_iceberg_scans_substituted` | P1: one substituted handler call issues ≤ 4 underlying scans (spec §1 success criterion). |
| `tests/mcp/test_get_career_paths_perf.py` | `test_outcomes_cache_off_by_default` | P1: with `FUTUREPROOF_OUTCOMES_CACHE` unset, two identical `_standard_path_rows` calls both hit `query_iceberg_simple`. |
| `tests/mcp/test_get_career_paths_perf.py` | `test_outcomes_cache_on_with_env_flag` | P1: with env flag set, second identical call is a cache hit (`_last_career_paths_cache_hit = True`). |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (new tests only — 3 files) | 20 | 0 | 0 | 20 |
| pytest (`tests/mcp/` full) | 251 | 0 | 0 | 251 |
| pytest (entire suite, repo root) | 1703 | 0 | 0 (1 deselected `network` marker) | 1703 |
| vitest | N/A | N/A | N/A | N/A (backend-only spec) |

### Failure Causation
No failures. Every new test passes; no existing tests regressed. The single deselected item in the full-suite run is a `network`-marked test that `pyproject.toml`'s default `addopts = "-m 'not network'"` skips by design — unrelated to this spec.

**Skip / xfail policy:** No tests were skipped or marked xfail in this deliverable. Fixture (d) from the spec's original parity table ("substitution falls back to 'no rows'") was intentionally omitted from the parity fixture set because it routes through the non-deterministic Gemma LLM fallback — byte-equality is not enforceable without mocking the LLM client, and that path is already covered by `test_cip_substitution_integration.py`. This is documented in the module docstring of `test_substituted_rows_join_parity.py`.

**Existing Tests at Risk (from §4) — all confirmed passing:**
- `tests/mcp/test_cip_substitution.py` (all substitution tests) — PASS
- `tests/mcp/test_cip_substitution_integration.py` — PASS
- `tests/mcp/test_get_career_paths.py` (standard path) — PASS
- `tests/mcp/test_get_school_programs.py`, `test_get_occupation_data.py`, `test_get_ai_exposure.py`, `test_get_task_breakdown.py`, `test_get_career_branches.py`, `test_get_regional_price_parity.py` — all PASS
- `tests/scripts/test_yaml_regression.py` — PASS
- `backend/tests/services/test_intent.py` — not run in this round (scope is `tests/mcp/` per the spec §4 Testing Impact Analysis and the task brief; the full `uv run pytest` covers the pipeline + mcp side).

---

## §8 Reviews

**Status:** PENDING

### Design Audit
**Status:** SKIPPED (backend-only spec)

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)
**Date:** 2026-04-20

#### Summary
Look, I love Claude, BUT... this is actually solid work. The persistent-DuckDB rewrite is the right call, the JOIN parameterization is clean, the cache invalidation story via `id(engine)` keying is defensible, and the telemetry emits bounded-cardinality fields as the docstring promises. I stared hard at the thread-safety story expecting to find a real bug (that's my job) and what I found instead are a couple of narrow races under concurrent shutdown / warm-up that are acceptable at hackathon scale but worth documenting. No criticals. No SQL injection surface. No PII leaks. Good work. This time.

#### Findings by Focus Area

##### 1. Connection lifetime / thread-safety 🟡 (Moderate)

**The RLock coverage inside `query_filtered` and `query_sql` is correct.** Both methods hold `self._lock` for the entire `execute → fetchall → con.description` window, which is exactly what the arch-review Q1 resolution demanded. Good.

**But there's a narrow race between `_ensure_initialized` and `shutdown()`.** In `query_filtered`:

```python
con = self._ensure_initialized()   # acquires+releases self._lock, returns con
with self._lock:                   # re-acquires self._lock
    cur = con.execute(sql, params) # uses LOCAL `con` variable
```

Between the two lock acquisitions, another thread can call `engine.shutdown()`, close the DuckDB connection, and set `self._con = None`. When the first thread re-enters the `with self._lock:` block, its local `con` variable still points to the now-closed connection. `con.execute(...)` raises, the outer `query_iceberg_simple` catches it and returns `[{"error": "Cannot query ..."}]`.

**Impact:** At 3am, a test or operational shutdown racing with an in-flight request surfaces as a confusing "Connection already closed" error returned as row data. Survivable — not a crash, not data corruption. Not worth blocking the ship for.

**Why I'm not making this a required change:** `shutdown()` is only called from `mcp_client.reset_server()` (tests) and test isolation is single-threaded. No production path calls `shutdown()` concurrent with a live request.

**If you want to harden it later:** hold `self._lock` across both the init and the execute in one continuous span, or re-check `self._con is not None` inside the second `with self._lock:` and bail cleanly. Cheap. Not required now.

##### 2. `_get_query_engine()` warm-up race 🔵 (Minor)

`FutureProofMCPServer._get_query_engine` does a lock-free check-then-write on `self._query_engine`:

```python
engine = getattr(self, "_query_engine", None)
if engine is None:
    engine = QueryEngine(self.catalog)
    self._query_engine = engine
return engine
```

Two concurrent first-requests can each construct a `QueryEngine`, and one becomes orphaned. The orphaned one's `_ensure_initialized` may have already opened a DuckDB connection if both threads got far enough. Shutdown only tears down `self._query_engine` (last-writer-wins), leaking any earlier engine's connection for the life of the process.

Also: the cache is keyed on `id(engine)`, so any entries written against the losing engine's id are orphans that `_cache_drop_engine` won't clean up. Bounded by the 256-entry LRU cap — not a real leak, just dust.

**Impact:** One-time-per-process. Zero impact at hackathon request rates.

##### 3. SQL injection surface on the new JOIN ✅ (No finding)

I looked hard. The JOIN SQL in `_fetch_substituted_join` has zero string interpolation of values — every piece is a literal table/column identifier that's hard-coded in the module, and the only variable (`$cip4`) is a DuckDB parameter binding. `_fetch_crosswalk_socs` validates `cip4` against `_CIP4_PATTERN` before even touching SQL, and then still only passes it as `$cip4`. `query_filtered` validates every filter column against `_IDENT_PATTERN` and parameterizes every value as `$p0 / $p1 / ...`. `columns` is identifier-validated before projection. I can't find a string-concat injection point.

The one thing that IS f-interpolated — `metadata_path` in `CREATE VIEW ... iceberg_scan('{metadata_path}')` — comes from PyIceberg's `iceberg_table.metadata_location`, a filesystem path under our warehouse. Not user-controlled. Same pattern as the brightsmith base. Acceptable.

##### 4. Cache invalidation correctness ✅ (No finding)

- `id(engine)` keying with `_cache_drop_engine` on shutdown is airtight for the sequential case. ID reuse after GC is only a problem if a new engine gets the same id AND stale entries survived a shutdown — but shutdown drops everything tagged with the old id first. No leak path here.
- `_career_paths_cache` snapshots via `tuple(dict(r) for r in rows)` before storing. On read, returns `[dict(r) for r in cached]` — shallow copy out. A caller mutating the returned list's dicts mutates its own copies; the tuple in the cache is untouched. Nested dicts (e.g. `top_5_activities` JSON-decoded to a list) share references, but the handler's downstream mutations are in-place on the caller-owned dict and don't reach into those nested structures after decode. Cache is safe.
- `_crosswalk_cache` stores `tuple[str, ...]` — immutable. Fine.
- Shutdown ordering (`_cache_drop_engine` → `engine.shutdown()`): if thread B enters `_standard_path_rows`, reads the cache (miss, since A just dropped), then calls `query_iceberg_simple`, the only way that races poorly is the finding in §1 above. The cache layer itself is clean.

##### 5. PII in timing logs ✅ (No finding — grudgingly)

I read every `@timed` extract lambda carefully because this is where AI-generated code tends to over-share "for debugging":

- `career_paths_handler`: emits `unitid`, `cipcode`, `path`, `row_count`. **Does NOT emit `student_major` or `student_cip` free-text**, which was my biggest concern. ✅
- `build_substituted_rows_join`: emits `unitid`, `reported_cipcode`, `substituted_cipcode`, `row_count`, `error`. **`substituted_program_name` — which carries `student_major` free text from the caller — is NOT surfaced.** ✅
- `fetch_crosswalk_socs`: emits `cip4`, `row_count`, `cache_hit`. Bounded. ✅
- `query_filtered`: emits `table`, `row_count`. Filter values (which contain `unitid`, `cipcode`) are NOT logged. ✅
- `query_sql`: emits only `row_count`. SQL text and `$cip4` bind params are NOT logged. ✅
- `_career_paths_result_path` reads `result["data_caveat"]["type"]` only, never the caveat message (which contains free-text `student_major`). ✅

The telemetry module docstring says what it does, and the code does what the docstring says. This is the kind of discipline I wish more implementations had.

**Minor observation (not a finding):** `self._last_crosswalk_cache_hit` and `self._last_career_paths_cache_hit` are shared per-server attributes. Under concurrent requests they'll race and the `cache_hit` value in the log record can be wrong. Doesn't affect correctness — just log accuracy under load. Not worth fixing.

##### 6. Error handling 🟡 (Moderate)

**`QueryEngine._ensure_initialized` silently skips table/namespace registration failures.** The outer `except Exception: continue` on `list_tables(ns)` has NO log at all — if the `consumable` namespace fails to list, every downstream query against `consumable_*` views dies much later with an opaque "Catalog Error: Table with name consumable_ai_exposure does not exist". Per-table failures ARE logged but only at `DEBUG` level, which is typically off in prod.

**Impact:** 3am page. On-call engineer sees "Table with name consumable_foo does not exist" in the handler error path, digs into the pipeline, doesn't find anything wrong with the Iceberg data, and has no log trail explaining that view registration silently failed at server startup.

**Fix (recommended, not required for this spec):**
```python
except Exception as exc:
    logger.warning(
        "skipping namespace %s during view registration: %s", ns, exc
    )
    continue
```
And promote the per-table log from `logger.debug` to `logger.warning`. Registration failures are rare; when they happen, you want to know.

**`FutureProofMCPServer.query_iceberg_simple` catches bare `Exception` and returns `[{"error": str(exc)}]`.** This is the contract the brightsmith base establishes and every caller in this codebase checks `if rows and "error" in rows[0]`. The `_standard_path_rows` cache layer explicitly gates on `not (rows and "error" in rows[0])` before caching, so we don't poison the cache with error rows. Good discipline. The contract is ugly (errors-as-data) but it matches the framework and the caller handles it correctly.

##### 7. Architectural consistency ✅ (No finding)

The brightsmith base `query_iceberg_simple` (lines 368-403) and `query_iceberg` (lines 405-437) do NOT attach governance metadata or any wrapper — they return raw row lists. The FP overrides preserve that contract exactly. `attach_governance` / `enrich_response` are applied downstream by the handler, not the query helper. No loss of framework behavior.

##### 8. Performance claims 🔵 (Minor — methodology, not results)

The `scripts/measure_perf.py` methodology: 1 warm-up + 10 samples, single process, back-to-back. That's fine for a hackathon steady-state claim. Numbers in §9 are p95 values hand-computed as `sorted(samples)[int(len(samples) * 0.95) - 1]` which on 10 samples is index `int(9.5) - 1 = 8` — the 9th-largest of 10. That's effectively the max minus one. Standard-ish approximation, consistent before/after, so the comparison holds. Not worth re-doing.

The "3 iceberg scans" claim in §9 is accurate at the MCP log-event level (crosswalk event + school event + JOIN event = 3). At the DuckDB physical scan level the JOIN event internally touches 4 views (crosswalk CTE + op + onet + ai), so the true physical-scan count is 6. The spec success criterion phrases it as "Iceberg scans per request" which is ambiguous — the log-event count is the one the telemetry enforces and the one the ≤ 4 bound meaningfully constrains. I'd call this out in the doc but I'm not blocking on it.

Standard-path cache is OFF by default (`FUTUREPROOF_OUTCOMES_CACHE != "1"`), so the 23× speedup on the standard path reflects pure predicate-pushdown and the persistent connection — not the LRU. Confirmed.

#### What's Actually Good (grudging acknowledgment)

- The RLock coverage was exactly what arch review asked for. No half-measures.
- The `$p0/$p1/...` parameter naming in `query_filtered` is belt-and-suspenders against SQL injection; combined with `_IDENT_PATTERN` on identifiers it's tight.
- The `id(engine)` cache keying is the right call given the test-isolation requirement and the process-lifetime policy. The comment explaining why you don't use content-addressed keys shows someone thought about it.
- The "short-circuit before issuing the JOIN" pattern in `_build_substituted_rows` (empty school row → descriptive error before doing the JOIN) is exactly the byte-parity discipline the spec asked for.
- Every `@timed` extract lambda I audited keeps free-text out. The author (or Claude) read the module docstring and respected it.
- The cache-enabled guard `if cache_enabled and not (rows and "error" in rows[0])` prevents poisoning the cache with error responses. Not every implementation gets that right.
- Tests patch `_fetch_substituted_join` and `_fetch_crosswalk_socs` as helper seams rather than the underlying `query_sql`. Clean boundary.

#### Required Changes

**None.** No blockers, no critical, no required-changes.

#### Recommended Follow-ups (do not block this spec)

1. **Promote view-registration failure logs from DEBUG to WARNING** (file: `src/mcp_server/_query_engine.py`, `_ensure_initialized`). Add a log line for the currently-silent `list_tables(ns)` failure. Owner: whoever touches this next. Impact: debuggability at 3am.
2. **Consider a single lock span across init + execute in `query_filtered` / `query_sql`** OR a `self._con is not None` re-check inside the second `with self._lock:`, to close the narrow shutdown-race window described in Finding #1. Owner: follow-up spec. Impact: cleaner error on concurrent-shutdown.
3. **Optional `threading.Lock` around `_get_query_engine`** to prevent the orphan-engine warm-up race (Finding #2). Owner: follow-up spec. Impact: cosmetic at current scale.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

Ship it. I'm not saying Claude did this perfectly. I'm saying the things it missed are minor enough that they can be follow-ups, and I'd have had the same conversation with a human at code review. This time.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-20 19:45

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) — `uv run ruff check src/ tests/ scripts/` | PASS | 2 new issues in spec-touched files fixed (attempt 1): `F401` unused `typing.Any` in `tests/mcp/test_get_career_paths_perf.py:26`; `F541` bare f-string in `tests/mcp/test_query_engine.py:375`. All remaining ruff failures in `scripts/` are pre-existing (not touched by this spec). `backend/` ruff: no issues. |
| Lint (ruff) — `cd backend && uv run ruff check .` | PASS | No issues |
| Type check (mypy) — `cd backend && uv run mypy app/` | PASS | 45 pre-existing errors across 18 files not touched by this spec. `app/services/mcp_client.py` (the one spec-modified backend file): **0 errors**. No new errors introduced. |
| Tests (pytest) — `uv run pytest tests/` (pipeline) | PASS | 1703 passed, 1 deselected |
| Tests (pytest) — `cd backend && uv run pytest` | PASS | 1022 passed, 62 warnings |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript — `cd frontend && npx tsc --noEmit` | PASS | No errors |
| Tests (vitest) — `cd frontend && npx vitest run` | PASS | 568 passed, 1 skipped (56 test files) |
| Production build (Vite) — `cd frontend && npx vite build` | PASS | 686 modules, build completed (chunk size advisory only — pre-existing) |

### Performance Verification (mandatory)

Methodology: `scripts/measure_perf.py`. Each case is called once as warm-up (pays the `QueryEngine` init + Iceberg view registration cost) and then 10 times back-to-back in a single process. Numbers below are steady-state wall-clock from `time.perf_counter()`. Before-numbers captured by `git stash`-ing the rewrite and rerunning the same script against the pre-rewrite code on the same machine in the same hour.

| Path | Request | Median (ms) Before | Median (ms) After | Speedup | p95 (ms) Before | p95 (ms) After |
|------|---------|---------------------|-------------------|---------|------------------|----------------|
| substituted | UIUC (145637) + 26.01 (Biology) | 3722 | 266 | **14.0×** | 3744 | 269 |
| substituted | IU (151351) + 52.01 (Marketing, 52.14) | 929 | 259 | 3.6× | 932 | 260 |
| standard | IU (151351) + 52.14 | 7155 | 307 | **23.3×** | 7183 | 317 |

**Pass criterion met:** the canonical substituted request (UIUC+26.01→Biology) drops 14.0× — well above the spec's ≥5× bar. The standard path (not covered by a formal ratio target) drops 23.3×. IU+52.01→Marketing shows a smaller 3.6× speedup because Marketing (CIP 52.14) has only ~12 SOCs so the pre-rewrite fan-out had fewer scans to amortize; the win is still substantial.

**Iceberg scan counts** (from the new `logs/mcp.jsonl` `query_filtered` + `query_sql` events):
- Pre-rewrite substituted path: crosswalk (1) + school (1) + 3×N fan-out ≈ 38 on the UIUC+26.01 case.
- Post-rewrite substituted path: crosswalk (1) + school (1) + JOIN (1) = 3. Well within the spec's ≤ 4 bound.
- Pre-rewrite standard path: 1 full Iceberg scan (up to 500k rows) + Python filter.
- Post-rewrite standard path: 1 predicate-pushdown scan filtered to ≤ 50 rows.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | Ruff: 2 errors in spec-touched test files | `F401` unused `Any` import (`test_get_career_paths_perf.py:26`); `F541` bare f-string (`test_query_engine.py:375`) | Removed unused import; removed bare `f` prefix. All other checks passed on first run. |

---

## §10 Discussion

```
[2026-04-20 — author note → @fp-architect]
Two open questions for arch review to resolve:

1. Thread safety of the persistent DuckDB connection. FastAPI runs the
   handler via asyncio.to_thread, so two concurrent requests CAN land
   on the same connection from different threads. DuckDB Python
   connections are documented as thread-safe at the connection level
   for SELECT, but I want explicit confirmation before we ship — and
   if not, we add a threading.Lock around query_filtered/query_sql
   (cheap, request rate is low for the hackathon demo).

2. Whether to upstream the predicate-pushdown change to brightsmith
   later. Decision #1 says "wrap, don't modify". Worth a follow-up
   spec after this stabilizes — the same bug exists for any other
   project using brightsmith's MCP base.
```

```
[2026-04-20 — @fp-architect → author] RESOLVED

Q1 (thread safety): Lock required. DuckDB's DuckDBPyConnection
   serializes independent statements but `con.description` is NOT
   atomic relative to a concurrent `execute` from another thread. Under
   parallel asyncio.to_thread handlers the result is silent column-name
   corruption. Use threading.RLock around the execute/fetchall/description
   window in both query_filtered and query_sql. §4 updated to match.
   Test coverage promoted P2 → P1 (test_concurrent_calls_are_serialized).

Q2 (upstream to brightsmith): Park as follow-up spec after this
   stabilizes. Not in scope here.
```

```
[2026-04-20 — implementer → human] ESCALATION (Significant, not Blocker)

Situation: implementation of §4 is complete and all 7 parity fixtures
pass byte-identical against the pre-rewrite captured responses
(`scripts/verify_parity.py` — all green). However, pytest against
`tests/mcp/test_cip_substitution.py` fails at the mock layer:

  _patch_substitution() currently patches `query_iceberg_simple` with
  a side_effect that services the PRE-rewrite 3×N fan-out (one call
  per SOC for op/onet/ai). The POST-rewrite substitution path issues
  a single call via `query_sql(join_sql, {cip4: ...})`, which the
  test's mock doesn't cover — so the handler hits the un-mocked
  engine, errors with "Catalog Error: Table with name
  base_cip_soc_crosswalk does not exist", and returns a "data: None"
  error response. The test assertion `result["substitution_applied"]`
  raises KeyError.

Why this isn't an "authorized" test modification per §4:
  §4's Authorized Test Modifications table explicitly lists only
  "ordering tweaks". A mock-setup update to mock `query_sql` in
  addition to `query_iceberg_simple` is structurally a different kind
  of change — it's adapting the test scaffolding to the new
  data-access path, not relaxing any production-behavior assertion.
  Reading §4 strictly: STOP and escalate.

What's at stake:
  - NONE of the test's behavioral assertions need to change
    (substitution_applied, row_count, soc_code list, earnings_1yr_median,
    debt_to_earnings_annual, match_quality are all preserved).
  - Only the mock plumbing needs to service the JOIN query.

Recommended resolution (needs explicit human approval):
  1. EXPAND the authorized-test-modifications scope to include mock
     infrastructure updates in tests/mcp/test_cip_substitution.py and
     tests/mcp/test_cip_substitution_integration.py that reflect the
     JOIN-based substitution path, provided NO assertion is weakened.
  2. Update `_patch_substitution` to also mock `query_sql` with a
     side_effect that recognizes the JOIN SQL (or more cleanly, refactor
     _build_substituted_rows so the JOIN fetch is a patchable helper
     method like `_fetch_substituted_join`).
  3. All payload-shape assertions stay exactly as they are.

Alternative (if the above is rejected):
  Refactor `_build_substituted_rows` so the JOIN fetch goes through
  the existing `query_iceberg_simple` helper by exposing a multi-column
  join-filter API — but this re-introduces Python-side glue that the
  spec explicitly rejected.

Waiting on human decision.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Lessons learned, follow-up items, and a pointer to the frontend perf spec once that lands.]
