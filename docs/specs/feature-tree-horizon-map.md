# Feature: Tree-as-Horizon-Map on /branch-tree

## Claude Code Prompt

```
Read the spec at docs/specs/feature-tree-horizon-map.md in its entirety.

PRECONDITION: feature-tree-as-map.md must be COMPLETE (it is — shipped 2026-04-28). This
spec REPLACES the tree column of that screen; it does NOT replace the chat column,
the embedded GemmaChat variant, the BranchHighlightDriver, or any backend surface.
If feature-tree-as-map.md is not COMPLETE, STOP and alert human.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1-§4 (frontend-only restructure: new horizon-map
     component replacing BranchTreeFlow on /branch-tree, no backend changes, no schema
     changes, no Gemma surface changes; the bidirectional flash binding is preserved
     via className contract on chips instead of React Flow nodes).
   - @fp-data-reviewer is SKIPPED — no pipeline / gold-zone / formula / crosswalk
     changes; only new READ paths over existing CareerBranch fields. See §2 Decision
     #11.
   - @genai-architect is SKIPPED — voice contract unchanged, no Gemma prompts touched,
     opener path unchanged.
   - Both write findings to §5 (Architecture Review).
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to fill §3 (UI/UX Design): horizon-map column layout,
     lane chrome, chip anatomy, "+N more" expand affordance, "Hide supplemental"
     toggle, empty-lane treatment, mobile drawer inheritance from feature-tree-as-map.md.
   - §3 becomes the pixel-perfect implementation target.
   - Do NOT redesign GemmaChat (still embedded variant from feature-tree-as-map.md).
   - Do NOT redesign the screen-level grid (tree col-span-5 + chat col-span-7 stays).

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec).
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update only tests listed in "Authorized Test Modifications".
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP
     and escalate to human via §10.
   - Reuse-don't-rebuild list (§4) is binding — agents must honor it.
   - Log all work to §6 (Implementation Log).
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). After 3:
     escalate via §10.

4. TESTING
   - Invoke @test-writer to review the full spec.
   - @test-writer MUST review §4 Testing Impact Analysis.
   - Implement all tests in "New Tests Required" by priority (P0 first).
   - Run ALL tests (pytest + vitest) to catch regressions.
   - If still broken after 3 attempts: escalate to human via §10.

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical Brightpath token + pattern compliance
     against the §3 mocks.
   - Writes findings to §8 (Design Audit).
   - If CHANGES REQUIRED: route to implementer via §10.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
   - Pay specific attention to: lane-assignment correctness on the long tail of
     `related_education_level` values (some-college vs no-credential vs postsecondary
     nondegree are all rank=1 — no double-assignment), the `education_level_name`
     null fallback (treats unknown build edu as bachelor's-equivalent), the
     "Hide supplemental" filter not breaking the cap-at-6 + "+N more" math when
     overflow disappears, BranchHighlightDriver candidate-set keying on chip ids
     (not React Flow node ids — the id schema changes when we drop the dendrogram).
   - Reviewer writes findings to §8 (Code Review).
   - If APPROVED: proceed to step 7.
   - If CHANGES REQUIRED: route to originating agent via §10.
   - If BLOCKER: STOP, alert human.

7. VERIFICATION
   - Invoke @fp-builder to run full build verification.
   - Backend: ruff check, mypy app/, pytest (no new backend tests; sentinel run only).
   - Frontend: tsc --noEmit, vitest run, vite build.
   - Log results to §9 (Verification).
   - If all green: mark status COMPLETE.

8. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Check off all completed Success Criteria in §1.
   - Update §6 Implementation Log, §7 Test Coverage, §8 Reviews.
   - Generate report to reports/feature-tree-horizon-map-YYYY-MM-DD.md.
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
| Spec Version | 1.0 |
| Last Updated | 2026-04-29 (HTML mockup added; §3 references it as binding visual target) |
| Blocked By | — |
| Related Specs | `feature-tree-as-map.md` (COMPLETE 2026-04-28 — defines the screen-level grid, embedded `GemmaChat` variant, `BranchHighlightDriver`, voice contract appendix; this spec replaces ONLY the tree column body), `feature-ask-gemma.md` (COMPLETE — provides `POST /chat/ask`, `AskScope` discriminator, `askGemma` client), `feature-chat-guardrails.md` (voice rules — inherited verbatim, untouched) |

---

## §1 Feature Description

### Overview
Replace `/branch-tree`'s React Flow dendrogram with a 3-lane "horizon map" of clickable chips, bucketed by **how much more education each branch requires relative to the student's current build**. Lanes: **Lateral** (same degree or less), **Step Up** (one credential more), **Long Climb** (two or more credentials more). The chat column from `feature-tree-as-map.md` is unchanged; only the left column's body changes.

### Problem Statement
The just-shipped `feature-tree-as-map.md` solved orientation by demoting the tree to a context rail and putting Gemma in the foreground — but it kept the underlying React Flow dendrogram. With ~22 L1 branches × multi-children per branch (median 20 destinations per source, max 75 per `consumable.career_branches`), the dendrogram requires aggressive `fitView` zoom-out: nodes render ~5px tall, only one branch fits in viewport, the four regex-derived L1 labels (`"Specialize"` / `"Go Management"` / `"Pivot Lateral"` / `"Stay Technical"` from `treeFlowLayout.ts::deriveBranchLabel`) carry no real meaning, and the bidirectional flash highlight from feature-tree-as-map silently fails because matched nodes are off-screen.

The product diagnosis (`@fp-product-partner` 2026-04-29): the *job* of the tree has shifted from wayfinding (user drives) to **a legend Gemma points at** (Gemma drives, user reads). A dendrogram gives the user a layout but not a legend; with 22 branches it gives them neither. The fix is a subway-map metaphor — three lanes that describe the *shape of the decision* in a vocabulary Gemma can use ("the long road through a master's" → Long Climb lane lights up).

### Success Criteria
- [ ] `/branch-tree`'s tree column renders 3 horizontal lanes — **Lateral**, **Step Up**, **Long Climb** — each with a header (label + plain-English subtitle) and a row of branch chips.
- [ ] Each chip is bucketed by `assign_lane(branch.related_education_level, build.career.education_level_name)` (see §2 Decision #1 for the binding pseudocode).
- [ ] Each lane shows at most 6 chips; overflow renders a `"+N more"` affordance that expands the lane inline (no navigation, no scope change). Confirmed load-bearing: SOC 11-9199 Lateral has ~21 chips post-bucketing.
- [ ] Within-lane sort: `Primary-Short` → `Primary-Long` → `Supplemental` by `relatedness_tier`, then `relatedness DESC` as tiebreaker.
- [ ] A "Hide supplemental" toggle in the column header filters `relatedness_tier == "Supplemental"` from all lanes when active. Default off. Persists per session, resets on screen mount.
- [ ] Each chip displays: `to_title` (truncated 32 chars), dominant stat-delta badge (largest abs of `delta_ern`/`delta_grw`/`delta_hmn`/`delta_res`, signed), `unlock` (when present), experience badge (only when `related_experience_tier in {"mid", "senior"}`), relatedness color bar on left edge.
- [ ] Clicking a chip sets `selectedNodeId` to the chip's React-derived id, updates `chatScope.target_id` to the chip's `to_soc`, clears chat history, re-fires the opener — identical contract to `feature-tree-as-map.md`'s tree-click behavior. The 300ms debounce + `sessionRef` bump are inherited.
- [ ] When Gemma's response names a branch verbatim (matched by `BranchHighlightDriver`), the corresponding chip flashes via the `branch-flash` className → CSS keyframe (`branchFlashPulse`, `accent-info`, 600ms). Multi-match stagger 200ms preserved.
- [ ] Empty-lane handling: when a lane has 0 chips post-bucketing, render the lane header + a `text-text-muted` empty-state line ("no [subtitle] paths in this data"). Do NOT hide the lane.
- [ ] Mobile (<768px) inherits `feature-tree-as-map.md`'s collapsible "Show map" drawer pattern unchanged. The horizon map renders inside the drawer body when expanded.
- [ ] No backend changes. `_context_for_branch`, the chat-time tool allowlist, the voice contract, and the system prompt appendix all unchanged from `feature-tree-as-map.md`.
- [ ] No new Pydantic models, no new Iceberg fields, no new MCP tools. Frontend-only derivation from existing `CareerBranch` fields read via `getTree(build.build_id)`.
- [ ] Voice contract holds: existing voice battery (`test_ask_gemma_voice.py`) all green; nothing in the horizon-map presentation surface causes a regression.
- [ ] Full build green: `ruff`, `mypy`, `pytest`, `tsc --noEmit`, `vitest run`, `vite build`.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Lane assignment is `branch_edu_rank − build_edu_rank`** with the 6-value rank table (HS=0, no-credential/postsecondary-nondegree/some-college=1, AA=2, BA=3, MA=4, doctoral=5). delta ≤ 0 → Lateral; delta == 1 → Step Up; delta ≥ 2 → Long Climb. | Anchors lanes to *the student's effort to reach this branch*, not absolute education level. A Bachelor's-bound student sees other Bachelor's roles as Lateral; a HS-only student sees the same role as Long Climb. The vocabulary maps to how students think ("can I do this with what I'm already doing, or do I need more school?"). | (a) Absolute education tier as lanes — rejected: gives identical layout to every student, defeats the personalization. (b) Time-since-graduation lanes via `related_experience_years` — rejected: that field is the *requirement* of the destination, not "years from now"; meaning slip would mislead. (c) `relatedness_tier` as lanes — rejected: 49.4% of rows are Supplemental which would dominate one lane; the tiers describe *similarity*, not *effort*. |
| 2 | **`related_education_level == None` → Lateral lane with muted "level unknown" treatment.** | 3.5% of rows (554/15944). A separate "Unknown" lane would be too sparse to justify; quietly placing them in Lateral with a muted chip prevents users from thinking the data is broken while still surfacing them for chat-driven exploration. | (a) Hide null rows — rejected: silently drops 3.5% of the decision space. (b) Dedicated "Lateral (level unknown)" sub-lane — rejected: lane proliferation kills the 3-lane mental model. |
| 3 | **`build.career.education_level_name == None` → treat as Bachelor's-equivalent (rank=3).** | 96% of `CareerOutcome` rows have a populated `education_level_name`; the 4% null are mostly residual / "All Other" SOCs. Bachelor's is the modal entry-level for college-bound students which is the audience FutureProof targets. | (a) Treat null build as HS — rejected: would misclassify the Lateral lane for most college-track students. (b) Refuse to render — rejected: 4% of careers shouldn't break the screen. |
| 4 | **Drop `related_experience_tier` from lane bucketing entirely.** | 86.7% of rows are in `early` + `entry` (8121 + 5701 / 15944). `mid` is 7.6%, `senior` is 0.2%. As an organizing axis it's a near-binary distribution masquerading as 4 buckets — not useful. Surface it instead as a small chip badge only when `mid` or `senior` (the interesting outliers). | (a) Use experience tier as a sub-axis within lanes — rejected: thin distribution. (b) Use `related_experience_years` as a continuous color gradient on chips — rejected: 6-month resolution on a chip is illegible at ~120px width. |
| 5 | **Within-lane sort: `relatedness_tier` ASC (Primary-Short=0, Primary-Long=1, Supplemental=2), then `relatedness DESC` as tiebreaker.** | The student's most-similar paths surface first within each lane. `relatedness_tier` is 100% populated; `relatedness` is the float backing tiebreak. | (a) Sort by `delta_ern` desc — rejected: makes earnings the dominant axis, fights the "education effort" lane framing. (b) Sort by `to_title` alphabetically — rejected: gives no information value. |
| 6 | **Cap each lane at 6 chips with `"+N more"` inline-expand overflow.** | For SOC 11-9199 (Jeff's test build) Lateral has ~21, Step Up ~10, Long Climb ~3. Without a cap the long lane wraps onto multiple rows and breaks the "6 chips fit in viewport" promise. Inline-expand keeps the user on the same screen — no navigation, no scope change, no chat-history clear. | (a) Hard cap, no overflow affordance — rejected: silently drops 60%+ of one lane's chips. (b) Cap at 4 — rejected: too aggressive given typical Lateral lane size of 10-25. (c) Cap at 8 — rejected: the row would already be near-overflowing the col-span-5 column at desktop. |
| 7 | **`"Hide supplemental"` toggle filters `relatedness_tier == "Supplemental"` (49.4% of all rows).** Default off. Per-session state, reset on screen mount. | Supplemental tier is half the dataset; for some careers it's the dominant tier and crowds out Primary-Short/Long. Optional filter lets power users de-noise without imposing a default that hides data. | (a) Hide Supplemental by default — rejected: defaults that hide data feel patronizing; some careers have very few non-Supplemental destinations. (b) Three-state segmented control (Show all / Primary only / Hide all) — rejected: complexity not earned by the use case. |
| 8 | **Drop `treeFlowLayout.ts::deriveBranchLabel`** (the regex that produced "Specialize"/"Go Management"/"Pivot Lateral"/"Stay Technical"). | These were the L1 category labels in the dendrogram. With lanes replacing the dendrogram structure, the regex labels have no host. The lane labels carry the meaning now. | Keep the function for some future use — rejected: dead code rots; if a future spec needs it, it can be re-introduced. |
| 9 | **Drop L2/L3 nodes entirely (the dendrogram's depth-2/3 destinations).** | The current tree shows 3 levels of cascade (root → branchLabel → career → endpoint). The horizon map flattens everything to 1 level: branches off the root. The user navigates deeper *through Gemma*, not by clicking L2 to expand to L3. | (a) Keep L2/L3 as drill-down on chip click — rejected: re-introduces the wayfinding metaphor we just rejected. (b) Add a "show details" affordance per chip that reveals child destinations inline — rejected: the chat panel is the descent mechanism now. |
| 10 | **Bidirectional flash binding preserved unchanged.** `BranchHighlightDriver` already keys on `(id, title)` pairs; the `id` schema changes from React Flow node ids (`career-${soc}-${idx}`) to chip ids (`chip-${to_soc}`), but the matching mechanism is identical. The `branch-flash` CSS keyframe applies to chip elements via the same className contract. | Keeps `feature-tree-as-map.md`'s bidirectional contract intact. The driver doesn't care what kind of element flashes as long as the className → keyframe link is preserved. | Re-architect highlighting to use structured tool output from Gemma — rejected: explicitly out of scope per `feature-tree-as-map.md` Decision #4. |
| 11 | **`@fp-data-reviewer` SKIPPED.** This spec adds new READ paths over existing `CareerBranch` Pydantic fields. No gold-zone schema, no formula, no crosswalk, no boss-formula changes. Same skip basis as `feature-tree-as-map.md` Decision #8. | Invoking @fp-data-reviewer "to be safe" — rejected; the gate is for pipeline + formula changes, not new readers. |
| 12 | **`@genai-architect` SKIPPED.** Voice contract unchanged; no Gemma prompts touched; opener path unchanged; no new tools or context-builder edits. The horizon map is a presentational layer between the tree response and the user — Gemma's surface is identical. | Invoking @genai-architect "to be safe" — rejected; the gate is for prompt/schema/tool changes, not presentational layers. |

### Constraints
- **Voice contract is a hard gate (inherited).** All voice rules from `feature-chat-guardrails.md` and the `_BRANCH_VOICE_APPENDIX` from `feature-tree-as-map.md` apply. The horizon map adds no Gemma surface — voice tests must remain all-green as a sentinel.
- **Backwards compat with `feature-tree-as-map.md`.** The screen-level grid (tree col-span-5 + chat col-span-7), the embedded `GemmaChat` variant, the 300ms node-click debounce, the `sessionRef` stale-drop pattern, and the `BranchHighlightDriver` lookaround regex matcher all continue to work unchanged. Tests in `BranchTreeScreen.test.tsx` for those behaviors must remain green.
- **Brightpath tokens only.** No hardcoded colors / spacing / typography in any new component. Reuse `bp-mid` / `bp-surface` / `bp-raised` / `border-subtle` / `accent-info` / `accent-thrive` / `accent-insight` / text-tier tokens.
- **Frontend-only.** No backend file changes. No Pydantic edits. No Iceberg edits. No DuckDB edits. No new MCP tools. The data anchor is `Build.career.education_level_name` (already on `CareerOutcome`) and the candidate set is `Build.branches[*]` plus the existing `getTree()` response.
- **The `branchFlash` motion preset stays in `motion.ts`.** The CSS keyframe `branchFlashPulse` stays in the styles file (moves from `reactflow-dark.css` to a new horizon-map-specific stylesheet, but the keyframe itself is unchanged).

### Out of Scope
- **Auto-pan-to-flash.** When Gemma names a branch off-screen on the dendrogram, the user has to find it. The horizon map *resolves this by architecture* — every chip is in viewport because each lane caps at 6 — so no pan-to-flash mechanism is needed. Flag as "resolved-by-architecture" not "future feature."
- **Tree depth restoration (L2/L3 navigation).** The horizon map flattens to L1. If the team wants L2/L3 navigation back, that's a separate spec. Likely premise: the chat panel is the descent mechanism, but advanced/data-curious users may want a click-to-drill-down affordance. Future spec name: `feature-horizon-drill-down.md` (TBD).
- **Re-bucketing for advanced students.** A build with `education_level_name == "Master's degree"` will see most things in Lateral or Step Up (Long Climb only fires for `doctoral`). Acceptable for v1; if demo dry-run shows pathological skew, future spec: `feature-horizon-rebalance.md` (TBD).
- **Mobile horizon-map redesign.** Mobile inherits `feature-tree-as-map.md`'s collapsible "Show map" drawer pattern unchanged. The horizon map renders inside the drawer body when expanded. No new mobile pattern.
- **Streaming chat opener (still deferred from `feature-tree-as-map.md`).** SSE-based streaming of opener generation is still a future spec.
- **Persistent chat history per branch across sessions.** Still ephemeral by design; clears on scope change AND on screen unmount.
- **L1 destination wage rendering on chips.** `CareerBranch` does not carry destination wage. If a chip needs wage, `get_occupation_data(soc=branch.to_soc)` is the chat-time tool path; the chip's stat-delta badge is the at-a-glance proxy.

---

## §3 UI/UX Design

> **@fp-design-visionary owns this section.** Fill BEFORE implementation begins. The chat column ships today as `feature-tree-as-map.md` §3 — **do not redesign it.** Only the tree column's body (replacing `BranchTreeFlow` with the new horizon-map component) and any new lane / chip / filter chrome are in scope.

### Reference mockup

`@fp-design-visionary` produced a standalone HTML mockup on 2026-04-29 covering all 9 required states (default, chip selected, branch flashing, "+N more" pre/post-expand, "Hide supplemental" on, empty Long Climb lane, mobile drawer expanded, mobile drawer collapsed). The mockup answers the 10 open questions below and adds 5 design calls beyond the spec text. **It is the binding visual target for implementation** — the implementer should match it pixel-for-pixel where it conflicts with the prose below.

- **Path:** `docs/mockups/feature-tree-horizon-map.html`
- **How to view:** `open docs/mockups/feature-tree-horizon-map.html`
- **Approved by Jeff:** 2026-04-29 ("beautiful")

Visionary's calls beyond the spec text (preserved here so the audit + code-review agents have them in scope):
1. **Selection dim is lane-local.** Only siblings *within the selected chip's own lane* dim. Other lanes stay full opacity. Rationale: the dendrogram's dim-everything pattern was load-bearing for orientation in a forest of nodes; on a 3-lane grid it's overkill.
2. **Lane left-edge accent bar** — each lane has a 3px gradient bar (`accent-thrive` / `accent-info` / `accent-insight` per Lateral / Step Up / Long Climb) so the three lanes are visually distinct on peripheral scan.
3. **Empty-lane copy is explanatory, not generic.** Instead of "no paths," the empty-state copy explains *why* in plain English ("from a Master's, the climb is one more credential — those are in Step Up"). Reads as data, not bug.
4. **Anchor sub-line** — the horizon-map header carries a `Bachelor's-anchored` / `Master's-anchored` data tag so the personalization (D#1 lane logic) is visible chrome, not implicit.
5. **Flash-mid border swap** — chip border picks up `accent-info` during the pulse, in addition to the box-shadow glow. Reads better at chip scale than glow alone.

### Open questions for @fp-design-visionary

> All 10 questions are **answered by the HTML mockup above**. Preserved here so implementers can quickly see *what was asked* alongside *what was answered*. If you find a question whose mockup answer is unclear, escalate via §10 Discussion.

1. **Lane-row vertical stacking** — three lane rows stacked vertically inside `col-span-5`, or three lane *columns* inside the tree column? The product brief says "horizontal lanes" which implies lane-row stacking; confirm the per-lane horizontal axis is the chip row (left to right), not a per-lane vertical axis.
2. **Chip dimensions** — the col-span-5 column is ~480-500px wide on desktop. With 6 chips per lane and gap, each chip has ~70-75px of horizontal real estate. Is that a *card* (vertical layout: title on top, badges below) or a *pill* (horizontal layout: title left, badge right)? Either way it must hold a 32-char-truncated `to_title`, a stat-delta badge, an optional unlock footer, and an optional experience badge.
3. **Lane header chrome** — label ("Lateral") + subtitle ("same degree, different role") + lane chip count ("6 of 21 shown") + "Hide supplemental" toggle (column-level, not per-lane). Where does the toggle live — top-right of the column header above all lanes, or repeated per-lane?
4. **`"+N more"` expand affordance** — a chip-shaped placeholder at the end of the row, or a lane-level link? When expanded, does it scroll, paginate, or grow the lane row vertically?
5. **Empty-lane treatment** — `text-text-muted` placeholder is specified in the brief; confirm typography (`font-body text-small`?) and any visual indicator that the lane is empty by data, not by filter.
6. **Relatedness color-bar on chip left edge** — exact widths and colors. Brief says: green for Primary-Short, blue for Primary-Long, gray for Supplemental. Map to `accent-thrive` / `accent-info` / `text-muted`? Confirm token mapping and bar width (3-4px?).
7. **Stat-delta badge styling** — colored corner badge with sign and stat code (e.g. `+12 ERN`). The voice contract bans stat codes in *Gemma's prose*, not in *UI affordances* — but it's worth confirming: per-screen rendering of `ERN`/`ROI`/`RES`/`GRW`/`HMN` as labels has been allowed elsewhere (pentagon overlay, `StatInfoPopover`). Confirm the convention holds here.
8. **Experience badge ("mid-career" / "senior")** — small pill in chip's bottom-right when `related_experience_tier in {"mid", "senior"}`. Color, size, weight?
9. **Selected chip treatment** — when a chip is the current `selectedNodeId`, does it dim siblings (existing dendrogram pattern), or only highlight itself? The dim treatment is load-bearing on the dendrogram for orientation; on a 3-lane grid it may be overkill.
10. **Branch-flash visual** — the `branchFlash` keyframe applies the same scale + glow to chip elements. Confirm the keyframe values (1 → 1.06 → 1, accent-info glow) read well at chip scale; if not, spec a chip-specific variant.

### Mockups
**Required states to mock** (fill in §3 with ASCII mockups or detailed descriptions per `_TEMPLATE.md` §3 conventions):
- default (all 3 lanes painted, "Hide supplemental" off, chat side fully populated from `feature-tree-as-map.md` reference)
- chip selected (one chip is the current chat scope, others dimmed/un-dimmed per visionary's pick)
- branch flashing (Gemma named a branch in chat, matching chip mid-pulse)
- "+N more" pre-expand (lane has overflow indicator)
- "+N more" post-expand (lane has all chips visible inline)
- "Hide supplemental" on (Supplemental-tier chips removed across all lanes; "+N more" counts updated)
- empty Long Climb lane (Master's-level build with no doctoral destinations)
- mobile (drawer expanded with horizon map inside)
- mobile (drawer collapsed, chat occupies full viewport)

### Interactions
- **First load:** tree fetch fires (existing); on tree-fetch success, lane assignment runs over `treeData.tree.children` (the L1 branches), chips render, chat opener fires per `feature-tree-as-map.md` §4 unchanged.
- **Click a chip:** identical contract to `feature-tree-as-map.md`'s tree-click. `selectedNodeId` updates to the chip's id, `chatScope.target_id` updates to the chip's `to_soc`, chat history clears, opener re-fires for that branch (300ms debounce + `sessionRef` bump apply).
- **Click "+N more":** expand lane inline. State is per-lane and ephemeral (resets on screen unmount). Does NOT change scope, chat, or selection.
- **Click "Hide supplemental" toggle:** toggle filter state. Re-renders all 3 lanes with Supplemental chips removed. Lane caps recompute.
- **Gemma response received:** `BranchHighlightDriver` parses for branch title matches against the chip set's `(id, title)` pairs (case-insensitive, longest-match-wins, dedup, stagger — all per `feature-tree-as-map.md`'s implementation). For each match, fire a highlight event with TTL ~700ms. The `branch-flash` className applies to the matching chip element.

### Responsive Behavior
Per @fp-design-visionary's pick. Desktop (≥768px) is primary. Mobile inherits `feature-tree-as-map.md`'s collapsible "Show map" drawer pattern unchanged — the horizon map renders inside the drawer body when expanded.

### Brightpath Design References
- **Backgrounds:** `bp-mid` (lane container), `bp-surface` (chip default bg), `bp-raised` (chip hover, "+N more" affordance), `bp-deep` (page bg, inherited from `PageContainer`).
- **Borders:** `border-subtle` for chip outlines, lane separators, filter toggle.
- **Accents:**
  - `accent-info` — branch flash glow (existing `branchFlash` preset), focus rings.
  - `accent-thrive` — Primary-Short relatedness color bar, selected-chip ring.
  - `accent-insight` — chat send button (inherited, unchanged).
  - `text-muted` — Supplemental relatedness color bar, empty-lane placeholder.
- **Typography:** `font-display` (Fredoka, semibold, lane label headers), `font-body` (Nunito, chip titles, lane subtitles, filter toggle), `text-data` (Space Mono, stat-delta badges if numeric — visionary's call).
- **Motion:**
  - `branchFlash` — chip flash pulse, **unchanged** from `feature-tree-as-map.md`.
  - `branchFlashStagger = 0.2` — multi-match stagger, **unchanged**.
  - `chipResponseExpand` — `"+N more"` expand affordance (reuses preset already in `motion.ts`).
  - `springs.snappy` — chip whileTap, filter toggle.
  - `transitions.fadeInUp` — lane initial reveal on first paint.

### Frontend libraries
| Library | Use |
|---------|-----|
| **Framer Motion** | Chip whileTap, lane reveal, expand affordance, branch flash entrance. |
| **shadcn/ui** | "Hide supplemental" toggle (matches existing toggle/checkbox primitive). |
| **React Flow** | **REMOVED** from `/branch-tree`'s tree column. The horizon map does not need a graph layout library. (React Flow stays in the codebase — it's used by other screens — but is not imported by the new horizon-map component.) |

### Accessibility
| Element | Identifier (data-testid) | Type | aria-label |
|---|---|---|---|
| Horizon map column container | `region-branch-horizon` | region | `Career path map by education effort` |
| Lane header (×3) | `lane-header-{lateral\|step-up\|long-climb}` | (heading h3) | (lane label, e.g. `Lateral career paths`) |
| Lane chip (×N per lane) | `chip-branch-{to_soc}` | button | `{branch.to_title}, {lane subtitle}` |
| "+N more" affordance | `btn-lane-expand-{lateral\|step-up\|long-climb}` | button | `Show {N} more {lane subtitle} paths` |
| "Hide supplemental" toggle | `toggle-hide-supplemental` | switch (aria-checked) | `Hide secondary career paths` |
| Empty-lane placeholder | `lane-empty-{lateral\|step-up\|long-climb}` | (status) | `No {lane subtitle} paths in this data` |

---

## §4 Technical Specification

### Architecture Overview
This spec is a **frontend-only presentation-layer swap** on `/branch-tree`. The screen-level grid (tree col-span-5 + chat col-span-7), the embedded `GemmaChat` variant, the bidirectional flash binding, the chat scope wiring, and every backend surface (`POST /chat/ask`, `_context_for_branch`, MCP tool allowlist, voice contract appendix) are all unchanged from `feature-tree-as-map.md`. Only the tree column's body changes: `BranchTreeFlow` (a React Flow dendrogram) is replaced with `BranchHorizonMap` (a 3-lane chip grid). The lane bucketing is a pure function over existing `CareerBranch` fields anchored on `Build.career.education_level_name`; no backend, schema, or pipeline changes.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonMap.tsx` | Create | New component. Props: `{ tree: TreeResponse, build: Build, selectedNodeId: string \| null, onSelectNode: (id: string \| null) => void, highlightedNodeIds: ReadonlySet<string> }`. Computes lane assignments via `assignLane(branch.related_education_level, build.career.education_level_name)`, sorts within lanes by `relatedness_tier` ASC then `relatedness DESC`, caps at 6 chips with "+N more" overflow, applies "Hide supplemental" filter from local state, renders 3 stacked lane rows inside a `bp-mid` container. Each chip's id is `chip-${branch.to_soc}` for `BranchHighlightDriver` candidate matching. Handles click → `onSelectNode(chipId)`. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonChip.tsx` | Create | New component. Props: `{ branch: CareerBranch, branchIdx: number, selected: boolean, dimmed: boolean, flashing: boolean, onClick: () => void }`. Renders chip body: `to_title` (truncated 32 chars), dominant stat-delta badge (largest abs of `delta_ern`/`delta_grw`/`delta_hmn`/`delta_res`, signed), `unlock` footer when present, experience badge when `related_experience_tier in {"mid", "senior"}`, relatedness color bar on left edge. `flashing && "branch-flash"` className applies. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/data/horizonLayout.ts` | Create | New module. Exports `assignLane(branch_edu, build_edu)`, `eduRank(level)`, `sortBranchesInLane(branches)`, `bucketBranches(treeBranches, buildEdu, hideSupplemental)`. Pure functions — no React, no DOM, no API. Full type signatures (no `any`). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchTreeFlow.tsx` | Delete | No longer used. The component shipped with `feature-tree-as-map.md`'s compact mode. Archive note: deleted in this spec; recoverable via git. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/data/treeFlowLayout.ts` | Modify | Delete `deriveBranchLabel` (lines ~83-100). Keep the rest of `treeToFlow` — it's still used by other consumers (the branch-results comparison view may reference it; verify during implementation). If no other consumers, delete the entire file. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/BranchTreeScreen.tsx` | Modify | Replace the two `<BranchTreeFlow>` renders (desktop + mobile drawer) with `<BranchHorizonMap>`. Drop the `--branch-flow-node-scale` CSS variable from both wrappers (no longer needed — no React Flow). Drop the React Flow `compact` prop, `heightClassName` prop, and the React Flow-specific imports. The `selectedNodeId`, `chatScope`, `flowNodeMap`, `highlightCandidates`, debounce, sessionRef, `BranchHighlightDriver` mount, and chat wiring all stay unchanged. Adapt `highlightCandidates` to use the new chip id schema (`chip-${branch.to_soc}`) — see §4 BranchHighlightDriver candidate schema below. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/styles/horizonMap.css` | Create | New stylesheet. Contains the relocated `branchFlashPulse` keyframe + `.horizon-chip.branch-flash` rule (moves from `reactflow-dark.css` since the dendrogram is gone). Also contains lane / chip / overflow / filter / empty-state styling. Reduced-motion fallback preserved (80ms opacity blink, no scale, no glow). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/styles/reactflow-dark.css` | Modify | Remove the `--branch-flow-node-scale` variable + the `[data-compact="true"] .react-flow__node` rule + the `branchFlashPulse` keyframe + the `.react-flow__node.branch-flash` rule + the reduced-motion fallback. The keyframe and class move to `horizonMap.css`. The CSS variable is no longer used. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/i18n/strings.ts` | Modify | Add lane labels + subtitles + filter toggle + empty states + experience badge labels (EN + ES). Remove the now-unused `tree.starterRoot.*` and `tree.starterBranch.*` keys IF the chip starters are absorbed into the horizon map; otherwise leave them (they're inherited by the chat side from `feature-tree-as-map.md`). New keys: `tree.lane.lateral`, `tree.lane.lateral.subtitle`, `tree.lane.stepUp`, `tree.lane.stepUp.subtitle`, `tree.lane.longClimb`, `tree.lane.longClimb.subtitle`, `tree.filter.hideSupplemental`, `tree.lane.empty.lateral`, `tree.lane.empty.stepUp`, `tree.lane.empty.longClimb`, `tree.expand.more` (param `{count}`), `tree.expand.collapse`, `tree.chip.experience.mid`, `tree.chip.experience.senior`, `tree.chip.levelUnknown`. |
| `/Users/jcernauske/code/bright/futureproof-data/DESIGN.md` | Modify | Update the "Tree-as-map node scale" entry under §Motion System: replace with a "Horizon Map" entry referencing the new lane / chip / cap-at-6 pattern. The `branchFlash` preset documentation stays unchanged (it just applies to chip elements now instead of React Flow nodes). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonMap.test.tsx` | Create | New test file. See §4 New Tests Required. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonChip.test.tsx` | Create | New test file. See §4 New Tests Required. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/data/horizonLayout.test.ts` | Create | New test file. Pure-function tests for `assignLane`, `eduRank`, `sortBranchesInLane`, `bucketBranches`. See §4 New Tests Required. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/BranchTreeScreen.test.tsx` | Modify | Re-baseline the structural assertions broken by the tree-column body swap (the wrapping grid + chat-column tests stay unchanged — those are inherited from `feature-tree-as-map.md` and are confirmed-safe sentinels). Update mocks: replace `BranchTreeFlow` mock with `BranchHorizonMap` mock. Update flash-test assertions to check chip className instead of React Flow node className. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHighlightDriver.test.tsx` | (no change) | The driver itself is unchanged. The candidate id schema changes from `career-${soc}-${idx}` to `chip-${to_soc}` — but the driver is id-agnostic (it returns whatever ids the parent passes). Existing tests pass without modification. |

