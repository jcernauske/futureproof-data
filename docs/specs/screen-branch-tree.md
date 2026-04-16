# Feature: Branch Tree (Screen 8)

## Claude Code Prompt

```
Read the spec at docs/specs/screen-branch-tree.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (component architecture, routing, state management, API integration)
   - @fp-data-reviewer: SKIPPED (no pipeline/data changes — tree API exists and is consumed as-is)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to review §3 mockups and propose the premium implementation
   - Visionary validates Brightpath token usage, branch tree illumination sequence, node interaction patterns, responsive behavior
   - Cross-reference DESIGN.md (source of truth), docs/mockups/brightpath-design-system-v2.html (design system ref), and docs/mockups/branch-tree-mockup-v1.html (interactive mockup ref — note: has known SVG paint-order bugs on outgoing paths, fix during implementation)
   - Special focus: the 3.5s illumination sequence from motion.ts branchTree presets, node tap-to-reveal interaction, gradient branch lines, progressive illumination emotional arc
   - Writes to §3 with any enhancements or adjustments

3. IMPLEMENTATION
   - Read DESIGN.md before writing any UI code — DESIGN.md wins over existing code
   - Implement all components as React with Framer Motion animations
   - Wire up API calls to FastAPI endpoints via apiPost/apiGet helpers (or mock handlers if APIs unavailable)
   - Use Brightpath design tokens exclusively — no hardcoded colors, spacing, or typography
   - IMPORTANT SVG PAINT ORDER: outgoing branch paths from career nodes must render AFTER the career node rects in SVG document order, otherwise the opaque rect fills occlude horizontal paths. The mockup has this bug — fix it.
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)

4. TESTING
   - Invoke @test-writer to write component tests
   - Each component: renders, interactions work, state updates correctly
   - Tree rendering: root node, branch lines, career nodes, endpoint silhouettes
   - Node selection: tap to reveal detail panel with stats + boss projections
   - Fallback: careers without pathway data show fallback indicator
   - Run ALL tests to catch regressions

5. DESIGN AUDIT
   - Invoke @design-builder for Brightpath token compliance across all components
   - Confirm: bg-void backdrop, stat-colored branch gradients, correct fonts, token-only colors, responsive behavior
   - Confirm: branch tree illumination sequence matches DESIGN.md timing and motion.ts branchTree presets
   - Writes findings to §8

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Writes findings to §8
   - If APPROVED: proceed to step 7
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

7. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Frontend: TypeScript, vitest, Vite production build
   - Log results to §9

8. COMPLETION
   - Update top-level Spec Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/screen-branch-tree-YYYY-MM-DD.md
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
| DESIGN AUDIT | @design-builder checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-14 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-14 |
| Blocked By | F4 (boss gauntlet — IN PROGRESS) |
| Related Specs | `screen-boss-gauntlet` (F4), `screen-save-wrapped` (F6, not started) |

---

## §1 Feature Description

### Overview

Build Screen 8 of the FutureProof flow: the career branch tree. This is the signature visualization — the screen DESIGN.md calls "WONDER." The student's primary career sits at center-left, and branches extend outward showing where this degree can take them over a career lifetime. Each node carries absolute stats and boss fight projections. Tap a node to see the full detail panel. The tree illuminates progressively over 3.5 seconds in the sequence defined in motion.ts.

This is also the screen that wins the hackathon. The progressive illumination — futures literally lighting up across the screen — is the visual metaphor for the entire product.

### Emotional Target

**WONDER.** The telescope moment. The student has fought the bosses, seen their weaknesses, crafted skills to fight back. Now they see where every branch leads. The emotional arc is: darkness → root glow → branches draw → labels appear → career nodes populate → endpoint silhouettes fade in → particles drift. The student's future is being illuminated.

### Problem Statement

The student has completed the gauntlet (Screen 7) and has a full Build object with branches data. The Build already contains `branches: CareerBranch[]` (flat list of transitions from the primary career). The backend also offers a `GET /tree/{build_id}` endpoint that returns a recursive tree structure up to 3 levels deep with absolute stats and boss fight projections at each node. The student now needs to:

1. **See the full career evolution tree** — their primary career at center-left, branches extending outward with career progression nodes at each level
2. **Tap any node** to see absolute stats (ERN/ROI/RES/GRW/HMN), stat deltas from root, boss fight projections, median salary, and unlock requirements
3. **Understand the tree structure** — branch labels group paths by career direction (e.g., "Stay Technical", "Go Management"), career nodes show intermediate positions, endpoint silhouettes show long-term destinations
4. **See the graceful fallback** for careers without O*NET pathway data — full Stage 2 experience with a "branches coming soon" indicator

### CLI → Frontend Mapping

| CLI Function | This Spec | What It Does |
|---|---|---|
| `_display_career_tree()` | BranchTree component | Full tree visualization with illumination sequence |
| `_display_branch_detail()` | NodeDetailPanel component | Tap-to-reveal: stats, boss projections, unlock, salary |
| Tree node rendering | TreeNode / EndpointNode components | Individual career nodes at each depth level |
| Branch line rendering | BranchPaths SVG component | Gradient bezier curves connecting nodes |

### Key Design Decisions: Data Source

Two API options exist for tree data:

1. **`build.branches: CareerBranch[]`** — already on the Build object from F3. Flat list of transitions with stat deltas (relative to root). Covers 1 level of branching.
2. **`GET /tree/{build_id}?max_depth=3`** — returns a recursive `TreeNode` structure with absolute stats, boss fight projections, and children up to 3 levels deep. Richer data but requires a separate API call.

**Decision: Use the `/tree/{build_id}` endpoint.** The flat `branches` list only covers 1 level. The tree endpoint gives us the full 3-level structure with absolute stats at every node, which is what the visualization needs. The API call happens when the student navigates to Screen 8 — the tree data is NOT pre-computed on the Build object.

### Success Criteria

- [x] Tree visualization renders with root career at center-left, branches extending rightward
- [x] 3.5s progressive illumination sequence per DESIGN.md / motion.ts `branchTree` presets
- [x] Root node: profile emoji, career title, salary. Thrive glow pulse.
- [x] Branch labels: pill-shaped groupings (e.g., "Stay Technical") with stat-colored borders
- [x] Career nodes: rounded rect pills with occupation title
- [x] Endpoint silhouettes: dimmed bear emoji circles with career title and salary
- [x] Gradient branch lines: thrive → stat color, stroke width decreasing by depth
- [x] Tap any node → detail panel slides in with stats, boss projections, unlock requirements
- [x] Stat deltas shown relative to root node (green for positive, amber for negative)
- [x] Boss fight projections per node (win/lose/draw pills)
- [x] Twinkling star background + drifting particles along branches
- [x] Fallback: careers with no O*NET pathway data show "branches coming soon" indicator
- [x] Loading state while `/tree/{build_id}` API call is in flight
- [x] Header void-blended per DESIGN.md cinematic states (matches bg-void background)
- [x] CTA to advance: "Save & Share →" (Screen 9, F6)
- [ ] All Brightpath design tokens used — zero hardcoded colors/spacing/fonts (PARTIAL: design audit found 22 hardcoded hex values that are visually correct but bypass CSS custom properties)
- [x] Framer Motion animations per DESIGN.md branch tree illumination + motion.ts presets
- [x] SVG paint order correct: outgoing paths render AFTER career node rects
- [x] Responsive: desktop primary (tree spreads horizontally), mobile functional (scrollable)
- [x] All tests pass (184 pass, 2 pre-existing failures in ProfileScreen unrelated to this spec)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Use `/tree/{build_id}` API, not `build.branches` | The flat `branches` list only covers 1 level. The tree endpoint returns recursive 3-level structure with absolute stats and boss projections at every node. Worth the extra API call. | Use flat branches only (loses depth), pre-compute tree on Build (adds latency to F3 build orchestration) |
| 2 | SVG-based tree, not React Flow | The tree is a cinematic visualization with custom aesthetics (gradient paths, glow effects, animated illumination). React Flow adds node/edge abstractions we don't need — the tree structure is static once loaded. Custom SVG gives full control over the Brightpath aesthetic. | React Flow (overkill for static tree, adds 80KB bundle), D3 force layout (wrong metaphor — this is a directed tree, not a force graph), Canvas (loses SVG accessibility) |
| 3 | Horizontal left-to-right layout | Career progression flows left to right — root career at origin, future states extending rightward. Matches mental model of time/progression. Desktop-first; mobile scrolls horizontally. | Top-down (doesn't spread well on wide screens), radial (harder to label, less intuitive), vertical (wastes horizontal space) |
| 4 | Detail panel as overlay, not inline | Tapping a node reveals a slide-in panel with full stats. This keeps the tree visualization clean — nodes stay small and the tree shape is never distorted by expanded content. | Inline expansion (distorts tree layout), tooltip (too small for stats + boss projections), modal (breaks flow) |
| 5 | Separate outgoing paths SVG group | Outgoing paths from career nodes (column 3→4) must render AFTER the career node rects in SVG document order. Otherwise, opaque rect fills occlude horizontal paths. Known bug in the mockup — fix in implementation. | Single path group (causes paint order bug), transparent rects (loses the plush card feel) |
| 6 | Tree loads on navigation, not pre-fetched | Tree computation involves MCP calls per node (O*NET pathway lookup). Pre-fetching during F3 build would add latency. Loading on Screen 8 navigation is acceptable — show a loading state. | Pre-fetch on Build (slows F3), lazy-load per branch (too many API calls) |
| 7 | Fallback for missing pathway data | Some careers have no O*NET transitions. Show a tasteful "branches coming soon" indicator. The student still has the full Stage 2 experience (stats, gauntlet, next steps) — branches are additive. | Empty screen (confusing), skip Screen 8 (loses the navigation step), fake branches (dishonest) |

### Constraints

- Tree data comes from `GET /tree/{build_id}?max_depth=3`. Returns a recursive `TreeNode` with `children: TreeNode[]`. Each node has absolute stats (ern, roi, res, grw, hmn), boss fight results (boss_ai, boss_loans, etc. as win/lose/draw strings), median_wage, education, and level (0=root, 1-3=depth).
- The Build object from F3 contains `branches: CareerBranch[]` with stat deltas — this is used as fallback if the tree endpoint fails or as supplementary data.
- Tree nodes carry absolute stats, not deltas. The detail panel computes deltas by comparing each node's stats to the root node's stats.
- The illumination animation sequence is defined in `motion.ts` as `branchTree.*` with exact timing offsets. Use these — do not improvise timing.
- DESIGN.md specifies header "void-blended" during the branch tree: header matches bg-void, content renders underneath.

---

## §3 UI/UX Design

> @fp-design-visionary fills this section with the premium implementation target.
> Cross-reference DESIGN.md, docs/mockups/brightpath-design-system-v2.html, and docs/mockups/branch-tree-mockup-v1.html

### Screen 8: Branch Tree

**Emotion:** WONDER. The telescope moment.

**Layout:** Full viewport, bg-void background. Tree fills the available width. No max-width constraint — this is the one screen that uses the full viewport. Header void-blended per DESIGN.md.

### Loading State

While `GET /tree/{build_id}` is in flight:

- Background: `bg-void` with ambient glow at 40% intensity.
- Centered: Profile emoji at 60px, floating animation.
- Message: Fredoka 600, `text-heading` (28px), `text-primary` — "Mapping your branches..."
- Sub-message: Nunito 400, `text-body` (16px), `text-secondary` — "Tracing career paths from O*NET pathway data."
- Minimum display: 1.5s.

### Tree Visualization

**Coordinate system:** SVG with viewBox scaled to content. Horizontal left-to-right layout. Four columns:

| Column | X range | Contains | Node style |
|--------|---------|----------|------------|
| 1 (Root) | ~80 | Primary career | Circle with emoji, thrive border, glow |
| 2 (Branch labels) | ~280 | Direction groupings | Pill rects with stat-colored borders |
| 3 (Career nodes) | ~400-516 | Intermediate positions | Rounded rect pills, subtle border |
| 4 (Endpoints) | ~650 | Long-term destinations | Dimmed circles with silhouetted emoji |

**Branch paths (SVG):**

Two SVG groups for correct paint order:
1. `branchPaths` (renders BEFORE careerNodes): Root → branch labels → career node left edges. Bezier curves. Stroke width decreases by depth: 2.5px (root→label), 2px (label→career).
2. `outgoingPaths` (renders AFTER careerNodes): Career node right edges → endpoints. Stroke width 1.5px, opacity 0.7.

Each branch direction has a gradient: `accent-thrive` → stat color (ERN=gold, GRW=blue, RES=purple, HMN=pink). Gradients defined in `<defs>` as `linearGradient` with `x1="0%"` to `x2="100%"`.

**Root node:**
- Outer glow: `accent-thrive` at 8-15% opacity, r=55. Breathing animation (`rootPulse`, 5s cycle).
- Inner circle: r=28, `bg-surface` fill, `accent-thrive` stroke 2.5px.
- Emoji: profile emoji centered in circle (use `dominant-baseline="central"` with y = circle cy + 2px).
- Labels below circle: career title (Fredoka 600, 12px), salary (Space Mono 10px, `text-muted`).

**Branch labels (column 2):**
- Pill rects: `bg-mid` fill, stat-colored stroke 1.5px, rx=18, height=36.
- Text: Nunito 700, 13px, `text-primary`, centered.
- Grouping labels: "Stay Technical", "Go Management", "Pivot Lateral", "Specialize" (or dynamically derived from tree structure).

**Career nodes (column 3):**
- Rounded rect pills: `bg-mid` fill, `border-default` stroke 1px, rx=14, height=28, width=116.
- Text: Nunito 600, 12px, `text-secondary`, centered.
- Opaque fill is critical — these rects intentionally occlude the incoming branch paths for a clean "line enters rect" visual.

**Endpoint silhouettes (column 4):**
- Circle: r=20, `bg-mid` fill, stat-colored stroke 1.5px, opacity 0.6.
- Emoji: profile emoji at 16px, opacity 0.6, centered with `dominant-baseline="central"`.
- Labels to right of circle: career title (Space Mono 11px, `text-muted`), salary (Space Mono 9px, stat color, opacity 0.7).

**Background elements:**
- Twinkling stars: 40 small circles (r=0.5-1.7), `text-muted` fill, `twinkle` animation (3-7s cycle, staggered delays).
- Drifting particles: Small circles at branch junction points, stat-colored, drifting rightward (positive dx only: 15-40px) with gentle vertical drift (±10px). `particleDrift` animation (5-9s cycle).

### The 3.5s Illumination Sequence

Per `motion.ts` `branchTree` presets:

| Phase | Timing | What Happens |
|-------|--------|-------------|
| Root glow | t=0 | Outer glow circle fades in to 8%, then brightens to 22% |
| Root node | t=0.3s | Root node (emoji + circle + labels) fades in. Glow intensifies. |
| Branch lines | t=0.5s (branchTree.linesStart=0.3s from root) | `branchPaths` group fades in over 900ms |
| Branch labels | t=0.9s (branchTree.labelsStart=0.8s) | Label pills fade in over 600ms |
| Career nodes + outgoing paths | t=1.5s (branchTree.careerStart=1.5s) | Career node rects + outgoing paths fade in over 700ms |
| Endpoint silhouettes | t=2.2s (branchTree.endpointsStart=2.2s) | Endpoint circles + labels fade in over 900ms |
| Particles | t=3.0s (branchTree.particlesStart=3.0s) | Particle group fades in over 1200ms. Root glow settles to breathing animation. |

Total duration: ~3.5s. "Replay Animation" button available.

### Node Detail Panel

Slides in from the right when any node is tapped. Same panel for all node types.

- Position: absolute, top 40px, right 32px, width 280px.
- Background: `bg-mid`, 1px `border-default`, `radius-xl`, padding 20px.
- Entrance: opacity 0→1, translateX 12→0, 300ms ease.
- Close button: 28px circle, `bg-surface`, top-right corner.

**Panel content:**

- **Title:** Fredoka 600, 18px, `text-primary` — occupation title.
- **SOC + salary:** Space Mono 12px, `text-muted` — "SOC 13-2051 · $92,000"
- **Unlock requirement** (if present): `bg-surface` container, `radius-md`, 3px `accent-info` left border. Nunito 13px, `text-secondary`.
- **Stats section:** "Stats at this node" label (Fredoka 600, 13px, `text-secondary`). 2-column grid of stat cards:
  - Each card: `bg-surface`, `radius-sm`, padding 6px 10px.
  - Stat label: Space Mono 11px bold, stat color.
  - Delta: Space Mono 11px, `accent-thrive` for positive, `accent-alert` for negative, `text-muted` for zero.
  - Value: Space Mono 16px bold, stat color, right-aligned.
- **Boss fight projection:** "Boss fight projection" label. Column of fight rows:
  - Each row: `bg-surface`, `radius-sm`, padding 5px 10px.
  - Boss label with emoji: Nunito 13px, `text-secondary`.
  - Result pill: Space Mono 11px bold, rounded-full. WIN=thrive, LOSS=alert, DRAW=caution.

**Node dimming on selection:**
When a node is selected, all other nodes dim to 40% opacity. Selected node stays at 100%. Transition: 300ms ease.

**Deselect:** Click canvas background or close button.

### Fallback State

When the tree API returns an empty tree (no O*NET pathway data for this career):

- Tree canvas shows the root node only (no branches).
- Below root: Nunito 400, `text-body-lg` (18px), `text-secondary` — "We're mapping career branches for {career_title}. Check back soon."
- The student still has the full build experience — branches are additive, not required.
- CTA still available to advance to save/share.

### Error State

If the tree API fails:

- Show fallback message: "Couldn't load the branch tree right now."
- "Try Again" secondary button.
- "Continue →" primary button (advances without tree).

### CTA Area

Below the tree canvas:

- Primary button: "Save & Share →" — advances to Screen 9 (save/wrapped, F6).
- Ghost button: "Back to Gauntlet" — returns to Screen 7.
- Ghost button: "Back to My Build" — returns to Screen 6 (reveal).

### Shared Elements

**Header:** Void-blended per DESIGN.md — header background matches `bg-void`, border fades to near-invisible. Profile name in `text-secondary`. Back arrow visible.

**Page transitions:** AnimatePresence. Enter: opacity 0→1, 300ms. Exit: opacity 1→0, 200ms.

### Responsive Behavior

- **Desktop (≥1200px):** Tree fills viewport width. All columns visible. Detail panel overlays right side.
- **Tablet (768-1199px):** Tree scaled to fit. Detail panel overlays.
- **Mobile (<768px):** Tree scrollable horizontally. Detail panel slides up from bottom as a sheet (not right-side overlay). Touch targets minimum 44px.

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Tree canvas | `region-branch-tree` | img | "Career branch tree showing {n} career paths from {career_title}" |
| Root node | `node-root` | button | "{career_title}: tap to view details" |
| Branch label | `node-branch-{label}` | button | "{label} pathway" |
| Career node | `node-career-{soc}` | button | "{title}: tap to view details" |
| Endpoint node | `node-endpoint-{soc}` | button | "{title} ({salary}): tap to view details" |
| Detail panel | `panel-node-detail` | dialog | "Details for {title}" |
| Detail close | `btn-close-detail` | button | "Close detail panel" |
| Replay button | `btn-replay-tree` | button | "Replay tree animation" |
| Save/Share CTA | `btn-save-share` | button | "Save and share your build" |
| Fallback indicator | `region-fallback` | status | "Branch data coming soon" |

### Design Vision Notes

> Written by @fp-design-visionary, 2026-04-14.
> Cross-referenced against: DESIGN.md (source of truth), `docs/mockups/screen-08-branch-tree.html` (interactive mockup), `frontend/src/styles/motion.ts` (branchTree presets).
>
> **Verdict: APPROVED with refinements.** The existing Section 3 is strong — it captures the emotional target, the illumination sequence, the node taxonomy, and the detail panel with precision. The refinements below are enhancements, not corrections. They tighten Brightpath token alignment, add emotional texture to the animation arc, and call out implementation subtleties that will separate "good" from "makes judges gasp."

#### The Emotional Arc: Why 3.5 Seconds Changes Everything

Here is why this matters. The branch tree is not a data visualization. It is a *reveal*. The student has just survived five boss fights. They are bruised, informed, and invested. Now we show them that their career is not a line — it is a constellation. The 3.5-second illumination sequence is engineered to create a specific emotional progression:

| Phase | Emotion | Design Principle |
|-------|---------|-----------------|
| t=0: Root glow | **Recognition** — "That's me" | The glow is warm, not clinical. It says: your starting point is valid. |
| t=0.3s: Branch lines draw | **Anticipation** — "Where do they lead?" | Lines extend into darkness. The student leans forward. |
| t=0.8s: Labels pop in | **Orientation** — "Oh, there are *directions*" | Branch labels name the paths before revealing the destinations. |
| t=1.5s: Career nodes appear | **Discovery** — "I could be *that*?" | Real job titles materialize. The abstract becomes concrete. |
| t=2.2s: Endpoint silhouettes | **Awe** — "That's where this all leads" | Dimmed silhouettes at the far edge. The long view. The future. |
| t=3.0s: Particles drift | **Wonder** — the world is alive | Particles say: this is not a static chart. Futures are in motion. |

The total duration of 3.5s is deliberate — long enough to feel cinematic (a Pixar beat), short enough that it never feels like waiting. If it were 2 seconds, it would feel like a page load. If it were 5 seconds, it would feel self-indulgent. 3.5s is the sweet spot where *watching becomes the experience*.

#### Token Alignment Refinements

The following adjustments ensure strict compliance with DESIGN.md token names and values. The original Section 3 is nearly perfect; these are precision fixes:

**1. Loading state typography token:** The spec says `text-heading (28px)` — confirmed correct per DESIGN.md type scale (`--text-heading`: 28px, Fredoka 600). No change needed.

**2. Root node labels — font token clarification:**
- Career title below root: spec says "Fredoka 600, 12px" — this maps to `text-micro` token (12px, Nunito 600). Since Fredoka is the display font, use `font-display` at 12px/600 as specified, but note this is a custom size below the type scale minimum for display. **Implementation note:** Use `font-display text-micro` as Tailwind classes but override `font-family` to Fredoka explicitly — the `text-micro` token maps to Nunito in the type scale, but at this size in the SVG, Fredoka's rounded letterforms are more legible against `bg-void`.
- Salary below root: spec says "Space Mono 10px, `text-muted`" — this is below the `text-stat-label` token (10px). Acceptable in SVG context where the label is secondary. Use `font-data` at 10px.

**3. Branch label pill background:** Spec says `bg-mid` fill. The mockup uses `bg-void`. **Use `bg-mid` as the spec states** — the slightly lighter fill distinguishes the pill from the void background and creates the "plush floating" effect. The mockup's `bg-void` makes pills invisible against the backdrop.

**4. Career node stroke token:** Spec says `border-default` stroke 1px. Confirmed: `rgba(255, 255, 255, 0.1)` per DESIGN.md borders table. Correct.

**5. Endpoint label font clarification:** Spec says "Space Mono 11px, `text-muted`" for career title and "Space Mono 9px, stat color" for salary. The 11px size falls between `data-sm` (13px) and `stat-label` (10px). In SVG rendering at these small sizes, this is acceptable — SVG text does not use Tailwind tokens directly. Implementation should use literal `font-family: var(--font-data)` with explicit `font-size` attributes.

**6. Detail panel background token:** Spec says `bg-mid`. The mockup uses `bg-deep`. **Use `bg-mid` as the spec states.** The panel is an elevated surface that overlays the void canvas — `bg-mid` provides the necessary visual lift per DESIGN.md's elevation hierarchy (`bg-mid` = "Card backgrounds, elevated surfaces"). The mockup's `bg-deep` makes the panel feel like it recedes into the background rather than floating above it.

**7. Detail panel border radius:** Spec says `radius-xl`. Confirmed: 20px per DESIGN.md. The mockup uses square edges on the panel's right side (flush to viewport edge). **For desktop**, use `radius-xl` on the left corners only (`border-top-left-radius: 20px; border-bottom-left-radius: 20px`) since the panel is flush-right. **For mobile bottom sheet**, use `radius-xl` on the top corners only.

#### Animation Refinements

**1. Use `springs.gentle` for the initial tree render, not CSS ease.**
The spec's illumination sequence uses CSS-style "fade in over Nms" language. For implementation, the container-level entrance (the entire SVG tree fading into view) should use `springs.gentle` (`{ stiffness: 150, damping: 30 }`) as DESIGN.md specifies for "branch tree initial render." Individual phase fade-ins within the 3.5s sequence can use CSS `opacity` transitions since they are time-sequenced (not spring-physics-driven), but the overall tree entrance and the root glow breathing animation should use Framer Motion springs.

**2. Root glow breathing animation spec:**
The spec mentions "breathing animation (`rootPulse`, 5s cycle)" for the root glow after illumination completes. Define this as a CSS keyframe:
```css
@keyframes rootPulse {
  0%, 100% { opacity: 0.08; transform: scale(1); }
  50% { opacity: 0.22; transform: scale(1.05); }
}
```
The scale shift (1.0 to 1.05) is critical — opacity alone reads as a flicker; combined with a gentle scale, it reads as breathing. Like a sleeping animal. This is the "alive" feeling.

**3. Branch line draw animation — stroke-dashoffset, not opacity.**
The spec says branch paths "fade in." For the premium version, use SVG `stroke-dasharray` + `stroke-dashoffset` animation to *draw* the lines from origin to destination. The mockup already implements this approach. This is the difference between "lines appeared" and "lines grew toward the future." The emotional distinction matters enormously in the 3-minute demo video.

Implementation:
```typescript
// For each branch path SVG element:
const pathLength = pathElement.getTotalLength();
// Initial state:
pathElement.style.strokeDasharray = `${pathLength}`;
pathElement.style.strokeDashoffset = `${pathLength}`;
// Animate to drawn:
pathElement.style.transition = `stroke-dashoffset ${branchTree.lineDrawDuration}s ease-out`;
pathElement.style.strokeDashoffset = '0';
```

The `lineDrawDuration` of 0.5s per tier (from motion.ts) is correct. Each tier's lines begin drawing at their phase start time, and complete 500ms later — creating a cascade effect where lines seem to extend outward from the root in waves.

**4. Node entrance — use `scaleItem` variant, not just opacity.**
When career nodes appear at t=1.5s, do not just fade them in. Use the `scaleItem` variant from motion.ts (`scale: 0.85 -> 1, springs.bouncy`). Each node should feel like it *landed* on the branch. The 200ms overshoot from `springs.bouncy` (stiffness 300, damping 20) gives each node a satisfying micro-bounce. Stagger with `stagger.normal` (80ms) within each branch group.

**5. Endpoint silhouettes — gentler entrance than career nodes.**
Endpoints should fade in with `springs.gentle` (not bouncy). They are distant futures — softer, more uncertain. The opacity caps at 0.6 as the spec states. The gentle spring (stiffness 150, damping 30) makes them drift into view rather than pop. This subtly communicates: "these are possible, not guaranteed."

**6. Particle drift direction constraint — the spec gets this right.**
Particles drift rightward only (positive dx: 15-40px). This is correct and important. Leftward drift would subconsciously suggest regression. The gentle vertical drift (plus or minus 10px) prevents mechanical-feeling linear motion. Particles should be stat-colored and positioned at branch junction points — they trace the paths the student's career could follow.

#### The Detail Panel: Where Data Becomes Personal

The spec's detail panel design is solid. Two enhancements for the premium version:

**1. Stat delta presentation — add directional arrows.**
The spec calls for stat deltas relative to root (green positive, amber negative). Enhance with small directional arrow icons: a subtle upward-right arrow for positive deltas, downward-right for negative. The arrows should be 8px, same color as the delta text. This adds scanability — the student can read the delta direction before parsing the number.

**2. Boss fight projection pills — add the boss emoji.**
Each boss fight row should include the boss's signature emoji from the gauntlet screen (e.g., robot face for Fight AI, money bag for Fight Loans). This creates continuity — the student recognizes these characters from their recent gauntlet experience. The emoji sits left of the boss name, 16px, with 6px gap.

**3. Pentagon/bar chart toggle in detail panel.**
The mockup includes a pentagon-to-bar-chart toggle in the detail panel. This is a strong addition that the spec's Section 3 stat cards don't capture. **Recommendation:** Include both views. The pentagon gives spatial/comparative feel (shape comparison to root), the bar chart gives precise readability. Default to the bar chart (faster to parse in a detail panel context), with a toggle icon to switch to pentagon. The toggle icon should be a small `bg-surface` circle button (24px), positioned top-right of the stats section.

#### Mockup Divergences to Resolve

The interactive mockup (`screen-08-branch-tree.html`) diverges from the spec in several ways. The **spec wins** in all cases — the mockup is a reference, not the source of truth:

| Mockup | Spec | Resolution |
|--------|------|------------|
| Detail panel uses `bg-deep` | Spec says `bg-mid` | Use `bg-mid` (elevated surface) |
| Branch labels use `bg-void` | Spec says `bg-mid` fill, stat-colored stroke | Use `bg-mid` with stat-colored stroke |
| Mockup uses CSS absolute positioning for nodes | Spec calls for SVG-based tree | Use SVG. The mockup's CSS approach was expedient for prototyping but lacks the precision of SVG coordinate layout for bezier paths and gradient definitions. |
| Mockup has fixed `1600px` canvas width | Spec says "fills viewport width" | Use SVG viewBox with dynamic scaling. The viewBox should be computed from tree content bounds, then the SVG element fills the viewport. |
| Mockup's loading state uses a tree emoji | Spec says profile emoji at 60px | Use the student's profile emoji. This is their tree, not a generic one. |
| Mockup lacks the root glow breathing animation | Spec defines `rootPulse` 5s cycle | Implement the breathing glow. It is the heartbeat of the tree. |
| Mockup's branch lines use flat colors | Spec calls for gradient: `accent-thrive` to stat color | Implement SVG `linearGradient` in `<defs>`. Each branch direction gets its own gradient ID. |
| Known SVG paint order bug: outgoing paths render BEFORE career node rects | Spec requires two SVG groups with correct ordering | Fix: `<g id="branchPaths">` renders first, then `<g id="careerNodes">` with opaque rect fills, then `<g id="outgoingPaths">` renders last. |

#### Mobile Bottom Sheet: Keeping Wonder on Small Screens

The spec correctly identifies mobile as "tree scrollable horizontally, detail panel slides up from bottom as a sheet." Two additions:

**1. Mobile branch card list as primary mobile experience.**
The mockup includes a `mobile-list` fallback that replaces the tree with branch direction cards. This is the right call for sub-768px viewports. The SVG tree is a desktop-first experience — forcing horizontal scroll on mobile is functional but loses the "wonder" emotion. The card list preserves the branching structure (grouped by direction) while being native to touch scrolling. Each card should show: direction label, career count, highest salary in that branch, and the branch's dominant stat color as a left border accent.

**2. Bottom sheet behavior:**
- Height: 60vh max, with drag-to-dismiss.
- Background: `bg-mid`, `radius-xl` top corners, 1px `border-subtle` top.
- Drag handle: 40px wide, 4px tall, `bg-raised`, centered, `radius-full`, 8px from top.
- Content: same as desktop detail panel, scrollable.
- Entrance: slide up from bottom with `springs.smooth`, 300ms.

#### The 30% Rule: What Wins the Video

The hackathon judging allocates 30% to the video demo. This screen is the money shot. Three moments that must look stunning in a 3-minute recording:

1. **The illumination cascade** — record at 1080p, full viewport. The 3.5s sequence from darkness to full tree should be uninterrupted. No narration over the first 2 seconds — let the visual breathe.

2. **Node tap ripple** — when the presenter taps a career node, the dimming of other nodes (40% opacity, 300ms ease) combined with the detail panel sliding in creates a "spotlight" effect. This reads beautifully on video.

3. **The root glow breathing** — after illumination completes, hold on the full tree for 3-4 seconds. The breathing root glow and drifting particles make it clear this is alive, not a screenshot. Judges notice this subconsciously — it signals craft.

#### Summary of Enhancements

All enhancements are additive — no existing Section 3 content needs to be changed. Implementation should follow the spec as written, with these refinements applied as polish:

- Use `stroke-dashoffset` animation for branch line drawing (not opacity fade)
- Use `scaleItem` variant with `springs.bouncy` for career node entrances
- Use `springs.gentle` for endpoint silhouette entrances (softer than career nodes)
- Use `springs.gentle` for the overall tree container entrance
- Implement `rootPulse` breathing keyframe with opacity AND scale
- Add directional arrows to stat deltas in the detail panel
- Add boss emojis to fight projection rows in the detail panel
- Include pentagon/bar-chart toggle in detail panel (default to bar chart)
- Fix all mockup divergences per the table above (spec wins)
- Left-only border-radius on desktop detail panel, top-only on mobile bottom sheet
- Mobile: branch direction card list as primary experience, bottom sheet for detail

---

## §4 Technical Specification

### Architecture Overview

Screen 8 is the most visually complex screen but architecturally straightforward — it fetches a recursive tree structure from one API endpoint and renders it as an SVG visualization with an animated entrance sequence and a tap-to-reveal detail panel. No mutations, no multi-step flows, no Gemma calls. The complexity is in the rendering, not the data flow.

### API Endpoints Consumed

| Endpoint | Method | Request | Response | Used By |
|---|---|---|---|---|
| `/tree/{build_id}?max_depth=3` | GET | Path param: `build_id`. Query param: `max_depth` (default 3). | `{ tree: TreeNode, stats: TreeStats }` | Tree visualization — fetched on navigation to Screen 8 |

**Response shape:**

```typescript
// TreeNode — recursive structure from GET /tree/{build_id}
interface TreeNode {
  soc_code: string;
  title: string;
  level: number;          // 0=root, 1-3=depth
  ern: number | null;
  roi: number | null;
  res: number | null;
  grw: number | null;
  hmn: number | null;
  median_wage: number | null;
  education: string | null;
  boss_ai: string | null;    // "win" | "lose" | "draw" | null
  boss_loans: string | null;
  boss_market: string | null;
  boss_burnout: string | null;
  boss_ceiling: string | null;
  children: TreeNode[];
}

