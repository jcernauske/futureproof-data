# Feature: /future Tree Enhancements (9-feature bundle)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-future-tree-enhancements.md in its entirety.

This spec bundles 9 in-scope enhancements across three tiers (T1, T2, T3) plus
2 cut enhancements documented in §10. Each in-scope enhancement is independently
shippable. The minimum-shippable subset for May 18, 2026 is T1.1 + T1.3.
Sequence per §6.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1-§4 (system architecture, data flow, API
     contracts, Pydantic models). Critical surfaces:
       a. T1.1 + T2.2 — adding `relatedness` to TreeNode (backend payload extension)
       b. T2.4 — backend support for re-rooting a build (new endpoint or client refetch)
       c. T3.3 — MCP latency on get_task_breakdown for both root + selected SOC
   - Invoke @fp-data-reviewer to review data quality implications:
       a. T2.2 relatedness gradient — verify CareerBranch.relatedness propagation
          through career_tree.build_tree without value drift
       b. Boss-outcome filter (T2.1) — verify computed boss_* values on TreeNode
          are stable + match the gauntlet's results for the same SOC
   - Both write findings to §5 (Architecture Review).
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED: STOP, alert human.
   - If REJECTED: STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to propose the premium version of each enhancement.
     Focus areas:
       a. T1.1 edge label pills — placement, typography, color tokens for delta-sign
          coloring, animation on hover/select.
       b. T1.2 tour chips — visual distinction from filter chips so students don't
          confuse "highlight" with "filter".
       c. T1.3 mini-compare delta strip — micro-typography, arrow glyphs, wrapping.
       d. T1.4 breadcrumb — inline above tree, hidden-by-filter ghosting state.
       e. T2.1 SURVIVES filter row — third row strategy: stay inline vs. expander.
       f. T2.2 relatedness gradient — edge thickness/opacity scale.
       g. T2.3 "what it takes" block — bullet vs. inline, transition from current
          single education line.
       h. T2.4 "Make this my path" CTA — placement on card, confirmation copy.
       i. T3.1 stage axis labels — ghost background labels vs. column headers.
   - Visionary writes to §3 by enhancement (T1.1, T1.2, ...).
   - For copy on chips, breadcrumb tooltips, CTA labels, and tour chip names: invoke
     @fp-copywriter (writes to §3 inline per enhancement).

3. IMPLEMENTATION
   - Implement per the sequencing in §6. Each tier may ship as its own PR.
   - BEFORE coding: review §4 Testing Impact Analysis — every enhancement has
     associated tests. Recursive filter machinery (educationFilter / statFilter)
     and the FitOnTreeChange anchored re-fit are the most fragile surfaces.
   - DURING coding: update tests listed in "Authorized Test Modifications" only.
     If any test NOT in that list fails, STOP and escalate.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) per tier.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). If still
     broken after 3, escalate via §10 Discussion.

4. TESTING
   - Invoke @test-writer to extend coverage per §4 "New Tests Required".
   - Backend: pytest for any backend payload changes (T2.2 relatedness, T2.4
     re-root endpoint).
   - Frontend: vitest for filter-logic recursion (T2.1 boss filter), edge label
     rendering math (T1.1), breadcrumb behavior (T1.4), mini-compare math (T1.3),
     tour-chip ranking functions (T1.2).
   - Run ALL tests. Existing 766+ vitest + ~1257 pytest must still pass.

5. DESIGN AUDIT
   - Invoke @fp-design-auditor to verify Brightpath token compliance across all
     new visual elements: edge label pills, tour chips, mini-compare strip,
     breadcrumb, SURVIVES row, "Make this my path" CTA.
   - Writes findings to §8 Design Audit.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
   - Focus areas: re-root flow (T2.4) for state-machine correctness, MCP fetch
     caching (T3.3) if shipped, backend payload schema (T2.2).
   - Writes findings to §8 Code Review.

7. VERIFICATION
   - Invoke @fp-builder to run full build verification (ruff + mypy + pytest +
     tsc + vitest + Vite production build).
   - Log results to §9.

8. COMPLETION
   - Update top-level Spec Status to COMPLETE (or partial COMPLETE per shipped tier).
   - Check off completed Success Criteria in §1 — note unchecked stretch items
     explicitly so future readers see what was deferred.
   - Generate report to reports/feature-future-tree-enhancements-YYYY-MM-DD.md.
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
| Created | 2026-05-01 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-01 |
| Branch | career-path-enhancements |
| Hackathon Deadline | 2026-05-18 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-tree-as-map.md` (predecessor /branches view), `docs/specs/feature-tree-horizon-map.md` (lane-style /branches), `docs/specs/feature-ask-gemma.md` (chat scope wiring) |

---

## §1 Feature Description

### Overview
Bundle of 9 in-scope enhancements (plus 2 cut, documented in §10) to the experimental `/future` screen — the React Flow tree sibling to `/branches`. Each in-scope enhancement is independently shippable; spec covers all of them so reviewers see the full design space before any subset goes out the door. The 11-feature original brainstorm was trimmed to 9 after author review (see §11 resolutions).

### Problem Statement
`/future` today is a navigable tree of career branches with two filter rows, a chat anchor, and a SOC card. It works, but a product brainstorm (`@fp-product-partner`, 2026-05-01) surfaced a clear story: the screen *shows shapes* without *answering decisions*. Edges are silent, the SOC card is absolute-only (no compare-to-root signal), and discovery is "click around and hope." Students don't return to the screen because nothing alive happens between visits.

The 11 enhancements collectively convert `/future` from a tree-explorer into a decision tool: each edge tells you what changes, each card tells you what's better, canned tours give you a starting point, and a survives-the-gauntlet filter closes the loop with the boss fights.

### Success Criteria

**Tier 1 (must-ship subset):**
- [x] Every visible edge in the tree carries a 1–2 word delta label (T1.1)
- [x] Selecting any non-root node renders a 3-row delta strip on the SOC card (T1.3)

**Tier 1 (full):**
- [x] Four "tour" chips above the tree highlight ranked subsets via flash, not filter (T1.2)
- [x] Selection persists visually as a clickable breadcrumb when filters hide it (T1.4)

**Tier 2:**
- [x] Filter row reorganized to 2-row grouping: SHOW ONLY + SURVIVES on row 1 (constraints), IMPROVES on row 2 (deltas) — third row "SURVIVES" filters by boss outcome (T2.1) — trimmed to 3 chips per @fp-data-reviewer
- [x] Edge thickness/opacity encodes relatedness rank (T2.2)
- [x] SOC card replaces single education line with a 3-bullet "what it takes" block (T2.3)
- [ ] ~~"Make this my path" secondary CTA on the SOC card re-roots the tree (T2.4)~~ — **CUT, see §10**

**Tier 3 (stretch):**
- [ ] ~~Stage axis labels above the tree ("Now / Next move / Move after") (T3.1)~~ — **shipped then removed at user request 2026-05-01** (felt like noise once the rest of the rail filled in)
- [ ] ~~Return-visit "What changed?" banner~~ — **CUT, see §10**
- [ ] ~~Task-overlap chip on SOC card via MCP `get_task_breakdown` (T3.3)~~ — **post-hackathon, deferred**

**Cross-cutting:**
- [x] No regressions in existing /future tests (now 17 — added breadcrumb-persistence regression test)
- [x] No regressions in existing /branches tests (BranchHorizonMap, etc.)
- [x] Tree pane height + zoom band still keep the root visible at default fit
- [x] Spanish + Arabic locale parity for every new string surface (49 new keys × en/es/ar)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Bundle all 11 enhancements in one spec rather than 11 specs | They share render surfaces (tree, SOC card, filter rows) and a coherent narrative ("convert /future from explorer to decision tool"). Spec discipline survives because each enhancement is independently testable and shippable. | One spec per enhancement (overhead, fragmented review). One spec per tier (still fragmented because Tier 1 alone has cross-component changes). |
| 2 | Filter applies recursively on T2.1 boss row, matching T1 (education) and T2 (stat) recursion behavior | Consistency: a parent passing the filter while its children fail produces a confusing surface — caught when shipping stat filter (Sales Mgrs $138k passing while Customer Service $42k rendered as child). | L1-only filter (cheaper but produces the bug we already fixed). |
| 3 | T1.2 tour chips use highlight (flash), not filter | Filtering reshapes the tree; highlighting preserves the full graph and just guides the eye. Reuses BranchHighlightDriver, which already handles the flash mechanic for Gemma name-drops. | Filter-style (would compete with the existing two filter rows + boss row); show-only-overlay (would need new state machine). |
| 4 | T1.3 mini-compare strip lives on SelectedNodeCard, not as a separate panel | Mini-delta is 80% of the value of side-by-side compare at 20% of cost (per @fp-product-partner). Avoids a third column on desktop. | Side-by-side compare panel — explicitly out of scope (§10). |
| 5 | T1.4 selection drops in actual state but persists in breadcrumb when filter hides it | Breadcrumb is a visual aid for "you'd be here if you cleared the filter" — re-asserting selection while the filter excludes it would surface confusing chat scope. | Hold selection in state regardless (chat anchors to invisible node — bad). Drop selection silently (current behavior, opaque). |
| 6 | T2.1 SURVIVES uses tier-3 filter row | Closes gauntlet ↔ /future loop, which is one of the only narrative threads holding the product together. | Cut entirely — but loses the loop. Move into IMPROVES row — wrong semantics, IMPROVES is delta-vs-root, SURVIVES is absolute outcome. |
| 7 | T2.2 relatedness data flows backend → frontend via TreeNode payload extension | TreeNode currently lacks `relatedness`; CareerBranch has it but isn't on the /future fetch path. Adding to TreeNode is the cleanest carry-through. | Frontend client-side join via separate /branches/{soc} fetch — extra latency, awkward state. |
| 8 | T2.4 "Make this my path" uses backend re-root (new endpoint) rather than client refetch | Re-anchoring chat scope, build identity, stat baseline all change atomically — backend is the right transactional boundary. Client refetch leaves stale state. | Client-side refetch of `/tree/{soc}` only — chat scope and SelectedNodeCard build context wouldn't follow. |
| 9 | T3.2 return banner is conditional on an actual refresh signal | Theater otherwise. If we ship a banner that says "X changed" without a real signal, students will catch us. | Always-on banner with rotating copy — dishonest. Skip entirely — also fine, but flagging as a real opportunity if a signal exists. |
| 10 | T3.3 task-overlap chip is post-hackathon | New MCP fetch on every selection adds latency to a UI loop that's already chat-driven. Caching + overlap algorithm is its own mini-spec. | Pre-fetch on all visible nodes — explodes MCP call count. Inline in T1.3 mini-compare — premature. |
| 11 | Brightpath design tokens used throughout — no hardcoded colors / spacing | Project-wide rule from `CLAUDE.md`. `@fp-design-visionary` defines exact tokens in §3 per enhancement. | Hardcoded colors for speed (would fail @fp-design-auditor). |

### Constraints

- **Hackathon deadline:** May 18, 2026. T1.1 + T1.3 are the must-ship subset. Anything else is upside.
- **Existing test floor:** 766+ vitest, ~1257 pytest. No regressions allowed.
- **`/branches` parity:** /future is an experiment alongside /branches. Both must remain functional. Whichever resonates better survives post-hackathon.
- **Brightpath only:** No Cozy Quest tokens. No light-mode. No hardcoded colors.
- **Locale parity:** Every new string ships in en + es + ar. The repo's i18n test catches missing keys.
- **Filter rail height ceiling:** Adding T2.1 puts three filter rows above the tree; on smaller laptops this pushes the tree below the fold. Tree pane height (currently 60vh, minHeight 480) may need re-tuning per @fp-design-visionary.
- **Backend payload size:** T2.2 adds `relatedness` to every TreeNode in the payload. Negligible bytes per node, but worth confirming with @fp-architect on the depth=2 fetch.

### Out of Scope

Listed in §10. Brief preview: HMN improvement filter, side-by-side compare panel, edge animations, more filter chips beyond a third row.

### Dependencies

| Dep | Affects | Notes |
|-----|---------|-------|
| `relatedness` on TreeNode | T1.1 (if used as a label fallback), T2.2 (gradient + Stretch chip) | Backend `career_tree.build_tree` carries `CareerBranch.relatedness` through to TreeNode. Schema-additive, non-breaking. |
| Backend re-root endpoint | T2.4 | Either new `POST /build/reroot` or extension of `/build/create` with `parent_build_id` + `from_branch_soc`. @fp-architect to scope. |
| MCP latency budget | T3.3 | `get_task_breakdown(soc)` × 2 (root + selected) per click — adds ~200-500ms per selection. Out of scope for hackathon; flag here so we don't accidentally land it. |
| Real data refresh signal | T3.2 | Only ship if BLS quarterly refresh / O*NET periodic update is wired to a per-build "last freshness" timestamp. Otherwise cut. |

---

## §3 UI/UX Design

> @fp-design-visionary fills each subsection per enhancement BEFORE implementation. Each becomes the pixel-perfect target.

### T1.1 — Edge labels with the delta

**Status:** LOCKED (visionary 2026-05-01)

**Emotional target:** *"Each branch is whispering what changes."* The student's eye glides along an edge and the pill calls out the one fact that matters — a degree, a salary jump, a tier shift. Reading the tree should feel like reading a comic strip's gutters: the pills are the connective tissue between panels.

**Scope:** Custom React Flow edge component (`flow/EdgeWithLabel.tsx`) renders a small pill anchored to the edge midpoint. Label text is computed by `data/edgeLabel.ts` per the priority chain (locked below).

#### Selection logic — LOCKED priority chain

```
1. Education tier delta if non-zero      → "+Master's" | "+Doctorate" | "+Bachelor's"
2. Experience tier delta if non-zero     → "Mid+" | "Senior+" | "+5 yrs" (use yrs label only when both tiers known)
3. Pay delta if |Δwage| ≥ $10,000        → "+$24k" | "-$12k"   (k-rounded — see formatting)
4. Relatedness fallback                  → "Close" if rank ≤ 5; "Stretch" if rank ≥ 11; else omit
5. Otherwise null                        → no pill renders (line stays uneventful)
```

The priority chain is opinionated: education trumps everything because "I need another degree" is the single biggest decision a student faces. Pay only wins when nothing more decision-shaping is true.

#### Two colors — LOCKED

Per §11 resolution: NO red. Only two pill kinds.

| Kind | Trigger | Background | Border | Text | Token chain |
|------|---------|-----------|--------|------|-------------|
| **improvement** | Education deeper, experience advances, pay up, relatedness "Close" | `rgba(125, 212, 163, 0.15)` | `rgba(125, 212, 163, 0.32)` | `--color-accent-thrive` | thrive @ 15% / 32% / full |
| **neutral** | Sideways/lateral, pay down, education shorter, relatedness "Stretch", or unknown direction | `rgba(45, 48, 96, 0.85)` | `--color-border-subtle` | `--color-text-secondary` | bg-surface @ 85% / border-subtle / text-secondary |

Rationale: a "Pivot Lateral" branch with lower pay isn't bad — it may carry life-fit. Painting it red would moralize. The neutral pill reads as a quiet caption; the improvement pill reads as a wink.

#### Pill geometry — LOCKED

```
shape:           rounded-full (--radius-full)
padding:         3px 8px
height:          ~20px (data-mono ascender + 6px vertical padding)
border:          1px solid (color per kind above)
font-family:     --font-data (Space Mono)
font-size:       11px              ← above text-stat-label (10px) so it reads at 0.5 zoom; below text-micro (12px)
font-weight:     700
letter-spacing:  0.4px
line-height:     1
white-space:     nowrap
backdrop-filter: blur(4px)         ← keeps pill legible when overlapping the edge stroke or another node halo
shadow:          --shadow-sm       ← lifts pill off the void backdrop, especially at default fitView zoom
```

The pill must read at fitView zoom (~0.5x). At that zoom 11px renders as ~5.5px on screen — borderline. The 700 weight + Space Mono's high x-height + the bg-surface fill keep it crisp. `text-stat-label` (10px) was tested and fails this; 12px (`text-micro`) bloats the pill at 1x. **11px is the locked size.**

#### Placement & math — LOCKED

```
x = (sourceX + targetX) / 2
y = (sourceY + targetY) / 2
offset perpendicular to edge: 0px (centered on the line)
transform: translate(-50%, -50%)
pointer-events: auto                ← so hover expansion works
z-index above edge stroke, below node card
```

The pill sits *on* the line, not floating above it. The bg-surface fill + 1px border + `backdrop-filter: blur(4px)` paint the stroke right out from underneath the text — a self-erasing background that lets the line keep its visual continuity while the label still owns the spot. This is cleaner than a perpendicular offset, which on the staircase layout creates a wandering label-cloud above the tree.

For relatedness-faded edges (T2.2) the pill background stays at full opacity — text emphasis must not fade with the edge.

#### Hover — LOCKED

```
Trigger:         pointerenter on the pill (200ms hold to prevent flicker on transit)
Visual:          pill expands to show full delta detail in the same pill shape
Content rules:
  Education kind:    "Bachelor's → Master's"
  Experience kind:   "Entry → Mid-career (~5 yrs)"
  Pay kind:          "$95k → $138k  (+$43k)"
  Relatedness kind:  "Close · rank 3 of 20" | "Stretch · rank 14 of 20"
Animation:       width auto-grows via Framer Motion layout animation, springs.snappy
                 (stiffness: 400, damping: 25)