### Reuse-don't-rebuild list (binding for all agents)

- **`POST /chat/ask`, `AskRequest` / `AskResponse`, `askGemma()` client, `GemmaChat.scope` prop wiring, embedded variant, sessionRef bump, opener-prompt path** — ALL provided by `feature-ask-gemma.md` + `feature-tree-as-map.md`. Do NOT re-implement.
- **`_context_for_branch`, `_BRANCH_VOICE_APPENDIX`, `_OPENER_PROMPT`, `_OPENER_PROMPT_BRANCH`, voice contract** — ALL backend; NOT touched by this spec.
- **`BranchHighlightDriver`** — id-agnostic; only the candidate set's id schema changes (computed in `BranchTreeScreen`). The driver code is not touched.
- **`branchFlash` motion preset + `branchFlashStagger` constant** in `frontend/src/styles/motion.ts` — unchanged. The chip flash applies the same keyframe as the React Flow node flash did.
- **300ms node-click debounce + `chatScope` `useMemo` on primitive deps** in `BranchTreeScreen.tsx` — unchanged. Chip clicks flow through the same debounce.
- **Mobile "Show map" drawer pattern + collapsible state** from `feature-tree-as-map.md` §3 — unchanged. The horizon map slots into the drawer body.
- **`getTree` API + `TreeResponse` types** — unchanged. The horizon map reads `treeData.tree.children` (the L1 branches) plus `build.career.education_level_name` (already on the build store).
- **`AskGemmaChipRow` (the starter-question chips below the chat opener)** — unchanged. Starter chips live in the chat column; the horizon-map lanes are separate.

