# Feature: Compare Screen Redesign — Enhanced Scroll + Institutional X-Ray

## Claude Code Prompt

```
Read the spec at docs/specs/feature-compare-screen-redesign.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, MCP integration for institution_aura, compare_builds response expansion)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION (UI spec)
   - Invoke @fp-design-visionary to propose the premium version of the enhanced Compare Screen
   - Visionary writes to §3 (UI/UX Design): accordion components, cost breakdown, school profile, salary range, layout reorder
   - §3 becomes the pixel-perfect implementation target

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x)
   - Run ALL tests to catch regressions

5. DESIGN AUDIT (UI spec)
   - Invoke @design-builder for mechanical token/pattern compliance against Brightpath design system
   - Writes findings to §8 (Design Audit section)
   - If CHANGES REQUIRED: route to implementer via §10 Discussion

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Update §6 Implementation Log, §7 Test Coverage, §8 Code Review
   - Generate report to reports/feature-compare-screen-redesign-YYYY-MM-DD.md
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @design-builder checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-03 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-03 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-compare-school-leaderboard.md`, `docs/specs/completed/full-pipeline-ipeds-finance.md`, `docs/specs/completed/full-pipeline-eada.md`, `docs/specs/completed/feature-institution-aura.md` |

---

## §1 Feature Description

### Overview

Redesign the Compare Screen to surface richer institutional and cost data through an enhanced scroll layout with collapsible accordion sections, while promoting the CompareWinners grid to a more prominent position and adding salary range (p25/p75) to the money comparison.

### Problem Statement

The Compare Screen currently shows pentagon stats, boss outcomes, median salary, career branches, and Gemma insights — but hides critical decision-making data that already exists in the pipeline. A student (and their parent) comparing ISU Business vs Purdue CS cannot see cost of attendance breakdowns, tuition detail (in-state vs out-of-state), salary variance, institution size, endowment, or what's behind the AURA score. This data exists in `consumable.institution_aura`, `consumable.ipeds_finance_profile`, and `CareerOutcome` fields — it just isn't surfaced on the compare endpoint or rendered in the UI.

Additionally, the CompareWinners grid (the most scannable comparison widget) is buried inside the Gemma section, gated behind AI insight loading. It should be the first concrete comparison the student sees after the pentagon.

### Success Criteria

- [ ] CompareWinners grid renders directly after the Pentagon Overlay (position 3), no longer inside the Gemma section
- [ ] Salary comparison shows p25–p75 range alongside the median for each build
- [ ] Cost Breakdown accordion (collapsed by default) shows sticker vs net price bars + cost line-item table (tuition, room & board, COA annual, COA 4-year, net price)
- [ ] School Profile accordion (collapsed by default) shows institution identity (name, control type, FTE enrollment, state) + AURA breakdown (endowment/student, marketing ratio, athletic spend/student, AURA score with basis)
- [ ] Backend `compare_builds()` returns all new fields (cost detail + institution profile) for each build
- [ ] All sections handle null/missing data gracefully — em-dash for missing values, contextual messages for missing AURA data
- [ ] Hover highlight system (`data-col` + `highlightIndex`) works across all new sections
- [ ] Mobile layout stacks properly for new accordion content
- [ ] All existing compare tests pass without modification (except authorized changes)
- [ ] New frontend + backend tests cover accordion rendering, new fields, null propagation

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Enhanced scroll with accordions, not tabbed layout | Preserves the current RPG-first flow; students who don't need deeper data get the same experience. Accordions provide progressive disclosure without forcing navigation changes. | Tabbed zones (5 tabs: Character/Cost/Institution/Careers/Gemma) — more structured but a bigger UI rewrite and breaks the current scroll flow. Hybrid (scroll + one Cost tab) — compromise rejected as half-measure. |
| 2 | Defer income quintile net price (net_price_q1–q5) | Requires Silver→Gold pipeline propagation work that's out of scope for this UI spec. Average net price is surfaced now; quintile personalization is a follow-up. | Include in this spec — higher impact but higher effort and pipeline risk pre-hackathon. |
| 3 | Full institutional X-ray (size + endowment + marketing + athletics) | "No other tool shows this" — surfacing marketing ratio and athletic spend per student is a transparency play that judges and parents notice. Data already in pipeline. | AURA breakdown only (lighter lift, still compelling). Cost data only (minimal, defers all institutional data). |
| 4 | Promote CompareWinners before Character Cards | It's the highest-value scannable widget — 6 chips showing who wins at what. Currently buried below Gemma prose. Moving it up means students see "who wins?" within 2 seconds. | Keep in Gemma section (current position). Move to after salary (still late). |
| 5 | Query `get_institution_aura` MCP tool per unique unitid in compare_builds | Same tool the stat_engine already uses — proven, cached per unitid. Avoids adding a new DuckDB join to the compare response. | Direct DuckDB join in compare_builds (faster but couples the function to a table not used elsewhere in builds.py). |
| 6 | Query `consumable.ipeds_finance_profile` for FTE enrollment | The IPEDS finance profile table has `total_fte_enrollment` and is the canonical source for institution size. A simple DuckDB query by unitid. | Add FTE to institution_aura MCP response (schema change to MCP tool). Pull from EADA (less coverage). |
| 7 | Accordions collapsed by default | The RPG layer (pentagon, bosses, salary) is the primary view for students. Cost/school data is one tap away for parents and deep divers. No information overload. | Expanded by default (overwhelming). First accordion expanded (arbitrary). |

