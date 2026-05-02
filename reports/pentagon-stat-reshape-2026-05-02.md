# Pentagon Stat Reshape — Completion Report

**Date:** 2026-05-02
**Branch:** `aura-stat`
**Spec:** `docs/specs/pentagon-stat-reshape.md` (v1.2)
**Status:** COMPLETE — all reviews APPROVED, ready to merge

---

## What Shipped

The pentagon stays a pentagon. Five axes. Two of the axes change meaning:

1. **RES absorbs HMN.** The defensive AI score (former RES, sourced from `consumable.ai_exposure.stat_res`) and the offensive human-skill score (former HMN, sourced from `consumable.onet_work_profiles.hmn_score_rounded`) collapse into a single new RES axis that captures the full resilience spectrum — *"the work needs people AND AI can't do most of it."*
2. **AURA takes HMN's slot.** The freed-up axis is now AURA — institutional brand gravity, sourced from `consumable.institution_aura.aura_score`. AURA is institution-level: every career outcome under a single school+major build shares the same AURA value.

Final pentagon: **ERN, ROI, RES (blended), GRW, AURA.**

This is a backend + frontend reshape only. **No data pipeline changes.** The stat engine reads AURA via a new MCP tool (`get_institution_aura`) and computes blended RES in Python from the raw `stat_res` + `stat_hmn` already on each `consumable.program_career_paths` row.

## Scope

- 109 files changed: +1863 / -629 lines
- 8 legacy build JSON files deleted (Decision 9 — saved-build state reset; no migration code)
- 1 new MCP tool: `get_institution_aura`
- 1 new shared design token: `--color-stat-aura: #E8B86B` (amber-copper for institutional weight)

## Key Decisions Honored

| # | Decision | What It Means |
|---|----------|---------------|
| 2 | Blend lives in `stat_engine` (Python), not the pipeline | EDA-tuned weights are a single-function PR away — no re-promotion. |
| 4 (revised) | Fight AI scores from raw `stat_res + stat_hmn` via new `CareerOutcome.raw_stat_res`/`raw_stat_hmn` fields, not from blended `stats.res` | Bit-exact with pre-reshape behavior. The `2 × blended_RES` formula proposed in v1.0 would have silently flipped 89k+ outcomes via half-up rounding bias. Caught by @fp-data-reviewer empirical check on 4.77M rows. |
| 5 | `CareerBranch.delta_aura: int = 0` always | AURA is institution-level; branches stay at the same school by construction. Structurally guaranteed by `consumable.career_branches` having no unitid column. |
| 6 | One AURA MCP lookup per `compute_pentagon`, stamped on every CareerOutcome | CIP substitution doesn't change `unitid` so AURA stays invariant under substitution. |
| 7 | NULL `aura_score` renders as "—" with no caveat banner | Honors the standing memory `feedback_no_substitution_caveat.md`. Pentagon vertex draws as an open ring at the outer perimeter (not collapsed to center) so the missing slice reads as "no signal" not "scored zero." Affects ~10% of student-reachable unitids. |
| 9 | Saved builds reset (no legacy migration) | Deleted 8 legacy JSONs; DuckDB `builds` table drops + recreates on first startup with the new column shape. Eliminates the silent `delta_hmn` data-loss path that the v1.0 "drop on parse" plan would have introduced. |

## Pipeline Stayed Green

Per the must-stay-green rule:
- **2124 / 2124** pipeline tests pass (1 deselected, network-only)
- 0 transformer touches in `src/raw/`, `src/silver/`, `src/gold/`
- 0 schema migrations on `consumable.program_career_paths`
- The new `get_institution_aura` MCP tool is purely additive

## Verification Final State

| Check | Result |
|-------|--------|
| Backend ruff | ✅ All checks passed |
| Backend mypy | ⚠️ 69 pre-existing `[no-untyped-def]` errors, **0 introduced** by this spec |
| Backend pytest | ✅ **1337 / 1337** |
| Pipeline pytest | ✅ **2124 / 2124** (1 deselected — network-only) |
| Frontend tsc | ✅ clean |
| Frontend vitest | ✅ **774 / 774** |
| Vite production build | ✅ 1.62s · 1.15 MB JS · 81.93 kB CSS |

## Review Trail