### Data Model Changes

**None.** No new Pydantic models. No Iceberg edits. No DuckDB edits. No MCP tool changes. The horizon map is a frontend derivation over existing `CareerBranch` fields.

### Service Changes

**None.** No new modules in `backend/app/`. No new public function signatures. No dependency changes. The lane assignment logic lives entirely in `frontend/src/data/horizonLayout.ts` as pure TypeScript.

#### Frontend module: `frontend/src/data/horizonLayout.ts`

```typescript
import type { CareerBranch } from "@/types/build";

export type LaneId = "lateral" | "stepUp" | "longClimb";

export interface BucketedLane {
  id: LaneId;
  branches: CareerBranch[];
  totalBeforeCap: number;  // for "+N more" math; respects hideSupplemental filter
}

export interface BucketedLanes {
  lateral: BucketedLane;
  stepUp: BucketedLane;
  longClimb: BucketedLane;
}

const EDU_RANK: Record<string, number> = {
  "High school diploma or equivalent": 0,
  "No formal educational credential": 1,
  "Postsecondary nondegree award": 1,
  "Some college, no degree": 1,
  "Associate's degree": 2,
  "Bachelor's degree": 3,
  "Master's degree": 4,
  "Doctoral or professional degree": 5,
};

const RELATEDNESS_TIER_ORDER: Record<string, number> = {
  "Primary-Short": 0,
  "Primary-Long": 1,
  "Supplemental": 2,
};

const LANE_CAP = 6;
const BUILD_EDU_FALLBACK_RANK = 3;  // bachelor's-equivalent

export function eduRank(educationLevelName: string | null | undefined): number | null {
  if (educationLevelName == null) return null;
  return EDU_RANK[educationLevelName] ?? null;
}

export function assignLane(
  branchEdu: string | null | undefined,
  buildEdu: string | null | undefined,
): LaneId {
  if (branchEdu == null) return "lateral";  // null → Lateral with muted treatment
  const buildRank = eduRank(buildEdu) ?? BUILD_EDU_FALLBACK_RANK;
  const branchRank = eduRank(branchEdu) ?? BUILD_EDU_FALLBACK_RANK;
  const delta = branchRank - buildRank;
  if (delta <= 0) return "lateral";
  if (delta === 1) return "stepUp";
  return "longClimb";
}

export function sortBranchesInLane(branches: CareerBranch[]): CareerBranch[] {
  return [...branches].sort((a, b) => {
    const ta = RELATEDNESS_TIER_ORDER[a.relatedness_tier ?? "Supplemental"] ?? 2;
    const tb = RELATEDNESS_TIER_ORDER[b.relatedness_tier ?? "Supplemental"] ?? 2;
    if (ta !== tb) return ta - tb;
    const ra = a.relatedness ?? -Infinity;
    const rb = b.relatedness ?? -Infinity;
    return rb - ra;  // DESC
  });
}

export function bucketBranches(
  branches: CareerBranch[],
  buildEdu: string | null | undefined,
  hideSupplemental: boolean,
  options: { laneCap?: number } = {},
): BucketedLanes {
  const cap = options.laneCap ?? LANE_CAP;
  const filtered = hideSupplemental
    ? branches.filter((b) => b.relatedness_tier !== "Supplemental")
    : branches;
  const byLane: Record<LaneId, CareerBranch[]> = {
    lateral: [],
    stepUp: [],
    longClimb: [],
  };
  for (const branch of filtered) {
    byLane[assignLane(branch.related_education_level, buildEdu)].push(branch);
  }
  const out: BucketedLanes = {
    lateral: { id: "lateral", branches: [], totalBeforeCap: 0 },
    stepUp: { id: "stepUp", branches: [], totalBeforeCap: 0 },
    longClimb: { id: "longClimb", branches: [], totalBeforeCap: 0 },
  };
  for (const laneId of ["lateral", "stepUp", "longClimb"] as const) {
    const sorted = sortBranchesInLane(byLane[laneId]);
    out[laneId] = {
      id: laneId,
      branches: sorted.slice(0, cap),
      totalBeforeCap: sorted.length,
    };
  }
  return out;
}
```

