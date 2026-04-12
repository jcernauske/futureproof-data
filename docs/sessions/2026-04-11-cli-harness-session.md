# Session: CLI Harness Implementation

**Session ID:** 2026-04-11-cli-harness
**Date:** 2026-04-11
**Agent:** Claude Code (general — no subagent delegation for implementation)
**Spec:** `docs/specs/cli-harness.md`
**Status:** IMPLEMENTATION COMPLETE

## Summary

Built the full FutureProof CLI harness — 8 service modules, Pydantic
models, interactive rich-formatted CLI, 59 hermetic unit tests. Validated
end-to-end against the real Iceberg catalog (IU-B Marketing →
Fundraisers → pentagon + boss gauntlet + 10 Stage 3 branches + build
round-trip).

## Artifacts

**New files:**
- `backend/app/models/career.py` — Pydantic contracts (API shape)
- `backend/app/services/__init__.py`
- `backend/app/services/mcp_client.py` — thin singleton over `FutureProofMCPServer`
- `backend/app/services/gemma_client.py` — unified OpenAI-compat client (Ollama + OpenRouter)
- `backend/app/services/school_lookup.py` — fuzzy search, program listing, 4-step major resolution
- `backend/app/services/stat_engine.py` — pentagon computation + effort adjustment
- `backend/app/services/boss_fights.py` — gauntlet logic + Gemma narratives
- `backend/app/services/branch_tree.py` — Stage 3 branches
- `backend/app/services/skill_recs.py` — Gemma skill recommendations + fallback
- `backend/app/services/guidance.py` — "Gemma's Take" narrative
- `backend/app/services/builds.py` — save/load/list/compare
- `backend/cli.py` — interactive rich CLI
- `backend/tests/services/` — 59 hermetic unit tests (7 test files)

**Modified:**
- `pyproject.toml` — added `openai`, `python-dotenv`, `rich`, `pyyaml`, `pytest-asyncio`, `mypy` to root venv
- `backend/pyproject.toml` — mirrored CLI deps so standalone backend install remains possible
- `backend/tests/conftest.py` — made fastapi import tolerant so `tests/services/` runs without fastapi in root venv
- `.gitignore` — added `backend/data/` and `backend/.venv/`
- `docs/specs/cli-harness.md` — set status to COMPLETE, documented implementation notes and deviations

## Key Decisions

1. **Data path via MCP server, not DuckDB.** CLAUDE.md references
   `data/futureproof.duckdb` but that file is empty. The real gold-zone
   data lives in `data/gold/iceberg_warehouse/consumable/*` tables
   referenced by `data/catalog/catalog.db`. `FutureProofMCPServer`
   reads them via PyIceberg and already implements CIP substitution,
   so the CLI is a thin wrapper around its `_handle_*` methods.

2. **Single unified venv.** The spec's `cd backend && python cli.py`
   invocation requires brightsmith/pyiceberg/pyyaml, which are only
   installed in the root venv. Rather than duplicate a second venv
   under `backend/`, we run via `uv run python backend/cli.py` from
   project root. `cli.py` adds `backend/` to `sys.path` on import so
   `app.*` resolves from either cwd.

3. **Gemma for narrative only.** Confirmed with Jeff: function calling
   agent loop is a separate future spec. CLI fetches data
   deterministically, assembles context, then hands Gemma the payload
   for 1-2 sentence boss narratives, skill recs, and the guidance
   block. Every Gemma call has a deterministic fallback so the CLI
   never crashes mid-session if Ollama isn't running.

4. **Effort slider.** Landed as a ±1 integer shift on ERN and ROI
   (`EFFORT_SHIFT` dict in `stat_engine`). Spec said "needs tuning
   during CLI testing" — constants are live-adjustable.

5. **Boss thresholds.** Landed as the spec's initial table. The
   `BOSS_SPECS` dict at the top of `boss_fights.py` is the single
   tuning surface for Jeff's kid testing session.

## Verification

- `uv run ruff check backend/app backend/cli.py backend/tests/services` → clean
- `uv run mypy backend/app backend/cli.py --config-file backend/pyproject.toml` → clean for all CLI code (4 pre-existing fastapi errors in `main.py`/`routers/health.py` unrelated to this spec)
- `uv run pytest backend/tests/services` → **59 passed in 0.5s**
- `uv run pytest -q` (full pipeline suite) → **1204 passed, 1 deselected** (zero regression)
- Live end-to-end: IU-B + "Marketing" → CIP 52.01 → 52.14 substitution → Fundraisers headline, ERN 8 / ROI 10 / RES 4 / GRW 6 / HMN 6, 3W/0L/2D gauntlet, 10 branches, build save+load round-trip ✅

## Known Issues

- `backend/.venv/` was accidentally created mid-session when I briefly
  ran `mypy` from the `backend/` working directory; `uv` auto-bootstrapped
  a second venv. It's gitignored now but the directory still exists
  locally. Safe to delete: `rm -rf backend/.venv`.
- `docs/specs/cli-harness.md` status line and headings have the new
  IMPLEMENTATION COMPLETE status + implementation notes appended; the
  body (spec content) is otherwise unchanged. When ready, move to
  `docs/specs/completed/`.

## Next

Hand the CLI to Jeff's kid. Watch over their shoulder. Tune thresholds
in `BOSS_SPECS` and `EFFORT_SHIFT` live. Then write the frontend spec
against the proven service layer.
