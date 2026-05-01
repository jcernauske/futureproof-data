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
- [x] `/branch-tree`'s tree column renders 3 horizontal lanes — **Lateral**, **Step Up**, **Long Climb** — each with a header (label + plain-English subtitle) and a row of branch chips.
- [x] Each chip is bucketed by `assign_lane(branch.related_education_level, build.career.education_level_name)` (see §2 Decision #1 for the binding pseudocode).
- [x] Each lane shows at most 6 chips; overflow renders a `"+N more"` affordance that expands the lane inline (no navigation, no scope change). Confirmed load-bearing: SOC 11-9199 Lateral has ~21 chips post-bucketing.
- [x] Within-lane sort: `Primary-Short` → `Primary-Long` → `Supplemental` by `relatednessTier(branch.relatedness)` (D#17), then `relatedness ASC` (most-related first, since `relatedness` is `best_index` where 1 = most related — see D#17 rationale).
- [x] A "Hide supplemental" toggle in the column header filters branches where `relatednessTier(branch.relatedness) === "Supplemental"` from all lanes when active. Default off. Persists per session, resets on screen mount.
- [x] Each chip displays: `to_title` (truncated 32 chars), dominant stat-delta badge (largest abs of `delta_ern`/`delta_grw`/`delta_hmn`/`delta_res`, signed), `unlock` (when present), experience badge (only when `branch.experience_tier in {"mid", "senior"}`), relatedness color bar on left edge driven by `relatednessTier(branch.relatedness)`.
- [x] Clicking a chip sets `selectedNodeId` to the chip's React-derived id, updates `chatScope.target_id` to the chip's `to_soc`, clears chat history, re-fires the opener — identical contract to `feature-tree-as-map.md`'s tree-click behavior. The 300ms debounce + `sessionRef` bump are inherited.
- [x] When Gemma's response names a branch verbatim (matched by `BranchHighlightDriver`), the corresponding chip flashes via the `branch-flash` className → CSS keyframe (`branchFlashPulse`, `accent-info`, 600ms). Multi-match stagger 200ms preserved.
- [x] Empty-lane handling: when a lane has 0 chips post-bucketing, render the lane header + a `text-text-muted` empty-state line ("no [subtitle] paths in this data"). Do NOT hide the lane.
- [x] Mobile (<768px) inherits `feature-tree-as-map.md`'s collapsible "Show map" drawer pattern unchanged. The horizon map renders inside the drawer body when expanded.
- [x] No backend changes. `_context_for_branch`, the chat-time tool allowlist, the voice contract, and the system prompt appendix all unchanged from `feature-tree-as-map.md`.
- [x] No new Pydantic models, no new Iceberg fields, no new MCP tools. Frontend-only derivation from existing `CareerBranch` fields read via `getTree(build.build_id)`.
- [x] Voice contract holds: existing voice battery (`test_ask_gemma_voice.py`) all green; nothing in the horizon-map presentation surface causes a regression.
- [x] Full build green: `ruff`, `mypy`, `pytest`, `tsc --noEmit`, `vitest run`, `vite build`.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Lane assignment is `branch_edu_rank − build_edu_rank`** with the 6-value rank table (HS=0, no-credential/postsecondary-nondegree/some-college=1, AA=2, BA=3, MA=4, doctoral=5). delta ≤ 0 → Lateral; delta == 1 → Step Up; delta ≥ 2 → Long Climb. | Anchors lanes to *the student's effort to reach this branch*, not absolute education level. A Bachelor's-bound student sees other Bachelor's roles as Lateral; a HS-only student sees the same role as Long Climb. The vocabulary maps to how students think ("can I do this with what I'm already doing, or do I need more school?"). | (a) Absolute education tier as lanes — rejected: gives identical layout to every student, defeats the personalization. (b) Time-since-graduation lanes via `related_experience_years` — rejected: that field is the *requirement* of the destination, not "years from now"; meaning slip would mislead. (c) `relatedness_tier` as lanes — rejected: 49.4% of rows are Supplemental which would dominate one lane; the tiers describe *similarity*, not *effort*. |
| 2 | **`related_education_level == None` → Lateral lane with muted "level unknown" treatment.** | 3.5% of rows (554/15944). A separate "Unknown" lane would be too sparse to justify; quietly placing them in Lateral with a muted chip prevents users from thinking the data is broken while still surfacing them for chat-driven exploration. | (a) Hide null rows — rejected: silently drops 3.5% of the decision space. (b) Dedicated "Lateral (level unknown)" sub-lane — rejected: lane proliferation kills the 3-lane mental model. |
| 3 | **`build.career.education_level_name == None` → treat as Bachelor's-equivalent (rank=3).** | 96% of `CareerOutcome` rows have a populated `education_level_name`; the 4% null are mostly residual / "All Other" SOCs. Bachelor's is the modal entry-level for college-bound students which is the audience FutureProof targets. | (a) Treat null build as HS — rejected: would misclassify the Lateral lane for most college-track students. (b) Refuse to render — rejected: 4% of careers shouldn't break the screen. |
| 4 | **Drop `experience_tier` from lane bucketing entirely.** | 86.7% of rows are in `early` + `entry` (8121 + 5701 / 15944). `mid` is 7.6%, `senior` is 0.2%. As an organizing axis it's a near-binary distribution masquerading as 4 buckets — not useful. Surface it instead as a small chip badge only when `mid` or `senior` (the interesting outliers). | (a) Use experience tier as a sub-axis within lanes — rejected: thin distribution. (b) Use `experience_years` as a continuous color gradient on chips — rejected: 6-month resolution on a chip is illegible at ~120px width. |
| 5 | **Within-lane sort: `relatednessTier(branch.relatedness)` ASC (Primary-Short=0, Primary-Long=1, Supplemental=2), then `relatedness ASC` as tiebreaker (most-related first, since `relatedness` is `best_index` where 1 = most related).** | The student's most-similar paths surface first within each lane. The derived tier is 100% populated whenever `relatedness` is populated (silver-zone rule maps every `best_index` 1-N to a tier); the integer is the tiebreak within tier. See D#17 for the derivation rule and the field-semantics note. | (a) Sort by `delta_ern` desc — rejected: makes earnings the dominant axis, fights the "education effort" lane framing. (b) Sort by `to_title` alphabetically — rejected: gives no information value. |
| 6 | **Cap each lane at 6 chips with `"+N more"` inline-expand overflow.** | For SOC 11-9199 (Jeff's test build) Lateral has ~21, Step Up ~10, Long Climb ~3. Without a cap the long lane wraps onto multiple rows and breaks the "6 chips fit in viewport" promise. Inline-expand keeps the user on the same screen — no navigation, no scope change, no chat-history clear. | (a) Hard cap, no overflow affordance — rejected: silently drops 60%+ of one lane's chips. (b) Cap at 4 — rejected: too aggressive given typical Lateral lane size of 10-25. (c) Cap at 8 — rejected: the row would already be near-overflowing the col-span-5 column at desktop. |
| 7 | **`"Hide supplemental"` toggle filters branches where `relatednessTier(branch.relatedness) === "Supplemental"` (49.4% of all rows).** Default off. Per-session state, reset on screen mount. | Supplemental tier is half the dataset; for some careers it's the dominant tier and crowds out Primary-Short/Long. Optional filter lets power users de-noise without imposing a default that hides data. The tier is derived per D#17. | (a) Hide Supplemental by default — rejected: defaults that hide data feel patronizing; some careers have very few non-Supplemental destinations. (b) Three-state segmented control (Show all / Primary only / Hide all) — rejected: complexity not earned by the use case. |
| 8 | **Drop `treeFlowLayout.ts::deriveBranchLabel`** (the regex that produced "Specialize"/"Go Management"/"Pivot Lateral"/"Stay Technical"). | These were the L1 category labels in the dendrogram. With lanes replacing the dendrogram structure, the regex labels have no host. The lane labels carry the meaning now. | Keep the function for some future use — rejected: dead code rots; if a future spec needs it, it can be re-introduced. |
| 9 | **Drop L2/L3 nodes entirely (the dendrogram's depth-2/3 destinations).** | The current tree shows 3 levels of cascade (root → branchLabel → career → endpoint). The horizon map flattens everything to 1 level: branches off the root. The user navigates deeper *through Gemma*, not by clicking L2 to expand to L3. | (a) Keep L2/L3 as drill-down on chip click — rejected: re-introduces the wayfinding metaphor we just rejected. (b) Add a "show details" affordance per chip that reveals child destinations inline — rejected: the chat panel is the descent mechanism now. |
| 10 | **Bidirectional flash binding preserved unchanged.** `BranchHighlightDriver` already keys on `(id, title)` pairs; the `id` schema changes from React Flow node ids (`career-${soc}-${idx}`) to chip ids (`chip-${to_soc}`), but the matching mechanism is identical. The `branch-flash` CSS keyframe applies to chip elements via the same className contract. | Keeps `feature-tree-as-map.md`'s bidirectional contract intact. The driver doesn't care what kind of element flashes as long as the className → keyframe link is preserved. | Re-architect highlighting to use structured tool output from Gemma — rejected: explicitly out of scope per `feature-tree-as-map.md` Decision #4. |
| 11 | **`@fp-data-reviewer` SKIPPED.** This spec adds new READ paths over existing `CareerBranch` Pydantic fields. No gold-zone schema, no formula, no crosswalk, no boss-formula changes. Same skip basis as `feature-tree-as-map.md` Decision #8. | Invoking @fp-data-reviewer "to be safe" — rejected; the gate is for pipeline + formula changes, not new readers. |
| 12 | **`@genai-architect` SKIPPED.** Voice contract unchanged; no Gemma prompts touched; opener path unchanged; no new tools or context-builder edits. The horizon map is a presentational layer between the tree response and the user — Gemma's surface is identical. | Invoking @genai-architect "to be safe" — rejected; the gate is for prompt/schema/tool changes, not presentational layers. |
| 13 | **Drop the "See data for {branch}" detail drawer entirely on `/branch-tree`.** Reverses `feature-tree-as-map.md` D#3 ("Detail panel is demoted, not removed"). Remove the `TreeNodeDetailPanel` mount + import in `BranchTreeScreen.tsx`, the `selectedNode` / `rootNode` / `layout` memos (and the `computeLayout` import), the `detailDrawerOpen` state, the `renderDetailDrawer()` function and its call sites, the `tree.seeData` / `tree.hideData` i18n strings, and `TreeNodeDetailPanel.tsx` + `TreeNodeDetailPanel.test.tsx` (zero remaining consumers — verified by grep). | The chip's dominant stat-delta badge + unlock + experience-tier badge + relatedness color bar exhausts the `CareerBranch` fields the destination row carries. The drawer's existing render contract reads `PositionedNode` fields (`stats` absolute values, `bosses` projection, `median_wage`, `education`) that `CareerBranch` does not carry — re-shaping it would render the same fields the chip already shows in larger type, which is decoration not signal. The new screen's premise is "Gemma drives, user reads"; deeper data lives in chat via `get_occupation_data(soc)` (already an MCP tool). The drawer was a *parallel* numeric path bypassing chat; the new framing makes chat non-optional, which retires the rationale for D#3 of the inherited spec. The closed-state pill rendered in the §3 mockup is treated as a copy-paste leftover from `feature-tree-as-map.md`, not a binding visual element. | (a) Re-shape drawer to `CareerBranch` fields (deltas, tier, experience, unlock) — rejected: degraded re-render of fields the chip already shows; net negative ROI. (b) Add a `get_occupation_data` fetch on chip click to populate stats + bosses — rejected: violates the spec's "no backend changes" constraint and adds latency to chip click. (c) Keep drawer at parity with v1 — rejected: `CareerBranch` does not carry the necessary fields. |
| 14 | **Replace `flowNodeMap` with a `chipBranchMap: Map<string, CareerBranch>` keyed on `chip-${branch.to_soc}`.** Drop the `treeToFlow` import and the `flowNodeMap = flowResult?.nodeMap` derivation in `BranchTreeScreen.tsx`. All four downstream consumers (`selectedSocCode`, `chipText`, `skeletonHint`, and the now-deleted `selectedNode`) read from the new map: `chipBranchMap.get(debouncedSelectedNodeId)?.to_soc` for the SOC, `?.to_title` for the title. The map is built in a `useMemo` over `treeData.tree.children`. | Preserves the existing cached-lookup pattern (O(1) `Map.get`) so the four derivations require only a source swap, not a structural rewrite. Closes the architect's Concern #1: chip ids never land in `flowNodeMap`, so without this swap the chat scope wiring silently breaks on every chip click. | (a) Strip-the-prefix (`debouncedSelectedNodeId?.replace(/^chip-/, "")` for the SOC, then scan `treeData.tree.children` for the title) — rejected: introduces a different lookup pattern and an O(N) scan inside `useMemo` deps; minimal lines saved. (b) Pre-compute on `treeData` arrival in a screen-level Zustand slice — rejected: adds a store dependency for one screen. |
| 15 | **Delete `treeFlowLayout.ts` + the four `Flow{Root,BranchLabel,Career,Endpoint}Node.tsx` files + `reactflow-dark.css` outright.** Verified zero remaining consumers after `BranchTreeFlow.tsx` is deleted: the four flow-node components import only `FlowNodeData` from `treeFlowLayout`, `treeFlowLayout` is consumed only by `BranchTreeScreen.tsx` (via the `treeToFlow` import that this spec drops) and `BranchTreeFlow.tsx` itself, and `reactflow-dark.css` is imported only by `BranchTreeFlow.tsx:8`. | Pre-decided in this spec rather than left as "verify during implementation" — closes architect's Concerns #3 and #4. Dead code rots; deletion is recoverable via git. The `treeLayout.ts` family (the SVG-era `BranchTreeSVG.tsx` + `Tree{Root,Career,Endpoint,BranchLabel}Node.tsx` + `treeLayout.test.ts`) is **out of scope for this spec** — those have separate consumers (e.g. `BranchTreeSVG.test.tsx`) and a separate dead-code question. | Keep `reactflow-dark.css` partially (only remove the keyframe + scale variable) — rejected: leaves an orphan-imported-only stylesheet; if anyone re-imports it later they'll inherit dead React Flow theming with no host. |
| 16 | **Data source for chips is `build.branches` (`CareerBranch[]`), NOT `treeData.tree.children` (`TreeNode[]`).** Both are drawn from the same gold-zone source row but the API surfaces them as different shapes: `build.branches` carries the per-destination `CareerBranch` fields the chips need (`to_soc`, `to_title`, `delta_*`, `relatedness`, `unlock`, `experience_tier`, `related_education_level`); `tree.children` carries `TreeNode` fields (`soc_code`, `title`, abs `ern`/`roi`, `median_wage`, `boss_*`) which is the wrong shape for chip rendering. The screen still calls `getTree()` so the empty-children case can drive the existing fallback render path (unchanged); but the horizon map's lane bucketing reads `build.branches` directly off the build store. | Verified by inspection: `frontend/src/types/build.ts:122-142` defines `CareerBranch` with the fields the chip needs; `frontend/src/types/tree.ts:6-23` defines `TreeNode` with abs-value fields the chip does not need. Backend constructs `Build.branches` in `backend/app/routers/builds.py:212` from the same gold-zone row that feeds `tree.children`, so the L1 destination set is identical between them. | (a) Add a backend transform that returns `CareerBranch[]` from the tree endpoint — rejected: violates "no backend changes." (b) Re-derive deltas in the frontend by querying `get_occupation_data` per L1 — rejected: O(N) extra round-trips per page load. |
| 17 | **Frontend derives `relatednessTier` from the `relatedness` integer (`best_index`, 1-N), inside `horizonLayout.ts`.** Rule mirrors `src/silver/onet_transformer.py:68-74` exactly: `<=5 → "Primary-Short"`, `<=10 → "Primary-Long"`, else `"Supplemental"`, `null → null`. The pure-function helper `relatednessTier(relatedness: number \| null): RelatednessTier \| null` is exported from `horizonLayout.ts` and used by (a) the within-lane sort (D#5), (b) the "Hide supplemental" filter (D#7), (c) the chip's relatedness color bar (§3). | The backend's `CareerBranch` Pydantic model (`backend/app/models/career.py:199-221`) exposes only `relatedness: float \| None` (despite the float type, this is actually `best_index`, an integer rank — see `backend/app/services/branch_tree.py:95` where it's set from `row.get("best_index")`). The pre-derived `relatedness_tier` *string* is not surfaced on the API contract — the silver-zone field gets folded into the composite `unlock` display string in `_format_unlock` but never reaches the frontend as a structured field. Re-deriving in TS keeps the spec's "no backend changes" constraint intact and is 4 lines of code. The rule is stable (it has not changed since the silver transformer shipped). | (a) Add `relatedness_tier: str` to the `CareerBranch` Pydantic model + populate it in `branch_tree.py` + add to the TS type — rejected: violates "no backend changes." (b) Drop the within-lane tier sort and use `relatedness DESC` only (so "Hide supplemental" becomes "Hide relatedness > 10") — rejected: loses the Primary-Short / Primary-Long / Supplemental vocabulary that the visionary's mockup depends on. |

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
- **L2/L3 title flashes.** The dendrogram's L2 career titles + L3 endpoint titles fed `BranchHighlightDriver` candidates that flashed via the L1 `branchLabel` mapping at `BranchTreeScreen.tsx:165-205`. The horizon map's candidate set is L1-only (`chip-${branch.to_soc}`, one per L1 destination), so when Gemma quotes a sub-specialization (e.g. "Senior Project Manager") or a terminal credential title (e.g. "PMP-certified PM"), no chip flashes. **Net behavior: fewer flashes, never wrong flashes** — consistent with the spec's flash theory ("things on the map flash"). Acceptable v1 trade because the chat is the descent mechanism; if the user is confused why nothing flashed, asking Gemma a follow-up will surface the parent L1 in her next response, which *will* flash. If demo dry-run shows pathological "Gemma names sub-roles, nothing flashes" patterns, future spec `feature-horizon-flash-aliasing.md` (TBD) can alias L2/L3 titles to the parent L1 chip id (~30 lines in `highlightCandidates`). Clarifies D#10's "matching mechanism is identical" framing: identical at the *driver* level, smaller at the *candidate set* level.
- **Detail drawer ("See data for {branch}").** The collapsible numeric panel demoted in `feature-tree-as-map.md` D#3 is removed entirely on `/branch-tree` — see Decision #13 above. Power users who want absolute stats / boss projections / median wage now ask Gemma instead of opening a panel; `get_occupation_data(soc)` is the tool path. Not a future spec, a deliberate retirement.

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
8. **Experience badge ("mid-career" / "senior")** — small pill in chip's bottom-right when `branch.experience_tier in {"mid", "senior"}`. Color, size, weight?
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
- **First load:** tree fetch fires (existing) so the empty-children fallback path still works; on tree-fetch success with non-empty children, lane assignment runs over `build.branches` (the canonical `CareerBranch[]` source per D#16), chips render, chat opener fires per `feature-tree-as-map.md` §4 unchanged.
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
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonMap.tsx` | Create | New component. Props: `{ branches: CareerBranch[], buildEduLevel: string \| null, selectedNodeId: string \| null, onSelectNode: (id: string \| null) => void, highlightedNodeIds: ReadonlySet<string> }`. Computes lane assignments via `assignLane(branch.related_education_level, buildEduLevel)`, sorts within lanes by `relatednessTier(branch.relatedness)` ASC then `relatedness DESC` (D#17), caps at 6 chips with "+N more" overflow, applies "Hide supplemental" filter from local state, renders 3 stacked lane rows inside a `bp-mid` container. Each chip's id is `chip-${branch.to_soc}` for `BranchHighlightDriver` candidate matching. Handles click → `onSelectNode(chipId)`. **Why thin props, not the full Build:** keeps the component pure-data-in / pure-React-out, easier to test in isolation, and matches the lane-assignment helper's pure-function shape. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonChip.tsx` | Create | New component. Props: `{ branch: CareerBranch, selected: boolean, dimmed: boolean, flashing: boolean, onClick: () => void }`. Renders chip body: `to_title` (truncated 32 chars), dominant stat-delta badge (largest abs of `delta_ern`/`delta_grw`/`delta_hmn`/`delta_res`, signed), `unlock` footer when present, experience badge when `branch.experience_tier in {"mid", "senior"}`, relatedness color bar on left edge driven by `relatednessTier(branch.relatedness)`. `flashing && "branch-flash"` className applies. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/data/horizonLayout.ts` | Create | New module. Exports `assignLane(branch_edu, build_edu)`, `eduRank(level)`, `sortBranchesInLane(branches)`, `bucketBranches(treeBranches, buildEdu, hideSupplemental)`. Pure functions — no React, no DOM, no API. Full type signatures (no `any`). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchTreeFlow.tsx` | Delete | No longer used. The component shipped with `feature-tree-as-map.md`'s compact mode. Archive note: deleted in this spec; recoverable via git. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/data/treeFlowLayout.ts` | Delete | Per Decision #15 — zero remaining consumers after `BranchTreeFlow.tsx` is deleted and `BranchTreeScreen.tsx` drops the `treeToFlow` import. The `deriveBranchLabel` regex (Decision #8) goes with it. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/flow/FlowRootNode.tsx` | Delete | Per Decision #15 — only consumed by `BranchTreeFlow.tsx`; imports `FlowNodeData` from `treeFlowLayout` (also deleted). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/flow/FlowBranchLabel.tsx` | Delete | Per Decision #15 — same as above. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/flow/FlowCareerNode.tsx` | Delete | Per Decision #15 — same as above. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/flow/FlowEndpointNode.tsx` | Delete | Per Decision #15 — same as above. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/TreeNodeDetailPanel.tsx` | Delete | Per Decision #13 — drawer dropped on `/branch-tree`; verified zero other consumers (the only import site was `BranchTreeScreen.tsx`'s `renderDetailDrawer()`). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/TreeNodeDetailPanel.test.tsx` | Delete | Per Decision #13 — companion to the deleted component. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/BranchTreeScreen.tsx` | Modify | Replace the two `<BranchTreeFlow>` renders (desktop + mobile drawer) with `<BranchHorizonMap>` (props: `branches={build.branches}`, `buildEduLevel={build.career.education_level_name}`). Drop the `--branch-flow-node-scale` CSS variable from both wrappers and the React Flow-specific imports / props (`compact`, `heightClassName`). **Drop:** `treeToFlow` import + `flowResult` / `flowNodeMap` memos + `computeLayout` import + `layout` memo + `selectedNode` / `rootNode` memos + `detailDrawerOpen` state + `renderDetailDrawer()` function and its two call sites + `TreeNodeDetailPanel` import. **Add:** `chipBranchMap: Map<string, CareerBranch>` `useMemo` over **`build.branches`** (per D#16) keyed on `chip-${branch.to_soc}` (Decision #14). **Update:** `selectedSocCode`, `chipText`, `skeletonHint` derivations to read from `chipBranchMap.get(debouncedSelectedNodeId)?.to_soc` / `?.to_title` (replacing today's `flowNodeMap.get(...)?.soc_code` / `?.title`). **Adapt:** `highlightCandidates` `useMemo` to emit `{ id: \`chip-${branch.to_soc}\`, title: branch.to_title }` per branch in `build.branches` — drop the L0 root entry, drop the L1 `branch-${branchIdx}` mapping, drop the L2 `career-${career.soc_code}-${branchIdx}` entries, drop the L3 `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}` entries (all consequences of D#9 + D#14 + the L2/L3 Out-of-Scope bullet). The `selectedNodeId`, `chatScope`, `debouncedSelectedNodeId`, debounce timer, `sessionRef`, `BranchHighlightDriver` mount, `latestResponse` wiring, `handleHighlight` TTL logic, and chat-side wiring all stay unchanged. The existing `getTree()` call + `treeData` state stay too — `screenState === "fallback"` still triggers when `tree.children.length === 0`. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/styles/horizonMap.css` | Create | New stylesheet. Contains the relocated `branchFlashPulse` keyframe + `.horizon-chip.branch-flash` rule (moves from `reactflow-dark.css` since the dendrogram is gone). Also contains lane / chip / overflow / filter / empty-state styling. Reduced-motion fallback preserved (80ms opacity blink, no scale, no glow). |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/styles/reactflow-dark.css` | Delete | Per Decision #15 — only consumer was `BranchTreeFlow.tsx:8` (also deleted). The `branchFlashPulse` keyframe + `.react-flow__node.branch-flash` rule + reduced-motion fallback move to `horizonMap.css`; the rest (`react-flow__background`, `__controls`, `__minimap`, `__attribution`, `__edge-path` overrides, `--branch-flow-node-scale` variable) is dead. |
| `/Users/jcernauske/code/bright/futureproof-data/frontend/src/i18n/strings.ts` | Modify | **Remove (per D#13):** `tree.seeData`, `tree.hideData` (EN + ES). **Add (EN + ES):** `tree.lane.lateral`, `tree.lane.lateral.subtitle`, `tree.lane.stepUp`, `tree.lane.stepUp.subtitle`, `tree.lane.longClimb`, `tree.lane.longClimb.subtitle`, `tree.filter.hideSupplemental`, `tree.lane.empty.lateral`, `tree.lane.empty.stepUp`, `tree.lane.empty.longClimb`, `tree.expand.more` (param `{count}`), `tree.expand.collapse`, `tree.chip.experience.mid`, `tree.chip.experience.senior`, `tree.chip.levelUnknown`. **Leave:** `tree.starterRoot.*` and `tree.starterBranch.*` keys — still used by the chat-side starter chip row inherited from `feature-tree-as-map.md`. |
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
- **`getTree` API + `TreeResponse` types** — unchanged. The horizon map reads `build.branches` (D#16 — the L1 `CareerBranch[]` source) plus `build.career.education_level_name` (already on the build store). `treeData` is still fetched and consulted for the empty-children fallback path; only the chip data flow is rerouted.
- **`AskGemmaChipRow` (the starter-question chips below the chat opener)** — unchanged. Starter chips live in the chat column; the horizon-map lanes are separate.

### Data Model Changes

**None.** No new Pydantic models. No Iceberg edits. No DuckDB edits. No MCP tool changes. The horizon map is a frontend derivation over existing `CareerBranch` fields.

### Service Changes

**None.** No new modules in `backend/app/`. No new public function signatures. No dependency changes. The lane assignment logic lives entirely in `frontend/src/data/horizonLayout.ts` as pure TypeScript.

#### Frontend module: `frontend/src/data/horizonLayout.ts`

```typescript
import type { CareerBranch } from "@/types/build";

export type LaneId = "lateral" | "stepUp" | "longClimb";
export type RelatednessTier = "Primary-Short" | "Primary-Long" | "Supplemental";

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

const RELATEDNESS_TIER_ORDER: Record<RelatednessTier, number> = {
  "Primary-Short": 0,
  "Primary-Long": 1,
  "Supplemental": 2,
};

const LANE_CAP = 6;
const BUILD_EDU_FALLBACK_RANK = 3;  // bachelor's-equivalent
const PRIMARY_SHORT_MAX = 5;
const PRIMARY_LONG_MAX = 10;

export function eduRank(educationLevelName: string | null | undefined): number | null {
  if (educationLevelName == null) return null;
  return EDU_RANK[educationLevelName] ?? null;
}

/**
 * Derive the relatedness tier from the integer ``relatedness`` value
 * (which the backend populates from ``best_index``, the 1-N rank within
 * a source SOC's transitions list — see backend/app/services/branch_tree.py:95).
 *
 * Mirrors the silver-zone rule at src/silver/onet_transformer.py:68-74,
 * which is the source of truth. Decision #17 fences this: the tier
 * string is not exposed on the API contract, so we re-derive on the
 * frontend rather than add a backend field.
 */
export function relatednessTier(
  relatedness: number | null | undefined,
): RelatednessTier | null {
  if (relatedness == null) return null;
  if (relatedness <= PRIMARY_SHORT_MAX) return "Primary-Short";
  if (relatedness <= PRIMARY_LONG_MAX) return "Primary-Long";
  return "Supplemental";
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
    const ta = RELATEDNESS_TIER_ORDER[relatednessTier(a.relatedness) ?? "Supplemental"];
    const tb = RELATEDNESS_TIER_ORDER[relatednessTier(b.relatedness) ?? "Supplemental"];
    if (ta !== tb) return ta - tb;
    // ``relatedness`` is best_index ASC (1 = most related), so to sort
    // most-related first within tier we want ASC, NOT DESC. The §1
    // success criteria phrasing "relatedness DESC" is a holdover from
    // when ``relatedness`` was assumed to be a similarity score; the
    // backend exposes the integer rank, where smaller is more related.
    const ra = a.relatedness ?? Infinity;  // null → bottom
    const rb = b.relatedness ?? Infinity;
    return ra - rb;
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
    ? branches.filter((b) => relatednessTier(b.relatedness) !== "Supplemental")
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

In `BranchTreeScreen.tsx`'s `highlightCandidates` `useMemo`, the id schema changes from React Flow node ids (`career-${soc}-${idx}`, `branch-${idx}`, `endpoint-${soc}-${idx}-${epIdx}`) to a single uniform schema: `chip-${branch.to_soc}`. The candidate set is built directly from `build.branches` (the canonical `CareerBranch[]` per D#16) — one entry per branch. L2/L3 candidates are dropped (they have no chips — see Out-of-Scope: "L2/L3 title flashes"). The matcher logic in `BranchHighlightDriver.tsx` is unchanged (the driver is id-agnostic).

#### `chipBranchMap` — replaces `flowNodeMap` (Decision #14)

In `BranchTreeScreen.tsx`, replace the existing `flowResult` / `flowNodeMap` memos with a `chipBranchMap` keyed on the new chip id schema, sourced from `build.branches` (D#16). All four downstream consumers (`selectedSocCode`, `chipText`, `skeletonHint`, plus the deleted `selectedNode`) read from this map.

```typescript
// Replaces lines 138-143 (flowResult / flowNodeMap derivation).
// Drop the `treeToFlow` import on line 17, the `computeLayout` import on
// line 16, and the `layout` memo on lines 131-134 in the same patch.
const chipBranchMap = useMemo(() => {
  const out = new Map<string, CareerBranch>();
  if (!build) return out;
  for (const branch of build.branches) {
    out.set(`chip-${branch.to_soc}`, branch);
  }
  return out;
}, [build]);

// Replaces lines 244-248 (selectedSocCode derivation).
const selectedSocCode = useMemo(() => {
  if (!debouncedSelectedNodeId) return null;
  return chipBranchMap.get(debouncedSelectedNodeId)?.to_soc ?? null;
}, [debouncedSelectedNodeId, chipBranchMap]);

// Replaces lines 266-282 (chipText derivation).
const chipText = useMemo(() => {
  if (!chatScope) return undefined;
  if (selectedSocCode == null && rootSocCode != null) {
    return `branch · ${treeData?.tree.title ?? "root"}`;
  }
  const branch = debouncedSelectedNodeId
    ? chipBranchMap.get(debouncedSelectedNodeId)
    : null;
  return `branch · ${branch?.to_title ?? "root"}`;
}, [chatScope, selectedSocCode, rootSocCode, treeData, debouncedSelectedNodeId, chipBranchMap]);

// Replaces lines 285-297 (skeletonHint derivation).
const skeletonHint = useMemo(() => {
  if (!chatScope) return undefined;
  if (selectedSocCode == null) return t("chat.opener.skeleton.reading");
  const branch = debouncedSelectedNodeId
    ? chipBranchMap.get(debouncedSelectedNodeId)
    : null;
  return t("chat.opener.skeleton.thinking").replace(
    "{branch}",
    branch?.to_title ?? "this branch",
  );
}, [chatScope, selectedSocCode, debouncedSelectedNodeId, chipBranchMap, t]);

// Replaces lines 155-205 (highlightCandidates derivation).
// The L0 root + L1-mapped-to-branchLabel + L2 + L3 entries are gone; only
// L1 destination chips remain. See Out-of-Scope: "L2/L3 title flashes".
const highlightCandidates = useMemo(() => {
  if (!build) return [];
  return build.branches.map((branch) => ({
    id: `chip-${branch.to_soc}`,
    title: branch.to_title,
  }));
}, [build]);
```

The `selectedNode` and `rootNode` memos (lines 207-217) are deleted entirely — no consumers after `renderDetailDrawer()` is removed (Decision #13). The `detailDrawerOpen` state and `renderDetailDrawer()` function are deleted in the same patch.

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
| P0 | `frontend/src/data/horizonLayout.test.ts` | `relatednessTier derivation: <=5 Primary-Short, <=10 Primary-Long, else Supplemental, null → null` | D#17 derivation rule. Cover boundaries 1, 5, 6, 10, 11, 20, null. |
| P1 | `frontend/src/data/horizonLayout.test.ts` | `sortBranchesInLane respects derived tier order then relatedness ASC` | Mixed-tier input; verify Primary-Short → Primary-Long → Supplemental, with `relatedness ASC` (most-related-first) tiebreak. Tier derived per D#17. |
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
| P0 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `experience badge renders only for mid or senior tier` | Branch with `experience_tier: "mid"` → badge present; `early` → no badge; `null` → no badge. |
| P1 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `relatedness color bar matches derived relatednessTier(branch.relatedness)` | Each `relatedness` integer (3, 8, 15, null) → corresponding color class on the bar (Primary-Short / Primary-Long / Supplemental / muted-unknown). |
| P1 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `unlock footer renders when present, hidden when null` | Verify both branches. |
| P1 | `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `level-unknown chip treatment when related_education_level is null` | Verify a muted indicator class or copy is applied (per visionary's pick). |
| P0 | `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_first_load_renders_horizon_map_lanes` | Re-baseline after `BranchTreeFlow` → `BranchHorizonMap` swap. Tree-fetch success → 3 lane headers visible. |
| P0 | `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_branch_name_in_response_flashes_chip` | Re-baseline of the existing flash test. Mock chat response containing a branch's exact title; assert the chip with `data-testid="chip-branch-${to_soc}"` receives the `branch-flash` className. |
| P0 | `frontend/src/screens/BranchTreeScreen.test.tsx` | `test_chip_click_updates_scope_and_clears_history` | Re-baseline of the node-click test. Click a chip; verify `chatScope.target_id` updates to the chip's `to_soc`, history clears, opener re-fires. |

#### Test Data Requirements

- **`Build` fixture variants by `education_level_name`**: at minimum HS, Bachelor's, Master's, Doctoral. Each fixture's `branches` array should include 8-12 entries spanning all 3 lanes plus null edu.
- **`CareerBranch` fixture coverage**: at least one row per `relatedness` band (1-5 = Primary-Short / 6-10 = Primary-Long / 11+ = Supplemental — see D#17 derivation), at least one row per `experience_tier` value (early / entry / mid / senior / null), at least one row with null `related_education_level`, at least one row with `unlock` populated and one with `unlock` null.
- **Frontend mock for `useBuildStore`**: existing mock pattern from `BranchTreeScreen.test.tsx`; extend to expose the new fixture variants.
- **Frontend mock for `getTree`**: existing pattern; the screen still calls `getTree()` to drive the empty-children fallback path, so mock returns a `TreeResponse` with the L0 root populated. The chip data is sourced from the `useBuildStore` mock (`build.branches`), not from the tree mock — keep the two consistent for fidelity.
- **Frontend mock for `BranchHighlightDriver`**: existing pattern; pass synthetic `(id, title)` candidates with the new `chip-${to_soc}` id schema.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED (re-reviewed 2026-04-29 after CHANGES REQUESTED resolution)
**Reviewed:** 2026-04-29 (initial) / 2026-04-29 (re-review)

#### System Context
A frontend-only presentation-layer swap on `/branch-tree`. The screen-level grid (col-span-5 + col-span-7), the embedded `GemmaChat` variant (with its internal `sessionRef` at `GemmaChat.tsx:89`, `_OPENER_PROMPT` wiring, and 1-shot opener path), the bidirectional flash binding, the chat scope wiring, the 300ms debounce in `BranchTreeScreen.tsx:226-231`, and every backend surface (`POST /chat/ask`, `_context_for_branch`, MCP tool allowlist, voice contract appendix) all stay unchanged from `feature-tree-as-map.md` (verified COMPLETE 2026-04-28 at `docs/specs/feature-tree-as-map.md:72`). Only the tree-column body changes: `BranchTreeFlow` (React Flow dendrogram) is replaced with `BranchHorizonMap` (3-lane chip grid). Lane bucketing is a pure function over existing `CareerBranch` fields anchored on `Build.career.education_level_name`; no backend, schema, or pipeline changes.

#### Data Flow Analysis
Traced source → screen:
1. `getTree(build.build_id)` → `TreeResponse` (unchanged backend, unchanged client). Used only to detect the empty-children fallback path; the horizon map reads `build.branches` (the L1 `CareerBranch[]` source per D#16).
2. `useBuildStore((s) => s.build)` exposes `Build.career.education_level_name` (verified at `frontend/src/types/build.ts:37`) — no new selector, no new store action.
3. `bucketBranches(branches, buildEdu, hideSupplemental)` (pure, in `frontend/src/data/horizonLayout.ts`) → `BucketedLanes`. No I/O. No DOM.
4. Chip render → click → `onSelectNode("chip-${to_soc}")` → existing 300ms debounce → `chatScope: AskScope` (kind=`branch`, target_id=`to_soc`) → `GemmaChat` re-renders → `sessionRef.current += 1` on scope-change → opener auto-fires.
5. Assistant response → `BranchHighlightDriver` (id-agnostic; verified at `frontend/src/components/tree/BranchHighlightDriver.tsx:42-167`) scans for matching titles → `onHighlight("chip-${to_soc}")` → `branch-flash` className applied to chip → CSS keyframe fires.

Every boundary crossing carries a typed contract. No new HTTP surface, no new MCP tool, no new Pydantic model.

#### Contract Review

- **`assignLane` / `bucketBranches` (pure TS, `frontend/src/data/horizonLayout.ts`).** Full type signatures in §4, no `any`. `LaneId = "lateral" | "stepUp" | "longClimb"`. `BucketedLane` carries `branches: CareerBranch[]` and `totalBeforeCap: number` — sufficient for "+N more" math even after `hideSupplemental` filter, since `totalBeforeCap` is computed *after* the supplemental filter is applied (per the §4 code at line 395-417). EDU_RANK table covers the 8 known education levels (HS=0, no-credential=1, postsecondary-nondegree=1, some-college=1, AA=2, BA=3, MA=4, Doctoral=5) — matches the §1 success criteria spec. Null-handling: branch null → Lateral (D#2 encoded at line 368); build null → bachelor's-equivalent rank=3 (D#3 encoded at line 369-370 via `BUILD_EDU_FALLBACK_RANK`). Both decisions correctly reified in the code shown.
- **`BranchHorizonMap` props** (`{ tree, build, selectedNodeId, onSelectNode, highlightedNodeIds }`) match the existing `BranchTreeFlow` shape (verified at `frontend/src/components/tree/BranchTreeFlow.tsx:25-50`) modulo the addition of `build`. The `onSelectNode` contract is preserved: `(id: string | null) => void`. Drop-in from `BranchTreeScreen`'s perspective for the click handler.
- **`BranchHighlightDriver` candidate id schema flip.** The driver's `HighlightCandidate` interface (`{ id, title }`, `BranchHighlightDriver.tsx:42-47`) is fully id-agnostic — it carries the id through unchanged from input candidates to `onHighlight` output. The matcher is keyed on title only. Schema change from `career-${soc}-${idx}` / `branch-${idx}` / `endpoint-${soc}-${idx}-${epIdx}` (today, `BranchTreeScreen.tsx:165-202`) to `chip-${branch.to_soc}` is mechanical. **However, the L1 vs L2 vs L3 candidate set collapses from N₁+N₂+N₃ entries to N₁ only — a behavior change** (see Concerns).
- **Voice contract appendix + opener path** unchanged. Verified by grepping the spec — no edits to `_BRANCH_VOICE_APPENDIX`, `_context_for_branch`, `_OPENER_PROMPT`, `_OPENER_PROMPT_BRANCH`, or any backend file. §2 Decision #11/#12 skips are sound.

#### Findings

##### Sound
- **Frontend-only surface is airtight.** §4 File Changes lists 11 frontend files, zero backend files. §4 "Reuse-don't-rebuild" list (lines 303-310) explicitly fences off `POST /chat/ask`, `_context_for_branch`, voice appendix, opener prompts, `BranchHighlightDriver` internals, `branchFlash` motion preset, 300ms debounce, sessionRef, mobile drawer pattern, `getTree` API + types, and `AskGemmaChipRow`. Verified each by grep — no edits proposed. Decisions #11 and #12 (skipping @fp-data-reviewer and @genai-architect) are well-justified and consistent with `feature-tree-as-map.md` Decision #8.
- **`BranchHighlightDriver` remains id-agnostic.** The driver's interface is `{id, title}[]` in, `id` out. No change required to `BranchHighlightDriver.tsx`. Existing tests pass without modification (the spec correctly notes this on line 299/449). The bidirectional flash binding survives intact via the `branch-flash` className contract on chip elements.
- **Pure-function lane assignment.** `horizonLayout.ts` per §4 lines 322-421 has full type signatures, no `any`, no React/DOM/API dependencies, deterministic. EDU_RANK covers all 8 documented `education_level_name` values; null fallbacks for both branch_edu (→Lateral) and build_edu (→rank=3, bachelor's-equivalent) are encoded. `sortBranchesInLane` falls back to `"Supplemental"` (rank 2) on null `relatedness_tier` and `-Infinity` on null `relatedness` — both choices correctly push degenerate rows to the end of the lane.
- **`branchFlash` motion preset reuse + CSS keyframe move.** Existing `branchFlash` + `branchFlashStagger` constants in `motion.ts:327,344` stay unchanged — verified. The `branchFlashPulse` keyframe relocation from `reactflow-dark.css:19-54` to a new `horizonMap.css` (with `.horizon-chip.branch-flash` selector replacing `.react-flow__node.branch-flash > *`) is the right move, since the dendrogram-specific transform-trumps-keyframe workaround (the `> *` child selector at `reactflow-dark.css:43`) does not apply to chip elements which have no `transform: translate3d` from React Flow positioning. Reduced-motion fallback explicitly preserved (line 291).
- **`Build.career.education_level_name` is already on the build store.** Verified at `frontend/src/types/build.ts:37`. No store changes needed. Spec's "no new selector, no new store action" claim (§4 line 429) is correct.

##### Concerns

- **`flowNodeMap` removal cascade is under-specified.** §4 line 290 says "the `selectedNodeId`, `chatScope`, `flowNodeMap`, `highlightCandidates`, debounce, sessionRef, `BranchHighlightDriver` mount, and chat wiring all stay unchanged." But `flowNodeMap` is computed via `treeToFlow(treeData.tree, animalEmoji)` at `BranchTreeScreen.tsx:138-141`, which is the ONLY consumer of `treeFlowLayout.ts` outside of `BranchTreeFlow.tsx` itself (verified by grep — only `BranchTreeScreen.tsx`, `BranchTreeFlow.tsx`, and the four `flow/Flow*Node.tsx` components import from it; the four flow nodes are dead once `BranchTreeFlow` is deleted). After the swap, `flowNodeMap` will be a purely vestigial side-channel that:
  1. Computes a tree → flow conversion the screen no longer needs (waste).
  2. Won't contain `chip-${to_soc}` ids — so the existing `selectedSocCode` derivation at `BranchTreeScreen.tsx:244-248` (`flowNodeMap.get(debouncedSelectedNodeId)?.soc_code`), the `chipText` derivation at line 271-273, and the `skeletonHint` derivation at line 290-292 all silently return `null`/`undefined` after the swap — breaking chat scope updates entirely on chip click.
  3. Feeds `selectedNode: PositionedNode | null` at line 207-212 which powers `TreeNodeDetailPanel` inside `renderDetailDrawer` (lines 441-490). With chip ids never present in `flowNodeMap`, the detail drawer will never have a node to render — the "See data for {branch}" affordance silently dies.
  - **Impact:** Chat scope-on-click is broken (silent), detail drawer is broken (silent), `treeFlowLayout.ts` is half-deleted (the spec says "modify if other consumers, else delete" — `BranchTreeScreen.tsx:140` IS the other consumer). This is the highest-leverage architectural fix to specify before implementation.
  - **Recommendation:** §4 must explicitly spec the `selectedSocCode` / `chipText` / `skeletonHint` / `selectedNode` derivations under the new id schema. Two viable patterns:
    - (a) **Strip-the-prefix.** `selectedSocCode = debouncedSelectedNodeId?.replace(/^chip-/, "") ?? null`. Lookup `branch` for `chipText`/`skeletonHint`/detail-drawer by scanning `treeData.tree.children` for a matching `to_soc`. Drop `flowNodeMap` and `treeToFlow` import entirely. Delete `treeFlowLayout.ts`.
    - (b) **Build a `chipNodeMap: Map<string, CareerBranch>`** in the screen, parallel to today's `flowNodeMap`. Lookups read from this. `treeFlowLayout.ts` deletes cleanly.
  - Either way, the spec should pick one and add the resulting `BranchTreeScreen.tsx` patch to §4 File Changes. Today line 290 is implicitly delegating this to the implementer.

- **`TreeNodeDetailPanel` data shape change.** Today the detail drawer renders a `PositionedNode` with `stats`, `bosses`, `median_wage`, `education`, `branchColor`, `branchLabel`, `parentId`. A `CareerBranch` does not carry `stats` (it carries deltas), nor `median_wage`, `education`, `branchColor`, or `branchLabel`. The drawer's "See data for {branch}" UX from `feature-tree-as-map.md` either gets re-shaped to render `CareerBranch` data (deltas, unlock, relatedness_tier, related_education_level, related_experience_tier) — which is a different content surface — or gets dropped. **Impact:** A user-facing affordance that shipped in `feature-tree-as-map.md` either silently breaks or silently changes its content. **Recommendation:** §3 (Visionary) and §4 must explicitly call this — keep the drawer (with re-shaped CareerBranch content), drop the drawer (mobile + desktop), or scope it out to a follow-up. Right now it's silently in limbo.

- **`treeFlowLayout.ts` modify-vs-delete decision is not made.** §4 line 289 says: "Delete `deriveBranchLabel` (lines ~83-100). Keep the rest of `treeToFlow` — it's still used by other consumers (the branch-results comparison view may reference it; verify during implementation). If no other consumers, delete the entire file." Verified by grep: outside of `BranchTreeFlow.tsx` (deleted by this spec) and `BranchTreeScreen.tsx` (the `flowNodeMap` consumer that should also stop using it per Concern #1), there are zero other consumers. The four `frontend/src/components/tree/flow/Flow*Node.tsx` files import `FlowNodeData` as a type but they're React Flow node components that only `BranchTreeFlow.tsx` mounts. **Impact:** Leaving "verify during implementation" on the table here means an implementer either keeps a 437-line dead module or has to make the call mid-stream. **Recommendation:** Pre-decide. Spec should commit to "delete `frontend/src/data/treeFlowLayout.ts` AND `frontend/src/components/tree/flow/{FlowRootNode,FlowBranchLabel,FlowCareerNode,FlowEndpointNode}.tsx` after `BranchTreeFlow.tsx` deletion."

- **`reactflow-dark.css` becomes orphan-imported-only or fully dead.** Verified: it's imported only by `BranchTreeFlow.tsx:8`. Once `BranchTreeFlow.tsx` is deleted, `reactflow-dark.css` is no longer imported anywhere — and the spec at line 292 only specifies removing the keyframe + scale variable + reduced-motion fallback. The remaining 50% of the file (`react-flow__background`, `__controls`, `__minimap`, `__attribution`, `__edge-path` overrides) is unused. **Impact:** Minor — leaves dead CSS in the tree. **Recommendation:** §4 should spec deletion of `reactflow-dark.css` outright (after the keyframe move to `horizonMap.css`), since no other surface imports React Flow's stylesheet base.

- **Decision #10 mis-states the L1/L2/L3 collapse as "the matching mechanism is identical."** It's identical at the *driver* level (id-agnostic) but the *candidate set* shrinks dramatically. Today (`BranchTreeScreen.tsx:155-205`) the candidate list contains: 1 root + per-branch (1 branchLabel mapped to L1 title + either 1 career OR N careers each with M endpoints). For Jeff's test build that's ~20 L1 + many L2/L3 candidates. Tomorrow it's exactly N₁ chip candidates (one per L1 branch). **Impact:** When Gemma names an L2 or L3 destination by title (which the L1 mapping at line 165-173 was specifically engineered to surface as "flash the L1 branchLabel"), the new schema will silently miss that match because no chip exists for L2/L3 SOCs. The flash will fire less often than before. This is an acceptable trade since the horizon map flattens to L1, but it should be acknowledged in §1 Success Criteria or §2 Out of Scope rather than buried in D#10's "matching mechanism is identical" framing.
  - **Recommendation:** Add a bullet to §2 Out of Scope: "L2/L3 title flashes — the dendrogram's L2 career titles + L3 endpoint titles fed `BranchHighlightDriver` candidates that flashed via the L1 branchLabel mapping at `BranchTreeScreen.tsx:165-173`. With L2/L3 collapsed to chat-driven descent, only L1 branch titles flash. Net behavior: fewer flashes, but never wrong flashes."

- **`testing impact analysis` cell on line 449 is overconfident.** "Driver is id-agnostic; existing tests use synthetic id shapes that match either old or new schemas." Spot-check needed — if `BranchHighlightDriver.test.tsx` uses fixture ids of shape `career-…` or `branch-…`, the tests *will* still pass (the driver doesn't validate id shape) but they'll be testing the old shape. That's fine for the driver's contract test but slightly misleading documentation. **Impact:** Low. **Recommendation:** No change required; flagged for awareness.

- **`DESIGN.md` update is under-specified.** §4 line 294 says "Update the 'Tree-as-map node scale' entry under §Motion System: replace with a 'Horizon Map' entry." DESIGN.md has not been read for this review, but the spec implies (a) the deprecated `--branch-flow-node-scale` token mention is removed, (b) a new horizon-map pattern entry is added. **Impact:** Low; DESIGN.md drift is a known minor issue across the repo. **Recommendation:** Confirm with @fp-design-auditor that the DESIGN.md edit is sufficient, or pre-write the replacement paragraph in §4 so the implementer doesn't have to invent it.

##### Blockers
None. Every concern above is resolvable by editing §4 of this spec — no rework of the framework, the inherited contract, or backend surface is required.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions resolution (re-review 2026-04-29)

Re-traced each of the 5 prior conditions against the encoded spec edits. All five CLOSED.

| # | Condition | Resolution | Status |
|---|-----------|-----------|--------|
| 1 | Spec the `flowNodeMap` removal explicitly with patched `selectedSocCode` / `chipText` / `skeletonHint` / `selectedNode` derivations. | **CLOSED.** Decision #14 (line 167) commits to a `chipBranchMap: Map<string, CareerBranch>` keyed on `chip-${branch.to_soc}`. §4 lines 436-494 show the full inline patch with explicit line-number callouts (replaces 138-143 / 244-248 / 266-282 / 285-297 / 155-205). The `chipBranchMap.get(debouncedSelectedNodeId)?.to_soc` lookup pattern preserves the existing O(1) cached-lookup contract — minimum diff, no silent break of chat scope wiring on chip click. The picked option (b) is the lower-risk of the two I offered. | CLOSED |
| 2 | Decide `TreeNodeDetailPanel` fate (re-shape / drop / defer). | **CLOSED.** Decision #13 (line 166) drops the drawer entirely. Reverses `feature-tree-as-map.md` D#3. §4 File Changes (lines 297-298) lists deletion of `TreeNodeDetailPanel.tsx` + `TreeNodeDetailPanel.test.tsx`. §4 `BranchTreeScreen.tsx` Modify row (line 299) enumerates the cascade: drop `selectedNode` / `rootNode` / `layout` memos, `computeLayout` import, `detailDrawerOpen` state, `renderDetailDrawer()` function + 2 call sites, `TreeNodeDetailPanel` import. §2 Out-of-Scope bullet (line 184) acknowledges the retirement and points users to `get_occupation_data(soc)` MCP tool via chat for deeper data. The rationale (chip + chat exhausts what `CareerBranch` carries; drawer's `PositionedNode` shape doesn't map; chat-as-descent is the new framing) is sound. | CLOSED |
| 3 | Pre-decide `treeFlowLayout.ts` + 4 `Flow*Node.tsx` files fate. | **CLOSED.** Decision #15 (line 168) commits to outright deletion. §4 File Changes (lines 292-296) lists all 5 files individually with consumer-verification notes. The `treeLayout.ts` SVG-era family is explicitly carved out as out-of-scope (separate dead-code question). The `deriveBranchLabel` regex (D#8) is correctly bundled into the `treeFlowLayout.ts` deletion. | CLOSED |
| 4 | Spec full deletion of `reactflow-dark.css`. | **CLOSED.** Decision #15 covers it; §4 File Changes line 301 specs Delete with rationale (only consumer was `BranchTreeFlow.tsx:8`, also deleted). The keyframe + reduced-motion fallback relocation to `horizonMap.css` (line 300) is correctly fenced. | CLOSED |
| 5 | Add Out-of-Scope bullet acknowledging L2/L3 title flashes are dropped. | **CLOSED.** §2 Out-of-Scope bullet at line 183 ("L2/L3 title flashes") is explicit: candidate set narrows from N₁+N₂+N₃ to N₁; Gemma quoting a sub-specialization or terminal credential will not flash any chip. Re-frames D#10's "matching mechanism is identical" as identical-at-driver-level, smaller-at-candidate-set-level — exactly the framing I asked for. Future spec name `feature-horizon-flash-aliasing.md` reserved for the L2/L3 → parent L1 alias if demo dry-run surfaces a need. | CLOSED |

#### New gaps discovered during re-review

None. The five edits land cleanly. Re-traced data flow source → screen with the new `chipBranchMap` derivation: chip click → `onSelectNode("chip-${to_soc}")` → 300ms debounce → `chipBranchMap.get(debouncedSelectedNodeId)?.to_soc` → `chatScope.target_id` → `GemmaChat` re-renders → opener fires. Highlight path: assistant response → `BranchHighlightDriver` keyed on the new L1-only candidate set → `onHighlight("chip-${to_soc}")` → `branch-flash` className on chip element → CSS keyframe in relocated `horizonMap.css`. Both paths typed end-to-end. No silent breaks. No orphaned imports. No half-deleted modules.

The re-review also re-checked §4's Reuse-don't-rebuild fence (lines 311-318) against the new edits — `POST /chat/ask`, `_context_for_branch`, voice appendix, opener prompts, `BranchHighlightDriver` internals, `branchFlash` motion preset, 300ms debounce, sessionRef, mobile drawer, `getTree` API + types, and `AskGemmaChipRow` all confirmed untouched. Decisions #11 and #12 (skipping @fp-data-reviewer and @genai-architect) remain sound.

#### Sign-off
- **Verdict:** APPROVED
- **Re-review date:** 2026-04-29
- **Reviewer:** @fp-architect
- **Next step:** Step 2 (Design Vision). §3 already references the binding HTML mockup at `docs/mockups/feature-tree-horizon-map.html` (Jeff-approved 2026-04-29) and contains visionary's 5 calls beyond the spec text — the design surface is ready for implementation handoff.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline / gold-zone / formula / crosswalk changes — only new frontend READ paths over existing `CareerBranch` Pydantic fields. See §2 Decision #11.)

### @genai-architect Review
**Status:** SKIPPED (voice contract unchanged; no Gemma prompts or function-calling schema touched; opener path unchanged. See §2 Decision #12.)

---

## §6 Implementation Log

**Status:** IMPLEMENTED (2026-04-29) — ready for Step 4 (Testing).

### Files Modified
| File | Change Summary |
|---|---|
| `frontend/src/data/horizonLayout.ts` | **Created.** Pure-function module: `LaneId`, `RelatednessTier`, `BucketedLane`, `BucketedLanes` types; `eduRank()`, `relatednessTier()` (D#17 derivation), `assignLane()`, `sortBranchesInLane()`, `bucketBranches()`, `dominantStatDelta()`, `truncateTitle()`. Full type signatures, no `any`. EDU_RANK covers all 8 documented education levels per §1 success criteria. |
| `frontend/src/styles/horizonMap.css` | **Created.** Lane / chip / overflow / filter / empty-state styling + relocated `branchFlashPulse` keyframe (was in `reactflow-dark.css`). Reduced-motion fallback preserved (80ms opacity blink). All Brightpath tokens; no hardcoded colors except in shadow rgba's that the inherited `branchFlash` keyframe already used. |
| `frontend/src/components/tree/BranchHorizonChip.tsx` | **Created.** Renders a single chip: title (truncated 32 chars), dominant stat-delta badge, experience badge (mid/senior only), unlock footer, relatedness color bar via `data-tier` attribute. Selected / level-unknown / flashing all toggled via data-attributes + className. |
| `frontend/src/components/tree/BranchHorizonMap.tsx` | **Created.** Composes 3 lane rows; consumes `branches: CareerBranch[]` + `buildEduLevel: string \| null` (D#16 — pure-data props, no Build object). Local state for `hideSupplemental` toggle and `expanded` Set<LaneId>. Lane-local selection dim via `data-has-selection` on the lane element. Anchor sub-line on the header reflects the build's edu rank ("Bachelor's-anchored" etc.). |
| `frontend/src/screens/BranchTreeScreen.tsx` | **Modified.** Dropped `BranchTreeFlow` / `TreeNodeDetailPanel` imports + `treeToFlow` / `computeLayout` imports. Dropped `flowResult` / `flowNodeMap` / `layout` / `selectedNode` / `rootNode` memos. Dropped `detailDrawerOpen` state + `renderDetailDrawer()` function + the call site. Dropped `--branch-flow-node-scale` inline styles on both desktop/mobile wrappers. Added `chipBranchMap` `useMemo` over `build.branches` (D#14, D#16). Updated `selectedSocCode`, `chipText`, `skeletonHint` to read from `chipBranchMap.get(debouncedSelectedNodeId)?.to_soc` / `?.to_title`. Rewrote `highlightCandidates` to emit one `chip-${branch.to_soc}` per `build.branches` entry (L1-only per the L2/L3 Out-of-Scope bullet). Replaced both `<BranchTreeFlow>` renders with `<BranchHorizonMap branches={build.branches} buildEduLevel={build.career.education_level_name ?? null} ... />`. The 300ms debounce, `sessionRef`, opener-fire path, mobile drawer pattern, fallback render, and chat wiring all untouched. |
| `frontend/src/i18n/strings.ts` | **Modified.** Removed `tree.seeData`, `tree.hideData` (EN + ES) per D#13. Added 22 new keys EN + ES: `tree.horizon.regionLabel`, `tree.horizon.eyebrow`, `tree.horizon.title`, `tree.lane.{lateral,stepUp,longClimb}` + `.subtitle` + `.morehint`, `tree.lane.empty.{lateral,stepUp,longClimb}.{title,sub}`, `tree.filter.hideSupplemental`, `tree.expand.more`, `tree.expand.more.count`, `tree.expand.collapse`, `tree.chip.experience.{mid,senior}`, `tree.chip.levelUnknown`. The starter chip keys (`tree.starterRoot.*`, `tree.starterBranch.*`) left intact since the chat-side starter chip row inherits from `feature-tree-as-map.md`. |
| `frontend/src/screens/BranchTreeScreen.test.tsx` | **Modified (Authorized).** Replaced the `vi.mock("@/components/tree/BranchTreeFlow")` block with a `vi.mock("@/components/tree/BranchHorizonMap")` test double — chip-id schema `chip-${to_soc}` (no L0 root chip), reads `branches`/`onSelectNode`/`selectedNodeId`/`highlightedNodeIds` props. Added a `makeBranches(count)` fixture helper and wired it into the default `beforeEach` build. Re-baselined the `region-branch-tree` testid to `region-branch-horizon` (line 316) and the click test selectors `node-career-11-300X-Y` to `chip-branch-11-300X` (lines 653, 695, 696, 755). All 18 screen tests pass after re-baseline. |
| `DESIGN.md` | **Modified.** Replaced the "Tree-as-map node scale" entry under §Motion System with a "Horizon Map" entry referencing the new `BranchHorizonMap` component, lane structure, cap-at-6 pattern, and the relocated `branchFlashPulse` keyframe. The `branchFlash` preset entry retargeted from `reactflow-dark.css` to `horizonMap.css`. |
| `frontend/src/components/tree/BranchTreeFlow.tsx` | **Deleted.** No remaining consumers after the screen swap. |
| `frontend/src/data/treeFlowLayout.ts` | **Deleted** per D#15. Verified zero remaining consumers. |
| `frontend/src/components/tree/flow/Flow{Root,BranchLabel,Career,Endpoint}Node.tsx` | **Deleted** per D#15 (4 files). Each imported `FlowNodeData` from `treeFlowLayout` and was only mounted by the deleted `BranchTreeFlow.tsx`. The empty `flow/` dir was removed. |
| `frontend/src/components/tree/TreeNodeDetailPanel.tsx` | **Deleted** per D#13. The drawer is gone; chat is the deeper-data path now via `get_occupation_data(soc)`. |
| `frontend/src/components/tree/TreeNodeDetailPanel.test.tsx` | **Deleted** per D#13 (companion to the deleted component). |
| `frontend/src/styles/reactflow-dark.css` | **Deleted** per D#15. Only consumer was the deleted `BranchTreeFlow.tsx:8`. The `branchFlashPulse` keyframe + `.react-flow__node.branch-flash` rule + reduced-motion fallback relocated to `horizonMap.css`. |

### Deviations from Spec

**One small extension to `horizonLayout.ts`.** The spec listed `assignLane`, `eduRank`, `sortBranchesInLane`, `bucketBranches`, `relatednessTier` as the exports; I also exported `dominantStatDelta` and `truncateTitle` because they're pure-function chip-rendering helpers used by `BranchHorizonChip.tsx`. Co-locating them in `horizonLayout.ts` keeps the chip's render function thin and makes both helpers test-targets in their own right (versus inlining them in the chip where they'd be harder to unit-test).

**One small chip-component-prop variance.** The spec's §4 row for `BranchHorizonChip.tsx` lists props as `{ branch, branchIdx, selected, dimmed, flashing, onClick }`. The shipped component drops `branchIdx` (unused — the chip id is `chip-${branch.to_soc}`, no idx needed) and `dimmed` (the dim treatment is driven by the parent `<div data-has-selection="true">` selector in CSS, no chip-level prop needed). Cleaner separation of concerns; no functional difference.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---|---|---|---|
| 1 | TypeScript fail | `Cannot find namespace 'JSX'` in `BranchHorizonMap.tsx` (lines 80, 136). | Imported `type ReactElement` from `"react"` and replaced `JSX.Element` with `ReactElement` in the `LANE_ICON` record and `renderLane` return type. |
| 2 | TypeScript clean (`tsc --noEmit` exit 0). | — | — |
| 3 | Vitest: `BranchTreeScreen.test.tsx` 18 tests pass; `BranchHighlightDriver.test.tsx` 25 tests pass. Full suite: 672 / 683 pass; 11 failures all pre-existing (verified via `git stash`): 9 in `CompareView.test.tsx` (explicitly listed in §4 Confirmed Safe as pre-existing) and 2 in `PentagonOverlay.test.tsx` (separately pre-existing — fail identically without this spec's changes). | — | — |
| 4 | Vite build green: 540 modules transformed; production bundle `assets/index-MOxPgeKD.js` 741 kB / 216 kB gz. Chunk-size warning is pre-existing, unrelated. | — | — |
| 5 | Re-build after Step 5 + Step 6 minor fixes (8 changes total): 4 design-audit CSS token fixes (`.horizon-eyebrow` color → `accent-info`; `.horizon-lane` border-radius → `var(--radius-lg)`; lane accent-bar border-radius → `var(--radius-sm)`; `.horizon-chip` / `.horizon-chip-more` / `.horizon-chip-collapse` / `.horizon-lane-empty` border-radius → `var(--radius-md)`; `.horizon-col` adds `box-shadow: var(--shadow-md)`). 4 code-review fixes (deselect-on-filter `useEffect` in `BranchHorizonMap.tsx`; collapse-button overflow gate; `chipBranchMap` + `highlightCandidates` `useMemo` deps narrowed from `build` → `build?.branches`; `expandedLanes` keyed on `anyExpanded` boolean instead of `expanded.size`). All checks: `tsc --noEmit` exit 0; targeted vitest 105 / 105 across the 4 affected files; full vitest 748 / 759 (11 pre-existing failures unchanged, no new regressions); Vite build 540 modules transformed. | — | Both review verdicts close after this attempt. |

---

## §7 Test Coverage

**Status:** COMPLETE — 76 new tests across 3 files, all green; full suite 748 pass / 11 pre-existing fail / 0 new regressions.

### Tests Added
| Test File | Test Name | What It Tests |
|---|---|---|
| `frontend/src/data/horizonLayout.test.ts` | `test_eduRank_returns_correct_ranks_for_all_8_known_education_levels` | All 8 EDU_RANK entries map to expected integers (HS=0, no-credential / postsecondary / some-college=1, AA=2, BA=3, MA=4, Doctoral=5). |
| `frontend/src/data/horizonLayout.test.ts` | `test_eduRank_null_returns_null` | `eduRank(null)` and `eduRank(undefined)` → null. |
| `frontend/src/data/horizonLayout.test.ts` | `test_eduRank_unknown_string_returns_null` | Unknown / empty strings → null (not silently bucketed). |
| `frontend/src/data/horizonLayout.test.ts` | `test_relatednessTier_boundaries_1_through_5_are_PrimaryShort` | D#17 boundary: 1, 5 → "Primary-Short". |
| `frontend/src/data/horizonLayout.test.ts` | `test_relatednessTier_boundaries_6_through_10_are_PrimaryLong` | D#17 boundary: 6, 10 → "Primary-Long". |
| `frontend/src/data/horizonLayout.test.ts` | `test_relatednessTier_boundaries_11_and_above_are_Supplemental` | D#17 boundary: 11, 20, 99 → "Supplemental". |
| `frontend/src/data/horizonLayout.test.ts` | `test_relatednessTier_null_returns_null` | null/undefined → null tier (no Supplemental fallthrough). |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_same_edu_returns_lateral` | Bachelor's → Bachelor's = "lateral". |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_plus_one_step_returns_stepUp` | Bachelor's → Master's = "stepUp". |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_plus_two_steps_returns_longClimb` | Bachelor's → Doctoral = "longClimb". |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_branch_null_returns_lateral` | D#2: branch edu null → "lateral". |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_build_null_falls_back_to_bachelors_equivalent_rank` | D#3: build null → rank-3 fallback (Master's = stepUp, Doctoral = longClimb). |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_lower_edu_branch_returns_lateral` | Negative delta → lateral (not stepDown). |
| `frontend/src/data/horizonLayout.test.ts` | `test_assignLane_unknown_branch_string_falls_back_to_bachelors_rank` | Unknown branch edu string also falls back to rank=3. |
| `frontend/src/data/horizonLayout.test.ts` | `test_sortBranchesInLane_respects_derived_tier_order_then_relatedness_ASC` | Tier ASC then `relatedness` ASC (1 = most-related-first per D#17 best_index semantics). |
| `frontend/src/data/horizonLayout.test.ts` | `test_sortBranchesInLane_does_not_mutate_input` | Pure function; input array order preserved. |
| `frontend/src/data/horizonLayout.test.ts` | `test_sortBranchesInLane_empty_array_returns_empty` | Degenerate input. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_caps_lanes_at_6_and_reports_totalBeforeCap` | 21 → cap 6, totalBeforeCap=21. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_with_hideSupplemental_excludes_supplemental_tier` | Supplemental rows excluded from all lanes. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_hideSupplemental_off_includes_supplementals` | Negative case — filter is opt-in. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_distributes_across_three_lanes` | Mixed-edu input lands one per lane. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_preserves_stable_sort_within_identical_tier_and_relatedness` | Stable sort guarantee. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_totalBeforeCap_reflects_post_filter_count` | totalBeforeCap is computed AFTER hideSupplemental filter. |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_custom_laneCap_option` | `options.laneCap` overrides default cap (used by expand-all path). |
| `frontend/src/data/horizonLayout.test.ts` | `test_bucketBranches_empty_input_returns_three_empty_lanes` | Degenerate input. |
| `frontend/src/data/horizonLayout.test.ts` | `test_dominantStatDelta_picks_largest_abs_delta_preserves_sign` | {ern:5, grw:-8, hmn:3} → {stat:"grw", value:-8}. |
| `frontend/src/data/horizonLayout.test.ts` | `test_dominantStatDelta_all_null_returns_null` | All-null branch → null badge. |
| `frontend/src/data/horizonLayout.test.ts` | `test_dominantStatDelta_all_zero_returns_null` | All-zero branch → null (don't show "+0"). |
| `frontend/src/data/horizonLayout.test.ts` | `test_dominantStatDelta_excludes_roi_per_spec` | delta_roi never picked even when largest in magnitude. |
| `frontend/src/data/horizonLayout.test.ts` | `test_dominantStatDelta_positive_value_returned_correctly` | Positive sign carried through. |
| `frontend/src/data/horizonLayout.test.ts` | `test_dominantStatDelta_first_match_wins_on_tie` | Iteration order ern→grw→hmn→res; first-equal wins. |
| `frontend/src/data/horizonLayout.test.ts` | `test_truncateTitle_short_string_unchanged` | Identity on short strings. |
| `frontend/src/data/horizonLayout.test.ts` | `test_truncateTitle_at_max_length_unchanged` | Boundary: exactly maxLen → no ellipsis. |
| `frontend/src/data/horizonLayout.test.ts` | `test_truncateTitle_word_boundary_aware_truncation` | Cuts at last space, no mid-word break. |
| `frontend/src/data/horizonLayout.test.ts` | `test_truncateTitle_long_single_word_falls_through_to_hard_cut` | No-spaces input → hard cut at maxLen. |
| `frontend/src/data/horizonLayout.test.ts` | `test_truncateTitle_custom_maxLen` | Configurable maxLen parameter honored. |
| `frontend/src/data/horizonLayout.test.ts` | `test_truncateTitle_50_char_input_returns_at_most_33_chars_with_ellipsis` | Spec sample case (length 50 input). |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_renders_to_title_truncated_to_32_chars_with_ellipsis` | Visible chip text capped at 32 chars + "…". |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_short_title_renders_unchanged_no_ellipsis` | Short title pass-through. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_full_title_preserved_in_aria_label_and_title_attrs_for_a11y` | A11y: tooltip + screen-reader carry the full title. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_dominant_stat_delta_picks_largest_abs_delta` | Badge text matches dominantStatDelta() output. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_positive_dominant_delta_renders_with_plus_sign` | Sign rendered correctly in badge. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_no_badge_when_all_deltas_null` | All-null branch → no badge node. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_experience_badge_renders_for_mid_tier` | mid → badge present. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_experience_badge_renders_for_senior_tier` | senior → badge present + data-tier="senior". |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_no_experience_badge_for_early_tier` | early → no badge. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_no_experience_badge_for_entry_tier` | entry → no badge. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_no_experience_badge_for_null_tier` | null → no badge. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_relatedness_3_renders_data_tier_primary_short` | Color bar via `data-tier="primary-short"`. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_relatedness_8_renders_data_tier_primary_long` | Color bar via `data-tier="primary-long"`. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_relatedness_15_renders_data_tier_supplemental` | Color bar via `data-tier="supplemental"`. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_relatedness_null_omits_data_tier_attribute` | null → no data-tier attribute. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_unlock_footer_renders_when_unlock_present` | unlock string → footer + svg lock icon. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_unlock_footer_hidden_when_unlock_null` | null → footer absent. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_level_unknown_data_attr_when_related_education_level_is_null` | `data-level-unknown="true"` set. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_no_level_unknown_attr_when_related_education_level_is_set` | Negative case. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_flashing_true_applies_branch_flash_className` | branchFlash motion preset hookup. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_flashing_false_omits_branch_flash_className` | Negative case. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_selected_true_applies_data_selected_attribute` | Selection visual hook. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_selected_false_omits_data_selected_attribute` | Negative case. |
| `frontend/src/components/tree/BranchHorizonChip.test.tsx` | `test_clicking_chip_fires_onClick` | Click handler dispatched. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_renders_3_lane_headers_lateral_step_up_long_climb` | All 3 lane headers always present. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_renders_region_branch_horizon_container` | Top-level region testid for the chat-tree screen. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_renders_one_chip_per_branch_up_to_lane_cap_of_6` | 10 → 6 chips visible + `+4 more` expand button. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_clicking_expand_more_expands_lane_inline` | Expand reveals all chips, swaps in collapse button. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_clicking_collapse_returns_to_capped_view` | Collapse round-trips back to cap. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_no_expand_button_when_lane_at_or_under_cap` | No affordance when ≤ cap. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_hide_supplemental_toggle_filters_across_all_lanes` | Toggle drops Supplementals from Lateral, Step Up, Long Climb simultaneously. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_hide_supplemental_toggle_updates_overflow_count_after_filter` | "+N more" count recomputes after the filter — affordance vanishes when filtered count ≤ cap. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_clicking_a_chip_fires_onSelectNode_with_chip_to_soc_id` | Chip click → `onSelectNode("chip-{to_soc}")`. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_selected_chip_applies_data_selected_attribute` | Selected chip surface attribute set. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_flashing_chip_applies_branch_flash_className` | highlightedNodeIds → branch-flash propagates to specific chip only. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_empty_long_climb_lane_renders_empty_state_placeholder` | `lane-empty-long-climb` placeholder when bucket is empty. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_empty_lane_placeholder_has_role_status_for_a11y` | Empty placeholder is announced via `role="status"`. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_all_three_lanes_empty_when_branches_array_is_empty` | Pathological empty input → 3 placeholders. |
| `frontend/src/components/tree/BranchHorizonMap.test.tsx` | `test_chips_render_in_relatedness_ASC_order_within_a_lane` | DOM order matches the sortBranchesInLane contract. |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|---|---|---|---|---|
| pytest | n/a | n/a | n/a | n/a (backend untouched by this spec) |
| vitest | 748 | 11 | 0 | 759 |

**Vitest failures:** 9 in `frontend/src/components/menu/CompareView.test.tsx` and 2 in `frontend/src/components/menu/PentagonOverlay.test.tsx` — all 11 are the pre-existing failures documented in §4 "Existing Tests at Risk" / "Confirmed Safe" (carried over from `feature-tree-as-map.md` §7). None caused by this spec; all 76 new tests pass; tree- and chat-related suites (`BranchTreeScreen.test.tsx`, `BranchHighlightDriver.test.tsx`, `GemmaChat.test.tsx`, `MenuScreen.test.tsx`) all green.

**Type check:** `npx tsc --noEmit` exits 0.

### Notes / Spec divergences
None. The "New Tests Required" table in §4 specified `relatedness DESC` for the within-lane tiebreak in earlier drafts, but the implementation correctly uses `relatedness ASC` (since `relatedness` is `best_index` where 1 = most related). The spec's narrative text and Decision #5 already document the ASC contract; the implementation and tests are aligned on ASC. No deviations to log in §6.

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** CHANGES REQUIRED

**Verdict: CHANGES REQUIRED** — 2 Minor violations, 1 Warning. No blockers; all are single-line fixes. Per §5 routing rule, flagged here for the implementer.

---

#### Audited files

- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/styles/horizonMap.css`
- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonMap.tsx`
- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonChip.tsx`
- `/Users/jcernauske/code/bright/futureproof-data/docs/mockups/feature-tree-horizon-map.html`

---

## horizonMap.css

### PASS
- All background colors reference `var(--color-bg-*)` tokens (bg-mid, bg-surface, bg-raised). No hardcoded hex backgrounds.
- All accent references use `var(--color-accent-*)` tokens: thrive, info, insight, caution, alert all correct.
- All text colors use `var(--color-text-*)` tokens: primary, secondary, muted, inverse all correct.
- All border colors use `var(--color-border-*)` tokens: subtle, default all correct.
- Font families reference `var(--font-display)`, `var(--font-body)`, `var(--font-data)` with appropriate fallbacks.
- `branchFlashPulse` keyframe: scale `1 → 1.06 → 1`, 600ms, `accent-info` glow at the 42% keyframe, border-color picks up `accent-info` mid-pulse. Matches DESIGN.md §Motion System "Branch Flash" spec and visionary call #5 exactly.
- Reduced-motion fallback present at definition point (80ms opacity blink, no scale, no glow). Compliant with DESIGN.md requirement: "New keyframes must include the reduced-motion override at the point of definition, not in a component."
- Lane-local selection dim (`data-has-selection` on lane, dim siblings only) correctly implements visionary call #1.
- Lane left-edge 3px accent bars: `accent-thrive` / `accent-info` / `accent-insight` per Lateral / Step Up / Long Climb. Correct per visionary call #2 and §3 Brightpath Design References.
- SVG inline icons inherit lane accent color via `currentColor`. Correct — no hardcoded color on icons.
- `data-tier` attribute values (`primary-short`, `primary-long`, `supplemental`) match CSS selectors. Correct.
- `data-selected="true"` selector applies `accent-thrive` ring + glow. Correct per §3.
- `data-level-unknown="true"` selector applies muted dashed treatment. Correct per D#2.

### FAIL

**FAIL 1 — Minor: Three `border-radius` values are hardcoded integers instead of radius tokens.**

- `horizonMap.css` line 151: `.horizon-lane { border-radius: 12px; }` — Expected `var(--radius-lg)` (14px) per DESIGN.md §Border Radii. Mockup uses `var(--radius-lg)` for lanes (`.lane { border-radius: var(--radius-lg); }`).
- `horizonMap.css` line 261: `.horizon-chip { border-radius: 10px; }` — Expected `var(--radius-md)` (10px) per DESIGN.md. Numerically equal but must reference the token. Mockup uses `var(--radius-md)` for chips.
- `horizonMap.css` line 486: `.horizon-chip-more { border-radius: 10px; }` — Same violation as line 261. Mockup uses `var(--radius-md)`.
- `horizonMap.css` line 552: `.horizon-chip-collapse { border-radius: 10px; }` — Same violation. Mockup uses `var(--radius-md)`.

  **Fix:** Replace each hardcoded integer with its token:
  - Line 151: `border-radius: 12px;` → `border-radius: var(--radius-lg);`
  - Lines 261, 486, 552: `border-radius: 10px;` → `border-radius: var(--radius-md);`

  Note: `border-radius: 999px;` on toggle switch (line 102) and `border-radius: 50%;` on circular elements are acceptable — these are geometry, not scale tokens; DESIGN.md does not define a `var(--radius-circle)` convention.

**FAIL 2 — Minor: `.horizon-eyebrow` color is `text-muted` but the mockup specifies `accent-info`.**

- `horizonMap.css` line 47: `color: var(--color-text-muted);` — the eyebrow ("CAREER PATHS") uses text-muted in the implementation.
- Mockup (line 291): `.horizon-eyebrow { color: var(--accent-info); letter-spacing: 0.18em; }` — the binding visual target uses `accent-info`.
- Per §3: "It is the binding visual target for implementation — the implementer should match it pixel-for-pixel where it conflicts with the prose below." The prose does not specify the eyebrow color; the mockup specifies `accent-info`. Mockup wins.

  **Fix:** `horizonMap.css` line 47: `color: var(--color-text-muted);` → `color: var(--color-accent-info);`

### WARNINGS

**WARNING 1 — `.horizon-chip.branch-flash` omits `forwards` fill-mode present in the mockup.**

- `horizonMap.css` line 465: `animation: branchFlashPulse 600ms ease-out;`
- Mockup line 546: `animation: branchFlashPulse 600ms ease-out forwards;`
- The `forwards` fill-mode holds the 100% keyframe after the animation completes. Without it, the chip's border snaps back to `border-subtle` immediately on animation end rather than settling through the final frame. At 600ms this is imperceptible in practice, and the 100% keyframe restores the pre-flash state intentionally — so this may be a deliberate omission (no fill-mode needed when the 100% frame is the resting state). Not a token violation; flagged for implementer review.

**WARNING 2 — Hardcoded `rgba(45, 48, 96, 0.30)` lane background duplicates the `bg-mid` hex without a token.**

- `horizonMap.css` line 149: `background: rgba(45, 48, 96, 0.30);` — `#232545` is `bg-mid` (`var(--color-bg-mid)`), but this is using an inline rgba with a hardcoded opacity rather than an opacity utility. There is no `color-mix` or `rgba(var(--color-bg-mid-rgb), 0.30)` pattern in the token set, so this is not a strict token violation (the design system does not define an alpha-variant of bg-mid). The mockup uses the identical value. Flagged as a warning to document the deliberate deviation, not as a required change.

---

## BranchHorizonMap.tsx

### PASS
- Class names (`horizon-col`, `horizon-header`, `horizon-lane`, `horizon-chip-row`, `horizon-lane-empty`) all map to matching selectors in `horizonMap.css`. No orphaned class names.
- `data-lane` values (`"lateral"`, `"step-up"`, `"long-climb"`) match the CSS selectors `[data-lane="lateral"]`, `[data-lane="step-up"]`, `[data-lane="long-climb"]`. The `LANE_DATA` record bridges camelCase `LaneId` to kebab-case data attributes correctly.
- `data-has-selection` attribute applied on the lane container when a chip within that lane is selected. Lane-local dim is correctly scoped to siblings only (visionary call #1 honored).
- Anchor sub-line (`anchorTag()` function) derives "Bachelor's-anchored" / "Master's-anchored" etc. and renders it via `.horizon-anchor-tag` (font-data, text-muted). Visionary call #4 honored.
- Inline SVG icons: `stroke="currentColor"` — inherits lane accent color from `.horizon-lane-icon` CSS rule. No hardcoded stroke colors.
- Toggle button uses `role="switch"` and `aria-checked`. Matches §3 Accessibility spec.
- `data-testid` values match §3 Accessibility table: `region-branch-horizon`, `lane-header-{lateral|step-up|long-climb}`, `btn-lane-expand-{lateral|step-up|long-climb}`, `toggle-hide-supplemental`, `lane-empty-{lateral|step-up|long-climb}`.

### FAIL
- None beyond what is already captured in the CSS findings above (the token violations manifest in the CSS file, not in the component).

### WARNINGS
- Framer Motion is not used for lane initial reveal (`transitions.fadeInUp`) or chip `whileTap` (`springs.snappy`). The §3 Motion spec lists both. The component uses CSS transitions on `.horizon-chip` for hover, which is correct per DESIGN.md ("For simple hover/focus states" use CSS transitions). However, the lane reveal animation (`transitions.fadeInUp` — `opacity 0 + y:24 → visible, smooth spring`) and `whileTap` press feedback (`springs.snappy`) are not implemented. DESIGN.md §Motion System: "All meaningful animations use Framer Motion spring physics." This is a semantic gap, not a token violation — flagged as a warning because the component renders and functions correctly without it; the missing motion is a fidelity gap against the §3 contract, not a hardcoded-value violation.

---

## BranchHorizonChip.tsx

### PASS
- `data-tier` values (`"primary-short"`, `"primary-long"`, `"supplemental"`) match the CSS `[data-tier]` selectors via `TIER_DATA` record. Schema is correct.
- `data-selected="true"` set when `selected` prop is true. Matches CSS `[data-selected="true"]` selector.
- `data-level-unknown="true"` set when `branch.related_education_level == null`. Matches CSS `[data-level-unknown="true"]` selector. D#2 honored.
- `className` toggles `"branch-flash"` when `flashing` prop is true. Correct — the `branch-flash` CSS class applies the `branchFlashPulse` keyframe.
- Stat-delta badge uses `data-stat` attribute to pick the correct `var(--color-stat-*)` color. No hardcoded stat colors.
- Experience badge uses `data-tier` for mid/senior color switch (caution → alert). Correct tokens.
- Unlock footer text uses `var(--color-text-muted)` via `.horizon-chip-unlock`. Correct.

### FAIL
- None.

### WARNINGS
- `aria-label` is set to `branch.to_title` only (line 59). §3 Accessibility table specifies `aria-label` as `"{branch.to_title}, {lane subtitle}"`. The lane subtitle context is missing from the label — a screen-reader user cannot distinguish which lane a chip is in from the chip's label alone. Not a token violation; flagged for implementer review against the §3 accessibility contract.

---

## Mockup conformance check (binding visual target per §3)

| Element | Mockup | Implementation | Status |
|---|---|---|---|
| `.horizon-col` background | `var(--bp-mid)` + `shadow-md` | `var(--color-bg-mid)` (no shadow-md) | Minor — shadow-md missing on the column shell. Mockup line 213: `box-shadow: var(--shadow-md)`. |
| Lane border-radius | `var(--radius-lg)` | `12px` (hardcoded) | Fail 1 above |
| Chip border-radius | `var(--radius-md)` | `10px` (hardcoded) | Fail 1 above |
| Eyebrow color | `accent-info` | `text-muted` | Fail 2 above |
| `branch-flash` fill-mode | `forwards` | absent | Warning 1 above |
| Lane left-edge bar border-radius | `0 var(--radius-sm) var(--radius-sm) 0` | `0 4px 4px 0` (hardcoded) | Minor — `4px` == `--radius-sm` (6px in DESIGN.md)... wait, DESIGN.md defines `--radius-sm` as 6px not 4px. The mockup uses `var(--radius-sm)` (6px); implementation uses `4px`. Token mismatch. Fix: `border-radius: 0 4px 4px 0` → `border-radius: 0 var(--radius-sm) var(--radius-sm) 0` at `horizonMap.css` line 163. |
| `.horizon-col` `box-shadow` | `var(--shadow-md)` | absent | Minor — add `box-shadow: var(--shadow-md)` to `.horizon-col` rule. |

**Additional finding from mockup diff:**

**FAIL 3 — Minor: `.horizon-lane`'s left-edge accent bar `border-radius` uses hardcoded `0 4px 4px 0` instead of `0 var(--radius-sm) var(--radius-sm) 0`.**

- `horizonMap.css` line 163: `border-radius: 0 4px 4px 0;`
- Mockup line 370: `border-radius: 0 var(--radius-sm) var(--radius-sm) 0;`
- DESIGN.md defines `--radius-sm` = 6px. The implementation uses 4px — a different value, not just a missing token reference.
- **Fix:** `horizonMap.css` line 163: `border-radius: 0 4px 4px 0;` → `border-radius: 0 var(--radius-sm) var(--radius-sm) 0;`

**FAIL 4 — Minor: `.horizon-col` is missing `box-shadow: var(--shadow-md)` present in the mockup.**

- `horizonMap.css` lines 15–25: `.horizon-col` rule has no `box-shadow` property.
- Mockup line 213: `.horizon-col { ... box-shadow: var(--shadow-md); ... }`
- DESIGN.md §Elevation & Shadows: `shadow-md` = "Cards". The column shell is a card-level surface; omitting the shadow flattens it against the page background.
- **Fix:** Add `box-shadow: var(--shadow-md);` to `.horizon-col` rule in `horizonMap.css`.

---

#### Summary of required changes

| # | Severity | File | Line | Issue | Fix |
|---|---|---|---|---|---|
| 1a | Minor | `horizonMap.css` | 151 | `.horizon-lane` border-radius is hardcoded `12px` | → `var(--radius-lg)` |
| 1b | Minor | `horizonMap.css` | 261 | `.horizon-chip` border-radius is hardcoded `10px` | → `var(--radius-md)` |
| 1c | Minor | `horizonMap.css` | 486 | `.horizon-chip-more` border-radius is hardcoded `10px` | → `var(--radius-md)` |
| 1d | Minor | `horizonMap.css` | 552 | `.horizon-chip-collapse` border-radius is hardcoded `10px` | → `var(--radius-md)` |
| 2 | Minor | `horizonMap.css` | 47 | `.horizon-eyebrow` color is `text-muted`; mockup (binding target) specifies `accent-info` | → `var(--color-accent-info)` |
| 3 | Minor | `horizonMap.css` | 163 | Lane accent bar `border-radius` is `0 4px 4px 0`; mockup uses `0 var(--radius-sm) var(--radius-sm) 0` (6px, different value) | → `0 var(--radius-sm) var(--radius-sm) 0` |
| 4 | Minor | `horizonMap.css` | 15–25 | `.horizon-col` missing `box-shadow: var(--shadow-md)` present in binding mockup | Add `box-shadow: var(--shadow-md);` |

All 4 findings are Minor. All are in a single file (`horizonMap.css`). No Blocker or Significant findings. No `BranchHorizonMap.tsx` or `BranchHorizonChip.tsx` changes required.

Routed to implementer per §5 / §10.

### Code Review (@faang-staff-engineer)
**Status:** APPROVED — 2026-04-29
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary
Look, I love Claude, BUT — I went into this expecting to find at least one 3am-page-waiting-to-happen, and instead I'm sitting here grudgingly impressed. The lane-assignment math is clean, the null fallbacks are encoded exactly where the spec says they should be, the "+N more" + hide-supplemental interaction holds together, and the chip-id schema flip from React Flow ids to `chip-${to_soc}` is consistent across `chipBranchMap`, `highlightCandidates`, and the `BranchHorizonMap` selection check. No security holes, no perf time bombs, no race conditions. The four findings below are all Minor — UX inconsistencies and a tiny perf nit. None gate ship.

This is great AI-generated code. It just needed... supervision. (Got it.) Approved.

#### Audited files
- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/data/horizonLayout.ts`
- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonMap.tsx`
- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/tree/BranchHorizonChip.tsx`
- `/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/BranchTreeScreen.tsx`

#### Focus-area verification (per Claude Code Prompt §6)

1. **Lane-assignment correctness on the long tail of `related_education_level` values.** ✅ PASS. `EDU_RANK` covers all 8 documented strings with `"No formal educational credential"`, `"Postsecondary nondegree award"`, and `"Some college, no degree"` all keyed to `1` — no double-assignment, no overlap with rank=0 (HS) or rank=2 (AA). Verified against the silver-zone source of truth at `src/silver/bls_ooh_transformer.py:61-70`. The bucket boundaries (`delta ≤ 0` → Lateral, `delta == 1` → Step Up, `delta ≥ 2` → Long Climb) match §1 success criteria and §2 D#1 verbatim. Negative deltas (advanced-degree builds looking at lower-edu branches) collapse to Lateral as specified — no off-by-one.

2. **`education_level_name` null fallback.** ✅ PASS. `assignLane`: `branchEdu == null` returns `"lateral"` early (D#2 — chip then carries `data-level-unknown="true"` via `BranchHorizonChip` line 41-42, 56). Build edu null falls through to `BUILD_EDU_FALLBACK_RANK = 3` via the `??` operator on line 81, encoding D#3. Both encoded exactly where the spec said they should be.

3. **"Hide supplemental" + cap-at-6 + "+N more" math.** ✅ PASS. `bucketBranches` filters BEFORE bucketing (line 108-110), and `totalBeforeCap` = `sorted.length` is the post-filter count (line 129). When the toggle flips on mid-render and overflow disappears, `lane.totalBeforeCap - lane.branches.length` correctly resolves to 0 and the `!isExpanded && overflowCount > 0` guard suppresses the "+N more" button. The `expandedLanes` recomputes via the `Number.MAX_SAFE_INTEGER` cap so all rows surface inside an expanded lane regardless of filter state. See Finding 1 below for a related UX wart.

4. **`BranchHighlightDriver` candidate-set keying on chip ids.** ✅ PASS. `highlightCandidates` (BranchTreeScreen.tsx:144-150) emits `{ id: \`chip-${branch.to_soc}\`, title: branch.to_title }` over `build.branches` — uniform L1-only schema. Driver is id-agnostic (verified at `BranchHighlightDriver.tsx:42-50` — it just returns whatever ids the parent supplies). The matching `chip-${to_soc}` consumed by `BranchHorizonMap.tsx:144` (selection check) and `BranchHorizonMap.tsx:210, 216` (flashing check) all align. No id-shape drift across the four sites that changed.

5. **`chipBranchMap` derivation source.** ✅ PASS. Sourced off `build.branches` at line 134 — NOT `treeData.tree.children`, as D#16 mandates. All four downstream consumers (`selectedSocCode` line 179, `chipText` line 204, `skeletonHint` line 223, and the `BranchHorizonMap` chip click round-trip) read through `chipBranchMap.get(...)`. The fourth consumer the prompt mentions (the deleted `selectedNode`) is gone, and `grep` confirms zero leftover references in the screen file.

#### Findings

##### Finding 1 — Minor 🔵: Selecting a chip then hiding supplementals leaves the chat anchored to a now-invisible scope.
**Impact:** UX inconsistency, not a correctness bug. Click a Supplemental chip → chat header reads `branch · {Title}` and Gemma is anchored on that SOC. Toggle "Hide supplemental" on → the chip vanishes from the lane but `selectedNodeId` retains its value, `chipBranchMap.get(selectedNodeId)` still resolves (the map isn't filter-aware), and the chat keeps streaming about a branch with no visible host. User can't deselect because there's no chip to click.
**Location:** `frontend/src/components/tree/BranchHorizonMap.tsx:110, 113-116` and `frontend/src/screens/BranchTreeScreen.tsx:131-138`.
**The Problem:** `chipBranchMap` is built from the unfiltered `build.branches`, but the visible lanes use `bucketBranches(branches, buildEduLevel, hideSupplemental, ...)`. The two diverge under the filter, leaving a "selected scope without a selected chip" state. Same shape applies if the user selects a chip in an expanded lane, then collapses the lane — the selected chip lives in the now-hidden tail and no `data-selected` mark is visible.
**The Fix:** When `hideSupplemental` flips on, drop the selection if the currently-selected branch is Supplemental tier. Equivalent guard for collapse. Roughly:
```typescript
useEffect(() => {
  if (!hideSupplemental || !selectedNodeId) return;
  const sel = chipBranchMap.get(selectedNodeId);
  if (sel && relatednessTier(sel.relatedness) === "Supplemental") {
    onSelectNode(null);
  }
}, [hideSupplemental, selectedNodeId, chipBranchMap, onSelectNode]);
```
This lives more naturally in `BranchTreeScreen.tsx` where `selectedNodeId` is owned. Acceptable to ship without the fix and address in a follow-up; flag for a 2-line patch when convenient.

##### Finding 2 — Minor 🔵: Stale "Show fewer" collapse button persists when filter eliminates overflow on an expanded lane.
**Impact:** Cosmetic. User expands Lateral (21 chips), toggles Hide Supplemental on, lane collapses to 4 chips post-filter. The lane stays in `expanded` state, so the "Show fewer" collapse button keeps rendering even though there's no overflow to hide. Clicking it re-collapses to a capped view that's already short of the cap — no-op for the user.
**Location:** `frontend/src/components/tree/BranchHorizonMap.tsx:241-251` (`isExpanded && (... collapse button ...)`).
**The Problem:** The `expanded` Set is independent of the actual overflow state. After filter changes, lanes can be marked expanded with nothing to expand.
**The Fix:** Gate the collapse button on actual overflow existing in the unfiltered (within-current-filter) state:
```typescript
{isExpanded && lane.totalBeforeCap > lane.branches.length && (
  <button ...>Show fewer</button>
)}
```
Or proactively prune `expanded` inside a `useEffect` when `hideSupplemental` flips. Same severity as Finding 1.

##### Finding 3 — Minor 🔵: `chipBranchMap` and `highlightCandidates` `useMemo` deps key off the entire `build` object.
**Impact:** Tiny perf nit. Re-runs the Map build every time anything else on the build changes (`build.skills_crafted` mutations from a parallel `/skills` flow, `build.gauntlet` after a fight, etc.). With ≤ 22 L1 branches per build the work is trivial, but it's a strictly-larger dep set than the function reads.
**Location:** `frontend/src/screens/BranchTreeScreen.tsx:138, 150`.
**The Fix:**
```typescript
const chipBranchMap = useMemo(() => { ... }, [build?.branches]);
const highlightCandidates = useMemo(() => { ... }, [build?.branches]);
```
Optional. Not blocking. I'm flagging it because the next person who adds a build mutation will silently rebuild these maps.

##### Finding 4 — Minor 🔵: `expandedLanes` recomputes on `expanded.size` changes for a result that doesn't depend on the value of `expanded`.
**Impact:** Same family as Finding 3 — micro-perf. The `expandedLanes` memo computes the same uncapped 3-lane structure for any non-zero `expanded.size`. Using `expanded.size` as a dep means toggling between two different lanes' expanded state (size flips 1→2→1) recomputes the same buckets twice for no reason.
**Location:** `frontend/src/components/tree/BranchHorizonMap.tsx:120-125`.
**The Fix:** Either compute `expandedLanes` unconditionally (it's not hot-path) and drop the `expanded.size` dep, or use a boolean `anyExpanded`:
```typescript
const anyExpanded = expanded.size > 0;
const expandedLanes = useMemo(
  () => (anyExpanded ? bucketBranches(branches, buildEduLevel, hideSupplemental, { laneCap: Number.MAX_SAFE_INTEGER }) : null),
  [branches, buildEduLevel, hideSupplemental, anyExpanded],
);
```
Optional. Same reason as Finding 3 — flag it before someone trips over it.

#### What's Actually Good (grudgingly)
- **Pure-function module is genuinely pure.** `horizonLayout.ts` has zero React, zero DOM, zero I/O. `sortBranchesInLane` even uses `[...branches].sort(...)` to avoid mutating input — explicitly tested. That's the hygiene I'd expect from someone who's been bitten by in-place sort once.
- **Null-safety is consistent.** `eduRank(null) → null`, `relatednessTier(null) → null`, `assignLane(branchEdu=null) → "lateral"` — the four-stage null-handling chain (eduRank → assignLane fallback → tier → sort) all returns to a defined behavior without crashing.
- **`dominantStatDelta` correctly excludes `delta_roi`** per the spec's "ern/grw/hmn/res only" constraint, with a test guarding the exclusion. Easy thing to drift on; didn't.
- **Zero leftover dead state.** I went hunting for `selectedNode`/`rootNode`/`detailDrawerOpen`/`flowResult`/`treeToFlow`/`computeLayout` in `BranchTreeScreen.tsx` — all gone except for one comment reference. Refactor was done all the way through.
- **No XSS surface.** `to_title` flows through React text content, `aria-label`, and `title` — all auto-escaped. No `dangerouslySetInnerHTML`. Safe even if a future spec lets users edit branch titles.
- **The `truncateTitle` word-boundary heuristic** (cuts at last space if it's past the half-mark) is the kind of small thing AI normally over-engineers or under-engineers. This one's right.
- **The §6 deviation note is honest.** Implementer extended the module with `dominantStatDelta` + `truncateTitle` and called it out explicitly in §6 instead of pretending the spec said so. Documentation hygiene I respect.

#### Questions for the Author
- **Finding 1's UX scenario:** is the chat-anchored-to-invisible-scope considered acceptable for the demo, or should the deselect-on-filter patch land before ship? Either is defensible — I'd lean "fix it" because it's 6 lines, but it's not a blocker.
- **`relatedness == 0`:** the silver-zone source treats `best_index` as a 1-N rank, so 0 shouldn't appear. Confirmed at `backend/app/services/branch_tree.py:95`. Defensive call: if a future pipeline change ever produces `relatedness = 0`, `relatednessTier(0)` returns `"Primary-Short"` (since `0 <= 5`), which is the right behavior. Just naming the assumption.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

Ship it. The four Minor findings can land as a follow-up patch; none of them gates the demo or causes data loss / outages / security issues. The CEO said use AI; this is the kind of output where I have to admit I'd have probably done it differently but not better. Just differently.

---

## §9 Verification

**Status:** GREEN
**Verified:** 2026-04-29 12:40

### Backend (@fp-builder)
| Check | Result | Details |
|---|---|---|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | PASS (pre-existing failures, not caused by this spec) | 71 pre-existing errors in 20 files — zero backend changes on this branch (git diff main...HEAD -- backend/ is empty; this is a frontend-only spec per §2 Constraint "Frontend-only"). Errors exist on main and are not regressions. |
| Tests (pytest) | PASS | 1232 passed, 0 failed, 152 warnings |

### Frontend (@fp-builder)
| Check | Result | Details |
|---|---|---|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 748 passed, 11 pre-existing failures per §4 (9 CompareView.test.tsx + 2 PentagonOverlay.test.tsx — no new regressions) |
| Production build (Vite) | PASS | Build completed — 540 modules, dist/assets/index-C7yXJPQh.js 741.46 kB |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---|---|---|---|
| 1 | All checks passed (modulo 11 documented pre-existing frontend failures) | — | — |

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

```
[2026-04-29] @fp-architect CHANGES REQUESTED → resolved (Jeff approved)

Architect raised 5 conditions on the initial draft (§5 Findings). All five
resolved by spec edits — none required backend, schema, or pipeline rework.

  1. flowNodeMap removal cascade → resolved by Decision #14 (chipBranchMap).
     §4 now shows the patched derivations for selectedSocCode, chipText,
     skeletonHint, highlightCandidates inline. Picked chipBranchMap over
     prefix-strip because it preserves the cached-lookup pattern; minimum
     diff to today's BranchTreeScreen.tsx.

  2. TreeNodeDetailPanel fate → resolved by Decision #13 (drop entirely).
     Reverses feature-tree-as-map.md D#3 ("demote, don't remove"). Rationale:
     the chip already surfaces the CareerBranch fields the destination row
     carries; the drawer's PositionedNode contract (stats/bosses/median_wage/
     education) doesn't map to CareerBranch; chat is the deeper-data path now
     (get_occupation_data MCP tool). Mockup's closed-state pill is treated
     as a copy-paste leftover, not binding.

  3. + 4. treeFlowLayout.ts / Flow*Node.tsx / reactflow-dark.css fate →
     resolved by Decision #15 (delete outright). Verified zero remaining
     consumers post BranchTreeFlow.tsx deletion. The treeLayout.ts family
     (SVG-era BranchTreeSVG.tsx + Tree*Node.tsx + treeLayout.test.ts) is
     OUT OF SCOPE — separate dead-code question.

  5. L2/L3 title flashes acknowledged → resolved by new §2 Out-of-Scope
     bullet. The candidate set narrows from N₁+N₂+N₃ to N₁; Gemma quoting
     a sub-specialization or terminal credential will not flash any chip.
     Net: fewer flashes, never wrong flashes. Future spec
     feature-horizon-flash-aliasing.md (TBD) can alias L2/L3 → parent L1
     in ~30 lines if demo dry-run shows pathological "Gemma names sub-roles,
     nothing flashes" patterns.

Architect to re-review with these resolutions encoded; expected verdict
APPROVED per the architect's own line 600 ("After these five edits land in
the spec, this review flips to APPROVED without further architecture review").
```

```
[2026-04-29] Implementation-time spec corrections (D#16, D#17)

While grounding code against the actual types and backend models, three
field-semantic mismatches surfaced between the spec and the API contract:

  1. Data source. The spec referenced ``treeData.tree.children`` as the
     chip data source, but ``TreeNode`` carries the wrong shape (abs
     ern/roi/median_wage/boss_*, no deltas). The CareerBranch shape the
     chips need lives on ``build.branches`` — same L1 destination set,
     different fields. Codified as Decision #16: ``build.branches`` is
     the canonical source; ``getTree()`` is still called for the
     empty-children fallback path.

  2. ``relatedness_tier`` field doesn't exist on the API contract. The
     silver zone derives it from ``best_index`` via derive_relatedness_tier
     and folds it into the ``unlock`` display string in _format_unlock,
     but never surfaces it as a structured field. Pydantic's
     CareerBranch.relatedness is ``best_index`` (an integer rank, despite
     the float type annotation). Codified as Decision #17: re-derive
     ``relatednessTier`` in horizonLayout.ts using the same <=5 / <=10
     bands as the silver-zone rule. The string "no backend changes" wins.

  3. ``related_experience_tier`` is the silver-zone column name; the API
     contract surfaces it as plain ``experience_tier`` on CareerBranch.
     Mechanical rename across §1, §2 D#4, §3 Q#8, §3 Interactions, §4
     BranchHorizonChip props row, and §4 New Tests Required.

  Side correction: ``relatedness`` is ``best_index`` where 1 = most
  related, so the within-lane tiebreak sort is ASC (most-related first),
  not DESC. The §1 success criterion phrasing was a holdover from the
  original spec author treating ``relatedness`` as a similarity score.
  Fixed in §1 + §2 D#5 + the inline horizonLayout.ts code; comment in
  the sort function explains the inversion.

Net effect on architecture: zero. None of these reach the backend, the
schema, or the Gemma surface — they are all corrections to where the
frontend reads existing fields. The architect's APPROVED verdict still
holds; the implementation just got cleaner.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]
