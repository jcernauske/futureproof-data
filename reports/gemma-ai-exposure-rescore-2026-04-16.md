# gemma-ai-exposure-rescore (S1) — Completion Report

**Date:** 2026-04-16
**Spec:** `docs/specs/gemma-ai-exposure-rescore-v4.md`
**Status:** COMPLETE
**Estimated effort:** 9–14 hours
**Actual effort (code scaffolding):** ~6 hours across spec iteration + implementation

## Outcome

Code scaffolding for the Gemma 4 AI exposure re-scoring pipeline is complete, reviewed, and verified. The system blends Gemma 4 task-level scores (~798 O*NET occupations) with Karpathy's prior-art Gemini Flash scores (~342 occupations) into `consumable.ai_exposure`, with Gemma preferred and Karpathy as fallback. All 14 columns of the new Gold schema are wired through Bronze, Silver, the Gold blender, the MCP server, the backend Pydantic model, and the receipts surface. Eight A/B validation gates are in place with fail-closed enforcement at promote time.

The 798-row Ollama batch run itself is operator-initiated (~1–2 hours of compute) — see "Operator action required" below.

## Spec lifecycle

| Stage | Verdict | Notes |
|-------|---------|-------|
| Spec v1 → v2 | CHANGES REQUESTED ×2 | Initial drafts had file-naming, schema, and formula divergences from shipped code |
| Spec v3 | CHANGES REQUESTED | 13 residuals: model tag, gitignored cache path, missing schema fields, etc. — all documented at v3 deprecation banner |
| Spec v4 architecture review | APPROVED | "Ship it." All 13 v3 residuals patched. |
| Spec v4 data review | APPROVED | "Stop iterating the spec." 5/8 gates plus distribution coverage in DQ rules. |
| Implementation | DONE | 17 files created, 7 modified. 88 new tests. |
| Stage 4 code review | CHANGES REQUIRED | 6 items: category vocabulary, Pydantic Literal, rationale length, A/B gate enforcement, sys.path mutation, bool guard |
| Stage 4 fix re-review | APPROVED | All 6 fixes verified. +12 tests for new behaviors. |
| Stage 5 verification | PASS | Zero v4-introduced regressions. Pipeline 1432/1434 (2 pre-existing failures unrelated). Backend 280/280. |

## What shipped

### Pipeline modules

| File | Description |
|------|-------------|
| `src/raw/gemma_ai_exposure_ingestor.py` | Bronze ingestor reading `governance/fixtures/gemma-ai-exposure-scores.json`. 15-column schema preserves error rows for audit. |
| `src/silver/gemma_ai_exposure_transformer.py` | SOC normalization, error-row drop, dedup, O*NET join validation, `gae-` record_id stamping. |
| `src/gold/ai_exposure_transformer.py` (modified) | 14-column schema, `derive_category()` SOC major-group mapping (Karpathy vocabulary, includes `55: military`), `blend_scores()` with all 4 cells of the truth table, `_check_ab_gate()` fail-closed enforcement, `_gemma_has_score()` with explicit bool guard. |
| `scripts/gemma_ai_exposure_scorer.py` | Resumable Ollama batch scorer. HTTP API directly via `requests` (no new dep). Deterministic (`temperature=0, seed=42, format=json`), 3-retry loop with backoff, JSON-string field decode in prompt assembly, checkpoint at `governance/fixtures/`, rationale length 50–800 chars enforced. |
| `reports/gemma_vs_karpathy_comparison.py` | 8-gate A/B validation (correlation, MAD, signed delta, category bias with small-N guard, mode collapse, std dev floor, bucket coverage, outlier list with Δ≥4 table + rationale diff for top 10). Pure-Python Pearson (no scipy). Markdown + JSON output. |

### MCP + backend

| File | Description |
|------|-------------|
| `src/mcp_server/futureproof_server.py` | `_JSON_STRUCT_FIELDS` extended for `task_breakdown_*`; `AI_EXPOSURE_RESPONSE_FIELDS` extended with 5 new fields; `get_ai_exposure` tool description rewritten for blended provenance; handler decodes JSON struct fields. |
| `backend/app/models/career.py` | `ScoringModel = Literal["gemma-4", "gemini-flash"]` type alias; `CareerOutcome` gains `scoring_model`, `model_tag`, `karpathy_score`, `task_breakdown_*` fields. |
| `backend/app/services/receipts.py` | RES receipt branches on `scoring_model` — Gemma rows surface "AI-estimated" tag + model_tag; Karpathy rows keep legacy wording. |

### Governance

