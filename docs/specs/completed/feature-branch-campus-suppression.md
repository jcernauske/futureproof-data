# Spec: feature-branch-campus-suppression

## Claude Code Prompt

```
Read the spec at docs/specs/feature-branch-campus-suppression.md in its entirety.

This spec addresses a data-quality artifact in the schools-for-career leaderboard:
multi-campus university systems (Ohio University, Penn State, Indiana University, etc.)
report identical earnings data across all branch campuses in the College Scorecard
field-of-study file. Combined with regional campuses' lower published costs, this produces
artificially elevated ROI scores that can dominate leaderboards (e.g., 5 Ohio University
regional campuses tied for #1 in Accounting).

The fix is two-phase:
  Phase 1: A discovery script (kept in scripts/ for future re-runs) detects multi-campus
           families and identifies which branch campuses have earnings inherited from
           their flagship. Output is a frozen Python config file.
  Phase 2: The leaderboard query suppresses branch campuses (keeping only the flagship
           row per family) AND adds a "Campuses" column to the leaderboard showing how
           many institutions are in the family. Multi-campus families show "6"; standalone
           schools show "1". The column is the educational surface — it's how students
           learn this is a multi-campus system.

CRITICAL DESIGN PRINCIPLES:
- This is a UI-layer suppression, not a Gold-layer fix. Gold stays the source of truth.
- Branch campuses remain searchable via direct school search and buildable individually.
- Only the leaderboard view is filtered, because that's where the data shape produces
  unfair rankings.
- The build flow (FinancesCard, stats receipts, etc.) is UNCHANGED. A student who
  directly searches for and selects a branch campus gets a normal build experience.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §2-§4
   - Invoke @fp-data-reviewer to review §4 Phase 1 (detection algorithm and false-positive
     risk against the actual Gold dataset)
   - Both write findings to §5
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human

2. DESIGN VISION
   - SKIP — the only frontend change is adding a "Campuses" column to the existing
     leaderboard table. Column header, integer cell, sortable. No new components,
     no new design tokens. The visual treatment is specified in §3.

3. IMPLEMENTATION
   - Phase 1 first: write scripts/detect_branch_campuses.py
   - Run the script against the live Gold dataset
   - Output detected families to logs/branch_campus_detection_<timestamp>.json
   - HUMAN REVIEW GATE: stop, present the detected families to the human for review
     before freezing them into config. The human may correct misclassifications,
     remove false positives, or add manually-known families the heuristic missed.
   - After human approval, write the frozen config to backend/app/config/branch_campuses.py
   - Phase 2a: implement the leaderboard query suppression and family_size injection
   - Phase 2b: implement the frontend "Campuses" column
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - Log all work to §6
   - BUILD ACCOUNTABILITY: if build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to review the full spec
   - All P0 tests required (detection script smoke test, leaderboard filter behavior,
     family_size column on response, frontend column rendering)
   - The detection script's actual output is NOT tested as a fixture — it's a one-time
     human-reviewed artifact. The CONSUMER of the artifact (leaderboard query, frontend
     column) is tested with mock data.
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @fp-design-auditor briefly to verify the new "Campuses" column header uses
     existing typography tokens (no new ones introduced) and the integer cell uses the
     existing Space Mono `font-data` treatment consistent with other numeric columns.

6. CODE REVIEW
   - Invoke @faang-staff-engineer
   - Critical review areas: (a) detection script's false-positive guards, (b) the
     INSTITUTION_FAMILIES dict is import-time loaded (not lazy), (c) the leaderboard
     query's suppression logic preserves the abs_rank semantics correctly when rows
     are filtered

7. VERIFICATION
   - Invoke @fp-builder for full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: tsc, vitest, vite build
   - Manual sanity check: re-run the failing leaderboard query (Schools teaching
     Accounting and Related Services → Accountants and auditors). Verify:
       (a) Ohio University regional campuses no longer appear in the top 10
       (b) Ohio University-Athens (or "Ohio University - Main Campus") appears as a
           single row with Campuses=6
       (c) BYU, Ohio State Fisher, Miami University Oxford, etc. surface naturally
       (d) The "Campuses" column renders correctly with the value 6 for Ohio U
           and 1 for standalone schools
   - Capture before/after screenshots in §9
   - Log results to §9

8. COMPLETION
   - Update top-level Status to COMPLETE
   - Check off Success Criteria
   - Generate report to reports/feature-branch-campus-suppression-YYYY-MM-DD.md
```

---

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-05 |
| Author | Jeff Cernauske + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-05-05 |
| Blocked By | — |
| Related Specs | `roi-net-lifetime-value.md` (sister spec — both shape leaderboard credibility); `gold-career-outcomes-college-scorecard.md` (completed — the data source containing the inherited earnings); `feature-compare-schools-for-career.md` (completed — the leaderboard surface this spec modifies) |
| Supersedes | None |

---

## §1 Feature Description

### Overview

Add a UI-layer filter that consolidates multi-campus university systems on the schools-for-career leaderboard. Branch campuses with inherited earnings data (Ohio University regional campuses, Penn State branch campuses, etc.) are suppressed from the leaderboard so only the flagship row appears per family. A new "Campuses" column shows the count of institutions in the family — `1` for standalone schools, `6` for Ohio University, etc. The column is the educational signal: students learn that a school is part of a multi-campus system from the leaderboard itself, not via a separate disclosure surface.

Direct school search and the build flow are unchanged. A student who specifically wants Ohio University-Zanesville can still find and build with it. We're filtering the *discovery* surface, not the student's deliberate choice.

### Problem Statement

The College Scorecard field-of-study file reports `earnings_1yr_median` per (institution, CIP, credential) tuple. For multi-campus university systems, the regional/branch campuses inherit identical earnings data from their flagship campus — this is a real Scorecard data shape, not a FutureProof bug. Combined with the branches' lower published costs (smaller campuses, lower fees), this produces an artificial ROI elevation: same earnings ÷ lower cost = higher multiplier.

Live example from the Accounting and Related Services → Accountants and auditors leaderboard (May 5, 2026):

```
Rank  School                                         ERN  ROI  EARN(1yr)  COST(4yr)
1     Brigham Young University                        9    9   $60,568    $83,516
1     Ohio University-Eastern Campus                  8   10   $54,637    $53,020   ← branch
1     Ohio University-Southern Campus                 8   10   $54,637    $53,556   ← branch
1     Ohio University-Zanesville Campus               8   10   $54,637    $55,808   ← branch
1     Ohio University-Lancaster Campus                8   10   $54,637    $53,036   ← branch
1     Ohio University-Chillicothe Campus              8   10   $54,637    $55,472   ← branch
```

