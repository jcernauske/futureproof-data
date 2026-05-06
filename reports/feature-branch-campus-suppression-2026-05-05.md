# Report: feature-branch-campus-suppression

**Spec:** `docs/specs/feature-branch-campus-suppression.md`
**Status:** COMPLETE
**Date:** 2026-05-05
**Author:** Jeff Cernauske + Claude Code (orchestration), with @fp-architect, @fp-data-reviewer, @test-writer, @fp-design-auditor, @faang-staff-engineer, @fp-builder agents.

---

## TL;DR

Multi-campus university systems (Ohio U, UConn, Pittsburgh, Strayer, DeVry, etc.) report identical earnings per branch in the College Scorecard field-of-study file. Combined with branches' lower published costs, this artificially elevated their ROI and produced rankings where regional commuter campuses dominated the top of leaderboards over genuinely well-regarded programs.

This spec adds a **UI-layer suppression** of branch campuses on the schools-for-career leaderboard plus a **"Campuses" column** that surfaces the family size as the educational signal. Gold stays the source of truth, direct school search and the build flow are unchanged. A student who deliberately searches for a branch campus still gets a normal build experience.

**Scale shipped:** 38 institution families, 184 suppressed branch UNITIDs.

---

## What changed

### Pipeline (new, kept permanently)
- `scripts/detect_branch_campuses.py` — discovery script that groups Gold `consumable.career_outcomes` by ampersand-normalized name prefix, identifies flagships via known-suffix list / "main" keyword / most-CIPs-then-highest-earnings, and flags branches whose ≥80% of overlapping CIPs share the flagship's per-CIP earnings within $1.00. Emits `low_overlap_warning` when fewer than 10 CIPs overlap.

### Backend
- `backend/app/config/branch_campuses.py` (new) — frozen config with `INSTITUTION_FAMILIES` (38 flagships → branch lists), `SUPPRESSED_BRANCH_UNITIDS` (frozenset of 184 UNITIDs), `FAMILY_SIZE_BY_FLAGSHIP_UNITID`. Import-time `_validate_int` raises `TypeError` (survives `python -O`) and rejects `bool` explicitly.
- `src/mcp_server/futureproof_server.py` — schools-for-career SQL gets `WHERE unitid NOT IN (...)` (only when set non-empty) and `CASE unitid WHEN <flagship> THEN <size> ... ELSE 1 END AS family_size`. Belt-and-suspenders `int()` casts at every interpolation point. Both HTTP and MCP wire whitelists carry `family_size`.
- `backend/app/models/career.py` — `SchoolForCareerRow.family_size: int = 1` (additive default; Pydantic-backward-compatible).

### Frontend
- `frontend/src/types/build.ts` — `family_size: number` on `SchoolForCareerRow`.
- `frontend/src/components/CompareSchoolsPanel.tsx` — desktop grid 7→8 columns with a new `font-data text-text-primary` cell between STATE and ERN; mobile card carries a "Campuses: N" line under the program name.
- `frontend/src/i18n/strings.ts` — `compareSchools.column.campuses` in en/es/ar.

### Tests
- 5 new backend tests on the frozen config invariants (P0 + P1).
- 3 new frontend tests on the desktop cell + mobile card label rendering (P1).

---

## Manual sanity check (Accounting → Accountants)

Re-ran the failing leaderboard query: Accounting and Related Services (CIP `52.03`) → Accountants and auditors (SOC `13-2011`), high+medium confidence floor, top 12. The dominant artifact at this filter level was the **University of Connecticut** branch campuses (Waterbury, Avery Point, Hartford) — three branch rows in the top 12 sharing the flagship's $65,893 earnings against their own much-cheaper published costs ($35K–$53K).

**After:** Three UConn branch campuses gone. Single UConn flagship row at #10 with `Campuses: 5` and the honest flagship sticker ($91,544). University of Illinois Urbana-Champaign and University of Southern California — both genuinely top-tier accounting programs — surfaced naturally at #11 and #12.