| File | Description |
|------|-------------|
| `governance/dq-rules/raw-gemma-ai-exposure.json` | 5 Bronze DQ rules — row count ≥780, error rate ≤3%, single-model-tag-per-batch, no duplicate SOCs, rationale length 50–800. |
| `governance/dq-rules/silver-base-gemma-ai-exposure.json` | 8 Silver rules — SOC format, range, mode-collapse ≤40%, JSON validity, referential integrity to O*NET, bucket coverage ≥10% per bucket, std dev ≥1.5, no duplicate normalized SOCs. |
| `governance/dq-rules/gold-ai-exposure.json` (modified) | Added GLD-AIE-016..019 — blended row count band, scoring_model enum, no Unknown category, model_tag for Gemma rows. |
| `governance/data-contracts/raw-gemma-ai-exposure.yaml` | Bronze contract for Gemma 4 scores. |
| `governance/data-contracts/base-gemma-ai-exposure.yaml` | Silver contract; documents distribution thresholds. |
| `governance/data-contracts/consumable-ai-exposure.yaml` (modified) | Appended 5 v4 columns; updated lineage to reference both Silver inputs; volume band split into `karpathy_only` and `v4_blended`. |
| `governance/data-contracts/mcp-ai-exposure.yaml` (modified) | Appended 5 v4 response fields. |

### Test coverage

| File | Tests | Focus |
|------|-------|-------|
| `tests/raw/test_gemma_ai_exposure_ingestor.py` | 5 | Fixture load, error-row preservation, schema shape |
| `tests/raw/test_gemma_ai_exposure_scorer.py` | 19 | Prompt assembly (no JSON double-encoding), structural validation incl. 50–800 char rationale bounds, deterministic config, 3-retry loop, error rows, checkpoint round-trip + corruption recovery |
| `tests/silver/test_gemma_ai_exposure_transformer.py` | 12 | SOC normalization edge cases, error-row drop, dedup, join_valid, record_id, model_tag preservation |
| `tests/gold/test_ai_exposure_blending.py` | 37 | Full 4-cell truth table, union coverage, record_id+promoted_at stamping, derive_category for all 23 SOC major groups, stat_res/boss_ai_score parametrized formulas, inverse invariant, **bool guard in `_gemma_has_score`**, **6 A/B gate enforcement tests** |
| `tests/gold/test_ab_validation.py` | 23 | Each of 8 gates exercised pass + fail; small-N category guard; outlier list; markdown report; fail-policy text |
| `tests/gold/test_ai_exposure_transformer.py` (modified) | 33 | Schema asserts 14 fields with original 9 required + scoring_model required + 4 nullable; Karpathy-only path stamps gemini-flash provenance |
| `tests/mcp/test_get_ai_exposure.py` (modified) | 13 | SAMPLE_ROW extended with v4 fields |
| `backend/tests/services/test_receipts_scoring_model.py` | 4 | RES wording branching by scoring_model; missing/None safe defaults |

**Totals:** 142 v4 pipeline tests, all passing. Full pipeline: 1432/1434 (2 pre-existing failures unrelated to v4). Backend: 280/280.

## Operator action required

The pipeline scaffolding is complete and verified, but the v4 system requires three operator-initiated steps to go end-to-end live:

1. **Run the batch scorer** — requires local Ollama with `gemma4:26b-a4b` pulled (~16GB RAM). Estimated 1–2 hours; resumable.
   ```bash
   uv run python scripts/gemma_ai_exposure_scorer.py
   ```
2. **Promote Bronze → Silver → Gold** (in this order — engine reads ai_exposure):
   ```bash
   uv run python -m raw.gemma_ai_exposure_ingestor
   uv run python -m silver.gemma_ai_exposure_transformer
   uv run python -m gold.ai_exposure_transformer
   uv run python -m gold.futureproof_engine
   ```
3. **Generate the A/B report and review the 8 gates**:
   ```bash
   uv run python reports/gemma_vs_karpathy_comparison.py
   ```
   If `overall_pass=False`, the Gold transformer's `_check_ab_gate()` will refuse to promote unless `AI_EXPOSURE_AB_OVERRIDE=1` is set with documented rationale in spec §6.

## Documented deviations from spec (already in §6)

1. Used Ollama HTTP API directly via `requests` instead of the `ollama` Python package (no new dep; identical config sent: temperature=0, seed=42, format=json, model `gemma4:26b-a4b`).
2. A/B Pearson computed in pure Python (no scipy dependency).
3. Karpathy-only fallback path retained in Gold `transform()` so the pentagon doesn't break before the Gemma batch is run; activates automatically once `base.gemma_ai_exposure` exists.

## Hackathon story

> "We used Karpathy's open-source AI exposure scores as our starting point — 342 occupations scored by Gemini Flash reading BLS job descriptions. Then we used Gemma 4 to re-score every occupation using task-level O*NET data from our governed pipeline. Gemma evaluates which specific tasks are automatable vs. human-essential — not just the job description, but the actual work. Coverage doubled from 342 to ~840 occupations. Here's how Gemma's scores compare to Karpathy's."

A/B report shape (`reports/gemma_vs_karpathy_comparison.md`) is ready for the writeup. Live numbers populate after the batch run.

## Files changed

- 17 created (5 source modules + 5 test files + 4 governance files + 3 contract YAMLs)
- 7 modified (Gold transformer, MCP server, backend career model, backend receipts, gold DQ rules, 2 contract YAMLs)
- 0 unrelated regressions (verified via baseline `git stash` comparison)