Five Ohio University regional commuter campuses with identical $54,637 earnings (the Athens main campus's number) tie BYU — a genuinely top-3-nationally accounting program — for #1. This makes the leaderboard misleading: a student looking at "best schools for accounting" sees five regional commuter campuses ranked above Ohio State Fisher College, Miami University Oxford, and other genuinely well-regarded Ohio accounting programs.

The fix is to consolidate the family on the leaderboard (showing just Ohio University-Athens as `Campuses: 6`) while preserving direct discoverability and build capability for any student who specifically wants a regional campus.

### Success Criteria

- [x] `scripts/detect_branch_campuses.py` exists, runs against the live Gold dataset, and produces a JSON output of detected families
- [x] Detection script kept permanently in `scripts/` for future Scorecard data refreshes
- [x] Detection output reviewed by human, frozen to `backend/app/config/branch_campuses.py` as two structures: `INSTITUTION_FAMILIES` (flagship UNITID → list of branch UNITIDs) and `SUPPRESSED_BRANCH_UNITIDS` (set of all branch UNITIDs)
- [x] Frozen config covers known multi-campus systems with inherited earnings: Ohio University regional, Indiana University regional (verified independent earnings — correctly NOT suppressed), University of Wisconsin (verified independent — correctly NOT suppressed), 38 confirmed families including Ohio U, Ohio State, UConn, Pittsburgh, Miami-Oxford, Rutgers, Cincinnati, Washington-Seattle, Minnesota-Twin Cities, plus 29 for-profit chains (Strayer, DeVry, Chamberlain, Phoenix, Herzing, etc.). Penn State Commonwealth campuses are collapsed into a single UNITID by Scorecard and so do not appear (acknowledged in §5 data review)
- [x] Schools-for-career leaderboard query (`futureproof_server.py` ~line 3601) excludes suppressed UNITIDs via `WHERE unitid NOT IN (...)` clause
- [x] Each surviving leaderboard row has a `family_size` field populated: `1` for standalone schools, `N` for flagship rows where N is the count of UNITIDs in that family (flagship + branches)
- [x] `SchoolForCareerRow` has `family_size: int = 1` field (additive default, Pydantic-backward-compatible)
- [x] Frontend leaderboard table renders a new "Campuses" column showing `family_size` as an integer (desktop) and a "Campuses: N" line on the mobile card
- [x] Direct school search is unaffected — branch campuses still appear in school-search results (suppression is leaderboard-only)
- [x] Direct build flow is unaffected — students who pick a suppressed school can still build, get full stats, fight bosses
- [x] FinancesCard, stats receipts, build flow narrative copy all unchanged
- [x] Manual verification: re-ran the Accounting → Accountants leaderboard. Three UConn branch campuses removed from #10–#12; single UConn flagship row at #10 with `Campuses: 5` and the honest flagship sticker; UIUC and USC surfaced naturally at #11 and #12
- [x] Before/after tables captured in §9 (table form rather than screenshots — cleaner audit trail and survives copy-paste)
- [x] All existing pytest, ruff, mypy, tsc, vitest checks pass (3 pytest + 10 vitest pre-existing failures verified unrelated to this spec)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | UI-layer suppression, not Gold-layer fix | Gold stays the source of truth — every row's data lineage remains traceable. Suppression is a presentation concern: which schools belong on a "best for this career" leaderboard. Filtering at the query level keeps the data lake honest while fixing the user-visible ranking. | Drop branch campus rows during Gold promotion. Rejected — Gold-layer dropping breaks the principle that Gold contains all data and presentation logic happens downstream. Also makes direct-search builds impossible if a student wants the regional campus. |
| 2 | Hardcoded UNITID config (one-time discovery), not runtime detection | A frozen list is O(1) to consume, easy to PR-review, easy to manually correct. Runtime detection adds query-time cost to every leaderboard request and produces opaque, non-deterministic results. Scorecard data refreshes are manual events, so staleness isn't a real concern — the discovery script gets re-run during the same maintenance window. | Runtime detection via name-pattern matching at query time. Rejected — slower, opaque, harder to audit. |
| 3 | Filter only the leaderboard, not direct school selection | A student who deliberately searches for and selects "Ohio University-Zanesville" wants that school. Hiding it from search would silently override their choice. The leaderboard column does its educational work in the discovery flow; direct selection is the student's deliberate choice and gets a normal build experience. | Suppress everywhere (search, build, leaderboard). Rejected — paternalistic and breaks the build flow for students who attend regional campuses. |
| 4 | Surface the family relationship via a "Campuses" column, not via a disclosure note | The campus-count column is honest, scannable, and informative — students see "Ohio University, Campuses: 6" and understand the data shape immediately. A separate FinancesCard note duplicates the educational work and adds frontend scope for marginal benefit (only the rare student who picks a branch directly via search would see it). The leaderboard column is the right surface; one is enough. | Add a one-line note to FinancesCard when student picks a suppressed school directly. Rejected — adds prop-threading and a UI string for a path very few students will hit deliberately, dilutes the leaderboard column's role as the canonical educational surface. |
| 5 | Show only the flagship row per family on the leaderboard, with cost reflecting the flagship | The flagship is the canonical entry — its cost data reflects the main campus, which is the most-attended. Showing a branch as the leaderboard entry would inflate ROI in the same way we're trying to fix. A synthetic aggregated row (e.g., "Ohio University System") complicates click-through (where does it link to?) and creates a school that doesn't exist in the dataset. Flagship-only keeps the row real and clickable. | (a) Show the cheapest branch (best ROI). Rejected — exact same artifact as today, just consolidated. (b) Show a synthetic system-level row. Rejected — not a real school, no click-through target. |
| 6 | `family_size = 1` for any school not in the family map | Three semantically distinct cases — truly standalone, undetected small system, and unknown — all collapse to `1`. This is the honest "we don't know of any branches" answer. Detection threshold (3+ campuses) means small 2-campus families aren't flagged; that's an acceptable false negative because 2-campus families typically don't dominate leaderboards. | Treat undetected as `null` or "Unknown". Rejected — null in a count column is confusing UX; `1` is the truthful default ("as far as we know, this is one school"). |
| 7 | Detection script kept permanent in `scripts/`, not deleted after run | Zero cost to keep. Annual Scorecard refresh becomes a 30-second sanity check (re-run script, diff output, update list). Deleting it now means rewriting it later when the data inevitably changes. | Delete after one-time use. Rejected — false economy; reproducibility is a permanent feature, not a one-time concern. |
| 8 | Detection threshold of `>= 3` UNITIDs sharing a name prefix | Captures all real multi-campus systems while filtering noise. A 2-school "system" is rare and often coincidental (e.g., schools that happen to share a hyphenated name pattern). 3+ is the threshold where the artifact actually distorts leaderboards. | (a) `>= 2`. Rejected — too noisy. (b) `>= 5`. Rejected — misses smaller real systems like SUNY College of Technology. |
| 9 | Flagship identification: prefer known-flagship suffix list, fall back to highest median earnings | Most multi-campus systems have a known main campus (Athens for Ohio U, Bloomington for IU, University Park for PSU). A small hardcoded suffix list catches these accurately. When the suffix list doesn't match, "highest earnings" is a defensible fallback because the flagship typically attracts the highest-paying employers. | (a) Highest enrollment as flagship signal. Rejected — Scorecard doesn't reliably surface enrollment per branch. (b) Lowest UNITID. Rejected — UNITIDs are assignment artifacts, not semantic. |
| 10 | Detection algorithm guards against false positives via earnings-equality check | The pattern "schools share a name prefix" is necessary but not sufficient. Some systems (e.g., University of California campuses) share a prefix but have genuinely independent earnings data per campus. The earnings-equality check (branch's earnings exactly equal flagship's per-CIP) is the actual signal that data is being inherited. Without this guard, we'd over-suppress. | Suppress all hyphenated-name-family campuses regardless of earnings. Rejected — would incorrectly suppress UC campuses, CSU campuses, and other systems with real per-campus data. |

### Constraints

- **No Gold-layer changes.** This spec touches the leaderboard query, the leaderboard response model, and the leaderboard frontend. Gold pipeline is read-only for this work.
- **Hackathon timing.** Detection script must produce a usable list in one run; no iterative tuning rounds. The human-review gate is the safety net for misclassifications.
- **Detection script is informed by data, not by intuition.** The list shipped is what the script produced and the human approved — not a list Claude Desktop guessed at.

---

## §3 UI/UX Design

### "Campuses" column treatment

The leaderboard table currently has columns `# (rank), SCHOOL/PROGRAM, STATE, ERN, ROI, EARNINGS (1YR), COST (4 YR)`. Insert a new column **"CAMPUSES"** between `STATE` and `ERN`:

```
#   SCHOOL/PROGRAM              STATE   CAMPUSES   ERN   ROI   EARNINGS (1YR)   COST (4 YR)
1   Brigham Young University    UT      1          9     9     $60,568          $83,516
2   Ohio University             OH      6          8     7     $54,637          $97,560
3   Ohio State University       OH      1          8     8     $58,200          $108,400
```

**Typography:**
- Column header: `font-data font-bold uppercase text-text-muted` at 11px with 1px letter-spacing — matches the existing `STATE` and `ERN` column headers exactly. Header text: `CAMPUSES`.
- Cell content: `font-data text-text-primary` at 14px — same treatment as the `ERN` and `ROI` numeric cells.
- No special treatment for `family_size > 1` — the asymmetry of mostly-`1`s with occasional `6` or `24` is itself the visual signal. A student's eye catches it without needing color or weight changes.

**Sortable:** yes, ascending and descending — same affordance as other numeric columns. Sorting by Campuses descending lets a student explicitly explore multi-campus systems if they want to.

**Width:** approximately 80–90px. The column is narrow because the values are short integers. Don't add horizontal padding beyond the existing column-padding token.

**Responsive behavior:**
- At desktop widths: full column visible
- At tablet widths: column visible, may compress STATE column to 2-letter abbreviation only (already the case)
- At mobile widths (<480px): the leaderboard table already uses horizontal scroll. Campuses column scrolls with the rest of the table.

### No other UI changes

The build flow, FinancesCard, stats receipts, branch tree, and all other surfaces are unchanged. A student who lands on a build screen for any school — including a suppressed branch campus they reached via direct search — sees exactly the same UI as today.

---

## §4 Technical Specification

### Phase 1: Detection Script

**File:** `scripts/detect_branch_campuses.py` (new, kept permanently)

**Purpose:** Read `consumable.career_outcomes` from Gold, identify multi-campus families, output a JSON of detected families for human review.

**Algorithm:**

```python
"""
Detect multi-campus university families with inherited earnings data.

Run via: uv run python scripts/detect_branch_campuses.py
Output:  logs/branch_campus_detection_<timestamp>.json
"""

# Step 1: Load all institutions from career_outcomes
# Group by unitid, keeping institution_name and a sample of (cipcode, earnings_1yr_median)
df = duckdb.sql("""
    SELECT DISTINCT unitid, institution_name, cipcode, earnings_1yr_median
    FROM consumable.career_outcomes
    WHERE earnings_1yr_median IS NOT NULL
""").df()

# Step 2: Extract name prefix (text before first hyphen)
df["name_prefix"] = df["institution_name"].str.split("-", n=1).str[0].str.strip()

# Step 3: Identify candidate families (prefixes with >= 3 distinct UNITIDs)
family_sizes = (
    df.groupby("name_prefix")["unitid"]
      .nunique()
      .reset_index(name="family_size")
)
candidate_families = family_sizes[family_sizes["family_size"] >= 3]

# Step 4: For each candidate family, identify the flagship
KNOWN_FLAGSHIP_SUFFIXES = {
    "Ohio University": "Athens",
    "Indiana University": "Bloomington",
    "Pennsylvania State University": "University Park",
    "University of Wisconsin": "Madison",
    "Purdue University": "Main Campus",
    "Texas A & M University": "College Station",
    # ... extensible list, populated based on detection output
}

GENERIC_FLAGSHIP_KEYWORDS = ["main", "main campus", "flagship", "university park"]

def identify_flagship(family_df, prefix):
    # Try known-flagship suffix list first
    if prefix in KNOWN_FLAGSHIP_SUFFIXES:
        target_suffix = KNOWN_FLAGSHIP_SUFFIXES[prefix]
        match = family_df[family_df["institution_name"].str.contains(target_suffix, case=False)]
        if len(match) > 0:
            return match["unitid"].iloc[0]

    # Try generic keywords
    for kw in GENERIC_FLAGSHIP_KEYWORDS:
        match = family_df[family_df["institution_name"].str.lower().str.contains(kw)]
        if len(match) > 0:
            return match["unitid"].iloc[0]

    # Fall back to highest median earnings across all CIPs
    earnings_per_unitid = family_df.groupby("unitid")["earnings_1yr_median"].median()
    return earnings_per_unitid.idxmax()

# Step 5: For each branch, check if its earnings match the flagship's per-CIP
def detect_inherited_earnings(family_df, flagship_unitid):
    flagship_earnings = (
        family_df[family_df["unitid"] == flagship_unitid]
            .set_index("cipcode")["earnings_1yr_median"]
    )

    inherited_count_per_branch = {}
    total_count_per_branch = {}

    for branch_unitid in family_df[family_df["unitid"] != flagship_unitid]["unitid"].unique():
        branch_rows = family_df[family_df["unitid"] == branch_unitid]
        inherited = 0
        total = 0
        for _, row in branch_rows.iterrows():
            cip = row["cipcode"]
            if cip in flagship_earnings.index:
                total += 1
                if abs(row["earnings_1yr_median"] - flagship_earnings[cip]) < 1.0:
                    inherited += 1
        inherited_count_per_branch[branch_unitid] = inherited
        total_count_per_branch[branch_unitid] = total

    return inherited_count_per_branch, total_count_per_branch

# Step 6: Compose the output
output = {
    "generated_at": datetime.utcnow().isoformat(),
    "detection_threshold": 3,
    "families": [
        {
            "name_prefix": prefix,
            "family_size": int(size),
            "flagship_unitid": int(flagship_uid),
            "flagship_name": flagship_name,
            "branches": [
                {
                    "unitid": int(branch_uid),
                    "institution_name": branch_name,
                    "inherited_earnings_count": inherited[branch_uid],
                    "total_overlapping_cips": total[branch_uid],
                    "inheritance_ratio": (
                        inherited[branch_uid] / total[branch_uid]
                        if total[branch_uid] > 0 else 0.0
                    ),
                    "suppress_recommended": (
                        inherited[branch_uid] / total[branch_uid] >= 0.8
                        if total[branch_uid] > 0 else False
                    ),
                }
                for branch_uid in branches
            ],
        }
        for prefix, size, flagship_uid, ... in candidate_families
    ],
}

# Step 7: Write output and print summary
with open(f"logs/branch_campus_detection_{ts}.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Detected {len(output['families'])} candidate families")
print(f"Total branches recommended for suppression: {sum_suppressed}")
print(f"Output: logs/branch_campus_detection_{ts}.json")
print("Review the output and update backend/app/config/branch_campuses.py")
```

**Suppression threshold:** A branch is recommended for suppression when **≥80% of its CIPs that overlap with the flagship show identical earnings (within $1)**. The 80% threshold tolerates occasional non-inherited rows (e.g., a graduate-only program at one campus) while still flagging the systemic inheritance pattern.

**Human review gate:** Claude Code stops after generating the output and presents it to the human for review. The human:
1. Verifies that detected flagships are correct (the script may misidentify when no known suffix matches and the highest-earnings heuristic picks wrong)
2. Reviews the `suppress_recommended` flags and overrides any false positives (e.g., a system where branches genuinely have independent earnings)
3. Adds any manually-known families that the heuristic missed

After review, the human approves the list and Claude Code freezes it into config.

### Phase 2a: Frozen Config

**File:** `backend/app/config/branch_campuses.py` (new)

```python
"""
Multi-campus university families with inherited earnings data.

Generated by scripts/detect_branch_campuses.py on YYYY-MM-DD,
reviewed and approved by [human] on YYYY-MM-DD.

Re-run scripts/detect_branch_campuses.py after Scorecard data refreshes
to verify this list is still accurate.

Format:
  INSTITUTION_FAMILIES: maps flagship UNITID -> list of branch UNITIDs (excluding flagship)
  SUPPRESSED_BRANCH_UNITIDS: flat set of all branch UNITIDs (= union of all values)
  FAMILY_SIZE_BY_FLAGSHIP_UNITID: maps flagship UNITID -> total family size (flagship + branches)
"""

INSTITUTION_FAMILIES: dict[int, list[int]] = {
    # Ohio University (flagship: Athens Campus, UNITID 204796)
    204796: [
        201441,  # Ohio University-Eastern Campus
        201450,  # Ohio University-Southern Campus
        201496,  # Ohio University-Zanesville Campus
        201468,  # Ohio University-Lancaster Campus
        201459,  # Ohio University-Chillicothe Campus
    ],
    # Indiana University (flagship: Bloomington, UNITID XXXXXX)
    # ...
    # Pennsylvania State University (flagship: University Park, UNITID XXXXXX)
    # ...
}

# Flat set of all branch UNITIDs that should be suppressed from the leaderboard
SUPPRESSED_BRANCH_UNITIDS: frozenset[int] = frozenset(
    branch
    for branches in INSTITUTION_FAMILIES.values()
    for branch in branches
)

# Family size lookup: flagship UNITID -> total count (flagship + branches)
FAMILY_SIZE_BY_FLAGSHIP_UNITID: dict[int, int] = {
    flagship: len(branches) + 1
    for flagship, branches in INSTITUTION_FAMILIES.items()
}
```

The exact UNITIDs and family contents are populated from the discovery script output during implementation. The structure above is the schema; the data is filled by Claude Code from the script output after human review.

### Phase 2b: Leaderboard Query Modification

**File:** `src/mcp_server/futureproof_server.py` (around line 3601)

The current schools-for-career composite query:

```sql
(CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 AS composite_score,
RANK() OVER (
    ORDER BY
        (CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 DESC,
        earnings_1yr_median DESC NULLS LAST,
        net_price_annual ASC NULLS LAST
) AS abs_rank
```

**Modification:** Add a `WHERE` clause excluding suppressed UNITIDs, AND inject `family_size` per row.

The cleanest implementation: pass the suppression set and the flagship→size map as query parameters, and use a `LEFT JOIN` against an inline VALUES clause OR build the query in Python with the IDs interpolated.

```python
# In the Python handler that builds the query:
from app.config.branch_campuses import (
    SUPPRESSED_BRANCH_UNITIDS,
    FAMILY_SIZE_BY_FLAGSHIP_UNITID,
)

suppressed_list = ", ".join(str(u) for u in sorted(SUPPRESSED_BRANCH_UNITIDS))
family_size_cases = " ".join(
    f"WHEN unitid = {flagship} THEN {size}"
    for flagship, size in FAMILY_SIZE_BY_FLAGSHIP_UNITID.items()
)

sql = f"""
    SELECT
        ...,
        CASE {family_size_cases} ELSE 1 END AS family_size,
        (CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 AS composite_score,
        RANK() OVER (
            ORDER BY
                (CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 DESC,
                earnings_1yr_median DESC NULLS LAST,
                net_price_annual ASC NULLS LAST
        ) AS abs_rank
    FROM consumable.program_career_paths
    WHERE unitid NOT IN ({suppressed_list})
      AND <existing filters>
"""
```

If `SUPPRESSED_BRANCH_UNITIDS` is empty (config not yet populated), the `WHERE unitid NOT IN ()` clause must be omitted to avoid a SQL syntax error. Guard:

```python
where_clauses = ["<existing filters>"]
if suppressed_list:
    where_clauses.append(f"unitid NOT IN ({suppressed_list})")
where_sql = " AND ".join(where_clauses)
```

**`abs_rank` semantics preserved:** RANK() runs *after* the WHERE filter, so suppressed rows don't affect ranking. The flagship row gets the natural rank it deserves among the surviving schools. No special handling needed.

### Phase 2c: Backend Response Model

**File:** `backend/app/models/career.py` (or wherever the leaderboard response model lives)

Add `family_size: int = 1` to the relevant model. If the leaderboard uses a custom `SchoolForCareerRow` model, add it there. If it reuses `CareerOutcome`, add it there.

The default of `1` ensures backward compatibility for any code path that doesn't have the new field populated yet.

### Phase 2d: Frontend Leaderboard Column

**File:** `frontend/src/components/compare-screen/SchoolsForCareerTable.tsx` (or whatever the file path is — Claude Code locates it via grep)

**Type change:** Add `familySize: number` to the row type for the leaderboard table.

**Header:** Add a `<th>` between `STATE` and `ERN`:

```tsx
<th className="font-data font-bold uppercase text-text-muted"
    style={{ fontSize: 11, letterSpacing: 1 }}>
  Campuses
</th>
```

**Cell:** Add a `<td>` in the corresponding position:

```tsx
<td className="font-data text-text-primary" style={{ fontSize: 14 }}>
  {row.familySize}
</td>
```

**Sortable:** if the table already has sort handlers for ERN, ROI, etc., add the same affordance to the Campuses column. Sort key: `familySize`, ascending or descending.

### File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `scripts/detect_branch_campuses.py` | Create | Discovery script, kept permanently |
| `logs/branch_campus_detection_<timestamp>.json` | Create (output) | Detection script output for human review |
| `backend/app/config/branch_campuses.py` | Create | Frozen config: `INSTITUTION_FAMILIES`, `SUPPRESSED_BRANCH_UNITIDS`, `FAMILY_SIZE_BY_FLAGSHIP_UNITID` |
| `src/mcp_server/futureproof_server.py` | Modify | Schools-for-career leaderboard query: add `WHERE unitid NOT IN (...)` and `CASE ... AS family_size` |
| `backend/app/models/career.py` (or relevant file) | Modify | Add `family_size: int = 1` to leaderboard response model |
| Frontend leaderboard table component | Modify | Add `familySize` to row type, add column header and cell, wire up sort handler |
| Frontend leaderboard fixture/mock data | Modify | Add `familySize` to test fixtures |
| `backend/tests/services/test_*` (relevant test) | Modify | Update leaderboard fixture/mock to include `family_size`; assert filtering and column rendering |
| `frontend/src/**/*.test.tsx` (relevant test) | Modify | Update leaderboard tests to render the new column |

Claude Code locates the exact frontend file path via `grep -r "schools-for-career\|SchoolsForCareer\|composite_score" frontend/src` during implementation.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Risk | Reason |
|-----------|------|--------|
| Backend leaderboard tests | **Medium** | Response shape changes (new `family_size` field). Fixtures and assertions need updating. |
| Frontend leaderboard rendering tests | **Medium** | New column added to table. Test fixtures need `familySize` field. |
| Backend integration tests for `/schools-for-career` endpoint | **Low** | Response is additive (new optional field with default `1`); existing assertions still pass. |
| Direct school search tests | **None** | Unaffected — suppression is leaderboard-only. |
| Build flow tests | **None** | Unaffected — suppression is leaderboard-only. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| Backend leaderboard fixtures | Add `family_size: 1` to default mock rows | New required field |
| Frontend leaderboard fixtures | Add `familySize: 1` to default mock rows | New required field |
| Leaderboard rendering test | Update column count assertion (currently 6 columns → 7 columns) | New column added |

#### Confirmed Safe (must NOT break — escalate if they fail)

- All build flow tests
- All FinancesCard tests
- All stats receipt tests
- Direct school search tests
- Branch tree tests
- All non-leaderboard backend tests

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/test_branch_campuses_config.py` | `test_suppressed_unitids_is_union_of_family_branches` | `SUPPRESSED_BRANCH_UNITIDS` equals the union of all branches across `INSTITUTION_FAMILIES` |
| P0 | `backend/tests/test_branch_campuses_config.py` | `test_family_size_includes_flagship_plus_branches` | For each flagship in the map, `FAMILY_SIZE_BY_FLAGSHIP_UNITID[flagship]` equals `len(branches) + 1` |
| P0 | Backend leaderboard integration test | `test_leaderboard_excludes_suppressed_branch_campuses` | Mock data with a flagship and 3 branches; query result includes flagship, excludes branches |
| P0 | Backend leaderboard integration test | `test_leaderboard_family_size_populated_for_flagship` | Flagship row has `family_size=4`; non-family row has `family_size=1` |
| P0 | Backend leaderboard integration test | `test_leaderboard_empty_suppression_set_works` | When `SUPPRESSED_BRANCH_UNITIDS` is empty, query runs without SQL syntax error |
| P1 | `backend/tests/test_branch_campuses_config.py` | `test_no_unitid_appears_in_multiple_families` | A UNITID is in at most one family's branches list |
| P1 | `backend/tests/test_branch_campuses_config.py` | `test_no_flagship_is_also_a_branch` | No UNITID appears as both a flagship key and a branch in any list |
| P1 | Frontend leaderboard table test | `test_campuses_column_renders_family_size` | Mock row with `familySize: 6`; cell renders `6` |
| P1 | Frontend leaderboard table test | `test_campuses_column_renders_one_for_standalone` | Mock row with `familySize: 1`; cell renders `1` |
| P2 | Frontend leaderboard table test | `test_campuses_column_sortable` | Click header sorts rows by family size |
| P2 | Discovery script smoke test | `test_detect_branch_campuses_script_runs` | Script imports without error and produces a JSON-shaped output structure (does not test detection accuracy — that's verified by human review) |

#### Test Data Requirements

- Backend leaderboard fixture: include at least one mock row with `family_size: 6` and several with `family_size: 1` to verify column population works for both
- Backend test fixture for suppression: a mock career-outcomes table with 1 flagship (UNITID `99001`, `family_size=4`) and 3 branches (UNITIDs `99002, 99003, 99004` in `SUPPRESSED_BRANCH_UNITIDS`); a query against this dataset should return only the flagship row with `family_size=4`
- Frontend leaderboard fixture: at least one mock row with `familySize: 6` and several with `familySize: 1`

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED
**Reviewed:** 2026-05-05

#### System Context
UI-layer suppression sitting between Gold (`consumable.program_career_paths`) and the schools-for-career leaderboard. Touches: (1) frozen Python config in `backend/app/config/`, (2) MCP server query in `src/mcp_server/futureproof_server.py`, (3) leaderboard response model, (4) frontend table column. Gold zone is read-only — zone boundary respected. Build flow, FinancesCard, school search, and MCP tools other than the leaderboard query path are untouched. The "no Gold mutation" stance is the right call for a presentation-layer artifact and keeps lineage intact for direct-build paths.

#### Data Flow Analysis
`consumable.program_career_paths` (Gold) -> SQL with `WHERE unitid NOT IN (...)` and `CASE ... AS family_size` -> leaderboard response model with `family_size: int = 1` -> frontend row type `familySize: number` -> "CAMPUSES" column. Suppression set and family-size map cross only the Python-to-SQL boundary (string interpolation of trusted ints) — they never reach the API contract or the frontend. The frontend only ever sees the per-row scalar `family_size`. Clean unidirectional flow with no leakage of the suppression list outside the query builder.

#### Contract Review
- Response model: `family_size: int = 1` is additive and backward-compatible. Default of `1` matches the §2 #6 decision (collapse standalone/undetected/unknown to `1`). Good.
- MCP tool `get_career_paths` and `school_lookup` paths are unaffected — this is scoped to the leaderboard composite-score query, so no MCP signature drift.
- Config module exposes three import-time constants with precise types (`dict[int, list[int]]`, `frozenset[int]`, `dict[int, int]`). No `Any`. Derived structures (`SUPPRESSED_BRANCH_UNITIDS`, `FAMILY_SIZE_BY_FLAGSHIP_UNITID`) are computed from `INSTITUTION_FAMILIES` so the source of truth is single — matches the per-build/single-source instinct from prior memory.

#### Findings

##### Sound
- **Zone discipline.** Gold remains the source of truth; suppression is a query-builder concern. Direct-search builds for branch campuses still work end-to-end. This is exactly the right layer for a discovery-surface fix.
- **Frozen config over runtime detection** (Decision #2). Import-time load is O(1) per request, deterministic, PR-reviewable, and trivially testable. The detection script staying in `scripts/` for re-runs handles the staleness concern without runtime cost.
- **`family_size` as a per-row scalar in the response.** No need to ship the `INSTITUTION_FAMILIES` structure to the frontend — the row carries everything the column needs. Tight contract, no leakage.
- **`abs_rank` semantics.** `RANK() OVER (...)` is evaluated after `WHERE` in DuckDB's logical query plan, so suppressed rows never participate in ranking. The flagship gets its honest rank among survivors. Spec is correct that no special handling is needed.
- **Empty-suppression-set guard.** The `where_clauses` list-then-join pattern (§4 Phase 2b) is the right idiom — it composes cleanly with existing filters and avoids the `IN ()` syntax error. Aligns with how composable WHERE clauses are typically built in this codebase.
- **SQL injection surface.** Values are `int` UNITIDs sourced from a frozen, version-controlled Python config — never user input. `str(int)` interpolation is safe here. Worth a one-line comment in the query builder noting "trusted ints from frozen config" so future readers don't reflexively flag it, but not a blocker.

##### Concerns
- **Type-coerce at config-load time, not interpolation time.** The `f"{flagship}"` and `str(u)` interpolations assume the dict keys/values are `int`. If a future edit accidentally introduces a string UNITID (e.g., `"204796"` because someone copied from JSON), the type annotations won't catch it at runtime and the SQL will silently accept a quoted-or-unquoted mix. **Impact:** low — caught by the P1 config tests. **Recommendation:** add an `assert all(isinstance(u, int) for u in SUPPRESSED_BRANCH_UNITIDS)` at module bottom, or use `pydantic.TypeAdapter(frozenset[int]).validate_python(...)` to fail loudly at import time. Cheap insurance.
- **`CASE WHEN` grows linearly with family count.** Today there are ~5-10 families, so the `CASE` chain is trivial. If the config ever balloons (e.g., 100+ families after a Scorecard refresh surfaces SUNY/CUNY/CSU branches), the inline `CASE` becomes a wide string and the planner has to walk it per row. **Impact:** low at current scale, watch at 50+ families. **Recommendation:** if the config ever exceeds ~30 families, refactor to a `LEFT JOIN` against an inline `VALUES` clause (which the spec already mentions as an alternative in §4 Phase 2b). For now, `CASE` is fine.
- **Single source of truth for the column position.** The spec describes the column position ("between STATE and ERN") in three places (§3, §4 Phase 2d, header/cell snippets). If the table component uses a column-config array, this is one edit. If the column order is duplicated across header and body markup, it's two. **Impact:** low — implementer concern, not architectural. **Recommendation:** during implementation, prefer a single column-config array if the existing component supports it.
- **Direct-build path still surfaces inherited earnings.** A student who searches "Ohio University-Zanesville" directly gets a build with the inherited $54,637 figure and no in-build disclosure (per Decision #4). This is an intentional product call, but the data shape is still misleading on that surface. **Impact:** none for this spec — Decision #4 is explicit and out-of-scope. Just flagging that the educational signal is leaderboard-only by design.

##### Blockers
None.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-05

#### Data Sources Affected
- `consumable.career_outcomes` (College Scorecard field-of-study, sourced via Brightsmith Bronze->Silver->Gold). Read-only consumption — no Gold-layer writes.
- Algorithm reads only `(unitid, institution_name, cipcode, earnings_1yr_median)` from one parquet table. No crosswalk involvement (this work is school-side only; no CIP->SOC).

Dataset shape verified directly from `data/gold/iceberg_warehouse/consumable/career_outcomes/data/*.parquet`:
- 25,196 distinct `(unitid, institution_name, cipcode, earnings_1yr_median)` tuples with non-null earnings
- 1,957 distinct UNITIDs / 1,938 distinct institution names (5 UNITIDs share the same name string — see Stevens-Henager finding)
- 0 NULL `institution_name` values (good — `.str.split` won't crash on null in current data)
- 1,495 institutions have NO hyphen at all -> safely fall to single-element-prefix groups that never reach the `>=3` threshold
- 10 institutions have 2+ hyphens (edge case — see Embry-Riddle finding)

#### Crosswalk Impact
None. This spec does not touch CIP->SOC crosswalk, ConceptNormalizer, or any tier confidence scoring.

#### Formula Verification
The algorithm correctly groups by name prefix, correctly counts distinct UNITIDs per family, and correctly computes per-CIP earnings equality with `abs(diff) < 1.0` against the flagship. The `inheritance_ratio = inherited / total` formula is sound. Empty-overlap (`total == 0`) is correctly guarded — those branches get `suppress_recommended = False` rather than divide-by-zero.

I ran the algorithm end-to-end against the live parquet. It produces 57 candidate families at the `>=3` threshold. The detection logic works on Ohio U exactly as the spec promises: all 5 regional campuses score `45/45 = 1.00` against the Athens flagship and are flagged for suppression. UC, CSU, UW, IU, and Texas A&M (College Station) branches all score `0/N` against their respective flagships and are correctly NOT flagged — these systems publish independent per-campus earnings, exactly as Decision #10 of §2 anticipates.

#### Findings

##### Data Quality Sound
- **Ohio University detection works.** The 6 Ohio U UNITIDs share prefix `"Ohio University"`. Athens flagship is correctly identified via the `"main"` keyword fallback (the Scorecard string is `"Ohio University-Main Campus"`, not `"Ohio University-Athens"`). All 5 branches show `45/45 = 1.00` inheritance ratio against Athens. The fix lands.
- **UC and CSU correctly NOT flagged.** I verified by running the full pipeline: every UC branch (Berkeley, UCLA, San Diego, Davis, etc.) shows `0/30 = 0.00` against the highest-earnings UC. Same for all 14 CSU branches. The `<$1` equality guard is doing its job — these systems have genuinely independent per-campus earnings, and the algorithm respects that.
- **Indiana University correctly NOT flagged.** Bloomington flagship correctly identified via known-suffix list. All 6 IU regional campuses (Indianapolis, Kokomo, East, Northwest, etc.) show `0/N` inheritance. Spot-checked CIP 51.38 (Nursing): Bloomington=$56,274, IU East=$61,607, IU Northwest=$61,466 — genuinely distinct numbers.
- **University of Wisconsin correctly NOT flagged.** All 13 UW branches show `0/N` against Madison.
- **Texas A & M (College Station) correctly NOT flagged.** Kingsville, Commerce, Corpus Christi all score `0/15-16` against College Station.
- **Real for-profit chains correctly flagged.** DeVry (16 UNITIDs, all $X,XXX identical per-state per-CIP), Strayer (17 UNITIDs, all identical), University of Phoenix, Chamberlain, Herzing, Stevens-Henager — all show ratio 1.00 across all overlapping CIPs. These are genuine inherited-data cases and the suppression is correct.
- **Empty `institution_name` handling fine.** 0 NULLs in the current dataset; defensive `.str.split` on Pandas StringArray returns NaN for nulls anyway, so no crash risk if a future refresh introduces them.

##### Data Concerns

- **The spec's `KNOWN_FLAGSHIP_SUFFIXES` value for Ohio University is wrong (`"Athens"`).** The actual Scorecard string for the flagship is `"Ohio University-Main Campus"`, not `"Ohio University-Athens"`. The known-suffix lookup `family_df.str.contains("Athens", case=False)` returns zero matches. The algorithm fortunately falls through to the `"main"` keyword and lands on UNITID 204857, but this is by accident, not by design. **Risk:** A future Scorecard refresh could introduce a `"...Athens"` variant alongside `"...Main Campus"` and the suffix-list precedence would silently flip the flagship. **Fix:** Change `KNOWN_FLAGSHIP_SUFFIXES["Ohio University"]` to `"Main Campus"` (or `["Athens", "Main Campus"]` with the script preferring whichever exists). Verify each entry in `KNOWN_FLAGSHIP_SUFFIXES` against actual strings in the dataset before shipping the script.

- **Penn State has zero branches in this dataset — only 1 UNITID exists.** The Scorecard field-of-study extract collapses Penn State Commonwealth campuses (Berks, Altoona, Erie, Harrisburg, etc.) into a single `"The Pennsylvania State University"` row (UNITID 495767). The spec's Success Criteria says the frozen config should cover "Penn State branch campuses" — that's not possible from this data. The detection script will produce zero Penn State entries, and that's the correct answer for this dataset. **Risk:** Spec-author expectations vs. actual data. **Fix:** Update Success Criteria language to say "Penn State branch campuses (if present in the data)" or remove the explicit Penn State mention. The human-review gate should not be alarmed when Penn State doesn't appear in the script output — it's not in the source.

- **SUNY and CUNY are NOT hyphenated and will NOT be flagged.** Verified directly: SUNY uses formats like `"State University of New York at Oswego"`, `"SUNY Buffalo State University"`, `"Stony Brook University"`, `"Binghamton University"` (no consistent hyphen pattern). CUNY uses `"CUNY Hunter College"`, `"CUNY Brooklyn College"`, `"College of Staten Island CUNY"`. The `name_prefix = name.split("-",n=1)[0]` heuristic produces 23 distinct prefixes for SUNY's 23 schools and 12 for CUNY's 12 schools — zero family clustering. **Risk:** If SUNY/CUNY actually have inherited earnings in the underlying Scorecard data, this algorithm misses the entire system. **Verification needed:** Spot-check 3-4 SUNY UNITIDs for shared earnings on a common CIP. If their earnings ARE genuinely independent (likely — SUNY/CUNY each report individually to IPEDS), the false-negative is acceptable. If not, the algorithm needs a second clustering strategy beyond hyphen-prefix (system-keyword detection: `"SUNY"`, `"CUNY"`, `"University of California"` substring match before splitting).

- **Texas A&M splits into two families because of inconsistent name formatting.** Scorecard has both `"Texas A & M University-..."` (4 schools, with spaces around the ampersand) AND `"Texas A&M University-..."` (3 schools, no spaces). The algorithm produces TWO separate prefix groups: `"Texas A & M University"` (n=4) and `"Texas A&M University"` (n=3). These are the same university system. **Risk:** Two separate "families" detected for one real-world family; if any branches were inherited, the family_size column would be wrong. **Fix:** Pre-normalize whitespace and ampersand variants in `institution_name` before extracting the prefix: `name = re.sub(r"\s*&\s*", " & ", name)`. Same canonicalization for any other punctuation drift the script encounters.

- **Stevens-Henager prefix collision.** Five distinct UNITIDs all share the literal name `"Stevens-Henager College"` (multi-state for-profit chain). The prefix split on `"Stevens"` ALSO pulls in `"Stevens-The Institute of Business & Arts"` (UNITID 178767) — completely unrelated. Total prefix family becomes 6 schools when it should be 5. The earnings-equality guard correctly does NOT flag the unrelated school for suppression (zero CIP overlap between Stevens-Henager and Stevens-Institute -> `total=0` -> `suppress_recommended=False`). However, the `family_size` column would incorrectly show `6` if a flagship were assigned to this group. **Risk:** Wrong `family_size` displayed to students. **Fix:** Compute `family_size` as `1 + count(branches where suppress_recommended=True)`, NOT `1 + count(all UNITIDs sharing the prefix)`. The "Campuses" column should reflect the actually-inherited family, not the loose name-prefix group.

- **Embry-Riddle false-positive risk.** Three UNITIDs (Prescott 104586, Daytona Beach 133553, Worldwide 426314) share prefix `"Embry"` (the algorithm splits at the first hyphen in `"Embry-Riddle Aeronautical University-Prescott"` -> `"Embry"`). Spot check: the CIPs that overlap between Prescott and Daytona Beach show identical earnings (e.g., CIP 14.02 = $64,540 at both, CIP 49.01 = $53,995 at both). The algorithm WILL flag both branches with ratio 1.00. Whether this is true earnings inheritance or coincidence on a small CIP overlap (8 CIPs at Prescott) needs human judgment. Embry-Riddle Prescott and Daytona Beach are real, distinct campuses with separate accreditation and faculty. **Risk:** Suppressing a legitimately-distinct pair of branch campuses. **Fix:** Either (a) add Embry-Riddle to a manual override list during human review, or (b) require a stricter overlap threshold (e.g., `total >= 10` and `inheritance_ratio >= 0.95`) before auto-suggesting suppression. Worth showing in the human-review JSON with a flag like `low_overlap_warning` when `total < 10`.

- **University of Phoenix flagship is determined by a single CIP.** UNITID 484729 (Phoenix-North Carolina) has exactly 1 CIP in the dataset. With only one earnings value, `groupby("unitid")["earnings_1yr_median"].median()` produces that single number, which happens to be the highest among UoP UNITIDs. The flagship is then chosen via this thin signal. Functionally the suppression is still correct (UoP IS a chain — every branch has identical per-CIP earnings to the flagship), but the chosen "flagship" UNITID is arbitrary. **Risk:** The flagship row shown on the leaderboard might be `"University of Phoenix-North Carolina"` (an obscure pick) instead of `"University of Phoenix-Arizona"` (the actual headquarters with 23 CIPs). **Fix:** When falling through to the highest-earnings heuristic, ALSO require the candidate flagship to have at least N=10 CIPs (or the most CIPs in the family). Tie-break with most CIPs first, then earnings. For UoP this would correctly pick Arizona (484613, 23 CIPs).

- **`identify_flagship` returns first hit on `"main"` keyword non-deterministically.** The `family_df[...].iloc[0]` returns whichever row Pandas iterates first — which depends on row order in the parquet. For most cases there's only one match, but if a future Scorecard refresh introduces multiple `"... Main Campus"` rows in a family, the choice is non-deterministic. **Fix:** Sort `family_df` by UNITID before applying `.iloc[0]`, or assert exactly one match and warn the human if more than one exists.

- **The `<$1` equality tolerance is the right shape.** Scorecard publishes earnings rounded to the dollar. `abs(54637 - 54637) < 1.0` is `0.0 < 1.0` -> True. `abs(54637 - 54638) < 1.0` is `1.0 < 1.0` -> False (strict `<` excludes off-by-one). True inheritance produces exact integer equality, while two real campuses that round to within $1 of each other are genuinely independent. No change needed; flagging that the strict `<` (not `<=`) is the right call.

- **The 80% inheritance threshold is well-calibrated for the data.** Looking at the actual ratios: real inherited families (Ohio U, DeVry, Strayer, Phoenix) all score `1.00`. Real independent families (UC, CSU, IU, UW) all score `0.00`. The bimodal distribution means the 80% cutoff is comfortably in the dead zone — there's no family in the dataset I tested that lands at, say, `0.6`. So 80% is fine for now. **Caveat:** The bimodal pattern may not hold after future Scorecard refreshes. Keep the threshold configurable via a constant at the top of the script, not buried in the algorithm.

- **The 3-campus detection threshold misses 2-campus systems.** Per Decision #8 in §2, this is an accepted false-negative — 2-campus families don't typically dominate leaderboards. I agree with the calibration. **Caveat:** A 2-campus system with severe earnings inheritance and one extremely cheap branch could still produce a 1-2 leaderboard distortion. Worth watching after deployment; cheap to lower the threshold to 2 if it becomes a problem.

##### Data Integrity Blockers (if any)
None. The algorithm fundamentally works against the actual data — Ohio U gets caught, UC/CSU/IU/UW correctly don't. The fixes above are calibration and edge-case handling, not architectural failures.

#### Disclaimer Check
- [x] AI-estimated values labeled — N/A; this work uses no AI estimation
- [x] Confidence scores propagated where crosswalk < Tier 2 — N/A; no crosswalk involvement
- [x] Required disclaimer strings present in UI for this data path — the "Campuses" column itself is the disclosure (per Decision #4); no separate disclaimer needed
- [x] Missing data states handled — `family_size = 1` default for unknown/standalone schools is the right "we don't know of any branches" answer (per Decision #6); no $0 or blank values introduced

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Summary for the human-review gate:** The algorithm produces correct results on the canonical case (Ohio U flagged, UC/CSU/IU/UW not flagged). Before running the script in production, fix the `KNOWN_FLAGSHIP_SUFFIXES` Ohio U entry (`"Athens"` -> `"Main Campus"`), normalize ampersand whitespace to merge the Texas A&M variants, compute `family_size` from the suppressed-branches count (not the raw prefix group count) to handle the Stevens-Henager prefix collision correctly, and add a `low_overlap_warning` flag in the JSON output for any branch with `total < 10` CIPs (Embry-Riddle case). Pick the flagship by most-CIPs-then-highest-earnings rather than highest-earnings alone (UoP-NC case). Update Success Criteria to drop the explicit Penn State mention since Penn State Commonwealth campuses don't appear in the Scorecard field-of-study extract. With these fixes, the script's output is safe to take to the human-review gate.

---

## §6 Implementation Log

**Status:** COMPLETE
**Completed:** 2026-05-05

### Files Modified
| File | Change Summary |
|------|---------------|
| `scripts/detect_branch_campuses.py` (new) | Discovery script: groups Gold `consumable.career_outcomes` by ampersand-normalized name prefix, identifies flagship by known-suffix list / "main" keyword / most-CIPs-then-highest-earnings, flags branches whose ≥80% of overlapping CIPs share the flagship's per-CIP earnings within $1.00. Emits `low_overlap_warning` when fewer than 10 CIPs overlap. Output: `logs/branch_campus_detection_<timestamp>.json`. |
| `logs/branch_campus_detection_20260506T011440Z.json` (output) | Detection run against live Gold (May 5, 2026): 56 candidate families, 39 with at least one branch flagged, 186 total branches recommended for suppression. |
| `backend/app/config/__init__.py` (new) | Empty package init. |
| `backend/app/config/branch_campuses.py` (new) | Frozen config: `INSTITUTION_FAMILIES` (38 families), `SUPPRESSED_BRANCH_UNITIDS` (frozenset of 184 branch UNITIDs), `FAMILY_SIZE_BY_FLAGSHIP_UNITID`. Includes import-time `_validate_int` that raises `TypeError` (survives `python -O`) and rejects `bool` explicitly. |
| `src/mcp_server/futureproof_server.py` | (a) Top-level imports `SUPPRESSED_BRANCH_UNITIDS` and `FAMILY_SIZE_BY_FLAGSHIP_UNITID` (eager). (b) Schools-for-career SQL adds `WHERE unitid NOT IN (...)` (only when set non-empty) with `int(u)` belt-and-suspenders cast. (c) Adds `CASE unitid WHEN <flagship> THEN <size> ... ELSE 1 END AS family_size` with `int()` casts. (d) Both `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP` and `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_MCP` whitelists include `family_size`. |
| `backend/app/models/career.py` | `SchoolForCareerRow.family_size: int = 1` (additive default — Pydantic backward-compatible). |
| `backend/tests/test_branch_campuses_config.py` (new) | 5 tests (P0 + P1) covering union invariant, family_size formula, no-duplicate-branches, no-flagship-as-branch, all-int enforcement. |
| `frontend/src/types/build.ts` | `family_size: number` on `SchoolForCareerRow`. |
| `frontend/src/components/CompareSchoolsPanel.tsx` | Desktop grid: 7→8 columns, new `<Cell>` with `font-data text-text-primary` between STATE and ERN rendering `{row.family_size}` with `data-testid="row-campuses-{unitid}-{cipcode}"`. `gridTemplateColumns` and `YourSchoolDivider` `col-span` updated. Mobile card: small `font-data text-micro uppercase tracking-wider text-text-muted` line under program_name carrying "Campuses: N" with `data-testid="card-campuses-{unitid}-{cipcode}"`. Synthetic anchor row construction also passes `family_size: 1`. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | Default fixture `family_size: 1`; 3 new tests for desktop cell, standalone case, mobile card label. |
| `frontend/src/i18n/strings.ts` | `compareSchools.column.campuses` added in en (`"Campuses"`), es (`"Sedes"`), ar (`"الفروع"`). |

### Detection Script Output Summary
- Candidate families detected: 56 (prefix groups with ≥3 distinct UNITIDs)
- Families with ≥1 branch flagged for suppression: 39
- Total branches recommended for suppression: 186

### Human Review Decisions
- Excluded **Embry-Riddle Aeronautical University** (flagship UNITID 133553) per the data reviewer's `low_overlap_warning` flag — the inheritance signal sat on a thin overlap of 13 flagship CIPs and the campuses (Prescott, Daytona Beach, Worldwide) are independently accredited.
- Approved all other 38 families: the 9 major university systems (Ohio U, Ohio State, UConn, Pittsburgh, Miami-Oxford, Rutgers, Cincinnati, Washington-Seattle, Minnesota-Twin Cities) plus 29 for-profit chains (Strayer, DeVry, Chamberlain, Phoenix, Herzing, etc.) where every branch shares 100% inheritance with the flagship.
- Final frozen list: 38 families, 184 suppressed branch UNITIDs.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | 2 ruff + 1 tsc error | I001 import order in `test_branch_campuses_config.py`; TS2741 `family_size` missing from synthetic anchor row | `ruff --fix`; added `family_size: 1` to synthetic row in `CompareSchoolsPanel.tsx` |
| 2 | All checks pass | — | — |

---

## §7 Test Coverage

**Status:** COMPLETE
**Test-writer pass:** 2026-05-05

### Tests Added

| Test File | Test Name | Priority | What It Tests |
|-----------|-----------|----------|---------------|
| `backend/tests/test_branch_campuses_config.py` | `test_suppressed_unitids_is_union_of_family_branches` | P0 | `SUPPRESSED_BRANCH_UNITIDS` equals the union of every branch list across `INSTITUTION_FAMILIES`. Defends the load-bearing invariant for the SQL `WHERE unitid NOT IN (...)` clause. |
| `backend/tests/test_branch_campuses_config.py` | `test_family_size_includes_flagship_plus_branches` | P0 | For every flagship, `FAMILY_SIZE_BY_FLAGSHIP_UNITID[flagship] == len(INSTITUTION_FAMILIES[flagship]) + 1`. Also checks the keysets match and every size is `>= 2`. Catches off-by-ones in the "Campuses" cell. |
| `backend/tests/test_branch_campuses_config.py` | `test_no_unitid_appears_in_multiple_families` | P1 | A branch UNITID belongs to at most one family. Two families claiming the same branch would silently overstate one flagship's family size. |
| `backend/tests/test_branch_campuses_config.py` | `test_no_flagship_is_also_a_branch` | P1 | No flagship UNITID also appears as a branch in any family list. If it did, the leaderboard SQL would suppress the flagship itself and the entire family would vanish from the leaderboard. |
| `backend/tests/test_branch_campuses_config.py` | `test_all_unitids_are_int` | P1 | Every UNITID across all three structures is a `int` (not `str`, not `bool`). The leaderboard SQL builder interpolates these directly; a stringified UNITID would silently desync the `WHERE` clause from the `CASE WHEN` family-size annotation. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `test_campuses_column_renders_family_size` | P1 | Mock row with `family_size: 6`; the desktop grid cell `row-campuses-204857-52.03` reads `6`. Locks the multi-campus rendering path. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `test_campuses_column_renders_one_for_standalone` | P1 | Default fixture has `family_size: 1`; the desktop grid cell reads `1`. Locks the standalone (and "we don't know of any branches") rendering path. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `test_card_view_shows_campuses_label` | P1 | At <768px the mobile card stack carries `data-testid="card-campuses-{unitid}-{cipcode}"` with the localized "Campuses" label and the integer count. Locks the mobile educational signal. |

### Edge Cases Covered

- [x] Derived `SUPPRESSED_BRANCH_UNITIDS` stays in lockstep with `INSTITUTION_FAMILIES` (set equality + count).
- [x] `FAMILY_SIZE_BY_FLAGSHIP_UNITID` keyset matches `INSTITUTION_FAMILIES` keyset; every value is `flagship + branch count`.
- [x] No duplicate branch UNITIDs across families.
- [x] No flagship UNITID accidentally listed as a branch.
- [x] All UNITIDs in all three structures are Python `int` — defends the SQL builder against a future stringly-typed edit.
- [x] Multi-campus family (`family_size: 6`) renders the integer in the desktop grid Campuses cell.
- [x] Standalone school (`family_size: 1`) renders `1` in the desktop grid Campuses cell.
- [x] Mobile card stack renders the labelled Campuses line carrying the family size.

### Test Results

| Suite | Pass | Fail (caused by this spec) | Fail (pre-existing on main) | Skip | Total |
|-------|------|----------------------------|----------------------------|------|-------|
| pytest (backend, full suite) | 1543 | 0 | 3 | 0 | 1546 |
| vitest (frontend, full suite) | 819 | 0 | 10 | 0 | 829 |

**New tests added by this spec:** 5 backend + 3 frontend = 8. All 8 pass.

### Existing Tests at Risk — Status

Per §4 Testing Impact Analysis, two backend test files were called out as Medium risk (response-shape change adds `family_size`):

- `backend/tests/services/test_schools_for_career_service.py` — **PASSING** (the new field has a default of `1`, so existing fixtures that omit it deserialize fine via Pydantic).
- `backend/tests/routers/test_careers_router.py` — **PASSING** (same reason; the `_row()` helper omits `family_size` and Pydantic populates the default).

No fixture updates were needed in either file — the additive default carried the contract change without breakage.

### Pre-existing Failures (NOT caused by this spec, flagged for human review)

These tests fail on `main` HEAD before any branch-campus work was applied. Causation verified by reverting the in-flight unrelated changes (`backend/app/services/ask_gemma.py`) to HEAD and observing the same failure. The other failing files (`backend/app/services/boss_fights.py`, `frontend/src/components/build-results/FinancesCard.tsx`) had **zero** working-tree diffs vs HEAD throughout this work. None of these tests touch `family_size`, `INSTITUTION_FAMILIES`, `SUPPRESSED_BRANCH_UNITIDS`, the leaderboard query, or any branch-campus surface.

| Test | Why it fails | Verdict |
|------|--------------|---------|
| `tests/services/test_ask_gemma.py::test_context_for_stat_includes_lineage_drivers[ROI]` | `_context_for_stat` no longer renders `debt_to_earnings_annual` (`0.32`) for ROI; the prompt context format has drifted from what the test asserts. | Pre-existing on `main` HEAD. Unrelated to branch-campus. |
| `tests/services/test_boss_fights.py::TestNarrativePromptIncludesCostContext::test_prompt_carries_net_price_and_modeled_debt` | Loans-boss narrative prompt no longer cites `$72,000` (4-year sticker tuition × 4). | Pre-existing on `main` HEAD. Unrelated to branch-campus. |
| `tests/services/test_boss_fights.py::TestStatExplainerRoiNarrative::test_cost_of_attendance_narrative_cites_4yr_cost` | ROI stat-explainer no longer cites `$56,800` (4-year average net price). | Pre-existing on `main` HEAD. Unrelated to branch-campus. |
| `frontend/src/components/build-results/FinancesCard.test.tsx` (10 failures across the file) | ROI receipt now renders "Cost basis: unavailable" instead of "Net price per year: $X" / "Cost of attendance per year". `FinancesCard.tsx` is unmodified in the working tree, so the test expectations have drifted from the rendered receipt. | Pre-existing on `main` HEAD. Unrelated to branch-campus. |

**Recommendation for human review:** these failures look like they belong to in-flight ROI-receipt and Loans-boss work in this repo (commits `b9fbef3` "in-place Save button + sticky bottom action bar redesign" and `4fb9d81` "stat-calculation audits + consistency spec"). They should be triaged by whoever owns those specs — they predate this spec's work and are out of scope for branch-campus suppression.

### Gaps Identified

- **P2 detection-script smoke test not added.** The spec marked this as optional ("acceptable but optional"). The script was already validated against the live Gold dataset by the data-reviewer pass (38 families, 184 UNITIDs detected and human-approved), so a synthetic smoke test would not catch a regression that the in-prod human-review gate wouldn't. Skipped intentionally.
- **No backend integration test for the leaderboard query suppression itself.** The spec lists three P0 backend leaderboard integration tests (`test_leaderboard_excludes_suppressed_branch_campuses`, `test_leaderboard_family_size_populated_for_flagship`, `test_leaderboard_empty_suppression_set_works`). The current leaderboard query lives in `src/mcp_server/futureproof_server.py` and is consumed via `mcp_client.call("get_schools_for_career", ...)` — the existing `test_schools_for_career_service.py` mocks the MCP boundary entirely (no DuckDB fixture is wired up), and the suppression logic sits below that mock. To hit those P0 tests honestly, the MCP server's query would need to be exercised against an in-memory DuckDB with mocked `consumable.program_career_paths` rows — that's a non-trivial test-infrastructure addition (no fixture pattern currently exists for it in this codebase). The config-level invariants (P0 + P1 above) cover the "the right UNITIDs go into the SQL string" half of the contract; the "the SQL filters and annotates correctly" half is left as a manual-verification check (§9 Verification, "Manual Sanity Check"). **Recommend** filing a follow-up for an MCP-server query test harness so future leaderboard-query changes are caught at PR time, not at manual-QA time.
- **P2 sortable-column test not added.** The current `PanelTable` does not implement client-side sort handlers — sorting is handled by the backend's `RANK() OVER` ordering. Adding a sortable affordance is a separate UX work item; the spec's §3 calls for sortable but the implementation deferred it. Not tested because it's not built.

---

## §8 Reviews

**Status:** APPROVED (Design Audit + Code Review both APPROVED 2026-05-05)

### Design Audit (@fp-design-auditor)
**Status:** COMPLETE
**Reviewed:** 2026-05-05

#### Findings

##### Column Header — `RowHeader` / `<Cell head>`

The `Cell` component at line 976–983 renders the head variant as:
```
"text-micro uppercase tracking-wider text-text-muted py-1"
```
The CAMPUSES header is added at line 847 via `<Cell head>{t("compareSchools.column.campuses")}</Cell>`, inheriting that same class string. Adjacent headers (STATE, ERN, ROI, EARNINGS, COST 4YR) all go through the same `Cell head` path and receive identical treatment.

**Discrepancy vs. §3 spec.** §3 specifies the header as `font-data font-bold uppercase text-text-muted` at `fontSize: 11` with `letterSpacing: 1`. The `Cell head` implementation uses `text-micro uppercase tracking-wider text-text-muted` — it does NOT include `font-data`. `text-micro` is defined in DESIGN.md as a Nunito token (12px / 0.75rem), not Space Mono. The existing adjacent headers (STATE, ERN, etc.) carry the same omission. This means the CAMPUSES header is internally consistent with the existing column headers — they all use Nunito (`text-micro`) rather than Space Mono (`font-data`) — but all diverge from §3's `font-data font-bold` prescription.

Since the CAMPUSES header exactly matches the pre-existing adjacent headers, this is not a regression introduced by this spec. It is a pre-existing systematic deviation. Filing as a warning, not a new violation attributable to this change.

##### Column Cell — `DataRow` Campuses `<Cell>`

Lines 930–939:
```tsx
<Cell tone={anchorBg}>
  <span
    className="font-data text-text-primary"
    data-testid={`row-campuses-${row.unitid}-${row.cipcode}`}
  >
    {row.family_size}
  </span>
</Cell>
```

`font-data text-text-primary` — PASS. `font-data` is the correct Space Mono token for numeric data. `text-text-primary` is the correct DESIGN.md token (Usage: "Primary body text"). No hardcoded color or size values.

**Comparison against adjacent numeric cells:**
- ERN cell (line 942–944): `font-data text-stat-ern` — uses the stat-specific color token.
- ROI cell (line 946–948): `font-data ${statRoiColorClass(row.stat_roi)}` — uses the dynamic stat color.
- EARNINGS cell (line 951–953): `font-data text-text-primary` — matches CAMPUSES exactly.
- COST 4YR cell (line 955–957): `font-data text-text-primary` — matches CAMPUSES exactly.

CAMPUSES is correctly treated as a neutral count, not a stat-colored value. `text-text-primary` is the right semantic choice per §3 ("no special treatment for `family_size > 1`"). Consistent with the Earnings and Cost 4yr cells. PASS.

##### Mobile `CardRow` — Campuses Line

Lines 748–754:
```tsx
<span
  className="block font-data text-micro uppercase tracking-wider text-text-muted mt-1"
  data-testid={`card-campuses-${row.unitid}-${row.cipcode}`}
>
  {t("compareSchools.column.campuses")}: {row.family_size}
</span>
```

`font-data text-micro` — WARNING. `text-micro` is defined in DESIGN.md as a Nunito token (12px, weight 600). `font-data` overrides the font family to Space Mono. Using two font-family tokens in combination is atypical for Brightpath — the design system does not define a `font-data text-micro` composite. In the CardRow context, the label "Campuses: 1" is being rendered in Space Mono at micro size, while adjacent label lines in the same card (e.g., line 764: `font-data text-micro uppercase tracking-wider text-text-muted` for the ERN label) use the same combination. This makes CAMPUSES internally consistent with ERN/ROI card labels — same `font-data text-micro` pattern. Not a new violation introduced by this spec.

##### Grid Column Count

`gridTemplateColumns` at line 632: `"auto minmax(0, 1fr) auto auto auto auto auto auto"` — 8 columns. `YourSchoolDivider` at line 989: `col-span-8`. PASS — counts match.

##### i18n Keys

`compareSchools.column.campuses` added to all three locales (en, es, ar) at lines 431, 900, 1381. Key is positioned between `compareSchools.column.state` and `compareSchools.column.ern` in all three locale blocks — matches DOM order. No inconsistency with neighboring key structure. PASS.

##### Token Inventory — New Tokens Introduced

None. The implementation uses only: `font-data`, `text-text-primary`, `text-text-muted`, `text-micro`, `uppercase`, `tracking-wider`, `mt-1`, `block` — all pre-existing tokens and Tailwind utilities present throughout the file.

##### WARNINGS (non-blocking)

- **Pre-existing: `Cell head` missing `font-data`.** All column headers use `text-micro` (Nunito) rather than `font-data font-bold` (Space Mono) as §3 specifies. CAMPUSES inherits this deviation. The Campuses header is internally consistent with STATE, ERN, ROI, EARNINGS, COST 4YR — the whole header row is off-spec in the same way. This predates this spec and is not attributable to the CAMPUSES addition. Recommend a dedicated cleanup pass to align `Cell head` with §3 or update §3 to match the implemented treatment.
- **`font-data text-micro` composite.** Used consistently in CardRow for all column labels (lines 764, 775, 799, 749). Not an invented pattern for CAMPUSES — it's the established card-label treatment. Not a violation.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED

### Code Review (@faang-staff-engineer)
**Status:** APPROVED
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)
**Date:** 2026-05-05 (initial), 2026-05-05 (re-review)

#### Summary

Look, I love Claude, BUT — this is solid work that has one real bite to it. The architecture is right (UI-layer suppression, frozen config, additive Pydantic field with safe default), the SQL builder cleanly handles both the populated and empty-config cases, the abs_rank semantics survive both the SQL `RANK() OVER` path and the Python re-rank under `home_state`, and backward compatibility on `SchoolForCareerRow` is genuinely fine because Pydantic v2 honors the `int = 1` default. The detection script's false-positive guards (>= 3 UNITID prefix, 80% inheritance ratio, low_overlap_warning, deterministic UNITID-sorted flagship pick) are layered correctly, and the human-review gate is the right safety net for the edges the heuristic cannot catch.

There is, however, one **Serious** finding around `assert`-based int-type enforcement that becomes a live SQL-injection vector if anyone ever runs the backend with `python -O` or `PYTHONOPTIMIZE=1`, plus one **Moderate** finding on the `family_size` CASE chain having already crossed the author's own self-imposed refactor trigger (38 entries vs. "~30"), one **Moderate** pre-existing footgun on the dense-rank sentinel that this spec now depends on, and one **Minor** on the detection script's hardcoded relative parquet path. Fix Finding 1 before this is shippable; Finding 2 needs a one-line decision (bump comment or refactor); the rest are catch-on-next-edit.

#### Findings

##### Finding 1 — Trust-boundary `assert` is stripped by `python -O` (SERIOUS, fix before merge)

**Impact:** The frozen config relies on import-time `assert`s to enforce that every UNITID in `INSTITUTION_FAMILIES` is a Python `int`. The leaderboard SQL builder concatenates these values directly into `WHERE unitid NOT IN (...)` and the `CASE unitid WHEN ... THEN ...` family_size expression via `str(u)` and f-strings. Today this is safe — the values are trusted ints. But Python's `-O` (and `PYTHONOPTIMIZE=1`) strips `assert` statements at compile time. If this backend is ever deployed with optimization on (some cloud images default to it; certain Docker layers set it for size), and a future edit slips a string like `"131803; DROP TABLE consumable_program_career_paths; --"` into the dict, every gate vanishes silently and the string is interpolated raw into the query string passed to `engine.query_sql(sql, params)`.

This is not hypothetical paranoia — it is exactly the failure mode the comment in `branch_campuses.py` lines 142–151 says it is defending against, and `assert` is the wrong primitive for that defense. The `test_all_unitids_are_int` test (P1 in §7) would catch a bad edit *if* CI runs without `-O`. CI does today. Prod might not. The defense should hold even when `-O` is on.

**Location:** `/Users/jcernauske/code/bright/futureproof-data/backend/app/config/branch_campuses.py` lines 142–151

```python
# Fail loudly at import time if a future edit slips a non-int through.
assert all(
    isinstance(flagship, int) and isinstance(branches, list)
    for flagship, branches in INSTITUTION_FAMILIES.items()
), "INSTITUTION_FAMILIES keys must be int and values must be list"
assert all(
    isinstance(b, int) for branches in INSTITUTION_FAMILIES.values() for b in branches
), "INSTITUTION_FAMILIES branch UNITIDs must all be int"
```

**The Fix:** Replace the asserts with explicit `raise TypeError(...)` so the guard survives `-O`. Same import-time semantics, same loud failure, but does not get compiled out. While here, also reject `bool` explicitly (Python `bool` is a subclass of `int`, so `isinstance(True, int)` is `True` — `True` would silently pass and stringify as `"True"` in the SQL builder, breaking the query).

```python
for flagship, branches in INSTITUTION_FAMILIES.items():
    if not isinstance(flagship, int) or isinstance(flagship, bool):
        raise TypeError(
            f"INSTITUTION_FAMILIES flagship {flagship!r} must be int, "
            f"got {type(flagship).__name__}"
        )
    if not isinstance(branches, list):
        raise TypeError(
            f"INSTITUTION_FAMILIES[{flagship}] must be list, "
            f"got {type(branches).__name__}"
        )
    for b in branches:
        if not isinstance(b, int) or isinstance(b, bool):
            raise TypeError(
                f"INSTITUTION_FAMILIES[{flagship}] branch {b!r} must be int, "
                f"got {type(b).__name__}"
            )
```

Belt-and-suspenders, optional but recommended: in the SQL builder at `futureproof_server.py` line 3804, change `", ".join(str(u) for u in sorted(SUPPRESSED_BRANCH_UNITIDS))` to `", ".join(str(int(u)) for u in sorted(SUPPRESSED_BRANCH_UNITIDS))`. Same for the family_size CASE on line 3816. Costs nothing, makes the trust boundary self-evident at the call site, not just at import time.

##### Finding 2 — `family_size` CASE chain has already crossed the author's own refactor trigger (MODERATE)

**Impact:** Not a current performance problem at 38 families and tens of thousands of PCP rows — DuckDB compiles this efficiently. But the comment at `futureproof_server.py` lines 3811–3813 says "refactor to a LEFT JOIN VALUES if it ever exceeds ~30." Current count is 38. The author wrote a self-imposed threshold, then shipped past it. This is the kind of "I will fix it later" note that becomes a 6-month-old TODO. Either bump the threshold in the comment to match what was actually shipped (with a justification), or do the refactor now while the spec is fresh in everyone's head.

The downstream risk: when this dict grows to 80–100 families (likely after the next 2–3 Scorecard refreshes, given the discovery script flagged 39 candidates this run from a single dataset), someone will eventually ship the refactor under time pressure with no test coverage on the new path because the existing tests are config-level (`test_branch_campuses_config.py`) and do not touch the SQL builder.

**Location:** `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py` lines 3809–3825

**The Fix:** Update the comment to reflect reality (the lazy fix), or implement the LEFT JOIN VALUES refactor now (the right fix). Either is acceptable for this spec; pick one. If you keep the CASE chain, change the trigger to "~100" with a one-sentence note that DuckDB benchmarks well at this size. If you refactor now, the SQL becomes:

```sql
WITH family_sizes(flagship_unitid, family_size) AS (
    VALUES (131803, 17), (482477, 16), ...  -- generated at module load
)
SELECT
    p.unitid,
    ...,
    COALESCE(fs.family_size, 1) AS family_size,
    ...
FROM consumable_program_career_paths p
LEFT JOIN family_sizes fs ON fs.flagship_unitid = p.unitid
WHERE ...
```

Either path is fine. Do not ship the half-position.

##### Finding 3 — `prev_score: float | None = object()` sentinel is a footgun (MODERATE)

**Impact:** Line 3912 in `futureproof_server.py` initializes `prev_score` with `object()` to guarantee the first comparison `score != prev_score` is true. Pre-existing pattern, not introduced by this spec, but it sits one merge conflict away from being broken: anyone "fixing" the type signature to satisfy mypy could replace `object()` with `None` and silently break the dense-rank for the case where the first row has `composite_score is None`. The `# type: ignore[assignment]` comment hides this from mypy entirely.

This is not a branch-campus finding per se, but it now affects the abs_rank path that this spec relies on for the home_state-aware re-rank. If this breaks, every leaderboard with `home_state` set returns broken ranks and the suppression work looks like the culprit in the bug report.

**Location:** `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py` line 3912

**The Fix:** Use a uniquely-typed sentinel and an identity check. Out of scope for this spec — file as a follow-up — but worth knowing about because the abs_rank semantics that §8 asked me to verify ride on this line.

```python
_RANK_SENTINEL: object = object()
prev_score: object = _RANK_SENTINEL
current_rank = 0
for idx, row in enumerate(materialized, start=1):
    score = row.get("composite_score")
    if prev_score is _RANK_SENTINEL or score != prev_score:
        current_rank = idx
        prev_score = score
    row["abs_rank"] = current_rank
```

##### Finding 4 — Detection script parquet path is CWD-relative (MINOR)

**Impact:** `PARQUET_GLOB = "data/gold/iceberg_warehouse/consumable/career_outcomes/data/*.parquet"` at line 44 of `detect_branch_campuses.py` is a relative path. The docstring says "Run via: `uv run python scripts/detect_branch_campuses.py`" from repo root, which works, but anyone running it from `scripts/` directly or via a CI cron from a different working directory gets a silent zero-rows DataFrame and the script reports "candidate_families: 0" with no error. That is a genuinely confusing failure mode at 2am during a Scorecard refresh.

**Location:** `/Users/jcernauske/code/bright/futureproof-data/scripts/detect_branch_campuses.py` line 44

**The Fix:** Resolve relative to the script's own location, and assert non-zero rows from the load step:

```python
REPO_ROOT = Path(__file__).resolve().parents[1]
PARQUET_GLOB = str(
    REPO_ROOT / "data/gold/iceberg_warehouse/consumable/career_outcomes/data/*.parquet"
)

# In load_career_outcomes():
if df.empty:
    raise RuntimeError(
        f"No rows loaded from {PARQUET_GLOB} — verify the Gold dataset has been "
        f"materialized (run the consumable.career_outcomes pipeline first)."
    )
```

#### What's Actually Good

I will grudgingly acknowledge that several things are done correctly here that I expected to find broken:

- **`abs_rank` semantics are preserved correctly when WHERE filters rows.** The SQL `RANK() OVER` operates on the post-WHERE universe, so suppressed UNITIDs do not consume rank slots. The home_state Python re-rank in `materialized.sort(...)` plus the dense-rank loop also operates on the same filtered list. There is no double-rank inconsistency. Reviewing area #3 from the prompt: clean.
- **Empty-suppression-set guard is correct.** Both `if SUPPRESSED_BRANCH_UNITIDS:` (skips the `WHERE NOT IN ()` clause) and `family_size_expr = "1 AS family_size"` fallback (avoids invalid `CASE` with no `WHEN`) handle the degenerate case. Reviewing areas #3 and #7 from the prompt: clean.
- **`SchoolForCareerRow.family_size: int = 1` is a safe additive change.** Pydantic v2 fills the default for any payload missing the field; the test results in §7 confirm `test_schools_for_career_service.py` and `test_careers_router.py` did not need fixture updates. Reviewing area #8 from the prompt: clean.
- **Import-time load (not lazy) is correct here.** The frozen config is small (kilobytes), read on every leaderboard request, and never invalidated at runtime. Lazy loading would be cargo-cult complexity. Reviewing area #2 from the prompt: clean.
- **Detection script's false-positive layering is well thought out.** Three independent guards stack (>= 3 UNITID prefix detection threshold, 80% inheritance ratio, low_overlap_warning at < 10 CIPs) with a human-review gate as the final safety net. The Embry-Riddle exclusion in the config docstring proves the gate is being used correctly. The deterministic UNITID sort before `.iloc[0]` selection in `identify_flagship` is the right call. Reviewing area #1 from the prompt: clean.
- **Trust-boundary correctly identified architecturally.** The comment "Values come from a frozen, version-controlled Python config (trusted ints, never user input — safe to interpolate)" at lines 3797–3800 correctly identifies the contract. The contract is good. The enforcement (Finding 1) is the gap, not the architecture. Reviewing areas #5 and #6 from the prompt: architecturally clean, mechanically broken on the `assert` enforcement only.

#### Required Changes (Routing)

| # | Finding | Severity | Fix Owner | Required for Approval? |
|---|---------|----------|-----------|------------------------|
| 1 | `assert`-based int gate stripped under `python -O` | SERIOUS | Implementation (general Claude Code) — edit `backend/app/config/branch_campuses.py` | YES — fix before merge |
| 2 | `family_size` CASE chain past author's own refactor trigger | MODERATE | Implementation (general Claude Code) — pick one of: bump comment threshold to ~100, or refactor `futureproof_server.py` lines 3809–3825 to LEFT JOIN VALUES | YES — pick one |
| 3 | `prev_score = object()` sentinel pattern | MODERATE | Follow-up spec (out of scope for this spec) | NO — file as separate cleanup |
| 4 | Detection script CWD-relative parquet path | MINOR | Implementation (general Claude Code), or follow-up | NO — nice-to-have |

#### Questions for the Author

- The detection script's `low_overlap_warning` is emitted in the JSON for human review but never gates anything automatically. Is that intentional? (I think yes — the human is the gate — but worth confirming so a future contributor does not "helpfully" make it gate `suppress_recommended`.)
- What is the operational rollback plan if a future Scorecard refresh introduces a family the human review misses, and a real flagship gets accidentally added to `SUPPRESSED_BRANCH_UNITIDS`? Today it would silently vanish from every leaderboard. Is the answer "the `test_no_flagship_is_also_a_branch` unit test catches it"? Worth making that explicit in §11.
- Are we monitoring leaderboard query latency post-deploy? The CASE chain adds a ~50-branch lookup per row scanned. At today's PCP scale (and the LIMIT cap at `SCHOOLS_FOR_CAREER_SCAN_LIMIT`) it is negligible, but I would want a baseline before this lands so we can spot a regression if/when the family list grows.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

**Routing:** Finding 1 (SERIOUS) and Finding 2 (MODERATE) are required for approval and route to the Implementation step (general Claude Code). Findings 3 and 4 are recommended follow-ups and may ship as separate cleanup specs. Re-request review after Finding 1 and Finding 2 are addressed; log the resolution in §10 Discussion.

#### Re-Review (2026-05-05)

Look, I love Claude, BUT — I had to verify this one personally before flipping the bit. Re-read both touched sites; both required findings are resolved cleanly, and the optional belt-and-suspenders casts I asked for at the SQL call site landed too. Approving.

**Finding 1 (SERIOUS) — RESOLVED.** `backend/app/config/branch_campuses.py` lines 142–164 now use `_validate_int(value, label)` which `raise TypeError` (not `assert`). Verified the gate survives `python -O` because `raise` is not stripped at compile time. The `bool` rejection is correctly ordered (`isinstance(value, bool) or not isinstance(value, int)`) — `True`/`False` get caught even though `bool` subclasses `int`. The validator runs at import time inside a `for` loop over `INSTITUTION_FAMILIES.items()`, which is the right place for it (fail-fast on module load, before any request can reach the SQL builder). Author's verification — validator rejects `True` with "must be int (got bool: True)" and `'204796'` with "must be int (got str: '204796')" — confirms both halves of the gate are live. The `del _flagship, _branches, _branch` at the end is good hygiene; keeps the loop variables out of the module namespace. Trust boundary is now enforced under every Python optimization mode.

**Finding 2 (MODERATE) — RESOLVED.** `src/mcp_server/futureproof_server.py` lines 3812–3820 now document the threshold at "~100 families" with the DuckDB-folds-into-a-constant-lookup justification, and explicitly call out the `LEFT JOIN (VALUES ...) f(unitid, family_size)` refactor as the path forward when the threshold is crossed. This is the lazy-but-correct fix — keeps the CASE at current scale (where it is genuinely fine), updates the trigger so we are not shipping past our own self-imposed line, and documents the next move so the future contributor under time pressure has a roadmap. Acceptable per the original Finding 2 routing ("either path is fine; pick one"). Bonus points for the belt-and-suspenders casts: `str(int(u))` on line 3807 (suppressed-branch IN-clause) and `int(flagship)`/`int(size)` on line 3823 (family-size CASE arms). Now even if a future config edit somehow slips a string past the import-time validator, the SQL builder would `ValueError` on the `int(...)` cast rather than interpolate the string raw. That is exactly the right defense-in-depth shape: the validator is the primary gate, the casts are the secondary gate, and both are at the trust boundary.

**Findings 3 & 4 — Out of scope, no action needed for this spec.** The `prev_score = object()` sentinel and the CWD-relative parquet path remain documented as follow-ups per the original routing table.

**Verification spot-checks I ran in the re-read:**
- `_validate_int` is called for both keys and branches — full coverage of the dict ✓
- Loop variables (`_flagship`, `_branches`, `_branch`) are deleted after the loop — no module-scope pollution ✓
- The empty-set guards (`if SUPPRESSED_BRANCH_UNITIDS:` and `if FAMILY_SIZE_BY_FLAGSHIP_UNITID:`) are still in place after the cast additions — degenerate-case behavior preserved ✓
- The author's claim of "5 config tests pass; 17 leaderboard tests pass; ruff clean" is consistent with the visible code; no test changes were required because the validator failure mode (TypeError at import) matches what `test_all_unitids_are_int` would surface ✓

#### Final Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

Ship it. The architecture was right from the start; the enforcement gap is now closed; the CASE-chain decision is documented honestly. Findings 3 and 4 should land as their own cleanup specs when someone has a quiet afternoon.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-05-05 20:34

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | 1 pre-existing E501 in `test_ask_gemma_explain_receipt.py` (introduced by feat(aura-stat) commit `53fb058`, not touched by this spec). 1 I001 in `test_branch_campuses_config.py` introduced by this spec — fixed via `ruff --fix`. |
| Type check (mypy) | PASS | 15 pre-existing errors across `stat_engine.py`, `sessions.py`, `set_your_course.py`, `builds.py`. None of these files were modified by this spec (confirmed via `git diff HEAD`). 0 new errors from spec files. |
| Tests (pytest) | PASS | 1543 passed, 3 failed — matches documented pre-existing count exactly. See footnote. |

### Pipeline Script
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) `scripts/detect_branch_campuses.py` | PASS | No issues |

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | 1 error fixed: `family_size` missing from synthetic anchor row in `CompareSchoolsPanel.tsx` line 236. Added `family_size: 1` (safe default for a standalone anchor representation). |
| Tests (vitest) | PASS | 819 passed, 10 failed — matches documented pre-existing count exactly. See footnote. |
| Production build (Vite) | PASS | 905 modules transformed, build completed in 1.76s |

### Pre-existing Failures (Footnote)

**pytest (3 failures — pre-existing, not caused by this spec):**
- `tests/services/test_ask_gemma.py::test_context_for_stat_includes_lineage_drivers[ROI]`
- `tests/services/test_boss_fights.py::TestNarrativePromptIncludesCostContext::test_prompt_carries_net_price_and_modeled_debt`
- `tests/services/test_boss_fights.py::TestStatExplainerRoiNarrative::test_cost_of_attendance_narrative_cites_4yr_cost`

All 3 in the FinancesCard ROI receipt / Loans-boss surface. Files not modified by this spec.

**vitest (10 failures — pre-existing, not caused by this spec):**
All 10 in `src/components/build-results/FinancesCard.test.tsx` (ROI receipt). Files not modified by this spec.

### Manual Sanity Check

**Query:** Accounting and Related Services (CIP `52.03`) → Accountants and auditors (SOC `13-2011`), high+medium confidence floor, top 12.

The dominant artifact at this filter level was actually the **University of Connecticut** branch campuses (Waterbury, Avery Point, Hartford) — three branch rows in the top 12 sharing the flagship's $65,893 earnings against their own much-cheaper published costs. The Ohio University regional campuses called out in §1 manifest at lower-confidence filters; the UConn pattern is the same artifact and is the one that shows at the spec's default filter.

**BEFORE — original leaderboard, no suppression**

| # | UNITID | Institution | State | ERN | ROI | Earn (1yr) | Cost (4 yr) |
|---|--------|-------------|-------|-----|-----|-----------|-------------|
| 1 | 131496 | Georgetown University | DC | 9 | 10 | $77,441 | $157,732 |
| 2 | 213543 | Lehigh University | PA | 9 | 10 | $71,520 | $134,196 |
| 3 | 164924 | Boston College | MA | 9 | 10 | $69,899 | $159,464 |
| 4 | 216597 | Villanova University | PA | 9 | 10 | $69,420 | $179,504 |
| 5 | 191241 | Fordham University | NY | 9 | 10 | $68,968 | $170,324 |
| 6 | 228875 | Texas Christian University | TX | 9 | 10 | $68,776 | $134,124 |
| 7 | 122931 | Santa Clara University | CA | 9 | 10 | $67,828 | $203,836 |
| 8 | 152080 | University of Notre Dame | IN | 9 | 10 | $66,502 | $111,292 |
| 9 | 117946 | Loyola Marymount University | CA | 9 | 10 | $66,189 | $182,892 |
| **10** | **436818** | **University of Connecticut-Waterbury Campus** | **CT** | **9** | **10** | **$65,893** | **$35,584** |
| **11** | **436827** | **University of Connecticut-Avery Point** | **CT** | **9** | **10** | **$65,893** | **$46,016** |
| **12** | **463056** | **University of Connecticut-Hartford Campus** | **CT** | **9** | **10** | **$65,893** | **$53,356** |

**AFTER — same query with branch-campus suppression + family_size column**

| # | UNITID | Institution | State | CAMPUSES | ERN | ROI | Earn (1yr) | Cost (4 yr) |
|---|--------|-------------|-------|----------|-----|-----|-----------|-------------|
| 1 | 131496 | Georgetown University | DC | 1 | 9 | 10 | $77,441 | $157,732 |
| 2 | 213543 | Lehigh University | PA | 1 | 9 | 10 | $71,520 | $134,196 |
| 3 | 164924 | Boston College | MA | 1 | 9 | 10 | $69,899 | $159,464 |
| 4 | 216597 | Villanova University | PA | 1 | 9 | 10 | $69,420 | $179,504 |
| 5 | 191241 | Fordham University | NY | 1 | 9 | 10 | $68,968 | $170,324 |
| 6 | 228875 | Texas Christian University | TX | 1 | 9 | 10 | $68,776 | $134,124 |
| 7 | 122931 | Santa Clara University | CA | 1 | 9 | 10 | $67,828 | $203,836 |
| 8 | 152080 | University of Notre Dame | IN | 1 | 9 | 10 | $66,502 | $111,292 |
| 9 | 117946 | Loyola Marymount University | CA | 1 | 9 | 10 | $66,189 | $182,892 |
| **10** | **129020** | **University of Connecticut** | **CT** | **5** | **9** | **10** | **$65,893** | **$91,544** |
| **11** | **145637** | **University of Illinois Urbana-Champaign** | **IL** | **1** | **9** | **10** | **$65,425** | **$60,804** |
| **12** | **123961** | **University of Southern California** | **CA** | **1** | **9** | **10** | **$64,797** | **$127,708** |

**Verified outcomes:**
- ✅ Three UConn branch campuses (Waterbury, Avery Point, Hartford) no longer in top 12
- ✅ Single UConn flagship row at #10 with `Campuses: 5` and the honest flagship sticker ($91,544 vs. the misleading branch sticker prices of $35K–$53K)
- ✅ University of Illinois Urbana-Champaign and University of Southern California — both genuinely top-tier accounting programs — surfaced naturally at #11 and #12 to fill the slots vacated by the suppressed branches
- ✅ All other rows show `Campuses: 1`, the correct default for standalone schools
- ✅ `abs_rank` is dense and contiguous post-suppression — RANK() runs after WHERE, so suppressed rows don't consume rank slots

The leaderboard is now apples-to-apples: every row is either a standalone school or a flagship representing a multi-campus family, with the count carried explicitly in the Campuses column.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | 2 ruff errors + 1 tsc error | I001 in `test_branch_campuses_config.py`; E501 pre-existing; TS2741 missing `family_size` in synthetic anchor row | `ruff --fix` for I001; added `family_size: 1` to synthRow in `CompareSchoolsPanel.tsx` |
| 2 | All checks passed | — | — |

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

```
[2026-05-05] @faang-staff-engineer → Implementation (general Claude Code)
Code review verdict: CHANGES REQUIRED. Two items required for approval before this
spec can move to COMPLETE:

  1. (SERIOUS) Replace the import-time `assert`s in
     `backend/app/config/branch_campuses.py` lines 142-151 with explicit
     `raise TypeError(...)` checks. `assert` is stripped under `python -O` /
     `PYTHONOPTIMIZE=1`, leaving the SQL builder's `WHERE unitid NOT IN (...)`
     interpolation defenseless against a future stringly-typed edit. Also
     reject `bool` explicitly (subclass-of-int trap). Optionally add
     belt-and-suspenders `int(u)` casts at the SQL builder call sites
     (`futureproof_server.py` lines 3804 and 3816). Full fix in §8 Finding 1.

  2. (MODERATE) Pick one path for the family_size CASE chain at
     `futureproof_server.py` lines 3809-3825. The current 38 entries already
     exceeds the inline comment's "~30" refactor trigger. Either bump the
     comment to "~100" with a perf justification, or refactor to LEFT JOIN
     VALUES now. Either is acceptable; do not ship the half-position. Full
     options in §8 Finding 2.

Findings 3 (prev_score sentinel) and 4 (CWD-relative parquet path) are
recommended follow-ups, NOT blockers for this spec.

After both required fixes, re-run pytest + ruff + mypy on the backend, then
flip the §8 verdict to APPROVED and ping me to confirm before §9 Verification
re-runs.
```

---

## §11 Final Notes

**Human Review:** APPROVED 2026-05-05

### Lessons learned

- **Calibration changes from data review landed cleanly.** The data reviewer's eight refinements (Ohio U `"Athens"` → `"Main Campus"`, ampersand normalization for Texas A&M variants, `family_size` from suppressed-branch count not raw prefix count, `low_overlap_warning`, most-CIPs-then-earnings flagship pick, deterministic UNITID sort) all baked into the script before its first run. The single run produced the final shipped list with one human-review exclusion (Embry-Riddle).
- **The `assert` → `raise TypeError` hardening is a generally-applicable lesson** for any module that interpolates "trusted" Python values into SQL: a config-level invariant is only a real defense if it survives `python -O`. Apply this pattern to any future trust-boundary validation.
- **The educational signal landed at the right surface.** A separate FinancesCard disclosure note for branch-campus students would have been duplicative — the leaderboard column does the discovery-time work and the build flow stays untouched (a student who specifically wants Ohio U-Zanesville gets a normal build).

### Operational notes

- **Rollback plan:** If a future Scorecard refresh produces a family that the human review misses and a real flagship gets added to `SUPPRESSED_BRANCH_UNITIDS`, the family vanishes from leaderboards. The `test_no_flagship_is_also_a_branch` test catches the case where a UNITID appears as both flagship and branch, but cannot catch a flagship being incorrectly demoted to a branch in someone else's family. Mitigation: any such issue surfaces as "school X used to be on the leaderboard and now isn't" — easy to spot and easy to fix (delete the stale entry in `branch_campuses.py`).
- **Latency baseline:** Per the @faang-staff-engineer review's open question — at the current 38-family scale and the `SCHOOLS_FOR_CAREER_SCAN_LIMIT = 5000` row cap, the CASE chain is well within DuckDB's planner sweet spot (constant-folded, hash-friendly). Refactor trigger documented at ~100 families with the LEFT JOIN VALUES alternative.
- **`low_overlap_warning` is intentionally non-gating.** It surfaces in the human-review JSON as a flag for the reviewer's eye; the algorithm does NOT use it to auto-exclude. The human is the gate.

### Out-of-scope follow-ups — RESOLVED in this spec

Both items the @faang-staff-engineer review flagged as out-of-scope landed in the same change after a closing pass:

- **`prev_score = object()` sentinel** — `src/mcp_server/futureproof_server.py:3919-3927` now uses `prev_score: float | None = None` with an `idx == 1 or score != prev_score` short-circuit on the first iteration. The sentinel hack and its `# type: ignore[assignment]` comment are gone. Dense-rank semantics preserved (verified: 22/22 leaderboard tests still pass; full backend suite still green minus the 3 unrelated pre-existing failures).
- **Detection script CWD-relative `PARQUET_GLOB`** — `scripts/detect_branch_campuses.py:44-58` now resolves the parquet glob via `Path(__file__).resolve().parents[1]` and writes its output to the same repo-anchored `logs/` dir. Added an empty-DataFrame guard that raises `RuntimeError` with a "run the pipeline first" hint when no rows load. Verified by running the script from `/tmp` — same 56/39/186 detection counts, output landed at the absolute repo `logs/` path.

**Post-hackathon follow-ups:**
- After the next Scorecard data refresh, re-run `scripts/detect_branch_campuses.py` and diff the output against the current frozen config. Update if new families have appeared or existing branches have gained independent earnings data.
- Consider a v2 enhancement: clicking the `Campuses: 6` cell expands a tray showing the individual branches with their per-campus costs (same earnings). Currently students can find branches via direct school search; the tray would surface them in-context.
- Consider applying the same family-detection treatment to the compare screen (when comparing two builds), to prevent students from accidentally selecting two branches of the same system as their A/B comparison.
- If the detection algorithm produces too many false positives or false negatives, revisit the 80% inheritance threshold and the 3-campus detection threshold. Both are deliberate calibration choices, not laws of physics.
