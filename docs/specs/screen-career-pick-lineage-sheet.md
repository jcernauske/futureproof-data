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
```

---

## Status: DRAFT

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

**Status:** PENDING — @fp-design-visionary fills this section before implementation.

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

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
_None yet._

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
| pytest (backend) | | | | |
| vitest (frontend) | | | | |

---

## §8 Reviews

**Status:** PENDING

### Design Vision (@fp-design-visionary)
**Status:** PENDING — §3 UI/UX Design must be filled in before implementation starts.

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