| Agent | Round 1 | Round 2 | Round 3 |
|-------|---------|---------|---------|
| @fp-architect | CHANGES REQUESTED (5 conditions) | APPROVED — see v1.1 changelog | — |
| @fp-data-reviewer | CHANGES REQUESTED (4 items) | CHANGES REQUESTED (2 fixes — `_score_ai` partial-null & receipt comment) | APPROVED — see v1.2 changelog |
| @fp-design-visionary | Proposed amber `#E8B86B`, "Brand Gravity" copy, missing-data open-ring treatment | — | — |
| @fp-design-auditor | CHANGES REQUESTED (5 issues — PentagonChart polygon, Glow label, bossData color/copy, mockups) | CHANGES REQUESTED (5 mockup-only — Perl sweep over-reached on `--accent-empathy`) | APPROVED |
| @faang-staff-engineer | CHANGES REQUIRED (5 critical + 3 minor — MiniPentagon, StatBarRow, PentagonOverlay, CharacterCard, `_fetch_aura` exception handling, gitignore, WhatItTakes, `_score_ai` reason string) | APPROVED | — |
| @fp-builder | ALL PASSED | — | — |

Total review iterations: **3 design audit rounds, 2 code review rounds, 2 architecture rounds, 1 builder round.** Every CHANGES REQUESTED finding was addressed in a single remediation pass before re-review.

## What Was Surgically Right

The v1.0 spec proposed `_score_ai = 2 × blended_RES` to "preserve" the old `RES + HMN` thresholds. @fp-data-reviewer ran the empirical check against the 4.77M-row gold zone and found that half-up rounding inside `_blend_res` would silently flip **49.4% of both-present rows** one point higher — re-classifying ~89k outcomes from draw/lose to win/draw. v1.1 plumbed raw row inputs through `CareerOutcome.raw_stat_res` / `raw_stat_hmn` so Fight AI scores from the underlying integers. The blend stays a presentation-only transformation. Existing fixtures stay bit-exact. Without the data reviewer this would have shipped wrong.

The v1.1 `_score_ai` partial-null branch then doubled the surviving input (`raw_hmn × 2` when `raw_res IS NULL`), which would have silently flipped another ~1.05M rows. v1.2 caught this and replaced with `_safe_sum(raw_res, raw_hmn)` to match today's drop-Nones-and-sum semantics.

The v1.2 staff-engineer review caught that PentagonChart's open-ring missing-data treatment was implemented but four sibling components (MiniPentagon, StatBarRow, PentagonOverlay, CharacterCard) were not retrofit — meaning ~10% of menu thumbnails, build-results bars, compare overlays, and character cards would still render null AURA as "0" with empty bars. All four now share the same em-dash + hollow-track treatment.

## What's Deferred

Two explicit follow-ups flagged in §11 Open Items:

1. **Blended RES weights** — the 50/50 mean is a placeholder pending EDA. A follow-up spec (`stat-engine-blended-res-weights.md`) should run EDA on the joint distribution of `stat_res` × `stat_hmn` across `consumable.program_career_paths`, pick weights, and update `_blend_res` only — no other surface changes.
2. **AURA tutorial copy** — visionary's shipping copy is in place; @fp-copywriter pass would refine the in-app voice further.

Plus one design concern surfaced by @fp-data-reviewer that the visionary addressed but worth re-watching after launch: **AURA "—" coverage rate is ~10.4%** of student-reachable unitids (265 of 2,550). The open-ring + em-dash treatment + tutorial copy framing handle this honestly today, but if the rate creeps higher as the product expands its school universe, the design treatment may need a second look.

## Files Touched

See spec §6 Files Modified for the full table. Headline counts:
- **Backend models:** 2 files
- **Backend services:** 14 files
- **Backend templates:** 2 files (wrapped/_base.css, wrapped/frame-pentagon.html)
- **Frontend types:** 3 files
- **Frontend components:** 19 files
- **Frontend screens + mocks:** 6 files
- **Frontend i18n + tokens + Tailwind:** 4 files
- **Tests (backend + frontend + MCP):** 30+ files updated, 1 new file
- **Mockups:** 3 files
- **Saved-build state:** 8 files deleted
- **`.gitignore`:** +1 line (`data/builds/`)

## Ready to Merge

All §1 success criteria checked off. Spec status COMPLETE. All independent reviews APPROVED. The aura-stat branch is ready for human review and merge to main.
