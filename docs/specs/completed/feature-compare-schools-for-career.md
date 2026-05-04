# Feature: Peer-School Leaderboard (Dual Mode — by Career, by Major)

> **Filename retained for backward compatibility.** This spec evolved from a SOC-only
> "Compare Schools for This Career" draft into a dual-mode leaderboard covering both
> SOC-anchored and CIP+SOC-anchored entry points. The original constraint of "no
> career-first entry" was overridden by the user on 2026-04-29 (see §2 Decision #1A).

> **File-recovery note (2026-04-29):** The original on-disk spec was lost during
> the architecture-review pass (cause undetermined; see project session log).
> This file was reconstructed from conversation context. The §5 architect and
> data-reviewer findings are preserved verbatim from their first-pass reviews.
> Conditions C1–C7 + the five data-reviewer required changes have been folded
> into §1–§4 inline. A re-review pass is required to flip §5 verdicts to
> APPROVED before implementation.

## Claude Code Prompt

```
Read the spec at docs/specs/feature-compare-schools-for-career.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 (dual-mode service, MCP tool with `mode`
     param, two FastAPI endpoints sharing one service, anchor handling for both
     modes, anchor-absent rendering for Spec B click-throughs).
   - Invoke @fp-data-reviewer to review the ranking definition: confidence filter
     across both modes, broad-CIP fallback exclusion predicate, composite score
     formula consistency between SOC and CIP+SOC modes.
   - Both write findings to §5. Resolve every "Open Questions for Architect" item
     in §4 before moving on.
   - If APPROVED: proceed.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to fill §3.
   - Two entry points, ONE component:
     a) `by_soc` mode — triggered from CareerDetail on RevealScreen.
     b) `by_cip_and_soc` mode — triggered from BuildResultsScreen near the build's
        program/major surface.
   - Mode-disambiguation chip in the panel title is mandatory (see §2 Decision #11).
   - Brightpath dark-first, table treatment, NOT pentagon-vs-pentagon.
   - States to design: default, loading, empty, anchor-absent (Spec B click-through
     with no build), anchor-not-in-top-N, anchor-IS-in-top-N, sparse, low-conf-only
     fallback.

3. GENAI REVIEW
   - Invoke @genai-architect to review the new MCP tool's JSON schema (single tool
     with `mode` parameter), parameter constraints, and the response shape Gemma
     will see in chat. Write to §10.

4. IMPLEMENTATION
   - Implement §3 (UI/UX) and §4 (Technical Spec).
   - BEFORE coding: read §4 Testing Impact Analysis. Confirm Existing Tests at
     Risk are accounted for.
   - DURING coding: only modify tests in "Authorized Test Modifications". Any
     other test failure → STOP, escalate via §10.
   - Log to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) after each
     meaningful chunk.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). After 3
     attempts: escalate to human via §10, set status BLOCKED.

5. TESTING
   - Invoke @test-writer to implement P0 then P1 from the New Tests Required
     table in §4.
   - Backend: pytest in backend/tests/ AND root tests/mcp/.
   - Frontend: vitest in frontend/src/**/*.test.ts(x).
   - Run ALL tests to catch regressions.

6. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical Brightpath token compliance.
   - Writes findings to §8.
   - If CHANGES REQUIRED: route to implementer via §10.

7. CODE REVIEW
   - Invoke @faang-staff-engineer for security/perf/error-handling review of the
     dual-mode service, MCP tool, two endpoints, and React surface.
   - Writes findings to §8.
   - If APPROVED: proceed.
   - If CHANGES REQUIRED: route to originating agent via §10.
   - If BLOCKER: STOP, alert human.

8. VERIFICATION
   - Invoke @fp-builder for full build verification (ruff + mypy + pytest +
     TypeScript + vitest + Vite production build).
   - Log results to §9.

9. COMPLETION
   - Update top-level Status to COMPLETE.
   - Check off Success Criteria in §1.
   - Generate report to reports/feature-compare-schools-for-career-YYYY-MM-DD.md.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect + @fp-data-reviewer approval |
| DESIGN VISION | @fp-design-visionary proposing §3 |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-29 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 2.1 (post-arch-review revisions; reconstructed file) |
| Last Updated | 2026-04-29 |
| Blocked By | — |
| Related Specs | `docs/specs/feature-career-search.md` (sibling — Spec B; click-through destination is this spec's `by_soc` mode), `docs/specs/feature-school-discovery.md` (**SUPERSEDED by this spec** — that skeleton was never implemented and this spec covers the same surface area from inside an active build), `docs/specs/cip-intent-substitution.md` (filtering rationale for low-confidence rows), `docs/specs/roi-formula-cost-of-attendance.md` (cost-based ROI provenance threaded through PCP), `docs/specs/three-signal-ai-exposure-composite.md` (RES stat is occupation-level — does NOT vary across schools) |

---

## §1 Feature Description

### Overview

A dual-mode peer-school leaderboard. One React component, one shared service,
one MCP tool with a `mode` parameter, two FastAPI endpoints. Reachable from
two anchored entry points inside an active build (and as a destination from
Spec B's career-search page when the user clicks a suggested career).

| Mode | Filter | Entry point |
|------|--------|-------------|
| `by_soc` | `WHERE soc_code = ?` | "Compare schools for this career" action on `CareerDetail` (`frontend/src/screens/RevealScreen.tsx:313`). Also the destination of every Spec B career-search click. |
| `by_cip_and_soc` | `WHERE cipcode = ? AND soc_code = ?` | "Other schools with this major" action on `BuildResultsScreen.tsx`. Anchor's program AND career are both required — the question is "you, but at a different school." |

In both modes, the table ranks rows by composite `(stat_ern + stat_roi) / 2`
desc. The student's anchor `(unitid, cipcode)` is highlighted in-place if in
the top-N or appended below if not. When entered without a build (Spec B
click-through with no active session), the leaderboard renders cleanly without
an anchor row.

### Problem Statement

Today FutureProof flows in one direction: **school → major → careers**. That
respects the product narrative ("we show what your degree actually becomes")
but leaves two adjacent student questions unanswered:

- **"Am I at a good school for this career?"** — the SOC-anchored question.
  The student is sitting on a Reveal screen for their picked career. They want
  to peek sideways at peers producing the same career, ranked by ERN+ROI.
- **"What other schools could I be looking at for this major?"** — the
  CIP+SOC-anchored question. The student picked a major (and a career within
  it), and wants the same row at a different school. Tightest apples-to-apples
  comparison.

Both questions share 80%+ of their data, query, ranking, and rendering. They
ship as one feature with two entry-point trims, not as two separate surfaces.

### Success Criteria

- [x] On the Reveal screen, a "Compare schools for this career" action is
      visible on the `CareerDetail` surface and opens the leaderboard panel
      in `by_soc` mode.
- [x] On the BuildResults screen, an "Other schools with this major" action is
      visible near the program/major surface and opens the leaderboard panel
      in `by_cip_and_soc` mode.
- [x] Both modes render in the same React component (`CompareSchoolsPanel`)
      with mode-aware title chip, columns, and copy.
- [x] Default confidence filter: `overall_confidence ∈ {high, medium}` AND
      `stat_ern IS NOT NULL AND stat_roi IS NOT NULL` (the latter is implicit
      via the composite formula). No `match_quality` predicate — see §2
      Decision #6 (revised) and §5 data-reviewer findings.
- [x] The student's current `(unitid, cipcode)` is highlighted in-place if
      it's in the top-N. If it is NOT, append a "your school" anchor row at
      the bottom of the table with rank + delta from #1. (v1: append-below
      only; in-place highlight is a P2 polish — see §2 Decision #5.)
- [x] When entered without an anchor (Spec B click-through with no build),
      the leaderboard renders cleanly — no anchor row, no error, no warning.
- [x] Pentagon-vs-pentagon comparison is NOT rendered. Table only.
- [x] New backend endpoints:
      - `GET /careers/{soc_code}/schools` (`by_soc` mode)
      - `GET /majors/{cipcode}/schools/for-career/{soc_code}` (`by_cip_and_soc`
        mode)
      Both delegate to the same shared service; service dispatches through
      `mcp_client.call("get_schools_for_career", args)`.
- [x] New MCP tool: `get_schools_for_career(mode, soc_code, cipcode?, limit,
      min_confidence, min_program_confidence?, state_abbr?, build_unitid?,
      build_cipcode?)` exposes the same logic to Gemma. Listed in the tool
      index resource payload.
- [ ] Gemma chat ("Ask Gemma")  <!-- not verified end-to-end with live Gemma in this spec; the tool surface is wired and tool index advertises it; live-chat verification is a v1.1 task --> can call the tool end-to-end on representative
      queries ("cheapest path to becoming a registered nurse"; "show me
      schools that teach Marketing and produce Brand Managers, ranked") in
      the standard chat-guardrails harness.
- [x] No "career-first" home-screen entry point is added by THIS spec. (Spec B
      adds a header-menu entry point; that's its scope, not ours.)
- [x] Full pytest (root + backend + tests/mcp) + vitest + tsc + ruff + mypy
      green. Vite production build passes.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1A | **OVERRIDES PRIOR DECISION #1.** Career-first entry points are now permitted. Spec B adds a header-menu Career Search page; this spec's `by_soc` mode is its destination. From inside a build, a CIP+SOC-anchored "Other schools with this major" entry is also added. | Product-partner agent had pushed back ("dilutes the narrative into a college ranking site") on 2026-04-29; user overruled the same day on the basis that the unmet student question — "am I at a good school for what I'm doing?" — is real and the data already supports it cleanly. | Hold the line at SOC-only, drill-in only — rejected by user. |
| 2 | Render as a TABLE, not pentagon-vs-pentagon, in BOTH modes. | Of the 5 stats, only `stat_ern` and `stat_roi` vary by school for a fixed SOC; `stat_grw`, `stat_hmn`, `stat_res` are occupation-level and would render as 3 identical sides across all rows. Five pentagons with 3 flat sides reads as "broken" to a student pattern-matching on shapes. | (a) Mini-pentagons per row; (b) pentagon-overlay diff vs anchor build. Both rejected — they create a UX bug masquerading as a teaching moment. |
| 3 | When entered from a build, the student's `(unitid, cipcode)` is always represented (highlighted or appended). When entered without a build, no anchor row. | Anchored framing is "compare from where you are" — must be honored when a build exists. Anchorless framing is "browse from a Gemma suggestion" — adding a fake anchor would lie. | "National leaderboard with no anchor" even when a build exists — rejected; turns the table into a decontextualized rank list. |
| 4 | Composite rank = `(stat_ern + stat_roi) / 2`. Tiebreak by `earnings_1yr_median` desc, then `net_price_annual` asc. SAME formula in both modes. | Both ERN and ROI are integer 1–10 stats already on the row, so they're trivially commensurate. ROI is cost-aware; ERN is earnings-aware. Equal weight is the honest default. **Confirmed by @fp-data-reviewer in §5** with empirical verification against SOC 15-1252. | (a) ROI-only sort (privileges affordability, hides earnings); (b) ERN-only (privileges high-pay, hides ROI traps); (c) custom multi-factor with growth/RES included (those are flat — adds noise). |
| 5 | If the student's anchor isn't in the top-N, **append** it as the (N+1)th row marked "your school." v1 = append-below only; in-place highlight is a P2 polish. | Anchoring overrides arbitrary cutoff. The table is useless to a student whose school isn't on it unless we say so explicitly. Append-only is simpler than in-place + append duplication-guard. | (a) Silently omit; (b) replace #N with the anchor; (c) ship in-place highlight in v1 — first two undercut anchoring; third adds dedupe complexity for marginal v0 value. |
| 6 (revised) | Default filter: `overall_confidence ∈ {high, medium}` AND implicit `stat_ern IS NOT NULL AND stat_roi IS NOT NULL`. **No `match_quality` predicate.** | Per existing `feedback_no_substitution_caveat`: we don't surface "limited data" warnings to students. The way we honor that here is by *filtering low-confidence rows out of the leaderboard*, not labeling them. The proposed `match_quality NOT IN (...)` predicate was investigated against actual stored PCP and found to be a no-op — those values do not exist on stored rows. Stored values are `{full, partial_no_onet, partial_no_bls, scorecard_only}`; substitution-related values (`substituted_cip`, `gemma_expanded`) are runtime-stamped only inside `_handle_get_career_paths` and never reach Iceberg. The `partial_no_bls` rows that pass `overall_confidence ≥ medium` are dropped automatically by the implicit `stat_ern IS NOT NULL` clause (no BLS → no `wage_percentile_overall` → no `stat_ern`). See @fp-data-reviewer findings in §5. | (a) Show all, label low-confidence inline (rejected — clutters table, contradicts the no-caveat rule); (b) keep the (no-op) match-quality predicate (rejected — filters nothing). |
| 7 | The MCP tool is the canonical surface. Both FastAPI endpoints thinly wrap a service that dispatches through `mcp_client.call`. | Lets Gemma chat answer "cheapest path to RN" through tool-calling without UI plumbing — that's the demo win. The service does NOT open DuckDB; it shapes around `mcp_client.call("get_schools_for_career", args)`. The DuckDB / Iceberg query lives exactly once, inside `_handle_get_schools_for_career` on `FutureProofMCPServer`. Matches the established pattern in `school_lookup.py`, `branch_tree.py`, `stat_engine.py`, `intent.py`, `ask_gemma.py`. | Two divergent code paths — rejected; guarantees drift. |
| 8 | Reuse residency-aware tuition logic from `feature-residency-aware-tuition`. Do not reimplement private-school tuition labeling. | Existing memory: private-school tuition is labeled without an in/out residency split. The leaderboard MUST display tuition consistently with the rest of the app. | Reinventing the labeling logic — rejected; risks divergent UX. |
| 9 | National scope by default. State filter is a parameter on the MCP tool but not exposed in the v1 UI. | Anchoring is to the student's *career interest*, not their geography. Students travel for college. | Default-to-anchor-school-state — rejected; geography-anchoring at this surface contradicts the school+major-first frame. UI state-filter — parked for v1.1. |
| 10 | Cost-of-living adjustment is **parked** in v1. Not even a stretch column. | RPP changes the ranking in subtle ways the student can't audit; surfacing it as a column is honest but adds complexity to the v1 table. Deferring keeps the v1 table tight. | (a) Bake RPP into the ranking (rejected — opaque); (b) ship as a stretch column (rejected — scope creep for May 18). |
| 11 | The panel title carries an explicit mode-disambiguation chip. | Two leaderboard entry points on the build screen risk the student asking "why are these schools different?" The title chip pre-empts the question: e.g. "Schools for Registered Nurse" (by_soc) vs "Schools teaching Nursing BSN producing Registered Nurse" (by_cip_and_soc). | Rely on visionary's hierarchy alone — rejected; entry context fades after navigation, the title chip is durable. |
| 12 | This spec **supersedes** `docs/specs/feature-school-discovery.md`. That skeleton is retired without implementation. | The school-discovery skeleton was tied to Set Your Course's `school_gap` chip CTA, never implemented (no route, no router, no component). Its surface area is fully covered by this spec's `by_cip_and_soc` mode (sourced from inside an active build) plus Spec B's career-search header entry. Maintaining a parallel never-shipped skeleton is dead weight. | Keep both as separate future work — rejected; surface-area duplication. |
| 13 | Optional `min_program_confidence` knob (default `low` = permissive) added to the MCP tool. | `confidence_tier_program` is a stored sample-size proxy on every PCP row (high/medium correspond to `completions_count >= 30`). v1 does not enable a default threshold because the demo benefits from broader coverage; v1.1 may default `medium` once empty-state UX is validated. | (a) Hard-code a completer threshold (rejected — premature); (b) join out to source data at query time (rejected — cross-zone bleed). |

### Constraints

- **One component, one service, one MCP tool, two endpoints.** Resist the
  temptation to fork code paths between modes. The mode parameter changes a
  WHERE clause and a title string — not a code path.
- **The service does NOT open DuckDB.** It calls `mcp_client.call`. The MCP
  handler is the single canonical Gold-zone reader. (See §2 Decision #7 +
  architect C1.)
- **Existing data, existing patterns.** No new Iceberg tables, no new schema
  evolution. Reuses `consumable.program_career_paths` and the
  `get_career_paths` tool layout in `src/mcp_server/futureproof_server.py` as
  a precedent.
- **No pentagon visualization on this surface.** Table only. Stating twice
  because the failure mode is obvious.
- **Build context is OPTIONAL at the API layer.** When present, used to mark
  the anchor row. When absent (Spec B click-through with no build), the
  endpoint returns a clean ranked list with no anchor.
- **Hackathon deadline.** May 18, 2026. Bias every architect/visionary
  trade-off toward "ship the small thing that makes the demo work."

### Out of Scope (parked future specs)

- A `/careers` browse-all-careers route (Spec B handles intent-search; raw
  browse is parked).
- Pentagon-vs-pentagon comparison UI.
- Multi-career compare ("show me schools that are good for *both* nursing and
  data science").
- Student-tunable rank weights ("I weight ROI 2x").
- Distance / zip sort.
- Saving / sharing leaderboard snapshots.
- Affordability simulator on the leaderboard (loan_pct stays at the build
  level; this surface is read-only against PCP).
- Per-school Gemma narration on the table rows.
- RPP cost-of-living adjusted earnings column.
- UI state-filter affordance (param exists at MCP/HTTP level).
- An action affordance on the `CareerCard` list rows of `BuildResultsScreen`
  for `by_soc` mode (drill-in via `CareerDetail` is the single v1 path).

---

## §3 UI/UX Design

### Design Vision: COMPLETE

@fp-design-visionary — 2026-04-29.

---

### A. Emotion First

Before any pixel: name what the student feels.

| Mode | Emotional target |
|------|------------------|
| **`by_soc`** ("Compare schools for this career") | **Curious validation.** The student is on Reveal having just witnessed their bear evolve into a Financial Analyst. The leaderboard answers a sideways question — "could I be doing this somewhere stronger?" — without re-litigating the build. It should feel like leaning out of the window of their own car to see the same road from a slightly different mile marker. *Not* a ranking gauntlet, *not* a buyer's-remorse generator. The anchor row pinned at its absolute rank is the whole point: "you are on the road, here is how far down the road you are." |
| **`by_cip_and_soc`** ("Other schools with this major") | **Tightest apples-to-apples honesty.** The student is on BuildResults, name + emoji + school + major are now fixed identity. The question is the most clinical one in the product: "the EXACT same row at a different school — what does the salary line look like?" This mode is closer to a board game's stat sheet — quiet, dense, monospace. Pride should NOT spike here; respect should. |

Both share a guarantee: **the leaderboard never shames the student's school.** A school in #14 is a school that exists at #14 — the row's data is its testimony. We don't outline anchor rows in red. We don't add deltas like "−$8,400 vs. #1." The anchor uses the build's identity color as a quiet underglow, like a bookmark, and the student decides what to feel.

---

### B. Container Surface (per entry point)

**Decision differs by entry point.** They live on screens with very different motion budgets, so we treat them differently and accept the asymmetry.

#### `by_soc` — slide-in side **sheet** (right edge)

Triggered from `CareerDetail` inside `RevealScreen.tsx:313`. Reveal already spent its motion budget on the cinematic pentagon-and-bear sequence at delays 2.8 / 3.0 / 3.3 / 3.7s. Pushing a route would unmount the bear; expanding in place would shove the pentagon off-screen and break the cinematic frame. **A side sheet preserves the bear in peripheral vision** while focusing attention on a new surface.

```
container:        position fixed, right: 0, top: 0, bottom: 0
width:            min(880px, calc(100vw - 64px))
                  → mobile: 100vw with 16px top inset (Bottom Sheet variant; see Mobile)
background:       bg-bp-mid
border-left:      1px solid border-default
border-radius:    radius-xl 0 0 radius-xl  (left edge only — visually a "drawer pulled out")
shadow:           shadow-lg
backdrop:         rgba(18, 19, 31, 0.55) with backdrop-blur(6px)
                  on the rest of the viewport (NOT a black-out — we want the bear half-lit behind it)
entrance:         x: 100% → 0 with springs.smooth, opacity 0 → 1 over 220ms
exit:             reverse, springs.snappy
focus:            traps inside sheet on open; Escape closes; click on backdrop closes; focus returns to trigger
z-index:          above PageContainer, below global Toast
```

The sheet's first child is a **header bar** (sticky top, `bg-bp-mid` with a 1px `border-border-subtle` on its bottom edge) that always shows: the mode chip (durable — see §B.B below), the panel title, and a 40×40 close button (ghost, `text-text-secondary`, `:hover` → `text-text-primary`, X icon, `aria-label="Close panel"`).

**Why a sheet, not a modal:** modals are 560px max-width and centered. The leaderboard is a wide table — even after column collapse it wants ≥720px to breathe at desktop. A sheet honors that. Centered modals also obscure the bear, which kills the "leaning out of the window" emotional frame.

#### `by_cip_and_soc` — **expand-in-place** disclosure panel

Triggered from `BuildResultsScreen.tsx`, slotted **inside the Path + Institution grid as a horizontal full-width panel directly below it** (after `</div>` closing the grid at ~line 600, before the Section 3 "Build Stats" header). BuildResults is already a *long, scroll-driven* page — `PathCard`, `FinancesCard`, `InstitutionCard`, `PentagonChart`, `BossGauntlet`, `BranchTree` preview, `Save`. Pushing a sheet here would feel like ducking out of the page; pushing a route would break the back-button reading flow.

The expand-in-place pattern is **a card that grows in height** when the trigger is clicked, with the rest of the page pushed down beneath it. Anchor stays in place. This matches the Brightpath inline-expansion idiom established by the Clarifier.

```
container:        the panel renders inline, full-width within max-w-[1280px] mx-auto px-4 tablet:px-6 desktop:px-8 (matches BuildResults content column)
background:       bg-bp-mid
border:           1px solid border-default
border-radius:    radius-xl
shadow:           shadow-md
padding:          space-6 (24px) on tablet+, space-4 (16px) on mobile
margin-top:       space-12 (48px) — same rhythm as the "Section 3" gap
header bar:       sticky top: 56px (clears AppHeader); bg-bp-mid; bottom border border-subtle
                  collapse-toggle as a ghost chevron button on the right
                  (aria-expanded, aria-controls)
entrance:         height auto-expand via Framer Motion height: 0 → "auto" + opacity 0 → 1
                  springs.smooth, ~220ms
                  inner stagger reveals fire AFTER the height settles (delay 0.18)
collapse:         same animation reversed
                  collapsed state shows ONLY the header bar (~64px tall)
                  with an inline preview pill: "Top: {institution_name_of_rank_1} · ranked among {N}"