Z-index lift:    +1 over peer pills, --shadow-md on hover
Dismiss:         pointerleave + 100ms grace
```

#### Number formatting — LOCKED

| Magnitude | Default pill | Hover expansion |
|-----------|--------------|-----------------|
| `\|Δ\| < $10k` | (no pay pill — fails priority gate) | n/a |
| `$10k ≤ \|Δ\| < $100k` | `+$24k` (round to nearest 1k) | `+$24,300` (full $) |
| `\|Δ\| ≥ $100k` | `+$120k` (round to nearest 1k) | `+$118,400` (full $) |

Pay pills always show sign (`+` or `-`). Default uses k-rounded for the at-a-glance read; hover gives the precise figure for the curious.

#### State coverage — LOCKED

| State | Pill behavior |
|-------|--------------|
| Default | Visible at fitView zoom and at 1.0x. Same colors, same size, same opacity. |
| Edge hidden by filter | Pill hidden with the edge (React Flow handles via parent edge `hidden`). |
| Edge has null delta after priority chain | No pill rendered. The edge breathes alone. |
| Selected-adjacent edges (parent edge of selected node, or child edges *from* selected node) | Pill `--shadow-glow-thrive` if improvement, `--shadow-glow-info` if neutral. Subtle 1.04 scale. Spring: `springs.snappy`. |
| Highlighted via BranchHighlightDriver / tour chip flash | Same selected-adjacent treatment for the duration of the flash window. |
| `prefers-reduced-motion: reduce` | Hover swaps content instantly (no width spring); selected-adjacent omits the scale, keeps the glow. |

#### Reduced-motion fallback — LOCKED

`@media (prefers-reduced-motion: reduce)` toggles a CSS class that:
- Removes the layout-spring on hover expansion (snap to expanded width)
- Removes the 1.04 scale on selected-adjacent
- Keeps the glow (it's a static shadow, not animation)

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Improvement bg | `rgba(125, 212, 163, 0.15)` (= thrive @ 15%, matches `pill-thrive` baseline) |
| Improvement border | `rgba(125, 212, 163, 0.32)` |
| Improvement text | `--color-accent-thrive` |
| Neutral bg | `rgba(45, 48, 96, 0.85)` (= bg-surface @ 85%) |
| Neutral border | `--color-border-subtle` |
| Neutral text | `--color-text-secondary` |
| Default shadow | `--shadow-sm` |
| Hover shadow | `--shadow-md` |
| Adjacent glow (improvement) | `--shadow-glow-thrive` |
| Adjacent glow (neutral) | `--shadow-glow-info` |
| Font | `--font-data` |
| Spring | `springs.snappy` |
| Radius | `--radius-full` |

### T1.2 — Canned "Show me the path that…" tours

**Status:** LOCKED (visionary 2026-05-01 — copy LOCKED by @fp-copywriter 2026-05-01, see Copy Bundle at end of §3)

**Emotional target:** *"Show me what's possible — but show me, don't make me filter."* The tour chips are guided binoculars. Tap one and three nodes in the tree flare like fireflies, then settle. Nothing reshapes, nothing hides. The student gets a pointed answer to a pointed question without losing their map.

**Scope:** 4 chips in a single row above the tree, visually distinct from the constraint and improves filter rows. Silent flash via `BranchHighlightDriver` — no Gemma narration. Active for the ~1.4s flash window, idle the rest of the time.

#### Chips — LOCKED structure (copy via copywriter)

| Chip ID | Label key | Ranking function |
|---------|-----------|------------------|
| `highest_ceiling` | `future.tour.highestCeiling` → "Highest pay" | Top 3 nodes by `median_wage` desc |
| `ai_resilient` | `future.tour.aiResilient` → "Survives AI" | Top 3 by `res` desc, tiebreak `median_wage` desc |
| `fastest_to_mid` | `future.tour.fastestToMid` → "Fastest to mid" | Top 3 by `experience_tier` asc (entry < early < mid < senior), tiebreak `relatedness` asc |
| `biggest_pay_jump` | `future.tour.biggestPayJump` → "Biggest raise" | Top 3 by `(median_wage − root.median_wage)` desc |

#### Visual treatment — distinct from filter chips

The two existing filter rows already use `accent-info` (education) and `accent-thrive` (stat). To prevent confusion, tour chips use a **third visual class**: insight-tinted, with a leading `✦` glyph (the same sparkle motif as the brand wordmark / Gemma).

```
shape:           rounded-full (--radius-full)
padding:         8px 14px           ← slightly tighter than filter chips (10px 18px) so the row reads as one band
height:          ~32px
gap from glyph:  6px
font-family:     --font-body (Nunito)
font-size:       --text-small (14px)
font-weight:     700                ← heavier than filter chips' 600 — these are actions
```

| State | Background | Border | Text + glyph | Shadow |
|-------|-----------|--------|--------------|--------|
| **idle** | `rgba(184, 169, 232, 0.08)` (insight @ 8%) | `rgba(184, 169, 232, 0.22)` | `--color-accent-insight` | none |
| **hover** | `rgba(184, 169, 232, 0.14)` | `rgba(184, 169, 232, 0.36)` | `--color-text-primary` (text); glyph stays insight | `--shadow-glow-insight` (subtle) |
| **active** (during 1.4s flash) | `rgba(184, 169, 232, 0.22)` | `--color-accent-insight` (full) | `--color-text-primary` | `--shadow-glow-insight` (full) — pulses 2x |
| **empty-result** (0 nodes match) | same as idle | `--color-border-subtle` | `--color-text-muted` | none — chip looks dimmed |
| **disabled / loading-tree** | `--color-state-disabled` | `--color-border-subtle` | `--color-text-muted` | none |

The glyph: `✦` (U+2726) at the same size as the label, color `--color-accent-insight`. This is the **only** chip family in the screen with a leading glyph — the visual signal that says "this is an action, not a filter toggle."

#### Active-state animation — LOCKED

The flash window is the BranchHighlightDriver's: 3 nodes × ~600ms each, staggered 100ms (`stagger.slow`) = ~1.4s total. The chip itself runs a parallel "I'm working" animation:

```ts
// Framer Motion variants
const tourChipActive = {
  initial: { boxShadow: "0 0 0 rgba(184, 169, 232, 0)" },
  animate: {
    boxShadow: [
      "0 0 0 rgba(184, 169, 232, 0)",
      "0 0 24px rgba(184, 169, 232, 0.45)",
      "0 0 12px rgba(184, 169, 232, 0.30)",
      "0 0 24px rgba(184, 169, 232, 0.45)",
      "0 0 0 rgba(184, 169, 232, 0)",
    ],
    transition: { duration: 1.4, times: [0, 0.15, 0.5, 0.85, 1], ease: "easeInOut" },
  },
};
```

Two breathing pulses synced to the highlight stagger. After 1.4s the chip returns to idle. Re-tap during the active window restarts the timer (no debouncing — it's a wand).

`prefers-reduced-motion: reduce`: omit the keyframe pulse; instead toggle `--shadow-glow-insight` for the duration as a static glow.

#### Row layout — LOCKED

```
container:       flex flex-wrap items-center gap-2
spacing above:   --space-3 (12px) below the breadcrumb (T1.4)
spacing below:   --space-4 (16px) above the constraint filter row (T2.1 row 1)
border-top:      none
prefix label:    NONE — the chips themselves carry their meaning via the ✦ glyph
```

No "TOURS" prefix label. The filter rows use prefix labels because their chips read as adjectives ("Bachelor's", "Earnings"); the tour chips read as full questions and don't need framing.

**Wrapping:** chips wrap to a second row at narrow widths via `flex-wrap`. On mobile (≤480px) the chip set scrolls horizontally inside `overflow-x: auto` with `scroll-snap-type: x mandatory` — preserves single-row presence and prevents the prelude from eating tree height.

#### Empty-result tooltip — LOCKED

When a chip's ranking returns 0 matches (e.g., `fastest_to_mid` and every node is `senior`):

- Chip renders in **empty-result** visual state above
- `aria-disabled="true"` (still focusable — see Chips spec)
- Tooltip on hover/focus: `future.tour.empty` → "No paths qualify"
- Click does nothing; no flash fires
- Tooltip uses the existing tooltip primitive: `--color-bg-raised` background, `--color-text-primary`, `--text-small`, `--shadow-md`, 200ms fade in via `transitions.fade`

#### State coverage

| State | Treatment |
|-------|-----------|
| Tree loading | All chips `disabled` |
| Tree loaded, root only (no branches) | All chips `empty-result` |
| Picked node ≠ null while flashing | Selection persists; flash highlights nodes per ranking but does NOT change selection |
| Filter active that hides matching nodes | Ranking still computes against the unfiltered tree; flash targets nodes that may currently be hidden — the flash fires on the hidden nodes' positions and the BranchHighlightDriver's existing behavior governs visibility (no special handling needed in this spec) |

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Idle bg | `rgba(184, 169, 232, 0.08)` (insight @ 8%) |
| Idle border | `rgba(184, 169, 232, 0.22)` |
| Hover bg | `rgba(184, 169, 232, 0.14)` |
| Active bg | `rgba(184, 169, 232, 0.22)` |
| Text + glyph (idle) | `--color-accent-insight` |
| Text (hover/active) | `--color-text-primary` |
| Empty bg | `rgba(184, 169, 232, 0.08)` |
| Empty text | `--color-text-muted` |
| Disabled bg | `--color-state-disabled` |
| Glow | `--shadow-glow-insight` |
| Font | `--font-body` weight 700 |
| Glyph | `✦` (U+2726) |
| Spacing above | `--space-3` |
| Spacing below | `--space-4` |
| Stagger | `stagger.slow` |

### T1.3 — Mini-compare delta strip on SelectedNodeCard

**Status:** LOCKED (visionary 2026-05-01)

**Emotional target:** *"How much better off am I — actually?"* The delta strip is the punchline of selection. The student picks a node and the card answers in three crisp lines: pay, AI resilience, growth — relative to where they are now. No charts, no qualifiers. Just numbers with arrows. The math is doing the rhetoric.

**Scope:** When `picked === true` AND `selected.soc !== root.soc`, render a 3-row delta strip at the top of the SelectedNodeCard, above the existing stat bars. Per-row math: `selected.<stat> − root.<stat>` for `median_wage`, `res`, `grw`.

#### Layout — LOCKED

```
┌────────────────────────────────────────────────┐
│ [icon] Sales Managers                          │
│        Bachelor's degree                       │
│                                                │
│ ┌─ COMPARED TO ADVERTISING & PROMOTIONS ────┐  │  ← strip container
│ │  Pay         ▲  +$11k                     │  │
│ │  AI res      ▲  +2                        │  │
│ │  Growth      ▼  −1                        │  │
│ └────────────────────────────────────────────┘  │
│                                                │
│ ROI bar / RES bar / GRW bar / HMN bar          │  ← existing card body
└────────────────────────────────────────────────┘
```

The strip is its own surface — a `bg-deep` block tucked inside the `bg-mid` card. That nesting reads as "this is meta-information about the card, not the card itself."

#### Strip container — LOCKED

```
margin-top:      --space-4 (16px below the title block)
margin-bottom:   --space-5 (20px above the existing stat bars)
padding:         12px 14px         ← --space-3 vertical, slightly tighter horizontal
background:      --color-bg-deep
border:          1px solid --color-border-subtle
border-radius:   --radius-lg (14px)
```

#### Header — LOCKED

```
text:            "COMPARED TO {root.title.toUpperCase()}"   ← copy key future.compare.header → "Compared to {career}" (uppercased by code)
                 narrow viewport (<480px): future.compare.headerShort → "Vs. {career}" (uppercased by code)
font-family:     --font-data (Space Mono)
font-size:       11px
font-weight:     700
letter-spacing:  1.5px
color:           --color-accent-info
margin-bottom:   --space-3 (12px)
```

This matches the existing **Section Labels** pattern (DESIGN.md line 1108–1120) — the same uppercase data-mono treatment used throughout the product. `accent-info` (not muted) signals "this is meta-data context, not chrome."

The root.title is uppercased programmatically. If `root.title.length > 28 chars`, truncate with ellipsis at 28 — keeps the header on a single line at card width (~340px). The full root.title is already visible in the breadcrumb above.

#### Delta rows — LOCKED

Each row is a 3-column flex layout:

| Column | Width | Content |
|--------|-------|---------|
| Stat label | `flex: 0 0 88px` | "Pay" / "AI res" / "Growth" — `font-body`, `text-small` (14px), weight 600, `--color-text-secondary` |
| Arrow glyph | `flex: 0 0 18px` (centered) | `▲` (U+25B2) up / `▼` (U+25BC) down / `▬` (U+25AC) flat — `font-data`, 13px, color per direction below |
| Delta value | `flex: 1` (left-aligned, no truncation) | `+$11k` / `+2` / `−1` — `font-data`, `--text-data-sm` (13px), weight 700, color per direction below |

Row gap: `--space-2` (8px) between rows. No row dividers — the typographic rhythm carries the structure.

#### Arrow glyphs + colors — LOCKED

| Direction | Glyph | Color | Reading |
|-----------|-------|-------|---------|
| Improvement | `▲` | `--color-accent-thrive` | Pay up; AI res up; Growth up |
| Regression | `▼` | `--color-text-muted` | Pay down; AI res down; Growth down |
| Flat (delta == 0) | `▬` | `--color-text-muted` | Hidden by default if all three are flat (rare; row stays hidden if exactly 0); shown if mixed with non-flat siblings |

**Per the spec's note on "growth-down vs pay-down":** they read differently in the world (growth-down might mean a more stable, mature field; pay-down might mean a deliberate values-trade), but in the strip they share the same neutral muted color. This is intentional consistency with T1.1's two-color rule. The card's own copy and the chat layer are where contextual nuance lives. The strip is the math; the words around it carry the temperature.

The minus sign on regression values is `−` (U+2212 minus sign), not `-` (U+002D hyphen) — it aligns vertically with `+` in Space Mono.

#### Pay formatting — LOCKED

The pay delta uses the **k-rounded** form by default, matching T1.1's pill formatting for visual cohesion across the screen.

| Magnitude | Display |
|-----------|---------|
| `\|Δ\| < $1,000` | `+$0k` is too imprecise — show `+${Δ}` exact (`+$420`) |
| `$1,000 ≤ \|Δ\| < $1,000,000` | `+$11k` (round to nearest 1k) |
| `\|Δ\| ≥ $1,000,000` | `+$1.2m` (one decimal place; rare-but-possible for "Surgeons" branches) |

The exact $-figure is **not** shown on hover here (unlike T1.1) because the SelectedNodeCard already shows the absolute median wage in the title block — the student can compute the exact delta if they care. Keeping the strip free of hover cuts cognitive load.

#### Stat deltas — LOCKED

`res` and `grw` are integer 0..10 scales already on TreeNode. Display: `+N` / `−N` / `0` (with `▬` glyph). Always show the sign for non-zero deltas.

#### Null-handling — LOCKED

```
For each row independently:
  if (selected.<stat> === null || root.<stat> === null) → hide that row
If all three rows hidden → hide the strip + header entirely (no empty container)
```

Per-row hiding (not all-or-nothing) is a deliberate revision from the original spec ("hide entire if any stat is null"). Real data: pay is reliably present; `res`/`grw` may be null on stretch branches. Hiding the whole strip because one stat is unknown loses the two known signals.

If only the strip header survives a render (rare: all three rows null but `picked` is true), suppress the header too. The card falls back to showing the stat bars alone — clean degradation.

#### Selected = root case — LOCKED

The strip + header do not render when `selected.soc === root.soc`. The breadcrumb (T1.4) collapses to just `[Root]`, the card shows the root's stats without comparison framing. No "compared to itself" infinite-loop visual.

#### Animation — LOCKED

```
On mount (when card first appears with delta strip):
  Strip container:       opacity 0 → 1, y: 8 → 0    (springs.smooth, delay 0.08s after card body)
  Each row:              opacity 0 → 1, x: -4 → 0   (springs.snappy, stagger 50ms — stagger.fast)
On stat changes (rare — only if root build mutates):
  Numbers tween via Framer Motion's number animation, 400ms easeOut
prefers-reduced-motion:  no entry animation (opacity flip only); no number tween (snap)
```

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Strip bg | `--color-bg-deep` |
| Strip border | `--color-border-subtle` |
| Strip radius | `--radius-lg` |
| Header text | `--color-accent-info` |
| Header font | `--font-data` 11px / 700 / 1.5px tracking — matches Section Labels |
| Stat label color | `--color-text-secondary` |
| Stat label font | `--font-body` `--text-small` weight 600 |
| Improvement arrow + value | `--color-accent-thrive` |
| Regression / flat arrow + value | `--color-text-muted` |
| Value font | `--font-data` `--text-data-sm` weight 700 |
| Row gap | `--space-2` |
| Outer top spacing | `--space-4` |
| Outer bottom spacing | `--space-5` |
| Entry spring | `springs.smooth` (container), `springs.snappy` (rows) |
| Stagger | `stagger.fast` |

### T1.4 — Selection persistence + breadcrumb

**Status:** LOCKED (visionary 2026-05-01 — copy LOCKED by @fp-copywriter 2026-05-01, see Copy Bundle at end of §3)

**Emotional target:** *"I know where I am, and one click puts me back."* The breadcrumb is the student's anchor line. As they wander deeper into the tree it grows. When a filter hides what they were just looking at, it doesn't snap away — it ghosts, and the student knows: "your selection is still here, the filter is just hiding the node." It's the difference between feeling lost and feeling guided.

**Scope:** Single-line breadcrumb above the tree (between the tour chips T1.2 and the constraint filter row T2.1 row 1). Renders only when selection depth ≥ 1 (root-only state hides the breadcrumb to recover vertical space). Each segment clickable. Hidden-by-filter segments render in ghost state but stay clickable.

#### Layout — LOCKED

```
container:       flex flex-row items-center gap-1
margin-top:      --space-3 (12px below tour chips)
margin-bottom:   --space-3 (12px above constraint filter row)
height:          ~24px (single line, no wrapping)
overflow:        ellipsis at container level if rare overflow
```

```
[Your career]  ›  [Advertising & Promo…]  ›  [Sales Managers]
```

#### Segment chip — LOCKED

Each segment is a button styled as a low-affordance breadcrumb chip — distinct from the filter chips so the row never reads as another filter rail.

```
shape:           rounded-md (--radius-md, 10px) — not full-pill, distinct from filters
padding:         4px 10px
font-family:     --font-body (Nunito)
font-size:       --text-small (14px)
font-weight:     600
white-space:     nowrap
max-width:       enforced by truncation (see below)
border:          none
background:      transparent
color:           --color-text-secondary
transition:      colors fast
```

#### Segment states — LOCKED

| State | Background | Text | Notes |
|-------|-----------|------|-------|
| **idle** | transparent | `--color-text-secondary` | Default for any non-current, visible segment |
| **current** (deepest selected) | `rgba(125, 212, 163, 0.10)` (= `--color-state-active`) | `--color-accent-thrive` | The "you are here" segment. Subtle thrive wash. |
| **hover** | `rgba(255, 255, 255, 0.04)` | `--color-text-primary` | Same hover treatment as a ghost chip |
| **ghost** (segment hidden by filter) | transparent | `--color-text-muted` + `text-decoration: line-through` | Stays clickable; hover shows tooltip |
| **focus-visible** | adds 2px ring `--color-focus-ring` | unchanged | Standard focus pattern |

#### Separator glyph — LOCKED

```
glyph:           ›  (U+203A — single right-pointing angle quote)
font-family:     --font-data
font-size:       14px
color:           --color-text-muted
margin:          0 (the gap-1 on the container provides the spacing)
opacity:         0.5
pointer-events:  none
aria-hidden:     true
```

The single angle quote is friendlier than the chevron `>` (too geometric) and less heavy than `→` (reads as causation, not navigation). Brightpath separator-of-record.

#### Truncation rules — LOCKED

| Viewport | Per-segment max chars | Ellipsis | Tooltip on truncated |
|----------|----------------------|----------|----------------------|
| Desktop (≥768px) | 24 | yes (`…`) | yes — full title via `title` attr |
| Mobile (<768px) | 16 | yes | yes |

Truncation runs per segment, not per row. If two segments both want 24 chars on a 360px viewport, the row may overflow — handled by `text-overflow: ellipsis` at the container level for the rare overflow. The breadcrumb is allowed to truncate the *root* segment's chip first because the root copy `future.breadcrumb.root` ("Your career") is the most stable anchor and easiest to recognize from a few characters.

#### Click behavior — LOCKED

| Click target | Effect |
|--------------|--------|
| Root segment | Sets `selectedNodeId = null` → chat scope returns to root context |
| L1 segment (visible) | Sets `selectedNodeId = L1.soc` |
| L2 segment (visible) | Already current — no state change; subtle press feedback only |
| Any segment in **ghost** state | Click attempts re-select: state setter is called with the segment's soc. If the node is filter-hidden, FutureScreen's existing reconciliation drops it again. **Net effect:** click feels like a no-op because the filter is the gate. The tooltip is the explanation. |

#### Ghost-state tooltip — LOCKED

```
trigger:         pointer hover or keyboard focus on a ghost segment
content:         future.breadcrumb.hiddenTooltip → "Hidden by filter. Clear filters to see."
delay:           400ms hover delay; instant on focus
container:       absolute, positioned below the segment
                 background: --color-bg-raised
                 border: 1px solid --color-border-default
                 border-radius: --radius-md
                 padding: 6px 10px
                 font: --font-body --text-small 400 --color-text-primary
                 max-width: 240px
                 box-shadow: --shadow-md
                 z-index: above the tree pane
animation:       opacity 0 → 1 + y: 4 → 0, --transition-fast (150ms ease-out)
```

The tooltip uses the existing tooltip primitive — no new component. Intentional — the breadcrumb is supposed to feel like a familiar piece of chrome, not a special-cased thing.

#### Animation — LOCKED

```
Segment append (when selection goes deeper):
  opacity 0 → 1, x: -8 → 0
  springs.snappy (stiffness: 400, damping: 25)
  Separator before it: same spring, 60ms behind

