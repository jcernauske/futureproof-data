# Feature: `/career-pick` lineage sheet + Ask-Gemma chips

## Claude Code Prompt

```
Read the spec at docs/specs/screen-career-pick-lineage-sheet.md in its entirety.

This is a Standard-weight UI spec with a material layout change + a new interactive component (iOS-style bottom sheet with drag-to-resize detents) + a new canned-question chip row that calls Gemma to explain the screen. Architecture Review and Data Review are SKIPPED — the backend adds two small endpoints but no schema changes, no stat formula changes, no pipeline work (§2 Decision #1 + §5). Design Vision and Design Audit are REQUIRED because the layout is being reworked and net-new components are being introduced.

Execute the following workflow:

1. DESIGN VISION
   - Invoke @fp-design-visionary to fill in §3 UI/UX Design.
   - Visionary proposes: (a) the vertical-stacked tier layout with 2-col card grids, (b) the three sheet detent heights + the drag-handle affordance, (c) the horizontal branch-flow rendering inside the sheet (selected career → arrows → branch chips with stat deltas), (d) entrance/exit animation for populate-on-select, (e) responsive behavior (desktop primary, mobile viewport fallback), (f) the Ask-Gemma chip row + inline response card inside the sheet — chip placement at each detent, response-card layout, loading/streaming affordance.
   - Visionary references Brightpath tokens + motion presets from DESIGN.md only. Flags any net-new motion presets needed for the sheet detent snap + drag-handle pulse + chip expand-to-response transition.
   - §3 becomes the pixel-perfect implementation target. If Visionary proposes a detour that breaks the §2 scope (e.g. relocating the branch view off-screen, or introducing a free-form chat input — see §2 Decision #9), route back via §10.

2. IMPLEMENTATION
   - Implement §3 (Design Vision output) and §4 Technical Specification as written.
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: update only the tests listed under "Authorized Test Modifications".
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human via §10 Discussion.
   - Log all work to §6 Implementation Log.
   - Run backend (ruff + mypy + pytest) + frontend (tsc + vitest) to verify the build at each milestone.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts). After 3: escalate via §10.

3. TESTING
   - Invoke @test-writer to review §4 Testing Impact Analysis and implement every "New Tests Required" entry in priority order (P0 first).
   - Frontend tests: vitest in frontend/src/ — covers CareerPickScreen layout, CareerLineageSheet detent behavior, branch fetch + populate-on-select, Ask-Gemma chip row + auto-elevation logic + fetch lifecycle, a11y.
   - Backend tests: pytest in backend/tests/ — coverage for the two new endpoints `GET /career-pick/chips` and `POST /career-pick/ask`, the canned-question prompt builder, intent-mismatch detection, fallback narratives, and `gemma.jsonl` coverage under the new call sites.
   - Run the full pytest + vitest suites to catch regressions.
   - If still broken after 3 attempts: escalate via §10.

4. DESIGN AUDIT
   - Invoke @fp-design-auditor to mechanically verify the implemented sheet + tier layout matches §3 and Brightpath tokens / motion presets in DESIGN.md.
   - Auditor checks: no hardcoded colors/spacing, correct typography tiers, motion durations come from `motion.ts` tokens (or a newly-added named preset authored in §3), focus ring on drag handle, aria-expanded on tier disclosures, aria-label states on sheet detents, reduced-motion respected.
   - Writes findings to §8 Design Audit.
   - If CHANGES REQUIRED: route back to implementer via §10.

5. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.
   - Pay special attention to:
     * drag gesture correctness under Framer Motion (no layout thrash on drag, snap math handles the three detents cleanly, dragEnd → detent resolution covers fling velocity)
     * keyboard + screen-reader equivalence for the drag gesture (discrete click-to-step buttons, arrow-key support)
     * branch fetch lifecycle (cancel on new selection, loading state, error state)
     * reduced-motion + prefers-contrast fallbacks
     * no regression in RevealScreen flow after this screen's state changes (buildStore + buildInputStore are shared).
   - Reviewer writes findings to §8 Code Review.
   - If APPROVED: proceed to step 6.
   - If CHANGES REQUIRED: route back via §10.

6. VERIFICATION
   - Invoke @fp-builder to run full build verification.
   - Backend: ruff check, mypy, pytest.
   - Frontend: TypeScript, vitest, Vite production build.
   - Log results to §9 Verification.
   - Run the manual interaction smoke listed in §9 (drag between detents on desktop, keyboard equivalents, mobile viewport, populate-on-select from each tier).
   - If all green: mark status COMPLETE.

7. COMPLETION
   - Update top-level Status to COMPLETE.
   - Check off all Success Criteria in §1.
   - Update §6 Implementation Log, §7 Test Coverage, §8 Reviews.
   - Generate report to reports/screen-career-pick-lineage-sheet-YYYY-MM-DD.md.
   - Move this file to docs/specs/completed/.
   - **Parallel-worktree discipline:** commit all work to the CURRENT branch only. This spec may run concurrently with `docs/specs/feature-gemma-tiered-matching.md` in a sibling worktree (per the `Parallel With` metadata row). Do NOT merge to `main`, do NOT `git push`, do NOT create a PR. The orchestrating session integrates branches to `main` after both parallel specs complete.
```

---