### Constraints

- Hackathon deadline: 2026-05-18. Must ship without pipeline schema changes.
- All new data must come from existing Gold-zone tables (`consumable.institution_aura`, `consumable.ipeds_finance_profile`) or fields already on `CareerOutcome`.
- The `compare_builds()` function loads full `Build` objects from disk — the `CareerOutcome` fields are already in memory. Adding them to the response dict is zero-cost.
- MCP calls for institution_aura add latency. Must cache by unitid within a single compare call.

### Out of Scope

- Income quintile net price selector (net_price_q1–q5) — follow-up spec, requires Silver→Gold propagation
- Books & supplies, off-campus room & board — not in Gold zone
- CompareSchoolsPanel deep-link from Compare Screen — follow-up spec
- Mobile swipe carousel for character cards — follow-up spec
- Shareable comparison card ("show mom this") — follow-up spec

---

## §3 UI/UX Design

> @fp-design-visionary fills this section BEFORE implementation begins. This becomes the pixel-perfect target.

### Scope for Visionary

The visionary should propose designs for:

1. **CompareWinners in new position** — directly after Pentagon Overlay, with its own section label
2. **Enhanced MoneySection** — median wage bar + p25/p75 range band
3. **CompareAccordion** — reusable disclosure component (collapsed by default, chevron, smooth animation)
4. **Cost Breakdown accordion content** — sticker vs net price bars + cost line-item comparison table
5. **School Profile accordion content** — institution identity strip + AURA breakdown table with inline bar visualizations

Reference Brightpath design tokens (DESIGN.md). Dark-first. Space Mono for data. Nunito for body. Framer Motion for accordion open/close. Show both desktop and mobile responsive behavior.

### Mockups

PENDING — @fp-design-visionary

### Interactions

PENDING — @fp-design-visionary

### Responsive Behavior

PENDING — @fp-design-visionary

### Brightpath Design References

PENDING — @fp-design-visionary

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| CompareWinners section | `region-compare-winners` | `section` | "Where they win — dimension comparison" |
| Cost Breakdown accordion | `accordion-cost-breakdown` | `section` | "Cost breakdown comparison" |
| Cost Breakdown toggle | `btn-toggle-cost-breakdown` | `button` | "Expand cost breakdown" / "Collapse cost breakdown" |
| School Profile accordion | `accordion-school-profile` | `section` | "School profile comparison" |
| School Profile toggle | `btn-toggle-school-profile` | `button` | "Expand school profile" / "Collapse school profile" |
| Salary range band | `salary-range-{build_id}` | `div` | "Salary range: $X to $Y" |

---

## §4 Technical Specification

### Architecture Overview

This spec touches two layers: (1) the backend `compare_builds()` service function that assembles comparison data, and (2) the frontend `CompareView` component that renders it.

**Backend:** The `compare_builds()` function in `backend/app/services/builds.py` already loads full `Build` objects (each containing a `CareerOutcome` with 50+ fields). Currently, the response dict cherry-picks ~12 fields per build. This spec adds ~9 more fields from `CareerOutcome` (zero-cost — already in memory) and ~7 fields from `consumable.institution_aura` + `consumable.ipeds_finance_profile` (requires one MCP call and one DuckDB query per unique unitid).