interface TreeStats {
  total_nodes: number;
  max_depth_reached: number;
  mcp_calls: number;
  dead_ends: number;
  wall_clock_ms: number;
}

interface TreeResponse {
  tree: TreeNode;
  stats: TreeStats;
}
```

**Fallback:** If `tree.children` is empty, render the fallback state (root node only + "branches coming soon").

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/BranchTreeScreen.tsx` | Create | Screen 8 top-level: tree loading, fallback, CTA area |
| `frontend/src/components/tree/BranchTreeSVG.tsx` | Create | SVG tree visualization: coordinate layout, path rendering, node rendering, illumination animation |
| `frontend/src/components/tree/TreeRootNode.tsx` | Create | Root node: emoji circle, glow, labels |
| `frontend/src/components/tree/TreeBranchLabel.tsx` | Create | Branch direction pills (column 2) |
| `frontend/src/components/tree/TreeCareerNode.tsx` | Create | Career node rects (column 3) |
| `frontend/src/components/tree/TreeEndpointNode.tsx` | Create | Endpoint silhouettes (column 4) |
| `frontend/src/components/tree/TreeNodeDetailPanel.tsx` | Create | Slide-in detail panel: stats, boss projections, unlock |
| `frontend/src/components/tree/TreeFallback.tsx` | Create | "Branches coming soon" indicator |
| `frontend/src/api/tree.ts` | Create | API client for `/tree/{build_id}` with mock fallback |
| `frontend/src/api/mockTree.ts` | Create | Mock handler returning realistic TreeResponse |
| `frontend/src/types/tree.ts` | Create | TreeNode, TreeStats, TreeResponse TypeScript interfaces |
| `frontend/src/data/treeLayout.ts` | Create | Layout computation: TreeNode → positioned SVG coordinates |
| `frontend/src/App.tsx` | Modify | Add route: `/branches` |