Segment remove (when selection retreats or root-click):
  opacity 1 → 0, x: -8
  --transition-fast (150ms ease-out) — quick exit, no spring

Idle → ghost (filter hides current):
  opacity 1 → 0.5 with cross-fade to muted color
  --transition-normal (200ms ease-out)

Ghost → idle (filter cleared):
  Reverse of above

prefers-reduced-motion: instant state swaps, opacity-only, no springs
```

The breadcrumb growing as the student goes deeper is a **directly perceptible signal of progress**. Spring physics on append gives it the "click → just-arrived" feel. Don't make this a CSS transition — it has to feel placed, not faded in.

#### State machine — LOCKED

```
Source of truth:    FutureScreen state — selectedNodeId, plus a derived breadcrumbPath
breadcrumbPath:     computed from `findPathToNode(tree, selectedNodeId)` — array of {soc, title}
                    Persists in component state across filter changes by snapshotting
                    the path at last successful selection. Cleared on root-click or
                    when selection moves to a sibling at the same level.
Filter-hidden:      a derived flag per segment: `isHiddenByFilter(filteredTree, segment.soc)`
```

The breadcrumb cache survives filter changes — that's the whole point. It does NOT survive a *new selection* (a click on a different visible node), which resets the path to that node's lineage. This matches the §2 Decision 5 (selection drops in actual state but persists in breadcrumb when filter hides).

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Idle text | `--color-text-secondary` |
| Current bg | `--color-state-active` |
| Current text | `--color-accent-thrive` |
| Hover bg | `rgba(255, 255, 255, 0.04)` (matches ghost-chip hover) |
| Hover text | `--color-text-primary` |
| Ghost text | `--color-text-muted` |
| Focus ring | `--color-focus-ring` |
| Separator | `›` (U+203A), `--color-text-muted` @ 0.5 opacity |
| Tooltip bg | `--color-bg-raised` |
| Tooltip border | `--color-border-default` |
| Tooltip shadow | `--shadow-md` |
| Font | `--font-body` `--text-small` weight 600 |
| Radius | `--radius-md` |
| Spring | `springs.snappy` |

### T2.1 — Boss-outcome filter row "SURVIVES"

**Status:** LOCKED (visionary 2026-05-01 — copy LOCKED by @fp-copywriter 2026-05-01, see Copy Bundle at end of §3)

**Emotional target:** *"Show me paths I can actually survive."* The SURVIVES chips close the loop with the gauntlet. The student fought five bosses; now the same bosses become filters here. The filter row reads like a sentence: *Show only paths that are Bachelor's, that survive AI, that survive burnout.* Constraints stack as one cohesive question.

**Scope:** Two-row filter rail. Per §11 resolution and the locked decision in §2. Row 1 carries constraints (CAN you take this path?); Row 2 carries improvements (DOES this path improve on where you are?). Copy keys are placeholders.

#### Row 1 — CONSTRAINTS — LOCKED

```
container:       flex flex-wrap items-center gap-2
prefix label:    future.filter.label → "Show only" (existing key, uppercased by code)
                 [3 education chips]
divider:          ·                             ← see "Divider treatment" below
prefix label:    future.survives.label → "Survives" (uppercased by code)
                 [3 boss chips]
```

Row 1 chips reuse the **existing FilterChip pattern** from `EducationFilterRow.tsx` / `StatFilterRow.tsx` — same shape, same spacing, same border/text/bg formula. Only the active accent color changes per group, which is how the student already learns to read the rail.

| Chip group | Idle | Active |
|------------|------|--------|
| Education (existing, unchanged) | `bg-bp-surface` / `border-border-subtle` / `text-text-secondary` | `bg-accent-info/15` / `border-accent-info` / `text-accent-info` |
| **SURVIVES (new — boss)** | `bg-bp-surface` / `border-border-subtle` / `text-text-secondary` | `bg-accent-caution/15` / `border-accent-caution` / `text-accent-caution` |

`accent-caution` for SURVIVES because it is the gauntlet's "draw" color (DESIGN.md line 622) — the chip color reads as "this is the survival/threat axis." NOT thrive (already used for IMPROVES) and NOT info (already used for SHOW ONLY). The three chip rows now have three distinct accent identities — the student's eye can sort the rail at a glance.

#### SURVIVES chip set — LOCKED (3 chips per data-reviewer trim)

| Chip ID | Label key | Boss field | Boss accent (DESIGN.md L77-83, NOT used for chip — informational only) |
|---------|-----------|-----------|------------------|
| `boss_ai` | `future.survives.ai` → "Survives AI" | `boss_ai` | `--color-boss-ai` (insight purple) |
| `boss_market` | `future.survives.market` → "Survives market" | `boss_market` | `--color-boss-market` (info ice blue) |
| `boss_burnout` | `future.survives.burnout` → "Survives burnout" | `boss_burnout` | `--color-boss-burnout` (empathy pink) |

All three chips share the **caution active color** above for visual cohesion as a row group. The per-boss accent colors are NOT used here — using all five boss colors as chip accents would scatter the eye and conflict with the gauntlet screen's color contract. The chip's caution color says "survive"; the chip's label says "what."

#### Divider treatment between SHOW ONLY and SURVIVES — LOCKED

After evaluating three options (vertical rule, extra gap, prefix-only), the locked treatment is **prefix-label-only with extra gap** — no rule.

```
gap between groups:     --space-5 (20px) — twice the within-group gap of --space-2 (8px)
visual divider glyph:   none
prefix label glyph:     none
```

Rationale:
- A vertical rule (1px hairline) reads as "two separate UI components" — the rail should read as one rail with two clauses, not two rails crammed together.
- A `·` glyph between groups was tested and reads as ornamental noise; the prefix labels already carry the grouping.
- Pure extra gap is the lightest possible separator and lets the prefix labels do the semantic work. The `--space-5` gap (vs. `--space-2` within a group) is enough that the eye groups correctly without explicit chrome.

#### Prefix labels — LOCKED

Both prefix labels reuse the **existing pattern** from `EducationFilterRow.tsx`:

```
font-family:     --font-data
font-size:       10px
font-weight:     normal (Space Mono 400)
text-transform:  uppercase
letter-spacing:  wider (Tailwind tracking-wider, ~0.05em)
color:           --color-text-muted
margin-right:    --space-1 (4px)
```

Identical typography across SHOW ONLY, SURVIVES, IMPROVES — only the chip colors carry the grouping. Locked to match existing code; do not invent a new label treatment.

#### Row 2 — IMPROVES — LOCKED (existing, unchanged)

The existing `StatFilterRow.tsx` ships as-is. The visionary's only ask here: row 2 is its own flex row, separated from row 1 by `--space-3` (12px). No row 2 visual changes.

#### Wrapping behavior — LOCKED

| Viewport | Row 1 behavior |
|----------|----------------|
| Desktop (≥1200px) | All 6 chips + 2 prefix labels render on a single line |
| Tablet (768–1199px) | `flex-wrap` allows the SURVIVES group to wrap to a second line of row 1 — prefix label stays with its group via grouping wrapper |
| Mobile (<768px) | Each group becomes its own implicit line (the gap-5 + flex-wrap accomplishes this naturally because the chip widths force overflow); the rail reads as a stack |

To make wrapping group-aware, **wrap each group in its own `flex` container** within the outer flex-wrap:

```tsx
<div className="flex flex-wrap items-center gap-x-5 gap-y-3">
  <div className="flex flex-wrap items-center gap-2">  {/* SHOW ONLY group */}
    <span className="…prefix-label…">SHOW ONLY</span>
    {educationChips}
  </div>
  <div className="flex flex-wrap items-center gap-2">  {/* SURVIVES group */}
    <span className="…prefix-label…">SURVIVES</span>
    {bossChips}
  </div>
</div>
```

The outer container's `gap-x-5 gap-y-3` keeps `--space-5` between groups horizontally and `--space-3` between wrapped lines vertically — clean wrapping without breaking the prefix-label-to-chips bond.

#### Empty state — LOCKED

When SURVIVES filter set is non-empty AND filtered tree has 0 visible non-root nodes (architect's flagged edge case where root itself fails a boss):

- Tree pane renders the existing empty-state component (no special handling needed)
- The active SURVIVES chips stay in their active visual state — the student can see exactly which constraints to relax
- No additional copy or banner from the chip row itself

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Education chip active | `bg-accent-info/15` / `border-accent-info` / `text-accent-info` (existing) |
| SURVIVES chip active | `bg-accent-caution/15` / `border-accent-caution` / `text-accent-caution` (NEW — first use of caution as a chip variant) |
| Idle chip | `bg-bp-surface` / `border-border-subtle` / `text-text-secondary` (existing) |
| Hover idle | `text-text-primary` / `border-border-default` (existing) |
| Prefix label | `--font-data` 10px / `--color-text-muted` / wider tracking (existing) |
| Within-group gap | `--space-2` (8px) |
| Between-group gap | `--space-5` (20px) |
| Between-row gap | `--space-3` (12px) |
| Focus ring | `--color-focus-ring` |
| Transition | `--transition-normal` (colors) |

### T2.2 — Relatedness gradient on edges

**Status:** LOCKED (visionary 2026-05-01, anchored to rank 1..20 per @fp-data-reviewer)

**Emotional target:** *"The closer the path, the bolder the line. The further the leap, the more the line whispers."* The relatedness gradient encodes the *grain* of the tree — which branches are short hops, which are bold pivots. Without this, every edge looks equally easy. With this, the student can read the tree the way a pilot reads a sectional chart: thick lines are the highways; thin lines are the bushwhacks.

**Scope:** Encode `child.relatedness` (rank 1..20, 1 = closest) onto each edge's stroke via **both** stroke-width and opacity. Combined-axis (not one or the other). Anchored to the rank 1..20 domain confirmed by @fp-data-reviewer. Edge labels (T1.1) keep constant text emphasis regardless.

#### Combined-axis encoding — LOCKED

Both axes carry the gradient because either alone is too subtle:
- Width-only is hard to read at fitView zoom (0.5 px diff disappears).
- Opacity-only loses thrust on the dark backdrop (faint colored line on near-black).
- Combined gives a clear visual hierarchy at every zoom — the close branches feel *built*, the stretch branches feel *suggested*.

#### Linear scale — LOCKED

```
domain:                      rank ∈ [1, 20]   (1 = closest, 20 = stretch ceiling)
clamp:                       outside [1, 20] → clamped to nearest end
null relatedness:            treated as rank 20 (most translucent / thinnest end)
                             — per architect's recommendation. Honest "we don't know" reads
                             as "assume distant" rather than NaN-ing into default styling.

Root → Career edge (the L1 edges):
  strokeWidth:   3.2px  at rank 1   →  1.4px  at rank 20    (current baseline: 2.0px)
  opacity:       0.95   at rank 1   →  0.40   at rank 20    (current baseline: 0.80)

Career → Endpoint edge (the L2 edges):
  strokeWidth:   2.4px  at rank 1   →  0.8px  at rank 20    (current baseline: 1.5px)
  opacity:       0.80   at rank 1   →  0.28   at rank 20    (current baseline: 0.50)
```

The midpoint of each scale lands close to the existing baseline (rank ~10 produces near-current visuals). This means existing trees won't look dramatically different on average — the *spread* is what's new. A tree with mostly close branches looks denser and more confident than today; a tree of mostly stretches looks more spacious and tentative. **Both correctly reflect what the student is looking at.**

L2 edges are scaled tighter than L1 because they already render thinner — preserving the L1-vs-L2 hierarchy that the existing layout depends on.

#### Computation — LOCKED

```ts
function relatednessStyle(
  rank: number | null,
  level: "root-career" | "career-endpoint",
  branchColor: string
): CSSProperties {
  const r = Math.max(1, Math.min(20, rank ?? 20));
  const t = (r - 1) / 19;  // 0 at rank 1, 1 at rank 20

  const ranges = level === "root-career"
    ? { wMax: 3.2, wMin: 1.4, oMax: 0.95, oMin: 0.40 }
    : { wMax: 2.4, wMin: 0.8, oMax: 0.80, oMin: 0.28 };

  return {
    stroke: branchColor,
    strokeWidth: ranges.wMax + (ranges.wMin - ranges.wMax) * t,
    opacity:     ranges.oMax + (ranges.oMin - ranges.oMax) * t,
  };
}
```

Linear interpolation. No log/quadratic curve — the rank distribution is already roughly linear within the 1..20 domain (per data-reviewer), and a linear visual map preserves the rank's intuitive meaning ("rank 5 looks twice as bold as rank 10" reads correctly).

#### Interaction with T1.1 edge labels — LOCKED

**The pill always reads at full emphasis regardless of edge faintness.** The pill background is `--color-bg-surface @ 85%` (neutral) or `accent-thrive @ 15%` (improvement) with `backdrop-filter: blur(4px)`. Both fills paint over the edge stroke entirely. Text emphasis is never tied to edge style.

This was the architect's primary concern (called out in §5 finding) and is now structurally guaranteed by T1.1's pill geometry — not a separate enforcement.

#### Interaction with selection/highlight — LOCKED

When an edge is **selected-adjacent** (parent-of-selected, or child-of-selected) or **highlighted** by BranchHighlightDriver:

```
override:        opacity → 1.0 for the duration of the highlight or while selected
strokeWidth:     no change (the gradient still encodes relatedness;
                 we lift the veil, not the topology)
addition:        edge gains a soft glow filter — the existing selected-edge treatment
                 in reactflow-dark.css continues to apply
```

This means: a stretch (rank 18) edge that's selected does NOT suddenly look like a close (rank 2) edge. It looks like a stretch edge the student is paying attention to. Honest.

#### Filter-hidden edges — LOCKED

When an edge is hidden by an active filter (T2.1 boss, education, stat), the edge does not render at all. Relatedness encoding is moot for hidden edges — no special handling.

#### Stretch filter chip — DEFERRED

The original spec mentions an optional "Stretch" filter chip (rank > 10). **Not in this delivery.** Reasoning:
1. The visual gradient already gives the student the "stretch-only" view — they can see the thinnest edges and follow them.
2. Adding a fourth chip group would push the rail back over budget.
3. If post-hackathon usage shows the gradient isn't enough to spot stretches, add the chip then with one click.

Spec §1 success criteria does not include this chip. Deferring is non-blocking.

#### Reduced motion — LOCKED

Stroke width and opacity are static styles — no animation. `prefers-reduced-motion: reduce` has no impact on T2.2.

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Stroke color | existing `branchColor` per branch (already in `treeFlowLayout.ts`) |
| Stroke width | computed in [0.8, 3.2] px — same domain as existing baseline (1.5–2.0) |
| Opacity | computed in [0.28, 0.95] — same domain as existing (0.5–0.8) |
| Selected/highlighted opacity override | `1.0` (already used by existing selected-edge css in `reactflow-dark.css`) |

No new color, no new shadow, no new keyframe. T2.2 is purely a parameterization of existing edge attributes.

**Backend dep:** Requires `relatedness: number | null` on TreeNode. See §4.

### T2.3 — "What it takes" block on SelectedNodeCard

**Status:** LOCKED (visionary 2026-05-01 — copy LOCKED by @fp-copywriter 2026-05-01, see Copy Bundle at end of §3)

**Emotional target:** *"Here's what you'd actually have to do."* The block trades the single educationLabel line for a structured three-line answer to the student's quietest question — *what would I have to become?* Education, experience, and the most-changed stat. Three sentences. The card stops being a profile and becomes a translation.

**Scope:** When `picked === true` AND `selected.soc !== root.soc`, replace the existing single-line `educationLabel` sub-line with a 3-bullet block. Root anchor keeps the existing single-line treatment (no "what it takes to be yourself" infinite loop).

#### Layout — LOCKED

Block sits **below the title block** and **above the mini-compare strip (T1.3)** when both render. The sequence on a fully-populated non-root selected card is:

```
[icon] Sales Managers
       ← title block (existing)

What it takes:
  ↑  Education: Bachelor's → Master's
  ↑  Experience: Entry → Mid-career (~5 yrs)
  ↑  Top stat shift: AI resilience +3
       ← what-it-takes block (T2.3, NEW)

COMPARED TO ADVERTISING & PROMOTIONS
  Pay     ▲  +$11k
  AI res  ▲  +2
  Growth  ▼  −1
       ← mini-compare strip (T1.3)

[ROI bar / RES bar / GRW bar / HMN bar]
       ← stat bars (existing)
```

The order is intentional: **what-it-takes** answers the qualitative question (*what would I have to become*); **mini-compare** answers the quantitative one (*what would change in numbers*); **stat bars** show the absolute state. Qualitative → relative → absolute is the natural reading flow.

#### Block container — LOCKED

```
margin-top:      --space-4 (16px below the title block)
margin-bottom:   --space-4 (16px above the mini-compare strip OR stat bars)
padding:         0                         ← no surface treatment, this is body content
background:      none
border:          none
```

No bordered surface here — that's the strip's job. The bullets read as part of the card body.

#### Title — LOCKED

```
text:            future.whatItTakes.title → "What it takes:"
font-family:     --font-body (Nunito)
font-size:       --text-small (14px)
font-weight:     700
color:           --color-text-primary
margin-bottom:   --space-2 (8px)
letter-spacing:  normal
case:            sentence
```

NOT the uppercase data-mono treatment used by the mini-compare header — that distinction is intentional. The mini-compare header is **section chrome** ("here is comparison data"); the what-it-takes title is a **prose label** ("here is what it takes:"). Sentence-case Nunito reads as a sentence the card is speaking; uppercase Space Mono reads as a column header.

#### Bullets — LOCKED

Three bullets, fixed order: Education → Experience → Top stat shift.

```
list:                        unstyled (no dot, no native list-style)
gap between bullets:         --space-2 (8px)
indent:                      none — content sits flush with title
flex layout per row:         flex flex-row items-baseline gap-2
```

Each bullet row has three parts:

| Part | Style |
|------|-------|
| Glyph | `↑` (U+2191, up arrow) — `font-data` 13px, weight 700, `--color-accent-thrive` (always — see "Glyph rule" below) |
| Inline label | "Education:" / "Experience:" / "Top stat shift:" — `font-body` `--text-small` (14px) weight 600, `--color-text-secondary` |
| Inline value | "Bachelor's → Master's" / "Entry → Mid-career (~5 yrs)" / "AI resilience +3" — `font-body` `--text-small` (14px) weight 400, `--color-text-primary` |

The label and value share the same line, separated by a space (the colon comes after the label per copy convention). The arrow glyph leads the row.

**Why baseline-aligned, not center-aligned:** the `↑` glyph sits visually higher than text-baseline; baseline alignment makes the arrow's tip sit just above the cap-line, which reads as "this is the direction" rather than "this is a bullet point."

#### Glyph rule — LOCKED

The arrow glyph color is **always thrive** (`--color-accent-thrive`) regardless of the actual delta direction. Rationale:

- T2.3 frames "what it takes" as **investment**, not as a delta.
- Even when education is a step *down* (rare but possible — Bachelor's → Associate's via a credential pivot), it's still a thing the student would *do*. Painting that arrow muted would moralize.
- The temperature of the change lives in the mini-compare strip below, where deltas have their proper green/muted treatment. The what-it-takes block is intentionally one-color.

If a future copywriter chooses a non-arrow glyph for visual variety, the rule extends: **all three bullets share one neutral-investment color.** Don't let glyph color split this block into "good change vs. bad change" — the strip already does that work.

#### Per-bullet content rules — LOCKED

| Bullet | Rendered if | Hidden if |
|--------|-------------|-----------|
| Education | `selected.education_level && root.education_level` are both known AND non-equal | Either is null, OR they're equal (no change to communicate) |
| Experience | `selected.experience_tier && root.experience_tier` are both known AND non-equal | Either is null, OR they're equal |
| Top stat shift | At least one of `res / grw / hmn` has `\|Δ\| ≥ 1` | All three deltas are < 1 absolute, OR all three sides are null |

For the "top stat shift" bullet: pick the stat with the **largest absolute delta** across `res`, `grw`, `hmn`. Ties broken in that priority order (res first, grw second, hmn third). Skip `median_wage` and `roi` here — they'd duplicate the mini-compare strip's first row.

The arrow on the top-stat bullet always points up (per the glyph rule) but the value carries the sign: `AI resilience +3` for an increase, `AI resilience −2` for a decrease. The minus-sign character is `−` (U+2212) consistent with T1.3.

#### Empty-state degradation — LOCKED

If all three bullets are hidden (rare — equal education, equal experience, no significant stat shift), the entire block (title + bullets) is suppressed. The card falls back to title block + mini-compare strip + stat bars. Clean degradation, no empty title.

If only one or two bullets render, the title still renders. "What it takes:" preceding a single bullet reads fine — the brevity is honest ("the only thing that changes is X").

#### Root case — LOCKED

When `selected.soc === root.soc` (root anchor), the entire what-it-takes block is suppressed. The original single-line `educationLabel` sub-line continues to render below the title block as it does today. **This is the only location in the spec where the old single-line treatment survives.**

#### Animation — LOCKED

```
On mount:
  Title:                opacity 0 → 1, y: 4 → 0          springs.smooth, no delay
  Each bullet:          opacity 0 → 1, x: -6 → 0         springs.snappy, stagger 60ms

