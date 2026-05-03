# Feature Report: Explain-Stat Receipt — ROI, RES, GRW

**Spec:** `docs/specs/feature-explain-stat-receipt-roi-res-grw.md`
**Date:** 2026-05-02
**Status:** COMPLETE
**Branch:** `aura-stat`

## Summary

Extended the structured `ExplainStatReceipt` JSON-mode path (built for ERN) to ROI, RES, and GRW. The registry-based dispatch replaces the ERN-only sentinel match with a generic `_STAT_EXPLAIN_REGISTRY` keyed by stat code. Each stat has its own appendix template, label allowlist, postprocessor, and math-line renderer.

## Changes

| File | Change |
|------|--------|
| `backend/app/services/ask_gemma.py` | Registry pattern (`_StatExplainConfig` + `_STAT_EXPLAIN_REGISTRY`), 3 postprocessors, 3 math-line renderers, `_extract_res_raw_scores`, `_extract_grw_employment_change`, position-based label normalization for RES, generalized sentinel regex |
| `backend/app/models/api.py` | `AskStatTarget` literal extended with `"ROI" | "RES" | "GRW"` |
| `frontend/src/screens/BuildResultsScreen.tsx` | `handleExplainStat` generalized from ERN-only; gate expanded to `ern|roi|res|grw` |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | `isMissing` heuristic fixed to `missing_reason !== null`; React key made unique for RES 50/50 |
| `frontend/src/types/chat.ts` | `AskStatTarget` type extended |
| `docs/reference/stat-display-surfaces.md` | §1a and §1i updated for all four stats |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | 120 tests (was 36 before this spec) |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | +4 tests (ROI/GRW no-percentile, ROI missing_reason, RES 2-component) |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | +4 tests (ROI/RES/GRW link visible, AURA excluded) |

## Code Review Findings (Resolved)

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| S1 | Blocker | `_render_math_line_roi` division by zero when `earnings_1yr_median == 0` | Guard: treat zero same as None |
| S2 | Blocker | Frontend `isMissing` dims all non-ERN receipts (checks `value_pct === null || anchor_dollars === null`) | Changed to `missing_reason !== null` |
| S3 | Moderate | Score-null path only handled for ERN | Added log line + comment; by-design per spec Decision 10 |
| S4 | Moderate | Unused `soc_code` param in `_extract_res_raw_scores` | Removed |
| S5 | Moderate | RES `value_pct = raw * 10` unclamped | Clamped to [0, 100] |

## Verification

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | PASS |
| pytest | PASS (1476 tests) |
| TypeScript | PASS |
| vitest | PASS (53 receipt/build tests) |
| Vite build | PASS |

## Deferred

- Manual smoke test with Ollama/OpenRouter (same as ERN — deferred to human)
- Score-null server-built receipt for ROI/RES/GRW (currently degrades to markdown prose; ERN has the full path)
