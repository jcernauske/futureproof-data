# Feature Report: SOC Expansion via Gemma Function Calling

**Spec:** `docs/specs/feature-soc-expansion-via-gemma-tools.md`
**Date:** 2026-04-20
**Status:** COMPLETE

## Summary

Shipped the project's first real Gemma function-calling integration (`tools=[...]` syntax). When a student's stated intent demands SOCs the BLS CIP-SOC crosswalk doesn't return (e.g., physicians for Biology + pre-med, or special-ed teachers for deaf education), Gemma now proposes up to 5 additional SOCs from a pre-filtered candidate pool drawn from the 832-SOC `consumable.occupation_profiles` universe.

## What Changed

| File | Change |
|------|--------|
| `backend/app/services/soc_expansion.py` | **New.** Core module: `expand_socs()` with synonym bridging, program-negating-crosswalk detection, candidate pool builder, Gemma tool-call invocation |
| `backend/app/services/gemma_client.py` | Added `generate_with_tools()` — sync helper for OpenAI-compatible function-calling with `tool_choice="required"` |
| `backend/app/models/api.py` | Added `intent_keywords` to `OutcomesRequest` and `BuildRequest` |
| `backend/app/services/stat_engine.py` | Threaded `intent_keywords` through `compute_pentagon()` and `compute_one()` |
| `backend/app/routers/builds.py` | Forwarded `intent_keywords` to stat engine |
| `src/mcp_server/futureproof_server.py` | Integrated expansion into both substituted and standard paths in `_handle_get_career_paths` |
| `frontend/src/api/build.ts` | Added `intentKeywords` param to `getOutcomes()` |
| `frontend/src/hooks/useSetYourCourse.ts` | Passed resolver's `intent_keywords` to `getOutcomes()` |

## Architecture Decisions

1. **Standard path expansion** — Standard-path rows are pre-joined from `program_career_paths`. Expansion extracts SOC codes, calls `expand_socs`, and builds new rows via dynamic JOIN for any Gemma-picked SOCs, marked `match_quality="gemma_expanded"`.
2. **Synonym bridging** — `SYNONYM_MAP` translates student language ("doctor", "pre-med") to BLS language ("physician", "surgeon") before substring matching. Without this, the canonical test case produces zero physician candidates.
3. **QueryEngine routing** — Candidate pool queries route through `QueryEngine.query_sql` (Iceberg catalog), not direct DuckDB access. `data/futureproof.duckdb` is empty.
4. **`tool_choice="required"`** — Forces Gemma to always return a structured tool call. Empty picks come back as `soc_codes: []` instead of prose.
5. **Program-negating crosswalk trigger** — Detects when crosswalk SOCs contradict the program name (e.g., "EXCEPT special education" for a Special Education major) and fires expansion even without explicit `intent_keywords`.

## Test Coverage

- **29 new tests** in `test_soc_expansion.py` covering pass-through, negation detection, synonym bridging, Gemma failure modes, candidate pool filtering, and the canonical pre-med/deaf-ed cases
- **5 new tests** in `test_gemma_client.py` covering tool-call parsing, fallback on no-tool-call, JSONL logging, transport errors, and unparseable arguments
- **Zero regressions** across all suites

## Verification Results

| Check | Result |
|-------|--------|
| Lint — pipeline (ruff) | PASS |
| Lint — backend (ruff) | PASS |
| Type check (mypy) | PASS (0 new errors) |
| Backend tests (pytest) | 1088 passed |
| Pipeline tests (pytest) | 1703 passed |
| TypeScript | PASS |
| Frontend tests (vitest) | 588 passed |
| Production build (Vite) | PASS |

## Code Review Findings (Resolved)

- **stats_available bug** — `_build_expanded_rows` was hardcoding `None` for ERN/ROI/loans-boss in the counter tuple, causing expanded SOCs to sort to the bottom. Fixed to inherit template values.
- **Empty SQL guard** — `_fetch_soc_titles` could produce `WHERE soc_code IN ()` when all SOCs fail regex validation. Added empty-list guard.

## Follow-ups

1. Promote `feature-gemma-tool-calling-migration.md` from placeholder to real spec, citing `generate_with_tools` as the reference implementation.
2. Manual verification with live Gemma (both Ollama and OpenRouter backends) pending.
3. Evaluate whether expanded SOCs need a visible "AI-expanded" label in the UI.
4. Consider caching `expand_socs` results if telemetry shows high repeat-call rates.