**Frontend:** The `CompareView.tsx` component gets a layout reorder (CompareWinners promoted), an enhanced `MoneySection` (p25/p75), and two new accordion sections (`CompareCostBreakdown`, `CompareSchoolProfile`) powered by a reusable `CompareAccordion` wrapper. The `CompareBuild` TypeScript interface expands to match the new backend fields.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/builds.py` | Modify | Expand `compare_builds()` return dict with cost detail + institution profile fields; add `_fetch_institution_profiles()` helper |
| `frontend/src/api/menu.ts` | Modify | Extend `CompareBuild` interface with 17 new fields |
| `frontend/src/api/mockMenu.ts` | Modify | Add new fields to mock compare data |
| `frontend/src/components/menu/CompareView.tsx` | Modify | Reorder sections (CompareWinners up), remove CompareWinners from Gemma section, add accordion sections |
| `frontend/src/components/menu/MoneySection.tsx` | Modify | Add p25/p75 range band behind median bar |
| `frontend/src/components/menu/CompareAccordion.tsx` | Create | Reusable collapsible accordion with Framer Motion animation |
| `frontend/src/components/menu/CompareCostBreakdown.tsx` | Create | Cost Breakdown accordion content: sticker vs net price bars + cost table |
| `frontend/src/components/menu/CompareSchoolProfile.tsx` | Create | School Profile accordion content: institution identity + AURA breakdown |
| `frontend/src/i18n/strings.ts` | Modify | Add strings for accordion labels, cost fields, school profile fields, salary range labels |
| `frontend/src/components/menu/CompareView.test.tsx` | Modify | Update tests for new section ordering; add tests for accordion sections |
| `backend/tests/services/test_builds.py` | Modify | Add tests for expanded compare_builds() response |

### Data Model Changes

No new Pydantic models needed. No Iceberg schema changes. No new DuckDB tables.

The `CompareBuild` TypeScript interface (frontend) expands:

```typescript
export interface CompareBuild {
  // Existing fields (unchanged)
  build_id: string;
  label: string;
  career: string;
  soc_code: string;
  profile_name: string;
  animal_emoji: string | null;
  school_name: string;
  major_text: string;
  effort: string;
  loan_pct: number;
  median_annual_wage: number | null;
  net_price_annual: number | null;
  modeled_total_debt: number | null;
  tuition_annual: number | null;
  is_out_of_state: boolean;
  institution_control: string | null;

  // NEW — Cost detail (from CareerOutcome, zero-cost)
  cost_of_attendance_annual: number | null;
  published_cost_4yr: number | null;
  room_board_on_campus: number | null;
  tuition_in_state: number | null;
  tuition_out_of_state: number | null;
  earnings_1yr_median: number | null;
  earnings_1yr_p25: number | null;
  earnings_1yr_p75: number | null;
  state_abbr: string | null;

  // NEW — Institution profile (from institution_aura + ipeds_finance_profile)
  fte_enrollment: number | null;
  endowment_per_fte: number | null;
  marketing_ratio: number | null;
  athletic_spend_per_fte: number | null;
  athletic_revenue_per_fte: number | null;
  athletic_subsidy_ratio: number | null;
  aura_score_basis: string | null;
  coverage_tier: string | null;
}
```

### Service Changes

#### Backend: `compare_builds()` expansion

In `backend/app/services/builds.py`, the `compare_builds()` function (lines 363-459) needs:

1. **Add CareerOutcome fields to the build dict** (lines 430-453). These are already loaded — just add them to the dict literal:

```python
"cost_of_attendance_annual": b.career.cost_of_attendance_annual,
"published_cost_4yr": b.career.published_cost_4yr,
"room_board_on_campus": b.career.room_board_on_campus,
"tuition_in_state": b.career.tuition_in_state,
"tuition_out_of_state": b.career.tuition_out_of_state,
"earnings_1yr_median": b.career.earnings_1yr_median,
"earnings_1yr_p25": b.career.earnings_1yr_p25,
"earnings_1yr_p75": b.career.earnings_1yr_p75,
"state_abbr": b.career.state_abbr,
"aura_score_basis": b.career.aura_score_basis,
```

2. **New helper: `_fetch_institution_profiles(builds)`** — before the return dict, collect unique unitids from the builds, call `get_institution_aura` via MCP client for each unique unitid (cache results), and query `consumable.ipeds_finance_profile` for `total_fte_enrollment`. Return a `dict[int, dict]` keyed by unitid.

```python
def _fetch_institution_profiles(builds: list[Build]) -> dict[int, dict[str, Any]]:
    """Fetch institution_aura + FTE for each unique unitid. Cached per unitid."""
    from src.mcp_server.futureproof_server import mcp_client
    
    profiles: dict[int, dict[str, Any]] = {}
    seen_unitids: set[int] = set()
    
    for build in builds:
        unitid = build.career.unitid
        if unitid in seen_unitids:
            continue
        seen_unitids.add(unitid)
        
        # Institution AURA via MCP
        aura_data: dict[str, Any] = {}
        try:
            result = mcp_client.call("get_institution_aura", {"unitid": unitid})
            if result:
                aura_data = result
        except Exception:
            pass
        
        # FTE enrollment via DuckDB
        fte: int | None = None
        try:
            con = duckdb.connect("data/futureproof.duckdb", read_only=True)
            row = con.execute(
                "SELECT total_fte_enrollment FROM consumable.ipeds_finance_profile WHERE unitid = ?",
                [unitid],
            ).fetchone()
            if row:
                fte = row[0]
            con.close()
        except Exception:
            pass
        
        profiles[unitid] = {
            "endowment_per_fte": aura_data.get("endowment_per_fte"),
            "marketing_ratio": aura_data.get("marketing_ratio"),
            "athletic_spend_per_fte": aura_data.get("athletic_spend_per_fte"),
            "athletic_revenue_per_fte": aura_data.get("athletic_revenue_per_fte"),
            "athletic_subsidy_ratio": aura_data.get("athletic_subsidy_ratio"),
            "coverage_tier": aura_data.get("coverage_tier"),
            "fte_enrollment": fte,
        }
    
    return profiles