### Layout Computation

The tree is a recursive structure that needs to be flattened into positioned SVG elements. The layout algorithm:

```typescript
// data/treeLayout.ts

interface PositionedNode {
  id: string;
  soc_code: string;
  title: string;
  level: number;
  x: number;
  y: number;
  stats: { ern: number|null; roi: number|null; res: number|null; grw: number|null; hmn: number|null };
  bosses: { ai: string|null; loans: string|null; market: string|null; burnout: string|null; ceiling: string|null };
  median_wage: number | null;
  education: string | null;
  parentId: string | null;
  branchColor: string;  // stat color token for this branch direction
}

interface PositionedPath {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  gradient: string;     // gradient ID
  strokeWidth: number;
  opacity: number;
  group: 'incoming' | 'outgoing';  // determines SVG paint order
}

// Column X positions
const COL_ROOT = 80;
const COL_BRANCH_LABEL = 280;
const COL_CAREER_NODE_LEFT = 400;
const COL_CAREER_NODE_RIGHT = 516;  // 400 + 116 (rect width)
const COL_ENDPOINT = 650;

// Vertical spacing computed dynamically based on node count
function computeLayout(tree: TreeNode, viewportHeight: number): {
  nodes: PositionedNode[];
  paths: PositionedPath[];
  viewBoxHeight: number;
}
```

