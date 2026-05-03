# Feature Report: Explain-Stat Receipt — AURA

**Date:** 2026-05-03
**Spec:** `docs/specs/feature-explain-stat-receipt-aura.md`
**Status:** COMPLETE
**Branch:** `aura-stat`

## Summary

AURA is now the fifth and final explain-stat receipt dispatch, completing the full pentagon. Clicking "Explain this to me" on the AURA stat row fires `[explain-this:AURA]`, dispatches via the registry, and renders a structured receipt with a purple rail, one institution-level component, server-stamped evidence bullets showing actual per-student dollar values, a continuous-score math line, a 5-tier scoring scale, and a basis byline (e.g., "based on endowment + marketing + athletics").

## What Changed

### Schema (additive, non-breaking)
- `ExplainStatReceipt` gained `score_provenance: str | None = Field(default=None, max_length=200)` with a sentinel-passthrough validator that handles None gracefully. ERN/ROI/RES/GRW emit `score_provenance: null`; the renderer suppresses the byline.

### Backend
- `_postprocess_aura_explain_receipt` follows the 10-step pipeline established by ERN. Server-stamps: score, score_provenance (from `_humanize_basis`), math_line (continuous score form), scoring_scale (5 tiers), evidence_bullets (actual per-student values from the `get_institution_aura` tool call).
- `get_institution_aura` added to `_TOOLS` for chat-time availability.
- Registry widened from 4 to 5 entries.

### Frontend
- Zod schema gained `score_provenance: z.string().max(200).nullable().optional()`.
- `ExplainStatReceiptCard` renders an italic byline "based on {score_provenance}" below the one-liner when populated.
- `BuildResultsScreen` explain trigger includes AURA, gated on `stats.aura != null`.

### Documentation
- `stat-display-surfaces.md` updated: §1a, §1b (AURA wired), §1g (explain-this affordance wired for non-null AURA), §1i (new AURA entry with full visual spec).

## Test Coverage

| Suite | New Tests | Total Pass |
|-------|-----------|------------|
| Backend (pytest) | 28 | 158/158 receipt tests |
| Frontend receipt (vitest) | 4 | 25/25 |
| Frontend Zod (vitest) | 8 | 8/8 |
| Frontend BuildResultsScreen | 2 (replaced 1) | 7/7 explain tests |

## Pipeline Steps

| Step | Agent | Verdict |
|------|-------|---------|
| Architecture Review | @fp-architect | APPROVED |
| Implementation | Claude Code | COMPLETE |
| Testing | @test-writer | 34 new tests, all passing |
| Code Review | @faang-staff-engineer | APPROVED (1 moderate fix applied) |
| Verification | @fp-builder | ALL PASSED |

## Deviations from Spec

1. `get_institution_aura` was not already in `_TOOLS` — added it.
2. `CareerOutcome.school_name` → `institution_name` (spec pseudo-code was wrong).
3. Added `isinstance(value, (int, float))` type guard on evidence bullet values (code review M1).

## Serialization Decision

**always-emit-null** — `score_provenance: null` appears in ERN/ROI/RES/GRW wire payloads. `exclude_none=True` would break semantically meaningful nulls on other fields. The ~30 bytes per receipt is negligible.

## Remaining

- Manual smoke verification on both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` (deferred to human, same as ERN/ROI/RES/GRW).