#### `BranchHighlightDriver` candidate schema change

In `BranchTreeScreen.tsx`'s `highlightCandidates` `useMemo`, the id schema changes from React Flow node ids (`career-${soc}-${idx}`, `branch-${idx}`, `endpoint-${soc}-${idx}-${epIdx}`) to a single uniform schema: `chip-${branch.to_soc}`. The candidate set is built directly from `treeData.tree.children` (the L1 `CareerBranch` records) — one entry per branch. L2/L3 candidates are dropped (they have no chips). The matcher logic is unchanged.

#### `useBuildStore` access for `Build.career.education_level_name`

The build store already exposes the full `Build` object (per the existing `useBuildStore((s) => s.build)` pattern in `BranchTreeScreen.tsx`). `build.career.education_level_name` is read directly — no new selector, no new store action.

### Testing Impact Analysis

> Search performed against: `frontend/src/screens/BranchTreeScreen.test.tsx`, `frontend/src/components/tree/*.test.tsx`, `frontend/src/components/menu/GemmaChat.test.tsx`, `frontend/src/components/menu/CompareView.test.tsx`, `frontend/src/components/menu/MenuScreen.test.tsx`, `backend/tests/services/test_ask_gemma.py`, `backend/tests/services/test_ask_gemma_voice.py`, `backend/tests/routers/test_ask_gemma_router.py`, `backend/tests/services/test_gemma_voice_contract.py`.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|---|---|---|---|
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_branch_name_in_response_flashes_node` | High | Asserts on the className of a React Flow node. After this spec, the className applies to a chip element. Re-baseline to query `[data-testid^="chip-branch-"]` instead of the React Flow node selector. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_node_click_updates_scope_and_clears_history` | Med | The mock `BranchTreeFlow` exposes a DOM button that fires `onSelectNode`. Replace with a mock `BranchHorizonMap` that exposes the same contract via a chip-shaped DOM button. The test contract (clicking → scope update → history clear) is unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_node_click_debounce_300ms` | Med | Same — re-mock `BranchHorizonMap` with the same `onSelectNode` contract. Debounce logic is in the screen, not the tree. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_first_load_fires_chat_ask_with_root_branch_scope` | Low | Tree mount triggers chat-ask. Behavior unchanged (the chat-column wiring is not touched). |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_parent_rerender_without_selection_change_does_not_refire` | Low | Memo / primitive-deps wiring unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_stale_opener_dropped_on_rapid_branch_switch` | Low | sessionRef wiring unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_fallback_career_renders_chat_at_root` | Low | Fallback path renders `TreeFallback`, not the horizon map. Unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_gemma_unavailable_renders_fallback_string` | Low | Chat-side test; tree-side unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | (col-span-5 / col-span-7 grid assertions) | Low | Grid is unchanged. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | (entire suite) | Low | GemmaChat is not modified by this spec. |
| `frontend/src/components/tree/BranchHighlightDriver.test.tsx` | (entire suite) | Low | Driver is id-agnostic; existing tests use synthetic id shapes that match either old or new schemas. |
| `backend/tests/services/test_ask_gemma.py` | (entire suite) | Low | Backend unchanged. |
| `backend/tests/services/test_ask_gemma_voice.py` | (entire suite) | Low | Backend unchanged. |
| `backend/tests/routers/test_ask_gemma_router.py` | (entire suite) | Low | Backend unchanged. |
| `backend/tests/services/test_gemma_voice_contract.py` | (entire suite) | Low | Backend unchanged. Voice contract sentinel must hold. |
| `frontend/src/components/menu/CompareView.test.tsx` | (entire suite) | Low | Compare scope unaffected. Pre-existing failures from `feature-tree-as-map.md` §7 still pre-existing. |
| `frontend/src/components/menu/MenuScreen.test.tsx` | (entire suite) | Low | Legacy slide-in path unchanged. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|---|---|---|
| `frontend/src/screens/BranchTreeScreen.test.tsx::test_branch_name_in_response_flashes_node` | Re-baseline assertion target from React Flow node className to chip element className (`[data-testid^="chip-branch-"]` selector). | The element being flashed changed; the contract did not. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` (mock for `BranchTreeFlow`) | Replace mock with `BranchHorizonMap` exposing the same `onSelectNode` contract via a chip-shaped DOM button. | The screen consumes a different component now; the tested contract is unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` (any structural assertion on tree-column DOM) | Re-baseline to the new horizon-map DOM (lanes, chips, "+N more"). | Tree-column body is replaced; the tested behavior of the screen-level grid is unchanged. |
| `frontend/src/screens/BranchTreeScreen.test.tsx::highlightCandidates` derivation | Update the `highlightCandidates` `useMemo` to produce `chip-${branch.to_soc}` ids (matches the new chip id schema). The test that asserts `BranchHighlightDriver` receives a non-empty candidate set and the flash test will need their fixture ids updated accordingly. | Id schema change. Mechanical re-baseline. |