On selection change (existing card, new node):
  Title persists; bullets cross-fade content — 200ms opacity flip via --transition-normal
  (avoids a re-stagger every click, which would feel jittery on a fast-clicking student)

prefers-reduced-motion: opacity-only, no springs, no stagger
```

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Title color | `--color-text-primary` |
| Title font | `--font-body` `--text-small` weight 700 |
| Bullet glyph color | `--color-accent-thrive` (always) |
| Bullet glyph font | `--font-data` 13px weight 700 |
| Bullet label color | `--color-text-secondary` |
| Bullet value color | `--color-text-primary` |
| Bullet label/value font | `--font-body` `--text-small` |
| Bullet gap | `--space-2` |
| Block top spacing | `--space-4` |
| Block bottom spacing | `--space-4` |
| Entry spring | `springs.smooth` (title) / `springs.snappy` (bullets) |
| Stagger | 60ms (between `stagger.fast` 50ms and `stagger.normal` 80ms — derived for 3-item list) |

### T2.4 — "Make this my path" CTA — **CUT (post-hackathon)**

**Status:** CUT — see §10 and §11 resolution.

**Why cut:** Most complex single feature in the spec. Atomic re-root requires a new backend endpoint (other approaches drift state). Value is "behavior change," not "decision support" — neither needed for the May 18 minimum-shippable subset. Risk-to-deadline ratio is the worst in the spec. Park as standalone post-hackathon spec.

Original scope preserved here for the future spec author:

- When `picked === true` on a non-root node, render a secondary CTA at the bottom of the SelectedNodeCard: "Make this my path."
- Click → re-roots the build to that SOC. Approaches considered: (a) new `POST /build/{id}/reroot` endpoint, (b) client-side refetch only, (c) reuse `/build/create` with target SOC.
- Author recommendation when picked back up: approach (a) for transactional cleanliness — chat scope, build identity, stat baseline all switch atomically.
- Consider also: a "Path history" breadcrumb showing the chain of re-roots once shipped.

### T3.1 — Stage axis labels

**Status:** LOCKED (visionary 2026-05-01)

**Emotional target:** *"This isn't a graph. It's the next decade of my life."* The three stage labels — "Now," "Next move," "Move after" — reframe the tree as a sequence in time, not a topology. They sit ghosted into the canvas like watermarks on a map. Once the student reads them they can't un-see them: the leftmost column is who they are now; the middle column is the choice in front of them; the right column is what comes after the choice. A graph becomes a journey.

**Scope:** Three large display-font labels overlaid on the tree pane at the three rank-axis x-positions (root, career, endpoint). Ghost-style — very low opacity, sit behind the tree's nodes and edges. Always horizontal at the top of the pane — they do NOT follow the staircase diagonal. Hidden on mobile.

#### Position math — LOCKED

The labels anchor to **horizontal x-positions only** at the **top** of the tree pane. They do not follow the staircase tilt of the rank axis — that was tested and reads as wobbly chrome. Top-horizontal reads as coordinate axis labels, which is exactly the metaphor we want.

```
container:                absolute layer above the React Flow viewport, below all nodes/edges
                          (z-index between viewport background and node z-stack)
height:                   matches the tree pane height
pointer-events:           none (entire layer is decorative)
overflow:                 visible (labels may bleed slightly above the pane top edge)

label x-positions:        anchored to React Flow world-space x-coordinates of the three rank tiers,
                          translated through the React Flow viewport transform so labels track
                          pan/zoom along x
                            x_now        = world x of root node center
                            x_nextMove   = world x of L1 (career) node centers (column average)
                            x_moveAfter  = world x of L2 (endpoint) node centers (column average)

label y-position:         fixed at top of the pane:  top: --space-4 (16px from pane top)
                          — does NOT translate with viewport transform on Y (labels stay pinned to
                          the top of the visible area, like a sticky header)

label transform:          translate(-50%, 0)  (center-align horizontally on each x-position)
```

The result: as the student pans horizontally, the labels glide left/right with the tree they label. As the student pans vertically, the labels stay at the top of the pane — they are the always-visible chapter headers of the canvas. As they zoom out, the labels stay readable (see scale rule below).

#### Typography — LOCKED (ghost watermark style)

```
font-family:     --font-display (Fredoka)
font-size:       --text-display (36px)
font-weight:     700
line-height:     1
letter-spacing:  0.02em
color:           --color-text-primary
opacity:         0.06              ← ghost watermark, sits beneath active content
text-transform:  none (sentence-case per copy)
white-space:     nowrap
```

The 6% opacity is the locked ghost level — tested across the dark backdrop (bg-void → bg-deep gradient). At 6% the labels are unmistakably present but never compete with a single line of edge label, never compete with a single chip. They become visible the moment the student looks for them and disappear the moment they look at anything else. That's the watermark contract.

A higher opacity (10%+) crosses into "second-class chrome that distracts from the tree." A lower opacity (3%) reads as a render artifact. **6% is the locked value.**

#### Scale-with-zoom — LOCKED

```
At React Flow zoom level z:
  fontSize = clamp(20px, 36 * (1 / sqrt(z)), 64px)
```

The square-root scaling means: at fitView zoom (~0.5x) the labels render at ~51px (still readable, more presence to anchor a small canvas); at 1.0x they render at 36px; at 2.0x they shrink to ~25px (don't bloat into the user's working zoom).

Clamped between 20px (never disappear) and 64px (never overwhelm).

#### Copy hooks — LOCKED keys

```
future.stage.now        → "Now"
future.stage.nextMove   → "Next move"
future.stage.moveAfter  → "Move after"
```

(Copywriter owns the actual strings; these are the i18n keys to use.)

#### Mobile behavior — LOCKED (hide)

```
@media (max-width: 768px):
  display: none
```

On mobile the tree layout flips to top-bottom (TB). "Now" at the top of a vertical tree is implicit — labeling it explicitly takes vertical real estate that's already scarce. Hidden entirely; no replacement chrome.

This matches §3 Responsive Behavior already locked.

#### Animation — LOCKED

```
On initial render (after tree loads):
  opacity 0 → 0.06              springs.gentle (slow, contemplative)
  no y-offset, no scale animation — they should feel like they were always there

On viewport pan/zoom:
  Position updates synchronously with React Flow viewport state — no springs (must track 1:1)
  Scale updates synchronously per the scale-with-zoom rule above

On filter/selection changes:
  No animation. Stage labels are decoupled from interactive state.

prefers-reduced-motion: omit the entry fade — render immediately at opacity 0.06.
```

#### Edge cases — LOCKED

| Case | Behavior |
|------|----------|
| Tree has zero L1 nodes (root only) | "Now" label renders. "Next move" and "Move after" do not render (no x-position to anchor to). |
| Tree has L1 but no L2 | "Now" and "Next move" render. "Move after" hidden. |
| Tree has L1 and L2 (canonical) | All three render. |
| L1 node positions span a wide x-range due to layout overflow | "Next move" anchors to the **arithmetic mean of L1 node center x-coords**, not the leftmost. Same rule for L2 / "Move after". |
| Pre-layout / loading | Labels hidden until first valid layout completes (no flash-of-misplaced-chrome). |

#### Accessibility — LOCKED

```
role:            none (purely decorative)
aria-hidden:     true
focusable:       false
contrast:        labels are watermark-grade (6% opacity); they are NOT text the student
                 needs to read. They function as a felt rhythm. WCAG contrast does not
                 apply to decorative content (per WCAG 2.1 § 1.4.3 Notes).
                 The actual semantics — "this column is a stage in time" — are
                 conveyed via the breadcrumb (T1.4) and the SelectedNodeCard's
                 "what it takes" block (T2.3) for screen-reader users.
```

The `aria-hidden` is critical — these labels would clutter screen-reader output and do not convey unique information.

#### Tokens used (zero invented values)

| Element | Token |
|---------|-------|
| Font family | `--font-display` (Fredoka) |
| Font size base | `--text-display` (36px) |
| Color | `--color-text-primary` at 0.06 opacity |
| Top spacing in pane | `--space-4` |
| Entry spring | `springs.gentle` |
| Mobile breakpoint | 768px (matches DESIGN.md tablet) |

### T3.2 — "What changed?" return banner — **CUT**

**Status:** CUT — see §10 and §11 resolution.

**Why cut:** BLS / O*NET ingestion is manual and quarterly. During the hackathon window (now → May 18, 2026) the underlying data won't refresh, so the banner would never trigger. Even with `gold.promoted_at` per build vs. build's `created_at` available, the comparison stays false 99%+ of the time. Park for post-hackathon when refresh cadence becomes real and a banner has signal to surface. Theater is worse than absence.

### T3.3 — Task-overlap chip on SOC card — **DEFERRED post-hackathon (confirmed)**

**Status:** DEFERRED — confirmed post-hackathon in §11 resolution.

**Why deferred:** Two MCP fetches per node click (root + selected) is a 400–800ms tax on the explore loop. Caching layer + overlap algorithm (set-intersection over weighted activity vectors) is its own mini-spec. High value, but the deadline-risk-to-value ratio is bad. The brainstorm's strongest post-hackathon candidate.

Original scope preserved here for the future spec author:

- On selection, fetch task profile via MCP `get_task_breakdown(soc)` for both root and selected
- Compute overlap as % of work activities (or top-tasks intersection)
- Render single number on the SOC card: "70% daily-work overlap with your current career"
- Cache results keyed on `(root_soc, selected_soc)` pair to avoid re-fetching on repeated selections

### Responsive Behavior

All enhancements must work at desktop (≥1200px), tablet (768–1199px), and mobile (<768px).

- Edge labels (T1.1): mobile may need a single-line layout that defers to long-press for full delta detail
- Tour chips (T1.2): wrap to a second row on narrow viewports
- Mini-compare (T1.3): card width unchanged; deltas already short
- Breadcrumb (T1.4): truncate harder on mobile (16 chars per segment vs. 24 on desktop)
- SURVIVES row (T2.1): always wraps to its own line on mobile (mobile already stacks filter rows)
- Stage labels (T3.1): hide on mobile (layout flips to TB; "Now" at top is implicit)

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Edge label (T1.1) | `edge-label-{from}-{to}` | text/decorative | n/a (reinforces edge meaning, not interactive) |
| Tour chip (T1.2) | `tour-chip-{id}` | button | "Highlight: {chip label}" |
| Mini-compare strip (T1.3) | `selected-node-compare` | region | "Comparison vs your current career" |
| Breadcrumb segment (T1.4) | `breadcrumb-{level}-{soc}` | button | "Select {title}" / "Hidden by filter — clear filter to see" |
| SURVIVES chip (T2.1) | `survives-chip-{boss}` | button (toggle) | "Show only paths that survive {boss}" |
| Stretch filter chip (T2.2) | `filter-chip-stretch` | button (toggle) | "Show only stretch paths" |
| Make this my path (T2.4) | `btn-make-my-path` | button | "Re-root your career path to {title}" |
| Stage label (T3.1) | `stage-label-{idx}` | text/decorative | n/a |
| Task overlap (T3.3) | `chip-task-overlap` | text | "{pct}% daily-work overlap with your current career" |

### Copy Bundle — LOCKED (copywriter 2026-05-01)

> Implementation reads from this bundle. Add these keys verbatim to `frontend/src/i18n/strings.ts` under each of `en`, `es`, `ar`. Keys preserve the existing `future.*` namespacing pattern.
>
> Voice notes:
> - Edge labels are pure data captions — abbreviations, no verbs, locale-formatted numbers stay code-side
> - Tour chips read as nouns/superlatives ("Highest pay"), not commands ("Show me…")
> - "Survives" reads as the existing IMPROVES rail's grammatical sibling — single declarative verb anchoring three boss nouns
> - Breadcrumb root segment is "Your career" — possessive, peer-voiced, never "You" or "Home"
> - Stage labels are temporal anchors, not edu-speak. "Now / Next move / Move after" — three beats, no glossary
> - Spanish: peer-tone `tú`-form throughout, no `usted`. Title-case proper nouns, sentence-case body
> - Arabic: MSA, sentence-case where applicable, RTL handled by code (no inline punctuation flips here)
>
> All numeric content (pay deltas, year deltas, ranks) is formatted by `Intl.NumberFormat`/`formatCurrency` at render time — locale data does not carry numbers.

#### T1.1 — Edge labels

Education and pay deltas use locale-formatted code output (`+$24k`, `+Master's`, `−$12k`). The strings below cover the **non-numeric** label fragments (degree names, tier names, fallback adjectives, hover-expansion labels). Code composes the `+` / `−` glyphs and numbers around them.

| Key | en | es | ar |
|-----|----|----|----|
| `future.edge.degree.bachelors` | `Bachelor's` | `Licenciatura` | `بكالوريوس` |
| `future.edge.degree.masters` | `Master's` | `Maestría` | `ماجستير` |
| `future.edge.degree.doctorate` | `Doctorate` | `Doctorado` | `دكتوراه` |
| `future.edge.degree.associates` | `Associate's` | `Asociado` | `درجة جامعية` |
| `future.edge.tier.entry` | `Entry` | `Inicio` | `مبتدئ` |
| `future.edge.tier.early` | `Early-career` | `Carrera temprana` | `بداية المسار` |
| `future.edge.tier.mid` | `Mid-career` | `Mitad de carrera` | `منتصف المسار` |
| `future.edge.tier.senior` | `Senior` | `Sénior` | `كبير` |
| `future.edge.tier.midShort` | `Mid+` | `Mitad+` | `منتصف+` |
| `future.edge.tier.seniorShort` | `Senior+` | `Sénior+` | `كبير+` |
| `future.edge.related.close` | `Close` | `Cercano` | `قريب` |
| `future.edge.related.stretch` | `Stretch` | `Estiramiento` | `بعيد` |
| `future.edge.hover.educationTo` | `{from} → {to}` | `{from} → {to}` | `{from} ← {to}` |
| `future.edge.hover.experienceTo` | `{fromTier} → {toTier} (~{years} yrs)` | `{fromTier} → {toTier} (~{years} años)` | `{fromTier} ← {toTier} (~{years} سنوات)` |
| `future.edge.hover.payTo` | `{fromPay} → {toPay} ({deltaPay})` | `{fromPay} → {toPay} ({deltaPay})` | `{fromPay} ← {toPay} ({deltaPay})` |
| `future.edge.hover.relatedRank` | `{label} · rank {rank} of {total}` | `{label} · rango {rank} de {total}` | `{label} · مرتبة {rank} من {total}` |

Notes:
- "Stretch" in Spanish: `Estiramiento` is the literal calque; alternate `A salto` ("a leap") was rejected as too colloquial. `Estiramiento` matches the noun-form posture of the English label.
- Arabic hover templates use `←` (right-to-left arrow) since RTL flips the visual direction; the placeholder order stays `{from}` first per i18n convention, code or RTL CSS does the rest.

#### T1.2 — Tour chips

| Key | en | es | ar |
|-----|----|----|----|
| `future.tour.highestCeiling` | `Highest pay` | `Mayor sueldo` | `أعلى راتب` |
| `future.tour.aiResilient` | `Survives AI` | `Sobrevive a la IA` | `يصمد أمام الذكاء الاصطناعي` |
| `future.tour.fastestToMid` | `Fastest to mid` | `Más rápido a mitad` | `الأسرع إلى المنتصف` |
| `future.tour.biggestPayJump` | `Biggest raise` | `Mayor aumento` | `أكبر زيادة` |
| `future.tour.empty` | `No paths qualify` | `Ninguna ruta califica` | `لا توجد مسارات مؤهلة` |
| `future.tour.aria` | `Highlight: {label}` | `Resaltar: {label}` | `تمييز: {label}` |

