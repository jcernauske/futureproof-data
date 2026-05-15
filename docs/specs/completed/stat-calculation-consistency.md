# Spec: stat-calculation-consistency

## Claude Code Prompt

```
Read the spec at docs/specs/stat-calculation-consistency.md in its entirety.

This spec resolves four cross-stat consistency issues identified by the May 4, 2026 audit
of ERN, RES, GRW, and AURA calculation sites (reports/stat-{ern,res,grw,aura}-calculation-
audit-2026-05-04.md). It is a sister spec to roi-net-lifetime-value.md and SHOULD LAND
TOGETHER. Both must ship before submission so the cross-stat patterns described in the
README are actually true in the code.

The four issues addressed:
  1. Rounding-method inconsistency — AURA uses Python built-in round() (banker's rounding);
     every other stat uses round-half-up. Normalize AURA to round_half_up.
  2. Runtime re-derivation pattern undocumented — ROI is the only stat that re-derives at
     runtime. The pattern is correct (residency-aware sticker cost requires it), but it
     should be explicitly documented as the intentional exception.
  3. Boss-fight signal pattern undocumented — Three different patterns exist for how bosses
     read from stats. RES boss reads raw inputs (sum), GRW boss reads displayed stat,
     ROI boss is independent (after this spec lands). All three are correct but the
     rationale per stat is not explained anywhere in code.
  4. Schools-for-career leaderboard composite score will produce different rankings under
     the new ROI formula. Math doesn't break (still 1-10 + 1-10), but rankings shift.
     Spec adds a sanity-check requirement.

This spec is a CLEANUP spec, not a behavior change. The only user-visible change is that
AURA scores for some institutions will shift by 1 point (where banker's rounding rounded
half-to-even and round-half-up rounds half-up). All architectural patterns described are
already in place — this spec adds DOCUMENTATION (in code, not in user-facing copy) and one
small numerical fix.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §2-§4
   - Invoke @fp-data-reviewer to review §4 (AURA rounding change impact on existing data)
   - Both write findings to §5
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED: STOP, alert human

2. DESIGN VISION — SKIP (no UI changes)

3. IMPLEMENTATION
   - Execute the four issues in the order described in §4. They are independent — any one
     can ship without the others — but order them as listed for clean PR diffs.
   - The AURA rounding change requires re-running the institution_aura Gold pipeline.
     Confirm with @fp-data-reviewer that this is safe before running.
   - Log all work to §6
   - Run backend (ruff + mypy + pytest) to verify build
   - BUILD ACCOUNTABILITY: if build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer
   - The AURA rounding change has known test impact: rerun affected fixtures, confirm
     diffs are limited to integer rounding boundaries
   - The leaderboard sanity check is a manual eyeball verification, not automated

5. DESIGN AUDIT — SKIP (no UI changes)

6. CODE REVIEW
   - Invoke @faang-staff-engineer
   - Critical review areas: (a) the comment blocks added at each site read clearly,
     (b) AURA rounding change doesn't break partial-null handling, (c) docstrings on
     the boss-fight scoring functions explain WHY each chose its pattern

7. VERIFICATION
   - Invoke @fp-builder
   - Backend: ruff check, mypy, pytest
   - Manual: run the leaderboard sanity-check query in §4 and visually inspect 5 sample
     careers' top-10 schools before/after; confirm rankings still pass the eyeball test
   - Log results to §9

8. COMPLETION
   - Update top-level Status to COMPLETE
   - Check off Success Criteria
   - Generate report to reports/stat-calculation-consistency-YYYY-MM-DD.md
```

---

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-04 |
| Author | Jeff Cernauske + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-05-04 |
| Blocked By | — |
| Sister Spec | `roi-net-lifetime-value.md` — should land in the same submission window |
| Related Specs | `pentagon-stat-reshape.md` (completed); `roi-formula-cost-of-attendance.md` (completed v2); the four `stat-{ern,res,grw,aura}-calculation-audit-2026-05-04.md` reports that surfaced the issues |
| Supersedes | None — additive cleanup |

