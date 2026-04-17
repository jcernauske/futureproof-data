# FutureProof — CLAUDE.md

## What This Is

FutureProof is an RPG-style career planning tool that shows students where a college degree actually leads — not just the first job, but the branching career paths that unfold over decades. Students pick a school and major, see their post-graduation character with five data-backed stats, fight boss battles representing real career threats, and explore a branching evolution tree of divergent career paths.

Powered by Gemma 4 via Ollama — any school can run it on their own hardware, forever, at zero cost.

**Hackathon:** Gemma 4 Good (Kaggle / Google DeepMind) — Deadline: May 18, 2026

Full product vision: `docs/futureproof_vision_roadmap.md`
Scoped PRD: `docs/futureproof_hackathon_prd.md`

This file is the source of truth for how Claude Code operates in this project.

## Monorepo Structure

This is a single repo containing both the **data pipeline** and the **web application**.

```
futureproof-data/
├── src/                    # Brightsmith data pipeline
│   ├── raw/                #   Bronze zone ingestors
│   ├── silver/             #   Silver zone transformers
│   ├── gold/               #   Gold zone transformers
│   └── mcp_server/         #   MCP server (Gemma-callable tools)
├── backend/                # FastAPI app + CLI
│   ├── app/                #   main.py, routers/, services/, models/
│   ├── cli.py              #   Interactive CLI harness (when built)
│   ├── pyproject.toml      #   Backend-specific dependencies
│   └── tests/              #   Backend tests (pytest)
├── frontend/               # React app
│   └── src/                #   components/, hooks/, lib/, styles/, types/
├── data/                   # Pipeline data (gitignored)
│   ├── bronze/             #   Raw ingested data
│   ├── silver/             #   Normalized data
│   ├── gold/               #   Consumable data products
│   ├── futureproof.duckdb  #   Gold zone DuckDB
│   └── reference/          #   YAML lookup tables (major_to_cip.yaml)
├── scripts/                # Spike scripts, one-off utilities
├── docs/
│   ├── specs/              #   ALL specs (pipeline + app + infra)
│   │   └── completed/
│   └── sessions/           #   Agent session logs
├── domain/                 # Brightsmith domain config
├── glossaries/             # Business glossary terms
├── governance/             # DQ rules, chaos manifests, data contracts
├── tests/                  # Pipeline tests (pytest)
│   ├── raw/
│   ├── silver/
│   ├── gold/
│   └── mcp/
├── .claude/agents/         # Agent definitions
├── .env                    # INFERENCE_BACKEND, OPENROUTER_API_KEY (gitignored)
└── CLAUDE.md               # You are here
```

## Framework