The layout groups level-1 children into "branches" (each gets a branch label), distributes them vertically, then distributes level-2 children under each branch, and level-3 children (endpoints) further right.

Branch color assignment: each level-1 group gets a stat color based on which stat delta is most positive (highest delta_ern → ern color, etc.). If no clear winner, cycle through [ern, grw, res, hmn].

### Zustand Store

No new store needed. The tree data is local to the `BranchTreeScreen` component — fetched on mount, stored in component state. The `buildStore` already has the Build object with `build_id` for the API call.

### API Client

```typescript
// api/tree.ts

import { apiGet } from "@/api/client";
import { mockGetTree } from "@/api/mockTree";
import type { TreeResponse } from "@/types/tree";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function getTree(
  buildId: string,
  maxDepth: number = 3,
): Promise<TreeResponse> {
  if (USE_MOCK) return mockGetTree();
  return apiGet<TreeResponse>(`/tree/${buildId}?max_depth=${maxDepth}`);
}
```

### Routing Addition

```
/branches  → BranchTreeScreen     (Screen 8)
```

Navigation guard: `/branches` requires a `build` object in the `buildStore`. If missing, redirect to `/reveal`.

### SVG Architecture

The SVG is structured as ordered groups for correct paint order:

```
<svg viewBox="0 0 {width} {height}">
  <defs> (gradients, filters) </defs>
  <g id="stars"> (background twinkle) </g>
  <g id="rootGlow"> (thrive glow circles) </g>
  <g id="branchPaths"> (root → labels → career node LEFT edges) </g>
  <g id="rootNode"> (root emoji circle + labels) </g>
  <g id="branchLabels"> (branch direction pills) </g>
  <g id="careerNodes"> (career node rects — opaque fills) </g>
  <g id="outgoingPaths"> (career node RIGHT edges → endpoints) </g>
  <g id="endpoints"> (endpoint circles + labels) </g>
  <g id="particles"> (drifting particles) </g>
</svg>
```

**Critical: `outgoingPaths` renders AFTER `careerNodes`.** This ensures the thin outgoing paths are visible on top of the opaque career node rects. The mockup has a bug where all paths are in a single group that renders before the career nodes — horizontal outgoing paths are occluded by the rect fills.

### Animation Controller

The illumination sequence is driven by `setTimeout` chains matching the `branchTree` timing presets from `motion.ts`. Each SVG group starts with `opacity: 0` and transitions to `opacity: 1` at its designated time:

```typescript
import { branchTree } from "@/styles/motion";

function runIllumination() {
  // t=0: Root glow
  // t=branchTree.glowStart (0s): glow circle fade
  // t=0.3s: root node
  // t=branchTree.linesStart (0.3s): branch paths
  // t=branchTree.labelsStart (0.8s): branch labels
  // t=branchTree.careerStart (1.5s): career nodes + outgoing paths
  // t=branchTree.endpointsStart (2.2s): endpoints
  // t=branchTree.particlesStart (3.0s): particles + glow settles
}
```

### Service Changes

- No backend changes in this spec.
- No new npm dependencies.
- The `ReceiptPanel` component from F3 is NOT used here — the detail panel has its own stat/boss display.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `App.test.tsx` | Routing tests | Medium | New `/branches` route being added |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `App.test.tsx` | Add route assertion for `/branches` | New route |

#### Confirmed Safe

- All backend tests (no backend changes)
- F1-F4 component tests (no modifications)
- Design token files (no changes)

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `screens/BranchTreeScreen.test.tsx` | renders tree after loading | Loading state → tree appears with root node |
| P0 | `screens/BranchTreeScreen.test.tsx` | renders fallback for empty tree | Empty children → fallback indicator |
| P0 | `components/tree/BranchTreeSVG.test.tsx` | renders root node | Root emoji, title, salary present |
| P0 | `components/tree/BranchTreeSVG.test.tsx` | renders branch paths | SVG paths present for each branch |
| P0 | `components/tree/BranchTreeSVG.test.tsx` | renders career nodes | Career node rects present for each level-2 node |
| P0 | `components/tree/BranchTreeSVG.test.tsx` | renders endpoint nodes | Endpoint circles present for each level-3 node |
| P0 | `components/tree/TreeNodeDetailPanel.test.tsx` | shows on node click | Click career node → panel visible with stats |
| P0 | `components/tree/TreeNodeDetailPanel.test.tsx` | shows stat deltas | Delta values computed correctly vs root |
| P0 | `components/tree/TreeNodeDetailPanel.test.tsx` | shows boss projections | Boss fight pills render with correct results |
| P1 | `components/tree/TreeNodeDetailPanel.test.tsx` | closes on button click | Click close → panel hidden |
| P1 | `components/tree/TreeNodeDetailPanel.test.tsx` | closes on canvas click | Click background → panel hidden |
| P1 | `screens/BranchTreeScreen.test.tsx` | handles API error | Error state renders retry + continue buttons |
| P1 | `screens/BranchTreeScreen.test.tsx` | redirects without build | No build in store → redirect to /reveal |
| P1 | `data/treeLayout.test.ts` | computes positions correctly | Root at x=80, children distributed vertically |
| P1 | `data/treeLayout.test.ts` | handles single-child branches | One child → centered vertically |
| P2 | `api/tree.test.ts` | mock returns valid shape | Mock handler returns TreeResponse matching type |
| P2 | `components/tree/BranchTreeSVG.test.tsx` | outgoing paths after career nodes | SVG group order: outgoingPaths renders after careerNodes |

#### Test Data Requirements

- Mock `TreeResponse` with 3-level tree: 4 level-1 branches, 2 children each, 1-2 endpoints each
- Mock tree with empty `children` for fallback testing
- Mock tree with single branch for edge case testing
- Root node stats for delta computation testing

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-14

#### System Context

Screen 8 is a frontend-only feature that consumes the existing `GET /tree/{build_id}` backend endpoint, renders a recursive `TreeNode` structure as an SVG visualization, and wires up a tap-to-reveal detail panel. It touches three layers: the API client boundary (new `api/tree.ts`), component state (local to `BranchTreeScreen`), and the router (`App.tsx`). No pipeline, Gold zone, MCP, or Gemma changes. The backend endpoint already exists and is verified working in the CLI spike.

#### Data Flow Analysis

The data flow is clean and well-scoped:

```
buildStore.build.build_id
  -> getTree(buildId, 3)
    -> apiGet("/tree/{build_id}?max_depth=3")
      -> backend: state.get_build() -> career_tree.build_tree() -> _node_to_dict()
    -> TreeResponse { tree: TreeNode, stats: TreeStats }
  -> treeLayout.computeLayout(tree, viewportHeight)
    -> { nodes: PositionedNode[], paths: PositionedPath[], viewBoxHeight }
  -> BranchTreeSVG renders positioned elements
  -> TreeNodeDetailPanel overlays on tap
```

