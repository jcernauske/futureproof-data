# FutureProof Data — CLAUDE.md

## Project

- **Name:** futureproof-data
- **Domain:** Education / Career Guidance
- **Description:** Maps school + major to career outcomes and AI exposure analysis using the Brightsmith data pipeline framework.
- **Contact:** jeff@hyenastudios.com

## Framework

This project is built on [Brightsmith](https://github.com/jcernauske/brightsmith). For the full agent workflow, governance model, zone architecture, and pipeline conventions, see the Brightsmith CLAUDE.md at `/Users/jcernauske/code/bright/brightsmith/CLAUDE.md`.

## Data Sources

| Source | Zone | Status | Taxonomy |
|--------|------|--------|----------|
| College Scorecard (Field of Study) | Raw | Scaffolded | CIP codes |
| BLS Occupational Outlook Handbook | Raw | Spec Draft | SOC codes |
| O*NET Task-Level Data | Raw | Planned | SOC codes |

## Domain Standards

- **CIP** (Classification of Instructional Programs) — program taxonomy used by College Scorecard
- **SOC** (Standard Occupational Classification) — occupation taxonomy used by BLS/O*NET
- **CIP-SOC Crosswalk** — maps programs to occupations; critical for Silver zone integration
- **IPEDS** — institution identifiers used across all education data

## Cross-Source Integration

The core analytical challenge: College Scorecard uses CIP codes (programs), while BLS and O*NET use SOC codes (occupations). The CIP-to-SOC crosswalk (maintained by NCES/BLS) bridges these in the Silver zone via ConceptNormalizer. This enables FutureProof's central question: "If I study X at school Y, what career outcomes can I expect, and how exposed are those careers to AI?"

## Key Commands

```bash
# Install dependencies
uv sync

# Run tests (skips network tests)
uv run pytest

# Run tests including network tests
uv run pytest -m network

# Lint
uv run ruff check src/ tests/
```

## Preferences

- **REQUIRE_HUMAN_APPROVAL:** true (for governance-reviewer and staff-engineer gates)
- All "PrivacySuppressed" values in College Scorecard data must be converted to null
- CIPCODE must always be treated as string type (XX.XXXX format), never float
- Large CSV files must be read in chunks (50,000 rows recommended)

## Session Logging

Every agent session must log to `docs/sessions/` with:
- Session ID and timestamp
- Agent name and spec being worked
- Actions taken and artifacts produced
- Decisions made and rationale

## Specs

| Spec | Zone | Status |
|------|------|--------|
| raw-ingest-college-scorecard | Raw | COMPLETE |
| silver-base-college-scorecard | Silver | COMPLETE |
| raw-ingest-bls-ooh | Raw | COMPLETE |
| silver-base-bls-ooh | Silver | COMPLETE |
| silver-base-onet | Silver | COMPLETE |
| crosswalk-cip-soc | Bronze + Silver | COMPLETE |
| gold-career-outcomes-college-scorecard | Gold | DRAFT |
| gold-occupation-profiles-bls-ooh | Gold | COMPLETE |