```

**Why expand-in-place, not a sheet:** the by_cip_and_soc mode is part of the *build inspection* flow, not a side-quest. Students will scroll back and forth between this table, the FinancesCard, and the PentagonChart to make a decision. Forcing them through a sheet open/close cycle for each comparison would interrupt the deliberation. The collapsed-header pill is the small thing that makes the demo work — at a glance, before opening, the student already knows there ARE peers and how many.

#### Why the asymmetry is OK

The mode chip carries the disambiguation either way (Decision #11). The component is one file; the *outer shell* differs by an `enclosure: "sheet" | "inline"` prop. Internal table layout is byte-identical. Two surfaces; one truth.

---

### B.B Mode Disambiguation Chip (durable in title)

Decision #11 says **durable**. The chip lives in the **header bar** (sticky in both enclosures), to the left of the panel title. It does not scroll out of view, ever.

#### Token treatment

```
display:          inline-flex, align-items: center, gap: 6px
padding:          4px 10px
border-radius:    radius-full
font-family:      font-data (Space Mono)
font-size:        text-micro (12px)
font-weight:      700
letter-spacing:   0.06em
text-transform:   uppercase
```

**by_soc mode chip (insight family — "lateral peek across schools"):**
```
background:       rgba(184, 169, 232, 0.12)       /* accent-insight @ 12% */
border:           1px solid rgba(184, 169, 232, 0.28)
color:            text-accent-insight
glyph:            ◇ prefix (rendered as a 6px insight diamond, font-data)
label:            BY CAREER
```

**by_cip_and_soc mode chip (info family — "your major, elsewhere"):**
```
background:       rgba(123, 184, 224, 0.12)       /* accent-info @ 12% */
border:           1px solid rgba(123, 184, 224, 0.28)
color:            text-accent-info
glyph:            ◇ prefix
label:            BY MAJOR + CAREER
```

**Why two different accents:** the student should be able to *feel* — not just read — the difference between the two leaderboards. Insight (purple) for the broad cross-career view; info (blue) for the precise within-major view. Both are cool tones (we reserve thrive/alert/caution for the build's identity and the row-level outcomes), so the chip never competes for attention with the row data.

**Why mono caps:** monospace + uppercase reads as a *system label*, not a button. Students don't accidentally click it. It's an identifier, not an action.

#### Title copy (refined per mode)

The §1 working titles are too long to pin durably. Refined Brightpath voice:

| Mode | Header Title (Fredoka, `text-heading`, font-semibold) | Header Subtitle (`text-body`, `text-text-secondary`) |
|------|-------------------------------------------------------|---------------------------------------------------|
| `by_soc` | **Schools for Financial Analysts** | "Programs that produce this career, ranked." |
| `by_cip_and_soc` | **Schools teaching Marketing → Brand Manager** | "The same row at a different school." |

Title interpolation: `Schools for {occupation_title_plural}` (by_soc) and `Schools teaching {program_name_short} → {occupation_title}` (by_cip_and_soc). The arrow "→" is literal Unicode U+2192 — same glyph used elsewhere in Brightpath ("Fight the Bosses →").

Pluralization for `by_soc`: backend exposes `occupation_title` already; the frontend appends "s" only when the title doesn't already end in "s" or "ans" (handled in i18n template, no smart inflection — fall back to "Schools producing {occupation_title}" if pluralization is uncertain).

`{program_name_short}` truncates at 28 chars with ellipsis to keep the title from wrapping past 2 lines on mobile.

---

### C. Table Row Treatment

#### Row architecture

A flat dark-on-dark table. Not a card grid. The table is the message: "rows are commensurate, comparable, sortable in your head."

```
table container:    bg-bp-mid (inherits from panel surface — no nested elevation)
column gap:         16px (gap-4)
row gap:            0 — rows separated by border-subtle bottom only
row height:         56px desktop (comfortable touch target stacking)
                    48px tablet
                    auto on mobile (cards)
header row:         sticky top: 64px inside scrollable area (clears the panel header bar)
                    bg-bp-mid
                    typography: font-body, text-micro (12px), font-semibold, text-text-muted, uppercase, letter-spacing 0.04em
                    bottom border: 1px border-subtle
data row:           bg transparent (inherits bg-bp-mid)
                    bottom border: 1px border-subtle (last row borderless)
                    transition: background-color duration-fast
hover (data row):   bg-bp-surface (no scale, no shadow — restraint)
                    cursor: default (rows are NOT clickable in v1; no drill-in)
focus-visible:      2px focus-ring inset (info @ 40%) on the row
```

#### Typography per cell

| Cell | Font | Size | Color (default) | Notes |
|------|------|------|-----------------|-------|
| Rank | `font-data` | `text-data` (16px) | `text-text-muted` | "1", "2", "3"… right-aligned within column. Anchor row's rank is `text-text-primary`, font-bold. |
| School | `font-body` | `text-body` (16px), font-semibold (600) | `text-text-primary` | Truncate via `truncate` class at column width; native `title` attribute provides full name on hover. |
| Program | `font-body` | `text-small` (14px) | `text-text-secondary` | Secondary line; truncate at column width. |
| State | `font-data` | `text-data-sm` (13px) | `text-text-muted` | "IN", "CA". Right-aligned. |
| ERN | `font-data` | `text-data` (16px), font-bold | `text-stat-ern` always | "8" — the digit only, no "/10" (header sets context). |
| ROI | `font-data` | `text-data` (16px), font-bold | dynamic per `roiColorClass` value mapping (see below) | "9" — digit only. |
| Earnings (1yr) | `font-data` | `text-data` (16px) | `text-text-primary` | `fmtMoney(earnings_1yr_median)` — exactly the existing helper at `CareerDetail.tsx:23`. Render `—` on null. |
| Net price | `font-data` | `text-data` (16px) | `text-text-secondary` | `fmtMoney(net_price_annual)`. The Decision #8 residency-aware label reuses the existing private/public logic from `FinancesCard` — extract a shared helper if not already present. |
| Confidence | (badge — see below) | — | — | Visual treatment: dot + label, NOT a chip. The chip vocabulary is reserved for the durable mode chip. |

**ROI color rule:** the existing `roiColorClass(dte)` in `CareerDetail.tsx:9` maps `debt_to_earnings_annual` (a continuous DTE float) to color. On the leaderboard, we don't have `debt_to_earnings_annual` in the row response — we have the integer `stat_roi` (1–10). Map directly off `stat_roi`:

```ts
function statRoiColorClass(roi: number | null): string {
  if (roi === null) return "text-text-muted";
  if (roi >= 7) return "text-accent-thrive";
  if (roi >= 4) return "text-accent-caution";
  return "text-accent-alert";
}
```

**ERN color rule:** stat-ern is always `text-stat-ern` regardless of value — the digit IS the meaning. We don't double-encode.

#### Confidence column visual

A 6px dot + a one-character label:

```
container:         inline-flex, align-items: center, gap: 6px
dot (span):        width 6px, height 6px, radius-full
label:             font-data, text-data-sm (13px), text-text-muted
```

| `overall_confidence` | Dot color | Label |
|----------------------|-----------|-------|
| `high` | `text-accent-thrive` (background dot) | "HIGH" |
| `medium` | `text-accent-caution` (background dot) | "MED" |
| `low` | `text-accent-alert` (background dot) | "LOW" — only visible after the "show all" escape hatch is triggered |

Tablet/mobile: the column hides; the dot moves inline next to the school name with no label.

#### Anchor row treatment (per Decision #5: append-only v1)

The anchor row is **the build's identity color, used as a quiet left-edge accent and a faint background tint**. It does NOT shout. The student already knows it's their build — we just need it findable when the table is at scroll-bottom.

For v1, the build's identity color is **`text-accent-thrive`** (matches the Hero Identity treatment on BuildResults — the same green that says "you, here, now"). If a future spec parameterizes per-build accent (e.g. by animal), this row honors that.

```
row background:    rgba(125, 212, 163, 0.06)   /* thrive @ 6% — barely there */
row left-border:   inset 0 0 0 0 ... actually a 3px solid accent-thrive on the left edge
                   (use `box-shadow: inset 3px 0 0 0 var(--color-accent-thrive)` so the
                    row doesn't shift width; matches the Substitution-notice idiom in CareerDetail)
row top-margin:    when appended (anchor_in_top_n === false), insert a 1px dashed
                   border-border-strong divider ABOVE the anchor row, with a centered
                   inline label: "Your school" — font-body, text-small, text-text-secondary,
                   bg-bp-mid, padded space-2 horizontal so the dashed line breaks around it
                   (CSS pseudo: ::before flex 1 + ::after flex 1, both height: 1px,
                   background image: dashed)
rank cell:         text-text-primary, font-data, font-bold (overrides muted default)
school cell:       text-text-primary, font-bold (already bold; promote to 700)
                   prepend a tiny "◆" glyph (font-data) in text-accent-thrive,
                   margin-right: 6px — the student's bookmark
data cells:        unchanged from default styling (don't double-encode)
ARIA:              aria-label="Your school: {institution_name}, ranked {rank} of {total_qualifying_programs}"
                   role="row" inherits from <tr>; the row has data-anchor="true" + a
                   visually-hidden <span class="sr-only">Your school</span> at the start of the school cell
data-testid:       row-anchor-{unitid}-{cipcode}
```

The dashed "Your school" divider is the *only* visual cue that distinguishes appended-anchor from in-place-anchor. When the anchor IS in the top-N (P2 polish; v1 still appends per Decision #5), the divider doesn't render. When v1.1 adds in-place highlight, the cells swap but the box-shadow + tint stay identical — `is_anchor: bool` is the single source of truth, and the layout doesn't fork.

#### "Ranked among N programs" footer

Below the table, a single line:

```
font-body, text-small (14px), text-text-muted, mt-4, text-center
"Ranked among {total_qualifying_programs} programs nationwide."
```

This is the demo-winning small thing: it tells the student that the table is a *slice* of a real universe, not "the only 10 schools that exist." Without it, top-10 looks arbitrary. With it, top-10 looks selected.

When `state_filter_applied` is set (v1.1), append " in {state_abbr}". Not in v1.

---

### C.1 State Designs

#### Default — populated, ≥5 rows

The table renders top-N (default 10) with the anchor row treatment as specified. First-open stagger reveal (see §E).

#### Loading

Skeleton rows. **Eight rows minimum** — enough to telegraph the table shape; not so many that the eventual settling feels long. No global spinner. No "Loading…" text.

```
skeleton row:      height 56px (same as data row)
cell skeletons:    rounded-md, bg rgba(255, 255, 255, 0.04), 60% width
                   for school col, 30% width for rank, 70% width for program,
                   uniform 40% for data cells
animation:         each cell carries .animate-skeleton-shimmer
                   (1.4s ease-in-out infinite, x: -100% → 100%, gradient sweep
                    from rgba(255,255,255,0.04) → rgba(255,255,255,0.08) → ...)
                   stagger: 80ms between rows so the wave reads as motion
```

The header row and panel header bar render at full fidelity during loading — only the data rows are skeletons. This signals "the surface is ready, the data is coming," not "everything is broken."

Loading state lasts a minimum of 200ms even on instant cache hits — sub-200ms flashes feel jarrier than no animation at all. Use a `loading: boolean` derived state with `useDeferredValue` on the response.

#### Empty — 0 rows after filter

Honest one-liner, then the **escape hatch**:

```
container:         padding: space-12, text-center
icon:              none — empty states stay textual; visuals here would cheapen the moment
title:             font-display, text-subheading, text-text-primary
                   "No high-confidence matches yet."
sub:               font-body, text-body, text-text-secondary, max-w-[480px], mx-auto, mt-2
                   by_soc:        "Try lowering the confidence floor to see emerging programs that haven't built up enough sample size yet."
                   by_cip_and_soc:"This major and career combination has thin coverage at high confidence. Lowering the floor surfaces programs in the data we know less about."
escape hatch:      mt-6, a primary button (see below)
                   label: "Show all programs"
                   onClick → re-fetch with min_confidence='low'
                   AFTER click → button stays in place; the table replaces the empty state below it; if
                   STILL empty (no rows even at 'low'), the empty-state message updates to
                   "No programs in the data for this {career|major + career}." and the button hides
```

The "Show all programs" button uses the `secondary` button variant (Brightpath secondary: `bg-bp-surface`, `border-default`, `text-text-primary`). Not a primary CTA — we don't want the student to feel they're missing the *real* answer.

#### Sparse — 1–4 rows

Render what exists. **No padding rows. No "and X more" placeholders.** Below the data: a `text-small text-text-muted` line: "Only {N} program(s) cleared the high-confidence filter for this {career|major + career}." Optional secondary action: "Show all programs" (same as empty-state escape hatch) inline as a ghost chip below that line.

#### Anchor-not-in-top-N — appended

The default v1 behavior. After top-N rows, the dashed divider with "Your school" label, then the anchor row. See §C anchor row treatment.

#### Anchor-IS-in-top-N — in-place (P2; v1 still appends)

Per architect resolution #7, v1 ships *append-below regardless*. When `anchor_in_top_n === true`, the response contains the anchor's row inside `rows[0..limit-1]` with `is_anchor: true`. The component renders that row with the anchor treatment in place, no dashed divider, no duplicate row at index N+1. The visual contract is identical to the appended case minus the divider.

#### Anchor-absent (Spec B click-through with no build)

When neither `build_unitid` nor `build_cipcode` is present in the request, the response carries no `is_anchor: true` row. The component renders the table cleanly: no anchor styling on any row, no "Your school" divider, no warning banner. The header subtitle stays the same — we don't apologize for not having an anchor.

#### Confidence-fallback-applied state (after "Show all" click)

When `min_confidence='low'` is the active filter, a **persistent caption** appears beneath the panel header:

```
container:         px-6 py-2, bg rgba(242, 212, 119, 0.06), border-l-[3px] border-accent-caution, mb-4
copy:              font-body, text-small, text-text-secondary
                   "Showing all programs, including low-confidence rows. Programs with smaller sample sizes appear here."
action:            inline-text "Restore default filter →" — onClick → re-fetch with min_confidence='medium'
                   font-body, text-small, text-accent-info, hover: brightness-125, cursor-pointer
```

This is the only place we surface the confidence-tier nuance. The bar is the receipt — the student opted in, we honor that, but we also offer the gentle return path.

---

### D. Columns + Responsive Collapse

#### Desktop (≥1200px) — full 9 columns

Order, left-to-right:

```
| #   | School (program below)        | State | ERN | ROI | Earnings   | Net price  | Conf |
| --- | ----------------------------- | ----- | --- | --- | ---------- | ---------- | ---- |
| 1   | Stanford University           | CA    |  9  |  9  | $115,400   | $61,200    | HIGH |
|     | Computer & Information Sci…   |       |     |     |            |            |      |
```

Column widths via `grid-template-columns` on a CSS grid (NOT a `<table>`; semantic `role="table"` + `<div role="row">` per row, for stickiness + responsive simplicity):

```
desktop (>=1200): 56px | 1fr (min-w 240px) | 56px | 56px | 56px | 128px | 128px | 96px
tablet (>=768):   48px | 1fr (min-w 200px) | 48px | 56px | 56px | 120px | 120px | (Conf hides)
mobile (<768):    card-stack — see Mobile below
```

**School column composition:** primary line is `institution_name` (font-body, text-body, font-semibold). Secondary line is `program_name` (font-body, text-small, text-text-secondary, mt-0.5, truncate). On focus or hover of the row, a third line appears underneath (transition opacity duration-fast): the `cipcode` in `font-data text-data-sm text-text-muted`. This honors the spec's "show cipcode as secondary metadata only on focus."

#### Tablet (768–1199px)

Hide: **Confidence column**. The dot (without label) attaches to the right of the school name as a 6px circle.

Keep: rank, school+program, state, ERN, ROI, earnings, net price.

#### Mobile (<768px) — card-stack

Cards, not tables. Each row becomes:

```
card:              radius-lg, padding space-4, bg-bp-mid, border 1px border-subtle, mb-3
                   anchor card: border-l-[3px] border-accent-thrive (instead of subtle on left)
                                + bg rgba(125, 212, 163, 0.06)
top row (flex):    rank pill (left) + school name (center, flex-1, truncate) + state (right)
                   rank pill: 28px×28px, radius-full, bg-bp-surface, font-data text-data-sm font-bold,
                              text-text-secondary; anchor card: bg-accent-thrive, text-text-inverse
school name:       font-body text-body font-semibold text-text-primary
program line:      font-body text-small text-text-secondary, truncate, mt-1
stats bar (flex):  mt-3, gap-4
                   ERN block: font-data text-micro text-text-muted "ERN" + below it font-data text-data font-bold text-stat-ern "{N}"
                   ROI block: same shape + statRoiColorClass color
                   visual divider: a 1px vertical hairline border-subtle between ERN and ROI block
cost row (flex):   mt-3, justify-between
                   left: font-body text-micro text-text-muted "EARNINGS" + font-data text-data text-text-primary "{fmtMoney(earnings_1yr_median)}"
                   right: font-body text-micro text-text-muted "NET PRICE" + font-data text-data text-text-secondary "{fmtMoney(net_price_annual)}"
confidence dot:    inline at top-right of the card, next to state — 6px dot, no label
```

The card-stack pattern preserves *every* data point except the confidence label, and the rank/anchor signaling stays unmistakable.

#### What we do NOT show, ever (locked)

- `composite_score` — server-internal, never on wire (architect C3).
- Pentagon visualization on this surface (Decision #2).
- A "delta from #1" column. The student can do their own math; we don't manufacture a pang.
- Any "Limited data" caveat per `feedback_no_substitution_caveat` — the confidence filter is the caveat.

---

### E. Motion

Restraint. The leaderboard is a stat sheet; over-animating it cheapens the data.

#### First-open sequence (open-and-stagger)

Triggered when `enclosure === "sheet"` opens for the first time per session, OR `enclosure === "inline"` toggles to expanded for the first time per session. The component owns a `hasOpenedOnce` ref so subsequent re-opens skip the stagger.

```ts
// Container
const containerVariants = {
  initial: hasOpenedOnce.current ? false : { opacity: 0, x: enclosure === "sheet" ? 480 : 0, height: enclosure === "inline" ? 0 : "auto" },
  animate: { opacity: 1, x: 0, height: "auto", transition: springs.smooth },
};

// Row stagger
const tableVariants = {
  animate: {
    transition: {
      delayChildren: 0.18,    // wait until container settles
      staggerChildren: 0.08,  // stagger.normal — 80ms
    },
  },
};

const rowVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: springs.smooth },
};
```

The anchor row, when appended, gets a *separate* slightly-delayed reveal: it lands 200ms after the last top-N row, not as the next staggered child. This is the small thing that matters — the student sees the leaderboard land first, *then* their school slides into place beneath it. The delay creates the emotional beat: "okay, here's the league. … and here's me."

```ts
const anchorRowVariants = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0, transition: { ...springs.smooth, delay: 0.18 + (limit * 0.08) + 0.2 } },
};
```

Subsequent re-opens use `initial={false}` — the panel and rows are simply visible. No re-stagger, no flicker, no lag.

#### Filter-changed re-fetch

When the student clicks "Show all programs" (or "Restore default filter"), the row stagger does NOT re-run. Instead:
- Existing rows fade out via `AnimatePresence` exit (opacity 1 → 0, springs.snappy, 120ms).
- New rows fade in (opacity 0 → 1, springs.snappy, 120ms) — no y-translation.
- Total transition under 250ms. Refilter feels like a **swap**, not a relaunch.

Screen reader note: when rows replace, fire a `aria-live="polite"` announcement ("Showing {N} programs at low-confidence floor.") on the empty-state container — see §G.

#### Hover / press

- Row hover: `bg-bp-surface` background fade, `transition-colors duration-fast` (150ms ease-out). No translate, no shadow. Rows are not clickable in v1.
- Close button hover: `text-text-muted` → `text-text-primary`, `bg-bp-surface` background, `transition-colors duration-fast`.
- "Show all programs" button press: `transitions.press` (`scale: 0.97` snappy).

---

### F. Trigger Affordances

#### `by_soc` trigger — on `CareerDetail`

**Placement:** new section inside the `<CareerDetail>` card, **after the AI Exposure block** and **before the substitution notice** if present (else before the closing `</div>`). Renders inside the same `bg-bp-mid border border-border-subtle rounded-xl p-6 space-y-5` shell that already structures CareerDetail. Slot in at the bottom of the existing `space-y-5` flow.

**Visual:** a horizontal rule divider above the trigger (`<hr className="border-border-subtle" />`) followed by the trigger button. The hr is the **dashed-feel separator** identical to the chip-rail separator pattern (`border-top: 1px dashed border-subtle`), with no flanking text — this is just a "section break." Then the button.

```
button:            full-width on mobile, flex-row inline-block on desktop
display:           inline-flex, align-items center, gap-2, justify-center
height:            44px (touch target)
padding:           0 space-5 (20px horizontal)
border-radius:     radius-lg
border:            1px solid border-strong
background:        bg-bp-surface
color:             text-text-primary
font:              font-body, text-cta (17px), font-semibold
hover:             bg-bp-raised, border-accent-insight, color text-accent-insight,
                   shadow-glow-insight, transition all duration-normal
press:             transitions.press (scale 0.97)
focus-visible:     2px focus-ring offset 2px
prefix glyph:      a 14px ⇄ icon (font-data), text-accent-insight
                   (the lateral-comparison vibe)
```

The button is *not* a primary CTA (that's "Fight the Bosses"). It's a **lateral, optional, secondary action**. The insight-purple hover state matches the by_soc mode chip, so the student gets a tiny preview of what they're about to open.

**Refined copy (Brightpath voice):** the working label "Compare schools for this career" is fine, but the chosen voice is more inviting:

```
i18n key:           "compareSchools.bySoc.trigger"
label (en):         "Compare schools for this career"  ← keep; we tested four alternatives
                   ("See peer programs", "How does {school} stack up", "Where else does this lead",
                    "Programs producing this career") — none beat the original on directness.
                   The action verb "Compare" is honest; the noun "schools" is concrete.
aria-label:         "Compare schools for this career"  ← same
data-testid:        btn-compare-schools-by-soc
```

#### `by_cip_and_soc` trigger — on `BuildResultsScreen`

**Placement:** a **new ghost-chip-rail-style row** between the Path + Institution grid (closes ~line 600) and the Section 3 "Build Stats" header (line ~603). The grid above ends; the chip rail introduces the panel beneath.

Composition:

```
container:         flex, items-center, justify-between, gap-3, mt-6, mb-2
                   on mobile: flex-direction: column, gap-2, items-stretch
left side:         a small section label
                   font-body, text-small, text-text-muted, italic
                   "Already in the right major?"
                   (this is the "lead-in" voice that frames the chip — same idiom
                    as the chip rail separator on Set Your Course)
right side:        the trigger chip — primary chip variant (see DESIGN.md Chips)
                   BUT in info family (info @ 12% bg, info @ 28% border, text-accent-info)
                   instead of caution, because this is a lateral exploration not a redirect
chip label:        "See it at other schools"
chip prefix:       a 12px ⇄ glyph in text-accent-info
chip aria-pressed: NOT used (this is not a toggle; opening the panel is one-shot)
```

When the panel below is **expanded**, the chip flips to its "ghost toggled-on" state per DESIGN.md §Chips (background → `--color-state-active`, border → thrive @ 28%, prepend `✓` glyph, `aria-pressed="true"`, `aria-controls="panel-compare-schools"`, `aria-expanded="true"`).

**Refined copy (Brightpath voice):** the working label "Other schools with this major" is *technically right* but too clinical for the moment. The build is fresh; the student just saw their bear. **Refined copy: "See it at other schools."** The pronoun "it" elegantly carries forward "your build" (school + major + career) without re-stating it. Reinforced by the lead-in label "Already in the right major?" — which softly poses the question the panel answers.

```
i18n key:           "compareSchools.byCipSoc.lead"     → "Already in the right major?"
i18n key:           "compareSchools.byCipSoc.trigger"  → "See it at other schools"
aria-label:         "See this major and career at other schools"
data-testid:        btn-other-schools-major
```

When the panel is collapsed, the chip rail also displays the **inline preview pill** described in §B (collapsed state), aligned left of the chip on tablet+ and stacked above on mobile:

```
preview pill:       inline-flex, gap-2, px-3 py-1.5, radius-full,
                    bg rgba(255,255,255,0.03), border border-subtle
                    font-body, text-small, text-text-secondary
                    glyph: a 6px thrive dot (you-are-here marker)
                    text: "Top: {institution_name_rank_1} · {N} programs nationwide"
                    (truncate institution_name to 24 chars + ellipsis)
                    onClick: same as the chip — opens the panel
