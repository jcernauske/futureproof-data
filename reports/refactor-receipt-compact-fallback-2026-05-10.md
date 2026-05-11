# Refactor: Deterministic Receipts for Compact Models

**Spec:** `docs/specs/refactor-receipt-compact-fallback.md`
**Date:** 2026-05-10
**Status:** COMPLETE

## Summary

On compact local models (Gemma e4b/e2b via Ollama), explain-this-stat receipts are now built deterministically by calling MCP tools server-side and templating the prose fields. No Gemma call is made. Wall-clock time drops from 10-30s to <1s.

The 26B model and OpenRouter paths are completely unchanged.

## What Changed

### `backend/app/services/ask_gemma.py`
- Added `_build_deterministic_receipt()` dispatcher + 5 per-stat builders (ERN, ROI, RES, GRW, AURA)
- Added `_dispatch_grw_explain_tools()` and `_dispatch_aura_explain_tools()` for server-side MCP dispatch
- Added intercept at both `chat_ask` and `chat_ask_stream` — fires when `runtime_profile().ask_skip_tool_calling == True`
- All 5 builders handle null scores gracefully with `missing_reason` fields

### `backend/tests/services/test_ask_gemma_explain_receipt.py`
- 23 new tests covering all 5 stats: valid schema, score from build, math_line format, null inputs, null scores, data interpolation, source parity, evidence bullets, score provenance, logging

### `backend/tests/services/test_gemma_client.py`
- 2 new tests: `compact_local` has `ask_skip_tool_calling=True`, `full` has `False`

### `backend/tests/services/test_ask_gemma_explain_integration.py`
- 6 tests updated with `_FULL_PROFILE` monkeypatch (authorized modification per spec §4)

## Review Pipeline

| Step | Agent | Verdict |
|------|-------|---------|
| Architecture Review | @fp-architect | CHANGES REQUESTED (C1: streaming bypass, C2: null-score guards) — both addressed |
| GenAI Review | @genai-architect | No blockers, 4 required fixes — all addressed |
| Code Review | @faang-staff-engineer | CHANGES REQUIRED (S1: div-by-zero on ROI, M1: hardcoded backend) — both fixed |
| Build Verification | @fp-builder | ALL PASSED |

## Test Results

| Suite | Pass | Fail | Skip |
|-------|------|------|------|
| pytest (backend) | 1879 | 1 (pre-existing) | 19 |
| vitest (frontend) | 890 | 3 (pre-existing) | 0 |

## Success Criteria

All 8 criteria met:
- [x] ERN deterministic receipt on compact_local
- [x] ROI/RES/GRW/AURA deterministic receipts on compact_local
- [x] Identical ExplainStatReceipt schema
- [x] Data-driven explainer prose with student-specific data
- [x] Full tier path unchanged
- [x] Logging with `_deterministic` call_site suffix
- [x] All existing tests pass (except authorized modifications)
- [x] Wall-clock time <1s on compact_local