---

## §1 Feature Description

### Overview

Resolve four cross-stat consistency issues surfaced by the May 4, 2026 calculation-site audit. Three of the four are documentation/clarity fixes (in-code comments, docstrings explaining intentional pattern divergence). One is a small numerical fix (AURA rounding method normalization). Together they ensure the pentagon stats present a coherent design story to anyone reading the code, and that the cross-stat consistency claims in `roi-net-lifetime-value.md`'s README updates are actually true in implementation.

### Problem Statement

The four-stat audit (ERN, RES, GRW, AURA) plus the eleven-site ROI inventory revealed that the pentagon stats follow the same overall architecture (Gold pipeline computes 1–10 score → backend reads → optional effort/skill/branch deltas → frontend displays), but four specific patterns diverge across stats without the rationale documented anywhere:

1. **Rounding methods diverge.** ERN, RES, GRW, HMN, and (current) ROI all use `_round_half_up` (`math.floor(x + 0.5)`). AURA uses Python's built-in `round()`, which is banker's rounding (round-half-to-even). At the .5 boundary these produce different integers — `round(0.5)` is 0 but `round_half_up(0.5)` is 1. AURA is the outlier and the audit explicitly flagged it ("banker's rounding here" comment at `institution_aura.py:304`). The drift is small (only affects values exactly at .5 boundaries), but it's an actual numerical inconsistency, not just a stylistic one.

2. **Runtime re-derivation is undocumented.** ERN, RES, GRW, AURA all read pre-computed Gold values at request time. ROI is the only stat that re-derives at runtime (in `_derive_roi`), because residency-aware tuition (out-of-state students paying more for public schools) cannot be modeled at Gold-pipeline time without per-user context. This is correct, but a reviewer reading the codebase will see the asymmetry and wonder if it's a bug. No comment explains why.

3. **Boss-fight signal patterns diverge without rationale.** Three different patterns exist:
   - **RES → Boss AI:** sums raw inputs (`raw_stat_res + raw_stat_hmn`, range 2–20). Diverges from displayed pentagon RES.
   - **GRW → Market Boss:** uses the post-modifier displayed stat directly (`stats.grw`, range 1–10).
   - **ROI → Boss Debt (after `roi-net-lifetime-value.md` v1.2):** independent of `stat_roi` entirely; computed from raw cost/loan/earnings inputs via amortization. Range 1–10 but produced by a separate function.

   All three are intentional and correct for their respective bosses, but the rationale-per-pattern is nowhere in the code.

4. **Schools-for-career leaderboard composite ranking will shift.** The leaderboard at `futureproof_server.py:3601-3606` ranks schools by `(stat_ern + stat_roi) / 2`. The ROI v1.2 spec changes the underlying ROI distribution, so the leaderboard's rankings will reorder. The math doesn't break (both stats remain 1–10 integers, composite remains 1–10), but the user-visible ranking will be different. There is no automated check that the new rankings pass an eyeball sanity test.

### Success Criteria