```

The preview pill is the **demo-winning small thing** for this entry. Before the student even clicks, they see "Top: University of Pennsylvania · 184 programs nationwide" — and they're already curious. The panel opens to a place they're already half inside.

---

### G. Accessibility

Extend the brief's table:

| Element | Identifier | Type | Role / aria | Notes |
|---------|------------|------|-------------|-------|
| Compare-schools-by-soc trigger | `btn-compare-schools-by-soc` | `<button>` | `aria-label="Compare schools for this career"` | Keyboard: `Space`/`Enter` opens sheet. |
| Other-schools-with-major trigger | `btn-other-schools-major` | `<button>` (chip variant) | `aria-controls="panel-compare-schools"`, `aria-expanded={open}`, `aria-label="See this major and career at other schools"` | Keyboard: `Space`/`Enter` toggles inline panel. `aria-pressed` is NOT used — toggle semantics handled via `aria-expanded`. |
| Inline preview pill | `pill-leaderboard-preview` | `<button>` | `aria-controls="panel-compare-schools"`, `aria-expanded={open}` | Same target as the chip; secondary tab-stop. |
| Leaderboard sheet (by_soc) | `panel-compare-schools` | `role="dialog"` | `aria-modal="true"`, `aria-labelledby="panel-compare-schools-title"`, `aria-describedby="panel-compare-schools-subtitle"` | Focus trap on open. Returns focus to trigger on close. |
| Leaderboard inline panel (by_cip_and_soc) | `panel-compare-schools` | `role="region"` | `aria-labelledby="panel-compare-schools-title"`, `aria-live="off"` | NOT a dialog — inline. No focus trap; standard tab order. |
| Panel title | `panel-compare-schools-title` | `<h2>` | — | id-target of the region/dialog labelledby. |
| Panel subtitle | `panel-compare-schools-subtitle` | `<p>` | — | id-target of describedby (sheet only). |
| Mode chip | `chip-leaderboard-mode` | `<span>` | `role="status"`, `aria-label="Leaderboard mode: {by career\|by major and career}"` | Decorative-but-announced. |
| Close button (sheet only) | `btn-close-compare-schools` | `<button>` | `aria-label="Close panel"` | Keyboard: `Escape` also closes. |
| Collapse toggle (inline only) | `btn-toggle-compare-schools` | `<button>` | Same `aria-controls`/`aria-expanded` as trigger chip. | Header bar chevron. |
| Table | `table-compare-schools` | `role="table"` | `aria-label="{title text} — {N} rows shown of {total_qualifying_programs} qualifying programs"` | Use semantic `<div role="table">` over `<table>` only because of sticky-header complexity in CSS-grid layout. |
| Header row | — | `role="row"` | — | Cells are `role="columnheader"` with `scope="col"`. |
| Data row | `row-{rank}-{unitid}` | `role="row"` | — | Cells are `role="cell"`. |
| Anchor row | `row-anchor-{unitid}-{cipcode}` | `role="row"` | `aria-label="Your school: {institution_name}, ranked {rank} of {total_qualifying_programs}"` + `data-anchor="true"` | Visually-hidden `<span class="sr-only">Your school</span>` precedes the school name in the cell. |
| "Show all" escape hatch | `btn-show-all-confidence` | `<button>` | `aria-label="Show all programs including low-confidence"` | — |
| "Restore filter" inline | `btn-restore-confidence` | `<button>` | `aria-label="Restore default confidence filter"` | — |
| Confidence-fallback caption | `notice-confidence-fallback` | `<div>` | `role="status"`, `aria-live="polite"` | Announces on appearance: "Showing all programs, including low-confidence rows." |
| Empty state | `empty-compare-schools` | `<div>` | `role="status"` | Static message; the live announcement happens on the fallback caption. |
| Loading skeleton | `skeleton-compare-schools` | `<div>` | `role="status"`, `aria-label="Loading peer schools"` | Skeletons themselves have `aria-hidden="true"`. |

#### Focus order (sheet, by_soc)

1. Close button (top-right of header).
2. Mode chip (programmatically focusable via `tabIndex=-1` only — not in tab order; screen readers announce on dialog open via labelledby/describedby).
3. Panel title (h2; not focusable).
4. *Skip to first row* link (visually-hidden, becomes visible on focus, `font-body text-small text-accent-info underline`).
5. Header row column headers (each `tabIndex=0`? **No** — column headers are not interactive in v1. Skip them.) Actually, skip directly to the first data row. Column headers are `tabIndex=-1`.
6. Data rows (rows are `tabIndex=0`; pressing `Enter` does nothing in v1 — no drill-in. Pressing `Down`/`Up` moves between rows. We don't implement full grid keyboard nav; arrow-keys-between-rows is a v1.1 polish.) **Simpler v1 rule:** rows are NOT in the tab order. The whole table is one tab-stop carrying the table aria-label. Inside-table navigation is a v1.1 concern.
7. "Show all" button (if visible).
8. "Restore filter" inline link (if visible).
9. Cycles back to close button.

`Escape` closes the sheet from any focus position.

#### Focus order (inline panel, by_cip_and_soc)

Standard document tab order, no trap. The collapse toggle in the header bar is part of the order.

#### Screen-reader announcement on filter change

When the student clicks "Show all programs" and the response returns:
- The `notice-confidence-fallback` element renders with `role="status"` + `aria-live="polite"`. The act of mounting it announces its content.
- AVOID announcing the row-count change directly on the table — that would fire on every data change including initial load. The caption is the *single* announcement point.

When "Restore filter" is clicked, the caption unmounts; the act of removing a `role="status"` element does NOT re-announce, so we add a deliberate `<span role="status" class="sr-only">Default filter restored. Showing high and medium confidence programs.</span>` that mounts for 1.5s and unmounts.

#### Reduced motion

Respect `prefers-reduced-motion: reduce`:
- Stagger reveal collapses to a single 200ms opacity fade for the whole table.
- The anchor-row delayed-reveal beat collapses (anchor lands with the rest).
- Filter-change swap collapses to instant.
- Hover/press transitions remain (they're not motion in the vestibular sense).

#### Color-contrast

All text/background pairings already pass WCAG AA at the chosen tokens (verified against Brightpath's published contrast matrix in DESIGN.md §Accessibility). The **anchor row's tinted background** (`thrive @ 6%`) is decorative — `text-text-primary` on `bg-bp-mid` is already AA-compliant; the tint is below the threshold that would change the effective contrast.

The confidence dot is paired with a text label on desktop (color is not the only signifier). On tablet+mobile where the label hides, the dot's *position* (next to the school name) and the row's overall context (low-confidence rows only appear after explicit "Show all" opt-in) carry the meaning.

---

### H. ASCII wireframe — sheet (by_soc, desktop)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ◇ BY CAREER  Schools for Financial Analysts                              [×]   │
│  ─────────────────────────────────────────────                                  │
│  Programs that produce this career, ranked.                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  #    SCHOOL / PROGRAM                       ST   ERN  ROI  EARNINGS    NETPRC  CONF  │
│  ─────────────────────────────────────────────────────────────────────────────  │
│  1    University of Pennsylvania              PA    9    9   $115,400   $24,800  ●HIGH│
│       Finance, General                                                          │
│  2    Princeton University                    NJ    9    9   $108,200   $21,400  ●HIGH│
│       Operations Research                                                       │
│  3    Stanford University                     CA    9    8   $115,600   $61,200  ●HIGH│
│       Management Science                                                        │
│  4    Massachusetts Institute of Technology   MA    9    8   $112,400   $25,300  ●HIGH│
│       Finance, General                                                          │
│  5    University of Michigan-Ann Arbor        MI    8    8    $87,400   $17,800  ●HIGH│
│       Finance, General                                                          │
│  ...                                                                            │
│  10   University of Texas at Austin           TX    7    8    $74,200   $14,600  ●HIGH│
│       Finance, General                                                          │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Your school ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                       │
│  74   ◆ Indiana University-Bloomington        IN    6    7    $58,400   $19,200  ●HIGH│
│       Finance, General                                                          │
│                                                                                 │
│              Ranked among 184 programs nationwide.                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

(◆ glyph and dashed divider mark the appended anchor row. ● is the confidence dot.)

### H.1 ASCII wireframe — inline panel (by_cip_and_soc), collapsed and expanded

```
COLLAPSED:
  Already in the right major?     [Top: U Penn · 184 programs nationwide]   [⇄ See it at other schools]
  ────────────────────────────────────────────────────────────────────────────────────────────────────
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ ◇ BY MAJOR + CAREER  Schools teaching Finance, General → Financial Analyst                  [˅]│
  │ ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔│
  └──────────────────────────────────────────────────────────────────────────────────────────────────┘

EXPANDED:
  Already in the right major?                                              [✓ See it at other schools]
  ────────────────────────────────────────────────────────────────────────────────────────────────────
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ ◇ BY MAJOR + CAREER  Schools teaching Finance, General → Financial Analyst                  [^]│
  │ The same row at a different school.                                                              │
  │ ──────────────────────────────────────────────────────────────────────────────────────────────── │
  │  #    SCHOOL / PROGRAM                       ST   ERN  ROI  EARNINGS    NETPRC  CONF             │
  │  1    University of Pennsylvania              PA    9    9   $115,400   $24,800  ●HIGH           │
  │       Finance, General                                                                           │
  │  2    Princeton University                    NJ    9    9   $108,200   $21,400  ●HIGH           │
  │       Finance, General                                                                           │
  │  ...                                                                                             │
  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ Your school ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                                            │
  │  62   ◆ Indiana University-Bloomington        IN    6    7    $58,400   $19,200  ●HIGH           │
  │       Finance, General                                                                           │
  │                                                                                                  │
  │            Ranked among 184 programs nationwide.                                                 │
  └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### H.2 ASCII wireframe — empty state with escape hatch

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ◇ BY MAJOR + CAREER  Schools teaching Deaf Education → Special Ed Teacher [×] │
│  The same row at a different school.                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                                                                                 │
│                       No high-confidence matches yet.                           │
│                                                                                 │
│       This major and career combination has thin coverage at high confidence.   │
│       Lowering the floor surfaces programs in the data we know less about.     │
│                                                                                 │
│                       [   Show all programs   ]                                 │
│                                                                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### I. Implementation hand-off summary

For the implementer, the §3 contract reduces to:

1. **One file**: `frontend/src/components/CompareSchoolsPanel.tsx`. Props:
   ```ts
   interface CompareSchoolsPanelProps {
     mode: "by_soc" | "by_cip_and_soc";
     enclosure: "sheet" | "inline";
     // Inputs
     socCode: string;
     cipcode?: string;        // required when mode === "by_cip_and_soc"
     occupationTitle: string; // for title
     programName?: string;    // required when mode === "by_cip_and_soc"
     anchor?: { unitid: number; cipcode: string };
     // Sheet only
     open?: boolean;
     onClose?: () => void;
     // Inline only
     defaultExpanded?: boolean;
   }
   ```
2. **Two trigger sites** (modify, do not create new components):
   - `frontend/src/components/CareerDetail.tsx` — append the trigger button at the bottom of the existing space-y-5 flow; manages its own `open` state for the sheet (or lifts to RevealScreen if the team prefers — implementer's call, no behavior difference).
   - `frontend/src/screens/BuildResultsScreen.tsx` — insert the chip rail + collapsible inline panel between Section 2 (Path + Institution grid) and Section 3 (Build Stats).
3. **No pentagon import**. Locked. There is a P0 vitest case that asserts zero `<PentagonChart>` instances in the panel subtree.
4. **i18n strings** to add to `frontend/src/i18n/strings.ts` (English baseline; locale layer wires Spanish per existing pattern):
   ```
   "compareSchools.bySoc.modeChip"        : "BY CAREER"
   "compareSchools.byCipSoc.modeChip"     : "BY MAJOR + CAREER"
   "compareSchools.bySoc.title"           : "Schools for {occupationTitlePlural}"
   "compareSchools.byCipSoc.title"        : "Schools teaching {programNameShort} → {occupationTitle}"
   "compareSchools.bySoc.subtitle"        : "Programs that produce this career, ranked."
   "compareSchools.byCipSoc.subtitle"     : "The same row at a different school."
   "compareSchools.bySoc.trigger"         : "Compare schools for this career"
   "compareSchools.byCipSoc.lead"         : "Already in the right major?"
   "compareSchools.byCipSoc.trigger"      : "See it at other schools"
   "compareSchools.byCipSoc.previewPill"  : "Top: {topSchool} · {totalQualifying} programs nationwide"
   "compareSchools.empty.title"           : "No high-confidence matches yet."
   "compareSchools.empty.subBySoc"        : "Try lowering the confidence floor to see emerging programs that haven't built up enough sample size yet."
   "compareSchools.empty.subByCipSoc"     : "This major and career combination has thin coverage at high confidence. Lowering the floor surfaces programs in the data we know less about."
   "compareSchools.empty.cta"             : "Show all programs"
   "compareSchools.fallback.notice"       : "Showing all programs, including low-confidence rows. Programs with smaller sample sizes appear here."
   "compareSchools.fallback.restore"      : "Restore default filter →"
   "compareSchools.fallback.restored"     : "Default filter restored. Showing high and medium confidence programs."
   "compareSchools.sparse.note"           : "Only {n} program(s) cleared the high-confidence filter."
   "compareSchools.totalLine"             : "Ranked among {total} programs nationwide."
   "compareSchools.yourSchoolDivider"     : "Your school"
   "compareSchools.column.rank"           : "#"
   "compareSchools.column.school"         : "School / Program"
   "compareSchools.column.state"          : "State"
   "compareSchools.column.ern"            : "ERN"
   "compareSchools.column.roi"            : "ROI"
   "compareSchools.column.earnings"       : "Earnings (1yr)"
   "compareSchools.column.netPrice"       : "Net price"
   "compareSchools.column.confidence"     : "Confidence"
   "compareSchools.close"                 : "Close panel"
   "compareSchools.toggle"                : "Toggle leaderboard"
   ```
5. **Reuse existing helpers**:
   - `fmtMoney` from `CareerDetail.tsx:23` — extract to `frontend/src/lib/format.ts` if not already, then both files import.
   - Residency-aware tuition labeling — existing logic per Decision #8; reuse the helper from `FinancesCard` if exposed or extract.
6. **Tests (mockable)**: the design vision is verified by the existing P0 vitest cases listed in §4 New Tests Required (renders correct title chip per mode; renders anchor row when anchor present; renders appended anchor row when below top-N; renders clean when no anchor; renders empty state with drop-confidence escape; does not render pentagon charts). No new tests required from the design vision beyond what §4 already enumerates.
7. **Demo-day choreography**: in the recorded video, the `by_cip_and_soc` flow is the headline. Open BuildResults → see the chip rail with the preview pill ("Top: Penn · 184 programs nationwide") → click → panel grows in place → top-10 stagger lands → 200ms beat → anchor row slides in below the dashed divider with the ◆ marker. **That beat is the moment.** Everything else in this spec serves it.

---

## §4 Technical Specification

### Architecture Overview

This is additive scope. New code lives in three places, all reusing existing
patterns:

1. **MCP tool** (`src/mcp_server/futureproof_server.py`) — a new
   `get_schools_for_career` handler with a `mode` parameter (`by_soc` |
   `by_cip_and_soc`). Filters `consumable.program_career_paths` per mode,
   applies the confidence filter, ranks by composite score using a single
   windowed query (`RANK() OVER`), returns up to `limit` rows plus an optional
   appended anchor row. Modeled on the existing `get_career_paths` handler.
2. **FastAPI endpoints** (`backend/app/routers/careers.py`, new file) — two
   thin HTTP wrappers over a new service module:
   - `GET /careers/{soc_code}/schools` → service with `mode="by_soc"`.
   - `GET /majors/{cipcode}/schools/for-career/{soc_code}` → service with
     `mode="by_cip_and_soc"`.
   Mounted in `backend/app/main.py` alongside existing routers. Spec B will
   later add a third endpoint (`POST /careers/search-from-intent`) to the
   same router.
3. **Frontend** (`frontend/src/components/CompareSchoolsPanel.tsx`, new
   component, plus action affordances in
   `frontend/src/components/CareerDetail.tsx` and
   `frontend/src/screens/BuildResultsScreen.tsx`) — fetches the appropriate
   endpoint per mode, renders the shared table with mode-aware title and
   anchor highlighting per §3.

The service layer (`backend/app/services/schools_for_career.py`) is a **thin
shaper** — it dispatches through `app.services.mcp_client.call` and validates
the response. No DuckDB access in the service.

No Iceberg schema changes. No new tables. No pipeline rerun.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/mcp_server/futureproof_server.py` | Modify | Add `get_schools_for_career` tool (with `mode` param): registration block in `get_tools()`, handler `_handle_get_schools_for_career`, response field whitelist `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS`. Add `_schools_for_career_cache` LRU + register in `_cache_drop_engine` sweep. Add to tools index resource. |
| `backend/app/services/schools_for_career.py` | Create | Pure-function shaper: `def rank_schools_for_career(...) -> SchoolsForCareerResponse`. **Dispatches through `app.services.mcp_client.call("get_schools_for_career", args)`** — does NOT open DuckDB. Validates the MCP response against `SchoolsForCareerResponse` and returns. Matches the existing pattern in `school_lookup.py`, `branch_tree.py`, `stat_engine.py`, `intent.py`, `ask_gemma.py`. |
| `backend/app/routers/careers.py` | Create | New router with TWO leaderboard endpoints (Spec B will add a third). Validates path/query params via FastAPI `Path`/`Query` regex (no runtime re-validation), delegates to the service, returns the Pydantic response. |
| `backend/app/main.py` | Modify | Import + register the new router (`application.include_router(careers.router, tags=["Careers"])`). |
| `backend/app/models/career.py` | Modify | Add Pydantic models: `LeaderboardMode` (Literal["by_soc", "by_cip_and_soc"]), `ConfidenceTier`, `AnchorBuild`, `SchoolForCareerRow`, `SchoolsForCareerResponse`. |
| `frontend/src/types/build.ts` | Modify | Add TS types mirroring the new Pydantic models. |
| `frontend/src/api/careers.ts` | Create | Two functions: `fetchSchoolsBySoc(socCode, opts)`, `fetchSchoolsByCipAndSoc(cipcode, socCode, opts)`. (Spec B extends with `searchCareers` later.) |
| `frontend/src/components/CompareSchoolsPanel.tsx` | Create | The mode-aware panel/sheet component per §3. Accepts `mode` prop; renders mode-specific title chip; uses `mode` to pick the right `fetch*` call. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | Create | Vitest. Cases per §4 New Tests Required. |
| `frontend/src/components/CareerDetail.tsx` | Modify | Add the `by_soc` trigger affordance per §3 (placement decided by @fp-design-visionary). |
| `frontend/src/components/CareerDetail.test.tsx` | Modify | Add ONE test confirming the trigger renders and is wired to open the panel. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Add the `by_cip_and_soc` trigger affordance per §3 (placement decided by @fp-design-visionary). |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Add ONE test confirming the trigger renders and is wired. |
| `frontend/src/i18n/strings.ts` | Modify | Add new strings: triggers, panel titles per mode, mode chip text per mode, columns, empty/anchor states. |
| `tests/mcp/test_get_schools_for_career.py` | Create | Pytest. Cases per §4 New Tests Required (covers BOTH modes). |
| `backend/tests/routers/test_careers_router.py` | Create | Pytest. Cases per §4 New Tests Required. |
| `backend/tests/services/test_schools_for_career_service.py` | Create | Pytest. Cases per §4 New Tests Required. |

### Data Model Changes

No Iceberg / DuckDB / pipeline schema changes. All required fields are already
on `consumable.program_career_paths` per `src/gold/futureproof_engine.py:161`.

#### New Pydantic models (in `backend/app/models/career.py`)

```python
LeaderboardMode = Literal["by_soc", "by_cip_and_soc"]
ConfidenceTier = Literal["high", "medium", "low"]  # high > medium > low

class AnchorBuild(BaseModel):
    unitid: int
    cipcode: str  # XX.XXXX string, never float

class SchoolForCareerRow(BaseModel):
    rank: int                                # 1-based, absolute (server-assigned via RANK() OVER)
    unitid: int
    institution_name: str
    institution_control: str | None
    state_abbr: str | None
    cipcode: str                             # never float — XX.XXXX
    program_name: str
    soc_code: str
    occupation_title: str
    stat_ern: int | None
    stat_roi: int | None
    earnings_1yr_median: float | None
    net_price_annual: float | None
    cost_of_attendance_annual: float | None
    tuition_in_state: float | None
    tuition_out_of_state: float | None
    overall_confidence: ConfidenceTier
    # confidence_tier_program: stored as open string in PCP; the historically observed
    # values are {high, medium, low, insufficient}. Kept open-typed because the upstream
    # transformer in `consumable.career_outcomes` reserves the right to add tiers without
    # a schema change. Frontend treats unknown tiers as 'low'.
    confidence_tier_program: str | None
    match_quality: Literal["full", "partial_no_onet", "partial_no_bls", "scorecard_only"]
    is_anchor: bool                          # true when this row matches the requesting build
    # NB: composite_score is server-internal and is NOT on the wire (architect C3).

class SchoolsForCareerResponse(BaseModel):
    mode: LeaderboardMode
    soc_code: str
    occupation_title: str
    cipcode: str | None                      # populated only in by_cip_and_soc mode
    program_name: str | None                 # populated only in by_cip_and_soc mode
    rows: list[SchoolForCareerRow]           # ranked top-N; appended anchor row at index N when anchor is below top-N
    anchor_in_top_n: bool                    # convenience flag for the frontend
    # total_qualifying_programs: count of RANKABLE rows for this anchor — rows that
    # pass the confidence filter AND have both stat_ern and stat_roi non-null (so the
    # composite formula yields a value). This is the universe the ranking draws from,
    # NOT the unfiltered PCP slice. Used by the frontend to show "ranked among N programs".
    total_qualifying_programs: int
    confidence_filter_applied: ConfidenceTier
    state_filter_applied: str | None
    min_program_confidence_applied: ConfidenceTier  # default 'low' (permissive); future v1.1 may default 'medium'
    generated_at: datetime
```

#### MCP tool surface (in `src/mcp_server/futureproof_server.py`)

```python
{
  "name": "get_schools_for_career",
  "description": "Career-to-school leaderboard. Use this tool when the student wants to COMPARE SCHOOLS for a specific career outcome — not for questions about one school's programs. Key distinction: get_career_paths answers 'what does [school+major] lead to?' — this tool answers 'which schools are best for producing [career]?'. Two modes: 'by_soc' returns all programs nationally that lead to the given occupation, ranked by earnings (ERN) and ROI; 'by_cip_and_soc' narrows to programs in a specific major field (cipcode) that lead to the occupation — the tightest apples-to-apples comparison. When mode='by_cip_and_soc', cipcode is required. Pass build_unitid + build_cipcode together (both or neither) to pin the student's current school as a reference row in the results.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "mode": {"type": "string", "enum": ["by_soc", "by_cip_and_soc"], "default": "by_soc"},
      "soc_code": {"type": "string", "description": "BLS SOC code, e.g. '15-1252' (Software Developers). Required for both modes."},
      "cipcode": {"type": "string", "description": "CIP code, XX.XXXX string. REQUIRED when mode='by_cip_and_soc'."},
      "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 5, "description": "Number of top-ranked programs to return. Default 5 is tuned for chat surfaces — total program count is always returned via total_qualifying_programs regardless. The HTTP endpoint may request up to 25."},
      "min_confidence": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium", "description": "Floor on overall_confidence. Default excludes 'low' rows."},
      "min_program_confidence": {"type": "string", "enum": ["high", "medium", "low"], "default": "low", "description": "Optional floor on confidence_tier_program (the upstream completer-count proxy). Default 'low' means no program-level sample-size filter is applied — the school simply needs programs on the books. Tighten to 'medium' to require completions_count >= 30 at the program level."},
      "state_abbr": {"type": "string", "description": "Optional 2-letter USPS state abbreviation (e.g., 'IN', 'CA', 'NY'). Unknown values return an empty result rather than an error."},
      "build_unitid": {"type": "integer", "description": "Optional. The student's current school IPEDS unitid, used to highlight their program in the leaderboard. MUST be passed together with build_cipcode — either both or neither. Passing only one is treated as no anchor."},
      "build_cipcode": {"type": "string", "description": "Optional. The student's current program CIP code (XX.XXXX format). MUST be passed together with build_unitid — either both or neither."}
    },
    "required": ["soc_code"]
  }
}
```

If `mode == "by_cip_and_soc"` and `cipcode` is missing, the handler returns a
structured error.

#### Response field whitelists — MCP vs HTTP (per genai-architect R4)

The MCP tool surface and the HTTP endpoint response use the SAME Pydantic
model (`SchoolsForCareerResponse`) but DIFFERENT response-field whitelists
when serializing. This is to keep Gemma's chat tool-result payload tight
without sacrificing the HTTP/React table's ability to render the full tuition
breakdown per §3.C.

- **`SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP`** — full row shape used by the
  React table. Includes all 20 row fields: `rank`, `unitid`,
  `institution_name`, `institution_control`, `state_abbr`, `cipcode`,
  `program_name`, `soc_code`, `occupation_title`, `stat_ern`, `stat_roi`,
  `earnings_1yr_median`, `net_price_annual`, **`cost_of_attendance_annual`,
  `tuition_in_state`, `tuition_out_of_state`** (the three tuition fields the
  React table uses for the residency-aware label per Decision #8),
  `overall_confidence`, `confidence_tier_program`, `match_quality`,
  `is_anchor`.

- **`SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_MCP`** — chat-tight whitelist that
  OMITS `cost_of_attendance_annual`, `tuition_in_state`, `tuition_out_of_state`.
  These three fields add ~60 chars per row (8% of row budget) for zero Gemma
  value — `net_price_annual` is the student-relevant cost signal at the chat
  layer. Saves ~250 tokens at `limit=5` and ~1,200 tokens at `limit=25`.

The MCP handler `_handle_get_schools_for_career` selects the whitelist based
on the call origin (or, simpler, ALWAYS uses the MCP whitelist; the HTTP
endpoint reads from the underlying materialized data and does its own field
selection). Implementation-decided detail; documented as a constraint here.

#### Implementation-time hygiene notes (per genai-architect R6, R7)

These do not require additional spec text but the implementer must address:

- **R6:** In `_handle_get_schools_for_career`, set `generated_at` as
  `datetime.now(timezone.utc).isoformat()` (a string) in the returned dict,
  NOT as a raw datetime object. `SchoolsForCareerResponse` Pydantic model
  coerces the ISO string to a `datetime` on `model_validate` — the round-trip
  is safe only if the MCP handler produces a string.
- **R7:** Decorate `_handle_get_schools_for_career` with
  `@timed("get_schools_for_career", extract=...)` consistent with
  `_fetch_crosswalk_socs` (line 1782) and `_build_substituted_rows` (line
  1831). The `extract` lambda should capture `mode`, `soc_code`,
  `cipcode_or_empty`, `row_count`, `cache_hit`. Logging to `logs/gemma.jsonl`
  via `_log_tool_turn` is automatic and needs no additional wiring.

### Service Changes

#### `backend/app/services/schools_for_career.py` (new)

This service is a **thin shaper around `app.services.mcp_client.call`** — it does
NOT open DuckDB. The canonical Gold-zone reader is the MCP server's
`_handle_get_schools_for_career`; the service only dispatches and validates.
This matches the pattern used by `school_lookup.py:39,72`, `branch_tree.py:67`,
`stat_engine.py:448`, `intent.py:180,203,284`, and `ask_gemma.py`.

```python
from app.models.career import (
    AnchorBuild,
    ConfidenceTier,
    LeaderboardMode,
    SchoolsForCareerResponse,
)
from app.services import mcp_client


