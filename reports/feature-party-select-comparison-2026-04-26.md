# Feature: Party Select — Build Comparison Redesign

**Spec:** `docs/specs/feature-party-select-comparison.md`
**Status:** COMPLETE
**Date:** 2026-04-26
**Branch:** `dead-code-prune`

## Summary

Redesigned the CompareView into a JRPG-style "Party Select" screen. Students can now compare 2-4 builds side by side with character cards, a stat pentagon overlay, boss battle grid with skill-assisted badges, salary/cost/debt breakdowns, branch previews with convergence detection, and two independent Gemma-generated insights (money analysis + tradeoff summary).

## What Changed

### Backend
- `compare_builds()` expanded: returns soc_code, profile_name, animal_emoji, school_name, major_text, effort, loan_pct, median_annual_wage, net_price_annual, modeled_total_debt per build; boss_id, skill_counts, original_values per boss row; branches with top-3 destinations
- New `POST /builds/compare-insights` endpoint firing two parallel Gemma calls via `asyncio.gather(return_exceptions=True)`
- Two new Gemma functions: `generate_money_insight_async()` and `generate_compare_summary_async()` with comparison-type detection (same school / same career / different)
- `CompareRequest` validated: `Field(min_length=2, max_length=4)`

### Frontend
- New components: `CharacterCard`, `MoneySection`, `BranchPreview`
- Redesigned: `CompareView` (Party Select layout), `RiskHeadlineCard` (skill badges + grid)
- Updated: `PentagonOverlay` (4th color), `MenuScreen` (cap raised to 4)
- Parallel API calls: data renders immediately, Gemma insights arrive async

## Agent Pipeline Results

| Step | Agent | Verdict |
|------|-------|---------|
| Architecture | @fp-architect | CHANGES REQUESTED → fixed (router placement, Pydantic validation) |
| Design Vision | @fp-design-visionary | Wrote §3 |
| GenAI Review | @genai-architect | APPROVED with 2 required changes (forbidden words) → fixed |
| Testing | @test-writer | Added 2 frontend + 6 backend tests |
| Design Audit | @fp-design-auditor | CHANGES REQUESTED → 5/6 blocking fixed, #1 deferred (testid pattern consistent) |
| Code Review | @faang-staff-engineer | CHANGES REQUESTED → all 3 fixed |
| Verification | @fp-builder | ALL PASSED |

## Test Results

| Suite | Pass | Fail | Total |
|-------|------|------|-------|
| pytest | 1128 | 0 | 1128 |
| vitest | 648 | 0 | 648 |

## Review Fixes Applied

1. `asyncio.gather` with `return_exceptions=True` — independent Gemma task failure
2. Consolidated useEffect IIFEs — gate insights on data success, log failures
3. "Highest Salary" badge — skip when all wages identical (`uniqueWages.size > 1`)
4. Skill badge `aria-label` added
5. Pentagon vertex labels: inline Fredoka font at 14px (SVG text)
6. Gemma insight surface: `bg-accent-insight/[0.06]`
7. `border-border-default` → `border-border` (Tailwind config fix)
8. Divider dots: `bg-bp-raised` → `bg-bp-surface`

## Follow-up Items

1. Non-blocking design audit cleanup (#7-15): type-scale tokens, avatar radius, pentagon dot styling
2. Integration test for `POST /builds/compare-insights`
3. `CompareRequest` max_length=4 rejection test
4. Gemma prompt polish: relabel WIN/LOSE/DRAW to plain-language in user prompts