- [ ] AURA rounding normalized to `_round_half_up` in `src/gold/institution_aura.py`
- [ ] AURA pipeline re-run; new `consumable.institution_aura` rows match `_round_half_up` semantics
- [ ] `src/gold/institution_aura.py:304` comment "banker's rounding here" removed (no longer applicable)
- [ ] `_derive_roi` in `backend/app/services/stat_engine.py` has a docstring explaining ROI is the *only* runtime-rederiving stat and *why* (residency-aware sticker cost)
- [ ] `_score_ai`, `_score_market`, and `_score_loans` in `backend/app/services/boss_fights.py` each have docstrings explaining the boss's signal-source pattern (raw sum vs. displayed stat vs. independent derivation) and why that pattern was chosen for that boss
- [ ] A "stat patterns reference" comment block exists at the top of `backend/app/services/stat_engine.py` summarizing which stat uses which pattern, so future developers don't have to read four spec files to understand the architecture
- [ ] The leaderboard composite query at `futureproof_server.py:3601-3606` has a comment noting it produces ranking-shift (not math-break) when underlying stats change
- [ ] Manual eyeball verification: top-10 schools for at least 5 representative careers (e.g., Software Developer, Registered Nurse, Marketing Manager, Mechanical Engineer, Elementary Teacher) before/after the ROI v1.2 + AURA rounding changes; rankings should still pass intuitive sanity test (no obvious nonsense)
- [ ] All existing pytest, ruff, and mypy checks pass
- [ ] Updated `test_institution_aura.py` fixtures reflect `_round_half_up` semantics (small number of fixture diffs expected)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Normalize AURA rounding to `_round_half_up`, not the other way around | Four out of five pentagon stats already use `_round_half_up`. AURA is the outlier. Changing AURA is a one-file change; changing the other four would mean re-running multiple Gold pipelines and updating significantly more fixtures. Round-half-up also matches the audit-spec convention used throughout `futureproof_engine.py`. | Normalize all stats to banker's rounding (matches Python's default). Rejected: would require touching ERN, RES, GRW, HMN, and ROI computations — much larger blast radius for a stylistic preference. The round-half-up convention also matches the spec-document style in `gold-futureproof-engine.md`. |
| 2 | Document patterns in code comments and docstrings, not by refactoring to a single pattern | The three boss-fight patterns and the runtime re-derivation asymmetry exist for **valid reasons specific to each stat**: RES-Boss AI sums raw signals to preserve pre-reshape thresholds; GRW-Market Boss uses the displayed stat because GRW is a single-input stat where modifiers (skills) genuinely should affect the boss; ROI is financing-agnostic so its boss must be independent. Forcing them into a single pattern would harm correctness, not improve consistency. The right fix is to *explain* why each diverges, not to *eliminate* the divergence. | Refactor all bosses to a single pattern. Rejected per above — the patterns are correct as designed. |
| 3 | Add a "stat patterns reference" comment block at the top of `stat_engine.py` | Future developers (and Claude in future sessions) shouldn't need to read four audit reports + four spec files to understand which stat does what. A 15–20 line comment block at the top of the canonical orchestration file documents the patterns once. | Put the documentation in `docs/architecture/stats.md` instead. Rejected: the repo has no `docs/architecture/` directory and adding one introduces a new convention. The comment block lives where developers already look. |
| 4 | Leaderboard sanity check is manual, not automated | The "is this ranking sensible" question requires human judgment. Automating it would require defining what "sensible" means, which is the actual hard problem. A 10-minute eyeball pass on 5 representative careers is faster and more honest than building a fragile automated check that we'd have to update every time a stat formula changes. | Snapshot test that locks in current top-10 lists. Rejected: would block every future stat change with a fixture update, even when the ranking shift is correct. |
| 5 | Ship this spec **with** `roi-net-lifetime-value.md`, not before or after | The README updates in the ROI spec describe cross-stat patterns ("Boss Debt is where financing matters", "ROI is the only financing-agnostic stat", etc.) that depend on this spec's documentation existing. If the ROI spec ships without this one, the README will reference patterns that aren't documented in code. If this spec ships without ROI, the leaderboard sanity-check requirement has nothing to verify against. | Ship them as separate releases. Rejected per above — they're sister specs by design. |

### Constraints

- **AURA rounding fix touches existing Gold data.** Re-running `institution_aura` Gold pipeline produces new `consumable.institution_aura` rows. Some institutions' AURA scores will change by ±1. Coordinate timing with @fp-data-reviewer.
- **No frontend changes.** Pentagon stat contract preserved — all stats remain 1–10 integers.
- **No new external data sources.** All inputs already in Gold.