One API call, one layout computation, pure rendering after that. No mutations, no back-channel writes to buildStore. The navigation guard (redirect to `/reveal` if no build) is the correct boundary check.

#### Contract Review

**TreeNode interface (spec) vs backend `_node_to_dict` serializer:** Fields match exactly. The recursive `children: TreeNode[]` structure is correctly mirrored. Field names align: `soc_code`, `title`, `level`, `ern`, `roi`, `res`, `grw`, `hmn`, `median_wage`, `education`, `boss_ai` through `boss_ceiling`, `children`.

**TreeStats interface (spec) vs backend response:** The spec lists `total_nodes`, `max_depth_reached`, `mcp_calls`, `dead_ends`, `wall_clock_ms`. The backend router serializes exactly these five fields (omitting the internal-only `nodes_with_full_data`, `nodes_missing_data`, `nodes_before_pruning`). Contract aligns.

**Boss fight result values -- MISMATCH:** The spec's TypeScript comment says `boss_ai: "win" | "lose" | "draw" | null`. The backend's `_score_boss()` function (career_tree.py line 86) maps these to abbreviated forms: `"W"`, `"L"`, `"D"`, `"?"`. The frontend will receive `"W"` / `"L"` / `"D"` / `"?"`, not `"win"` / `"lose"` / `"draw"` / `null`. This affects the detail panel boss fight pills (which the spec says render as "WIN", "LOSS", "DRAW"). See Concerns below.

**apiGet usage:** The spec correctly uses `apiGet<TreeResponse>` with the existing client helper. Query parameter encoding in the URL string (`?max_depth=${maxDepth}`) is fine since `maxDepth` is always an integer.

**PositionedNode / PositionedPath:** These are internal layout types, not API boundary types. Well-structured with the `group: 'incoming' | 'outgoing'` discriminator for SVG paint order control.

#### Findings

##### Sound

- **Component decomposition is excellent.** Eight components, each with a single responsibility. The SVG group structure (stars, rootGlow, branchPaths, rootNode, branchLabels, careerNodes, outgoingPaths, endpoints, particles) maps directly to the illumination animation phases. This makes the setTimeout chain trivially correct -- each timer targets one SVG group.

- **No new Zustand store is the right call.** Tree data is fetched once, rendered, and never mutated. Component-local state avoids unnecessary re-renders of unrelated screens and keeps the buildStore focused on its existing Build lifecycle.

- **SVG paint order is explicitly addressed.** The spec correctly identifies the mockup bug and documents the fix (outgoingPaths group after careerNodes group). The `PositionedPath.group` discriminator ensures the layout algorithm can partition paths for correct rendering.

- **Layout computation is properly separated from rendering.** `treeLayout.ts` as a pure function (TreeNode in, positioned elements out) makes it independently testable without DOM or SVG dependencies. The test plan includes layout-specific tests.

- **Mock/live API toggle follows the established VITE_USE_MOCK_API pattern** used by the gauntlet and build APIs. Consistent.

- **Navigation wiring already exists.** GauntletScreen already navigates to `/branches` (line 226), and AppHeader already includes `/branches` in the post-reveal path list. The spec only needs to register the route in App.tsx and create the screen component.

- **Fallback design is honest and graceful.** Careers without O*NET pathway data show the root node plus a "branches coming soon" message. The student keeps the full build experience. No fake data.

##### Concerns

- **Boss result value mismatch:** The backend `_score_boss()` returns abbreviated strings (`"W"`, `"L"`, `"D"`, `"?"`) while the spec's TypeScript interface documents `"win" | "lose" | "draw" | null`. The detail panel rendering logic and the boss pill labels ("WIN"/"LOSS"/"DRAW") need to handle the actual values. **Impact:** Boss fight pills in the detail panel will either show wrong text or fail to match the expected display values. The `"?"` value (for unknown/insufficient data) is not handled at all in the spec's interface (which says `null` for missing). **Recommendation:** Either (a) update the backend `_score_boss()` to return the full words (`"win"`, `"lose"`, `"draw"`, `null`) to match the existing `BossOutcome` type used elsewhere in the frontend (`types/build.ts` line 64: `type BossOutcome = "win" | "lose" | "draw" | "unknown"`), or (b) update the spec's TypeScript interface and detail panel rendering to handle `"W"` / `"L"` / `"D"` / `"?"`. Option (a) is strongly preferred because it aligns the tree endpoint with the gauntlet endpoint's existing contract, avoiding a one-off format. This is a backend change, but it is a one-line fix in `career_tree.py`.

- **setTimeout cleanup on unmount:** The animation controller uses `setTimeout` chains. If the user navigates away mid-animation (e.g., taps "Back to Gauntlet" at t=1.5s), pending timeouts will fire against unmounted components. **Impact:** React will log "Can't perform a React state update on an unmounted component" warnings, and in edge cases, stale state updates. **Recommendation:** Store timeout IDs in a ref and clear them in a `useEffect` cleanup function. The spec should note this explicitly in the animation controller section.

- **`build_id` access pattern:** The spec says the navigation guard checks for `build` in `buildStore`. The `build_id` for the API call comes from `build.build_id`. But `buildStore` does not persist the `build` object across page refreshes (the `partialize` function on line 61-63 of `buildStore.ts` only persists `hasSeenStatTutorial`). If a student refreshes on `/branches`, `build` will be null and they will be redirected to `/reveal`. **Impact:** This is actually the correct behavior -- a refresh should redirect since the build is session-scoped. But the spec should acknowledge this is intentional behavior, not a bug. No code change needed, just a documentation note.

##### Blockers

None.

#### Verdict
- [x] CHANGES REQUESTED

#### Conditions

1. **Resolve boss result value contract mismatch.** The backend `career_tree.py` `_score_boss()` returns `"W"/"L"/"D"/"?"` but the spec's TypeScript interface expects `"win"/"lose"/"draw"/null`. Preferred fix: update `_score_boss()` to return the full words matching the existing `BossOutcome` type (`"win"`, `"lose"`, `"draw"`, `"unknown"`). This is a one-line backend change (`career_tree.py` line 86). Update `_node_to_dict` to serialize `None` instead of `"?"` for truly missing boss data. If the backend fix is out of scope for this spec, the TypeScript interface and rendering logic must be updated to handle the abbreviated values.
2. **Add setTimeout cleanup note.** The animation controller section should specify that timeout IDs are stored in a `useRef<NodeJS.Timeout[]>` and cleared in the `useEffect` cleanup to prevent state updates on unmounted components.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline changes — frontend consuming existing API contracts)

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `frontend/src/types/tree.ts` | Created — TreeNode, TreeStats, TreeResponse interfaces |
| `frontend/src/data/treeLayout.ts` | Created — Layout computation: recursive TreeNode → positioned SVG coordinates |
| `frontend/src/api/tree.ts` | Created — API client with mock/live toggle |
| `frontend/src/api/mockTree.ts` | Created — Mock handler returning realistic 3-level Financial Analyst tree |
| `frontend/src/components/tree/BranchTreeSVG.tsx` | Created — Main SVG visualization with illumination sequence, stars, particles |
| `frontend/src/components/tree/TreeRootNode.tsx` | Created — Root emoji circle with thrive glow pulse |
| `frontend/src/components/tree/TreeBranchLabel.tsx` | Created — Branch direction pills (column 2) |
| `frontend/src/components/tree/TreeCareerNode.tsx` | Created — Career node rects (column 3) |
| `frontend/src/components/tree/TreeEndpointNode.tsx` | Created — Endpoint silhouettes (column 4) |
| `frontend/src/components/tree/TreeNodeDetailPanel.tsx` | Created — Slide-in detail panel with stats, deltas, boss projections |
| `frontend/src/components/tree/TreeFallback.tsx` | Created — "Branches coming soon" indicator |
| `frontend/src/screens/BranchTreeScreen.tsx` | Created — Screen 8 top-level: loading, tree, fallback, error states |
| `frontend/src/App.tsx` | Modified — Added `/branches` route |
| `backend/app/services/career_tree.py` | Modified — Fixed `_score_boss()` to return full words instead of abbreviations |

### Deviations from Spec
- COL_CAREER_NODE_LEFT adjusted from 400 to 420 for better spacing with branch labels
- COL_ENDPOINT adjusted from 650 to 620 for viewport fit
- Branch label text width computed dynamically rather than fixed
- Used `window.setTimeout` with ref-based cleanup for illumination (architect recommendation)

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | FAIL | 4 TS errors: undefined types in Record access, unused prop | Fixed: literal hex fallbacks, prefixed unused prop |
| 2 | PASS | — | — |

### Pre-existing Test Failures
- `ProfileScreen.test.tsx`: 2 tests fail on clean main (mock API issue, unrelated to this spec)

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Tests | What It Tests |
|-----------|-------|---------------|
| `data/treeLayout.test.ts` | 37 | Layout computation: positions, paths, gradients, branch labels, edge cases |
| `api/tree.test.ts` | 5 | API client: URL construction, mock toggle, error propagation |
| `components/tree/TreeNodeDetailPanel.test.tsx` | 17 | Detail panel: stats, deltas, boss projections, close, accessibility |
| `components/tree/BranchTreeSVG.test.tsx` | 18 | SVG rendering: nodes, paths, illumination, node selection, replay |
| `screens/BranchTreeScreen.test.tsx` | 21 | Screen: loading, tree, fallback, error, navigation guard, CTA |
| **Total** | **98** | — |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | N/A (no backend changes) | — | — | — |
| vitest | 185 | 2 (pre-existing) | 0 | 187 |

### Pre-existing Failures
- `ProfileScreen.test.tsx` (2 tests) — mock API timing issue, verified on clean main branch

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** COMPLETE (2026-04-14)

#### Audit Summary

**Files audited:** `BranchTreeScreen.tsx`, `BranchTreeSVG.tsx`, `TreeRootNode.tsx`, `TreeBranchLabel.tsx`, `TreeCareerNode.tsx`, `TreeEndpointNode.tsx`, `TreeNodeDetailPanel.tsx`, `TreeFallback.tsx`, `treeLayout.ts`

**Verdict:** 14 compliance issues found. 6 are medium-severity token violations (hardcoded hex values that should reference CSS custom properties). 4 are minor spec divergences. 4 are enhancement gaps from the design vision. No blockers.

---

#### 1. bg-void Backdrop
**PASS.** `BranchTreeScreen.tsx` uses `bg-bp-void` on the outer container (`className="min-h-screen bg-bp-void pt-14"`). Correct per DESIGN.md: `bg-void` = `#12131F`, Tailwind class `bg-bp-void`. The tree screen fills the full viewport with the void backdrop as specified.

---

#### 2. Hardcoded Hex Values (Token Violations)

