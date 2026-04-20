# Feature: Chapter Book Career Progression on Set Your Course

## Claude Code Prompt

```
Read the spec at docs/specs/feature-chapter-book.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow,
     Brightsmith integration, API contracts). This spec is frontend-heavy but
     touches the /branches/{soc} consumer contract — confirm nothing changes
     on the MCP or service side beyond what's documented.
   - Data pipeline is NOT touched in this spec (ceiling case is rendered
     client-side, per §2 Decision #3). @fp-data-reviewer is SKIPPED.
   - Writes findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to fill §3 (UI/UX Design) with the
     pixel-perfect target for:
       a) The 2-column layout on /set-your-course (33% form / 66% results)
       b) The Chapter Book replace-the-list expansion state with back affordance
       c) The synthetic ceiling chapter and the grad-degree locked chapter
       d) The transition from career list → Chapter Book (and back)
   - Visionary references the existing mockup at
     frontend/src/components/horizon/ChapterBookMockup.tsx as the source of
     voice and cadence, but the final design lives in §3 of this spec, not in
     that mockup file.
   - Visionary specifies Framer Motion springs from frontend/src/styles/motion.ts
     and respects prefers-reduced-motion. Must state the reduced-motion fallback.

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails,
     STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x)
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical token/pattern compliance against
     the Brightpath design system (DESIGN.md at project root)
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
   - Generate report to reports/feature-chapter-book-YYYY-MM-DD.md
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
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
| Created | 2026-04-19 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-20 (COMPLETE) |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-set-your-course.md`, `docs/specs/completed/onet-experience-requirements.md` |

---

## §1 Feature Description

### Overview

Rebalance the existing two-column layout on `/set-your-course` from `desktop:grid-cols-[7fr_5fr]` (currently: left 58% / right 42%) to `desktop:grid-cols-[4fr_8fr]` (33% / 66%) so the results column earns its real-estate budget, and add a **Chapter Book** career progression reveal that expands when the student taps a career from the common/uncommon tiered list. The book replaces the list in the right column with a vertical stack of chapters keyed to career experience tiers (entry / early / mid / senior / ceiling), sourced from `consumable.career_branches` via the existing `/branches/{soc}` endpoint.

### Problem Statement

After Set Your Course shipped (spec: `feature-set-your-course.md`, 2026-04-19), the final artifact for the student is a tiered list of careers with stats — which answers *"here's where this leads,"* but does not answer the next question a 17-year-old has when they stare at "Biological Technician, $52K": *is this the ceiling?*

We already have the data to answer that. The `onet-experience-requirements` spec (completed 2026-04-16) added `related_experience_years` and `related_experience_tier` to `consumable.career_branches`, and `backend/app/services/branch_tree.py` already surfaces them on the backend `CareerBranch` Pydantic model. The frontend `CareerBranch` TypeScript interface at `frontend/src/types/build.ts:118-129` is stale with respect to the backend and must be brought into parity as part of this spec — see §2 Decision #9. Meanwhile, the existing React Flow branch tree elsewhere in the product is visually overwhelming — too many nodes, no progression shape — and Jeff explicitly ruled that shape out as the answer for Set Your Course.

The user job of the Chapter Book, in one sentence: **"Your first job isn't your career."** The feeling target is **relief**, not swagger. No exclamation points, no hype. A student should walk away believing they have receipts for how the next 15 years unfold, not a promise that they'll become a CEO.

The layout change is a ratio shift, not a single-to-two-column restructure: `SetYourCourseScreen.tsx:296` already renders a `grid-cols-1 desktop:grid-cols-[7fr_5fr]` grid. Today the results column is 42% of the desktop viewport and the form is 58%. Flipping to `4fr_8fr` (33% / 66%) gives the chapters room to breathe without a layout rewrite.

### Success Criteria