---

## §3 UI/UX Design

> SKIPPED — backend + Gold pipeline only. The AURA rounding fix may shift some institutions' displayed AURA score by 1 point, which is a numerical change rather than a UI change. No design or layout work required.

---

## §4 Technical Specification

### Issue 1: AURA Rounding Normalization

**Files modified:**

| File | Change |
|------|--------|
| `src/gold/institution_aura.py` | Replace Python built-in `round()` with `_round_half_up`. Remove the "banker's rounding here" comment. Add an inline comment confirming round-half-up matches the project-wide stat convention. |
| `backend/tests/services/test_institution_aura.py` (or equivalent test file) | Update any fixtures whose expected AURA value sits exactly at a .5 boundary. Most fixtures will be unchanged. |

**Code change** (in `institution_aura.py:290-304`, the `rescale_aura` function):

```python
# Before:
def rescale_aura(raw_score):
    span = 0.9400 - 0.1413
    t = (raw_score - 0.1413) / span
    t_clipped = max(0.0, min(1.0, t))
    aura_continuous = 1.0 + 9.0 * t_clipped
    return aura_continuous, round(aura_continuous)  # banker's rounding here

# After:
def rescale_aura(raw_score):
    span = 0.9400 - 0.1413
    t = (raw_score - 0.1413) / span
    t_clipped = max(0.0, min(1.0, t))
    aura_continuous = 1.0 + 9.0 * t_clipped
    # Round-half-up to match project-wide pentagon-stat convention
    # (ERN, RES, GRW, HMN, ROI all use _round_half_up).
    return aura_continuous, _round_half_up(aura_continuous)
```

Add `_round_half_up` import or local definition consistent with how other Gold modules do it (check `futureproof_engine.py` for the canonical pattern — likely `from src.gold.futureproof_engine import _round_half_up` or a shared utility).

**Pipeline re-run:** After the code change, re-run the institution_aura Gold pipeline (`/bs:cast institution-aura` or equivalent). Verify the row count is unchanged and that any AURA score changes are limited to ±1 (the maximum a rounding-method change can produce).

### Issue 2: Document Runtime Re-derivation Asymmetry

**Files modified:**

| File | Change |
|------|--------|
| `backend/app/services/stat_engine.py` | Add docstring to `_derive_roi` explaining that ROI is the *only* runtime-rederiving stat and *why* |

**Code change** (in `stat_engine.py`, on or near `_derive_roi`):

```python
def _derive_roi(
    *,
    published_cost_4yr: float | None,
    earnings_1yr_median: float | None,
    raw_stat_roi: int | None,
) -> int | None:
    """Runtime ROI: 15-year payback multiplier with residency-aware cost basis.

    ROI is the only pentagon stat that re-derives at runtime. ERN, RES, GRW,
    and AURA all read pre-computed Gold values directly. ROI re-derives because
    residency-aware tuition (out-of-state students paying more for public
    schools) cannot be modeled at Gold-pipeline time without per-user context.

    When residency data is unavailable or `published_cost_4yr` is None, this
    function falls back to `raw_stat_roi` (the Gold-precomputed value, which
    uses sticker cost without residency adjustment).

    Financing-agnostic — does not accept loan_pct. The slider does not move ROI.
    Earnings projected at flat 3% nominal growth.
    See spec: docs/specs/roi-net-lifetime-value.md
    """
    ...
```

### Issue 3: Document Boss-Fight Signal Patterns

**Files modified:**

| File | Change |
|------|--------|
| `backend/app/services/boss_fights.py` | Add docstrings to `_score_ai`, `_score_market`, `_score_loans` explaining the signal-source pattern and rationale |

**Code change** (in `boss_fights.py`):