The data pipeline is built on [Brightsmith](https://github.com/jcernauske/brightsmith). For the full agent workflow, governance model, zone architecture, and pipeline conventions, see the Brightsmith CLAUDE.md at `/Users/jcernauske/code/bright/brightsmith/CLAUDE.md`.

## Stack

| Layer | Technology |
|-------|-----------|
| Data Pipeline | Brightsmith (Bronze → Silver → Gold → MCP zones) |
| Data Storage | DuckDB (Gold zone), Apache Iceberg |
| MCP Server | Python, exposes Gold-zone data as Gemma-callable tools |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| LLM | Gemma 4 via Ollama (local) or OpenRouter (cloud) |
| Web Frontend | React, Vite, TypeScript, Tailwind CSS, Framer Motion |
| Design | Brightpath design system — dark-first, plush, cinematic (see DESIGN.md) |
| Linting | ruff |
| Testing | pytest (pipeline + backend), vitest (frontend) |

## Data Sources

| Source | Status | Taxonomy |
|--------|--------|----------|
| College Scorecard (Field of Study) | COMPLETE | CIP codes |
| BLS Occupational Outlook Handbook | COMPLETE | SOC codes |
| O*NET Task-Level Data | COMPLETE | SOC codes |
| CIP-SOC Crosswalk | COMPLETE | CIP ↔ SOC |
| Karpathy AI Exposure Scores | COMPLETE | SOC codes |
| BEA Regional Price Parities | In Progress | FIPS codes |

## Gold Zone Tables

The backend and CLI read these from `data/futureproof.duckdb`:

```python
import duckdb
con = duckdb.connect("data/futureproof.duckdb", read_only=True)
```

| Table | Rows | Powers |
|-------|------|--------|
| `consumable.career_outcomes` | 69,947 | ERN, ROI, effort slider |
| `consumable.occupation_profiles` | 832 | GRW, Ceiling boss, Market boss |
| `consumable.onet_work_profiles` | 798 | HMN, Burnout boss |
| `consumable.career_transitions` | 15,944 | Stage 3 branching graph |
| `consumable.program_career_paths` | 626,406 | THE CORE TABLE — school+major→career with all stats/bosses |
| `consumable.career_branches` | 15,944 | Stage 3 branches with stat deltas |
| `consumable.ai_exposure` | 342 | RES stat, Fight AI boss |

Pipeline stats: 700K+ rows, 280+ DQ rules, 500+ tests, 7 data contracts, 80+ business terms, chaos monkey hardened.

## MCP Server

`src/mcp_server/futureproof_server.py` exposes Gold-zone data as tools:

| Tool | What It Does |
|------|-------------|
| `get_school_programs` | Fuzzy school search → list programs with earnings/debt |
| `get_career_paths` | Core query: school + major → career outcomes with 5-stat pentagon + boss scores |
| `get_occupation_data` | BLS occupation detail for a SOC code |
| `get_task_breakdown` | O*NET task-level profile for a SOC code |
| `get_career_branches` | Stage 3 branching paths from a SOC code |
| `get_ai_exposure` | Karpathy AI exposure score for a SOC code |
| `get_regional_price_parity` | BEA cost-of-living adjustment by state |
| `compare_purchasing_power` | Compare salary purchasing power between two states |

The backend services can import directly from `src/mcp_server/` — same repo, same venv.

## Inference Backend

Gemma 4 inference is configured via `.env` in the project root:

```bash
# .env (gitignored)
INFERENCE_BACKEND=ollama          # or "openrouter"
OPENROUTER_API_KEY=sk-or-v1-...   # only needed for openrouter backend
```

- **Ollama** (`localhost:11434`): Local inference for dev, testing, Ollama track video
- **OpenRouter** (`openrouter.ai/api/v1`): Cloud inference for live demo, model `google/gemma-4-26b-a4b-it`
- Both use OpenAI-compatible chat completions API — switching is a config change, not a code change
- See `docs/specs/cloud-gemma-deployment.md` for details

## Domain Standards

- **CIP** (Classification of Instructional Programs) — program taxonomy used by College Scorecard
- **SOC** (Standard Occupational Classification) — occupation taxonomy used by BLS/O*NET
- **CIP-SOC Crosswalk** — maps programs to occupations; critical for Silver zone integration
- **IPEDS** — institution identifiers used across all education data

## Visual Design

The design system is **Brightpath** — dark-first, plush/soft, cinematic. See `DESIGN.md` at the project root for the complete specification including all tokens, components, motion presets, and usage guidelines.

## Rules

- **Specs are the source of truth.** If it's not in the spec, it doesn't get built.
- **No schema changes without a spec.** Iceberg table creation, schema evolution, and pipeline interface changes require a spec.
- **Type hints everywhere.** Every public function and class gets type hints. No `Any` unless genuinely unavoidable.
- **Pydantic v2 for data models.** Use `BaseModel` for anything that crosses module boundaries.
- **REQUIRE_HUMAN_APPROVAL:** true (for governance-reviewer and staff-engineer gates)
- All "PrivacySuppressed" values in College Scorecard data must be converted to null
- CIPCODE must always be treated as string type (XX.XXXX format), never float
- Large CSV files must be read in chunks (50,000 rows recommended)

## Key Commands

```bash
# Pipeline
uv sync                            # Install pipeline deps
uv run pytest                      # Run pipeline tests (skips network)
uv run pytest -m network           # Include network tests
uv run ruff check src/ tests/      # Lint pipeline code

# Backend
cd backend && pip install -e ".[dev]"  # Install backend deps
cd backend && pytest               # Run backend tests
cd backend && ruff check .         # Lint backend
cd backend && mypy app/            # Type check backend

# Frontend
cd frontend && npm install         # Install frontend deps
cd frontend && npx vitest run      # Run frontend tests
cd frontend && npx tsc --noEmit    # Type check frontend

# CLI (when built)
cd backend && python cli.py        # Interactive CLI harness
```

## Specs

Each spec's status is tracked in the spec file itself. Completed specs move to `docs/specs/completed/`. Do not maintain a status list here — it drifts.

---

## Spec-Driven Workflow

All feature and bugfix work follows the spec-driven workflow. Specs live in `docs/specs/` and are the single source of truth for what gets built.

### Reading a Spec

When given a spec file to execute:

1. **Read the entire spec first** — especially the Claude Code Prompt at the top
2. **Follow the workflow exactly** — the prompt defines the sequence of agents and handoffs
3. **Write to the designated sections** — each agent has specific sections to fill in
4. **Respect the escalation rules:**
   - Minor: Fix and continue, document in §6
   - Significant: STOP, alert human
   - Blocker: STOP, set status BLOCKED, alert human

### Agent Pipeline

| Step | Agent | Role |
|------|-------|------|
| Architecture Review | `@fp-architect` | System architecture: data flow, Brightsmith integration, Gemma function calling, API contracts |
| Design Vision | `@fp-design-visionary` | Proposes the premium version of each screen. Owns Brightpath aesthetic. |
| Data Review | `@fp-data-reviewer` | Pipeline quality: ingestor output, CIP → SOC crosswalk, stat formulas, boss fight data |
| Implementation | Claude Code (general) | Writes the code |
| Testing | `@test-writer` | pytest (backend/pipeline) + vitest (frontend) |
| Design Audit | `@fp-design-auditor` | Mechanical token/pattern compliance against Brightpath design system (DESIGN.md) |
| Code Review | `@faang-staff-engineer` | Security, performance, error handling, architecture |
| Verification | `@fp-builder` | ruff + mypy + pytest + TypeScript + vitest + Vite build |

### Agent Delegation Rules

**CRITICAL: When a spec requests a specific agent, you MUST delegate to that agent. Do not do the work yourself.**

### Build Accountability

- If your changes break the build, YOU fix it (max 3 attempts)
- After 3 failed attempts: escalate to human, set status BLOCKED

### Test Suite Integrity

**Every test failure is a big deal. Never silently dismiss one.**

After your changes, run the full test suite. If ANY test fails:

1. **Name the failing test(s)** explicitly
2. **Determine causation** — did your changes cause it?
3. **If your changes caused it:** fix it before marking the spec complete
4. **If genuinely pre-existing:** document clearly, flag for human review
5. **Never mark a spec COMPLETE** without acknowledging every failure

**Prohibited:** Silently disabling tests, placeholder assertions, deleting tests, saying "pre-existing" without evidence.

## Session Logging

Every agent session must log to `docs/sessions/` with:
- Session ID and timestamp
- Agent name and spec being worked
- Actions taken and artifacts produced
- Decisions made and rationale

## Preferences

- **Format:** Markdown only. Never create Word/docx files unless explicitly requested.
- All specs live in `docs/specs/`. Completed specs move to `docs/specs/completed/`.
