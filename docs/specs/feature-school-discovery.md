# Feature: School Discovery — Top Schools for a Program (SKELETON)

## Claude Code Prompt (to be finalized when spec is promoted from backlog)

```
Read the spec at docs/specs/feature-school-discovery.md in its entirety.

Execute the standard FutureProof workflow:

1. ARCHITECTURE REVIEW — @fp-architect (new MCP tool + new endpoint + new screen).
2. DESIGN VISION — @fp-design-visionary (new screen, ranking list, sort control, zip input).
3. DATA REVIEW — @fp-data-reviewer (ranking definition, location data source, data quality).
4. GENAI REVIEW — @genai-architect (if Gemma narrates per-school, prompt + tool-call shape).
5. IMPLEMENTATION — follow §4.
6. TEST — @test-writer (P0 items in §4 Testing Impact Analysis).
7. DESIGN AUDIT — @fp-design-auditor.
8. CODE REVIEW — @faang-staff-engineer.
9. VERIFICATION — @fp-builder.
10. COMPLETION — standard sequence.
```

---

## Status: BACKLOG (SKELETON) + v0.5 STUB carved for hackathon

> **Full spec is post-hackathon.** §1–§4 below describe the complete feature. A **v0.5 stub** was carved out on 2026-04-19 to satisfy Set Your Course's `school_gap` CTA without building the full screen — see §v0.5 Stub Scope immediately below.

---

## §v0.5 Stub Scope (hackathon slice, ships with Set Your Course)

**Goal:** Honor the `school_gap` CTA link from Set Your Course without building the full ranked discovery screen. The stub is a static read-only surface; everything fancy (sort control, zip distance, MCP tool) is deferred to the full spec.

**What ships:**

- [ ] New route `/discover?cip=<cip4>` rendered by a new minimal component `frontend/src/screens/SchoolDiscoveryStubScreen.tsx`.
- [ ] Backend endpoint `GET /schools/top-for-cip?cip4=<cip4>` returns top-10 schools offering the CIP, ranked by a **single composite score** (median_earnings * 0.5 + roi * 0.3 + completion_rate * 0.2 — tunable one-liner, not the full normalization scheme). No sort parameters. No zip. No MCP tool.
- [ ] Response shape reuses `SchoolCard` and `TopSchoolsResponse` from the full spec's §4 — compatible with the full screen when it lands, no shape change required.
- [ ] Screen renders: page title ("Top schools for [program title]"), 10 cards showing school name + state + median earnings + median debt + "See this school" button.
- [ ] "See this school" navigates back to Set Your Course with `?unitid=<n>&cip=<cip4>` pre-populated.
- [ ] Empty / sparse state: if DuckDB returns fewer than 10 schools for the CIP, show what exists with an honest one-liner ("Not many schools report this program — here's what we found.").
- [ ] No zip input. No sort control. No distance. No MCP tool. No Gemma narration. **All of that lands in the full spec post-hackathon.**
- [ ] A visible footer note: "Ranking will get smarter soon. For now, we sort by a mix of earnings, ROI, and completion rate."

**Explicitly deferred to the full spec:**

- Zip input + distance sort (full §1 criteria).
- User-facing sort control (earnings / ROI / enrollment / distance).
- MCP tool `get_top_schools_for_cip` — the chip debug trace can't tool-call the v0.5 stub. Set Your Course's chip-routing prompt, when it returns `school_gap`, emits the `cta_link` but does not surface ranked schools inline.
- Gemma page-level narration blurb.
- Empty-state smart fallbacks (peer-program suggestions).
- Full composite ranking normalization.

**v0.5 file changes (small):**

| File | Action |
|------|--------|
| `frontend/src/screens/SchoolDiscoveryStubScreen.tsx` | Create |
| `frontend/src/api/school_discovery.ts` | Create — one `fetchTopSchools(cip4)` function |
| `frontend/src/App.tsx` | Add `/discover` route → stub component |
| `backend/app/routers/school_discovery.py` | Create — single endpoint, no sort/zip params |
| `backend/app/services/school_discovery.py` | Create — single ranking query, no zip math |
| `backend/app/models/api.py` | Add `SchoolCard`, `TopSchoolsResponse`, `CtaLink` (all shape-compatible with full spec) |
| `backend/tests/routers/test_school_discovery_router.py` | Create — 3 tests (happy path, invalid CIP, empty result) |