```python
def _score_ai(career: CareerOutcome) -> tuple[int | None, str]:
    """Boss AI score = raw_stat_res + raw_stat_hmn (sum, range 2-20).

    Pattern: reads RAW inputs, not the displayed pentagon RES.

    Why this pattern: the displayed RES is a 50/50 blend of stat_res and
    stat_hmn (computed by `_blend_res`). Boss AI predates that blend and was
    calibrated against the raw sum (thresholds: win >= 14, draw >= 10).
    Preserving the raw sum keeps Boss AI bit-exact compatible with pre-reshape
    thresholds, which matters for fight-balance regression testing.

    Other stats use different boss patterns — see stat_engine.py top-of-file
    comment block for the full pattern reference.
    """
    raw_res = career.raw_stat_res
    raw_hmn = career.raw_stat_hmn
    score = _safe_sum(raw_res, raw_hmn)
    return score, f"raw {res_str} + {hmn_str} = {score}"

def _score_market(career: CareerOutcome) -> tuple[int | None, str]:
    """Market Boss score = career.stats.grw (post-modifier displayed stat, range 1-10).

    Pattern: reads the displayed pentagon stat AFTER skill/branch deltas.

    Why this pattern: GRW has a single input (BLS employment_change_pct) and
    skill modifiers (Emerging-Tech Cert, Industry Conference) genuinely
    represent the student improving their position in a growing market.
    The boss should reflect those modifiers — beating Market Boss is
    meaningfully easier with the right skills, by design.

    Other stats use different boss patterns — see stat_engine.py top-of-file
    comment block for the full pattern reference.
    """
    if career.stats.grw is None:
        return None, "GRW unavailable"
    return career.stats.grw, f"GRW {career.stats.grw}"

def _score_loans(career: CareerOutcome) -> tuple[int | None, str]:
    """Boss Debt score = independent of stat_roi; derived from amortization
    of (published_cost_4yr × loan_pct) at federal rate.

    Pattern: independent — does NOT read any pentagon stat.

    Why this pattern: ROI is financing-agnostic by design (see
    roi-net-lifetime-value.md §2 Decision #1). The slider does not move ROI.
    But Boss Debt MUST depend on the slider — that's literally what the boss
    represents. Therefore Boss Debt cannot be derived from stat_roi; it must
    compute its own signal from raw cost/loan/earnings inputs via amortization.

    Score signal: total_interest_paid / earnings_1yr_median (as a multiple of
    first-year salary), mapped to 1-10 via _interest_burden_to_score.

    Other stats use different boss patterns — see stat_engine.py top-of-file
    comment block for the full pattern reference.
    """
    ...
```

### Issue 4: Add "Stat Patterns Reference" Comment Block

**Files modified:**

| File | Change |
|------|--------|
| `backend/app/services/stat_engine.py` | Add module-level docstring at the top documenting cross-stat patterns |

**Code change** (top of `stat_engine.py`, after imports):