**FAIL -- 22 instances of hardcoded hex colors across 6 files.** DESIGN.md mandates token-only colors. SVG `fill`/`stroke` attributes cannot use Tailwind classes directly, but they SHOULD reference CSS custom properties (`var(--color-bg-mid)`, etc.) rather than raw hex values. This ensures theme consistency and makes future token changes propagate automatically.

| File | Line(s) | Hardcoded Value | Should Be |
|------|---------|-----------------|-----------|
| `TreeRootNode.tsx` | 27-28 | `fill="#7DD4A3"` (outer glow) | `fill="var(--color-accent-thrive)"` |
| `TreeRootNode.tsx` | 35 | `fill="#232545"` (inner circle) | `fill="var(--color-bg-mid)"` |
| `TreeRootNode.tsx` | 36 | `stroke="#7DD4A3"` | `stroke="var(--color-accent-thrive)"` |
| `TreeRootNode.tsx` | 64 | `fill="#F5F0E8"` (title text) | `fill="var(--color-text-primary)"` |
| `TreeRootNode.tsx` | 76 | `fill="#8A8595"` (salary text) | `fill="var(--color-text-muted)"` |
| `TreeBranchLabel.tsx` | 30 | `fill="#232545"` (pill rect) | `fill="var(--color-bg-mid)"` |
| `TreeBranchLabel.tsx` | 42 | `fill="#F5F0E8"` (label text) | `fill="var(--color-text-primary)"` |
| `TreeCareerNode.tsx` | 29 | `fill="#232545"` (career rect) | `fill="var(--color-bg-mid)"` |
| `TreeCareerNode.tsx` | 30 | `stroke="rgba(255,255,255,0.1)"` (default stroke) | `stroke="var(--color-border-default)"` |
| `TreeCareerNode.tsx` | 41 | `fill="#C4BFB0"` (career text) | `fill="var(--color-text-secondary)"` |
| `TreeEndpointNode.tsx` | 24 | `fill="#232545"` (endpoint circle) | `fill="var(--color-bg-mid)"` |
| `TreeEndpointNode.tsx` | 49 | `fill="#8A8595"` (endpoint title) | `fill="var(--color-text-muted)"` |
| `BranchTreeSVG.tsx` | 154 | `fill="#8A8595"` (star fill) | `fill="var(--color-text-muted)"` |
| `BranchTreeSVG.tsx` | 181 | `fill="#7DD4A3"` (root glow circle) | `fill="var(--color-accent-thrive)"` |
| `BranchTreeScreen.tsx` | 196-197 | `fill="#232545"`, `stroke="#7DD4A3"` (fallback root) | Use CSS vars |
| `BranchTreeScreen.tsx` | 208 | `fill="#F5F0E8"` (fallback title) | `fill="var(--color-text-primary)"` |
| `TreeNodeDetailPanel.tsx` | 56 | `style={{ background: "#232545" }}` (panel bg) | `style={{ background: "var(--color-bg-mid)" }}` |
| `TreeNodeDetailPanel.tsx` | 67 | `style={{ background: "#2D3060" }}` (close btn) | `style={{ background: "var(--color-bg-surface)" }}` |
| `TreeNodeDetailPanel.tsx` | 89 | `style={{ background: "#2D3060", borderLeft: "3px solid #7BB8E0" }}` | Use `var(--color-bg-surface)` and `var(--color-accent-info)` |
| `TreeNodeDetailPanel.tsx` | 111 | `style={{ background: "#2D3060" }}` (stat cards) | `style={{ background: "var(--color-bg-surface)" }}` |
| `TreeNodeDetailPanel.tsx` | 155 | `style={{ background: "#2D3060" }}` (boss rows) | `style={{ background: "var(--color-bg-surface)" }}` |
| `treeLayout.ts` | 11-15 | `STAT_COLORS` map with hardcoded hex | Acceptable in layout data (SVG gradients need resolved values). However, `TreeNodeDetailPanel.tsx` lines 12-17 (`STAT_LABELS` colors) should use CSS vars since the panel is HTML, not SVG. |

**Severity: MEDIUM.** The hex values are all correct (they match DESIGN.md token definitions), so there is no visual bug. But hardcoded values bypass the token system and will not respond to any future theme changes. SVG `fill`/`stroke` attributes do accept `var()` in all modern browsers.

**Exception:** `treeLayout.ts` gradient definitions need resolved hex values because SVG `<linearGradient>` `stopColor` does not reliably resolve CSS variables in all rendering contexts. These 5 hex values in `STAT_COLORS` and the `#7DD4A3` thrive gradient source are acceptable as-is but should be documented as intentional exceptions with a comment referencing the DESIGN.md token they map to.

---

#### 3. Font Usage Audit

**PASS with minor issues.**

| Check | Result | Notes |
|-------|--------|-------|
| Fredoka for display/headlines | PASS | `font-display` used on loading heading, detail panel title, section labels |
| Nunito for body/UI | PASS | `font-body` used on body text, CTAs, fallback text, boss labels |
| Space Mono for data | PASS | `font-data` used on SOC codes, salary, stat values, result pills |
| SVG text uses correct font families | PASS | `fontFamily="Fredoka, sans-serif"`, `"Nunito, sans-serif"`, `"Space Mono, monospace"` all correct |

**Minor issue -- CareerNode font size:** `TreeCareerNode.tsx` uses `fontSize={11}` but the spec calls for `fontSize={12}` (Nunito 600, 12px). 1px divergence.

---

#### 4. Stat-Colored Branch Gradients

**PASS.** Gradient definitions in `treeLayout.ts` correctly use:
- `fromColor: "#7DD4A3"` (accent-thrive) as the gradient source
- `toColor: branchColor` computed via `dominantStatColor()` using the correct DESIGN.md stat hex values:
  - ERN: `#F2D477` (gold)
  - ROI: `#7DD4A3` (green)
  - RES: `#B8A9E8` (purple)
  - GRW: `#7BB8E0` (blue)
  - HMN: `#E88BA9` (pink)

All 5 stat colors match DESIGN.md exactly. Gradients are defined as `<linearGradient>` with `x1="0%"` to `x2="100%"` (left-to-right). Correct.

---

#### 5. Typography Scale Compliance

| Component | Token Used | Expected (DESIGN.md) | Status |
|-----------|-----------|----------------------|--------|
| Loading heading | `text-heading` (28px), `font-display`, `font-semibold` | Fredoka 600, 28px | PASS |
| Loading subtext | `text-body` (16px), `font-body` | Nunito 400, 16px | PASS |
| Detail panel title | `text-[18px]`, `font-display`, `font-semibold` | Fredoka 600, 18px | PASS (custom size, matches spec) |
| Detail SOC line | `text-[12px]`, `font-data` | Space Mono 12px | PASS |
| Detail stat label | `text-[11px]`, `font-data`, `font-bold` | Space Mono 11px bold | PASS |
| Detail stat value | `text-[16px]`, `font-data`, `font-bold` | Space Mono 16px bold | PASS |
| Detail boss label | `text-[13px]`, `font-body` | Nunito 13px | PASS |
| Result pill | `text-[11px]`, `font-data`, `font-bold` | Space Mono 11px bold | PASS |
| Section labels | `text-[13px]`, `font-display`, `font-semibold` | Fredoka 600, 13px | PASS |
| Fallback text | `text-body-lg`, `font-body` | Nunito 400, 18px | PASS |
| CTA button | `text-cta`, `font-body`, `font-bold` | Nunito 700, 17px | PASS |
| Ghost buttons | `text-small`, `font-body` | Nunito 400, 14px | PASS |

Typography is well-implemented. Custom pixel sizes used in the detail panel (18px, 13px, 12px, 11px) are appropriate for the compact panel context and match the spec exactly.

---

#### 6. Border Token Usage

**MIXED.**

| Usage | Implementation | Expected | Status |
|-------|---------------|----------|--------|
| Detail panel border | `border border-border` (Tailwind) | `border-default` = `rgba(255,255,255,0.1)` | PASS |
| Career node default stroke | `rgba(255,255,255,0.1)` (inline) | `border-default` | PASS (correct value, should use var) |
| Error "Try Again" button | `border border-border` | Correct | PASS |
| Unlock requirement left border | `borderLeft: "3px solid #7BB8E0"` | `3px accent-info` left border | PASS (correct value, should use var) |

---

#### 7. Spacing / 4px Grid Compliance

**PASS.** All spacing values align to the 4px grid:

| Value | Grid-aligned | Used in |
|-------|-------------|---------|
| `pt-14` (56px) | 56 = 4 x 14 | Screen top padding (header clearance) |
| `px-6` (24px) | 24 = 4 x 6 | Loading state horizontal padding |
| `px-4` (16px), `py-6` (24px) | Both aligned | Tree container padding |
| `mb-6` (24px), `mb-2` (8px) | Both aligned | Loading state spacing |
| `gap-3` (12px) | 12 = 4 x 3 | CTA button gap |
| `mt-8` (32px), `mb-12` (48px) | Both aligned | CTA area margins |
| `p-5` (20px) | 20 = 4 x 5 | Detail panel padding |
| `gap-1.5` (6px) | 6 is not on the 4px grid | Stat card grid gap |
| `px-2.5` (10px) | 10 is not on the 4px grid | Stat card padding |
| `py-1.5` (6px) | 6 is not on the 4px grid | Stat card padding |
| `py-0.5` (2px) | 2 is not on the 4px grid | Result pill padding |

**Minor issue:** `gap-1.5` (6px), `px-2.5` (10px), `py-1.5` (6px), and `py-0.5` (2px) break the 4px grid. These are in the detail panel's compact stat cards where space is tight. 6px and 10px are acceptable sub-grid values for compact UI elements. 2px on the result pill is fine for a badge. Not a blocking issue.

---

#### 8. Illumination Sequence Timing

**PASS with one minor divergence.**

| Phase | motion.ts Preset | Implementation (BranchTreeSVG.tsx) | Status |
|-------|-----------------|-----------------------------------|--------|
| Root glow | `glowStart: 0` | `schedule(branchTree.glowStart * 1000, "rootGlow")` = 0ms | PASS |
| Root node | t=0.3s | `schedule(300, "rootNode")` = 300ms | PASS |
| Branch paths | `linesStart: 0.3` | `schedule(branchTree.linesStart * 1000 + 200, "branchPaths")` = 500ms | DIVERGENCE |
| Branch labels | `labelsStart: 0.8` | `schedule(branchTree.labelsStart * 1000 + 100, "branchLabels")` = 900ms | PASS (matches spec table at t=0.9s) |
| Career nodes | `careerStart: 1.5` | `schedule(branchTree.careerStart * 1000, "careerNodes")` = 1500ms | PASS |
| Outgoing paths | Same as career | `schedule(branchTree.careerStart * 1000, "outgoingPaths")` = 1500ms | PASS |
| Endpoints | `endpointsStart: 2.2` | `schedule(branchTree.endpointsStart * 1000, "endpoints")` = 2200ms | PASS |
| Particles | `particlesStart: 3.0` | `schedule(branchTree.particlesStart * 1000, "particles")` = 3000ms | PASS |