def rank_schools_for_career(
    mode: LeaderboardMode,
    soc_code: str,
    cipcode: str | None = None,
    limit: int = 10,
    min_confidence: ConfidenceTier = "medium",
    min_program_confidence: ConfidenceTier = "low",
    state_abbr: str | None = None,
    anchor: AnchorBuild | None = None,
) -> SchoolsForCareerResponse:
    """Dispatch to MCP, validate, return."""
    if mode == "by_cip_and_soc" and not cipcode:
        raise ValueError("cipcode is required when mode='by_cip_and_soc'")
    args: dict[str, object] = {
        "mode": mode,
        "soc_code": soc_code,
        "limit": limit,
        "min_confidence": min_confidence,
        "min_program_confidence": min_program_confidence,
    }
    if cipcode is not None:
        args["cipcode"] = cipcode
    if state_abbr is not None:
        args["state_abbr"] = state_abbr
    if anchor is not None:
        args["build_unitid"] = anchor.unitid
        args["build_cipcode"] = anchor.cipcode
    raw = mcp_client.call("get_schools_for_career", args)
    return SchoolsForCareerResponse.model_validate(raw)
```

The DuckDB / Iceberg read happens **exactly once**, inside
`_handle_get_schools_for_career` on `FutureProofMCPServer` in
`src/mcp_server/futureproof_server.py`. That handler implementation contract:

1. **Validate mode invariants.** `by_cip_and_soc` requires `cipcode`; return a
   structured error otherwise. `by_soc` accepts cipcode but ignores it.
2. **Apply common filters in the Iceberg/DuckDB query** against
   `consumable.program_career_paths`. WHERE clause built from:
   - `soc_code = ?` (always)
   - `cipcode = ?` (only when `by_cip_and_soc`)
   - `overall_confidence` IN the set computed from `min_confidence`
     (`high`→{high}; `medium`→{high, medium}; `low`→{high, medium, low})
   - `confidence_tier_program` IN the set computed from `min_program_confidence`
     (default `low` is permissive — no constraint added)
   - `state_abbr = ?` if provided
   - `stat_ern IS NOT NULL AND stat_roi IS NOT NULL` — implicit but mandatory
     so the composite formula yields a value
   - **No `match_quality` predicate.** The proposed `match_quality NOT IN
     ('broad_cip_substituted', 'broad_cip_unblended')` filter was investigated
     against actual stored PCP and found to be a no-op: those values do not
     exist on stored rows. Stored values are `{full, partial_no_onet,
     partial_no_bls, scorecard_only}`; substitution-related values
     (`substituted_cip`, `gemma_expanded`) are runtime-stamped only inside
     `_handle_get_career_paths` and never reach Iceberg. The `partial_no_bls`
     rows that pass `overall_confidence ≥ medium` are dropped automatically by
     the `stat_ern IS NOT NULL` clause (no BLS → no `wage_percentile_overall`
     → no `stat_ern`). See @fp-data-reviewer findings in §5.
3. **Compute composite score in SQL:** `(stat_ern + stat_roi) / 2.0`.
4. **Compute absolute rank in SQL:** `RANK() OVER (ORDER BY composite DESC,
   earnings_1yr_median DESC NULLS LAST, net_price_annual ASC NULLS LAST)`.
   Single windowed query — no second round trip for anchor lookup
   (architect C4).
5. **`total_qualifying_programs`** is the count of rows in this materialized
   ranked CTE (after confidence filters AND the implicit non-null stats
   filter). Compute once from the same CTE.
6. **Top-N selection.** Materialize the full ranked CTE into a Python list
   once, then take `top_n = ranked[:limit]`.
7. **Anchor handling.** If `anchor` is provided:
   - If `(anchor.unitid, anchor.cipcode)` matches a row in `top_n`, set
     `is_anchor=True` on that row. `anchor_in_top_n=True`.
   - Else find the anchor row in the same materialized list; if present,
     append a copy at index N with `is_anchor=True`. `anchor_in_top_n=False`.
   - If absent from the materialized list (anchor failed the filter, e.g.
     low-confidence), no anchor row is returned. `anchor_in_top_n=False`.
   In `by_cip_and_soc` mode, the anchor's cipcode must equal the filter
   cipcode by construction (router rejects mismatch at 422 — see C6).
8. **Trim to response-field whitelist** before serialization (see
   `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS` constant). Composite score is internal
   and is NOT on the wire.

#### MCP cache (per architect C5)

Add to `src/mcp_server/futureproof_server.py`:

```python
_SCHOOLS_FOR_CAREER_CACHE_MAX = 128
_schools_for_career_cache: collections.OrderedDict[
    tuple[int, str, str, str, str, str, str, int],
    # (id(engine), mode, soc, cip_or_empty, min_conf, min_prog_conf, state_or_empty, limit)
    SchoolsForCareerCacheEntry,
] = collections.OrderedDict()
```

- **Cache key:** `(id(engine), mode, soc_code, cipcode_or_empty,
  min_confidence, min_program_confidence, state_abbr_or_empty, limit)`.
  `build_unitid` and `build_cipcode` are NOT in the key — they only affect
  anchor row selection on a copy of the cached materialized list.
- **Eviction:** OrderedDict LRU at `_SCHOOLS_FOR_CAREER_CACHE_MAX`.
- **Engine sweep:** add `_schools_for_career_cache` to the `_cache_drop_engine`
  for-loop at `src/mcp_server/futureproof_server.py:520` so engine reload
  flushes it.
- **Gate:** reuse `FUTUREPROOF_OUTCOMES_CACHE=1` env flag for parity with
  `_career_paths_cache`. No new flag.

#### `backend/app/routers/careers.py` (new)

```python
from fastapi import APIRouter, HTTPException, Path, Query
from app.models.career import (
    AnchorBuild,
    ConfidenceTier,
    SchoolsForCareerResponse,
)
from app.services.schools_for_career import rank_schools_for_career

router = APIRouter(tags=["Careers"])

_CIP_PATTERN = r"^\d{2}\.\d{4}$"


@router.get(
    "/careers/{soc_code}/schools",
    response_model=SchoolsForCareerResponse,
)
def get_schools_for_career_by_soc(
    soc_code: str,
    limit: int = Query(10, ge=1, le=25),
    min_confidence: ConfidenceTier = Query("medium"),
    min_program_confidence: ConfidenceTier = Query("low"),
    state_abbr: str | None = Query(None, min_length=2, max_length=2),
    build_unitid: int | None = Query(None),
    build_cipcode: str | None = Query(None, pattern=_CIP_PATTERN),
) -> SchoolsForCareerResponse:
    anchor = _maybe_anchor(build_unitid, build_cipcode)
    return rank_schools_for_career(
        mode="by_soc",
        soc_code=soc_code,
        limit=limit,
        min_confidence=min_confidence,
        min_program_confidence=min_program_confidence,
        state_abbr=state_abbr,
        anchor=anchor,
    )


@router.get(
    "/majors/{cipcode}/schools/for-career/{soc_code}",
    response_model=SchoolsForCareerResponse,
)
def get_schools_by_cip_and_soc(
    cipcode: str = Path(..., pattern=_CIP_PATTERN),  # C6: regex on Path; FastAPI returns 422 automatically
    soc_code: str = Path(...),
    limit: int = Query(10, ge=1, le=25),
    min_confidence: ConfidenceTier = Query("medium"),
    min_program_confidence: ConfidenceTier = Query("low"),
    state_abbr: str | None = Query(None, min_length=2, max_length=2),
    build_unitid: int | None = Query(None),
    build_cipcode: str | None = Query(None, pattern=_CIP_PATTERN),
) -> SchoolsForCareerResponse:
    anchor = _maybe_anchor(build_unitid, build_cipcode)
    return rank_schools_for_career(
        mode="by_cip_and_soc",
        soc_code=soc_code,
        cipcode=cipcode,
        limit=limit,
        min_confidence=min_confidence,
        min_program_confidence=min_program_confidence,
        state_abbr=state_abbr,
        anchor=anchor,
    )
```

### Open Questions for Architect

All seven Open Questions are now RESOLVED — see §5 architect findings for the
full reasoning. Summary:

1. **Match-quality predicate.** RESOLVED — drop the predicate. Proposed values
   don't exist on stored PCP. (See §2 Decision #6 revised; §5 architect resolution #1; §5 data-reviewer resolution #1.)
2. **Composite score formula.** RESOLVED — `(stat_ern + stat_roi)/2.0`
   confirmed with NULL-on-either drops. (§5 architect resolution #2; §5 data-reviewer resolution #2.)
3. **National vs anchor-state default.** RESOLVED — national. (§5 architect resolution #3.)
4. **Completer-count threshold.** RESOLVED — no join needed. Use stored
   `confidence_tier_program` as the sample-size proxy via optional
   `min_program_confidence` knob, default permissive. (§5 architect resolution #4; §5 data-reviewer resolution #3.)
5. **Anchor-rank query cost.** RESOLVED — single windowed `RANK() OVER` query,
   not two queries. (§5 architect resolution #5.)
6. **Cache strategy.** RESOLVED — reuse existing LRU pattern, key on
   `(engine_id, mode, soc, cip, min_conf, min_prog_conf, state, limit)`. (§5 architect resolution #6.)
7. **v1 anchor highlight (in-place vs append).** RESOLVED — append-below for
   v1; `is_anchor` flag drives identical visual treatment regardless of
   position. (§5 architect resolution #7; §2 Decision #5.)

### Testing Impact Analysis

> Searched `tests/`, `tests/mcp/`, `backend/tests/`, and
> `frontend/src/**/*.test.tsx` for tests touching `get_career_paths`,
> `program_career_paths`, `CareerDetail`, `BuildResultsScreen`, and
> `RevealScreen`.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/mcp/test_get_career_paths.py` | (entire suite) | Low | We do not modify `get_career_paths`. Risk only if a shared helper (e.g. response-field whitelist) is refactored. |
| `tests/mcp/test_cip_substitution.py` | (entire suite) | Low | Confidence-filter logic should not interfere with substitution path. |
| `frontend/src/components/CareerDetail.test.tsx` | "ROI receipt" suite | Low | Adding a trigger button below the existing receipt content. |
| `frontend/src/screens/RevealScreen.test.tsx` (if exists) | reveal sequence | Low | Adding a child component shouldn't affect the reveal animation tests. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | existing build-results assertions | Low | Adding one new action button alongside existing ones. |
| `tests/gold/test_futureproof_engine.py` | PCP derivation | Low | We don't touch the engine. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/components/CareerDetail.test.tsx` | Add ONE new test for the by_soc trigger; do NOT modify the existing "ROI receipt" or "debt-vs-median" tests. | New affordance is a sibling. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Add ONE new test for the by_cip_and_soc trigger. | Same rationale. |
| `backend/app/main.py` | Register the new router. Existing main tests (if any) may need to refresh route counts. | Mechanical addition. |

#### Confirmed Safe (must NOT break)

- `tests/mcp/test_get_career_paths.py` — full suite.
- `tests/mcp/test_cip_substitution.py` — full suite.
- `tests/gold/test_futureproof_engine.py` — full suite.
- `frontend/src/components/CareerDetail.test.tsx` "ROI receipt" suite.
- `frontend/src/screens/RevealScreen` rendering tests.
- All existing `consumable.program_career_paths` row count / DQ tests.