```python
"""
Pentagon stat orchestration. Reads pre-computed Gold values, applies effort/skill/branch
deltas, returns a PentagonStats for the build response.

================================================================================
PENTAGON STAT PATTERN REFERENCE
================================================================================

All five stats produce 1-10 integers but follow different patterns. Each pattern is
intentional and correct for its stat. The asymmetries below are NOT bugs.

                  | RUNTIME      | EFFORT  | SKILL    | BRANCH    | BOSS
STAT              | RE-DERIVE?   | SHIFT?  | DELTA?   | DELTA?    | PATTERN
------------------+--------------+---------+----------+-----------+-------------------
ERN (Earning)     | No           | Yes     | Yes      | Yes (thr) | (no boss)
ROI (Payback)     | YES (resid.) | No      | Yes      | Yes (thr) | INDEPENDENT
RES (AI Resil.)   | No           | No      | Yes      | Yes (tbl) | RAW SUM (raw_res
                  |              |         |          |           |  + raw_hmn, 2-20)
GRW (Growth)      | No           | No      | Yes      | Yes (lit) | DISPLAYED STAT
                  |              |         |          |           |  (stats.grw, 1-10)
AURA (Brand)      | No           | No      | No       | No        | (no boss)

Legend:
  thr = threshold-based delta from wage_delta
  tbl = pre-computed delta read from Gold table
  lit = literal arithmetic difference between source/target

Why ROI alone re-derives at runtime: residency-aware sticker cost (out-of-state
public-school tuition) requires per-user context not available at Gold-pipeline time.
See _derive_roi docstring.

Why ERN alone gets effort shift: effort represents how hard the student works to
maximize earning potential. It would be incoherent to apply effort to GRW (market
growth doesn't care how hard you study) or RES (AI exposure is a property of the
job, not your study habits) or AURA (institutional brand power is fixed) or ROI
(program payback is financing-agnostic, see Decision #1 of
roi-net-lifetime-value.md).

Why AURA alone is fully immutable: AURA is institution-level (one value per UNITID,
shared across all CareerOutcome rows for the build) and represents fixed
characteristics — endowment, marketing spend, athletics. Skills and branches don't
change which school you attended.

For boss-fight pattern rationale, see boss_fights.py docstrings on _score_ai,
_score_market, _score_loans.

For stat-by-stat audits, see:
  reports/stat-ern-calculation-audit-2026-05-04.md
  reports/stat-res-calculation-audit-2026-05-04.md
  reports/stat-grw-calculation-audit-2026-05-04.md
  reports/stat-aura-calculation-audit-2026-05-04.md
"""
```

### Issue 5: Leaderboard Composite Comment + Sanity Check

**Files modified:**

| File | Change |
|------|--------|
| `src/mcp_server/futureproof_server.py` (around line 3601) | Add a comment to the composite-score query explaining ranking-shift behavior |

**Code change** (in `futureproof_server.py:3601-3606`, the leaderboard query):

```python
# Composite score = (stat_ern + stat_roi) / 2.
# Both inputs are 1-10 integers, so composite remains in [1, 10].
# Note: when either stat's underlying formula changes (e.g., ROI v1.2),
# this composite continues to compute correctly but the *rankings shift*
# because the underlying values shift. This is expected behavior — verify
# top-10 lists pass eyeball sanity test for representative careers when
# stat formulas change. See spec: stat-calculation-consistency.md §4 Issue 5.
sql = """
    (CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 AS composite_score,
    RANK() OVER (
        ORDER BY
            (CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 DESC,
            earnings_1yr_median DESC NULLS LAST,
            net_price_annual ASC NULLS LAST
    ) AS abs_rank
"""
```

**Manual sanity-check procedure** (to be run after both this spec and `roi-net-lifetime-value.md` land):

```
For each of the following representative careers, query the schools-for-career
leaderboard endpoint and inspect the top 10 results:

  1. Software Developers (15-1252)
  2. Registered Nurses (29-1141)
  3. Marketing Managers (11-2021)
  4. Mechanical Engineers (17-2141)
  5. Elementary School Teachers (25-2021)

For each top-10 list, verify:
  - No school appears with obviously absurd ranking (e.g., a school known for low
    earnings in this field should not be #1)
  - The price/earnings tradeoff visible in the list looks reasonable (cheap public
    schools with strong earnings should rank well; expensive privates with average
    earnings should not dominate the top)
  - The ordering passes the "would I show this to a real student" test

Document findings in §6 Implementation Log with screenshots or copy-paste output.
If any list fails the eyeball test, escalate to human before marking COMPLETE —
the issue may be with the new ROI thresholds in roi-net-lifetime-value.md, not
with this spec.
```

### Migration Order

The five issues are independent and any can ship without the others, but for clean PR diffs:

1. **Issue 4 (stat patterns reference comment block)** — pure documentation, zero risk, can land first.
2. **Issue 2 (`_derive_roi` docstring)** — pure documentation, zero risk.
3. **Issue 3 (boss-fight docstrings)** — pure documentation, zero risk.
4. **Issue 5 (leaderboard composite comment)** — pure documentation, zero risk.
5. **Issue 1 (AURA rounding fix)** — code change + Gold pipeline re-run. Land last so the previous documentation lands cleanly first.
6. **Manual sanity check (Issue 5 verification)** — runs after both this spec and `roi-net-lifetime-value.md` are merged.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_institution_aura.py` (or equivalent) | Any test asserting a specific AURA integer at a `.5` continuous-score boundary | **Low** | Banker's rounding vs. round-half-up only diverges at exact .5 values. Most fixtures will be unchanged. |
| All other `test_*.py` | — | **None** | The other four issues are documentation-only. No behavior change. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_institution_aura.py` boundary fixtures | Recompute expected AURA value using `_round_half_up` | Numerical fix |

#### Confirmed Safe (must NOT break — escalate if they fail)

- All ERN, RES, GRW, ROI tests (no behavior change)
- All boss-fight tests (no behavior change)
- All branch tree, skill pool, and effort-adjustment tests
- The sister spec `roi-net-lifetime-value.md` test suite

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `test_institution_aura.py` | `test_aura_uses_round_half_up_at_boundaries` | At continuous score values of exactly N.5 (e.g., 5.5), `aura_score` is `N+1` (round-half-up), not `N` (banker's rounds-to-even at 5.5 → 6 by coincidence, but at 4.5 → 4) |

Note: only one new automated test required. The other four issues are documentation, which lints/tests don't enforce — they're enforced by code review (@faang-staff-engineer reviews comment quality in §8).

#### Test Data Requirements

- Fixture `EVEN_BOUNDARY_AURA`: continuous score 4.5 → expected `aura_score = 5` (under round-half-up; banker's would give 4)
- Fixture `ODD_BOUNDARY_AURA`: continuous score 5.5 → expected `aura_score = 6` (both methods agree here)
- Fixture `NON_BOUNDARY_AURA`: continuous score 7.3 → expected `aura_score = 7` (both methods agree)

The test should pass under round-half-up and FAIL under banker's rounding for the EVEN_BOUNDARY_AURA fixture, demonstrating the change is real.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING

#### Findings
[Filled in by @fp-architect — review §2 design decisions, the comment-block content for accuracy, the documented patterns for completeness]

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** PENDING

#### Findings
[Filled in by @fp-data-reviewer — review the AURA rounding change for data impact: how many institutions shift by 1 point, whether the shift direction is balanced or systematically biased, whether the post-fix distribution still passes the v1 anchor-school validation]

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### AURA Distribution Impact
[Filled in after AURA pipeline re-run — count of institutions whose `aura_score` changed by ±1, distribution of shift direction, confirmation that all 13 anchor schools still validate]

### Leaderboard Sanity Check Results
[Filled in after both specs land — top-10 lists for the 5 representative careers, before/after, with eyeball-test verdict]

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

---

## §8 Reviews

**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** PENDING

#### Findings
[Filled in by reviewer — special attention to (a) comment-block readability for a reviewer who has NOT read the four audit reports, (b) docstrings clearly explain the why-this-pattern rationale per stat, (c) AURA rounding change doesn't break partial-null handling]

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
| AURA pipeline re-run | |
| Leaderboard sanity check | |

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

[Final thoughts, lessons learned, follow-up items.]

**Post-hackathon follow-ups:**
- If future stats are added to the pentagon, update the "stat patterns reference" comment block in `stat_engine.py` to include them
- If a new boss is added, add a docstring to its scoring function explaining the signal-source pattern
- Consider extracting `_round_half_up` to a shared utility module (`backend/app/util/rounding.py` or `src/gold/_rounding.py`) so it doesn't have to be re-imported across files
- Consider an automated lint rule that fails CI if any new `round()` call appears in stat-computing code (use `_round_half_up` instead)