**v0.5 success criteria:**

- [ ] Set Your Course's `school_gap` CTA link lands on a real page that renders real data — no 404, no dead link, no "coming soon" placeholder.
- [ ] Student can click from the stub back to Set Your Course at a different school; the pre-populated unitid drives a fresh resolution.
- [ ] Full pytest + vitest + tsc + ruff passes. No frontend regression.

**v0.5 does NOT need:**

- Architecture review (additive scope, reuses existing patterns).
- Design visionary round (no design innovation — list-of-cards following Brightpath tokens is sufficient).
- @fp-data-reviewer (single query, uses existing Gold-zone tables).

When the full spec is promoted from backlog, the v0.5 stub evolves in-place: same route, same component gets extended, same endpoint gains params. No rework, no migration.

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 0.1 (skeleton) |
| Last Updated | 2026-04-19 |
| Blocked By | Design tokens for list/card treatment (none new; reuse Brightpath) |
| Related Specs | `docs/specs/feature-set-your-course.md` (entry point — school_gap feasibility mode links here), `docs/specs/feature-gemma-tool-calling-migration.md` (the new MCP tool becomes another Gemma-callable surface), `docs/specs/feature-receipts.md` (stub card footer carries source attribution per §2 Decision #7 of receipts spec + §2 Decisions #13/#14 of Set Your Course), `docs/specs/feature-chat-guardrails.md` (School Discovery surfaces inherit the voice rules: no taxonomy codes, acronym spell-out on first reference) |
| Mockup reference | `docs/specs/design/set-your-course-mockup/index.html` — **Scenario 13** shows the `school_gap` CTA tile that links to this screen's v0.5 stub |

---

## §1 Feature Description

### Overview

When a student on the Set Your Course screen lands in the **`school_gap`** feasibility mode — meaning their chosen school genuinely doesn't offer the program they were searching for — we give them a link to a new **School Discovery** screen. On it, they see the **top-ranked schools nationally** for that specific program, grounded in real earnings / ROI / career-outcomes data from the Gold zone. An optional zip-code input lets them re-sort by geographic distance from a location they care about. The app never stores the zip. The app doesn't know who they are.

The design choice matters: we are **not** showing "schools near you." Students travel for college. Showing the best places to find the thing they want respects the scope of the decision they're actually making. The zip sort is an opt-in affordance for the minority who want to weight geography — not the default framing.

### Problem Statement

Today, when Set Your Course's chip flow hits `school_gap`, Gemma's response is honest but dead-ends: *"Your school doesn't offer this. Nearby options include X, Y, Z."* That "nearby" framing is wrong — a Minnesota kid wanting marine biology isn't limited to the upper Midwest. And the response is terminal: no path from the dead-end to a real discovery surface.

Set Your Course needs an escape hatch that opens the national picture and invites the student to actually shop for the path, not just get consoled that it's unavailable where they started.

### Success Criteria

- [ ] New React screen at `frontend/src/screens/SchoolDiscoveryScreen.tsx` rendered at a route like `/discover?cip=52.14`.
- [ ] Entry point: Set Your Course's `school_gap` response includes a "See top schools for [program]" CTA. Clicking it navigates to `/discover?cip=<target_cip4>`.
- [ ] Screen renders a ranked list of up to 50 schools nationally offering the requested CIP, with cards showing: school name, state, program stats (median earnings, typical debt, ROI, career outcomes pentagon summary).
- [ ] Default sort: composite ranking (§2 Decision #3). Secondary sort options: earnings descending, ROI descending, enrollment descending.
- [ ] **Zip-code sort (opt-in).** An input field accepts a 5-digit US zip code. When provided, a new "Distance" sort option activates. List re-ranks by distance from the zip centroid (haversine against each school's lat/long).
- [ ] Zip code is **never persisted** — not logged, not stored, not cookied. Lives only in the current page's URL query string or local React state. Navigation away clears it.
- [ ] Clicking a school card navigates back to Set Your Course with `unitid` + CIP pre-populated, so the student can pick up the flow at the new school.
- [ ] New MCP tool: `get_top_schools_for_cip(cip4: str, sort_by: str, zip_code: str | None, k: int) -> list[SchoolCard]`. Exposes the same ranking to any Gemma call site that needs it (e.g. the chip debug trace in `school_gap` bucket can surface top candidates inline without waiting for the student to click through).
- [ ] Full test suite passes: backend + root pytest, frontend vitest, TypeScript. Ruff + mypy clean. Vite build succeeds.
- [ ] Design audit against Brightpath tokens passes (`DESIGN.md`). No new tokens.
- [ ] Every Gemma call this surface makes (if any — see §4) logs to `logs/gemma.jsonl` with `call_site: "school_discovery"`.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Default ranking is national, not geographic.** | Students travel for college. Framing the default view as "schools near you" limits the decision before the student has had a chance to see the full landscape. "Best places to find this thing" is the right default. | "Schools near you" as default — rejected per user observation. Geo-first anchors the student to their current location and undersells the scope of the choice they're making. |
| 2 | **Zip code is opt-in, never stored.** | Privacy-first framing: the product doesn't know who the student is and doesn't want to. Zip is a temporary weight the student applies to the ranking, not a profile field. Zero persistence also means zero legal/compliance surface for what is otherwise a purely-public-data feature. | Auto-detect via IP — rejected, feels invasive + unreliable. Require an account — rejected, we have no account system. Persist for session — rejected, "session" is itself a data footprint we don't want. |
| 3 | **Default ranking is a composite**, not a single axis. | Single-axis rankings are biased: earnings-only favors prestige + finance-heavy schools; debt-only favors cheap regional schools; enrollment favors big state schools. A composite of (median earnings, debt-to-earnings ratio, career outcome coverage, program completion rate) surfaces schools that are actually *good at the specific program*, not just large or expensive. | Single-axis earnings-only — rejected, biases toward Ivy-League-y answers. Let Gemma rank — rejected, introduces non-determinism into a data-heavy surface that benefits from being reproducible. |
| 4 | **Fixed top-50 list**, not infinite scroll. | 50 is enough to cover the meaningful landscape for almost any CIP. Longer lists invite decision paralysis and don't add signal for a high-school-senior making a first pass. Rank cuts off at 50 by policy. | Full list — rejected, 6000-school lists for common CIPs are useless to a student. Top-10 — rejected, cuts some genuinely-good options (strong regional programs). |
| 5 | **Clicking a school card re-enters Set Your Course** with that school pre-selected. | The whole flow is: "can't find marketing at my school → oh, here are the real top marketing programs → let me pick one and see what my build looks like there." The School Discovery screen is a waypoint, not a terminus. | Discovery as terminal screen — rejected, leaves the student to manually navigate back and re-type the school. |
| 6 | **Expose ranking as an MCP tool**, not just as a hidden endpoint. | The ranking logic becomes reusable — the Set Your Course chip debug trace in the `school_gap` bucket can tool-call `get_top_schools_for_cip` and surface top candidates inline in the Gemma response, not just as a navigate-away link. Same data, two surfaces. Also consistent with `feature-gemma-tool-calling-migration.md` — new MCP tools land as tool-call-first by default. | Dedicated FastAPI endpoint only, no MCP — rejected, duplicates the query surface and breaks the tool-call pattern. |
| 7 | **Zip-to-distance is haversine on school lat/long**, not a mapping-service API call. | No external service dependency. Lat/long is in the IPEDS institution data we already ingest. Haversine is 5 lines of math. Works offline. | Google Maps API / similar — rejected, adds an external dep for zero accuracy gain on the scale of "is Ohio State closer than UT Austin." |
| 8 | **No Gemma narration in the v1 ranking cards.** | The ranking surface is pure data — school name, state, stats, program. Adding Gemma per-card would 50× the Gemma call cost and introduce inconsistency (two students see different taglines for the same school). If narration is valuable, v2 adds a single Gemma call per page that generates an opening blurb (e.g. "Top marketing programs concentrate on the coasts; look at these 10 first.") rather than per-card. | Gemma narration per card — rejected, cost + consistency. No narration at all, v1 and beyond — rejected, we may want the page-level blurb in v2. |
| 9 | **No logged-in state, no saved favorites, no compare list.** | v1 is discovery + jump-back-to-Set-Your-Course. Favorites / comparison is a v2 feature that needs account infrastructure we don't have. | Include compare list in v1 — rejected, scope. |

### Constraints

- `backend/app/services/intent.py` — changes only to the `school_gap` response to include the CTA link. The School Discovery screen itself doesn't touch `resolve_intent`.
- `data/futureproof.duckdb` Gold zone — the source of truth. Must include school lat/long; if not, data-pipeline work is a prereq (see §4 Data Model Changes).
- `src/mcp_server/futureproof_server.py` — new tool `get_top_schools_for_cip`. Same pattern as existing tools.
- Brightpath design system (`DESIGN.md`) — no new tokens. Reuse existing list/card treatment.
- No external HTTP dependencies for ranking or distance (haversine only).
- Zip code treated as PII-like — never logged, never stored.

### Out of Scope

- **Account / profile persistence of zip or saved schools.** v2.
- **Comparison list ("compare 3 schools side by side").** v2.
- **Filter by distance threshold** (e.g. "within 500 miles"). v2; default sort is national.
- **International schools.** US-only (College Scorecard + IPEDS scope).
- **Graduate programs.** Undergraduate scope matches the rest of FutureProof.
- **School pages / profiles.** This spec renders a ranked list; full school pages are elsewhere (future).
- **Gemma narration per card** (see §2 Decision #8). v2 at the page level only.
- **Any feature that requires student identity.** The product does not know who the student is; no spec surface relaxes this.

---

## §3 UI/UX Design

**PENDING — @fp-design-visionary when this spec is promoted.** The visionary should propose:

1. **Screen wireframe** — how the ranked list + sort control + zip input coexist without feeling like a spreadsheet. The list cards must carry enough stats to be decision-useful (earnings, debt, ROI, pentagon summary) but not so much they become a datasheet.
2. **Empty state** — when a CIP has few (<10) or zero schools in the Gold zone. ("Not many schools report this program; here's what we found.")
3. **Sort-control treatment** — chips? dropdown? toggle group? Must be fast to operate, mobile-friendly.
4. **Zip input affordance** — a persistent top-of-page input? A chip that expands on click? Frame it as opt-in without pressuring.
5. **Distance sort reveal** — the "Distance" sort option is greyed out until zip is provided. Needs visible enable state.
6. **Click-a-school-card result** — does the navigate-back-to-Set-Your-Course feel like a commitment or a preview? Probably preview (can bail back) — design picks the pattern.
7. **Card density** — five-stat pentagon summary per card? Or one-line stat strip? Picking too much data per card hurts scannability; too little hurts decisions.

Constraints for the visionary:
- Brightpath dark-first, plush, cinematic.
- Mobile + desktop both first-class.
- No new design tokens.
- Tone: cool, confident, data-honest, never hype. Ranking copy is numbers, not adjectives. "Median earnings $58k" not "impressive earnings potential."

---

## §4 Technical Specification

### Architecture Overview

**Frontend:**
- New screen: `frontend/src/screens/SchoolDiscoveryScreen.tsx`.
- New route in `App.tsx`: `/discover?cip=<cip4>&zip=<optional>&sort=<optional>`. Query-string only; no state in store required (navigation clears).
- API client: `frontend/src/api/school_discovery.ts` — `fetchTopSchools(cip4, sortBy, zipCode, k)`.
- Click-school handler pushes the user back to Set Your Course with query params `?unitid=<n>&cip=<cip4>`.

**Backend:**
- New router: `backend/app/routers/school_discovery.py` with `GET /schools/top-for-cip`.
- New service: `backend/app/services/school_discovery.py` — ranking logic, zip→distance, MCP-tool backing.
- MCP tool: extend `src/mcp_server/futureproof_server.py` with `get_top_schools_for_cip(cip4, sort_by, zip_code, k)` — thin wrapper over the service.
- Queries: Gold zone `consumable.program_career_paths` joined with IPEDS institution metadata (lat/long, state, name).

**Set Your Course integration:**
- When the chip-routing prompt emits feasibility_mode `school_gap` for any candidate career, the response includes a `cta_link` field: `{"label": "See top schools for Marketing", "href": "/discover?cip=52.14"}`. Frontend renders the CTA under the Gemma response.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/SchoolDiscoveryScreen.tsx` | Create | The screen. Query-string driven; no store state. |
| `frontend/src/screens/SchoolDiscoveryScreen.test.tsx` | Create | Vitest coverage: render, sort toggle, zip input, card click. |
| `frontend/src/api/school_discovery.ts` | Create | `fetchTopSchools(...)` fetch wrapper. |
| `frontend/src/App.tsx` | Modify | New route `/discover`. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Render `cta_link` from `school_gap` responses. |
| `backend/app/routers/school_discovery.py` | Create | `GET /schools/top-for-cip`. |
| `backend/app/services/school_discovery.py` | Create | Ranking + zip distance. |
| `backend/app/services/set_your_course.py` | Modify | Chip-routing prompt: when `school_gap`, emit `cta_link` in the response. |
| `backend/app/models/api.py` | Modify | Add `SchoolCard`, `TopSchoolsResponse`, extend `ChipResponse` with optional `cta_link`. |
| `backend/tests/services/test_school_discovery.py` | Create | Ranking correctness, zip distance math, sort stability, top-k truncation. |
| `backend/tests/routers/test_school_discovery_router.py` | Create | Happy path, invalid CIP, invalid zip, empty result. |
| `src/mcp_server/futureproof_server.py` | Modify | Add `get_top_schools_for_cip` tool. |
| `tests/mcp/test_school_discovery_tool.py` | Create | MCP tool surface test. |

### Data Model Changes

**New Pydantic — `backend/app/models/api.py`:**

```python
class SchoolCard(BaseModel):
    unitid: int
    instnm: str
    state: str
    cip4: str
    program_title: str
    median_earnings: int | None
    median_debt: int | None
    roi: float | None              # (earnings - debt_service) / debt or similar composite
    completion_rate: float | None
    composite_score: float         # the default ranking score
    distance_miles: float | None   # populated only when zip was provided

class TopSchoolsResponse(BaseModel):
    cip4: str
    program_title: str
    sort_by: Literal["composite", "earnings", "roi", "enrollment", "distance"]
    schools: list[SchoolCard]      # capped at 50
    zip_used: str | None

class CtaLink(BaseModel):
    label: str                     # "See top schools for Marketing"
    href: str                      # "/discover?cip=52.14"

# Extension to existing ChipResponse:
class ChipResponse(BaseModel):
    ...existing fields...
    cta_link: CtaLink | None = None  # populated only when school_gap mode
```

**Gold-zone query (pseudo-SQL):**

```sql
SELECT
  p.unitid,
  i.instnm,
  i.state,
  p.cip4,
  p.program_title,
  p.median_earnings,
  p.median_debt,
  p.roi,
  p.completion_rate,
  i.latitude,
  i.longitude
FROM consumable.program_career_paths p
JOIN consumable.institutions i ON p.unitid = i.unitid
WHERE p.cip4 = :cip4
  AND p.median_earnings IS NOT NULL  -- exclude privacy-suppressed rows
ORDER BY <composite_score> DESC
LIMIT 50
```

**Composite score formula (v1 — tunable by @fp-data-reviewer when promoted):**

```python
composite_score = (
    0.35 * normalize(median_earnings)
  + 0.25 * normalize(roi)
  + 0.20 * normalize(completion_rate)
  + 0.20 * normalize(career_outcome_coverage)
)
# Normalized per-CIP so a weak CIP's best school still scores ~1.0 at the top.
```

**Distance math:**

```python
def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    # Standard haversine formula; ~5 lines.
```

**Zip → centroid:**

```python
def _zip_to_latlong(zip5: str) -> tuple[float, float] | None:
    # Static table of US zip centroids loaded from a CSV in data/reference/
    # (~42k rows, ~1MB). Committed; no external service.
```

### Data Dependencies (prereqs before implementation)

Gate on data-pipeline availability:

- [ ] **Institution table with lat/long.** Confirm `consumable.institutions` (or equivalent) exists in the Gold zone with `unitid`, `instnm`, `state`, `latitude`, `longitude`. If not, this is a Bronze→Gold pipeline task and must land before implementation.
- [ ] **Program-level rank-ready columns.** Confirm `median_earnings`, `median_debt`, `roi`, `completion_rate` are present per (unitid, cip4) in `consumable.program_career_paths`. Partial coverage is fine (privacy suppression is legitimate); we filter nulls out of ranking.
- [ ] **Zip centroid lookup.** Acquire a public-domain zip-to-latlong CSV (USPS / Census ZCTA). ~1MB file at `data/reference/zip_centroids.csv`. Not a pipeline task — one-time commit.

### Gemma / MCP Tool Design

New MCP tool exposed via `src/mcp_server/futureproof_server.py`:

```python
@mcp_tool
def get_top_schools_for_cip(
    cip4: str,
    sort_by: Literal["composite", "earnings", "roi", "enrollment", "distance"] = "composite",
    zip_code: str | None = None,
    k: int = 10,
) -> list[SchoolCard]:
    """Top-ranked schools offering a given CIP. When zip is provided,
    enables the 'distance' sort option. Same logic as the HTTP endpoint."""
```

Consumed by:
- The HTTP endpoint (direct call).
- Set Your Course's `school_gap` chip-routing prompt (tool-call from Gemma, per `feature-gemma-tool-calling-migration.md` Tier P0). Gemma can surface top schools inline in the chip response, THEN append the CTA link for full browsing.

No Gemma narration per card in v1 (§2 Decision #8). The page-level blurb is v2.

### Testing Impact Analysis

**To be expanded when promoted.** Initial sketch of P0 tests:

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `test_school_discovery.py` | `test_default_composite_rank_is_stable` | Same CIP → same top-10 across runs (deterministic composite). |
| P0 | `test_school_discovery.py` | `test_null_earnings_excluded` | Suppressed rows never appear in ranking. |
| P0 | `test_school_discovery.py` | `test_zip_distance_sort` | "90210" pushes LA-area schools to top. |
| P0 | `test_school_discovery.py` | `test_invalid_zip_returns_zip_used_null` | Bad zip → error gracefully, no crash. |
| P0 | `test_school_discovery.py` | `test_top_k_truncation` | `k=10` returns exactly 10 when >10 eligible. |
| P0 | `test_school_discovery_router.py` | `test_get_happy_path` | Endpoint returns 200 with valid shape. |
| P0 | `test_school_discovery_tool.py` | `test_mcp_tool_same_result_as_endpoint` | MCP tool and HTTP endpoint return byte-identical results for same args. |
| P1 | `SchoolDiscoveryScreen.test.tsx` | `test_card_click_navigates_to_set_your_course` | Click navigates with correct query params. |
| P1 | `SchoolDiscoveryScreen.test.tsx` | `test_zip_input_enables_distance_sort` | Distance sort is disabled without zip, enabled with zip. |
| P1 | `SchoolDiscoveryScreen.test.tsx` | `test_zip_not_persisted_across_navigations` | Navigating away clears the zip from state. |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING (spec in backlog)

### @fp-data-reviewer Review
**Status:** PENDING (spec in backlog)

### @genai-architect Review (ad-hoc)
**Status:** PENDING (spec in backlog) — light scope, mostly for the new MCP tool and any v2 Gemma narration.

---

## §6 Implementation Log

**Status:** PENDING (spec in backlog)

---

## §7 Test Coverage

**Status:** PENDING (spec in backlog)

---

## §8 Reviews

**Status:** PENDING (spec in backlog)

---

## §9 Verification

**Status:** PENDING (spec in backlog)

---

## §10 Discussion

```
[2026-04-19] Skeleton drafted after founder request during V2 regression wait.

Key design premise: "we should not show schools near you because kids travel for
college. Show the best places to find that thing. On that page, maybe sort by
distance from a zip they provide. We don't know who they are or where they are."

Three things that fall out of that framing:
1. Default ranking is national, not geographic (§2 Decision #1).
2. Zip is opt-in, never stored (§2 Decision #2).
3. Entry point is the school_gap feasibility mode in Set Your Course —
   this screen is the escape hatch when a student's chosen school genuinely
   doesn't offer what they want.

Key open questions for when this gets promoted:
- Composite ranking weights (§4) — @fp-data-reviewer picks defensible defaults.
- Per-card stats density — @fp-design-visionary picks what goes on each card.
- Sort-control UI pattern — @fp-design-visionary picks the affordance.
- Whether to add a page-level Gemma blurb in v2 (§2 Decision #8 alternative).
- Whether the MCP tool should also power an in-chip response before the CTA
  (tool-call from Gemma → Gemma surfaces top 3 → full link for more). Probably yes.

Hackathon-relevant slice: just the school_gap CTA link in Set Your Course's
chip response. The actual School Discovery screen is post-May-18. The CTA can
ship as a dead link ("soon") for demo safety, or be omitted entirely in the
hackathon build — TBD when picking this up.

Scope note: this spec is US-only and undergrad-only. International + grad are
separate specs if ever.
```

---

## §11 Final Notes

**Human Review:** PENDING — this skeleton is in the backlog. Promotion to DRAFT requires a human review of §1–§4 and resolution of the open questions in §10.
