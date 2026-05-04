# Feature: Compare Screen Redesign — Completion Report

**Spec:** `docs/specs/feature-compare-screen-redesign.md`
**Status:** COMPLETE
**Date:** 2026-05-03

## Summary

Redesigned the Compare Screen with enhanced scroll layout, collapsible accordion sections for cost and institutional data, promoted CompareWinners grid, and salary range visualization.

## Changes

### Backend (1 file modified)

- `backend/app/services/builds.py` — Added `_fetch_institution_profiles()` helper that queries MCP `get_institution_aura` and Iceberg `consumable.ipeds_finance_profile` per unique unitid with caching. Expanded `compare_builds()` return dict with 17 new nullable fields (10 from CareerOutcome, 7 from institution profiles).

### Frontend (5 files modified, 3 files created)

- **CompareAccordion.tsx** (NEW) — Reusable collapsible disclosure with Framer Motion spring animation
- **CompareCostBreakdown.tsx** (NEW) — Sticker vs net price comparison bars + 6-row cost line-item table with desktop grid and mobile card layouts
- **CompareSchoolProfile.tsx** (NEW) — Institution identity cards + AURA breakdown table with inline bar visualizations and coverage tier pills
- **MoneySection.tsx** (MODIFIED) — p25/p75 salary range bars with shared horizontal scale; falls back to median-only when range data absent
- **CompareView.tsx** (MODIFIED) — Layout reorder: CompareWinners promoted to position 3, removed from Gemma section; Cost Breakdown + School Profile accordions added between Salary and Career Branches
- **menu.ts** (MODIFIED) — `CompareBuild` interface expanded with 17 new fields
- **mockMenu.ts** (MODIFIED) — Mock data expanded with realistic cost/institution values
- **CompareView.test.tsx** + **PentagonOverlay.test.tsx** (MODIFIED) — Test mocks updated for new fields

## Test Coverage

| Suite | New Tests | Total Pass | Pre-existing Failures |
|-------|-----------|------------|----------------------|
| pytest | 4 | 1517 | 4 (stat_engine, boss_fights, ask_gemma) |
| vitest | 8 | 813 | 10 (FinancesCard) |

## Build Verification

| Check | Result |
|-------|--------|
| ruff | PASS |
| mypy | PASS (2 pre-existing) |
| pytest | PASS (4 pre-existing failures) |
| TypeScript | PASS |
| vitest | PASS (10 pre-existing failures) |
| Vite build | PASS |

## Reviews

| Agent | Verdict |
|-------|---------|
| @fp-architect | CHANGES REQUESTED → resolved (3 conditions fixed in spec) |
| @fp-design-visionary | §3 complete |
| @design-builder | PASS |
| @faang-staff-engineer | APPROVED (2 findings fixed: division-by-zero guard, Iceberg error logging) |

## Code Review Fixes Applied

1. **SalaryBar division-by-zero** — When all builds share identical salary data, `scaleMax - scaleMin` = 0. Fixed with `|| 1` guard.
2. **Silent Iceberg error** — `query_iceberg_simple` returns `[{"error": "..."}]` instead of raising. Added explicit `"error"` key check with logging.