If any of the above breaks, STOP and escalate via §10.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_by_soc_returns_top_n` | SOC with ≥10 high-confidence rows returns 10 rows ordered by composite score desc, mode='by_soc'. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_by_cip_and_soc_filters_to_anchor_program` | mode='by_cip_and_soc' with cipcode='11.0701' and soc_code='15-1252' returns only rows matching both. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_by_cip_and_soc_requires_cipcode` | mode='by_cip_and_soc' without cipcode returns a structured error / 422. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_anchor_appended_when_not_in_top_n` | When anchor's (unitid, cipcode) is below top-N (in by_soc mode), response appends it as the (N+1)th row with `is_anchor=true` and absolute rank. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_anchor_in_place_when_in_top_n` | When anchor is in top-N, exactly one row has `is_anchor=true` and no duplicate row is appended. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_no_anchor_renders_clean` | When neither build_unitid nor build_cipcode is supplied, response has no `is_anchor=true` row and no error. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_low_confidence_rows_excluded_by_default` | Default `min_confidence=medium` filters out `overall_confidence == "low"` rows in BOTH modes. |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_returned_match_quality_values_are_storage_layer_only` | Every returned row's `match_quality` is in `{full, partial_no_onet, partial_no_bls, scorecard_only}` — i.e., the service did not accidentally pull in runtime-stamped rows from the `get_career_paths` substitution path. (Replaces previous `test_broad_cip_fallback_excluded_by_default` per data-reviewer item 4.) |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_partial_no_bls_dropped_by_implicit_stat_filter` | A `partial_no_bls` row that passes `overall_confidence ≥ medium` does NOT appear in rankings — `stat_ern` is NULL on those rows and the composite formula's NULL-in-either-drops behavior excludes them. (Per data-reviewer item 5.) |
| P0 | `tests/mcp/test_get_schools_for_career.py` | `test_empty_after_filter_with_drop_confidence_escape` | An SOC where all rows fail the confidence filter returns `rows=[]`, `total_qualifying_programs=0`. Re-querying with `min_confidence='low'` returns rows. (Per architect concern in §5: empty-after-filter case deserves its own test.) |
| P0 | `backend/tests/routers/test_careers_router.py` | `test_by_soc_endpoint_happy_path` | `GET /careers/15-1252/schools?build_unitid=X&build_cipcode=Y.YYYY` returns 200 with the documented shape. |
| P0 | `backend/tests/routers/test_careers_router.py` | `test_by_cip_and_soc_endpoint_happy_path` | `GET /majors/11.0701/schools/for-career/15-1252?build_unitid=X` returns 200, mode=by_cip_and_soc. |
| P0 | `backend/tests/routers/test_careers_router.py` | `test_invalid_cipcode_format_rejected` | `cipcode="11"` in path → 422 from FastAPI Path regex (no manual validator runs). |
| P0 | `backend/tests/routers/test_careers_router.py` | `test_unknown_soc_returns_empty` | Unknown SOC returns 200 with `rows=[]` and `total_qualifying_programs=0`. |
| P0 | `backend/tests/services/test_schools_for_career_service.py` | `test_composite_score_formula_via_mcp_dispatch` | Service dispatches through `mcp_client.call`; ordering follows `(stat_ern + stat_roi)/2` desc with the documented tiebreak. (Mocks `mcp_client.call` to validate the args + shaping.) |
| P0 | `backend/tests/services/test_schools_for_career_service.py` | `test_mode_dispatches_correct_args` | by_soc and by_cip_and_soc on the same fixture send appropriately filtered args to the MCP. |
| P0 | `backend/tests/services/test_schools_for_career_service.py` | `test_service_does_not_open_duckdb` | The service module imports do NOT include `duckdb` and the service makes no DuckDB connection. (Locks architect C1.) |
| P0 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_correct_title_chip_per_mode` | by_soc title contains occupation_title; by_cip_and_soc title contains both program_name and occupation_title. |
| P0 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_anchor_row_when_anchor_present` | When the anchor unitid+cipcode is in the response, that row carries the anchor styling/identifier. |
| P0 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_appended_anchor_row_when_below_top_n` | When `anchor_in_top_n=false`, the appended anchor row renders with its absolute rank. |
| P0 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_clean_when_no_anchor` | When neither build is set in the response, no anchor row exists and no warning is rendered. |
| P0 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_empty_state_with_drop_confidence_escape` | Empty rows + medium-confidence filter renders the empty state and the "show all" affordance. |
| P0 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `does_not_render_pentagon_charts` | Panel must contain zero `<PentagonChart>` instances. (Locks Decision #2.) |
| P1 | `tests/mcp/test_get_schools_for_career.py` | `test_state_filter_applied` | `state_abbr="IN"` returns only IN rows (both modes). |
| P1 | `tests/mcp/test_get_schools_for_career.py` | `test_limit_param_clamped` | `limit=999` returns ≤25 rows (max enforced). |
| P1 | `tests/mcp/test_get_schools_for_career.py` | `test_min_confidence_low_includes_all` | `min_confidence="low"` includes rows previously filtered. |
| P1 | `tests/mcp/test_get_schools_for_career.py` | `test_min_program_confidence_optional_filter` | `min_program_confidence="medium"` excludes rows where `confidence_tier_program ∈ {low, insufficient}`. (Per data-reviewer item 4.) |
| P1 | `backend/tests/routers/test_careers_router.py` | `test_anchor_only_partially_provided` | `build_unitid` without `build_cipcode` → response treats anchor as None (does not 422). |
| P1 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `formats_money_via_existing_helper` | Earnings + net price are rendered with the same formatting as `CareerDetail`. |
| P2 | `tests/mcp/test_get_schools_for_career.py` | `test_response_field_whitelist_no_pii_leak` | Returned rows contain only the documented fields; `composite_score` is NOT present on the wire (locks architect C3). |
| P2 | `frontend/src/components/CompareSchoolsPanel.test.tsx` | `narrow_viewport_collapses_columns` | At <640px, confidence column hides. |

#### Test Data Requirements

- A test fixture SOC with ≥12 PCP rows spanning multiple confidence tiers,
  states, and CIPs (so by_cip_and_soc filtering is exercised). Reuse an
  existing fixture if available; otherwise add to the conftest used by
  `tests/mcp/`.
- A fixture SOC where ALL rows have `overall_confidence == "low"` (for the
  empty-after-filter test).
- A fixture row with `match_quality == "partial_no_bls"` AND
  `overall_confidence ∈ {high, medium}` AND NULL `stat_ern` (for the
  implicit-drop test).
- Anchor build fixture: a (unitid, cipcode) pair that is intentionally NOT
  in the top-10 for the test SOC.
- A second anchor pair that IS in the top-10.
- Frontend: handcrafted `SchoolsForCareerResponse` JSON in
  `frontend/src/test/fixtures/` covering: by_soc full-10, by_cip_and_soc
  full-N, anchor-in-top, anchor-appended, anchor-absent (no build), empty,
  sparse.

### Gemma-touching work

This spec adds a Gemma-callable surface but does NOT modify any existing
`gemma_client.generate*` call site. Tool-index resource (`get_resources()` in
`src/mcp_server/futureproof_server.py`) gets one new tool advertised.

Verification deliverables (covered by @genai-architect in §10):

- The tool's JSON schema validates against the existing MCP harness.
- The tool's response shape, when JSON-serialized, fits within the configured
  response budget for the chat surface.
- Representative chat queries — "what's the cheapest path to becoming a
  registered nurse?" (by_soc) and "show me schools that teach Marketing and
  produce Brand Managers, ranked by ROI" (by_cip_and_soc) — successfully
  tool-call `get_schools_for_career` end-to-end under both
  `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`. Document
  transcripts.
- Fallback: if the tool is unreachable, Gemma's existing chat-guardrails
  fallback (no tool call) is unchanged.
- `logs/gemma.jsonl` captures the new tool calls with `tool_name` and
  `tool_args`.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED (first pass; re-review required after C1–C7 folded into §1–§4)
**Reviewed:** 2026-04-29

#### System Context

This feature sits at the **MCP -> FastAPI -> React** seam. It reads `consumable.program_career_paths` (Gold zone, the canonical PCP table that already powers `get_career_paths`), exposes it through one new MCP tool with a `mode` discriminator, wraps that tool in two thin FastAPI routes, and renders the result as a single Brightpath table component. No new Iceberg schema, no new pipeline rerun, no new Gold-zone product. It is pure read scope.

The single architectural risk is the **service layer**. The spec proposes a new `backend/app/services/schools_for_career.py` that opens DuckDB read-only directly. That contradicts every existing backend Gold-zone reader (`school_lookup`, `branch_tree`, `stat_engine`, `intent`, `ask_gemma`) — they all dispatch through `mcp_client.call(tool_name, args)`. Letting one service crack the Iceberg/DuckDB layer outside the MCP boundary would create a second canonical Gold-zone reader and is a contract leak. The fix is mechanical and lands in the conditions below. Once that is corrected, the dual-mode shape is sound.

#### Resolutions to "Open Questions for Architect"

1. **Match-quality predicate (where it lives in code).** The proposed predicate `match_quality NOT IN ('broad_cip_substituted', 'broad_cip_unblended')` references values that **do not exist** on `consumable.program_career_paths`. Verified against `src/gold/futureproof_engine.py:132-141`: the real `match_quality` enum is `{"full", "partial_no_onet", "partial_no_bls", "scorecard_only"}`. The "broad-CIP fallback" concept lives at runtime inside `_handle_get_career_paths` (`substitution_applied`, `data_caveat.type in {"blended_substitution", "broaden_cip", "cip_broadening"}`) — it is a per-call substitution path, **not a stored row attribute**. **Architect decision:** the broad-CIP filter is non-applicable for this surface. Default confidence filter is `overall_confidence IN ('high', 'medium')` only, with the implicit `stat_ern IS NOT NULL AND stat_roi IS NOT NULL` doing the rest. The predicate **lives inside `_handle_get_schools_for_career` on the MCP server** (one canonical reader; see C1).

2. **Composite score formula.** `(stat_ern + stat_roi) / 2.0` is **confirmed**. Both stats are integer 1–10, normalized identically by the Gold engine. `WHERE stat_ern IS NOT NULL AND stat_roi IS NOT NULL` so NULL-on-either drops the row. Tiebreak `composite DESC, earnings_1yr_median DESC NULLS LAST, net_price_annual ASC NULLS LAST` is sound.

3. **National vs anchor-state default.** **National.** Decision #9 stands.

4. **Completer-count threshold feasibility.** **Skip a hard threshold for v1.** PCP carries no completer count column. Joining out to silver/raw at query time is unacceptable cross-zone bleed. Use the optional `min_program_confidence` knob instead (default `low` = permissive), threading through `confidence_tier_program` (which IS a stored sample-size proxy per data-reviewer).

5. **Anchor-rank query cost.** **Single windowed query.** The two-query approach has a race-condition footgun and doubles round trips. `SELECT *, RANK() OVER (ORDER BY composite_score DESC, ...) AS abs_rank FROM filtered_rows` gives the absolute rank for free.

6. **Cache strategy.** **Yes — reuse the existing LRU pattern**, keyed on `(engine_id, mode, soc_code, cipcode_or_empty, min_confidence, min_program_confidence, state_abbr_or_empty, limit)`. `build_unitid` and `build_cipcode` MUST NOT be in the key. Add a new `_schools_for_career_cache` ordered dict alongside `_career_paths_cache`, with `_SCHOOLS_FOR_CAREER_CACHE_MAX = 128`. Add to `_cache_drop_engine` sweep. Gate on existing `FUTUREPROOF_OUTCOMES_CACHE=1`.

7. **v1 anchor highlight: append-only vs in-place.** **v1 ships append-below ONLY.** Decision #5 stands. Every row carries `is_anchor: bool`; the in-place vs append distinction is whether the anchor row is returned within `rows[0..limit-1]` (in-place) or as `rows[limit]` (appended). The component renders identically. Visual polish for "in the leaderboard" vs "below it" is P2.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (must address before IMPLEMENTATION)

1. **C1 — Service layer must not open DuckDB directly.** Rewrite the §4 description of `backend/app/services/schools_for_career.py` so it dispatches through `app.services.mcp_client.call("get_schools_for_career", args)` and returns `SchoolsForCareerResponse`. The DuckDB / Iceberg read happens exactly once, inside `_handle_get_schools_for_career` on `FutureProofMCPServer`. **APPLIED in §4.**

2. **C2 — Correct the match-quality predicate.** Replace the proposed predicate with the actual stored values. Default proposal: `overall_confidence IN ('high','medium')` only, no `match_quality` filter. **APPLIED in §2 Decision #6 revised and §4 service contract step 2.**

3. **C3 — Drop `composite_score` from the public response model.** Remove from `SchoolForCareerRow`. Rows carry `rank: int`. **APPLIED in §4 Pydantic model.**

4. **C4 — Use a single windowed query for anchor rank.** Replace §4 service-contract step 8 (two-query design) with a single `RANK() OVER (...)` query. **APPLIED in §4 service contract step 4.**

5. **C5 — Wire the new LRU cache and engine-shutdown sweep.** New `_schools_for_career_cache` + `_SCHOOLS_FOR_CAREER_CACHE_MAX = 128` + `_cache_drop_engine` registration. **APPLIED in §4 MCP cache section.**

6. **C6 — De-duplicate the cipcode validator.** Use `cipcode: str = Path(..., pattern=r"^\d{2}\.\d{4}$")` in the router; remove the runtime regex check. **APPLIED in §4 router code.**

7. **C7 — Tighten `confidence_tier_program` typing.** Either narrow to `Literal[...]` or document the open-string contract with a docstring. Bare `str | None` ships only with explicit comment. **APPLIED in §4 Pydantic model with explicit docstring.**

Once C1–C7 are addressed in the spec text (a doc edit, not code), this spec is ready for IMPLEMENTATION.

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED (first pass; re-review required after the 5 required changes folded into §1–§4)
**Reviewed:** 2026-04-29

#### Data Sources Affected

This spec touches **`consumable.program_career_paths`** (PCP) only — no Bronze
or Silver-zone changes, no new joins to source data.

#### Formula Verification

Composite score: `(stat_ern + stat_roi) / 2.0`. Both inputs traced to source:
- `stat_ern` = `compute_stat_ern(cip_family_earnings_rank, wage_percentile_overall)` — integer 1-10 by construction. NULL-propagates if either input is NULL.
- `stat_roi` = `compute_stat_roi(debt_to_earnings_annual)` — integer 1-10 by piecewise mapping with floor (10) and cap (1). NULL-propagates if `debt_to_earnings_annual` is NULL.
- Iceberg schema declares both columns `IntegerType()` and `required=False`. Confirmed via direct read of `consumable.program_career_paths` (626,406 rows): observed range `[stat_ern: 1..10, stat_roi: 1..10]`.

Both stats are guaranteed integer 1-10 OR NULL. Equal-weight average is
mathematically sound. NULL-in-either-drops is correct.

Tiebreak ordering verified empirically against SOC 15-1252 (Software Developers): produces intuitive top-10 (Stanford 11.07, Princeton 14.09, UW Bothell 14.09 all at composite=10.0, sorted by earnings then by lowest net price).

#### Findings

##### Data Quality Sound

- **`overall_confidence` is reliably populated.** Of 626,406 PCP rows, ZERO have NULL. Schema declares `required=True`. Default `min_confidence=medium` is safe.
- **`min_confidence=medium` produces ranked output for 520 distinct SOC codes** out of ~900 in BLS, with 308 SOCs carrying ≥100 rankable programs.
- **Iceberg schema enforces the data shape.** `match_quality` and `overall_confidence` are `required=True`; pentagon stats are `IntegerType()` not `DoubleType()`.

##### Data Concerns

- **The proposed `match_quality NOT IN ('broad_cip_substituted', 'broad_cip_unblended')` predicate is INCORRECT for PCP-as-stored.** The strings `broad_cip_substituted` and `broad_cip_unblended` do NOT exist on any of the 626,406 stored rows. `substituted_cip` and `gemma_expanded` are runtime-only values that the `get_career_paths` MCP handler stamps at request time (lines 2064 and 2258 of `src/mcp_server/futureproof_server.py`); they never reach the Iceberg table. **Fix:** Drop the predicate entirely. The work it was meant to do is already done by (a) `overall_confidence ≥ medium` and (b) the implicit `stat_ern IS NOT NULL AND stat_roi IS NOT NULL` from the composite formula. All 14,884 `partial_no_bls` rows in the high+medium subset have NULL `stat_ern` and would be dropped by the formula regardless.

- **Substitution/expansion rows do NOT reach this surface.** The new service must SELECT directly from `consumable.program_career_paths`; it must NOT delegate to `get_career_paths`. A P0 test should assert that `match_quality` on every returned row is in `{full, partial_no_onet, partial_no_bls, scorecard_only}`.

- **`partial_no_bls` rows survive the confidence filter but cannot be ranked.** All 14,884 such rows have NULL `stat_ern` and are silently dropped by the formula. This is correct end-state behavior, but it means `total_qualifying_programs` needs a precise definition. **Fix:** Define as "rows passing the confidence filter AND having both stats non-null."

- **Suggested second filter knob: `confidence_tier_program`.** PCP carries `confidence_tier_program` (sourced from `consumable.career_outcomes.confidence_tier`), which IS a sample-size proxy: `confidence_tier_program in {high, medium}` corresponds to `completions_count >= 30` (verified — high tier averages 108 completions, medium 66, low/insufficient capped at 29). **Recommendation (NOT a blocker):** Add an OPTIONAL `min_program_confidence: ConfidenceTier = "low"` parameter (default permissive); v1.1 may default `medium` once empty-state UX is validated.

##### Data Integrity Blockers

None. The fundamental shape is correct. The match_quality predicate issue is an EASY FIX (delete the predicate) rather than a fundamental data-correctness failure.

#### Resolution of the Three Required Questions

**1. Match-quality broad-CIP exclusion predicate.** **The exact set of `match_quality` values that should be filtered out is the empty set** — the proposed predicate is unnecessary because the values it targets do not exist at the storage layer. **Action: drop the `match_quality NOT IN (...)` clause from §4 service contract.** **APPLIED in §2 Decision #6 revised and §4 service contract step 2.**

**2. Composite score formula.** APPROVED. `(stat_ern + stat_roi) / 2.0` is mathematically sound, semantically honest, empirically produces intuitive rankings.

**3. Completer-count threshold.** No join required — `confidence_tier_program` is already on every PCP row. v1: do NOT add a default threshold; DO add an optional `min_program_confidence` knob. v1.1 may default to `medium`. **APPLIED in §4 MCP tool surface and §4 service signature.**

#### Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Required changes before implementation:**

1. **Update §4 service contract** to remove the `match_quality NOT IN (...)` filter. **APPLIED.**
2. **Define `total_qualifying_programs` precisely** as "rows passing the `overall_confidence` filter AND having both `stat_ern` and `stat_roi` non-null." **APPLIED in §4 Pydantic comment.**
3. **Update Open Questions #1 and #4** to RESOLVED. **APPLIED.**
4. **Replace `test_broad_cip_fallback_excluded_by_default`** with `test_returned_match_quality_values_are_storage_layer_only`. Add a P1 test for `min_program_confidence`. **APPLIED in §4 New Tests Required.**
5. **Add a P0 test** asserting `partial_no_bls` rows in the high+medium subset are correctly dropped. **APPLIED in §4 New Tests Required.**

Once these spec edits land, the data-correctness story is solid and I will flip to APPROVED.

---

## §6 Implementation Log

**Status:** IMPLEMENTED (P0/P1 tests pending step 5)

### Files Modified

| File | Change Summary |
|------|---------------|
| `src/mcp_server/futureproof_server.py` | Added `datetime, timezone` import; `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP` (20 fields) and `_MCP` (17 fields, drops 3 tuition fields per genai-architect R4); `_LEADERBOARD_MODES`, `_CONFIDENCE_TIERS_DESC`, `SCHOOLS_FOR_CAREER_SCAN_LIMIT = 5000`; `_SCHOOLS_FOR_CAREER_CACHE_MAX = 128` and `_schools_for_career_cache` LRU; registered cache in `_cache_drop_engine`; new `ToolDef("get_schools_for_career", ...)` in `get_tools()` (with `mode` discriminator, conditional cipcode requirement enforced at handler, `limit` default 5, `min_program_confidence` second knob, anchor-pair contract documented per genai-architect R2); new `_handle_get_schools_for_career` handler (windowed `RANK() OVER` query against `consumable_program_career_paths`, anchor in-place / append / absent paths, ISO 8601 `generated_at` per R6, `@timed` decoration per R7); module-level `_confidence_floor_to_set` helper. |
| `backend/app/models/career.py` | Added `datetime` import; `LeaderboardMode`, `ConfidenceTier`, `LeaderboardMatchQuality`, `AnchorBuild`, `SchoolForCareerRow`, `SchoolsForCareerResponse` Pydantic models. NO `composite_score` on the wire (architect C3). `confidence_tier_program: str \| None` with explicit comment per architect C7. |
| `backend/app/services/schools_for_career.py` (NEW) | Thin shaper around `mcp_client.call("get_schools_for_career", ...)`. Validates response into `SchoolsForCareerResponse`. Does NOT open DuckDB (architect C1). |
| `backend/app/routers/careers.py` (NEW) | Two endpoints: `GET /careers/{soc_code}/schools` and `GET /majors/{cipcode}/schools/for-career/{soc_code}`. Path/Query regex validation via FastAPI (architect C6). Both delegate to `rank_schools_for_career`. Spec B will later add `POST /careers/search-from-intent` to the same router. |
| `backend/app/main.py` | Imported `careers` router; registered with `tags=["Careers"]`. |
| `frontend/src/types/build.ts` | Added `LeaderboardMode`, `ConfidenceTier`, `LeaderboardMatchQuality`, `SchoolForCareerRow`, `SchoolsForCareerResponse` TS types mirroring the Pydantic shapes. |
| `frontend/src/api/careers.ts` (NEW) | `fetchSchoolsBySoc(socCode, opts)`, `fetchSchoolsByCipAndSoc(cipcode, socCode, opts)` over `apiGet`. |
| `frontend/src/lib/format.ts` (NEW) | Extracted `fmtMoney` from `CareerDetail.tsx`; added `roiColorClass`, `statRoiColorClass(roi)` helper for the leaderboard row coloring. |
| `frontend/src/components/CareerDetail.tsx` | Imported `fmtMoney`/`roiColorClass` from `@/lib/format` (deleted local copies); imported `useT`; added `useState` for `compareOpen`; appended `btn-compare-schools-by-soc` trigger button at the bottom of the existing `space-y-5` flow per §3.F; mounted `<CompareSchoolsPanel mode="by_soc" enclosure="sheet" />` with anchor pinned to the build's `(unitid, cipcode)`. |
| `frontend/src/components/CareerDetail.test.tsx` | Added one P0 test (`Compare schools trigger`) confirming the trigger renders, has the correct aria-label, and opens the panel on click. |
| `frontend/src/components/CompareSchoolsPanel.tsx` (NEW) | Mode-aware leaderboard component. Two enclosures: right-edge slide-in `<motion.aside role="dialog">` for `enclosure="sheet"` (with backdrop, ESC handler, focus close button); inline `<section role="region">` with disclosure toggle for `enclosure="inline"`. Header: durable mode chip (`BY CAREER` insight purple / `BY MAJOR + CAREER` info blue) + interpolated title + subtitle. CSS-grid table (7 columns, NOT `<table>`). `is_anchor` rows get thrive accent + ◆ glyph; "Your school" dashed divider before appended anchor. States: loading skeleton (8 rows), error with retry, empty with "Show all programs" escape hatch (drops filter to `low`), `low`-fallback notice with "Restore default filter →". Framer Motion stagger reveal with reduced-motion fallback. Locked: zero `<PentagonChart>` instances rendered. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Imported `<CompareSchoolsPanel>`; inserted inline panel between Section 2 (Path + Institution grid) and Section 3 (Build Stats) per §3.B, with `data-testid="compare-schools-host"`, anchor pinned to the active build. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Added one P0 test (`renders_compare_schools_inline_trigger`) asserting both the host wrapper and the panel region are present after render. |
| `frontend/src/i18n/strings.ts` | Added 32 `compareSchools.*` strings to the `en` block per §3.I. Added empty `ar: {}` block to satisfy `Record<AppLocale, ...>` after `ar` was added to `AppLocale` (`getString` falls through to `en`). |

### Deviations from Spec

- **`SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_MCP` vs `_HTTP` split is documented but not yet used asymmetrically.** The handler emits the HTTP-shape (20 fields) for both call paths in v1. The MCP-shape constant exists for future trimming (genai-architect R4 acknowledged the trimming would only reduce token cost; correctness is unaffected). v1.1 may add a `compact: bool` arg or call-origin sniff to apply the MCP whitelist. Documented in the §4 file-changes table; not a contract violation.
- **`fmtMoney` helper extraction.** Per §3.I item 5 instruction. `CareerDetail.tsx` now imports from `@/lib/format` instead of holding a local copy. Mechanical refactor; no behavior change. Existing `CareerDetail.test.tsx` tests pass unchanged.

### Pre-existing Test Failures (NOT caused by this spec)

Two test files in `frontend/src/components/menu/` carry pre-existing failures unrelated to this spec — verified by running my new tests in isolation (47 passed, 0 failed across `CareerDetail.test.tsx`, `BuildResultsScreen.test.tsx`, `RevealScreen.test.tsx`). The pre-existing failures are:

- `frontend/src/components/menu/CompareView.test.tsx` — 9 failures: `useNavigate() may be used only in the context of a <Router> component`. Modified by commit `d3d8d9c feat: compare view redesign` (this branch) and not since touched.
- `frontend/src/components/menu/PentagonOverlay.test.tsx` — 2 failures: `Unable to find an element by: [data-testid="overlay-legend"]` / `[data-testid="svg-pentagon-overlay"]`. Same commit ancestry.

Neither file is in §4 "Existing Tests at Risk" or "Authorized Test Modifications" — they are out of this spec's blast radius. Flagged here for human review but NOT fixed in this spec per the no-silent-disable rule.

### Verification Run (post-implementation)

| Check | Result |
|-------|--------|
| Backend `ruff check` | ✓ Clean |
| Backend `mypy` (touched files: routers/careers.py, services/schools_for_career.py) | ✓ Clean |
| Backend full `pytest` | ✓ 1232 passed |
| Frontend `tsc --noEmit` | ✓ Clean |
| Frontend `vitest` (touched files only) | ✓ 47 passed (CareerDetail + BuildResultsScreen + RevealScreen) |
| Frontend full `vitest` | ⚠ 11 pre-existing failures in `menu/CompareView.test.tsx` and `menu/PentagonOverlay.test.tsx` — flagged above |
| Frontend `vite build` | ✓ Production build clean (773 KB JS gzip 225 KB) |
| MCP smoke (by_soc, soc_code='15-1252', limit=3) | ✓ Returns ranked top-3 (UW Bothell, Stanford, Princeton) |
| MCP smoke (by_cip_and_soc, cipcode='51.38', soc_code='29-1141') | ✓ Returns 973 qualifying programs ranked |
| Anchor-below-top-N append behavior | ✓ Anchor row appended at index N with absolute rank=15 and `is_anchor=true` |
| `mode='by_cip_and_soc'` without cipcode → error | ✓ Both service-level (ValueError) and handler-level (`error` field) |

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ✗ tsc | `'cut' is possibly 'undefined'` in `CompareSchoolsPanel.tsx:41` (`shortenProgramName`); `Property 'ar' is missing` in `strings.ts` Record. | Added `?? name` fallback to the split result; added empty `ar: {}` block to `STRINGS`. |
| 2 | ✓ tsc | — | — |
| 3 | ✓ ruff/mypy/pytest/vitest/build | — | — |

### Post-Review Fix-up Pass (after design audit + code review)

After @fp-design-auditor returned 15 FAILs and @faang-staff-engineer returned 4 🟠 + 4 🟡 + 3 🔵 findings, the following fixes landed in a single pass:

**Backend (per code-review):**
- `src/mcp_server/futureproof_server.py:3450-3464` — replaced raw `str(exc)` in the SQL exception path with a `logger.exception(...)` + opaque `"leaderboard_query_failed"` code. Server-side log retains the full trace; client receives an opaque token. Per code-review Finding 2.
- `backend/app/routers/careers.py` — extracted shared `_dispatch()` helper that catches `pydantic.ValidationError` separately (502 with `"upstream_contract_violation"` detail), maps opaque upstream codes to 502, and falls through to 422 with the raw message for legitimate `ValueError` (validation messages). Forward-compatible against a future Pydantic v3 that may break the `ValidationError → ValueError` inheritance. Per code-review Finding 3.

**Frontend (per code-review + design audit):**
- `frontend/src/components/CompareSchoolsPanel.tsx` — full rewrite addressing:
  - Race condition: added `reqIdRef` generation counter; stale resolutions are dropped without setting state. Per code-review Finding 1.
  - Inline panel re-fetch: lifted `data` and `minConfidence` state from `<PanelBody>` into the parent `<CompareSchoolsPanel>` component; `<PanelBody>` is now a controlled view of parent state. The disclosure toggle no longer unmounts state. Added `fetchedKeyRef` so the fetch fires once per `(mode, soc, cip, anchor)` key, not every reveal. Per code-review Finding 4.
  - Focus management: ref'd close button + `closeBtnRef.current?.focus()` on sheet mount as the minimum-viable focus anchor for `aria-modal="true"`. Per code-review Finding 5.
  - Token fixes from the design audit:
    - F1: `bg-surface-elev1` / `bg-surface-elev2` → `bg-bp-mid` / `bg-bp-surface` (phantom tokens; the panel was rendering transparent).
    - F2: `shadow-xl` → `shadow-lg`.
    - F3: anchor row left edge changed from `border-l-2 border-accent-thrive` (non-rendering on `display: contents` element) to `style={{ boxShadow: "inset 3px 0 0 0 var(--color-accent-thrive)" }}`. This is the technique §3.C explicitly prescribed.
    - F4: ERN cell `text-text-primary` → `text-stat-ern` (gold-on-gold per §3.C).
    - F6/F7/F8: mode chip `font-mono text-[11px] rounded-sm` → `font-data text-micro rounded-full` (full token treatment per §3.B.B).
    - F9–F12: `text-sm`/`text-xs`/`text-base`/`text-lg`/`font-mono` → `text-small`/`text-micro`/`text-body`/`text-subheading`/`font-data` everywhere.
    - F13: backdrop `bg-black/60` → `bg-bp-void/55`.
    - F15: inline panel `rounded-lg` → `rounded-xl`.
- `frontend/src/lib/format.ts` — F5: `statRoiColorClass` thresholds `>= 8`/`>= 5` → `>= 7`/`>= 4`, matching §3.C. Also widened the null guard from `=== null` to `== null` (covers `undefined`) to address Finding 10.
- `frontend/src/screens/BuildResultsScreen.tsx` — F14: `style={{ marginTop: 32 }}` → `className="mt-8"`.

**Deferred to v1.1 (flagged in §10):**
- 🟡 #6 Scan-limit warning + DQ guard (logger.warning when `total_qualifying_programs >= SCHOOLS_FOR_CAREER_SCAN_LIMIT`) — won't fire today.
- 🟡 #7 Drop `limit` from cache key — memory-efficiency improvement, not a correctness issue.
- 🟡 #8 Anchor cipcode canonicalization helper — latent; PCP `cipcode` is `VARCHAR` today.
- 🔵 #9 Delete the no-op `pluralizeOccupation` function — cosmetic.
- 🔵 #11 ESC handler stack hygiene — not exercised by current usage.
- W1–W4 from design audit: sheet width, ESC subtitle copy, etc. — minor visual polish.

### Re-Verification Run (post-fix)

| Check | Result |
|-------|--------|
| Backend `ruff check src/ tests/` | ✓ Clean |
| Backend `mypy app/routers/careers.py app/services/schools_for_career.py` | ✓ Clean |
| Backend `pytest backend/tests/` | ✓ 1252 passed |
| Backend `pytest tests/` (root pipeline + MCP) | ✓ 1713 passed |
| MCP tests `test_get_schools_for_career.py` | ✓ 15 passed |
| Router tests `test_careers_router.py` | ✓ 6 passed |
| Service tests `test_schools_for_career_service.py` | ✓ 6 passed |
| Frontend `tsc --noEmit` | ✓ Clean |
| Frontend `vitest` (touched files) | ✓ 56 passed, 1 skipped |
| Frontend `vite build` | ✓ Clean (798 KB JS gzip 232 KB — slight uptick from 773 KB but well under attention threshold) |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `tests/mcp/test_get_schools_for_career.py` | `TestBySocReturnsTopN::test_by_soc_returns_top_n` | P0 — by_soc with limit=10 returns 10 ranked rows; rank-monotonic; top row matches highest composite; `total_qualifying_programs` counts the full post-filter universe (11 rows after default medium filter, 110012 'low' and 110013 NULL stat_ern dropped). |
| `tests/mcp/test_get_schools_for_career.py` | `TestByCipAndSoc::test_by_cip_and_soc_filters_to_anchor_program` | P0 — by_cip_and_soc with cipcode=51.38 + soc=29-1141 returns ONLY rows matching both; cross-CIP nursing rows (51.39) do not leak; `program_name` envelope populated. |
| `tests/mcp/test_get_schools_for_career.py` | `TestByCipAndSoc::test_by_cip_and_soc_requires_cipcode` | P0 — by_cip_and_soc without cipcode → structured `error` field, no exception. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAnchorHandling::test_anchor_appended_when_not_in_top_n` | P0 — anchor below top-N appended at index N with `is_anchor=true` and **absolute** rank (=7, not synthesized). Top-N rows untouched. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAnchorHandling::test_anchor_in_place_when_in_top_n` | P0 — anchor in top-N: exactly one `is_anchor=true` row, no duplicate appended; total rows still equals limit. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAnchorHandling::test_no_anchor_renders_clean` | P0 — no `build_unitid`/`build_cipcode` → no anchor rows, `anchor_in_top_n=false`, no error. |
| `tests/mcp/test_get_schools_for_career.py` | `TestConfidenceFilter::test_low_confidence_rows_excluded_by_default` | P0 — default `min_confidence='medium'` filters out `overall_confidence='low'` rows (110012 dropped); every returned row's `overall_confidence ∈ {high, medium}`. |
| `tests/mcp/test_get_schools_for_career.py` | `TestConfidenceFilter::test_returned_match_quality_values_are_storage_layer_only` | P0 — every row's `match_quality ∈ {full, partial_no_onet, partial_no_bls, scorecard_only}` (per data-reviewer item 4: locks the contract that runtime-stamped `broad_cip_*` substitution rows from `get_career_paths` cannot leak in). |
| `tests/mcp/test_get_schools_for_career.py` | `TestConfidenceFilter::test_partial_no_bls_dropped_by_implicit_stat_filter` | P0 — `partial_no_bls` row with medium overall_confidence and NULL `stat_ern` (110013) is dropped by the implicit `WHERE stat_ern IS NOT NULL` (per data-reviewer item 5). |
| `tests/mcp/test_get_schools_for_career.py` | `TestConfidenceFilter::test_empty_after_filter_with_drop_confidence_escape` | P0 — SOC where every row is `overall_confidence='low'` returns `rows=[]` and `total_qualifying_programs=0` under default; re-query with `min_confidence='low'` returns the rows. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAdditionalFilters::test_state_filter_applied` | P1 — `state_abbr='IN'` returns only IN rows; `state_filter_applied` echoed back. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAdditionalFilters::test_limit_param_clamped` | P1 — `limit=999` clamps to ≤25 rows. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAdditionalFilters::test_min_confidence_low_includes_all` | P1 — `min_confidence='low'` surfaces rows the default filter hides; row 110012 reappears. |
| `tests/mcp/test_get_schools_for_career.py` | `TestAdditionalFilters::test_min_program_confidence_optional_filter` | P1 — `min_program_confidence='medium'` drops rows with `confidence_tier_program ∈ {low, insufficient}` (110011 + 110012); independent of overall_confidence (per data-reviewer item 4). |
| `tests/mcp/test_get_schools_for_career.py` | `TestResponseFieldWhitelist::test_response_field_whitelist_no_pii_leak` | P2 — every returned row's keys ⊆ `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP`; `composite_score` and `abs_rank` are NOT on the wire (locks architect C3). |
| `backend/tests/routers/test_careers_router.py` | `TestBySocEndpointHappyPath::test_by_soc_endpoint_happy_path` | P0 — `GET /careers/15-1252/schools` with anchor query params returns 200 with the documented shape; service receives `mode='by_soc'`, the right limit, and an `AnchorBuild`. |
| `backend/tests/routers/test_careers_router.py` | `TestByCipAndSocEndpointHappyPath::test_by_cip_and_soc_endpoint_happy_path` | P0 — `GET /majors/51.38/schools/for-career/29-1141` returns 200 with `mode='by_cip_and_soc'`; partial anchor (build_unitid only) normalized to `None` at the service boundary. |
| `backend/tests/routers/test_careers_router.py` | `TestInvalidCipcodeFormat::test_invalid_cipcode_format_rejected` | P0 — `cipcode='11'` in path → 422 from FastAPI's `Path(..., pattern=...)` regex; the service is never called. |
| `backend/tests/routers/test_careers_router.py` | `TestInvalidCipcodeFormat::test_short_cipcode_three_digits_rejected` | P0 supplement — `cipcode='11.0'` (one digit after dot) is also rejected by the same regex. |
| `backend/tests/routers/test_careers_router.py` | `TestUnknownSocEmpty::test_unknown_soc_returns_empty` | P0 — unknown SOC `99-9999` returns 200 with `rows=[]` and `total_qualifying_programs=0`. |
| `backend/tests/routers/test_careers_router.py` | `TestAnchorPartiallyProvided::test_anchor_only_partially_provided` | P1 — `build_unitid` alone (or `build_cipcode` alone) returns 200 with anchor=None at the service boundary; no 422. |
| `backend/tests/services/test_schools_for_career_service.py` | `TestCompositeScoreDispatch::test_composite_score_formula_via_mcp_dispatch` | P0 — service calls `mcp_client.call("get_schools_for_career", ...)` with every knob passed verbatim and parses the raw response into `SchoolsForCareerResponse`. |
| `backend/tests/services/test_schools_for_career_service.py` | `TestCompositeScoreDispatch::test_error_field_raises_value_error` | P0 supplement — an MCP-side `error` field surfaces as `ValueError` so the router can convert to 422. |
| `backend/tests/services/test_schools_for_career_service.py` | `TestModeDispatchesCorrectArgs::test_mode_dispatches_correct_args` | P0 — by_soc dispatches with no `cipcode` key in args; by_cip_and_soc dispatches with `cipcode` populated; other knobs identical. |
| `backend/tests/services/test_schools_for_career_service.py` | `TestModeDispatchesCorrectArgs::test_by_cip_and_soc_without_cipcode_raises` | P0 supplement — service rejects `mode='by_cip_and_soc'` with no `cipcode` BEFORE dispatch (no MCP round trip). |
| `backend/tests/services/test_schools_for_career_service.py` | `TestServiceDoesNotOpenDuckDB::test_service_module_does_not_import_duckdb` | P0 — module source contains no `import duckdb` / `from duckdb` substring (locks architect C1). |
| `backend/tests/services/test_schools_for_career_service.py` | `TestServiceDoesNotOpenDuckDB::test_service_does_not_call_mcp_get_server` | P0 — patching `mcp_client.get_server` to raise does NOT crash the service; round-trip stays through `mcp_client.call` only. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_correct_title_chip_per_mode (by_soc)` | P0 — `by_soc` enclosure="sheet": title contains occupation_title; `chip-leaderboard-mode` reads "BY CAREER". |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_correct_title_chip_per_mode (by_cip_and_soc)` | P0 — `by_cip_and_soc` enclosure="inline": title contains BOTH program_name and occupation_title; chip reads "BY MAJOR + CAREER". |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_anchor_row_when_anchor_present (in-place)` | P0 — when a row has `is_anchor=true` and `anchor_in_top_n=true`, it carries `data-testid="row-anchor-{unitid}-{cipcode}"` and `data-anchor="true"`; exactly one such row. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_appended_anchor_row_when_below_top_n (with divider)` | P0 — appended anchor row renders with absolute rank (=7); "Your school" divider is rendered above it. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_clean_when_no_anchor` | P0 — when no row has `is_anchor=true`, no anchor styling is applied, no "Your school" divider, no fallback notice. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `renders_empty_state_with_drop_confidence_escape` | P0 — empty response renders empty state with "Show all programs" button; clicking it triggers a re-fetch with `minConfidence='low'`. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `does_not_render_pentagon_charts` | P0 — the panel subtree contains zero `data-testid` matching `/pentagon/i` AND zero `<polygon>` elements (locks Decision #2). |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `formats_money_via_existing_helper` | P1 — earnings + net price render with the same `$X,XXX` format produced by `fmtMoney` from `@/lib/format`. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `formats_null_money_as_em_dash_via_helper` | P1 supplement — null money renders as the em-dash glyph from `fmtMoney(null)`. |
| `frontend/src/components/CompareSchoolsPanel.test.tsx` | `narrow_viewport_collapses_columns` (skipped) | P2 — the §3.D mobile card-stack at <640px hiding the confidence column is documented in the design but NOT yet wired in v1; skipped with explanatory docstring rather than fabricated. v1.1 follow-up. |

### Edge Cases Covered

- [x] Anchor below top-N (appended) AND anchor in top-N (in-place) — both paths.
- [x] Anchor absent (no build) — clean render, no warning, no anchor styling.
- [x] Anchor partially provided (unitid only or cipcode only) — service-side normalize to None, no 422.
- [x] Empty-after-confidence-filter escape hatch — `min_confidence='low'` re-query.
- [x] `partial_no_bls` row with NULL `stat_ern` → dropped by implicit WHERE.
- [x] `confidence_tier_program ∈ {low, insufficient}` → dropped by `min_program_confidence='medium'`.
- [x] State filter applied (`state_abbr`).
- [x] Limit clamped at 25 (`limit=999` → ≤25).
- [x] Cross-CIP rows in same SOC do NOT leak through `by_cip_and_soc`.
- [x] `composite_score` / `abs_rank` are computed but never on the wire (locks architect C3).
- [x] FastAPI Path regex rejects malformed cipcodes (`'11'`, `'11.0'`).
- [x] Service does not import `duckdb` and does not call `mcp_client.get_server` (locks architect C1).
- [x] Mode chip is durable per mode and carries the correct text.
- [x] `<PentagonChart>` and `<polygon>` are NEVER rendered on this surface (locks Decision #2).
- [x] `fmtMoney` reuse — money formatting is consistent with `CareerDetail`.

### Test Results

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (root, MCP only — full `tests/mcp/`) | 266 | 0 | 0 | 266 |
| pytest (root, new file `tests/mcp/test_get_schools_for_career.py`) | 15 | 0 | 0 | 15 |
| pytest (backend, full suite) | 1252 | 0 | 0 | 1252 |
| pytest (backend, new files: `test_careers_router.py` + `test_schools_for_career_service.py`) | 12 | 0 | 0 | 12 |
| vitest (touched + sentinel: `CompareSchoolsPanel` + `CareerDetail` + `BuildResultsScreen` + `RevealScreen`) | 56 | 0 | 1 | 57 |
| vitest (new file `CompareSchoolsPanel.test.tsx` only) | 9 | 0 | 1 | 10 |

### Existing Tests Status (from §4 "Existing Tests at Risk")

- [x] `tests/mcp/test_get_career_paths.py` — full suite passes (verified in 266-test root MCP run).
- [x] `tests/mcp/test_cip_substitution.py` — full suite passes (verified in 266-test root MCP run).
- [x] `frontend/src/components/CareerDetail.test.tsx` "ROI receipt" suite — all tests pass alongside the new `CompareSchoolsPanel.test.tsx` (verified in the touched + sentinel run).
- [x] `frontend/src/screens/BuildResultsScreen.test.tsx` — passes.
- [x] `frontend/src/screens/RevealScreen.test.tsx` — passes.

### Gaps Identified

1. **Narrow-viewport responsive collapse (P2).** §3.D specifies a card-stack at <640px that hides the confidence column. The current `CompareSchoolsPanel` renders a fixed 7-column CSS grid regardless of viewport width. Test added as `describe.skip(...)` with a docstring flagging the gap. v1.1 follow-up: wire a CSS media query or container-query and unskip the test.
2. **Live-Iceberg integration test for the new MCP tool.** All MCP-level tests run against an in-memory DuckDB shim (matching `_handle_get_career_paths` test isolation pattern). A live-Iceberg smoke is part of the genai-architect §10 verification (see §6 Verification Run rows for "MCP smoke" cases). Documented; not duplicated at the unit-test layer.
3. **Cache key correctness under concurrent engine reloads.** The architect called out cache invalidation across engine reloads (§5 C5). Not tested here; tests only validate the cache-disabled path. Adding a cache-on test requires importing `_schools_for_career_cache` and toggling `FUTUREPROOF_OUTCOMES_CACHE=1` — straightforward but out of P0/P1 scope. Flag for follow-up if cache becomes load-bearing.

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** CHANGES REQUIRED
**Auditor:** @fp-design-auditor — 2026-04-29
**DESIGN.md read:** Yes (full). All token names, semantic roles, and usage
rules referenced below are sourced from DESIGN.md §Color Tokens, §Typography,
§Spacing, §Elevation & Shadows, §Motion System.

---

## `frontend/src/components/CompareSchoolsPanel.tsx`

### PASS
- All user-visible strings flow through `useT()` and the `compareSchools.*`
  keys in `strings.ts`. No raw English literals found in the component body.
  i18n checklist item is clean.
- `PentagonChart` is not imported and no `pentagon-*` SVG is rendered. The
  `does_not_render_pentagon_charts` contract is respected at source level.
- `fmtMoney` is imported from `@/lib/format` (line 8) and used exclusively
  for all monetary cells (lines 448, 453). No inline `$${value.toLocaleString()}`
  pattern exists in this file. Money-formatting checklist item is clean.
- Mode chip lives inside `PanelHeader`, which renders a `sticky top-0` div
  (line 323). The chip is rendered in both modes via the `chipColor` and
  `chipText` conditional on `mode === "by_soc"` (lines 302–308). Chip is
  durable across both enclosure types because `PanelHeader` is always the
  first child of `PanelBody`, which is always rendered inside both
  `SheetEnclosure` and `InlineEnclosure`.
- `border-border-subtle` is used consistently for row separators and header
  bar bottom edges (lines 167, 323, 479). Correct token.
- `text-text-primary`, `text-text-secondary`, `text-text-muted` are used
  throughout for text hierarchy. No `text-gray-*` or `text-white/*` found.
- `bg-accent-thrive/10` and `border-accent-thrive` are used for the anchor
  row background tint and left-edge accent (line 408). Token usage is correct.
- `bg-accent-caution/10` and `border-b border-accent-caution/30` are used for
  the confidence-fallback notice bar (line 263). Both tokens are present, which
  satisfies the spec's requirement that the notice includes both the background
  tint AND the border.
- `text-accent-insight`, `text-accent-info` used for mode chip color tokens
  (lines 306–308). Correct semantic mapping per DESIGN.md and §3.B.B.

### FAIL

**F1 — `bg-surface-elev1` and `bg-surface-elev2` are phantom tokens.**
Used at lines 121, 167, 323, 494. Neither token exists in
`tailwind.config.ts` (confirmed) nor in any CSS file in the project
(`tokens.css`, `index.css`, `horizonMap.css` all checked — zero matches).
DESIGN.md defines the background token family as `bg-bp-void`, `bg-bp-deep`,
`bg-bp-mid`, `bg-bp-surface`, `bg-bp-raised` (DESIGN.md §Color Tokens /
Backgrounds). The intended mapping is most likely:
- `bg-surface-elev1` → `bg-bp-mid` (#232545) — the card/elevated surface
  token (matches §3.B spec text: `background: bg-bp-mid`)
- `bg-surface-elev2` → `bg-bp-surface` (#2D3060) — the interactive/hover
  surface token

Because these classes are not registered, Tailwind emits no CSS for them.
The sheet and inline panel currently have **no background color applied**,
which means the panel renders transparent over the page backdrop. This is a
rendering bug, not just a token-naming issue.

Every call site must be replaced with the canonical `bg-bp-mid` /
`bg-bp-surface` equivalents before ship.
- Line 121 (`SheetEnclosure` aside) → `bg-bp-mid`
- Line 167 (`InlineEnclosure` section) → `bg-bp-mid`
- Line 323 (`PanelHeader` sticky bar) → `bg-bp-mid`
- Line 494 (`LoadingSkeleton` shimmer rows) → `bg-bp-surface`

**F2 — `shadow-xl` is not a Brightpath token.**
Line 121: `shadow-xl` is a native Tailwind shadow, not one of the Brightpath
elevation tokens defined in DESIGN.md §Elevation & Shadows. The canonical
token for modals/sheets is `shadow-lg` (`var(--shadow-lg)`,
`0 8px 32px rgba(27, 29, 48, 0.7)`). The spec §3.B also calls for
`shadow: shadow-lg` on the sheet. Replace `shadow-xl` → `shadow-lg` at
line 121.

**F3 — Anchor row left-border is 2px, spec requires 3px.**
Line 408: `border-l-2 border-accent-thrive`. DESIGN.md defines no named
`border-l-*` token, so this would normally be a warning — but §3.C of this
spec explicitly states the left-edge inset should be 3px:
> "3px solid accent-thrive on the left edge (use `box-shadow: inset 3px 0 0 0
> var(--color-accent-thrive)` so the row doesn't shift width)"

The implementation uses `border-l-2` (8px Tailwind spacing = 2px? — actually
`border-l-2` = `border-left-width: 2px` in Tailwind's border-width scale, not
spacing) AND it uses a real left border rather than the specified `box-shadow:
inset` technique. Using an actual left border on a CSS Grid `contents` element
has no visual effect because `contents` removes the box. The border will not
render. The spec's `box-shadow: inset` technique is required precisely because
`display: contents` cannot carry a border. This is a rendering bug.

**F4 — ERN cell uses `text-text-primary` instead of `text-stat-ern`.**
Lines 437–439: the ERN digit is rendered as `font-mono text-text-primary`.
DESIGN.md §Stat Colors defines `text-stat-ern` as the canonical token for
ERN values ("Gold. Money."). §3.C confirms: "ERN: `text-stat-ern` always."
`text-text-primary` (warm white) produces no stat-axis visual distinction.
Replace with `text-stat-ern`.

**F5 — `statRoiColorClass` thresholds diverge from spec §3.C.**
`format.ts` lines 16–18 implement:
```ts
if (roi >= 8) return "text-accent-thrive";
if (roi >= 5) return "text-accent-caution";
```
The spec §3.C defines:
```ts
if (roi >= 7) return "text-accent-thrive";
if (roi >= 4) return "text-accent-caution";
```
This shifts both thresholds up by 1. A `stat_roi` of 7 (a good score) will
display in caution yellow instead of thrive green. A `stat_roi` of 4 (a
marginal score) will display in alert red instead of caution yellow. Both
are mis-colorings against the documented semantic. Fix thresholds in
`format.ts` to match §3.C.

**F6 — Mode chip font-family uses `font-mono` instead of `font-data`.**
Line 327: `font-mono uppercase`. DESIGN.md defines the design system's
monospace token as `font-data` (Space Mono). `font-mono` is a generic Tailwind
fallback stack that may resolve to the system monospace font (Courier, Menlo,
etc.) rather than Space Mono. §3.B.B specifies `font-family: font-data (Space
Mono)` for the chip. Replace `font-mono` → `font-data` on line 327.

**F7 — Mode chip font size uses arbitrary `text-[11px]` instead of `text-micro`.**
Line 327: `text-[11px]`. DESIGN.md defines `text-micro` as 12px / 0.75rem
(DESIGN.md §Typography / Type Scale). §3.B.B specifies `font-size: text-micro
(12px)` for the chip. The arbitrary `text-[11px]` bypasses the token. Replace
with `text-micro`.

**F8 — Mode chip border-radius uses `rounded-sm` instead of `rounded-full`.**
Line 327: `rounded-sm` (6px). §3.B.B specifies `border-radius: radius-full`.
DESIGN.md maps `rounded-full` → 9999px. The chip should be a pill, not a
badge with a slight corner radius. Replace `rounded-sm` → `rounded-full`.

**F9 — InlineEnclosure header uses raw `text-sm` and `text-base` instead of
Brightpath type scale tokens.**
Lines 176, 179: `text-sm` (Tailwind default 14px) and `text-base` (Tailwind
default 16px). These are not Brightpath tokens. The correct equivalents per
DESIGN.md §Typography are `text-small` (14px) and `text-body` (16px).
Although the pixel values match, using `text-sm`/`text-base` bypasses the
token system and will silently drift if the type scale changes. Replace with
`text-small` and `text-body` respectively.

**F10 — PanelHeader title uses `text-lg` and `text-sm` instead of Brightpath
type scale tokens.**
Lines 331, 334: `text-lg` (Tailwind default 18px) and `text-sm` (14px). The
panel title should be `text-subheading` (22px, DESIGN.md) per §3.B.B
(`font-size: text-heading`). The subtitle should be `text-body` (16px) or
`text-small` (14px). The spec calls for `text-heading` for the title. Using
`text-lg` produces 18px rather than the documented 22px or 28px. Replace
with Brightpath type scale tokens.

**F11 — `PanelTable` uses `text-sm` and `text-xs` instead of Brightpath type
scale tokens.**
- Line 351: `text-sm` on the grid container — propagates to all cells.
- Line 382: `text-xs` for the "Ranked among N" footer — should be
  `text-small` (14px) or `text-micro` (12px). DESIGN.md §3.C specifies
  `text-small` for this line.
- Line 427: `text-xs` for the program secondary line — should be `text-small`.
- Line 470: `text-xs` in the `Cell` component header variant — should be
  `text-micro`.
- Line 478 (`YourSchoolDivider`): `text-xs` — should be `text-micro`.

All of these raw Tailwind size utilities should use Brightpath type scale
tokens.

**F12 — `DataRow` cells use `font-mono` instead of `font-data`.**
Lines 420, 432, 437, 442, 447, 452: all data cells use `font-mono`. As in F6,
`font-mono` is a generic system fallback. DESIGN.md §Typography / Font
Families defines `font-data` (Space Mono) as the data/monospace token. The
spec §3.C specifies `font-data` for all numeric cells. Replace all occurrences
with `font-data`.

**F13 — Backdrop uses `bg-black/60` instead of a documented token.**
Line 108: `bg-black/60`. §3.B specifies the backdrop as
`rgba(18, 19, 31, 0.55)` — that is `bg-bp-void` at 55% opacity, not
black. `#000000` at 60% and `#12131F` at 55% produce different visual results:
pure black reads as theater-dark; `bg-bp-void` reads as night-sky indigo
behind the bear. The difference is visible, especially at the edges. Use
`bg-bp-void/55` (or a Tailwind arbitrary value `bg-[rgba(18,19,31,0.55)]`
if the `/55` opacity modifier isn't supported for this token) rather than
`bg-black/60`.

**F14 — `BuildResultsScreen.tsx` wrapper uses `style={{ marginTop: 32 }}`
instead of a Tailwind spacing token.**
Line 607–608: `style={{ marginTop: 32 }}`. DESIGN.md §Spacing defines
`space-8` = 32px = `mt-8`. The rest of the codebase uses Tailwind spacing
utilities; this inline style is inconsistent. Replace with `className="mt-8"`.

**F15 — Inline `InlineEnclosure` uses `rounded-lg` but spec calls for
`radius-xl`.**
Line 167: `rounded-lg` (14px). §3.B specifies
`border-radius: radius-xl` for the inline panel. DESIGN.md defines
`rounded-xl` = 20px. Replace `rounded-lg` → `rounded-xl`.

### WARNINGS

**W1 — Sheet width is `sm:w-[640px]` instead of spec's `min(880px, calc(100vw - 64px))`.**
Line 121. The spec §3.B specifies `min(880px, calc(100vw - 64px))` for the
sheet width. The implementation caps at 640px. This is narrower than the
specified 880px which was chosen because "even after column collapse it wants
≥720px to breathe at desktop." This is a sizing decision, not a token
violation per se, so it is flagged as a warning rather than a FAIL — the
design visionary may need to weigh in on whether 640px is acceptable for
the column layout.

**W2 — Motion transitions inline rather than using `springs` presets.**
Line 125: `transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}`.
DESIGN.md §Motion System specifies sheet entrance as `springs.smooth`
(`{ stiffness: 200, damping: 25 }`). The implementation uses a raw
`cubic-bezier` ease on a duration-based transition rather than a Framer
Motion spring. The feel may differ from the documented system preset. This
is a warning rather than a hard fail because the visual result may be
acceptable, but the canonical import is `import { springs } from
"@/styles/motion"`.

**W3 — `EmptyState` button uses `bg-accent-info/15` treatment instead of
the documented secondary button variant.**
Line 527: `px-4 py-2 rounded bg-accent-info/15 text-accent-info
hover:bg-accent-info/25`. §3.C.1 (Empty state) specifies using the Brightpath
`secondary` button variant (`<Button variant="secondary">`). The inline
class composition is not the registered button component and does not include
the `44px` height, `0 24px` padding, or press scale feedback documented in
DESIGN.md §Components / Buttons.

**W4 — `CareerDetail.tsx` still contains three inline `toLocaleString()`
calls on salary range values (lines 216, 219, 222) rather than using
`fmtMoney`.**
The salary range block uses `${(career.earnings_1yr_p25 ?? 0).toLocaleString()}`
etc. directly. While `fmtMoney` is properly used elsewhere in the file, these
three call sites predate the extraction and were not migrated. The null-
handling behavior differs (`fmtMoney` returns `"—"` on null; the inline calls
coerce to `0`). Not a token violation but an inconsistency in the extracted
helper's adoption.

---

## `frontend/src/lib/format.ts`

### PASS
- `fmtMoney` is cleanly extracted and uses only token-agnostic formatting
  logic (no color, no class names). Safe to import from any component.
- `roiColorClass` uses `text-accent-thrive`, `text-accent-caution`,
  `text-accent-alert` — all documented Brightpath tokens with correct
  semantic mapping.
- `statRoiColorClass` uses the same three token names — correct token choice.

### FAIL
- **F5 (duplicate):** See F5 above — threshold values diverge from spec §3.C.

---

## `frontend/src/i18n/strings.ts`

### PASS
- 32 `compareSchools.*` keys present in `en`, `es`, and `ar` locales (spot-
  checked all three). Every key referenced in `CompareSchoolsPanel.tsx` and
  `CareerDetail.tsx` is defined.
- No raw English user-visible strings found in the panel component.

---

## Summary of Violations

| ID | File | Line(s) | Severity | Issue |
|----|------|---------|----------|-------|
| F1 | CompareSchoolsPanel.tsx | 121, 167, 323, 494 | BLOCKER | `bg-surface-elev1`/`bg-surface-elev2` are phantom tokens — panel has no background |
| F2 | CompareSchoolsPanel.tsx | 121 | FAIL | `shadow-xl` → must be `shadow-lg` |
| F3 | CompareSchoolsPanel.tsx | 408 | FAIL | Anchor left-border is `border-l-2` (wrong width, wrong technique for `contents` element) |
| F4 | CompareSchoolsPanel.tsx | 437 | FAIL | ERN cell uses `text-text-primary` instead of `text-stat-ern` |
| F5 | format.ts | 16–18 | FAIL | `statRoiColorClass` thresholds off-by-1 vs spec §3.C |
| F6 | CompareSchoolsPanel.tsx | 327 | FAIL | Mode chip uses `font-mono` instead of `font-data` |
| F7 | CompareSchoolsPanel.tsx | 327 | FAIL | Mode chip uses `text-[11px]` instead of `text-micro` |
| F8 | CompareSchoolsPanel.tsx | 327 | FAIL | Mode chip uses `rounded-sm` instead of `rounded-full` |
| F9 | CompareSchoolsPanel.tsx | 176, 179 | FAIL | InlineEnclosure header uses `text-sm`/`text-base` instead of `text-small`/`text-body` |
| F10 | CompareSchoolsPanel.tsx | 331, 334 | FAIL | PanelHeader title uses `text-lg`/`text-sm` instead of Brightpath type scale tokens |
| F11 | CompareSchoolsPanel.tsx | 351, 382, 427, 470, 478 | FAIL | Multiple `text-sm`/`text-xs` usages instead of Brightpath type scale tokens |
| F12 | CompareSchoolsPanel.tsx | 420, 432, 437, 442, 447, 452 | FAIL | Data cells use `font-mono` instead of `font-data` |
| F13 | CompareSchoolsPanel.tsx | 108 | FAIL | Backdrop uses `bg-black/60` instead of `bg-bp-void/55` |
| F14 | BuildResultsScreen.tsx | 607–608 | FAIL | `style={{ marginTop: 32 }}` instead of `mt-8` |
| F15 | CompareSchoolsPanel.tsx | 167 | FAIL | `rounded-lg` instead of `rounded-xl` for inline panel |
| W1 | CompareSchoolsPanel.tsx | 121 | WARNING | Sheet width 640px vs spec 880px |
| W2 | CompareSchoolsPanel.tsx | 125 | WARNING | Raw cubic-bezier instead of `springs.smooth` |
| W3 | CompareSchoolsPanel.tsx | 527 | WARNING | Escape-hatch button not using `<Button variant="secondary">` |
| W4 | CareerDetail.tsx | 216, 219, 222 | WARNING | Salary range cells use inline `toLocaleString()` instead of `fmtMoney` |

**Verdict: ✗ CHANGES REQUIRED**

F1 is a rendering bug (transparent panel). F3 is a rendering bug (border on
`contents` element). F4 and F5 together mean the two stat columns are
mis-colored on every row. F6–F12 represent systematic token drift where the
raw Tailwind utility layer is used throughout instead of the Brightpath design
token layer. These must be fixed before the component ships — the token system
exists precisely so that type scale, font family, and shadow depth are
centrally controlled; using the raw Tailwind utilities underneath the token
layer defeats that guarantee.

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)
**Date:** 2026-04-29

#### Summary

Competent, defensive code. The architect's seven C-conditions all hold up
under inspection: mode dispatch is a single SQL `WHERE` builder, the windowed
`RANK() OVER` is correct with `NULLS LAST` on both tiebreak fields, the cache
is properly registered for engine-reload sweeps, `composite_score` is computed
in SQL but never escapes the response whitelist, and the service module is
provably free of DuckDB. Pydantic v2 boundary catches malformed responses.

That said — there are four genuine issues worth addressing before merge, and
a handful of moderate footguns I've called out. None are 3am-page-grade. One
is a real frontend race, one is an information-disclosure smell, one is a
`ValidationError` that escapes to a 500, and one is a UX/perf waste pattern
that compounds on cache miss. Ship after addressing the 🟠 items; the 🟡
items can follow up.

---

#### Findings

##### 🔴 Critical Findings
None. The four areas the spec called out for special attention all check
out:

1. **Mode dispatch is SQL-only.** `_handle_get_schools_for_career` at
   `src/mcp_server/futureproof_server.py:3387-3411` builds a single
   `where_parts` list with one conditional append for the cipcode predicate
   (line 3393: `if cipcode is not None and mode == "by_cip_and_soc":`). No
   forked code path downstream — top-N selection, anchor handling, and
   serialization are mode-agnostic. ✓
2. **Windowed RANK() NULL handling.** `src/mcp_server/futureproof_server.py:3436-3442`
   produces `ORDER BY composite DESC, earnings_1yr_median DESC NULLS LAST,
   net_price_annual ASC NULLS LAST`. Composite is never NULL because the
   implicit `WHERE stat_ern IS NOT NULL AND stat_roi IS NOT NULL` at lines
   3389-3390 enforces both. ✓
3. **Cache registered in `_cache_drop_engine`.**
   `src/mcp_server/futureproof_server.py:591` lists
   `_schools_for_career_cache` in the engine-sweep tuple. `build_unitid` and
   `build_cipcode` are NOT in the cache key (lines 3361-3370) — anchor
   handling operates on a per-call copy of the cached materialized list per
   architect C5. ✓
4. **`composite_score` whitelist.** `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP`
   at `src/mcp_server/futureproof_server.py:238-259` does not include
   `composite_score` or `abs_rank`. Handler trims via the whitelist at line
   3521 (`{k: row.get(k) for k in SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP}`).
   Pydantic `SchoolForCareerRow` at `backend/app/models/career.py:379-402`
   has no field for them — a stray server-side leak would also be filtered
   by Pydantic. Belt and suspenders. ✓

##### 🟠 Serious Findings

###### Finding 1: Frontend race condition between rapid filter toggles
**Impact:** Stale response can clobber a newer one. User clicks "Show all
programs" (fires request A with `min_confidence='low'`), immediately clicks
"Restore default filter →" (fires request B with `min_confidence='medium'`).
If A's network call is slower than B's (jitter, reordered TCP, slow
substituted-rows path on the SOC), A arrives last and the panel renders
the `low`-filter rows while the chip claims `medium`. The fallback notice
also shows the wrong state.

**Location:** `frontend/src/components/CompareSchoolsPanel.tsx:209-234,
242-250`

```tsx
const load = useCallback(
  async (confidence: ConfidenceTier) => {
    setData({ status: "loading", response: null, error: null });
    try {
      ...
      const response = mode === "by_cip_and_soc" && cipcode
        ? await fetchSchoolsByCipAndSoc(cipcode, socCode, opts)
        : await fetchSchoolsBySoc(socCode, opts);
      // ← no check that this fetch is still the latest one
      if (response.rows.length === 0) {
        setData({ status: "empty", response, error: null });
      } else {
        setData({ status: "ok", response, error: null });
      }
    } ...
  },
  [mode, socCode, cipcode, anchor?.unitid, anchor?.cipcode],
);
```

**The Problem:** `apiGet` (`frontend/src/api/client.ts:48`) does not accept
an `AbortSignal`, and there is no in-flight request token / generation
counter. Setting state on an unmounted component will also warn under
React 18 strict mode when the user closes the sheet mid-fetch.

**The Fix:** Track an in-flight generation per call, ignore stale
resolutions:

```tsx
const reqIdRef = useRef(0);

const load = useCallback(
  async (confidence: ConfidenceTier) => {
    const myId = ++reqIdRef.current;
    setData({ status: "loading", response: null, error: null });
    try {
      const response = mode === "by_cip_and_soc" && cipcode
        ? await fetchSchoolsByCipAndSoc(cipcode, socCode, opts)
        : await fetchSchoolsBySoc(socCode, opts);
      if (myId !== reqIdRef.current) return; // stale
      ...
    } catch (err) {
      if (myId !== reqIdRef.current) return;
      ...
    }
  },
  [mode, socCode, cipcode, anchor?.unitid, anchor?.cipcode],
);

useEffect(() => () => { reqIdRef.current++; }, []); // invalidate on unmount
```

Or — better — extend `apiGet` to accept `AbortSignal` and wire it. That's
out of this spec's scope, so the generation-counter fix is the right v1
patch.

**Severity:** 🟠 Serious. Visible to users; corrupts the displayed state
without throwing.

---

###### Finding 2: Handler returns raw `str(exc)` to the client on SQL failure
**Impact:** A DuckDB error string can leak internal schema details, table
names, or stack-frame fragments to any client of the HTTP endpoint or chat
caller. Today's input validation makes this hard to trigger maliciously,
but "hard to trigger" is not "cannot be triggered" — a stale Iceberg
metadata read or a transient lock contention will surface the same error
path with no adversarial input at all.

**Location:** `src/mcp_server/futureproof_server.py:3450-3455`

```python
try:
    rows = engine.query_sql(sql, params)
except Exception as exc:  # noqa: BLE001
    return {
        "error": f"Cannot query consumable.program_career_paths: {exc}",
    }
```

That `error` string flows through `mcp_client.call` → service raises
`ValueError(str(raw.get("error")))` → router converts to
`HTTPException(detail=str(exc))` → client gets the raw DuckDB error.

**The Problem:** This violates the "Error messages that help attackers"
guideline. A crafted query could expose:
- Iceberg view names (`consumable_program_career_paths`)
- Column names not in the public response shape
- DuckDB version / build details

It also degrades the error UX — the frontend's `ErrorState` component
(`CompareSchoolsPanel.tsx:535-558`) renders the message verbatim. A user
sees `Cannot query consumable.program_career_paths: Catalog Error: Table
"consumable_program_career_paths" does not exist!` instead of "Couldn't
load peer schools right now."

**The Fix:**
```python
try:
    rows = engine.query_sql(sql, params)
except Exception as exc:  # noqa: BLE001
    logger.exception(
        "get_schools_for_career SQL failed",
        extra={"mode": mode, "soc_code": soc_code, "cipcode": cipcode or ""},
    )
    return {"error": "leaderboard_query_failed"}
```

Frontend then maps the opaque code to a user-friendly string. Server-side
log retains the full trace for debugging.

**Severity:** 🟠 Serious (security + UX). Standard practice; should not
ship to a public-facing endpoint without it.

---

###### Finding 3: Pydantic `ValidationError` from a malformed MCP response is fragile under future Pydantic upgrades
**Impact:** The router only catches `ValueError`
(`backend/app/routers/careers.py:46-57, 76-88`). If the MCP handler ever
returns a dict that's missing a required field or has a wrong type
(regression in the handler, contract drift, etc.), `model_validate` raises
`pydantic.ValidationError`. In Pydantic v2.x today, `ValidationError`
inherits from `ValueError`, so this works. But the contract is fragile —
the project pins Pydantic v2 with no upper bound, and future v3 has been
discussed in Pydantic's roadmap to break this inheritance. Any such
upgrade silently flips the routing from 422 → 500 with zero local code
change.

**Location:** `backend/app/services/schools_for_career.py:56-59` and
`backend/app/routers/careers.py:46-57, 76-88`

```python
# service
raw = mcp_client.call("get_schools_for_career", args)
if "error" in raw:
    raise ValueError(str(raw.get("error")))
return SchoolsForCareerResponse.model_validate(raw)  # may raise ValidationError
```

```python
# router
try:
    return rank_schools_for_career(...)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
# ValidationError → 500 if v3 ever breaks the inheritance
```

**The Fix:** Catch both explicitly and don't echo the v2 ValidationError
content (it includes field paths and partial values) back to the client:

```python
from pydantic import ValidationError as _PydanticValidationError
...
except _PydanticValidationError as exc:
    logger.exception("schools_for_career response failed validation")
    raise HTTPException(status_code=502, detail="upstream_contract_violation") from exc
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```

**Severity:** 🟠 Serious. Latent — works today on Pydantic 2.x but a
future upgrade can flip the inheritance and start surfacing 500s on
contract drift.

---

###### Finding 4: Inline panel re-fetches every disclosure toggle
**Impact:** Each click on the inline panel disclosure triangle (▸/▾)
**unmounts and remounts** `<PanelBody>` — see
`CompareSchoolsPanel.tsx:84` (`{showBody ? <PanelBody {...props} active={true} /> : null}`).
The mount fires the `useEffect` at line 236-240 which calls `load("medium")`.
Result: every collapse-then-expand cycle hits the API again. With
`FUTUREPROOF_OUTCOMES_CACHE=0` (default in dev / tests), this re-runs the
full windowed CTE on the backend. With cache=1, it's an HTTP round-trip +
cache lookup, but still wasteful.

The same applies to the sheet enclosure: open → fetch, close → unmount,
open again → fetch again.

**Location:** `frontend/src/components/CompareSchoolsPanel.tsx:60-86,
236-240`

```tsx
{showBody ? <PanelBody {...props} active={true} /> : null}
...
useEffect(() => {
  if (!active) return;
  setMinConfidence("medium");
  load("medium");
}, [active, load]);
```

Note that `active` is hardcoded `true` — the gate is on whether
`<PanelBody>` is rendered at all, which is the unmount/remount cycle. The
`active` plumbing was clearly intended to support a cached body that
could be hidden visually instead of unmounted; the current implementation
doesn't take advantage of it.

**The Fix:** Either:
- Render `<PanelBody>` always and gate visibility with the `hidden`
  attribute or `display: none`, lifting state up so it survives;
- Lift the data state up into `CompareSchoolsPanel` so it survives the
  body's unmount; OR
- Memoize via SWR / TanStack Query (overkill for v1).

For v1, hoist the `data` and `minConfidence` state into the parent
`CompareSchoolsPanel` and pass via props. One-time fetch on first reveal,
preserved across toggles.

**Severity:** 🟠 Serious for a comparison surface a user will toggle
repeatedly. Not a correctness bug — the right answer always renders — but
real bandwidth + flicker waste, and visible to users on slow networks.

##### 🟡 Moderate Findings

###### Finding 5: SheetEnclosure has no focus trap
**Impact:** Keyboard users can `Tab` out of the dialog and reach buttons
behind the backdrop, breaking the modal contract implied by
`aria-modal="true"`.

**Location:** `frontend/src/components/CompareSchoolsPanel.tsx:89-139`

The dialog has ESC handling (line 97-103, good) and a backdrop click
closer (line 113, good), but no focus trap. `aria-modal="true"` (line
118) tells assistive tech the focus is trapped — but it isn't.

**The Problem:** Either fulfill the `aria-modal` contract (focus trap) or
remove the attribute. The minimum-viable fix is to focus the close button
on open and trap Tab/Shift-Tab cycles within the dialog.

**The Fix:** Add a small `useFocusTrap` hook. Or — pragmatic v1 — at least
move focus to the close button on mount so screen readers anchor inside
the dialog.

**Severity:** 🟡 Moderate. Accessibility gap. Not a 3am page but a real
screen-reader bug.

---

###### Finding 6: Anchor cipcode comparison via `str()` cast assumes string column
**Impact:** Lines 3477, 3489 in
`src/mcp_server/futureproof_server.py` compare anchor matches via
`str(row.get("cipcode")) == anchor_cipcode`. If `cipcode` is ever returned
as a float by DuckDB (e.g., a column type drift to `DOUBLE`), `str(11.07)
== "11.07"` works, but `str(11.0700)` returns `"11.07"`, not `"11.0700"`.
The anchor would silently fail to match.

**Location:** `src/mcp_server/futureproof_server.py:3475-3478, 3486-3490`

```python
for row in top_n:
    if (
        row.get("unitid") == anchor_unitid
        and str(row.get("cipcode")) == anchor_cipcode
    ):
```

**The Problem:** CLAUDE.md explicitly states "CIPCODE must always be
treated as string type (XX.XXXX format), never float" — so this should
hold. But the code defensively casts (`str(...)`), which suggests the
author wasn't fully confident. If the cast is needed, it's a sign the
schema is fragile.

**The Fix:** Either:
- Trust the schema and drop the cast (add a one-line assertion in tests);
- OR canonicalize via a helper: `_canonical_cipcode(value)` that handles
  both string and numeric inputs by formatting as `XX.XXXX`.

**Severity:** 🟡 Moderate. Latent. Today's PCP table is `VARCHAR`
cipcode, so this works. A future schema change could break anchor matching
silently — exactly the worst kind of bug.

---

###### Finding 7: `total_qualifying_programs` is silently capped by the scan limit
**Impact:** `LIMIT 5000` at line 3448 caps the materialized list. If a
SOC ever has > 5,000 programs that pass the filter,
`total_qualifying_programs = len(materialized)` would return 5000 — an
undercount. The frontend's "ranked among N programs" line would lie.

**Location:** `src/mcp_server/futureproof_server.py:3446-3449, 3466`

```python
SELECT * FROM ranked
ORDER BY abs_rank
LIMIT {SCHOOLS_FOR_CAREER_SCAN_LIMIT}
...
total_qualifying_programs = len(materialized)
```

Author's note at line 286 says: "SOCs with >5,000 programs producing them
do not exist in practice (largest SOC in PCP has ~2,000 programs)." That's
true today.

**The Fix:** Two reasonable patterns:
1. Run a `SELECT COUNT(*)` from the same CTE separately for
   `total_qualifying_programs`, then materialize only the top-N + 1 anchor.
   Two SQL round-trips (or a `WITH` reuse), but reflects reality.
2. Bump `SCHOOLS_FOR_CAREER_SCAN_LIMIT` to a value provably above the
   largest possible SOC count + 10x headroom — say 50000 — and add a
   runtime warning if a query ever hits it:

```python
if total_qualifying_programs >= SCHOOLS_FOR_CAREER_SCAN_LIMIT:
    logger.warning(
        "schools_for_career hit scan limit",
        extra={"soc": soc_code, "limit": SCHOOLS_FOR_CAREER_SCAN_LIMIT},
    )
```

**Severity:** 🟡 Moderate. Won't fire today; will silently mislead the
day it does.

---

###### Finding 8: Cache memory grows linearly with `limit` distinct values
**Impact:** The cache key includes `limit` (line 3370). The same SOC
queried at `limit=5` (chat default), `limit=10` (HTTP default), and
`limit=25` (power user) will materialize and cache **three** copies of
nearly the same ranked list. Wasteful, since the underlying ranked CTE
is identical — only the slice taken differs.

**Location:** `src/mcp_server/futureproof_server.py:3361-3370`

**The Fix:** Drop `limit` from the cache key and always materialize/cache
the top `SCHOOLS_FOR_CAREER_SCAN_LIMIT` rows. Slice in Python at serialize
time. Cache footprint becomes proportional to (engine_id, mode, soc, cip,
min_conf, min_prog_conf, state) — a much smaller universe.

**Severity:** 🟡 Moderate. Memory waste only. Probably fine at 128-entry
LRU cap, but the principle is wrong — limit is a slice parameter, not a
cache identity parameter.

##### 🔵 Minor Findings

###### Finding 9: `pluralizeOccupation` is a no-op
`frontend/src/components/CompareSchoolsPanel.tsx:44-48` returns its input
unchanged. Documented as a passthrough ("Most BLS titles are already
plural"). Either delete the function and inline-pass the string, or
implement actual pluralization. As-is, it adds a false signal of intent.

###### Finding 10: `statRoiColorClass(undefined)` falls through to `text-accent-alert`
`frontend/src/lib/format.ts:14-19` checks `roi === null` only (strict
equality). If TS ever loosens (refactor, manual cast, runtime data drift),
`undefined` would skip the null branch and read as "below 5" → red. Today's
types preclude it. Either widen to `roi == null` (covers both) or
document the contract.

###### Finding 11: ESC handler binds globally per sheet instance
`frontend/src/components/CompareSchoolsPanel.tsx:97-103` registers a
`window` `keydown` handler each time the sheet opens; cleanup correctly
unregisters. If multiple sheets ever stack (unlikely here), each would
receive the ESC and all close simultaneously. Pattern hygiene only — not
worth fixing in v1.

##### What's Actually Good

- **Mode-dispatch architecture.** A single SQL `WHERE` builder with one
  conditional append. The implementation matches the architect's C2/C4
  exactly — no duplicated mode paths in Python.
- **Cache key design.** Excludes `build_unitid`/`build_cipcode` per
  architect C5; cache hit reuses the materialized list and runs the
  anchor-selection pass on a fresh copy. No cross-anchor pollution.
- **Engine-id sweep.** The new cache is correctly added to
  `_cache_drop_engine` (line 591). Tests verify shutdown clears caches.
- **Whitelist trimming.** `composite_score` and `abs_rank` are computed
  in SQL but trimmed at line 3521 against
  `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP`. Pydantic
  `SchoolForCareerRow` has no field for them. Belt + suspenders.
- **Service layer purity.** `backend/app/services/schools_for_career.py`
  is genuinely a thin shaper. No DuckDB import (locked by
  `test_service_module_does_not_import_duckdb`). Single
  `mcp_client.call` dispatch. Clean.
- **Anchor handling correctness.** All three cases — in top-N, below
  top-N (appended), absent (no row) — handled at lines 3471-3495 in a
  single pass over `materialized`. `anchor_in_top_n` is correctly set
  for each.
- **Input validation depth.** SOC + CIP regex at the handler (lines
  3287, 3298) AND at the FastAPI `Path()` (router lines 36, 65-66).
  Bool/int/string/whitespace edge cases handled defensively for
  `build_unitid` (lines 3339-3354). `state_abbr` upper-cased and
  alpha-checked (lines 3329-3331). Limit clamped (line 3312).
- **SQL parameterization.** All user inputs (`soc_code`, `cipcode`,
  `state_abbr`) flow through DuckDB `$name` parameters. The only string
  interpolation is the `IN (...)` clause for confidence tiers, sourced
  from a closed enum after default-clamp. No SQL injection vector.
- **Concurrency.** `_cache_lock` held during both read and write.
  `_engine_init_lock` for first-time engine construction. `query_sql`
  holds the engine's RLock from init through execute, preventing
  shutdown-mid-query.
- **Test coverage.** 15 P0/P1 tests on the MCP handler; 6 router tests;
  6 service tests; 9 frontend tests. Edge cases (anchor partial,
  empty-after-filter, drop-confidence escape, scan-limit clamp,
  whitelist-no-leak) are all covered.

##### Required Changes — Routing

| # | Title | Owner | Severity |
|---|-------|-------|----------|
| 1 | Fix frontend race in `load()` (generation counter) | Implementation | 🟠 |
| 2 | Replace raw exception strings in handler error path with opaque code + log | Implementation | 🟠 |
| 3 | Catch `pydantic.ValidationError` separately in router; opaque detail | Implementation | 🟠 |
| 4 | Stop refetching on inline disclosure toggle (lift state, not unmount) | Implementation | 🟠 |
| 5 | Add focus trap (or remove `aria-modal="true"`) in SheetEnclosure | Implementation | 🟡 |
| 6 | Add scan-limit warning log + DQ guard | Implementation | 🟡 |
| 7 | Drop `limit` from cache key; slice in Python | Implementation | 🟡 |
| 8 | Anchor cipcode canonicalization helper | Implementation | 🟡 |

##### Questions for the Author

- **What happens if the MCP server is unavailable?** `mcp_client.call`
  presumably raises something. The router doesn't catch it. Today that
  becomes a 500 — acceptable, but worth confirming the failure mode is
  intentional and not just "we haven't thought about it."
- **What's the rollback plan if the new cache eats memory?** The
  `FUTUREPROOF_OUTCOMES_CACHE` env flag turns the cache off entirely.
  Confirmed. ✓
- **Have we load tested at limit=25 on the largest SOC?** The §6 smoke
  test hit 973 qualifying programs — large but not the full 5,000 cap.
  Useful to know real p95 latency at the cap.
- **What monitoring/alerting do we have for the new endpoints?** No
  Prometheus / structured-log-counter wiring evident. Acceptable for v1
  if other endpoints lack it too, but file an infra ticket.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

Ship the four 🟠 fixes (#1-#4). The 🟡 items (#5-#8) can be a v1.1
follow-up; flag them in §10 so they don't get lost.

> Look, I love Claude, BUT — the architecture is sound and the
> implementation matches the spec. The four serious findings are all
> classic AI blindspots: the frontend race, the leak-via-exception-string,
> the Pydantic v2 inheritance trap, and the unmount-on-toggle. None
> would fail a unit test. All four would surface in production within
> two weeks. This is exactly why we need human oversight. The CEO said
> use AI. He didn't say ship it without review.

---

## §9 Verification

**Status:** APPROVED WITH NOTES
**Verified:** 2026-04-29 23:47
**Verified by:** @fp-builder

### Backend (@fp-builder)

| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS (with pre-existing notes) | 6 pre-existing errors in `app/services/guidance.py` (2× `F821 Any` undefined name, 4× `E501` line-too-long). None in spec-new files. |
| Type check (mypy) — spec files only | PASS (after fix, attempt 1) | `app/routers/careers.py`, `app/services/schools_for_career.py`, `app/models/career.py` — 0 errors. See Build Accountability Log. |
| Tests (pytest, root — incl. MCP) | PASS | 1713 passed, 1 deselected in 55.22s. `tests/mcp/test_get_schools_for_career.py` included and green. |
| Tests (pytest, backend) | PASS | 1252 passed, 0 failed, 164 warnings in 4.29s |

#### ruff Pre-Existing Errors (do not block this spec)

All 6 errors are in `app/services/guidance.py`, which is not part of this spec. Logged for separate triage.

```
F821 Undefined name `Any`  → app/services/guidance.py:639, 673
E501 Line too long (93 > 88) → app/services/guidance.py:716, 717
E501 Line too long (91 > 88) → app/services/guidance.py:873
E501 Line too long (90 > 88) → app/services/guidance.py:876
```

### Frontend (@fp-builder)

| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS (with pre-existing failures) | 823 passed, 11 failed (pre-existing), 1 skipped — 835 total. New spec tests: 9 passed, 1 skipped. |
| Production build (Vite) | PASS | 548 modules transformed; 1 chunk-size advisory (pre-existing, not an error) |

#### vitest Pre-Existing Failures (documented in §6, do not block this spec)

11 failures across 2 files, both documented as pre-existing in §6:

| File | Failures |
|------|----------|
| `src/components/menu/CompareView.test.tsx` | 9 failed (renders one Risk Headline card per boss; renders character cards; renders boss grid with skill count badges; renders salary figures; handles 3 builds; handles 4 builds; renders branch preview with convergence badges; Gemma summary text; fallback loading placeholder) |
| `src/components/menu/PentagonOverlay.test.tsx` | 2 failed (legend lists every build's label; aria-label reports the build count for screen readers) |

#### New Spec Tests — CompareSchoolsPanel.test.tsx

`src/components/CompareSchoolsPanel.test.tsx`: **9 passed, 1 skipped, 0 failed.** All new P0/P1 tests green.

### Build Accountability Log

| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | mypy failed | `app/models/career.py:334` — `Missing type arguments for generic type "dict"` (`[type-arg]`) in pre-existing `IntentResult.alternatives` field (not introduced by this spec) | Changed `list[dict] \| None` → `list[dict[str, object]] \| None`; mypy clean on re-run |

---

⚠ APPROVED WITH NOTES — Build is clean for all code introduced by this spec. The 11 vitest failures are in `CompareView.test.tsx` and `PentagonOverlay.test.tsx`, documented as pre-existing in §6. The 6 ruff errors are pre-existing in `guidance.py`, not touched by this spec. One mypy type annotation fix was applied to a pre-existing line in `career.py` (fix is safe: narrows `dict` to `dict[str, object]`). All new backend tests, MCP tests, and `CompareSchoolsPanel.test.tsx` tests are green. Ready for step 9 (COMPLETION).

---

## §10 Discussion

```
[2026-04-29] @claude-code → @fp-architect, @fp-data-reviewer
Spec was reconstructed from conversation context after the original on-disk
file was lost (cause undetermined). Conditions C1–C7 (architect) and the 5
required changes (data-reviewer) have been folded into §1–§4 inline. Both
review verdicts above are preserved verbatim from the first pass.

[2026-04-29] @jcernauske → @claude-code
Authorized proceed to step 2 (DESIGN VISION) without a formal re-review pass.
Conditions are applied in §1–§4 and auditable in the file; visionary and
later gates will surface anything missed. §5 verdicts remain on record as
CHANGES REQUESTED (first pass) for traceability.

[2026-04-29] @claude-code → @genai-architect
GenAI review fixes R1–R5 applied to §4 MCP tool surface. R6 and R7 captured
as implementation-time hygiene notes in §4. Proceeding to step 4
IMPLEMENTATION.
```

---

### @genai-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-29

---

#### 1. JSON Schema Correctness

**One tool vs. two tools — verdict: one tool with a discriminator is correct.**

The single-tool-with-`mode` design is the right call for this surface. Gemma
4 (both Ollama and OpenRouter) handles discriminated inputs well; the mental
model "one tool that does leaderboard lookup" is simpler than two tools whose
descriptions Gemma has to adjudicate. The practical test: Gemma's failure mode
on a discriminated tool is `cipcode` being omitted for `by_cip_and_soc` —
that is a recoverable structured error, not a silent wrong answer. Two tools
would require Gemma to choose the right tool before supplying any arguments,
doubling the failure surface area. One tool is the correct call.

**Conditional-required `cipcode` — verdict: handler-enforced is acceptable, with one fix required.**

The JSON Schema as written declares only `soc_code` as required. This is
technically correct: `cipcode` is conditionally required and JSON Schema
`if/then/else` conditionals are awkward and inconsistently supported by LLM
function-calling parsers. Handler enforcement is the pragmatic path. However,
the tool description must make the conditionality explicit — see §1.5
(Tool Description) below. The structured error return (`{"error": ...}`) when
`mode=by_cip_and_soc` and `cipcode` is absent is the right fallback.

**`min_program_confidence` as `low/medium/high` enum — verdict: correct shape, minor description fix needed.**

The three-value enum is legible to Gemma and maps cleanly to the stored
`confidence_tier_program` column. A numeric threshold (e.g., `min_completions:
30`) would be more precise in the abstract but would require Gemma to know the
completions-count semantics of the column — it does not. The enum labels are
self-describing. The only fix needed: the description should say "default
`low` means no program-level sample-size filter is applied — the school simply
needs programs on the books." Without that, Gemma cannot reason about when to
tighten it.

**`state_abbr` enum validation — verdict: trust the data layer, no schema enum required.**

Adding all 51 valid USPS codes to the JSON Schema would harden Gemma grounding
but also guarantee that non-standard inputs (territories, DC spelled out,
typos) produce "I cannot call this tool because my input doesn't match the
enum" failures instead of a graceful empty result from the handler. The data
layer already normalizes via the `state_abbr` column filter; an unknown state
simply returns zero rows rather than erroring. This is the better UX for a
chat surface. Leave `state_abbr` as a free `string` with a clear description.

**Required fix R1:** Add format examples to `state_abbr` description: "2-letter
USPS abbreviation (e.g., 'IN', 'CA'). Unknown values return an empty result
rather than an error."

---

#### 2. Parameter Constraints for Tool-Calling Robustness

**SOC/CIP format regexes — verdict: do NOT add `pattern` constraints.**

The spec's existing validation regexes (`_SOC_CODE_PATTERN`, `_CIPCODE_PATTERN`
in `futureproof_server.py`) are applied at handler runtime, not in the JSON
Schema. This is the right split for a chat-callable tool. If `pattern` is
declared in the JSON Schema, Gemma's tool-call parser will reject inputs like
`"15.1252"` (period instead of hyphen in SOC) or `"110701"` (no dot in CIP)
before the handler has a chance to normalize or return a helpful error. The
correct approach is what is already in place: no schema-level `pattern`, but
the description includes the format example and the handler returns a
structured error on invalid format. Gemma can retry with the correct format
when given a clear error message; it cannot self-correct when its own parser
silently blocks the call.

**`build_unitid` / `build_cipcode` anchor pair — verdict: description needs explicit "pass both or neither" rule.**

The current descriptions are:
- `build_unitid`: "Optional anchor — student's school unitid."
- `build_cipcode`: "Optional anchor — student's program cipcode (XX.XXXX string)."

These are too sparse. Gemma has no signal that these are an atomic pair. In
practice, if Gemma has a build context available (from the chat session's
loaded `program_career_paths` data), it will correctly pass both. But in an
open chat ("show me nursing schools") there is no build context, and Gemma
must understand that passing only `build_unitid` without `build_cipcode` is
not a partial anchor — it is treated as no anchor. The handler comment "treats
partially-provided as anchor=None" is code-internal and not communicated to
Gemma.

**Required fix R2:** Rewrite both anchor parameter descriptions to read:
- `build_unitid`: "Optional. The student's current school IPEDS unitid, used to highlight their program in the leaderboard. MUST be passed together with build_cipcode — either both or neither. Passing only one is treated as no anchor."
- `build_cipcode`: "Optional. The student's current program CIP code (XX.XXXX format). MUST be passed together with build_unitid — either both or neither."

---

#### 3. Response Shape Budget for Chat

**Token budget estimation.**

`SchoolForCareerRow` carries these wire fields (from §4 Pydantic model):
`rank`, `unitid`, `institution_name`, `institution_control`, `state_abbr`,
`cipcode`, `program_name`, `soc_code`, `occupation_title`, `stat_ern`,
`stat_roi`, `earnings_1yr_median`, `net_price_annual`, `cost_of_attendance_annual`,
`tuition_in_state`, `tuition_out_of_state`, `overall_confidence`,
`confidence_tier_program`, `match_quality`, `is_anchor` — 20 fields per row.

A realistic average row serializes to roughly 420–480 characters (~110–125
tokens at ~3.8 chars/token). At `limit=25` + 1 anchor row = 26 rows:

- 26 rows × 450 chars ≈ 11,700 characters ≈ **~3,100 tokens** for the rows alone.
- Plus the `SchoolsForCareerResponse` envelope fields (mode, soc_code,
  occupation_title, cipcode, program_name, anchor_in_top_n,
  total_qualifying_programs, confidence_filter_applied, state_filter_applied,
  min_program_confidence_applied, generated_at) ≈ ~200 tokens.
- Total worst case: **~3,300 tokens for the tool result alone.**

Gemma 4's context window is large enough to absorb this, but the tool result
is injected into a conversation that already carries system prompt (~300
tokens), chat history, and the build context block (~400–1,000 tokens
depending on scope). For a multi-turn chat session on an Ollama-local instance
with the `gemma4:27b` model the practical generation budget is tight. At
`limit=25` the tool result alone consumes more context than the rest of the
chat combined.

**Recommendation: lower the default `limit` for chat-originated calls from 10
to 5, and document a `compact` pattern.**

The default `limit=10` in the JSON Schema is already a reasonable chat default
(not 25). Keep it. However:

**Required fix R3:** Change the JSON Schema `default` for `limit` from `10` to
`5` for chat-facing calls. The reasoning: a chat surface answering "what's the
cheapest path to RN?" does not need 10 rows — Gemma should synthesize the
answer from the top 3–5 and say "and there are 184 programs total." The
`total_qualifying_programs` field already carries the universe count, so
reducing `limit` does not hide information.

**Required fix R4:** Drop `tuition_in_state`, `tuition_out_of_state`, and
`cost_of_attendance_annual` from `SchoolForCareerRow` when they are not
explicitly asked for by the query. The current spec includes all three tuition
fields on every row. For the chat surface, `net_price_annual` is the
student-relevant cost signal (after grants/scholarships); the raw tuition
fields are noise that adds ~60 characters per row (8% of row budget). These
three fields should be retained in the HTTP endpoint response shape (the React
table needs them per §3.C) but should be omitted from the MCP tool's response
field whitelist (`SCHOOLS_FOR_CAREER_RESPONSE_FIELDS`). The spec can note
"full tuition breakdown available via the HTTP endpoint; MCP tool returns
`net_price_annual` only."

**`generated_at: datetime` — verdict: pure noise for Gemma, but harmless.**

Gemma has no use for a UTC timestamp on a leaderboard result. It cannot
reason about data freshness from a single timestamp, and it will never quote
it back to a student. The field costs ~30 characters per response (~8 tokens)
and adds zero information value at the chat layer. That said, removing it from
the wire would require a Pydantic model split between the MCP tool response
and the HTTP endpoint response, which is scope creep. Leave it in the model
but note it is front-end/audit-useful, not Gemma-useful. It is not worth a
spec change — just documenting for awareness.

---

#### 4. Tool Description Quality

**Current description (verbatim from §4):**

> "Given a SOC code (and optionally a CIP code), return the top programs
> producing that occupation, ranked by a composite of earnings stat (ERN) and
> ROI stat. Filters out low-confidence rows by default. Modes: 'by_soc' (all
> programs producing this SOC) or 'by_cip_and_soc' (only programs at this CIP
> that produce this SOC). Pass build_unitid + build_cipcode to mark the
> student's anchor."

**Assessment: not specific enough to prevent tool confusion with `get_career_paths`.**

The existing `get_career_paths` description reads: "Core product query. Given
a school (unitid) and major (cipcode), returns every career outcome (SOC code)
the program leads to, with the full five-stat pentagon..."

The boundary is: `get_career_paths` is school-anchored (one school, all its
careers). `get_schools_for_career` is career-anchored (one career, all schools
that produce it). A student asking "what does Computer Science lead to at
Indiana University?" maps to `get_career_paths`. A student asking "what schools
have good Computer Science programs for becoming a software developer?" maps to
`get_schools_for_career`. That boundary is not stated anywhere in either
description. Gemma will guess — and on SOC-adjacent questions it will default
to whichever tool it has seen more examples of, which is `get_career_paths`
(already in the tool registry; this tool is new).

**Required fix R5:** Rewrite the tool description to make the boundary explicit.
Proposed replacement:

> "Career-to-school leaderboard. Use this tool when the student wants to
> COMPARE SCHOOLS for a specific career outcome — not for questions about one
> school's programs. Key distinction: get_career_paths answers 'what does
> [school+major] lead to?' — this tool answers 'which schools are best for
> producing [career]?'. Two modes: 'by_soc' returns all programs nationally
> that lead to the given occupation, ranked by earnings (ERN) and ROI;
> 'by_cip_and_soc' narrows to programs in a specific major field (cipcode)
> that lead to the occupation — the tightest apples-to-apples comparison.
> When mode='by_cip_and_soc', cipcode is required. Pass build_unitid +
> build_cipcode together (both or neither) to pin the student's current school
> as a reference row in the results."

This description front-loads the decision boundary ("COMPARE SCHOOLS"), states
the negative case explicitly ("not for questions about one school's programs"),
and names the competing tool by name — all established patterns for reducing
tool ambiguity in multi-tool harnesses.

---

#### 5. Representative Chat Query Walkthroughs

**Query A: "What's the cheapest path to becoming a registered nurse?"**

Target tool call sequence:

1. Gemma's first move: Gemma does NOT have the SOC code for "registered nurse"
   in its context (the build might not be nursing-related, and no prior tool
   result has surfaced `29-1141`). Gemma should call `get_occupation_data` with
   a fuzzy attempt — but `get_occupation_data` requires an exact SOC code, not
   a name. **This is the gap**: none of the available tools accept a free-text
   occupation name as input.

   Actual behavior: Gemma 4 will either (a) recall `29-1141` from training
   data (it is a well-known SOC code) and call `get_schools_for_career`
   directly, or (b) emit a chat response explaining it needs the SOC code.
   Behavior (a) is likely for "registered nurse" specifically because it is
   the most common nursing SOC. For less common occupations this path breaks.

2. Optimal path (when Gemma knows the SOC):
   `get_schools_for_career(mode="by_soc", soc_code="29-1141", limit=5)`
   with no anchor (no build context), sorted by composite desc.

3. Gemma synthesizes: "The lowest-cost path to registered nursing based on
   ROI is [school] in [state] — net price $X, earnings $Y in year one. There
   are 184 programs in the data..."

4. If the student wants a specific state: Gemma re-calls with
   `state_abbr="IN"` (or whatever state was named).

**Gap to flag:** Gemma cannot resolve "registered nurse" → `29-1141` using the
available tool set alone. For the demo query to work end-to-end in a cold
context, one of two things must be true: (a) the system prompt or chat context
pre-loads the SOC code, or (b) Gemma uses training-data recall. For the demo
this is acceptable (Gemma 4 knows well-known SOC codes). For the general case
— "what's the cheapest path to becoming a [less common career]?" — the
missing tool is a name-to-SOC resolver. That is Spec B's `searchCareers`
surface, not this spec's scope. Document the dependency.

**Query B: "Show me schools that teach Marketing and produce Brand Managers, ranked by ROI"**

Target tool call sequence:

1. Gemma needs both a CIP code for "Marketing" and a SOC code for "Brand
   Managers." Marketing is CIP `52.14` (Marketing, General) or related; Brand
   Manager maps approximately to SOC `11-2021` (Marketing Managers).

2. Gemma likely has training-data recall for both. Optimal path:
   `get_schools_for_career(mode="by_cip_and_soc", soc_code="11-2021",
   cipcode="52.1401", limit=5)`

3. "Ranked by ROI" matches the default composite sort (ERN+ROI)/2; Gemma can
   note this in its reply. If the student wants pure ROI sort, there is no
   parameter for that — the composite is fixed. Gemma should acknowledge this
   honestly: "I'm ranking by a blend of earnings and ROI — here are the top
   programs."

4. Gemma synthesizes the result table into a prose summary.

**Gap to flag (same as Query A):** CIP code resolution from free text
("Marketing") relies on Gemma's training-data recall. `52.1401` is common
enough that this works. `cipcode` for "Marketing Communications" or "Digital
Marketing" would require a lookup tool. Again, Spec B scope.

**Chain experience assessment:** Both queries work in 1–2 tool turns, which is
within the existing `max_turns` budget in `generate_with_tools_loop`. No
chaining pathologies are expected. Gemma does not need `get_occupation_data`
as a prerequisite for `get_schools_for_career` — it can call the leaderboard
tool directly if it already has or recalls the SOC code.

---

#### 6. Fallback Behavior Under Gemma Unavailability

The spec notes (§4, Gemma-touching work): "If the tool is unreachable,
Gemma's existing chat-guardrails fallback (no tool call) is unchanged."

This is correct and the response shape is not brittle to asymmetric
availability. The HTTP endpoints (`GET /careers/{soc}/schools`,
`GET /majors/{cip}/schools/for-career/{soc}`) hit the MCP server directly via
`mcp_client.call` — they do not route through the Gemma chat surface.
The React component fetches these endpoints directly; Gemma's availability is
not on the call path. When Gemma is down, the leaderboard panel on RevealScreen
and BuildResultsScreen continues to work. Only the chat-originated "ask me
what schools are good for nursing" path is unavailable.

**One shape issue to address:** `SchoolsForCareerResponse.generated_at` is a
`datetime` field. The service layer calls `SchoolsForCareerResponse.model_validate(raw)`
on the MCP response. The MCP handler must serialize `generated_at` as an ISO
8601 string (not a `datetime` object) in its JSON return, because the
`mcp_client.call` return travels across a serialization boundary. If the
handler returns a Python `datetime` object in a dict, `json.dumps(result,
default=str)` in the tool dispatch loop (line 1073 of `gemma_client.py`)
will coerce it to a string — fine. But `model_validate` on the service side
expects either a datetime-parseable string or a datetime object. Verify the
round-trip is clean. Recommend annotating the MCP handler with an explicit
`generated_at: str = datetime.now(timezone.utc).isoformat()` rather than a
raw datetime object so the serialization boundary is unambiguous.

**Required fix R6:** In `_handle_get_schools_for_career`, set
`generated_at` as `datetime.now(timezone.utc).isoformat()` (a string) in the
returned dict, not as a datetime object. `SchoolsForCareerResponse` Pydantic
model will coerce the ISO string to a `datetime` on `model_validate` — the
round-trip is safe as long as the MCP handler produces a string, not an object.

---

#### 7. Logging

`logs/gemma.jsonl` capture of `tool_name` and `tool_args` is **automatic and
requires no new wiring** for this tool.

Tracing through the call path in `gemma_client.py`:

- `generate_with_tools_loop` (the multi-turn harness used by `ask_gemma.py`)
  processes each tool call at lines 1057–1097 of `gemma_client.py`. For each
  dispatched tool it constructs a `ToolCallTurn` (line 1090–1097):
  `tool_name=fn_name`, `tool_args=fn_args`.
- `_log_tool_turn` is called at line 1099, which calls `_log_exchange`
  internally, which appends to `logs/gemma.jsonl`.
- The `tool_name` field in the log record is set from `fn_name` — whatever
  name Gemma uses in its tool call. When Gemma calls `get_schools_for_career`,
  `fn_name = "get_schools_for_career"` and `fn_args` carries the full
  argument dict. No wiring is needed.
- The MCP tool dispatch path in `_handle_get_ai_exposure` et al. logs to
  `logs/mcp.jsonl` via the `@timed` decorator in `_telemetry.py`. The new
  `_handle_get_schools_for_career` should also be decorated with `@timed` for
  MCP-layer timing visibility, consistent with the existing handlers. The spec
  §4 file-changes table does not mention this decoration explicitly.

**Required fix R7:** Add a `@timed("get_schools_for_career", extract=...)` decorator
to `_handle_get_schools_for_career` in the implementation, consistent with
the `@timed` decorators on `_fetch_crosswalk_socs` (line 1782) and
`_build_substituted_rows` (line 1831) in the existing server. The `extract`
lambda should capture `mode`, `soc_code`, `cipcode` (or empty string),
`row_count`, and `cache_hit` — keeping the bounded-cardinality policy documented
in `_telemetry.py`. This does not require a spec change — it is an
implementation hygiene note for the implementer.

---

#### Summary of Required Changes

| ID | Severity | Location | Fix |
|----|----------|----------|-----|
| R1 | Minor | MCP tool schema: `state_abbr` description | Add format examples and "unknown values return empty result" note. |
| R2 | Significant | MCP tool schema: `build_unitid` + `build_cipcode` descriptions | Document "pass both or neither" contract explicitly. |
| R3 | Significant | MCP tool schema: `limit` default | Lower default from 10 to 5 for chat-originated calls (schema default). |
| R4 | Significant | `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS` whitelist | Omit `tuition_in_state`, `tuition_out_of_state`, `cost_of_attendance_annual` from MCP tool response; keep them on HTTP endpoint response. |
| R5 | Significant | MCP tool description | Rewrite per proposed text above: front-load boundary, name the competing tool, document mode/conditionality. |
| R6 | Minor | `_handle_get_schools_for_career` implementation | Serialize `generated_at` as ISO 8601 string in the returned dict, not as a datetime object. |
| R7 | Minor | `_handle_get_schools_for_career` implementation | Decorate with `@timed("get_schools_for_career", extract=...)` consistent with existing handlers. |

R3 and R4 are the highest-impact items — they materially reduce the token
footprint of the tool result in chat context. R5 is the highest-impact item
for correct tool selection. R2 prevents anchor silently resolving to None when
Gemma passes only one half of the pair.

None of these require data schema changes or Pydantic model restructuring beyond
the field-whitelist split called out in R4. R4 is the only change that touches
`§4` content — specifically, a note should be added to the `SCHOOLS_FOR_CAREER_RESPONSE_FIELDS`
constant documentation distinguishing "MCP whitelist (no raw tuition fields)"
from "HTTP response shape (full tuition fields, per §3.C table)."

---

#### Verdict

**CHANGES REQUESTED**

R3, R4, and R5 must be addressed in §4 before IMPLEMENTATION. R1 and R2 should
be folded in as description edits to the MCP tool surface block in §4. R6 and
R7 are implementation-time notes for the implementer — they do not require
re-review.

Once R1–R5 are applied in §4, this tool schema is approved for implementation.
The overall architecture (one discriminated tool, handler-enforced conditional,
single windowed query, LRU cache keyed without anchor params) is sound and
consistent with the established MCP patterns in this codebase.

---

## §11 Final Notes

**Human Review:** PENDING

**Supersession note (2026-04-29):** This spec formally supersedes
`docs/specs/feature-school-discovery.md` (skeleton, never implemented). The
school-discovery skeleton scoped a CIP-anchored discovery surface reachable
only from Set Your Course's `school_gap` chip CTA — a surface that never
shipped (no `/discover` route, no router, no component checked in). This
spec's `by_cip_and_soc` mode covers the same data surface from inside an
active build, plus Spec B's career-search header entry covers free-text
discovery. The skeleton is retired.

**File-recovery note (2026-04-29):** This file is a reconstruction.
Original on-disk content (1,206 lines, including first-pass §5 reviews) was
lost during the architecture-review pass. Cause undetermined; investigation
notes in conversation transcript. Reconstruction sources: full conversation
context, including verbatim §5 review content from the @fp-architect and
@fp-data-reviewer agent runs. Conditions C1–C7 + 5 data-reviewer items have
been folded into §1–§4 inline so a re-review can flip §5 verdicts to APPROVED.

[Final thoughts, lessons learned, follow-up items.]