Notes:
- "Highest pay" beat "Highest ceiling" — "ceiling" is product jargon (it's a boss name); on a chip it would read as cross-reference. "Pay" is the actual measure.
- "Survives AI" intentionally mirrors the SURVIVES filter chip below — same phrase, different surface (chip = highlight action; filter chip = constraint toggle). The repetition reinforces the boss vocabulary across the screen.
- "Fastest to mid" trims "mid-career" because the chip's adjacent context (a tree of careers) makes the noun unambiguous and the syllable savings matter at chip width.
- "Biggest raise" beat "Biggest pay jump" — "raise" is one syllable, peer language, and what students actually call it. "Jump" is animator-speak.

#### T1.3 — Mini-compare strip

| Key | en | es | ar |
|-----|----|----|----|
| `future.compare.header` | `Compared to {career}` | `Comparado con {career}` | `بالمقارنة مع {career}` |
| `future.compare.headerShort` | `Vs. {career}` | `Vs. {career}` | `مقابل {career}` |
| `future.compare.row.pay` | `Pay` | `Sueldo` | `الراتب` |
| `future.compare.row.aiRes` | `AI res` | `Res. IA` | `مقاومة الذكاء` |
| `future.compare.row.growth` | `Growth` | `Crecimiento` | `النمو` |
| `future.compare.aria` | `Comparison vs your current career` | `Comparación con tu carrera actual` | `المقارنة مع مهنتك الحالية` |

Notes:
- Header is uppercased by code (matches existing Section Label pattern). Strings are sentence-case in the bundle to keep `Intl` lower/upper transforms locale-correct.
- `headerShort` triggers below 480px viewport — saves ~10 chars on a phone-narrow card.
- Row labels are intentionally compressed ("AI res", "Res. IA") to fit the locked `flex: 0 0 88px` column. Full names live in `future.stat.aiResilient` and are surfaced in hover/tooltip (existing key, reuse).

#### T1.4 — Breadcrumb

| Key | en | es | ar |
|-----|----|----|----|
| `future.breadcrumb.root` | `Your career` | `Tu carrera` | `مهنتك` |
| `future.breadcrumb.hiddenTooltip` | `Hidden by filter. Clear filters to see.` | `Oculto por filtro. Quita los filtros para ver.` | `مخفي بواسطة الفلتر. امسح الفلاتر للعرض.` |
| `future.breadcrumb.aria.select` | `Select {title}` | `Seleccionar {title}` | `اختيار {title}` |
| `future.breadcrumb.aria.hidden` | `Hidden by filter — clear filter to see` | `Oculto por filtro: quita el filtro para ver` | `مخفي بواسطة الفلتر — امسح الفلتر للعرض` |
| `future.breadcrumb.aria.root` | `Back to your career` | `Volver a tu carrera` | `العودة إلى مهنتك` |

Notes:
- "Your career" beats "Home" / "You" / "Start" — possessive framing keeps the breadcrumb peer-voiced and tied to the build's identity, not the app's chrome.
- Hidden tooltip is a 2-clause sentence with periods (not em-dash). Matches the error-copy convention: state, then the next step.
- Aria-label for ghost segments matches the §3 accessibility table's wording (em-dash form) — kept verbatim there for screen-reader continuity with the in-tooltip phrasing.

#### T2.1 — SURVIVES filter row

| Key | en | es | ar |
|-----|----|----|----|
| `future.survives.label` | `Survives` | `Sobrevive a` | `يصمد أمام` |
| `future.survives.ai` | `Survives AI` | `Sobrevive a la IA` | `يصمد أمام الذكاء الاصطناعي` |
| `future.survives.market` | `Survives market` | `Sobrevive al mercado` | `يصمد أمام السوق` |
| `future.survives.burnout` | `Survives burnout` | `Sobrevive al agotamiento` | `يصمد أمام الإرهاق` |
| `future.survives.aria` | `Filter career paths by which bosses they survive` | `Filtrar trayectorias según qué jefes sobreviven` | `تصفية المسارات حسب المعارك التي تصمد أمامها` |
| `future.survives.chipAria` | `Show only paths that survive {boss}` | `Mostrar solo rutas que sobrevivan a {boss}` | `إظهار المسارات التي تصمد أمام {boss} فقط` |

Notes:
- "Survives" (not "Beats" / "Wins" / "Defeats") — locked vocabulary uses WIN/DRAW/LOSE for outcomes, but the *filter axis* is survival. The chip says "this path survives Fight AI" not "this path beats AI." Survival is the durable claim; "beats" is a single-fight result.
- Spanish prefix label is `Sobrevive a` (with preposition baked into the prefix) so each chip reads cleanly: "Sobrevive a · Sobrevive a la IA" — slight redundancy in the chip itself is intentional, mirrors English "Survives · Survives AI."
- Arabic prefix `يصمد أمام` works the same way.
- Boss names ("AI", "market", "burnout") in chip labels are deliberately lowercase in en (not "Fight AI") because the filter-row context already names the axis. The "Fight" prefix only appears on the gauntlet screen and in narrative copy. The `chipAria` template does interpolate `{boss}` from the localized boss-name keys (existing `boss.ai.title`, etc.) to keep screen-reader output aligned with the gauntlet's full names.

#### T2.3 — "What it takes" block

| Key | en | es | ar |
|-----|----|----|----|
| `future.whatItTakes.title` | `What it takes:` | `Lo que hace falta:` | `ما يتطلبه الأمر:` |
| `future.whatItTakes.education` | `Education: {from} → {to}` | `Educación: {from} → {to}` | `التعليم: {from} ← {to}` |
| `future.whatItTakes.experience` | `Experience: {fromTier} → {toTier} (+{years} yrs)` | `Experiencia: {fromTier} → {toTier} (+{years} años)` | `الخبرة: {fromTier} ← {toTier} (+{years} سنوات)` |
| `future.whatItTakes.topStat` | `Top stat shift: {statName} {delta}` | `Cambio principal: {statName} {delta}` | `أكبر تغير: {statName} {delta}` |

Stat-name strings (reuse existing `future.stat.*` keys — no duplication):
- `future.stat.aiResilient` → `AI resilience` / `Más resistente a la IA` / `أكثر مقاومة للذكاء الاصطناعي`
- `future.stat.growth` → `Growth` / `Mayor crecimiento` / `نمو أسرع`
- For HMN, add: `future.stat.humanWork` → `Human work` / `Trabajo humano` / `العمل البشري`

Notes:
- "What it takes:" with the trailing colon is intentional — it grammatically opens the bullet list as a sentence the card is speaking. Spanish "Lo que hace falta:" matches; Arabic "ما يتطلبه الأمر:" is the natural equivalent.
- "Top stat shift" beat "Biggest change" / "Most-changed stat" — "shift" is concrete, neutral, and matches the investment-not-judgment frame of the block.
- The existing `future.stat.aiResilient` key carries "Más resistente a la IA" in es — when surfaced inside `topStat`, that full phrase is correct. If the implementation needs a shorter standalone form for inline use, a future key `future.stat.aiResilient.short` can be added; not required for this delivery.
- Year delta is always rendered with `+` per the template — this is "what it takes," investment framing. A negative-experience-delta (rare) would be a separate edge case; skip the bullet rather than show a `−` here.

#### T3.1 — Stage axis labels

| Key | en | es | ar |
|-----|----|----|----|
| `future.stage.now` | `Now` | `Ahora` | `الآن` |
| `future.stage.nextMove` | `Next move` | `Siguiente paso` | `الخطوة التالية` |
| `future.stage.moveAfter` | `Move after` | `Paso después` | `الخطوة بعدها` |

Notes:
- "Move after" (not "Then" / "Later" / "After that") — "Move" reinforces the sequence-of-decisions frame the labels are establishing. Three labels, three "moves" implied. "Now / Next move / Move after" reads as a beat the student can hear.
- Spanish "Siguiente paso / Paso después" preserves the noun-form parallel.
- Arabic uses "الخطوة" (step) consistently across the second and third labels for the same parallel rhythm.
- These are watermarks at 6% opacity per §3 — short matters more than poetic. Every word here was chosen for syllable economy.

#### Strings.ts insertion plan (implementation reference)

Implementation will add the keys above to all three locale blocks in `frontend/src/i18n/strings.ts`. The existing `future.*` namespacing convention is preserved. Net new keys: 49 (en) + 49 (es) + 49 (ar) = 147 entries. One existing key (`future.stat.humanWork`) is added per the T2.3 stat-name list. No existing keys are modified.

---

## §4 Technical Specification

### Architecture Overview

This bundle touches:

- **Frontend tree rendering layer:** `BranchTreeFlow.tsx`, `treeFlowLayout.ts`, `flow/Flow*.tsx` for edge labels (T1.1), relatedness encoding (T2.2), stage labels (T3.1).
- **Frontend filter system:** `educationFilter.ts`, `statFilter.ts` (already recursive), new `bossFilter.ts` for T2.1.
- **Frontend SOC card:** `SelectedNodeCard.tsx`, `CareerCard.tsx` for mini-compare (T1.3), what-it-takes block (T2.3), make-my-path CTA (T2.4), task-overlap chip (T3.3).
- **Frontend FutureScreen orchestration:** `FutureScreen.tsx` for breadcrumb (T1.4), tour chips (T1.2), filter row composition (T2.1), return banner (T3.2).
- **Backend tree builder:** `backend/app/services/career_tree.py` — adds `relatedness` field to TreeNode payload (T2.2).
- **Backend re-root endpoint:** new file or extension of `backend/app/routers/builds.py` for T2.4 (decision matrix in §3).
- **Backend MCP fetch surface:** existing `mcp_client` for T3.3 task-overlap (post-hackathon).
- **i18n:** new strings across en/es/ar in `frontend/src/i18n/strings.ts`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/data/treeFlowLayout.ts` | Modify | Add edge `data` for delta labels (T1.1), edge `style` modulation by relatedness (T2.2). |
| `frontend/src/components/tree/BranchTreeFlow.tsx` | Modify | Wire `edgeTypes` for custom edge with label (T1.1). Apply T2.2 style modulation. Add stage label overlay (T3.1). |
| `frontend/src/components/tree/flow/EdgeWithLabel.tsx` | Create | Custom edge component rendering pill at midpoint. (T1.1) |
| `frontend/src/data/edgeLabel.ts` | Create | Pure function: `pickEdgeLabel(parent, child) → { text, kind } \| null`. (T1.1) |
| `frontend/src/data/edgeLabel.test.ts` | Create | Unit tests for label-selection priority chain. (T1.1) |
| `frontend/src/components/tree/TourChipRow.tsx` | Create | Four tour chips with ranking function dispatch. (T1.2) |
| `frontend/src/data/tourRanking.ts` | Create | Ranking functions per tour chip; return top-N node IDs to flash. (T1.2) |
| `frontend/src/data/tourRanking.test.ts` | Create | Unit tests for each ranker. (T1.2) |
| `frontend/src/components/tree/SelectedNodeCard.tsx` | Modify | Add mini-compare strip (T1.3); replace educationLabel with what-it-takes block (T2.3); add make-my-path CTA (T2.4); add task-overlap chip (T3.3, gated). |
| `frontend/src/components/CareerCard.tsx` | Modify | Optional `compareStrip` slot prop for the mini-compare strip rendering. (T1.3) |
| `frontend/src/components/tree/SelectedNodeCard.test.tsx` | Modify | Tests for compare strip math, what-it-takes rendering. (T1.3, T2.3) |
| `frontend/src/components/tree/Breadcrumb.tsx` | Create | Breadcrumb component with ghost state. (T1.4) |
| `frontend/src/components/tree/Breadcrumb.test.tsx` | Create | Tests for click handlers + ghost state. (T1.4) |
| `frontend/src/screens/FutureScreen.tsx` | Modify | Wire TourChipRow (T1.2), Breadcrumb (T1.4), boss filter state (T2.1), make-my-path handler (T2.4), return banner (T3.2). |
| `frontend/src/screens/FutureScreen.test.tsx` | Modify | Add tests for tour chips, breadcrumb persistence across filters, boss filter row, re-root flow. |
| `frontend/src/data/bossFilter.ts` | Create | Pure function `filterTreeByBoss(tree, filters)` with recursive L1+L2 application. (T2.1) |
| `frontend/src/data/bossFilter.test.ts` | Create | Unit tests for boss filter logic. (T2.1) |
| `frontend/src/components/tree/BossFilterRow.tsx` | Create | Third filter chip row, mirrors `StatFilterRow`. (T2.1) |
| `frontend/src/types/tree.ts` | Modify | Add `relatedness: number \| null` to `TreeNode`. (T2.2) |
| `backend/app/services/career_tree.py` | Modify | Carry `best_index` from row dict through `build_tree` into `TreeNode.relatedness` (default `None`). (T2.2) |
| `backend/app/routers/branches.py` | Modify | Add `"relatedness": node.relatedness` to `_node_to_dict` — this is the only serialization seam (no Pydantic model). (T2.2) |
| `backend/tests/services/test_career_tree.py` | Modify | Add test for relatedness propagation. Fix existing fixture `"best_index": 2.0 → 2` to match `IntegerType`. (T2.2) |
| `frontend/src/api/build.ts` | Modify | If T2.4 uses backend re-root: add `rerootBuild(buildId, fromSoc)` API client. |
| `backend/app/routers/builds.py` | Modify | If T2.4 uses backend re-root: add `POST /build/{id}/reroot` endpoint. |
| `backend/app/services/build_pipeline.py` | Modify | If T2.4 uses backend re-root: implement re-root logic. (TODO @fp-architect refine) |
| `backend/tests/routers/test_builds.py` | Modify | Tests for re-root endpoint. (T2.4) |
| `frontend/src/i18n/strings.ts` | Modify | Add ~25 new keys × 3 locales for T1.2 chip labels, T1.4 tooltip, T2.1 chips, T2.3 bullets, T2.4 CTA, T3.1 stage labels. |
| `frontend/src/styles/reactflow-dark.css` | Modify | Edge label pill styling, stage label background style, breadcrumb ghost styling. |

### Data Model Changes

#### Frontend `TreeNode` extension (T2.2)

```ts
// frontend/src/types/tree.ts
export interface TreeNode {
  // ... existing fields
  relatedness: number | null;  // O*NET best_index rank (1-99); 1 = closest match
}
```

#### Backend `TreeNode` propagation (T2.2)

```python
# backend/app/services/career_tree.py
@dataclass
class TreeNode:
    soc_code: str
    title: str
    level: int
    # ... existing fields
    relatedness: int | None = None  # carried from CareerBranch.best_index
```

#### Backend re-root endpoint (T2.4, if approach (a))

```python
# backend/app/routers/builds.py
class RerootRequest(BaseModel):
    from_soc: str  # the new root SOC the student is jumping to

@router.post("/build/{build_id}/reroot")
async def reroot_build(
    build_id: str,
    request: RerootRequest,
) -> Build:
    """Re-root an existing build to a new SOC reachable from the original
    career via career_transitions. Spawns a new Build record (preserves
    parent_build_id chain) with the new SOC as the anchor career.
    """
    ...
```

@fp-architect to refine signature + persistence semantics.

### Service Changes

#### `frontend/src/data/edgeLabel.ts` (T1.1)

```ts
export type EdgeLabelKind =
  | "education"
  | "experience"
  | "pay"
  | "relatedness_close"
  | "relatedness_stretch";

export interface EdgeLabel {
  text: string;       // "+Master's", "+5 yrs", "+$24k", "Close", "Stretch"
  kind: EdgeLabelKind;
  isPositive: boolean; // drives green vs muted color
}

/**
 * Pick the most striking delta to surface on an edge from `parent` to `child`.
 * Priority: education > experience > pay > relatedness > none.
 * Returns null when no delta clears the threshold for visibility.
 */
export function pickEdgeLabel(
  parent: TreeNode,
  child: TreeNode,
): EdgeLabel | null;
```

#### `frontend/src/data/tourRanking.ts` (T1.2)

```ts
export type TourId =
  | "highest_ceiling"
  | "ai_resilient"
  | "fastest_to_mid"
  | "biggest_pay_jump";

/**
 * Return the top-N node IDs (in flash priority order) for a given tour
 * over the current visible (filtered) tree.
 */
export function rankNodesForTour(
  tour: TourId,
  tree: TreeNode,
  topN?: number,
): string[];
```

#### `frontend/src/data/bossFilter.ts` (T2.1)

```ts
// Trimmed to 3 chips per @fp-data-reviewer — boss_loans / boss_ceiling
// drop ~100% of non-root nodes in real data (no signal).
export type BossFilter =
  | "boss_ai"
  | "boss_market"
  | "boss_burnout";

export function nodePassesBossFilter(
  node: TreeNode,
  filter: BossFilter,
): boolean;

export function nodePassesAllBossFilters(
  node: TreeNode,
  filters: ReadonlySet<BossFilter>,
): boolean;

/**
 * Recursive — applies filter to L1 AND L2. Mirrors the
 * filterTreeByEducation / filterTreeByStats pattern.
 */
export function filterTreeByBoss(
  tree: TreeNode,
  filters: ReadonlySet<BossFilter>,
): TreeNode;
```

### Testing Impact Analysis

> **IMPORTANT**: Search the test directories for tests related to files being modified before finalizing this section.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/FutureScreen.test.tsx` | All 16 existing tests | Med | Adding tour chips, breadcrumb, boss filter row to JSX may shift testid lookups. Likely compatible — testids are stable — but verify each test still finds its target. |
| `frontend/src/components/tree/SelectedNodeCard.test.tsx` | All 9 existing tests | Med | Card layout changes (compare strip + what-it-takes) restructure the rendered DOM. Tests targeting wage / education text should still pass; tests targeting absent elements need re-checking. |
| `frontend/src/data/educationFilter.test.ts` | All 16 existing tests | Low | No filter-logic changes; only adding bossFilter alongside. |
| `frontend/src/data/statFilter.test.ts` | All 16 existing tests | Low | Same. |
| `backend/tests/services/test_career_tree.py` | `test_build_tree_*` | Low | Adding `relatedness` field is additive. Tests not asserting on TreeNode field count should still pass. |
| `backend/tests/routers/test_builds.py` | All build-creation tests | Low (assuming T2.4 approach (a)) | New `/build/{id}/reroot` endpoint is additive. |
| `frontend/src/components/CareerCard.tsx` callers (set-your-course flow) | `SetYourCourseScreen.test.tsx`, `CareerTierSection.test.tsx` | Med | Adding `compareStrip` slot prop must not affect default-rendering. Existing callers don't pass the prop. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `SelectedNodeCard.test.tsx` "renders the wage formatted as dollars" | Adjust query if compare-strip wraps the wage in a wrapper element | Layout restructure for T1.3 |
| `SelectedNodeCard.test.tsx` "renders the education label" | Replace with "renders the what-it-takes block" assertion when picked | T2.3 replaces single line with bullet block |
| `FutureScreen.test.tsx` filter tests | Possibly add boss filter assertions to existing combined-filter tests | T2.1 layered filters |

#### Confirmed Safe

These tests must NOT break. If they fail, STOP and escalate:

- All `educationFilter.test.ts` and `statFilter.test.ts` tests — filter logic itself is unchanged.
- `BranchHorizonMap.test.tsx` (the /branches view) — this spec doesn't touch /branches.
- Any backend test not in `test_career_tree.py` or `test_builds.py`.
- `BranchHighlightDriver.test.tsx` — its API is reused by tour chips but not modified.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `edgeLabel.test.ts` | `pickEdgeLabel_education_delta_wins` | Education delta beats experience + pay when present |
| P0 | `edgeLabel.test.ts` | `pickEdgeLabel_returns_null_for_uneventful_edge` | Sub-threshold deltas yield no label |
| P0 | `edgeLabel.test.ts` | `pickEdgeLabel_pay_threshold_10k` | Pay delta < $10k is suppressed |
| P0 | `SelectedNodeCard.test.tsx` | `renders_compare_strip_when_picked_non_root` | Mini-compare strip renders for picked L1/L2 |
| P0 | `SelectedNodeCard.test.tsx` | `hides_compare_strip_on_root_anchor` | No strip when picked is root |
| P0 | `SelectedNodeCard.test.tsx` | `compare_strip_pay_delta_math` | `selected.median_wage − root.median_wage` correct, sign correct, abbreviated to $k correctly |
| P1 | `tourRanking.test.ts` | `highest_ceiling_picks_top_3_by_wage` | Sort + slice correctness |
| P1 | `tourRanking.test.ts` | `fastest_to_mid_prefers_low_experience_tier` | Tier ordering: entry < early < mid < senior |
| P1 | `tourRanking.test.ts` | `biggest_pay_jump_uses_delta_not_absolute` | Delta-vs-root, not absolute pay |
| P1 | `tourRanking.test.ts` | `ranker_handles_empty_tree_gracefully` | Returns `[]` not throw |
| P1 | `Breadcrumb.test.tsx` | `clicking_segment_re_selects_that_node` | Selection state updates |
| P1 | `Breadcrumb.test.tsx` | `ghost_state_when_node_filtered_out` | Strikethrough + tooltip render |
| P1 | `bossFilter.test.ts` | `filter_keeps_node_with_win_outcome` | "win" passes |
| P1 | `bossFilter.test.ts` | `filter_keeps_node_with_draw_outcome` | "draw" passes |
| P1 | `bossFilter.test.ts` | `filter_drops_node_with_lose_outcome` | "lose" fails |
| P1 | `bossFilter.test.ts` | `filter_recursive_to_L2` | Mismatching L2s hidden under matching L1 |
| P1 | `bossFilter.test.ts` | `multi_select_AND_within_row` | All chips must pass |
| P1 | `FutureScreen.test.tsx` | `tour_chip_flashes_top_3` | Click chip → BranchHighlightDriver fires for 3 nodes |
| P1 | `FutureScreen.test.tsx` | `breadcrumb_persists_across_filter_toggle` | Selection drops in state, breadcrumb retains visual |
| P1 | `FutureScreen.test.tsx` | `boss_filter_row_renders_3_chips` | Layout sanity |
| P1 | `FutureScreen.test.tsx` | `make_my_path_cta_re_roots_tree` | Click → tree reloads with new root SOC |
| P1 | `test_career_tree.py` | `test_build_tree_carries_relatedness` | TreeNode.relatedness populated from CareerBranch.best_index (T2.2 backend) |
| P1 | `test_builds.py` | `test_reroot_endpoint_creates_new_build_with_parent_link` | (T2.4 backend, if approach (a)) |
| P2 | `FutureScreen.test.tsx` | `stage_axis_labels_render_at_correct_x` | T3.1 |
| P2 | `SelectedNodeCard.test.tsx` | `task_overlap_chip_fetches_and_renders` | T3.3 (post-hackathon stretch) |

#### Test Data Requirements

- Existing `makeBuild()` + `makeMixedEducationTree()` + `makeMixedStatsTree()` fixtures in `FutureScreen.test.tsx` are reusable; extend with `relatedness` values for T2.2 testing.
- New fixture: `makeMixedBossTree()` with varied boss outcomes per branch for T2.1 boss filter tests.
- Existing fixtures in `test_career_tree.py` may need `best_index` values added if not already present.

### Gemma-touching work

This spec touches Gemma in T1.2 only — and only optionally. If the tour-chip-fires-a-chat-opener behavior ships, the chat opener prompt updates from a generic "Give me a 3-sentence orientation" to a tour-specific opener like "Tell me about the highest-ceiling paths from this career: {names}."

- **Fallback behavior:** If Gemma is unavailable, the tour chip still flashes nodes (visual side-channel works without backend). Chat opener falls back to existing root opener.
- **Logging:** No new log surfaces; existing `logs/gemma.jsonl` captures the new opener like any other.
- **Backend agnosticism:** Works under `INFERENCE_BACKEND=ollama` and `=openrouter` identically (text prompt change only).
- **Rate limits:** No new fetch volume; tour chip just modifies the existing opener.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED
**Reviewed:** 2026-05-01
**Scope reviewed:** T1.1, T1.2, T1.3, T1.4, T2.1, T2.2, T2.3, T3.1 only. T2.4 / T3.2 / T3.3 explicitly out of scope per §11.

#### System Context
Bundle sits entirely in the frontend `/future` React Flow surface plus one additive backend payload extension (T2.2). Layers touched: `backend/app/services/career_tree.py` (dataclass + propagation), `backend/app/routers/branches.py` (one new key in `_node_to_dict`), `frontend/src/types/tree.ts` (one optional field), and several frontend components/data modules. No MCP tool surface change. No Brightsmith zone change. No Pydantic model anywhere — `/tree/{build_id}` already serializes via a hand-rolled dict, so this is a contract-shape extension, not a model change.

#### Data Flow Analysis
T2.2 trace, source -> screen:

1. **Gold zone:** `consumable.career_branches` already exposes `best_index` (numeric O*NET relatedness rank, lower = closer). Confirmed in `src/mcp_server/futureproof_server.py:449` (`CAREER_BRANCHES_RESPONSE_FIELDS`).
2. **MCP:** `_handle_get_career_branches` returns rows with `best_index` already in the response dict (`src/mcp_server/futureproof_server.py:3208-3270`). Already used internally as the sort key. **Field name is `best_index`, not `relatedness_rank`** — spec §4 data-model snippet says `best_index` in the comment but the TS field is named `relatedness`; that rename is fine and intentional (frontend semantic vs. backend physical).
3. **Backend service:** `career_tree._fetch_raw_branches` already returns the row dict unchanged. Add one line in the `expand()` child-construction block in `career_tree.py:200-223` reading `as_int(row.get("best_index"))`. Use the existing `as_int` coercion (already imported) — no float drift, no int-truncation surprise (best_index is already integral O*NET ranks 1..N).
4. **Backend router:** `branches.py:45-63` `_node_to_dict` needs one new key `"relatedness": node.relatedness`. Hand-rolled serialization, so this is the only serialization seam.
5. **Frontend type:** `frontend/src/types/tree.ts` adds `relatedness: number | null;`. Type matches the optional `int | None` from backend; JSON `null` deserializes cleanly.
6. **Frontend consumer:** edge style modulation in `treeFlowLayout.ts` reads `child.relatedness` for stroke width/opacity scaling.

Root node relatedness: **must be `None`**. The root is the student's anchor career — there is no parent, hence no O*NET relatedness rank. The root `TreeNode` constructor in `career_tree.py:150-162` already omits the field; defaulting `relatedness: int | None = None` on the dataclass means root reads as `None` for free, no extra code. Frontend edge logic should never look up relatedness on the root anyway (root has no incoming edge).

#### Contract Review

- **TreeNode (dataclass):** Add `relatedness: int | None = None` after the existing `experience_tier` field. Defaulted, so all existing call sites (root construction, child construction without best_index) stay valid.
- **`_node_to_dict` (router):** Add `"relatedness": node.relatedness` key. Additive — existing callers see one extra field; clients that don't read it are unaffected.
- **Frontend `TreeNode` (TS):** Add `relatedness: number | null;`. Matches backend serialization shape.
- **API contract for `/tree/{build_id}`:** Strictly additive. No existing field changes type, name, or position. No breaking change for any consumer.
- **Boss outcome contract for T2.1:** `_compute_boss_results` (`career_tree.py:87-119`) writes exactly `"win" | "lose" | "draw" | "unknown"` via `_score_boss` (line 83-84). `boss_fights.rescore_fight` returns the same domain (confirmed at `boss_fights.py:565-568`). Frontend SURVIVES filter logic `node.boss_X in {"win", "draw"}` is sound; `"unknown"` correctly fails the filter (the right behavior — if we don't know whether the path survives a boss, we shouldn't claim it does). This matches §2 Decision 6.

#### Findings

##### Sound
- **T2.2 backend extension is clean.** Single `as_int(row.get("best_index"))` call in the existing child-construction block; defaulted dataclass field; one new key in `_node_to_dict`. Three-line backend change. No new ingestor, no schema migration, no MCP tool change.
- **No Pydantic TreeNode model exists** (confirmed: nothing in `backend/app/models/` references TreeNode). The router serializes via `_node_to_dict`, so the additive field has exactly one serialization seam to update. Spec §4 doesn't claim a Pydantic model — good.
- **TreeNode payload size:** one nullable int per node. At depth=2 with ~10 children/node ceiling, that's ~110 nodes max -> ~440 bytes upper bound. Negligible.
- **Boss outcome stability for T2.1:** `_compute_boss_results` runs at every node via `walk()` (`career_tree.py:232-244`), so every `TreeNode` in the payload has all five `boss_*` fields populated to the canonical 4-value domain. Frontend filter machinery has a stable contract to work against. `boss_loans` and `boss_market` and `boss_ceiling` are computed with `loans=None, market=None, ceiling=None` raw inputs (`career_tree.py:109-115`) — they will mostly evaluate to `"unknown"`, meaning the SURVIVES chips for those bosses will hide most non-root nodes. This is correct behavior (we genuinely don't have the data to claim survival), but visionary should know: the SURVIVES row will feel sparser than students might expect for loans/market/ceiling. Worth a tooltip note like "Unknown outcomes are hidden". Not a blocker.
- **API contract is additive only.** Existing /future tests, /branches tests, and any other consumer of `/tree/{build_id}` continue to work without modification.

##### Concerns
- **Field naming consistency (minor):** Backend dataclass field is named `relatedness`, sourced from row column `best_index`. Spec §4 backend snippet comment says "carried from CareerBranch.best_index" — accurate. Recommend a one-line docstring on the dataclass field: `# carried from career_branches.best_index (O*NET rank, lower = closer)`. **Impact:** future readers won't have to grep MCP source to figure out the provenance. **Recommendation:** add the comment when the field is added; not a blocker.
- **Frontend null-handling for edge gradient (T2.2):** Spec §3 T2.2 doesn't explicitly say what an edge does when `child.relatedness === null`. With the current backend, this is rare (only happens when MCP returns no `best_index` for a row, which the existing sort key handles via `float("inf")`). Recommend: edges with null relatedness render at the *thinnest/most-translucent* end of the scale (treat as "we don't know how related — assume distant"). Visionary should make that explicit. **Impact:** otherwise renderer may NaN out or render at default. **Recommendation:** call this out in the §3 T2.2 visionary pass.
- **T2.1 SURVIVES filter on root (minor):** Filter is recursive per §2 Decision 6. The root passes any boss filter where it itself survives, which is correct. Edge case: if root fails (e.g., `boss_ai === "lose"`) and a SURVIVES filter is on for that boss, recursive filter will hide root + all children. Tree pane will render empty. This is the consistent behavior with existing `educationFilter` and `statFilter`, so it's fine — but the empty-state UX should be explicit (existing empty-state component should already handle it). **Recommendation:** verify in the test pass that `boss_filter_drops_root_when_root_fails` produces the existing empty-state, not a crash.
- **T2.1 chip count (minor):** Spec §3 T2.1 lists 5 boss chips but the row 1 packing math assumes 3 boss + 3 education = 6 chips. Five boss chips on row 1 would be 8 chips total; might wrap awkwardly on tablet. Visionary needs to either (a) confirm the trim to 3 chips (which 3?) or (b) accept the wrap. Not architectural. **Recommendation:** flag for visionary in §3 T2.1.

##### Blockers
None.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

Proceed to design vision (step 2). Backend extension for T2.2 is a 3-line surgical change; everything else is frontend-only. No further architectural review needed before implementation.

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-01
**Scope reviewed:** T1.1, T1.2, T1.3, T1.4, T2.1, T2.2, T2.3, T3.1. Skipped per spec: T2.4 (cut), T3.2 (cut), T3.3 (deferred).

#### Data Sources Affected
- **O*NET Related Occupations** (Silver `base.onet_career_transitions` -> Gold `consumable.career_branches`) — source of `best_index` (T2.2) plus `related_grw`, `related_hmn`, `related_res`, `related_burnout`, `related_ai_boss` consumed by `_compute_boss_results` (T2.1).
- **BLS OOH** (occupation profiles) — backs `related_grw`, `related_burnout`, `related_wage` via the Gold `futureproof_engine` join.
- **Karpathy AI Exposure** — backs `related_res` and `related_ai_boss` (Gold backfill, schema fields 25-30 of `career_branches`).
- No new ingestor or pipeline change. Strictly additive read-side propagation.

#### Crosswalk Impact
- None. `best_index` is the O*NET SOC<->SOC relatedness rank, not a CIP<->SOC crosswalk. Tier 1-4 crosswalk machinery is untouched.
- Provenance traced and confirmed: O*NET `related_index` (1..N) -> Silver `transform_career_transitions` keeps the **lowest** index per (src, tgt) pair (`onet_transformer.py:400`) -> Silver `derive_relatedness_tier` buckets 1-5 = Primary-Short, 6-10 = Primary-Long, 11-20 = Supplemental (`onet_transformer.py:68`) -> Gold `career_branches.best_index` (`required=True`, IntegerType, `futureproof_engine.py:253`) -> MCP `_handle_get_career_branches` already includes `best_index` in `CAREER_BRANCHES_RESPONSE_FIELDS` (`futureproof_server.py:449`) and uses it as the primary sort key (line 3258-3264) -> live probe of SOC 15-1252 returned 15 rows with `best_index` 1..18, **0 nulls**, all `IntegerType` as declared.
- **Rank semantics confirmed: 1 = closest, higher = stretch.** Spec's assumption is correct. The gradient direction in §3 T2.2 ("Rank 1-5 = bold/opaque", "rank 50+ = thin/translucent") is right but the upper bound is wrong: real ranks cap at 20 (Silver tier ceiling), not 50+. Visionary should anchor the gradient at 1..20, not 1..50.

#### Formula Verification

##### T2.2 propagation chain — clean
- Backend coercion: `as_int(row.get("best_index"))` is the right call. Source is already `IntegerType`, so `as_int` is defensive-only — no float drift, no truncation. Confirmed `best_index` is `required=True` on Gold + non-null in live data, so the `None`-on-missing path is theoretically reachable only if a future ingestor regression breaks the contract. Acceptable.
- Root node `relatedness=None` is correct — root has no parent, hence no rank. Frontend must not look up `relatedness` on root (no incoming edge).
- One serialization seam: `_node_to_dict` in `backend/app/routers/branches.py:45-63` is hand-rolled and currently DOES NOT include the field. The architect flagged the dataclass change but the router add is the seam that actually ships the data. Spec §4 calls this out implicitly ("backend payload extension"); make sure it's not missed.

##### T2.1 boss-outcome stability — diverges from gauntlet for 2 of 5 bosses
- **Gauntlet vs. tree-node scoring is NOT identical.** `_compute_boss_results` (`career_tree.py:87-119`) builds a synthetic `CareerOutcome` with `bosses=BossScores(ai=ai_boss_raw, loans=None, market=None, burnout=burnout_raw, ceiling=None)` and `stats=PentagonStats(ern=node.ern, roi=root_roi, res=node.res, grw=node.grw, hmn=node.hmn)`. Per-boss stability:
  - `boss_ai`: scorer reads `stats.res + stats.hmn`. Both are occupation-level, populated on every TreeNode from `related_res`/`related_hmn`. **Stable** — re-rooted gauntlet yields the same outcome for the same SOC.
  - `boss_burnout`: scorer reads `bosses.burnout`. Populated from `related_burnout`. **Stable.**
  - `boss_market`: scorer reads `stats.grw` only. Populated from `related_grw`. **Stable.** (Note: the user's brief assumed `boss_market` was synthetic-None; it isn't. `_score_market` looks at `stats.grw`, not `bosses.market`.)
  - `boss_loans`: scorer prefers `bosses.loans` (financing-aware), falls back to `stats.roi`. TreeNode passes `bosses.loans=None` and `stats.roi=root_roi`. So tree-side `boss_loans` is computed against the ROOT BUILD's ROI, not the would-be ROI of a re-rooted build at this SOC. **Diverges** — at re-root the student would have a different financing-aware loans score. For non-root tree nodes the result is dominated by the root build's ROI, which is misleading: a "Survives loans" chip on a Software Developer branch reads as if it's about Software Developer financing, but it's actually about the student's current school+program ROI propagated downstream.
  - `boss_ceiling`: scorer reads `bosses.ceiling`, falls back to `stats.ern`. TreeNode passes `bosses.ceiling=None` and `ern=None`. **Always returns "unknown"** for non-root nodes. Live verification: 15/15 nodes off SOC 15-1252 returned `ceiling=unknown`.
- Live empirical distribution across 15 branches off SOC 15-1252 (real data, current code path):
  - `boss_ai`: 0 win / 11 lose / 4 draw / 0 unknown — **real signal**
  - `boss_loans`: 0 / 0 / 0 / **15 unknown** — **dead chip in practice** (ROI fallback also `None` because `roi=root_roi` only ferries the root's ROI; for the root node it'd score, for children it'd score against the root's ROI which is conceptually wrong)
  - `boss_market`: 12 / 2 / 1 / 0 — **real signal**
  - `boss_burnout`: 0 / 0 / 14 / 1 — **real signal but mostly draws** (burnout score range collapses to mid-band on the inverted scale)
  - `boss_ceiling`: 0 / 0 / 0 / **15 unknown** — **dead chip**
- **Recommendation:** trim T2.1 chip set to the three with real signal: `boss_ai`, `boss_market`, `boss_burnout`. Drop `boss_loans` and `boss_ceiling` from this spec entirely. Rationale: a "Survives loans" / "Survives ceiling" chip that hides every non-root child every time is a worse UX than no chip — it teaches the student the filter is broken. This also dovetails with §3 T2.1's "TODO trim to 3 most-meaningful" note. If the visionary insists on keeping all five, §5 must add a tooltip on those two chips: "Loans / Ceiling outcomes need program-level data we don't have for branches yet — these chips will hide most paths."

#### Findings

##### Data Quality Sound
- **`best_index` propagation:** clean, no value drift. `IntegerType` source -> `as_int` coercion -> `int | None` dataclass field -> JSON int. Confirmed 0 nulls in a live SOC sample (15-1252).
- **Rank semantics match spec:** 1 = closest, higher = stretch. Tier buckets are 1-5 / 6-10 / 11-20.
- **Field name:** `best_index` is the right physical column; renaming to `relatedness` at the dataclass/payload boundary is fine and intentional (frontend semantic > backend physical). Architect already approved this rename.
- **`boss_ai`, `boss_market`, `boss_burnout` are stable and correct against the gauntlet** for the same SOC at the same ranks: scorers read occupation-level stats that don't change with school/program context.
- **Root node populates all five `boss_*` fields from real career data,** not the synthetic shim — `_compute_boss_results` runs on root last in `walk()` but reads `node.ern`, `node.roi` (from `career.stats.roi`), `node.bosses.burnout`/`ai_boss` set from `career.bosses.*`. Root SURVIVES filter is honest.

##### Data Concerns
- **`boss_loans` on non-root nodes propagates the ROOT build's ROI as the loans score, not the branch's own financing.** **Risk:** student looks at a Sales Manager branch with "Survives loans = win" and assumes it means Sales Manager debt outcomes are good — but the score reflects their CURRENT school+program loan picture, not what they'd borrow to become a Sales Manager. **Fix:** drop `boss_loans` from T2.1 chips; OR set `node.roi = None` on non-root TreeNodes so the scorer returns `unknown` (honest "we don't know") instead of an inherited-but-misleading number; OR document the caveat in chip tooltip copy.
- **`boss_ceiling` is `unknown` for 100% of non-root nodes in real data.** **Risk:** "Survives ceiling" chip hides every branch when activated, looking like a broken filter. **Fix:** drop the chip from T2.1, OR exclude from the row pending a future enrichment that puts ceiling-relevant per-branch wage percentiles (`earnings_1yr_p25/p75`) onto the branch row.
- **Test fixtures in `frontend/src/screens/FutureScreen.test.tsx` and `frontend/src/api/mockTree.ts` set `boss_loans: "win"`** on most nodes — this is unreachable in real data with the current `_compute_boss_results`. **Risk:** vitest passes against fictional outcome distributions; vitest does not catch the dead-chip behavior. **Fix:** either (a) align mocks with the real distribution (`boss_loans: "unknown"` everywhere except the root in mocks too) so tests reflect reality, or (b) keep current mocks but explicitly add a vitest case asserting the SURVIVES filter behavior matches the real backend's outcome, not the mock's. Recommend (a) — the mocks should not lie.
- **`max_depth=3` in `build_tree` plus the architect's "depth=2" assumption.** Architect's payload-size estimate (~110 nodes max at depth 2) is fine; default is depth 3. At depth 3 with 20 branches per parent, worst case is 1 + 20 + 400 + 8000 = 8421 nodes. The `seen: set[str]` dedup in `expand()` and `CAREER_BRANCHES_MAX_ROWS=20` cap will trim that significantly, but worth flagging that adding `relatedness` adds one nullable int * (8421 nodes worst case) = ~33KB upper bound. Still negligible, but the architect's "440 bytes" was depth-2-arithmetic. Doesn't change the verdict.
- **Existing backend test fixture uses `"best_index": 2.0` (a float).** Source schema is `IntegerType`. Live data is int. The fixture's float value coerces cleanly through `as_int` but masks the contract. **Fix:** change to `"best_index": 2` in `tests/services/test_career_tree.py:91` when adding the relatedness propagation test.

##### Data Integrity Blockers
None. Nothing here would put a wrong number on a student's character card. The concerns are about FILTER UX correctness (chips that don't filter, or filter against the wrong stat), not stat-card data integrity.

#### Disclaimer Check
- [ ] AI-estimated values labeled — N/A (no Gemma estimates in this payload; all numbers are deterministic from O*NET / BLS / Karpathy)
- [ ] Confidence scores propagated where crosswalk < Tier 2 — N/A for `best_index` itself; `relatedness_tier` is already on the row and architect-approved as future visionary input
- [ ] Required disclaimer strings present in UI for this data path — **TODO**: if `boss_loans`/`boss_ceiling` chips ship, add tooltip copy explaining the per-branch data limitation
- [ ] Missing data states handled (not blank, not $0, not misleading) — **PARTIAL**: `boss_loans`/`boss_ceiling` resolve to `"unknown"` (good), and the architect's note (§5 architect review) confirms `unknown` correctly fails the SURVIVES predicate (`node.boss_X in {"win", "draw"}`). But the resulting empty-state needs a UX path — see concerns above.

#### Required Changes Before Implementation
1. **T2.1 chip set:** trim from 5 -> 3 (drop `boss_loans`, `boss_ceiling`). If kept, add tooltip copy from @fp-copywriter explaining the data limitation. Update §3 T2.1 chip table accordingly. Update §4 `bossFilter.ts` `BossFilter` union type and tests.
2. **T2.2 visionary input:** anchor the gradient at the real rank range 1..20, not the §3 T2.2 placeholder 1..50.
3. **T2.2 router seam:** confirm `_node_to_dict` in `backend/app/routers/branches.py` adds `"relatedness": node.relatedness` when the dataclass field is added — the dataclass change alone won't ship the data.
4. **Test fixtures:** align `frontend/src/api/mockTree.ts` and `FutureScreen.test.tsx` boss outcome distributions with what `_compute_boss_results` actually produces (real `boss_loans`/`boss_ceiling` are almost always `"unknown"` for non-root). Otherwise vitest will green-light a UX that fails on real data.
5. **Backend test fixture:** change `"best_index": 2.0` -> `"best_index": 2` (`backend/tests/services/test_career_tree.py:91`) to match `IntegerType` contract; add the new T2.2 relatedness propagation test against the corrected fixture.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

The T2.2 propagation is clean and the data physics check out. The blocker for the verdict is T2.1: as-specified, two of five SURVIVES chips will hide every non-root node every time (dead chips), and the test fixtures lie about boss outcomes so vitest won't catch it. Trim the chip set or tooltip the limitation before implementation kicks off.

---

## §6 Implementation Log

**Status:** PENDING

### Recommended Sequencing & PR Splits

After §11 resolution, scope is 9 enhancements (T2.4 + T3.2 cut, T3.3 deferred). Sequencing:

**Minimum shippable subset for May 18 (highest leverage):**

- **PR 1: T1.1 + T1.3** (edge labels + mini-compare). Together they convert /future from "look at the shape" to "compare and decide." Independent of every other enhancement; no backend changes; reuses existing test infrastructure. Shippable in 1–2 days. **Ship-or-die for May 18.**

**Strong follow-ups before deadline if time:**

- **PR 2: T1.2 + T1.4** (tour chips + breadcrumb). Discovery + state continuity. Independent of PR 1; no backend changes. T1.2 confirmed silent-flash only. ~1 day.

- **PR 3: T2.1 + T2.3** (boss filter + what-it-takes block). Card + filter rail polish. Independent of PR 1/2. T2.1 uses two-row constraint/improvement reorganization (decision locked, see §3 T2.1). ~1–2 days.

**Tier 2 backend-coupled:**

- **PR 4: T2.2** (relatedness gradient). Requires backend payload extension to TreeNode (`career_tree.py`) + frontend visual encoding. Backend half-day, frontend quarter-day, plus design vision call.

**Tier 3 (stretch):**

- **PR 5: T3.1** (stage labels). Trivial; bundle with any in-flight PR if room.

**Cut / deferred (NOT in this spec's PR plan):**

- ~~T2.4 "Make this my path"~~ — CUT. Post-hackathon spec.
- ~~T3.2 return banner~~ — CUT. No real refresh signal during hackathon window.
- ~~T3.3 task overlap~~ — DEFERRED post-hackathon.

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

### Design Audit (@fp-design-auditor)
**Status:** CHANGES REQUIRED

Audit date: 2026-05-01. Files audited: 8. DESIGN.md read in full before auditing.

---

#### `frontend/src/styles/reactflow-dark.css` (lines 89–134) — T1.1 edge pill CSS

##### PASS
- `.tree-edge-pill` base: `var(--font-data)`, 11px, 700, 0.4px tracking, `border-radius: 9999px` (radius-full), `backdrop-filter: blur(4px)`, `var(--shadow-sm)` — all match spec exactly.
- `.tree-edge-pill--improvement`: `rgba(125,212,163,0.15)` bg, `rgba(125,212,163,0.32)` border, `var(--color-accent-thrive)` text — match locked T1.1 tokens. Intentional rgba values per §3 T1.1.
- `.tree-edge-pill--neutral`: `rgba(45,48,96,0.85)` bg, `var(--color-border-subtle)` border, `var(--color-text-secondary)` text — match locked T1.1 tokens.
- Adjacent improvement: `var(--shadow-glow-thrive)` — correct.
- Adjacent neutral: `var(--shadow-glow-info)` — correct.

##### FAIL
- **Wrong fallback on `--color-border-subtle`**: `reactflow-dark.css:119` uses fallback `rgba(255,255,255,0.1)` which is `border-default`. Expected fallback: `rgba(255,255,255,0.06)` (`border-subtle`).

##### WARNINGS
- Selected-adjacent 1.04 scale (spec §3 T1.1 "State coverage") is absent from both the CSS and `EdgeWithLabel.tsx`. Not a token violation per se but the spec's behavior coverage is incomplete.

---

#### `frontend/src/components/tree/flow/EdgeWithLabel.tsx` — T1.1 edge component

##### PASS
- `springs` imported from `@/styles/motion`; no inline stiffness/damping.
- `transition={reducedMotion ? { duration: 0 } : springs.snappy}` — correct token for hover expansion.
- HOVER_HOLD_MS = 200ms, HOVER_GRACE_MS = 100ms — match spec.
- `pointerEvents: "auto"` on pill — correct.
- All color styling deferred to CSS classes, not inline values.

##### WARNINGS
- Adjacent 1.04 scale animation absent (same gap noted in CSS section above).

---

#### `frontend/src/components/tree/TourChipRow.tsx` — T1.2 tour chips

##### PASS
- Idle bg `rgba(184,169,232,0.08)`, border `rgba(184,169,232,0.22)`, text `text-accent-insight` — match T1.2 idle tokens.
- Hover bg `rgba(184,169,232,0.14)`, hover text `text-text-primary` — match T1.2 hover tokens.
- Empty state: `bg-[rgba(184,169,232,0.08)] border-border-subtle text-text-muted` — correct.
- Disabled: `bg-state-disabled border-border-subtle text-text-muted` — correct.
- `rounded-full px-3.5 py-2 font-body text-small font-bold` — radius, padding (8px/14px), font all match.
- `gap-1.5` (6px glyph gap) — correct.
- Pulse keyframe values and timing (`1.4s, times [0,0.15,0.5,0.85,1], easeInOut`) — match spec verbatim.
- `✦` glyph with `text-accent-insight`, `aria-hidden` — correct.
- Focus ring via `var(--color-focus-ring)` — correct.

##### FAIL
- **Hover border missing**: `TourChipRow.tsx:155` — hover state applies `hover:bg-[rgba(184,169,232,0.14)] hover:text-text-primary` but omits `hover:border-[rgba(184,169,232,0.36)]`. Spec §3 T1.2 locks hover border at `rgba(184,169,232,0.36)`.
- **Hover shadow missing**: `TourChipRow.tsx:155` — spec §3 T1.2 hover state requires `--shadow-glow-insight` (subtle). No hover shadow class present.
- **Flash stagger is a raw hardcode**: `TourChipRow.tsx:33` — `const FLASH_STAGGER_MS = 100`. Spec §3 T1.2 tokens table lists "Stagger: `stagger.slow`." `stagger.slow = 0.1s = 100ms` — correct value — but must reference the imported token, not a raw literal. If the token value changes this will silently drift. Expected: `import { stagger } from "@/styles/motion"` and `stagger.slow * 1000`.

---

#### `frontend/src/components/tree/MiniCompareStrip.tsx` — T1.3 mini-compare

##### PASS
- Container: `rounded-lg border-border-subtle bg-bp-deep px-3.5 py-3 mt-4 mb-5` — radius-lg, border-subtle, bg-deep, 14px/12px padding, space-4 top, space-5 bottom. All correct.
- Header: `font-data text-[11px] font-bold tracking-[1.5px] text-accent-info mb-3` — 11px, 700, 1.5px tracking (locked intentional deviation from Section Labels 2px — confirmed not a violation per §3 T1.3).
- Label column: `font-body text-small font-semibold text-text-secondary flex: 0 0 88px` — matches spec.
- Arrow column: `font-data text-[13px] flex: 0 0 18px` — correct.
- Value column: `font-data text-data-sm font-bold flex: 1` — correct.
- Arrow + value color: thrive (up) / muted (down, flat) — correct two-color rule.
- Container spring: `springs.smooth delay: 0.08` — correct.
- Row stagger: `i * stagger.fast` using imported token — correct.
- Row spring: `springs.snappy` — correct.

##### WARNINGS
- None.

---

#### `frontend/src/components/tree/Breadcrumb.tsx` — T1.4 breadcrumb

##### PASS
- Container: `flex flex-row items-center gap-1 mt-3 mb-3 h-6` — gap-1, space-3 top/bottom, 24px height. All correct.
- Chip: `rounded-md px-2.5 py-1 font-body text-small font-semibold whitespace-nowrap` — radius-md, 10px/4px padding, font-body text-small weight 600. All match.
- Idle: `text-text-secondary` — correct.
- Current: `bg-state-active text-accent-thrive` — correct.
- Hover: `hover:bg-white/[0.04] hover:text-text-primary` — `rgba(255,255,255,0.04)` and primary text. Correct.
- Ghost: `text-text-muted line-through opacity-50` — correct.
- Separator `›` in `font-data text-text-muted opacity-50` — correct glyph, font, color, opacity.
- Focus ring via `var(--color-focus-ring)` — correct.
- Spring: `springs.snappy` on segment append — correct.
- Exit: `{ duration: 0.15 }` — matches spec's 150ms ease-out exit.
- `transition-colors duration-fast` — correct.

##### WARNINGS
- None.

---

#### `frontend/src/components/tree/BossFilterRow.tsx` — T2.1 SURVIVES chips

##### PASS
- Active chip: `bg-accent-caution/15 border-accent-caution text-accent-caution` — match T2.1 caution active tokens.
- Idle chip: `bg-bp-surface border-border-subtle text-text-secondary` — correct.
- Hover idle: `hover:text-text-primary hover:border-border-default` — correct.
- Shape: `rounded-full px-3 py-1.5 font-body text-small font-semibold` — matches existing FilterChip pattern.
- Focus ring via `var(--color-focus-ring)` — correct.
- `transition-colors duration-normal` — correct.
- `aria-pressed` on each chip — correct.

##### FAIL
- **Wrong font on prefix label**: `BossFilterRow.tsx:43` — `font-mono` used instead of `font-data`. Spec §3 T2.1 "Prefix labels" says `font-family: --font-data` (Space Mono), explicitly noting "Identical typography across SHOW ONLY, SURVIVES, IMPROVES — locked to match existing code." `font-mono` is Tailwind's generic monospace stack (`ui-monospace, SFMono-Regular, Menlo, ...`); it does not map to `--font-data`. Expected: `font-data` class.

---

#### `frontend/src/components/tree/WhatItTakes.tsx` — T2.3 what-it-takes block

##### PASS
- Spacing: `mt-4 mb-4` (space-4 each) — correct.
- Title: `font-body text-small font-bold text-text-primary mb-2` — matches spec title exactly.
- Title spring: `springs.smooth` — correct.
- Glyph `↑`: `font-data text-[13px] font-bold text-accent-thrive` — correct, always thrive per glyph rule.
- Bullet gap: `gap-2` (space-2) — correct.
- `items-baseline` on bullet row — correct.
- Bullet spring: `springs.snappy` — correct.
- Stagger: `delay: 0.06 * i` — 60ms, the locked derived value called out in §3 T2.3 tokens table. NOT a violation.
- Reduced motion pattern — correct.
- Root-guard via `soc_code` comparison — correct.

##### FAIL
- **Bullet label and value collapsed into one span**: `WhatItTakes.tsx:176` — `<span className="font-body text-small text-text-primary">{bullet.text}</span>`. Spec §3 T2.3 "Bullets" defines two distinct styled parts: the inline label ("Education:" / "Experience:" / "Top stat shift:") in `font-body text-small` weight **600** `--color-text-secondary`, and the inline value in `font-body text-small` weight **400** `--color-text-primary`. The implementation renders both as a single string in weight 400 / text-primary — the label portion is missing weight 600 and `text-text-secondary`. The bullet data model must expose `{labelText, valueText}` separately so they can be rendered in two styled spans.

##### WARNINGS
- The current i18n template approach bakes label and value into one string (e.g. "Education: Bachelor's → Master's"). A split requires restructuring the `Bullet` interface and `buildBullets` output, or splitting the rendered string at the `: ` boundary. Either approach is implementer's choice, but the spec requires the visual distinction.

---

#### `frontend/src/components/tree/StageAxisLabels.tsx` — T3.1 stage labels

##### PASS
- `opacity: 0.06` — locked ghost level, correct.
- `font-display font-bold text-text-primary` — correct font, weight, color.
- `fontSize` computed as `clamp(20, 36/sqrt(z), 64)` — matches spec formula exactly.
- `letterSpacing: "0.02em"`, `lineHeight: 1`, `whiteSpace: "nowrap"` — all correct.
- `top: TOP_OFFSET_PX` where `TOP_OFFSET_PX = 16` (space-4) — correct.
- `transform: "translate(-50%, 0)"` — correct.
- `aria-hidden="true"` — correct.
- `pointer-events-none` — correct.
- `hidden tablet:block` (hides <768px) — matches spec mobile breakpoint.
- World-space x via `a.worldX * zoom + x` — correct viewport transform.
- Y pinned (does not follow pan) — correct.
- `zIndex: 1` — correct layering.
- Missing-tier anchors not rendered — correct edge-case handling.

##### FAIL
- **Entry animation absent**: `StageAxisLabels.tsx` has no Framer Motion import. Spec §3 T3.1 "Animation" requires `opacity 0 → 0.06` via `springs.gentle` on initial render (`prefers-reduced-motion` renders immediately at 0.06, skipping the fade). The implementation renders statically at `opacity: 0.06` for all users — `springs.gentle` entry is entirely missing. Expected: wrap each label `<span>` in `<motion.span>` with `initial={{ opacity: 0 }} animate={{ opacity: 0.06 }} transition={reducedMotion ? { duration: 0 } : springs.gentle}`.

---

### Overall Verdict: CHANGES REQUIRED

#### Minimum-fix list (6 items)

1. **`reactflow-dark.css:119`** — Fix `--color-border-subtle` fallback: `rgba(255,255,255,0.1)` → `rgba(255,255,255,0.06)`.

2. **`TourChipRow.tsx:155`** — Add `hover:border-[rgba(184,169,232,0.36)]` and `hover:shadow-glow-insight` to the normal-state chip class string.

3. **`TourChipRow.tsx:33`** — Replace raw `100` with token: `import { stagger } from "@/styles/motion"` and use `stagger.slow * 1000`.

4. **`BossFilterRow.tsx:43`** — Replace `font-mono` with `font-data` on the SURVIVES prefix label span.

5. **`WhatItTakes.tsx:176`** — Split the bullet span into two: `<span className="font-body text-small font-semibold text-text-secondary">{bullet.labelText}</span><span className="font-body text-small text-text-primary">{bullet.valueText}</span>`. Update the `Bullet` interface and `buildBullets` to produce separate `labelText`/`valueText` fields.

6. **`StageAxisLabels.tsx`** — Add `springs.gentle` entry fade. Import `motion`, `useReducedMotion` from `framer-motion` and `springs` from `@/styles/motion`. Wrap each label span in `<motion.span initial={{ opacity: 0 }} animate={{ opacity: 0.06 }} transition={reducedMotion ? { duration: 0 } : springs.gentle}>`.

Priority order: 2+3 (TourChip hover correctness and token-drift risk) > 4 (font token on a visible label) > 5 (requires the most restructuring) > 6 (missing but purely cosmetic entry animation) > 1 (wrong fallback, live value is correct).

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewed:** 2026-05-01
**Scope reviewed:** Backend `career_tree.py` + `branches.py` (T2.2 propagation), frontend filter chain composition (`FutureScreen.tsx`), Breadcrumb state machine (`Breadcrumb.tsx` + `FutureScreen.tsx` orchestration), edge label hover state (`EdgeWithLabel.tsx`), tour chip cleanup (`TourChipRow.tsx`), `mockTree.ts` updates, type contract (`types/tree.ts`), `_node_to_dict` recursion, `treeFlowLayout.ts` relatedness gradient, `StageAxisLabels.tsx`. Out of scope: T2.4, T3.2, T3.3 (cut/deferred).

#### Summary
Backend T2.2 propagation is genuinely clean — three-line surgical change with defaulted dataclass field, `as_int` coercion (defensive against future float drift), and additive router serialization. All 23 backend tests pass including three new T2.2 tests covering int / float-coerce / null cases. Frontend pure data layers (edgeLabel, tourRanking, bossFilter, buildBreadcrumbSegments) are all well-tested and correct in isolation.

The blocker is in the **FutureScreen orchestration layer** between independently-correct units. Specifically, the breadcrumb state machine has a one-shot wipe bug that defeats the entire point of T1.4's persistence promise: hide the selection via filter and the breadcrumb vanishes entirely, never reappearing. The unit tests for `Breadcrumb.tsx` validate the component contract; they do not exercise the orchestration that's broken. Compounding this, the P1 integration tests called out in §4 ("breadcrumb_persists_across_filter_toggle", "tour_chip_flashes_top_3", "boss_filter_row_renders_3_chips") are missing from `FutureScreen.test.tsx`, which is exactly the suite that would have caught the snapshot wipe.

Two more real issues sit just behind the breadcrumb bug: an empty-state label that excludes boss filters (the boss-filter-only empty case shows a missing-context message), and stale `worldX` anchors in `StageAxisLabels.tsx` due to a useMemo dep that never changes (filtered tree → labels float at old positions).

T2.2 backend extension is approved as-is. The frontend issues are fixable in a small follow-up pass; nothing is fundamentally architected wrong.

#### Critical Findings (BLOCKER)

##### 🔴 1. Breadcrumb snapshot is one-shot — gets wiped the moment filter hides selection

**Location:** `frontend/src/screens/FutureScreen.tsx:307-336`

**Impact:** Defeats the locked T1.4 spec behavior ("Persists across filter toggles so a hidden segment renders as a ghost rather than vanishing"). User selects an L2 endpoint → applies a filter that hides it → entire breadcrumb disappears (snapshot zeroed). User clears the filter → breadcrumb stays gone. The "ghost segment" UX is unreachable through normal user flow.

**Trace:**
1. User selects `endpoint-X-...`. Snapshot effect fires → `breadcrumbSnapshot = [root, L1, X]`. Breadcrumb renders 3 segments.
2. User toggles a filter that recursively prunes X (and likely its parent L1). `nodeRefsById` no longer contains X.
3. Effect at `:310-314` fires: `selectedNodeId && !nodeRefsById.has(selectedNodeId)` → `setSelectedNodeId(null)`.
4. Re-render. Effect at `:325-336` reads `selectedNodeId == null` → `setBreadcrumbSnapshot([])`.
5. `breadcrumbSegments = []` → `<Breadcrumb segments={[]}>` returns null.
6. User clears the filter. Snapshot is still `[]`. Nothing brings it back.

The `findPathToNodeId` lookup is correctly run against `treeData.tree` (the **unfiltered** tree, per the in-code comment "recompute the lineage from the *current* tree (not the filtered one) so the snapshot survives a later filter that hides one of the ancestors") — but the very next branch in the same effect wipes the snapshot before `findPathToNodeId` is ever consulted, because `selectedNodeId == null` is checked first.

**The Fix:** Distinguish "user cleared selection" from "filter hid selection." Two viable patterns:

```ts
// Option A — only wipe snapshot on a true user-initiated root click.
// In handleSelectNode (currently the only user-initiated path that
// passes null), set the snapshot to [] alongside the selection.
// Remove the snapshot-wipe branch from the post-render effect.
const handleSelectNode = useCallback((id: string | null) => {
  setSelectedNodeId(id);
  if (id == null) setBreadcrumbSnapshot([]);
  if (id != null) setSheetOpen(true);
}, []);

useEffect(() => {
  if (!treeData) return;
  if (selectedNodeId == null) return;        // <-- no wipe; let snapshot survive
  const path = findPathToNodeId(treeData.tree, selectedNodeId);
  if (path == null) return;
  setBreadcrumbSnapshot(path.map((n) => ({ socCode: n.soc_code, title: n.title })));
}, [selectedNodeId, treeData]);

// And in the breadcrumb segment click handler — clearing root already
// explicitly wipes, which stays correct.
```

Option B — track a separate `selectionClearReason` ref to make the wipe conditional. Heavier; A is preferred.

After the fix, also add a P1 integration test that was already called out in §4 (`FutureScreen.test.tsx::breadcrumb_persists_across_filter_toggle`) so this never regresses.

#### Serious Findings (CHANGES REQUIRED)

##### 🟠 2. `filterEmptyLabel` ignores `bossFilters` entirely — empty-state message renders without filter context

**Location:** `frontend/src/screens/FutureScreen.tsx:519-538`

**Impact:** Activate ONLY a boss filter (e.g., "Survives AI") that empties the tree → the FilterEmptyState card renders the i18n string `future.filter.empty.message` with `{filters}` replaced by an empty string. Reads as a broken sentence to the student. The "anyFilterActive" gate (line 513) DOES include bossFilters, so the empty state shows; the label just has no content for the boss case.

**The Problem:** The useMemo only checks `educationFilters` and `statFilters`. Boss filter labels are never appended.

**The Fix:**

```ts
const filterEmptyLabel = useMemo(() => {
  const labels: string[] = [];
  if (educationFilters.has("bachelors")) labels.push(t("future.filter.bachelors"));
  if (educationFilters.has("masters")) labels.push(t("future.filter.masters"));
  if (educationFilters.has("doctoral")) labels.push(t("future.filter.doctoral"));
  if (bossFilters.has("boss_ai")) labels.push(t("future.survives.ai"));
  if (bossFilters.has("boss_market")) labels.push(t("future.survives.market"));
  if (bossFilters.has("boss_burnout")) labels.push(t("future.survives.burnout"));
  if (statFilters.has("earnings")) labels.push(t("future.stat.earnings"));
  if (statFilters.has("ai_resilient")) labels.push(t("future.stat.aiResilient"));
  if (statFilters.has("growth")) labels.push(t("future.stat.growth"));
  // ...rest unchanged
}, [educationFilters, statFilters, bossFilters, t]);  // <-- add bossFilters dep
```

Add a regression test fixture: `boss_filter_only_empty_state_includes_chip_label`.

##### 🟠 3. `StageAxisLabels` worldX anchors are stale across filter changes

**Location:** `frontend/src/components/tree/StageAxisLabels.tsx:44-73`

**Impact:** The three ghost stage labels ("Now" / "Next move" / "Move after") render at world-x positions computed only on first render. When the user filters the tree (which reshapes node positions in the React Flow store), the labels stay anchored to the original positions — they will visibly drift off the actual stage columns.

**The Problem:** `useMemo` deps are `[reactFlow, enabled]`. `reactFlow` is the stable instance returned by `useReactFlow()` — its identity never changes. `enabled` is a boolean prop. The memo never invalidates on a filter-driven node-set change because nothing in the deps observes the underlying node store.

```ts
const anchors = useMemo(() => {
  // ...uses reactFlow.getNodes()
}, [reactFlow, enabled]);  // <-- reactFlow stable; getNodes() result not observed
```

**The Fix:** Observe the node count or a node-set fingerprint via `useNodes()` from `@xyflow/react` and key the memo off that:

```ts
import { useNodes } from "@xyflow/react";

const nodes = useNodes();  // re-renders whenever the node set changes
const anchors = useMemo(() => {
  if (!enabled || nodes.length === 0) return [];
  const root = nodes.find(...);
  // ...same logic but on `nodes` (already typed-narrowed in scope)
  return result;
}, [nodes, enabled]);
```

This component is also missing the P2 test (`stage_axis_labels_render_at_correct_x`) called out in §4. Add it after the fix; verify `worldX` updates when nodes change.

#### Moderate Findings 🟡

##### 🟡 4. `EdgeWithLabel` hover/exit timers are not cleared on unmount

**Location:** `frontend/src/components/tree/flow/EdgeWithLabel.tsx:94-129`

**Impact:** If an edge unmounts (filter prunes a branch the user is hovering, or build reload mid-hover) while a 200ms hover-hold or 100ms exit-grace timer is pending, the timer fires `setHovered(...)` on the unmounted component. React logs a warning; tiny memory leak per orphaned edge. Not a 3am page; will show up as console noise during filter-heavy QA.

**The Fix:**

```ts
useEffect(() => {
  return () => {
    if (hoverTimer != null) window.clearTimeout(hoverTimer);
    if (exitTimer != null) window.clearTimeout(exitTimer);
  };
}, [hoverTimer, exitTimer]);
```

Or — preferred — switch the timers from `useState` to `useRef` and clear in a single mount-only cleanup effect. The state-based pattern triggers re-renders for what is purely transient mechanism.

##### 🟡 5. Test fixtures in `FutureScreen.test.tsx` still carry `boss_loans: "win"` / `boss_ceiling: "win"` distributions

**Location:** `frontend/src/screens/FutureScreen.test.tsx` (multiple lines: 152, 155, 172, 175, 193, 196, 387, 390, 407, 410, 428, 431, 449, 452, 611, 614, 632, 635, 654, 657)

**Impact:** Data-reviewer's required change #4 said: "align mockTree.ts AND FutureScreen.test.tsx boss outcome distributions." `mockTree.ts` was updated (`boss_loans: "unknown"` for non-root). `FutureScreen.test.tsx` was NOT. These fixtures still produce fictional `boss_loans: "win"` distributions that no real backend would emit.

In practice the impact is small because BossFilter shipped with `boss_loans` and `boss_ceiling` chips REMOVED — no production code consumes those fixture fields. So this is dead test data, not actively misleading test data. Still: the data reviewer's directive was explicit, and the fixtures will mislead future readers about what real backend payloads look like.

**The Fix:** Mass-replace `boss_loans: "win"` → `boss_loans: "unknown"` and `boss_ceiling: "<anything>"` → `boss_ceiling: "unknown"` for non-root nodes in `FutureScreen.test.tsx`. Root node may keep realistic values (root scoring DOES populate those bosses honestly).

#### Minor Findings 🔵

##### 🔵 6. P1 integration tests called out in §4 are missing from `FutureScreen.test.tsx`

The spec listed these P1 tests:
- `tour_chip_flashes_top_3` (T1.2)
- `breadcrumb_persists_across_filter_toggle` (T1.4) — would have caught Finding #1
- `boss_filter_row_renders_3_chips` (T2.1)

None exist. Unit tests for the constituent pieces are present and pass, but the orchestration is unverified end-to-end. The breadcrumb bug above is the cost of skipping these.

##### 🔵 7. `MiniCompareStrip.isNarrowViewport` reads `window.innerWidth` once at render — no resize listener

**Location:** `frontend/src/components/tree/MiniCompareStrip.tsx:88-91`

The narrow-vs-wide header swap happens at component render time and never updates if the user resizes the window across the 480px boundary mid-session. Acceptable for desktop demo usage; would manifest in a narrow desktop window the student stretches mid-flow. Not blocking.

#### What's Actually Good
- **Backend T2.2 propagation is exemplary** — `as_int(row.get("best_index"))` mirrors the existing `as_float`/`as_int` pattern, defaulted dataclass field means no breakage at any call site, single serialization seam in `_node_to_dict`, and three new pytest cases (int / float-coerce / null) cover the contract surface.
- **`relatednessStyle()` in `treeFlowLayout.ts`** correctly anchors at rank 1..20 per the data reviewer's empirical finding (not the placeholder 1..50). Linear interpolation, null-clamps to rank-20 (most translucent) per the architect's "honest 'we don't know'" recommendation. Different ranges for L1 vs L2 edges preserves the existing visual hierarchy.
- **Filter chain composition (`filteredTree` useMemo)** is genuinely AND'd correctly. Each filter preserves the root TreeNode (with its original `median_wage`/`res`/`grw`), so `filterTreeByStats` consuming the post-edu-post-boss tree as its `root` reference still gets stable comparison anchors. Order independence verified by inspection.
- **`bossFilter.ts` SURVIVES semantics** are honest — `unknown` correctly fails the predicate (matches data-reviewer spec). 13 unit tests cover win/draw/lose/unknown/null + multi-select AND + recursive L1+L2 + immutability.
- **`pickEdgeLabel` priority chain** is well-structured (education > experience > pay > relatedness), with appropriate threshold ($10k pay) and rank gates (≤5 close, ≥11 stretch). 20 tests for it.
- **Tour chip cleanup is correct** — `stagTimeoutsRef` flush in mount cleanup; `ttlTimeoutRef` cleared on unmount per chip. No dangling timers.
- **Breadcrumb component itself (`Breadcrumb.tsx`) is clean** — `buildBreadcrumbSegments` handles ghost state, nodeId resolution, and current-marking correctly. The bug in Finding #1 is in the orchestration that uses it, not the component contract.
- **Defensive double-frame retry in `FitOnTreeChange`** — first frame reads node positions; if React Flow store hasn't absorbed them yet, second frame retries with a snap. Solid pattern for the React-Flow-renders-on-its-own-cadence pain point.

#### Recommendations (priority-ordered)
1. Fix breadcrumb snapshot wipe (Finding #1) — BLOCKER for T1.4 to actually deliver its spec behavior. Routes to: implementing agent.
2. Add `bossFilters` to `filterEmptyLabel` (Finding #2). Routes to: implementing agent.
3. Fix `StageAxisLabels` stale anchors via `useNodes()` (Finding #3). Routes to: implementing agent.
4. Add the three missing P1 integration tests in `FutureScreen.test.tsx` (Finding #6) — including the regression test for #1. Routes to: `@test-writer`.
5. Clear EdgeWithLabel timers on unmount (Finding #4). Routes to: implementing agent.
6. Align FutureScreen test fixtures with real boss-outcome distributions per data reviewer's required change #4 (Finding #5). Routes to: `@test-writer`.

#### Questions for the Author
- Was the breadcrumb integration deliberately left untested at the FutureScreen level, or did the missing P1 tests get dropped during the implementation pass?
- Why was `useNodes()` not used for `StageAxisLabels` anchors (vs `reactFlow.getNodes()` inside a useMemo)? `useNodes` re-renders on node-set changes; the current pattern doesn't.
- For the boss-only empty-state label gap (Finding #2): is there any scenario where bossFilters get a different empty-state copy intentionally? Reading §3 T2.1, I don't see one — flagging in case I missed it.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

Backend T2.2 ships as-is. Frontend Findings #1 (BLOCKER for T1.4 spec compliance), #2, and #3 must be fixed before verification. Findings #4–#6 should be addressed but are not strictly blocking; if the implementing agent has bandwidth, fold them in.

---

## §9 Verification

**Status:** FAILED
**Verified:** 2026-05-01 20:05

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | PASS (pre-existing failures only) | 69 errors in 18 files — all pre-existing. 4 errors in `branches.py` confirmed pre-existing via stash to main baseline. Zero new errors in `career_tree.py` or any spec-introduced file. |
| Tests (pytest) | PASS | 1298 passed, 0 failed |

### Pipeline (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | FAIL | 4 errors in `src/data/edgeLabel.test.ts` |
| Tests (vitest) | PASS | 838 passed, 0 failed (66 test files) |
| Production build (Vite) | PASS | Build completed (721 modules) |

#### TypeScript Errors — `src/data/edgeLabel.test.ts`

```
src/data/edgeLabel.test.ts(279,14): error TS18047: 'ctx' is possibly 'null'.
src/data/edgeLabel.test.ts(280,14): error TS18047: 'ctx' is possibly 'null'.
src/data/edgeLabel.test.ts(281,14): error TS18047: 'ctx' is possibly 'null'.
src/data/edgeLabel.test.ts(298,14): error TS18047: 'ctx' is possibly 'null'.
```

All four errors are in the same pattern: `ctx` is typed `EdgeHoverCtx | null`. The test uses `if (ctx!.kind === "pay")` to branch, but the non-null assertion on the condition (`ctx!`) does not narrow `ctx` to non-null inside the block — TypeScript strict mode still considers `ctx` possibly null at lines 279–281. Same issue at line 298 inside `if (ctx!.kind === "experience")`. Fix: change `if (ctx!.kind === "pay")` → `if (ctx && ctx.kind === "pay")` (and same for the experience branch).

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | TypeScript FAIL | `ctx` possibly null in `edgeLabel.test.ts` lines 279, 280, 281, 298 | None — surfaced to implementing agent per instructions |

---

## §10 Discussion

### Cut from this spec (originally proposed)

These were proposed during the @fp-product-partner brainstorm but cut after §11 author review. Detailed rationale + preserved scope in §3 sub-sections of each:

| Item | Why cut |
|------|---------|
| **T2.4 "Make this my path" CTA** | Most complex single feature. Atomic re-root requires new backend endpoint. Value is "behavior change," not "decision support." Risk-to-deadline ratio worst in spec. Park as standalone post-hackathon spec. |
| **T3.2 "What changed?" return banner** | BLS / O*NET ingestion is manual + quarterly; data won't refresh during May 18 hackathon window, so banner never triggers. Theater otherwise. Park for when refresh cadence becomes real. |
| **T3.3 Task-overlap chip on SOC card** | DEFERRED post-hackathon (not strictly cut). Two MCP fetches per click is 400–800ms latency. Caching + overlap algorithm is its own subspec. Strongest post-hackathon candidate. |

### Out of scope (explicit non-goals from brainstorm)

These were considered during the brainstorm and intentionally excluded — they did NOT make it into the original 11:

| Item | Why excluded |
|------|--------------|
| HMN improvement filter | Students don't yet feel ownership of HMN as a stat; boss filters (T2.1) hit the same emotional ground harder. |
| Side-by-side compare panel | The mini-compare strip on the existing card (T1.3) is 80% of the value at 20% of the cost. A second panel would crowd desktop and double the mental model. |
| Edge animations / path-tracing | Cool, costly, doesn't change a decision. |
| More filter chips beyond what's in T2.1 | Two-row reorganized layout is the visual ceiling. Adding a third row would push the tree below the fold on smaller laptops. |
| ROI improvement filter | ROI is build-level (school + program + cost) and doesn't vary per branch — no meaningful filter axis. |
| Branch-level confidence/quality flags surfaced as filters | Adds chrome; data confidence is already implicit in the relatedness rank (T2.2). |
| Red/regression color on edge labels (T1.1) | Two colors only — green improvement, muted neutral. Career framing isn't winners-and-losers; "Pivot Lateral" with lower pay isn't bad, it might have better life-fit. |
| Tour chips driving Gemma chat opener (T1.2) | Silent flash only — feeding Gemma a list and hoping it echoes the names is fragile. Chat narration of tours is a follow-up spec. |

### Discussion Log

```
[2026-05-01 18:00] @fp-product-partner → human
Brainstorm output: 11 ideas tier-tagged, "don't build" list, recommended sequencing.
Highest-leverage pair is T1.1 (edge labels) + T1.3 (mini-compare).
```

```
[2026-05-01 20:30] @faang-staff-engineer → implementing agent + @test-writer
Code review complete. CHANGES REQUIRED.

Backend T2.2 ships clean. Three frontend issues need fixes before verification:

  1. (BLOCKER) FutureScreen breadcrumb snapshot is one-shot — wiped the
     moment a filter hides the selection. Defeats T1.4's "persists across
     filter toggles" promise. See §8 Code Review Finding #1 for the
     trace and fix (move the wipe out of the post-render effect into
     handleSelectNode).

  2. filterEmptyLabel ignores bossFilters → empty-state with only a
     boss filter active renders a broken sentence. Fix: add the three
     boss-chip labels and bossFilters to the deps array.

  3. StageAxisLabels worldX is computed once via useMemo with stable
     deps; switch to useNodes() so it tracks filter-driven node changes.

Plus: three missing P1 integration tests in FutureScreen.test.tsx
(breadcrumb_persists_across_filter_toggle, tour_chip_flashes_top_3,
boss_filter_row_renders_3_chips) — needed to prevent regression of
the breadcrumb fix in particular. Routes to @test-writer.

Two non-blocking moderates: EdgeWithLabel timer cleanup; FutureScreen
test fixtures still carrying boss_loans/boss_ceiling="win" distributions
that mockTree was already corrected for.

Full findings, severity rationale, and code patches in §8 Reviews →
Code Review.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Open Questions — RESOLVED 2026-05-01

All six open questions from the original draft were resolved by the author before the agent pipeline kicks off.

| # | Question | Resolution |
|---|----------|-----------|
| 1 | T2.4 "Make this my path" backend approach (a/b/c)? | **CUT.** Most complex single feature; behavior change, not decision support. Post-hackathon spec. (See §10.) |
| 2 | T2.1 three-filter-row crowding (a/b/c)? | **(c) Reorganize to two rows.** SHOW ONLY + SURVIVES on row 1 (constraints), IMPROVES on row 2 (deltas). Semantic grouping; no tree-height cost. (See §3 T2.1.) |
| 3 | T3.2 "What changed?" return banner — does a real refresh signal exist? | **No (during hackathon window). CUT.** BLS / O*NET refresh is quarterly; banner would never trigger. Theater otherwise. (See §10.) |
| 4 | T3.3 task overlap — confirm post-hackathon? | **Confirmed deferred.** New MCP fetches + caching + algorithm is its own subspec. Strongest post-hackathon candidate. (See §3 T3.3, §10.) |
| 5 | T1.2 tour chips → Gemma chat opener integration? | **Silent flash only.** Tour chips fire `onHighlight` directly via BranchHighlightDriver API. Chat opener stays generic. Narration of tours is a follow-up spec. (See §3 T1.2.) |
| 6 | T1.1 edge label color semantic — confirm green = improvement / muted = neutral? | **Confirmed two colors only.** No red/regression color. Career framing isn't winners-and-losers. (See §3 T1.1, §10.) |

### Follow-up Items (post-completion)

- Once T1.1 + T1.3 ship, run a quick A/B-style visual check between /branches and /future with hackathon judges / beta students. The "decision tool" framing should make /future feel categorically different from /branches.
- T2.4 "Make this my path" — when picked back up, consider also adding a "Path history" breadcrumb showing the chain of re-roots (`Original career → re-rooted to X → re-rooted to Y`).
- T3.3 task overlap is the most truthful answer to "what does it actually feel like to switch?" — strong candidate for first post-hackathon spec.
- T3.2 banner — re-evaluate when there's a real `gold.promoted_at` cycle the student would actually notice between visits.