#### Confirmed Safe (must NOT break — STOP and escalate if they do)

- **All `backend/tests/services/test_gemma_voice_contract.py` tests** — voice contract is untouched.
- **All `backend/tests/services/test_ask_gemma.py` tests** (all 6 scope kinds: stat/boss/skill/build/compare/branch) — backend unchanged.
- **All `backend/tests/services/test_ask_gemma_voice.py` tests** (existing 18-prompt battery + 7 branch jailbreaks + verb-label quoting) — backend unchanged.
- **All `backend/tests/routers/test_ask_gemma_router.py` tests** (all 6 scope kinds) — backend unchanged.
- **All `backend/tests/services/test_boss_fights.py` tests** — no boss-formula changes.
- **All `backend/tests/services/test_builds.py` tests** — no build-construction changes.
- **All `backend/tests/routers/test_builds.py` tests** — `POST /{build_id}/chat` and `POST /build/...` endpoints untouched.
- **All `frontend/src/components/menu/MenuScreen.test.tsx` tests** — legacy slide-in path unchanged.
- **All `frontend/src/components/menu/GemmaChat.test.tsx` tests** — GemmaChat component unchanged.
- **All `frontend/src/components/menu/CompareView.test.tsx` tests** (modulo the 9 pre-existing failures from `feature-tree-as-map.md` §7's verification) — compare scope unaffected.
- **All `frontend/src/components/tree/BranchHighlightDriver.test.tsx` tests** — driver is id-agnostic; existing tests should pass without modification.
- **All `frontend/src/screens/BuildResultsScreen.test.tsx` tests and per-element entry-point tests from `feature-ask-gemma.md`** — untouched by this spec.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|---|---|---|---|
| P0 | `frontend/src/data/horizonLayout.test.ts` | `eduRank returns correct ranks for all 8 known education levels` | `eduRank("High school diploma or equivalent")` → 0; `eduRank("Bachelor's degree")` → 3; `eduRank("Doctoral or professional degree")` → 5; `eduRank(null)` → null; `eduRank("Some college, no degree")` → 1 (same rank as no-credential and postsecondary nondegree). |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `assignLane bucket boundaries: same edu → Lateral` | Build edu = Bachelor's, branch edu = Bachelor's → `"lateral"`. |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `assignLane bucket boundaries: +1 step → Step Up` | Build edu = Bachelor's, branch edu = Master's → `"stepUp"`. |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `assignLane bucket boundaries: +2 steps → Long Climb` | Build edu = Bachelor's, branch edu = Doctoral → `"longClimb"`. |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `assignLane bucket boundaries: branch null → Lateral` | Build edu = Bachelor's, branch edu = null → `"lateral"`. |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `assignLane bucket boundaries: build null → bachelor's-equivalent fallback` | Build edu = null, branch edu = Master's → `"stepUp"` (3 → 4 = +1). |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `assignLane bucket boundaries: lower edu branch → Lateral` | Build edu = Master's, branch edu = Bachelor's → `"lateral"` (delta = -1, ≤ 0). |
| P1 | `frontend/src/data/horizonLayout.test.ts` | `sortBranchesInLane respects relatedness_tier order then relatedness DESC` | Mixed-tier input; verify Primary-Short → Primary-Long → Supplemental, with relatedness DESC tiebreak. |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `bucketBranches caps lanes at 6 and reports totalBeforeCap` | Input 21 branches all bucketing to Lateral; output `lateral.branches.length === 6` and `lateral.totalBeforeCap === 21`. |
| P0 | `frontend/src/data/horizonLayout.test.ts` | `bucketBranches with hideSupplemental excludes supplemental tier from all lanes` | Input mix; verify Supplemental rows absent from `branches` arrays AND `totalBeforeCap` reflects the post-filter count. |
| P1 | `frontend/src/data/horizonLayout.test.ts` | `bucketBranches preserves stable sort within identical relatedness/tier` | Two branches with identical tier + relatedness; verify input order is preserved (sort is stable). |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `renders 3 lane headers (Lateral / Step Up / Long Climb)` | Mount with non-empty branches; verify all 3 lane headers present with `data-testid="lane-header-{lateral\|step-up\|long-climb}"`. |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `renders one chip per branch up to lane cap of 6` | Input 10 branches all bucketing to Lateral; verify 6 chips render with `data-testid="chip-branch-{to_soc}"`, plus a "+4 more" affordance with `data-testid="btn-lane-expand-lateral"`. |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `clicking +N more expands lane inline` | Click the expand affordance; verify all 10 chips now render and the affordance is replaced with a "Show fewer" or hidden state. |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `Hide supplemental toggle filters across all lanes` | Mount with 50% Supplemental rows distributed across lanes; toggle on; verify Supplemental chips removed and "+N more" counts update. |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `clicking a chip fires onSelectNode with chip-${to_soc}` | Click a chip; verify `onSelectNode("chip-{to_soc}")` called. |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `flashing chip applies branch-flash className` | Pass `highlightedNodeIds = new Set(["chip-13-1075"])`; verify the chip with that id has the `branch-flash` class. |
| P0 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `empty Long Climb lane renders empty-state placeholder` | Mount with branches that all bucket to Lateral (Master's-level build); verify `data-testid="lane-empty-long-climb"` present with the localized empty-state copy. |
| P1 | `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `selected chip applies a selected treatment` | Pass `selectedNodeId="chip-13-1075"`; verify the chip has the `data-selected="true"` attribute or equivalent. |
| P0 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `renders to_title truncated to 32 chars with ellipsis` | Title length 50; rendered text length ≤ 33 and ends with `…`. |
| P0 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `dominant stat-delta badge picks the largest abs(delta)` | Branch with deltas {ern: 5, grw: -8, hmn: 3}; rendered badge shows `-8 GRW`. Sign and magnitude match. |
| P0 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `experience badge renders only for mid or senior tier` | Branch with `related_experience_tier: "mid"` → badge present; `early` → no badge; `null` → no badge. |
| P1 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `relatedness color bar matches relatedness_tier` | Each tier value → corresponding color class on the bar. |
| P1 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `unlock footer renders when present, hidden when null` | Verify both branches. |
| P1 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `level-unknown chip treatment when related_education_level is null` | Verify a muted indicator class or copy is applied (per visionary's pick). |
| P0 | `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_first_load_renders_horizon_map_lanes` | Re-baseline after `BranchTreeFlow` → `BranchHorizonMap` swap. Tree-fetch success → 3 lane headers visible. |
| P0 | `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_branch_name_in_response_flashes_chip` | Re-baseline of the existing flash test. Mock chat response containing a branch's exact title; assert the chip with `data-testid="chip-branch-${to_soc}"` receives the `branch-flash` className. |
| P0 | `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_chip_click_updates_scope_and_clears_history` | Re-baseline of the node-click test. Click a chip; verify `chatScope.target_id` updates to the chip's `to_soc`, history clears, opener re-fires. |

#### Test Data Requirements

- **`Build` fixture variants by `education_level_name`**: at minimum HS, Bachelor's, Master's, Doctoral. Each fixture's `branches` array should include 8-12 entries spanning all 3 lanes plus null edu.
- **`CareerBranch` fixture coverage**: at least one row per `relatedness_tier` value (Primary-Short / Primary-Long / Supplemental), at least one row per `related_experience_tier` value (early / entry / mid / senior / null), at least one row with null `related_education_level`, at least one row with `unlock` populated and one with `unlock` null.
- **Frontend mock for `useBuildStore`**: existing mock pattern from `BranchTreeScreen.test.tsx`; extend to expose the new fixture variants.
- **Frontend mock for `getTree`**: existing pattern; ensure the L1 `tree.children` matches the build's `branches` array for fidelity.
- **Frontend mock for `BranchHighlightDriver`**: existing pattern; pass synthetic `(id, title)` candidates with the new `chip-${to_soc}` id schema.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING

#### Findings
[Filled in by @fp-architect — focus areas: (1) frontend-only restructure surface (no backend / no schema); (2) the `BranchHighlightDriver` candidate-id schema change from React Flow node ids to `chip-${to_soc}` and the implication that the driver remains id-agnostic; (3) reuse-don't-rebuild list discipline (we're keeping the chat column, the embedded GemmaChat variant, the debounce, the sessionRef bump, the motion preset, and the mobile drawer pattern — verify none of these are unintentionally modified); (4) the lane-assignment pure function is in `frontend/src/data/horizonLayout.ts` with full type signatures — confirm; (5) DESIGN.md update path for the deprecated `--branch-flow-node-scale` variable and the new horizon-map documentation.]

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline / gold-zone / formula / crosswalk changes — only new frontend READ paths over existing `CareerBranch` Pydantic fields. See §2 Decision #11.)

### @genai-architect Review
**Status:** SKIPPED (voice contract unchanged; no Gemma prompts or function-calling schema touched; opener path unchanged. See §2 Decision #12.)

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|---|---|

### Deviations from Spec
[Any divergence from §3/§4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---|---|---|---|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added
| Test File | Test Name | What It Tests |
|---|---|---|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|---|---|---|---|---|
| pytest | | | | |
| vitest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** PENDING
[Brightpath token compliance check against §3 mocks: lane chrome, chip anatomy, "+N more" affordance, "Hide supplemental" toggle, empty-lane placeholder, branch-flash applied to chip elements, mobile drawer inheritance.]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — focus areas per Claude Code Prompt §6: lane-assignment correctness on the long tail of `related_education_level` values; the `education_level_name` null fallback; the "Hide supplemental" filter not breaking cap-at-6 + "+N more" math; `BranchHighlightDriver` candidate-id schema change.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|---|---|
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Frontend (@fp-builder)
| Check | Result |
|---|---|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---|---|---|---|

---

## §10 Discussion

```
[2026-04-29] Author note
This spec was triggered by Jeff's live-test feedback on feature-tree-as-map.md
(shipped 2026-04-28): the dendrogram is too dense to be a useful map. The flash
highlight from feature-tree-as-map.md silently lands off-screen because most
matched nodes are outside the viewport at the zoom level fitView produces.

Product partner @fp-product-partner evaluated 3 options (top-N-by-relatedness
single column, 3-lane horizon map, top-N filtered tree) and recommended the
3-lane horizon map. DuckDB distribution check confirmed:
  - related_education_level is 96.5% populated, 9 distinct values — viable axis
  - related_experience_tier is 86.7% concentrated in early+entry — too thin to bucket on
  - relatedness_tier is 100% populated — viable as within-lane sort
  - branches per source SOC: median 20, max 75 — cap-at-6 is load-bearing

Lane assignment anchors on edu_delta from build.career.education_level_name (not
absolute education) so the same destination role looks different to a HS-bound
student vs a Bachelor's-bound student. This is the personalization that makes
"the long road through a master's" mean something different to each user.

The bidirectional flash binding from feature-tree-as-map.md is preserved by
making the chip elements receive the branch-flash className via the same
keyframe. The BranchHighlightDriver itself is id-agnostic so its tests don't
need to change.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