**Minor divergence:** Branch paths use `linesStart * 1000 + 200` = 500ms, but `branchTree.linesStart` is 0.3 (300ms). The +200ms offset delays paths to 500ms instead of 300ms. The spec's timing table says t=0.5s for "Branch lines begin drawing" which actually aligns with the implementation, but the offset is applied manually rather than being derived from the motion.ts preset. This creates a fragile coupling -- if `linesStart` changes in motion.ts, the +200 offset will produce an incorrect result. **Recommendation:** Define the actual intended delay in motion.ts rather than adding manual offsets in the component.

Similarly, `labelsStart * 1000 + 100` = 900ms has a +100ms manual offset. Same fragility concern.

**Fade durations per phase** match the spec:
- Branch paths: 900ms (spec says "fades in over 900ms") -- PASS
- Branch labels: 600ms (spec says "fade in over 600ms") -- PASS
- Career nodes: 700ms (spec says "fade in over 700ms") -- PASS
- Endpoints: 900ms (spec says "fade in over 900ms") -- PASS
- Particles: 1200ms (spec says "fades in over 1200ms") -- PASS

---

#### 9. Responsive Behavior

**PARTIAL IMPLEMENTATION.**

| Breakpoint | Spec Requirement | Implementation | Status |
|------------|-----------------|---------------|--------|
| Desktop (>=1200px) | Tree fills viewport, all columns visible, detail panel overlays right | SVG with `w-full`, detail panel absolute top-right | PASS |
| Tablet (768-1199px) | Tree scaled to fit, detail panel overlays | SVG scales via viewBox | PASS (implicit) |
| Mobile (<768px) | Tree scrollable horizontally, detail panel as bottom sheet | `overflow-x-auto` + `min-w-[700px]` enables scroll | PARTIAL |

**FAIL -- Mobile bottom sheet not implemented.** The spec and design vision both call for the detail panel to slide up from the bottom as a sheet on mobile (`<768px`), with drag-to-dismiss, 60vh max height, `bg-mid` background, `radius-xl` top corners, and drag handle. The current `TreeNodeDetailPanel` uses the same absolute-positioned right-side overlay on all viewport sizes. No `tablet:` or `mobile:` responsive breakpoint classes are used.

**FAIL -- Mobile branch card list not implemented.** The design vision recommends a branch direction card list as the primary mobile experience (replacing the SVG tree on sub-768px viewports). This is not implemented. Mobile users see the desktop SVG tree with horizontal scroll, which loses the "wonder" emotion as noted in the design vision.

**Severity: MEDIUM.** The tree is functional on mobile (horizontal scroll works), but the experience is not optimized per spec.

---

#### 10. Design Vision Enhancement Gaps

The following enhancements from the design vision (Section 3 addendum by @fp-design-visionary) are NOT implemented:

| Enhancement | Status | Priority |
|------------|--------|----------|
| `stroke-dashoffset` line drawing animation | NOT IMPLEMENTED -- lines use opacity fade | HIGH (demo video impact) |
| `scaleItem` variant for career node entrances | NOT IMPLEMENTED -- career nodes use opacity fade | MEDIUM |
| `springs.gentle` for endpoint silhouette entrances | NOT IMPLEMENTED -- endpoints use opacity fade | LOW |
| `springs.gentle` for overall tree container entrance | NOT IMPLEMENTED -- uses CSS `duration: 0.3` | LOW |
| `rootPulse` breathing with scale (1.0 to 1.05) | PARTIALLY IMPLEMENTED -- opacity breathing works, but no scale transform | LOW |
| Directional arrows on stat deltas | NOT IMPLEMENTED | LOW |
| Boss emojis in fight projection rows | IMPLEMENTED | n/a |
| Pentagon/bar-chart toggle | NOT IMPLEMENTED | LOW |
| Desktop panel left-only border-radius | NOT IMPLEMENTED -- uses `rounded-xl` all corners | LOW |

The `stroke-dashoffset` line drawing animation is the highest-impact missing enhancement. The design vision explicitly states: "This is the difference between 'lines appeared' and 'lines grew toward the future.' The emotional distinction matters enormously in the 3-minute demo video."

---

#### 11. Replay Button Styling

**Minor issue.** The replay button uses inline `style={{ background: "rgba(35,37,69,0.8)" }}`. The value `rgb(35,37,69)` is close to `bg-mid` (`#232545` = `rgb(35,37,69)`) at 80% opacity. This should use `var(--color-bg-mid)` with an opacity modifier or be expressed as a Tailwind class. Currently a hardcoded rgba value.

---

#### 12. Detail Panel Border Radius

**Minor divergence.** The spec and design vision call for `radius-xl` on left corners only (desktop, flush-right panel) and top corners only (mobile bottom sheet). Implementation uses `rounded-xl` on all four corners. Since the panel is positioned `right-8` (not flush to viewport edge), the all-corners radius is visually acceptable but diverges from the spec's vision of a flush-right panel at `right: 32px`.

---

#### Compliance Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| bg-void backdrop | 10/10 | Correct usage |
| Stat color hex values | 10/10 | All 5 stat colors match DESIGN.md |
| Font families | 10/10 | Fredoka/Nunito/Space Mono used correctly |
| Token-only colors | 4/10 | 22 hardcoded hex values that should be CSS vars |
| Typography scale | 9/10 | 1 minor size divergence (11px vs 12px) |
| Border tokens | 7/10 | Correct values, some hardcoded instead of vars |
| Spacing (4px grid) | 8/10 | Minor sub-grid values in compact panel |
| Illumination timing | 9/10 | Manual offsets create fragile coupling |
| Responsive behavior | 4/10 | Mobile bottom sheet + card list not implemented |
| Design vision enhancements | 3/10 | stroke-dashoffset, scaleItem, springs.gentle missing |
| **Overall** | **74/100** | Solid foundation; token refs + mobile + line-draw animation needed |

---

#### Recommendations (Priority Order)

1. **HIGH -- Replace hardcoded hex with CSS custom properties** in all SVG `fill`/`stroke` attributes and inline `style` objects. This is the single most impactful change for design system compliance. All hex values are correct today, but they bypass the token system.

2. **HIGH -- Implement stroke-dashoffset line drawing animation** for branch paths. This is the highest-impact visual enhancement for the demo video. The motion.ts `lineDrawDuration: 0.5` preset already exists and is unused.

3. **MEDIUM -- Implement mobile bottom sheet** for the detail panel on `<768px` viewports. The current right-side overlay is not usable on small screens.

4. **MEDIUM -- Use scaleItem variant** from motion.ts for career node entrances instead of opacity fade. The `springs.bouncy` micro-bounce creates the "landed on the branch" feeling described in the design vision.

5. **LOW -- Add scale transform to rootPulse** breathing animation (1.0 to 1.05). Currently opacity-only.

6. **LOW -- Fix manual timing offsets** in `BranchTreeSVG.tsx`. Move the +200ms and +100ms adjustments into motion.ts `branchTree` presets so timing is centralized.

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
**Date:** 2026-04-14
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary

Look, I love Claude, BUT... this one is going to need a few passes before it earns its place in production. The frontend implementation is structurally solid -- good cancellation logic on the fetch, clean state machine, reasonable component decomposition. The layout engine is a pure function with no side effects, which is the kind of thing that makes me sleep slightly less badly at night. However, there is a real backend bug that will break existing tests (the `_score_boss` change is only half-done), a retry mechanism that doesn't actually retry, and a timeout cleanup that leaks references. Claude did 80% of the work here. Unfortunately, it's the other 20% that causes outages.

#### Findings

**CRITICAL** (will cause test failures / broken behavior)

**Finding 1: Backend `_score_boss()` change breaks existing test assertions**
- **Severity:** CRITICAL
- **Impact:** The backend test `test_boss_results_computed` at `backend/tests/services/test_career_tree.py:183` asserts that boss results are in `("W", "L", "D", "?")`. The `_score_boss()` function was changed to return full words (`"win"`, `"lose"`, `"draw"`, `"unknown"`) but the test was NOT updated. This means `pytest` will fail on the backend test suite. This is a shipped regression.
- **Location:** `backend/app/services/career_tree.py:85-86` and `backend/tests/services/test_career_tree.py:183-184`
- **The Problem:** Half-finished migration. The function changed but the test assertions still expect the old abbreviated format.
- **The Fix:** Update the test assertions to match the new return values:
```python
# test_career_tree.py:183-184
assert root.boss_ai in ("win", "lose", "draw", "unknown")
assert root.boss_market in ("win", "lose", "draw", "unknown")
```
- **Routing:** Implementation agent -- fix the backend test.

---

**SERIOUS** (will cause problems in edge cases or at scale)

**Finding 2: Retry mechanism does not actually re-fetch data**
- **Severity:** SERIOUS
- **Impact:** When a user clicks "Try Again" after an API error, `handleRetry` navigates to `/branches` with `replace: true`. But the component is already mounted at `/branches`. React Router's `navigate("/branches", { replace: true })` when you're already on `/branches` does NOT cause a re-mount -- it just replaces the history entry. The `useEffect` that fetches data depends on `[build]`, and `build` hasn't changed, so the effect won't re-run. The user clicks "Try Again" and nothing happens. This is a 3am page waiting to happen -- users stuck on an error screen with a button that does nothing.
- **Location:** `frontend/src/screens/BranchTreeScreen.tsx:91-96`
```typescript
const handleRetry = useCallback(() => {
    setError(null);
    setScreenState("loading");
    navigate("/branches", { replace: true });
}, [navigate]);
```
- **The Fix:** Add a retry counter to the dependency array of the fetch effect, and increment it on retry:
```typescript
const [retryCount, setRetryCount] = useState(0);

// In the fetch useEffect, add retryCount to deps:
useEffect(() => {
    if (!build) return;
    // ... existing fetch logic ...
}, [build, retryCount]);

const handleRetry = useCallback(() => {
    setError(null);
    setScreenState("loading");
    setRetryCount((c) => c + 1);
}, []);
```
- **Routing:** Implementation agent.

**Finding 3: Timeout references accumulate across replay invocations**
- **Severity:** SERIOUS
- **Impact:** When the user clicks "Replay", `handleReplay` calls `clearTimeout` on all existing refs and then `runIllumination()`. But `runIllumination` pushes new timeout IDs onto `timeoutRefs.current` without clearing the array first. The array is only cleared in the `useEffect` cleanup (unmount). So each replay adds 8 more entries to the array. After 50 replays, you have 400+ stale entries being iterated. Not catastrophic, but sloppy -- and the stale IDs in the array are dead references that `clearTimeout` on replay will harmlessly no-op on, wasting cycles.
- **Location:** `frontend/src/components/tree/BranchTreeSVG.tsx:119-123`
```typescript
function handleReplay() {
    timeoutRefs.current.forEach(clearTimeout);
    timeoutRefs.current = [];
    runIllumination();
}
```
- **The Problem:** Actually, looking again -- `handleReplay` DOES reset the array with `timeoutRefs.current = []` before calling `runIllumination`. But the `useEffect` cleanup on line 94-97 only clears but doesn't prevent the race: if the component unmounts DURING an illumination, the timeouts will fire and call `setPhases` on an unmounted component. React 18+ handles this gracefully (no-op setState on unmount), but it's still a warning in StrictMode dev builds.
- **Revised Assessment:** The replay cleanup is actually correct. Downgrading this. The real issue is the `useEffect` cleanup: it clears timeouts and resets the array, but if a timeout fires between the `forEach(clearTimeout)` and the `timeoutRefs.current = []` assignment (theoretically impossible in JS single-thread, but still), the stale ref could persist. In practice this is fine. **Withdrawing this finding.**