Full BEFORE/AFTER tables in spec §9.

---

## Design + code review verdicts

| Reviewer | Verdict | Notes |
|----------|---------|-------|
| @fp-architect | APPROVED | Zone discipline holds; contract is additive; abs_rank semantics correct. Three minor non-blocking suggestions (all addressed). |
| @fp-data-reviewer | CHANGES REQUESTED → resolved | 8 algorithmic refinements baked into the script before its first run. No architectural blockers; explicitly said the script's output was safe to take to the human-review gate after the calibration fixes. |
| @fp-design-auditor | APPROVED | No new design tokens. New column reuses `font-data text-text-primary` consistent with adjacent numeric cells. Pre-existing `Cell head` deviation flagged as warning, not new violation. |
| @faang-staff-engineer | CHANGES REQUIRED → APPROVED on re-review | Two real findings: (1) `assert`-based int gate stripped under `python -O` — fixed with `raise TypeError` + explicit `bool` rejection. (2) CASE chain past author's own refactor trigger — fixed by bumping comment to ~100 with DuckDB-folds-into-constant-lookup justification + belt-and-suspenders `int()` casts at SQL builder. Two out-of-scope follow-ups documented in §11. |
| @fp-builder | ALL PASSED | ruff, mypy, pytest (1543 pass / 3 pre-existing fail), tsc, vitest (819 pass / 10 pre-existing fail), Vite build. Pre-existing failures verified unrelated (FinancesCard ROI receipt + Loans-boss in-flight work). |

---

## Pre-existing test failures (NOT caused by this spec)

**pytest (3):** All in the FinancesCard ROI receipt / Loans-boss surface — `test_ask_gemma.py::test_context_for_stat_includes_lineage_drivers[ROI]`, `test_boss_fights.py::TestNarrativePromptIncludesCostContext::test_prompt_carries_net_price_and_modeled_debt`, `test_boss_fights.py::TestStatExplainerRoiNarrative::test_cost_of_attendance_narrative_cites_4yr_cost`. Files not modified by this spec; failures reproduce on `main` HEAD.

**vitest (10):** All in `src/components/build-results/FinancesCard.test.tsx`. File not modified by this spec.

These belong to in-flight ROI-receipt / Loans-boss work (commits `b9fbef3`, `4fb9d81`) and should be triaged by the owners of those specs.

---

## Out-of-scope follow-ups (file as separate specs)

1. **`prev_score: float | None = object()` sentinel** in the home_state re-rank loop (`futureproof_server.py` line 3912) — pre-existing footgun this spec now depends on. Cleanup belongs in its own spec.
2. **Detection script CWD-relative `PARQUET_GLOB`** — should resolve via `Path(__file__).resolve().parents[1]` so the script runs from any working directory. Add an empty-DataFrame guard while at it.
3. **Post-Scorecard-refresh re-run protocol** — re-run `scripts/detect_branch_campuses.py` after each Scorecard refresh and diff against the frozen config. Add to release-engineering checklist.
4. **Tray expansion on Campuses cell** — clicking the `Campuses: 6` cell could expand a tray showing the individual branches with their per-campus costs (same earnings). Currently students find branches via direct school search; the tray would surface them in-context.
5. **Compare screen family-detection** — when comparing two builds, prevent students from accidentally selecting two branches of the same system as their A/B comparison.

---

## Files in this change

```
NEW:
  scripts/detect_branch_campuses.py
  logs/branch_campus_detection_20260506T011440Z.json
  backend/app/config/__init__.py
  backend/app/config/branch_campuses.py
  backend/tests/test_branch_campuses_config.py

MODIFIED:
  src/mcp_server/futureproof_server.py
  backend/app/models/career.py
  frontend/src/types/build.ts
  frontend/src/components/CompareSchoolsPanel.tsx
  frontend/src/components/CompareSchoolsPanel.test.tsx
  frontend/src/i18n/strings.ts
  docs/specs/feature-branch-campus-suppression.md  (Status: DRAFT → COMPLETE)
```
