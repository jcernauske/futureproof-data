# Performance: SOC Retrieval Hot Path — Completion Report

**Spec:** `docs/specs/performance-soc-retrieval.md`
**Status:** COMPLETE
**Delivered:** 2026-04-20
**Spec Version:** 1.2

---

## Headline

The Set Your Course SOC retrieval hot path went from **3.7–7.2 seconds** to **260–310ms** steady-state per request. The dominant fixes were (1) a persistent DuckDB connection replacing per-call extension+view setup, (2) predicate pushdown replacing full-table scans + Python filters, and (3) a single parameterized JOIN replacing the 3×N substitution fan-out. Response payloads are byte-identical across 7 captured fixtures. All 251 MCP tests pass; 20 new tests added.

## Perf Table

| Path | Request | Median Before | Median After | Speedup | p95 Before | p95 After |
|------|---------|--------------|--------------|---------|------------|-----------|
| substituted | UIUC + 26.01 (Biology) | 3722 ms | 266 ms | **14.0×** | 3744 ms | 269 ms |
| substituted | IU + 52.01 (Marketing) | 929 ms | 259 ms | 3.6× | 932 ms | 260 ms |
| standard | IU + 52.14 | 7155 ms | 307 ms | **23.3×** | 7183 ms | 317 ms |

Iceberg scan counts (per substituted request):
- **Before:** ~38 (crosswalk + school + 3×N fan-out on ~12 SOCs)
- **After:** 3 (crosswalk + school + JOIN)

Spec pass criterion (≥5× on canonical substituted path) met with 2.8× headroom.

## What Shipped

| Component | File |
|-----------|------|
| Persistent DuckDB + Iceberg view registry | `src/mcp_server/_query_engine.py` (new) |
| Structured JSONL timing logs | `src/mcp_server/_telemetry.py` (new) |
| `query_iceberg_simple` / `query_iceberg` overrides; JOIN helper; LRU caches; handler timing decoration | `src/mcp_server/futureproof_server.py` (modify) |
| `reset_server()` → `server.shutdown()` | `backend/app/services/mcp_client.py` (modify) |
| JOIN-parity test mocks | `tests/mcp/test_cip_substitution.py` (modify, per §10 expansion) |
| 7 parity fixtures + capture script | `tests/mcp/fixtures/career_paths_responses/*.json`, `scripts/capture_career_paths_fixtures.py` |
| Parity verifier + perf harness | `scripts/verify_parity.py`, `scripts/measure_perf.py` |
| P0/P1/P2 tests (20 total) | `tests/mcp/test_substituted_rows_join_parity.py`, `tests/mcp/test_query_engine.py`, `tests/mcp/test_get_career_paths_perf.py` |

## Spec Workflow Actually Followed

| Step | Owner | Outcome |
|------|-------|---------|
| Architecture Review | `@fp-architect` | CHANGES REQUESTED (7 items) → folded into §4 v1.1 → APPROVED |
| Data Review | `@fp-data-reviewer` | CHANGES REQUESTED (2 Sig + 3 Minor + 2 P0 fixtures) → folded into §4 v1.1 → APPROVED |
| Implementation | Claude Code | 2 in-loop failures (documented in §6 Build Accountability); escalated once for test-mock scope expansion (§10 2026-04-20, human approved) |
| Testing | `@test-writer` | 20 new tests added, all pass; 251/251 MCP; 1703/1703 pipeline; 1022/1022 backend |
| Code Review | `@faang-staff-engineer` | APPROVED, 2 narrow races flagged (both folded into v1.2 below) |
| Verification | `@fp-builder` | All 8 checks pass after 1 fix (2 ruff issues in new test files); spec §9 populated |
| Race Fixes (post-review) | Claude Code | Shutdown race in `query_filtered`/`query_sql` + check-then-act race in `_get_query_engine` both closed; parity + suite re-verified |

## Deviations from Spec

1. **Cache: `OrderedDict` LRU instead of `functools.lru_cache`.** `functools.lru_cache` can't express the `(engine_id, cip4)` key pattern without either passing the engine (unhashable) or using a weak registry (fragile on id-reuse). The OrderedDict satisfies every stated requirement (maxsize, LRU, invalidation on shutdown). Stdlib only.
2. **Test-mock authorization expanded** for the JOIN path — approved by human in §10 2026-04-20. No behavioral assertions weakened.

## Known Non-Issues (documented, not blockers)

- Fixture (d) "substitution with no crosswalk SOCs" was dropped from the parity set — routes through `_fallback_gemma_soc_resolution`, which is non-deterministic by construction.
- Pre-existing mypy errors in `backend/app/routers/*` and ruff issues in `scripts/spike_compare.py` — not caused by this spec; untouched.

## Follow-ups

- Frontend perf spec (`docs/specs/performance-soc-reveal-frontend.md`) is unblocked.
- Potential future spec: upstream the predicate-pushdown change to brightsmith so every project benefits.
- Low-priority debuggability note from code review: `QueryEngine._ensure_initialized` logs per-table registration failures at DEBUG only. If a critical view silently fails to register, the log trail is thin. Consider elevating to WARNING in a follow-up.

## Final Verification Summary

| Check | Result |
|-------|--------|
| Pipeline pytest | 1703 passed, 1 deselected |
| Backend pytest | 1022 passed |
| MCP pytest (subset) | 251 passed |
| Frontend vitest | 568 passed, 1 skipped |
| Frontend TypeScript | Clean |
| Frontend Vite build | Clean (686 modules) |
| Ruff (spec-touched) | Clean |
| Mypy (spec-touched) | Clean |
| JOIN parity (7 fixtures) | 7/7 byte-identical |

**Ship it.**