## Status: IMPLEMENTATION

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
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
| Created | 2026-04-18 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-18 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/screen-career-pick-reveal.md`, `docs/specs/completed/feature-stage3-branch-tree.md` (if present — the Gold-zone spec that created `consumable.career_branches` / `consumable.career_transitions`) |
| Parallel With | `docs/specs/feature-gemma-tiered-matching.md` — safe to run concurrently in a sibling git worktree per §0. Expect additive-only merge conflicts on `DESIGN.md` + `docs/mockups/brightpath-design-system-v3.html` at integration time. |

---

## §1 Feature Description

### Overview

Rework `/career-pick` so students see each career card as a **trajectory** rather than a single first-job snapshot, AND give them a way to ask Gemma canonical questions about what's on the screen. The top two-thirds of the screen becomes a vertically-stacked list of collapsible Common / Less Common / Stretch tiers (2-column card grids inside each). The bottom third becomes a new iOS-style bottom sheet (`CareerLineageSheet`) that populates with the selected card's stage-3 career branches — same data that's already served at `GET /branches/{soc}` via `backend/app/services/branch_tree.py` and shown later in the `/reveal` cinematic tree. The sheet is draggable between three detents (compact / medium / large) so a student can keep the tier cards visible while glancing at progressions, or promote the sheet to near-full-screen when they want to study the lineage in depth. A canned-question chip row inside the sheet (e.g. "Why don't I see 'doctor'?", "What does this career actually do?", "Is this the right school for this?") lets students tap to get a Gemma-generated, screen-grounded explanation — no free-form input, no guardrail surface area beyond the canned prompts.

### Problem Statement

A student searching Millikin University for "pre-med" sees Gemma suggest Biology, picks it, and lands on `/career-pick`. The current screen shows three tiers of cards — "Biological technicians $52k," "Agricultural technicians $46k," etc. — and stops there. There is no way to tell, at pick time, whether any of those cards leads toward something like "physician" or tops out at technician. The `consumable.career_branches` table already has stage-3 progression data keyed by SOC; the `/reveal` screen already renders it; but it's invisible on the pick screen where the decision is actually being made.

Separately, the current Common / Less Common / Stretch 3-column layout makes each card a narrow vertical strip — stat pills wrap awkwardly, titles truncate, and there's no room to hint at lineage without a redesign. Stacking tiers vertically with 2-col card grids gives each card the horizontal room to breathe and also makes room on the page for the lineage sheet.

**The "why don't I see doctor?" problem specifically:** a student searching "pre-med" sees Gemma suggest Biology (correct — biology IS the standard pre-med major), picks it, and then doesn't see physician on this screen (also correct — the CIP–SOC crosswalk is undergrad-first-job and physician requires an MD). Without an explanation, the student can't tell whether (a) Millikin is the problem, (b) Biology was the wrong pick, or (c) our data is broken. The Ask-Gemma chip is the real fix: Gemma can cite the actual data on the screen and explain the undergrad / graduate-school distinction in plain language, at 6th-grade reading level, in ~4 sentences. This obviates the need for a graduate-track data-work spec for the hackathon demo (though that spec remains a valuable long-term follow-up — see §11).

**Auto-elevation heuristic:** when the student's original `major_text` matches a known graduate-track intent pattern (`pre-med`, `premed`, `pre med`, `pre-law`, `prelaw`, `pre law`, `pre-vet`, `prevet`, `pre vet`, `pre-dental`, `predental`) AND the rendered tier outcomes don't contain the expected terminal SOC (physician `29-12**`, lawyer `23-1011`, veterinarian `29-1131`, dentist `29-1022` etc.), the "Why don't I see [X]?" chip is elevated to the top of the chip row and styled with the Brightpath alert-accent to signal it's likely the question the student is about to ask. This is the bit that makes it feel like Gemma read their mind.

### Success Criteria

- [ ] `/career-pick` top 2/3 renders Common / Less Common / Stretch as vertically-stacked, individually-collapsible tier sections. Each tier body is a 2-column card grid on desktop (reduces to 1-column at tablet width and below).
- [ ] Tier disclosure state is individually persistent during the session (a student who collapses "Stretch" doesn't lose that setting by clicking a card in "Common"). Default state: all three expanded.
- [ ] Bottom 1/3 of the viewport is occupied by a new `CareerLineageSheet` component when the screen mounts. Sheet starts in "compact" detent.
- [ ] Clicking a career card populates the sheet with branches fetched from `GET /branches/{soc}`. The selected card's SOC is passed; the sheet re-fetches + re-renders on any subsequent selection.
- [ ] Sheet supports three vertical-drag detents: **compact** (≈33 % of viewport), **medium** (≈50 %), **large** (≈85 %). Snapping is velocity-aware (fling past the mid-point lands on the next detent).
- [ ] Sheet has a visible drag handle at the top edge. Handle is keyboard-focusable; `ArrowUp` / `ArrowDown` steps between detents. An alternate pair of chevron buttons (up/down) is always visible for non-pointer users.
- [ ] Sheet renders the branch flow as a left-to-right horizontal layout: selected career "chip" at the left, a connector glyph, then each branch rendered as its own chip with `to_title`, the non-zero `delta_*` stat deltas, and a short rationale from `career_transitions` when available. Horizontal overflow scrolls.
- [ ] Loading / empty / error states present with Brightpath-compliant styling. Loading uses the `GemmaThinking` / `GemmaSpinner` pattern already in use on `/career-pick`.
- [ ] No new backend API surface. All data comes from the existing `GET /branches/{soc}` endpoint.
- [ ] Building + picking flow through to `/reveal` is unchanged. `selectedCareer` is still the single source of truth that `/reveal` consumes from `buildStore`.
- [ ] `aria-expanded` on tier disclosures; `role="dialog"` / `aria-modal="false"` on the sheet with dynamic `aria-label` reflecting the current detent; `prefers-reduced-motion` respected (snap still occurs, drag animation attenuated; no easing spring on motion-averse).
- [ ] Ask-Gemma chip row renders inside the sheet (visible at compact detent; expanded response card renders at medium+ detent). Chip set is delivered by the backend via a new `GET /career-pick/chips` endpoint keyed by `(cipcode, major_text, tiered_careers)` so the backend owns the auto-elevation logic.
- [ ] Auto-elevation of the "Why don't I see [X]?" chip fires for known graduate-track intent patterns when the terminal SOC is absent from the rendered tiers. Elevated chip is first in order and visually distinct (Brightpath accent-alert).
- [ ] Clicking a chip fires `POST /career-pick/ask` with `{chip_id, cipcode, major_text, tiered_careers, selected_soc?}` and renders the Gemma-generated response in the sheet's response card. Response is 4–6 sentences, 6th-grade reading level, grounded in the actual screen data. Deterministic fallback string fires when Gemma returns empty.
- [ ] No free-form chat input anywhere on `/career-pick`. Chips only. (§2 Decision #9.)
- [ ] Every chip-click Gemma call appears in `logs/gemma.jsonl` with a `call_site: "career_pick.ask"` tag so the demo audit trail is complete.
- [ ] pytest suite green (incl. new tests for the two new endpoints + intent-mismatch detection); ruff + mypy clean; vitest green including new CareerLineageSheet + CareerPickScreen + AskGemmaChips tests; Vite production build clean.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Reuse the existing `GET /branches/{soc}` endpoint** (defined in `backend/app/routers/branches.py:9` → `branch_tree.get_branches(soc)`) rather than proposing a new endpoint | The endpoint already exists, is already used by the `/reveal` gauntlet path, has a sync handler that `/build` wraps via `asyncio.to_thread`. No new API surface means no new architecture review burden and no schema changes. | (a) Build a new `/career-pick/branches/{soc}` with additional fields (e.g. pre-joined `career_transitions.rationale`) — rejected, premature. If we need more fields, enrich the existing endpoint in a follow-up spec. (b) Fetch branches eagerly at screen mount for every tier card — rejected, 10 SOCs × one MCP call each is wasted work and noisy `gemma.jsonl`-adjacent logs. Lazy-on-select is right. |
| 2 | **Bottom sheet is built with Framer Motion's `drag="y"` + `dragConstraints` + custom `onDragEnd` snap logic**, not a new library | Framer Motion is already a dep, already owns every animation on this project. Adding `vaul`, `react-spring-bottom-sheet`, or `@react-spring/web` introduces a second animation runtime + bundle weight for one component. The drag-to-snap math is ~25 lines. | (a) `vaul` (the shadcn-recommended sheet lib) — clean API but imports Radix primitives we otherwise don't use on this screen and it's a second motion runtime alongside Framer Motion. Rejected. (b) `react-spring-bottom-sheet` — abandoned upstream, last release 2022. Rejected. (c) shadcn `<Sheet>` — full-width slide-over pattern, not the 3-detent drag-to-resize we want. Rejected. |
| 3 | **Three detents: compact (~33 % of viewport), medium (~50 %), large (~85 %)** — no fully-closed state | The point of the sheet is to always show lineage context at pick time. "Closed" would mean a student on a small viewport has no indication the data exists. A compact detent that always shows the selected-career chip + first 2–3 branch chips keeps lineage ambiently visible without forcing them to engage. | (a) Four detents including fully-closed — rejected, removes the signal. (b) Two detents (compact + full) — rejected, missing the middle "I want to browse branches without covering my cards" state. (c) Free-form resize — rejected, iOS-sheet-style detents are the user's explicit ask and are more discoverable than a free slider. |
| 4 | **Sheet populates on click (not hover)** | Hover populate creates a network call storm as students mouse over cards to compare them. Click is an intentional "I want to know more about this one" gesture. Also works on touch where hover is meaningless. | (a) Populate on hover with 300 ms debounce — rejected, still causes flicker and doesn't match the intentionality. (b) Populate on both hover and click — rejected, redundant. |
| 5 | **Selecting a card for the build is still a separate action from populating the sheet** | A student should be able to browse lineage without committing. Design Vision must define the distinction clearly (e.g. primary "Pick this path" button inside a card vs. the click-to-populate). Current `/career-pick` already has `selectedSoc` + a "See my build" CTA; we preserve that separation. | Unifying click = select + populate — rejected, forces students to commit their build selection to see lineage and loses the "ambient comparison" that's the whole point. |
| 6 | **No new `buildStore` field.** Sheet state (current detent + currently-shown SOC) lives local to `CareerPickScreen` via `useState`. `selectedCareer` stays the one cross-screen contract | The sheet is UI-local. Promoting detent / shown-SOC to Zustand creates cross-screen coupling with no cross-screen consumer. | Promoting sheet state to `buildStore` — rejected per YAGNI. |
| 7 | **Existing `CareerTierSection` component already does the disclosure pattern correctly** (`aria-expanded`, `AnimatePresence` reveal, 2-col grid on tablet+). This spec **does not rewrite `CareerTierSection`** — it changes the *outer* layout in `CareerPickScreen.tsx` from 3-column-tiers-side-by-side to 1-column-tiers-stacked. | Cheapest change that meets the scope. The per-tier disclosure behavior is already shipping and already meets the spec's accessibility requirements. | Rewrite `CareerTierSection` with a new API — rejected, scope creep. |
| 8 | **Graduate-track paths (pre-med → MD → physician) are OUT OF SCOPE as data work, and largely OBVIATED for the hackathon demo by the Ask-Gemma chip** | The root pain point was student confusion, not missing data. Gemma can explain the undergrad/graduate distinction plainly and cite the real data on screen. Data-work to seed actual physician branches remains valuable long-term but is no longer on the hackathon critical path. | (a) Seed graduate branches now — rejected, out of scope for this spec, slower to ship, doesn't obviate the general "help me understand what I'm seeing" pattern that will recur on other screens. (b) Ignore the gap entirely — rejected, the "why don't I see doctor?" experience is a clear demo-killer. |
| 9 | **Chips only — no free-form chat input on `/career-pick`** | Free-form chat with a large language model exposed to high schoolers is a liability surface disproportionate to the value gained on this specific screen. Teens will type off-topic content; Gemma will try to answer; the demo will produce embarrassing transcripts. Canned chips give us 80 % of the insight value (the anticipated questions ARE the canonical ones for this screen) with ~0 % of the guardrail burden. | (a) Chat input with a guardrail system prompt — rejected, guardrail prompts are not reliable enough for a public demo and every chat turn is a new chance to go off-rails. (b) Chat input gated behind moderation (OpenAI moderation endpoint) — rejected, adds a second LLM dependency + cost + latency for marginal value. (c) Chips + optional free-form box at medium-trust schools only — rejected, complicates scope and the chip set already covers the expected question space. Free-form chat can land in a separate spec later (`feature-ask-gemma-freeform.md`) with proper moderation + refusal coverage. |
| 10 | **Chip set is delivered by the backend, not hardcoded in the frontend** | The auto-elevation heuristic (intent-mismatch detection between `major_text` and tiered SOCs) is Gemma-adjacent product logic that belongs on the server where it can evolve without a frontend deploy. The frontend just renders whatever `GET /career-pick/chips` returns, in the order returned. | Hardcode chips in React — rejected, makes auto-elevation a frontend concern, couples chip copy to frontend releases, and duplicates the graduate-intent pattern list in two places. |
| 11 | **Every chip click is one non-streaming `gemma_client.generate_async` call** — no streaming on `/career-pick/ask` | Streaming SSE was explicitly rejected for `/build` in the reveal-loading-screen perf spec (Decision #6 in `docs/specs/completed/perf-reveal-loading-screen.md`) on the same grounds: streaming adds a state machine, an SSE endpoint, and an EventSource on the frontend for marginal perceived-latency value on short responses. 4–6 sentences is short enough that non-streaming feels fine. | Streaming SSE — rejected. Reuse the already-landed `generate_async` + semaphore infrastructure. |

### Constraints

- Framer Motion already a project dependency — no new animation libraries.
- Brightpath design system (see `DESIGN.md`) is the only token source. Any net-new motion preset or spacing token needed for the sheet (e.g. `detent.compact`, `detent.medium`, `detent.large`, `sheetSnap` spring) must be authored into `frontend/src/styles/motion.ts` as part of §3 Design Vision, not invented ad-hoc at implementation time.
- Reduced-motion (`prefers-reduced-motion: reduce`) must degrade drag + snap animations but keep functional state changes (snap still happens instantly).
- Keyboard equivalence required: every drag gesture must be operable via chevron buttons / arrow keys. No exceptions — the primary demo audience includes screen-reader users.
- No regression in the existing `/career-pick` → `/reveal` flow: `buildStore.selectedCareer` stays the single handoff contract, and the `RevealScreen` perf work (see `docs/specs/completed/perf-reveal-loading-screen.md`) is untouched.
- No free-form text input to Gemma anywhere on `/career-pick`. Chip-click is the only Gemma-call entry point on this screen.
- All Gemma calls go through the already-landed `gemma_client.generate_async` (semaphore-capped, thread-safe JSONL append, OpenAI-compatible API). No new Gemma call path.
- `CIPCODE` is always string per `CLAUDE.md` — the new Pydantic models carry it as `str` (never `float`).

### Out of Scope (future specs)

- **`feature-ask-gemma-freeform.md`** — free-form text input for asking Gemma anything on `/career-pick` (and potentially elsewhere). Requires a guardrail system prompt, an input-moderation pass (OpenAI moderation endpoint or similar), off-topic refusal coverage, and a reviewed transcript-capture plan. Not a hackathon blocker. Spec this after the chip row proves out which questions students actually ask.
- **`feature-graduate-track-branches.md`** — seed `consumable.career_branches` with professional-school jumps (pre-med → MD, pre-law → JD, pre-vet → DVM, MBA ladders, etc.) so graduate-track students see the terminal occupation as an actual node on the lineage flow. Data-work spec. De-prioritized from the hackathon critical path now that the chip handles student confusion (§2 Decision #8). Still valuable long-term.
- **Ask-Gemma chips on other screens** (e.g. gauntlet, reveal) — out of scope; this spec is `/career-pick` only. If the pattern works here, we'll port it in a follow-up.
- **Inline lineage on `CareerCard` itself** — a mini-preview of the next-hop titles directly on the card, no sheet needed. Possibly redundant with the sheet; revisit after student testing.
- **Lineage sheet on other screens** (e.g. the gauntlet screen) — out of scope; this spec is `/career-pick` only.
- **Changes to how cards are tiered into Common / Less Common / Stretch** — `career_tiering` service logic is untouched.

---

## §3 UI/UX Design

**Status:** APPROVED — see content below.

### Emotional Target

Two feelings, layered:

1. **Orientation, not overwhelm.** The student just landed on a screen with eight-plus career paths and no map. The tier layout gives them a calm ladder — Common feels within reach, Stretch feels aspirational, Less Common fills the middle. Stacking tiers vertically (instead of three side-by-side columns) says "take your time, there's no race."
2. **A telescope, not a glossary.** The lineage sheet gives them a second instrument. They tap a card, and the sheet quietly lights up a five-year arc from that job. They don't have to commit to see. The horizontal flow — chip → connector → chip → chip → chip — reads like the first frame of the branch tree they'll eventually meet on `/reveal`. This screen becomes the place where students first *discover that lineage exists at all.*

When the elevated chip pulses at the top of the sheet ("Why don't I see 'doctor'?"), Gemma isn't answering a question — Gemma is anticipating one. That tiny pulse is the screen reading the student's mind. That's the demo moment.

### 3.1 Page Layout

The header region, `PageContainer`, profile chip, eyebrow ("CHOOSE YOUR PATH"), H1, and subhead are **unchanged**. Only the tier region and CTA chrome change. The sheet is a new layer anchored to the bottom of the viewport.

**Viewport math.** The sheet is positioned `fixed` to the viewport bottom with its height driven by detent vh constants (§3.4). Because the sheet is fixed, the document scroll continues to own the tier cards above it — a student can scroll tier content independently of the sheet. Critically, the tier region must reserve bottom padding equal to the **compact** detent height plus a one-gutter breathing margin, so the last tier is never hidden beneath the sheet at rest. Reservation values go on `CareerPickScreen` as `pb-[calc(33vh+var(--space-6))]` at desktop and `pb-[calc(45vh+var(--space-6))]` at mobile (see §3.5).

```
┌──────────────────────────────────────────────────────────────────┐
│  [Header: profile chip · eyebrow · H1 · subhead]                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▾ Common  (5 paths)              — description row       │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐│   │
│  │  │ Financial Analyst       │  │ Budget Analyst          ││   │
│  │  │ $76k · ERN+++ · GRW+    │  │ $82k · ERN++ · GRW+     ││   │
│  │  └─────────────────────────┘  └─────────────────────────┘│   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐│   │
│  │  │ Credit Analyst          │  │ Market Research Analyst ││   │
│  │  └─────────────────────────┘  └─────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▾ Less Common  (3 paths)                                 │   │
│  │   … 2-col grid …                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ▸ Stretch  (2 paths) — collapsed                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│       [ See my build ✦ ]  (primary CTA, centered)                │
│                                                                  │
├══════════════════════════════════════════════════════════════════┤  ← sheet
│   ═══  (drag handle)                                        ˄ ˅  │
│   WHERE THIS CAREER LEADS  · Financial Analyst · (Gemma idle)    │
│  ┌──────────────┐  →  ┌──────────────┐  ┌─────────────┐  …        │
│  │ Financial    │     │ Portfolio    │  │ CFO         │          │
│  │ Analyst      │     │ Manager      │  │ ERN +++     │          │
│  │ (you are     │     │ ERN++ GRW+   │  │ "10+ yrs"   │          │
│  │  here)       │     └──────────────┘  └─────────────┘          │
│  └──────────────┘                                                │
│  Not sure about something? Ask Gemma.                            │
│  [◎ Why don't I see 'doctor'?]  [What does this do?]  [ROI?]  …  │
└──────────────────────────────────────────────────────────────────┘
```

**Grid + spans (12-col Brightpath grid, per DESIGN.md §Grid System).**

| Region | Mobile (<768) | Tablet (768–1199) | Desktop (≥1200) |
|--------|---------------|-------------------|-----------------|
| Header block | `col-span-12` | `col-span-12` | `col-span-12` |
| Tier sections (outer wrapper) | `col-span-12`, 1 section per row | `col-span-12`, 1 section per row | `col-span-12`, 1 section per row — **not** 3-up |
| Each tier's inner card grid | `grid-cols-1` | `grid-cols-2` | `grid-cols-2` |
| Sheet | `fixed inset-x-0 bottom-0`, full-bleed (ignores grid) | same | same |
| "See my build" CTA | inline below tiers, inside `PageContainer` | inline below tiers | inline below tiers |

Note the divergence from today's code: the existing screen puts the three tiers in a `desktop:grid-cols-3` row and uses a mobile-only fixed-bottom CTA. In the new layout the tiers are **always stacked** (outer container is `grid-cols-1` at every breakpoint) and the CTA is always **inline** below the tier region — never fixed. The fixed layer belongs to the sheet.

**"See my build" CTA visibility across detents.**

| Detent | CTA behavior |
|--------|--------------|
| compact (≈33vh desktop) | CTA is visible. The tier region reserves a compact-height-plus-gutter bottom pad; the CTA sits at the bottom of the document content and is always above the sheet's top edge. |
| medium (≈50vh desktop) | CTA may be covered as the sheet rises. This is acceptable — at medium the student is studying lineage, not committing. We do **not** shift the CTA. |
| large (≈85vh desktop) | CTA is definitionally hidden. Also acceptable — large detent means the student is deep in lineage and not yet committing (spec success criteria). When the sheet collapses back to medium or compact, the CTA re-appears. |

**Z-index stack.**

| Layer | z-index | Notes |
|-------|---------|-------|
| Page body / tier cards | 0 | Default document flow. |
| "See my build" CTA | 10 | Lifts it above the ambient glow layer. |
| Application Header | 100 | Existing chrome, unchanged. |
| `CareerLineageSheet` root | 40 | Above document body, below app header. Header stays visible and tappable at every detent. |
| Sheet's drag handle + chevrons | 41 | Relative to the sheet itself — not a separate global layer. Kept above the sheet's own inner-scroll content so it's never occluded. |

**Sheet shell tokens.**

- Position: `fixed inset-x-0 bottom-0`
- Background: `bg-bp-mid` (`#232545`) — same elevation family as a card
- Top border: `1px solid border-default` (`rgba(255,255,255,0.1)`). No left/right/bottom border — the sheet meets the viewport edges
- Border radius: `rounded-t-[20px]` (Brightpath `radius-xl`), zero bottom radius
- Shadow: `shadow-lg` (`0 8px 32px rgba(27, 29, 48, 0.7)`) cast **upward** via negative y. Implementation: `shadow-[0_-8px_32px_rgba(27,29,48,0.7)]`
- Ambient insight wash: layered `box-shadow: inset 0 40px 80px -40px rgba(184, 169, 232, 0.12)` to echo Gemma's color family and distinguish the sheet visually from a plain card

### 3.2 CareerLineageSheet — Structure

The sheet is a single `motion.div` with five vertically-stacked zones:

```
┌────────────────────────────────────────────────────────────────┐
│  Zone 1 — Handle row          (h: 40px, centered drag pill)    │
│             ┌───────┐                                   ˄ ˅    │
│             └───────┘                                          │
├────────────────────────────────────────────────────────────────┤
│  Zone 2 — Title row           (py-3, eyebrow + title)          │
│  WHERE THIS CAREER LEADS                                       │
│  Financial Analyst       ⟡ Gemma is loading branches…           │
├────────────────────────────────────────────────────────────────┤
│  Zone 3 — Lineage flow        (h: fills, horizontal scroll)    │
│  [career ▸] → [branch 1] [branch 2] [branch 3] …                │
├────────────────────────────────────────────────────────────────┤
│  Zone 4 — Ask-Gemma chip row  (always visible at every detent) │
│  Not sure about something? Ask Gemma.                          │
│  [● Why don't I see 'doctor'?]  [What does this do?]  [ROI?]    │
├────────────────────────────────────────────────────────────────┤
│  Zone 5 — Ask-Gemma response card  (appears medium+ only)      │
│  ⟡ Gemma: Biology is the standard pre-med path…                 │
│                                      [↻ Regenerate]  [✕ Close] │
└────────────────────────────────────────────────────────────────┘
```

**Outer sheet container specs.**

| Property | Value |
|----------|-------|
| Padding | `px-6 tablet:px-8` horizontal; `pb-6` bottom. Top padding is driven by the handle zone's own 40px height. |
| Overflow | `overflow-y-hidden` on the sheet root. Inner zones manage their own scroll. |
| Inner column | A single flex column with `gap-3 tablet:gap-4` between zones. |
| Width | Full viewport width at every breakpoint. |

**Zone 1 — Drag handle row (h: 40px).**

The handle is a **horizontal pill** centered top:

| Property | Value |
|----------|-------|
| Size | `w-10 h-1` (40px × 4px) |
| Color (idle) | `bg-text-muted` at 40% opacity (`rgba(138, 133, 149, 0.4)`) |
| Color (hover) | `bg-text-secondary` at 60% opacity |
| Color (focus-visible) | Adds a 3px `box-shadow` ring using `--color-focus-ring` (`rgba(123, 184, 224, 0.4)`) and brightens the pill to `bg-text-secondary` 80% |
| Color (dragging) | `bg-accent-thrive` at 80% opacity — the "engaged" tell |
| Radius | `rounded-full` |
| Hit target | Parent `<div role="slider">` is `w-full h-10` (40px tall) — the pill is visual, the whole bar is clickable/draggable/focusable. This preserves the iOS affordance while giving us a 40px minimum hit area for touch + keyboard users. |
| Keyboard focus | `tabIndex={0}`; focus ring on the **bar**, not on the pill |
| Optional ambient pulse | See `handlePulse` preset in §3.4. Disabled when `prefers-reduced-motion: reduce`. Optional — implementer may ship v1 without and add later. If included, it's a 2.2s opacity breathe on the pill only, never on the focus ring. |

**Chevron buttons (top-right of Zone 1, vertically centered to handle row).**

| Property | Value |
|----------|-------|
| Layout | Stacked pair, 4px gap, positioned `absolute right-4 top-1/2 -translate-y-1/2` relative to Zone 1 |
| Size each | 32px × 32px — circular (`rounded-full`) |
| Background | `bg-bp-surface` (`#2D3060`) |
| Hover background | `bg-bp-raised` (`#3A3D75`) |
| Icon | 16px chevron, `text-text-secondary` (idle) → `text-text-primary` (hover). Lucide `ChevronUp` / `ChevronDown`, 2px stroke |
| Disabled | When at limit detent: icon `text-text-muted`, background `bg-bp-surface/50`, `cursor-not-allowed`, no hover. `aria-disabled="true"`. Still keyboard-focusable so screen readers announce the limit. |
| Press | `whileTap={{ scale: 0.92 }}` + `springs.snappy` |
| Aria | Up chevron: `aria-label="Raise lineage panel"`. Down chevron: `aria-label="Lower lineage panel"`. |

**Zone 2 — Title row.**

Two lines:

| Element | Typography | Color |
|---------|-----------|-------|
| Eyebrow | `font-data text-micro font-bold uppercase tracking-[2px]` — matches DESIGN.md "Section Labels" | `accent-info` (`#7BB8E0`) |
| Career title | `font-body text-subheading font-bold` (22px/1.375rem, weight 700) | `text-text-primary`. While branches are loading, the title keeps full opacity — only the inline GemmaThinking mark signals in-flight. |
| Inline loader | Reuse `GemmaThinking` component from `components/ui/GemmaThinking.tsx`. Flex-aligned to the right of the title with `gap-3`. Only rendered while the branch fetch is in flight. On resolve, fades out per the spec's 250ms `duration: 0.25, ease: "easeIn"` exit pattern. |

Title row carries `aria-live="polite"` on the title `<h2>`. When `soc` prop changes and the new title resolves, the screen reader announces "Where this career leads — Financial Analyst."

**Zone 3 — Lineage flow area.**

Horizontal row of three element types, left-to-right, rendered in a flex row inside a horizontally-scrolling container:

```
[selected career chip] [connector ▸] [BranchChip 1] [BranchChip 2] [BranchChip 3] ...
```

| Property | Value |
|----------|-------|
| Container | `flex items-stretch gap-4 overflow-x-auto overflow-y-hidden py-2 snap-x snap-mandatory scroll-pl-6 scroll-pr-6` |
| Scrollbar | Custom: `scrollbar-thin` with `scrollbar-thumb: var(--color-bg-raised)`, `scrollbar-track: transparent`. On WebKit: `::-webkit-scrollbar { height: 6px }`. |
| Scroll snap | Each chip is `snap-start`. When the student scrolls horizontally, chips settle into view cleanly. |
| Left inset | `pl-6 tablet:pl-8` so the "you are here" chip doesn't crowd the sheet edge. |
| Right inset | `pr-6 tablet:pr-8` with a 24px fade-out mask via a `mask-image: linear-gradient(to right, black 92%, transparent)` so overflow is visually suggested, not cut hard. |
| Empty state | When `soc` is null, replace the row with a centered empty panel: `font-body text-body text-text-muted italic` reading "Pick a career path above to see where it leads." Panel is `py-8 px-6`, no border, just centered text. |

**Selected-career chip ("you are here").**

This is a distinct visual element from a `BranchChip` — it's the anchor, styled so the student's eye knows "this is the root":

| Property | Value |
|----------|-------|
| Size | `min-w-[180px] max-w-[220px] h-auto` — intrinsic height. |
| Background | `bg-bp-surface` with inset accent-thrive gradient: `linear-gradient(135deg, rgba(125,212,163,0.10) 0%, transparent 60%)` |
| Border | `1px solid rgba(125, 212, 163, 0.35)` — thrive at 35%. Left edge adds a 3px thrive accent stripe (`border-l-[3px] border-l-accent-thrive`) — same "this is yours" pattern used on the Gemma Match Card. |
| Radius | `rounded-xl` (20px) |
| Padding | `p-4` |
| Content | eyebrow "YOU ARE HERE" (`font-data text-micro font-bold uppercase tracking-[2px] text-accent-thrive`) + career title (`font-body text-body font-bold text-text-primary`, 2-line clamp) + salary (`font-data text-data-sm text-text-secondary`) |
| Shadow | `shadow-glow-thrive` at 15% — a persistent quiet halo |

**Connector glyph.**

A minimal arrow between the anchor and the first branch:

- 24px wide, vertically centered on the row
- Rendered as an inline SVG: a 16px `ChevronRight` icon (Lucide, 2px stroke) tinted `text-text-muted`, with a 1px horizontal rule extending 6px on either side at `rgba(255,255,255,0.08)`. Aria: decorative, `aria-hidden="true"`.
- Between branch chips (not between the anchor and branch chip 1), no connector — branches sit in a flex-gap row. The connector only appears once, after the anchor.

**BranchChip (one branch card).**

Rendered per `CareerBranch`:

| Property | Value |
|----------|-------|
| Size | `min-w-[220px] max-w-[260px]` — wider than anchor so deltas can breathe. Height driven by content. |
| Background | `bg-bp-mid` (`#232545`) |
| Border | `1px solid border-subtle` (`rgba(255,255,255,0.06)`) |
| Hover border | `border-default` (`rgba(255,255,255,0.1)`) |
| Radius | `rounded-xl` |
| Padding | `p-4` |
| Shadow | `shadow-md` default; hover adds `shadow-lg` |
| Hover transform | `translateY(-2px)` — matches DESIGN.md card hover |

Content stack (vertical):

1. **Title.** `font-body text-body font-bold text-text-primary`, 2-line clamp. (e.g. "Portfolio Manager")
2. **Stat delta pills row.** `flex flex-wrap gap-1.5 mt-2`. One pill per non-zero `delta_*` field (zeros suppressed — BranchChip test P2). Each pill uses the stat's own color as background at 15% opacity and the stat color for text, following DESIGN.md Pills pattern. Content format: `ERN +++`, `GRW ++`, `RES -` — the `+` / `-` count encodes magnitude per 1-unit-per-symbol, capped at `+++` / `---`. Typography: `font-data text-data-sm font-bold`.
3. **Rationale.** When present, `font-body text-small text-text-secondary italic mt-2`. Two-line clamp. When absent, omit entirely (BranchChip test P2).

**Chip entrance.** When the branches resolve, BranchChips enter with `staggerContainer(0, stagger.fast)` + `staggerItem` — 50ms apart, fade-up from y:12. The anchor chip is present immediately (no stagger) so the "you are here" feels grounded and the new branches light up after it.

**Horizontal scroll behavior.** When branches exceed viewport width, the row scrolls horizontally. Scroll is ambient — no visual affordance beyond the right-edge fade-mask. Touch: native horizontal swipe. Pointer: trackpad horizontal or shift+scroll; mouse-wheel vertical is captured by the page, not the row, so vertical scrolling doesn't hijack the page while the student's pointer hovers the sheet. Keyboard: row container is `tabIndex={-1}`; individual BranchChips are focusable (`tabIndex={0}`, `role="article"`), and focus cycling advances through chips, auto-scrolling the focused chip into view via `scrollIntoView({ behavior: "smooth", inline: "nearest" })`.

**Empty / loading / error states.**

| State | Treatment |
|-------|-----------|
| Empty (`soc === null`) | Zone 3 renders only the centered "Pick a career path above to see where it leads." copy. Zone 2 renders the eyebrow; title is "—" in `text-text-muted`. Zones 4 + 5 still render (the chip row is always present; clicking a chip pre-selection is allowed — the chip's context just omits `selected_soc`). |
| Loading | Zone 3 keeps the anchor chip visible (if we already know which SOC was clicked) and replaces the branch row with a single centered `GemmaThinking` message "Gemma is loading branches…". Zone 2's inline `GemmaThinking` mark is also visible. |
| Error | Zone 3 renders an inline error panel: an `accent-alert`-tinted card (background `var(--color-state-error)`, border `rgba(244,169,126,0.35)`, radius `radius-lg`, padding `p-4`). Copy: "Couldn't load the lineage. Try again?" (`font-body text-body text-text-primary`). Right-aligned "Try again" button follows the **Secondary** button spec (`accent-info` text, transparent background, 44px height). Retry button fires the same `getBranchesForSoc(soc)` call. |

### 3.3 Ask-Gemma Chip Row + Response Card

**Placement at each detent.**

The chip row (Zone 4) is **always rendered** regardless of detent. The response card (Zone 5) is rendered only when (a) the sheet is at medium or large detent AND (b) a chip is active.

| Detent | Zone 4 visible? | Zone 5 visible? | Notes |
|--------|-----------------|-----------------|-------|
| compact (≈33vh) | Yes | No | Zone 3 (lineage) + Zone 4 (chips) compete for vertical space. Zone 3 shrinks to ~120px (enough for one row of chips + anchor vertically clipped). Zone 4 stays fixed at ~72px. Clicking a chip at compact **auto-promotes** the sheet to medium via `onDetentChange("medium")` so the response card has room (CareerLineageSheet test P0 "chip click auto-promotes compact detent to medium"). |
| medium (≈50vh) | Yes | Yes when active | Zone 3 gets the majority of the added room; Zone 5 renders below Zone 4 with a max-height of `~160px` and internal scroll. |
| large (≈85vh) | Yes | Yes when active, with generous room | Zone 5 expands to fill up to `~360px`; Zone 3 + Zone 5 coexist comfortably. |

**Hint line (above chip row).**

Before any chip has been clicked: `font-body text-small text-text-muted italic pl-6`, copy: "Not sure about something? Ask Gemma." Once any chip has been clicked during the session, this line is replaced with a thinner affordance: a 14px `GemmaStar` + `font-small text-text-muted` reading "Ask another question." (`pl-6`, `flex items-center gap-2`). The tonal shift signals the student has engaged and now the experience is hinting at repeat use.

**Chip pill style (base, non-elevated).**

Leverages the existing Brightpath pill spec (DESIGN.md §Pills / Badges) as the base recipe — the Ask-Gemma chip is a larger, interactive variant:

| Property | Value |
|----------|-------|
| Display | `inline-flex items-center gap-2` |
| Padding | `px-4 py-2` (larger than standard pill — these are tappable) |
| Font | `font-body text-small font-semibold` (14px weight 600) |
| Color (idle) | Background `rgba(123, 184, 224, 0.10)` (accent-info at 10%), text `accent-info`, 1px border `rgba(123,184,224,0.22)` |
| Radius | `rounded-full` |
| Hover | Background `rgba(123,184,224,0.18)`, border `rgba(123,184,224,0.35)`, cursor pointer |
| Active (chip is the current response target) | Background `rgba(123,184,224,0.22)`, text `text-text-primary`, border `rgba(123,184,224,0.6)`, adds `shadow-glow-info` at reduced intensity (`0 0 14px rgba(123,184,224,0.25)`). The active chip *glows gently* to tell the student "this is the answer you're reading." |
| Press | `whileTap={{ scale: 0.96 }}` + `springs.snappy` |
| Focus-visible | 3px ring using `--color-focus-ring` (info at 40%) |
| Keyboard | `role="button"`, `tabIndex={0}`, Enter/Space activate (test P0) |

Icon prefix (optional, per chip): when the chip carries a `terminal_title` or otherwise represents a "missing thing" question, render a 14px Lucide `HelpCircle` icon at the left, `text-accent-info`. For generic chips (no terminal_title), no icon — keeps the row visually calm.

**Elevated chip treatment ("Why don't I see 'doctor'?").**

Same shape and size as a base chip, but the palette swaps entirely to `accent-alert`:

| Property | Value |
|----------|-------|
| Background (idle) | `rgba(244, 169, 126, 0.15)` |
| Border | `1px solid rgba(244, 169, 126, 0.45)` |
| Text | `accent-alert` (`#F4A97E`) |
| Icon prefix | Filled 14px dot (`●`, render as a `<span>` with background `accent-alert`, `w-2 h-2 rounded-full`) — the "this is elevated" tell. Not a HelpCircle; the dot is a *status* signal. |
| Glow | `shadow-glow-alert` at 30% (`0 0 16px rgba(244,169,126,0.22)`) even when idle — it's always lit |
| Pulse | `elevatedChipPulse` preset (§3.4) — the glow breathes on a 2.4s cycle. Opacity of the shadow ramps 0.22 → 0.38 → 0.22. Disabled under reduced-motion. |
| Order | Always first in DOM order. Comes with a left margin on the following sibling (`gap-3`) so it visually separates from the base chip cluster. |

The elevated chip carries `aria-describedby={elevationHintId}` pointing to a visually-hidden `<span>` inside the sheet: `"Gemma thinks this question might be relevant based on what you searched for."` (`sr-only` Tailwind class). Screen-reader users hear that hint the moment they focus the chip.

**Chip-active visual state.**

At most one chip is active at a time. When a student clicks a chip, it locks into the Active style described above. Previously-active chip (if any) reverts to idle. The response card beneath re-fetches and replaces in place (CareerLineageSheet test P0 "switching chips replaces the response card"). There is **no** animation between chip-active swaps on the chips themselves — the glow simply moves. The response card, however, cross-fades: 180ms fade-out → 220ms expand-in (`chipResponseExpand` preset, §3.4).

**Response card (Zone 5) layout.**

```
┌──────────────────────────────────────────────────────────────┐
│  ✦ Gemma                                                     │  ← attribution row
│  Biology is the standard pre-med path — Gemma matched your   │  ← body copy
│  "pre-med" to Biology and it IS the right major if you want │
│  to apply to medical school later. Physician doesn't show    │
│  up here because our data tracks your first job out of       │
│  college, and to become a physician you typically need four  │
│  more years of medical school after your bachelor's.         │
│                                                              │
│                              [ ↻ Regenerate ]  [ ✕ Close ]   │  ← action row
└──────────────────────────────────────────────────────────────┘
```

| Property | Value |
|----------|-------|
| Container | `bg-bp-surface` (`#2D3060`), `rounded-xl`, `p-5 tablet:p-6`, `border-l-[3px] border-l-accent-insight` — echoes the Gemma Match Card pattern (left-edge insight stripe). |
| Position | Directly below the chip row with `mt-3`. Width fills sheet horizontal content area. |
| Max height | `max-h-40` at medium, `max-h-[360px]` at large. `overflow-y-auto` for scroll when Gemma's answer runs long. |
| Attribution row | `flex items-center gap-2 mb-3`. `GemmaStar` (14px) + "Gemma" in `font-body text-small text-text-secondary font-semibold`. |
| Body copy | `font-body text-body text-text-primary`, `leading-relaxed` (1.6). Rendered as plain text (Gemma system prompt forbids markdown). |
| Action row | `flex justify-end gap-2 mt-4`. |
| Regenerate button | Ghost variant (DESIGN.md §Buttons) — `h-10 px-4 rounded-lg`, `font-body font-bold text-small`, `text-accent-info`, transparent background. Prefix with 14px `RotateCcw` Lucide icon. Label: "Regenerate". Hover brightens to `text-text-primary` + background `rgba(255,255,255,0.05)`. |
| Close button | Icon-only. `w-8 h-8 rounded-full bg-bp-surface text-text-secondary`. 14px `X` icon. Hover: `bg-bp-raised`, text `text-text-primary`. Aria: `aria-label="Close answer"`. |
| Loading state | Body region replaced by `<GemmaThinking message="Gemma is answering…" />` centered. Regenerate + Close remain visible but `disabled` (opacity 50%). |
| Entrance | `chipResponseExpand` preset — height animates from 0 to auto alongside opacity 0 → 1. Uses `AnimatePresence` + Framer's height animation. 220ms with `springs.smooth`. |
| Exit (close or chip-swap) | 180ms fade + shrink: `{ opacity: 0, height: 0, transition: { duration: 0.18, ease: "easeIn" } }`. |
| Aria | `role="region" aria-live="polite" aria-label="Gemma answer"`. Announces the full answer text when it lands. |

**Response-replaces-on-new-chip rule.** When the student clicks a different chip while a response is rendered, the existing response card does **not** unmount → remount. It stays mounted and its inner content transitions: body fades out (180ms), `GemmaThinking` replaces it, new answer fades in (220ms). This keeps the card from jumping in size and preserves scroll position / focus. Tested explicitly (CareerLineageSheet test P0 "switching chips replaces the response card").

### 3.4 Motion Specifications

All values below are **named presets to be added to `frontend/src/styles/motion.ts`** during implementation. Each entry lists the exact config + the reduced-motion degradation. The implementer lands these verbatim.

**New presets to author in `motion.ts`:**

```ts
// ============================================================
// SHEET DETENTS (CareerLineageSheet)
// ============================================================

/**
 * Detent heights as fractions of the viewport.
 * Desktop + tablet use the standard values; mobile uses larger compacts
 * so the chip row + title row stay legible on small viewports.
 */
export const sheetDetent = {
  compact: { desktop: 0.33, tablet: 0.33, mobile: 0.45 },
  medium:  { desktop: 0.50, tablet: 0.50, mobile: 0.60 },
  large:   { desktop: 0.85, tablet: 0.85, mobile: 0.88 },
} as const;

/**
 * Snap spring used by CareerLineageSheet when dragging ends and the
 * sheet resolves to a detent. Tuned for "confident thunk" — fast enough
 * to feel deliberate, damped enough to not overshoot an iOS-style sheet.
 */
export const sheetSnap = {
  type: "spring" as const,
  stiffness: 420,
  damping: 42,
  mass: 0.9,
  restDelta: 0.5,
} as const;

/**
 * Drag elasticity — resistance past the compact/large limits.
 * 0.12 means the sheet follows the finger at 12% of the overshoot.
 * Below 0.1 feels walled-off; above 0.2 feels loose.
 */
export const sheetDragElastic = 0.12;

/**
 * Velocity threshold that promotes a drag-end to the "next" detent
 * even if the student didn't cross the midpoint.
 * Units: px/s (Framer Motion pan velocity). ±600 ≈ a moderate flick.
 */
export const sheetFlingVelocity = 600;

// ============================================================
// CHIP ROW + RESPONSE CARD (CareerLineageSheet)
// ============================================================

/**
 * Response card expand/collapse. Uses a custom spring so the height
 * animation doesn't feel like a CSS transition — it has real physics.
 */
export const chipResponseExpand = {
  initial: { opacity: 0, height: 0 },
  animate: { opacity: 1, height: "auto" },
  exit:    { opacity: 0, height: 0 },
  transition: {
    opacity: { duration: 0.22, ease: "easeOut" as const },
    height:  { type: "spring" as const, stiffness: 260, damping: 30 },
  },
} as const;

/**
 * Elevated-chip ambient pulse. The chip's shadow opacity breathes.
 * Stateful: applied via an `animate` array on the motion component.
 * Period = 2.4s, peak at t=1.2s.
 */
export const elevatedChipPulse = {
  animate: {
    boxShadow: [
      "0 0 14px rgba(244, 169, 126, 0.22)",
      "0 0 22px rgba(244, 169, 126, 0.38)",
      "0 0 14px rgba(244, 169, 126, 0.22)",
    ] as string[],
  },
  transition: {
    duration: 2.4,
    ease: "easeInOut" as const,
    repeat: Infinity,
  },
} as const;

/**
 * Optional idle ambient pulse on the drag handle pill.
 * OPTIONAL — implementer may ship v1 without. If included, 2.2s cycle.
 */
export const handlePulse = {
  animate: { opacity: [0.4, 0.65, 0.4] as number[] },
  transition: {
    duration: 2.2,
    ease: "easeInOut" as const,
    repeat: Infinity,
  },
} as const;
```

**Reduced-motion degradations** (per preset; gate at consumer, not inside `motion.ts`):

| Preset | Under `prefers-reduced-motion: reduce` |
|--------|----------------------------------------|
| `sheetSnap` | Replace with `{ duration: 0, ease: "linear" }` so the detent change is instant but state still updates (CareerLineageSheet test P1 "reduced-motion user gets instant detent change"). |
| `sheetDragElastic` | Set to `0` — drag doesn't rubber-band past limits. |
| `sheetFlingVelocity` | Unchanged — resolution logic still respects fling, it just lands instantly. |
| `chipResponseExpand` | Replace spring with `{ duration: 0.12, ease: "linear" }`; height animation still occurs (instant collapse feels broken), opacity fades on the attenuated timing. |
| `elevatedChipPulse` | Skip the `animate` prop entirely — chip gets the static high-state glow `0 0 16px rgba(244,169,126,0.30)` instead of the breathe cycle. |
| `handlePulse` | Skip the `animate` prop entirely — handle stays at idle opacity 0.4. |
| Branch chip entrance stagger (reuse existing `stagger.fast` + `staggerItem`) | No change — `staggerItem` uses `springs.smooth`, which Framer Motion already honors when `useReducedMotion()` returns true (springs shortcut to a 0-duration tween). Consumer does not need to special-case. |

**Stagger reuse.** The horizontal row of BranchChips uses `staggerContainer(0, stagger.fast)` + `staggerItem` already in `motion.ts`. No new stagger preset needed.

### 3.5 Responsive Behavior

| Breakpoint | Tier grid | Sheet detents | Chevron visibility | Hit targets |
|------------|-----------|---------------|--------------------|-------------|
| Mobile <768 | 1-col card grid inside each tier | compact 45vh / medium 60vh / large 88vh | Chevrons render full-size (32px). Drag is primary; chevrons are the a11y fallback. | All interactive elements ≥44px per touch guidelines. Drag handle bar remains 40px but with a 4px vertical `padding` to reach 44px effective hit. |
| Tablet 768–1199 | 2-col card grid | compact 33vh / medium 50vh / large 85vh | Chevrons full size | Default |
| Desktop ≥1200 | 2-col card grid | compact 33vh / medium 50vh / large 85vh | Chevrons full size | Default |

**Mobile specific notes:**

- Tier region bottom padding: `pb-[calc(45vh+var(--space-6))]` so the last tier card clears the taller compact detent.
- Chip row stays horizontal-scroll if it overflows (same behavior as desktop — don't wrap).
- Response card `max-height` tightens to `max-h-[220px]` at medium (vs. 160px desktop — mobile has less vertical budget and a longer read is helpful) and `max-h-[440px]` at large.
- The inline `GemmaThinking` mark in Zone 2 stacks below the title on mobile (title + mark in a `flex-col` instead of `flex-row`) so the title doesn't truncate.

**No new breakpoints.** Everything uses the existing Brightpath `mobile:`/`tablet:`/`desktop:` prefixes (DESIGN.md §Breakpoints).

### 3.6 Accessibility

**Sheet container** (`<div>` wrapping the full sheet):

- `role="dialog"` + `aria-modal="false"` — persistent peek, not blocking.
- `aria-label` updates with detent: `"Lineage panel — compact"`, `"Lineage panel — medium"`, `"Lineage panel — expanded"` (copy: "compact" / "medium" / "expanded" — "expanded" reads more naturally than "full" or "large" for screen readers).
- `aria-describedby` points to the title `<h2>` so screen readers hear the current career when they enter the dialog.

**Drag handle bar** (the focusable `<div>` that wraps the visual pill):

- `role="slider"`, `aria-orientation="vertical"`, `aria-valuemin={0}`, `aria-valuemax={2}`, `aria-valuenow={0|1|2}` (compact=0, medium=1, large=2).
- `aria-valuetext="compact"` / `"medium"` / `"expanded"` — human-readable, read by screen readers in place of the numeric valuenow.
- `aria-label="Lineage panel height — drag or use arrow keys to resize"`.
- `tabIndex={0}`, focus-visible ring per DESIGN.md focus token.
- Keyboard handlers: `ArrowUp` / `ArrowDown` cycle through detents (CareerLineageSheet test P0 "ArrowUp / ArrowDown on handle cycles detents"). `Home` → compact. `End` → large. `PageUp` / `PageDown` behave same as arrow keys.

**Chevron buttons**:

- `aria-label="Raise lineage panel"` / `aria-label="Lower lineage panel"`.
- `aria-disabled="true"` when at limit detent — still focusable so screen-reader users hear the disabled state.

**Title region** (`<h2>` in Zone 2):

- `aria-live="polite"` + `aria-atomic="true"`.
- Updates when `soc` prop changes (CareerLineageSheet test P1 "aria-live title announces on SOC change").

**Chip row**:

- Row container: `role="group" aria-label="Ask Gemma about this screen"`.
- Each chip: `role="button"`, `tabIndex={0}`, Enter/Space activation.
- Elevated chip: `aria-describedby={elevationHintId}`; a visually-hidden `<span id={elevationHintId} className="sr-only">Gemma thinks this question might be relevant to you based on what you searched for.</span>` lives adjacent to the row.
- Focus order: elevated chip first (it's first in DOM), then base chips in order returned by the API.

**Response card**:

- `role="region"`, `aria-live="polite"`, `aria-label="Gemma answer"`.
- When the answer text lands, screen readers announce it (CareerLineageSheet test P1 "aria-live title announces…" — paired behavior on the response card).
- Regenerate button: `aria-label="Regenerate answer"`. Close button: `aria-label="Close answer"`.

**Reduced motion**:

- Consumer components call `useReducedMotion()` from Framer Motion and gate the presets per §3.4 table.
- Functional state changes (detent resolution, chip activation, response-card mount/unmount) still happen — only the animation is attenuated.

**Focus management on sheet**:

- The sheet is non-modal. Focus is NOT trapped inside the sheet.
- Tab order: drag handle → up chevron → down chevron → anchor chip (if focusable) → branch chips in row order → elevated chip → base chips in row order → active response card (Regenerate → Close if open).
- Escape key on any chip closes the response card (if open). No other escape behavior — the sheet itself can't be closed (by spec — compact is the minimum).

### 3.7 Vision Verdict

APPROVED. All Brightpath tokens referenced exist in `DESIGN.md`. All motion values are either existing presets in `motion.ts` or authored above with exact config values ready to drop into `frontend/src/styles/motion.ts` verbatim. No §2 Decisions have been contested; no §10 routing needed.

---

### Scope for @fp-design-visionary

Deliver pixel-perfect specs for:

1. **Page layout (desktop primary, mobile secondary).**
   - Header (CHOOSE YOUR PATH eyebrow, H1, subhead) — unchanged.
   - Top region (~2/3 viewport): three vertically-stacked tier sections. Each tier opens to a 2-column card grid on desktop (`grid-cols-1 tablet:grid-cols-2` — same grid already used inside `CareerTierSection`; only the outer containment changes). Cards wider than the current 3-tiers-side-by-side layout.
   - Bottom region (~1/3 viewport): `CareerLineageSheet` anchored to the bottom of the viewport, spanning full page width. Always visible.
   - "See my build" CTA stays below the tier zone but must never be obscured by the sheet at the compact detent. (Verify: at compact 33 %, CTA is still visible; at medium 50 %, CTA may scroll under sheet; at large 85 %, CTA is definitionally hidden.)

2. **CareerLineageSheet component (new).**
   - Structure: drag handle + title row + lineage flow area + Ask-Gemma chip row + Ask-Gemma response card + chevron buttons.
   - Drag handle: centered, top edge, standard iOS pill affordance sized to Brightpath spacing tokens.
   - Title row: "Where this career leads" + selected career title + inline `GemmaThinking` indicator when branch fetch in flight.
   - Lineage flow area: horizontal flow. Selected-career chip on the left, connector glyph, then each branch chip in sequence. Each branch chip shows `to_title`, non-zero stat deltas (stacked pill style), and optional rationale text when available from `career_transitions`. Horizontal scroll (not wrap) when the row overflows the viewport.
   - Chevron buttons (up/down) vertically centered on the right edge of the handle area. Clicking steps up/down one detent.
   - Empty state (no SOC selected): "Pick a career path above to see where it leads." (dimmed, centered).
   - Loading state: `GemmaThinking` pattern inline with title.
   - Error state: terse failure message + retry button using existing `RetryButton` / error styling patterns.

3. **Ask-Gemma chip row (new, lives inside `CareerLineageSheet`).**
   - Always visible — renders at every detent. At compact detent the chips sit directly beneath the lineage flow; at medium/large the response card also opens beneath the selected chip.
   - Chip set comes from `GET /career-pick/chips` (backend-owned, see §4). Frontend renders in the order returned.
   - Elevated ("Why don't I see [X]?") chip is visually distinct: Brightpath `accent-alert` background tint + a subtle ambient pulse (respecting reduced-motion).
   - Each chip is a button with `role="button"`, keyboard-activatable with Enter/Space.
   - Clicking a chip: (a) visually marks it as active, (b) fires `POST /career-pick/ask`, (c) opens the response card below with a `GemmaThinking` indicator until the response lands, (d) if the sheet is at compact detent, auto-promotes to medium so the response is legible.
   - Response card: Gemma's answer rendered in body typography. Regenerate button on the right edge (same chip, new Gemma call). Close button collapses back to chips-only. Only one response card visible at a time — clicking a different chip replaces the response.
   - Empty state for the Ask-Gemma row (before any click): a one-line hint "Not sure about something? Ask Gemma." above the chip row.

4. **Motion specifications (add to `frontend/src/styles/motion.ts`).**
   - Detent heights: `sheetDetent.compact = 33vh`, `sheetDetent.medium = 50vh`, `sheetDetent.large = 85vh` (or percentage of container — Visionary's call).
   - Snap spring preset: new named preset, e.g. `sheetSnap` (stiffness ≈ 420, damping ≈ 42 — Visionary tunes).
   - Drag handle pulse (idle affordance): optional ambient animation. If added, must respect reduced-motion.
   - Branch chip entrance stagger: reuse `stagger` from `motion.ts` if it fits; otherwise propose a named preset.
   - Elevated-chip ambient pulse: new named preset. Honor reduced-motion by disabling the pulse.
   - Chip-to-response transition: new named preset for the response card expanding beneath its chip (height + opacity). Visionary's call on exact spring.

5. **Responsive behavior.**
   - Desktop ≥1024 px (primary): as above.
   - Tablet 768–1023 px: sheet behaves identically; card grid collapses to 1 column inside each tier.
   - Mobile <768 px: sheet detents adjust (compact may need to grow to ~45 % to stay legible on small viewports); cards 1 column. Chip row stays horizontal-scroll if it overflows.

6. **Accessibility.**
   - Tier disclosures: `aria-expanded`, keyboard-operable. (Already done in `CareerTierSection.tsx:37–38`; this is just confirmation.)
   - Sheet: `role="dialog"` with `aria-modal="false"` (it's a persistent peek, not a blocking modal). `aria-label` updates with detent: "Lineage panel — compact / medium / full".
   - Drag handle: `role="slider"`, `aria-valuetext="compact | medium | large"`, `aria-orientation="vertical"`. `tabIndex={0}`, focus-visible ring using Brightpath focus token.
   - Keyboard: `ArrowUp`/`ArrowDown` on the handle or either chevron cycles detents. `Enter`/`Space` on chevron activates.
   - Reduced motion: honor `prefers-reduced-motion: reduce` — snap instantly, no easing; drag handle pulse disabled; elevated-chip ambient pulse disabled.
   - Card-select → sheet-populate transition: announce politely via `aria-live="polite"` on the sheet title.
   - Ask-Gemma chip row: chips are keyboard-focusable in DOM order; elevated chip announces its elevation via `aria-describedby` pointing at a visually-hidden "this question might be relevant to you" span. Response card has `role="region"` with `aria-live="polite"` so the answer text is announced when it arrives. Regenerate + close buttons labeled.

---

## §4 Technical Specification

### Architecture Overview

**Frontend.** The screen `frontend/src/screens/CareerPickScreen.tsx` is reworked at the outer layout level; the inner `CareerTierSection.tsx` is untouched. Net-new components: `CareerLineageSheet.tsx` (the sheet) + `BranchChip.tsx` (one branch) + `AskGemmaChipRow.tsx` (the chip row inside the sheet) + `AskGemmaResponseCard.tsx` (the response). Motion tokens land in `frontend/src/styles/motion.ts`. The frontend adds two new API clients: `getBranchesForSoc(soc)` against the existing `GET /branches/{soc}`, and `getCareerPickChips(...)` + `askCareerPickChip(...)` against the new endpoints described below.

**Backend.** Two new endpoints under a new router `backend/app/routers/career_pick.py`, plus one new service module `backend/app/services/career_pick_qna.py` that owns the canned question catalog + auto-elevation heuristic + the Gemma prompt builder. The service calls the already-landed `gemma_client.generate_async` (with its semaphore + JSONL-safe log append) so concurrency + logging are inherited for free. No schema changes, no new Iceberg tables, no stat formula changes.

**State.** No changes to `buildStore` / `buildInputStore` / `profileStore`. Sheet detent, currently-displayed-SOC, active chip id, and Ask-Gemma response text are all local `useState` in `CareerPickScreen` (or in the sheet component — implementer's call, but not promoted to Zustand).

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/screens/CareerPickScreen.tsx` | Modify | Rework outer layout from 3-col-tiers-side-by-side to 1-col-tiers-stacked. Add `CareerLineageSheet` at the bottom. Add `useState` for sheet detent + currently-displayed-SOC + active chip id + Ask-Gemma response text. Pass a new `onExplore` handler to each `CareerTierSection` card to populate the sheet on click (separate from existing `onSelect` that sets `selectedCareer`). On mount, prefetch chips via `getCareerPickChips` so they're ready by the time the sheet populates. Existing `loading` / `error` / `tieredCareers` logic unchanged. |
| `frontend/src/components/CareerLineageSheet.tsx` | Create | New component. Framer Motion `motion.div` with `drag="y"` + `dragConstraints` + `dragElastic` + `onDragEnd` snap-to-detent logic. Renders title row, horizontal branch flow, `AskGemmaChipRow`, `AskGemmaResponseCard` (when active), drag handle + chevron buttons. Fetches via `getBranchesForSoc` (new client). Loading/empty/error states. Full props contract in §4 Service Changes below. |
| `frontend/src/components/BranchChip.tsx` | Create | Renders one branch entry: `to_title`, non-zero stat deltas as Brightpath stat pills (reuse `StatPill` if it exists — confirm during implementation), optional rationale. Extracted into its own component so `CareerLineageSheet` stays focused on the sheet mechanics. |
| `frontend/src/components/AskGemmaChipRow.tsx` | Create | Renders the horizontal chip row. Props: `chips: CareerPickChip[]`, `activeChipId: string | null`, `onChipClick: (chip) => void`. Elevated chip gets `accent-alert` styling + ambient pulse. Keyboard-focusable, `role="button"`, Enter/Space activation. Horizontal scroll on overflow. |
| `frontend/src/components/AskGemmaResponseCard.tsx` | Create | Renders the response card beneath the active chip. Props: `loading: boolean`, `answer: string | null`, `onRegenerate: () => void`, `onClose: () => void`. Loading state uses `GemmaThinking`. Response uses body typography. Regenerate + close buttons labeled + keyboard-accessible. |
| `frontend/src/api/tree.ts` | Modify | Add `getBranchesForSoc(soc: string): Promise<CareerBranch[]>` that calls `GET /branches/{soc}` via `apiGet`. Keep existing `getTree(buildId)` untouched. Alternative: land the new function in a new file `frontend/src/api/branches.ts` if the split feels right — implementer's call. |
| `frontend/src/api/careerPick.ts` | Create | New API client module. Exports `getCareerPickChips(args)` and `askCareerPickChip(args)` — full signatures in §4 Service Changes. Mirror the `USE_MOCK` pattern in `tree.ts` + `mockCareerPick.ts`. |
| `frontend/src/api/mockCareerPick.ts` | Create | Mock fixture for offline dev. Returns a canned 4-chip set with the "Why don't I see 'doctor'?" chip included (mocked elevation flag) + canned Gemma-style responses. |
| `frontend/src/api/mockBranches.ts` | Create (if `VITE_USE_MOCK_API` is honored by the new client) | Mock fixture returning a small, deterministic `CareerBranch[]` for Storybook-style offline dev. Mirror the `USE_MOCK` pattern from `tree.ts:5`. |
| `frontend/src/styles/motion.ts` | Modify | Add named detent-height constants + `sheetSnap` spring preset + elevated-chip pulse + chip-to-response expand preset + (optional) drag-handle pulse. Exact values proposed by @fp-design-visionary in §3. |
| `frontend/src/types/build.ts` *(or wherever `CareerBranch` already lives — confirm during implementation)* | Modify (if fields missing) | Verify `CareerBranch` has the fields consumed by `BranchChip` (`to_soc`, `to_title`, `delta_ern`, `delta_roi`, `delta_res`, `delta_grw`, `delta_hmn`, optional `rationale`). If the rationale field is missing, this spec does not add it — surfacing rationale is a nice-to-have; flag as follow-up. |
| `frontend/src/types/careerPick.ts` | Create | New type file. Exports `CareerPickChip` + `AskCareerPickResponse` types matching the backend Pydantic models defined below. |
| `frontend/src/components/CareerLineageSheet.test.tsx` | Create | New vitest file. Covers detent snap logic, keyboard equivalence, populate-on-select fetch lifecycle, empty / loading / error states, a11y attributes, auto-promote-to-medium-on-chip-click. |
| `frontend/src/components/AskGemmaChipRow.test.tsx` | Create | New vitest file. Renders, keyboard activation, elevated-chip styling + aria-describedby, onChipClick wiring. |
| `frontend/src/components/AskGemmaResponseCard.test.tsx` | Create | New vitest file. Loading state, answer rendering, regenerate button fires callback, close button fires callback, aria-live announcement. |
| `frontend/src/screens/CareerPickScreen.test.tsx` *(if exists; otherwise create)* | Modify or Create | Covers the new outer layout (tiers stacked vertically), the onExplore → sheet populate wiring, the separation between `onSelect` (commits) and `onExplore` (previews), and the chip prefetch on mount. |
| `backend/app/routers/career_pick.py` | Create | New FastAPI router. Two endpoints: `GET /career-pick/chips` (query: `cipcode`, `major_text`, `soc_codes[]`) returning `list[CareerPickChip]`; `POST /career-pick/ask` (body: `AskCareerPickRequest`) returning `AskCareerPickResponse`. Both async. Register in `backend/app/main.py` alongside existing routers. |
| `backend/app/services/career_pick_qna.py` | Create | New service module. Owns: (a) the canned question catalog (constant list of `CannedQuestion` entries with `id`, `label`, `prompt_template`, `graduate_intent_pattern?`, `terminal_soc_pattern?`), (b) `build_chip_list(cipcode, major_text, soc_codes) -> list[CareerPickChip]` which applies the auto-elevation heuristic, (c) `ask(question_id, context) -> AskCareerPickResponse` which resolves the canned prompt template + calls `gemma_client.generate_async` with the scoped system prompt + logs the call with `call_site="career_pick.ask"`, (d) deterministic fallback strings per question when Gemma returns empty. |
| `backend/app/models/career_pick.py` | Create | New Pydantic models: `CareerPickChip`, `AskCareerPickRequest`, `AskCareerPickResponse`. Full schemas in §4 Data Model Changes. |
| `backend/app/main.py` | Modify | Register the new `career_pick` router under `/career-pick`. |
| `backend/tests/routers/test_career_pick_router.py` | Create | Covers the two endpoints: happy path, empty SOC list, malformed request → 422, `ask` returns fallback when Gemma is mocked to return empty, auto-elevation fires for `pre-med` + absent physician SOC. |
| `backend/tests/services/test_career_pick_qna.py` | Create | Covers the canned-question catalog, `build_chip_list` auto-elevation heuristic (positive + negative cases across pre-med, pre-law, pre-vet, pre-dental, "no match → no elevation"), `ask` prompt-builder shape, fallback-on-empty-Gemma, and `gemma.jsonl` receives `call_site="career_pick.ask"`. |
| `backend/app/routers/branches.py` | *(no change)* | Existing endpoint reused as-is. No new route added. |
| `backend/app/services/branch_tree.py` | *(no change)* | Existing service reused. |
| `backend/app/services/gemma_client.py` | *(no change)* | Reused. `generate_async` already has the semaphore + thread-safe JSONL append landed in `perf-reveal-loading-screen`. |

### Data Model Changes

**No Iceberg / DuckDB / MCP schema changes.** Three new Pydantic models in `backend/app/models/career_pick.py` for the two new endpoints:

```python
# backend/app/models/career_pick.py
from __future__ import annotations

from pydantic import BaseModel, Field


class CareerPickChip(BaseModel):
    """One canned question surfaced on /career-pick.

    Delivered by GET /career-pick/chips in the order the frontend should render.
    Elevated chips (``elevated=True``) are visually distinguished and move to the
    top of the row. ``terminal_title`` is populated only when the chip's question
    is parameterized on a terminal occupation the student's intent implies
    (e.g. "Why don't I see 'doctor'?" sets ``terminal_title="doctor"``).
    """

    id: str = Field(..., description="Stable chip identifier, e.g. 'why_no_terminal_soc'")
    label: str = Field(..., description="Button text shown to the student")
    elevated: bool = Field(default=False)
    terminal_title: str | None = Field(
        default=None, description="If this chip is about a specific missing occupation"
    )


class AskCareerPickRequest(BaseModel):
    """Student clicked a chip — resolve the canned prompt + call Gemma."""

    chip_id: str
    cipcode: str  # keep string per CLAUDE.md rule — CIPCODE is never float
    major_text: str
    soc_codes: list[str] = Field(default_factory=list)
    selected_soc: str | None = None
    terminal_title: str | None = None  # echoed back from the chip when applicable


class AskCareerPickResponse(BaseModel):
    """Gemma's answer (or deterministic fallback)."""

    chip_id: str
    answer: str = Field(..., description="4-6 sentences, 6th-grade reading level")
    fallback_fired: bool = Field(default=False)
```

**Frontend `CareerBranch` type** — implementer verifies during the first coding pass that it carries the fields `BranchChip` renders. If `rationale` is missing, the chip renders without it; adding rationale end-to-end is a follow-up, not in this spec.

**New frontend type file** `frontend/src/types/careerPick.ts` mirrors the three Pydantic models above in TypeScript.

### Service Changes

**Frontend public surface:**

```typescript
// frontend/src/api/tree.ts (or new file frontend/src/api/branches.ts)
export async function getBranchesForSoc(soc: string): Promise<CareerBranch[]>;

// frontend/src/api/careerPick.ts (new)
import type { CareerPickChip, AskCareerPickResponse } from "@/types/careerPick";

export interface GetChipsArgs {
  cipcode: string;
  majorText: string;
  socCodes: string[];
}

export async function getCareerPickChips(
  args: GetChipsArgs,
): Promise<CareerPickChip[]>;

export interface AskChipArgs {
  chipId: string;
  cipcode: string;
  majorText: string;
  socCodes: string[];
  selectedSoc?: string;
  terminalTitle?: string;
}

export async function askCareerPickChip(
  args: AskChipArgs,
): Promise<AskCareerPickResponse>;
```

**New component props:**

```typescript
// frontend/src/components/CareerLineageSheet.tsx
export type SheetDetent = "compact" | "medium" | "large";

interface CareerLineageSheetProps {
  /** SOC to fetch branches for. When null, the sheet shows its empty state. */
  soc: string | null;
  /** Full CareerOutcome of the selected-for-lineage card. Null when soc is null. */
  career: CareerOutcome | null;
  /** Current detent — controlled from CareerPickScreen. */
  detent: SheetDetent;
  /** Called on drag / chevron / arrow-key detent change. */
  onDetentChange: (next: SheetDetent) => void;
  /** Preloaded chip set from GET /career-pick/chips. Empty array while loading. */
  chips: CareerPickChip[];
  /** Context fields forwarded to POST /career-pick/ask when a chip is clicked. */
  askContext: { cipcode: string; majorText: string; socCodes: string[] };
}

export function CareerLineageSheet(props: CareerLineageSheetProps): JSX.Element;

// frontend/src/components/BranchChip.tsx
interface BranchChipProps {
  branch: CareerBranch;
}
export function BranchChip({ branch }: BranchChipProps): JSX.Element;

// frontend/src/components/AskGemmaChipRow.tsx
interface AskGemmaChipRowProps {
  chips: CareerPickChip[];
  activeChipId: string | null;
  onChipClick: (chip: CareerPickChip) => void;
}
export function AskGemmaChipRow(props: AskGemmaChipRowProps): JSX.Element;

// frontend/src/components/AskGemmaResponseCard.tsx
interface AskGemmaResponseCardProps {
  loading: boolean;
  answer: string | null;
  onRegenerate: () => void;
  onClose: () => void;
}
export function AskGemmaResponseCard(props: AskGemmaResponseCardProps): JSX.Element;
```

**Backend public surface** (in `backend/app/services/career_pick_qna.py`):

```python
# Canonical question catalog — add new entries here, not in the router.
@dataclass(frozen=True)
class CannedQuestion:
    id: str
    label_template: str               # may reference {terminal_title}
    prompt_template: str              # Gemma user prompt, may reference context fields
    fallback_template: str            # deterministic string when Gemma returns ""
    graduate_intent_pattern: str | None = None  # e.g. r"pre[\s-]?med"
    terminal_socs: tuple[str, ...] = ()         # e.g. ("29-1215", "29-1216", ...)
    terminal_title: str | None = None           # e.g. "doctor"


# Module-level constant — not reassigned at runtime.
CANNED_QUESTIONS: tuple[CannedQuestion, ...] = (...)


def build_chip_list(
    *,
    cipcode: str,
    major_text: str,
    soc_codes: Sequence[str],
) -> list[CareerPickChip]:
    """Return the chip set for this screen state.

    Applies the auto-elevation heuristic: if ``major_text`` matches a question's
    ``graduate_intent_pattern`` AND none of ``soc_codes`` is in that question's
    ``terminal_socs``, the chip is elevated and moved to the front. Otherwise
    returned in catalog order.
    """


async def ask(
    *,
    request: AskCareerPickRequest,
) -> AskCareerPickResponse:
    """Resolve the canned prompt for ``request.chip_id`` + call Gemma.

    Returns the Gemma response when non-empty, else the question's
    deterministic fallback. Always populates ``fallback_fired`` so the
    frontend / downstream telemetry can distinguish the two paths.
    Adds ``call_site="career_pick.ask"`` to the gemma.jsonl record.
    """
```

**Backend router surface** (in `backend/app/routers/career_pick.py`):

```python
router = APIRouter(prefix="/career-pick", tags=["career-pick"])


@router.get("/chips", response_model=list[CareerPickChip])
async def get_chips(
    cipcode: str,
    major_text: str,
    soc_codes: list[str] = Query(default_factory=list),
) -> list[CareerPickChip]: ...


@router.post("/ask", response_model=AskCareerPickResponse)
async def ask(request: AskCareerPickRequest) -> AskCareerPickResponse: ...
```

**Gemma system prompt** (constant in `career_pick_qna.py`):

```
You are Gemma, explaining a single career-pick screen to a high school student.

Context you see:
- The student's original typed major text (could be informal like "pre-med")
- The CIP code their major resolved to
- The list of occupation SOC codes currently shown on their screen
- Optionally, a specific terminal occupation the student was implicitly looking for

Your job: answer the one canned question the student clicked, in 4-6 sentences,
at a 6th-grade reading level. Cite the actual data on the screen when possible
(name the jobs, cite salary ranges if present). Never give medical, legal, or
financial advice. Never recommend a different school. If the question is about
a missing occupation, explain the undergrad-vs-graduate distinction plainly and
tell the student what they'd typically need to pursue that path (e.g. "doctor
usually means going to med school after college").

Voice rules (inherit from the `guidance.py` canon):
- Short sentences. Concrete nouns. Zero filler.
- Never use: empowering, journey, unlock, transform, passion, dream career.
- No exclamation points. No "as an AI". No markdown.
- No bullet points. Plain prose, 4-6 sentences.
```

Individual question `prompt_template`s fill in the question-specific body and pass the context fields. The service enforces the `max_tokens` ceiling and the `temperature` (same 0.7 default as other narrative call sites).

### Gemma-Touching Discipline

This spec adds one new `gemma_client.generate_async` call site (`career_pick_qna.ask`). Per FutureProof Gemma discipline:

- **Fallback per call site.** Each `CannedQuestion` carries its own `fallback_template`. If Gemma returns empty string (transport error → `""` per `generate_async` contract), `ask()` substitutes the canonical fallback, sets `AskCareerPickResponse.fallback_fired = True`, and still returns a 200 to the frontend. The UI must render any non-empty `answer` the same way; only telemetry cares about `fallback_fired`.
- **`logs/gemma.jsonl` completeness.** Every call passes `call_site="career_pick.ask"` as an added record field so the audit trail is inspectable. Add the field to the `_log_exchange` record from the call site; no changes to `gemma_client` itself.
- **Both backends verified.** The spec's success criteria apply under both `INFERENCE_BACKEND=ollama` (local) and `INFERENCE_BACKEND=openrouter` (cloud demo). No streaming, so no backend-specific SSE quirks. §9 manual smoke covers both.
- **Rate-limit / concurrency.** `generate_async` already owns the module-level `asyncio.Semaphore` (capped by `GEMMA_MAX_CONCURRENCY`, default 8). A chip click on top of an in-flight `/build` fan-out will queue behind the existing 8-wide budget. Acceptable — chip clicks are interactive and bursty, not sustained. No new rate-limit work.

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/CareerPickScreen.test.tsx` (if present) | Any test asserting the outer 3-column tier layout or the presence/absence of a lineage sheet / chip row | High | Layout is being reworked and a chip row + sheet are being added. |
| `frontend/src/components/CareerTierSection.test.tsx` (if present) | All | Low | `CareerTierSection` is untouched. Any failure here is a real regression, not an authorized change. |
| `frontend/src/screens/RevealScreen.test.tsx` | All | None (Confirmed Safe) | `RevealScreen` is downstream of `/career-pick`. `selectedCareer` contract is unchanged. |
| `frontend/src/api/tree.test.ts` | All | Low | We add a function; existing `getTree` tests are untouched. Any existing test expecting `tree.ts` to export exactly `getTree` and nothing else will need updating — that's the only authorized change here. |
| `backend/tests/services/test_branch_tree.py` (if present) | All | None (Confirmed Safe) | No backend changes to `branch_tree`. |
| `backend/tests/services/test_gemma_client.py` | All | None (Confirmed Safe) | No changes to `gemma_client` itself. New call site passes an extra `call_site` log field through the existing record dict — doesn't modify `gemma_client`'s signature. |
| `backend/tests/routers/**` existing | All | None (Confirmed Safe) | No changes to existing routers. |
| `backend/app/main.py` router registration | N/A | Low | Adding one more `app.include_router(career_pick.router)` line. If tests assert exact registered router count, they need updating — explicitly authorized below. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `CareerPickScreen.test.tsx` (if it exists) | Update layout-structure assertions to match the new vertical-stacked tiers + sheet-present + chip-row-present DOM. Preserve selection-flow assertions. | Outer DOM changes materially. |
| `tree.test.ts` | If a test asserts the module exports exactly `{ getTree }`, expand to include `{ getTree, getBranchesForSoc }`. | New client function added to the module. |
| Any backend test that asserts the exact list of registered routers on `app.main.app` | Add `career_pick` to the expected list. | One new router registered. |

#### Confirmed Safe

These tests must NOT break. If any fail during implementation, STOP and escalate via §10:

- `RevealScreen.test.tsx` — reveal flow, pacing floor.
- `CareerTierSection.test.tsx` (if present) — per-tier disclosure.
- `CareerCard.test.tsx` (if present) — card internals.
- `GemmaThinking.test.tsx` (if present) — loading indicator.
- All backend tests — no backend changes.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `renders empty state when soc is null` | Empty state text + no fetch fired. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `fetches branches when soc prop changes` | `getBranchesForSoc` called exactly once per distinct SOC; cancels in-flight on prop change. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `renders branch chips for each returned branch` | Every returned `CareerBranch` produces a `BranchChip`; ordering matches API response ordering. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `chevron up transitions compact → medium → large` | Click the up-chevron from each detent; assert `onDetentChange` called with the next detent each time. Large stays at large. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `chevron down transitions large → medium → compact` | Mirror of above. Compact stays at compact. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `ArrowUp / ArrowDown on handle cycles detents` | Keyboard equivalence. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `renders error state when fetch rejects` | Error message visible; retry button present. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `retry button refetches after error` | Clicking retry triggers a new `getBranchesForSoc` call. |
| P0 | `frontend/src/screens/CareerPickScreen.test.tsx` | `tiers render stacked vertically, each individually collapsible` | Outer container is single-column; every tier disclosure toggles independently. |
| P0 | `frontend/src/screens/CareerPickScreen.test.tsx` | `clicking a card populates the lineage sheet with that card's SOC` | `onExplore` (new handler) wires to sheet soc prop; does NOT call `setSelectedCareer`. |
| P0 | `frontend/src/screens/CareerPickScreen.test.tsx` | `committing a pick still navigates to /reveal` | `selectedCareer` + "See my build" → navigate is unchanged. |
| P1 | `frontend/src/components/CareerLineageSheet.test.tsx` | `drag end past mid-point snaps to next detent` | Simulate `onDragEnd` with offset + velocity; assert resolved detent is the expected one. (Framer Motion drag gesture is JSDOM-hostile; mock Framer internals or drive `onDragEnd` directly.) |
| P1 | `frontend/src/components/CareerLineageSheet.test.tsx` | `reduced-motion user gets instant detent change` | `matchMedia` stub for `prefers-reduced-motion: reduce`; assert snap animation uses zero-duration preset. |
| P1 | `frontend/src/components/CareerLineageSheet.test.tsx` | `aria-label reflects current detent` | `aria-label` on the sheet contains "compact / medium / full" per state. |
| P1 | `frontend/src/components/CareerLineageSheet.test.tsx` | `aria-live title announces on SOC change` | Title region has `aria-live="polite"`; title text updates when soc prop changes. |
| P1 | `frontend/src/screens/CareerPickScreen.test.tsx` | `onExplore and onSelect are distinct gestures` | Explicit coverage that populate-sheet and commit-pick are not conflated (spec §2 Decision #5). |
| P2 | `frontend/src/components/BranchChip.test.tsx` | `renders non-zero stat deltas only` | Stat pills only appear for deltas ≠ 0. Deltas of 0 are suppressed. |
| P2 | `frontend/src/components/BranchChip.test.tsx` | `renders rationale when present, omits when missing` | Rationale field is optional. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_build_chip_list_elevates_pre_med_when_physician_missing` | `major_text="pre-med"`, SOC list lacks `29-1216` → `why_no_terminal_soc` chip is first + `elevated=True` + `terminal_title="doctor"`. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_build_chip_list_no_elevation_when_physician_present` | `major_text="pre-med"`, SOC list includes `29-1216` → the elevated chip is NOT in the list (or at least not elevated). |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_build_chip_list_handles_pre_med_variants` | Matches "pre-med", "premed", "pre med" case-insensitively; does NOT match "premedication" or "comedy premeditation" (word-boundary safety). |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_build_chip_list_pre_law_variant` | `major_text="pre-law"`, SOC list lacks `23-1011` → elevated chip targets "lawyer". Symmetry check for pre-vet, pre-dental. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_build_chip_list_non_graduate_intent_returns_base_catalog` | `major_text="marketing"` → no elevation, chips in catalog order. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_ask_happy_path` | `generate_async` mocked to return canned text; `AskCareerPickResponse.answer` matches, `fallback_fired=False`. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_ask_falls_back_when_gemma_returns_empty` | `generate_async` mocked to return `""`; response uses the question's `fallback_template` and `fallback_fired=True`. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_ask_falls_back_when_gemma_raises` | `generate_async` mocked to raise; service catches and falls back identically. |
| P0 | `backend/tests/services/test_career_pick_qna.py` | `test_ask_unknown_chip_id_raises_value_error` | Calling `ask` with a chip_id not in the catalog raises a clean `ValueError` (router maps to 404 or 422 — assert from the router test). |
| P1 | `backend/tests/services/test_career_pick_qna.py` | `test_ask_writes_call_site_to_gemma_jsonl` | Patch `_log_path` to tmp, call `ask`, assert the emitted JSONL record contains `call_site="career_pick.ask"` + `chip_id`. |
| P0 | `backend/tests/routers/test_career_pick_router.py` | `test_get_chips_returns_elevated_chip_for_pre_med` | `GET /career-pick/chips?cipcode=26.0101&major_text=pre-med&soc_codes=19-1029` → response has elevated chip first, `terminal_title="doctor"`. |
| P0 | `backend/tests/routers/test_career_pick_router.py` | `test_post_ask_returns_gemma_response` | `POST /career-pick/ask` with a valid chip_id → 200 with `AskCareerPickResponse`. Gemma mocked. |
| P0 | `backend/tests/routers/test_career_pick_router.py` | `test_post_ask_unknown_chip_id_returns_422` | Unknown chip_id → 422. |
| P1 | `backend/tests/routers/test_career_pick_router.py` | `test_post_ask_malformed_body_returns_422` | Missing required fields → 422 from Pydantic. |
| P0 | `frontend/src/components/AskGemmaChipRow.test.tsx` | `renders chips in order with elevated chip styled distinctly` | Elevated chip gets `accent-alert` class; non-elevated chips don't. |
| P0 | `frontend/src/components/AskGemmaChipRow.test.tsx` | `keyboard activation (Enter/Space) fires onChipClick` | |
| P0 | `frontend/src/components/AskGemmaChipRow.test.tsx` | `aria-describedby on elevated chip points to elevation hint` | |
| P0 | `frontend/src/components/AskGemmaResponseCard.test.tsx` | `renders loading state with GemmaThinking` | |
| P0 | `frontend/src/components/AskGemmaResponseCard.test.tsx` | `renders answer when loaded` | |
| P0 | `frontend/src/components/AskGemmaResponseCard.test.tsx` | `regenerate button fires onRegenerate` | |
| P0 | `frontend/src/components/AskGemmaResponseCard.test.tsx` | `close button fires onClose` | |
| P1 | `frontend/src/components/AskGemmaResponseCard.test.tsx` | `has role=region and aria-live=polite` | |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `chip click auto-promotes compact detent to medium` | After `onChipClick`, `onDetentChange` called with `"medium"`. No-op from medium or large. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `chip click fires askCareerPickChip with correct context` | Context fields from props + active chip id/terminal_title. |
| P0 | `frontend/src/components/CareerLineageSheet.test.tsx` | `switching chips replaces the response card` | Only one response card at a time. |
| P0 | `frontend/src/screens/CareerPickScreen.test.tsx` | `prefetches chips on mount once tiered careers resolve` | `getCareerPickChips` called once with `{cipcode, majorText, socCodes}` derived from the tier response. |

#### Test Data Requirements

- Mock `getBranchesForSoc` in CareerLineageSheet tests via `vi.mock("@/api/tree", ...)` (or `@/api/branches` if implementer chose the split). Seed with 3–5 branches covering different delta-stat combinations.
- Mock `getCareerPickChips` + `askCareerPickChip` in frontend tests via `vi.mock("@/api/careerPick", ...)`. Canned chip fixtures include one elevated chip so that styling can be exercised.
- Reuse the existing `CareerOutcome` test fixtures from `CareerPickScreen` tests (if present) or build a small `_career()` factory mirroring `backend/tests/services/test_builds.py::_career`.
- `matchMedia` stub for reduced-motion in test setup — confirm `frontend/src/test/setup.ts` already has one; if not, add it.
- Framer Motion drag gesture testing: JSDOM does not dispatch pointer events in a way Framer Motion's gesture layer fully consumes. Tests should verify the `onDragEnd` handler contract by calling the component's resolved-detent function directly (expose via a small helper or via `ref.current`), rather than trying to drive a pointer drag end-to-end. Document this pattern in the test file header.
- Backend: mock `gemma_client.generate_async` in `test_career_pick_qna.py` + `test_career_pick_router.py` via `monkeypatch.setattr`. Autouse fixture `_reset_gemma_client_state` (landed in `backend/tests/services/conftest.py` via the perf-reveal-loading-screen spec) already handles semaphore cache reset — confirm it's inherited by the new router test module; if not, add a similar fixture in `backend/tests/routers/conftest.py`.
- Backend: one fixture `_canned_catalog_for_tests` that freezes the `CANNED_QUESTIONS` list so future catalog changes don't silently break existing tests. Tests that want to exercise a specific question import its `CannedQuestion` instance from the service module.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** SKIPPED — No new backend API surface, no schema changes, no new module creating architectural coupling. Frontend-only layout + component work. (Per §2 Decision #1 and the spec's Standard-weight calibration.)

### @fp-data-reviewer Review
**Status:** SKIPPED — No pipeline changes, no stat formula changes, no crosswalk changes. Existing `consumable.career_branches` + `consumable.career_transitions` tables consumed read-only via an existing backend endpoint.

---

## §6 Implementation Log

**Status:** COMPLETE (pending test-writer + audit + review)

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/models/career_pick.py` | Created — `CareerPickChip`, `AskCareerPickRequest`, `AskCareerPickResponse`. CIPCODE kept as `str` per project rule. |
| `backend/app/services/career_pick_qna.py` | Created — seven `CannedQuestion` entries (pre-med → "Why don't I see 'doctor'?", pre-law → "Why don't I see 'lawyer'?", pre-vet, pre-dental, plus three base-catalog questions: what-does-this-do / right-school-for-this / why-these-tiers). Owns `build_chip_list` (auto-elevation via word-boundary regex + terminal-SOC absence) and `ask` (prompt builder → `gemma_client.generate_async` → deterministic fallback on empty, supplemental JSONL record tagged `call_site="career_pick.ask"`). |
| `backend/app/routers/career_pick.py` | Created — `GET /career-pick/chips` (async) and `POST /career-pick/ask` (async). Unknown chip_id is translated to 422 via `ValueError` → `HTTPException`. |
| `backend/app/main.py` | Added `career_pick` to the import list + registered the router. |
| `frontend/src/styles/motion.ts` | Added the seven §3.4 presets verbatim: `sheetDetent` (vh fractions), `sheetSnap` (spring), `sheetDragElastic`, `sheetFlingVelocity`, `chipResponseExpand` (hybrid opacity tween + height spring), `elevatedChipPulse` (2.4s boxShadow breathe), `handlePulse` (2.2s opacity breathe, optional). |
| `frontend/src/types/careerPick.ts` | Created — mirrors the three Pydantic models. |
| `frontend/src/api/careerPick.ts` | Created — `getCareerPickChips` + `askCareerPickChip`. Honors `VITE_USE_MOCK_API`. |
| `frontend/src/api/mockCareerPick.ts` | Created — fixture chip set with pre-med elevation flag applied when `majorText` matches; canned answers keyed by chip_id. |
| `frontend/src/api/mockBranches.ts` | Created — deterministic branch fixture keyed by SOC. |
| `frontend/src/api/tree.ts` | Added `getBranchesForSoc(soc)` alongside existing `getTree(buildId)`. Mock-aware via the same `VITE_USE_MOCK_API` switch. |
| `frontend/src/components/BranchChip.tsx` | Created — renders branch title, non-zero stat delta pills (0 suppressed, magnitude 1-3 as `+`/`-` glyphs), optional rationale, keyboard-focusable with the Brightpath focus ring. |
| `frontend/src/components/AskGemmaChipRow.tsx` | Created — renders the chip set in the order delivered by the backend. Elevated chip carries `accent-alert` palette + filled dot + `aria-describedby` pointing at the elevation hint + ambient pulse (gated on `useReducedMotion`). Non-elevated chips use accent-info palette; active state adds the glow. Enter/Space fires `onChipClick`. |
| `frontend/src/components/AskGemmaResponseCard.tsx` | Created — Gemma attribution row + body copy (with `whitespace-pre-line` so the plain-prose answer renders naturally) + Regenerate + Close buttons. `role="region"` + `aria-live="polite"` so screen readers announce the answer. Enter/exit via the `chipResponseExpand` preset. |
| `frontend/src/components/CareerLineageSheet.tsx` | Created — the centerpiece. `motion.div` with `drag="y"` + elastic `dragConstraints` + `sheetSnap` animation. Five zones (handle + chevrons, title, lineage flow, chip row, response card). Exposes a pure `resolveDetent` helper for P0/P1 drag-end tests without driving a live pointer. Generation-token fetch guard for branch lifecycle (cancels stale responses on SOC change). Chip click auto-promotes `compact` → `medium`. `prefers-reduced-motion` swaps the snap animation for a zero-duration tween and zeroes the drag elasticity. |
| `frontend/src/components/CareerCard.tsx` | Split click-gesture: the card body fires `onExplore` (populates the sheet), a dedicated inline "Pick this path" button fires `onSelect` (commits to `buildStore`). The pick button carries `role="radio"` so the existing radiogroup semantics inside `CareerTierSection` remain intact and keyboard-accessible. |
| `frontend/src/components/CareerTierSection.tsx` | Added a required `onExplore` prop that forwards to `CareerCard`. No other behavior change — disclosure + grid layout untouched per §2 Decision #7. |
| `frontend/src/screens/CareerPickScreen.tsx` | Outer layout: tiers are always `grid-cols-1` (never 3-up). CTA is inline below the tiers, never fixed. Reserves bottom padding for the compact detent (`pb-[calc(33vh+var(--space-6))]` at desktop/tablet, `calc(45vh+var(--space-6))` at mobile). New `useState`s for `lineageCareer`, `detent`, `chips`. Prefetches chips via `getCareerPickChips` once `tieredCareers` lands. Mounts `CareerLineageSheet` at the bottom of the viewport once tiers resolve. |
| `frontend/src/components/CareerTierSection.test.tsx` | Added `onExplore={vi.fn()}` to each render call — required-prop addition, not a behavior change. |
| `frontend/src/screens/CareerPickScreen.test.tsx` | Updated: (a) outer grid assertion checks `grid-cols-1` and absence of `desktop:grid-cols-3`, (b) new explore-vs-select separation test, (c) card-body click triggers `getBranchesForSoc` without mutating `selectedCareer`, (d) chip prefetch firing on mount. All prior selection-flow assertions preserved via the inline pick button. |

### Deviations from Spec

- **Decision #5 resolution.** §2 Decision #5 required "a separate action from populating the sheet" but §3 Design Vision didn't spec the exact gesture split. Implemented as: card-body click → `onExplore`; inline "Pick this path" pill inside each card → `onSelect`. The pill carries `role="radio"` to preserve the radiogroup semantics already wired through `CareerTierSection`. This preserves every existing CareerPickScreen test's intent and keeps keyboard + screen-reader parity for the commit gesture.
- **Frontend status.** `CareerBranch` was verified to already carry every field `BranchChip` reads (`to_title`, `delta_*`). `unlock` is rendered in place of `rationale` since `unlock` is the already-populated human-readable descriptor from the Gold data (`branch_tree.py` formats `related_education_level` + `relatedness_tier` into `unlock`). When the follow-up `rationale` field lands on the backend, `BranchChip` swaps the prop name — one-line change.
- **Backend mypy.** `backend/app/main.py:54 async def startup():` has a pre-existing missing-return-type error unrelated to this spec's changes. Confirmed pre-existing via `git blame` (commit ead552dd, 2026-04-12). Not fixed under this spec.
- **Frontend vitest.** `src/screens/ProfileScreen.test.tsx` has 2 pre-existing failing tests (seeded-profile deterministic naming). Confirmed pre-existing on `main` via `git stash` + rerun. Not caused by this spec.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 (backend) | pass | ruff clean; new files pytest green; mypy pre-existing startup annotation | none (not this spec's scope) |
| 1 (frontend tsc) | 6 errors | `SheetDetent \| undefined` from array indexing; `HTMLElement \| undefined` from `getAllByRole(...)[0]` under `noUncheckedIndexedAccess` | explicit `as SheetDetent` casts on the bounds-checked array reads; `!` non-null assertions on test selectors |
| 2 (frontend tsc) | pass | — | — |
| 1 (vitest) | 11/11 affected tests pass; only pre-existing ProfileScreen tests fail | — | — |

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | | | | |
| vitest (frontend) | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Vision (@fp-design-visionary)
**Status:** APPROVED — §3 UI/UX Design filled in 2026-04-18. Net-new motion presets authored in §3.4 ready to land in `frontend/src/styles/motion.ts` verbatim: `sheetDetent`, `sheetSnap`, `sheetDragElastic`, `sheetFlingVelocity`, `chipResponseExpand`, `elevatedChipPulse`, `handlePulse` (optional). No DESIGN.md edits required — all color, typography, pill, card, and shadow tokens already exist.

### Design Audit (@fp-design-auditor)
**Status:** PENDING — runs post-implementation against §3 + `DESIGN.md`.

#### Findings
_Filled in by auditor._

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

### Code Review (@faang-staff-engineer)
**Status:** PENDING

#### Findings
_Filled in by reviewer._

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
| Lint (ruff check backend/) | |
| Type check (mypy backend/app/) | |
| Tests (pytest backend/) | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript (tsc --noEmit) | |
| Tests (vitest run) | |
| Production build (vite build) | |

### Manual Interaction Smoke

Run through the following on a live dev server (`npm run dev`) at desktop viewport + a ≤768 px mobile-emulated viewport:

| Scenario | Expected | Actual |
|----------|----------|--------|
| Load `/career-pick` after picking a school + major | Three tiers stacked vertically; sheet at compact detent; sheet empty state visible | |
| Click a Common-tier card | Sheet fetches + populates with that SOC's branches; loading indicator visible briefly | |
| Click a different Common-tier card | Sheet re-fetches for new SOC; in-flight previous fetch cancelled (no race) | |
| Drag sheet handle up slowly past mid-point | Snaps to medium detent | |
| Drag sheet handle up fast (fling) | Snaps to large detent | |
| Keyboard: Tab to handle, press `ArrowUp` twice | Detent goes compact → medium → large | |
| Click chevron-up button | Same as ArrowUp | |
| Toggle Stretch tier collapsed, click Common-tier card | Stretch stays collapsed; sheet populates | |
| Select a card + click "See my build" | Navigates to `/reveal`; build succeeds | |
| Mobile emulated viewport | Tier cards collapse to 1 column; sheet detents scale appropriately; drag + chevron both functional | |
| `prefers-reduced-motion: reduce` (via devtools rendering emulation) | Sheet snaps without easing; drag-handle pulse disabled | |
| Screen reader (VoiceOver / NVDA spot-check) | Sheet announces its detent; card click announces lineage populated; chip clicks announce their response | |
| Searched "pre-med" at Millikin → picked Biology → landed on this screen | Elevated "Why don't I see 'doctor'?" chip is first, styled in accent-alert tint, optional pulse | |
| Clicked the elevated "Why don't I see 'doctor'?" chip | Response card opens, `GemmaThinking` shows briefly, 4-6 sentence Gemma answer appears explaining the undergrad / med-school distinction | |
| Clicked a non-graduate-intent major (e.g. "marketing") + any card | No elevated chip; base chip catalog appears | |
| Clicked chip, clicked Regenerate | New Gemma call fires, answer updates; `fallback_fired` is false when Gemma live | |
| Force Gemma failure (kill Ollama or bad OpenRouter key) + click chip | Fallback string renders (not error state); `gemma.jsonl` record still written with `call_site="career_pick.ask"` + `error` field | |
| Tail `logs/gemma.jsonl` after a session with multiple chip clicks | Every chip click has one record with `call_site="career_pick.ask"` + `chip_id` + `answer`/`error` | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[placeholder — timestamped messages between agents go here]
```

---

## §11 Final Notes

**Human Review:** PENDING

**Companion follow-up specs (after this one lands):**

1. **`feature-ask-gemma-freeform.md`** (Priority: post-hackathon). Free-form chat input for asking Gemma anything on `/career-pick` (and eventually elsewhere). Requires a guardrail system prompt, OpenAI-moderation-style pre-pass, off-topic refusal coverage, reviewed-transcript capture. Scoped only after the chip row surfaces which canned questions students actually click — that'll tell us what the long-tail looks like and whether free-form is worth the guardrail spend.
2. **`feature-graduate-track-branches.md`** (Priority: long-term, not hackathon). Seed `consumable.career_branches` with professional-school jumps so pre-med / pre-law / pre-vet / MBA-ladder students see graduate-track destinations as actual nodes on the lineage flow (not just in Gemma's explanation text). De-prioritized by the Ask-Gemma chip in this spec — Gemma can explain the distinction today, which solves the user-confusion root cause. Real data still adds value (the "Physicians" card appearing in the lineage sheet would be genuinely better than Gemma talking about physicians), but no longer a demo blocker.
3. **Ask-Gemma chips on `/gauntlet` + `/reveal`** (Priority: medium). If the chip pattern proves out here, port to the other screens with screen-specific canned question catalogs. Pattern + infrastructure already in place from this spec.

_Final thoughts, lessons learned, follow-up items live here at COMPLETE time._