```

Then in the build dict, merge institution profile fields:

```python
inst = institution_profiles.get(b.career.unitid, {})
# ... add to build dict:
"endowment_per_fte": inst.get("endowment_per_fte"),
"marketing_ratio": inst.get("marketing_ratio"),
"athletic_spend_per_fte": inst.get("athletic_spend_per_fte"),
"athletic_revenue_per_fte": inst.get("athletic_revenue_per_fte"),
"athletic_subsidy_ratio": inst.get("athletic_subsidy_ratio"),
"coverage_tier": inst.get("coverage_tier"),
"fte_enrollment": inst.get("fte_enrollment"),
```

#### Frontend: New components

1. **`CompareAccordion`** — generic disclosure wrapper:
   - Props: `title: string`, `testId: string`, `children: ReactNode`, `defaultOpen?: boolean`
   - State: `open` boolean, toggled by clicking the header
   - Animation: Framer Motion `AnimatePresence` + `motion.div` with height auto-animation
   - Chevron rotates 180° on open

2. **`CompareCostBreakdown`** — renders inside Cost accordion:
   - Props: `builds: CompareBuild[]`, `highlightIndex: number | null`
   - Sticker vs Net Price bars: horizontal bars proportional to max value
   - Cost table: rows = line items, columns = builds

3. **`CompareSchoolProfile`** — renders inside School Profile accordion:
   - Props: `builds: CompareBuild[]`, `highlightIndex: number | null`, `stats: CompareStatRow[]`
   - Institution identity cards per build
   - AURA breakdown table with inline bars

4. **Enhanced `MoneySection`**:
   - Accept new `CompareBuild` fields (`earnings_1yr_p25`, `earnings_1yr_p75`)
   - Render p25/p75 range as a lighter band behind the median value

### Testing Impact Analysis

> All test file paths and test names confirmed via codebase search.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/components/menu/CompareView.test.tsx` | `renders_the_Gemma_summary_text_once_compareInsights_resolves` | Med | CompareWinners removal from Gemma section changes DOM structure |
| `frontend/src/components/menu/CompareView.test.tsx` | `renders_one_Risk_Headline_card_per_boss_in_the_result` | Low | Section reorder changes DOM order but not content — test uses `data-testid` |
| `frontend/src/components/menu/CompareView.test.tsx` | `renders_salary_figures_in_money_section` | Med | MoneySection now shows additional range data alongside median |
| `frontend/src/api/mockMenu.ts` (not a test, but test dependency) | `mockCompareBuilds` | High | All frontend compare tests mock through this — must add new fields |
| `backend/tests/services/test_builds.py` | `test_compare_builds_returns_expanded_build_fields` | High | Asserts specific keys in compare response — new keys added |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/api/mockMenu.ts` : `mockCompareBuilds` | Add 17 new fields to mock build dicts | New fields on CompareBuild interface; all frontend tests depend on this mock |
| `frontend/src/components/menu/CompareView.test.tsx` | Update DOM queries if CompareWinners position change affects test selectors | Section reorder moves CompareWinners from Gemma section to position 3 |
| `backend/tests/services/test_builds.py` : `test_compare_builds_returns_expanded_build_fields` | Add assertions for new fields in compare response | New fields added to compare_builds() return dict |

#### Confirmed Safe

These tests MUST NOT break. If any fail, STOP and escalate:

- `backend/tests/services/test_builds.py` : `test_compare_builds_returns_stat_and_boss_rows` — stat/boss structure unchanged
- `backend/tests/services/test_builds.py` : `test_compare_builds_returns_boss_skill_counts_and_original_values` — boss structure unchanged
- `backend/tests/services/test_builds.py` : `test_compare_builds_handles_four_builds` — 4-build support unchanged
- `backend/tests/services/test_builds.py` : `test_compare_builds_branches_limited_to_three` — branch logic unchanged
- `backend/tests/services/test_builds.py` : `test_compare_builds_missing_fight_shows_dash_and_zero_skills` — boss edge case unchanged
- `backend/tests/routers/test_builds_collection.py` : all `TestCompareBuildsRouter` tests — endpoint contract is additive only
- `frontend/src/components/menu/CompareView.test.tsx` : `renders_character_cards_for_each_build` — card rendering unchanged
- `frontend/src/components/menu/CompareView.test.tsx` : `handles_3_builds` / `handles_4_builds` — multi-build support unchanged
- `frontend/src/components/menu/CompareView.test.tsx` : `Ask Gemma compare entry button` suite — chat integration unchanged
- `frontend/src/screens/MenuScreen.test.tsx` : all compare-mode tests — MenuScreen not touched
- `frontend/src/components/menu/GemmaChat.test.tsx` : `works_for_compare_scope_without_a_build_prop` — chat scope unchanged

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_builds.py` | `test_compare_builds_returns_cost_detail_fields` | New cost fields (cost_of_attendance_annual, published_cost_4yr, room_board_on_campus, tuition_in_state, tuition_out_of_state, earnings_1yr_p25, earnings_1yr_p75) present in response |
| P0 | `backend/tests/services/test_builds.py` | `test_compare_builds_returns_institution_profile_fields` | Institution profile fields (fte_enrollment, endowment_per_fte, marketing_ratio, athletic_spend_per_fte, aura_score_basis, coverage_tier) present in response |
| P0 | `frontend/src/components/menu/CompareView.test.tsx` | `test_renders_compare_winners_before_character_cards` | CompareWinners grid appears in DOM before CharacterCard section |
| P0 | `frontend/src/components/menu/CompareView.test.tsx` | `test_renders_cost_breakdown_accordion_collapsed` | Cost Breakdown accordion exists, is collapsed by default |
| P0 | `frontend/src/components/menu/CompareView.test.tsx` | `test_renders_school_profile_accordion_collapsed` | School Profile accordion exists, is collapsed by default |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `test_cost_accordion_expands_and_shows_cost_table` | Clicking Cost accordion reveals cost breakdown table with line items |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `test_school_profile_accordion_expands_and_shows_aura_breakdown` | Clicking School Profile accordion reveals AURA breakdown |
| P1 | `frontend/src/components/menu/CompareView.test.tsx` | `test_salary_section_shows_p25_p75_range` | MoneySection renders p25/p75 range data |
| P1 | `backend/tests/services/test_builds.py` | `test_compare_builds_caches_institution_profile_by_unitid` | Two builds at same school = one MCP call (verify via mock call count) |
| P2 | `frontend/src/components/menu/CompareView.test.tsx` | `test_cost_accordion_handles_null_cost_data` | Cost breakdown shows em-dash for missing values |
| P2 | `frontend/src/components/menu/CompareView.test.tsx` | `test_school_profile_handles_missing_aura_data` | School Profile shows "Not available" when AURA data is missing |
| P2 | `backend/tests/services/test_builds.py` | `test_compare_builds_handles_missing_institution_aura` | Builds with no institution_aura data get null institution profile fields |

#### Test Data Requirements

- **Backend:** Existing `_make_build()` / `_make_career_outcome()` test fixtures in `test_builds.py` need to be verified for CareerOutcome fields (cost_of_attendance_annual, published_cost_4yr, room_board_on_campus, tuition_in_state, tuition_out_of_state, earnings_1yr_p25, earnings_1yr_p75, state_abbr, aura_score_basis). If not present, add them to fixtures.
- **Backend:** Mock `mcp_client.call("get_institution_aura", ...)` to return realistic aura data for institution profile tests. Mock DuckDB query for `total_fte_enrollment`.
- **Frontend:** `mockCompareBuilds` in `mockMenu.ts` must include all 17 new fields with realistic test values. At least one mock build should have null values for cost/institution fields to test null handling.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline/data/stat changes — this spec only reads existing Gold-zone data)

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §3/§4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** PENDING
[Filled in by @design-builder — Brightpath token compliance, dark-first enforcement, responsive behavior]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

**Follow-up specs:**
- Income quintile net price selector (net_price_q1–q5) — requires Silver→Gold propagation
- CompareSchoolsPanel deep-link from Compare Screen character cards
- Mobile swipe carousel for character cards
- Shareable 1-screen comparison card for the "convince the parent" use case