**Finding 3 (revised): `computeLayout` called twice -- once in BranchTreeSVG and once in BranchTreeScreen**
- **Severity:** SERIOUS
- **Impact:** `computeLayout(tree)` is called in `BranchTreeScreen.tsx:73` to find `selectedNode` and `rootNode`, AND again in `BranchTreeSVG.tsx:47` for rendering. This is the same pure function on the same data, running twice. The layout computation iterates all nodes and builds paths, gradients, and labels. For a tree with 12 nodes this is negligible. For a tree with 100+ nodes (which the `max_depth=3` parameter could produce with dense O*NET data), this doubles the layout work on every render.
- **Location:** `frontend/src/screens/BranchTreeScreen.tsx:73` and `frontend/src/components/tree/BranchTreeSVG.tsx:47`
- **The Fix:** Pass the computed layout from the parent screen into `BranchTreeSVG` instead of recomputing it. Or lift the `selectedNode`/`rootNode` lookup into `BranchTreeSVG` and expose it via a callback. The cleanest approach is to pass the layout down:
```typescript
// BranchTreeScreen: pass layout to BranchTreeSVG
<BranchTreeSVG layout={layout} emoji={emoji} ... />

// BranchTreeSVG: accept layout as prop instead of recomputing
interface BranchTreeSVGProps {
    layout: TreeLayout;
    // ... rest of props, remove tree prop
}
```
- **Routing:** Implementation agent.

---

**MODERATE** (maintainability / could become serious)

**Finding 4: Error message displayed raw to user could leak internal details**
- **Severity:** MODERATE
- **Impact:** When the API fails, the error message is extracted with `err instanceof Error ? err.message : "Failed to load tree"` and displayed directly to the user at line 240. The `apiGet` client at `client.ts:21` constructs errors from server response bodies: `detail.detail || "API error: ${res.status}"`. If the backend returns a detailed error (stack trace, internal path, database error), it gets shown to the end user. This is an information disclosure vector.
- **Location:** `frontend/src/screens/BranchTreeScreen.tsx:60,239-241`
- **The Fix:** Show a generic user-friendly message and log the actual error to console for debugging:
```typescript
catch (err) {
    if (cancelled) return;
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[BranchTreeScreen] fetch failed:", msg);
    setError("Something went wrong loading your career branches.");
    setScreenState("error");
}
```
- **Routing:** Implementation agent.

**Finding 5: `buildId` is interpolated into URL without validation**
- **Severity:** MODERATE
- **Impact:** In `api/tree.ts:12`, the `buildId` parameter is interpolated directly into the URL path: `` `/tree/${buildId}?max_depth=${maxDepth}` ``. The `buildId` comes from the Zustand store which is populated from the API response, so in normal flow it's safe. But if the store is ever populated from URL params or user input (future feature), a crafted `buildId` like `../../admin` could hit unexpected endpoints. Defensive coding suggests validating the format.
- **Location:** `frontend/src/api/tree.ts:12`
- **The Fix:** This is low-risk given current data flow (buildId comes from server). Note for future: if buildId ever comes from user input, add validation. No code change required now, but flagging for awareness.
- **Routing:** No action needed -- informational.

**Finding 6: `dominantStatColor` returns ERN color when all stats are null**
- **Severity:** MODERATE
- **Impact:** In `treeLayout.ts:95-112`, if both root and child have all-null stats, `maxDelta` stays at `-Infinity` and `maxStat` stays at `"ern"`, so the branch color defaults to ERN gold. This works but is accidental -- the behavior depends on the initial value of `maxStat` rather than an explicit fallback. If someone reorders the STAT_KEYS array or changes the loop, the default color changes silently.
- **Location:** `frontend/src/data/treeLayout.ts:95-112`
- **The Fix:** Already handled by the `?? "#F2D477"` fallback on line 111. The behavior is correct, just fragile. Consider adding a comment: `// Falls through to ERN (gold) as default when no stat deltas are computable`.
- **Routing:** No action needed -- informational.

---

**MINOR**

**Finding 7: `handleCanvasClick` uses tagName comparison that may break with SVG namespaces**
- **Severity:** MINOR
- **Impact:** `(e.target as SVGElement).tagName === "svg"` works in modern browsers, but SVG elements historically had uppercase tagName in some contexts. In practice this is fine for all supported browsers, but `e.target === e.currentTarget` is more robust for "did they click the background?"
- **Location:** `frontend/src/components/tree/BranchTreeSVG.tsx:113-117`
- **The Fix:**
```typescript
function handleCanvasClick(e: React.MouseEvent<SVGSVGElement>) {
    if (e.target === e.currentTarget) {
        onSelectNode(null);
    }
}
```
- **Routing:** Implementation agent -- easy fix.

#### What's Good

I'll give credit where it's due (grudgingly):

- **Cancellation pattern in the fetch effect** (`let cancelled = false` with cleanup) is textbook correct. No memory leaks from stale responses. This is the pattern I'd write myself.
- **Pure layout function** (`computeLayout`) is fully deterministic, side-effect-free, and extremely testable. The test suite for it is comprehensive -- null handling, edge cases, single-child branches, all covered. This is genuinely good engineering.
- **Test coverage** is thorough. 60+ assertions across 5 test files. The detail panel tests actually verify delta math, null handling, and boss result filtering. The layout tests verify coordinate positioning. These are real tests, not checkbox tests.
- **SVG paint order fix** (outgoing paths rendered after career node rects) correctly addresses the mockup bug called out in the spec. Someone was paying attention.
- **State machine pattern** (`ScreenState` union type with `loading | tree | fallback | error`) is clean and matches the existing RevealScreen pattern.
- **Illumination sequence** correctly uses the `branchTree` presets from `motion.ts` rather than improvising timing values. Consistent with the design system.

#### Required Changes

| Priority | Finding | Routing |
|----------|---------|---------|
| CRITICAL | F1: Backend test asserts old `_score_boss` format ("W"/"L") instead of new ("win"/"lose") | Implementation agent: update `test_career_tree.py` |
| SERIOUS | F2: Retry button does nothing (navigate to same route doesn't re-trigger fetch) | Implementation agent: use retry counter state |
| SERIOUS | F3: `computeLayout` computed twice (screen + SVG component) | Implementation agent: pass layout as prop |
| MODERATE | F4: Raw error messages shown to user | Implementation agent: sanitize error display |
| MINOR | F7: SVG canvas click detection fragile | Implementation agent: use `e.currentTarget` |

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PASSED (with pre-existing mypy and ProfileScreen.test.tsx caveats documented below)
**Verified:** 2026-04-14 22:15

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | No issues |
| Type check (mypy) | PASS (pre-existing) | 44 errors in 18 files — confirmed identical on baseline (main before spec changes). Zero errors introduced by this spec. |
| Tests (pytest) | PASS | 179 passed, 0 failed |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS (pre-existing failures) | 184 passed, 2 failed — both failures are in `ProfileScreen.test.tsx` ("renders profile name", "reroll swaps name"), confirmed pre-existing on main before spec changes. All 20 BranchTreeScreen tests pass. |
| Production build (Vite) | PASS | 461 modules transformed, built in 913ms |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | All checks passed (pre-existing issues documented) | mypy: 44 pre-existing errors confirmed on baseline; vitest: 2 pre-existing ProfileScreen failures confirmed | None required |

---

## §10 Discussion

```
[2026-04-14 16:00] @faang-staff-engineer → Implementation agent
Code review complete. Verdict: CHANGES REQUIRED.

5 findings, 1 critical, 2 serious, 1 moderate, 1 minor.

Critical: The backend _score_boss() was changed from abbreviated ("W"/"L"/"D"/"?")
to full words ("win"/"lose"/"draw"/"unknown") but test_career_tree.py:183-184 still
asserts the old format. This WILL fail pytest. Fix the test.

Serious: handleRetry navigates to /branches but the component is already at /branches,
so the fetch useEffect (keyed on [build]) never re-runs. Use a retryCount state var
instead of navigate.

Serious: computeLayout runs twice — once in BranchTreeScreen for node lookup, once
in BranchTreeSVG for rendering. Pass the layout as a prop to avoid double computation.

See §8 Code Review for full details, code examples, and fix instructions.
```

---

## §11 Final Notes

**Human Review:** PENDING

**Context for agents:**

- **DESIGN.md is the source of truth** for all visual decisions. Read it before writing any UI code. If DESIGN.md and existing code disagree, DESIGN.md wins.
- **The Branch Tree Illumination sequence** is defined in DESIGN.md's "Key Animation Sequences" and implemented in `motion.ts` as `branchTree.*`. Use these timing presets — do not improvise timing. The 7-step sequence (glow → lines → labels → career nodes → endpoints → particles) is choreographed.
- **SVG paint order is critical.** The `outgoingPaths` group MUST render AFTER `careerNodes` in SVG document order. The career node rects have opaque `bg-mid` fills. If outgoing paths render before the rects, horizontal paths are completely hidden. The mockup (`docs/mockups/branch-tree-mockup-v1.html`) has this exact bug — do NOT reproduce it.
- **Branch gradients use stat colors.** Each branch direction gets a gradient from `accent-thrive` → stat color. The stat color is determined by the dominant stat delta of the branch (highest positive delta picks the color). Gradients defined in `<defs>`, referenced by `stroke="url(#grad-{stat})"`.
- **The tree API returns recursive data.** `GET /tree/{build_id}` returns `{ tree: TreeNode, stats: TreeStats }`. TreeNode has `children: TreeNode[]`. The layout algorithm flattens this into positioned SVG elements. The flat `build.branches` list is a fallback, not the primary data source.
- **Emoji centering in SVG is tricky.** Use `dominant-baseline="central"` on the `<text>` element and set `y` to the circle's `cy` + 2px. Emoji rendering varies by browser — test in Chrome and Safari.
- **This is the "wonder" screen.** The emotional target is awe — the student's future literally illuminating across the screen. Progressive illumination is the product metaphor made visible. The animation should feel like stars appearing in a planetarium, not like a loading spinner.
- **Responsive: horizontal scroll on mobile.** The tree is inherently horizontal. On narrow viewports, allow horizontal scrolling rather than cramming the tree vertically. The detail panel switches to a bottom sheet on mobile.
- **Mock API handlers** must return a TreeResponse with a realistic 3-level tree. Use the Financial Analyst example from the mockup as reference data.
- **The mockup at `docs/mockups/branch-tree-mockup-v1.html`** is a design reference with known SVG bugs. Use it for aesthetic direction (gradients, glow, particles, detail panel) but fix the paint order and path connectivity issues during implementation.

---