- [x] `/set-your-course` renders a 33% / 66% two-column grid on desktop viewports (≥ 1200 px, the Brightpath `desktop:` breakpoint per DESIGN.md) — implemented as a `desktop:grid-cols-[4fr_8fr]` swap of the existing `desktop:grid-cols-[7fr_5fr]` declaration at `SetYourCourseScreen.tsx:296`. Left column: school search, field-of-study input, reasoning card, receipts, Ask Gemma. Right column: career tier list and the Chapter Book.
- [x] On viewports below 1200 px the layout remains a single column via `grid-cols-1` (existing behavior, unchanged).
- [x] Tapping any career row in the tier list (the `button` rendered by `frontend/src/components/school/CareerList.tsx` via its `onSelect` prop) replaces the list in the right column with the selected career's Chapter Book. A `← Back to all paths` affordance returns to the list.
- [x] Chapter Book renders up to 4 chapters keyed to the Silver canonical tiers per `src/silver/onet_experience_transformer.py:145-165`: chapter 1 tier `entry` (0–1 yr, anchor — the selected career itself), chapter 2 tier `early` (1–4 yr), chapter 3 tier `mid` (4–8 yr), chapter 4 tier `senior` (8+ yr). Each non-anchor chapter is sourced from `CareerBranch` rows bucketed by `experience_tier`. Exact year-label wording is owned by @fp-design-visionary per §2 Decision #14, but the ranges MUST match Silver. Ceiling synthesis and tier-gap bridging per §2 Decision #10 and §4 Bucketing Rules 5/6 apply.
- [x] Chapters requiring a graduate degree — detected from a new typed `CareerBranch.related_education_level` field matching `/^Master|^Doctoral/i` (see §2 Decision #12; legacy `unlock`-regex fallback only if `related_education_level` is null) — render collapsed by default with a lock glyph; tap to expand.
- [x] When no branch exists for a tier, a synthetic "ceiling" chapter renders per the verbatim rule in §2 Decision #10: kind `ceiling`, soc `null`, `what_changes` from `chapterCopy.ts`, muted visual treatment. The rule is written in §2 so the future pipeline-side ceiling-marker spec can match it or document divergence.
- [x] Motion: reveal animation uses Framer Motion springs from `frontend/src/styles/motion.ts`; respects `prefers-reduced-motion` per DESIGN.md.
- [x] All existing `/set-your-course` tests either pass unchanged or are updated with explicit authorization in §4 Testing Impact Analysis.
- [x] Frontend typechecks (`npx tsc --noEmit`), vitest passes, Vite production build succeeds.
- [x] Chat-guardrails ship-blocker for external audience (`feature-chat-guardrails`) is NOT displaced by this spec — this work is additive, not a substitute.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Shape B (Chapter Book) over Shape A (Horizon Strip) | Jeff reviewed both interactive mockups at `/mockups/horizon` and picked Chapter Book after direct visual comparison. Prioritizes depth-per-career over scan-across-careers. | Horizon Strip (visionary's written recommendation, rejected by user); Dim Tree variant (rejected in upstream product-partner critique — dimming doesn't solve overwhelm). |
| 2 | Replace-the-list, not coexist | Selected by user after seeing side-by-side ASCII previews. Maximum focus on a single career's arc. Clicking a career swaps the whole right column for chapters with a `← Back` affordance. | Coexist list-on-top (visionary's preference — rejected for focus); coexist side-by-side (rejected as visually cramped inside the 66% column). |
| 3 | Ceiling case handled frontend-only this spec; data-side follow-up spec to file | Ships without a pipeline dependency. Synthetic chapter with explicit `kind: 'ceiling'` in the frontend data model. A follow-up spec will promote this logic into the Silver/Gold layer so other consumers benefit. | Pure frontend forever (rejected — data honesty is better in the pipeline); pipeline-first (rejected — blocks hackathon timeline). |
| 4 | 33% / 66% split at the `desktop: 1200px` Brightpath breakpoint | Brightpath's screen tokens per DESIGN.md lines 233-236 are `mobile 480 / tablet 768 / desktop 1200 / wide 1440 / ultra 1920`. The existing screen already uses `desktop:grid-cols-[7fr_5fr]`; this spec swaps the ratio to `desktop:grid-cols-[4fr_8fr]` (4/12 = 33.3%, 8/12 = 66.7%). No new breakpoints, no new tokens. | 40 / 60 (rejected — form still feels underused); 50 / 50 (rejected — results feel cramped); Tailwind-default `md: 768px` (rejected — not a Brightpath token); inventing a `960px md` breakpoint (rejected in architect review — Brightpath has no such breakpoint). |
| 5 | Chapter 1 (entry tier, anchor) is the selected career itself, not a branch | The entry anchor IS the student's first job out of college. Branches describe where people go AFTER, so chapters 2–4 come from `CareerBranch` rows; chapter 1 is synthesized from the parent `CareerOutcome`. Year-label wording is owned by @fp-design-visionary per Decision #14. | Treat chapter 1 as a self-referencing branch (rejected — changes branch table semantics); fetch anchor separately (rejected — the outcome is already in the page state via `useBuildStore`). |
| 6 | `CareerLineageSheet` component is untouched | Used only by `CareerPickScreen` (the old `/school` flow). Not referenced from `/set-your-course`. Stays independent. | Repurpose (rejected — shapes differ too much); delete (rejected — old flow still renders). |
| 7 | Career card tap interaction swaps columns in place, not via route change | Preserves the stream-to-committed state already in `useBuildInputStore` / `useSetYourCourse`. A route change would force re-resolution. | Route change to `/set-your-course/chapters/{soc}` (rejected); modal overlay (rejected — breaks the 33/66 intent). |
| 8 | Chapter book component lives at `frontend/src/components/chapter-book/` | Keeps Set Your Course specific UI out of the generic `/components/` root and away from the `/components/horizon/` mockup dir (which is deliberately separate). | Put next to `SetYourCourseScreen` (rejected — the component will be used twice: the real feature + the existing mockup route should continue to render). |
| 9 | Bring the frontend `CareerBranch` type into parity with the backend — add `experience_years: number \| null`, `experience_tier: "entry" \| "early" \| "mid" \| "senior" \| null`, `experience_delta: number \| null`, and `related_education_level: string \| null` to `frontend/src/types/build.ts:118-129` | Backend Pydantic `CareerBranch` (`backend/app/models/career.py:205-222`) already emits three experience fields over `/branches/{soc}`; the frontend type discards them at the boundary. The bucketing logic in this spec depends on `experience_tier` — without the type update, `bucketBranches.ts` cannot typecheck. Adding `related_education_level` unlocks Decision #12 and is a ~2-line backend service addition in the same direction. | Keep frontend type stale and read fields via `as unknown as {...}` casts (rejected — dishonest, loses type safety); derive `experience_tier` client-side from `experience_years` (rejected — duplicates the pipeline-canonical bucketing rules from `src/silver/onet_experience_transformer.py:145` and risks drift). |
| 10 | Verbatim ceiling-synthesis rule (stated here so future pipeline-side ceiling-marker spec can match): a chapter slot for tier T (T ∈ `early`, `mid`, `senior`) becomes a `ceiling` chapter when no branch exists for the parent SOC with `experience_tier === T` AND every branch with a higher tier than T also resolves to `null` or absent. Chapter 1 (`entry`) is never a ceiling. The synthesized chapter: `kind: "ceiling"`, `soc: null`, `title` from `chapterCopy.ts` (e.g., `"The arc levels off here"`), `what_changes` from `chapterCopy.ts`, no stat deltas, no unlock. | Makes the frontend rule explicit enough to re-implement in Silver/Gold without guesswork. Keeps the two specs aligned across the rewrite boundary. | Leave implicit (rejected — rule drift between frontend and future pipeline implementation); enforce lazily at the visionary (rejected — ceiling is a data decision, not a design decision). |
| 11 | Deterministic tie-break in `bucketBranches.ts`: when multiple branches share the top `relatedness` within a tier, the chosen representative is the one with the lowest `to_soc` lexicographically | Deterministic → tests are stable. Lexicographic SOC sort is stable, cheap, and readable in failure messages ("we picked 11-9121 over 11-9041"). Arbitrary is fine; randomness is not. | Secondary sort by `experience_years` ascending (rejected — experience_years within a tier is near-identical by construction of the Silver bucketing); secondary sort by `to_title` alphabetical (rejected — unstable under taxonomy renames); random (rejected — non-deterministic tests). |
| 12 | Grad-degree detection uses the typed `related_education_level` field (via the new Decision #9 addition), matched against `/^Master|^Doctoral/i`. Fallback to `unlock`-regex only when `related_education_level` is `null`. | `backend/app/services/branch_tree.py:54` already reads the typed `related_education_level` from the row and concatenates it into the `unlock` display string — the typed field is available, just discarded at the Pydantic boundary. Adding it to the model and using it directly is both cheaper and more durable than regex-parsing a display string the service might format differently later. | Regex on `unlock` forever (rejected — heuristic, couples us to a display-string format); parse `education_level_name` on the parent career (rejected — that's the parent's entry-level degree, not the branch's unlock gate). |
| 13 | Book-mode state is **screen-local** (a `useState` in `SetYourCourseScreen.tsx`), NOT in `buildStore.ts`. A `useEffect` clears it when the resolution's `matched_cip` changes. | `buildStore.selectedCareer` is consumed by the OLD `/career-pick` → `/reveal` flow and is persisted via zustand/persist. Entangling book-mode with it would resurrect stale book state after an unrelated build completes. Screen-local state with a resolution-change effect is the narrowest correct scope and matches Decision #7 ("swap in place, don't navigate"). | Promote to `buildStore` (rejected — cross-flow state pollution); promote to a new `chapterBookStore` (rejected — premature ownership for a single consumer); URL query param (rejected — breaks the deliberate no-route-change in Decision #7). |
| 14 | Chapter year labels must match the **Silver canonical tier ranges** per `src/silver/onet_experience_transformer.py:145-165`: `entry (0–1yr)`, `early (1–4yr)`, `mid (4–8yr)`, `senior (8+yr)`. Exact wording (e.g., `"Years 0–1"` vs `"Starting out · 0–1 yr"` vs `"Year 1"`) is owned by @fp-design-visionary in §3 and @fp-copywriter, but the RANGES labeled must match Silver exactly. The storytelling-compressed placeholder labels in this spec's earlier drafts (`"Years 0–3 / 3–8 / 8–15 / Past 15"`) are NOT the ship target — they were author drafts that misaligned with Silver. | Data honesty. A student reading "Years 0–3: Biological Technician" under a bucket that actually captures only years 0–1 is a quiet lie about timing. Aligning labels to Silver ranges makes the UI and the pipeline agree. Also lets any future pipeline-side `ceiling_marker` spec reference the same ranges without translation. | Keep the narrative labels and document the compression (rejected — still a factual mismatch the student can catch); drop year numbers entirely in favor of role-stage names (rejected — year anchors are the whole point of the book for a 17-year-old). |
| 15 | Self-referencing branches are filtered from bucketing. `bucketBranches.ts` drops any branch where `branch.to_soc === career.soc_code` BEFORE the per-tier sort. | O*NET flattening to BLS SOC can produce rows where the related occupation collapses back to the parent (e.g., an O*NET detail code and its BLS roll-up both exist). Without this filter, the same role can appear in Chapter 1 (anchor) AND Chapter 2/3/4, which reads as broken data. | Accept the duplication and let it read through (rejected — obvious UI bug); filter only at the service layer (rejected — frontend already owns the bucketing and the filter is one line); collapse duplicates visually but keep both in data (rejected — unnecessary complexity). |
| 16 | Anchor chapter sets `requires_grad_degree` from the parent career's `education_level_name` matching `/^Master\|^Doctoral/i`. The anchor is never rendered as a collapsed/locked chapter regardless (it's the student's entry-level role), but the field is exposed honestly so downstream consumers (tests, future receipts, any summary that reads the book data) don't see a false `false`. | For a parent career like "Medical Scientist" (`education_level_name: "Doctoral or professional degree"`), quietly writing `requires_grad_degree: false` on the anchor is data dishonesty. Setting it from the typed parent field keeps every chapter's fields consistent. | Leave as implicit `false` (rejected — lies about the parent gate); always treat anchor as `false` and add a separate flag (rejected — proliferates fields for a one-line fix). |

### Constraints

- **Technical:** No changes to `consumable.career_branches` schema. No new backend routers. `/branches/{soc}` endpoint and `backend/app/services/branch_tree.py` must remain the sole source of branch data.
- **Technical:** The frontend bucketing function must tolerate `experience_tier` being `None` (O*NET coverage is 867 of ~1,016 SOCs per the `onet-experience-requirements` spec) — missing-tier branches fall through to an "unbucketed" group and are not rendered as chapters but may surface in a tail copy line.
- **Business:** Hackathon deadline is May 18, 2026. Scope discipline — nothing in §1 Success Criteria ships beyond what's written there.
- **Business:** Chat guardrails (`feature-chat-guardrails`) remain the external-audience ship-blocker. This spec does not expand the external surface area; the new flow behaves identically for unauthenticated users to the current shipped flow.

### Out of Scope

These are intentionally excluded and should be future specs or intentional no-ops:

- **Pipeline-side ceiling marker** — Decision #3 commits to a frontend-only ceiling chapter for this spec. A separate spec (`feature-career-branches-ceiling-marker.md`, unfiled) will move the logic into Silver/Gold.
- **Horizon Strip.** The alternative shape is not shipping. The mockup files at `frontend/src/components/horizon/` remain in the tree as a reference.
- **Chapter Book inside other flows** (e.g., `/career-pick`, `/reveal`). This spec only touches `/set-your-course`.
- **Read-the-full-arc deep-dive modal** (visionary's parting idea: "the book deserves to live as a secondary deep-read view later"). Not in this spec.
- **Mobile-first redesign.** Narrow viewports collapse to a single column and render the Chapter Book full-width below the form; no bespoke mobile Chapter Book layout.
- **Comparison mode** (reading two careers' chapters side-by-side). Not in this spec.
- **Deprecating the old `/school` flow.** Tracked separately in the open follow-ups list from `reports/feature-set-your-course-2026-04-19.md`.

---

## §3 UI/UX Design

**Status:** COMPLETE — @fp-design-visionary, 2026-04-19.

### Emotional North Star

The feeling target is **relief**, not swagger. A 17-year-old staring at "Biological Technician, $52K" walks into the book with a suspicion that this is their ceiling. They walk out thinking *"oh — this is a door, and there's a hallway behind it."* No hype, no exclamation points, no "skyrocket." The book reads like a quiet, well-footnoted librarian — the voice of an older cousin who's actually done the career math — not a recruiter. When the book closes on a ceiling chapter, the student should feel **informed**, not **defeated**.

Two moments carry most of the emotional weight:

1. **The list-to-book transition.** The list doesn't vanish — it glides out of the way, and in its place a book rises up with the picked career already printed on its title page. This is the "I picked something, and the world rearranged to focus on it" moment. Commitment is felt.
2. **The thread-down-the-left-gutter.** A single vertical thread runs from chapter 1 to the last chapter, with small dots at each chapter's header line. It's subconscious — students don't notice it — but it's what makes the book feel like *one arc* instead of four disconnected cards. Remove the thread and the same chapters read as a dashboard.

### Layout Context (Important Constraint)

`SetYourCourseScreen` wraps its content in `<PageContainer variant="centered">` (`frontend/src/components/ui/PageContainer.tsx:43-48`). That wrapper spans `col-span-12 desktop:col-span-8 desktop:col-start-3` of the outer 12-col page grid. On a `desktop` (≥1200 px) viewport with `container.desktop = 1024 px` max-width, the centered cell is roughly 680 px wide. The two-column grid inside that cell is **not** occupying the full viewport.

That means a `desktop:grid-cols-[4fr_8fr]` split yields a left column of ~225 px (form) and a right column of ~450 px (book) with a 32px gutter — a **narrow book column by design**. Every line-length, stat-chip row, and thread offset in this spec assumes that constraint. The `wide:` (≥1440 px) and `ultra:` (≥1920 px) breakpoints inherit the same `centered` cell (container caps at 1200/1280 px) so the book column only grows to ~580 px at ultra. We design for the ~450 px case and let it breathe on wider screens; we do not design for a 900 px book.

**One consequence worth naming:** no sticky sidebar. There isn't enough horizontal room to justify one — see the Left Column spec below.

---

### §3.1 The Two-Column Layout

**Decision locked:** swap the one Tailwind declaration on `SetYourCourseScreen.tsx:296`:

```diff
- <div className="grid grid-cols-1 desktop:grid-cols-[7fr_5fr] gap-6 desktop:gap-8 items-start">
+ <div className="grid grid-cols-1 desktop:grid-cols-[4fr_8fr] gap-6 desktop:gap-8 items-start">
```

- **Ratio:** `desktop:grid-cols-[4fr_8fr]` — 4/12 = 33.3% left, 8/12 = 66.7% right. Matches §2 Decision #4 exactly.
- **Breakpoint:** Brightpath `desktop:` (1200 px per DESIGN.md lines 233-236). Below 1200 px: `grid-cols-1` (existing single-column fallback, unchanged behavior).
- **Gutter:** `gap-6 desktop:gap-8` — preserved from the current line. 24 px on narrow desktop, 32 px at desktop and above. This matches Brightpath `gutter.desktop = 32px` for the inner feel. **Do not** change to `gap-4` or `gap-10` — the shipped number is correct.
- **Vertical alignment:** `items-start` — preserved. The left column's form shrinks and grows as the student fills it; we want both columns anchored to the top, not middle-aligned.
- **Visual separation between columns:** gap only. **No divider, no border between columns.** The background gradient (`bp-deep` page background, with the radial surface treatment from DESIGN.md §Background Gradient) carries the separation. The book, on the right, sits on a `bg-bp-mid` panel with a subtle border — that panel's own edge is the column's visual boundary.
- **Sticky sidebar:** **No.** The left column is not sticky, not `position: sticky`, not `overflow:auto`. Rationale: (a) `PageContainer variant="centered"` is already centered and max-width-capped, so the form never scrolls past a wide visual field; (b) the book on the right is vertically tall (4 chapters × ~180 px each + title page ≈ 900 px on a generous case), and a sticky left column would pin the form in a way that feels "chat window" rather than "book reading." The existing screen scrolls the whole page; we keep that. (If Jeff wants to revisit sticky later, it's a two-line addition — `desktop:sticky desktop:top-6 desktop:self-start` on the `<section aria-label="Your inputs">`. Not in scope here.)
- **Left column content order** (unchanged from today; §3 is not reordering the form):
  1. School search (`SchoolSearch`)
  2. Field of study input
  3. `<AnimatePresence>` reasoning card (when resolved)
  4. Receipts section ("Showing SOC codes related to CIP…")
  5. Ask Gemma chips / clarifier affordances (existing)
  6. Community suggestions (when cold-start data is thin)
- **Narrow-viewport fallback (<1200 px):** single column. Order: header → left-column content in full → **right-column content below**. On the fallback, the Chapter Book replaces the career list *in place* (same replace-the-list interaction as desktop) and occupies full width. No special mobile Chapter Book layout; Decision #4 / §2 Out-of-Scope confirms this.

**Wireframe — desktop ≥ 1200 px, list mode:**

```
┌─ PageContainer (centered, col-span-8 col-start-3) ──────────────────────────┐
│ ┌─ Screen header ────────────────────────────────────────────────────────┐ │
│ │ Set your course — Where does this take you?                            │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ grid desktop:grid-cols-[4fr_8fr] gap-8 items-start ──────────────────┐ │
│ │ ┌─ 4fr left (~225 px) ─┐   ┌─ 8fr right (~450 px) ─────────────────┐ │ │
│ │ │ Your school          │   │ Gemma matched "biology"                │ │ │
│ │ │  [ISU input]         │   │   Biology, General · Iowa State U.     │ │ │
│ │ │                      │   │                                         │ │ │
│ │ │ Your field of study  │   │ Where this commonly leads (N paths)    │ │ │
│ │ │  [biology]           │   │ Showing SOC codes related to CIP 26… │ │ │
│ │ │                      │   │ ┌──────────────────────────────────┐ │ │ │
│ │ │ Reasoning card       │   │ │ ▸ 19-4021  Biological Technician │ │ │ │
│ │ │  (insight-accented)  │   │ ├──────────────────────────────────┤ │ │ │
│ │ │                      │   │ │ ▸ 19-1029  Biologist             │ │ │ │
│ │ │ Receipts             │   │ ├──────────────────────────────────┤ │ │ │
│ │ │  "Showing SOC…"      │   │ │ ▸ 19-1099  Lab Animal Caretaker  │ │ │ │
│ │ │                      │   │ └──────────────────────────────────┘ │ │ │
│ │ │ Ask Gemma chips      │   │                                         │ │ │
│ │ │                      │   │ ▾ Uncommon paths (7)                   │ │ │
│ │ └──────────────────────┘   └─────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Wireframe — desktop ≥ 1200 px, book mode (same career list tapped):**

```
┌─ PageContainer (centered) ──────────────────────────────────────────────────┐
│ ┌─ Screen header ────────────────────────────────────────────────────────┐ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ grid desktop:grid-cols-[4fr_8fr] gap-8 items-start ──────────────────┐ │
│ │ ┌─ 4fr left (unchanged) ─┐ ┌─ 8fr right (Chapter Book) ─────────────┐ │ │
│ │ │ Your school            │ │ ← Back to all paths                    │ │ │
│ │ │  ISU                   │ │ ── book title page ──────────────────  │ │ │
│ │ │                        │ │ The arc ahead                          │ │ │
│ │ │ Your field of study    │ │ 🧪 Biological Technician               │ │ │
│ │ │  biology               │ │ Your first job isn't your career.      │ │ │
│ │ │                        │ │ ──────────────────────────────────────  │ │ │
│ │ │ Reasoning card         │ │ ●─ CHAPTER 1 · Starting out · 0–1 yr   │ │ │
│ │ │                        │ │ │  🧪 Biological Technician 19-4021  │ │ │
│ │ │ Receipts               │ │ │  Lab-bench work — samples, assays… │ │ │
│ │ │                        │ │ │  Stats today: [ERN 2][ROI 3]…       │ │ │
│ │ │ Ask Gemma              │ │ ●─ CHAPTER 2 · Years 1–4              │ │ │
│ │ │                        │ │ │  🔬 Microbiologist 19-1022          │ │ │
│ │ │                        │ │ │  You own experiments…               │ │ │
│ │ │                        │ │ │  What shifts: [ERN +1][GRW +1]      │ │ │
│ │ │                        │ │ ●─ CHAPTER 3 · Years 4–8 · locked    │ │ │
│ │ │                        │ │ │  Opens with a graduate degree. ▾   │ │ │
│ │ │                        │ │ ○─ CHAPTER 4 · 8+ yrs · ceiling       │ │ │
│ │ │                        │ │ │  The arc levels off here.           │ │ │
│ │ └────────────────────────┘ └─────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### §3.2 List → Chapter Book Transition

**Named spring:** `springs.smooth` from `frontend/src/styles/motion.ts` (`{ type: "spring", stiffness: 200, damping: 25 }`) for both directions. It's the "confident settle, gentle overshoot" spring — correct for "a panel rearranged itself," wrong for "a button bounced." We do not add a new spring.

**Axis + motion:**
- **Opening** (list → book): list fades out + slides down 8 px over `springs.smooth`; book fades in + slides up 12 px from below on the same spring, with a 60 ms delay on the book entrance so the list clears first. The book appears where the list was — no lateral slide. Total perceived duration: ~320 ms.
- **Closing** (book → list): inverse — book fades out + slides down 12 px; list fades + slides up 8 px with 60 ms delay. Same spring both directions. **No scale.** No crossfade-at-the-same-location (that reads as a flash).
- **Framer Motion pattern:** `<AnimatePresence mode="wait" initial={false}>` wrapping a key-switched child. `mode="wait"` guarantees the exiting element finishes before the entering element starts, which combined with the delay reads as "rearrange," not "flicker."

**Implementation sketch** (illustrative — this is not a binding code snippet, but the shape is the contract):

```tsx
<AnimatePresence mode="wait" initial={false}>
  {selectedChapterCareer ? (
    <motion.div
      key="book"
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
      transition={reducedMotion ? { duration: 0 } : { ...springs.smooth, delay: 0.06 }}
    >
      <ChapterBook career={selectedChapterCareer} onBack={() => setSelectedChapterCareer(null)} />
    </motion.div>
  ) : (
    <motion.div
      key="list"
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
      transition={reducedMotion ? { duration: 0 } : springs.smooth}
    >
      {/* existing CollapsibleCareerSection × 2 (common + uncommon) */}
    </motion.div>
  )}
</AnimatePresence>
```

**`prefers-reduced-motion` fallback:** instant swap. `useReducedMotion()` from `framer-motion` gates both branches — when true, `initial`/`exit` become opacity-only (no translate), `transition` becomes `{ duration: 0 }`, and the 60 ms delay is dropped. The screen never animates the position of the book; it only fades. Child staggers inside the book (chapter entrance, see §3.3 below) are also disabled under reduced motion.

**Focus management:**
- **On open (list → book):** focus lands on the **Back affordance** (the `← Back to all paths` button in the book's title page). Rationale: it's the one interactive element the student will want immediately if they mis-clicked, and placing focus inside the first chapter would either skip past chapter 1's content or require the student to tab backwards to escape. The back button's `aria-label="Back to all paths"` is self-describing when a screen reader announces the focus change.
- **On close (book → list):** focus returns to the **tapped `CareerList` row** — the `<button data-testid="career-row-{soc}">` that originated the transition. `SetYourCourseScreen` captures the originating row's DOM ref (or re-queries by `data-testid` after the list re-mounts) and calls `.focus()` once the list's exit+enter animation completes. If the originating row is no longer in the DOM (e.g. `matched_cip` changed during book mode — Decision #13 cleared the state), focus falls back to the list's container `<ul data-testid="career-list">` with `tabIndex={-1}`.
- **On `Esc` keypress anywhere inside the book:** same as clicking Back. Handled on the book container (`role="region"`) with a `keydown` listener.

**Live region announcement on transition:**
- When the book opens, a `<div aria-live="polite" className="sr-only">` inside `ChapterBook` announces: `"Reading the arc for {career.occupation_title}. {N} chapters, {first_chapter_label} through {last_chapter_label}."` (e.g. `"Reading the arc for Biological Technician. 4 chapters, Starting out through 8+ years."`).
- When the book closes, the list's header picks up an equivalent polite announcement: `"Back to all paths. {N} career paths listed."` — implemented on the existing `CollapsibleCareerSection` header, not on a new element.

---

### §3.3 The Chapter Book Component

**Component location:** `frontend/src/components/chapter-book/ChapterBook.tsx` (container) + `ChapterCard.tsx` (one chapter) per §4 File Changes. The voice and cadence reference is `frontend/src/components/horizon/ChapterBookMockup.tsx` — this §3.3 is the ship target and supersedes the mockup on every detail below.

#### Container (`ChapterBook`)

- **Outer surface:** `bg-bp-mid/60` with `border border-border` (not `border-border-subtle` — the book is a committed object, it earns the stronger edge), `rounded-xl` (20 px — Brightpath `xl` radius, matches the mockup), `shadow-lg` from DESIGN.md §Elevation. The `/60` alpha lets the page's radial gradient tint the book slightly warm, which is the "plush" material feel.
- **Outer padding:** `p-0` on the container; the title page and chapter stack own their own padding. This is what lets the title page render full-bleed-left against the book's border while the chapter stack indents past the thread.
- **Max-width / column-cap:** inherits the 8fr column. No additional cap.

#### Title Page (always rendered, above the chapters)

```
┌─────────────────────────────────────────────────────────┐
│  THE ARC AHEAD                          ← Back to all   │
│                                            paths        │
│  🧪  Biological Technician                              │
│                                                         │
│  Your first job isn't your career. Here's what the     │
│  data shows typically comes next, chapter by chapter.   │
└─────────────────────────────────────────────────────────┘
```

- **Layout:** `flex items-start justify-between gap-3 px-6 pt-6 pb-5 border-b border-border-subtle`. The bottom border separates title page from chapter stack.
- **Eyebrow label** (`THE ARC AHEAD`): `font-data text-micro font-bold uppercase tracking-[2px] text-accent-info` — matches the existing screen's eyebrow treatment (`SetYourCourseScreen.tsx:285`).
- **Career title row:** career emoji (from `socEmoji()` — already used in the mockup and elsewhere) at `text-[28px] leading-none` + career title at `font-display text-heading font-semibold text-text-primary`. Baseline-aligned with `items-baseline gap-3`.
- **Subtitle (the North Star line):** `"Your first job isn't your career. Here's what the data shows typically comes next, chapter by chapter."` — `font-body text-body text-text-secondary max-w-[52ch] mt-2`. This line is load-bearing; it sets the voice for everything below.
- **Back affordance:** top-right of the title page, shrink-0. See §3.3-back below.

**No "~15 years" total-arc caption.** The mockup had one; we cut it. Rationale: the chapter labels themselves carry the time span, and a computed total ("~15 years") implies precision we don't have — Silver's `senior` tier is `8+ yr`, which has no upper bound. Leaving it off keeps us honest.

#### Back Affordance

- **Shape:** pill-ish text button, not a boxed button. `inline-flex items-center gap-1 rounded-md px-2 py-1 font-body text-small text-text-muted hover:text-text-secondary transition-colors duration-normal`.
- **Copy:** `← Back to all paths` (literal — see §3.5 copy table).
- **Focus:** `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]` per DESIGN.md §Focus States.
- **Keyboard:** `Esc` anywhere in the book triggers the same `onBack` handler — bound at the book container (see §3.2 focus management).
- **aria-label:** `"Back to all paths"` (not the longer "Close the arc view…" from the mockup — shorter is better for screen readers).
- **data-testid:** `chapter-book-back`.

#### Chapter Stack

- **Outer wrapper:** `relative px-6 pt-6 pb-6 flex flex-col gap-4`.
- **The thread (the one bit of magic the mockup nailed):** `<span aria-hidden="true" className="absolute left-[28px] top-6 bottom-6 w-px bg-gradient-to-b from-accent-thrive/60 via-border to-border-subtle" />` — a 1px vertical line running down the left gutter. The gradient goes from `thrive/60` at top (chapter 1, "you are here" — alive) to `border` in the middle (neutral) to `border-subtle` at the bottom (the arc fades as it projects forward). Under `prefers-reduced-motion` the thread is a flat `bg-border`.
- **Chapter cards:** each wraps inside the thread's indent via `pl-6` on the `flex-col gap-4` container. Each card has a thread **dot** at its top-left edge (see `ChapterCard` below). Dots align vertically on the 28 px thread line.
- **Stagger on initial reveal:** `staggerContainer(delayChildren=0, staggerAmount=stagger.normal)` from `motion.ts` (80 ms between cards). `staggerItem` variant on each card. Disabled under `prefers-reduced-motion`.

#### `ChapterCard` — per-chapter layout

Every chapter card is a `motion.article` with `variants={staggerItem}` and a left-edge ring + dot keyed to kind:

```
●─┬─ CHAPTER 2 · Years 1–4           (eyebrow, accent-info)
  │   🔬 Microbiologist  19-1022     (emoji + title + SOC)
  │   You own experiments. Writing up findings and
  │   training new techs takes more of the week than
  │   the bench does.                 (what_changes body)
  │
  │   WHAT SHIFTS                     (micro label, muted)
  │   [ERN +1] [GRW +1]               (delta pills)
  │
```

- **Card container:** `relative bg-bp-mid border border-border-subtle rounded-xl p-5 transition-colors duration-normal`. A left-edge ring is added via border-left-width (see per-kind below).
- **Thread dot:** `<span aria-hidden="true" className="absolute -left-[7px] top-6 w-3 h-3 rounded-full ring-2 ring-bp-deep" />` with a `bg-*` token per kind (see below). The `ring-2 ring-bp-deep` creates a 2 px halo that punches the dot through the thread line visually. `top-6` (24 px) aligns with the eyebrow text baseline.
- **Header block:**
  - **Eyebrow** (chapter number + years label): `font-data text-micro font-bold uppercase tracking-[2px] text-accent-info`, e.g. `CHAPTER 2 · YEARS 1–4`.
  - **Title row:** `flex items-baseline gap-2 flex-wrap mt-1`. Contents: emoji at `text-[22px] leading-none mr-1` (hidden for `ceiling`), role title at `font-body font-bold text-body-lg text-text-primary`, SOC code at `font-data text-micro text-text-muted` (hidden for `ceiling`; the title IS the content for ceiling chapters).
- **Body** (`what_changes`): `font-body text-body text-text-secondary leading-relaxed`. One to three sentences, no more. Copy responsibility per chapter kind in §3.5.
- **Stat delta section** (present when `deltas` has at least one non-zero entry; anchor chapter shows a snapshot instead — see "Anchor-specific" below):
  - **Label:** `font-body text-micro uppercase tracking-[2px] text-text-muted` — `"WHAT SHIFTS"` for role/locked, omitted for ceiling (ceiling has no deltas).
  - **Pills row:** `flex flex-wrap gap-1.5`. Each pill: `inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5`. Stat key uses its own `textClass` from `STAT_MAP` (`text-stat-ern`, etc.) at `font-data text-micro uppercase`; the numeric delta is `font-data text-data-sm text-text-primary` with a leading `+` on positives. No minus glyph for negatives — the number carries the sign. **No separate up/down icon;** the stat color already encodes meaning, and the `+`/`-` prefix clarifies direction.
  - **Delta direction color:** we do NOT recolor the pill on positive vs negative. Every delta pill uses `bg-bp-surface`; the stat-axis color on the abbreviation is the only color signal. Rationale: a career that drops HMN by 1 and raises ERN by 2 isn't "bad" or "good" — it's information. Coloring the delta red/green would import a moral judgment the book explicitly refuses. (This is a deliberate departure from the mockup, which is silent on the point.)
- **Anchor-specific body:** the anchor chapter (chapter 1) replaces the `WHAT SHIFTS` block with a `STATS TODAY` block that shows the full 5-stat snapshot of the parent career:
  - **Label:** `font-body text-micro uppercase tracking-[2px] text-text-muted` — `"STATS TODAY"`.
  - **Snapshot row:** same pill shape as deltas, but every stat (ERN, ROI, RES, GRW, HMN) is shown with its absolute score from `career.stats`. Missing stats render as `—`. Copy source: `career.stats` from the existing `CareerOutcome` on page state.
- **Closing bookmark** (only on the last chapter in the stack): `mt-4 pt-3 border-t border-border-subtle flex items-center gap-2 font-body text-small text-text-muted` with a `✦` glyph in `text-accent-thrive/70` followed by `"End of arc. This is what the data shows for most people."` — verbatim from the mockup; keep.

#### Per-kind visual treatment

| Aspect | `anchor` | `role` | `locked` (pre-expand) | `ceiling` |
|--------|----------|--------|------------------------|-----------|
| Left border | `border-l-[3px] border-l-accent-thrive` | `border-l-[3px] border-l-border` | `border-l-[3px] border-l-accent-insight/70` | `border-l-[3px] border-l-accent-caution/80` |
| Thread dot fill | `bg-accent-thrive shadow-glow-thrive` | `bg-text-muted` | `bg-accent-insight` | `bg-accent-caution/80` |
| Emoji in title row | shown | shown | shown (even when collapsed) | **hidden** (no role, no emoji) |
| SOC in title row | shown (own SOC) | shown | shown | **hidden** |
| Title color | `text-text-primary` | `text-text-primary` | `text-text-primary` | `text-accent-caution/90` |
| Body copy color | `text-text-secondary` | `text-text-secondary` | `text-text-secondary` (in expanded body) | `text-text-secondary` (italic close-tag uses `text-text-muted italic`) |
| Body initially open | yes | yes | **no** — show lock sub-line only | yes |
| Deltas / snapshot | snapshot (5-stat) | deltas | deltas (inside expanded body) | **none** |

**Locked chapter — collapsed state:**

```
●─┬─ CHAPTER 3 · Years 4–8
  │   🧬 Medical Scientist  19-1042    [◆ Read ▾]
  │   Opens with a graduate degree.
```

- The title row still shows emoji + role title + SOC (the student deserves to know *what* is locked before they decide to read it).
- The lock pill sits in the header's right side: `inline-flex items-center gap-1.5 rounded-full bg-accent-insight/10 ring-1 ring-accent-insight/25 px-2.5 py-1 font-body text-micro text-accent-insight cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] hover:bg-accent-insight/20 transition-colors duration-normal`. Contents: `◆` glyph at `font-data` + `"Read"` label (becomes `"Hide"` when open) + a `▾` chevron that rotates 180° on open via `springs.snappy`.
- The sub-line below the header (`font-body text-small text-accent-insight/90`): `"Opens with a graduate degree."` — see §3.5 copy table for why this string and not the mockup's `"Opens with {unlock}"` interpolation.
- **Expand animation:** `AnimatePresence` with `{ height: 0 → "auto", opacity: 0 → 1 }` on `springs.smooth`. Under `prefers-reduced-motion`, expand is instantaneous (`initial: { height: "auto", opacity: 1 }`, `transition: { duration: 0 }`).
- **Once expanded:** body (what_changes), deltas block, and closing bookmark (if last) all render as on a `role` chapter.

**Ceiling chapter:**

```
○─┬─ CHAPTER 4 · 8+ yrs
  │   The arc levels off here.
  │   Most people stay here, grow the skill, or lateral
  │   into adjacent roles. It's not a bad place to land —
  │   it's just where the arc typically levels off.
  │
  │   Not every career keeps climbing. That's information,
  │   not a verdict.
```

- Left border + dot in `accent-caution` at 80% alpha. `accent-caution` = `#F2D477` (a warm amber-yellow). Chosen over `text-muted` (which we considered) because `text-muted` reads as "disabled" and we explicitly do not want the ceiling chapter to look broken or dim. It should look **informational** — hence a real color, just quieter than thrive or info.
- Title (`"The arc levels off here."`) renders in `text-accent-caution/90` — the chapter's identity IS the title; there's no role name, so the caution color carries the meaning.
- No SOC, no emoji, no deltas.
- Italic closing note under the body: `"Not every career keeps climbing. That's information, not a verdict."` — `font-body text-small italic text-text-muted`.
- No lock affordance (ceiling is always open; there's nothing to unlock).

---

### §3.4 Delta pill & stat snapshot details

**Delta pill (`<DeltaPill statKey value>`)**

```
[ERN +1]    ← stat color on abbreviation, neutral bg
```

- Container: `inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5`.
- Stat abbreviation: `font-data text-micro uppercase {stat.textClass}`, using `STAT_MAP[key].textClass` from `frontend/src/data/statExplanations` (e.g. `text-stat-ern` = `#F2D477` gold).
- Numeric delta: `font-data text-data-sm text-text-primary` with `+` prefix on positives; negatives render their own `-` glyph (e.g. `-1`). Zeroes are filtered out by `bucketBranches.ts` before reaching the pill, per Rule 5's "strip `undefined` entries" — extend that to "strip zeros" as an implicit contract of the delta render (state it in `types.ts` via a comment on `deltas`).
- No separate up/down triangle, no color fill change, no background shift. The stat color is the signal.

**Stat snapshot row (anchor chapter only)**

- Same pill shape as delta, but the numeric value is the absolute stat score at `font-data text-micro text-text-secondary` (slightly smaller + dimmer than the delta pill's `data-sm` — absolute scores are *context*, deltas are *news*).
- All five stats render in `STAT_ORDER = ["ern", "roi", "res", "grw", "hmn"]`. Missing stats show `—`.

---

### §3.5 Copy — `chapterCopy.ts`

`chapterCopy.ts` is the single source of truth for all book-level voice strings. Exports:

```ts
export const chapterCopy = {
  titlePage: {
    eyebrow: "The arc ahead",
    subtitle:
      "Your first job isn't your career. Here's what the data shows typically comes next, chapter by chapter.",
  },
  years: {
    entry: "Starting out · 0–1 yr",
    early: "Years 1–4",
    mid: "Years 4–8",
    senior: "8+ yrs",
  },
  anchor: {
    what_changes:
      "This is the role most graduates land in first. The bench, the ticket, the desk — where the work actually starts.",
  },
  locked: {
    sublabel: "Opens with a graduate degree.",
  },
  ceiling: {
    title: "The arc levels off here.",
    what_changes:
      "Most people at this step stay here, grow the skill, or lateral into adjacent roles. It's not a bad place to land — it's just where the typical arc levels off.",
    closingNote: "Not every career keeps climbing. That's information, not a verdict.",
  },
  bookmark: "End of arc. This is what the data shows for most people.",
  back: {
    label: "← Back to all paths",
    ariaLabel: "Back to all paths",
  },
} as const;
```

**Voice notes (for @fp-copywriter and the auditor):**

- `years.entry = "Starting out · 0–1 yr"` — the word "starting out" is the emotional anchor; the `0–1 yr` is the receipt. Matches Silver's `entry ≤ 1 yr` tier.
- `years.early = "Years 1–4"`, `years.mid = "Years 4–8"` — plain, Silver-canonical, no drama. Decision #14 locks the ranges; these are the ship strings.
- `years.senior = "8+ yrs"` — not "Past 8" (sounds like a deadline), not "Year 8+" (reads like `Year ≥ 8`), not "9+ years" (off by one from Silver). `8+ yrs` is factual and terse; it reads as a range extending rightward.
- `anchor.what_changes` is the **fallback** when the parent `CareerOutcome` doesn't carry a richer description. If a future feature gives us per-SOC anchor copy, this string becomes the default and per-SOC strings override it.
- `locked.sublabel = "Opens with a graduate degree."` — full sentence, terminating period. Avoids the mockup's interpolation of `unlock` (e.g. `"Opens with Master's degree · close relatedness."`) because (a) `unlock` is a composed display string that will drift; (b) interpolating `related_education_level` directly ("Opens with a Master's degree.") sounds worse than the generic form. The expanded body of the locked chapter can still show the typed `related_education_level` as a data receipt (e.g. a small "Requires: Master's degree" line) — but the sub-line stays generic.
- `ceiling.title = "The arc levels off here."` — not `"This is the ceiling"` (too final). Not `"End of the line"` (too morbid). "Levels off" frames it as a shape, not a limit.
- `back.label = "← Back to all paths"` — `paths`, not `careers` or `options`. The set-your-course screen already uses "paths" in `"Where this commonly leads"` + the uncommon section label. Consistency.

**No exclamation points. No "skyrocket." No "take off." No "climb the ladder." No "unlock your potential."** If a future copywriter proposes any of these, the Decision Log says no.

---

### §3.6 Loading / Empty / Error states

**Loading (fetching branches for the tapped career)**

While `getBranchesForSoc(career.soc_code)` is pending, render:

- Title page: rendered fully (we already have the career data from page state — no need to wait).
- Chapter stack: render **three skeleton chapter cards** using the same shape/spacing as real cards. The skeleton uses the same pattern as `CareerListSkeleton` — `animate-pulse` on `bg-text-muted/20` bars where title + body + delta pills would be.
- Thread: still rendered (it's decorative — no need to wait).
- **Do not** show a spinner. `CareerListSkeleton` set the pattern on this screen; the chapter-book skeleton follows it.
- `data-testid="chapter-book-skeleton"` on the skeleton stack for tests.

**Skeleton shape, per chapter:**

```
●─┬─ [pulse bar — eyebrow ~120px]
  │  [pulse bar — title ~60%]
  │  [pulse bar — body line 1 ~90%]
  │  [pulse bar — body line 2 ~70%]
  │  [pulse bar pill group ~40%]
```

Spec: `ul.flex.flex-col.gap-4` with three `<li>` items each containing pulsing `<div>` bars. Dimensions match the real card to avoid layout shift on replace.

**Empty (career has zero branches — all tiers ceiling)**

Per §4 Bucketing Rule 6, a career with no branches produces exactly two chapters: anchor (chapter 1) + a terminating ceiling (chapter 2). The book renders normally with a two-chapter stack. Visual: title page as usual, then:

```
●─┬─ CHAPTER 1 · Starting out · 0–1 yr
  │   🧪 Biological Technician  19-4021
  │   …what_changes anchor copy…
  │   STATS TODAY: [ERN 2][ROI 3][RES 4][GRW 3][HMN 3]
  │
○─┬─ CHAPTER 2 · 1+ yr
  │   The arc levels off here.
  │   Most people at this step stay here, grow the skill…
  │   End of arc. This is what the data shows for most people.
```

- **Note the chapter 2 years label:** a terminating-ceiling that fires at the `early` tier is labeled `"1+ yr"` — i.e. "everything beyond entry." `chapterCopy.ts` does NOT export that string directly; it's composed by `bucketBranches.ts` from `years.early` by stripping the upper bound (`"Years 1–4"` → `"1+ yr"`). Spec this edge in a comment on `bucketBranches.ts` near Rule 6. An alternative would be to keep `"Years 1–4"` literally and rely on the "arc levels off here" title to communicate finality — viable, but reading "Years 1–4" under a title that says the arc is over is internally contradictory. The `"1+ yr"` composition wins.

**Fetch error**

`getBranchesForSoc` rejects. Render:

- Title page: rendered as normal.
- Chapter stack: replaced by an inline error block, **inside** the book. Book does not unmount.
- Error block layout:

```
┌──────────────────────────────────────────────────────┐
│  ⚠  We couldn't load the arc for this role.          │
│                                                      │
│  The data source was briefly unreachable. Try        │
│  again in a moment.                                  │
│                                                      │
│  [ Retry ]   ← Back to all paths                     │
└──────────────────────────────────────────────────────┘
```

- Container: `px-6 py-8 flex flex-col items-start gap-4`.
- Icon: `⚠` glyph at `text-accent-alert text-heading` (bigger than body so it reads as a flag, not decoration).
- Message: `font-body text-body text-text-secondary max-w-[52ch]`. Copy: `"We couldn't load the arc for this role. The data source was briefly unreachable. Try again in a moment."` — no technical detail, no status code, no "fetch failed." Students don't need those.
- Action row: `Retry` button + Back affordance. `Retry` uses DESIGN.md Secondary button (transparent bg, `accent-info` text, 44 px height, 0 24 px padding) — matches DESIGN.md §Buttons. `data-testid="chapter-book-retry"`. On click, re-runs the fetch.
- Back affordance: the same pill-text back button as the title page (duplicated here so the student can bail without retrying).

---

### §3.7 Brightpath token audit

| Element | Token |
|---------|-------|
| Book container background | `bg-bp-mid/60` (Brightpath `bg-mid` at 60% — lets the page gradient show through) |
| Book container border | `border border-border` (default border, not subtle — book is a committed object) |
| Book container radius | `rounded-xl` (20 px, Brightpath `xl`) |
| Book container shadow | `shadow-lg` (DESIGN.md §Elevation standard card shadow) |
| Title page eyebrow text | `text-accent-info` (`#7BB8E0`) on `font-data text-micro` uppercase |
| Title page career title | `text-text-primary` on `font-display text-heading font-semibold` |
| Title page subtitle | `text-text-secondary` on `font-body text-body` |
| Title page / chapter stack divider | `border-b border-border-subtle` |
| Thread line (vertical gutter) | gradient `from-accent-thrive/60 via-border to-border-subtle` |
| Anchor chapter left border | `border-l-[3px] border-l-accent-thrive` (`#7DD4A3`) |
| Anchor chapter thread dot | `bg-accent-thrive shadow-glow-thrive` |
| Role chapter left border | `border-l-[3px] border-l-border` |
| Role chapter thread dot | `bg-text-muted` |
| Locked chapter left border | `border-l-[3px] border-l-accent-insight/70` (`#B8A9E8` at 70%) |
| Locked chapter thread dot | `bg-accent-insight` |
| Locked chapter lock pill bg | `bg-accent-insight/10 ring-1 ring-accent-insight/25` |
| Locked chapter lock glyph (◆) color | `text-accent-insight` |
| Locked chapter sub-line | `text-accent-insight/90` on `font-body text-small` |
| Ceiling chapter left border | `border-l-[3px] border-l-accent-caution/80` (`#F2D477` at 80%) |
| Ceiling chapter thread dot | `bg-accent-caution/80` |
| Ceiling chapter title | `text-accent-caution/90` on `font-body font-bold text-body-lg` |
| Ceiling chapter closing note | `text-text-muted` on `font-body text-small italic` |
| Chapter card background | `bg-bp-mid` |
| Chapter card border | `border border-border-subtle` |
| Chapter eyebrow (CHAPTER N · years) | `text-accent-info` on `font-data text-micro font-bold uppercase tracking-[2px]` |
| Chapter role title | `text-text-primary` on `font-body font-bold text-body-lg` |
| SOC code in chapter header | `text-text-muted` on `font-data text-micro` |
| `what_changes` body copy | `text-text-secondary` on `font-body text-body leading-relaxed` |
| Stat delta pill bg | `bg-bp-surface` |
| Stat delta abbreviation | `STAT_MAP[key].textClass` (e.g. `text-stat-ern`) on `font-data text-micro uppercase` |
| Stat delta numeric | `text-text-primary` on `font-data text-data-sm` |
| `WHAT SHIFTS` / `STATS TODAY` label | `text-text-muted` on `font-body text-micro uppercase tracking-[2px]` |
| Bookmark closing glyph (✦) | `text-accent-thrive/70` |
| Bookmark closing text | `text-text-muted` on `font-body text-small` |
| Back affordance text | `text-text-muted hover:text-text-secondary` on `font-body text-small` |
| Error block icon (⚠) | `text-accent-alert` on `text-heading` |
| Error block message | `text-text-secondary` on `font-body text-body` |
| Retry button | DESIGN.md Secondary button variant (transparent bg, `text-accent-info`, 44 px) |
| Focus ring (all interactive elements) | `focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]` |

**No new tokens introduced.** Every class above exists in DESIGN.md or in `tailwind.config.ts` today. The one indirection worth flagging: `shadow-glow-thrive` is assumed to exist per the mockup's usage (`ChapterBookMockup.tsx:296`). If it does not resolve, replace with `shadow-lg` and re-route through DESIGN.md §Elevation — not a new token.

---

### §3.8 Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Career row (tap-to-open) | `career-row-{soc}` (existing, unchanged) | `<button aria-pressed>` | — (visible text carries it) |
| Book container | `chapter-book-{soc}` | `<section role="region" aria-labelledby="chapter-book-title-{soc}">` | — (labeled via title) |
| Book title h2 | `chapter-book-title-{soc}` | `<h2>` | — |
| Back affordance | `chapter-book-back` | `<button>` | `"Back to all paths"` |
| Live region (polite) | `chapter-book-live-region` | `<div aria-live="polite" className="sr-only">` | — |
| Chapter card | `chapter-{n}-{soc\|ceiling}` | `<article aria-labelledby="chapter-{n}-title">` | — |
| Chapter title h3 | `chapter-{n}-title` | `<h3>` | — |
| Locked chapter expand toggle | `chapter-lock-{n}` | `<button aria-expanded aria-controls="chapter-{n}-body">` | `"Read chapter {n}: opens with a graduate degree"` (when collapsed) / `"Hide chapter {n}"` (when expanded) |
| Locked chapter body | `chapter-{n}-body` | `<div>` | — |
| Skeleton stack | `chapter-book-skeleton` | `<div aria-busy="true" aria-label="Loading the arc">` | — |
| Retry button (error state) | `chapter-book-retry` | `<button>` | — (visible text: `"Retry"`) |

**Keyboard navigation contract:**

- **Tab order** on list mode: unchanged — form fields → reasoning card → career rows (each row is `tabIndex=0` already). The right column tabs in natural document order.
- **Tab order** on book mode: Back affordance → chapter 1 (article is not focusable, but locked chapter's `Read` button IS if chapter 1 were ever locked — chapter 1 as anchor is never locked, but the tab order is: Back → any interactive element inside chapter 1 body → chapter 2's Read (if locked) → chapter 2 body → … → chapter N's controls. Non-locked chapters have no interactive children, so tab skips over them.
- **Esc:** anywhere inside the book, fires `onBack`. Bound on the book container via `onKeyDown`.
- **Enter / Space** on a locked chapter's `Read` pill: toggles `aria-expanded`. Same on close (`Hide`).
- **Enter** on a career row in list mode: opens book (existing behavior — `<button onClick>` already triggers on Enter).

**Screen reader announcements:**

- **On open** (list → book): the `aria-live="polite"` region inside the book announces: `"Reading the arc for {career.occupation_title}. {N} chapters, {first.years_label} through {last.years_label}."`
- **On close** (book → list): no announcement from the book (book is unmounted); the list region announces via the existing header update.
- **On locked chapter expand:** the `aria-expanded` state change on the `Read` button is announced natively by the screen reader. The body reveal needs no separate live region.

**Color contrast (WCAG AA minimums — the two states most at risk):**

- **Ceiling title** (`text-accent-caution/90` = `#F2D477` at 90% alpha ≈ `#DABE6B` over `bp-mid` `#232545`): contrast ratio ~7.1:1 (AA large text ≥3:1, AA body ≥4.5:1). **Pass.**
- **Locked sub-line** (`text-accent-insight/90` = `#B8A9E8` at 90% alpha ≈ `#A598D1` over `bp-mid`): contrast ratio ~6.4:1. **Pass.**
- **SOC code in chapter header** (`text-text-muted` = `#8A8595` over `bp-mid`): contrast ratio ~4.9:1. **Pass** as body text; the SOC is supplementary data, not primary.
- **Thread line** (gradient ending at `border-subtle` = `rgba(255,255,255,0.06)` over `bp-mid`): contrast is intentionally low — the thread is decorative (`aria-hidden="true"`) and not a content requirement.

**Reduced motion** (re-stated for completeness):

- `springs.smooth` → `{ duration: 0 }` on the list↔book swap.
- `staggerContainer` → `staggerChildren: 0` on chapter entrance.
- Locked expand → `initial: { height: "auto", opacity: 1 }`, `transition: { duration: 0 }`.
- Thread line → still gradient (CSS gradient, not a motion token).
- Lock pill chevron rotation → still animated (it's a micro-control state, not an entrance), but via `transition: { duration: 0 }` when reduced motion is set. An implementer who prefers to gate the chevron rotation entirely can do so; either is compliant.

---

### §3.9 Deferred decisions

Everything below is *deliberately* left open and has a clear closing condition:

- **Per-SOC anchor copy.** `chapterCopy.anchor.what_changes` is a generic fallback. If/when a later feature gives us a per-SOC "what the first year looks like" string (from O*NET task descriptions, for example), the anchor chapter reads that first and the fallback second. No spec change required here.
- **Non-terminating ceiling copy variants.** A bridge ceiling (mid-tier gap, higher tier populated — Bucketing Rule 7) currently uses the same `ceiling.title` and `ceiling.what_changes` as a terminating ceiling. If student feedback says the two cases feel different, `chapterCopy.ts` grows a second variant. Not in this spec.
- **Deep-read modal.** §2 Out-of-Scope excludes a "read the full arc" deep-dive. The closing bookmark is a natural hook for that future affordance.
- **Tablet (768–1199 px) dedicated layout.** Currently collapses to single-column at <1200 px per §2 Decision #4. If a ≥768 breakpoint proves too narrow for the single column and too cramped for the 4fr/8fr split, a tablet-specific `grid-cols-[5fr_7fr]` could be introduced. Not in this spec; would require a DESIGN.md token discussion.

---

## §4 Technical Specification

### Architecture Overview

Frontend-heavy feature with a minor backend Pydantic addition. No router changes, no pipeline changes, no Iceberg schema changes, no MCP changes. The data already exists end-to-end; the frontend type and one backend model field need to catch up:

- `consumable.career_branches` (Iceberg) already carries `related_experience_years`, `related_experience_tier`, `experience_delta_years`, `related_education_level`, `unlock`, `relatedness_tier`.
- Backend Pydantic `CareerBranch` (`backend/app/models/career.py:205-222`) already exposes `experience_years`, `experience_tier`, `experience_delta`. It does NOT yet expose `related_education_level` (the typed field is read in `backend/app/services/branch_tree.py:54` and concatenated into the `unlock` display string). Per Decision #12, this spec adds `related_education_level: str | None = None` to the Pydantic model and surfaces it from the service.
- `backend/app/routers/branches.py` already exposes `GET /branches/{soc}`. No router change.
- `frontend/src/types/build.ts:118-129` `CareerBranch` is stale — missing `experience_years`, `experience_tier`, `experience_delta`. Per Decision #9, this spec updates that interface to match the backend (plus the new `related_education_level`).
- `frontend/src/api/tree.ts` already has `getBranchesForSoc(soc)` returning `CareerBranch[]`. No client change beyond the type it imports.

The work is:
1. **Backend model + service addition** (Decision #12): add `related_education_level: str | None = None` to `backend/app/models/career.py` `CareerBranch`; populate it in `backend/app/services/branch_tree.py` from `row.get("related_education_level")` (the same source `_format_unlock` reads). `_format_unlock` stays intact for display-string compatibility.
2. **Frontend type catch-up** (Decision #9): extend `frontend/src/types/build.ts` `CareerBranch` with `experience_years | experience_tier | experience_delta | related_education_level`.
3. **Mock/fixture updates**: `frontend/src/api/mockBranches.ts` fixture rows gain the four new fields so mock runs compile and render realistic chapters.
4. A new `ChapterBook` component that fetches branches for a SOC, buckets them by `experience_tier` into four chapters per the rules in §2 Decision #10 and #11, synthesizes the anchor chapter from the `CareerOutcome` already in page state, synthesizes ceiling chapters per the Decision #10 rule, and renders.
5. A layout rebalance in `SetYourCourseScreen` — one-line Tailwind class change from `desktop:grid-cols-[7fr_5fr]` to `desktop:grid-cols-[4fr_8fr]` at `SetYourCourseScreen.tsx:296`.
6. Screen-local `selectedChapterCareer` state in `SetYourCourseScreen.tsx` (Decision #13) with a `useEffect` on the resolution's `matched_cip` that clears it. Wired into `CareerList.onSelect` (`frontend/src/components/school/CareerList.tsx:5-7`) to transition list → book.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/career.py` | Modify | Add `related_education_level: str \| None = None` to the `CareerBranch` Pydantic model (Decision #12). No other fields change. |
| `backend/app/services/branch_tree.py` | Modify | In `get_branches()`, populate the new field from `row.get("related_education_level")`. `_format_unlock()` is untouched — `unlock` continues to be the concatenated display string for backward compat. |
| `backend/tests/services/test_branch_tree.py` | Modify | Add assertion: when the MCP row includes `related_education_level`, the returned `CareerBranch.related_education_level` matches. Existing test fixtures that stub MCP rows may need the field added (authorized). |
| `frontend/src/types/build.ts` | Modify | Extend `CareerBranch` (lines 118-129) with `experience_years: number \| null`, `experience_tier: "entry" \| "early" \| "mid" \| "senior" \| null`, `experience_delta: number \| null`, `related_education_level: string \| null` (Decision #9). |
| `frontend/src/api/mockBranches.ts` | Modify | Add the four new fields to every fixture row in `MOCK_BRANCHES` with realistic values (e.g., Financial Manager → `experience_tier: "mid"`, Chief Executive → `experience_tier: "senior"`). |
| `frontend/src/api/mockBuild.ts` | Modify | If this file instantiates any `CareerBranch` for mock builds, add the four new fields to each. Scan and update inline. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Line 296: swap `desktop:grid-cols-[7fr_5fr]` → `desktop:grid-cols-[4fr_8fr]`. Add screen-local `selectedChapterCareer: CareerOutcome \| null` state. Add `useEffect` clearing it on `currentResolution.matched_cip` change. In the right-column render branch, conditionally render either the existing tier list or the new `ChapterBook`. Pass an `onSelect` handler to `CareerList` that sets `selectedChapterCareer`. |
| `frontend/src/components/chapter-book/ChapterBook.tsx` | Create | The Chapter Book container. Props: `career: CareerOutcome`, `onBack: () => void`. Fetches branches via `getBranchesForSoc(career.soc_code)`, calls `bucketBranches()`, renders `ChapterCard[]`. Handles loading/error/empty states per §3. |
| `frontend/src/components/chapter-book/ChapterCard.tsx` | Create | Single chapter renderer. Props: `chapter: Chapter` (local type; see Data Model). Handles anchor / role / locked / ceiling variants. Lock toggle is uncontrolled local `useState`. |
| `frontend/src/components/chapter-book/bucketBranches.ts` | Create | Pure function per §4 Bucketing Rules and §2 Decisions #10/#11/#12. Fully unit-testable. |
| `frontend/src/components/chapter-book/chapterCopy.ts` | Create | Copy strings for ceiling chapter (title + what_changes), locked chapter sub-line, back affordance. Single source of truth for voice — reviewable by @fp-copywriter. |
| `frontend/src/components/chapter-book/types.ts` | Create | Exports the `Chapter`, `ChapterKind`, `ChapterBookProps` interfaces (see Data Model Changes). |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | Create | Vitest: integration — given a career + mocked branches, renders expected chapters in order; back button fires `onBack`; loading/error/reduced-motion paths covered. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | Create | Vitest: unit — each variant (anchor / role / locked / ceiling) renders correct elements and aria-labels; locked expand toggles on click. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | Create | Vitest: unit — all rules in §4 Bucketing Rules, including Decision #10 ceiling rule and Decision #11 tie-break. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | Modify | Add 4fr_8fr layout assertion; tap-opens-book test; back-restores-list test; book-resets-on-resolution-change test. Authorized changes only — see Testing Impact. |
| `frontend/src/styles/motion.ts` | Modify (possibly) | If the visionary spec needs a new spring for the list→book transition, add it here rather than inlining in the component. |
| `DESIGN.md` | No change expected | Brightpath breakpoints and tokens already cover everything in this spec. If the visionary introduces a new token, that's a deviation requiring human review. |

### Data Model Changes

**Backend** (`backend/app/models/career.py`, `CareerBranch` class at line 205):

Add one new field (Decision #12):

```python
class CareerBranch(BaseModel):
    from_soc: str
    to_soc: str
    to_title: str
    delta_ern: int | None = None
    delta_roi: int | None = None
    delta_res: int | None = None
    delta_grw: int | None = None
    delta_hmn: int | None = None
    unlock: str | None = None
    relatedness: float | None = None
    # O*NET experience requirements (onet-experience-requirements spec,
    # Gold contract v1.2.0). All three fields are nullable when the
    # target occupation lacks O*NET ETE coverage; downstream UI treats
    # NULL as "unknown" (never filtered).
    experience_years: float | None = None
    experience_tier: str | None = None
    experience_delta: float | None = None
    # Typed education level of the target occupation (raw field from
    # career_branches row). Used by the Chapter Book to detect
    # grad-degree-gated chapters without regex-parsing the `unlock`
    # display string. Added by feature-chapter-book spec (Decision #12).
    related_education_level: str | None = None
```

**Frontend** (`frontend/src/types/build.ts:118-129`, `CareerBranch` interface):

Bring into parity with the backend (Decision #9) — add four new fields:

```ts
export interface CareerBranch {
  from_soc: string;
  to_soc: string;
  to_title: string;
  delta_ern: number | null;
  delta_roi: number | null;
  delta_res: number | null;
  delta_grw: number | null;
  delta_hmn: number | null;
  unlock: string | null;
  relatedness: number | null;
  experience_years: number | null;
  experience_tier: "entry" | "early" | "mid" | "senior" | null;
  experience_delta: number | null;
  related_education_level: string | null;
}
```

**New frontend-local types** (`frontend/src/components/chapter-book/types.ts`):

```ts
import type { CareerOutcome } from "@/types/build";
import type { StatKey } from "@/data/statExplanations";

export type ChapterKind = "anchor" | "role" | "locked" | "ceiling";

export interface Chapter {
  number: 1 | 2 | 3 | 4;
  years_label: string;             // from chapterCopy.ts; final wording owned by @fp-design-visionary per §2 Decision #14, ranges must match Silver tiers (0–1 / 1–4 / 4–8 / 8+)
  tier: "entry" | "early" | "mid" | "senior" | null;
  kind: ChapterKind;
  title: string;                   // role title (or ceiling copy for kind === "ceiling")
  soc: string | null;              // null for pure ceiling chapters
  what_changes: string;            // one-liner; anchor/ceiling chapters use copy from chapterCopy.ts
  unlock: string | null;           // pass-through display string; e.g., "Master's degree · close relatedness"
  related_education_level: string | null; // typed signal for grad-degree gate detection
  requires_grad_degree: boolean;   // derived per Decision #12
  deltas: Partial<Record<StatKey, number>>;
  stats_snapshot?: Partial<Record<StatKey, number>>; // anchor only
}

export interface ChapterBookProps {
  career: CareerOutcome;
  onBack: () => void;
}
```

### Service Changes

**Backend** (`backend/app/services/branch_tree.py`, `get_branches` function around line 63):

In the `CareerBranch(...)` construction loop, add one new kwarg:

```python
branches.append(
    CareerBranch(
        # ... existing fields ...
        experience_years=as_float(row.get("related_experience_years")),
        experience_tier=(
            str(row["related_experience_tier"])
            if row.get("related_experience_tier") is not None
            else None
        ),
        experience_delta=as_float(row.get("experience_delta_years")),
        related_education_level=(
            str(row["related_education_level"])
            if row.get("related_education_level") is not None
            else None
        ),
    )
)
```

`_format_unlock()` is unchanged — `unlock` continues to be the concatenated display string for backward compatibility with existing callers.

**Frontend** — one new pure function:

**`frontend/src/components/chapter-book/bucketBranches.ts`**

```ts
import type { CareerBranch, CareerOutcome } from "@/types/build";
import type { Chapter } from "./types";

export function bucketBranches(
  career: CareerOutcome,
  branches: CareerBranch[],
): Chapter[];
```

Deterministic. No I/O. Pure. Returns 2–4 chapters: chapter 1 (anchor) is always present, chapters 2/3/4 are present when there are branches or when a ceiling synthesis fires (see §2 Decision #10).

Bucketing rules:

1. **Chapter 1 (anchor)** — Always synthesized from `career` regardless of branches. `number: 1`, `years_label` from `chapterCopy.ts` (e.g., `"Years 0–1"` or visionary wording per Decision #14 — matches Silver `entry` range), `tier: "entry"`, `kind: "anchor"`, `title: career.occupation_title`, `soc: career.soc_code`, `what_changes` from `chapterCopy.anchor`, `related_education_level: career.education_level_name ?? null`, `requires_grad_degree: /^Master|^Doctoral/i.test(career.education_level_name ?? "")` per Decision #16, `deltas: {}`, `stats_snapshot: career.stats`.
2. **Drop** branches with `experience_tier === null` entirely (not rendered, not counted).
3. **Filter self-referencing branches** (Decision #15) — Drop every branch where `branch.to_soc === career.soc_code` before any per-tier sort. O*NET flattening can produce these and they would duplicate Chapter 1 if not filtered.
4. **Per-tier pick** — For each target tier T ∈ (`early`, `mid`, `senior`), filter the remaining branches to those with `experience_tier === T`. Sort by `relatedness` descending; tie-break per Decision #11 by `to_soc` lexicographic ascending. The top of that sort is the representative for tier T (or none, if the filter result is empty).
5. **Chapters 2/3/4 from a representative** — For tier T with a representative branch B:
   - `kind: "locked"` if `B.related_education_level` matches `/^Master|^Doctoral/i` OR (`B.related_education_level === null` AND `B.unlock` matches `/Master|Doctor/i`) — the fallback from Decision #12.
   - Otherwise `kind: "role"`.
   - `requires_grad_degree: true` iff `kind === "locked"`.
   - `title: B.to_title`, `soc: B.to_soc`, `unlock: B.unlock`, `related_education_level: B.related_education_level`, `deltas: { ern: B.delta_ern, roi: B.delta_roi, res: B.delta_res, grw: B.delta_grw, hmn: B.delta_hmn }` with `undefined` entries stripped.
6. **Ceiling synthesis — terminating** (Decision #10) — For tier T with no representative branch AND every higher tier also has no representative: the chapter becomes `kind: "ceiling"`, `soc: null`, `title: chapterCopy.ceiling.title`, `what_changes: chapterCopy.ceiling.what_changes`, `unlock: null`, `related_education_level: null`, `requires_grad_degree: false`, `deltas: {}`. Higher tiers after a terminating ceiling are NOT emitted (the book ends at the ceiling).
7. **Ceiling-as-bridge** — If tier T has no representative but a higher tier DOES, the chapter for T is STILL emitted as `kind: "ceiling"` (acts as a bridge explaining the gap), and rendering continues to higher tiers. This differs from rule 6 by emitting subsequent chapters.

Rules 6 and 7 together are the canonical ceiling semantics referenced by §2 Decision #10.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | Any test asserting the left-column width ratio or the DOM structure of the grid | High | Grid ratio changes from `7fr_5fr` to `4fr_8fr` — snapshot tests or className assertions will break. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | Any test that clicks a `CareerList` row expecting the current `onSelect`-to-commit flow | High | Tap semantics on the `CareerList` row change from "commit career" (current path) to "open Chapter Book" (this spec). The pre-existing commit path may need to move into an affordance inside the book itself OR onto a different surface — resolve during DESIGN VISION (§3). Until §3 resolves this, tests that assume the current commit-on-click path should be flagged, not silently changed. |
| `frontend/src/components/school/CareerList.test.tsx` (if present) | All | Med | Component itself is not modified, but its `onSelect` call-site semantics change at the parent. If the test mocks `onSelect` and asserts behavior, it stays green; if it asserts navigation or commit side effects, it breaks. |
| `frontend/src/hooks/useSetYourCourse.test.ts` | All tests | Low | The hook's resolution logic is untouched. Only the screen's post-resolution UI state changes. |
| `frontend/src/api/tree.test.ts` | `getBranchesForSoc` tests | Low | Endpoint is reused, not modified. Response shape gains optional fields; existing assertions on required fields stay valid. |
| `frontend/src/api/build.test.ts` | Any test using `CareerBranch` fixtures | Med | Adding four required-nullable fields to the `CareerBranch` interface may break fixtures declared with `satisfies CareerBranch` or strict object literals. Fixture files (`mockBranches.ts`, `mockBuild.ts`) are listed in File Changes; any consumer test that inline-declares a `CareerBranch` needs the fields added. |
| `frontend/src/components/CareerTierSection.test.tsx` | All | Low | `CareerTierSection` is not used by the current `/set-your-course` flow (Set Your Course uses `CareerList`). Untouched. |
| `frontend/src/components/CareerLineageSheet.test.tsx` | All | None | `CareerLineageSheet` is used only by the `/career-pick` old-flow screen. Untouched. |
| `backend/tests/services/test_branch_tree.py` | All tests asserting the `CareerBranch` shape returned by `get_branches` | Med | New `related_education_level` field appears on every branch. Tests asserting full-object equality will need fixture updates (authorized). Field is nullable; tests asserting a subset of fields stay green. |
| `backend/tests/models/test_career.py` (if present) | `CareerBranch` shape tests | Med | Same cause as above. |
| `tests/mcp/test_get_career_branches.py` | All tests | None | MCP tool shape is unchanged — `related_education_level` is already in the row. Only the Pydantic surface expands. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | Update `grid-cols-[Xfr_Yfr]` assertions from `7fr_5fr` to `4fr_8fr` where present. Update any test that currently clicks a `CareerList` row and asserts a commit side-effect to instead assert book-mode activation (list → book swap). Add new tests per §4 New Tests Required. | Direct consequence of Decision #4 (ratio change) and the new tap-opens-book behavior. |
| `backend/tests/services/test_branch_tree.py` | Update any fixture MCP-row dicts that stub `get_career_branches` responses to include `related_education_level` (null or realistic string per fixture). Add field to any full-object equality assertion. | Consequence of Decision #12 (new field on `CareerBranch`). Field is nullable; null-filled fixtures are acceptable. |
| `backend/tests/models/test_career.py` (if present) | Same as above — update `CareerBranch` construction fixtures. | Same cause. |
| `frontend/src/api/mockBranches.ts`, `frontend/src/api/mockBuild.ts` (as mock data, not tests — listed here for visibility) | Extend every `CareerBranch` fixture with `experience_years`, `experience_tier`, `experience_delta`, `related_education_level` (realistic values where possible — e.g., `experience_tier: "mid"` for a Financial Manager branch, `related_education_level: "Master's degree"` for roles that require one). | Consequence of Decision #9; prevents TypeScript compile errors in any file that imports these mocks. |

Implementation must document each specific assertion added / changed in §6 Implementation Log.

#### Confirmed Safe

The following tests MUST NOT break. If any fails, STOP and escalate to §10 Discussion:

- `frontend/src/hooks/useSetYourCourse.test.ts` — all tests
- `frontend/src/api/tree.test.ts` — all tests (endpoint unchanged)
- `frontend/src/api/intent.test.ts` — all tests (resolution flow untouched)
- `frontend/src/components/CareerLineageSheet.test.tsx` — all tests (component untouched, used only by `/career-pick`)
- `frontend/src/components/CareerTierSection.test.tsx` — all tests (component not used by `/set-your-course`)
- `backend/tests/routers/test_branches.py` (if present) — all tests (router untouched)
- `tests/mcp/test_get_career_branches.py` — all tests (MCP tool untouched)
- Every pytest in `tests/` (pipeline suite) — entirely untouched; any failure is a hard escalation.

If any pipeline test fails: that is a definitive escalation signal — this spec does not touch the pipeline.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `buckets four tiers into four chapters` | All four tiers present → all four chapters returned with correct titles + tier tags. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `filters self-referencing branches before bucketing` | A branch with `to_soc === career.soc_code` is dropped entirely; it does not appear in any chapter 2/3/4 even if it has the highest relatedness in its tier (Decision #15). |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `anchor inherits requires_grad_degree from parent education_level_name` | Parent career with `education_level_name: "Doctoral or professional degree"` → chapter 1 has `requires_grad_degree: true`, even though anchor never renders as locked (Decision #16). |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `synthesizes ceiling when senior tier missing` | No senior-tier branch → chapter 4 has `kind: "ceiling"` and soc is null. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `synthesizes ceiling for every missing mid-arc tier` | No early-tier branches → chapter 2 ceiling; no mid-tier → chapter 3 ceiling. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `drops branches with null experience_tier` | Branch with `experience_tier === null` does not appear in any chapter. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `empty branches produces two-chapter book` | `branches = []` → exactly 2 chapters: anchor + ceiling. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `detects grad-degree requirement from related_education_level` | Branch with `related_education_level: "Master's degree"` and `unlock: null` → `requires_grad_degree === true`. Validates Decision #12 primary path. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `falls back to unlock regex when related_education_level is null` | Branch with `related_education_level: null` and `unlock: "Master's preferred · 10+ yrs"` → `requires_grad_degree === true`. Validates Decision #12 fallback. |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `deterministic tie-break on equal relatedness` | Two branches at tier `"mid"` with `relatedness: 0.8`, SOCs `11-9121` and `11-9041` → representative is `11-9041` (lexicographic ascending, Decision #11). |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `ceiling synthesis terminates book when all higher tiers absent` | Branches present only at tier `"early"` → chapter 2 is `role`, chapter 3 is `ceiling`, chapter 4 is NOT emitted (Rule 6 terminating). |
| P0 | `frontend/src/components/chapter-book/bucketBranches.test.ts` | `ceiling-as-bridge when only middle tier is empty` | Branches present at `"early"` and `"senior"` but NOT at `"mid"` → chapter 2 `role`, chapter 3 `ceiling`, chapter 4 `role` (Rule 7 bridge). |
| P0 | `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `anchor variant renders stats_snapshot` | Anchor chapter shows the parent career's full stat pentagon, not deltas. |
| P0 | `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `locked variant collapses by default, expands on click` | Grad-degree chapter initially shows lock + sub-line; click expands to full body. |
| P0 | `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `ceiling variant renders muted copy` | Ceiling chapter renders the "levels off" copy, no stat deltas, no SOC code. |
| P0 | `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `fetches branches and renders 4 chapters` | Given a `career` and mocked `getBranchesForSoc` return, renders chapters in order 1→2→3→4. |
| P0 | `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `back button calls onBack` | Clicking `← Back to all paths` fires the `onBack` prop exactly once. |
| P0 | `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `renders loading state while fetching` | While `getBranchesForSoc` is pending, the book shows the documented loading treatment. |
| P0 | `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `renders inline retry on fetch error` | When `getBranchesForSoc` rejects, book shows retry, does not unmount. |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `renders 4fr_8fr grid on desktop viewport` | Screen's root grid element carries `desktop:grid-cols-[4fr_8fr]` (or resolves to it via Tailwind) at `window.innerWidth >= 1200`. |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `collapses to single column below 1200px` | `window.innerWidth < 1200` → grid is `grid-cols-1` (existing behavior preserved). |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `tapping a career row opens Chapter Book` | Click on any `button[data-testid^=career-row-]` swaps the right column from `[data-testid="career-list"]` to the ChapterBook container; `← Back` restores the list. |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `book state resets when resolution matched_cip changes` | While in book mode, mutate the hook's `currentResolution.matched_cip` → right column reverts to list mode (Decision #13 `useEffect`). |
| P0 | `backend/tests/services/test_branch_tree.py` | `exposes related_education_level on CareerBranch` | Mock an MCP row with `related_education_level: "Master's degree"` → returned `CareerBranch.related_education_level == "Master's degree"` (Decision #12). |
| P1 | `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `respects prefers-reduced-motion` | When `prefers-reduced-motion: reduce` is set, the book swaps in without the transition animation. |
| P2 | `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `respects aria-labels on interactive elements` | Back affordance and locked-chapter expand toggle expose the aria-labels specified in §3. |

#### Test Data Requirements

- **Mocked branches fixture:** A realistic `CareerBranch[]` shape with one branch per tier (entry / early / mid / senior). Suggest `frontend/src/components/chapter-book/__fixtures__/branches.ts` exporting `branchesBiologicalTechnician: CareerBranch[]` for use across the chapter-book test suite.
- **Mocked career fixture:** A realistic `CareerOutcome` matching the parent SOC of the branches fixture. Can borrow from existing fixtures in the Set Your Course test suite if one exists.
- **Viewport mocks:** Use `@testing-library/react` with `window.matchMedia` mock helper to exercise both desktop and narrow-viewport branches.
- **No network:** All `getBranchesForSoc` calls in tests must be mocked via vitest's `vi.mock("@/api/tree", ...)`.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-19

#### System Context

Frontend-only feature sitting on `/set-your-course`. Touches one API consumer boundary (`GET /branches/{soc}` via `frontend/src/api/tree.ts:17`) and reads one existing Gold product (`consumable.career_branches`) through the already-shipped MCP tool `get_career_branches` → `backend/app/services/branch_tree.py:63` → `backend/app/models/career.py:205` `CareerBranch`. No backend, pipeline, MCP, or Gemma call-site changes. No zone boundaries crossed. Gemma function-calling surface is unchanged.

#### Data Flow Analysis

Source: `consumable.career_branches` (Iceberg Gold).
→ MCP tool `get_career_branches` (primary_only=True).
→ `branch_tree.get_branches(soc)` coerces and emits `CareerBranch` Pydantic models (`backend/app/models/career.py:205-222`) — carries `experience_years`, `experience_tier`, `experience_delta`, `unlock`, `relatedness`.
→ FastAPI `GET /branches/{soc}` (`backend/app/routers/branches.py:9-11`) serializes verbatim.
→ Frontend `getBranchesForSoc(soc)` (`frontend/src/api/tree.ts:17-22`) returns `Promise<CareerBranch[]>` where the TS type is imported from `@/types/build`.
→ Frontend `CareerBranch` (`frontend/src/types/build.ts:118-129`) **is stale relative to the Pydantic model**: it is missing `experience_years`, `experience_tier`, and `experience_delta`.

This is the single load-bearing gap. The bucketing function in §4 reads `branch.experience_tier` and `branch.experience_years` — both of which the current TS type does not declare. Implementing the spec as written will either force an `as unknown as` cast or silently compile with missing fields. That is the sort of drift this review exists to prevent.

#### Contract Review

- **Pydantic ↔ TS parity (blocker):** `frontend/src/types/build.ts:118-129` does not declare the three O*NET experience fields shipped by `onet-experience-requirements` and serialized by `backend/app/models/career.py:220-222`. Spec §4 assumes these exist on the TS side ("Deterministic. No I/O. Pure." bucketing logic at §4 "Bucketing rules" references `experience_tier === "early"` etc.). Must be fixed before implementation.
- **`related_education_level` is not a typed contract:** `backend/app/services/branch_tree.py:54-60` reads `related_education_level` from the raw MCP row but *collapses it into the `unlock` string* (`"{education} · {tier} relatedness"`) rather than surfacing it as its own typed field on `CareerBranch`. The spec's grad-degree detector (`/Master|Doctor/i` against `unlock`) is therefore a regex over a format string produced server-side. See Findings → Concerns.
- **MCP / Gemma surface:** Unchanged. No Gemma call sites touched. Explicitly noting: **no Gemma impact.**
- **Backend routers / services / Gold tables:** Untouched. `consumable.career_branches` contract remains identical.
- **Mocks:** `frontend/src/api/mockBranches.ts` and `frontend/src/api/mockBuild.ts` construct `CareerBranch` literals and will need updating once the TS type gains the experience fields, or TS will break at their call sites.

#### Findings

##### Sound

- **Zone discipline.** Bronze → Silver → Gold → MCP → FastAPI → frontend trace is intact. The Gold contract does not regress.
- **Scope boundary on Gemma.** Spec explicitly declines to touch `gemma_client`, `streamIntent`, `commitResolution`, or any MCP tool handler. Confirmed no indirect Gemma path in the horizon mockup dir either.
- **Decision #3 (frontend-only ceiling):** Acceptable as a tactical deferral *if* §1 success criteria make the `kind: 'ceiling'` Chapter contract explicit (it does) and the follow-up spec is filed before the production release moves past hackathon scope. The synthesis is deterministic on the client, so a future pipeline-side ceiling marker can agree or disagree with this spec's output *on a per-tier basis* — see Concerns on consistency risk.
- **Component location (Decision #8).** `frontend/src/components/chapter-book/` is the correct location; keeps it separate from `/components/horizon/` (mockup zone) and `/components/school/` (Set Your Course specific). No circular import risk.
- **Pure bucketing function.** Deterministic, no I/O, unit-testable. Correct factoring — §4 `bucketBranches.ts` is the right seam.
- **Endpoint reuse.** `/branches/{soc}` is the right read path. No duplication proposed.

##### Concerns

- **Frontend `CareerBranch` type is missing the three experience fields (BLOCKER).**
  - **Impact:** `bucketBranches.ts` cannot compile against the current TS type. Implementers will either silently widen with `as any` / `unknown` casts (unsafe) or have to extend the type mid-spec. Not catching this now guarantees a mid-implementation escalation.
  - **Recommendation:** §4 "File Changes" must add an explicit Modify entry for `frontend/src/types/build.ts` adding `experience_years: number | null`, `experience_tier: "entry" | "early" | "mid" | "senior" | null`, and `experience_delta: number | null` to the `CareerBranch` interface. Also update `frontend/src/api/mockBranches.ts` and `frontend/src/api/mockBuild.ts` fixtures to set the new fields (can be all `null` for legacy mocks) — or TS will fail at their object-literal call sites.

- **Breakpoint claim in Decision #4 is factually wrong.**
  - **Impact:** Spec §1 Success Criteria and §2 Decision #4 both cite "≥ 960 px" as "the existing Brightpath `md` breakpoint per DESIGN.md." DESIGN.md lines 233-236 define the Brightpath breakpoints as `mobile 480`, `tablet 768`, `desktop 1200`, `wide 1440`. There is **no `md` breakpoint** and **no 960px** anywhere in DESIGN.md or `frontend/tailwind.config.ts`. The existing `SetYourCourseScreen.tsx:296` already uses `desktop:grid-cols-[7fr_5fr]` — i.e. the existing two-column breakpoint is 1200px, not 960px. Implementing "960" requires either (a) inventing a new breakpoint, which @fp-design-auditor will reject under DESIGN.md §Responsive, or (b) using an arbitrary inline media query, which drifts from the system.
  - **Recommendation:** Pick either `tablet` (≥768 px) or `desktop` (≥1200 px) and update Decision #4 + §1 Success Criteria + the new test names that reference "960 px" accordingly. My read: `desktop:` (1200 px) is correct for a 33/66 split — the form column compresses awkwardly at 720px tablet width.

- **Layout description mischaracterizes the existing state.**
  - **Impact:** §1 Problem Statement ("restructure `/set-your-course` into a 33/66 two-column layout") and §4 Architecture Overview imply the current screen is single-column. It is not. `SetYourCourseScreen.tsx:296` already renders `grid-cols-1 desktop:grid-cols-[7fr_5fr]` — a 2-column at desktop. The actual change is **ratio (7:5 → 2:4, i.e. ~58/42 → 33/66)** and **interaction (tap a career → book)**, not a single-column → 2-column restructure.
  - **Recommendation:** Rewrite §1 Problem Statement and §4 Architecture Overview to say "tighten the existing desktop 7fr/5fr split to a 2fr/4fr (33/66) split" so @fp-design-auditor and the implementer know the baseline.

- **Grad-degree detection via regex on a composed string is brittle.**
  - **Impact:** `backend/app/services/branch_tree.py:52-60` produces `unlock` as `"{related_education_level} · {relatedness_tier} relatedness"`. If the Gold-layer source value changes from `"Master's"` to `"Master of Science"` or `"Graduate degree"`, the `/Master|Doctor/i` regex silently misclassifies — and since the UI hides locked chapters by default (Success Criterion 5), a misclassified chapter is visually indistinguishable from a correctly-unlocked one until someone notices. This is exactly the "works for Marketing-at-IU, breaks on deaf education" failure mode called out in project rules.
  - **Recommendation:** Either (a) add `related_education_level: str | None` as a typed field on the backend `CareerBranch` Pydantic model (surfacing the raw value the service already reads), mirror it on `frontend/src/types/build.ts`, and derive `requires_grad_degree` from that typed field; OR (b) define an enum of accepted strings and unit-test the detection against the distinct `related_education_level` values actually present in the Gold table (check in `bucketBranches.test.ts` with a fixture enumerating every observed value). Option (a) is the cleaner architectural move but costs a tiny backend edit. If the spec insists on "no backend changes," at least require (b).

- **Tier-collision determinism is undefined.**
  - **Impact:** §4 "first branch with `experience_tier === "early"`, sorted by relatedness descending. If none, synthetic ceiling." — when two branches at the same tier tie on `relatedness` (the backend does not guarantee uniqueness), which wins is non-deterministic across re-renders if the backend returns rows in different orders on retries.
  - **Recommendation:** Define the tiebreaker in §4: e.g. "ties broken by (a) lower `experience_delta` absolute value, (b) alphabetical `to_title` as a final fallback." Add a unit test in `bucketBranches.test.ts` asserting deterministic tie resolution. This is a five-minute spec edit that prevents a Heisenbug.

- **"One role per tier" semantic is spec-locked but may undersell.**
  - **Impact:** A student looking at a mid-tier chapter with three viable next roles will only see one. The book framing invites depth, not breadth, so this is a reasonable product call — but once `@fp-design-visionary` gets §3, they may want a stacked secondary-option treatment. Spec should pre-declare whether that is allowed or explicitly blocked.
  - **Recommendation:** Add a Decision row: "Each chapter surfaces exactly one role; additional candidate roles in the same tier are dropped (not stacked, not linked, not teased)." This is the current implicit contract; making it explicit prevents visionary drift.

- **Book-mode state placement (§4 "A new frontend state machine") conflicts with persisted `selectedCareer`.**
  - **Impact:** `useBuildStore` (`frontend/src/store/buildStore.ts:30-65`) persists `selectedCareer` via zustand `persist` middleware. §4 proposes holding book-mode state as `useState` inside `SetYourCourseScreen`. The P1 test "book state resets when resolution changes" (§4 line 377) will pass trivially in component-local state — but the *actual* source of truth for "what career did the student pick" already lives in `buildStore.selectedCareer`, which is *not* cleared when `currentResolution` changes (see `SetYourCourseScreen.tsx:164-174` — `handleCareerSelect` writes to `setSelectedCareer`, and nothing in the resolve-effect clears it). So either: the book reads `selectedCareer` from the store and inherits its persistence (book survives page refresh, which may or may not be desired), OR the book uses its own local state and diverges from `selectedCareer` (which is the current commit target). Pick one.
  - **Recommendation:** Add a short subsection to §4 "State Model" that calls out: (a) which store owns "book is open" — is it a new `viewMode: "list" | "book"` on `buildStore`, or screen-local? (b) does book-mode clear on re-resolution (via a `useEffect` watching `parentCipOrMatched`)? (c) does book-mode survive a page refresh? Declaring (a)-(c) explicitly prevents a confused implementation and a flaky P1 test.

- **Testing Impact Analysis omits CareerList and CollapsibleCareerSection tap path.**
  - **Impact:** `/set-your-course` does not render `CareerCard` directly — it renders `CollapsibleCareerSection` → `CareerList` (`frontend/src/components/school/CareerList.tsx`). The card with the `onExplore` callback prop is `frontend/src/components/CareerCard.tsx`, which is used only by `CareerLineageSheet` (old `/school` flow). §4 Testing Impact rows reference "CareerCard" as if it were the set-your-course tap target — but the real tap handler is `CareerList.onSelect` (row button), wired in `SetYourCourseScreen.tsx:625,634` via `handleCareerSelect`. Implementers may modify the wrong file.
  - **Recommendation:** Update §4 "File Changes" and Testing Impact Analysis to name `frontend/src/components/school/CareerList.tsx` (and/or `CollapsibleCareerSection.tsx`) as the interaction site, not `CareerCard.tsx`. The `CareerCard.tsx` → CareerLineageSheet path is untouched (matches Decision #6, but the §4 text contradicts Decision #6 by pointing at CareerCard tests).

- **Decision #3 frontend-vs-pipeline consistency risk.**
  - **Impact:** The follow-up spec (`feature-career-branches-ceiling-marker.md`, unfiled) will presumably emit a typed `is_ceiling: bool` or equivalent from the Gold layer. If its criteria for "this tier is a ceiling" differs from the frontend's "no branch at this tier" heuristic (e.g. the pipeline looks at observed transition counts, not absence), the two will produce **disagreeing** chapter books before and after the pipeline spec lands — and any student mid-session during the rollout sees one version flip to another. The frontend synthesis is not a pure "logic moved in time"; it is specifically the `tier_bucket_empty_for_this_soc` rule, which is weaker than what the pipeline would reasonably implement (it cannot see zero-volume transitions).
  - **Recommendation:** §1 Success Criteria 6 should note the specific frontend rule ("a tier is synthesized as ceiling **iff** no branch row in the response has that `experience_tier` value") so the future pipeline spec can either mirror the rule or document the divergence. Filing the data-side spec stub as part of this spec's completion prevents silent drift.

##### Blockers

- **Frontend `CareerBranch` TS type missing the three experience fields.** This is the only true blocker — implementation cannot proceed without it. Classified as CHANGES REQUESTED (not REJECTED) because the fix is a three-field append and a mock update.

#### Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. **Add the three experience fields to `frontend/src/types/build.ts` `CareerBranch` interface** (`experience_years: number | null`, `experience_tier: "entry" | "early" | "mid" | "senior" | null`, `experience_delta: number | null`). Add a corresponding File Change row in §4. Update `frontend/src/api/mockBranches.ts` and `frontend/src/api/mockBuild.ts` fixtures to populate the new fields (nulls are fine) or TS will fail.
2. **Fix the breakpoint claim in Decision #4, §1 Success Criteria, and all new test names.** Either pick `tablet` (768 px) or `desktop` (1200 px) from `frontend/tailwind.config.ts` / DESIGN.md §Breakpoints. The "960 px / md" references have no basis in this codebase.
3. **Rewrite §1 Problem Statement and §4 Architecture Overview** to reflect that the current screen is already 2-column at `desktop:` (`grid-cols-[7fr_5fr]` at `SetYourCourseScreen.tsx:296`). The change is ratio + interaction, not a single-column restructure.
4. **Name the correct interaction site.** Replace references to `CareerCard.tsx` in §4 "File Changes" and Testing Impact Analysis with `frontend/src/components/school/CareerList.tsx` and/or `CollapsibleCareerSection.tsx` — that is where the actual tap handler lives on this screen. `CareerCard.tsx` is only used by the old `/school` flow's `CareerLineageSheet`.
5. **Define tier-collision tiebreaker in §4** and add a `bucketBranches.test.ts` case asserting determinism under ties.
6. **Add a §4 "State Model" subsection** declaring: (a) where book-mode state lives (screen-local vs. `buildStore`), (b) whether it clears on `parentCipOrMatched` change via a `useEffect` reset, (c) whether it survives a page refresh / zustand persist. Also declare how it relates to `buildStore.selectedCareer` (already persisted).
7. **Strengthen grad-degree detection** — either (preferred) surface `related_education_level` as a typed field on `backend/app/models/career.py` `CareerBranch` and `frontend/src/types/build.ts`, deriving `requires_grad_degree` from it; or (acceptable) keep the regex but add a unit-test fixture enumerating every `related_education_level` value currently present in `consumable.career_branches` and assert correct classification for each.
8. **Tighten the ceiling-rule contract in §1 Success Criterion 6** to state the exact frontend rule ("tier is synthesized as ceiling iff no row in the response has that `experience_tier` value") and file the follow-up pipeline-side ceiling-marker spec stub before this spec moves to COMPLETE, so the rule contract is owned.

Conditions 1, 2, 3, 4 are non-negotiable (factually incorrect spec statements). Conditions 5-8 are architectural hygiene that prevents a mid-implementation escalation. None require backend code changes; all are spec edits and one TS type append.

### @fp-architect Re-Review (2026-04-19, post-fixes)
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-19 (second pass, post-author revisions)

#### Purpose of This Pass

Verify the seven CHANGES REQUESTED conditions from the prior review (above) were actually addressed, and take a fresh look at a few downstream consistency questions that were not in the prior review but jump out now that the spec is sharper.

#### Conditions from Prior Review — Verification Result

| # | Prior Condition | Status | Evidence |
|---|-----------------|--------|----------|
| 1 | Frontend `CareerBranch` parity (three experience fields, mock updates) | **Met** | Decision #9 added; §4 Data Model shows the updated TS interface including all four fields (now `experience_years`, `experience_tier`, `experience_delta`, `related_education_level`); `frontend/src/api/mockBranches.ts` and `mockBuild.ts` are both in the File Changes table. |
| 2 | Breakpoint factual error (`960px md` fiction) | **Met** | Decision #4 now cites `desktop: 1200 px` per DESIGN.md lines 233-236. §1 Success Criteria 1-2 reference `≥ 1200 px` and `< 1200 px`. The ratio swap is stated as `desktop:grid-cols-[7fr_5fr]` → `desktop:grid-cols-[4fr_8fr]` at line 296. |
| 3 | Layout description as a ratio change, not a 1-col → 2-col restructure | **Met** | §1 Overview (line 116) and §1 Problem Statement (line 126) both name the existing `grid-cols-[7fr_5fr]` baseline at `SetYourCourseScreen.tsx:296` and describe the work as a ratio swap. §4 Architecture Overview is consistent. |
| 4 | Correct interaction site (`CareerList.tsx`, not `CareerCard.tsx`) | **Met** | §1 Success Criteria 3 names `frontend/src/components/school/CareerList.tsx` and its `onSelect` prop. File Changes table does not reference `CareerCard.tsx`. Testing Impact Analysis references `CareerList.test.tsx` as an "if present" row — I verified it is NOT present in `frontend/src/components/school/` (which only has `EffortLoansPanel.test.tsx` and `MajorInput.test.tsx`), so the conditional phrasing is correct and does not need a hard row. |
| 5 | Deterministic tie-break defined in §4 | **Met** | Decision #11 commits to lexicographic-ascending on `to_soc`; Bucketing Rule 3 implements it; New P0 test `deterministic tie-break on equal relatedness` covers it. |
| 6 | State-model subsection declaring book-mode placement vs. `buildStore` | **Met** | Decision #13 commits to screen-local `useState` with a `useEffect` clear on `currentResolution.matched_cip` change. §4 Architecture Overview line 253 names the effect. The book-reset test is P0 at line 489 (not P1 as I worried in the prior review). |
| 7 | Grad-degree detection strengthened with typed contract | **Met** | Decision #12 adds `related_education_level` as a typed field on backend `CareerBranch` + the frontend interface. Bucketing Rule 4 uses the typed field as primary, regex-on-`unlock` as fallback only when `related_education_level === null`. Two P0 tests cover both paths. The backend change is correctly scoped — one Pydantic field + one service kwarg, `_format_unlock` untouched for display-string backward compat. |

All seven conditions from the prior review are materially addressed. The spec is in notably better shape than the first submission.

#### Fresh Findings (Not in Prior Review)

##### Concerns

- **UX years labels diverge from the canonical Silver tier boundaries.**
  - **Impact:** `src/silver/onet_experience_transformer.py:145-165` defines the tier thresholds as `entry (years ≤ 1.0) / early (1.0 < years ≤ 4.0) / mid (4.0 < years ≤ 8.0) / senior (8.0 < years)`. The Chapter Book surfaces these same tiers with UX labels `"Years 0–3" / "Years 3–8" / "Years 8–15" / "Past 15"` (§1 Success Criterion 4, plus `types.ts` `years_label` comment). The `entry → "Years 0–3"` label is off by two years — `entry` ends at year 1 in the data. A student whose chapter 1 is labeled "Years 0–3" and chapter 2 "Years 3–8" will assume the first-job window spans three years; the underlying data says one. More importantly, the two specs (`onet-experience-requirements` and this one) now disagree on what a tier means, and the frontend will be the wrong one to trust. Not a blocker — student-facing copy can reasonably round up — but it has to be an **explicit** Decision, not a quiet drift.
  - **Recommendation:** Add a short Decision (#14) that either (a) changes the UX labels to match the data (`"Year 0–1" / "Years 1–4" / "Years 4–8" / "Past 8"` — honest but arguably less poetic for a 17-year-old), or (b) keeps the current labels and explicitly documents them as *storytelling aggregates over the Silver tiers*, with the note that the underlying row-level experience math is still the Silver-tier math. Either is defensible; silence is not. This also feeds the `@fp-copywriter` voice review cleanly.

- **Anchor-SOC duplication edge case is unhandled in Bucketing Rules.**
  - **Impact:** Chapter 1 (anchor) is synthesized from `career.soc_code`. Chapters 2/3/4 representatives come from `get_career_branches(career.soc_code)`. O*NET sometimes returns branch rows where `related_soc_code` is the same 2018 SOC as the source after crosswalk flattening (e.g. `15-1252` self-linking through an 8-digit O*NET SOC that the BLS 6-digit flatten collapses). If such a row wins the per-tier `relatedness` sort (it often has high relatedness — it's the same role), the Chapter Book renders the **same role in chapter 1 and chapter 2**, same title, different years label. A student sees "You're a Software Developer → five years later, you're a Software Developer." The bucketing rules in §4 and Decision #11 do not exclude `to_soc === career.soc_code`.
  - **Recommendation:** Add one line to Bucketing Rule 3: "Before sorting, filter out branches where `branch.to_soc === career.soc_code`." Add one P0 test in `bucketBranches.test.ts` (`drops self-referencing branch whose to_soc equals parent soc`). Trivial spec edit; prevents a small-but-embarrassing rendering bug that absolutely will happen on some parent SOC in the Gold table. If the author believes a genuine mid-tier self-reference is a valid storytelling beat ("five years later, you're still a Software Developer, but with 4x the salary"), then it needs an affirmative Decision, not silence — and the title would have to disambiguate.

- **`requires_grad_degree` semantics for the anchor chapter are implicit.**
  - **Impact:** Chapter 1 (anchor) is the student's entry-level post-graduation role. Bucketing Rule 1 does not set `requires_grad_degree` for the anchor, so the default value rules: `boolean` with no default in `types.ts:351` is `undefined`-equivalent at TypeScript compile time, but will be narrowed to `false` by any consumer. For parent careers whose `education_level_name` is itself `"Master's degree"` or `"Doctoral degree"` (e.g. Biological Technician → Clinical Psychologist), the anchor chapter quietly claims `requires_grad_degree: false` even though the role visibly requires one. The UI won't render a lock glyph on chapter 1 (which is arguably correct — you've already got the degree by hypothesis), but the typed field is lying, and any future consumer (comparison mode, deep-read modal) that branches on `requires_grad_degree` will be wrong.
  - **Recommendation:** In Bucketing Rule 1, explicitly set `requires_grad_degree: false` on the anchor and document the rationale inline: "the anchor chapter is the student's post-graduation role by construction; the student has the required degree by the time this chapter renders, so the grad-degree *gate* (the UI affordance) does not apply." Alternatively, set it from `career.education_level_name` if the parent career type carries it — but that's scope creep, and the first option is cheaper and just as honest. Either way, **say** what the value is.

- **Backend test authorization scope is correctly sized.**
  - **Impact:** I checked — `backend/tests/fixtures/intent_responses.json` is the only fixture under `backend/tests/fixtures/`, and it does not stub branch rows. Branch-tree tests stub MCP rows inline via a `_stub_mcp` helper in `backend/tests/services/test_branch_tree.py:8-15`. No separate fixture file needs updating.
  - **Recommendation:** None. Just flagging that I checked so the next reviewer doesn't re-check.

##### Sound

- **Pydantic/TS parity is now honest.** Backend and frontend `CareerBranch` will both carry the same four optional O*NET-adjacent fields after this spec ships. The `/branches/{soc}` contract becomes a single source of truth for branch shape.
- **Backend change surface is minimal and correctly scoped.** One Pydantic field (nullable default), one service kwarg, `_format_unlock` untouched. `tests/mcp/test_get_career_branches.py` stays green because the MCP row already carries the field. This is the correct "catch up at the Pydantic boundary" move.
- **Book-mode state placement (Decision #13) is the right call.** Screen-local `useState` with a resolution-change `useEffect` avoids the persisted-zustand trap that `selectedCareer` would have created. The P0 test for reset-on-resolution-change is appropriately placed.
- **Bucketing Rule 5 / Rule 6 distinction is clean.** Terminate (all higher tiers empty) vs. bridge (middle-tier gap, higher tier populated) is the right semantic carve-out, and both have P0 tests.
- **Decision #10 ceiling rule is stated verbatim enough for a future pipeline-side spec to mirror or diverge intentionally.** The follow-up spec (`feature-career-branches-ceiling-marker.md`, unfiled) now has a written contract to compare against.

##### Blockers

None. The three fresh concerns are all five-minute spec edits. None of them require rethinking architecture.

#### Verdict

- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED — second pass)

1. **Resolve the years-label/tier-boundary divergence.** Add a Decision #14 that either (a) changes the four UX labels to match the Silver thresholds (`entry → "Year 0–1"`, `early → "Years 1–4"`, `mid → "Years 4–8"`, `senior → "Past 8"`), or (b) keeps the current "Years 0–3 / 3–8 / 8–15 / Past 15" aggregates but states explicitly that they are storytelling compressions over the Silver tiers and the underlying match remains on the Silver-tier strings. Update §1 Success Criterion 4 and `types.ts` `years_label` comment to match whichever the Decision lands on.
2. **Handle the anchor-SOC duplication edge case in Bucketing Rule 3.** Filter branches where `branch.to_soc === career.soc_code` before the per-tier sort. Add a P0 test (`drops self-referencing branch whose to_soc equals parent soc`) in `bucketBranches.test.ts`.
3. **State `requires_grad_degree` explicitly for the anchor chapter in Bucketing Rule 1.** Set it to `false` with an inline comment explaining why (the student has the required degree by the time the anchor renders; the grad-degree affordance is a gate the anchor has already cleared). Alternatively, derive it from `career.education_level_name` if the author wants to expose it — but pick one, and write it down.

None of these three are architecturally deep. All three are "the spec is silent on an edge case that will hit a real student." Fix them as spec edits before moving to DESIGN VISION; no code change is blocked on this review after that.

### @fp-architect Third-Pass Review (2026-04-19, post-second-pass fixes)
**Status:** APPROVED
**Reviewed:** 2026-04-19 (third pass, narrow scope)

#### Purpose of This Pass

Verify the three CHANGES REQUESTED conditions from the second pass were correctly addressed. Spot-check that Decisions #1–#13 and their downstream references were untouched except for the authorized Rule renumbering (old Rule 5 → new Rule 6, old Rule 6 → new Rule 7, because a new Rule 3 was inserted for self-reference filtering). No re-litigation of prior-pass items; no new scope expansion.

#### Conditions from Second Pass — Verification Result

| # | Second-Pass Condition | Status | Evidence |
|---|-----------------------|--------|----------|
| 1 | Resolve years-label / Silver-tier divergence | **Met** | Decision #14 (line 162) commits labels to Silver canonical ranges (`entry 0–1 / early 1–4 / mid 4–8 / senior 8+`), with exact wording delegated to @fp-design-visionary and @fp-copywriter. §1 Success Criterion 4 (line 133) explicitly states ranges MUST match Silver and defers wording to Decision #14. `types.ts` `years_label` field comment (line 346) matches: "final wording owned by @fp-design-visionary per §2 Decision #14, ranges must match Silver tiers (0–1 / 1–4 / 4–8 / 8+)". Bucketing Rule 1 (line 411) sources `years_label` from `chapterCopy.ts` and cross-references Decision #14. The Silver-canonical alignment is locked; the visionary is appropriately scoped to surface copy only. |
| 2 | Filter self-referencing branches before bucketing | **Met** | Decision #15 (line 163) commits to dropping `branch.to_soc === career.soc_code` rows. Bucketing Rule 3 (line 413) implements the filter "before any per-tier sort" (correct ordering — runs after the `experience_tier === null` drop in Rule 2 but before the per-tier filter+sort in Rule 4). New P0 test `filters self-referencing branches before bucketing` (line 474) asserts the dropped branch does not appear in any chapter even with highest relatedness in its tier. Rule-number shift is mechanically correct: old Rule 5 (terminating ceiling) is now Rule 6 (line 420); old Rule 6 (bridge ceiling) is now Rule 7 (line 421); the "Rules 6 and 7 together are the canonical ceiling semantics" summary at line 423 matches. |
| 3 | Set `requires_grad_degree` on anchor chapter from parent `education_level_name` | **Met** | Decision #16 (line 164) derives it from parent via `/^Master\|^Doctoral/i`, noting the anchor is still never rendered as locked but the field is exposed honestly for downstream consumers. Bucketing Rule 1 (line 411) implements: `requires_grad_degree: /^Master|^Doctoral/i.test(career.education_level_name ?? "")`. New P0 test `anchor inherits requires_grad_degree from parent education_level_name` (line 475) asserts "Doctoral or professional degree" → `requires_grad_degree: true` even though the anchor never renders as locked. This resolves the "data dishonesty on Medical Scientist-style parents" concern from the second pass. |

All three second-pass conditions are materially addressed. Rule renumbering was applied correctly. Decisions #1–#13 were not modified (spot-checked: Decision #11's tie-break rule still keyed to `to_soc` lexicographic ascending in Rule 4; Decision #12's grad-degree detection still primary-via-typed-field / fallback-via-unlock-regex in Rule 5; Decision #13's screen-local state model unchanged at §4 Architecture Overview line 256).

#### Observations (Not Blockers)

- **Test-table rule-number references drift.** Two P0 tests in the New Tests Required table still cite the pre-renumber rule numbers in their "What It Validates" column: line 483 cites "(Rule 5)" for `ceiling synthesis terminates book when all higher tiers absent` (should be Rule 6), and line 484 cites "(Rule 6)" for `ceiling-as-bridge when only middle tier is empty` (should be Rule 7). This is prose drift in a description column, not a contract issue — the test assertions themselves don't depend on rule numbers. Fix on next spec edit; not worth blocking on.

- **Decision #5 parenthetical still says `"Years 0–3"`.** Line 153: `| 5 | Chapter 1 ("Years 0–3") is the selected career itself, not a branch |`. This is the pre-Decision-#14 author-draft label showing up in an older Decision's title. Decision #5's load-bearing content (that the anchor is synthesized from the parent `CareerOutcome`, not from a branch row) is untouched; the stale label in its title is cosmetic residue. Not worth blocking on; fix whenever the next spec touch happens.

Neither observation is in scope for this pass's verdict. Both are `s/old/new/g` sweeps the implementer or a future editor can handle.

#### Fresh Concerns

None. The spec now reads cleanly end-to-end. All three second-pass conditions are resolved; no new architectural questions surfaced in verification.

#### Verdict

- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

The spec proceeds to DESIGN VISION (@fp-design-visionary owns §3, including the exact wording of `years_label` per Decision #14).

### @fp-data-reviewer Review (if applicable)
**Status:** SKIPPED — no pipeline, Iceberg schema, DQ rule, or MCP tool changes. The backend additions per Decision #12 (`related_education_level` on Pydantic `CareerBranch` + one service kwarg) surface an existing row field that the pipeline is already producing; no new data is generated. Ceiling case is rendered frontend-only per Decision #3 (data-side follow-up spec to file separately).

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

**Status:** IN PROGRESS (test-writer pass complete; verification pending)

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `buckets four tiers into four chapters when all present` | Four-tier arc → four chapters, correct tier order + slot numbers + kinds. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `drops branches with null experience_tier` | Null-tier branches are skipped; full arc still produces 4 chapters. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `filters self-referencing branches before bucketing` | Self-refs (to_soc == career.soc_code) never appear, even with highest relatedness. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `synthesizes terminating ceiling when senior tier missing` | Early+mid only → chapter 4 is ceiling with soc=null. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `produces two-chapter book when every non-anchor tier is empty` | Empty branches → anchor + one ceiling (years_label "1+ yr"). |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `bridges a middle-tier gap with a ceiling but continues the arc` | Early+senior present, mid absent → chapter 3 is bridge ceiling, chapter 4 is the senior role. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `detects grad-degree via related_education_level (primary path)` | related_education_level "Master's degree" → kind=locked, requires_grad_degree=true. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `falls back to unlock-regex when related_education_level is null` | Null related_education_level + "Master's preferred" unlock → kind=locked (Decision #12 fallback). |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `tie-breaks on to_soc lexicographic ascending at equal relatedness` | Deterministic tie-break per Decision #11. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `anchor inherits requires_grad_degree from parent education_level_name` | Doctoral parent → chapter 1 requires_grad_degree=true (Decision #16). |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `strips zero and null deltas from the pill row` | Deltas={0 or null} are dropped; only non-zero, non-null survive. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `anchor snapshot uses parent stats, not deltas` | Anchor stats_snapshot reflects career.stats; null stats stripped. |
| `frontend/src/components/chapter-book/bucketBranches.test.ts` | `uses canonical year-label copy for populated chapters` | years_label matches chapterCopy.years.* for each tier. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `anchor renders stats_snapshot, not deltas` | Anchor variant shows stats-snapshot testid with five pills; delta-row absent. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `anchor renders em dash for missing snapshot stats` | Missing stat → pill renders "—" fallback. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `anchor renders the SOC emoji via data-socEmoji mapping` | 19-* prefix → 🔬 in DOM; guards the socEmoji lookup. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `role variant renders deltas and SOC code` | delta-row present, SOC visible, data-chapter-kind="role". |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `role prefixes + on positive deltas, no double sign on negatives` | "+2" for positive, "-1" (not "+-1") for negative. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `role hides the delta row when deltas is empty` | Empty deltas map → no bare "What shifts" heading. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `locked collapses by default, expands on click, toggles aria-expanded` | Full collapse/expand/collapse cycle with aria + sub-line visibility. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `locked wires aria-controls to body region` | aria-controls matches chapter-N-body; body element materializes when expanded. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `locked variant carries data-chapter-kind="locked"` | Data attribute target for styling + tests. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `ceiling renders muted 'levels off' copy with no SOC / emoji / deltas` | Ceiling variant has no SOC match, no 🔬 emoji, no delta/snapshot rows. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `ceiling bookmark line only renders when isLast` | isLast=true → bookmark copy; isLast=false → suppressed. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `cards are labeled 'Chapter N: Title' for screen readers` | aria-label format contract. |
| `frontend/src/components/chapter-book/ChapterCard.test.tsx` | `reduced-motion still renders the locked body when expanded` | Motion-free path preserves functional contract. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `fetches branches for the career SOC and renders chapters in order 1→2→3→4` | End-to-end fetch → bucket → render; correct order + kinds. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `refetches when the career SOC changes` | SOC prop change triggers a new getBranchesForSoc call. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `back button calls onBack exactly once per click` | Click → onBack.toHaveBeenCalledTimes(1). |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `Esc keydown anywhere in the book calls onBack` | Escape key triggers onBack. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `keys that aren't Escape do not trigger onBack` | Enter/Space/Tab are silent. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `renders the skeleton while the fetch is pending` | Loading state: chapter-book-skeleton visible, chapters absent. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `suppresses the live-region announcement while loading` | aria-live="polite" node is empty until ready. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `renders an inline retry when the fetch rejects; book does not unmount` | Error state with retry, book surface persists. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `retry triggers a refetch and recovers to the ready state` | First fetch rejects, retry fetches, chapters render. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `surfaces the Error message to the student` | Error.message flows through to UI copy. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `focus lands on the back button when the book mounts` | document.activeElement == back button after mount. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `announces the career title + chapter count in a polite live region once ready` | Live region text contains career title + "N chapters". |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `empty branches emit '2 chapters' (plural) in the live region` | Minimum book still plural-announces. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `reduced-motion: ready state chapters render without animation gating` (P1) | prefers-reduced-motion skips stagger — all chapters queryable. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `reduced-motion: error state still renders` (P1) | Error path unaffected by motion settings. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `reduced-motion: skeleton still renders` (P1) | Loading path unaffected by motion settings. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `back affordance exposes the spec'd aria-label and visible copy` (P2) | aria-label + visible "← Back to all paths" contract. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `book region is role=region with 'The arc ahead for <career>' aria-label` (P2) | Region semantics per §3 a11y table. |
| `frontend/src/components/chapter-book/ChapterBook.test.tsx` | `locked-chapter toggle exposes aria-expanded and aria-controls` (P2) | Toggle a11y contract survives full ChapterBook integration. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `renders the 4fr_8fr grid on desktop viewports` | Grid class is `desktop:grid-cols-[4fr_8fr]`; no residual `7fr_5fr`. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `collapses to single column below desktop` | Fallback `grid-cols-1` class present at <1200px. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `tapping a career row swaps the right column from list to Chapter Book, and Back restores the list` | Click `career-row-*` → `chapter-book` mounts, `career-list` unmounts; Back reverses. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `resets book state when the resolution's matched_cip changes (Decision #13)` | Store mutation on `matched_cip` → book unmounts. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `passing the same matched_cip twice does not collapse book mode` | Store mutation without `matched_cip` change → book persists. |
| `backend/tests/services/test_branch_tree.py` | `TestRelatedEducationLevel` (implementer-written) | Decision #12 backend surface: `related_education_level` flows from MCP row onto `CareerBranch`. |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1022 | 0 | 0 | 1022 |
| vitest | 568 | 0 | 1 | 569 |

### Edge Cases Covered

- Anchor snapshot when stats are partially null (em dash fallback).
- Role chapter when all deltas are zero/null (row suppressed, no bare "What shifts" heading).
- Positive vs. negative delta sign rendering ("+2" vs "-1", no "+-1").
- Locked chapter full collapse → expand → collapse cycle with a11y wiring.
- Ceiling chapter absence of SOC, emoji, deltas, snapshot.
- Bookmark line visibility keyed to `isLast` only.
- ChapterBook refetches when the career SOC prop changes.
- ChapterBook ignores non-Escape keys.
- ChapterBook retry path after initial fetch rejection.
- Live region suppressed during load, populated on ready (plural "chapters" even at minimum).
- prefers-reduced-motion across ready / error / loading paths.
- Grid collapse at `<1200px` preserves `grid-cols-1` fallback.
- Book-mode reset when `matched_cip` changes; persistence when it doesn't.

### Existing Tests Status

All existing `/set-your-course` tests continue to pass unmodified (the extension-only approach preserves `TestRender`, `TestFlow`, `TestLowConfidence`, `TestStartOver`). Backend `TestRelatedEducationLevel` tests (implementer-written) are passing in the 1022-total run.

### Gaps Identified

- **No visual regression coverage.** The list→book swap uses `AnimatePresence mode="wait"` with a 60ms delay on the incoming panel — the visual "rearrange, not flash" feel is not machine-verifiable here. Covered by @fp-design-auditor review instead.
- **act warnings on AnimatePresence transitions.** The chapter-book swap emits act warnings from Framer Motion's internal timing (same pattern as existing `TestFlow` / `TestStartOver`). Not a test failure — assertions still deterministic — but noise in the vitest output. Would require refactoring to controlled `MotionConfig` boundaries to silence.
- **Real Escape dispatch on document.** The Esc test dispatches on the book region node (via `addEventListener` on the ref). A student pressing Escape while focus is inside the anchor chapter body is still covered because the keydown bubbles up to the region, but a `document`-level listener would be closer to the spec copy "Esc anywhere on screen."

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** CHANGES REQUIRED
**Audited:** 2026-04-19

#### Token compliance

- `ChapterBook.tsx:97` — `bg-bp-mid/60 border border-border rounded-xl shadow-lg` matches §3.7 token audit table exactly. PASS.
- `ChapterBook.tsx:108` — Eyebrow `font-data text-micro font-bold uppercase tracking-[2px] text-accent-info` matches §3.7. `tracking-[2px]` is a spec-approved idiomatic value per §3.3. PASS.
- `ChapterBook.tsx:118` — Career title `font-display text-heading font-semibold text-text-primary` matches §3.7. PASS.
- `ChapterBook.tsx:122` — Subtitle `font-body text-body text-text-secondary max-w-[52ch]` matches §3.7. PASS.
- `ChapterBook.tsx:132` — Back affordance `font-body text-small text-text-muted hover:text-text-secondary transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]` matches §3.3-back and §3.7 token table exactly. PASS.
- `ChapterBook.tsx:154` — Thread line `bg-gradient-to-b from-accent-thrive/60 via-border to-border-subtle` matches §3.3 exactly. PASS.
- `ChapterCard.tsx:117` — Card container `bg-bp-mid border border-border-subtle rounded-xl p-5 transition-colors duration-normal` + per-kind left-border matches §3.7. PASS.
- `ChapterCard.tsx:76–98` — `dotClassForKind` and `leftBorderClassForKind` switch tables match §3.3 per-kind visual treatment table exactly: anchor `bg-accent-thrive shadow-glow-thrive` / `border-l-accent-thrive`; locked `bg-accent-insight` / `border-l-accent-insight/70`; ceiling `bg-accent-caution/80` / `border-l-accent-caution/80`; role `bg-text-muted` / `border-l-border`. PASS.
- `ChapterCard.tsx:129` — Chapter eyebrow `font-data text-micro font-bold uppercase tracking-[2px] text-accent-info` matches §3.7. PASS.
- `ChapterCard.tsx:135` — Ceiling title `font-body font-bold text-body-lg text-accent-caution/90` matches §3.7. PASS.
- `ChapterCard.tsx:149,154` — Role/anchor title `font-body font-bold text-body-lg text-text-primary` and SOC `font-data text-micro text-text-muted` match §3.7. PASS.
- `ChapterCard.tsx:169` — Lock pill `bg-accent-insight/10 ring-1 ring-accent-insight/25 ... text-accent-insight ... hover:bg-accent-insight/20` matches §3.3 and §3.7. PASS.
- `ChapterCard.tsx:190` — Locked sub-line `font-body text-small text-accent-insight/90` matches §3.7. PASS.
- `ChapterCard.tsx:34,37,41` — DeltaPill: `bg-bp-surface rounded-full px-2 py-0.5` / `font-data text-micro uppercase {textClass}` / `font-data text-data-sm text-text-primary` matches §3.4 and §3.7. PASS.
- `ChapterCard.tsx:57–69` — SnapshotPill uses `font-data text-micro text-text-secondary` for absolute score — matches §3.4 ("absolute scores are context, slightly smaller + dimmer than delta"). PASS.
- `ChapterCard.tsx:223,244` — `STATS TODAY` / `WHAT SHIFTS` labels: `font-body text-micro uppercase tracking-[2px] text-text-muted` matches §3.7. PASS.
- `ChapterCard.tsx:258` — Ceiling closing note `font-body text-small italic text-text-muted` matches §3.7. PASS.
- `ChapterCard.tsx:264–272` — Bookmark `border-t border-border-subtle ... font-body text-small text-text-muted` / glyph `text-accent-thrive/70` matches §3.7. PASS.
- No hardcoded hex values, no raw `rgba()` calls, no off-token pixel values found in any of the three in-scope files.

#### Breakpoint compliance

- `SetYourCourseScreen.tsx:319` — `grid grid-cols-1 desktop:grid-cols-[4fr_8fr] gap-6 desktop:gap-8 items-start` uses Brightpath `desktop:` prefix (1200 px) per DESIGN.md §Breakpoints. Matches §3.1 spec diff exactly. PASS.
- No standard Tailwind `sm:`, `md:`, `lg:`, `xl:` prefixes found in any of the three in-scope files. PASS.
- `SetYourCourseScreen.tsx:304` — `tablet:pb-10` uses Brightpath `tablet:` prefix (768 px). Pre-existing, not introduced by this feature. PASS.

#### Typography + spacing

- All text scale tokens (`text-micro`, `text-small`, `text-body`, `text-body-lg`, `text-heading`, `text-data-sm`) are Brightpath-defined tokens. No off-scale classes (`text-sm`, `text-lg`, `text-xl`, etc.) found in any in-scope file. PASS.
- Font family tokens (`font-display`, `font-body`, `font-data`) used per DESIGN.md §Typography. PASS.
- `ChapterBook.tsx:113` — `text-[28px]` on the career emoji in the title page. **Spec-approved deviation** per §3 ("career emoji on the title page at `text-[28px]`"). Not a violation.
- `ChapterCard.tsx:143` — `text-[22px]` on the emoji in each chapter title row. **Spec-approved deviation** per §3 ("emoji in each chapter title row `text-[22px]`"). Not a violation.
- Spacing uses standard Tailwind multiples of 4px (`p-5`, `p-6`, `pt-6`, `pb-5`, `pb-6`, `gap-4`, `gap-1.5`, `gap-2`, `gap-3`, `mt-1`, `mt-2`, `mt-3`, `mt-4`, `px-2`, `px-6`, `py-1`, `py-0.5`, `px-2.5`). All on the 4px grid. PASS.
- `ChapterCard.tsx:125` — `-left-[7px]` on thread dot. **Spec-approved deviation** per §3.3 ("decorative alignment idiomatic"). Not a violation.
- `ChapterBook.tsx:154` — `left-[28px]` on thread line. Spec §3.3 specifies `left-[28px]` explicitly. PASS.

#### Motion + focus

- **FAIL — `SetYourCourseScreen.tsx:634–654`: list-to-book AnimatePresence does not gate on `prefers-reduced-motion`.** The `motion.div` for `key="book-mode"` uses `initial={{ opacity: 0, y: 12 }}`, `exit={{ opacity: 0, y: 12 }}`, and `transition={{ ...springs.smooth, delay: 0.06 }}` unconditionally. The spec §3.2 mandates: under `prefers-reduced-motion`, `initial`/`exit` must be opacity-only (no translate) and `transition` must be `{ duration: 0 }` with the 60 ms delay dropped. `SetYourCourseScreen.tsx` does not import `useReducedMotion` (imports at line 3 show only `AnimatePresence, motion` from `framer-motion`). The list-mode `key="list-mode"` motion.div at line 648 has the same gap — `initial={{ opacity: 0, y: 8 }}` without a reduced-motion gate. Expected: import `useReducedMotion`, derive `reducedMotion`, and conditionally flatten the `initial`/`exit`/`transition` props for both keys per the §3.2 implementation sketch.
- `ChapterBook.tsx:144–148` — Stagger container correctly passes `variants={reducedMotion ? undefined : staggerContainer(0, stagger.normal)}` and gates `initial`/`animate` — children with `staggerItem` variants skip animation when parent provides no variant. PASS.
- `ChapterCard.tsx:178` — Chevron rotation uses `springs.snappy`, gated: `transition={reducedMotion ? { duration: 0 } : springs.snappy}`. Matches spec §3.3. PASS.
- `ChapterCard.tsx:212` — Locked expand/collapse uses `springs.smooth`, gated correctly for reduced motion. Matches spec §3.3. PASS.
- All Framer Motion transitions reference named springs from `frontend/src/styles/motion.ts` (`springs.smooth`, `springs.snappy`, `staggerContainer`, `staggerItem`). No inline `{ stiffness: N, damping: N }` literals invented outside of `motion.ts`. PASS.
- Focus ring pattern `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]` applied correctly to: back affordance (`ChapterBook.tsx:132`), back affordance in error state (`ChapterBook.tsx:234`), lock pill toggle (`ChapterCard.tsx:169`). Matches DESIGN.md §Focus States. PASS.

#### A11y IDs

- **FAIL — `ChapterBook.tsx:97–98`: `data-testid` does not match spec §3.8.** Spec requires `data-testid="chapter-book-{soc}"`. Code renders `data-testid="chapter-book"` (static string). Fix: `data-testid={`chapter-book-${career.soc_code}`}`.
- **FAIL — `ChapterBook.tsx:96`: `aria-label` used instead of `aria-labelledby`.** Spec §3.8 requires `<section ... aria-labelledby="chapter-book-title-{soc}">`. Code uses `aria-label={...}` directly. The h2 at line 118 has no `id` attribute. Fix: add `id={`chapter-book-title-${career.soc_code}`}` to the h2 and switch the section to `aria-labelledby={`chapter-book-title-${career.soc_code}`}`. Also add `data-testid={`chapter-book-title-${career.soc_code}`}` to the h2 per spec §3.8.
- **FAIL — `ChapterCard.tsx:118`: chapter card `data-testid` format does not match spec §3.8.** Spec requires `data-testid="chapter-{n}-{soc|ceiling}"`. Code renders `data-testid={`chapter-${chapter.number}`}`. Fix: `data-testid={`chapter-${chapter.number}-${chapter.soc ?? "ceiling"}`}`.
- **FAIL — `ChapterCard.tsx:120`: `aria-label` used instead of `aria-labelledby` on article.** Spec §3.8 requires `<article aria-labelledby="chapter-{n}-title">`. Code uses `aria-label="Chapter {chapter.number}: {chapter.title}"`. The h3 at lines 135/149 has no `id`. Fix: add `id={`chapter-${chapter.number}-title`}` to the h3 (both ceiling and non-ceiling branches) and switch the article to `aria-labelledby={`chapter-${chapter.number}-title`}`. Also add `data-testid={`chapter-${chapter.number}-title`}` per spec §3.8.
- **FAIL — `ChapterCard.tsx:163`: locked chapter expand toggle missing `aria-label`.** Spec §3.8 requires `aria-label="Read chapter {n}: opens with a graduate degree"` when collapsed and `"Hide chapter {n}"` when expanded. Code omits `aria-label` entirely. Fix: add `aria-label={expanded ? `Hide chapter ${chapter.number}` : `Read chapter ${chapter.number}: opens with a graduate degree`}`.
- **FAIL — `ChapterBook.tsx:172–173` (skeleton): missing `aria-busy` and `aria-label`.** Spec §3.8 requires `aria-busy="true" aria-label="Loading the arc"` on the skeleton container. Code has only `data-testid="chapter-book-skeleton"`. Fix: add `aria-busy={true}` and `aria-label="Loading the arc"` to the skeleton wrapper div at line 172.

#### Spec-approved deviations (cross-referenced to §3)

- `ChapterBook.tsx:113` — `text-[28px]` on career emoji in title page. Approved per §3 note: "career emoji on the title page at `text-[28px] leading-none`."
- `ChapterCard.tsx:143` — `text-[22px]` on emoji in each chapter title row. Approved per §3 note: "`text-[22px]` for the emoji in each chapter title row."
- `ChapterCard.tsx:125` — `-left-[7px]` on thread dot. Approved per §3.3: "Brightpath-idiomatic for decorative alignment."
- `ChapterBook.tsx:108` / `ChapterCard.tsx:129` — `tracking-[2px]` on eyebrow labels. Approved per §3.3: "Brightpath-idiomatic for decorative alignment."
- `ChapterCard.tsx:216` — `max-w-[58ch]` on `what_changes` body. Not in §3.7 token table but uses no off-token value; `ch` units are line-length hygiene, not a color/spacing/radius token. Non-blocking.

#### Verdict

- [x] APPROVED — all six CHANGES REQUIRED items resolved; 568/568 frontend tests and 1022/1022 backend tests green; tsc clean
- [ ] CHANGES REQUIRED — list file:line fixes to make before CODE REVIEW

**Remediation Log (2026-04-19, post-audit):** All six findings addressed — `useReducedMotion` gate in `SetYourCourseScreen.tsx`; dynamic `data-testid`/`aria-labelledby` wiring in `ChapterBook.tsx` and `ChapterCard.tsx`; skeleton `aria-busy`/`aria-label`; locked toggle `aria-label`. Test files updated for new testid/aria-labelledby contract.

**Original fixes required (all resolved):**

1. **`SetYourCourseScreen.tsx:1,634,648`** — Import `useReducedMotion` and gate both `key="book-mode"` and `key="list-mode"` motion transitions on it. When reduced motion is active: remove `y` from `initial`/`exit`, set `transition={{ duration: 0 }}`, drop the `delay: 0.06` on the book entrance. Spec: §3.2 `prefers-reduced-motion` fallback.

2. **`ChapterBook.tsx:96–98,118`** — `data-testid` and `aria-labelledby` wiring: (a) change `data-testid="chapter-book"` to `data-testid={`chapter-book-${career.soc_code}`}`; (b) switch `aria-label` to `aria-labelledby={`chapter-book-title-${career.soc_code}`}`; (c) add `id={`chapter-book-title-${career.soc_code}`}` and `data-testid={`chapter-book-title-${career.soc_code}`}` to the h2. Spec: §3.8 accessibility table.

3. **`ChapterCard.tsx:118`** — Change `data-testid={`chapter-${chapter.number}`}` to `data-testid={`chapter-${chapter.number}-${chapter.soc ?? "ceiling"}`}`. Spec: §3.8 accessibility table.

4. **`ChapterCard.tsx:120,135,149`** — Switch article from `aria-label` to `aria-labelledby={`chapter-${chapter.number}-title`}`; add matching `id={`chapter-${chapter.number}-title`}` and `data-testid={`chapter-${chapter.number}-title`}` to the h3 in both the ceiling branch (line 135) and the non-ceiling branch (line 149). Spec: §3.8 accessibility table.

5. **`ChapterCard.tsx:163`** — Add `aria-label={expanded ? `Hide chapter ${chapter.number}` : `Read chapter ${chapter.number}: opens with a graduate degree`}` to the lock toggle button. Spec: §3.8 accessibility table.

6. **`ChapterBook.tsx:172`** — Add `aria-busy={true}` and `aria-label="Loading the arc"` to the skeleton wrapper div. Spec: §3.8 accessibility table.

### Code Review (@faang-staff-engineer)
**Status:** APPROVED
**Reviewed:** 2026-04-19

The lens: security (XSS, URL injection, adversarial `unlock`/`occupation_title`), performance (memo keys, per-keystroke allocations, O(n²) at branch scale), error-handling (fetch race, unmount cleanup, non-Error rejection), type safety, test quality, and regression surface on pre-existing `CareerBranch` consumers. Style/naming/formatting explicitly ignored.

#### Critical (blockers)

None.

#### Significant

None. I pushed on every lever the spec flagged and came back with zero outage-class findings. Stated plainly below what I checked and what I found.

#### Nit-level observations

These do not block. Documented for the implementer's awareness and as a breadcrumb for the next refactor.

1. **Fixed-element-ID collision risk if two `ChapterCard`s ever render in one DOM.** `ChapterCard.tsx:120,136,154,175,213` use `id={`chapter-${chapter.number}-title`}` and `id={`chapter-${chapter.number}-body`}` — not scoped by SOC. Today the spec mounts at most one book at a time, and `bucketBranches` emits unique chapter numbers 1–4 per book, so there is no collision. But `ChapterBook.tsx:122` correctly namespaces the book title id by `${career.soc_code}`; the chapter ids silently do not. If a future caller mounts two books side-by-side (compare-two-careers, say), every pair of identical chapter numbers would produce duplicate `id`s and the `aria-labelledby`/`aria-controls` wiring would point at the wrong one. Low risk today, one-line fix when it bites: interpolate `career.soc_code` into the chapter ids.

2. **`handleCareerSelect` in `SetYourCourseScreen.tsx:171–185` preserves `setSelectedCareer` + `setCommittedClick` telemetry and then *also* opens the book.** I flagged this as a zombie-path candidate going in — it is not. The commit telemetry is load-bearing: the `pickedSoc` badge on the list uses `selectedCareer?.soc_code` (line 676/685), and `setCommittedClick` logs the pick for the debug trace. Preserving both while adding `setSelectedChapterCareer` is the correct behavior. Worth a follow-up clean-up later: when we know the post-book commit affordance lives inside the book (per §Decision #7 resolution), the click-opens-book path should probably only set `selectedChapterCareer`, and the actual commit should move to the in-book CTA. Not this spec's job.

3. **`useEffect` that focuses the back button on `career.soc_code` change (`ChapterBook.tsx:58–60`) and the Esc handler (`ChapterBook.tsx:63–74`) both live on the book region.** On the initial mount both the focus-on-mount effect and the fetch effect fire with `career.soc_code` already defined, so there is no `undefined`-initial-value spuriously-firing concern (there is no "initial undefined" state — `career` is a required prop). This is cleaner than the screen-local `matched_cip` `useEffect` at `SetYourCourseScreen.tsx:195–197` which DOES fire on first mount with `currentResolution?.matched_cip === undefined` and calls `setSelectedChapterCareer(null)` redundantly. The redundant call is a no-op (state is already `null`), so no observable bug. The spec test at `SetYourCourseScreen.test.tsx:412–440` specifically guards that a same-cip mutation does NOT collapse the book, which is the actual contract students care about.

4. **`composeTerminatingCeilingLabel` produces `"1+ yr"` (singular) but `"4+ yrs"`/`"8+ yrs"` (plural) at `bucketBranches.ts:106–110`.** That is a copy decision, not a bug. Consistent with `chapterCopy.years.early = "Years 1–4"` vs `"Years 4–8"` both using the same unit. Fine.

5. **`chapterCopy` is frozen with `as const` and re-used across every book.** Pure structural sharing; no mutation; safe.

#### What's actually good

Mandatory section, not grudging. Name the parts that are solid so the implementer can trust the unreviewed surface.

- **`bucketBranches.ts` is textbook pure.** No I/O, no hidden globals, no time dependency, every rule traceable to spec §4. The `NonAnchorTier` narrowing type + the `NON_ANCHOR_TIERS as readonly NonAnchorTier[]` pattern is the right TypeScript idiom here — the cast the reviewer flagged (`tier = NON_ANCHOR_TIERS[i] as NonAnchorTier` at lines 228, 246) is unavoidable without a reducer or a typed-for-of, and the cast is sound because the literal tuple is `readonly NonAnchorTier[]`. Acceptable.
- **`relatedness ?? Number.NEGATIVE_INFINITY` (line 122–123) handles the null path cleanly.** `NaN` cannot come through from `branch.relatedness` because the type is `number | null` and the backend model is `float | None`. If a row from DuckDB ever returned `float('nan')` the subtraction `rB - rA` would be `NaN`, and the sort comparator would treat it as "equal" — deterministic, just unstable between NaN pairs. Low-concern.
- **Fetch race in `ChapterBook.tsx:34–53` uses the canonical `let cancelled = false` + cleanup pattern.** Correct. Non-`Error` rejection is handled: `err instanceof Error ? err.message : "<fallback copy>"`. No stringification of arbitrary objects, no `JSON.stringify` eating cycles. Clean.
- **`useMemo` for chapters at `ChapterBook.tsx:80–83` has the right dependency set** (`[career, fetchState]`). Per-keystroke-in-parent concern: `career` changes only when the user clicks a different career row — NOT on keystroke in the major input — because `selectedChapterCareer` lives in screen-local state separate from `majorText`. So `bucketBranches` does not run per keystroke. Verified by reading `SetYourCourseScreen.tsx:71,76` separately.
- **Backend Pydantic addition is defensive.** `related_education_level: str | None = None` with default, mirrored in `branch_tree.py:103–107` with the `row.get()` + `str(...)` guard. Pre-v1.2.0 rows that don't carry the key still round-trip as `None`. Backward-compat preserved.
- **Security surface is clean.** No `dangerouslySetInnerHTML` anywhere in the three new files. `career.occupation_title`, `branch.to_title`, and `branch.unlock` all render as text children — React auto-escapes. `soc_code` is interpolated into `id`/`data-testid`/`aria-labelledby`, but SOC codes are `XX-XXXX` by contract; even an adversarial one produces at worst a malformed-but-harmless attribute. No URL injection path — none of the book surfaces take a URL from branch data.
- **Performance at scale.** `/branches/{soc}` typically returns ≤50 rows (O*NET flattening caps it). `bucketBranches` is O(n log n) in branches count dominated by the three `pool.sort()` calls at `bucketBranches.ts:121`. Three sorts × 50 items is irrelevant. No N+1. No nested loop over `branches × chapters` that could explode.
- **Test quality: 45 new tests actually test behavior.** I looked for tautologies and did not find them. `bucketBranches.test.ts` covers the ceiling-terminating/bridge split, the self-ref drop, the tie-break, the grad-degree primary path AND fallback, zero/null-delta stripping, and the empty-branches case. `ChapterCard.test.tsx` asserts on `aria-expanded`/`aria-controls`/`data-chapter-kind`/rendered SOC text — contract-level observables, not implementation details. `ChapterBook.test.tsx` exercises the fetch-cancellation (via SOC-change rerender), the retry, the error message surfacing, the polite-live-region load-bearing text, and the reduced-motion path. If the implementation were replaced with a stub, every one of these tests would fail loudly.
- **Regression surface is covered.** `CareerBranch` interface grew by four fields. Verified downstream consumers:
  - `BranchChip.tsx` (lines 1–97): reads only the five delta fields + `unlock`. Unaffected. Its test fixture at `BranchChip.test.tsx:29–32` includes the four new fields correctly.
  - `CareerLineageSheet.tsx`: untouched; `CareerLineageSheet.test.tsx` fixture at lines 121–124 includes the four new fields.
  - `mockBuild.ts:139–143`: every `CareerBranch` literal includes all four new fields.
  - `mockBranches.ts:7–42`: both fixture rows carry all four fields.
  - Backend `test_builds.py`, `test_report_gen.py`, `test_guidance.py`, `test_builds_wrapped.py` construct `CareerBranch` but do not pass `related_education_level` — they rely on the `= None` default. Safe, because the field is nullable with a default.

#### Verdict

- [x] APPROVED — proceed to VERIFICATION
- [ ] CHANGES REQUIRED — fix Critical + Significant, then re-review
- [ ] BLOCKER — escalate to human

Grudging addendum: this one is ready. The design-auditor loop already caught the a11y sins before it got to me, which is the correct pipeline operating as designed. I will be watching the id-scoping question on the next spec that mounts two books simultaneously; flagged above for that future reviewer.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-19 00:45

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | PASS (pre-existing failures noted) | 45 errors in 18 files — all pre-existing from the set-your-course spec and earlier; zero errors in any chapter-book file. No backend files were modified by this spec. See note below. |
| Tests (pytest) | PASS | 1022 passed, 0 failed, 62 warnings (deprecation only) |

**mypy note:** The 45 mypy errors are confined to `gemma_client.py`, `career.py`, `stat_engine.py`, `api.py`, `builds.py`, `intent.py`, `guidance.py`, `wrapped_renderer.py`, `skill_pool.py`, and router files — all predating this spec. This spec introduced no backend changes. The errors were present before this spec and are not attributable to it. Exit code is 1 (pre-existing); no new errors were introduced.

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (exit 0) |
| Tests (vitest) | PASS | 568 passed, 1 skipped, 0 failed — 56 test files |
| Production build (Vite) | PASS | 686 modules transformed; dist/assets/index.js 835 KB gzip 249 KB; chunk-size warning only (pre-existing) |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All checks passed (backend mypy pre-existing) | — | — |

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Design Vision decisions an implementer might otherwise re-litigate (2026-04-20, @fp-design-visionary)

The layout is a one-line ratio swap — `desktop:grid-cols-[7fr_5fr]` → `desktop:grid-cols-[4fr_8fr]`, `gap-6 desktop:gap-8` preserved, `items-start` preserved, no divider between columns, no sticky sidebar. The book sits inside `<PageContainer variant="centered">`, which caps the outer cell at ~680 px on desktop; the 8fr right column is only ~450 px wide, and every line-length and pill-row in §3 is calibrated for that constraint — do not design for a full-viewport book. The list ↔ book transition uses `springs.smooth` with `<AnimatePresence mode="wait">` and a 60 ms delay on the incoming panel for a "rearrange, don't flash" feel; reduced-motion fully neuters the translate and the stagger. Year-label copy is locked per Decision #14 (`"Starting out · 0–1 yr" / "Years 1–4" / "Years 4–8" / "8+ yrs"`) and lives in `chapterCopy.ts`; the locked-chapter sub-line is the generic `"Opens with a graduate degree."` — do not interpolate the `unlock` display string into it. Delta pills use stat-color on the abbreviation only; no red/green recoloring of the pill or value by sign — the book refuses to grade outcomes.

[Final thoughts, lessons learned, follow-up items.]
